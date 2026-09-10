"""Generate and validate the synthetic lexical-grounding domain."""

from __future__ import annotations

import hashlib
import itertools
import random
from collections import Counter
from collections.abc import Iterable


DIMENSIONS = {
    "contour": ("angular", "rounded", "lobed", "tapered"),
    "surface": ("matte", "glossy", "striped", "mottled"),
    "marking": ("banded", "spotted", "ringed", "plain"),
}
PROTOTYPES = (
    ("angular", "matte", "banded"),
    ("angular", "glossy", "spotted"),
    ("rounded", "matte", "spotted"),
    ("rounded", "glossy", "banded"),
)
CATEGORY_IDS = ("category-1", "category-2", "category-3", "category-4")
CATEGORY_RELATIONS = (
    (0, 1, 2, 3),
    (0, 2, 3, 1),
    (2, 1, 3, 0),
    (0, 3, 1, 2),
)
AUDITORY_SEGMENTS = {
    "segment-1": ("auditory-feature-1", "auditory-feature-2"),
    "segment-2": ("auditory-feature-2", "auditory-feature-3"),
    "segment-3": ("auditory-feature-1", "auditory-feature-3"),
}
PSEUDOWORD_SEGMENTS = (
    ("segment-1", "segment-2", "segment-3"),
    ("segment-1", "segment-3", "segment-2"),
    ("segment-2", "segment-1", "segment-3"),
    ("segment-2", "segment-3", "segment-1"),
)


class DomainValidationError(ValueError):
    """The generated domain violates one or more scientific constraints."""

    def __init__(self, failed_checks: Iterable[str]):
        self.failed_checks = tuple(failed_checks)
        super().__init__("invalid synthetic domain: " + ", ".join(self.failed_checks))


def _derived_seed(seed: int, *parts: str) -> int:
    material = ":".join((str(seed), *parts)).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _properties(values: tuple[str, ...]) -> list[dict[str, str]]:
    return [
        {"dimension": dimension, "value": value}
        for dimension, value in zip(DIMENSIONS, values, strict=True)
    ]


def _signature(instance: dict) -> tuple[str, ...]:
    return tuple(property_["value"] for property_ in instance["properties"])


def _instances(
    category_id: str,
    prototype: tuple[str, ...],
    relation: tuple[int, ...],
    seed: int,
    final_held_out_seed: int,
) -> dict[str, list[dict]]:
    dimension_values = tuple(DIMENSIONS.values())
    candidates = [
        (
            dimension_values[0][first],
            dimension_values[1][second],
            dimension_values[2][(relation[first] + second) % 4],
        )
        for first, second in itertools.product(range(4), repeat=2)
    ]
    random.Random(_derived_seed(seed, category_id, "development")).shuffle(candidates)
    development = candidates[:12]
    final_held_out = candidates[12:]
    random.Random(
        _derived_seed(final_held_out_seed, category_id, "final-held-out")
    ).shuffle(final_held_out)

    splits = {
        "acquisition": development[:8],
        "basin_estimation": development[8:],
        "final_held_out": final_held_out,
    }
    return {
        split: [
            {
                "id": f"{category_id}-{split}-{index}",
                "properties": _properties(values),
                "prototype_distance": sum(
                    left != right
                    for left, right in zip(values, prototype, strict=True)
                ),
            }
            for index, values in enumerate(values_by_split, start=1)
        ]
        for split, values_by_split in splits.items()
    }


def _pseudowords() -> list[dict]:
    return [
        {
            "id": f"pseudoword-{index}",
            "segments": list(segments),
            "controls": {
                "reversed": list(reversed(segments)),
                "permuted": [segments[1], segments[2], segments[0]],
                "repeated_segment": [segments[1]] * 3,
            },
        }
        for index, segments in enumerate(PSEUDOWORD_SEGMENTS, start=1)
    ]


def _pairings(categories: list[dict], seed: int) -> list[dict]:
    pairings = []
    for category_index, category in enumerate(categories):
        correct_pseudoword = category["pseudoword_id"]
        mismatched_pseudoword = categories[
            (category_index + 1) % len(categories)
        ]["pseudoword_id"]
        for instance in category["splits"]["acquisition"]:
            for kind, pseudoword, success_signal in (
                ("correct", correct_pseudoword, 1.0),
                ("mismatched", mismatched_pseudoword, 0.0),
            ):
                pairings.append(
                    {
                        "id": f"pairing-{len(pairings) + 1}",
                        "split": "acquisition",
                        "epoch": 1,
                        "category_id": category["id"],
                        "visual_instance_id": instance["id"],
                        "pseudoword_id": pseudoword,
                        "kind": kind,
                        "success_signal": success_signal,
                    }
                )
    random.Random(_derived_seed(seed, "pairing-order")).shuffle(pairings)
    return pairings


def _prototype_property_counts(dataset: dict) -> Counter[tuple[str, str]]:
    return Counter(
        (property_["dimension"], property_["value"])
        for category in dataset["categories"]
        for property_ in category["prototype"]["properties"]
    )


def _category_property_counts(category: dict) -> Counter[tuple[str, str]]:
    return Counter(
        (property_["dimension"], property_["value"])
        for instances in category["splits"].values()
        for instance in instances
        for property_ in instance["properties"]
    )


def evaluate_constraints(dataset: dict) -> list[dict]:
    """Return every visual constraint and its observed result."""
    categories = dataset["categories"]
    property_counts = _prototype_property_counts(dataset)
    category_property_counts = [
        _category_property_counts(category) for category in categories
    ]
    generated_properties = set().union(*category_property_counts)
    marginal_frequencies = {
        property_: [counts[property_] for counts in category_property_counts]
        for property_ in generated_properties
    }
    prototype_sets = [
        {
            (property_["dimension"], property_["value"])
            for property_ in category["prototype"]["properties"]
        }
        for category in categories
    ]
    acquisition_and_held_out_overlap = sum(
        len(
            {_signature(row) for row in category["splits"]["acquisition"]}
            & {_signature(row) for row in category["splits"]["final_held_out"]}
        )
        for category in categories
    )
    distances_by_category = {
        category["id"]: {
            sum(
                property_["value"] != prototype_property["value"]
                for property_, prototype_property in zip(
                    instance["properties"],
                    category["prototype"]["properties"],
                    strict=True,
                )
            )
            for split in category["splits"].values()
            for instance in split
        }
        for category in categories
    }
    segment_categories: dict[str, set[str]] = {
        segment["id"]: set() for segment in dataset["auditory_segments"]
    }
    feature_categories: dict[str, set[str]] = {
        feature: set() for feature in dataset["auditory_features"]
    }
    segment_features = {
        segment["id"]: segment["features"]
        for segment in dataset["auditory_segments"]
    }
    for pseudoword in dataset["pseudowords"]:
        for segment in pseudoword["segments"]:
            segment_categories.setdefault(segment, set()).add(pseudoword["id"])
            for feature in segment_features.get(segment, []):
                feature_categories.setdefault(feature, set()).add(pseudoword["id"])
    controls_are_complete = all(
        pseudoword["controls"]["reversed"]
        == list(reversed(pseudoword["segments"]))
        and pseudoword["controls"]["permuted"]
        not in (
            pseudoword["segments"],
            pseudoword["controls"]["reversed"],
        )
        and len(set(pseudoword["controls"]["repeated_segment"])) == 1
        for pseudoword in dataset["pseudowords"]
    )
    pairing_counts = Counter(pairing["kind"] for pairing in dataset["pairings"])
    category_pairing_counts = Counter(
        (pairing["category_id"], pairing["kind"])
        for pairing in dataset["pairings"]
    )
    pseudoword_pairing_counts = Counter(
        (pairing["pseudoword_id"], pairing["kind"])
        for pairing in dataset["pairings"]
    )
    pairings_are_balanced = (
        pairing_counts["correct"] == pairing_counts["mismatched"] == 32
        and set(category_pairing_counts.values()) == {8}
        and set(pseudoword_pairing_counts.values()) == {8}
        and all(
            pairing["success_signal"]
            == (1.0 if pairing["kind"] == "correct" else 0.0)
            for pairing in dataset["pairings"]
        )
    )

    return [
        {
            "name": "no_category_unique_prototype_property",
            "passed": bool(property_counts) and min(property_counts.values()) > 1,
            "evidence": {"minimum_category_count": min(property_counts.values(), default=0)},
        },
        {
            "name": "balanced_visual_property_marginals",
            "passed": all(
                len(set(frequencies)) == 1
                for frequencies in marginal_frequencies.values()
            ),
            "evidence": {
                "frequencies_by_category": sorted(marginal_frequencies.values())
            },
        },
        {
            "name": "complete_pairwise_prototype_overlap",
            "passed": all(
                prototype_sets[left] & prototype_sets[right]
                for left in range(len(prototype_sets))
                for right in range(left + 1, len(prototype_sets))
            ),
            "evidence": {"category_pairs": 6},
        },
        {
            "name": "prototype_property_shared_by_exactly_two_categories",
            "passed": any(count == 2 for count in property_counts.values()),
            "evidence": {
                "property_count": sum(count == 2 for count in property_counts.values())
            },
        },
        {
            "name": "acquisition_and_final_held_out_are_disjoint",
            "passed": acquisition_and_held_out_overlap == 0,
            "evidence": {"overlap_count": acquisition_and_held_out_overlap},
        },
        {
            "name": "prototype_distance_varies",
            "passed": all(
                len(distances) > 1 for distances in distances_by_category.values()
            ),
            "evidence": {
                category: sorted(distances)
                for category, distances in distances_by_category.items()
            },
        },
        {
            "name": "pseudowords_have_three_ordered_segments",
            "passed": len({tuple(row["segments"]) for row in dataset["pseudowords"]})
            == len(dataset["categories"])
            and len(
                {
                    tuple(sorted(row["segments"]))
                    for row in dataset["pseudowords"]
                }
            )
            == 1
            and all(len(row["segments"]) == 3 for row in dataset["pseudowords"]),
            "evidence": {"pseudoword_count": len(dataset["pseudowords"])},
        },
        {
            "name": "auditory_segments_are_distributed",
            "passed": all(
                len(segment["features"]) > 1
                for segment in dataset["auditory_segments"]
            ),
            "evidence": {
                "minimum_features": min(
                    (
                        len(segment["features"])
                        for segment in dataset["auditory_segments"]
                    ),
                    default=0,
                )
            },
        },
        {
            "name": "auditory_features_and_segments_are_reused",
            "passed": min(
                (len(categories) for categories in segment_categories.values()),
                default=0,
            )
            > 1
            and min(
                (len(categories) for categories in feature_categories.values()),
                default=0,
            )
            > 1,
            "evidence": {
                "minimum_segment_categories": min(
                    (len(categories) for categories in segment_categories.values()),
                    default=0,
                ),
                "minimum_feature_categories": min(
                    (len(categories) for categories in feature_categories.values()),
                    default=0,
                ),
            },
        },
        {
            "name": "pseudoword_controls_are_complete",
            "passed": controls_are_complete,
            "evidence": {"controls_per_pseudoword": 3},
        },
        {
            "name": "acquisition_pairings_are_balanced",
            "passed": pairings_are_balanced,
            "evidence": dict(pairing_counts),
        },
    ]


def validate_domain(dataset: dict) -> list[dict]:
    """Reject a candidate domain rather than repairing a failed constraint."""
    checks = evaluate_constraints(dataset)
    failed = [check["name"] for check in checks if not check["passed"]]
    if failed:
        raise DomainValidationError(failed)
    return checks


def generate_domain(seed: int, *, final_held_out_seed: int | None = None) -> dict:
    """Return a validated deterministic domain generated from ``seed``.

    Development data is allocated before final held-out data and from a separate random
    stream. The optional held-out seed exists to verify that evaluation data cannot
    influence generation decisions; experiment definitions use the declared master seed.
    """
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    held_out_seed = (
        _derived_seed(seed, "final-held-out")
        if final_held_out_seed is None
        else final_held_out_seed
    )
    categories = [
        {
            "id": category_id,
            "prototype": {"properties": _properties(prototype)},
            "pseudoword_id": f"pseudoword-{index}",
            "splits": _instances(
                category_id,
                prototype,
                relation,
                seed,
                held_out_seed,
            ),
        }
        for index, (category_id, prototype, relation) in enumerate(
            zip(CATEGORY_IDS, PROTOTYPES, CATEGORY_RELATIONS, strict=True),
            start=1,
        )
    ]

    dataset = {
        "contract": "ncl-synthetic-domain-v1",
        "seed": seed,
        "generation": {
            "development_seed": seed,
            "final_held_out_seed": held_out_seed,
            "generation_decision_splits": ["acquisition", "basin_estimation"],
        },
        "visual_property_dimensions": [
            {"id": dimension, "values": list(values)}
            for dimension, values in DIMENSIONS.items()
        ],
        "auditory_features": sorted(
            {
                feature
                for features in AUDITORY_SEGMENTS.values()
                for feature in features
            }
        ),
        "auditory_segments": [
            {"id": segment, "features": list(features)}
            for segment, features in AUDITORY_SEGMENTS.items()
        ],
        "pseudowords": _pseudowords(),
        "categories": categories,
        "pairings": _pairings(categories, seed),
    }
    dataset["constraint_checks"] = validate_domain(dataset)
    return dataset
