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
    epoch: int,
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
        "durable_weights_changed": changed,
        "projections": projections,
    }


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
    dataset = generate_domain(int(definition["seed"]))
    network = Network(definition["network"])
    if network.plasticity is None:
        raise ValueError("success-gated acquisition requires Network plasticity")
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
        learning = network.apply_success_signal(success_signal)
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

    projection_offsets = [0]
    for projection in network.projections:
        projection_offsets.append(projection_offsets[-1] + projection.sources.size)
    chunks = [
        sample.settling.activity
        for record in records
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
    failures = sum(record.settling_failures for record in records)
    durations = np.stack([record.sample_durations for record in records])

    return {
        "contract": "ncl-functional-web-v1",
        "dataset": dataset,
        "topology": initial_topology,
        "topology_arrays": initial_topology_arrays,
        "presentations": presentation_rows,
        "learning": {
            "parameters": dict(network.plasticity),
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
        },
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
            "trajectory_offsets": np.asarray(trajectory_offsets, dtype=np.int64),
            "labels": labels,
            "compartments": np.asarray(["Input", "Integration", "Output"]),
            "presentation_ids": np.asarray([record.identifier for record in records]),
            "conditions": conditions,
        },
        "activity": {
            "labels": labels.tolist(),
            "compartments": ["Input", "Integration", "Output"],
            "presentation_ids": [record.identifier for record in records],
            "settled_states": [record.settled_states.tolist() for record in records],
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
        },
    }
