#!/usr/bin/env python3
"""Formal read-only v0.6.26 attribution of v0.6.25 residual direction failures."""
from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import build_edge_graph
from factor_lab.visual_structure.two_wave.v0625_residual_attribution_v0626 import (
    attribution_verdict,
    d1_topology,
    range_relative_margin,
    rescue_topology,
    transition_category,
)

SPEC = importlib.util.spec_from_file_location(
    "v0625_runner", ROOT / "scripts/run_two_wave_d1_huber_margin_rescue_v0625.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load frozen v0625 runner")
v0625 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v0625)

STATES = ("range", "uptrend", "downtrend")
CATEGORIES = ("retained_exact", "introduced_harm", "repaired_old_nonexact", "persistent_nonexact")


def quantiles(values):
    if not values:
        return {"count": 0}
    arr = np.asarray(values, dtype=float)
    return {
        "count": int(len(arr)),
        "min": float(arr.min()),
        "p10": float(np.quantile(arr, 0.10)),
        "p25": float(np.quantile(arr, 0.25)),
        "median": float(np.quantile(arr, 0.50)),
        "p75": float(np.quantile(arr, 0.75)),
        "p90": float(np.quantile(arr, 0.90)),
        "max": float(arr.max()),
        "mean": float(arr.mean()),
    }


def state_margin_summary(rows):
    by_state = {}
    for state in STATES:
        group = [r for r in rows if r["state"] == state]
        kept = [r for r in group if r["kept"]]
        withheld = [r for r in group if not r["kept"]]
        entry = {
            "candidate_count": len(group),
            "kept_count": len(kept),
            "withheld_count": len(withheld),
            "keep_fraction": len(kept) / len(group) if group else 0.0,
            "margin_all": quantiles([r["margin"] for r in group]),
            "margin_kept": quantiles([r["margin"] for r in kept]),
            "margin_withheld": quantiles([r["margin"] for r in withheld]),
        }
        if state == "range":
            entry["range_relative_margin_all"] = quantiles([range_relative_margin(r["margin"]) for r in group])
            entry["range_relative_margin_kept"] = quantiles([range_relative_margin(r["margin"]) for r in kept])
            entry["range_relative_margin_withheld"] = quantiles([range_relative_margin(r["margin"]) for r in withheld])
        by_state[state] = entry
    trend = [r for r in rows if r["state"] in {"uptrend", "downtrend"}]
    trend_kept = [r for r in trend if r["kept"]]
    return by_state, (len(trend_kept) / len(trend) if trend else 0.0)


def write_card(path: Path, result: dict):
    mg = result["single_view_margin_geometry"]
    lines = [
        "# Two-Wave v0.6.26 v0.6.25 residual direction attribution",
        "",
        f"Formal attribution: **`{result['formal_attribution']}`**",
        "",
        "v0.6.26 changes no recognizer rule, threshold, qualification policy, or authority pointer.",
        "",
        "## Frozen control reproduction",
        "",
        f"- filtered pairs: **{result['controls']['filtered_pairs']}**",
        f"- raw strict pairs: **{result['controls']['raw_strict_pairs']}**",
        f"- both-v0.6.18-qualified pairs: **{result['controls']['both_v0618_qualified_pairs']}**",
        f"- D1 exact: **{result['controls']['D1_exact_count']}/1462**",
        f"- v0.6.23 exact: **{result['controls']['v0623_exact_count']}/1462**",
        f"- v0.6.25 exact: **{result['controls']['v0625_exact_count']}/1462**",
        "",
        "## D1 -> v0.6.25 pair transitions",
        "",
        "| category | count |",
        "|---|---:|",
    ]
    for key in CATEGORIES:
        lines.append(f"| {key} | {result['transition_counts'].get(key, 0)} |")
    lines += [
        "",
        "## v0.6.23 rescue candidates kept by v0.6.25 margin gate",
        "",
        "| state | candidates | kept | withheld | keep fraction |",
        "|---|---:|---:|---:|---:|",
    ]
    for state in STATES:
        row = mg["by_state"][state]
        lines.append(
            f"| {state} | {row['candidate_count']} | {row['kept_count']} | {row['withheld_count']} | {row['keep_fraction']:.2%} |"
        )
    lines += [
        "",
        f"Range keep fraction: **{mg['range_keep_fraction']:.2%}**",
        f"Trend combined keep fraction: **{mg['trend_keep_fraction']:.2%}**",
        f"Introduced-harm one-sided rescue fraction: **{result['verdict_inputs']['introduced_harm_one_sided_fraction']:.2%}**",
        "",
        "Frozen attribution gates:",
        f"- Range keep <= 0.5 * Trend keep: **{result['verdict_inputs']['range_suppression_gate']}**",
        f"- introduced harm one-sided >= 80%: **{result['verdict_inputs']['introduced_harm_one_sided_gate']}**",
        "",
        "This result is diagnostic only. D1 remains the historical direction stability baseline; v0.6.18 remains qualification champion; morphology acceptance remains false.",
    ]
    path.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    filtered, records, maps, bars, closes, states = {}, {}, {}, {}, {}, {}
    single_view_margin_rows = []

    for view in v0625.VIEWS:
        filtered[view] = v0625.load_gz(v0625.find_one(args.input, f"filtered-{view}.json.gz"))
        records[view] = v0625.load_gz(v0625.find_one(args.input, f"records-{view}.json.gz"))
        maps[view] = {v0625.fkey(r): r for r in records[view]}
        bars[view], _ = load_development_bars(
            ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json"
        )
        closes[view] = [float(x["close"]) for x in bars[view]]
        states[view] = {}
        for row in records[view]:
            if not bool(row["candidate_qualified"]):
                continue
            s = v0625.state(row, bars[view], closes[view], view)
            states[view][v0625.fkey(row)] = s
            if s["D1"] == "uncertain" and s["v0623_rescue"]:
                margin = s["v0625_margin"]
                if margin is None:
                    raise AssertionError("v0623 decisive rescue must expose frozen consensus margin")
                single_view_margin_rows.append({
                    "view": view,
                    "state": s["v0623"],
                    "margin": float(margin),
                    "kept": bool(s["v0625_rescue"]),
                })

    transition_counts = Counter()
    per_offset = {}
    by_category_topology = defaultdict(Counter)
    by_category_d1_topology = defaultdict(Counter)
    by_category_rescue_state = defaultdict(Counter)
    introduced_harm_topologies = []
    details = []
    pooled_d1, pooled_old, pooled_new = [], [], []
    total_bothq = 0
    main_view = "5m_offset_0"

    for view in v0625.VIEWS[1:]:
        graph = build_edge_graph(
            filtered[main_view], filtered[view],
            time_field="five_filtered_occurrence_times",
            nominal_bar_minutes=5.0,
            require_phase=True,
        )
        fp = list(graph.mutual_unique_matches)
        assert len(fp) == v0625.EXPECTED_FILTERED[view]
        strict = []
        for i, j in fp:
            left = maps[main_view].get(v0625.fkey(filtered[main_view][i]))
            right = maps[view].get(v0625.fkey(filtered[view][j]))
            if left is not None and right is not None and strict_anchor_edge(left, right, 5.0) is not None:
                strict.append((left, right))
        assert len(strict) == v0625.EXPECTED_RAW[view]
        assert v0625.qmatrix(strict) == v0625.EXPECTED_V0618[view]
        both = [(a, b) for a, b in strict if a["candidate_qualified"] and b["candidate_qualified"]]
        total_bothq += len(both)
        offset_counts = Counter()
        for left, right in both:
            ls = states[main_view][v0625.fkey(left)]
            rs = states[view][v0625.fkey(right)]
            pooled_d1.append((ls["D1"], rs["D1"]))
            pooled_old.append((ls["v0623"], rs["v0623"]))
            pooled_new.append((ls["v0625"], rs["v0625"]))
            category = transition_category(ls["D1"], rs["D1"], ls["v0625"], rs["v0625"])
            rtop = rescue_topology(ls["v0625_rescue"], rs["v0625_rescue"])
            dtop = d1_topology(ls["D1"], rs["D1"])
            transition_counts[category] += 1
            offset_counts[category] += 1
            by_category_topology[category][rtop] += 1
            by_category_d1_topology[category][dtop] += 1
            if category == "introduced_harm":
                introduced_harm_topologies.append(rtop)
            for side in (ls, rs):
                if side["v0625_rescue"]:
                    by_category_rescue_state[category][side["v0625"]] += 1
            if category != "retained_exact":
                details.append({
                    "offset": view,
                    "category": category,
                    "rescue_topology": rtop,
                    "D1_topology": dtop,
                    "main": ls,
                    "other": rs,
                })
        per_offset[view] = dict(offset_counts)

    assert total_bothq == v0625.EXPECTED_BOTHQ
    d1 = v0625.metrics(pooled_d1)
    old = v0625.metrics(pooled_old)
    new = v0625.metrics(pooled_new)
    assert d1["exact_agreement_count"] == 1400
    assert old["exact_agreement_count"] == 1397
    assert new["exact_agreement_count"] == 1402
    assert abs(d1["pooled_decisive_coverage"] - v0625.EXPECTED_D1_COVERAGE) <= 1e-12
    assert abs(new["pooled_decisive_coverage"] - 0.7086183310533516) <= 1e-12
    assert new["decisive_agreement"] == 1.0
    assert new["opposite_trend_conflict_count"] == 0
    assert sum(transition_counts.values()) == total_bothq

    by_state, trend_keep_fraction = state_margin_summary(single_view_margin_rows)
    range_keep_fraction = by_state["range"]["keep_fraction"]
    verdict_inputs = attribution_verdict(
        range_keep_fraction, trend_keep_fraction, introduced_harm_topologies
    )

    result = {
        "schema": "two_wave_v0625_residual_direction_attribution@0.6.26",
        "formal_attribution": verdict_inputs["verdict"],
        "controls": {
            "filtered_pairs": 57029,
            "raw_strict_pairs": 29453,
            "both_v0618_qualified_pairs": total_bothq,
            "D1_exact_count": d1["exact_agreement_count"],
            "v0623_exact_count": old["exact_agreement_count"],
            "v0625_exact_count": new["exact_agreement_count"],
            "D1_decisive_coverage": d1["pooled_decisive_coverage"],
            "v0625_decisive_coverage": new["pooled_decisive_coverage"],
            "v0625_decisive_agreement": new["decisive_agreement"],
            "v0625_opposite_trend_conflicts": new["opposite_trend_conflict_count"],
            "reproduced": True,
        },
        "transition_counts": dict(transition_counts),
        "per_offset_transition_counts": per_offset,
        "by_transition": {
            category: {
                "rescue_topology_counts": dict(by_category_topology[category]),
                "D1_topology_counts": dict(by_category_d1_topology[category]),
                "rescued_state_counts": dict(by_category_rescue_state[category]),
            }
            for category in CATEGORIES
        },
        "single_view_margin_geometry": {
            "candidate_record_count": len(single_view_margin_rows),
            "range_keep_fraction": range_keep_fraction,
            "trend_keep_fraction": trend_keep_fraction,
            "by_state": by_state,
        },
        "verdict_inputs": verdict_inputs,
        "changed_recognizer_rules": [],
        "qualification_policy": "v0.6.18",
        "morphology_acceptance": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "production_authority": False,
    }
    (args.output / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    with gzip.open(args.output / "nonexact_pair_details.jsonl.gz", "wt", encoding="utf-8") as fh:
        for row in details:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    write_card(args.output / "RESULT_CARD.md", result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
