# pyright: reportAny=false, reportArgumentType=false
# pyright: reportAssignmentType=false, reportAttributeAccessIssue=false
# pyright: reportCallIssue=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownLambdaType=false
# pyright: reportOperatorIssue=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Causal factor materialization for formula-derived tool mechanisms.

The permanent R2F registry contains 21 existing market-state attributes and
13 proposed formula-derived diagnostics.  This module materializes the latter
without reading any post-2020 observation and joins them to the existing
attribute ledger.  The formulas are deliberately low freedom: they use fixed
20/60/120 trading-day scales and do not select windows from performance.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.time_scale_catalog import (
    TimeScaleCatalog,
    build_time_scale_catalog_v2,
)

PROPOSED_FACTOR_IDS: Final[tuple[str, ...]] = (
    "extrema_age_imbalance",
    "group_delay_to_run_age",
    "innovation_whiteness",
    "ma_spread_to_noise",
    "model_weight_entropy",
    "prior_breakout_followthrough",
    "regression_residual_autocorrelation",
    "rolling_regression_r2",
    "signal_margin_to_noise",
    "spectral_edge_leakage",
    "standardized_breakout_margin",
    "transfer_weighted_energy_share",
    "width_response_gap",
)

MECHANISM_PRIMARY_SCALE: Final[Mapping[str, str]] = {
    "spectral_scale_match": "medium_60d",
    "delay_duration_tradeoff": "medium_60d",
    "path_noise_false_switch": "fast_20d",
    "volatility_width_adaptation": "fast_20d",
    "breakout_follow_through": "fast_20d",
    "tail_jump_asymmetry": "fast_20d",
    "linear_channel_fit_quality": "medium_60d",
    "extrema_memory": "medium_60d",
    "state_space_innovation_fit": "fast_20d",
    "moving_average_separation": "medium_60d",
    "switch_cost_burden": "fast_20d",
}

_BARS_PER_TRADING_DAY: Final[Mapping[str, int]] = {
    "1d": 1,
    "60m": 4,
    "15m": 16,
}
_RESEARCH_END_EXCLUSIVE = pd.Timestamp("2021-01-01")
_EPSILON = 1e-12


def _legacy_bar_windows(
    *,
    frequency: str,
    time_scale_catalog: TimeScaleCatalog | None,
) -> tuple[int, int, int]:
    """Project frozen V2 physical-session scales into the unchanged V1 adapter.

    This module's historical formulas still consume bar counts.  The catalog
    is the single source of the 20/60/120 session identities, while the
    conversion intentionally preserves the old V1 arithmetic and outputs.
    New V2 physical-session computations should use ``horizons`` directly.
    """

    bars_per_day = _BARS_PER_TRADING_DAY[frequency]
    catalog = time_scale_catalog or build_time_scale_catalog_v2()
    return (
        catalog.factor_lookback_sessions("fast_20d") * bars_per_day,
        catalog.factor_lookback_sessions("medium_60d") * bars_per_day,
        catalog.factor_lookback_sessions("slow_120d") * bars_per_day,
    )


def mechanism_primary_factor_scale_id(
    mechanism_id: str,
    *,
    time_scale_catalog: TimeScaleCatalog | None = None,
) -> str:
    """Return the V2 factor-scale identity for a legacy mechanism projection."""

    try:
        legacy_scale_id = MECHANISM_PRIMARY_SCALE[mechanism_id]
    except KeyError as exc:
        raise ValidationError(f"unregistered tool mechanism: {mechanism_id}") from exc
    catalog = time_scale_catalog or build_time_scale_catalog_v2()
    return catalog.factor_scale_id_for_legacy(legacy_scale_id)


def _naive_datetime(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, errors="coerce")
    try:
        return parsed.dt.tz_convert("Asia/Shanghai").dt.tz_localize(None)
    except (TypeError, AttributeError):
        try:
            return parsed.dt.tz_localize(None)
        except (TypeError, AttributeError):
            return parsed


def _validated_bars(bars: pd.DataFrame, *, frequency: str) -> pd.DataFrame:
    required = {"timestamp", "high", "low", "close"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValidationError(f"mechanism factors missing price columns: {missing}")
    if frequency not in _BARS_PER_TRADING_DAY:
        raise ValidationError(f"unsupported mechanism-factor frequency: {frequency}")
    frame = bars.loc[:, sorted(required)].copy()
    frame["timestamp"] = _naive_datetime(frame["timestamp"])
    for column in ("high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = (
        frame.dropna()
        .sort_values("timestamp")
        .drop_duplicates("timestamp")
        .loc[lambda item: item["timestamp"].lt(_RESEARCH_END_EXCLUSIVE)]
        .reset_index(drop=True)
    )
    if frame.empty or not bool(frame["close"].gt(0.0).all()):
        raise ValidationError("mechanism-factor price frame is empty or invalid")
    return frame


def _rolling_regression_diagnostics(
    values: np.ndarray,
    *,
    window: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Return causal rolling OLS R² and lag-one residual correlation."""

    count = len(values)
    r2 = np.full(count, np.nan, dtype=float)
    residual_acf = np.full(count, np.nan, dtype=float)
    if window < 8 or count < window:
        return r2, residual_acf
    x = np.arange(window, dtype=float)
    x_centered = x - float(x.mean())
    denominator = float(np.dot(x_centered, x_centered))
    for position in range(window - 1, count):
        sample = values[position - window + 1 : position + 1]
        if not bool(np.isfinite(sample).all()):
            continue
        sample_mean = float(sample.mean())
        centered = sample - sample_mean
        total = float(np.dot(centered, centered))
        beta = float(np.dot(x_centered, centered) / denominator)
        fitted = sample_mean + beta * x_centered
        residual = sample - fitted
        explained = float(np.dot(fitted - sample_mean, fitted - sample_mean))
        r2[position] = min(1.0, max(0.0, explained / total)) if total > _EPSILON else 0.0
        left = residual[:-1]
        right = residual[1:]
        left_centered = left - float(left.mean())
        right_centered = right - float(right.mean())
        scale = math.sqrt(
            float(np.dot(left_centered, left_centered))
            * float(np.dot(right_centered, right_centered))
        )
        residual_acf[position] = (
            float(np.dot(left_centered, right_centered)) / scale
            if scale > _EPSILON
            else 0.0
        )
    return r2, residual_acf


def _rolling_extrema_age_imbalance(
    high: pd.Series,
    low: pd.Series,
    *,
    window: int,
) -> pd.Series:
    high_position = high.rolling(window, min_periods=window).apply(
        lambda sample: float(np.argmax(sample)),
        raw=True,
    )
    low_position = low.rolling(window, min_periods=window).apply(
        lambda sample: float(np.argmin(sample)),
        raw=True,
    )
    high_age = float(window - 1) - high_position
    low_age = float(window - 1) - low_position
    return (high_age - low_age) / max(1.0, float(window - 1))


def _prior_breakout_followthrough(
    close: pd.Series,
    *,
    window: int,
    horizon: int,
) -> pd.Series:
    upper = close.rolling(window, min_periods=window).max().shift(1)
    lower = close.rolling(window, min_periods=window).min().shift(1)
    direction = pd.Series(
        np.where(close.gt(upper), 1.0, np.where(close.lt(lower), -1.0, np.nan)),
        index=close.index,
        dtype=float,
    )
    settled_direction = direction.shift(horizon)
    settled_return = np.log(close / close.shift(horizon))
    settled_success = (
        settled_direction * settled_return
    ).gt(0.0).where(settled_direction.notna())
    return (
        settled_success.astype(float)
        .rolling(window, min_periods=max(8, window // 4))
        .mean()
    )


def _spectral_energy_proxy(
    log_close: pd.Series,
    *,
    period: int,
    energy_window: int,
) -> pd.Series:
    center = log_close.rolling(period, min_periods=period).mean()
    component = log_close - center
    increment = component.diff()
    return increment.pow(2).rolling(
        energy_window,
        min_periods=max(8, energy_window // 3),
    ).mean()


def build_proposed_factor_matrix(
    bars: pd.DataFrame,
    *,
    frequency: str,
    time_scale_catalog: TimeScaleCatalog | None = None,
) -> pd.DataFrame:
    """Build all 13 proposed diagnostics from observations available at t."""

    frame = _validated_bars(bars, frequency=frequency)
    bars_per_day = _BARS_PER_TRADING_DAY[frequency]
    fast, medium, slow = _legacy_bar_windows(
        frequency=frequency,
        time_scale_catalog=time_scale_catalog,
    )
    breakout_horizon = max(2, 5 * bars_per_day)

    close = frame["close"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    log_close = np.log(close)
    log_return = log_close.diff()
    fast_volatility = log_return.rolling(
        fast,
        min_periods=max(8, fast // 3),
    ).std(ddof=0)
    slow_volatility = log_return.rolling(
        medium,
        min_periods=max(8, medium // 3),
    ).std(ddof=0)

    fast_center = log_close.rolling(fast, min_periods=fast).mean()
    medium_center = log_close.rolling(medium, min_periods=medium).mean()
    signal_increment = medium_center.diff()
    signal_noise = log_return.rolling(
        fast,
        min_periods=max(8, fast // 3),
    ).std(ddof=0)
    signal_margin_to_noise = signal_increment.abs() / (
        signal_noise + _EPSILON
    )

    prior_upper = close.rolling(fast, min_periods=fast).max().shift(1)
    prior_lower = close.rolling(fast, min_periods=fast).min().shift(1)
    return_scale = log_return.rolling(
        fast,
        min_periods=max(8, fast // 3),
    ).std(ddof=0)
    upper_margin = np.log(close / prior_upper)
    lower_margin = np.log(close / prior_lower)
    standardized_breakout_margin = pd.Series(
        np.where(
            close.gt(prior_upper),
            upper_margin / (return_scale + _EPSILON),
            np.where(
                close.lt(prior_lower),
                lower_margin / (return_scale + _EPSILON),
                0.0,
            ),
        ),
        index=close.index,
        dtype=float,
    )
    # Before the rolling extrema and return scale are available, neither
    # branch comparison is meaningful.  ``np.where`` would otherwise turn
    # both False comparisons into a fabricated neutral zero.
    breakout_ready = (
        prior_upper.notna() & prior_lower.notna() & return_scale.notna()
    )
    standardized_breakout_margin = standardized_breakout_margin.where(
        breakout_ready
    )

    regression_r2, residual_acf = _rolling_regression_diagnostics(
        log_close.to_numpy(dtype=float),
        window=medium,
    )
    residual_acf_series = pd.Series(residual_acf, index=close.index)
    innovation_whiteness = (1.0 - residual_acf_series.abs()).clip(0.0, 1.0)

    energy_fast = _spectral_energy_proxy(
        log_close,
        period=fast,
        energy_window=medium,
    )
    energy_medium = _spectral_energy_proxy(
        log_close,
        period=medium,
        energy_window=medium,
    )
    energy_slow = _spectral_energy_proxy(
        log_close,
        period=slow,
        energy_window=medium,
    )
    energy_total = energy_fast + energy_medium + energy_slow + _EPSILON
    transfer_share = energy_medium / energy_total
    edge_leakage = (energy_fast + energy_slow) / (
        energy_medium + _EPSILON
    )
    weights = pd.concat(
        [
            energy_fast / energy_total,
            energy_medium / energy_total,
            energy_slow / energy_total,
        ],
        axis=1,
    ).clip(lower=_EPSILON)
    # Require all three energy bands.  DataFrame.sum() defaults to skipna and
    # would otherwise manufacture ``-0.0`` during warmup.
    entropy = -(weights * np.log(weights)).sum(axis=1, min_count=3) / math.log(3.0)

    spread = (fast_center - medium_center).abs()
    spread_noise = log_return.rolling(
        medium,
        min_periods=max(8, medium // 3),
    ).std(ddof=0) * math.sqrt(float(medium))

    result = pd.DataFrame(
        {
            "decision_time": frame["timestamp"],
            "extrema_age_imbalance": _rolling_extrema_age_imbalance(
                high,
                low,
                window=medium,
            ),
            # Pair-specific theoretical group delay is inserted by the
            # validation engine; this placeholder is intentionally NaN.
            "group_delay_to_run_age": np.nan,
            "innovation_whiteness": innovation_whiteness,
            "ma_spread_to_noise": spread / (spread_noise + _EPSILON),
            "model_weight_entropy": entropy.clip(0.0, 1.0),
            "prior_breakout_followthrough": _prior_breakout_followthrough(
                close,
                window=fast,
                horizon=breakout_horizon,
            ),
            "regression_residual_autocorrelation": residual_acf_series,
            "rolling_regression_r2": regression_r2,
            "signal_margin_to_noise": signal_margin_to_noise,
            "spectral_edge_leakage": edge_leakage,
            "standardized_breakout_margin": standardized_breakout_margin,
            "transfer_weighted_energy_share": transfer_share,
            "width_response_gap": (
                (fast_volatility - slow_volatility).abs()
                / (slow_volatility + _EPSILON)
            ),
        }
    )
    if tuple(sorted(set(PROPOSED_FACTOR_IDS) - set(result.columns))):
        raise ValidationError("proposed mechanism factor coverage is incomplete")
    if result["decision_time"].max() >= _RESEARCH_END_EXCLUSIVE:
        raise ValidationError("proposed mechanism factors opened the blackbox")
    return result


def build_existing_factor_matrices(
    states: pd.DataFrame,
    *,
    frequency: str,
    required_factor_ids: set[str],
    time_scale_catalog: TimeScaleCatalog | None = None,
) -> dict[str, pd.DataFrame]:
    """Pivot existing raw attributes into one causal matrix per fixed scale."""

    required = {
        "bar_frequency",
        "observation_time",
        "physical_attribute_id",
        "measurement_scale_id",
        "raw_value",
        "state_valid",
    }
    missing = sorted(required - set(states.columns))
    if missing:
        raise ValidationError(f"existing mechanism states missing columns: {missing}")
    frame = states.loc[
        states["bar_frequency"].eq(frequency)
        & states["physical_attribute_id"].isin(required_factor_ids)
    ].copy()
    frame["decision_time"] = _naive_datetime(frame["observation_time"])
    frame = frame.loc[
        frame["decision_time"].lt(_RESEARCH_END_EXCLUSIVE)
        & frame["state_valid"].eq(True)
    ]
    frame["raw_value"] = pd.to_numeric(frame["raw_value"], errors="coerce")
    matrices: dict[str, pd.DataFrame] = {}
    catalog = time_scale_catalog or build_time_scale_catalog_v2()
    primary_legacy_scale_ids = tuple(sorted(set(MECHANISM_PRIMARY_SCALE.values())))
    for scale in primary_legacy_scale_ids:
        _ = catalog.factor_scale_id_for_legacy(scale)
        selected = frame.loc[frame["measurement_scale_id"].eq(scale)]
        matrix = (
            selected.pivot_table(
                index="decision_time",
                columns="physical_attribute_id",
                values="raw_value",
                aggfunc="last",
            )
            .reset_index()
            .rename_axis(columns=None)
        )
        absent = sorted(required_factor_ids - set(matrix.columns))
        if absent:
            raise ValidationError(
                f"existing {frequency}/{scale} factor matrix missing: {absent}"
            )
        matrices[scale] = matrix
    return matrices


def merge_factor_matrices(
    *,
    existing_by_scale: Mapping[str, pd.DataFrame],
    proposed: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Join the proposed formula diagnostics to every existing scale matrix."""

    result: dict[str, pd.DataFrame] = {}
    for scale, existing in existing_by_scale.items():
        merged = existing.merge(
            proposed,
            on="decision_time",
            how="inner",
            validate="one_to_one",
        )
        if merged.empty:
            raise ValidationError(f"mechanism factor matrix is empty: {scale}")
        result[scale] = merged.sort_values("decision_time").reset_index(drop=True)
    return result


__all__ = [
    "MECHANISM_PRIMARY_SCALE",
    "PROPOSED_FACTOR_IDS",
    "build_existing_factor_matrices",
    "build_proposed_factor_matrix",
    "mechanism_primary_factor_scale_id",
    "merge_factor_matrices",
]
