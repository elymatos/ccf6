"""Tests for the claims the mechanics are supposed to make.

Each one names a premise from CONTEXT.md or an ADR. A test that only pins current
behaviour is worth less than one that would fail if a premise stopped holding.
"""

from __future__ import annotations

import numpy as np
import pytest

from ccf6 import params
from ccf6.space import Space, relax, transmit
from ccf6.metrics import two_way_selectivity
from ccf6.thalamus import LocalistColour, PopulationColour, Thalamus, LocalistPosition
from ccf6.world import Object, World


@pytest.fixture
def p():
    return params.resolve()


def test_a_uniform_world_produces_no_contrast(p):
    """E5: a region with no internal relations registers as empty, by design."""
    world = World(8)
    assert world.contrast().max() == pytest.approx(0.0)


def test_a_single_coloured_cell_is_maximally_contrastive():
    world = World(8)
    world.place(1, (3, 3))
    field = world.contrast()
    assert field[3, 3] == pytest.approx(1.0)
    assert field[0, 0] == pytest.approx(0.0)


def test_object_structure_is_the_same_at_every_world_position():
    """ADR-0004: what is stored is part-relative and carries no origin."""
    shape = Object("L", ((((0, 0)), 1), (((0, 1)), 1), (((1, 0)), 1)))
    assert shape.relations() == shape.relations()

    world_a, world_b = World(8), World(8)
    world_a.place_object(shape, (1, 1))
    world_b.place_object(shape, (5, 4))
    # Identical structure, different World positions, identical relations.
    assert shape.relations() == Object("L", shape.parts).relations()
    assert world_a.contrast().sum() == pytest.approx(world_b.contrast().sum())


def test_relaxation_never_leaves_the_declared_bounds(p):
    """ADR-0006: the target is clamped before relaxation, so state stays in range."""
    state = np.zeros(4)
    huge = np.array([-50.0, 0.0, 0.5, 50.0])
    for _ in range(500):
        state = relax(state, huge, p["tau_l4"], p)
    assert state.min() >= p["activation_floor"] - 1e-9
    assert state.max() <= p["activation_ceiling"] + 1e-9


def test_relaxation_cannot_overshoot_at_any_step_size(p):
    """Exponential relaxation is exact for a constant target; Euler would oscillate."""
    for dt in (0.001, 0.1, 1.0, 100.0):
        wide = dict(p, dt=dt)
        state = relax(np.zeros(1), np.array([0.8]), wide["tau_l4"], wide)
        assert 0.0 <= state[0] <= 0.8 + 1e-12


def test_transmission_removes_the_activation_floor(p):
    """The floor keeps the network alive; it must not accumulate through fan-in."""
    resting = np.full(16, p["activation_floor"])
    assert transmit(resting, p).sum() == pytest.approx(0.0)


def test_the_top_level_competes_globally_and_lower_levels_locally():
    """H2/G1: once convergence stops being spatial, competition cannot stay spatial."""
    space = Space(
        "a", (8, 8), 3, 64,
        cortical_area="parietal", modality="visual",
        local_levels=2, pooling=4, fanin=12, rng=np.random.default_rng(0),
    )
    lower_neighbours = int((space.levels[0].w_lateral[0] > 0).sum())
    top_neighbours = int((space.levels[-1].w_lateral[0] > 0).sum())
    assert lower_neighbours == 3          # corner Column of an 8-neighbourhood
    assert top_neighbours == 63           # every other Column at the top


def test_swapping_the_colour_encoder_changes_nothing_downstream():
    """D3: the Thalamus is the sole site of the encoding decision."""
    localist = Thalamus(LocalistColour(8), LocalistPosition(8))
    population = Thalamus(PopulationColour(8, 32), LocalistPosition(8))

    assert localist.project(3, (2, 2), 1.0)["colour"].sum() == pytest.approx(1.0)
    assert (localist.project(3, (2, 2), 1.0)["colour"] > 0).sum() == 1
    # A population code spreads one value over many Columns; the interface is identical.
    assert (population.project(3, (2, 2), 1.0)["colour"] > 0.01).sum() > 1
    assert localist.project(3, (2, 2), 1.0)["position"].shape == (64,)


def test_selectivity_separates_the_two_factors():
    """A Column following colour scores on colour; one following position does not."""
    responses = np.zeros((4, 5, 3))
    responses[:, :, 0] = np.arange(4)[:, None]      # varies with colour only
    responses[:, :, 1] = np.arange(5)[None, :]      # varies with position only
    responses[:, :, 2] = 0.5                        # never moves

    colour, position = two_way_selectivity(responses)
    assert colour[0] == pytest.approx(1.0)
    assert position[0] == pytest.approx(0.0)
    assert position[1] == pytest.approx(1.0)
    assert colour[2] == pytest.approx(0.0) and position[2] == pytest.approx(0.0)


def test_a_space_declares_where_it_sits_and_how_its_content_arrives():
    """CONTEXT.md: Cortical Area and Modality are declared, and neither implies the other.

    position and colour are both visual and sit in different Cortical Areas, so a Space
    cannot infer one from the other and must be told both.
    """
    from ccf6.network import Architecture, Network
    from ccf6.thalamus import LocalistColour, LocalistPosition

    network = Network(Architecture(), Thalamus(LocalistColour(8), LocalistPosition(8)))
    assert network.position.cortical_area == "parietal"
    assert network.colour.cortical_area == "temporal"
    # Two Spaces, one Modality: distinctness is a matter of dimension, not of channel.
    assert network.position.modality == network.colour.modality == "visual"
    # A Hub is fed by other Spaces rather than by the World, so no channel is its own.
    assert network.hub.modality is None


def test_a_space_outside_the_declared_anatomy_is_refused():
    """An invented Cortical Area would look like a claim CCF6 has not made."""
    with pytest.raises(ValueError):
        Space("a", (2, 2), 1, 4, cortical_area="occipital", modality="visual",
              local_levels=1, pooling=2, fanin=2, rng=np.random.default_rng(0))
    with pytest.raises(ValueError):
        Space("a", (2, 2), 1, 4, cortical_area="parietal", modality="olfactory",
              local_levels=1, pooling=2, fanin=2, rng=np.random.default_rng(0))


def test_an_unknown_parameter_is_refused():
    """A misspelled parameter that did nothing would look like one with no effect."""
    with pytest.raises(KeyError):
        params.resolve({"recurrant_gain": 0.5})
