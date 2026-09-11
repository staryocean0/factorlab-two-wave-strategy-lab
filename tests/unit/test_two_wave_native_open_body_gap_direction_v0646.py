import pytest

from factor_lab.visual_structure.two_wave.native_open_body_gap_direction_v0646 import (
    anchor_kinds,
    harmless_pair_metrics,
    open_anchor_metrics,
)


def _bar(op, close):
    hi = max(op, close) + 1.0
    lo = min(op, close) - 1.0
    return {"open": float(op), "high": hi, "low": lo, "close": float(close)}


def test_anchor_kinds_are_frozen_alternating_phase():
    assert anchor_kinds("low") == ("low", "high", "low", "high", "low")
    assert anchor_kinds("high") == ("high", "low", "high", "low", "high")


def test_open_anchor_metrics_use_only_frozen_anchor_open_close_and_preceding_close():
    bars = [
        _bar(99, 99),
        _bar(101, 100),
        _bar(108, 110),
        _bar(104, 102),
        _bar(111, 113),
        _bar(106, 105),
    ]
    out = open_anchor_metrics(bars, [1, 2, 3, 4, 5], "low", 10.0)
    assert out["anchor_body_in_amplitude_units"] == [-0.1, 0.2, -0.2, 0.2, -0.1]
    assert out["anchor_oriented_body_in_amplitude_units"] == [0.1, 0.2, 0.2, 0.2, 0.1]
    assert abs(out["mean_abs_anchor_body"] - 0.16) < 1e-12
    assert abs(out["mean_oriented_anchor_body"] - 0.16) < 1e-12
    assert out["positive_oriented_body_fraction"] == 1.0
    assert out["anchor_gap_in_amplitude_units"] == [0.2, 0.8, -0.6, 0.9, -0.7]
    assert abs(out["mean_abs_anchor_gap"] - 0.64) < 1e-12
    assert out["close_phase_steps_in_amplitude_units"] == [0.2, 0.3, 0.3]
    assert out["open_phase_steps_in_amplitude_units"] == [0.3, 0.2, 0.3]
    assert abs(out["open_adjustment_l1"] - (0.2 / 3.0)) < 1e-12


def test_anchor_zero_fails_closed_because_gap_needs_preceding_row():
    bars = [_bar(100, 100) for _ in range(5)]
    with pytest.raises(ValueError, match="preceding observed row"):
        open_anchor_metrics(bars, [0, 1, 2, 3, 4], "low", 10.0)


def test_harmless_pair_metrics_positive_gain_means_open_steps_more_stable():
    main = {
        "close_phase_steps_in_amplitude_units": [0.0, 0.2, -0.1],
        "open_phase_steps_in_amplitude_units": [0.0, 0.1, -0.1],
        "open_adjustment_vector": [0.0, -0.1, 0.0],
        "mean_abs_anchor_body": 0.2,
        "mean_oriented_anchor_body": 0.1,
        "mean_abs_anchor_gap": 0.3,
    }
    other = {
        "close_phase_steps_in_amplitude_units": [0.3, -0.1, 0.2],
        "open_phase_steps_in_amplitude_units": [0.1, 0.0, 0.0],
        "open_adjustment_vector": [-0.2, 0.1, -0.2],
        "mean_abs_anchor_body": 0.3,
        "mean_oriented_anchor_body": -0.1,
        "mean_abs_anchor_gap": 0.5,
    }
    out = harmless_pair_metrics(main, other)
    assert abs(out["close_step_view_distance_l1"] - 0.3) < 1e-12
    assert abs(out["open_step_view_distance_l1"] - 0.1) < 1e-12
    assert abs(out["open_stability_gain_l1"] - 0.2) < 1e-12
    assert abs(out["open_adjustment_view_distance_l1"] - 0.2) < 1e-12
    assert abs(out["mean_abs_body_view_delta"] - 0.1) < 1e-12
    assert abs(out["mean_oriented_body_view_delta"] - 0.2) < 1e-12
    assert abs(out["mean_abs_gap_view_delta"] - 0.2) < 1e-12
    assert out["comparison_offsets_runtime_information"] is False
