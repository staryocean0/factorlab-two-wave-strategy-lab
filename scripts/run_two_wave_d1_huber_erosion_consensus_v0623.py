#!/usr/bin/env python3
"""Formal v0.6.23 D1-primary endpoint-erosion-consensus Huber replay."""
from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.d1_huber_erosion_consensus_v0623 import (
    d1_primary_erosion_consensus_rescue,
)
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.models import stable_id
from factor_lab.visual_structure.two_wave.same_scale_v04 import evaluate_pair
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import build_edge_graph
from factor_lab.visual_structure.two_wave.whole_window_huber_direction_v0621 import classify_parent_window

VIEWS = tuple(f"5m_offset_{i}" for i in range(5))
EXPECTED_FILTERED = {"5m_offset_1":14784,"5m_offset_2":12725,"5m_offset_3":13412,"5m_offset_4":16108}
EXPECTED_RAW = {"5m_offset_1":8381,"5m_offset_2":5770,"5m_offset_3":6204,"5m_offset_4":9098}
EXPECTED_V0618 = {
    "5m_offset_1":{"both_qualified":400,"both_rejected":7809,"main_only_qualified":101,"other_only_qualified":71},
    "5m_offset_2":{"both_qualified":287,"both_rejected":5323,"main_only_qualified":93,"other_only_qualified":67},
    "5m_offset_3":{"both_qualified":302,"both_rejected":5736,"main_only_qualified":90,"other_only_qualified":76},
    "5m_offset_4":{"both_qualified":473,"both_rejected":8447,"main_only_qualified":102,"other_only_qualified":76},
}
EXPECTED_BOTHQ = 1462
EXPECTED_D1_EXACT = 0.957592339261286
EXPECTED_D1_COVERAGE = 0.4890560875512996
LABELS = ("range", "uptrend", "downtrend", "uncertain")


def load_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


def find_one(root: Path, name: str) -> Path:
    hits = list(root.rglob(name))
    if len(hits) != 1:
        raise RuntimeError(f"expected one {name}, got {len(hits)}")
    return hits[0]


def fkey(row):
    return str(row["phase"]), tuple(int(x) for x in row["five_filtered_occurrence_bars"])


def qmatrix(pairs):
    out = {"both_qualified":0,"both_rejected":0,"main_only_qualified":0,"other_only_qualified":0}
    for a, b in pairs:
        qa, qb = bool(a["candidate_qualified"]), bool(b["candidate_qualified"])
        if qa and qb:
            out["both_qualified"] += 1
        elif not qa and not qb:
            out["both_rejected"] += 1
        elif qa:
            out["main_only_qualified"] += 1
        else:
            out["other_only_qualified"] += 1
    return out


def reconstruct_pair(row, bars, view):
    cfg = MaturityConfig(timeframe=view)
    raw = [int(x) for x in row["published_raw_occurrence_bars"]]
    confirmation = int(row["publishing_confirmation_bar"])
    phase = str(row["phase"])
    other = "high" if phase == "low" else "low"
    kinds = [phase, other, phase, other, phase]
    ct = str(bars[confirmation]["timestamp"])
    points = []
    for ordinal, (kind, occurrence) in enumerate(zip(kinds, raw)):
        price = float(bars[occurrence]["close"])
        points.append({
            "kind": kind,
            "occurrence_bar": occurrence,
            "occurrence_time": str(bars[occurrence]["timestamp"]),
            "price": price,
            "log_price": math.log(price),
            "left_censored": False,
            "confirmation_bar": confirmation,
            "confirmation_time": ct,
            "bar_end_assumed": False,
            "pivot_id": stable_id(
                "v0623_audit_pivot",
                [view, phase, raw, confirmation, ordinal, occurrence, price],
            ),
        })
    return evaluate_pair(points, bars, cfg, source="v0623_direction_audit")


def state(row, bars, closes, view):
    pair = reconstruct_pair(row, bars, view)
    d1 = str(pair["direction_versions"]["D1"])
    amp = float(pair["amplitude_unit_price"])
    raw = row["published_raw_occurrence_bars"]
    full = classify_parent_window(closes, raw, amp)
    candidate = d1_primary_erosion_consensus_rescue(d1, closes, raw, amp)
    if d1 == "uncertain":
        assert candidate["support_states"]["full"] == full["classification"]
        assert abs(candidate["support_scores"]["full"] - float(full["normalized_parent_drift"])) <= 1e-12
    else:
        assert candidate["classification"] == d1
    return {
        "D1": d1,
        "full_Huber": str(full["classification"]),
        "v0623": str(candidate["classification"]),
        "source": str(candidate["decision_source"]),
        "overridden": bool(candidate["D1_decisive_overridden"]),
        "rescue_applied": bool(candidate["rescue_applied"]),
        "erosion_consensus_state": candidate.get("erosion_consensus_state"),
    }


def metrics(pairs):
    n = len(pairs)
    exact = sum(a == b for a, b in pairs)
    decisive = [(a, b) for a, b in pairs if a != "uncertain" and b != "uncertain"]
    labels = [x for pair in pairs for x in pair]
    counts = Counter(labels)
    decisive_counts = Counter(x for x in labels if x != "uncertain")
    decisive_total = sum(decisive_counts.values())
    return {
        "pairs": n,
        "exact_agreement": exact / n if n else 0.0,
        "exact_agreement_count": exact,
        "decisive_agreement": (sum(a == b for a, b in decisive) / len(decisive)) if decisive else 0.0,
        "decisive_pair_count": len(decisive),
        "opposite_trend_conflict_count": sum({a, b} == {"uptrend", "downtrend"} for a, b in pairs),
        "main_decisive_coverage": sum(a != "uncertain" for a, _ in pairs) / n if n else 0.0,
        "other_decisive_coverage": sum(b != "uncertain" for _, b in pairs) / n if n else 0.0,
        "pooled_decisive_coverage": decisive_total / (2 * n) if n else 0.0,
        "pooled_label_counts": {k: counts.get(k, 0) for k in LABELS},
        "pooled_decisive_label_shares": {
            k: (decisive_counts.get(k, 0) / decisive_total if decisive_total else 0.0)
            for k in LABELS if k != "uncertain"
        },
    }


def write_card(path: Path, result: dict):
    baseline = result["pooled"]["D1"]
    candidate = result["pooled"]["v0623"]
    lines = [
        "# Two-Wave v0.6.23 D1-primary endpoint-erosion-consensus Huber rescue result",
        "",
        f"Formal verdict: **`{result['verdict']}`**",
        "",
        f"D1 decisive overrides: **{result['rescue_audit']['D1_decisive_override_count']}**.",
        f"D1-Uncertain records rescued by unanimous endpoint-erosion consensus: **{result['rescue_audit']['rescued_record_count']}**.",
        f"D1-Uncertain records withheld because support states were not unanimous decisive: **{result['rescue_audit']['withheld_uncertain_record_count']}**.",
        "",
        "| metric | D1 | v0.6.23 |",
        "|---|---:|---:|",
        f"| pooled exact agreement | {baseline['exact_agreement']:.2%} | {candidate['exact_agreement']:.2%} |",
        f"| pooled decisive coverage | {baseline['pooled_decisive_coverage']:.2%} | {candidate['pooled_decisive_coverage']:.2%} |",
        f"| decisive agreement | {baseline['decisive_agreement']:.2%} | {candidate['decisive_agreement']:.2%} |",
        f"| opposite trend conflicts | {baseline['opposite_trend_conflict_count']} | {candidate['opposite_trend_conflict_count']} |",
        "",
        "Per-offset exact agreement:",
        "",
        "| offset | D1 | v0.6.23 | delta pp |",
        "|---|---:|---:|---:|",
    ]
    for view, row in result["per_offset"].items():
        d = row["D1"]["exact_agreement"]
        c = row["v0623"]["exact_agreement"]
        lines.append(f"| {view} | {d:.2%} | {c:.2%} | {(c-d)*100:.2f} |")
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

    filtered = {}
    records = {}
    maps = {}
    bars = {}
    closes = {}
    states = {}
    override_count = 0
    rescued = Counter()
    withheld_uncertain = 0

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
            if s["rescue_applied"]:
                rescued[s["v0623"]] += 1
            elif s["D1"] == "uncertain":
                withheld_uncertain += 1
    assert override_count == 0

    main_view = "5m_offset_0"
    total_bothq = 0
    pooled_d1 = []
    pooled_candidate = []
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
        d1_pairs = []
        candidate_pairs = []
        for left, right in both:
            ls = states[main_view][fkey(left)]
            rs = states[view][fkey(right)]
            d1_pairs.append((ls["D1"], rs["D1"]))
            candidate_pairs.append((ls["v0623"], rs["v0623"]))
        pooled_d1 += d1_pairs
        pooled_candidate += candidate_pairs
        per_offset[view] = {"D1": metrics(d1_pairs), "v0623": metrics(candidate_pairs)}

    assert total_bothq == EXPECTED_BOTHQ
    d1 = metrics(pooled_d1)
    candidate = metrics(pooled_candidate)
    assert abs(d1["exact_agreement"] - EXPECTED_D1_EXACT) <= 1e-12
    assert abs(d1["pooled_decisive_coverage"] - EXPECTED_D1_COVERAGE) <= 1e-12
    assert d1["decisive_agreement"] == 1.0
    assert d1["opposite_trend_conflict_count"] == 0

    shares = candidate["pooled_decisive_label_shares"]
    gates = {
        "upstream_controls": True,
        "D1_controls_reproduced": True,
        "D1_decisive_override_zero": override_count == 0,
        "all_offsets_exact_agreement_nonworse": all(
            row["v0623"]["exact_agreement"] >= row["D1"]["exact_agreement"]
            for row in per_offset.values()
        ),
        "pooled_exact_agreement_nonworse": candidate["exact_agreement"] >= d1["exact_agreement"],
        "pooled_decisive_coverage_material": (
            candidate["pooled_decisive_coverage"] >= 0.65
            and candidate["pooled_decisive_coverage"] >= d1["pooled_decisive_coverage"] + 0.15
        ),
        "each_offset_side_decisive_coverage_at_least_55pct": all(
            min(row["v0623"]["main_decisive_coverage"], row["v0623"]["other_decisive_coverage"]) >= 0.55
            for row in per_offset.values()
        ),
        "pooled_decisive_agreement_at_least_99_5pct": candidate["decisive_agreement"] >= 0.995,
        "opposite_trend_conflict_zero": candidate["opposite_trend_conflict_count"] == 0,
        "decisive_class_diversity": (
            shares.get("uptrend", 0) >= 0.15
            and shares.get("downtrend", 0) >= 0.15
            and shares.get("range", 0) >= 0.02
        ),
        "nonzero_consensus_rescue": sum(rescued.values()) > 0,
    }
    passed = all(gates.values())
    result = {
        "schema": "two_wave_d1_huber_erosion_consensus_result@0.6.23",
        "verdict": (
            "v0623_D1_primary_erosion_consensus_Huber_rescue_direction_research_component_pass"
            if passed else
            "v0623_D1_primary_erosion_consensus_Huber_rescue_direction_rejected"
        ),
        "controls": {
            "filtered_pairs": 57029,
            "raw_strict_pairs": 29453,
            "both_v0618_qualified_pairs": total_bothq,
            "reproduced": True,
        },
        "rescue_audit": {
            "D1_decisive_override_count": override_count,
            "rescued_record_count": sum(rescued.values()),
            "rescued_label_counts": dict(rescued),
            "withheld_uncertain_record_count": withheld_uncertain,
        },
        "pooled": {"D1": d1, "v0623": candidate},
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
