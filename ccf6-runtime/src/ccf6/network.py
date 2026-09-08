"""The Network: Spaces, a Hub, and the Thalamus that feeds them.

Three Spaces in the first configuration. The position Space and the colour Space are
spokes, each a code for one dimension. The Hub sees the tops of both and is the only
place a Cardinal Node can form, since cardinality is cross-Space by definition.

Both spokes carry the **visual** Modality and differ in Cortical Area — position in
parietal, colour in temporal. They are two Spaces because they are codes for two
dimensions, not because they arrive through two channels; see CONTEXT.md, where whether
cardinality also requires crossing Modalities is recorded as open.

Mapped onto the population vocabulary: the position Space carries `g`, the colour Space
carries `x`, and the Hub carries `p`. That is a mapping between two vocabularies, not an
identity — see CONTEXT.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ccf6.space import Space
from ccf6.thalamus import Thalamus


#: Where each Space of the first configuration sits, and how its content arrives. An
#: experiment overrides this by declaring `spaces` in its architecture; the same field
#: says which Spaces to build, so a Space that is not sited is not built.
DEFAULT_SPACES: dict[str, dict[str, str | None]] = {
    "position": {"cortical_area": "parietal", "modality": "visual"},
    "colour": {"cortical_area": "temporal", "modality": "visual"},
    "hub": {"cortical_area": "frontal", "modality": None},
}


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
    #: Which Spaces to build, and how each is sited. An experiment that asks about one
    #: Space should not have to run the others: they would contribute nothing and their
    #: activity would only make the picture harder to read.
    spaces: dict[str, dict[str, str | None]] = field(
        default_factory=lambda: {name: dict(siting) for name, siting in DEFAULT_SPACES.items()}
    )
    colour_shape: tuple[int, int] = (8, 8)

    @property
    def position_shape(self) -> tuple[int, int]:
        return (self.world_size, self.world_size)

    def siting(self, name: str) -> dict[str, str | None]:
        """Cortical Area and Modality for one Space, falling back to the default.

        An experiment may name a Space without re-stating where it sits, since the
        siting is a claim about the model rather than about the run.
        """
        declared = self.spaces.get(name) or {}
        return {**DEFAULT_SPACES.get(name, {}), **declared}


class Network:
    def __init__(self, arch: Architecture, thalamus: Thalamus):
        self.arch = arch
        self.thalamus = thalamus
        rng = np.random.default_rng(arch.seed)
        self.spaces: dict[str, Space] = {}

        self.position = Space(
            "position",
            arch.position_shape,
            arch.levels,
            thalamus.position.size,
            **arch.siting("position"),
            local_levels=arch.local_levels,
            pooling=arch.pooling,
            fanin=arch.fanin,
            rng=rng,
        )
        self.spaces["position"] = self.position

        self.colour = None
        self.hub = None
        if "colour" not in arch.spaces:
            return

        self.colour = Space(
            "colour",
            arch.colour_shape,
            arch.levels,
            thalamus.colour.size,
            **arch.siting("colour"),
            local_levels=arch.local_levels,
            pooling=arch.pooling,
            fanin=arch.fanin,
            rng=rng,
        )
        self.spaces["colour"] = self.colour
        if "hub" not in arch.spaces:
            return

        hub_input = self.position.top.n + self.colour.top.n
        self.hub = Space(
            "hub",
            arch.position_shape,
            arch.hub_levels,
            hub_input,
            **arch.siting("hub"),
            local_levels=0,          # the Hub is non-local at every Level
            pooling=arch.pooling,
            fanin=arch.fanin,
            rng=rng,
            input_mode="sparse",
        )
        self.spaces["hub"] = self.hub

    def reset(self) -> None:
        for space in self.spaces.values():
            space.reset()

    def step(self, colour: int | None, position: tuple[int, int] | None, strength: float, p: dict) -> None:
        """One synchronous tick of the whole Network.

        Every Space computes from the state left by the previous tick, so the order the
        Spaces appear in below does not affect the result.
        """
        if colour is None or position is None or strength <= 0.0:
            drive = {"colour": None, "position": None}
        else:
            drive = self.thalamus.project(colour, position, strength)

        from ccf6.space import transmit

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
        """Every Space's siting and wiring, plus what feeds the Hub."""
        return {
            "spaces": {name: space.describe() for name, space in self.spaces.items()},
            "hub_sources": [
                {
                    "space": name,
                    "cortical_area": self.spaces[name].cortical_area,
                    "modality": self.spaces[name].modality,
                    "level": self.spaces[name].top.name,
                    "columns": self.spaces[name].top.n,
                }
                for name in ("position", "colour")
                if self.hub is not None and name in self.spaces
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
                for level in space.levels
            }
            for name, space in self.spaces.items()
        }

    def response_vector(self) -> np.ndarray:
        """L5 of every Column in the Network, in a fixed order.

        The order is stable for the life of a Network, so a Column's index means the
        same thing in every stimulus of a run.
        """
        parts = []
        for space in self.spaces.values():
            for level in space.levels:
                parts.append(level.l5)
        return np.concatenate(parts)

    def column_labels(self) -> list[str]:
        labels = []
        for space in self.spaces.values():
            for level in space.levels:
                labels.extend(f"{level.name}#{i}" for i in range(level.n))
        return labels
