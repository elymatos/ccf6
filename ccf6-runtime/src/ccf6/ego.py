"""Ego, and the sequence in which a figure is shown.

A figure with several parts cannot be presented as a single signal: the arrangement is
the thing being represented, and an arrangement is only visible across more than one
sample. So a presentation is a **sequence**. Ego visits the World positions carrying
structure; at each stop the Thalamus encodes what is there; the offset to the next stop
is the **Relation**.

The Relation is *given* — geometry supplies it, because two positions sampled together
have an offset whether or not anything moved (ADR-0003). Enacted Relations, where Ego
moves under a policy and the movement supplies the offset, are a later addition to be
measured against this baseline rather than assumed into it.

The visiting order is declared rather than discovered, so that two runs of one
experiment see the same sequence and a run remains reproducible from its definition.

**Figure-ground segmentation is not solved here and is not claimed to be.** Contrast
marks a boundary region, not a figure: for a thin-stroke figure the figure's own cells
and the background cells hugging it occupy overlapping contrast ranges, so no threshold
separates them in general. An experiment therefore presents a known Object and Ego
visits its parts. `of_contrast` remains for the case where the question really is "look
wherever there is structure", and it takes its threshold explicitly so that nobody
acquires a segmenter by accident.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ccf6.world import World

Position = tuple[int, int]


@dataclass(frozen=True)
class Step:
    """One stop: where Ego looked, what was there, and how it got there.

    `relation` is None for the first stop. One always looks from somewhere before one
    has moved, and inventing an offset to the origin would put a World coordinate into
    the structural code by the back door.
    """

    position: Position
    colour: int
    contrast: float
    relation: Position | None


@dataclass(frozen=True)
class Presentation:
    """A figure, as the sequence of stops that shows it."""

    steps: list[Step]

    @classmethod
    def over(cls, world: World, positions: list[Position], order: str) -> Presentation:
        """The core constructor: show these positions, in this declared order."""
        positions = visiting_order(order)(list(positions))
        field = world.contrast()
        steps = []
        for index, position in enumerate(positions):
            previous = positions[index - 1] if index else None
            steps.append(
                Step(
                    position=position,
                    colour=int(world.cells[position]),
                    contrast=float(field[position]),
                    relation=None if previous is None else
                    (position[0] - previous[0], position[1] - previous[1]),
                )
            )
        return cls(steps)

    @classmethod
    def of_object(
        cls, world: World, obj, origin: Position, order: str = "raster"
    ) -> Presentation:
        """Show a known Object: Ego visits its parts and nothing else.

        The Object supplies the figure, so no segmentation decision is being made and
        none is being hidden.
        """
        return cls.over(world, [(i, j) for i, j, _ in obj.cells_at(origin)], order)

    @classmethod
    def of_contrast(cls, world: World, threshold: float, order: str = "raster") -> Presentation:
        """Show wherever contrast exceeds a threshold the caller states.

        No default: a threshold that separates figure from background for one figure
        will not for another, so choosing one is the experiment's business (ADR-0006).
        """
        return cls.over(world, world.sampled_positions(threshold), order)

    def relations(self) -> list[Position]:
        return [s.relation for s in self.steps if s.relation is not None]

    def describe(self) -> dict:
        return {
            "stops": len(self.steps),
            "positions": [list(s.position) for s in self.steps],
            "relations": [list(s.relation) for s in self.steps if s.relation is not None],
        }


def _raster(positions: list[Position]) -> list[Position]:
    """Row by row, left to right. Arbitrary, but declared and reproducible."""
    return sorted(positions)


def _nearest(positions: list[Position]) -> list[Position]:
    """Always step to the closest unvisited part, starting from the first in raster order.

    Keeps Relations small, which matters once the Schema's modules have short periods:
    a long jump can wrap a module and lose the distinction a short step preserves.
    """
    if not positions:
        return []
    remaining = sorted(positions)
    walk = [remaining.pop(0)]
    while remaining:
        here = walk[-1]
        nearest = min(
            remaining,
            key=lambda q: ((q[0] - here[0]) ** 2 + (q[1] - here[1]) ** 2, q),
        )
        remaining.remove(nearest)
        walk.append(nearest)
    return walk


ORDERS: dict[str, Callable[[list[Position]], list[Position]]] = {
    "raster": _raster,
    "nearest": _nearest,
}


def visiting_order(name: str) -> Callable[[list[Position]], list[Position]]:
    """The declared orders. An unknown one is an error rather than a silent default."""
    if name not in ORDERS:
        raise KeyError(f"unknown visiting order {name!r}; declared: {sorted(ORDERS)}")
    return ORDERS[name]
