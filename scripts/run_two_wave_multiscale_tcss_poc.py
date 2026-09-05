#!/usr/bin/env python3
"""Execute the frozen v0.5 TCSS representation POC; no D1, P&L or trading."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.multiscale_v050 import (
    build_scale_levels,
    confirmed_extrema,
    default_scale_sigmas,
    time_causal_scale_space,
    two_wave_candidates,
)
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig, TemporalMaturityEngine

VIEWS = [f"5m_offset_{i}" for i in range(5)] + ["1m_official"]
FIXED_DAYS = ["2018-06-20", "2019-04-15", "2020-07-15"]
FOCUS_CASES = {
    "case_00_A_clear_C_uncertain",
    "case_02_C_new_downtrend",
    "case_10_stable_range",
    "case_11_stable_range",
    "case_14_stable_uptrend",
}
PREFIX_FRACTIONS = (0.25, 0.50, 0.75)


def save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def quantiles(values) -> dict[str, float] | None:
    a = np.asarray(list(values), dtype=float)
    if not len(a):
        return None
    return {str(q): float(np.quantile(a, q)) for q in (0, 0.5, 0.9, 0.99, 1)}


def run_v043(bars, view):
    engine = TemporalMaturityEngine(MaturityConfig(timeframe=view))
    for bar in bars:
        engine.update(bar)
    return engine


def kernel_mean_delay(levels) -> dict[str, float]:
    """Mean age of each cumulative causal kernel; descriptive, never left-shifted."""
    cumulative = 0.0
    out = {}
    for level in levels:
        if level.pole:
            cumulative += level.pole / (1.0 - level.pole)
        out[level.scale_id] = cumulative
    return out


def event_tuple(event):
    return (
        event.scale_id,
        event.kind,
        event.occurrence_index,
        event.confirmation_index,
        event.value,
    )


def candidate_tuple(candidate):
    return (
        candidate.scale_id,
        candidate.occurrence_indices,
        candidate.confirmation_index,
        candidate.cycle_durations,
    )


def interval_iou(a0, a1, b0, b1):
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = (a1 - a0) + (b1 - b0) - inter
    return inter / union if union else 1.0


def local_overlay(candidates, local_pivots):
    bars = np.asarray(
        [p["occurrence_bar"] for p in local_pivots if not p.get("left_censored", False)],
        dtype=int,
    )
    counts = []
    excess = []
    for candidate in candidates:
        lo, hi = candidate.occurrence_indices[0], candidate.occurrence_indices[-1]
        count = int(np.sum((bars >= lo) & (bars <= hi)))
        counts.append(count)
        excess.append(max(0, count - 5))
    return {
        "v043_local_pivots_inside_candidate_quantiles": quantiles(counts),
        "v043_excess_local_pivots_beyond_five_quantiles": quantiles(excess),
        "candidates_with_at_least_one_excess_v043_local_pivot": int(sum(v > 0 for v in excess)),
    }


def summarize_scale(scale_id, series, local_pivots, mean_delay):
    extrema = confirmed_extrema(series, scale_id)
    candidates = two_wave_candidates(extrema)
    durations = [d for c in candidates for d in c.cycle_durations]
    pair_spans = [c.occurrence_indices[-1] - c.occurrence_indices[0] for c in candidates]
    target = [
        c for c in candidates
        if all(12 <= d <= 48 for d in c.cycle_durations)
        and c.occurrence_indices[-1] - c.occurrence_indices[0] <= 96
    ]
    return {
        "scale_id": scale_id,
        "extrema": len(extrema),
        "two_wave_candidates_overlapping_audit_layer": len(candidates),
        "cycle_duration_bars_quantiles": quantiles(durations),
        "pair_span_bars_quantiles": quantiles(pair_spans),
        "target_12_48_duration_diagnostic_only_count": len(target),
        "mean_causal_kernel_age_bars_not_time_shifted": float(mean_delay),
        "last_confirmed_extremum_confirmation_bar": extrema[-1].confirmation_index if extrema else None,
        "raw_reversal_semantics": True,
        **local_overlay(candidates, local_pivots),
    }, extrema, candidates


def fixed_day_bar_ranges(bars):
    by_day = {}
    for i, bar in enumerate(bars):
        day = str(bar.get("trading_day"))
        by_day.setdefault(day, [i, i])
        by_day[day][1] = i
    return {day: by_day.get(day) for day in FIXED_DAYS}


def compact_candidate(candidate, legacy_interval=None):
    row = {
        "scale_id": candidate.scale_id,
        "occurrence_indices": list(candidate.occurrence_indices),
        "confirmation_index": candidate.confirmation_index,
        "cycle_durations": list(candidate.cycle_durations),
    }
    if legacy_interval is not None:
        row["legacy_interval_iou_not_model_selection"] = interval_iou(
            legacy_interval[0], legacy_interval[1],
            candidate.occurrence_indices[0], candidate.occurrence_indices[-1],
        )
    return row


def audit_ranges(candidates_by_scale, ranges):
    out = {}
    for label, interval in ranges.items():
        if interval is None:
            out[label] = {"present": False}
            continue
        lo, hi = interval
        per_scale = {}
        for scale_id, candidates in candidates_by_scale.items():
            overlapping = [
                c for c in candidates
                if c.occurrence_indices[-1] >= lo and c.occurrence_indices[0] <= hi
            ]
            ranked = sorted(
                overlapping,
                key=lambda c: interval_iou(lo, hi, c.occurrence_indices[0], c.occurrence_indices[-1]),
                reverse=True,
            )
            per_scale[scale_id] = {
                "overlap_candidate_count": len(overlapping),
                "top_interval_overlaps_not_model_selection": [
                    compact_candidate(c, (lo, hi)) for c in ranked[:3]
                ],
            }
        out[label] = {"present": True, "bar_range": [lo, hi], "all_scales": per_scale}
    return out


def legacy_ranges(path):
    if not path.exists():
        return {}, {"present": False}
    cases = json.loads(path.read_text())
    ranges = {}
    raw = []
    for case in cases:
        if case["case"] in FOCUS_CASES:
            pivots = case["five_occurrence_bars"]
            ranges[case["case"]] = [int(pivots[0]), int(pivots[-1])]
            raw.append({
                "case": case["case"],
                "five_occurrence_bars": list(map(int, pivots)),
                "cycle_bars": case.get("cycle_bars"),
                "leg_bars": case.get("leg_bars"),
            })
    return ranges, {"present": True, "source": str(path.relative_to(ROOT)), "cases": raw}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "cloud_results/two_wave_multiscale_tcss_v050")
    parser.add_argument("--views", nargs="+", default=VIEWS)
    args = parser.parse_args()

    sigmas = default_scale_sigmas()
    levels = build_scale_levels(sigmas)
    delays = kernel_mean_delay(levels)
    sources = [
        Path(__file__),
        ROOT / "src/factor_lab/visual_structure/two_wave/multiscale_v050.py",
        ROOT / "tests/unit/test_two_wave_multiscale_v050.py",
        ROOT / "docs/research/two_wave_multiscale_pre_research_v050.md",
        ROOT / "docs/research/two_wave_multiscale_poc_protocol_v050.md",
    ]
    summary = {
        "schema": "two_wave_multiscale_tcss_poc@0.5.0-prestudy",
        "status": "representation_poc_not_a_new_baseline",
        "operational_baseline": "v0.4.3",
        "changed_component_only": "causal_multiscale_representation_and_parent_candidate_audit",
        "qualification_changed": False,
        "d1_changed": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "fresh_oos": False,
        "raw_reversal_semantics": True,
        "scale_selection_performed": False,
        "old_12_48_used_for_scale_selection_or_closure": False,
        "old_12_48_role": "diagnostic_only",
        "scale_sigmas_kernel_std_bars": list(sigmas),
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "source_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources
        },
        "views": {},
        "prefix_checks": [],
    }

    main_candidates = None
    main_bars = None
    for view in args.views:
        bars, audit = load_development_bars(
            ROOT / f"data/development/{view}.parquet",
            ROOT / "data/manifest.json",
        )
        raw = np.log(np.asarray([b["close"] for b in bars], dtype=float))
        baseline = run_v043(bars, view)
        if view == "5m_offset_0":
            base_tuple = (
                len(baseline.ledger.records),
                sum(r["scale_qualified"] for r in baseline.ledger.records),
                len(baseline.ledger.selected),
            )
            assert base_tuple == (4706, 341, 212), base_tuple

        space = time_causal_scale_space(raw, sigmas)
        extrema_counts = []
        scales = {}
        candidates_by_scale = {}
        extrema_by_scale = {}
        for scale_id, series in space.items():
            row, extrema, candidates = summarize_scale(scale_id, series, baseline.pivots, delays[scale_id])
            scales[scale_id] = row
            extrema_by_scale[scale_id] = extrema
            candidates_by_scale[scale_id] = candidates
            extrema_counts.append(len(extrema))

        # Core real-data hierarchy gate: every cumulative scale must not create
        # additional extrema.  This is representation evidence, not accuracy.
        nonincreasing = all(a >= b for a, b in zip(extrema_counts, extrema_counts[1:]))
        assert nonincreasing, (view, extrema_counts)

        for fraction in PREFIX_FRACTIONS:
            n = int(len(raw) * fraction)
            prefix_space = time_causal_scale_space(raw[:n], sigmas)
            checked = 0
            for scale_id, prefix_series in prefix_space.items():
                np.testing.assert_array_equal(prefix_series, space[scale_id][:n])
                prefix_events = confirmed_extrema(prefix_series, scale_id)
                full_events = [e for e in extrema_by_scale[scale_id] if e.confirmation_index < n]
                assert [event_tuple(e) for e in prefix_events] == [event_tuple(e) for e in full_events]
                prefix_pairs = two_wave_candidates(prefix_events)
                full_pairs = [c for c in candidates_by_scale[scale_id] if c.confirmation_index < n]
                assert [candidate_tuple(c) for c in prefix_pairs] == [candidate_tuple(c) for c in full_pairs]
                checked += 1
            summary["prefix_checks"].append({
                "view": view,
                "fraction": fraction,
                "bars": n,
                "scales_checked": checked,
                "confirmed_rewrite_count": 0,
                "passed": True,
            })

        summary["views"][view] = {
            "data_audit": audit,
            "v043_audit_overlay": {
                "local_pivots": len(baseline.pivots),
                "candidates": len(baseline.ledger.records),
                "qualified": sum(r["scale_qualified"] for r in baseline.ledger.records),
                "selected_disjoint": len(baseline.ledger.selected),
            },
            "tcss": {
                "all_scales": scales,
                "extrema_counts_fine_to_coarse": extrema_counts,
                "extrema_count_nonincreasing_across_scale": nonincreasing,
                "coarsest_to_finest_extrema_ratio": extrema_counts[-1] / extrema_counts[0] if extrema_counts[0] else None,
                "scale_selection_performed": False,
            },
        }
        if view == "5m_offset_0":
            main_candidates = candidates_by_scale
            main_bars = bars
        save(args.output / "summary.json", summary)
        print(
            "VIEW_DONE", view,
            "extrema", extrema_counts[0], "->", extrema_counts[-1],
            "ratio", f"{extrema_counts[-1] / extrema_counts[0]:.6f}" if extrema_counts[0] else "na",
            flush=True,
        )

    assert len(summary["prefix_checks"]) == 3 * len(args.views)
    assert all(row["passed"] and row["confirmed_rewrite_count"] == 0 for row in summary["prefix_checks"])

    if main_candidates is not None and main_bars is not None:
        summary["fixed_window_audit"] = audit_ranges(main_candidates, fixed_day_bar_ranges(main_bars))
        legacy_path = ROOT / "cloud_results/two_wave_same_scale_delivery/v04/legacy_case_reaudit.json"
        legacy, source = legacy_ranges(legacy_path)
        summary["legacy_case_source"] = source
        summary["legacy_case_audit"] = audit_ranges(main_candidates, legacy)

    save(args.output / "summary.json", summary)
    print("PREFIX_CHECKS", len(summary["prefix_checks"]), "all_passed", flush=True)
    if "5m_offset_0" in summary["views"]:
        print("MAIN_TCSSLADDER", json.dumps(
            summary["views"]["5m_offset_0"]["tcss"]["extrema_counts_fine_to_coarse"],
            ensure_ascii=False,
        ), flush=True)
    if "legacy_case_audit" in summary:
        print("CASE00", json.dumps(summary["legacy_case_audit"].get("case_00_A_clear_C_uncertain"), ensure_ascii=False), flush=True)
    print("STUDY_COMPLETE", args.output, flush=True)


if __name__ == "__main__":
    main()
