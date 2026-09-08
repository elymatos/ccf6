"""Running a declared experiment and writing its artifact.

An experiment is a file. Running it is a function from that file to an artifact
directory, so a run is reproducible, diffable and re-renderable without re-running.
Nothing meaningful is configured anywhere else — the UI may *generate* this file, but
it may not carry semantics the file does not.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ccf6 import params
from ccf6.metrics import summarise_by_level, two_way_selectivity
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
    arch = Architecture(**definition.get("architecture", {}))
    world = World(arch.world_size)
    colour_encoder = ENCODERS[definition.get("colour_encoder", "localist_colour")]
    if colour_encoder.__name__ == "PopulationColour":
        colour = colour_encoder(arch.n_colours, arch.colour_shape[0] * arch.colour_shape[1])
    else:
        colour = colour_encoder(arch.n_colours)
    thalamus = Thalamus(colour=colour, position=ENCODERS["localist_position"](arch.world_size))
    # The colour Space's Grid must hold exactly what the colour encoder produces.
    arch.colour_shape = (1, colour.size)
    network = Network(arch, thalamus)
    return network, world, params.resolve(definition.get("parameters"))


def run_colour_selectivity(definition: dict) -> dict:
    """Present every (colour, position) pair once and measure what responds to what.

    A factorial design on purpose: colour and position vary independently, so the
    variance decomposition can say which factor a Column follows. No learning happens
    — this measures the substrate.
    """
    network, world, p = build(definition)
    arch = network.arch
    ticks = int(definition.get("ticks", 30))
    colours = definition.get("colours") or list(range(1, arch.n_colours))
    positions = [(i, j) for i in range(arch.world_size) for j in range(arch.world_size)]

    responses = np.zeros((len(colours), len(positions), network.response_vector().size))
    snapshots = []
    # A central position and a corner one: the corner shows what the border does to
    # contrast, which is a real effect and easier to see than to describe.
    of_interest = [tuple(pos) for pos in definition.get("snapshot_positions", [[3, 3], [0, 0]])]

    for ci, colour in enumerate(colours):
        for pi, position in enumerate(positions):
            world.clear()
            world.place(colour, position)
            strength = float(world.contrast()[position])

            network.reset()
            for _ in range(ticks):
                network.step(colour, position, strength, p)

            responses[ci, pi] = network.response_vector()
            if position in of_interest and ci < 3:
                snapshots.append(
                    {
                        "colour": PALETTE[colour],
                        "colour_index": int(colour),
                        "position": list(position),
                        "contrast": strength,
                        "world": world.cells.tolist(),
                        "spaces": network.snapshot(),
                    }
                )

    colour_sel, position_sel = two_way_selectivity(responses)
    labels = network.column_labels()
    return {
        "summary": summarise_by_level(colour_sel, position_sel, labels),
        "responses": responses,
        "colour_selectivity": colour_sel,
        "position_selectivity": position_sel,
        "labels": labels,
        "snapshots": snapshots,
        "connectivity": network.describe(),
        "palette": list(PALETTE),
        "stimuli": {"colours": [PALETTE[c] for c in colours], "positions": len(positions)},
        "parameters": p,
    }


def run_position_representation(definition: dict) -> dict:
    """Can one Level hold all 64 World positions apart, with no two alike?

    Position is presented at every World position in turn and Level 1's output is
    recorded. Each position therefore yields a 64-element vector, and the question is
    whether those 64 vectors are distinct — whether the Level is a faithful code for
    position, or whether two different places produce the same activity and become
    indistinguishable to everything downstream.

    Colour is held constant throughout: this experiment asks about position alone.
    """
    network, world, p = build(definition)
    arch = network.arch
    ticks = int(definition.get("ticks", 250))
    colour = int(definition.get("colour", 1))
    level = network.position.levels[0]
    positions = [(i, j) for i in range(arch.world_size) for j in range(arch.world_size)]

    patterns = np.zeros((len(positions), level.n))
    records = []
    for index, position in enumerate(positions):
        world.clear()
        world.place(colour, position)
        strength = float(world.contrast()[position])

        network.reset()
        for _ in range(ticks):
            network.step(colour, position, strength, p)

        patterns[index] = level.l5
        records.append(
            {
                "position": list(position),
                "contrast": strength,
                "world": world.cells.tolist(),
                "level": level.grid("l5").tolist(),
                "peak": int(np.argmax(level.l5)),
                "peak_value": float(level.l5.max()),
            }
        )

    # Cosine similarity: two positions are indistinguishable if their patterns point
    # the same way, whatever their overall magnitude.
    norms = np.linalg.norm(patterns, axis=1, keepdims=True)
    unit = np.divide(patterns, norms, out=np.zeros_like(patterns), where=norms > 1e-12)
    similarity = unit @ unit.T
    off_diagonal = similarity - np.eye(len(positions)) * 2.0

    tolerance = float(definition.get("duplicate_tolerance", 0.999))
    duplicates = [
        {
            "a": list(positions[i]),
            "b": list(positions[j]),
            "similarity": float(similarity[i, j]),
        }
        for i, j in zip(*np.triu_indices(len(positions), k=1))
        if similarity[i, j] >= tolerance
    ]
    peaks = [record["peak"] for record in records]

    return {
        "summary": {
            "positions": len(positions),
            "distinct_patterns": int(len({tuple(np.round(row, 6)) for row in patterns})),
            "distinct_peaks": int(len(set(peaks))),
            "peak_is_a_bijection": bool(len(set(peaks)) == len(positions)),
            "duplicate_pairs": len(duplicates),
            "max_off_diagonal_similarity": float(off_diagonal.max()),
            "mean_off_diagonal_similarity": float(
                (similarity.sum() - np.trace(similarity)) / (len(positions) ** 2 - len(positions))
            ),
            "silent_positions": int((patterns.max(axis=1) <= p["activation_floor"] + 1e-9).sum()),
        },
        "records": records,
        "similarity": similarity.tolist(),
        "duplicates": duplicates,
        "responses": patterns[:, None, :],
        "colour_selectivity": np.zeros(level.n),
        "position_selectivity": np.zeros(level.n),
        "labels": network.column_labels(),
        "snapshots": [],
        "connectivity": network.describe(),
        "palette": list(PALETTE),
        "stimuli": {"colours": [PALETTE[colour]], "positions": len(positions)},
        "parameters": p,
    }


KINDS = {
    "colour_selectivity_baseline": run_colour_selectivity,
    "position_representation": run_position_representation,
}


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
    (out / "manifest.json").write_text(
        json.dumps(
            {
                "digest": run_digest,
                # The experiment's number, so a run can be located by the file that
                # produced it rather than by a timestamp.
                "number": str(definition.get("number", "—")),
                "kind": kind,
                "name": definition.get("name", kind),
                "started": started.isoformat(),
                "finished": finished.isoformat(),
                "seconds": (finished - started).total_seconds(),
                "stimuli": result["stimuli"],
                "parameters": result["parameters"],
            },
            indent=2,
        )
    )
    (out / "summary.json").write_text(json.dumps(result["summary"], indent=2))
    (out / "snapshots.json").write_text(json.dumps(result["snapshots"]))
    if "records" in result:
        (out / "positions.json").write_text(
            json.dumps(
                {
                    "records": result["records"],
                    "similarity": result["similarity"],
                    "duplicates": result["duplicates"],
                }
            )
        )
    (out / "connectivity.json").write_text(
        json.dumps({"connectivity": result["connectivity"], "palette": result["palette"]}, indent=2)
    )
    np.savez_compressed(
        out / "responses.npz",
        responses=result["responses"],
        colour_selectivity=result["colour_selectivity"],
        position_selectivity=result["position_selectivity"],
        labels=np.array(result["labels"]),
    )
    return out
