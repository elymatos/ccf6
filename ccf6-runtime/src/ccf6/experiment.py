"""Running a declared experiment and writing its artifact.

An experiment is a file. Running it is a function from that file to an artifact
directory, so a run is reproducible, diffable and re-renderable without re-running
(ADR-0007). Nothing meaningful is configured anywhere else — the workbench may
*generate* this file, but it may not carry semantics the file does not.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ccf6 import figures, params
from ccf6.ego import Presentation
from ccf6.metrics import (
    figure_separation,
    population_separation,
    summarise_by_level,
    two_way_selectivity,
)
from ccf6.network import Architecture, Network
from ccf6.thalamus import ENCODERS, Thalamus
from ccf6.world import PALETTE, World


def load(path: str | Path) -> dict:
    text = Path(path).read_text()
    if str(path).endswith((".yaml", ".yml")):
        import yaml  # optional; JSON needs no dependency at all

        return yaml.safe_load(text)
    return json.loads(text)


def digest(definition: dict) -> str:
    """A run's identity is its definition. Change the definition, change the run."""
    canonical = json.dumps(definition, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def build(definition: dict) -> tuple[Network, World, dict]:
    declared = dict(definition.get("architecture", {}))
    declared.pop("structures", None)
    arch = Architecture(**declared)
    if "structures" in definition.get("architecture", {}):
        arch.structures = tuple(definition["architecture"]["structures"])

    colour_kind = definition.get("colour_encoder", "population_colour")
    encoder = ENCODERS[colour_kind]
    colour = (encoder(arch.n_colours, arch.n_colours * 8) if colour_kind == "population_colour"
              else encoder(arch.n_colours))
    available = {
        "colour": colour,
        "shape": ENCODERS["local_shape"](),
        "position": ENCODERS["localist_position"](arch.world_size),
    }
    # Only the Spaces an experiment declared get an encoder: the Thalamus projects to
    # the Spaces that exist, and no others.
    thalamus = Thalamus({n: e for n, e in available.items() if n in arch.spaces})
    return Network(arch, thalamus), World(arch.world_size), params.resolve(definition.get("parameters"))


def _signals(world: World, patch_radius: int):
    """What the Thalamus is handed at one stop: what is here, not where here is.

    `patch_radius` comes from the shape encoder rather than being fixed here, so
    widening the window is one change in one place.

    The field is read from the World *as it stands when this is built*, so it must be
    rebuilt after every placement. A closure over a stale field would hand the network
    an empty patch and the Space fed by it would sit silently at the activation floor,
    looking like a wiring problem rather than a bookkeeping one.
    """
    padded = world.foreground(patch_radius)

    def at(step):
        i, j = step.position
        window = padded[i:i + 2 * patch_radius + 1, j:j + 2 * patch_radius + 1]
        return {"colour": step.colour, "shape": window, "position": step.position}

    return at


def run_structure_baseline(definition: dict) -> dict:
    """Present every figure at every position it fits, and measure what responds.

    A factorial design on purpose: shape and position vary independently, so the
    variance decomposition can say which factor a Column follows. No learning happens —
    this measures the substrate, and the numbers it reports are the null a local rule
    has to beat.
    """
    network, world, p = build(definition)
    if network.web is None:
        raise ValueError(
            "this experiment measures what Columns respond to, so it needs a Web; "
            "declare it in architecture.structures"
        )
    arch = network.arch
    ticks = int(definition.get("ticks", 20))
    order = definition.get("visiting_order", "raster")
    shapes = figures.named(definition.get("figures", sorted(figures.FIGURES)))
    names = definition.get("figures", sorted(figures.FIGURES))

    shape_encoder = network.thalamus.encoders.get("shape")
    radius = getattr(shape_encoder, "radius", 1)

    origins = [
        (i, j)
        for i in range(arch.world_size)
        for j in range(arch.world_size)
        if all(world.fits(shape, (i, j)) for shape in shapes)
    ]
    if not origins:
        raise ValueError("no World position holds every figure; enlarge the World")

    # Every origin gives a bit-identical response — the boundary is translation
    # invariant to machine precision — so running all of them buys nothing but cost.
    # An experiment declares how many to keep; `invariance_origins` is the separate,
    # cheap check that the claim still holds over all of them.
    limit = definition.get("max_origins")
    if limit:
        step = max(1, len(origins) // int(limit))
        origins = origins[::step][: int(limit)]

    responses = np.zeros((len(shapes), len(origins), max(network.response_vector().size, 1)))
    snapshots, schema_states, stops = [], {}, 0
    of_interest = [tuple(pos) for pos in definition.get("snapshot_positions", [origins[0]])]

    for si, shape in enumerate(shapes):
        for oi, origin in enumerate(origins):
            world.clear()
            world.place_object(shape, origin)
            presentation = Presentation.of_object(world, shape, origin, order)

            network.reset()
            # Built after placement: the field is a property of the World as it now
            # stands, not as it stood when the run began.
            responses[si, oi] = network.present(
                presentation, _signals(world, radius), ticks, p
            )
            stops += len(presentation.steps)
            if network.schema is not None:
                for step in presentation.steps:
                    schema_states.setdefault(step.position, None)
            if origin in of_interest and si < 4:
                snapshots.append({
                    "figure": names[si],
                    "origin": list(origin),
                    "world": world.cells.tolist(),
                    "presentation": presentation.describe(),
                    **network.snapshot(),
                })

    shape_sel, position_sel = two_way_selectivity(responses)
    separation = figure_separation(responses)
    population, distances = population_separation(responses)
    labels = network.column_labels()
    active = int((shape_sel + position_sel > 1e-9).sum())

    result = {
        "summary": {
            "overall": {
                "columns": len(labels),
                "shape_selectivity_max": float(shape_sel.max(initial=0.0)),
                "shape_selectivity_mean": float(shape_sel.mean()) if labels else 0.0,
                "position_selectivity_max": float(position_sel.max(initial=0.0)),
                "position_selectivity_mean": float(position_sel.mean()) if labels else 0.0,
                "separation_max": float(separation.max(initial=0.0)),
                "separation_mean": float(separation.mean()) if labels else 0.0,
                "population_separation": population,
                "active_columns": active,
                "silent_columns": len(labels) - active,
            },
            "by_level": summarise_by_level(
                shape_sel, position_sel, labels, ("shape", "position"), separation,
                responses, names,
            ),
            "presentation": {
                "figures": names,
                "origins": len(origins),
                "stops_per_figure": len(shapes[0].parts),
                "parts_per_figure": len(shapes[0].parts),
                "relations_per_figure": len(shapes[0].parts) - 1,
                "visiting_order": order,
            },
            "figure_distances": {
                f"{names[a]} vs {names[b]}": float(distances[a, b])
                for a in range(len(names))
                for b in range(a + 1, len(names))
            },
        },
        "responses": responses,
        "shape_selectivity": shape_sel,
        "position_selectivity": position_sel,
        "separation": separation,
        "labels": labels,
        "snapshots": snapshots,
        "connectivity": network.describe(),
        "palette": list(PALETTE),
        "stimuli": {"figures": names, "origins": len(origins)},
        "parameters": p,
    }
    result["summary"]["schema"] = _schema_report(network, world, p)
    result["summary"]["index"] = _index_report(network, stops, p)
    return result


def _schema_report(network: Network, world: World, p: dict) -> dict:
    """Separation and path consistency, measured rather than asserted (§3.2)."""
    if network.schema is None:
        return {}
    schema = network.schema
    size = world.size
    states = {(i, j): schema.at((i, j), p) for i in range(size) for j in range(size)}
    distinct = {tuple(np.round(state, 6)) for state in states.values()}

    # Reach one position two ways: the states must agree, or a memory stored there
    # becomes unreachable from a new direction.
    worst = 0.0
    for target in ((1, 2), (2, 3), (3, 1)):
        a = schema.advance(schema.advance(schema.origin(), (target[0], 0), p), (0, target[1]), p)
        b = schema.advance(schema.advance(schema.origin(), (0, target[1]), p), (target[0], 0), p)
        worst = max(worst, float(np.abs(a - b).max()))

    return {
        "columns": schema.size,
        "periods": list(schema.periods),
        "capacity": schema.capacity,
        "positions_visited": size * size,
        "distinct_states": len(distinct),
        "path_consistency_error": worst,
    }


def _index_report(network: Network, stops: int, p: dict) -> dict:
    """Did the last presentation's bindings come back from a positional cue?"""
    if network.index is None:
        return {}
    index = network.index
    hits, bound = 0, 0
    for content, where in index.stored():
        if np.linalg.norm(content) <= 1e-12:
            continue                      # nothing was there to bind
        bound += 1
        recovered, _ = index.complete(schema_state=where)
        denominator = np.linalg.norm(content) * np.linalg.norm(recovered)
        if denominator > 1e-12 and content @ recovered / denominator > 0.9:
            hits += 1
    return {
        "entries": index.entries,
        "stops": index.entries,
        "bindings_with_content": bound,
        "total_stops_in_run": stops,
        "completion_accuracy": hits / bound if bound else 0.0,
    }


KINDS = {"structure_baseline": run_structure_baseline}


def execute(definition: dict, artifact_root: str | Path = "artifacts") -> Path:
    kind = definition.get("kind")
    if kind not in KINDS:
        raise KeyError(f"unknown experiment kind {kind!r}; declared: {sorted(KINDS)}")

    run_digest = digest(definition)
    started = datetime.now(timezone.utc)
    result = KINDS[kind](definition)
    finished = datetime.now(timezone.utc)

    number = str(definition.get("number", "000"))
    out = Path(artifact_root) / f"{number}-{started:%Y%m%dT%H%M%S}-{run_digest}"
    out.mkdir(parents=True, exist_ok=True)

    (out / "definition.json").write_text(json.dumps(definition, indent=2, sort_keys=True))
    (out / "manifest.json").write_text(json.dumps({
        "digest": run_digest,
        "number": number,
        "kind": kind,
        "name": definition.get("name", kind),
        "question": definition.get("question", ""),
        "started": started.isoformat(),
        "finished": finished.isoformat(),
        "seconds": (finished - started).total_seconds(),
        "stimuli": result["stimuli"],
        "parameters": result["parameters"],
    }, indent=2))
    (out / "summary.json").write_text(json.dumps(result["summary"], indent=2))
    (out / "snapshots.json").write_text(json.dumps(result["snapshots"]))
    (out / "connectivity.json").write_text(json.dumps(
        {"connectivity": result["connectivity"], "palette": result["palette"]}, indent=2
    ))
    np.savez_compressed(
        out / "responses.npz",
        responses=result["responses"],
        shape_selectivity=result["shape_selectivity"],
        position_selectivity=result["position_selectivity"],
        separation=result["separation"],
        labels=np.array(result["labels"]),
    )
    return out
