from factor_lab.visual_structure.two_wave.w1_residual_attribution_v0636 import (
    margin_authorized,
    semantic_class,
    summarize_slacks,
)


def test_semantic_classes_are_frozen():
    assert semantic_class(("uncertain", "uncertain"), ("range", "uncertain")) == "introduced_harm"
    assert semantic_class(("range", "uncertain"), ("range", "range")) == "repaired_old_nonexact"
    assert semantic_class(("uptrend", "uncertain"), ("uptrend", "range")) == "persistent_nonexact"
    assert semantic_class(("range", "range"), ("range", "range")) == "retained_exact"


def test_slack_summary_uses_frozen_boundary():
    out = summarize_slacks([0.01, 0.02, 0.04, 0.05])
    assert out["count"] == 4
    assert out["fraction_le_0_03"] == 0.5


def test_margin_gate_fails_closed_on_small_repair_group():
    stats = {
        "introduced_harm": {"count": 20, "median": 0.01, "fraction_le_0_03": 0.8},
        "repaired_old_nonexact": {"count": 19, "median": 0.05, "fraction_le_0_03": 0.3},
    }
    ok, gates = margin_authorized(stats)
    assert ok is False
    assert gates["repaired_n_at_least_20"] is False


def test_margin_gate_requires_all_frozen_conditions():
    stats = {
        "introduced_harm": {"count": 25, "median": 0.01, "fraction_le_0_03": 0.72},
        "repaired_old_nonexact": {"count": 22, "median": 0.05, "fraction_le_0_03": 0.35},
    }
    ok, gates = margin_authorized(stats)
    assert ok is True
    assert all(gates.values())
