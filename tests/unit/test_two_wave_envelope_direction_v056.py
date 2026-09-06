import pytest

from factor_lab.visual_structure.two_wave.envelope_direction_v056 import (
    NUMERIC_EPSILON,
    add_d2_to_record,
    d2_from_phase_steps,
)
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig


def test_parallel_higher_envelopes_are_uptrend():
    # same-envelope total = 0.35, other envelope = 0.40
    out = d2_from_phase_steps([0.20, 0.15, 0.40], "low")
    assert out["label"] == "uptrend"
    assert out["reason"] == "both_parent_envelopes_up"


def test_parallel_lower_envelopes_are_downtrend():
    out = d2_from_phase_steps([-0.20, -0.15, -0.40], "high")
    assert out["label"] == "downtrend"
    assert out["reason"] == "both_parent_envelopes_down"


def test_both_parent_envelopes_low_translation_are_range_even_with_local_reversal():
    # Local same-envelope path moves strongly up then down, but the complete
    # lower/upper parent envelopes do not translate over the two-wave window.
    out = d2_from_phase_steps([0.35, -0.30, 0.10], "low")
    assert out["same_envelope_total_drift"] == pytest.approx(0.05)
    assert out["label"] == "range"


def test_local_reversal_does_not_veto_coherent_parent_up_translation():
    out = d2_from_phase_steps([-0.30, 0.70, 0.35], "low")
    assert out["label"] == "uptrend"


def test_local_reversal_does_not_veto_coherent_parent_down_translation():
    out = d2_from_phase_steps([0.30, -0.70, -0.35], "high")
    assert out["label"] == "downtrend"


def test_opposite_parent_envelopes_remain_uncertain():
    out = d2_from_phase_steps([0.30, 0.20, -0.30], "low")
    assert out["label"] == "uncertain"


def test_one_clear_one_weak_parent_envelope_remains_uncertain():
    out = d2_from_phase_steps([0.20, 0.20, 0.05], "low")
    assert out["label"] == "uncertain"


def test_original_d0_false_range_counterexample_stays_downtrend():
    out = d2_from_phase_steps(
        [-0.2335380601, -0.2638717691, -0.3512174141], "low"
    )
    assert out["label"] == "downtrend"


def test_low_high_start_mapping_is_direction_symmetric():
    steps = [-0.25, 0.60, 0.30]
    low = d2_from_phase_steps(steps, "low")
    high = d2_from_phase_steps(steps, "high")
    assert low["label"] == high["label"] == "uptrend"
    assert low["upper_envelope_drift"] == high["lower_envelope_drift"]
    assert low["lower_envelope_drift"] == high["upper_envelope_drift"]


def test_exact_frozen_threshold_boundary_is_not_clear_translation():
    cfg = MaturityConfig()
    out = d2_from_phase_steps([0.10, 0.05, 0.15], "low", cfg)
    assert out["label"] == "range"
    assert out["numeric_epsilon"] == NUMERIC_EPSILON


def test_numeric_epsilon_does_not_materially_loosen_frozen_threshold():
    cfg = MaturityConfig()
    out = d2_from_phase_steps([0.10, 0.050001, 0.150001], "low", cfg)
    assert out["label"] == "uptrend"


def test_adding_d2_preserves_historical_d0_d1_and_record_id():
    record = {
        "record_id": "frozen-record",
        "timeframe": "5m_offset_0",
        "phase": "low",
        "phase_steps_in_amplitude_units": [-0.30, 0.70, 0.35],
        "scale_qualified": True,
        "classification": "uncertain",
        "direction_versions": {
            "D0": "range",
            "D0_reason": "legacy",
            "D1": "uncertain",
            "D1_reason": "phase_migration_or_conflict_not_resolved",
        },
        "selected": True,
        "overlap_suppressed_by": None,
    }
    out = add_d2_to_record(record)
    assert out["record_id"] == record["record_id"]
    assert out["direction_versions"]["D0"] == "range"
    assert out["direction_versions"]["D1"] == "uncertain"
    assert out["direction_versions"]["D2"] == "uptrend"
    assert out["classification"] == "uptrend"
    assert out["trade_authority"] is False
    assert out["future_outcome_used"] is False
