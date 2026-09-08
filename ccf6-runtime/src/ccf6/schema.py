"""The Schema: reusable structure, advanced by Relations.

A stack of periodic modules over a torus. Each module holds a bump whose phase moves
by the offset a Relation supplies; the Schema's state is every module's bump at once.
Nothing here learns — the transformation a Relation selects is declared, in the sense
of ADR-0006, not fitted. That is deliberate for a baseline: the properties §3.2
requires (separation, path consistency, composition) then hold by construction and can
be *tested* rather than hoped for, which is what makes a later learned Schema
comparable to something.

Why periodic modules rather than one big grid of positions. A code with one unit per
position is a coordinate: it separates, but composition is a lookup and nothing
transfers. Phases on a torus compose by addition, so a route never travelled arrives
where the structure implies. Capacity is the least common multiple of the periods, so
a handful of small modules covers a large field — which is the whole reason the
arrangement is cheaper to carry than the positions it distinguishes.

The Schema is blind to content by construction: `advance` takes a Relation and nothing
else. There is no argument through which what-is-here could reach it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Schema:
    """Periodic modules over a torus, addressed by offset.

    `periods` are the module sizes. `width` is the bump's spread in cells; a small
    width approaches a one-hot code, a larger one spreads the same position over more
    Columns without changing what the position *is*.
    """

    periods: tuple[int, ...]
    width: float

    @property
    def size(self) -> int:
        """How many Columns carry the state."""
        return sum(p * p for p in self.periods)

    @property
    def capacity(self) -> int:
        """How far the code runs before it repeats, along one axis."""
        return math.lcm(*self.periods)

    def origin(self) -> np.ndarray:
        return self._encode((0, 0))

    def at(self, position: tuple[int, int], p: dict) -> np.ndarray:
        """The state at a position, reached from the origin by one offset."""
        return self._clip(self._encode(position), p)

    def advance(self, state: np.ndarray, relation: tuple[int, int], p: dict) -> np.ndarray:
        """Apply a Relation: every module's bump moves by the same offset.

        Modules differ in period, so one offset moves them by different fractions of
        their own cycle. That is what makes the combined state separate positions the
        modules cannot separate individually.
        """
        di, dj = relation
        out = []
        cursor = 0
        for period in self.periods:
            block = state[cursor:cursor + period * period].reshape(period, period)
            out.append(np.roll(block, (di, dj), axis=(0, 1)).ravel())
            cursor += period * period
        return self._clip(np.concatenate(out), p)

    def _encode(self, position: tuple[int, int]) -> np.ndarray:
        i, j = position
        blocks = []
        for period in self.periods:
            axis = np.arange(period)
            # Circular distance, so the bump wraps rather than being clipped at a seam.
            di = np.minimum((axis - i) % period, (i - axis) % period)
            dj = np.minimum((axis - j) % period, (j - axis) % period)
            bump = np.exp(-0.5 * ((di[:, None] ** 2 + dj[None, :] ** 2) / self.width ** 2))
            blocks.append(bump.ravel())
        return np.concatenate(blocks)

    def _clip(self, state: np.ndarray, p: dict) -> np.ndarray:
        return np.clip(state, 0.0, p["activation_ceiling"])

    def blocks(self, state: np.ndarray) -> list[np.ndarray]:
        """The state per module, shaped for drawing."""
        out, cursor = [], 0
        for period in self.periods:
            out.append(state[cursor:cursor + period * period].reshape(period, period))
            cursor += period * period
        return out

    def describe(self) -> dict:
        return {
            "periods": list(self.periods),
            "width": self.width,
            "columns": self.size,
            "capacity": self.capacity,
        }
