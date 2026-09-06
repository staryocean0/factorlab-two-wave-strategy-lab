from factor_lab.visual_structure.two_wave.d1_semantic_attribution_v055 import (
    diagnose_with_subtype,
    range_span_bound,
)
from factor_lab.visual_structure.two_wave.same_scale_v04 import direction_versions
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig


def _record(steps, *, phase="low", spans=None):
    cfg = MaturityConfig()
    if spans is None:
        levels = [0.0, float(steps[0]), float(steps[0] + steps[1])]
        spans = [max(levels) - min(levels), abs(float(steps[2]))]
    dv = direction_versions(list(map(float, steps)), list(map(float, spans)), cfg)
    return {
        "record_id": "synthetic",
        "timeframe": "5m_offset_0",
        "phase": phase,
        "phase_steps_in_amplitude_units": list(map(float, steps)),
        "phase_spans_in_amplitude_units": list(map(float, spans)),
        "detrended_amplitudes_price": [10.0, 12.0],
        "cycle_durations": [20, 24],
        "corresponding_leg_duration_diagnostic": {"max_ratio": 2.5},
        "direction_versions": dv,
    }


def test_range_span_gate_is_algebraically_implied_by_all_small_steps():
    proof = range_span_bound()
    assert proof["same_phase_span_upper_bound"] == 0.30
    assert proof["opposite_phase_span_upper_bound"] == 0.15
    assert proof["strong_drift_gate"] == 0.50
    assert proof["range_span_gate_implied"] is True

    row = diagnose_with_subtype(_record([0.10, -0.10, 0.05]))
    assert row["D1"] == "range"
    assert row["range_all_steps_small"] is True
    assert row["range_span_gate_pass"] is True
    assert row["uncertain_subtype"] is None


def test_low_and_high_start_envelope_mapping_is_symmetric():
    low = diagnose_with_subtype(_record([0.20, 0.30, 0.40], phase="low"))
    high = diagnose_with_subtype(_record([0.20, 0.30, 0.40], phase="high"))
    assert low["lower_envelope_drift"] == high["upper_envelope_drift"] == 0.50
    assert low["upper_envelope_drift"] == high["lower_envelope_drift"] == 0.40
    assert low["center_drift_linear_diagnostic"] == high["center_drift_linear_diagnostic"]


def test_uncertain_subtypes_are_explanations_not_relabels():
    cases = [
        ([0.30, -0.30, 0.00], "same_phase_reversal_conflict"),
        ([0.20, 0.20, -0.30], "opposite_envelope_conflict"),
        ([0.40, 0.30, -0.10], "strong_net_with_opposed_phase"),
        ([0.14, 0.14, 0.16], "coherent_but_subthreshold"),
        ([0.20, 0.00, -0.02], "single_phase_dominant"),
        ([0.25, -0.10, 0.25], "large_migration_without_coherent_direction"),
    ]
    for steps, expected in cases:
        row = diagnose_with_subtype(_record(steps))
        assert row["D1"] == "uncertain"
        assert row["uncertain_subtype"] == expected


def test_inconsistent_all_small_steps_are_flagged_as_large_migration_not_range():
    # This span is algebraically impossible for a genuine five-point record
    # whose three frozen phase steps are all within +/-0.15.  The diagnostic
    # should surface the inconsistency as large migration rather than forcing
    # it into range.  This test guards attribution semantics only; it does not
    # modify the frozen D1 classifier.
    row = diagnose_with_subtype(_record([0.10, -0.10, 0.10], spans=[0.60, 0.10]))
    assert row["D1"] == "uncertain"
    assert row["range_all_steps_small"] is True
    assert row["range_span_gate_pass"] is False
    assert row["uncertain_subtype"] == "large_migration_without_coherent_direction"


def test_diagnostics_do_not_change_frozen_direction_label():
    record = _record([0.30, 0.25, 0.20])
    frozen = record["direction_versions"]["D1"]
    row = diagnose_with_subtype(record)
    assert frozen == "uptrend"
    assert row["D1"] == frozen
    assert row["uncertain_subtype"] is None
