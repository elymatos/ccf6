"""Validation for complete, rerun-free Functional Web artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


REQUIRED_FUNCTIONAL_WEB_FILES = (
    "definition.json",
    "manifest.json",
    "dataset.json",
    "topology.npz",
    "presentations.jsonl",
    "learning.npz",
    "activity.npz",
    "basins.json",
    "webs.json",
    "cardinals.json",
    "metrics.json",
    "aggregate.json",
    "summary.json",
)


def validate_functional_web_artifact(path: str | Path) -> dict:
    """Read and validate every normative file without executing the experiment."""
    root = Path(path)
    if not root.is_dir():
        raise ValueError("artifact path must be a directory")
    missing = [name for name in REQUIRED_FUNCTIONAL_WEB_FILES if not (root / name).is_file()]
    if missing:
        raise ValueError(f"artifact is missing required files {missing}")

    json_files = (
        "definition.json",
        "manifest.json",
        "dataset.json",
        "basins.json",
        "webs.json",
        "cardinals.json",
        "metrics.json",
        "aggregate.json",
        "summary.json",
    )
    decoded = {}
    for name in json_files:
        try:
            decoded[name] = json.loads((root / name).read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"{name} is not readable JSON") from error
        if not isinstance(decoded[name], dict):
            raise ValueError(f"{name} must contain a JSON object")

    manifest = decoded["manifest.json"]
    if manifest.get("contract") != "ncl-functional-web-v1":
        raise ValueError("manifest does not declare ncl-functional-web-v1")
    if tuple(manifest.get("files", ())) != REQUIRED_FUNCTIONAL_WEB_FILES:
        raise ValueError("manifest file inventory is not the complete contract")
    for field in ("digest", "software_version", "kind", "status"):
        if field not in manifest:
            raise ValueError(f"manifest is missing {field}")
    expected_checksums = set(REQUIRED_FUNCTIONAL_WEB_FILES) - {"manifest.json"}
    if set(manifest.get("checksums", {})) != expected_checksums:
        raise ValueError("manifest checksum inventory is incomplete")
    for name, expected in manifest["checksums"].items():
        with (root / name).open("rb") as artifact:
            observed = hashlib.file_digest(artifact, "sha256").hexdigest()
        if observed != expected:
            raise ValueError(f"{name} does not match its recorded checksum")

    presentations = []
    try:
        for number, line in enumerate((root / "presentations.jsonl").read_text().splitlines(), 1):
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(
                    f"presentations.jsonl line {number} must contain an object"
                )
            presentations.append(row)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("presentations.jsonl is not readable JSON Lines") from error
    if not presentations:
        raise ValueError("presentations.jsonl must not be empty")

    definition = decoded["definition.json"]
    seeds = definition.get("replication", {}).get("seed_inventory")
    if (
        definition.get("kind") != "replicated_milestone"
        or not isinstance(seeds, list)
        or not seeds
    ):
        raise ValueError("definition does not declare the replicated seed inventory")
    if manifest.get("kind") != "replicated_milestone" or manifest.get("status") != "completed":
        raise ValueError("manifest kind or completion status is invalid")
    if manifest.get("parameters") != definition["replication"]:
        raise ValueError("manifest parameters do not match the definition")
    if manifest.get("stimuli") != {
        "seeds": seeds,
        "arms": ["trained", "untrained", "shuffled"],
    }:
        raise ValueError("manifest arm or seed inventory does not match the definition")
    if decoded["metrics.json"].get("seed_inventory") != seeds:
        raise ValueError("metrics seed inventory does not match the definition")
    rows = decoded["metrics.json"].get("seeds")
    if not isinstance(rows, list) or [row.get("seed") for row in rows] != seeds:
        raise ValueError("metrics must contain one ordered row per declared seed")
    expected_seed_keys = {str(seed) for seed in seeds}
    for name in ("dataset.json", "basins.json", "webs.json", "cardinals.json"):
        if set(decoded[name].get("seeds", {})) != expected_seed_keys:
            raise ValueError(f"{name} does not contain every declared seed")
    if {row.get("seed") for row in presentations} != set(seeds):
        raise ValueError("presentations.jsonl does not contain every declared seed")

    arrays = {}
    required_arrays = {
        "topology.npz": ("population_ids", "thresholds"),
        "learning.npz": (
            "ascending_eligibility",
            "descending_eligibility",
            "pre_ascending_weights",
            "post_ascending_weights",
            "pre_descending_weights",
            "post_descending_weights",
            "pre_thresholds",
            "post_thresholds",
            "pre_entrenchment",
            "post_entrenchment",
            "post_contributor_counts",
            "recruited",
        ),
        "activity.npz": (
            "completion_initial_output",
            "completion_settled_output",
            "lexical_visual_trajectory",
            "lexical_correct_trajectory",
            "lexical_control_trajectories",
        ),
    }
    for name in ("topology.npz", "learning.npz", "activity.npz"):
        try:
            with np.load(root / name, allow_pickle=False) as archive:
                if not archive.files:
                    raise ValueError(f"{name} must contain arrays")
                arrays[name] = len(archive.files)
                for field in archive.files:
                    np.asarray(archive[field])
                fields = set(archive.files)
                for seed in seeds:
                    for field in required_arrays[name]:
                        if f"seed_{seed}__{field}" not in fields:
                            raise ValueError(
                                f"{name} is missing {field} for seed {seed}"
                            )
        except (OSError, ValueError) as error:
            if isinstance(error, ValueError) and str(error).startswith(name):
                raise
            raise ValueError(f"{name} is not a readable numerical archive") from error

    aggregate = decoded["aggregate.json"]
    if not isinstance(aggregate.get("effects"), dict) or not isinstance(
        aggregate.get("criteria"), dict
    ) or not isinstance(aggregate.get("verdict"), bool):
        raise ValueError("aggregate.json is missing effects, criteria, or verdict")
    summary_verdict = decoded["summary.json"].get("milestone_verdict")
    if summary_verdict is not aggregate["verdict"]:
        raise ValueError("summary and aggregate verdicts disagree")

    return {
        "files": list(REQUIRED_FUNCTIONAL_WEB_FILES),
        "presentations": len(presentations),
        "arrays": arrays,
        "seed_count": len(decoded["metrics.json"].get("seeds", [])),
        "verdict": decoded["aggregate.json"].get("verdict"),
    }
