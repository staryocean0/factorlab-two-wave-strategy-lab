"""Stage-3 mechanical replay of an accepted, immutable joint policy."""

# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Final, Literal, cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.formula_derivation.materialization import (
    validate_materialized_rows_against_receipt,
)
from factor_lab.market_state.formula_derivation.validation import (
    require_digest,
    require_exact_keys,
    require_zero_authority,
    validate_semantic_digest,
)
from factor_lab.market_state.joint_policy_attempt_registry import (
    JointPolicyAttemptRegistry,
    JointPolicyCandidate,
    require_candidate_in_registered_attempt_manifest,
)
from factor_lab.market_state.joint_policy_family_registry import (
    JointPolicyFamily,
    JointPolicyFamilyRegistry,
)
from factor_lab.market_state.joint_policy_runtime import evaluate_joint_policy
from factor_lab.market_state.joint_research_decision_package import (
    JointResearchDecisionPackage,
    validate_joint_research_decision_package,
)

BACKTEST_ACCEPTANCE_SCHEMA_ID: Final[str] = "market_state_backtest_acceptance_package@1.0"
_BACKTEST_ACCEPTANCE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_id", "package_id", "decision_package_ref", "replay_status",
        "failure_type", "failure_reason_zh", "frozen_policy_digest",
        "replay_action_digest", "causal_evidence", "aggregate_backtest_evidence",
        "evidence_mode", "independent_holdout_evidence",
        "action_detail_exposed", "stage3_may_modify_rule", "production_authority",
        "dynamic_parameter_authority", "tool_routing_authority", "field_labels_zh",
        "semantic_digest",
    }
)
ReplayStatus = Literal["accepted_frozen_replay", "return_to_formula_derivation"]
FailureType = Literal["none", "implementation", "causal", "coverage", "backtest", "robustness"]


@dataclass(frozen=True, slots=True)
class BacktestAcceptancePackage:
    """Aggregate-only replay evidence; no rule search or trade-level disclosure."""

    package_id: str
    decision_package_ref: Mapping[str, object]
    replay_status: ReplayStatus
    failure_type: FailureType
    failure_reason_zh: str
    frozen_policy_digest: str
    replay_action_digest: str
    causal_evidence: Mapping[str, object]
    aggregate_backtest_evidence: Mapping[str, object]
    evidence_mode: Literal["mechanical_same_dataset_replay"] = (
        "mechanical_same_dataset_replay"
    )
    independent_holdout_evidence: bool = False
    action_detail_exposed: bool = False
    stage3_may_modify_rule: bool = False
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        if not self.package_id.strip():
            raise ValidationError("backtest acceptance identity is required")
        _ = require_digest(self.frozen_policy_digest, field="frozen_policy_digest")
        _ = require_digest(self.replay_action_digest, field="replay_action_digest")
        expected_failure = self.replay_status != "accepted_frozen_replay"
        if (self.failure_type != "none") != expected_failure:
            raise ValidationError("backtest acceptance status and failure type disagree")
        if expected_failure != bool(self.failure_reason_zh.strip()):
            raise ValidationError("backtest acceptance failure reason disagrees with status")
        if self.action_detail_exposed or self.stage3_may_modify_rule:
            raise ValidationError("Stage 3 cannot expose trade detail or modify the frozen rule")
        if (
            self.evidence_mode != "mechanical_same_dataset_replay"
            or self.independent_holdout_evidence
        ):
            raise ValidationError(
                "Stage 3 is mechanical same-dataset replay, not independent holdout evidence"
            )
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("backtest acceptance cannot grant authority")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": BACKTEST_ACCEPTANCE_SCHEMA_ID,
            "package_id": self.package_id,
            "decision_package_ref": dict(self.decision_package_ref),
            "replay_status": self.replay_status,
            "failure_type": self.failure_type,
            "failure_reason_zh": self.failure_reason_zh,
            "frozen_policy_digest": self.frozen_policy_digest,
            "replay_action_digest": self.replay_action_digest,
            "causal_evidence": dict(self.causal_evidence),
            "aggregate_backtest_evidence": dict(self.aggregate_backtest_evidence),
            "evidence_mode": self.evidence_mode,
            "independent_holdout_evidence": self.independent_holdout_evidence,
            "action_detail_exposed": self.action_detail_exposed,
            "stage3_may_modify_rule": self.stage3_may_modify_rule,
            "production_authority": self.production_authority,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "field_labels_zh": {
                "decision_package_ref": "第二段联合决定包引用",
                "replay_status": "冻结规则机械重放裁决",
                "failure_type": "类型化失败类别",
                "causal_evidence": "前缀、追加与状态恢复证据",
                "aggregate_backtest_evidence": "不含逐笔拆解的聚合回测证据",
                "evidence_mode": "第三段证据模式",
                "independent_holdout_evidence": "是否构成独立留出证据",
                "action_detail_exposed": "是否暴露逐笔动作或盈亏",
                "stage3_may_modify_rule": "第三段是否可修改规则",
            },
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload


def replay_frozen_joint_policy(
    *,
    decision: JointResearchDecisionPackage,
    feature_rows: Sequence[Mapping[str, float]],
    forward_returns: Sequence[float],
    feature_materialization_receipt: Mapping[str, object],
    observation_dates: Sequence[str],
    sample_end_date: str,
    baseline_actions: Sequence[float] | None = None,
    registered_policy_attempt_manifest: Mapping[str, object] | None = None,
    registered_family: JointPolicyFamily | None = None,
) -> BacktestAcceptancePackage:
    """Replay exactly one accepted rule and return aggregate black-box evidence."""

    decision_payload = decision.to_dict()
    validate_joint_research_decision_package(decision_payload)
    decision_digest = require_digest(
        decision_payload["semantic_digest"],
        field="decision semantic_digest",
    )
    frozen = decision.frozen_joint_policy
    fallback_digest = canonical_digest({"decision_semantic_digest": decision_digest})
    if decision.decision_status != "accepted_joint_policy" or not decision.stage3_handoff_eligible:
        return _failure(
            decision=decision,
            decision_digest=decision_digest,
            frozen_policy_digest=fallback_digest,
            failure_type="implementation",
            reason_zh="只有 accepted_joint_policy 可进入第三段机械重放",
        )
    frozen_digest = _digest_value(frozen.get("semantic_digest"))
    if frozen_digest is None:
        return _failure(
            decision=decision,
            decision_digest=decision_digest,
            frozen_policy_digest=fallback_digest,
            failure_type="implementation",
            reason_zh="冻结规则缺少合法的候选语义摘要",
        )
    if len(feature_rows) < 4 or len(feature_rows) != len(forward_returns):
        return _failure(
            decision=decision,
            decision_digest=decision_digest,
            frozen_policy_digest=frozen_digest,
            failure_type="backtest",
            reason_zh="第三段特征与前瞻收益长度不一致或样本不足",
        )
    if baseline_actions is not None and len(baseline_actions) != len(feature_rows):
        return _failure(
            decision=decision,
            decision_digest=decision_digest,
            frozen_policy_digest=frozen_digest,
            failure_type="backtest",
            reason_zh="第三段冻结基线动作长度不一致",
        )
    if any(not isfinite(value) for value in forward_returns) or (
        baseline_actions is not None and any(not isfinite(value) for value in baseline_actions)
    ):
        return _failure(
            decision=decision,
            decision_digest=decision_digest,
            frozen_policy_digest=frozen_digest,
            failure_type="backtest",
            reason_zh="第三段收益或冻结基线包含非有限值",
        )
    try:
        parsed_end_date = date.fromisoformat(sample_end_date)
    except ValueError:
        return _failure(
            decision=decision,
            decision_digest=decision_digest,
            frozen_policy_digest=frozen_digest,
            failure_type="causal",
            reason_zh="第三段样本截止日不是 ISO-8601",
        )
    if parsed_end_date > date(2020, 12, 31):
        return _failure(
            decision=decision,
            decision_digest=decision_digest,
            frozen_policy_digest=frozen_digest,
            failure_type="causal",
            reason_zh="第三段不得打开 2021—2026 密封区间",
        )
    raw_candidate = frozen.get("candidate")
    if not isinstance(raw_candidate, Mapping):
        return _failure(
            decision=decision,
            decision_digest=decision_digest,
            frozen_policy_digest=frozen_digest,
            failure_type="implementation",
            reason_zh="冻结规则缺少可独立重建的完整候选公式",
        )
    try:
        candidate = JointPolicyCandidate.from_dict(cast(Mapping[str, object], raw_candidate))
        if candidate.semantic_digest != frozen_digest:
            raise ValidationError("frozen candidate digest drifted")
        if registered_policy_attempt_manifest is None or registered_family is None:
            raise ValidationError("Stage-3 replay lacks the registered Stage-1 attempt set")
        require_candidate_in_registered_attempt_manifest(
            payload=registered_policy_attempt_manifest,
            family=registered_family,
            candidate=candidate,
            expected_attempt_set_digest=require_digest(
                frozen.get("attempt_set_digest"),
                field="frozen policy attempt-set digest",
            ),
        )
        actions = evaluate_joint_policy(candidate, feature_rows)
    except ValidationError:
        return _failure(
            decision=decision,
            decision_digest=decision_digest,
            frozen_policy_digest=frozen_digest,
            failure_type="implementation",
            reason_zh="冻结候选公式无法逐字重建或语义摘要漂移",
        )
    split = len(feature_rows) // 2
    historical_rows = feature_rows[:split]
    appended_rows = feature_rows[split:]
    historical_actions = evaluate_joint_policy(candidate, historical_rows)
    appended_replay_actions = evaluate_joint_policy(
        candidate,
        (*historical_rows, *appended_rows),
    )
    memory_values = cast(
        Sequence[object],
        candidate.derived_expression_topology.get("state_memory_bars_used", ()),
    )
    maximum_memory = max((int(str(value)) for value in memory_values), default=1)
    restored_suffix = evaluate_joint_policy(
        candidate,
        feature_rows[split:],
        initial_previous_action=actions[split - 1],
        initial_action_history=actions[max(0, split - maximum_memory) : split],
    )
    prefix_invariant = historical_actions == actions[:split]
    tail_append_preserves_history = (
        appended_replay_actions[:split] == historical_actions
        and appended_replay_actions == actions
    )
    state_restore_invariant = historical_actions + restored_suffix == actions
    if not prefix_invariant or not tail_append_preserves_history or not state_restore_invariant:
        return _failure(
            decision=decision,
            decision_digest=decision_digest,
            frozen_policy_digest=frozen_digest,
            failure_type="causal",
            reason_zh="冻结状态机未通过前缀不变或状态恢复不变量",
        )
    baseline = tuple(baseline_actions) if baseline_actions is not None else (0.0,) * len(actions)
    try:
        validate_materialized_rows_against_receipt(
            receipt=feature_materialization_receipt,
            feature_rows=feature_rows,
            forward_returns=forward_returns,
            baseline_actions=baseline,
            observation_dates=observation_dates,
            expected_graph_digest=str(decision.feature_materialization_ref.get("graph_digest", "")),
        )
        if (
            feature_materialization_receipt.get("semantic_digest") != decision.feature_materialization_ref.get("semantic_digest")
            or feature_materialization_receipt.get("feature_rows_digest") != decision.feature_materialization_ref.get("feature_rows_digest")
            or feature_materialization_receipt.get("observation_dates_digest")
            != decision.feature_materialization_ref.get("observation_dates_digest")
            or not observation_dates
            or str(observation_dates[-1])[:10] != sample_end_date
        ):
            raise ValidationError("Stage-3 feature materialization binding changed")
        selection_policy_payload = frozen.get("selection_policy")
        selection_consensus = frozen.get("selection_consensus")
        raw_attempts = registered_policy_attempt_manifest.get("complete_policy_attempts")
        if (
            not isinstance(selection_policy_payload, Mapping)
            or not isinstance(selection_consensus, Mapping)
            or not isinstance(raw_attempts, list)
        ):
            raise ValidationError("Stage-3 selection replay contract is incomplete")
        from factor_lab.market_state.joint_mechanism_research import (
            JointValidationPolicy,
            recompute_development_selection_consensus,
            run_joint_mechanism_research,
        )

        registered_candidates = tuple(
            JointPolicyCandidate.from_dict(cast(Mapping[str, object], row))
            for row in cast(list[object], raw_attempts)
            if isinstance(row, Mapping)
        )
        if len(registered_candidates) != len(raw_attempts):
            raise ValidationError("Stage-3 attempt set contains an invalid candidate")
        validation_policy = JointValidationPolicy.from_dict(cast(Mapping[str, object], selection_policy_payload))
        recomputed_consensus = recompute_development_selection_consensus(
            family=registered_family,
            candidates=registered_candidates,
            feature_rows=feature_rows,
            forward_returns=forward_returns,
            baseline_actions=baseline,
            validation_policy=validation_policy,
        )
        if dict(selection_consensus) != recomputed_consensus:
            raise ValidationError("Stage-3 frozen candidate was not selected on permanent development data")
        family_registry = JointPolicyFamilyRegistry()
        _ = family_registry.register(registered_family)
        rebuilt_attempt_registry = JointPolicyAttemptRegistry(family_registry)
        _ = rebuilt_attempt_registry.register(registered_family, registered_candidates)
        recomputed_research = run_joint_mechanism_research(
            family=registered_family,
            attempt_registry=rebuilt_attempt_registry,
            candidates=registered_candidates,
            feature_rows=feature_rows,
            forward_returns=forward_returns,
            feature_materialization_receipt=feature_materialization_receipt,
            observation_dates=observation_dates,
            sample_end_date=sample_end_date,
            baseline_actions=baseline,
            validation_policy=validation_policy,
        )
        if (
            recomputed_research.assessment.to_dict() != decision.assessment.to_dict()
            or recomputed_research.assessment.decision_status != "accepted_joint_policy"
            or not recomputed_research.assessment.stage3_handoff_eligible
            or recomputed_research.final_frozen_policy_id != candidate.policy_id
            or recomputed_research.final_frozen_policy_digest != candidate.semantic_digest
        ):
            raise ValidationError("Stage-3 outer acceptance provenance differs from an independent Stage-2 rerun")
    except ValidationError:
        return _failure(
            decision=decision,
            decision_digest=decision_digest,
            frozen_policy_digest=frozen_digest,
            failure_type="implementation",
            reason_zh="第三段输入、冻结物化收据或研发窗选择重放不一致",
        )
    cost_bps = _finite_nonnegative(frozen.get("cost_bps"))
    if cost_bps is None:
        return _failure(
            decision=decision,
            decision_digest=decision_digest,
            frozen_policy_digest=frozen_digest,
            failure_type="implementation",
            reason_zh="冻结规则缺少合法的非负交易成本",
        )
    if cost_bps != float(str(decision.feature_materialization_ref.get("cost_bps"))):
        return _failure(
            decision=decision,
            decision_digest=decision_digest,
            frozen_policy_digest=frozen_digest,
            failure_type="implementation",
            reason_zh="第三段冻结成本与特征物化收据不一致",
        )
    candidate_metrics = _aggregate_utility(actions, forward_returns, cost_bps)
    baseline_metrics = _aggregate_utility(baseline, forward_returns, cost_bps)
    action_digest = canonical_digest({"frozen_actions": list(actions)})
    aggregate = {
        "event_count": len(actions),
        "candidate_gross_utility": candidate_metrics["gross"],
        "candidate_total_cost": candidate_metrics["cost"],
        "candidate_net_utility": candidate_metrics["net"],
        "baseline_net_utility": baseline_metrics["net"],
        "net_utility_delta": candidate_metrics["net"] - baseline_metrics["net"],
        "cost_bps": cost_bps,
        "sample_end_date": sample_end_date,
        "post_2020_rows_used": 0,
        "trade_or_event_rows_emitted": 0,
    }
    causal = {
        "prefix_invariant": prefix_invariant,
        "tail_append_preserves_history": tail_append_preserves_history,
        "state_restore_invariant": state_restore_invariant,
        "signal_clock": "after_close",
        "execution_lag_bars": 1,
        "stage3_rule_modification_count": 0,
        "registered_attempt_membership_verified": True,
        "attempt_set_digest": frozen["attempt_set_digest"],
    }
    return BacktestAcceptancePackage(
        package_id="backtest-acceptance:" + action_digest.removeprefix("sha256:")[:24],
        decision_package_ref={
            "artifact_id": decision.package_id,
            "semantic_digest": decision_digest,
        },
        replay_status="accepted_frozen_replay",
        failure_type="none",
        failure_reason_zh="",
        frozen_policy_digest=frozen_digest,
        replay_action_digest=action_digest,
        causal_evidence=causal,
        aggregate_backtest_evidence=aggregate,
    )


def validate_backtest_acceptance_package(payload: Mapping[str, object]) -> None:
    if payload.get("schema_id") != BACKTEST_ACCEPTANCE_SCHEMA_ID:
        raise ValidationError("backtest acceptance schema changed")
    require_exact_keys(payload, _BACKTEST_ACCEPTANCE_KEYS, label="backtest acceptance package")
    validate_semantic_digest(payload)
    require_zero_authority(payload)
    if payload.get("action_detail_exposed") is not False:
        raise ValidationError("backtest acceptance exposed action detail")
    if payload.get("stage3_may_modify_rule") is not False:
        raise ValidationError("backtest acceptance allowed rule modification")
    if (
        payload.get("evidence_mode") != "mechanical_same_dataset_replay"
        or payload.get("independent_holdout_evidence") is not False
    ):
        raise ValidationError(
            "backtest acceptance misrepresented mechanical replay as independent evidence"
        )
    if any(
        payload.get(field) is not False
        for field in (
            "production_authority",
            "dynamic_parameter_authority",
            "tool_routing_authority",
        )
    ):
        raise ValidationError("backtest acceptance authority changed")
    status = payload.get("replay_status")
    failure_type = payload.get("failure_type")
    if (status == "accepted_frozen_replay") != (failure_type == "none"):
        raise ValidationError("backtest acceptance status and failure type disagree")
    causal = payload.get("causal_evidence")
    aggregate = payload.get("aggregate_backtest_evidence")
    if not isinstance(causal, Mapping) or not isinstance(aggregate, Mapping):
        raise ValidationError("backtest acceptance evidence is incomplete")
    if status == "accepted_frozen_replay":
        expected_causal_keys = {
            "prefix_invariant",
            "tail_append_preserves_history",
            "state_restore_invariant",
            "signal_clock",
            "execution_lag_bars",
            "stage3_rule_modification_count",
            "registered_attempt_membership_verified",
            "attempt_set_digest",
        }
        expected_aggregate_keys = {
            "event_count",
            "candidate_gross_utility",
            "candidate_total_cost",
            "candidate_net_utility",
            "baseline_net_utility",
            "net_utility_delta",
            "cost_bps",
            "sample_end_date",
            "post_2020_rows_used",
            "trade_or_event_rows_emitted",
        }
        if set(causal) != expected_causal_keys or set(aggregate) != expected_aggregate_keys:
            raise ValidationError("backtest acceptance contains unregistered nested evidence")
        if (
            causal.get("prefix_invariant") is not True
            or causal.get("tail_append_preserves_history") is not True
            or causal.get("state_restore_invariant") is not True
            or causal.get("signal_clock") != "after_close"
            or causal.get("execution_lag_bars") != 1
            or causal.get("stage3_rule_modification_count") != 0
            or causal.get("registered_attempt_membership_verified") is not True
        ):
            raise ValidationError("backtest acceptance causal evidence changed")
        _ = require_digest(causal.get("attempt_set_digest"), field="attempt_set_digest")
        event_count = aggregate.get("event_count")
        if isinstance(event_count, bool) or not isinstance(event_count, int) or event_count < 1:
            raise ValidationError("backtest acceptance event count is invalid")
        for field in (
            "candidate_gross_utility",
            "candidate_total_cost",
            "candidate_net_utility",
            "baseline_net_utility",
            "net_utility_delta",
            "cost_bps",
        ):
            value = aggregate.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
                raise ValidationError("backtest acceptance aggregate metric is invalid")
        try:
            sample_end = date.fromisoformat(str(aggregate.get("sample_end_date", "")))
        except ValueError as exc:
            raise ValidationError("backtest acceptance sample end date is invalid") from exc
        if sample_end > date(2020, 12, 31) or aggregate.get("post_2020_rows_used") != 0:
            raise ValidationError("backtest acceptance opened the sealed interval")
        if aggregate.get("trade_or_event_rows_emitted") != 0:
            raise ValidationError("backtest acceptance exposed trade or event rows")
    else:
        if dict(causal) != {"stage3_rule_modification_count": 0}:
            raise ValidationError("failed backtest acceptance causal evidence changed")
        if dict(aggregate) != {"trade_or_event_rows_emitted": 0}:
            raise ValidationError("failed backtest acceptance exposed nested evidence")


def _failure(
    *,
    decision: JointResearchDecisionPackage,
    decision_digest: str,
    frozen_policy_digest: str,
    failure_type: Literal["implementation", "causal", "coverage", "backtest", "robustness"],
    reason_zh: str,
) -> BacktestAcceptancePackage:
    action_digest = canonical_digest({"decision_semantic_digest": decision_digest, "failure_type": failure_type})
    return BacktestAcceptancePackage(
        package_id="backtest-failure:" + action_digest.removeprefix("sha256:")[:24],
        decision_package_ref={
            "artifact_id": decision.package_id,
            "semantic_digest": decision_digest,
        },
        replay_status="return_to_formula_derivation",
        failure_type=failure_type,
        failure_reason_zh=reason_zh,
        frozen_policy_digest=frozen_policy_digest,
        replay_action_digest=action_digest,
        causal_evidence={"stage3_rule_modification_count": 0},
        aggregate_backtest_evidence={"trade_or_event_rows_emitted": 0},
    )


def _aggregate_utility(
    actions: Sequence[float],
    returns: Sequence[float],
    cost_bps: float,
) -> dict[str, float]:
    previous = 0.0
    gross = 0.0
    total_cost = 0.0
    unit_cost = cost_bps / 10000.0
    for action, forward_return in zip(actions, returns, strict=True):
        if not isfinite(forward_return):
            raise ValidationError("backtest return must be finite")
        gross += action * forward_return
        total_cost += abs(action - previous) * unit_cost
        previous = action
    return {"gross": gross, "cost": total_cost, "net": gross - total_cost}


def _digest_value(value: object) -> str | None:
    if isinstance(value, str):
        try:
            return require_digest(value, field="frozen policy digest")
        except ValidationError:
            return None
    return None


def _finite_nonnegative(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if isfinite(numeric) and numeric >= 0.0 else None


__all__ = [
    "BACKTEST_ACCEPTANCE_SCHEMA_ID",
    "BacktestAcceptancePackage",
    "FailureType",
    "ReplayStatus",
    "replay_frozen_joint_policy",
    "validate_backtest_acceptance_package",
]
