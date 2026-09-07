"""The World: an arrangement CCF6 is shown, holding no Columns of its own.

A World is a square grid of colour indices. Colour 0 is white, and white is an
ordinary colour rather than a gap — a blank cell is a fact, not an absence.

What reaches the Thalamus is not the colour field but its *contrast*: how much a cell
differs from its neighbours. That is a deliberate premise: the framework is meant to
record relations between things rather than the things themselves, so a region with no
internal relations registers as empty. A uniform white field produces almost nothing,
and that is intended behaviour, not a defect.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

#: Index 0 is white. The palette is localist at the World boundary; how a colour index
#: becomes activation is the Thalamus's decision, not the World's.
PALETTE = ("white", "red", "green", "blue", "yellow", "cyan", "magenta", "black")

NEIGHBOUR_OFFSETS = tuple(
    (di, dj) for di in (-1, 0, 1) for dj in (-1, 0, 1) if (di, dj) != (0, 0)
)


@dataclass(frozen=True)
class Object:
    """A configuration of coloured cells, defined by the arrangement of its parts.

    `parts` holds ((di, dj), colour) pairs whose offsets are relative to the Object's
    own origin, never World coordinates: the same arrangement placed elsewhere is the
    same Object (ADR-0004). An Object knows nothing about where it is.
    """

    name: str
    parts: tuple[tuple[tuple[int, int], int], ...]

    def cells_at(self, origin: tuple[int, int]) -> list[tuple[int, int, int]]:
        oi, oj = origin
        return [(oi + di, oj + dj, colour) for (di, dj), colour in self.parts]

    def relations(self) -> list[tuple[int, int]]:
        """The part-relative structure: every offset between two parts.

        This is what ADR-0004 says gets stored. It carries no origin, so it is
        identical for the same Object at every World position.
        """
        offsets = []
        for (ai, aj), _ in self.parts:
            for (bi, bj), _ in self.parts:
                if (ai, aj) != (bi, bj):
                    offsets.append((bi - ai, bj - aj))
        return sorted(offsets)


class World:
    """A square grid of colour indices."""

    def __init__(self, size: int, background: int = 0):
        self.size = size
        self.background = background
        self.cells = np.full((size, size), background, dtype=np.int16)

    def clear(self) -> None:
        self.cells[:] = self.background

    def place(self, colour: int, position: tuple[int, int]) -> None:
        i, j = position
        if not (0 <= i < self.size and 0 <= j < self.size):
            raise IndexError(f"position {position} outside a {self.size}x{self.size} World")
        self.cells[i, j] = colour

    def place_object(self, obj: Object, origin: tuple[int, int]) -> None:
        for i, j, colour in obj.cells_at(origin):
            self.place(colour, (i, j))

    def fits(self, obj: Object, origin: tuple[int, int]) -> bool:
        return all(
            0 <= i < self.size and 0 <= j < self.size
            for i, j, _ in obj.cells_at(origin)
        )

    def contrast(self) -> np.ndarray:
        """Per-cell fraction of neighbours whose colour differs from this cell's.

        The divisor is the full neighbourhood, not the neighbours a cell happens to
        have. Scoring border cells against their own smaller neighbourhood inflates
        their contrast, so the same Object registers more strongly near an edge than
        in the middle — which would break the translation invariance ADR-0004 rests
        on. Off-field neighbours count as not differing: the frame of the World is not
        an edge in the World.
        """
        differing = np.zeros((self.size, self.size), dtype=np.float64)
        for di, dj in NEIGHBOUR_OFFSETS:
            shifted = np.full_like(self.cells, -1)
            src_i = slice(max(0, -di), self.size - max(0, di))
            src_j = slice(max(0, -dj), self.size - max(0, dj))
            dst_i = slice(max(0, di), self.size - max(0, -di))
            dst_j = slice(max(0, dj), self.size - max(0, -dj))
            shifted[dst_i, dst_j] = self.cells[src_i, src_j]
            valid = shifted >= 0
            differing += valid & (shifted != self.cells)
        return differing / len(NEIGHBOUR_OFFSETS)

    def sampled_positions(self, threshold: float = 0.0) -> list[tuple[int, int]]:
        """World positions carrying contrast above threshold.

        One always looks from somewhere, but the places worth looking at are the ones
        with structure in them.
        """
        field = self.contrast()
        return [(int(i), int(j)) for i, j in zip(*np.nonzero(field > threshold))]
