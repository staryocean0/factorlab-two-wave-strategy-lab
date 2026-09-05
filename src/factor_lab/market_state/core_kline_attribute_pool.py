"""Pure K-line core attributes with spectral/tool-response fields excluded."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

BASE_CORE_NUMERIC_COLUMNS = (
    "efficiency_ratio_2d",
    "ols_slope_t_abs_2d",
    "ols_r2_2d",
    "efficiency_ratio_4d",
    "ols_slope_t_abs_4d",
    "ols_r2_4d",
    "efficiency_ratio_8d",
    "ols_slope_t_abs_8d",
    "ols_r2_8d",
    "efficiency_ratio_16d",
    "ols_slope_t_abs_16d",
    "ols_r2_16d",
    "return_autocorr_lag1",
    "return_autocorr_lag4",
    "return_autocorr_lag16",
    "sign_persistence",
    "directional_run_mean",
    "middle_crossing_density",
    "realized_volatility",
    "volatility_of_volatility",
    "downside_upside_variance_ratio",
    "jump_tail_share",
    "overnight_gap_share",
    "intraday_range_efficiency",
)

HORIZON_DAYS = (2, 4, 8, 16)
NEW_CORE_NUMERIC_COLUMNS = (
    *(f"signed_efficiency_ratio_{days}d" for days in HORIZON_DAYS),
    *(f"ols_slope_t_signed_{days}d" for days in HORIZON_DAYS),
    *(f"bdci_score_{days}d" for days in HORIZON_DAYS),
    *(f"bci_imbalance_{days}d" for days in HORIZON_DAYS),
    *(f"wbi_score_{days}d" for days in HORIZON_DAYS),
    *(f"dii_score_{days}d" for days in HORIZON_DAYS),
    "body_to_range_ratio_median",
    "upper_wick_share_median",
    "lower_wick_share_median",
    "close_location_value_median",
    "parkinson_volatility",
    "rogers_satchell_volatility",
    "no_buffer_reversal_rate",
    "bipower_jump_share",
)
CORE_NUMERIC_COLUMNS = (*BASE_CORE_NUMERIC_COLUMNS, *NEW_CORE_NUMERIC_COLUMNS)
if len(CORE_NUMERIC_COLUMNS) != 56:  # pragma: no cover - import-time contract
    raise RuntimeError("core K-line attribute contract must contain exactly 56 columns")


def _rolling_sum(values: np.ndarray, window: int) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if window <= 0 or len(values) < window:
        return np.array([], dtype=float)
    cumulative = np.r_[0.0, np.cumsum(values, dtype=float)]
    return cumulative[window:] - cumulative[:-window]


def _signed_efficiency(log_close: np.ndarray, window: int) -> np.ndarray:
    if len(log_close) < window + 1:
        return np.array([], dtype=float)
    displacement = log_close[window:] - log_close[:-window]
    path = _rolling_sum(np.abs(np.diff(log_close)), window)
    return np.divide(displacement, path, out=np.zeros_like(displacement), where=path > 0)


def _signed_ols_t(values: np.ndarray, window: int) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if len(values) < window or window <= 2:
        return np.array([], dtype=float)
    count = len(values) - window + 1
    x = np.arange(window, dtype=float)
    x_mean = float(x.mean())
    xss = float(np.square(x - x_mean).sum())
    sum_y = _rolling_sum(values, window)
    sum_y2 = _rolling_sum(np.square(values), window)
    weighted = np.empty(count, dtype=float)
    weighted[0] = float(np.dot(x, values[:window]))
    if count > 1:
        delta = -(sum_y[:-1] - values[: count - 1]) + (window - 1) * values[window:]
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
    return r * np.sqrt((window - 2) / np.maximum(1.0 - r2, 1e-12))


def _rolling_direction_metrics(returns: np.ndarray, window: int) -> dict[str, np.ndarray]:
    if len(returns) < window:
        empty = np.array([], dtype=float)
        return {"bdci": empty, "bci": empty, "wbi": empty, "dii": empty}
    sign = np.sign(returns)
    nonzero = sign != 0
    pair_valid = (nonzero[1:] & nonzero[:-1]).astype(float)
    switches = ((sign[1:] != sign[:-1]) & (pair_valid > 0)).astype(float)
    valid_pairs = _rolling_sum(pair_valid, window - 1)
    switch_count = _rolling_sum(switches, window - 1)
    bdci = 1.0 - np.divide(
        switch_count,
        valid_pairs,
        out=np.zeros_like(switch_count),
        where=valid_pairs > 0,
    )
    valid = _rolling_sum(nonzero.astype(float), window)
    bci = np.divide(
        _rolling_sum(sign, window), valid, out=np.zeros_like(valid), where=valid > 0
    )
    path = _rolling_sum(np.abs(returns), window)
    net = _rolling_sum(returns, window)
    wbi = np.divide(net, path, out=np.zeros_like(net), where=path > 0)
    energy = np.sqrt(_rolling_sum(np.square(returns), window))
    impulse = np.divide(net, energy, out=np.zeros_like(net), where=energy > 0)
    efficiency = np.divide(net, path, out=np.zeros_like(net), where=path > 0)
    dii = impulse * (0.5 + 0.5 * np.abs(efficiency).clip(0.0, 1.0))
    return {"bdci": bdci, "bci": bci, "wbi": wbi, "dii": dii}


def _safe_median(values: np.ndarray) -> float:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    return float(np.median(finite)) if len(finite) else 0.0


def _bar_geometry(part: pd.DataFrame) -> dict[str, float]:
    open_ = part["open"].to_numpy(float)
    high = part["high"].to_numpy(float)
    low = part["low"].to_numpy(float)
    close = part["close"].to_numpy(float)
    log_range = np.log(high / low)
    body = np.abs(np.log(close / open_))
    upper = np.log(high / np.maximum(open_, close))
    lower = np.log(np.minimum(open_, close) / low)
    body_ratio = np.divide(body, log_range, out=np.zeros_like(body), where=log_range > 0)
    upper_share = np.divide(upper, log_range, out=np.zeros_like(upper), where=log_range > 0)
    lower_share = np.divide(lower, log_range, out=np.zeros_like(lower), where=log_range > 0)
    price_range = high - low
    clv = np.divide(
        2.0 * close - high - low,
        price_range,
        out=np.zeros_like(close),
        where=price_range > 0,
    )
    parkinson = math.sqrt(float(np.mean(np.square(log_range))) / (4.0 * math.log(2.0)))
    rs_terms = np.log(high / open_) * np.log(high / close) + np.log(low / open_) * np.log(low / close)
    rogers_satchell = math.sqrt(max(float(np.mean(rs_terms)), 0.0))
    return {
        "body_to_range_ratio_median": _safe_median(body_ratio),
        "upper_wick_share_median": _safe_median(upper_share),
        "lower_wick_share_median": _safe_median(lower_share),
        "close_location_value_median": _safe_median(clv),
        "parkinson_volatility": parkinson,
        "rogers_satchell_volatility": rogers_satchell,
    }


def _reversal_jump(returns: np.ndarray, *, bars_per_day: int) -> dict[str, float]:
    series = pd.Series(returns, dtype=float)
    rank_window = max(20, 20 * bars_per_day)
    prior_threshold = (
        series.abs()
        .rolling(rank_window, min_periods=rank_window)
        .quantile(0.80)
        .shift(1)
    )
    strong = series.abs().ge(prior_threshold)
    opposite = np.sign(series).ne(np.sign(series.shift(1)))
    abrupt = strong & strong.shift(1, fill_value=False) & opposite
    no_buffer_rate = float(abrupt.dropna().mean()) if len(abrupt) else 0.0
    rv = float(np.square(returns).sum())
    bv = (
        math.pi
        / 2.0
        * float((np.abs(returns[1:]) * np.abs(returns[:-1])).sum())
    ) if len(returns) > 1 else 0.0
    jump_share = max(rv - bv, 0.0) / rv if rv > 0 else 0.0
    return {
        "no_buffer_reversal_rate": no_buffer_rate,
        "bipower_jump_share": jump_share,
    }


def annual_core_extensions(
    frame: pd.DataFrame,
    *,
    carrier: str,
    years: tuple[int, ...],
    bars_per_day: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    timestamps = pd.DatetimeIndex(frame["timestamp"])
    for year in years:
        part = frame.loc[timestamps.year == year].copy()
        if len(part) < 100 * bars_per_day:
            raise ValueError(f"insufficient core attribute rows: {carrier} {year}")
        log_close = np.log(part["close"].to_numpy(float))
        returns = np.diff(log_close)
        row: dict[str, Any] = {"carrier": carrier, "year": int(year)}
        for days in HORIZON_DAYS:
            window = days * bars_per_day
            row[f"signed_efficiency_ratio_{days}d"] = _safe_median(
                _signed_efficiency(log_close, window)
            )
            row[f"ols_slope_t_signed_{days}d"] = _safe_median(
                _signed_ols_t(log_close, window)
            )
            direction = _rolling_direction_metrics(returns, window)
            row[f"bdci_score_{days}d"] = _safe_median(direction["bdci"])
            row[f"bci_imbalance_{days}d"] = _safe_median(direction["bci"])
            row[f"wbi_score_{days}d"] = _safe_median(direction["wbi"])
            row[f"dii_score_{days}d"] = _safe_median(direction["dii"])
        row.update(_bar_geometry(part))
        row.update(_reversal_jump(returns, bars_per_day=bars_per_day))
        rows.append(row)
    result = pd.DataFrame(rows)
    missing = sorted(set(NEW_CORE_NUMERIC_COLUMNS).difference(result.columns))
    if missing:
        raise RuntimeError(f"core extension columns missing: {missing}")
    return result


__all__ = [
    "BASE_CORE_NUMERIC_COLUMNS",
    "CORE_NUMERIC_COLUMNS",
    "HORIZON_DAYS",
    "NEW_CORE_NUMERIC_COLUMNS",
    "annual_core_extensions",
]
