from factor_lab.visual_structure.two_wave.cycle_drift_sign_topology_v0641 import (
    categorical_summary,
    cycle_drift_topology,
    strict_sign,
    true_rate,
)


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
