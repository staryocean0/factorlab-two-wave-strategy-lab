#!/usr/bin/env python3
"""Read-only v0.5.7b geometry attribution for D2 uncertain-resolution instability.

The frozen v0.5.6 recognizer is rebuilt only to recover geometry that was not
stored in the formal coverage artifacts. No formula, threshold, qualification,
selection, or label is changed. Formal v0.5.6 coverage IDs/intervals and the
v0.5.7a Stage-A counts are re-verified before any geometry is summarized.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from aggregate_two_wave_envelope_direction_v056_five_view import load_payloads
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.envelope_direction_v056 import build_envelope_direction_run
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from run_two_wave_extremum_ridge_v052 import save

VIEWS = [f"5m_offset_{i}" for i in range(5)]
CATEGORIES = ("both_agree", "D2_harm", "D2_help", "both_disagree")
TOL = 0.15


def load_stage_a(root: Path) -> dict:
    matches = []
    for path in root.rglob("summary.json"):
        payload = json.loads(path.read_text())
        if payload.get("schema") == "two_wave_d1_cross_offset_disagreement_attribution@0.5.7a":
            matches.append((path, payload))
    if len(matches) != 1:
        raise AssertionError(f"expected one v0.5.7a summary, found {len(matches)}")
    return matches[0][1]


def timeline(records: list[dict], timestamps: np.ndarray, version: str):
    n = len(timestamps)
    mask = np.zeros(n, dtype=bool)
    labels = np.full(n, "", dtype=object)
    record_ids = np.full(n, "", dtype=object)
    for row in records:
        start = pd.Timestamp(row["start_time"]).value
        end = pd.Timestamp(row["end_time"]).value
        left = int(np.searchsorted(timestamps, start, side="right"))
        right = int(np.searchsorted(timestamps, end, side="right"))
        if right < left:
            raise AssertionError("invalid interval mapping")
        if np.any(mask[left:right]):
            raise AssertionError("selected intervals must be disjoint within a view")
        mask[left:right] = True
        labels[left:right] = row["direction_versions"][version]
        record_ids[left:right] = row["record_id"]
    return mask, labels, record_ids


def ratio(values) -> float | None:
    vals = [float(x) for x in values]
    if not vals or min(vals) <= 0:
        return None
    return max(vals) / min(vals)


def corr_leg_ratio(legs) -> float | None:
    vals = [float(x) for x in legs]
    if len(vals) != 4 or min(vals) <= 0:
        return None
    return max(ratio([vals[0], vals[2]]) or 0.0, ratio([vals[1], vals[3]]) or 0.0)


def cancellation_index(s0: float, s1: float) -> float:
    den = abs(s0) + abs(s1)
    if den == 0:
        return 0.0
    return 1.0 - abs(s0 + s1) / den


def boundary_distance(value: float, tol: float = TOL) -> float:
    return min(abs(value - tol), abs(value + tol))


def boundary_bin(norm: float) -> str:
    if norm <= 0.25:
        return "very_near"
    if norm <= 0.50:
        return "near"
    if norm <= 1.00:
        return "mid"
    return "far"


def sign_flip(a: float, b: float) -> bool:
    return a * b < 0.0


def q(values, weights=None):
    vals = []
    if weights is None:
        vals = [float(v) for v in values if v is not None and np.isfinite(float(v))]
    else:
        for value, weight in zip(values, weights):
            if value is None or not np.isfinite(float(value)) or int(weight) <= 0:
                continue
            vals.extend([float(value)] * int(weight))
    if not vals:
        return None
    arr = np.asarray(vals, dtype=float)
    return {str(x): float(np.quantile(arr, x)) for x in (0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99, 1)}


def occurrence_ns(record: dict, bars: list[dict]) -> list[int]:
    out = []
    for idx in record["five_occurrence_bars"]:
        out.append(pd.Timestamp(bars[int(idx)]["timestamp"]).value)
    return out


def record_geom(record: dict, bars: list[dict]) -> dict:
    steps = [float(v) for v in record["phase_steps_in_amplitude_units"]]
    if len(steps) != 3:
        raise AssertionError("three frozen phase steps required")
    s0, s1, s2 = steps
    net = s0 + s1
    dv = record["direction_versions"]
    upper = float(dv["D2_upper_envelope_drift"])
    lower = float(dv["D2_lower_envelope_drift"])
    cycles = [float(x) for x in record["cycle_durations"]]
    legs = [float(x) for x in record["leg_durations"]]
    return {
        "record_id": record["record_id"],
        "phase": record["phase"],
        "D1": dv["D1"],
        "D2": dv["D2"],
        "s0": s0,
        "s1": s1,
        "s2": s2,
        "net": net,
        "upper": upper,
        "lower": lower,
        "cancellation_index": cancellation_index(s0, s1),
        "amplitude_unit_price": float(record["amplitude_unit_price"]),
        "amplitude_ratio": float(record["amplitude_ratio"]) if record.get("amplitude_ratio") is not None else None,
        "cycle_durations": cycles,
        "mean_cycle_duration": float(np.mean(cycles)),
        "full_cycle_duration_ratio": ratio(cycles),
        "max_corresponding_leg_duration_ratio": corr_leg_ratio(legs),
        "birth_scale_level": int(record["birth_scale_level"]),
        "birth_sigma_bars": float(record["birth_sigma_bars"]),
        "occurrence_ns": occurrence_ns(record, bars),
        "five_occurrence_bars": list(record["five_occurrence_bars"]),
    }


def pair_features(main: dict, other: dict, main_bars: list[dict], other_bars: list[dict]) -> dict:
    m = record_geom(main, main_bars)
    o = record_geom(other, other_bars)
    boundary_values = [m["upper"], m["lower"], o["upper"], o["lower"]]
    min_d = min(boundary_distance(v) for v in boundary_values)
    norm = min_d / TOL
    ds0 = abs(m["s0"] - o["s0"])
    ds1 = abs(m["s1"] - o["s1"])
    ds2 = abs(m["s2"] - o["s2"])
    dnet = abs(m["net"] - o["net"])
    den = max(ds0, ds1)
    net_delta_ratio = dnet / den if den > 0 else 0.0
    occurrence_disp = [abs(a - b) / 60_000_000_000.0 for a, b in zip(m["occurrence_ns"], o["occurrence_ns"])]
    amp_ratio = ratio([m["amplitude_unit_price"], o["amplitude_unit_price"]])
    upper_flip = sign_flip(m["upper"], o["upper"])
    lower_flip = sign_flip(m["lower"], o["lower"])
    net_flip = sign_flip(m["net"], o["net"])
    labels = {m["D2"], o["D2"]}
    direct_up_down = labels == {"uptrend", "downtrend"}
    uncertain_trend = "uncertain" in labels and bool(labels & {"uptrend", "downtrend"})
    return {
        "main_record_id": m["record_id"],
        "other_record_id": o["record_id"],
        "main_D1": m["D1"],
        "other_D1": o["D1"],
        "main_D2": m["D2"],
        "other_D2": o["D2"],
        "main_phase": m["phase"],
        "other_phase": o["phase"],
        "phase_match": m["phase"] == o["phase"],
        "pair_min_boundary_distance": min_d,
        "pair_min_boundary_distance_norm": norm,
        "boundary_bin": boundary_bin(norm),
        "upper_sign_flip": upper_flip,
        "lower_sign_flip": lower_flip,
        "any_envelope_sign_flip": upper_flip or lower_flip,
        "net_sign_flip": net_flip,
        "direct_up_down_reversal": direct_up_down,
        "uncertain_trend_transition": uncertain_trend,
        "range_involved": "range" in labels,
        "main_upper": m["upper"],
        "main_lower": m["lower"],
        "other_upper": o["upper"],
        "other_lower": o["lower"],
        "main_s0": m["s0"],
        "main_s1": m["s1"],
        "main_s2": m["s2"],
        "other_s0": o["s0"],
        "other_s1": o["s1"],
        "other_s2": o["s2"],
        "main_net": m["net"],
        "other_net": o["net"],
        "abs_delta_s0": ds0,
        "abs_delta_s1": ds1,
        "abs_delta_s2": ds2,
        "abs_delta_net": dnet,
        "delta_net_to_max_component_delta": net_delta_ratio,
        "main_cancellation_index": m["cancellation_index"],
        "other_cancellation_index": o["cancellation_index"],
        "max_cancellation_index": max(m["cancellation_index"], o["cancellation_index"]),
        "amplitude_unit_ratio_main_other": amp_ratio,
        "main_amplitude_ratio": m["amplitude_ratio"],
        "other_amplitude_ratio": o["amplitude_ratio"],
        "main_mean_cycle_duration": m["mean_cycle_duration"],
        "other_mean_cycle_duration": o["mean_cycle_duration"],
        "mean_cycle_duration_ratio_main_other": ratio([m["mean_cycle_duration"], o["mean_cycle_duration"]]),
        "main_full_cycle_duration_ratio": m["full_cycle_duration_ratio"],
        "other_full_cycle_duration_ratio": o["full_cycle_duration_ratio"],
        "main_max_corresponding_leg_duration_ratio": m["max_corresponding_leg_duration_ratio"],
        "other_max_corresponding_leg_duration_ratio": o["max_corresponding_leg_duration_ratio"],
        "main_birth_scale_level": m["birth_scale_level"],
        "other_birth_scale_level": o["birth_scale_level"],
        "birth_scale_level_abs_delta": abs(m["birth_scale_level"] - o["birth_scale_level"]),
        "birth_sigma_ratio_main_other": ratio([m["birth_sigma_bars"], o["birth_sigma_bars"]]),
        "occurrence_timestamp_abs_delta_minutes": occurrence_disp,
        "max_occurrence_timestamp_abs_delta_minutes": max(occurrence_disp),
        "median_occurrence_timestamp_abs_delta_minutes": float(np.median(occurrence_disp)),
        "first_endpoint_timestamp_abs_delta_minutes": occurrence_disp[0],
        "last_endpoint_timestamp_abs_delta_minutes": occurrence_disp[-1],
    }


def formal_rows(coverage: dict) -> list[tuple]:
    return [(r["record_id"], r["start_time"], r["end_time"]) for r in coverage["D1"]]


def rebuilt_rows(records: list[dict]) -> list[tuple]:
    return [(r["record_id"], str(r["start_time"]), str(r["end_time"])) for r in records]


def pair_categories(main_records, other_records, timestamps):
    m1 = timeline(main_records, timestamps, "D1")
    m2 = timeline(main_records, timestamps, "D2")
    o1 = timeline(other_records, timestamps, "D1")
    o2 = timeline(other_records, timestamps, "D2")
    assert np.array_equal(m1[0], m2[0]) and np.array_equal(m1[2], m2[2])
    assert np.array_equal(o1[0], o2[0]) and np.array_equal(o1[2], o2[2])
    common = m1[0] & o1[0]
    a1, b1 = m1[1][common], o1[1][common]
    a2, b2 = m2[1][common], o2[1][common]
    mid, oid = m1[2][common], o1[2][common]
    groups = defaultdict(int)
    meta = {}
    for i in range(int(np.sum(common))):
        d1a, d2a = a1[i] == b1[i], a2[i] == b2[i]
        if d1a and d2a:
            cat = "both_agree"
        elif d1a and not d2a:
            cat = "D2_harm"
        elif not d1a and d2a:
            cat = "D2_help"
        else:
            cat = "both_disagree"
        key = (str(mid[i]), str(oid[i]))
        groups[key] += 1
        row = (cat, str(a1[i]), str(b1[i]), str(a2[i]), str(b2[i]))
        if key in meta and meta[key] != row:
            raise AssertionError("category/labels changed within one record-pair overlap")
        meta[key] = row
    return groups, meta, int(np.sum(common))


METRICS = (
    "pair_min_boundary_distance_norm",
    "abs_delta_s0",
    "abs_delta_s1",
    "abs_delta_s2",
    "abs_delta_net",
    "delta_net_to_max_component_delta",
    "main_cancellation_index",
    "other_cancellation_index",
    "max_cancellation_index",
    "amplitude_unit_ratio_main_other",
    "mean_cycle_duration_ratio_main_other",
    "main_full_cycle_duration_ratio",
    "other_full_cycle_duration_ratio",
    "main_max_corresponding_leg_duration_ratio",
    "other_max_corresponding_leg_duration_ratio",
    "birth_scale_level_abs_delta",
    "birth_sigma_ratio_main_other",
    "max_occurrence_timestamp_abs_delta_minutes",
    "median_occurrence_timestamp_abs_delta_minutes",
    "first_endpoint_timestamp_abs_delta_minutes",
    "last_endpoint_timestamp_abs_delta_minutes",
)


def summarize_pairs(rows: list[dict]) -> dict:
    if not rows:
        return {"pairs": 0, "bars": 0}
    weights = [int(r["bars"]) for r in rows]
    bars = sum(weights)
    bins = Counter()
    flags = Counter()
    phases = Counter()
    transitions = Counter()
    for row, w in zip(rows, weights):
        bins[row["boundary_bin"]] += w
        for flag in (
            "upper_sign_flip", "lower_sign_flip", "any_envelope_sign_flip", "net_sign_flip",
            "direct_up_down_reversal", "uncertain_trend_transition", "range_involved", "phase_match",
        ):
            if row[flag]:
                flags[flag] += w
        phases[(row["main_phase"], row["other_phase"])] += w
        transitions[(row["main_D2"], row["other_D2"])] += w
    return {
        "pairs": len(rows),
        "bars": bars,
        "boundary_bin_bar_counts": {k: int(bins.get(k, 0)) for k in ("very_near", "near", "mid", "far")},
        "boundary_bin_bar_fractions": {k: bins.get(k, 0) / bars for k in ("very_near", "near", "mid", "far")},
        "flag_bar_counts": {k: int(v) for k, v in flags.items()},
        "flag_bar_fractions": {k: v / bars for k, v in flags.items()},
        "phase_pair_bar_counts": {f"{a}->{b}": int(v) for (a, b), v in phases.items()},
        "D2_transition_bar_counts": {f"{a}->{b}": int(v) for (a, b), v in transitions.items()},
        "weighted_metric_quantiles": {metric: q([r.get(metric) for r in rows], weights) for metric in METRICS},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--stage-a-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "cloud_results/two_wave_d1_uncertain_resolution_geometry_v057b/summary.json",
    )
    args = parser.parse_args()

    stage_a = load_stage_a(args.stage_a_root)
    assert stage_a["next_diagnostic_branch_by_frozen_rule"] == "stageB_uncertain_resolution_instability"
    formal_summaries, formal_coverages = load_payloads(args.formal_root)
    formal_prefix = [row for view in VIEWS for row in formal_summaries[view]["prefix_checks"]]
    assert len(formal_prefix) == 15
    assert all(row["passed"] and row["confirmed_rewrite_count"] == 0 for row in formal_prefix)

    one_minute, one_minute_audit = load_development_bars(
        ROOT / "data/development/1m_official.parquet", ROOT / "data/manifest.json"
    )
    timestamps = np.asarray([pd.Timestamp(b["timestamp"]).value for b in one_minute], dtype=np.int64)

    runs = {}
    bars_by_view = {}
    rebuild_audits = {}
    for view in VIEWS:
        bars, audit = load_development_bars(
            ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json"
        )
        cfg = MaturityConfig(timeframe=view)
        if not math.isclose(cfg.phase_tolerance, TOL, abs_tol=0.0, rel_tol=0.0):
            raise AssertionError("frozen D2 phase tolerance changed")
        run = build_envelope_direction_run(bars, cfg=cfg)
        selected = run.ledger.selected
        formal = formal_rows(formal_coverages[view])
        rebuilt = rebuilt_rows(selected)
        if rebuilt != formal:
            raise AssertionError(f"full rebuild selected identity/interval mismatch for {view}")
        if any(r.get("future_outcome_used", False) or r.get("trade_authority", False) for r in selected):
            raise AssertionError("outcome/trade authority contamination")
        runs[view] = run
        bars_by_view[view] = bars
        rebuild_audits[view] = {
            "data_audit": audit,
            "selected": len(selected),
            "formal_selected_identity_interval_exact_match": True,
        }

    main_records = runs["5m_offset_0"].ledger.selected
    main_map = {r["record_id"]: r for r in main_records}
    all_pair_rows = []
    by_offset = {}
    pooled_category_counts = Counter()
    pooled_shared_d1_uncertain_harm = 0

    for view in VIEWS[1:]:
        other_records = runs[view].ledger.selected
        other_map = {r["record_id"]: r for r in other_records}
        weights, meta, common_n = pair_categories(main_records, other_records, timestamps)
        stage_row = stage_a["offsets"][view]
        if common_n != stage_row["common_owned_1m_bars"]:
            raise AssertionError(f"Stage-A common bar mismatch for {view}")
        category_bars = Counter()
        rows = []
        for key, weight in weights.items():
            cat, main_d1, other_d1, main_d2, other_d2 = meta[key]
            category_bars[cat] += weight
            feat = pair_features(main_map[key[0]], other_map[key[1]], bars_by_view["5m_offset_0"], bars_by_view[view])
            if (feat["main_D1"], feat["other_D1"], feat["main_D2"], feat["other_D2"]) != (
                main_d1, other_d1, main_d2, other_d2
            ):
                raise AssertionError("rebuilt geometry labels differ from frozen Stage-A pair labels")
            feat.update({"view": view, "category": cat, "bars": int(weight), "shared_D1": main_d1 if main_d1 == other_d1 else None})
            rows.append(feat)
            all_pair_rows.append(feat)
        expected = stage_row["four_way_bar_counts"]
        for cat in CATEGORIES:
            if int(category_bars.get(cat, 0)) != int(expected[cat]):
                raise AssertionError(f"Stage-A category mismatch {view} {cat}")
            pooled_category_counts[cat] += int(category_bars.get(cat, 0))
        target = [r for r in rows if r["category"] == "D2_harm" and r["shared_D1"] == "uncertain"]
        target_bars = sum(r["bars"] for r in target)
        if target_bars != int(stage_row["D2_harm_shared_D1_labels"]["uncertain"]):
            raise AssertionError(f"Stage-A uncertain harm mismatch for {view}")
        pooled_shared_d1_uncertain_harm += target_bars
        by_offset[view] = {
            "common_owned_1m_bars": common_n,
            "all_pair_categories": summarize_pairs(rows),
            "shared_D1_uncertain_D2_harm": summarize_pairs(target),
            "top_uncertain_harm_pairs_by_weight": sorted(target, key=lambda r: r["bars"], reverse=True)[:30],
        }

    stage_pooled = stage_a["pooled"]["four_way_bar_counts_across_four_offset_comparisons"]
    for cat in CATEGORIES:
        if pooled_category_counts[cat] != int(stage_pooled[cat]):
            raise AssertionError(f"pooled Stage-A category mismatch for {cat}")
    if pooled_shared_d1_uncertain_harm != int(stage_a["pooled"]["D2_harm_shared_D1_labels"]["uncertain"]):
        raise AssertionError("pooled Stage-A uncertain harm mismatch")

    target_rows = [
        r for r in all_pair_rows
        if r["category"] == "D2_harm" and r["shared_D1"] == "uncertain"
    ]
    help_rows = [r for r in all_pair_rows if r["category"] == "D2_help"]
    agree_rows = [r for r in all_pair_rows if r["category"] == "both_agree"]
    target_summary = summarize_pairs(target_rows)
    target_bars = target_summary["bars"]
    bins = target_summary["boundary_bin_bar_counts"]
    near_bars = bins["very_near"] + bins["near"]
    far_bars = bins["far"]
    far_signflip_bars = sum(
        r["bars"] for r in target_rows
        if r["boundary_bin"] == "far" and r["any_envelope_sign_flip"]
    )
    near_fraction = near_bars / target_bars if target_bars else 0.0
    far_fraction = far_bars / target_bars if target_bars else 0.0
    far_signflip_fraction = far_signflip_bars / target_bars if target_bars else 0.0

    rule_b = far_fraction >= 0.25 or far_signflip_fraction > 0.10
    rule_a = near_fraction >= (2.0 / 3.0) and far_signflip_fraction <= 0.10
    if rule_b:
        verdict = "endpoint_D2_route_rejected"
    elif rule_a:
        verdict = "confidence_gate_route_supported"
    else:
        verdict = "mixed_geometry_requires_more_attribution"

    output = {
        "schema": "two_wave_d1_uncertain_resolution_geometry_attribution@0.5.7b",
        "status": "read_only_uncertain_resolution_geometry_attribution_not_classifier_result",
        "protocol": "docs/research/two_wave_d1_uncertain_resolution_geometry_protocol_v057b.md",
        "stage_a_source_run": 34010153423,
        "stage_a_source_artifact": 9982207960,
        "formal_v056_source_run": 34009427027,
        "recognizer_formula_changed": False,
        "classifier_threshold_changed": False,
        "frozen_full_view_rebuild_performed_for_features_only": True,
        "formal_selected_identity_interval_exact_match_all_views": True,
        "formal_native5m_prefix_evidence_reused": 15,
        "one_minute_data_audit": one_minute_audit,
        "rebuild_audits": rebuild_audits,
        "by_offset": by_offset,
        "pooled": {
            "all_category_bar_counts_verified_against_stage_a": {cat: int(pooled_category_counts[cat]) for cat in CATEGORIES},
            "shared_D1_uncertain_D2_harm": target_summary,
            "D2_help_comparator": summarize_pairs(help_rows),
            "both_agree_comparator": summarize_pairs(agree_rows),
            "route_gate_inputs": {
                "target_bars": int(target_bars),
                "near_or_very_near_bars": int(near_bars),
                "near_or_very_near_fraction": near_fraction,
                "far_bars": int(far_bars),
                "far_fraction": far_fraction,
                "far_with_any_envelope_sign_flip_bars": int(far_signflip_bars),
                "far_with_any_envelope_sign_flip_fraction": far_signflip_fraction,
                "rule_B_endpoint_risk_triggered": rule_b,
                "rule_A_confidence_gate_supported": rule_a,
                "precedence": "B_then_A_then_C",
            },
        },
        "next_route_verdict_by_frozen_rule": verdict,
        "trade_authority": False,
        "future_outcome_used": False,
    }
    save(args.output, output)
    details_path = args.output.parent / "pair_details.json"
    save(details_path, {
        "schema": "two_wave_d1_uncertain_resolution_geometry_pair_details@0.5.7b",
        "rows": all_pair_rows,
    })
    print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
