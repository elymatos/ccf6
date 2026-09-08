"""Premises about sparse connectivity (spec §8.1 / architecture §8.1).

Sparsity is a design quantity, not an optimization: convergence is only meaningful
when a Column draws from a limited subset, and separation depends on low overlap.
These tests would fail if connectivity quietly became dense.
"""

from __future__ import annotations

import numpy as np
import pytest

from ccf6.connections import Connections, local_pooling, neighbourhood, sparse_nonlocal


def test_forward_sums_only_the_declared_sources():
    """A Column adds up what reaches it, and nothing else reaches it."""
    c = Connections.from_pairs(3, 4, [(0, 1, 1.0), (0, 3, 2.0), (2, 0, 0.5)])
    out = c.forward(np.array([10.0, 1.0, 100.0, 2.0]))
    assert out.tolist() == [1.0 * 1.0 + 2.0 * 2.0, 0.0, 0.5 * 10.0]


def test_backward_is_the_transpose_of_forward():
    """Feedback runs the same connections the other way; it is not a second wiring."""
    rng = np.random.default_rng(0)
    c = sparse_nonlocal(16, 32, fanin=4, rng=rng)
    x = rng.random(32)
    y = rng.random(16)
    # <Wx, y> == <x, W^T y> for any x, y — the definition of a transpose.
    assert c.forward(x) @ y == pytest.approx(x @ c.backward(y))


def test_fan_in_is_what_was_declared():
    rng = np.random.default_rng(0)
    c = sparse_nonlocal(64, 256, fanin=12, rng=rng)
    assert c.fan_in().min() == 12
    assert c.fan_in().max() == 12


def test_no_column_draws_from_the_whole_population_below():
    """A Column seeing everything below it is identical to every other such Column."""
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        sparse_nonlocal(16, 8, fanin=8, rng=rng)


def test_local_pooling_reaches_a_neighbourhood_and_no_further():
    c = local_pooling((8, 8), (8, 8), k=3)
    # A corner Column has a 2x2 neighbourhood; a middle one has 3x3.
    fan = c.fan_in().reshape(8, 8)
    assert fan[0, 0] == 4
    assert fan[4, 4] == 9


def test_neighbourhood_competition_excludes_the_self():
    c = neighbourhood((8, 8))
    fan = c.fan_in().reshape(8, 8)
    assert fan[0, 0] == 3          # corner of an 8-neighbourhood
    assert fan[4, 4] == 8
    dense = c.to_dense()
    assert np.diag(dense).max() == 0.0


def test_memory_is_proportional_to_connections_not_to_the_square_of_the_population():
    """A dense 4096x4096 matrix is ~134MB; the same wiring sparse is under a megabyte."""
    rng = np.random.default_rng(0)
    c = sparse_nonlocal(4096, 4096, fanin=12, rng=rng)
    assert c.nbytes < 2_000_000
