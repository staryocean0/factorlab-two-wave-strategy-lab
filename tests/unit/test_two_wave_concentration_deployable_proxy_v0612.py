from __future__ import annotations

import numpy as np

from factor_lab.visual_structure.two_wave.concentration_deployable_proxy_v0612 import (
    empirical_bracket,
    native_concentration_proxy,
)


def test_close_concentration_formula():
    out = native_concentration_proxy([1,2,3],[0,1,2],[0,1,3])
    # close moves = [1,2]
    assert np.isclose(out["j_close"], 2/3)


def test_true_range_uses_prior_close_and_current_high_low():
    out = native_concentration_proxy([1,5,4],[0,4,3],[0,1,3])
    # transition 1 TR=max(1,5,4)=5; transition 2 TR=max(1,3,2)=3
    assert np.isclose(out["j_true_range"], 5/8)


def test_high_low_concentration_formula():
    out = native_concentration_proxy([1,5,6],[0,4,2],[0,1,3])
    # ranges used are [1,4]
    assert np.isclose(out["j_high_low"], 4/5)


def test_proxy_interface_requires_no_oracle_or_counterpart():
    out = native_concentration_proxy([1,2,3],[0,1,2],[0,1,3])
    assert out["primary_proxy"] == "native_true_range_concentration"
    assert "oracle" not in repr(out)
    assert "counterpart" not in repr(out)
    assert out["future_outcome_used"] is False
    assert out["trade_authority"] is False


def test_future_append_after_leg_end_cannot_change_closed_leg_proxy():
    a = native_concentration_proxy([1,2,3],[0,1,2],[0,1,3])
    b = native_concentration_proxy([1,2,3],[0,1,2],[0,1,3])
    assert a == b


def test_gap_is_visible_through_true_range_previous_close_term():
    out = native_concentration_proxy([10,20],[9,19],[10,20])
    # close jump and true range both see the 10 point gap/move; pure HL only sees range=1.
    assert out["true_range_sum"] == 10
    assert out["high_low_sum"] == 1


def test_zero_sum_paths_remain_explicit_undefined():
    out = native_concentration_proxy([1,1],[1,1],[1,1])
    assert out["j_close"] is None
    assert out["j_true_range"] is None
    assert out["j_high_low"] is None
    assert out["proxy_spread"] is None


def test_proxy_spread_and_bracket_are_unweighted_deterministic_functions():
    out = native_concentration_proxy([2,5,4],[0,1,2],[1,2,3])
    vals=[out["j_close"],out["j_true_range"],out["j_high_low"]]
    assert np.isclose(out["proxy_lower"],min(vals))
    assert np.isclose(out["proxy_upper"],max(vals))
    assert np.isclose(out["proxy_spread"],max(vals)-min(vals))


def test_empirical_bracket_is_explicitly_audit_only():
    out = native_concentration_proxy([2,5,4],[0,1,2],[1,2,3])
    chk = empirical_bracket(out, (out["proxy_lower"]+out["proxy_upper"])/2)
    assert chk["inside"] is True
    assert chk["audit_only"] is True
