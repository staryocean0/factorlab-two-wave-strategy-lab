# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportMissingTypeStubs=false
"""Filter timing strategy construction and validation workflow.

This workflow is downstream of parameter generation and filter tool selection.
It builds explicit long/cash strategy templates from governed filter outputs.
The template registry is intentionally incremental: when research validates a
new reusable timing grammar, it is added here as a first-class template instead
of being treated as a one-off baseline.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Literal, cast

import numpy as np
import pandas as pd

from factor_lab.filtering.costs import (
    DEFAULT_COMMISSION_BPS,
    DEFAULT_STAMP_TAX_BPS,
    resolve_long_cash_cost_model,
)
from factor_lab.filtering.scale_hierarchy import (
    DEFAULT_MAX_HIGHER_CYCLE_RATIO,
    DEFAULT_MIN_HIGHER_CYCLE_RATIO,
    DEFAULT_SAME_LEVEL_MAX_RATIO,
    GATE_RATIO_POLICY_ROLE,
    GATE_RATIO_SELECTION_PROTOCOL,
    FilterScaleHierarchyConfig,
    assess_filter_scale_relation,
)
from factor_lab.filtering.strategy_rendering import (
    write_filter_timing_strategy_render_artifacts,
)
from factor_lab.filtering.timing_validation import (
    BacktestMetrics,
    FilterSpec,
    PeriodName,
    TimingValidationConfig,
    apply_filter_spec,
    backtest_long_cash,
    resample_close_frame,
    signal_from_filtered,
    signal_rule_for_output_kind,
)
from factor_lab.filtering.tool_selection import filter_spec_to_dict

ConflictPolicy = Literal["flat_on_conflict", "hold_until_exit_trigger"]
StrategyTemplate = Literal[
    "higher_period_gate_execution_trigger",
    "single_period_component_trigger",
    "single_period_level_slope_trigger",
]
SUPPORTED_STRATEGY_TEMPLATES: tuple[StrategyTemplate, ...] = (
    "higher_period_gate_execution_trigger",
    "single_period_component_trigger",
    "single_period_level_slope_trigger",
)

PERIOD_FINE_TO_COARSE_RANK: dict[str, int] = {
    "1min": 0,
    "5min": 1,
    "15min": 2,
    "30min": 3,
    "60min": 4,
    "day": 5,
    "week": 6,
}


@dataclass(frozen=True, slots=True)
class FilterTimingStrategyConfig:
    """Configuration for one governed filter timing strategy template."""

    higher_period: PeriodName = "day"
    execution_period: PeriodName = "60min"
    higher_filter_spec: FilterSpec | None = None
    execution_filter_spec: FilterSpec | None = None
    strategy_template: StrategyTemplate = "higher_period_gate_execution_trigger"
    conflict_policy: ConflictPolicy = "flat_on_conflict"
    cost_bps: float | None = None
    commission_bps: float = DEFAULT_COMMISSION_BPS
    stamp_tax_bps: float = DEFAULT_STAMP_TAX_BPS
    min_observations: int = 30
    timestamp_column: str = "timestamp"
    close_column: str = "close"
    higher_cycle_days_equiv: float | None = None
    execution_cycle_days_equiv: float | None = None
    same_level_max_ratio: float = DEFAULT_SAME_LEVEL_MAX_RATIO
    min_higher_cycle_ratio: float = DEFAULT_MIN_HIGHER_CYCLE_RATIO
    max_higher_cycle_ratio: float = DEFAULT_MAX_HIGHER_CYCLE_RATIO
    render_output_prefix: str | None = None
    render_price_scale: Literal["linear", "log"] = "linear"
    render_max_bars: int = 1600
    min_hold_bars: int = 0
    cooldown_bars: int = 0
    confirmation_bars: int = 1

    def __post_init__(self) -> None:
        if self.strategy_template not in SUPPORTED_STRATEGY_TEMPLATES:
            raise ValueError("Unsupported strategy_template")
        if self.execution_filter_spec is None:
            raise ValueError("execution_filter_spec is required")
        if self.strategy_template == "higher_period_gate_execution_trigger":
            if PERIOD_FINE_TO_COARSE_RANK[
                self.higher_period
            ] <= PERIOD_FINE_TO_COARSE_RANK[self.execution_period]:
                raise ValueError("higher_period must be coarser than execution_period")
            if self.higher_filter_spec is None:
                raise ValueError("higher_filter_spec is required")
        else:
            if self.higher_filter_spec is not None:
                raise ValueError(
                    "higher_filter_spec must be omitted for single-period templates"
                )
            if self.higher_cycle_days_equiv is not None:
                raise ValueError(
                    "higher_cycle_days_equiv must be omitted for "
                    + "single-period templates"
                )
            if (
                self.strategy_template == "single_period_component_trigger"
                and self.execution_filter_spec.output_kind != "component"
            ):
                raise ValueError(
                    "single_period_component_trigger requires "
                    + "execution_filter_spec.output_kind='component'"
                )
            if (
                self.strategy_template == "single_period_level_slope_trigger"
                and self.execution_filter_spec.output_kind != "level"
            ):
                raise ValueError(
                    "single_period_level_slope_trigger requires "
                    + "execution_filter_spec.output_kind='level'"
                )
        if self.conflict_policy not in {"flat_on_conflict", "hold_until_exit_trigger"}:
            raise ValueError("Unsupported conflict_policy")
        _ = resolve_long_cash_cost_model(
            cost_bps=self.cost_bps,
            commission_bps=self.commission_bps,
            stamp_tax_bps=self.stamp_tax_bps,
        )
        if self.min_observations < 3:
            raise ValueError("min_observations must be >= 3")
        if self.render_price_scale not in {"linear", "log"}:
            raise ValueError("render_price_scale must be 'linear' or 'log'")
        if self.render_max_bars < 50:
            raise ValueError("render_max_bars must be >= 50")
        if self.min_hold_bars < 0:
            raise ValueError("min_hold_bars must be >= 0")
        if self.cooldown_bars < 0:
            raise ValueError("cooldown_bars must be >= 0")
        if self.confirmation_bars < 1:
            raise ValueError("confirmation_bars must be >= 1")
        hierarchy_config = FilterScaleHierarchyConfig(
            same_level_max_ratio=self.same_level_max_ratio,
            min_higher_cycle_ratio=self.min_higher_cycle_ratio,
            max_higher_cycle_ratio=self.max_higher_cycle_ratio,
        )
        if self.strategy_template == "higher_period_gate_execution_trigger":
            if (self.higher_cycle_days_equiv is None) != (
                self.execution_cycle_days_equiv is None
            ):
                raise ValueError(
                    "higher_cycle_days_equiv and execution_cycle_days_equiv must "
                    + "be provided together"
                )
        if self.execution_cycle_days_equiv is not None:
            if self.execution_cycle_days_equiv <= 0.0:
                raise ValueError("execution_cycle_days_equiv must be > 0")
        if self.higher_cycle_days_equiv is not None:
            if self.higher_cycle_days_equiv <= 0.0:
                raise ValueError("higher_cycle_days_equiv must be > 0")
        if (
            self.strategy_template == "higher_period_gate_execution_trigger"
            and self.higher_cycle_days_equiv is not None
            and self.execution_cycle_days_equiv is not None
        ):
            assessment = assess_filter_scale_relation(
                execution_cycle_days=self.execution_cycle_days_equiv,
                candidate_cycle_days=self.higher_cycle_days_equiv,
                config=hierarchy_config,
            )
            if not assessment.usable_as_direction_gate:
                raise ValueError(
                    "higher cycle is not a valid direction gate for execution "
                    + f"cycle: ratio={assessment.ratio:.3g}, "
                    + f"relation={assessment.relation}, required range="
                    + f"{self.min_higher_cycle_ratio:g}-"
                    + f"{self.max_higher_cycle_ratio:g}x"
                )


@dataclass(frozen=True, slots=True)
class FilterTimingStrategySignals:
    """Signal diagnostics for the composite strategy."""

    sample_start: str
    sample_end: str
    sample_count: int
    gate_on_share: float
    trigger_on_share: float
    composite_on_share: float
    conflict_share: float
    entry_count: int
    exit_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FilterTimingStrategyWorkflowResult:
    """Reusable strategy construction and validation artifact."""

    strategy_template: str
    higher_period: str | None
    execution_period: str
    signal_diagnostics: FilterTimingStrategySignals
    composite_backtest: BacktestMetrics
    baseline_backtests: dict[str, dict[str, object]]
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "strategy_template": self.strategy_template,
            "higher_period": self.higher_period,
            "execution_period": self.execution_period,
            "signal_diagnostics": self.signal_diagnostics.to_dict(),
            "composite_backtest": self.composite_backtest.to_dict(),
            "baseline_backtests": self.baseline_backtests,
            "metadata": self.metadata,
        }


def run_filter_timing_strategy_workflow(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: FilterTimingStrategyConfig,
    index_ref: str = "index_series",
) -> FilterTimingStrategyWorkflowResult:
    """Build and validate one governed filter timing strategy template."""

    if config.strategy_template in {
        "single_period_component_trigger",
        "single_period_level_slope_trigger",
    }:
        return _run_single_period_strategy(
            rows,
            config=config,
            index_ref=index_ref,
        )
    return _run_higher_period_gate_strategy(
        rows,
        config=config,
        index_ref=index_ref,
    )


def _run_higher_period_gate_strategy(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: FilterTimingStrategyConfig,
    index_ref: str,
) -> FilterTimingStrategyWorkflowResult:
    """Build and validate a higher-period gate + execution trigger strategy."""

    higher_spec = cast(FilterSpec, config.higher_filter_spec)
    execution_spec = cast(FilterSpec, config.execution_filter_spec)
    cost_model = resolve_long_cash_cost_model(
        cost_bps=config.cost_bps,
        commission_bps=config.commission_bps,
        stamp_tax_bps=config.stamp_tax_bps,
    )
    execution_close = resample_close_frame(
        rows,
        config=TimingValidationConfig(
            period=config.execution_period,
            min_observations=config.min_observations,
            timestamp_column=config.timestamp_column,
            close_column=config.close_column,
            cost_bps=config.cost_bps,
            commission_bps=config.commission_bps,
            stamp_tax_bps=config.stamp_tax_bps,
        ),
    )
    higher_close = resample_close_frame(
        rows,
        config=TimingValidationConfig(
            period=config.higher_period,
            min_observations=3,
            timestamp_column=config.timestamp_column,
            close_column=config.close_column,
            cost_bps=config.cost_bps,
            commission_bps=config.commission_bps,
            stamp_tax_bps=config.stamp_tax_bps,
        ),
    )
    if len(execution_close) < config.min_observations:
        raise ValueError(
            "Not enough execution-period observations for strategy workflow"
        )
    if len(higher_close) < 3:
        raise ValueError("Not enough higher-period observations for strategy workflow")

    execution_log = pd.Series(
        np.log(execution_close.to_numpy(dtype=np.float64)),
        index=execution_close.index,
    )
    higher_log = pd.Series(
        np.log(higher_close.to_numpy(dtype=np.float64)),
        index=higher_close.index,
    )
    raw_returns = execution_log.diff().dropna()

    higher_filtered = apply_filter_spec(higher_log, higher_spec).dropna()
    execution_filtered = apply_filter_spec(execution_log, execution_spec).dropna()
    if len(higher_filtered) < 3 or len(execution_filtered) < 3:
        raise ValueError("Filter specs produced insufficient strategy signals")

    higher_gate = signal_from_filtered(
        higher_filtered,
        output_kind=higher_spec.output_kind,
    )
    available_higher_indicator = higher_filtered.shift(1)
    execution_trigger = signal_from_filtered(
        execution_filtered,
        output_kind=execution_spec.output_kind,
    )
    available_higher_gate = higher_gate.shift(1)
    aligned_gate = cast(
        pd.Series,
        available_higher_gate.reindex(raw_returns.index, method="ffill")
        .fillna(0.0)
        .clip(0.0, 1.0),
    )
    aligned_trigger = (
        execution_trigger.reindex(raw_returns.index).fillna(0.0).clip(0.0, 1.0)
    )
    raw_composite_signal = _composite_signal(
        gate=aligned_gate,
        trigger=aligned_trigger,
        conflict_policy=config.conflict_policy,
    )
    composite_signal = apply_signal_governance(
        raw_composite_signal,
        min_hold_bars=config.min_hold_bars,
        cooldown_bars=config.cooldown_bars,
        confirmation_bars=config.confirmation_bars,
    )
    higher_signal_policy = signal_rule_for_output_kind(higher_spec.output_kind)
    execution_signal_policy = signal_rule_for_output_kind(execution_spec.output_kind)
    composite_signal_rule = (
        f"{config.conflict_policy}: higher_gate AND execution_trigger; "
        f"execution={execution_signal_policy['signal_rule']}; "
        f"governance={_signal_governance_label(config)}"
    )
    composite_signal_rule_zh = (
        f"复合信号采用 {config.conflict_policy}：上一级门禁与本级别触发同时成立才持有；"
        f"本级别触发规则为：{execution_signal_policy['signal_rule_zh']}；"
        f"信号治理：{_signal_governance_label_zh(config)}"
    )
    scale_assessment = _scale_assessment_from_config(config)
    strategy_name = (
        f"{config.higher_period}_{higher_spec.name}__"
        f"{config.execution_period}_{execution_spec.name}__{config.conflict_policy}"
    )
    composite = backtest_long_cash(
        filter_name=strategy_name,
        raw_returns=raw_returns,
        signal=composite_signal,
        bars_per_year=TimingValidationConfig(
            period=config.execution_period,
            cost_bps=config.cost_bps,
            commission_bps=config.commission_bps,
            stamp_tax_bps=config.stamp_tax_bps,
        ).bars_per_year,
        cost_bps=config.cost_bps,
        commission_bps=config.commission_bps,
        stamp_tax_bps=config.stamp_tax_bps,
        signal_rule=composite_signal_rule,
        signal_rule_zh=composite_signal_rule_zh,
    )
    baseline_execution = backtest_long_cash(
        filter_name=f"execution_only_{execution_spec.name}",
        raw_returns=raw_returns,
        signal=aligned_trigger,
        bars_per_year=TimingValidationConfig(period=config.execution_period).bars_per_year,
        cost_bps=config.cost_bps,
        commission_bps=config.commission_bps,
        stamp_tax_bps=config.stamp_tax_bps,
        signal_rule=execution_signal_policy["signal_rule"],
        signal_rule_zh=execution_signal_policy["signal_rule_zh"],
    )
    baseline_gate = backtest_long_cash(
        filter_name=f"higher_gate_only_{higher_spec.name}",
        raw_returns=raw_returns,
        signal=aligned_gate,
        bars_per_year=TimingValidationConfig(period=config.execution_period).bars_per_year,
        cost_bps=config.cost_bps,
        commission_bps=config.commission_bps,
        stamp_tax_bps=config.stamp_tax_bps,
        signal_rule=higher_signal_policy["signal_rule"],
        signal_rule_zh=higher_signal_policy["signal_rule_zh"],
    )
    diagnostics = _signal_diagnostics(
        gate=aligned_gate,
        trigger=aligned_trigger,
        composite=composite_signal,
    )
    render_artifacts = None
    if config.render_output_prefix:
        aligned_higher_indicator = cast(
            pd.Series,
            available_higher_indicator.reindex(
                raw_returns.index,
                method="ffill",
            ),
        )
        render_artifacts = write_filter_timing_strategy_render_artifacts(
            output_prefix=config.render_output_prefix,
            index_ref=index_ref,
            higher_period=config.higher_period,
            execution_period=config.execution_period,
            higher_filter_name=higher_spec.name,
            execution_filter_name=execution_spec.name,
            execution_close=execution_close,
            execution_filtered=execution_filtered,
            higher_filtered_available=aligned_higher_indicator,
            aligned_gate=aligned_gate,
            aligned_trigger=aligned_trigger,
            composite_signal=composite_signal,
            cost_bps=config.cost_bps,
            commission_bps=config.commission_bps,
            stamp_tax_bps=config.stamp_tax_bps,
            price_scale=config.render_price_scale,
            max_chart_bars=config.render_max_bars,
        ).to_dict()
    return FilterTimingStrategyWorkflowResult(
        strategy_template=config.strategy_template,
        higher_period=config.higher_period,
        execution_period=config.execution_period,
        signal_diagnostics=diagnostics,
        composite_backtest=composite,
        baseline_backtests={
            "execution_only": baseline_execution.to_dict(),
            "higher_gate_only": baseline_gate.to_dict(),
        },
        metadata={
            "workflow_role": "filter_timing_strategy_construction_validation_workflow",
            "workflow_version": "strategy_template_registry_v2",
            "index_ref": index_ref,
            "strategy_template_role": (
                "上一级周期负责方向门禁，本周期滤波信号负责买卖触发"
            ),
            "strategy_template_registry": _strategy_template_registry_metadata(),
            "higher_filter_spec": filter_spec_to_dict(higher_spec),
            "execution_filter_spec": filter_spec_to_dict(execution_spec),
            "conflict_policy": config.conflict_policy,
            "cost_model": cost_model.to_dict(),
            "render_artifacts": render_artifacts,
            "render_policy": (
                "optional final backtest visualization includes execution-period "
                "close-to-close K-line, buy/sell execution markers, execution "
                "filter, and no-lookahead shifted higher filter"
            ),
            "scale_hierarchy_assessment": (
                scale_assessment.to_dict() if scale_assessment is not None else None
            ),
            "scale_hierarchy_policy": FilterScaleHierarchyConfig(
                same_level_max_ratio=config.same_level_max_ratio,
                min_higher_cycle_ratio=config.min_higher_cycle_ratio,
                max_higher_cycle_ratio=config.max_higher_cycle_ratio,
            ).to_dict(),
            "gate_ratio_selection_policy": _gate_ratio_selection_policy_metadata(),
            "filter_role_selection_policy": _filter_role_selection_policy_metadata(),
            "parameter_governance": (
                "filter frequency intervals come from opportunity-density; filter "
                "tools come from quality-only selection; strategy parameters may "
                "be optimized only with train/validation/test or walk-forward splits"
            ),
            "lookahead_policy": (
                "higher_period_gate_is_shifted_one_higher_bar_then_forward_filled; "
                "composite_signal_at_execution_bar_t_executes_on_t_plus_1; "
                "signal_governance_uses_only_current_and_past_signal_states"
            ),
            "signal_governance_policy": _signal_governance_policy_metadata(config),
            "signal_generation_policy": {
                "higher_filter": higher_signal_policy,
                "execution_filter": execution_signal_policy,
                "composite_signal_rule": composite_signal_rule,
                "composite_signal_rule_zh": composite_signal_rule_zh,
            },
            "factor_lifecycle_mutation": False,
            "strategy_lifecycle_mutation": False,
        },
    )


def _run_single_period_strategy(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: FilterTimingStrategyConfig,
    index_ref: str,
) -> FilterTimingStrategyWorkflowResult:
    """Build and validate a single-period component or level-slope strategy."""

    execution_spec = cast(FilterSpec, config.execution_filter_spec)
    cost_model = resolve_long_cash_cost_model(
        cost_bps=config.cost_bps,
        commission_bps=config.commission_bps,
        stamp_tax_bps=config.stamp_tax_bps,
    )
    execution_close = resample_close_frame(
        rows,
        config=TimingValidationConfig(
            period=config.execution_period,
            min_observations=config.min_observations,
            timestamp_column=config.timestamp_column,
            close_column=config.close_column,
            cost_bps=config.cost_bps,
            commission_bps=config.commission_bps,
            stamp_tax_bps=config.stamp_tax_bps,
        ),
    )
    if len(execution_close) < config.min_observations:
        raise ValueError(
            "Not enough execution-period observations for strategy workflow"
        )

    execution_log = pd.Series(
        np.log(execution_close.to_numpy(dtype=np.float64)),
        index=execution_close.index,
    )
    raw_returns = execution_log.diff().dropna()
    execution_filtered = apply_filter_spec(execution_log, execution_spec).dropna()
    if len(execution_filtered) < 3:
        raise ValueError("Filter specs produced insufficient strategy signals")

    execution_trigger = signal_from_filtered(
        execution_filtered,
        output_kind=execution_spec.output_kind,
    )
    aligned_trigger = (
        execution_trigger.reindex(raw_returns.index).fillna(0.0).clip(0.0, 1.0)
    )
    governed_trigger = apply_signal_governance(
        aligned_trigger,
        min_hold_bars=config.min_hold_bars,
        cooldown_bars=config.cooldown_bars,
        confirmation_bars=config.confirmation_bars,
    )
    no_higher_gate = pd.Series(1.0, index=raw_returns.index, dtype=float)
    execution_signal_policy = signal_rule_for_output_kind(execution_spec.output_kind)
    template_label = config.strategy_template
    single_signal_rule = (
        f"{template_label}: execution_filter_state; "
        f"execution={execution_signal_policy['signal_rule']}; "
        f"governance={_signal_governance_label(config)}"
    )
    role_zh = (
        "本周期低通水平滤波器以斜率方向承担趋势状态和买卖触发"
        if template_label == "single_period_level_slope_trigger"
        else "本周期滤波分量自己同时承担方向识别和买卖触发"
    )
    single_signal_rule_zh = (
        f"单周期模板：{role_zh}；"
        f"触发规则为：{execution_signal_policy['signal_rule_zh']}；"
        f"信号治理：{_signal_governance_label_zh(config)}"
    )
    strategy_name = (
        f"{config.execution_period}_{execution_spec.name}__"
        f"{template_label}"
    )
    composite = backtest_long_cash(
        filter_name=strategy_name,
        raw_returns=raw_returns,
        signal=governed_trigger,
        bars_per_year=TimingValidationConfig(
            period=config.execution_period,
            cost_bps=config.cost_bps,
            commission_bps=config.commission_bps,
            stamp_tax_bps=config.stamp_tax_bps,
        ).bars_per_year,
        cost_bps=config.cost_bps,
        commission_bps=config.commission_bps,
        stamp_tax_bps=config.stamp_tax_bps,
        signal_rule=single_signal_rule,
        signal_rule_zh=single_signal_rule_zh,
    )
    diagnostics = _signal_diagnostics(
        gate=no_higher_gate,
        trigger=aligned_trigger,
        composite=governed_trigger,
    )
    render_artifacts = None
    if config.render_output_prefix:
        render_artifacts = write_filter_timing_strategy_render_artifacts(
            output_prefix=config.render_output_prefix,
            index_ref=index_ref,
            higher_period=None,
            execution_period=config.execution_period,
            higher_filter_name=None,
            execution_filter_name=execution_spec.name,
            execution_close=execution_close,
            execution_filtered=execution_filtered,
            higher_filtered_available=None,
            aligned_gate=no_higher_gate,
            aligned_trigger=aligned_trigger,
            composite_signal=governed_trigger,
            cost_bps=config.cost_bps,
            commission_bps=config.commission_bps,
            stamp_tax_bps=config.stamp_tax_bps,
            price_scale=config.render_price_scale,
            max_chart_bars=config.render_max_bars,
        ).to_dict()
    return FilterTimingStrategyWorkflowResult(
        strategy_template=config.strategy_template,
        higher_period=None,
        execution_period=config.execution_period,
        signal_diagnostics=diagnostics,
        composite_backtest=composite,
        baseline_backtests={},
        metadata={
            "workflow_role": "filter_timing_strategy_construction_validation_workflow",
            "workflow_version": "strategy_template_registry_v2",
            "index_ref": index_ref,
            "strategy_template_role": role_zh,
            "strategy_template_registry": _strategy_template_registry_metadata(),
            "higher_filter_spec": None,
            "execution_filter_spec": filter_spec_to_dict(execution_spec),
            "execution_cycle_days_equiv": config.execution_cycle_days_equiv,
            "conflict_policy": None,
            "cost_model": cost_model.to_dict(),
            "render_artifacts": render_artifacts,
            "render_policy": (
                "optional final backtest visualization includes execution-period "
                "close-to-close K-line, buy/sell execution markers, and the "
                "execution filter; no higher-period gate is used"
            ),
            "scale_hierarchy_assessment": None,
            "scale_hierarchy_policy": None,
            "gate_ratio_selection_policy": _gate_ratio_selection_policy_metadata(),
            "filter_role_selection_policy": _filter_role_selection_policy_metadata(),
            "parameter_governance": (
                "filter frequency intervals come from frequency-first DII discovery; "
                "filter tools come from quality-only selection; strategy parameters "
                "may be optimized only with train/validation/test or walk-forward "
                "splits"
            ),
            "lookahead_policy": (
                "execution_filter_signal_at_bar_t_executes_on_t_plus_1; "
                "no_higher_period_gate_is_used; "
                "signal_governance_uses_only_current_and_past_signal_states"
            ),
            "signal_governance_policy": _signal_governance_policy_metadata(config),
            "signal_generation_policy": {
                "higher_filter": None,
                "execution_filter": execution_signal_policy,
                "composite_signal_rule": single_signal_rule,
                "composite_signal_rule_zh": single_signal_rule_zh,
            },
            "factor_lifecycle_mutation": False,
            "strategy_lifecycle_mutation": False,
        },
    )



def apply_signal_governance(
    signal: pd.Series,
    *,
    min_hold_bars: int = 0,
    cooldown_bars: int = 0,
    confirmation_bars: int = 1,
) -> pd.Series:
    """Apply causal signal governance before next-bar execution.

    The input is a desired long/cash state observed at bar ``t``.  The returned
    state is still observed at bar ``t`` and must be shifted by the backtester
    before execution.  Confirmation requires the same raw desired state to have
    appeared for ``confirmation_bars`` consecutive bars.  ``min_hold_bars`` and
    ``cooldown_bars`` are counted in already-observed bars, so the state machine
    never reads future values.
    """

    if min_hold_bars < 0:
        raise ValueError("min_hold_bars must be >= 0")
    if cooldown_bars < 0:
        raise ValueError("cooldown_bars must be >= 0")
    if confirmation_bars < 1:
        raise ValueError("confirmation_bars must be >= 1")
    if signal.empty:
        return signal.astype(float)

    desired = signal.fillna(0.0).clip(0.0, 1.0).to_numpy(dtype=np.float64) > 0.0
    governed: list[float] = []
    current = False
    bars_in_state = 10**9
    bars_since_switch = 10**9
    for index, target in enumerate(desired):
        window_start = index + 1 - confirmation_bars
        confirmed = False
        if window_start >= 0:
            window = desired[window_start : index + 1]
            confirmed = bool(np.all(window == target))
        if (
            target != current
            and confirmed
            and bars_in_state >= min_hold_bars
            and bars_since_switch >= cooldown_bars
        ):
            current = bool(target)
            bars_in_state = 0
            bars_since_switch = 0
        governed.append(1.0 if current else 0.0)
        bars_in_state += 1
        bars_since_switch += 1
    return pd.Series(governed, index=signal.index, dtype=float)

def _strategy_template_registry_metadata() -> dict[str, str]:
    return {
        "higher_period_gate_execution_trigger": (
            "双周期候选模板：上一级滤波信号定方向门禁，本周期滤波信号定买卖触发。"
        ),
        "single_period_component_trigger": (
            "单周期候选模板：本周期带通/高通滤波分量的涨跌方向状态同时承担"
            "方向识别和买卖触发。"
        ),
        "single_period_level_slope_trigger": (
            "单周期候选模板：本周期低通水平滤波器以滤波值斜率状态承担"
            "趋势方向识别和买卖触发。"
        ),
    }



def _signal_governance_policy_metadata(
    config: FilterTimingStrategyConfig,
) -> dict[str, object]:
    return {
        "min_hold_bars": config.min_hold_bars,
        "cooldown_bars": config.cooldown_bars,
        "confirmation_bars": config.confirmation_bars,
        "execution_timing": "governed_signal_at_bar_t_executes_on_bar_t_plus_1",
        "causality": "uses only current and past raw signal states",
        "policy_zh": _signal_governance_label_zh(config),
    }


def _signal_governance_label(config: FilterTimingStrategyConfig) -> str:
    return (
        f"confirmation_bars={config.confirmation_bars},"
        f"min_hold_bars={config.min_hold_bars},"
        f"cooldown_bars={config.cooldown_bars}"
    )


def _signal_governance_label_zh(config: FilterTimingStrategyConfig) -> str:
    return (
        f"连续确认 {config.confirmation_bars} 根；"
        f"最短持有 {config.min_hold_bars} 根；"
        f"换向冷却 {config.cooldown_bars} 根；"
        "治理后信号仍在下一根K线执行"
    )

def _gate_ratio_selection_policy_metadata() -> dict[str, object]:
    return {
        "selection_role": GATE_RATIO_POLICY_ROLE,
        "selection_protocol": GATE_RATIO_SELECTION_PROTOCOL,
        "selection_protocol_zh": (
            "3–8 倍只作为结构候选区间，用来判断候选方向门禁是否可能属于"
            "高一级；最终采用几倍必须用 walk-forward 或 train/validation/test "
            "样本外证据，在收益保留、回撤压缩、年度稳定、暴露率和换手之间"
            "做 Pareto 权衡，不能按全样本收益曲线拍脑门。"
        ),
        "primary_tradeoff_metrics": [
            "reward_retention_vs_single",
            "drawdown_compression_vs_single",
            "out_of_sample_cagr",
            "out_of_sample_max_drawdown",
            "annual_excess_stability",
            "turnover_and_exposure",
        ],
    }


def _filter_role_selection_policy_metadata() -> dict[str, object]:
    return {
        "direction_gate_role_zh": (
            "方向门禁滤波器负责判断大环境是否允许做多，目标是开门后提高"
            "本级触发胜率、关门时压缩回撤和噪声交易，同时保留足够收益。"
        ),
        "execution_trigger_role_zh": (
            "买卖点滤波器负责执行周期的具体进出场，目标是低滞后、转向清晰、"
            "分量 BDCI/连续度高、交易成本可承受。"
        ),
        "same_tool_not_required": True,
        "same_tool_not_required_zh": (
            "定方向与定买卖点的职责不同，工具不要求一致；上一级方向工具"
            "必须在自己的周期/频率范围独立选择，不能因为本级 IIR 强就默认"
            "方向门禁也必须用 IIR。"
        ),
        "direction_candidate_families": [
            "ema_baseline_lowpass",
            "laplace_iir_lowpass_or_bandpass",
            "fourier_rolling_lowpass_or_bandpass",
            "wavelet_haar_lowpass_or_bandpass",
            "volatility_normalized_hysteresis_research_candidate",
        ],
        "direction_selection_metrics": [
            "gate_open_share",
            "conflict_share",
            "reward_retention_vs_single",
            "drawdown_compression_vs_single",
            "annual_excess_stability",
            "turnover_and_exposure",
        ],
    }


def _scale_assessment_from_config(config: FilterTimingStrategyConfig):
    if (
        config.higher_cycle_days_equiv is None
        or config.execution_cycle_days_equiv is None
    ):
        return None
    return assess_filter_scale_relation(
        execution_cycle_days=config.execution_cycle_days_equiv,
        candidate_cycle_days=config.higher_cycle_days_equiv,
        config=FilterScaleHierarchyConfig(
            same_level_max_ratio=config.same_level_max_ratio,
            min_higher_cycle_ratio=config.min_higher_cycle_ratio,
            max_higher_cycle_ratio=config.max_higher_cycle_ratio,
        ),
    )


def _composite_signal(
    *,
    gate: pd.Series,
    trigger: pd.Series,
    conflict_policy: ConflictPolicy,
) -> pd.Series:
    gate_bool = gate > 0.0
    trigger_bool = trigger > 0.0
    if conflict_policy == "flat_on_conflict":
        return cast(pd.Series, (gate_bool & trigger_bool).astype(float))
    position: list[float] = []
    current = 0.0
    for gate_on, trigger_on in zip(gate_bool, trigger_bool, strict=True):
        if current <= 0.0:
            current = 1.0 if bool(gate_on and trigger_on) else 0.0
        else:
            current = 0.0 if not bool(trigger_on) else 1.0
        position.append(current)
    return pd.Series(position, index=trigger.index, dtype=float)


def _signal_diagnostics(
    *,
    gate: pd.Series,
    trigger: pd.Series,
    composite: pd.Series,
) -> FilterTimingStrategySignals:
    conflict = cast(pd.Series, (gate > 0.0) & (trigger <= 0.0))
    entries = int(((composite.diff().fillna(composite) > 0.0)).sum())
    exits = int(((composite.diff().fillna(0.0) < 0.0)).sum())
    return FilterTimingStrategySignals(
        sample_start=_series_date_label(composite, boundary="min"),
        sample_end=_series_date_label(composite, boundary="max"),
        sample_count=len(composite),
        gate_on_share=float((gate > 0.0).mean()),
        trigger_on_share=float((trigger > 0.0).mean()),
        composite_on_share=float((composite > 0.0).mean()),
        conflict_share=float(conflict.mean()),
        entry_count=entries,
        exit_count=exits,
    )


def _series_date_label(series: pd.Series, *, boundary: Literal["min", "max"]) -> str:
    raw_value = series.index.min() if boundary == "min" else series.index.max()
    return str(pd.Timestamp(str(raw_value)).date())
