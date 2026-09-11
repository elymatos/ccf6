"""Matched experimental arms and frozen Target Basin artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ccf6.experiment import execute, load


def test_matched_arms_produce_complete_frozen_target_basins(tmp_path):
    definition_path = (
        Path(__file__).parents[2] / "experiments/007-matched-target-basins.json"
    )

    run = execute(load(definition_path), tmp_path)

    manifest = json.loads((run / "manifest.json").read_text())
    summary = json.loads((run / "summary.json").read_text())
    arms = json.loads((run / "arms.json").read_text())
    basins = json.loads((run / "basins.json").read_text())
    arm_arrays = np.load(run / "arms.npz", allow_pickle=False)
    assert manifest["files"] == [
        "definition.json",
        "manifest.json",
        "dataset.json",
        "topology.npz",
        "topology.json",
        "arms.npz",
        "arms.json",
        "presentations.jsonl",
        "learning.npz",
        "learning.json",
        "activity.npz",
        "activity.json",
        "basins.json",
        "summary.json",
    ]
    assert summary["arms"] == {
        "count": 3,
        "matched_initial_conditions": True,
        "untrained_durable_change": False,
        "shuffled_difference": ["category_pseudoword_pairing"],
    }
    assert arms["shared"]["seed"] == 20260910
    assert len({row["dataset_digest"] for row in arms["arms"]}) == 1
    assert len({row["split_digest"] for row in arms["arms"]}) == 1
    assert len({row["initial_topology_digest"] for row in arms["arms"]}) == 1
    assert len({row["parameter_digest"] for row in arms["arms"]}) == 1

    trained, untrained, shuffled = range(3)
    np.testing.assert_array_equal(
        arm_arrays["initial_ascending_weights"][trained],
        arm_arrays["initial_ascending_weights"][untrained],
    )
    np.testing.assert_array_equal(
        arm_arrays["initial_ascending_weights"][trained],
        arm_arrays["initial_ascending_weights"][shuffled],
    )
    np.testing.assert_array_equal(
        arm_arrays["initial_descending_weights"][trained],
        arm_arrays["initial_descending_weights"][untrained],
    )
    np.testing.assert_array_equal(
        arm_arrays["initial_descending_weights"][trained],
        arm_arrays["initial_descending_weights"][shuffled],
    )
    np.testing.assert_array_equal(
        arm_arrays["initial_thresholds"][trained],
        arm_arrays["initial_thresholds"][untrained],
    )
    np.testing.assert_array_equal(
        arm_arrays["initial_thresholds"][trained],
        arm_arrays["initial_thresholds"][shuffled],
    )
    np.testing.assert_array_equal(
        arm_arrays["final_ascending_weights"][untrained],
        arm_arrays["initial_ascending_weights"][untrained],
    )
    np.testing.assert_array_equal(
        arm_arrays["final_descending_weights"][untrained],
        arm_arrays["initial_descending_weights"][untrained],
    )
    np.testing.assert_array_equal(
        arm_arrays["final_thresholds"][untrained],
        arm_arrays["initial_thresholds"][untrained],
    )
    np.testing.assert_array_equal(
        arm_arrays["final_activity_average"][untrained],
        0.0,
    )
    np.testing.assert_array_equal(
        arm_arrays["final_entrenchment"][untrained],
        0.0,
    )
    np.testing.assert_array_equal(
        arm_arrays["final_contributor_counts"][untrained],
        0,
    )
    assert not np.any(arm_arrays["final_recruited"][untrained])
    assert not np.array_equal(
        arm_arrays["final_ascending_weights"][trained],
        arm_arrays["initial_ascending_weights"][trained],
    )
    np.testing.assert_array_equal(
        arm_arrays["pairing_pseudoword_ids"][trained],
        arm_arrays["pairing_pseudoword_ids"][untrained],
    )
    assert not np.array_equal(
        arm_arrays["pairing_pseudoword_ids"][trained],
        arm_arrays["pairing_pseudoword_ids"][shuffled],
    )
    assert sorted(arm_arrays["pairing_pseudoword_ids"][trained]) == sorted(
        arm_arrays["pairing_pseudoword_ids"][shuffled]
    )

    assert set(basins["arms"]) == {"trained", "untrained", "shuffled"}
    held_out_ids = {
        instance["id"]
        for category in json.loads((run / "dataset.json").read_text())["categories"]
        for instance in category["splits"]["final_held_out"]
    }
    for arm in basins["arms"].values():
        frozen = arm["frozen"]
        assert frozen["fit_splits"] == ["acquisition", "basin_estimation"]
        assert frozen["held_out_used_for_fit"] is False
        assert min(frozen["pooled_scale"]) >= 0.05
        assert len(arm["held_out_evaluations"]) == 16
        for basin in frozen["categories"].values():
            assert len(basin["instance_ids"]) == 4
            assert held_out_ids.isdisjoint(basin["instance_ids"])
            assert basin["reliable_columns"] >= 5
            assert len(basin["within_distances"]) == 4
            assert len(basin["between_distances"]) == 3
            assert basin["margin"] >= 0.0
        for evaluation in arm["held_out_evaluations"]:
            expected = evaluation["expected_category"]
            margin = frozen["categories"][expected]["margin"]
            assert evaluation["margin"] == margin
            assert evaluation["beats_every_competitor"] == all(
                evaluation["correct_distance"] + margin < distance
                for distance in evaluation["competing_distances"].values()
            )
