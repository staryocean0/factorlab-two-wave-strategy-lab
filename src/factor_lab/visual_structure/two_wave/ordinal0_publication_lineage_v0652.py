"""Aggregate-only helpers for v0.6.52 ordinal-0/publication lineage audit."""
from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Sequence

SCHEMA = "two_wave_ordinal0_publication_lineage_audit@0.6.52"
PREDECESSOR_SPECIFIC_REASONS = {
    "ordinal0_left_censored_no_predecessor",
    "predecessor_kind_not_opposite",
    "predecessor_confirmed_after_tuple_birth",
    "birth_first_node_missing_from_level",
    "birth_nodes_not_consecutive_at_level",
}


def distribution(values: Sequence[float]) -> dict:
    vals = sorted(float(x) for x in values)
    if not vals:
        return {"count": 0, "median": None, "q1": None, "q3": None}

    def quantile(p: float) -> float:
        if len(vals) == 1:
            return vals[0]
        pos = (len(vals) - 1) * p
        lo = int(pos)
        hi = min(lo + 1, len(vals) - 1)
        frac = pos - lo
        return vals[lo] * (1.0 - frac) + vals[hi] * frac

    return {
        "count": len(vals),
        "median": float(median(vals)),
        "q1": float(quantile(0.25)),
        "q3": float(quantile(0.75)),
    }


def validate_projection_contract(row: dict, filtered: Sequence[int]) -> dict:
    """Verify frozen v0.6.4 ordinal provenance on one valid evidence member."""
    if not bool(row.get("valid")):
        raise ValueError("valid evidence member required")
    raw = [int(x) for x in row["raw_occurrence_bars"]]
    filtered = [int(x) for x in filtered]
    windows = list(row["windows"])
    if len(raw) != 5 or len(filtered) != 5 or len(windows) != 5:
        raise AssertionError("five-anchor projection contract drift")
    pred = int(row["predecessor_occurrence_bar"])
    member_confirmation = int(row["member_confirmation_bar"])

    widths = []
    displacement = []
    for i, window in enumerate(windows):
        lower = int(window["lower_bar"])
        upper = int(window["upper_bar"])
        selected = int(window["selected_raw_bar"])
        if selected != raw[i]:
            raise AssertionError("window selected raw anchor drift")
        if i == 0:
            if lower != pred + 1:
                raise AssertionError("ordinal0 lower bound no longer derives from predecessor")
            if window.get("source_predecessor_bar") is None or int(window["source_predecessor_bar"]) != pred:
                raise AssertionError("ordinal0 predecessor provenance marker drift")
        else:
            if lower != raw[i - 1] + 1:
                raise AssertionError("ordinal1-4 lower bound no longer derives from previous raw anchor")
            if window.get("source_predecessor_bar") is not None:
                raise AssertionError("predecessor provenance leaked beyond ordinal0")
        expected_upper = member_confirmation if i == 4 else min(filtered[i + 1] - 1, member_confirmation)
        if upper != expected_upper:
            raise AssertionError("projection upper-bound contract drift")
        if not (lower <= selected <= upper):
            raise AssertionError("selected raw anchor outside projection window")
        widths.append(upper - lower + 1)
        displacement.append(abs(raw[i] - filtered[i]))

    return {
        "window_widths": widths,
        "raw_filtered_abs_displacement": displacement,
    }


def compare_later_valid(publishing: dict, later: dict) -> dict:
    if not bool(publishing.get("valid")) or not bool(later.get("valid")):
        raise ValueError("two valid evidence members required")
    base = [int(x) for x in publishing["raw_occurrence_bars"]]
    other = [int(x) for x in later["raw_occurrence_bars"]]
    changed = [i for i, (a, b) in enumerate(zip(base, other)) if a != b]
    pred_changed = int(publishing["predecessor_occurrence_bar"]) != int(later["predecessor_occurrence_bar"])
    return {
        "rewrite": bool(changed),
        "changed_ordinals": changed,
        "first_changed_ordinal": changed[0] if changed else None,
        "ordinal0_only": changed == [0],
        "predecessor_changed": pred_changed,
        "ordinal0_changed": 0 in changed,
    }


def summarize_groups(groups: Sequence[dict]) -> dict:
    """Summarize already reconstructed published groups without identity-level output."""
    groups = list(groups)
    prior_reason_counts: Counter[str] = Counter()
    pred_prior_group_count = 0
    prior_invalid_group_count = 0
    all_prior_invalid_members = 0
    pred_prior_invalid_members = 0

    later_valid_groups = 0
    rewrite_groups = 0
    later_comparisons = 0
    rewrite_comparisons = 0
    changed_counts = [0] * 5
    first_changed_counts = [0] * 5
    ordinal0_only = 0
    pred_changed_total = 0
    pred_changed_p0 = 0
    pred_same_total = 0
    pred_same_p0 = 0

    window_widths = [[] for _ in range(5)]
    displacement = [[] for _ in range(5)]
    spread = [[] for _ in range(5)]
    evidence_member_counts = []
    valid_member_counts = []
    publication_levels: Counter[int] = Counter()

    for group in groups:
        members = list(group["ordered_members"])
        publishing = group["publishing_member"]
        pub_index = int(group["publishing_index"])
        if publishing is None or not bool(publishing.get("valid")):
            raise AssertionError("summarized group lacks valid publishing member")
        if any(bool(x.get("valid")) for x in members[:pub_index]):
            raise AssertionError("publishing member is not first valid evidence")
        if pub_index != int(group["prior_invalid_count"]):
            raise AssertionError("prior-invalid count and first-valid index diverged")

        evidence_member_counts.append(len(members))
        valid_members = [x for x in members if bool(x.get("valid"))]
        valid_member_counts.append(len(valid_members))
        publication_levels[int(publishing["birth_level"])] += 1

        prior = members[:pub_index]
        if prior:
            prior_invalid_group_count += 1
        group_has_pred_invalid = False
        for row in prior:
            reason = str(row.get("reason"))
            prior_reason_counts[reason] += 1
            all_prior_invalid_members += 1
            if reason in PREDECESSOR_SPECIFIC_REASONS:
                pred_prior_invalid_members += 1
                group_has_pred_invalid = True
        if group_has_pred_invalid:
            pred_prior_group_count += 1

        contract = validate_projection_contract(publishing, group["filtered"])
        for i in range(5):
            window_widths[i].append(contract["window_widths"][i])
            displacement[i].append(contract["raw_filtered_abs_displacement"][i])

        if len(valid_members) >= 2:
            for i in range(5):
                vals = [int(x["raw_occurrence_bars"][i]) for x in valid_members]
                spread[i].append(max(vals) - min(vals))

        later_valid = [x for x in members[pub_index + 1 :] if bool(x.get("valid"))]
        if later_valid:
            later_valid_groups += 1
        group_rewrite = False
        for later in later_valid:
            later_comparisons += 1
            comp = compare_later_valid(publishing, later)
            if comp["predecessor_changed"]:
                pred_changed_total += 1
                pred_changed_p0 += int(comp["ordinal0_changed"])
            else:
                pred_same_total += 1
                pred_same_p0 += int(comp["ordinal0_changed"])
            if not comp["rewrite"]:
                continue
            group_rewrite = True
            rewrite_comparisons += 1
            for i in comp["changed_ordinals"]:
                changed_counts[i] += 1
            first_changed_counts[int(comp["first_changed_ordinal"])] += 1
            ordinal0_only += int(comp["ordinal0_only"])
        rewrite_groups += int(group_rewrite)

    n = len(groups)
    pred_group_inc = pred_prior_group_count / n if n else 0.0
    pred_member_share = pred_prior_invalid_members / all_prior_invalid_members if all_prior_invalid_members else 0.0
    rewrite_group_inc = rewrite_groups / later_valid_groups if later_valid_groups else 0.0
    changed_inc = [x / rewrite_comparisons if rewrite_comparisons else 0.0 for x in changed_counts]
    first_inc = [x / rewrite_comparisons if rewrite_comparisons else 0.0 for x in first_changed_counts]
    pred_changed_rate = pred_changed_p0 / pred_changed_total if pred_changed_total else None
    pred_same_rate = pred_same_p0 / pred_same_total if pred_same_total else None

    return {
        "published_groups": n,
        "evidence_member_count": distribution(evidence_member_counts),
        "valid_member_count": distribution(valid_member_counts),
        "publication_birth_level_counts": {str(k): v for k, v in sorted(publication_levels.items())},
        "pre_publication_invalid": {
            "groups_with_any_prior_invalid": prior_invalid_group_count,
            "groups_with_predecessor_specific_prior_invalid": pred_prior_group_count,
            "predecessor_specific_group_incidence": pred_group_inc,
            "all_prior_invalid_members": all_prior_invalid_members,
            "predecessor_specific_prior_invalid_members": pred_prior_invalid_members,
            "predecessor_specific_member_share": pred_member_share,
            "reason_counts": dict(sorted(prior_reason_counts.items())),
        },
        "later_valid_publication_stability": {
            "groups_with_later_valid_evidence": later_valid_groups,
            "groups_with_suppressed_rewrite": rewrite_groups,
            "rewrite_group_incidence": rewrite_group_inc,
            "later_valid_comparisons": later_comparisons,
            "suppressed_rewrite_comparisons": rewrite_comparisons,
            "ordinal0_only_rewrite_comparisons": ordinal0_only,
            "ordinal0_only_rewrite_incidence": ordinal0_only / rewrite_comparisons if rewrite_comparisons else 0.0,
            "per_ordinal_changed_counts": {str(i): changed_counts[i] for i in range(5)},
            "per_ordinal_changed_incidence": {str(i): changed_inc[i] for i in range(5)},
            "first_changed_ordinal_counts": {str(i): first_changed_counts[i] for i in range(5)},
            "first_changed_ordinal_incidence": {str(i): first_inc[i] for i in range(5)},
        },
        "predecessor_change_association": {
            "predecessor_changed_comparisons": pred_changed_total,
            "predecessor_changed_p0_changed": pred_changed_p0,
            "p0_change_incidence_given_predecessor_changed": pred_changed_rate,
            "predecessor_same_comparisons": pred_same_total,
            "predecessor_same_p0_changed": pred_same_p0,
            "p0_change_incidence_given_predecessor_same": pred_same_rate,
        },
        "publishing_projection": {
            "per_ordinal_window_width": {str(i): distribution(window_widths[i]) for i in range(5)},
            "per_ordinal_raw_filtered_abs_displacement": {str(i): distribution(displacement[i]) for i in range(5)},
        },
        "cross_valid_member_spread": {
            "groups_with_at_least_two_valid_members": sum(len([x for x in g["ordered_members"] if bool(x.get("valid"))]) >= 2 for g in groups),
            "per_ordinal_raw_occurrence_spread": {str(i): distribution(spread[i]) for i in range(5)},
        },
    }


def frozen_decision(primary: dict) -> dict:
    invalid = primary["pre_publication_invalid"]
    stability = primary["later_valid_publication_stability"]
    assoc = primary["predecessor_change_association"]
    proj = primary["publishing_projection"]["per_ordinal_raw_filtered_abs_displacement"]

    gate_a = (
        float(invalid["predecessor_specific_group_incidence"]) >= 0.10
        or (
            int(invalid["predecessor_specific_prior_invalid_members"]) >= 50
            and float(invalid["predecessor_specific_member_share"]) >= 0.50
        )
    )

    later_groups = int(stability["groups_with_later_valid_evidence"])
    gate_b_denominator_ok = later_groups >= 100
    gate_b = gate_b_denominator_ok and float(stability["rewrite_group_incidence"]) >= 0.20

    rewrite_comps = int(stability["suppressed_rewrite_comparisons"])
    p0_changed = float(stability["per_ordinal_changed_incidence"]["0"])
    max_other = max(float(stability["per_ordinal_changed_incidence"][str(i)]) for i in range(1, 5))
    first0 = float(stability["first_changed_ordinal_incidence"]["0"])
    gate_c_denominator_ok = rewrite_comps >= 100
    gate_c = gate_c_denominator_ok and first0 >= 0.70 and p0_changed - max_other >= 0.15

    pred_changed_n = int(assoc["predecessor_changed_comparisons"])
    pred_same_n = int(assoc["predecessor_same_comparisons"])
    pred_changed_rate = assoc["p0_change_incidence_given_predecessor_changed"]
    pred_same_rate = assoc["p0_change_incidence_given_predecessor_same"]
    gate_d_denominator_ok = pred_changed_n >= 50 and pred_same_n >= 50
    gate_d = bool(
        gate_d_denominator_ok
        and pred_changed_rate is not None
        and pred_same_rate is not None
        and float(pred_changed_rate) >= 0.70
        and float(pred_changed_rate) - float(pred_same_rate) >= 0.20
    )

    m0 = proj["0"]["median"]
    other_medians = [proj[str(i)]["median"] for i in range(1, 4)]
    m123 = max(float(x) for x in other_medians if x is not None) if all(x is not None for x in other_medians) else None
    gate_e = bool(m0 is not None and m123 is not None and float(m0) >= 2.0 and float(m0) >= 1.5 * m123)

    if gate_a and gate_b and gate_c and gate_d:
        category = "v0652_ordinal0_predecessor_first_valid_freeze_mechanism_supported"
    elif gate_b and gate_c:
        category = "v0652_p0_specific_first_valid_rewrite_instability_without_predecessor_change_link"
    elif gate_b:
        category = "v0652_first_valid_publication_rewrite_instability_not_ordinal0_specific"
    elif gate_a:
        category = "v0652_predecessor_support_materially_affects_publication_eligibility_only"
    else:
        category = "v0652_structural_ordinal0_provenance_asymmetry_not_materially_expressed"

    return {
        "gate_a_predecessor_eligibility_bottleneck_material": gate_a,
        "gate_b_first_valid_freeze_material": gate_b,
        "gate_b_denominator_ok": gate_b_denominator_ok,
        "gate_c_ordinal0_rewrite_dominant": gate_c,
        "gate_c_denominator_ok": gate_c_denominator_ok,
        "gate_d_predecessor_change_associated_with_p0_change": gate_d,
        "gate_d_denominator_ok": gate_d_denominator_ok,
        "gate_e_publishing_p0_projection_displacement_larger": gate_e,
        "primary_category": category,
    }
