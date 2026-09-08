"""The World: an arrangement CCF6 is shown, holding no Columns of its own.

A World is a square grid of colour indices. Colour 0 is white, and white is an
ordinary colour rather than a gap — a blank cell is a fact, not an absence.

What reaches the Thalamus is the colour field, at unit strength. It was once the
*contrast* field — how much a cell differs from its neighbours — on the premise that a
framework meant to record relations should be shown relations rather than things. That
premise moved (ADR-0009): contrast is not translation invariant, because a figure
touching the World's frame scores lower than the same figure in the middle, and it was
also serving as drive magnitude, so it carried that non-invariance into every Space at
once. The relational quantity supplied at the boundary is now the **Relation** between
two sampled World positions, and nothing else.

`contrast()` survives as something one can compute *about* a World and draw. Nothing in
the encoding path calls it.
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
        have, and off-field neighbours count as not differing: the frame of the World is
        not an edge in the World.

        **This is still not translation invariant**, and that is why it is no longer the
        input code (ADR-0009). Counting an absent neighbour as not-differing makes a
        figure touching the frame score *lower* than the same figure in the middle. One
        Object at its 80 fitting origins in a 12x12 World has nine distinct contrast
        signatures. The full divisor removed the inflation, not the dependence.
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

    def foreground(self, radius: int) -> np.ndarray:
        """The figure as a mask, padded by `radius` cells of background.

        Padded with background rather than reflected or wrapped, so a patch read at the
        World's frame is the same patch read in the middle: an Object's neighbourhood
        does not depend on where the Object was put (ADR-0004).

        A mask rather than the colour indices, because a Column adds its inputs and a
        raw index would drive one colour seven times harder than another — the same
        confusion of strength with identity that ADR-0009 removed. What colour a cell is
        belongs to the colour Space; whether a cell is filled belongs here.
        """
        return np.pad((self.cells != self.background).astype(np.float64), radius)

    def sampled_positions(self, threshold: float = 0.0) -> list[tuple[int, int]]:
        """World positions carrying contrast above threshold.

        One always looks from somewhere, but the places worth looking at are the ones
        with structure in them. This is a segmentation heuristic, not the input path;
        see `Presentation.of_contrast` for why it takes its threshold explicitly.
        """
        field = self.contrast()
        return [(int(i), int(j)) for i, j in zip(*np.nonzero(field > threshold))]
