"""Offline detection of Functional Webs from converging evidence."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np


@dataclass(frozen=True)
class EvidenceResult:
    score: float
    control_threshold: float
    raw_p_value: float
    corrected_p_value: float
    passed: bool
    control_distribution: tuple[float, ...]

    def as_dict(self) -> dict:
        return {
            "score": self.score,
            "control_threshold": self.control_threshold,
            "raw_p_value": self.raw_p_value,
            "corrected_p_value": self.corrected_p_value,
            "passed": self.passed,
            "control_distribution": list(self.control_distribution),
        }


@dataclass(frozen=True)
class ColumnEvidence:
    reliability: EvidenceResult
    causal: EvidenceResult
    connectivity: EvidenceResult
    selected: bool

    def as_dict(self) -> dict:
        return {
            "reliability": self.reliability.as_dict(),
            "causal": self.causal.as_dict(),
            "connectivity": self.connectivity.as_dict(),
            "selected": self.selected,
        }


@dataclass(frozen=True)
class DetectedWeb:
    members: tuple[str, ...]
    columns: dict[str, ColumnEvidence]

    def as_dict(self) -> dict:
        return {
            "members": list(self.members),
            "columns": {
                label: evidence.as_dict()
                for label, evidence in self.columns.items()
            },
        }


@dataclass(frozen=True)
class FunctionalWebDetection:
    control_quantile: float
    fdr_alpha: float
    minimum_association_distance: float
    webs: dict[str, DetectedWeb]
    shared_columns: dict[str, tuple[str, ...]]
    association_distances: dict[str, float]
    association_distinguishable: bool

    def as_dict(self) -> dict:
        return {
            "detector": {
                "control_quantile": self.control_quantile,
                "fdr_alpha": self.fdr_alpha,
                "minimum_association_distance": self.minimum_association_distance,
            },
            "webs": {
                category: web.as_dict() for category, web in self.webs.items()
            },
            "shared_columns": {
                label: list(categories)
                for label, categories in self.shared_columns.items()
            },
            "association_distances": dict(self.association_distances),
            "association_distinguishable": self.association_distinguishable,
        }


def _benjamini_hochberg(raw_p_values: np.ndarray) -> np.ndarray:
    """Return monotone Benjamini-Hochberg adjusted p-values."""
    count = raw_p_values.size
    order = np.argsort(raw_p_values, kind="stable")
    ranked = raw_p_values[order]
    adjusted = ranked * count / np.arange(1, count + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    corrected = np.empty(count, dtype=np.float64)
    corrected[order] = np.clip(adjusted, 0.0, 1.0)
    return corrected


def _column_metadata(network) -> tuple[tuple[str, ...], np.ndarray, np.ndarray]:
    labels = tuple(network.column_labels())
    populations = []
    degrees = np.zeros(len(labels), dtype=np.int64)
    offsets = {}
    offset = 0
    for identifier in network.population_order:
        offsets[identifier] = offset
        columns = network.populations[identifier].columns
        populations.extend([identifier] * columns)
        offset += columns
    for projection in network.projections:
        sources = offsets[projection.source] + projection.sources
        targets = offsets[projection.target] + projection.targets
        np.add.at(degrees, sources, 1)
        np.add.at(degrees, targets, 1)
    return labels, np.asarray(populations), degrees


def _effective_connectivity(network, profile: np.ndarray) -> np.ndarray:
    values = np.zeros(profile.size, dtype=np.float64)
    offsets = {}
    offset = 0
    for identifier in network.population_order:
        offsets[identifier] = offset
        offset += network.populations[identifier].columns
    for projection in network.projections:
        sources = offsets[projection.source] + projection.sources
        targets = offsets[projection.target] + projection.targets
        reciprocal = np.sqrt(
            projection.ascending_weights * projection.descending_weights
        )
        effective = reciprocal * np.minimum(profile[sources], profile[targets])
        np.add.at(values, sources, effective)
        np.add.at(values, targets, effective)
    return values


def build_functional_web_evidence(
    *,
    network,
    category_ids: tuple[str, ...],
    basin_activity: np.ndarray,
    causal_scores: np.ndarray,
    control_resamples: int,
    seed: int,
) -> dict:
    """Build detector inputs solely from frozen basin-estimation observations."""
    activity = np.asarray(basin_activity, dtype=np.float64)
    if activity.ndim != 3 or activity.shape[0] != len(category_ids):
        raise ValueError("basin activity must be category-by-instance-by-Column")
    if isinstance(control_resamples, bool) or control_resamples < 1:
        raise ValueError("control resamples must be a positive integer")
    labels, populations, degrees = _column_metadata(network)
    if activity.shape[2] != len(labels):
        raise ValueError("basin activity does not match Network Columns")
    randomizer = np.random.default_rng(seed)
    category_count, instance_count, column_count = activity.shape
    profiles = activity.mean(axis=1)
    flattened = activity.reshape(category_count * instance_count, column_count)

    reliability = np.empty((category_count, column_count), dtype=np.float64)
    for category in range(category_count):
        other = np.delete(activity, category, axis=0)
        reliability[category] = (
            activity[category].mean(axis=0) - other.mean(axis=(0, 1))
        )
    reliability_controls = np.empty(
        (category_count, column_count, control_resamples), dtype=np.float64
    )
    for resample in range(control_resamples):
        shuffled = flattened[randomizer.permutation(flattened.shape[0])].reshape(
            category_count, instance_count, column_count
        )
        for category in range(category_count):
            reliability_controls[category, :, resample] = (
                shuffled[category].mean(axis=0)
                - np.delete(shuffled, category, axis=0).mean(axis=(0, 1))
            )

    causal = np.asarray(causal_scores, dtype=np.float64)
    if causal.shape != reliability.shape or not np.all(np.isfinite(causal)):
        raise ValueError("causal scores must be finite with one value per category and Column")
    causal_controls = np.empty(
        (category_count, column_count, control_resamples), dtype=np.float64
    )
    for category in range(category_count):
        for column in range(column_count):
            same_population = np.flatnonzero(populations == populations[column])
            peers = same_population[same_population != column]
            degree_matched = peers[degrees[peers] == degrees[column]]
            candidates = degree_matched if degree_matched.size else peers
            if candidates.size == 0:
                candidates = np.asarray([column])
            activity_gap = np.abs(profiles[category, candidates] - profiles[category, column])
            order = np.argsort(activity_gap, kind="stable")
            matched = candidates[order[: max(1, min(4, candidates.size))]]
            causal_controls[category, column] = randomizer.choice(
                causal[category, matched], control_resamples, replace=True
            )

    connectivity = np.stack(
        [_effective_connectivity(network, profile) for profile in profiles]
    )
    connectivity_controls = np.empty(
        (category_count, column_count, control_resamples), dtype=np.float64
    )
    degree_matched_indices = [
        np.flatnonzero((populations == identifier) & (degrees == degree))
        for identifier in network.population_order
        for degree in np.unique(degrees[populations == identifier])
    ]
    for category in range(category_count):
        for resample in range(control_resamples):
            shuffled_profile = profiles[category].copy()
            for indices in degree_matched_indices:
                shuffled_profile[indices] = randomizer.permutation(
                    shuffled_profile[indices]
                )
            connectivity_controls[category, :, resample] = _effective_connectivity(
                network, shuffled_profile
            )

    association_indices = np.asarray(
        [index for index, label in enumerate(labels) if "association#" in label]
    )
    if association_indices.size == 0:
        raise ValueError("Functional Web detection requires association Columns")
    return {
        "category_ids": tuple(category_ids),
        "column_labels": labels,
        "reliability_scores": reliability,
        "reliability_controls": reliability_controls,
        "causal_scores": causal,
        "causal_controls": causal_controls,
        "connectivity_scores": connectivity,
        "connectivity_controls": connectivity_controls,
        "association_activity": profiles[:, association_indices],
    }


class FunctionalWebObserver:
    """Classify webs without feeding observer results back into the Network."""

    def __init__(
        self,
        *,
        control_quantile: float,
        fdr_alpha: float,
        minimum_association_distance: float = 0.0,
    ):
        if not 0.0 < control_quantile < 1.0:
            raise ValueError("control quantile must be between zero and one")
        if not 0.0 < fdr_alpha < 1.0:
            raise ValueError("FDR alpha must be between zero and one")
        if minimum_association_distance < 0.0:
            raise ValueError("minimum association distance must not be negative")
        self.control_quantile = float(control_quantile)
        self.fdr_alpha = float(fdr_alpha)
        self.minimum_association_distance = float(minimum_association_distance)

    @staticmethod
    def _arrays(
        scores: np.ndarray,
        controls: np.ndarray,
        *,
        category_count: int,
        column_count: int,
        name: str,
    ) -> tuple[np.ndarray, np.ndarray]:
        observed = np.asarray(scores, dtype=np.float64)
        null = np.asarray(controls, dtype=np.float64)
        if observed.shape != (category_count, column_count):
            raise ValueError(
                f"{name} scores must have one value per category and Column"
            )
        if null.ndim != 3 or null.shape[:2] != observed.shape or null.shape[2] < 1:
            raise ValueError(
                f"{name} controls must have a non-empty distribution per score"
            )
        if not np.all(np.isfinite(observed)) or not np.all(np.isfinite(null)):
            raise ValueError(f"{name} evidence must be finite")
        return observed, null

    def _evidence(
        self,
        scores: np.ndarray,
        controls: np.ndarray,
    ) -> list[list[EvidenceResult]]:
        rows = []
        for category_scores, category_controls in zip(
            scores, controls, strict=True
        ):
            raw = np.asarray(
                [
                    (1.0 + np.count_nonzero(null >= score)) / (len(null) + 1.0)
                    for score, null in zip(
                        category_scores, category_controls, strict=True
                    )
                ]
            )
            corrected = _benjamini_hochberg(raw)
            category_rows = []
            for score, null, raw_p, corrected_p in zip(
                category_scores,
                category_controls,
                raw,
                corrected,
                strict=True,
            ):
                threshold = float(
                    np.quantile(null, self.control_quantile, method="higher")
                )
                category_rows.append(
                    EvidenceResult(
                        score=float(score),
                        control_threshold=threshold,
                        raw_p_value=float(raw_p),
                        corrected_p_value=float(corrected_p),
                        passed=bool(
                            score > threshold and corrected_p <= self.fdr_alpha
                        ),
                        control_distribution=tuple(float(value) for value in null),
                    )
                )
            rows.append(category_rows)
        return rows

    def detect(
        self,
        *,
        category_ids: tuple[str, ...],
        column_labels: tuple[str, ...],
        reliability_scores: np.ndarray,
        reliability_controls: np.ndarray,
        causal_scores: np.ndarray,
        causal_controls: np.ndarray,
        connectivity_scores: np.ndarray,
        connectivity_controls: np.ndarray,
        association_activity: np.ndarray,
    ) -> FunctionalWebDetection:
        categories = tuple(category_ids)
        labels = tuple(column_labels)
        if not categories or len(set(categories)) != len(categories):
            raise ValueError("category IDs must be non-empty and unique")
        if not labels or len(set(labels)) != len(labels):
            raise ValueError("Column labels must be non-empty and unique")
        dimensions = {
            "reliability": (reliability_scores, reliability_controls),
            "causal": (causal_scores, causal_controls),
            "connectivity": (connectivity_scores, connectivity_controls),
        }
        prepared = {
            name: self._arrays(
                scores,
                controls,
                category_count=len(categories),
                column_count=len(labels),
                name=name,
            )
            for name, (scores, controls) in dimensions.items()
        }
        evidence = {
            name: self._evidence(*values) for name, values in prepared.items()
        }

        webs = {}
        memberships: dict[str, list[str]] = {label: [] for label in labels}
        for category_index, category in enumerate(categories):
            columns = {}
            members = []
            for column_index, label in enumerate(labels):
                row = ColumnEvidence(
                    reliability=evidence["reliability"][category_index][column_index],
                    causal=evidence["causal"][category_index][column_index],
                    connectivity=evidence["connectivity"][category_index][column_index],
                    selected=all(
                        evidence[name][category_index][column_index].passed
                        for name in evidence
                    ),
                )
                columns[label] = row
                if row.selected:
                    members.append(label)
                    memberships[label].append(category)
            webs[category] = DetectedWeb(tuple(members), columns)

        activity = np.asarray(association_activity, dtype=np.float64)
        if activity.ndim != 2 or activity.shape[0] != len(categories):
            raise ValueError("association activity must have one profile per category")
        if activity.shape[1] < 1 or not np.all(np.isfinite(activity)):
            raise ValueError("association activity profiles must be non-empty and finite")
        distances = {
            f"{left}:{right}": float(
                np.linalg.norm(activity[left_index] - activity[right_index])
            )
            for (left_index, left), (right_index, right) in combinations(
                enumerate(categories), 2
            )
        }
        shared = {
            label: tuple(category_memberships)
            for label, category_memberships in memberships.items()
            if len(category_memberships) > 1
        }
        return FunctionalWebDetection(
            control_quantile=self.control_quantile,
            fdr_alpha=self.fdr_alpha,
            minimum_association_distance=self.minimum_association_distance,
            webs=webs,
            shared_columns=shared,
            association_distances=distances,
            association_distinguishable=bool(
                distances
                and min(distances.values())
                > self.minimum_association_distance
            ),
        )
