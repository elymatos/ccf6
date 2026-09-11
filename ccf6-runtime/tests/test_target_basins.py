"""Frozen Target Basin estimation and evaluation."""

from __future__ import annotations

import copy

import numpy as np
import pytest

from ccf6.target_basins import TargetBasinObserver


def test_standardized_distance_uses_frozen_scales_masks_and_margin():
    observations = {
        "category-1": np.asarray(
            [
                [0.0, 0.0, 0.5],
                [0.0, 0.4, 0.5],
                [0.0, 0.0, 0.5],
                [0.0, 0.4, 0.5],
            ]
        ),
        "category-2": np.asarray(
            [
                [1.0, 0.6, 0.5],
                [1.0, 1.0, 0.5],
                [1.0, 0.6, 0.5],
                [1.0, 1.0, 0.5],
            ]
        ),
    }
    observer = TargetBasinObserver(
        minimum_scale=0.2,
        maximum_column_standard_deviation=0.1,
        minimum_reliable_columns=2,
        margin_quantile=0.95,
    )

    frozen = observer.fit(
        observations,
        column_labels=("population#0", "population#1", "population#2"),
        instance_ids={
            "category-1": ("a1", "a2", "a3", "a4"),
            "category-2": ("b1", "b2", "b3", "b4"),
        },
    )

    np.testing.assert_allclose(frozen.pooled_scale[2], 0.2)
    np.testing.assert_array_equal(
        frozen.categories["category-1"].reliable_mask,
        [True, False, True],
    )
    np.testing.assert_array_equal(
        frozen.categories["category-2"].reliable_mask,
        [True, False, True],
    )
    assert frozen.categories["category-1"].centroid.tolist() == [0.0, 0.2, 0.5]
    assert frozen.categories["category-2"].centroid.tolist() == [1.0, 0.8, 0.5]
    assert frozen.categories["category-1"].within_distances == (0.0, 0.0, 0.0, 0.0)
    assert frozen.categories["category-1"].margin == 0.0

    before = copy.deepcopy(frozen.as_dict())
    evaluation = frozen.evaluate(
        expected_category="category-1",
        initial_activity=np.asarray([0.9, 0.8, 0.5]),
        settled_activity=np.asarray([0.1, 0.9, 0.5]),
    )

    assert evaluation.correct_basin is True
    assert evaluation.settled_distance == pytest.approx(0.13228756555322954)
    assert evaluation.settled_distance < evaluation.initial_distance
    assert evaluation.correct_distance + evaluation.margin < min(
        evaluation.competing_distances.values()
    )
    failed_evaluation = frozen.evaluate(
        expected_category="category-1",
        initial_activity=np.asarray([0.9, 0.8, 0.5]),
        settled_activity=np.asarray([0.1, 0.9, 0.5]),
        settled_successfully=False,
    )
    assert failed_evaluation.closer_after_settling is True
    assert failed_evaluation.beats_every_competitor is True
    assert failed_evaluation.settling_failure is True
    assert failed_evaluation.correct_basin is False
    assert frozen.as_dict() == before
