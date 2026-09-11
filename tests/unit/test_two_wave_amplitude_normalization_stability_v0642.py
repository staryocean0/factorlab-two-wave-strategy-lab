from factor_lab.visual_structure.two_wave.amplitude_normalization_stability_v0642 import (
    amplitude_metrics,
    counterfactual_crossing_attribution,
    sign_bucket,
    signed_symmetric_relative_difference,
    symmetric_relative_difference,
)


def test_symmetric_relative_difference_is_threshold_free():
    assert symmetric_relative_difference(1.0, 1.0) == 0.0
    assert abs(symmetric_relative_difference(2.0, 1.0) - 2.0 / 3.0) < 1e-12
    assert symmetric_relative_difference(0.0, 0.0) == 0.0


def test_signed_symmetric_relative_difference_keeps_orientation():
    assert signed_symmetric_relative_difference(2.0, 1.0) > 0
    assert signed_symmetric_relative_difference(1.0, 2.0) < 0
    assert signed_symmetric_relative_difference(0.0, 0.0) == 0.0


def test_amplitude_metrics_reproduce_frozen_mean_unit():
    out = amplitude_metrics([2.0, 4.0], 3.0)
    assert out["amp1_price"] == 2.0
    assert out["amp2_price"] == 4.0
    assert out["amplitude_unit_price"] == 3.0
    assert abs(out["cycle_amplitude_imbalance"] - 2.0 / 3.0) < 1e-12


def test_counterfactual_raw_only_sufficient():
    out = counterfactual_crossing_attribution(
        rescue_max_raw_w1=1.0,
        rescue_amplitude_unit=10.0,
        nonrescue_max_raw_w1=2.0,
        nonrescue_amplitude_unit=10.0,
        inherited_w1_ceiling=0.15,
    )
    assert out["attribution_category"] == "raw_numerator_change_sufficient"
    assert out["raw_only_pass"] is True
    assert out["denominator_only_pass"] is False


def test_counterfactual_denominator_only_sufficient():
    out = counterfactual_crossing_attribution(
        rescue_max_raw_w1=1.6,
        rescue_amplitude_unit=12.0,
        nonrescue_max_raw_w1=1.6,
        nonrescue_amplitude_unit=10.0,
        inherited_w1_ceiling=0.15,
    )
    assert out["attribution_category"] == "amplitude_denominator_change_sufficient"
    assert out["raw_only_pass"] is False
    assert out["denominator_only_pass"] is True


def test_counterfactual_both_changes_required():
    out = counterfactual_crossing_attribution(
        rescue_max_raw_w1=1.4,
        rescue_amplitude_unit=10.0,
        nonrescue_max_raw_w1=1.8,
        nonrescue_amplitude_unit=10.5,
        inherited_w1_ceiling=0.15,
    )
    assert out["attribution_category"] == "both_changes_required"
    assert out["raw_only_pass"] is False
    assert out["denominator_only_pass"] is False


def test_sign_bucket_uses_only_numeric_zero():
    assert sign_bucket(0.1) == "positive"
    assert sign_bucket(-0.1) == "negative"
    assert sign_bucket(0.0) == "zero"
