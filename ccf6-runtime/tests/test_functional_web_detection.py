"""Offline Functional Web detection from converging causal evidence."""

from __future__ import annotations

import numpy as np

from ccf6.functional_webs import FunctionalWebObserver


def evidence_fixture():
    categories = ("category-1", "category-2")
    columns = (
        "visual-contour#0",
        "visual-contour#1",
        "cross-domain-association#0",
        "cross-domain-association#1",
    )
    controls = np.linspace(0.0, 0.49, 1000)
    control_cube = np.broadcast_to(controls, (2, 4, controls.size)).copy()
    reliability = np.asarray(
        [
            [0.9, 0.1, 0.9, 0.1],
            [0.9, 0.1, 0.1, 0.9],
        ]
    )
    causal = reliability.copy()
    connectivity = reliability.copy()
    association = np.asarray([[0.9, 0.1], [0.1, 0.9]])
    return {
        "category_ids": categories,
        "column_labels": columns,
        "reliability_scores": reliability,
        "reliability_controls": control_cube,
        "causal_scores": causal,
        "causal_controls": control_cube.copy(),
        "connectivity_scores": connectivity,
        "connectivity_controls": control_cube.copy(),
        "association_activity": association,
    }


def test_web_membership_requires_all_evidence_and_corrected_control_superiority():
    inputs = evidence_fixture()
    # Activation reliability alone is high for this Column; causal evidence is not.
    inputs["causal_scores"][0, 2] = 0.2

    result = FunctionalWebObserver(control_quantile=0.95, fdr_alpha=0.05).detect(
        **inputs
    )

    first = result.webs["category-1"]
    assert first.members == ("visual-contour#0",)
    rejected = first.columns["cross-domain-association#0"]
    assert rejected.reliability.passed is True
    assert rejected.causal.passed is False
    assert rejected.selected is False
    assert len(rejected.causal.control_distribution) == 1000
    assert rejected.causal.corrected_p_value > 0.05


def test_detected_webs_can_overlap_while_association_activity_is_distinguishable():
    result = FunctionalWebObserver(
        control_quantile=0.95,
        fdr_alpha=0.05,
        minimum_association_distance=0.5,
    ).detect(**evidence_fixture())

    assert result.webs["category-1"].members == (
        "visual-contour#0",
        "cross-domain-association#0",
    )
    assert result.webs["category-2"].members == (
        "visual-contour#0",
        "cross-domain-association#1",
    )
    assert result.shared_columns == {
        "visual-contour#0": ("category-1", "category-2")
    }
    assert result.association_distinguishable is True
    assert result.as_dict()["detector"] == {
        "control_quantile": 0.95,
        "fdr_alpha": 0.05,
        "minimum_association_distance": 0.5,
    }


def test_activation_threshold_set_cannot_qualify_as_a_functional_web():
    inputs = evidence_fixture()
    inputs["causal_scores"].fill(0.1)
    inputs["connectivity_scores"].fill(0.1)

    result = FunctionalWebObserver(control_quantile=0.95, fdr_alpha=0.05).detect(
        **inputs
    )

    assert all(not web.members for web in result.webs.values())
