"""Premises about the Schema (architecture §3.2).

The Schema holds a state advanced by a Relation. Its value is that the same Relation
transforms it the same way wherever it applies. Each test below names one of the
properties §3.2 requires; a Schema that lost any of them would stop being reusable
structure and become a second content code.
"""

from __future__ import annotations

import numpy as np
import pytest

from ccf6 import params
from ccf6.schema import Schema


@pytest.fixture
def p():
    return params.resolve()


@pytest.fixture
def schema():
    return Schema(periods=(3, 4, 5), width=0.6)


def test_distinct_positions_have_distinct_states(schema, p):
    """Separation: two positions sharing a state could not hold different memories."""
    seen = {}
    for i in range(8):
        for j in range(8):
            state = schema.at((i, j), p)
            key = tuple(np.round(state, 6))
            assert key not in seen, f"({i},{j}) collides with {seen[key]}"
            seen[key] = (i, j)


def test_the_same_position_reached_two_ways_has_the_same_state(schema, p):
    """Path consistency: otherwise a memory becomes unreachable from a new direction."""
    east_then_north = schema.advance(schema.advance(schema.origin(), (0, 1), p), (1, 0), p)
    north_then_east = schema.advance(schema.advance(schema.origin(), (1, 0), p), (0, 1), p)
    assert east_then_north == pytest.approx(north_then_east)


def test_relations_compose_along_a_route_never_travelled(schema, p):
    """Composition is what buys inference: arrive somewhere new and query what is there."""
    walked = schema.origin()
    for relation in ((1, 0), (0, 1), (1, 0), (0, 1), (1, 1)):
        walked = schema.advance(walked, relation, p)
    assert walked == pytest.approx(schema.at((3, 3), p))


def test_a_relation_and_its_inverse_return_to_the_start(schema, p):
    there = schema.advance(schema.origin(), (2, -3), p)
    back = schema.advance(there, (-2, 3), p)
    assert back == pytest.approx(schema.origin())


def test_the_schema_is_blind_to_what_occupies_a_position(schema, p):
    """§3.2: the moment it knows the content, the skeleton stops transferring."""
    # advance() takes a Relation and nothing else. There is no content argument to give
    # it, and the state after a move depends only on where the move went.
    assert schema.advance(schema.origin(), (1, 2), p) == pytest.approx(schema.at((1, 2), p))


def test_state_stays_within_the_declared_activation_bounds(schema, p):
    state = schema.at((5, 3), p)
    assert state.min() >= 0.0
    assert state.max() <= p["activation_ceiling"] + 1e-9


def test_periods_that_share_a_factor_wrap_sooner(p):
    """Capacity is the least common multiple of the module periods, and it is declared."""
    assert Schema(periods=(3, 4, 5), width=0.6).capacity == 60
    assert Schema(periods=(2, 4, 8), width=0.6).capacity == 8
