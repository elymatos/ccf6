"""Areas, Levels, and the Column circuit.

A Column holds three private activations. A Level is a Grid of Columns. An Area is a
stack of Levels. Connections between Columns are dense matrices: the grids are small
enough that sparsity would cost readability and buy nothing.

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


def transmit(l5: np.ndarray, p: dict) -> np.ndarray:
    """What a Column actually sends: its output above a transmission threshold.

    The activation floor means no Column is ever silent, so raw L5 carries a constant
    background. Summed over a fan-in of sixteen that background outweighs the signal.
    Subtracting the threshold before transmission keeps the floor doing its job — the
    network cannot die — without letting it accumulate through depth.
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
        self.w_input: np.ndarray | None = None      # into L4, from below or Thalamus
        self.w_feedback: np.ndarray | None = None   # into L2/3, from the Level above
        self.w_lateral: np.ndarray | None = None    # into L2/3, inhibitory, same Level

    def reset(self) -> None:
        self.l4[:] = 0.0
        self.l23[:] = 0.0
        self.l5[:] = 0.0

    def grid(self, layer: str = "l5") -> np.ndarray:
        return getattr(self, layer).reshape(self.shape)


def local_pooling(shape: tuple[int, int], source_shape: tuple[int, int], k: int) -> np.ndarray:
    """Each Column draws from a k x k neighbourhood centred on its own position.

    Receptive fields grow additively with depth: RF = 1 + level * (k - 1). Local
    structure below, which is what the early Levels are for.
    """
    h, w = shape
    sh, sw = source_shape
    weights = np.zeros((h * w, sh * sw))
    half = k // 2
    scale_i, scale_j = sh / h, sw / w
    for i in range(h):
        for j in range(w):
            ci, cj = int(i * scale_i), int(j * scale_j)
            for di in range(-half, half + 1):
                for dj in range(-half, half + 1):
                    si, sj = ci + di, cj + dj
                    if 0 <= si < sh and 0 <= sj < sw:
                        weights[i * w + j, si * sw + sj] = 1.0
    return weights


def sparse_nonlocal(
    shape: tuple[int, int], source_shape: tuple[int, int], fanin: int, rng: np.random.Generator
) -> np.ndarray:
    """Each Column draws from a random subset of the Level below, from anywhere.

    Above a certain depth, restricting convergence to a neighbourhood puts a ceiling
    on receptive-field size that no number of Levels can lift. Sparse non-local
    sampling reaches the whole Level immediately, and gives every Column a different,
    overlapping input set — which is what makes distinct convergence possible at all.
    """
    n = shape[0] * shape[1]
    source_n = source_shape[0] * source_shape[1]
    weights = np.zeros((n, source_n))
    take = min(fanin, source_n)
    for row in range(n):
        picks = rng.choice(source_n, size=take, replace=False)
        weights[row, picks] = 1.0
    return weights


def neighbourhood_inhibition(shape: tuple[int, int]) -> np.ndarray:
    """8-neighbourhood competition. No self-inhibition.

    8 rather than 4 so that a diagonal arrangement does not compete differently from
    an axis-aligned one.
    """
    h, w = shape
    n = h * w
    weights = np.zeros((n, n))
    for i in range(h):
        for j in range(w):
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if 0 <= ni < h and 0 <= nj < w:
                        weights[i * w + j, ni * w + nj] = 1.0
    counts = weights.sum(axis=1, keepdims=True)
    return np.divide(weights, counts, out=np.zeros_like(weights), where=counts > 0)


def global_inhibition(shape: tuple[int, int]) -> np.ndarray:
    """All-to-all competition, for a top Level whose Columns are not grid neighbours.

    Once convergence stops being spatial, competition cannot stay spatial either:
    two Columns standing for different things have no reason to be adjacent.
    """
    n = shape[0] * shape[1]
    weights = np.ones((n, n)) - np.eye(n)
    return weights / max(n - 1, 1)


class Area:
    """A stack of Levels sharing one functional specialization."""

    def __init__(
        self,
        name: str,
        shape: tuple[int, int],
        n_levels: int,
        input_size: int,
        *,
        local_levels: int,
        pooling: int,
        fanin: int,
        rng: np.random.Generator,
        input_mode: str = "identity",
    ):
        self.name = name
        self.shape = shape
        self._input_mode = input_mode
        self._local_levels = local_levels
        self._pooling = pooling
        self.levels = [Level(f"{name}.L{i + 1}", shape) for i in range(n_levels)]

        for index, level in enumerate(self.levels):
            if index == 0:
                # Thalamic drive arrives here. An Area fed by the Thalamus takes it
                # one-to-one, which the encoders size to match. A Hub is fed by the
                # tops of several Areas instead, and that convergence is non-local by
                # nature: nothing makes a colour Column and a position Column
                # neighbours, so there is no neighbourhood to draw from.
                if input_mode == "identity":
                    level.w_input = np.eye(level.n, input_size)
                elif input_mode == "sparse":
                    take = min(fanin, input_size)
                    level.w_input = np.zeros((level.n, input_size))
                    for row in range(level.n):
                        picks = rng.choice(input_size, size=take, replace=False)
                        level.w_input[row, picks] = 1.0
                else:
                    raise ValueError(f"unknown input_mode {input_mode!r}")
            elif index < local_levels:
                level.w_input = local_pooling(shape, shape, pooling)
            else:
                level.w_input = sparse_nonlocal(shape, shape, fanin, rng)

            is_top = index == len(self.levels) - 1
            level.w_lateral = (
                global_inhibition(shape) if is_top else neighbourhood_inhibition(shape)
            )

        # Feedback is reciprocal: whatever a Level draws from below, it feeds back to.
        for index in range(len(self.levels) - 1):
            above = self.levels[index + 1]
            self.levels[index].w_feedback = above.w_input.T

    def describe(self) -> list[dict]:
        """How every Level of this Area is wired, in plain counts.

        Written by the code that built the connections rather than restated by hand,
        so it cannot drift from what actually ran.
        """
        rows = []
        for index, level in enumerate(self.levels):
            incoming = (level.w_input > 0).sum(axis=1)
            lateral = (level.w_lateral > 0).sum(axis=1)
            if index == 0:
                source = "Thalamus" if self._input_mode == "identity" else "tops of other Areas"
                rule = ("one-to-one" if self._input_mode == "identity"
                        else f"sparse non-local, {int(incoming.mean())} drawn from anywhere")
                receptive = 1
            elif index < self._local_levels:
                source = f"{self.name}.L{index}"
                rule = f"local pooling, {self._pooling}x{self._pooling} neighbourhood"
                receptive = 1 + index * (self._pooling - 1)
            else:
                source = f"{self.name}.L{index}"
                rule = f"sparse non-local, {int(incoming.mean())} drawn from anywhere"
                receptive = self.shape[0] * self.shape[1]
            rows.append({
                "level": level.name,
                "columns": level.n,
                "shape": list(level.shape),
                "source": source,
                "rule": rule,
                "fan_in": int(incoming.mean()),
                "fan_in_min": int(incoming.min()),
                "fan_in_max": int(incoming.max()),
                "receptive_field": int(receptive),
                "competition": "every other Column" if index == len(self.levels) - 1
                               else "8 grid neighbours",
                "competitors": int(lateral.mean()),
                "feedback_from": self.levels[index + 1].name if level.w_feedback is not None else None,
            })
        return rows

    @property
    def top(self) -> Level:
        return self.levels[-1]

    def reset(self) -> None:
        for level in self.levels:
            level.reset()

    def step(self, thalamic_drive: np.ndarray | None, p: dict) -> None:
        """One synchronous tick over every Level of this Area."""
        exc, inh = p["excitatory"], p["inhibitory"]
        next_state = []

        for index, level in enumerate(self.levels):
            if index == 0:
                source = thalamic_drive if thalamic_drive is not None else np.zeros(level.w_input.shape[1])
                drive_l4 = exc * p["thalamic_gain"] * (level.w_input @ source)
            else:
                drive_l4 = exc * (level.w_input @ transmit(self.levels[index - 1].l5, p))

            feedback = 0.0
            if level.w_feedback is not None:
                feedback = exc * p["feedback_gain"] * (
                    level.w_feedback @ transmit(self.levels[index + 1].l5, p)
                )

            drive_l23 = (
                exc * level.l4
                + exc * p["recurrent_gain"] * level.l23
                + feedback
                - inh * p["lateral_gain"] * (level.w_lateral @ level.l23)
            )
            drive_l5 = exc * level.l23

            next_state.append(
                (
                    relax(level.l4, drive_l4, p["tau_l4"], p),
                    relax(level.l23, drive_l23, p["tau_l23"], p),
                    relax(level.l5, drive_l5, p["tau_l5"], p),
                )
            )

        for level, (l4, l23, l5) in zip(self.levels, next_state):
            level.l4, level.l23, level.l5 = l4, l23, l5
