"""Presentations sampled from an external World.

Sampling is experimental apparatus, not a cognitive structure. A presentation retains
its samples so sequence-sensitive network behaviour can be measured without installing
a separate sequence processor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ccf6.world import World

Position = tuple[int, int]


@dataclass(frozen=True)
class Sample:
    position: Position
    colour: int


@dataclass(frozen=True)
class Presentation:
    samples: list[Sample]

    @classmethod
    def over(cls, world: World, positions: list[Position], order: str) -> Presentation:
        ordered = visiting_order(order)(list(positions))
        return cls([Sample(position, int(world.cells[position])) for position in ordered])

    @classmethod
    def of_object(
        cls, world: World, obj, origin: Position, order: str = "raster"
    ) -> Presentation:
        return cls.over(
            world,
            [(row, column) for row, column, _ in obj.cells_at(origin)],
            order,
        )

    def describe(self) -> dict:
        return {
            "samples": len(self.samples),
            "positions": [list(sample.position) for sample in self.samples],
        }


def _raster(positions: list[Position]) -> list[Position]:
    return sorted(positions)


def _nearest(positions: list[Position]) -> list[Position]:
    if not positions:
        return []
    remaining = sorted(positions)
    walk = [remaining.pop(0)]
    while remaining:
        here = walk[-1]
        nearest = min(
            remaining,
            key=lambda position: (
                (position[0] - here[0]) ** 2 + (position[1] - here[1]) ** 2,
                position,
            ),
        )
        remaining.remove(nearest)
        walk.append(nearest)
    return walk


ORDERS: dict[str, Callable[[list[Position]], list[Position]]] = {
    "raster": _raster,
    "nearest": _nearest,
}


def visiting_order(name: str) -> Callable[[list[Position]], list[Position]]:
    if name not in ORDERS:
        raise KeyError(f"unknown visiting order {name!r}; declared: {sorted(ORDERS)}")
    return ORDERS[name]
