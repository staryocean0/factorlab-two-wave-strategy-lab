#!/usr/bin/env python3
"""Run frozen v0.6.19 duration-geometry disagreement decomposition.

This runner is read-only with respect to the recognizer. It consumes only the
five sealed v0.6.18 row-level artifacts and reproduces the frozen same-event
pair universe before attributing the remaining qualification disagreements.
"""
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

from factor_lab.visual_structure.two_wave.duration_geometry_decomposition_v0619 import (
    LOCAL_DURATION_REASONS,
    classify_rejected_reasons,
    interpretation_category,
    local_duration_boundary_diagnostics,
)
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import build_edge_graph

VIEWS = tuple(f"5m_offset_{i}" for i in range(5))
EXPECTED_FILTERED = {
    "5m_offset_1": 14784,
    "5m_offset_2": 12725,
    "5m_offset_3": 13412,
    "5m_offset_4": 16108,
}
EXPECTED_RAW = {
    "5m_offset_1": 8381,
    "5m_offset_2": 5770,
    "5m_offset_3": 6204,
    "5m_offset_4": 9098,
}
EXPECTED_CANDIDATE = {
    "5m_offset_1": {"both_qualified": 400, "both_rejected": 7809, "main_only_qualified": 101, "other_only_qualified": 71},
    "5m_offset_2": {"both_qualified": 287, "both_rejected": 5323, "main_only_qualified": 93, "other_only_qualified": 67},
    "5m_offset_3": {"both_qualified": 302, "both_rejected": 5736, "main_only_qualified": 90, "other_only_qualified": 76},
    "5m_offset_4": {"both_qualified": 473, "both_rejected": 8447, "main_only_qualified": 102, "other_only_qualified": 76},
}
EXPECTED_AGGREGATE = {"both_qualified": 1462, "both_rejected": 27315, "main_only_qualified": 386, "other_only_qualified": 290}
ARTIFACT_IDS = {
    "5m_offset_0": 10132007935,
    "5m_offset_1": 10132046343,
    "5m_offset_2": 10132056291,
    "5m_offset_3": 10132017437,
    "5m_offset_4": 10132055670,
}


def load_jsonl_gz(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def find_one(root: Path, name: str) -> Path:
    hits = list(root.rglob(name))
    if len(hits) != 1:
        raise RuntimeError(f"expected exactly one {name}, got {len(hits)}")
    return hits[0]


def filtered_key(row: dict) -> tuple[str, tuple[int, ...]]:
    return str(row["phase"]), tuple(int(x) for x in row["five_filtered_occurrence_bars"])


def matrix(pairs: list[tuple[dict, dict]]) -> dict:
    out = {"both_qualified": 0, "both_rejected": 0, "main_only_qualified": 0, "other_only_qualified": 0}
    for main, other in pairs:
        qm = bool(main["candidate_qualified"])
        qo = bool(other["candidate_qualified"])
        if qm and qo:
            out["both_qualified"] += 1
        elif not qm and not qo:
            out["both_rejected"] += 1
        elif qm:
            out["main_only_qualified"] += 1
        else:
            out["other_only_qualified"] += 1
    return out


def add_matrix(total: dict, row: dict) -> None:
    for key in total:
        total[key] += int(row[key])


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    if not 0.0 <= q <= 1.0:
        raise ValueError("quantile outside [0,1]")
    rows = sorted(float(x) for x in values)
    if len(rows) == 1:
        return rows[0]
    pos = (len(rows) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return rows[lo]
    w = pos - lo
    return rows[lo] * (1.0 - w) + rows[hi] * w


def quantiles(values: list[float]) -> dict:
    return {str(q): quantile(values, q) for q in (0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0)}


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    primary = Counter(row["primary_family"] for row in rows)
    involved = Counter(family for row in rows for family in row["involved_families"])
    orientation = Counter(row["orientation"] for row in rows)
    mixed = Counter(
        "+".join(row["involved_families"])
        for row in rows
        if row["primary_family"] == "mixed_multi_family"
    )
    local_rows = [row for row in rows if "local_duration" in row["involved_families"]]
    local_only = [row for row in rows if row["primary_family"] == "local_duration_only"]
    local_only_simple = sum(bool(row["duration_diagnostics"]["simple_one_bar_boundary_case"]) for row in local_only)

    reason_boundary = {}
    reason_to_flag = {
        "short_leg": "short_leg_one_bar_boundary",
        "short_cycle": "short_cycle_one_bar_boundary",
        "cycle_duration_mismatch": "cycle_ratio_one_bar_boundary",
    }
    for reason, flag in reason_to_flag.items():
        subset = [row for row in local_rows if reason in row["hard_reasons"]]
        yes = sum(bool(row["duration_diagnostics"]["boundary_flags"].get(flag)) for row in subset)
        reason_boundary[reason] = {
            "count": len(subset),
            "one_bar_boundary_count": yes,
            "one_bar_boundary_fraction": yes / len(subset) if subset else 0.0,
        }

    return {
        "disagreements": n,
        "primary_family_counts": dict(sorted(primary.items())),
        "primary_family_fractions": {key: value / n for key, value in sorted(primary.items())} if n else {},
        "any_family_involvement_counts": dict(sorted(involved.items())),
        "any_family_involvement_fractions": {key: value / n for key, value in sorted(involved.items())} if n else {},
        "mixed_family_combinations": dict(sorted(mixed.items())),
        "orientation_counts": dict(sorted(orientation.items())),
        "local_duration_only_count": len(local_only),
        "local_duration_only_simple_one_bar_count": local_only_simple,
        "local_duration_only_simple_one_bar_fraction": local_only_simple / len(local_only) if local_only else 0.0,
        "reason_level_boundary": reason_boundary,
        "long_span_safety_involved_count": involved.get("long_span", 0),
        "long_span_safety_involved_fraction": involved.get("long_span", 0) / n if n else 0.0,
        "duration_quantiles": {
            "max_abs_leg_duration_delta": quantiles([row["duration_diagnostics"]["max_abs_leg_duration_delta"] for row in local_rows]),
            "max_abs_cycle_duration_delta": quantiles([row["duration_diagnostics"]["max_abs_cycle_duration_delta"] for row in local_rows]),
            "rejected_cycle_ratio_minus_2": quantiles([row["duration_diagnostics"]["rejected"]["cycle_duration_ratio"] - 2.0 for row in local_rows]),
            "two_minus_qualified_cycle_ratio": quantiles([2.0 - row["duration_diagnostics"]["qualified"]["cycle_duration_ratio"] for row in local_rows]),
            "rejected_minus_qualified_cycle_ratio": quantiles([
                row["duration_diagnostics"]["rejected"]["cycle_duration_ratio"]
                - row["duration_diagnostics"]["qualified"]["cycle_duration_ratio"]
                for row in local_rows
            ]),
        },
    }


def write_result_card(path: Path, result: dict) -> None:
    pooled = result["pooled"]
    lines = [
        "# Two-Wave v0.6.19 duration-geometry decomposition result",
        "",
        f"Formal attribution: **`{result['interpretation_category']}`**",
        "",
        "v0.6.19 changes no recognizer or qualification rule. It decomposes only the 676 remaining v0.6.18 cross-slicing qualification disagreements.",
        "",
        "## Frozen control reproduction",
        "",
        f"- filtered mutual-unique same-event pairs: **{result['controls']['filtered_pairs']:,}**",
        f"- published raw strict same-event pairs: **{result['controls']['raw_strict_pairs']:,}**",
        f"- v0.6.18 disagreements: **{pooled['disagreements']}**",
        "",
        "## Decisive attribution",
        "",
        f"- local-duration family involved: **{pooled['any_family_involvement_counts'].get('local_duration', 0)}/{pooled['disagreements']} = {pooled['any_family_involvement_fractions'].get('local_duration', 0.0):.2%}**",
        f"- local-duration-only: **{pooled['local_duration_only_count']}**",
        f"- local-duration-only simple one-bar boundary: **{pooled['local_duration_only_simple_one_bar_count']}/{pooled['local_duration_only_count']} = {pooled['local_duration_only_simple_one_bar_fraction']:.2%}**",
        f"- long-span safety involved: **{pooled['long_span_safety_involved_count']}/{pooled['disagreements']} = {pooled['long_span_safety_involved_fraction']:.2%}**",
        "",
        "| reason | involved | one-bar boundary | fraction |",
        "|---|---:|---:|---:|",
    ]
    for reason in ("short_leg", "short_cycle", "cycle_duration_mismatch"):
        row = pooled["reason_level_boundary"][reason]
        lines.append(f"| {reason} | {row['count']} | {row['one_bar_boundary_count']} | {row['one_bar_boundary_fraction']:.2%} |")
    lines += [
        "",
        "Per-offset local-duration attribution:",
        "",
        "| offset | disagreements | local involved | local-only | local-only simple boundary |",
        "|---|---:|---:|---:|---:|",
    ]
    for view in VIEWS[1:]:
        row = result["per_offset"][view]
        lines.append(
            f"| {view} | {row['disagreements']} | {row['any_family_involvement_counts'].get('local_duration', 0)} ({row['any_family_involvement_fractions'].get('local_duration', 0.0):.2%}) | {row['local_duration_only_count']} | {row['local_duration_only_simple_one_bar_count']} ({row['local_duration_only_simple_one_bar_fraction']:.2%}) |"
        )
    lines += [
        "",
        "## Consequence",
        "",
        "The frozen category authorizes a future version to preregister **one narrow duration-boundary repair candidate**. It does not itself change any duration threshold, does not change v0.6.18 qualification authority, and does not unfreeze Range/UpTrend/DownTrend direction classification.",
        "",
        "`morphology_acceptance=false`  ",
        "`trade_authority=false`  ",
        "`production_authority=false`",
    ]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    filtered = {}
    records = {}
    record_by_filtered = {}
    for view in VIEWS:
        filtered[view] = load_jsonl_gz(find_one(args.input, f"filtered-{view}.json.gz"))
        records[view] = load_jsonl_gz(find_one(args.input, f"records-{view}.json.gz"))
        mapping = {filtered_key(row): row for row in records[view]}
        if len(mapping) != len(records[view]):
            raise AssertionError(f"duplicate published filtered key on {view}")
        record_by_filtered[view] = mapping

    main_view = VIEWS[0]
    aggregate_matrix = {key: 0 for key in EXPECTED_AGGREGATE}
    total_filtered = 0
    total_raw = 0
    disagreements = []
    per_offset_rows = {}

    for view in VIEWS[1:]:
        graph = build_edge_graph(
            filtered[main_view],
            filtered[view],
            time_field="five_filtered_occurrence_times",
            nominal_bar_minutes=5.0,
            require_phase=True,
        )
        filtered_pairs = list(graph.mutual_unique_matches)
        if len(filtered_pairs) != EXPECTED_FILTERED[view]:
            raise AssertionError(f"filtered pair drift {view}: {len(filtered_pairs)} != {EXPECTED_FILTERED[view]}")

        strict_pairs: list[tuple[dict, dict]] = []
        for i, j in filtered_pairs:
            main_record = record_by_filtered[main_view].get(filtered_key(filtered[main_view][i]))
            other_record = record_by_filtered[view].get(filtered_key(filtered[view][j]))
            if main_record is None or other_record is None:
                continue
            if strict_anchor_edge(main_record, other_record, 5.0) is not None:
                strict_pairs.append((main_record, other_record))
        if len(strict_pairs) != EXPECTED_RAW[view]:
            raise AssertionError(f"raw strict drift {view}: {len(strict_pairs)} != {EXPECTED_RAW[view]}")

        candidate_matrix = matrix(strict_pairs)
        if candidate_matrix != EXPECTED_CANDIDATE[view]:
            raise AssertionError(f"v0.6.18 candidate matrix drift {view}: {candidate_matrix} != {EXPECTED_CANDIDATE[view]}")
        add_matrix(aggregate_matrix, candidate_matrix)
        total_filtered += len(filtered_pairs)
        total_raw += len(strict_pairs)

        view_disagreements = []
        for main_record, other_record in strict_pairs:
            main_q = bool(main_record["candidate_qualified"])
            other_q = bool(other_record["candidate_qualified"])
            if main_q == other_q:
                continue
            if main_q:
                qualified = main_record
                rejected = other_record
                orientation = "main_qualified_other_rejected"
            else:
                qualified = other_record
                rejected = main_record
                orientation = "other_qualified_main_rejected"
            hard_reasons = [str(x) for x in rejected["candidate_hard_reasons"]]
            family = classify_rejected_reasons(hard_reasons)
            row = {
                "offset": view,
                "orientation": orientation,
                "phase": str(rejected["phase"]),
                "main_raw_occurrence_bars": [int(x) for x in main_record["published_raw_occurrence_bars"]],
                "other_raw_occurrence_bars": [int(x) for x in other_record["published_raw_occurrence_bars"]],
                **family,
            }
            if set(hard_reasons) & LOCAL_DURATION_REASONS:
                row["duration_diagnostics"] = local_duration_boundary_diagnostics(
                    rejected["published_raw_occurrence_bars"],
                    qualified["published_raw_occurrence_bars"],
                    hard_reasons,
                )
            view_disagreements.append(row)
            disagreements.append(row)
        per_offset_rows[view] = view_disagreements

    if total_filtered != 57029:
        raise AssertionError(f"aggregate filtered pair drift: {total_filtered} != 57029")
    if total_raw != 29453:
        raise AssertionError(f"aggregate raw strict drift: {total_raw} != 29453")
    if aggregate_matrix != EXPECTED_AGGREGATE:
        raise AssertionError(f"aggregate v0.6.18 matrix drift: {aggregate_matrix} != {EXPECTED_AGGREGATE}")
    if len(disagreements) != 676:
        raise AssertionError(f"disagreement drift: {len(disagreements)} != 676")

    pooled = summarize(disagreements)
    per_offset = {view: summarize(per_offset_rows[view]) for view in VIEWS[1:]}
    local_involved = pooled["any_family_involvement_counts"].get("local_duration", 0)
    category = interpretation_category(
        pooled["disagreements"],
        local_involved,
        pooled["local_duration_only_count"],
        pooled["local_duration_only_simple_one_bar_count"],
    )

    result = {
        "schema": "two_wave_duration_geometry_decomposition_result@0.6.19",
        "interpretation_category": category,
        "source_workflow_run": 34423674192,
        "source_artifact_ids": ARTIFACT_IDS,
        "controls": {
            "filtered_pairs": total_filtered,
            "raw_strict_pairs": total_raw,
            "candidate_matrix": aggregate_matrix,
            "control_reproduction": True,
        },
        "pooled": pooled,
        "per_offset": per_offset,
        "recognizer_changed": False,
        "qualification_rule_changed": False,
        "morphology_acceptance": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "production_authority": False,
    }

    (args.output / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    with gzip.open(args.output / "disagreements.jsonl.gz", "wt", encoding="utf-8") as fh:
        for row in disagreements:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    write_result_card(args.output / "RESULT_CARD.md", result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
