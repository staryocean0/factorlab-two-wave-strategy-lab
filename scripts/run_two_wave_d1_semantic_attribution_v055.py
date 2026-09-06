#!/usr/bin/env python3
"""Read-only main-5m semantic attribution for frozen D1 on v0.5.4 records."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.cycle_scale_qualification_v054 import (
    build_cycle_scale_qualification_run,
)
from factor_lab.visual_structure.two_wave.d1_semantic_attribution_v055 import (
    SCHEMA,
    diagnose_with_subtype,
    range_span_bound,
)
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig

VIEW = "5m_offset_0"
OUTPUT = ROOT / "cloud_results/two_wave_d1_semantic_attribution_v055"
FIXED_DAYS = ("2018-06-20", "2019-04-15", "2020-07-15")
FOCUS_CASES = {
    "case_00_A_clear_C_uncertain",
    "case_02_C_new_downtrend",
    "case_10_stable_range",
    "case_11_stable_range",
    "case_14_stable_uptrend",
}
METRICS = (
    "s0_same_phase_first",
    "s1_same_phase_second",
    "s2_opposite_envelope",
    "net_same_phase_drift",
    "upper_envelope_drift",
    "lower_envelope_drift",
    "upper_minus_lower_drift",
    "center_drift_linear_diagnostic",
    "amplitude_change_fraction",
    "max_corresponding_leg_duration_ratio",
    "net_drift_per_mean_cycle_bar",
    "center_drift_per_mean_cycle_bar",
    "max_abs_phase_step",
    "max_phase_span",
    "phase_tolerance_margin_max_abs",
    "strong_drift_margin_abs_net",
    "minimum_directed_margin_to_opposite_tolerance",
)


def save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def quantiles(values):
    vals = [float(v) for v in values if v is not None and np.isfinite(float(v))]
    if not vals:
        return None
    arr = np.asarray(vals, dtype=float)
    return {str(q): float(np.quantile(arr, q)) for q in (0, 0.1, 0.25, 0.5, 0.75, 0.9, 1)}


def _diag_rows(records, cfg):
    out = []
    for row in records:
        d = diagnose_with_subtype(row, cfg)
        d["scale_qualified"] = bool(row["scale_qualified"])
        d["selected"] = bool(row["selected"])
        d["classification"] = row["classification"]
        d["start_bar"] = int(row["start_bar"])
        d["end_bar"] = int(row["end_bar"])
        d["five_occurrence_bars"] = list(row["five_occurrence_bars"])
        d["cycle_durations"] = list(row["cycle_durations"])
        d["leg_durations"] = list(row["leg_durations"])
        d["birth_scale_level"] = int(row["birth_scale_level"])
        d["birth_sigma_bars"] = float(row["birth_sigma_bars"])
        steps = [abs(float(d[k])) for k in ("s0_same_phase_first", "s1_same_phase_second", "s2_opposite_envelope")]
        d["min_abs_distance_to_phase_tolerance"] = min(abs(v - cfg.phase_tolerance) for v in steps)
        subtype = d["uncertain_subtype"]
        if subtype in {
            "same_phase_reversal_conflict",
            "opposite_envelope_conflict",
            "strong_net_with_opposed_phase",
            "large_migration_without_coherent_direction",
        }:
            d["uncertain_attribution_group"] = "explicit_geometry_conflict"
        elif subtype is not None:
            d["uncertain_attribution_group"] = "insufficient_or_weak_direction_evidence"
        else:
            d["uncertain_attribution_group"] = None
        out.append(d)
    return out


def group_quantiles(rows, key):
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key))].append(row)
    out = {}
    for group, members in sorted(grouped.items()):
        out[group] = {
            "count": len(members),
            "metrics": {metric: quantiles(row.get(metric) for row in members) for metric in METRICS},
            "min_abs_distance_to_phase_tolerance": quantiles(row["min_abs_distance_to_phase_tolerance"] for row in members),
        }
    return out


def summarize(records, cfg):
    rows = _diag_rows(records, cfg)
    labels = Counter(row["D1"] for row in rows)
    reasons = Counter(str(row["D1_reason"]) for row in rows)
    transitions = Counter(f"{row['D0']}->{row['D1']}" for row in rows)
    sign_patterns = Counter(row["raw_sign_pattern"] for row in rows)
    threshold_patterns = Counter(row["threshold_pattern"] for row in rows)
    uncertain = [row for row in rows if row["D1"] == "uncertain"]
    subtypes = Counter(row["uncertain_subtype"] for row in uncertain)
    groups = Counter(row["uncertain_attribution_group"] for row in uncertain)
    all_small = [row for row in rows if row["range_all_steps_small"]]
    span_counterexamples = [row for row in all_small if not row["range_span_gate_pass"]]
    return {
        "records": len(rows),
        "label_counts": dict(labels),
        "label_fractions": {k: v / len(rows) for k, v in labels.items()} if rows else {},
        "D1_reason_counts": dict(reasons),
        "D0_to_D1": dict(transitions),
        "raw_sign_patterns": dict(sign_patterns.most_common()),
        "threshold_patterns": dict(threshold_patterns.most_common()),
        "metrics_all": {metric: quantiles(row.get(metric) for row in rows) for metric in METRICS},
        "metrics_by_D1": group_quantiles(rows, "D1"),
        "uncertain_records": len(uncertain),
        "uncertain_subtype_counts": dict(subtypes),
        "uncertain_attribution_group_counts": dict(groups),
        "metrics_by_uncertain_subtype": group_quantiles(uncertain, "uncertain_subtype"),
        "range_redundancy": {
            "algebraic_bound": range_span_bound(cfg),
            "all_steps_small_records": len(all_small),
            "span_gate_counterexamples": len(span_counterexamples),
            "counterexample_record_ids": [row["record_id"] for row in span_counterexamples[:20]],
        },
        "phase_boundary_distance_quantiles": quantiles(row["min_abs_distance_to_phase_tolerance"] for row in rows),
        "uncertain_phase_boundary_distance_quantiles": quantiles(row["min_abs_distance_to_phase_tolerance"] for row in uncertain),
        "strong_drift_margin_quantiles": quantiles(row["strong_drift_margin_abs_net"] for row in rows),
        "uncertain_strong_drift_margin_quantiles": quantiles(row["strong_drift_margin_abs_net"] for row in uncertain),
        "diagnostics": rows,
    }


def fixed_day_ranges(bars):
    found = {}
    for i, bar in enumerate(bars):
        day = str(bar.get("trading_day"))
        if day in FIXED_DAYS:
            found.setdefault(day, [i, i])[1] = i
    return {day: found.get(day) for day in FIXED_DAYS}


def legacy_ranges(path: Path):
    data = json.loads(path.read_text())
    out = {}
    for row in data["cases"]:
        if row["case"] in FOCUS_CASES:
            bars = row["five_occurrence_bars"]
            out[row["case"]] = [int(bars[0]), int(bars[-1])]
    return out


def interval_iou(a0, a1, b0, b1):
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = (a1 - a0) + (b1 - b0) - inter
    return inter / union if union else 1.0


def compact_audit_record(record, cfg):
    d = diagnose_with_subtype(record, cfg)
    return {
        "record_id": record["record_id"],
        "raw_five_occurrence_bars": list(record["five_occurrence_bars"]),
        "cycle_durations": list(record["cycle_durations"]),
        "leg_durations": list(record["leg_durations"]),
        "scale_qualified": bool(record["scale_qualified"]),
        "selected": bool(record["selected"]),
        "D0": d["D0"],
        "D1": d["D1"],
        "D1_reason": d["D1_reason"],
        "uncertain_subtype": d["uncertain_subtype"],
        "s0": d["s0_same_phase_first"],
        "s1": d["s1_same_phase_second"],
        "s2": d["s2_opposite_envelope"],
        "net": d["net_same_phase_drift"],
        "center_drift": d["center_drift_linear_diagnostic"],
        "upper_drift": d["upper_envelope_drift"],
        "lower_drift": d["lower_envelope_drift"],
        "amplitude_change_fraction": d["amplitude_change_fraction"],
        "max_corresponding_leg_duration_ratio": d["max_corresponding_leg_duration_ratio"],
    }


def audit_ranges(records, ranges, cfg):
    out = {}
    for name, interval in ranges.items():
        if interval is None:
            out[name] = {"present": False}
            continue
        lo, hi = interval
        overlapping = [r for r in records if r["end_bar"] >= lo and r["start_bar"] <= hi]
        ranked = sorted(overlapping, key=lambda r: interval_iou(lo, hi, r["start_bar"], r["end_bar"]), reverse=True)
        out[name] = {
            "present": True,
            "bar_range": [lo, hi],
            "evaluated_overlap": len(overlapping),
            "qualified_overlap": sum(r["scale_qualified"] for r in overlapping),
            "selected_overlap": sum(r["selected"] for r in overlapping),
            "D1_counts_on_qualified": dict(Counter(r["direction_versions"]["D1"] for r in overlapping if r["scale_qualified"])),
            "top_overlap_records": [compact_audit_record(r, cfg) for r in ranked[:10]],
        }
    return out


def main():
    bars, data_audit = load_development_bars(
        ROOT / "data/development/5m_offset_0.parquet", ROOT / "data/manifest.json"
    )
    cfg = MaturityConfig(timeframe=VIEW)
    run = build_cycle_scale_qualification_run(bars, cfg=cfg)
    records = run.ledger.records
    qualified = [r for r in records if r["scale_qualified"]]
    selected = run.ledger.selected

    assert len(records) == len(run.evaluated_records)
    assert all(r["classification"] == r["direction_versions"]["D1"] for r in qualified)
    assert all(not r.get("future_outcome_used", False) for r in records)
    assert all(not r.get("trade_authority", False) for r in records)

    qualified_summary = summarize(qualified, cfg)
    selected_summary = summarize(selected, cfg)
    all_eval_diags = _diag_rows(records, cfg)

    summary = {
        "schema": SCHEMA,
        "status": "readonly_semantic_attribution_generated_pending_interpretation",
        "view": VIEW,
        "data_audit": data_audit,
        "frozen_upstream": "v0.5.2_exact_ridge_parent_plus_v0.5.4_full_cycle_qualification",
        "no_relabel": True,
        "no_requalification": True,
        "no_outcomes": True,
        "trade_authority": False,
        "thresholds": {
            "phase_tolerance": cfg.phase_tolerance,
            "opposite_tolerance": cfg.opposite_tolerance,
            "strong_drift": cfg.strong_drift,
        },
        "evaluated": len(records),
        "qualified": len(qualified),
        "selected": len(selected),
        "qualified_summary": {k: v for k, v in qualified_summary.items() if k != "diagnostics"},
        "selected_summary": {k: v for k, v in selected_summary.items() if k != "diagnostics"},
        "all_evaluated_D1_counts_diagnostic_only": dict(Counter(row["D1"] for row in all_eval_diags)),
        "fixed_window_audit": audit_ranges(records, fixed_day_ranges(bars), cfg),
        "legacy_case_audit": audit_ranges(
            records,
            legacy_ranges(ROOT / "docs/research/two_wave_v04_legacy_cases.json"),
            cfg,
        ),
        "interpretation_not_model_selection": True,
    }

    save(OUTPUT / "summary.json", summary)
    save(OUTPUT / "qualified_diagnostics.json", qualified_summary["diagnostics"])
    save(OUTPUT / "selected_diagnostics.json", selected_summary["diagnostics"])
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
