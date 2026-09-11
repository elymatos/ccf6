"""Causal Functional Web evidence and artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from ccf6.experiment import execute, load


def test_functional_web_detection_preserves_every_control_and_selected_membership(
    tmp_path,
):
    definition_path = (
        Path(__file__).parents[2] / "experiments/009-functional-web-detection.json"
    )

    run = execute(load(definition_path), tmp_path)

    manifest = json.loads((run / "manifest.json").read_text())
    webs = json.loads((run / "webs.json").read_text())
    summary = json.loads((run / "summary.json").read_text())
    assert manifest["kind"] == "functional_web_detection"
    assert "webs.json" in manifest["files"]
    assert webs["data_scope"] == ["acquisition", "basin_estimation"]
    assert webs["held_out_used"] is False
    assert webs["durable_state_frozen"] is True
    assert webs["durable_state_before_digest"] == webs["durable_state_after_digest"]
    assert webs["detector"] == {
        "control_quantile": 0.95,
        "fdr_alpha": 0.05,
        "minimum_association_distance": 0.05,
    }
    assert set(webs["webs"]) == {
        "category-1",
        "category-2",
        "category-3",
        "category-4",
    }
    for web in webs["webs"].values():
        selected = []
        for label, column in web["columns"].items():
            assert all(
                len(column[name]["control_distribution"]) == 1000
                for name in ("reliability", "causal", "connectivity")
            )
            assert column["selected"] == all(
                column[name]["passed"]
                for name in ("reliability", "causal", "connectivity")
            )
            if column["selected"]:
                selected.append(label)
        assert web["members"] == selected
    assert summary["web_detection"]["detected_webs"] == sum(
        bool(web["members"]) for web in webs["webs"].values()
    )
    assert summary["web_detection"]["simple_activation_threshold_used"] is False
