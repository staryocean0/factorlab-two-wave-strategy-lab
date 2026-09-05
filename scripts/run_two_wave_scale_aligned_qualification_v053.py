#!/usr/bin/env python3
"""Main-5m mechanism audit for frozen v0.5.3 qualification ablation; no outcomes."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from factor_lab.visual_structure.two_wave.scale_aligned_qualification_v053 import (
    FROZEN_NUMERICAL_THRESHOLD,
    QUALIFICATION_COMPONENT,
    SCHEMA,
    build_scale_aligned_qualification_run,
)

DEFAULT_VIEW = "5m_offset_0"
CASE_00_BAR_RANGE = (48720, 48801)  # frozen audit range inherited from v0.5.2 result


def quantiles(values):
    values = list(values)
    if not values:
        return None
    arr = np.asarray(values, dtype=float)
    return {str(q): float(np.quantile(arr, q)) for q in (0, 0.1, 0.5, 0.9, 0.99, 1)}


def identity(record):
    return (
        record["ridge_tuple_id"],
        tuple(record["ridge_ids"]),
        tuple(record["five_occurrence_bars"]),
        record["birth_scale_id"],
        record["birth_scale_level"],
        record["confirmation_bar"],
    )


def overlap(record, lo, hi):
    return record["end_bar"] >= lo and record["start_bar"] <= hi


def compact(record):
    return {
        "record_id": record["record_id"],
        "ridge_tuple_id": record["ridge_tuple_id"],
        "classification": record["classification"],
        "raw_five_occurrence_bars": list(record["five_occurrence_bars"]),
        "filtered_occurrence_bars": list(record["filtered_occurrence_bars"]),
        "cycle_durations": list(record["cycle_durations"]),
        "leg_durations": list(record["leg_durations"]),
        "birth_scale_level": record["birth_scale_level"],
        "birth_sigma_bars": record["birth_sigma_bars"],
        "raw_min_leg_efficiency": min(path["efficiency"] for path in record["raw_leg_paths_frozen_v043"]),
        "scale_aligned_min_leg_efficiency": record["scale_aligned_min_leg_efficiency"],
        "scale_qualified": record["scale_qualified"],
        "scale_rejection_reasons": list(record["scale_rejection_reasons"]),
        "selected": record.get("selected", False),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--view", default=DEFAULT_VIEW)
    parser.add_argument("--output", default="cloud_results/two_wave_scale_aligned_qualification_v053_main5m")
    args = parser.parse_args()

    cfg = MaturityConfig(timeframe=args.view)
    assert cfg.min_leg_efficiency == FROZEN_NUMERICAL_THRESHOLD == 0.5
    bars, audit = load_development_bars(
        ROOT / f"data/development/{args.view}.parquet",
        ROOT / "data/manifest.json",
    )
    run = build_scale_aligned_qualification_run(bars, cfg=cfg)
    before = run.base_run.evaluated_records
    after = run.evaluated_records
    assert len(before) == len(after)
    assert [identity(r) for r in before] == [identity(r) for r in after]

    frozen_reasons = {
        "short_leg", "short_cycle", "long_cycle", "long_pair",
        "cycle_duration_mismatch", "corresponding_leg_duration_mismatch",
        "invalid_amplitude", "amplitude_mismatch", "jump_dominated_leg",
        "flat_dominated_leg", "too_many_observed_days", "wall_span_too_long",
        "confirmation_too_late",
    }
    for old, new in zip(before, after):
        old_set, new_set = set(old["scale_rejection_reasons"]), set(new["scale_rejection_reasons"])
        for reason in frozen_reasons:
            assert (reason in old_set) == (reason in new_set), (reason, identity(old))
        assert old_set.symmetric_difference(new_set) <= {"inefficient_leg"}
        assert new["trade_authority"] is False and new["future_outcome_used"] is False

    before_reason_counts = Counter(reason for row in before for reason in row["scale_rejection_reasons"])
    after_reason_counts = Counter(reason for row in after for reason in row["scale_rejection_reasons"])
    only_efficiency_before = [row for row in before if row["scale_rejection_reasons"] == ["inefficient_leg"]]
    after_by_identity = {identity(row): row for row in after}
    released_only_efficiency = [
        after_by_identity[identity(row)] for row in only_efficiency_before
        if after_by_identity[identity(row)]["scale_qualified"]
    ]
    old_qualified = {identity(row) for row in before if row["scale_qualified"]}
    new_qualified = {identity(row) for row in after if row["scale_qualified"]}

    raw_min = [min(path["efficiency"] for path in row["raw_leg_paths_frozen_v043"]) for row in after]
    scale_min = [row["scale_aligned_min_leg_efficiency"] for row in after]

    day_indices = [i for i, bar in enumerate(bars) if bar.get("trading_day") == "2018-06-20"]
    day_range = [min(day_indices), max(day_indices)] if day_indices else None

    def audit_range(lo, hi):
        old_rows = [row for row in before if overlap(row, lo, hi)]
        new_rows = [row for row in run.ledger.records if overlap(row, lo, hi)]
        ranked = sorted(
            new_rows,
            key=lambda row: (
                abs(row["start_bar"] - lo) + abs(row["end_bar"] - hi),
                row["confirmation_bar"], row["record_id"],
            ),
        )
        return {
            "bar_range": [lo, hi],
            "v052_overlap": len(old_rows),
            "v053_overlap": len(new_rows),
            "v052_qualified": sum(row["scale_qualified"] for row in old_rows),
            "v053_qualified": sum(row["scale_qualified"] for row in new_rows),
            "v053_selected": sum(row.get("selected", False) for row in new_rows),
            "nearest_v053_records_not_model_selection": [compact(row) for row in ranked[:8]],
        }

    summary = {
        "schema": SCHEMA,
        "qualification_component": QUALIFICATION_COMPONENT,
        "status": "main5m_mechanism_result_generated_pending_adjudication",
        "operational_baseline": "v0.4.3",
        "parent_identity": "frozen_v0.5.2_exact_ridge_birth",
        "view": args.view,
        "data_audit": audit,
        "frozen_threshold": FROZEN_NUMERICAL_THRESHOLD,
        "candidate_identity_count": len(before),
        "candidate_identity_exact_match": True,
        "v052": {
            "qualified": len(old_qualified),
            "selected": len(run.base_run.ledger.selected),
            "inefficient_leg_rejections": before_reason_counts["inefficient_leg"],
            "rejection_reason_counts": dict(sorted(before_reason_counts.items())),
        },
        "v053": {
            "qualified": len(new_qualified),
            "selected": len(run.ledger.selected),
            "inefficient_leg_rejections": after_reason_counts["inefficient_leg"],
            "rejection_reason_counts": dict(sorted(after_reason_counts.items())),
        },
        "qualification_delta": {
            "newly_qualified": len(new_qualified - old_qualified),
            "lost_qualified": len(old_qualified - new_qualified),
            "only_efficiency_rejected_before": len(only_efficiency_before),
            "only_efficiency_released": len(released_only_efficiency),
        },
        "raw_min_leg_efficiency_quantiles": quantiles(raw_min),
        "birth_scale_min_leg_efficiency_quantiles": quantiles(scale_min),
        "fixed_window_2018_06_20": audit_range(*day_range) if day_range else {"present": False},
        "case_00_fixed_audit": audit_range(*CASE_00_BAR_RANGE),
    }

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
