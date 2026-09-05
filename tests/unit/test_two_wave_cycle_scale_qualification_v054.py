"""Result-before tests for v0.5.4 cycle-scale qualification ablation."""
from __future__ import annotations

import copy

from factor_lab.visual_structure.two_wave.cycle_scale_qualification_v054 import (
    REMOVED_HARD_REASON,
    corresponding_leg_duration_ratios,
    requalify_record,
)


def _record(reasons, legs=(8, 12, 20, 4)):
    return {
        "schema_version": "two_wave_extremum_ridge@0.5.2",
        "record_id": "old",
        "ridge_tuple_id": "tuple",
        "ridge_ids": ["r0", "r1", "r2", "r3", "r4"],
        "birth_scale_id": "scale",
        "birth_scale_level": 4,
        "five_occurrence_bars": [0, 8, 20, 40, 44],
        "confirmation_bar": 50,
        "leg_durations": list(legs),
        "cycle_durations": [legs[0] + legs[1], legs[2] + legs[3]],
        "scale_rejection_reasons": list(reasons),
        "scale_qualified": False,
        "direction_versions": {"D1": "downtrend"},
        "classification": "not_same_scale",
        "selected": False,
        "overlap_suppressed_by": None,
        "trade_authority": False,
        "future_outcome_used": False,
    }


def test_only_corresponding_leg_reason_is_demoted():
    out = requalify_record(_record([REMOVED_HARD_REASON]))
    assert out["scale_qualified"]
    assert out["scale_rejection_reasons"] == []
    assert out["classification"] == "downtrend"
    assert out["corresponding_leg_duration_diagnostic"]["frozen_v052_triggered"] is True
    assert out["corresponding_leg_duration_diagnostic"]["hard_gate"] is False


def test_cycle_duration_and_other_hard_reasons_remain():
    reasons = ["cycle_duration_mismatch", REMOVED_HARD_REASON, "jump_dominated_leg"]
    out = requalify_record(_record(reasons))
    assert out["scale_rejection_reasons"] == ["cycle_duration_mismatch", "jump_dominated_leg"]
    assert not out["scale_qualified"]


def test_short_efficiency_amplitude_confirmation_are_not_relaxed():
    reasons = [
        "short_leg", "short_cycle", "amplitude_mismatch", "inefficient_leg",
        "confirmation_too_late", REMOVED_HARD_REASON,
    ]
    out = requalify_record(_record(reasons))
    assert out["scale_rejection_reasons"] == reasons[:-1]
    assert not out["scale_qualified"]


def test_diagnostic_ratios_preserve_phase_allocation_mismatch():
    r = _record([REMOVED_HARD_REASON], legs=(8, 12, 20, 4))
    ratios = corresponding_leg_duration_ratios(r)
    assert ratios == [2.5, 3.0]
    out = requalify_record(r)
    assert out["corresponding_leg_duration_diagnostic"]["ratios"] == [2.5, 3.0]
    assert out["corresponding_leg_duration_diagnostic"]["max_ratio"] == 3.0


def test_input_v052_record_is_immutable():
    r = _record([REMOVED_HARD_REASON, "jump_dominated_leg"])
    snapshot = copy.deepcopy(r)
    requalify_record(r)
    assert r == snapshot
