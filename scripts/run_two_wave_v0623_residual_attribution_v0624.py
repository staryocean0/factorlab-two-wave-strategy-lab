#!/usr/bin/env python3
"""Formal read-only v0.6.24 attribution of v0.6.23 residual direction disagreement."""
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
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.d1_huber_erosion_consensus_v0623 import (
    d1_primary_erosion_consensus_rescue,
)
from factor_lab.visual_structure.two_wave.d1_semantic_attribution_v055 import diagnose_with_subtype
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import build_edge_graph
from factor_lab.visual_structure.two_wave.v0623_residual_attribution_v0624 import (
    consensus_margin_and_span,
    d1_pair_topology,
    pair_transition_category,
    rescue_topology,
)

SPEC = importlib.util.spec_from_file_location(
    "v0623_runner", ROOT / "scripts/run_two_wave_d1_huber_erosion_consensus_v0623.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load frozen v0623 runner")
v0623 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v0623)

VIEWS = tuple(f"5m_offset_{i}" for i in range(5))
EXPECTED_V0623_EXACT_COUNT = 1397
EXPECTED_V0623_EXACT = 0.9555403556771546
EXPECTED_V0623_COVERAGE = 0.7855677154582763
TARGET_GROUPS = ("introduced_harm", "repaired_old_nonexact", "retained_exact")


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


def side_state(row, bars, closes, view):
    pair = v0623.reconstruct_pair(row, bars, view)
    d1 = str(pair["direction_versions"]["D1"])
    amp = float(pair["amplitude_unit_price"])
    candidate = d1_primary_erosion_consensus_rescue(
        d1, closes, row["published_raw_occurrence_bars"], amp
    )
    subtype = None
    margin = None
    span = None
    support_states = None
    support_scores = None
    if d1 == "uncertain":
        subtype = diagnose_with_subtype(pair)["uncertain_subtype"]
        support_states = candidate["support_states"]
        support_scores = candidate["support_scores"]
        if candidate["rescue_applied"]:
            robust = consensus_margin_and_span(
                support_states, support_scores, candidate["erosion_consensus_state"]
            )
            margin = robust["consensus_margin_to_frozen_boundary"]
            span = robust["support_score_span"]
    return {
        "D1": d1,
        "v0623": str(candidate["classification"]),
        "rescued": bool(candidate["rescue_applied"]),
        "rescue_label": str(candidate["classification"]) if candidate["rescue_applied"] else None,
        "uncertain_subtype": subtype,
        "consensus_margin_to_frozen_boundary": margin,
        "support_score_span": span,
        "support_states": support_states,
        "support_scores": support_scores,
    }


def write_card(path: Path, result: dict):
    t = result["transition_counts"]
    lines = [
        "# Two-Wave v0.6.24 v0.6.23 residual direction attribution",
        "",
        "v0.6.24 changes no recognizer rule.",
        "",
        "## Frozen control reproduction",
        "",
        f"- pairs: **{result['controls']['both_v0618_qualified_pairs']}**",
        f"- D1 exact: **{result['controls']['D1_exact_agreement']:.4%}**",
        f"- v0.6.23 exact: **{result['controls']['v0623_exact_agreement']:.4%}**",
        f"- v0.6.23 decisive coverage: **{result['controls']['v0623_decisive_coverage']:.4%}**",
        "",
        "## Pair transition accounting",
        "",
        "| category | count |",
        "|---|---:|",
    ]
    for key in ("retained_exact", "introduced_harm", "repaired_old_nonexact", "persistent_nonexact"):
        lines.append(f"| {key} | {t.get(key,0)} |")
    lines += ["", "## Introduced-harm topology", ""]
    for key, value in result["by_transition"]["introduced_harm"]["rescue_topology_counts"].items():
        lines.append(f"- {key}: **{value}**")
    lines += ["", "## Rescued-side uncertain subtypes", ""]
    for group in TARGET_GROUPS:
        lines.append(f"### {group}")
        counts = result["by_transition"][group]["rescued_side_uncertain_subtype_counts"]
        if not counts:
            lines.append("- none")
        else:
            for key, value in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
                lines.append(f"- {key}: **{value}**")
        lines.append("")
    lines += [
        "No authority changes follow from this attribution alone. D1 remains the historical direction stability baseline and v0.6.18 remains qualification champion.",
        "",
        "`morphology_acceptance=false`  ",
        "`trade_authority=false`  ",
        "`production_authority=false`",
    ]
    path.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    filtered = {}
    records = {}
    maps = {}
    bars = {}
    closes = {}
    states = {}
    for view in VIEWS:
        filtered[view] = v0623.load_gz(v0623.find_one(args.input, f"filtered-{view}.json.gz"))
        records[view] = v0623.load_gz(v0623.find_one(args.input, f"records-{view}.json.gz"))
        maps[view] = {v0623.fkey(r): r for r in records[view]}
        bars[view], _ = load_development_bars(
            ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json"
        )
        closes[view] = [float(x["close"]) for x in bars[view]]
        states[view] = {
            v0623.fkey(r): side_state(r, bars[view], closes[view], view)
            for r in records[view] if bool(r["candidate_qualified"])
        }

    transition_counts = Counter()
    per_offset_transition = {}
    topology = defaultdict(lambda: Counter())
    d1_topology_counts = defaultdict(lambda: Counter())
    rescued_labels = defaultdict(lambda: Counter())
    subtype_counts = defaultdict(lambda: Counter())
    margins = defaultdict(list)
    spans = defaultdict(list)
    details = []
    pooled_d1 = []
    pooled_candidate = []
    total_bothq = 0
    main_view = "5m_offset_0"

    for view in VIEWS[1:]:
        graph = build_edge_graph(
            filtered[main_view], filtered[view],
            time_field="five_filtered_occurrence_times",
            nominal_bar_minutes=5.0,
            require_phase=True,
        )
        fp = list(graph.mutual_unique_matches)
        assert len(fp) == v0623.EXPECTED_FILTERED[view]
        strict = []
        for i, j in fp:
            left = maps[main_view].get(v0623.fkey(filtered[main_view][i]))
            right = maps[view].get(v0623.fkey(filtered[view][j]))
            if left is not None and right is not None and strict_anchor_edge(left, right, 5.0) is not None:
                strict.append((left, right))
        assert len(strict) == v0623.EXPECTED_RAW[view]
        assert v0623.qmatrix(strict) == v0623.EXPECTED_V0618[view]
        both = [(a, b) for a, b in strict if a["candidate_qualified"] and b["candidate_qualified"]]
        total_bothq += len(both)
        offset_counter = Counter()
        for left, right in both:
            ls = states[main_view][v0623.fkey(left)]
            rs = states[view][v0623.fkey(right)]
            pooled_d1.append((ls["D1"], rs["D1"]))
            pooled_candidate.append((ls["v0623"], rs["v0623"]))
            category = pair_transition_category(ls["D1"], rs["D1"], ls["v0623"], rs["v0623"])
            rtop = rescue_topology(ls["rescued"], rs["rescued"])
            dtop = d1_pair_topology(ls["D1"], rs["D1"])
            transition_counts[category] += 1
            offset_counter[category] += 1
            topology[category][rtop] += 1
            d1_topology_counts[category][dtop] += 1
            for side_name, state in (("main", ls), ("other", rs)):
                if not state["rescued"]:
                    continue
                rescued_labels[category][state["rescue_label"]] += 1
                if category in TARGET_GROUPS:
                    subtype_counts[category][state["uncertain_subtype"]] += 1
                    margins[category].append(float(state["consensus_margin_to_frozen_boundary"]))
                    spans[category].append(float(state["support_score_span"]))
            if category != "retained_exact":
                details.append({
                    "offset": view,
                    "category": category,
                    "rescue_topology": rtop,
                    "D1_topology": dtop,
                    "main": ls,
                    "other": rs,
                })
        per_offset_transition[view] = dict(offset_counter)

    assert total_bothq == v0623.EXPECTED_BOTHQ
    d1_metrics = v0623.metrics(pooled_d1)
    candidate_metrics = v0623.metrics(pooled_candidate)
    assert d1_metrics["exact_agreement_count"] == 1400
    assert abs(d1_metrics["exact_agreement"] - v0623.EXPECTED_D1_EXACT) <= 1e-12
    assert candidate_metrics["exact_agreement_count"] == EXPECTED_V0623_EXACT_COUNT
    assert abs(candidate_metrics["exact_agreement"] - EXPECTED_V0623_EXACT) <= 1e-12
    assert abs(candidate_metrics["pooled_decisive_coverage"] - EXPECTED_V0623_COVERAGE) <= 1e-12
    assert candidate_metrics["decisive_agreement"] == 1.0
    assert candidate_metrics["opposite_trend_conflict_count"] == 0
    assert sum(transition_counts.values()) == total_bothq

    by_transition = {}
    for category in ("retained_exact", "introduced_harm", "repaired_old_nonexact", "persistent_nonexact"):
        by_transition[category] = {
            "rescue_topology_counts": dict(topology[category]),
            "D1_topology_counts": dict(d1_topology_counts[category]),
            "rescued_label_counts": dict(rescued_labels[category]),
            "rescued_side_uncertain_subtype_counts": dict(subtype_counts[category]),
            "consensus_margin_quantiles": quantiles(margins[category]),
            "support_score_span_quantiles": quantiles(spans[category]),
        }

    result = {
        "schema": "two_wave_v0623_residual_direction_attribution@0.6.24",
        "controls": {
            "filtered_pairs": 57029,
            "raw_strict_pairs": 29453,
            "both_v0618_qualified_pairs": total_bothq,
            "D1_exact_agreement": d1_metrics["exact_agreement"],
            "D1_exact_count": d1_metrics["exact_agreement_count"],
            "D1_decisive_coverage": d1_metrics["pooled_decisive_coverage"],
            "v0623_exact_agreement": candidate_metrics["exact_agreement"],
            "v0623_exact_count": candidate_metrics["exact_agreement_count"],
            "v0623_decisive_coverage": candidate_metrics["pooled_decisive_coverage"],
            "v0623_decisive_agreement": candidate_metrics["decisive_agreement"],
            "v0623_opposite_trend_conflicts": candidate_metrics["opposite_trend_conflict_count"],
            "reproduced": True,
        },
        "transition_counts": dict(transition_counts),
        "per_offset_transition_counts": per_offset_transition,
        "by_transition": by_transition,
        "changed_recognizer_rules": [],
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
