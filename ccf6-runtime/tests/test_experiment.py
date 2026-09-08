"""The primary seam: a declared experiment runs to an artifact (ADR-0007).

Every behavioural claim about the foundation is asserted here, on what a run wrote.
The artifact is the unit of result, so a test that reads it is testing what the
workbench and a future reader will actually see.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from ccf6.experiment import digest, execute

BASELINE = {
    "number": "004",
    "name": "Structure baseline",
    "kind": "structure_baseline",
    "question": "With no learning, how selective does any Column become?",
    "ticks": 20,
    "architecture": {"world_size": 8, "levels": 2, "convergence_levels": 1, "seed": 1},
    "parameters": {},
}


@pytest.fixture
def run(tmp_path):
    return execute(dict(BASELINE), tmp_path)


def read(run, name):
    return json.loads((run / name).read_text())


def test_a_run_writes_the_artifact_a_reader_needs(run):
    for name in ("definition.json", "manifest.json", "summary.json",
                 "connectivity.json", "snapshots.json", "responses.npz"):
        assert (run / name).exists(), name


def test_the_definition_is_recorded_verbatim(run):
    assert read(run, "definition.json")["kind"] == "structure_baseline"


def test_a_runs_identity_is_its_definition():
    """Change the definition, change the run."""
    other = dict(BASELINE, ticks=21)
    assert digest(BASELINE) != digest(other)
    assert digest(BASELINE) == digest(dict(BASELINE))


def test_the_wiring_is_reported_by_the_code_that_built_it(run):
    wiring = read(run, "connectivity.json")["connectivity"]
    assert set(wiring["structures"]) == {"web", "schema", "index"}
    for space in wiring["web"]["spaces"].values():
        assert space["cortical_area"] in ("frontal", "parietal", "temporal")
        for level in space["levels"]:
            assert level["fan_in"] >= 1
            assert level["connections"] > 0


def test_no_column_draws_from_the_whole_population_below_it(run):
    wiring = read(run, "connectivity.json")["connectivity"]
    for space in wiring["web"]["spaces"].values():
        for level in space["levels"]:
            assert level["fan_in_max"] < level["columns"] or level["columns"] == 1


def test_the_baseline_reports_what_a_learning_rule_must_beat(run):
    summary = read(run, "summary.json")
    assert "shape_selectivity_max" in summary["overall"]
    assert "position_selectivity_max" in summary["overall"]
    assert summary["overall"]["columns"] > 0
    assert 0 <= summary["overall"]["silent_columns"] <= summary["overall"]["columns"]


def test_every_part_of_every_figure_reached_the_network(run):
    """A multi-part figure is presented as a sequence, and no part is dropped."""
    summary = read(run, "summary.json")
    assert summary["presentation"]["stops_per_figure"] == summary["presentation"]["parts_per_figure"]
    assert summary["presentation"]["relations_per_figure"] == (
        summary["presentation"]["stops_per_figure"] - 1
    )


def test_the_schema_separates_positions_and_is_path_consistent(run):
    """The two properties §3.2 requires, measured on the run rather than asserted."""
    schema = read(run, "summary.json")["schema"]
    assert schema["distinct_states"] == schema["positions_visited"]
    assert schema["path_consistency_error"] == pytest.approx(0.0, abs=1e-9)


def test_the_index_bound_one_entry_per_stop(run):
    index = read(run, "summary.json")["index"]
    assert index["entries"] == index["stops"]
    assert index["completion_accuracy"] >= 0.0


def test_a_structure_not_declared_is_not_built(tmp_path):
    definition = dict(BASELINE, architecture=dict(BASELINE["architecture"], structures=["web"]))
    run = execute(definition, tmp_path)
    wiring = read(run, "connectivity.json")["connectivity"]
    assert wiring["structures"] == ["web"]
    assert "schema" not in wiring and "index" not in wiring


def test_a_baseline_without_a_web_is_refused(tmp_path):
    """The measurement is over Columns, so a run with nothing to measure is an error."""
    definition = dict(BASELINE, architecture=dict(BASELINE["architecture"], structures=["schema"]))
    with pytest.raises(ValueError):
        execute(definition, tmp_path)


def test_an_unknown_experiment_kind_is_refused(tmp_path):
    with pytest.raises(KeyError):
        execute(dict(BASELINE, kind="haruspicy"), tmp_path)


def test_an_unknown_parameter_is_refused(tmp_path):
    with pytest.raises(KeyError):
        execute(dict(BASELINE, parameters={"recurrant_gain": 0.5}), tmp_path)


def test_responses_are_saved_with_labels_that_name_their_level(run):
    data = np.load(run / "responses.npz", allow_pickle=False)
    assert data["responses"].shape[-1] == data["labels"].size
    assert all("." in str(label) for label in data["labels"])
