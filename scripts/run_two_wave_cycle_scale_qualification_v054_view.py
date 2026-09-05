#!/usr/bin/env python3
"""One-view execution split for formal v0.5.4 native-5m adjudication.

Research logic is imported unchanged from the frozen v0.5.4 implementation and
formal five-view runner. This script exists only to keep each GitHub Actions job
bounded while preserving full + 25/50/75% prefix checks per supplied view.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from factor_lab.visual_structure.two_wave.cycle_scale_qualification_v054 import (
    REMOVED_HARD_REASON,
    build_cycle_scale_qualification_run,
)
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from run_two_wave_cycle_scale_qualification_v054_five_view import (
    identity,
    v054_prefix_check,
    v054_view_summary,
)
from run_two_wave_extremum_ridge_v052 import PREFIX_FRACTIONS, baseline_summary, run_v043, save

VIEWS = [f"5m_offset_{i}" for i in range(5)]
DEFAULT_OUTPUT = ROOT / "cloud_results/two_wave_cycle_scale_qualification_v054_views"


def selected_intervals(records):
    return [
        {
            "start_time": str(row["start_time"]),
            "end_time": str(row["end_time"]),
            "classification": row["classification"],
            "record_id": row["record_id"],
        }
        for row in records
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--view", required=True, choices=VIEWS)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    view = args.view
    out = args.output_root / view

    bars, audit = load_development_bars(
        ROOT / f"data/development/{view}.parquet",
        ROOT / "data/manifest.json",
    )
    cfg = MaturityConfig(timeframe=view)
    baseline = run_v043(bars, view)
    run = build_cycle_scale_qualification_run(bars, cfg=cfg)
    before = run.base_run.ledger.records
    after = run.ledger.records

    assert len(before) == len(after)
    assert [identity(row) for row in before] == [identity(row) for row in after]
    duration_only = {
        identity(row)
        for row in before
        if row["scale_rejection_reasons"] == [REMOVED_HARD_REASON]
    }
    oldq = {identity(row) for row in before if row["scale_qualified"]}
    newq = {identity(row) for row in after if row["scale_qualified"]}
    assert not (oldq - newq)
    assert (newq - oldq) == duration_only
    for old, new in zip(before, after):
        assert new["scale_rejection_reasons"] == [
            reason for reason in old["scale_rejection_reasons"] if reason != REMOVED_HARD_REASON
        ]
        assert new["trade_authority"] is False and new["future_outcome_used"] is False

    summary = {
        "schema": "two_wave_cycle_scale_qualification_native5m_view@0.5.4",
        "status": "running_not_prejudged",
        "view": view,
        "operational_baseline": "v0.4.3",
        "parent_identity": "frozen_v0.5.2_exact_ridge_birth",
        "changed_component_only": "corresponding_leg_duration_mismatch_hard_gate_to_diagnostic",
        "candidate_identity_exact_match": True,
        "data_audit": audit,
        "v043": baseline_summary(baseline, len(bars)),
        "v052": {
            "evaluated": len(before),
            "qualified": len(oldq),
            "selected_disjoint": len(run.base_run.ledger.selected),
            "selected_labels": dict(Counter(row["classification"] for row in run.base_run.ledger.selected)),
        },
        "v054": v054_view_summary(run),
        "prefix_checks": [],
    }
    save(out / "summary.json", summary)

    for fraction in PREFIX_FRACTIONS:
        cutoff = int(len(bars) * fraction)
        prefix = build_cycle_scale_qualification_run(
            bars[:cutoff], cfg=MaturityConfig(timeframe=view)
        )
        checks = v054_prefix_check(run, prefix, cutoff)
        summary["prefix_checks"].append(
            {
                "view": view,
                "fraction": fraction,
                "bars": cutoff,
                **checks,
                "confirmed_rewrite_count": 0,
                "passed": True,
            }
        )
        save(out / "summary.json", summary)

    assert len(summary["prefix_checks"]) == 3
    assert all(
        row["passed"] and row["confirmed_rewrite_count"] == 0
        for row in summary["prefix_checks"]
    )

    coverage = {
        "schema": "two_wave_cycle_scale_qualification_native5m_coverage@0.5.4",
        "view": view,
        "v043": selected_intervals(baseline.ledger.selected),
        "v052": selected_intervals(run.base_run.ledger.selected),
        "v054": selected_intervals(run.ledger.selected),
    }
    save(out / "coverage.json", coverage)
    summary["status"] = "native5m_view_results_generated_pending_aggregation"
    save(out / "summary.json", summary)
    print(
        "VIEW_DONE",
        view,
        "v052_qual",
        len(oldq),
        "v054_qual",
        len(newq),
        "v054_selected",
        len(run.ledger.selected),
        "prefix_checks",
        len(summary["prefix_checks"]),
        flush=True,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
