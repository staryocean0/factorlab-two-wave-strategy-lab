#!/usr/bin/env python3
"""Formal v0.5.3 single-component confirmation; no outcomes or trading."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.legacy_er_v053 import (
    CHANGED_COMPONENT,
    REMOVED_REASON,
    SCHEMA,
    LegacyEROverlayRun,
    build_legacy_er_run_v053,
)
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from run_two_wave_extremum_ridge_v052 import (
    absorbed_local_count,
    audit_ranges,
    coverage_and_labels,
    cross_offset_metrics,
    fixed_day_ranges,
    legacy_ranges,
    local_pivot_bars,
    prefix_check as v052_prefix_check,
    quantiles,
    run_v043,
    save,
)

VIEWS = [f"5m_offset_{i}" for i in range(5)] + ["1m_official"]
FIVE_VIEWS = [f"5m_offset_{i}" for i in range(5)]
PREFIX_FRACTIONS = (0.25, 0.50, 0.75)
FINGERPRINT = {
    "5m_offset_0": (780, 431),
    "5m_offset_1": (714, 396),
    "5m_offset_2": (700, 387),
    "5m_offset_3": (737, 394),
    "5m_offset_4": (764, 411),
}


def _v053_signature(row: dict):
    return (
        row["record_id"],
        row["ridge_tuple_id"],
        tuple(row["ridge_ids"]),
        tuple(row["five_occurrence_bars"]),
        row["confirmation_bar"],
        row["birth_scale_level"],
        row["birth_scale_id"],
        row["scale_qualified"],
        tuple(row["scale_rejection_reasons"]),
        row["classification"],
        row["selected"],
        row["overlap_suppressed_by"],
        tuple(row["legacy_raw_er_original_reasons"]),
        tuple(round(float(x), 15) for x in row["legacy_raw_er_audit_values"]),
        row["legacy_raw_er_parent_gate_active"],
    )


def _signatures(records, cutoff: int):
    return [_v053_signature(row) for row in records if row["confirmation_bar"] < cutoff]


def _identity_signature(row: dict):
    return (
        row["record_id"],
        row["ridge_tuple_id"],
        tuple(row["ridge_ids"]),
        tuple(row["five_occurrence_bars"]),
        row["birth_scale_level"],
        row["birth_scale_id"],
        row["birth_sigma_bars"],
        row["confirmation_bar"],
        row["known_at"],
        row["start_bar"],
        row["end_bar"],
    )


def assert_single_component_isolation(run: LegacyEROverlayRun):
    before = {row["record_id"]: row for row in run.base_run.ledger.records}
    after = {row["record_id"]: row for row in run.ledger.records}
    assert set(before) == set(after)

    expected_new = set()
    actual_new = set()
    for record_id, old in before.items():
        new = after[record_id]
        assert _identity_signature(new) == _identity_signature(old), record_id
        expected_reasons = [reason for reason in old["scale_rejection_reasons"] if reason != REMOVED_REASON]
        assert new["scale_rejection_reasons"] == expected_reasons, record_id
        assert new["scale_qualified"] == (not expected_reasons), record_id
        assert new["legacy_raw_er_original_reasons"] == old["scale_rejection_reasons"], record_id
        old_er = [float(path["efficiency"]) for path in old["leg_paths"]]
        new_er = [float(path["efficiency"]) for path in new["leg_paths"]]
        assert new_er == old_er == new["legacy_raw_er_audit_values"], record_id
        if old["scale_qualified"]:
            assert new["scale_qualified"], record_id
        if old["scale_rejection_reasons"] == [REMOVED_REASON]:
            expected_new.add(record_id)
        if new["scale_qualified"] and not old["scale_qualified"]:
            actual_new.add(record_id)
    assert actual_new == expected_new
    return expected_new


def prefix_check(full: LegacyEROverlayRun, prefix: LegacyEROverlayRun, cutoff: int):
    base_checks = v052_prefix_check(full.base_run, prefix.base_run, cutoff)
    checks = {
        "v052_ridge_and_projection": all(base_checks.values()),
        "v053_evaluated_records": _signatures(prefix.ledger.records, cutoff)
        == _signatures(full.ledger.records, cutoff),
        "v053_selected_records": _signatures(prefix.ledger.selected, cutoff)
        == _signatures(full.ledger.selected, cutoff),
    }
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise AssertionError(f"v0.5.3 prefix rewrite at cutoff={cutoff}: {failed}")
    return {**{f"v052_{k}": v for k, v in base_checks.items()}, **checks}


def _absorption(records, pivots):
    values = [absorbed_local_count(row, pivots)[1] for row in records]
    count = sum(value > 0 for value in values)
    return {
        "records": len(records),
        "parent_like_absorbed_micro": int(count),
        "parent_like_fraction": count / len(records) if records else None,
        "excess_micro_quantiles": quantiles(values),
    }


def view_summary(run: LegacyEROverlayRun, baseline):
    pivots = local_pivot_bars(baseline)
    before_records = run.base_run.ledger.records
    after_records = run.ledger.records
    before_q = [row for row in before_records if row["scale_qualified"]]
    after_q = [row for row in after_records if row["scale_qualified"]]
    before_s = run.base_run.ledger.selected
    after_s = run.ledger.selected
    before_q_ids = {row["record_id"] for row in before_q}
    before_s_ids = {row["record_id"] for row in before_s}
    new_q = [row for row in after_q if row["record_id"] not in before_q_ids]
    new_s = [row for row in after_s if row["record_id"] not in before_s_ids]
    displaced = [row for row in before_s if row["record_id"] not in {x["record_id"] for x in after_s}]
    return {
        "evaluated": len(after_records),
        "v052_qualified": len(before_q),
        "v053_qualified": len(after_q),
        "v052_selected": len(before_s),
        "v053_selected": len(after_s),
        "newly_qualified": _absorption(new_q, pivots),
        "newly_selected": _absorption(new_s, pivots),
        "v052_qualified_absorption": _absorption(before_q, pivots),
        "v053_qualified_absorption": _absorption(after_q, pivots),
        "v052_selected_absorption": _absorption(before_s, pivots),
        "v053_selected_absorption": _absorption(after_s, pivots),
        "previously_selected_displaced_by_ledger": len(displaced),
        "v052_labels": dict(Counter(row["classification"] for row in before_s)),
        "v053_labels": dict(Counter(row["classification"] for row in after_s)),
        "v053_selected_birth_levels": dict(Counter(str(row["birth_scale_level"]) for row in after_s)),
        "v053_selected_min_raw_er_quantiles": quantiles(
            min(float(path["efficiency"]) for path in row["leg_paths"]) for row in after_s
        ),
    }


def _proxy(run: LegacyEROverlayRun):
    return SimpleNamespace(tuple_births=run.base_run.tuple_births, ledger=run.ledger)


def _exact(records, five):
    target = tuple(five)
    return [row for row in records if tuple(row["five_occurrence_bars"]) == target]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "cloud_results/two_wave_legacy_er_v053")
    parser.add_argument("--views", nargs="+", default=VIEWS)
    parser.add_argument("--skip-offset-stability", action="store_true")
    args = parser.parse_args()

    summary = {
        "schema": SCHEMA,
        "changed_component_only": CHANGED_COMPONENT,
        "operational_baseline": "v0.4.3",
        "parent_identity": "v0.5.2_exact_ridge_tuple_birth",
        "other_qualification_changed": False,
        "d1_changed": False,
        "ledger_policy_changed": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "views": {},
        "prefix_checks": [],
        "status": "formal_v053_running_not_prejudged",
    }

    bars_by_view = {}
    baseline_by_view = {}
    run_by_view = {}

    for view in args.views:
        bars, audit = load_development_bars(
            ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json"
        )
        cfg = MaturityConfig(timeframe=view)
        baseline = run_v043(bars, view)
        run = build_legacy_er_run_v053(bars, cfg)
        new_ids = assert_single_component_isolation(run)

        if view in FINGERPRINT:
            fingerprint = (
                sum(row["scale_qualified"] for row in run.ledger.records),
                len(run.ledger.selected),
            )
            assert fingerprint == FINGERPRINT[view], (view, fingerprint, FINGERPRINT[view])

        assert all(row["scale_qualified"] for row in run.ledger.selected)
        assert all(
            cfg.min_cycle <= min(row["cycle_durations"]) <= max(row["cycle_durations"]) <= cfg.max_cycle
            and row["pair_duration"] <= cfg.max_pair
            for row in run.ledger.selected
        )

        summary["views"][view] = {
            "data_audit": audit,
            "newly_qualified_identity_count": len(new_ids),
            **view_summary(run, baseline),
        }
        bars_by_view[view] = bars
        baseline_by_view[view] = baseline
        run_by_view[view] = run
        save(args.output / "summary.json", summary)

        for fraction in PREFIX_FRACTIONS:
            cutoff = int(len(bars) * fraction)
            prefix = build_legacy_er_run_v053(bars[:cutoff], MaturityConfig(timeframe=view))
            assert_single_component_isolation(prefix)
            checks = prefix_check(run, prefix, cutoff)
            summary["prefix_checks"].append(
                {
                    "view": view,
                    "fraction": fraction,
                    "bars": cutoff,
                    **checks,
                    "confirmed_rewrite_count": 0,
                    "passed": True,
                }
            )
            save(args.output / "summary.json", summary)

        print(
            "VIEW_V053", view,
            "eval", len(run.ledger.records),
            "q", sum(row["scale_qualified"] for row in run.ledger.records),
            "s", len(run.ledger.selected),
            "new_q", len(new_ids),
            flush=True,
        )

    assert len(summary["prefix_checks"]) == len(args.views) * len(PREFIX_FRACTIONS)
    assert all(row["passed"] and row["confirmed_rewrite_count"] == 0 for row in summary["prefix_checks"])

    if not args.skip_offset_stability and all(view in run_by_view for view in FIVE_VIEWS):
        minute_bars, minute_audit = load_development_bars(
            ROOT / "data/development/1m_official.parquet", ROOT / "data/manifest.json"
        )
        minute_ns = np.asarray([pd.Timestamp(row["timestamp"]).value for row in minute_bars], dtype=np.int64)
        v052_series = {
            view: coverage_and_labels(run_by_view[view].base_run.ledger.selected, minute_ns)
            for view in FIVE_VIEWS
        }
        v053_series = {
            view: coverage_and_labels(run_by_view[view].ledger.selected, minute_ns)
            for view in FIVE_VIEWS
        }
        summary["offset_mapping_data_audit"] = minute_audit
        summary["native_5m_offset_stability"] = {
            "v052": cross_offset_metrics(v052_series),
            "v053": cross_offset_metrics(v053_series),
            "mapping_basis": "existing 1m timestamps only; no price resampling",
            "iou_role": "boundary_stability_not_accuracy",
        }
        expected_iou = {
            "5m_offset_1": 0.43333776222743847,
            "5m_offset_2": 0.3743405904811868,
            "5m_offset_3": 0.40041896474689986,
            "5m_offset_4": 0.4497153278178098,
        }
        for view, expected in expected_iou.items():
            actual = summary["native_5m_offset_stability"]["v053"][view]["iou"]
            assert abs(actual - expected) < 1e-12, (view, actual, expected)

    if "5m_offset_0" in run_by_view:
        run = run_by_view["5m_offset_0"]
        baseline = baseline_by_view["5m_offset_0"]
        bars = bars_by_view["5m_offset_0"]
        pivots = local_pivot_bars(baseline)
        proxy = _proxy(run)
        summary["fixed_window_audit"] = audit_ranges(proxy, pivots, fixed_day_ranges(bars))
        legacy_path = ROOT / "cloud_results/two_wave_same_scale_delivery/v04/legacy_case_reaudit.json"
        ranges, source = legacy_ranges(legacy_path)
        summary["legacy_case_source"] = source
        summary["legacy_case_audit"] = audit_ranges(proxy, pivots, ranges)

        exact = _exact(run.ledger.records, [48720, 48749, 48754, 48768, 48801])
        assert exact
        for row in exact:
            assert row["scale_rejection_reasons"] == [
                "corresponding_leg_duration_mismatch",
                "jump_dominated_leg",
            ]
            assert not row["scale_qualified"] and not row["selected"]
        summary["case00_exact_parent"] = [
            {
                "record_id": row["record_id"],
                "remaining_reasons": list(row["scale_rejection_reasons"]),
                "scale_qualified": row["scale_qualified"],
                "selected": row["selected"],
            }
            for row in exact
        ]
        case02 = summary["legacy_case_audit"]["case_02_C_new_downtrend"]
        assert case02["qualified_overlap_count"] == 0
        assert case02["selected_overlap_count"] == 0

    summary["status"] = "formal_v053_results_generated_pending_adjudication"
    save(args.output / "summary.json", summary)
    print("PREFIX_CHECKS", len(summary["prefix_checks"]), "all_passed", flush=True)
    if "native_5m_offset_stability" in summary:
        print("OFFSET_V053", json.dumps(summary["native_5m_offset_stability"], ensure_ascii=False), flush=True)
    print("V053_FORMAL_COMPLETE", args.output, flush=True)


if __name__ == "__main__":
    main()
