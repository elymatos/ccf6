"""The Thalamus: the sole site of the encoding decision.

It converts one World signal into activation across many Columns of Level 1. Every
encoder lives behind the same interface, so replacing a localist code with a population
code changes this module and nothing downstream — which is the whole reason the
Thalamus is a separate structure rather than wiring inside a Space.

It carries **no state between samples**. A presentation is a sequence, and the moment
the boundary remembered where it had been it would have quietly become the Schema, and
the encoding could no longer be changed independently of everything else.
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

    Chosen because you can look at the picture and know at once whether the right thing
    fired. It installs no similarity between colours, which keeps that available as
    something to find rather than something we supplied.
    """

    def __init__(self, n_colours: int):
        self.n_colours = n_colours
        self.size = n_colours

    def encode(self, value: int, strength: float = 1.0) -> np.ndarray:
        out = np.zeros(self.size)
        out[int(value)] = strength
        return out


class PopulationColour:
    """Colours as overlapping bumps over a ring of broadly tuned Columns."""

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


class LocalForm:
    """The contrast neighbourhood at the stop Ego is looking from.

    Nine Columns for a 3x3 patch. This is what distinguishes the end of a stroke from
    its middle and from a junction — the local evidence a convergence hierarchy has to
    work with before any arrangement is available. It is a *sensory* code: it says what
    is here, not where here is.
    """

    def __init__(self, radius: int = 1):
        self.radius = radius
        self.side = 2 * radius + 1
        self.size = self.side * self.side

    def encode(self, value: np.ndarray, strength: float = 1.0) -> np.ndarray:
        patch = np.asarray(value, dtype=np.float64).ravel()
        if patch.size != self.size:
            raise ValueError(f"expected a {self.side}x{self.side} patch, got {patch.size} values")
        return strength * patch


class LocalistPosition:
    """One Column per World position, on a Grid the same shape as the World.

    Retained as a *sensory* code for where-something-is. It is emphatically not the
    structural code: it is a coordinate handed over rather than integrated, so a
    path-consistency claim made of it would be passed vacuously. The Schema carries
    structure; this carries retinotopy.
    """

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
    "local_form": LocalForm,
    "localist_position": LocalistPosition,
}


class Thalamus:
    """Holds one encoder per Space it projects to."""

    def __init__(self, encoders: dict[str, Encoder]):
        self.encoders = encoders

    def sizes(self) -> dict[str, int]:
        return {name: encoder.size for name, encoder in self.encoders.items()}

    def project(self, signals: dict[str, object], strength: float) -> dict[str, np.ndarray]:
        """One stop of a presentation becomes drive for every Space that has an encoder.

        `strength` is the contrast at that World position, so a cell that differs from
        nothing drives nothing.
        """
        return {
            name: encoder.encode(signals[name], strength)
            for name, encoder in self.encoders.items()
            if name in signals
        }
