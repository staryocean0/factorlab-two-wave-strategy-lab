#!/usr/bin/env python3
"""v0.6.2 audit: raw-projection financial identity without changing recognizer logic."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gc
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.cycle_scale_qualification_v054 import (
    build_cycle_scale_qualification_run,
)
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import _projection_adapter
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import (
    canonicalize_qualified_records,
    causal_publish_qualified_identities,
    mutual_unique_strict_matches,
)
from factor_lab.visual_structure.two_wave.raw_projection_identity_v062 import (
    CanonicalPathIndex,
    NOMINAL_BAR_MINUTES,
    audit_projection_event,
    earliest_valid_member,
    one_minute_projection_from_windows,
    paired_window_diagnostics,
    raw_pair_displacement,
    strict_time_tuple_match,
    summarize_projection_group,
    to_minutes,
)
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import (
    attach_times,
    build_edge_graph,
    canonicalize_evaluated_records,
    canonicalize_tuple_births,
)

VIEWS = [f"5m_offset_{i}" for i in range(5)]
EXPECTED_QUALIFIED = {
    "5m_offset_0": 734,
    "5m_offset_1": 691,
    "5m_offset_2": 691,
    "5m_offset_3": 721,
    "5m_offset_4": 746,
}
EXPECTED_CANONICAL = {
    "5m_offset_0": 712,
    "5m_offset_1": 673,
    "5m_offset_2": 678,
    "5m_offset_3": 700,
    "5m_offset_4": 728,
}
EXPECTED_V060 = {
    "5m_offset_1": (180, 1, 1, 531, 492),
    "5m_offset_2": (129, 0, 0, 583, 549),
    "5m_offset_3": (129, 1, 0, 582, 571),
    "5m_offset_4": (184, 1, 1, 527, 543),
}
EXPECTED_POST_TUPLE = {
    "5m_offset_1": 191,
    "5m_offset_2": 195,
    "5m_offset_3": 194,
    "5m_offset_4": 209,
}
EXPECTED_POST_TUPLE_DISPLACED = {
    "5m_offset_1": 191,
    "5m_offset_2": 194,
    "5m_offset_3": 193,
    "5m_offset_4": 209,
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


def build_projection_groups(run, tuple_groups: list[dict], bars: list[dict]) -> list[dict]:
    projection_by_event = {str(row["event_id"]): row for row in run.base_run.projection_audit}
    birth_by_event = {str(row.event_id): row for row in run.base_run.tuple_births}
    closes = np.asarray([float(row["close"]) for row in bars], dtype=float)
    groups = []
    for group in tuple_groups:
        members = []
        for event_id in group["member_event_ids"]:
            event_id = str(event_id)
            birth = birth_by_event[event_id]
            projection = projection_by_event[event_id]
            members.append(
                {
                    "event_id": event_id,
                    "birth_level": int(birth.level),
                    "birth_confirmation_bar": int(birth.confirmation_index),
                    "projection_valid": bool(projection.get("projection_valid")),
                    "projection_reason": projection.get("projection_reason"),
                    "raw_occurrence_bars": (
                        [int(x) for x in projection["raw_occurrence_bars"]]
                        if projection.get("raw_occurrence_bars") is not None
                        else None
                    ),
                }
            )
        projection_summary = summarize_projection_group(members)
        representative = earliest_valid_member(members)
        representative_audit = None
        if representative is not None:
            birth = birth_by_event[str(representative["event_id"])]
            representative_audit = audit_projection_event(_projection_adapter(birth), bars, closes)
        raw_identity_times = []
        for raw in projection_summary["valid_raw_identities"]:
            raw_identity_times.append(attach_times(raw, bars))
        groups.append(
            {
                **group,
                "projection_summary": projection_summary,
                "projection_members": members,
                "valid_raw_identity_times": raw_identity_times,
                "representative_event_id": (
                    str(representative["event_id"]) if representative is not None else None
                ),
                "representative_audit": representative_audit,
            }
        )
    return groups


def build_view(view: str) -> dict:
    bars, data_audit = load_development_bars(
        ROOT / f"data/development/{view}.parquet",
        ROOT / "data/manifest.json",
    )
    run = build_cycle_scale_qualification_run(bars, cfg=MaturityConfig(timeframe=view))
    qualified = [row for row in run.ledger.records if bool(row.get("scale_qualified"))]
    canonical = canonicalize_qualified_records(qualified)
    for row in canonical:
        row["five_occurrence_times"] = attach_times(row["five_occurrence_bars"], bars)
    causal = causal_publish_qualified_identities(qualified)
    causal_by_id = {row["canonical_identity_id"]: row for row in causal["identity_events"]}
    evaluated = canonicalize_evaluated_records(run.evaluated_records, bars)
    tuples = canonicalize_tuple_births(run.base_run.tuple_births, bars)
    projection_groups = build_projection_groups(run, tuples, bars)
    return {
        "view": view,
        "bars": bars,
        "data_audit": data_audit,
        "run": run,
        "qualified": qualified,
        "canonical": canonical,
        "causal_by_id": causal_by_id,
        "record_by_id": {str(row["record_id"]): row for row in run.evaluated_records},
        "evaluated": evaluated,
        "evaluated_index": {
            event_key(row, "five_occurrence_bars"): i for i, row in enumerate(evaluated)
        },
        "tuples": projection_groups,
        "tuple_index": {
            event_key(row, "five_filtered_occurrence_bars"): i
            for i, row in enumerate(projection_groups)
        },
    }


def per_view_summary(view: dict) -> dict:
    statuses = Counter(row["projection_summary"]["status"] for row in view["tuples"])
    invalid = Counter()
    changed_ordinal = Counter()
    multi_changed_patterns = Counter()
    tail_all = []
    tail_multi = []
    for group in view["tuples"]:
        ps = group["projection_summary"]
        invalid.update(ps["projection_invalid_reasons"])
        if ps["status"] == "multi_valued_projection":
            pattern = tuple(int(x) for x in ps["changed_raw_ordinals"])
            multi_changed_patterns[str(pattern)] += 1
            for ordinal in pattern:
                changed_ordinal[int(ordinal)] += 1
        member_by_id = {row["event_id"]: row for row in group["projection_members"]}
        birth_by_event = {str(row.event_id): row for row in view["run"].base_run.tuple_births}
        for event_id in member_by_id:
            birth = birth_by_event[event_id]
            extension = int(birth.confirmation_index - birth.occurrence_indices[4])
            tail_all.append(extension)
            if ps["status"] == "multi_valued_projection":
                tail_multi.append(extension)
    return {
        "view": view["view"],
        "canonical_filtered_tuple_groups": len(view["tuples"]),
        "projection_group_status": dict(sorted(statuses.items())),
        "projection_invalid_reasons": dict(sorted(invalid.items())),
        "multi_projection_changed_ordinal_counts": {
            str(k): v for k, v in sorted(changed_ordinal.items())
        },
        "multi_projection_changed_patterns": dict(sorted(multi_changed_patterns.items())),
        "ordinal4_tail_extension_bars_all_members": summarize_numeric(tail_all),
        "ordinal4_tail_extension_bars_multi_projection_members": summarize_numeric(tail_multi),
    }


def identity_context(main: dict, main_event: dict) -> tuple[dict, int]:
    causal = main["causal_by_id"][main_event["canonical_identity_id"]]
    first_id = str(causal["first_record_id"])
    record = main["record_by_id"][first_id]
    key = (str(record["phase"]), tuple(int(x) for x in record["filtered_occurrence_bars"]))
    idx = main["tuple_index"].get(key)
    if idx is None:
        raise AssertionError("causal evaluated record has no canonical filtered tuple")
    return record, idx


def post_tuple_targets(main: dict, other: dict) -> list[dict]:
    q0 = mutual_unique_strict_matches(main["canonical"], other["canonical"], NOMINAL_BAR_MINUTES)
    expected = EXPECTED_V060[other["view"]]
    actual = (
        len(q0.matches), len(q0.ambiguous_a), len(q0.ambiguous_b),
        len(q0.unmatched_a), len(q0.unmatched_b),
    )
    if actual != expected:
        raise AssertionError(f"v0.6.0 control drift {other['view']}: {actual} != {expected}")

    q_graph = build_edge_graph(
        main["canonical"], other["canonical"],
        time_field="five_occurrence_times", require_phase=True,
    )
    eval_same = build_edge_graph(
        main["evaluated"], other["evaluated"],
        time_field="five_occurrence_times", require_phase=True,
    )
    eval_ignore = build_edge_graph(
        main["evaluated"], other["evaluated"],
        time_field="five_occurrence_times", require_phase=False,
    )
    tuple_same = build_edge_graph(
        main["tuples"], other["tuples"],
        time_field="five_filtered_occurrence_times", require_phase=True,
    )
    tuple_ignore = build_edge_graph(
        main["tuples"], other["tuples"],
        time_field="five_filtered_occurrence_times", require_phase=False,
    )

    out = []
    for i in q0.unmatched_a:
        main_event = main["canonical"][i]
        if q_graph.a_edges[i]:
            continue
        main_eval_idx = main["evaluated_index"][event_key(main_event, "five_occurrence_bars")]
        partner_ignore = eval_ignore.mutual_partner_a(main_eval_idx)
        if partner_ignore is not None and other["evaluated"][partner_ignore]["phase"] != main_event["phase"]:
            continue
        partner_same = eval_same.mutual_partner_a(main_eval_idx)
        if partner_same is not None:
            if bool(other["evaluated"][partner_same]["qualified_any"]):
                raise AssertionError("qualified raw counterpart missing from qualified graph")
            continue
        if eval_same.a_edges[main_eval_idx] or eval_ignore.a_edges[main_eval_idx]:
            continue

        record, main_tuple_idx = identity_context(main, main_event)
        tuple_ignore_partner = tuple_ignore.mutual_partner_a(main_tuple_idx)
        if (
            tuple_ignore_partner is not None
            and other["tuples"][tuple_ignore_partner]["phase"] != record["phase"]
        ):
            continue
        tuple_partner = tuple_same.mutual_partner_a(main_tuple_idx)
        if tuple_partner is None:
            continue
        main_raw_times = attach_times(record["five_occurrence_bars"], main["bars"])
        other_group = other["tuples"][tuple_partner]
        valid_other = [
            row for row in other_group["projection_members"]
            if row["projection_valid"] and row.get("raw_occurrence_bars") is not None
        ]
        displaced = False
        for row in valid_other:
            other_times = attach_times(row["raw_occurrence_bars"], other["bars"])
            if not strict_time_tuple_match(record["phase"], main_raw_times, other_group["phase"], other_times):
                displaced = True
        out.append(
            {
                "canonical_identity_id": main_event["canonical_identity_id"],
                "main_tuple_index": main_tuple_idx,
                "other_tuple_index": tuple_partner,
                "main_raw_times": main_raw_times,
                "projection_displacement_case": displaced,
                "other_projection_valid_count": len(valid_other),
            }
        )
    return out


def pair_audit(main: dict, other: dict, one_min_index: CanonicalPathIndex) -> tuple[dict, dict]:
    tuple_graph = build_edge_graph(
        main["tuples"], other["tuples"],
        time_field="five_filtered_occurrence_times", require_phase=True,
    )
    status = Counter()
    first_displaced = Counter()
    displaced_ordinal = Counter()
    suffix_count = 0
    tie_count = 0
    one_min = Counter()
    cross_membership = defaultdict(Counter)
    e4_tail_main = []
    e4_tail_other = []
    raw_displaced_pair_count = 0

    for i, j in tuple_graph.mutual_unique_matches:
        a = main["tuples"][i]
        b = other["tuples"][j]
        sa = a["projection_summary"]
        sb = b["projection_summary"]
        if sa["status"] == "no_valid_projection" or sb["status"] == "no_valid_projection":
            status["projection_invalid_group"] += 1
            continue
        if sa["status"] == "multi_valued_projection" or sb["status"] == "multi_valued_projection":
            status["within_view_multi_projection"] += 1
            continue
        times_a = a["valid_raw_identity_times"][0]
        times_b = b["valid_raw_identity_times"][0]
        disp = raw_pair_displacement(times_a, times_b)
        if disp["strict_match"]:
            status["raw_projection_strict_match"] += 1
            continue
        status["raw_projection_displaced"] += 1
        raw_displaced_pair_count += 1
        first_displaced[str(disp["first_displaced_ordinal"])] += 1
        for ordinal in disp["displaced_ordinals"]:
            displaced_ordinal[str(ordinal)] += 1
        suffix_count += int(disp["displaced_is_suffix"])

        audit_a = a["representative_audit"]
        audit_b = b["representative_audit"]
        if not audit_a or not audit_b or not audit_a["valid"] or not audit_b["valid"]:
            raise AssertionError("single-valued valid group must have valid causal representative")
        paired = paired_window_diagnostics(audit_a["windows"], audit_b["windows"])
        tie_count += int(paired["any_exact_tie"])
        for row in paired["rows"]:
            ordinal = str(row["ordinal"])
            cross_membership[ordinal]["a_inside_b"] += int(row["a_selected_inside_b_window"])
            cross_membership[ordinal]["b_inside_a"] += int(row["b_selected_inside_a_window"])
            cross_membership[ordinal]["both_inside"] += int(
                row["a_selected_inside_b_window"] and row["b_selected_inside_a_window"]
            )
            cross_membership[ordinal]["total"] += 1

        one_a = one_minute_projection_from_windows(audit_a["windows"], one_min_index)
        one_b = one_minute_projection_from_windows(audit_b["windows"], one_min_index)
        if not one_a["available"] or not one_b["available"]:
            one_min["one_minute_unavailable"] += 1
        elif strict_time_tuple_match(a["phase"], one_a["times"], b["phase"], one_b["times"]):
            one_min["one_minute_strict_match"] += 1
        else:
            one_min["one_minute_displaced"] += 1

        e4_tail_main.append(audit_a["windows"][4]["tail_extension_from_filtered_e4_minutes"])
        e4_tail_other.append(audit_b["windows"][4]["tail_extension_from_filtered_e4_minutes"])

    targets = post_tuple_targets(main, other)
    if len(targets) != EXPECTED_POST_TUPLE[other["view"]]:
        raise AssertionError(
            f"v0.6.1 post-tuple target drift {other['view']}: {len(targets)} != {EXPECTED_POST_TUPLE[other['view']]}"
        )
    displaced_targets = sum(bool(row["projection_displacement_case"]) for row in targets)
    if displaced_targets != EXPECTED_POST_TUPLE_DISPLACED[other["view"]]:
        raise AssertionError(
            f"v0.6.1 displacement control drift {other['view']}: {displaced_targets} != {EXPECTED_POST_TUPLE_DISPLACED[other['view']]}"
        )

    pair_summary = {
        "main_view": main["view"],
        "other_view": other["view"],
        "mutual_unique_filtered_tuple_pairs": len(tuple_graph.mutual_unique_matches),
        "ambiguous_main_filtered_tuple": sum(len(x) > 1 for x in tuple_graph.a_edges),
        "ambiguous_other_filtered_tuple": sum(len(x) > 1 for x in tuple_graph.b_edges),
        "projection_pair_status": dict(sorted(status.items())),
        "raw_displaced_first_ordinal": dict(sorted(first_displaced.items())),
        "raw_displaced_ordinal_counts": dict(sorted(displaced_ordinal.items())),
        "raw_displaced_suffix_count": suffix_count,
        "raw_displaced_suffix_fraction": suffix_count / raw_displaced_pair_count if raw_displaced_pair_count else None,
        "raw_displaced_any_exact_tie_count": tie_count,
        "raw_displaced_any_exact_tie_fraction": tie_count / raw_displaced_pair_count if raw_displaced_pair_count else None,
        "raw_displaced_cross_window_membership": {
            key: dict(sorted(value.items())) for key, value in sorted(cross_membership.items())
        },
        "raw_displaced_one_minute_diagnostic": dict(sorted(one_min.items())),
        "raw_displaced_representative_e4_tail_minutes_main": summarize_numeric(e4_tail_main),
        "raw_displaced_representative_e4_tail_minutes_other": summarize_numeric(e4_tail_other),
        "v061_post_tuple_target_count": len(targets),
        "v061_post_tuple_projection_displacement_count": displaced_targets,
    }
    target_summary = {
        "other_view": other["view"],
        "target_count": len(targets),
        "projection_displacement_count": displaced_targets,
        "other_projection_valid_count_distribution": dict(
            sorted(Counter(int(row["other_projection_valid_count"]) for row in targets).items())
        ),
    }
    return pair_summary, target_summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--output",
        type=Path,
        default=ROOT / "cloud_results/cloud_chat_v062_raw_projection_identity_audit",
    )
    args = ap.parse_args()

    one_min_bars, one_min_audit = load_development_bars(
        ROOT / "data/development/1m_official.parquet",
        ROOT / "data/manifest.json",
    )
    one_min_index = CanonicalPathIndex.from_bars(one_min_bars)

    main_view = build_view("5m_offset_0")
    if len(main_view["qualified"]) != EXPECTED_QUALIFIED["5m_offset_0"]:
        raise AssertionError("IDENTITY_INPUT_DRIFT main qualified")
    if len(main_view["canonical"]) != EXPECTED_CANONICAL["5m_offset_0"]:
        raise AssertionError("IDENTITY_INPUT_DRIFT main canonical")

    per_view = {"5m_offset_0": per_view_summary(main_view)}
    pair_summaries = {}
    target_summaries = {}
    data_audits = {"5m_offset_0": main_view["data_audit"]}

    for view in VIEWS[1:]:
        other = build_view(view)
        if len(other["qualified"]) != EXPECTED_QUALIFIED[view]:
            raise AssertionError(f"IDENTITY_INPUT_DRIFT {view} qualified")
        if len(other["canonical"]) != EXPECTED_CANONICAL[view]:
            raise AssertionError(f"IDENTITY_INPUT_DRIFT {view} canonical")
        per_view[view] = per_view_summary(other)
        pair_summary, target_summary = pair_audit(main_view, other, one_min_index)
        pair_summaries[view] = pair_summary
        target_summaries[view] = target_summary
        data_audits[view] = other["data_audit"]
        save(args.output / f"pair_offset_{view[-1]}.json", pair_summary)
        del other
        gc.collect()

    save(args.output / "per_view_single_valuedness.json", per_view)
    save(args.output / "v061_target_diagnostics.json", target_summaries)

    data_identity = {
        "schema": "two_wave_v062_data_identity@1.0",
        "instrument": "000852.SH",
        "fresh_oos": False,
        "local_resampling_performed": False,
        "post_2020_rows_included": False,
        "views": [],
    }
    for view in VIEWS:
        path = ROOT / f"data/development/{view}.parquet"
        audit = data_audits[view]
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
    one_min_path = ROOT / "data/development/1m_official.parquet"
    data_identity["one_minute_audit_only"] = {
        "path": str(one_min_path.relative_to(ROOT)),
        "sha256": file_sha256(one_min_path),
        "rows": int(one_min_audit["rows"]),
        "minimum_trading_day": one_min_audit["minimum_trading_day"],
        "maximum_trading_day": one_min_audit["maximum_trading_day"],
        "manifest_verified": bool(one_min_audit.get("manifest_verified")),
        "recognizer_input": False,
    }
    save(args.output / "data_identity.json", data_identity)

    result = {
        "schema": "two_wave_raw_projection_identity_audit@0.6.2",
        "status": "raw_projection_identity_audit_generated_pending_cloud_adjudication",
        "frozen_projection": "sequential_raw_close_extreme_inside_filtered_phase_bounds",
        "nominal_bar_minutes": NOMINAL_BAR_MINUTES,
        "qualified_counts": EXPECTED_QUALIFIED,
        "canonical_qualified_counts": EXPECTED_CANONICAL,
        "per_view": per_view,
        "pair_audits": pair_summaries,
        "v061_target_controls": target_summaries,
        "one_minute_role": "audit_only_no_resampling_no_recognizer_authority",
        "future_outcome_used": False,
        "trade_authority": False,
        "operational_baseline": "v0.4.3",
        "morphology_status": "morphology_replication_not_yet_accepted",
    }
    save(args.output / "summary.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
