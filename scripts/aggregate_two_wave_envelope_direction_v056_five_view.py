#!/usr/bin/env python3
"""Aggregate frozen v0.5.6 native-5m shards without re-running any recognizer."""
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


def load_payloads(root: Path):
    summaries, coverages = {}, {}
    for path in root.rglob("summary.json"):
        payload = json.loads(path.read_text())
        if payload.get("schema") != "two_wave_envelope_direction_native5m_view@0.5.6":
            continue
        view = payload["view"]
        if view in summaries:
            raise AssertionError(f"duplicate summary for {view}: {path}")
        summaries[view] = payload
    for path in root.rglob("coverage.json"):
        payload = json.loads(path.read_text())
        if payload.get("schema") != "two_wave_envelope_direction_native5m_coverage@0.5.6":
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
        default=ROOT / "cloud_results/two_wave_envelope_direction_v056_five_view/final_summary.json",
    )
    args = parser.parse_args()

    summaries, coverages = load_payloads(args.input_root)
    prefix_checks = [row for view in VIEWS for row in summaries[view]["prefix_checks"]]
    assert len(prefix_checks) == 15
    assert all(row["passed"] and row["confirmed_rewrite_count"] == 0 for row in prefix_checks)
    assert all(summaries[v]["upstream_identity_exact_match"] for v in VIEWS)
    assert all(summaries[v]["selected_record_ids_exact_match"] for v in VIEWS)
    assert all(summaries[v]["selected_intervals_exact_match"] for v in VIEWS)

    one_minute_bars, one_minute_audit = load_development_bars(
        ROOT / "data/development/1m_official.parquet", ROOT / "data/manifest.json"
    )
    timestamps = np.asarray(
        [pd.Timestamp(bar["timestamp"]).value for bar in one_minute_bars], dtype=np.int64
    )

    series = {"D1": {}, "D2": {}}
    per_view_interval_identity = {}
    for view in VIEWS:
        d1_rows, d2_rows = coverages[view]["D1"], coverages[view]["D2"]
        d1_ids = [row["record_id"] for row in d1_rows]
        d2_ids = [row["record_id"] for row in d2_rows]
        d1_bounds = [(row["start_time"], row["end_time"]) for row in d1_rows]
        d2_bounds = [(row["start_time"], row["end_time"]) for row in d2_rows]
        assert d1_ids == d2_ids
        assert d1_bounds == d2_bounds
        series["D1"][view] = coverage_and_labels(d1_rows, timestamps)
        series["D2"][view] = coverage_and_labels(d2_rows, timestamps)
        d1_mask, _ = series["D1"][view]
        d2_mask, _ = series["D2"][view]
        assert np.array_equal(d1_mask, d2_mask)
        per_view_interval_identity[view] = True

    metrics = {
        "D1": cross_offset_metrics(series["D1"]),
        "D2": cross_offset_metrics(series["D2"]),
    }
    agreement = {}
    deltas = []
    for view in VIEWS[1:]:
        d1 = metrics["D1"][view]
        d2 = metrics["D2"][view]
        assert d1["intersection_1m_bars"] == d2["intersection_1m_bars"]
        assert d1["union_1m_bars"] == d2["union_1m_bars"]
        assert d1["iou"] == d2["iou"]
        a1 = d1["same_label_fraction_on_common_owned"]
        a2 = d2["same_label_fraction_on_common_owned"]
        delta = None if a1 is None or a2 is None else a2 - a1
        if delta is not None:
            deltas.append(delta)
        agreement[view] = {
            "common_owned_1m_bars": d1["intersection_1m_bars"],
            "D1_same_label_fraction": a1,
            "D2_same_label_fraction": a2,
            "D2_minus_D1": delta,
            "boundary_iou_identical": True,
            "iou": d1["iou"],
        }

    worse_count = sum(delta < 0 for delta in deltas)
    all_four_worse = len(deltas) == 4 and worse_count == 4
    if all_four_worse:
        raise AssertionError("D2 label agreement is systematically lower than D1 on all four native offsets")

    final = {
        "schema": "two_wave_envelope_direction_five_view_adjudication@0.5.6",
        "status": "five_view_passed_pending_1m_causal_adjudication",
        "upstream": "v0.5.2_exact_ridge_plus_v0.5.4_full_cycle_qualification",
        "changed_component_only": "D2_whole_parent_envelope_translation",
        "views": summaries,
        "prefix_checks": prefix_checks,
        "prefix_zero_rewrite_count": 15,
        "selected_interval_identity": per_view_interval_identity,
        "native_5m": {
            "D1_cross_offset": metrics["D1"],
            "D2_cross_offset": metrics["D2"],
            "label_agreement_comparison": agreement,
            "D2_agreement_worse_count": worse_count,
            "D2_agreement_all_four_worse": all_four_worse,
            "mean_D2_minus_D1_label_agreement": float(np.mean(deltas)) if deltas else None,
            "boundary_iou_exactly_identical_D1_D2": True,
            "boundary_iou_role": "stability_not_accuracy",
            "mapping_basis": "existing shipped 1m timestamps only; no price resampling",
            "one_minute_data_audit": one_minute_audit,
        },
        "trade_authority": False,
        "fresh_oos": False,
    }
    save(args.output, final)
    print(json.dumps(final, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
