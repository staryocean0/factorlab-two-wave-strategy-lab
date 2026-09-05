# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Adaptive-lookback path efficiency after a causal short-vs-long vol expansion.

This module does not inherit the previous next-window organization/two-head
coefficients, emit routing states, or grant production authority.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_layer2_next_path_efficiency import (
    ER_FLOOR,
    LOOKBACK_MEAN_BARS,
    PRIMARY_HORIZON_BARS,
    build_future_efficiency_ratio,
    build_lookback_mean_er_feature,
    build_trailing_native_er_feature,
    fit_lookback_mean_er,
    fit_trailing_native_er,
    forecast_clipped_er_frame,
    trailing_efficiency_ratio,
)

ADAPTIVE_ID = "timing_layer2_adaptive_horizon_path_efficiency@1.0"
HORIZONS = (5, 8, 16, 32, 64)
SHORT_BARS = 5
LONG_BARS = 64
ONSET_QUIET_BARS = 5
MIN_LOOKBACK = 5
MAX_LOOKBACK = 64
REF_LOOKBACK = PRIMARY_HORIZON_BARS
ADAPTIVE_METHODS = (
    "expanding_after_expansion",
    "shrinking_after_expansion",
    "vol_matched_always",
)
SIMPLE_METHODS = ("trailing_native_er", "lookback_mean_er_w60")


@dataclass(frozen=True, slots=True)
class FittedAdaptiveLookback:
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
        if self.method_id not in ADAPTIVE_METHODS:
            raise ValidationError("unsupported adaptive-lookback method")
        if self.runtime_feature_future_reads != 0:
            raise ValidationError("adaptive-lookback runtime features cannot read the future")
        if any((self.direction_forecast, self.strategy_authority, self.routing_authority, self.production_authority)):
            raise ValidationError("adaptive-lookback cards cannot grant strategy authority")
        if len(self.feature_names) != len(self.coefficients):
            raise ValidationError("adaptive-lookback coefficient width mismatch")
        if self.training_rows < len(self.feature_names) + 2 or self.calibration_rows < 30:
            raise ValidationError("adaptive-lookback train/calibration support is insufficient")
        if tuple(sorted(self.residual_quantiles)) != self.residual_quantiles:
            raise ValidationError("adaptive-lookback residual quantiles are unordered")


def _positive_log_close(close: pd.Series) -> pd.Series:
    values = pd.to_numeric(close, errors="raise").astype(float)
    if values.le(0.0).any():
        raise ValidationError("adaptive-lookback requires positive prices")
    if not isinstance(values.index, pd.DatetimeIndex) or values.index.tz is None:
        raise ValidationError("adaptive-lookback close requires a timezone-aware DatetimeIndex")
    return np.log(values).rename("log_close")


def realized_variance_intensity(close: pd.Series, *, horizon_bars: int) -> pd.Series:
    if horizon_bars < 2:
        raise ValidationError("RV intensity horizon must be at least 2 bars")
    squared = _positive_log_close(close).diff().pow(2)
    mean_sq = squared.rolling(horizon_bars, min_periods=horizon_bars).mean().clip(lower=1e-12)
    return np.log(mean_sq).rename(f"rv_intensity_{horizon_bars}")


def expansion_intensity(close: pd.Series) -> pd.Series:
    short = realized_variance_intensity(close, horizon_bars=SHORT_BARS)
    long = realized_variance_intensity(close, horizon_bars=LONG_BARS)
    return (short - long).rename("expansion_intensity")


def _zero_cross_onset(intensity: pd.Series, *, direction: str, quiet_bars: int = ONSET_QUIET_BARS) -> pd.Series:
    values = pd.to_numeric(intensity, errors="coerce").astype(float)
    if direction == "expansion":
        current = values > 0.0
        quiet = values <= 0.0
    elif direction == "contraction":
        current = values < 0.0
        quiet = values >= 0.0
    else:
        raise ValidationError("onset direction must be expansion or contraction")
    quiet_run = quiet.rolling(quiet_bars, min_periods=quiet_bars).sum().eq(float(quiet_bars)).shift(1)
    onset = current.eq(True) & quiet_run.eq(True)
    return onset.rename(f"{direction}_onset")


def regime_age(onset: pd.Series) -> pd.Series:
    flags = onset.fillna(False).to_numpy(bool)
    ages = np.zeros(len(flags), dtype=int)
    age = -1
    started = False
    for i, flag in enumerate(flags):
        if flag:
            started = True
            age = 0
        elif started:
            age += 1
        ages[i] = age if started else -1
    return pd.Series(ages, index=onset.index, name="regime_age")


def expansion_regime(close: pd.Series) -> pd.DataFrame:
    intensity = expansion_intensity(close)
    expansion_onset = _zero_cross_onset(intensity, direction="expansion")
    contraction_onset = _zero_cross_onset(intensity, direction="contraction")
    state = np.full(len(intensity), "", dtype=object)
    current = ""
    for i, (exp_on, con_on) in enumerate(zip(expansion_onset.fillna(False), contraction_onset.fillna(False), strict=True)):
        if bool(exp_on):
            current = "expansion"
        elif bool(con_on):
            current = "contraction"
        state[i] = current
    expansion_age = regime_age(expansion_onset)
    expansion_age = expansion_age.where(pd.Series(state, index=close.index).eq("expansion"), other=-1)
    contraction_age = regime_age(contraction_onset)
    contraction_age = contraction_age.where(pd.Series(state, index=close.index).eq("contraction"), other=-1)
    return pd.DataFrame(
        {
            "expansion_intensity": intensity,
            "expansion_onset": expansion_onset.fillna(False),
            "contraction_onset": contraction_onset.fillna(False),
            "regime": pd.Series(state, index=close.index),
            "expansion_age": expansion_age.astype(int),
            "contraction_age": contraction_age.astype(int),
        },
        index=close.index,
    )


def trailing_efficiency_term_structure(
    close: pd.Series,
    *,
    horizons: tuple[int, ...] | range = range(MIN_LOOKBACK, MAX_LOOKBACK + 1),
) -> pd.DataFrame:
    log_close = _positive_log_close(close)
    travel_cum = log_close.diff().abs().cumsum()
    columns: dict[int, pd.Series] = {}
    for horizon in horizons:
        if int(horizon) < 2:
            raise ValidationError("term-structure horizon must be at least 2 bars")
        displacement = (log_close - log_close.shift(int(horizon))).abs()
        travel = (travel_cum - travel_cum.shift(int(horizon))).clip(lower=ER_FLOOR)
        ratio = (displacement / travel).clip(lower=ER_FLOOR, upper=1.0)
        columns[int(horizon)] = ratio
    frame = pd.DataFrame(columns, index=close.index)
    return frame.replace([np.inf, -np.inf], np.nan)


def rv_intensity_term_structure(close: pd.Series, *, horizons: tuple[int, ...] = HORIZONS) -> pd.DataFrame:
    output = pd.DataFrame(index=close.index)
    for horizon in horizons:
        output[horizon] = realized_variance_intensity(close, horizon_bars=horizon)
    return output


def organization_term_structure(efficiency: pd.DataFrame) -> pd.DataFrame:
    scaled = efficiency.copy()
    for column in scaled.columns:
        scaled[column] = pd.to_numeric(scaled[column], errors="coerce") * np.sqrt(float(column))
    return scaled


def _clip_horizon(values: pd.Series) -> pd.Series:
    rounded = pd.to_numeric(values, errors="coerce").round()
    return rounded.clip(lower=MIN_LOOKBACK, upper=MAX_LOOKBACK)


def adaptive_lookback_horizon(close: pd.Series, *, method_id: str) -> pd.Series:
    regime = expansion_regime(close)
    if method_id == "expanding_after_expansion":
        expanding = MIN_LOOKBACK + regime["expansion_age"]
        horizon = expanding.where(regime["regime"].eq("expansion"), other=REF_LOOKBACK)
    elif method_id == "shrinking_after_expansion":
        shrinking = MAX_LOOKBACK - regime["expansion_age"]
        horizon = shrinking.where(regime["regime"].eq("expansion"), other=REF_LOOKBACK)
    elif method_id == "vol_matched_always":
        scale = np.exp(-pd.to_numeric(regime["expansion_intensity"], errors="coerce"))
        horizon = REF_LOOKBACK * scale
    else:
        raise ValidationError("unsupported adaptive-lookback method")
    horizon = _clip_horizon(horizon)
    horizon = horizon.where(regime["expansion_intensity"].notna())
    return horizon.rename(method_id)


def adaptive_trailing_efficiency(close: pd.Series, *, method_id: str) -> pd.Series:
    horizons = adaptive_lookback_horizon(close, method_id=method_id)
    structure = trailing_efficiency_term_structure(close)
    picked = pd.Series(np.nan, index=close.index, dtype=float)
    valid = horizons.dropna()
    if valid.empty:
        return picked.rename(method_id)
    integer = valid.astype(int)
    for horizon, locations in integer.groupby(integer):
        picked.loc[locations.index] = structure.loc[locations.index, horizon]
    return picked.rename(method_id)


def build_adaptive_feature(close: pd.Series, *, method_id: str) -> pd.DataFrame:
    return pd.DataFrame({method_id: adaptive_trailing_efficiency(close, method_id=method_id)}, index=close.index)


def _fit_linear(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    method_id: str,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
) -> FittedAdaptiveLookback:
    if not isinstance(features.index, pd.DatetimeIndex) or features.index.tz is None:
        raise ValidationError("adaptive-lookback features require a timezone-aware DatetimeIndex")
    if train_end.tzinfo is None or calibration_end.tzinfo is None or calibration_end <= train_end:
        raise ValidationError("adaptive-lookback train/calibration boundaries are invalid")
    joined = features.copy()
    joined["__target"] = pd.to_numeric(target, errors="coerce")
    joined = joined.replace([np.inf, -np.inf], np.nan).dropna()
    train = joined.loc[joined.index <= train_end]
    calibration = joined.loc[(joined.index > train_end) & (joined.index <= calibration_end)]
    names = tuple(str(column) for column in features.columns)
    if len(train) < len(names) + 2 or len(calibration) < 30:
        raise ValidationError("adaptive-lookback split support is insufficient")
    x = train[list(names)].to_numpy(float)
    y = train["__target"].to_numpy(float)
    design = np.column_stack([np.ones(len(x)), x])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    intercept = float(coefficients[0])
    betas = tuple(float(value) for value in coefficients[1:])
    prediction = intercept + calibration[list(names)].to_numpy(float) @ np.asarray(betas)
    residual = calibration["__target"].to_numpy(float) - prediction
    quantiles = tuple(float(value) for value in np.quantile(residual, [0.1, 0.5, 0.9]))
    return FittedAdaptiveLookback(
        method_id=method_id,
        target_id="future_efficiency_ratio",
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


def fit_adaptive_lookback(
    close: pd.Series,
    target: pd.Series,
    *,
    method_id: str,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
) -> FittedAdaptiveLookback:
    return _fit_linear(
        build_adaptive_feature(close, method_id=method_id),
        target,
        method_id=method_id,
        train_end=train_end,
        calibration_end=calibration_end,
    )


def common_scale_correlation(intensity: pd.DataFrame) -> dict[str, float]:
    clean = intensity.replace([np.inf, -np.inf], np.nan).dropna()
    if len(clean) < 8 or clean.shape[1] < 2:
        raise ValidationError("common-scale correlation support is insufficient")
    corr = clean.corr(method="spearman")
    pairs: list[float] = []
    columns = list(corr.columns)
    for i, left in enumerate(columns):
        for right in columns[i + 1 :]:
            pairs.append(float(corr.loc[left, right]))
    short_long = float(corr.loc[SHORT_BARS, LONG_BARS]) if SHORT_BARS in corr.index and LONG_BARS in corr.columns else float("nan")
    return {
        "n": float(len(clean)),
        "mean_pairwise_spearman": float(np.mean(pairs)),
        "min_pairwise_spearman": float(np.min(pairs)),
        "short_long_spearman": short_long,
    }


def mean_term_structure(frame: pd.DataFrame) -> dict[str, float]:
    clean = frame.replace([np.inf, -np.inf], np.nan).dropna()
    if len(clean) < 5:
        raise ValidationError("term-structure support is insufficient")
    return {str(column): float(clean[column].mean()) for column in clean.columns}


__all__ = [
    "ADAPTIVE_ID",
    "ADAPTIVE_METHODS",
    "HORIZONS",
    "LOOKBACK_MEAN_BARS",
    "PRIMARY_HORIZON_BARS",
    "SIMPLE_METHODS",
    "FittedAdaptiveLookback",
    "adaptive_lookback_horizon",
    "adaptive_trailing_efficiency",
    "build_adaptive_feature",
    "build_future_efficiency_ratio",
    "build_lookback_mean_er_feature",
    "build_trailing_native_er_feature",
    "common_scale_correlation",
    "expansion_intensity",
    "expansion_regime",
    "fit_adaptive_lookback",
    "fit_lookback_mean_er",
    "fit_trailing_native_er",
    "forecast_clipped_er_frame",
    "mean_term_structure",
    "organization_term_structure",
    "realized_variance_intensity",
    "rv_intensity_term_structure",
    "trailing_efficiency_ratio",
    "trailing_efficiency_term_structure",
]
