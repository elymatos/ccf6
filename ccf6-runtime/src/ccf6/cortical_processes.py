"""Process-level simulations over the explicit laminar cortical circuit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from ccf6.cortical_circuit import ROUTE_FAMILIES, CorticalCircuit, TickResult


PROCESS_ROUTES = {
    "All": None,
    "Input": frozenset({"Input", "Pv"}),
    "Flow": frozenset({"Flow"}),
    "Ascend": frozenset({"Ascend"}),
    "Topdown": frozenset({"Topdown"}),
    "Lateral": frozenset({"Lateral", "Pv", "Som"}),
    "Pv": frozenset({"Input", "Pv"}),
    "Som": frozenset({"Som", "Topdown"}),
    "Vip": frozenset({"Vip", "Som", "Topdown"}),
    "Integration": frozenset({"Input", "Flow", "Pv", "Som", "Lateral", "Topdown"}),
    "Predictive": frozenset({"Input", "Ascend", "Topdown", "Som", "Vip", "Pv"}),
    "Competition": frozenset({"Input", "Flow", "Lateral", "Pv", "Som"}),
    "Gain": frozenset({"Input", "Flow", "Pv"}),
    "Behavior": frozenset({"Input", "Flow", "Ascend", "Topdown", "Pv", "Som", "Vip"}),
    "Attention": frozenset({"Topdown", "Som", "Vip"}),
    "Arousal": frozenset({"Input", "Flow", "Pv"}),
    "Novelty": frozenset({"Input", "Flow", "Ascend", "Topdown", "Vip"}),
    "Reward": frozenset({"Topdown", "Som", "Vip"}),
    "Sustained": frozenset({"Flow", "Pv", "Som"}),
    "Hebbian": frozenset({"Flow"}),
}


@dataclass(frozen=True)
class ProcessResult:
    process: str
    active_routes: tuple[str, ...]
    ticks: int
    labels: tuple[str, ...]
    trajectory: np.ndarray
    pathway_labels: tuple[str, ...]
    pathway_flux_trajectory: np.ndarray
    activity: dict[str, float]
    pathway_flux: dict[str, float]
    final_drives: dict[str, dict[str, float]]
    learning: dict | None


def run_cortical_process(
    circuit_definition: dict,
    *,
    process: str,
    ticks: int,
    external_drives: dict[str, float],
    disabled_routes: Iterable[str] = (),
    drive_ticks: int | None = None,
    success_signal: float | None = None,
    presentation_id: str = "process-presentation",
) -> ProcessResult:
    """Run one declared process while retaining complete population trajectories."""
    if process not in PROCESS_ROUTES:
        raise ValueError(f"unknown cortical process {process!r}")
    if isinstance(ticks, bool) or not isinstance(ticks, int) or ticks < 1:
        raise ValueError("cortical process ticks must be a positive integer")
    if drive_ticks is not None and (
        isinstance(drive_ticks, bool) or not isinstance(drive_ticks, int) or not 0 <= drive_ticks <= ticks
    ):
        raise ValueError("cortical process drive_ticks must be between zero and ticks")
    if success_signal is not None and process != "Hebbian":
        raise ValueError("Success Signal is only valid for the Hebbian process")
    circuit = CorticalCircuit.from_definition(circuit_definition)
    active_routes = PROCESS_ROUTES[process]
    labels = tuple(circuit.populations)
    pathway_labels = tuple(circuit.pathways)
    trajectory = [circuit.activity_vector()]
    pathway_flux_trajectory = [np.zeros(len(pathway_labels), dtype=np.float64)]
    tick_result: TickResult | None = None
    for tick_index in range(ticks):
        applied_drives = (
            external_drives
            if drive_ticks is None or tick_index < drive_ticks
            else {}
        )
        tick_result = circuit.tick(
            applied_drives,
            active_routes=None if active_routes is None else set(active_routes),
            disabled_routes=disabled_routes,
        )
        trajectory.append(circuit.activity_vector())
        pathway_flux_trajectory.append(
            np.asarray(
                [tick_result.pathway_flux[label] for label in pathway_labels],
                dtype=np.float64,
            )
        )
    assert tick_result is not None
    learning = None
    if success_signal is not None:
        before = {
            identifier: circuit.pathway_state(identifier)
            for identifier in circuit.pathways
        }
        outcome = circuit.apply_success_signal(
            success_signal,
            presentation_id=presentation_id,
        )
        learning = {
            "success_signal": outcome.success_signal,
            "adaptation_applied": outcome.adaptation_applied,
            "changed_pathways": {
                identifier: {
                    "before": before[identifier],
                    "after": circuit.pathway_state(identifier),
                }
                for identifier in outcome.changed_pathways
            },
        }
    selected = set(ROUTE_FAMILIES) if active_routes is None else set(active_routes)
    selected -= set(disabled_routes)
    return ProcessResult(
        process=process,
        active_routes=tuple(sorted(selected)),
        ticks=ticks,
        labels=labels,
        trajectory=np.stack(trajectory),
        pathway_labels=pathway_labels,
        pathway_flux_trajectory=np.stack(pathway_flux_trajectory),
        activity=tick_result.activity,
        pathway_flux=tick_result.pathway_flux,
        final_drives=tick_result.drives,
        learning=learning,
    )


def run_cortical_process_suite(definition: dict) -> dict:
    """Run independent process trials and return artifact-ready evidence."""
    required = {"seed", "circuit", "processes"}
    missing = required - definition.keys()
    if missing:
        raise ValueError(f"cortical process suite missing {sorted(missing)}")
    if not isinstance(definition["processes"], list) or not definition["processes"]:
        raise ValueError("cortical process suite requires at least one process")
    if int(definition["seed"]) != int(definition["circuit"].get("seed", -1)):
        raise ValueError("experiment and cortical circuit seeds must match")

    circuit = CorticalCircuit.from_definition(definition["circuit"])
    topology = circuit.topology_snapshot()
    labels = tuple(circuit.populations)
    label_index = {label: index for index, label in enumerate(labels)}
    arrays: dict[str, np.ndarray] = {"labels": np.asarray(labels)}
    process_evidence: dict[str, dict] = {}
    identifiers: set[str] = set()
    controls = 0
    release_changes = 0
    receptiveness_changes = 0
    structural_changes = 0

    for declaration in definition["processes"]:
        required_process = {"id", "process", "ticks", "external_drives"}
        missing_process = required_process - declaration.keys()
        if missing_process:
            raise ValueError(
                f"cortical process declaration missing {sorted(missing_process)}"
            )
        identifier = declaration["id"]
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("cortical process id must be a non-empty string")
        if identifier in identifiers:
            raise ValueError(f"duplicate cortical process id {identifier!r}")
        identifiers.add(identifier)
        result = run_cortical_process(
            definition["circuit"],
            process=declaration["process"],
            ticks=declaration["ticks"],
            external_drives=declaration["external_drives"],
            disabled_routes=declaration.get("disabled_routes", ()),
            drive_ticks=declaration.get("drive_ticks"),
            success_signal=declaration.get("success_signal"),
            presentation_id=f"{identifier}-presentation",
        )
        arrays[f"{identifier}.trajectory"] = result.trajectory
        arrays[f"{identifier}.pathway_flux_trajectory"] = (
            result.pathway_flux_trajectory
        )
        evidence = _process_evidence(declaration, result)

        control_routes = declaration.get("control_disabled_routes")
        if control_routes:
            control = run_cortical_process(
                definition["circuit"],
                process=declaration["process"],
                ticks=declaration["ticks"],
                external_drives=declaration["external_drives"],
                disabled_routes=control_routes,
                drive_ticks=declaration.get("drive_ticks"),
            )
            arrays[f"{identifier}.control_trajectory"] = control.trajectory
            arrays[f"{identifier}.control_pathway_flux_trajectory"] = (
                control.pathway_flux_trajectory
            )
            activity_difference = {
                label: result.activity[label] - control.activity[label]
                for label in labels
            }
            evidence["control"] = {
                "disabled_routes": list(control_routes),
                "trajectory": control.trajectory.tolist(),
                "pathway_flux_trajectory": control.pathway_flux_trajectory.tolist(),
                "final_activity": control.activity,
                "activity_difference": activity_difference,
            }
            evidence["measurements"]["control_maximum_activity_difference"] = max(
                abs(value) for value in activity_difference.values()
            )
            evidence["measurements"]["control_activity_difference_norm"] = float(
                np.linalg.norm(np.asarray(list(activity_difference.values())))
            )
            controls += 1

        if result.learning is not None:
            for change in result.learning["changed_pathways"].values():
                before = change["before"]
                after = change["after"]
                release_changes += after["release_facilitation"] > before["release_facilitation"]
                receptiveness_changes += (
                    after["postsynaptic_receptiveness"]
                    > before["postsynaptic_receptiveness"]
                )
                structural_changes += (
                    after["structural_contacts"] > before["structural_contacts"]
                )
        process_evidence[identifier] = evidence

    pathways = list(circuit.pathways.values())
    topology_arrays = {
        "population_labels": np.asarray(labels),
        "pathway_labels": np.asarray([pathway.identifier for pathway in pathways]),
        "pathway_sources": np.asarray(
            [label_index[pathway.source] for pathway in pathways], dtype=np.int64
        ),
        "pathway_targets": np.asarray(
            [label_index[pathway.target] for pathway in pathways], dtype=np.int64
        ),
        "pathway_effects": np.asarray([pathway.effect for pathway in pathways]),
        "pathway_routes": np.asarray([pathway.route for pathway in pathways]),
        "base_strengths": np.asarray(
            [pathway.base_strength for pathway in pathways], dtype=np.float64
        ),
    }
    return {
        "contract": "ncl-cortical-circuit-v1",
        "dataset": {
            "schema": "ncl-cortical-process-suite-v1",
            "seed": int(definition["seed"]),
            "process_inventory": list(process_evidence),
        },
        "topology": topology,
        "topology_arrays": topology_arrays,
        "activity": {"labels": list(labels), "processes": process_evidence},
        "activity_arrays": arrays,
        "summary": {
            "circuit": {
                "levels": {key: len(value) for key, value in circuit.hierarchy.items()},
                "columns": sum(len(value) for value in circuit.hierarchy.values()),
                "populations": len(circuit.populations),
                "pathways": len(circuit.pathways),
            },
            "processes": {
                "total": len(process_evidence),
                "with_controls": controls,
                "inventory": list(process_evidence),
            },
            "learning": {
                "release_facilitation_changes": release_changes,
                "postsynaptic_receptiveness_changes": receptiveness_changes,
                "structural_growth_changes": structural_changes,
                "stdp_enabled": False,
            },
        },
        "stimuli": {
            identifier: evidence["external_drives"]
            for identifier, evidence in process_evidence.items()
        },
        "parameters": {
            "hierarchy": definition["circuit"]["hierarchy"],
            "pathway_initialization": definition["circuit"]["pathway_initialization"],
            "dynamics": definition["circuit"]["dynamics"],
            "plasticity": definition["circuit"]["plasticity"],
        },
    }


def _process_evidence(declaration: dict, result: ProcessResult) -> dict:
    return {
        "process": result.process,
        "active_routes": list(result.active_routes),
        "ticks": result.ticks,
        "drive_ticks": declaration.get("drive_ticks", result.ticks),
        "external_drives": dict(declaration["external_drives"]),
        "trajectory": result.trajectory.tolist(),
        "pathway_labels": list(result.pathway_labels),
        "pathway_flux_trajectory": result.pathway_flux_trajectory.tolist(),
        "measurements": _process_measurements(declaration, result),
        "final_activity": result.activity,
        "final_pathway_flux": result.pathway_flux,
        "final_drives": result.final_drives,
        "learning": result.learning,
    }


def _process_measurements(declaration: dict, result: ProcessResult) -> dict:
    activity_norms = np.linalg.norm(result.trajectory, axis=1)
    active_counts = np.count_nonzero(result.trajectory > 0.01, axis=1)
    peak_index = np.unravel_index(
        int(np.argmax(result.trajectory)), result.trajectory.shape
    )
    return {
        "activity_threshold": 0.01,
        "peak_activity": float(result.trajectory[peak_index]),
        "peak_activity_population": result.labels[peak_index[1]],
        "peak_activity_tick": int(peak_index[0]),
        "peak_active_populations": int(np.max(active_counts)),
        "final_active_populations": int(active_counts[-1]),
        "peak_activity_norm": float(np.max(activity_norms)),
        "final_activity_norm": float(activity_norms[-1]),
        "drive_removed_after_tick": declaration.get("drive_ticks"),
        "control_maximum_activity_difference": None,
        "control_activity_difference_norm": None,
    }
