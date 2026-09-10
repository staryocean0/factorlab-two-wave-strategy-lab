#!/usr/bin/env python3
"""Evaluate the single frozen v0.6.20 duration-boundary challenger.

Uses only the sealed v0.6.18 row artifacts. Cross-view data define the frozen
evaluation universe; the candidate decision itself uses only each identity's
own raw bars and v0.6.18 hard reasons.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.one_bar_duration_repair_v0620 import (
    LONG_SPAN_SAFETY_REASONS,
    v0620_hard_reasons,
)
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import build_edge_graph

VIEWS = tuple(f"5m_offset_{i}" for i in range(5))
EXPECTED_FILTERED = {
    "5m_offset_1": 14784,
    "5m_offset_2": 12725,
    "5m_offset_3": 13412,
    "5m_offset_4": 16108,
}
EXPECTED_STRICT = {
    "5m_offset_1": 8381,
    "5m_offset_2": 5770,
    "5m_offset_3": 6204,
    "5m_offset_4": 9098,
}
BASELINE = {
    "5m_offset_1": {
        "matrix": {"both_qualified": 400, "both_rejected": 7809, "main_only_qualified": 101, "other_only_qualified": 71},
        "positive_overlap": 0.6993006993006993,
    },
    "5m_offset_2": {
        "matrix": {"both_qualified": 287, "both_rejected": 5323, "main_only_qualified": 93, "other_only_qualified": 67},
        "positive_overlap": 0.6420581655480985,
    },
    "5m_offset_3": {
        "matrix": {"both_qualified": 302, "both_rejected": 5736, "main_only_qualified": 90, "other_only_qualified": 76},
        "positive_overlap": 0.6452991452991453,
    },
    "5m_offset_4": {
        "matrix": {"both_qualified": 473, "both_rejected": 8447, "main_only_qualified": 102, "other_only_qualified": 76},
        "positive_overlap": 0.7265745007680492,
    },
}
BASELINE_AGG = {"both_qualified": 1462, "both_rejected": 27315, "main_only_qualified": 386, "other_only_qualified": 290}
BASELINE_POSITIVE_OVERLAP = 0.6838166510757717
MIN_CANDIDATE_POSITIVE_OVERLAP = 0.7138166511
MIN_CANDIDATE_BOTH_QUALIFIED = 1609
EXPECTED_FILTERED_TOTAL = 57029
EXPECTED_STRICT_TOTAL = 29453


def load_jsonl_gz(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def locate_one(root: Path, pattern: str) -> Path:
    hits = list(root.rglob(pattern))
    if len(hits) != 1:
        raise RuntimeError(f"expected exactly one {pattern}, found {len(hits)}")
    return hits[0]


def publication_map(rows: list[dict]) -> dict[tuple[str, tuple[int, ...]], dict]:
    out = {}
    for row in rows:
        key = (str(row["phase"]), tuple(int(x) for x in row["five_filtered_occurrence_bars"]))
        if key in out:
            raise AssertionError(f"duplicate published filtered identity: {key}")
        out[key] = row
    return out


def add_matrix(total: dict, row: dict) -> None:
    for key in total:
        total[key] += int(row[key])


def positive_overlap(m: dict) -> float:
    den = int(m["both_qualified"] + m["main_only_qualified"] + m["other_only_qualified"])
    return float(m["both_qualified"] / den) if den else 0.0


def classify_pair(qa: bool, qb: bool) -> str:
    if qa and qb:
        return "both_qualified"
    if not qa and not qb:
        return "both_rejected"
    if qa:
        return "main_only_qualified"
    return "other_only_qualified"


def candidate_decision(row: dict) -> tuple[bool, list[str], dict]:
    old = [str(x) for x in row["candidate_hard_reasons"]]
    raw = [int(x) for x in row["published_raw_occurrence_bars"]]
    new, diag = v0620_hard_reasons(old, raw)

    if any(reason in old for reason in LONG_SPAN_SAFETY_REASONS):
        if not any(reason in new for reason in LONG_SPAN_SAFETY_REASONS):
            raise AssertionError("long-span safety reason was demoted")
        if not new:
            raise AssertionError("long-span safety identity became qualified")
    if "short_leg" in old and int(diag["min_leg"]) <= 2 and "short_leg" not in new:
        raise AssertionError("severe short_leg was demoted")
    if "short_cycle" in old and int(diag["min_cycle"]) <= 10 and "short_cycle" not in new:
        raise AssertionError("severe short_cycle was demoted")
    if "cycle_duration_mismatch" in old and "cycle_duration_mismatch" not in new:
        raise AssertionError("cycle_duration_mismatch was demoted")
    if any(reason not in old for reason in new):
        raise AssertionError("candidate added a hard reason")
    if bool(row["candidate_qualified"]) and new:
        raise AssertionError("v0.6.18 qualified identity regressed")

    return not new, new, diag


def write_card(path: Path, result: dict) -> None:
    agg = result["aggregate"]
    lines = [
        "# Two-Wave v0.6.20 result card",
        "",
        f"Formal verdict: **`{result['verdict']}`**",
        "",
        "The sole challenger demotes `short_leg` only at `min_leg == 3` and `short_cycle` only at `min_cycle == 11`. More severe duration failures, cycle-duration mismatch, amplitude, confirmation and long-span safety gates remain hard. No cross-view data enter the candidate decision.",
        "",
        "## Frozen control reproduction",
        "",
        f"- filtered mutual-unique pairs: **{result['controls']['filtered_pairs']:,} / 57,029**",
        f"- published raw strict pairs: **{result['controls']['strict_pairs']:,} / 29,453**",
        f"- v0.6.18 aggregate matrix: `{result['controls']['baseline_matrix']}`",
        "",
        "## Candidate stability",
        "",
        "| offset | v0.6.18 +overlap | v0.6.20 +overlap | delta pp | both-Q v0618 | both-Q v0620 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for view in VIEWS[1:]:
        row = result["offsets"][view]
        lines.append(
            f"| {view} | {row['baseline_positive_overlap']:.4%} | {row['candidate_positive_overlap']:.4%} | {row['positive_overlap_delta_pp']:+.4f} | {row['baseline_matrix']['both_qualified']} | {row['candidate_matrix']['both_qualified']} |"
        )
    lines += [
        "",
        f"Aggregate positive overlap: **{BASELINE_POSITIVE_OVERLAP:.4%} -> {agg['candidate_positive_overlap']:.4%}** ({agg['positive_overlap_delta_pp']:+.4f} pp).",
        f"Aggregate both-qualified: **1,462 -> {agg['candidate_matrix']['both_qualified']:,}**.",
        f"Unique published identities newly qualified by the exact boundary rule: **{result['identity_level']['newly_qualified_unique_across_views']:,}** (view-summed {result['identity_level']['newly_qualified_view_sum']:,}).",
        "",
        "## Frozen promotion gate",
        "",
        f"- exact control reproduction: **{result['gates']['control_reproduction']}**",
        f"- all four offsets non-worse: **{result['gates']['all_offsets_nonworse']}**",
        f"- aggregate positive overlap >= 71.38166511%: **{result['gates']['aggregate_positive_overlap_material']}**",
        f"- aggregate both-qualified >= 1,609: **{result['gates']['aggregate_both_qualified_material']}**",
        f"- hard safety invariants: **{result['gates']['hard_safety_invariants']}**",
        "",
        "This is a qualification-policy component adjudication only. Full morphology acceptance remains false; direction/state classification, outcomes, trading and production remain frozen.",
    ]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    filtered = {}
    records = {}
    pubmaps = {}
    candidate_cache: dict[tuple[str, str, tuple[int, ...]], tuple[bool, list[str], dict]] = {}
    newly_qualified_keys = set()
    newly_qualified_view_sum = 0

    for view in VIEWS:
        filtered[view] = load_jsonl_gz(locate_one(args.input, f"filtered-{view}.json.gz"))
        records[view] = load_jsonl_gz(locate_one(args.input, f"records-{view}.json.gz"))
        pubmaps[view] = publication_map(records[view])
        for row in records[view]:
            raw_key = tuple(int(x) for x in row["published_raw_occurrence_bars"])
            key = (view, str(row["phase"]), raw_key)
            decision = candidate_decision(row)
            candidate_cache[key] = decision
            if decision[0] and not bool(row["candidate_qualified"]):
                newly_qualified_view_sum += 1
                # Timestamps + phase define a cross-view-neutral audit identity only for dedup description.
                newly_qualified_keys.add((str(row["phase"]), tuple(str(x) for x in row["five_occurrence_times"])))

    offsets = {}
    base_total = {k: 0 for k in BASELINE_AGG}
    cand_total = {k: 0 for k in BASELINE_AGG}
    filtered_total = 0
    strict_total = 0
    all_nonworse = True
    main_view = "5m_offset_0"

    for view in VIEWS[1:]:
        graph = build_edge_graph(
            filtered[main_view], filtered[view],
            time_field="five_filtered_occurrence_times",
            nominal_bar_minutes=5.0,
            require_phase=True,
        )
        fm = list(graph.mutual_unique_matches)
        if len(fm) != EXPECTED_FILTERED[view]:
            raise AssertionError(f"filtered control drift {view}: {len(fm)}")

        strict = []
        for i, j in fm:
            fa, fb = filtered[main_view][i], filtered[view][j]
            ka = (str(fa["phase"]), tuple(int(x) for x in fa["five_filtered_occurrence_bars"]))
            kb = (str(fb["phase"]), tuple(int(x) for x in fb["five_filtered_occurrence_bars"]))
            a, b = pubmaps[main_view].get(ka), pubmaps[view].get(kb)
            if a is not None and b is not None and strict_anchor_edge(a, b, 5.0) is not None:
                strict.append((a, b))
        if len(strict) != EXPECTED_STRICT[view]:
            raise AssertionError(f"strict control drift {view}: {len(strict)}")

        base = {k: 0 for k in BASELINE_AGG}
        cand = {k: 0 for k in BASELINE_AGG}
        for a, b in strict:
            base[classify_pair(bool(a["candidate_qualified"]), bool(b["candidate_qualified"]))] += 1
            ka = (main_view, str(a["phase"]), tuple(int(x) for x in a["published_raw_occurrence_bars"]))
            kb = (view, str(b["phase"]), tuple(int(x) for x in b["published_raw_occurrence_bars"]))
            cand[classify_pair(candidate_cache[ka][0], candidate_cache[kb][0])] += 1
        if base != BASELINE[view]["matrix"]:
            raise AssertionError(f"v0.6.18 matrix drift {view}: {base}")

        p0 = positive_overlap(base)
        p1 = positive_overlap(cand)
        if abs(p0 - BASELINE[view]["positive_overlap"]) > 1e-12:
            raise AssertionError(f"v0.6.18 positive overlap drift {view}")
        all_nonworse = all_nonworse and p1 >= p0
        offsets[view] = {
            "filtered_pairs": len(fm),
            "strict_pairs": len(strict),
            "baseline_matrix": base,
            "candidate_matrix": cand,
            "baseline_positive_overlap": p0,
            "candidate_positive_overlap": p1,
            "positive_overlap_delta_pp": 100.0 * (p1 - p0),
        }
        filtered_total += len(fm)
        strict_total += len(strict)
        add_matrix(base_total, base)
        add_matrix(cand_total, cand)

    if filtered_total != EXPECTED_FILTERED_TOTAL or strict_total != EXPECTED_STRICT_TOTAL:
        raise AssertionError("aggregate identity universe drift")
    if base_total != BASELINE_AGG:
        raise AssertionError(f"aggregate v0.6.18 matrix drift: {base_total}")

    cand_pos = positive_overlap(cand_total)
    gates = {
        "control_reproduction": True,
        "all_offsets_nonworse": bool(all_nonworse),
        "aggregate_positive_overlap_material": cand_pos >= MIN_CANDIDATE_POSITIVE_OVERLAP,
        "aggregate_both_qualified_material": cand_total["both_qualified"] >= MIN_CANDIDATE_BOTH_QUALIFIED,
        "hard_safety_invariants": True,
    }
    passed = all(gates.values())
    verdict = (
        "v0620_exact_one_bar_duration_repair_pass"
        if passed else "v0620_exact_one_bar_duration_repair_rejected"
    )
    result = {
        "schema": "two_wave_one_bar_duration_repair_result@0.6.20",
        "verdict": verdict,
        "input_workflow_run": 34423674192,
        "candidate_count": 1,
        "changed_component_only": [
            "short_leg hard->diagnostic only when min_leg==3",
            "short_cycle hard->diagnostic only when min_cycle==11",
        ],
        "controls": {
            "filtered_pairs": filtered_total,
            "strict_pairs": strict_total,
            "baseline_matrix": base_total,
        },
        "offsets": offsets,
        "aggregate": {
            "baseline_positive_overlap": BASELINE_POSITIVE_OVERLAP,
            "candidate_positive_overlap": cand_pos,
            "positive_overlap_delta_pp": 100.0 * (cand_pos - BASELINE_POSITIVE_OVERLAP),
            "baseline_matrix": base_total,
            "candidate_matrix": cand_total,
        },
        "identity_level": {
            "newly_qualified_view_sum": newly_qualified_view_sum,
            "newly_qualified_unique_across_views": len(newly_qualified_keys),
        },
        "gates": gates,
        "eligible_for_qualification_component_update": bool(passed),
        "morphology_acceptance": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "production_authority": False,
    }
    (args.output / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_card(args.output / "RESULT_CARD.md", result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
