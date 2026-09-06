from __future__ import annotations

from factor_lab.visual_structure.two_wave.path_metric_resolution_response_v069 import (
    duration_bin,
    path_metrics,
    resolution_response,
    threshold_transition,
)


def test_native_metric_formula():
    out = path_metrics([0, 1, 0, 2])
    assert out["total_variation"] == 4.0
    assert out["net_displacement"] == 2.0
    assert out["efficiency"] == 0.5
    assert out["jump_share"] == 0.5


def test_nested_refinement_tv_monotone_and_efficiency_nonincrease():
    out = resolution_response([0, 0, 0], [0, 2, 0, 2, 0])
    assert out["tv_monotonicity_holds"] is True
    assert out["efficiency_nonincrease_holds"] is True


def test_fine_path_not_identified_by_coarse_endpoints():
    a = path_metrics([0, 1, 2])
    b = path_metrics([0, 3, -1, 2])
    assert a["net_displacement"] == b["net_displacement"]
    assert a["total_variation"] != b["total_variation"]


def test_jump_share_is_not_assumed_monotone():
    # coarse net move cancels a large fine excursion; fine jump share can differ either way.
    out = resolution_response([0, 1, 0], [0, 4, 1, 0])
    assert isinstance(out["jump_share_delta"], float)


def test_constant_path_convention():
    out = path_metrics([1, 1, 1])
    assert out["efficiency"] == 0.0
    assert out["jump_share"] == 1.0
    assert out["flat_share"] == 1.0


def test_frozen_threshold_transition_labels():
    assert threshold_transition(0.6, 0.4, metric="efficiency") == "pass->fail"
    assert threshold_transition(0.6, 0.4, metric="jump_share") == "fail->pass"


def test_duration_bins_are_frozen():
    assert duration_bin(3) == "1-3"
    assert duration_bin(4) == "4-5"
    assert duration_bin(7) == "6-11"
    assert duration_bin(15) == "12-23"
    assert duration_bin(24) == "24+"
