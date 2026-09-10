"""Coordinated visual and ordered phonological Presentations."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ccf6.domain import generate_domain
from ccf6.experiment import execute, load
from ccf6.functional_network import Network
from ccf6.functional_presentation import PresentationProtocol


def network_definition() -> dict:
    populations = [
        {
            "id": f"visual-{dimension}",
            "columns": 4,
            "provenance": f"generated {dimension} properties",
            "wiring_role": "visual sensory input",
            "inhibition": {"radius": 1, "strength": 0.0},
        }
        for dimension in ("contour", "surface", "marking")
    ]
    populations.append(
        {
            "id": "auditory-feature",
            "columns": 3,
            "provenance": "generated reusable auditory features",
            "wiring_role": "auditory sensory input",
            "inhibition": {"radius": 1, "strength": 0.0},
        }
    )
    return {
        "seed": 20260910,
        "populations": populations,
        "projections": [],
        "thresholds": {
            "distribution": "uniform",
            "low": 0.35,
            "high": 0.55,
            "minimum": 0.2,
            "maximum": 0.8,
        },
        "dynamics": {
            "dt": 0.1,
            "tau_input": 0.3,
            "tau_integration": 0.4,
            "tau_output": 0.5,
            "recurrent_gain": 1.0,
            "temperature": 0.1,
            "transmission_cutoff": 0.05,
        },
        "settling": {"epsilon": 0.0001, "stable_ticks": 3, "max_ticks": 200},
    }


def test_activity_persists_between_samples_and_resets_between_presentations():
    dataset = generate_domain(20260910)
    network = Network(network_definition())
    protocol = PresentationProtocol(
        network,
        dataset,
        visual_populations={
            "contour": "visual-contour",
            "surface": "visual-surface",
            "marking": "visual-marking",
        },
        auditory_population="auditory-feature",
    )
    category = dataset["categories"][0]
    pseudoword = dataset["pseudowords"][0]

    first = protocol.run(
        presentation_id="presentation-1",
        category=category,
        pseudoword_id=pseudoword["id"],
        segments=pseudoword["segments"],
        condition="correct",
        success_signal=1.0,
    )
    second = protocol.run(
        presentation_id="presentation-2",
        category=category,
        pseudoword_id=pseudoword["id"],
        segments=pseudoword["segments"],
        condition="correct",
        success_signal=1.0,
    )

    assert [sample.kind for sample in first.samples] == [
        "visual",
        "auditory",
        "auditory",
        "auditory",
    ]
    np.testing.assert_array_equal(first.initial_activity, 0.0)
    np.testing.assert_array_equal(second.initial_activity, 0.0)
    for previous, current in zip(first.samples, first.samples[1:], strict=False):
        np.testing.assert_array_equal(
            previous.settling.activity[-1],
            current.settling.activity[0],
        )
    visual_columns = 12
    visual_response = first.samples[0].settling.activity[-1, :visual_columns, 2].sum()
    assert all(
        sample.settling.activity[-1, :visual_columns, 2].sum()
        >= 0.9 * visual_response
        for sample in first.samples[1:]
    )


def test_eligibility_persists_between_samples_and_resets_between_presentations():
    definition_path = (
        Path(__file__).parents[2] / "experiments/005-success-gated-learning.json"
    )
    definition = load(definition_path)
    dataset = generate_domain(definition["seed"])
    network = Network(definition["network"])
    protocol = PresentationProtocol(
        network,
        dataset,
        visual_populations=definition["presentation"]["visual_populations"],
        auditory_population=definition["presentation"]["auditory_population"],
    )
    category = dataset["categories"][0]
    pseudoword = dataset["pseudowords"][0]

    first = protocol.run(
        presentation_id="presentation-1",
        category=category,
        pseudoword_id=pseudoword["id"],
        segments=pseudoword["segments"],
        condition="correct",
        success_signal=1.0,
    )
    second = protocol.run(
        presentation_id="presentation-2",
        category=category,
        pseudoword_id=pseudoword["id"],
        segments=pseudoword["segments"],
        condition="correct",
        success_signal=1.0,
    )

    assert np.any(first.samples[0].settled_eligibility > 0.0)
    for previous, current in zip(first.samples, first.samples[1:], strict=False):
        np.testing.assert_array_equal(
            previous.settled_eligibility,
            current.initial_eligibility,
        )
    np.testing.assert_array_equal(first.samples[0].initial_eligibility, 0.0)
    np.testing.assert_array_equal(second.samples[0].initial_eligibility, 0.0)


def test_every_generated_visual_dimension_requires_one_population():
    dataset = generate_domain(20260910)
    network = Network(network_definition())

    with pytest.raises(
        ValueError,
        match="one visual-property Population is required per dimension",
    ):
        PresentationProtocol(
            network,
            dataset,
            visual_populations={
                "contour": "visual-contour",
                "surface": "visual-surface",
            },
            auditory_population="auditory-feature",
        )


def test_presentations_preserve_order_and_reject_unordered_feature_bags(tmp_path):
    definition_path = (
        Path(__file__).parents[2] / "experiments/004-coordinated-presentation.json"
    )

    run = execute(load(definition_path), tmp_path)

    manifest = json.loads((run / "manifest.json").read_text())
    summary = json.loads((run / "summary.json").read_text())
    topology = json.loads((run / "topology.json").read_text())
    assert manifest["files"] == [
        "definition.json",
        "manifest.json",
        "dataset.json",
        "topology.npz",
        "topology.json",
        "presentations.jsonl",
        "activity.npz",
        "activity.json",
        "summary.json",
    ]
    assert [row["id"] for row in topology["populations"]] == [
        "visual-contour",
        "visual-surface",
        "visual-marking",
        "visual-association",
        "cross-domain-association",
        "phonological-association",
        "auditory-feature",
    ]
    assert summary["presentations"]["total"] == 28
    assert summary["presentations"]["samples"] == 112
    assert summary["presentations"]["by_condition"] == {
        "correct": 4,
        "reversed": 4,
        "permuted": 4,
        "repeated_segment": 4,
        "competing": 12,
    }
    assert summary["persistence"]["minimum_visual_retention_ratio"] >= 0.9
    assert summary["sequence_sensitivity"]["same_bag_sequence_pairs"] > 0
    assert summary["sequence_sensitivity"]["minimum_trajectory_distance"] > 0.0
    assert summary["sequence_sensitivity"]["passed"] is True
    assert summary["settling"]["failures"] == 0
    assert "category-" not in json.dumps(topology["populations"])
    assert {
        (row["source"], row["target"]) for row in topology["projections"]
    } == {
        ("visual-contour", "visual-association"),
        ("visual-surface", "visual-association"),
        ("visual-marking", "visual-association"),
        ("visual-association", "cross-domain-association"),
        ("phonological-association", "cross-domain-association"),
        ("auditory-feature", "phonological-association"),
    }

    presentations = [
        json.loads(line)
        for line in (run / "presentations.jsonl").read_text().splitlines()
    ]
    assert len(presentations) == 28
    assert all(
        [sample["kind"] for sample in row["samples"]]
        == ["visual", "auditory", "auditory", "auditory"]
        for row in presentations
    )
    assert all(
        [sample["id"] for sample in row["samples"][1:]] == row["segments"]
        for row in presentations
    )
    assert all(
        "output_trajectory" in sample
        for row in presentations
        for sample in row["samples"]
    )

    activity = np.load(run / "activity.npz")
    assert activity["initial_activity"].shape == (28, 55, 3)
    assert activity["settled_activity"].shape == (28, 4, 55, 3)
    assert activity["sample_durations"].shape == (28, 4)
    assert activity["trajectory_offsets"].shape == (113,)
    assert np.all(activity["initial_activity"] == 0.0)
    assert np.all(activity["sample_settled"])

    correct = np.flatnonzero(activity["conditions"] == "correct")[0]
    reversed_control = np.flatnonzero(activity["conditions"] == "reversed")[0]
    assert sorted(activity["sample_ids"][correct, 1:]) == sorted(
        activity["sample_ids"][reversed_control, 1:]
    )
    assert not np.allclose(
        activity["settled_activity"][correct, 1:, :, 2],
        activity["settled_activity"][reversed_control, 1:, :, 2],
    )
