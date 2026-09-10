from factor_lab.visual_structure.two_wave.d1_huber_state_relative_margin_v0627 import state_relative_margin_requirement
from factor_lab.visual_structure.two_wave.d1_cycle_band_range_rescue_v0629 import MIN_IQR_OVERLAP
from factor_lab.visual_structure.two_wave.d1_range_evidence_intersection_v0630 import d1_primary_range_evidence_intersection


def test_v0630_reuses_frozen_range_margin_and_overlap_thresholds():
    assert state_relative_margin_requirement("range") == 0.03
    assert MIN_IQR_OVERLAP == 0.50


def test_decisive_d1_is_preserved_without_range_evidence_evaluation():
    out = d1_primary_range_evidence_intersection("downtrend", [], [], 1.0)
    assert out["classification"] == "downtrend"
    assert out["v0625_classification"] == "downtrend"
    assert out["D1_decisive_overridden"] is False
    assert out["new_range_rescue_applied"] is False
    assert out["range_consensus"] is None
    assert out["range_margin_gate_pass"] is None
    assert out["cycle_band_overlap_gate_pass"] is None


def test_v0630_has_no_new_threshold_parameter_surface():
    import inspect
    sig = inspect.signature(d1_primary_range_evidence_intersection)
    assert list(sig.parameters) == [
        "d1_label", "closes", "five_occurrence_bars", "amplitude_unit_price"
    ]
