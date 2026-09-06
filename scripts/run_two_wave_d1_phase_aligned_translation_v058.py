#!/usr/bin/env python3
"""Frozen v0.5.8 PAWCT five-view continuous-representation POC."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from aggregate_two_wave_envelope_direction_v056_five_view import load_payloads
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.envelope_direction_v056 import build_envelope_direction_run
from factor_lab.visual_structure.two_wave.parent_translation_v058 import build_pawct_for_record
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from run_two_wave_extremum_ridge_v052 import save

VIEWS = [f"5m_offset_{i}" for i in range(5)]
LARGE_MARGIN = 0.30


def load_v057b(root: Path):
    summary = []
    details = []
    for path in root.rglob("summary.json"):
        payload = json.loads(path.read_text())
        if payload.get("schema") == "two_wave_d1_uncertain_resolution_geometry_attribution@0.5.7b":
            summary.append(payload)
    for path in root.rglob("pair_details.json"):
        payload = json.loads(path.read_text())
        if payload.get("schema") == "two_wave_d1_uncertain_resolution_geometry_pair_details@0.5.7b":
            details.append(payload)
    if len(summary) != 1 or len(details) != 1:
        raise AssertionError(f"expected one v057b summary/details, got {len(summary)}/{len(details)}")
    return summary[0], details[0]["rows"]


def formal_rows(coverage: dict) -> list[tuple]:
    return [(r["record_id"], r["start_time"], r["end_time"]) for r in coverage["D1"]]


def rebuilt_rows(records: list[dict]) -> list[tuple]:
    return [(r["record_id"], str(r["start_time"]), str(r["end_time"])) for r in records]


def weighted_quantile(values, weights, quantiles=(0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99, 1)):
    pairs = sorted(
        (float(v), int(w))
        for v, w in zip(values, weights)
        if v is not None and np.isfinite(float(v)) and int(w) > 0
    )
    if not pairs:
        return None
    vals = np.asarray([p[0] for p in pairs], dtype=float)
    w = np.asarray([p[1] for p in pairs], dtype=float)
    cum = np.cumsum(w)
    total = cum[-1]
    out = {}
    for q in quantiles:
        target = float(q) * total
        idx = int(np.searchsorted(cum, target, side="left"))
        idx = min(idx, len(vals) - 1)
        out[str(q)] = float(vals[idx])
    return out


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"pairs": 0, "bars": 0}
    weights = [int(r["bars"]) for r in rows]
    bars = sum(weights)
    large = sum(r["bars"] for r in rows if r["large_margin_scalar_sign_flip"])
    ordinary = sum(r["bars"] for r in rows if r["ordinary_scalar_sign_flip"])
    phase_match = sum(r["bars"] for r in rows if r["phase_match"])
    return {
        "pairs": len(rows),
        "bars": int(bars),
        "large_margin_scalar_sign_flip_bars": int(large),
        "large_margin_scalar_sign_flip_fraction": large / bars,
        "ordinary_scalar_sign_flip_bars": int(ordinary),
        "ordinary_scalar_sign_flip_fraction": ordinary / bars,
        "phase_match_bars": int(phase_match),
        "phase_match_fraction": phase_match / bars,
        "weighted_quantiles": {
            "T_main": weighted_quantile([r["T_main"] for r in rows], weights),
            "T_other": weighted_quantile([r["T_other"] for r in rows], weights),
            "abs_delta_T": weighted_quantile([r["abs_delta_T"] for r in rows], weights),
            "D_endpoint": weighted_quantile([r["D_endpoint"] for r in rows], weights),
            "main_MAD": weighted_quantile([r["main_MAD"] for r in rows], weights),
            "other_MAD": weighted_quantile([r["other_MAD"] for r in rows], weights),
            "main_first_leg_median": weighted_quantile([r["main_first_leg_median"] for r in rows], weights),
            "main_second_leg_median": weighted_quantile([r["main_second_leg_median"] for r in rows], weights),
            "other_first_leg_median": weighted_quantile([r["other_first_leg_median"] for r in rows], weights),
            "other_second_leg_median": weighted_quantile([r["other_second_leg_median"] for r in rows], weights),
            "max_occurrence_timestamp_abs_delta_minutes": weighted_quantile(
                [r["max_occurrence_timestamp_abs_delta_minutes"] for r in rows], weights
            ),
            "max_cancellation_index": weighted_quantile([r["max_cancellation_index"] for r in rows], weights),
            "birth_scale_level_abs_delta": weighted_quantile([r["birth_scale_level_abs_delta"] for r in rows], weights),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--v057b-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "cloud_results/two_wave_d1_phase_aligned_translation_v058/summary.json",
    )
    args = parser.parse_args()

    formal_summaries, formal_coverages = load_payloads(args.formal_root)
    prefix = [row for view in VIEWS for row in formal_summaries[view]["prefix_checks"]]
    assert len(prefix) == 15 and all(r["passed"] and r["confirmed_rewrite_count"] == 0 for r in prefix)
    v057b, pair_rows = load_v057b(args.v057b_root)
    assert v057b["next_route_verdict_by_frozen_rule"] == "endpoint_D2_route_rejected"
    assert v057b["pooled"]["shared_D1_uncertain_D2_harm"]["bars"] == 21802

    selected_by_view = {}
    pawct_by_view = {}
    data_audits = {}
    for view in VIEWS:
        bars, audit = load_development_bars(
            ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json"
        )
        cfg = MaturityConfig(timeframe=view)
        if not math.isclose(cfg.phase_tolerance, 0.15, rel_tol=0.0, abs_tol=0.0):
            raise AssertionError("frozen phase tolerance changed")
        run = build_envelope_direction_run(bars, cfg=cfg)
        selected = run.ledger.selected
        if rebuilt_rows(selected) != formal_rows(formal_coverages[view]):
            raise AssertionError(f"frozen formal identity mismatch for {view}")
        selected_by_view[view] = {r["record_id"]: r for r in selected}
        pawct_by_view[view] = {r["record_id"]: build_pawct_for_record(r, bars) for r in selected}
        data_audits[view] = {
            "data": audit,
            "selected": len(selected),
            "formal_selected_identity_interval_exact_match": True,
        }

    enriched = []
    category_bars = Counter()
    for row in pair_rows:
        view = row["view"]
        m = pawct_by_view["5m_offset_0"][row["main_record_id"]]
        o = pawct_by_view[view][row["other_record_id"]]
        tm = float(m["translation_in_amplitude_units"])
        to = float(o["translation_in_amplitude_units"])
        ordinary_flip = tm * to < 0.0
        large_flip = ordinary_flip and abs(tm) > LARGE_MARGIN and abs(to) > LARGE_MARGIN
        d_endpoint = max(
            abs(float(row["main_upper"]) - float(row["other_upper"])),
            abs(float(row["main_lower"]) - float(row["other_lower"])),
        )
        item = {
            "view": view,
            "category": row["category"],
            "shared_D1": row["shared_D1"],
            "bars": int(row["bars"]),
            "main_record_id": row["main_record_id"],
            "other_record_id": row["other_record_id"],
            "phase_match": bool(row["phase_match"]),
            "T_main": tm,
            "T_other": to,
            "abs_delta_T": abs(tm - to),
            "D_endpoint": d_endpoint,
            "ordinary_scalar_sign_flip": ordinary_flip,
            "large_margin_scalar_sign_flip": large_flip,
            "main_MAD": float(m["translation_mad_in_amplitude_units"]),
            "other_MAD": float(o["translation_mad_in_amplitude_units"]),
            "main_first_leg_median": float(m["first_leg_median_translation"]),
            "main_second_leg_median": float(m["second_leg_median_translation"]),
            "other_first_leg_median": float(o["first_leg_median_translation"]),
            "other_second_leg_median": float(o["second_leg_median_translation"]),
            "max_occurrence_timestamp_abs_delta_minutes": float(row["max_occurrence_timestamp_abs_delta_minutes"]),
            "max_cancellation_index": float(row["max_cancellation_index"]),
            "birth_scale_level_abs_delta": float(row["birth_scale_level_abs_delta"]),
        }
        category_bars[row["category"]] += int(row["bars"])
        enriched.append(item)

    expected = v057b["pooled"]["all_category_bar_counts_verified_against_stage_a"]
    for cat, count in expected.items():
        if int(category_bars[cat]) != int(count):
            raise AssertionError(f"v057b pair/bar count drift for {cat}")

    target = [r for r in enriched if r["category"] == "D2_harm" and r["shared_D1"] == "uncertain"]
    help_rows = [r for r in enriched if r["category"] == "D2_help"]
    agree_rows = [r for r in enriched if r["category"] == "both_agree"]
    if sum(r["bars"] for r in target) != 21802:
        raise AssertionError("frozen shared-D1-uncertain target changed")

    target_summary = summarize(target)
    help_summary = summarize(help_rows)
    agree_summary = summarize(agree_rows)
    target_pawct_med = target_summary["weighted_quantiles"]["abs_delta_T"]["0.5"]
    target_endpoint_med = target_summary["weighted_quantiles"]["D_endpoint"]["0.5"]

    r1 = target_summary["large_margin_scalar_sign_flip_fraction"] < 0.05
    r2 = (
        help_summary["large_margin_scalar_sign_flip_fraction"] <= 0.05
        and agree_summary["large_margin_scalar_sign_flip_fraction"] <= 0.05
    )
    r3 = target_pawct_med < target_endpoint_med
    r4 = (
        target_summary["bars"] == 21802
        and help_summary["bars"] == v057b["pooled"]["D2_help_comparator"]["bars"]
        and agree_summary["bars"] == v057b["pooled"]["both_agree_comparator"]["bars"]
    )
    verdict = "PAWCT_representation_candidate_pass" if all((r1, r2, r3, r4)) else "PAWCT_representation_candidate_fail"

    per_offset = {}
    for view in VIEWS[1:]:
        rows = [r for r in enriched if r["view"] == view]
        per_offset[view] = {
            "all": summarize(rows),
            "shared_D1_uncertain_D2_harm": summarize([
                r for r in rows if r["category"] == "D2_harm" and r["shared_D1"] == "uncertain"
            ]),
            "D2_help": summarize([r for r in rows if r["category"] == "D2_help"]),
            "both_agree": summarize([r for r in rows if r["category"] == "both_agree"]),
        }

    result = {
        "schema": "two_wave_d1_phase_aligned_translation_representation@0.5.8",
        "status": "continuous_representation_poc_not_parent_classifier",
        "protocol": "docs/research/two_wave_d1_phase_aligned_translation_protocol_v058.md",
        "formal_v056_source_run": 34009427027,
        "v057b_source_run": 34010814782,
        "v057b_source_artifact": 9982490147,
        "grid_points_per_leg": 65,
        "total_phase_points": 129,
        "location_function": "median",
        "normalization": "frozen_record_amplitude_unit_price",
        "large_margin_diagnostic_abs_T": LARGE_MARGIN,
        "formula_or_threshold_changed_upstream": False,
        "parent_classifier_emitted": False,
        "formal_selected_identity_interval_exact_match_all_views": True,
        "data_audits": data_audits,
        "per_offset": per_offset,
        "pooled": {
            "shared_D1_uncertain_D2_harm": target_summary,
            "D2_help": help_summary,
            "both_agree": agree_summary,
            "gate_inputs": {
                "R1_target_large_margin_sign_flip_fraction": target_summary["large_margin_scalar_sign_flip_fraction"],
                "R1_threshold": "<0.05",
                "R2_help_large_margin_sign_flip_fraction": help_summary["large_margin_scalar_sign_flip_fraction"],
                "R2_agree_large_margin_sign_flip_fraction": agree_summary["large_margin_scalar_sign_flip_fraction"],
                "R2_threshold": "<=0.05 each",
                "R3_target_weighted_median_abs_delta_T": target_pawct_med,
                "R3_target_weighted_median_D_endpoint": target_endpoint_med,
                "R4_counts_exact": r4,
            },
            "hard_gates": {"R1": r1, "R2": r2, "R3": r3, "R4": r4},
        },
        "research_verdict": verdict,
        "future_outcome_used": False,
        "trade_authority": False,
    }
    save(args.output, result)
    save(args.output.parent / "pair_details.json", {
        "schema": "two_wave_d1_phase_aligned_translation_pair_details@0.5.8",
        "rows": enriched,
    })
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
