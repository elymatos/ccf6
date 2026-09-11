"""Cross-Presentation Recruitment, homeostasis, and frozen evaluation."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ccf6.experiment import execute, load


def test_recruitment_requires_distinct_presentations_and_evaluation_is_frozen(tmp_path):
    definition_path = (
        Path(__file__).parents[2] / "experiments/006-recruitment-homeostasis.json"
    )

    run = execute(load(definition_path), tmp_path)

    manifest = json.loads((run / "manifest.json").read_text())
    summary = json.loads((run / "summary.json").read_text())
    learning_rows = json.loads((run / "learning.json").read_text())
    learning = np.load(run / "learning.npz", allow_pickle=False)
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
    assert summary["recruitment"]["minimum_presentations"] == 3
    assert summary["recruitment"]["recruited_columns"] > 0
    assert summary["recruitment"]["recruited_after_first_presentation"] == 0
    assert summary["recruitment"]["cardinal_candidates_declared"] is False
    assert summary["homeostasis"]["unsuccessful_presentations_updated"] == 12
    assert summary["homeostasis"]["thresholds_within_bounds"] is True
    assert summary["evaluation"] == {
        "presentations": 4,
        "adaptation_frozen": True,
        "durable_changes": 0,
    }

    assert learning["pre_thresholds"].shape == (24, 55)
    assert learning["post_thresholds"].shape == (24, 55)
    assert learning["post_entrenchment"].shape == (24, 55)
    assert learning["post_contributor_counts"].shape == (24, 55)
    assert learning["recruited"].shape == (24, 55)
    assert not np.any(learning["recruited"][0])
    assert np.any(learning["recruited"][-1])
    assert np.all(
        learning["post_contributor_counts"][learning["recruited"]]
        >= summary["recruitment"]["minimum_presentations"]
    )
    assert np.all(
        learning["post_entrenchment"][learning["recruited"]]
        >= summary["recruitment"]["threshold"]
    )
    unsuccessful = learning["success_signals"] == 0.0
    assert np.all(
        np.any(
            learning["post_thresholds"][unsuccessful]
            != learning["pre_thresholds"][unsuccessful],
            axis=1,
        )
    )
    assert all(
        any(population["contributing_presentations"])
        for population in learning_rows["presentations"][-1]["populations"]
    )
    assert "cardinal" not in json.dumps(
        learning_rows["presentations"][-1]["populations"]
    ).lower()
