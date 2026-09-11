import pytest

from factor_lab.visual_structure.two_wave.d1_two_cycle_wasserstein_range_v0635 import (
    RANGE_W1_MAX,
    cycle_wasserstein_distance,
    d1_primary_two_cycle_wasserstein_range_rescue,
    erosion_cycle_wasserstein,
)


def test_v0635_reuses_frozen_morphology_tolerance():
    assert RANGE_W1_MAX == 0.15


def test_cycle_wasserstein_is_zero_for_matching_empirical_cycles():
    closes = [10.0, 10.5, 11.0, 10.5, 10.0, 10.5, 11.0, 10.5, 10.0]
    out = cycle_wasserstein_distance(closes, [0, 2, 4, 6, 8], 1.0)
    assert out["normalized_cycle_wasserstein"] == pytest.approx(0.0)
    assert out["range_w1_pass"] is True


def test_cycle_wasserstein_detects_shifted_cycle_distribution():
    closes = [10.0, 10.5, 11.0, 10.5, 10.0, 11.0, 11.5, 12.0, 11.0]
    out = cycle_wasserstein_distance(closes, [0, 2, 4, 6, 8], 1.0)
    assert out["normalized_cycle_wasserstein"] > RANGE_W1_MAX
    assert out["range_w1_pass"] is False


def test_all_four_endpoint_supports_are_required():
    closes = [10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0]
    out = erosion_cycle_wasserstein(closes, [2,7,12,17,22], 1.0)
    assert set(out["support_range_w1_pass"]) == {"full", "left_eroded_1", "right_eroded_1", "both_eroded_1"}
    assert out["all_supports_range_w1_pass"] == all(out["support_range_w1_pass"].values())


def test_decisive_v0625_output_is_never_overridden():
    closes = [10.0,10.2,10.4,10.2,10.0,10.2,10.4,10.2,10.0]
    out = d1_primary_two_cycle_wasserstein_range_rescue("uptrend", closes, [0,2,4,6,8], 1.0)
    assert out["classification"] == "uptrend"
    assert out["new_range_rescue_applied"] is False
