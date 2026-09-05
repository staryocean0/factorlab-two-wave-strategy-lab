"""Result-before tests for v0.5.3 scale-aligned leg efficiency."""
from __future__ import annotations

import copy

import numpy as np
import pytest

from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from factor_lab.visual_structure.two_wave.scale_aligned_qualification_v053 import (
    FROZEN_NUMERICAL_THRESHOLD,
    requalify_record,
    scale_aligned_leg_paths,
)


def _record(reasons):
    return {
        "schema_version": "two_wave_extremum_ridge@0.5.2",
        "record_id": "old",
        "ridge_tuple_id": "tuple",
        "birth_scale_id": "scale",
        "birth_scale_level": 3,
        "characteristic_scale_id": "scale",
        "characteristic_scale_level": 3,
        "five_occurrence_bars": [0, 4, 8, 12, 16],
        "leg_paths": [
            {"efficiency": 0.2, "jump_share": 0.1, "flat_share": 0.0},
            {"efficiency": 0.2, "jump_share": 0.1, "flat_share": 0.0},
            {"efficiency": 0.2, "jump_share": 0.1, "flat_share": 0.0},
            {"efficiency": 0.2, "jump_share": 0.1, "flat_share": 0.0},
        ],
        "scale_rejection_reasons": list(reasons),
        "scale_qualified": False,
        "direction_versions": {"D1": "uptrend"},
        "classification": "not_same_scale",
        "selected": False,
        "overlap_suppressed_by": None,
        "trade_authority": False,
        "future_outcome_used": False,
    }


def test_threshold_is_frozen_at_point_five():
    assert FROZEN_NUMERICAL_THRESHOLD == 0.5
    with pytest.raises(ValueError, match="freezes min_leg_efficiency at 0.5"):
        requalify_record(_record(["inefficient_leg"]), np.arange(17.0), MaturityConfig(min_leg_efficiency=0.49))


def test_scale_aligned_efficiency_can_remove_only_inefficient_leg():
    # A monotone causal parent-scale path has ER=1 on each parent leg even if
    # the frozen raw diagnostic said the raw-close path was rough.
    series = np.arange(17.0)
    out = requalify_record(_record(["inefficient_leg"]), series, MaturityConfig())
    assert out["scale_qualified"]
    assert out["scale_rejection_reasons"] == []
    assert out["classification"] == "uptrend"
    assert min(path["efficiency"] for path in out["scale_aligned_leg_paths"]) == 1.0
    assert all(path["efficiency"] == 0.2 for path in out["raw_leg_paths_frozen_v043"])


def test_jump_rejection_is_not_relaxed_by_smooth_parent_scale_path():
    series = np.arange(17.0)
    out = requalify_record(_record(["inefficient_leg", "jump_dominated_leg"]), series, MaturityConfig())
    assert not out["scale_qualified"]
    assert out["scale_rejection_reasons"] == ["jump_dominated_leg"]
    assert out["classification"] == "not_same_scale"


def test_unrelated_duration_and_amplitude_rejections_are_frozen():
    series = np.arange(17.0)
    reasons = ["cycle_duration_mismatch", "amplitude_mismatch", "inefficient_leg"]
    out = requalify_record(_record(reasons), series, MaturityConfig())
    assert out["scale_rejection_reasons"] == ["cycle_duration_mismatch", "amplitude_mismatch"]
    assert not out["scale_qualified"]


def test_prefix_native_efficiency_uses_no_future_samples():
    prefix = np.asarray([0, 1, 2, 3, 4, 3, 2, 1, 0, 1, 2, 3, 4, 5, 6, 7, 8], dtype=float)
    extended = np.concatenate([prefix, np.asarray([1000.0, -1000.0, 500.0])])
    record = _record(["inefficient_leg"])
    a = scale_aligned_leg_paths(record, prefix)
    b = scale_aligned_leg_paths(record, extended)
    assert a == b


def test_requalification_does_not_mutate_v052_record():
    original = _record(["inefficient_leg", "jump_dominated_leg"])
    snapshot = copy.deepcopy(original)
    requalify_record(original, np.arange(17.0), MaturityConfig())
    assert original == snapshot
