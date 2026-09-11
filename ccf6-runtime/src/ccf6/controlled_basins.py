"""Matched experimental arms and frozen Target Basin observations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np

from ccf6.cardinals import CardinalObserver
from ccf6.completion_evaluation import OrderedTrajectoryObserver
from ccf6.domain import generate_domain
from ccf6.functional_network import LearningResult, Network
from ccf6.functional_presentation import PresentationProtocol, PresentationRecord
from ccf6.functional_webs import (
    FunctionalWebObserver,
    build_functional_web_evidence,
)
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
    learning_results: list[LearningResult]
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


def _learning_values(
    result: LearningResult,
    collection: str,
    attribute: str,
) -> np.ndarray:
    return np.concatenate(
        [getattr(value, attribute) for value in getattr(result, collection)]
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
    learning_results = []
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
                learning_results.append(
                    network.apply_success_signal(signal, identifier)
                )
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
        learning_results=learning_results,
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


def _durable_state(network: Network) -> dict[str, np.ndarray]:
    return {
        "ascending_weights": _projection_values(network, "ascending_weights").copy(),
        "descending_weights": _projection_values(network, "descending_weights").copy(),
        "thresholds": _population_values(network, "thresholds").copy(),
        "activity_average": _population_values(network, "activity_average").copy(),
        "entrenchment": _population_values(network, "entrenchment").copy(),
        "contributor_counts": _contributor_counts(network),
    }


def _output_trajectory(
    record: PresentationRecord,
    column_indices: np.ndarray,
    *,
    auditory_only: bool,
) -> np.ndarray:
    samples = [
        sample
        for sample in record.samples
        if not auditory_only or sample.kind == "auditory"
    ]
    chunks = []
    for index, sample in enumerate(samples):
        activity = sample.settling.activity[:, column_indices, 2]
        chunks.append(activity if index == 0 else activity[1:])
    return np.concatenate(chunks)


def _completion_evidence(
    definition: dict,
    dataset: dict,
    categories: list[dict],
    arms: list[ArmRun],
) -> tuple[dict, dict[str, np.ndarray], list[dict], dict]:
    declaration = definition["completion"]
    required_conditions = {
        "full",
        "visual_only",
        "pseudoword_only",
        "partial_visual",
        "atypical_held_out",
    }
    if set(declaration) != {
        "conditions",
        "partial_visual_dimensions",
        "atypical_selection",
        "trajectory_sample_points",
        "trajectory_populations",
    }:
        raise ValueError("completion must declare cue and trajectory parameters")
    if set(declaration["conditions"]) != required_conditions or len(
        declaration["conditions"]
    ) != len(required_conditions):
        raise ValueError(f"completion conditions must be {sorted(required_conditions)}")
    if declaration["atypical_selection"] != "maximum_prototype_distance":
        raise ValueError("atypical held-out selection must use prototype distance")
    visual_dimensions = {row["id"] for row in dataset["visual_property_dimensions"]}
    partial_dimensions = tuple(declaration["partial_visual_dimensions"])
    if not partial_dimensions or not set(partial_dimensions) < visual_dimensions:
        raise ValueError("partial visual dimensions must be a non-empty proper subset")
    trajectory_observer = OrderedTrajectoryObserver(
        sample_points=declaration["trajectory_sample_points"]
    )
    all_pseudowords = dataset["pseudowords"]
    condition_order = tuple(declaration["conditions"])
    completion_initial = []
    completion_settled = []
    completion_success = []
    lexical_correct = []
    lexical_controls = []
    lexical_control_labels = []
    lexical_visual_trajectories = []
    lexical_correct_trajectories = []
    lexical_control_trajectories = []
    presentation_rows = []
    arm_evidence = {}
    durable_changes = 0
    settling_failures = 0

    for arm in arms:
        before = _durable_state(arm.network)
        labels = arm.network.column_labels()
        trajectory_indices = np.asarray(
            [
                index
                for index, label in enumerate(labels)
                if any(
                    label.startswith(f"{population_id}#")
                    for population_id in declaration["trajectory_populations"]
                )
            ],
            dtype=np.int64,
        )
        if trajectory_indices.size == 0:
            raise ValueError("trajectory Populations select no Columns")
        condition_records: dict[str, list[PresentationRecord]] = {
            condition: [] for condition in condition_order
        }
        condition_rows = {condition: [] for condition in condition_order}
        arm_initial = []
        arm_settled = []
        arm_success = []
        for condition in condition_order:
            condition_initial = []
            condition_settled = []
            condition_success = []
            for index, category in enumerate(categories):
                pseudoword = arm.pairing[index]
                prototype = category["prototype"]["properties"]
                visual_properties = prototype
                visual_identifier = category["id"]
                segments: tuple[str, ...] | list[str] = pseudoword["segments"]
                if condition == "visual_only":
                    segments = ()
                elif condition == "pseudoword_only":
                    visual_properties = None
                    visual_identifier = "none"
                elif condition == "partial_visual":
                    visual_properties = [
                        property_
                        for property_ in prototype
                        if property_["dimension"] in partial_dimensions
                    ]
                    segments = ()
                elif condition == "atypical_held_out":
                    atypical = max(
                        category["splits"]["final_held_out"],
                        key=lambda row: (row["prototype_distance"], row["id"]),
                    )
                    visual_properties = atypical["properties"]
                    visual_identifier = atypical["id"]
                identifier = f"{arm.identifier}-{condition}-{category['id']}"
                record = arm.protocol.run_cue(
                    presentation_id=identifier,
                    category=category,
                    pseudoword_id=pseudoword["id"],
                    visual_properties=visual_properties,
                    visual_identifier=visual_identifier,
                    segments=segments,
                    condition=condition,
                )
                settled_successfully = record.settling_failures == 0
                initial = record.samples[0].settling.activity[1, :, 2]
                settled = record.settled_states[-1, :, 2]
                basin_evaluation = arm.frozen_basins.evaluate(
                    expected_category=category["id"],
                    initial_activity=initial,
                    settled_activity=settled,
                    settled_successfully=settled_successfully,
                )
                row = basin_evaluation.as_dict()
                row.update(
                    {
                        "id": identifier,
                        "arm_id": arm.identifier,
                        "condition": condition,
                        "category_id": category["id"],
                        "pseudoword_id": pseudoword["id"],
                        "visual_instance_id": visual_identifier,
                        "segments": list(segments),
                        "settling_failure": not settled_successfully,
                        "correct_basin": basin_evaluation.correct_basin,
                    }
                )
                settling_failures += int(not settled_successfully)
                condition_records[condition].append(record)
                condition_rows[condition].append(row)
                condition_initial.append(initial)
                condition_settled.append(settled)
                condition_success.append(settled_successfully)
                presentation_rows.append(
                    _presentation_row(
                        record,
                        arm_id=arm.identifier,
                        phase="frozen_evaluation",
                        visual_instance_id=visual_identifier,
                    )
                )
            arm_initial.append(np.stack(condition_initial))
            arm_settled.append(np.stack(condition_settled))
            arm_success.append(np.asarray(condition_success))

        arm_lexical = []
        arm_lexical_correct = []
        arm_lexical_controls = []
        arm_control_labels = []
        arm_visual_trajectories = []
        arm_correct_trajectories = []
        arm_control_trajectories = []
        for index, category in enumerate(categories):
            pseudoword = arm.pairing[index]
            visual_record = condition_records["visual_only"][index]
            full_record = condition_records["full"][index]
            visual_trajectory = _output_trajectory(
                visual_record,
                trajectory_indices,
                auditory_only=False,
            )
            correct_trajectory = _output_trajectory(
                full_record,
                trajectory_indices,
                auditory_only=True,
            )
            controls = {
                "reversed": pseudoword["controls"]["reversed"],
                "permuted": pseudoword["controls"]["permuted"],
                "repeated_segment": pseudoword["controls"]["repeated_segment"],
            }
            controls.update(
                {
                    f"competing:{competitor['id']}": competitor["segments"]
                    for competitor in all_pseudowords
                    if competitor["id"] != pseudoword["id"]
                }
            )
            control_trajectories = {}
            control_failed = False
            for control_name, control_segments in controls.items():
                identifier = (
                    f"{arm.identifier}-lexical-{control_name}-{category['id']}"
                )
                control_record = arm.protocol.run_cue(
                    presentation_id=identifier,
                    category=category,
                    pseudoword_id=pseudoword["id"],
                    visual_properties=category["prototype"]["properties"],
                    visual_identifier=category["id"],
                    segments=control_segments,
                    condition=f"lexical_control:{control_name}",
                )
                failed = control_record.settling_failures > 0
                control_failed = control_failed or failed
                settling_failures += int(failed)
                control_trajectories[control_name] = _output_trajectory(
                    control_record,
                    trajectory_indices,
                    auditory_only=True,
                )
                presentation_rows.append(
                    _presentation_row(
                        control_record,
                        arm_id=arm.identifier,
                        phase="lexical_control",
                        visual_instance_id=category["id"],
                    )
                )
            lexical = trajectory_observer.evaluate(
                visual_reactivation=visual_trajectory,
                correct_trajectory=correct_trajectory,
                control_trajectories=control_trajectories,
            )
            lexical_row = lexical.as_dict()
            lexical_row.update(
                {
                    "arm_id": arm.identifier,
                    "category_id": category["id"],
                    "pseudoword_id": pseudoword["id"],
                    "settling_failure": control_failed
                    or visual_record.settling_failures > 0
                    or full_record.settling_failures > 0,
                    "correct_better_than_every_control": (
                        lexical.correct_better_than_every_control
                        and not control_failed
                        and visual_record.settling_failures == 0
                        and full_record.settling_failures == 0
                    ),
                }
            )
            arm_lexical.append(lexical_row)
            arm_lexical_correct.append(lexical.correct_distance)
            arm_lexical_controls.append(
                [lexical.control_distances[name] for name in controls]
            )
            arm_control_labels.append(list(controls))
            arm_visual_trajectories.append(
                trajectory_observer.sample(visual_trajectory)
            )
            arm_correct_trajectories.append(
                trajectory_observer.sample(correct_trajectory)
            )
            arm_control_trajectories.append(
                np.stack(
                    [
                        trajectory_observer.sample(control_trajectories[name])
                        for name in controls
                    ]
                )
            )
        after = _durable_state(arm.network)
        durable_changed = any(
            not np.array_equal(before[name], after[name]) for name in before
        )
        durable_changes += int(durable_changed)
        arm_evidence[arm.identifier] = {
            "durable_state_frozen": not durable_changed,
            "durable_state_before_digest": _array_digest(before),
            "durable_state_after_digest": _array_digest(after),
            "conditions": condition_rows,
            "lexical_reactivation": arm_lexical,
        }
        completion_initial.append(np.stack(arm_initial))
        completion_settled.append(np.stack(arm_settled))
        completion_success.append(np.stack(arm_success))
        lexical_correct.append(np.asarray(arm_lexical_correct))
        lexical_controls.append(np.asarray(arm_lexical_controls))
        lexical_control_labels.append(np.asarray(arm_control_labels))
        lexical_visual_trajectories.append(np.stack(arm_visual_trajectories))
        lexical_correct_trajectories.append(np.stack(arm_correct_trajectories))
        lexical_control_trajectories.append(np.stack(arm_control_trajectories))

    condition_counts = {
        condition: sum(
            len(arm_evidence[arm_id]["conditions"][condition])
            for arm_id in ARM_IDS
        )
        for condition in condition_order
    }
    correct_basin = {
        arm_id: {
            condition: sum(
                row["correct_basin"]
                for row in arm_evidence[arm_id]["conditions"][condition]
            )
            for condition in condition_order
        }
        for arm_id in ARM_IDS
    }
    reactivation_success = {
        arm_id: sum(
            row["correct_better_than_every_control"]
            for row in arm_evidence[arm_id]["lexical_reactivation"]
        )
        for arm_id in ARM_IDS
    }
    evidence = {
        "primary_distance": "standardized_euclidean",
        "secondary_diagnostic": "cosine_distance",
        "trajectory_distance": "resampled_root_mean_square",
        "trajectory_sample_points": declaration["trajectory_sample_points"],
        "partial_visual_dimensions": list(partial_dimensions),
        "arms": arm_evidence,
    }
    arrays = {
        "completion_condition_ids": np.asarray(condition_order),
        "completion_initial_output": np.stack(completion_initial),
        "completion_settled_output": np.stack(completion_settled),
        "completion_settled": np.stack(completion_success),
        "lexical_correct_distance": np.stack(lexical_correct),
        "lexical_control_distances": np.stack(lexical_controls),
        "lexical_control_labels": np.stack(lexical_control_labels),
        "lexical_visual_trajectory": np.stack(lexical_visual_trajectories),
        "lexical_correct_trajectory": np.stack(lexical_correct_trajectories),
        "lexical_control_trajectories": np.stack(lexical_control_trajectories),
    }
    summary = {
        "completion": {
            "conditions": condition_counts,
            "correct_basin_by_arm_and_condition": correct_basin,
            "durable_changes_during_evaluation": durable_changes,
            "settling_failures": settling_failures,
        },
        "reactivation": {
            "correct_better_than_controls_by_arm": reactivation_success,
            "trained_correct_better_than_controls": reactivation_success["trained"],
        },
    }
    return evidence, arrays, presentation_rows, summary


def _causal_completion_scores(
    definition: dict,
    categories: list[dict],
    arm: ArmRun,
) -> np.ndarray:
    """Measure each Column's effect on frozen partial-cue completion."""
    if "completion" not in definition:
        raise ValueError("Functional Web detection requires completion cues")
    partial_dimensions = set(
        definition["completion"]["partial_visual_dimensions"]
    )
    labels = tuple(arm.network.column_labels())
    scores = np.zeros((len(categories), len(labels)), dtype=np.float64)
    counts = np.zeros_like(scores, dtype=np.int64)
    for category_index, category in enumerate(categories):
        pseudoword = arm.pairing[category_index]
        for instance in category["splits"]["basin_estimation"]:
            properties = [
                property_
                for property_ in instance["properties"]
                if property_["dimension"] in partial_dimensions
            ]
            baseline = arm.protocol.run_cue(
                presentation_id=f"web-baseline-{instance['id']}",
                category=category,
                pseudoword_id=pseudoword["id"],
                visual_properties=properties,
                visual_identifier=instance["id"],
                segments=(),
                condition="web_detection_baseline",
            )
            if baseline.settling_failures:
                continue
            baseline_distance = arm.frozen_basins.evaluate(
                expected_category=category["id"],
                initial_activity=baseline.samples[0].settling.activity[1, :, 2],
                settled_activity=baseline.settled_states[-1, :, 2],
            ).correct_distance
            for column_index, label in enumerate(labels):
                with arm.network.lesion((label,)):
                    perturbed = arm.protocol.run_cue(
                        presentation_id=f"web-lesion-{instance['id']}-{label}",
                        category=category,
                        pseudoword_id=pseudoword["id"],
                        visual_properties=properties,
                        visual_identifier=instance["id"],
                        segments=(),
                        condition="web_detection_lesion",
                    )
                if perturbed.settling_failures:
                    continue
                lesion_distance = arm.frozen_basins.evaluate(
                    expected_category=category["id"],
                    initial_activity=perturbed.samples[0].settling.activity[1, :, 2],
                    settled_activity=perturbed.settled_states[-1, :, 2],
                ).correct_distance
                scores[category_index, column_index] += (
                    lesion_distance - baseline_distance
                )
                counts[category_index, column_index] += 1
    np.divide(scores, counts, out=scores, where=counts > 0)
    return scores


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
            "completion": definition.get("completion"),
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
    learning_attributes = (
        "ascending_eligibility",
        "descending_eligibility",
        "pre_ascending_weights",
        "post_ascending_weights",
        "pre_descending_weights",
        "post_descending_weights",
    )
    learning_arrays = {
        attribute: np.stack(
            [
                np.stack(
                    [
                        _learning_values(result, "projections", attribute)
                        for result in arm.learning_results
                    ]
                )
                for arm in arms
            ]
        )
        for attribute in learning_attributes
    }
    population_learning_attributes = (
        "pre_thresholds",
        "post_thresholds",
        "pre_activity_average",
        "post_activity_average",
        "pre_entrenchment",
        "post_entrenchment",
        "post_contributor_counts",
        "recruited",
    )
    learning_arrays.update(
        {
            attribute: np.stack(
                [
                    np.stack(
                        [
                            _learning_values(result, "populations", attribute)
                            for result in arm.learning_results
                        ]
                    )
                    for arm in arms
                ]
            )
            for attribute in population_learning_attributes
        }
    )
    learning_arrays.update(
        {
            "arm_ids": np.asarray(ARM_IDS),
            "presentation_ids": np.asarray(
                [
                    [result.presentation_id for result in arm.learning_results]
                    for arm in arms
                ]
            ),
            "success_signals": np.asarray(
                [
                    [result.success_signal for result in arm.learning_results]
                    for arm in arms
                ]
            ),
        }
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
    result = {
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
        "learning": {
            "arm_ids": list(ARM_IDS),
            "parameters": dict(definition["network"]["plasticity"]),
            "adaptation_parameters": dict(definition["network"]["adaptation"]),
            "presentations": {
                arm.identifier: [
                    {
                        "id": learning.presentation_id,
                        "success_signal": learning.success_signal,
                        "adaptation_applied": learning.adaptation_applied,
                        "ascending_eligibility_sum": float(
                            sum(
                                projection.ascending_eligibility.sum()
                                for projection in learning.projections
                            )
                        ),
                        "descending_eligibility_sum": float(
                            sum(
                                projection.descending_eligibility.sum()
                                for projection in learning.projections
                            )
                        ),
                    }
                    for learning in arm.learning_results
                ]
                for arm in arms
            },
        },
        "learning_arrays": learning_arrays,
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
    if "completion" in definition:
        evidence, arrays, rows, summary = _completion_evidence(
            definition,
            dataset,
            categories,
            arms,
        )
        result["completion"] = evidence
        result["activity_arrays"].update(arrays)
        result["presentations"].extend(rows)
        result["summary"].update(summary)
        result["parameters"]["trajectory_sample_points"] = definition[
            "completion"
        ]["trajectory_sample_points"]
    detection = None
    detector_inputs = None
    if "web_detection" in definition:
        declaration = definition["web_detection"]
        if set(declaration) != {
            "control_quantile",
            "fdr_alpha",
            "control_resamples",
            "minimum_association_distance",
        }:
            raise ValueError(
                "web detection must declare controls, correction, and association distance"
            )
        durable_before = _durable_state(arms[0].network)
        causal_scores = _causal_completion_scores(
            definition,
            categories,
            arms[0],
        )
        durable_after = _durable_state(arms[0].network)
        detector_inputs = build_functional_web_evidence(
            network=arms[0].network,
            category_ids=tuple(category["id"] for category in categories),
            basin_activity=basin_array[0],
            causal_scores=causal_scores,
            control_resamples=declaration["control_resamples"],
            seed=int(definition["seed"]),
        )
        detection = FunctionalWebObserver(
            control_quantile=declaration["control_quantile"],
            fdr_alpha=declaration["fdr_alpha"],
            minimum_association_distance=declaration[
                "minimum_association_distance"
            ],
        ).detect(**detector_inputs)
        web_report = detection.as_dict()
        web_report.update(
            {
                "data_scope": ["acquisition", "basin_estimation"],
                "held_out_used": False,
                "control_resamples": declaration["control_resamples"],
                "arm": "trained",
                "durable_state_frozen": all(
                    np.array_equal(durable_before[name], durable_after[name])
                    for name in durable_before
                ),
                "durable_state_before_digest": _array_digest(durable_before),
                "durable_state_after_digest": _array_digest(durable_after),
                "evidence_definitions": {
                    "reliability": {
                        "score": "category_mean_minus_pooled_other_category_mean",
                        "control": "label_shuffle_preserving_category_counts",
                    },
                    "causal": {
                        "score": "partial_cue_correct_basin_distance_increase_after_output_lesion",
                        "control": "Population_degree_activity_matched_random_Column_lesions",
                    },
                    "connectivity": {
                        "score": (
                            "sum_sqrt_directional_weight_product_times_"
                            "minimum_endpoint_activity"
                        ),
                        "control": "within_Population_activity_shuffle_over_fixed_degree_topology",
                    },
                    "multiple_testing": "benjamini_hochberg_within_category_and_evidence",
                },
            }
        )
        result["webs"] = web_report
        result["summary"]["web_detection"] = {
            "detected_webs": sum(bool(web.members) for web in detection.webs.values()),
            "selected_memberships": sum(
                len(web.members) for web in detection.webs.values()
            ),
            "shared_columns": len(detection.shared_columns),
            "association_distinguishable": detection.association_distinguishable,
            "simple_activation_threshold_used": False,
        }
        result["parameters"].update(declaration)
    if "cardinals" in definition:
        if detection is None or detector_inputs is None:
            raise ValueError("Cardinal classification requires Functional Web detection")
        declaration = definition["cardinals"]
        if set(declaration) != {
            "entry_route_threshold",
            "stability_threshold",
            "control_quantile",
            "stimulation_pulse_ticks",
            "minimum_subwebs_reinstated",
            "control_tolerances",
        }:
            raise ValueError(
                "cardinals must declare lifecycle, intervention, and control parameters"
            )
        pulse_ticks = declaration["stimulation_pulse_ticks"]
        if isinstance(pulse_ticks, bool) or not isinstance(pulse_ticks, int) or pulse_ticks < 1:
            raise ValueError("stimulation pulse ticks must be a positive integer")
        observer = CardinalObserver(
            entry_route_threshold=declaration["entry_route_threshold"],
            stability_threshold=declaration["stability_threshold"],
            control_quantile=declaration["control_quantile"],
            minimum_subwebs_reinstated=declaration[
                "minimum_subwebs_reinstated"
            ],
        )
        labels = tuple(arms[0].network.column_labels())
        recruited = np.concatenate(list(arms[0].network.recruited_columns().values()))
        condition_ids = list(result["activity_arrays"]["completion_condition_ids"])
        completion_output = result["activity_arrays"]["completion_settled_output"][0]
        visual_output = completion_output[condition_ids.index("visual_only")]
        pseudoword_output = completion_output[condition_ids.index("pseudoword_only")]
        full_medians = np.median(basin_array[0], axis=1)
        held_out_stability = np.clip(
            1.0 - np.std(held_settled_array[0], axis=1),
            0.0,
            1.0,
        )
        category_reports = {}
        all_candidate_labels = []
        all_cardinal_labels = []
        for category_index, category in enumerate(categories):
            category_id = category["id"]
            web_members = set(detection.webs[category_id].members)
            rows = []
            for column_index, label in enumerate(labels):
                row = {
                    "label": label,
                    "recruited": bool(recruited[column_index]),
                    "functional_web_member": label in web_members,
                    "entry_routes": {
                        "visual": float(visual_output[category_index, column_index]),
                        "pseudoword": float(
                            pseudoword_output[category_index, column_index]
                        ),
                    },
                    "held_out_stability": float(
                        held_out_stability[category_index, column_index]
                    ),
                    "supporting_web_stimulation": 0.0,
                    "matched_non_recruited_stimulation": [0.0],
                    "stimulation_amplitude": float(
                        full_medians[category_index, column_index]
                    ),
                    "interventions": {
                        "status": "not_tested_without_candidate_evidence",
                        "stimulation": {
                            "subwebs_reinstated": 0,
                            "ignition": 0.0,
                            "completion": 0.0,
                            "feature_accessibility": 0.0,
                            "ordered_reactivation": 0.0,
                        },
                        "individual_lesion": {
                            "ignition_impairment": 0.0,
                            "completion_impairment": 0.0,
                            "feature_accessibility": 0.0,
                            "ordered_reactivation_impairment": 0.0,
                        },
                        "group_lesion": {
                            "ignition_impairment": 0.0,
                            "completion_impairment": 0.0,
                            "feature_accessibility": 0.0,
                            "ordered_reactivation_impairment": 0.0,
                        },
                        "matched_control_lesion_impairment": [0.0],
                        "redundant_recovery": 0.0,
                    },
                    "replicated_across_seeds": False,
                }
                rows.append(row)
            observation = observer.classify(tuple(rows))
            report = observation.as_dict()
            report.update(
                {
                    "candidate_group_intervention": {
                        "status": "not_tested_no_candidates",
                        "members": report["candidate_labels"],
                    },
                    "matched_recruited_controls": [],
                    "matched_random_controls": [],
                    "failures": [
                        "no_causally_detected_Functional_Web"
                    ]
                    if not web_members
                    else [],
                }
            )
            category_reports[category_id] = report
            all_candidate_labels.extend(report["candidate_labels"])
            all_cardinal_labels.extend(report["cardinal_node_labels"])
        result["cardinals"] = {
            "observer_only": True,
            "runtime_cardinal_flags": False,
            "stimulation_protocol": {
                "amplitude": "median_full_presentation_output",
                "pulse_ticks": pulse_ticks,
                "sensory_input": "absent",
            },
            "lesion_protocol": {
                "output": "clamped_to_zero",
                "input_observable": True,
                "integration_observable": True,
            },
            "control_matching": {
                "fields": [
                    "Population",
                    "Level",
                    "activity",
                    "incoming_degree",
                    "outgoing_degree",
                    "entrenchment",
                    "baseline_perturbation_sensitivity",
                ],
                "tolerances": declaration["control_tolerances"],
            },
            "categories": category_reports,
            "candidate_labels": all_candidate_labels,
            "cardinal_node_labels": all_cardinal_labels,
            "replication_status": "pending_multi_seed_experiment",
        }
        result["summary"]["cardinals"] = {
            "candidates": len(all_candidate_labels),
            "cardinal_nodes": len(all_cardinal_labels),
            "negative_result": not all_candidate_labels,
            "intervention_failures": sum(
                len(report["failures"]) for report in category_reports.values()
            ),
        }
        result["parameters"].update(declaration)
    return result
