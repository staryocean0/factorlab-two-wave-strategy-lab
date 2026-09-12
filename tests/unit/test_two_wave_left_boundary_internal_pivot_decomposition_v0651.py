from factor_lab.visual_structure.two_wave.left_boundary_internal_pivot_decomposition_v0651 import (
    decompose_case,
    frozen_decision,
    summarize_decomposition,
)


def test_decompose_case_exact_alignment():
    row = decompose_case([10, 20, 30, 40, 50], [10, 20, 30, 40, 50])
    assert row["raw_anchor_mae_bars"] == 0
    assert row["internal_phase_mae"] == 0
    assert row["leg_share_mae"] == 0


def test_decompose_case_rigid_translation_removes_error():
    row = decompose_case([15, 25, 35, 45, 55], [10, 20, 30, 40, 50])
    assert row["signed_anchor_displacement"] == [5.0] * 5
    assert row["boundary_offset_disagreement"] == 0
    assert row["translation_removed_anchor_mae_bars"] == 0
    assert row["translation_mae_reduction_fraction"] == 1.0
    assert row["internal_phase_mae"] == 0


def test_internal_phase_normalization_ignores_outer_translation_and_scale():
    row = decompose_case([20, 30, 40, 50, 60], [0, 20, 40, 60, 80])
    assert row["internal_phase_mae"] == 0
    assert row["leg_share_mae"] == 0


def test_left_boundary_decision_requires_internal_geometry_alignment():
    # Model starts 12 bars later, end agrees, but normalized internal phase remains aligned.
    rows = [decompose_case([12, 29, 46, 63, 80], [0, 20, 40, 60, 80]) for _ in range(11)]
    out = frozen_decision(rows)
    assert out["left_boundary_dominant"] is True
    assert out["primary_category"] == "v0651_left_boundary_definition_dominant"


def test_internal_phase_mismatch_decision():
    rows = [decompose_case([0, 10, 20, 70, 80], [0, 20, 40, 60, 80]) for _ in range(11)]
    out = frozen_decision(rows)
    assert out["internal_pivot_phase_mismatch"] is True
    assert out["primary_category"] == "v0651_internal_pivot_phase_mismatch_dominant"


def test_mixed_boundary_and_internal_mismatch_precedence():
    rows = [decompose_case([15, 25, 35, 70, 80], [0, 20, 40, 60, 80]) for _ in range(11)]
    out = frozen_decision(rows)
    assert out["internal_pivot_phase_mismatch"] is True
    assert out["mixed_boundary_and_internal_mismatch"] is True
    assert out["primary_category"] == "v0651_mixed_boundary_and_internal_pivot_mismatch"


def test_summary_is_aggregate_only():
    rows = [decompose_case([15, 25, 35, 45, 55], [10, 20, 30, 40, 50]) for _ in range(11)]
    out = summarize_decomposition(rows)
    assert out["anchored_cases"] == 11
    assert "per_anchor" in out
    assert out["boundary_asymmetry_incidence"]["equal_abs_count"] == 11
    assert "case_id" not in str(out)
