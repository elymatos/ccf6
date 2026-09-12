"""Validation for complete, rerun-free Functional Web artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


REQUIRED_CORTICAL_CIRCUIT_FILES = (
    "definition.json",
    "manifest.json",
    "dataset.json",
    "topology.npz",
    "topology.json",
    "activity.npz",
    "activity.json",
    "summary.json",
)


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


def validate_cortical_circuit_artifact(path: str | Path) -> dict:
    """Validate a detailed cortical-circuit artifact without simulating it."""
    root = Path(path)
    if not root.is_dir():
        raise ValueError("artifact path must be a directory")
    missing = [
        name for name in REQUIRED_CORTICAL_CIRCUIT_FILES if not (root / name).is_file()
    ]
    if missing:
        raise ValueError(f"artifact is missing required files {missing}")

    decoded = {}
    for name in (
        "definition.json",
        "manifest.json",
        "dataset.json",
        "topology.json",
        "activity.json",
        "summary.json",
    ):
        try:
            decoded[name] = json.loads((root / name).read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"{name} is not readable JSON") from error
        if not isinstance(decoded[name], dict):
            raise ValueError(f"{name} must contain a JSON object")

    manifest = decoded["manifest.json"]
    if manifest.get("contract") != "ncl-cortical-circuit-v1":
        raise ValueError("manifest does not declare ncl-cortical-circuit-v1")
    if manifest.get("kind") != "cortical_process_suite":
        raise ValueError("manifest does not declare a cortical process suite")
    if tuple(manifest.get("files", ())) != REQUIRED_CORTICAL_CIRCUIT_FILES:
        raise ValueError("manifest file inventory is not the cortical circuit contract")
    expected_checksums = set(REQUIRED_CORTICAL_CIRCUIT_FILES) - {"manifest.json"}
    if set(manifest.get("checksums", {})) != expected_checksums:
        raise ValueError("manifest checksum inventory is incomplete")
    for name, expected in manifest["checksums"].items():
        with (root / name).open("rb") as artifact:
            observed = hashlib.file_digest(artifact, "sha256").hexdigest()
        if observed != expected:
            raise ValueError(f"{name} does not match its recorded checksum")

    definition = decoded["definition.json"]
    declarations = definition.get("processes")
    if definition.get("kind") != "cortical_process_suite" or not isinstance(
        declarations, list
    ) or not declarations:
        raise ValueError("definition does not declare cortical processes")
    process_ids = [declaration.get("id") for declaration in declarations]
    if any(not isinstance(identifier, str) or not identifier for identifier in process_ids):
        raise ValueError("every cortical process requires an identity")
    if len(process_ids) != len(set(process_ids)):
        raise ValueError("cortical process identities must be unique")
    if decoded["dataset.json"].get("process_inventory") != process_ids:
        raise ValueError("dataset process inventory does not match the definition")
    activity = decoded["activity.json"]
    if list(activity.get("processes", {})) != process_ids:
        raise ValueError("activity process inventory does not match the definition")

    topology = decoded["topology.json"]
    populations = topology.get("populations")
    pathways = topology.get("pathways")
    if not isinstance(populations, dict) or not populations:
        raise ValueError("topology has no cortical populations")
    if not isinstance(pathways, list) or not pathways:
        raise ValueError("topology has no cortical pathways")
    population_labels = list(populations)
    if activity.get("labels") != population_labels:
        raise ValueError("activity labels do not match cortical topology")

    try:
        with np.load(root / "topology.npz", allow_pickle=False) as archive:
            required_topology = {
                "population_labels",
                "pathway_labels",
                "pathway_sources",
                "pathway_targets",
                "pathway_effects",
                "pathway_routes",
                "base_strengths",
            }
            if set(archive.files) != required_topology:
                raise ValueError("topology.npz array inventory is incomplete")
            if archive["population_labels"].shape != (len(populations),):
                raise ValueError("topology population array has an invalid shape")
            if archive["pathway_labels"].shape != (len(pathways),):
                raise ValueError("topology pathway array has an invalid shape")
        with np.load(root / "activity.npz", allow_pickle=False) as archive:
            if "labels" not in archive.files:
                raise ValueError("activity.npz has no population labels")
            for declaration in declarations:
                identifier = declaration["id"]
                trajectory_name = f"{identifier}.trajectory"
                flux_name = f"{identifier}.pathway_flux_trajectory"
                if trajectory_name not in archive.files or flux_name not in archive.files:
                    raise ValueError(f"activity.npz is missing {identifier} trajectories")
                expected_ticks = int(declaration["ticks"]) + 1
                if archive[trajectory_name].shape != (
                    expected_ticks,
                    len(populations),
                ):
                    raise ValueError(f"{identifier} activity trajectory has an invalid shape")
                if archive[flux_name].shape != (expected_ticks, len(pathways)):
                    raise ValueError(f"{identifier} pathway trajectory has an invalid shape")
    except (OSError, ValueError) as error:
        message = str(error)
        if message.startswith(("topology", "activity")) or any(
            identifier in message for identifier in process_ids
        ):
            raise
        raise ValueError("cortical numerical archives are not readable") from error

    return {
        "files": list(REQUIRED_CORTICAL_CIRCUIT_FILES),
        "populations": len(populations),
        "pathways": len(pathways),
        "processes": len(process_ids),
    }
