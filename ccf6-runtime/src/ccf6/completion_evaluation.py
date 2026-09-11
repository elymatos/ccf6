"""Frozen completion and ordered phonological trajectory observations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class OrderedTrajectoryEvaluation:
    correct_distance: float
    control_distances: dict[str, float]
    correct_better_than_every_control: bool

    def as_dict(self) -> dict:
        return {
            "correct_distance": self.correct_distance,
            "control_distances": dict(self.control_distances),
            "correct_better_than_every_control": (
                self.correct_better_than_every_control
            ),
        }


class OrderedTrajectoryObserver:
    """Compare variable-duration trajectories without collapsing temporal order."""

    def __init__(self, *, sample_points: int):
        if isinstance(sample_points, bool) or not isinstance(sample_points, int):
            raise ValueError("trajectory sample points must be an integer")
        if sample_points < 2:
            raise ValueError("trajectory sample points must be at least 2")
        self.sample_points = sample_points

    def sample(self, trajectory: np.ndarray) -> np.ndarray:
        """Return the declared, order-preserving trajectory representation."""
        values = np.asarray(trajectory, dtype=np.float64)
        if values.ndim != 2 or values.shape[0] < 1 or values.shape[1] < 1:
            raise ValueError("trajectory must be a non-empty tick-by-Column matrix")
        source = np.linspace(0.0, 1.0, values.shape[0])
        target = np.linspace(0.0, 1.0, self.sample_points)
        return np.column_stack(
            [np.interp(target, source, values[:, column]) for column in range(values.shape[1])]
        )

    def _distance(self, left: np.ndarray, right: np.ndarray) -> float:
        left_sampled = self.sample(left)
        right_sampled = self.sample(right)
        if left_sampled.shape != right_sampled.shape:
            raise ValueError("ordered trajectories must use the same Columns")
        return float(np.sqrt(np.mean(np.square(left_sampled - right_sampled))))

    def evaluate(
        self,
        *,
        visual_reactivation: np.ndarray,
        correct_trajectory: np.ndarray,
        control_trajectories: dict[str, np.ndarray],
    ) -> OrderedTrajectoryEvaluation:
        if not control_trajectories:
            raise ValueError("ordered reactivation requires control trajectories")
        correct_distance = self._distance(
            visual_reactivation,
            correct_trajectory,
        )
        control_distances = {
            name: self._distance(visual_reactivation, trajectory)
            for name, trajectory in control_trajectories.items()
        }
        return OrderedTrajectoryEvaluation(
            correct_distance=correct_distance,
            control_distances=control_distances,
            correct_better_than_every_control=all(
                correct_distance < distance
                for distance in control_distances.values()
            ),
        )
