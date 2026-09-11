"""Partial-cue completion and ordered phonological reactivation observers."""

from __future__ import annotations

import copy

import numpy as np

from ccf6.completion_evaluation import OrderedTrajectoryObserver


def test_ordered_trajectory_observer_rejects_the_same_unordered_feature_bag():
    observer = OrderedTrajectoryObserver(sample_points=6)
    correct = np.asarray(
        [
            [1.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
        ]
    )
    reversed_trajectory = correct[::-1].copy()
    permuted_trajectory = np.concatenate((correct[2:], correct[:2]))
    repeated_trajectory = np.repeat(correct[2:3], len(correct), axis=0)
    visual_reactivation = correct.copy()
    controls = {
        "reversed": reversed_trajectory,
        "permuted": permuted_trajectory,
        "repeated_segment": repeated_trajectory,
    }
    before = copy.deepcopy(controls)

    result = observer.evaluate(
        visual_reactivation=visual_reactivation,
        correct_trajectory=correct,
        control_trajectories=controls,
    )

    assert result.correct_distance == 0.0
    assert result.correct_better_than_every_control is True
    assert all(distance > 0.0 for distance in result.control_distances.values())
    assert all(
        np.array_equal(controls[name], before[name]) for name in controls
    )
