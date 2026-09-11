"""Observer-only Cardinal Candidate and Cardinal Node classification."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ControlMatch:
    label: str
    population: str
    level: int
    differences: dict[str, float]
    within_tolerance: dict[str, bool]

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "population": self.population,
            "level": self.level,
            "differences": dict(self.differences),
            "within_tolerance": dict(self.within_tolerance),
        }


class MatchedControlSelector:
    """Select controls only when every declared matching constraint holds."""

    FIELDS = (
        "activity",
        "incoming_degree",
        "outgoing_degree",
        "entrenchment",
        "baseline_perturbation_sensitivity",
    )

    def __init__(self, *, tolerances: dict[str, float]):
        if set(tolerances) != set(self.FIELDS):
            raise ValueError("control tolerances must declare every matching field")
        if any(float(value) < 0.0 for value in tolerances.values()):
            raise ValueError("control tolerances must not be negative")
        self.tolerances = {key: float(value) for key, value in tolerances.items()}

    def select(self, *, target: dict, controls: tuple[dict, ...]) -> ControlMatch:
        required = {"label", "population", "level", *self.FIELDS}
        if not required <= target.keys():
            raise ValueError("target is missing control-matching evidence")
        eligible = []
        for control in controls:
            if not required <= control.keys():
                raise ValueError("control is missing matching evidence")
            if (
                control["population"] != target["population"]
                or control["level"] != target["level"]
                or control["label"] == target["label"]
            ):
                continue
            differences = {
                field: abs(float(control[field]) - float(target[field]))
                for field in self.FIELDS
            }
            within = {
                field: difference <= self.tolerances[field]
                for field, difference in differences.items()
            }
            if all(within.values()):
                scaled = sum(
                    difference / self.tolerances[field]
                    if self.tolerances[field] > 0.0
                    else 0.0
                    for field, difference in differences.items()
                )
                eligible.append((scaled, str(control["label"]), control, differences, within))
        if not eligible:
            raise ValueError("no control satisfies every matching constraint")
        _, _, selected, differences, within = min(eligible)
        return ControlMatch(
            label=str(selected["label"]),
            population=str(selected["population"]),
            level=int(selected["level"]),
            differences=differences,
            within_tolerance=within,
        )


@dataclass(frozen=True)
class CardinalClassification:
    candidate: bool
    cardinal_node: bool
    failed_candidate_criteria: tuple[str, ...]
    failed_cardinal_criteria: tuple[str, ...]
    measures: dict[str, float]
    evidence: dict

    def as_dict(self) -> dict:
        return {
            "candidate": self.candidate,
            "cardinal_node": self.cardinal_node,
            "failed_candidate_criteria": list(self.failed_candidate_criteria),
            "failed_cardinal_criteria": list(self.failed_cardinal_criteria),
            "measures": dict(self.measures),
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class CardinalObservation:
    columns: dict[str, CardinalClassification]

    def as_dict(self) -> dict:
        return {
            "columns": {
                label: classification.as_dict()
                for label, classification in self.columns.items()
            },
            "candidate_labels": [
                label for label, value in self.columns.items() if value.candidate
            ],
            "cardinal_node_labels": [
                label for label, value in self.columns.items() if value.cardinal_node
            ],
        }


class CardinalObserver:
    """Advance lifecycle classifications only from declared behavioral evidence."""

    def __init__(
        self,
        *,
        entry_route_threshold: float,
        stability_threshold: float,
        control_quantile: float,
        minimum_subwebs_reinstated: int = 2,
    ):
        for name, value in {
            "entry route threshold": entry_route_threshold,
            "stability threshold": stability_threshold,
            "control quantile": control_quantile,
        }.items():
            if not 0.0 < float(value) < 1.0:
                raise ValueError(f"{name} must be between zero and one")
        if (
            isinstance(minimum_subwebs_reinstated, bool)
            or not isinstance(minimum_subwebs_reinstated, int)
            or minimum_subwebs_reinstated < 2
        ):
            raise ValueError("minimum reinstated Subwebs must be at least two")
        self.entry_route_threshold = float(entry_route_threshold)
        self.stability_threshold = float(stability_threshold)
        self.control_quantile = float(control_quantile)
        self.minimum_subwebs_reinstated = minimum_subwebs_reinstated

    def _control_threshold(self, values: list[float]) -> float:
        controls = np.asarray(values, dtype=np.float64)
        if controls.ndim != 1 or controls.size < 1 or not np.all(np.isfinite(controls)):
            raise ValueError("cardinal control distributions must be non-empty and finite")
        return float(np.quantile(controls, self.control_quantile, method="higher"))

    def classify(self, evidence_rows: tuple[dict, ...]) -> CardinalObservation:
        columns = {}
        for row in evidence_rows:
            label = str(row["label"])
            routes = {
                str(name): float(value)
                for name, value in row["entry_routes"].items()
            }
            stimulation_threshold = self._control_threshold(
                row["matched_non_recruited_stimulation"]
            )
            candidate_checks = {
                "recruited": bool(row["recruited"]),
                "functional_web_membership": bool(row["functional_web_member"]),
                "independent_entry_routes": sum(
                    value >= self.entry_route_threshold for value in routes.values()
                )
                >= 2,
                "held_out_stability": float(row["held_out_stability"])
                >= self.stability_threshold,
                "supporting_web_stimulation": float(
                    row["supporting_web_stimulation"]
                )
                > stimulation_threshold,
            }
            failed_candidate = tuple(
                name for name, passed in candidate_checks.items() if not passed
            )
            candidate = not failed_candidate

            interventions = row["interventions"]
            stimulation = interventions["stimulation"]
            individual = interventions["individual_lesion"]
            group = interventions["group_lesion"]
            lesion_threshold = self._control_threshold(
                interventions["matched_control_lesion_impairment"]
            )
            measures = {
                "ignition": float(stimulation["ignition"]),
                "completion": float(stimulation["completion"]),
                "feature_accessibility": float(individual["feature_accessibility"]),
                "ordered_phonological_reactivation": float(
                    individual["ordered_reactivation_impairment"]
                ),
                "redundant_recovery": float(interventions["redundant_recovery"]),
                "individual_lesion_ignition_impairment": float(
                    individual["ignition_impairment"]
                ),
                "group_lesion_ignition_impairment": float(
                    group["ignition_impairment"]
                ),
            }
            cardinal_checks = {
                "candidate": candidate,
                "lesion_impairs_ignition": measures[
                    "individual_lesion_ignition_impairment"
                ]
                > lesion_threshold,
                "features_remain_partly_accessible": measures[
                    "feature_accessibility"
                ]
                > 0.0,
                "stimulation_reinstates_multiple_subwebs": int(
                    stimulation["subwebs_reinstated"]
                )
                >= self.minimum_subwebs_reinstated,
                "redundancy_reported": "redundant_recovery" in interventions,
                "replicated_across_seeds": bool(row["replicated_across_seeds"]),
            }
            failed_cardinal = tuple(
                name for name, passed in cardinal_checks.items() if not passed
            )
            columns[label] = CardinalClassification(
                candidate=candidate,
                cardinal_node=not failed_cardinal,
                failed_candidate_criteria=failed_candidate,
                failed_cardinal_criteria=failed_cardinal,
                measures=measures,
                evidence=row,
            )
        return CardinalObservation(columns=columns)
