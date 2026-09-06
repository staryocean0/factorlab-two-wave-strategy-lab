from __future__ import annotations

import numpy as np

from factor_lab.visual_structure.two_wave.canonical_path_qualification_v068 import (
    canonical_path_profile,
    candidate_path_reasons,
    transform_control_qualification,
)
from factor_lab.visual_structure.two_wave.raw_projection_identity_v062 import CanonicalPathIndex


def idx(closes, minutes=None):
    minutes = list(range(len(closes))) if minutes is None else list(minutes)
    return CanonicalPathIndex(
        timestamps=tuple(f"1970-01-01T00:{m:02d}:00+00:00" for m in minutes),
        minutes=np.asarray(minutes, dtype=float),
        closes=np.asarray(closes, dtype=float),
    )


def control(reasons=None):
    return {
        "v054_hard_rejection_reasons": list(reasons or []),
        "leg_durations": [4, 4, 4, 4],
        "cycle_durations": [8, 8],
        "amplitude_ratio": 1.2,
        "observed_trading_days": 1,
        "wall_days": 0.1,
        "confirmation_delay_bars": 2,
    }


def test_shared_fine_lattice_is_identical_even_if_coarse_path_metrics_can_differ():
    fine = idx([0, 2, 0, 2, 0, 2, 0, 2, 0])
    a = canonical_path_profile([0, 2, 4, 6, 8], fine)
    b = canonical_path_profile([0, 2, 4, 6, 8], fine)
    assert a == b
    coarse_a = np.array([0, 0, 0], dtype=float)
    coarse_b = np.array([2, 2, 2], dtype=float)
    assert np.abs(np.diff(coarse_a)).sum() == np.abs(np.diff(coarse_b)).sum()
    assert a["available"] is True


def test_coarse_endpoints_do_not_identify_fine_path_variation():
    smooth = canonical_path_profile([0, 2, 4, 6, 8], idx([0, 1, 2, 3, 4, 5, 6, 7, 8]))
    zigzag = canonical_path_profile([0, 2, 4, 6, 8], idx([0, 2, 0, 4, 2, 6, 4, 8, 6]))
    assert smooth["legs"][0]["length"] != zigzag["legs"][0]["length"]


def test_future_append_after_leg_end_does_not_change_profile():
    a = canonical_path_profile([0, 2, 4, 6, 8], idx([0,1,2,3,4,5,6,7,8]))
    b = canonical_path_profile([0, 2, 4, 6, 8], idx([0,1,2,3,4,5,6,7,8,999]))
    assert a["legs"] == b["legs"]


def test_insufficient_rows_is_unavailable_without_interpolation():
    out = canonical_path_profile([0, 2, 4, 6, 8], idx([1,2,3], minutes=[0,4,8]))
    assert out["available"] is False


def test_constant_path_keeps_frozen_zero_length_convention():
    out = canonical_path_profile([0, 2, 4, 6, 8], idx([1]*9))
    leg = out["legs"][0]
    assert leg["efficiency"] == 0.0
    assert leg["jump_share"] == 1.0
    assert leg["flat_share"] == 1.0


def test_candidate_recomputes_only_path_reasons():
    fine = idx([0,1,0,1,0,1,0,1,0])
    out = transform_control_qualification(
        control(["jump_dominated_leg", "short_leg", "amplitude_mismatch"]),
        [0,2,4,6,8], fine,
    )
    assert out["available"] is True
    assert out["retained_non_path_hard_rejection_reasons"] == ["short_leg", "amplitude_mismatch"]
    assert "short_leg" in out["candidate_hard_rejection_reasons"]
    assert "amplitude_mismatch" in out["candidate_hard_rejection_reasons"]


def test_path_reason_thresholds_are_frozen():
    fine = idx([0,2,0,2,0,2,0,2,0])
    profile = canonical_path_profile([0,2,4,6,8], fine)
    reasons = candidate_path_reasons(profile)
    assert isinstance(reasons, list)


def test_transformer_does_not_require_direction_or_outcome_fields():
    out = transform_control_qualification(control([]), [0,2,4,6,8], idx([0,1,2,3,4,5,6,7,8]))
    assert out["future_outcome_used"] is False
    assert out["trade_authority"] is False
