"""Detailed laminar cortical-column circuit behavior."""

from __future__ import annotations

import copy

import numpy as np
import pytest

from ccf6.cortical_circuit import CorticalCircuit, default_cortical_definition
from ccf6.cortical_processes import run_cortical_process


def circuit_definition() -> dict:
    definition = default_cortical_definition(seed=20260910)
    definition["hierarchy"] = {
        "lower_columns": 5,
        "middle_columns": 3,
        "higher_columns": 2,
        "lateral_radius": 1,
        "ascending_fan_out": 2,
    }
    return definition


def test_constructs_multiple_laminar_columns_with_named_neural_populations():
    circuit = CorticalCircuit.from_definition(circuit_definition())

    topology = circuit.topology_snapshot()

    assert topology["hierarchy"] == {
        "lower": ["A", "B", "C", "D", "E"],
        "middle": ["M1", "M2", "M3"],
        "higher": ["H1", "H2"],
    }
    assert topology["columns"]["A"]["populations"] == [
        "A.L23Tuft",
        "A.L5Tuft",
        "A.L23Pyr",
        "A.L4Pyr",
        "A.L5Pyr",
        "A.L6Pyr",
        "A.PV4",
        "A.PV23",
        "A.PV5",
        "A.SOM23",
        "A.SOM5",
        "A.VIP",
    ]
    assert topology["populations"]["A.L4Pyr"]["legacy_name"] == "A4"
    assert topology["populations"]["A.SOM23"]["legacy_name"] == "ASOM"
    assert topology["populations"]["A.L23Tuft"]["target_compartment"] == "apical_dendrite"
    assert topology["populations"]["A.PV23"]["target_compartment"] == "soma"
    assert any(
        pathway["source"] == "thal"
        and pathway["target"] == "A.L4Pyr"
        and pathway["route"] == "Input"
        for pathway in topology["pathways"]
    )
    assert any(
        pathway["source"] == "A.VIP"
        and pathway["target"] == "A.SOM23"
        and pathway["effect"] == "inhibitory"
        for pathway in topology["pathways"]
    )


def test_rejects_a_hierarchy_with_fewer_than_five_lower_columns():
    definition = circuit_definition()
    definition["hierarchy"]["lower_columns"] = 4

    with pytest.raises(ValueError, match="at least 5 lower cortical Columns"):
        CorticalCircuit.from_definition(definition)


@pytest.mark.parametrize(
    ("level", "count", "message"),
    [
        ("middle_columns", 1, "at least 2 middle cortical Columns"),
        ("higher_columns", 1, "at least 2 higher cortical Columns"),
    ],
)
def test_rejects_a_hierarchy_without_multiple_association_columns(
    level: str,
    count: int,
    message: str,
):
    definition = circuit_definition()
    definition["hierarchy"][level] = count

    with pytest.raises(ValueError, match=message):
        CorticalCircuit.from_definition(definition)


def test_thalamic_activity_reaches_l4_and_fast_pv_before_pv_suppresses_l4():
    full = run_cortical_process(
        circuit_definition(),
        process="Input",
        ticks=35,
        external_drives={"thal": 1.0},
    )
    without_pv = run_cortical_process(
        circuit_definition(),
        process="Input",
        ticks=35,
        external_drives={"thal": 1.0},
        disabled_routes=("Pv",),
    )

    assert full.activity["A.PV4"] > 0.25
    assert full.activity["A.L4Pyr"] > 0.0
    assert full.activity["A.L4Pyr"] < without_pv.activity["A.L4Pyr"]
    assert full.pathway_flux["thal-to-A.L4Pyr"] > 0.0
    assert full.pathway_flux["A.PV4-to-A.L4Pyr"] < 0.0


def test_rejects_external_activity_outside_the_normalized_range():
    circuit = CorticalCircuit.from_definition(circuit_definition())

    with pytest.raises(ValueError, match="external drive must be in \\[0,1\\]"):
        circuit.tick({"thal": 1.1})


def test_tick_uses_one_immutable_prior_state_for_every_population():
    circuit = CorticalCircuit.from_definition(circuit_definition())

    first = circuit.tick({"thal": 1.0}, active_routes={"Input", "Pv"})
    second = circuit.tick({"thal": 1.0}, active_routes={"Input", "Pv"})

    assert first.activity["thal"] > 0.0
    assert first.activity["A.L4Pyr"] == 0.0
    assert second.activity["A.L4Pyr"] > 0.0
    assert second.activity["A.PV4"] > 0.0


def test_confirmed_hebbian_activity_strengthens_three_distinct_connection_factors():
    circuit = CorticalCircuit.from_definition(circuit_definition())
    pathway_id = "thal-to-A.L4Pyr"
    for _ in range(20):
        circuit.tick({"thal": 1.0}, active_routes={"Input"})
    before = circuit.pathway_state(pathway_id)

    learning = circuit.apply_success_signal(1.0, presentation_id="presentation-1")
    after = circuit.pathway_state(pathway_id)

    assert learning.adaptation_applied is True
    assert after["release_facilitation"] > before["release_facilitation"]
    assert after["postsynaptic_receptiveness"] > before["postsynaptic_receptiveness"]
    assert after["terminal_boutons"] > before["terminal_boutons"]
    assert after["axonal_branches"] > before["axonal_branches"]
    assert after["dendritic_spines"] > before["dendritic_spines"]
    assert after["structural_contacts"] > before["structural_contacts"]
    assert after["effective_strength"] > before["effective_strength"]


def test_unconfirmed_hebbian_activity_does_not_change_connection_strength():
    circuit = CorticalCircuit.from_definition(circuit_definition())
    for _ in range(20):
        circuit.tick({"thal": 1.0}, active_routes={"Input"})
    before = copy.deepcopy(circuit.pathway_state("thal-to-A.L4Pyr"))

    learning = circuit.apply_success_signal(0.0, presentation_id="presentation-1")

    assert learning.adaptation_applied is False
    assert circuit.pathway_state("thal-to-A.L4Pyr") == before


def test_same_seed_produces_identical_activity_and_pathway_state():
    first = CorticalCircuit.from_definition(circuit_definition())
    second = CorticalCircuit.from_definition(circuit_definition())

    for _ in range(12):
        first.tick({"thal": 0.8, "attention": 0.4})
        second.tick({"thal": 0.8, "attention": 0.4})

    np.testing.assert_array_equal(first.activity_vector(), second.activity_vector())
    assert first.pathway_state("thal-to-A.L4Pyr") == second.pathway_state(
        "thal-to-A.L4Pyr"
    )


def test_different_seeds_produce_different_initial_pathway_strengths():
    first = CorticalCircuit.from_definition(circuit_definition())
    changed = circuit_definition()
    changed["seed"] = 20260911
    second = CorticalCircuit.from_definition(changed)

    assert first.pathway_state("thal-to-A.L4Pyr")["base_strength"] != second.pathway_state(
        "thal-to-A.L4Pyr"
    )["base_strength"]


def test_intracolumnar_flow_reaches_each_pyramidal_layer_in_causal_order():
    result = run_cortical_process(
        circuit_definition(),
        process="Flow",
        ticks=24,
        external_drives={"A.L4Pyr": 1.0},
    )
    index = {label: position for position, label in enumerate(result.labels)}

    def first_active(label: str) -> int:
        values = result.trajectory[:, index[label]]
        return int(np.flatnonzero(values > 0.001)[0])

    assert first_active("A.L4Pyr") < first_active("A.L23Pyr")
    assert first_active("A.L23Pyr") < first_active("A.L5Pyr")
    assert first_active("A.L5Pyr") < first_active("A.L6Pyr")
    assert result.activity["motor"] > 0.0


def test_ascending_activity_reaches_multiple_middle_columns():
    result = run_cortical_process(
        circuit_definition(),
        process="Ascend",
        ticks=20,
        external_drives={"A.L23Pyr": 1.0},
    )

    active_middle_inputs = [
        result.activity[f"{column}.L4Pyr"] for column in ("M1", "M2", "M3")
    ]
    assert sum(value > 0.0 for value in active_middle_inputs) == 2


def test_top_down_activity_enters_apical_tuft_before_reaching_pyramidal_soma():
    result = run_cortical_process(
        circuit_definition(),
        process="Topdown",
        ticks=20,
        external_drives={"H1.L23Pyr": 1.0},
    )
    index = {label: position for position, label in enumerate(result.labels)}
    tuft = result.trajectory[:, index["M1.L23Tuft"]]
    soma = result.trajectory[:, index["M1.L23Pyr"]]

    assert int(np.flatnonzero(tuft > 0.001)[0]) < int(np.flatnonzero(soma > 0.001)[0])
    assert result.activity["M1.L6Pyr"] > 0.0


def test_vip_activity_disinhibits_an_apical_tuft_by_suppressing_som():
    with_vip = run_cortical_process(
        circuit_definition(),
        process="Vip",
        ticks=45,
        external_drives={
            "attention": 1.0,
            "M1.L23Pyr": 0.8,
            "A.SOM23": 0.55,
        },
    )
    without_vip = run_cortical_process(
        circuit_definition(),
        process="Vip",
        ticks=45,
        external_drives={
            "attention": 1.0,
            "M1.L23Pyr": 0.8,
            "A.SOM23": 0.55,
        },
        disabled_routes=("Vip",),
    )

    assert with_vip.activity["A.SOM23"] < without_vip.activity["A.SOM23"]
    assert with_vip.activity["A.L23Tuft"] > without_vip.activity["A.L23Tuft"]


def test_stronger_column_recruits_more_inhibition_in_its_neighbor():
    result = run_cortical_process(
        circuit_definition(),
        process="Competition",
        ticks=40,
        external_drives={"A.L23Pyr": 1.0, "B.L23Pyr": 0.65},
    )
    control = run_cortical_process(
        circuit_definition(),
        process="Competition",
        ticks=40,
        external_drives={"A.L23Pyr": 1.0, "B.L23Pyr": 0.65},
        disabled_routes=("Lateral",),
    )

    assert result.activity["B.PV23"] > control.activity["B.PV23"]
    assert result.activity["B.SOM23"] > control.activity["B.SOM23"]
    assert result.activity["B.L23Pyr"] < control.activity["B.L23Pyr"]
