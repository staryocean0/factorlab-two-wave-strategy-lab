from factor_lab.visual_structure.two_wave.duration_geometry_decomposition_v0619 import (
    classify_rejected_reasons,
    duration_metrics,
    interpretation_category,
    local_duration_boundary_diagnostics,
)


def row(raw):
    return {"published_raw_occurrence_bars": raw}


def test_duration_metrics_are_frozen_bar_differences():
    out = duration_metrics([10, 14, 22, 27, 34])
    assert out["legs"] == [4, 8, 5, 7]
    assert out["cycles"] == [12, 12]
    assert out["min_leg"] == 4
    assert out["min_cycle"] == 12
    assert out["cycle_duration_ratio"] == 1.0


def test_reason_family_classification_is_fail_closed():
    assert classify_rejected_reasons(["short_leg", "short_cycle"])["primary_family"] == "local_duration_only"
    assert classify_rejected_reasons(["amplitude_mismatch"])["primary_family"] == "amplitude_only"
    assert classify_rejected_reasons(["confirmation_too_late"])["primary_family"] == "confirmation_only"
    assert classify_rejected_reasons(["long_cycle", "long_pair"])["primary_family"] == "long_span_only"
    mixed = classify_rejected_reasons(["short_leg", "amplitude_mismatch"])
    assert mixed["primary_family"] == "mixed_multi_family"
    assert set(mixed["involved_families"]) == {"local_duration", "amplitude"}


def test_short_leg_one_bar_boundary():
    rejected = [0, 3, 12, 20, 28]
    qualified = [0, 4, 12, 20, 28]
    out = local_duration_boundary_diagnostics(rejected, qualified, ["short_leg"])
    assert out["boundary_flags"]["short_leg_one_bar_boundary"] is True
    assert out["simple_one_bar_boundary_case"] is True


def test_short_cycle_one_bar_boundary():
    rejected = [0, 4, 11, 18, 24]
    qualified = [0, 4, 12, 18, 24]
    out = local_duration_boundary_diagnostics(rejected, qualified, ["short_cycle"])
    assert out["boundary_flags"]["short_cycle_one_bar_boundary"] is True
    assert out["simple_one_bar_boundary_case"] is True


def test_cycle_ratio_one_bar_boundary_requires_corresponding_cycles_within_one_bar():
    rejected = [0, 5, 15, 20, 46]  # cycles 15,31 => >2
    qualified = [0, 5, 15, 20, 45]  # cycles 15,30 => 2
    out = local_duration_boundary_diagnostics(rejected, qualified, ["cycle_duration_mismatch"])
    assert out["boundary_flags"]["cycle_ratio_one_bar_boundary"] is True
    assert out["simple_one_bar_boundary_case"] is True

    far = local_duration_boundary_diagnostics(
        [0, 5, 15, 20, 46],
        [0, 5, 16, 20, 44],
        ["cycle_duration_mismatch"],
    )
    assert far["boundary_flags"]["cycle_ratio_one_bar_boundary"] is False


def test_mixed_case_diagnostic_does_not_change_family_classification():
    reasons = ["short_leg", "amplitude_mismatch"]
    family = classify_rejected_reasons(reasons)
    diag = local_duration_boundary_diagnostics(
        [0, 3, 12, 20, 28], [0, 4, 12, 20, 28], reasons
    )
    assert family["primary_family"] == "mixed_multi_family"
    assert diag["simple_one_bar_boundary_case"] is True


def test_interpretation_categories_are_exactly_frozen():
    assert interpretation_category(676, 393, 361, 318) == "v0619_local_duration_boundary_sensitivity_dominant"
    assert interpretation_category(100, 50, 40, 23) == "v0619_local_duration_geometry_material_not_simple_boundary"
    assert interpretation_category(100, 49, 40, 40) == "v0619_duration_not_dominant_after_v0618"
