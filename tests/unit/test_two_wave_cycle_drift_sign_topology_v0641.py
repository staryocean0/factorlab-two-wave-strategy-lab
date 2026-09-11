from factor_lab.visual_structure.two_wave.cycle_drift_sign_topology_v0641 import (
    categorical_summary,
    cycle_drift_topology,
    reconstruct_phase_steps,
    strict_sign,
    true_rate,
)


def test_reconstruct_phase_steps_matches_frozen_d1_formula():
    closes = [100.0, 105.0, 110.0, 107.0, 104.0, 109.0, 115.0, 112.0, 109.0]
    out = reconstruct_phase_steps(closes, [0, 2, 4, 6, 8])
    unit = (8.0 + 8.5) / 2.0
    expected = [4.0 / unit, 5.0 / unit, 5.0 / unit]
    assert all(abs(a - b) < 1e-12 for a, b in zip(out, expected))


def test_reconstruct_phase_steps_uses_only_published_pivot_closes():
    anchors = [0, 2, 4, 6, 8]
    base = [100.0, 999.0, 110.0, -999.0, 104.0, 999.0, 115.0, -999.0, 109.0]
    altered = [100.0, -123.0, 110.0, 456.0, 104.0, -789.0, 115.0, 321.0, 109.0]
    assert reconstruct_phase_steps(base, anchors) == reconstruct_phase_steps(altered, anchors)


def test_strict_sign_uses_only_structural_zero():
    assert strict_sign(0.3) == "positive"
    assert strict_sign(-0.3) == "negative"
    assert strict_sign(0.0) == "zero"
    assert strict_sign(5e-13) == "zero"


def test_same_direction_all_three():
    out = cycle_drift_topology([0.01, 0.02, 0.03])
    assert out["cycle_drift_relation"] == "same_direction"
    assert out["all_three_same_direction"] is True
    assert out["opposite_envelope_agrees_when_cycles_coherent"] is True


def test_same_cycle_direction_but_opposite_envelope_disagrees():
    out = cycle_drift_topology([-0.01, -0.02, 0.03])
    assert out["cycle_drift_relation"] == "same_direction"
    assert out["all_three_same_direction"] is False
    assert out["opposite_envelope_agrees_when_cycles_coherent"] is False


def test_opposite_cycle_drifts_have_no_envelope_agreement_state():
    out = cycle_drift_topology([0.01, -0.02, 0.03])
    assert out["cycle_drift_relation"] == "opposite_direction"
    assert out["all_three_same_direction"] is False
    assert out["opposite_envelope_agrees_when_cycles_coherent"] is None


def test_zero_cycle_drift_is_structural_contains_zero():
    out = cycle_drift_topology([0.0, 0.02, 0.03])
    assert out["cycle_drift_relation"] == "contains_zero"


def test_summaries():
    out = categorical_summary(["a", "a", "b"])
    assert out["count"] == 3
    assert out["counts"] == {"a": 2, "b": 1}
    assert abs(out["rates"]["a"] - 2 / 3) < 1e-12
    assert true_rate([True, False, True]) == 2 / 3
