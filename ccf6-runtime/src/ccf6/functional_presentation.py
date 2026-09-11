"""Present coordinated visual properties and ordered auditory Samples."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ccf6.functional_network import Network, SettlingResult


@dataclass(frozen=True)
class SampleRecord:
    number: int
    kind: str
    identifier: str
    active_features: tuple[str, ...]
    initial_eligibility: np.ndarray
    settled_eligibility: np.ndarray
    settling: SettlingResult


@dataclass(frozen=True)
class PresentationRecord:
    identifier: str
    category_id: str
    pseudoword_id: str
    condition: str
    segments: tuple[str, ...]
    success_signal: float
    initial_activity: np.ndarray
    samples: tuple[SampleRecord, ...]

    @property
    def settled_states(self) -> np.ndarray:
        return np.stack([sample.settling.activity[-1] for sample in self.samples])

    @property
    def sample_durations(self) -> np.ndarray:
        return np.asarray([sample.settling.ticks for sample in self.samples])

    @property
    def settling_failures(self) -> int:
        return sum(not sample.settling.success for sample in self.samples)

    def as_dict(self) -> dict:
        return {
            "id": self.identifier,
            "category_id": self.category_id,
            "pseudoword_id": self.pseudoword_id,
            "condition": self.condition,
            "segments": list(self.segments),
            "success_signal": self.success_signal,
            "initial_activity": self.initial_activity.tolist(),
            "settling_failures": self.settling_failures,
            "samples": [
                {
                    "number": sample.number,
                    "kind": sample.kind,
                    "id": sample.identifier,
                    "active_features": list(sample.active_features),
                    "initial_eligibility": {
                        "ascending_sum": float(sample.initial_eligibility[:, 0].sum()),
                        "descending_sum": float(sample.initial_eligibility[:, 1].sum()),
                    },
                    "settled_eligibility": {
                        "ascending_sum": float(sample.settled_eligibility[:, 0].sum()),
                        "descending_sum": float(sample.settled_eligibility[:, 1].sum()),
                    },
                    "duration_ticks": sample.settling.ticks,
                    "settled": sample.settling.success,
                    "stable_ticks": sample.settling.stable_ticks,
                    "final_delta": sample.settling.final_delta,
                    "max_ticks_reached": sample.settling.max_ticks_reached,
                    "initial_activity": sample.settling.activity[0].tolist(),
                    "settled_activity": sample.settling.activity[-1].tolist(),
                    "settled_output": sample.settling.activity[-1, :, 2].tolist(),
                    "output_trajectory": sample.settling.activity[:, :, 2].tolist(),
                }
                for sample in self.samples
            ],
        }


class PresentationProtocol:
    """Run one independent Presentation while preserving state between Samples."""

    def __init__(
        self,
        network: Network,
        dataset: dict,
        *,
        visual_populations: dict[str, str],
        auditory_population: str,
    ):
        self.network = network
        self.visual_populations = dict(visual_populations)
        self.auditory_population = auditory_population
        self.visual_dimensions = {
            row["id"]: tuple(row["values"])
            for row in dataset["visual_property_dimensions"]
        }
        if set(self.visual_populations) != set(self.visual_dimensions):
            raise ValueError("one visual-property Population is required per dimension")
        for dimension, population_id in self.visual_populations.items():
            if population_id not in network.populations:
                raise ValueError(
                    f"{dimension}: unknown visual Population {population_id!r}"
                )
            expected = len(self.visual_dimensions[dimension])
            if network.populations[population_id].columns != expected:
                raise ValueError(
                    f"{population_id}: needs {expected} Columns for {dimension}"
                )
        if auditory_population not in network.populations:
            raise ValueError(f"unknown auditory Population {auditory_population!r}")
        self.auditory_features = tuple(dataset["auditory_features"])
        if network.populations[auditory_population].columns != len(
            self.auditory_features
        ):
            raise ValueError(
                f"{auditory_population}: needs {len(self.auditory_features)} "
                "Columns for auditory features"
            )
        self.segment_features = {
            row["id"]: tuple(row["features"])
            for row in dataset["auditory_segments"]
        }

    def _visual_sensory(self, properties: list[dict]) -> dict[str, np.ndarray]:
        sensory = {}
        for property_ in properties:
            dimension = property_["dimension"]
            values = self.visual_dimensions[dimension]
            activity = np.zeros(len(values))
            activity[values.index(property_["value"])] = 1.0
            sensory[self.visual_populations[dimension]] = activity
        return sensory

    def _auditory_sensory(self, segment: str) -> dict[str, np.ndarray]:
        if segment not in self.segment_features:
            raise ValueError(f"unknown auditory segment {segment!r}")
        features = self.segment_features[segment]
        activity = np.zeros(len(self.auditory_features))
        for feature in features:
            activity[self.auditory_features.index(feature)] = 1.0
        return {self.auditory_population: activity}

    def run(
        self,
        *,
        presentation_id: str,
        category: dict,
        pseudoword_id: str,
        segments: list[str] | tuple[str, ...],
        condition: str,
        success_signal: float,
        visual_instance: dict | None = None,
    ) -> PresentationRecord:
        """Reset once, present visual activity, then ordered auditory Samples."""
        if len(segments) != 3:
            raise ValueError("a pseudoword Presentation requires exactly three segments")
        self.network.reset()
        samples = []

        visual = visual_instance or category["prototype"]
        visual_features = tuple(
            f"{row['dimension']}={row['value']}"
            for row in visual["properties"]
        )
        initial_eligibility = self.network.eligibility_matrix()
        visual_result = self.network.settle(
            self._visual_sensory(visual["properties"])
        )
        samples.append(
            SampleRecord(
                number=1,
                kind="visual",
                identifier=visual.get("id", category["id"]),
                active_features=visual_features,
                initial_eligibility=initial_eligibility,
                settled_eligibility=self.network.eligibility_matrix(),
                settling=visual_result,
            )
        )
        for number, segment in enumerate(segments, start=2):
            initial_eligibility = self.network.eligibility_matrix()
            auditory_result = self.network.settle(self._auditory_sensory(segment))
            samples.append(
                SampleRecord(
                    number=number,
                    kind="auditory",
                    identifier=segment,
                    active_features=self.segment_features[segment],
                    initial_eligibility=initial_eligibility,
                    settled_eligibility=self.network.eligibility_matrix(),
                    settling=auditory_result,
                )
            )

        return PresentationRecord(
            identifier=presentation_id,
            category_id=category["id"],
            pseudoword_id=pseudoword_id,
            condition=condition,
            segments=tuple(segments),
            success_signal=float(success_signal),
            initial_activity=visual_result.activity[0],
            samples=tuple(samples),
        )
