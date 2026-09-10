#!/usr/bin/env python3
"""Aggregate frozen v0.6.18 native-5m shards and apply preregistered gates."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import (
    build_edge_graph,
)

VIEWS = tuple(f"5m_offset_{i}" for i in range(5))
EXPECTED_FILTERED_MATCHES = {
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
EXPECTED_CONTROL = {
    "5m_offset_1": {"both_qualified": 135, "both_rejected": 8067, "main_only_qualified": 89, "other_only_qualified": 90},
    "5m_offset_2": {"both_qualified": 93, "both_rejected": 5519, "main_only_qualified": 90, "other_only_qualified": 68},
    "5m_offset_3": {"both_qualified": 93, "both_rejected": 5924, "main_only_qualified": 89, "other_only_qualified": 98},
    "5m_offset_4": {"both_qualified": 161, "both_rejected": 8762, "main_only_qualified": 84, "other_only_qualified": 91},
}
CONTROL_AGGREGATE = {"both_qualified": 482, "both_rejected": 28272, "main_only_qualified": 352, "other_only_qualified": 347}
MIN_AGGREGATE_POSITIVE_OVERLAP = 0.458129
MIN_AGGREGATE_BOTH_QUALIFIED = 531


def load_jsonl_gz(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def filtered_key(row: dict) -> tuple[str, tuple[int, ...]]:
    return str(row["phase"]), tuple(int(x) for x in row["five_filtered_occurrence_bars"])


def published_index(rows: list[dict]) -> dict[tuple[str, tuple[int, ...]], int]:
    out: dict[tuple[str, tuple[int, ...]], int] = {}
    for i, row in enumerate(rows):
        key = filtered_key(row)
        if key in out:
            raise AssertionError("published filtered identity must be single-valued")
        out[key] = i
    return out


def frozen_raw_strict_pairs(
    filtered_a: list[dict],
    filtered_b: list[dict],
    published_a: list[dict],
    published_b: list[dict],
) -> tuple[int, list[tuple[int, int]]]:
    """Reproduce the v0.6.5 two-layer pair semantics exactly.

    First establish the mutual-unique same-event relation in the canonical
    filtered tuple-birth universe. Only within those frozen parent-event pairs
    ask whether both immutable raw publications exist and their five raw
    anchors remain strict under the same one-nominal-bar locality rule.
    """
    graph = build_edge_graph(
        filtered_a,
        filtered_b,
        time_field="five_filtered_occurrence_times",
        nominal_bar_minutes=5.0,
        require_phase=True,
    )
    pub_a = published_index(published_a)
    pub_b = published_index(published_b)
    strict: list[tuple[int, int]] = []
    for ia, ib in graph.mutual_unique_matches:
        ka = filtered_key(filtered_a[ia])
        kb = filtered_key(filtered_b[ib])
        pa = pub_a.get(ka)
        pb = pub_b.get(kb)
        if pa is None or pb is None:
            continue
        if strict_anchor_edge(published_a[pa], published_b[pb], 5.0) is not None:
            strict.append((pa, pb))
    return len(graph.mutual_unique_matches), strict


def matrix(a: list[dict], b: list[dict], matches: list[tuple[int, int]], field: str) -> dict:
    out = {"both_qualified": 0, "both_rejected": 0, "main_only_qualified": 0, "other_only_qualified": 0}
    for i, j in matches:
        qa = bool(a[i][field])
        qb = bool(b[j][field])
        if qa and qb:
            out["both_qualified"] += 1
        elif not qa and not qb:
            out["both_rejected"] += 1
        elif qa:
            out["main_only_qualified"] += 1
        else:
            out["other_only_qualified"] += 1
    return out


def positive_overlap(m: dict) -> float:
    den = int(m["both_qualified"] + m["main_only_qualified"] + m["other_only_qualified"])
    return float(m["both_qualified"] / den) if den else 0.0


def add_matrix(total: dict, row: dict) -> None:
    for key in total:
        total[key] += int(row[key])


def write_result_card(path: Path, result: dict) -> None:
    lines = [
        "# Two-Wave v0.6.18 result card",
        "",
        f"Formal verdict: **`{result['verdict']}`**",
        "",
        "Only `inefficient_leg` and `jump_dominated_leg` were demoted from hard vetoes to diagnostics. Parent identity, v0.6.5 publication, all non-path v0.5.4 hard reasons, D1, matcher, outcomes and trading remained frozen.",
        "",
        "## Frozen control reproduction",
        "",
        f"Filtered mutual-unique pairs: **{result['aggregate']['filtered_pairs']:,}** (expected 57,029).",
        f"Published raw strict same-event pairs: **{result['aggregate']['strict_pairs']:,}** (expected 29,453).",
        f"Control matrix: `{result['aggregate']['control_matrix']}`.",
        "",
        "## Candidate qualification stability",
        "",
        "| offset | filtered pairs | raw strict | control +overlap | candidate +overlap | both-Q control | both-Q candidate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for view in VIEWS[1:]:
        row = result["offsets"][view]
        lines.append(
            f"| {view} | {row['filtered_pairs']:,} | {row['strict_pairs']:,} | {row['control_positive_overlap']:.4%} | {row['candidate_positive_overlap']:.4%} | {row['control_matrix']['both_qualified']} | {row['candidate_matrix']['both_qualified']} |"
        )
    agg = result["aggregate"]
    lines += [
        "",
        f"Aggregate positive overlap: **{agg['control_positive_overlap']:.4%} -> {agg['candidate_positive_overlap']:.4%}**.",
        f"Aggregate both-qualified: **{agg['control_matrix']['both_qualified']} -> {agg['candidate_matrix']['both_qualified']}**.",
        "",
        "## Gate",
        "",
        f"- all four offsets non-worse: **{result['gates']['all_offsets_positive_overlap_nonworse']}**",
        f"- aggregate positive overlap >= 45.8129%: **{result['gates']['aggregate_positive_overlap']}**",
        f"- aggregate both-qualified >= 531: **{result['gates']['aggregate_both_qualified']}**",
        f"- upstream/control reproduction: **{result['gates']['control_reproduction']}**",
        "",
        "This result is a research qualification-policy adjudication only. It is not independent morphology acceptance and carries no trade or production authority.",
    ]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    records: dict[str, list[dict]] = {}
    filtered: dict[str, list[dict]] = {}
    view_summaries = {}
    for view in VIEWS:
        record_files = list(args.input.rglob(f"records-{view}.json.gz"))
        filtered_files = list(args.input.rglob(f"filtered-{view}.json.gz"))
        summaries = list(args.input.rglob(f"summary-{view}.json"))
        if len(record_files) != 1 or len(filtered_files) != 1 or len(summaries) != 1:
            raise RuntimeError(f"expected exactly one complete shard for {view}")
        records[view] = load_jsonl_gz(record_files[0])
        filtered[view] = load_jsonl_gz(filtered_files[0])
        view_summaries[view] = json.loads(summaries[0].read_text())

    main_rows = records["5m_offset_0"]
    main_filtered = filtered["5m_offset_0"]
    offsets = {}
    control_total = {key: 0 for key in CONTROL_AGGREGATE}
    candidate_total = {key: 0 for key in CONTROL_AGGREGATE}
    strict_total = 0
    filtered_total = 0
    all_nonworse = True

    for view in VIEWS[1:]:
        filtered_matches, matches = frozen_raw_strict_pairs(
            main_filtered,
            filtered[view],
            main_rows,
            records[view],
        )
        if filtered_matches != EXPECTED_FILTERED_MATCHES[view]:
            raise AssertionError(
                f"filtered pair control drift {view}: {filtered_matches} != {EXPECTED_FILTERED_MATCHES[view]}"
            )
        if len(matches) != EXPECTED_STRICT[view]:
            raise AssertionError(f"strict pair control drift {view}: {len(matches)} != {EXPECTED_STRICT[view]}")
        control = matrix(main_rows, records[view], matches, "control_qualified")
        if control != EXPECTED_CONTROL[view]:
            raise AssertionError(f"v0.6.6 control matrix drift {view}: {control} != {EXPECTED_CONTROL[view]}")
        candidate = matrix(main_rows, records[view], matches, "candidate_qualified")
        c0 = positive_overlap(control)
        c1 = positive_overlap(candidate)
        all_nonworse = all_nonworse and c1 >= c0
        offsets[view] = {
            "filtered_pairs": filtered_matches,
            "strict_pairs": len(matches),
            "control_matrix": control,
            "candidate_matrix": candidate,
            "control_positive_overlap": c0,
            "candidate_positive_overlap": c1,
            "positive_overlap_delta_pp": 100.0 * (c1 - c0),
        }
        filtered_total += filtered_matches
        strict_total += len(matches)
        add_matrix(control_total, control)
        add_matrix(candidate_total, candidate)

    if filtered_total != 57029:
        raise AssertionError(f"aggregate filtered-pair control drift: {filtered_total} != 57029")
    if strict_total != 29453 or control_total != CONTROL_AGGREGATE:
        raise AssertionError("aggregate frozen control drift")

    control_pos = positive_overlap(control_total)
    candidate_pos = positive_overlap(candidate_total)
    gates = {
        "control_reproduction": True,
        "all_offsets_positive_overlap_nonworse": bool(all_nonworse),
        "aggregate_positive_overlap": candidate_pos >= MIN_AGGREGATE_POSITIVE_OVERLAP,
        "aggregate_both_qualified": candidate_total["both_qualified"] >= MIN_AGGREGATE_BOTH_QUALIFIED,
    }
    passed = all(gates.values())
    verdict = (
        "v0618_path_gate_demotion_research_candidate_pass"
        if passed
        else "v0618_path_gate_demotion_rejected"
    )

    result = {
        "schema": "two_wave_path_gate_demotion_result@0.6.18",
        "verdict": verdict,
        "data_role": "development_material",
        "fresh_oos": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "morphology_acceptance": False,
        "changed_component_only": ["inefficient_leg hard->diagnostic", "jump_dominated_leg hard->diagnostic"],
        "view_summaries": view_summaries,
        "offsets": offsets,
        "aggregate": {
            "filtered_pairs": filtered_total,
            "strict_pairs": strict_total,
            "control_matrix": control_total,
            "candidate_matrix": candidate_total,
            "control_positive_overlap": control_pos,
            "candidate_positive_overlap": candidate_pos,
            "positive_overlap_delta_pp": 100.0 * (candidate_pos - control_pos),
        },
        "gates": gates,
    }
    (args.output / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_result_card(args.output / "RESULT_CARD.md", result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
