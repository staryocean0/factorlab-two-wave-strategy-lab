#!/usr/bin/env python3
"""Formal v0.5.1 characteristic-scale morphology experiment; no outcomes/trading."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.characteristic_scale_v051 import (
    GAMMA,
    SCHEMA,
    SELECTOR,
    build_characteristic_run,
)
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig, TemporalMaturityEngine

VIEWS = [f"5m_offset_{i}" for i in range(5)] + ["1m_official"]
PREFIX_FRACTIONS = (0.25, 0.50, 0.75)
FIXED_DAYS = ["2018-06-20", "2019-04-15", "2020-07-15"]
FOCUS_CASES = {
    "case_00_A_clear_C_uncertain",
    "case_02_C_new_downtrend",
    "case_10_stable_range",
    "case_11_stable_range",
    "case_14_stable_uptrend",
}


def save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def quantiles(values):
    arr = np.asarray(list(values), dtype=float)
    if not len(arr):
        return None
    return {str(q): float(np.quantile(arr, q)) for q in (0, 0.5, 0.9, 0.99, 1)}


def run_v043(bars, view):
    engine = TemporalMaturityEngine(MaturityConfig(timeframe=view))
    for bar in bars:
        engine.update(bar)
    return engine


def event_signature(event):
    return (
        event.event_id,
        event.family_id,
        event.level,
        event.scale_id,
        event.feature.occurrence_indices,
        event.feature.confirmation_index,
        event.confirmation_index,
        event.scale_selection_delay_bars,
        event.feature.common_response,
        event.finer_feature.common_response,
        event.coarser_feature.common_response,
    )


def record_signature(record):
    return (
        record["record_id"],
        tuple(record["five_occurrence_bars"]),
        record["confirmation_bar"],
        record["characteristic_scale_level"],
        record["characteristic_scale_id"],
        record["scale_qualified"],
        tuple(record["scale_rejection_reasons"]),
        record["classification"],
        record["selected"],
        record["overlap_suppressed_by"],
    )


def local_pivot_bars(baseline):
    return np.asarray(
        sorted(p["occurrence_bar"] for p in baseline.pivots if not p.get("left_censored", False)),
        dtype=int,
    )


def absorbed_local_count(record, pivot_bars):
    lo, hi = record["start_bar"], record["end_bar"]
    count = int(np.searchsorted(pivot_bars, hi, side="right") - np.searchsorted(pivot_bars, lo, side="left"))
    return count, max(0, count - 5)


def compact_record(record, pivot_bars=None):
    row = {
        "record_id": record["record_id"],
        "classification": record["classification"],
        "raw_five_occurrence_bars": list(record["five_occurrence_bars"]),
        "filtered_occurrence_bars": list(record["filtered_occurrence_bars"]),
        "cycle_durations": list(record["cycle_durations"]),
        "leg_durations": list(record["leg_durations"]),
        "confirmation_bar": record["confirmation_bar"],
        "characteristic_scale_level": record["characteristic_scale_level"],
        "characteristic_scale_id": record["characteristic_scale_id"],
        "characteristic_sigma_bars": record["characteristic_sigma_bars"],
        "scale_selection_delay_bars": record["scale_selection_delay_bars"],
        "confirmation_delay_bars": record["confirmation_delay_bars"],
        "scale_qualified": record["scale_qualified"],
        "scale_rejection_reasons": list(record["scale_rejection_reasons"]),
        "selected": record["selected"],
        "overlap_suppressed_by": record["overlap_suppressed_by"],
    }
    if pivot_bars is not None:
        total, excess = absorbed_local_count(record, pivot_bars)
        row["v043_local_pivots_inside"] = total
        row["v043_excess_local_pivots_beyond_five"] = excess
    return row


def view_summary(run, baseline, bars):
    pivots = local_pivot_bars(baseline)
    projection_valid = sum(row["projection_valid"] for row in run.projection_audit)
    rejection = Counter(row["projection_reason"] for row in run.projection_audit if not row["projection_valid"])
    evaluated = run.ledger.records
    qualified = [row for row in evaluated if row["scale_qualified"]]
    selected = run.ledger.selected
    family_count = len({member.family_id for member in run.family_members})
    selected_absorption = [absorbed_local_count(row, pivots)[1] for row in selected]
    return {
        "bars": len(bars),
        "features_per_scale": [len(rows) for rows in run.features_by_level],
        "family_members": len(run.family_members),
        "families": family_count,
        "characteristic_events": len(run.characteristic_events),
        "projection_valid": projection_valid,
        "projection_invalid": len(run.projection_audit) - projection_valid,
        "projection_invalid_reasons": dict(rejection),
        "evaluated_raw_pairs": len(evaluated),
        "qualified_after_frozen_v043_rules": len(qualified),
        "selected_disjoint": len(selected),
        "selected_labels": dict(Counter(row["classification"] for row in selected)),
        "characteristic_event_scale_counts": dict(Counter(event.level for event in run.characteristic_events)),
        "evaluated_scale_counts": dict(Counter(row["characteristic_scale_level"] for row in evaluated)),
        "qualified_scale_counts": dict(Counter(row["characteristic_scale_level"] for row in qualified)),
        "selected_scale_counts": dict(Counter(row["characteristic_scale_level"] for row in selected)),
        "scale_selection_delay_quantiles": quantiles(event.scale_selection_delay_bars for event in run.characteristic_events),
        "evaluated_total_confirmation_delay_quantiles": quantiles(row["confirmation_delay_bars"] for row in evaluated),
        "selected_total_confirmation_delay_quantiles": quantiles(row["confirmation_delay_bars"] for row in selected),
        "selected_excess_v043_local_pivots_quantiles": quantiles(selected_absorption),
        "selected_with_absorbed_v043_micro_pivots": int(sum(value > 0 for value in selected_absorption)),
        "status": "morphology_replication_not_yet_accepted",
    }


def coverage_and_labels(selected, timestamps):
    mask = np.zeros(len(timestamps), dtype=bool)
    labels = np.full(len(timestamps), "", dtype=object)
    for record in selected:
        start = pd.Timestamp(record["start_time"]).value
        end = pd.Timestamp(record["end_time"]).value
        left = np.searchsorted(timestamps, start, side="right")
        right = np.searchsorted(timestamps, end, side="right")
        mask[left:right] = True
        labels[left:right] = record["classification"]
    return mask, labels


def cross_offset_metrics(series):
    main_mask, main_labels = series["5m_offset_0"]
    out = {}
    for view in [f"5m_offset_{i}" for i in range(1, 5)]:
        mask, labels = series[view]
        inter_mask = main_mask & mask
        union = int(np.sum(main_mask | mask))
        inter = int(np.sum(inter_mask))
        same_label = int(np.sum((main_labels == labels) & inter_mask))
        out[view] = {
            "intersection_1m_bars": inter,
            "union_1m_bars": union,
            "iou": inter / union if union else None,
            "main_owned_fraction": float(np.mean(main_mask)),
            "other_owned_fraction": float(np.mean(mask)),
            "both_uncovered_fraction": float(np.mean(~main_mask & ~mask)),
            "same_label_fraction_on_common_owned": same_label / inter if inter else None,
        }
    return out


def interval_iou(a0, a1, b0, b1):
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = (a1 - a0) + (b1 - b0) - inter
    return inter / union if union else 1.0


def audit_ranges(records, selected, pivot_bars, ranges):
    out = {}
    selected_ids = {row["record_id"] for row in selected}
    for label, interval in ranges.items():
        if interval is None:
            out[label] = {"present": False}
            continue
        lo, hi = interval
        overlapping = [row for row in records if row["end_bar"] >= lo and row["start_bar"] <= hi]
        ranked = sorted(
            overlapping,
            key=lambda row: interval_iou(lo, hi, row["start_bar"], row["end_bar"]),
            reverse=True,
        )
        out[label] = {
            "present": True,
            "bar_range": [lo, hi],
            "evaluated_overlap_count": len(overlapping),
            "qualified_overlap_count": sum(row["scale_qualified"] for row in overlapping),
            "selected_overlap_count": sum(row["record_id"] in selected_ids for row in overlapping),
            "top_interval_overlaps_not_model_selection": [
                {
                    **compact_record(row, pivot_bars),
                    "reference_interval_iou_not_model_selection": interval_iou(lo, hi, row["start_bar"], row["end_bar"]),
                }
                for row in ranked[:5]
            ],
            "selected": [compact_record(row, pivot_bars) for row in overlapping if row["record_id"] in selected_ids],
        }
    return out


def fixed_day_ranges(bars):
    by_day = {}
    for i, bar in enumerate(bars):
        day = str(bar.get("trading_day"))
        if day not in by_day:
            by_day[day] = [i, i]
        by_day[day][1] = i
    return {day: by_day.get(day) for day in FIXED_DAYS}


def legacy_ranges(path):
    if not path.exists():
        return {}, {"present": False}
    cases = json.loads(path.read_text())
    ranges = {}
    source_rows = []
    for case in cases:
        if case["case"] in FOCUS_CASES:
            pivots = list(map(int, case["five_occurrence_bars"]))
            ranges[case["case"]] = [pivots[0], pivots[-1]]
            source_rows.append(
                {
                    "case": case["case"],
                    "five_occurrence_bars": pivots,
                    "cycle_bars": case.get("cycle_bars"),
                    "leg_bars": case.get("leg_bars"),
                }
            )
    return ranges, {"present": True, "source": str(path.relative_to(ROOT)), "cases": source_rows}


def baseline_summary(engine, n):
    selected = engine.ledger.selected
    owned = sum(row["pair_duration"] for row in selected)
    return {
        "candidates": len(engine.ledger.records),
        "qualified": sum(row["scale_qualified"] for row in engine.ledger.records),
        "selected_disjoint": len(selected),
        "selected_labels": dict(Counter(row["classification"] for row in selected)),
        "owned_fraction_not_accuracy": owned / n,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "cloud_results/two_wave_characteristic_scale_v051")
    parser.add_argument("--views", nargs="+", default=VIEWS)
    args = parser.parse_args()

    sources = [
        Path(__file__),
        ROOT / "src/factor_lab/visual_structure/two_wave/characteristic_scale_v051.py",
        ROOT / "tests/unit/test_two_wave_characteristic_scale_v051.py",
        ROOT / "docs/research/two_wave_characteristic_scale_protocol_v051.md",
    ]
    summary = {
        "schema": "two_wave_characteristic_scale_experiment@0.5.1",
        "component_schema": SCHEMA,
        "selector": SELECTOR,
        "gamma": GAMMA,
        "status": "experiment_running_not_prejudged",
        "operational_baseline": "v0.4.3",
        "changed_component_only": "tcss_characteristic_scale_identity_and_raw_projection",
        "qualification_changed": False,
        "d1_changed": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "fresh_oos": False,
        "old_12_48_used_in_scale_selection": False,
        "old_12_48_role": "downstream_frozen_qualification_only",
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources
        },
        "views": {},
        "prefix_checks": [],
    }

    bars_by_view = {}
    baseline_by_view = {}
    run_by_view = {}

    for view in args.views:
        bars, audit = load_development_bars(
            ROOT / f"data/development/{view}.parquet",
            ROOT / "data/manifest.json",
        )
        cfg = MaturityConfig(timeframe=view)
        baseline = run_v043(bars, view)
        run = build_characteristic_run(bars, cfg)
        if view == "5m_offset_0":
            base_tuple = (
                len(baseline.ledger.records),
                sum(row["scale_qualified"] for row in baseline.ledger.records),
                len(baseline.ledger.selected),
            )
            assert base_tuple == (4706, 341, 212), base_tuple

        # General safety consequences of the unchanged qualification layer.
        assert all(row["scale_qualified"] for row in run.ledger.selected)
        assert all(
            cfg.min_cycle <= min(row["cycle_durations"]) <= max(row["cycle_durations"]) <= cfg.max_cycle
            and row["pair_duration"] <= cfg.max_pair
            for row in run.ledger.selected
        )

        summary["views"][view] = {
            "data_audit": audit,
            "v043": baseline_summary(baseline, len(bars)),
            "v051": view_summary(run, baseline, bars),
        }
        bars_by_view[view] = bars
        baseline_by_view[view] = baseline
        run_by_view[view] = run
        save(args.output / "summary.json", summary)

        for fraction in PREFIX_FRACTIONS:
            n = int(len(bars) * fraction)
            prefix = build_characteristic_run(bars[:n], MaturityConfig(timeframe=view))
            expected_events = [event_signature(event) for event in run.characteristic_events if event.confirmation_index < n]
            assert [event_signature(event) for event in prefix.characteristic_events] == expected_events
            expected_records = [record_signature(row) for row in run.ledger.records if row["confirmation_bar"] < n]
            assert [record_signature(row) for row in prefix.ledger.records] == expected_records
            expected_selected = [record_signature(row) for row in run.ledger.selected if row["confirmation_bar"] < n]
            assert [record_signature(row) for row in prefix.ledger.selected] == expected_selected
            summary["prefix_checks"].append(
                {
                    "view": view,
                    "fraction": fraction,
                    "bars": n,
                    "characteristic_events": len(prefix.characteristic_events),
                    "evaluated_records": len(prefix.ledger.records),
                    "selected": len(prefix.ledger.selected),
                    "confirmed_rewrite_count": 0,
                    "passed": True,
                }
            )
            save(args.output / "summary.json", summary)

        print(
            "VIEW_DONE",
            view,
            "char", len(run.characteristic_events),
            "eval", len(run.ledger.records),
            "qual", sum(row["scale_qualified"] for row in run.ledger.records),
            "selected", len(run.ledger.selected),
            flush=True,
        )

    assert len(summary["prefix_checks"]) == 3 * len(args.views)
    assert all(row["passed"] and row["confirmed_rewrite_count"] == 0 for row in summary["prefix_checks"])

    five_views = [f"5m_offset_{i}" for i in range(5)]
    if all(view in run_by_view for view in five_views) and "1m_official" in bars_by_view:
        one_minute_ns = np.asarray(
            [pd.Timestamp(bar["timestamp"]).value for bar in bars_by_view["1m_official"]],
            dtype=np.int64,
        )
        baseline_series = {
            view: coverage_and_labels(baseline_by_view[view].ledger.selected, one_minute_ns)
            for view in five_views
        }
        v051_series = {
            view: coverage_and_labels(run_by_view[view].ledger.selected, one_minute_ns)
            for view in five_views
        }
        summary["native_5m_offset_stability"] = {
            "v043": cross_offset_metrics(baseline_series),
            "v051": cross_offset_metrics(v051_series),
            "mapping_basis": "existing 1m timestamps only; no price resampling",
            "iou_role": "boundary_stability_not_accuracy",
        }

    if "5m_offset_0" in run_by_view:
        bars = bars_by_view["5m_offset_0"]
        baseline = baseline_by_view["5m_offset_0"]
        run = run_by_view["5m_offset_0"]
        pivots = local_pivot_bars(baseline)
        summary["fixed_window_audit"] = audit_ranges(
            run.ledger.records,
            run.ledger.selected,
            pivots,
            fixed_day_ranges(bars),
        )
        legacy_path = ROOT / "cloud_results/two_wave_same_scale_delivery/v04/legacy_case_reaudit.json"
        ranges, source = legacy_ranges(legacy_path)
        summary["legacy_case_source"] = source
        summary["legacy_case_audit"] = audit_ranges(
            run.ledger.records,
            run.ledger.selected,
            pivots,
            ranges,
        )

    summary["status"] = "formal_v051_results_generated_pending_adjudication"
    save(args.output / "summary.json", summary)
    print("PREFIX_CHECKS", len(summary["prefix_checks"]), "all_passed", flush=True)
    if "5m_offset_0" in summary["views"]:
        print("MAIN_V051", json.dumps(summary["views"]["5m_offset_0"], ensure_ascii=False), flush=True)
    if "native_5m_offset_stability" in summary:
        print("OFFSET_STABILITY", json.dumps(summary["native_5m_offset_stability"], ensure_ascii=False), flush=True)
    if "legacy_case_audit" in summary:
        print("CASE00", json.dumps(summary["legacy_case_audit"].get("case_00_A_clear_C_uncertain"), ensure_ascii=False), flush=True)
        print("CASE02", json.dumps(summary["legacy_case_audit"].get("case_02_C_new_downtrend"), ensure_ascii=False), flush=True)
    print("STUDY_COMPLETE", args.output, flush=True)


if __name__ == "__main__":
    main()
