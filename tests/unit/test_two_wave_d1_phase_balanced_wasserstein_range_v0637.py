import numpy as np
import pytest

from factor_lab.visual_structure.two_wave.d1_phase_balanced_wasserstein_range_v0637 import (
    LEG_MASS,
    RANGE_W1_MAX,
    _phase_balanced_cycle,
    d1_primary_phase_balanced_wasserstein_range_rescue,
    erosion_phase_balanced_cycle_wasserstein,
    phase_balanced_cycle_wasserstein_distance,
)


def test_v0637_reuses_frozen_w1_ceiling_and_equal_leg_mass():
    assert RANGE_W1_MAX == 0.15
    assert LEG_MASS == 0.5


def test_phase_balancing_gives_each_leg_half_mass_despite_duration():
    arr = np.asarray([10.0, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6], dtype=float)
    _, weights, counts = _phase_balanced_cycle(arr, 0, 4, 6)
    n1, n2 = counts
    assert (n1, n2) == (5, 3)
    assert weights[:n1].sum() == pytest.approx(0.5)
    assert weights[n1:].sum() == pytest.approx(0.5)
    assert weights.sum() == pytest.approx(1.0)


def test_phase_balanced_wasserstein_is_zero_for_matching_cycles():
    closes = [10.0, 10.5, 11.0, 10.5, 10.0, 10.5, 11.0, 10.5, 10.0]
    out = phase_balanced_cycle_wasserstein_distance(closes, [0, 2, 4, 6, 8], 1.0)
    assert out["normalized_phase_balanced_cycle_wasserstein"] == pytest.approx(0.0)
    assert out["range_w1_pass"] is True
    assert out["leg_probability_mass"] == 0.5


def test_phase_balanced_wasserstein_detects_shifted_cycle_distribution():
    closes = [10.0, 10.5, 11.0, 10.5, 10.0, 11.0, 11.5, 12.0, 11.0]
    out = phase_balanced_cycle_wasserstein_distance(closes, [0, 2, 4, 6, 8], 1.0)
    assert out["normalized_phase_balanced_cycle_wasserstein"] > RANGE_W1_MAX
    assert out["range_w1_pass"] is False


def test_all_four_endpoint_supports_are_required():
    closes = [10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0]
    out = erosion_phase_balanced_cycle_wasserstein(closes, [2,7,12,17,22], 1.0)
    assert set(out["support_range_w1_pass"]) == {"full", "left_eroded_1", "right_eroded_1", "both_eroded_1"}
    assert out["all_supports_range_w1_pass"] == all(out["support_range_w1_pass"].values())


def test_decisive_v0625_output_is_never_overridden():
    closes = [10.0,10.2,10.4,10.2,10.0,10.2,10.4,10.2,10.0]
    out = d1_primary_phase_balanced_wasserstein_range_rescue(
        "uptrend", closes, [0,2,4,6,8], 1.0
    )
    assert out["classification"] == "uptrend"
    assert out["new_range_rescue_applied"] is False
    assert out["max_normalized_phase_balanced_cycle_wasserstein"] is None
