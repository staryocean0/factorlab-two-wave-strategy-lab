"""Private causal channel math owned by the CloudRidge filtering strategy."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class _PriorRollingOls:
    slope: NDArray[np.float64]
    prediction: NDArray[np.float64]
    r2: NDArray[np.float64]
    residual_sigma: NDArray[np.float64]


def _prior_rolling_ols(values: NDArray[np.float64], window_bars: int) -> _PriorRollingOls:
    """Fit OLS windows ending immediately before each output position."""

    raw = np.asarray(values, dtype=float)
    if raw.ndim != 1:
        raise ValueError("values must be one-dimensional")
    if len(raw) < window_bars + 1:
        empty = np.full(len(raw), np.nan, dtype=float)
        return _PriorRollingOls(empty.copy(), empty.copy(), empty.copy(), empty.copy())
    if not np.isfinite(raw).all():
        raise ValueError("values must be finite")

    n = len(raw)
    # A log-price series may sit around an arbitrary additive level.  Remove a
    # fixed offset before moment calculations so changing the index base cannot
    # change residual variance through catastrophic cancellation.
    level_offset = float(raw[0])
    working = raw - level_offset
    x = np.arange(window_bars, dtype=float)
    x_mean = float(x.mean())
    sxx = float(np.square(x - x_mean).sum())
    positions = np.arange(window_bars, n)

    cumulative = np.concatenate(([0.0], np.cumsum(working)))
    cumulative_square = np.concatenate(([0.0], np.cumsum(np.square(working))))
    sum_y = cumulative[positions] - cumulative[positions - window_bars]
    sum_y_square = (
        cumulative_square[positions] - cumulative_square[positions - window_bars]
    )
    # np.correlate returns the dot product for each consecutive full window.
    dot_xy = np.correlate(working, x, mode="valid")[: n - window_bars]
    centered_xy = dot_xy - x_mean * sum_y
    slope_values = centered_xy / sxx
    intercept_values = sum_y / float(window_bars) - slope_values * x_mean
    predictions = (
        intercept_values + slope_values * float(window_bars) + level_offset
    )

    total_square = np.maximum(
        sum_y_square - np.square(sum_y) / float(window_bars),
        0.0,
    )
    residual_square = np.maximum(total_square - slope_values * centered_xy, 0.0)
    r2_values = np.divide(
        residual_square,
        total_square,
        out=np.ones_like(residual_square),
        where=total_square > np.finfo(float).eps,
    )
    r2_values = 1.0 - r2_values
    sigma_values = np.sqrt(residual_square / float(max(window_bars - 2, 1)))

    slope = np.full(n, np.nan, dtype=float)
    prediction = np.full(n, np.nan, dtype=float)
    r2 = np.full(n, np.nan, dtype=float)
    residual_sigma = np.full(n, np.nan, dtype=float)
    slope[positions] = slope_values
    prediction[positions] = predictions
    r2[positions] = r2_values
    residual_sigma[positions] = sigma_values
    return _PriorRollingOls(slope, prediction, r2, residual_sigma)


def _validate_ohlc(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"open", "high", "low", "close"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise KeyError(f"OHLC columns missing: {missing}")
    clean = frame.copy()
    for column in ("open", "high", "low", "close"):
        clean[column] = pd.to_numeric(clean[column], errors="raise").astype(float)
    values = clean[["open", "high", "low", "close"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or bool((values <= 0.0).any()):
        raise ValueError("OHLC values must be finite and positive")
    if bool((clean["high"] < clean[["open", "close"]].max(axis=1)).any()):
        raise ValueError("high must not be below open or close")
    if bool((clean["low"] > clean[["open", "close"]].min(axis=1)).any()):
        raise ValueError("low must not be above open or close")
    return clean
