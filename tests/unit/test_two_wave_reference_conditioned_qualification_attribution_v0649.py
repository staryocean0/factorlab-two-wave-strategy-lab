from __future__ import annotations

import pytest

from factor_lab.visual_structure.two_wave.reference_conditioned_qualification_attribution_v0649 import (
    DiagnosticSpec,
    binary_result,
    continuous_result,
    family_decision,
    rank_probability,
)


def test_rank_probability_counts_ties_half():
    assert rank_probability([2, 2], [1, 2]) == pytest.approx(0.75)


def test_lower_direction_is_adjusted():
    spec = DiagnosticSpec("x", "f", "lower")
    row = continuous_result(spec, [1, 1, 2], [3, 4])
    assert row["rank_probability_no_gt_yes_plus_half_tie"] == 0.0
    assert row["direction_adjusted_failure_rank"] == 1.0
    assert row["strong_support"] is True


def test_binary_gap_rule():
    row = binary_result([True, True, False, True], [False, False, False, False], "path_noise")
    assert row["reference_no_incidence"] == 0.75
    assert row["incidence_difference_no_minus_yes"] == 0.75
    assert row["strong_support"] is True


def _c(strong=False):
    return {"strong_support": strong, "incidence_difference_no_minus_yes": 0.0}


def test_family_decision_single_and_diffuse():
    cont = {
        "confirmation_delay_bars": _c(),
        "completion_buffer_fraction": _c(),
        "parent_span_fraction": _c(True),
        "parent_anchor_excursion_fraction": _c(True),
        "amplitude_unit_fraction": _c(),
        "cycle_duration_ratio": _c(),
        "corresponding_leg_duration_max_ratio": _c(),
        "amplitude_ratio": _c(),
        "min_leg_efficiency": _c(),
        "max_leg_jump_share": _c(),
        "max_leg_flat_share": _c(),
        "qualified_identity_count_at_cutoff": _c(),
    }
    binary = {
        "inefficient_leg_triggered": _c(),
        "jump_dominated_leg_triggered": _c(),
        "corresponding_leg_duration_mismatch_triggered": _c(),
        "multi_identity_at_cutoff": _c(),
    }
    assert family_decision(cont, binary)["primary_attribution"] == "fragment_parent_scale"
    cont["parent_span_fraction"] = _c()
    cont["parent_anchor_excursion_fraction"] = _c()
    assert family_decision(cont, binary)["primary_attribution"] == "diffuse_or_fundamental_semantic_object_mismatch"


def test_identity_ambiguity_requires_rank_and_incidence_gap():
    cont = {
        "confirmation_delay_bars": _c(),
        "completion_buffer_fraction": _c(),
        "parent_span_fraction": _c(),
        "parent_anchor_excursion_fraction": _c(),
        "amplitude_unit_fraction": _c(),
        "cycle_duration_ratio": _c(),
        "corresponding_leg_duration_max_ratio": _c(),
        "amplitude_ratio": _c(),
        "min_leg_efficiency": _c(),
        "max_leg_jump_share": _c(),
        "max_leg_flat_share": _c(),
        "qualified_identity_count_at_cutoff": _c(True),
    }
    binary = {
        "inefficient_leg_triggered": _c(),
        "jump_dominated_leg_triggered": _c(),
        "corresponding_leg_duration_mismatch_triggered": _c(),
        "multi_identity_at_cutoff": {"strong_support": False, "incidence_difference_no_minus_yes": 0.11},
    }
    assert family_decision(cont, binary)["primary_attribution"] == "identity_ambiguity"
