# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportOperatorIssue=false, reportPrivateUsage=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Causal Layer 2 volume, cross-sectional, and path-lifecycle measurements."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.core_kline_attribute_pool import _signed_ols_t
from factor_lab.market_state.timing_layer2_measurement_plane import (
    Layer2MeasurementCoordinate,
    validate_measurement_output_columns,
)
from factor_lab.market_state.timing_layer2_pit_core import PITCoreBinding

EXTENDED_MEASUREMENT_SCHEMA_ID: Final[str] = "timing_layer2_extended_measurements@1.0"
EXTENDED_HORIZON_DAYS: Final[tuple[int, ...]] = (5, 20, 60)


def build_volume_liquidity_measurements(
    bars: pd.DataFrame,
    *,
    binding: PITCoreBinding,
    horizon_days: tuple[int, ...] = EXTENDED_HORIZON_DAYS,
) -> pd.DataFrame:
    """Measure amount/volume activation, coherence, and K-line liquidity."""

    frame = _validated_extended_bars(bars, require_volume=True)
    _validate_horizons(horizon_days)
    _validate_binding(frame, binding, estimator_id="volume_liquidity")
    timestamp = pd.DatetimeIndex(frame["timestamp"])
    close = frame["close"].astype(float)
    log_return = np.log(close).diff()
    log_amount = np.log(frame["amount"].astype(float).clip(lower=1e-12))
    log_volume = np.log(frame["volume"].astype(float).clip(lower=1e-12))
    amount_change = log_amount.diff()
    output = _identity_panel(timestamp, binding)
    output["log_return"] = log_return
    output["log_amount"] = log_amount
    output["log_volume"] = log_volume
    for days in horizon_days:
        window = days * binding.bars_per_day
        output[f"amount_z_{days}d"] = _prior_zscore(log_amount, window)
        output[f"volume_z_{days}d"] = _prior_zscore(log_volume, window)
        output[f"amount_participation_{days}d"] = _relative_to_prior_median(frame["amount"].astype(float), window)
        output[f"volume_participation_{days}d"] = _relative_to_prior_median(frame["volume"].astype(float), window)
        coherence = log_return.rolling(window, min_periods=window).corr(amount_change)
        output[f"price_amount_coherence_{days}d"] = coherence.replace([np.inf, -np.inf], np.nan)
        amihud = log_return.abs() / frame["amount"].astype(float).replace(0.0, np.nan)
        output[f"amihud_kline_{days}d"] = amihud.rolling(window, min_periods=window).mean()
    return _finish(
        output,
        binding,
        family="volume_liquidity",
        horizons=horizon_days,
    )


def build_path_lifecycle_measurements(
    bars: pd.DataFrame,
    *,
    binding: PITCoreBinding,
    horizon_days: tuple[int, ...] = EXTENDED_HORIZON_DAYS,
) -> pd.DataFrame:
    """Measure drawdown, reclaim, slope decay, curvature, and endpoint age."""

    frame = _validated_extended_bars(bars, require_volume=False)
    _validate_horizons(horizon_days)
    _validate_binding(frame, binding, estimator_id="path_lifecycle")
    timestamp = pd.DatetimeIndex(frame["timestamp"])
    log_close = pd.Series(np.log(frame["close"].to_numpy(float)), index=frame.index, dtype=float)
    output = _identity_panel(timestamp, binding)
    output["log_return"] = log_close.diff()
    output["log_return_acceleration"] = log_close.diff().diff()
    for days in horizon_days:
        window = days * binding.bars_per_day
        rolling_high = log_close.rolling(window, min_periods=window).max()
        rolling_low = log_close.rolling(window, min_periods=window).min()
        prior_high = log_close.rolling(window, min_periods=window).max().shift(1)
        prior_low = log_close.rolling(window, min_periods=window).min().shift(1)
        output[f"drawdown_depth_{days}d"] = log_close - rolling_high
        output[f"runup_height_{days}d"] = log_close - rolling_low
        output[f"prior_high_reclaim_margin_{days}d"] = log_close - prior_high
        output[f"prior_low_break_margin_{days}d"] = log_close - prior_low
        output[f"channel_width_{days}d"] = rolling_high - rolling_low
        output[f"channel_width_change_{days}d"] = output[f"channel_width_{days}d"].diff(binding.bars_per_day)
        output[f"peak_age_bars_{days}d"] = log_close.rolling(window, min_periods=window).apply(_age_since_maximum, raw=True)
        output[f"trough_age_bars_{days}d"] = log_close.rolling(window, min_periods=window).apply(_age_since_minimum, raw=True)
        slope = _align(_signed_ols_t(log_close.to_numpy(float), window), len(frame), window - 1)
        output[f"signed_slope_t_{days}d"] = slope
        output[f"signed_slope_t_decay_{days}d"] = pd.Series(slope).diff(binding.bars_per_day)
    return _finish(
        output,
        binding,
        family="path_lifecycle",
        horizons=horizon_days,
    )


def build_cross_sectional_structure_measurements(
    panel: pd.DataFrame,
    *,
    timestamp_column: str = "timestamp",
    symbol_column: str = "symbol",
    return_column: str = "log_return",
    amount_column: str = "amount",
    group_column: str | None = None,
    availability_delay_seconds: int = 0,
) -> pd.DataFrame:
    """Aggregate contemporaneous breadth, tails, dispersion, and concentration."""

    required = {timestamp_column, symbol_column, return_column, amount_column}
    if group_column:
        required.add(group_column)
    missing = sorted(required.difference(panel.columns))
    if missing:
        raise ValidationError(f"cross-sectional panel missing columns: {missing}")
    if availability_delay_seconds < 0:
        raise ValidationError("cross-sectional availability delay cannot be negative")
    frame = panel.copy()
    timestamp = pd.DatetimeIndex(pd.to_datetime(frame[timestamp_column], errors="raise"))
    if timestamp.tz is None:
        raise ValidationError("cross-sectional timestamps must be timezone-aware")
    frame[timestamp_column] = timestamp
    frame[return_column] = pd.to_numeric(frame[return_column], errors="raise").astype(float)
    frame[amount_column] = pd.to_numeric(frame[amount_column], errors="raise").astype(float)
    if bool((frame[amount_column] < 0.0).any()) or not np.isfinite(frame[[return_column, amount_column]].to_numpy(float)).all():
        raise ValidationError("cross-sectional returns/amount must be finite and amount nonnegative")
    if frame.duplicated([timestamp_column, symbol_column]).any():
        raise ValidationError("cross-sectional symbol/timestamp keys must be unique")
    rows: list[dict[str, object]] = []
    for observation_time, part in frame.groupby(timestamp_column, sort=True):
        returns = part[return_column].to_numpy(float)
        amounts = part[amount_column].to_numpy(float)
        positive = np.maximum(returns, 0.0)
        amount_total = float(amounts.sum())
        amount_weights = amounts / amount_total if amount_total > 0 else np.zeros(len(amounts))
        positive_total = float(positive.sum())
        top_count = max(1, int(math_ceil_tenth(len(returns))))
        top_positive = float(np.sort(positive)[-top_count:].sum())
        row: dict[str, object] = {
            "observation_time": observation_time,
            "available_at": observation_time + pd.Timedelta(seconds=availability_delay_seconds),
            "symbol_count": len(part),
            "positive_breadth": float(np.mean(returns > 0.0)),
            "negative_breadth": float(np.mean(returns < 0.0)),
            "direction_imbalance": float(np.mean(np.sign(returns))),
            "return_q05": float(np.quantile(returns, 0.05)),
            "return_q25": float(np.quantile(returns, 0.25)),
            "return_median": float(np.median(returns)),
            "return_q75": float(np.quantile(returns, 0.75)),
            "return_q95": float(np.quantile(returns, 0.95)),
            "return_iqr": float(np.quantile(returns, 0.75) - np.quantile(returns, 0.25)),
            "left_tail_mean": float(np.mean(np.sort(returns)[:top_count])),
            "right_tail_mean": float(np.mean(np.sort(returns)[-top_count:])),
            "positive_leader_concentration": (top_positive / positive_total if positive_total > 0 else 0.0),
            "amount_hhi": float(np.square(amount_weights).sum()),
            "amount_top10_share": float(np.sort(amount_weights)[-top_count:].sum()),
        }
        if group_column:
            group_share = part[group_column].astype(str).value_counts(normalize=True)
            row["group_top1_purity"] = float(group_share.iloc[0])
            row["group_count"] = int(len(group_share))
        rows.append(row)
    result = pd.DataFrame(rows).sort_values("observation_time").reset_index(drop=True)
    validate_measurement_output_columns(result.columns)
    result.attrs["timing_layer_contract"] = {
        "schema_id": EXTENDED_MEASUREMENT_SCHEMA_ID,
        "family": "cross_sectional_structure",
        "same_timestamp_only": True,
        "threshold_selection": False,
        "static_group_runtime_authority": False,
        "measurement_authority": True,
        "routing_authority": False,
        "production_authority": False,
    }
    return result


def _identity_panel(timestamp: pd.DatetimeIndex, binding: PITCoreBinding) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "carrier_id": binding.carrier_id,
            "view_id": binding.view_id,
            "observation_time": timestamp,
            "available_at": timestamp + pd.to_timedelta(binding.availability_delay_seconds, unit="s"),
            "quality_status": "ready",
        }
    )


def _finish(
    output: pd.DataFrame,
    binding: PITCoreBinding,
    *,
    family: str,
    horizons: tuple[int, ...],
) -> pd.DataFrame:
    validate_measurement_output_columns(output.columns)
    output.attrs["timing_layer_contract"] = {
        "schema_id": EXTENDED_MEASUREMENT_SCHEMA_ID,
        "family": family,
        "binding": binding.to_dict(),
        "horizon_days": list(horizons),
        "threshold_selection": False,
        "local_resampling": False,
        "measurement_authority": True,
        "routing_authority": False,
        "production_authority": False,
    }
    return output


def _validate_binding(frame: pd.DataFrame, binding: PITCoreBinding, *, estimator_id: str) -> None:
    timestamp = pd.DatetimeIndex(frame["timestamp"])
    first = timestamp[0].to_pydatetime()
    _ = Layer2MeasurementCoordinate(
        carrier_id=binding.carrier_id,
        view_id=binding.view_id,
        physical_horizon="5d/20d/60d",
        observation_time=first,
        available_at=first + timedelta(seconds=binding.availability_delay_seconds),
        source_id=binding.source_id,
        source_version=binding.source_version,
        source_receipt_sha256=binding.source_receipt_sha256,
        estimator_id=estimator_id,
        estimator_version="1.0",
        bar_authority=binding.bar_authority,
        carrier_source_authority=binding.carrier_source_authority,
        membership_version=binding.membership_version,
        gap_policy=binding.gap_policy,
    )


def _validated_extended_bars(frame: pd.DataFrame, *, require_volume: bool) -> pd.DataFrame:
    required = {"timestamp", "open", "high", "low", "close"}
    if require_volume:
        required.update({"volume", "amount"})
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValidationError(f"extended measurement bars missing columns: {missing}")
    result = frame.copy().reset_index(drop=True)
    timestamp = pd.DatetimeIndex(pd.to_datetime(result["timestamp"], errors="raise"))
    if timestamp.tz is None or timestamp.has_duplicates or not timestamp.is_monotonic_increasing:
        raise ValidationError("extended measurement timestamps must be timezone-aware, unique, ordered")
    result["timestamp"] = timestamp
    numeric = ["open", "high", "low", "close"]
    if require_volume:
        numeric.extend(["volume", "amount"])
    for column in numeric:
        result[column] = pd.to_numeric(result[column], errors="raise").astype(float)
    if not np.isfinite(result[numeric].to_numpy(float)).all():
        raise ValidationError("extended measurement numeric inputs must be finite")
    if bool((result[["open", "high", "low", "close"]] <= 0.0).any().any()):
        raise ValidationError("extended measurement OHLC must be positive")
    if require_volume and bool((result[["volume", "amount"]] < 0.0).any().any()):
        raise ValidationError("extended measurement volume/amount cannot be negative")
    return result


def _validate_horizons(horizons: tuple[int, ...]) -> None:
    if horizons != EXTENDED_HORIZON_DAYS:
        raise ValidationError("extended measurement horizons are frozen at 5/20/60 days")


def _prior_zscore(series: pd.Series, window: int) -> pd.Series:
    history = series.rolling(window, min_periods=window)
    mean = history.mean().shift(1)
    std = history.std(ddof=0).shift(1).replace(0.0, np.nan)
    return (series - mean) / std


def _relative_to_prior_median(series: pd.Series, window: int) -> pd.Series:
    prior = series.rolling(window, min_periods=window).median().shift(1).replace(0.0, np.nan)
    return series / prior - 1.0


def _age_since_maximum(values: np.ndarray) -> float:
    return float(len(values) - 1 - int(np.argmax(values)))


def _age_since_minimum(values: np.ndarray) -> float:
    return float(len(values) - 1 - int(np.argmin(values)))


def _align(values: np.ndarray, size: int, start: int) -> np.ndarray:
    output = np.full(size, np.nan, dtype=float)
    if len(values):
        output[start:] = values
    return output


def math_ceil_tenth(count: int) -> int:
    return (count + 9) // 10


__all__ = [
    "EXTENDED_HORIZON_DAYS",
    "EXTENDED_MEASUREMENT_SCHEMA_ID",
    "build_cross_sectional_structure_measurements",
    "build_path_lifecycle_measurements",
    "build_volume_liquidity_measurements",
]
