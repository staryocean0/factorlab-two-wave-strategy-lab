from __future__ import annotations

import numpy as np

from factor_lab.visual_structure.two_wave.roughness_interval_sensitivity_v0611 import (
    MinutePathIndex,
    boundary_sliver_diagnostics,
    common_support_oracle,
    erosion_roughness_ensemble,
    interval_roughness,
    pair_roughness_decomposition,
    path_roughness,
)


def idx(minutes=range(30), closes=None):
    mm = np.asarray(list(minutes), dtype=int)
    if closes is None:
        closes = np.asarray([0,1,0,2,1,3,2,4,3,5,4,6,5,7,6,8,7,9,8,10,9,11,10,12,11,13,12,14,13,15], dtype=float)[:len(mm)]
    return MinutePathIndex(mm, np.asarray(closes, dtype=float))


def test_roughness_formula():
    out = path_roughness([0, 1, 0, 2])
    assert out["total_variation"] == 4.0
    assert out["net_displacement"] == 2.0
    assert np.isclose(out["roughness"], np.log(2.0))


def test_pair_decomposition_identity():
    a = path_roughness([0, 1, 0, 2])
    b = path_roughness([0, 1, 2])
    out = pair_roughness_decomposition(a, b)
    assert abs(out["identity_error"]) < 1e-12


def test_erosion_grid_attempts_exactly_25_inward_cells():
    out = erosion_roughness_ensemble(idx(), 0, 20)
    assert out["attempted_count"] == 25
    assert len(out["cells"]) == 25
    assert {(r["start_erosion_minutes"], r["end_erosion_minutes"]) for r in out["cells"]} == {(s,e) for s in range(5) for e in range(5)}
    assert all(r["start_minute"] >= 0 and r["end_minute"] <= 20 for r in out["cells"])


def test_missing_exact_shift_is_not_nearest_filled():
    index = idx(minutes=[0,1,2,4,5,6,7,8,9,10], closes=[0,1,0,2,1,3,2,4,3,5])
    out = erosion_roughness_ensemble(index, 0, 10)
    cell = next(r for r in out["cells"] if r["start_erosion_minutes"] == 3 and r["end_erosion_minutes"] == 0)
    assert cell["defined"] is False
    assert cell["reason"] == "missing_shifted_start"


def test_zero_tv_and_zero_displacement_remain_undefined():
    constant = MinutePathIndex(np.arange(8), np.ones(8))
    out = interval_roughness(constant, 0, 7)
    assert out["defined"] is False
    assert out["reason"] == "zero_total_variation"
    back = MinutePathIndex(np.arange(5), np.array([0,1,2,1,0], dtype=float))
    out2 = interval_roughness(back, 0, 4)
    assert out2["defined"] is False
    assert out2["reason"] == "zero_net_displacement"


def test_future_append_after_original_end_does_not_change_ensemble():
    a = idx(minutes=range(21))
    b = idx(minutes=range(30))
    ea = erosion_roughness_ensemble(a, 0, 20)
    eb = erosion_roughness_ensemble(b, 0, 20)
    assert ea["erosion_roughness_median"] == eb["erosion_roughness_median"]
    assert ea["erosion_roughness_range"] == eb["erosion_roughness_range"]
    assert ea["cells"] == eb["cells"]


def test_registered_candidate_requires_no_counterpart_information():
    out = erosion_roughness_ensemble(idx(), 2, 22)
    assert out["candidate"] == "single_view_inward_erosion_roughness_ensemble"
    assert "counterpart" not in repr(out)
    assert out["future_outcome_used"] is False
    assert out["trade_authority"] is False


def test_common_support_is_explicitly_audit_only():
    out = common_support_oracle(idx(), 0, 20, 2, 22)
    assert out["audit_only"] is True
    assert out["uses_counterpart_information"] is True
    assert out["common_start_minute"] == 2
    assert out["common_end_minute"] == 20


def test_boundary_sliver_diagnostics_are_descriptive_only():
    out = boundary_sliver_diagnostics(idx(), 0, 20)
    assert set(["original","left4","right4","both4"]).issubset(out)
    assert "scale_qualified" not in out
    assert out["future_outcome_used"] is False
