"""Cardinal intervention protocol and observer artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from ccf6.experiment import execute, load


def test_cardinal_artifact_exposes_lifecycle_controls_interventions_and_failures(
    tmp_path,
):
    definition_path = (
        Path(__file__).parents[2] / "experiments/010-cardinal-classification.json"
    )

    run = execute(load(definition_path), tmp_path)

    manifest = json.loads((run / "manifest.json").read_text())
    cardinals = json.loads((run / "cardinals.json").read_text())
    summary = json.loads((run / "summary.json").read_text())
    assert "cardinals.json" in manifest["files"]
    assert "learning.json" in manifest["files"]
    assert "learning.npz" in manifest["files"]
    assert list(manifest["checksums"]) == [
        name for name in manifest["files"] if name != "manifest.json"
    ]
    for name, checksum in manifest["checksums"].items():
        assert hashlib.sha256((run / name).read_bytes()).hexdigest() == checksum
    learning = np.load(run / "learning.npz", allow_pickle=False)
    assert learning["ascending_eligibility"].shape[:2] == (3, 24)
    assert learning["pre_ascending_weights"].shape == learning[
        "post_ascending_weights"
    ].shape
    assert learning["pre_descending_weights"].shape == learning[
        "post_descending_weights"
    ].shape
    assert cardinals["observer_only"] is True
    assert cardinals["runtime_cardinal_flags"] is False
    assert cardinals["stimulation_protocol"] == {
        "amplitude": "median_full_presentation_output",
        "pulse_ticks": 20,
        "sensory_input": "absent",
    }
    assert cardinals["lesion_protocol"] == {
        "output": "clamped_to_zero",
        "input_observable": True,
        "integration_observable": True,
    }
    assert cardinals["control_matching"]["fields"] == [
        "Population",
        "Level",
        "activity",
        "incoming_degree",
        "outgoing_degree",
        "entrenchment",
        "baseline_perturbation_sensitivity",
    ]
    assert set(cardinals["categories"]) == {
        "category-1",
        "category-2",
        "category-3",
        "category-4",
    }
    for category in cardinals["categories"].values():
        assert set(category) >= {
            "columns",
            "candidate_group_intervention",
            "matched_recruited_controls",
            "matched_random_controls",
            "failures",
        }
        for column in category["columns"].values():
            assert set(column["measures"]) == {
                "ignition",
                "completion",
                "feature_accessibility",
                "ordered_phonological_reactivation",
                "redundant_recovery",
                "individual_lesion_ignition_impairment",
                "group_lesion_ignition_impairment",
            }
    assert summary["cardinals"]["candidates"] == 0
    assert summary["cardinals"]["cardinal_nodes"] == 0
    assert summary["cardinals"]["negative_result"] is True
