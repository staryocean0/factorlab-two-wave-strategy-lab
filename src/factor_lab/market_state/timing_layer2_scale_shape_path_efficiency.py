# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Split common RV energy scale from residual shape for next-window ER."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_layer2_adaptive_horizon_path_efficiency import (
    rv_intensity_term_structure,
)
from factor_lab.market_state.timing_layer2_next_path_efficiency import (
    PRIMARY_HORIZON_BARS,
    build_future_efficiency_ratio,
    build_future_log_path_length,
    build_lookback_mean_er_feature,
    build_trailing_native_er_feature,
    fit_lookback_mean_er,
    fit_trailing_native_er,
    forecast_clipped_er_frame,
    forecast_linear_follower_frame,
)

SCALE_SHAPE_ID = "timing_layer2_scale_shape_path_efficiency@1.0"
INTENSITY_HORIZONS = (5, 16, 64)
SCALE_SHAPE_METHODS = ("common_scale_only", "shape_residual", "scale_and_shape")


@dataclass(frozen=True, slots=True)
class FittedScaleShape:
    method_id: str
    target_id: str
    horizon_bars: int
    feature_names: tuple[str, ...]
    coefficients: tuple[float, ...]
    intercept: float
    residual_quantiles: tuple[float, float, float]
    training_rows: int
    calibration_rows: int
    train_end: str
    calibration_end: str
    runtime_feature_future_reads: int = 0
    direction_forecast: bool = False
    strategy_authority: bool = False
    routing_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.method_id not in SCALE_SHAPE_METHODS:
            raise ValidationError("unsupported scale-shape method")
        if self.runtime_feature_future_reads != 0:
            raise ValidationError("scale-shape runtime features cannot read the future")
        if any((self.direction_forecast, self.strategy_authority, self.routing_authority, self.production_authority)):
            raise ValidationError("scale-shape cards cannot grant strategy authority")
        if len(self.feature_names) != len(self.coefficients):
            raise ValidationError("scale-shape coefficient width mismatch")
        if self.training_rows < len(self.feature_names) + 2 or self.calibration_rows < 30:
            raise ValidationError("scale-shape train/calibration support is insufficient")
        if tuple(sorted(self.residual_quantiles)) != self.residual_quantiles:
            raise ValidationError("scale-shape residual quantiles are unordered")


def build_scale_shape_features(close: pd.Series) -> pd.DataFrame:
    intensity = rv_intensity_term_structure(close, horizons=INTENSITY_HORIZONS)
    common = intensity.mean(axis=1)
    output = pd.DataFrame(
        {
            "common_scale": common,
            "shape_short": intensity[5] - common,
            "shape_long": intensity[64] - common,
        },
        index=close.index,
    )
    return output.replace([np.inf, -np.inf], np.nan)


def features_for_method(close: pd.Series, *, method_id: str) -> pd.DataFrame:
    full = build_scale_shape_features(close)
    if method_id == "common_scale_only":
        return full.loc[:, ["common_scale"]].copy()
    if method_id == "shape_residual":
        return full.loc[:, ["shape_short", "shape_long"]].copy()
    if method_id == "scale_and_shape":
        return full.copy()
    raise ValidationError("unsupported scale-shape method")


def _fit_linear(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    method_id: str,
    target_id: str,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
) -> FittedScaleShape:
    if not isinstance(features.index, pd.DatetimeIndex) or features.index.tz is None:
        raise ValidationError("scale-shape features require a timezone-aware DatetimeIndex")
    if train_end.tzinfo is None or calibration_end.tzinfo is None or calibration_end <= train_end:
        raise ValidationError("scale-shape train/calibration boundaries are invalid")
    joined = features.copy()
    joined["__target"] = pd.to_numeric(target, errors="coerce")
    joined = joined.replace([np.inf, -np.inf], np.nan).dropna()
    train = joined.loc[joined.index <= train_end]
    calibration = joined.loc[(joined.index > train_end) & (joined.index <= calibration_end)]
    names = tuple(str(column) for column in features.columns)
    if len(train) < len(names) + 2 or len(calibration) < 30:
        raise ValidationError("scale-shape split support is insufficient")
    x = train[list(names)].to_numpy(float)
    y = train["__target"].to_numpy(float)
    design = np.column_stack([np.ones(len(x)), x])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    intercept = float(coefficients[0])
    betas = tuple(float(value) for value in coefficients[1:])
    prediction = intercept + calibration[list(names)].to_numpy(float) @ np.asarray(betas)
    residual = calibration["__target"].to_numpy(float) - prediction
    quantiles = tuple(float(value) for value in np.quantile(residual, [0.1, 0.5, 0.9]))
    return FittedScaleShape(
        method_id=method_id,
        target_id=target_id,
        horizon_bars=PRIMARY_HORIZON_BARS,
        feature_names=names,
        coefficients=betas,
        intercept=intercept,
        residual_quantiles=quantiles,  # type: ignore[arg-type]
        training_rows=len(train),
        calibration_rows=len(calibration),
        train_end=train_end.isoformat(),
        calibration_end=calibration_end.isoformat(),
    )


def fit_scale_shape(
    close: pd.Series,
    target: pd.Series,
    *,
    method_id: str,
    target_id: str,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
) -> FittedScaleShape:
    return _fit_linear(
        features_for_method(close, method_id=method_id),
        target,
        method_id=method_id,
        target_id=target_id,
        train_end=train_end,
        calibration_end=calibration_end,
    )


__all__ = [
    "INTENSITY_HORIZONS",
    "PRIMARY_HORIZON_BARS",
    "SCALE_SHAPE_ID",
    "SCALE_SHAPE_METHODS",
    "FittedScaleShape",
    "build_future_efficiency_ratio",
    "build_future_log_path_length",
    "build_lookback_mean_er_feature",
    "build_scale_shape_features",
    "build_trailing_native_er_feature",
    "features_for_method",
    "fit_lookback_mean_er",
    "fit_scale_shape",
    "fit_trailing_native_er",
    "forecast_clipped_er_frame",
    "forecast_linear_follower_frame",
]
