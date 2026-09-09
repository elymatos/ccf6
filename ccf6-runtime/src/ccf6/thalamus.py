"""The Thalamus: the sole site of the encoding decision.

It converts one World signal into activation across many Columns of Level 1. Every
encoder lives behind the same interface, so replacing a localist code with a population
code changes this module and nothing downstream — which is the whole reason the
Thalamus is a separate structure rather than wiring inside a Space.

It carries **no state between samples**. A presentation is a sequence, and the moment
the boundary remembered where it had been it would have quietly become the Schema, and
the encoding could no longer be changed independently of everything else.

It carries **no separate strength channel** either (ADR-0009). What is shown decides
which Columns are driven; nothing decides how hard. A magnitude alongside the signal is
a second, undeclared code, and Columns add their inputs, so whatever it carries arrives
everywhere at once.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np


class Encoder(Protocol):
    """One signal in, a Level-1 activation vector out."""

    size: int

    def encode(self, value) -> np.ndarray: ...


class LocalistColour:
    """One Column per colour. Colour 3 is Column 3 firing, everything else silent.

    Chosen because you can look at the picture and know at once whether the right thing
    fired. It installs no similarity between colours, which keeps that available as
    something to find rather than something we supplied.
    """

    def __init__(self, n_colours: int):
        self.n_colours = n_colours
        self.size = n_colours

    def encode(self, value: int) -> np.ndarray:
        out = np.zeros(self.size)
        out[int(value)] = 1.0
        return out


class PopulationColour:
    """Colours as overlapping bumps over a ring of broadly tuned Columns."""

    def __init__(self, n_colours: int, size: int, width: float = 1.2):
        self.n_colours = n_colours
        self.size = size
        self.width = width
        self._centres = np.linspace(0.0, size, n_colours, endpoint=False)

    def encode(self, value: int) -> np.ndarray:
        positions = np.arange(self.size, dtype=np.float64)
        offset = np.abs(positions - self._centres[int(value)])
        circular = np.minimum(offset, self.size - offset)
        return np.exp(-0.5 * (circular / self.width) ** 2)


class LocalShape:
    """The neighbourhood the stop is looked at from, graded by eccentricity.

    Ego is focused somewhere, but the rest of what is in view is not silent. So the
    window is larger than the focus and its drive falls off with distance: full at the
    cell being looked at, less on the ring of 8 neighbours, less again beyond. A fovea
    with a periphery, and the 8 neighbours that make a stroke a stroke rather than a
    dot are the innermost ring.

    The window is **ego-centric**: it is centred on the stop and padded rather than
    clipped, so a figure at the World frame encodes exactly as it does in the middle and
    the same figure at any origin encodes identically. Retinotopy would be a different
    Space, and `LocalistPosition` is it.

    The eccentricity profile is a declared constant (ADR-0006), fixed for the life of a
    run and identical at every stop. It is therefore not a magnitude channel in the sense
    ADR-0009 removed: it carries nothing about what is being shown, cannot vary with the
    stimulus, and has no way to smuggle position into a Space.

    **What this encoder cannot see, and it is not a matter of degree.** Summed over a
    presentation, one fixed window around every one of a figure's cells computes that
    figure's local autocorrelation: entry *d* counts the cell pairs separated by offset
    *d*, weighted by the profile. An autocorrelation is centrally symmetric, and a
    symmetric profile keeps it so, so the summed code is **identical for any figure and
    its 180-degree rotation** — T and a bottom sum to the same numbers. Widening the
    window or grading it does not help: the blindness is in the summing, and a wider
    window is a wider sum.

    The per-stop windows do all differ, and so do their multisets, so the distinction
    survives in *which* windows occurred and in what order. That is the traversal, and it
    belongs to the Schema and the Index.
    """

    #: Drive by ring: the focused cell, its 8 neighbours, then the next ring out.
    ECCENTRICITY: tuple[float, ...] = (1.0, 0.6, 0.2)

    def __init__(self, radius: int = 2, eccentricity: tuple[float, ...] | None = None):
        self.radius = radius
        self.side = 2 * radius + 1
        self.size = self.side * self.side
        profile = tuple(eccentricity if eccentricity is not None else self.ECCENTRICITY)
        if len(profile) < radius + 1:
            raise ValueError(
                f"a radius of {radius} needs {radius + 1} eccentricity values, got {len(profile)}"
            )
        self.eccentricity = profile[: radius + 1]
        offsets = np.arange(-radius, radius + 1)
        rings = np.maximum(np.abs(offsets)[:, None], np.abs(offsets)[None, :])
        self._weights = np.asarray(self.eccentricity)[rings]

    def encode(self, value: np.ndarray) -> np.ndarray:
        window = np.asarray(value, dtype=np.float64)
        if window.size != self.size:
            raise ValueError(
                f"expected a {self.side}x{self.side} window, got {window.size} values"
            )
        return (window.reshape(self.side, self.side) * self._weights).ravel()


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

    def encode(self, value: tuple[int, int]) -> np.ndarray:
        i, j = value
        out = np.zeros(self.size)
        out[i * self.world_size + j] = 1.0
        return out


ENCODERS = {
    "localist_colour": LocalistColour,
    "population_colour": PopulationColour,
    "local_shape": LocalShape,
    "localist_position": LocalistPosition,
}


class Thalamus:
    """Holds one encoder per Space it projects to."""

    def __init__(self, encoders: dict[str, Encoder]):
        self.encoders = encoders

    def sizes(self) -> dict[str, int]:
        return {name: encoder.size for name, encoder in self.encoders.items()}

    def project(self, signals: dict[str, object]) -> dict[str, np.ndarray]:
        """One stop of a presentation becomes drive for every Space that has an encoder.

        Every encoder is driven at unit strength. There is no magnitude argument, so
        there is nowhere for a second code to hide (ADR-0009).
        """
        return {
            name: encoder.encode(signals[name])
            for name, encoder in self.encoders.items()
            if name in signals
        }
