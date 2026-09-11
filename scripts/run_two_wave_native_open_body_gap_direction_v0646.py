#!/usr/bin/env python3
"""Formal read-only v0.6.46 native open/body/gap direction attribution."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.d1_huber_margin_rescue_v0625 import d1_primary_margin_rescue
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.leg_asymmetry_stability_v0640 import greater_probability
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.native_open_body_gap_direction_v0646 import (
    harmless_pair_metrics,
    open_anchor_metrics,
)
from factor_lab.visual_structure.two_wave.order_sensitive_residual_shape_v0639 import numeric_summary
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import build_edge_graph
from scripts.run_two_wave_d1_huber_erosion_consensus_v0623 import (
    EXPECTED_BOTHQ,
    EXPECTED_FILTERED,
    EXPECTED_RAW,
    EXPECTED_V0618,
    VIEWS,
    fkey,
    find_one,
    load_gz,
    qmatrix,
    reconstruct_pair,
)

EXPECTED_D1_EXACT_COUNT = 1400
EXPECTED_V0625_EXACT_COUNT = 1402
EXPECTED_V0625_DECISIVE_AGREEMENT = 1.0
EXPECTED_V0625_OPPOSITE_TREND_CONFLICTS = 0

PAIR_FIELDS = (
    "pair_mean_abs_anchor_body",
    "pair_mean_abs_mean_oriented_anchor_body",
    "pair_mean_abs_anchor_gap",
    "pair_mean_open_adjustment_l1",
    "pair_mean_open_adjustment_linf",
    "pair_mean_close_migration_l1",
    "pair_mean_open_migration_l1",
    "close_step_view_distance_l1",
    "open_step_view_distance_l1",
    "open_stability_gain_l1",
    "open_adjustment_view_distance_l1",
    "mean_abs_body_view_delta",
    "mean_oriented_body_view_delta",
    "mean_abs_gap_view_delta",
)


def side_state(row: dict, bars: list[dict], closes: list[float], view: str) -> dict:
    pair = reconstruct_pair(row, bars, view)
    d1 = str(pair["direction_versions"]["D1"])
    amp = float(pair["amplitude_unit_price"])
    anchors = tuple(int(x) for x in row["published_raw_occurrence_bars"])
    metrics = open_anchor_metrics(bars, anchors, str(row["phase"]), amp)
    frozen_steps = tuple(float(x) for x in pair["phase_steps_in_amplitude_units"])
    measured_steps = tuple(float(x) for x in metrics["close_phase_steps_in_amplitude_units"])
    if len(frozen_steps) != 3 or any(abs(a - b) > 1e-12 for a, b in zip(frozen_steps, measured_steps)):
        raise AssertionError("v0646 close-step reconstruction drifted from frozen D1 geometry")
    v0625 = d1_primary_margin_rescue(d1, closes, anchors, amp)
    if bool(v0625["D1_decisive_overridden"]):
        raise AssertionError("v0625 must not override decisive D1")
    return {
        "D1": d1,
        "v0625": str(v0625["classification"]),
        "v0625_source": str(v0625["decision_source"]),
        **metrics,
    }


def summarize(rows: list[dict], fields: tuple[str, ...] = PAIR_FIELDS) -> dict:
    if not rows:
        return {field: None for field in fields}
    return {field: numeric_summary([float(row[field]) for row in rows]) for field in fields}


def positive_fraction(values: list[float]) -> float:
    if not values:
        raise ValueError("non-empty values required")
    return float(sum(float(x) > 0.0 for x in values) / len(values))


def rank_nonexact_gt_exact(nonexact: list[dict], exact: list[dict], field: str) -> float:
    return greater_probability(
        [float(r[field]) for r in nonexact],
        [float(r[field]) for r in exact],
    )


def write_card(path: Path, result: dict) -> None:
    rank = result["v0625_threshold_free_rank_probabilities"]
    exact = result["v0625_group_summary"]["exact"]
    non = result["v0625_group_summary"]["nonexact"]
    rows = [
        ("pair mean abs anchor body", "pair_mean_abs_anchor_body", "nonexact_mean_abs_anchor_body_gt_exact"),
        ("pair mean abs oriented-body mean", "pair_mean_abs_mean_oriented_anchor_body", "nonexact_abs_mean_oriented_anchor_body_gt_exact"),
        ("pair mean abs opening gap", "pair_mean_abs_anchor_gap", "nonexact_mean_abs_anchor_gap_gt_exact"),
        ("open-adjustment view distance L1", "open_adjustment_view_distance_l1", "nonexact_open_adjustment_view_distance_l1_gt_exact"),
        ("open stability gain L1", "open_stability_gain_l1", "nonexact_open_stability_gain_l1_gt_exact"),
    ]
    lines = [
        "# Two-Wave v0.6.46 native open/body/gap direction attribution",
        "",
        f"Formal attribution: **`{result['formal_attribution']}`**",
        "",
        f"Frozen universe reproduced: **{result['controls']['both_v0618_qualified_pairs']}** pairs; D1 exact = **{result['controls']['D1_exact_count']}**; v0.6.25 exact = **{result['controls']['v0625_exact_count']}**.",
        "",
        "| quantity | v0.6.25 exact median | v0.6.25 nonexact median | P(nonexact > exact) |",
        "|---|---:|---:|---:|",
    ]
    for label, field, rank_field in rows:
        lines.append(
            f"| {label} | {exact[field]['median']:.6f} | {non[field]['median']:.6f} | {rank[rank_field]:.6f} |"
        )
    lines += [
        "",
        f"Positive open-stability-gain fraction, v0.6.25 exact: `{result['open_stability_gain_positive_fraction']['v0625_exact']:.6f}`.",
        f"Positive open-stability-gain fraction, v0.6.25 nonexact: `{result['open_stability_gain_positive_fraction']['v0625_nonexact']:.6f}`.",
        f"Per-offset gain medians: `{result['per_offset_open_stability_gain_median']}`.",
        "",
        "Interpretation category is intentionally assigned only by the pre-frozen governance readout. No threshold, classifier, rescue or veto is authorized by this raw statistics bundle.",
    ]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    filtered: dict[str, list[dict]] = {}
    records: dict[str, list[dict]] = {}
    maps: dict[str, dict] = {}
    bars: dict[str, list[dict]] = {}
    closes: dict[str, list[float]] = {}
    states: dict[str, dict] = {}

    for view in VIEWS:
        filtered[view] = load_gz(find_one(args.input, f"filtered-{view}.json.gz"))
        records[view] = load_gz(find_one(args.input, f"records-{view}.json.gz"))
        maps[view] = {fkey(r): r for r in records[view]}
        bars[view], _ = load_development_bars(
            ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json"
        )
        closes[view] = [float(x["close"]) for x in bars[view]]
        states[view] = {}
        for row in records[view]:
            if bool(row["candidate_qualified"]):
                states[view][fkey(row)] = side_state(row, bars[view], closes[view], view)

    main_view = "5m_offset_0"
    pair_rows: list[dict] = []
    total = 0
    per_offset_counts: dict[str, dict] = {}

    for view in VIEWS[1:]:
        graph = build_edge_graph(
            filtered[main_view], filtered[view],
            time_field="five_filtered_occurrence_times",
            nominal_bar_minutes=5.0,
            require_phase=True,
        )
        fp = list(graph.mutual_unique_matches)
        if len(fp) != EXPECTED_FILTERED[view]:
            raise AssertionError(f"filtered control drift for {view}")
        strict = []
        for i, j in fp:
            a = maps[main_view].get(fkey(filtered[main_view][i]))
            b = maps[view].get(fkey(filtered[view][j]))
            if a is not None and b is not None and strict_anchor_edge(a, b, 5.0) is not None:
                strict.append((a, b))
        if len(strict) != EXPECTED_RAW[view]:
            raise AssertionError(f"raw strict control drift for {view}")
        if qmatrix(strict) != EXPECTED_V0618[view]:
            raise AssertionError(f"v0618 qualification matrix drift for {view}")
        bothq = [(a, b) for a, b in strict if a["candidate_qualified"] and b["candidate_qualified"]]
        total += len(bothq)

        d1_exact_offset = 0
        v25_exact_offset = 0
        for a, b in bothq:
            sa = states[main_view][fkey(a)]
            sb = states[view][fkey(b)]
            pm = harmless_pair_metrics(sa, sb)
            d1_exact = sa["D1"] == sb["D1"]
            v25_exact = sa["v0625"] == sb["v0625"]
            d1_exact_offset += int(d1_exact)
            v25_exact_offset += int(v25_exact)
            pair_rows.append({
                "offset_pair": view,
                "D1_main": sa["D1"], "D1_other": sb["D1"], "D1_exact": d1_exact,
                "v0625_main": sa["v0625"], "v0625_other": sb["v0625"], "v0625_exact": v25_exact,
                "pair_mean_abs_anchor_body": float((sa["mean_abs_anchor_body"] + sb["mean_abs_anchor_body"]) / 2.0),
                "pair_mean_abs_mean_oriented_anchor_body": float((abs(sa["mean_oriented_anchor_body"]) + abs(sb["mean_oriented_anchor_body"])) / 2.0),
                "pair_mean_abs_anchor_gap": float((sa["mean_abs_anchor_gap"] + sb["mean_abs_anchor_gap"]) / 2.0),
                "pair_mean_open_adjustment_l1": float((sa["open_adjustment_l1"] + sb["open_adjustment_l1"]) / 2.0),
                "pair_mean_open_adjustment_linf": float((sa["open_adjustment_linf"] + sb["open_adjustment_linf"]) / 2.0),
                "pair_mean_close_migration_l1": float((sa["close_migration_l1"] + sb["close_migration_l1"]) / 2.0),
                "pair_mean_open_migration_l1": float((sa["open_migration_l1"] + sb["open_migration_l1"]) / 2.0),
                **pm,
            })
        per_offset_counts[view] = {
            "pairs": len(bothq),
            "D1_exact_count": d1_exact_offset,
            "v0625_exact_count": v25_exact_offset,
        }

    if total != EXPECTED_BOTHQ or len(pair_rows) != EXPECTED_BOTHQ:
        raise AssertionError("pooled both-qualified control drift")
    d1_exact_count = sum(bool(r["D1_exact"]) for r in pair_rows)
    v25_exact_count = sum(bool(r["v0625_exact"]) for r in pair_rows)
    if d1_exact_count != EXPECTED_D1_EXACT_COUNT:
        raise AssertionError(f"D1 exact control drift: {d1_exact_count}")
    if v25_exact_count != EXPECTED_V0625_EXACT_COUNT:
        raise AssertionError(f"v0625 exact control drift: {v25_exact_count}")

    decisive = [r for r in pair_rows if r["v0625_main"] != "uncertain" and r["v0625_other"] != "uncertain"]
    decisive_agreement = sum(r["v0625_main"] == r["v0625_other"] for r in decisive) / len(decisive)
    opposite_conflicts = sum({r["v0625_main"], r["v0625_other"]} == {"uptrend", "downtrend"} for r in pair_rows)
    if abs(decisive_agreement - EXPECTED_V0625_DECISIVE_AGREEMENT) > 1e-12:
        raise AssertionError("v0625 decisive agreement control drift")
    if opposite_conflicts != EXPECTED_V0625_OPPOSITE_TREND_CONFLICTS:
        raise AssertionError("v0625 opposite-trend conflict control drift")

    d1_groups = {"exact": [r for r in pair_rows if r["D1_exact"]], "nonexact": [r for r in pair_rows if not r["D1_exact"]]}
    v25_groups = {"exact": [r for r in pair_rows if r["v0625_exact"]], "nonexact": [r for r in pair_rows if not r["v0625_exact"]]}

    rank = {
        "nonexact_mean_abs_anchor_body_gt_exact": rank_nonexact_gt_exact(v25_groups["nonexact"], v25_groups["exact"], "pair_mean_abs_anchor_body"),
        "nonexact_abs_mean_oriented_anchor_body_gt_exact": rank_nonexact_gt_exact(v25_groups["nonexact"], v25_groups["exact"], "pair_mean_abs_mean_oriented_anchor_body"),
        "nonexact_mean_abs_anchor_gap_gt_exact": rank_nonexact_gt_exact(v25_groups["nonexact"], v25_groups["exact"], "pair_mean_abs_anchor_gap"),
        "nonexact_open_adjustment_view_distance_l1_gt_exact": rank_nonexact_gt_exact(v25_groups["nonexact"], v25_groups["exact"], "open_adjustment_view_distance_l1"),
        "nonexact_open_stability_gain_l1_gt_exact": rank_nonexact_gt_exact(v25_groups["nonexact"], v25_groups["exact"], "open_stability_gain_l1"),
    }

    per_offset_gain_median = {}
    per_offset_group_summary = {}
    for view in VIEWS[1:]:
        rows = [r for r in pair_rows if r["offset_pair"] == view]
        exact = [r for r in rows if r["v0625_exact"]]
        nonexact = [r for r in rows if not r["v0625_exact"]]
        per_offset_gain_median[view] = {
            "all": numeric_summary([float(r["open_stability_gain_l1"]) for r in rows])["median"],
            "v0625_exact": numeric_summary([float(r["open_stability_gain_l1"]) for r in exact])["median"],
            "v0625_nonexact": numeric_summary([float(r["open_stability_gain_l1"]) for r in nonexact])["median"],
        }
        per_offset_group_summary[view] = {
            "counts": {"all": len(rows), "v0625_exact": len(exact), "v0625_nonexact": len(nonexact)},
            "all": summarize(rows),
            "v0625_exact": summarize(exact),
            "v0625_nonexact": summarize(nonexact),
        }

    result = {
        "schema": "two_wave_native_open_body_gap_direction_result@0.6.46",
        "formal_attribution": "v0646_native_open_body_gap_fixed_statistics_complete_pending_governance_category",
        "controls": {
            "filtered_pairs": 57029,
            "raw_strict_pairs": 29453,
            "both_v0618_qualified_pairs": total,
            "D1_exact_count": d1_exact_count,
            "v0625_exact_count": v25_exact_count,
            "v0625_decisive_agreement": float(decisive_agreement),
            "v0625_opposite_trend_conflicts": int(opposite_conflicts),
            "reproduced": True,
        },
        "D1_group_counts": {k: len(v) for k, v in d1_groups.items()},
        "D1_group_summary": {k: summarize(v) for k, v in d1_groups.items()},
        "v0625_group_counts": {k: len(v) for k, v in v25_groups.items()},
        "v0625_group_summary": {k: summarize(v) for k, v in v25_groups.items()},
        "v0625_threshold_free_rank_probabilities": rank,
        "open_stability_gain_positive_fraction": {
            "v0625_exact": positive_fraction([float(r["open_stability_gain_l1"]) for r in v25_groups["exact"]]),
            "v0625_nonexact": positive_fraction([float(r["open_stability_gain_l1"]) for r in v25_groups["nonexact"]]),
        },
        "per_offset_counts": per_offset_counts,
        "per_offset_open_stability_gain_median": per_offset_gain_median,
        "per_offset_group_summary": per_offset_group_summary,
        "pair_level_within_view_scalar_rule": "arithmetic_mean_of_main_and_other_view_values_for_rank_comparisons",
        "descriptor_menu_frozen": True,
        "interpretation_category": None,
        "gate_authorized": False,
        "recognizer_changed": False,
        "qualification_changed": False,
        "direction_winner_changed": False,
        "morphology_acceptance": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "production_authority": False,
    }

    (args.output / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_card(args.output / "RESULT_CARD.md", result)
    with gzip.open(args.output / "pair_rows.jsonl.gz", "wt", encoding="utf-8") as fh:
        for row in pair_rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
