from factor_lab.visual_structure.two_wave.d1_cycle_band_range_rescue_v0629 import MIN_IQR_OVERLAP
from factor_lab.visual_structure.two_wave.d1_two_cycle_distribution_intersection_v0634 import (
    erosion_two_cycle_distribution_evidence,
)
from factor_lab.visual_structure.two_wave.d1_two_cycle_median_shift_range_v0633 import RANGE_LOCATION_SHIFT_MAX


def test_v0634_reuses_frozen_thresholds():
    assert RANGE_LOCATION_SHIFT_MAX == 0.15
    assert MIN_IQR_OVERLAP == 0.50


def test_all_four_supports_and_both_conditions_are_required():
    closes = [10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0,10.1,10.0]
    out = erosion_two_cycle_distribution_evidence(closes,[2,7,12,17,22],1.0)
    assert set(out["support_distribution_pass"]) == {"full","left_eroded_1","right_eroded_1","both_eroded_1"}
    for detail in out["support_distribution_evidence"].values():
        assert detail["joint_pass"] == (detail["location_shift_pass"] and detail["iqr_overlap_pass"])
