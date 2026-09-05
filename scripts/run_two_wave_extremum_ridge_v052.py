#!/usr/bin/env python3
"""Formal v0.5.2 extremum-ridge morphology experiment; no outcomes/trading."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import (
    RAW_PROJECTION,
    REPRESENTATION,
    SCHEMA,
    STRUCTURAL_SCALE_RULE,
    build_ridge_run,
)
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


def local_pivot_bars(baseline):
    return np.asarray(
        sorted(p["occurrence_bar"] for p in baseline.pivots if not p.get("left_censored", False)),
        dtype=int,
    )


def absorbed_local_count(record, pivot_bars):
    lo, hi = record["start_bar"], record["end_bar"]
    count = int(np.searchsorted(pivot_bars, hi, side="right") - np.searchsorted(pivot_bars, lo, side="left"))
    return count, max(0, count - 5)


def _ridge_node_signatures(run, cutoff):
    rows = []
    for level_rows in run.ridge_nodes_by_level:
        for row in level_rows:
            if row.node.confirmation_index < cutoff:
                rows.append(
                    (
                        row.node.level,
                        row.node.node_id,
                        row.ridge_id,
                        row.root_node_id,
                        row.node.kind,
                        row.node.occurrence_index,
                        row.node.confirmation_index,
                        row.node.corrected_occurrence,
                    )
                )
    return sorted(rows)


def _edge_signatures(run, cutoff):
    return sorted(
        (
            row.fine_level,
            row.coarse_level,
            row.fine_node_id,
            row.coarse_node_id,
            row.ridge_id,
            row.confirmation_index,
            row.corrected_occurrence_distance,
        )
        for row in run.edges
        if row.confirmation_index < cutoff
    )


def _death_signatures(run, cutoff):
    return sorted(
        (
            row.fine_level,
            row.coarse_level,
            row.fine_node_id,
            row.ridge_id,
            row.kind,
            row.occurrence_index,
            row.confirmation_index,
            row.reason,
        )
        for row in run.deaths
        if row.confirmation_index < cutoff
    )


def _anomaly_signatures(run, cutoff):
    return sorted(
        (
            row.coarse_level,
            row.coarse_node_id,
            row.kind,
            row.occurrence_index,
            row.confirmation_index,
            row.reason,
        )
        for row in run.lineage_anomalies
        if row.confirmation_index < cutoff
    )


def _birth_signatures(run, cutoff):
    return sorted(
        (
            row.event_id,
            row.tuple_id,
            row.level,
            row.scale_id,
            row.ridge_ids,
            row.occurrence_indices,
            tuple(sorted(death.ridge_id for death in row.internal_child_deaths)),
            row.confirmation_index,
            row.prior_internal_ridge_count,
        )
        for row in run.tuple_births
        if row.confirmation_index < cutoff
    )


def _projection_signatures(run, cutoff):
    rows = []
    for row in run.projection_audit:
        if row["birth_confirmation_bar"] >= cutoff:
            continue
        rows.append(
            (
                row["event_id"],
                row["tuple_id"],
                row["birth_level"],
                tuple(row["ridge_ids"]),
                tuple(row["filtered_occurrence_bars"]),
                row["birth_confirmation_bar"],
                row["projection_valid"],
                row["projection_reason"],
                tuple(row.get("raw_occurrence_bars", [])),
            )
        )
    return sorted(rows)


def _record_signature(row):
    return (
        row["record_id"],
        row["ridge_tuple_id"],
        tuple(row["ridge_ids"]),
        tuple(row["five_occurrence_bars"]),
        row["confirmation_bar"],
        row["birth_scale_level"],
        row["birth_scale_id"],
        row["internal_child_death_count"],
        tuple(row["internal_child_ridge_ids"]),
        row["scale_qualified"],
        tuple(row["scale_rejection_reasons"]),
        row["classification"],
        row["selected"],
        row["overlap_suppressed_by"],
    )


def _record_signatures(records, cutoff):
    return [_record_signature(row) for row in records if row["confirmation_bar"] < cutoff]


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


def tuple_survival_levels(run):
    appearances = defaultdict(list)
    for level_rows in run.tuples_by_level:
        for row in level_rows:
            appearances[row.tuple_id].append(row.level)
    return {
        birth.tuple_id: len([level for level in appearances[birth.tuple_id] if level >= birth.level])
        for birth in run.tuple_births
    }


def view_summary(run, baseline, bars):
    pivots = local_pivot_bars(baseline)
    evaluated = run.ledger.records
    qualified = [row for row in evaluated if row["scale_qualified"]]
    selected = run.ledger.selected
    projection_valid = sum(row["projection_valid"] for row in run.projection_audit)
    projection_reasons = Counter(row["projection_reason"] for row in run.projection_audit if not row["projection_valid"])
    coarse_node_count = sum(len(rows) for rows in run.ridge_nodes_by_level[1:])
    absorption_eval = [absorbed_local_count(row, pivots)[1] for row in evaluated]
    absorption_qual = [absorbed_local_count(row, pivots)[1] for row in qualified]
    absorption_selected = [absorbed_local_count(row, pivots)[1] for row in selected]
    survival = tuple_survival_levels(run)
    birth_survival = [survival[row.tuple_id] for row in run.tuple_births]
    edge_distances = [row.corrected_occurrence_distance for row in run.edges]
    internal_deaths = [len(row.internal_child_deaths) for row in run.tuple_births]

    anomalies_by_level = Counter(row.coarse_level for row in run.lineage_anomalies)
    births_by_level = Counter(row.level for row in run.tuple_births)
    selected_by_level = Counter(row["birth_scale_level"] for row in selected)
    return {
        "bars": len(bars),
        "extremum_nodes_per_scale": [len(rows) for rows in run.nodes_by_level],
        "ridge_nodes_per_scale": [len(rows) for rows in run.ridge_nodes_by_level],
        "exact_tuples_per_scale": [len(rows) for rows in run.tuples_by_level],
        "ridge_edges": len(run.edges),
        "ridge_deaths": len(run.deaths),
        "lineage_anomalies": len(run.lineage_anomalies),
        "lineage_anomaly_fraction_of_coarse_nodes": len(run.lineage_anomalies) / coarse_node_count if coarse_node_count else None,
        "lineage_anomalies_by_level": {str(k): int(v) for k, v in sorted(anomalies_by_level.items())},
        "ridge_edge_corrected_distance_quantiles": quantiles(edge_distances),
        "tuple_births": len(run.tuple_births),
        "tuple_birth_counts_by_level": {str(k): int(v) for k, v in sorted(births_by_level.items())},
        "tuple_birth_internal_child_death_quantiles": quantiles(internal_deaths),
        "tuple_birth_survival_levels_quantiles": quantiles(birth_survival),
        "projection_valid": projection_valid,
        "projection_invalid": len(run.projection_audit) - projection_valid,
        "projection_invalid_reasons": dict(projection_reasons),
        "evaluated_raw_pairs": len(evaluated),
        "qualified_after_frozen_v043_rules": len(qualified),
        "selected_disjoint": len(selected),
        "selected_labels": dict(Counter(row["classification"] for row in selected)),
        "selected_birth_scale_counts": {str(k): int(v) for k, v in sorted(selected_by_level.items())},
        "evaluated_total_confirmation_delay_quantiles": quantiles(row["confirmation_delay_bars"] for row in evaluated),
        "selected_total_confirmation_delay_quantiles": quantiles(row["confirmation_delay_bars"] for row in selected),
        "evaluated_excess_v043_local_pivots_quantiles": quantiles(absorption_eval),
        "qualified_excess_v043_local_pivots_quantiles": quantiles(absorption_qual),
        "selected_excess_v043_local_pivots_quantiles": quantiles(absorption_selected),
        "qualified_with_absorbed_v043_micro_pivots": int(sum(value > 0 for value in absorption_qual)),
        "selected_with_absorbed_v043_micro_pivots": int(sum(value > 0 for value in absorption_selected)),
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
        common = main_mask & mask
        union = int(np.sum(main_mask | mask))
        inter = int(np.sum(common))
        same = int(np.sum((main_labels == labels) & common))
        out[view] = {
            "intersection_1m_bars": inter,
            "union_1m_bars": union,
            "iou": inter / union if union else None,
            "main_owned_fraction": float(np.mean(main_mask)),
            "other_owned_fraction": float(np.mean(mask)),
            "both_uncovered_fraction": float(np.mean(~main_mask & ~mask)),
            "same_label_fraction_on_common_owned": same / inter if inter else None,
        }
    return out


def interval_iou(a0, a1, b0, b1):
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = (a1 - a0) + (b1 - b0) - inter
    return inter / union if union else 1.0


def compact_record(record, pivot_bars=None):
    row = {
        "record_id": record["record_id"],
        "ridge_tuple_id": record["ridge_tuple_id"],
        "ridge_ids": list(record["ridge_ids"]),
        "classification": record["classification"],
        "raw_five_occurrence_bars": list(record["five_occurrence_bars"]),
        "filtered_occurrence_bars": list(record["filtered_occurrence_bars"]),
        "cycle_durations": list(record["cycle_durations"]),
        "leg_durations": list(record["leg_durations"]),
        "confirmation_bar": record["confirmation_bar"],
        "birth_scale_level": record["birth_scale_level"],
        "birth_scale_id": record["birth_scale_id"],
        "birth_sigma_bars": record["birth_sigma_bars"],
        "tuple_birth_delay_bars": record["tuple_birth_delay_bars"],
        "internal_child_death_count": record["internal_child_death_count"],
        "prior_internal_ridge_count": record["prior_internal_ridge_count"],
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


def compact_birth(birth):
    return {
        "event_id": birth.event_id,
        "tuple_id": birth.tuple_id,
        "birth_level": birth.level,
        "birth_scale_id": birth.scale_id,
        "birth_sigma_bars": birth.sigma_bars,
        "ridge_ids": list(birth.ridge_ids),
        "filtered_occurrence_bars": list(birth.occurrence_indices),
        "confirmation_bar": birth.confirmation_index,
        "internal_child_death_count": len(birth.internal_child_deaths),
        "internal_child_death_occurrences": [row.occurrence_index for row in birth.internal_child_deaths],
        "prior_internal_ridge_count": birth.prior_internal_ridge_count,
    }


def audit_ranges(run, pivot_bars, ranges):
    records = run.ledger.records
    selected = run.ledger.selected
    selected_ids = {row["record_id"] for row in selected}
    out = {}
    for label, interval in ranges.items():
        if interval is None:
            out[label] = {"present": False}
            continue
        lo, hi = interval
        births = [row for row in run.tuple_births if row.occurrence_indices[-1] >= lo and row.occurrence_indices[0] <= hi]
        overlapping = [row for row in records if row["end_bar"] >= lo and row["start_bar"] <= hi]
        ranked = sorted(
            overlapping,
            key=lambda row: interval_iou(lo, hi, row["start_bar"], row["end_bar"]),
            reverse=True,
        )
        out[label] = {
            "present": True,
            "bar_range": [lo, hi],
            "tuple_birth_overlap_count": len(births),
            "evaluated_overlap_count": len(overlapping),
            "qualified_overlap_count": sum(row["scale_qualified"] for row in overlapping),
            "selected_overlap_count": sum(row["record_id"] in selected_ids for row in overlapping),
            "top_tuple_births_not_model_selection": [compact_birth(row) for row in births[:8]],
            "top_interval_overlaps_not_model_selection": [
                {
                    **compact_record(row, pivot_bars),
                    "reference_interval_iou_not_model_selection": interval_iou(lo, hi, row["start_bar"], row["end_bar"]),
                }
                for row in ranked[:8]
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


def prefix_check(full, prefix, cutoff):
    checks = {
        "ridge_nodes": _ridge_node_signatures(prefix, cutoff) == _ridge_node_signatures(full, cutoff),
        "ridge_edges": _edge_signatures(prefix, cutoff) == _edge_signatures(full, cutoff),
        "ridge_deaths": _death_signatures(prefix, cutoff) == _death_signatures(full, cutoff),
        "lineage_anomalies": _anomaly_signatures(prefix, cutoff) == _anomaly_signatures(full, cutoff),
        "tuple_births": _birth_signatures(prefix, cutoff) == _birth_signatures(full, cutoff),
        "raw_projection": _projection_signatures(prefix, cutoff) == _projection_signatures(full, cutoff),
        "evaluated_records": _record_signatures(prefix.ledger.records, cutoff) == _record_signatures(full.ledger.records, cutoff),
        "selected_records": _record_signatures(prefix.ledger.selected, cutoff) == _record_signatures(full.ledger.selected, cutoff),
    }
    if not all(checks.values()):
        failed = [key for key, passed in checks.items() if not passed]
        raise AssertionError(f"v0.5.2 prefix rewrite at cutoff={cutoff}: {failed}")
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "cloud_results/two_wave_extremum_ridge_v052")
    parser.add_argument("--views", nargs="+", default=VIEWS)
    parser.add_argument("--skip-offset-stability", action="store_true")
    args = parser.parse_args()

    sources = [
        Path(__file__),
        ROOT / "src/factor_lab/visual_structure/two_wave/extremum_ridge_v052.py",
        ROOT / "tests/unit/test_two_wave_extremum_ridge_v052.py",
        ROOT / "docs/research/two_wave_extremum_ridge_protocol_v052.md",
        ROOT / "docs/research/two_wave_extremum_ridge_synthetic_results_v052.md",
    ]
    summary = {
        "schema": "two_wave_extremum_ridge_experiment@0.5.2",
        "component_schema": SCHEMA,
        "representation": REPRESENTATION,
        "structural_scale_rule": STRUCTURAL_SCALE_RULE,
        "raw_projection": RAW_PROJECTION,
        "status": "experiment_running_not_prejudged",
        "operational_baseline": "v0.4.3",
        "changed_component_only": "cross_scale_parent_identity_single_extremum_ridges_and_exact_tuple_birth",
        "qualification_changed": False,
        "d1_changed": False,
        "raw_projection_changed": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "fresh_oos": False,
        "old_12_48_used_in_hierarchy": False,
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
        run = build_ridge_run(bars, cfg)
        if view == "5m_offset_0":
            base_tuple = (
                len(baseline.ledger.records),
                sum(row["scale_qualified"] for row in baseline.ledger.records),
                len(baseline.ledger.selected),
            )
            assert base_tuple == (4706, 341, 212), base_tuple

        assert all(row["scale_qualified"] for row in run.ledger.selected)
        assert all(
            cfg.min_cycle <= min(row["cycle_durations"]) <= max(row["cycle_durations"]) <= cfg.max_cycle
            and row["pair_duration"] <= cfg.max_pair
            for row in run.ledger.selected
        )

        summary["views"][view] = {
            "data_audit": audit,
            "v043": baseline_summary(baseline, len(bars)),
            "v052": view_summary(run, baseline, bars),
        }
        bars_by_view[view] = bars
        baseline_by_view[view] = baseline
        run_by_view[view] = run
        save(args.output / "summary.json", summary)

        for fraction in PREFIX_FRACTIONS:
            cutoff = int(len(bars) * fraction)
            prefix = build_ridge_run(bars[:cutoff], MaturityConfig(timeframe=view))
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
            "VIEW_DONE", view,
            "births", len(run.tuple_births),
            "anomalies", len(run.lineage_anomalies),
            "eval", len(run.ledger.records),
            "qual", sum(row["scale_qualified"] for row in run.ledger.records),
            "selected", len(run.ledger.selected),
            flush=True,
        )

    assert len(summary["prefix_checks"]) == len(args.views) * len(PREFIX_FRACTIONS)
    assert all(row["passed"] and row["confirmed_rewrite_count"] == 0 for row in summary["prefix_checks"])

    five_views = [f"5m_offset_{i}" for i in range(5)]
    if (
        not args.skip_offset_stability
        and all(view in run_by_view for view in five_views)
        and "1m_official" in bars_by_view
    ):
        one_minute_ns = np.asarray(
            [pd.Timestamp(bar["timestamp"]).value for bar in bars_by_view["1m_official"]],
            dtype=np.int64,
        )
        baseline_series = {
            view: coverage_and_labels(baseline_by_view[view].ledger.selected, one_minute_ns)
            for view in five_views
        }
        v052_series = {
            view: coverage_and_labels(run_by_view[view].ledger.selected, one_minute_ns)
            for view in five_views
        }
        summary["native_5m_offset_stability"] = {
            "v043": cross_offset_metrics(baseline_series),
            "v052": cross_offset_metrics(v052_series),
            "mapping_basis": "existing 1m timestamps only; no price resampling",
            "iou_role": "boundary_stability_not_accuracy",
        }

    if "5m_offset_0" in run_by_view:
        bars = bars_by_view["5m_offset_0"]
        baseline = baseline_by_view["5m_offset_0"]
        run = run_by_view["5m_offset_0"]
        pivots = local_pivot_bars(baseline)
        summary["fixed_window_audit"] = audit_ranges(run, pivots, fixed_day_ranges(bars))
        legacy_path = ROOT / "cloud_results/two_wave_same_scale_delivery/v04/legacy_case_reaudit.json"
        ranges, source = legacy_ranges(legacy_path)
        summary["legacy_case_source"] = source
        summary["legacy_case_audit"] = audit_ranges(run, pivots, ranges)

    summary["status"] = "formal_v052_results_generated_pending_adjudication"
    save(args.output / "summary.json", summary)
    print("PREFIX_CHECKS", len(summary["prefix_checks"]), "all_passed", flush=True)
    if "5m_offset_0" in summary["views"]:
        print("MAIN_V052", json.dumps(summary["views"]["5m_offset_0"], ensure_ascii=False), flush=True)
    if "native_5m_offset_stability" in summary:
        print("OFFSET_STABILITY", json.dumps(summary["native_5m_offset_stability"], ensure_ascii=False), flush=True)
    if "legacy_case_audit" in summary:
        print("CASE00", json.dumps(summary["legacy_case_audit"].get("case_00_A_clear_C_uncertain"), ensure_ascii=False), flush=True)
        print("CASE02", json.dumps(summary["legacy_case_audit"].get("case_02_C_new_downtrend"), ensure_ascii=False), flush=True)
    print("STUDY_COMPLETE", args.output, flush=True)


if __name__ == "__main__":
    main()
