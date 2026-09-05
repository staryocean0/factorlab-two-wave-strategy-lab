# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Calibrated, multi-carrier research forecasts for future K-line properties."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.csi1000_future_kline_property_provider import (
    SUPPORTED_TARGETS as V1_TARGETS,
)
from factor_lab.market_state.csi1000_future_kline_property_provider import (
    build_causal_property_features,
    build_future_property_target,
)

PROVIDER_V2_ID = "timing_layer2_future_path_provider@2.0"
EXPERIMENTAL_TARGETS = ("future_log_path_inefficiency", "future_log_jump_burden")
SUPPORTED_TARGETS_V2 = (*V1_TARGETS, *EXPERIMENTAL_TARGETS)


@dataclass(frozen=True, slots=True)
class FittedFuturePathProviderV2:
    carrier_id: str
    view_id: str
    target_id: str
    horizon_bars: int
    feature_names: tuple[str, ...]
    feature_mean: tuple[float, ...]
    feature_scale: tuple[float, ...]
    coefficients: tuple[float, ...]
    intercept: float
    residual_quantiles: tuple[float, float, float]
    training_rows: int
    calibration_rows: int
    train_end: str
    calibration_end: str
    alpha: float
    runtime_feature_future_reads: int = 0
    strategy_authority: bool = False
    routing_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.target_id not in SUPPORTED_TARGETS_V2 or self.horizon_bars < 2:
            raise ValidationError("future path V2 target identity is invalid")
        width = len(self.feature_names)
        if width == 0 or not all(len(x) == width for x in (self.feature_mean, self.feature_scale, self.coefficients)):
            raise ValidationError("future path V2 fit dimensions differ")
        if self.training_rows < width + 2 or self.calibration_rows < 30:
            raise ValidationError("future path V2 train/calibration support is insufficient")
        if tuple(sorted(self.residual_quantiles)) != self.residual_quantiles:
            raise ValidationError("future path V2 residual quantiles are unordered")
        if self.runtime_feature_future_reads != 0 or any((self.strategy_authority, self.routing_authority, self.production_authority)):
            raise ValidationError("future path V2 cannot grant strategy authority")


@dataclass(frozen=True, slots=True)
class FuturePathForecastCardV2:
    provider_id: str
    carrier_id: str
    view_id: str
    target_id: str
    horizon_bars: int
    mean: float | None
    q10: float | None
    q50: float | None
    q90: float | None
    abstained: bool
    abstention_reason: str | None
    training_rows: int
    calibration_rows: int
    direction_forecast: bool = False
    strategy_authority: bool = False
    routing_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.provider_id != PROVIDER_V2_ID:
            raise ValidationError("future path V2 card provider identity changed")
        if self.abstained:
            if any(value is not None for value in (self.mean, self.q10, self.q50, self.q90)) or not self.abstention_reason:
                raise ValidationError("abstained future path card must omit forecasts and explain why")
        elif None in (self.mean, self.q10, self.q50, self.q90):
            raise ValidationError("non-abstained future path card is incomplete")
        elif not float(self.q10) <= float(self.q50) <= float(self.q90):
            raise ValidationError("future path V2 forecast quantiles are unordered")
        if self.direction_forecast or any((self.strategy_authority, self.routing_authority, self.production_authority)):
            raise ValidationError("future path V2 card cannot predict direction or grant authority")


def build_future_path_features(close: pd.Series, *, windows: tuple[int, ...] = (32, 128, 512, 2048)) -> pd.DataFrame:
    return build_causal_property_features(close, windows=windows)


def build_future_path_target(close: pd.Series, *, target_id: str, horizon_bars: int) -> pd.Series:
    if target_id in V1_TARGETS:
        return build_future_property_target(close, target_id=target_id, horizon_bars=horizon_bars)
    if target_id not in EXPERIMENTAL_TARGETS or horizon_bars < 2:
        raise ValidationError("future path V2 target is unsupported")
    values = pd.to_numeric(close, errors="raise").astype(float)
    if bool((values <= 0).any()):
        raise ValidationError("future path V2 target requires positive prices")
    level = np.log(values.to_numpy(float))
    result = pd.Series(np.nan, index=close.index, dtype=float)
    for location in range(len(level) - horizon_bars):
        path = level[location : location + horizon_bars + 1]
        returns = np.diff(path)
        total = float(np.abs(returns).sum())
        if target_id == "future_log_path_inefficiency":
            endpoint = abs(float(path[-1] - path[0]))
            if total > 0:
                result.iloc[location] = np.log(total / max(endpoint, 1e-12))
        else:
            rv = float(np.square(returns).sum())
            bv = float(np.pi / 2.0 * (np.abs(returns[1:]) * np.abs(returns[:-1])).sum()) if len(returns) > 1 else 0.0
            if rv > 0:
                result.iloc[location] = np.log(max((rv - bv) / rv, 1e-12))
    return result


def fit_future_path_provider_v2(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    carrier_id: str,
    view_id: str,
    target_id: str,
    horizon_bars: int,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
    alpha: float = 10.0,
) -> FittedFuturePathProviderV2:
    if target_id not in SUPPORTED_TARGETS_V2 or alpha <= 0:
        raise ValidationError("future path V2 fit configuration is invalid")
    if not isinstance(features.index, pd.DatetimeIndex) or features.index.tz is None:
        raise ValidationError("future path V2 features require a timezone-aware DatetimeIndex")
    if train_end.tzinfo is None or calibration_end.tzinfo is None or calibration_end <= train_end:
        raise ValidationError("future path V2 train/calibration boundaries are invalid")
    joined = features.copy()
    joined["__target"] = pd.to_numeric(target, errors="coerce")
    joined = joined.replace([np.inf, -np.inf], np.nan).dropna()
    train = joined.loc[joined.index <= train_end]
    calibration = joined.loc[(joined.index > train_end) & (joined.index <= calibration_end)]
    names = tuple(str(column) for column in features.columns)
    if len(train) < len(names) + 2 or len(calibration) < 30:
        raise ValidationError("future path V2 split support is insufficient")
    x = train[list(names)].to_numpy(float)
    y = train["__target"].to_numpy(float)
    mean = x.mean(axis=0)
    scale = np.where(x.std(axis=0, ddof=1) > 0, x.std(axis=0, ddof=1), 1.0)
    standardized = (x - mean) / scale
    intercept = float(y.mean())
    coefficients = np.linalg.solve(
        standardized.T @ standardized + alpha * np.eye(len(names)),
        standardized.T @ (y - intercept),
    )
    x_cal = calibration[list(names)].to_numpy(float)
    prediction = intercept + ((x_cal - mean) / scale) @ coefficients
    residual = calibration["__target"].to_numpy(float) - prediction
    quantiles = tuple(float(value) for value in np.quantile(residual, [0.1, 0.5, 0.9]))
    return FittedFuturePathProviderV2(
        carrier_id=carrier_id,
        view_id=view_id,
        target_id=target_id,
        horizon_bars=horizon_bars,
        feature_names=names,
        feature_mean=tuple(float(value) for value in mean),
        feature_scale=tuple(float(value) for value in scale),
        coefficients=tuple(float(value) for value in coefficients),
        intercept=intercept,
        residual_quantiles=quantiles,  # type: ignore[arg-type]
        training_rows=len(train),
        calibration_rows=len(calibration),
        train_end=train_end.isoformat(),
        calibration_end=calibration_end.isoformat(),
        alpha=alpha,
    )


def forecast_future_path_v2(fitted: FittedFuturePathProviderV2, latest_features: pd.Series) -> FuturePathForecastCardV2:
    try:
        values = np.asarray([float(latest_features[name]) for name in fitted.feature_names])
    except (KeyError, TypeError, ValueError):
        values = np.asarray([], dtype=float)
    if len(values) != len(fitted.feature_names) or not np.isfinite(values).all():
        return FuturePathForecastCardV2(
            PROVIDER_V2_ID,
            fitted.carrier_id,
            fitted.view_id,
            fitted.target_id,
            fitted.horizon_bars,
            None,
            None,
            None,
            None,
            True,
            "latest_features_incomplete",
            fitted.training_rows,
            fitted.calibration_rows,
        )
    prediction = float(
        fitted.intercept + ((values - np.asarray(fitted.feature_mean)) / np.asarray(fitted.feature_scale)) @ np.asarray(fitted.coefficients)
    )
    q10, q50, q90 = (prediction + value for value in fitted.residual_quantiles)
    return FuturePathForecastCardV2(
        PROVIDER_V2_ID,
        fitted.carrier_id,
        fitted.view_id,
        fitted.target_id,
        fitted.horizon_bars,
        prediction,
        q10,
        q50,
        q90,
        False,
        None,
        fitted.training_rows,
        fitted.calibration_rows,
    )


__all__ = [
    "EXPERIMENTAL_TARGETS",
    "PROVIDER_V2_ID",
    "SUPPORTED_TARGETS_V2",
    "FittedFuturePathProviderV2",
    "FuturePathForecastCardV2",
    "build_future_path_features",
    "build_future_path_target",
    "fit_future_path_provider_v2",
    "forecast_future_path_v2",
]
