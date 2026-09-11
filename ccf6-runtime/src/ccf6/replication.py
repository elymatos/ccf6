"""Deterministic seed-level aggregation for the Functional Web milestone."""

from __future__ import annotations

import copy
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from itertools import combinations

import numpy as np


EFFECT_NAMES = (
    "completion",
    "reactivation",
    "pairing_localization",
    "candidate_intervention",
    "held_out_separation_change",
)


@dataclass(frozen=True)
class AggregateEffect:
    seed_values: tuple[float, ...]
    median: float
    interval_low: float
    interval_high: float
    expected_direction_count: int
    expected_direction_proportion: float
    failure_count: int

    def as_dict(self) -> dict:
        def finite_or_none(value: float) -> float | None:
            return float(value) if np.isfinite(value) else None

        return {
            "seed_values": [finite_or_none(value) for value in self.seed_values],
            "median": finite_or_none(self.median),
            "interval_95": [
                finite_or_none(self.interval_low),
                finite_or_none(self.interval_high),
            ],
            "expected_direction_count": self.expected_direction_count,
            "expected_direction_proportion": self.expected_direction_proportion,
            "failure_count": self.failure_count,
        }


@dataclass(frozen=True)
class MilestoneAggregate:
    replicate_unit: str
    seed_count: int
    bootstrap_resamples: int
    bootstrap_seed: int
    effects: dict[str, AggregateEffect]
    criteria: dict[str, dict]
    total_settling_failures: int
    failed_seed_count: int
    failed_seeds: tuple[dict, ...]
    verdict: bool

    def as_dict(self) -> dict:
        return {
            "replicate_unit": self.replicate_unit,
            "seed_count": self.seed_count,
            "bootstrap": {
                "resamples": self.bootstrap_resamples,
                "seed": self.bootstrap_seed,
                "statistic": "median_paired_seed_effect",
                "interval": 0.95,
            },
            "effects": {
                name: effect.as_dict() for name, effect in self.effects.items()
            },
            "criteria": self.criteria,
            "total_settling_failures": self.total_settling_failures,
            "failed_seed_count": self.failed_seed_count,
            "failed_seeds": list(self.failed_seeds),
            "verdict": self.verdict,
        }


def _category_separation(activity: np.ndarray, frozen_basins: dict) -> float:
    centroids = np.asarray(activity, dtype=np.float64).mean(axis=1)
    category_ids = tuple(frozen_basins["categories"])
    pooled_scale = np.asarray(frozen_basins["pooled_scale"], dtype=np.float64)
    distances = []
    for left, right in combinations(range(centroids.shape[0]), 2):
        for reference, other in ((left, right), (right, left)):
            mask = np.asarray(
                frozen_basins["categories"][category_ids[reference]]["reliable_mask"],
                dtype=bool,
            )
            distances.append(
                np.sqrt(
                    np.mean(
                        np.square(
                            (centroids[reference, mask] - centroids[other, mask])
                            / pooled_scale[mask]
                        )
                    )
                )
            )
    return float(np.mean(distances))


def _seed_metrics(result: dict, seed: int) -> dict:
    summary = result["summary"]
    completion = summary["completion"]["correct_basin_by_arm_and_condition"]
    reactivation = summary["reactivation"]["correct_better_than_controls_by_arm"]
    trained_completion = completion["trained"]["partial_visual"] / 4.0
    untrained_completion = completion["untrained"]["partial_visual"] / 4.0
    shuffled_completion = completion["shuffled"]["partial_visual"] / 4.0
    trained_reactivation = reactivation["trained"] / 4.0
    untrained_reactivation = reactivation["untrained"] / 4.0
    shuffled_reactivation = reactivation["shuffled"] / 4.0
    held = result["activity_arrays"]["held_out_settled_output"]
    trained_separation = _category_separation(
        held[0], result["basins"]["arms"]["trained"]["frozen"]
    )
    untrained_separation = _category_separation(
        held[1], result["basins"]["arms"]["untrained"]["frozen"]
    )
    separation_change = (
        (trained_separation - untrained_separation) / untrained_separation
        if untrained_separation > 0.0
        else float("nan")
    )
    web_summary = summary["web_detection"]
    cardinal_summary = summary["cardinals"]
    web_overlap = (
        web_summary["shared_columns"] > 0
        and web_summary["association_distinguishable"]
    )
    candidate_intervention = (
        cardinal_summary["candidates"] > 0
        and cardinal_summary["cardinal_nodes"] > 0
        and cardinal_summary["intervention_failures"] == 0
    )
    failures = []
    if not web_overlap:
        failures.append("functional_web_overlap_not_detected")
    if cardinal_summary["candidates"] == 0:
        failures.append("candidate_stimulation_and_lesion_not_executable")
    settling_failures = int(
        summary["settling"]["failures"]
        + summary["completion"]["settling_failures"]
    )
    if settling_failures:
        failures.append("settling_failure")
    return {
        "seed": seed,
        "replicate_unit": "seed",
        "presentation_count": len(result["presentations"]),
        "arms": ["trained", "untrained", "shuffled"],
        "conditions": {
            "stimulation_executed": cardinal_summary["candidates"] > 0,
            "lesion_executed": cardinal_summary["candidates"] > 0,
        },
        "values": {
            "trained_completion": trained_completion,
            "untrained_completion": untrained_completion,
            "shuffled_completion": shuffled_completion,
            "trained_reactivation": trained_reactivation,
            "untrained_reactivation": untrained_reactivation,
            "shuffled_reactivation": shuffled_reactivation,
            "trained_held_out_separation": trained_separation,
            "untrained_held_out_separation": untrained_separation,
            "detected_webs": web_summary["detected_webs"],
            "shared_columns": web_summary["shared_columns"],
            "candidates": cardinal_summary["candidates"],
            "cardinal_nodes": cardinal_summary["cardinal_nodes"],
        },
        "effects": {
            "completion": trained_completion - untrained_completion,
            "reactivation": trained_reactivation - untrained_reactivation,
            "pairing_localization": (
                (trained_completion + trained_reactivation)
                - (shuffled_completion + shuffled_reactivation)
            )
            / 2.0,
            "candidate_intervention": (
                1.0 if candidate_intervention else 0.0
            ),
            "held_out_separation_change": separation_change,
        },
        "criteria": {
            "correct_basins": (
                summary["held_out"]["correct_basin_by_arm"]["trained"]
                == summary["held_out"]["total_by_arm"]["trained"]
                and completion["trained"]["partial_visual"] == 4
            ),
            "ordered_pseudowords": reactivation["trained"] == 4,
            "web_overlap": web_overlap,
            "candidate_intervention": candidate_intervention,
        },
        "settling_failures": settling_failures,
        "seed_failures": failures,
    }


def _run_seed(payload: tuple[dict, int]) -> dict:
    from ccf6.controlled_basins import run_matched_target_basins

    template, seed = payload
    definition = copy.deepcopy(template)
    definition["seed"] = seed
    definition["network"]["seed"] = seed
    try:
        return _seed_metrics(run_matched_target_basins(definition), seed)
    except Exception as error:
        return {
            "seed": seed,
            "replicate_unit": "seed",
            "presentation_count": 0,
            "arms": ["trained", "untrained", "shuffled"],
            "conditions": {
                "stimulation_executed": False,
                "lesion_executed": False,
            },
            "values": {},
            "effects": {name: None for name in EFFECT_NAMES},
            "criteria": {
                "correct_basins": False,
                "ordered_pseudowords": False,
                "web_overlap": False,
                "candidate_intervention": False,
            },
            "settling_failures": 0,
            "seed_failures": [f"{type(error).__name__}: {error}"],
        }


def run_replicated_milestone(definition: dict) -> dict:
    """Execute paired seed replicates and emit one auditable verdict."""
    declaration = definition.get("replication")
    if not isinstance(declaration, dict) or set(declaration) != {
        "seed_inventory",
        "workers",
        "bootstrap_resamples",
        "bootstrap_seed",
        "separation_noninferiority_margin",
    }:
        raise ValueError("replication must declare seeds, workers, bootstrap, and margin")
    seeds = declaration["seed_inventory"]
    if (
        not isinstance(seeds, list)
        or len(seeds) < 20
        or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds)
        or len(set(seeds)) != len(seeds)
    ):
        raise ValueError("replication requires at least 20 unique integer seeds")
    workers = declaration["workers"]
    if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
        raise ValueError("replication workers must be a positive integer")
    template = copy.deepcopy(definition)
    template.pop("replication")
    template["kind"] = "cardinal_classification"
    with ProcessPoolExecutor(max_workers=workers) as executor:
        rows = tuple(executor.map(_run_seed, ((template, seed) for seed in seeds)))
    aggregate = MilestoneAggregator(
        bootstrap_resamples=declaration["bootstrap_resamples"],
        bootstrap_seed=declaration["bootstrap_seed"],
        separation_noninferiority_margin=declaration[
            "separation_noninferiority_margin"
        ],
    ).aggregate(rows)
    aggregate_dict = aggregate.as_dict()
    return {
        "contract": "ncl-functional-web-v1",
        "metrics": {
            "replicate_unit": "seed",
            "seed_inventory": list(seeds),
            "seeds": list(rows),
        },
        "aggregate": aggregate_dict,
        "summary": {
            "replication": {
                "seeds": len(seeds),
                "paired_arms_per_seed": 3,
                "bootstrap_resamples": declaration["bootstrap_resamples"],
                "failed_seeds": aggregate.failed_seed_count,
                "settling_failures": aggregate.total_settling_failures,
            },
            "criteria": aggregate.criteria,
            "milestone_verdict": aggregate.verdict,
        },
        "stimuli": {
            "seeds": list(seeds),
            "arms": ["trained", "untrained", "shuffled"],
        },
        "parameters": dict(declaration),
    }


class MilestoneAggregator:
    """Aggregate paired seed effects without treating Presentations as replicates."""

    def __init__(
        self,
        *,
        bootstrap_resamples: int,
        bootstrap_seed: int,
        separation_noninferiority_margin: float,
    ):
        if (
            isinstance(bootstrap_resamples, bool)
            or not isinstance(bootstrap_resamples, int)
            or bootstrap_resamples < 10_000
        ):
            raise ValueError("bootstrap requires at least 10,000 resamples")
        if isinstance(bootstrap_seed, bool) or not isinstance(bootstrap_seed, int):
            raise ValueError("bootstrap seed must be an integer")
        margin = float(separation_noninferiority_margin)
        if not 0.0 < margin < 1.0:
            raise ValueError("separation non-inferiority margin must be between zero and one")
        self.bootstrap_resamples = bootstrap_resamples
        self.bootstrap_seed = bootstrap_seed
        self.separation_noninferiority_margin = margin

    def _effect(
        self,
        values: tuple[float, ...],
        *,
        randomizer: np.random.Generator,
        expected_minimum: float,
        external_failures: int,
    ) -> AggregateEffect:
        array = np.asarray(values, dtype=np.float64)
        finite = np.isfinite(array)
        failures = int(np.count_nonzero(~finite)) + external_failures
        usable = array[finite]
        if usable.size == 0:
            return AggregateEffect(
                seed_values=values,
                median=float("nan"),
                interval_low=float("nan"),
                interval_high=float("nan"),
                expected_direction_count=0,
                expected_direction_proportion=0.0,
                failure_count=failures,
            )
        indices = randomizer.integers(
            0,
            usable.size,
            size=(self.bootstrap_resamples, usable.size),
        )
        bootstrap = np.median(usable[indices], axis=1)
        interval_low, interval_high = np.quantile(bootstrap, [0.025, 0.975])
        direction_count = int(np.count_nonzero(usable > expected_minimum))
        return AggregateEffect(
            seed_values=values,
            median=float(np.median(usable)),
            interval_low=float(interval_low),
            interval_high=float(interval_high),
            expected_direction_count=direction_count,
            expected_direction_proportion=float(direction_count / len(array)),
            failure_count=failures,
        )

    def aggregate(self, seed_rows: tuple[dict, ...]) -> MilestoneAggregate:
        if len(seed_rows) < 20:
            raise ValueError("milestone aggregation requires at least 20 paired seeds")
        seeds = [row["seed"] for row in seed_rows]
        if len(set(seeds)) != len(seeds):
            raise ValueError("replicated seed inventory must be unique")
        randomizer = np.random.default_rng(self.bootstrap_seed)
        effects = {}
        for name in EFFECT_NAMES:
            values = tuple(
                float(value) if value is not None else float("nan")
                for row in seed_rows
                for value in (row["effects"].get(name),)
            )
            expected_minimum = (
                -self.separation_noninferiority_margin
                if name == "held_out_separation_change"
                else 0.0
            )
            external_failures = (
                sum(
                    not row["conditions"]["stimulation_executed"]
                    or not row["conditions"]["lesion_executed"]
                    for row in seed_rows
                )
                if name == "candidate_intervention"
                else sum(bool(row["settling_failures"]) for row in seed_rows)
            )
            effects[name] = self._effect(
                values,
                randomizer=randomizer,
                expected_minimum=expected_minimum,
                external_failures=external_failures,
            )

        failed_seeds = tuple(
            {
                "seed": row["seed"],
                "failures": [
                    *row["seed_failures"],
                    *(
                        ["settling_failure"]
                        if row["settling_failures"]
                        and "settling_failure" not in row["seed_failures"]
                        else []
                    ),
                ],
            }
            for row in seed_rows
            if row["seed_failures"] or row["settling_failures"]
        )
        criteria = {
            "completion_improvement": {
                "passed": effects["completion"].interval_low > 0.0,
                "evidence": "completion interval lower bound above zero",
            },
            "cross_route_reactivation_improvement": {
                "passed": effects["reactivation"].interval_low > 0.0,
                "evidence": "reactivation interval lower bound above zero",
            },
            "correct_basins": {
                "passed": all(row["criteria"]["correct_basins"] for row in seed_rows),
                "failure_count": sum(
                    not row["criteria"]["correct_basins"] for row in seed_rows
                ),
            },
            "ordered_pseudowords": {
                "passed": all(
                    row["criteria"]["ordered_pseudowords"] for row in seed_rows
                ),
                "failure_count": sum(
                    not row["criteria"]["ordered_pseudowords"] for row in seed_rows
                ),
            },
            "pairing_localization": {
                "passed": effects["pairing_localization"].interval_low > 0.0,
                "evidence": "trained-minus-shuffled interval lower bound above zero",
            },
            "web_overlap": {
                "passed": all(row["criteria"]["web_overlap"] for row in seed_rows),
                "failure_count": sum(
                    not row["criteria"]["web_overlap"] for row in seed_rows
                ),
            },
            "candidate_interventions": {
                "passed": (
                    all(
                        row["criteria"]["candidate_intervention"]
                        for row in seed_rows
                    )
                    and effects["candidate_intervention"].interval_low > 0.0
                ),
                "failure_count": sum(
                    not row["criteria"]["candidate_intervention"]
                    for row in seed_rows
                ),
            },
            "held_out_separation_noninferiority": {
                "passed": effects[
                    "held_out_separation_change"
                ].interval_low
                > -self.separation_noninferiority_margin,
                "margin": -self.separation_noninferiority_margin,
            },
            "seed_execution": {
                "passed": not failed_seeds,
                "failure_count": len(failed_seeds),
            },
            "failure_reporting": {
                "passed": True,
                "settling_failures": sum(
                    int(row["settling_failures"]) for row in seed_rows
                ),
                "failed_seeds": len(failed_seeds),
            },
        }
        verdict = all(criterion["passed"] for criterion in criteria.values())
        return MilestoneAggregate(
            replicate_unit="seed",
            seed_count=len(seed_rows),
            bootstrap_resamples=self.bootstrap_resamples,
            bootstrap_seed=self.bootstrap_seed,
            effects=effects,
            criteria=criteria,
            total_settling_failures=sum(
                int(row["settling_failures"]) for row in seed_rows
            ),
            failed_seed_count=len(failed_seeds),
            failed_seeds=failed_seeds,
            verdict=verdict,
        )
