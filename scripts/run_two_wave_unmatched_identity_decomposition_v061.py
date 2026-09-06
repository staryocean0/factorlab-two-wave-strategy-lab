#!/usr/bin/env python3
"""v0.6.1 audit: decompose v0.6.0 unmatched identities.

Evaluator-only: replay frozen v0.5.2/v0.5.4, reproduce v0.6.0 controls,
then trace each unmatched main identity through evaluated raw identity,
filtered tuple birth, and filtered-extremum survival layers.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.cycle_scale_qualification_v054 import (
    build_cycle_scale_qualification_run,
)
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import (
    canonicalize_qualified_records,
    causal_publish_qualified_identities,
    mutual_unique_strict_matches,
)
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import (
    NOMINAL_BAR_MINUTES,
    any_level_anchor_survival,
    attach_times,
    build_edge_graph,
    canonicalize_evaluated_records,
    canonicalize_tuple_births,
    level_anchor_survival,
    local_envelope_overlap_diagnostic,
    session_boundary_overlay,
    to_minutes,
)

VIEWS = [f"5m_offset_{i}" for i in range(5)]
EXPECTED_QUALIFIED = {
    "5m_offset_0": 734,
    "5m_offset_1": 691,
    "5m_offset_2": 691,
    "5m_offset_3": 721,
    "5m_offset_4": 746,
}
EXPECTED_CANONICAL_MAIN = 712
EXPECTED_V060 = {
    "5m_offset_1": (180, 1, 1, 531, 492),
    "5m_offset_2": (129, 0, 0, 583, 549),
    "5m_offset_3": (129, 1, 0, 582, 571),
    "5m_offset_4": (184, 1, 1, 527, 543),
}


def save(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def attach_raw_times(event: dict, bars: list[dict]) -> dict:
    out = dict(event)
    out["five_occurrence_times"] = attach_times(out["five_occurrence_bars"], bars)
    return out


def event_key(event: dict, bars_field: str) -> tuple[str, tuple[int, ...]]:
    return str(event["phase"]), tuple(int(x) for x in event[bars_field])


def q(values: list[float], frac: float):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[int(round((len(ordered) - 1) * frac))]


def summarize_numeric(values) -> dict:
    rows = [float(x) for x in values if x is not None]
    if not rows:
        return {"count": 0, "min": None, "median": None, "p90": None, "max": None}
    return {
        "count": len(rows),
        "min": min(rows),
        "median": q(rows, 0.5),
        "p90": q(rows, 0.9),
        "max": max(rows),
    }


def build_view(view: str) -> dict:
    bars, data_audit = load_development_bars(
        ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json"
    )
    run = build_cycle_scale_qualification_run(bars, cfg=MaturityConfig(timeframe=view))
    qualified = [r for r in run.ledger.records if bool(r.get("scale_qualified"))]
    canonical = [attach_raw_times(e, bars) for e in canonicalize_qualified_records(qualified)]
    causal = causal_publish_qualified_identities(qualified)
    causal_by_id = {e["canonical_identity_id"]: e for e in causal["identity_events"]}
    if {e["canonical_identity_id"] for e in canonical} != set(causal_by_id):
        raise AssertionError("static and causal v0.6.0 identity sets differ")
    evaluated = canonicalize_evaluated_records(run.evaluated_records, bars)
    tuples = canonicalize_tuple_births(run.base_run.tuple_births, bars)
    record_by_id = {str(r["record_id"]): r for r in run.evaluated_records}
    projection_by_event = {str(row["event_id"]): row for row in run.base_run.projection_audit}
    return {
        "view": view,
        "bars": bars,
        "data_audit": data_audit,
        "run": run,
        "qualified_records": qualified,
        "canonical": canonical,
        "causal_by_id": causal_by_id,
        "evaluated": evaluated,
        "tuples": tuples,
        "record_by_id": record_by_id,
        "projection_by_event": projection_by_event,
        "evaluated_index": {
            event_key(e, "five_occurrence_bars"): i for i, e in enumerate(evaluated)
        },
        "tuple_index": {
            event_key(e, "five_filtered_occurrence_bars"): i for i, e in enumerate(tuples)
        },
    }


def projection_diagnostics(main_record: dict, other_tuple: dict, other: dict) -> dict:
    rows = [other["projection_by_event"].get(str(event_id)) for event_id in other_tuple["member_event_ids"]]
    rows = [row for row in rows if row is not None]
    reasons = sorted({str(row.get("projection_reason")) for row in rows if row.get("projection_reason")})
    projection_valid = sum(bool(row.get("projection_valid")) for row in rows)
    evaluate_pair_invalid = sum(
        str(row.get("projection_reason", "")).startswith("evaluate_pair_invalid:") for row in rows
    )
    raw_projection_displacement = False
    projected_max_deltas = []
    main_times = attach_times(main_record["five_occurrence_bars"], main_record["__bars"])
    for row in rows:
        raw = row.get("raw_occurrence_bars")
        if not row.get("projection_valid") or raw is None:
            continue
        other_times = attach_times(raw, other["bars"])
        deltas = [abs(to_minutes(a) - to_minutes(b)) for a, b in zip(main_times, other_times)]
        projected_max_deltas.append(max(deltas))
        if max(deltas) > NOMINAL_BAR_MINUTES:
            raw_projection_displacement = True
    return {
        "projection_audit_rows": len(rows),
        "projection_valid_rows": projection_valid,
        "projection_invalid_rows": len(rows) - projection_valid,
        "evaluate_pair_invalid_rows": evaluate_pair_invalid,
        "projection_reasons": reasons,
        "raw_projection_displacement": raw_projection_displacement,
        "projected_raw_max_delta_minutes": summarize_numeric(projected_max_deltas),
    }


def identity_context(main: dict, main_event: dict) -> tuple[dict, list[str], list[str], dict]:
    causal = main["causal_by_id"][main_event["canonical_identity_id"]]
    first_id = str(causal["first_record_id"])
    record = dict(main["record_by_id"][first_id])
    record["__bars"] = main["bars"]
    filtered_times = attach_times(record["filtered_occurrence_bars"], main["bars"])
    raw_times = main_event["five_occurrence_times"]
    boundary = session_boundary_overlay(raw_times, filtered_times)
    return record, raw_times, filtered_times, boundary


def audit_pair(main: dict, other: dict) -> tuple[dict, list[dict]]:
    q0 = mutual_unique_strict_matches(main["canonical"], other["canonical"], NOMINAL_BAR_MINUTES)
    expected = EXPECTED_V060[other["view"]]
    actual = (
        len(q0.matches),
        len(q0.ambiguous_a),
        len(q0.ambiguous_b),
        len(q0.unmatched_a),
        len(q0.unmatched_b),
    )
    if actual != expected:
        raise AssertionError(f"v0.6.0 pair control drift for {other['view']}: {actual} != {expected}")

    q_graph = build_edge_graph(
        main["canonical"], other["canonical"], time_field="five_occurrence_times", require_phase=True
    )
    eval_same = build_edge_graph(
        main["evaluated"], other["evaluated"], time_field="five_occurrence_times", require_phase=True
    )
    eval_ignore = build_edge_graph(
        main["evaluated"], other["evaluated"], time_field="five_occurrence_times", require_phase=False
    )
    tuple_same = build_edge_graph(
        main["tuples"], other["tuples"], time_field="five_filtered_occurrence_times", require_phase=True
    )
    tuple_ignore = build_edge_graph(
        main["tuples"], other["tuples"], time_field="five_filtered_occurrence_times", require_phase=False
    )

    matched_main = {i for i, _ in q0.matches}
    ambiguous_main = set(q0.ambiguous_a)
    details = []

    for i in q0.unmatched_a:
        main_event = main["canonical"][i]
        record, raw_times, filtered_times, boundary = identity_context(main, main_event)
        primary = None
        evidence = {}

        if q_graph.a_edges[i]:
            primary = "qualified_strict_edge_nonmutual"
            evidence["qualified_edge_degree_main"] = len(q_graph.a_edges[i])
            evidence["qualified_target_degrees"] = [len(q_graph.b_edges[j]) for j in q_graph.a_edges[i]]

        main_eval_idx = main["evaluated_index"][event_key(main_event, "five_occurrence_bars")]
        if primary is None:
            partner_ignore = eval_ignore.mutual_partner_a(main_eval_idx)
            if partner_ignore is not None:
                other_eval = other["evaluated"][partner_ignore]
                if other_eval["phase"] != main_event["phase"]:
                    primary = "phase_mismatch_raw_evaluated"
                    evidence["other_phase"] = other_eval["phase"]
                    evidence["other_qualified_any"] = bool(other_eval["qualified_any"])

        if primary is None:
            partner_same = eval_same.mutual_partner_a(main_eval_idx)
            if partner_same is not None:
                other_eval = other["evaluated"][partner_same]
                if bool(other_eval["qualified_any"]):
                    raise AssertionError("qualified evaluated counterpart missing from v0.6.0 qualified match graph")
                primary = "qualification_survival_loss"
                evidence["rejection_reasons"] = list(other_eval["rejection_reasons_union"])
                evidence["other_birth_scale_levels"] = list(other_eval["birth_scale_levels"])
            elif eval_same.a_edges[main_eval_idx] or eval_ignore.a_edges[main_eval_idx]:
                primary = "evaluated_identity_nonmutual"
                evidence["same_phase_edge_degree_main"] = len(eval_same.a_edges[main_eval_idx])
                evidence["phase_ignored_edge_degree_main"] = len(eval_ignore.a_edges[main_eval_idx])

        main_tuple_key = (str(record["phase"]), tuple(int(x) for x in record["filtered_occurrence_bars"]))
        main_tuple_idx = main["tuple_index"].get(main_tuple_key)
        if main_tuple_idx is None:
            raise AssertionError("causal evaluated record has no source filtered tuple birth")

        if primary is None:
            tuple_ignore_partner = tuple_ignore.mutual_partner_a(main_tuple_idx)
            if tuple_ignore_partner is not None:
                other_tuple = other["tuples"][tuple_ignore_partner]
                if other_tuple["phase"] != record["phase"]:
                    primary = "phase_mismatch_filtered_tuple"
                    evidence["other_phase"] = other_tuple["phase"]

        if primary is None:
            tuple_partner = tuple_same.mutual_partner_a(main_tuple_idx)
            if tuple_partner is not None:
                other_tuple = other["tuples"][tuple_partner]
                primary = "post_tuple_birth_loss"
                evidence["main_birth_scale_level"] = int(record["birth_scale_level"])
                evidence["other_tuple_birth_scale_levels"] = list(other_tuple["birth_scale_levels"])
                evidence["projection"] = projection_diagnostics(record, other_tuple, other)
            elif tuple_same.a_edges[main_tuple_idx] or tuple_ignore.a_edges[main_tuple_idx]:
                primary = "tuple_identity_nonmutual"
                evidence["same_phase_edge_degree_main"] = len(tuple_same.a_edges[main_tuple_idx])
                evidence["phase_ignored_edge_degree_main"] = len(tuple_ignore.a_edges[main_tuple_idx])

        birth_level = int(record["birth_scale_level"])
        if birth_level < 0 or birth_level >= len(other["run"].base_run.nodes_by_level):
            raise AssertionError("birth scale level outside other-view TCSS level range")
        same_level = level_anchor_survival(
            filtered_times,
            str(record["phase"]),
            other["run"].base_run.nodes_by_level[birth_level],
            other["bars"],
        )
        any_level = any_level_anchor_survival(
            filtered_times,
            str(record["phase"]),
            other["run"].base_run.nodes_by_level,
            other["bars"],
        )

        if primary is None:
            if same_level["all_unique"]:
                primary = "tuple_topology_or_death_certification_mismatch"
            else:
                levels = list(any_level["all_unique_levels"])
                if len(levels) == 1:
                    if levels[0] == birth_level:
                        raise AssertionError("same-level survival contradiction")
                    primary = "birth_scale_path_shift"
                    evidence["recovered_other_level"] = levels[0]
                elif len(levels) > 1:
                    primary = "birth_scale_path_ambiguous"
                    evidence["recovered_other_levels"] = levels
                else:
                    primary = "filtered_extremum_survival_mismatch"

        local = local_envelope_overlap_diagnostic(main_event, other["canonical"])
        details.append(
            {
                "main_view": main["view"],
                "other_view": other["view"],
                "canonical_identity_id": main_event["canonical_identity_id"],
                "phase": main_event["phase"],
                "five_occurrence_times": raw_times,
                "causal_first_record_id": record["record_id"],
                "causal_birth_scale_level": birth_level,
                "causal_filtered_occurrence_times": filtered_times,
                "primary_attribution": primary,
                "evidence": evidence,
                "same_level_anchor_survival": {
                    k: same_level[k]
                    for k in (
                        "candidate_counts", "unique_anchor_count", "missing_anchor_count",
                        "ambiguous_anchor_count", "all_unique"
                    )
                },
                "any_level_anchor_survival": {
                    "all_unique_levels": any_level["all_unique_levels"],
                    "max_unique_anchor_count": any_level["max_unique_anchor_count"],
                },
                "session_boundary": boundary,
                "local_envelope_overlap": local,
                "future_outcome_used": False,
                "trade_authority": False,
            }
        )

    if len(details) != len(q0.unmatched_a):
        raise AssertionError("every v0.6.0 unmatched main identity must receive one detail row")
    if any(not row["primary_attribution"] for row in details):
        raise AssertionError("every unmatched main identity must receive exactly one primary attribution")
    if len(matched_main) + len(ambiguous_main) + len(details) != len(main["canonical"]):
        raise AssertionError("main identity accounting does not close")

    counts = Counter(row["primary_attribution"] for row in details)
    rejection = Counter()
    projection = Counter()
    same_unique = Counter()
    any_unique = Counter()
    boundary_by_category = defaultdict(lambda: [0, 0])
    local_counts = []
    local_min_deltas = []
    for row in details:
        cat = row["primary_attribution"]
        boundary_by_category[cat][1] += 1
        boundary_by_category[cat][0] += int(row["session_boundary"]["boundary_tagged"])
        same_unique[int(row["same_level_anchor_survival"]["unique_anchor_count"])] += 1
        any_unique[int(row["any_level_anchor_survival"]["max_unique_anchor_count"])] += 1
        local_counts.append(int(row["local_envelope_overlap"]["candidate_count"]))
        if row["local_envelope_overlap"]["minimum_max_delta_minutes"] is not None:
            local_min_deltas.append(float(row["local_envelope_overlap"]["minimum_max_delta_minutes"]))
        if cat == "qualification_survival_loss":
            rejection.update(row["evidence"].get("rejection_reasons", []))
        if cat == "post_tuple_birth_loss":
            p = row["evidence"].get("projection", {})
            projection["projection_invalid_rows"] += int(p.get("projection_invalid_rows", 0))
            projection["evaluate_pair_invalid_rows"] += int(p.get("evaluate_pair_invalid_rows", 0))
            projection["raw_projection_displacement_cases"] += int(bool(p.get("raw_projection_displacement")))

    matched_boundary = 0
    for i in matched_main:
        event = main["canonical"][i]
        _, raw_times, filtered_times, boundary = identity_context(main, event)
        matched_boundary += int(boundary["boundary_tagged"])

    summary = {
        "main_view": main["view"],
        "other_view": other["view"],
        "v060_control": {
            "main_events": len(main["canonical"]),
            "other_events": len(other["canonical"]),
            "mutual_unique_matches": len(q0.matches),
            "ambiguous_main": len(q0.ambiguous_a),
            "ambiguous_other": len(q0.ambiguous_b),
            "unmatched_main": len(q0.unmatched_a),
            "unmatched_other": len(q0.unmatched_b),
        },
        "attribution_denominator": len(details),
        "attribution_counts": dict(sorted(counts.items())),
        "attribution_fractions": {
            key: value / len(details) if details else None for key, value in sorted(counts.items())
        },
        "qualification_rejection_reasons": dict(sorted(rejection.items())),
        "post_tuple_projection_diagnostics": dict(sorted(projection.items())),
        "same_level_unique_anchor_count_distribution": {str(k): v for k, v in sorted(same_unique.items())},
        "max_any_level_unique_anchor_count_distribution": {str(k): v for k, v in sorted(any_unique.items())},
        "session_boundary_by_attribution": {
            key: {"tagged": tagged, "total": total, "fraction": tagged / total if total else None}
            for key, (tagged, total) in sorted(boundary_by_category.items())
        },
        "session_boundary_strict_matched_control": {
            "tagged": matched_boundary,
            "total": len(matched_main),
            "fraction": matched_boundary / len(matched_main) if matched_main else None,
        },
        "local_envelope_candidate_count": summarize_numeric(local_counts),
        "local_envelope_minimum_max_delta_minutes": summarize_numeric(local_min_deltas),
    }
    return summary, details


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--output",
        type=Path,
        default=ROOT / "cloud_results/local_v061_unmatched_identity_decomposition",
    )
    args = ap.parse_args()

    views = {view: build_view(view) for view in VIEWS}
    for view, expected in EXPECTED_QUALIFIED.items():
        actual = len(views[view]["qualified_records"])
        if actual != expected:
            raise AssertionError(f"IDENTITY_INPUT_DRIFT {view}: {actual} != {expected}")
    if len(views["5m_offset_0"]["canonical"]) != EXPECTED_CANONICAL_MAIN:
        raise AssertionError("IDENTITY_INPUT_DRIFT main canonical count")

    pair_summaries = {}
    for view in VIEWS[1:]:
        pair_summary, details = audit_pair(views["5m_offset_0"], views[view])
        pair_summaries[view] = pair_summary
        save(args.output / f"details_offset_{view[-1]}.json", details)

    data_identity = {
        "schema": "two_wave_v061_data_identity@1.0",
        "instrument": "000852.SH",
        "fresh_oos": False,
        "local_resampling_performed": False,
        "post_2020_rows_included": False,
        "views": [],
    }
    for view in VIEWS:
        path = ROOT / f"data/development/{view}.parquet"
        audit = views[view]["data_audit"]
        data_identity["views"].append(
            {
                "view": view,
                "path": str(path.relative_to(ROOT)),
                "sha256": file_sha256(path),
                "rows": int(audit["rows"]),
                "minimum_trading_day": audit["minimum_trading_day"],
                "maximum_trading_day": audit["maximum_trading_day"],
                "manifest_verified": bool(audit.get("manifest_verified")),
            }
        )
    save(args.output / "data_identity.json", data_identity)

    result = {
        "schema": "two_wave_unmatched_identity_decomposition@0.6.1",
        "status": "unmatched_identity_decomposition_generated_pending_cloud_adjudication",
        "frozen_upstream": "v0.5.2_exact_ridge_plus_v0.5.4_full_cycle_qualification_plus_v0.6.0_Route_M",
        "nominal_bar_minutes": NOMINAL_BAR_MINUTES,
        "qualified_counts": {view: len(views[view]["qualified_records"]) for view in VIEWS},
        "canonical_qualified_counts": {view: len(views[view]["canonical"]) for view in VIEWS},
        "pair_decomposition": pair_summaries,
        "future_outcome_used": False,
        "trade_authority": False,
        "operational_baseline": "v0.4.3",
        "morphology_status": "morphology_replication_not_yet_accepted",
    }
    save(args.output / "summary.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
