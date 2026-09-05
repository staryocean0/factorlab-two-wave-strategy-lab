# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportCallIssue=false, reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Failure-conditioned, carrier-orthogonal factor gate for timing research.

The gate does not ask whether a raw feature predicts a generally good return.
It first removes the strategy's already-consumed carrier inputs, then asks a
much narrower causal question: does an extreme of the remaining information
identify unusually severe future absolute loss, relative loss to buy and hold,
or relative loss to the frozen static strategy?  This is a *research
eligibility* gate; it never grants a signal,
parameter, routing, or production permission.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, cast

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest

SCHEMA_ID: Final[str] = "market_state_timing_factor_failure_gate@1.0"
CODE_VERSION: Final[str] = "timing-factor-failure-gate-20260810-r4"
DEFAULT_OUTPUT_DIR: Final[Path] = Path("artifacts/market_state/timing_factor_failure_gate_v1")
CANONICAL_ENTRYPOINT: Final[str] = "docs/user/market_state_dynamic_parameter_reliability_workflow.md"

FailureTarget = Literal[
    "absolute_strategy_loss",
    "relative_buy_hold_loss",
    "relative_frozen_static_loss",
]
TailDirection = Literal["lower", "upper"]

BASE_COLUMNS: Final[tuple[str, ...]] = (
    "event_id",
    "independent_event_group_id",
    "comparison_id",
    "candidate_id",
    "phase",
    "factor_asof_time",
    "decision_time",
    "execution_time",
    "outcome_start_time",
    "outcome_end_exclusive",
    "factor_value",
    "strategy_net_log_return",
    "buy_hold_net_log_return",
    "carrier_manifest_digest",
    "factor_definition_digest",
    "opportunity_ledger_digest",
    "execution_semantics_digest",
    "cost_model_digest",
)
REQUIRED_PHASES: Final[tuple[str, ...]] = ("development", "repeat_audit")

FIELD_LABELS_ZH: Final[dict[str, str]] = {
    "event_id": "决策事件身份",
    "phase": "样本阶段",
    "factor_value": "候选因子原始值",
    "carrier_residual": "去除载体输入后的候选残差",
    "strategy_net_log_return": "事件后策略净对数收益",
    "buy_hold_net_log_return": "同期买入持有净对数收益",
    "absolute_strategy_loss": "策略绝对大幅亏损",
    "relative_buy_hold_loss": "策略相对买入持有大幅跑输",
    "relative_frozen_static_loss": "策略相对冻结静态策略大幅跑输",
    "failure_rate_tail": "因子极端尾部失败率",
    "failure_rate_center": "非极端中心失败率",
    "failure_rate_lift": "极端尾部相对中心失败率增量",
    "failure_severity_delta": "极端尾部相对中心失败严重度差",
    "residual_variance_share": "去除载体线性及低阶非线性解释后的残差方差占比",
    "adjusted_failure_p_value": "按预注册假设数量校正后的失败关系显著性",
    "factor_failure_gate": "正交且大幅失败相关前置门",
}


@dataclass(frozen=True, slots=True)
class FailureFactorPolicy:
    """Pre-registered policy for one factor family and one failure target.

    Thresholds are fitted from the *development phase only* and then frozen
    when scoring ``repeat_audit``.  The lower and upper tail are separate
    hypotheses; choosing a direction after reading the audit data is rejected.
    """

    primary_target: FailureTarget
    tail_direction: TailDirection
    registered_at_utc: str
    carrier_manifest_digest: str
    factor_definition_digest: str
    attempt_set_digest: str
    tail_fraction: float = 0.20
    minimum_residual_variance_share: float = 0.20
    minimum_failure_rate_lift: float = 0.05
    minimum_failure_severity_delta: float = 0.005
    maximum_absolute_failure_return: float = -0.01
    maximum_relative_failure_return: float = -0.01
    maximum_frozen_static_failure_return: float = -0.01
    minimum_phase_event_count: int = 20
    minimum_failure_event_count: int = 3
    familywise_alpha: float = 0.10
    registered_hypothesis_count: int = 1
    required_phases: tuple[str, ...] = REQUIRED_PHASES
    numerical_tolerance: float = 1e-12

    def __post_init__(self) -> None:
        if self.primary_target not in {
            "absolute_strategy_loss",
            "relative_buy_hold_loss",
            "relative_frozen_static_loss",
        }:
            raise ValidationError("unsupported failure target")
        if self.tail_direction not in {"lower", "upper"}:
            raise ValidationError("unsupported tail direction")
        registered = pd.to_datetime(self.registered_at_utc, errors="coerce", utc=True)
        if pd.isna(registered):
            raise ValidationError("registered_at_utc must be a parseable timestamp")
        for value, name in (
            (self.carrier_manifest_digest, "carrier manifest"),
            (self.factor_definition_digest, "factor definition"),
            (self.attempt_set_digest, "attempt set"),
        ):
            if len(str(value)) < 8:
                raise ValidationError(f"{name} digest must not be a placeholder")
        if not 0.0 < self.tail_fraction < 0.5:
            raise ValidationError("tail_fraction must lie in (0, 0.5)")
        if not 0.0 < self.minimum_residual_variance_share <= 1.0:
            raise ValidationError("minimum residual variance share must lie in (0, 1]")
        if not 0.0 <= self.minimum_failure_rate_lift <= 1.0:
            raise ValidationError("minimum failure-rate lift must lie in [0, 1]")
        if self.minimum_failure_severity_delta <= 0.0:
            raise ValidationError("minimum failure severity delta must be positive")
        if self.maximum_absolute_failure_return >= 0.0:
            raise ValidationError("absolute failure threshold must be strictly negative")
        if self.maximum_relative_failure_return >= 0.0:
            raise ValidationError("relative failure threshold must be strictly negative")
        if self.maximum_frozen_static_failure_return >= 0.0:
            raise ValidationError("frozen-static failure threshold must be strictly negative")
        if self.minimum_phase_event_count < 10:
            raise ValidationError("minimum phase event count must be at least 10")
        if self.minimum_failure_event_count < 1:
            raise ValidationError("minimum failure event count must be positive")
        if not 0.0 < self.familywise_alpha <= 0.10:
            raise ValidationError("familywise alpha must lie in (0, 0.10]")
        if self.registered_hypothesis_count < 1:
            raise ValidationError("registered hypothesis count must be positive")
        if tuple(self.required_phases) != REQUIRED_PHASES:
            raise ValidationError("development and repeat_audit are both mandatory")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": SCHEMA_ID,
            "policy": {**asdict(self), "required_phases": list(self.required_phases)},
            "threshold_source": "development_phase_only",
            "tail_direction_must_be_predeclared": True,
            "field_labels_zh": {
                "primary_target": "主要失败目标",
                "tail_direction": "预注册因子极端方向",
                "registered_at_utc": "因子假设预注册时间",
                "carrier_manifest_digest": "载体完整输入清单摘要",
                "factor_definition_digest": "候选因子定义摘要",
                "attempt_set_digest": "完整候选尝试集合摘要",
                "tail_fraction": "极端尾部比例",
                "minimum_residual_variance_share": "最小去载体残差信息占比",
                "minimum_failure_rate_lift": "最小尾部失败率增量",
                "minimum_failure_severity_delta": "最小尾部失败严重度增量",
                "maximum_absolute_failure_return": "绝对失败必须低于的负收益边界",
                "maximum_relative_failure_return": "相对失败必须低于的负超额边界",
                "maximum_frozen_static_failure_return": "相对冻结静态失败必须低于的负超额边界",
                "minimum_phase_event_count": "每阶段最小独立事件数",
                "minimum_failure_event_count": "每阶段最小真实失败事件数",
                "familywise_alpha": "假设族整体显著性上限",
                "registered_hypothesis_count": "预注册假设总数",
                "required_phases": "必须同向成立的阶段",
            },
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload


def timing_factor_failure_gate_contract() -> dict[str, object]:
    """Return the factor selection contract used before dynamic research."""

    return {
        "schema_id": SCHEMA_ID,
        "code_version": CODE_VERSION,
        "purpose": "carrier_orthogonal_failure_conditioned_factor_eligibility",
        "required_sequence": [
            "freeze carrier strategy and its already-consumed inputs",
            "fit candidate residualization using development state rows only",
            "freeze failure and factor-tail thresholds from development outcomes only",
            "test absolute buy-hold-relative and frozen-static-relative loss ledgers separately",
            "require same predeclared tail direction across development and repeat audit",
            "only then permit a low-capacity parameter-or-routing hypothesis",
        ],
        "raw_factor_correlation_is_insufficient": True,
        "generic_return_prediction_is_insufficient": True,
        "strictly_negative_failure_boundary_required": True,
        "decision_time_and_point_in_time_fields_required": True,
        "research_clock_rule": (
            "registration is compared with research-package generation time, never with historical market timestamps"
        ),
        "development_and_repeat_audit_are_mandatory": True,
        "nonlinear_carrier_reencoding_rejected": True,
        "registered_hypothesis_multiplicity_control_required": True,
        "retrospective_tail_direction_selection_forbidden": True,
        "full_sample_static_oracle_comparator_forbidden": True,
        "required_failure_views": [
            "absolute_strategy_loss",
            "relative_underperformance_to_buy_and_hold",
            "relative_underperformance_to_frozen_static",
        ],
        "profitable_but_benchmark_lagging_is_failure": True,
        "dynamic_parameter_authority": False,
        "signal_authority": False,
        "routing_authority": False,
        "production_authority": False,
        "field_labels_zh": dict(FIELD_LABELS_ZH),
    }


def validate_factor_failure_panel(
    panel: pd.DataFrame,
    *,
    carrier_columns: tuple[str, ...],
    policy: FailureFactorPolicy | None = None,
) -> None:
    """Validate causal event rows before residualization or outcome scoring."""

    target_columns = (
        {"frozen_static_net_log_return"}
        if policy is not None and policy.primary_target == "relative_frozen_static_loss"
        else set()
    )
    missing = (
        set(BASE_COLUMNS).difference(panel.columns)
        | set(carrier_columns).difference(panel.columns)
        | target_columns.difference(panel.columns)
    )
    if missing:
        raise ValidationError(f"factor failure panel missing columns: {sorted(missing)}")
    if panel.empty:
        raise ValidationError("factor failure panel must not be empty")
    if panel["event_id"].astype(str).duplicated().any():
        raise ValidationError("factor failure panel event_id must be unique")
    if panel[["phase", "independent_event_group_id"]].astype(str).duplicated().any():
        raise ValidationError("independent event groups must be unique inside each phase")
    numeric_columns = ["factor_value", *carrier_columns, "strategy_net_log_return", "buy_hold_net_log_return"]
    if "frozen_static_net_log_return" in panel.columns:
        numeric_columns.append("frozen_static_net_log_return")
    numeric = panel[numeric_columns].apply(
        pd.to_numeric, errors="coerce"
    )
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy(float)).all():
        raise ValidationError("factor panel values must be finite")
    if set(panel["phase"].astype(str)) != set(REQUIRED_PHASES):
        raise ValidationError("factor panel must contain exactly development and repeat_audit")
    if not carrier_columns:
        raise ValidationError("at least one carrier input is required for an orthogonality audit")
    for column in (
        "comparison_id",
        "candidate_id",
        "carrier_manifest_digest",
        "factor_definition_digest",
        "execution_semantics_digest",
        "cost_model_digest",
    ):
        values = panel[column].astype(str)
        if values.str.len().lt(4).any() or values.nunique() != 1:
            raise ValidationError(f"factor panel must bind one non-placeholder {column}")
    ledger_values = panel["opportunity_ledger_digest"].astype(str)
    if ledger_values.str.len().lt(4).any():
        raise ValidationError("opportunity ledger identities must not be placeholders")

    timestamps = {
        column: pd.to_datetime(panel[column], errors="coerce", utc=True)
        for column in (
            "factor_asof_time",
            "decision_time",
            "execution_time",
            "outcome_start_time",
            "outcome_end_exclusive",
        )
    }
    if any(values.isna().any() for values in timestamps.values()):
        raise ValidationError("factor panel causal timestamps must be parseable")
    if not (timestamps["factor_asof_time"] <= timestamps["decision_time"]).all():
        raise ValidationError("factor must be available no later than decision time")
    if not (timestamps["decision_time"] < timestamps["execution_time"]).all():
        raise ValidationError("execution must occur after the decision")
    if not (timestamps["execution_time"] <= timestamps["outcome_start_time"]).all():
        raise ValidationError("outcome cannot start before execution")
    if not (timestamps["outcome_start_time"] < timestamps["outcome_end_exclusive"]).all():
        raise ValidationError("outcome window must have positive duration")
    development = panel["phase"].astype(str).eq("development")
    audit = panel["phase"].astype(str).eq("repeat_audit")
    if timestamps["outcome_end_exclusive"].loc[development].max() > timestamps["factor_asof_time"].loc[audit].min():
        raise ValidationError("repeat audit starts before development outcomes are fully closed")
    if timestamps["outcome_end_exclusive"].loc[audit].max() > pd.Timestamp("2021-01-01", tz="UTC"):
        raise ValidationError("factor gate must not open post-2020 outcomes")
    if policy is not None:
        counts = panel.groupby("phase")["independent_event_group_id"].nunique()
        if (counts < policy.minimum_phase_event_count).any():
            raise ValidationError("factor panel has insufficient independent events in a required phase")
        if not panel["carrier_manifest_digest"].astype(str).eq(policy.carrier_manifest_digest).all():
            raise ValidationError("factor panel carrier manifest differs from the pre-registered policy")
        if not panel["factor_definition_digest"].astype(str).eq(policy.factor_definition_digest).all():
            raise ValidationError("factor panel definition differs from the pre-registered policy")


def _carrier_design(values: np.ndarray) -> np.ndarray:
    """Build a frozen low-capacity basis for obvious nonlinear carrier reuse."""

    columns: list[np.ndarray] = [np.ones(len(values))]
    for index in range(values.shape[1]):
        column = values[:, index]
        columns.extend((column, np.square(column), np.abs(column)))
    for left in range(values.shape[1]):
        for right in range(left + 1, values.shape[1]):
            columns.append(values[:, left] * values[:, right])
    return np.column_stack(columns)


def _fit_development_residual(
    panel: pd.DataFrame,
    *,
    carrier_columns: tuple[str, ...],
) -> tuple[pd.Series, float]:
    """Fit factor~carrier inputs on development only and return all-row residual."""

    development = panel.loc[panel["phase"].astype(str).eq("development")]
    design_width = 1 + 3 * len(carrier_columns) + len(carrier_columns) * (len(carrier_columns) - 1) // 2
    if len(development) <= design_width + 5:
        raise ValidationError("development factor panel has insufficient rows for carrier residualization")
    x_train = _carrier_design(development.loc[:, carrier_columns].to_numpy(float))
    y_train = development["factor_value"].to_numpy(float)
    coefficients, *_ = np.linalg.lstsq(x_train, y_train, rcond=None)
    x_all = _carrier_design(panel.loc[:, carrier_columns].to_numpy(float))
    residual = pd.Series(panel["factor_value"].to_numpy(float) - x_all @ coefficients, index=panel.index)
    raw_variance = float(np.var(y_train))
    residual_variance = float(np.var(residual.loc[development.index].to_numpy(float)))
    if raw_variance <= 0.0:
        raise ValidationError("factor has zero development variance")
    return residual, residual_variance / raw_variance


def _failure_outcome(panel: pd.DataFrame, target: FailureTarget) -> pd.Series:
    if target == "absolute_strategy_loss":
        return cast(pd.Series, panel["strategy_net_log_return"].astype(float))
    if target == "relative_frozen_static_loss":
        if "frozen_static_net_log_return" not in panel.columns:
            raise ValidationError("relative frozen-static failure needs frozen_static_net_log_return")
        return cast(
            pd.Series,
            panel["strategy_net_log_return"].astype(float)
            - panel["frozen_static_net_log_return"].astype(float),
        )
    return cast(
        pd.Series,
        panel["strategy_net_log_return"].astype(float) - panel["buy_hold_net_log_return"].astype(float),
    )


def _tail_mask(values: pd.Series, *, threshold: float, direction: TailDirection) -> pd.Series:
    return values <= threshold if direction == "lower" else values >= threshold


def evaluate_factor_failure_gate(
    panel: pd.DataFrame,
    *,
    factor_id: str,
    carrier_columns: tuple[str, ...],
    policy: FailureFactorPolicy,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Evaluate a predeclared factor tail against causally later failure.

    The returned detail table keeps both failure labels so researchers cannot
    silently relabel a relative failure as an absolute loss, or vice versa.
    ``accepted_for_low_capacity_hypothesis`` remains research-only.
    """

    validate_factor_failure_panel(panel, carrier_columns=carrier_columns, policy=policy)
    residual, residual_variance_share = _fit_development_residual(panel, carrier_columns=carrier_columns)
    working = panel.copy()
    working["carrier_residual"] = residual
    working["absolute_strategy_outcome"] = _failure_outcome(working, "absolute_strategy_loss")
    working["relative_buy_hold_outcome"] = _failure_outcome(working, "relative_buy_hold_loss")
    if "frozen_static_net_log_return" in working.columns:
        working["relative_frozen_static_outcome"] = _failure_outcome(
            working, "relative_frozen_static_loss"
        )
    policy_payload = policy.to_dict()
    if residual_variance_share < policy.minimum_residual_variance_share:
        # A renamed or lightly transformed carrier signal has no independent
        # tail to test.  Return an explicit diagnostic instead of pretending
        # that an arbitrary numerical tie-break among near-zero residuals is
        # evidence of a failure relation.
        details = pd.DataFrame(
            [
                {
                    "factor_id": factor_id,
                    "phase": str(phase),
                    "primary_target": policy.primary_target,
                    "tail_direction": policy.tail_direction,
                    "event_count": int(len(local)),
                    "tail_event_count": 0,
                    "center_event_count": 0,
                    "residual_variance_share": residual_variance_share,
                    "thresholds_fit_on_development_only": True,
                    "factor_failure_evaluation_status": "not_evaluated_carrier_information_reused",
                    "weighted_score_used": False,
                }
                for phase, local in working.groupby("phase", sort=True)
            ]
        )
        early_result: dict[str, object] = {
            "schema_id": SCHEMA_ID,
            "code_version": CODE_VERSION,
            "factor_id": factor_id,
            "comparison_id": str(working["comparison_id"].iloc[0]),
            "candidate_id": str(working["candidate_id"].iloc[0]),
            "carrier_columns": list(carrier_columns),
            "carrier_manifest_digest": str(working["carrier_manifest_digest"].iloc[0]),
            "factor_definition_digest": str(working["factor_definition_digest"].iloc[0]),
            "primary_target": policy.primary_target,
            "tail_direction": policy.tail_direction,
            "residual_variance_share": residual_variance_share,
            "orthogonality_gate_passed": False,
            "failure_extreme_gate_passed": False,
            "verdict": "rejected_carrier_information_reused",
            "accepted_for_low_capacity_hypothesis": False,
            "policy_digest": policy_payload["semantic_digest"],
            "thresholds_fit_on_development_only": True,
            "causal_clock_validated": True,
            "required_phases_enforced": list(REQUIRED_PHASES),
            "dynamic_parameter_authority": False,
            "signal_authority": False,
            "routing_authority": False,
            "production_authority": False,
            "field_labels_zh": dict(FIELD_LABELS_ZH),
        }
        early_result["semantic_digest"] = canonical_digest(early_result)
        return details, early_result
    development = working.loc[working["phase"].astype(str).eq("development")]
    target_column = {
        "absolute_strategy_loss": "absolute_strategy_outcome",
        "relative_buy_hold_loss": "relative_buy_hold_outcome",
        "relative_frozen_static_loss": "relative_frozen_static_outcome",
    }[policy.primary_target]
    quantile_threshold = float(development[target_column].quantile(policy.tail_fraction))
    semantic_failure_ceiling = {
        "absolute_strategy_loss": policy.maximum_absolute_failure_return,
        "relative_buy_hold_loss": policy.maximum_relative_failure_return,
        "relative_frozen_static_loss": policy.maximum_frozen_static_failure_return,
    }[policy.primary_target]
    failure_threshold = min(quantile_threshold, semantic_failure_ceiling)
    factor_quantile = policy.tail_fraction if policy.tail_direction == "lower" else 1.0 - policy.tail_fraction
    residual_threshold = float(development["carrier_residual"].quantile(factor_quantile))

    rows: list[dict[str, object]] = []
    for phase, local in working.groupby("phase", sort=True):
        tail = _tail_mask(local["carrier_residual"], threshold=residual_threshold, direction=policy.tail_direction)
        if tail.all() or (~tail).all():
            raise ValidationError(f"factor tail has no contrast in phase={phase}")
        target = local[target_column]
        failure = target <= failure_threshold
        failure_count = int(failure.sum())
        tail_rate = float(failure.loc[tail].mean())
        center_rate = float(failure.loc[~tail].mean())
        tail_mean = float(target.loc[tail].mean())
        center_mean = float(target.loc[~tail].mean())
        tail_failures = int(failure.loc[tail].sum())
        center_failures = int(failure.loc[~tail].sum())
        _, p_value = fisher_exact(
            [
                [tail_failures, int(tail.sum()) - tail_failures],
                [center_failures, int((~tail).sum()) - center_failures],
            ],
            alternative="greater",
        )
        adjusted_p_value = min(1.0, float(p_value) * policy.registered_hypothesis_count)
        rows.append(
            {
                "factor_id": factor_id,
                "phase": str(phase),
                "primary_target": policy.primary_target,
                "tail_direction": policy.tail_direction,
                "event_count": int(len(local)),
                "tail_event_count": int(tail.sum()),
                "center_event_count": int((~tail).sum()),
                "failure_event_count": failure_count,
                "development_failure_threshold": failure_threshold,
                "development_residual_tail_threshold": residual_threshold,
                "failure_rate_tail": tail_rate,
                "failure_rate_center": center_rate,
                "failure_rate_lift": tail_rate - center_rate,
                "failure_severity_tail_mean": tail_mean,
                "failure_severity_center_mean": center_mean,
                "failure_severity_delta": center_mean - tail_mean,
                "fisher_exact_p_value": float(p_value),
                "adjusted_failure_p_value": adjusted_p_value,
                "residual_variance_share": residual_variance_share,
                "thresholds_fit_on_development_only": True,
                "weighted_score_used": False,
            }
        )
    details = pd.DataFrame(rows)
    required_rows = details.loc[details["phase"].astype(str).isin(REQUIRED_PHASES)]
    has_required = set(required_rows["phase"].astype(str)) == set(REQUIRED_PHASES)
    orthogonal = residual_variance_share >= policy.minimum_residual_variance_share
    failure_stable = bool(
        has_required
        and (required_rows["failure_event_count"] >= policy.minimum_failure_event_count).all()
        and (required_rows["failure_rate_lift"] >= policy.minimum_failure_rate_lift - policy.numerical_tolerance).all()
        and (required_rows["failure_severity_delta"] >= policy.minimum_failure_severity_delta - policy.numerical_tolerance).all()
        and (required_rows["adjusted_failure_p_value"] <= policy.familywise_alpha + policy.numerical_tolerance).all()
    )
    if not orthogonal:
        verdict = "rejected_carrier_information_reused"
    elif not failure_stable:
        verdict = "rejected_no_stable_extreme_failure_relation"
    else:
        verdict = "eligible_for_low_capacity_failure_hypothesis"
    result: dict[str, object] = {
        "schema_id": SCHEMA_ID,
        "code_version": CODE_VERSION,
        "factor_id": factor_id,
        "comparison_id": str(working["comparison_id"].iloc[0]),
        "candidate_id": str(working["candidate_id"].iloc[0]),
        "carrier_columns": list(carrier_columns),
        "carrier_manifest_digest": str(working["carrier_manifest_digest"].iloc[0]),
        "factor_definition_digest": str(working["factor_definition_digest"].iloc[0]),
        "primary_target": policy.primary_target,
        "tail_direction": policy.tail_direction,
        "residual_variance_share": residual_variance_share,
        "orthogonality_gate_passed": orthogonal,
        "failure_extreme_gate_passed": failure_stable,
        "verdict": verdict,
        "accepted_for_low_capacity_hypothesis": verdict == "eligible_for_low_capacity_failure_hypothesis",
        "policy_digest": policy_payload["semantic_digest"],
        "thresholds_fit_on_development_only": True,
        "causal_clock_validated": True,
        "required_phases_enforced": list(REQUIRED_PHASES),
        "dynamic_parameter_authority": False,
        "signal_authority": False,
        "routing_authority": False,
        "production_authority": False,
        "field_labels_zh": dict(FIELD_LABELS_ZH),
    }
    result["semantic_digest"] = canonical_digest(result)
    return details, result


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    _ = path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _validate_research_registration_clock(*, registered_at_utc: str, generated_at_utc: str) -> None:
    """Validate the research wall clock without confusing it with market time."""

    registered = pd.to_datetime(registered_at_utc, errors="coerce", utc=True)
    generated = pd.to_datetime(generated_at_utc, errors="coerce", utc=True)
    if pd.isna(registered) or pd.isna(generated) or registered >= generated:
        raise ValidationError("factor policy receipt must predate evaluation package generation")


def run_factor_failure_gate_package(
    *,
    output_dir: Path,
    panel: pd.DataFrame,
    factor_id: str,
    carrier_columns: tuple[str, ...],
    policy: FailureFactorPolicy,
) -> dict[str, object]:
    """Persist a factor gate result with its input, thresholds and hashes."""

    generated_at_utc = datetime.now(UTC).isoformat()
    _validate_research_registration_clock(
        registered_at_utc=policy.registered_at_utc,
        generated_at_utc=generated_at_utc,
    )
    details, result = evaluate_factor_failure_gate(
        panel,
        factor_id=factor_id,
        carrier_columns=carrier_columns,
        policy=policy,
    )
    parent = output_dir.parent
    _ = parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=parent))
    try:
        panel.to_csv(temporary / "event_panel.csv", index=False, float_format="%.17g")
        details.to_csv(temporary / "failure_tail_detail.csv", index=False, float_format="%.17g")
        _write_json(temporary / "policy.json", policy.to_dict())
        _write_json(temporary / "result.json", result)
        report = "\n".join(
            [
                "# 择时因子正交—大幅失败前置门报告",
                "",
                f"- 因子：`{factor_id}`。",
                f"- 载体已使用输入：`{', '.join(carrier_columns)}`。",
                f"- 结论：`{result['verdict']}`。",
                "- 本结果仅决定能否形成低容量研究假设；不授予任何参数、路由或交易权限。",
                "- 极端方向、失败阈值均以开发期冻结后才评估重复审计期。",
            ]
        ) + "\n"
        _ = (temporary / "report_zh.md").write_text(report, encoding="utf-8")
        artifacts = ["event_panel.csv", "failure_tail_detail.csv", "policy.json", "result.json", "report_zh.md"]
        manifest: dict[str, object] = {
            "schema_id": SCHEMA_ID,
            "code_version": CODE_VERSION,
            "canonical_entrypoint": CANONICAL_ENTRYPOINT,
            "generated_at_utc": generated_at_utc,
            "factor_id": factor_id,
            "comparison_id": result["comparison_id"],
            "candidate_id": result["candidate_id"],
            "carrier_columns": list(carrier_columns),
            "carrier_manifest_digest": result["carrier_manifest_digest"],
            "factor_definition_digest": result["factor_definition_digest"],
            "policy_digest": policy.to_dict()["semantic_digest"],
            "result_digest": result["semantic_digest"],
            "authority": {
                "evaluation_authority": True,
                "signal_authority": False,
                "routing_authority": False,
                "dynamic_parameter_authority": False,
                "production_authority": False,
            },
            "artifacts": [
                {"path": name, "sha256": _sha256_file(temporary / name), "size_bytes": (temporary / name).stat().st_size}
                for name in artifacts
            ],
            "field_labels_zh": dict(FIELD_LABELS_ZH),
        }
        manifest["semantic_digest"] = canonical_digest(manifest)
        _write_json(temporary / "manifest.json", manifest)
        if output_dir.exists():
            _ = shutil.rmtree(output_dir)
        _ = temporary.replace(output_dir)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    validate_persisted_factor_failure_gate_package(output_dir)
    return json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))


def validate_persisted_factor_failure_gate_package(output_dir: Path) -> None:
    """Recompute the persisted gate so hashes cannot bless false semantics."""

    manifest_path = output_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ValidationError("factor failure gate manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_id") != SCHEMA_ID:
        raise ValidationError("factor failure gate manifest schema changed")
    authority = manifest.get("authority", {})
    if not isinstance(authority, dict):
        raise ValidationError("factor failure gate authority is malformed")
    for key in ("signal_authority", "routing_authority", "dynamic_parameter_authority", "production_authority"):
        if authority.get(key) is not False:
            raise ValidationError(f"factor failure gate cannot grant {key}")
    expected_artifacts = {
        "event_panel.csv",
        "failure_tail_detail.csv",
        "policy.json",
        "result.json",
        "report_zh.md",
    }
    artifact_rows = manifest.get("artifacts", [])
    if not isinstance(artifact_rows, list) or {
        str(item.get("path")) for item in artifact_rows if isinstance(item, Mapping)
    } != expected_artifacts:
        raise ValidationError("factor failure gate artifact set is incomplete")
    for item in artifact_rows:
        if not isinstance(item, dict):
            raise ValidationError("factor failure gate artifact entry is malformed")
        path = output_dir / str(item["path"])
        if not path.is_file() or _sha256_file(path) != str(item["sha256"]):
            raise ValidationError(f"factor failure gate artifact hash mismatch: {item['path']}")
    unsigned = dict(manifest)
    stored = unsigned.pop("semantic_digest", None)
    if stored != canonical_digest(unsigned):
        raise ValidationError("factor failure gate manifest semantic digest mismatch")
    result = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
    if result.get("semantic_digest") != manifest.get("result_digest"):
        raise ValidationError("factor failure gate result digest drifted")
    unsigned_result = dict(result)
    stored_result_digest = unsigned_result.pop("semantic_digest", None)
    if stored_result_digest != canonical_digest(unsigned_result):
        raise ValidationError("factor failure gate result semantic digest mismatch")
    policy_payload = json.loads((output_dir / "policy.json").read_text(encoding="utf-8"))
    if policy_payload.get("semantic_digest") != manifest.get("policy_digest"):
        raise ValidationError("factor failure gate policy digest drifted")
    raw_policy = policy_payload.get("policy")
    if not isinstance(raw_policy, Mapping):
        raise ValidationError("factor failure gate policy is malformed")
    policy_values = dict(raw_policy)
    policy_values["required_phases"] = tuple(policy_values.get("required_phases", ()))
    policy = FailureFactorPolicy(**policy_values)
    _validate_research_registration_clock(
        registered_at_utc=policy.registered_at_utc,
        generated_at_utc=str(manifest.get("generated_at_utc", "")),
    )
    panel = pd.read_csv(output_dir / "event_panel.csv")
    recomputed_details, recomputed_result = evaluate_factor_failure_gate(
        panel,
        factor_id=str(manifest.get("factor_id")),
        carrier_columns=tuple(str(value) for value in manifest.get("carrier_columns", [])),
        policy=policy,
    )
    stored_details = pd.read_csv(output_dir / "failure_tail_detail.csv")
    try:
        pd.testing.assert_frame_equal(
            stored_details.reset_index(drop=True),
            recomputed_details.reset_index(drop=True),
            check_dtype=False,
            check_exact=False,
            rtol=1e-9,
            atol=1e-11,
        )
    except AssertionError as exc:
        raise ValidationError("factor failure gate detail does not replay") from exc
    stored_replay = {key: value for key, value in result.items() if key != "semantic_digest"}
    recomputed_replay = {
        key: value for key, value in recomputed_result.items() if key != "semantic_digest"
    }
    if set(stored_replay) != set(recomputed_replay):
        raise ValidationError("factor failure gate result fields do not replay")
    for key, stored_value in stored_replay.items():
        recomputed_value = recomputed_replay[key]
        if isinstance(stored_value, bool) or isinstance(recomputed_value, bool):
            values_match = stored_value == recomputed_value
        elif isinstance(stored_value, (int, float)) and isinstance(
            recomputed_value, (int, float)
        ):
            values_match = bool(
                np.isclose(stored_value, recomputed_value, rtol=1e-12, atol=1e-14)
            )
        else:
            values_match = stored_value == recomputed_value
        if not values_match:
            raise ValidationError(f"factor failure gate result does not replay: {key}")


__all__ = [
    "CANONICAL_ENTRYPOINT",
    "CODE_VERSION",
    "DEFAULT_OUTPUT_DIR",
    "FailureFactorPolicy",
    "FIELD_LABELS_ZH",
    "SCHEMA_ID",
    "evaluate_factor_failure_gate",
    "run_factor_failure_gate_package",
    "timing_factor_failure_gate_contract",
    "validate_factor_failure_panel",
    "validate_persisted_factor_failure_gate_package",
]
