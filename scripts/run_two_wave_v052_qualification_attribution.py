#!/usr/bin/env python3
"""Read-only v0.5.2 qualification failure attribution.

This script does NOT change thresholds, formulas, D1, ledger ordering, ridge
identity, tuple birth, raw projection, or any production output.  It reruns the
frozen v0.5.2 candidate pipeline and decomposes the already-observed rejection
reasons so that a later v0.5.3 protocol can freeze exactly one qualification
component on ex-ante evidence rather than case-by-case tuning.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import build_ridge_run
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from run_two_wave_extremum_ridge_v052 import (
    absorbed_local_count,
    fixed_day_ranges,
    legacy_ranges,
    local_pivot_bars,
    run_v043,
    save,
)

VIEWS = [f"5m_offset_{i}" for i in range(5)]
OUTPUT = ROOT / "cloud_results/two_wave_v052_qualification_attribution"


def _counter(rows):
    return {str(k): int(v) for k, v in sorted(Counter(rows).items(), key=lambda kv: (-kv[1], str(kv[0])))}


def _signature_counter(records):
    signatures = ["+".join(sorted(row["scale_rejection_reasons"])) for row in records if row["scale_rejection_reasons"]]
    return _counter(signatures)


def _reason_frequency(records):
    reasons = Counter()
    for row in records:
        reasons.update(row["scale_rejection_reasons"])
    return {str(k): int(v) for k, v in sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))}


def _single_reason(records):
    return _counter(row["scale_rejection_reasons"][0] for row in records if len(row["scale_rejection_reasons"]) == 1)


def _birth_level_summary(records):
    out = {}
    levels = sorted({int(row["birth_scale_level"]) for row in records})
    for level in levels:
        subset = [row for row in records if int(row["birth_scale_level"]) == level]
        rejected = [row for row in subset if not row["scale_qualified"]]
        out[str(level)] = {
            "records": len(subset),
            "qualified": sum(bool(row["scale_qualified"]) for row in subset),
            "rejected": len(rejected),
            "reason_frequency": _reason_frequency(rejected),
            "single_reason_count": _single_reason(rejected),
        }
    return out


def _compact_record(row, pivots):
    total, excess = absorbed_local_count(row, pivots)
    return {
        "record_id": row["record_id"],
        "start_bar": row["start_bar"],
        "end_bar": row["end_bar"],
        "five_occurrence_bars": list(row["five_occurrence_bars"]),
        "leg_durations": list(row["leg_durations"]),
        "cycle_durations": list(row["cycle_durations"]),
        "birth_scale_level": int(row["birth_scale_level"]),
        "birth_sigma_bars": float(row["birth_sigma_bars"]),
        "reasons": list(row["scale_rejection_reasons"]),
        "qualified": bool(row["scale_qualified"]),
        "v043_local_pivots_inside": int(total),
        "v043_excess_local_pivots_beyond_five": int(excess),
        "raw_leg_efficiencies": [float(path["efficiency"]) for path in row["leg_paths"]],
        "raw_jump_shares": [float(path["jump_share"]) for path in row["leg_paths"]],
    }


def _interval_iou(a0, a1, b0, b1):
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = (a1 - a0) + (b1 - b0) - inter
    return inter / union if union else 1.0


def _range_audit(records, pivots, ranges):
    out = {}
    for label, interval in ranges.items():
        if interval is None:
            out[label] = {"present": False}
            continue
        lo, hi = interval
        overlapping = [row for row in records if row["end_bar"] >= lo and row["start_bar"] <= hi]
        ranked = sorted(overlapping, key=lambda row: _interval_iou(lo, hi, row["start_bar"], row["end_bar"]), reverse=True)
        out[label] = {
            "present": True,
            "bar_range": [int(lo), int(hi)],
            "overlap_count": len(overlapping),
            "reason_frequency": _reason_frequency([row for row in overlapping if not row["scale_qualified"]]),
            "single_reason_count": _single_reason([row for row in overlapping if not row["scale_qualified"]]),
            "top_interval_overlaps_not_model_selection": [
                {**_compact_record(row, pivots), "reference_interval_iou_not_model_selection": _interval_iou(lo, hi, row["start_bar"], row["end_bar"])}
                for row in ranked[:10]
            ],
        }
    return out


def _view_attribution(view, bars, run, baseline):
    records = run.ledger.records
    pivots = local_pivot_bars(baseline)
    rejected = [row for row in records if not row["scale_qualified"]]
    absorbed = []
    absorbed_rejected = []
    for row in records:
        _, excess = absorbed_local_count(row, pivots)
        if excess > 0:
            absorbed.append(row)
            if not row["scale_qualified"]:
                absorbed_rejected.append(row)

    single = _single_reason(rejected)
    single_absorbed = _single_reason(absorbed_rejected)
    reason_freq = _reason_frequency(rejected)
    reason_freq_absorbed = _reason_frequency(absorbed_rejected)

    return {
        "view": view,
        "bars": len(bars),
        "evaluated": len(records),
        "qualified": sum(bool(row["scale_qualified"]) for row in records),
        "rejected": len(rejected),
        "records_absorbing_v043_micro_pivots": len(absorbed),
        "rejected_absorbing_v043_micro_pivots": len(absorbed_rejected),
        "reason_frequency": reason_freq,
        "single_reason_count": single,
        "leave_one_reason_out_new_qualified": single,
        "top_reason_signatures": dict(list(_signature_counter(rejected).items())[:30]),
        "absorbed_reason_frequency": reason_freq_absorbed,
        "absorbed_single_reason_count": single_absorbed,
        "absorbed_leave_one_reason_out_new_qualified": single_absorbed,
        "top_absorbed_reason_signatures": dict(list(_signature_counter(absorbed_rejected).items())[:30]),
        "birth_level_summary": _birth_level_summary(records),
    }, pivots


def main():
    summary = {
        "schema": "two_wave_v052_qualification_failure_attribution@1.0",
        "research_logic": "frozen_v052_candidates_read_only_rejection_decomposition",
        "operational_baseline": "v0.4.3",
        "threshold_or_formula_changes": False,
        "views": {},
        "status": "running_not_prejudged",
    }

    main_records = None
    main_pivots = None
    main_bars = None
    for view in VIEWS:
        bars, audit = load_development_bars(
            ROOT / f"data/development/{view}.parquet",
            ROOT / "data/manifest.json",
        )
        cfg = MaturityConfig(timeframe=view)
        baseline = run_v043(bars, view)
        run = build_ridge_run(bars, cfg)
        attribution, pivots = _view_attribution(view, bars, run, baseline)
        summary["views"][view] = {"data_audit": audit, **attribution}
        save(OUTPUT / "summary.json", summary)
        print(
            "VIEW_ATTRIBUTION", view,
            "eval", attribution["evaluated"],
            "qual", attribution["qualified"],
            "absorbed", attribution["records_absorbing_v043_micro_pivots"],
            "single", json.dumps(attribution["single_reason_count"], sort_keys=True),
            flush=True,
        )
        if view == "5m_offset_0":
            main_records = run.ledger.records
            main_pivots = pivots
            main_bars = bars

    assert main_records is not None and main_pivots is not None and main_bars is not None
    legacy_path = ROOT / "cloud_results/two_wave_same_scale_delivery/v04/legacy_case_reaudit.json"
    legacy, source = legacy_ranges(legacy_path)
    summary["main_5m_fixed_windows"] = _range_audit(main_records, main_pivots, fixed_day_ranges(main_bars))
    summary["main_5m_legacy_case_source"] = source
    summary["main_5m_legacy_cases"] = _range_audit(main_records, main_pivots, legacy)

    # Cross-view consistency of the one-gate counterfactual.  This is the key
    # pre-protocol signal; it is descriptive only and does not select a threshold.
    all_reasons = sorted({
        reason
        for view in summary["views"].values()
        for reason in view["reason_frequency"]
    })
    summary["cross_view_single_failure_matrix"] = {
        reason: {
            view: int(summary["views"][view]["single_reason_count"].get(reason, 0))
            for view in VIEWS
        }
        for reason in all_reasons
    }
    summary["cross_view_absorbed_single_failure_matrix"] = {
        reason: {
            view: int(summary["views"][view]["absorbed_single_reason_count"].get(reason, 0))
            for view in VIEWS
        }
        for reason in all_reasons
    }
    summary["status"] = "attribution_complete_no_qualification_change"
    save(OUTPUT / "summary.json", summary)
    print("ATTRIBUTION_COMPLETE", OUTPUT, flush=True)


if __name__ == "__main__":
    main()
