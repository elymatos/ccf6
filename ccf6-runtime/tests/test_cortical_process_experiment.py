"""Artifact execution for explicit cortical-process simulations."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ccf6.artifacts import validate_cortical_circuit_artifact
from ccf6.cortical_circuit import default_cortical_definition
from ccf6.experiment import execute


def experiment_definition() -> dict:
    return {
        "number": "012",
        "name": "Detailed cortical process suite",
        "kind": "cortical_process_suite",
        "question": "Do named laminar populations expose causal cortical pathways?",
        "seed": 20260910,
        "circuit": default_cortical_definition(20260910),
        "processes": [
            {
                "id": "thalamocortical-input",
                "process": "Input",
                "ticks": 20,
                "external_drives": {"thal": 1.0},
                "control_disabled_routes": ["Pv"],
            },
            {
                "id": "hebbian-strengthening",
                "process": "Hebbian",
                "ticks": 20,
                "external_drives": {"A.L4Pyr": 1.0, "A.L23Pyr": 1.0},
                "success_signal": 1.0,
            },
        ],
    }


def test_writes_reproducible_topology_activity_and_process_evidence(tmp_path):
    definition = experiment_definition()

    first = execute(definition, tmp_path / "first")
    second = execute(definition, tmp_path / "second")

    first_manifest = json.loads((first / "manifest.json").read_text())
    second_manifest = json.loads((second / "manifest.json").read_text())
    summary = json.loads((first / "summary.json").read_text())
    activity = json.loads((first / "activity.json").read_text())
    topology = json.loads((first / "topology.json").read_text())

    assert first_manifest["contract"] == "ncl-cortical-circuit-v1"
    assert first_manifest["digest"] == second_manifest["digest"]
    assert summary["circuit"]["columns"] == 10
    assert summary["processes"]["total"] == 2
    assert summary["processes"]["with_controls"] == 1
    assert summary["learning"]["release_facilitation_changes"] > 0
    assert summary["learning"]["postsynaptic_receptiveness_changes"] > 0
    assert summary["learning"]["structural_growth_changes"] > 0
    assert set(activity["processes"]) == {
        "thalamocortical-input",
        "hebbian-strengthening",
    }
    assert topology["populations"]["A.PV4"]["kind"] == "pv"
    with np.load(first / "activity.npz", allow_pickle=False) as arrays:
        assert arrays["thalamocortical-input.trajectory"].shape == (21, 126)
        assert arrays["thalamocortical-input.pathway_flux_trajectory"].shape == (
            21,
            418,
        )
        assert arrays["hebbian-strengthening.trajectory"].shape == (21, 126)
    validation = validate_cortical_circuit_artifact(first)
    assert validation["populations"] == 126
    assert validation["pathways"] == 418
    assert validation["processes"] == 2


def test_declared_suite_runs_every_documented_pathway_and_process(tmp_path):
    definition_path = (
        Path(__file__).parents[2] / "experiments/012-detailed-cortical-circuit.json"
    )

    run = execute(json.loads(definition_path.read_text()), tmp_path)

    summary = json.loads((run / "summary.json").read_text())
    activity = json.loads((run / "activity.json").read_text())
    assert summary["processes"]["total"] == 20
    assert summary["processes"]["inventory"] == [
        "all-circuits",
        "thalamocortical-input",
        "intracolumnar-flow",
        "ascending-residual",
        "top-down-prediction",
        "lateral-competition",
        "pv-fast-gain",
        "som-dendritic-gate",
        "vip-disinhibition",
        "sensory-integration",
        "predictive-coding-loop",
        "winner-takes-most",
        "perisomatic-gain-control",
        "behavioral-state-ensemble",
        "attention",
        "arousal",
        "novelty",
        "reward",
        "sustained-pyramidal-activity",
        "hebbian-strengthening",
    ]
    assert summary["learning"]["stdp_enabled"] is False
    input_measurements = activity["processes"]["thalamocortical-input"][
        "measurements"
    ]
    assert input_measurements["peak_activity"] > 0.9
    assert input_measurements["peak_active_populations"] > 1
    assert input_measurements["control_maximum_activity_difference"] > 0.0
    sustained = activity["processes"]["sustained-pyramidal-activity"][
        "measurements"
    ]
    assert sustained["drive_removed_after_tick"] == 12
    assert sustained["final_activity_norm"] < sustained["peak_activity_norm"]
