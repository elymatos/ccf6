"""Hierarchical populations of cortical-column abstractions.

A Column is the smallest addressable processing population. A Population groups Columns
that receive a common class of evidence; its function comes from its connections and
observed response profile, never from a symbolic value stored in a Column.
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

MODALITIES = ("visual", "auditory", "tactile", "motor", "affective")


def transmit(output: np.ndarray, parameters: dict) -> np.ndarray:
    """Return activation above the declared transmission threshold."""
    return np.maximum(0.0, output - parameters["transmission_threshold"])


def relax(
    current: np.ndarray, drive: np.ndarray, tau: float, parameters: dict
) -> np.ndarray:
    """Relax toward a bounded target without overshoot."""
    target = np.clip(
        drive, parameters["activation_floor"], parameters["activation_ceiling"]
    )
    alpha = 1.0 - np.exp(-parameters["dt"] / tau)
    return current + (target - current) * alpha


def _clusters(shape: tuple[int, int], side: int) -> np.ndarray:
    height, width = shape
    if height % side or width % side:
        raise ValueError(
            f"a cluster of {side} does not tile a {height}x{width} Grid exactly"
        )
    blocks = []
    for top in range(0, height, side):
        for left in range(0, width, side):
            blocks.append(
                [
                    row * width + column
                    for row in range(top, top + side)
                    for column in range(left, left + side)
                ]
            )
    return np.asarray(blocks, dtype=np.int64)


class Level:
    """One grid of Columns and the connections arriving at it."""

    def __init__(self, name: str, shape: tuple[int, int]):
        self.name = name
        self.shape = shape
        self.n = shape[0] * shape[1]
        self.l4 = np.zeros(self.n)
        self.l23 = np.zeros(self.n)
        self.l5 = np.zeros(self.n)
        self.thresholds = np.full(self.n, 0.5)
        self.plasticity = np.ones(self.n)
        self.wins = np.zeros(self.n, dtype=np.int64)
        self.cluster_members: np.ndarray | None = None
        self.input_by_target: np.ndarray | None = None
        self.w_input: Connections | None = None
        self.w_feedback: Connections | None = None
        self.w_lateral: Connections | None = None

    def reset(self) -> None:
        """Clear activity while preserving learned state."""
        self.l4[:] = 0.0
        self.l23[:] = 0.0
        self.l5[:] = 0.0

    def grid(self, layer: str = "l5") -> np.ndarray:
        return getattr(self, layer).reshape(self.shape)


class Population:
    """A hierarchy of Columns receiving sensory or population activity."""

    def __init__(
        self,
        name: str,
        shape: tuple[int, int],
        levels: int,
        input_size: int,
        *,
        role: str,
        modality: str | None,
        sources: tuple[str, ...],
        local_levels: int,
        pooling: int,
        fanin: int,
        cluster: int,
        rng: np.random.Generator,
    ):
        if role not in ("sensory", "association"):
            raise ValueError(f"{name}: role must be sensory or association")
        if modality is not None and modality not in MODALITIES:
            raise ValueError(
                f"{name}: unknown modality {modality!r}; declared: {list(MODALITIES)} or null"
            )
        if role == "sensory" and not modality:
            raise ValueError(f"{name}: a sensory Population needs a modality")
        if role == "association" and not sources:
            raise ValueError(f"{name}: an association Population needs sources")

        self.name = name
        self.shape = shape
        self.role = role
        self.modality = modality
        self.sources = sources
        self.local_levels = local_levels
        self.pooling = pooling
        self.cluster = cluster
        self.levels = [Level(f"{name}.L{index + 1}", shape) for index in range(levels)]

        for index, level in enumerate(self.levels):
            if index == 0:
                level.w_input = sparse_nonlocal(level.n, input_size, fanin, rng)
            elif index < local_levels:
                level.w_input = local_pooling(shape, shape, pooling)
            else:
                level.w_input = sparse_nonlocal(level.n, level.n, fanin, rng)

            level.w_lateral = (
                clustered_competition(shape, cluster)
                if index == len(self.levels) - 1
                else neighbourhood(shape)
            )
            level.cluster_members = _clusters(shape, cluster)
            level.input_by_target = level.w_input.by_target()

        for index in range(len(self.levels) - 1):
            self.levels[index].w_feedback = self.levels[index + 1].w_input

    @property
    def top(self) -> Level:
        return self.levels[-1]

    def reset(self) -> None:
        for level in self.levels:
            level.reset()

    def step(
        self,
        input_drive: np.ndarray,
        parameters: dict,
        top_down: np.ndarray | None = None,
    ) -> None:
        """Update every Level synchronously from current network state."""
        excitation = parameters["excitatory"]
        inhibition = parameters["inhibitory"]
        next_state = []

        for index, level in enumerate(self.levels):
            source = (
                input_drive
                if index == 0
                else transmit(self.levels[index - 1].l5, parameters)
            )
            drive_l4 = excitation * level.w_input.forward(source)

            feedback = np.zeros(level.n)
            if level.w_feedback is not None:
                feedback = excitation * parameters["feedback_gain"] * level.w_feedback.backward(
                    transmit(self.levels[index + 1].l5, parameters)
                )
            if index == len(self.levels) - 1 and top_down is not None:
                feedback += parameters["feedback_gain"] * top_down

            drive_l23 = (
                excitation * level.l4
                + excitation * parameters["recurrent_gain"] * level.l23
                + feedback
                - inhibition
                * parameters["lateral_gain"]
                * level.w_lateral.forward(level.l23)
            )
            next_state.append(
                (
                    relax(level.l4, drive_l4, parameters["tau_l4"], parameters),
                    relax(level.l23, drive_l23, parameters["tau_l23"], parameters),
                    relax(level.l5, excitation * level.l23, parameters["tau_l5"], parameters),
                )
            )

        for level, (l4, l23, l5) in zip(self.levels, next_state):
            level.l4, level.l23, level.l5 = l4, l23, l5

    def learn(self, input_drive: np.ndarray, rule) -> int:
        changed = 0
        for index, level in enumerate(self.levels):
            source = input_drive if index == 0 else self.levels[index - 1].l5
            changed += rule.apply(level, source)
        return changed

    def describe(self) -> dict:
        rows = []
        for index, level in enumerate(self.levels):
            counts = level.w_input.describe()
            rows.append(
                {
                    "level": level.name,
                    "columns": level.n,
                    "shape": list(level.shape),
                    "source": "sensory adapter" if index == 0 and self.role == "sensory" else (
                        ", ".join(self.sources) if index == 0 else self.levels[index - 1].name
                    ),
                    "rule": (
                        f"local pooling, {self.pooling}x{self.pooling} neighbourhood"
                        if 0 < index < self.local_levels
                        else f"sparse non-local, {counts['fan_in']} sources"
                    ),
                    "competition": (
                        f"cluster {self.cluster}x{self.cluster}"
                        if index == len(self.levels) - 1
                        else "8 grid neighbours"
                    ),
                    "competitors": int(level.w_lateral.fan_in().mean()),
                    **counts,
                }
            )
        return {
            "role": self.role,
            "modality": self.modality,
            "sources": list(self.sources),
            "levels": rows,
        }
