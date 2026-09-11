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


def learning_definition() -> dict:
    declared = definition()
    declared["projections"][0]["incoming_norm"] = 0.4
    declared["plasticity"] = {
        "eligibility_decay": 0.5,
        "learning_rate": 0.2,
    }
    return declared


def adaptive_definition() -> dict:
    declared = learning_definition()
    declared["adaptation"] = {
        "activity_average_rate": 0.25,
        "threshold_rate": 0.1,
        "target_activity": 0.4,
        "recruitment_threshold": 0.1,
        "minimum_presentations": 2,
    }
    return declared


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
    network.projections[0].ascending_eligibility.fill(1.0)
    network.projections[0].descending_eligibility.fill(1.0)

    network.reset()

    snapshot = network.snapshot()
    for population in snapshot["populations"].values():
        assert population["input"] == [0.0] * len(population["input"])
        assert population["integration"] == [0.0] * len(
            population["integration"]
        )
        assert population["output"] == [0.0] * len(population["output"])
    np.testing.assert_array_equal(
        network.projections[0].ascending_eligibility,
        0.0,
    )
    np.testing.assert_array_equal(
        network.projections[0].descending_eligibility,
        0.0,
    )


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


def test_lesion_suppresses_output_but_preserves_incoming_activity():
    network = Network(one_population_definition())

    with network.lesion(("visual-feature#0",)):
        result = network.settle({"visual-feature": np.asarray([1.0, 0.0])})

    assert result.success is True
    assert result.activity[-1, 0, 0] > 0.0
    assert result.activity[-1, 0, 1] > 0.0
    assert result.activity[-1, 0, 2] == 0.0
    assert result.activity[-1, 1, 2] > 0.0

    network.reset()
    unlesioned = network.settle({"visual-feature": np.asarray([1.0, 0.0])})
    assert unlesioned.activity[-1, 0, 2] > 0.0


def test_stimulation_clamps_declared_outputs_without_sensory_input():
    network = Network(one_population_definition())
    network.reset()

    with network.stimulate({"visual-feature#0": 0.63}):
        for _ in range(5):
            network.tick()
            assert network.populations["visual-feature"].output[0] == 0.63
        assert network.populations["visual-feature"].input[0] == 0.0

    network.tick()
    assert network.populations["visual-feature"].output[0] != 0.63


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


def test_eligibility_follows_bounded_decay_and_endpoint_coactivity():
    network = Network(learning_definition())
    projection = network.projections[0]
    source = network.populations[projection.source]
    target = network.populations[projection.target]
    projection.ascending_eligibility.fill(0.9)
    projection.descending_eligibility.fill(0.9)
    source.output[:] = np.linspace(0.1, 1.0, source.columns)
    source.integration[:] = np.linspace(0.2, 0.9, source.columns)
    target.output[:] = np.linspace(0.3, 1.0, target.columns)
    target.integration[:] = np.linspace(0.4, 1.0, target.columns)
    expected_ascending = np.clip(
        0.5 * 0.9
        + source.output[projection.sources]
        * target.integration[projection.targets],
        0.0,
        1.0,
    )
    expected_descending = np.clip(
        0.5 * 0.9
        + target.output[projection.targets]
        * source.integration[projection.sources],
        0.0,
        1.0,
    )

    network.tick()

    np.testing.assert_allclose(
        projection.ascending_eligibility,
        expected_ascending,
    )
    np.testing.assert_allclose(
        projection.descending_eligibility,
        expected_descending,
    )
    assert np.any(expected_ascending == 1.0)
    assert np.any(expected_descending == 1.0)


def test_only_success_confirms_eligible_connections():
    unsuccessful = Network(learning_definition())
    unsuccessful.settle({"visual-feature": np.ones(6)})
    unsuccessful_projection = unsuccessful.projections[0]
    unsuccessful_pre_ascending = unsuccessful_projection.ascending_weights.copy()
    unsuccessful_pre_descending = unsuccessful_projection.descending_weights.copy()

    unsuccessful_learning = unsuccessful.apply_success_signal(0.0)

    np.testing.assert_array_equal(
        unsuccessful_projection.ascending_weights,
        unsuccessful_pre_ascending,
    )
    np.testing.assert_array_equal(
        unsuccessful_projection.descending_weights,
        unsuccessful_pre_descending,
    )
    assert unsuccessful_learning.success_signal == 0.0

    successful = Network(learning_definition())
    successful.settle({"visual-feature": np.ones(6)})
    successful_projection = successful.projections[0]
    successful_pre_ascending = successful_projection.ascending_weights.copy()
    successful_pre_descending = successful_projection.descending_weights.copy()

    successful_learning = successful.apply_success_signal(1.0)

    assert not np.array_equal(
        successful_projection.ascending_weights,
        successful_pre_ascending,
    )
    assert not np.array_equal(
        successful_projection.descending_weights,
        successful_pre_descending,
    )
    assert successful_learning.success_signal == 1.0


def test_directional_learning_uses_its_own_eligibility_and_local_normalization():
    network = Network(learning_definition())
    network.settle({"visual-feature": np.linspace(0.1, 1.0, 6)})
    projection = network.projections[0]
    projection.ascending_eligibility[:] = np.linspace(0.1, 0.7, 12)
    projection.descending_eligibility[:] = np.linspace(0.8, 0.2, 12)

    result = network.apply_success_signal(1.0).projections[0]

    def expected_weights(
        weights: np.ndarray,
        eligibility: np.ndarray,
        destinations: np.ndarray,
    ) -> np.ndarray:
        updated = np.clip(weights + 0.2 * eligibility * (1.0 - weights), 0.0, 1.0)
        expected = updated.copy()
        for destination in np.unique(destinations):
            incoming = destinations == destination
            expected[incoming] *= (
                projection.incoming_norm / updated[incoming].sum()
            )
        return expected

    np.testing.assert_allclose(
        result.post_ascending_weights,
        expected_weights(
            result.pre_ascending_weights,
            result.ascending_eligibility,
            projection.targets,
        ),
    )
    np.testing.assert_allclose(
        result.post_descending_weights,
        expected_weights(
            result.pre_descending_weights,
            result.descending_eligibility,
            projection.sources,
        ),
    )
    assert not np.array_equal(
        result.ascending_eligibility,
        result.descending_eligibility,
    )
    assert not np.array_equal(
        result.post_ascending_weights - result.pre_ascending_weights,
        result.post_descending_weights - result.pre_descending_weights,
    )
    assert np.all(
        (0.0 <= result.post_ascending_weights)
        & (result.post_ascending_weights <= 1.0)
    )
    assert np.all(
        (0.0 <= result.post_descending_weights)
        & (result.post_descending_weights <= 1.0)
    )


def test_success_signal_is_rejected_before_settling_or_after_confirmation():
    network = Network(learning_definition())

    with pytest.raises(RuntimeError, match="successfully settled"):
        network.apply_success_signal(1.0)

    network.settle({"visual-feature": np.ones(6)})
    network.apply_success_signal(1.0)

    with pytest.raises(RuntimeError, match="already been applied"):
        network.apply_success_signal(1.0)


def test_entrenchment_uses_confirmed_incoming_eligibility():
    network = Network(adaptive_definition())
    network.settle({"visual-feature": np.ones(6)})

    result = network.apply_success_signal(1.0, "presentation-1")

    expected = {
        identifier: np.zeros(population.columns)
        for identifier, population in network.populations.items()
    }
    for learned, projection in zip(
        result.projections,
        network.projections,
        strict=True,
    ):
        np.maximum.at(
            expected[projection.target],
            projection.targets,
            learned.ascending_eligibility,
        )
        np.maximum.at(
            expected[projection.source],
            projection.sources,
            learned.descending_eligibility,
        )
    for population in result.populations:
        np.testing.assert_allclose(
            population.post_entrenchment - population.pre_entrenchment,
            expected[population.identifier],
        )
        assert all(
            contributors == ({"presentation-1"} if confirmed > 0.0 else set())
            for contributors, confirmed in zip(
                network.populations[
                    population.identifier
                ].contributing_presentations,
                expected[population.identifier],
                strict=True,
            )
        )


def test_one_presentation_cannot_recruit_by_itself():
    network = Network(adaptive_definition())
    network.settle({"visual-feature": np.ones(6)})

    first = network.apply_success_signal(1.0, "presentation-1")

    assert any(
        np.any(population.post_entrenchment > 0.0)
        for population in first.populations
    )
    assert all(
        np.all(population.post_contributor_counts <= 1)
        for population in first.populations
    )
    assert not any(np.any(population.recruited) for population in first.populations)

    network.reset()
    network.settle({"visual-feature": np.ones(6)})

    repeated = network.apply_success_signal(1.0, "presentation-1")

    assert not any(np.any(population.recruited) for population in repeated.populations)

    network.reset()
    network.settle({"visual-feature": np.ones(6)})

    second = network.apply_success_signal(1.0, "presentation-2")

    assert any(np.any(population.recruited) for population in second.populations)
    assert "cardinal" not in json.dumps(network.snapshot()).lower()

    high_threshold = adaptive_definition()
    high_threshold["adaptation"]["recruitment_threshold"] = 10.0
    network = Network(high_threshold)
    for presentation_id in ("presentation-1", "presentation-2"):
        network.reset()
        network.settle({"visual-feature": np.ones(6)})
        below_threshold = network.apply_success_signal(1.0, presentation_id)

    assert any(
        np.any(population.post_contributor_counts >= 2)
        for population in below_threshold.populations
    )
    assert not any(
        np.any(population.recruited) for population in below_threshold.populations
    )


def test_homeostasis_is_local_and_independent_of_success():
    successful = Network(adaptive_definition())
    unsuccessful = Network(adaptive_definition())
    sensory = {"visual-feature": np.ones(6)}
    successful.settle(sensory)
    unsuccessful.settle(sensory)
    initial_thresholds = {
        identifier: population.thresholds.copy()
        for identifier, population in successful.populations.items()
    }

    successful_result = successful.apply_success_signal(1.0, "presentation-1")
    unsuccessful_result = unsuccessful.apply_success_signal(0.0, "presentation-1")

    for successful_population, unsuccessful_population in zip(
        successful_result.populations,
        unsuccessful_result.populations,
        strict=True,
    ):
        expected_average = 0.25 * successful_population.settled_output
        expected_thresholds = np.clip(
            initial_thresholds[successful_population.identifier]
            + 0.1 * (expected_average - 0.4),
            0.2,
            0.8,
        )
        np.testing.assert_allclose(
            successful_population.post_activity_average,
            expected_average,
        )
        np.testing.assert_allclose(
            successful_population.post_thresholds,
            expected_thresholds,
        )
        np.testing.assert_array_equal(
            successful_population.post_activity_average,
            unsuccessful_population.post_activity_average,
        )
        np.testing.assert_array_equal(
            successful_population.post_thresholds,
            unsuccessful_population.post_thresholds,
        )


def test_homeostatic_thresholds_preserve_declared_bounds():
    network = Network(adaptive_definition())
    network.settle({"visual-feature": np.ones(6)})
    population = network.populations["visual-feature"]
    population.thresholds[:2] = [0.2, 0.8]
    population.activity_average[:2] = [0.0, 1.0]
    population.output[:2] = [0.0, 1.0]

    result = network.apply_success_signal(0.0, "presentation-1")

    visual = next(
        population
        for population in result.populations
        if population.identifier == "visual-feature"
    )
    np.testing.assert_array_equal(visual.post_thresholds[:2], [0.2, 0.8])


def test_activity_reset_preserves_all_durable_column_and_connection_state():
    network = Network(adaptive_definition())
    network.settle({"visual-feature": np.ones(6)})
    network.apply_success_signal(1.0, "presentation-1")
    durable_before = {
        identifier: (
            population.thresholds.copy(),
            population.activity_average.copy(),
            population.entrenchment.copy(),
            tuple(frozenset(values) for values in population.contributing_presentations),
        )
        for identifier, population in network.populations.items()
    }
    weights_before = [
        (
            projection.sources.copy(),
            projection.targets.copy(),
            projection.ascending_weights.copy(),
            projection.descending_weights.copy(),
        )
        for projection in network.projections
    ]

    network.reset()

    for identifier, population in network.populations.items():
        thresholds, average, entrenchment, contributors = durable_before[identifier]
        np.testing.assert_array_equal(population.thresholds, thresholds)
        np.testing.assert_array_equal(population.activity_average, average)
        np.testing.assert_array_equal(population.entrenchment, entrenchment)
        assert tuple(
            frozenset(values) for values in population.contributing_presentations
        ) == contributors
    for projection, before in zip(network.projections, weights_before, strict=True):
        sources, targets, ascending, descending = before
        np.testing.assert_array_equal(projection.sources, sources)
        np.testing.assert_array_equal(projection.targets, targets)
        np.testing.assert_array_equal(projection.ascending_weights, ascending)
        np.testing.assert_array_equal(projection.descending_weights, descending)


def test_evaluation_freezes_every_durable_adaptation():
    network = Network(adaptive_definition())
    network.settle({"visual-feature": np.ones(6)})
    network.apply_success_signal(1.0, "presentation-1")
    network.freeze_adaptation()
    network.reset()
    network.settle({"visual-feature": np.ones(6)})

    frozen = network.apply_success_signal(1.0, "evaluation-1")

    assert frozen.adaptation_applied is False
    for projection in frozen.projections:
        np.testing.assert_array_equal(
            projection.post_ascending_weights,
            projection.pre_ascending_weights,
        )
        np.testing.assert_array_equal(
            projection.post_descending_weights,
            projection.pre_descending_weights,
        )
    for population in frozen.populations:
        np.testing.assert_array_equal(
            population.post_thresholds,
            population.pre_thresholds,
        )
        np.testing.assert_array_equal(
            population.post_activity_average,
            population.pre_activity_average,
        )
        np.testing.assert_array_equal(
            population.post_entrenchment,
            population.pre_entrenchment,
        )


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
            "activity_average",
            "entrenchment",
            "contributing_presentations",
            "recruited",
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
        lambda value: value.update(
            plasticity={"eligibility_decay": 1.1, "learning_rate": 0.05}
        ),
        lambda value: value.update(
            plasticity={"eligibility_decay": 0.5, "learning_rate": 0.0}
        ),
        lambda value: value.update(
            adaptation={
                "activity_average_rate": 0.2,
                "threshold_rate": 0.1,
                "target_activity": 0.4,
                "recruitment_threshold": 1.0,
                "minimum_presentations": 2,
            }
        ),
        lambda value: value.update(
            plasticity={"eligibility_decay": 0.5, "learning_rate": 0.1},
            adaptation={
                "activity_average_rate": 1.1,
                "threshold_rate": 0.1,
                "target_activity": 0.4,
                "recruitment_threshold": 1.0,
                "minimum_presentations": 2,
            },
        ),
        lambda value: value.update(
            plasticity={"eligibility_decay": 0.5, "learning_rate": 0.1},
            adaptation={
                "activity_average_rate": 0.2,
                "threshold_rate": 0.1,
                "target_activity": 0.4,
                "recruitment_threshold": 1.0,
                "minimum_presentations": 1,
            },
        ),
    ),
    ids=(
        "fan-in",
        "initialization distribution",
        "incoming norm",
        "inhibition radius",
        "threshold bounds",
        "dynamics constant",
        "settling constant",
        "eligibility decay",
        "learning rate",
        "adaptation without plasticity",
        "activity average rate",
        "minimum Presentations",
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
