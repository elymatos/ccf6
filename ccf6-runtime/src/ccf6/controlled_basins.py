"""Matched experimental arms and frozen Target Basin observations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np

from ccf6.domain import generate_domain
from ccf6.functional_network import Network
from ccf6.functional_presentation import PresentationProtocol, PresentationRecord
from ccf6.target_basins import FrozenTargetBasins, TargetBasinObserver


ARM_IDS = ("trained", "untrained", "shuffled")


@dataclass
class ArmRun:
    identifier: str
    network: Network
    protocol: PresentationProtocol
    pairing: tuple[dict, ...]
    initial_ascending: np.ndarray
    initial_descending: np.ndarray
    initial_thresholds: np.ndarray
    acquisition_presentations: list[dict]
    frozen_basins: FrozenTargetBasins | None = None
    held_out_evaluations: list[dict] | None = None


def _json_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _array_digest(arrays: dict[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for name, values in sorted(arrays.items()):
        contiguous = np.ascontiguousarray(values)
        digest.update(name.encode())
        digest.update(str(contiguous.dtype).encode())
        digest.update(str(contiguous.shape).encode())
        digest.update(contiguous.tobytes())
    return digest.hexdigest()


def _projection_values(network: Network, attribute: str) -> np.ndarray:
    return np.concatenate(
        [getattr(projection, attribute) for projection in network.projections]
    )


def _population_values(network: Network, attribute: str) -> np.ndarray:
    return np.concatenate(
        [getattr(network.populations[name], attribute) for name in network.population_order]
    )


def _contributor_counts(network: Network) -> np.ndarray:
    return np.concatenate(
        [
            np.asarray(
                [
                    len(values)
                    for values in network.populations[name].contributing_presentations
                ],
                dtype=np.int64,
            )
            for name in network.population_order
        ]
    )


def _presentation_row(
    record: PresentationRecord,
    *,
    arm_id: str,
    phase: str,
    visual_instance_id: str,
) -> dict:
    return {
        "id": record.identifier,
        "arm_id": arm_id,
        "phase": phase,
        "condition": record.condition,
        "category_id": record.category_id,
        "pseudoword_id": record.pseudoword_id,
        "visual_instance_id": visual_instance_id,
        "success_signal": record.success_signal,
        "settling_failures": record.settling_failures,
        "samples": [
            {
                "number": sample.number,
                "kind": sample.kind,
                "id": sample.identifier,
                "duration_ticks": sample.settling.ticks,
                "settled": sample.settling.success,
            }
            for sample in record.samples
        ],
    }


def _validate_definition(definition: dict) -> None:
    for key in ("seed", "network", "presentation", "acquisition", "arms", "basins"):
        if key not in definition:
            raise ValueError(f"matched Target Basin experiment requires {key}")
    if set(definition["arms"]) != {"shuffled_pairing_rotation"}:
        raise ValueError("arms must declare shuffled_pairing_rotation")
    rotation = definition["arms"]["shuffled_pairing_rotation"]
    if isinstance(rotation, bool) or not isinstance(rotation, int) or rotation < 1:
        raise ValueError("shuffled pairing rotation must be a positive integer")
    if set(definition["basins"]) != {
        "minimum_scale",
        "maximum_column_standard_deviation",
        "minimum_reliable_columns",
        "margin_quantile",
    }:
        raise ValueError(
            "basins must declare scale, reliability, and margin parameters"
        )


def _train_arm(
    arm_id: str,
    definition: dict,
    dataset: dict,
    categories: list[dict],
    pairing: tuple[dict, ...],
) -> ArmRun:
    network = Network(definition["network"])
    presentation = definition["presentation"]
    protocol = PresentationProtocol(
        network,
        dataset,
        visual_populations=presentation["visual_populations"],
        auditory_population=presentation["auditory_population"],
    )
    initial_ascending = _projection_values(network, "ascending_weights").copy()
    initial_descending = _projection_values(network, "descending_weights").copy()
    initial_thresholds = _population_values(network, "thresholds").copy()
    if arm_id == "untrained":
        network.freeze_adaptation()
    epochs = definition["acquisition"]["epochs"]
    mismatch_rotation = definition["acquisition"]["mismatch_rotation"]
    rows = []
    for epoch in range(1, epochs + 1):
        for index, category in enumerate(categories):
            acquisition_instances = category["splits"]["acquisition"]
            visual_instance = acquisition_instances[
                (epoch - 1) % len(acquisition_instances)
            ]
            conditions = (
                ("correct", pairing[index], 1.0),
                (
                    "mismatched",
                    pairing[(index + mismatch_rotation) % len(categories)],
                    0.0,
                ),
            )
            for condition, pseudoword, signal in conditions:
                identifier = f"{arm_id}-epoch-{epoch}-{condition}-{category['id']}"
                record = protocol.run(
                    presentation_id=identifier,
                    category=category,
                    pseudoword_id=pseudoword["id"],
                    segments=pseudoword["segments"],
                    condition=condition,
                    success_signal=signal,
                    visual_instance=visual_instance,
                )
                if record.settling_failures:
                    raise RuntimeError(
                        f"{identifier}: cannot train from a settling failure"
                    )
                network.apply_success_signal(signal, identifier)
                rows.append(
                    _presentation_row(
                        record,
                        arm_id=arm_id,
                        phase="acquisition",
                        visual_instance_id=visual_instance["id"],
                    )
                )
    network.freeze_adaptation()
    return ArmRun(
        identifier=arm_id,
        network=network,
        protocol=protocol,
        pairing=pairing,
        initial_ascending=initial_ascending,
        initial_descending=initial_descending,
        initial_thresholds=initial_thresholds,
        acquisition_presentations=rows,
    )


def _fit_and_evaluate(
    arm: ArmRun,
    categories: list[dict],
    observer: TargetBasinObserver,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict], list[dict]]:
    observations = {}
    instance_ids = {}
    basin_rows = []
    basin_output = []
    for index, category in enumerate(categories):
        category_output = []
        category_ids = []
        pseudoword = arm.pairing[index]
        for instance in category["splits"]["basin_estimation"]:
            identifier = f"{arm.identifier}-basin-{instance['id']}"
            record = arm.protocol.run(
                presentation_id=identifier,
                category=category,
                pseudoword_id=pseudoword["id"],
                segments=pseudoword["segments"],
                condition="basin_estimation",
                success_signal=0.0,
                visual_instance=instance,
            )
            if record.settling_failures:
                raise RuntimeError(f"{identifier}: Target Basin failed to settle")
            category_output.append(record.settled_states[-1, :, 2])
            category_ids.append(instance["id"])
            basin_rows.append(
                _presentation_row(
                    record,
                    arm_id=arm.identifier,
                    phase="basin_estimation",
                    visual_instance_id=instance["id"],
                )
            )
        observations[category["id"]] = np.stack(category_output)
        instance_ids[category["id"]] = tuple(category_ids)
        basin_output.append(np.stack(category_output))
    frozen = observer.fit(
        observations,
        column_labels=tuple(arm.network.column_labels()),
        instance_ids=instance_ids,
    )
    arm.frozen_basins = frozen

    held_initial = []
    held_settled = []
    held_rows = []
    evaluations = []
    for index, category in enumerate(categories):
        category_initial = []
        category_settled = []
        pseudoword = arm.pairing[index]
        for instance in category["splits"]["final_held_out"]:
            identifier = f"{arm.identifier}-held-out-{instance['id']}"
            record = arm.protocol.run(
                presentation_id=identifier,
                category=category,
                pseudoword_id=pseudoword["id"],
                segments=pseudoword["segments"],
                condition="final_held_out",
                success_signal=0.0,
                visual_instance=instance,
            )
            if record.settling_failures:
                raise RuntimeError(f"{identifier}: held-out evaluation failed to settle")
            initial = record.samples[0].settling.activity[0, :, 2]
            settled = record.settled_states[-1, :, 2]
            evaluation = frozen.evaluate(
                expected_category=category["id"],
                initial_activity=initial,
                settled_activity=settled,
            ).as_dict()
            evaluation.update(
                {
                    "id": identifier,
                    "visual_instance_id": instance["id"],
                    "prototype_distance": instance["prototype_distance"],
                }
            )
            evaluations.append(evaluation)
            category_initial.append(initial)
            category_settled.append(settled)
            held_rows.append(
                _presentation_row(
                    record,
                    arm_id=arm.identifier,
                    phase="final_held_out",
                    visual_instance_id=instance["id"],
                )
            )
        held_initial.append(np.stack(category_initial))
        held_settled.append(np.stack(category_settled))
    arm.held_out_evaluations = evaluations
    return (
        np.stack(basin_output),
        np.stack(held_initial),
        np.stack(held_settled),
        basin_rows,
        held_rows,
    )


def run_matched_target_basins(definition: dict) -> dict:
    """Run matched arms, freeze adaptation, fit basins, then evaluate held-out data."""
    _validate_definition(definition)
    dataset = generate_domain(int(definition["seed"]))
    categories = dataset["categories"]
    pseudowords = {row["id"]: row for row in dataset["pseudowords"]}
    canonical = tuple(pseudowords[row["pseudoword_id"]] for row in categories)
    rotation = definition["arms"]["shuffled_pairing_rotation"] % len(categories)
    if rotation == 0:
        raise ValueError("shuffled pairing rotation must change every pairing")
    shuffled = canonical[rotation:] + canonical[:rotation]
    pairings = {
        "trained": canonical,
        "untrained": canonical,
        "shuffled": shuffled,
    }
    arms = [
        _train_arm(arm_id, definition, dataset, categories, pairings[arm_id])
        for arm_id in ARM_IDS
    ]
    observer = TargetBasinObserver(**definition["basins"])
    basin_activity = []
    held_initial = []
    held_settled = []
    presentation_rows = []
    for arm in arms:
        basin, initial, settled, basin_rows, held_rows = _fit_and_evaluate(
            arm,
            categories,
            observer,
        )
        basin_activity.append(basin)
        held_initial.append(initial)
        held_settled.append(settled)
        presentation_rows.extend(arm.acquisition_presentations)
        presentation_rows.extend(basin_rows)
        presentation_rows.extend(held_rows)

    first_topology = Network(definition["network"])
    topology = first_topology.topology_snapshot()
    topology_arrays = {
        name: values.copy() for name, values in first_topology.topology_arrays().items()
    }
    dataset_digest = _json_digest(dataset)
    split_digest = _json_digest(
        {
            category["id"]: category["splits"]
            for category in categories
        }
    )
    topology_digest = _array_digest(topology_arrays)
    parameter_digest = _json_digest(
        {
            "network": definition["network"],
            "presentation": definition["presentation"],
            "acquisition": definition["acquisition"],
            "basins": definition["basins"],
        }
    )
    initial_ascending = np.stack([arm.initial_ascending for arm in arms])
    initial_descending = np.stack([arm.initial_descending for arm in arms])
    initial_thresholds = np.stack([arm.initial_thresholds for arm in arms])
    final_ascending = np.stack(
        [_projection_values(arm.network, "ascending_weights") for arm in arms]
    )
    final_descending = np.stack(
        [_projection_values(arm.network, "descending_weights") for arm in arms]
    )
    final_thresholds = np.stack(
        [_population_values(arm.network, "thresholds") for arm in arms]
    )
    final_average = np.stack(
        [_population_values(arm.network, "activity_average") for arm in arms]
    )
    final_entrenchment = np.stack(
        [_population_values(arm.network, "entrenchment") for arm in arms]
    )
    final_contributors = np.stack([_contributor_counts(arm.network) for arm in arms])
    final_recruited = np.stack(
        [
            np.concatenate(list(arm.network.recruited_columns().values()))
            for arm in arms
        ]
    )
    pairing_ids = np.asarray(
        [[pseudoword["id"] for pseudoword in arm.pairing] for arm in arms]
    )
    arm_rows = []
    for index, arm in enumerate(arms):
        durable_change = not (
            np.array_equal(initial_ascending[index], final_ascending[index])
            and np.array_equal(initial_descending[index], final_descending[index])
            and np.array_equal(initial_thresholds[index], final_thresholds[index])
            and np.all(final_average[index] == 0.0)
            and np.all(final_entrenchment[index] == 0.0)
        )
        arm_rows.append(
            {
                "id": arm.identifier,
                "seed": definition["seed"],
                "dataset_digest": dataset_digest,
                "split_digest": split_digest,
                "initial_topology_digest": topology_digest,
                "parameter_digest": parameter_digest,
                "category_pairings": {
                    category["id"]: pseudoword["id"]
                    for category, pseudoword in zip(
                        categories,
                        arm.pairing,
                        strict=True,
                    )
                },
                "control_difference": (
                    ["category_pseudoword_pairing"]
                    if arm.identifier == "shuffled"
                    else (
                        ["durable_learning_disabled"]
                        if arm.identifier == "untrained"
                        else []
                    )
                ),
                "acquisition_presentations": len(arm.acquisition_presentations),
                "durable_change": durable_change,
                "final_durable_digest": _array_digest(
                    {
                        "ascending": final_ascending[index],
                        "descending": final_descending[index],
                        "thresholds": final_thresholds[index],
                        "average": final_average[index],
                        "entrenchment": final_entrenchment[index],
                        "contributors": final_contributors[index],
                    }
                ),
            }
        )
    basins = {
        "parameters": dict(definition["basins"]),
        "arms": {
            arm.identifier: {
                "frozen": arm.frozen_basins.as_dict(),
                "held_out_evaluations": arm.held_out_evaluations,
            }
            for arm in arms
        },
    }
    basin_array = np.stack(basin_activity)
    held_initial_array = np.stack(held_initial)
    held_settled_array = np.stack(held_settled)
    held_success = {
        arm.identifier: sum(
            evaluation["correct_basin"]
            for evaluation in arm.held_out_evaluations
        )
        for arm in arms
    }
    matched_initial = bool(
        np.all(initial_ascending == initial_ascending[0])
        and np.all(initial_descending == initial_descending[0])
        and np.all(initial_thresholds == initial_thresholds[0])
    )
    return {
        "contract": "ncl-functional-web-v1",
        "dataset": dataset,
        "topology": topology,
        "topology_arrays": topology_arrays,
        "arms": {
            "shared": {
                "seed": definition["seed"],
                "dataset_digest": dataset_digest,
                "split_digest": split_digest,
                "initial_topology_digest": topology_digest,
                "parameter_digest": parameter_digest,
            },
            "arms": arm_rows,
        },
        "arm_arrays": {
            "arm_ids": np.asarray(ARM_IDS),
            "category_ids": np.asarray([category["id"] for category in categories]),
            "pairing_pseudoword_ids": pairing_ids,
            "initial_ascending_weights": initial_ascending,
            "initial_descending_weights": initial_descending,
            "initial_thresholds": initial_thresholds,
            "final_ascending_weights": final_ascending,
            "final_descending_weights": final_descending,
            "final_thresholds": final_thresholds,
            "final_activity_average": final_average,
            "final_entrenchment": final_entrenchment,
            "final_contributor_counts": final_contributors,
            "final_recruited": final_recruited,
        },
        "basins": basins,
        "presentations": presentation_rows,
        "activity_arrays": {
            "arm_ids": np.asarray(ARM_IDS),
            "category_ids": np.asarray([category["id"] for category in categories]),
            "column_labels": np.asarray(first_topology.column_labels()),
            "basin_settled_output": basin_array,
            "held_out_initial_output": held_initial_array,
            "held_out_settled_output": held_settled_array,
        },
        "activity": {
            "arm_ids": list(ARM_IDS),
            "category_ids": [category["id"] for category in categories],
            "column_labels": first_topology.column_labels(),
            "basin_shape": list(basin_array.shape),
            "held_out_shape": list(held_settled_array.shape),
        },
        "summary": {
            "arms": {
                "count": len(arms),
                "matched_initial_conditions": matched_initial,
                "untrained_durable_change": arm_rows[1]["durable_change"],
                "shuffled_difference": arm_rows[2]["control_difference"],
            },
            "basins": {
                "categories_per_arm": len(categories),
                "estimation_instances_per_category": 4,
                "minimum_scale": definition["basins"]["minimum_scale"],
                "held_out_used_for_fit": False,
            },
            "held_out": {
                "instances_per_category": 4,
                "correct_basin_by_arm": held_success,
                "total_by_arm": {
                    arm.identifier: len(arm.held_out_evaluations) for arm in arms
                },
            },
            "settling": {
                "failures": sum(
                    row["settling_failures"] for row in presentation_rows
                ),
            },
        },
        "stimuli": {
            "categories": [category["id"] for category in categories],
            "arms": list(ARM_IDS),
        },
        "parameters": {
            **definition["network"]["dynamics"],
            **definition["network"]["plasticity"],
            **definition["network"]["adaptation"],
            **definition["basins"],
        },
    }
