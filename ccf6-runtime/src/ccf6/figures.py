"""The figures used to probe learned conjunctions and categories.

Objects carry no origin, so one arrangement can be presented at varied positions. The
four figures share the same coarse feature inventory while differing in arrangement.
They expose whether the network develops stable, context-sensitive convergence rather
than succeeding from a unique feature supplied at the boundary.
"""

from __future__ import annotations

from ccf6.world import Object

#: Stroke length either side of the junction. Long enough that no 3x3 patch spans the
#: junction and both terminations, which is what stops a single local feature from
#: standing in for the arrangement.
ARM = 2


def _bar(along: str, offset: int, extent: int) -> list[tuple[int, int]]:
    if along == "row":
        return [(offset, d) for d in range(-extent, extent + 1)]
    return [(d, offset) for d in range(-extent, extent + 1)]


def _stem(towards: str, extent: int) -> list[tuple[int, int]]:
    steps = range(1, extent + 1)
    return {
        "down": [(d, 0) for d in steps],
        "up": [(-d, 0) for d in steps],
        "right": [(0, d) for d in steps],
        "left": [(0, -d) for d in steps],
    }[towards]


def _figure(name: str, bar_along: str, towards: str, colour: int = 1) -> Object:
    cells = _bar(bar_along, 0, ARM) + _stem(towards, ARM)
    return Object(name, tuple((cell, colour) for cell in cells))


#: The confusion set. Identical parts, four arrangements.
TEE = _figure("T", "row", "down")
TEE_UP = _figure("⊥", "row", "up")
TEE_RIGHT = _figure("⊢", "column", "right")
TEE_LEFT = _figure("⊣", "column", "left")

FIGURES = {"T": TEE, "T-up": TEE_UP, "T-right": TEE_RIGHT, "T-left": TEE_LEFT}

#: Colours crossed with figures so association Columns can encounter recurring
#: conjunctions. Index 0 is the World's background and is excluded.
COLOURS = (1, 2, 3, 4)


def named(names: list[str]) -> list[Object]:
    unknown = [n for n in names if n not in FIGURES]
    if unknown:
        raise KeyError(f"unknown figures {unknown}; declared: {sorted(FIGURES)}")
    return [FIGURES[n] for n in names]


def in_colour(obj: Object, colour: int) -> Object:
    """The same arrangement, shown in another colour.

    Shape and colour stay orthogonal at the sensory boundary. A Column responding to
    their conjunction must therefore receive and integrate both pathways.
    """
    if colour < 1:
        raise ValueError(f"colour {colour} is the World's background; a figure needs its own")
    return Object(obj.name, tuple((offset, colour) for offset, _ in obj.parts))
