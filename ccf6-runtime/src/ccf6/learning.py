"""Local recruitment of Columns by repeated successful co-activation.

A winning Column strengthens the active connections that contributed to its response.
Repeated wins spend its remaining plasticity, making recruitment observable without
turning the Column into a symbolic concept container.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Recruitment:
    rate: float = 0.05
    commitment: float = 0.02
    floor: float = 0.05

    def apply(self, level, source: np.ndarray) -> int:
        """Apply one local update to each active competition cluster."""
        if level.w_input is None or level.input_by_target is None or self.rate <= 0.0:
            return 0

        members = level.cluster_members
        activity = level.l23[members]
        best = activity.argmax(axis=1)
        winners = members[np.arange(members.shape[0]), best]
        active = activity[np.arange(members.shape[0]), best] > self.floor
        winners = winners[active]
        if winners.size == 0:
            return 0

        indices = level.input_by_target[winners]
        weights = level.w_input.weights
        drawn = source[level.w_input.cols[indices]]
        norms = np.linalg.norm(drawn, axis=1, keepdims=True)
        target = np.divide(
            drawn, norms, out=np.zeros_like(drawn), where=norms > 1e-12
        )

        step = self.rate * level.plasticity[winners][:, None]
        current = weights[indices]
        updated = current + step * (target - current)
        totals = updated.sum(axis=1, keepdims=True)
        scale = np.divide(
            current.sum(axis=1, keepdims=True),
            totals,
            out=np.ones_like(totals),
            where=totals > 1e-12,
        )
        weights[indices] = updated * scale

        level.plasticity[winners] *= 1.0 - self.commitment
        level.wins[winners] += 1
        return int(winners.size)

    def describe(self) -> dict:
        return {
            "rate": self.rate,
            "commitment": self.commitment,
            "floor": self.floor,
        }


def committed(level, threshold: float = 0.5) -> np.ndarray:
    """Return Columns that have spent more than the given plasticity fraction."""
    return level.plasticity < (1.0 - threshold)
