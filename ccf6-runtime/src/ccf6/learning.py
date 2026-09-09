"""Recruitment: the local rule that commits a Column to a conjunction.

The architecture calls recruitment its central mechanism and neither source tradition
supplies it. This is the smallest version that could fail.

Three parts, from the neurocognitive-linguistics account:

**Redundancy.** A Level is 4096 Columns each drawing 4 sources at random, so the
population already holds a large sample of the possible conjunctions of what is below
it. Nothing here creates a conjunction. Learning selects among conjunctions that the
wiring already offers, which is what makes it local: no connection is added, moved or
searched for.

**Strengthening.** The Column that wins its cluster moves its weights toward the input
that made it win. That is one line of vector quantization, and it is Hebbian in the only
sense ADR-0005 allows: the change at a connection depends on the activity at its two
ends and on nothing else.

**Commitment.** A Column that keeps winning becomes progressively less plastic, so a
conjunction that recurs stops being available to represent anything else. This is what
"recruited when necessary" has to mean once the units are not created on demand: the
population is fixed, and recruitment is the act of spending one of it.

What this cannot do, stated so a result is not read for more than it is worth: it cannot
change *which* sources a Column draws from, so a conjunction absent from the random
wiring cannot be learned however often it occurs. Widening the fan-in or growing the
population are the knobs for that, and both are declared quantities rather than
something the rule discovers.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Recruitment:
    """How fast a winner moves toward its input, and how fast it stops moving.

    `rate` is the step toward the input pattern. `commitment` is the fraction of a
    Column's remaining plasticity spent each time it wins, so a Column that wins *n*
    times has (1 - commitment)^n of its plasticity left.
    """

    rate: float = 0.05
    commitment: float = 0.02
    #: A cluster whose winner is barely above the activation floor has not represented
    #: anything, and letting it learn would commit Columns to noise.
    floor: float = 0.05

    def apply(self, level, source: np.ndarray) -> int:
        """One learning step at one Level. Returns how many Columns changed.

        `source` is what arrived from below, already thresholded for transmission.
        """
        if level.w_input is None or level.input_by_target is None or self.rate <= 0.0:
            return 0

        members = level.cluster_members          # (clusters, members per cluster)
        activity = level.l23[members]            # (clusters, members)
        best = activity.argmax(axis=1)
        winners = members[np.arange(members.shape[0]), best]
        alive = activity[np.arange(members.shape[0]), best] > self.floor
        winners = winners[alive]
        if winners.size == 0:
            return 0

        index = level.input_by_target[winners]   # (winners, fan-in)
        weights = level.w_input.weights
        drawn = source[level.w_input.cols[index]]

        # Toward the input as a direction, not as a magnitude: a loud stop and a quiet
        # one carrying the same pattern should teach the same thing.
        norms = np.linalg.norm(drawn, axis=1, keepdims=True)
        target = np.divide(drawn, norms, out=np.zeros_like(drawn), where=norms > 1e-12)

        step = self.rate * level.plasticity[winners][:, None]
        current = weights[index]
        updated = current + step * (target - current)

        # Keep each Column's total drive fixed, so winning cannot make a Column win
        # everything afterwards by being louder rather than better matched.
        totals = updated.sum(axis=1, keepdims=True)
        scale = np.divide(current.sum(axis=1, keepdims=True), totals,
                          out=np.ones_like(totals), where=totals > 1e-12)
        weights[index] = updated * scale

        level.plasticity[winners] *= 1.0 - self.commitment
        level.wins[winners] += 1
        return int(winners.size)

    def describe(self) -> dict:
        return {"rate": self.rate, "commitment": self.commitment, "floor": self.floor}


def committed(level, threshold: float = 0.5) -> np.ndarray:
    """Columns that have spent more than `threshold` of their plasticity.

    The observable §10's fourth prediction asks for: a unit recruited from a recurring
    conjunction should be identifiable as such after training.
    """
    return level.plasticity < (1.0 - threshold)
