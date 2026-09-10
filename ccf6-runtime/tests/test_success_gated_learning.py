"""Success-gated local Eligibility learning over balanced acquisition."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ccf6.experiment import execute, load


def test_acquisition_rejects_learning_from_a_settling_failure(tmp_path):
    definition_path = (
        Path(__file__).parents[2] / "experiments/005-success-gated-learning.json"
    )
    definition = load(definition_path)
    definition["network"]["settling"] = {
        "epsilon": 1.0,
        "stable_ticks": 3,
        "max_ticks": 2,
    }

    with pytest.raises(RuntimeError, match="cannot learn from a settling failure"):
        execute(definition, tmp_path)


def test_balanced_acquisition_changes_weights_only_after_success(tmp_path):
    definition_path = (
        Path(__file__).parents[2] / "experiments/005-success-gated-learning.json"
    )

    run = execute(load(definition_path), tmp_path)

    manifest = json.loads((run / "manifest.json").read_text())
    summary = json.loads((run / "summary.json").read_text())
    assert manifest["files"] == [
        "definition.json",
        "manifest.json",
        "dataset.json",
        "topology.npz",
        "topology.json",
        "presentations.jsonl",
        "learning.npz",
        "learning.json",
        "activity.npz",
        "activity.json",
        "summary.json",
    ]
    assert summary["acquisition"] == {
        "epochs": 3,
        "presentations": 24,
        "correct": 12,
        "mismatched": 12,
        "balanced": True,
    }
    assert summary["learning"]["unsuccessful_presentations_changed"] == 0
    assert summary["learning"]["successful_presentations_changed"] == 12
    assert summary["learning"]["maximum_normalization_error"] < 1e-12
    assert summary["learning"]["weights_within_bounds"] is True
    assert set(summary["eligibility"]) == {
        "minimum",
        "maximum",
        "reset_at_presentation_boundaries",
        "continuous_between_samples",
    }
    assert summary["eligibility"]["reset_at_presentation_boundaries"] is True
    assert summary["eligibility"]["continuous_between_samples"] is True
    assert 0.0 <= summary["eligibility"]["minimum"]
    assert summary["eligibility"]["maximum"] <= 1.0

    learning_rows = json.loads((run / "learning.json").read_text())
    assert all(
        counts == {"correct": 3, "mismatched": 3}
        for counts in learning_rows["category_balance"].values()
    )
    assert all(
        counts == {"correct": 3, "mismatched": 3}
        for counts in learning_rows["pseudoword_balance"].values()
    )
    assert all(
        "pre_weights" in projection["ascending"]
        and "post_weights" in projection["ascending"]
        and "pre_weights" in projection["descending"]
        and "post_weights" in projection["descending"]
        for row in learning_rows["presentations"]
        for projection in row["projections"]
    )

    learning = np.load(run / "learning.npz", allow_pickle=False)
    signals = learning["success_signals"]
    successful = signals == 1.0
    unsuccessful = signals == 0.0
    for epoch in (1, 2, 3):
        in_epoch = learning["epochs"] == epoch
        assert np.count_nonzero(successful & in_epoch) == 4
        assert np.count_nonzero(unsuccessful & in_epoch) == 4
        assert len(set(learning["category_ids"][successful & in_epoch])) == 4
        assert len(set(learning["category_ids"][unsuccessful & in_epoch])) == 4
        assert len(set(learning["pseudoword_ids"][successful & in_epoch])) == 4
        assert len(set(learning["pseudoword_ids"][unsuccessful & in_epoch])) == 4
    assert learning["initial_eligibility"].shape == (24, 324, 2)
    assert learning["sample_initial_eligibility"].shape == (24, 4, 324, 2)
    assert learning["sample_settled_eligibility"].shape == (24, 4, 324, 2)
    np.testing.assert_array_equal(learning["initial_eligibility"], 0.0)
    np.testing.assert_array_equal(
        learning["sample_initial_eligibility"][:, 1:],
        learning["sample_settled_eligibility"][:, :-1],
    )
    assert np.all(learning["ascending_eligibility"][unsuccessful].sum(axis=1) > 0.0)
    assert np.all(learning["descending_eligibility"][unsuccessful].sum(axis=1) > 0.0)
    np.testing.assert_array_equal(
        learning["pre_ascending_weights"][unsuccessful],
        learning["post_ascending_weights"][unsuccessful],
    )
    np.testing.assert_array_equal(
        learning["pre_descending_weights"][unsuccessful],
        learning["post_descending_weights"][unsuccessful],
    )
    assert np.all(
        np.any(
            learning["pre_ascending_weights"][successful]
            != learning["post_ascending_weights"][successful],
            axis=1,
        )
    )
    assert np.all(
        np.any(
            learning["pre_descending_weights"][successful]
            != learning["post_descending_weights"][successful],
            axis=1,
        )
    )
    np.testing.assert_array_equal(
        learning["post_ascending_weights"][:-1],
        learning["pre_ascending_weights"][1:],
    )
    np.testing.assert_array_equal(
        learning["post_descending_weights"][:-1],
        learning["pre_descending_weights"][1:],
    )
    assert not np.array_equal(
        learning["ascending_eligibility"],
        learning["descending_eligibility"],
    )

    topology = np.load(run / "topology.npz", allow_pickle=False)
    initial_ascending = np.concatenate(
        [
            topology[f"{projection_id}.ascending_weights"]
            for projection_id in learning["projection_ids"]
        ]
    )
    initial_descending = np.concatenate(
        [
            topology[f"{projection_id}.descending_weights"]
            for projection_id in learning["projection_ids"]
        ]
    )
    np.testing.assert_array_equal(
        learning["pre_ascending_weights"][0],
        initial_ascending,
    )
    np.testing.assert_array_equal(
        learning["pre_descending_weights"][0],
        initial_descending,
    )
