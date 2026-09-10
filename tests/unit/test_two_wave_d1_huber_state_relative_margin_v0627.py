from factor_lab.visual_structure.two_wave.d1_huber_state_relative_margin_v0627 import (
    RANGE_BOUNDARY_SCALE,
    RELATIVE_MARGIN_FRACTION,
    TREND_BOUNDARY_SCALE,
    state_relative_margin_pass,
    state_relative_margin_requirement,
)


def test_relative_fraction_is_frozen_twenty_percent():
    assert RELATIVE_MARGIN_FRACTION == 0.20


def test_trend_requirement_is_exactly_v0625_absolute_margin():
    assert TREND_BOUNDARY_SCALE == 0.50
    assert state_relative_margin_requirement("uptrend") == 0.10
    assert state_relative_margin_requirement("downtrend") == 0.10
    assert state_relative_margin_pass("uptrend", 0.10)
    assert state_relative_margin_pass("downtrend", 0.10)
    assert not state_relative_margin_pass("uptrend", 0.099)


def test_range_requirement_is_same_relative_fraction_of_range_scale():
    assert RANGE_BOUNDARY_SCALE == 0.15
    assert abs(state_relative_margin_requirement("range") - 0.03) < 1e-12
    assert state_relative_margin_pass("range", 0.03)
    assert not state_relative_margin_pass("range", 0.029)


def test_unsupported_state_rejected():
    try:
        state_relative_margin_requirement("uncertain")
    except ValueError:
        pass
    else:
        raise AssertionError("uncertain must not have a decisive-state margin requirement")
