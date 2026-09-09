"""v0.6.3 audit-only helpers for residual phase-window semantics.

No recognizer or projection behavior is changed.  These helpers operate only on
already-frozen v0.6.2 projection windows and supplied canonical-path selections.
"""
from __future__ import annotations

from datetime import datetime
from typing import Sequence

from .raw_projection_identity_v062 import (
    CanonicalPathIndex,
    NOMINAL_BAR_MINUTES,
    one_minute_projection_from_windows,
    raw_pair_displacement,
    to_minutes,
)

SCHEMA = "two_wave_phase_window_residual_audit@0.6.3"
SESSION_BOUNDARY_UTC_MINUTES = (90, 210, 300, 420)


def _dt(value: object) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _outside(value: object, lower: object, upper: object) -> tuple[bool, bool]:
    x, lo, hi = to_minutes(value), to_minutes(lower), to_minutes(upper)
    return x < lo, x > hi


def classify_residual_pair(
    windows_a: Sequence[dict],
    windows_b: Sequence[dict],
    one_min_a: dict,
    one_min_b: dict,
) -> dict:
    """Assign exactly one frozen primary attribution at earliest 1m displacement."""
    if len(windows_a) != 5 or len(windows_b) != 5:
        raise ValueError("five projection windows required")
    if not one_min_a.get("available") or not one_min_b.get("available"):
        raise ValueError("v0.6.3 primary population requires available 1m projections")
    times_a, times_b = one_min_a.get("times"), one_min_b.get("times")
    if times_a is None or times_b is None:
        raise ValueError("five canonical-path times required")
    disp = raw_pair_displacement(times_a, times_b)
    if disp["strict_match"]:
        raise ValueError("v0.6.3 primary population requires 1m residual displacement")
    k = int(disp["first_displaced_ordinal"])
    wa, wb = windows_a[k], windows_b[k]
    ta, tb = times_a[k], times_b[k]
    a_before_b, a_after_b = _outside(ta, wb["lower_time"], wb["upper_time"])
    b_before_a, b_after_a = _outside(tb, wa["lower_time"], wa["upper_time"])
    lower = bool(a_before_b or b_before_a)
    upper = bool(a_after_b or b_after_a)

    if lower and upper:
        category = "mixed_lower_upper_exclusion"
    elif k == 0 and lower:
        category = "ordinal0_extrapolated_left_bound_exclusion"
    elif k < 4 and upper:
        category = "filtered_predecessor_upper_bound_exclusion"
    elif k > 0 and lower:
        category = "sequential_lower_bound_exclusion"
    elif k == 4 and upper:
        category = "confirmation_tail_upper_bound_exclusion"
    elif not lower and not upper:
        category = "mutual_window_overlap_extreme_competition"
    else:
        raise AssertionError("frozen v0.6.3 attribution order did not close")

    return {
        "schema": SCHEMA,
        "primary_attribution": category,
        "first_displaced_ordinal": k,
        "one_minute_displacement": disp,
        "lower_exclusion_present": lower,
        "upper_exclusion_present": upper,
        "a_before_b_lower": a_before_b,
        "a_after_b_upper": a_after_b,
        "b_before_a_lower": b_before_a,
        "b_after_a_upper": b_after_a,
        "a_selected_time": ta,
        "b_selected_time": tb,
        "a_selected_close": float(one_min_a["rows"][k]["close"]),
        "b_selected_close": float(one_min_b["rows"][k]["close"]),
        "a_tie_count": int(one_min_a["rows"][k]["tie_count"]),
        "b_tie_count": int(one_min_b["rows"][k]["tie_count"]),
        "lower_bound_delta_minutes": abs(to_minutes(wa["lower_time"]) - to_minutes(wb["lower_time"])),
        "upper_bound_delta_minutes": abs(to_minutes(wa["upper_time"]) - to_minutes(wb["upper_time"])),
    }


def session_gap_overlay(windows_a: Sequence[dict], windows_b: Sequence[dict], ordinal: int) -> dict:
    """Descriptive lunch/overnight/session-boundary overlay for one ordinal."""
    k = int(ordinal)
    if not 0 <= k < 5:
        raise ValueError("ordinal must be in [0,4]")
    wa, wb = windows_a[k], windows_b[k]
    lunch = False
    overnight = False
    nearby = False
    rows = []
    for bound in ("lower_time", "upper_time"):
        a, b = _dt(wa[bound]), _dt(wb[bound])
        ma = a.hour * 60 + a.minute + a.second / 60.0
        mb = b.hour * 60 + b.minute + b.second / 60.0
        if a.date() == b.date() and ((ma <= 210 and mb >= 300) or (mb <= 210 and ma >= 300)):
            lunch = True
        if a.date() != b.date():
            overnight = True
        if any(abs(ma - x) <= NOMINAL_BAR_MINUTES for x in SESSION_BOUNDARY_UTC_MINUTES) or any(
            abs(mb - x) <= NOMINAL_BAR_MINUTES for x in SESSION_BOUNDARY_UTC_MINUTES
        ):
            nearby = True
        rows.append({"bound": bound, "a": str(wa[bound]), "b": str(wb[bound])})
    return {
        "lunch_gap_straddled": lunch,
        "overnight_gap_straddled": overnight,
        "session_boundary_nearby": nearby,
        "bounds": rows,
    }


def sequential_overlay(
    windows_a: Sequence[dict],
    windows_b: Sequence[dict],
    one_min_a: dict,
    one_min_b: dict,
    ordinal: int,
) -> dict:
    k = int(ordinal)
    disp = raw_pair_displacement(one_min_a["times"], one_min_b["times"])
    return {
        "ordinal": k,
        "prior_5m_selected_time_differs": (
            bool(k > 0 and windows_a[k - 1]["selected_raw_time"] != windows_b[k - 1]["selected_raw_time"])
        ),
        "residual_displaced_is_suffix": bool(disp["displaced_is_suffix"]),
    }


def intersection_diagnostic(
    window_a: dict,
    window_b: dict,
    index: CanonicalPathIndex,
    selected_a: object,
    selected_b: object,
) -> dict:
    """Project only on the absolute window intersection; diagnostic, never runtime."""
    lo = max(to_minutes(window_a["lower_time"]), to_minutes(window_b["lower_time"]))
    hi = min(to_minutes(window_a["upper_time"]), to_minutes(window_b["upper_time"]))
    if lo > hi:
        return {"available": False, "reason": "empty_absolute_intersection"}
    projected = index.project_window(lo, hi, str(window_a["kind"]))
    if projected is None:
        return {"available": False, "reason": "no_supplied_1m_row_in_intersection"}
    ta, tb, ti = to_minutes(selected_a), to_minutes(selected_b), to_minutes(projected["occurrence_time"])
    return {
        "available": True,
        "reason": None,
        "occurrence_time": projected["occurrence_time"],
        "close": float(projected["close"]),
        "tie_count": int(projected["tie_count"]),
        "delta_to_a_minutes": abs(ti - ta),
        "delta_to_b_minutes": abs(ti - tb),
        "within_one_bar_of_both": abs(ti - ta) <= NOMINAL_BAR_MINUTES and abs(ti - tb) <= NOMINAL_BAR_MINUTES,
    }


def project_canonical_windows(windows: Sequence[dict], index: CanonicalPathIndex) -> dict:
    return one_minute_projection_from_windows(windows, index)
