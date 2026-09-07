from __future__ import annotations

import numpy as np

from factor_lab.visual_structure.two_wave.step_count_normalized_concentration_v0613 import (
    concentration_profile,
    profile_from_closes,
    uniformly_subdivide,
)


def test_uniform_movements_zero_profile():
    out = concentration_profile([1, 1, 1, 1])
    assert out["defined"] is True
    assert abs(out["c_inf"]) < 1e-12
    assert abs(out["c_1"]) < 1e-12
    assert abs(out["c_2"]) < 1e-12


def test_nonuniform_movements_positive_concentration():
    out = concentration_profile([8, 1, 1, 1])
    assert out["c_inf"] > 0
    assert out["c_1"] > 0
    assert out["c_2"] > 0


def test_uniform_subdivision_invariance_multiple_k():
    base = np.array([0.5, 1.5, 3.0, 2.0], dtype=float)
    a = concentration_profile(base)
    for k in (1, 2, 3, 5, 8):
        b = concentration_profile(uniformly_subdivide(base, k))
        assert abs(a["c_inf"] - b["c_inf"]) < 1e-12
        assert abs(a["c_1"] - b["c_1"]) < 1e-12
        assert abs(a["c_2"] - b["c_2"]) < 1e-12


def test_positive_scale_invariance():
    a = concentration_profile([1, 2, 5, 3])
    b = concentration_profile([7, 14, 35, 21])
    assert abs(a["c_inf"] - b["c_inf"]) < 1e-12
    assert abs(a["c_1"] - b["c_1"]) < 1e-12
    assert abs(a["c_2"] - b["c_2"]) < 1e-12


def test_zero_weights_follow_zero_log_zero_convention():
    out = concentration_profile([0, 2, 0, 2])
    assert out["defined"] is True
    assert np.isfinite(out["c_inf"])
    assert np.isfinite(out["c_1"])
    assert np.isfinite(out["c_2"])


def test_zero_sum_is_explicit_undefined():
    out = concentration_profile([0, 0, 0])
    assert out["defined"] is False
    assert out["reason"] == "zero_total_movement"
    assert out["c_inf"] is None


def test_fewer_than_two_movements_is_explicit_undefined():
    out = concentration_profile([1])
    assert out["defined"] is False
    assert out["reason"] == "fewer_than_two_movements"


def test_profile_from_closes_is_prefix_local_for_closed_leg():
    a = profile_from_closes([0, 1, 3, 2, 5])
    b = profile_from_closes([0, 1, 3, 2, 5])
    assert a == b
    assert a["future_outcome_used"] is False
    assert a["trade_authority"] is False


def test_primitive_interface_has_no_oracle_or_counterpart_dependency():
    out = concentration_profile([1, 2, 1, 4])
    text = repr(out)
    assert "oracle" not in text
    assert "counterpart" not in text
    assert "direction" not in text
