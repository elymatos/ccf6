"""One recurrent network of connected cortical-column populations.

The runtime has no separate symbolic processor, structural-state machine, or binding
store. Sensory and association populations use the same Column mechanics. Functional
webs and cardinal candidates are observations about learned connectivity and activity.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ccf6.ego import Presentation, Sample
from ccf6.learning import Recruitment, committed
from ccf6.population import Population, transmit
from ccf6.thalamus import Thalamus


@dataclass(frozen=True)
class Traversal:
    """Population activity retained for every sample in a presentation."""

    responses: np.ndarray

    @property
    def mean(self) -> np.ndarray:
        return self.responses.mean(axis=0) if self.responses.size else self.responses

    @property
    def sequence(self) -> np.ndarray:
        return self.responses.ravel()


@dataclass
class Architecture:
    """The declared populations and numerical shape of a network."""

    world_size: int = 12
    n_colours: int = 8
    side: int = 32
    cluster: int = 8
    pooling: int = 3
    fanin: int = 4
    association_fanin: int = 12
    populations: dict[str, dict] = field(
        default_factory=lambda: {
            "shape": {
                "role": "sensory",
                "modality": "visual",
                "levels": 3,
            },
            "colour": {
                "role": "sensory",
                "modality": "visual",
                "levels": 3,
            },
            "concept": {
                "role": "association",
                "modality": None,
                "levels": 2,
                "sources": ["shape", "colour"],
            },
        }
    )
    learning: dict | None = None
    seed: int = 20260909


class Network:
    """A recurrent graph whose populations all use one Column implementation."""

    def __init__(self, architecture: Architecture, thalamus: Thalamus):
        self.architecture = architecture
        self.thalamus = thalamus
        self.populations: dict[str, Population] = {}
        rng = np.random.default_rng(architecture.seed)

        for name, declaration in architecture.populations.items():
            role = declaration["role"]
            sources = tuple(declaration.get("sources", ()))
            if role == "sensory":
                if name not in thalamus.encoders:
                    raise ValueError(f"sensory Population {name!r} has no sensory adapter")
                input_size = thalamus.encoders[name].size
                fanin = architecture.fanin
            else:
                missing = [source for source in sources if source not in self.populations]
                if missing:
                    raise ValueError(
                        f"association Population {name!r} has unavailable sources {missing}"
                    )
                input_size = sum(self.populations[source].top.n for source in sources)
                fanin = architecture.association_fanin

            self.populations[name] = Population(
                name,
                (architecture.side, architecture.side),
                int(declaration.get("levels", 1)),
                input_size,
                role=role,
                modality=declaration.get("modality"),
                sources=sources,
                local_levels=int(declaration.get("local_levels", 0)),
                pooling=architecture.pooling,
                fanin=fanin,
                cluster=architecture.cluster,
                rng=rng,
            )

        self.rule = Recruitment(**architecture.learning) if architecture.learning else None

    def reset(self) -> None:
        for population in self.populations.values():
            population.reset()

    def _drives(self, sensory: dict[str, np.ndarray], parameters: dict) -> dict[str, np.ndarray]:
        drives: dict[str, np.ndarray] = {}
        for name, population in self.populations.items():
            if population.role == "sensory":
                drives[name] = sensory.get(
                    name, np.zeros(population.levels[0].w_input.n_in)
                )
            else:
                drives[name] = np.concatenate(
                    [transmit(self.populations[source].top.l5, parameters) for source in population.sources]
                )
        return drives

    def _top_down(self, parameters: dict) -> dict[str, np.ndarray]:
        feedback = {
            name: np.zeros(population.top.n)
            for name, population in self.populations.items()
        }
        for population in self.populations.values():
            if population.role != "association":
                continue
            returned = population.levels[0].w_input.backward(
                transmit(population.levels[0].l5, parameters)
            )
            cursor = 0
            for source in population.sources:
                size = self.populations[source].top.n
                feedback[source] += returned[cursor : cursor + size]
                cursor += size
        return feedback

    def sample(self, sample: Sample, signals: dict, ticks: int, parameters: dict) -> None:
        sensory = self.thalamus.project(signals)
        for _ in range(ticks):
            drives = self._drives(sensory, parameters)
            top_down = self._top_down(parameters)
            for name, population in self.populations.items():
                population.step(drives[name], parameters, top_down[name])

        if self.rule is not None:
            drives = self._drives(sensory, parameters)
            for name, population in self.populations.items():
                population.learn(drives[name], self.rule)

    def traverse(
        self, presentation: Presentation, signals, ticks: int, parameters: dict
    ) -> Traversal:
        responses = []
        for sample in presentation.samples:
            self.sample(sample, signals(sample), ticks, parameters)
            responses.append(self.response_vector())
        if not responses:
            return Traversal(np.zeros((0, self.response_vector().size)))
        return Traversal(np.stack(responses))

    def response_vector(self) -> np.ndarray:
        return np.concatenate(
            [
                level.l5
                for population in self.populations.values()
                for level in population.levels
            ]
        )

    def population_output(self, name: str, parameters: dict) -> np.ndarray:
        return transmit(self.populations[name].top.l5, parameters)

    def column_labels(self) -> list[str]:
        return [
            f"{level.name}#{index}"
            for population in self.populations.values()
            for level in population.levels
            for index in range(level.n)
        ]

    def cardinal_candidates(self, commitment_threshold: float = 0.5) -> dict[str, int]:
        """Count recruited convergence Columns without declaring them concepts by fiat."""
        return {
            name: int(committed(population.top, commitment_threshold).sum())
            for name, population in self.populations.items()
            if population.role == "association"
        }

    def recruitment_report(self, threshold: float = 0.5) -> dict:
        return {
            level.name: {
                "committed": int(committed(level, threshold).sum()),
                "columns": level.n,
                "wins_max": int(level.wins.max()),
                "plasticity_min": float(level.plasticity.min()),
            }
            for population in self.populations.values()
            for level in population.levels
        }

    def describe(self) -> dict:
        return {
            "model": "ncl-column-network-v1",
            "populations": {
                name: population.describe()
                for name, population in self.populations.items()
            },
            "learning": self.rule.describe() if self.rule is not None else None,
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
                for level in population.levels
            }
            for name, population in self.populations.items()
        }
