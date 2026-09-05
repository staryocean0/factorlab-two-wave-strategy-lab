#!/usr/bin/env python3
"""Diagnostic-only rejection attribution for frozen v0.5.2 qualification."""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import build_ridge_run
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig

VIEW = "5m_offset_0"
FIXED_DAYS = ("2018-06-20", "2019-04-15", "2020-07-15")
FOCUS_CASES = {
    "case_00_A_clear_C_uncertain",
    "case_02_C_new_downtrend",
    "case_11_stable_range",
    "case_14_stable_uptrend",
}


def q(values):
    values = list(values)
    if not values:
        return None
    a = np.asarray(values, dtype=float)
    return {str(x): float(np.quantile(a, x)) for x in (0, .1, .5, .9, .99, 1)}


def interval_overlap(row, lo, hi):
    return row["end_bar"] >= lo and row["start_bar"] <= hi


def feature_row(row):
    cycles = list(map(float, row["cycle_durations"]))
    legs = list(map(float, row["leg_durations"]))
    leg_pairs = [(legs[0], legs[2]), (legs[1], legs[3])]
    corr_ratio = max(max(a, b) / min(a, b) if min(a, b) > 0 else math.inf for a, b in leg_pairs)
    cycle_ratio = max(cycles) / min(cycles) if min(cycles) > 0 else math.inf
    return {
        "birth_scale_level": row["birth_scale_level"],
        "cycle_duration_ratio": cycle_ratio,
        "corresponding_leg_duration_ratio_max": corr_ratio,
        "min_raw_leg_efficiency": min(p["efficiency"] for p in row["leg_paths"]),
        "max_jump_share": max(p["jump_share"] for p in row["leg_paths"]),
        "max_flat_share": max(p["flat_share"] for p in row["leg_paths"]),
        "pair_duration": row["pair_duration"],
    }


def stratify(rows):
    feats = [feature_row(r) for r in rows]
    return {
        "count": len(rows),
        "birth_scale_level_counts": dict(sorted(Counter(f["birth_scale_level"] for f in feats).items())),
        "cycle_duration_ratio_quantiles": q(f["cycle_duration_ratio"] for f in feats),
        "corresponding_leg_duration_ratio_max_quantiles": q(f["corresponding_leg_duration_ratio_max"] for f in feats if np.isfinite(f["corresponding_leg_duration_ratio_max"])),
        "min_raw_leg_efficiency_quantiles": q(f["min_raw_leg_efficiency"] for f in feats),
        "max_jump_share_quantiles": q(f["max_jump_share"] for f in feats),
        "max_flat_share_quantiles": q(f["max_flat_share"] for f in feats),
        "pair_duration_quantiles": q(f["pair_duration"] for f in feats),
    }


def fixed_day_ranges(bars):
    by = {}
    for i, bar in enumerate(bars):
        day = str(bar["trading_day"])
        by.setdefault(day, [i, i])[1] = i
    return {day: by.get(day) for day in FIXED_DAYS}


def load_case_ranges():
    path = ROOT / "cloud_results/two_wave_same_scale_delivery/v04/legacy_case_reaudit.json"
    if not path.exists():
        return {}, {"present": False, "expected_path": str(path.relative_to(ROOT))}
    data = json.loads(path.read_text())
    ranges = {}
    for case in data:
        if case.get("case") in FOCUS_CASES:
            pivots = list(map(int, case["five_occurrence_bars"]))
            ranges[case["case"]] = [pivots[0], pivots[-1]]
    return ranges, {"present": True, "path": str(path.relative_to(ROOT)), "ranges": ranges}


def audit_ranges(records, ranges):
    out = {}
    for label, rng in ranges.items():
        if rng is None:
            out[label] = {"present": False}
            continue
        lo, hi = rng
        rows = [r for r in records if interval_overlap(r, lo, hi)]
        combos = Counter(tuple(r["scale_rejection_reasons"]) for r in rows)
        exclusive = Counter(r["scale_rejection_reasons"][0] for r in rows if len(r["scale_rejection_reasons"]) == 1)
        out[label] = {
            "present": True,
            "bar_range": [lo, hi],
            "overlap": len(rows),
            "qualified": sum(r["scale_qualified"] for r in rows),
            "exclusive_reason_counts": dict(sorted(exclusive.items())),
            "top_rejection_chains": [
                {"reasons": list(k), "count": v}
                for k, v in combos.most_common(12)
            ],
        }
    return out


def main():
    bars, audit = load_development_bars(
        ROOT / f"data/development/{VIEW}.parquet",
        ROOT / "data/manifest.json",
    )
    cfg = MaturityConfig(timeframe=VIEW)
    run = build_ridge_run(bars, cfg)
    records = run.evaluated_records
    reasons = sorted({reason for r in records for reason in r["scale_rejection_reasons"]})
    rejected = [r for r in records if not r["scale_qualified"]]
    total_reason = Counter(reason for r in rejected for reason in r["scale_rejection_reasons"])
    exclusive = Counter(r["scale_rejection_reasons"][0] for r in rejected if len(r["scale_rejection_reasons"]) == 1)
    reason_count_distribution = Counter(len(r["scale_rejection_reasons"]) for r in records)

    pair_rows = []
    n = len(rejected)
    sets = {reason: {i for i, r in enumerate(rejected) if reason in r["scale_rejection_reasons"]} for reason in reasons}
    for a, b in combinations(reasons, 2):
        inter = len(sets[a] & sets[b])
        if not inter:
            continue
        union = len(sets[a] | sets[b])
        pa, pb, pab = len(sets[a]) / n, len(sets[b]) / n, inter / n
        lift = pab / (pa * pb) if pa and pb else None
        pair_rows.append({
            "a": a, "b": b, "count": inter,
            "jaccard": inter / union if union else None,
            "lift": lift,
        })
    pair_rows.sort(key=lambda x: (-x["count"], x["a"], x["b"]))

    near_pass = {reason: [r for r in rejected if r["scale_rejection_reasons"] == [reason]] for reason in reasons}

    summary = {
        "schema": "two_wave_qualification_attribution@1.0",
        "status": "diagnostic_complete_no_rule_changed",
        "view": VIEW,
        "data_audit": audit,
        "parent_identity": "frozen_v0.5.2_exact_ridge_birth",
        "qualification_config_hash": cfg.config_hash,
        "evaluated": len(records),
        "qualified": sum(r["scale_qualified"] for r in records),
        "rejected": len(rejected),
        "selected": len(run.ledger.selected),
        "reason_total_counts": dict(sorted(total_reason.items())),
        "reason_exclusive_only_counts": {reason: exclusive[reason] for reason in reasons},
        "remove_this_reason_only_newly_qualified": {reason: exclusive[reason] for reason in reasons},
        "rejection_count_distribution": {str(k): v for k, v in sorted(reason_count_distribution.items())},
        "exactly_one_reason_near_pass_total": sum(exclusive.values()),
        "near_pass_stratification": {reason: stratify(near_pass[reason]) for reason in reasons},
        "pair_cooccurrence_top": pair_rows[:80],
        "fixed_window_audit": audit_ranges(records, fixed_day_ranges(bars)),
    }
    ranges, case_source = load_case_ranges()
    summary["legacy_case_source"] = case_source
    summary["legacy_case_audit"] = audit_ranges(records, ranges)

    out = ROOT / "cloud_results/two_wave_qualification_attribution"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
