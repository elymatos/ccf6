"""The figures an experiment can show.

Objects are part-relative and carry no origin (ADR-0004), so the same arrangement at a
different World position is the same Object. The set below is chosen to discriminate
rather than to illustrate: T, ⊥, ⊢ and ⊣ have an identical feature bag — one
horizontal stroke, one vertical stroke, one junction — and differ only in the
arrangement. A structure that converges over co-occurring features sees the same bundle
four times, so anything that separates them separated them relationally.

Because the four are rotations of one another, they also make the signed-invariance
rule concrete: translation must preserve identity here, and rotation must destroy it.
A rotation-invariant system could not tell T from ⊥ and would make the set unlearnable.

**A limit this set exposes.** `Object.relations()` stores the *unordered multiset* of
pairwise offsets, and that multiset is closed under reflection whenever the bar is
symmetric — so T and ⊥ store identically, as do ⊢ and ⊣. The bag keeps which offsets
occur and throws away how they were traversed. The arrangement lives in the traversal,
which is why the Schema is advanced by a sequence of Relations rather than handed a set
of them. See the premise tests for both halves of this.
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


def named(names: list[str]) -> list[Object]:
    unknown = [n for n in names if n not in FIGURES]
    if unknown:
        raise KeyError(f"unknown figures {unknown}; declared: {sorted(FIGURES)}")
    return [FIGURES[n] for n in names]
