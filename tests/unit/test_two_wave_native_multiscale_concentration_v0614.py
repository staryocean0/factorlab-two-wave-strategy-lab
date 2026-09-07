from __future__ import annotations

import numpy as np

from factor_lab.visual_structure.two_wave.native_multiscale_concentration_v0614 import (
    native_multiscale_response,
    subpartition_indices,
)
from factor_lab.visual_structure.two_wave.step_count_normalized_concentration_v0613 import profile_from_closes


def test_subpartition_indices_are_deterministic():
    assert subpartition_indices(10, 2, 0) == (0, 2, 4, 6, 8, 9)
    assert subpartition_indices(10, 2, 1) == (0, 1, 3, 5, 7, 9)
    assert subpartition_indices(10, 3, 2) == (0, 2, 5, 8, 9)


def test_endpoints_are_always_preserved_once():
    for stride in (1,2,3,4):
        for phase in range(stride):
            idx = subpartition_indices(13, stride, phase)
            assert idx[0] == 0 and idx[-1] == 12
            assert len(idx) == len(set(idx))


def test_stride_one_reproduces_direct_v0613_profile():
    y = [0,1,3,2,5,4,8]
    direct = profile_from_closes(y)
    out = native_multiscale_response(y)
    p = out["strides"]["1"]["phases"][0]["profile"]
    for k in ("c_inf","c_1","c_2"):
        assert abs(direct[k] - p[k]) < 1e-12


def test_all_phases_are_retained_without_best_selection():
    out = native_multiscale_response([0,1,0,3,1,4,2,5,1])
    assert [len(out["strides"][str(s)]["phases"]) for s in (1,2,3,4)] == [1,2,3,4]
    assert "best" not in repr(out)


def test_future_append_outside_closed_input_cannot_enter_response():
    y = [0,1,0,3,1,4,2]
    a = native_multiscale_response(y)
    b = native_multiscale_response(y)
    assert a == b


def test_positive_price_scaling_preserves_response_components():
    y = np.array([1,2,1,4,2,6,3,7], dtype=float)
    a = native_multiscale_response(y)
    b = native_multiscale_response(11*y)
    for name in ("c_inf","c_1","c_2"):
        for key in ("native_value","delta_2","delta_3","delta_4","range_2","range_3","range_4"):
            av,bv=a["response"][name][key],b["response"][name][key]
            if av is None or bv is None:
                assert av is bv
            else:
                assert abs(av-bv)<1e-12


def test_short_subpartitions_remain_explicit_undefined():
    out = native_multiscale_response([0,1,2])
    # stride 4 phases cannot all form two movements; undefined profiles remain explicit.
    assert any(row["profile"]["defined"] is False for row in out["strides"]["4"]["phases"])


def test_native_api_has_no_oracle_counterpart_or_outcome_dependency():
    out = native_multiscale_response([0,1,0,3,1,4,2])
    text = repr(out)
    assert "oracle" not in text
    assert "counterpart" not in text
    assert "direction" not in text
    assert out["future_outcome_used"] is False
    assert out["trade_authority"] is False
