from factor_lab.visual_structure.two_wave.lifecycle_qualified_direction_v0707 import (
    frozen_decision,
    summarize_semantic_direction_cases,
    unanimous_case_label,
)


def clean_stage_a(rescues=3):
    return {
        "upstream_v0706_exact_reproduction": True,
        "D1_evaluated_count": 115,
        "D1_exception_count": 0,
        "v0625_evaluated_count": 115,
        "v0625_exception_count": 0,
        "publication_or_lifecycle_identity_mutation_count": 0,
        "qualification_result_mutation_count": 0,
        "future_bar_dependency_violation_count": 0,
        "future_outcome_or_trade_authority_leak_count": 0,
        "D1_decisive_override_count": 0,
        "invalid_classification_change_count": 0,
        "rescue_nonunanimous_consensus_count": 0,
        "rescue_below_frozen_margin_count": 0,
        "v0625_rescue_count": rescues,
    }


def supported_rows():
    states = [
        "range",
        "uptrend",
        "downtrend",
        "range",
        "uptrend",
        "downtrend",
        "range",
        "uptrend",
        "downtrend",
    ]
    return [
        {
            "reference_state": state,
            "D1": state,
            "v0625": state,
            "D1_publication_labels": [state],
            "v0625_publication_labels": [state],
        }
        for state in states
    ]


def stage_b_from_rows(rows):
    out = summarize_semantic_direction_cases(rows)
    out["qualified_semantic_support_reproduced"] = True
    return out


def test_unanimity_aggregation_refuses_publication_cherry_pick():
    assert unanimous_case_label(["uptrend", "uptrend"]) == "uptrend"
    assert unanimous_case_label(["uptrend", "downtrend"]) == "uncertain"
    assert unanimous_case_label(["range", "uncertain", "range"]) == "uncertain"


def test_stage_a_implementation_invalid_has_first_precedence():
    audit = clean_stage_a()
    audit["D1_exception_count"] = 1
    decision = frozen_decision(stage_a=audit, stage_b=stage_b_from_rows(supported_rows()))
    assert decision["stage_a_gates_1_to_10_pass"] is False
    assert decision["primary_category"] == "v0707_direction_interface_or_contract_invalid"


def test_mechanically_inert_challenger_has_second_precedence():
    decision = frozen_decision(stage_a=clean_stage_a(rescues=0), stage_b=None)
    assert decision["stage_a_gates_1_to_10_pass"] is True
    assert decision["stage_a_gate_11_material_expression_pass"] is False
    assert decision["primary_category"] == "v0707_v0625_challenger_not_materially_expressed"


def test_stage_b_support_drift_is_upstream_invalid_not_semantic_rejection():
    stage_b = stage_b_from_rows(supported_rows()[:-1])
    decision = frozen_decision(stage_a=clean_stage_a(), stage_b=stage_b)
    assert decision["stage_b_qualified_semantic_support_reproduced_9_of_11"] is False
    assert decision["primary_category"] == "v0707_direction_interface_or_contract_invalid"


def test_clean_nonworse_semantics_supports_development_only_transplant():
    stage_b = stage_b_from_rows(supported_rows())
    decision = frozen_decision(stage_a=clean_stage_a(), stage_b=stage_b)
    assert decision["semantic_gate_pass"] is True
    assert decision["primary_category"] == (
        "v0707_v0625_lifecycle_direction_transplant_supported_"
        "development_only_external_validation_blocked"
    )


def test_semantic_harm_rejects_transplant_without_retuning():
    rows = supported_rows()
    rows[0] = {
        **rows[0],
        "v0625": "uncertain",
        "v0625_publication_labels": ["uncertain"],
    }
    stage_b = stage_b_from_rows(rows)
    decision = frozen_decision(stage_a=clean_stage_a(), stage_b=stage_b)
    assert decision["semantic_gate_pass"] is False
    assert decision["semantic_gates"]["v0625_case_exact_not_lower_than_D1"] is False
    assert decision["semantic_gates"]["no_human_exact_decisive_D1_case_harmed"] is False
    assert decision["primary_category"] == (
        "v0707_direction_interface_clean_but_v0625_semantic_transplant_not_supported"
    )
