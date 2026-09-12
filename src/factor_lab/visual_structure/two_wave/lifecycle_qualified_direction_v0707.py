"""Frozen v0.7.7 lifecycle-qualified direction transplant adjudication helpers."""
from __future__ import annotations

from collections import Counter
from typing import Sequence

SCHEMA = "two_wave_lifecycle_qualified_direction_transplant@0.7.7"
LABELS = ("range", "uptrend", "downtrend", "uncertain")
DECISIVE = frozenset({"range", "uptrend", "downtrend"})
EXPECTED_PUBLICATIONS = 1543
EXPECTED_V0618_QUALIFIED_PUBLICATIONS = 115
EXPECTED_SUPPORTED_CASES = 9


def _label(value: str) -> str:
    out = str(value).strip().lower()
    if out not in LABELS:
        raise ValueError(f"state outside frozen four-state vocabulary: {value!r}")
    return out


def unanimous_case_label(labels: Sequence[str]) -> str:
    """Conservative frozen aggregation over all supporting publications."""
    values = [_label(x) for x in labels]
    if not values:
        raise ValueError("at least one supporting-publication classification is required")
    return values[0] if len(set(values)) == 1 else "uncertain"


def _component_metrics(rows: Sequence[dict], key: str) -> dict:
    rows = list(rows)
    confusion = {ref: {pred: 0 for pred in LABELS} for ref in LABELS}
    exact = 0
    decisive_predictions = 0
    decisive_exact = 0
    uncertain = 0
    opposite = 0
    mixed = 0

    publication_key = f"{key}_publication_labels"
    for row in rows:
        ref = _label(row["reference_state"])
        pred = _label(row[key])
        confusion[ref][pred] += 1
        exact += int(pred == ref)
        decisive_predictions += int(pred in DECISIVE)
        decisive_exact += int(pred in DECISIVE and pred == ref)
        uncertain += int(pred == "uncertain")
        opposite += int({pred, ref} == {"uptrend", "downtrend"})
        pub_labels = [_label(x) for x in row[publication_key]]
        mixed += int(len(set(pub_labels)) > 1)

    n = len(rows)
    return {
        "supported_case_count": n,
        "exact_count": exact,
        "exact_fraction": exact / n if n else None,
        "decisive_prediction_count": decisive_predictions,
        "decisive_exact_count": decisive_exact,
        "decisive_exact_fraction_of_decisive": (
            decisive_exact / decisive_predictions if decisive_predictions else None
        ),
        "decisive_exact_fraction_of_supported": decisive_exact / n if n else None,
        "uncertain_count": uncertain,
        "uncertain_fraction": uncertain / n if n else None,
        "opposite_human_trend_conflict_count": opposite,
        "mixed_supporting_publication_classification_case_count": mixed,
        "confusion_matrix_reference_rows_model_columns": confusion,
    }


def summarize_semantic_direction_cases(rows: Sequence[dict]) -> dict:
    rows = list(rows)
    d1 = _component_metrics(rows, "D1")
    v0625 = _component_metrics(rows, "v0625")
    transitions: Counter[str] = Counter()
    harmed_decisive_d1 = 0
    for row in rows:
        ref = _label(row["reference_state"])
        d1_label = _label(row["D1"])
        v0625_label = _label(row["v0625"])
        transitions[f"{d1_label}->{v0625_label}"] += 1
        harmed_decisive_d1 += int(
            d1_label in DECISIVE and d1_label == ref and v0625_label != ref
        )
    return {
        "supported_case_count": len(rows),
        "D1": d1,
        "v0625": v0625,
        "D1_to_v0625_case_transition_counts": dict(sorted(transitions.items())),
        "human_exact_decisive_D1_harmed_case_count": harmed_decisive_d1,
    }


def stage_a_gates(audit: dict) -> dict[str, bool]:
    return {
        "upstream_v0706_exact_reproduction": bool(audit["upstream_v0706_exact_reproduction"]),
        "D1_evaluated_115_of_115_zero_exceptions": (
            int(audit["D1_evaluated_count"]) == EXPECTED_V0618_QUALIFIED_PUBLICATIONS
            and int(audit["D1_exception_count"]) == 0
        ),
        "v0625_evaluated_115_of_115_zero_exceptions": (
            int(audit["v0625_evaluated_count"]) == EXPECTED_V0618_QUALIFIED_PUBLICATIONS
            and int(audit["v0625_exception_count"]) == 0
        ),
        "publication_or_lifecycle_identity_mutation_zero": (
            int(audit["publication_or_lifecycle_identity_mutation_count"]) == 0
        ),
        "qualification_result_mutation_zero": int(audit["qualification_result_mutation_count"]) == 0,
        "future_bar_dependency_violation_zero": int(audit["future_bar_dependency_violation_count"]) == 0,
        "future_outcome_or_trade_authority_leak_zero": (
            int(audit["future_outcome_or_trade_authority_leak_count"]) == 0
        ),
        "D1_decisive_override_zero": int(audit["D1_decisive_override_count"]) == 0,
        "all_classification_changes_are_D1_uncertain_to_decisive": (
            int(audit["invalid_classification_change_count"]) == 0
        ),
        "all_rescues_have_unanimous_decisive_consensus_and_margin": (
            int(audit["rescue_nonunanimous_consensus_count"]) == 0
            and int(audit["rescue_below_frozen_margin_count"]) == 0
        ),
        "at_least_one_D1_uncertain_publication_rescued": int(audit["v0625_rescue_count"]) > 0,
    }


def semantic_gates(stage_b: dict, publication_rescue_count: int) -> dict[str, bool]:
    d1 = stage_b["D1"]
    v0625 = stage_b["v0625"]
    return {
        "v0625_case_exact_not_lower_than_D1": int(v0625["exact_count"]) >= int(d1["exact_count"]),
        "v0625_opposite_human_trend_conflicts_zero": (
            int(v0625["opposite_human_trend_conflict_count"]) == 0
        ),
        "v0625_uncertain_count_not_greater_than_D1": (
            int(v0625["uncertain_count"]) <= int(d1["uncertain_count"])
        ),
        "no_human_exact_decisive_D1_case_harmed": (
            int(stage_b["human_exact_decisive_D1_harmed_case_count"]) == 0
        ),
        "publication_level_D1_uncertainty_rescue_expressed": int(publication_rescue_count) > 0,
    }


def frozen_decision(*, stage_a: dict, stage_b: dict | None) -> dict:
    a_gates = stage_a_gates(stage_a)
    hard_stage_a_names = list(a_gates)[:10]
    hard_stage_a_pass = all(a_gates[name] for name in hard_stage_a_names)
    material_expression = bool(a_gates["at_least_one_D1_uncertain_publication_rescued"])

    stage_b_reproduced = bool(
        stage_b is not None
        and int(stage_b.get("supported_case_count", 0)) == EXPECTED_SUPPORTED_CASES
        and bool(stage_b.get("qualified_semantic_support_reproduced", False))
    )
    s_gates = None
    semantic_pass = False
    if stage_b_reproduced:
        s_gates = semantic_gates(stage_b, int(stage_a["v0625_rescue_count"]))
        semantic_pass = all(s_gates.values())

    if not hard_stage_a_pass:
        category = "v0707_direction_interface_or_contract_invalid"
    elif not material_expression:
        category = "v0707_v0625_challenger_not_materially_expressed"
    elif not stage_b_reproduced:
        # The frozen 9/11 semantic-support universe is an upstream invariant;
        # drift here is implementation/upstream invalid, not a direction loss.
        category = "v0707_direction_interface_or_contract_invalid"
    elif semantic_pass:
        category = (
            "v0707_v0625_lifecycle_direction_transplant_supported_"
            "development_only_external_validation_blocked"
        )
    else:
        category = "v0707_direction_interface_clean_but_v0625_semantic_transplant_not_supported"

    return {
        "stage_a_gates": a_gates,
        "stage_a_gates_1_to_10_pass": hard_stage_a_pass,
        "stage_a_gate_11_material_expression_pass": material_expression,
        "stage_b_qualified_semantic_support_reproduced_9_of_11": stage_b_reproduced,
        "semantic_gates": s_gates,
        "semantic_gate_pass": semantic_pass,
        "primary_category": category,
    }
