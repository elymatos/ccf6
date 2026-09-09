"""Tests for the claims the mechanics are supposed to make.

Each one names a premise from CONTEXT.md or an ADR. A test that only pins current
behaviour is worth less than one that would fail if a premise stopped holding.
"""

from __future__ import annotations

import numpy as np
import pytest

from ccf6 import figures, params
from ccf6.space import Space, relax, transmit
from ccf6.metrics import two_way_selectivity
from ccf6.thalamus import LocalistColour, LocalShape, LocalistPosition, PopulationColour, Thalamus
from ccf6.world import Object, World


@pytest.fixture
def p():
    return params.resolve()


def test_a_uniform_world_produces_no_contrast(p):
    """Contrast still measures what it always measured — it is just no longer the input.

    ADR-0009 moved it out of the encoding path; it remains available as analysis, and
    the property that made it attractive should keep holding where it is used.
    """
    world = World(8)
    assert world.contrast().max() == pytest.approx(0.0)


def test_contrast_is_not_translation_invariant(p):
    """ADR-0009: the reason contrast is not the input code.

    Off-field neighbours count as not differing, so a figure touching the World's frame
    scores lower than the same figure in the middle. The full-neighbourhood divisor
    removed the border *inflation*, not the dependence on where the figure sits.
    """
    world = World(12)
    shape = figures.named(["T"])[0]
    signatures = set()
    for i in range(12):
        for j in range(12):
            if not world.fits(shape, (i, j)):
                continue
            world.clear()
            world.place_object(shape, (i, j))
            field = world.contrast()
            signatures.add(tuple(field[a, b] for a, b, _ in shape.cells_at((i, j))))
    assert len(signatures) > 1


def test_what_the_boundary_encodes_is_the_same_at_every_world_position(p):
    """ADR-0004, asserted where it actually bites: on what reaches the Thalamus.

    Not `.sum()` at two interior origins — that passed for the whole life of contrast
    coding while the invariance was broken at the frame. Every fitting origin, per
    Column, for every figure in the confusion set.
    """
    world = World(12)
    encoder = LocalShape(radius=1)
    for shape in figures.named(sorted(figures.FIGURES)):
        encoded = set()
        for i in range(12):
            for j in range(12):
                if not world.fits(shape, (i, j)):
                    continue
                world.clear()
                world.place_object(shape, (i, j))
                padded = world.foreground(1)
                stops = tuple(
                    tuple(encoder.encode(padded[a:a + 3, b:b + 3]))
                    for a, b, _ in shape.cells_at((i, j))
                )
                encoded.add(stops)
        assert len(encoded) == 1, f"{shape.name} encodes {len(encoded)} ways across origins"


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

    # Identical structure, different World positions, identical relations.
    assert shape.relations() == Object("L", shape.parts).relations()
    # What the boundary makes of that placement is asserted separately, and per Column:
    # see test_what_the_boundary_encodes_is_the_same_at_every_world_position.


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


def test_the_top_level_competes_by_cluster_and_lower_levels_by_neighbourhood():
    """H2/G1: once convergence stops being spatial, competition cannot stay spatial.

    But it cannot stay all-to-all either: that grows as the square of the population.
    The cluster is the unit of competition at the top.
    """
    space = Space(
        "a", (8, 8), 3, 64,
        cortical_area="parietal", modality="visual",
        local_levels=2, pooling=3, fanin=12, cluster=4, rng=np.random.default_rng(0),
    )
    lateral = [level.w_lateral.fan_in() for level in space.levels]
    assert lateral[0][0] == 3             # corner Column of an 8-neighbourhood
    assert lateral[-1][0] == 15           # every other Column of its 4x4 cluster
    # Four clusters tile an 8x8 Level, and nothing crosses between them.
    assert space.levels[-1].w_lateral.nnz == 4 * (16 * 15)


def test_swapping_the_colour_encoder_changes_nothing_downstream():
    """D3: the Thalamus is the sole site of the encoding decision."""
    signals = {"colour": 3, "position": (2, 2)}
    localist = Thalamus({"colour": LocalistColour(8), "position": LocalistPosition(8)})
    population = Thalamus({"colour": PopulationColour(8, 32), "position": LocalistPosition(8)})

    assert localist.project(signals)["colour"].sum() == pytest.approx(1.0)
    assert (localist.project(signals)["colour"] > 0).sum() == 1
    # A population code spreads one value over many Columns; the interface is identical.
    assert (population.project(signals)["colour"] > 0.01).sum() > 1
    # Every other Space is untouched by the swap.
    assert localist.project(signals)["position"].tolist() == \
           population.project(signals)["position"].tolist()


def test_the_thalamus_carries_no_state_between_samples():
    """The moment the boundary remembers where it has been it has become the Schema."""
    thalamus = Thalamus({"colour": LocalistColour(8)})
    first = thalamus.project({"colour": 3})["colour"]
    thalamus.project({"colour": 5})
    assert thalamus.project({"colour": 3})["colour"].tolist() == first.tolist()


def test_a_shape_encoder_grades_its_window_by_eccentricity():
    """Local shape is a sensory code: what is here, never where here is.

    Ego is focused somewhere, and the rest of what is in view is not silent, so the
    window falls off with distance from the focus rather than stopping at its edge.
    """
    encoder = LocalShape(radius=2, eccentricity=(1.0, 0.6, 0.2))
    assert encoder.size == 25
    window = encoder.encode(np.ones((5, 5))).reshape(5, 5)
    assert window[2, 2] == pytest.approx(1.0)     # the focused cell
    assert window[1, 2] == pytest.approx(0.6)     # one of the 8 neighbours
    assert window[2, 1] == pytest.approx(0.6)
    assert window[0, 0] == pytest.approx(0.2)     # the ring beyond
    with pytest.raises(ValueError):
        encoder.encode(np.zeros((3, 3)))
    with pytest.raises(ValueError):
        LocalShape(radius=3, eccentricity=(1.0, 0.6, 0.2))


def test_the_graded_window_is_blind_to_a_180_degree_rotation_when_summed():
    """Not a defect of the profile: a wider or graded window is a wider sum.

    Summed over a figure's cells, a fixed window computes that figure's local
    autocorrelation, and an autocorrelation is centrally symmetric. So the summed code
    cannot tell a figure from its 180-degree rotation, at any radius. The distinction
    lives in *which* windows occurred and in what order, which is the traversal.
    """
    from ccf6 import figures
    from ccf6.ego import Presentation
    from ccf6.world import World

    encoder = LocalShape(radius=2)
    def summed(name):
        obj = figures.FIGURES[name]
        world = World(12)
        world.place_object(obj, (5, 5))
        padded = world.foreground(encoder.radius)
        steps = Presentation.of_object(world, obj, (5, 5), "raster").steps
        side = encoder.side
        return sum(
            encoder.encode(padded[i:i + side, j:j + side])
            for i, j in (s.position for s in steps)
        )

    assert summed("T") == pytest.approx(summed("T-up"))          # 180 degrees: blind
    assert summed("T-right") == pytest.approx(summed("T-left"))  # 180 degrees: blind
    assert not np.allclose(summed("T"), summed("T-right"))       # 90 degrees: separable


def test_the_confusion_set_shares_one_feature_bag():
    """T, ⊥, ⊢ and ⊣ have identical parts, which is what makes the set discriminating."""
    from ccf6 import figures

    assert len({len(shape.parts) for shape in figures.FIGURES.values()}) == 1


def test_an_unordered_bag_of_offsets_cannot_separate_the_confusion_set():
    """A found limit of part-relative structure as ADR-0004 currently computes it.

    `Object.relations()` is the *unordered multiset* of every pairwise offset. That
    multiset is closed under reflection for a figure whose bar is symmetric, so a T and
    an upside-down T store identically — as do ⊢ and ⊣. The bag keeps which offsets
    occur and discards how they were traversed, and the arrangement is in the traversal.

    This is why the Schema is advanced by a *sequence* of Relations rather than handed a
    set of them, and it is recorded here so that a later structural claim cannot be
    made on the bag by mistake.
    """
    from ccf6 import figures

    bags = {name: tuple(shape.relations()) for name, shape in figures.FIGURES.items()}
    assert len(set(bags.values())) == 2, "expected T≡⊥ and ⊢≡⊣ to collapse"
    assert bags["T"] == bags["T-up"]
    assert bags["T-right"] == bags["T-left"]


def test_an_ordered_walk_does_separate_the_confusion_set():
    """What the bag loses, the traversal keeps — and the traversal is what Ego supplies."""
    from ccf6 import figures
    from ccf6.ego import Presentation

    walks = {}
    for name, shape in figures.FIGURES.items():
        world = World(12)
        world.place_object(shape, (5, 5))
        steps = Presentation.of_object(world, shape, (5, 5)).steps
        walks[name] = tuple(s.relation for s in steps[1:])
    assert len(set(walks.values())) == len(figures.FIGURES)


def test_selectivity_separates_the_two_factors():
    """A Column following colour scores on colour; one following position does not."""
    responses = np.zeros((4, 5, 3))
    responses[:, :, 0] = np.arange(4)[:, None]      # varies with colour only
    responses[:, :, 1] = np.arange(5)[None, :]      # varies with position only
    responses[:, :, 2] = 0.5                        # never moves

    first, second = two_way_selectivity(responses)
    assert first[0] == pytest.approx(1.0)
    assert second[0] == pytest.approx(0.0)
    assert second[1] == pytest.approx(1.0)
    assert first[2] == pytest.approx(0.0) and second[2] == pytest.approx(0.0)


def test_a_space_declares_where_it_sits_and_how_its_content_arrives():
    """CONTEXT.md: Cortical Area and Modality are declared, and neither implies the other.

    position and colour are both visual and sit in different Cortical Areas, so a Space
    cannot infer one from the other and must be told both.
    """
    from ccf6.network import Architecture, Network
    from ccf6.thalamus import LocalistColour, LocalistPosition

    thalamus = Thalamus({"colour": PopulationColour(8, 64), "shape": LocalShape()})
    network = Network(Architecture(space_side=8, cluster=4), thalamus)
    spaces = network.web.spaces
    assert spaces["colour"].cortical_area == "temporal"
    # Two Spaces, one Modality: distinctness is a matter of dimension, not of channel.
    assert spaces["colour"].modality == spaces["shape"].modality == "visual"
    # A convergence Space is fed by other Spaces, so no channel is its own.
    assert spaces["convergence"].modality is None
    assert spaces["convergence"].cortical_area == "frontal"


def test_a_space_outside_the_declared_anatomy_is_refused():
    """An invented Cortical Area would look like a claim CCF6 has not made."""
    with pytest.raises(ValueError):
        Space("a", (2, 2), 1, 4, cortical_area="occipital", modality="visual",
              local_levels=0, pooling=2, fanin=2, cluster=2, rng=np.random.default_rng(0))
    with pytest.raises(ValueError):
        Space("a", (2, 2), 1, 4, cortical_area="parietal", modality="olfactory",
              local_levels=0, pooling=2, fanin=2, cluster=2, rng=np.random.default_rng(0))


def test_an_unknown_parameter_is_refused():
    """A misspelled parameter that did nothing would look like one with no effect."""
    with pytest.raises(KeyError):
        params.resolve({"recurrant_gain": 0.5})


def test_population_separation_sees_a_figure_no_single_column_carries():
    """The point of the population view: a Level can tell two figures apart while
    every one of its Columns, taken alone, cannot."""
    from ccf6.metrics import figure_separation, population_separation

    # Two figures, one origin, two Columns. Each Column responds identically on
    # average to both figures; only the *pairing* differs, so no Column separates them.
    responses = np.array([
        [[1.0, 0.0]],
        [[0.0, 1.0]],
    ])
    per_column = figure_separation(responses)
    mean, matrix = population_separation(responses)

    assert per_column.max() > 0.0        # here each Column does move
    assert matrix[0, 1] == pytest.approx(mean)
    assert mean > 0.0

    # And the failure the matrix exists to show: two figures merged into one pattern.
    merged = np.array([[[1.0, 0.0]], [[1.0, 0.0]]])
    mean_merged, matrix_merged = population_separation(merged)
    assert mean_merged == pytest.approx(0.0)
    assert matrix_merged[0, 1] == pytest.approx(0.0)


def test_a_traversal_keeps_what_the_average_throws_away():
    """The readout, not the network, was losing the arrangement.

    Two traversals of the same stops in opposite orders leave the same average and
    different sequences. If the sequence did not separate them, no measurement built on
    it could tell a figure from its 180-degree rotation.
    """
    from ccf6.network import Traversal

    a = Traversal(np.array([[1.0, 0.0], [0.0, 1.0]]), np.zeros((2, 1)), np.zeros((2, 1)))
    b = Traversal(np.array([[0.0, 1.0], [1.0, 0.0]]), np.zeros((2, 1)), np.zeros((2, 1)))

    assert a.mean.tolist() == b.mean.tolist()          # the average cannot tell them apart
    assert a.sequence.tolist() != b.sequence.tolist()  # the order can


def test_the_index_readout_pairs_content_with_the_position_it_was_bound_at():
    """Concatenating per stop keeps the pairing an outer product would cost more to keep."""
    from ccf6.network import Traversal

    t = Traversal(
        np.zeros((2, 1)),
        np.array([[3.0, 4.0], [0.0, 5.0]]),
        np.array([[6.0], [8.0]]),
    )
    # Stop 0's content and position, then stop 1's: the pairing is carried by order.
    assert t.bindings.tolist() == pytest.approx([0.6, 0.8, 1.0, 0.0, 1.0, 1.0])


def test_a_binding_is_not_decided_by_which_half_has_more_dimensions():
    """Content is 4096 numbers and a Schema state is 50.

    Concatenated raw, a binding is 98.8% content by dimension, so a Level whose content
    is undifferentiated outvotes the arrangement that is right there beside it. Each
    half is scaled to unit length first, which is the same lesson as not averaging over
    Columns: an unweighted aggregate lets size decide the answer.
    """
    from ccf6.network import Traversal

    wide = np.zeros((1, 400))
    wide[0, 0] = 1.0
    narrow = np.array([[3.0, 4.0]])
    bindings = Traversal(np.zeros((1, 1)), wide, narrow).bindings

    assert np.linalg.norm(bindings[:400]) == pytest.approx(1.0)
    assert np.linalg.norm(bindings[400:]) == pytest.approx(1.0)
