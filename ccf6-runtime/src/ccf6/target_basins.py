"""Offline frozen Target Basin estimation without held-out evidence."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TargetBasin:
    category_id: str
    instance_ids: tuple[str, ...]
    centroid: np.ndarray
    column_standard_deviation: np.ndarray
    reliable_mask: np.ndarray
    within_distances: tuple[float, ...]
    within_cosine_distances: tuple[float, ...]
    between_distances: dict[str, float]
    between_cosine_distances: dict[str, float]
    margin: float


@dataclass(frozen=True)
class BasinEvaluation:
    expected_category: str
    initial_distance: float
    settled_distance: float
    correct_distance: float
    competing_distances: dict[str, float]
    margin: float
    closer_after_settling: bool
    beats_every_competitor: bool
    correct_basin: bool

    def as_dict(self) -> dict:
        return {
            "expected_category": self.expected_category,
            "initial_distance": self.initial_distance,
            "settled_distance": self.settled_distance,
            "correct_distance": self.correct_distance,
            "competing_distances": dict(self.competing_distances),
            "margin": self.margin,
            "closer_after_settling": self.closer_after_settling,
            "beats_every_competitor": self.beats_every_competitor,
            "correct_basin": self.correct_basin,
        }


class FrozenTargetBasins:
    """Immutable fitted basin evidence used by later evaluation only."""

    def __init__(
        self,
        *,
        categories: dict[str, TargetBasin],
        pooled_scale: np.ndarray,
        minimum_scale: float,
        column_labels: tuple[str, ...],
        maximum_column_standard_deviation: float,
        minimum_reliable_columns: int,
        margin_quantile: float,
    ):
        self.categories = dict(categories)
        self.pooled_scale = pooled_scale.copy()
        self.pooled_scale.setflags(write=False)
        self.minimum_scale = minimum_scale
        self.column_labels = column_labels
        self.maximum_column_standard_deviation = (
            maximum_column_standard_deviation
        )
        self.minimum_reliable_columns = minimum_reliable_columns
        self.margin_quantile = margin_quantile

    def _distance(self, activity: np.ndarray, basin: TargetBasin) -> float:
        difference = (
            np.asarray(activity, dtype=np.float64)[basin.reliable_mask]
            - basin.centroid[basin.reliable_mask]
        ) / self.pooled_scale[basin.reliable_mask]
        return float(np.sqrt(np.mean(np.square(difference))))

    def evaluate(
        self,
        *,
        expected_category: str,
        initial_activity: np.ndarray,
        settled_activity: np.ndarray,
    ) -> BasinEvaluation:
        if expected_category not in self.categories:
            raise ValueError(f"unknown Target Basin {expected_category!r}")
        if np.asarray(initial_activity).shape != self.pooled_scale.shape:
            raise ValueError("initial activity does not match Target Basin Columns")
        if np.asarray(settled_activity).shape != self.pooled_scale.shape:
            raise ValueError("settled activity does not match Target Basin Columns")
        correct = self.categories[expected_category]
        initial_distance = self._distance(initial_activity, correct)
        settled_distance = self._distance(settled_activity, correct)
        competing = {
            category_id: self._distance(settled_activity, basin)
            for category_id, basin in self.categories.items()
            if category_id != expected_category
        }
        beats_every = all(
            settled_distance + correct.margin < distance
            for distance in competing.values()
        )
        closer = settled_distance < initial_distance
        return BasinEvaluation(
            expected_category=expected_category,
            initial_distance=initial_distance,
            settled_distance=settled_distance,
            correct_distance=settled_distance,
            competing_distances=competing,
            margin=correct.margin,
            closer_after_settling=closer,
            beats_every_competitor=beats_every,
            correct_basin=closer and beats_every,
        )

    def as_dict(self) -> dict:
        return {
            "fit_splits": ["acquisition", "basin_estimation"],
            "held_out_used_for_fit": False,
            "minimum_scale": self.minimum_scale,
            "pooled_scale": self.pooled_scale.tolist(),
            "column_labels": list(self.column_labels),
            "reliability": {
                "maximum_column_standard_deviation": self.maximum_column_standard_deviation,
                "minimum_reliable_columns": self.minimum_reliable_columns,
            },
            "margin_quantile": self.margin_quantile,
            "categories": {
                category_id: {
                    "instance_ids": list(basin.instance_ids),
                    "centroid": basin.centroid.tolist(),
                    "column_standard_deviation": (
                        basin.column_standard_deviation.tolist()
                    ),
                    "reliable_mask": basin.reliable_mask.tolist(),
                    "reliable_columns": int(np.count_nonzero(basin.reliable_mask)),
                    "within_distances": list(basin.within_distances),
                    "within_cosine_distances": list(
                        basin.within_cosine_distances
                    ),
                    "between_distances": dict(basin.between_distances),
                    "between_cosine_distances": dict(
                        basin.between_cosine_distances
                    ),
                    "margin": basin.margin,
                }
                for category_id, basin in self.categories.items()
            },
        }


class TargetBasinObserver:
    """Fit reliable basin distributions from basin-estimation activity."""

    def __init__(
        self,
        *,
        minimum_scale: float,
        maximum_column_standard_deviation: float,
        minimum_reliable_columns: int,
        margin_quantile: float,
    ):
        if minimum_scale <= 0.0:
            raise ValueError("minimum scale must be positive")
        if maximum_column_standard_deviation < 0.0:
            raise ValueError("maximum Column standard deviation cannot be negative")
        if minimum_reliable_columns < 1:
            raise ValueError("minimum reliable Columns must be positive")
        if not 0.0 <= margin_quantile <= 1.0:
            raise ValueError("margin quantile must be in [0,1]")
        self.minimum_scale = float(minimum_scale)
        self.maximum_column_standard_deviation = float(
            maximum_column_standard_deviation
        )
        self.minimum_reliable_columns = int(minimum_reliable_columns)
        self.margin_quantile = float(margin_quantile)

    @staticmethod
    def _cosine_distance(left: np.ndarray, right: np.ndarray) -> float:
        denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
        if denominator == 0.0:
            return 0.0 if np.array_equal(left, right) else 1.0
        return float(1.0 - np.dot(left, right) / denominator)

    @staticmethod
    def _freeze(array: np.ndarray) -> np.ndarray:
        frozen = np.asarray(array).copy()
        frozen.setflags(write=False)
        return frozen

    def fit(
        self,
        observations: dict[str, np.ndarray],
        *,
        column_labels: tuple[str, ...],
        instance_ids: dict[str, tuple[str, ...]],
    ) -> FrozenTargetBasins:
        if len(observations) < 2:
            raise ValueError("Target Basins require at least two categories")
        if set(observations) != set(instance_ids):
            raise ValueError("Target Basin observations and instance identities differ")
        arrays = {
            category_id: np.asarray(values, dtype=np.float64)
            for category_id, values in observations.items()
        }
        column_count = len(column_labels)
        for category_id, values in arrays.items():
            if values.shape != (4, column_count):
                raise ValueError(
                    f"{category_id}: Target Basin estimation requires four "
                    f"instances with {column_count} Columns"
                )
            if len(instance_ids[category_id]) != 4:
                raise ValueError(
                    f"{category_id}: four basin-estimation identities are required"
                )
        pooled_scale = np.maximum(
            np.std(np.concatenate(list(arrays.values())), axis=0, ddof=1),
            self.minimum_scale,
        )
        centroids = {
            category_id: values.mean(axis=0)
            for category_id, values in arrays.items()
        }
        basins = {}
        for category_id, values in arrays.items():
            standard_deviation = np.std(values, axis=0)
            reliable = (
                standard_deviation
                <= self.maximum_column_standard_deviation
            )
            if np.count_nonzero(reliable) < self.minimum_reliable_columns:
                raise ValueError(
                    f"{category_id}: only {np.count_nonzero(reliable)} reliable "
                    f"Columns; {self.minimum_reliable_columns} required"
                )
            centroid = centroids[category_id]
            within = tuple(
                float(
                    np.sqrt(
                        np.mean(
                            np.square(
                                (activity[reliable] - centroid[reliable])
                                / pooled_scale[reliable]
                            )
                        )
                    )
                )
                for activity in values
            )
            within_cosine = tuple(
                self._cosine_distance(activity[reliable], centroid[reliable])
                for activity in values
            )
            between = {
                other_id: float(
                    np.sqrt(
                        np.mean(
                            np.square(
                                (
                                    centroids[other_id][reliable]
                                    - centroid[reliable]
                                )
                                / pooled_scale[reliable]
                            )
                        )
                    )
                )
                for other_id in centroids
                if other_id != category_id
            }
            between_cosine = {
                other_id: self._cosine_distance(
                    centroids[other_id][reliable],
                    centroid[reliable],
                )
                for other_id in centroids
                if other_id != category_id
            }
            basins[category_id] = TargetBasin(
                category_id=category_id,
                instance_ids=tuple(instance_ids[category_id]),
                centroid=self._freeze(centroid),
                column_standard_deviation=self._freeze(standard_deviation),
                reliable_mask=self._freeze(reliable),
                within_distances=within,
                within_cosine_distances=within_cosine,
                between_distances=between,
                between_cosine_distances=between_cosine,
                margin=float(np.quantile(within, self.margin_quantile)),
            )
        return FrozenTargetBasins(
            categories=basins,
            pooled_scale=pooled_scale,
            minimum_scale=self.minimum_scale,
            column_labels=column_labels,
            maximum_column_standard_deviation=(
                self.maximum_column_standard_deviation
            ),
            minimum_reliable_columns=self.minimum_reliable_columns,
            margin_quantile=self.margin_quantile,
        )
