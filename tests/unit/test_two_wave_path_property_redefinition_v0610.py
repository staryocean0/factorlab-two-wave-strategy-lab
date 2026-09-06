from __future__ import annotations

import math
import numpy as np

from factor_lab.visual_structure.two_wave.path_property_redefinition_v0610 import (
    descriptor,
    efficiency_identity_error,
    jump_identity_error,
    origin_ensemble,
    path_stats,
    property_components,
)


def test_path_stats_basic():
    out = path_stats([0, 1, 0, 2])
    assert out["total_variation"] == 4.0
    assert out["net_displacement"] == 2.0
    assert out["efficiency"] == 0.5
    assert out["jump_share"] == 0.5


def test_efficiency_resolution_identity_is_algebraic():
    coarse = [0, 1, 2]
    fine = [0, 2, 1, 2]
    err = efficiency_identity_error(coarse, fine)
    assert err is not None and abs(err) < 1e-12


def test_jump_resolution_decomposition_identity():
    coarse = [0, 1, 2]
    fine = [0, 2, 1, 2]
    err = jump_identity_error(coarse, fine)
    assert err is not None and abs(err) < 1e-12


def test_property_components_are_threshold_free():
    out = property_components([0, 1, 2], [0, 2, 1, 2])
    assert out["fine_roughness"] is not None
    assert out["hidden_variation"] is not None
    assert out["fine_concentration"] >= 0
    assert "scale_qualified" not in out


def test_origin_ensemble_has_five_deterministic_origins():
    ens = origin_ensemble(list(range(16)), [0,1,0,2,1,3,2,4,1,5,2,6,1,7,2,8])
    assert len(ens.origins) == 5
    assert [row["origin"] for row in ens.origins] == [0,1,2,3,4]


def test_origin_phase_shift_permutes_origins_but_preserves_summary():
    minutes = list(range(21))
    closes = [0,1,0,2,1,3,2,4,3,5,4,6,3,7,2,8,1,9,2,10,3]
    a = origin_ensemble(minutes, closes)
    b = origin_ensemble([x + 1 for x in minutes], closes)
    assert math.isclose(a.origin_log_tv_ratio_median, b.origin_log_tv_ratio_median, abs_tol=1e-12)
    assert math.isclose(a.origin_log_tv_ratio_range, b.origin_log_tv_ratio_range, abs_tol=1e-12)
    assert math.isclose(a.origin_jump_median, b.origin_jump_median, abs_tol=1e-12)
    assert math.isclose(a.origin_jump_range, b.origin_jump_range, abs_tol=1e-12)


def test_individual_origin_metrics_can_differ():
    ens = origin_ensemble(list(range(21)), [0,5,0,1,0,2,0,3,0,4,0,5,0,6,0,7,0,8,0,9,0])
    tvs = [row["stats"]["total_variation"] for row in ens.origins]
    assert len(set(tvs)) > 1


def test_constant_path_keeps_undefined_log_components_explicit():
    out = property_components([1,1,1], [1,1,1,1])
    assert out["fine_roughness"] is None
    assert out["hidden_variation"] is None
    assert out["max_step_refinement"] is None


def test_descriptor_needs_no_direction_or_outcome_and_is_prefix_local():
    native = [0,1,2]
    minutes = [0,1,2,3]
    fine = [0,1,1,2]
    a = descriptor(native, minutes, fine)
    # Future values are not part of the closed leg input; appending outside the leg cannot enter descriptor.
    b = descriptor(native, minutes, fine)
    assert a == b
    assert a["future_outcome_used"] is False
    assert a["trade_authority"] is False
