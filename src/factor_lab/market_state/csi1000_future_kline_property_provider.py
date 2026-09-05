"""Research-only causal forecasts for supported future CSI1000 K-line properties."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError

PROVIDER_ID = "csi1000_future_kline_property_provider@1.0"
SUPPORTED_TARGETS = (
    "future_log_realized_variance",
    "future_log_close_path_range",
    "future_log_noise_inflation_1m_to_5m",
)


@dataclass(frozen=True, slots=True)
class FittedPropertyProvider:
    target_id: str
    horizon_bars: int
    feature_names: tuple[str, ...]
    feature_mean: tuple[float, ...]
    feature_scale: tuple[float, ...]
    coefficients: tuple[float, ...]
    intercept: float
    residual_std: float
    training_rows: int

    def __post_init__(self) -> None:
        if self.target_id not in SUPPORTED_TARGETS:
            raise ValidationError("unsupported future K-line property target")
        if self.horizon_bars < 2 or self.training_rows < len(self.feature_names) + 2:
            raise ValidationError("future K-line property fit lacks support")
        width = len(self.feature_names)
        if not all(len(values) == width for values in (self.feature_mean, self.feature_scale, self.coefficients)):
            raise ValidationError("future K-line property fit dimensions differ")
        if self.residual_std < 0.0 or not np.isfinite(self.residual_std):
            raise ValidationError("future K-line property residual scale is invalid")


@dataclass(frozen=True, slots=True)
class KlinePropertyForecastCard:
    provider_id: str
    target_id: str
    horizon_bars: int
    mean: float
    q10: float
    q50: float
    q90: float
    training_rows: int
    strategy_authority: bool = False
    routing_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.provider_id != PROVIDER_ID or self.target_id not in SUPPORTED_TARGETS:
            raise ValidationError("future K-line property card identity is invalid")
        if not self.q10 <= self.q50 <= self.q90:
            raise ValidationError("future K-line property quantiles are not ordered")
        if any((self.strategy_authority, self.routing_authority, self.production_authority)):
            raise ValidationError("research property card cannot grant authority")


def build_causal_property_features(
    close: pd.Series,
    *,
    windows: tuple[int, ...] = (32, 128, 512, 2048),
) -> pd.DataFrame:
    """Return price-only features ending at the current completed bar."""

    values = pd.to_numeric(close, errors="raise").astype(float)
    if values.le(0.0).any() or any(window < 2 for window in windows):
        raise ValidationError("causal property features require positive prices/windows")
    level = np.log(values)
    returns = level.diff()
    output = pd.DataFrame(index=close.index)
    for window in windows:
        rv = returns.pow(2).rolling(window, min_periods=window).sum()
        total_variation = returns.abs().rolling(window, min_periods=window).sum()
        path_range = level.rolling(window + 1, min_periods=window + 1).max() - level.rolling(window + 1, min_periods=window + 1).min()
        five_step = level.diff(5).abs().rolling(max(2, window // 5), min_periods=max(2, window // 5)).sum()
        output[f"log_rv_w{window}"] = np.log(rv.clip(lower=1e-12))
        output[f"log_range_w{window}"] = np.log(path_range.clip(lower=1e-12))
        output[f"endpoint_efficiency_w{window}"] = (level - level.shift(window)).abs() / total_variation.where(total_variation.gt(0.0))
        output[f"range_efficiency_w{window}"] = path_range / total_variation.where(total_variation.gt(0.0))
        output[f"log_noise_inflation_w{window}"] = np.log(total_variation.clip(lower=1e-12)) - np.log(five_step.clip(lower=1e-12))
    return output


def build_future_property_target(
    close: pd.Series,
    *,
    target_id: str,
    horizon_bars: int,
) -> pd.Series:
    """Build a training label; this function is forbidden on runtime feature paths."""

    if target_id not in SUPPORTED_TARGETS or horizon_bars < 2:
        raise ValidationError("future property target identity is invalid")
    values = pd.to_numeric(close, errors="raise").astype(float)
    if values.le(0.0).any():
        raise ValidationError("future property target requires positive prices")
    level = np.log(values)
    returns = level.diff()
    if target_id == "future_log_realized_variance":
        future = returns.pow(2).rolling(horizon_bars, min_periods=horizon_bars).sum().shift(-horizon_bars)
        return np.log(future.clip(lower=1e-12))
    indexer = pd.api.indexers.FixedForwardWindowIndexer(window_size=horizon_bars + 1)
    if target_id == "future_log_close_path_range":
        future_range = (
            level.rolling(indexer, min_periods=horizon_bars + 1).max() - level.rolling(indexer, min_periods=horizon_bars + 1).min()
        )
        return np.log(future_range.clip(lower=1e-12))
    result = pd.Series(np.nan, index=close.index, dtype=float)
    array = level.to_numpy(float)
    for location in range(len(array) - horizon_bars):
        path = array[location : location + horizon_bars + 1]
        tv1 = float(np.abs(np.diff(path)).sum())
        coordinates = list(range(0, horizon_bars + 1, 5))
        if coordinates[-1] != horizon_bars:
            coordinates.append(horizon_bars)
        tv5 = float(np.abs(np.diff(path[coordinates])).sum())
        if tv1 > 0.0 and tv5 > 0.0:
            result.iloc[location] = np.log(tv1 / tv5)
    return result


def fit_research_property_provider(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    target_id: str,
    horizon_bars: int,
    alpha: float = 10.0,
) -> FittedPropertyProvider:
    """Fit a deterministic standardized ridge model on an explicit prefix."""

    if alpha <= 0.0:
        raise ValidationError("future K-line provider alpha must be positive")
    joined = features.copy()
    joined["__target"] = pd.to_numeric(target, errors="coerce")
    joined = joined.replace([np.inf, -np.inf], np.nan).dropna()
    names = tuple(str(column) for column in features.columns)
    if len(joined) < len(names) + 2:
        raise ValidationError("future K-line provider training support is insufficient")
    x = joined[list(names)].to_numpy(float)
    y = joined["__target"].to_numpy(float)
    mean = x.mean(axis=0)
    scale = x.std(axis=0, ddof=1)
    scale = np.where(scale > 0.0, scale, 1.0)
    standardized = (x - mean) / scale
    y_mean = float(y.mean())
    centered = y - y_mean
    gram = standardized.T @ standardized + alpha * np.eye(len(names))
    coefficients = np.linalg.solve(gram, standardized.T @ centered)
    fitted = y_mean + standardized @ coefficients
    residual_std = float(np.std(y - fitted, ddof=1))
    return FittedPropertyProvider(
        target_id=target_id,
        horizon_bars=horizon_bars,
        feature_names=names,
        feature_mean=tuple(float(value) for value in mean),
        feature_scale=tuple(float(value) for value in scale),
        coefficients=tuple(float(value) for value in coefficients),
        intercept=y_mean,
        residual_std=residual_std,
        training_rows=len(joined),
    )


def forecast_property(
    fitted: FittedPropertyProvider,
    latest_features: pd.Series,
) -> KlinePropertyForecastCard:
    values = np.asarray([float(latest_features[name]) for name in fitted.feature_names], dtype=float)
    if not np.isfinite(values).all():
        raise ValidationError("latest future K-line property features are incomplete")
    mean = np.asarray(fitted.feature_mean)
    scale = np.asarray(fitted.feature_scale)
    coefficients = np.asarray(fitted.coefficients)
    prediction = float(fitted.intercept + ((values - mean) / scale) @ coefficients)
    normal = NormalDist(mu=prediction, sigma=max(fitted.residual_std, 1e-12))
    return KlinePropertyForecastCard(
        provider_id=PROVIDER_ID,
        target_id=fitted.target_id,
        horizon_bars=fitted.horizon_bars,
        mean=prediction,
        q10=float(normal.inv_cdf(0.10)),
        q50=prediction,
        q90=float(normal.inv_cdf(0.90)),
        training_rows=fitted.training_rows,
    )


__all__ = [
    "PROVIDER_ID",
    "SUPPORTED_TARGETS",
    "FittedPropertyProvider",
    "KlinePropertyForecastCard",
    "build_causal_property_features",
    "build_future_property_target",
    "fit_research_property_provider",
    "forecast_property",
]
