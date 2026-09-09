"""The Network: a Web, a Schema, an Index, and the Thalamus that feeds them.

Two slow abstractors and one fast binder. The **Web** converges over co-occurrence and
says what things are. The **Schema** converges over transitions and says how things
change. The **Index** binds fast and separates, and says what happened where. The
pressures on the Web's code and the Index's code are opposite — convergence against
separation — which is why they are different structures rather than one structure with
a compromise setting.

A presentation is a sequence. At each stop the Thalamus encodes what is there and the
Web settles; the Relation to that stop advances the Schema; the Web's convergence
output is bound to the Schema's state in the Index.

Nothing in the Web or the Schema learns. The Index binds, because binding is what it
is for and a Hebbian association is a local rule rather than a gradient, but no
connectivity changes, nothing is recruited and nothing is promoted. That is what makes
a run a baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ccf6.ego import Presentation, Step
from ccf6.index import Index
from ccf6.schema import Schema
from ccf6.thalamus import Thalamus
from ccf6.web import Web


@dataclass
class Architecture:
    """Everything about the network's shape that an experiment declares."""

    world_size: int = 8
    n_colours: int = 8
    levels: int = 3
    convergence_levels: int = 2
    #: Local pooling assumes a Grid's neighbourhood means something. For a Space over
    #: colour or local shape it does not — adjacency there is an artefact of laying the
    #: dimension out on a square. Only a genuinely spatial Space should pool locally, so
    #: the default is none, and `pooling` waits for one that has a real neighbourhood.
    local_levels: int = 0
    pooling: int = 3
    #: Must be smaller than the narrowest Space, or its Columns all see the same thing.
    fanin: int = 4
    #: Fan-in is declared per connection class, not once for the network. A convergence
    #: Space draws from the tops of every Space at once, so a fan-in sized for a narrow
    #: spoke would leave most of its Columns sampling only silent sources and its output
    #: would fall below the transmission threshold before reaching its own top.
    convergence_fanin: int = 12
    #: Every Space is this many Columns a side, at every Level. A Space's width is a
    #: declared quantity rather than a consequence of what feeds it: the encoder no
    #: longer sizes the Grid, so Level 1 is a sparse expansion of the boundary instead
    #: of a copy of it.
    space_side: int = 64
    #: The unit of competition inside a Level. Columns in one cluster compete for the
    #: right to represent; Columns in different clusters do not compete at all.
    cluster: int = 8
    #: Module periods for the Schema. Capacity along one axis is their least common
    #: multiple, so coprime periods buy a large field from a few small modules.
    schema_periods: tuple[int, ...] = (3, 4, 5)
    schema_width: float = 0.6
    #: Which Spaces to build, and how each is sited.
    spaces: dict[str, dict[str, str | None]] = field(
        default_factory=lambda: {
            name: dict(sited) for name, sited in Web.DEFAULT_SITING.items()
            if name in ("colour", "shape", "convergence")
        }
    )
    #: Which structures to build. A question about one need not run the others.
    structures: tuple[str, ...] = ("web", "schema", "index")
    seed: int = 20260908

    def siting(self, name: str) -> dict[str, str | None]:
        declared = self.spaces.get(name) or {}
        return {**Web.DEFAULT_SITING.get(name, {}), **declared}


class Network:
    def __init__(self, arch: Architecture, thalamus: Thalamus):
        self.arch = arch
        self.thalamus = thalamus
        rng = np.random.default_rng(arch.seed)

        self.web: Web | None = None
        if "web" in arch.structures:
            siting = {name: arch.siting(name) for name in arch.spaces}
            self.web = Web(
                siting,
                thalamus.sizes(),
                levels=arch.levels,
                convergence_levels=arch.convergence_levels,
                local_levels=arch.local_levels,
                pooling=arch.pooling,
                fanin=arch.fanin,
                convergence_fanin=arch.convergence_fanin,
                cluster=arch.cluster,
                side=arch.space_side,
                rng=rng,
            )

        self.schema: Schema | None = None
        self.schema_state: np.ndarray | None = None
        if "schema" in arch.structures:
            self.schema = Schema(tuple(arch.schema_periods), arch.schema_width)

        self.index: Index | None = None
        if "index" in arch.structures:
            if self.web is None or self.schema is None:
                raise ValueError("an Index binds Web content to a Schema state; it needs both")
            self.index = Index(self.web.content_size, self.schema.size)

    def reset(self) -> None:
        if self.web is not None:
            self.web.reset()
        if self.schema is not None:
            self.schema_state = self.schema.origin()
        if self.index is not None:
            self.index.reset()

    def present(
        self, presentation: Presentation, signals, ticks: int, p: dict
    ) -> np.ndarray:
        """Run one whole presentation and report the response to the figure.

        The response is averaged over the stops rather than read off the last one. A
        figure is the whole traversal, so scoring the state left at the final stop would
        measure that cell's neighbourhood and call it the figure — and since the figures
        differ in which cell comes last, that artefact would masquerade as selectivity.
        """
        seen = []
        for index, step in enumerate(presentation.steps):
            self.stop(step, signals(step), ticks, p, first=index == 0)
            seen.append(self.response_vector())
        return np.mean(seen, axis=0) if seen else self.response_vector()

    def stop(self, step: Step, signals: dict, ticks: int, p: dict, *, first: bool) -> None:
        """One stop of a presentation.

        The Relation advances the Schema *before* binding, so what gets bound is the
        content at the position the network has arrived at rather than the one it left.
        """
        if self.schema is not None:
            if first:
                self.schema_state = self.schema.origin()
            elif step.relation is not None:
                self.schema_state = self.schema.advance(self.schema_state, step.relation, p)

        if self.web is not None:
            drive = self.thalamus.project(signals)
            for _ in range(ticks):
                self.web.step(drive, p)

        if self.index is not None:
            self.index.write(self.web.content(p), self.schema_state)

    def response_vector(self) -> np.ndarray:
        """L5 of every Column in the Web, in a fixed order.

        The order is stable for the life of a Network, so a Column's index means the
        same thing in every stimulus of a run.
        """
        if self.web is None:
            return np.zeros(0)
        return np.concatenate(
            [level.l5 for space in self.web.spaces.values() for level in space.levels]
        )

    def column_labels(self) -> list[str]:
        if self.web is None:
            return []
        return [
            f"{level.name}#{i}"
            for space in self.web.spaces.values()
            for level in space.levels
            for i in range(level.n)
        ]

    def describe(self) -> dict:
        out: dict = {"structures": list(self.arch.structures)}
        if self.web is not None:
            out["web"] = self.web.describe()
        if self.schema is not None:
            out["schema"] = self.schema.describe()
        if self.index is not None:
            out["index"] = self.index.describe()
        return out

    def snapshot(self) -> dict:
        out: dict = {}
        if self.web is not None:
            out["web"] = self.web.snapshot()
        if self.schema is not None and self.schema_state is not None:
            out["schema"] = [b.tolist() for b in self.schema.blocks(self.schema_state)]
        return out
