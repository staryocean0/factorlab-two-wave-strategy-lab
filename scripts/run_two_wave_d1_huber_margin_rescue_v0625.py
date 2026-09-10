#!/usr/bin/env python3
"""Formal v0.6.25 D1-primary erosion-consensus Huber margin rescue replay."""
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
from factor_lab.visual_structure.two_wave.d1_huber_erosion_consensus_v0623 import (
    d1_primary_erosion_consensus_rescue,
)
from factor_lab.visual_structure.two_wave.d1_huber_margin_rescue_v0625 import (
    MIN_CONSENSUS_MARGIN,
    d1_primary_margin_rescue,
)
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import build_edge_graph
from scripts.run_two_wave_d1_huber_erosion_consensus_v0623 import (
    EXPECTED_BOTHQ,
    EXPECTED_D1_COVERAGE,
    EXPECTED_D1_EXACT,
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

EXPECTED_V0623_EXACT_COUNT = 1397
EXPECTED_V0623_EXACT = EXPECTED_V0623_EXACT_COUNT / EXPECTED_BOTHQ


def state(row, bars, closes, view):
    pair = reconstruct_pair(row, bars, view)
    d1 = str(pair["direction_versions"]["D1"])
    amp = float(pair["amplitude_unit_price"])
    raw = row["published_raw_occurrence_bars"]
    old = d1_primary_erosion_consensus_rescue(d1, closes, raw, amp)
    candidate = d1_primary_margin_rescue(d1, closes, raw, amp)
    if d1 != "uncertain":
        assert old["classification"] == d1
        assert candidate["classification"] == d1
        assert candidate["D1_decisive_overridden"] is False
    return {
        "D1": d1,
        "v0623": str(old["classification"]),
        "v0625": str(candidate["classification"]),
        "v0623_rescue": bool(old["rescue_applied"]),
        "v0625_rescue": bool(candidate["rescue_applied"]),
        "v0625_margin": candidate.get("consensus_margin_to_frozen_boundary"),
        "overridden": bool(candidate["D1_decisive_overridden"]),
    }


def write_card(path: Path, result: dict):
    d1 = result["pooled"]["D1"]
    old = result["pooled"]["v0623"]
    cand = result["pooled"]["v0625"]
    lines = [
        "# Two-Wave v0.6.25 D1-primary erosion-consensus Huber margin rescue result",
        "",
        f"Formal verdict: **`{result['verdict']}`**",
        "",
        f"Frozen consensus-margin threshold: **{MIN_CONSENSUS_MARGIN:.2f} amplitude units**.",
        f"D1 decisive overrides: **{result['rescue_audit']['D1_decisive_override_count']}**.",
        f"v0.6.23 rescues: **{result['rescue_audit']['v0623_rescued_record_count']}**.",
        f"v0.6.25 margin-qualified rescues: **{result['rescue_audit']['v0625_rescued_record_count']}**.",
        f"v0.6.23 rescues withheld only by the new margin gate: **{result['rescue_audit']['withheld_by_margin_count']}**.",
        "",
        "| metric | D1 | v0.6.23 | v0.6.25 |",
        "|---|---:|---:|---:|",
        f"| pooled exact agreement | {d1['exact_agreement']:.2%} | {old['exact_agreement']:.2%} | {cand['exact_agreement']:.2%} |",
        f"| pooled decisive coverage | {d1['pooled_decisive_coverage']:.2%} | {old['pooled_decisive_coverage']:.2%} | {cand['pooled_decisive_coverage']:.2%} |",
        f"| decisive agreement | {d1['decisive_agreement']:.2%} | {old['decisive_agreement']:.2%} | {cand['decisive_agreement']:.2%} |",
        f"| opposite trend conflicts | {d1['opposite_trend_conflict_count']} | {old['opposite_trend_conflict_count']} | {cand['opposite_trend_conflict_count']} |",
        "",
        "Per-offset exact agreement:",
        "",
        "| offset | D1 | v0.6.23 | v0.6.25 | delta vs D1 pp |",
        "|---|---:|---:|---:|---:|",
    ]
    for view, row in result["per_offset"].items():
        b = row["D1"]["exact_agreement"]
        o = row["v0623"]["exact_agreement"]
        c = row["v0625"]["exact_agreement"]
        lines.append(f"| {view} | {b:.2%} | {o:.2%} | {c:.2%} | {(c-b)*100:.2f} |")
    lines += ["", "Promotion gates:"]
    lines += [f"- {key}: **{value}**" for key, value in result["gates"].items()]
    lines += [
        "",
        "Qualification remained frozen at v0.6.18. Independent morphology acceptance remains false; no trading or production authority follows.",
    ]
    path.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    filtered, records, maps, bars, closes, states = {}, {}, {}, {}, {}, {}
    override_count = 0
    rescued_old = Counter()
    rescued_new = Counter()
    withheld_by_margin = 0

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
            if not bool(row["candidate_qualified"]):
                continue
            s = state(row, bars[view], closes[view], view)
            states[view][fkey(row)] = s
            override_count += int(s["overridden"])
            if s["v0623_rescue"]:
                rescued_old[s["v0623"]] += 1
            if s["v0625_rescue"]:
                rescued_new[s["v0625"]] += 1
            if s["v0623_rescue"] and not s["v0625_rescue"]:
                withheld_by_margin += 1
    assert override_count == 0

    main_view = "5m_offset_0"
    total_bothq = 0
    pooled_d1, pooled_old, pooled_new = [], [], []
    per_offset = {}

    for view in VIEWS[1:]:
        graph = build_edge_graph(
            filtered[main_view], filtered[view],
            time_field="five_filtered_occurrence_times",
            nominal_bar_minutes=5.0,
            require_phase=True,
        )
        filtered_pairs = list(graph.mutual_unique_matches)
        assert len(filtered_pairs) == EXPECTED_FILTERED[view]
        strict = []
        for i, j in filtered_pairs:
            left = maps[main_view].get(fkey(filtered[main_view][i]))
            right = maps[view].get(fkey(filtered[view][j]))
            if left is not None and right is not None and strict_anchor_edge(left, right, 5.0) is not None:
                strict.append((left, right))
        assert len(strict) == EXPECTED_RAW[view]
        assert qmatrix(strict) == EXPECTED_V0618[view]
        both = [(a, b) for a, b in strict if a["candidate_qualified"] and b["candidate_qualified"]]
        total_bothq += len(both)
        d1_pairs, old_pairs, new_pairs = [], [], []
        for left, right in both:
            ls = states[main_view][fkey(left)]
            rs = states[view][fkey(right)]
            d1_pairs.append((ls["D1"], rs["D1"]))
            old_pairs.append((ls["v0623"], rs["v0623"]))
            new_pairs.append((ls["v0625"], rs["v0625"]))
        pooled_d1 += d1_pairs
        pooled_old += old_pairs
        pooled_new += new_pairs
        per_offset[view] = {
            "D1": metrics(d1_pairs),
            "v0623": metrics(old_pairs),
            "v0625": metrics(new_pairs),
        }

    assert total_bothq == EXPECTED_BOTHQ
    d1 = metrics(pooled_d1)
    old = metrics(pooled_old)
    cand = metrics(pooled_new)
    assert abs(d1["exact_agreement"] - EXPECTED_D1_EXACT) <= 1e-12
    assert abs(d1["pooled_decisive_coverage"] - EXPECTED_D1_COVERAGE) <= 1e-12
    assert d1["decisive_agreement"] == 1.0
    assert d1["opposite_trend_conflict_count"] == 0
    assert old["exact_agreement_count"] == EXPECTED_V0623_EXACT_COUNT
    assert abs(old["exact_agreement"] - EXPECTED_V0623_EXACT) <= 1e-12

    shares = cand["pooled_decisive_label_shares"]
    gates = {
        "upstream_controls": True,
        "D1_controls_reproduced": True,
        "v0623_control_reproduced": True,
        "D1_decisive_override_zero": override_count == 0,
        "all_offsets_exact_agreement_nonworse": all(
            row["v0625"]["exact_agreement"] >= row["D1"]["exact_agreement"]
            for row in per_offset.values()
        ),
        "pooled_exact_agreement_nonworse": cand["exact_agreement"] >= d1["exact_agreement"],
        "pooled_decisive_coverage_material": (
            cand["pooled_decisive_coverage"] >= 0.65
            and cand["pooled_decisive_coverage"] >= d1["pooled_decisive_coverage"] + 0.15
        ),
        "each_offset_side_decisive_coverage_at_least_55pct": all(
            min(row["v0625"]["main_decisive_coverage"], row["v0625"]["other_decisive_coverage"]) >= 0.55
            for row in per_offset.values()
        ),
        "pooled_decisive_agreement_at_least_99_5pct": cand["decisive_agreement"] >= 0.995,
        "opposite_trend_conflict_zero": cand["opposite_trend_conflict_count"] == 0,
        "decisive_class_diversity": (
            shares.get("uptrend", 0) >= 0.15
            and shares.get("downtrend", 0) >= 0.15
            and shares.get("range", 0) >= 0.02
        ),
        "nonzero_margin_rescue": sum(rescued_new.values()) > 0,
    }
    passed = all(gates.values())
    result = {
        "schema": "two_wave_d1_huber_margin_rescue_result@0.6.25",
        "verdict": (
            "v0625_D1_primary_erosion_consensus_margin_rescue_direction_research_component_pass"
            if passed else
            "v0625_D1_primary_erosion_consensus_margin_rescue_direction_rejected"
        ),
        "controls": {
            "filtered_pairs": 57029,
            "raw_strict_pairs": 29453,
            "both_v0618_qualified_pairs": total_bothq,
            "D1_exact_count": d1["exact_agreement_count"],
            "v0623_exact_count": old["exact_agreement_count"],
            "reproduced": True,
        },
        "rescue_audit": {
            "D1_decisive_override_count": override_count,
            "v0623_rescued_record_count": sum(rescued_old.values()),
            "v0625_rescued_record_count": sum(rescued_new.values()),
            "v0625_rescued_label_counts": dict(rescued_new),
            "withheld_by_margin_count": withheld_by_margin,
            "minimum_consensus_margin": MIN_CONSENSUS_MARGIN,
        },
        "pooled": {"D1": d1, "v0623": old, "v0625": cand},
        "per_offset": per_offset,
        "gates": gates,
        "qualification_policy": "v0.6.18",
        "qualification_changed": False,
        "morphology_acceptance": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "production_authority": False,
    }
    (args.output / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    write_card(args.output / "RESULT_CARD.md", result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
