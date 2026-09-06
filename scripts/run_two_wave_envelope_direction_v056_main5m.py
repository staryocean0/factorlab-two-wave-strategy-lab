#!/usr/bin/env python3
"""Formal main-5m mechanism audit for frozen v0.5.6 D2."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.d1_semantic_attribution_v055 import diagnose_with_subtype
from factor_lab.visual_structure.two_wave.envelope_direction_v056 import (
    SCHEMA,
    build_envelope_direction_run,
    d2_from_phase_steps,
)
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from run_two_wave_d1_semantic_attribution_v055 import FIXED_DAYS, FOCUS_CASES, fixed_day_ranges, legacy_ranges

VIEW = "5m_offset_0"
OUTPUT = ROOT / "cloud_results/two_wave_envelope_direction_v056_main5m"


def save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def q(values):
    vals = [float(v) for v in values if v is not None and np.isfinite(float(v))]
    if not vals:
        return None
    arr = np.asarray(vals, dtype=float)
    return {str(x): float(np.quantile(arr, x)) for x in (0, 0.1, 0.25, 0.5, 0.75, 0.9, 1)}


def identity(record):
    return (
        record["record_id"],
        record["ridge_tuple_id"],
        tuple(record["five_occurrence_bars"]),
        record["birth_scale_id"],
        record["confirmation_bar"],
        record["start_bar"],
        record["end_bar"],
    )


def compact(record):
    dv = record["direction_versions"]
    return {
        "record_id": record["record_id"],
        "five_occurrence_bars": list(record["five_occurrence_bars"]),
        "cycle_durations": list(record["cycle_durations"]),
        "leg_durations": list(record["leg_durations"]),
        "scale_qualified": bool(record["scale_qualified"]),
        "selected": bool(record["selected"]),
        "D0": dv.get("D0"),
        "D1": dv.get("D1"),
        "D1_reason": dv.get("D1_reason"),
        "D2": dv.get("D2"),
        "D2_reason": dv.get("D2_reason"),
        "s0": float(record["phase_steps_in_amplitude_units"][0]),
        "s1": float(record["phase_steps_in_amplitude_units"][1]),
        "s2": float(record["phase_steps_in_amplitude_units"][2]),
        "E_upper": float(dv["D2_upper_envelope_drift"]),
        "E_lower": float(dv["D2_lower_envelope_drift"]),
    }


def audit_ranges(records, ranges):
    out = {}
    for name, interval in ranges.items():
        if interval is None:
            out[name] = {"present": False}
            continue
        lo, hi = interval
        rows = [r for r in records if r["end_bar"] >= lo and r["start_bar"] <= hi]
        qualified = [r for r in rows if r["scale_qualified"]]
        selected = [r for r in rows if r["selected"]]
        out[name] = {
            "present": True,
            "bar_range": [lo, hi],
            "evaluated_overlap": len(rows),
            "qualified_overlap": len(qualified),
            "selected_overlap": len(selected),
            "D1_counts_qualified": dict(Counter(r["direction_versions"]["D1"] for r in qualified)),
            "D2_counts_qualified": dict(Counter(r["direction_versions"]["D2"] for r in qualified)),
            "qualified_records": [compact(r) for r in qualified[:20]],
            "selected_records": [compact(r) for r in selected[:20]],
        }
    return out


def main():
    bars, data_audit = load_development_bars(
        ROOT / "data/development/5m_offset_0.parquet", ROOT / "data/manifest.json"
    )
    cfg = MaturityConfig(timeframe=VIEW)
    run = build_envelope_direction_run(bars, cfg=cfg)
    before = run.base_run.ledger.records
    after = run.ledger.records
    before_selected = run.base_run.ledger.selected
    after_selected = run.ledger.selected

    assert len(before) == len(after)
    assert [identity(r) for r in before] == [identity(r) for r in after]
    assert [r["scale_qualified"] for r in before] == [r["scale_qualified"] for r in after]
    assert [r["record_id"] for r in before_selected] == [r["record_id"] for r in after_selected]
    assert [tuple(r["five_occurrence_bars"]) for r in before_selected] == [
        tuple(r["five_occurrence_bars"]) for r in after_selected
    ]
    assert all(r["direction_versions"]["D1"] == b["direction_versions"]["D1"] for b, r in zip(before, after))
    assert all(not r.get("future_outcome_used", False) for r in after)
    assert all(not r.get("trade_authority", False) for r in after)

    old_counterexample = d2_from_phase_steps(
        [-0.2335380601, -0.2638717691, -0.3512174141], "low", cfg
    )
    assert old_counterexample["label"] == "downtrend"

    qualified = [r for r in after if r["scale_qualified"]]
    selected = after_selected
    transitions_q = Counter(
        f"{r['direction_versions']['D1']}->{r['direction_versions']['D2']}" for r in qualified
    )
    transitions_s = Counter(
        f"{r['direction_versions']['D1']}->{r['direction_versions']['D2']}" for r in selected
    )

    subtype_transitions = defaultdict(Counter)
    for before_row, after_row in zip(before, after):
        if not after_row["scale_qualified"] or before_row["direction_versions"]["D1"] != "uncertain":
            continue
        diag = diagnose_with_subtype(before_row, cfg)
        subtype_transitions[str(diag["uncertain_subtype"])][after_row["direction_versions"]["D2"]] += 1

    d2_ranges = [r for r in qualified if r["direction_versions"]["D2"] == "range"]
    d2_trends = [r for r in qualified if r["direction_versions"]["D2"] in {"uptrend", "downtrend"}]
    local_reversal_ranges = [
        r for r in d2_ranges
        if float(r["phase_steps_in_amplitude_units"][0]) * float(r["phase_steps_in_amplitude_units"][1]) < 0
    ]
    range_excursions = [
        max(abs(float(r["phase_steps_in_amplitude_units"][0])), abs(float(r["phase_steps_in_amplitude_units"][1])))
        for r in d2_ranges
    ]
    trend_margins = [
        min(abs(float(r["direction_versions"]["D2_upper_envelope_drift"])),
            abs(float(r["direction_versions"]["D2_lower_envelope_drift"]))) - cfg.phase_tolerance
        for r in d2_trends
    ]

    summary = {
        "schema": SCHEMA,
        "status": "main5m_mechanism_audit_generated_pending_adjudication",
        "view": VIEW,
        "data_audit": data_audit,
        "thresholds": {
            "phase_tolerance_reused": cfg.phase_tolerance,
            "legacy_strong_drift_diagnostic_only": cfg.strong_drift,
            "legacy_opposite_tolerance_diagnostic_only": cfg.opposite_tolerance,
        },
        "upstream_invariants": {
            "candidate_identity_exact_match": True,
            "qualification_exact_match": True,
            "selected_record_ids_exact_match": True,
            "selected_occurrence_intervals_exact_match": True,
            "historical_D1_preserved": True,
            "future_outcome_used": False,
            "trade_authority": False,
        },
        "counts": {
            "evaluated": len(after),
            "qualified": len(qualified),
            "selected": len(selected),
            "D1_qualified": dict(Counter(r["direction_versions"]["D1"] for r in qualified)),
            "D2_qualified": dict(Counter(r["direction_versions"]["D2"] for r in qualified)),
            "D1_selected": dict(Counter(r["direction_versions"]["D1"] for r in selected)),
            "D2_selected": dict(Counter(r["direction_versions"]["D2"] for r in selected)),
        },
        "D1_to_D2_qualified": dict(transitions_q),
        "D1_to_D2_selected": dict(transitions_s),
        "D1_uncertain_subtype_to_D2": {k: dict(v) for k, v in sorted(subtype_transitions.items())},
        "D2_range_diagnostics": {
            "qualified_range_count": len(d2_ranges),
            "local_s0_s1_reversal_count": len(local_reversal_ranges),
            "local_s0_s1_reversal_fraction": len(local_reversal_ranges) / len(d2_ranges) if d2_ranges else None,
            "max_local_same_envelope_step_quantiles": q(range_excursions),
        },
        "D2_trend_diagnostics": {
            "qualified_trend_count": len(d2_trends),
            "minimum_envelope_margin_above_0_15_quantiles": q(trend_margins),
        },
        "old_D0_counterexample": old_counterexample,
        "fixed_window_audit": audit_ranges(after, fixed_day_ranges(bars)),
        "legacy_case_audit": audit_ranges(
            after,
            legacy_ranges(ROOT / "docs/research/two_wave_v04_legacy_cases.json"),
        ),
        "pass_criteria": {
            "upstream_zero_drift": True,
            "synthetic_semantics_delegated_to_full_regression": True,
            "old_D0_counterexample_preserved": True,
            "result_not_judged_by_label_balance": True,
        },
    }
    save(OUTPUT / "summary.json", summary)
    save(OUTPUT / "qualified_records.json", [compact(r) for r in qualified])
    save(OUTPUT / "selected_records.json", [compact(r) for r in selected])
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
