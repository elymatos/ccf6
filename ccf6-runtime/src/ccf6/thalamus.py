"""Stateless sensory adapters at the network boundary.

Adapters transduce experimental values into distributed activation. They do not learn,
retain sequence state, or assign cognitive meaning; downstream function is learned from
connectivity and activity.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np


class Encoder(Protocol):
    size: int

    def encode(self, value) -> np.ndarray: ...


class LocalistColour:
    def __init__(self, n_colours: int):
        self.size = n_colours

    def encode(self, value: int) -> np.ndarray:
        output = np.zeros(self.size)
        output[int(value)] = 1.0
        return output


class PopulationColour:
    """Represent colours as overlapping activity over a ring."""

    def __init__(self, n_colours: int, size: int, width: float = 1.2):
        self.size = size
        self.width = width
        self.centres = np.linspace(0.0, size, n_colours, endpoint=False)

    def encode(self, value: int) -> np.ndarray:
        positions = np.arange(self.size, dtype=np.float64)
        offset = np.abs(positions - self.centres[int(value)])
        circular = np.minimum(offset, self.size - offset)
        return np.exp(-0.5 * (circular / self.width) ** 2)


class LocalShape:
    """Encode the foreground around the current focus with graded eccentricity."""

    ECCENTRICITY: tuple[float, ...] = (1.0, 0.6, 0.2)

    def __init__(self, radius: int = 2, eccentricity: tuple[float, ...] | None = None):
        self.radius = radius
        self.side = 2 * radius + 1
        self.size = self.side * self.side
        profile = tuple(eccentricity or self.ECCENTRICITY)
        if len(profile) < radius + 1:
            raise ValueError(
                f"a radius of {radius} needs {radius + 1} eccentricity values, got {len(profile)}"
            )
        self.eccentricity = profile[: radius + 1]
        offsets = np.arange(-radius, radius + 1)
        rings = np.maximum(np.abs(offsets)[:, None], np.abs(offsets)[None, :])
        self.weights = np.asarray(self.eccentricity)[rings]

    def encode(self, value: np.ndarray) -> np.ndarray:
        window = np.asarray(value, dtype=np.float64)
        if window.size != self.size:
            raise ValueError(
                f"expected a {self.side}x{self.side} window, got {window.size} values"
            )
        return (window.reshape(self.side, self.side) * self.weights).ravel()


ENCODERS = {
    "localist_colour": LocalistColour,
    "population_colour": PopulationColour,
    "local_shape": LocalShape,
}


class Thalamus:
    """Apply one stateless encoder per sensory Population."""

    def __init__(self, encoders: dict[str, Encoder]):
        self.encoders = encoders

    def project(self, signals: dict[str, object]) -> dict[str, np.ndarray]:
        return {
            name: encoder.encode(signals[name])
            for name, encoder in self.encoders.items()
            if name in signals
        }
