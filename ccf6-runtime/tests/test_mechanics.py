"""Behavioral premises of the NCL-only column network."""

from __future__ import annotations

import numpy as np
import pytest

from ccf6 import params
from ccf6.learning import Recruitment, committed
from ccf6.network import Architecture, Network
from ccf6.population import Population, relax, transmit
from ccf6.thalamus import LocalShape, PopulationColour, Thalamus


@pytest.fixture
def parameters():
    return params.resolve()


def population(**overrides):
    arguments = {
        "name": "features",
        "shape": (8, 8),
        "levels": 2,
        "input_size": 16,
        "role": "sensory",
        "modality": "visual",
        "sources": (),
        "local_levels": 0,
        "pooling": 3,
        "fanin": 4,
        "cluster": 4,
        "rng": np.random.default_rng(0),
    }
    arguments.update(overrides)
    return Population(**arguments)


def test_relaxation_is_bounded_and_cannot_overshoot(parameters):
    state = np.zeros(4)
    drive = np.array([-50.0, 0.0, 0.5, 50.0])
    for _ in range(500):
        state = relax(state, drive, parameters["tau_l4"], parameters)
    assert state.min() >= parameters["activation_floor"] - 1e-9
    assert state.max() <= parameters["activation_ceiling"] + 1e-9

    for dt in (0.001, 0.1, 1.0, 100.0):
        varied = dict(parameters, dt=dt)
        next_state = relax(np.zeros(1), np.array([0.8]), varied["tau_l4"], varied)
        assert 0.0 <= next_state[0] <= 0.8 + 1e-12


def test_transmission_removes_resting_activity(parameters):
    resting = np.full(16, parameters["activation_floor"])
    assert transmit(resting, parameters).sum() == pytest.approx(0.0)


def test_top_columns_compete_in_bounded_clusters():
    subject = population()
    assert subject.levels[0].w_lateral.fan_in()[0] == 3
    assert subject.top.w_lateral.fan_in()[0] == 15
    assert subject.top.w_lateral.nnz == 4 * (16 * 15)


def test_population_role_and_modality_are_explicit():
    sensory = population()
    association = population(
        name="concept",
        role="association",
        modality=None,
        sources=("features",),
    )
    assert sensory.modality == "visual"
    assert association.sources == ("features",)

    with pytest.raises(ValueError):
        population(modality="olfactory")
    with pytest.raises(ValueError):
        population(role="association", modality=None, sources=())


def test_sensory_adapters_are_replaceable_and_stateless():
    first = Thalamus({"colour": PopulationColour(8, 32)})
    expected = first.project({"colour": 3})["colour"]
    first.project({"colour": 5})
    assert first.project({"colour": 3})["colour"] == pytest.approx(expected)

    shape = LocalShape(radius=2, eccentricity=(1.0, 0.6, 0.2))
    window = shape.encode(np.ones((5, 5))).reshape(5, 5)
    assert window[2, 2] == pytest.approx(1.0)
    assert window[1, 2] == pytest.approx(0.6)
    assert window[0, 0] == pytest.approx(0.2)


def test_recruitment_strengthens_contributing_connections():
    subject = population()
    level = subject.levels[0]
    level.l23[5] = 1.0
    sources = level.w_input.cols[level.input_by_target[5]]
    activity = np.zeros(16)
    activity[sources[:2]] = 1.0
    before = level.w_input.weights[level.input_by_target[5]].copy()

    changed = Recruitment(rate=0.5, commitment=0.0).apply(level, activity)
    after = level.w_input.weights[level.input_by_target[5]]

    assert changed == 1
    assert (after[:2] > before[:2]).all()
    assert (after[2:] < before[2:]).all()
    assert after.sum() == pytest.approx(before.sum())


def test_repeated_wins_make_a_cardinal_candidate_observable():
    subject = population()
    level = subject.top
    rule = Recruitment(rate=0.1, commitment=0.5)
    for _ in range(3):
        level.l23[:] = 0.0
        level.l23[5] = 1.0
        rule.apply(level, np.ones(level.w_input.n_in))

    assert committed(level)[5]
    assert not committed(level)[6]
    subject.reset()
    assert committed(level)[5]


def test_association_feedback_uses_the_same_cross_population_connections(parameters):
    architecture = Architecture(
        side=8,
        cluster=4,
        populations={
            "shape": {"role": "sensory", "modality": "visual", "levels": 1},
            "colour": {"role": "sensory", "modality": "visual", "levels": 1},
            "concept": {
                "role": "association",
                "modality": None,
                "levels": 1,
                "sources": ["shape", "colour"],
            },
        },
        seed=1,
    )
    network = Network(
        architecture,
        Thalamus({"shape": LocalShape(), "colour": PopulationColour(8, 64)}),
    )
    concept = network.populations["concept"]
    concept.levels[0].l5[:] = 1.0
    feedback = network._top_down(parameters)
    assert feedback["shape"].sum() > 0.0
    assert feedback["colour"].sum() > 0.0


def test_unknown_numerical_parameter_is_refused():
    with pytest.raises(KeyError):
        params.resolve({"recurrant_gain": 0.5})
