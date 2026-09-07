"""The Network: Areas, a Hub, and the Thalamus that feeds them.

Three Areas in the first configuration. The position Area and the colour Area are
spokes, each seeing one kind of thing. The Hub sees the tops of both and is the only
place a Cardinal Node can form, since cardinality is multimodal by definition.

Mapped onto the population vocabulary: the position Area carries `g`, the colour Area
carries `x`, and the Hub carries `p`. That is a mapping between two vocabularies, not
an identity — see CONTEXT.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ccf6.area import Area
from ccf6.thalamus import Thalamus


@dataclass
class Architecture:
    """Everything about the network's shape that an experiment declares."""

    world_size: int = 8
    n_colours: int = 8
    levels: int = 3
    local_levels: int = 2
    pooling: int = 4
    fanin: int = 12
    hub_levels: int = 2
    seed: int = 20260907
    #: Which Areas to build. An experiment that asks about one Area should not have to
    #: run the others: they would contribute nothing and their activity would only make
    #: the picture harder to read.
    areas: tuple[str, ...] = ("position", "colour", "hub")
    colour_shape: tuple[int, int] = (8, 8)

    @property
    def position_shape(self) -> tuple[int, int]:
        return (self.world_size, self.world_size)


class Network:
    def __init__(self, arch: Architecture, thalamus: Thalamus):
        self.arch = arch
        self.thalamus = thalamus
        rng = np.random.default_rng(arch.seed)
        self.areas: dict[str, Area] = {}

        self.position = Area(
            "position",
            arch.position_shape,
            arch.levels,
            thalamus.position.size,
            local_levels=arch.local_levels,
            pooling=arch.pooling,
            fanin=arch.fanin,
            rng=rng,
        )
        self.areas["position"] = self.position

        self.colour = None
        self.hub = None
        if "colour" not in arch.areas:
            return

        self.colour = Area(
            "colour",
            arch.colour_shape,
            arch.levels,
            thalamus.colour.size,
            local_levels=arch.local_levels,
            pooling=arch.pooling,
            fanin=arch.fanin,
            rng=rng,
        )
        self.areas["colour"] = self.colour
        if "hub" not in arch.areas:
            return

        hub_input = self.position.top.n + self.colour.top.n
        self.hub = Area(
            "hub",
            arch.position_shape,
            arch.hub_levels,
            hub_input,
            local_levels=0,          # the Hub is non-local at every Level
            pooling=arch.pooling,
            fanin=arch.fanin,
            rng=rng,
            input_mode="sparse",
        )
        self.areas["hub"] = self.hub

    def reset(self) -> None:
        for area in self.areas.values():
            area.reset()

    def step(self, colour: int | None, position: tuple[int, int] | None, strength: float, p: dict) -> None:
        """One synchronous tick of the whole Network.

        Every Area computes from the state left by the previous tick, so the order the
        Areas appear in below does not affect the result.
        """
        if colour is None or position is None or strength <= 0.0:
            drive = {"colour": None, "position": None}
        else:
            drive = self.thalamus.project(colour, position, strength)

        from ccf6.area import transmit

        hub_drive = (
            np.concatenate([transmit(self.position.top.l5, p), transmit(self.colour.top.l5, p)])
            if self.hub is not None
            else None
        )

        self.position.step(drive["position"], p)
        if self.colour is not None:
            self.colour.step(drive["colour"], p)
        if self.hub is not None:
            self.hub.step(hub_drive, p)

    def describe(self) -> dict:
        """Every Area's wiring, plus what feeds the Hub."""
        return {
            "areas": {name: area.describe() for name, area in self.areas.items()},
            "hub_sources": [
                {"area": name, "level": self.areas[name].top.name, "columns": self.areas[name].top.n}
                for name in ("position", "colour")
                if self.hub is not None and name in self.areas
            ],
        }

    def snapshot(self) -> dict:
        """Every drawable field, as nested lists. What the workbench renders."""
        return {
            name: {
                level.name: {
                    "shape": list(level.shape),
                    "l4": level.grid("l4").tolist(),
                    "l23": level.grid("l23").tolist(),
                    "l5": level.grid("l5").tolist(),
                }
                for level in area.levels
            }
            for name, area in self.areas.items()
        }

    def response_vector(self) -> np.ndarray:
        """L5 of every Column in the Network, in a fixed order.

        The order is stable for the life of a Network, so a Column's index means the
        same thing in every stimulus of a run.
        """
        parts = []
        for area in self.areas.values():
            for level in area.levels:
                parts.append(level.l5)
        return np.concatenate(parts)

    def column_labels(self) -> list[str]:
        labels = []
        for area in self.areas.values():
            for level in area.levels:
                labels.extend(f"{level.name}#{i}" for i in range(level.n))
        return labels
