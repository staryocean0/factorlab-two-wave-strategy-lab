# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Explicit-window PIT successors for annual-only K-line summaries."""

from __future__ import annotations

import math
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_layer2_measurement_plane import validate_measurement_output_columns
from factor_lab.market_state.timing_layer2_pit_core import PITCoreBinding

CONTEXT_SCHEMA_ID: Final[str] = "timing_layer2_context_measurements@1.0"
CONTEXT_HORIZON_DAYS: Final[tuple[int, ...]] = (20, 60, 120)


def build_context_measurements(
    bars: pd.DataFrame,
    *,
    binding: PITCoreBinding,
    horizon_days: tuple[int, ...] = CONTEXT_HORIZON_DAYS,
) -> pd.DataFrame:
    if horizon_days != CONTEXT_HORIZON_DAYS:
        raise ValidationError("context horizons are frozen at 20/60/120 physical days")
    required = {"timestamp", "open", "high", "low", "close"}
    missing = sorted(required.difference(bars.columns))
    if missing:
        raise ValidationError(f"context bars missing columns: {missing}")
    frame = bars.copy().reset_index(drop=True)
    timestamp = pd.DatetimeIndex(pd.to_datetime(frame["timestamp"], errors="raise"))
    if timestamp.tz is None or timestamp.has_duplicates or not timestamp.is_monotonic_increasing:
        raise ValidationError("context timestamps must be timezone-aware, unique, ordered")
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype(float)
    if not np.isfinite(frame[["open", "high", "low", "close"]].to_numpy(float)).all():
        raise ValidationError("context OHLC must be finite")
    log_close = np.log(frame["close"].astype(float))
    returns = log_close.diff()
    sign = np.sign(returns)
    output = pd.DataFrame(
        {
            "carrier_id": binding.carrier_id,
            "view_id": binding.view_id,
            "observation_time": timestamp,
            "available_at": timestamp + pd.to_timedelta(binding.availability_delay_seconds, unit="s"),
        }
    )
    one_day_vol = returns.rolling(binding.bars_per_day, min_periods=binding.bars_per_day).std(ddof=0)
    center = log_close.rolling(4 * binding.bars_per_day, min_periods=4 * binding.bars_per_day).mean()
    center_side = np.sign(log_close - center)
    gap = np.log(frame["open"].astype(float) / frame["close"].astype(float).shift(1)).abs()
    intraday_range = np.log(frame["high"].astype(float) / frame["low"].astype(float))
    intraday_net = np.log(frame["close"].astype(float) / frame["open"].astype(float)).abs()
    for days in horizon_days:
        window = days * binding.bars_per_day
        for lag in (1, 4, 16):
            output[f"return_autocorr_lag{lag}_{days}d"] = (
                returns.rolling(window, min_periods=window).corr(returns.shift(lag)).replace([np.inf, -np.inf], np.nan)
            )
        output[f"sign_persistence_{days}d"] = sign.eq(sign.shift(1)).astype(float).rolling(window, min_periods=window).mean()
        output[f"directional_run_mean_{days}d"] = sign.rolling(window, min_periods=window).apply(_mean_run_length, raw=True)
        output[f"middle_crossing_density_{days}d"] = (
            center_side.ne(center_side.shift(1)).astype(float).rolling(window, min_periods=window).mean()
        )
        output[f"realized_volatility_{days}d"] = returns.pow(2).rolling(window, min_periods=window).sum().pow(0.5)
        output[f"volatility_of_volatility_{days}d"] = one_day_vol.rolling(window, min_periods=window).std(ddof=0)
        output[f"downside_upside_variance_ratio_{days}d"] = returns.rolling(window, min_periods=window).apply(_down_up_ratio, raw=True)
        output[f"jump_tail_share_{days}d"] = returns.rolling(window, min_periods=window).apply(_tail_share, raw=True)
        squared = returns.pow(2).rolling(window, min_periods=window).sum()
        bipower = returns.abs().mul(returns.abs().shift(1)).rolling(window, min_periods=window).sum() * (math.pi / 2.0)
        output[f"bipower_jump_share_{days}d"] = (squared - bipower).clip(lower=0.0) / squared.replace(0.0, np.nan)
        prior_q80 = returns.abs().rolling(window, min_periods=window).quantile(0.8).shift(1)
        abrupt = returns.abs().ge(prior_q80) & returns.abs().shift(1).ge(prior_q80.shift(1)) & sign.ne(sign.shift(1))
        output[f"no_buffer_reversal_rate_{days}d"] = abrupt.astype(float).rolling(window, min_periods=window).mean()
        output[f"overnight_gap_share_{days}d"] = gap.rolling(window, min_periods=window).sum() / (
            gap.add(returns.abs(), fill_value=0.0).rolling(window, min_periods=window).sum().replace(0.0, np.nan)
        )
        output[f"intraday_range_efficiency_{days}d"] = intraday_net.rolling(window, min_periods=window).sum() / intraday_range.rolling(
            window, min_periods=window
        ).sum().replace(0.0, np.nan)
    numeric = output.select_dtypes(include=[np.number]).columns
    output[numeric] = output[numeric].replace([np.inf, -np.inf], np.nan)
    validate_measurement_output_columns(output.columns)
    output.attrs["timing_layer_contract"] = {
        "schema_id": CONTEXT_SCHEMA_ID,
        "horizon_days": list(horizon_days),
        "annual_names_reused": False,
        "local_resampling": False,
        "measurement_authority": True,
        "routing_authority": False,
        "production_authority": False,
    }
    return output


def _mean_run_length(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    finite = finite[finite != 0]
    if len(finite) == 0:
        return math.nan
    changes = np.flatnonzero(np.diff(finite) != 0) + 1
    return float(np.diff(np.r_[0, changes, len(finite)]).mean())


def _down_up_ratio(values: np.ndarray) -> float:
    down = values[values < 0]
    up = values[values > 0]
    if len(up) == 0:
        return math.nan
    return float(np.mean(np.square(down)) / np.mean(np.square(up))) if len(down) else 0.0


def _tail_share(values: np.ndarray) -> float:
    absolute = np.abs(values[np.isfinite(values)])
    if len(absolute) == 0 or float(absolute.sum()) == 0.0:
        return math.nan
    threshold = float(np.quantile(absolute, 0.95))
    return float(absolute[absolute >= threshold].sum() / absolute.sum())


__all__ = ["CONTEXT_HORIZON_DAYS", "CONTEXT_SCHEMA_ID", "build_context_measurements"]
