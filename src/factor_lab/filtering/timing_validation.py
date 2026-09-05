# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportMissingTypeStubs=false
# pyright: reportUnnecessaryCast=false
"""Multi-period filter timing-validation workflow.

The workflow compares baseline smoothers with causal Fourier, Z/Laplace-domain
IIR, and causal Haar-wavelet filters.  It is designed for index timing-signal
research: quality metrics describe the filtered series, while the backtest uses
next-bar long/cash execution to avoid lookahead.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Literal, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from factor_lab.filtering.costs import (
    DEFAULT_COMMISSION_BPS,
    DEFAULT_STAMP_TAX_BPS,
    resolve_long_cash_cost_model,
)
from factor_lab.indicators.bar_direction_continuity import (
    compute_bar_direction_continuity,
)

PeriodName = Literal["1min", "5min", "15min", "30min", "60min", "day", "week"]
FilterFamily = Literal[
    "ema_baseline",
    "fourier_rolling",
    "laplace_iir",
    "wavelet_haar",
]
FilterMode = Literal["lowpass", "highpass", "bandpass"]
OutputKind = Literal["level", "component"]

PERIOD_RESAMPLE_RULE: dict[str, str] = {
    "1min": "1min",
    "5min": "5min",
    "15min": "15min",
    "30min": "30min",
    "60min": "60min",
    "day": "1D",
    "week": "W-FRI",
}
PERIOD_ANNUALIZATION_BARS: dict[str, float] = {
    "1min": 244.0 * 240.0,
    "5min": 244.0 * 48.0,
    "15min": 244.0 * 16.0,
    "30min": 244.0 * 8.0,
    "60min": 244.0 * 4.0,
    "day": 244.0,
    "week": 244.0 / 5.0,
}

COMPONENT_DIRECTION_SWITCH_SIGNAL_RULE = (
    "component_delta_direction_switch_next_bar_execution"
)
COMPONENT_DIRECTION_SWITCH_SIGNAL_RULE_ZH = (
    "带通/高通滤波分量先被视为一组新的分量K线；分量K线由下跌转为上涨时，"
    "第一根上涨K线收线后在下一根K线买入；分量K线由上涨转为下跌时，"
    "第一根下跌K线收线后在下一根K线卖出。分量的高 BDCI/连续度用于证明"
    "其涨跌方向切换少、状态持续性强。"
)
LEVEL_SLOPE_SIGNAL_RULE = "level_filter_slope_state_next_bar_execution"
LEVEL_SLOPE_SIGNAL_RULE_ZH = (
    "水平型滤波器以斜率为方向：滤波值上行时下一根K线持有，"
    "滤波值不再上行时下一根K线空仓。"
)
BACKTEST_FIELD_LABELS_ZH: dict[str, str] = {
    "filter_name": "滤波器名称",
    "final_nav": "最终净值",
    "cagr": "年化收益率",
    "annualized_volatility": "年化波动率",
    "sharpe_like": "类夏普比率：年化收益率 / 年化波动率",
    "sortino_like": "类索提诺比率：年化收益率 / 下行波动率",
    "max_drawdown": "最大回撤：净值从历史高点到后续低点的最大跌幅",
    "calmar_like": "类卡玛比率：年化收益率 / 最大回撤绝对值",
    "drawdown_duration_bars": "最长回撤持续K线数",
    "exposure": "平均持仓比例",
    "turnover_per_year": "年化换手次数",
    "trade_count": "买卖成交次数",
    "avg_hold_bars": "平均持仓K线数",
    "whipsaw5_rate": "5根K线内反复交易占比",
    "hit_rate": "逐K线正收益占比",
    "profit_factor": "盈利因子：盈利K线收益和 / 亏损K线绝对收益和",
    "cost_bps": "平均单边成本bps，仅解释成本模型",
    "buy_cost_bps": "买入成本bps",
    "sell_cost_bps": "卖出成本bps",
    "cost_model": "成本模型",
    "sample_start": "样本开始日期",
    "sample_end": "样本结束日期",
    "execution_protocol": "执行口径机器名",
    "execution_protocol_zh": "执行口径中文说明",
    "signal_rule": "信号规则机器名",
    "signal_rule_zh": "信号规则中文说明",
}
QUALITY_FIELD_LABELS_ZH: dict[str, str] = {
    "bdci_or_component_continuity": "BDCI或分量方向连续度，越高表示转向越少",
    "continuity_type": "连续度口径",
    "lag_bars_est": "估计滞后K线数",
    "same_bar_corr": "同K线相关性",
    "best_lag_corr": "最佳滞后相关性",
    "volatility_retention": "波动保留比例",
    "signal_rule": "该滤波输出默认如何变成买卖状态",
    "signal_rule_zh": "信号规则中文说明",
}

@dataclass(frozen=True, slots=True)
class FilterSpec:
    """One candidate filter to evaluate."""

    name: str
    family: FilterFamily
    mode: FilterMode
    params: Mapping[str, float | int]
    output_kind: OutputKind = "level"


@dataclass(frozen=True, slots=True)
class TimingValidationConfig:
    """Evaluation protocol for one bar period."""

    period: PeriodName = "day"
    cost_bps: float | None = None
    commission_bps: float = DEFAULT_COMMISSION_BPS
    stamp_tax_bps: float = DEFAULT_STAMP_TAX_BPS
    min_observations: int = 30
    timestamp_column: str = "timestamp"
    close_column: str = "close"
    annualization_bars: float | None = None

    @property
    def bars_per_year(self) -> float:
        if self.annualization_bars is not None:
            return self.annualization_bars
        return PERIOD_ANNUALIZATION_BARS[self.period]

    def __post_init__(self) -> None:
        if self.period not in PERIOD_RESAMPLE_RULE:
            raise ValueError(f"Unsupported timing-validation period: {self.period}")
        _ = resolve_long_cash_cost_model(
            cost_bps=self.cost_bps,
            commission_bps=self.commission_bps,
            stamp_tax_bps=self.stamp_tax_bps,
        )
        if self.min_observations < 3:
            raise ValueError("min_observations must be >= 3")
        if self.annualization_bars is not None and self.annualization_bars <= 0.0:
            raise ValueError("annualization_bars must be > 0 when provided")


@dataclass(frozen=True, slots=True)
class FilterQualityMetrics:
    """Quality metrics for a filtered series."""

    filter_name: str
    family: str
    mode: str
    output_kind: str
    bdci_or_component_continuity: float | None
    continuity_type: str
    lag_bars_est: int | None
    same_bar_corr: float | None
    best_lag_corr: float | None
    volatility_retention: float | None
    sample_start: str
    sample_end: str
    sample_count: int
    no_lookahead_protocol: str
    signal_rule: str
    signal_rule_zh: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BacktestMetrics:
    """Long/cash next-bar backtest metrics."""

    filter_name: str
    final_nav: float
    cagr: float
    annualized_volatility: float
    sharpe_like: float | None
    sortino_like: float | None
    max_drawdown: float
    calmar_like: float | None
    drawdown_duration_bars: int
    exposure: float
    turnover_per_year: float
    trade_count: int
    avg_hold_bars: float | None
    whipsaw5_rate: float | None
    hit_rate: float | None
    profit_factor: float | None
    cost_bps: float
    buy_cost_bps: float
    sell_cost_bps: float
    cost_model: str
    sample_start: str
    sample_end: str
    execution_protocol: str
    execution_protocol_zh: str
    signal_rule: str
    signal_rule_zh: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TimingValidationResult:
    """Complete workflow result for one input series and period."""

    period: str
    quality: list[FilterQualityMetrics]
    backtests: list[BacktestMetrics]
    ranked: list[dict[str, object]]
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "period": self.period,
            "quality": [item.to_dict() for item in self.quality],
            "backtests": [item.to_dict() for item in self.backtests],
            "ranked": self.ranked,
            "metadata": self.metadata,
        }


def default_filter_specs() -> tuple[FilterSpec, ...]:
    """Return the default battle roster."""

    return (
        FilterSpec("ema10_baseline_lowpass", "ema_baseline", "lowpass", {"span": 10}),
        FilterSpec("ema20_baseline_lowpass", "ema_baseline", "lowpass", {"span": 20}),
        FilterSpec(
            "fourier_lp_w128_p40",
            "fourier_rolling",
            "lowpass",
            {"window": 128, "cutoff_period": 40},
        ),
        FilterSpec(
            "fourier_bp_w256_p20_80",
            "fourier_rolling",
            "bandpass",
            {"window": 256, "low_period": 20, "high_period": 80},
            "component",
        ),
        FilterSpec("laplace_iir_lp_p60", "laplace_iir", "lowpass", {"period": 60}),
        FilterSpec(
            "laplace_iir_bp_p40",
            "laplace_iir",
            "bandpass",
            {"period": 40, "q": 1.0},
            "component",
        ),
        FilterSpec(
            "wavelet_haar_lp_l3_w64",
            "wavelet_haar",
            "lowpass",
            {"window": 64, "level": 3},
        ),
        FilterSpec(
            "wavelet_haar_detail_l2_w64",
            "wavelet_haar",
            "highpass",
            {"window": 64, "level": 2},
            "component",
        ),
        FilterSpec(
            "wavelet_haar_bp_l2_l5_w128",
            "wavelet_haar",
            "bandpass",
            {"window": 128, "level": 2, "slow_level": 5},
            "component",
        ),
    )


DEFAULT_FILTER_SPECS = default_filter_specs()


def resample_close_frame(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: TimingValidationConfig,
) -> pd.Series:
    """Return close prices at the requested bar period."""

    frame = (
        pd.DataFrame(rows).copy()
        if not isinstance(rows, pd.DataFrame)
        else rows.copy()
    )
    if config.timestamp_column not in frame.columns:
        raise ValueError(f"Missing timestamp column: {config.timestamp_column}")
    if config.close_column not in frame.columns:
        raise ValueError(f"Missing close column: {config.close_column}")
    timestamp_index = pd.DatetimeIndex(pd.to_datetime(frame[config.timestamp_column]))
    close = cast(pd.Series, pd.to_numeric(frame[config.close_column], errors="coerce"))
    series = pd.Series(
        close.to_numpy(dtype=np.float64),
        index=timestamp_index,
    )
    series = series.sort_index()
    series = cast(pd.Series, series[np.isfinite(series)])
    series = cast(pd.Series, series[series > 0.0])
    rule = PERIOD_RESAMPLE_RULE[config.period]
    return cast(pd.Series, series.resample(rule).last().dropna())


def apply_filter_spec(log_close: pd.Series, spec: FilterSpec) -> pd.Series:
    """Apply one candidate filter to log close prices."""

    if spec.family == "ema_baseline":
        span = _positive_int(spec.params, "span")
        return cast(
            pd.Series,
            log_close.ewm(span=span, adjust=False, min_periods=span).mean(),
        )
    if spec.family == "fourier_rolling":
        return _rolling_fourier_filter(log_close, spec)
    if spec.family == "laplace_iir":
        return _iir_biquad_filter(log_close, spec)
    if spec.family == "wavelet_haar":
        return _rolling_haar_filter(log_close, spec)
    raise ValueError(f"Unsupported filter family: {spec.family}")


def signal_rule_for_output_kind(output_kind: OutputKind) -> dict[str, str]:
    """Return the governed signal policy for one filtered output kind."""

    if output_kind == "component":
        return {
            "signal_rule": COMPONENT_DIRECTION_SWITCH_SIGNAL_RULE,
            "signal_rule_zh": COMPONENT_DIRECTION_SWITCH_SIGNAL_RULE_ZH,
        }
    return {
        "signal_rule": LEVEL_SLOPE_SIGNAL_RULE,
        "signal_rule_zh": LEVEL_SLOPE_SIGNAL_RULE_ZH,
    }


def signal_from_filtered(filtered: pd.Series, *, output_kind: OutputKind) -> pd.Series:
    """Generate the governed long/cash timing state from a filtered output.

    Component outputs are band-pass/high-pass oscillatory components.  Their
    governed use is the direction of the component's own K-line: when
    `filtered.diff()` changes from down to up, the signal switches long; when it
    changes from up to down, the signal switches cash.  `backtest_long_cash`
    applies the one-bar execution shift, so the first up/down component bar
    itself never earns the return created by its signal.
    """

    if output_kind == "level":
        return cast(pd.Series, (filtered.diff() > 0.0).astype(float))
    return _component_delta_direction_state(filtered)


def _component_delta_direction_state(filtered: pd.Series) -> pd.Series:
    changes = filtered.diff()
    signs = pd.Series(np.sign(changes.to_numpy(dtype=float)), index=filtered.index)
    # Flat component bars do not create a new up/down K-line direction.  Carry
    # the last non-zero direction so buy/sell events are tied to true direction
    # switches, matching the BDCI convention that ignores zero returns.
    carried = cast(pd.Series, signs.replace(0.0, np.nan).ffill().fillna(-1.0))
    return cast(pd.Series, (carried > 0.0).astype(float))


def evaluate_filter_quality(
    spec: FilterSpec,
    *,
    log_close: pd.Series,
    raw_returns: pd.Series | None = None,
) -> FilterQualityMetrics | None:
    """Evaluate one causal filter without running a return backtest.

    This is the public quality-only entry point used by the filter-tool
    selection workflow.  It deliberately reports signal quality, lag, fidelity
    and continuity only; it does not inspect strategy PnL.
    """

    returns = raw_returns if raw_returns is not None else log_close.diff().dropna()
    filtered = apply_filter_spec(log_close, spec).dropna()
    if len(filtered) < 3:
        return None
    return _quality_metrics(spec, filtered=filtered, raw_returns=returns)


def run_filter_timing_validation(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: TimingValidationConfig | None = None,
    filter_specs: Sequence[FilterSpec] = DEFAULT_FILTER_SPECS,
) -> TimingValidationResult:
    """Run quality metrics and next-bar long/cash backtests for filter specs."""

    cfg = config or TimingValidationConfig()
    close = resample_close_frame(rows, config=cfg)
    if len(close) < cfg.min_observations:
        raise ValueError("Not enough observations for timing validation")
    log_close = pd.Series(
        np.log(close.to_numpy(dtype=np.float64)),
        index=close.index,
    )
    raw_returns = log_close.diff().dropna()
    cost_model = resolve_long_cash_cost_model(
        cost_bps=cfg.cost_bps,
        commission_bps=cfg.commission_bps,
        stamp_tax_bps=cfg.stamp_tax_bps,
    )

    quality: list[FilterQualityMetrics] = []
    backtests: list[BacktestMetrics] = []
    for spec in filter_specs:
        filtered = apply_filter_spec(log_close, spec).dropna()
        if len(filtered) < cfg.min_observations:
            continue
        signal = signal_from_filtered(filtered, output_kind=spec.output_kind)
        signal_policy = signal_rule_for_output_kind(spec.output_kind)
        quality.append(
            _quality_metrics(
                spec,
                filtered=filtered,
                raw_returns=raw_returns,
            )
        )
        backtests.append(
            backtest_long_cash(
                filter_name=spec.name,
                raw_returns=raw_returns,
                signal=signal,
                bars_per_year=cfg.bars_per_year,
                cost_bps=cfg.cost_bps,
                commission_bps=cfg.commission_bps,
                stamp_tax_bps=cfg.stamp_tax_bps,
                signal_rule=signal_policy["signal_rule"],
                signal_rule_zh=signal_policy["signal_rule_zh"],
            )
        )

    ranked = _rank_results(quality, backtests)
    return TimingValidationResult(
        period=cfg.period,
        quality=quality,
        backtests=backtests,
        ranked=ranked,
        metadata={
            "sample_start": _series_date_label(close, boundary="min"),
            "sample_end": _series_date_label(close, boundary="max"),
            "sample_count": len(close),
            "cost_bps": cost_model.cost_bps,
            "cost_model": cost_model.to_dict(),
            "bar_annualization": cfg.bars_per_year,
            "workflow_role": "filter_timing_validation",
            "factor_lifecycle_mutation": False,
            "strategy_lifecycle_mutation": False,
            "lookahead_policy": "signal_at_bar_t_executes_on_bar_t_plus_1",
            "signal_generation_policy": {
                "component": signal_rule_for_output_kind("component"),
                "level": signal_rule_for_output_kind("level"),
            },
            "field_labels_zh": {
                "backtests": dict(BACKTEST_FIELD_LABELS_ZH),
                "quality": dict(QUALITY_FIELD_LABELS_ZH),
            },
        },
    )


def backtest_long_cash(
    *,
    filter_name: str,
    raw_returns: pd.Series,
    signal: pd.Series,
    bars_per_year: float,
    cost_bps: float | None = None,
    commission_bps: float = DEFAULT_COMMISSION_BPS,
    stamp_tax_bps: float = DEFAULT_STAMP_TAX_BPS,
    signal_rule: str = "binary_state_signal_next_bar_execution",
    signal_rule_zh: str = (
        "输入 signal 是0/1持仓状态；bar t 观察到的状态在 bar t+1 执行。"
    ),
) -> BacktestMetrics:
    """Backtest a long/cash signal using next-bar execution.

    The position is `signal.shift(1)`, so a signal observed at bar t cannot earn
    bar t's return.  This is the core anti-lookahead rule for the workflow.
    """

    aligned_signal = signal.reindex(raw_returns.index).fillna(0.0).clip(0.0, 1.0)
    position = cast(pd.Series, aligned_signal.shift(1).fillna(0.0))
    position_change = cast(pd.Series, position.diff().fillna(position))
    turnover = position_change.abs()
    buy_turnover = position_change.clip(lower=0.0)
    sell_turnover = (-position_change).clip(lower=0.0)
    cost_model = resolve_long_cash_cost_model(
        cost_bps=cost_bps,
        commission_bps=commission_bps,
        stamp_tax_bps=stamp_tax_bps,
    )
    strategy_returns = cast(
        pd.Series,
        position * raw_returns
        - buy_turnover * (cost_model.buy_cost_bps / 10000.0)
        - sell_turnover * (cost_model.sell_cost_bps / 10000.0),
    )
    nav = pd.Series(
        np.exp(strategy_returns.cumsum().to_numpy(dtype=np.float64)),
        index=strategy_returns.index,
    )
    nav = cast(pd.Series, nav[nav > 0.0])
    if nav.empty:
        raise ValueError("Backtest produced no positive NAV observations")

    ann_return = _annualized_return(nav, bars_per_year=bars_per_year)
    ann_vol = float(strategy_returns.std() * math.sqrt(bars_per_year))
    downside = strategy_returns[strategy_returns < 0.0]
    downside_vol = (
        float(downside.std() * math.sqrt(bars_per_year)) if len(downside) else 0.0
    )
    max_dd = max_drawdown(nav)
    calmar = ann_return / abs(max_dd) if max_dd < 0.0 else None
    sharpe = ann_return / ann_vol if ann_vol > 0.0 else None
    sortino = ann_return / downside_vol if downside_vol > 0.0 else None
    intervals = _position_change_intervals(position)
    wins = strategy_returns[strategy_returns > 0.0]
    losses = strategy_returns[strategy_returns < 0.0]
    loss_sum = abs(float(losses.sum()))
    profit_factor = float(wins.sum()) / loss_sum if loss_sum > 0.0 else None
    years = len(strategy_returns) / bars_per_year

    return BacktestMetrics(
        filter_name=filter_name,
        final_nav=float(nav.iloc[-1]),
        cagr=ann_return,
        annualized_volatility=ann_vol,
        sharpe_like=sharpe,
        sortino_like=sortino,
        max_drawdown=max_dd,
        calmar_like=calmar,
        drawdown_duration_bars=_max_drawdown_duration(nav),
        exposure=float(position.mean()),
        turnover_per_year=float(turnover.sum() / years) if years > 0.0 else 0.0,
        trade_count=int(round(float(turnover.sum()))),
        avg_hold_bars=float(np.mean(intervals)) if len(intervals) else None,
        whipsaw5_rate=float(np.mean(intervals <= 5)) if len(intervals) else None,
        hit_rate=float((strategy_returns > 0.0).mean()),
        profit_factor=profit_factor,
        cost_bps=cost_model.cost_bps,
        buy_cost_bps=cost_model.buy_cost_bps,
        sell_cost_bps=cost_model.sell_cost_bps,
        cost_model=cost_model.cost_model,
        sample_start=_series_date_label(strategy_returns, boundary="min"),
        sample_end=_series_date_label(strategy_returns, boundary="max"),
        execution_protocol="signal_at_bar_t_executes_on_bar_t_plus_1",
        execution_protocol_zh="bar t 产生的信号在下一根K线执行，避免同K线未来函数",
        signal_rule=signal_rule,
        signal_rule_zh=signal_rule_zh,
    )


def max_drawdown(nav: pd.Series) -> float:
    """Return peak-to-trough max drawdown on a NAV curve.

    A -0.40 drawdown means the strategy NAV fell 40% from a previous equity high
    to a later trough inside the tested sample; it is not a single-trade loss.
    """

    positive_nav = nav.dropna()
    if positive_nav.empty:
        return 0.0
    drawdown = positive_nav / positive_nav.cummax() - 1.0
    return float(drawdown.min())


def _quality_metrics(
    spec: FilterSpec,
    *,
    filtered: pd.Series,
    raw_returns: pd.Series,
) -> FilterQualityMetrics:
    if spec.output_kind == "level":
        positive_level = np.exp(filtered - filtered.iloc[0]) * 1000.0
        bdci = compute_bar_direction_continuity(positive_level.tolist()).score
        continuity_type = "official_level_bdci"
    else:
        bdci = _component_direction_continuity(filtered)
        continuity_type = "component_delta_continuity_not_official_bdci"
    lag_bars, best_corr, same_corr, vol_retention = _lag_quality(raw_returns, filtered)
    return FilterQualityMetrics(
        filter_name=spec.name,
        family=spec.family,
        mode=spec.mode,
        output_kind=spec.output_kind,
        bdci_or_component_continuity=bdci,
        continuity_type=continuity_type,
        lag_bars_est=lag_bars,
        same_bar_corr=same_corr,
        best_lag_corr=best_corr,
        volatility_retention=vol_retention,
        sample_start=_series_date_label(filtered, boundary="min"),
        sample_end=_series_date_label(filtered, boundary="max"),
        sample_count=len(filtered),
        no_lookahead_protocol="causal_filter_uses_current_and_past_bars_only",
        **signal_rule_for_output_kind(spec.output_kind),
    )


def _rank_results(
    quality: Sequence[FilterQualityMetrics],
    backtests: Sequence[BacktestMetrics],
) -> list[dict[str, object]]:
    quality_by_name = {item.filter_name: item for item in quality}
    ranked: list[dict[str, object]] = []
    for bt in backtests:
        q = quality_by_name[bt.filter_name]
        continuity = q.bdci_or_component_continuity or 0.0
        sharpe = bt.sharpe_like or 0.0
        whipsaw = bt.whipsaw5_rate or 0.0
        lag = float(q.lag_bars_est or 0)
        score = (
            35.0 * sharpe
            + 0.25 * continuity
            - 12.0 * abs(bt.max_drawdown)
            - 8.0 * whipsaw
            - 0.35 * bt.turnover_per_year
            - 0.4 * lag
        )
        ranked.append(
            {
                "filter_name": bt.filter_name,
                "family": q.family,
                "mode": q.mode,
                "continuity": continuity,
                "continuity_type": q.continuity_type,
                "cagr": bt.cagr,
                "sharpe_like": bt.sharpe_like,
                "max_drawdown": bt.max_drawdown,
                "turnover_per_year": bt.turnover_per_year,
                "whipsaw5_rate": bt.whipsaw5_rate,
                "lag_bars_est": q.lag_bars_est,
                "composite_score": score,
            }
        )
    return sorted(
        ranked,
        key=lambda row: float(cast(float, row["composite_score"])),
        reverse=True,
    )


def _rolling_fourier_filter(log_close: pd.Series, spec: FilterSpec) -> pd.Series:
    window = _positive_int(spec.params, "window")
    values = log_close.to_numpy(dtype=float)
    output = np.full(len(values), np.nan)
    freqs = np.abs(np.fft.fftfreq(window, d=1.0))
    for index in range(window - 1, len(values)):
        segment = values[index - window + 1 : index + 1]
        mean_value = float(np.mean(segment))
        centered = segment - mean_value
        spectrum = np.fft.fft(centered)
        mask = _fourier_mask(freqs, spec)
        filtered = np.fft.ifft(spectrum * mask).real
        output[index] = filtered[-1] + (mean_value if spec.mode == "lowpass" else 0.0)
    return pd.Series(output, index=log_close.index)


def _fourier_mask(freqs: NDArray[np.float64], spec: FilterSpec) -> NDArray[np.bool_]:
    if spec.mode == "lowpass":
        cutoff_period = _positive_float(spec.params, "cutoff_period")
        return freqs <= (1.0 / cutoff_period)
    if spec.mode == "highpass":
        cutoff_period = _positive_float(spec.params, "cutoff_period")
        mask = freqs >= (1.0 / cutoff_period)
        mask[0] = False
        return mask
    low_period = _positive_float(spec.params, "low_period")
    high_period = _positive_float(spec.params, "high_period")
    if high_period <= low_period:
        raise ValueError("bandpass high_period must be > low_period")
    mask = (freqs >= (1.0 / high_period)) & (freqs <= (1.0 / low_period))
    mask[0] = False
    return mask


def _iir_biquad_filter(log_close: pd.Series, spec: FilterSpec) -> pd.Series:
    period = _positive_float(spec.params, "period")
    q = float(spec.params.get("q", 1.0 / math.sqrt(2.0)))
    if q <= 0.0 or not math.isfinite(q):
        raise ValueError("q must be finite and > 0")
    b0, b1, b2, a1, a2 = _biquad_coefficients(spec.mode, period, q)
    source = log_close.to_numpy(dtype=float)
    # High-pass and band-pass filters reject a constant level, but centering on
    # the full-sample mean leaks future observations into the recursive filter's
    # initial state.  Anchor to the first observation instead: it is known at
    # initialization, preserves constant-shift invariance, and makes every
    # computed prefix independent of later appended bars.
    causal_anchor = float(source[0]) if len(source) and np.isfinite(source[0]) else 0.0
    base = source if spec.mode == "lowpass" else source - causal_anchor
    output = np.zeros(len(base), dtype=float)
    x1 = x2 = y1 = y2 = 0.0
    for index, value in enumerate(base):
        y0 = b0 * value + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        output[index] = y0
        x2, x1 = x1, value
        y2, y1 = y1, y0
    result = pd.Series(output, index=log_close.index)
    warmup = min(len(result), max(5, int(period * 3)))
    result.iloc[:warmup] = np.nan
    return result


def _biquad_coefficients(
    mode: FilterMode, period: float, q: float
) -> tuple[float, float, float, float, float]:
    omega = 2.0 * math.pi / period
    cosine = math.cos(omega)
    sine = math.sin(omega)
    alpha = sine / (2.0 * q)
    if mode == "lowpass":
        b0 = (1.0 - cosine) / 2.0
        b1 = 1.0 - cosine
        b2 = (1.0 - cosine) / 2.0
    elif mode == "highpass":
        b0 = (1.0 + cosine) / 2.0
        b1 = -(1.0 + cosine)
        b2 = (1.0 + cosine) / 2.0
    else:
        b0 = alpha
        b1 = 0.0
        b2 = -alpha
    a0 = 1.0 + alpha
    a1 = -2.0 * cosine
    a2 = 1.0 - alpha
    return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0


def _rolling_haar_filter(log_close: pd.Series, spec: FilterSpec) -> pd.Series:
    window = _positive_int(spec.params, "window")
    level = _positive_int(spec.params, "level")
    if window % (2**level) != 0:
        raise ValueError("wavelet window must be divisible by 2**level")
    if spec.mode == "bandpass":
        slow_level = _positive_int(spec.params, "slow_level")
        if slow_level <= level:
            raise ValueError("wavelet slow_level must be > level for bandpass")
        if window % (2**slow_level) != 0:
            raise ValueError("wavelet window must be divisible by 2**slow_level")
    else:
        slow_level = level
    values = log_close.to_numpy(dtype=float)
    output = np.full(len(values), np.nan)
    for index in range(window - 1, len(values)):
        segment = values[index - window + 1 : index + 1]
        low_component = _haar_lowpass_reconstruction(segment, level)
        if spec.mode == "lowpass":
            output[index] = low_component[-1]
        elif spec.mode == "highpass":
            output[index] = segment[-1] - low_component[-1]
        else:
            slow_component = _haar_lowpass_reconstruction(segment, slow_level)
            output[index] = low_component[-1] - slow_component[-1]
    return pd.Series(output, index=log_close.index)


def _haar_lowpass_reconstruction(
    segment: NDArray[np.float64], level: int
) -> NDArray[np.float64]:
    """Return trailing-window Haar DWT low-pass reconstruction.

    The decomposition and reconstruction are computed only inside the current
    trailing window.  The caller later reads the last point, so the output is
    causal for backtesting despite being a transform over the trailing window.
    """

    approximation = segment.astype(float, copy=True)
    details: list[NDArray[np.float64]] = []
    for _ in range(level):
        left = approximation[0::2]
        right = approximation[1::2]
        details.append((left - right) / 2.0)
        approximation = (left + right) / 2.0
    for detail in reversed(details):
        zeros = np.zeros_like(detail)
        reconstructed = np.empty(detail.size * 2, dtype=float)
        reconstructed[0::2] = approximation + zeros
        reconstructed[1::2] = approximation - zeros
        approximation = reconstructed
    return cast(NDArray[np.float64], approximation.astype(np.float64, copy=False))


def _component_direction_continuity(component: pd.Series) -> float | None:
    changes = component.dropna().diff().dropna()
    changes = cast(pd.Series, changes[changes != 0.0])
    if len(changes) < 2:
        return None
    signs = np.sign(changes.to_numpy(dtype=float))
    switch_count = int((signs[1:] != signs[:-1]).sum())
    opportunities = len(signs) - 1
    return 100.0 * (1.0 - switch_count / opportunities)


def _lag_quality(
    raw_returns: pd.Series, filtered: pd.Series, max_lag: int = 20
) -> tuple[int | None, float | None, float | None, float | None]:
    filtered_returns = filtered.diff().dropna()
    common_index = raw_returns.index.intersection(filtered_returns.index)
    if len(common_index) < 10:
        return None, None, None, None
    base = raw_returns.loc[common_index]
    current = filtered_returns.loc[common_index]
    same_corr = _safe_corr(base, current)
    best_lag = 0
    best_corr = same_corr if same_corr is not None else -math.inf
    for lag in range(1, max_lag + 1):
        shifted = base.shift(lag).dropna()
        lag_index = shifted.index.intersection(current.index)
        if len(lag_index) < 10:
            continue
        corr = _safe_corr(shifted.loc[lag_index], current.loc[lag_index])
        if corr is not None and corr > best_corr:
            best_lag = lag
            best_corr = corr
    base_std = float(base.std())
    retention = float(current.std() / base_std) if base_std > 0.0 else None
    return (
        best_lag,
        (best_corr if math.isfinite(best_corr) else None),
        same_corr,
        retention,
    )


def _safe_corr(left: pd.Series, right: pd.Series) -> float | None:
    corr = float(left.corr(right))
    return corr if math.isfinite(corr) else None


def _annualized_return(nav: pd.Series, *, bars_per_year: float) -> float:
    if len(nav) < 2:
        return 0.0
    years = len(nav) / bars_per_year
    if years <= 0.0:
        return 0.0
    return float(nav.iloc[-1] ** (1.0 / years) - 1.0)


def _max_drawdown_duration(nav: pd.Series) -> int:
    running_peak = nav.cummax()
    underwater = nav < running_peak
    longest = current = 0
    for is_underwater in underwater:
        current = current + 1 if bool(is_underwater) else 0
        longest = max(longest, current)
    return longest


def _position_change_intervals(position: pd.Series) -> NDArray[np.int64]:
    changes = position.diff().abs().fillna(0.0)
    change_locations = np.flatnonzero(changes.to_numpy(dtype=float) > 0.0)
    if len(change_locations) < 2:
        return np.array([], dtype=np.int64)
    return cast(NDArray[np.int64], np.diff(change_locations))


def _series_date_label(series: pd.Series, *, boundary: Literal["min", "max"]) -> str:
    raw_value = series.index.min() if boundary == "min" else series.index.max()
    return str(pd.Timestamp(str(raw_value)).date())


def _positive_int(params: Mapping[str, float | int], key: str) -> int:
    raw = params.get(key)
    value = int(raw) if raw is not None else 0
    if value <= 0:
        raise ValueError(f"{key} must be > 0")
    return value


def _positive_float(params: Mapping[str, float | int], key: str) -> float:
    raw = params.get(key)
    value = float(raw) if raw is not None else 0.0
    if value <= 0.0 or not math.isfinite(value):
        raise ValueError(f"{key} must be finite and > 0")
    return value
