# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Causal next-window path-efficiency forecast.

This module forecasts the next H-bar Kaufman efficiency from currently
observable path-organization features. It does not persist a lookback-mean
efficiency climate, emit routing states, or grant production authority.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_layer2_attribute_followability import (
    forecast_linear_follower_frame,
    quantile_coverage,
    score_followability,
    trailing_log_realized_variance,
    trailing_ols_r2,
)

FORECAST_ID = "timing_layer2_next_path_efficiency_forecast@1.0"
PRIMARY_HORIZON_BARS = 16
TWIN_HORIZON_BARS = 5
LOOKBACK_MEAN_BARS = 60
ORGANIZATION_WINDOW_BARS = 60
JUMP_WINDOW_BARS = 20
SIMPLE_METHODS = ("trailing_native_er", "lookback_mean_er_w60")
HARD_METHODS = ("organization_ols", "two_head_ratio")
ORGANIZATION_FEATURE_NAMES = (
    "ret_ac_lag1_w60",
    "ret_ac_lag5_w60",
    "abs_ac_lag1_w60",
    "variance_ratio_qH_w60",
    "direction_consistency_w60",
    "ols_r2_w60",
    "jump_share_w20",
)
DISPLACEMENT_FEATURE_NAMES = (
    "ret_ac_lag1_w60",
    "variance_ratio_qH_w60",
    "direction_consistency_w60",
    "ols_r2_w60",
)
LENGTH_FEATURE_NAMES = ("log_rv_d", "log_rv_w", "log_rv_m")
ER_FLOOR = 1e-6


@dataclass(frozen=True, slots=True)
class FittedNextPathEfficiency:
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
        allowed = SIMPLE_METHODS + HARD_METHODS + ("length_head", "displacement_head")
        if self.method_id not in allowed:
            raise ValidationError("unsupported next-path-efficiency method")
        if self.horizon_bars < 2:
            raise ValidationError("next-path-efficiency horizon must be at least 2 bars")
        if self.runtime_feature_future_reads != 0:
            raise ValidationError("next-path-efficiency runtime features cannot read the future")
        if any((self.direction_forecast, self.strategy_authority, self.routing_authority, self.production_authority)):
            raise ValidationError("next-path-efficiency cards cannot grant strategy authority")
        if len(self.feature_names) != len(self.coefficients):
            raise ValidationError("next-path-efficiency coefficient width mismatch")
        if self.training_rows < len(self.feature_names) + 2 or self.calibration_rows < 30:
            raise ValidationError("next-path-efficiency train/calibration support is insufficient")
        if tuple(sorted(self.residual_quantiles)) != self.residual_quantiles:
            raise ValidationError("next-path-efficiency residual quantiles are unordered")


def _positive_log_close(close: pd.Series) -> pd.Series:
    values = pd.to_numeric(close, errors="raise").astype(float)
    if values.le(0.0).any():
        raise ValidationError("next-path-efficiency requires positive prices")
    if not isinstance(values.index, pd.DatetimeIndex) or values.index.tz is None:
        raise ValidationError("next-path-efficiency close requires a timezone-aware DatetimeIndex")
    return np.log(values).rename("log_close")


def _clip_er(series: pd.Series) -> pd.Series:
    clipped = pd.to_numeric(series, errors="coerce").astype(float).clip(lower=ER_FLOOR, upper=1.0)
    return clipped.replace([np.inf, -np.inf], np.nan)


def trailing_efficiency_ratio(close: pd.Series, *, horizon_bars: int) -> pd.Series:
    if horizon_bars < 2:
        raise ValidationError("efficiency-ratio horizon must be at least 2 bars")
    log_close = _positive_log_close(close)
    abs_step = log_close.diff().abs()
    travel = abs_step.rolling(horizon_bars, min_periods=horizon_bars).sum()
    displacement = (log_close - log_close.shift(horizon_bars)).abs()
    return _clip_er(displacement / travel).rename(f"trailing_efficiency_ratio_{horizon_bars}")


def build_future_efficiency_ratio(close: pd.Series, *, horizon_bars: int) -> pd.Series:
    trailing = trailing_efficiency_ratio(close, horizon_bars=horizon_bars)
    future = trailing.shift(-horizon_bars)
    future.iloc[-horizon_bars:] = np.nan
    return future.rename(f"future_efficiency_ratio_{horizon_bars}")


def trailing_log_abs_displacement(close: pd.Series, *, horizon_bars: int) -> pd.Series:
    log_close = _positive_log_close(close)
    displacement = (log_close - log_close.shift(horizon_bars)).abs().clip(lower=ER_FLOOR)
    return np.log(displacement).rename(f"trailing_log_abs_displacement_{horizon_bars}")


def trailing_log_path_length(close: pd.Series, *, horizon_bars: int) -> pd.Series:
    log_close = _positive_log_close(close)
    travel = log_close.diff().abs().rolling(horizon_bars, min_periods=horizon_bars).sum().clip(lower=ER_FLOOR)
    return np.log(travel).rename(f"trailing_log_path_length_{horizon_bars}")


def build_future_log_abs_displacement(close: pd.Series, *, horizon_bars: int) -> pd.Series:
    future = trailing_log_abs_displacement(close, horizon_bars=horizon_bars).shift(-horizon_bars)
    future.iloc[-horizon_bars:] = np.nan
    return future.rename(f"future_log_abs_displacement_{horizon_bars}")


def build_future_log_path_length(close: pd.Series, *, horizon_bars: int) -> pd.Series:
    future = trailing_log_path_length(close, horizon_bars=horizon_bars).shift(-horizon_bars)
    future.iloc[-horizon_bars:] = np.nan
    return future.rename(f"future_log_path_length_{horizon_bars}")


def build_future_organization_residual(close: pd.Series, *, horizon_bars: int) -> pd.Series:
    future = build_future_efficiency_ratio(close, horizon_bars=horizon_bars) * np.sqrt(float(horizon_bars))
    return future.rename(f"future_organization_residual_{horizon_bars}")


def _rolling_autocorr(series: pd.Series, *, window: int, lag: int) -> pd.Series:
    if lag < 1 or window <= lag + 2:
        raise ValidationError("autocorr window/lag is invalid")
    lagged = series.shift(lag)
    return series.rolling(window, min_periods=window).corr(lagged)


def rolling_variance_ratio(close: pd.Series, *, lookback_bars: int, horizon_bars: int) -> pd.Series:
    if lookback_bars < horizon_bars + 8:
        raise ValidationError("variance-ratio lookback is shorter than the horizon")
    log_close = _positive_log_close(close)
    returns = log_close.diff()
    q_sum = returns.rolling(horizon_bars, min_periods=horizon_bars).sum()
    var_q = q_sum.rolling(lookback_bars, min_periods=lookback_bars).var(ddof=1)
    var_1 = returns.rolling(lookback_bars, min_periods=lookback_bars).var(ddof=1)
    ratio = var_q / (float(horizon_bars) * var_1.replace(0.0, np.nan))
    return ratio.replace([np.inf, -np.inf], np.nan).rename(
        f"variance_ratio_q{horizon_bars}_w{lookback_bars}"
    )


def rolling_direction_consistency(close: pd.Series, *, window: int) -> pd.Series:
    log_close = _positive_log_close(close)
    signs = np.sign(log_close.diff()).replace(0.0, np.nan)
    return signs.rolling(window, min_periods=window).mean().abs().rename(f"direction_consistency_w{window}")


def rolling_jump_share(close: pd.Series, *, window: int) -> pd.Series:
    if window < 3:
        raise ValidationError("jump-share window must be at least 3 bars")
    log_close = _positive_log_close(close)
    returns = log_close.diff()
    realized = returns.pow(2).rolling(window, min_periods=window).sum()
    bipower = (np.pi / 2.0) * (returns.abs() * returns.abs().shift(1)).rolling(window, min_periods=window).sum()
    share = (realized - bipower).clip(lower=0.0) / realized.replace(0.0, np.nan)
    return share.replace([np.inf, -np.inf], np.nan).rename(f"jump_share_w{window}")


def build_trailing_native_er_feature(close: pd.Series, *, horizon_bars: int) -> pd.DataFrame:
    return pd.DataFrame(
        {"trailing_native_er": trailing_efficiency_ratio(close, horizon_bars=horizon_bars)},
        index=close.index,
    )


def build_lookback_mean_er_feature(close: pd.Series, *, horizon_bars: int, lookback_bars: int = LOOKBACK_MEAN_BARS) -> pd.DataFrame:
    native = trailing_efficiency_ratio(close, horizon_bars=horizon_bars)
    averaged = native.rolling(lookback_bars, min_periods=lookback_bars).mean()
    return pd.DataFrame({"lookback_mean_er_w60": averaged}, index=close.index)


def build_organization_features(close: pd.Series, *, horizon_bars: int) -> pd.DataFrame:
    log_close = _positive_log_close(close)
    returns = log_close.diff()
    output = pd.DataFrame(index=close.index)
    output["ret_ac_lag1_w60"] = _rolling_autocorr(returns, window=ORGANIZATION_WINDOW_BARS, lag=1)
    output["ret_ac_lag5_w60"] = _rolling_autocorr(returns, window=ORGANIZATION_WINDOW_BARS, lag=5)
    output["abs_ac_lag1_w60"] = _rolling_autocorr(returns.abs(), window=ORGANIZATION_WINDOW_BARS, lag=1)
    output["variance_ratio_qH_w60"] = rolling_variance_ratio(
        close, lookback_bars=ORGANIZATION_WINDOW_BARS, horizon_bars=horizon_bars
    )
    output["direction_consistency_w60"] = rolling_direction_consistency(close, window=ORGANIZATION_WINDOW_BARS)
    output["ols_r2_w60"] = trailing_ols_r2(close, horizon_bars=ORGANIZATION_WINDOW_BARS)
    output["jump_share_w20"] = rolling_jump_share(close, window=JUMP_WINDOW_BARS)
    if tuple(output.columns) != ORGANIZATION_FEATURE_NAMES:
        raise ValidationError("organization feature identity drifted")
    return output.replace([np.inf, -np.inf], np.nan)


def build_displacement_features(close: pd.Series, *, horizon_bars: int) -> pd.DataFrame:
    features = build_organization_features(close, horizon_bars=horizon_bars)
    return features.loc[:, list(DISPLACEMENT_FEATURE_NAMES)].copy()


def build_length_features(close: pd.Series) -> pd.DataFrame:
    from factor_lab.market_state.timing_layer2_attribute_followability import build_har_rv_features

    features = build_har_rv_features(close)
    return features.loc[:, list(LENGTH_FEATURE_NAMES)].copy()


def _fit_linear(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    method_id: str,
    target_id: str,
    horizon_bars: int,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
) -> FittedNextPathEfficiency:
    if not isinstance(features.index, pd.DatetimeIndex) or features.index.tz is None:
        raise ValidationError("next-path-efficiency features require a timezone-aware DatetimeIndex")
    if train_end.tzinfo is None or calibration_end.tzinfo is None or calibration_end <= train_end:
        raise ValidationError("next-path-efficiency train/calibration boundaries are invalid")
    joined = features.copy()
    joined["__target"] = pd.to_numeric(target, errors="coerce")
    joined = joined.replace([np.inf, -np.inf], np.nan).dropna()
    train = joined.loc[joined.index <= train_end]
    calibration = joined.loc[(joined.index > train_end) & (joined.index <= calibration_end)]
    names = tuple(str(column) for column in features.columns)
    if len(train) < len(names) + 2 or len(calibration) < 30:
        raise ValidationError("next-path-efficiency split support is insufficient")
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
    return FittedNextPathEfficiency(
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


def fit_trailing_native_er(
    close: pd.Series,
    target: pd.Series,
    *,
    horizon_bars: int,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
) -> FittedNextPathEfficiency:
    return _fit_linear(
        build_trailing_native_er_feature(close, horizon_bars=horizon_bars),
        target,
        method_id="trailing_native_er",
        target_id="future_efficiency_ratio",
        horizon_bars=horizon_bars,
        train_end=train_end,
        calibration_end=calibration_end,
    )


def fit_lookback_mean_er(
    close: pd.Series,
    target: pd.Series,
    *,
    horizon_bars: int,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
) -> FittedNextPathEfficiency:
    return _fit_linear(
        build_lookback_mean_er_feature(close, horizon_bars=horizon_bars),
        target,
        method_id="lookback_mean_er_w60",
        target_id="future_efficiency_ratio",
        horizon_bars=horizon_bars,
        train_end=train_end,
        calibration_end=calibration_end,
    )


def fit_organization_ols(
    close: pd.Series,
    target: pd.Series,
    *,
    horizon_bars: int,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
) -> FittedNextPathEfficiency:
    return _fit_linear(
        build_organization_features(close, horizon_bars=horizon_bars),
        target,
        method_id="organization_ols",
        target_id="future_efficiency_ratio",
        horizon_bars=horizon_bars,
        train_end=train_end,
        calibration_end=calibration_end,
    )


def fit_length_head(
    close: pd.Series,
    *,
    horizon_bars: int,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
) -> FittedNextPathEfficiency:
    return _fit_linear(
        build_length_features(close),
        build_future_log_path_length(close, horizon_bars=horizon_bars),
        method_id="length_head",
        target_id="future_log_path_length",
        horizon_bars=horizon_bars,
        train_end=train_end,
        calibration_end=calibration_end,
    )


def fit_displacement_head(
    close: pd.Series,
    *,
    horizon_bars: int,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
) -> FittedNextPathEfficiency:
    return _fit_linear(
        build_displacement_features(close, horizon_bars=horizon_bars),
        build_future_log_abs_displacement(close, horizon_bars=horizon_bars),
        method_id="displacement_head",
        target_id="future_log_abs_displacement",
        horizon_bars=horizon_bars,
        train_end=train_end,
        calibration_end=calibration_end,
    )


def forecast_clipped_er_frame(fitted: FittedNextPathEfficiency, features: pd.DataFrame) -> pd.DataFrame:
    frame = forecast_linear_follower_frame(fitted, features)  # type: ignore[arg-type]
    for column in ("mean", "q10", "q50", "q90"):
        frame[column] = _clip_er(frame[column])
    unordered = frame.loc[~frame["abstained"], ["q10", "q50", "q90"]]
    if not unordered.empty and not bool((unordered["q10"] <= unordered["q50"]).all() and (unordered["q50"] <= unordered["q90"]).all()):
        # Clipping can collapse quantiles onto the ER bounds; keep order by construction.
        frame.loc[~frame["abstained"], "q10"] = np.minimum(frame.loc[~frame["abstained"], "q10"], frame.loc[~frame["abstained"], "q50"])
        frame.loc[~frame["abstained"], "q90"] = np.maximum(frame.loc[~frame["abstained"], "q90"], frame.loc[~frame["abstained"], "q50"])
    return frame


def combine_two_head_er(
    displacement_forecast: pd.DataFrame,
    length_forecast: pd.DataFrame,
) -> pd.DataFrame:
    if not displacement_forecast.index.equals(length_forecast.index):
        raise ValidationError("two-head forecasts must share an index")
    abstained = displacement_forecast["abstained"] | length_forecast["abstained"]
    disp = pd.to_numeric(displacement_forecast["mean"], errors="coerce")
    length = pd.to_numeric(length_forecast["mean"], errors="coerce")
    combined = _clip_er(np.exp(disp - length))
    disp_q10 = pd.to_numeric(displacement_forecast["q10"], errors="coerce")
    disp_q90 = pd.to_numeric(displacement_forecast["q90"], errors="coerce")
    len_q10 = pd.to_numeric(length_forecast["q10"], errors="coerce")
    len_q90 = pd.to_numeric(length_forecast["q90"], errors="coerce")
    # Conservative ER interval: small displacement over large path, then the reverse.
    q10 = _clip_er(np.exp(disp_q10 - len_q90))
    q90 = _clip_er(np.exp(disp_q90 - len_q10))
    q50 = combined
    q10 = np.minimum(q10, q50)
    q90 = np.maximum(q90, q50)
    combined = combined.where(~abstained)
    return pd.DataFrame(
        {
            "mean": combined,
            "q10": q10.where(~abstained),
            "q50": q50.where(~abstained),
            "q90": q90.where(~abstained),
            "abstained": abstained,
        },
        index=displacement_forecast.index,
    )


def train_q70(target: pd.Series, *, train_end: pd.Timestamp) -> float:
    values = pd.to_numeric(target.loc[target.index <= train_end], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(values) < 30:
        raise ValidationError("train q70 support is insufficient")
    return float(values.quantile(0.70))


def top_q70_precision(forecast: pd.Series, realized: pd.Series, *, realized_q70: float, forecast_q70: float) -> dict[str, float]:
    joined = pd.concat({"forecast": forecast, "realized": realized}, axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    predicted_good = joined["forecast"] > forecast_q70
    if int(predicted_good.sum()) < 10:
        raise ValidationError("top-q70 precision support is insufficient")
    return {
        "n_predicted_good": float(predicted_good.sum()),
        "precision": float((joined.loc[predicted_good, "realized"] > realized_q70).mean()),
        "realized_base_rate": float((joined["realized"] > realized_q70).mean()),
        "realized_q70": float(realized_q70),
        "forecast_q70": float(forecast_q70),
    }


def partial_spearman_vs_trailing_log_rv(
    forecast: pd.Series,
    realized: pd.Series,
    close: pd.Series,
    *,
    horizon_bars: int,
    train_end: pd.Timestamp,
    eval_start: pd.Timestamp,
    eval_end: pd.Timestamp,
) -> float:
    rv = trailing_log_realized_variance(close, horizon_bars=horizon_bars)
    joined = pd.concat(
        {"forecast": forecast, "realized": realized, "rv": rv},
        axis=1,
    ).replace([np.inf, -np.inf], np.nan).dropna()
    train = joined.loc[joined.index <= train_end]
    eval_rows = joined.loc[(joined.index >= eval_start) & (joined.index <= eval_end)]
    if len(train) < 30 or len(eval_rows) < 30:
        raise ValidationError("partial Spearman support is insufficient")
    design = np.column_stack([np.ones(len(train)), train["rv"].to_numpy(float)])
    coef, *_ = np.linalg.lstsq(design, train["realized"].to_numpy(float), rcond=None)
    residual = eval_rows["realized"].to_numpy(float) - (coef[0] + coef[1] * eval_rows["rv"].to_numpy(float))
    return float(pd.Series(eval_rows["forecast"].to_numpy(float)).corr(pd.Series(residual), method="spearman"))


def beats_simple_baselines(challenger: dict[str, float], baselines: list[dict[str, float]]) -> bool:
    if not baselines:
        raise ValidationError("simple baselines are required")
    return all(
        float(challenger["mae"]) < float(baseline["mae"]) and float(challenger["rank_ic"]) > float(baseline["rank_ic"])
        for baseline in baselines
    )


__all__ = [
    "DISPLACEMENT_FEATURE_NAMES",
    "FORECAST_ID",
    "HARD_METHODS",
    "LENGTH_FEATURE_NAMES",
    "LOOKBACK_MEAN_BARS",
    "ORGANIZATION_FEATURE_NAMES",
    "PRIMARY_HORIZON_BARS",
    "SIMPLE_METHODS",
    "TWIN_HORIZON_BARS",
    "FittedNextPathEfficiency",
    "beats_simple_baselines",
    "build_displacement_features",
    "build_future_efficiency_ratio",
    "build_future_log_abs_displacement",
    "build_future_log_path_length",
    "build_future_organization_residual",
    "build_length_features",
    "build_lookback_mean_er_feature",
    "build_organization_features",
    "build_trailing_native_er_feature",
    "combine_two_head_er",
    "fit_displacement_head",
    "fit_length_head",
    "fit_lookback_mean_er",
    "fit_organization_ols",
    "fit_trailing_native_er",
    "forecast_clipped_er_frame",
    "partial_spearman_vs_trailing_log_rv",
    "quantile_coverage",
    "rolling_direction_consistency",
    "rolling_jump_share",
    "rolling_variance_ratio",
    "score_followability",
    "top_q70_precision",
    "trailing_efficiency_ratio",
    "trailing_log_abs_displacement",
    "trailing_log_path_length",
    "train_q70",
]
