# pyright: reportAny=false, reportArgumentType=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
"""Causal forecasts of the next-block average path-efficiency climate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_layer2_attribute_followability import trailing_log_realized_variance
from factor_lab.market_state.timing_layer2_er_climate import climate_mean, native_efficiency_ratio

FORECAST_ID: Final[str] = "timing_layer2_er_climate_forecast@1.0"
NATIVE_WINDOWS: Final[tuple[int, ...]] = (8, 16, 32)
HORIZONS: Final[tuple[int, ...]] = (20, 40, 60, 80)
MODEL_IDS: Final[tuple[str, ...]] = (
    "copy",
    "median",
    "ar1",
    "shrink_median",
    "qbin5",
    "har_er",
    "har_er_rv",
    "har_er_rv_run",
    "ridge_pack",
)


def future_block_mean(native_er: pd.Series, *, horizon: int) -> pd.Series:
    if horizon < 2:
        raise ValidationError("future block horizon must be at least 2")
    trailing = native_er.rolling(horizon, min_periods=horizon).mean()
    future = trailing.shift(-horizon)
    future.iloc[-horizon:] = np.nan
    return future.rename(f"future_er_mean_{horizon}")


def _run_length(flag: pd.Series) -> pd.Series:
    values = flag.fillna(False).astype(bool).to_numpy()
    out = np.zeros(len(values), dtype=float)
    run = 0
    for i, on in enumerate(values):
        run = run + 1 if on else 0
        out[i] = float(run)
    return pd.Series(out, index=flag.index, name="run_length")


def build_forecast_features(close: pd.Series, *, native_window: int, median: float) -> pd.DataFrame:
    native = native_efficiency_ratio(close, window=native_window)
    rv = trailing_log_realized_variance(close, horizon_bars=max(native_window, 20))
    frame = pd.DataFrame(
        {
            "er_now": native,
            "er_sma20": climate_mean(native, window=20),
            "er_sma40": climate_mean(native, window=40),
            "er_sma60": climate_mean(native, window=60),
            "er_sma80": climate_mean(native, window=80),
            "er_sma120": climate_mean(native, window=120),
            "rv_now": rv,
            "high_run": _run_length(native > median),
            "low_run": _run_length(native < median),
        },
        index=close.index,
    )
    return frame.replace([np.inf, -np.inf], np.nan)


def _origin_cutoff(index: pd.DatetimeIndex, *, end: pd.Timestamp, horizon: int) -> pd.Series:
    pos = pd.Series(np.arange(len(index)), index=index)
    in_period = pos.loc[:end]
    if in_period.empty:
        raise ValidationError("forecast period is empty")
    end_pos = int(in_period.max())
    return pos.reindex(index) + horizon <= end_pos


def _pair_frame(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    extra: tuple[str, ...],
    horizon: int,
) -> pd.DataFrame:
    cols = ["er_now", *extra]
    missing = [name for name in cols if name not in features.columns]
    if missing:
        raise ValidationError(f"forecast features missing: {missing}")
    joined = features.loc[:, cols].copy()
    joined["target"] = pd.to_numeric(target, errors="coerce")
    joined = joined.replace([np.inf, -np.inf], np.nan).dropna()
    inside = (joined.index >= start) & (joined.index <= end)
    causal = _origin_cutoff(features.index, end=end, horizon=horizon).reindex(joined.index).fillna(False)
    joined = joined.loc[inside & causal.astype(bool)]
    if len(joined) < 40:
        raise ValidationError("forecast pair support is insufficient")
    return joined


def _ols(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    design = np.column_stack([np.ones(len(x)), x])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    return coef, float(coef[0])


@dataclass(frozen=True, slots=True)
class FittedClimateForecast:
    model_id: str
    native_window: int
    horizon: int
    median: float
    extra: tuple[str, ...]
    intercept: float
    coefficients: tuple[float, ...]
    bin_edges: tuple[float, ...]
    bin_means: tuple[float, ...]
    train_rows: int

    def __post_init__(self) -> None:
        if self.model_id not in MODEL_IDS:
            raise ValidationError("unknown climate forecast model")
        if self.train_rows < 40:
            raise ValidationError("climate forecast train support is insufficient")


def fit_climate_forecast(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    model_id: str,
    native_window: int,
    horizon: int,
    median: float,
    train_end: pd.Timestamp,
) -> FittedClimateForecast:
    extra_by_model: dict[str, tuple[str, ...]] = {
        "copy": (),
        "median": (),
        "ar1": (),
        "shrink_median": (),
        "qbin5": (),
        "har_er": ("er_sma20", "er_sma60", "er_sma120"),
        "har_er_rv": ("er_sma20", "er_sma60", "er_sma120", "rv_now"),
        "har_er_rv_run": ("er_sma20", "er_sma60", "er_sma120", "rv_now", "high_run", "low_run"),
        "ridge_pack": ("er_sma20", "er_sma60", "er_sma120", "rv_now"),
    }
    extra = extra_by_model[model_id]
    train = _pair_frame(features, target, start=features.index.min(), end=train_end, extra=extra, horizon=horizon)
    y = train["target"].to_numpy(float)
    now = train["er_now"].to_numpy(float)
    if model_id == "copy":
        intercept, coef, edges, means = 0.0, (1.0,), (), ()
    elif model_id == "median":
        intercept, coef, edges, means = float(median), (), (), ()
    elif model_id == "ar1":
        coefs, intercept = _ols(now.reshape(-1, 1), y)
        coef = tuple(float(value) for value in coefs[1:])
        edges, means = (), ()
    elif model_id == "shrink_median":
        gap = (float(median) - now).reshape(-1, 1)
        delta = y - now
        coefs, _intercept = _ols(gap, delta)
        # future = now + k*(median-now) + c; store c as intercept, k as coefficient
        intercept = float(coefs[0])
        coef = (float(coefs[1]),)
        edges, means = (), ()
    elif model_id == "qbin5":
        quantiles = np.quantile(now, [0.2, 0.4, 0.6, 0.8])
        edges = tuple(float(value) for value in quantiles)
        bins = np.digitize(now, quantiles, right=True)
        means = tuple(float(y[bins == i].mean()) if np.any(bins == i) else float(median) for i in range(5))
        intercept, coef = 0.0, ()
    else:
        x = train.loc[:, list(extra)].to_numpy(float)
        coefs, intercept = _ols(x, y)
        coef = tuple(float(value) for value in coefs[1:])
        edges, means = (), ()
    return FittedClimateForecast(
        model_id=model_id,
        native_window=native_window,
        horizon=horizon,
        median=float(median),
        extra=extra,
        intercept=float(intercept),
        coefficients=coef,
        bin_edges=edges,
        bin_means=means,
        train_rows=len(train),
    )


def predict_climate_forecast(fitted: FittedClimateForecast, features: pd.DataFrame) -> pd.Series:
    now = pd.to_numeric(features["er_now"], errors="coerce")
    if fitted.model_id == "copy":
        pred = now
    elif fitted.model_id == "median":
        pred = pd.Series(fitted.median, index=features.index)
    elif fitted.model_id == "ar1":
        pred = fitted.intercept + fitted.coefficients[0] * now
    elif fitted.model_id == "shrink_median":
        pred = now + fitted.intercept + fitted.coefficients[0] * (fitted.median - now)
    elif fitted.model_id == "qbin5":
        bins = np.digitize(now.to_numpy(float), np.asarray(fitted.bin_edges), right=True)
        pred = pd.Series(np.asarray(fitted.bin_means)[np.clip(bins, 0, 4)], index=features.index)
        pred = pred.where(now.notna())
    else:
        matrix = features.loc[:, list(fitted.extra)].to_numpy(float)
        pred = pd.Series(np.full(len(features), np.nan), index=features.index)
        ok = np.isfinite(matrix).all(axis=1)
        pred.loc[ok] = fitted.intercept + matrix[ok] @ np.asarray(fitted.coefficients)
    return pred.rename(fitted.model_id)


def score_forecast(
    pred: pd.Series,
    target: pd.Series,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    horizon: int,
    index: pd.DatetimeIndex,
) -> dict[str, float]:
    joined = pd.concat({"pred": pred, "target": target}, axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    inside = (joined.index >= start) & (joined.index <= end)
    causal = _origin_cutoff(index, end=end, horizon=horizon).reindex(joined.index).fillna(False)
    joined = joined.loc[inside & causal.astype(bool)]
    if len(joined) < 40:
        raise ValidationError("forecast score support is insufficient")
    error = joined["pred"] - joined["target"]
    return {
        "n": float(len(joined)),
        "mae": float(error.abs().mean()),
        "rmse": float(np.sqrt(np.square(error).mean())),
        "rank_ic": float(joined["pred"].corr(joined["target"], method="spearman")),
    }


__all__ = [
    "FORECAST_ID",
    "HORIZONS",
    "MODEL_IDS",
    "NATIVE_WINDOWS",
    "FittedClimateForecast",
    "build_forecast_features",
    "fit_climate_forecast",
    "future_block_mean",
    "predict_climate_forecast",
    "score_forecast",
    "_origin_cutoff",
]
