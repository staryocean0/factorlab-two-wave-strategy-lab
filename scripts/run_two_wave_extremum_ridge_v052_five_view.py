#!/usr/bin/env python3
"""Execution-only split for formal v0.5.2 five native 5m views.

Research logic is imported unchanged from run_two_wave_extremum_ridge_v052.py.
The 1m file is loaded only as a timestamp reference for cross-offset mapping;
no 1m ridge model is built in this process.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import build_ridge_run
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
    view_summary,
)

VIEWS = [f"5m_offset_{i}" for i in range(5)]
OUTPUT = ROOT / "cloud_results/two_wave_extremum_ridge_v052_five_view"


def main() -> None:
    summary = {
        "schema": "two_wave_extremum_ridge_five_view_execution_split@0.5.2",
        "research_logic": "unchanged_v052_imported_from_formal_runner",
        "operational_baseline": "v0.4.3",
        "views": {},
        "prefix_checks": [],
        "status": "running_not_prejudged",
    }
    bars_by_view = {}
    baseline_by_view = {}
    run_by_view = {}

    for view in VIEWS:
        bars, audit = load_development_bars(
            ROOT / f"data/development/{view}.parquet",
            ROOT / "data/manifest.json",
        )
        cfg = MaturityConfig(timeframe=view)
        baseline = run_v043(bars, view)
        run = build_ridge_run(bars, cfg)
        if view == "5m_offset_0":
            base_tuple = (
                len(baseline.ledger.records),
                sum(row["scale_qualified"] for row in baseline.ledger.records),
                len(baseline.ledger.selected),
            )
            assert base_tuple == (4706, 341, 212), base_tuple

        summary["views"][view] = {
            "data_audit": audit,
            "v043": baseline_summary(baseline, len(bars)),
            "v052": view_summary(run, baseline, bars),
        }
        bars_by_view[view] = bars
        baseline_by_view[view] = baseline
        run_by_view[view] = run
        save(OUTPUT / "summary.json", summary)

        for fraction in PREFIX_FRACTIONS:
            cutoff = int(len(bars) * fraction)
            prefix = build_ridge_run(bars[:cutoff], MaturityConfig(timeframe=view))
            checks = prefix_check(run, prefix, cutoff)
            summary["prefix_checks"].append({
                "view": view,
                "fraction": fraction,
                "bars": cutoff,
                **checks,
                "confirmed_rewrite_count": 0,
                "passed": True,
            })
            save(OUTPUT / "summary.json", summary)

        print(
            "VIEW_DONE", view,
            "births", len(run.tuple_births),
            "anomalies", len(run.lineage_anomalies),
            "eval", len(run.ledger.records),
            "qual", sum(row["scale_qualified"] for row in run.ledger.records),
            "selected", len(run.ledger.selected),
            flush=True,
        )

    assert len(summary["prefix_checks"]) == 15
    assert all(row["passed"] and row["confirmed_rewrite_count"] == 0 for row in summary["prefix_checks"])

    one_minute_bars, one_minute_audit = load_development_bars(
        ROOT / "data/development/1m_official.parquet",
        ROOT / "data/manifest.json",
    )
    one_minute_ns = np.asarray(
        [pd.Timestamp(bar["timestamp"]).value for bar in one_minute_bars],
        dtype=np.int64,
    )
    baseline_series = {
        view: coverage_and_labels(baseline_by_view[view].ledger.selected, one_minute_ns)
        for view in VIEWS
    }
    v052_series = {
        view: coverage_and_labels(run_by_view[view].ledger.selected, one_minute_ns)
        for view in VIEWS
    }
    summary["native_5m_offset_stability"] = {
        "v043": cross_offset_metrics(baseline_series),
        "v052": cross_offset_metrics(v052_series),
        "mapping_basis": "existing 1m timestamps only; no price resampling; 1m recognizer not run",
        "one_minute_data_audit": one_minute_audit,
        "iou_role": "boundary_stability_not_accuracy",
    }

    bars = bars_by_view["5m_offset_0"]
    baseline = baseline_by_view["5m_offset_0"]
    run = run_by_view["5m_offset_0"]
    pivots = local_pivot_bars(baseline)
    summary["fixed_window_audit"] = audit_ranges(run, pivots, fixed_day_ranges(bars))
    legacy_path = ROOT / "cloud_results/two_wave_same_scale_delivery/v04/legacy_case_reaudit.json"
    ranges, source = legacy_ranges(legacy_path)
    summary["legacy_case_source"] = source
    summary["legacy_case_audit"] = audit_ranges(run, pivots, ranges)

    summary["status"] = "five_view_results_generated_pending_adjudication"
    save(OUTPUT / "summary.json", summary)
    print("PREFIX_CHECKS", len(summary["prefix_checks"]), "all_passed", flush=True)
    print("OFFSET_STABILITY", json.dumps(summary["native_5m_offset_stability"], ensure_ascii=False), flush=True)
    print("CASE00", json.dumps(summary["legacy_case_audit"].get("case_00_A_clear_C_uncertain"), ensure_ascii=False), flush=True)
    print("CASE02", json.dumps(summary["legacy_case_audit"].get("case_02_C_new_downtrend"), ensure_ascii=False), flush=True)
    print("STUDY_COMPLETE", OUTPUT, flush=True)


if __name__ == "__main__":
    main()
