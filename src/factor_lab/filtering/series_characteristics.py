# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportMissingTypeStubs=false
"""Time-series characteristic profiling before filter/timing research.

This module is the governed preflight step for the filtering workflow chain.
It inspects a standardized timestamp/close series and answers a narrower
question than a backtest: what kind of structure does this series expose at
each requested bar period?  The output guides method choice before filter
parameter selection, tool battle, and strategy construction.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Literal, cast

import numpy as np
import pandas as pd

from factor_lab.filtering.timing_validation import (
    PERIOD_ANNUALIZATION_BARS,
    PeriodName,
    TimingValidationConfig,
    resample_close_frame,
)
from factor_lab.indicators.bar_direction_continuity import (
    compute_bar_direction_continuity,
)

CharacteristicStatus = Literal["completed", "skipped"]
CharacteristicUseCategory = Literal[
    "cycle",
    "trend",
    "mean_reversion",
    "non_direct",
]

USE_CATEGORY_LABELS: dict[CharacteristicUseCategory, str] = {
    "cycle": "适合做周期",
    "trend": "适合做趋势",
    "mean_reversion": "适合做震荡（反向）",
    "non_direct": "非直接交易策略内容",
}

DIRECT_GATE_THRESHOLDS: dict[CharacteristicUseCategory, float] = {
    "cycle": 8.0,
    "trend": 52.0,
    "mean_reversion": -0.03,
    "non_direct": 0.0,
}

LAG1_RETURN_AUTOCORR_TREND_THRESHOLD = 0.03
LAG1_RETURN_AUTOCORR_MEAN_REVERSION_THRESHOLD = DIRECT_GATE_THRESHOLDS["mean_reversion"]


@dataclass(frozen=True, slots=True)
class CharacteristicWindowPolicy:
    """Default window policy for stability sampling at one bar period."""

    period: str
    window_bars: int
    step_bars: int
    min_window_bars: int
    description: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


DEFAULT_CHARACTERISTIC_WINDOW_POLICIES: dict[str, CharacteristicWindowPolicy] = {
    "week": CharacteristicWindowPolicy(
        "week",
        window_bars=156,
        step_bars=52,
        min_window_bars=104,
        description="约3年周线窗口，逐年滚动。",
    ),
    "day": CharacteristicWindowPolicy(
        "day",
        window_bars=732,
        step_bars=244,
        min_window_bars=500,
        description="约3年日线窗口，逐年滚动。",
    ),
    "60min": CharacteristicWindowPolicy(
        "60min",
        window_bars=976,
        step_bars=488,
        min_window_bars=600,
        description="约1年小时线窗口，半年滚动。",
    ),
    "30min": CharacteristicWindowPolicy(
        "30min",
        window_bars=976,
        step_bars=488,
        min_window_bars=600,
        description="约半年30分钟窗口，季度滚动。",
    ),
    "15min": CharacteristicWindowPolicy(
        "15min",
        window_bars=976,
        step_bars=976,
        min_window_bars=600,
        description="约3个月15分钟窗口，分段采样。",
    ),
    "5min": CharacteristicWindowPolicy(
        "5min",
        window_bars=2400,
        step_bars=2400,
        min_window_bars=1200,
        description="约50个交易日5分钟窗口，分段采样。",
    ),
    "1min": CharacteristicWindowPolicy(
        "1min",
        window_bars=7200,
        step_bars=7200,
        min_window_bars=3600,
        description="约30个交易日1分钟窗口，分段采样。",
    ),
}


@dataclass(frozen=True, slots=True)
class TimeSeriesCharacteristicConfig:
    """Configuration for a multi-period time-series health check."""

    periods: tuple[PeriodName, ...] = (
        "week",
        "day",
        "60min",
        "30min",
        "15min",
        "5min",
        "1min",
    )
    timestamp_column: str = "timestamp"
    close_column: str = "close"
    min_observations: int = 80
    max_autocorr_lag: int = 20
    variance_ratio_lags: tuple[int, ...] = (2, 4, 8, 16)
    hurst_lags: tuple[int, ...] = (2, 4, 8, 16, 32)
    top_frequency_count: int = 3
    use_period_specific_windows: bool = True
    max_windows_per_period: int = 40

    def __post_init__(self) -> None:
        if not self.periods:
            raise ValueError("periods must not be empty")
        if self.min_observations < 20:
            raise ValueError("min_observations must be >= 20")
        if self.max_autocorr_lag < 1:
            raise ValueError("max_autocorr_lag must be >= 1")
        if self.top_frequency_count <= 0:
            raise ValueError("top_frequency_count must be > 0")
        if self.max_windows_per_period <= 0:
            raise ValueError("max_windows_per_period must be > 0")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CharacteristicScore:
    """One normalized characteristic score in [0, 100]."""

    name: str
    score: float
    strength: str
    interpretation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DominantCycle:
    """A spectral peak candidate used only as descriptive evidence."""

    rank: int
    period_bars: float
    period_days_equiv: float
    power_share: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CharacteristicUseGate:
    """Single decisive initial-screen gate for one direct research route."""

    category: CharacteristicUseCategory
    label: str
    metric: str
    value: float
    threshold: float
    operator: str
    passed: bool
    interpretation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CharacteristicWindowResult:
    """One sub-sample characteristic profile for stability checking."""

    window_index: int
    sample_start: str | None
    sample_end: str | None
    sample_count: int
    scores: dict[str, float]
    primary_method: str
    candidate_categories: list[CharacteristicUseCategory]
    candidate_category_labels: list[str]
    use_category: CharacteristicUseCategory
    use_category_label: str
    recommended_use: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TimeSeriesCharacteristicPeriodResult:
    """Characteristic profile for one bar period."""

    period: str
    status: CharacteristicStatus
    sample_start: str | None
    sample_end: str | None
    sample_count: int
    scores: list[CharacteristicScore]
    metrics: dict[str, object]
    dominant_cycles: list[DominantCycle]
    method_recommendations: list[str]
    direct_use_gates: list[CharacteristicUseGate]
    candidate_categories: list[CharacteristicUseCategory]
    candidate_category_labels: list[str]
    use_category: CharacteristicUseCategory
    use_category_label: str
    recommended_use: str
    unsuitable_for: list[str]
    stability: dict[str, object]
    windows: list[CharacteristicWindowResult]
    caveats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "period": self.period,
            "status": self.status,
            "sample_start": self.sample_start,
            "sample_end": self.sample_end,
            "sample_count": self.sample_count,
            "scores": [item.to_dict() for item in self.scores],
            "metrics": self.metrics,
            "dominant_cycles": [item.to_dict() for item in self.dominant_cycles],
            "method_recommendations": self.method_recommendations,
            "direct_use_gates": [item.to_dict() for item in self.direct_use_gates],
            "candidate_categories": list(self.candidate_categories),
            "candidate_category_labels": list(self.candidate_category_labels),
            "use_category": self.use_category,
            "use_category_label": self.use_category_label,
            "recommended_use": self.recommended_use,
            "unsuitable_for": self.unsuitable_for,
            "stability": self.stability,
            "windows": [item.to_dict() for item in self.windows],
            "caveats": self.caveats,
        }


@dataclass(frozen=True, slots=True)
class TimeSeriesCharacteristicWorkflowResult:
    """Preflight workflow artifact for one index/portfolio series."""

    index_ref: str
    periods: list[TimeSeriesCharacteristicPeriodResult]
    summary: dict[str, object]
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "index_ref": self.index_ref,
            "periods": [item.to_dict() for item in self.periods],
            "summary": self.summary,
            "metadata": self.metadata,
        }


def run_time_series_characteristics_workflow(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    index_ref: str = "index_series",
    config: TimeSeriesCharacteristicConfig | None = None,
) -> TimeSeriesCharacteristicWorkflowResult:
    """Profile trend, cycle, randomness and regime features by bar period."""

    cfg = config or TimeSeriesCharacteristicConfig()
    period_results = [
        _profile_period(rows, period=period, config=cfg) for period in cfg.periods
    ]
    completed = [item for item in period_results if item.status == "completed"]
    return TimeSeriesCharacteristicWorkflowResult(
        index_ref=index_ref,
        periods=period_results,
        summary=_summary(completed),
        metadata={
            "workflow_role": "time_series_characteristics_workflow",
            "workflow_position": "preflight_before_filter_parameter_workflow",
            "index_ref": index_ref,
            "periods_requested": list(cfg.periods),
            "periods_completed": [item.period for item in completed],
            "window_policy": {
                period: DEFAULT_CHARACTERISTIC_WINDOW_POLICIES[period].to_dict()
                for period in DEFAULT_CHARACTERISTIC_WINDOW_POLICIES
                if period in cfg.periods
            },
            "use_category_universe": dict(USE_CATEGORY_LABELS),
            "direct_initial_screen_policy": {
                "cycle": {
                    "metric": "spectral_top3_concentration_ratio",
                    "operator": ">=",
                    "threshold": DIRECT_GATE_THRESHOLDS["cycle"],
                },
                "trend": {
                    "operator": "any",
                    "gates": [
                        {
                            "metric": "bdci",
                            "operator": ">=",
                            "threshold": DIRECT_GATE_THRESHOLDS["trend"],
                            "role": "sign_direction_continuity",
                        },
                        {
                            "metric": "return_autocorr_lag1",
                            "operator": ">=",
                            "threshold": LAG1_RETURN_AUTOCORR_TREND_THRESHOLD,
                            "role": "signed_return_persistence",
                        },
                    ],
                },
                "mean_reversion": {
                    "metric": "return_autocorr_lag1",
                    "operator": "<=",
                    "threshold": LAG1_RETURN_AUTOCORR_MEAN_REVERSION_THRESHOLD,
                },
            },
            "lag1_return_autocorr_policy": {
                "metric": "return_autocorr_lag1",
                "formula": "corr(r_t, r_{t-1})",
                "trend_threshold": LAG1_RETURN_AUTOCORR_TREND_THRESHOLD,
                "mean_reversion_threshold": (
                    LAG1_RETURN_AUTOCORR_MEAN_REVERSION_THRESHOLD
                ),
                "role_zh": (
                    "一阶收益自相关是收益序列的有符号线性延续/反转证据；"
                    "它比BDCI更重视收益幅度，可作为趋势初筛的替代放行门，"
                    "也继续作为震荡/反向初筛的决定性指标。"
                ),
            },
            "max_windows_per_period": cfg.max_windows_per_period,
            "factor_lifecycle_mutation": False,
            "strategy_lifecycle_mutation": False,
            "lookahead_policy": "descriptive_current_and_past_sample_only_no_backtest",
            "score_scale": "0_to_100_higher_means_characteristic_more_visible",
            "governance_boundary": (
                "This preflight stage selects method families from descriptive "
                "series structure and multi-window stability; it must not tune "
                "frequency parameters or strategy rules by backtest return."
            ),
        },
    )


def render_time_series_characteristics_markdown(
    result: TimeSeriesCharacteristicWorkflowResult,
) -> str:
    """Render a Chinese Markdown report from a characteristic artifact."""

    lines = [
        f"# {result.index_ref} 时间序列特性体检报告",
        "",
        "本报告位于滤波/择时研究链路最前置阶段：先判断序列特性，"
        "再选择处理方法、滤波工具和策略模板。它不读取回测收益，"
        "也不会创建因子或策略。",
        "",
        "## 总览",
        "",
        (
            "| 周期 | 样本 | 窗口 | 初筛候选 | 趋势 | 均值回复/震荡 | 周期 | 随机 | "
            "波动聚集 | 结构切换 | 明确建议 |"
        ),
        "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in result.periods:
        if item.status != "completed":
            lines.append(
                f"| {item.period} | {item.sample_count} | 0 | "
                f"{item.use_category_label} | - | - | - | - | - | - | "
                f"{'; '.join(item.caveats) or '样本不足'} |"
            )
            continue
        scores = _score_map(item)
        lines.append(
            f"| {item.period} | {item.sample_count} | "
            f"{int(item.stability.get('window_count') or 0)} | "
            f"{_candidate_label_text(item)} | "
            f"{scores['trend']:.1f} | {scores['mean_reversion']:.1f} | "
            f"{scores['cycle']:.1f} | {scores['randomness']:.1f} | "
            f"{scores['volatility_clustering']:.1f} | "
            f"{scores['regime_shift']:.1f} | {item.recommended_use} |"
        )
    lines.extend(["", "## 分周期细节", ""])
    for item in result.periods:
        lines.extend(_period_markdown(item))
    lines.extend(
        [
            "",
            "## 评分口径",
            "",
            "- 趋势性：BDCI、Hurst、方差比和收益自相关共同衡量方向延续；"
            "其中 BDCI 与 lag1 正收益自相关是趋势初筛的两条并列放行门。",
            "- 均值回复/震荡性：lag1 负收益自相关、Hurst<0.5、方差比<1"
            "和方向切换共同衡量；lag1 负收益自相关继续作为反向初筛门。",
            "- 周期性：频谱能量集中度、频谱熵和主峰功率占比共同衡量。",
            "- 随机性：Hurst≈0.5、方差比≈1、收益自相关弱、"
            "runs test 接近随机、频谱熵高共同衡量。",
            "- 波动聚集：绝对收益/平方收益自相关衡量高低波动状态是否延续。",
            "- 跳跃厚尾：峰度、尾部比率和最大标准化跳动衡量极端风险。",
            "- 结构切换：滚动均值/滚动波动率离散度衡量参数是否漂移。",
        ]
    )
    return "\n".join(lines) + "\n"


def _profile_period(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    period: PeriodName,
    config: TimeSeriesCharacteristicConfig,
) -> TimeSeriesCharacteristicPeriodResult:
    close = resample_close_frame(
        rows,
        config=TimingValidationConfig(
            period=period,
            timestamp_column=config.timestamp_column,
            close_column=config.close_column,
            min_observations=3,
        ),
    )
    if len(close) < config.min_observations:
        return TimeSeriesCharacteristicPeriodResult(
            period=period,
            status="skipped",
            sample_start=_date_label(close, "min"),
            sample_end=_date_label(close, "max"),
            sample_count=len(close),
            scores=[],
            metrics={},
            dominant_cycles=[],
            method_recommendations=[],
            direct_use_gates=[],
            candidate_categories=[],
            candidate_category_labels=[],
            use_category="non_direct",
            use_category_label=USE_CATEGORY_LABELS["non_direct"],
            recommended_use="不适合判断：样本不足。",
            unsuitable_for=["任何需要统计稳定性的择时判断"],
            stability={
                "window_count": 0,
                "stability_grade": "insufficient_sample",
            },
            windows=[],
            caveats=[f"样本数低于 min_observations={config.min_observations}"],
        )
    metrics, cycles, scores = _profile_close(close, period=period, config=config)
    windows = _window_profiles(close, period=period, config=config)
    stability = _window_stability(
        windows,
        period=period,
        policy=_window_policy(period, config),
    )
    direct_use_gates = _direct_use_gates(metrics)
    candidate_categories = _candidate_categories(direct_use_gates)
    use_category = _primary_use_category(candidate_categories)
    recommended_use, unsuitable_for = _direct_initial_screen_recommendation(
        direct_use_gates,
        metrics=metrics,
        stability=stability,
    )
    scores = _scores(metrics)
    recommendations, caveats = _recommend(
        scores,
        metrics,
        period=period,
        stability=stability,
        recommended_use=recommended_use,
    )
    return TimeSeriesCharacteristicPeriodResult(
        period=period,
        status="completed",
        sample_start=_date_label(close, "min"),
        sample_end=_date_label(close, "max"),
        sample_count=len(close),
        scores=scores,
        metrics=metrics,
        dominant_cycles=cycles,
        method_recommendations=recommendations,
        direct_use_gates=direct_use_gates,
        candidate_categories=candidate_categories,
        candidate_category_labels=[
            USE_CATEGORY_LABELS[category] for category in candidate_categories
        ],
        use_category=use_category,
        use_category_label=USE_CATEGORY_LABELS[use_category],
        recommended_use=recommended_use,
        unsuitable_for=unsuitable_for,
        stability=stability,
        windows=windows,
        caveats=caveats,
    )


def _profile_close(
    close: pd.Series,
    *,
    period: PeriodName,
    config: TimeSeriesCharacteristicConfig,
) -> tuple[dict[str, object], list[DominantCycle], list[CharacteristicScore]]:
    log_close = pd.Series(np.log(close.to_numpy(dtype=np.float64)), index=close.index)
    returns = cast(pd.Series, log_close.diff().dropna())
    metrics, cycles = _metrics(
        close=close,
        log_close=log_close,
        returns=returns,
        period=period,
        config=config,
    )
    scores = _scores(metrics)
    return metrics, cycles, scores


def _window_profiles(
    close: pd.Series,
    *,
    period: PeriodName,
    config: TimeSeriesCharacteristicConfig,
) -> list[CharacteristicWindowResult]:
    policy = _window_policy(period, config)
    if len(close) < policy.min_window_bars:
        return []
    window_bars = min(policy.window_bars, len(close))
    step_bars = max(1, policy.step_bars)
    starts = list(range(0, max(1, len(close) - window_bars + 1), step_bars))
    last_start = max(0, len(close) - window_bars)
    if not starts or starts[-1] != last_start:
        starts.append(last_start)
    if len(starts) > config.max_windows_per_period:
        indices = np.linspace(
            0,
            len(starts) - 1,
            num=config.max_windows_per_period,
            dtype=int,
        )
        starts = [starts[index] for index in sorted(set(indices.tolist()))]

    windows: list[CharacteristicWindowResult] = []
    for window_index, start in enumerate(starts, start=1):
        sample = close.iloc[start : start + window_bars]
        if len(sample) < policy.min_window_bars:
            continue
        metrics, _, scores = _profile_close(sample, period=period, config=config)
        score_map = {item.name: item.score for item in scores}
        direct_use_gates = _direct_use_gates(metrics)
        candidate_categories = _candidate_categories(direct_use_gates)
        use_category = _primary_use_category(candidate_categories)
        primary_method = _candidate_method_family(candidate_categories)
        recommended_use, _ = _direct_initial_screen_recommendation(
            direct_use_gates,
            metrics=metrics,
            stability={"stability_grade": "single_window"},
        )
        windows.append(
            CharacteristicWindowResult(
                window_index=window_index,
                sample_start=_date_label(sample, "min"),
                sample_end=_date_label(sample, "max"),
                sample_count=len(sample),
                scores=score_map,
                primary_method=primary_method,
                candidate_categories=candidate_categories,
                candidate_category_labels=[
                    USE_CATEGORY_LABELS[category] for category in candidate_categories
                ],
                use_category=use_category,
                use_category_label=USE_CATEGORY_LABELS[use_category],
                recommended_use=recommended_use,
            )
        )
    return windows


def _window_policy(
    period: str,
    config: TimeSeriesCharacteristicConfig,
) -> CharacteristicWindowPolicy:
    if config.use_period_specific_windows:
        return DEFAULT_CHARACTERISTIC_WINDOW_POLICIES[period]
    window_bars = max(config.min_observations * 3, 120)
    return CharacteristicWindowPolicy(
        period=period,
        window_bars=window_bars,
        step_bars=max(config.min_observations, window_bars // 2),
        min_window_bars=config.min_observations,
        description="全周期统一窗口；仅用于复现实验。",
    )


def _window_stability(
    windows: Sequence[CharacteristicWindowResult],
    *,
    period: str,
    policy: CharacteristicWindowPolicy,
) -> dict[str, object]:
    if not windows:
        return {
            "period": period,
            "window_count": 0,
            "window_policy": policy.to_dict(),
            "stability_grade": "insufficient_windows",
            "score_median": {},
            "score_iqr": {},
            "strong_or_medium_share": {},
            "primary_method_counts": {},
            "primary_method": "insufficient_windows",
            "primary_method_share": 0.0,
        }
    names = sorted(windows[0].scores)
    score_median = {
        name: float(np.median([window.scores[name] for window in windows]))
        for name in names
    }
    score_iqr = {
        name: float(
            np.quantile([window.scores[name] for window in windows], 0.75)
            - np.quantile([window.scores[name] for window in windows], 0.25)
        )
        for name in names
    }
    strong_or_medium_share = {
        name: float(np.mean([window.scores[name] >= 45.0 for window in windows]))
        for name in names
    }
    counts: dict[str, int] = {}
    for window in windows:
        counts[window.primary_method] = counts.get(window.primary_method, 0) + 1
    primary_method = max(counts, key=counts.__getitem__)
    primary_share = counts[primary_method] / len(windows)
    if len(windows) < 3:
        grade = "weak_evidence"
    elif primary_share >= 0.67:
        grade = "stable"
    elif primary_share >= 0.45:
        grade = "mixed_but_usable"
    else:
        grade = "unstable"
    return {
        "period": period,
        "window_count": len(windows),
        "window_policy": policy.to_dict(),
        "stability_grade": grade,
        "score_median": {key: round(value, 6) for key, value in score_median.items()},
        "score_iqr": {key: round(value, 6) for key, value in score_iqr.items()},
        "strong_or_medium_share": {
            key: round(value, 6) for key, value in strong_or_medium_share.items()
        },
        "primary_method_counts": counts,
        "primary_method": primary_method,
        "primary_method_share": round(primary_share, 6),
    }


def _metrics(
    *,
    close: pd.Series,
    log_close: pd.Series,
    returns: pd.Series,
    period: PeriodName,
    config: TimeSeriesCharacteristicConfig,
) -> tuple[dict[str, object], list[DominantCycle]]:
    acf = _autocorrelations(returns, config.max_autocorr_lag)
    abs_acf = _autocorrelations(returns.abs(), config.max_autocorr_lag)
    squared_acf = _autocorrelations(returns * returns, config.max_autocorr_lag)
    variance_ratios = {
        str(lag): _variance_ratio(returns, lag)
        for lag in config.variance_ratio_lags
        if lag < len(returns) // 2
    }
    hurst = _hurst_exponent(log_close, config.hurst_lags)
    spectral = _spectral_metrics(returns, period=period, config=config)
    rolling = _rolling_regime_metrics(returns)
    runs_z = _runs_zscore(returns)
    bdci = compute_bar_direction_continuity(close.tolist()).score
    lag1_return_autocorr = acf.get("1")
    metrics: dict[str, object] = {
        "bdci": bdci,
        "hurst": hurst,
        "variance_ratios": variance_ratios,
        "variance_ratio_mean": _finite_mean(variance_ratios.values()),
        "return_autocorr_lag1": lag1_return_autocorr,
        "return_autocorr_lag1_regime": _lag1_return_autocorr_regime(
            lag1_return_autocorr
        ),
        "return_autocorr_mean": _finite_mean(acf.values()),
        "return_abs_autocorr_mean": _finite_mean(abs_acf.values()),
        "return_squared_autocorr_mean": _finite_mean(squared_acf.values()),
        "runs_zscore": runs_z,
        "spectral_entropy": spectral["spectral_entropy"],
        "spectral_top_power_share": spectral["spectral_top_power_share"],
        "spectral_top3_power_share": spectral["spectral_top3_power_share"],
        "spectral_top_power_concentration_ratio": spectral[
            "spectral_top_power_concentration_ratio"
        ],
        "spectral_top3_concentration_ratio": spectral[
            "spectral_top3_concentration_ratio"
        ],
        "spectral_positive_frequency_count": spectral[
            "spectral_positive_frequency_count"
        ],
        "dominant_period_bars": spectral["dominant_period_bars"],
        "dominant_period_days_equiv": spectral["dominant_period_days_equiv"],
        "annualized_volatility": float(
            returns.std() * math.sqrt(PERIOD_ANNUALIZATION_BARS[period])
        ),
        "skew": _skew(returns),
        "excess_kurtosis": _excess_kurtosis(returns),
        "tail_ratio_99_95": _tail_ratio(returns),
        "max_abs_return_zscore": _max_abs_zscore(returns),
        "zero_return_share": float((returns.abs() < 1e-12).mean()),
        "directional_drift_tstat": _drift_tstat(returns),
        "rolling_mean_dispersion": rolling["rolling_mean_dispersion"],
        "rolling_volatility_cv": rolling["rolling_volatility_cv"],
        "sample_return_mean": float(returns.mean()),
        "sample_return_std": float(returns.std()),
    }
    return metrics, cast(list[DominantCycle], spectral["dominant_cycles"])


def _scores(metrics: Mapping[str, object]) -> list[CharacteristicScore]:
    bdci = _float(metrics.get("bdci"), 50.0)
    hurst = _float(metrics.get("hurst"), 0.5)
    vr = _float(metrics.get("variance_ratio_mean"), 1.0)
    acf1 = _float(metrics.get("return_autocorr_lag1"), 0.0)
    acf_abs = abs(_float(metrics.get("return_autocorr_mean"), 0.0))
    drift_tstat = abs(_float(metrics.get("directional_drift_tstat"), 0.0))
    runs_z = abs(_float(metrics.get("runs_zscore"), 0.0))
    entropy = _float(metrics.get("spectral_entropy"), 1.0)
    top_share = _float(metrics.get("spectral_top_power_share"), 0.0)
    top3_share = _float(metrics.get("spectral_top3_power_share"), 0.0)
    abs_vol_acf = _float(metrics.get("return_abs_autocorr_mean"), 0.0)
    squared_vol_acf = _float(metrics.get("return_squared_autocorr_mean"), 0.0)
    kurt = _float(metrics.get("excess_kurtosis"), 0.0)
    tail_ratio = _float(metrics.get("tail_ratio_99_95"), 1.0)
    max_z = _float(metrics.get("max_abs_return_zscore"), 0.0)
    rolling_mean_dispersion = _float(metrics.get("rolling_mean_dispersion"), 0.0)
    rolling_vol_cv = _float(metrics.get("rolling_volatility_cv"), 0.0)
    zero_share = _float(metrics.get("zero_return_share"), 0.0)

    bdci_trend = _scale((bdci - 50.0) / 25.0)
    drift_trend = _scale(drift_tstat / 3.0)
    trend = max(
        _mean_score(
            bdci_trend,
            _scale((hurst - 0.50) / 0.20),
            _scale((vr - 1.0) / 0.50),
            _scale(acf1 / 0.12),
        ),
        100.0 * (0.45 * bdci_trend + 0.55 * drift_trend),
    )
    mean_reversion = _mean_score(
        _scale((50.0 - bdci) / 25.0),
        _scale((0.50 - hurst) / 0.20),
        _scale((1.0 - vr) / 0.40),
        _scale((-acf1) / 0.12),
    ) * (1.0 - 0.40 * bdci_trend)
    cycle = _mean_score(
        _scale(top_share / 0.20),
        _scale(top3_share / 0.45),
        _scale((0.90 - entropy) / 0.35),
    )
    randomness = _mean_score(
        _scale(1.0 - abs(hurst - 0.50) / 0.20),
        _scale(1.0 - abs(vr - 1.0) / 0.35),
        _scale(1.0 - acf_abs / 0.12),
        _scale(1.0 - runs_z / 2.0),
        _scale(entropy),
    )
    volatility_clustering = _mean_score(
        _scale(abs_vol_acf / 0.18),
        _scale(squared_vol_acf / 0.18),
    )
    jump_tail = _mean_score(
        _scale(kurt / 8.0),
        _scale((tail_ratio - 1.0) / 2.5),
        _scale((max_z - 3.0) / 5.0),
    )
    regime_shift = _mean_score(
        _scale(rolling_mean_dispersion / 1.5),
        _scale(rolling_vol_cv / 0.75),
    )
    microstructure_noise = _mean_score(
        _scale(zero_share / 0.15),
        _scale((-acf1) / 0.18),
        _scale((runs_z - 1.0) / 2.0),
    )
    raw = {
        "trend": (
            trend,
            "趋势性",
            "方向延续越明显，越适合低通趋势、突破或大周期方向门禁。",
        ),
        "mean_reversion": (
            mean_reversion,
            "均值回复/震荡性",
            "偏离中心后越容易回摆，越适合 z-score、布林带或区间策略。",
        ),
        "cycle": (
            cycle,
            "周期性",
            "频谱能量越集中，越适合先找频段再做带通/低通滤波。",
        ),
        "randomness": (
            randomness,
            "随机性",
            "越接近随机游走，越不应强行用价格本身做择时。",
        ),
        "volatility_clustering": (
            volatility_clustering,
            "波动率聚集",
            "高低波动状态越延续，越需要波动率目标仓位和动态阈值。",
        ),
        "jump_tail": (
            jump_tail,
            "跳跃/厚尾风险",
            "极端跳变越强，越需要保守杠杆、gap-aware 回测和鲁棒风控。",
        ),
        "regime_shift": (
            regime_shift,
            "结构切换/非平稳",
            "参数漂移越强，越需要 walk-forward、自适应或分 regime 处理。",
        ),
        "microstructure_noise": (
            microstructure_noise,
            "微观结构噪声",
            "短周期噪声越强，越应降频、合并信号或只做入场微调。",
        ),
    }
    return [
        CharacteristicScore(
            name=name,
            score=float(round(score, 6)),
            strength=_strength(score),
            interpretation=interpretation,
        )
        for name, (score, _label, interpretation) in raw.items()
    ]


def _recommend(
    scores: Sequence[CharacteristicScore],
    metrics: Mapping[str, object],
    *,
    period: str,
    stability: Mapping[str, object],
    recommended_use: str,
) -> tuple[list[str], list[str]]:
    score_map = {item.name: item.score for item in scores}
    recommendations: list[str] = [f"明确结论：{recommended_use}"]
    caveats: list[str] = []
    grade = str(stability.get("stability_grade") or "unknown")
    window_count = int(stability.get("window_count") or 0)
    if window_count >= 2:
        recommendations.append(
            f"稳定性证据：{window_count} 个子区间，稳定性评级 {grade}。"
        )
    if (
        score_map["randomness"] >= 70
        and max(
            score_map["trend"],
            score_map["cycle"],
            score_map["mean_reversion"],
        )
        < 45
    ):
        recommendations.append(
            "补充风险：随机性占优；不否决初筛，但后续需要更严格样本外验证。"
        )
    if score_map["trend"] >= 55:
        recommendations.append("趋势性可见：优先低通趋势、突破或大周期方向门禁。")
    if score_map["mean_reversion"] >= 55:
        recommendations.append("均值回复可见：优先 z-score、布林带、区间高抛低吸。")
    if score_map["cycle"] >= 55:
        recommendations.append(
            "周期性可见：先用单位机会密度定频段，再比较 IIR/Fourier/小波带通。"
        )
    if score_map["volatility_clustering"] >= 55:
        recommendations.append("波动率聚集明显：所有策略应加波动率仓位或动态阈值。")
    if score_map["regime_shift"] >= 55:
        recommendations.append(
            "结构切换明显：正式调参必须 walk-forward，避免固定全样本参数。"
        )
    if score_map["microstructure_noise"] >= 55:
        recommendations.append("短周期噪声明显：后续需要成交成本、延迟和滑点验证。")
    if period in {"1min", "5min", "15min"} and score_map["microstructure_noise"] >= 45:
        caveats.append("分钟级结果对成交成本、撮合延迟和停牌/缺口更敏感。")
    if grade in {"unstable", "weak_evidence", "insufficient_windows"}:
        caveats.append("子区间稳定性证据不足，不能直接固化单一处理方法。")
    if _float(metrics.get("sample_return_std"), 0.0) <= 0.0:
        caveats.append("收益标准差为0，特性评分可能无意义。")
    return recommendations, caveats


def _direct_use_gates(
    metrics: Mapping[str, object],
) -> list[CharacteristicUseGate]:
    cycle_value = _float(metrics.get("spectral_top3_concentration_ratio"), 0.0)
    bdci_trend_value = _float(metrics.get("bdci"), 50.0)
    lag1_value = _float(metrics.get("return_autocorr_lag1"), 0.0)
    return [
        CharacteristicUseGate(
            category="cycle",
            label=USE_CATEGORY_LABELS["cycle"],
            metric="spectral_top3_concentration_ratio",
            value=round(cycle_value, 6),
            threshold=DIRECT_GATE_THRESHOLDS["cycle"],
            operator=">=",
            passed=cycle_value >= DIRECT_GATE_THRESHOLDS["cycle"],
            interpretation=(
                "前三主频能量相对均匀频谱的集中倍数；越高越值得进入周期/"
                "带通/单位机会密度研究。"
            ),
        ),
        CharacteristicUseGate(
            category="trend",
            label=USE_CATEGORY_LABELS["trend"],
            metric="bdci",
            value=round(bdci_trend_value, 6),
            threshold=DIRECT_GATE_THRESHOLDS["trend"],
            operator=">=",
            passed=bdci_trend_value >= DIRECT_GATE_THRESHOLDS["trend"],
            interpretation=(
                "K线方向连续度；50附近近似随机，超过门槛说明方向延续有初筛希望。"
            ),
        ),
        CharacteristicUseGate(
            category="trend",
            label=USE_CATEGORY_LABELS["trend"],
            metric="return_autocorr_lag1",
            value=round(lag1_value, 6),
            threshold=LAG1_RETURN_AUTOCORR_TREND_THRESHOLD,
            operator=">=",
            passed=lag1_value >= LAG1_RETURN_AUTOCORR_TREND_THRESHOLD,
            interpretation=(
                "一阶收益自相关；足够为正说明收益方向和幅度存在线性延续，"
                "可作为BDCI之外的趋势初筛放行证据。"
            ),
        ),
        CharacteristicUseGate(
            category="mean_reversion",
            label=USE_CATEGORY_LABELS["mean_reversion"],
            metric="return_autocorr_lag1",
            value=round(lag1_value, 6),
            threshold=LAG1_RETURN_AUTOCORR_MEAN_REVERSION_THRESHOLD,
            operator="<=",
            passed=lag1_value <= LAG1_RETURN_AUTOCORR_MEAN_REVERSION_THRESHOLD,
            interpretation=(
                "一阶收益自相关；足够为负说明上一根方向更容易被下一根反向修正。"
            ),
        ),
    ]


def _candidate_categories(
    gates: Sequence[CharacteristicUseGate],
) -> list[CharacteristicUseCategory]:
    categories: list[CharacteristicUseCategory] = []
    for gate in gates:
        if gate.passed and gate.category not in categories:
            categories.append(gate.category)
    return categories


def _primary_use_category(
    candidates: Sequence[CharacteristicUseCategory],
) -> CharacteristicUseCategory:
    for category in ("trend", "mean_reversion", "cycle"):
        if category in candidates:
            return category
    return "non_direct"


def _candidate_method_family(
    candidates: Sequence[CharacteristicUseCategory],
) -> str:
    if not candidates:
        return "non_direct_initial_screen"
    if len(candidates) > 1:
        return "multi_direct_initial_screen"
    return f"{candidates[0]}_initial_screen"


def _direct_initial_screen_recommendation(
    gates: Sequence[CharacteristicUseGate],
    *,
    metrics: Mapping[str, object],
    stability: Mapping[str, object],
) -> tuple[str, list[str]]:
    candidates = _candidate_categories(gates)
    unsuitable: list[str] = []
    if candidates:
        labels = "、".join(USE_CATEGORY_LABELS[category] for category in candidates)
        use = (
            f"通过直接路线初筛：{labels}。这只是研究路线放行，"
            "不代表已经形成可交易策略。"
        )
    else:
        use = (
            "未通过周期/趋势/震荡（反向）的直接路线初筛；归入非直接交易策略内容，"
            "只适合观察、风控、过滤或等待新证据。"
        )
        unsuitable.extend(["独立周期策略", "独立趋势策略", "独立反向策略"])

    risk_notes: list[str] = []
    score_map = {score.name: score.score for score in _scores(metrics)}
    if score_map["volatility_clustering"] >= 55:
        risk_notes.append("波动率聚集高，后续必须做仓位/阈值管理")
    if score_map["jump_tail"] >= 70:
        risk_notes.append("厚尾跳跃风险高，后续必须做成本、缺口和回撤验证")
    grade = str(stability.get("stability_grade") or "")
    if grade in {"unstable", "weak_evidence", "insufficient_windows"}:
        risk_notes.append("子区间稳定性不足，后续只能作为探索候选")
    if risk_notes:
        use = f"{use} 风险提示：{'；'.join(risk_notes)}。"
    return use, unsuitable


def _summary(
    completed: Sequence[TimeSeriesCharacteristicPeriodResult],
) -> dict[str, object]:
    if not completed:
        return {
            "primary_periods": [],
            "dominant_characteristics": [],
            "method_routing": [],
        }
    rows: list[dict[str, object]] = []
    for item in completed:
        scores = _score_map(item)
        strongest = max(scores, key=scores.__getitem__)
        rows.append(
            {
                "period": item.period,
                "strongest_characteristic": strongest,
                "strongest_score": scores[strongest],
                "candidate_categories": list(item.candidate_categories),
                "candidate_category_labels": list(item.candidate_category_labels),
                "use_category": item.use_category,
                "use_category_label": item.use_category_label,
                "recommendation": item.method_recommendations[0],
            }
        )
    return {
        "primary_periods": rows,
        "dominant_characteristics": sorted(
            rows,
            key=lambda row: float(row["strongest_score"]),
            reverse=True,
        )[:3],
        "method_routing": _method_routing(completed),
    }


def _method_routing(
    completed: Sequence[TimeSeriesCharacteristicPeriodResult],
) -> list[dict[str, object]]:
    routing: list[dict[str, object]] = []
    for item in completed:
        scores = _score_map(item)
        stable_family = str(item.stability.get("primary_method") or "")
        routing.append(
            {
                "period": item.period,
                "suggested_method_family": stable_family
                or _candidate_method_family(item.candidate_categories),
                "candidate_categories": list(item.candidate_categories),
                "candidate_category_labels": list(item.candidate_category_labels),
                "use_category": item.use_category,
                "use_category_label": item.use_category_label,
                "recommended_use": item.recommended_use,
                "stability_grade": item.stability.get("stability_grade"),
                "window_count": item.stability.get("window_count"),
                "scores": scores,
            }
        )
    return routing


def _period_markdown(item: TimeSeriesCharacteristicPeriodResult) -> list[str]:
    if item.status != "completed":
        return [
            f"### {item.period}",
            "",
            f"- 状态：跳过；样本数 {item.sample_count}。",
            f"- 原因：{'; '.join(item.caveats) or '样本不足'}。",
            "",
        ]
    scores = _score_map(item)
    lines = [
        f"### {item.period}",
        "",
        f"- 样本：{item.sample_start} 至 {item.sample_end}，{item.sample_count} 根。",
        f"- 初筛候选：{_candidate_label_text(item)}。",
        f"- 明确建议：{item.recommended_use}",
        f"- 子区间稳定性：{item.stability.get('stability_grade')}；"
        f"窗口数 {int(item.stability.get('window_count') or 0)}。",
        f"- BDCI：{_float(item.metrics.get('bdci')):.2f}；"
        f"lag1收益自相关：{_float(item.metrics.get('return_autocorr_lag1')):.3f}"
        f"（{item.metrics.get('return_autocorr_lag1_regime', 'unknown')}）；"
        f"Hurst：{_float(item.metrics.get('hurst')):.3f}；"
        f"方差比均值：{_float(item.metrics.get('variance_ratio_mean')):.3f}。",
        "",
        "| 初筛路线 | 决定性指标 | 数值 | 门槛 | 是否通过 |",
        "|---|---|---:|---|---|",
    ]
    for gate in item.direct_use_gates:
        lines.append(
            f"| {gate.label} | `{gate.metric}` | {gate.value:.3f} | "
            f"{gate.operator} {gate.threshold:.3f} | "
            f"{'通过' if gate.passed else '未通过'} |"
        )
    lines.extend(
        [
            "",
            "| 特性 | 分数 | 强度 |",
            "|---|---:|---|",
        ]
    )
    for score in item.scores:
        lines.append(f"| {score.name} | {score.score:.1f} | {score.strength} |")
    lines.extend(
        [
            "",
            "| 主频候选 | 周期K线数 | 交易日等效 | 功率占比 |",
            "|---:|---:|---:|---:|",
        ]
    )
    for cycle in item.dominant_cycles:
        lines.append(
            f"| {cycle.rank} | {cycle.period_bars:.2f} | "
            f"{cycle.period_days_equiv:.2f} | {cycle.power_share:.2%} |"
        )
    if not item.dominant_cycles:
        lines.append("| - | - | - | - |")
    lines.extend(
        [
            "",
            "| 子区间 | 区间 | 主方法 | 初筛候选 | 趋势 | 周期 | 随机 | 建议 |",
            "|---:|---|---|---|---:|---:|---:|---|",
        ]
    )
    for window in item.windows[:12]:
        lines.append(
            f"| {window.window_index} | "
            f"{(window.sample_start or '')[:10]}~{(window.sample_end or '')[:10]} | "
            f"{window.primary_method} | "
            f"{_candidate_label_text(window)} | "
            f"{window.scores.get('trend', 0.0):.1f} | "
            f"{window.scores.get('cycle', 0.0):.1f} | "
            f"{window.scores.get('randomness', 0.0):.1f} | "
            f"{window.recommended_use} |"
        )
    if len(item.windows) > 12:
        remaining = len(item.windows) - 12
        lines.append(
            f"| ... | 另有 {remaining} 个窗口 | ... | ... | ... | ... | ... | ... |"
        )
    if not item.windows:
        lines.append("| - | - | - | - | - | - | - | 子区间不足 |")
    lines.extend(["", "建议："])
    for recommendation in item.method_recommendations:
        lines.append(f"- {recommendation}")
    if item.unsuitable_for:
        lines.append("")
        lines.append("不适合：")
        for unsuitable in item.unsuitable_for:
            lines.append(f"- {unsuitable}")
    if item.caveats:
        lines.append("")
        lines.append("注意：")
        for caveat in item.caveats:
            lines.append(f"- {caveat}")
    lines.append("")
    _ = scores
    return lines


def _candidate_label_text(
    item: TimeSeriesCharacteristicPeriodResult | CharacteristicWindowResult,
) -> str:
    return (
        "、".join(item.candidate_category_labels)
        if item.candidate_category_labels
        else USE_CATEGORY_LABELS["non_direct"]
    )


def _score_map(item: TimeSeriesCharacteristicPeriodResult) -> dict[str, float]:
    return {score.name: score.score for score in item.scores}


def _spectral_metrics(
    series: pd.Series,
    *,
    period: PeriodName,
    config: TimeSeriesCharacteristicConfig,
) -> dict[str, object]:
    values = series.dropna().to_numpy(dtype=np.float64)
    x = values - np.mean(values)
    if len(x) < 8 or float(np.std(x)) <= 0.0:
        return {
            "spectral_entropy": 1.0,
            "spectral_top_power_share": 0.0,
            "spectral_top3_power_share": 0.0,
            "spectral_top_power_concentration_ratio": 0.0,
            "spectral_top3_concentration_ratio": 0.0,
            "spectral_positive_frequency_count": 0,
            "dominant_period_bars": None,
            "dominant_period_days_equiv": None,
            "dominant_cycles": [],
        }
    spectrum = np.fft.rfft(x)
    power = np.abs(spectrum) ** 2
    freqs = np.fft.rfftfreq(len(x), d=1.0)
    mask = freqs > 0
    freqs = freqs[mask]
    power = power[mask]
    if len(power) == 0 or float(power.sum()) <= 0.0:
        return {
            "spectral_entropy": 1.0,
            "spectral_top_power_share": 0.0,
            "spectral_top3_power_share": 0.0,
            "spectral_top_power_concentration_ratio": 0.0,
            "spectral_top3_concentration_ratio": 0.0,
            "spectral_positive_frequency_count": 0,
            "dominant_period_bars": None,
            "dominant_period_days_equiv": None,
            "dominant_cycles": [],
        }
    share = power / power.sum()
    entropy = -float(np.sum(share * np.log(share + 1e-12))) / math.log(len(share))
    order = np.argsort(power)[::-1]
    cycles: list[DominantCycle] = []
    for rank, idx in enumerate(order[: config.top_frequency_count], start=1):
        freq = float(freqs[idx])
        if freq <= 0.0:
            continue
        bars = 1.0 / freq
        cycles.append(
            DominantCycle(
                rank=rank,
                period_bars=float(bars),
                period_days_equiv=float(bars / _bars_per_day(period)),
                power_share=float(share[idx]),
            )
        )
    top_share = float(share[order[0]]) if len(order) else 0.0
    top3_share = float(share[order[:3]].sum()) if len(order) else 0.0
    positive_count = len(share)
    top_expected = 1.0 / positive_count if positive_count else 1.0
    top3_expected = min(3, positive_count) / positive_count if positive_count else 1.0
    dominant = cycles[0] if cycles else None
    return {
        "spectral_entropy": entropy,
        "spectral_top_power_share": top_share,
        "spectral_top3_power_share": top3_share,
        "spectral_top_power_concentration_ratio": (
            top_share / top_expected if top_expected > 0.0 else 0.0
        ),
        "spectral_top3_concentration_ratio": (
            top3_share / top3_expected if top3_expected > 0.0 else 0.0
        ),
        "spectral_positive_frequency_count": positive_count,
        "dominant_period_bars": dominant.period_bars if dominant else None,
        "dominant_period_days_equiv": (
            dominant.period_days_equiv if dominant else None
        ),
        "dominant_cycles": cycles,
    }


def _autocorrelations(series: pd.Series, max_lag: int) -> dict[str, float]:
    clean = series.dropna()
    values: dict[str, float] = {}
    if len(clean) < 4 or float(clean.std()) <= 0.0:
        return values
    for lag in range(1, min(max_lag, len(clean) // 3) + 1):
        value = clean.autocorr(lag=lag)
        if value is not None and math.isfinite(float(value)):
            values[str(lag)] = float(value)
    return values


def _variance_ratio(returns: pd.Series, lag: int) -> float:
    clean = returns.dropna()
    if lag <= 1 or len(clean) <= lag * 2:
        return math.nan
    one = float(clean.var(ddof=1))
    if one <= 0.0:
        return math.nan
    multi = clean.rolling(lag).sum().dropna()
    if len(multi) < 3:
        return math.nan
    return float(multi.var(ddof=1) / (lag * one))


def _hurst_exponent(log_close: pd.Series, lags: Sequence[int]) -> float:
    values = log_close.to_numpy(dtype=np.float64)
    x: list[float] = []
    y: list[float] = []
    for lag in lags:
        if lag <= 1 or lag >= len(values) // 2:
            continue
        diff = values[lag:] - values[:-lag]
        scale = float(np.std(diff))
        if scale <= 0.0 or not math.isfinite(scale):
            continue
        x.append(math.log(float(lag)))
        y.append(math.log(scale))
    if len(x) < 2:
        return 0.5
    slope = float(np.polyfit(np.asarray(x), np.asarray(y), 1)[0])
    return float(np.clip(slope, 0.0, 1.0))


def _runs_zscore(returns: pd.Series) -> float:
    signs = np.sign(returns.to_numpy(dtype=np.float64))
    signs = signs[signs != 0.0]
    if len(signs) < 10:
        return 0.0
    positives = int(np.sum(signs > 0.0))
    negatives = int(np.sum(signs < 0.0))
    if positives == 0 or negatives == 0:
        return 0.0
    runs = 1 + int(np.sum(signs[1:] != signs[:-1]))
    n = positives + negatives
    expected = 1.0 + 2.0 * positives * negatives / n
    numerator = 2.0 * positives * negatives * (2.0 * positives * negatives - n)
    denominator = float(n * n * (n - 1))
    variance = numerator / denominator if denominator > 0.0 else 0.0
    if variance <= 0.0:
        return 0.0
    return float((runs - expected) / math.sqrt(variance))


def _rolling_regime_metrics(returns: pd.Series) -> dict[str, float]:
    clean = returns.dropna()
    window = max(20, min(252, len(clean) // 6))
    if len(clean) < window * 3:
        return {"rolling_mean_dispersion": 0.0, "rolling_volatility_cv": 0.0}
    rolling_mean = clean.rolling(window).mean().dropna()
    rolling_vol = clean.rolling(window).std().dropna()
    base_std = float(clean.std())
    mean_dispersion = (
        float(rolling_mean.std() / base_std)
        if base_std > 0.0 and len(rolling_mean)
        else 0.0
    )
    vol_mean = float(rolling_vol.mean()) if len(rolling_vol) else 0.0
    vol_cv = (
        float(rolling_vol.std() / vol_mean)
        if vol_mean > 0.0 and len(rolling_vol)
        else 0.0
    )
    return {
        "rolling_mean_dispersion": mean_dispersion,
        "rolling_volatility_cv": vol_cv,
    }


def _skew(series: pd.Series) -> float:
    value = series.skew()
    return float(value) if math.isfinite(float(value)) else 0.0


def _excess_kurtosis(series: pd.Series) -> float:
    value = series.kurt()
    return float(value) if math.isfinite(float(value)) else 0.0


def _tail_ratio(series: pd.Series) -> float:
    abs_values = np.abs(series.dropna().to_numpy(dtype=np.float64))
    if len(abs_values) < 10:
        return 1.0
    q95 = float(np.quantile(abs_values, 0.95))
    q99 = float(np.quantile(abs_values, 0.99))
    return q99 / q95 if q95 > 0.0 else 1.0


def _max_abs_zscore(series: pd.Series) -> float:
    clean = series.dropna()
    std = float(clean.std())
    if len(clean) == 0 or std <= 0.0:
        return 0.0
    return float((clean - clean.mean()).abs().max() / std)


def _drift_tstat(returns: pd.Series) -> float:
    clean = returns.dropna()
    std = float(clean.std())
    if len(clean) < 3 or std <= 0.0:
        return 0.0
    return float(clean.mean() / (std / math.sqrt(len(clean))))


def _finite_mean(values: Sequence[float] | object) -> float | None:
    finite = [float(value) for value in values if math.isfinite(float(value))]
    return float(np.mean(finite)) if finite else None


def _lag1_return_autocorr_regime(value: object) -> str:
    lag1 = _float(value, math.nan)
    if not math.isfinite(lag1):
        return "unknown"
    if lag1 >= LAG1_RETURN_AUTOCORR_TREND_THRESHOLD:
        return "positive_persistence"
    if lag1 <= LAG1_RETURN_AUTOCORR_MEAN_REVERSION_THRESHOLD:
        return "negative_reversal"
    return "weak_serial_dependence"


def _mean_score(*parts: float) -> float:
    return 100.0 * float(np.mean([_scale(part) for part in parts]))


def _scale(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return float(np.clip(value, 0.0, 1.0))


def _strength(score: float) -> str:
    if score >= 70.0:
        return "strong"
    if score >= 45.0:
        return "medium"
    return "weak"


def _float(value: object, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _bars_per_day(period: str) -> float:
    mapping = {
        "1min": 240.0,
        "5min": 48.0,
        "15min": 16.0,
        "30min": 8.0,
        "60min": 4.0,
        "day": 1.0,
        "week": 1.0 / 5.0,
    }
    return mapping[period]


def _date_label(series: pd.Series, boundary: str) -> str | None:
    if series.empty:
        return None
    timestamp = series.index.min() if boundary == "min" else series.index.max()
    if isinstance(timestamp, pd.Timestamp):
        return timestamp.isoformat()
    return str(timestamp)
