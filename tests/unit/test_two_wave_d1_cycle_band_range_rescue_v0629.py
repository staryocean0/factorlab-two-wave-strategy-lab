from factor_lab.visual_structure.two_wave.d1_cycle_band_range_rescue_v0629 import (
    MIN_IQR_OVERLAP,
    cycle_iqr_overlap,
    d1_primary_cycle_band_range_rescue,
)


def test_v0629_frozen_overlap_threshold():
    assert MIN_IQR_OVERLAP == 0.50


def test_identical_cycle_occupancy_bands_have_full_overlap():
    closes = [1.0, 2.0, 3.0, 2.0, 1.0, 2.0, 3.0, 2.0, 1.0]
    out = cycle_iqr_overlap(closes, [0, 2, 4, 6, 8])
    assert out["iqr_overlap_coefficient"] == 1.0


def test_separated_cycle_occupancy_bands_have_zero_overlap():
    closes = [1.0, 2.0, 3.0, 2.0, 4.0, 10.0, 11.0, 10.0, 9.0]
    out = cycle_iqr_overlap(closes, [0, 2, 4, 6, 8])
    assert out["iqr_overlap_coefficient"] == 0.0


def test_degenerate_iqr_fails_closed():
    closes = [1.0] * 9
    out = cycle_iqr_overlap(closes, [0, 2, 4, 6, 8])
    assert out["iqr_overlap_coefficient"] == 0.0


def test_decisive_d1_is_never_overridden_or_even_band_checked():
    out = d1_primary_cycle_band_range_rescue("uptrend", [], [], 1.0)
    assert out["classification"] == "uptrend"
    assert out["v0625_classification"] == "uptrend"
    assert out["new_range_rescue_applied"] is False
    assert out["cycle_band_checked"] is False
    assert out["D1_decisive_overridden"] is False
