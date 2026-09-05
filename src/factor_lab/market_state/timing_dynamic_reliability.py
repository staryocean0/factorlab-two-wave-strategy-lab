# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportCallIssue=false, reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Stability-first evaluation for causal dynamic timing parameters.

This module deliberately does *not* compare a dynamic policy with the best
static parameter selected after observing the same full history.  That would
turn an oracle into an unfair baseline.  Instead it compares a pre-development
frozen static policy and a pre-declared causal dynamic policy on identical,
small evaluation blocks.

The output is a Pareto ledger, not a fitted weighted score.  A dynamic policy
may trade some headline return for materially fewer bad blocks, but it may not
claim success merely by staying flat: an explicit, pre-registered long-run
viability floor remains mandatory.
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

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest

SCHEMA_ID: Final[str] = "market_state_timing_dynamic_reliability@1.0"
CODE_VERSION: Final[str] = "timing-dynamic-reliability-20260810-r4"
DEFAULT_OUTPUT_DIR: Final[Path] = Path("artifacts/market_state/timing_dynamic_reliability_v1")
CANONICAL_ENTRYPOINT: Final[str] = "docs/user/market_state_dynamic_parameter_reliability_workflow.md"

ParameterMode = Literal["static", "causal_dynamic", "six_axis_dynamic"]
PolicyScope = Literal["frozen_predevelopment", "predeclared_causal"]
ComparisonScope = Literal["complete_policy", "local_ablation"]
OpportunityDisposition = Literal[
    "captured_by_selected_parameter",
    "routed_to_parallel_tool",
    "cash_with_registered_risk_case",
    "unaccounted",
]
DYNAMIC_PARAMETER_MODES: Final[frozenset[str]] = frozenset(
    {"causal_dynamic", "six_axis_dynamic"}
)

IDENTITY_COLUMNS: Final[tuple[str, ...]] = (
    "comparison_id",
    "candidate_id",
    "parameter_mode",
    "period",
    "period_role",
    "opportunity_side",
    "state_cell_id",
    "evaluation_block_id",
    "block_start",
    "block_end_exclusive",
    "policy_scope",
    "parameter_policy_digest",
    "evaluation_plan_digest",
    "opportunity_ledger_digest",
    "execution_semantics_digest",
    "cost_model_digest",
    "comparison_scope",
    "strategy_completeness_digest",
    "reference_set_digest",
    "full_path_repriced",
)
RETURN_COLUMNS: Final[tuple[str, ...]] = (
    "strategy_net_log_return",
    "buy_hold_net_log_return",
)
ACTIVITY_COLUMNS: Final[tuple[str, ...]] = (
    "active_exposure_fraction",
    "opportunity_coverage_fraction",
)
PAIR_COLUMNS: Final[tuple[str, ...]] = (
    "comparison_id",
    "period",
    "period_role",
    "opportunity_side",
    "state_cell_id",
    "evaluation_block_id",
)
SUMMARY_GROUP_COLUMNS: Final[tuple[str, ...]] = (
    "comparison_id",
    "period",
    "period_role",
    "opportunity_side",
    "state_cell_id",
)

FIELD_LABELS_ZH: Final[dict[str, str]] = {
    "comparison_id": "静态—动态公平对照身份",
    "candidate_id": "候选策略身份",
    "parameter_mode": "参数模式",
    "period": "评价区间",
    "period_role": "区间角色",
    "evaluation_block_id": "细粒度评价块身份",
    "block_start": "评价块起点",
    "block_end_exclusive": "评价块终点（不含）",
    "policy_scope": "参数策略形成范围",
    "strategy_net_log_return": "策略块净对数收益",
    "buy_hold_net_log_return": "同期买入持有净对数收益",
    "excess_to_buy_hold": "策略相对买入持有净对数收益",
    "excess_to_frozen_static": "动态策略相对冻结静态策略净对数收益",
    "negative_return_block_rate": "绝对亏损块占比",
    "relative_failure_block_rate": "跑输买入持有块占比",
    "relative_static_failure_block_rate": "跑输冻结静态策略块占比",
    "worst_block_net_log_return": "最差单块策略净对数收益",
    "worst_block_excess_to_buy_hold": "最差单块相对持有收益",
    "worst_block_excess_to_frozen_static": "最差单块相对冻结静态收益",
    "tail_mean_net_log_return": "最差尾部块平均策略收益",
    "tail_mean_excess_to_buy_hold": "最差尾部块平均相对持有收益",
    "tail_mean_excess_to_frozen_static": "最差尾部块平均相对冻结静态收益",
    "block_excess_iqr": "块级相对持有收益四分位距",
    "total_strategy_net_log_return": "全区间策略净对数收益",
    "total_excess_to_buy_hold": "全区间相对持有净对数收益",
    "annualized_strategy_net_log_return": "按评价块实际时长年化的策略净对数收益",
    "annualized_excess_to_buy_hold": "按评价块实际时长年化的相对持有净对数收益",
    "annualized_excess_to_frozen_static": "按评价块实际时长年化的相对冻结静态净对数收益",
    "active_exposure_fraction": "策略实际参与时间占比",
    "opportunity_coverage_fraction": "策略覆盖已登记机会的比例",
    "reliability_verdict": "稳定性优先裁决",
    "viability_verdict": "长期可生存性裁决",
}


@dataclass(frozen=True, slots=True)
class StrategyCompletenessEvidence:
    """Pre-registered proof that a candidate is a whole tradable policy.

    A local parameter ablation may be useful diagnostically, but it is not a
    fair opponent for buy-and-hold or another full strategy when it knowingly
    abandons the opportunity that triggered the parameter change.  A complete
    policy therefore names one owner and one opportunity disposition for every
    declared decision state, reprices the resulting continuous path, and binds
    all comparison references before outcomes are read.
    """

    comparison_id: str
    comparison_scope: ComparisonScope
    registered_at_utc: str
    decision_state_owner: Mapping[str, str]
    opportunity_disposition_by_state: Mapping[str, OpportunityDisposition]
    reference_candidate_ids: tuple[str, ...]
    full_path_repriced: bool
    mutually_exclusive_state_ownership: bool
    execution_semantics_digest: str
    cost_model_digest: str

    def __post_init__(self) -> None:
        if self.comparison_scope not in {"complete_policy", "local_ablation"}:
            raise ValidationError("unsupported strategy comparison scope")
        registered = pd.to_datetime(self.registered_at_utc, errors="coerce", utc=True)
        if pd.isna(registered):
            raise ValidationError("strategy completeness registration must be parseable")
        if len(self.comparison_id) < 4:
            raise ValidationError("strategy completeness comparison_id must not be a placeholder")
        for value, name in (
            (self.execution_semantics_digest, "execution semantics"),
            (self.cost_model_digest, "cost model"),
        ):
            if len(str(value)) < 4:
                raise ValidationError(f"strategy completeness {name} digest must not be a placeholder")
        owners = {str(key): str(value) for key, value in self.decision_state_owner.items()}
        dispositions = {
            str(key): str(value) for key, value in self.opportunity_disposition_by_state.items()
        }
        if not owners or set(owners) != set(dispositions):
            raise ValidationError("every declared decision state needs both an owner and an opportunity disposition")
        allowed_dispositions = {
            "captured_by_selected_parameter",
            "routed_to_parallel_tool",
            "cash_with_registered_risk_case",
            "unaccounted",
        }
        if not set(dispositions.values()).issubset(allowed_dispositions):
            raise ValidationError("strategy completeness contains an unsupported opportunity disposition")
        references = {str(value) for value in self.reference_candidate_ids}
        if self.comparison_scope == "complete_policy":
            if any(not owner or owner == "unassigned" for owner in owners.values()):
                raise ValidationError("complete policy cannot leave a decision state unassigned")
            if "unaccounted" in dispositions.values():
                raise ValidationError("complete policy cannot discard a triggered opportunity without ownership")
            if not self.full_path_repriced:
                raise ValidationError("complete policy must reprice its actual continuous path")
            if not self.mutually_exclusive_state_ownership:
                raise ValidationError("complete policy needs one mutually exclusive owner per decision state")
            if not {"buy_and_hold", "frozen_static"}.issubset(references):
                raise ValidationError("complete policy must compare with buy_and_hold and frozen_static")

    @property
    def reference_set_digest(self) -> str:
        return canonical_digest({"reference_candidate_ids": sorted(map(str, self.reference_candidate_ids))})

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": SCHEMA_ID,
            "evidence_type": "strategy_completeness",
            "evidence": asdict(self),
            "reference_set_digest": self.reference_set_digest,
            "authority_eligible": self.comparison_scope == "complete_policy",
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload


@dataclass(frozen=True, slots=True)
class DynamicReliabilityPolicy:
    """Pre-registered, non-fitted floors for a stability comparison.

    Floors are intentionally supplied by the caller.  They cannot be selected
    after seeing the dynamic candidate.  ``tail_fraction`` defines a reporting
    tail, not a return threshold or a fitted winner score.
    """

    minimum_annualized_strategy_net_log_return: float
    minimum_annualized_excess_to_buy_hold: float
    minimum_annualized_excess_to_frozen_static: float
    registered_at_utc: str
    evaluation_plan_digest: str
    static_policy_digest: str
    dynamic_policy_digest: str
    comparison_scope: ComparisonScope
    strategy_completeness_digest: str
    reference_set_digest: str
    minimum_active_exposure_fraction: float = 0.05
    minimum_opportunity_coverage_fraction: float = 0.05
    tail_fraction: float = 0.10
    numerical_tolerance: float = 1e-12

    def __post_init__(self) -> None:
        if self.comparison_scope not in {"complete_policy", "local_ablation"}:
            raise ValidationError("unsupported reliability comparison scope")
        if not 0.0 < self.tail_fraction <= 0.5:
            raise ValidationError("tail_fraction must lie in (0, 0.5]")
        if not 0.0 < self.numerical_tolerance < 1e-4:
            raise ValidationError("numerical_tolerance must lie in (0, 1e-4)")
        values = (
            self.minimum_annualized_strategy_net_log_return,
            self.minimum_annualized_excess_to_buy_hold,
            self.minimum_annualized_excess_to_frozen_static,
        )
        if not all(np.isfinite(values)):
            raise ValidationError("reliability viability floors must be finite")
        if self.minimum_annualized_strategy_net_log_return <= 0.0:
            raise ValidationError("strategy viability floor must be strictly positive")
        for value, name in (
            (self.minimum_active_exposure_fraction, "active exposure"),
            (self.minimum_opportunity_coverage_fraction, "opportunity coverage"),
        ):
            if not 0.0 < value <= 1.0:
                raise ValidationError(f"minimum {name} fraction must lie in (0, 1]")
        registered = pd.to_datetime(self.registered_at_utc, errors="coerce", utc=True)
        if pd.isna(registered):
            raise ValidationError("registered_at_utc must be a parseable timestamp")
        for value, name in (
            (self.evaluation_plan_digest, "evaluation plan"),
            (self.static_policy_digest, "static policy"),
            (self.dynamic_policy_digest, "dynamic policy"),
            (self.strategy_completeness_digest, "strategy completeness"),
            (self.reference_set_digest, "reference set"),
        ):
            if len(str(value)) < 8:
                raise ValidationError(f"{name} digest must not be a placeholder")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": SCHEMA_ID,
            "policy": asdict(self),
            "policy_selection": "pre_registered_not_fitted_from_candidate_outcomes",
            "field_labels_zh": {
                "minimum_annualized_strategy_net_log_return": "策略年化净收益最低线",
                "minimum_annualized_excess_to_buy_hold": "相对买入持有年化收益最低线",
                "minimum_annualized_excess_to_frozen_static": "相对冻结静态策略年化收益最低线",
                "minimum_active_exposure_fraction": "最小实际参与比例",
                "minimum_opportunity_coverage_fraction": "最小机会覆盖比例",
                "registered_at_utc": "政策预注册时间",
                "evaluation_plan_digest": "预注册评价块方案摘要",
                "comparison_scope": "完整策略或局部消融的比较范围",
                "strategy_completeness_digest": "策略状态所有权与机会处置证据摘要",
                "reference_set_digest": "预注册比较基线集合摘要",
                "tail_fraction": "最差尾部块比例",
                "numerical_tolerance": "数值比较容差",
            },
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload


def timing_dynamic_reliability_contract() -> dict[str, object]:
    """Return the public stability-first contract for dynamic parameters."""

    return {
        "schema_id": SCHEMA_ID,
        "code_version": CODE_VERSION,
        "purpose": "stability_first_dynamic_parameter_evaluation",
        "static_baseline_rule": (
            "static policy must be frozen before the development period; full-sample retrospective best static is prohibited"
        ),
        "dynamic_policy_rule": "dynamic policy must be predeclared and causal before its evaluated block",
        "research_clock_rule": (
            "registration is compared with research-package generation time, never with historical market timestamps"
        ),
        "comparison_unit": "identical fine-grained time block rather than only phase aggregate",
        "required_period_roles": ["development", "repeat_audit"],
        "aggregate_blackbox_detail_forbidden": True,
        "pre_registered_nonoverlapping_complete_block_plan_required": True,
        "required_failure_views": [
            "absolute_strategy_loss",
            "relative_underperformance_to_buy_and_hold",
            "relative_underperformance_to_frozen_static",
        ],
        "complete_policy_comparison_required_for_authority": True,
        "local_ablation_cannot_grant_dynamic_authority": True,
        "unaccounted_triggered_opportunity_forbidden": True,
        "full_path_repricing_required": True,
        "required_complete_policy_references": ["buy_and_hold", "frozen_static"],
        "stability_metrics": [
            "negative_return_block_rate",
            "relative_failure_block_rate",
            "relative_static_failure_block_rate",
            "worst_block_net_log_return",
            "worst_block_excess_to_buy_hold",
            "worst_block_excess_to_frozen_static",
            "tail_mean_net_log_return",
            "tail_mean_excess_to_buy_hold",
            "tail_mean_excess_to_frozen_static",
            "block_excess_iqr",
        ],
        "selection_order": [
            "reject retrospective static oracle",
            "reject local ablation as a whole-strategy conclusion",
            "require one owner and one opportunity disposition for every declared state",
            "require identical ledger execution cost and blocks",
            "compare stability metrics by Pareto relation",
            "apply pre-registered long-run viability floor",
            "reject zero-participation or negligible-opportunity-coverage pseudo stability",
            "require the same candidate to pass development and repeat audit",
            "among viable stability winners, prefer greater long-run return",
        ],
        "weighted_score_forbidden": True,
        "per_block_buy_hold_outperformance_required": False,
        "dynamic_parameter_authority": False,
        "signal_authority": False,
        "routing_authority": False,
        "production_authority": False,
        "field_labels_zh": dict(FIELD_LABELS_ZH),
    }


def _parse_timestamp_column(frame: pd.DataFrame, column: str) -> pd.Series:
    parsed = pd.to_datetime(frame[column], errors="coerce", utc=False)
    if parsed.isna().any():
        raise ValidationError(f"{column} must contain parseable timestamps")
    return parsed


def validate_dynamic_reliability_scorecard(
    scorecard: pd.DataFrame,
    *,
    policy: DynamicReliabilityPolicy | None = None,
) -> None:
    """Fail closed unless static and dynamic policies took the same block exam."""

    missing = (
        set(IDENTITY_COLUMNS).difference(scorecard.columns)
        | set(RETURN_COLUMNS).difference(scorecard.columns)
        | set(ACTIVITY_COLUMNS).difference(scorecard.columns)
    )
    if missing:
        raise ValidationError(f"dynamic reliability scorecard missing columns: {sorted(missing)}")
    if scorecard.empty:
        raise ValidationError("dynamic reliability scorecard must not be empty")
    if not set(scorecard["parameter_mode"].astype(str)).issubset(
        {"static", *DYNAMIC_PARAMETER_MODES}
    ):
        raise ValidationError("parameter_mode must be static or a registered causal dynamic mode")
    if set(scorecard["period_role"].astype(str)) != {"development", "repeat_audit"}:
        raise ValidationError("detailed reliability needs exactly development and repeat_audit; blackbox detail is forbidden")
    block_start = pd.to_datetime(scorecard["block_start"], errors="coerce", utc=True)
    block_end = pd.to_datetime(scorecard["block_end_exclusive"], errors="coerce", utc=True)
    if block_start.isna().any() or block_end.isna().any():
        raise ValidationError("block timestamps must be parseable")
    if not (block_start < block_end).all():
        raise ValidationError("every evaluation block must have a positive time span")
    numeric = scorecard[[*RETURN_COLUMNS, *ACTIVITY_COLUMNS]].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy(float)).all():
        raise ValidationError("return and activity columns must be finite")
    if not numeric[list(ACTIVITY_COLUMNS)].apply(lambda values: values.between(0.0, 1.0)).all().all():
        raise ValidationError("activity and opportunity coverage must lie in [0, 1]")
    if not set(scorecard["comparison_scope"].astype(str)).issubset(
        {"complete_policy", "local_ablation"}
    ):
        raise ValidationError("comparison_scope must be complete_policy or local_ablation")
    repriced = scorecard["full_path_repriced"]
    if not repriced.map(lambda value: isinstance(value, (bool, np.bool_))).all():
        raise ValidationError("full_path_repriced must contain strict booleans")

    development = scorecard["period_role"].astype(str).eq("development")
    audit = scorecard["period_role"].astype(str).eq("repeat_audit")
    cutoff_2018 = pd.Timestamp("2018-01-01", tz="UTC")
    cutoff_2021 = pd.Timestamp("2021-01-01", tz="UTC")
    if block_end.loc[development].max() > cutoff_2018:
        raise ValidationError("development reliability blocks must end before 2018")
    if block_start.loc[audit].min() < cutoff_2018 or block_end.loc[audit].max() > cutoff_2021:
        raise ValidationError("repeat audit reliability blocks must remain inside 2018-2020")
    if block_end.loc[development].max() > block_start.loc[audit].min():
        raise ValidationError("repeat audit overlaps development")

    for keys, local in scorecard.groupby(list(PAIR_COLUMNS), sort=False):
        modes = local["parameter_mode"].astype(str).value_counts().to_dict()
        dynamic_modes = [mode for mode in modes if mode in DYNAMIC_PARAMETER_MODES]
        if modes.get("static") != 1 or len(dynamic_modes) != 1 or modes[dynamic_modes[0]] != 1:
            raise ValidationError(f"each block requires one static and one dynamic result: {keys}")
        static = local.loc[local["parameter_mode"].astype(str).eq("static")].iloc[0]
        dynamic = local.loc[local["parameter_mode"].astype(str).eq(dynamic_modes[0])].iloc[0]
        if str(static["policy_scope"]) != "frozen_predevelopment":
            raise ValidationError("static baseline must use policy_scope=frozen_predevelopment")
        if str(dynamic["policy_scope"]) != "predeclared_causal":
            raise ValidationError("dynamic policy must use policy_scope=predeclared_causal")
        for column in (
            "buy_hold_net_log_return",
            "evaluation_plan_digest",
            "opportunity_ledger_digest",
            "execution_semantics_digest",
            "cost_model_digest",
            "block_start",
            "block_end_exclusive",
            "comparison_scope",
            "strategy_completeness_digest",
            "reference_set_digest",
            "full_path_repriced",
        ):
            if local[column].astype(str).nunique() != 1:
                raise ValidationError(f"unfair dynamic reliability comparison: {column} differs inside {keys}")

    for keys, local in scorecard.groupby(list(SUMMARY_GROUP_COLUMNS), sort=False):
        blocks = (
            local[["evaluation_block_id", "block_start", "block_end_exclusive"]]
            .drop_duplicates()
            .assign(
                _start=lambda frame: pd.to_datetime(frame["block_start"], utc=True),
                _end=lambda frame: pd.to_datetime(frame["block_end_exclusive"], utc=True),
            )
            .sort_values("_start")
        )
        if blocks["evaluation_block_id"].astype(str).duplicated().any():
            raise ValidationError(f"evaluation block identity is reused with different boundaries: {keys}")
        starts = blocks["_start"].reset_index(drop=True)
        ends = blocks["_end"].reset_index(drop=True)
        if len(blocks) > 1 and not starts.iloc[1:].reset_index(drop=True).eq(ends.iloc[:-1].reset_index(drop=True)).all():
            raise ValidationError(f"evaluation blocks must be contiguous and non-overlapping: {keys}")

    for keys, local in scorecard.groupby(["comparison_id", "candidate_id", "parameter_mode"], sort=False):
        if local["parameter_policy_digest"].astype(str).nunique() != 1:
            raise ValidationError(f"parameter policy digest changed across blocks: {keys}")
        if local["evaluation_plan_digest"].astype(str).nunique() != 1:
            raise ValidationError(f"evaluation plan digest changed across blocks: {keys}")

    if policy is not None:
        if not scorecard["evaluation_plan_digest"].astype(str).eq(policy.evaluation_plan_digest).all():
            raise ValidationError("scorecard does not match the pre-registered evaluation plan")
        static_rows = scorecard.loc[scorecard["parameter_mode"].astype(str).eq("static")]
        dynamic_rows = scorecard.loc[
            scorecard["parameter_mode"].astype(str).isin(DYNAMIC_PARAMETER_MODES)
        ]
        if not static_rows["parameter_policy_digest"].astype(str).eq(policy.static_policy_digest).all():
            raise ValidationError("static rows do not match the registered policy digest")
        if not dynamic_rows["parameter_policy_digest"].astype(str).eq(policy.dynamic_policy_digest).all():
            raise ValidationError("dynamic rows do not match the registered policy digest")
        if not scorecard["comparison_scope"].astype(str).eq(policy.comparison_scope).all():
            raise ValidationError("scorecard comparison scope differs from the registered policy")
        if not scorecard["strategy_completeness_digest"].astype(str).eq(
            policy.strategy_completeness_digest
        ).all():
            raise ValidationError("scorecard strategy completeness evidence differs from policy")
        if not scorecard["reference_set_digest"].astype(str).eq(policy.reference_set_digest).all():
            raise ValidationError("scorecard reference set differs from policy")
        if policy.comparison_scope == "complete_policy" and not scorecard[
            "full_path_repriced"
        ].astype(bool).all():
            raise ValidationError("complete-policy scorecard must contain fully repriced paths")


def _expected_shortfall(values: pd.Series, fraction: float) -> float:
    ordered = np.sort(values.to_numpy(float))
    count = max(1, int(np.ceil(len(ordered) * fraction)))
    return float(ordered[:count].mean())


def summarize_dynamic_reliability(
    scorecard: pd.DataFrame,
    *,
    policy: DynamicReliabilityPolicy,
) -> pd.DataFrame:
    """Compute block-level stability diagnostics for every policy and phase."""

    validate_dynamic_reliability_scorecard(scorecard, policy=policy)
    static_reference = scorecard.loc[
        scorecard["parameter_mode"].astype(str).eq("static"),
        [*PAIR_COLUMNS, "strategy_net_log_return"],
    ].rename(columns={"strategy_net_log_return": "frozen_static_net_log_return"})
    working = scorecard.merge(static_reference, on=list(PAIR_COLUMNS), how="left", validate="many_to_one")
    if working["frozen_static_net_log_return"].isna().any():
        raise ValidationError("every reliability block needs a frozen static reference return")
    rows: list[dict[str, object]] = []
    for keys, local in working.groupby(
        list(SUMMARY_GROUP_COLUMNS) + ["candidate_id", "parameter_mode"], sort=True
    ):
        returns = local["strategy_net_log_return"].astype(float)
        excess = returns - local["buy_hold_net_log_return"].astype(float)
        static_excess = returns - local["frozen_static_net_log_return"].astype(float)
        start = pd.to_datetime(local["block_start"], utc=True).min()
        end = pd.to_datetime(local["block_end_exclusive"], utc=True).max()
        elapsed_years = max((end - start).total_seconds() / (365.25 * 24.0 * 3600.0), 1.0 / 365.25)
        rows.append(
            {
                **dict(zip((*SUMMARY_GROUP_COLUMNS, "candidate_id", "parameter_mode"), keys, strict=True)),
                "block_count": int(len(local)),
                "total_strategy_net_log_return": float(returns.sum()),
                "total_buy_hold_net_log_return": float(local["buy_hold_net_log_return"].astype(float).sum()),
                "total_excess_to_buy_hold": float(excess.sum()),
                "elapsed_years": elapsed_years,
                "annualized_strategy_net_log_return": float(returns.sum()) / elapsed_years,
                "annualized_excess_to_buy_hold": float(excess.sum()) / elapsed_years,
                "total_excess_to_frozen_static": float(static_excess.sum()),
                "annualized_excess_to_frozen_static": float(static_excess.sum()) / elapsed_years,
                "mean_active_exposure_fraction": float(local["active_exposure_fraction"].astype(float).mean()),
                "mean_opportunity_coverage_fraction": float(
                    local["opportunity_coverage_fraction"].astype(float).mean()
                ),
                "negative_return_block_rate": float((returns < 0.0).mean()),
                "relative_failure_block_rate": float((excess < 0.0).mean()),
                "relative_static_failure_block_rate": float((static_excess < 0.0).mean()),
                "worst_block_net_log_return": float(returns.min()),
                "worst_block_excess_to_buy_hold": float(excess.min()),
                "worst_block_excess_to_frozen_static": float(static_excess.min()),
                "tail_mean_net_log_return": _expected_shortfall(returns, policy.tail_fraction),
                "tail_mean_excess_to_buy_hold": _expected_shortfall(excess, policy.tail_fraction),
                "tail_mean_excess_to_frozen_static": _expected_shortfall(
                    static_excess, policy.tail_fraction
                ),
                "block_excess_iqr": float(excess.quantile(0.75) - excess.quantile(0.25)),
                "block_static_excess_iqr": float(
                    static_excess.quantile(0.75) - static_excess.quantile(0.25)
                ),
                "comparison_scope": str(local["comparison_scope"].iloc[0]),
                "full_path_repriced": bool(local["full_path_repriced"].astype(bool).all()),
                "tail_fraction": policy.tail_fraction,
                "weighted_score_used": False,
                "per_block_buy_hold_outperformance_required": False,
            }
        )
    return pd.DataFrame(rows)


def _no_worse_dynamic(dynamic: pd.Series, static: pd.Series, tolerance: float) -> tuple[bool, bool]:
    """Return (dynamic no worse, dynamic strictly better) on reliability axes."""

    lower_is_better = ("negative_return_block_rate", "relative_failure_block_rate", "block_excess_iqr")
    higher_is_better = (
        "worst_block_net_log_return",
        "worst_block_excess_to_buy_hold",
        "tail_mean_net_log_return",
        "tail_mean_excess_to_buy_hold",
    )
    no_worse = all(float(dynamic[key]) <= float(static[key]) + tolerance for key in lower_is_better) and all(
        float(dynamic[key]) >= float(static[key]) - tolerance for key in higher_is_better
    )
    strict = any(float(dynamic[key]) < float(static[key]) - tolerance for key in lower_is_better) or any(
        float(dynamic[key]) > float(static[key]) + tolerance for key in higher_is_better
    )
    return no_worse, strict


def compare_dynamic_reliability(
    summary: pd.DataFrame,
    *,
    policy: DynamicReliabilityPolicy,
) -> pd.DataFrame:
    """Compare stability by Pareto relation, then apply the declared floor."""

    required = {
        *SUMMARY_GROUP_COLUMNS,
        "candidate_id",
        "parameter_mode",
        "total_strategy_net_log_return",
        "total_excess_to_buy_hold",
        "annualized_strategy_net_log_return",
        "annualized_excess_to_buy_hold",
        "total_excess_to_frozen_static",
        "annualized_excess_to_frozen_static",
        "mean_active_exposure_fraction",
        "mean_opportunity_coverage_fraction",
        "negative_return_block_rate",
        "relative_failure_block_rate",
        "worst_block_net_log_return",
        "worst_block_excess_to_buy_hold",
        "tail_mean_net_log_return",
        "tail_mean_excess_to_buy_hold",
        "block_excess_iqr",
        "relative_static_failure_block_rate",
        "worst_block_excess_to_frozen_static",
        "tail_mean_excess_to_frozen_static",
        "block_static_excess_iqr",
        "comparison_scope",
        "full_path_repriced",
    }
    missing = required.difference(summary.columns)
    if missing:
        raise ValidationError(f"reliability summary missing columns: {sorted(missing)}")
    rows: list[dict[str, object]] = []
    for keys, local in summary.groupby(list(SUMMARY_GROUP_COLUMNS), sort=True):
        modes = local["parameter_mode"].astype(str).value_counts().to_dict()
        dynamic_modes = [mode for mode in modes if mode in DYNAMIC_PARAMETER_MODES]
        if modes.get("static") != 1 or len(dynamic_modes) != 1 or modes[dynamic_modes[0]] != 1:
            raise ValidationError(f"each reliability group needs static and dynamic rows: {keys}")
        indexed = local.set_index("parameter_mode")
        static = indexed.loc["static"]
        dynamic = indexed.loc[dynamic_modes[0]]
        dynamic_no_worse, dynamic_strict = _no_worse_dynamic(dynamic, static, policy.numerical_tolerance)
        static_no_worse, static_strict = _no_worse_dynamic(static, dynamic, policy.numerical_tolerance)
        viable = (
            float(dynamic["annualized_strategy_net_log_return"])
            >= policy.minimum_annualized_strategy_net_log_return - policy.numerical_tolerance
            and float(dynamic["annualized_excess_to_buy_hold"])
            >= policy.minimum_annualized_excess_to_buy_hold - policy.numerical_tolerance
            and float(dynamic["annualized_excess_to_frozen_static"])
            >= policy.minimum_annualized_excess_to_frozen_static - policy.numerical_tolerance
            and float(dynamic["mean_active_exposure_fraction"])
            >= policy.minimum_active_exposure_fraction - policy.numerical_tolerance
            and float(dynamic["mean_opportunity_coverage_fraction"])
            >= policy.minimum_opportunity_coverage_fraction - policy.numerical_tolerance
            and policy.comparison_scope == "complete_policy"
            and bool(dynamic["full_path_repriced"])
        )
        if dynamic_no_worse and dynamic_strict:
            reliability_verdict = "dynamic_reliability_pareto_dominates"
        elif static_no_worse and static_strict:
            reliability_verdict = "static_reliability_pareto_dominates"
        else:
            reliability_verdict = "reliability_tradeoff_no_universal_winner"
        viability_verdict = "dynamic_viability_floor_passed" if viable else "dynamic_viability_floor_failed"
        rows.append(
            {
                **dict(zip(SUMMARY_GROUP_COLUMNS, keys, strict=True)),
                "static_candidate_id": str(static["candidate_id"]),
                "dynamic_candidate_id": str(dynamic["candidate_id"]),
                "dynamic_minus_static_total_strategy_net_log_return": float(dynamic["total_strategy_net_log_return"])
                - float(static["total_strategy_net_log_return"]),
                "dynamic_minus_static_total_excess_to_buy_hold": float(dynamic["total_excess_to_buy_hold"])
                - float(static["total_excess_to_buy_hold"]),
                "dynamic_annualized_strategy_net_log_return": float(
                    dynamic["annualized_strategy_net_log_return"]
                ),
                "dynamic_annualized_excess_to_buy_hold": float(dynamic["annualized_excess_to_buy_hold"]),
                "dynamic_annualized_excess_to_frozen_static": float(
                    dynamic["annualized_excess_to_frozen_static"]
                ),
                "dynamic_relative_static_failure_block_rate": float(
                    dynamic["relative_static_failure_block_rate"]
                ),
                "dynamic_worst_block_excess_to_frozen_static": float(
                    dynamic["worst_block_excess_to_frozen_static"]
                ),
                "dynamic_tail_mean_excess_to_frozen_static": float(
                    dynamic["tail_mean_excess_to_frozen_static"]
                ),
                "comparison_scope": policy.comparison_scope,
                "complete_policy_comparison": policy.comparison_scope == "complete_policy",
                "dynamic_mean_active_exposure_fraction": float(dynamic["mean_active_exposure_fraction"]),
                "dynamic_mean_opportunity_coverage_fraction": float(
                    dynamic["mean_opportunity_coverage_fraction"]
                ),
                "reliability_verdict": reliability_verdict,
                "viability_verdict": viability_verdict,
                "dynamic_stability_improvement_is_usable": bool(
                    reliability_verdict == "dynamic_reliability_pareto_dominates" and viable
                ),
                "static_baseline_is_retrospective_oracle": False,
                "weighted_score_used": False,
                "policy_digest": policy.to_dict()["semantic_digest"],
                "dynamic_parameter_authority": False,
            }
        )
    return pd.DataFrame(rows)


def summarize_cross_period_reliability(comparison: pd.DataFrame) -> pd.DataFrame:
    """Require one frozen candidate to pass both development and repeat audit."""

    group_columns = ("comparison_id", "opportunity_side", "state_cell_id")
    required = {
        *group_columns,
        "period_role",
        "static_candidate_id",
        "dynamic_candidate_id",
        "dynamic_stability_improvement_is_usable",
        "dynamic_annualized_strategy_net_log_return",
        "dynamic_annualized_excess_to_buy_hold",
        "dynamic_annualized_excess_to_frozen_static",
        "policy_digest",
    }
    missing = required.difference(comparison.columns)
    if missing:
        raise ValidationError(f"cross-period reliability comparison missing columns: {sorted(missing)}")
    rows: list[dict[str, object]] = []
    for keys, local in comparison.groupby(list(group_columns), sort=True):
        if set(local["period_role"].astype(str)) != {"development", "repeat_audit"}:
            raise ValidationError(f"cross-period reliability needs development and repeat audit: {keys}")
        for column in ("static_candidate_id", "dynamic_candidate_id", "policy_digest"):
            if local[column].astype(str).nunique() != 1:
                raise ValidationError(f"cross-period reliability changed {column}: {keys}")
        passed = bool(local["dynamic_stability_improvement_is_usable"].astype(bool).all())
        rows.append(
            {
                **dict(zip(group_columns, keys, strict=True)),
                "static_candidate_id": str(local["static_candidate_id"].iloc[0]),
                "dynamic_candidate_id": str(local["dynamic_candidate_id"].iloc[0]),
                "required_period_roles": "development|repeat_audit",
                "passed_period_count": int(local["dynamic_stability_improvement_is_usable"].astype(bool).sum()),
                "required_period_count": 2,
                "worst_period_annualized_strategy_net_log_return": float(
                    local["dynamic_annualized_strategy_net_log_return"].min()
                ),
                "worst_period_annualized_excess_to_buy_hold": float(
                    local["dynamic_annualized_excess_to_buy_hold"].min()
                ),
                "worst_period_annualized_excess_to_frozen_static": float(
                    local["dynamic_annualized_excess_to_frozen_static"].min()
                ),
                "mean_period_annualized_strategy_net_log_return": float(
                    local["dynamic_annualized_strategy_net_log_return"].mean()
                ),
                "cross_period_verdict": (
                    "dynamic_reliability_passed_both_periods"
                    if passed
                    else "dynamic_reliability_failed_at_least_one_period"
                ),
                "cross_period_dynamic_is_usable": passed,
                "policy_digest": str(local["policy_digest"].iloc[0]),
                "dynamic_parameter_authority": False,
            }
        )
    return pd.DataFrame(rows)


def rank_cross_period_candidates(cross_period: pd.DataFrame) -> pd.DataFrame:
    """Rank only already-viable candidates; return never overrides stability."""

    ranked = cross_period.copy()
    ranked["stable_candidate_return_rank"] = pd.Series(pd.NA, index=ranked.index, dtype="Int64")
    for _, local in ranked.groupby(["opportunity_side", "state_cell_id"], sort=True):
        eligible = local.loc[local["cross_period_dynamic_is_usable"].astype(bool)]
        if eligible.empty:
            continue
        order = eligible["mean_period_annualized_strategy_net_log_return"].rank(
            method="dense", ascending=False
        ).astype("Int64")
        ranked.loc[eligible.index, "stable_candidate_return_rank"] = order
    ranked["return_ranking_applied_only_after_stability"] = True
    return ranked


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    _ = path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _validate_research_registration_clock(*, registered_at_utc: str, generated_at_utc: str) -> None:
    """Keep wall-clock governance separate from historical market time.

    Historical block timestamps describe when prices occurred.  A policy
    receipt describes when the *research rule* was frozen.  Comparing those
    clocks would reject every honest retrospective study registered today.
    The auditable constraint is therefore that the receipt predates this
    evaluation package; audit-data access remains governed by the workflow's
    sealed-input procedure and version history.
    """

    registered = pd.to_datetime(registered_at_utc, errors="coerce", utc=True)
    generated = pd.to_datetime(generated_at_utc, errors="coerce", utc=True)
    if pd.isna(registered) or pd.isna(generated) or registered >= generated:
        raise ValidationError("reliability policy receipt must predate evaluation package generation")


def run_dynamic_reliability_package(
    *,
    output_dir: Path,
    scorecard: pd.DataFrame,
    policy: DynamicReliabilityPolicy,
    strategy_completeness: StrategyCompletenessEvidence,
) -> dict[str, object]:
    """Persist an auditable stability-first evaluation package atomically."""

    generated_at_utc = datetime.now(UTC).isoformat()
    _validate_research_registration_clock(
        registered_at_utc=policy.registered_at_utc,
        generated_at_utc=generated_at_utc,
    )
    _validate_research_registration_clock(
        registered_at_utc=strategy_completeness.registered_at_utc,
        generated_at_utc=generated_at_utc,
    )
    completeness_payload = strategy_completeness.to_dict()
    if completeness_payload["semantic_digest"] != policy.strategy_completeness_digest:
        raise ValidationError("reliability policy is not bound to its strategy completeness evidence")
    if strategy_completeness.reference_set_digest != policy.reference_set_digest:
        raise ValidationError("reliability policy is not bound to its registered reference set")
    if strategy_completeness.comparison_scope != policy.comparison_scope:
        raise ValidationError("reliability policy and strategy completeness scope differ")
    validate_dynamic_reliability_scorecard(scorecard, policy=policy)
    if not scorecard["comparison_id"].astype(str).eq(strategy_completeness.comparison_id).all():
        raise ValidationError("scorecard comparison_id differs from strategy completeness evidence")
    if not scorecard["execution_semantics_digest"].astype(str).eq(
        strategy_completeness.execution_semantics_digest
    ).all():
        raise ValidationError("strategy completeness execution semantics differ from scorecard")
    if not scorecard["cost_model_digest"].astype(str).eq(strategy_completeness.cost_model_digest).all():
        raise ValidationError("strategy completeness cost model differs from scorecard")
    summary = summarize_dynamic_reliability(scorecard, policy=policy)
    comparison = compare_dynamic_reliability(summary, policy=policy)
    cross_period = summarize_cross_period_reliability(comparison)
    ranking = rank_cross_period_candidates(cross_period)
    parent = output_dir.parent
    _ = parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=parent))
    try:
        scorecard.to_csv(temporary / "block_scorecard.csv", index=False, float_format="%.17g")
        summary.to_csv(temporary / "reliability_summary.csv", index=False, float_format="%.17g")
        comparison.to_csv(temporary / "reliability_comparison.csv", index=False, float_format="%.17g")
        cross_period.to_csv(temporary / "cross_period_reliability.csv", index=False, float_format="%.17g")
        ranking.to_csv(temporary / "stable_candidate_ranking.csv", index=False, float_format="%.17g")
        policy_payload = policy.to_dict()
        _write_json(temporary / "policy.json", policy_payload)
        _write_json(temporary / "strategy_completeness.json", completeness_payload)
        report = "\n".join(
            [
                "# 动态参数稳定性优先评价报告",
                "",
                "- 静态基线必须在开发期前冻结；事后全样本最优静态参数被拒绝。",
                "- 每个评价块分别统计绝对亏损、相对买入持有跑输、最差块、尾部块和离散度。",
                "- 盈利但跑输买入持有、或跑输冻结静态策略，仍分别记为相对失败。",
                "- 只有状态无缺口、机会有明确去向且整条实际路径独立重定价的完整策略，才有资格形成最终比较结论。",
                f"- 本包比较范围：`{policy.comparison_scope}`；局部消融只能用于诊断。",
                "- 稳定性使用 Pareto 关系，不把收益、回撤和失败率压成一个拟合总分。",
                "- 动态策略即使稳定性更好，仍须通过预注册的长期可生存性下限；空仓伪稳定不会被接受。",
                "",
                f"开发与重复审计均通过的候选数：{int(cross_period['cross_period_dynamic_is_usable'].sum())}/{len(cross_period)}。",
            ]
        ) + "\n"
        _ = (temporary / "report_zh.md").write_text(report, encoding="utf-8")
        artifacts = [
            "block_scorecard.csv",
            "reliability_summary.csv",
            "reliability_comparison.csv",
            "cross_period_reliability.csv",
            "stable_candidate_ranking.csv",
            "policy.json",
            "strategy_completeness.json",
            "report_zh.md",
        ]
        manifest: dict[str, object] = {
            "schema_id": SCHEMA_ID,
            "code_version": CODE_VERSION,
            "canonical_entrypoint": CANONICAL_ENTRYPOINT,
            "generated_at_utc": generated_at_utc,
            "policy_digest": policy_payload["semantic_digest"],
            "strategy_completeness_digest": completeness_payload["semantic_digest"],
            "reference_set_digest": strategy_completeness.reference_set_digest,
            "comparison_scope": policy.comparison_scope,
            "block_count": int(len(scorecard) // 2),
            "comparison_group_count": int(len(comparison)),
            "usable_dynamic_stability_improvement_count": int(
                comparison["dynamic_stability_improvement_is_usable"].sum()
            ),
            "cross_period_usable_candidate_count": int(cross_period["cross_period_dynamic_is_usable"].sum()),
            "candidate_ids": sorted(cross_period["dynamic_candidate_id"].astype(str).unique().tolist()),
            "evaluation_plan_digest": policy.evaluation_plan_digest,
            "opportunity_ledger_digests": sorted(scorecard["opportunity_ledger_digest"].astype(str).unique().tolist()),
            "execution_semantics_digests": sorted(scorecard["execution_semantics_digest"].astype(str).unique().tolist()),
            "cost_model_digests": sorted(scorecard["cost_model_digest"].astype(str).unique().tolist()),
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
    validate_persisted_dynamic_reliability_package(output_dir)
    return cast(dict[str, object], json.loads((output_dir / "manifest.json").read_text(encoding="utf-8")))


def validate_persisted_dynamic_reliability_package(output_dir: Path) -> None:
    """Verify hashes, bindings and a full semantic replay of the package."""

    path = output_dir / "manifest.json"
    if not path.is_file():
        raise ValidationError("dynamic reliability manifest is missing")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_id") != SCHEMA_ID:
        raise ValidationError("dynamic reliability manifest schema changed")
    authority = cast(Mapping[str, object], manifest.get("authority", {}))
    for key in ("signal_authority", "routing_authority", "dynamic_parameter_authority", "production_authority"):
        if authority.get(key) is not False:
            raise ValidationError(f"dynamic reliability package cannot grant {key}")
    expected_artifacts = {
        "block_scorecard.csv",
        "reliability_summary.csv",
        "reliability_comparison.csv",
        "cross_period_reliability.csv",
        "stable_candidate_ranking.csv",
        "policy.json",
        "strategy_completeness.json",
        "report_zh.md",
    }
    artifact_rows = cast(list[Mapping[str, object]], manifest.get("artifacts", []))
    if {str(item.get("path")) for item in artifact_rows} != expected_artifacts:
        raise ValidationError("dynamic reliability artifact set is incomplete")
    for item in artifact_rows:
        artifact = output_dir / str(item["path"])
        if not artifact.is_file() or _sha256_file(artifact) != str(item["sha256"]):
            raise ValidationError(f"dynamic reliability artifact hash mismatch: {item['path']}")
    stored = manifest.get("semantic_digest")
    unsigned = dict(manifest)
    _ = unsigned.pop("semantic_digest", None)
    if stored != canonical_digest(unsigned):
        raise ValidationError("dynamic reliability manifest semantic digest mismatch")
    policy = json.loads((output_dir / "policy.json").read_text(encoding="utf-8"))
    if policy.get("semantic_digest") != manifest.get("policy_digest"):
        raise ValidationError("dynamic reliability policy digest drifted")
    unsigned_policy = dict(policy)
    stored_policy_digest = unsigned_policy.pop("semantic_digest", None)
    if stored_policy_digest != canonical_digest(unsigned_policy):
        raise ValidationError("dynamic reliability policy semantic digest mismatch")
    raw_policy = policy.get("policy")
    if not isinstance(raw_policy, Mapping):
        raise ValidationError("dynamic reliability policy is malformed")
    reconstructed = DynamicReliabilityPolicy(**dict(raw_policy))
    completeness = json.loads((output_dir / "strategy_completeness.json").read_text(encoding="utf-8"))
    stored_completeness_digest = completeness.get("semantic_digest")
    unsigned_completeness = dict(completeness)
    _ = unsigned_completeness.pop("semantic_digest", None)
    if stored_completeness_digest != canonical_digest(unsigned_completeness):
        raise ValidationError("strategy completeness semantic digest mismatch")
    if stored_completeness_digest != manifest.get("strategy_completeness_digest"):
        raise ValidationError("strategy completeness manifest binding drifted")
    raw_completeness = completeness.get("evidence")
    if not isinstance(raw_completeness, Mapping):
        raise ValidationError("strategy completeness evidence is malformed")
    reconstructed_completeness = StrategyCompletenessEvidence(**dict(raw_completeness))
    if reconstructed.strategy_completeness_digest != stored_completeness_digest:
        raise ValidationError("reliability policy strategy-completeness binding drifted")
    if reconstructed.reference_set_digest != reconstructed_completeness.reference_set_digest:
        raise ValidationError("reliability policy reference-set binding drifted")
    if reconstructed.comparison_scope != reconstructed_completeness.comparison_scope:
        raise ValidationError("reliability policy comparison scope drifted")
    if reconstructed_completeness.reference_set_digest != manifest.get("reference_set_digest"):
        raise ValidationError("strategy completeness reference set drifted")
    if reconstructed_completeness.comparison_scope != manifest.get("comparison_scope"):
        raise ValidationError("strategy completeness comparison scope drifted")
    _validate_research_registration_clock(
        registered_at_utc=reconstructed.registered_at_utc,
        generated_at_utc=str(manifest.get("generated_at_utc", "")),
    )
    _validate_research_registration_clock(
        registered_at_utc=reconstructed_completeness.registered_at_utc,
        generated_at_utc=str(manifest.get("generated_at_utc", "")),
    )
    scorecard = pd.read_csv(output_dir / "block_scorecard.csv")
    validate_dynamic_reliability_scorecard(scorecard, policy=reconstructed)
    recomputed_summary = summarize_dynamic_reliability(scorecard, policy=reconstructed)
    recomputed_comparison = compare_dynamic_reliability(recomputed_summary, policy=reconstructed)
    recomputed_cross = summarize_cross_period_reliability(recomputed_comparison)
    recomputed_ranking = rank_cross_period_candidates(recomputed_cross)
    for name, recomputed in (
        ("reliability_summary.csv", recomputed_summary),
        ("reliability_comparison.csv", recomputed_comparison),
        ("cross_period_reliability.csv", recomputed_cross),
        ("stable_candidate_ranking.csv", recomputed_ranking),
    ):
        stored_frame = pd.read_csv(output_dir / name)
        if "stable_candidate_return_rank" in recomputed.columns:
            recomputed = recomputed.copy()
            recomputed["stable_candidate_return_rank"] = pd.to_numeric(
                recomputed["stable_candidate_return_rank"], errors="coerce"
            ).astype(float)
        try:
            pd.testing.assert_frame_equal(
                stored_frame.reset_index(drop=True),
                recomputed.reset_index(drop=True),
                check_dtype=False,
                check_exact=False,
                rtol=1e-9,
                atol=1e-11,
            )
        except AssertionError as exc:
            raise ValidationError(f"dynamic reliability artifact does not replay: {name}") from exc


__all__ = [
    "CANONICAL_ENTRYPOINT",
    "CODE_VERSION",
    "DEFAULT_OUTPUT_DIR",
    "DynamicReliabilityPolicy",
    "FIELD_LABELS_ZH",
    "SCHEMA_ID",
    "StrategyCompletenessEvidence",
    "compare_dynamic_reliability",
    "rank_cross_period_candidates",
    "run_dynamic_reliability_package",
    "summarize_dynamic_reliability",
    "summarize_cross_period_reliability",
    "timing_dynamic_reliability_contract",
    "validate_dynamic_reliability_scorecard",
    "validate_persisted_dynamic_reliability_package",
]
