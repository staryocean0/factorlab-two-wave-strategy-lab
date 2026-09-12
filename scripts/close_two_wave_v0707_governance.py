#!/usr/bin/env python3
"""Close v0.7.7 governance after the authoritative formal direction transplant."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "experiments/two_wave_lifecycle_qualified_direction_v0707/RESULT.json"
ADJUDICATION_PATH = ROOT / "experiments/two_wave_lifecycle_qualified_direction_v0707/ADJUDICATION.json"
AUTHORITY_PATH = ROOT / "experiments/two_wave_m0_authority.json"
EXPECTED_CATEGORY = (
    "v0707_v0625_lifecycle_direction_transplant_supported_"
    "development_only_external_validation_blocked"
)
FORMAL_RUN = 34690335291
FORMAL_RESULT_COMMIT = "37cf51ab4b546a2ac8650f31b8dfb1deef5e2c59"
PROTOCOL_FREEZE_COMMIT = "c2fe567fec232e7bbd93614917d85f85b984dfbb"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def verify_formal_result(result: dict, adjudication: dict) -> None:
    if result["primary_category"] != EXPECTED_CATEGORY:
        raise AssertionError(f"unexpected v0707 verdict: {result['primary_category']}")
    if adjudication["primary_category"] != EXPECTED_CATEGORY:
        raise AssertionError("v0707 adjudication/result verdict mismatch")
    decision = result["frozen_decision"]
    required_true = (
        "stage_a_gates_1_to_10_pass",
        "stage_a_gate_11_material_expression_pass",
        "stage_b_qualified_semantic_support_reproduced_9_of_11",
        "semantic_gate_pass",
    )
    for key in required_true:
        if decision[key] is not True:
            raise AssertionError(f"v0707 frozen gate failed: {key}")

    stage_a = result["stage_a_direction_interface_and_contract_audit"]
    if int(stage_a["qualified_publication_universe_count"]) != 115:
        raise AssertionError("v0707 qualified direction universe drift")
    if int(stage_a["D1_evaluated_count"]) != 115 or int(stage_a["v0625_evaluated_count"]) != 115:
        raise AssertionError("v0707 direction evaluation count drift")
    if int(stage_a["D1_exception_count"]) or int(stage_a["v0625_exception_count"]):
        raise AssertionError("v0707 direction interface exception")
    for key in (
        "publication_or_lifecycle_identity_mutation_count",
        "qualification_result_mutation_count",
        "future_bar_dependency_violation_count",
        "future_outcome_or_trade_authority_leak_count",
        "D1_decisive_override_count",
        "rescue_nonunanimous_consensus_count",
        "rescue_below_frozen_margin_count",
        "invalid_classification_change_count",
    ):
        if int(stage_a[key]) != 0:
            raise AssertionError(f"v0707 Stage-A invariant drift: {key}")
    if int(stage_a["D1_uncertain_count"]) != 69:
        raise AssertionError("v0707 D1 uncertainty count drift")
    if int(stage_a["v0625_label_counts"]["uncertain"]) != 50:
        raise AssertionError("v0707 v0625 uncertainty count drift")
    if int(stage_a["v0625_rescue_count"]) != 19:
        raise AssertionError("v0707 material-expression drift")

    stage_b = result["stage_b_semantic_direction_comparison"]
    if int(stage_b["supported_case_count"]) != 9:
        raise AssertionError("v0707 supported-case count drift")
    if int(stage_b["v0618_qualified_semantic_support_cases"]) != 9:
        raise AssertionError("v0707 v0618 semantic support drift")
    if int(stage_b["semantically_supported_publication_count"]) != 11:
        raise AssertionError("v0707 supported-publication count drift")
    if int(stage_b["D1"]["exact_count"]) != 7 or int(stage_b["v0625"]["exact_count"]) != 7:
        raise AssertionError("v0707 case-level exact count drift")
    if int(stage_b["D1"]["uncertain_count"]) != 2 or int(stage_b["v0625"]["uncertain_count"]) != 2:
        raise AssertionError("v0707 case-level uncertainty drift")
    if int(stage_b["human_exact_decisive_D1_harmed_case_count"]) != 0:
        raise AssertionError("v0707 harmed an exact decisive D1 case")

    if result["negative_constraint_snapshot"]["v0647_temporal_replication"]["binding_external_validation_weakness"] is not True:
        raise AssertionError("v0647 weakness must remain binding")
    if result["negative_constraint_snapshot"]["v0648_independent_reference_calibration"]["binding_external_validation_weakness"] is not True:
        raise AssertionError("v0648 weakness must remain binding")
    if result["direction_winner"] is not None or result["active_semantic_parent_authority"] is not None:
        raise AssertionError("v0707 must not install direction or morphology authority")
    if result["morphology_acceptance"] or result["trade_authority"] or result["production_authority"]:
        raise AssertionError("v0707 must not grant morphology/trade/production authority")


def updated_authority(authority: dict, result: dict) -> dict:
    a = authority
    stage_a = result["stage_a_direction_interface_and_contract_audit"]
    stage_b = result["stage_b_semantic_direction_comparison"]
    a["schema"] = "two_wave_m0_authority@1.32"
    a["global_status"] = (
        "v0707_v0625_direction_transplant_supported_development_only_"
        "external_validation_blocked_no_direction_winner"
    )

    parent = a["component_authority"]["parent_identity"]
    parent["status"] = (
        "f3_prefix_causal_lifecycle_publication_qualification_and_direction_"
        "transplant_development_supported_external_validation_blocked"
    )
    parent["active_semantic_parent_authority"] = None
    parent["v0707_direction_supported_case_count"] = int(stage_b["supported_case_count"])
    parent["v0707_direction_semantic_gate_pass"] = bool(result["frozen_decision"]["semantic_gate_pass"])

    q = a["component_authority"]["qualification_policy"]
    q["status"] = (
        "v0706_v0618_lifecycle_publication_qualification_transplant_supported_"
        "and_preserved_through_v0707_development_only"
    )
    q["v0707_qualified_direction_publication_count"] = int(stage_a["qualified_publication_universe_count"])
    q["v0707_direction_interface_exception_count"] = int(stage_a["D1_exception_count"]) + int(stage_a["v0625_exception_count"])

    d = a["component_authority"]["parent_direction"]
    d["winner"] = None
    d["status"] = (
        "v0707_v0625_lifecycle_direction_transplant_supported_as_development_"
        "contribution_external_validation_blocked_no_winner"
    )
    d["v0707"] = {
        "formal_workflow_run": FORMAL_RUN,
        "formal_result_commit": FORMAL_RESULT_COMMIT,
        "protocol_freeze_commit": PROTOCOL_FREEZE_COMMIT,
        "qualified_publication_count": int(stage_a["qualified_publication_universe_count"]),
        "D1_uncertain_count": int(stage_a["D1_uncertain_count"]),
        "v0625_uncertain_count": int(stage_a["v0625_label_counts"]["uncertain"]),
        "v0625_rescue_count": int(stage_a["v0625_rescue_count"]),
        "supported_case_count": int(stage_b["supported_case_count"]),
        "D1_case_exact_count": int(stage_b["D1"]["exact_count"]),
        "v0625_case_exact_count": int(stage_b["v0625"]["exact_count"]),
        "D1_case_uncertain_count": int(stage_b["D1"]["uncertain_count"]),
        "v0625_case_uncertain_count": int(stage_b["v0625"]["uncertain_count"]),
        "v0625_case_semantic_advantage_over_D1": False,
        "v0647_external_validation_blocked": True,
        "v0648_external_validation_blocked": True,
        "winner_installed": False,
    }
    strongest = d["strongest_pooled_exact_contribution"]
    strongest["status"] = (
        "v0707_transplant_supported_development_contribution_"
        "external_validation_blocked_not_direction_winner"
    )
    strongest["v0707_publication_level_rescue_count"] = int(stage_a["v0625_rescue_count"])
    strongest["v0707_supported_case_exact_count"] = int(stage_b["v0625"]["exact_count"])
    strongest["v0707_supported_case_count"] = int(stage_b["supported_case_count"])
    strongest["v0707_case_semantic_advantage_over_D1"] = False

    a["f3_lifecycle_direction_transplant"] = {
        "v0707": {
            "status": "supported_development_direction_contribution_external_validation_blocked_no_winner",
            "protocol": "docs/research/TWO_WAVE_LIFECYCLE_QUALIFIED_DIRECTION_TRANSPLANT_V0707_PROTOCOL.md",
            "protocol_freeze_commit": PROTOCOL_FREEZE_COMMIT,
            "formal_workflow_run": FORMAL_RUN,
            "formal_result_commit": FORMAL_RESULT_COMMIT,
            "result": "experiments/two_wave_lifecycle_qualified_direction_v0707/RESULT.json",
            "result_card": "experiments/two_wave_lifecycle_qualified_direction_v0707/RESULT_CARD.md",
            "adjudication": "experiments/two_wave_lifecycle_qualified_direction_v0707/ADJUDICATION.json",
            "publication_count": int(result["qualification_summary"]["publication_count"]),
            "v0618_qualified_publication_count": int(stage_a["qualified_publication_universe_count"]),
            "D1_evaluated_count": int(stage_a["D1_evaluated_count"]),
            "v0625_evaluated_count": int(stage_a["v0625_evaluated_count"]),
            "direction_interface_exception_count": int(stage_a["D1_exception_count"]) + int(stage_a["v0625_exception_count"]),
            "identity_mutation_count": int(stage_a["publication_or_lifecycle_identity_mutation_count"]),
            "qualification_result_mutation_count": int(stage_a["qualification_result_mutation_count"]),
            "future_bar_dependency_violation_count": int(stage_a["future_bar_dependency_violation_count"]),
            "D1_decisive_override_count": int(stage_a["D1_decisive_override_count"]),
            "D1_uncertain_count": int(stage_a["D1_uncertain_count"]),
            "v0625_uncertain_count": int(stage_a["v0625_label_counts"]["uncertain"]),
            "v0625_rescue_count": int(stage_a["v0625_rescue_count"]),
            "v0618_qualified_semantic_support_cases": int(stage_b["v0618_qualified_semantic_support_cases"]),
            "D1_case_exact_count": int(stage_b["D1"]["exact_count"]),
            "v0625_case_exact_count": int(stage_b["v0625"]["exact_count"]),
            "D1_case_uncertain_count": int(stage_b["D1"]["uncertain_count"]),
            "v0625_case_uncertain_count": int(stage_b["v0625"]["uncertain_count"]),
            "v0625_semantic_advantage_over_D1": False,
            "v0647_external_validation_weakness_binding": True,
            "v0648_external_validation_weakness_binding": True,
            "primary_category": EXPECTED_CATEGORY,
            "direction_thresholds_changed": False,
            "qualification_changed": False,
            "publication_or_lifecycle_identity_changed": False,
            "active_parent_authority_granted": False,
            "direction_winner_installed": False,
            "morphology_acceptance_changed": False,
            "trade_authority_changed": False,
            "production_authority_changed": False,
        }
    }
    a["counteroffensive_current_breakpoint"] = (
        "direction_transplant_development_supported_external_validation_blocked_no_winner"
    )
    a["next_authorized_step"] = (
        "close the current Development direction-transplant line with v0.6.25 retained as a non-winning contribution and no parent-direction winner installed; "
        "do not open another in-sample direction rescue/tuning branch from v0.7.7. Any reopening of v0.6.25 direction authority requires a new preregistered external-validation protocol and genuinely external evidence that directly addresses both the v0.6.47 temporal-replication exact-agreement deficit and the v0.6.48 independent-reference coverage/calibration weakness without tuning on those held-out outcomes. Until such evidence exists, retain D1 only as the historical baseline and keep direction winner null."
    )
    a["no_current_direction_challenger_authorized"] = True
    a["current_parent_representation_status"] = (
        "F3_prefix_causal_lifecycle_publication_and_v0618_qualification_supported_"
        "as_development_representation_direction_authority_external_validation_blocked"
    )
    a["current_direction_transplant_status"] = (
        "v0707_complete_development_supported_semantically_neutral_to_D1_on_"
        "frozen_supported_subset_external_validation_blocked_no_winner"
    )
    shortcuts = list(a.get("forbidden_next_shortcuts", []))
    for item in (
        "install_v0625_as_direction_winner_from_v0707_development_support",
        "treat_v0707_19_publication_rescues_as_semantic_improvement_on_the_frozen_reference_subset",
        "retune_v0625_margin_or_Huber_thresholds_after_v0707",
        "ignore_v0647_temporal_replication_exact_agreement_deficit",
        "ignore_v0648_independent_reference_coverage_or_calibration_weakness",
        "open_another_in_sample_direction_rescue_branch_without_new_external_validation",
        "treat_v0707_as_morphology_trade_or_production_authority",
    ):
        if item not in shortcuts:
            shortcuts.append(item)
    a["forbidden_next_shortcuts"] = shortcuts
    return a


def append_once(path: Path, marker: str, block: str) -> None:
    text = path.read_text()
    if marker not in text:
        path.write_text(text.rstrip() + "\n\n\n" + block.strip() + "\n")


def synchronize_docs() -> None:
    append_once(
        ROOT / "README.md",
        "v0.7.7 then transplanted the historical D1 / v0.6.25 direction stack",
        """v0.7.7 then transplanted the historical D1 / v0.6.25 direction stack onto the 115 immutable v0.7.6-qualified lifecycle publications. Both components evaluated `115/115` with zero exceptions, mutations, future-bar dependencies, or D1-decisive overrides. v0.6.25 legally rescued `19` D1-uncertain publications, but on the frozen v0.6.18-qualified human-semantic subset it was neutral to D1: both were exact on `7/9` supported cases, with `2/9` uncertain and zero opposite-trend conflicts; across the 11 semantically supported publications both were exact on `8/11`. The formal verdict is **`v0707_v0625_lifecycle_direction_transplant_supported_development_only_external_validation_blocked`**. v0.6.25 is retained only as a Development contribution: v0.6.47 still favors D1 on temporal-replication exact agreement (`242/253` vs `238/253`) and v0.6.48 remains weak (`5/16` exact for both, only `16/120` reference-confirmed candidate presence). No direction winner, morphology, trade, or production authority is installed.""",
    )
    append_once(
        ROOT / "docs/INDEX.md",
        "### v0.7.7 lifecycle-qualified direction transplant — complete",
        """### v0.7.7 lifecycle-qualified direction transplant — complete

- Protocol: `research/TWO_WAVE_LIFECYCLE_QUALIFIED_DIRECTION_TRANSPLANT_V0707_PROTOCOL.md`
- Result: `../experiments/two_wave_lifecycle_qualified_direction_v0707/RESULT.json`
- Result card: `../experiments/two_wave_lifecycle_qualified_direction_v0707/RESULT_CARD.md`
- Adjudication: `../experiments/two_wave_lifecycle_qualified_direction_v0707/ADJUDICATION.json`
- Verdict: `v0707_v0625_lifecycle_direction_transplant_supported_development_only_external_validation_blocked` (`115/115` D1/v0.6.25 evaluation, zero interface/causality violations, `19` legal v0.6.25 uncertainty rescues, frozen semantic subset tied with D1 at `7/9` case exact).
- Authority: Development contribution only; no direction winner. v0.6.47 temporal replication and v0.6.48 independent-reference calibration remain binding external-validation blocks.""",
    )
    append_once(
        ROOT / "docs/research/TWO_WAVE_DIRECTION_CONTRIBUTION_LEDGER.md",
        "## v0.7.7 lifecycle-qualified direction transplant",
        """## v0.7.7 lifecycle-qualified direction transplant

- Upstream representation and v0.6.18 qualification were reproduced unchanged: `1543` publications and `115` qualified publications, with zero qualification interface exceptions or contract violations.
- D1 and v0.6.25 both evaluated all `115` qualified publications with zero exceptions, identity mutations, qualification-result mutations, future-bar dependencies, future/trade leaks, or D1-decisive overrides.
- v0.6.25 was materially expressed: it rescued `19` D1-uncertain publications (`12` DownTrend, `6` UpTrend, `1` Range) under the unchanged unanimous erosion-consensus and `0.10` margin rule.
- Frozen human semantics nevertheless showed no advantage over D1. On the `9/11` supported anchored cases, D1 and v0.6.25 were both exact `7/9`, uncertain `2/9`, and had zero opposite-trend conflicts; all 9 conservative case labels were unchanged. Across the 11 semantically supported publications both were exact `8/11`.
- Therefore v0.6.25 is retained as a **Development direction contribution**, not a direction winner.
- External constraints remain binding: v0.6.47 temporal replication exact agreement favors D1 (`242/253`) over v0.6.25 (`238/253`), while v0.6.48 independent-reference calibration remains only `5/16` exact for both with `16/120` reference-confirmed candidate presence.
- Current route: close further in-sample direction rescue/tuning. Any authority reopening requires a new preregistered external-validation design using genuinely external evidence; no morphology, trade, or production authority follows from v0.7.7.""",
    )
    append_once(
        ROOT / "docs/research/TWO_WAVE_M0_AUTHORITY.md",
        "## v0.7.7: lifecycle-qualified direction transplant — Development-supported, external-validation-blocked",
        """## v0.7.7: lifecycle-qualified direction transplant — Development-supported, external-validation-blocked

Frozen protocol: `docs/research/TWO_WAVE_LIFECYCLE_QUALIFIED_DIRECTION_TRANSPLANT_V0707_PROTOCOL.md`.  
Protocol freeze commit: `c2fe567fec232e7bbd93614917d85f85b984dfbb`.  
Authoritative formal run: `34690335291`.  
Authoritative result commit: `37cf51ab4b546a2ac8650f31b8dfb1deef5e2c59`.  
Result: `experiments/two_wave_lifecycle_qualified_direction_v0707/RESULT.json`.  
Result card: `experiments/two_wave_lifecycle_qualified_direction_v0707/RESULT_CARD.md`.  
Adjudication: `experiments/two_wave_lifecycle_qualified_direction_v0707/ADJUDICATION.json`.

The formal run reproduced the full v0.7.6 qualification universe and then evaluated D1 and v0.6.25 only on the `115` publication-prefix-qualified lifecycle publications. Both direction interfaces covered `115/115` objects with zero exceptions, publication/lifecycle mutations, qualification-result mutations, future-bar dependencies, future-outcome/trade leaks, or D1-decisive overrides. v0.6.25 was materially active, rescuing `19` D1-uncertain publications under its unchanged unanimous erosion-consensus and absolute `0.10` margin gate.

After the label-free Stage-A gates passed, the frozen human-semantic Stage B reproduced v0.6.18-qualified support in `9/11` anchored cases. The conservative all-publication case aggregation showed D1 and v0.6.25 tied at `7/9` exact, `2/9` uncertain, and zero opposite UpTrend/DownTrend conflicts; no human-exact decisive D1 case was harmed. Across the 11 semantically supported publications both components were exact `8/11`. Thus v0.6.25 is technically transplantable and materially expressed, but it did not establish a semantic advantage over D1 on the frozen Development reference subset.

The formal verdict is **`v0707_v0625_lifecycle_direction_transplant_supported_development_only_external_validation_blocked`**. The retained v0.6.47 temporal replication still favors D1 on exact agreement (`242/253` versus `238/253`), and v0.6.48 independent-reference calibration remains weak (`5/16` exact for each component with only `16/120` reference-confirmed candidate presence). These are binding external-validation constraints. Consequently v0.6.25 remains a retained Development contribution, `parent_direction.winner=null`, `active_semantic_parent_authority=null`, `morphology_acceptance=false`, `trade_authority=false`, and `production_authority=false`.

The current in-sample direction-transplant line is closed. Any future reopening of v0.6.25 direction authority requires a new preregistered external-validation protocol and genuinely external evidence that directly addresses both v0.6.47 and v0.6.48 without tuning on those held-out outcomes.""",
    )


def main() -> int:
    result = load_json(RESULT_PATH)
    adjudication = load_json(ADJUDICATION_PATH)
    verify_formal_result(result, adjudication)
    authority = updated_authority(load_json(AUTHORITY_PATH), result)
    AUTHORITY_PATH.write_text(json.dumps(authority, ensure_ascii=False, indent=2) + "\n")
    synchronize_docs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
