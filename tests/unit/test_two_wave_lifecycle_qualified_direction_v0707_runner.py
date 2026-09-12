from scripts.run_two_wave_lifecycle_qualified_direction_v0707_formal import (
    authoritative_v0706_supported,
)


def authoritative_result():
    return {
        "primary_category": "v0706_v0618_lifecycle_qualification_transplant_supported",
        "required_upstream_replication": {"published_lifecycle_object_count": 1543},
        "interface_audit": {"v054_exception_count": 0, "v0618_exception_count": 0},
        "qualification_summary": {
            "contract_violation_count": 0,
            "v0618": {"qualified_count": 115},
        },
        "semantic_transplant": {"v0618_qualified_semantic_support_cases": 9},
        "frozen_decision": {
            "interface_gate_passed": True,
            "v0618_contract_gate_passed": True,
            "semantic_support_gate_passed": True,
            "upstream_replication_ok": True,
        },
    }


def test_authoritative_v0706_gate_names_are_exact():
    result = authoritative_result()
    assert authoritative_v0706_supported(result) is True
    result["frozen_decision"]["semantic_support_gate_passed"] = False
    assert authoritative_v0706_supported(result) is False


def test_missing_or_invented_authority_field_cannot_pass():
    result = authoritative_result()
    del result["frozen_decision"]["upstream_replication_ok"]
    result["frozen_decision"]["qualification_transplant_supported"] = True
    assert authoritative_v0706_supported(result) is False
