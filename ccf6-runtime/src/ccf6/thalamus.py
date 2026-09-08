"""The Thalamus: the sole site of the encoding decision.

It converts one World signal into activation across many Columns of Level 1. Every
encoder lives behind the same interface, so replacing a localist code with a
population code changes this module and nothing downstream — which is the whole
reason the Thalamus is a separate structure rather than wiring inside a Space.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np


class Encoder(Protocol):
    """One signal in, a Level-1 activation vector out."""

    size: int

    def encode(self, value, strength: float = 1.0) -> np.ndarray: ...


class LocalistColour:
    """One Column per colour. Colour 3 is Column 3 firing, everything else silent.

    The starting encoder, chosen because you can look at the picture and know at once
    whether the right thing fired. It installs no similarity between colours, which
    keeps that available as something to find rather than something we supplied.
    """

    def __init__(self, n_colours: int):
        self.n_colours = n_colours
        self.size = n_colours

    def encode(self, value: int, strength: float = 1.0) -> np.ndarray:
        out = np.zeros(self.size)
        out[int(value)] = strength
        return out


class PopulationColour:
    """Colours as overlapping bumps over a ring of broadly tuned Columns.

    Not used by the first experiment. It is here so that the swap D3 asked for is a
    one-line change in an experiment file rather than a refactor.
    """

    def __init__(self, n_colours: int, size: int, width: float = 1.2):
        self.n_colours = n_colours
        self.size = size
        self.width = width
        self._centres = np.linspace(0.0, size, n_colours, endpoint=False)

    def encode(self, value: int, strength: float = 1.0) -> np.ndarray:
        positions = np.arange(self.size, dtype=np.float64)
        offset = np.abs(positions - self._centres[int(value)])
        circular = np.minimum(offset, self.size - offset)
        return strength * np.exp(-0.5 * (circular / self.width) ** 2)


class LocalistPosition:
    """One Column per World position, on a Grid the same shape as the World."""

    def __init__(self, world_size: int):
        self.world_size = world_size
        self.size = world_size * world_size

    def encode(self, value: tuple[int, int], strength: float = 1.0) -> np.ndarray:
        i, j = value
        out = np.zeros(self.size)
        out[i * self.world_size + j] = strength
        return out


ENCODERS = {
    "localist_colour": LocalistColour,
    "population_colour": PopulationColour,
    "localist_position": LocalistPosition,
}


class Thalamus:
    """Holds one encoder per Space it projects to."""

    def __init__(self, colour: Encoder, position: Encoder):
        self.colour = colour
        self.position = position

    def project(
        self, colour_index: int, position: tuple[int, int], strength: float
    ) -> dict[str, np.ndarray]:
        """One sample of the World becomes drive for two Spaces.

        `strength` is the contrast at that World position, so a cell that differs
        from nothing drives nothing.
        """
        return {
            "colour": self.colour.encode(colour_index, strength),
            "position": self.position.encode(position, strength),
        }
