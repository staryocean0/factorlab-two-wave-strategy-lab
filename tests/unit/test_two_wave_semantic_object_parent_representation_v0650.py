from factor_lab.visual_structure.two_wave.semantic_object_parent_representation_v0650 import (
    anchor_alignment,
    canonical_identity,
    frozen_decision,
    parse_human_anchors,
    rank_probability,
    summarize_alignment,
    visible_anchor_positions,
)


def test_rank_probability_exact_with_ties():
    assert rank_probability([2, 2], [1, 2]) == 0.75


def test_canonical_identity_is_reference_independent_lexicographic():
    rows = [
        {"published_raw_occurrence_bars": [3, 4, 5, 6, 7], "phase": "low"},
        {"published_raw_occurrence_bars": [1, 4, 5, 6, 8], "phase": "high"},
    ]
    assert canonical_identity(rows)["published_raw_occurrence_bars"][0] == 1


def test_visible_anchor_positions_maps_cutoff_to_95():
    assert visible_anchor_positions([100, 110, 120, 130, 140], 145) == [50, 60, 70, 80, 90]


def test_parse_human_anchors_requires_complete_valid_yes_row():
    row = {
        "two_complete_same_scale_waves": "yes",
        "p0": "10", "p1": "20", "p2": "30", "p3": "40", "p4": "50",
    }
    assert parse_human_anchors(row) == [10, 20, 30, 40, 50]
    row["p2"] = ""
    assert parse_human_anchors(row) is None


def test_anchor_alignment_exact_and_fragment():
    exact = anchor_alignment([10, 20, 30, 40, 50], [10, 20, 30, 40, 50])
    assert exact["anchor_mae_fraction"] == 0
    assert exact["interval_iou"] == 1
    assert exact["containment"] == "mutual_equal_boundaries"

    frag = anchor_alignment([20, 30, 40, 50, 60], [10, 25, 40, 55, 70])
    assert frag["containment"] == "model_inside_human"
    assert frag["span_ratio"] == 1.5


def test_summary_needs_eight_cases_for_identification():
    row = anchor_alignment([10, 20, 30, 40, 50], [10, 20, 30, 40, 50])
    assert summarize_alignment([row] * 7)["anchor_correspondence_status"] == "insufficient_frozen_human_anchor_coverage"
    assert summarize_alignment([row] * 8)["anchor_correspondence_status"] == "strong_correspondence"


def test_frozen_decision_precedence_visibility_before_other_evidence():
    alignment = {
        "anchor_correspondence_identified": True,
        "anchor_correspondence_status": "strong_boundary_mismatch",
        "median_span_ratio": 2.0,
        "containment_incidence": {"model_inside_human": 1.0},
    }
    out = frozen_decision(
        no_not_visible_incidence=0.30,
        yes_not_visible_incidence=0.00,
        right_edge_gap_rank_no_gt_yes=0.9,
        span_fraction_rank_no_lt_yes=0.9,
        alignment=alignment,
    )
    assert out["primary_category"] == "v0650_packet_window_visibility_failure"


def test_fragment_category_requires_family_support_and_human_fragment_when_identified():
    alignment = {
        "anchor_correspondence_identified": True,
        "anchor_correspondence_status": "mixed_or_indeterminate",
        "median_span_ratio": 1.5,
        "containment_incidence": {"model_inside_human": 0.75},
    }
    out = frozen_decision(
        no_not_visible_incidence=0.0,
        yes_not_visible_incidence=0.0,
        right_edge_gap_rank_no_gt_yes=0.5,
        span_fraction_rank_no_lt_yes=0.75,
        alignment=alignment,
    )
    assert out["primary_category"] == "v0650_algorithmic_parent_fragment_sizing_supported"
