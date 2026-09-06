#!/usr/bin/env python3
"""Read-only diagnostics for the frozen v0.5.6 five-view hard-gate failure.

This script never runs a recognizer and never changes the pass/fail criterion.
It only computes and persists the D1 vs D2 label-agreement numbers that caused
the frozen aggregate to raise before writing its normal final_summary.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from run_two_wave_envelope_direction_v056_five_view import load_payloads
from run_two_wave_extremum_ridge_v052 import coverage_and_labels, cross_offset_metrics, save

VIEWS = [f"5m_offset_{i}" for i in range(5)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "cloud_results/two_wave_envelope_direction_v056_failure_diagnostic/summary.json",
    )
    args = parser.parse_args()

    summaries, coverages = load_payloads(args.input_root)
    prefix_checks = [row for view in VIEWS for row in summaries[view]["prefix_checks"]]
    assert len(prefix_checks) == 15
    assert all(row["passed"] and row["confirmed_rewrite_count"] == 0 for row in prefix_checks)

    one_minute_bars, one_minute_audit = load_development_bars(
        ROOT / "data/development/1m_official.parquet", ROOT / "data/manifest.json"
    )
    timestamps = np.asarray([pd.Timestamp(bar["timestamp"]).value for bar in one_minute_bars], dtype=np.int64)

    series = {"D1": {}, "D2": {}}
    for view in VIEWS:
        d1_rows, d2_rows = coverages[view]["D1"], coverages[view]["D2"]
        assert [r["record_id"] for r in d1_rows] == [r["record_id"] for r in d2_rows]
        assert [(r["start_time"], r["end_time"]) for r in d1_rows] == [
            (r["start_time"], r["end_time"]) for r in d2_rows
        ]
        series["D1"][view] = coverage_and_labels(d1_rows, timestamps)
        series["D2"][view] = coverage_and_labels(d2_rows, timestamps)
        assert np.array_equal(series["D1"][view][0], series["D2"][view][0])

    metrics = {version: cross_offset_metrics(series[version]) for version in ("D1", "D2")}
    comparison = {}
    deltas = []
    for view in VIEWS[1:]:
        d1 = metrics["D1"][view]
        d2 = metrics["D2"][view]
        assert d1["intersection_1m_bars"] == d2["intersection_1m_bars"]
        assert d1["union_1m_bars"] == d2["union_1m_bars"]
        assert d1["iou"] == d2["iou"]
        a1 = d1["same_label_fraction_on_common_owned"]
        a2 = d2["same_label_fraction_on_common_owned"]
        delta = a2 - a1
        deltas.append(delta)
        comparison[view] = {
            "common_owned_1m_bars": d1["intersection_1m_bars"],
            "boundary_iou": d1["iou"],
            "D1_same_label_fraction": a1,
            "D2_same_label_fraction": a2,
            "D2_minus_D1": delta,
        }

    result = {
        "schema": "two_wave_envelope_direction_v056_failed_aggregate_diagnostic@1.0",
        "source_formal_run": 34009427027,
        "source_execution_commit": "266bac6389098169598084667fcb46897a53ccf2",
        "formal_gate_failure": "D2 label agreement is systematically lower than D1 on all four native offsets",
        "prefix_zero_rewrite_count": 15,
        "selected_interval_identity_D1_D2": True,
        "comparison": comparison,
        "worse_count": sum(x < 0 for x in deltas),
        "all_four_worse": all(x < 0 for x in deltas),
        "mean_D2_minus_D1": float(np.mean(deltas)),
        "one_minute_data_audit": one_minute_audit,
        "research_verdict_unchanged": "v0.5.6_rejected_by_frozen_multiview_label_stability_gate",
        "trade_authority": False,
        "future_outcome_used": False,
    }
    assert result["worse_count"] == 4 and result["all_four_worse"] is True
    save(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
