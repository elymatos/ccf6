"""The synthetic lexical-grounding domain at the artifact seam."""

from __future__ import annotations

import copy
import json

import pytest

from ccf6.domain import DomainValidationError, generate_domain, validate_domain
from ccf6.experiment import execute


DEFINITION = {
    "number": "002",
    "name": "Synthetic lexical-grounding domain",
    "kind": "synthetic_lexical_grounding",
    "question": "Does the generated domain satisfy the Functional Web constraints?",
    "seed": 20260910,
}


def read(run, name):
    return json.loads((run / name).read_text())


def test_a_declared_seed_generates_the_complete_domain_artifact(tmp_path):
    run = execute(DEFINITION, tmp_path)

    dataset = read(run, "dataset.json")
    manifest = read(run, "manifest.json")
    assert dataset["seed"] == 20260910
    assert len(dataset["categories"]) == 4
    assert manifest["contract"] == "ncl-functional-web-v1"
    assert manifest["files"] == [
        "definition.json",
        "manifest.json",
        "dataset.json",
        "summary.json",
    ]


def test_every_category_has_a_prototype_and_immutable_disjoint_splits(tmp_path):
    dataset = read(execute(DEFINITION, tmp_path), "dataset.json")

    for category in dataset["categories"]:
        assert len(category["prototype"]["properties"]) == 3
        assert len(category["splits"]["acquisition"]) == 8
        assert len(category["splits"]["basin_estimation"]) == 4
        assert len(category["splits"]["final_held_out"]) == 4
        split_ids = [
            instance["id"]
            for instances in category["splits"].values()
            for instance in instances
        ]
        assert len(split_ids) == len(set(split_ids))
        assert len({
            instance["prototype_distance"]
            for instances in category["splits"].values()
            for instance in instances
        }) > 1


def test_generated_domain_satisfies_constraints(tmp_path):
    dataset = read(execute(DEFINITION, tmp_path), "dataset.json")

    checks = {check["name"]: check for check in dataset["constraint_checks"]}
    expected = {
        "no_category_unique_prototype_property",
        "balanced_visual_property_marginals",
        "complete_pairwise_prototype_overlap",
        "prototype_property_shared_by_exactly_two_categories",
        "acquisition_and_final_held_out_are_disjoint",
        "prototype_distance_varies",
    }
    assert set(checks) >= expected
    assert all(checks[name]["passed"] is True for name in expected)


def test_a_category_unique_property_is_rejected():
    dataset = generate_domain(1)
    candidate = copy.deepcopy(dataset)
    candidate["categories"][0]["prototype"]["properties"][0]["value"] = "unique"

    with pytest.raises(DomainValidationError) as error:
        validate_domain(candidate)

    assert "no_category_unique_prototype_property" in error.value.failed_checks


def test_unbalanced_property_marginals_are_rejected():
    candidate = generate_domain(2)
    candidate["categories"][0]["splits"]["acquisition"][0]["properties"][0][
        "value"
    ] = "angular"

    with pytest.raises(DomainValidationError) as error:
        validate_domain(candidate)

    assert "balanced_visual_property_marginals" in error.value.failed_checks


def test_missing_pairwise_overlap_is_rejected():
    candidate = generate_domain(3)
    candidate["categories"][0]["prototype"]["properties"][2]["value"] = "spotted"

    with pytest.raises(DomainValidationError) as error:
        validate_domain(candidate)

    assert "complete_pairwise_prototype_overlap" in error.value.failed_checks


def test_missing_exactly_two_category_overlap_is_rejected():
    candidate = generate_domain(4)
    prototype = copy.deepcopy(candidate["categories"][0]["prototype"])
    for category in candidate["categories"]:
        category["prototype"] = copy.deepcopy(prototype)

    with pytest.raises(DomainValidationError) as error:
        validate_domain(candidate)

    assert (
        "prototype_property_shared_by_exactly_two_categories"
        in error.value.failed_checks
    )


def test_duplicate_acquisition_and_final_held_out_instances_are_rejected():
    candidate = generate_domain(5)
    category = candidate["categories"][0]
    category["splits"]["final_held_out"][0]["properties"] = copy.deepcopy(
        category["splits"]["acquisition"][0]["properties"]
    )

    with pytest.raises(DomainValidationError) as error:
        validate_domain(candidate)

    assert "acquisition_and_final_held_out_are_disjoint" in error.value.failed_checks


def test_no_prototype_distance_variation_is_rejected():
    candidate = generate_domain(6)
    for category in candidate["categories"]:
        one_step_instance = copy.deepcopy(category["splits"]["acquisition"][0])
        for instances in category["splits"].values():
            for instance in instances:
                instance["properties"] = copy.deepcopy(one_step_instance["properties"])

    with pytest.raises(DomainValidationError) as error:
        validate_domain(candidate)

    assert "prototype_distance_varies" in error.value.failed_checks


def test_pseudoword_identity_requires_order(tmp_path):
    dataset = read(execute(DEFINITION, tmp_path), "dataset.json")

    segments = {segment["id"]: segment for segment in dataset["auditory_segments"]}
    pseudowords = dataset["pseudowords"]
    segment_uses = {
        segment_id: sum(
            segment_id in pseudoword["segments"] for pseudoword in pseudowords
        )
        for segment_id in segments
    }
    feature_uses = {
        feature: sum(
            feature in segment["features"] for segment in segments.values()
        )
        for feature in dataset["auditory_features"]
    }
    assert all(len(segment["features"]) > 1 for segment in segments.values())
    assert min(segment_uses.values()) > 1
    assert min(feature_uses.values()) > 1
    assert len({tuple(sorted(row["segments"])) for row in pseudowords}) == 1
    for pseudoword in pseudowords:
        assert len(pseudoword["segments"]) == 3
        assert pseudoword["controls"]["reversed"] == list(
            reversed(pseudoword["segments"])
        )
        assert pseudoword["controls"]["permuted"] not in (
            pseudoword["segments"],
            pseudoword["controls"]["reversed"],
        )
        assert len(set(pseudoword["controls"]["repeated_segment"])) == 1


def test_acquisition_pairings_balance_success_and_mismatch(tmp_path):
    dataset = read(execute(DEFINITION, tmp_path), "dataset.json")

    pairings = dataset["pairings"]
    correct = [pairing for pairing in pairings if pairing["kind"] == "correct"]
    mismatched = [
        pairing for pairing in pairings if pairing["kind"] == "mismatched"
    ]
    assert {pairing["epoch"] for pairing in pairings} == {1}
    assert len(correct) == 32
    assert len(mismatched) == 32
    assert {pairing["success_signal"] for pairing in correct} == {1.0}
    assert {pairing["success_signal"] for pairing in mismatched} == {0.0}
    for category in dataset["categories"]:
        category_id = category["id"]
        assert sum(row["category_id"] == category_id for row in correct) == 8
        assert sum(row["category_id"] == category_id for row in mismatched) == 8


def test_generation_is_deterministic_from_the_declared_seed():
    first = generate_domain(31415)
    second = generate_domain(31415)

    assert first == second
    assert first != generate_domain(31416)


def test_final_held_out_data_cannot_influence_generation_decisions():
    first = generate_domain(2718, final_held_out_seed=11)
    second = generate_domain(2718, final_held_out_seed=12)

    for first_category, second_category in zip(
        first["categories"], second["categories"], strict=True
    ):
        assert first_category["prototype"] == second_category["prototype"]
        assert (
            first_category["splits"]["acquisition"]
            == second_category["splits"]["acquisition"]
        )
        assert (
            first_category["splits"]["basin_estimation"]
            == second_category["splits"]["basin_estimation"]
        )
    assert first["pseudowords"] == second["pseudowords"]
    assert first["pairings"] == second["pairings"]
    assert [
        category["splits"]["final_held_out"] for category in first["categories"]
    ] != [
        category["splits"]["final_held_out"] for category in second["categories"]
    ]


def test_a_pseudoword_without_three_ordered_segments_is_rejected():
    candidate = generate_domain(7)
    candidate["pseudowords"][0]["segments"] = ["segment-1", "segment-2"]

    with pytest.raises(DomainValidationError) as error:
        validate_domain(candidate)

    assert "pseudowords_have_three_ordered_segments" in error.value.failed_checks


def test_a_segment_without_distributed_features_is_rejected():
    candidate = generate_domain(8)
    candidate["auditory_segments"][0]["features"] = ["auditory-feature-1"]

    with pytest.raises(DomainValidationError) as error:
        validate_domain(candidate)

    assert "auditory_segments_are_distributed" in error.value.failed_checks


def test_a_segment_or_feature_unique_to_one_category_is_rejected():
    candidate = generate_domain(9)
    candidate["pseudowords"][0]["segments"][0] = "unique-segment"
    candidate["auditory_segments"][0]["features"][0] = "unique-feature"

    with pytest.raises(DomainValidationError) as error:
        validate_domain(candidate)

    assert "auditory_features_and_segments_are_reused" in error.value.failed_checks


def test_missing_pseudoword_controls_are_rejected():
    candidate = generate_domain(10)
    candidate["pseudowords"][0]["controls"]["reversed"] = candidate[
        "pseudowords"
    ][0]["segments"]

    with pytest.raises(DomainValidationError) as error:
        validate_domain(candidate)

    assert "pseudoword_controls_are_complete" in error.value.failed_checks


def test_unbalanced_pairings_are_rejected():
    candidate = generate_domain(11)
    candidate["pairings"].pop()

    with pytest.raises(DomainValidationError) as error:
        validate_domain(candidate)

    assert "acquisition_pairings_are_balanced" in error.value.failed_checks
