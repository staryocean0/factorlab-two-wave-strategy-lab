#!/usr/bin/env python3
"""Read-only ablation of the legacy raw path-efficiency qualification gate.

The frozen v0.5.2 exact-ridge candidate identity and all other qualification
reasons are preserved.  Only `inefficient_leg` is removed from a deep-copied
record, then the unchanged CharacteristicExclusiveLedger is replayed.
No outcomes or trading authority are used.
"""
from __future__ import annotations

import copy
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

from factor_lab.visual_structure.two_wave.characteristic_scale_v051 import CharacteristicExclusiveLedger
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import build_ridge_run
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from run_two_wave_extremum_ridge_v052 import (
    absorbed_local_count,
    audit_ranges,
    coverage_and_labels,
    cross_offset_metrics,
    fixed_day_ranges,
    legacy_ranges,
    local_pivot_bars,
    quantiles,
    run_v043,
    save,
)

VIEWS = [f"5m_offset_{i}" for i in range(5)]
OUTPUT = ROOT / "cloud_results/two_wave_legacy_er_redundancy_poc_v053"
IDENTITY_FIELDS = (
    "record_id",
    "ridge_tuple_id",
    "ridge_ids",
    "five_occurrence_bars",
    "birth_scale_level",
    "birth_scale_id",
    "birth_sigma_bars",
    "confirmation_bar",
    "known_at",
    "start_bar",
    "end_bar",
)


def _remove_legacy_er(record: dict) -> dict:
    out = copy.deepcopy(record)
    before = list(out["scale_rejection_reasons"])
    after = [reason for reason in before if reason != "inefficient_leg"]
    out["scale_rejection_reasons"] = after
    out["legacy_raw_er_gate_ablated_for_poc"] = True
    out["legacy_raw_er_original_reasons"] = before
    out["legacy_raw_er_original_efficiencies"] = [float(path["efficiency"]) for path in out["leg_paths"]]
    out["scale_qualified"] = not after
    out["classification"] = out["geometric_direction_diagnostic"] if out["scale_qualified"] else "not_same_scale"
    return out


def build_no_er_ledger(run):
    modified = [_remove_legacy_er(row) for row in run.evaluated_records]
    ledger = CharacteristicExclusiveLedger()
    ledger.add_records(modified)
    return ledger


def _assert_isolated_change(run, ledger):
    original = {row["record_id"]: row for row in run.evaluated_records}
    altered = {row["record_id"]: row for row in ledger.records}
    assert set(original) == set(altered)

    expected_new = set()
    actual_new = set()
    for record_id, before in original.items():
        after = altered[record_id]
        for field in IDENTITY_FIELDS:
            assert after[field] == before[field], (record_id, field)
        before_other = [r for r in before["scale_rejection_reasons"] if r != "inefficient_leg"]
        assert after["scale_rejection_reasons"] == before_other, record_id
        assert after["scale_qualified"] == (len(before_other) == 0), record_id
        if before["scale_qualified"]:
            assert after["scale_qualified"], record_id
        if before["scale_rejection_reasons"] == ["inefficient_leg"]:
            expected_new.add(record_id)
        if after["scale_qualified"] and not before["scale_qualified"]:
            actual_new.add(record_id)
    assert actual_new == expected_new, (len(actual_new), len(expected_new))
    return expected_new


def _absorption_stats(records, pivots):
    values = [absorbed_local_count(row, pivots)[1] for row in records]
    parent = sum(value > 0 for value in values)
    return {
        "records": len(records),
        "parent_like_absorbed_micro": int(parent),
        "parent_like_fraction": parent / len(records) if records else None,
        "excess_micro_quantiles": quantiles(values),
    }


def _raw_er_stats(records):
    mins = [min(float(path["efficiency"]) for path in row["leg_paths"]) for row in records]
    return {
        "min_raw_er_quantiles": quantiles(mins),
        "below_0_5": int(sum(value < 0.5 for value in mins)),
        "below_0_25": int(sum(value < 0.25 for value in mins)),
    }


def _birth_levels(records):
    return {str(k): int(v) for k, v in sorted(Counter(int(row["birth_scale_level"]) for row in records).items())}


def _other_reason_counts(records):
    counts = Counter()
    for row in records:
        for reason in row["scale_rejection_reasons"]:
            if reason != "inefficient_leg":
                counts[reason] += 1
    return {str(k): int(v) for k, v in sorted(counts.items())}


def _view_summary(run, ledger, baseline):
    pivots = local_pivot_bars(baseline)
    original_records = run.ledger.records
    original_selected = run.ledger.selected
    noer_records = ledger.records
    noer_selected = ledger.selected

    original_qualified = [row for row in original_records if row["scale_qualified"]]
    noer_qualified = [row for row in noer_records if row["scale_qualified"]]
    before_q = {row["record_id"] for row in original_qualified}
    before_s = {row["record_id"] for row in original_selected}
    new_q = [row for row in noer_qualified if row["record_id"] not in before_q]
    new_s = [row for row in noer_selected if row["record_id"] not in before_s]
    displaced_s = [row for row in original_selected if row["record_id"] not in {x["record_id"] for x in noer_selected}]

    before_other = _other_reason_counts(run.evaluated_records)
    after_other = _other_reason_counts(noer_records)
    assert before_other == after_other

    return {
        "evaluated_identity_count": len(noer_records),
        "qualified_before_v052": len(original_qualified),
        "qualified_after_no_er": len(noer_qualified),
        "newly_qualified": len(new_q),
        "selected_before_v052": len(original_selected),
        "selected_after_no_er": len(noer_selected),
        "newly_selected": len(new_s),
        "previously_selected_displaced_by_ledger": len(displaced_s),
        "labels_before": dict(Counter(row["classification"] for row in original_selected)),
        "labels_after": dict(Counter(row["classification"] for row in noer_selected)),
        "birth_levels_before_selected": _birth_levels(original_selected),
        "birth_levels_after_selected": _birth_levels(noer_selected),
        "birth_levels_newly_selected": _birth_levels(new_s),
        "other_rejection_reason_counts_unchanged": before_other,
        "existing_qualified": _absorption_stats(original_qualified, pivots),
        "newly_qualified": _absorption_stats(new_q, pivots),
        "final_qualified": _absorption_stats(noer_qualified, pivots),
        "existing_selected": _absorption_stats(original_selected, pivots),
        "newly_selected": _absorption_stats(new_s, pivots),
        "final_selected": _absorption_stats(noer_selected, pivots),
        "newly_selected_raw_er": _raw_er_stats(new_s),
        "final_selected_raw_er": _raw_er_stats(noer_selected),
        "newly_selected_pair_duration_quantiles": quantiles(row["pair_duration"] for row in new_s),
        "newly_selected_leg_duration_quantiles": quantiles(
            duration for row in new_s for duration in row["leg_durations"]
        ),
    }


def _proxy_run(run, ledger):
    return SimpleNamespace(tuple_births=run.tuple_births, ledger=ledger)


def _find_exact(records, five):
    target = tuple(five)
    return [row for row in records if tuple(row["five_occurrence_bars"]) == target]


def main():
    summary = {
        "schema": "two_wave_legacy_raw_er_redundancy_ablation@0.5.3-preprotocol",
        "research_logic": "remove_only_inefficient_leg_from_frozen_v052_records",
        "operational_baseline": "v0.4.3",
        "candidate_parent_identity": "v0.5.2_exact_ridge_tuple_birth",
        "qualification_component_changed": "legacy_raw_er_gate_presence_only",
        "other_thresholds_changed": False,
        "d1_changed": False,
        "ledger_changed": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "views": {},
        "status": "running_not_prejudged",
    }

    one_minute_bars, one_min_audit = load_development_bars(
        ROOT / "data/development/1m_official.parquet", ROOT / "data/manifest.json"
    )
    minute_ns = np.asarray([pd.Timestamp(bar["timestamp"]).value for bar in one_minute_bars], dtype=np.int64)
    summary["offset_mapping_data_audit"] = one_min_audit

    run_by_view = {}
    noer_by_view = {}
    baseline_by_view = {}
    bars_by_view = {}

    for view in VIEWS:
        bars, audit = load_development_bars(
            ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json"
        )
        cfg = MaturityConfig(timeframe=view)
        baseline = run_v043(bars, view)
        run = build_ridge_run(bars, cfg)
        ledger = build_no_er_ledger(run)
        expected_new = _assert_isolated_change(run, ledger)
        assert len(expected_new) == sum(
            row["scale_rejection_reasons"] == ["inefficient_leg"] for row in run.evaluated_records
        )

        summary["views"][view] = {
            "data_audit": audit,
            **_view_summary(run, ledger, baseline),
        }
        run_by_view[view] = run
        noer_by_view[view] = ledger
        baseline_by_view[view] = baseline
        bars_by_view[view] = bars
        save(OUTPUT / "summary.json", summary)
        print(
            "VIEW_NOER", view,
            "q", summary["views"][view]["qualified_before_v052"], "->", summary["views"][view]["qualified_after_no_er"],
            "s", summary["views"][view]["selected_before_v052"], "->", summary["views"][view]["selected_after_no_er"],
            "new_parent_q", summary["views"][view]["newly_qualified"]["parent_like_fraction"],
            "new_parent_s", summary["views"][view]["newly_selected"]["parent_like_fraction"],
            flush=True,
        )

    v052_series = {
        view: coverage_and_labels(run_by_view[view].ledger.selected, minute_ns) for view in VIEWS
    }
    noer_series = {
        view: coverage_and_labels(noer_by_view[view].selected, minute_ns) for view in VIEWS
    }
    summary["native_5m_offset_stability"] = {
        "v052": cross_offset_metrics(v052_series),
        "no_legacy_er": cross_offset_metrics(noer_series),
        "mapping_basis": "existing 1m timestamps only; no price resampling",
        "iou_role": "boundary_stability_not_accuracy",
    }

    main_view = "5m_offset_0"
    main_run = run_by_view[main_view]
    main_noer = noer_by_view[main_view]
    main_baseline = baseline_by_view[main_view]
    main_bars = bars_by_view[main_view]
    pivots = local_pivot_bars(main_baseline)
    proxy = _proxy_run(main_run, main_noer)

    summary["fixed_window_audit"] = audit_ranges(proxy, pivots, fixed_day_ranges(main_bars))
    legacy_path = ROOT / "cloud_results/two_wave_same_scale_delivery/v04/legacy_case_reaudit.json"
    ranges, source = legacy_ranges(legacy_path)
    summary["legacy_case_source"] = source
    summary["legacy_case_audit"] = audit_ranges(proxy, pivots, ranges)

    target = [48720, 48749, 48754, 48768, 48801]
    exact = _find_exact(main_noer.records, target)
    assert exact, "case_00 exact parent record disappeared"
    summary["case00_exact_parent_after_no_er"] = [
        {
            "record_id": row["record_id"],
            "five_occurrence_bars": list(row["five_occurrence_bars"]),
            "remaining_reasons": list(row["scale_rejection_reasons"]),
            "scale_qualified": bool(row["scale_qualified"]),
            "selected": bool(row["selected"]),
            "raw_leg_efficiencies": [float(path["efficiency"]) for path in row["leg_paths"]],
        }
        for row in exact
    ]
    for row in exact:
        assert row["scale_rejection_reasons"] == [
            "corresponding_leg_duration_mismatch", "jump_dominated_leg"
        ], row["scale_rejection_reasons"]
        assert not row["scale_qualified"] and not row["selected"]

    case02 = summary["legacy_case_audit"].get("case_02_C_new_downtrend", {})
    case11 = summary["legacy_case_audit"].get("case_11_stable_range", {})
    case14 = summary["legacy_case_audit"].get("case_14_stable_uptrend", {})
    summary["safety_assertions"] = {
        "case00_still_rejected_by_duration_and_jump": True,
        "case02_selected_count": case02.get("selected_count"),
        "case11_selected_count": case11.get("selected_count"),
        "case14_selected_count": case14.get("selected_count"),
    }

    summary["status"] = "legacy_er_redundancy_ablation_complete_pending_adjudication"
    save(OUTPUT / "summary.json", summary)
    print("OFFSET", json.dumps(summary["native_5m_offset_stability"], ensure_ascii=False), flush=True)
    print("CASE00", json.dumps(summary["case00_exact_parent_after_no_er"], ensure_ascii=False), flush=True)
    print("LEGACY_ER_REDUNDANCY_POC_COMPLETE", OUTPUT, flush=True)


if __name__ == "__main__":
    main()
