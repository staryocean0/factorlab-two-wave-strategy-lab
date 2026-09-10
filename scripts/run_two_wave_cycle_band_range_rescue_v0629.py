#!/usr/bin/env python3
"""Formal v0.6.29 cycle-band Range rescue replay."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.d1_cycle_band_range_rescue_v0629 import (
    MIN_IQR_OVERLAP,
    d1_primary_cycle_band_range_rescue,
)
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
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
    metrics,
    qmatrix,
    reconstruct_pair,
)

EXPECTED_V0625_EXACT_COUNT = 1402
EXPECTED_V0625_COVERAGE = 0.7086183310533516
EXPECTED_V0625_RANGE_LABELS = 22
EXPECTED_V0625_EXACT_BY_OFFSET = {
    "5m_offset_1": 380,
    "5m_offset_2": 271,
    "5m_offset_3": 292,
    "5m_offset_4": 459,
}


def state(row, bars, closes, view):
    pair = reconstruct_pair(row, bars, view)
    d1 = str(pair["direction_versions"]["D1"])
    cand = d1_primary_cycle_band_range_rescue(
        d1,
        closes,
        row["published_raw_occurrence_bars"],
        float(pair["amplitude_unit_price"]),
    )
    old = str(cand["v0625_classification"])
    new = str(cand["classification"])
    if old != new:
        assert old == "uncertain" and new == "range"
    return {
        "D1": d1,
        "v0625": old,
        "v0629": new,
        "overridden": bool(cand["D1_decisive_overridden"]),
        "new_range": bool(cand["new_range_rescue_applied"]),
        "band_checked": bool(cand["cycle_band_checked"]),
        "overlap": cand.get("cycle_band_overlap_coefficient"),
    }


def write_card(path, result):
    b = result["pooled"]["v0625"]
    c = result["pooled"]["v0629"]
    lines = [
        "# Two-Wave v0.6.29 cycle-band Range rescue result",
        "",
        f"Formal verdict: **`{result['verdict']}`**",
        "",
        f"Frozen cycle-IQR overlap threshold: **{MIN_IQR_OVERLAP:.2f}**.",
        f"D1 decisive overrides: **{result['audit']['D1_decisive_override_count']}**.",
        f"New Range rescues beyond v0.6.25: **{result['audit']['new_range_rescue_count']}**.",
        "",
        "| metric | v0.6.25 | v0.6.29 |",
        "|---|---:|---:|",
        f"| pooled exact agreement | {b['exact_agreement']:.2%} | {c['exact_agreement']:.2%} |",
        f"| pooled decisive coverage | {b['pooled_decisive_coverage']:.2%} | {c['pooled_decisive_coverage']:.2%} |",
        f"| decisive agreement | {b['decisive_agreement']:.2%} | {c['decisive_agreement']:.2%} |",
        f"| Range share among decisive labels | {b['pooled_decisive_label_shares'].get('range',0):.2%} | {c['pooled_decisive_label_shares'].get('range',0):.2%} |",
        f"| opposite trend conflicts | {b['opposite_trend_conflict_count']} | {c['opposite_trend_conflict_count']} |",
        "",
        "Per-offset exact agreement:",
        "",
        "| offset | v0.6.25 | v0.6.29 | delta pp |",
        "|---|---:|---:|---:|",
    ]
    for view, row in result["per_offset"].items():
        old = row["v0625"]["exact_agreement"]
        new = row["v0629"]["exact_agreement"]
        lines.append(f"| {view} | {old:.2%} | {new:.2%} | {(new-old)*100:.2f} |")
    lines += ["", "Promotion gates:"]
    lines += [f"- {k}: **{v}**" for k, v in result["gates"].items()]
    lines += ["", "Qualification remains v0.6.18; morphology acceptance, trading and production authority remain false."]
    path.write_text("\n".join(lines) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    filtered, records, maps, bars, closes, states = {}, {}, {}, {}, {}, {}
    override_count = 0
    new_range_count = 0
    checked_count = 0
    overlap_values = []

    for view in VIEWS:
        filtered[view] = load_gz(find_one(args.input, f"filtered-{view}.json.gz"))
        records[view] = load_gz(find_one(args.input, f"records-{view}.json.gz"))
        maps[view] = {fkey(r): r for r in records[view]}
        bars[view], _ = load_development_bars(ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json")
        closes[view] = [float(x["close"]) for x in bars[view]]
        states[view] = {}
        for row in records[view]:
            if not bool(row["candidate_qualified"]):
                continue
            s = state(row, bars[view], closes[view], view)
            states[view][fkey(row)] = s
            override_count += int(s["overridden"])
            new_range_count += int(s["new_range"])
            checked_count += int(s["band_checked"])
            if s["overlap"] is not None:
                overlap_values.append(float(s["overlap"]))
    assert override_count == 0

    main_view = "5m_offset_0"
    total_bothq = 0
    pooled_old, pooled_new = [], []
    per_offset = {}
    pair_change_topology = Counter()

    for view in VIEWS[1:]:
        graph = build_edge_graph(filtered[main_view], filtered[view], time_field="five_filtered_occurrence_times", nominal_bar_minutes=5.0, require_phase=True)
        fp = list(graph.mutual_unique_matches)
        assert len(fp) == EXPECTED_FILTERED[view]
        strict = []
        for i, j in fp:
            left = maps[main_view].get(fkey(filtered[main_view][i]))
            right = maps[view].get(fkey(filtered[view][j]))
            if left is not None and right is not None and strict_anchor_edge(left, right, 5.0) is not None:
                strict.append((left, right))
        assert len(strict) == EXPECTED_RAW[view]
        assert qmatrix(strict) == EXPECTED_V0618[view]
        both = [(a, b) for a, b in strict if a["candidate_qualified"] and b["candidate_qualified"]]
        total_bothq += len(both)
        old_pairs, new_pairs = [], []
        for left, right in both:
            ls = states[main_view][fkey(left)]
            rs = states[view][fkey(right)]
            old_pair = (ls["v0625"], rs["v0625"])
            new_pair = (ls["v0629"], rs["v0629"])
            old_pairs.append(old_pair)
            new_pairs.append(new_pair)
            lc = ls["v0625"] != ls["v0629"]
            rc = rs["v0625"] != rs["v0629"]
            pair_change_topology["both" if lc and rc else "main_only" if lc else "other_only" if rc else "none"] += 1
        pooled_old += old_pairs
        pooled_new += new_pairs
        per_offset[view] = {"v0625": metrics(old_pairs), "v0629": metrics(new_pairs)}
        assert per_offset[view]["v0625"]["exact_agreement_count"] == EXPECTED_V0625_EXACT_BY_OFFSET[view]

    assert total_bothq == EXPECTED_BOTHQ
    old = metrics(pooled_old)
    cand = metrics(pooled_new)
    assert old["exact_agreement_count"] == EXPECTED_V0625_EXACT_COUNT
    assert abs(old["pooled_decisive_coverage"] - EXPECTED_V0625_COVERAGE) <= 1e-12
    assert old["pooled_label_counts"].get("range", 0) == EXPECTED_V0625_RANGE_LABELS
    assert old["decisive_agreement"] == 1.0
    assert old["opposite_trend_conflict_count"] == 0

    shares = cand["pooled_decisive_label_shares"]
    gates = {
        "upstream_controls": True,
        "D1_decisive_override_zero": override_count == 0,
        "all_changes_are_uncertain_to_range": True,
        "all_offsets_exact_nonworse_vs_v0625": all(row["v0629"]["exact_agreement"] >= row["v0625"]["exact_agreement"] for row in per_offset.values()),
        "pooled_exact_plus_0_20pp_vs_v0625": cand["exact_agreement"] >= old["exact_agreement"] + 0.002,
        "pooled_decisive_coverage_plus_1pp": cand["pooled_decisive_coverage"] >= old["pooled_decisive_coverage"] + 0.01,
        "pooled_decisive_agreement_at_least_99_5pct": cand["decisive_agreement"] >= 0.995,
        "opposite_trend_conflict_zero": cand["opposite_trend_conflict_count"] == 0,
        "decisive_class_diversity": shares.get("range", 0) >= 0.02 and shares.get("uptrend", 0) >= 0.15 and shares.get("downtrend", 0) >= 0.15,
    }
    passed = all(gates.values())
    result = {
        "schema": "two_wave_cycle_band_range_rescue_result@0.6.29",
        "verdict": "v0629_cycle_band_range_rescue_direction_research_component_pass" if passed else "v0629_cycle_band_range_rescue_direction_rejected",
        "controls": {"filtered_pairs": 57029, "raw_strict_pairs": 29453, "both_v0618_qualified_pairs": total_bothq, "v0625_exact_count": old["exact_agreement_count"], "reproduced": True},
        "audit": {"D1_decisive_override_count": override_count, "new_range_rescue_count": new_range_count, "cycle_band_checked_count": checked_count, "pair_change_topology": dict(pair_change_topology), "minimum_iqr_overlap": MIN_IQR_OVERLAP, "overlap_min": min(overlap_values) if overlap_values else None, "overlap_max": max(overlap_values) if overlap_values else None},
        "pooled": {"v0625": old, "v0629": cand},
        "per_offset": per_offset,
        "gates": gates,
        "qualification_policy": "v0.6.18",
        "qualification_changed": False,
        "morphology_acceptance": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "production_authority": False,
    }
    (args.output / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_card(args.output / "RESULT_CARD.md", result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
