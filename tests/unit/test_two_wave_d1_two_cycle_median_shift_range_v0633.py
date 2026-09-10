from factor_lab.visual_structure.two_wave.d1_two_cycle_median_shift_range_v0633 import (
    RANGE_LOCATION_SHIFT_MAX,
    cycle_median_shift,
    erosion_cycle_median_shift,
)


def test_threshold_is_inherited_frozen_phase_tolerance():
    assert RANGE_LOCATION_SHIFT_MAX == 0.15


def test_cycle_median_shift_detects_same_location_cycles():
    closes = [10, 11, 10, 11, 10, 11, 10, 11, 10]
    out = cycle_median_shift(closes, [0,2,4,6,8], 1.0)
    assert out["normalized_cycle_median_shift"] == 0.0
    assert out["range_location_pass"]


def test_cycle_median_shift_rejects_translated_cycles():
    closes = [10,11,10,11,10, 12,13,12,13]
    out = cycle_median_shift(closes, [0,2,4,6,8], 1.0)
    assert out["normalized_cycle_median_shift"] > RANGE_LOCATION_SHIFT_MAX
    assert not out["range_location_pass"]


def test_all_four_supports_are_required():
    closes = [10.0 + (0.05 if i >= 10 else 0.0) for i in range(25)]
    out = erosion_cycle_median_shift(closes, [2,7,12,17,22], 1.0)
    assert set(out["support_range_location_pass"]) == {"full","left_eroded_1","right_eroded_1","both_eroded_1"}
