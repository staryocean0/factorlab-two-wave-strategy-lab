from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

V0708_CATEGORY = "v0708_external_validation_evidence_gap_no_candidate_opened"
AUTHORITY_SCHEMA = "two_wave_m0_authority@1.33"
GLOBAL_STATUS = "v0708_external_validation_evidence_gap_no_candidate_opened_no_direction_winner"

V0708_AUDIT_DOC = "docs/research/TWO_WAVE_EXTERNAL_VALIDATION_EVIDENCE_AVAILABILITY_V0708.md"
V0708_ADJUDICATION = "experiments/two_wave_external_validation_availability_v0708/ADJUDICATION.json"

REQUIRED_REOPENING_TRIGGERS = (
    "genuinely_new_temporal_sample_not_previously_consumed_by_v0647_or_later_validation",
    "independently_frozen_two_wave_morphology_reference_labels_created_before_model_scoring",
)

FORBIDDEN_V0708_SHORTCUTS = (
    "reuse_v0647_consumed_data_as_new_external_evidence",
    "treat_same_datahub_snapshot_copy_as_independent_temporal_evidence",
    "use_non_morphology_annotations_as_two_wave_reference_labels",
    "open_direction_candidate_before_v0708_trigger_A_and_B",
    "retune_v0625_or_D1_without_new_external_protocol",
    "promote_v0707_to_direction_winner_without_new_external_evidence",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_v0708_adjudication(adjudication: Mapping[str, Any]) -> None:
    _require(adjudication.get("primary_category") == V0708_CATEGORY, "unexpected v0708 category")
    _require(int(adjudication.get("connected_repository_count", -1)) == 7, "v0708 repository census drift")

    eligibility = adjudication.get("eligibility", {})
    _require(eligibility.get("new_temporal_evidence_available") is False, "v0708 temporal evidence unexpectedly available")
    _require(eligibility.get("new_independent_reference_label_evidence_available") is False, "v0708 label evidence unexpectedly available")
    _require(eligibility.get("both_reopening_requirements_satisfied") is False, "v0708 must remain blocked")

    actions = adjudication.get("actions_frozen", {})
    for key in (
        "candidate_identity_frozen",
        "external_validation_protocol_opened",
        "direction_scoring_opened",
        "threshold_change_opened",
        "result_opened",
    ):
        _require(actions.get(key) is False, f"v0708 action must remain closed: {key}")

    authority = adjudication.get("authority", {})
    _require(authority.get("parent_direction_winner") is None, "v0708 cannot install a direction winner")
    for key in ("morphology_acceptance", "trade_authority", "production_authority"):
        _require(authority.get(key) is False, f"v0708 cannot grant {key}")


def updated_authority(current: Mapping[str, Any], adjudication: Mapping[str, Any]) -> dict[str, Any]:
    verify_v0708_adjudication(adjudication)
    out = deepcopy(dict(current))

    out["schema"] = AUTHORITY_SCHEMA
    out["global_status"] = GLOBAL_STATUS
    out["morphology_acceptance"] = False

    component_authority = out.setdefault("component_authority", {})
    parent = component_authority.setdefault("parent_identity", {})
    parent["status"] = (
        "f3_prefix_causal_lifecycle_publication_qualification_direction_transplant_"
        "development_supported_external_validation_evidence_gap"
    )
    parent["active_semantic_parent_authority"] = None

    direction = component_authority.setdefault("parent_direction", {})
    direction["winner"] = None
    direction["status"] = (
        "v0707_development_direction_transplant_retained_"
        "v0708_external_validation_evidence_gap_no_winner"
    )

    retention = out.setdefault("counteroffensive_component_retention", {})
    retention["direction_D1_v0625"] = (
        "v0707_transplant_supported_development_only_external_validation_blocked_no_winner"
    )

    out["external_validation_availability"] = {
        "v0708": {
            "status": "evidence_gap_no_candidate_opened",
            "audit": V0708_AUDIT_DOC,
            "adjudication": V0708_ADJUDICATION,
            "connected_repository_count": int(adjudication["connected_repository_count"]),
            "new_temporal_evidence_available": False,
            "new_independent_reference_label_evidence_available": False,
            "both_reopening_requirements_satisfied": False,
            "candidate_opened": False,
            "external_validation_protocol_opened": False,
            "direction_scoring_opened": False,
            "threshold_change_opened": False,
            "required_reopening_triggers": list(REQUIRED_REOPENING_TRIGGERS),
            "primary_category": V0708_CATEGORY,
        }
    }

    out["counteroffensive_current_breakpoint"] = "external_validation_evidence_gap_no_candidate_opened"
    out["current_parent_representation_status"] = (
        "F3_prefix_causal_lifecycle_publication_v0618_qualification_and_v0707_direction_"
        "transplant_supported_as_development_only_external_validation_evidence_gap"
    )
    out["current_direction_transplant_status"] = (
        "v0707_complete_development_supported_v0708_external_validation_evidence_gap_no_winner"
    )
    out["next_authorized_step"] = (
        "Do not open another in-sample direction challenger or retune D1/v0.6.25. Reopen direction authority only under a new preregistered external-validation protocol after BOTH: "
        "(A) genuinely new CSI1000 temporal evidence not previously consumed by v0.6.47 or later validation, and "
        "(B) independently produced Two-Wave morphology/reference labels whose provenance, case universe and labeling protocol are frozen before model scoring."
    )
    out["no_current_direction_challenger_authorized"] = True

    shortcuts = list(out.get("forbidden_next_shortcuts", []))
    for shortcut in FORBIDDEN_V0708_SHORTCUTS:
        if shortcut not in shortcuts:
            shortcuts.append(shortcut)
    out["forbidden_next_shortcuts"] = shortcuts

    return out


def validate_current_authority(authority: Mapping[str, Any]) -> None:
    _require(authority.get("schema") == AUTHORITY_SCHEMA, "authority schema is not current")
    _require(authority.get("global_status") == GLOBAL_STATUS, "authority global status is not current")
    _require(authority.get("morphology_acceptance") is False, "morphology authority must remain off")
    _require(authority.get("no_current_direction_challenger_authorized") is True, "direction challengers must remain closed")

    components = authority.get("component_authority", {})
    _require(components.get("parent_identity", {}).get("active_semantic_parent_authority") is None, "semantic parent authority must remain unset")
    _require(components.get("parent_direction", {}).get("winner") is None, "direction winner must remain unset")

    v0708 = authority.get("external_validation_availability", {}).get("v0708", {})
    _require(v0708.get("primary_category") == V0708_CATEGORY, "v0708 authority block missing")
    _require(v0708.get("candidate_opened") is False, "v0708 candidate must remain unopened")
    _require(v0708.get("both_reopening_requirements_satisfied") is False, "v0708 reopening gate must remain blocked")
