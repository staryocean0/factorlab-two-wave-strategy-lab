#!/usr/bin/env python3
"""Formal five-native-5m adjudication for frozen v0.5.4 qualification."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from factor_lab.visual_structure.two_wave.cycle_scale_qualification_v054 import (
    REMOVED_HARD_REASON,
    build_cycle_scale_qualification_run,
)
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from run_two_wave_extremum_ridge_v052 import (
    PREFIX_FRACTIONS,
    audit_ranges,
    baseline_summary,
    coverage_and_labels,
    cross_offset_metrics,
    fixed_day_ranges,
    legacy_ranges,
    local_pivot_bars,
    prefix_check,
    run_v043,
    save,
)

VIEWS = [f"5m_offset_{i}" for i in range(5)]
OUTPUT = ROOT / "cloud_results/two_wave_cycle_scale_qualification_v054_five_view"


def identity(row):
    return (
        row["ridge_tuple_id"], tuple(row["ridge_ids"]), tuple(row["five_occurrence_bars"]),
        row["birth_scale_id"], row["birth_scale_level"], row["confirmation_bar"],
    )


def record_signature(row):
    return (
        row["record_id"], row["ridge_tuple_id"], tuple(row["ridge_ids"]),
        tuple(row["five_occurrence_bars"]), row["confirmation_bar"],
        row["birth_scale_level"], row["birth_scale_id"],
        row["scale_qualified"], tuple(row["scale_rejection_reasons"]),
        row["classification"], row["selected"], row["overlap_suppressed_by"],
        row["corresponding_leg_duration_diagnostic"]["frozen_v052_triggered"],
        tuple(row["corresponding_leg_duration_diagnostic"]["ratios"]),
    )


def signatures(records, cutoff):
    return [record_signature(r) for r in records if r["confirmation_bar"] < cutoff]


def v054_prefix_check(full, prefix, cutoff):
    upstream = prefix_check(full.base_run, prefix.base_run, cutoff)
    checks = {
        "v054_evaluated_records": signatures(prefix.ledger.records, cutoff) == signatures(full.ledger.records, cutoff),
        "v054_selected_records": signatures(prefix.ledger.selected, cutoff) == signatures(full.ledger.selected, cutoff),
    }
    if not all(checks.values()):
        failed = [k for k, ok in checks.items() if not ok]
        raise AssertionError(f"v0.5.4 qualification/ledger prefix rewrite at cutoff={cutoff}: {failed}")
    return {**{f"v052_{k}": v for k, v in upstream.items()}, **checks}


def qualified_count(run):
    return sum(r["scale_qualified"] for r in run.ledger.records)


def v054_view_summary(run):
    newly = [
        old for old in run.base_run.ledger.records
        if old["scale_rejection_reasons"] == [REMOVED_HARD_REASON]
    ]
    return {
        "evaluated": len(run.ledger.records),
        "qualified": qualified_count(run),
        "selected_disjoint": len(run.ledger.selected),
        "selected_labels": dict(Counter(r["classification"] for r in run.ledger.selected)),
        "duration_only_newly_qualified": len(newly),
        "lost_v052_qualified": 0,
    }


def main():
    summary = {
        "schema": "two_wave_cycle_scale_qualification_five_view@0.5.4",
        "status": "running_not_prejudged",
        "operational_baseline": "v0.4.3",
        "parent_identity": "frozen_v0.5.2_exact_ridge_birth",
        "changed_component_only": "corresponding_leg_duration_mismatch_hard_gate_to_diagnostic",
        "views": {},
        "prefix_checks": [],
    }
    bars_by_view, baseline_by_view, v052_by_view, v054_by_view = {}, {}, {}, {}

    for view in VIEWS:
        bars, audit = load_development_bars(
            ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json"
        )
        cfg = MaturityConfig(timeframe=view)
        baseline = run_v043(bars, view)
        run = build_cycle_scale_qualification_run(bars, cfg=cfg)
        before = run.base_run.ledger.records
        after = run.ledger.records
        assert len(before) == len(after)
        assert [identity(r) for r in before] == [identity(r) for r in after]
        duration_only = {identity(r) for r in before if r["scale_rejection_reasons"] == [REMOVED_HARD_REASON]}
        oldq = {identity(r) for r in before if r["scale_qualified"]}
        newq = {identity(r) for r in after if r["scale_qualified"]}
        assert not (oldq - newq)
        assert (newq - oldq) == duration_only
        for old, new in zip(before, after):
            assert new["scale_rejection_reasons"] == [r for r in old["scale_rejection_reasons"] if r != REMOVED_HARD_REASON]

        summary["views"][view] = {
            "data_audit": audit,
            "v043": baseline_summary(baseline, len(bars)),
            "v052": {
                "evaluated": len(before),
                "qualified": len(oldq),
                "selected_disjoint": len(run.base_run.ledger.selected),
                "selected_labels": dict(Counter(r["classification"] for r in run.base_run.ledger.selected)),
            },
            "v054": v054_view_summary(run),
        }
        bars_by_view[view], baseline_by_view[view] = bars, baseline
        v052_by_view[view], v054_by_view[view] = run.base_run, run
        save(OUTPUT / "summary.json", summary)

        for fraction in PREFIX_FRACTIONS:
            cutoff = int(len(bars) * fraction)
            prefix = build_cycle_scale_qualification_run(bars[:cutoff], cfg=MaturityConfig(timeframe=view))
            checks = v054_prefix_check(run, prefix, cutoff)
            summary["prefix_checks"].append({
                "view": view, "fraction": fraction, "bars": cutoff,
                **checks, "confirmed_rewrite_count": 0, "passed": True,
            })
            save(OUTPUT / "summary.json", summary)
        print("VIEW_DONE", view, "v052_qual", len(oldq), "v054_qual", len(newq), "v054_selected", len(run.ledger.selected), flush=True)

    assert len(summary["prefix_checks"]) == 15
    assert all(x["passed"] and x["confirmed_rewrite_count"] == 0 for x in summary["prefix_checks"])

    one_minute_bars, one_minute_audit = load_development_bars(
        ROOT / "data/development/1m_official.parquet", ROOT / "data/manifest.json"
    )
    one_minute_ns = np.asarray([pd.Timestamp(b["timestamp"]).value for b in one_minute_bars], dtype=np.int64)
    v043_series = {v: coverage_and_labels(baseline_by_view[v].ledger.selected, one_minute_ns) for v in VIEWS}
    v052_series = {v: coverage_and_labels(v052_by_view[v].ledger.selected, one_minute_ns) for v in VIEWS}
    v054_series = {v: coverage_and_labels(v054_by_view[v].ledger.selected, one_minute_ns) for v in VIEWS}
    summary["native_5m_offset_stability"] = {
        "v043": cross_offset_metrics(v043_series),
        "v052": cross_offset_metrics(v052_series),
        "v054": cross_offset_metrics(v054_series),
        "mapping_basis": "existing 1m timestamps only; no price resampling; 1m recognizer not run",
        "one_minute_data_audit": one_minute_audit,
        "iou_role": "boundary_stability_not_accuracy",
    }

    bars = bars_by_view["5m_offset_0"]
    baseline = baseline_by_view["5m_offset_0"]
    run = v054_by_view["5m_offset_0"]
    pivots = local_pivot_bars(baseline)
    summary["fixed_window_audit"] = audit_ranges(run, pivots, fixed_day_ranges(bars))
    ranges, source = legacy_ranges(ROOT / "cloud_results/two_wave_same_scale_delivery/v04/legacy_case_reaudit.json")
    summary["legacy_case_source"] = source
    summary["legacy_case_audit"] = audit_ranges(run, pivots, ranges)
    summary["status"] = "five_view_results_generated_pending_adjudication"
    save(OUTPUT / "summary.json", summary)
    print("PREFIX_CHECKS 15 all_passed", flush=True)
    print("OFFSET_STABILITY", json.dumps(summary["native_5m_offset_stability"], ensure_ascii=False), flush=True)
    print("STUDY_COMPLETE", OUTPUT, flush=True)


if __name__ == "__main__":
    main()
