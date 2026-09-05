"""Nested time-series OOS evaluation of complete registered joint-policy families."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from math import isfinite
from random import Random
from statistics import median
from typing import Literal, cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.formula_derivation.materialization import (
    validate_materialized_rows_against_receipt,
)
from factor_lab.market_state.formula_derivation.validation import (
    require_digest,
    require_exact_keys,
    require_mapping,
    require_zero_authority,
    validate_semantic_digest,
)
from factor_lab.market_state.joint_mechanism_assessment import (
    AssessmentStatus,
    JointMechanismAssessment,
    validate_joint_mechanism_assessment,
)
from factor_lab.market_state.joint_policy_attempt_registry import (
    JointPolicyAttemptRegistry,
    JointPolicyCandidate,
    PolicyExpression,
    validate_policy_expression,
)
from factor_lab.market_state.joint_policy_family_registry import JointPolicyFamily
from factor_lab.market_state.joint_policy_runtime import (
    branch_nodes as _branch_nodes,
)
from factor_lab.market_state.joint_policy_runtime import (
    evaluate_expression as _evaluate_expression,
)
from factor_lab.market_state.joint_policy_runtime import (
    evaluate_joint_policy,
)
from factor_lab.market_state.joint_policy_runtime import (
    expression_children as _expression_children,
)
from factor_lab.market_state.joint_policy_runtime import (
    expression_inventory as _expression_inventory,
)
from factor_lab.market_state.joint_policy_runtime import (
    finite_number as _finite_number,
)
from factor_lab.market_state.joint_research_decision_package import (
    JointResearchDecisionPackage,
)

ContinuationStatus = Literal[
    "no_continuation_rejected",
    "residual_exhausted_stop",
    "registered_residual_family_required",
    "return_to_formula_derivation",
    "return_to_external_factor_registration",
    "underpowered_collect_support",
    "registered_family_exhausted_stop",
]
ResidualGapClassification = Literal[
    "formula_internal_path",
    "formula_external_market_state",
    "insufficient_sample_support",
    "registered_family_exhausted",
]
_RESULT_KEYS = frozenset(
    {
        "schema_id", "family_ref", "feature_materialization_ref",
        "selected_policy_ids", "selected_policy_digests", "final_frozen_policy",
        "final_refit_evidence", "fold_evidence", "assessment", "continuation",
        "production_authority", "dynamic_parameter_authority",
        "tool_routing_authority", "field_labels_zh", "semantic_digest",
    }
)
_FINAL_POLICY_KEYS = frozenset(
    {"policy_id", "semantic_digest", "expression", "complexity", "selection_rule"}
)
_FINAL_REFIT_KEYS = frozenset(
    {
        "selection_scope", "selection_votes", "selection_policy",
        "coverage_gate_passed", "outer_outcomes_used_for_handoff_selection",
        "outer_outcomes_used_for_diagnostics", "outer_outcomes_used_for_continuation",
    }
)
_CONTINUATION_KEYS = frozenset(
    {"status", "remaining_gap_ratio", "required_registration", "reason_zh"}
)


@dataclass(frozen=True, slots=True)
class NestedTimeSeriesFold:
    """One permanent-development fold followed by an untouched outer block."""

    fold_id: str
    outer_train_start: int
    outer_train_end: int
    inner_train_end: int
    inner_validation_start: int
    inner_validation_end: int
    outer_test_start: int
    outer_test_end: int

    def __post_init__(self) -> None:
        if not (
            self.outer_train_start
            == 0
            < self.inner_train_end
            == self.inner_validation_start
            < self.inner_validation_end
            == self.outer_train_end
            <= self.outer_test_start
            < self.outer_test_end
        ):
            raise ValidationError("nested time-series fold boundaries are invalid")


@dataclass(frozen=True, slots=True)
class JointValidationPolicy:
    """Pre-registered Stage-2 evidence gates and cost/multiplicity settings."""

    outer_fold_count: int = 4
    minimum_train_size: int = 80
    outer_test_size: int = 20
    inner_validation_fraction: float = 0.25
    minimum_positive_outer_folds: int = 3
    family_alpha: float = 0.05
    permutation_count: int = 99
    permutation_block_size: int = 5
    cost_bps: float = 7.0
    minimum_action_disagreement_ratio: float = 0.02
    minimum_branch_leaf_share: float = 0.02
    minimum_state_transition_count: int = 1
    maximum_positive_tail_contribution_share: float = 0.70
    residual_gap_ratio_for_continuation: float = 0.10

    def __post_init__(self) -> None:
        if (
            min(
                self.outer_fold_count,
                self.minimum_train_size,
                self.outer_test_size,
                self.minimum_positive_outer_folds,
                self.permutation_count,
                self.permutation_block_size,
                self.minimum_state_transition_count,
            )
            < 1
        ):
            raise ValidationError("joint validation counts must be positive")
        if self.minimum_positive_outer_folds > self.outer_fold_count:
            raise ValidationError("positive-fold gate exceeds outer-fold count")
        if not 0.0 < self.inner_validation_fraction < 0.5:
            raise ValidationError("inner validation fraction must be in (0, 0.5)")
        if not 0.0 < self.family_alpha <= 1.0:
            raise ValidationError("family alpha must be in (0, 1]")
        if self.cost_bps < 0.0:
            raise ValidationError("joint validation cost cannot be negative")
        if not 0.0 <= self.minimum_action_disagreement_ratio <= 1.0:
            raise ValidationError("joint validation disagreement ratio is invalid")
        if not 0.0 <= self.minimum_branch_leaf_share <= 0.5:
            raise ValidationError("joint validation branch leaf share is invalid")
        if not 0.0 < self.maximum_positive_tail_contribution_share <= 1.0:
            raise ValidationError("joint validation tail share cap is invalid")
        if not 0.0 <= self.residual_gap_ratio_for_continuation <= 1.0:
            raise ValidationError("joint validation residual-gap ratio is invalid")

    def to_dict(self) -> dict[str, int | float]:
        return {
            "outer_fold_count": self.outer_fold_count,
            "minimum_train_size": self.minimum_train_size,
            "outer_test_size": self.outer_test_size,
            "inner_validation_fraction": self.inner_validation_fraction,
            "minimum_positive_outer_folds": self.minimum_positive_outer_folds,
            "family_alpha": self.family_alpha,
            "permutation_count": self.permutation_count,
            "permutation_block_size": self.permutation_block_size,
            "cost_bps": self.cost_bps,
            "minimum_action_disagreement_ratio": self.minimum_action_disagreement_ratio,
            "minimum_branch_leaf_share": self.minimum_branch_leaf_share,
            "minimum_state_transition_count": self.minimum_state_transition_count,
            "maximum_positive_tail_contribution_share": self.maximum_positive_tail_contribution_share,
            "residual_gap_ratio_for_continuation": self.residual_gap_ratio_for_continuation,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> JointValidationPolicy:
        expected = set(cls().to_dict())
        if set(payload) != expected:
            raise ValidationError("joint validation policy fields changed")
        return cls(
            outer_fold_count=_policy_integer(payload, "outer_fold_count"),
            minimum_train_size=_policy_integer(payload, "minimum_train_size"),
            outer_test_size=_policy_integer(payload, "outer_test_size"),
            inner_validation_fraction=_policy_float(payload, "inner_validation_fraction"),
            minimum_positive_outer_folds=_policy_integer(
                payload,
                "minimum_positive_outer_folds",
            ),
            family_alpha=_policy_float(payload, "family_alpha"),
            permutation_count=_policy_integer(payload, "permutation_count"),
            permutation_block_size=_policy_integer(payload, "permutation_block_size"),
            cost_bps=_policy_float(payload, "cost_bps"),
            minimum_action_disagreement_ratio=_policy_float(
                payload,
                "minimum_action_disagreement_ratio",
            ),
            minimum_branch_leaf_share=_policy_float(payload, "minimum_branch_leaf_share"),
            minimum_state_transition_count=_policy_integer(
                payload,
                "minimum_state_transition_count",
            ),
            maximum_positive_tail_contribution_share=_policy_float(
                payload,
                "maximum_positive_tail_contribution_share",
            ),
            residual_gap_ratio_for_continuation=_policy_float(
                payload,
                "residual_gap_ratio_for_continuation",
            ),
        )


@dataclass(frozen=True, slots=True)
class ResidualContinuationDecision:
    """A continuation request based on remaining gap, never on factor depth."""

    status: ContinuationStatus
    remaining_gap_ratio: float
    required_registration: str | None
    reason_zh: str


@dataclass(frozen=True, slots=True)
class JointMechanismResearchResult:
    """Complete nested evidence, assessment, and residual continuation decision."""

    family: JointPolicyFamily
    attempt_set_digest: str
    feature_materialization_ref: Mapping[str, object]
    selected_policy_ids: tuple[str, ...]
    selected_policy_digests: tuple[str, ...]
    final_frozen_policy_id: str
    final_frozen_policy_digest: str
    final_frozen_policy_expression: PolicyExpression
    final_frozen_policy_complexity: Mapping[str, object]
    final_refit_evidence: Mapping[str, object]
    fold_evidence: tuple[Mapping[str, object], ...]
    assessment: JointMechanismAssessment
    continuation: ResidualContinuationDecision
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        _ = require_digest(self.attempt_set_digest, field="attempt_set_digest")
        _ = require_digest(
            self.feature_materialization_ref.get("semantic_digest"),
            field="feature materialization semantic_digest",
        )
        if len(self.selected_policy_ids) != len(self.fold_evidence):
            raise ValidationError("joint research selected-policy and fold counts disagree")
        if not self.final_frozen_policy_id:
            raise ValidationError("joint research final frozen policy is required")
        if not self.final_frozen_policy_complexity:
            raise ValidationError("joint research final frozen policy complexity is required")
        _ = require_digest(
            self.final_frozen_policy_digest,
            field="final_frozen_policy_digest",
        )
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("joint mechanism research cannot grant authority")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": "market_state_joint_mechanism_research_result@1.0",
            "family_ref": {
                "family_id": self.family.family_id,
                "semantic_digest": self.family.to_dict()["semantic_digest"],
                "attempt_set_digest": self.attempt_set_digest,
            },
            "feature_materialization_ref": dict(self.feature_materialization_ref),
            "selected_policy_ids": list(self.selected_policy_ids),
            "selected_policy_digests": list(self.selected_policy_digests),
            "final_frozen_policy": {
                "policy_id": self.final_frozen_policy_id,
                "semantic_digest": self.final_frozen_policy_digest,
                "expression": dict(self.final_frozen_policy_expression),
                "complexity": dict(self.final_frozen_policy_complexity),
                "selection_rule": "permanent_development_inner_consensus_only",
            },
            "final_refit_evidence": dict(self.final_refit_evidence),
            "fold_evidence": [dict(row) for row in self.fold_evidence],
            "assessment": self.assessment.to_dict(),
            "continuation": {
                "status": self.continuation.status,
                "remaining_gap_ratio": self.continuation.remaining_gap_ratio,
                "required_registration": self.continuation.required_registration,
                "reason_zh": self.continuation.reason_zh,
            },
            "production_authority": self.production_authority,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "field_labels_zh": {
                "family_ref": "完整联合策略家族引用",
                "feature_materialization_ref": "原始K线特征物化收据引用",
                "selected_policy_ids": "各外层折内层选定策略",
                "final_frozen_policy": "完整允许样本重选后的冻结策略",
                "final_refit_evidence": "完整允许样本训练覆盖与行为去重证据",
                "fold_evidence": "冻结策略外层样本外证据",
                "assessment": "联合机制评估",
                "continuation": "剩余公式缺口接续裁决",
            },
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload

    def to_decision_package(
        self,
        *,
        derivation_package_id: str,
        derivation_package_relative_path: str,
        joint_family_relative_path: str,
    ) -> JointResearchDecisionPackage:
        """Create the governed Stage-2 handoff without granting Stage-3 authority."""

        accepted = self.assessment.decision_status == "accepted_joint_policy"
        frozen_policy: dict[str, object] = {}
        handoff_rule: dict[str, object] = {
            "status": "no_rule",
            "rule_zh": "未接受联合策略，不生成第三段规则",
            "signal_clock": "after_close",
            "execution_lag_bars": 1,
            "stage3_may_modify_rule": False,
        }
        if accepted:
            selection_consensus = {
                "selected_policy_ids": list(self.selected_policy_ids),
                "selected_policy_digests": list(self.selected_policy_digests),
                "selection_votes": dict(
                    cast(Mapping[str, object], self.final_refit_evidence["selection_votes"])
                ),
                "final_policy_id": self.final_frozen_policy_id,
                "final_policy_digest": self.final_frozen_policy_digest,
                "selection_rule": "permanent_development_inner_consensus_only",
            }
            candidate_payload = {
                "policy_id": self.final_frozen_policy_id,
                "family_id": self.family.family_id,
                "expression": dict(self.final_frozen_policy_expression),
                "complexity": dict(self.final_frozen_policy_complexity),
            }
            frozen_policy = {
                "policy_id": self.final_frozen_policy_id,
                "semantic_digest": self.final_frozen_policy_digest,
                "expression": dict(self.final_frozen_policy_expression),
                "candidate": candidate_payload,
                "family_id": self.family.family_id,
                "attempt_set_digest": self.attempt_set_digest,
                "selection_consensus": selection_consensus,
                "selection_consensus_digest": canonical_digest(selection_consensus),
                "selection_rule": "permanent_development_inner_consensus_only",
                "selection_policy": dict(
                    cast(Mapping[str, object], self.final_refit_evidence["selection_policy"])
                ),
                "feature_materialization_digest": self.feature_materialization_ref["semantic_digest"],
                "cost_bps": self.feature_materialization_ref["cost_bps"],
                "action_clip": [-1.0, 1.0],
                "initial_previous_action": 0.0,
                "missing_policy": "fail_closed",
            }
            handoff_rule = {
                "status": "frozen_rule",
                "rule_zh": "收线后计算冻结状态，下一根执行；第三段不得改写",
                "signal_clock": "after_close",
                "execution_lag_bars": 1,
                "stage3_may_modify_rule": False,
            }
        family_digest = require_digest(
            self.family.to_dict()["semantic_digest"],
            field="family semantic_digest",
        )
        return JointResearchDecisionPackage(
            package_id=("joint-decision:" + canonical_digest(self.to_dict()).removeprefix("sha256:")[:24]),
            tool_id=self.family.tool_id,
            derivation_package_ref={
                "artifact_id": derivation_package_id,
                "relative_path": derivation_package_relative_path,
                "semantic_digest": self.family.derivation_package_digest,
            },
            joint_policy_family_ref={
                "artifact_id": self.family.family_id,
                "relative_path": joint_family_relative_path,
                "semantic_digest": family_digest,
            },
            feature_materialization_ref=dict(self.feature_materialization_ref),
            assessment=self.assessment,
            decision_status=self.assessment.decision_status,
            frozen_joint_policy=frozen_policy,
            handoff_rule=handoff_rule,
            stage3_handoff_eligible=accepted,
        )


def validate_joint_mechanism_research_result(payload: Mapping[str, object]) -> None:
    """Validate the emitted aggregate result without reopening row-level evidence."""

    if payload.get("schema_id") != "market_state_joint_mechanism_research_result@1.0":
        raise ValidationError("joint mechanism research result schema changed")
    require_exact_keys(payload, _RESULT_KEYS, label="joint mechanism research result")
    require_zero_authority(payload)
    validate_semantic_digest(payload)
    family_ref = require_mapping(payload, "family_ref")
    require_exact_keys(
        family_ref,
        {"family_id", "semantic_digest", "attempt_set_digest"},
        label="joint mechanism research family reference",
    )
    _ = require_digest(family_ref.get("semantic_digest"), field="research family digest")
    _ = require_digest(family_ref.get("attempt_set_digest"), field="research attempt-set digest")
    frozen = require_mapping(payload, "final_frozen_policy")
    require_exact_keys(frozen, _FINAL_POLICY_KEYS, label="joint research frozen policy")
    expression = require_mapping(frozen, "expression")
    validate_policy_expression(expression)
    _ = require_digest(frozen.get("semantic_digest"), field="research frozen-policy digest")
    refit = require_mapping(payload, "final_refit_evidence")
    require_exact_keys(refit, _FINAL_REFIT_KEYS, label="joint research final-refit evidence")
    if any(
        refit.get(key) is not False
        for key in (
            "outer_outcomes_used_for_handoff_selection",
            "outer_outcomes_used_for_diagnostics",
            "outer_outcomes_used_for_continuation",
        )
    ):
        raise ValidationError("outer outcomes altered the frozen research policy")
    assessment = require_mapping(payload, "assessment")
    validate_joint_mechanism_assessment(assessment)
    folds = payload.get("fold_evidence")
    joint = require_mapping(assessment, "joint_outer_oos_evidence")
    if not isinstance(folds, list) or folds != joint.get("outer_fold_evidence"):
        raise ValidationError("joint research fold evidence lost assessment binding")
    continuation = require_mapping(payload, "continuation")
    require_exact_keys(continuation, _CONTINUATION_KEYS, label="joint research continuation")
    ratio = continuation.get("remaining_gap_ratio")
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not 0.0 <= float(ratio) <= 1.0:
        raise ValidationError("joint research continuation ratio must be within [0, 1]")


def build_expanding_nested_splits(
    row_count: int,
    policy: JointValidationPolicy,
) -> tuple[NestedTimeSeriesFold, ...]:
    """Create a permanent development window plus disjoint outer test blocks.

    Outer blocks are never recycled into later training, selection, diagnostics,
    or continuation.  The historical function name is retained for API
    compatibility, but the statistical contract is now a fixed-development
    nested holdout.
    """

    required = policy.minimum_train_size + policy.outer_fold_count * policy.outer_test_size
    if row_count < required:
        raise ValidationError(f"joint validation needs at least {required} rows, received {row_count}")
    folds: list[NestedTimeSeriesFold] = []
    for index in range(policy.outer_fold_count):
        train_end = policy.minimum_train_size
        validation_size = max(1, int(train_end * policy.inner_validation_fraction))
        validation_start = train_end - validation_size
        test_start = policy.minimum_train_size + index * policy.outer_test_size
        folds.append(
            NestedTimeSeriesFold(
                fold_id=f"outer-{index + 1:02d}",
                outer_train_start=0,
                outer_train_end=train_end,
                inner_train_end=validation_start,
                inner_validation_start=validation_start,
                inner_validation_end=train_end,
                outer_test_start=test_start,
                outer_test_end=test_start + policy.outer_test_size,
            )
        )
    return tuple(folds)


def run_joint_mechanism_research(
    *,
    family: JointPolicyFamily,
    attempt_registry: JointPolicyAttemptRegistry,
    candidates: Sequence[JointPolicyCandidate],
    feature_rows: Sequence[Mapping[str, float]],
    forward_returns: Sequence[float],
    feature_materialization_receipt: Mapping[str, object],
    observation_dates: Sequence[str],
    sample_end_date: str,
    baseline_actions: Sequence[float] | None = None,
    validation_policy: JointValidationPolicy | None = None,
    formula_derived_residual_candidates_available: bool = False,
    residual_gap_classification: ResidualGapClassification = "registered_family_exhausted",
) -> JointMechanismResearchResult:
    """Select only inside outer training and evaluate frozen policies outside it."""

    policy = validation_policy or JointValidationPolicy()
    attempt_set_digest = attempt_registry.require_registered(family, candidates)
    _validate_inputs(
        family,
        candidates,
        feature_rows,
        forward_returns,
        baseline_actions,
        sample_end_date,
    )
    folds = build_expanding_nested_splits(len(feature_rows), policy)
    candidate_actions = {candidate.policy_id: evaluate_joint_policy(candidate, feature_rows) for candidate in candidates}
    baseline = tuple(baseline_actions) if baseline_actions is not None else (0.0,) * len(feature_rows)
    validate_materialized_rows_against_receipt(
        receipt=feature_materialization_receipt,
        feature_rows=feature_rows,
        forward_returns=forward_returns,
        baseline_actions=baseline,
        observation_dates=observation_dates,
        expected_graph_digest=family.formula_graph_digest,
    )
    if (
        feature_materialization_receipt.get("tool_id") != family.tool_id
        or feature_materialization_receipt.get("derivation_package_digest") != family.derivation_package_digest
        or float(str(feature_materialization_receipt.get("cost_bps"))) != policy.cost_bps
        or tuple(
            cast(
                Sequence[object],
                feature_materialization_receipt.get("feature_columns", ()),
            )
        )
        != tuple(feature_rows[0])
    ):
        raise ValidationError("joint research feature materialization binding changed")
    selected_ids: list[str] = []
    fold_rows: list[Mapping[str, object]] = []
    outer_deltas: list[float] = []
    outer_event_deltas: list[float] = []
    coverage_gate_passes: list[bool] = []
    for fold in folds:
        selected, coverage_by_policy, coverage_gate_passed, behavior_unique_candidate_count = (
            _select_development_candidate(
                candidates=candidates,
                candidate_actions=candidate_actions,
                feature_rows=feature_rows,
                baseline_actions=baseline,
                selection_returns=forward_returns,
                start=fold.outer_train_start,
                end=fold.outer_train_end,
                selection_start=fold.inner_validation_start,
                selection_end=fold.inner_validation_end,
                policy=policy,
            )
        )
        coverage_gate_passes.append(coverage_gate_passed)
        selected_ids.append(selected.policy_id)
        actions = candidate_actions[selected.policy_id]
        candidate_utility, event_values = _net_utility_with_events(
            actions,
            forward_returns,
            fold.outer_test_start,
            fold.outer_test_end,
            policy.cost_bps,
        )
        baseline_utility, baseline_events = _net_utility_with_events(
            baseline,
            forward_returns,
            fold.outer_test_start,
            fold.outer_test_end,
            policy.cost_bps,
        )
        delta = candidate_utility - baseline_utility
        outer_deltas.append(delta)
        outer_event_deltas.extend(
            candidate_event - baseline_event
            for candidate_event, baseline_event in zip(
                event_values,
                baseline_events,
                strict=True,
            )
        )
        fold_rows.append(
            {
                "fold_id": fold.fold_id,
                "inner_selection_end_exclusive": fold.inner_validation_end,
                "outer_test_start": fold.outer_test_start,
                "outer_test_end_exclusive": fold.outer_test_end,
                "selected_policy_id": selected.policy_id,
                "selected_policy_digest": selected.semantic_digest,
                "candidate_net_utility": candidate_utility,
                "baseline_net_utility": baseline_utility,
                "net_utility_delta": delta,
                "outer_data_used_for_inner_selection": False,
                "training_coverage_gate_passed": coverage_gate_passed,
                "training_coverage_by_policy": coverage_by_policy,
                "behavior_unique_candidate_count": behavior_unique_candidate_count,
            }
        )
    total_delta = sum(outer_deltas)
    positive_folds = sum(value > 0.0 for value in outer_deltas)
    tail_share = _positive_tail_share(outer_event_deltas)
    max_t_pvalue = _permutation_max_t_pvalue(
        candidates=candidates,
        candidate_actions=candidate_actions,
        forward_returns=forward_returns,
        folds=folds,
        baseline_actions=baseline,
        feature_rows=feature_rows,
        policy=policy,
        observed_total_delta=total_delta,
    )
    accepted = (
        total_delta > 0.0
        and median(outer_deltas) > 0.0
        and positive_folds >= policy.minimum_positive_outer_folds
        and max_t_pvalue <= policy.family_alpha
        and tail_share <= policy.maximum_positive_tail_contribution_share
        and all(coverage_gate_passes)
    )
    decision_status: AssessmentStatus
    if not all(coverage_gate_passes):
        decision_status = "underpowered_defer"
    elif accepted:
        decision_status = "accepted_joint_policy"
    else:
        decision_status = "rejected_joint_policy"
    by_id = {candidate.policy_id: candidate for candidate in candidates}
    # The frozen member is selected only inside the permanent development
    # window. Every outer block remains accept/reject-only forever.
    selection_votes = {policy_id: selected_ids.count(policy_id) for policy_id in set(selected_ids)}
    final_policy_id = max(selection_votes, key=lambda item: (selection_votes[item], item))
    final_candidate = by_id[final_policy_id]
    diagnostic_end = folds[0].outer_test_start
    diagnostic_actions = candidate_actions[final_policy_id][:diagnostic_end]
    diagnostic_baseline = baseline[:diagnostic_end]
    diagnostic_returns = forward_returns[:diagnostic_end]
    atomic_evidence = _atomic_marginal_evidence(
        atom_ids=family.atom_attribute_ids,
        feature_rows=feature_rows[:diagnostic_end],
        forward_returns=diagnostic_returns,
    )
    oracle_gap = _oracle_gap_evidence(
        actions=diagnostic_actions,
        baseline_actions=diagnostic_baseline,
        forward_returns=diagnostic_returns,
    )
    oracle_gap["evidence_scope"] = "permanent_development_window_only"
    oracle_gap["diagnostic_end_exclusive"] = diagnostic_end
    oracle_gap["outer_outcomes_used_for_continuation"] = False
    assessment = JointMechanismAssessment(
        assessment_id=(
            "joint-assessment:"
            + canonical_digest(
                {
                    "family": family.to_dict()["semantic_digest"],
                    "selected_policy_ids": selected_ids,
                    "fold_evidence": fold_rows,
                }
            ).removeprefix("sha256:")[:24]
        ),
        family_id=family.family_id,
        family_semantic_digest=require_digest(
            family.to_dict()["semantic_digest"],
            field="family semantic_digest",
        ),
        atomic_marginal_evidence=atomic_evidence,
        joint_outer_oos_evidence={
            "nested_time_series_oos": True,
            "permanent_development_window": True,
            "outer_blocks_never_recycled": True,
            "development_end_exclusive": diagnostic_end,
            "outer_data_used_for_inner_selection": False,
            "outer_outcomes_used_for_diagnostics": False,
            "outer_outcomes_used_for_continuation": False,
            "registered_policy_attempt_count_evaluated": len(candidates),
            "post_2020_rows_used": 0,
            "sample_end_date": sample_end_date,
            "action_semantics": "after_close_signal_next_bar_forward_return",
            "attempt_set_digest": attempt_set_digest,
            "feature_materialization_digest": feature_materialization_receipt["semantic_digest"],
            "outer_fold_evidence": fold_rows,
            "positive_outer_folds": positive_folds,
            "total_net_utility_delta": total_delta,
            "median_fold_net_utility_delta": median(outer_deltas),
            "positive_tail_contribution_share": tail_share,
            "cost_bps": policy.cost_bps,
            "training_coverage_all_folds_passed": all(coverage_gate_passes),
            "training_coverage_fold_pass_count": sum(coverage_gate_passes),
        },
        multiplicity_evidence={
            "family_wide_correction_applied": True,
            "registered_policy_attempt_count_denominator": len(candidates),
            "method": "fixed_development_full_selection_replay_permutation_maxT",
            "selection_procedure_replayed": True,
            "coverage_gate_replayed": True,
            "behavior_deduplication_replayed": True,
            "adjusted_pvalue": max_t_pvalue,
            "permutation_count": policy.permutation_count,
            "permutation_block_size": policy.permutation_block_size,
            "attempt_set_digest": attempt_set_digest,
        },
        oracle_gap_evidence=oracle_gap,
        decision_status=decision_status,
        decision_reason_zh=(
            "完整联合策略家族通过嵌套时序样本外、成本、尾部与maxT门"
            if decision_status == "accepted_joint_policy"
            else (
                "训练折覆盖、叶可达性或状态切换不足，延后而非否定联合机制"
                if decision_status == "underpowered_defer"
                else "完整联合策略家族未同时通过嵌套时序样本外、成本、尾部与maxT门"
            )
        ),
        stage3_handoff_eligible=accepted,
    )
    diagnostic_remaining_gap_ratio = _finite_number(
        oracle_gap["remaining_gap_ratio"],
        "remaining gap ratio",
    )
    continuation = (
        ResidualContinuationDecision(
            status="underpowered_collect_support",
            remaining_gap_ratio=diagnostic_remaining_gap_ratio,
            required_registration=None,
            reason_zh="训练覆盖或样本支持不足，延后裁决且不追加因子深度",
        )
        if not all(coverage_gate_passes)
        else _route_material_residual(
            remaining_gap_ratio=diagnostic_remaining_gap_ratio,
            formula_derived_candidates_available=(formula_derived_residual_candidates_available),
            gap_classification=residual_gap_classification,
            threshold=policy.residual_gap_ratio_for_continuation,
        )
    )
    return JointMechanismResearchResult(
        family=family,
        attempt_set_digest=attempt_set_digest,
        feature_materialization_ref={
            "receipt_id": feature_materialization_receipt["receipt_id"],
            "semantic_digest": feature_materialization_receipt["semantic_digest"],
            "graph_digest": feature_materialization_receipt["graph_digest"],
            "derivation_package_digest": feature_materialization_receipt["derivation_package_digest"],
            "factor_spec_digests": feature_materialization_receipt["factor_spec_digests"],
            "benchmark_spec_digest": feature_materialization_receipt["benchmark_spec_digest"],
            "frequency": feature_materialization_receipt["frequency"],
            "parameters_digest": feature_materialization_receipt["parameters_digest"],
            "provenance_binding_digest": feature_materialization_receipt["provenance_binding_digest"],
            "dataset_ref": feature_materialization_receipt["dataset_ref"],
            "dataset_sha256": feature_materialization_receipt["dataset_sha256"],
            "raw_kline_content_digest": feature_materialization_receipt["raw_kline_content_digest"],
            "observation_dates_digest": feature_materialization_receipt["observation_dates_digest"],
            "feature_rows_digest": feature_materialization_receipt["feature_rows_digest"],
            "baseline_action_digest": feature_materialization_receipt["baseline_action_digest"],
            "forward_return_digest": feature_materialization_receipt["forward_return_digest"],
            "cost_bps": feature_materialization_receipt["cost_bps"],
        },
        selected_policy_ids=tuple(selected_ids),
        selected_policy_digests=tuple(by_id[policy_id].semantic_digest for policy_id in selected_ids),
        final_frozen_policy_id=final_candidate.policy_id,
        final_frozen_policy_digest=final_candidate.semantic_digest,
        final_frozen_policy_expression=final_candidate.expression,
        final_frozen_policy_complexity={
            "coefficient_count": final_candidate.coefficient_count,
            "exponent_count": final_candidate.exponent_count,
            "branch_count": final_candidate.branch_count,
            "threshold_count": final_candidate.threshold_count,
            "scale_count": final_candidate.scale_count,
            "state_memory_count": final_candidate.state_memory_count,
        },
        final_refit_evidence={
            "selection_scope": "permanent_development_inner_consensus_only",
            "outer_outcomes_used_for_handoff_selection": False,
            "outer_outcomes_used_for_diagnostics": False,
            "outer_outcomes_used_for_continuation": False,
            "selection_votes": dict(sorted(selection_votes.items())),
            "selection_policy": policy.to_dict(),
            "coverage_gate_passed": all(coverage_gate_passes),
        },
        fold_evidence=tuple(fold_rows),
        assessment=assessment,
        continuation=continuation,
    )


def recompute_development_selection_consensus(
    *,
    family: JointPolicyFamily,
    candidates: Sequence[JointPolicyCandidate],
    feature_rows: Sequence[Mapping[str, float]],
    forward_returns: Sequence[float],
    baseline_actions: Sequence[float],
    validation_policy: JointValidationPolicy,
) -> dict[str, object]:
    """Recompute only the permanent-development winner, never outer outcomes."""

    if not feature_rows or not (
        len(feature_rows) == len(forward_returns) == len(baseline_actions)
    ):
        raise ValidationError("development selection inputs are not aligned")
    if not candidates or any(candidate.family_id != family.family_id for candidate in candidates):
        raise ValidationError("development selection candidates do not match the registered family")
    folds = build_expanding_nested_splits(len(feature_rows), validation_policy)
    candidate_actions = {
        candidate.policy_id: evaluate_joint_policy(candidate, feature_rows)
        for candidate in candidates
    }
    selected_ids: list[str] = []
    selected_digests: list[str] = []
    for fold in folds:
        selected, _, _, _ = _select_development_candidate(
            candidates=candidates,
            candidate_actions=candidate_actions,
            feature_rows=feature_rows,
            baseline_actions=baseline_actions,
            selection_returns=forward_returns,
            start=fold.outer_train_start,
            end=fold.outer_train_end,
            selection_start=fold.inner_validation_start,
            selection_end=fold.inner_validation_end,
            policy=validation_policy,
        )
        selected_ids.append(selected.policy_id)
        selected_digests.append(selected.semantic_digest)
    votes = {policy_id: selected_ids.count(policy_id) for policy_id in set(selected_ids)}
    winner = max(votes, key=lambda item: (votes[item], item))
    by_id = {candidate.policy_id: candidate for candidate in candidates}
    return {
        "selected_policy_ids": selected_ids,
        "selected_policy_digests": selected_digests,
        "selection_votes": dict(sorted(votes.items())),
        "final_policy_id": winner,
        "final_policy_digest": by_id[winner].semantic_digest,
        "selection_rule": "permanent_development_inner_consensus_only",
    }


def _policy_integer(payload: Mapping[str, object], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"joint validation policy {field} must be an integer")
    return value


def _policy_float(payload: Mapping[str, object], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"joint validation policy {field} must be numeric")
    parsed = float(value)
    if not isfinite(parsed):
        raise ValidationError(f"joint validation policy {field} must be finite")
    return parsed


def decide_residual_continuation(
    *,
    assessment: JointMechanismAssessment,
    remaining_gap_ratio: float,
    formula_derived_candidates_available: bool,
    gap_classification: ResidualGapClassification,
    threshold: float,
) -> ResidualContinuationDecision:
    """Request another registered family only when accepted residual remains material."""

    if assessment.decision_status == "underpowered_defer":
        return ResidualContinuationDecision(
            status="underpowered_collect_support",
            remaining_gap_ratio=remaining_gap_ratio,
            required_registration=None,
            reason_zh="训练覆盖或样本支持不足，延后裁决且不追加因子深度",
        )
    if assessment.decision_status != "accepted_joint_policy":
        return ResidualContinuationDecision(
            status="no_continuation_rejected",
            remaining_gap_ratio=remaining_gap_ratio,
            required_registration=None,
            reason_zh="当前联合策略未接受，不以追加原子掩盖失败",
        )
    return _route_material_residual(
        remaining_gap_ratio=remaining_gap_ratio,
        formula_derived_candidates_available=formula_derived_candidates_available,
        gap_classification=gap_classification,
        threshold=threshold,
    )


def _route_material_residual(
    *,
    remaining_gap_ratio: float,
    formula_derived_candidates_available: bool,
    gap_classification: ResidualGapClassification,
    threshold: float,
) -> ResidualContinuationDecision:
    """Route diagnostic residuals without consulting any outer OOS outcome."""

    if remaining_gap_ratio <= threshold:
        return ResidualContinuationDecision(
            status="residual_exhausted_stop",
            remaining_gap_ratio=remaining_gap_ratio,
            required_registration=None,
            reason_zh="剩余Oracle缺口低于事前阈值，无需新增联合家族",
        )
    if gap_classification == "formula_internal_path":
        return ResidualContinuationDecision(
            status="return_to_formula_derivation",
            remaining_gap_ratio=remaining_gap_ratio,
            required_registration="versioned_formula_derivation_package",
            reason_zh="剩余缺口来自公式内部路径遗漏，返回第一段升版推导包",
        )
    if gap_classification == "insufficient_sample_support":
        return ResidualContinuationDecision(
            status="underpowered_collect_support",
            remaining_gap_ratio=remaining_gap_ratio,
            required_registration=None,
            reason_zh="剩余缺口样本支持不足，不扩大因子或策略家族",
        )
    if gap_classification == "registered_family_exhausted":
        return ResidualContinuationDecision(
            status="registered_family_exhausted_stop",
            remaining_gap_ratio=remaining_gap_ratio,
            required_registration=None,
            reason_zh="已穷尽事前登记家族，按停止规则结束本轮",
        )
    if formula_derived_candidates_available:
        return ResidualContinuationDecision(
            status="registered_residual_family_required",
            remaining_gap_ratio=remaining_gap_ratio,
            required_registration="new_complete_formula_derived_joint_policy_family",
            reason_zh="仍有实质残差；先注册新的完整公式派生家族再验证",
        )
    return ResidualContinuationDecision(
        status="return_to_external_factor_registration",
        remaining_gap_ratio=remaining_gap_ratio,
        required_registration="internal_factor_pool_then_factor_spec_registration",
        reason_zh="公式外部市场状态缺少已注册候选，先过内部因子池与注册链",
    )


def _validate_inputs(
    family: JointPolicyFamily,
    candidates: Sequence[JointPolicyCandidate],
    feature_rows: Sequence[Mapping[str, float]],
    forward_returns: Sequence[float],
    baseline_actions: Sequence[float] | None,
    sample_end_date: str,
) -> None:
    if len(candidates) != family.registered_policy_attempt_count:
        raise ValidationError("every registered whole-policy attempt must be instantiated")
    if len({candidate.policy_id for candidate in candidates}) != len(candidates):
        raise ValidationError("joint-policy candidate identities must be unique")
    if not feature_rows or len(feature_rows) != len(forward_returns):
        raise ValidationError("joint research features and returns must align")
    if baseline_actions is not None and len(baseline_actions) != len(feature_rows):
        raise ValidationError("joint research baseline actions must align")
    try:
        parsed_end_date = date.fromisoformat(sample_end_date)
    except ValueError as exc:
        raise ValidationError("joint research sample_end_date must be ISO-8601") from exc
    if parsed_end_date > date(2020, 12, 31):
        raise ValidationError("joint research cannot open the sealed 2021-2026 interval")
    allowed = set(family.allowed_operators) | {"atom", "constant", "previous_action"}
    for candidate in candidates:
        if candidate.family_id != family.family_id:
            raise ValidationError("joint-policy candidate belongs to another family")
        atoms, operators = _expression_inventory(candidate.expression)
        if not atoms.issubset(family.atom_attribute_ids):
            raise ValidationError("joint-policy candidate uses an unregistered atom")
        if not operators.issubset(allowed):
            raise ValidationError("joint-policy candidate uses an unregistered operator")
        expected_counts = family.complexity_budget
        if (
            candidate.coefficient_count != expected_counts.coefficient_count
            or candidate.exponent_count != expected_counts.exponent_count
            or candidate.branch_count != expected_counts.branch_count
            or candidate.threshold_count != expected_counts.threshold_count
            or candidate.scale_count != expected_counts.scale_count
            or candidate.state_memory_count != expected_counts.state_memory_count
        ):
            raise ValidationError("joint-policy candidate does not carry the registered family budget")
    if any(not isfinite(value) for value in forward_returns):
        raise ValidationError("joint research returns must be finite")


def _net_utility(
    actions: Sequence[float],
    returns: Sequence[float],
    start: int,
    end: int,
    cost_bps: float,
) -> float:
    total, _ = _net_utility_with_events(actions, returns, start, end, cost_bps)
    return total


def _net_utility_with_events(
    actions: Sequence[float],
    returns: Sequence[float],
    start: int,
    end: int,
    cost_bps: float,
) -> tuple[float, list[float]]:
    previous = actions[start - 1] if start > 0 else 0.0
    events: list[float] = []
    cost = cost_bps / 10000.0
    for index in range(start, end):
        action = actions[index]
        events.append(action * returns[index] - abs(action - previous) * cost)
        previous = action
    return sum(events), events


def _positive_tail_share(events: Sequence[float]) -> float:
    positives = sorted((value for value in events if value > 0.0), reverse=True)
    if not positives:
        return 1.0
    tail_count = max(1, len(positives) // 10)
    return sum(positives[:tail_count]) / sum(positives)


def _permutation_max_t_pvalue(
    *,
    candidates: Sequence[JointPolicyCandidate],
    candidate_actions: Mapping[str, Sequence[float]],
    forward_returns: Sequence[float],
    folds: Sequence[NestedTimeSeriesFold],
    baseline_actions: Sequence[float],
    feature_rows: Sequence[Mapping[str, float]],
    policy: JointValidationPolicy,
    observed_total_delta: float,
) -> float:
    exceedances = 0
    row_count = len(forward_returns)
    # Coverage and behavior fingerprints depend only on the frozen features,
    # actions, baseline, fold, and policy.  Cache them once per fold while still
    # replaying the full selector for every permuted return path.
    coverage_selection_by_fold = {
        fold.fold_id: _coverage_selection_pool(
            candidates=candidates,
            candidate_actions=candidate_actions,
            feature_rows=feature_rows,
            baseline_actions=baseline_actions,
            start=fold.outer_train_start,
            end=fold.outer_train_end,
            policy=policy,
        )
        for fold in folds
    }
    for permutation in range(1, policy.permutation_count + 1):
        shifted = _time_block_permutation(
            forward_returns,
            block_size=policy.permutation_block_size,
            seed=permutation * 104729 + row_count,
        )
        selected_path_delta = 0.0
        for fold in folds:
            selected, _, _, _ = _select_development_candidate(
                candidates=candidates,
                candidate_actions=candidate_actions,
                feature_rows=feature_rows,
                baseline_actions=baseline_actions,
                selection_returns=shifted,
                start=fold.outer_train_start,
                end=fold.outer_train_end,
                selection_start=fold.inner_validation_start,
                selection_end=fold.inner_validation_end,
                policy=policy,
                precomputed_coverage_selection=coverage_selection_by_fold[fold.fold_id],
            )
            selected_path_delta += _net_utility(
                candidate_actions[selected.policy_id],
                shifted,
                fold.outer_test_start,
                fold.outer_test_end,
                policy.cost_bps,
            ) - _net_utility(
                baseline_actions,
                shifted,
                fold.outer_test_start,
                fold.outer_test_end,
                policy.cost_bps,
            )
        if selected_path_delta >= observed_total_delta:
            exceedances += 1
    return (exceedances + 1.0) / (policy.permutation_count + 1.0)


def _training_coverage_evidence(
    *,
    candidate: JointPolicyCandidate,
    actions: Sequence[float],
    feature_rows: Sequence[Mapping[str, float]],
    baseline_actions: Sequence[float],
    start: int,
    end: int,
    policy: JointValidationPolicy,
) -> dict[str, object]:
    operators = _expression_inventory(candidate.expression)[1]
    row_count = end - start
    disagreements = sum(abs(actions[index] - baseline_actions[index]) > 1e-12 for index in range(start, end))
    transitions = sum(abs(actions[index] - actions[index - 1]) > 1e-12 for index in range(max(start + 1, 1), end))
    branch_leaf_share = _minimum_branch_leaf_share(
        expression=candidate.expression,
        feature_rows=feature_rows,
        actions=actions,
        start=start,
        end=end,
    )
    disagreement_ratio = disagreements / row_count
    branch_passed = (
        branch_leaf_share >= policy.minimum_branch_leaf_share if operators.intersection({"threshold_branch", "state_transition"}) else True
    )
    state_passed = transitions >= policy.minimum_state_transition_count if "state_transition" in operators else True
    passed = disagreement_ratio >= policy.minimum_action_disagreement_ratio and branch_passed and state_passed
    fingerprint = canonical_digest({"actions": [round(actions[index], 12) for index in range(start, end)]})
    return {
        "coverage_gate_passed": passed,
        "action_disagreement_ratio": disagreement_ratio,
        "minimum_branch_leaf_share": branch_leaf_share,
        "state_transition_count": transitions,
        "branch_coverage_passed": branch_passed,
        "state_coverage_passed": state_passed,
        "behavior_fingerprint": fingerprint,
        "behavior_deduplication_scope": "permanent_development_window_only",
    }


def _coverage_selection_pool(
    *,
    candidates: Sequence[JointPolicyCandidate],
    candidate_actions: Mapping[str, Sequence[float]],
    feature_rows: Sequence[Mapping[str, float]],
    baseline_actions: Sequence[float],
    start: int,
    end: int,
    policy: JointValidationPolicy,
) -> tuple[tuple[JointPolicyCandidate, ...], dict[str, Mapping[str, object]]]:
    coverage_by_policy: dict[str, Mapping[str, object]] = {}
    behavior_representatives: dict[str, JointPolicyCandidate] = {}
    for candidate in candidates:
        evidence = _training_coverage_evidence(
            candidate=candidate,
            actions=candidate_actions[candidate.policy_id],
            feature_rows=feature_rows,
            baseline_actions=baseline_actions,
            start=start,
            end=end,
            policy=policy,
        )
        coverage_by_policy[candidate.policy_id] = evidence
        if evidence["coverage_gate_passed"] is not True:
            continue
        fingerprint = str(evidence["behavior_fingerprint"])
        existing = behavior_representatives.get(fingerprint)
        if existing is None or candidate.policy_id < existing.policy_id:
            behavior_representatives[fingerprint] = candidate
    representatives = tuple(sorted(behavior_representatives.values(), key=lambda candidate: candidate.policy_id))
    return representatives, coverage_by_policy


def _select_development_candidate(
    *,
    candidates: Sequence[JointPolicyCandidate],
    candidate_actions: Mapping[str, Sequence[float]],
    feature_rows: Sequence[Mapping[str, float]],
    baseline_actions: Sequence[float],
    selection_returns: Sequence[float],
    start: int,
    end: int,
    selection_start: int,
    selection_end: int,
    policy: JointValidationPolicy,
    precomputed_coverage_selection: tuple[
        tuple[JointPolicyCandidate, ...],
        dict[str, Mapping[str, object]],
    ]
    | None = None,
) -> tuple[
    JointPolicyCandidate,
    dict[str, Mapping[str, object]],
    bool,
    int,
]:
    """Replay the exact observed coverage, deduplication, and utility selector."""

    if precomputed_coverage_selection is None:
        selection_pool, coverage_by_policy = _coverage_selection_pool(
            candidates=candidates,
            candidate_actions=candidate_actions,
            feature_rows=feature_rows,
            baseline_actions=baseline_actions,
            start=start,
            end=end,
            policy=policy,
        )
    else:
        selection_pool, coverage_by_policy = precomputed_coverage_selection
    coverage_gate_passed = bool(selection_pool)
    behavior_unique_candidate_count = len(selection_pool)
    effective_pool = selection_pool or tuple(candidates)
    selected = max(
        effective_pool,
        key=lambda candidate: (
            _net_utility(
                candidate_actions[candidate.policy_id],
                selection_returns,
                selection_start,
                selection_end,
                policy.cost_bps,
            ),
            candidate.policy_id,
        ),
    )
    return (
        selected,
        coverage_by_policy,
        coverage_gate_passed,
        behavior_unique_candidate_count,
    )


def _minimum_branch_leaf_share(
    *,
    expression: PolicyExpression,
    feature_rows: Sequence[Mapping[str, float]],
    actions: Sequence[float],
    start: int,
    end: int,
) -> float:
    branch_nodes = _branch_nodes(expression)
    if not branch_nodes:
        return 1.0
    minimum_share = 1.0
    for branch in branch_nodes:
        children = _expression_children(branch)
        if len(children) != 3:
            raise ValidationError("joint-policy branch requires three arguments")
        threshold = _finite_number(branch.get("threshold"), "branch threshold")
        true_count = 0
        for index in range(start, end):
            previous_action = actions[index - 1] if index > 0 else 0.0
            condition = _evaluate_expression(
                children[0],
                row=feature_rows[index],
                previous_action=previous_action,
            )
            true_count += condition >= threshold
        false_count = end - start - true_count
        minimum_share = min(minimum_share, true_count / (end - start), false_count / (end - start))
    return minimum_share


def _time_block_permutation(
    values: Sequence[float],
    *,
    block_size: int,
    seed: int,
) -> tuple[float, ...]:
    blocks = [tuple(values[index : index + block_size]) for index in range(0, len(values), block_size)]
    Random(seed).shuffle(blocks)
    return tuple(value for block in blocks for value in block)


def _atomic_marginal_evidence(
    *,
    atom_ids: Sequence[str],
    feature_rows: Sequence[Mapping[str, float]],
    forward_returns: Sequence[float],
) -> dict[str, object]:
    evidence: dict[str, object] = {
        "admission_gate_applied": False,
        "evidence_scope": "train_and_inner_validation_only",
        "outer_outcomes_used": False,
    }
    for atom_id in atom_ids:
        values = [row[atom_id] for row in feature_rows]
        mean_x = sum(values) / len(values)
        mean_y = sum(forward_returns) / len(forward_returns)
        covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(values, forward_returns, strict=True))
        variance_x = sum((x - mean_x) ** 2 for x in values)
        variance_y = sum((y - mean_y) ** 2 for y in forward_returns)
        correlation = covariance / (variance_x * variance_y) ** 0.5 if variance_x > 0.0 and variance_y > 0.0 else 0.0
        evidence[atom_id] = {
            "pearson": correlation,
            "status": "reported_not_admission_gate",
        }
    return evidence


def _oracle_gap_evidence(
    *,
    actions: Sequence[float],
    baseline_actions: Sequence[float],
    forward_returns: Sequence[float],
) -> dict[str, object]:
    oracle_utility = sum(abs(value) for value in forward_returns)
    baseline_utility = sum(action * value for action, value in zip(baseline_actions, forward_returns, strict=True))
    candidate_utility = sum(action * value for action, value in zip(actions, forward_returns, strict=True))
    total_gap = max(0.0, oracle_utility - baseline_utility)
    recovered = min(max(candidate_utility - baseline_utility, 0.0), total_gap)
    remaining = total_gap - recovered
    return {
        "total_oracle_gap": total_gap,
        "gross_gap_recovered": recovered,
        "remaining_gap": remaining,
        "remaining_gap_ratio": remaining / total_gap if total_gap else 0.0,
        "event_count": len(forward_returns),
    }


__all__ = [
    "ContinuationStatus",
    "JointMechanismResearchResult",
    "JointPolicyCandidate",
    "JointValidationPolicy",
    "NestedTimeSeriesFold",
    "ResidualContinuationDecision",
    "ResidualGapClassification",
    "build_expanding_nested_splits",
    "decide_residual_continuation",
    "evaluate_joint_policy",
    "validate_joint_mechanism_research_result",
    "recompute_development_selection_consensus",
    "run_joint_mechanism_research",
]
