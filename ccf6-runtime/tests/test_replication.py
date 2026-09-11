"""Seed-level paired inference and milestone verdicts."""

from __future__ import annotations

import copy
import json

import pytest

import ccf6.replication as replication
from ccf6.experiment import execute
from ccf6.replication import MilestoneAggregator


def seed_rows():
    return tuple(
        {
            "seed": 1000 + index,
            "presentation_count": 500 + index,
            "conditions": {
                "stimulation_executed": True,
                "lesion_executed": True,
            },
            "effects": {
                "completion": 0.2 + index / 1000,
                "reactivation": 0.15 + index / 1000,
                "pairing_localization": 0.1 + index / 1000,
                "candidate_intervention": 0.05 + index / 1000,
                "held_out_separation_change": -0.01 + index / 10000,
            },
            "criteria": {
                "correct_basins": True,
                "ordered_pseudowords": True,
                "web_overlap": True,
                "candidate_intervention": True,
            },
            "settling_failures": 0,
            "seed_failures": [],
        }
        for index in range(20)
    )


def test_bootstrap_resamples_seed_effects_deterministically_not_presentations():
    rows = seed_rows()
    before = copy.deepcopy(rows)
    aggregator = MilestoneAggregator(
        bootstrap_resamples=10_000,
        bootstrap_seed=20260910,
        separation_noninferiority_margin=0.05,
    )

    first = aggregator.aggregate(rows)
    second = aggregator.aggregate(rows)

    assert first.as_dict() == second.as_dict()
    assert rows == before
    assert first.replicate_unit == "seed"
    assert first.seed_count == 20
    assert first.bootstrap_resamples == 10_000
    completion = first.effects["completion"]
    assert completion.seed_values == tuple(
        row["effects"]["completion"] for row in rows
    )
    assert completion.interval_low > 0.0
    assert completion.expected_direction_proportion == 1.0
    assert completion.failure_count == 0
    assert first.total_settling_failures == sum(
        row["settling_failures"] for row in rows
    )
    assert first.verdict is True


def test_verdict_reports_each_failed_criterion_and_seed_failure():
    rows = list(seed_rows())
    rows[0]["effects"]["completion"] = -1.0
    rows[1]["criteria"]["web_overlap"] = False
    rows[2]["seed_failures"] = ["candidate_conditions_not_executable"]
    rows[3]["settling_failures"] = 2

    result = MilestoneAggregator(
        bootstrap_resamples=10_000,
        bootstrap_seed=9,
        separation_noninferiority_margin=0.05,
    ).aggregate(tuple(rows))

    assert result.criteria["web_overlap"]["passed"] is False
    assert result.criteria["seed_execution"]["passed"] is False
    assert result.criteria["seed_execution"]["failure_count"] == 2
    assert result.failed_seed_count == 2
    assert result.verdict is False


def test_replicated_run_preserves_seed_rows_and_aggregate_artifacts(
    monkeypatch,
    tmp_path,
):
    rows = seed_rows()

    class ImmediateExecutor:
        def __init__(self, *, max_workers):
            assert max_workers == 2

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def map(self, function, payloads):
            return [function(payload) for payload in payloads]

    monkeypatch.setattr(replication, "ProcessPoolExecutor", ImmediateExecutor)
    monkeypatch.setattr(
        replication,
        "_run_seed",
        lambda payload: rows[payload[1] - 1000],
    )
    definition = {
        "number": "011-test",
        "kind": "replicated_milestone",
        "network": {"seed": 1000},
        "replication": {
            "seed_inventory": list(range(1000, 1020)),
            "workers": 2,
            "bootstrap_resamples": 10_000,
            "bootstrap_seed": 7,
            "separation_noninferiority_margin": 0.05,
        },
    }

    run = execute(definition, tmp_path)

    metrics = json.loads((run / "metrics.json").read_text())
    aggregate = json.loads((run / "aggregate.json").read_text())
    manifest = json.loads((run / "manifest.json").read_text())
    assert metrics["replicate_unit"] == "seed"
    assert len(metrics["seeds"]) == 20
    assert aggregate["bootstrap"]["resamples"] == 10_000
    assert aggregate["verdict"] is True
    assert manifest["files"] == [
        "definition.json",
        "manifest.json",
        "metrics.json",
        "aggregate.json",
        "summary.json",
    ]


def test_replication_requires_twenty_seeds_and_ten_thousand_resamples():
    with pytest.raises(ValueError, match="at least 10,000"):
        MilestoneAggregator(
            bootstrap_resamples=9_999,
            bootstrap_seed=1,
            separation_noninferiority_margin=0.05,
        )

    aggregator = MilestoneAggregator(
        bootstrap_resamples=10_000,
        bootstrap_seed=1,
        separation_noninferiority_margin=0.05,
    )
    with pytest.raises(ValueError, match="at least 20"):
        aggregator.aggregate(seed_rows()[:19])
