"""Complete Functional Web artifact validation and identity."""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest

from ccf6.artifacts import (
    REQUIRED_FUNCTIONAL_WEB_FILES,
    validate_functional_web_artifact,
)
from ccf6.experiment import artifact_digest, digest


def complete_artifact(tmp_path):
    for name in REQUIRED_FUNCTIONAL_WEB_FILES:
        path = tmp_path / name
        if name == "presentations.jsonl":
            path.write_text('{"seed":1,"id":"presentation-1"}\n')
        else:
            path.write_text("{}")
    np.savez_compressed(
        tmp_path / "topology.npz",
        seed_1__population_ids=np.asarray(["population"]),
        seed_1__thresholds=np.asarray([0.5]),
    )
    learning_fields = (
        "ascending_eligibility", "descending_eligibility",
        "pre_ascending_weights", "post_ascending_weights",
        "pre_descending_weights", "post_descending_weights",
        "pre_thresholds", "post_thresholds", "pre_entrenchment",
        "post_entrenchment", "post_contributor_counts", "recruited",
    )
    np.savez_compressed(
        tmp_path / "learning.npz",
        **{f"seed_1__{field}": np.asarray([1.0]) for field in learning_fields},
    )
    activity_fields = (
        "completion_initial_output", "completion_settled_output",
        "lexical_visual_trajectory", "lexical_correct_trajectory",
        "lexical_control_trajectories",
    )
    np.savez_compressed(
        tmp_path / "activity.npz",
        **{f"seed_1__{field}": np.asarray([1.0]) for field in activity_fields},
    )
    manifest = {
        "contract": "ncl-functional-web-v1",
        "digest": "identity",
        "software_version": "0.2.0",
        "kind": "replicated_milestone",
        "status": "completed",
        "parameters": {"seed_inventory": [1]},
        "stimuli": {
            "seeds": [1],
            "arms": ["trained", "untrained", "shuffled"],
        },
        "files": list(REQUIRED_FUNCTIONAL_WEB_FILES),
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "definition.json").write_text(json.dumps({
        "kind": "replicated_milestone",
        "replication": {"seed_inventory": [1]},
    }))
    for name in ("dataset.json", "basins.json", "webs.json", "cardinals.json"):
        (tmp_path / name).write_text(json.dumps({"seeds": {"1": {}}}))
    (tmp_path / "metrics.json").write_text(json.dumps({
        "seed_inventory": [1],
        "seeds": [{"seed": 1}],
    }))
    (tmp_path / "aggregate.json").write_text(json.dumps({
        "effects": {}, "criteria": {}, "verdict": False,
    }))
    (tmp_path / "summary.json").write_text(json.dumps({"milestone_verdict": False}))
    manifest["checksums"] = {
        name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
        for name in REQUIRED_FUNCTIONAL_WEB_FILES
        if name != "manifest.json"
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    return tmp_path


def test_complete_artifact_is_readable_without_rerunning(tmp_path):
    report = validate_functional_web_artifact(complete_artifact(tmp_path))

    assert report["files"] == list(REQUIRED_FUNCTIONAL_WEB_FILES)
    assert report["presentations"] == 1
    assert report["seed_count"] == 1
    assert report["verdict"] is False
    assert set(report["arrays"]) == {
        "topology.npz",
        "learning.npz",
        "activity.npz",
    }


def test_missing_or_malformed_contract_is_rejected_honestly(tmp_path):
    complete_artifact(tmp_path)
    (tmp_path / "webs.json").write_text("not-json")
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    manifest["checksums"]["webs.json"] = hashlib.sha256(b"not-json").hexdigest()
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))

    with pytest.raises(ValueError, match="webs.json is not readable JSON"):
        validate_functional_web_artifact(tmp_path)


def test_staged_artifact_identity_uses_content_not_archive_bytes(tmp_path):
    definition = {"kind": "replicated_milestone", "replication": {"seed_inventory": [1]}}
    directories = [tmp_path / "first", tmp_path / "second"]
    for directory in directories:
        directory.mkdir()
        (directory / "dataset.json").write_text(
            json.dumps({"seeds": {"1": {"generated": [1, 2, 3]}}}, indent=2)
        )
        np.savez_compressed(
            directory / "topology.npz",
            seed_1__weights=np.asarray([0.1, 0.2]),
        )

    assert artifact_digest(
        definition, {"staged_artifacts": str(directories[0])}
    ) == artifact_digest(definition, {"staged_artifacts": str(directories[1])})


def test_artifact_identity_covers_definition_software_dataset_and_topology():
    definition = {"kind": "test", "seed": 1, "parameter": 0.1}
    result = {
        "dataset": {"generated": [1, 2, 3]},
        "topology_arrays": {"weights": np.asarray([0.1, 0.2])},
    }
    identity = artifact_digest(definition, result)

    assert artifact_digest({**definition, "parameter": 0.2}, result) != identity
    assert artifact_digest(
        definition,
        {**result, "dataset": {"generated": [1, 2, 4]}},
    ) != identity
    assert artifact_digest(
        definition,
        {**result, "topology_arrays": {"weights": np.asarray([0.2, 0.1])}},
    ) != identity
    assert digest(definition, software_version="0.2.0") != digest(
        definition, software_version="0.3.0"
    )
