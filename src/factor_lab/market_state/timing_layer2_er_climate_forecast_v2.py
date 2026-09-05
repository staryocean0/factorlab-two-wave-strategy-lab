# pyright: reportAny=false, reportArgumentType=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
"""V2: longer-train stage-ER forecasts with OHLC path quality and ridge."""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_layer2_attribute_followability import (
    trailing_log_realized_variance,
    trailing_ols_r2,
)
from factor_lab.market_state.timing_layer2_er_climate import climate_mean, native_efficiency_ratio
from factor_lab.market_state.timing_layer2_er_climate_forecast import (
    FittedClimateForecast,
    _origin_cutoff,
    _pair_frame,
    _run_length,
    fit_climate_forecast,
    predict_climate_forecast,
    score_forecast,
)

V2_ID: Final[str] = "timing_layer2_er_climate_forecast@2.0"
STAGE_HORIZONS: Final[tuple[int, ...]] = (10, 15, 20, 30, 40, 60)
RIDGE_ALPHA: Final[float] = 10.0
V2_MODELS: Final[tuple[str, ...]] = (
    "copy",
    "median",
    "ar1",
    "shrink_median",
    "qbin5",
    "ridge_pack",
)


def stage_range_efficiency(bars: pd.DataFrame, *, horizon: int) -> pd.Series:
    if horizon < 2:
        raise ValidationError("stage range efficiency horizon must be at least 2")
    required = {"high", "low", "close"}
    missing = sorted(required.difference(bars.columns))
    if missing:
        raise ValidationError(f"stage range efficiency missing columns: {missing}")
    high = pd.to_numeric(bars["high"], errors="raise").astype(float)
    low = pd.to_numeric(bars["low"], errors="raise").astype(float)
    close = pd.to_numeric(bars["close"], errors="raise").astype(float)
    if (close <= 0).any() or (high < low).any():
        raise ValidationError("stage range efficiency prices are invalid")
    span = horizon + 1
    envelope = high.rolling(span, min_periods=span).max() - low.rolling(span, min_periods=span).min()
    net = (close - close.shift(horizon)).abs()
    return (net / envelope.replace(0.0, np.nan)).rename(f"range_eff_{horizon}")


def build_stage_features(bars: pd.DataFrame, *, horizon: int, median: float) -> pd.DataFrame:
    close = pd.Series(pd.to_numeric(bars["close"], errors="raise").astype(float).to_numpy(), index=bars.index)
    er = native_efficiency_ratio(close, window=horizon)
    half = max(horizon // 2, 5)
    slow = horizon * 3
    frame = pd.DataFrame(
        {
            "er_now": er,
            "er_half": native_efficiency_ratio(close, window=half),
            "er_slow": climate_mean(er, window=max(slow, horizon + 5)),
            "er_dev": er - climate_mean(er, window=max(slow, horizon + 5)),
            "range_eff": stage_range_efficiency(bars, horizon=horizon),
            "ols_r2": trailing_ols_r2(close, horizon_bars=max(horizon, 4)),
            "rv": trailing_log_realized_variance(close, horizon_bars=horizon),
            "high_run": _run_length(er > median),
            "low_run": _run_length(er < median),
        },
        index=bars.index,
    )
    return frame.replace([np.inf, -np.inf], np.nan)


def fit_ridge_pack(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    horizon: int,
    median: float,
    train_end: pd.Timestamp,
    extra: tuple[str, ...] = ("er_now", "er_half", "er_dev", "range_eff", "ols_r2", "rv", "high_run", "low_run"),
) -> FittedClimateForecast:
    train = _pair_frame(
        features,
        target,
        start=features.index.min(),
        end=train_end,
        extra=tuple(name for name in extra if name != "er_now"),
        horizon=horizon,
    )
    names = ["er_now", *[name for name in extra if name != "er_now"]]
    names = [name for name in names if name in train.columns]
    x = train.loc[:, names].to_numpy(float)
    y = train["target"].to_numpy(float)
    mean = x.mean(axis=0)
    scale = x.std(axis=0, ddof=1)
    scale = np.where(scale > 0, scale, 1.0)
    standardized = (x - mean) / scale
    intercept = float(y.mean())
    coef = np.linalg.solve(
        standardized.T @ standardized + RIDGE_ALPHA * np.eye(len(names)),
        standardized.T @ (y - intercept),
    )
    return FittedClimateForecast(
        model_id="ridge_pack",
        native_window=horizon,
        horizon=horizon,
        median=float(median),
        extra=tuple(names),
        intercept=intercept,
        coefficients=tuple(float(value) for value in coef),
        bin_edges=tuple(float(value) for value in mean),
        bin_means=tuple(float(value) for value in scale),
        train_rows=len(train),
    )


def predict_ridge_pack(fitted: FittedClimateForecast, features: pd.DataFrame) -> pd.Series:
    names = list(fitted.extra)
    matrix = features.loc[:, names].to_numpy(float)
    mean = np.asarray(fitted.bin_edges)
    scale = np.asarray(fitted.bin_means)
    pred = pd.Series(np.full(len(features), np.nan), index=features.index)
    ok = np.isfinite(matrix).all(axis=1)
    pred.loc[ok] = fitted.intercept + ((matrix[ok] - mean) / scale) @ np.asarray(fitted.coefficients)
    return pred.rename("ridge_pack")


__all__ = [
    "RIDGE_ALPHA",
    "STAGE_HORIZONS",
    "V2_ID",
    "V2_MODELS",
    "build_stage_features",
    "fit_climate_forecast",
    "fit_ridge_pack",
    "predict_climate_forecast",
    "predict_ridge_pack",
    "score_forecast",
    "stage_range_efficiency",
    "_origin_cutoff",
]
