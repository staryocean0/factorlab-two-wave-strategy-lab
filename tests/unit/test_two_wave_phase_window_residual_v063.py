from __future__ import annotations

from factor_lab.visual_structure.two_wave.phase_window_residual_v063 import (
    classify_residual_pair,
    intersection_diagnostic,
    sequential_overlay,
    session_gap_overlay,
)
from factor_lab.visual_structure.two_wave.raw_projection_identity_v062 import CanonicalPathIndex


def wins(lower_a=0, upper_a=10, lower_b=0, upper_b=10):
    a = []
    b = []
    for k in range(5):
        a.append({
            "ordinal": k,
            "kind": "low" if k % 2 == 0 else "high",
            "lower_time": lower_a,
            "upper_time": upper_a,
            "selected_raw_time": 2 + k,
        })
        b.append({
            "ordinal": k,
            "kind": "low" if k % 2 == 0 else "high",
            "lower_time": lower_b,
            "upper_time": upper_b,
            "selected_raw_time": 3 + k,
        })
    return a, b


def one(times, closes=None, ties=None):
    closes = closes or [1.0] * 5
    ties = ties or [1] * 5
    return {
        "available": True,
        "times": times,
        "rows": [
            {"occurrence_time": t, "close": c, "tie_count": q}
            for t, c, q in zip(times, closes, ties)
        ],
    }


def test_ordinal0_lower_exclusion_maps_to_extrapolated_left_bound():
    a, b = wins(lower_a=0, upper_a=20, lower_b=8, upper_b=20)
    out = classify_residual_pair(a, b, one([2, 4, 6, 8, 10]), one([10, 4, 6, 8, 10]))
    assert out["first_displaced_ordinal"] == 0
    assert out["primary_attribution"] == "ordinal0_extrapolated_left_bound_exclusion"


def test_predecessor_upper_exclusion_at_middle_ordinal():
    a, b = wins()
    a[2]["upper_time"] = 12
    b[2]["upper_time"] = 30
    out = classify_residual_pair(a, b, one([0, 5, 10, 15, 20]), one([0, 5, 25, 15, 20]))
    assert out["first_displaced_ordinal"] == 2
    assert out["primary_attribution"] == "filtered_predecessor_upper_bound_exclusion"


def test_sequential_lower_exclusion_at_middle_ordinal():
    a, b = wins()
    a[2]["upper_time"] = 30
    b[2]["lower_time"] = 20
    b[2]["upper_time"] = 40
    out = classify_residual_pair(a, b, one([0, 5, 10, 15, 20]), one([0, 5, 25, 15, 20]))
    assert out["first_displaced_ordinal"] == 2
    assert out["primary_attribution"] == "sequential_lower_bound_exclusion"


def test_confirmation_tail_upper_exclusion_at_ordinal4():
    a, b = wins()
    a[4]["upper_time"] = 24
    b[4]["upper_time"] = 40
    out = classify_residual_pair(a, b, one([0, 5, 10, 15, 20]), one([0, 5, 10, 15, 30]))
    assert out["first_displaced_ordinal"] == 4
    assert out["primary_attribution"] == "confirmation_tail_upper_bound_exclusion"


def test_mixed_lower_upper_exclusion_has_priority():
    a, b = wins(lower_a=0, upper_a=10, lower_b=8, upper_b=30)
    out = classify_residual_pair(a, b, one([2, 4, 6, 8, 10]), one([20, 4, 6, 8, 10]))
    assert out["primary_attribution"] == "mixed_lower_upper_exclusion"


def test_overlap_extreme_competition_when_neither_selection_excluded():
    a, b = wins(lower_a=0, upper_a=30, lower_b=0, upper_b=30)
    out = classify_residual_pair(a, b, one([2, 4, 6, 8, 10]), one([20, 4, 6, 8, 10]))
    assert out["primary_attribution"] == "mutual_window_overlap_extreme_competition"


def test_intersection_diagnostic_is_read_only_common_support():
    idx = CanonicalPathIndex(
        timestamps=("1970-01-01T00:00:00+00:00", "1970-01-01T00:05:00+00:00", "1970-01-01T00:10:00+00:00"),
        minutes=__import__("numpy").array([0.0, 5.0, 10.0]),
        closes=__import__("numpy").array([3.0, 1.0, 2.0]),
    )
    a = {"kind": "low", "lower_time": 0, "upper_time": 10}
    b = {"kind": "low", "lower_time": 4, "upper_time": 10}
    out = intersection_diagnostic(a, b, idx, 5, 5)
    assert out["available"] is True
    assert out["occurrence_time"] == "1970-01-01T00:05:00+00:00"
    assert out["within_one_bar_of_both"] is True


def test_session_gap_overlay_tags_lunch_and_boundary_nearby():
    a, b = wins()
    a[0]["lower_time"] = "2020-01-02T03:30:00+00:00"
    b[0]["lower_time"] = "2020-01-02T05:00:00+00:00"
    a[0]["upper_time"] = "2020-01-02T03:35:00+00:00"
    b[0]["upper_time"] = "2020-01-02T05:05:00+00:00"
    out = session_gap_overlay(a, b, 0)
    assert out["lunch_gap_straddled"] is True
    assert out["session_boundary_nearby"] is True


def test_sequential_overlay_reports_prior_selection_difference_and_suffix():
    a, b = wins()
    a[1]["selected_raw_time"] = 5
    b[1]["selected_raw_time"] = 6
    out = sequential_overlay(a, b, one([0, 5, 10, 15, 20]), one([0, 5, 20, 25, 30]), 2)
    assert out["prior_5m_selected_time_differs"] is True
    assert out["residual_displaced_is_suffix"] is True
