"""Run declared NCL experiments and write inspectable artifacts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ccf6 import figures, params
from ccf6.domain import generate_domain
from ccf6.ego import Presentation
from ccf6.metrics import (
    conjunction_selectivity,
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
        import yaml

        return yaml.safe_load(text)
    return json.loads(text)


def digest(definition: dict) -> str:
    canonical = json.dumps(definition, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def build(definition: dict) -> tuple[Network, World, dict]:
    architecture = Architecture(**definition.get("architecture", {}))
    colour_kind = definition.get("colour_encoder", "population_colour")
    colour_encoder = ENCODERS[colour_kind]
    colour = (
        colour_encoder(architecture.n_colours, architecture.n_colours * 8)
        if colour_kind == "population_colour"
        else colour_encoder(architecture.n_colours)
    )
    available = {
        "colour": colour,
        "shape": ENCODERS["local_shape"](),
    }
    sensory_names = {
        name
        for name, declaration in architecture.populations.items()
        if declaration["role"] == "sensory"
    }
    missing = sensory_names - available.keys()
    if missing:
        raise ValueError(f"no sensory adapter available for {sorted(missing)}")
    thalamus = Thalamus({name: available[name] for name in sensory_names})
    return (
        Network(architecture, thalamus),
        World(architecture.world_size),
        params.resolve(definition.get("parameters")),
    )


def _signals(world: World, radius: int, channels: set[str] | None = None):
    padded = world.foreground(radius)
    enabled = channels or {"shape", "colour"}

    def at(sample):
        row, column = sample.position
        values = {
            "colour": sample.colour,
            "shape": padded[
                row : row + 2 * radius + 1,
                column : column + 2 * radius + 1,
            ],
        }
        return {name: value for name, value in values.items() if name in enabled}

    return at


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = np.linalg.norm(left) * np.linalg.norm(right)
    return float(left @ right / denominator) if denominator > 1e-12 else 0.0


def run_cardinal_recruitment(definition: dict) -> dict:
    """Test convergence, recruitment, partial recognition, and reciprocal completion."""
    network, world, parameters = build(definition)
    architecture = network.architecture
    ticks = int(definition.get("ticks", 80))
    order = definition.get("visiting_order", "raster")
    names = definition.get("figures", sorted(figures.FIGURES))
    base_figures = figures.named(names)
    colours = [int(colour) for colour in definition.get("colours", figures.COLOURS)]
    stimuli = [
        [figures.in_colour(shape, colour) for colour in colours]
        for shape in base_figures
    ]
    shape_encoder = network.thalamus.encoders["shape"]
    radius = shape_encoder.radius

    origins = [
        (row, column)
        for row in range(architecture.world_size)
        for column in range(architecture.world_size)
        if all(world.fits(shape, (row, column)) for shape in base_figures)
    ]
    limit = definition.get("max_origins")
    if limit:
        stride = max(1, len(origins) // int(limit))
        origins = origins[::stride][: int(limit)]
    if not origins:
        raise ValueError("no World position holds every figure; enlarge the World")

    epochs = int(definition.get("epochs", 0)) if network.rule is not None else 0
    for _ in range(epochs):
        for shape_row in stimuli:
            for shape in shape_row:
                for origin in origins:
                    world.clear()
                    world.place_object(shape, origin)
                    network.reset()
                    network.traverse(
                        Presentation.of_object(world, shape, origin, order),
                        _signals(world, radius),
                        ticks,
                        parameters,
                    )

    recruitment = network.recruitment_report() if epochs else {}
    cardinal_candidates = network.cardinal_candidates()
    network.rule = None

    width = network.response_vector().size
    responses = np.zeros((len(base_figures), len(colours), len(origins), width))
    traces = []
    snapshots = []
    completion = {"shape_cue": [], "colour_cue": []}

    for shape_index, shape_row in enumerate(stimuli):
        for colour_index, shape in enumerate(shape_row):
            for origin_index, origin in enumerate(origins):
                world.clear()
                world.place_object(shape, origin)
                presentation = Presentation.of_object(world, shape, origin, order)

                network.reset()
                traversal = network.traverse(
                    presentation, _signals(world, radius), ticks, parameters
                )
                responses[shape_index, colour_index, origin_index] = traversal.mean
                traces.append(traversal.responses)
                full_concept = network.population_output("concept", parameters)
                full_shape = network.population_output("shape", parameters)
                full_colour = network.population_output("colour", parameters)

                network.reset()
                network.traverse(
                    presentation,
                    _signals(world, radius, {"shape"}),
                    ticks,
                    parameters,
                )
                completion["shape_cue"].append(
                    {
                        "concept": _cosine(
                            full_concept,
                            network.population_output("concept", parameters),
                        ),
                        "reinstated_colour": _cosine(
                            full_colour,
                            network.population_output("colour", parameters),
                        ),
                    }
                )

                network.reset()
                network.traverse(
                    presentation,
                    _signals(world, radius, {"colour"}),
                    ticks,
                    parameters,
                )
                completion["colour_cue"].append(
                    {
                        "concept": _cosine(
                            full_concept,
                            network.population_output("concept", parameters),
                        ),
                        "reinstated_shape": _cosine(
                            full_shape,
                            network.population_output("shape", parameters),
                        ),
                    }
                )

                if origin_index == 0 and colour_index == 0:
                    snapshots.append(
                        {
                            "figure": names[shape_index],
                            "colour": colours[colour_index],
                            "origin": list(origin),
                            "world": world.cells.tolist(),
                            "presentation": presentation.describe(),
                            "network": network.snapshot(),
                        }
                    )

    by_shape = responses.mean(axis=1)
    by_colour = responses.mean(axis=0)
    by_conjunction = responses.reshape(
        len(base_figures) * len(colours), len(origins), width
    )
    factorial = responses.mean(axis=2)
    shape_selectivity, colour_selectivity = two_way_selectivity(factorial)
    conjunction = conjunction_selectivity(factorial)
    separation = figure_separation(by_shape)
    population, distances = population_separation(by_conjunction)
    labels = network.column_labels()
    stimulus_names = [
        f"{names[shape_index]}/{colours[colour_index]}"
        for shape_index in range(len(names))
        for colour_index in range(len(colours))
    ]
    trace = np.stack(traces).reshape(
        len(base_figures), len(colours), len(origins), -1, width
    )

    def average(key: str, field: str) -> float:
        values = [row[field] for row in completion[key]]
        return float(np.mean(values)) if values else 0.0

    return {
        "summary": {
            "overall": {
                "columns": len(labels),
                "shape_selectivity_max": float(shape_selectivity.max(initial=0.0)),
                "colour_selectivity_max": float(colour_selectivity.max(initial=0.0)),
                "conjunction_selectivity_max": float(conjunction.max(initial=0.0)),
                "figure_separation_max": float(separation.max(initial=0.0)),
                "population_separation": population,
            },
            "recruitment": {
                "epochs": epochs,
                "by_level": recruitment,
                "cardinal_candidates": cardinal_candidates,
            },
            "completion": {
                "shape_cue_concept_similarity": average("shape_cue", "concept"),
                "shape_cue_reinstated_colour": average(
                    "shape_cue", "reinstated_colour"
                ),
                "colour_cue_concept_similarity": average("colour_cue", "concept"),
                "colour_cue_reinstated_shape": average(
                    "colour_cue", "reinstated_shape"
                ),
            },
            "presentation": {
                "figures": names,
                "colours": colours,
                "origins": len(origins),
                "samples_per_figure": len(base_figures[0].parts),
                "visiting_order": order,
            },
            "by_level": summarise_by_level(
                shape_selectivity,
                colour_selectivity,
                labels,
                ("shape", "colour"),
                separation,
                by_conjunction,
                stimulus_names,
                trace.reshape(len(stimulus_names), len(origins), -1, width),
                conjunction=conjunction,
            ),
            "distances": {
                f"{stimulus_names[left]} vs {stimulus_names[right]}": float(
                    distances[left, right]
                )
                for left in range(len(stimulus_names))
                for right in range(left + 1, len(stimulus_names))
            },
        },
        "responses": responses,
        "trace": trace[:, :, :1],
        "shape_selectivity": shape_selectivity,
        "colour_selectivity": colour_selectivity,
        "conjunction_selectivity": conjunction,
        "separation": separation,
        "labels": labels,
        "snapshots": snapshots,
        "connectivity": network.describe(),
        "palette": list(PALETTE),
        "stimuli": {"figures": names, "origins": len(origins)},
        "parameters": parameters,
    }


def run_synthetic_lexical_grounding(definition: dict) -> dict:
    """Generate the validated domain consumed by later Functional Web experiments."""
    if "seed" not in definition:
        raise ValueError("synthetic lexical-grounding experiments must declare a seed")

    dataset = generate_domain(int(definition["seed"]))

    pairing_counts = {
        kind: sum(pairing["kind"] == kind for pairing in dataset["pairings"])
        for kind in ("correct", "mismatched")
    }
    return {
        "contract": "ncl-functional-web-v1",
        "dataset": dataset,
        "summary": {
            "domain": {
                "categories": len(dataset["categories"]),
                "visual_property_dimensions": len(
                    dataset["visual_property_dimensions"]
                ),
                "instances_per_category": {
                    split: len(dataset["categories"][0]["splits"][split])
                    for split in (
                        "acquisition",
                        "basin_estimation",
                        "final_held_out",
                    )
                },
                "pseudowords": len(dataset["pseudowords"]),
                "auditory_segments": len(dataset["auditory_segments"]),
                "auditory_features": len(dataset["auditory_features"]),
                "pairings": {"total": len(dataset["pairings"]), **pairing_counts},
                "constraints": {
                    "passed": sum(
                        check["passed"] for check in dataset["constraint_checks"]
                    ),
                    "total": len(dataset["constraint_checks"]),
                },
            }
        },
        "stimuli": {"categories": [row["id"] for row in dataset["categories"]]},
        "parameters": {},
    }


KINDS = {
    "cardinal_recruitment": run_cardinal_recruitment,
    "synthetic_lexical_grounding": run_synthetic_lexical_grounding,
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
    output = Path(artifact_root) / f"{number}-{started:%Y%m%dT%H%M%S}-{run_digest}"
    output.mkdir(parents=True, exist_ok=True)

    (output / "definition.json").write_text(
        json.dumps(definition, indent=2, sort_keys=True)
    )
    files = ["definition.json", "manifest.json", "summary.json"]
    if "dataset" in result:
        files.insert(2, "dataset.json")
    else:
        files.extend(["connectivity.json", "snapshots.json", "responses.npz"])

    (output / "manifest.json").write_text(
        json.dumps(
            {
                "contract": result.get("contract", "ncl-column-network-v1"),
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
                "files": files,
            },
            indent=2,
        )
    )
    if "dataset" in result:
        (output / "dataset.json").write_text(
            json.dumps(result["dataset"], indent=2)
        )
    (output / "summary.json").write_text(
        json.dumps(result["summary"], indent=2)
    )
    if "connectivity" in result:
        (output / "snapshots.json").write_text(json.dumps(result["snapshots"]))
        (output / "connectivity.json").write_text(
            json.dumps(
                {
                    "connectivity": result["connectivity"],
                    "palette": result["palette"],
                },
                indent=2,
            )
        )
        np.savez_compressed(
            output / "responses.npz",
            responses=result["responses"],
            trace=result["trace"],
            shape_selectivity=result["shape_selectivity"],
            colour_selectivity=result["colour_selectivity"],
            conjunction_selectivity=result["conjunction_selectivity"],
            separation=result["separation"],
            labels=np.array(result["labels"]),
        )
    return output
