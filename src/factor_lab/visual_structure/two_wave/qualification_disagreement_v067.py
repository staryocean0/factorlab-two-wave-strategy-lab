"""v0.6.7 audit-only helpers for qualification disagreement decomposition.

No qualification threshold or recognizer behavior is changed. Helpers classify
frozen v0.5.4 rejection reasons and provide read-only canonical-1m diagnostics.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence
from zoneinfo import ZoneInfo

import numpy as np

from .raw_projection_identity_v062 import CanonicalPathIndex, to_minutes

SCHEMA = "two_wave_qualification_disagreement_decomposition@0.6.7"
PATH_REASONS = {"jump_dominated_leg", "inefficient_leg", "flat_dominated_leg"}
DURATION_REASONS = {"short_leg", "short_cycle", "long_cycle", "long_pair", "cycle_duration_mismatch"}
AMPLITUDE_REASONS = {"invalid_amplitude", "amplitude_mismatch"}
CALENDAR_REASONS = {"too_many_observed_days", "wall_span_too_long"}
CONFIRMATION_REASONS = {"confirmation_too_late"}
REASON_FAMILY = {
    **{x: "path_metric" for x in PATH_REASONS},
    **{x: "duration_geometry" for x in DURATION_REASONS},
    **{x: "amplitude" for x in AMPLITUDE_REASONS},
    **{x: "calendar" for x in CALENDAR_REASONS},
    **{x: "confirmation_clock" for x in CONFIRMATION_REASONS},
}
SESSION_BOUNDARY_UTC_MINUTES = (90, 210, 300, 420)


def classify_primary_family(hard_reasons: Sequence[str]) -> str:
    reasons = [str(x) for x in hard_reasons]
    if not reasons:
        raise ValueError("rejected-side hard reasons required")
    unknown = sorted(set(reasons) - set(REASON_FAMILY))
    if unknown:
        raise ValueError(f"unknown hard reasons: {unknown}")
    families = {REASON_FAMILY[x] for x in reasons}
    if len(families) == 1:
        return f"{next(iter(families))}_only"
    return "mixed_multi_family"


def _min(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("nonempty values required")
    return float(min(values))


def _max(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("nonempty values required")
    return float(max(values))


def reason_metric_and_margin(reason: str, qualification: dict) -> dict:
    """Return the frozen metric and signed violation margin for one hard reason."""
    r = str(reason)
    legs = [float(x) for x in qualification["leg_durations"]]
    cycles = [float(x) for x in qualification["cycle_durations"]]
    eff = [float(x) for x in qualification["leg_efficiencies"]]
    jumps = [float(x) for x in qualification["leg_jump_shares"]]
    flats = [float(x) for x in qualification["leg_flat_shares"]]
    if r == "jump_dominated_leg":
        value = _max(jumps); threshold = 0.5; margin = value - threshold
    elif r == "inefficient_leg":
        value = _min(eff); threshold = 0.5; margin = threshold - value
    elif r == "flat_dominated_leg":
        value = _max(flats); threshold = 0.5; margin = value - threshold
    elif r == "short_leg":
        value = _min(legs); threshold = 4.0; margin = threshold - value
    elif r == "short_cycle":
        value = _min(cycles); threshold = 12.0; margin = threshold - value
    elif r == "long_cycle":
        value = _max(cycles); threshold = 48.0; margin = value - threshold
    elif r == "long_pair":
        value = float(sum(legs)); threshold = 96.0; margin = value - threshold
    elif r == "cycle_duration_mismatch":
        value = _max(cycles) / _min(cycles); threshold = 2.0; margin = value - threshold
    elif r == "invalid_amplitude":
        return {"reason": r, "value": None, "threshold": None, "signed_violation_margin": None, "validity_flag": False}
    elif r == "amplitude_mismatch":
        value = float(qualification["amplitude_ratio"]); threshold = 2.0; margin = value - threshold
    elif r == "confirmation_too_late":
        value = float(qualification["confirmation_delay_bars"]); threshold = 8.0; margin = value - threshold
    elif r == "too_many_observed_days":
        value = float(qualification["observed_trading_days"]); threshold = 3.0; margin = value - threshold
    elif r == "wall_span_too_long":
        value = float(qualification["wall_days"]); threshold = 7.0; margin = value - threshold
    else:
        raise ValueError(f"unknown hard reason: {r}")
    return {"reason": r, "value": value, "threshold": threshold, "signed_violation_margin": float(margin)}


def path_metrics_from_times(start_time: object, end_time: object, index: CanonicalPathIndex) -> dict | None:
    lo_t, hi_t = to_minutes(start_time), to_minutes(end_time)
    if lo_t >= hi_t:
        raise ValueError("strictly increasing leg times required")
    lo = int(np.searchsorted(index.minutes, lo_t, side="left"))
    hi = int(np.searchsorted(index.minutes, hi_t, side="right"))
    if lo >= hi or hi - lo < 2:
        return None
    y = np.asarray(index.closes[lo:hi], dtype=float)
    changes = np.abs(np.diff(y))
    length = float(changes.sum())
    efficiency = abs(float(y[-1] - y[0])) / length if length else 0.0
    jump_share = float(changes.max()) / length if length else 1.0
    flat_share = float(np.mean(changes == 0))
    return {
        "rows": int(len(y)),
        "start_time": index.timestamps[lo],
        "end_time": index.timestamps[hi - 1],
        "efficiency": efficiency,
        "jump_share": jump_share,
        "flat_share": flat_share,
    }


def one_minute_path_profile(anchor_times: Sequence[object], index: CanonicalPathIndex) -> dict:
    if len(anchor_times) != 5:
        raise ValueError("five anchor times required")
    legs = [path_metrics_from_times(a, b, index) for a, b in zip(anchor_times, anchor_times[1:])]
    available = all(x is not None for x in legs)
    return {"available": available, "legs": legs}


def one_minute_path_reason_flag(reason: str, profile: dict) -> bool | None:
    if reason not in PATH_REASONS:
        raise ValueError("path reason required")
    if not profile.get("available"):
        return None
    legs = profile["legs"]
    if reason == "jump_dominated_leg":
        return max(float(x["jump_share"]) for x in legs) > 0.5
    if reason == "inefficient_leg":
        return min(float(x["efficiency"]) for x in legs) < 0.5
    return max(float(x["flat_share"]) for x in legs) > 0.5


def diagnostic_relation(rejected_flag: bool | None, qualified_flag: bool | None) -> str:
    if rejected_flag is None or qualified_flag is None:
        return "unavailable"
    if rejected_flag and qualified_flag:
        return "both_fail"
    if not rejected_flag and not qualified_flag:
        return "both_pass"
    if rejected_flag:
        return "rejected_side_only"
    return "qualified_side_only"


def anchor_displacement(times_a: Sequence[object], times_b: Sequence[object]) -> dict:
    if len(times_a) != 5 or len(times_b) != 5:
        raise ValueError("five anchor times required")
    deltas = [abs(to_minutes(a) - to_minutes(b)) for a, b in zip(times_a, times_b)]
    return {
        "deltas_minutes": deltas,
        "max_delta_minutes": max(deltas),
        "sum_delta_minutes": sum(deltas),
        "nonzero_anchor_count": sum(x > 0 for x in deltas),
    }


def _minute_of_day(value: object) -> float:
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt.hour * 60 + dt.minute + dt.second / 60.0


def session_calendar_overlay(anchor_times: Sequence[object], confirmation_time: object) -> dict:
    if len(anchor_times) != 5:
        raise ValueError("five anchor times required")
    values = [*anchor_times, confirmation_time]
    nearby = any(any(abs(_minute_of_day(v) - b) <= 5.0 for b in SESSION_BOUNDARY_UTC_MINUTES) for v in values)
    lunch_cross = False
    sh = ZoneInfo("Asia/Shanghai")
    dates = []
    for a, b in zip(anchor_times, anchor_times[1:]):
        da = datetime.fromisoformat(str(a).replace("Z", "+00:00")); db = datetime.fromisoformat(str(b).replace("Z", "+00:00"))
        ma, mb = _minute_of_day(a), _minute_of_day(b)
        if da.date() == db.date() and ma <= 210 and mb >= 300:
            lunch_cross = True
        dates.extend([da.astimezone(sh).date().isoformat(), db.astimezone(sh).date().isoformat()])
    return {
        "session_boundary_nearby": nearby,
        "lunch_gap_crossed": lunch_cross,
        "multiple_shanghai_dates": len(set(dates)) > 1,
    }
