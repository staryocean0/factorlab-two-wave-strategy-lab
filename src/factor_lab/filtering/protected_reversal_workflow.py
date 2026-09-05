"""Protected short-horizon reversal workflow.

This workflow is the reversal-side companion to the frequency-first trend
timing workflow.  The shared backbone is still periodic filtering: a coarser
filter defines the allowed direction, while a shorter-horizon filter/deviation
template waits for an adverse small-cycle overextension and enters only in the
coarser direction.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from typing import Literal, cast

import numpy as np
import pandas as pd

from factor_lab.filtering.costs import (
    DEFAULT_COMMISSION_BPS,
    DEFAULT_STAMP_TAX_BPS,
)
from factor_lab.filtering.short_horizon_attribution import (
    GovernanceFeedbackLoopConfig,
    GovernanceFeedbackLoopDecision,
    LossProfitOptimizationPlan,
    ShortHorizonFailureAttribution,
    analyze_short_horizon_position_frame,
    build_loss_profit_optimization_plan,
    decide_governance_feedback_loop,
    extract_long_cash_trades,
)
from factor_lab.filtering.strategy_workflow import apply_signal_governance
from factor_lab.filtering.timing_validation import (
    BacktestMetrics,
    FilterSpec,
    PeriodName,
    TimingValidationConfig,
    apply_filter_spec,
    backtest_long_cash,
    resample_close_frame,
    signal_from_filtered,
)
from factor_lab.filtering.tool_selection import filter_spec_to_dict

PERIOD_FINE_TO_COARSE_RANK: dict[str, int] = {
    "1min": 0,
    "5min": 1,
    "15min": 2,
    "30min": 3,
    "60min": 4,
    "day": 5,
    "week": 6,
}

ProtectedReversalTemplate = Literal[
    "lowpass_deviation_reversal",
    "bandpass_phase_exhaustion_reversal",
    "return_zscore_reversal",
]

SUPPORTED_PROTECTED_REVERSAL_TEMPLATES: tuple[ProtectedReversalTemplate, ...] = (
    "lowpass_deviation_reversal",
    "bandpass_phase_exhaustion_reversal",
    "return_zscore_reversal",
)


@dataclass(frozen=True, slots=True)
class ProtectedReversalConfig:
    """Configuration for a higher-direction protected reversal template."""

    higher_period: PeriodName = "60min"
    execution_period: PeriodName = "5min"
    higher_filter_spec: FilterSpec | None = None
    execution_filter_spec: FilterSpec | None = None
    reversal_template: ProtectedReversalTemplate = "bandpass_phase_exhaustion_reversal"
    entry_z: float = 1.5
    exit_z: float = 0.25
    z_window_bars: int = 96
    return_lookback_bars: int = 8
    higher_cycle_days_equiv: float | None = None
    execution_cycle_days_equiv: float | None = None
    min_higher_cycle_ratio: float = 2.0
    max_higher_cycle_ratio: float = 64.0
    max_hold_bars: int = 48
    min_hold_bars: int = 1
    cooldown_bars: int = 0
    confirmation_bars: int = 1
    min_observations: int = 60
    commission_bps: float = DEFAULT_COMMISSION_BPS
    stamp_tax_bps: float = DEFAULT_STAMP_TAX_BPS

    def __post_init__(self) -> None:
        if self.reversal_template not in SUPPORTED_PROTECTED_REVERSAL_TEMPLATES:
            raise ValueError("Unsupported reversal_template")
        if (
            PERIOD_FINE_TO_COARSE_RANK[self.higher_period]
            <= PERIOD_FINE_TO_COARSE_RANK[self.execution_period]
        ):
            raise ValueError("higher_period must be coarser than execution_period")
        if self.higher_filter_spec is None:
            raise ValueError("higher_filter_spec is required")
        if self.reversal_template != "return_zscore_reversal":
            if self.execution_filter_spec is None:
                raise ValueError("execution_filter_spec is required")
            if (
                self.reversal_template == "lowpass_deviation_reversal"
                and self.execution_filter_spec.output_kind != "level"
            ):
                raise ValueError(
                    "lowpass_deviation_reversal requires "
                    + "execution_filter_spec.output_kind='level'"
                )
            if (
                self.reversal_template == "lowpass_deviation_reversal"
                and self.execution_filter_spec.mode != "lowpass"
            ):
                raise ValueError(
                    "lowpass_deviation_reversal requires "
                    + "execution_filter_spec.mode='lowpass'"
                )
            if (
                self.reversal_template == "bandpass_phase_exhaustion_reversal"
                and self.execution_filter_spec.output_kind != "component"
            ):
                raise ValueError(
                    "bandpass_phase_exhaustion_reversal requires "
                    + "execution_filter_spec.output_kind='component'"
                )
            if (
                self.reversal_template == "bandpass_phase_exhaustion_reversal"
                and self.execution_filter_spec.mode != "bandpass"
            ):
                raise ValueError(
                    "bandpass_phase_exhaustion_reversal requires "
                    + "execution_filter_spec.mode='bandpass'"
                )
        if self.entry_z <= 0.0:
            raise ValueError("entry_z must be > 0")
        if self.exit_z < 0.0:
            raise ValueError("exit_z must be >= 0")
        if self.z_window_bars < 10:
            raise ValueError("z_window_bars must be >= 10")
        if self.return_lookback_bars < 1:
            raise ValueError("return_lookback_bars must be >= 1")
        if (self.higher_cycle_days_equiv is None) != (
            self.execution_cycle_days_equiv is None
        ):
            raise ValueError(
                "higher_cycle_days_equiv and execution_cycle_days_equiv must be " +
                "provided together"
            )
        if self.higher_cycle_days_equiv is not None:
            if self.higher_cycle_days_equiv <= 0.0:
                raise ValueError("higher_cycle_days_equiv must be > 0")
            if self.execution_cycle_days_equiv is None:
                raise ValueError("execution_cycle_days_equiv is required")
            if self.execution_cycle_days_equiv <= 0.0:
                raise ValueError("execution_cycle_days_equiv must be > 0")
            ratio = self.higher_cycle_days_equiv / self.execution_cycle_days_equiv
            if not (
                self.min_higher_cycle_ratio <= ratio <= self.max_higher_cycle_ratio
            ):
                raise ValueError(
                    "higher_cycle_days_equiv must be a valid larger physical "
                    + "cycle for protected reversal"
                )
        if self.min_higher_cycle_ratio <= 1.0:
            raise ValueError("min_higher_cycle_ratio must be > 1")
        if self.max_higher_cycle_ratio < self.min_higher_cycle_ratio:
            raise ValueError("max_higher_cycle_ratio must be >= min_higher_cycle_ratio")
        if self.max_hold_bars < 1:
            raise ValueError("max_hold_bars must be >= 1")
        if self.min_hold_bars < 0:
            raise ValueError("min_hold_bars must be >= 0")
        if self.cooldown_bars < 0:
            raise ValueError("cooldown_bars must be >= 0")
        if self.confirmation_bars < 1:
            raise ValueError("confirmation_bars must be >= 1")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["higher_filter_spec"] = (
            filter_spec_to_dict(self.higher_filter_spec)
            if self.higher_filter_spec is not None
            else None
        )
        payload["execution_filter_spec"] = (
            filter_spec_to_dict(self.execution_filter_spec)
            if self.execution_filter_spec is not None
            else None
        )
        return payload


@dataclass(frozen=True, slots=True)
class ProtectedReversalSignals:
    """Signal diagnostics for one protected reversal run."""

    sample_start: str
    sample_end: str
    sample_count: int
    higher_gate_on_share: float
    raw_reversal_on_share: float
    composite_on_share: float
    blocked_by_higher_gate_share: float
    blocked_raw_reversal_share: float
    admitted_raw_reversal_share: float
    entry_count: int
    exit_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProtectedReversalWorkflowResult:
    """Backtest artifact for a protected reversal strategy."""

    template: str
    period: str
    higher_period: str
    metrics: BacktestMetrics
    signal_diagnostics: ProtectedReversalSignals
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "template": self.template,
            "period": self.period,
            "higher_period": self.higher_period,
            "metrics": self.metrics.to_dict(),
            "signal_diagnostics": self.signal_diagnostics.to_dict(),
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class ProtectedReversalGovernanceLoopConfig:
    """Bounded governance-loop controls for protected reversal candidates."""

    max_iterations: int = 3
    apply_retry_experiments: bool = True
    use_backtest_metrics_as_oos_proxy: bool = False
    governance_policy: GovernanceFeedbackLoopConfig = field(
        default_factory=GovernanceFeedbackLoopConfig
    )
    whipsaw_bars: int = 5

    def __post_init__(self) -> None:
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        if self.whipsaw_bars < 1:
            raise ValueError("whipsaw_bars must be >= 1")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["governance_policy"] = self.governance_policy.to_dict()
        return payload


@dataclass(frozen=True, slots=True)
class ProtectedReversalGovernanceIteration:
    """One protected-reversal governance-loop iteration."""

    iteration: int
    config: ProtectedReversalConfig
    result: ProtectedReversalWorkflowResult
    attribution: ShortHorizonFailureAttribution
    loss_profit_plan: LossProfitOptimizationPlan
    decision: GovernanceFeedbackLoopDecision
    next_config: ProtectedReversalConfig | None
    mutation_notes_zh: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "iteration": self.iteration,
            "config": self.config.to_dict(),
            "result": self.result.to_dict(),
            "attribution": self.attribution.to_dict(),
            "loss_profit_plan": self.loss_profit_plan.to_dict(),
            "decision": self.decision.to_dict(),
            "next_config": self.next_config.to_dict() if self.next_config else None,
            "mutation_notes_zh": self.mutation_notes_zh,
        }


@dataclass(frozen=True, slots=True)
class ProtectedReversalGovernanceLoopResult:
    """Closed-loop governance artifact for a protected reversal candidate."""

    iterations: list[ProtectedReversalGovernanceIteration]
    final_action: str
    final_rationale_zh: str
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "iterations": [item.to_dict() for item in self.iterations],
            "final_action": self.final_action,
            "final_rationale_zh": self.final_rationale_zh,
            "metadata": self.metadata,
        }


def run_protected_reversal_workflow(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: ProtectedReversalConfig,
) -> ProtectedReversalWorkflowResult:
    """Run a long-only reversal strategy protected by a coarser direction gate.

    Long entries are allowed only when the higher-period filter is bullish.
    The short-horizon side then waits for a negative overextension / exhaustion
    and buys in the higher-period direction.  Bearish higher-period states are
    represented as cash because the project backtester is long/cash.
    """

    close = resample_close_frame(
        rows,
        config=TimingValidationConfig(
            period=config.execution_period,
            min_observations=config.min_observations,
            commission_bps=config.commission_bps,
            stamp_tax_bps=config.stamp_tax_bps,
        ),
    )
    if len(close) < config.min_observations:
        raise ValueError("Not enough observations for protected reversal workflow")
    log_close = pd.Series(np.log(close.to_numpy(dtype=float)), index=close.index)
    higher_gate = _higher_direction_gate(rows, config=config, target_index=close.index)
    raw_reversal, reversal_score = _raw_reversal_signal(
        log_close=log_close,
        config=config,
    )
    governed_reversal = apply_signal_governance(
        raw_reversal,
        min_hold_bars=config.min_hold_bars,
        cooldown_bars=config.cooldown_bars,
        confirmation_bars=config.confirmation_bars,
    )
    composite = _apply_max_hold(
        governed_reversal.reindex(close.index).fillna(0.0)
        * higher_gate.reindex(close.index).fillna(0.0),
        max_hold_bars=config.max_hold_bars,
    )
    raw_returns = log_close.diff().dropna()
    metrics = backtest_long_cash(
        filter_name=f"protected_reversal:{config.reversal_template}",
        raw_returns=raw_returns,
        signal=composite,
        bars_per_year=TimingValidationConfig(
            period=config.execution_period
        ).bars_per_year,
        commission_bps=config.commission_bps,
        stamp_tax_bps=config.stamp_tax_bps,
        signal_rule="higher_direction_protected_short_horizon_reversal",
        signal_rule_zh=(
            "高一级滤波方向为多头时，小周期出现反向乖离/衰竭才允许下一根K线做多；"
            "高一级方向关闭时保持空仓。"
        ),
    )
    diag = _signal_diagnostics(
        close.index,
        higher_gate=higher_gate,
        raw_reversal=raw_reversal,
        composite=composite,
    )
    return ProtectedReversalWorkflowResult(
        template=config.reversal_template,
        period=config.execution_period,
        higher_period=config.higher_period,
        metrics=metrics,
        signal_diagnostics=diag,
        metadata={
            "workflow_role": "protected_short_horizon_reversal_workflow",
            "workflow_role_zh": "大周期方向保护下的小周期反向/乖离择时工作流",
            "config": config.to_dict(),
            "unit_policy": (
                "periodic filters remain the backbone; higher filter provides "
                "direction, short-horizon filter/deviation provides reversal entry"
            ),
            "unit_policy_zh": (
                "周期滤波仍是中轴：大周期滤波提供方向保护，小周期滤波/乖离只负责"
                "在大方向内寻找反向过度延伸后的入场。"
            ),
            "gate_selection_policy": (
                "higher_period is only the carrier; when physical cycle metadata "
                "is supplied, higher_cycle_days_equiv must be a larger physical "
                "cycle than execution_cycle_days_equiv"
            ),
            "gate_selection_policy_zh": (
                "大周期保护不是拍脑袋固定某个K线级别；higher_period 只是承载K线。"
                "若提供物理周期，higher_cycle_days_equiv 必须相对执行周期构成更大"
                "级别的方向保护。"
            ),
            "long_cash_constraint_zh": (
                "当前回测为 long/cash；高一级空头方向不反手做空，只转为空仓。"
            ),
            "no_lookahead_policy": "signals_observed_at_bar_t_execute_at_bar_t_plus_1",
            "field_labels_zh": {
                "higher_gate_on_share": "大周期方向允许交易的时间占比",
                "raw_reversal_on_share": "小周期原始反向信号出现占比",
                "blocked_by_higher_gate_share": "被大周期方向阻断的时间占比",
                "blocked_raw_reversal_share": "原始反向信号中被大周期 gate 阻断的比例",
                "admitted_raw_reversal_share": "原始反向信号中被允许进入交易的比例",
                "composite_on_share": "最终持仓信号占比",
                "entry_count": "最终组合信号入场次数",
                "exit_count": "最终组合信号离场次数",
            },
            "reversal_score_sample": {
                "min": float(reversal_score.min()) if len(reversal_score) else None,
                "max": float(reversal_score.max()) if len(reversal_score) else None,
            },
        },
    )


def run_protected_reversal_governance_loop(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    initial_config: ProtectedReversalConfig,
    loop_config: ProtectedReversalGovernanceLoopConfig | None = None,
    candidate_id: str = "protected_reversal_candidate",
) -> ProtectedReversalGovernanceLoopResult:
    """Run a bounded attribution-driven optimization loop.

    The loop mirrors the trend workflow's review cycle: backtest, attribute
    failure/profit buckets, propose portable governance experiments, and re-run.
    It does not move frequency boundaries, change filter specs, or remove the
    higher-period protection gate.
    """

    loop_cfg = loop_config or ProtectedReversalGovernanceLoopConfig()
    iterations: list[ProtectedReversalGovernanceIteration] = []
    cfg = initial_config
    final_action = "park_or_abandon"
    final_rationale = "治理循环未产生可升级结论。"

    for iteration in range(loop_cfg.max_iterations):
        result = run_protected_reversal_workflow(rows, config=cfg)
        frame = _position_frame(rows, config=cfg)
        bars_per_year = TimingValidationConfig(
            period=cfg.execution_period
        ).bars_per_year
        attribution = analyze_short_horizon_position_frame(
            frame,
            candidate_id=f"{candidate_id}:iter{iteration}",
            period=cfg.execution_period,
            filter_mode=cfg.reversal_template,
            center_period_days=cfg.execution_cycle_days_equiv,
            bars_per_year=bars_per_year,
            buy_cost_bps=cfg.commission_bps,
            sell_cost_bps=cfg.commission_bps + cfg.stamp_tax_bps,
            whipsaw_bars=loop_cfg.whipsaw_bars,
        )
        trades = extract_long_cash_trades(
            frame,
            buy_cost_bps=cfg.commission_bps,
            sell_cost_bps=cfg.commission_bps + cfg.stamp_tax_bps,
            whipsaw_bars=loop_cfg.whipsaw_bars,
        )
        loss_profit_plan = build_loss_profit_optimization_plan(trades)
        oos_cagr = (
            result.metrics.cagr if loop_cfg.use_backtest_metrics_as_oos_proxy else None
        )
        oos_mdd = (
            result.metrics.max_drawdown
            if loop_cfg.use_backtest_metrics_as_oos_proxy
            else None
        )
        decision = decide_governance_feedback_loop(
            attribution,
            oos_cagr=oos_cagr,
            oos_mdd=oos_mdd,
            iteration=iteration,
            config=loop_cfg.governance_policy,
        )
        next_config: ProtectedReversalConfig | None = None
        notes: list[str] = []
        if (
            decision.action == "retry_with_governance_experiments"
            and loop_cfg.apply_retry_experiments
            and iteration + 1 < loop_cfg.max_iterations
        ):
            next_config, notes = _next_governance_config(cfg, attribution)
            if next_config == cfg:
                next_config = None
                notes = ["治理建议未形成可迁移配置变化；停止继续循环，避免空转。"]
        iterations.append(
            ProtectedReversalGovernanceIteration(
                iteration=iteration,
                config=cfg,
                result=result,
                attribution=attribution,
                loss_profit_plan=loss_profit_plan,
                decision=decision,
                next_config=next_config,
                mutation_notes_zh=notes,
            )
        )
        final_action = decision.action
        final_rationale = decision.rationale_zh
        if next_config is None:
            if (
                decision.action == "retry_with_governance_experiments"
                and iteration + 1 >= loop_cfg.max_iterations
            ):
                final_action = "max_iterations_reached_review_required"
                final_rationale = (
                    "本次治理闭环已达到最大迭代次数，" +
                    "最后一轮仍显示存在可迁移治理实验；" +
                    "应由研究员查看治理前后图形和归因后决定继续循环、" +
                    "转执行 overlay 或暂停。"
                )
            break
        cfg = next_config

    return ProtectedReversalGovernanceLoopResult(
        iterations=iterations,
        final_action=final_action,
        final_rationale_zh=final_rationale,
        metadata={
            "workflow_role": "protected_reversal_attribution_governance_loop",
            "workflow_role_zh": "周期保护型反向工作流的归因驱动治理闭环",
            "loop_config": loop_cfg.to_dict(),
            "candidate_id": candidate_id,
            "loop_contract": (
                "backtest -> attribution -> portable governance experiment -> "
                "rerun until promote/park/max_iterations"
            ),
            "loop_contract_zh": (
                "每轮先回测和逐笔归因，再生成可迁移治理实验；用户可以在任一轮停止，"
                "也可以继续循环。循环不得移动频率边界、替换频率证据或取消大周期保护。"
            ),
            "validation_scope": (
                "single-sample loop control; production upgrade still requires "
                "walk-forward or out-of-sample evidence"
            ),
            "validation_scope_zh": (
                "该闭环提供流程控制和治理实验证据；" +
                "升级生产仍需 walk-forward 或样本外验证。"
            ),
        },
    )


def _higher_direction_gate(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: ProtectedReversalConfig,
    target_index: pd.Index,
) -> pd.Series:
    higher_close = resample_close_frame(
        rows,
        config=TimingValidationConfig(
            period=config.higher_period,
            min_observations=max(10, min(config.min_observations, 60)),
        ),
    )
    higher_log = pd.Series(
        np.log(higher_close.to_numpy(dtype=float)), index=higher_close.index
    )
    filtered = apply_filter_spec(
        higher_log,
        cast(FilterSpec, config.higher_filter_spec),
    ).dropna()
    signal = signal_from_filtered(
        filtered,
        output_kind=cast(FilterSpec, config.higher_filter_spec).output_kind,
    )
    governed = apply_signal_governance(signal, confirmation_bars=1)
    return governed.reindex(target_index, method="ffill").fillna(0.0).clip(0.0, 1.0)


def _position_frame(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: ProtectedReversalConfig,
) -> pd.DataFrame:
    close = resample_close_frame(
        rows,
        config=TimingValidationConfig(
            period=config.execution_period,
            min_observations=config.min_observations,
            commission_bps=config.commission_bps,
            stamp_tax_bps=config.stamp_tax_bps,
        ),
    )
    log_close = pd.Series(np.log(close.to_numpy(dtype=float)), index=close.index)
    higher_gate = _higher_direction_gate(rows, config=config, target_index=close.index)
    raw_reversal, _ = _raw_reversal_signal(log_close=log_close, config=config)
    governed_reversal = apply_signal_governance(
        raw_reversal,
        min_hold_bars=config.min_hold_bars,
        cooldown_bars=config.cooldown_bars,
        confirmation_bars=config.confirmation_bars,
    )
    desired = _apply_max_hold(
        governed_reversal.reindex(close.index).fillna(0.0)
        * higher_gate.reindex(close.index).fillna(0.0),
        max_hold_bars=config.max_hold_bars,
    )
    raw_returns = log_close.diff().dropna()
    position = desired.reindex(raw_returns.index).fillna(0.0).shift(1).fillna(0.0)
    aligned_close = close.reindex(raw_returns.index).ffill()
    return pd.DataFrame(
        {
            "timestamp": raw_returns.index.astype(str),
            "close": aligned_close.to_numpy(dtype=float),
            "position": position.to_numpy(dtype=float),
        }
    )


def _next_governance_config(
    config: ProtectedReversalConfig,
    attribution: ShortHorizonFailureAttribution,
) -> tuple[ProtectedReversalConfig, list[str]]:
    notes: list[str] = []
    kwargs: dict[str, object] = {}
    if attribution.root_cause == "microstructure_noise":
        kwargs["cooldown_bars"] = config.cooldown_bars + 2
        kwargs["min_hold_bars"] = config.min_hold_bars + 1
        kwargs["confirmation_bars"] = config.confirmation_bars + 1
        kwargs["entry_z"] = config.entry_z + 0.25
        notes.append("微结构反复亏损：提高确认、冷却、最小持仓和入场极端阈值。")
    elif attribution.root_cause == "cost_amplified_overtrading":
        kwargs["cooldown_bars"] = config.cooldown_bars + 3
        kwargs["entry_z"] = config.entry_z + 0.25
        kwargs["max_hold_bars"] = max(1, int(round(config.max_hold_bars * 0.8)))
        notes.append("成本放大高换手：提高入场阈值、增加冷却，并压缩无效持仓上限。")
    elif attribution.root_cause == "overnight_gap_risk":
        kwargs["max_hold_bars"] = max(1, int(round(config.max_hold_bars * 0.6)))
        kwargs["confirmation_bars"] = config.confirmation_bars + 1
        notes.append(
            "隔夜/开盘风险偏高：先用更短 max_hold 和更强确认做可迁移治理实验。"
        )
    elif attribution.root_cause == "payoff_or_winrate_defect":
        kwargs["entry_z"] = config.entry_z + 0.25
        kwargs["exit_z"] = min(config.entry_z * 0.5, config.exit_z + 0.1)
        kwargs["confirmation_bars"] = config.confirmation_bars + 1
        notes.append("胜率/盈亏比不足：提高入场质量并要求更稳定确认。")
    else:
        notes.append("归因更适合角色转换为执行 overlay，不自动改动反向模板参数。")
    if not kwargs:
        return config, notes
    return replace(config, **kwargs), notes


def _raw_reversal_signal(
    *,
    log_close: pd.Series,
    config: ProtectedReversalConfig,
) -> tuple[pd.Series, pd.Series]:
    if config.reversal_template == "return_zscore_reversal":
        recent = log_close.diff(config.return_lookback_bars)
        scale = log_close.diff().rolling(
            config.z_window_bars, min_periods=max(5, config.z_window_bars // 5)
        ).std().shift(1) * np.sqrt(config.return_lookback_bars)
        score = recent / scale.replace(0.0, np.nan)
        raw = score <= -config.entry_z
        exit_zone = score >= -config.exit_z
        return _state_until_exit(raw, exit_zone), score.fillna(0.0)

    filtered = apply_filter_spec(
        log_close,
        cast(FilterSpec, config.execution_filter_spec),
    ).dropna()
    if config.reversal_template == "lowpass_deviation_reversal":
        deviation = log_close.reindex(filtered.index) - filtered
        scale = (
            deviation.rolling(
                config.z_window_bars,
                min_periods=max(5, config.z_window_bars // 5),
            )
            .std()
            .shift(1)
        )
        score = deviation / scale.replace(0.0, np.nan)
        raw = score <= -config.entry_z
        exit_zone = score >= -config.exit_z
        return _state_until_exit(raw, exit_zone).reindex(log_close.index).fillna(
            0.0
        ), score.fillna(0.0)

    component = filtered
    scale = (
        component.rolling(
            config.z_window_bars,
            min_periods=max(5, config.z_window_bars // 5),
        )
        .std()
        .shift(1)
    )
    score = component / scale.replace(0.0, np.nan)
    slope_turning_up = component.diff() > 0.0
    raw = (score <= -config.entry_z) & slope_turning_up
    exit_zone = score >= -config.exit_z
    return _state_until_exit(raw, exit_zone).reindex(log_close.index).fillna(
        0.0
    ), score.fillna(0.0)


def _state_until_exit(entry: pd.Series, exit_zone: pd.Series) -> pd.Series:
    state: list[float] = []
    current = False
    for enter, exit_now in zip(
        entry.fillna(False).to_numpy(dtype=bool),
        exit_zone.fillna(False).to_numpy(dtype=bool),
        strict=True,
    ):
        if current and exit_now:
            current = False
        if (not current) and enter:
            current = True
        state.append(1.0 if current else 0.0)
    return pd.Series(state, index=entry.index, dtype=float)


def _apply_max_hold(signal: pd.Series, *, max_hold_bars: int) -> pd.Series:
    output: list[float] = []
    hold = 0
    current = False
    for desired in signal.fillna(0.0).to_numpy(dtype=float) > 0.0:
        if not current and desired:
            current = True
            hold = 0
        elif current and (not desired):
            current = False
            hold = 0
        if current and hold >= max_hold_bars:
            current = False
            hold = 0
        output.append(1.0 if current else 0.0)
        if current:
            hold += 1
    return pd.Series(output, index=signal.index, dtype=float)


def _signal_diagnostics(
    index: pd.Index,
    *,
    higher_gate: pd.Series,
    raw_reversal: pd.Series,
    composite: pd.Series,
) -> ProtectedReversalSignals:
    gate = higher_gate.reindex(index).fillna(0.0)
    raw = raw_reversal.reindex(index).fillna(0.0)
    comp = composite.reindex(index).fillna(0.0)
    changes = comp.diff().fillna(comp)
    raw_on = raw > 0.0
    blocked = raw_on & (gate <= 0.0)
    admitted = raw_on & (gate > 0.0)
    raw_count = int(raw_on.sum())
    return ProtectedReversalSignals(
        sample_start=str(index.min()),
        sample_end=str(index.max()),
        sample_count=len(index),
        higher_gate_on_share=float((gate > 0.0).mean()),
        raw_reversal_on_share=float((raw > 0.0).mean()),
        composite_on_share=float((comp > 0.0).mean()),
        blocked_by_higher_gate_share=float(blocked.mean()),
        blocked_raw_reversal_share=(
            float(blocked.sum() / raw_count) if raw_count > 0 else 0.0
        ),
        admitted_raw_reversal_share=(
            float(admitted.sum() / raw_count) if raw_count > 0 else 0.0
        ),
        entry_count=int((changes > 0.0).sum()),
        exit_count=int((changes < 0.0).sum()),
    )
