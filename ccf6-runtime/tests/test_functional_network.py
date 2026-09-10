"""Normative mechanics of the NCL Functional Web Network."""

from __future__ import annotations

import copy
import json

import numpy as np
import pytest

from ccf6.experiment import execute
from ccf6.functional_network import Network


def definition() -> dict:
    return {
        "seed": 20260910,
        "populations": [
            {
                "id": "visual-feature",
                "columns": 6,
                "provenance": "generated visual properties",
                "wiring_role": "sensory input",
                "inhibition": {"radius": 1, "strength": 0.2},
            },
            {
                "id": "visual-association",
                "columns": 4,
                "provenance": "latent association population",
                "wiring_role": "association",
                "inhibition": {"radius": 1, "strength": 0.2},
            },
        ],
        "projections": [
            {
                "id": "visual-feature-to-association",
                "source": "visual-feature",
                "target": "visual-association",
                "fan_in": 3,
                "initialization": {
                    "distribution": "uniform",
                    "low": 0.1,
                    "high": 0.3,
                },
                "incoming_norm": 1.0,
            }
        ],
        "thresholds": {
            "distribution": "uniform",
            "low": 0.35,
            "high": 0.55,
            "minimum": 0.2,
            "maximum": 0.8,
        },
        "dynamics": {
            "dt": 0.1,
            "tau_input": 0.3,
            "tau_integration": 0.4,
            "tau_output": 0.5,
            "recurrent_gain": 0.25,
            "temperature": 0.1,
            "transmission_cutoff": 0.05,
        },
        "settling": {"epsilon": 0.0001, "stable_ticks": 3, "max_ticks": 200},
    }


def one_population_definition() -> dict:
    declared = definition()
    declared["populations"] = [
        {
            "id": "visual-feature",
            "columns": 2,
            "provenance": "generated visual properties",
            "wiring_role": "sensory input",
            "inhibition": {"radius": 1, "strength": 0.0},
        }
    ]
    declared["projections"] = []
    return declared


def test_reset_has_zero_activity():
    network = Network(definition())
    network.tick({"visual-feature": np.ones(6)})

    network.reset()

    snapshot = network.snapshot()
    for population in snapshot["populations"].values():
        assert population["input"] == [0.0] * len(population["input"])
        assert population["integration"] == [0.0] * len(
            population["integration"]
        )
        assert population["output"] == [0.0] * len(population["output"])


def test_compartments_follow_normative_equations_synchronously():
    network = Network(one_population_definition())
    population = network.populations["visual-feature"]
    population.input[:] = [0.2, 0.4]
    population.integration[:] = [0.3, 0.5]
    population.output[:] = [0.1, 0.7]
    population.thresholds[:] = [0.4, 0.6]

    network.tick({"visual-feature": np.array([1.0, 0.0])})

    input_alpha = 1.0 - np.exp(-0.1 / 0.3)
    integration_alpha = 1.0 - np.exp(-0.1 / 0.4)
    output_alpha = 1.0 - np.exp(-0.1 / 0.5)
    np.testing.assert_allclose(
        population.input,
        [0.2 + (1.0 - 0.2) * input_alpha, 0.4 + (0.0 - 0.4) * input_alpha],
    )
    np.testing.assert_allclose(
        population.integration,
        [
            0.3 + (0.2 + 0.25 * 0.3 - 0.3) * integration_alpha,
            0.5 + (0.4 + 0.25 * 0.5 - 0.5) * integration_alpha,
        ],
    )
    responses = 1.0 / (1.0 + np.exp(-((np.array([0.3, 0.5]) - [0.4, 0.6]) / 0.1)))
    np.testing.assert_allclose(
        population.output,
        np.array([0.1, 0.7]) + (responses - [0.1, 0.7]) * output_alpha,
    )


def test_output_is_graded_around_threshold():
    network = Network(one_population_definition())
    population = network.populations["visual-feature"]
    population.integration[:] = [0.3, 0.5]
    population.thresholds[:] = [0.4, 0.4]

    network.tick()

    assert 0.0 < population.output[0] < population.output[1] < 1.0


def test_transmission_cutoff_does_not_change_stored_output():
    network = Network(one_population_definition())
    population = network.populations["visual-feature"]
    population.output[:] = [0.049, 0.05]

    broadcast = network.broadcast(population)

    np.testing.assert_array_equal(broadcast, [0.0, 0.05])
    np.testing.assert_array_equal(population.output, [0.049, 0.05])


def test_local_inhibition_uses_prior_output_in_the_integration_equation():
    declared = one_population_definition()
    declared["populations"][0]["inhibition"]["strength"] = 0.2
    network = Network(declared)
    population = network.populations["visual-feature"]
    population.input[:] = [0.5, 0.5]
    population.integration[:] = [0.4, 0.4]
    population.output[:] = [0.8, 0.2]

    network.tick()

    alpha = 1.0 - np.exp(-0.1 / 0.4)
    np.testing.assert_allclose(
        population.integration,
        [
            0.4 + (0.5 + 0.25 * 0.4 - 0.2 * 0.2 - 0.4) * alpha,
            0.4 + (0.5 + 0.25 * 0.4 - 0.2 * 0.8 - 0.4) * alpha,
        ],
    )


def test_population_iteration_order_cannot_change_a_tick():
    first = Network(definition())
    second = Network(definition())
    second.populations = dict(reversed(second.populations.items()))
    sensory = {"visual-feature": np.linspace(0.0, 1.0, 6)}

    for _ in range(5):
        first.tick(sensory)
        second.tick(sensory)

    first_state = first.snapshot()["populations"]
    second_state = second.snapshot()["populations"]
    for identifier in first_state:
        for compartment in ("input", "integration", "output"):
            np.testing.assert_array_equal(
                first_state[identifier][compartment],
                second_state[identifier][compartment],
            )


def test_reciprocal_routes_have_independent_weights():
    network = Network(definition())
    projection = network.projections[0]

    assert projection.sources.size == 12
    assert projection.targets.size == 12
    np.testing.assert_array_equal(np.bincount(projection.targets), [3, 3, 3, 3])
    assert not np.array_equal(
        projection.ascending_weights,
        projection.descending_weights,
    )
    np.testing.assert_array_equal(projection.ascending_eligibility, np.zeros(12))
    np.testing.assert_array_equal(projection.descending_eligibility, np.zeros(12))
    np.testing.assert_allclose(
        np.bincount(
            projection.targets,
            weights=projection.ascending_weights,
        ),
        np.ones(4),
    )
    descending_norms = np.bincount(
        projection.sources,
        weights=projection.descending_weights,
        minlength=6,
    )
    np.testing.assert_allclose(descending_norms[descending_norms > 0.0], 1.0)


def test_activity_travels_both_directions_over_reciprocal_endpoints():
    network = Network(definition())
    projection = network.projections[0]
    network.populations[projection.source].output[:] = 1.0

    network.tick()

    assert network.populations[projection.target].input.sum() > 0.0

    network.reset()
    network.populations[projection.target].output[:] = 1.0

    network.tick()

    assert network.populations[projection.source].integration.sum() > 0.0


def test_settling_requires_stable_output():
    declared = one_population_definition()
    declared["settling"] = {"epsilon": 1.0, "stable_ticks": 3, "max_ticks": 10}
    network = Network(declared)

    result = network.settle({"visual-feature": np.ones(2)})

    assert result.success is True
    assert result.ticks == 3
    assert result.stable_ticks == 3
    assert result.max_ticks_reached is False


def test_reaching_max_ticks_is_a_recorded_settling_failure():
    declared = one_population_definition()
    declared["settling"] = {"epsilon": 1.0, "stable_ticks": 3, "max_ticks": 2}
    network = Network(declared)

    result = network.settle({"visual-feature": np.ones(2)})

    assert result.success is False
    assert result.ticks == 2
    assert result.stable_ticks == 2
    assert result.max_ticks_reached is True


def test_every_population_uses_the_same_column_mechanics():
    network = Network(definition())

    assert len({type(population) for population in network.populations.values()}) == 1
    assert all(
        set(network.snapshot()["populations"][identifier])
        == {
            "provenance",
            "wiring_role",
            "thresholds",
            "input",
            "integration",
            "output",
        }
        for identifier in network.populations
    )


def test_semantic_and_cardinal_population_flags_are_refused():
    declared = definition()
    declared["populations"][0]["cardinal"] = True

    with pytest.raises(ValueError, match="unknown.*cardinal"):
        Network(declared)


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value["projections"][0].update(fan_in=6),
        lambda value: value["projections"][0]["initialization"].update(
            distribution="normal"
        ),
        lambda value: value["projections"][0].update(incoming_norm=0.0),
        lambda value: value["populations"][0]["inhibition"].update(radius=6),
        lambda value: value["thresholds"].update(low=0.9),
        lambda value: value["dynamics"].update(temperature=0.0),
        lambda value: value["settling"].update(epsilon=0.0),
    ),
    ids=(
        "fan-in",
        "initialization distribution",
        "incoming norm",
        "inhibition radius",
        "threshold bounds",
        "dynamics constant",
        "settling constant",
    ),
)
def test_required_topology_and_dynamics_declarations_are_validated(mutation):
    declared = copy.deepcopy(definition())
    mutation(declared)

    with pytest.raises(ValueError):
        Network(declared)


def experiment_definition() -> dict:
    network_definition = definition()
    network_definition["populations"][0]["columns"] = 12
    network_definition["populations"][1]["columns"] = 8
    network_definition["projections"][0]["fan_in"] = 4
    return {
        "number": "003",
        "name": "Zero-rest reciprocal Network",
        "kind": "zero_rest_network",
        "question": "Do ordinary Columns settle under the normative equations?",
        "seed": 20260910,
        "network": network_definition,
        "stimulus": {
            "category_id": "category-1",
            "population_id": "visual-feature",
        },
    }


def test_zero_rest_experiment_writes_reproducible_topology_and_activity(tmp_path):
    run = execute(experiment_definition(), tmp_path)

    manifest = json.loads((run / "manifest.json").read_text())
    summary = json.loads((run / "summary.json").read_text())
    topology = json.loads((run / "topology.json").read_text())
    activity = np.load(run / "activity.npz", allow_pickle=False)
    archived_topology = np.load(run / "topology.npz", allow_pickle=False)
    assert manifest["files"] == [
        "definition.json",
        "manifest.json",
        "dataset.json",
        "topology.npz",
        "topology.json",
        "activity.npz",
        "activity.json",
        "summary.json",
    ]
    assert summary["settling"]["success"] is True
    assert topology["projections"][0]["connections"] == 32
    assert len(topology["projections"][0]["endpoints"]) == 32
    np.testing.assert_array_equal(activity["initial_activity"], 0.0)
    assert activity["settled_activity"].shape == (20, 3)
    endpoints = topology["projections"][0]["endpoints"]
    np.testing.assert_array_equal(
        archived_topology["visual-feature-to-association.sources"],
        [edge["source_column"] for edge in endpoints],
    )
    np.testing.assert_allclose(
        archived_topology["visual-feature-to-association.ascending_weights"],
        [edge["ascending_weight"] for edge in endpoints],
    )
    np.testing.assert_allclose(
        archived_topology["visual-feature-to-association.descending_weights"],
        [edge["descending_weight"] for edge in endpoints],
    )
    np.testing.assert_array_equal(
        archived_topology["visual-feature-to-association.ascending_eligibility"],
        0.0,
    )


def test_max_tick_failure_is_preserved_in_the_activity_artifact(tmp_path):
    declared = experiment_definition()
    declared["network"]["settling"] = {
        "epsilon": 1.0,
        "stable_ticks": 3,
        "max_ticks": 2,
    }

    run = execute(declared, tmp_path)

    summary = json.loads((run / "summary.json").read_text())
    activity = np.load(run / "activity.npz", allow_pickle=False)
    assert summary["settling"]["success"] is False
    assert summary["settling"]["max_ticks_reached"] is True
    assert summary["settling"]["ticks"] == 2
    assert activity["trajectory"].shape == (3, 20, 3)
