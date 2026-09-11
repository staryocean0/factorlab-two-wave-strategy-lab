from factor_lab.visual_structure.two_wave.leg_asymmetry_stability_v0640 import (
    greater_probability,
    leg_asymmetry,
    sign_bucket,
    sign_fractions,
)


def test_leg_asymmetry_is_first_minus_second():
    out = leg_asymmetry(
        {
            "first_leg_progress_l1": 0.20,
            "second_leg_progress_l1": 0.08,
            "first_leg_progress_linf": 0.50,
            "second_leg_progress_linf": 0.30,
        }
    )
    assert abs(out["A_L1"] - 0.12) < 1e-12
    assert abs(out["A_Linf"] - 0.20) < 1e-12
    assert out["future_outcome_used"] is False
    assert out["trade_authority"] is False


def test_leg_asymmetry_can_be_negative():
    out = leg_asymmetry(
        {
            "first_leg_progress_l1": 0.04,
            "second_leg_progress_l1": 0.10,
            "first_leg_progress_linf": 0.20,
            "second_leg_progress_linf": 0.35,
        }
    )
    assert abs(out["A_L1"] + 0.06) < 1e-12
    assert abs(out["A_Linf"] + 0.15) < 1e-12


def test_sign_bucket_uses_structural_zero_only():
    assert sign_bucket(0.1) == "positive"
    assert sign_bucket(-0.1) == "negative"
    assert sign_bucket(0.0) == "zero"
    assert sign_bucket(5e-13) == "zero"


def test_sign_fractions():
    out = sign_fractions([1.0, 2.0, -1.0, 0.0])
    assert out == {"count": 4, "positive": 0.5, "zero": 0.25, "negative": 0.25}


def test_greater_probability_with_ties():
    # P(left > right)=2/4 and P(tie)=1/4 => 0.625.
    assert greater_probability([1.0, 2.0], [1.0, 1.5]) == 0.625
