"""Evidence contract for bounded whole-family nested time-series validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Literal, cast

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.formula_derivation.validation import (
    attach_semantic_digest,
    require_digest,
    require_exact_keys,
    require_field_labels,
    require_mapping,
    require_text,
    require_zero_authority,
    validate_semantic_digest,
)

JOINT_MECHANISM_ASSESSMENT_SCHEMA_ID: Final[str] = (
    "market_state_joint_mechanism_assessment@1.0"
)
AssessmentStatus = Literal[
    "accepted_joint_policy",
    "diagnostic_joint_candidate",
    "rejected_joint_policy",
    "underpowered_defer",
    "return_to_formula_derivation",
    "return_to_external_factor_registration",
    "exhausted_registered_family_stop",
]

ASSESSMENT_LABELS_ZH: Final[dict[str, str]] = {
    "assessment_id": "联合机制评估标识",
    "family_id": "联合策略家族标识",
    "family_semantic_digest": "联合策略家族语义摘要",
    "atomic_marginal_evidence": "原子属性边际证据",
    "joint_outer_oos_evidence": "完整联合策略外层样本外证据",
    "multiplicity_evidence": "完整家族多重性证据",
    "oracle_gap_evidence": "冻结基线Oracle缺口证据",
    "decision_status": "联合机制裁决",
    "stage3_handoff_eligible": "是否具备第三段交接资格",
    "stage3_authorized": "是否已获第三段执行授权",
    "production_authority": "生产权限",
    "dynamic_parameter_authority": "动态参数权限",
    "tool_routing_authority": "工具路由权限",
}

_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "accepted_joint_policy",
        "diagnostic_joint_candidate",
        "rejected_joint_policy",
        "underpowered_defer",
        "return_to_formula_derivation",
        "return_to_external_factor_registration",
        "exhausted_registered_family_stop",
    }
)
_ASSESSMENT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_id", "assessment_id", "family_id", "family_semantic_digest",
        "atomic_marginal_evidence", "joint_outer_oos_evidence",
        "multiplicity_evidence", "oracle_gap_evidence", "decision_status",
        "decision_reason_zh", "stage3_handoff_eligible", "stage3_authorized",
        "production_authority", "dynamic_parameter_authority",
        "tool_routing_authority", "field_labels_zh", "semantic_digest",
    }
)
_JOINT_OOS_KEYS: Final[frozenset[str]] = frozenset(
    {
        "nested_time_series_oos", "permanent_development_window",
        "outer_blocks_never_recycled", "development_end_exclusive",
        "outer_data_used_for_inner_selection", "outer_outcomes_used_for_diagnostics",
        "outer_outcomes_used_for_continuation",
        "registered_policy_attempt_count_evaluated", "post_2020_rows_used",
        "sample_end_date", "action_semantics", "attempt_set_digest",
        "feature_materialization_digest", "outer_fold_evidence",
        "positive_outer_folds", "total_net_utility_delta",
        "median_fold_net_utility_delta", "positive_tail_contribution_share",
        "cost_bps", "training_coverage_all_folds_passed",
        "training_coverage_fold_pass_count",
    }
)
_OUTER_FOLD_KEYS: Final[frozenset[str]] = frozenset(
    {
        "fold_id", "inner_selection_end_exclusive", "outer_test_start",
        "outer_test_end_exclusive", "selected_policy_id", "selected_policy_digest",
        "baseline_net_utility", "candidate_net_utility", "net_utility_delta",
        "outer_data_used_for_inner_selection", "training_coverage_by_policy",
        "training_coverage_gate_passed", "behavior_unique_candidate_count",
    }
)
_COVERAGE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "action_disagreement_ratio", "minimum_branch_leaf_share",
        "state_transition_count", "branch_coverage_passed", "state_coverage_passed",
        "coverage_gate_passed", "behavior_fingerprint",
        "behavior_deduplication_scope",
    }
)
_MULTIPLICITY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "family_wide_correction_applied", "registered_policy_attempt_count_denominator",
        "method", "adjusted_pvalue", "permutation_count",
        "permutation_block_size", "attempt_set_digest",
        "selection_procedure_replayed", "coverage_gate_replayed",
        "behavior_deduplication_replayed",
    }
)
_ORACLE_GAP_KEYS: Final[frozenset[str]] = frozenset(
    {
        "total_oracle_gap", "gross_gap_recovered", "remaining_gap",
        "remaining_gap_ratio", "event_count", "evidence_scope",
        "diagnostic_end_exclusive", "outer_outcomes_used_for_continuation",
    }
)


@dataclass(frozen=True, slots=True)
class JointMechanismAssessment:
    """One assessment where marginal failure does not block joint evaluation."""

    assessment_id: str
    family_id: str
    family_semantic_digest: str
    atomic_marginal_evidence: Mapping[str, object]
    joint_outer_oos_evidence: Mapping[str, object]
    multiplicity_evidence: Mapping[str, object]
    oracle_gap_evidence: Mapping[str, object]
    decision_status: AssessmentStatus
    decision_reason_zh: str
    stage3_handoff_eligible: bool
    stage3_authorized: bool = False
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        if not self.assessment_id.strip() or not self.family_id.strip():
            raise ValidationError("joint mechanism assessment identity is required")
        _ = require_digest(self.family_semantic_digest, field="family_semantic_digest")
        if not self.atomic_marginal_evidence:
            raise ValidationError("atomic marginal evidence must be reported, including null evidence")
        if self.atomic_marginal_evidence.get("admission_gate_applied") is not False:
            raise ValidationError("atomic marginal evidence cannot act as an admission gate")
        evaluated = _mapping_integer(
            self.joint_outer_oos_evidence,
            "registered_policy_attempt_count_evaluated",
        )
        denominator = _mapping_integer(
            self.multiplicity_evidence,
            "registered_policy_attempt_count_denominator",
        )
        if evaluated != denominator:
            raise ValidationError("all registered whole-policy attempts must remain in the denominator")
        if self.joint_outer_oos_evidence.get("nested_time_series_oos") is not True:
            raise ValidationError("joint mechanism assessment requires nested time-series OOS")
        if self.joint_outer_oos_evidence.get("outer_data_used_for_inner_selection") is not False:
            raise ValidationError("outer data cannot alter inner selection")
        if self.joint_outer_oos_evidence.get("post_2020_rows_used") != 0:
            raise ValidationError("joint mechanism assessment opened the sealed interval")
        if self.multiplicity_evidence.get("family_wide_correction_applied") is not True:
            raise ValidationError("joint mechanism assessment needs family-wide multiplicity correction")
        if any(
            self.multiplicity_evidence.get(field) is not True
            for field in (
                "selection_procedure_replayed",
                "coverage_gate_replayed",
                "behavior_deduplication_replayed",
            )
        ):
            raise ValidationError(
                "joint mechanism multiplicity null did not replay the observed selector"
            )
        if self.decision_status not in _STATUSES or not self.decision_reason_zh.strip():
            raise ValidationError("joint mechanism assessment decision is invalid")
        expected_handoff = self.decision_status == "accepted_joint_policy"
        if self.stage3_handoff_eligible != expected_handoff:
            raise ValidationError("only accepted_joint_policy can be eligible for Stage 3 handoff")
        if self.stage3_authorized:
            raise ValidationError("assessment eligibility is not Stage-3 authorization")
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("joint mechanism assessment cannot grant authority")

    def to_dict(self) -> dict[str, object]:
        return attach_semantic_digest(
            {
                "schema_id": JOINT_MECHANISM_ASSESSMENT_SCHEMA_ID,
                "assessment_id": self.assessment_id,
                "family_id": self.family_id,
                "family_semantic_digest": self.family_semantic_digest,
                "atomic_marginal_evidence": dict(self.atomic_marginal_evidence),
                "joint_outer_oos_evidence": dict(self.joint_outer_oos_evidence),
                "multiplicity_evidence": dict(self.multiplicity_evidence),
                "oracle_gap_evidence": dict(self.oracle_gap_evidence),
                "decision_status": self.decision_status,
                "decision_reason_zh": self.decision_reason_zh,
                "stage3_handoff_eligible": self.stage3_handoff_eligible,
                "stage3_authorized": self.stage3_authorized,
                "production_authority": self.production_authority,
                "dynamic_parameter_authority": self.dynamic_parameter_authority,
                "tool_routing_authority": self.tool_routing_authority,
                "field_labels_zh": dict(ASSESSMENT_LABELS_ZH),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> JointMechanismAssessment:
        return cls(
            assessment_id=require_text(payload, "assessment_id"),
            family_id=require_text(payload, "family_id"),
            family_semantic_digest=require_text(payload, "family_semantic_digest"),
            atomic_marginal_evidence=require_mapping(payload, "atomic_marginal_evidence"),
            joint_outer_oos_evidence=require_mapping(payload, "joint_outer_oos_evidence"),
            multiplicity_evidence=require_mapping(payload, "multiplicity_evidence"),
            oracle_gap_evidence=require_mapping(payload, "oracle_gap_evidence"),
            decision_status=cast(AssessmentStatus, require_text(payload, "decision_status")),
            decision_reason_zh=require_text(payload, "decision_reason_zh"),
            stage3_handoff_eligible=payload.get("stage3_handoff_eligible") is True,
            stage3_authorized=payload.get("stage3_authorized") is True,
            production_authority=payload.get("production_authority") is True,
            dynamic_parameter_authority=payload.get("dynamic_parameter_authority") is True,
            tool_routing_authority=payload.get("tool_routing_authority") is True,
        )


def validate_joint_mechanism_assessment(payload: Mapping[str, object]) -> None:
    if payload.get("schema_id") != JOINT_MECHANISM_ASSESSMENT_SCHEMA_ID:
        raise ValidationError("joint mechanism assessment schema changed")
    require_exact_keys(payload, _ASSESSMENT_KEYS, label="joint mechanism assessment")
    require_zero_authority(payload)
    require_field_labels(payload, set(ASSESSMENT_LABELS_ZH))
    validate_semantic_digest(payload)
    _validate_nested_assessment_evidence(payload)
    assessment = JointMechanismAssessment.from_dict(payload)
    if assessment.to_dict() != dict(payload):
        raise ValidationError("joint mechanism assessment does not round-trip canonically")


def _validate_nested_assessment_evidence(payload: Mapping[str, object]) -> None:
    atomic = require_mapping(payload, "atomic_marginal_evidence")
    if set(atomic).intersection({"admission_gate_applied", "evidence_scope", "outer_outcomes_used"}) != {
        "admission_gate_applied", "evidence_scope", "outer_outcomes_used"
    }:
        raise ValidationError("atomic marginal evidence is incomplete")
    if (
        atomic.get("admission_gate_applied") is not False
        or atomic.get("outer_outcomes_used") is not False
        or atomic.get("evidence_scope") != "train_and_inner_validation_only"
    ):
        raise ValidationError("atomic marginal evidence boundary changed")
    for atom_id, raw in atomic.items():
        if atom_id in {"admission_gate_applied", "evidence_scope", "outer_outcomes_used"}:
            continue
        if not isinstance(raw, Mapping):
            raise ValidationError("atomic marginal evidence row changed")
        row = cast(Mapping[str, object], raw)
        if set(row) != {"pearson", "status"}:
            raise ValidationError("atomic marginal evidence row changed")
        if row.get("status") != "reported_not_admission_gate":
            raise ValidationError("atomic marginal evidence became an admission gate")

    joint = require_mapping(payload, "joint_outer_oos_evidence")
    require_exact_keys(joint, _JOINT_OOS_KEYS, label="joint outer OOS evidence")
    folds = joint.get("outer_fold_evidence")
    if not isinstance(folds, list) or not folds:
        raise ValidationError("joint outer OOS folds are missing")
    for raw_fold in cast(list[object], folds):
        if not isinstance(raw_fold, Mapping):
            raise ValidationError("joint outer OOS fold is invalid")
        fold = cast(Mapping[str, object], raw_fold)
        require_exact_keys(fold, _OUTER_FOLD_KEYS, label="joint outer OOS fold")
        coverage = fold.get("training_coverage_by_policy")
        if not isinstance(coverage, Mapping) or not coverage:
            raise ValidationError("joint outer OOS training coverage is missing")
        for raw_coverage in cast(Mapping[str, object], coverage).values():
            if not isinstance(raw_coverage, Mapping):
                raise ValidationError("joint policy coverage row is invalid")
            require_exact_keys(
                cast(Mapping[str, object], raw_coverage),
                _COVERAGE_KEYS,
                label="joint policy coverage row",
            )

    multiplicity = require_mapping(payload, "multiplicity_evidence")
    require_exact_keys(multiplicity, _MULTIPLICITY_KEYS, label="joint multiplicity evidence")
    oracle = require_mapping(payload, "oracle_gap_evidence")
    require_exact_keys(oracle, _ORACLE_GAP_KEYS, label="joint oracle-gap evidence")
    ratio = oracle.get("remaining_gap_ratio")
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not 0.0 <= float(ratio) <= 1.0:
        raise ValidationError("joint oracle remaining-gap ratio must be within [0, 1]")
    if oracle.get("outer_outcomes_used_for_continuation") is not False:
        raise ValidationError("outer outcomes cannot drive residual continuation")


def _mapping_integer(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValidationError(f"{key} must be a positive integer")
    return value


__all__ = [
    "JOINT_MECHANISM_ASSESSMENT_SCHEMA_ID",
    "AssessmentStatus",
    "JointMechanismAssessment",
    "validate_joint_mechanism_assessment",
]
