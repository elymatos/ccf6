"""Observer-only Cardinal Candidate and Cardinal Node classification."""

from __future__ import annotations

from ccf6.cardinals import CardinalObserver, MatchedControlSelector


def candidate_evidence(**overrides):
    evidence = {
        "label": "cross-domain-association#0",
        "recruited": True,
        "functional_web_member": True,
        "entry_routes": {"visual": 0.8, "pseudoword": 0.75},
        "held_out_stability": 0.9,
        "supporting_web_stimulation": 0.7,
        "matched_non_recruited_stimulation": [0.1, 0.2, 0.3, 0.25],
        "interventions": {
            "stimulation": {
                "subwebs_reinstated": 2,
                "ignition": 0.8,
                "completion": 0.7,
                "feature_accessibility": 0.8,
                "ordered_reactivation": 0.7,
            },
            "individual_lesion": {
                "ignition_impairment": 0.6,
                "completion_impairment": 0.5,
                "feature_accessibility": 0.4,
                "ordered_reactivation_impairment": 0.5,
            },
            "group_lesion": {
                "ignition_impairment": 0.8,
                "completion_impairment": 0.7,
                "feature_accessibility": 0.3,
                "ordered_reactivation_impairment": 0.7,
            },
            "matched_control_lesion_impairment": [0.1, 0.2, 0.15, 0.2],
            "redundant_recovery": 0.3,
        },
        "replicated_across_seeds": True,
    }
    evidence.update(overrides)
    return evidence


def test_commitment_or_activation_alone_cannot_create_a_candidate():
    evidence = candidate_evidence(
        functional_web_member=False,
        entry_routes={"visual": 0.99},
        held_out_stability=0.99,
        supporting_web_stimulation=0.99,
    )

    result = CardinalObserver(
        entry_route_threshold=0.5,
        stability_threshold=0.5,
        control_quantile=0.95,
    ).classify((evidence,))

    column = result.columns[evidence["label"]]
    assert column.candidate is False
    assert "functional_web_membership" in column.failed_candidate_criteria
    assert "independent_entry_routes" in column.failed_candidate_criteria
    assert column.cardinal_node is False


def test_cardinal_requires_route_stability_causal_lesion_stimulation_and_replication():
    observer = CardinalObserver(
        entry_route_threshold=0.5,
        stability_threshold=0.5,
        control_quantile=0.95,
    )

    positive = observer.classify((candidate_evidence(),))
    unreplicated = observer.classify(
        (candidate_evidence(replicated_across_seeds=False),)
    )

    classified = positive.columns["cross-domain-association#0"]
    assert classified.candidate is True
    assert classified.cardinal_node is True
    assert classified.measures["ignition"] == 0.8
    assert classified.measures["completion"] == 0.7
    assert classified.measures["feature_accessibility"] == 0.4
    assert classified.measures["ordered_phonological_reactivation"] == 0.5
    assert classified.measures["redundant_recovery"] == 0.3
    assert unreplicated.columns["cross-domain-association#0"].candidate is True
    assert unreplicated.columns["cross-domain-association#0"].cardinal_node is False


def test_controls_match_every_declared_dimension():
    selector = MatchedControlSelector(
        tolerances={
            "activity": 0.05,
            "incoming_degree": 1.0,
            "outgoing_degree": 1.0,
            "entrenchment": 0.1,
            "baseline_perturbation_sensitivity": 0.05,
        }
    )
    target = {
        "label": "association#0",
        "population": "association",
        "level": 0,
        "activity": 0.7,
        "incoming_degree": 6,
        "outgoing_degree": 6,
        "entrenchment": 2.0,
        "baseline_perturbation_sensitivity": 0.2,
    }
    controls = (
        {
            **target,
            "label": "association#1",
            "activity": 0.72,
            "entrenchment": 2.05,
            "baseline_perturbation_sensitivity": 0.18,
        },
        {**target, "label": "other-population#0", "population": "other-population"},
        {**target, "label": "association#2", "incoming_degree": 9},
    )

    match = selector.select(target=target, controls=controls)

    assert match.label == "association#1"
    assert match.population == target["population"]
    assert match.level == target["level"]
    assert all(match.within_tolerance.values())
