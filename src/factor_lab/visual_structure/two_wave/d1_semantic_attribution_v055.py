"""Read-only semantic diagnostics for frozen D1 labels (v0.5.5).

This module does not classify, requalify, select, or use outcomes.  It only
expands the already-frozen v0.5.4 record geometry into interpretable parent
migration diagnostics and partitions existing D1='uncertain' records into
mutually exclusive attribution buckets.
"""
from __future__ import annotations

import math
from typing import Any

from .same_scale_v043 import MaturityConfig

SCHEMA = "two_wave_d1_semantic_attribution@0.5.5"


def _finite(values) -> bool:
    return all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v)) for v in values)


def _raw_sign(value: float, eps: float = 1e-12) -> str:
    if value > eps:
        return "+"
    if value < -eps:
        return "-"
    return "0"


def _threshold_state(value: float, tolerance: float) -> str:
    if value > tolerance:
        return "U"
    if value < -tolerance:
        return "D"
    return "W"


def range_span_bound(cfg: MaturityConfig | None = None) -> dict[str, float | bool]:
    """Show why the frozen range span gate is implied by all-small phase steps.

    If |s0|,|s1|<=phase_tolerance, the three same-phase levels can span at most
    2*phase_tolerance.  The opposite-phase span is |s2|<=phase_tolerance.
    Therefore max(spans)<=strong_drift is algebraically redundant whenever
    2*phase_tolerance <= strong_drift.
    """
    c = cfg or MaturityConfig()
    bound = 2.0 * c.phase_tolerance
    return {
        "same_phase_span_upper_bound": bound,
        "opposite_phase_span_upper_bound": c.phase_tolerance,
        "strong_drift_gate": c.strong_drift,
        "range_span_gate_implied": bound <= c.strong_drift,
    }


def diagnose_record(record: dict[str, Any], cfg: MaturityConfig | None = None) -> dict[str, Any]:
    """Expand one frozen v0.5.4 record without changing any existing decision."""
    c = cfg or MaturityConfig(timeframe=record.get("timeframe", "5m_offset_0"))
    steps = record.get("phase_steps_in_amplitude_units")
    spans = record.get("phase_spans_in_amplitude_units")
    if not (isinstance(steps, list) and len(steps) == 3 and _finite(steps)):
        raise ValueError("three finite frozen phase steps required")
    if not (isinstance(spans, list) and len(spans) == 2 and _finite(spans)):
        raise ValueError("two finite frozen phase spans required")
    s0, s1, s2 = (float(v) for v in steps)
    net = s0 + s1
    phase = record.get("phase")
    if phase not in {"low", "high"}:
        raise ValueError("record phase must be low or high")

    if phase == "low":
        lower_drift, upper_drift = net, s2
    else:
        upper_drift, lower_drift = net, s2

    center_drift = 0.25 * net + 0.5 * s2
    amplitudes = [float(x) for x in record.get("detrended_amplitudes_price", [])]
    if len(amplitudes) != 2 or not _finite(amplitudes) or min(amplitudes) <= 0:
        amplitude_change = None
    else:
        mean_amp = 0.5 * (amplitudes[0] + amplitudes[1])
        amplitude_change = (amplitudes[1] - amplitudes[0]) / mean_amp

    cycles = [float(x) for x in record.get("cycle_durations", [])]
    if len(cycles) != 2 or not _finite(cycles) or min(cycles) <= 0:
        mean_cycle = None
        net_speed = None
        center_speed = None
    else:
        mean_cycle = 0.5 * (cycles[0] + cycles[1])
        net_speed = net / mean_cycle
        center_speed = center_drift / mean_cycle

    corr = record.get("corresponding_leg_duration_diagnostic", {})
    max_corr_ratio = corr.get("max_ratio")
    if max_corr_ratio is not None:
        max_corr_ratio = float(max_corr_ratio)

    dversions = record.get("direction_versions", {})
    d0 = dversions.get("D0")
    d1 = dversions.get("D1")
    d1_reason = dversions.get("D1_reason")

    same_phase_conflict = s0 * s1 < 0 and min(abs(s0), abs(s1)) > c.phase_tolerance
    envelope_conflict = net * s2 < 0 and min(abs(net), abs(s2)) > c.phase_tolerance
    envelope_same_direction = upper_drift * lower_drift > 0
    same_phase_same_direction = s0 * s1 > 0

    orientation_source = net if abs(net) > 1e-12 else (s0 + s1 + s2)
    orientation = 1.0 if orientation_source >= 0 else -1.0
    directed = [orientation * v for v in (s0, s1, s2)]
    strong_net = abs(net) > c.strong_drift
    opposed_beyond_frozen_tolerance = min(directed) < -c.opposite_tolerance
    clear_directed_phases = sum(v > c.phase_tolerance for v in directed)

    return {
        "schema": SCHEMA,
        "record_id": record.get("record_id"),
        "phase": phase,
        "D0": d0,
        "D1": d1,
        "D1_reason": d1_reason,
        "s0_same_phase_first": s0,
        "s1_same_phase_second": s1,
        "s2_opposite_envelope": s2,
        "net_same_phase_drift": net,
        "upper_envelope_drift": upper_drift,
        "lower_envelope_drift": lower_drift,
        "upper_minus_lower_drift": upper_drift - lower_drift,
        "center_drift_linear_diagnostic": center_drift,
        "amplitude_change_fraction": amplitude_change,
        "max_corresponding_leg_duration_ratio": max_corr_ratio,
        "mean_cycle_duration": mean_cycle,
        "net_drift_per_mean_cycle_bar": net_speed,
        "center_drift_per_mean_cycle_bar": center_speed,
        "same_phase_same_direction": same_phase_same_direction,
        "envelope_same_direction": envelope_same_direction,
        "same_phase_reversal_conflict": same_phase_conflict,
        "opposite_envelope_conflict": envelope_conflict,
        "strong_net": strong_net,
        "opposed_beyond_frozen_tolerance": opposed_beyond_frozen_tolerance,
        "clear_directed_phase_count": clear_directed_phases,
        "raw_sign_pattern": "".join(_raw_sign(v) for v in (s0, s1, s2)),
        "threshold_pattern": "".join(_threshold_state(v, c.phase_tolerance) for v in (s0, s1, s2)),
        "max_abs_phase_step": max(abs(s0), abs(s1), abs(s2)),
        "max_phase_span": max(float(v) for v in spans),
        "phase_tolerance_margin_max_abs": max(abs(s0), abs(s1), abs(s2)) - c.phase_tolerance,
        "strong_drift_margin_abs_net": abs(net) - c.strong_drift,
        "minimum_directed_margin_to_opposite_tolerance": min(directed) + c.opposite_tolerance,
        "range_all_steps_small": max(abs(s0), abs(s1), abs(s2)) <= c.phase_tolerance,
        "range_span_gate_pass": max(float(v) for v in spans) <= c.strong_drift,
    }


def uncertain_subtype(diagnostic: dict[str, Any], cfg: MaturityConfig | None = None) -> str | None:
    """Mutually exclusive explanation for an already-frozen D1='uncertain'."""
    if diagnostic.get("D1") != "uncertain":
        return None
    c = cfg or MaturityConfig()
    s0 = float(diagnostic["s0_same_phase_first"])
    s1 = float(diagnostic["s1_same_phase_second"])
    s2 = float(diagnostic["s2_opposite_envelope"])
    net = float(diagnostic["net_same_phase_drift"])

    if diagnostic["same_phase_reversal_conflict"]:
        return "same_phase_reversal_conflict"
    if diagnostic["opposite_envelope_conflict"]:
        return "opposite_envelope_conflict"
    if diagnostic["strong_net"] and diagnostic["opposed_beyond_frozen_tolerance"]:
        return "strong_net_with_opposed_phase"

    orient_source = net if abs(net) > 1e-12 else (s0 + s1 + s2)
    orient = 1.0 if orient_source >= 0 else -1.0
    directed = [orient * v for v in (s0, s1, s2)]
    coherent = min(directed) >= -c.opposite_tolerance and sum(v > 0 for v in directed) >= 2
    if coherent:
        return "coherent_but_subthreshold"

    clear = sum(abs(v) > c.phase_tolerance for v in (s0, s1, s2))
    if clear == 1:
        return "single_phase_dominant"
    if diagnostic["max_phase_span"] > c.strong_drift or clear >= 2:
        return "large_migration_without_coherent_direction"
    return "weak_mixed_migration"


def diagnose_with_subtype(record: dict[str, Any], cfg: MaturityConfig | None = None) -> dict[str, Any]:
    out = diagnose_record(record, cfg)
    out["uncertain_subtype"] = uncertain_subtype(out, cfg)
    return out
