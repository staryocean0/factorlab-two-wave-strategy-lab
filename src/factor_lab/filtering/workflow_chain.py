# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportMissingTypeStubs=false
# pyright: reportUnusedFunction=false
"""End-to-end chain for frequency-first DII, tool, and strategy workflows.

This module is the user-facing orchestration layer for governed filter
workflows.  It deliberately keeps the upstream non-PnL stages separate from the
final strategy backtest while making the handoffs reproducible:

1. time-series characteristic preflight;
2. DII full-spectrum frequency discovery on a canonical physical-frequency axis;
3. positive-frequency ridge clustering and carrier projection;
4. quality-only filter tool selection for each selected carrier target;
5. strategy-template candidate backtests:
   higher-period direction gate + execution-period trigger, and validated
   single-period component/level direction trigger;
6. optional K-line/indicator/trade rendering for the final backtest.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

import pandas as pd

from factor_lab.filtering.costs import (
    DEFAULT_COMMISSION_BPS,
    DEFAULT_STAMP_TAX_BPS,
    resolve_long_cash_cost_model,
)
from factor_lab.filtering.directional_information import (
    DirectionalInformationSurfaceConfig,
    run_directional_information_surface,
)
from factor_lab.filtering.frequency_workflow import (
    DEFAULT_DII_FILTER_MODES,
    DEFAULT_DII_FREQUENCY_GRID_POINTS,
    DEFAULT_DII_HORIZON_FRACTIONS,
    DEFAULT_DII_MAX_BARS_PER_CYCLE,
    DEFAULT_DII_MIN_BARS_PER_CYCLE,
    DEFAULT_DII_POSITIVE_ENTRY_THRESHOLD_BPS,
    DEFAULT_DII_Q_VALUES,
    DiiFrequencyDiscoveryConfig,
    DiiFrequencyWorkflowResult,
    carrier_targets_for_backtest,
    run_dii_full_spectrum_frequency_discovery,
)
from factor_lab.filtering.parameter_workflow import (
    DEFAULT_WORKFLOW_PERIODS,
    PERIOD_BARS_PER_DAY,
    PERIOD_FINE_TO_COARSE_RANK,
    FilterParameterMergedOwnedInterval,
    FilterParameterRecommendation,
    FilterParameterWorkflowResult,
    ParameterEvidenceStrength,
)
from factor_lab.filtering.research_decision import build_filter_research_decision
from factor_lab.filtering.scale_hierarchy import (
    DEFAULT_MAX_HIGHER_CYCLE_RATIO,
    DEFAULT_MIN_HIGHER_CYCLE_RATIO,
    DEFAULT_SAME_LEVEL_MAX_RATIO,
    GATE_RATIO_POLICY_ROLE,
    GATE_RATIO_SELECTION_PROTOCOL,
    FilterScaleHierarchyConfig,
    assess_filter_scale_relation,
)
from factor_lab.filtering.series_characteristics import (
    TimeSeriesCharacteristicConfig,
    run_time_series_characteristics_workflow,
)
from factor_lab.filtering.strategy_rendering import SIGNAL_FIELD_LABELS_ZH
from factor_lab.filtering.strategy_workflow import (
    SUPPORTED_STRATEGY_TEMPLATES,
    FilterTimingStrategyConfig,
    StrategyTemplate,
    run_filter_timing_strategy_workflow,
)
from factor_lab.filtering.timing_validation import (
    BACKTEST_FIELD_LABELS_ZH,
    FilterMode,
    PeriodName,
    signal_rule_for_output_kind,
)
from factor_lab.filtering.tool_selection import (
    FilterToolEvaluation,
    FilterToolSelectionConfig,
    FilterToolSelectionResult,
    filter_spec_from_dict,
    run_filter_tool_selection,
)

ChainStageStatus = Literal["completed", "skipped", "failed"]
PreStrategyTradabilityStatus = Literal[
    "passed",
    "passed_with_execution_risk_note",
    "unknown",
]

SUMMARY_BACKTEST_FIELD_LABELS_ZH: dict[str, str] = {
    "strategy_template": "策略模板",
    "execution_period": "执行K线级别（采样粒度）",
    "higher_period": "上一级门禁K线级别（采样粒度）",
    "execution_filter_name": "本级别滤波器名称",
    "higher_filter_name": "上一级滤波器名称",
    "execution_filter_rank": "本级别工具质量排名",
    "higher_filter_rank": "上一级工具质量排名",
    "execution_cycle_days": "本级别滤波中心交易日等效",
    "higher_cycle_days": "上一级滤波中心交易日等效",
    "cycle_ratio": "上一级/本级别周期倍数",
    "pre_strategy_tradability_status": "策略前可交易性/执行风险提示状态",
    "pre_strategy_tradability_reason_zh": "策略前可交易性/执行风险提示说明",
    "expected_leg_days": "目标滤波周期的理论半周期交易日等效",
    "final_nav": "最终净值",
    "cagr": "年化收益率",
    "sharpe_like": "类夏普比率",
    "max_drawdown": "最大回撤",
    "trade_count": "交易次数",
    "exposure": "平均持仓比例",
    "turnover_per_year": "年化换手次数",
    "reward_retention_vs_single": (
        "收益保留率：双周期年化收益率 / 同执行滤波器单周期年化收益率；"
        "单周期收益率<=0时该比例不可解释，改看收益改善"
    ),
    "cagr_delta_vs_single": "收益改善：双周期年化收益率 - 同执行滤波器单周期年化收益率",
    "drawdown_compression_vs_single": (
        "回撤压缩率：1 - 双周期最大回撤绝对值 / 同执行滤波器单周期最大回撤绝对值"
    ),
    "pareto_frontier": "是否位于同执行滤波器的收益-回撤帕累托前沿",
    "gate_tradeoff_status": "双周期门禁相对单周期的机器可读权衡状态",
    "gate_tradeoff_note_zh": "双周期门禁相对单周期的收益/回撤权衡说明",
    "render_artifacts": "渲染产物路径与字段说明",
}


@dataclass(frozen=True, slots=True)
class _PreStrategyTradabilityPrecheck:
    status: PreStrategyTradabilityStatus
    expected_leg_days: float | None
    reason_zh: str | None


@dataclass(frozen=True, slots=True)
class FilterWorkflowChainConfig:
    """Configuration for the end-to-end filter strategy workflow chain."""

    periods: tuple[PeriodName, ...] = DEFAULT_WORKFLOW_PERIODS
    timestamp_column: str = "timestamp"
    close_column: str = "close"
    parameter_window_years: int = 3
    parameter_step_years: int = 1
    parameter_min_observations: int = 500
    workflow_min_observations: int = 120
    parameter_nperseg: int = 512
    parameter_random_baseline_count: int = 20
    parameter_min_cycle_observations: float = 8.0
    parameter_min_vs_random_median: float = 1.0
    parameter_min_stability_share: float = 0.50
    parameter_min_continuous_peak_window_share: float = 0.50
    parameter_use_period_specific_defaults: bool = True
    max_parameter_recommendations_per_period: int = 2
    tool_top_n: int = 1
    tool_min_quality_score: float = 0.0
    tool_max_acceptable_lag_bars: int = 20
    enable_directional_information_precheck: bool = True
    directional_information_q_values: tuple[float, ...] = (0.707, 1.0, 1.4)
    directional_information_horizon_fractions: tuple[float, ...] = (
        0.125,
        0.25,
        0.5,
    )
    directional_information_center_grid_points: int = 3
    directional_information_top_n_per_target: int = 3
    dii_min_center_days: float | None = None
    dii_max_center_days: float | None = None
    dii_frequency_grid_points: int = DEFAULT_DII_FREQUENCY_GRID_POINTS
    dii_q_values: tuple[float, ...] = DEFAULT_DII_Q_VALUES
    dii_horizon_fractions: tuple[float, ...] = DEFAULT_DII_HORIZON_FRACTIONS
    dii_filter_modes: tuple[FilterMode, ...] = DEFAULT_DII_FILTER_MODES
    dii_min_bars_per_cycle: float = DEFAULT_DII_MIN_BARS_PER_CYCLE
    dii_max_bars_per_cycle: float = DEFAULT_DII_MAX_BARS_PER_CYCLE
    dii_positive_entry_threshold_bps: float = DEFAULT_DII_POSITIVE_ENTRY_THRESHOLD_BPS
    dii_tradable_band_merge_ratio: float = 1.35
    max_strategies_per_execution_period: int = 1
    strategy_templates: tuple[StrategyTemplate, ...] = (
        "higher_period_gate_execution_trigger",
        "single_period_component_trigger",
        "single_period_level_slope_trigger",
    )
    synthesize_missing_higher_targets: bool = True
    synthesized_higher_ratio: float | None = None
    cost_bps: float | None = None
    commission_bps: float = DEFAULT_COMMISSION_BPS
    stamp_tax_bps: float = DEFAULT_STAMP_TAX_BPS
    conflict_policy: Literal[
        "flat_on_conflict",
        "hold_until_exit_trigger",
    ] = "flat_on_conflict"
    same_level_max_ratio: float = DEFAULT_SAME_LEVEL_MAX_RATIO
    min_higher_cycle_ratio: float = DEFAULT_MIN_HIGHER_CYCLE_RATIO
    max_higher_cycle_ratio: float = DEFAULT_MAX_HIGHER_CYCLE_RATIO
    enable_ashare_t1_daily_near_hard_gate: bool = False
    ashare_t1_min_expected_leg_days: float = 1.0
    render_output_dir: str | None = None
    render_price_scale: Literal["linear", "log"] = "log"
    render_max_bars: int = 1600

    def __post_init__(self) -> None:
        if not self.periods:
            raise ValueError("periods must not be empty")
        for period in self.periods:
            if period not in PERIOD_FINE_TO_COARSE_RANK:
                raise ValueError(f"Unsupported period: {period}")
        if self.workflow_min_observations < 30:
            raise ValueError("workflow_min_observations must be >= 30")
        _ = DiiFrequencyDiscoveryConfig(
            allowed_periods=self.periods,
            timestamp_column=self.timestamp_column,
            close_column=self.close_column,
            min_center_days=self.dii_min_center_days,
            max_center_days=self.dii_max_center_days,
            frequency_grid_points=self.dii_frequency_grid_points,
            q_values=self.dii_q_values,
            horizon_fractions=self.dii_horizon_fractions,
            filter_modes=self.dii_filter_modes,
            min_bars_per_cycle=self.dii_min_bars_per_cycle,
            max_bars_per_cycle=self.dii_max_bars_per_cycle,
            positive_entry_threshold_bps=self.dii_positive_entry_threshold_bps,
            min_observations=self.workflow_min_observations,
        )
        if self.tool_top_n <= 0:
            raise ValueError("tool_top_n must be > 0")
        if not 0.0 <= self.tool_min_quality_score <= 1.0:
            raise ValueError("tool_min_quality_score must be in [0, 1]")
        if self.max_strategies_per_execution_period <= 0:
            raise ValueError("max_strategies_per_execution_period must be > 0")
        if not self.directional_information_q_values:
            raise ValueError("directional_information_q_values must not be empty")
        if any(
            value <= 0.0 or not math.isfinite(value)
            for value in self.directional_information_q_values
        ):
            raise ValueError("directional_information_q_values must be finite and > 0")
        if not self.directional_information_horizon_fractions:
            raise ValueError(
                "directional_information_horizon_fractions must not be empty"
            )
        if any(
            value <= 0.0 or not math.isfinite(value)
            for value in self.directional_information_horizon_fractions
        ):
            raise ValueError(
                "directional_information_horizon_fractions must be finite and > 0"
            )
        if self.directional_information_center_grid_points <= 0:
            raise ValueError("directional_information_center_grid_points must be > 0")
        if self.directional_information_top_n_per_target <= 0:
            raise ValueError("directional_information_top_n_per_target must be > 0")
        if not self.strategy_templates:
            raise ValueError("strategy_templates must not be empty")
        for template in self.strategy_templates:
            if template not in SUPPORTED_STRATEGY_TEMPLATES:
                raise ValueError(f"Unsupported strategy_template: {template}")
        _ = resolve_long_cash_cost_model(
            cost_bps=self.cost_bps,
            commission_bps=self.commission_bps,
            stamp_tax_bps=self.stamp_tax_bps,
        )
        _ = FilterScaleHierarchyConfig(
            same_level_max_ratio=self.same_level_max_ratio,
            min_higher_cycle_ratio=self.min_higher_cycle_ratio,
            max_higher_cycle_ratio=self.max_higher_cycle_ratio,
        )
        if self.ashare_t1_min_expected_leg_days <= 0.0:
            raise ValueError("ashare_t1_min_expected_leg_days must be > 0")
        if self.render_price_scale not in {"linear", "log"}:
            raise ValueError("render_price_scale must be 'linear' or 'log'")
        if self.render_max_bars < 50:
            raise ValueError("render_max_bars must be >= 50")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FilterWorkflowChainToolTarget:
    """One parameter recommendation handed to tool selection."""

    period: str
    recommendation_rank: int
    target_period_lo_bars: float
    target_period_hi_bars: float
    target_center_days: float | None
    filter_mode: FilterMode
    recommendation_score: float
    median_vs_random: float
    continuous_peak_window_share: float
    parameter_evidence_strength: ParameterEvidenceStrength
    parameter_evidence_strength_label_zh: str
    expected_leg_days: float | None
    pre_strategy_tradability_status: PreStrategyTradabilityStatus
    pre_strategy_tradability_reason_zh: str | None
    target_source: str = "parameter_recommendation"
    source_execution_period: str | None = None
    frequency_candidate_id: str | None = None
    candidate_evidence_label: str | None = None
    center_frequency_cycles_per_day: float | None = None
    dii_bps: float | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FilterWorkflowChainToolResult:
    """Tool-selection result for one period target."""

    target: FilterWorkflowChainToolTarget
    status: ChainStageStatus
    selected_filter: dict[str, object] | None
    selected_tool_quality_score: float | None
    tool_selection: dict[str, object] | None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "target": self.target.to_dict(),
            "status": self.status,
            "selected_filter": self.selected_filter,
            "selected_tool_quality_score": self.selected_tool_quality_score,
            "tool_selection": self.tool_selection,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class FilterWorkflowChainStrategyResult:
    """Final strategy backtest result for one higher/execution pair."""

    strategy_template: str
    execution_period: str
    higher_period: str | None
    execution_filter_name: str
    higher_filter_name: str | None
    execution_filter_rank: int
    higher_filter_rank: int | None
    execution_cycle_days: float
    higher_cycle_days: float | None
    ratio: float | None
    status: ChainStageStatus
    strategy: dict[str, object] | None
    composite_backtest: dict[str, object] | None
    render_artifacts: dict[str, object] | None
    error: str | None = None
    frequency_candidate_id: str | None = None
    candidate_evidence_label: str | None = None
    center_frequency_cycles_per_day: float | None = None
    dii_bps: float | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FilterWorkflowChainResult:
    """Reusable artifact for the chained workflow."""

    index_ref: str
    series_characteristics: dict[str, object]
    parameter_workflow: dict[str, object]
    frequency_discovery: dict[str, object]
    tool_results: list[FilterWorkflowChainToolResult]
    directional_information_results: list[dict[str, object]]
    strategy_results: list[FilterWorkflowChainStrategyResult]
    summary_backtests: list[dict[str, object]]
    research_decision: dict[str, object]
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "index_ref": self.index_ref,
            "series_characteristics": self.series_characteristics,
            "parameter_workflow": self.parameter_workflow,
            "frequency_discovery": self.frequency_discovery,
            "frequency_candidates": self.frequency_discovery.get(
                "frequency_candidates",
                [],
            ),
            "carrier_candidates": self.frequency_discovery.get(
                "carrier_candidates",
                [],
            ),
            "tool_results": [item.to_dict() for item in self.tool_results],
            "directional_information_results": self.directional_information_results,
            "strategy_results": [item.to_dict() for item in self.strategy_results],
            "summary_backtests": self.summary_backtests,
            "research_decision": self.research_decision,
            "metadata": self.metadata,
        }


def run_filter_workflow_chain(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: FilterWorkflowChainConfig | None = None,
    index_ref: str = "index_series",
) -> FilterWorkflowChainResult:
    """Run frequency discovery -> tool -> strategy -> render as one governed chain."""

    cfg = config or FilterWorkflowChainConfig()
    cost_model = resolve_long_cash_cost_model(
        cost_bps=cfg.cost_bps,
        commission_bps=cfg.commission_bps,
        stamp_tax_bps=cfg.stamp_tax_bps,
    )
    characteristics = run_time_series_characteristics_workflow(
        rows,
        index_ref=index_ref,
        config=TimeSeriesCharacteristicConfig(
            periods=cfg.periods,
            timestamp_column=cfg.timestamp_column,
            close_column=cfg.close_column,
            min_observations=max(80, cfg.workflow_min_observations),
        ),
    )
    frequency = run_dii_full_spectrum_frequency_discovery(
        rows,
        index_ref=index_ref,
        config=DiiFrequencyDiscoveryConfig(
            allowed_periods=cfg.periods,
            timestamp_column=cfg.timestamp_column,
            close_column=cfg.close_column,
            min_center_days=cfg.dii_min_center_days,
            max_center_days=cfg.dii_max_center_days,
            frequency_grid_points=cfg.dii_frequency_grid_points,
            q_values=cfg.dii_q_values,
            horizon_fractions=cfg.dii_horizon_fractions,
            filter_modes=cfg.dii_filter_modes,
            min_bars_per_cycle=cfg.dii_min_bars_per_cycle,
            max_bars_per_cycle=cfg.dii_max_bars_per_cycle,
            positive_entry_threshold_bps=cfg.dii_positive_entry_threshold_bps,
            tradable_band_merge_ratio=cfg.dii_tradable_band_merge_ratio,
            min_observations=cfg.workflow_min_observations,
        ),
    )
    targets = _tool_targets_from_frequency(frequency, config=cfg)
    tool_results = [
        _run_tool_selection_for_target(
            rows,
            target=target,
            config=cfg,
            index_ref=index_ref,
        )
        for target in targets
    ]
    if cfg.synthesize_missing_higher_targets:
        synthetic_targets = _synthesized_higher_targets(tool_results, cfg)
        for target in synthetic_targets:
            tool_results.append(
                _run_tool_selection_for_target(
                    rows,
                    target=target,
                    config=cfg,
                    index_ref=index_ref,
                )
            )
    directional_information_results = [
        item.to_dict() for item in frequency.frequency_surfaces
    ]
    strategy_results = _run_chain_strategies(
        rows,
        tool_results=tool_results,
        config=cfg,
        index_ref=index_ref,
    )
    characteristics_payload = characteristics.to_dict()
    frequency_payload = frequency.to_dict()
    parameter_payload: dict[str, object] = {
        "status": "skipped",
        "metadata": {
            "workflow_role": "filter_parameter_workflow",
            "deprecated_parameter_stage_ignored": True,
            "skip_reason": (
                "workflow-chain is frequency-first: DII full-spectrum discovery "
                "replaces parameter-workflow as the main routing source"
            ),
        },
    }
    summary_backtests = _summary_backtests(strategy_results)
    tool_payloads = [item.to_dict() for item in tool_results]
    return FilterWorkflowChainResult(
        index_ref=index_ref,
        series_characteristics=characteristics_payload,
        parameter_workflow=parameter_payload,
        frequency_discovery=frequency_payload,
        tool_results=tool_results,
        directional_information_results=directional_information_results,
        strategy_results=strategy_results,
        summary_backtests=summary_backtests,
        research_decision=build_filter_research_decision(
            index_ref=index_ref,
            series_characteristics=characteristics_payload,
            frequency_discovery=frequency_payload,
            tool_results=tool_payloads,
            summary_backtests=summary_backtests,
        ).to_dict(),
        metadata={
            "workflow_role": "filter_strategy_workflow_chain",
            "workflow_version": (
                "characteristics_dii_frequency_tool_strategy_render_decision_v7"
            ),
            "index_ref": index_ref,
            "chain_order": [
                "time_series_characteristics_workflow",
                "dii_full_spectrum_frequency_discovery",
                "dii_positive_frequency_ridge_clustering",
                "tradable_frequency_band_consolidation",
                "carrier_projection_and_selection",
                "filter_tool_selection_workflow",
                "pre_strategy_execution_risk_annotation",
                "filter_timing_strategy_template_candidate_backtests",
                "filter_timing_strategy_render_artifacts",
                "short_horizon_failure_attribution",
                "attribution_driven_governance_feedback_loop",
                "filter_timing_research_decision_synthesis",
            ],
            "periods_requested": list(cfg.periods),
            "allowed_carriers": list(cfg.periods),
            "deprecated_parameter_stage_ignored": True,
            "deprecated_parameter_stage_ignored_zh": (
                "workflow-chain 中 --parameter-* 仅为兼容旧脚本而解析，"
                "不再影响主链路频率发现、工具选择或回测。"
            ),
            "frequency_candidate_count": len(frequency.frequency_candidates),
            "carrier_candidate_count": len(frequency.carrier_candidates),
            "frequency_candidate_semantics": {
                "dii_points_are": "frequency_axis_samples_not_final_factors",
                "ridge_representatives_are": "evidence_points_before_consolidation",
                "downstream_candidates_are": "tradable_frequency_bands",
                "same_mode_adjacent_ridges_are_merged_before_tool_selection": True,
                "bandpass_lowpass_same_neighborhood_are": (
                    "related_frequency_family_alternative_filter_semantics_not_one_filter"
                ),
                "final_reporting_contract": (
                    "one_lowpass_trend_anchor_plus_non_overlapping_faster_bandpass_layers"
                ),
                "final_reporting_contract_zh": (
                    "最终生产叙事不输出一堆互相冲突的机会频段；理想形态是"
                    "一个最低频低通趋势锚，加多个更快且尽量不重叠的带通层。"
                ),
                "combination_presentation_contract": (
                    "state_distribution_chart_plus_cagr_mdd_turnover_tradeoff_chart"
                ),
                "combination_presentation_contract_zh": (
                    "带通合并/不合并的结论必须配套直观展示：带通状态分布图"
                    "说明是否同一个交易开关，CAGR/MDD/换手权衡图说明组合代价。"
                ),
                "short_horizon_sample_policy": (
                    "extend_same_carrier_history_before_rejecting_for_short_sample"
                ),
                "short_horizon_sample_policy_zh": (
                    "短周期候选不能仅因初始样本短被删除；"
                    "应先拉长同载体历史样本重跑 walk-forward，"
                    "再按收益、回撤、换手、成本/滑点稳定性降级或保留。"
                ),
                "short_horizon_failure_attribution_contract": (
                    "after_rendering_before_final_governance_threshold_changes"
                ),
                "short_horizon_failure_attribution_contract_zh": (
                    "1min/5min 等短周期候选在被删除、降级或调治理算子前，必须先输出"
                    "交易图和逐笔归因：胜率、盈亏比、短持仓反复亏损、隔夜跳空亏损、"
                    "成本前后差异和可迁移优化假设。"
                ),
                "governance_feedback_loop_contract": (
                    "post_wf_governance_then_backtest_render_attribution_then_retry_until_promote_or_abandon"
                ),
                "governance_feedback_loop_contract_zh": (
                    "治理优化不是一次性步骤：初始治理后若仍失败，必须用失败归因生成"
                    "可迁移治理实验，重跑 walk-forward 和图形归因；循环直到升级为"
                    "执行 overlay/生产候选，或触达最大迭代、收益回撤/胜率盈亏比/换手"
                    "停止条件后明确暂停或放弃。"
                ),
                "short_horizon_standard_experiments": [
                    "higher_timeframe_direction_gate",
                    "session_risk_governance_no_overnight_open_wait_late_no_new_entry",
                    "deadband_or_slope_threshold",
                    "cooldown_and_min_hold",
                    "role_conversion_test_to_execution_overlay",
                ],
                "short_horizon_standard_experiments_zh": (
                    "短周期失败归因后的标准实验包括：高一级方向门禁、交易时段/隔夜治理"
                    "（不隔夜、开盘等待、尾盘不新开仓）、零轴/斜率阈值、冷却/最小持仓，"
                    "以及独立仓位层失败后的执行 overlay 角色转换测试。"
                ),
                "loss_profit_bucket_optimization_contract": (
                    "attribute_largest_loss_buckets_then_suppress_without_destroying_top_profit_buckets"
                ),
                "loss_profit_bucket_optimization_contract_zh": (
                    "短周期治理闭环必须先按逐笔交易拆亏损桶和盈利桶：优先压缩贡献最大的"
                    "1-3个亏损归因桶，同时报告主要盈利桶保留率；若治理规则压掉主要盈利桶，"
                    "不得仅因回撤改善而升级。"
                ),
                "discriminative_loss_profit_filtering_contract": (
                    "find_features_that_separate_loss_cases_from_profit_cases_within_the_same_bucket"
                ),
                "discriminative_loss_profit_filtering_contract_zh": (
                    "治理不能按亏损现象一刀切；若同一现象同时贡献亏损和盈利，例如隔夜亏损"
                    "与隔夜盈利并存，必须寻找能区分两者的上下文特征（高一级方向、趋势质量、"
                    "滤波能量、波动状态等），优先测试判别式过滤，而不是直接删除整个现象。"
                ),
                "protected_reversal_branch_contract": (
                    "short_horizon_reversal_requires_higher_period_direction_protection"
                ),
                "protected_reversal_branch_contract_zh": (
                    "短周期反向/乖离策略是独立分支，但仍以周期滤波为中轴：大周期滤波"
                    "必须先给出方向保护，1min/5min 只在大方向内等待小周期反向过度延伸"
                    "后顺大方向入场；禁止无保护地逆高一级趋势抄底摸顶。"
                ),
                "governance_feedback_loop_default_max_iterations": 3,
            },
            "tool_target_count": len(targets),
            "synthetic_higher_target_count": len(
                [
                    item
                    for item in tool_results
                    if item.target.target_source == "ratio_synthesized_direction_probe"
                ]
            ),
            "tool_selected_count": len(
                [item for item in tool_results if item.status == "completed"]
            ),
            "directional_information_enabled": True,
            "directional_information_completed_count": len(
                [
                    item
                    for item in directional_information_results
                    if item.get("status") == "completed"
                ]
            ),
            "strategy_count": len(strategy_results),
            "strategy_completed_count": len(
                [item for item in strategy_results if item.status == "completed"]
            ),
            "strategy_skipped_count": len(
                [item for item in strategy_results if item.status == "skipped"]
            ),
            "strategy_templates": list(cfg.strategy_templates),
            "render_enabled": cfg.render_output_dir is not None,
            "scale_hierarchy_policy": FilterScaleHierarchyConfig(
                same_level_max_ratio=cfg.same_level_max_ratio,
                min_higher_cycle_ratio=cfg.min_higher_cycle_ratio,
                max_higher_cycle_ratio=cfg.max_higher_cycle_ratio,
            ).to_dict(),
            "gate_ratio_selection_policy": {
                "selection_role": GATE_RATIO_POLICY_ROLE,
                "selection_protocol": GATE_RATIO_SELECTION_PROTOCOL,
                "selection_protocol_zh": (
                    "周期倍数窗口只负责把结构上可能合格的上一级方向门禁放入"
                    "候选集；最终采用几倍必须在策略阶段用 walk-forward 或 "
                    "train/validation/test 样本外结果比较，按收益保留率、"
                    "回撤压缩率、年度超额稳定性、暴露率和换手做 Pareto 权衡。"
                ),
                "default_candidate_window": {
                    "min_higher_cycle_ratio": cfg.min_higher_cycle_ratio,
                    "max_higher_cycle_ratio": cfg.max_higher_cycle_ratio,
                    "geometric_probe_ratio": cfg.synthesized_higher_ratio
                    or math.sqrt(
                        cfg.min_higher_cycle_ratio * cfg.max_higher_cycle_ratio
                    ),
                },
                "summary_tradeoff_fields": [
                    "reward_retention_vs_single",
                    "cagr_delta_vs_single",
                    "drawdown_compression_vs_single",
                    "pareto_frontier",
                    "gate_tradeoff_status",
                ],
                "retention_ratio_caveat": (
                    "when the single-period CAGR is <= 0, reward_retention_vs_single "
                    "is not economically meaningful; use cagr_delta_vs_single and "
                    "drawdown_compression_vs_single instead"
                ),
            },
            "filter_role_selection_policy": {
                "direction_gate_role_zh": (
                    "方向门禁负责判断大环境是否允许做多，优先看回撤压缩、"
                    "噪声交易过滤、年度超额稳定和收益保留。"
                ),
                "execution_trigger_role_zh": (
                    "买卖点触发负责执行周期进出场，优先看低滞后、转向清晰、"
                    "分量 BDCI/连续度和成本后交易质量。"
                ),
                "same_tool_not_required": True,
                "same_tool_not_required_zh": (
                    "方向门禁和买卖点触发不要求使用同一种滤波工具；每个角色"
                    "必须按自己的周期、频率范围和目标函数独立选择。"
                ),
                "direction_candidate_families": [
                    "ema_baseline_lowpass",
                    "laplace_iir_lowpass_or_bandpass",
                    "fourier_rolling_lowpass_or_bandpass",
                    "wavelet_haar_lowpass_or_bandpass",
                    "volatility_normalized_hysteresis_research_candidate",
                ],
            },
            "cost_model": cost_model.to_dict(),
            "governance_boundary": (
                "DII frequency discovery and tool-selection stages do not use "
                "strategy PnL; only the final strategy stage reads backtest returns"
            ),
            "directional_information_policy": {
                "role": (
                    "main pre-backtest full-spectrum frequency discovery stage; "
                    "it checks whether causal filter direction aligns with future "
                    "returns before any strategy PnL is read"
                ),
                "formula": (
                    "DII(T,Q,phi)=E[sign(delta filtered_t) * "
                    "(logP_{t+round(phi*T/delta)}-logP_t)]"
                ),
                "unit_policy_zh": (
                    "DII 频率曲面的规范轴是物理频率/交易日等价周期 T；K线根数 P "
                    "只是给定采样粒度 delta 下的实现坐标，P=T/delta。"
                ),
                "surface_requirement_zh": (
                    "必须观察频率/物理周期曲面是否形成宽厚正山脊；孤立高点"
                    "只能视为过拟合风险较高的薄弱边际，不能直接升级为强候选。"
                ),
                "not_a_backtest_zh": (
                    "DII 不计算仓位、交易成本、净值、回撤或换手，只是策略前"
                    "时间序列方向信息体检。"
                ),
            },
            "strategy_tool_variant_policy": (
                "tool_top_n controls how many quality-selected filters per "
                "target are retained for the final strategy-stage battle; "
                "selected_filter remains the top quality-only filter for "
                "readable handoff, but summary_backtests includes the exact "
                "execution_filter_name and higher_filter_name used"
            ),
            "strategy_template_policy": (
                "strategy templates are collected incrementally: the chain may "
                "run the dual-cycle higher-period direction gate template and "
                "single-period bandpass component / lowpass level-slope templates "
                "as parallel first-class candidates; controls stay controls and do "
                "not become the only narrative"
            ),
            "period_semantics_policy": {
                "period_field_meaning": "allowed_bar_carrier_not_filter_cycle_owner",
                "period_field_meaning_zh": (
                    "1min/5min/60min/day/week 只表示AI被允许使用的K线采样/"
                    "执行载体，不再表示固定频段归属。"
                ),
                "target_cycle_field": "target_center_days / execution_cycle_days",
                "target_cycle_field_zh": (
                    "滤波目标周期使用交易日等效字段表达；同一 T_days 会按"
                    " bars_per_trading_day(period) 换算为不同 K线根数。"
                ),
            },
            "pre_strategy_tradability_gate_policy": {
                "enabled": False,
                "hard_gate": None,
                "legacy_flag_ignored": True,
                "min_expected_leg_days": cfg.ashare_t1_min_expected_leg_days,
                "expected_leg_days_formula": "target_center_days / 2",
                "effect_zh": (
                    "A股T+1/日内约束不再作为策略前硬门禁；若目标滤波周期"
                    "理论半周期小于或等于1个交易日，只写入执行风险提示，"
                    "仍进入工具选择、单周期/双周期回测和后续walk-forward筛选。"
                ),
            },
            "filter_design_interval_policy": (
                "tool-selection targets come from physical DII ridge clusters "
                "projected onto allowed bar carriers; period is carrier permission, "
                "not fixed frequency ownership"
            ),
            "parameter_evidence_strength_policy": (
                "tool target carries weak_candidate/candidate/strong_candidate "
                "DII-ridge strength; all positive representatives enter backtests, "
                "but weak/thin candidates must not be narrated as strong candidates"
            ),
            "days_equiv_policy": {
                "meaning": "trading_day_equivalent_not_24h_clock_day",
                "bars_per_day": dict(PERIOD_BARS_PER_DAY),
            },
            "signal_generation_policy": {
                "component": signal_rule_for_output_kind("component"),
                "level": signal_rule_for_output_kind("level"),
                "bdci_gate_reasoning_zh": (
                    "合格的带通滤波分量应具备高 BDCI/高连续度，表示分量自身"
                    "涨跌方向少切换、能承载行情状态；因此策略阶段以滤波"
                    "分量K线由跌转涨/由涨转跌作为买卖状态切换，并在下一根"
                    "K线执行。"
                ),
            },
            "field_labels_zh": {
                "summary_backtests": dict(SUMMARY_BACKTEST_FIELD_LABELS_ZH),
                "backtest_metrics": dict(BACKTEST_FIELD_LABELS_ZH),
                "signals_csv": dict(SIGNAL_FIELD_LABELS_ZH),
            },
            "factor_lifecycle_mutation": False,
            "strategy_lifecycle_mutation": False,
        },
    )


def _tool_targets_from_parameter(
    parameter: FilterParameterWorkflowResult,
    *,
    config: FilterWorkflowChainConfig,
) -> list[FilterWorkflowChainToolTarget]:
    if parameter.merged_owned_intervals:
        return [
            _target_from_merged_owned_interval(interval, rank=index, config=config)
            for index, interval in enumerate(parameter.merged_owned_intervals, start=1)
        ]
    targets: list[FilterWorkflowChainToolTarget] = []
    for period_result in parameter.periods:
        if period_result.status != "completed":
            continue
        for recommendation in period_result.recommendations:
            targets.append(_target_from_recommendation(recommendation, config=config))
    return targets


def _tool_targets_from_frequency(
    frequency: DiiFrequencyWorkflowResult,
    *,
    config: FilterWorkflowChainConfig,
) -> list[FilterWorkflowChainToolTarget]:
    targets: list[FilterWorkflowChainToolTarget] = []
    seen: set[tuple[str, str, str]] = set()
    for rank, carrier in enumerate(carrier_targets_for_backtest(frequency), start=1):
        key = (carrier.candidate_id, carrier.period, carrier.filter_mode)
        if key in seen:
            continue
        seen.add(key)
        precheck = _pre_strategy_tradability_precheck(
            period=carrier.period,
            target_center_days=carrier.target_center_days,
            config=config,
        )
        targets.append(
            FilterWorkflowChainToolTarget(
                period=carrier.period,
                recommendation_rank=rank,
                target_period_lo_bars=carrier.target_period_lo_bars,
                target_period_hi_bars=carrier.target_period_hi_bars,
                target_center_days=carrier.target_center_days,
                filter_mode=cast(FilterMode, carrier.filter_mode),
                recommendation_score=carrier.best_dii_bps,
                median_vs_random=max(
                    0.0,
                    min(3.0, 1.0 + carrier.best_dii_bps / 100.0),
                ),
                continuous_peak_window_share=carrier.hit_rate,
                parameter_evidence_strength=carrier.parameter_evidence_strength,
                parameter_evidence_strength_label_zh=(
                    carrier.parameter_evidence_strength_label_zh
                ),
                expected_leg_days=precheck.expected_leg_days,
                pre_strategy_tradability_status=precheck.status,
                pre_strategy_tradability_reason_zh=precheck.reason_zh,
                target_source="dii_positive_frequency_ridge",
                source_execution_period=None,
                frequency_candidate_id=carrier.candidate_id,
                candidate_evidence_label=carrier.candidate_evidence_label,
                center_frequency_cycles_per_day=(
                    carrier.center_frequency_cycles_per_day
                ),
                dii_bps=carrier.best_dii_bps,
            )
        )
    return targets


def _run_directional_information_prechecks(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    tool_results: Sequence[FilterWorkflowChainToolResult],
    config: FilterWorkflowChainConfig,
    index_ref: str,
) -> list[dict[str, object]]:
    if not config.enable_directional_information_precheck:
        return []
    payloads: list[dict[str, object]] = []
    for tool_result in tool_results:
        target = tool_result.target
        if tool_result.status != "completed":
            payloads.append(
                {
                    "target": target.to_dict(),
                    "status": "skipped",
                    "skip_reason": "tool_selection_not_completed",
                }
            )
            continue
        try:
            surface = run_directional_information_surface(
                rows,
                index_ref=index_ref,
                config=DirectionalInformationSurfaceConfig(
                    period=cast(PeriodName, target.period),
                    timestamp_column=config.timestamp_column,
                    close_column=config.close_column,
                    min_observations=max(
                        60,
                        config.workflow_min_observations,
                    ),
                    filter_mode=target.filter_mode,
                    center_period_bars=_directional_information_center_grid(
                        target,
                        points=config.directional_information_center_grid_points,
                    ),
                    q_values=config.directional_information_q_values,
                    horizon_fractions=(
                        config.directional_information_horizon_fractions
                    ),
                    top_n=config.directional_information_top_n_per_target,
                ),
            )
            payloads.append(
                {
                    "target": target.to_dict(),
                    "status": "completed",
                    "surface": surface.to_dict(),
                    "selected": [
                        item.to_dict()
                        for item in surface.selected[
                            : config.directional_information_top_n_per_target
                        ]
                    ],
                }
            )
        except Exception as exc:
            payloads.append(
                {
                    "target": target.to_dict(),
                    "status": "failed",
                    "error": str(exc),
                }
            )
    return payloads


def _directional_information_center_grid(
    target: FilterWorkflowChainToolTarget,
    *,
    points: int,
) -> tuple[float, ...]:
    lo = max(3.0, float(target.target_period_lo_bars))
    hi = max(lo, float(target.target_period_hi_bars))
    if points == 1 or math.isclose(lo, hi):
        return (math.sqrt(lo * hi),)
    values = [
        math.exp(value)
        for value in list(
            pd.Series(
                [
                    math.log(lo) + (math.log(hi) - math.log(lo)) * index / (points - 1)
                    for index in range(points)
                ]
            )
            .round(6)
            .unique()
        )
    ]
    return tuple(float(value) for value in values)


def _target_from_merged_owned_interval(
    interval: FilterParameterMergedOwnedInterval,
    *,
    rank: int,
    config: FilterWorkflowChainConfig,
) -> FilterWorkflowChainToolTarget:
    precheck = _pre_strategy_tradability_precheck(
        period=interval.assigned_period,
        target_center_days=interval.center_period_days,
        config=config,
    )
    return FilterWorkflowChainToolTarget(
        period=interval.assigned_period,
        recommendation_rank=rank,
        target_period_lo_bars=interval.assigned_period_lo_bars,
        target_period_hi_bars=interval.assigned_period_hi_bars,
        target_center_days=interval.center_period_days,
        filter_mode=_coerce_filter_mode(interval.filter_mode),
        recommendation_score=interval.median_vs_random_max,
        median_vs_random=interval.median_vs_random_max,
        continuous_peak_window_share=interval.continuous_peak_window_share_max,
        parameter_evidence_strength=interval.evidence_strength,
        parameter_evidence_strength_label_zh=interval.evidence_strength_label_zh,
        expected_leg_days=precheck.expected_leg_days,
        pre_strategy_tradability_status=precheck.status,
        pre_strategy_tradability_reason_zh=precheck.reason_zh,
        target_source="merged_owned_responsibility_interval",
    )


def _target_from_recommendation(
    recommendation: FilterParameterRecommendation,
    *,
    config: FilterWorkflowChainConfig,
) -> FilterWorkflowChainToolTarget:
    precheck = _pre_strategy_tradability_precheck(
        period=recommendation.period,
        target_center_days=recommendation.center_period_days_equiv,
        config=config,
    )
    return FilterWorkflowChainToolTarget(
        period=recommendation.period,
        recommendation_rank=recommendation.rank,
        target_period_lo_bars=recommendation.retained_period_lo_bars,
        target_period_hi_bars=recommendation.retained_period_hi_bars,
        target_center_days=recommendation.center_period_days_equiv,
        filter_mode=_coerce_filter_mode(recommendation.filter_mode),
        recommendation_score=recommendation.recommendation_score,
        median_vs_random=recommendation.median_vs_random,
        continuous_peak_window_share=recommendation.continuous_peak_window_share,
        parameter_evidence_strength=recommendation.evidence_strength,
        parameter_evidence_strength_label_zh=recommendation.evidence_strength_label_zh,
        expected_leg_days=precheck.expected_leg_days,
        pre_strategy_tradability_status=precheck.status,
        pre_strategy_tradability_reason_zh=precheck.reason_zh,
    )


def _pre_strategy_tradability_precheck(
    *,
    period: str,
    target_center_days: float | None,
    config: FilterWorkflowChainConfig,
) -> _PreStrategyTradabilityPrecheck:
    if target_center_days is None or target_center_days <= 0.0:
        return _PreStrategyTradabilityPrecheck(
            status="unknown",
            expected_leg_days=None,
            reason_zh="目标滤波周期缺失，无法计算策略前执行风险提示。",
        )
    expected_leg_days = target_center_days / 2.0
    if expected_leg_days <= config.ashare_t1_min_expected_leg_days:
        return _PreStrategyTradabilityPrecheck(
            status="passed_with_execution_risk_note",
            expected_leg_days=expected_leg_days,
            reason_zh=(
                f"{period} 是K线采样粒度，不是目标周期；该目标滤波周期约"
                f"{target_center_days:.2f}个交易日，理论半周期约"
                f"{expected_leg_days:.2f}个交易日，短于或等于A股T+1与"
                "下一根K线执行约束的传统风险阈值。该信息仅作为执行风险"
                "提示，不再阻断单周期、双周期或walk-forward验证。"
            ),
        )
    return _PreStrategyTradabilityPrecheck(
        status="passed",
        expected_leg_days=expected_leg_days,
        reason_zh=None,
    )


def _target_pre_strategy_blocked(_target: FilterWorkflowChainToolTarget) -> bool:
    return False


def _coerce_filter_mode(value: str) -> FilterMode:
    if value not in {"lowpass", "highpass", "bandpass"}:
        raise ValueError(f"Unsupported filter mode: {value}")
    return cast(FilterMode, value)


def _run_tool_selection_for_target(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    target: FilterWorkflowChainToolTarget,
    config: FilterWorkflowChainConfig,
    index_ref: str,
) -> FilterWorkflowChainToolResult:
    try:
        result = run_filter_tool_selection(
            rows,
            index_ref=index_ref,
            config=FilterToolSelectionConfig(
                period=cast(PeriodName, target.period),
                target_period_lo_bars=target.target_period_lo_bars,
                target_period_hi_bars=target.target_period_hi_bars,
                target_filter_mode=target.filter_mode,
                timestamp_column=config.timestamp_column,
                close_column=config.close_column,
                min_observations=config.workflow_min_observations,
                max_acceptable_lag_bars=config.tool_max_acceptable_lag_bars,
                top_n=config.tool_top_n,
                min_tool_quality_score=config.tool_min_quality_score,
            ),
        )
    except Exception as exc:
        return FilterWorkflowChainToolResult(
            target=target,
            status="failed",
            selected_filter=None,
            selected_tool_quality_score=None,
            tool_selection=None,
            error=str(exc),
        )
    selected = _best_selected_tool(result)
    if selected is None:
        return FilterWorkflowChainToolResult(
            target=target,
            status="skipped",
            selected_filter=None,
            selected_tool_quality_score=None,
            tool_selection=result.to_dict(),
            error="no selected filter passed tool quality threshold",
        )
    return FilterWorkflowChainToolResult(
        target=target,
        status="completed",
        selected_filter=selected.filter_spec,
        selected_tool_quality_score=selected.tool_quality_score,
        tool_selection=result.to_dict(),
    )


def _synthesized_higher_targets(
    tool_results: Sequence[FilterWorkflowChainToolResult],
    config: FilterWorkflowChainConfig,
) -> list[FilterWorkflowChainToolTarget]:
    completed = [item for item in tool_results if item.status == "completed"]
    targets: list[FilterWorkflowChainToolTarget] = []
    for execution in completed:
        if _target_pre_strategy_blocked(execution.target):
            continue
        has_valid = any(
            _is_coarser_period(candidate.target.period, execution.target.period)
            and not _target_pre_strategy_blocked(candidate.target)
            and _valid_ratio(candidate.target, execution.target, config)
            for candidate in completed
        )
        if has_valid or execution.target.target_center_days is None:
            continue
        target = _synthesize_higher_target(execution.target, config)
        if target is not None and not _target_already_present(target, completed):
            targets.append(target)
    return targets


def _synthesize_higher_target(
    execution: FilterWorkflowChainToolTarget,
    config: FilterWorkflowChainConfig,
) -> FilterWorkflowChainToolTarget | None:
    ratio = config.synthesized_higher_ratio or math.sqrt(
        config.min_higher_cycle_ratio * config.max_higher_cycle_ratio
    )
    center_days = (execution.target_center_days or 0.0) * ratio
    if center_days <= 0.0 or not math.isfinite(center_days):
        return None
    period = _best_coarser_period_for_cycle_days(
        execution.period,
        center_days,
        config.periods,
    )
    if period is None:
        return None
    bars_per_day = PERIOD_BARS_PER_DAY[period]
    lo_days = _target_days_from_bars(execution.target_period_lo_bars, execution.period)
    hi_days = _target_days_from_bars(execution.target_period_hi_bars, execution.period)
    target_lo_bars = max(2.0, lo_days * ratio * bars_per_day)
    target_hi_bars = max(target_lo_bars, hi_days * ratio * bars_per_day)
    precheck = _pre_strategy_tradability_precheck(
        period=period,
        target_center_days=center_days,
        config=config,
    )
    return FilterWorkflowChainToolTarget(
        period=period,
        recommendation_rank=1000 + execution.recommendation_rank,
        target_period_lo_bars=target_lo_bars,
        target_period_hi_bars=target_hi_bars,
        target_center_days=center_days,
        filter_mode=execution.filter_mode,
        recommendation_score=execution.recommendation_score,
        median_vs_random=execution.median_vs_random,
        continuous_peak_window_share=execution.continuous_peak_window_share,
        parameter_evidence_strength=execution.parameter_evidence_strength,
        parameter_evidence_strength_label_zh=(
            execution.parameter_evidence_strength_label_zh
        ),
        expected_leg_days=precheck.expected_leg_days,
        pre_strategy_tradability_status=precheck.status,
        pre_strategy_tradability_reason_zh=precheck.reason_zh,
        target_source="ratio_synthesized_direction_probe",
        source_execution_period=execution.period,
        frequency_candidate_id=execution.frequency_candidate_id,
        candidate_evidence_label=execution.candidate_evidence_label,
        center_frequency_cycles_per_day=(
            1.0 / center_days if center_days > 0.0 else None
        ),
        dii_bps=execution.dii_bps,
    )


def _target_days_from_bars(period_bars: float, period: str) -> float:
    return period_bars / PERIOD_BARS_PER_DAY[period]


def _best_coarser_period_for_cycle_days(
    execution_period: str,
    cycle_days: float,
    periods: Sequence[str],
) -> str | None:
    candidates = [
        period for period in periods if _is_coarser_period(period, execution_period)
    ]
    if not candidates:
        return None
    target_bars = 32.0
    return min(
        candidates,
        key=lambda period: abs(
            math.log(max(cycle_days * PERIOD_BARS_PER_DAY[period], 1e-12) / target_bars)
        ),
    )


def _target_already_present(
    target: FilterWorkflowChainToolTarget,
    completed: Sequence[FilterWorkflowChainToolResult],
) -> bool:
    for item in completed:
        if item.target.period != target.period:
            continue
        if item.target.target_center_days is None:
            continue
        ratio = item.target.target_center_days / max(
            target.target_center_days or 1.0,
            1e-12,
        )
        if 0.80 <= ratio <= 1.25:
            return True
    return False


def _best_selected_tool(
    result: FilterToolSelectionResult,
) -> FilterToolEvaluation | None:
    if not result.selected:
        return None
    return max(result.selected, key=lambda item: item.tool_quality_score)


def _run_chain_strategies(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    tool_results: Sequence[FilterWorkflowChainToolResult],
    config: FilterWorkflowChainConfig,
    index_ref: str,
) -> list[FilterWorkflowChainStrategyResult]:
    completed = [item for item in tool_results if item.status == "completed"]
    strategy_results: list[FilterWorkflowChainStrategyResult] = []
    for execution in completed:
        if _target_pre_strategy_blocked(execution.target):
            strategy_results.extend(
                _skipped_pre_strategy_results_for_blocked_target(execution, config)
            )
            continue
        if execution.target.target_source != "ratio_synthesized_direction_probe":
            for execution_filter_rank, execution_filter in _selected_filter_variants(
                execution
            ):
                output_kind = str(execution_filter.get("output_kind", "level"))
                if (
                    "single_period_component_trigger" in config.strategy_templates
                    and output_kind == "component"
                ):
                    strategy_results.append(
                        _run_one_single_period_strategy(
                            rows,
                            execution=execution,
                            execution_filter=execution_filter,
                            execution_filter_rank=execution_filter_rank,
                            strategy_template="single_period_component_trigger",
                            config=config,
                            index_ref=index_ref,
                        )
                    )
                if (
                    "single_period_level_slope_trigger" in config.strategy_templates
                    and output_kind == "level"
                ):
                    strategy_results.append(
                        _run_one_single_period_strategy(
                            rows,
                            execution=execution,
                            execution_filter=execution_filter,
                            execution_filter_rank=execution_filter_rank,
                            strategy_template="single_period_level_slope_trigger",
                            config=config,
                            index_ref=index_ref,
                        )
                    )
        if "higher_period_gate_execution_trigger" in config.strategy_templates:
            candidates = [
                candidate
                for candidate in completed
                if _is_coarser_period(candidate.target.period, execution.target.period)
                and not _target_pre_strategy_blocked(candidate.target)
                and _valid_ratio(candidate.target, execution.target, config)
            ]
            candidates = sorted(
                candidates,
                key=lambda candidate: _pair_score(candidate, execution, config),
                reverse=True,
            )[: config.max_strategies_per_execution_period]
            for higher in candidates:
                for higher_filter_rank, higher_filter in _selected_filter_variants(
                    higher
                ):
                    for (
                        execution_filter_rank,
                        execution_filter,
                    ) in _selected_filter_variants(execution):
                        strategy_results.append(
                            _run_one_strategy_pair(
                                rows,
                                higher=higher,
                                execution=execution,
                                higher_filter=higher_filter,
                                execution_filter=execution_filter,
                                higher_filter_rank=higher_filter_rank,
                                execution_filter_rank=execution_filter_rank,
                                config=config,
                                index_ref=index_ref,
                            )
                        )
    return strategy_results


def _skipped_pre_strategy_results_for_blocked_target(
    execution: FilterWorkflowChainToolResult,
    config: FilterWorkflowChainConfig,
) -> list[FilterWorkflowChainStrategyResult]:
    execution_filter = execution.selected_filter or {}
    execution_filter_name = str(execution_filter.get("name", ""))
    reason = execution.target.pre_strategy_tradability_reason_zh or (
        "pre-strategy tradability hard gate blocked this target"
    )
    results: list[FilterWorkflowChainStrategyResult] = []
    for single_template in (
        "single_period_component_trigger",
        "single_period_level_slope_trigger",
    ):
        if (
            single_template not in config.strategy_templates
            or execution.target.target_source == "ratio_synthesized_direction_probe"
        ):
            continue
        results.append(
            FilterWorkflowChainStrategyResult(
                strategy_template=single_template,
                execution_period=execution.target.period,
                higher_period=None,
                execution_filter_name=execution_filter_name,
                higher_filter_name=None,
                execution_filter_rank=1,
                higher_filter_rank=None,
                execution_cycle_days=execution.target.target_center_days or 0.0,
                higher_cycle_days=None,
                ratio=None,
                status="skipped",
                strategy=None,
                composite_backtest=None,
                render_artifacts=None,
                error=reason,
                frequency_candidate_id=execution.target.frequency_candidate_id,
                candidate_evidence_label=execution.target.candidate_evidence_label,
                center_frequency_cycles_per_day=(
                    execution.target.center_frequency_cycles_per_day
                ),
                dii_bps=execution.target.dii_bps,
            )
        )
    if "higher_period_gate_execution_trigger" in config.strategy_templates:
        results.append(
            FilterWorkflowChainStrategyResult(
                strategy_template="higher_period_gate_execution_trigger",
                execution_period=execution.target.period,
                higher_period=None,
                execution_filter_name=execution_filter_name,
                higher_filter_name=None,
                execution_filter_rank=1,
                higher_filter_rank=None,
                execution_cycle_days=execution.target.target_center_days or 0.0,
                higher_cycle_days=None,
                ratio=None,
                status="skipped",
                strategy=None,
                composite_backtest=None,
                render_artifacts=None,
                error=reason,
                frequency_candidate_id=execution.target.frequency_candidate_id,
                candidate_evidence_label=execution.target.candidate_evidence_label,
                center_frequency_cycles_per_day=(
                    execution.target.center_frequency_cycles_per_day
                ),
                dii_bps=execution.target.dii_bps,
            )
        )
    return results


def _selected_filter_variants(
    result: FilterWorkflowChainToolResult,
) -> list[tuple[int, Mapping[str, object]]]:
    """Return all selected filter specs retained by tool selection.

    `selected_filter` remains the best quality-only tool for backward-readable
    summaries, but strategy research must be able to battle the top-N selected
    tools because final tradability can differ even when signal-quality scores
    are close.
    """

    tool_selection = result.tool_selection or {}
    raw_selected = tool_selection.get("selected")
    variants: list[tuple[int, Mapping[str, object]]] = []
    if isinstance(raw_selected, list):
        for rank, item in enumerate(raw_selected, start=1):
            if not isinstance(item, Mapping):
                continue
            raw_spec = item.get("filter_spec")
            if isinstance(raw_spec, Mapping):
                variants.append((rank, raw_spec))
    if variants:
        return variants
    if result.selected_filter is not None:
        return [(1, result.selected_filter)]
    return []


def _is_coarser_period(candidate_period: str, execution_period: str) -> bool:
    return (
        PERIOD_FINE_TO_COARSE_RANK[candidate_period]
        > PERIOD_FINE_TO_COARSE_RANK[execution_period]
    )


def _valid_ratio(
    higher: FilterWorkflowChainToolTarget,
    execution: FilterWorkflowChainToolTarget,
    config: FilterWorkflowChainConfig,
) -> bool:
    if higher.target_center_days is None or execution.target_center_days is None:
        return False
    assessment = assess_filter_scale_relation(
        execution_cycle_days=execution.target_center_days,
        candidate_cycle_days=higher.target_center_days,
        config=FilterScaleHierarchyConfig(
            same_level_max_ratio=config.same_level_max_ratio,
            min_higher_cycle_ratio=config.min_higher_cycle_ratio,
            max_higher_cycle_ratio=config.max_higher_cycle_ratio,
        ),
    )
    return assessment.usable_as_direction_gate


def _pair_score(
    higher: FilterWorkflowChainToolResult,
    execution: FilterWorkflowChainToolResult,
    config: FilterWorkflowChainConfig,
) -> float:
    higher_days = higher.target.target_center_days or 0.0
    execution_days = execution.target.target_center_days or 0.0
    ratio = higher_days / execution_days if execution_days > 0.0 else 0.0
    ideal_ratio = math.sqrt(
        config.min_higher_cycle_ratio * config.max_higher_cycle_ratio
    )
    ratio_score = math.exp(-abs(math.log(max(ratio, 1e-12) / ideal_ratio)))
    return (
        ratio_score
        + 0.25 * (higher.selected_tool_quality_score or 0.0)
        + 0.25 * (execution.selected_tool_quality_score or 0.0)
        + 0.10 * higher.target.median_vs_random
        + 0.10 * execution.target.median_vs_random
    )


def _run_one_strategy_pair(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    higher: FilterWorkflowChainToolResult,
    execution: FilterWorkflowChainToolResult,
    higher_filter: Mapping[str, object],
    execution_filter: Mapping[str, object],
    higher_filter_rank: int,
    execution_filter_rank: int,
    config: FilterWorkflowChainConfig,
    index_ref: str,
) -> FilterWorkflowChainStrategyResult:
    higher_days = cast(float, higher.target.target_center_days)
    execution_days = cast(float, execution.target.target_center_days)
    ratio = higher_days / execution_days
    render_prefix = _render_prefix(
        config=config,
        index_ref=index_ref,
        strategy_template="higher_period_gate_execution_trigger",
        higher=higher,
        execution=execution,
        higher_filter=higher_filter,
        execution_filter=execution_filter,
        higher_filter_rank=higher_filter_rank,
        execution_filter_rank=execution_filter_rank,
    )
    try:
        strategy = run_filter_timing_strategy_workflow(
            rows,
            index_ref=index_ref,
            config=FilterTimingStrategyConfig(
                strategy_template="higher_period_gate_execution_trigger",
                higher_period=cast(PeriodName, higher.target.period),
                execution_period=cast(PeriodName, execution.target.period),
                higher_filter_spec=filter_spec_from_dict(higher_filter),
                execution_filter_spec=filter_spec_from_dict(execution_filter),
                conflict_policy=config.conflict_policy,
                cost_bps=config.cost_bps,
                commission_bps=config.commission_bps,
                stamp_tax_bps=config.stamp_tax_bps,
                min_observations=config.workflow_min_observations,
                timestamp_column=config.timestamp_column,
                close_column=config.close_column,
                higher_cycle_days_equiv=higher_days,
                execution_cycle_days_equiv=execution_days,
                same_level_max_ratio=config.same_level_max_ratio,
                min_higher_cycle_ratio=config.min_higher_cycle_ratio,
                max_higher_cycle_ratio=config.max_higher_cycle_ratio,
                render_output_prefix=render_prefix,
                render_price_scale=config.render_price_scale,
                render_max_bars=config.render_max_bars,
            ),
        ).to_dict()
    except Exception as exc:
        return FilterWorkflowChainStrategyResult(
            strategy_template="higher_period_gate_execution_trigger",
            execution_period=execution.target.period,
            higher_period=higher.target.period,
            execution_filter_name=str(execution_filter.get("name", "")),
            higher_filter_name=str(higher_filter.get("name", "")),
            execution_filter_rank=execution_filter_rank,
            higher_filter_rank=higher_filter_rank,
            execution_cycle_days=execution_days,
            higher_cycle_days=higher_days,
            ratio=ratio,
            status="failed",
            strategy=None,
            composite_backtest=None,
            render_artifacts=None,
            error=str(exc),
            frequency_candidate_id=execution.target.frequency_candidate_id,
            candidate_evidence_label=execution.target.candidate_evidence_label,
            center_frequency_cycles_per_day=(
                execution.target.center_frequency_cycles_per_day
            ),
            dii_bps=execution.target.dii_bps,
        )
    metadata = cast(dict[str, object], strategy.get("metadata", {}))
    return FilterWorkflowChainStrategyResult(
        strategy_template="higher_period_gate_execution_trigger",
        execution_period=execution.target.period,
        higher_period=higher.target.period,
        execution_filter_name=str(execution_filter.get("name", "")),
        higher_filter_name=str(higher_filter.get("name", "")),
        execution_filter_rank=execution_filter_rank,
        higher_filter_rank=higher_filter_rank,
        execution_cycle_days=execution_days,
        higher_cycle_days=higher_days,
        ratio=ratio,
        status="completed",
        strategy=strategy,
        composite_backtest=cast(dict[str, object], strategy.get("composite_backtest")),
        render_artifacts=cast(
            dict[str, object] | None,
            metadata.get("render_artifacts"),
        ),
        frequency_candidate_id=execution.target.frequency_candidate_id,
        candidate_evidence_label=execution.target.candidate_evidence_label,
        center_frequency_cycles_per_day=(
            execution.target.center_frequency_cycles_per_day
        ),
        dii_bps=execution.target.dii_bps,
    )


def _run_one_single_period_strategy(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    execution: FilterWorkflowChainToolResult,
    execution_filter: Mapping[str, object],
    execution_filter_rank: int,
    strategy_template: StrategyTemplate,
    config: FilterWorkflowChainConfig,
    index_ref: str,
) -> FilterWorkflowChainStrategyResult:
    execution_days = float(execution.target.target_center_days or 0.0)
    render_prefix = _render_prefix(
        config=config,
        index_ref=index_ref,
        strategy_template=strategy_template,
        higher=None,
        execution=execution,
        higher_filter=None,
        execution_filter=execution_filter,
        higher_filter_rank=None,
        execution_filter_rank=execution_filter_rank,
    )
    try:
        strategy = run_filter_timing_strategy_workflow(
            rows,
            index_ref=index_ref,
            config=FilterTimingStrategyConfig(
                strategy_template=strategy_template,
                execution_period=cast(PeriodName, execution.target.period),
                execution_filter_spec=filter_spec_from_dict(execution_filter),
                cost_bps=config.cost_bps,
                commission_bps=config.commission_bps,
                stamp_tax_bps=config.stamp_tax_bps,
                min_observations=config.workflow_min_observations,
                timestamp_column=config.timestamp_column,
                close_column=config.close_column,
                execution_cycle_days_equiv=(
                    execution_days if execution_days > 0.0 else None
                ),
                render_output_prefix=render_prefix,
                render_price_scale=config.render_price_scale,
                render_max_bars=config.render_max_bars,
            ),
        ).to_dict()
    except Exception as exc:
        return FilterWorkflowChainStrategyResult(
            strategy_template=strategy_template,
            execution_period=execution.target.period,
            higher_period=None,
            execution_filter_name=str(execution_filter.get("name", "")),
            higher_filter_name=None,
            execution_filter_rank=execution_filter_rank,
            higher_filter_rank=None,
            execution_cycle_days=execution_days,
            higher_cycle_days=None,
            ratio=None,
            status="failed",
            strategy=None,
            composite_backtest=None,
            render_artifacts=None,
            error=str(exc),
            frequency_candidate_id=execution.target.frequency_candidate_id,
            candidate_evidence_label=execution.target.candidate_evidence_label,
            center_frequency_cycles_per_day=(
                execution.target.center_frequency_cycles_per_day
            ),
            dii_bps=execution.target.dii_bps,
        )
    metadata = cast(dict[str, object], strategy.get("metadata", {}))
    return FilterWorkflowChainStrategyResult(
        strategy_template=strategy_template,
        execution_period=execution.target.period,
        higher_period=None,
        execution_filter_name=str(execution_filter.get("name", "")),
        higher_filter_name=None,
        execution_filter_rank=execution_filter_rank,
        higher_filter_rank=None,
        execution_cycle_days=execution_days,
        higher_cycle_days=None,
        ratio=None,
        status="completed",
        strategy=strategy,
        composite_backtest=cast(dict[str, object], strategy.get("composite_backtest")),
        render_artifacts=cast(
            dict[str, object] | None,
            metadata.get("render_artifacts"),
        ),
        frequency_candidate_id=execution.target.frequency_candidate_id,
        candidate_evidence_label=execution.target.candidate_evidence_label,
        center_frequency_cycles_per_day=(
            execution.target.center_frequency_cycles_per_day
        ),
        dii_bps=execution.target.dii_bps,
    )


def _render_prefix(
    *,
    config: FilterWorkflowChainConfig,
    index_ref: str,
    strategy_template: StrategyTemplate,
    higher: FilterWorkflowChainToolResult | None,
    execution: FilterWorkflowChainToolResult,
    higher_filter: Mapping[str, object] | None,
    execution_filter: Mapping[str, object],
    higher_filter_rank: int | None,
    execution_filter_rank: int,
) -> str | None:
    if not config.render_output_dir:
        return None
    safe_index = _safe_slug(index_ref)
    safe_execution_filter = _safe_slug(str(execution_filter.get("name", "exec")))
    if strategy_template in {
        "single_period_component_trigger",
        "single_period_level_slope_trigger",
    }:
        single_label = (
            "single_level"
            if strategy_template == "single_period_level_slope_trigger"
            else "single"
        )
        filename = (
            f"{safe_index}_{execution.target.period}_{single_label}_"
            f"{execution.target.recommendation_rank}_tool_"
            f"{execution_filter_rank}_{safe_execution_filter}"
        )
        return str(Path(config.render_output_dir) / filename)
    if higher is None or higher_filter is None or higher_filter_rank is None:
        raise ValueError("higher inputs are required for dual-cycle render prefix")
    safe_higher_filter = _safe_slug(str(higher_filter.get("name", "gate")))
    filename = (
        f"{safe_index}_{execution.target.period}_exec_"
        f"{execution.target.recommendation_rank}_tool_{execution_filter_rank}_"
        f"{safe_execution_filter}_by_"
        f"{higher.target.period}_gate_{higher.target.recommendation_rank}_"
        f"tool_{higher_filter_rank}_{safe_higher_filter}"
    )
    return str(Path(config.render_output_dir) / filename)


def _safe_slug(value: str) -> str:
    chars = [ch.lower() if ch.isalnum() else "_" for ch in value]
    slug = "".join(chars).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "index"


def _summary_backtests(
    strategy_results: Sequence[FilterWorkflowChainStrategyResult],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in strategy_results:
        if item.status != "completed" or not item.composite_backtest:
            continue
        backtest = item.composite_backtest
        rows.append(
            {
                "strategy_template": item.strategy_template,
                "execution_period": item.execution_period,
                "higher_period": item.higher_period,
                "execution_filter_name": item.execution_filter_name,
                "higher_filter_name": item.higher_filter_name,
                "execution_filter_rank": item.execution_filter_rank,
                "higher_filter_rank": item.higher_filter_rank,
                "execution_cycle_days": item.execution_cycle_days,
                "higher_cycle_days": item.higher_cycle_days,
                "cycle_ratio": item.ratio,
                "frequency_candidate_id": item.frequency_candidate_id,
                "center_frequency_cycles_per_day": (
                    item.center_frequency_cycles_per_day
                ),
                "candidate_evidence_label": item.candidate_evidence_label,
                "dii_bps": item.dii_bps,
                "pre_strategy_tradability_status": "passed",
                "pre_strategy_tradability_reason_zh": None,
                "expected_leg_days": (
                    item.execution_cycle_days / 2.0
                    if item.execution_cycle_days > 0.0
                    else None
                ),
                "final_nav": backtest.get("final_nav"),
                "cagr": backtest.get("cagr"),
                "sharpe_like": backtest.get("sharpe_like"),
                "max_drawdown": backtest.get("max_drawdown"),
                "trade_count": backtest.get("trade_count"),
                "exposure": backtest.get("exposure"),
                "turnover_per_year": backtest.get("turnover_per_year"),
                "reward_retention_vs_single": None,
                "cagr_delta_vs_single": None,
                "drawdown_compression_vs_single": None,
                "pareto_frontier": None,
                "gate_tradeoff_status": None,
                "gate_tradeoff_note_zh": None,
                "render_artifacts": item.render_artifacts,
            }
        )
    rows = _annotate_gate_ratio_tradeoffs(rows)
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("execution_period")),
            (
                0
                if row.get("strategy_template")
                == "higher_period_gate_execution_trigger"
                else 1
            ),
            str(row.get("higher_period") or ""),
        ),
    )


def _annotate_gate_ratio_tradeoffs(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Add single-vs-dual trade-off fields to summary rows.

    The annotations are descriptive.  They deliberately do not select the
    winning ratio, because production selection must be made with
    walk-forward/Pareto evidence rather than full-sample curve fitting.
    """

    single_by_key: dict[tuple[str, str, int], dict[str, object]] = {}
    best_single_by_period: dict[str, dict[str, object]] = {}
    for row in rows:
        if not str(row.get("strategy_template", "")).startswith("single_period_"):
            continue
        period = str(row.get("execution_period"))
        filter_name = str(row.get("execution_filter_name"))
        filter_rank = _int_value(row.get("execution_filter_rank"))
        single_by_key[(period, filter_name, filter_rank)] = row
        current_best = best_single_by_period.get(period)
        if current_best is None or _float_value(row.get("cagr")) > _float_value(
            current_best.get("cagr")
        ):
            best_single_by_period[period] = row

    dual_groups: dict[tuple[str, str, int], list[dict[str, object]]] = {}
    for row in rows:
        if row.get("strategy_template") != "higher_period_gate_execution_trigger":
            continue
        period = str(row.get("execution_period"))
        filter_name = str(row.get("execution_filter_name"))
        filter_rank = _int_value(row.get("execution_filter_rank"))
        key = (period, filter_name, filter_rank)
        baseline = single_by_key.get(key) or best_single_by_period.get(period)
        if baseline is not None:
            _annotate_one_dual_tradeoff(row, baseline)
        dual_groups.setdefault(key, []).append(row)

    for group in dual_groups.values():
        _mark_pareto_frontier(group)
    return rows


def _annotate_one_dual_tradeoff(
    row: dict[str, object],
    baseline: Mapping[str, object],
) -> None:
    dual_cagr = _float_or_none(row.get("cagr"))
    single_cagr = _float_or_none(baseline.get("cagr"))
    dual_drawdown = _float_or_none(row.get("max_drawdown"))
    single_drawdown = _float_or_none(baseline.get("max_drawdown"))

    reward_retention = None
    if dual_cagr is not None and single_cagr is not None and single_cagr > 1e-12:
        reward_retention = dual_cagr / single_cagr
    cagr_delta = (
        dual_cagr - single_cagr
        if dual_cagr is not None and single_cagr is not None
        else None
    )
    drawdown_compression = None
    if (
        dual_drawdown is not None
        and single_drawdown is not None
        and abs(single_drawdown) > 1e-12
    ):
        drawdown_compression = 1.0 - abs(dual_drawdown) / abs(single_drawdown)

    row["reward_retention_vs_single"] = reward_retention
    row["cagr_delta_vs_single"] = cagr_delta
    row["drawdown_compression_vs_single"] = drawdown_compression
    row["gate_tradeoff_status"] = _gate_tradeoff_status(
        dual_cagr=dual_cagr,
        single_cagr=single_cagr,
        reward_retention=reward_retention,
        drawdown_compression=drawdown_compression,
    )
    row["gate_tradeoff_note_zh"] = _gate_tradeoff_note(row["gate_tradeoff_status"])


def _gate_tradeoff_status(
    *,
    dual_cagr: float | None,
    single_cagr: float | None,
    reward_retention: float | None,
    drawdown_compression: float | None,
) -> str | None:
    if dual_cagr is None or single_cagr is None or drawdown_compression is None:
        return None
    if single_cagr <= 0.0 and dual_cagr > 0.0 and drawdown_compression >= 0.0:
        return "loss_to_gain_with_drawdown_compression"
    if single_cagr <= 0.0 and dual_cagr > 0.0:
        return "loss_to_gain_without_drawdown_compression"
    if reward_retention is None:
        return None
    if reward_retention >= 1.0 and drawdown_compression >= 0.0:
        return "enhanced_gate_candidate"
    if reward_retention < 1.0 and drawdown_compression > 0.0:
        return "defensive_gate_candidate"
    if reward_retention >= 1.0 and drawdown_compression < 0.0:
        return "return_up_drawdown_up"
    return "dominated_gate_candidate"


def _gate_tradeoff_note(status: object) -> str | None:
    if not isinstance(status, str):
        return None
    return {
        "loss_to_gain_with_drawdown_compression": (
            "双周期把亏损单周期修正为正收益并压缩回撤；收益保留率在单周期为负时"
            "不可解释，属于增强型门禁候选，仍需样本外确认。"
        ),
        "loss_to_gain_without_drawdown_compression": (
            "双周期把亏损单周期修正为正收益，但未压缩回撤；需要看风险预算和样本外稳定性。"
        ),
        "enhanced_gate_candidate": (
            "相对单周期同时保留/提高收益并压缩回撤，属于增强型门禁候选。"
        ),
        "defensive_gate_candidate": (
            "相对单周期牺牲部分收益以换取回撤压缩，属于防守型门禁候选。"
        ),
        "return_up_drawdown_up": (
            "相对单周期提高收益但放大回撤，需要看风险偏好和年度稳定性。"
        ),
        "dominated_gate_candidate": (
            "相对单周期收益下降且回撤未改善，通常不应升级为门禁参数。"
        ),
    }.get(status)


def _mark_pareto_frontier(group: Sequence[dict[str, object]]) -> None:
    candidates = [
        row
        for row in group
        if _float_or_none(row.get("cagr")) is not None
        and _float_or_none(row.get("max_drawdown")) is not None
    ]
    for row in group:
        row["pareto_frontier"] = False
    for row in candidates:
        cagr = _float_value(row.get("cagr"))
        drawdown_abs = abs(_float_value(row.get("max_drawdown")))
        dominated = False
        for other in candidates:
            if other is row:
                continue
            other_cagr = _float_value(other.get("cagr"))
            other_drawdown_abs = abs(_float_value(other.get("max_drawdown")))
            if (
                other_cagr >= cagr
                and other_drawdown_abs <= drawdown_abs
                and (other_cagr > cagr or other_drawdown_abs < drawdown_abs)
            ):
                dominated = True
                break
        row["pareto_frontier"] = not dominated


def _float_or_none(value: object) -> float | None:
    if not isinstance(value, int | float | str):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def _float_value(value: object) -> float:
    result = _float_or_none(value)
    return result if result is not None else float("-inf")


def _int_value(value: object) -> int:
    if not isinstance(value, int | float | str):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
