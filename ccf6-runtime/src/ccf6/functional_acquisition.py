"""Balanced acquisition using local Eligibility and diffuse Success Signals."""

from __future__ import annotations

from collections import Counter

import numpy as np

from ccf6.domain import generate_domain
from ccf6.functional_network import LearningResult, Network, ProjectionLearningResult
from ccf6.functional_presentation import PresentationProtocol, PresentationRecord


def _require_acquisition(definition: dict) -> tuple[int, int]:
    if "seed" not in definition or "network" not in definition:
        raise ValueError("success-gated acquisition requires seed and Network")
    acquisition = definition.get("acquisition", {})
    if set(acquisition) != {"epochs", "mismatch_rotation"}:
        raise ValueError("acquisition must declare epochs and mismatch_rotation")
    epochs = acquisition["epochs"]
    rotation = acquisition["mismatch_rotation"]
    if isinstance(epochs, bool) or not isinstance(epochs, int) or epochs < 1:
        raise ValueError("acquisition epochs must be a positive integer")
    if isinstance(rotation, bool) or not isinstance(rotation, int) or rotation < 1:
        raise ValueError("mismatch rotation must be a positive integer")
    presentation = definition.get("presentation", {})
    if set(presentation) != {"visual_populations", "auditory_population"}:
        raise ValueError(
            "presentation must declare visual_populations and auditory_population"
        )
    return epochs, rotation


def _flatten(result: LearningResult, attribute: str) -> np.ndarray:
    return np.concatenate(
        [getattr(projection, attribute) for projection in result.projections]
    )


def _flatten_populations(result: LearningResult, attribute: str) -> np.ndarray:
    return np.concatenate(
        [getattr(population, attribute) for population in result.populations]
    )


def _projection_learning_row(
    projection: ProjectionLearningResult,
    incoming_norm: float,
) -> dict:
    ascending_delta = (
        projection.post_ascending_weights - projection.pre_ascending_weights
    )
    descending_delta = (
        projection.post_descending_weights - projection.pre_descending_weights
    )
    return {
        "id": projection.identifier,
        "incoming_norm": incoming_norm,
        "eligibility": {
            "ascending_sum": float(projection.ascending_eligibility.sum()),
            "ascending_max": float(projection.ascending_eligibility.max()),
            "descending_sum": float(projection.descending_eligibility.sum()),
            "descending_max": float(projection.descending_eligibility.max()),
        },
        "ascending": {
            "pre_weights": projection.pre_ascending_weights.tolist(),
            "post_weights": projection.post_ascending_weights.tolist(),
            "changed_connections": int(np.count_nonzero(ascending_delta)),
            "delta_l2": float(np.linalg.norm(ascending_delta)),
        },
        "descending": {
            "pre_weights": projection.pre_descending_weights.tolist(),
            "post_weights": projection.post_descending_weights.tolist(),
            "changed_connections": int(np.count_nonzero(descending_delta)),
            "delta_l2": float(np.linalg.norm(descending_delta)),
        },
    }


def _learning_row(
    record: PresentationRecord,
    result: LearningResult,
    epoch: int | None,
    network: Network,
) -> dict:
    projections = [
        _projection_learning_row(projection, topology.incoming_norm)
        for projection, topology in zip(
            result.projections,
            network.projections,
            strict=True,
        )
    ]
    populations = []
    for learned in result.populations:
        population = network.populations[learned.identifier]
        populations.append(
            {
                "id": learned.identifier,
                "settled_output": learned.settled_output.tolist(),
                "thresholds": {
                    "pre": learned.pre_thresholds.tolist(),
                    "post": learned.post_thresholds.tolist(),
                },
                "activity_average": {
                    "pre": learned.pre_activity_average.tolist(),
                    "post": learned.post_activity_average.tolist(),
                },
                "entrenchment": {
                    "pre": learned.pre_entrenchment.tolist(),
                    "post": learned.post_entrenchment.tolist(),
                },
                "contributor_counts": learned.post_contributor_counts.tolist(),
                "contributing_presentations": [
                    sorted(values)
                    for values in population.contributing_presentations
                ],
                "recruited": learned.recruited.tolist(),
                "recruited_columns": int(np.count_nonzero(learned.recruited)),
            }
        )
    changed = any(
        projection[direction]["changed_connections"] > 0
        for projection in projections
        for direction in ("ascending", "descending")
    )
    return {
        "presentation_id": record.identifier,
        "epoch": epoch,
        "condition": record.condition,
        "category_id": record.category_id,
        "pseudoword_id": record.pseudoword_id,
        "success_signal": result.success_signal,
        "adaptation_applied": result.adaptation_applied,
        "durable_weights_changed": changed,
        "projections": projections,
        "populations": populations,
    }


def _has_durable_change(result: LearningResult) -> bool:
    return any(
        not np.array_equal(
            projection.pre_ascending_weights,
            projection.post_ascending_weights,
        )
        or not np.array_equal(
            projection.pre_descending_weights,
            projection.post_descending_weights,
        )
        for projection in result.projections
    ) or any(
        not np.array_equal(population.pre_thresholds, population.post_thresholds)
        or not np.array_equal(
            population.pre_activity_average,
            population.post_activity_average,
        )
        or not np.array_equal(
            population.pre_entrenchment,
            population.post_entrenchment,
        )
        for population in result.populations
    )


def _normalization_error(
    learning_results: list[LearningResult],
    network: Network,
) -> float:
    errors = []
    for result in learning_results:
        for learned, projection in zip(
            result.projections,
            network.projections,
            strict=True,
        ):
            ascending_totals = np.bincount(
                projection.targets,
                weights=learned.post_ascending_weights,
                minlength=network.populations[projection.target].columns,
            )
            descending_totals = np.bincount(
                projection.sources,
                weights=learned.post_descending_weights,
                minlength=network.populations[projection.source].columns,
            )
            errors.extend(np.abs(ascending_totals - projection.incoming_norm))
            errors.extend(
                np.abs(
                    descending_totals[descending_totals > 0.0]
                    - projection.incoming_norm
                )
            )
    return float(max(errors, default=0.0))


def run_success_gated_acquisition(definition: dict) -> dict:
    """Run frequency-balanced correct and mismatched acquisition Presentations."""
    epochs, rotation = _require_acquisition(definition)
    evaluation_count = 0
    if "evaluation" in definition:
        evaluation = definition["evaluation"]
        if set(evaluation) != {"full_pair_presentations_per_category"}:
            raise ValueError(
                "evaluation must declare full_pair_presentations_per_category"
            )
        evaluation_count = evaluation["full_pair_presentations_per_category"]
        if (
            isinstance(evaluation_count, bool)
            or not isinstance(evaluation_count, int)
            or evaluation_count < 1
        ):
            raise ValueError(
                "evaluation full-pair Presentations must be a positive integer"
            )
    dataset = generate_domain(int(definition["seed"]))
    network = Network(definition["network"])
    if network.plasticity is None:
        raise ValueError("success-gated acquisition requires Network plasticity")
    if evaluation_count and network.adaptation is None:
        raise ValueError("frozen evaluation requires Network adaptation")
    categories = dataset["categories"]
    if rotation % len(categories) == 0:
        raise ValueError("mismatch rotation must pair each category with another word")
    pseudowords = {row["id"]: row for row in dataset["pseudowords"]}
    ordered_pseudowords = [pseudowords[row["pseudoword_id"]] for row in categories]
    presentation = definition["presentation"]
    protocol = PresentationProtocol(
        network,
        dataset,
        visual_populations=presentation["visual_populations"],
        auditory_population=presentation["auditory_population"],
    )
    initial_topology = network.topology_snapshot()
    initial_topology_arrays = {
        name: values.copy() for name, values in network.topology_arrays().items()
    }
    records: list[PresentationRecord] = []
    learning_results: list[LearningResult] = []
    learning_rows = []

    def acquire(
        epoch: int,
        category: dict,
        pseudoword: dict,
        condition: str,
        success_signal: float,
    ) -> None:
        identifier = f"epoch-{epoch}-{condition}-{category['id']}"
        record = protocol.run(
            presentation_id=identifier,
            category=category,
            pseudoword_id=pseudoword["id"],
            segments=pseudoword["segments"],
            condition=condition,
            success_signal=success_signal,
        )
        if record.settling_failures:
            raise RuntimeError(
                f"{identifier}: cannot learn from a settling failure"
            )
        learning = network.apply_success_signal(success_signal, identifier)
        records.append(record)
        learning_results.append(learning)
        learning_rows.append(_learning_row(record, learning, epoch, network))

    for epoch in range(1, epochs + 1):
        for index, category in enumerate(categories):
            acquire(epoch, category, ordered_pseudowords[index], "correct", 1.0)
            acquire(
                epoch,
                category,
                ordered_pseudowords[(index + rotation) % len(categories)],
                "mismatched",
                0.0,
            )

    evaluation_records: list[PresentationRecord] = []
    evaluation_results: list[LearningResult] = []
    evaluation_rows = []
    if evaluation_count:
        network.freeze_adaptation()
        for repetition in range(1, evaluation_count + 1):
            for index, category in enumerate(categories):
                identifier = f"evaluation-{repetition}-{category['id']}"
                pseudoword = ordered_pseudowords[index]
                record = protocol.run(
                    presentation_id=identifier,
                    category=category,
                    pseudoword_id=pseudoword["id"],
                    segments=pseudoword["segments"],
                    condition="evaluation",
                    success_signal=1.0,
                )
                if record.settling_failures:
                    raise RuntimeError(
                        f"{identifier}: cannot evaluate a settling failure"
                    )
                result = network.apply_success_signal(1.0, identifier)
                evaluation_records.append(record)
                evaluation_results.append(result)
                evaluation_rows.append(
                    _learning_row(record, result, None, network)
                )
    all_records = records + evaluation_records

    projection_offsets = [0]
    for projection in network.projections:
        projection_offsets.append(projection_offsets[-1] + projection.sources.size)
    chunks = [
        sample.settling.activity
        for record in all_records
        for sample in record.samples
    ]
    trajectory_offsets = [0]
    for chunk in chunks:
        trajectory_offsets.append(trajectory_offsets[-1] + len(chunk))
    labels = np.asarray(network.column_labels())
    success_signals = np.asarray(
        [result.success_signal for result in learning_results]
    )
    conditions = np.asarray([record.condition for record in records])
    all_conditions = np.asarray([record.condition for record in all_records])
    pre_ascending = np.stack(
        [_flatten(result, "pre_ascending_weights") for result in learning_results]
    )
    post_ascending = np.stack(
        [_flatten(result, "post_ascending_weights") for result in learning_results]
    )
    pre_descending = np.stack(
        [_flatten(result, "pre_descending_weights") for result in learning_results]
    )
    post_descending = np.stack(
        [_flatten(result, "post_descending_weights") for result in learning_results]
    )
    ascending_eligibility = np.stack(
        [_flatten(result, "ascending_eligibility") for result in learning_results]
    )
    descending_eligibility = np.stack(
        [_flatten(result, "descending_eligibility") for result in learning_results]
    )
    pre_thresholds = np.stack(
        [_flatten_populations(result, "pre_thresholds") for result in learning_results]
    )
    post_thresholds = np.stack(
        [_flatten_populations(result, "post_thresholds") for result in learning_results]
    )
    pre_activity_average = np.stack(
        [
            _flatten_populations(result, "pre_activity_average")
            for result in learning_results
        ]
    )
    post_activity_average = np.stack(
        [
            _flatten_populations(result, "post_activity_average")
            for result in learning_results
        ]
    )
    pre_entrenchment = np.stack(
        [_flatten_populations(result, "pre_entrenchment") for result in learning_results]
    )
    post_entrenchment = np.stack(
        [_flatten_populations(result, "post_entrenchment") for result in learning_results]
    )
    post_contributor_counts = np.stack(
        [
            _flatten_populations(result, "post_contributor_counts")
            for result in learning_results
        ]
    )
    recruited = np.stack(
        [_flatten_populations(result, "recruited") for result in learning_results]
    )
    changed = np.any(pre_ascending != post_ascending, axis=1) | np.any(
        pre_descending != post_descending,
        axis=1,
    )
    condition_counts = Counter(record.condition for record in records)
    category_balance = {
        category["id"]: Counter(
            record.condition
            for record in records
            if record.category_id == category["id"]
        )
        for category in categories
    }
    pseudoword_balance = {
        pseudoword["id"]: Counter(
            record.condition
            for record in records
            if record.pseudoword_id == pseudoword["id"]
        )
        for pseudoword in ordered_pseudowords
    }
    balanced = all(
        counts == {"correct": epochs, "mismatched": epochs}
        for counts in (*category_balance.values(), *pseudoword_balance.values())
    )
    presentation_rows = []
    for record, learning_row in zip(records, learning_rows, strict=True):
        row = record.as_dict()
        row["epoch"] = learning_row["epoch"]
        row["learning"] = {
            "success_signal": learning_row["success_signal"],
            "durable_weights_changed": learning_row["durable_weights_changed"],
            "ascending_eligibility_sum": sum(
                projection["eligibility"]["ascending_sum"]
                for projection in learning_row["projections"]
            ),
            "descending_eligibility_sum": sum(
                projection["eligibility"]["descending_sum"]
                for projection in learning_row["projections"]
            ),
        }
        presentation_rows.append(row)
    for record, evaluation_row in zip(
        evaluation_records,
        evaluation_rows,
        strict=True,
    ):
        row = record.as_dict()
        row["evaluation"] = {
            "adaptation_applied": evaluation_row["adaptation_applied"],
            "durable_weights_changed": evaluation_row["durable_weights_changed"],
        }
        presentation_rows.append(row)
    failures = sum(record.settling_failures for record in all_records)
    durations = np.stack([record.sample_durations for record in all_records])
    unsuccessful_threshold_updates = int(
        np.count_nonzero(
            np.any(pre_thresholds != post_thresholds, axis=1)
            & (success_signals == 0.0)
        )
    )
    final_recruited = {
        population.identifier: int(np.count_nonzero(population.recruited))
        for population in learning_results[-1].populations
    }
    evaluation_changes = sum(
        _has_durable_change(result) for result in evaluation_results
    )

    return {
        "contract": "ncl-functional-web-v1",
        "dataset": dataset,
        "topology": initial_topology,
        "topology_arrays": initial_topology_arrays,
        "presentations": presentation_rows,
        "learning": {
            "parameters": dict(network.plasticity),
            "adaptation_parameters": (
                dict(network.adaptation) if network.adaptation else None
            ),
            "projection_ids": [
                projection.identifier for projection in network.projections
            ],
            "projection_offsets": projection_offsets,
            "category_balance": {
                key: dict(value) for key, value in category_balance.items()
            },
            "pseudoword_balance": {
                key: dict(value) for key, value in pseudoword_balance.items()
            },
            "presentations": learning_rows,
            "evaluation": evaluation_rows,
        },
        "learning_arrays": {
            "presentation_ids": np.asarray([record.identifier for record in records]),
            "epochs": np.repeat(np.arange(1, epochs + 1), len(categories) * 2),
            "conditions": conditions,
            "category_ids": np.asarray([record.category_id for record in records]),
            "pseudoword_ids": np.asarray([record.pseudoword_id for record in records]),
            "success_signals": success_signals,
            "projection_ids": np.asarray(
                [projection.identifier for projection in network.projections]
            ),
            "projection_offsets": np.asarray(projection_offsets, dtype=np.int64),
            "initial_eligibility": np.stack(
                [record.samples[0].initial_eligibility for record in records]
            ),
            "sample_initial_eligibility": np.stack(
                [
                    [sample.initial_eligibility for sample in record.samples]
                    for record in records
                ]
            ),
            "sample_settled_eligibility": np.stack(
                [
                    [sample.settled_eligibility for sample in record.samples]
                    for record in records
                ]
            ),
            "ascending_eligibility": ascending_eligibility,
            "descending_eligibility": descending_eligibility,
            "pre_ascending_weights": pre_ascending,
            "post_ascending_weights": post_ascending,
            "pre_descending_weights": pre_descending,
            "post_descending_weights": post_descending,
            "pre_thresholds": pre_thresholds,
            "post_thresholds": post_thresholds,
            "pre_activity_average": pre_activity_average,
            "post_activity_average": post_activity_average,
            "pre_entrenchment": pre_entrenchment,
            "post_entrenchment": post_entrenchment,
            "post_contributor_counts": post_contributor_counts,
            "recruited": recruited,
        },
        "activity_arrays": {
            "initial_activity": np.stack(
                [record.initial_activity for record in all_records]
            ),
            "settled_activity": np.stack(
                [record.settled_states for record in all_records]
            ),
            "sample_durations": durations,
            "sample_settled": np.asarray(
                [
                    [sample.settling.success for sample in record.samples]
                    for record in all_records
                ]
            ),
            "trajectory": np.concatenate(chunks),
            "trajectory_offsets": np.asarray(trajectory_offsets, dtype=np.int64),
            "labels": labels,
            "compartments": np.asarray(["Input", "Integration", "Output"]),
            "presentation_ids": np.asarray(
                [record.identifier for record in all_records]
            ),
            "conditions": all_conditions,
        },
        "activity": {
            "labels": labels.tolist(),
            "compartments": ["Input", "Integration", "Output"],
            "presentation_ids": [record.identifier for record in all_records],
            "settled_states": [
                record.settled_states.tolist() for record in all_records
            ],
        },
        "summary": {
            "acquisition": {
                "epochs": epochs,
                "presentations": len(records),
                "correct": condition_counts["correct"],
                "mismatched": condition_counts["mismatched"],
                "balanced": balanced,
            },
            "learning": {
                "successful_presentations_changed": int(
                    np.count_nonzero(changed & (success_signals == 1.0))
                ),
                "unsuccessful_presentations_changed": int(
                    np.count_nonzero(changed & (success_signals == 0.0))
                ),
                "ascending_weight_shift_l2": float(
                    np.linalg.norm(post_ascending[-1] - pre_ascending[0])
                ),
                "descending_weight_shift_l2": float(
                    np.linalg.norm(post_descending[-1] - pre_descending[0])
                ),
                "maximum_normalization_error": _normalization_error(
                    learning_results,
                    network,
                ),
                "weights_within_bounds": bool(
                    np.all((post_ascending >= 0.0) & (post_ascending <= 1.0))
                    and np.all((post_descending >= 0.0) & (post_descending <= 1.0))
                ),
            },
            "recruitment": {
                "threshold": (
                    float(network.adaptation["recruitment_threshold"])
                    if network.adaptation
                    else None
                ),
                "minimum_presentations": (
                    int(network.adaptation["minimum_presentations"])
                    if network.adaptation
                    else None
                ),
                "recruited_columns": sum(final_recruited.values()),
                "recruited_by_population": final_recruited,
                "recruited_after_first_presentation": int(
                    np.count_nonzero(recruited[0])
                ),
                "cardinal_candidates_declared": False,
            },
            "homeostasis": {
                "unsuccessful_presentations_updated": unsuccessful_threshold_updates,
                "threshold_histories": len(records),
                "thresholds_within_bounds": bool(
                    np.all(
                        post_thresholds
                        >= float(definition["network"]["thresholds"]["minimum"])
                    )
                    and np.all(
                        post_thresholds
                        <= float(definition["network"]["thresholds"]["maximum"])
                    )
                ),
            },
            "evaluation": {
                "presentations": len(evaluation_records),
                "adaptation_frozen": bool(
                    evaluation_results
                    and all(
                        not result.adaptation_applied
                        for result in evaluation_results
                    )
                ),
                "durable_changes": evaluation_changes,
            },
            "eligibility": {
                "minimum": float(
                    min(ascending_eligibility.min(), descending_eligibility.min())
                ),
                "maximum": float(
                    max(ascending_eligibility.max(), descending_eligibility.max())
                ),
                "reset_at_presentation_boundaries": bool(
                    np.all(
                        [
                            record.samples[0].initial_eligibility == 0.0
                            for record in records
                        ]
                    )
                ),
                "continuous_between_samples": bool(
                    all(
                        np.array_equal(
                            previous.settled_eligibility,
                            current.initial_eligibility,
                        )
                        for record in records
                        for previous, current in zip(
                            record.samples,
                            record.samples[1:],
                            strict=False,
                        )
                    )
                ),
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
            "categories": [row["id"] for row in categories],
            "conditions": dict(condition_counts),
        },
        "parameters": {
            **network.dynamics,
            **network.plasticity,
            **(network.adaptation or {}),
        },
    }
