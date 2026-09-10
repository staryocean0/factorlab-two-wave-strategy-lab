from factor_lab.visual_structure.two_wave.one_bar_duration_repair_v0620 import (
    requalify_v0618,
    v0620_hard_reasons,
)


def control(reasons):
    return {
        "schema": "two_wave_path_gate_demotion@0.6.18",
        "v0618_hard_rejection_reasons": list(reasons),
        "scale_qualified": not bool(reasons),
        "future_outcome_used": False,
        "trade_authority": False,
    }


def test_exact_min_leg_three_is_the_only_short_leg_demotion():
    new, diag = v0620_hard_reasons(["short_leg"], [0, 3, 12, 20, 28])
    assert new == []
    assert diag["min_leg"] == 3
    assert diag["short_leg_exact_one_bar_boundary_demoted"] is True

    new2, diag2 = v0620_hard_reasons(["short_leg"], [0, 2, 12, 20, 28])
    assert new2 == ["short_leg"]
    assert diag2["min_leg"] == 2
    assert diag2["short_leg_exact_one_bar_boundary_demoted"] is False


def test_exact_min_cycle_eleven_is_the_only_short_cycle_demotion():
    new, diag = v0620_hard_reasons(["short_cycle"], [0, 4, 11, 18, 24])
    assert new == []
    assert diag["min_cycle"] == 11
    assert diag["short_cycle_exact_one_bar_boundary_demoted"] is True

    new2, diag2 = v0620_hard_reasons(["short_cycle"], [0, 4, 10, 18, 24])
    assert new2 == ["short_cycle"]
    assert diag2["min_cycle"] == 10
    assert diag2["short_cycle_exact_one_bar_boundary_demoted"] is False


def test_other_hard_reasons_are_never_removed():
    reasons = [
        "short_leg",
        "short_cycle",
        "cycle_duration_mismatch",
        "amplitude_mismatch",
        "confirmation_too_late",
        "long_cycle",
        "long_pair",
        "too_many_observed_days",
        "wall_span_too_long",
    ]
    # min_leg=3 and min_cycle=11: only the two exact boundary reasons may disappear.
    new, _ = v0620_hard_reasons(reasons, [0, 3, 11, 18, 24])
    assert new == [
        "cycle_duration_mismatch",
        "amplitude_mismatch",
        "confirmation_too_late",
        "long_cycle",
        "long_pair",
        "too_many_observed_days",
        "wall_span_too_long",
    ]


def test_requalification_is_monotone_and_preserves_safety():
    out = requalify_v0618(
        control(["short_leg", "long_pair"]),
        [0, 3, 12, 20, 28],
    )
    assert out["v0620_hard_rejection_reasons"] == ["long_pair"]
    assert out["scale_qualified"] is False


def test_exact_boundary_can_rescue_when_it_is_the_only_reason():
    out = requalify_v0618(control(["short_cycle"]), [0, 4, 11, 18, 24])
    assert out["v0620_hard_rejection_reasons"] == []
    assert out["scale_qualified"] is True
    assert out["future_outcome_used"] is False
    assert out["trade_authority"] is False


def test_already_qualified_v0618_stays_qualified():
    out = requalify_v0618(control([]), [0, 4, 12, 20, 28])
    assert out["scale_qualified"] is True
    assert out["v0620_hard_rejection_reasons"] == []


def test_cycle_ratio_reason_is_never_demoted_even_if_duration_edges_move():
    out = requalify_v0618(
        control(["short_cycle", "cycle_duration_mismatch"]),
        [0, 4, 11, 18, 40],
    )
    assert "cycle_duration_mismatch" in out["v0620_hard_rejection_reasons"]
    assert out["scale_qualified"] is False
