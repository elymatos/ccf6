"""Sparse connections between populations of Columns.

Connectivity is stored as triplets — which Column, from which Column, how strongly —
so memory scales with the number of connections rather than with the square of the
population. That is a design decision rather than an optimization (ADR: architecture
§8.1): a Column that drew from the whole population below it would be identical to
every other such Column and would distinguish nothing, so a bounded fan-in is what
makes convergence mean anything. Density would defeat the mechanism before it cost
anything.

One structure carries both directions. Feedback runs the same connections backwards
rather than declaring a second wiring, which is what makes reciprocity structural: a
Level feeds back to exactly what it draws from, and cannot drift out of correspondence.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Connections:
    """A sparse map from `n_in` sources to `n_out` targets.

    `rows`, `cols` and `weights` are parallel arrays: connection *k* carries
    `weights[k]` from source `cols[k]` to target `rows[k]`.
    """

    n_out: int
    n_in: int
    rows: np.ndarray
    cols: np.ndarray
    weights: np.ndarray

    @classmethod
    def from_pairs(cls, n_out: int, n_in: int, triplets) -> Connections:
        rows, cols, weights = ([], [], []) if not triplets else map(list, zip(*triplets))
        return cls(
            n_out,
            n_in,
            np.asarray(rows, dtype=np.int64),
            np.asarray(cols, dtype=np.int64),
            np.asarray(weights, dtype=np.float64),
        )

    def forward(self, source: np.ndarray) -> np.ndarray:
        """What arrives at each target: the weighted sum of its sources."""
        contributions = self.weights * source[self.cols]
        return np.bincount(self.rows, weights=contributions, minlength=self.n_out)

    def backward(self, target: np.ndarray) -> np.ndarray:
        """The same connections run the other way, for feedback."""
        contributions = self.weights * target[self.rows]
        return np.bincount(self.cols, weights=contributions, minlength=self.n_in)

    def by_target(self) -> np.ndarray | None:
        """Connection indices grouped by target Column, as (n_out, fan-in).

        None where fan-in is not uniform, because the grouping is a rectangle. Built
        once and cached by the Level: a rule that searched `rows` on every stop would be
        quadratic in the population it exists to keep sparse.
        """
        counts = np.bincount(self.rows, minlength=self.n_out)
        if counts.size == 0 or counts.min() != counts.max():
            # Local pooling gives edge Columns fewer sources than middle ones. Nothing
            # is wrong with that wiring; it just cannot be indexed as a rectangle, and
            # the caller decides whether to learn on this Level at all.
            return None
        order = np.argsort(self.rows, kind="stable")
        return order.reshape(self.n_out, int(counts.max()))

    def fan_in(self) -> np.ndarray:
        """How many Columns send into each target."""
        return np.bincount(self.rows, minlength=self.n_out)

    @property
    def nnz(self) -> int:
        return int(self.rows.size)

    @property
    def nbytes(self) -> int:
        return int(self.rows.nbytes + self.cols.nbytes + self.weights.nbytes)

    def to_dense(self) -> np.ndarray:
        """Only for inspection and tests. Never used on the hot path."""
        dense = np.zeros((self.n_out, self.n_in))
        np.add.at(dense, (self.rows, self.cols), self.weights)
        return dense

    def describe(self) -> dict:
        fan = self.fan_in()
        return {
            "connections": self.nnz,
            "fan_in": int(fan.mean()),
            "fan_in_min": int(fan.min()),
            "fan_in_max": int(fan.max()),
        }


def sparse_nonlocal(
    n_out: int, n_in: int, fanin: int, rng: np.random.Generator
) -> Connections:
    """Each target draws from a random subset of the source population.

    Restricting convergence to a neighbourhood puts a ceiling on receptive-field size
    that no number of Levels can lift. Sampling from anywhere reaches the whole
    population at once and gives every Column a different, overlapping input set,
    which is what makes distinct convergence possible.
    """
    if fanin >= n_in:
        raise ValueError(
            f"fan-in {fanin} covers the whole source population of {n_in}: every target "
            "would receive the same thing and they would become indistinguishable"
        )
    rows = np.repeat(np.arange(n_out), fanin)
    cols = np.concatenate([rng.choice(n_in, size=fanin, replace=False) for _ in range(n_out)])
    return Connections(n_out, n_in, rows, cols, np.ones(rows.size))


def local_pooling(
    shape: tuple[int, int], source_shape: tuple[int, int], k: int
) -> Connections:
    """Each Column draws from a k x k neighbourhood centred on its own position.

    Receptive fields grow additively with depth, which is what the early Levels are
    for: local structure before anything global.
    """
    h, w = shape
    sh, sw = source_shape
    if k * k >= sh * sw:
        raise ValueError(
            f"a {k}x{k} neighbourhood covers a source population of {sh * sw}: every target "
            "would receive the same thing and they would become indistinguishable"
        )
    half = k // 2
    scale_i, scale_j = sh / h, sw / w
    rows, cols = [], []
    for i in range(h):
        for j in range(w):
            ci, cj = int(i * scale_i), int(j * scale_j)
            for di in range(-half, half + 1):
                for dj in range(-half, half + 1):
                    si, sj = ci + di, cj + dj
                    if 0 <= si < sh and 0 <= sj < sw:
                        rows.append(i * w + j)
                        cols.append(si * sw + sj)
    return Connections(
        h * w, sh * sw,
        np.asarray(rows, dtype=np.int64), np.asarray(cols, dtype=np.int64),
        np.ones(len(rows)),
    )


def neighbourhood(shape: tuple[int, int]) -> Connections:
    """8-neighbourhood competition, normalized by how many neighbours a Column has.

    Eight rather than four so that a diagonal arrangement does not compete differently
    from an axis-aligned one. No self-inhibition: a Column does not suppress itself.
    """
    h, w = shape
    rows, cols = [], []
    for i in range(h):
        for j in range(w):
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if 0 <= ni < h and 0 <= nj < w:
                        rows.append(i * w + j)
                        cols.append(ni * w + nj)
    rows = np.asarray(rows, dtype=np.int64)
    counts = np.bincount(rows, minlength=h * w)
    return Connections(
        h * w, h * w, rows, np.asarray(cols, dtype=np.int64), 1.0 / counts[rows]
    )


def clustered_competition(shape: tuple[int, int], side: int) -> Connections:
    """All-to-all competition inside a cluster, and none across clusters.

    Once convergence stops being spatial, competition cannot stay spatial either: two
    Columns standing for different things have no reason to be grid neighbours. But
    competing every Column against every other grows as the square of the population,
    and at 64x64 that is 16.8 million connections for one Level — the failure §8.1
    exists to prevent, arriving in the one place the code still allowed it.

    A cluster is the unit of competition instead: Columns inside one compete for the
    right to represent, Columns in different clusters do not compete at all. Cost falls
    from n(n-1) to n(m-1) for a cluster of m.

    **The known artefact.** A partition has edges, so two adjacent Columns either side of
    a cluster boundary never compete however similar they are. An overlapping rule would
    not have that property, and would cost more. Recorded rather than hidden.
    """
    h, w = shape
    if side < 2:
        raise ValueError(f"a cluster of {side} has nothing to compete: give it at least 2 a side")
    rows, cols, weights = [], [], []
    for top in range(0, h, side):
        for left in range(0, w, side):
            members = np.array([
                i * w + j
                for i in range(top, min(top + side, h))
                for j in range(left, min(left + side, w))
            ])
            m = members.size
            if m < 2:
                continue
            a = np.repeat(members, m)
            b = np.tile(members, m)
            keep = a != b
            rows.append(a[keep])
            cols.append(b[keep])
            weights.append(np.full(int(keep.sum()), 1.0 / (m - 1)))
    if not rows:
        return Connections(h * w, h * w, np.array([], dtype=np.int64),
                           np.array([], dtype=np.int64), np.array([]))
    return Connections(
        h * w, h * w,
        np.concatenate(rows).astype(np.int64),
        np.concatenate(cols).astype(np.int64),
        np.concatenate(weights),
    )
