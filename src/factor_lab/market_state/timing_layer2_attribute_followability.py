# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Causal Layer-2 attribute followability cards: EWMA, HAR, and FuturePath ridge.

This module forecasts K-line attributes. It does not rank strategies, emit
routing states, or grant production authority.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.lat_kline_attribute_atlas import _rolling_trend

FOLLOWABILITY_ID = "timing_layer2_attribute_followability@1.0"
HAR_DAY = 1
HAR_WEEK = 5
HAR_MONTH = 22
EWMA_SPAN_BARS = 20
PRIMARY_HORIZON_BARS = 20
TWIN_HORIZON_BARS = 5
RIDGE_WINDOWS = (32, 128, 512, 2048)


@dataclass(frozen=True, slots=True)
class FittedLinearFollower:
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
        if self.method_id not in {"ewma_persistence", "har"}:
            raise ValidationError("unsupported followability method")
        if self.horizon_bars < 2:
            raise ValidationError("followability horizon must be at least 2 bars")
        if self.runtime_feature_future_reads != 0:
            raise ValidationError("followability runtime features cannot read the future")
        if any((self.direction_forecast, self.strategy_authority, self.routing_authority, self.production_authority)):
            raise ValidationError("followability cards cannot grant strategy authority")
        if len(self.feature_names) != len(self.coefficients):
            raise ValidationError("followability coefficient width mismatch")
        if self.training_rows < len(self.feature_names) + 2 or self.calibration_rows < 30:
            raise ValidationError("followability train/calibration support is insufficient")
        if tuple(sorted(self.residual_quantiles)) != self.residual_quantiles:
            raise ValidationError("followability residual quantiles are unordered")



def build_future_ols_r2_target(close: pd.Series, *, horizon_bars: int) -> pd.Series:
    trailing = trailing_ols_r2(close, horizon_bars=horizon_bars)
    future = trailing.shift(-horizon_bars)
    future.iloc[-horizon_bars:] = np.nan
    return future.rename(f"future_ols_r2_{horizon_bars}")


def trailing_ols_r2(close: pd.Series, *, horizon_bars: int) -> pd.Series:
    values = pd.to_numeric(close, errors="raise").astype(float)
    if values.le(0.0).any() or horizon_bars < 3:
        raise ValidationError("trailing ols_r2 requires positive prices and horizon>=3")
    level = np.log(values.to_numpy(float))
    _t_abs, r2 = _rolling_trend(level, horizon_bars)
    aligned = np.full(len(values), np.nan)
    aligned[horizon_bars - 1 :] = r2
    return pd.Series(aligned, index=close.index, name=f"trailing_ols_r2_{horizon_bars}")


def build_har_r2_features(close: pd.Series) -> pd.DataFrame:
    output = pd.DataFrame(index=close.index)
    for window in (4, 8, 16):
        output[f"r2_scale_{window}"] = trailing_ols_r2(close, horizon_bars=window)
    return output.replace([np.inf, -np.inf], np.nan)

def trailing_log_realized_variance(close: pd.Series, *, horizon_bars: int) -> pd.Series:
    values = pd.to_numeric(close, errors="raise").astype(float)
    if values.le(0.0).any() or horizon_bars < 2:
        raise ValidationError("trailing RV requires positive prices and horizon>=2")
    returns = np.log(values).diff()
    rv = returns.pow(2).rolling(horizon_bars, min_periods=horizon_bars).sum()
    return np.log(rv.clip(lower=1e-12)).rename("trailing_log_rv")


def build_har_rv_features(close: pd.Series) -> pd.DataFrame:
    values = pd.to_numeric(close, errors="raise").astype(float)
    if values.le(0.0).any():
        raise ValidationError("HAR features require positive prices")
    daily = np.log(values).diff().pow(2)
    weekly = daily.rolling(HAR_WEEK, min_periods=HAR_WEEK).mean()
    monthly = daily.rolling(HAR_MONTH, min_periods=HAR_MONTH).mean()
    output = pd.DataFrame(
        {
            "log_rv_d": np.log(daily.clip(lower=1e-12)),
            "log_rv_w": np.log(weekly.clip(lower=1e-12)),
            "log_rv_m": np.log(monthly.clip(lower=1e-12)),
        },
        index=close.index,
    )
    return output.replace([np.inf, -np.inf], np.nan)


def trailing_log_path_inefficiency(close: pd.Series, *, horizon_bars: int) -> pd.Series:
    values = pd.to_numeric(close, errors="raise").astype(float)
    if values.le(0.0).any() or horizon_bars < 2:
        raise ValidationError("trailing path inefficiency requires positive prices and horizon>=2")
    level = np.log(values)
    returns = level.diff()
    total = returns.abs().rolling(horizon_bars, min_periods=horizon_bars).sum()
    endpoint = (level - level.shift(horizon_bars)).abs()
    inefficiency = np.log(total.clip(lower=1e-12) / endpoint.clip(lower=1e-12))
    return inefficiency.rename("trailing_log_path_inefficiency")


def trailing_attribute(close: pd.Series, *, target_id: str, horizon_bars: int) -> pd.Series:
    if target_id == "future_log_realized_variance":
        return trailing_log_realized_variance(close, horizon_bars=horizon_bars)
    if target_id == "future_log_path_inefficiency":
        return trailing_log_path_inefficiency(close, horizon_bars=horizon_bars)
    if target_id == "future_ols_r2":
        return trailing_ols_r2(close, horizon_bars=horizon_bars)
    raise ValidationError(f"unsupported followability target: {target_id}")


def build_ewma_feature(close: pd.Series, *, target_id: str, horizon_bars: int) -> pd.DataFrame:
    trailing = trailing_attribute(close, target_id=target_id, horizon_bars=horizon_bars)
    ewma = trailing.ewm(span=EWMA_SPAN_BARS, min_periods=EWMA_SPAN_BARS, adjust=False).mean()
    return pd.DataFrame({"ewma_trailing_attribute": ewma}, index=close.index)


def build_har_inefficiency_features(close: pd.Series) -> pd.DataFrame:
    output = pd.DataFrame(index=close.index)
    for window in (5, 20, 60):
        output[f"log_ineff_{window}"] = trailing_log_path_inefficiency(close, horizon_bars=window)
    return output.replace([np.inf, -np.inf], np.nan)


def build_har_features(close: pd.Series, *, target_id: str) -> pd.DataFrame:
    if target_id == "future_log_realized_variance":
        return build_har_rv_features(close)
    if target_id == "future_log_path_inefficiency":
        return build_har_inefficiency_features(close)
    if target_id == "future_ols_r2":
        return build_har_r2_features(close)
    raise ValidationError(f"unsupported HAR target: {target_id}")


def _fit_linear(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    method_id: str,
    target_id: str,
    horizon_bars: int,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
) -> FittedLinearFollower:
    if not isinstance(features.index, pd.DatetimeIndex) or features.index.tz is None:
        raise ValidationError("followability features require a timezone-aware DatetimeIndex")
    if train_end.tzinfo is None or calibration_end.tzinfo is None or calibration_end <= train_end:
        raise ValidationError("followability train/calibration boundaries are invalid")
    joined = features.copy()
    joined["__target"] = pd.to_numeric(target, errors="coerce")
    joined = joined.replace([np.inf, -np.inf], np.nan).dropna()
    train = joined.loc[joined.index <= train_end]
    calibration = joined.loc[(joined.index > train_end) & (joined.index <= calibration_end)]
    names = tuple(str(column) for column in features.columns)
    if len(train) < len(names) + 2 or len(calibration) < 30:
        raise ValidationError("followability split support is insufficient")
    x = train[list(names)].to_numpy(float)
    y = train["__target"].to_numpy(float)
    design = np.column_stack([np.ones(len(x)), x])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    intercept = float(coefficients[0])
    betas = tuple(float(value) for value in coefficients[1:])
    x_cal = calibration[list(names)].to_numpy(float)
    prediction = intercept + x_cal @ np.asarray(betas)
    residual = calibration["__target"].to_numpy(float) - prediction
    quantiles = tuple(float(value) for value in np.quantile(residual, [0.1, 0.5, 0.9]))
    return FittedLinearFollower(
        method_id=method_id,
        target_id=target_id,
        horizon_bars=horizon_bars,
        feature_names=names,
        coefficients=betas,
        intercept=intercept,
        residual_quantiles=quantiles,  # type: ignore[arg-type]
        training_rows=len(train),
        calibration_rows=len(calibration),
        train_end=train_end.isoformat(),
        calibration_end=calibration_end.isoformat(),
    )


def fit_ewma_follower(
    close: pd.Series,
    target: pd.Series,
    *,
    target_id: str,
    horizon_bars: int,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
) -> FittedLinearFollower:
    return _fit_linear(
        build_ewma_feature(close, target_id=target_id, horizon_bars=horizon_bars),
        target,
        method_id="ewma_persistence",
        target_id=target_id,
        horizon_bars=horizon_bars,
        train_end=train_end,
        calibration_end=calibration_end,
    )


def fit_har_follower(
    close: pd.Series,
    target: pd.Series,
    *,
    target_id: str,
    horizon_bars: int,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
) -> FittedLinearFollower:
    return _fit_linear(
        build_har_features(close, target_id=target_id),
        target,
        method_id="har",
        target_id=target_id,
        horizon_bars=horizon_bars,
        train_end=train_end,
        calibration_end=calibration_end,
    )


def forecast_linear_follower_frame(fitted: FittedLinearFollower, features: pd.DataFrame) -> pd.DataFrame:
    missing = [name for name in fitted.feature_names if name not in features.columns]
    if missing:
        raise ValidationError(f"followability features missing columns: {missing}")
    matrix = features.loc[:, list(fitted.feature_names)].to_numpy(float)
    finite = np.isfinite(matrix).all(axis=1)
    means = np.full(len(features), np.nan)
    means[finite] = fitted.intercept + matrix[finite] @ np.asarray(fitted.coefficients)
    q10 = means + fitted.residual_quantiles[0]
    q50 = means + fitted.residual_quantiles[1]
    q90 = means + fitted.residual_quantiles[2]
    return pd.DataFrame(
        {
            "mean": means,
            "q10": q10,
            "q50": q50,
            "q90": q90,
            "abstained": ~finite,
        },
        index=features.index,
    )


def forecast_linear_follower(fitted: FittedLinearFollower, latest_features: pd.Series) -> dict[str, object]:
    try:
        values = np.asarray([float(latest_features[name]) for name in fitted.feature_names])
    except (KeyError, TypeError, ValueError):
        values = np.asarray([], dtype=float)
    if len(values) != len(fitted.feature_names) or not np.isfinite(values).all():
        return {
            "method_id": fitted.method_id,
            "target_id": fitted.target_id,
            "mean": None,
            "q10": None,
            "q50": None,
            "q90": None,
            "abstained": True,
            "abstention_reason": "latest_features_incomplete",
            "direction_forecast": False,
            "production_authority": False,
        }
    prediction = float(fitted.intercept + values @ np.asarray(fitted.coefficients))
    q10, q50, q90 = (prediction + value for value in fitted.residual_quantiles)
    if not q10 <= q50 <= q90:
        raise ValidationError("followability forecast quantiles are unordered")
    return {
        "method_id": fitted.method_id,
        "target_id": fitted.target_id,
        "mean": prediction,
        "q10": q10,
        "q50": q50,
        "q90": q90,
        "abstained": False,
        "abstention_reason": None,
        "direction_forecast": False,
        "production_authority": False,
    }


def score_followability(forecast: pd.Series, realized: pd.Series) -> dict[str, float]:
    joined = pd.concat({"forecast": forecast, "realized": realized}, axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(joined) < 30:
        raise ValidationError("followability score support is insufficient")
    error = joined["forecast"] - joined["realized"]
    mae = float(error.abs().mean())
    rmse = float(np.sqrt(np.square(error).mean()))
    rank_ic = float(joined["forecast"].corr(joined["realized"], method="spearman"))
    return {
        "n": float(len(joined)),
        "mae": mae,
        "rmse": rmse,
        "rank_ic": rank_ic,
    }


def quantile_coverage(realized: pd.Series, q10: pd.Series, q50: pd.Series, q90: pd.Series) -> dict[str, float]:
    joined = pd.concat({"y": realized, "q10": q10, "q50": q50, "q90": q90}, axis=1).dropna()
    if len(joined) < 30:
        raise ValidationError("quantile coverage support is insufficient")
    return {
        "n": float(len(joined)),
        "hit_q10": float((joined["y"] <= joined["q10"]).mean()),
        "hit_q50": float((joined["y"] <= joined["q50"]).mean()),
        "hit_q90": float((joined["y"] <= joined["q90"]).mean()),
    }


__all__ = [
    "EWMA_SPAN_BARS",
    "FOLLOWABILITY_ID",
    "HAR_DAY",
    "HAR_MONTH",
    "HAR_WEEK",
    "PRIMARY_HORIZON_BARS",
    "RIDGE_WINDOWS",
    "TWIN_HORIZON_BARS",
    "FittedLinearFollower",
    "build_ewma_feature",
    "build_har_features",
    "build_har_inefficiency_features",
    "build_har_rv_features",
    "fit_ewma_follower",
    "fit_har_follower",
    "forecast_linear_follower",
    "forecast_linear_follower_frame",
    "quantile_coverage",
    "score_followability",
    "trailing_attribute",
    "trailing_log_path_inefficiency",
    "trailing_log_realized_variance",
    "trailing_ols_r2",
    "build_future_ols_r2_target",
    "build_har_r2_features",
]
