"""Explicit laminar cortical-column circuits for the detailed NCL apparatus.

This module models named neural populations and anatomical pathway families at a
population-rate level.  It is intentionally separate from the accepted
three-compartment Functional Web runtime so the two implementations can be
compared before any later abstraction replaces either one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


COLUMN_POPULATION_ORDER = (
    "L23Tuft",
    "L5Tuft",
    "L23Pyr",
    "L4Pyr",
    "L5Pyr",
    "L6Pyr",
    "PV4",
    "PV23",
    "PV5",
    "SOM23",
    "SOM5",
    "VIP",
)

POPULATION_DECLARATIONS = {
    "L23Tuft": ("tuft", "L1", "apical_dendrite"),
    "L5Tuft": ("tuft", "L1", "apical_dendrite"),
    "L23Pyr": ("pyramidal", "L2/3", "soma"),
    "L4Pyr": ("pyramidal", "L4", "soma"),
    "L5Pyr": ("pyramidal", "L5", "soma"),
    "L6Pyr": ("pyramidal", "L6", "soma"),
    "PV4": ("pv", "L4", "soma"),
    "PV23": ("pv", "L2/3", "soma"),
    "PV5": ("pv", "L5", "soma"),
    "SOM23": ("som", "L2/3", "apical_dendrite"),
    "SOM5": ("som", "L5", "apical_dendrite"),
    "VIP": ("vip", "L2/3", "interneuron"),
}

LEGACY_SUFFIXES = {
    "L23Tuft": "1",
    "L5Tuft": "5T",
    "L23Pyr": "23",
    "L4Pyr": "4",
    "L5Pyr": "5",
    "L6Pyr": "6",
    "PV4": "PV4",
    "PV23": "PV23",
    "PV5": "PV5",
    "SOM23": "SOM",
    "SOM5": "SOM5",
    "VIP": "VIP",
}

ROUTE_FAMILIES = frozenset(
    {"Input", "Flow", "Ascend", "Topdown", "Lateral", "Pv", "Som", "Vip"}
)


@dataclass
class NeuralPopulation:
    identifier: str
    column: str | None
    level: str
    layer: str | None
    kind: str
    target_compartment: str
    legacy_name: str
    activity: float = 0.0


@dataclass
class CorticalPathway:
    identifier: str
    source: str
    target: str
    effect: str
    route: str
    declared_strength: float
    base_strength: float
    plastic: bool
    release_facilitation: float = 1.0
    postsynaptic_receptiveness: float = 1.0
    terminal_boutons: int = 4
    axonal_branches: int = 1
    dendritic_spines: int = 4
    structural_credit: float = 0.0
    eligibility: float = 0.0


@dataclass(frozen=True)
class TickResult:
    activity: dict[str, float]
    pathway_flux: dict[str, float]
    drives: dict[str, dict[str, float]]


@dataclass(frozen=True)
class CorticalLearningResult:
    success_signal: float
    presentation_id: str
    adaptation_applied: bool
    changed_pathways: tuple[str, ...]


def default_cortical_definition(seed: int) -> dict:
    """Return a fully declared population-rate cortical hierarchy."""
    return {
        "seed": int(seed),
        "hierarchy": {
            "lower_columns": 5,
            "middle_columns": 3,
            "higher_columns": 2,
            "lateral_radius": 1,
            "ascending_fan_out": 2,
        },
        "dynamics": {
            "dt": 0.05,
            "transmission_cutoff": 0.02,
            "modulatory_scale": 0.5,
            "time_constants": {
                "relay": 0.12,
                "state": 0.15,
                "pyramidal": 0.20,
                "tuft": 0.25,
                "pv": 0.08,
                "som": 0.24,
                "vip": 0.15,
            },
            "thresholds": {
                "relay": 0.0,
                "state": 0.0,
                "pyramidal": 0.08,
                "tuft": 0.05,
                "pv": 0.04,
                "som": 0.05,
                "vip": 0.04,
            },
        },
        "pathway_initialization": {"relative_variation": 0.05},
        "strengths": {
            "thalamic_l4": 1.0,
            "thalamic_pv4": 0.9,
            "thalamic_direct": 0.18,
            "l4_l23": 0.95,
            "l23_l5": 0.80,
            "l5_l6": 0.70,
            "l5_motor": 0.35,
            "l6_thalamus": 0.12,
            "pyr_pv": 0.76,
            "pv_pyr": 0.84,
            "pv_cross_layer": 0.48,
            "pyr_som": 0.44,
            "som_tuft": 0.84,
            "som_pv": 0.32,
            "som_vip": 0.42,
            "pv_som": 0.24,
            "pv_vip": 0.14,
            "vip_som": 0.90,
            "tuft_soma": 0.65,
            "recurrent_l5_l23": 0.46,
            "ascending_l23": 0.58,
            "ascending_l5": 0.34,
            "topdown_l23_tuft": 0.68,
            "topdown_l5_tuft": 0.72,
            "topdown_l6": 0.30,
            "lateral_pv": 0.72,
            "lateral_som23": 0.56,
            "lateral_som5": 0.42,
            "attention_vip_selected": 0.96,
            "attention_vip_unselected": 0.18,
            "arousal_thalamus": 0.82,
            "arousal_pv": 0.45,
            "novelty_residual": 0.72,
            "reward_higher": 0.68,
            "reward_vip": 0.62,
        },
        "plasticity": {
            "eligibility_decay": 0.8,
            "release_facilitation_rate": 0.03,
            "postsynaptic_receptiveness_rate": 0.02,
            "structural_credit_rate": 1.0,
            "structural_growth_threshold": 0.5,
            "initial_terminal_boutons": 4,
            "initial_axonal_branches": 1,
            "initial_dendritic_spines": 4,
            "maximum_terminal_boutons": 12,
            "maximum_axonal_branches": 4,
            "maximum_dendritic_spines": 12,
            "maximum_release_facilitation": 1.5,
            "maximum_postsynaptic_receptiveness": 1.5,
            "maximum_effective_strength": 3.0,
        },
    }


class CorticalCircuit:
    """A hierarchy of explicit laminar Columns behind one simulation interface."""

    def __init__(self, definition: dict):
        self.definition = definition
        self._validate_definition()
        self.seed = int(definition["seed"])
        self.dynamics = definition["dynamics"]
        self.strengths = {key: float(value) for key, value in definition["strengths"].items()}
        self.plasticity = definition["plasticity"]
        self._randomizer = np.random.default_rng(self.seed)
        self.hierarchy = self._column_hierarchy(definition["hierarchy"])
        self.populations: dict[str, NeuralPopulation] = {}
        self.pathways: dict[str, CorticalPathway] = {}
        self._contributors: dict[str, set[str]] = {}
        self._build_populations()
        self._build_pathways()

    @classmethod
    def from_definition(cls, definition: dict) -> CorticalCircuit:
        return cls(definition)

    def _validate_definition(self) -> None:
        required = {
            "seed",
            "hierarchy",
            "dynamics",
            "pathway_initialization",
            "strengths",
            "plasticity",
        }
        missing = required - definition_keys(self.definition)
        if missing:
            raise ValueError(f"cortical circuit definition missing {sorted(missing)}")
        hierarchy = self.definition["hierarchy"]
        if int(hierarchy.get("lower_columns", 0)) < 5:
            raise ValueError("detailed hierarchy requires at least 5 lower cortical Columns")
        if int(hierarchy.get("middle_columns", 0)) < 2:
            raise ValueError("detailed hierarchy requires at least 2 middle cortical Columns")
        if int(hierarchy.get("higher_columns", 0)) < 2:
            raise ValueError("detailed hierarchy requires at least 2 higher cortical Columns")
        if int(hierarchy.get("lateral_radius", 0)) < 1:
            raise ValueError("lateral radius must be at least 1")
        if int(hierarchy.get("ascending_fan_out", 0)) < 1:
            raise ValueError("ascending fan-out must be at least 1")
        dynamics = self.definition["dynamics"]
        if float(dynamics.get("dt", 0.0)) <= 0.0:
            raise ValueError("cortical dt must be positive")
        if not 0.0 <= float(dynamics.get("transmission_cutoff", -1.0)) <= 1.0:
            raise ValueError("cortical transmission cutoff must be in [0,1]")
        for kind in ("relay", "state", "pyramidal", "tuft", "pv", "som", "vip"):
            if float(dynamics.get("time_constants", {}).get(kind, 0.0)) <= 0.0:
                raise ValueError(f"{kind} time constant must be positive")
            threshold = float(dynamics.get("thresholds", {}).get(kind, -1.0))
            if not 0.0 <= threshold < 1.0:
                raise ValueError(f"{kind} threshold must be in [0,1)")
        variation = float(
            self.definition["pathway_initialization"].get("relative_variation", -1.0)
        )
        if not 0.0 <= variation < 1.0:
            raise ValueError("cortical pathway relative variation must be in [0,1)")
        if any(float(value) < 0.0 for value in self.definition["strengths"].values()):
            raise ValueError("cortical pathway strengths must be non-negative")
        plasticity = self.definition["plasticity"]
        if not 0.0 <= float(plasticity.get("eligibility_decay", -1.0)) <= 1.0:
            raise ValueError("cortical eligibility decay must be in [0,1]")

    @staticmethod
    def _column_hierarchy(declaration: dict) -> dict[str, list[str]]:
        lower_count = int(declaration["lower_columns"])
        if lower_count > 26:
            raise ValueError("lower cortical Column names support at most 26 Columns")
        return {
            "lower": [chr(ord("A") + index) for index in range(lower_count)],
            "middle": [f"M{index + 1}" for index in range(int(declaration["middle_columns"]))],
            "higher": [f"H{index + 1}" for index in range(int(declaration["higher_columns"]))],
        }

    def _build_populations(self) -> None:
        for level, columns in self.hierarchy.items():
            for column in columns:
                for local_name in COLUMN_POPULATION_ORDER:
                    kind, layer, target_compartment = POPULATION_DECLARATIONS[local_name]
                    identifier = f"{column}.{local_name}"
                    self.populations[identifier] = NeuralPopulation(
                        identifier=identifier,
                        column=column,
                        level=level,
                        layer=layer,
                        kind=kind,
                        target_compartment=target_compartment,
                        legacy_name=f"{column}{LEGACY_SUFFIXES[local_name]}",
                    )
        for identifier, label, kind in (
            ("thal", "Thalamus", "relay"),
            ("motor", "Subcortical motor output", "relay"),
            ("attention", "Attention", "state"),
            ("arousal", "Arousal", "state"),
            ("novelty", "Novelty", "state"),
            ("reward", "Reward", "state"),
        ):
            self.populations[identifier] = NeuralPopulation(
                identifier=identifier,
                column=None,
                level="external",
                layer=None,
                kind=kind,
                target_compartment="external",
                legacy_name=label,
            )

    def _add_pathway(
        self,
        source: str,
        target: str,
        effect: str,
        route: str,
        strength_key: str,
        *,
        plastic: bool | None = None,
    ) -> None:
        identifier = f"{source}-to-{target}"
        if identifier in self.pathways:
            raise ValueError(f"duplicate cortical pathway {identifier}")
        if source not in self.populations or target not in self.populations:
            raise ValueError(f"cortical pathway {identifier} has an unknown endpoint")
        if route not in ROUTE_FAMILIES:
            raise ValueError(f"cortical pathway {identifier} has unknown route {route}")
        initial_boutons = int(self.plasticity["initial_terminal_boutons"])
        initial_axonal_branches = int(
            self.plasticity["initial_axonal_branches"]
        )
        initial_dendritic_spines = int(
            self.plasticity["initial_dendritic_spines"]
        )
        declared_strength = self.strengths[strength_key]
        variation = float(
            self.definition["pathway_initialization"]["relative_variation"]
        )
        initialized_strength = declared_strength * self._randomizer.uniform(
            1.0 - variation,
            1.0 + variation,
        )
        self.pathways[identifier] = CorticalPathway(
            identifier=identifier,
            source=source,
            target=target,
            effect=effect,
            route=route,
            declared_strength=declared_strength,
            base_strength=float(initialized_strength),
            plastic=effect != "inhibitory" if plastic is None else plastic,
            terminal_boutons=initial_boutons,
            axonal_branches=initial_axonal_branches,
            dendritic_spines=initial_dendritic_spines,
        )
        self._contributors[identifier] = set()

    def _build_pathways(self) -> None:
        for level, columns in self.hierarchy.items():
            for column in columns:
                self._add_intracolumnar_pathways(column)
                if level == "lower":
                    self._add_pathway("thal", f"{column}.L4Pyr", "excitatory", "Input", "thalamic_l4")
                    self._add_pathway("thal", f"{column}.PV4", "excitatory", "Pv", "thalamic_pv4")
                    self._add_pathway("thal", f"{column}.L23Pyr", "modulatory", "Input", "thalamic_direct")
                    self._add_pathway("thal", f"{column}.L6Pyr", "modulatory", "Input", "thalamic_direct")
                    self._add_pathway(f"{column}.L5Pyr", "motor", "excitatory", "Flow", "l5_motor")
                    self._add_pathway(f"{column}.L6Pyr", "thal", "modulatory", "Flow", "l6_thalamus")
            self._add_lateral_pathways(columns)

        self._add_hierarchical_pathways(self.hierarchy["lower"], self.hierarchy["middle"])
        self._add_hierarchical_pathways(self.hierarchy["middle"], self.hierarchy["higher"])
        self._add_behavioral_pathways()

    def _add_intracolumnar_pathways(self, column: str) -> None:
        node = lambda name: f"{column}.{name}"
        self._add_pathway(node("L4Pyr"), node("L23Pyr"), "excitatory", "Flow", "l4_l23")
        self._add_pathway(node("L23Pyr"), node("L5Pyr"), "excitatory", "Flow", "l23_l5")
        self._add_pathway(node("L5Pyr"), node("L6Pyr"), "excitatory", "Flow", "l5_l6")
        self._add_pathway(node("L5Pyr"), node("L23Pyr"), "excitatory", "Flow", "recurrent_l5_l23")

        self._add_pathway(node("L23Pyr"), node("PV23"), "excitatory", "Pv", "pyr_pv")
        self._add_pathway(node("PV23"), node("L23Pyr"), "inhibitory", "Pv", "pv_pyr")
        self._add_pathway(node("PV23"), node("L5Pyr"), "inhibitory", "Pv", "pv_cross_layer")
        self._add_pathway(node("L5Pyr"), node("PV5"), "excitatory", "Pv", "pyr_pv")
        self._add_pathway(node("PV5"), node("L5Pyr"), "inhibitory", "Pv", "pv_pyr")
        self._add_pathway(node("PV4"), node("L4Pyr"), "inhibitory", "Pv", "pv_pyr")
        self._add_pathway(node("PV4"), node("SOM23"), "inhibitory", "Pv", "pv_som")
        self._add_pathway(node("PV4"), node("VIP"), "inhibitory", "Pv", "pv_vip")

        self._add_pathway(node("L23Pyr"), node("SOM23"), "excitatory", "Som", "pyr_som")
        self._add_pathway(node("L5Pyr"), node("SOM5"), "excitatory", "Som", "pyr_som")
        self._add_pathway(node("SOM23"), node("L23Tuft"), "inhibitory", "Som", "som_tuft")
        self._add_pathway(node("SOM23"), node("L5Tuft"), "inhibitory", "Som", "som_tuft")
        self._add_pathway(node("SOM5"), node("L5Tuft"), "inhibitory", "Som", "som_tuft")
        self._add_pathway(node("SOM23"), node("PV23"), "inhibitory", "Som", "som_pv")
        self._add_pathway(node("SOM23"), node("VIP"), "inhibitory", "Som", "som_vip")

        self._add_pathway(node("VIP"), node("SOM23"), "inhibitory", "Vip", "vip_som")
        self._add_pathway(node("VIP"), node("SOM5"), "inhibitory", "Vip", "vip_som")
        self._add_pathway(node("L23Tuft"), node("L23Pyr"), "modulatory", "Topdown", "tuft_soma")
        self._add_pathway(node("L5Tuft"), node("L5Pyr"), "modulatory", "Topdown", "tuft_soma")

    def _add_lateral_pathways(self, columns: list[str]) -> None:
        radius = int(self.definition["hierarchy"]["lateral_radius"])
        for source_index, source in enumerate(columns):
            for target_index, target in enumerate(columns):
                if source == target or abs(source_index - target_index) > radius:
                    continue
                self._add_pathway(f"{source}.L23Pyr", f"{target}.PV23", "excitatory", "Lateral", "lateral_pv")
                self._add_pathway(f"{source}.L23Pyr", f"{target}.SOM23", "excitatory", "Lateral", "lateral_som23")
                self._add_pathway(f"{source}.L23Pyr", f"{target}.SOM5", "excitatory", "Lateral", "lateral_som5")

    def _add_hierarchical_pathways(self, lower: list[str], higher: list[str]) -> None:
        fan_out = min(int(self.definition["hierarchy"]["ascending_fan_out"]), len(higher))
        for lower_index, lower_column in enumerate(lower):
            for offset in range(fan_out):
                higher_column = higher[(lower_index + offset) % len(higher)]
                self._add_pathway(f"{lower_column}.L23Pyr", f"{higher_column}.L4Pyr", "excitatory", "Ascend", "ascending_l23")
                self._add_pathway(f"{lower_column}.L5Pyr", f"{higher_column}.L4Pyr", "excitatory", "Ascend", "ascending_l5")
                self._add_pathway(f"{higher_column}.L23Pyr", f"{lower_column}.L23Tuft", "modulatory", "Topdown", "topdown_l23_tuft")
                self._add_pathway(f"{higher_column}.L5Pyr", f"{lower_column}.L5Tuft", "modulatory", "Topdown", "topdown_l5_tuft")
                self._add_pathway(f"{higher_column}.L23Pyr", f"{lower_column}.L6Pyr", "modulatory", "Topdown", "topdown_l6")

    def _add_behavioral_pathways(self) -> None:
        all_columns = [column for columns in self.hierarchy.values() for column in columns]
        for index, column in enumerate(all_columns):
            attention_key = "attention_vip_selected" if index == 0 else "attention_vip_unselected"
            self._add_pathway("attention", f"{column}.VIP", "modulatory", "Vip", attention_key)
            self._add_pathway("reward", f"{column}.VIP", "modulatory", "Vip", "reward_vip")
        self._add_pathway("arousal", "thal", "modulatory", "Input", "arousal_thalamus")
        for column in self.hierarchy["lower"]:
            self._add_pathway("arousal", f"{column}.PV4", "modulatory", "Pv", "arousal_pv")
            self._add_pathway("novelty", f"{column}.L23Pyr", "modulatory", "Ascend", "novelty_residual")
        for column in self.hierarchy["middle"]:
            self._add_pathway("novelty", f"{column}.L4Pyr", "modulatory", "Ascend", "novelty_residual")
        for column in self.hierarchy["higher"]:
            self._add_pathway("reward", f"{column}.L23Pyr", "modulatory", "Topdown", "reward_higher")

    def reset(self) -> None:
        for population in self.populations.values():
            population.activity = 0.0
        for pathway in self.pathways.values():
            pathway.eligibility = 0.0

    def tick(
        self,
        external_drives: dict[str, float] | None = None,
        *,
        active_routes: set[str] | None = None,
        disabled_routes: Iterable[str] = (),
    ) -> TickResult:
        external_drives = external_drives or {}
        unknown_populations = set(external_drives) - self.populations.keys()
        if unknown_populations:
            raise ValueError(f"external drive names unknown populations {sorted(unknown_populations)}")
        for value in external_drives.values():
            if isinstance(value, bool):
                raise ValueError("external drive must be in [0,1]")
            try:
                normalized_value = float(value)
            except (TypeError, ValueError) as error:
                raise ValueError("external drive must be in [0,1]") from error
            if not np.isfinite(normalized_value) or not 0.0 <= normalized_value <= 1.0:
                raise ValueError("external drive must be in [0,1]")
        selected_routes = ROUTE_FAMILIES if active_routes is None else frozenset(active_routes)
        unknown_routes = selected_routes - ROUTE_FAMILIES
        disabled = frozenset(disabled_routes)
        unknown_routes |= disabled - ROUTE_FAMILIES
        if unknown_routes:
            raise ValueError(f"unknown cortical route families {sorted(unknown_routes)}")
        selected_routes = selected_routes - disabled

        previous = {identifier: population.activity for identifier, population in self.populations.items()}
        drives = {
            identifier: {
                "external": float(external_drives.get(identifier, 0.0)),
                "excitatory": 0.0,
                "inhibitory": 0.0,
                "modulatory": 0.0,
                "net": 0.0,
            }
            for identifier in self.populations
        }
        pathway_flux: dict[str, float] = {}
        cutoff = float(self.dynamics["transmission_cutoff"])
        decay = float(self.plasticity["eligibility_decay"])
        for pathway in self.pathways.values():
            if pathway.route not in selected_routes:
                pathway_flux[pathway.identifier] = 0.0
                pathway.eligibility *= decay
                continue
            source_activity = previous[pathway.source]
            broadcast = source_activity if source_activity >= cutoff else 0.0
            flux = self._effective_strength(pathway) * broadcast
            if pathway.effect == "inhibitory":
                drives[pathway.target]["inhibitory"] += flux
                pathway_flux[pathway.identifier] = -flux
            elif pathway.effect == "modulatory":
                scaled = flux * float(self.dynamics["modulatory_scale"])
                drives[pathway.target]["modulatory"] += scaled
                pathway_flux[pathway.identifier] = scaled
            else:
                drives[pathway.target]["excitatory"] += flux
                pathway_flux[pathway.identifier] = flux
            if pathway.plastic:
                pathway.eligibility = min(
                    1.0,
                    decay * pathway.eligibility
                    + previous[pathway.source] * previous[pathway.target],
                )

        next_activity: dict[str, float] = {}
        dt = float(self.dynamics["dt"])
        for identifier, population in self.populations.items():
            components = drives[identifier]
            net = max(
                0.0,
                min(
                    1.0,
                    components["external"]
                    + components["excitatory"]
                    + components["modulatory"]
                    - components["inhibitory"],
                ),
            )
            components["net"] = net
            threshold = float(self.dynamics["thresholds"][population.kind])
            target = max(0.0, min(1.0, (net - threshold) / (1.0 - threshold)))
            tau = float(self.dynamics["time_constants"][population.kind])
            alpha = 1.0 - np.exp(-dt / tau)
            next_activity[identifier] = float(
                population.activity + (target - population.activity) * alpha
            )
        for identifier, activity in next_activity.items():
            self.populations[identifier].activity = activity
        return TickResult(
            activity=dict(next_activity),
            pathway_flux=pathway_flux,
            drives=drives,
        )

    def apply_success_signal(
        self, success_signal: float, *, presentation_id: str
    ) -> CorticalLearningResult:
        signal = float(success_signal)
        if not 0.0 <= signal <= 1.0:
            raise ValueError("Success Signal must be in [0,1]")
        if not presentation_id:
            raise ValueError("Hebbian adaptation requires a Presentation identity")
        changed: list[str] = []
        for pathway in self.pathways.values():
            if not pathway.plastic or signal == 0.0 or pathway.eligibility == 0.0:
                continue
            confirmation = signal * pathway.eligibility
            pathway.release_facilitation += float(
                self.plasticity["release_facilitation_rate"]
            ) * confirmation * (
                float(self.plasticity["maximum_release_facilitation"])
                - pathway.release_facilitation
            )
            pathway.postsynaptic_receptiveness += float(
                self.plasticity["postsynaptic_receptiveness_rate"]
            ) * confirmation * (
                float(self.plasticity["maximum_postsynaptic_receptiveness"])
                - pathway.postsynaptic_receptiveness
            )
            pathway.structural_credit += float(
                self.plasticity["structural_credit_rate"]
            ) * confirmation
            growth_threshold = float(self.plasticity["structural_growth_threshold"])
            maximum_boutons = int(self.plasticity["maximum_terminal_boutons"])
            maximum_branches = int(self.plasticity["maximum_axonal_branches"])
            maximum_spines = int(self.plasticity["maximum_dendritic_spines"])
            while pathway.structural_credit >= growth_threshold and (
                pathway.terminal_boutons < maximum_boutons
                or pathway.axonal_branches < maximum_branches
                or pathway.dendritic_spines < maximum_spines
            ):
                pathway.terminal_boutons = min(
                    maximum_boutons, pathway.terminal_boutons + 1
                )
                pathway.axonal_branches = min(
                    maximum_branches, pathway.axonal_branches + 1
                )
                pathway.dendritic_spines = min(
                    maximum_spines, pathway.dendritic_spines + 1
                )
                pathway.structural_credit -= growth_threshold
            self._contributors[pathway.identifier].add(presentation_id)
            changed.append(pathway.identifier)
        return CorticalLearningResult(
            success_signal=signal,
            presentation_id=presentation_id,
            adaptation_applied=bool(changed),
            changed_pathways=tuple(changed),
        )

    def _effective_strength(self, pathway: CorticalPathway) -> float:
        strength = (
            pathway.base_strength
            * pathway.release_facilitation
            * pathway.postsynaptic_receptiveness
            * self._structural_factor(pathway)
        )
        return min(float(self.plasticity["maximum_effective_strength"]), strength)

    def _structural_factor(self, pathway: CorticalPathway) -> float:
        return min(
            pathway.terminal_boutons
            / float(self.plasticity["initial_terminal_boutons"]),
            pathway.axonal_branches
            / float(self.plasticity["initial_axonal_branches"]),
            pathway.dendritic_spines
            / float(self.plasticity["initial_dendritic_spines"]),
        )

    def pathway_state(self, identifier: str) -> dict:
        if identifier not in self.pathways:
            raise KeyError(f"unknown cortical pathway {identifier!r}")
        pathway = self.pathways[identifier]
        return {
            "base_strength": pathway.base_strength,
            "release_facilitation": pathway.release_facilitation,
            "postsynaptic_receptiveness": pathway.postsynaptic_receptiveness,
            "terminal_boutons": pathway.terminal_boutons,
            "axonal_branches": pathway.axonal_branches,
            "dendritic_spines": pathway.dendritic_spines,
            "structural_contacts": self._structural_factor(pathway),
            "structural_credit": pathway.structural_credit,
            "eligibility": pathway.eligibility,
            "effective_strength": self._effective_strength(pathway),
            "contributing_presentations": len(self._contributors[identifier]),
        }

    def activity_vector(self) -> np.ndarray:
        return np.asarray(
            [self.populations[identifier].activity for identifier in self.populations],
            dtype=np.float64,
        )

    def topology_snapshot(self) -> dict:
        columns = {
            column: {
                "level": level,
                "populations": [f"{column}.{name}" for name in COLUMN_POPULATION_ORDER],
            }
            for level, level_columns in self.hierarchy.items()
            for column in level_columns
        }
        populations = {
            identifier: {
                "column": population.column,
                "level": population.level,
                "layer": population.layer,
                "kind": population.kind,
                "target_compartment": population.target_compartment,
                "legacy_name": population.legacy_name,
            }
            for identifier, population in self.populations.items()
        }
        pathways = [
            {
                "id": pathway.identifier,
                "source": pathway.source,
                "target": pathway.target,
                "effect": pathway.effect,
                "route": pathway.route,
                "declared_strength": pathway.declared_strength,
                "base_strength": pathway.base_strength,
                "plastic": pathway.plastic,
            }
            for pathway in self.pathways.values()
        ]
        return {
            "seed": self.seed,
            "hierarchy": {key: list(value) for key, value in self.hierarchy.items()},
            "columns": columns,
            "populations": populations,
            "pathways": pathways,
        }


def definition_keys(definition: object) -> set[str]:
    if not isinstance(definition, dict):
        raise ValueError("cortical circuit definition must be an object")
    return set(definition)
