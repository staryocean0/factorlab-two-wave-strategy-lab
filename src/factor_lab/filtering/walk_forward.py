# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportMissingTypeStubs=false
# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportReturnType=false
# pyright: reportUnusedParameter=false
"""Walk-forward validation for governed filter timing signals.

The walk-forward layer keeps the workflow boundary explicit:

* each fold selects a filter only from the training window using the
  quality-only tool-selection score;
* the selected filter is then evaluated on the following test window;
* all trading metrics are computed only on out-of-sample test bars under the
  same next-bar execution protocol as the normal timing backtest.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from factor_lab.filtering.costs import (
    DEFAULT_COMMISSION_BPS,
    DEFAULT_STAMP_TAX_BPS,
    LongCashCostModel,
    resolve_long_cash_cost_model,
)
from factor_lab.filtering.strategy_workflow import apply_signal_governance
from factor_lab.filtering.timing_validation import (
    BACKTEST_FIELD_LABELS_ZH,
    COMPONENT_DIRECTION_SWITCH_SIGNAL_RULE,
    COMPONENT_DIRECTION_SWITCH_SIGNAL_RULE_ZH,
    FilterMode,
    FilterSpec,
    PeriodName,
    TimingValidationConfig,
    apply_filter_spec,
    max_drawdown,
    resample_close_frame,
    signal_from_filtered,
)
from factor_lab.filtering.tool_selection import (
    FilterToolSelectionConfig,
    FilterToolSelectionResult,
    run_filter_tool_selection,
)

WALK_FORWARD_FIELD_LABELS_ZH: dict[str, str] = {
    "fold_id": "滚动验证折编号",
    "train_start": "训练窗口开始日期",
    "train_end": "训练窗口结束日期，不含该日之后的新信息",
    "test_start": "样本外测试窗口开始日期",
    "test_end": "样本外测试窗口结束日期",
    "selected_filter_name": "训练段非收益质量分选出的滤波器",
    "train_tool_quality_score": (
        "训练段工具质量分：不使用收益，只看频率匹配、低滞后、连续度、"
        "保真、波动保留、可解释性"
    ),
    "final_nav": "测试段最终净值",
    "cagr": "测试段年化收益率",
    "sharpe_like": "测试段类夏普",
    "max_drawdown": "测试段最大回撤",
    "trade_count": "测试段交易次数",
    "turnover_per_year": "测试段年化换手",
    "positive_fold_count": "正收益测试折数量",
    "fold_count": "有效测试折数量",
}


@dataclass(frozen=True, slots=True)
class WalkForwardConfig:
    """Configuration for rolling walk-forward validation."""

    period: PeriodName = "60min"
    train_years: int = 5
    test_years: int = 1
    step_years: int = 1
    min_train_observations: int = 500
    min_test_observations: int = 50
    target_period_lo_bars: float = 25.0
    target_period_hi_bars: float = 64.0
    target_filter_mode: FilterMode = "bandpass"
    timestamp_column: str = "timestamp"
    close_column: str = "close"
    cost_bps: float | None = None
    commission_bps: float = DEFAULT_COMMISSION_BPS
    stamp_tax_bps: float = DEFAULT_STAMP_TAX_BPS
    annualization_bars: float | None = None
    max_acceptable_lag_bars: int = 20
    include_partial_final_test: bool = True
    min_hold_bars: int = 0
    cooldown_bars: int = 0
    confirmation_bars: int = 1

    @property
    def bars_per_year(self) -> float:
        return TimingValidationConfig(
            period=self.period,
            annualization_bars=self.annualization_bars,
        ).bars_per_year

    def __post_init__(self) -> None:
        if self.train_years <= 0:
            raise ValueError("train_years must be > 0")
        if self.test_years <= 0:
            raise ValueError("test_years must be > 0")
        if self.step_years <= 0:
            raise ValueError("step_years must be > 0")
        if self.min_train_observations < 3:
            raise ValueError("min_train_observations must be >= 3")
        if self.min_test_observations < 2:
            raise ValueError("min_test_observations must be >= 2")
        if self.target_period_lo_bars <= 0.0:
            raise ValueError("target_period_lo_bars must be > 0")
        if self.target_period_hi_bars < self.target_period_lo_bars:
            raise ValueError("target_period_hi_bars must be >= target_period_lo_bars")
        if self.max_acceptable_lag_bars <= 0:
            raise ValueError("max_acceptable_lag_bars must be > 0")
        if self.min_hold_bars < 0:
            raise ValueError("min_hold_bars must be >= 0")
        if self.cooldown_bars < 0:
            raise ValueError("cooldown_bars must be >= 0")
        if self.confirmation_bars < 1:
            raise ValueError("confirmation_bars must be >= 1")
        _ = resolve_long_cash_cost_model(
            cost_bps=self.cost_bps,
            commission_bps=self.commission_bps,
            stamp_tax_bps=self.stamp_tax_bps,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WalkForwardBacktestSummary:
    """Metrics for one out-of-sample return slice."""

    filter_name: str
    final_nav: float
    cagr: float
    annualized_volatility: float
    sharpe_like: float | None
    max_drawdown: float
    exposure: float
    turnover_per_year: float
    trade_count: int
    hit_rate: float | None
    sample_start: str
    sample_end: str
    sample_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WalkForwardFoldResult:
    """One rolling train/test fold."""

    fold_id: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_count: int
    test_count: int
    selected_filter_name: str
    train_tool_quality_score: float
    train_selection_rows: list[dict[str, object]]
    test_backtests: list[WalkForwardBacktestSummary]
    selected_test_backtest: WalkForwardBacktestSummary

    def to_dict(self) -> dict[str, object]:
        return {
            "fold_id": self.fold_id,
            "train_start": self.train_start,
            "train_end": self.train_end,
            "test_start": self.test_start,
            "test_end": self.test_end,
            "train_count": self.train_count,
            "test_count": self.test_count,
            "selected_filter_name": self.selected_filter_name,
            "train_tool_quality_score": self.train_tool_quality_score,
            "train_selection_rows": self.train_selection_rows,
            "test_backtests": [item.to_dict() for item in self.test_backtests],
            "selected_test_backtest": self.selected_test_backtest.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class WalkForwardResult:
    """Complete walk-forward validation artifact."""

    index_ref: str
    period: str
    folds: list[WalkForwardFoldResult]
    selected_oos_summary: WalkForwardBacktestSummary
    fixed_filter_oos_summaries: list[WalkForwardBacktestSummary]
    selection_counts: dict[str, int]
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "index_ref": self.index_ref,
            "period": self.period,
            "folds": [fold.to_dict() for fold in self.folds],
            "selected_oos_summary": self.selected_oos_summary.to_dict(),
            "fixed_filter_oos_summaries": [
                item.to_dict() for item in self.fixed_filter_oos_summaries
            ],
            "challenger_report": build_walk_forward_challenger_report(self),
            "selection_counts": dict(self.selection_counts),
            "metadata": self.metadata,
        }


def build_walk_forward_challenger_report(
    result: WalkForwardResult,
) -> list[dict[str, object]]:
    """Rank fixed-filter OOS challengers against train-quality selection.

    This is a validation-stage diagnostic only.  It explains when a fixed tool
    family outperformed the fold-by-fold quality selector after the OOS returns
    are known, without changing the no-PnL training selection protocol.
    """

    selected = result.selected_oos_summary
    selection_total = sum(result.selection_counts.values())
    rows: list[dict[str, object]] = []
    for rank, summary in enumerate(
        sorted(
            result.fixed_filter_oos_summaries,
            key=lambda item: item.cagr,
            reverse=True,
        ),
        start=1,
    ):
        selected_count = int(result.selection_counts.get(summary.filter_name, 0))
        cagr_delta = summary.cagr - selected.cagr
        rows.append(
            {
                "rank": rank,
                "filter_name": summary.filter_name,
                "fixed_filter_cagr": summary.cagr,
                "fixed_filter_max_drawdown": summary.max_drawdown,
                "fixed_filter_turnover_per_year": summary.turnover_per_year,
                "selected_oos_cagr": selected.cagr,
                "cagr_delta_vs_train_quality_selected": cagr_delta,
                "selection_count": selected_count,
                "selection_share": (
                    selected_count / selection_total if selection_total > 0 else 0.0
                ),
                "challenger_status": _challenger_status(cagr_delta, selected_count),
            }
        )
    return rows


def _challenger_status(cagr_delta: float, selected_count: int) -> str:
    if cagr_delta > 0.02 and selected_count == 0:
        return "missed_validation_challenger"
    if cagr_delta > 0.02:
        return "underweighted_validation_challenger"
    if cagr_delta >= -0.02:
        return "near_selected"
    return "inferior_to_selected"


@dataclass(frozen=True, slots=True)
class _StrategySurface:
    returns: pd.Series
    position: pd.Series
    position_change: pd.Series


def run_filter_walk_forward_validation(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: WalkForwardConfig | None = None,
    filter_specs: Sequence[FilterSpec],
    index_ref: str = "index_series",
) -> WalkForwardResult:
    """Run quality-selected rolling walk-forward validation.

    The training window calls `run_filter_tool_selection`, whose score formula
    does not inspect strategy returns.  Test-window metrics are computed after
    that selection decision is fixed.
    """

    cfg = config or WalkForwardConfig()
    if not filter_specs:
        raise ValueError("filter_specs must not be empty")
    close = resample_close_frame(
        rows,
        config=TimingValidationConfig(
            period=cfg.period,
            min_observations=cfg.min_train_observations,
            timestamp_column=cfg.timestamp_column,
            close_column=cfg.close_column,
            annualization_bars=cfg.annualization_bars,
        ),
    )
    log_close = pd.Series(np.log(close.to_numpy(dtype=np.float64)), index=close.index)
    raw_returns = log_close.diff().dropna()
    cost_model = resolve_long_cash_cost_model(
        cost_bps=cfg.cost_bps,
        commission_bps=cfg.commission_bps,
        stamp_tax_bps=cfg.stamp_tax_bps,
    )
    surfaces = {
        spec.name: _surface_for_spec(
            log_close=log_close,
            raw_returns=raw_returns,
            spec=spec,
            cost_model=cost_model,
            min_hold_bars=cfg.min_hold_bars,
            cooldown_bars=cfg.cooldown_bars,
            confirmation_bars=cfg.confirmation_bars,
        )
        for spec in filter_specs
    }
    spec_by_name = {spec.name: spec for spec in filter_specs}

    folds: list[WalkForwardFoldResult] = []
    fold_test_indexes: list[pd.Index] = []
    fold_id = 1
    offset_years = 0
    first_timestamp = pd.Timestamp(close.index.min())
    last_timestamp = pd.Timestamp(close.index.max())
    while True:
        train_start = first_timestamp + pd.DateOffset(years=offset_years)
        train_end = train_start + pd.DateOffset(years=cfg.train_years)
        test_start = train_end
        test_end = test_start + pd.DateOffset(years=cfg.test_years)
        if test_start > last_timestamp:
            break
        train_close = _slice_series(close, start=train_start, end=train_end)
        test_index = _slice_series(raw_returns, start=test_start, end=test_end).index
        if (
            len(train_close) >= cfg.min_train_observations
            and len(test_index) >= cfg.min_test_observations
        ):
            fold = _run_one_fold(
                fold_id=fold_id,
                train_close=train_close,
                test_index=test_index,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=min(test_end, last_timestamp),
                config=cfg,
                filter_specs=filter_specs,
                spec_by_name=spec_by_name,
                surfaces=surfaces,
                index_ref=index_ref,
            )
            folds.append(fold)
            fold_test_indexes.append(test_index)
            fold_id += 1
        elif test_end > last_timestamp and not cfg.include_partial_final_test:
            break
        offset_years += cfg.step_years

    if not folds:
        raise ValueError("walk-forward produced no valid folds")

    selected_summary = _selected_oos_summary(
        folds=folds,
        fold_indexes=fold_test_indexes,
        surfaces=surfaces,
        raw_returns=raw_returns,
        cost_model=cost_model,
        bars_per_year=cfg.bars_per_year,
    )
    fixed_summaries = [
        _concat_fold_summary(
            filter_name=spec.name,
            surface=surfaces[spec.name],
            fold_indexes=fold_test_indexes,
            bars_per_year=cfg.bars_per_year,
        )
        for spec in filter_specs
    ]
    selection_counts = dict(Counter(fold.selected_filter_name for fold in folds))
    return WalkForwardResult(
        index_ref=index_ref,
        period=cfg.period,
        folds=folds,
        selected_oos_summary=selected_summary,
        fixed_filter_oos_summaries=fixed_summaries,
        selection_counts=selection_counts,
        metadata={
            "config": cfg.to_dict(),
            "sample_start": _date_label(close.index.min()),
            "sample_end": _date_label(close.index.max()),
            "sample_count": len(close),
            "cost_model": cost_model.to_dict(),
            "selection_protocol": (
                "each fold selects filters on the training window with "
                "quality-only tool_selection; no PnL or test-window data is used"
            ),
            "selection_protocol_zh": (
                "每个折只在训练窗口用非收益工具质量分选滤波器；不读取训练收益、"
                "测试收益或测试窗口数据。"
            ),
            "lookahead_policy": (
                "filters are causal; signal governance uses only current and past "
                "signal states; test returns use signals observed on the previous "
                "bar; filter state may use prior training bars"
            ),
            "lookahead_policy_zh": (
                "滤波器只使用当前及过去K线；测试段收益使用上一根K线已经观察到的信号；"
                "测试段起点允许继承训练段形成的因果滤波状态。"
            ),
            "signal_governance_policy": {
                "min_hold_bars": cfg.min_hold_bars,
                "cooldown_bars": cfg.cooldown_bars,
                "confirmation_bars": cfg.confirmation_bars,
                "execution_timing": "governed_signal_at_bar_t_executes_on_bar_t_plus_1",
                "causality": "uses only current and past raw signal states",
            },
            "challenger_report_policy": (
                "fixed-filter out-of-sample summaries are retained as validation-stage "
                "challengers against the train-quality selected filter; they do not "
                "feed back into fold selection"
            ),
            "signal_rule": COMPONENT_DIRECTION_SWITCH_SIGNAL_RULE,
            "signal_rule_zh": COMPONENT_DIRECTION_SWITCH_SIGNAL_RULE_ZH,
            "field_labels_zh": {
                "walk_forward": dict(WALK_FORWARD_FIELD_LABELS_ZH),
                "backtest": dict(BACKTEST_FIELD_LABELS_ZH),
            },
        },
    )


def _run_one_fold(
    *,
    fold_id: int,
    train_close: pd.Series,
    test_index: pd.Index,
    train_start: pd.Timestamp,
    train_end: pd.Timestamp,
    test_start: pd.Timestamp,
    test_end: pd.Timestamp,
    config: WalkForwardConfig,
    filter_specs: Sequence[FilterSpec],
    spec_by_name: Mapping[str, FilterSpec],
    surfaces: Mapping[str, _StrategySurface],
    index_ref: str,
) -> WalkForwardFoldResult:
    selection = run_filter_tool_selection(
        _rows_from_close(train_close, config=config),
        config=FilterToolSelectionConfig(
            period=config.period,
            target_period_lo_bars=config.target_period_lo_bars,
            target_period_hi_bars=config.target_period_hi_bars,
            target_filter_mode=config.target_filter_mode,
            timestamp_column=config.timestamp_column,
            close_column=config.close_column,
            min_observations=config.min_train_observations,
            max_acceptable_lag_bars=config.max_acceptable_lag_bars,
            top_n=1,
            min_tool_quality_score=0.0,
        ),
        filter_specs=filter_specs,
        index_ref=index_ref,
    )
    selected_name, selected_score = _selected_from_quality(selection)
    if selected_name not in spec_by_name:
        raise ValueError(f"Selected unknown filter: {selected_name}")
    test_backtests = [
        _summarize_surface(
            filter_name=spec.name,
            surface=surfaces[spec.name],
            index=test_index,
            bars_per_year=config.bars_per_year,
        )
        for spec in filter_specs
    ]
    selected_backtest = next(
        item for item in test_backtests if item.filter_name == selected_name
    )
    return WalkForwardFoldResult(
        fold_id=fold_id,
        train_start=_date_label(train_close.index.min()),
        train_end=_date_label(train_close.index.max()),
        test_start=_date_label(test_index.min()),
        test_end=_date_label(test_index.max()),
        train_count=len(train_close),
        test_count=len(test_index),
        selected_filter_name=selected_name,
        train_tool_quality_score=selected_score,
        train_selection_rows=_selection_rows(selection),
        test_backtests=test_backtests,
        selected_test_backtest=selected_backtest,
    )


def _surface_for_spec(
    *,
    log_close: pd.Series,
    raw_returns: pd.Series,
    spec: FilterSpec,
    cost_model: LongCashCostModel,
    min_hold_bars: int = 0,
    cooldown_bars: int = 0,
    confirmation_bars: int = 1,
) -> _StrategySurface:
    filtered = apply_filter_spec(log_close, spec).dropna()
    signal = signal_from_filtered(filtered, output_kind=spec.output_kind)
    aligned_signal = signal.reindex(raw_returns.index).fillna(0.0).clip(0.0, 1.0)
    governed_signal = apply_signal_governance(
        aligned_signal,
        min_hold_bars=min_hold_bars,
        cooldown_bars=cooldown_bars,
        confirmation_bars=confirmation_bars,
    )
    position = governed_signal.shift(1).fillna(0.0).clip(0.0, 1.0)
    position_change = position.diff().fillna(position)
    buy_turnover = position_change.clip(lower=0.0)
    sell_turnover = (-position_change).clip(lower=0.0)
    returns = (
        position * raw_returns
        - buy_turnover * (cost_model.buy_cost_bps / 10000.0)
        - sell_turnover * (cost_model.sell_cost_bps / 10000.0)
    )
    return _StrategySurface(
        returns=returns,
        position=position,
        position_change=position_change,
    )


def _selected_oos_summary(
    *,
    folds: Sequence[WalkForwardFoldResult],
    fold_indexes: Sequence[pd.Index],
    surfaces: Mapping[str, _StrategySurface],
    raw_returns: pd.Series,
    cost_model: LongCashCostModel,
    bars_per_year: float,
) -> WalkForwardBacktestSummary:
    position_parts: list[pd.Series] = []
    for fold, index in zip(folds, fold_indexes, strict=True):
        position_parts.append(surfaces[fold.selected_filter_name].position.loc[index])
    position = pd.concat(position_parts).sort_index()
    position = position[~position.index.duplicated(keep="last")]
    local_returns = raw_returns.loc[position.index]
    position_change = position.diff().fillna(position)
    buy_turnover = position_change.clip(lower=0.0)
    sell_turnover = (-position_change).clip(lower=0.0)
    strategy_returns = (
        position * local_returns
        - buy_turnover * (cost_model.buy_cost_bps / 10000.0)
        - sell_turnover * (cost_model.sell_cost_bps / 10000.0)
    )
    return _summarize_returns(
        filter_name="walk_forward_selected_by_train_quality",
        returns=strategy_returns,
        position=position,
        position_change=position_change,
        bars_per_year=bars_per_year,
    )


def _concat_fold_summary(
    *,
    filter_name: str,
    surface: _StrategySurface,
    fold_indexes: Sequence[pd.Index],
    bars_per_year: float,
) -> WalkForwardBacktestSummary:
    if not fold_indexes:
        raise ValueError("fold_indexes must not be empty")
    index = fold_indexes[0]
    for fold_index in fold_indexes[1:]:
        index = index.append(fold_index)
    index = index.drop_duplicates().sort_values()
    return _summarize_surface(
        filter_name=filter_name,
        surface=surface,
        index=index,
        bars_per_year=bars_per_year,
    )


def _summarize_surface(
    *,
    filter_name: str,
    surface: _StrategySurface,
    index: pd.Index,
    bars_per_year: float,
) -> WalkForwardBacktestSummary:
    return _summarize_returns(
        filter_name=filter_name,
        returns=surface.returns.loc[index],
        position=surface.position.loc[index],
        position_change=surface.position_change.loc[index],
        bars_per_year=bars_per_year,
    )


def _summarize_returns(
    *,
    filter_name: str,
    returns: pd.Series,
    position: pd.Series,
    position_change: pd.Series,
    bars_per_year: float,
) -> WalkForwardBacktestSummary:
    clean_returns = returns.dropna()
    if clean_returns.empty:
        raise ValueError(f"No out-of-sample returns for {filter_name}")
    nav = pd.Series(
        np.exp(clean_returns.cumsum().to_numpy(dtype=np.float64)),
        index=clean_returns.index,
    )
    years = len(clean_returns) / bars_per_year
    final_nav = float(nav.iloc[-1])
    cagr = final_nav ** (1.0 / years) - 1.0 if years > 0.0 else 0.0
    annualized_volatility = float(clean_returns.std() * math.sqrt(bars_per_year))
    sharpe_like = (
        cagr / annualized_volatility if annualized_volatility > 0.0 else None
    )
    turnover = position_change.loc[clean_returns.index].abs()
    return WalkForwardBacktestSummary(
        filter_name=filter_name,
        final_nav=final_nav,
        cagr=cagr,
        annualized_volatility=annualized_volatility,
        sharpe_like=sharpe_like,
        max_drawdown=max_drawdown(nav),
        exposure=float(position.loc[clean_returns.index].mean()),
        turnover_per_year=float(turnover.sum() / years) if years > 0.0 else 0.0,
        trade_count=int(round(float(turnover.sum()))),
        hit_rate=float((clean_returns > 0.0).mean()),
        sample_start=_date_label(clean_returns.index.min()),
        sample_end=_date_label(clean_returns.index.max()),
        sample_count=len(clean_returns),
    )


def _selected_from_quality(selection: FilterToolSelectionResult) -> tuple[str, float]:
    if selection.selected:
        item = selection.selected[0]
        return item.filter_name, item.tool_quality_score
    if not selection.evaluations:
        raise ValueError("training selection produced no candidate evaluations")
    item = max(
        selection.evaluations,
        key=lambda candidate: candidate.tool_quality_score,
    )
    return item.filter_name, item.tool_quality_score


def _selection_rows(selection: FilterToolSelectionResult) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for rank, item in enumerate(selection.evaluations, start=1):
        rows.append(
            {
                "rank": rank,
                "filter_name": item.filter_name,
                "family": item.family,
                "tool_quality_score": item.tool_quality_score,
                "frequency_fit_score": item.frequency_fit_score,
                "low_lag_score": item.low_lag_score,
                "continuity_score": item.continuity_score,
                "fidelity_score": item.fidelity_score,
                "volatility_retention_score": item.volatility_retention_score,
                "interpretability_score": item.interpretability_score,
                "selection_status": item.selection_status,
            }
        )
    return rows


def _rows_from_close(close: pd.Series, *, config: WalkForwardConfig) -> pd.DataFrame:
    return pd.DataFrame(
        {
            config.timestamp_column: close.index,
            config.close_column: close.to_numpy(dtype=np.float64),
        }
    )


def _slice_series(
    series: pd.Series,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.Series:
    return series[(series.index >= start) & (series.index < end)]


def _date_label(value: object) -> str:
    return str(pd.Timestamp(value).date())
