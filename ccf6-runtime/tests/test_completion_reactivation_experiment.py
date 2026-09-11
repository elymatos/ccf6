"""Frozen partial-cue completion and ordered lexical reactivation artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ccf6.experiment import execute, load


def test_frozen_cues_record_completion_and_ordered_reactivation_by_arm(tmp_path):
    definition_path = (
        Path(__file__).parents[2] / "experiments/008-completion-reactivation.json"
    )

    run = execute(load(definition_path), tmp_path)

    manifest = json.loads((run / "manifest.json").read_text())
    summary = json.loads((run / "summary.json").read_text())
    evaluation = json.loads((run / "evaluation.json").read_text())
    activity = np.load(run / "activity.npz", allow_pickle=False)
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
        "evaluation.json",
        "summary.json",
    ]
    assert evaluation["primary_distance"] == "standardized_euclidean"
    assert evaluation["secondary_diagnostic"] == "cosine_distance"
    assert summary["completion"]["conditions"] == {
        "full": 12,
        "visual_only": 12,
        "pseudoword_only": 12,
        "partial_visual": 12,
        "atypical_held_out": 12,
    }
    assert summary["completion"]["durable_changes_during_evaluation"] == 0
    assert summary["completion"]["settling_failures"] == 0
    trained_reactivation = evaluation["arms"]["trained"]["lexical_reactivation"]
    assert summary["reactivation"]["trained_correct_better_than_controls"] == sum(
        row["correct_better_than_every_control"] for row in trained_reactivation
    )
    assert set(summary["completion"]["correct_basin_by_arm_and_condition"]) == {
        "trained",
        "untrained",
        "shuffled",
    }

    assert activity["completion_initial_output"].shape == (3, 5, 4, 55)
    assert activity["completion_settled_output"].shape == (3, 5, 4, 55)
    assert activity["completion_settled"].shape == (3, 5, 4)
    assert activity["lexical_correct_distance"].shape == (3, 4)
    assert activity["lexical_control_distances"].shape == (3, 4, 6)
    assert activity["lexical_visual_trajectory"].shape == (3, 4, 12, 15)
    assert activity["lexical_correct_trajectory"].shape == (3, 4, 12, 15)
    assert activity["lexical_control_trajectories"].shape == (3, 4, 6, 12, 15)
    np.testing.assert_allclose(
        activity["lexical_correct_distance"],
        np.sqrt(
            np.mean(
                np.square(
                    activity["lexical_visual_trajectory"]
                    - activity["lexical_correct_trajectory"]
                ),
                axis=(2, 3),
            )
        ),
    )
    assert np.all(activity["completion_settled"])
    assert np.any(activity["completion_initial_output"] != 0.0)

    for arm in evaluation["arms"].values():
        assert arm["durable_state_frozen"] is True
        assert arm["durable_state_before_digest"] == arm["durable_state_after_digest"]
        assert set(arm["conditions"]) == {
            "full",
            "visual_only",
            "pseudoword_only",
            "partial_visual",
            "atypical_held_out",
        }
        assert all(len(rows) == 4 for rows in arm["conditions"].values())
        for row in arm["conditions"]["partial_visual"]:
            if row["correct_basin"]:
                assert row["settling_failure"] is False
                assert row["closer_after_settling"] is True
                assert row["beats_every_competitor"] is True
        for row in arm["conditions"]["full"]:
            assert "correct_cosine_distance" in row
            assert "competing_cosine_distances" in row
        for row in arm["lexical_reactivation"]:
            assert row["correct_better_than_every_control"] == (
                not row["settling_failure"]
                and row["correct_distance"] < min(row["control_distances"].values())
            )
            assert set(row["control_distances"]) == {
                "reversed",
                "permuted",
                "repeated_segment",
                *{
                    f"competing:{number}"
                    for number in ("pseudoword-1", "pseudoword-2", "pseudoword-3", "pseudoword-4")
                    if number != row["pseudoword_id"]
                },
            }
