#!/usr/bin/env python3
"""v0.6.3 audit: decompose canonical-1m residual phase-window instability."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gc
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.phase_window_residual_v063 import (
    classify_residual_pair,
    intersection_diagnostic,
    sequential_overlay,
    session_gap_overlay,
)
from factor_lab.visual_structure.two_wave.raw_projection_identity_v062 import (
    CanonicalPathIndex,
    one_minute_projection_from_windows,
    raw_pair_displacement,
    strict_time_tuple_match,
)
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import build_edge_graph
from run_two_wave_raw_projection_identity_audit_v062 import build_view, post_tuple_targets

VIEWS = [f"5m_offset_{i}" for i in range(5)]
EXPECTED_RESIDUAL = {
    "5m_offset_1": 1578,
    "5m_offset_2": 1738,
    "5m_offset_3": 1806,
    "5m_offset_4": 1718,
}
EXPECTED_TARGET_RESIDUAL = {
    "5m_offset_1": 32,
    "5m_offset_2": 28,
    "5m_offset_3": 30,
    "5m_offset_4": 32,
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


def one_min_index() -> tuple[CanonicalPathIndex, dict]:
    bars, audit = load_development_bars(
        ROOT / "data/development/1m_official.parquet",
        ROOT / "data/manifest.json",
    )
    return CanonicalPathIndex.from_bars(bars), audit


def _fraction(count: int, total: int):
    return count / total if total else None


def audit_pair(main: dict, other: dict, one_min: CanonicalPathIndex) -> tuple[dict, dict]:
    graph = build_edge_graph(
        main["tuples"], other["tuples"],
        time_field="five_filtered_occurrence_times", require_phase=True,
    )
    target_rows = post_tuple_targets(main, other)
    target_pairs = {
        (int(row["main_tuple_index"]), int(row["other_tuple_index"]))
        for row in target_rows if bool(row["projection_displacement_case"])
    }

    primary = Counter()
    first = Counter()
    lower_by_ordinal = Counter()
    upper_by_ordinal = Counter()
    exact_tie = 0
    lunch = overnight = nearby = 0
    seq_prior = seq_suffix = 0
    intersection_available = intersection_both = intersection_rows = 0

    target_primary = Counter()
    target_first = Counter()
    target_ties = target_lunch = target_overnight = target_nearby = 0
    target_seq_prior = target_seq_suffix = 0
    target_intersection_available = target_intersection_both = target_intersection_rows = 0

    residual = 0
    target_residual = 0

    for i, j in graph.mutual_unique_matches:
        a, b = main["tuples"][i], other["tuples"][j]
        sa, sb = a["projection_summary"], b["projection_summary"]
        if sa["status"] != "single_valued_projection" or sb["status"] != "single_valued_projection":
            continue
        if strict_time_tuple_match(
            a["phase"], a["valid_raw_identity_times"][0],
            b["phase"], b["valid_raw_identity_times"][0],
        ):
            continue
        aa, bb = a["representative_audit"], b["representative_audit"]
        if aa is None or bb is None or not aa.get("valid") or not bb.get("valid"):
            continue
        one_a = one_minute_projection_from_windows(aa["windows"], one_min)
        one_b = one_minute_projection_from_windows(bb["windows"], one_min)
        if not one_a["available"] or not one_b["available"]:
            continue
        if strict_time_tuple_match(a["phase"], one_a["times"], b["phase"], one_b["times"]):
            continue

        residual += 1
        out = classify_residual_pair(aa["windows"], bb["windows"], one_a, one_b)
        k = int(out["first_displaced_ordinal"])
        primary[out["primary_attribution"]] += 1
        first[str(k)] += 1
        lower_by_ordinal[str(k)] += int(out["lower_exclusion_present"])
        upper_by_ordinal[str(k)] += int(out["upper_exclusion_present"])
        exact_tie += int(out["a_tie_count"] > 1 or out["b_tie_count"] > 1)

        gap = session_gap_overlay(aa["windows"], bb["windows"], k)
        lunch += int(gap["lunch_gap_straddled"])
        overnight += int(gap["overnight_gap_straddled"])
        nearby += int(gap["session_boundary_nearby"])
        seq = sequential_overlay(aa["windows"], bb["windows"], one_a, one_b, k)
        seq_prior += int(seq["prior_5m_selected_time_differs"])
        seq_suffix += int(seq["residual_displaced_is_suffix"])

        disp = raw_pair_displacement(one_a["times"], one_b["times"])
        pair_intersection_available = pair_intersection_both = pair_intersection_n = 0
        for ordinal in disp["displaced_ordinals"]:
            inter = intersection_diagnostic(
                aa["windows"][ordinal], bb["windows"][ordinal], one_min,
                one_a["times"][ordinal], one_b["times"][ordinal],
            )
            intersection_rows += 1
            pair_intersection_n += 1
            if inter["available"]:
                intersection_available += 1
                pair_intersection_available += 1
                intersection_both += int(inter["within_one_bar_of_both"])
                pair_intersection_both += int(inter["within_one_bar_of_both"])

        is_target = (i, j) in target_pairs
        if is_target:
            target_residual += 1
            target_primary[out["primary_attribution"]] += 1
            target_first[str(k)] += 1
            target_ties += int(out["a_tie_count"] > 1 or out["b_tie_count"] > 1)
            target_lunch += int(gap["lunch_gap_straddled"])
            target_overnight += int(gap["overnight_gap_straddled"])
            target_nearby += int(gap["session_boundary_nearby"])
            target_seq_prior += int(seq["prior_5m_selected_time_differs"])
            target_seq_suffix += int(seq["residual_displaced_is_suffix"])
            target_intersection_rows += pair_intersection_n
            target_intersection_available += pair_intersection_available
            target_intersection_both += pair_intersection_both

    if residual != EXPECTED_RESIDUAL[other["view"]]:
        raise AssertionError(
            f"v0.6.2 residual control drift {other['view']}: {residual} != {EXPECTED_RESIDUAL[other['view']]}"
        )
    if target_residual != EXPECTED_TARGET_RESIDUAL[other["view"]]:
        raise AssertionError(
            f"v0.6.1 target residual drift {other['view']}: {target_residual} != {EXPECTED_TARGET_RESIDUAL[other['view']]}"
        )

    summary = {
        "main_view": main["view"],
        "other_view": other["view"],
        "residual_count": residual,
        "primary_attribution": dict(sorted(primary.items())),
        "primary_attribution_fraction": {k: _fraction(v, residual) for k, v in sorted(primary.items())},
        "first_one_minute_displaced_ordinal": dict(sorted(first.items())),
        "lower_exclusion_at_first_by_ordinal": dict(sorted(lower_by_ordinal.items())),
        "upper_exclusion_at_first_by_ordinal": dict(sorted(upper_by_ordinal.items())),
        "one_minute_exact_tie_at_first": {"count": exact_tie, "fraction": _fraction(exact_tie, residual)},
        "session_gap_overlay": {
            "lunch_gap_straddled": lunch,
            "overnight_gap_straddled": overnight,
            "session_boundary_nearby": nearby,
        },
        "sequential_overlay": {
            "prior_5m_selected_time_differs": seq_prior,
            "residual_displaced_is_suffix": seq_suffix,
        },
        "intersection_diagnostic": {
            "displaced_ordinal_rows": intersection_rows,
            "available": intersection_available,
            "within_one_bar_of_both": intersection_both,
            "available_fraction": _fraction(intersection_available, intersection_rows),
            "within_one_bar_of_both_fraction": _fraction(intersection_both, intersection_rows),
        },
    }
    target = {
        "other_view": other["view"],
        "target_residual_count": target_residual,
        "primary_attribution": dict(sorted(target_primary.items())),
        "primary_attribution_fraction": {
            k: _fraction(v, target_residual) for k, v in sorted(target_primary.items())
        },
        "first_one_minute_displaced_ordinal": dict(sorted(target_first.items())),
        "one_minute_exact_tie_at_first": target_ties,
        "session_gap_overlay": {
            "lunch_gap_straddled": target_lunch,
            "overnight_gap_straddled": target_overnight,
            "session_boundary_nearby": target_nearby,
        },
        "sequential_overlay": {
            "prior_5m_selected_time_differs": target_seq_prior,
            "residual_displaced_is_suffix": target_seq_suffix,
        },
        "intersection_diagnostic": {
            "displaced_ordinal_rows": target_intersection_rows,
            "available": target_intersection_available,
            "within_one_bar_of_both": target_intersection_both,
        },
    }
    return summary, target


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--output", type=Path,
        default=ROOT / "cloud_results/cloud_chat_v063_phase_window_residual_audit",
    )
    args = ap.parse_args()

    one_min, one_min_audit = one_min_index()
    main_view = build_view("5m_offset_0")
    pair_rows = {}
    target_rows = {}
    for view in VIEWS[1:]:
        other = build_view(view)
        pair_rows[view], target_rows[view] = audit_pair(main_view, other, one_min)
        save(args.output / f"pair_offset_{view[-1]}.json", pair_rows[view])
        del other
        gc.collect()

    aggregate_primary = Counter()
    aggregate_first = Counter()
    aggregate_residual = 0
    for row in pair_rows.values():
        aggregate_residual += int(row["residual_count"])
        aggregate_primary.update(row["primary_attribution"])
        aggregate_first.update(row["first_one_minute_displaced_ordinal"])
    if aggregate_residual != 6840:
        raise AssertionError(f"aggregate residual drift: {aggregate_residual} != 6840")

    aggregate_target = Counter()
    aggregate_target_n = 0
    for row in target_rows.values():
        aggregate_target_n += int(row["target_residual_count"])
        aggregate_target.update(row["primary_attribution"])
    if aggregate_target_n != 122:
        raise AssertionError(f"aggregate target residual drift: {aggregate_target_n} != 122")

    data_identity = {
        "schema": "two_wave_v063_data_identity@1.0",
        "one_minute": {
            "path": "data/development/1m_official.parquet",
            "sha256": file_sha256(ROOT / "data/development/1m_official.parquet"),
            "rows": int(one_min_audit["rows"]),
            "minimum_trading_day": one_min_audit["minimum_trading_day"],
            "maximum_trading_day": one_min_audit["maximum_trading_day"],
            "manifest_verified": bool(one_min_audit.get("manifest_verified")),
        },
        "fresh_oos": False,
        "local_resampling_performed": False,
        "post_2020_rows_included": False,
    }
    save(args.output / "data_identity.json", data_identity)
    save(args.output / "v061_target_residual_summary.json", target_rows)

    result = {
        "schema": "two_wave_phase_window_residual_audit@0.6.3",
        "status": "phase_window_residual_audit_generated_pending_cloud_adjudication",
        "residual_counts": {view: row["residual_count"] for view, row in pair_rows.items()},
        "aggregate_residual_count": aggregate_residual,
        "aggregate_primary_attribution": dict(sorted(aggregate_primary.items())),
        "aggregate_primary_attribution_fraction": {
            k: v / aggregate_residual for k, v in sorted(aggregate_primary.items())
        },
        "aggregate_first_one_minute_displaced_ordinal": dict(sorted(aggregate_first.items())),
        "target_residual_counts": {
            view: row["target_residual_count"] for view, row in target_rows.items()
        },
        "aggregate_target_residual_count": aggregate_target_n,
        "aggregate_target_primary_attribution": dict(sorted(aggregate_target.items())),
        "pair_audits": pair_rows,
        "future_outcome_used": False,
        "trade_authority": False,
        "operational_baseline": "v0.4.3",
        "morphology_status": "morphology_replication_not_yet_accepted",
    }
    save(args.output / "summary.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
