"""The declared-experiment to artifact interface."""

from __future__ import annotations

import json

import numpy as np
import pytest

from ccf6.experiment import digest, execute

DEFINITION = {
    "number": "001",
    "name": "Cardinal recruitment",
    "kind": "cardinal_recruitment",
    "question": "Can local recruitment stabilize convergence?",
    "ticks": 5,
    "figures": ["T", "T-up"],
    "colours": [1, 2],
    "max_origins": 1,
    "architecture": {
        "world_size": 12,
        "side": 8,
        "cluster": 4,
        "seed": 1,
        "learning": {"rate": 0.05, "commitment": 0.2, "floor": 0.01},
    },
    "epochs": 1,
    "parameters": {},
}


def read(run, name):
    return json.loads((run / name).read_text())


@pytest.fixture
def run(tmp_path):
    return execute(dict(DEFINITION), tmp_path)


def test_a_run_writes_the_complete_artifact(run):
    for name in (
        "definition.json",
        "manifest.json",
        "summary.json",
        "connectivity.json",
        "snapshots.json",
        "responses.npz",
    ):
        assert (run / name).exists(), name


def test_the_definition_determines_run_identity():
    assert digest(DEFINITION) == digest(dict(DEFINITION))
    assert digest(DEFINITION) != digest(dict(DEFINITION, ticks=6))


def test_the_artifact_declares_only_the_ncl_column_network(run):
    manifest = read(run, "manifest.json")
    wiring = read(run, "connectivity.json")["connectivity"]
    assert manifest["contract"] == "ncl-column-network-v1"
    assert wiring["model"] == "ncl-column-network-v1"
    assert set(wiring["populations"]) == {"shape", "colour", "concept"}
    assert wiring["populations"]["concept"]["sources"] == ["shape", "colour"]


def test_the_run_reports_recruitment_and_bidirectional_partial_cues(run):
    summary = read(run, "summary.json")
    assert "concept" in summary["recruitment"]["cardinal_candidates"]
    completion = summary["completion"]
    assert set(completion) == {
        "shape_cue_concept_similarity",
        "shape_cue_reinstated_colour",
        "colour_cue_concept_similarity",
        "colour_cue_reinstated_shape",
    }
    assert all(0.0 <= value <= 1.0 for value in completion.values())


def test_every_figure_part_reaches_the_network(run):
    presentation = read(run, "summary.json")["presentation"]
    assert presentation["samples_per_figure"] == 7


def test_responses_are_saved_with_stable_column_labels(run):
    data = np.load(run / "responses.npz", allow_pickle=False)
    assert data["responses"].shape[-1] == data["labels"].size
    assert all("." in str(label) for label in data["labels"])


def test_an_unknown_experiment_kind_is_refused(tmp_path):
    with pytest.raises(KeyError):
        execute(dict(DEFINITION, kind="haruspicy"), tmp_path)


def test_an_unknown_parameter_is_refused(tmp_path):
    with pytest.raises(KeyError):
        execute(dict(DEFINITION, parameters={"recurrant_gain": 0.5}), tmp_path)
