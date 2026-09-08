"""Premises about the Index (architecture §3.3).

Fast, sparse, separating. It binds a content activation to a Schema state and
completes the pair from either half. The pressure on its code is the opposite of the
Web's: entries must stay apart rather than converge, which is why it is a separate
structure at all (§2.1).
"""

from __future__ import annotations

import numpy as np
import pytest

from ccf6.index import Index


def sparse_pattern(size: int, active: list[int]) -> np.ndarray:
    out = np.zeros(size)
    out[active] = 1.0
    return out


@pytest.fixture
def index():
    return Index(content_size=12, schema_size=9)


def test_a_single_exposure_is_enough_to_write(index):
    """Anything needing repetition cannot serve as episodic memory."""
    content = sparse_pattern(12, [0, 1])
    where = sparse_pattern(9, [3])
    index.write(content, where)
    assert index.entries == 1


def test_completion_from_a_position_recovers_the_content(index):
    content = sparse_pattern(12, [4, 5])
    where = sparse_pattern(9, [2])
    index.write(content, where)
    recovered, _ = index.complete(schema_state=where)
    assert int(np.argmax(recovered)) in (4, 5)


def test_completion_from_a_content_recovers_the_position(index):
    """Both directions: retrieval one way, relocalization the other."""
    content = sparse_pattern(12, [7])
    where = sparse_pattern(9, [6])
    index.write(content, where)
    _, located = index.complete(content=content)
    assert int(np.argmax(located)) == 6


def test_two_similar_episodes_do_not_merge(index):
    """Separation is the Index's whole job: it must not average what it stores."""
    where_a, where_b = sparse_pattern(9, [1]), sparse_pattern(9, [2])
    index.write(sparse_pattern(12, [0]), where_a)
    index.write(sparse_pattern(12, [1]), where_b)

    from_a, _ = index.complete(schema_state=where_a)
    from_b, _ = index.complete(schema_state=where_b)
    assert int(np.argmax(from_a)) == 0
    assert int(np.argmax(from_b)) == 1


def test_a_partial_cue_still_completes(index):
    """Pattern completion, not exact lookup."""
    content = sparse_pattern(12, [2, 3, 4])
    where = sparse_pattern(9, [5])
    index.write(content, where)
    partial = sparse_pattern(12, [2])          # one third of the cue
    _, located = index.complete(content=partial)
    assert int(np.argmax(located)) == 5


def test_an_unwritten_cue_recovers_nothing(index):
    """An empty Index must not invent a binding."""
    recovered, _ = index.complete(schema_state=sparse_pattern(9, [0]))
    assert recovered.max() == pytest.approx(0.0)


def test_the_index_does_not_generalize(index):
    """§6: an Index that starts merging entries has become a slow Web, badly tuned."""
    for slot in range(9):
        index.write(sparse_pattern(12, [slot]), sparse_pattern(9, [slot]))
    for slot in range(9):
        recovered, _ = index.complete(schema_state=sparse_pattern(9, [slot]))
        assert int(np.argmax(recovered)) == slot


def test_completion_needs_at_least_one_half_of_the_cue(index):
    with pytest.raises(ValueError):
        index.complete()
