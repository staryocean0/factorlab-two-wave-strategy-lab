#!/usr/bin/env python3
"""Read-only competition between candidate parent-leg efficiency definitions.

No qualification output is changed.  The frozen v0.5.2 exact-ridge candidates
are rebuilt, then several predeclared efficiency measurements are computed for
structural diagnostics only.  See
`docs/research/two_wave_leg_efficiency_definition_preanalysis_v053.md`.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import build_ridge_run
from factor_lab.visual_structure.two_wave.multiscale_v050 import (
    build_scale_levels,
    default_scale_sigmas,
    time_causal_scale_space,
)
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
DEFINITIONS = (
    "raw_er",
    "birth_scale_raw_interval_er",
    "prebirth_scale_raw_interval_er",
    "prebirth_ridge_interval_er",
    "birth_ridge_interval_er",
)
OUTPUT = ROOT / "cloud_results/two_wave_leg_efficiency_definition_poc_v053"


def _sign(value: float, atol: float = 1e-14) -> int:
    return 1 if value > atol else (-1 if value < -atol else 0)


def _path_er(series: np.ndarray, a: int, b: int) -> tuple[float, int]:
    if not (0 <= a < b < len(series)):
        return math.nan, 0
    y = np.asarray(series[a : b + 1], dtype=float)
    if y.size < 2 or not np.isfinite(y).all():
        return math.nan, 0
    changes = np.abs(np.diff(y))
    length = float(changes.sum())
    displacement = float(y[-1] - y[0])
    if length <= 0:
        return 0.0, _sign(displacement)
    return abs(displacement) / length, _sign(displacement)


def _quantiles(values):
    arr = np.asarray([x for x in values if math.isfinite(x)], dtype=float)
    if arr.size == 0:
        return {str(q): None for q in (0, .1, .5, .9, .99, 1)}
    return {str(q): float(np.quantile(arr, q)) for q in (0, .1, .5, .9, .99, 1)}


def _record_metrics(record, run, levels, scale_space, closes):
    raw_ids = list(record["five_occurrence_bars"])
    raw_signs = [_sign(float(closes[b] - closes[a])) for a, b in zip(raw_ids, raw_ids[1:])]
    birth_level = int(record["birth_scale_level"])
    birth_id = record["birth_scale_id"]
    birth_series = scale_space[birth_id]

    by_level = []
    for rows in run.ridge_nodes_by_level:
        by_level.append({row.ridge_id: row.node for row in rows})

    values = {name: None for name in DEFINITIONS}
    signs = {name: None for name in DEFINITIONS}

    values["raw_er"] = [float(path["efficiency"]) for path in record["leg_paths"]]
    signs["raw_er"] = list(raw_signs)

    tmp = [_path_er(birth_series, a, b) for a, b in zip(raw_ids, raw_ids[1:])]
    values["birth_scale_raw_interval_er"] = [row[0] for row in tmp]
    signs["birth_scale_raw_interval_er"] = [row[1] for row in tmp]

    ridge_ids = list(record["ridge_ids"])
    birth_nodes = [by_level[birth_level].get(ridge_id) for ridge_id in ridge_ids]
    if all(node is not None for node in birth_nodes):
        birth_occ = [int(node.occurrence_index) for node in birth_nodes]
        tmp = [_path_er(birth_series, a, b) for a, b in zip(birth_occ, birth_occ[1:])]
        values["birth_ridge_interval_er"] = [row[0] for row in tmp]
        signs["birth_ridge_interval_er"] = [row[1] for row in tmp]
    else:
        birth_occ = None

    prebirth_occ = None
    prebirth_id = None
    if birth_level > 0:
        pre_level = birth_level - 1
        prebirth_id = levels[pre_level].scale_id
        prebirth_series = scale_space[prebirth_id]
        tmp = [_path_er(prebirth_series, a, b) for a, b in zip(raw_ids, raw_ids[1:])]
        values["prebirth_scale_raw_interval_er"] = [row[0] for row in tmp]
        signs["prebirth_scale_raw_interval_er"] = [row[1] for row in tmp]

        pre_nodes = [by_level[pre_level].get(ridge_id) for ridge_id in ridge_ids]
        if all(node is not None for node in pre_nodes):
            prebirth_occ = [int(node.occurrence_index) for node in pre_nodes]
            tmp = [_path_er(prebirth_series, a, b) for a, b in zip(prebirth_occ, prebirth_occ[1:])]
            values["prebirth_ridge_interval_er"] = [row[0] for row in tmp]
            signs["prebirth_ridge_interval_er"] = [row[1] for row in tmp]

    out = {}
    for name in DEFINITIONS:
        vals = values[name]
        sgns = signs[name]
        valid = vals is not None and len(vals) == 4 and all(math.isfinite(x) for x in vals)
        disagreement = None
        if valid and sgns is not None:
            disagreement = sum(
                int(raw != 0 and measured != raw)
                for raw, measured in zip(raw_signs, sgns)
            )
        out[name] = {
            "valid": bool(valid),
            "leg_er": [float(x) for x in vals] if valid else None,
            "min_leg_er": float(min(vals)) if valid else None,
            "legs_below_0_5": int(sum(x < .5 for x in vals)) if valid else None,
            "legs_at_or_above_0_99": int(sum(x >= .99 for x in vals)) if valid else None,
            "raw_direction_disagreement_legs": int(disagreement) if disagreement is not None else None,
        }
    return {
        "definitions": out,
        "raw_leg_signs": raw_signs,
        "birth_level": birth_level,
        "birth_scale_id": birth_id,
        "prebirth_scale_id": prebirth_id,
        "raw_occurrence_bars": raw_ids,
        "birth_ridge_occurrence_bars": birth_occ,
        "prebirth_ridge_occurrence_bars": prebirth_occ,
    }


def _definition_summary(rows, name):
    valid = [row for row in rows if row["metrics"]["definitions"][name]["valid"]]
    mins = [row["metrics"]["definitions"][name]["min_leg_er"] for row in valid]
    leg_values = [
        value
        for row in valid
        for value in row["metrics"]["definitions"][name]["leg_er"]
    ]
    disagree = sum(
        row["metrics"]["definitions"][name]["raw_direction_disagreement_legs"] or 0
        for row in valid
    )
    legs = 4 * len(valid)

    parent = [row for row in valid if row["excess_micro"] > 0]
    nonparent = [row for row in valid if row["excess_micro"] == 0]
    single_eff = [
        row for row in valid
        if row["reasons"] == ["inefficient_leg"]
    ]
    qualified = [row for row in valid if row["qualified"]]

    def passed(subset):
        return sum(row["metrics"]["definitions"][name]["min_leg_er"] >= .5 for row in subset)

    raw_delta_parent = []
    raw_delta_nonparent = []
    if name != "raw_er":
        for row in parent:
            raw = row["metrics"]["definitions"]["raw_er"]
            cur = row["metrics"]["definitions"][name]
            if raw["valid"]:
                raw_delta_parent.append(cur["min_leg_er"] - raw["min_leg_er"])
        for row in nonparent:
            raw = row["metrics"]["definitions"]["raw_er"]
            cur = row["metrics"]["definitions"][name]
            if raw["valid"]:
                raw_delta_nonparent.append(cur["min_leg_er"] - raw["min_leg_er"])

    return {
        "valid_records": len(valid),
        "min_leg_er_quantiles": _quantiles(mins),
        "leg_er_quantiles": _quantiles(leg_values),
        "record_all_legs_at_or_above_0_99": sum(x >= .99 for x in mins),
        "record_all_legs_at_or_above_0_99_fraction": sum(x >= .99 for x in mins) / len(valid) if valid else None,
        "leg_er_at_or_above_0_99_fraction": sum(x >= .99 for x in leg_values) / len(leg_values) if leg_values else None,
        "raw_direction_disagreement_legs": disagree,
        "raw_direction_disagreement_fraction": disagree / legs if legs else None,
        "pass_0_5_all": passed(valid),
        "pass_0_5_all_fraction": passed(valid) / len(valid) if valid else None,
        "parent_like_records": len(parent),
        "pass_0_5_parent_like": passed(parent),
        "pass_0_5_parent_like_fraction": passed(parent) / len(parent) if parent else None,
        "nonparent_records": len(nonparent),
        "pass_0_5_nonparent": passed(nonparent),
        "pass_0_5_nonparent_fraction": passed(nonparent) / len(nonparent) if nonparent else None,
        "inefficient_single_records": len(single_eff),
        "pass_0_5_inefficient_single": passed(single_eff),
        "pass_0_5_inefficient_single_fraction": passed(single_eff) / len(single_eff) if single_eff else None,
        "already_qualified_records": len(qualified),
        "qualified_preserved_by_efficiency_gate": passed(qualified),
        "qualified_preservation_fraction": passed(qualified) / len(qualified) if qualified else None,
        "delta_vs_raw_min_er_parent_like_quantiles": _quantiles(raw_delta_parent),
        "delta_vs_raw_min_er_nonparent_quantiles": _quantiles(raw_delta_nonparent),
    }


def _interval_iou(a0, a1, b0, b1):
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = (a1 - a0) + (b1 - b0) - inter
    return inter / union if union else 1.0


def _audit_ranges(rows, ranges):
    out = {}
    for label, interval in ranges.items():
        if interval is None:
            out[label] = {"present": False}
            continue
        lo, hi = interval
        overlap = [row for row in rows if row["end_bar"] >= lo and row["start_bar"] <= hi]
        ranked = sorted(overlap, key=lambda row: _interval_iou(lo, hi, row["start_bar"], row["end_bar"]), reverse=True)
        compact = []
        for row in ranked[:10]:
            compact.append({
                "record_id": row["record_id"],
                "raw_occurrence_bars": row["raw_occurrence_bars"],
                "birth_level": row["birth_level"],
                "birth_scale_id": row["birth_scale_id"],
                "excess_micro": row["excess_micro"],
                "reasons": row["reasons"],
                "qualified": row["qualified"],
                "reference_interval_iou_not_model_selection": _interval_iou(lo, hi, row["start_bar"], row["end_bar"]),
                "definitions": {
                    name: {
                        "min_leg_er": row["metrics"]["definitions"][name]["min_leg_er"],
                        "leg_er": row["metrics"]["definitions"][name]["leg_er"],
                        "raw_direction_disagreement_legs": row["metrics"]["definitions"][name]["raw_direction_disagreement_legs"],
                    }
                    for name in DEFINITIONS
                },
            })
        out[label] = {
            "present": True,
            "bar_range": [int(lo), int(hi)],
            "overlap_count": len(overlap),
            "top_interval_overlaps_not_model_selection": compact,
        }
    return out


def _build_rows(view, bars, run, baseline):
    closes = np.asarray([bar["close"] for bar in bars], dtype=float)
    sigmas = default_scale_sigmas()
    levels = build_scale_levels(sigmas)
    scale_space = time_causal_scale_space(np.log(closes), sigmas)
    pivots = local_pivot_bars(baseline)
    rows = []
    for record in run.evaluated_records:
        _, excess = absorbed_local_count(record, pivots)
        metrics = _record_metrics(record, run, levels, scale_space, closes)
        rows.append({
            "record_id": record["record_id"],
            "start_bar": int(record["start_bar"]),
            "end_bar": int(record["end_bar"]),
            "raw_occurrence_bars": list(record["five_occurrence_bars"]),
            "birth_level": int(record["birth_scale_level"]),
            "birth_scale_id": record["birth_scale_id"],
            "excess_micro": int(excess),
            "reasons": list(record["scale_rejection_reasons"]),
            "qualified": bool(record["scale_qualified"]),
            "metrics": metrics,
        })
    return rows


def _cross_view(view_summaries):
    out = {}
    for name in DEFINITIONS:
        out[name] = {
            "raw_direction_disagreement_fraction_by_view": {
                view: view_summaries[view]["definitions"][name]["raw_direction_disagreement_fraction"]
                for view in VIEWS
            },
            "record_saturation_fraction_by_view": {
                view: view_summaries[view]["definitions"][name]["record_all_legs_at_or_above_0_99_fraction"]
                for view in VIEWS
            },
            "parent_pass_0_5_fraction_by_view": {
                view: view_summaries[view]["definitions"][name]["pass_0_5_parent_like_fraction"]
                for view in VIEWS
            },
            "nonparent_pass_0_5_fraction_by_view": {
                view: view_summaries[view]["definitions"][name]["pass_0_5_nonparent_fraction"]
                for view in VIEWS
            },
            "inefficient_single_pass_0_5_fraction_by_view": {
                view: view_summaries[view]["definitions"][name]["pass_0_5_inefficient_single_fraction"]
                for view in VIEWS
            },
            "qualified_preservation_fraction_by_view": {
                view: view_summaries[view]["definitions"][name]["qualified_preservation_fraction"]
                for view in VIEWS
            },
        }
    return out


def main():
    # Small deterministic mathematical self-check, independent of market data.
    straight = np.asarray([0., 1., 2., 3., 4.])
    zigzag = np.asarray([0., 1., .2, 1.2, .4])
    assert abs(_path_er(straight, 0, 4)[0] - 1.0) < 1e-12
    assert 0 <= _path_er(zigzag, 0, 4)[0] < 1.0

    summary = {
        "schema": "two_wave_leg_efficiency_definition_competition@0.5.3-preprotocol",
        "research_logic": "read_only_definition_competition_on_frozen_v052_candidates",
        "operational_baseline": "v0.4.3",
        "candidate_parent_identity": "v0.5.2_exact_ridge_tuple_birth",
        "qualification_changed": False,
        "threshold_changed": False,
        "definitions": list(DEFINITIONS),
        "views": {},
        "status": "running_not_prejudged",
    }

    main_rows = None
    main_bars = None
    for view in VIEWS:
        bars, audit = load_development_bars(
            ROOT / f"data/development/{view}.parquet",
            ROOT / "data/manifest.json",
        )
        cfg = MaturityConfig(timeframe=view)
        baseline = run_v043(bars, view)
        run = build_ridge_run(bars, cfg)
        rows = _build_rows(view, bars, run, baseline)
        definitions = {name: _definition_summary(rows, name) for name in DEFINITIONS}
        summary["views"][view] = {
            "data_audit": audit,
            "evaluated": len(rows),
            "qualified_frozen_v052": sum(row["qualified"] for row in rows),
            "parent_like_absorbed_micro": sum(row["excess_micro"] > 0 for row in rows),
            "inefficient_single": sum(row["reasons"] == ["inefficient_leg"] for row in rows),
            "definitions": definitions,
        }
        save(OUTPUT / "summary.json", summary)
        print(
            "VIEW_DEFINITION_POC", view,
            json.dumps({
                name: {
                    "sat": definitions[name]["record_all_legs_at_or_above_0_99_fraction"],
                    "dir_dis": definitions[name]["raw_direction_disagreement_fraction"],
                    "parent_pass": definitions[name]["pass_0_5_parent_like_fraction"],
                    "single_pass": definitions[name]["pass_0_5_inefficient_single_fraction"],
                    "preserve": definitions[name]["qualified_preservation_fraction"],
                }
                for name in DEFINITIONS
            }, sort_keys=True),
            flush=True,
        )
        if view == "5m_offset_0":
            main_rows = rows
            main_bars = bars

    assert main_rows is not None and main_bars is not None
    legacy_path = ROOT / "cloud_results/two_wave_same_scale_delivery/v04/legacy_case_reaudit.json"
    legacy, source = legacy_ranges(legacy_path)
    summary["cross_view"] = _cross_view(summary["views"])
    summary["main_5m_fixed_windows"] = _audit_ranges(main_rows, fixed_day_ranges(main_bars))
    summary["main_5m_legacy_case_source"] = source
    summary["main_5m_legacy_cases"] = _audit_ranges(main_rows, legacy)
    summary["status"] = "definition_competition_complete_no_qualification_change"
    save(OUTPUT / "summary.json", summary)
    print("DEFINITION_COMPETITION_COMPLETE", OUTPUT, flush=True)


if __name__ == "__main__":
    main()
