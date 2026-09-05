"""Canonical evaluation contract for long/cash state-machine buckets."""

# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false, reportMissingTypeStubs=false
# pyright: reportIndexIssue=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from factor_lab.market_state.timing_evaluation import (
    counterfactual_action_value_table,
    summarize_timing_opportunity_events,
    timing_evaluation_contract,
)
from factor_lab.market_state.timing_evaluation import (
    elapsed_years as common_elapsed_years,
)
from factor_lab.market_state.timing_evaluation import (
    override_position_inside_bucket as override_timing_position_inside_bucket,
)
from factor_lab.market_state.timing_evaluation import (
    period_shift_table as common_period_shift_table,
)
from factor_lab.market_state.timing_evaluation import (
    summarize_bucket_episodes as common_summarize_bucket_episodes,
)

BucketAction = Literal["long", "cash"]

FIELD_LABELS_ZH: dict[str, str] = {
    "level": "状态层级",
    "bucket": "状态桶",
    "period": "评价区间",
    "assigned_action": "当前分配动作",
    "opposite_action": "相反对照动作",
    "bar_count": "责任K线数",
    "episode_count": "责任事件数",
    "long_minus_cash_net_log_return_delta": "持仓相对空仓的账户净对数收益增量",
    "assigned_action_net_log_value": "当前动作净对数价值",
    "assigned_action_relative_wealth_ratio": "当前动作相对财富倍数",
    "assigned_action_relative_wealth_effect": "当前动作相对财富影响",
    "value_sign": "价值正负",
    "interpretation_zh": "中文解读",
    "out_of_bucket_router_frozen": "桶外路由是否固定",
    "values_additive_across_buckets": "跨桶数值是否可直接相加",
    "opportunities_per_year": "年均下跌机会数",
    "mean_net_decline": "平均峰谷净跌幅",
    "downside_supply_per_year": "年均下跌供给",
    "positive_net_protection_rate": "正净保护机会占比",
    "downside_capture_rate": "下跌能量捕获率",
    "mean_net_protection_per_opportunity": "单次机会平均净保护价值",
    "episodes_per_year": "年均责任事件数",
    "mean_bars_per_episode": "单次责任事件平均K线数",
    "mean_value_per_episode": "单次责任事件平均净价值",
    "assigned_value_per_1000_bars": "每1000根责任K线净价值",
    "incremental_cost_per_episode": "单次责任事件增量成本",
    "requires_matched_attribution": "是否需要第二层匹配归因",
    "matched_attribution_adapter_status": "匹配归因适配器状态",
}

OPPORTUNITY_THRESHOLDS: tuple[float, ...] = (0.01, 0.02, 0.03, 0.05)
PRIMARY_OPPORTUNITY_THRESHOLD = 0.02

_REQUIRED_METRIC_COLUMNS = {
    "level",
    "bucket",
    "period",
    "assigned_action",
    "bar_count",
    "episode_count",
    "long_minus_cash_net_log_return_delta",
}


def override_position_inside_bucket(
    current_position: pd.Series,
    bucket_mask: pd.Series,
    action: BucketAction,
) -> pd.Series:
    """V62 long/cash adapter over the project-level timing evaluator."""

    numeric = pd.to_numeric(current_position, errors="coerce").astype(float)
    if numeric.isna().any() or not numeric.isin((0.0, 1.0)).all():
        raise ValueError("current_position must contain only finite binary values")
    return override_timing_position_inside_bucket(
        numeric,
        bucket_mask,
        action,
        allowed_positions=(0.0, 1.0),
    )


def assigned_action_value_table(bucket_metrics: pd.DataFrame) -> pd.DataFrame:
    """Orient values so positive always means the assigned action adds value."""

    missing = _REQUIRED_METRIC_COLUMNS.difference(bucket_metrics.columns)
    if missing:
        raise ValueError(f"bucket_metrics missing required columns: {sorted(missing)}")
    actions = set(bucket_metrics["assigned_action"].astype(str))
    if not actions.issubset({"long", "cash"}):
        raise ValueError("assigned_action must contain only long/cash leaf actions")

    result = bucket_metrics.loc[:, sorted(_REQUIRED_METRIC_COLUMNS)].copy()
    direction = np.where(result["assigned_action"].eq("long"), 1.0, -1.0)
    value = direction * pd.to_numeric(
        result["long_minus_cash_net_log_return_delta"],
        errors="raise",
    ).astype(float)
    result["counterfactual_action"] = np.where(
        result["assigned_action"].eq("long"),
        "cash",
        "long",
    )
    result["assigned_minus_counterfactual_net_log_return_delta"] = value
    common = counterfactual_action_value_table(result)
    common["opposite_action"] = common["counterfactual_action"]
    common["long_minus_cash_net_log_return_delta"] = result["long_minus_cash_net_log_return_delta"].to_numpy(float)
    return common.drop(
        columns=[
            "counterfactual_action",
            "assigned_minus_counterfactual_net_log_return_delta",
        ]
    )


def state_bucket_evaluation_contract() -> dict[str, object]:
    """Return the persisted authority and sign convention for bucket evaluation."""

    return {
        "schema_id": "risk_off_state_bucket_evaluation@1.0",
        "infrastructure_contract": timing_evaluation_contract()["schema_id"],
        "position_domain": [0, 1],
        "candidate_actions": ["long", "cash"],
        "primary_formula": ("assigned_action_account_net_log_return_minus_opposite_action_account_net_log_return"),
        "counterfactual_rule": ("override_only_the_target_bucket_and_freeze_every_out_of_bucket_route"),
        "positive_meaning": "current_assigned_action_adds_value",
        "negative_meaning": "current_assigned_action_harms_account",
        "relative_wealth_effect_formula": "exp(assigned_action_net_log_value)-1",
        "bucket_cagr_is_authoritative": False,
        "isolated_bucket_with_outside_cash_is_authoritative": False,
        "values_additive_across_buckets": False,
        "continuous_account_attribution_required_for_additive_contribution": True,
        "field_labels_zh": dict(FIELD_LABELS_ZH),
    }


def elapsed_years(index: pd.DatetimeIndex) -> float:
    """V62 adapter for the common elapsed-year denominator."""

    return common_elapsed_years(index)


def zigzag_decline_segments(
    prices: pd.Series,
    threshold: float,
) -> list[tuple[int, int, int | None]]:
    """Return ex-post non-overlapping peak/trough/rebound index triples."""

    if not 0.0 < threshold < 1.0:
        raise ValueError("threshold must lie strictly between zero and one")
    values = pd.to_numeric(prices, errors="coerce").to_numpy(float)
    if len(values) == 0 or not np.isfinite(values).all() or np.any(values <= 0.0):
        raise ValueError("prices must be non-empty, finite, and positive")
    peak = 0
    trough = 0
    active = False
    rows: list[tuple[int, int, int | None]] = []
    for index in range(1, len(values)):
        if not active:
            if values[index] >= values[peak]:
                peak = index
            if values[index] / values[peak] - 1.0 <= -threshold:
                active = True
                trough = index
            continue
        if values[index] <= values[trough]:
            trough = index
        if values[index] / values[trough] - 1.0 >= threshold:
            rows.append((peak, trough, index))
            peak = index
            trough = index
            active = False
    if active:
        rows.append((peak, trough, None))
    return rows


def summarize_opportunity_events(events: pd.DataFrame) -> pd.DataFrame:
    """Map the V62 downside ledger onto the common opportunity normalizer."""

    adapter = events.rename(
        columns={
            "net_peak_to_trough_decline": "opportunity_size",
            "gross_downside_bar_supply": "opportunity_supply",
            "positive_net_protection": "positive_net_value",
            "avoided_downside": "captured_opportunity",
            "missed_upside": "missed_favorable_move",
            "net_protection_value": "net_opportunity_value",
        }
    )
    summary = summarize_timing_opportunity_events(adapter)
    return summary.rename(
        columns={
            "mean_opportunity_size": "mean_net_decline",
            "median_opportunity_size": "median_net_decline",
            "opportunity_supply_total": "downside_supply_total",
            "opportunity_supply_per_year": "downside_supply_per_year",
            "positive_net_value_count": "positive_net_protection_count",
            "positive_net_value_rate": "positive_net_protection_rate",
            "captured_opportunity_total": "avoided_downside_total",
            "opportunity_capture_rate": "downside_capture_rate",
            "missed_favorable_move_total": "missed_upside_total",
            "net_opportunity_value_total": "net_protection_total",
            "net_opportunity_value_per_year": "net_protection_per_year",
            "mean_net_value_per_opportunity": ("mean_net_protection_per_opportunity"),
        }
    )


def summarize_bucket_episodes(episodes: pd.DataFrame) -> pd.DataFrame:
    """V62 adapter for the common episode normalizer."""

    return common_summarize_bucket_episodes(episodes)


def period_shift_table(
    summary: pd.DataFrame,
    *,
    entity: str,
    metrics: list[str],
    development_period: str,
    diagnostic_period: str,
) -> pd.DataFrame:
    """V62 adapter for the common cross-period normalizer."""

    return common_period_shift_table(
        summary,
        entity=entity,
        metrics=metrics,
        development_period=development_period,
        diagnostic_period=diagnostic_period,
    )


def opportunity_attribution_contract() -> dict[str, object]:
    """Return the mandatory post-optimization opportunity attribution contract."""

    return {
        "schema_id": "risk_off_v62_opportunity_attribution@1.0",
        "infrastructure_contract": timing_evaluation_contract()["schema_id"],
        "authority": "evaluation_authority_not_runtime_signal_not_parameter_authority",
        "required_after_every_optimization_round": True,
        "workflow_stage": "stage_1_cross_period_inconsistency_screening",
        "screening_result_is_final_causal_attribution": False,
        "stage_2_contract": "risk_off_cross_period_matched_attribution@1.0",
        "opportunity_definition": "ex_post_non_overlapping_zigzag_peak_to_trough",
        "thresholds": list(OPPORTUNITY_THRESHOLDS),
        "primary_descriptive_threshold": PRIMARY_OPPORTUNITY_THRESHOLD,
        "threshold_selection_by_best_result_forbidden": True,
        "runtime_signal_use_forbidden": True,
        "development_period": "2009-2017",
        "diagnostic_period": "2018-2020",
        "sealed_2021_plus_must_remain_unread": True,
        "caught_definition": "event_net_protection_value_strictly_positive",
        "normalization_layers": ["per_year", "per_opportunity", "per_bucket_episode", "per_bar"],
        "required_attribution_axes": [
            "opportunity_supply",
            "opportunity_size",
            "capture_skill",
            "bucket_action_sign_stability",
            "lifecycle_fragmentation",
            "transaction_cost",
        ],
        "diagnostic_labels": {
            "opportunity_scarcity": "opportunities_or_downside_supply_per_year_declines",
            "capability_drift": "per_opportunity_or_per_bar_value_declines",
            "structural_instability": "assigned_action_value_changes_sign_across_periods",
            "persistent_wrong_assignment": "assigned_action_value_is_negative_in_both_periods",
        },
        "overfit_is_causal_proof": False,
        "field_labels_zh": dict(FIELD_LABELS_ZH),
    }


__all__ = [
    "BucketAction",
    "FIELD_LABELS_ZH",
    "OPPORTUNITY_THRESHOLDS",
    "PRIMARY_OPPORTUNITY_THRESHOLD",
    "assigned_action_value_table",
    "elapsed_years",
    "opportunity_attribution_contract",
    "override_position_inside_bucket",
    "period_shift_table",
    "state_bucket_evaluation_contract",
    "summarize_bucket_episodes",
    "summarize_opportunity_events",
    "zigzag_decline_segments",
]
