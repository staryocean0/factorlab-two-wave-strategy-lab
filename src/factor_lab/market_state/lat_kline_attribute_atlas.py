"""Comparable annual K-line attributes for LAT carrier attribution."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from factor_lab.market_state.brickwall_bandvol import (
    CURRENT_V4_BAND_NAMES,
    CURRENT_V4_EDGES,
    brickwall_components,
)
from factor_lab.market_state.lat_index_portability import (
    LatCandidate,
    evaluate_open_fill_path,
    fold_direction_state,
)
from factor_lab.strategy.services.risk_off_v58_frequency_bollinger import (
    causal_lowpass,
    causal_thickness_component,
)

REFERENCE_BARS_PER_DAY = 16.0
TARGET_BANDS = ("P29", "P38", "P43", "P48", "P53", "P67", "P95")
HIGH_FREQUENCY_TARGET_BANDS = ("P10", "P17", *TARGET_BANDS)
COMMON_15M_CLOCKS = (
    "09:50",
    "10:05",
    "10:20",
    "10:35",
    "10:50",
    "11:05",
    "11:20",
    "13:20",
    "13:35",
    "13:50",
    "14:05",
    "14:20",
    "14:35",
    "14:50",
)


def band_period_days() -> dict[str, float]:
    edges = (0.0, *CURRENT_V4_EDGES, float("inf"))
    return {
        name: float(np.sqrt(lo * hi) / REFERENCE_BARS_PER_DAY)
        for name, lo, hi in zip(CURRENT_V4_BAND_NAMES, edges[:-1], edges[1:], strict=True)
        if np.isfinite(lo) and lo > 0.0 and np.isfinite(hi)
    }


def normalize_ohlc_frame(frame: pd.DataFrame, *, common_clock_only: bool) -> pd.DataFrame:
    required = {"timestamp", "trading_day", "open", "high", "low", "close"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"K-line attribute frame missing columns: {sorted(missing)}")
    ordered = frame.copy()
    ordered["timestamp"] = pd.to_datetime(ordered["timestamp"], errors="raise")
    ordered = ordered.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    if common_clock_only:
        clocks = ordered["timestamp"].dt.strftime("%H:%M")
        ordered = ordered.loc[clocks.isin(COMMON_15M_CLOCKS)].copy()
    for column in ("open", "high", "low", "close"):
        ordered[column] = pd.to_numeric(ordered[column], errors="raise")
    if ordered.empty or (ordered[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("K-line attribute frame is empty or nonpositive")
    return ordered.reset_index(drop=True)


def _rolling_efficiency(values: np.ndarray, window: int) -> np.ndarray:
    if len(values) < window + 1:
        return np.array([], dtype=float)
    displacement = np.abs(values[window:] - values[:-window])
    absolute_step = np.abs(np.diff(values))
    cumulative_path = np.r_[0.0, np.cumsum(absolute_step, dtype=float)]
    path = cumulative_path[window:] - cumulative_path[:-window]
    return np.divide(displacement, path, out=np.zeros_like(displacement), where=path > 0)


def _rolling_trend(values: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    if len(values) < window:
        return np.array([], dtype=float), np.array([], dtype=float)
    values = np.asarray(values, dtype=float)
    count = len(values) - window + 1
    x = np.arange(window, dtype=float)
    x_mean = float(x.mean())
    xss = float(np.square(x - x_mean).sum())
    cumulative = np.r_[0.0, np.cumsum(values, dtype=float)]
    cumulative_sq = np.r_[0.0, np.cumsum(np.square(values), dtype=float)]
    sum_y = cumulative[window:] - cumulative[:-window]
    sum_y2 = cumulative_sq[window:] - cumulative_sq[:-window]
    weighted = np.empty(count, dtype=float)
    weighted[0] = float(np.dot(x, values[:window]))
    if count > 1:
        delta = -(
            sum_y[:-1] - values[: count - 1]
        ) + (window - 1) * values[window:]
        weighted[1:] = weighted[0] + np.cumsum(delta, dtype=float)
    covariance = weighted - x_mean * sum_y
    yss = np.maximum(sum_y2 - np.square(sum_y) / float(window), 0.0)
    r = np.divide(
        covariance,
        np.sqrt(yss * xss),
        out=np.zeros_like(covariance),
        where=yss > 0,
    )
    r2 = np.clip(np.square(r), 0.0, 1.0)
    t_abs = np.abs(r) * np.sqrt((window - 2) / np.maximum(1.0 - r2, 1e-12))
    return t_abs, r2


def _directional_run_mean(returns: np.ndarray) -> float:
    signs = np.sign(returns)
    signs = signs[signs != 0]
    if len(signs) == 0:
        return 0.0
    boundaries = np.flatnonzero(np.diff(signs) != 0) + 1
    runs = np.diff(np.r_[0, boundaries, len(signs)])
    return float(np.mean(runs))


def _daily_shape(frame: pd.DataFrame) -> dict[str, float]:
    rows: list[dict[str, float]] = []
    prior_close: float | None = None
    for _day, part in frame.groupby("trading_day", sort=True):
        open_ = float(part.iloc[0]["open"])
        close = float(part.iloc[-1]["close"])
        ranges = np.log(part["high"].to_numpy(float) / part["low"].to_numpy(float))
        path = float(np.sum(np.abs(np.diff(np.log(part["close"].to_numpy(float))))))
        rows.append(
            {
                "gap": abs(np.log(open_ / prior_close)) if prior_close else 0.0,
                "path": path,
                "range_sum": float(ranges.sum()),
                "net": abs(np.log(close / open_)),
            }
        )
        prior_close = close
    daily = pd.DataFrame(rows)
    total_path = float((daily["gap"] + daily["path"]).sum())
    return {
        "overnight_gap_share": float(daily["gap"].sum() / total_path) if total_path > 0 else 0.0,
        "intraday_range_efficiency": float(
            np.median(
                np.divide(
                    daily["net"].to_numpy(float),
                    daily["range_sum"].to_numpy(float),
                    out=np.zeros(len(daily)),
                    where=daily["range_sum"].to_numpy(float) > 0,
                )
            )
        ),
    }


def annual_kline_attributes(
    frame: pd.DataFrame,
    *,
    carrier: str,
    years: tuple[int, ...],
    bars_per_day: int,
    target_bands: tuple[str, ...] = TARGET_BANDS,
) -> pd.DataFrame:
    unknown_bands = sorted(set(target_bands).difference(CURRENT_V4_BAND_NAMES))
    if not target_bands or unknown_bands:
        raise ValueError(f"invalid target_bands: {unknown_bands or target_bands}")
    physical_periods = band_period_days()
    fast_mid = tuple(
        band for band in target_bands if physical_periods[band] <= physical_periods["P53"]
    )
    slow = tuple(band for band in target_bands if band not in fast_mid)
    rows: list[dict[str, Any]] = []
    day_edges = tuple(float(value) / REFERENCE_BARS_PER_DAY for value in CURRENT_V4_EDGES)
    bar_edges = tuple(value * bars_per_day for value in day_edges)
    for year in years:
        part = frame.loc[pd.DatetimeIndex(frame["timestamp"]).year == year].copy()
        if len(part) < bars_per_day * 100:
            raise ValueError(f"insufficient annual K-line rows: {carrier} {year}")
        log_close = np.log(part["close"].to_numpy(float))
        returns = np.diff(log_close)
        row: dict[str, Any] = {"carrier": carrier, "year": year, "bar_count": len(part)}
        for days in (2, 4, 8, 16):
            efficiency = _rolling_efficiency(log_close, days * bars_per_day)
            t_abs, r2 = _rolling_trend(log_close, days * bars_per_day)
            row[f"efficiency_ratio_{days}d"] = float(np.median(efficiency))
            row[f"ols_slope_t_abs_{days}d"] = float(np.median(t_abs))
            row[f"ols_r2_{days}d"] = float(np.median(r2))
        for lag in (1, 4, 16):
            row[f"return_autocorr_lag{lag}"] = float(pd.Series(returns).autocorr(lag=lag)) if len(returns) > lag + 2 else 0.0
        signs = np.sign(returns)
        row["sign_persistence"] = float(np.mean(signs[1:] == signs[:-1]))
        row["directional_run_mean"] = _directional_run_mean(returns)
        middle = causal_lowpass(
            pd.Series(log_close, index=pd.RangeIndex(len(log_close))),
            4 * bars_per_day,
            1,
        ).to_numpy(float)
        side = np.sign(log_close - middle)
        row["middle_crossing_density"] = float(np.mean(side[1:] != side[:-1]))
        row["realized_volatility"] = float(np.std(returns, ddof=0))
        daily_vol = pd.Series(returns).rolling(bars_per_day, min_periods=bars_per_day).std(ddof=0)
        row["volatility_of_volatility"] = float(daily_vol.std(ddof=0))
        downside = returns[returns < 0]
        upside = returns[returns > 0]
        down_var = float(np.mean(np.square(downside))) if len(downside) else 0.0
        up_var = float(np.mean(np.square(upside))) if len(upside) else 0.0
        row["downside_upside_variance_ratio"] = down_var / up_var if up_var > 0 else 0.0
        threshold = float(np.quantile(np.abs(returns), 0.95))
        absolute = np.abs(returns)
        row["jump_tail_share"] = float(absolute[absolute >= threshold].sum() / absolute.sum())
        row.update(_daily_shape(part))
        components = brickwall_components(
            log_close,
            interior_edges=bar_edges,
            band_names=CURRENT_V4_BAND_NAMES,
            pad=min(8192, len(log_close) - 2),
        )
        energies: dict[str, float] = {}
        return_rms = float(np.std(returns, ddof=0))
        for band in target_bands:
            rms = float(np.sqrt(np.mean(np.square(components[band]))))
            row[f"band_rms_{band}"] = rms / return_rms
            energies[band] = rms * rms
        total_energy = sum(energies.values())
        row["fast_mid_band_share"] = sum(energies[b] for b in fast_mid) / total_energy
        row["slow_band_share"] = sum(energies[b] for b in slow) / total_energy
        row["spectral_concentration"] = sum((value / total_energy) ** 2 for value in energies.values())
        rows.append(row)
    return pd.DataFrame(rows)


def standard_lat_annual_panel(
    frame: pd.DataFrame,
    *,
    carrier: str,
    years: tuple[int, ...],
    bars_per_day: int,
) -> pd.DataFrame:
    index = pd.DatetimeIndex(frame["timestamp"])
    log_close = pd.Series(np.log(frame["close"].to_numpy(float)), index=index)
    raw_open = pd.Series(frame["open"].to_numpy(float), index=index)
    rows: list[dict[str, Any]] = []
    periods = band_period_days()
    for band in TARGET_BANDS:
        period = int(round(periods[band] * bars_per_day))
        middle = causal_lowpass(log_close, period, 1)
        component = causal_thickness_component(
            log_close,
            period_bars=period,
            source="bandpass",
            order=1,
            band_upper_frequency_ratio=2.0,
        )
        window = max(16, int(round(0.75 * period)))
        width_unit = component.pow(2).rolling(window, min_periods=window).mean().pow(0.5).ewm(halflife=0.125 * period, adjust=False).mean()
        valid = pd.Series(np.arange(len(index)) >= max(2 * period, window), index=index)
        valid &= width_unit.notna()
        paths: dict[str, pd.Series] = {}
        for direction, k in (("long", 1.5), ("short", 1.0)):
            candidate = LatCandidate(periods[band], period, 1, 0.75, window, 0.125, 0.125 * period, k)
            decision = fold_direction_state(
                log_close=log_close,
                middle=middle,
                width=width_unit * candidate.width_multiplier,
                valid=valid,
                direction=direction,  # type: ignore[arg-type]
            )
            paths[direction] = evaluate_open_fill_path(
                decision=decision,
                raw_open=raw_open,
                direction=direction,  # type: ignore[arg-type]
            )
        for year in years:
            mask = index.year == year
            rows.append(
                {
                    "carrier": carrier,
                    "year": year,
                    "band": band,
                    "period_days": periods[band],
                    "long_net": float(paths["long"].loc[mask].sum()),
                    "short_net": float(paths["short"].loc[mask].sum()),
                    "sleeve_sum_net": float((paths["long"] + paths["short"]).loc[mask].sum()),
                }
            )
    return pd.DataFrame(rows)


__all__ = [
    "COMMON_15M_CLOCKS",
    "HIGH_FREQUENCY_TARGET_BANDS",
    "TARGET_BANDS",
    "annual_kline_attributes",
    "band_period_days",
    "normalize_ohlc_frame",
    "standard_lat_annual_panel",
]
