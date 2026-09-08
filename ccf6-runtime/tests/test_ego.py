"""Premises about Ego, sampling and given Relations (architecture §8.2, ADR-0003).

A figure with several parts is presented as a sequence: Ego visits the positions
carrying structure, and the offset between successive stops is the Relation. Without
this the Schema has nothing to integrate and the Index has nothing to bind.
"""

from __future__ import annotations

import pytest

from ccf6.ego import Presentation, visiting_order
from ccf6.world import Object, World

T = Object("T", (((0, -1), 1), ((0, 0), 1), ((0, 1), 1), ((1, 0), 1), ((2, 0), 1)))


def test_a_presentation_visits_every_part_of_a_figure():
    world = World(8)
    world.place_object(T, (2, 3))
    steps = Presentation.of_object(world, T, (2, 3)).steps
    assert len(steps) == len(T.parts)


def test_the_visiting_order_is_reproducible():
    world = World(8)
    world.place_object(T, (2, 3))
    first = [s.position for s in Presentation.of_object(world, T, (2, 3)).steps]
    second = [s.position for s in Presentation.of_object(world, T, (2, 3)).steps]
    assert first == second


def test_relations_between_stops_are_the_offsets_walked():
    world = World(8)
    world.place_object(T, (2, 3))
    steps = Presentation.of_object(world, T, (2, 3)).steps
    for before, after in zip(steps, steps[1:]):
        assert after.relation == (
            after.position[0] - before.position[0],
            after.position[1] - before.position[1],
        )


def test_the_first_stop_has_no_incoming_relation():
    """One looks from somewhere before one has moved."""
    world = World(8)
    world.place_object(T, (2, 3))
    assert Presentation.of_object(world, T, (2, 3)).steps[0].relation is None


def test_the_same_figure_elsewhere_walks_the_same_relations():
    """ADR-0004: what is stored is part-relative, so translation must not show up here."""
    here, there = World(8), World(8)
    here.place_object(T, (1, 1))
    there.place_object(T, (4, 4))
    walk = lambda w, o: [s.relation for s in Presentation.of_object(w, T, o).steps[1:]]
    assert walk(here, (1, 1)) == walk(there, (4, 4))


def test_relations_sum_to_the_offset_between_first_and_last_stop():
    """Composition has to hold at the boundary before the Schema can rely on it."""
    world = World(8)
    world.place_object(T, (2, 3))
    steps = Presentation.of_object(world, T, (2, 3)).steps
    di = sum(s.relation[0] for s in steps[1:])
    dj = sum(s.relation[1] for s in steps[1:])
    assert (di, dj) == (
        steps[-1].position[0] - steps[0].position[0],
        steps[-1].position[1] - steps[0].position[1],
    )


def test_a_contrast_presentation_needs_a_threshold_the_caller_states():
    """Contrast marks a boundary region, not a figure; no default could be right."""
    world = World(8)
    world.place_object(T, (2, 3))
    figure = {(2 + di, 3 + dj) for (di, dj), _ in T.parts}
    seen = {s.position for s in Presentation.of_contrast(world, threshold=0.0).steps}
    # Everything hugging the figure is contrastive too, which is why segmentation is
    # not claimed here: the surround comes along.
    assert figure < seen


def test_an_empty_world_is_presented_as_nothing():
    assert Presentation.of_contrast(World(8), threshold=0.0).steps == []


def test_an_unknown_visiting_order_is_refused():
    with pytest.raises(KeyError):
        visiting_order("spiral-widdershins")
