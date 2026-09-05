# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownParameterType=false
# pyright: reportMissingTypeStubs=false
# pyright: reportInvalidCast=false, reportAttributeAccessIssue=false
# pyright: reportArgumentType=false, reportMissingTypeArgument=false
# pyright: reportUnnecessaryCast=false
"""Pre-backtest directional-information surface for index timing research.

This module deliberately sits between frequency-structure research and strategy
backtests.  Opportunity density can say "there is a cycle"; it cannot say the
cycle phase or slope points to future returns.  The directional-information
surface answers that narrower, pre-backtest question:

    does a causal filter direction at sample t align with the future log return
    over a fixed fraction of the tested physical cycle?

The surface is frequency/physical-period first.  ``center_period_bars`` remains
the filter implementation coordinate because filters run on sampled bars, but
the invariant research object is the center period in trading-day-equivalent
time (or its reciprocal, cycles per trading day).  A 120-minute cycle is the
same frequency whether it is represented as 120 one-minute bars, 24 five-minute
bars, or 2 sixty-minute bars; coarse sampling may simply be unable to observe it
without aliasing.

The output is still not a tradable strategy.  It contains no position sizing,
costs, next-bar execution, NAV, drawdown or turnover.  It is a governed
time-series diagnostic used to decide whether a parameter neighborhood is worth
promotion into the strategy workflow.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Literal, cast

import numpy as np
import pandas as pd

from factor_lab.filtering.parameter_workflow import PERIOD_BARS_PER_DAY
from factor_lab.filtering.timing_validation import (
    FilterMode,
    FilterSpec,
    OutputKind,
    PeriodName,
    TimingValidationConfig,
    apply_filter_spec,
    resample_close_frame,
)
from factor_lab.filtering.tool_selection import filter_spec_to_dict

TRADING_MINUTES_PER_DAY = 240.0

DirectionalInformationStrength = Literal[
    "no_directional_edge",
    "thin_directional_edge",
    "directional_candidate",
    "strong_directional_candidate",
]
DirectionalInformationSignalRule = Literal[
    "filtered_delta_sign",
]
DirectionalInformationStabilityPolicy = Literal[
    "calendar_year",
    "fixed_window",
]

PERIOD_DEFAULT_DII_GRIDS: dict[PeriodName, tuple[float, ...]] = {
    "week": (12.0, 16.0, 20.0, 26.0, 39.0, 52.0),
    "day": (20.0, 30.0, 40.0, 60.0, 90.0, 120.0),
    "60min": (24.0, 32.0, 40.0, 48.0, 64.0, 80.0),
    "30min": (24.0, 32.0, 40.0, 56.0, 72.0, 96.0),
    "15min": (24.0, 32.0, 48.0, 72.0, 96.0, 144.0),
    "5min": (24.0, 40.0, 56.0, 72.0, 96.0, 144.0),
    "1min": (24.0, 48.0, 96.0, 144.0, 240.0, 360.0, 480.0, 672.0),
}

PERIOD_DEFAULT_STABILITY_WINDOWS: dict[PeriodName, int] = {
    "week": 104,
    "day": 244,
    "60min": 244 * 4,
    "30min": 244 * 8 // 2,
    "15min": 244 * 16 // 4,
    "5min": 48 * 50,
    "1min": 240 * 30,
}


@dataclass(frozen=True, slots=True)
class DirectionalInformationSurfaceConfig:
    """Configuration for a pre-backtest frequency-surface diagnostic.

    ``center_period_days`` is the preferred frequency-first input.  The legacy
    ``center_period_bars`` field is retained because the underlying filters are
    parameterized in sampled bars.  When bars are used, they are immediately
    normalized into trading-day-equivalent periods in the output artifact.
    """

    period: PeriodName = "day"
    timestamp_column: str = "timestamp"
    close_column: str = "close"
    min_observations: int = 120
    filter_family: Literal["laplace_iir"] = "laplace_iir"
    filter_mode: FilterMode = "bandpass"
    output_kind: OutputKind = "component"
    center_period_bars: tuple[float, ...] | None = None
    center_period_days: tuple[float, ...] | None = None
    q_values: tuple[float, ...] = (0.707, 1.0, 1.4)
    horizon_fractions: tuple[float, ...] = (0.125, 0.25, 0.5)
    signal_rule: DirectionalInformationSignalRule = "filtered_delta_sign"
    stability_policy: DirectionalInformationStabilityPolicy = "calendar_year"
    stability_window_bars: int | None = None
    stability_step_bars: int | None = None
    robust_quantile: float = 0.25
    robust_period_neighborhood_pct: float = 0.15
    robust_q_neighborhood_ratio: float = 1.50
    robust_horizon_neighborhood_pct: float = 0.30
    min_edge_bps: float = 5.0
    min_robust_edge_bps: float = 2.0
    min_hit_rate: float = 0.51
    min_abs_direction_corr: float = 0.015
    min_positive_window_share: float = 0.65
    min_stability_windows_for_strong: int = 6
    top_n: int = 10

    def __post_init__(self) -> None:
        if self.min_observations < 30:
            raise ValueError("min_observations must be >= 30")
        if self.filter_family != "laplace_iir":
            raise ValueError("Only laplace_iir directional surface is implemented")
        if self.filter_mode not in {"lowpass", "highpass", "bandpass"}:
            raise ValueError("Unsupported filter_mode")
        if self.center_period_bars is not None and self.center_period_days is not None:
            raise ValueError(
                "Use either center_period_bars or center_period_days, not both"
            )
        periods = self.period_grid
        if not periods:
            raise ValueError("center period grid must not be empty")
        if any(period <= 2.0 or not math.isfinite(period) for period in periods):
            message = (
                "center periods must be finite and > 2 sampled bars after "
                "frequency-to-bar conversion"
            )
            raise ValueError(message)
        if not self.q_values:
            raise ValueError("q_values must not be empty")
        if any(q <= 0.0 or not math.isfinite(q) for q in self.q_values):
            raise ValueError("q_values must be finite and > 0")
        if not self.horizon_fractions:
            raise ValueError("horizon_fractions must not be empty")
        if any(
            fraction <= 0.0 or not math.isfinite(fraction)
            for fraction in self.horizon_fractions
        ):
            raise ValueError("horizon_fractions must be finite and > 0")
        if self.signal_rule != "filtered_delta_sign":
            raise ValueError("Unsupported signal_rule")
        if self.stability_policy not in {"calendar_year", "fixed_window"}:
            raise ValueError("Unsupported stability_policy")
        if self.stability_window_bars is not None and self.stability_window_bars < 10:
            raise ValueError("stability_window_bars must be >= 10 when provided")
        if self.stability_step_bars is not None and self.stability_step_bars < 1:
            raise ValueError("stability_step_bars must be >= 1 when provided")
        if not 0.0 < self.robust_quantile <= 1.0:
            raise ValueError("robust_quantile must be in (0, 1]")
        if self.robust_period_neighborhood_pct < 0.0:
            raise ValueError("robust_period_neighborhood_pct must be >= 0")
        if self.robust_q_neighborhood_ratio < 1.0:
            raise ValueError("robust_q_neighborhood_ratio must be >= 1")
        if self.robust_horizon_neighborhood_pct < 0.0:
            raise ValueError("robust_horizon_neighborhood_pct must be >= 0")
        if self.min_stability_windows_for_strong <= 0:
            raise ValueError("min_stability_windows_for_strong must be > 0")
        if self.top_n <= 0:
            raise ValueError("top_n must be > 0")

    @property
    def period_grid(self) -> tuple[float, ...]:
        if self.center_period_days is not None:
            return tuple(
                _period_bars_from_days(self.period, days)
                for days in self.center_period_days
            )
        return tuple(self.center_period_bars or PERIOD_DEFAULT_DII_GRIDS[self.period])

    @property
    def period_days_grid(self) -> tuple[float, ...]:
        return tuple(
            _period_days_from_bars(self.period, bars) for bars in self.period_grid
        )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["center_period_bars"] = list(self.period_grid)
        payload["center_period_days"] = list(self.period_days_grid)
        payload["center_frequency_cycles_per_day"] = [
            _frequency_cycles_per_day(days) for days in self.period_days_grid
        ]
        return payload


@dataclass(frozen=True, slots=True)
class DirectionalInformationWindowMetric:
    """Directional information measured in one stability window."""

    window_id: str
    sample_start: str
    sample_end: str
    sample_count: int
    dii_bps: float
    hit_rate: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DirectionalInformationSurfacePoint:
    """One parameter-surface point before strategy backtesting."""

    filter_name: str
    filter_spec: dict[str, object]
    center_period_bars: float
    center_period_days: float
    center_frequency_cycles_per_day: float
    q: float
    horizon_fraction: float
    horizon_bars: int
    horizon_days: float
    valid_observations: int
    dii_bps: float
    hit_rate: float
    direction_corr: float | None
    naive_t_stat: float | None
    future_return_vol_bps: float
    positive_window_count: int
    total_window_count: int
    positive_window_share: float | None
    median_window_dii_bps: float | None
    min_window_dii_bps: float | None
    robust_dii_quantile_bps: float | None
    robust_neighborhood_count: int
    evidence_strength: DirectionalInformationStrength
    interpretation_zh: str
    window_metrics: list[DirectionalInformationWindowMetric] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "window_metrics": [item.to_dict() for item in self.window_metrics],
        }


@dataclass(frozen=True, slots=True)
class DirectionalInformationSurfaceResult:
    """Reusable artifact for pure time-series timing feasibility research."""

    index_ref: str
    period: str
    sample_start: str
    sample_end: str
    sample_count: int
    points: list[DirectionalInformationSurfacePoint]
    selected: list[DirectionalInformationSurfacePoint]
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "index_ref": self.index_ref,
            "period": self.period,
            "sample_start": self.sample_start,
            "sample_end": self.sample_end,
            "sample_count": self.sample_count,
            "points": [item.to_dict() for item in self.points],
            "selected": [item.to_dict() for item in self.selected],
            "metadata": self.metadata,
        }


def run_directional_information_surface(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: DirectionalInformationSurfaceConfig | None = None,
    index_ref: str = "index_series",
) -> DirectionalInformationSurfaceResult:
    """Compute a causal filter-parameter DII surface without running a backtest."""

    cfg = config or DirectionalInformationSurfaceConfig()
    close = resample_close_frame(
        rows,
        config=TimingValidationConfig(
            period=cfg.period,
            timestamp_column=cfg.timestamp_column,
            close_column=cfg.close_column,
            min_observations=cfg.min_observations,
        ),
    )
    if len(close) < cfg.min_observations:
        raise ValueError(
            f"Not enough observations for {cfg.period}: "
            + f"{len(close)} < {cfg.min_observations}"
        )
    log_close = cast(pd.Series, np.log(close))
    log_close.index = close.index
    raw_points: list[dict[str, object]] = []
    for center_period in cfg.period_grid:
        for q in cfg.q_values:
            spec = FilterSpec(
                name=_filter_name(cfg, center_period=center_period, q=q),
                family=cfg.filter_family,
                mode=cfg.filter_mode,
                params={"period": float(center_period), "q": float(q)},
                output_kind=_output_kind_for_mode(cfg.filter_mode, cfg.output_kind),
            )
            filtered = apply_filter_spec(log_close, spec)
            direction = _direction_from_filtered(filtered)
            for horizon_fraction in cfg.horizon_fractions:
                horizon_bars = max(1, int(round(center_period * horizon_fraction)))
                raw_points.append(
                    _evaluate_surface_point(
                        log_close=log_close,
                        direction=direction,
                        spec=spec,
                        center_period=center_period,
                        q=q,
                        horizon_fraction=horizon_fraction,
                        horizon_bars=horizon_bars,
                        config=cfg,
                    )
                )
    enriched = _attach_robustness(raw_points, config=cfg)
    points = [_surface_point_from_raw(item, config=cfg) for item in enriched]
    points = sorted(
        points,
        key=lambda item: (
            _strength_rank(item.evidence_strength),
            item.robust_dii_quantile_bps
            if item.robust_dii_quantile_bps is not None
            else -math.inf,
            item.dii_bps,
            item.positive_window_share
            if item.positive_window_share is not None
            else -math.inf,
        ),
        reverse=True,
    )
    selected = points[: cfg.top_n]
    return DirectionalInformationSurfaceResult(
        index_ref=index_ref,
        period=cfg.period,
        sample_start=str(close.index[0]),
        sample_end=str(close.index[-1]),
        sample_count=int(len(close)),
        points=points,
        selected=selected,
        metadata={
            "workflow_role": "filter_directional_information_surface",
            "workflow_version": "dii_frequency_surface_v2",
            "index_ref": index_ref,
            "surface_domain": "frequency_physical_period",
            "sampling_granularity": cfg.period,
            "unit_policy": {
                "canonical_axis": (
                    "center_period_days / center_frequency_cycles_per_day"
                ),
                "bars_are": "sampling_implementation_coordinate_not_research_object",
                "trading_day_equivalent": True,
                "trading_minutes_per_day": TRADING_MINUTES_PER_DAY,
                "bars_per_trading_day": PERIOD_BARS_PER_DAY[cfg.period],
                "sampling_interval_days": _sampling_interval_days(cfg.period),
                "nyquist_min_center_period_days": _nyquist_min_period_days(
                    cfg.period
                ),
                "formula": "P_bars = T_days * bars_per_trading_day",
            },
            "pre_backtest_boundary": (
                "Directional information uses only price, causal filter output "
                "at sample t, and future-return labels for diagnostic scoring. It "
                "does not compute NAV, drawdown, trade count, costs or position "
                "execution, and must not be narrated as a strategy backtest."
            ),
            "dii_formula": (
                "DII(T,Q,phi)=E[sign(delta filtered_t) * "
                "(logP_{t+round(phi*T/delta)}-logP_t)]"
            ),
            "legacy_bar_coordinate_formula": (
                "For a fixed sampling granularity, P_bars=T/delta and "
                "h_bars=round(phi*P_bars)."
            ),
            "robust_surface_policy": {
                "robust_quantile": cfg.robust_quantile,
                "physical_period_neighborhood_pct": (
                    cfg.robust_period_neighborhood_pct
                ),
                "q_neighborhood_ratio": cfg.robust_q_neighborhood_ratio,
                "horizon_neighborhood_pct": cfg.robust_horizon_neighborhood_pct,
                "interpretation": (
                    "A wide/thick ridge in physical-period/frequency space is "
                    "required before a point is treated as structural evidence. "
                    "Isolated high DII points are thin edges and must be treated "
                    "as overfit-prone."
                ),
            },
            "strength_thresholds": {
                "min_edge_bps": cfg.min_edge_bps,
                "min_robust_edge_bps": cfg.min_robust_edge_bps,
                "min_hit_rate": cfg.min_hit_rate,
                "min_abs_direction_corr": cfg.min_abs_direction_corr,
                "min_positive_window_share": cfg.min_positive_window_share,
                "min_stability_windows_for_strong": (
                    cfg.min_stability_windows_for_strong
                ),
            },
            "signal_rule": cfg.signal_rule,
            "stability_policy": cfg.stability_policy,
            "config": cfg.to_dict(),
            "factor_lifecycle_mutation": False,
            "strategy_lifecycle_mutation": False,
        },
    )


def render_directional_information_markdown(
    result: DirectionalInformationSurfaceResult,
) -> str:
    """Render a compact Chinese report for CLI artifacts."""

    lines: list[str] = [
        f"# {result.index_ref} {result.period} 方向信息频率曲面",
        "",
        f"- 样本：{result.sample_start} → {result.sample_end}",
        f"- K线数：{result.sample_count}",
        "- 曲面口径：频率/物理周期优先；K线根数只是该采样级别上的滤波实现坐标。",
        (
            "- 口径：只用价格序列、因果滤波方向和未来收益标签；"
            "不含交易成本、仓位、净值或回撤。"
        ),
        "",
        "## Top 候选",
        "",
        (
            "| 排名 | 滤波器 | T(交易日) | f(次/日) | h(bars) | "
            "DII(bps) | 命中率 | 相关 | "
            "稳健分位(bps) | 年/窗为正 | 强度 |"
        ),
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for index, point in enumerate(result.selected, start=1):
        corr = "" if point.direction_corr is None else f"{point.direction_corr:.4f}"
        robust = (
            ""
            if point.robust_dii_quantile_bps is None
            else f"{point.robust_dii_quantile_bps:.2f}"
        )
        share = (
            "n/a"
            if point.positive_window_share is None
            else f"{point.positive_window_count}/{point.total_window_count}"
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    point.filter_name,
                    f"{point.center_period_days:.4g}",
                    f"{point.center_frequency_cycles_per_day:.4g}",
                    str(point.horizon_bars),
                    f"{point.dii_bps:.2f}",
                    f"{point.hit_rate:.2%}",
                    corr,
                    robust,
                    share,
                    point.evidence_strength,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 判读规则",
            "",
            "- `DII>0` 只说明滤波方向与未来收益同向，不是回测收益。",
            (
                "- DII 频率曲面本质是频率/物理周期曲面；同一频率在不同K线级别上"
                "会换算成不同 bars。"
            ),
            (
                "- `robust_dii_quantile_bps` 是频率邻域分位数；"
                "宽厚正山脊优先，孤立尖峰降级。"
            ),
            (
                "- `strong_directional_candidate` 仍只是进入策略模板/"
                "样本外验证的候选，不自动成为有效因子或交易策略。"
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def _filter_name(
    config: DirectionalInformationSurfaceConfig,
    *,
    center_period: float,
    q: float,
) -> str:
    period_label = f"{center_period:g}".replace(".", "p")
    q_label = f"{q:g}".replace(".", "p")
    return f"dii_{config.filter_family}_{config.filter_mode}_p{period_label}_q{q_label}"


def _output_kind_for_mode(
    mode: FilterMode,
    configured: OutputKind,
) -> OutputKind:
    if mode == "lowpass":
        return "level"
    return configured


def _direction_from_filtered(filtered: pd.Series) -> pd.Series:
    changes = filtered.diff()
    signs = pd.Series(np.sign(changes.to_numpy(dtype=float)), index=filtered.index)
    return cast(pd.Series, signs.replace(0.0, np.nan).ffill())


def _evaluate_surface_point(
    *,
    log_close: pd.Series,
    direction: pd.Series,
    spec: FilterSpec,
    center_period: float,
    q: float,
    horizon_fraction: float,
    horizon_bars: int,
    config: DirectionalInformationSurfaceConfig,
) -> dict[str, object]:
    future_return = cast(pd.Series, log_close.shift(-horizon_bars) - log_close)
    frame = pd.DataFrame(
        {
            "direction": direction,
            "future_return": future_return,
        }
    ).dropna()
    frame = frame[frame["direction"] != 0.0]
    if len(frame) < max(30, config.min_observations // 4):
        raise ValueError(
            f"Not enough valid DII observations for {spec.name}, h={horizon_bars}"
        )
    aligned = frame["direction"].to_numpy(dtype=float) * frame[
        "future_return"
    ].to_numpy(dtype=float)
    future = frame["future_return"].to_numpy(dtype=float)
    direct = frame["direction"].to_numpy(dtype=float)
    std = float(np.std(aligned, ddof=1)) if len(aligned) > 1 else 0.0
    mean = float(np.mean(aligned))
    direction_corr = _safe_corr(direct, future)
    window_metrics = _window_metrics(frame, config=config)
    return {
        "filter_name": spec.name,
        "filter_spec": filter_spec_to_dict(spec),
        "center_period_bars": float(center_period),
        "center_period_days": _period_days_from_bars(config.period, center_period),
        "center_frequency_cycles_per_day": _frequency_cycles_per_day(
            _period_days_from_bars(config.period, center_period)
        ),
        "q": float(q),
        "horizon_fraction": float(horizon_fraction),
        "horizon_bars": int(horizon_bars),
        "horizon_days": _period_days_from_bars(config.period, horizon_bars),
        "valid_observations": int(len(aligned)),
        "dii_bps": mean * 10000.0,
        "hit_rate": float(np.mean(aligned > 0.0)),
        "direction_corr": direction_corr,
        "naive_t_stat": (
            float(mean / (std / math.sqrt(len(aligned))))
            if std > 0.0 and len(aligned) > 1
            else None
        ),
        "future_return_vol_bps": std * 10000.0,
        "window_metrics": window_metrics,
    }


def _window_metrics(
    frame: pd.DataFrame,
    *,
    config: DirectionalInformationSurfaceConfig,
) -> list[DirectionalInformationWindowMetric]:
    aligned = cast(pd.Series, frame["direction"] * frame["future_return"])
    if config.stability_policy == "calendar_year":
        metrics: list[DirectionalInformationWindowMetric] = []
        for year, group in frame.assign(aligned=aligned).groupby(frame.index.year):
            if len(group) < 20:
                continue
            values = group["aligned"].to_numpy(dtype=float)
            metrics.append(
                DirectionalInformationWindowMetric(
                    window_id=str(year),
                    sample_start=str(group.index[0]),
                    sample_end=str(group.index[-1]),
                    sample_count=int(len(group)),
                    dii_bps=float(np.mean(values) * 10000.0),
                    hit_rate=float(np.mean(values > 0.0)),
                )
            )
        if metrics:
            return metrics
    return _fixed_window_metrics(frame, config=config)


def _fixed_window_metrics(
    frame: pd.DataFrame,
    *,
    config: DirectionalInformationSurfaceConfig,
) -> list[DirectionalInformationWindowMetric]:
    window = config.stability_window_bars or PERIOD_DEFAULT_STABILITY_WINDOWS[
        config.period
    ]
    step = config.stability_step_bars or max(1, window // 2)
    if len(frame) < window:
        window = max(20, len(frame) // 3)
        step = max(1, window)
    metrics: list[DirectionalInformationWindowMetric] = []
    values = (
        cast(pd.Series, frame["direction"] * frame["future_return"])
        .to_numpy(dtype=float)
        .copy()
    )
    for start in range(0, max(1, len(frame) - window + 1), step):
        stop = min(len(frame), start + window)
        if stop - start < 20:
            continue
        chunk = values[start:stop]
        metrics.append(
            DirectionalInformationWindowMetric(
                window_id=f"{start}:{stop}",
                sample_start=str(frame.index[start]),
                sample_end=str(frame.index[stop - 1]),
                sample_count=int(stop - start),
                dii_bps=float(np.mean(chunk) * 10000.0),
                hit_rate=float(np.mean(chunk > 0.0)),
            )
        )
    return metrics


def _attach_robustness(
    rows: list[dict[str, object]],
    *,
    config: DirectionalInformationSurfaceConfig,
) -> list[dict[str, object]]:
    enriched: list[dict[str, object]] = []
    for row in rows:
        center = float(row["center_period_bars"])
        q = float(row["q"])
        horizon = float(row["horizon_bars"])
        neighbors = [
            other
            for other in rows
            if _is_neighbor(
                center=center,
                q=q,
                horizon=horizon,
                other=other,
                config=config,
            )
        ]
        dii_values = [float(item["dii_bps"]) for item in neighbors]
        copy = dict(row)
        copy["robust_dii_quantile_bps"] = (
            float(np.quantile(dii_values, config.robust_quantile))
            if dii_values
            else None
        )
        copy["robust_neighborhood_count"] = len(neighbors)
        enriched.append(copy)
    return enriched


def _is_neighbor(
    *,
    center: float,
    q: float,
    horizon: float,
    other: Mapping[str, object],
    config: DirectionalInformationSurfaceConfig,
) -> bool:
    other_center = float(other["center_period_bars"])
    other_q = float(other["q"])
    other_horizon = float(other["horizon_bars"])
    period_ok = (
        abs(other_center - center)
        <= max(1e-12, center * config.robust_period_neighborhood_pct)
    )
    q_ok = (
        other_q >= q / config.robust_q_neighborhood_ratio
        and other_q <= q * config.robust_q_neighborhood_ratio
    )
    horizon_ok = (
        abs(other_horizon - horizon)
        <= max(1.0, horizon * config.robust_horizon_neighborhood_pct)
    )
    return period_ok and q_ok and horizon_ok


def _surface_point_from_raw(
    row: Mapping[str, object],
    *,
    config: DirectionalInformationSurfaceConfig,
) -> DirectionalInformationSurfacePoint:
    windows = cast(list[DirectionalInformationWindowMetric], row["window_metrics"])
    window_values = [item.dii_bps for item in windows]
    positive_count = len([value for value in window_values if value > 0.0])
    total_count = len(window_values)
    positive_share = positive_count / total_count if total_count else None
    robust = cast(float | None, row["robust_dii_quantile_bps"])
    strength = _classify_strength(
        dii_bps=float(row["dii_bps"]),
        hit_rate=float(row["hit_rate"]),
        direction_corr=cast(float | None, row["direction_corr"]),
        positive_window_share=positive_share,
        total_window_count=total_count,
        robust_dii_quantile_bps=robust,
        config=config,
    )
    return DirectionalInformationSurfacePoint(
        filter_name=str(row["filter_name"]),
        filter_spec=cast(dict[str, object], row["filter_spec"]),
        center_period_bars=float(row["center_period_bars"]),
        center_period_days=float(row["center_period_days"]),
        center_frequency_cycles_per_day=float(
            row["center_frequency_cycles_per_day"]
        ),
        q=float(row["q"]),
        horizon_fraction=float(row["horizon_fraction"]),
        horizon_bars=int(row["horizon_bars"]),
        horizon_days=float(row["horizon_days"]),
        valid_observations=int(row["valid_observations"]),
        dii_bps=float(row["dii_bps"]),
        hit_rate=float(row["hit_rate"]),
        direction_corr=cast(float | None, row["direction_corr"]),
        naive_t_stat=cast(float | None, row["naive_t_stat"]),
        future_return_vol_bps=float(row["future_return_vol_bps"]),
        positive_window_count=positive_count,
        total_window_count=total_count,
        positive_window_share=positive_share,
        median_window_dii_bps=(
            float(np.median(window_values)) if window_values else None
        ),
        min_window_dii_bps=float(np.min(window_values)) if window_values else None,
        robust_dii_quantile_bps=robust,
        robust_neighborhood_count=int(row["robust_neighborhood_count"]),
        evidence_strength=strength,
        interpretation_zh=_strength_interpretation(strength),
        window_metrics=windows,
    )


def _classify_strength(
    *,
    dii_bps: float,
    hit_rate: float,
    direction_corr: float | None,
    positive_window_share: float | None,
    total_window_count: int,
    robust_dii_quantile_bps: float | None,
    config: DirectionalInformationSurfaceConfig,
) -> DirectionalInformationStrength:
    corr_ok = (
        direction_corr is not None
        and abs(direction_corr) >= config.min_abs_direction_corr
        and direction_corr > 0.0
    )
    robust_ok = (
        robust_dii_quantile_bps is not None
        and robust_dii_quantile_bps >= config.min_robust_edge_bps
    )
    stable_ok = (
        positive_window_share is not None
        and positive_window_share >= config.min_positive_window_share
    )
    edge_ok = dii_bps >= config.min_edge_bps and hit_rate >= config.min_hit_rate
    if (
        edge_ok
        and robust_ok
        and corr_ok
        and stable_ok
        and total_window_count >= config.min_stability_windows_for_strong
    ):
        return "strong_directional_candidate"
    if edge_ok and robust_ok and corr_ok and stable_ok:
        return "directional_candidate"
    if dii_bps > 0.0 and hit_rate > 0.50:
        return "thin_directional_edge"
    return "no_directional_edge"


def _strength_rank(strength: DirectionalInformationStrength) -> int:
    return {
        "no_directional_edge": 0,
        "thin_directional_edge": 1,
        "directional_candidate": 2,
        "strong_directional_candidate": 3,
    }[strength]


def _strength_interpretation(strength: DirectionalInformationStrength) -> str:
    return {
        "no_directional_edge": (
            "滤波方向与未来收益没有形成可用正耦合；不应仅凭频谱功率进入策略。"
        ),
        "thin_directional_edge": (
            "存在薄弱正方向信息，但幅度、邻域或稳定性不足；只允许作为探索/对照。"
        ),
        "directional_candidate": (
            "方向信息、邻域稳健性和分段稳定性同时通过基础门槛；可进入策略模板验证。"
        ),
        "strong_directional_candidate": (
            "参数邻域宽厚且跨多个稳定窗口复现；这是优先进入样本外策略验证的强方向候选。"
        ),
    }[strength]


def _safe_corr(left: np.ndarray, right: np.ndarray) -> float | None:
    if len(left) < 3 or len(right) < 3:
        return None
    left_std = float(np.std(left))
    right_std = float(np.std(right))
    if left_std == 0.0 or right_std == 0.0:
        return None
    value = float(np.corrcoef(left, right)[0, 1])
    return value if math.isfinite(value) else None


def _period_bars_from_days(period: PeriodName, days: float) -> float:
    return float(days) * PERIOD_BARS_PER_DAY[period]


def _period_days_from_bars(period: PeriodName, bars: float) -> float:
    return float(bars) / PERIOD_BARS_PER_DAY[period]


def _frequency_cycles_per_day(period_days: float) -> float:
    return 1.0 / float(period_days)


def _sampling_interval_days(period: PeriodName) -> float:
    return 1.0 / PERIOD_BARS_PER_DAY[period]


def _nyquist_min_period_days(period: PeriodName) -> float:
    return 2.0 * _sampling_interval_days(period)
