#!/usr/bin/env python3
"""Formal v0.6.37 phase-balanced Wasserstein Range replay."""
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
from factor_lab.visual_structure.two_wave.d1_phase_balanced_wasserstein_range_v0637 import (
    LEG_MASS,
    RANGE_W1_MAX,
    d1_primary_phase_balanced_wasserstein_range_rescue,
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
from scripts.run_two_wave_mutual_median_range_rescue_v0631 import (
    EXPECTED_V0625_EXACT_BY_OFFSET,
    EXPECTED_V0625_EXACT_COUNT,
    EXPECTED_V0625_COVERAGE,
    EXPECTED_V0625_RANGE_LABELS,
)


def state(row, bars, closes, view):
    pair = reconstruct_pair(row, bars, view)
    d1 = str(pair["direction_versions"]["D1"])
    out = d1_primary_phase_balanced_wasserstein_range_rescue(
        d1,
        closes,
        row["published_raw_occurrence_bars"],
        float(pair["amplitude_unit_price"]),
    )
    old = str(out["v0625_classification"])
    new = str(out["classification"])
    if old != new:
        assert old == "uncertain" and new == "range"
        assert bool(out.get("new_range_rescue_applied", False))
    return {
        "v0625": old,
        "v0637": new,
        "changed": old != new,
        "override": bool(out.get("D1_decisive_overridden", False)),
        "max_phase_balanced_w1": out.get(
            "max_normalized_phase_balanced_cycle_wasserstein"
        ),
    }


def write_card(path: Path, result: dict) -> None:
    b = result["pooled"]["v0625"]
    c = result["pooled"]["v0637"]
    lines = [
        "# Two-Wave v0.6.37 phase-balanced Wasserstein Range result",
        "",
        f"Formal verdict: **`{result['verdict']}`**",
        "",
        f"New Range rescues: **{result['audit']['new_range_rescue_count']}**. D1/v0.6.25 decisive overrides: **{result['audit']['D1_decisive_override_count']}**.",
        "",
        "| metric | v0.6.25 | v0.6.37 |",
        "|---|---:|---:|",
        f"| pooled exact agreement | {b['exact_agreement']:.2%} | {c['exact_agreement']:.2%} |",
        f"| pooled decisive coverage | {b['pooled_decisive_coverage']:.2%} | {c['pooled_decisive_coverage']:.2%} |",
        f"| decisive agreement | {b['decisive_agreement']:.2%} | {c['decisive_agreement']:.2%} |",
        f"| Range decisive share | {b['pooled_decisive_label_shares'].get('range', 0):.2%} | {c['pooled_decisive_label_shares'].get('range', 0):.2%} |",
        "",
        "Per-offset exact agreement:",
        "",
        "| offset | v0.6.25 | v0.6.37 | delta pp |",
        "|---|---:|---:|---:|",
    ]
    for view, row in result["per_offset"].items():
        a = row["v0625"]["exact_agreement"]
        n = row["v0637"]["exact_agreement"]
        lines.append(f"| {view} | {a:.2%} | {n:.2%} | {(n-a)*100:.2f} |")
    lines += ["", "Promotion gates:"] + [
        f"- {k}: **{v}**" for k, v in result["gates"].items()
    ]
    lines += [
        "",
        "Qualification remains v0.6.18. Independent morphology acceptance, trading and production authority remain false.",
    ]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    filtered = {}
    records = {}
    maps = {}
    bars = {}
    closes = {}
    states = {}
    override = 0
    rescued = 0

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
            override += int(s["override"])
            rescued += int(s["changed"])
    assert override == 0

    main_view = "5m_offset_0"
    total = 0
    pooled_old = []
    pooled_new = []
    per_offset = {}
    topology = Counter()

    for view in VIEWS[1:]:
        graph = build_edge_graph(
            filtered[main_view],
            filtered[view],
            time_field="five_filtered_occurrence_times",
            nominal_bar_minutes=5.0,
            require_phase=True,
        )
        fp = list(graph.mutual_unique_matches)
        assert len(fp) == EXPECTED_FILTERED[view]
        strict = []
        for i, j in fp:
            a = maps[main_view].get(fkey(filtered[main_view][i]))
            b = maps[view].get(fkey(filtered[view][j]))
            if a is not None and b is not None and strict_anchor_edge(a, b, 5.0) is not None:
                strict.append((a, b))
        assert len(strict) == EXPECTED_RAW[view]
        assert qmatrix(strict) == EXPECTED_V0618[view]
        both = [
            (a, b)
            for a, b in strict
            if a["candidate_qualified"] and b["candidate_qualified"]
        ]
        total += len(both)
        old_pairs = []
        new_pairs = []
        for a, b in both:
            sa = states[main_view][fkey(a)]
            sb = states[view][fkey(b)]
            op = (sa["v0625"], sb["v0625"])
            npair = (sa["v0637"], sb["v0637"])
            old_pairs.append(op)
            new_pairs.append(npair)
            lc = op[0] != npair[0]
            rc = op[1] != npair[1]
            topology[
                "both" if lc and rc else "main_only" if lc else "other_only" if rc else "none"
            ] += 1
        pooled_old += old_pairs
        pooled_new += new_pairs
        per_offset[view] = {"v0625": metrics(old_pairs), "v0637": metrics(new_pairs)}
        assert (
            per_offset[view]["v0625"]["exact_agreement_count"]
            == EXPECTED_V0625_EXACT_BY_OFFSET[view]
        )

    assert total == EXPECTED_BOTHQ
    old = metrics(pooled_old)
    cand = metrics(pooled_new)
    assert old["exact_agreement_count"] == EXPECTED_V0625_EXACT_COUNT
    assert abs(old["pooled_decisive_coverage"] - EXPECTED_V0625_COVERAGE) <= 1e-12
    assert old["pooled_label_counts"].get("range", 0) == EXPECTED_V0625_RANGE_LABELS

    shares = cand["pooled_decisive_label_shares"]
    gates = {
        "upstream_controls": True,
        "D1_v0625_decisive_override_zero": override == 0,
        "all_changes_uncertain_to_range": True,
        "all_offsets_exact_nonworse_vs_v0625": all(
            r["v0637"]["exact_agreement"] >= r["v0625"]["exact_agreement"]
            for r in per_offset.values()
        ),
        "pooled_exact_plus_0_20pp": cand["exact_agreement"]
        >= old["exact_agreement"] + 0.002,
        "pooled_decisive_coverage_plus_1pp": cand["pooled_decisive_coverage"]
        >= old["pooled_decisive_coverage"] + 0.01,
        "pooled_decisive_agreement_at_least_99_5pct": cand["decisive_agreement"] >= 0.995,
        "opposite_trend_conflict_zero": cand["opposite_trend_conflict_count"] == 0,
        "decisive_class_diversity": shares.get("range", 0) >= 0.02
        and shares.get("uptrend", 0) >= 0.15
        and shares.get("downtrend", 0) >= 0.15,
    }
    passed = all(gates.values())
    result = {
        "schema": "two_wave_phase_balanced_wasserstein_range_result@0.6.37",
        "verdict": "v0637_phase_balanced_wasserstein_range_direction_research_component_pass"
        if passed
        else "v0637_phase_balanced_wasserstein_range_direction_rejected",
        "controls": {
            "filtered_pairs": 57029,
            "raw_strict_pairs": 29453,
            "both_v0618_qualified_pairs": total,
            "v0625_exact_count": old["exact_agreement_count"],
            "reproduced": True,
        },
        "audit": {
            "D1_decisive_override_count": override,
            "new_range_rescue_count": rescued,
            "pair_change_topology": dict(topology),
            "range_w1_max": RANGE_W1_MAX,
            "leg_probability_mass": LEG_MASS,
            "phase_balanced": True,
            "all_four_supports_required": True,
        },
        "pooled": {"v0625": old, "v0637": cand},
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
