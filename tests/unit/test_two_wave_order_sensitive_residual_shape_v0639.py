import numpy as np
import pytest

from factor_lab.visual_structure.two_wave.order_sensitive_residual_shape_v0639 import (
    GRID_POINTS_PER_LEG,
    harm_greater_probability,
    numeric_summary,
    phase_progress_curve,
    progress_shape_descriptors,
)


def test_progress_curve_removes_level_scale_and_direction():
    up = phase_progress_curve([10.0, 11.0, 12.0])
    shifted_scaled_up = phase_progress_curve([30.0, 32.0, 34.0])
    down = phase_progress_curve([12.0, 11.0, 10.0])
    assert len(up) == GRID_POINTS_PER_LEG == 65
    assert np.allclose(up, shifted_scaled_up)
    assert np.allclose(up, down)
    assert up[0] == pytest.approx(0.0)
    assert up[-1] == pytest.approx(1.0)


def test_progress_curve_preserves_within_leg_order_shape():
    linear = phase_progress_curve([0.0, 0.5, 1.0])
    front_loaded = phase_progress_curve([0.0, 0.9, 1.0])
    assert np.mean(np.abs(linear - front_loaded)) > 0.0
    assert np.max(np.abs(linear - front_loaded)) > 0.0


def test_descriptor_is_zero_for_matching_cycle_shapes_despite_translation_and_scale():
    closes = [
        10.0, 10.5, 11.0,
        10.5, 10.0,
        20.0, 21.0, 22.0,
        21.0, 20.0,
    ]
    out = progress_shape_descriptors(closes, [0, 2, 4, 7, 9])
    for key in (
        "first_leg_progress_l1",
        "second_leg_progress_l1",
        "first_leg_progress_linf",
        "second_leg_progress_linf",
        "mean_leg_progress_l1",
        "max_leg_progress_l1",
        "mean_leg_progress_linf",
        "max_leg_progress_linf",
    ):
        assert out[key] == pytest.approx(0.0)


def test_descriptor_detects_shape_difference_without_using_absolute_translation():
    closes = [
        0.0, 0.5, 1.0,
        0.5, 0.0,
        10.0, 11.8, 12.0,
        11.0, 10.0,
    ]
    out = progress_shape_descriptors(closes, [0, 2, 4, 7, 9])
    assert out["first_leg_progress_l1"] > 0.0
    assert out["first_leg_progress_linf"] > 0.0


def test_numeric_summary_and_rank_probability_are_threshold_free():
    s = numeric_summary([1.0, 2.0, 3.0, 4.0])
    assert s["count"] == 4
    assert s["median"] == pytest.approx(2.5)
    assert harm_greater_probability([3.0, 4.0], [1.0, 2.0]) == pytest.approx(1.0)
    assert harm_greater_probability([1.0, 2.0], [3.0, 4.0]) == pytest.approx(0.0)
    assert harm_greater_probability([1.0], [1.0]) == pytest.approx(0.5)


def test_zero_displacement_leg_is_rejected():
    with pytest.raises(ValueError):
        phase_progress_curve([1.0, 1.0, 1.0])
