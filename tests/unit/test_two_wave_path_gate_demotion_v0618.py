from factor_lab.visual_structure.two_wave.path_gate_demotion_v0618 import (
    DEMOTED_PATH_REASONS,
    requalify_v066_control,
    v0618_hard_reasons,
)


def control(reasons):
    return {
        "schema": "two_wave_published_identity_qualification@0.6.6",
        "v054_hard_rejection_reasons": list(reasons),
        "scale_qualified": not reasons,
        "leg_efficiencies": [0.4, 0.8, 0.9, 0.7],
        "leg_jump_shares": [0.2, 0.6, 0.1, 0.3],
        "leg_flat_shares": [0.0, 0.0, 0.0, 0.0],
        "future_outcome_used": False,
        "trade_authority": False,
    }


def test_registered_demotions_are_exact():
    assert DEMOTED_PATH_REASONS == {"inefficient_leg", "jump_dominated_leg"}
    reasons = [
        "short_leg",
        "inefficient_leg",
        "jump_dominated_leg",
        "amplitude_mismatch",
        "confirmation_too_late",
    ]
    assert v0618_hard_reasons(reasons) == [
        "short_leg",
        "amplitude_mismatch",
        "confirmation_too_late",
    ]


def test_path_only_rejection_becomes_qualified_and_diagnostics_survive():
    out = requalify_v066_control(control(["inefficient_leg", "jump_dominated_leg"]))
    assert out["scale_qualified"] is True
    assert out["v0618_hard_rejection_reasons"] == []
    assert out["demoted_path_diagnostics"] == {
        "inefficient_leg": True,
        "jump_dominated_leg": True,
    }
    assert out["leg_efficiencies"] == [0.4, 0.8, 0.9, 0.7]
    assert out["leg_jump_shares"] == [0.2, 0.6, 0.1, 0.3]


def test_mixed_path_and_nonpath_rejection_remains_rejected():
    out = requalify_v066_control(
        control(["inefficient_leg", "short_cycle", "jump_dominated_leg", "amplitude_mismatch"])
    )
    assert out["scale_qualified"] is False
    assert out["v0618_hard_rejection_reasons"] == ["short_cycle", "amplitude_mismatch"]


def test_already_qualified_remains_qualified():
    out = requalify_v066_control(control([]))
    assert out["scale_qualified"] is True
    assert out["v0618_hard_rejection_reasons"] == []
    assert out["demoted_path_reason_count"] == 0


def test_nonpath_only_rejection_is_byte_semantically_unchanged():
    reasons = [
        "short_leg",
        "short_cycle",
        "long_cycle",
        "long_pair",
        "cycle_duration_mismatch",
        "invalid_amplitude",
        "amplitude_mismatch",
        "flat_dominated_leg",
        "too_many_observed_days",
        "wall_span_too_long",
        "confirmation_too_late",
    ]
    out = requalify_v066_control(control(reasons))
    assert out["v0618_hard_rejection_reasons"] == reasons
    assert out["scale_qualified"] is False


def test_no_outcome_or_trade_authority_can_be_introduced():
    row = control(["inefficient_leg"])
    row["future_outcome_used"] = True
    row["trade_authority"] = True
    out = requalify_v066_control(row)
    assert out["future_outcome_used"] is False
    assert out["trade_authority"] is False
