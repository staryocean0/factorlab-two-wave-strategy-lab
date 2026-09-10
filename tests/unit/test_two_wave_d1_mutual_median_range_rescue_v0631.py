from factor_lab.visual_structure.two_wave.d1_huber_state_relative_margin_v0627 import state_relative_margin_requirement
from factor_lab.visual_structure.two_wave.d1_mutual_median_range_rescue_v0631 import (
    cycle_mutual_median_containment,
    d1_primary_mutual_median_range_rescue,
    erosion_mutual_median_containment,
)


def test_v0631_reuses_frozen_range_margin():
    assert state_relative_margin_requirement("range") == 0.03


def test_identical_cycles_pass_mutual_median_containment():
    closes = [1.0, 2.0, 3.0, 2.0, 1.0, 2.0, 3.0, 2.0, 1.0]
    out = cycle_mutual_median_containment(closes, [0, 2, 4, 6, 8])
    assert out["mutual_median_containment"] is True


def test_separated_cycles_fail_mutual_median_containment():
    closes = [1.0, 2.0, 3.0, 2.0, 4.0, 10.0, 11.0, 10.0, 9.0]
    out = cycle_mutual_median_containment(closes, [0, 2, 4, 6, 8])
    assert out["mutual_median_containment"] is False


def test_degenerate_cycles_fail_closed():
    closes = [1.0] * 9
    out = cycle_mutual_median_containment(closes, [0, 2, 4, 6, 8])
    assert out["mutual_median_containment"] is False


def test_all_four_frozen_endpoint_supports_are_required():
    closes = [1.0, 1.5, 2.0, 2.5, 2.0, 1.5, 1.0, 1.5, 2.0, 2.5, 2.0, 1.5, 1.0]
    out = erosion_mutual_median_containment(closes, [0, 3, 6, 9, 12])
    assert set(out["support_mutual_median_containment"]) == {
        "full", "left_eroded_1", "right_eroded_1", "both_eroded_1"
    }
    assert out["all_supports_mutual_median_containment"] == all(out["support_mutual_median_containment"].values())


def test_decisive_d1_is_preserved_without_new_range_evidence():
    out = d1_primary_mutual_median_range_rescue("uptrend", [], [], 1.0)
    assert out["classification"] == "uptrend"
    assert out["v0625_classification"] == "uptrend"
    assert out["D1_decisive_overridden"] is False
    assert out["new_range_rescue_applied"] is False
    assert out["all_supports_mutual_median_containment"] is None


def test_v0631_has_no_new_threshold_parameter_surface():
    import inspect
    sig = inspect.signature(d1_primary_mutual_median_range_rescue)
    assert list(sig.parameters) == [
        "d1_label", "closes", "five_occurrence_bars", "amplitude_unit_price"
    ]
