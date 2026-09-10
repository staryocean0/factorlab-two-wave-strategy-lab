#!/usr/bin/env python3
"""Analyze frozen v0.6.18 row artifacts under the v0.6.19 protocol.

This script is read-only with respect to recognizer rules. It reproduces the
filtered-first same-event universe, the published-raw strict universe, and the
v0.6.18 candidate matrix before emitting any attribution result.
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
    AMPLITUDE_REASONS,
    CONFIRMATION_REASONS,
    LOCAL_DURATION_REASONS,
    LONG_SPAN_REASONS,
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
EXPECTED_STRICT = {
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
EXPECTED_AGG = {"both_qualified": 1462, "both_rejected": 27315, "main_only_qualified": 386, "other_only_qualified": 290}
EXPECTED_FILTERED_TOTAL = 57029
EXPECTED_STRICT_TOTAL = 29453
EXPECTED_DISAGREEMENTS = 676

FAMILY_REASON_MAP = {
    "local_duration": LOCAL_DURATION_REASONS,
    "amplitude": AMPLITUDE_REASONS,
    "confirmation": CONFIRMATION_REASONS,
    "long_span": LONG_SPAN_REASONS,
}


def load_jsonl_gz(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def locate_one(root: Path, pattern: str) -> Path:
    hits = list(root.rglob(pattern))
    if len(hits) != 1:
        raise RuntimeError(f"expected one {pattern}, found {len(hits)}")
    return hits[0]


def publication_map(rows: list[dict]) -> dict[tuple[str, tuple[int, ...]], dict]:
    out = {}
    for row in rows:
        key = (str(row["phase"]), tuple(int(x) for x in row["five_filtered_occurrence_bars"]))
        if key in out:
            raise AssertionError(f"duplicate published filtered identity: {key}")
        out[key] = row
    return out


def matrix(pairs: list[tuple[dict, dict]]) -> dict:
    out = {"both_qualified": 0, "both_rejected": 0, "main_only_qualified": 0, "other_only_qualified": 0}
    for a, b in pairs:
        qa = bool(a["candidate_qualified"])
        qb = bool(b["candidate_qualified"])
        if qa and qb:
            out["both_qualified"] += 1
        elif not qa and not qb:
            out["both_rejected"] += 1
        elif qa:
            out["main_only_qualified"] += 1
        else:
            out["other_only_qualified"] += 1
    return out


def add_counts(total: dict, row: dict) -> None:
    for key in total:
        total[key] += int(row[key])


def q(values: list[float]) -> dict:
    if not values:
        return {k: None for k in ("0", "0.25", "0.5", "0.75", "0.9", "0.99", "1")}
    xs = sorted(float(x) for x in values)
    def at(p: float) -> float:
        if len(xs) == 1:
            return xs[0]
        pos = p * (len(xs) - 1)
        lo = math.floor(pos)
        hi = math.ceil(pos)
        if lo == hi:
            return xs[lo]
        w = pos - lo
        return xs[lo] * (1.0 - w) + xs[hi] * w
    return {str(p): at(p) for p in (0, 0.25, 0.5, 0.75, 0.9, 0.99, 1)}


def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    primary = Counter(r["primary_family"] for r in rows)
    involvement = Counter(f for r in rows for f in set(r["involved_families"]))
    orientation = Counter(r["orientation"] for r in rows)
    local_only = [r for r in rows if r["primary_family"] == "local_duration_only"]
    local_only_simple = sum(bool(r["simple_one_bar_boundary_case"]) for r in local_only)

    reason_counts = Counter(reason for r in rows for reason in set(r["rejected_hard_reasons"]))
    reason_boundary_num = Counter()
    reason_boundary_den = Counter()
    reason_flag = {
        "short_leg": "short_leg_one_bar_boundary",
        "short_cycle": "short_cycle_one_bar_boundary",
        "cycle_duration_mismatch": "cycle_ratio_one_bar_boundary",
    }
    for r in rows:
        for reason, flag in reason_flag.items():
            if reason in r["rejected_hard_reasons"]:
                reason_boundary_den[reason] += 1
                if bool(r["boundary_flags"].get(flag, False)):
                    reason_boundary_num[reason] += 1

    local_rows = [r for r in rows if "local_duration" in r["involved_families"]]
    ratio_rejected_margin = [max(0.0, float(r["rejected_duration"]["cycle_duration_ratio"]) - 2.0) for r in local_rows]
    ratio_qualified_margin = [max(0.0, 2.0 - float(r["qualified_duration"]["cycle_duration_ratio"])) for r in local_rows]

    return {
        "disagreements": total,
        "primary_family_counts": dict(primary),
        "primary_family_fractions": {k: v / total for k, v in primary.items()} if total else {},
        "any_family_involvement_counts": dict(involvement),
        "any_family_involvement_fractions": {k: v / total for k, v in involvement.items()} if total else {},
        "orientation_counts": dict(orientation),
        "local_duration_only": len(local_only),
        "local_duration_only_simple_one_bar": local_only_simple,
        "local_duration_only_simple_one_bar_fraction": local_only_simple / len(local_only) if local_only else 0.0,
        "reason_involvement_counts": dict(reason_counts),
        "reason_one_bar_boundary": {
            reason: {
                "numerator": reason_boundary_num[reason],
                "denominator": reason_boundary_den[reason],
                "fraction": reason_boundary_num[reason] / reason_boundary_den[reason] if reason_boundary_den[reason] else 0.0,
            }
            for reason in reason_flag
        },
        "duration_delta_quantiles": {
            "max_abs_leg_duration_delta": q([r["max_abs_leg_duration_delta"] for r in local_rows]),
            "max_abs_cycle_duration_delta": q([r["max_abs_cycle_duration_delta"] for r in local_rows]),
            "rejected_cycle_ratio_excess_over_2": q(ratio_rejected_margin),
            "qualified_cycle_ratio_headroom_below_2": q(ratio_qualified_margin),
        },
        "long_span_material_involvement": {
            "count": involvement.get("long_span", 0),
            "fraction": involvement.get("long_span", 0) / total if total else 0.0,
        },
    }


def write_card(path: Path, result: dict) -> None:
    pooled = result["pooled"]
    lines = [
        "# Two-Wave v0.6.19 result card",
        "",
        f"Formal attribution: **`{result['interpretation_category']}`**",
        "",
        "v0.6.19 changes no recognizer or qualification rule. It decomposes the 676 remaining v0.6.18 qualification disagreements on the exact frozen same-event universe.",
        "",
        "## Frozen control reproduction",
        "",
        f"- filtered mutual-unique pairs: **{result['controls']['filtered_pairs']:,} / 57,029**",
        f"- published raw strict pairs: **{result['controls']['strict_pairs']:,} / 29,453**",
        f"- v0.6.18 disagreements: **{pooled['disagreements']} / 676**",
        f"- v0.6.18 candidate matrix: `{result['controls']['candidate_matrix']}`",
        "",
        "## Pooled attribution",
        "",
        f"- local-duration involved: **{pooled['any_family_involvement_counts'].get('local_duration', 0)} / {pooled['disagreements']} = {pooled['any_family_involvement_fractions'].get('local_duration', 0.0):.2%}**",
        f"- local-duration-only: **{pooled['local_duration_only']}**",
        f"- simple one-bar boundary among local-duration-only: **{pooled['local_duration_only_simple_one_bar']} / {pooled['local_duration_only']} = {pooled['local_duration_only_simple_one_bar_fraction']:.2%}**",
        f"- amplitude involved: **{pooled['any_family_involvement_counts'].get('amplitude', 0)} = {pooled['any_family_involvement_fractions'].get('amplitude', 0.0):.2%}**",
        f"- confirmation involved: **{pooled['any_family_involvement_counts'].get('confirmation', 0)} = {pooled['any_family_involvement_fractions'].get('confirmation', 0.0):.2%}**",
        f"- long-span involved: **{pooled['any_family_involvement_counts'].get('long_span', 0)} = {pooled['any_family_involvement_fractions'].get('long_span', 0.0):.2%}**",
        "",
        "## Per-offset disagreements",
        "",
        "| offset | disagreements | local involved | local-only | simple one-bar / local-only |",
        "|---|---:|---:|---:|---:|",
    ]
    for view in VIEWS[1:]:
        row = result["offsets"][view]
        lines.append(
            f"| {view} | {row['disagreements']} | {row['any_family_involvement_counts'].get('local_duration', 0)} | {row['local_duration_only']} | {row['local_duration_only_simple_one_bar_fraction']:.2%} |"
        )
    lines += [
        "",
        "## Consequence",
        "",
        "v0.6.18 remains the current best qualification-policy component. This result does not change global morphology acceptance, direction/state classification, trade authority, or production authority.",
    ]
    if result["interpretation_category"] == "v0619_local_duration_boundary_sensitivity_dominant":
        lines.append("The frozen protocol therefore authorizes one next preregistered narrow duration-boundary repair candidate; it does not authorize broad threshold loosening.")
    elif result["interpretation_category"] == "v0619_local_duration_geometry_material_not_simple_boundary":
        lines.append("The next step must redefine/model duration geometry rather than simply add one native bar to a threshold.")
    else:
        lines.append("Duration tuning is deprioritized; the largest remaining family becomes the next audit target.")
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
    for view in VIEWS:
        filtered[view] = load_jsonl_gz(locate_one(args.input, f"filtered-{view}.json.gz"))
        records[view] = load_jsonl_gz(locate_one(args.input, f"records-{view}.json.gz"))
        pubmaps[view] = publication_map(records[view])

    all_rows = []
    offsets = {}
    candidate_total = {key: 0 for key in EXPECTED_AGG}
    filtered_total = 0
    strict_total = 0
    main_view = VIEWS[0]

    for view in VIEWS[1:]:
        graph = build_edge_graph(
            filtered[main_view],
            filtered[view],
            time_field="five_filtered_occurrence_times",
            nominal_bar_minutes=5.0,
            require_phase=True,
        )
        filtered_matches = list(graph.mutual_unique_matches)
        if len(filtered_matches) != EXPECTED_FILTERED[view]:
            raise AssertionError(f"filtered pair control drift {view}: {len(filtered_matches)} != {EXPECTED_FILTERED[view]}")

        strict = []
        for i, j in filtered_matches:
            fa = filtered[main_view][i]
            fb = filtered[view][j]
            ka = (str(fa["phase"]), tuple(int(x) for x in fa["five_filtered_occurrence_bars"]))
            kb = (str(fb["phase"]), tuple(int(x) for x in fb["five_filtered_occurrence_bars"]))
            a = pubmaps[main_view].get(ka)
            b = pubmaps[view].get(kb)
            if a is None or b is None:
                continue
            if strict_anchor_edge(a, b, 5.0) is not None:
                strict.append((a, b))
        if len(strict) != EXPECTED_STRICT[view]:
            raise AssertionError(f"raw strict control drift {view}: {len(strict)} != {EXPECTED_STRICT[view]}")
        cand = matrix(strict)
        if cand != EXPECTED_CANDIDATE[view]:
            raise AssertionError(f"v0.6.18 candidate matrix drift {view}: {cand} != {EXPECTED_CANDIDATE[view]}")

        rows = []
        for a, b in strict:
            qa = bool(a["candidate_qualified"])
            qb = bool(b["candidate_qualified"])
            if qa == qb:
                continue
            if qa:
                qualified, rejected = a, b
                orientation = "main_qualified_other_rejected"
            else:
                qualified, rejected = b, a
                orientation = "main_rejected_other_qualified"
            reasons = [str(x) for x in rejected["candidate_hard_reasons"]]
            family = classify_rejected_reasons(reasons)
            local = local_duration_boundary_diagnostics(
                rejected["published_raw_occurrence_bars"],
                qualified["published_raw_occurrence_bars"],
                reasons,
            )
            row = {
                "offset": view,
                "orientation": orientation,
                "phase": str(rejected["phase"]),
                "rejected_hard_reasons": sorted(set(reasons)),
                **family,
                "rejected_duration": local["rejected"],
                "qualified_duration": local["qualified"],
                "max_abs_leg_duration_delta": local["max_abs_leg_duration_delta"],
                "max_abs_cycle_duration_delta": local["max_abs_cycle_duration_delta"],
                "boundary_flags": local["boundary_flags"],
                "simple_one_bar_boundary_case": local["simple_one_bar_boundary_case"],
                "future_outcome_used": False,
                "trade_authority": False,
            }
            rows.append(row)
            all_rows.append(row)

        offsets[view] = summarize(rows)
        offsets[view]["filtered_pairs"] = len(filtered_matches)
        offsets[view]["strict_pairs"] = len(strict)
        offsets[view]["candidate_matrix"] = cand
        filtered_total += len(filtered_matches)
        strict_total += len(strict)
        add_counts(candidate_total, cand)

    if filtered_total != EXPECTED_FILTERED_TOTAL:
        raise AssertionError(f"aggregate filtered control drift: {filtered_total}")
    if strict_total != EXPECTED_STRICT_TOTAL:
        raise AssertionError(f"aggregate strict control drift: {strict_total}")
    if candidate_total != EXPECTED_AGG:
        raise AssertionError(f"aggregate v0.6.18 candidate matrix drift: {candidate_total}")
    if len(all_rows) != EXPECTED_DISAGREEMENTS:
        raise AssertionError(f"disagreement control drift: {len(all_rows)}")

    pooled = summarize(all_rows)
    category = interpretation_category(
        pooled["disagreements"],
        pooled["any_family_involvement_counts"].get("local_duration", 0),
        pooled["local_duration_only"],
        pooled["local_duration_only_simple_one_bar"],
    )
    result = {
        "schema": "two_wave_duration_geometry_decomposition_result@0.6.19",
        "interpretation_category": category,
        "input_workflow_run": 34423674192,
        "controls": {
            "filtered_pairs": filtered_total,
            "strict_pairs": strict_total,
            "candidate_matrix": candidate_total,
            "control_reproduction": True,
        },
        "pooled": pooled,
        "offsets": offsets,
        "changed_recognizer_rules": [],
        "v0618_remains_best_qualification_component": True,
        "morphology_acceptance": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "production_authority": False,
    }
    (args.output / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    with gzip.open(args.output / "disagreements.jsonl.gz", "wt", encoding="utf-8") as fh:
        for row in all_rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    write_card(args.output / "RESULT_CARD.md", result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
