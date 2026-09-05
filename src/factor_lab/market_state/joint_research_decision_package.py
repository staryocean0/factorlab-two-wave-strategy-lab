"""V3 joint-policy decision handoff with read-only V1 compatibility."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Final, cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
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
from factor_lab.market_state.joint_mechanism_assessment import (
    AssessmentStatus,
    JointMechanismAssessment,
)
from factor_lab.market_state.joint_policy_attempt_registry import JointPolicyCandidate
from factor_lab.market_state.research_decision_package import (
    validate_research_decision_package,
)

JOINT_RESEARCH_DECISION_PACKAGE_SCHEMA_ID: Final[str] = "market_state_research_decision_package@2.0"
JOINT_RESEARCH_DECISION_PACKAGE_VERSION: Final[str] = "joint_research_decision_package_v2"
_JOINT_RESEARCH_DECISION_PACKAGE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_id", "package_version", "package_id", "tool_id",
        "derivation_package_ref", "joint_policy_family_ref",
        "feature_materialization_ref", "assessment", "decision_status",
        "frozen_joint_policy", "handoff_rule", "stage3_handoff_eligible",
        "stage3_authorized", "production_authority", "dynamic_parameter_authority",
        "tool_routing_authority", "field_labels_zh", "semantic_digest",
    }
)

_SELECTION_POLICY_INTEGER_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "outer_fold_count",
        "minimum_train_size",
        "outer_test_size",
        "minimum_positive_outer_folds",
        "permutation_count",
        "permutation_block_size",
        "minimum_state_transition_count",
    }
)
_SELECTION_POLICY_FLOAT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "inner_validation_fraction",
        "family_alpha",
        "cost_bps",
        "minimum_action_disagreement_ratio",
        "minimum_branch_leaf_share",
        "maximum_positive_tail_contribution_share",
        "residual_gap_ratio_for_continuation",
    }
)

DECISION_LABELS_ZH: Final[dict[str, str]] = {
    "package_id": "联合研究决定包标识",
    "tool_id": "择时工具标识",
    "derivation_package_ref": "公式派生包引用",
    "joint_policy_family_ref": "联合策略家族引用",
    "feature_materialization_ref": "特征物化收据引用",
    "assessment": "联合机制评估",
    "decision_status": "联合机制裁决",
    "frozen_joint_policy": "冻结联合策略",
    "handoff_rule": "第三段机械重放规则",
    "stage3_handoff_eligible": "第三段交接资格",
    "stage3_authorized": "第三段执行授权",
    "production_authority": "生产权限",
    "dynamic_parameter_authority": "动态参数权限",
    "tool_routing_authority": "工具路由权限",
}


@dataclass(frozen=True, slots=True)
class JointResearchDecisionPackage:
    """The complete Stage-2 V3 decision; eligibility never grants authority."""

    package_id: str
    tool_id: str
    derivation_package_ref: Mapping[str, object]
    joint_policy_family_ref: Mapping[str, object]
    feature_materialization_ref: Mapping[str, object]
    assessment: JointMechanismAssessment
    decision_status: AssessmentStatus
    frozen_joint_policy: Mapping[str, object]
    handoff_rule: Mapping[str, object]
    stage3_handoff_eligible: bool
    stage3_authorized: bool = False
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        if not self.package_id.strip() or not self.tool_id.strip():
            raise ValidationError("joint research decision identity is required")
        _validate_ref(self.derivation_package_ref, "derivation_package_ref")
        _validate_ref(self.joint_policy_family_ref, "joint_policy_family_ref")
        _validate_materialization_ref(self.feature_materialization_ref)
        if self.assessment.family_id != self.joint_policy_family_ref.get("artifact_id"):
            raise ValidationError("joint assessment and family reference disagree")
        if self.decision_status != self.assessment.decision_status:
            raise ValidationError("joint decision and assessment status disagree")
        accepted = self.decision_status == "accepted_joint_policy"
        if self.stage3_handoff_eligible != accepted:
            raise ValidationError("only accepted_joint_policy can be handed to Stage 3")
        handoff_status = self.handoff_rule.get("status")
        if accepted:
            if not self.frozen_joint_policy or handoff_status != "frozen_rule":
                raise ValidationError("accepted joint policy needs a frozen policy and rule")
            candidate_payload = self.frozen_joint_policy.get("candidate")
            if not isinstance(candidate_payload, Mapping):
                raise ValidationError("accepted joint policy needs a reconstructable candidate")
            candidate = JointPolicyCandidate.from_dict(cast(Mapping[str, object], candidate_payload))
            if (
                candidate.family_id != self.joint_policy_family_ref.get("artifact_id")
                or self.frozen_joint_policy.get("family_id") != candidate.family_id
            ):
                raise ValidationError("accepted candidate and registered family disagree")
            _ = require_digest(
                self.frozen_joint_policy.get("attempt_set_digest"),
                field="frozen_joint_policy.attempt_set_digest",
            )
            consensus = self.frozen_joint_policy.get("selection_consensus")
            if not isinstance(consensus, Mapping):
                raise ValidationError("accepted joint policy needs selection consensus evidence")
            typed_consensus = cast(Mapping[str, object], consensus)
            consensus_digest = require_digest(
                self.frozen_joint_policy.get("selection_consensus_digest"),
                field="frozen_joint_policy.selection_consensus_digest",
            )
            if canonical_digest(dict(typed_consensus)) != consensus_digest:
                raise ValidationError("accepted policy selection consensus drifted")
            selection_policy = self.frozen_joint_policy.get("selection_policy")
            if not isinstance(selection_policy, Mapping):
                raise ValidationError("accepted policy lacks its development selection policy")
            _validate_selection_policy(cast(Mapping[str, object], selection_policy))
            if (
                typed_consensus.get("final_policy_id") != candidate.policy_id
                or typed_consensus.get("final_policy_digest") != candidate.semantic_digest
                or typed_consensus.get("selection_rule") != "permanent_development_inner_consensus_only"
            ):
                raise ValidationError("accepted policy is not the frozen development consensus")
            selected_ids_raw = typed_consensus.get("selected_policy_ids")
            selected_digests_raw = typed_consensus.get("selected_policy_digests")
            votes_raw = typed_consensus.get("selection_votes")
            if not isinstance(selected_ids_raw, list) or not isinstance(selected_digests_raw, list) or not isinstance(votes_raw, Mapping):
                raise ValidationError("accepted policy selection consensus is incomplete")
            selected_ids = [str(value) for value in cast(list[object], selected_ids_raw)]
            selected_digests = [str(value) for value in cast(list[object], selected_digests_raw)]
            votes = cast(Mapping[str, object], votes_raw)
            if len(selected_ids) != len(selected_digests) or not selected_ids:
                raise ValidationError("accepted policy selection consensus widths disagree")
            recomputed_votes = {str(policy_id): selected_ids.count(policy_id) for policy_id in set(selected_ids)}
            if dict(votes) != recomputed_votes:
                raise ValidationError("accepted policy selection votes do not reconcile")
            winner = max(recomputed_votes, key=lambda item: (recomputed_votes[item], item))
            if winner != candidate.policy_id or any(
                digest != candidate.semantic_digest
                for policy_id, digest in zip(selected_ids, selected_digests, strict=True)
                if policy_id == winner
            ):
                raise ValidationError("accepted policy did not win the frozen selection consensus")
            frozen_digest = require_digest(
                self.frozen_joint_policy.get("semantic_digest"),
                field="frozen_joint_policy.semantic_digest",
            )
            if candidate.semantic_digest != frozen_digest:
                raise ValidationError("accepted joint policy candidate digest drifted")
            if (
                self.frozen_joint_policy.get("policy_id") != candidate.policy_id
                or self.frozen_joint_policy.get("expression") != candidate.expression
            ):
                raise ValidationError("accepted joint policy top-level rule drifted from candidate")
            if self.frozen_joint_policy.get("feature_materialization_digest") != self.feature_materialization_ref.get("semantic_digest"):
                raise ValidationError("accepted policy lost its feature materialization binding")
            if self.handoff_rule.get("execution_lag_bars") != 1:
                raise ValidationError("accepted joint policy must execute next-bar")
            if self.handoff_rule.get("signal_clock") != "after_close":
                raise ValidationError("accepted joint policy must use after-close signals")
            if self.handoff_rule.get("stage3_may_modify_rule") is not False:
                raise ValidationError("Stage 3 cannot modify a frozen joint policy")
        elif self.frozen_joint_policy or handoff_status != "no_rule":
            raise ValidationError("non-accepted joint decision cannot carry a frozen rule")
        if self.stage3_authorized:
            raise ValidationError("joint decision handoff eligibility is not authorization")
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("joint research decision cannot grant authority")

    def to_dict(self) -> dict[str, object]:
        return attach_semantic_digest(
            {
                "schema_id": JOINT_RESEARCH_DECISION_PACKAGE_SCHEMA_ID,
                "package_version": JOINT_RESEARCH_DECISION_PACKAGE_VERSION,
                "package_id": self.package_id,
                "tool_id": self.tool_id,
                "derivation_package_ref": dict(self.derivation_package_ref),
                "joint_policy_family_ref": dict(self.joint_policy_family_ref),
                "feature_materialization_ref": dict(self.feature_materialization_ref),
                "assessment": self.assessment.to_dict(),
                "decision_status": self.decision_status,
                "frozen_joint_policy": dict(self.frozen_joint_policy),
                "handoff_rule": dict(self.handoff_rule),
                "stage3_handoff_eligible": self.stage3_handoff_eligible,
                "stage3_authorized": self.stage3_authorized,
                "production_authority": self.production_authority,
                "dynamic_parameter_authority": self.dynamic_parameter_authority,
                "tool_routing_authority": self.tool_routing_authority,
                "field_labels_zh": dict(DECISION_LABELS_ZH),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> JointResearchDecisionPackage:
        return cls(
            package_id=require_text(payload, "package_id"),
            tool_id=require_text(payload, "tool_id"),
            derivation_package_ref=require_mapping(payload, "derivation_package_ref"),
            joint_policy_family_ref=require_mapping(payload, "joint_policy_family_ref"),
            feature_materialization_ref=require_mapping(
                payload,
                "feature_materialization_ref",
            ),
            assessment=JointMechanismAssessment.from_dict(require_mapping(payload, "assessment")),
            decision_status=cast(AssessmentStatus, require_text(payload, "decision_status")),
            frozen_joint_policy=require_mapping(payload, "frozen_joint_policy"),
            handoff_rule=require_mapping(payload, "handoff_rule"),
            stage3_handoff_eligible=payload.get("stage3_handoff_eligible") is True,
            stage3_authorized=payload.get("stage3_authorized") is True,
            production_authority=payload.get("production_authority") is True,
            dynamic_parameter_authority=payload.get("dynamic_parameter_authority") is True,
            tool_routing_authority=payload.get("tool_routing_authority") is True,
        )


def validate_joint_research_decision_package(payload: Mapping[str, object]) -> None:
    if payload.get("schema_id") != JOINT_RESEARCH_DECISION_PACKAGE_SCHEMA_ID:
        raise ValidationError("joint research decision package schema changed")
    if payload.get("package_version") != JOINT_RESEARCH_DECISION_PACKAGE_VERSION:
        raise ValidationError("joint research decision package version changed")
    require_exact_keys(
        payload,
        _JOINT_RESEARCH_DECISION_PACKAGE_KEYS,
        label="joint research decision package",
    )
    require_zero_authority(payload)
    require_field_labels(payload, set(DECISION_LABELS_ZH))
    validate_semantic_digest(payload)
    package = JointResearchDecisionPackage.from_dict(payload)
    if package.to_dict() != dict(payload):
        raise ValidationError("joint research decision package does not round-trip canonically")


def _validate_selection_policy(payload: Mapping[str, object]) -> None:
    expected = _SELECTION_POLICY_INTEGER_FIELDS | _SELECTION_POLICY_FLOAT_FIELDS
    if frozenset(payload) != expected:
        raise ValidationError("joint validation policy fields changed")
    integers: dict[str, int] = {}
    for field in _SELECTION_POLICY_INTEGER_FIELDS:
        value = payload[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValidationError(f"joint validation policy {field} must be a positive integer")
        integers[field] = value
    numeric: dict[str, float] = {}
    for field in _SELECTION_POLICY_FLOAT_FIELDS:
        value = payload[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(f"joint validation policy {field} must be numeric")
        parsed = float(value)
        if not isfinite(parsed):
            raise ValidationError(f"joint validation policy {field} must be finite")
        numeric[field] = parsed
    if integers["minimum_positive_outer_folds"] > integers["outer_fold_count"]:
        raise ValidationError("positive-fold gate exceeds outer-fold count")
    if not 0.0 < numeric["inner_validation_fraction"] < 0.5:
        raise ValidationError("inner validation fraction must be in (0, 0.5)")
    if not 0.0 < numeric["family_alpha"] <= 1.0:
        raise ValidationError("family alpha must be in (0, 1]")
    if numeric["cost_bps"] < 0.0:
        raise ValidationError("joint validation cost cannot be negative")
    if not 0.0 <= numeric["minimum_action_disagreement_ratio"] <= 1.0:
        raise ValidationError("joint validation disagreement ratio is invalid")
    if not 0.0 <= numeric["minimum_branch_leaf_share"] <= 0.5:
        raise ValidationError("joint validation branch leaf share is invalid")
    if not 0.0 < numeric["maximum_positive_tail_contribution_share"] <= 1.0:
        raise ValidationError("joint validation tail share cap is invalid")
    if not 0.0 <= numeric["residual_gap_ratio_for_continuation"] <= 1.0:
        raise ValidationError("joint validation residual-gap ratio is invalid")


def read_legacy_research_decision_as_diagnostic(
    payload: Mapping[str, object],
) -> dict[str, object]:
    """Validate V1 first, then expose it as non-promotable diagnostic evidence."""

    validate_research_decision_package(payload)
    decision = require_mapping(payload, "decision")
    legacy_status = require_text(decision, "status")
    diagnostic_status = {
        "single_factor_candidate": "legacy_single_factor_diagnostic",
        "second_factor_mandate": "legacy_second_factor_diagnostic",
        "change_mechanism": "return_to_formula_derivation",
        "stop": "exhausted_registered_family_stop",
    }.get(legacy_status)
    if diagnostic_status is None:
        raise ValidationError("legacy decision status cannot be mapped")
    return attach_semantic_digest(
        {
            "source_schema_id": payload.get("schema_id"),
            "source_package_id": require_text(payload, "package_id"),
            "source_semantic_digest": require_digest(
                payload.get("semantic_digest"),
                field="legacy source semantic_digest",
            ),
            "legacy_decision_status": legacy_status,
            "v3_diagnostic_status": diagnostic_status,
            "v3_migration_status": "legacy_diagnostic_only",
            "accepted_joint_policy": False,
            "promotion_allowed": False,
            "stage3_handoff_eligible": False,
            "stage3_authorized": False,
            "production_authority": False,
            "dynamic_parameter_authority": False,
            "tool_routing_authority": False,
            "field_labels_zh": {
                "legacy_decision_status": "旧版研究裁决",
                "v3_migration_status": "V3只读迁移状态",
                "v3_diagnostic_status": "V3只读诊断映射",
                "promotion_allowed": "是否允许静默升格",
            },
        }
    )


def _validate_ref(payload: Mapping[str, object], field: str) -> None:
    _ = require_text(payload, "artifact_id")
    _ = require_text(payload, "relative_path")
    _ = require_digest(payload.get("semantic_digest"), field=f"{field}.semantic_digest")


def _validate_materialization_ref(payload: Mapping[str, object]) -> None:
    for field in ("receipt_id", "dataset_ref", "frequency"):
        _ = require_text(payload, field)
    for field in (
        "semantic_digest",
        "graph_digest",
        "derivation_package_digest",
        "benchmark_spec_digest",
        "parameters_digest",
        "provenance_binding_digest",
        "dataset_sha256",
        "raw_kline_content_digest",
        "observation_dates_digest",
        "feature_rows_digest",
        "baseline_action_digest",
        "forward_return_digest",
    ):
        _ = require_digest(payload.get(field), field=f"feature_materialization_ref.{field}")
    factor_digests = payload.get("factor_spec_digests")
    if not isinstance(factor_digests, list) or not factor_digests:
        raise ValidationError("feature materialization reference lacks FactorSpec digests")
    for digest in cast(list[object], factor_digests):
        _ = require_digest(digest, field="feature_materialization_ref.factor_spec_digests")
    dataset_ref = str(payload.get("dataset_ref", ""))
    fixture_prefixes = (
        "fixture://deterministic_counterexample_fixture/",
        "fixture://deterministic_stage1_bound_counterexample_fixture/",
    )
    if (
        payload.get("dataset_sha256") != payload.get("raw_kline_content_digest")
        and not dataset_ref.startswith(fixture_prefixes)
    ):
        raise ValidationError("source materialization dataset digest is not content-derived")
    cost = payload.get("cost_bps")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or float(cost) < 0.0:
        raise ValidationError("feature materialization reference cost is invalid")


__all__ = [
    "JOINT_RESEARCH_DECISION_PACKAGE_SCHEMA_ID",
    "JOINT_RESEARCH_DECISION_PACKAGE_VERSION",
    "JointResearchDecisionPackage",
    "read_legacy_research_decision_as_diagnostic",
    "validate_joint_research_decision_package",
]
