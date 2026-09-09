"""Spaces, Levels, and the Column circuit.

A Column holds three private activations. A Level is a Grid of Columns. A Space is a
stack of Levels over one conceptual dimension, sited in a Cortical Area and carrying a
Modality. Connections are sparse (see `connections`): fan-in is a declared quantity,
because a Column drawing from everything below it distinguishes nothing.

The circuit, per ADR-0002:

    L4   <- lower Level L5, or the Thalamus at Level 1
    L2/3 <- L4, own recurrent state, L5 feedback from above,
            and grid neighbours inhibitorily
    L5   <- L2/3, and projects up and down

Updates are synchronous: every Level computes its input from the current state, then
every activation is written at once. Nothing within a tick sees a partially updated
network.
"""

from __future__ import annotations

import numpy as np

from ccf6.connections import (
    Connections,
    clustered_competition,
    local_pooling,
    neighbourhood,
    sparse_nonlocal,
)

#: The channels through which content can reach a Space. A convergence Space has none:
#: it is fed by other Spaces rather than by the World, so no channel is its own.
MODALITIES = ("visual", "auditory", "tactile", "motor", "affective")

#: Where a Space sits. An anatomical claim and nothing else — it never says what job
#: the Space does; the Space's dimension says that.
CORTICAL_AREAS = ("frontal", "parietal", "temporal")


def transmit(l5: np.ndarray, p: dict) -> np.ndarray:
    """What a Column actually sends: its output above a transmission threshold.

    The activation floor means no Column is ever silent, so raw L5 carries a constant
    background. Summed over a fan-in the background outweighs the signal. Subtracting
    the threshold before transmission keeps the floor doing its job — the network
    cannot die — without letting it accumulate through depth.
    """
    return np.maximum(0.0, l5 - p["transmission_threshold"])


def relax(current: np.ndarray, drive: np.ndarray, tau: float, p: dict) -> np.ndarray:
    """Bounded leaky relaxation toward a clamped target.

    The target is clamped before relaxation rather than the state after it, so
    activation stays in range by construction. Exponential relaxation is the exact
    solution for a constant target and therefore cannot overshoot at any step size —
    which matters for something meant to be single-stepped and watched.
    """
    target = np.clip(drive, p["activation_floor"], p["activation_ceiling"])
    alpha = 1.0 - np.exp(-p["dt"] / tau)
    return current + (target - current) * alpha


class Level:
    """One Grid of Columns, and the connections arriving at it."""

    def __init__(self, name: str, shape: tuple[int, int]):
        self.name = name
        self.shape = shape
        self.n = shape[0] * shape[1]
        self.l4 = np.zeros(self.n)
        self.l23 = np.zeros(self.n)
        self.l5 = np.zeros(self.n)
        # Filled in by the connectivity builders.
        self.w_input: Connections | None = None      # into L4, from below or Thalamus
        self.w_feedback: Connections | None = None   # into L2/3, from the Level above
        self.w_lateral: Connections | None = None    # into L2/3, inhibitory, same Level

    def reset(self) -> None:
        self.l4[:] = 0.0
        self.l23[:] = 0.0
        self.l5[:] = 0.0

    def grid(self, layer: str = "l5") -> np.ndarray:
        return getattr(self, layer).reshape(self.shape)


class Space:
    """A stack of Levels over one conceptual dimension.

    Where the Space sits (`cortical_area`) and how its content arrives (`modality`)
    are declared, not inferred, because neither follows from the other: two Spaces can
    share a Modality and sit in different Cortical Areas.
    """

    def __init__(
        self,
        name: str,
        shape: tuple[int, int],
        n_levels: int,
        input_size: int,
        *,
        cortical_area: str,
        modality: str | None,
        local_levels: int,
        pooling: int,
        fanin: int,
        cluster: int,
        rng: np.random.Generator,
        input_mode: str = "identity",
        boundary: str = "Thalamus",
    ):
        if cortical_area not in CORTICAL_AREAS:
            raise ValueError(
                f"{name}: unknown cortical_area {cortical_area!r}; declared: {list(CORTICAL_AREAS)}"
            )
        if modality is not None and modality not in MODALITIES:
            raise ValueError(
                f"{name}: unknown modality {modality!r}; declared: {list(MODALITIES)} or null"
            )
        self.name = name
        self.shape = shape
        self.cortical_area = cortical_area
        self.modality = modality
        self._input_mode = input_mode
        # What feeds Level 1, for the record a run writes. It cannot be inferred from
        # `input_mode` any more: a sensory Space samples its encoder sparsely too, now
        # that the Grid is declared rather than sized by the encoder.
        self._boundary_source = boundary
        self._local_levels = local_levels
        self._pooling = pooling
        self._cluster = cluster
        self.levels = [Level(f"{name}.L{i + 1}", shape) for i in range(n_levels)]

        for index, level in enumerate(self.levels):
            if index == 0:
                level.w_input = self._boundary(level, input_size, fanin, rng)
            elif index < local_levels:
                level.w_input = local_pooling(shape, shape, pooling)
            else:
                level.w_input = sparse_nonlocal(level.n, level.n, fanin, rng)

            is_top = index == len(self.levels) - 1
            level.w_lateral = (clustered_competition(shape, cluster) if is_top
                               else neighbourhood(shape))

        # Feedback is reciprocal: whatever a Level draws from below, it feeds back to.
        # Running the same connections backwards is what keeps that structural rather
        # than a second wiring that could drift out of correspondence.
        for index in range(len(self.levels) - 1):
            self.levels[index].w_feedback = self.levels[index + 1].w_input

    def _boundary(
        self, level: Level, input_size: int, fanin: int, rng: np.random.Generator
    ) -> Connections:
        """What arrives at Level 1.

        A Space fed by the Thalamus takes it one-to-one, which the encoders size to
        match. A Space fed by the tops of several other Spaces takes a sparse
        non-local sample, because that convergence has no neighbourhood to draw from:
        nothing makes a Column of one Space a grid neighbour of a Column of another.
        """
        if self._input_mode == "identity":
            take = min(level.n, input_size)
            axis = np.arange(take)
            return Connections(level.n, input_size, axis, axis, np.ones(take))
        if self._input_mode == "sparse":
            return sparse_nonlocal(level.n, input_size, fanin, rng)
        raise ValueError(f"unknown input_mode {self._input_mode!r}")

    @property
    def top(self) -> Level:
        return self.levels[-1]

    def reset(self) -> None:
        for level in self.levels:
            level.reset()

    def describe(self) -> dict:
        """How this Space is sited, and how every one of its Levels is wired.

        Written by the code that built the connections rather than restated by hand,
        so it cannot drift from what actually ran.
        """
        rows = []
        for index, level in enumerate(self.levels):
            counts = level.w_input.describe()
            if index == 0:
                source = self._boundary_source
                rule = ("one-to-one" if self._input_mode == "identity"
                        else f"sparse non-local, {counts['fan_in']} drawn from anywhere")
                receptive = 1
            elif index < self._local_levels:
                source = self.levels[index - 1].name
                rule = f"local pooling, {self._pooling}x{self._pooling} neighbourhood"
                receptive = 1 + index * (self._pooling - 1)
            else:
                source = self.levels[index - 1].name
                rule = f"sparse non-local, {counts['fan_in']} drawn from anywhere"
                receptive = self.shape[0] * self.shape[1]
            rows.append({
                "level": level.name,
                "columns": level.n,
                "shape": list(level.shape),
                "source": source,
                "rule": rule,
                "receptive_field": int(receptive),
                "competition": f"every other Column in its {self._cluster}x{self._cluster} cluster"
                               if index == len(self.levels) - 1 else "8 grid neighbours",
                "competitors": int(level.w_lateral.fan_in().mean()),
                "feedback_from": self.levels[index + 1].name if level.w_feedback else None,
                **counts,
            })
        return {
            "cortical_area": self.cortical_area,
            "modality": self.modality,
            "levels": rows,
        }

    def step(self, drive_in: np.ndarray | None, p: dict) -> None:
        """One synchronous tick over every Level of this Space."""
        exc, inh = p["excitatory"], p["inhibitory"]
        next_state = []

        for index, level in enumerate(self.levels):
            if index == 0:
                source = drive_in if drive_in is not None else np.zeros(level.w_input.n_in)
                drive_l4 = exc * p["thalamic_gain"] * level.w_input.forward(source)
            else:
                drive_l4 = exc * level.w_input.forward(transmit(self.levels[index - 1].l5, p))

            feedback = 0.0
            if level.w_feedback is not None:
                feedback = exc * p["feedback_gain"] * level.w_feedback.backward(
                    transmit(self.levels[index + 1].l5, p)
                )

            drive_l23 = (
                exc * level.l4
                + exc * p["recurrent_gain"] * level.l23
                + feedback
                - inh * p["lateral_gain"] * level.w_lateral.forward(level.l23)
            )
            next_state.append((
                relax(level.l4, drive_l4, p["tau_l4"], p),
                relax(level.l23, drive_l23, p["tau_l23"], p),
                relax(level.l5, exc * level.l23, p["tau_l5"], p),
            ))

        for level, (l4, l23, l5) in zip(self.levels, next_state):
            level.l4, level.l23, level.l5 = l4, l23, l5
