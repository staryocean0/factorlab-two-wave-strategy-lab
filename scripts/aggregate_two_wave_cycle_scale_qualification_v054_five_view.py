#!/usr/bin/env python3
"""Aggregate already-computed v0.5.4 native-5m view artifacts.

No model is executed here. The script only combines per-view summaries and maps
selected intervals onto the shipped 1m timestamps to reproduce the frozen
cross-offset coverage/label IoU diagnostic used by v0.5.2.
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
from run_two_wave_extremum_ridge_v052 import coverage_and_labels, cross_offset_metrics, save

VIEWS = [f"5m_offset_{i}" for i in range(5)]
VERSIONS = ("v043", "v052", "v054")


def load_payloads(root: Path):
    summaries = {}
    coverages = {}
    for path in root.rglob("summary.json"):
        payload = json.loads(path.read_text())
        if payload.get("schema") != "two_wave_cycle_scale_qualification_native5m_view@0.5.4":
            continue
        view = payload["view"]
        if view in summaries:
            raise AssertionError(f"duplicate summary for {view}: {path}")
        summaries[view] = payload
    for path in root.rglob("coverage.json"):
        payload = json.loads(path.read_text())
        if payload.get("schema") != "two_wave_cycle_scale_qualification_native5m_coverage@0.5.4":
            continue
        view = payload["view"]
        if view in coverages:
            raise AssertionError(f"duplicate coverage for {view}: {path}")
        coverages[view] = payload
    assert sorted(summaries) == VIEWS, sorted(summaries)
    assert sorted(coverages) == VIEWS, sorted(coverages)
    return summaries, coverages


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "cloud_results/two_wave_cycle_scale_qualification_v054_five_view/final_summary.json",
    )
    args = parser.parse_args()

    summaries, coverages = load_payloads(args.input_root)
    prefix_checks = [
        row
        for view in VIEWS
        for row in summaries[view]["prefix_checks"]
    ]
    assert len(prefix_checks) == 15
    assert all(
        row["passed"] and row["confirmed_rewrite_count"] == 0
        for row in prefix_checks
    )
    assert all(summaries[view]["candidate_identity_exact_match"] for view in VIEWS)

    one_minute_bars, one_minute_audit = load_development_bars(
        ROOT / "data/development/1m_official.parquet",
        ROOT / "data/manifest.json",
    )
    one_minute_ns = np.asarray(
        [pd.Timestamp(bar["timestamp"]).value for bar in one_minute_bars],
        dtype=np.int64,
    )

    stability = {}
    for version in VERSIONS:
        series = {
            view: coverage_and_labels(coverages[view][version], one_minute_ns)
            for view in VIEWS
        }
        stability[version] = cross_offset_metrics(series)

    deltas = {}
    for view in VIEWS[1:]:
        before = stability["v052"][view]["iou"]
        after = stability["v054"][view]["iou"]
        deltas[view] = {
            "v052_iou": before,
            "v054_iou": after,
            "delta": None if before is None or after is None else after - before,
        }
    numeric_deltas = [row["delta"] for row in deltas.values() if row["delta"] is not None]

    final = {
        "schema": "two_wave_cycle_scale_qualification_five_view_adjudication@0.5.4",
        "status": "five_view_results_generated_pending_final_adjudication",
        "operational_baseline": "v0.4.3",
        "parent_identity": "frozen_v0.5.2_exact_ridge_birth",
        "changed_component_only": "corresponding_leg_duration_mismatch_hard_gate_to_diagnostic",
        "views": summaries,
        "prefix_checks": prefix_checks,
        "prefix_zero_rewrite_count": 15,
        "native_5m_offset_stability": {
            **stability,
            "v054_minus_v052": deltas,
            "worse_count": sum(delta < 0 for delta in numeric_deltas),
            "all_four_worse": len(numeric_deltas) == 4 and all(delta < 0 for delta in numeric_deltas),
            "mean_iou_delta": float(np.mean(numeric_deltas)) if numeric_deltas else None,
            "mapping_basis": "existing 1m timestamps only; no price resampling; 1m recognizer not run in this aggregation",
            "one_minute_data_audit": one_minute_audit,
            "iou_role": "boundary_stability_not_accuracy",
        },
        "trade_authority": False,
        "fresh_oos": False,
    }
    save(args.output, final)
    print(json.dumps(final, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
