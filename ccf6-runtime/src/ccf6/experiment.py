"""Run declared NCL experiments and write inspectable artifacts."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np

from ccf6 import figures, params
from ccf6.domain import generate_domain
from ccf6.ego import Presentation
from ccf6.functional_acquisition import run_success_gated_acquisition
from ccf6.functional_network import Network as FunctionalNetwork
from ccf6.functional_presentation import PresentationProtocol
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


def run_zero_rest_network(definition: dict) -> dict:
    """Run one generated visual prototype through the normative Network."""
    if "seed" not in definition:
        raise ValueError("zero-rest Network experiments must declare a seed")
    if "network" not in definition:
        raise ValueError("zero-rest Network experiments must declare a Network")

    dataset = generate_domain(int(definition["seed"]))
    network = FunctionalNetwork(definition["network"])
    stimulus = definition.get("stimulus", {})
    if set(stimulus) != {"category_id", "population_id"}:
        raise ValueError("stimulus must declare category_id and population_id")
    category = next(
        (row for row in dataset["categories"] if row["id"] == stimulus["category_id"]),
        None,
    )
    if category is None:
        raise ValueError(f"unknown generated category {stimulus['category_id']!r}")
    population_id = stimulus["population_id"]
    if population_id not in network.populations:
        raise ValueError(f"unknown stimulus Population {population_id!r}")

    values_by_dimension = {
        row["id"]: row["values"] for row in dataset["visual_property_dimensions"]
    }
    sensory = np.zeros(sum(len(values) for values in values_by_dimension.values()))
    cursor = 0
    for property_ in category["prototype"]["properties"]:
        values = values_by_dimension[property_["dimension"]]
        sensory[cursor + values.index(property_["value"])] = 1.0
        cursor += len(values)
    if sensory.size != network.populations[population_id].columns:
        raise ValueError(
            f"{population_id!r} has {network.populations[population_id].columns} Columns "
            f"but generated visual activity has {sensory.size} values"
        )

    result = network.settle({population_id: sensory})
    activity_labels = np.asarray(network.column_labels())
    topology = network.topology_snapshot()
    return {
        "contract": "ncl-functional-web-v1",
        "dataset": dataset,
        "topology": topology,
        "topology_arrays": network.topology_arrays(),
        "activity_arrays": {
            "initial_activity": result.activity[0],
            "settled_activity": result.activity[-1],
            "trajectory": result.activity,
            "labels": activity_labels,
            "compartments": np.asarray(["Input", "Integration", "Output"]),
            "sensory": sensory,
        },
        "activity": {
            "labels": activity_labels.tolist(),
            "compartments": ["Input", "Integration", "Output"],
            "initial": result.activity[0].tolist(),
            "settled": result.activity[-1].tolist(),
            "trajectory": result.activity.tolist(),
            "sensory": sensory.tolist(),
        },
        "summary": {
            "network": {
                "populations": len(network.populations),
                "columns": len(activity_labels),
                "projections": len(network.projections),
                "connections": sum(
                    projection.sources.size for projection in network.projections
                ),
            },
            "stimulus": {
                "category_id": category["id"],
                "population_id": population_id,
                "properties": category["prototype"]["properties"],
                "active_features": int(np.count_nonzero(sensory)),
            },
            "settling": {
                "success": result.success,
                "ticks": result.ticks,
                "stable_ticks": result.stable_ticks,
                "epsilon": float(network.settling["epsilon"]),
                "max_ticks": int(network.settling["max_ticks"]),
                "final_delta": result.final_delta,
                "max_ticks_reached": result.max_ticks_reached,
            },
            "activity": {
                "input_max": float(result.activity[-1, :, 0].max(initial=0.0)),
                "integration_max": float(
                    result.activity[-1, :, 1].max(initial=0.0)
                ),
                "output_max": float(result.activity[-1, :, 2].max(initial=0.0)),
            },
        },
        "stimuli": {
            "categories": [category["id"]],
            "population": population_id,
        },
        "parameters": dict(network.dynamics),
    }


def run_coordinated_presentation(definition: dict) -> dict:
    """Run visual-first, ordered auditory Presentations and their controls."""
    if "seed" not in definition or "network" not in definition:
        raise ValueError("coordinated Presentation experiments require seed and Network")
    presentation = definition.get("presentation", {})
    if set(presentation) != {
        "visual_populations",
        "auditory_population",
        "controls",
    }:
        raise ValueError(
            "presentation must declare visual_populations, auditory_population, and controls"
        )
    required_controls = {
        "reversed",
        "permuted",
        "repeated_segment",
        "competing",
    }
    if (
        len(presentation["controls"]) != len(required_controls)
        or set(presentation["controls"]) != required_controls
    ):
        raise ValueError(f"presentation controls must be {sorted(required_controls)}")

    dataset = generate_domain(int(definition["seed"]))
    network = FunctionalNetwork(definition["network"])
    protocol = PresentationProtocol(
        network,
        dataset,
        visual_populations=presentation["visual_populations"],
        auditory_population=presentation["auditory_population"],
    )
    pseudowords = {row["id"]: row for row in dataset["pseudowords"]}
    records = []

    def append_record(
        category: dict,
        pseudoword_id: str,
        segments: list[str],
        condition: str,
        success_signal: float,
    ) -> None:
        records.append(
            protocol.run(
                presentation_id=f"presentation-{len(records) + 1}",
                category=category,
                pseudoword_id=pseudoword_id,
                segments=segments,
                condition=condition,
                success_signal=success_signal,
            )
        )

    for category in dataset["categories"]:
        pseudoword = pseudowords[category["pseudoword_id"]]
        append_record(category, pseudoword["id"], pseudoword["segments"], "correct", 1.0)
        for control in ("reversed", "permuted", "repeated_segment"):
            append_record(
                category,
                pseudoword["id"],
                pseudoword["controls"][control],
                control,
                0.0,
            )
        for competitor in dataset["pseudowords"]:
            if competitor["id"] != pseudoword["id"]:
                append_record(
                    category,
                    competitor["id"],
                    competitor["segments"],
                    f"competing:{competitor['id']}",
                    0.0,
                )

    labels = np.asarray(network.column_labels())
    visual_indices = np.asarray(
        [
            index
            for index, label in enumerate(labels)
            if any(
                label.startswith(f"{population_id}#")
                for population_id in presentation["visual_populations"].values()
            )
        ],
        dtype=np.int64,
    )
    retention_ratios = []
    continuity_passed = True
    reset_passed = True
    for record in records:
        reset_passed = reset_passed and bool(np.all(record.initial_activity == 0.0))
        visual_output = record.samples[0].settling.activity[-1, visual_indices, 2]
        visual_total = float(visual_output.sum())
        for previous, current in zip(record.samples, record.samples[1:]):
            continuity_passed = continuity_passed and bool(
                np.array_equal(
                    previous.settling.activity[-1],
                    current.settling.activity[0],
                )
            )
            retained = float(current.settling.activity[-1, visual_indices, 2].sum())
            retention_ratios.append(retained / visual_total if visual_total > 0.0 else 0.0)

    sequence_pair_count = 0
    distinct_trajectory_count = 0
    trajectory_distances = []
    for category in dataset["categories"]:
        sequence_trajectories = {}
        for record in records:
            if record.category_id != category["id"] or record.condition == "repeated_segment":
                continue
            sequence_trajectories.setdefault(
                record.segments,
                record.settled_states[1:, :, 2],
            )
        for (left_segments, left), (right_segments, right) in combinations(
            sequence_trajectories.items(), 2
        ):
            if sorted(left_segments) != sorted(right_segments):
                continue
            sequence_pair_count += 1
            trajectory_distances.append(float(np.linalg.norm(left - right)))
            distinct_trajectory_count += int(not np.allclose(left, right))

    chunks = [sample.settling.activity for record in records for sample in record.samples]
    offsets = [0]
    for chunk in chunks:
        offsets.append(offsets[-1] + len(chunk))
    condition_counts = Counter(
        record.condition.split(":", maxsplit=1)[0] for record in records
    )
    failures = sum(record.settling_failures for record in records)
    durations = np.stack([record.sample_durations for record in records])
    presentation_rows = [record.as_dict() for record in records]
    topology = network.topology_snapshot()
    return {
        "contract": "ncl-functional-web-v1",
        "dataset": dataset,
        "topology": topology,
        "topology_arrays": network.topology_arrays(),
        "presentations": presentation_rows,
        "activity_arrays": {
            "initial_activity": np.stack(
                [record.initial_activity for record in records]
            ),
            "settled_activity": np.stack(
                [record.settled_states for record in records]
            ),
            "sample_durations": durations,
            "sample_settled": np.asarray(
                [
                    [sample.settling.success for sample in record.samples]
                    for record in records
                ]
            ),
            "trajectory": np.concatenate(chunks),
            "trajectory_offsets": np.asarray(offsets, dtype=np.int64),
            "labels": labels,
            "compartments": np.asarray(["Input", "Integration", "Output"]),
            "presentation_ids": np.asarray([record.identifier for record in records]),
            "category_ids": np.asarray([record.category_id for record in records]),
            "pseudoword_ids": np.asarray(
                [record.pseudoword_id for record in records]
            ),
            "conditions": np.asarray([record.condition for record in records]),
            "sample_ids": np.asarray(
                [[sample.identifier for sample in record.samples] for record in records]
            ),
        },
        "activity": {
            "labels": labels.tolist(),
            "compartments": ["Input", "Integration", "Output"],
            "presentation_ids": [record.identifier for record in records],
            "settled_states": [record.settled_states.tolist() for record in records],
        },
        "summary": {
            "network": {
                "populations": len(network.populations),
                "population_ids": list(network.population_order),
                "columns": len(labels),
                "projections": len(network.projections),
            },
            "presentations": {
                "total": len(records),
                "samples": len(chunks),
                "by_condition": dict(condition_counts),
                "reset_at_boundaries": reset_passed,
                "state_continuity_between_samples": continuity_passed,
            },
            "persistence": {
                "minimum_visual_retention_ratio": min(retention_ratios, default=0.0),
            },
            "sequence_sensitivity": {
                "same_bag_sequence_pairs": sequence_pair_count,
                "distinct_trajectory_pairs": distinct_trajectory_count,
                "minimum_trajectory_distance": min(
                    trajectory_distances, default=0.0
                ),
                "passed": sequence_pair_count > 0
                and distinct_trajectory_count == sequence_pair_count,
            },
            "settling": {
                "failures": failures,
                "successful_samples": len(chunks) - failures,
                "duration_ticks_min": int(durations.min()),
                "duration_ticks_max": int(durations.max()),
                "duration_ticks_mean": float(durations.mean()),
            },
        },
        "stimuli": {
            "categories": [row["id"] for row in dataset["categories"]],
            "conditions": dict(condition_counts),
        },
        "parameters": dict(network.dynamics),
    }


KINDS = {
    "cardinal_recruitment": run_cardinal_recruitment,
    "synthetic_lexical_grounding": run_synthetic_lexical_grounding,
    "zero_rest_network": run_zero_rest_network,
    "coordinated_presentation": run_coordinated_presentation,
    "success_gated_learning": run_success_gated_acquisition,
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
    if "topology" in result:
        topology_files = [
            "dataset.json",
            "topology.npz",
            "topology.json",
        ]
        if "presentations" in result:
            topology_files.append("presentations.jsonl")
        if "learning" in result:
            topology_files.extend(["learning.npz", "learning.json"])
        topology_files.extend(["activity.npz", "activity.json"])
        files[2:2] = topology_files
    elif "dataset" in result:
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
    if "topology" in result:
        (output / "topology.json").write_text(
            json.dumps(result["topology"], indent=2)
        )
        np.savez_compressed(output / "topology.npz", **result["topology_arrays"])
        if "presentations" in result:
            (output / "presentations.jsonl").write_text(
                "".join(
                    json.dumps(row, separators=(",", ":")) + "\n"
                    for row in result["presentations"]
                )
            )
        if "learning" in result:
            np.savez_compressed(output / "learning.npz", **result["learning_arrays"])
            (output / "learning.json").write_text(
                json.dumps(result["learning"], separators=(",", ":"))
            )
        np.savez_compressed(output / "activity.npz", **result["activity_arrays"])
        (output / "activity.json").write_text(
            json.dumps(result["activity"], separators=(",", ":"))
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
