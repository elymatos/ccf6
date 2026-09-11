"""Normative zero-rest Network for the NCL Functional Web experiments."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class PopulationState:
    """The same three-compartment Column mechanics for every Population."""

    identifier: str
    provenance: str
    wiring_role: str
    thresholds: np.ndarray
    activity_average: np.ndarray
    entrenchment: np.ndarray
    contributing_presentations: list[set[str]]
    input: np.ndarray
    integration: np.ndarray
    output: np.ndarray

    @property
    def columns(self) -> int:
        return int(self.output.size)

    def reset(self) -> None:
        self.input.fill(0.0)
        self.integration.fill(0.0)
        self.output.fill(0.0)


@dataclass
class ReciprocalProjection:
    """Shared endpoints with independent directional state."""

    identifier: str
    source: str
    target: str
    sources: np.ndarray
    targets: np.ndarray
    ascending_weights: np.ndarray
    descending_weights: np.ndarray
    ascending_eligibility: np.ndarray
    descending_eligibility: np.ndarray
    fan_in: int
    incoming_norm: float
    initialization: dict


@dataclass
class InhibitionTopology:
    population: str
    sources: np.ndarray
    targets: np.ndarray
    weights: np.ndarray
    radius: int
    strength: float


@dataclass(frozen=True)
class SettlingResult:
    success: bool
    ticks: int
    stable_ticks: int
    final_delta: float
    max_ticks_reached: bool
    activity: np.ndarray


@dataclass(frozen=True)
class ProjectionLearningResult:
    identifier: str
    ascending_eligibility: np.ndarray
    descending_eligibility: np.ndarray
    pre_ascending_weights: np.ndarray
    post_ascending_weights: np.ndarray
    pre_descending_weights: np.ndarray
    post_descending_weights: np.ndarray


@dataclass(frozen=True)
class PopulationLearningResult:
    identifier: str
    settled_output: np.ndarray
    pre_thresholds: np.ndarray
    post_thresholds: np.ndarray
    pre_activity_average: np.ndarray
    post_activity_average: np.ndarray
    pre_entrenchment: np.ndarray
    post_entrenchment: np.ndarray
    post_contributor_counts: np.ndarray
    recruited: np.ndarray


@dataclass(frozen=True)
class LearningResult:
    success_signal: float
    presentation_id: str | None
    adaptation_applied: bool
    projections: tuple[ProjectionLearningResult, ...]
    populations: tuple[PopulationLearningResult, ...]


def _require_keys(
    value: dict,
    required: set[str],
    context: str,
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing or unknown:
        details = []
        if missing:
            details.append(f"missing {sorted(missing)}")
        if unknown:
            details.append(f"unknown {sorted(unknown)}")
        raise ValueError(f"{context}: {', '.join(details)}")


def _number(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context} must be numerical")
    return float(value)


def _positive(value: object, context: str) -> float:
    number = _number(value, context)
    if number <= 0.0:
        raise ValueError(f"{context} must be positive")
    return number


def _normalize_by_destination(
    weights: np.ndarray, destinations: np.ndarray, count: int, norm: float
) -> np.ndarray:
    normalized = weights.copy()
    totals = np.bincount(destinations, weights=normalized, minlength=count)
    scale = np.divide(
        norm,
        totals,
        out=np.zeros_like(totals),
        where=totals > 0.0,
    )
    normalized *= scale[destinations]
    return normalized


def _leaky(current: np.ndarray, target: np.ndarray, dt: float, tau: float) -> np.ndarray:
    return current + (target - current) * (1.0 - np.exp(-dt / tau))


def _response(
    integration: np.ndarray, thresholds: np.ndarray, temperature: float
) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-(integration - thresholds) / temperature))


class Network:
    """One connected Network of ordinary Columns with declared numerical behavior."""

    def __init__(self, definition: dict):
        self.definition = definition
        self._validate_definition()
        self.seed = int(definition["seed"])
        self.dynamics = {
            key: float(value) for key, value in definition["dynamics"].items()
        }
        self.settling = dict(definition["settling"])
        self.plasticity = (
            {
                key: float(value)
                for key, value in definition["plasticity"].items()
            }
            if "plasticity" in definition
            else None
        )
        self.adaptation = dict(definition["adaptation"]) if "adaptation" in definition else None
        self.adaptation_frozen = False
        randomizer = np.random.default_rng(self.seed)

        threshold_declaration = definition["thresholds"]
        self.populations: dict[str, PopulationState] = {}
        self.inhibition: dict[str, InhibitionTopology] = {}
        self.population_order = tuple(
            declaration["id"] for declaration in definition["populations"]
        )
        for declaration in definition["populations"]:
            identifier = declaration["id"]
            columns = int(declaration["columns"])
            thresholds = randomizer.uniform(
                threshold_declaration["low"],
                threshold_declaration["high"],
                columns,
            )
            self.populations[identifier] = PopulationState(
                identifier=identifier,
                provenance=declaration["provenance"],
                wiring_role=declaration["wiring_role"],
                thresholds=thresholds,
                activity_average=np.zeros(columns),
                entrenchment=np.zeros(columns),
                contributing_presentations=[set() for _ in range(columns)],
                input=np.zeros(columns),
                integration=np.zeros(columns),
                output=np.zeros(columns),
            )
            self.inhibition[identifier] = self._build_inhibition(
                identifier,
                columns,
                declaration["inhibition"],
            )

        self.projections = [
            self._build_projection(declaration, randomizer)
            for declaration in definition["projections"]
        ]
        self._last_settling_success = False
        self._outcome_applied = False

    def _validate_definition(self) -> None:
        _require_keys(
            self.definition,
            {
                "seed",
                "populations",
                "projections",
                "thresholds",
                "dynamics",
                "settling",
            },
            "Network definition",
            optional={"plasticity", "adaptation"},
        )
        if isinstance(self.definition["seed"], bool) or not isinstance(
            self.definition["seed"], int
        ):
            raise ValueError("Network seed must be an integer")

        populations = self.definition["populations"]
        if not isinstance(populations, list) or not populations:
            raise ValueError("Network populations must be a non-empty list")
        identifiers = []
        population_sizes = {}
        for declaration in populations:
            _require_keys(
                declaration,
                {"id", "columns", "provenance", "wiring_role", "inhibition"},
                "Population declaration",
            )
            identifier = declaration["id"]
            if not isinstance(identifier, str) or not identifier:
                raise ValueError("Population id must be a non-empty string")
            if identifier in identifiers:
                raise ValueError(f"duplicate Population {identifier!r}")
            identifiers.append(identifier)
            columns = declaration["columns"]
            if isinstance(columns, bool) or not isinstance(columns, int) or columns < 2:
                raise ValueError(f"{identifier}: columns must be an integer of at least 2")
            population_sizes[identifier] = columns
            if not isinstance(declaration["provenance"], str) or not isinstance(
                declaration["wiring_role"], str
            ):
                raise ValueError(f"{identifier}: provenance and wiring role must be strings")
            inhibition = declaration["inhibition"]
            _require_keys(inhibition, {"radius", "strength"}, f"{identifier} inhibition")
            radius = inhibition["radius"]
            if (
                isinstance(radius, bool)
                or not isinstance(radius, int)
                or not 0 < radius < columns
            ):
                raise ValueError(
                    f"{identifier}: inhibition radius must be a positive integer "
                    "smaller than the Population"
                )
            strength = _number(inhibition["strength"], f"{identifier} inhibition strength")
            if not 0.0 <= strength <= 1.0:
                raise ValueError(f"{identifier}: inhibition strength must be in [0,1]")

        thresholds = self.definition["thresholds"]
        _require_keys(
            thresholds,
            {"distribution", "low", "high", "minimum", "maximum"},
            "threshold declaration",
        )
        if thresholds["distribution"] != "uniform":
            raise ValueError("threshold distribution must be 'uniform'")
        threshold_values = {
            key: _number(thresholds[key], f"threshold {key}")
            for key in ("low", "high", "minimum", "maximum")
        }
        if not (
            0.0
            <= threshold_values["minimum"]
            <= threshold_values["low"]
            < threshold_values["high"]
            <= threshold_values["maximum"]
            <= 1.0
        ):
            raise ValueError("threshold distribution must lie within declared [0,1] bounds")

        projections = self.definition["projections"]
        if not isinstance(projections, list):
            raise ValueError("Network projections must be a list")
        projection_ids = set()
        for declaration in projections:
            _require_keys(
                declaration,
                {
                    "id",
                    "source",
                    "target",
                    "fan_in",
                    "initialization",
                    "incoming_norm",
                },
                "projection declaration",
            )
            identifier = declaration["id"]
            if identifier in projection_ids:
                raise ValueError(f"duplicate projection {identifier!r}")
            projection_ids.add(identifier)
            source = declaration["source"]
            target = declaration["target"]
            if source not in population_sizes or target not in population_sizes:
                raise ValueError(f"{identifier}: projection endpoint is not a Population")
            if source == target:
                raise ValueError(f"{identifier}: inter-Population endpoints must differ")
            fan_in = declaration["fan_in"]
            if (
                isinstance(fan_in, bool)
                or not isinstance(fan_in, int)
                or not 0 < fan_in < population_sizes[source]
            ):
                raise ValueError(
                    f"{identifier}: fan-in must be a positive integer smaller than "
                    f"the source Population ({population_sizes[source]})"
                )
            norm = _positive(declaration["incoming_norm"], f"{identifier} incoming norm")
            if norm > 1.0:
                raise ValueError(f"{identifier}: incoming norm cannot exceed 1")
            initialization = declaration["initialization"]
            _require_keys(
                initialization,
                {"distribution", "low", "high"},
                f"{identifier} initialization",
            )
            if initialization["distribution"] != "uniform":
                raise ValueError(f"{identifier}: initialization must be uniform")
            low = _number(initialization["low"], f"{identifier} initialization low")
            high = _number(initialization["high"], f"{identifier} initialization high")
            if not 0.0 < low < high <= 1.0:
                raise ValueError(
                    f"{identifier}: initialization bounds must satisfy 0 < low < high <= 1"
                )

        dynamics = self.definition["dynamics"]
        _require_keys(
            dynamics,
            {
                "dt",
                "tau_input",
                "tau_integration",
                "tau_output",
                "recurrent_gain",
                "temperature",
                "transmission_cutoff",
            },
            "dynamics declaration",
        )
        for name in ("dt", "tau_input", "tau_integration", "tau_output", "temperature"):
            _positive(dynamics[name], f"dynamics {name}")
        if _number(dynamics["recurrent_gain"], "dynamics recurrent gain") < 0.0:
            raise ValueError("dynamics recurrent gain must not be negative")
        cutoff = _number(dynamics["transmission_cutoff"], "transmission cutoff")
        if not 0.0 <= cutoff <= 1.0:
            raise ValueError("transmission cutoff must be in [0,1]")

        settling = self.definition["settling"]
        _require_keys(
            settling,
            {"epsilon", "stable_ticks", "max_ticks"},
            "settling declaration",
        )
        _positive(settling["epsilon"], "settling epsilon")
        for name in ("stable_ticks", "max_ticks"):
            value = settling[name]
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"settling {name} must be a positive integer")

        if "plasticity" in self.definition:
            plasticity = self.definition["plasticity"]
            _require_keys(
                plasticity,
                {"eligibility_decay", "learning_rate"},
                "plasticity declaration",
            )
            decay = _number(
                plasticity["eligibility_decay"],
                "plasticity eligibility decay",
            )
            if not 0.0 <= decay <= 1.0:
                raise ValueError("plasticity eligibility decay must be in [0,1]")
            _positive(plasticity["learning_rate"], "plasticity learning rate")

        if "adaptation" in self.definition:
            if "plasticity" not in self.definition:
                raise ValueError("Column adaptation requires connection plasticity")
            adaptation = self.definition["adaptation"]
            _require_keys(
                adaptation,
                {
                    "activity_average_rate",
                    "threshold_rate",
                    "target_activity",
                    "recruitment_threshold",
                    "minimum_presentations",
                },
                "adaptation declaration",
            )
            average_rate = _positive(
                adaptation["activity_average_rate"],
                "adaptation activity average rate",
            )
            if average_rate > 1.0:
                raise ValueError("adaptation activity average rate must not exceed 1")
            _positive(adaptation["threshold_rate"], "adaptation threshold rate")
            target = _number(
                adaptation["target_activity"],
                "adaptation target activity",
            )
            if not 0.0 <= target <= 1.0:
                raise ValueError("adaptation target activity must be in [0,1]")
            _positive(
                adaptation["recruitment_threshold"],
                "adaptation recruitment threshold",
            )
            minimum = adaptation["minimum_presentations"]
            if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 2:
                raise ValueError("adaptation minimum presentations must be at least 2")

    def _build_projection(
        self, declaration: dict, randomizer: np.random.Generator
    ) -> ReciprocalProjection:
        source_count = self.populations[declaration["source"]].columns
        target_count = self.populations[declaration["target"]].columns
        fan_in = int(declaration["fan_in"])
        targets = np.repeat(np.arange(target_count, dtype=np.int64), fan_in)
        sources = np.concatenate(
            [
                randomizer.choice(source_count, fan_in, replace=False)
                for _ in range(target_count)
            ]
        ).astype(np.int64)
        initialization = declaration["initialization"]
        ascending = randomizer.uniform(
            initialization["low"], initialization["high"], targets.size
        )
        descending = randomizer.uniform(
            initialization["low"], initialization["high"], targets.size
        )
        norm = float(declaration["incoming_norm"])
        ascending = _normalize_by_destination(ascending, targets, target_count, norm)
        descending = _normalize_by_destination(descending, sources, source_count, norm)
        return ReciprocalProjection(
            identifier=declaration["id"],
            source=declaration["source"],
            target=declaration["target"],
            sources=sources,
            targets=targets,
            ascending_weights=ascending,
            descending_weights=descending,
            ascending_eligibility=np.zeros(targets.size),
            descending_eligibility=np.zeros(targets.size),
            fan_in=fan_in,
            incoming_norm=norm,
            initialization=dict(initialization),
        )

    @staticmethod
    def _build_inhibition(
        identifier: str, columns: int, declaration: dict
    ) -> InhibitionTopology:
        radius = int(declaration["radius"])
        strength = float(declaration["strength"])
        targets = []
        sources = []
        weights = []
        for target in range(columns):
            neighbours = [
                source
                for source in range(max(0, target - radius), min(columns, target + radius + 1))
                if source != target
            ]
            for source in neighbours:
                targets.append(target)
                sources.append(source)
                weights.append(strength / len(neighbours))
        return InhibitionTopology(
            population=identifier,
            sources=np.asarray(sources, dtype=np.int64),
            targets=np.asarray(targets, dtype=np.int64),
            weights=np.asarray(weights, dtype=np.float64),
            radius=radius,
            strength=strength,
        )

    def reset(self) -> None:
        """Reset activity and Eligibility while preserving durable state."""
        for population in self.populations.values():
            population.reset()
        for projection in self.projections:
            projection.ascending_eligibility.fill(0.0)
            projection.descending_eligibility.fill(0.0)
        self._last_settling_success = False
        self._outcome_applied = False

    def broadcast(self, population: PopulationState) -> np.ndarray:
        return np.where(
            population.output >= self.dynamics["transmission_cutoff"],
            population.output,
            0.0,
        )

    def tick(self, sensory: dict[str, np.ndarray] | None = None) -> None:
        """Advance all Populations synchronously from one immutable prior state."""
        self._last_settling_success = False
        self._outcome_applied = False
        sensory = sensory or {}
        unknown = sensory.keys() - self.populations.keys()
        if unknown:
            raise ValueError(f"sensory activity names unknown Populations {sorted(unknown)}")
        previous = {
            identifier: (
                population.input.copy(),
                population.integration.copy(),
                population.output.copy(),
            )
            for identifier, population in self.populations.items()
        }
        input_drives = {
            identifier: np.asarray(
                sensory.get(identifier, np.zeros(population.columns)),
                dtype=np.float64,
            ).copy()
            for identifier, population in self.populations.items()
        }
        for identifier, drive in input_drives.items():
            if drive.shape != (self.populations[identifier].columns,):
                raise ValueError(
                    f"{identifier}: sensory activity must have "
                    f"{self.populations[identifier].columns} values"
                )

        descending_drives = {
            identifier: np.zeros(population.columns)
            for identifier, population in self.populations.items()
        }
        for projection in self.projections:
            source_output = np.where(
                previous[projection.source][2]
                >= self.dynamics["transmission_cutoff"],
                previous[projection.source][2],
                0.0,
            )
            np.add.at(
                input_drives[projection.target],
                projection.targets,
                projection.ascending_weights * source_output[projection.sources],
            )
            target_output = np.where(
                previous[projection.target][2]
                >= self.dynamics["transmission_cutoff"],
                previous[projection.target][2],
                0.0,
            )
            np.add.at(
                descending_drives[projection.source],
                projection.sources,
                projection.descending_weights * target_output[projection.targets],
            )

        if self.plasticity is not None:
            decay = self.plasticity["eligibility_decay"]
            for projection in self.projections:
                projection.ascending_eligibility[:] = np.clip(
                    decay * projection.ascending_eligibility
                    + previous[projection.source][2][projection.sources]
                    * previous[projection.target][1][projection.targets],
                    0.0,
                    1.0,
                )
                projection.descending_eligibility[:] = np.clip(
                    decay * projection.descending_eligibility
                    + previous[projection.target][2][projection.targets]
                    * previous[projection.source][1][projection.sources],
                    0.0,
                    1.0,
                )

        next_states = {}
        for identifier, population in self.populations.items():
            old_input, old_integration, old_output = previous[identifier]
            inhibition = self.inhibition[identifier]
            inhibition_drive = np.bincount(
                inhibition.targets,
                weights=inhibition.weights * old_output[inhibition.sources],
                minlength=population.columns,
            )
            next_input = _leaky(
                old_input,
                np.clip(input_drives[identifier], 0.0, 1.0),
                self.dynamics["dt"],
                self.dynamics["tau_input"],
            )
            next_integration = _leaky(
                old_integration,
                np.clip(
                    old_input
                    + self.dynamics["recurrent_gain"] * old_integration
                    + descending_drives[identifier]
                    - inhibition_drive,
                    0.0,
                    1.0,
                ),
                self.dynamics["dt"],
                self.dynamics["tau_integration"],
            )
            next_output = _leaky(
                old_output,
                _response(
                    old_integration,
                    population.thresholds,
                    self.dynamics["temperature"],
                ),
                self.dynamics["dt"],
                self.dynamics["tau_output"],
            )
            next_states[identifier] = (
                next_input,
                next_integration,
                next_output,
            )

        for identifier, state in next_states.items():
            population = self.populations[identifier]
            population.input, population.integration, population.output = state

    def _activity_matrix(self) -> np.ndarray:
        return np.concatenate(
            [
                np.column_stack(
                    (
                        self.populations[identifier].input,
                        self.populations[identifier].integration,
                        self.populations[identifier].output,
                    )
                )
                for identifier in self.population_order
            ],
            axis=0,
        )

    def _output_vector(self) -> np.ndarray:
        return np.concatenate(
            [self.populations[identifier].output for identifier in self.population_order]
        )

    def settle(self, sensory: dict[str, np.ndarray] | None = None) -> SettlingResult:
        """Tick until Output is stable for the declared consecutive duration."""
        trajectory = [self._activity_matrix()]
        stable_ticks = 0
        final_delta = 0.0
        max_ticks = int(self.settling["max_ticks"])
        required_stable_ticks = int(self.settling["stable_ticks"])
        epsilon = float(self.settling["epsilon"])

        for tick in range(1, max_ticks + 1):
            previous_output = self._output_vector()
            self.tick(sensory)
            current_output = self._output_vector()
            final_delta = float(np.max(np.abs(current_output - previous_output)))
            trajectory.append(self._activity_matrix())
            stable_ticks = stable_ticks + 1 if final_delta < epsilon else 0
            if stable_ticks >= required_stable_ticks:
                self._last_settling_success = True
                return SettlingResult(
                    success=True,
                    ticks=tick,
                    stable_ticks=stable_ticks,
                    final_delta=final_delta,
                    max_ticks_reached=False,
                    activity=np.stack(trajectory),
                )

        self._last_settling_success = False
        return SettlingResult(
            success=False,
            ticks=max_ticks,
            stable_ticks=stable_ticks,
            final_delta=final_delta,
            max_ticks_reached=True,
            activity=np.stack(trajectory),
        )

    def apply_success_signal(
        self,
        success_signal: float,
        presentation_id: str | None = None,
    ) -> LearningResult:
        """Apply one diffuse outcome and local adaptation after settling."""
        if self.plasticity is None:
            raise RuntimeError("Network has no plasticity declaration")
        signal = _number(success_signal, "Success Signal")
        if not 0.0 <= signal <= 1.0:
            raise ValueError("Success Signal must be in [0,1]")
        if not self._last_settling_success:
            raise RuntimeError("Success Signal requires a successfully settled outcome")
        if self._outcome_applied:
            raise RuntimeError("Success Signal has already been applied")
        if self.adaptation is not None and (
            not isinstance(presentation_id, str) or not presentation_id
        ):
            raise ValueError("Column adaptation requires a Presentation identity")

        learning_rate = self.plasticity["learning_rate"]
        results = []
        for projection in self.projections:
            pre_ascending = projection.ascending_weights.copy()
            pre_descending = projection.descending_weights.copy()
            if signal > 0.0 and not self.adaptation_frozen:
                ascending = np.clip(
                    pre_ascending
                    + learning_rate
                    * signal
                    * projection.ascending_eligibility
                    * (1.0 - pre_ascending),
                    0.0,
                    1.0,
                )
                descending = np.clip(
                    pre_descending
                    + learning_rate
                    * signal
                    * projection.descending_eligibility
                    * (1.0 - pre_descending),
                    0.0,
                    1.0,
                )
                projection.ascending_weights[:] = _normalize_by_destination(
                    ascending,
                    projection.targets,
                    self.populations[projection.target].columns,
                    projection.incoming_norm,
                )
                projection.descending_weights[:] = _normalize_by_destination(
                    descending,
                    projection.sources,
                    self.populations[projection.source].columns,
                    projection.incoming_norm,
                )
            results.append(
                ProjectionLearningResult(
                    identifier=projection.identifier,
                    ascending_eligibility=projection.ascending_eligibility.copy(),
                    descending_eligibility=projection.descending_eligibility.copy(),
                    pre_ascending_weights=pre_ascending,
                    post_ascending_weights=projection.ascending_weights.copy(),
                    pre_descending_weights=pre_descending,
                    post_descending_weights=projection.descending_weights.copy(),
                )
            )
        population_results = []
        incoming_eligibility = {
            identifier: np.zeros(population.columns)
            for identifier, population in self.populations.items()
        }
        for projection in self.projections:
            np.maximum.at(
                incoming_eligibility[projection.target],
                projection.targets,
                projection.ascending_eligibility,
            )
            np.maximum.at(
                incoming_eligibility[projection.source],
                projection.sources,
                projection.descending_eligibility,
            )
        for identifier in self.population_order:
            population = self.populations[identifier]
            pre_thresholds = population.thresholds.copy()
            pre_average = population.activity_average.copy()
            pre_entrenchment = population.entrenchment.copy()
            if self.adaptation is not None and not self.adaptation_frozen:
                if signal > 0.0:
                    confirmed = signal * incoming_eligibility[identifier]
                    for column in np.flatnonzero(confirmed > 0.0):
                        contributors = population.contributing_presentations[column]
                        if presentation_id not in contributors:
                            population.entrenchment[column] += confirmed[column]
                            contributors.add(presentation_id)
                average_rate = float(self.adaptation["activity_average_rate"])
                population.activity_average += average_rate * (
                    population.output - population.activity_average
                )
                threshold_declaration = self.definition["thresholds"]
                population.thresholds[:] = np.clip(
                    population.thresholds
                    + float(self.adaptation["threshold_rate"])
                    * (
                        population.activity_average
                        - float(self.adaptation["target_activity"])
                    ),
                    threshold_declaration["minimum"],
                    threshold_declaration["maximum"],
                )
            contributor_counts = np.asarray(
                [len(values) for values in population.contributing_presentations],
                dtype=np.int64,
            )
            recruited = self._recruited(population, contributor_counts)
            population_results.append(
                PopulationLearningResult(
                    identifier=identifier,
                    settled_output=population.output.copy(),
                    pre_thresholds=pre_thresholds,
                    post_thresholds=population.thresholds.copy(),
                    pre_activity_average=pre_average,
                    post_activity_average=population.activity_average.copy(),
                    pre_entrenchment=pre_entrenchment,
                    post_entrenchment=population.entrenchment.copy(),
                    post_contributor_counts=contributor_counts,
                    recruited=recruited,
                )
            )
        self._outcome_applied = True
        return LearningResult(
            success_signal=signal,
            presentation_id=presentation_id,
            adaptation_applied=not self.adaptation_frozen,
            projections=tuple(results),
            populations=tuple(population_results),
        )

    def freeze_adaptation(self) -> None:
        """Freeze all durable adaptation until explicitly re-enabled."""
        self.adaptation_frozen = True

    def enable_adaptation(self) -> None:
        """Enable durable adaptation for acquisition Presentations."""
        self.adaptation_frozen = False

    def _recruited(
        self,
        population: PopulationState,
        contributor_counts: np.ndarray | None = None,
    ) -> np.ndarray:
        if self.adaptation is None:
            return np.zeros(population.columns, dtype=bool)
        if contributor_counts is None:
            contributor_counts = np.asarray(
                [len(values) for values in population.contributing_presentations],
                dtype=np.int64,
            )
        return (
            population.entrenchment
            >= float(self.adaptation["recruitment_threshold"])
        ) & (
            contributor_counts >= int(self.adaptation["minimum_presentations"])
        )

    def recruited_columns(self) -> dict[str, np.ndarray]:
        """Classify Recruited Columns from durable evidence without semantics."""
        return {
            identifier: self._recruited(population)
            for identifier, population in self.populations.items()
        }

    def eligibility_matrix(self) -> np.ndarray:
        """Return directional Eligibility ordered by projection and endpoint."""
        if not self.projections:
            return np.empty((0, 2), dtype=np.float64)
        return np.concatenate(
            [
                np.column_stack(
                    (
                        projection.ascending_eligibility,
                        projection.descending_eligibility,
                    )
                )
                for projection in self.projections
            ],
            axis=0,
        )

    def column_labels(self) -> list[str]:
        return [
            f"{identifier}#{column}"
            for identifier in self.population_order
            for column in range(self.populations[identifier].columns)
        ]

    def topology_snapshot(self) -> dict:
        """Return every generated endpoint and directional value as plain data."""
        return {
            "model": "ncl-functional-web-v1",
            "seed": self.seed,
            "threshold_declaration": dict(self.definition["thresholds"]),
            "dynamics": dict(self.dynamics),
            "settling": dict(self.settling),
            "populations": [
                {
                    "id": identifier,
                    "columns": self.populations[identifier].columns,
                    "provenance": self.populations[identifier].provenance,
                    "wiring_role": self.populations[identifier].wiring_role,
                    "thresholds": self.populations[identifier].thresholds.tolist(),
                    "inhibition": {
                        "radius": self.inhibition[identifier].radius,
                        "strength": self.inhibition[identifier].strength,
                        "connections": int(self.inhibition[identifier].sources.size),
                        "endpoints": [
                            {
                                "source_column": int(source),
                                "target_column": int(target),
                                "weight": float(weight),
                            }
                            for source, target, weight in zip(
                                self.inhibition[identifier].sources,
                                self.inhibition[identifier].targets,
                                self.inhibition[identifier].weights,
                                strict=True,
                            )
                        ],
                    },
                }
                for identifier in self.population_order
            ],
            "projections": [
                {
                    "id": projection.identifier,
                    "source": projection.source,
                    "target": projection.target,
                    "fan_in": projection.fan_in,
                    "incoming_norm": projection.incoming_norm,
                    "initialization": dict(projection.initialization),
                    "connections": int(projection.sources.size),
                    "endpoints": [
                        {
                            "source_column": int(source),
                            "target_column": int(target),
                            "ascending_weight": float(ascending_weight),
                            "descending_weight": float(descending_weight),
                            "ascending_eligibility": float(ascending_eligibility),
                            "descending_eligibility": float(descending_eligibility),
                        }
                        for (
                            source,
                            target,
                            ascending_weight,
                            descending_weight,
                            ascending_eligibility,
                            descending_eligibility,
                        ) in zip(
                            projection.sources,
                            projection.targets,
                            projection.ascending_weights,
                            projection.descending_weights,
                            projection.ascending_eligibility,
                            projection.descending_eligibility,
                            strict=True,
                        )
                    ],
                }
                for projection in self.projections
            ],
        }

    def topology_arrays(self) -> dict[str, np.ndarray]:
        """Return the lossless numerical topology without object arrays."""
        arrays = {
            "population_ids": np.asarray(self.population_order),
            "population_columns": np.asarray(
                [self.populations[name].columns for name in self.population_order],
                dtype=np.int64,
            ),
            "thresholds": np.concatenate(
                [self.populations[name].thresholds for name in self.population_order]
            ),
        }
        for projection in self.projections:
            prefix = projection.identifier
            arrays[f"{prefix}.sources"] = projection.sources
            arrays[f"{prefix}.targets"] = projection.targets
            arrays[f"{prefix}.ascending_weights"] = projection.ascending_weights
            arrays[f"{prefix}.descending_weights"] = projection.descending_weights
            arrays[f"{prefix}.ascending_eligibility"] = (
                projection.ascending_eligibility
            )
            arrays[f"{prefix}.descending_eligibility"] = (
                projection.descending_eligibility
            )
        for identifier in self.population_order:
            inhibition = self.inhibition[identifier]
            arrays[f"{identifier}.inhibition_sources"] = inhibition.sources
            arrays[f"{identifier}.inhibition_targets"] = inhibition.targets
            arrays[f"{identifier}.inhibition_weights"] = inhibition.weights
        return arrays

    def snapshot(self) -> dict:
        """Return complete observable Column state."""
        recruited = self.recruited_columns()
        return {
            "populations": {
                identifier: {
                    "provenance": population.provenance,
                    "wiring_role": population.wiring_role,
                    "thresholds": population.thresholds.tolist(),
                    "activity_average": population.activity_average.tolist(),
                    "entrenchment": population.entrenchment.tolist(),
                    "contributing_presentations": [
                        sorted(values)
                        for values in population.contributing_presentations
                    ],
                    "recruited": recruited[identifier].tolist(),
                    "input": population.input.tolist(),
                    "integration": population.integration.tolist(),
                    "output": population.output.tolist(),
                }
                for identifier, population in self.populations.items()
            }
        }
