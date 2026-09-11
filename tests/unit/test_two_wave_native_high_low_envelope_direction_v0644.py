from factor_lab.visual_structure.two_wave.native_high_low_envelope_direction_v0644 import (
    anchor_kinds,
    envelope_anchor_metrics,
    harmless_pair_metrics,
)


def _bar(close, high, low):
    return {"close": float(close), "high": float(high), "low": float(low)}


def test_anchor_kinds_are_frozen_alternating_phase():
    assert anchor_kinds("low") == ("low", "high", "low", "high", "low")
    assert anchor_kinds("high") == ("high", "low", "high", "low", "high")


def test_low_phase_envelope_metrics_use_same_bar_low_high_extremes_only():
    bars = [
        _bar(100, 101, 99),
        _bar(110, 112, 108),
        _bar(102, 103, 100),
        _bar(113, 116, 111),
        _bar(105, 106, 102),
    ]
    out = envelope_anchor_metrics(bars, [0, 1, 2, 3, 4], "low", 10.0)
    assert out["anchor_envelope_prices"] == [99.0, 112.0, 100.0, 116.0, 102.0]
    assert out["anchor_outward_excursions"] == [0.1, 0.2, 0.2, 0.3, 0.3]
    assert out["close_phase_steps_in_amplitude_units"] == [0.2, 0.3, 0.3]
    assert out["envelope_phase_steps_in_amplitude_units"] == [0.1, 0.2, 0.4]
    assert all(
        abs(a - b) < 1e-12
        for a, b in zip(out["envelope_adjustment_vector"], [-0.1, -0.1, 0.1])
    )
    assert abs(out["mean_anchor_outward_excursion"] - 0.22) < 1e-12
    assert abs(out["envelope_adjustment_l1"] - 0.1) < 1e-12


def test_harmless_pair_metrics_positive_gain_means_envelope_more_stable():
    main = {
        "close_phase_steps_in_amplitude_units": [0.0, 0.2, -0.1],
        "envelope_phase_steps_in_amplitude_units": [0.0, 0.1, -0.1],
        "envelope_adjustment_vector": [0.0, -0.1, 0.0],
        "mean_anchor_outward_excursion": 0.2,
    }
    other = {
        "close_phase_steps_in_amplitude_units": [0.3, -0.1, 0.2],
        "envelope_phase_steps_in_amplitude_units": [0.1, 0.0, 0.0],
        "envelope_adjustment_vector": [-0.2, 0.1, -0.2],
        "mean_anchor_outward_excursion": 0.3,
    }
    out = harmless_pair_metrics(main, other)
    assert abs(out["close_step_view_distance_l1"] - 0.3) < 1e-12
    assert abs(out["envelope_step_view_distance_l1"] - 0.1) < 1e-12
    assert abs(out["envelope_stability_gain_l1"] - 0.2) < 1e-12
    assert out["envelope_stability_gain_l1"] > 0
    assert abs(out["mean_anchor_excursion_view_delta"] - 0.1) < 1e-12
    assert out["comparison_offsets_runtime_information"] is False
