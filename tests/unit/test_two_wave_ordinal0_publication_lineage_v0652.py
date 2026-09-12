from factor_lab.visual_structure.two_wave.ordinal0_publication_lineage_v0652 import (
    compare_later_valid,
    frozen_decision,
    summarize_groups,
    validate_projection_contract,
)


def valid_member(raw, pred=9, level=2, event="e", filtered=None):
    if filtered is None:
        filtered = [10, 20, 30, 40, 50]
    windows = []
    lower = pred + 1
    member_confirmation = 58
    for i in range(5):
        upper = member_confirmation if i == 4 else min(filtered[i + 1] - 1, member_confirmation)
        windows.append({
            "ordinal": i,
            "lower_bar": lower,
            "upper_bar": upper,
            "selected_raw_bar": raw[i],
            "source_predecessor_bar": pred if i == 0 else None,
        })
        lower = raw[i] + 1
    return {
        "valid": True,
        "raw_occurrence_bars": list(raw),
        "predecessor_occurrence_bar": pred,
        "member_confirmation_bar": member_confirmation,
        "windows": windows,
        "birth_level": level,
        "event_id": event,
        "reason": None,
    }


def invalid_member(reason, level=1, event="bad"):
    return {
        "valid": False,
        "reason": reason,
        "birth_level": level,
        "event_id": event,
    }


def group(members, pub_index=0, filtered=None):
    if filtered is None:
        filtered = [10, 20, 30, 40, 50]
    return {
        "ordered_members": members,
        "publishing_member": members[pub_index],
        "publishing_index": pub_index,
        "prior_invalid_count": pub_index,
        "filtered": filtered,
    }


def test_projection_contract_distinguishes_ordinal0_predecessor_source():
    row = valid_member([12, 22, 32, 42, 52])
    out = validate_projection_contract(row, [10, 20, 30, 40, 50])
    assert out["window_widths"][0] == 10
    assert out["raw_filtered_abs_displacement"] == [2, 2, 2, 2, 2]


def test_compare_later_valid_reports_first_changed_and_predecessor_change():
    a = valid_member([12, 22, 32, 42, 52], pred=9)
    b = valid_member([13, 22, 32, 42, 52], pred=8)
    out = compare_later_valid(a, b)
    assert out["rewrite"] is True
    assert out["changed_ordinals"] == [0]
    assert out["first_changed_ordinal"] == 0
    assert out["ordinal0_only"] is True
    assert out["predecessor_changed"] is True


def test_summarize_groups_counts_predecessor_invalid_before_publication():
    pub = valid_member([12, 22, 32, 42, 52], pred=9, event="pub")
    later = valid_member([13, 22, 32, 42, 52], pred=8, event="later")
    g = group([
        invalid_member("ordinal0_left_censored_no_predecessor"),
        pub,
        later,
    ], pub_index=1)
    out = summarize_groups([g])
    assert out["pre_publication_invalid"]["groups_with_predecessor_specific_prior_invalid"] == 1
    assert out["later_valid_publication_stability"]["suppressed_rewrite_comparisons"] == 1
    assert out["later_valid_publication_stability"]["first_changed_ordinal_counts"]["0"] == 1


def base_primary():
    return {
        "pre_publication_invalid": {
            "predecessor_specific_group_incidence": 0.0,
            "predecessor_specific_prior_invalid_members": 0,
            "predecessor_specific_member_share": 0.0,
        },
        "later_valid_publication_stability": {
            "groups_with_later_valid_evidence": 200,
            "rewrite_group_incidence": 0.0,
            "suppressed_rewrite_comparisons": 200,
            "per_ordinal_changed_incidence": {"0": 0.9, "1": 0.5, "2": 0.4, "3": 0.3, "4": 0.2},
            "first_changed_ordinal_incidence": {"0": 0.8, "1": 0.1, "2": 0.05, "3": 0.03, "4": 0.02},
        },
        "predecessor_change_association": {
            "predecessor_changed_comparisons": 100,
            "predecessor_same_comparisons": 100,
            "p0_change_incidence_given_predecessor_changed": 0.9,
            "p0_change_incidence_given_predecessor_same": 0.4,
        },
        "publishing_projection": {
            "per_ordinal_raw_filtered_abs_displacement": {
                "0": {"median": 6.0}, "1": {"median": 2.0}, "2": {"median": 3.0},
                "3": {"median": 2.0}, "4": {"median": 2.0},
            }
        },
    }


def test_frozen_decision_full_mechanism_requires_a_b_c_d():
    x = base_primary()
    x["pre_publication_invalid"]["predecessor_specific_group_incidence"] = 0.2
    x["later_valid_publication_stability"]["rewrite_group_incidence"] = 0.3
    out = frozen_decision(x)
    assert out["gate_a_predecessor_eligibility_bottleneck_material"] is True
    assert out["gate_b_first_valid_freeze_material"] is True
    assert out["gate_c_ordinal0_rewrite_dominant"] is True
    assert out["gate_d_predecessor_change_associated_with_p0_change"] is True
    assert out["gate_e_publishing_p0_projection_displacement_larger"] is True
    assert out["primary_category"] == "v0652_ordinal0_predecessor_first_valid_freeze_mechanism_supported"


def test_frozen_decision_structural_only_when_a_to_d_fail():
    x = base_primary()
    out = frozen_decision(x)
    assert out["gate_b_first_valid_freeze_material"] is False
    assert out["primary_category"] == "v0652_structural_ordinal0_provenance_asymmetry_not_materially_expressed"
