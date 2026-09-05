"""Three-layer evidence contract for timing-strategy development.

The existing timing-evaluation kernel starts from a fully runnable routed
account.  This companion kernel covers the earlier research stages where a
strategy may have only an opportunity definition and an entry signal.  It
keeps three different questions separate:

1. how much independent market opportunity existed;
2. whether causal entries found it with stable post-entry outcomes;
3. whether a complete entry/exit lifecycle converted it into account value.

Strategy adapters own event semantics.  This module owns validation,
normalisation and fail-closed stage authority.
"""

# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportIndexIssue=false, reportMissingTypeStubs=false, reportOperatorIssue=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

StageStatus = Literal["pass", "fail", "inconclusive", "not_applicable"]
OpportunityLedgerStatus = Literal["verified", "inaccurate", "inconclusive"]
EvaluationMode = Literal["entry_only", "full_lifecycle"]
OpportunitySide = Literal["up", "down"]

FIELD_LABELS_ZH: dict[str, str] = {
    "strategy_id": "策略标识",
    "period": "评价区间",
    "year": "自然年",
    "opportunity_side": "机会方向",
    "opportunity_count": "行情机会数",
    "opportunities_per_year": "年均行情机会数",
    "opportunity_supply_per_year": "年均行情机会供给",
    "entry_count": "入场次数",
    "true_hit_count": "真命中数",
    "weak_hit_count": "弱命中数",
    "false_hit_count": "假命中数",
    "true_hit_rate": "真命中率",
    "weak_hit_rate": "弱命中率",
    "false_hit_rate": "假命中率",
    "useful_hit_rate": "真加弱命中率",
    "mean_maximum_favorable_log": "入场后平均最大有利对数跌幅",
    "median_maximum_favorable_log": "入场后最大有利对数跌幅中位数",
    "opportunity_recall_rate": "行情机会召回率",
    "mean_remaining_opportunity_fraction": "入场后剩余机会占比",
    "episode_count": "完整交易次数",
    "mean_net_log_value": "单笔平均净对数价值",
    "assigned_value_per_year": "年均净对数价值",
    "daily_sharpe": "日频夏普",
    "mean_exit_giveback_log": "平均出场回吐",
    "stage_status": "层级状态",
    "ledger_status": "机会账本准确性状态",
    "lock_authority": "锁定权限",
}


@dataclass(frozen=True, slots=True)
class ThreeLayerEvaluationProfile:
    strategy_id: str
    mode: EvaluationMode
    development_period: str
    repeat_audit_period: str
    aggregate_blackbox_period: str
    minimum_detailed_entries: int = 20
    retention_floor: float = 0.80

    def __post_init__(self) -> None:
        if not self.strategy_id.strip():
            raise ValueError("strategy_id must be non-empty")
        periods = {
            self.development_period,
            self.repeat_audit_period,
            self.aggregate_blackbox_period,
        }
        if len(periods) != 3 or any(not value.strip() for value in periods):
            raise ValueError("evaluation periods must be distinct and non-empty")
        if self.minimum_detailed_entries < 1:
            raise ValueError("minimum_detailed_entries must be positive")
        if not 0.0 < self.retention_floor <= 1.0:
            raise ValueError("retention_floor must lie in (0, 1]")


def timing_strategy_stage_evaluation_contract() -> dict[str, object]:
    """Return the fail-closed contract shared by entry-only and full strategies."""

    return {
        "schema_id": "market_state_timing_strategy_stage_evaluation@1.0",
        "infrastructure_owner": "independent_bidirectional_timing_strategy_middle_platform",
        "risk_off_v62_relationship": "reference_example_only_never_owner_or_dependency",
        "authority": "evaluation_only_not_runtime_signal_parameter_or_production_authority",
        "stage_order": [
            "independent_opportunity_universe",
            "causal_entry_hit_and_timing",
            "complete_entry_exit_account_replay",
        ],
        "supported_modes": ["entry_only", "full_lifecycle"],
        "supported_opportunity_sides": ["up", "down", "both_as_separate_ledgers"],
        "stage_gate_rule": (
            "entry evaluation requires a verified opportunity ledger; opportunity "
            "accuracy is not strategy performance and has no pass/fail verdict"
        ),
        "entry_only_rule": "layer_three_is_not_applicable_not_passed_until_an_exit_exists",
        "opportunity_layer": {
            "strategy_signal_independent": True,
            "ex_post_labels_diagnostic_only": True,
            "performance_pass_fail_semantics_forbidden": True,
            "ledger_accuracy_status_required": True,
            "up_and_down_opportunities_must_not_be_netted": True,
            "opportunity_count_size_duration_and_supply_required": True,
            "calendar_year_summary_required_before_sealed_boundary": True,
        },
        "entry_layer": {
            "clock_starts_at_executable_entry": True,
            "true_weak_false_must_remain_separate": True,
            "aggregate_useful_rate_alone_forbidden": True,
            "mean_and_median_depth_required": True,
            "opportunity_recall_and_remaining_fraction_required": True,
            "calendar_year_summary_required_before_sealed_boundary": True,
            "outcome_labels_are_not_trade_exits": True,
        },
        "trade_layer": {
            "next_bar_executable_account_required": True,
            "intrabar_mfe_and_executable_pnl_must_be_separate": True,
            "full_horizon_opportunity_and_held_path_must_be_separate": True,
            "exit_reason_giveback_cost_sharpe_and_drawdown_required": True,
        },
        "blackbox_rule": {
            "aggregate_only": True,
            "criterion_must_match_development_before_comparison": True,
            "missing_layers_are_inconclusive_not_passed": True,
            "may_select_parameters": False,
        },
        "field_labels_zh": dict(FIELD_LABELS_ZH),
    }


def _require_columns(frame: pd.DataFrame, required: set[str], *, name: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{name} missing required columns: {sorted(missing)}")


def directional_zigzag_segments(
    prices: pd.Series,
    threshold: float,
    *,
    side: OpportunitySide,
) -> list[tuple[int, int, int | None]]:
    """Return non-overlapping directional start/extreme/confirmation triples.

    The implementation is direction-neutral: an upside opportunity is a
    downside opportunity in inverse price.  Returned indices always preserve
    original chronological order.  Labels are diagnostic and cannot be used
    by a runtime strategy.
    """

    if side not in {"up", "down"}:
        raise ValueError("side must be 'up' or 'down'")
    if not 0.0 < threshold < 1.0:
        raise ValueError("threshold must lie strictly between zero and one")
    numeric = pd.to_numeric(prices, errors="coerce").to_numpy(float)
    if len(numeric) == 0 or not np.isfinite(numeric).all() or np.any(numeric <= 0.0):
        raise ValueError("prices must be non-empty, finite, and positive")
    values = numeric if side == "down" else 1.0 / numeric
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


def validate_opportunity_ledger(opportunities: pd.DataFrame) -> None:
    """Validate a direction-explicit, strategy-independent opportunity ledger."""

    required = {
        "period",
        "opportunity_id",
        "opportunity_side",
        "start_timestamp",
        "extreme_timestamp",
        "opportunity_size_log",
        "opportunity_bar_count",
        "strategy_signal_independent",
        "diagnostic_only",
    }
    _require_columns(opportunities, required, name="opportunity ledger")
    if opportunities["opportunity_id"].duplicated().any():
        raise ValueError("opportunity_id must be unique")
    if not set(opportunities["opportunity_side"].astype(str)).issubset({"up", "down"}):
        raise ValueError("opportunity_side must contain only up/down")
    start = pd.to_datetime(opportunities["start_timestamp"], errors="raise")
    extreme = pd.to_datetime(opportunities["extreme_timestamp"], errors="raise")
    if not extreme.ge(start).all():
        raise ValueError("opportunity extreme must not precede its start")
    size = pd.to_numeric(opportunities["opportunity_size_log"], errors="raise").to_numpy(
        float
    )
    bars = pd.to_numeric(opportunities["opportunity_bar_count"], errors="raise").to_numpy(
        float
    )
    if not np.isfinite(size).all() or np.any(size <= 0.0) or np.any(bars <= 0.0):
        raise ValueError("opportunity size and duration must be positive and finite")
    if not bool(opportunities["strategy_signal_independent"].astype(bool).all()):
        raise ValueError("opportunity universe must be independent of strategy signals")
    if not bool(opportunities["diagnostic_only"].astype(bool).all()):
        raise ValueError("ex-post opportunities must remain diagnostic-only")


def summarize_opportunities(
    opportunities: pd.DataFrame,
    *,
    group_columns: Sequence[str] = ("period", "opportunity_side"),
) -> pd.DataFrame:
    """Summarize market opportunity without mixing the two directions."""

    validate_opportunity_ledger(opportunities)
    _require_columns(
        opportunities,
        {"elapsed_years", "captured_by_entry", "first_entry_remaining_fraction"},
        name="opportunity ledger",
    )
    rows: list[dict[str, object]] = []
    for keys, local in opportunities.groupby(list(group_columns), sort=True):
        normalized = keys if isinstance(keys, tuple) else (keys,)
        years = 1.0 if "year" in group_columns else float(local["elapsed_years"].iloc[0])
        size = pd.to_numeric(local["opportunity_size_log"], errors="raise")
        captured = local["captured_by_entry"].astype(bool)
        remaining = pd.to_numeric(
            local.loc[captured, "first_entry_remaining_fraction"], errors="coerce"
        ).dropna()
        row: dict[str, object] = dict(zip(group_columns, normalized, strict=True))
        row.update(
            {
                "opportunity_count": len(local),
                "opportunities_per_year": len(local) / years,
                "mean_opportunity_size_log": float(size.mean()),
                "median_opportunity_size_log": float(size.median()),
                "opportunity_supply_per_year": float(size.sum()) / years,
                "mean_opportunity_bars": float(
                    pd.to_numeric(local["opportunity_bar_count"], errors="raise").mean()
                ),
                "captured_opportunity_count": int(captured.sum()),
                "opportunity_recall_rate": float(captured.mean()),
                "mean_first_entry_remaining_fraction": (
                    float(remaining.mean()) if len(remaining) else np.nan
                ),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def validate_entry_outcome_ledger(entries: pd.DataFrame) -> None:
    """Validate one causal, scale-native entry outcome ledger."""

    required = {
        "period",
        "entry_id",
        "signal_timestamp",
        "execution_timestamp",
        "weak_threshold_log",
        "true_threshold_log",
        "maximum_favorable_intrabar_log",
        "outcome_class",
    }
    _require_columns(entries, required, name="entry outcome ledger")
    if entries["entry_id"].duplicated().any():
        raise ValueError("entry_id must be unique")
    signal = pd.to_datetime(entries["signal_timestamp"], errors="raise")
    execution = pd.to_datetime(entries["execution_timestamp"], errors="raise")
    if not execution.gt(signal).all():
        raise ValueError("entry execution must be strictly after signal close")
    weak = pd.to_numeric(entries["weak_threshold_log"], errors="raise").to_numpy(float)
    true = pd.to_numeric(entries["true_threshold_log"], errors="raise").to_numpy(float)
    mfe = pd.to_numeric(entries["maximum_favorable_intrabar_log"], errors="raise").to_numpy(float)
    if not (np.isfinite(weak).all() and np.isfinite(true).all() and np.isfinite(mfe).all()):
        raise ValueError("entry thresholds and MFE must be finite")
    if np.any(weak <= 0.0) or np.any(true <= weak) or np.any(mfe < 0.0):
        raise ValueError("entry thresholds must satisfy 0 < weak < true and MFE >= 0")
    expected = np.where(mfe >= true, "true_hit", np.where(mfe >= weak, "weak_hit", "false_hit"))
    observed = entries["outcome_class"].astype(str).to_numpy()
    if not np.array_equal(expected, observed):
        raise ValueError("entry outcome classes do not match the registered thresholds")


def summarize_entry_outcomes(
    entries: pd.DataFrame,
    *,
    group_columns: Sequence[str] = ("period",),
) -> pd.DataFrame:
    """Keep hit composition and depth visible instead of collapsing to one rate."""

    validate_entry_outcome_ledger(entries)
    _require_columns(
        entries,
        {"bars_to_trough", "matched_opportunity", "remaining_opportunity_fraction"},
        name="entry outcome ledger",
    )
    rows: list[dict[str, object]] = []
    grouped = entries.groupby(list(group_columns), sort=True, dropna=False)
    for keys, local in grouped:
        normalized_keys = keys if isinstance(keys, tuple) else (keys,)
        counts = local["outcome_class"].value_counts()
        total = len(local)
        matched = local["matched_opportunity"].astype(bool)
        remaining = pd.to_numeric(
            local.loc[matched, "remaining_opportunity_fraction"], errors="coerce"
        ).dropna()
        row: dict[str, object] = dict(zip(group_columns, normalized_keys, strict=True))
        true_count = int(counts.get("true_hit", 0))
        weak_count = int(counts.get("weak_hit", 0))
        false_count = int(counts.get("false_hit", 0))
        mfe = pd.to_numeric(local["maximum_favorable_intrabar_log"], errors="raise")
        row.update(
            {
                "entry_count": total,
                "true_hit_count": true_count,
                "weak_hit_count": weak_count,
                "false_hit_count": false_count,
                "true_hit_rate": true_count / total if total else 0.0,
                "weak_hit_rate": weak_count / total if total else 0.0,
                "false_hit_rate": false_count / total if total else 0.0,
                "useful_hit_rate": (true_count + weak_count) / total if total else 0.0,
                "mean_maximum_favorable_log": float(mfe.mean()) if total else 0.0,
                "median_maximum_favorable_log": float(mfe.median()) if total else 0.0,
                "p25_maximum_favorable_log": float(mfe.quantile(0.25)) if total else 0.0,
                "mean_bars_to_trough": float(
                    pd.to_numeric(local["bars_to_trough"], errors="coerce").mean()
                ),
                "matched_opportunity_entry_count": int(matched.sum()),
                "mean_remaining_opportunity_fraction": (
                    float(remaining.mean()) if len(remaining) else np.nan
                ),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def classify_entry_stability(
    summary: pd.DataFrame,
    *,
    profile: ThreeLayerEvaluationProfile,
) -> pd.DataFrame:
    """Compare depth and composition, failing closed when evidence is too small."""

    required = {
        "period",
        "entry_count",
        "true_hit_rate",
        "weak_hit_rate",
        "false_hit_rate",
        "useful_hit_rate",
        "mean_maximum_favorable_log",
    }
    _require_columns(summary, required, name="entry summary")
    reference_rows = summary.loc[summary["period"].eq(profile.development_period)]
    if len(reference_rows) != 1:
        raise ValueError("development entry summary must contain exactly one row")
    reference = reference_rows.iloc[0]
    rows: list[dict[str, object]] = []
    for period in (profile.repeat_audit_period, profile.aggregate_blackbox_period):
        evaluated_rows = summary.loc[summary["period"].eq(period)]
        if evaluated_rows.empty:
            rows.append(
                {
                    "period": period,
                    "stage_status": "inconclusive",
                    "reason": "required_period_missing",
                    "entry_count": 0,
                }
            )
            continue
        if len(evaluated_rows) != 1:
            raise ValueError(f"entry summary for {period} must contain exactly one row")
        evaluated = evaluated_rows.iloc[0]
        count = int(evaluated["entry_count"])
        compatible = bool(evaluated.get("criterion_compatible", True))
        ratios: dict[str, float] = {}
        for metric in (
            "true_hit_rate",
            "useful_hit_rate",
            "mean_maximum_favorable_log",
        ):
            reference_value = float(reference[metric])
            value = float(evaluated[metric])
            ratios[f"{metric}_retention"] = (
                value / reference_value if reference_value > 0.0 and np.isfinite(value) else np.nan
            )
        finite_ratios = [value for value in ratios.values() if np.isfinite(value)]
        depth_or_composition_flag = bool(
            finite_ratios and min(finite_ratios) < profile.retention_floor
        )
        if not compatible:
            status: StageStatus = "inconclusive"
            reason = "outcome_criterion_incompatible"
        elif count < profile.minimum_detailed_entries:
            status = "inconclusive"
            reason = "insufficient_detailed_entries"
        elif depth_or_composition_flag:
            status = "fail"
            reason = "entry_depth_or_hit_composition_degraded"
        else:
            status = "pass"
            reason = "entry_depth_and_hit_composition_retained"
        rows.append(
            {
                "period": period,
                "stage_status": status,
                "reason": reason,
                "entry_count": count,
                "criterion_compatible": compatible,
                "depth_or_composition_degradation_flag": depth_or_composition_flag,
                **ratios,
            }
        )
    return pd.DataFrame(rows)


def validate_trade_lifecycle_ledger(trades: pd.DataFrame) -> None:
    """Validate an executable long/short lifecycle without netting directions."""

    required = {
        "period",
        "episode_id",
        "opportunity_side",
        "signal_timestamp",
        "execution_timestamp",
        "exit_timestamp",
        "net_log_value",
        "full_horizon_mfe_log",
        "held_path_mfe_log",
        "exit_giveback_log",
        "transaction_cost_log",
    }
    _require_columns(trades, required, name="trade lifecycle ledger")
    if trades["episode_id"].duplicated().any():
        raise ValueError("episode_id must be unique")
    if not set(trades["opportunity_side"].astype(str)).issubset({"up", "down"}):
        raise ValueError("opportunity_side must contain only up/down")
    signal = pd.to_datetime(trades["signal_timestamp"], errors="raise")
    execution = pd.to_datetime(trades["execution_timestamp"], errors="raise")
    exit_time = pd.to_datetime(trades["exit_timestamp"], errors="raise")
    if not execution.gt(signal).all() or not exit_time.ge(execution).all():
        raise ValueError("trades must execute after signal and exit no earlier than execution")
    numeric_columns = {
        "net_log_value",
        "full_horizon_mfe_log",
        "held_path_mfe_log",
        "exit_giveback_log",
        "transaction_cost_log",
    }
    numeric = trades.loc[:, sorted(numeric_columns)].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(numeric.to_numpy(float)).all():
        raise ValueError("trade lifecycle metrics must be finite")
    nonnegative = numeric.loc[
        :, [
            "full_horizon_mfe_log",
            "held_path_mfe_log",
            "exit_giveback_log",
            "transaction_cost_log",
        ]
    ]
    if not nonnegative.ge(0.0).all().all():
        raise ValueError("MFE, giveback, and cost metrics must be nonnegative")


def summarize_trade_lifecycles(
    trades: pd.DataFrame,
    *,
    group_columns: Sequence[str] = ("period", "opportunity_side"),
) -> pd.DataFrame:
    """Summarize complete account episodes while preserving long/short ownership."""

    validate_trade_lifecycle_ledger(trades)
    _require_columns(trades, {"elapsed_years", "bar_count"}, name="trade lifecycle ledger")
    rows: list[dict[str, object]] = []
    for keys, local in trades.groupby(list(group_columns), sort=True):
        normalized = keys if isinstance(keys, tuple) else (keys,)
        years = 1.0 if "year" in group_columns else float(local["elapsed_years"].iloc[0])
        net = pd.to_numeric(local["net_log_value"], errors="raise")
        row: dict[str, object] = dict(zip(group_columns, normalized, strict=True))
        row.update(
            {
                "episode_count": len(local),
                "episodes_per_year": len(local) / years,
                "mean_net_log_value": float(net.mean()),
                "median_net_log_value": float(net.median()),
                "positive_episode_rate": float(net.gt(0.0).mean()),
                "assigned_value_per_year": float(net.sum()) / years,
                "mean_full_horizon_mfe_log": float(
                    pd.to_numeric(local["full_horizon_mfe_log"], errors="raise").mean()
                ),
                "mean_held_path_mfe_log": float(
                    pd.to_numeric(local["held_path_mfe_log"], errors="raise").mean()
                ),
                "mean_exit_giveback_log": float(
                    pd.to_numeric(local["exit_giveback_log"], errors="raise").mean()
                ),
                "mean_transaction_cost_log": float(
                    pd.to_numeric(local["transaction_cost_log"], errors="raise").mean()
                ),
                "mean_bars": float(pd.to_numeric(local["bar_count"], errors="raise").mean()),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def build_three_layer_manifest(
    *,
    profile: ThreeLayerEvaluationProfile,
    opportunity_stage: Mapping[str, object],
    entry_stage: Mapping[str, object],
    trade_stage: Mapping[str, object] | None,
) -> dict[str, object]:
    """Build separate entry-lock and whole-strategy-lock decisions."""

    allowed: set[str] = {"pass", "fail", "inconclusive", "not_applicable"}

    def status_of(stage: Mapping[str, object], name: str) -> str:
        status = str(stage.get("stage_status", ""))
        if status not in allowed:
            raise ValueError(f"{name} has invalid stage_status: {status!r}")
        return status

    if "stage_status" in opportunity_stage:
        raise ValueError("opportunity_stage uses ledger_status, never pass/fail stage_status")
    opportunity_status = str(opportunity_stage.get("ledger_status", ""))
    if opportunity_status not in {"verified", "inaccurate", "inconclusive"}:
        raise ValueError(
            f"opportunity_stage has invalid ledger_status: {opportunity_status!r}"
        )
    entry_status = status_of(entry_stage, "entry_stage")
    if trade_stage is None:
        trade_status = "not_applicable" if profile.mode == "entry_only" else "inconclusive"
        normalized_trade: dict[str, object] = {
            "stage_status": trade_status,
            "reason": "exit_not_defined" if profile.mode == "entry_only" else "trade_stage_missing",
        }
    else:
        trade_status = status_of(trade_stage, "trade_stage")
        normalized_trade = dict(trade_stage)
    if profile.mode == "entry_only" and trade_status != "not_applicable":
        raise ValueError("entry_only evaluation must not mark the trade layer passed")
    entry_lock_eligible = opportunity_status == "verified" and entry_status == "pass"
    strategy_lock_eligible = entry_lock_eligible and trade_status == "pass"
    return {
        "schema_id": "market_state_timing_strategy_three_layer_manifest@1.0",
        "strategy_id": profile.strategy_id,
        "mode": profile.mode,
        "contract_schema": timing_strategy_stage_evaluation_contract()["schema_id"],
        "layers": {
            "opportunity_universe": dict(opportunity_stage),
            "entry_hit_and_timing": dict(entry_stage),
            "complete_trade_lifecycle": normalized_trade,
        },
        "entry_lock_eligible": entry_lock_eligible,
        "strategy_lock_eligible": strategy_lock_eligible,
        "lock_authority": (
            "eligible_for_strategy_lock_review"
            if strategy_lock_eligible
            else (
                "eligible_for_entry_lock_review_only"
                if entry_lock_eligible
                else "do_not_lock_failed_or_incomplete_evidence"
            )
        ),
        "later_stage_may_override_earlier_failure": False,
        "runtime_or_parameter_authority": False,
        "field_labels_zh": dict(FIELD_LABELS_ZH),
    }


__all__ = [
    "EvaluationMode",
    "FIELD_LABELS_ZH",
    "OpportunitySide",
    "OpportunityLedgerStatus",
    "StageStatus",
    "ThreeLayerEvaluationProfile",
    "build_three_layer_manifest",
    "classify_entry_stability",
    "directional_zigzag_segments",
    "summarize_entry_outcomes",
    "summarize_opportunities",
    "summarize_trade_lifecycles",
    "timing_strategy_stage_evaluation_contract",
    "validate_entry_outcome_ledger",
    "validate_opportunity_ledger",
    "validate_trade_lifecycle_ledger",
]
