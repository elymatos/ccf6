"""The Web: what things are.

Slow, overlapping, converging over co-occurrence. A hierarchy of Spaces whose tops
feed a convergence Space; features drive conjunctions, conjunctions drive categories,
and many different inputs come to drive one shared response, which is what makes a
category exist at all.

The Web is an organization *of* Spaces rather than a replacement for them. Space,
Modality and Cortical Area keep their settled meanings: each Space converges over one
dimension, a **Convergence Node** sits at the top of each, and a **Cardinal Node** can
form only where several Spaces meet — cardinality is cross-Space by definition, so the
convergence Space is the only place one could appear.

Nothing here learns yet. Connectivity is fixed at construction, which is what makes a
run a baseline: whatever selectivity appears comes from arbitrary wiring and is the
number a later local rule has to beat.
"""

from __future__ import annotations

import numpy as np

from ccf6.space import Space, transmit


class Web:
    """Named Spaces, and the convergence Space fed by their tops."""

    #: Where each Space of the first configuration sits, and how its content arrives.
    #: An experiment overrides this by declaring `spaces`; the same field says which
    #: Spaces to build, so a Space that is not sited is not built.
    DEFAULT_SITING: dict[str, dict[str, str | None]] = {
        "colour": {"cortical_area": "temporal", "modality": "visual"},
        "shape": {"cortical_area": "temporal", "modality": "visual"},
        "position": {"cortical_area": "parietal", "modality": "visual"},
        "convergence": {"cortical_area": "frontal", "modality": None},
    }

    def __init__(
        self,
        siting: dict[str, dict[str, str | None]],
        input_sizes: dict[str, int],
        *,
        levels: int,
        convergence_levels: int,
        local_levels: int,
        pooling: int,
        fanin: int,
        convergence_fanin: int,
        cluster: int,
        side: int,
        rng: np.random.Generator,
    ):
        self.spaces: dict[str, Space] = {}
        self._convergence_sources: list[str] = []

        for name, sited in siting.items():
            if name == "convergence":
                continue
            size = input_sizes[name]
            self.spaces[name] = Space(
                name,
                (side, side),
                levels,
                size,
                cortical_area=sited["cortical_area"],
                modality=sited["modality"],
                local_levels=local_levels,
                pooling=pooling,
                fanin=fanin,
                cluster=cluster,
                rng=rng,
                input_mode="sparse",
                boundary="Thalamus",
            )
            self._convergence_sources.append(name)

        self.convergence: Space | None = None
        if "convergence" in siting and len(self._convergence_sources) >= 2:
            fan_in_size = sum(self.spaces[n].top.n for n in self._convergence_sources)
            sited = siting["convergence"]
            self.convergence = Space(
                "convergence",
                (side, side),
                convergence_levels,
                fan_in_size,
                cortical_area=sited["cortical_area"],
                modality=sited["modality"],
                local_levels=0,        # convergence is non-local at every Level
                pooling=pooling,
                fanin=convergence_fanin,
                cluster=cluster,
                rng=rng,
                input_mode="sparse",
                boundary="tops of other Spaces",
            )
            self.spaces["convergence"] = self.convergence

    @property
    def content_size(self) -> int:
        """The width of the activation the Web offers as content to be bound."""
        return self.top.n

    @property
    def top(self):
        """Where a Cardinal Node could form: the convergence Space's top Level.

        With fewer than two Spaces there is no cross-Space convergence, so the deepest
        single Space stands in — and no Cardinal Node is claimed to exist there.
        """
        if self.convergence is not None:
            return self.convergence.top
        return next(iter(self.spaces.values())).top

    def content(self, p: dict) -> np.ndarray:
        """What the Web offers the Index: its convergence output, above threshold."""
        return transmit(self.top.l5, p)

    def reset(self) -> None:
        for space in self.spaces.values():
            space.reset()

    def step(self, drive: dict[str, np.ndarray], p: dict) -> None:
        """One synchronous tick. Every Space computes from the previous tick's state,
        so the order they appear in below cannot affect the result."""
        convergence_drive = None
        if self.convergence is not None:
            convergence_drive = np.concatenate(
                [transmit(self.spaces[n].top.l5, p) for n in self._convergence_sources]
            )
        for name in self._convergence_sources:
            self.spaces[name].step(drive.get(name), p)
        if self.convergence is not None:
            self.convergence.step(convergence_drive, p)

    def describe(self) -> dict:
        return {
            "spaces": {name: space.describe() for name, space in self.spaces.items()},
            "convergence_sources": [
                {
                    "space": name,
                    "cortical_area": self.spaces[name].cortical_area,
                    "modality": self.spaces[name].modality,
                    "level": self.spaces[name].top.name,
                    "columns": self.spaces[name].top.n,
                }
                for name in self._convergence_sources
                if self.convergence is not None
            ],
        }

    def snapshot(self) -> dict:
        return {
            name: {
                level.name: {
                    "shape": list(level.shape),
                    "l4": level.grid("l4").tolist(),
                    "l23": level.grid("l23").tolist(),
                    "l5": level.grid("l5").tolist(),
                }
                for level in space.levels
            }
            for name, space in self.spaces.items()
        }


def _grid_for(size: int) -> tuple[int, int]:
    """The nearest square Grid that holds `size` Columns.

    No longer used to size a Space — every Space now declares one side (§ the 64x64
    decision), so a Space's width is independent of what feeds it. Kept because it is
    still the right answer for anything sized by its contents rather than declared.
    """
    side = int(np.ceil(np.sqrt(size)))
    return (side, side)
