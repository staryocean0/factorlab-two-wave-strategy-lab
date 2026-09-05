#!/usr/bin/env python3
"""Main-5m mechanism audit for frozen v0.5.4 cycle-scale qualification."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.cycle_scale_qualification_v054 import (
    REMOVED_HARD_REASON,
    build_cycle_scale_qualification_run,
)
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig

VIEW = "5m_offset_0"
FIXED_DAYS = ("2018-06-20", "2019-04-15", "2020-07-15")
FOCUS_CASES = {
    "case_00_A_clear_C_uncertain",
    "case_02_C_new_downtrend",
    "case_11_stable_range",
    "case_14_stable_uptrend",
}


def identity(record):
    return (
        record["ridge_tuple_id"],
        tuple(record["ridge_ids"]),
        tuple(record["five_occurrence_bars"]),
        record["birth_scale_id"],
        record["birth_scale_level"],
        record["confirmation_bar"],
    )


def q(values):
    vals = list(values)
    if not vals:
        return None
    arr = np.asarray(vals, dtype=float)
    return {str(x): float(np.quantile(arr, x)) for x in (0, .1, .5, .9, .99, 1)}


def feature(record):
    legs = [float(x) for x in record["leg_durations"]]
    cycles = [float(x) for x in record["cycle_durations"]]
    corr = [max(legs[0], legs[2]) / min(legs[0], legs[2]), max(legs[1], legs[3]) / min(legs[1], legs[3])]
    return {
        "birth_scale_level": record["birth_scale_level"],
        "birth_sigma_bars": record["birth_sigma_bars"],
        "cycle_ratio": max(cycles) / min(cycles),
        "corresponding_leg_ratio_max": max(corr),
        "min_raw_leg_efficiency": min(p["efficiency"] for p in record["leg_paths"]),
        "max_jump_share": max(p["jump_share"] for p in record["leg_paths"]),
        "pair_duration": record["pair_duration"],
    }


def summarize_features(records):
    feats = [feature(r) for r in records]
    return {
        "count": len(records),
        "birth_scale_level_counts": dict(sorted(Counter(f["birth_scale_level"] for f in feats).items())),
        "cycle_ratio_quantiles": q(f["cycle_ratio"] for f in feats),
        "corresponding_leg_ratio_max_quantiles": q(f["corresponding_leg_ratio_max"] for f in feats),
        "min_raw_leg_efficiency_quantiles": q(f["min_raw_leg_efficiency"] for f in feats),
        "max_jump_share_quantiles": q(f["max_jump_share"] for f in feats),
        "pair_duration_quantiles": q(f["pair_duration"] for f in feats),
    }


def compact(old, new):
    return {
        "ridge_tuple_id": old["ridge_tuple_id"],
        "raw_five_occurrence_bars": list(old["five_occurrence_bars"]),
        "filtered_occurrence_bars": list(old["filtered_occurrence_bars"]),
        "cycle_durations": list(old["cycle_durations"]),
        "leg_durations": list(old["leg_durations"]),
        "birth_scale_level": old["birth_scale_level"],
        "birth_sigma_bars": old["birth_sigma_bars"],
        "v052_reasons": list(old["scale_rejection_reasons"]),
        "v054_reasons": list(new["scale_rejection_reasons"]),
        "v054_classification": new["classification"],
        "v054_selected": bool(new.get("selected", False)),
        **feature(old),
    }


def day_ranges(bars):
    out = {}
    for day in FIXED_DAYS:
        idx = [i for i, bar in enumerate(bars) if str(bar["trading_day"]) == day]
        out[day] = [min(idx), max(idx)] if idx else None
    return out


def case_ranges():
    path = ROOT / "cloud_results/two_wave_same_scale_delivery/v04/legacy_case_reaudit.json"
    if not path.exists():
        return {}, {"present": False, "expected_path": str(path.relative_to(ROOT))}
    rows = json.loads(path.read_text())
    ranges = {}
    for row in rows:
        if row.get("case") in FOCUS_CASES:
            bars = list(map(int, row["five_occurrence_bars"]))
            ranges[row["case"]] = [bars[0], bars[-1]]
    return ranges, {"present": True, "path": str(path.relative_to(ROOT)), "ranges": ranges}


def overlaps(record, lo, hi):
    return record["end_bar"] >= lo and record["start_bar"] <= hi


def audit_range(before, after, rng):
    if rng is None:
        return {"present": False}
    lo, hi = rng
    old_rows = [r for r in before if overlaps(r, lo, hi)]
    new_by = {identity(r): r for r in after}
    old_newly = [r for r in old_rows if r["scale_rejection_reasons"] == [REMOVED_HARD_REASON]]
    pairs = [(r, new_by[identity(r)]) for r in old_newly]
    all_new_rows = [r for r in after if overlaps(r, lo, hi)]
    return {
        "present": True,
        "bar_range": [lo, hi],
        "overlap": len(old_rows),
        "v052_qualified": sum(r["scale_qualified"] for r in old_rows),
        "v054_qualified": sum(r["scale_qualified"] for r in all_new_rows),
        "duration_only_newly_qualified": len(pairs),
        "duration_only_records": [compact(old, new) for old, new in pairs[:20]],
    }


def main():
    bars, data_audit = load_development_bars(
        ROOT / f"data/development/{VIEW}.parquet",
        ROOT / "data/manifest.json",
    )
    cfg = MaturityConfig(timeframe=VIEW)
    run = build_cycle_scale_qualification_run(bars, cfg=cfg)
    before = run.base_run.evaluated_records
    after = run.evaluated_records
    assert len(before) == len(after)
    assert [identity(r) for r in before] == [identity(r) for r in after]

    new_by = {identity(r): r for r in after}
    old_qualified = {identity(r) for r in before if r["scale_qualified"]}
    new_qualified = {identity(r) for r in after if r["scale_qualified"]}
    duration_only = {identity(r) for r in before if r["scale_rejection_reasons"] == [REMOVED_HARD_REASON]}
    newly = new_qualified - old_qualified
    lost = old_qualified - new_qualified

    # Single-component hard invariant: every candidate can differ only by the
    # one predeclared reason, and all old qualified records remain qualified.
    for old, new in zip(before, after):
        old_reasons = list(old["scale_rejection_reasons"])
        expected = [r for r in old_reasons if r != REMOVED_HARD_REASON]
        assert new["scale_rejection_reasons"] == expected
        assert new["trade_authority"] is False and new["future_outcome_used"] is False
    assert not lost
    assert newly == duration_only

    newly_old = [r for r in before if identity(r) in newly]
    ranges, source = case_ranges()
    summary = {
        "schema": "two_wave_cycle_scale_qualification_main5m@0.5.4",
        "status": "main5m_result_generated_pending_adjudication",
        "operational_baseline": "v0.4.3",
        "parent_identity": "frozen_v0.5.2_exact_ridge_birth",
        "view": VIEW,
        "data_audit": data_audit,
        "qualification_config_hash": cfg.config_hash,
        "candidate_identity_exact_match": True,
        "evaluated": len(before),
        "v052": {"qualified": len(old_qualified), "selected": len(run.base_run.ledger.selected)},
        "v054": {"qualified": len(new_qualified), "selected": len(run.ledger.selected)},
        "delta": {
            "newly_qualified": len(newly),
            "lost_qualified": len(lost),
            "matches_frozen_duration_only_set": newly == duration_only,
        },
        "newly_qualified_features": summarize_features(newly_old),
        "fixed_window_audit": {
            label: audit_range(before, after, rng)
            for label, rng in day_ranges(bars).items()
        },
        "legacy_case_source": source,
        "legacy_case_audit": {
            label: audit_range(before, after, rng)
            for label, rng in ranges.items()
        },
    }
    out = ROOT / "cloud_results/two_wave_cycle_scale_qualification_v054_main5m"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
