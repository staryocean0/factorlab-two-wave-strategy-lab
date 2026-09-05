# pyright: reportAny=false, reportArgumentType=false, reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Canonical Sepp--Lucic paper-kernel time-series primitives.

This module intentionally exposes the realized daily paper kernel itself.  It
does not estimate a rolling covariance, subtract a local mean product, choose a
trend/reversal route, or select a timing-tool parameter.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError

PAPER_KERNEL_SPAN_DAYS: Final[tuple[int, ...]] = (
    1,
    2,
    3,
    4,
    5,
    10,
    15,
    20,
    30,
    60,
    100,
    150,
    200,
    300,
    400,
    500,
)
PAPER_KERNEL_VOLATILITY_SPAN: Final[int] = 33
PAPER_KERNEL_ANNUALIZATION: Final[int] = 260
PAPER_KERNEL_VOLATILITY_TARGET: Final[float] = 0.15
PAPER_KERNEL_EMPIRICAL_WARMUP_DAYS: Final[int] = 250


def paper_kernel_signal_column_name(span_days: int) -> str:
    """Return the stable column name for the strictly lagged signal."""

    _validate_span(span_days)
    return f"paper_signal_s{span_days}_t_minus_1"


def paper_kernel_return_column_name(span_days: int) -> str:
    """Return the stable column name for the daily realized gross kernel."""

    _validate_span(span_days)
    return f"paper_kernel_daily_gross_return_s{span_days}"


def build_paper_kernel_panel(
    daily_panel: pd.DataFrame,
    *,
    spans: Sequence[int] = PAPER_KERNEL_SPAN_DAYS,
    drop_warmup: bool = False,
) -> pd.DataFrame:
    """Build exact, causal, one-point-per-day paper-kernel series.

    The first 250 rows are a one-off empirical warmup following Section 7.3 of
    the paper.  When ``drop_warmup`` is false those rows remain present with
    kernel fields set to missing so this panel can align with a wider attribute
    table.  They are physically removed when ``drop_warmup`` is true.
    """

    ordered_spans = _validated_spans(spans)
    daily = _validated_daily(daily_panel)
    normalized = _normalized_simple_returns(daily["close"].to_numpy(dtype=float))
    row_index = np.arange(len(daily))
    warmed = row_index >= PAPER_KERNEL_EMPIRICAL_WARMUP_DAYS
    columns: dict[str, np.ndarray] = {"normalized_return_z_t": normalized.copy()}
    all_finite = np.isfinite(normalized)
    for span in ordered_spans:
        nu = 1.0 - 2.0 / (span + 1.0)
        raw_filter = _ewma_filter(normalized, nu)
        loading = math.sqrt((1.0 + nu) / (1.0 - nu))
        signal = loading * raw_filter
        lagged_signal = np.roll(signal, 1)
        lagged_signal[0] = np.nan
        daily_gross = PAPER_KERNEL_VOLATILITY_TARGET / math.sqrt(PAPER_KERNEL_ANNUALIZATION) * lagged_signal * normalized
        signal_column = paper_kernel_signal_column_name(span)
        return_column = paper_kernel_return_column_name(span)
        columns[signal_column] = np.where(warmed, lagged_signal, np.nan)
        columns[return_column] = np.where(warmed, daily_gross, np.nan)
        all_finite &= np.isfinite(daily_gross)
    result = pd.concat(
        [daily[["timestamp"]], pd.DataFrame(columns, index=daily.index)],
        axis=1,
    )
    if drop_warmup:
        result = result.loc[warmed & all_finite].reset_index(drop=True)
    return result


def _validated_daily(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"timestamp", "close"}
    missing = required - set(frame.columns)
    if missing:
        raise ValidationError(f"paper-kernel daily panel missing columns: {sorted(missing)}")
    daily = frame.loc[:, ["timestamp", "close"]].copy()
    daily["timestamp"] = pd.to_datetime(daily["timestamp"], errors="coerce")
    daily["close"] = pd.to_numeric(daily["close"], errors="coerce")
    daily = daily.dropna().sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    if len(daily) <= PAPER_KERNEL_EMPIRICAL_WARMUP_DAYS:
        raise ValidationError("paper-kernel daily panel does not cover the empirical warmup")
    if bool((daily["close"] <= 0.0).any()):
        raise ValidationError("paper-kernel close values must be positive")
    return daily


def _validated_spans(spans: Sequence[int]) -> tuple[int, ...]:
    ordered = tuple(int(value) for value in spans)
    if not ordered or ordered != tuple(sorted(set(ordered))):
        raise ValidationError("paper-kernel spans must be non-empty, unique, and increasing")
    for span in ordered:
        _validate_span(span)
    return ordered


def _validate_span(span_days: int) -> None:
    if isinstance(span_days, bool) or int(span_days) != span_days or span_days < 1:
        raise ValidationError("paper-kernel span must be a positive integer number of days")


def _normalized_simple_returns(close: np.ndarray) -> np.ndarray:
    returns = np.full(len(close), np.nan, dtype=float)
    returns[1:] = close[1:] / close[:-1] - 1.0
    alpha = 2.0 / (PAPER_KERNEL_VOLATILITY_SPAN + 1.0)
    variance = np.full(len(close), np.nan, dtype=float)
    current = math.nan
    for index, value in enumerate(returns):
        if not math.isfinite(float(value)):
            continue
        current = value * value if not math.isfinite(current) else alpha * value * value + (1.0 - alpha) * current
        variance[index] = current
    volatility = np.sqrt(variance)
    lagged_volatility = np.roll(volatility, 1)
    lagged_volatility[0] = np.nan
    normalized = returns / lagged_volatility
    normalized[~np.isfinite(normalized)] = np.nan
    return normalized


def _ewma_filter(values: np.ndarray, nu: float) -> np.ndarray:
    output = np.full(len(values), np.nan, dtype=float)
    current = 0.0
    finite_count = 0
    for index, value in enumerate(values):
        if not math.isfinite(float(value)):
            continue
        current = (1.0 - nu) * float(value) + nu * current
        output[index] = current
        finite_count += 1
    if finite_count == 0:
        raise ValidationError("paper-kernel EWMA received no finite returns")
    return output


__all__ = [
    "PAPER_KERNEL_ANNUALIZATION",
    "PAPER_KERNEL_EMPIRICAL_WARMUP_DAYS",
    "PAPER_KERNEL_SPAN_DAYS",
    "PAPER_KERNEL_VOLATILITY_SPAN",
    "PAPER_KERNEL_VOLATILITY_TARGET",
    "build_paper_kernel_panel",
    "paper_kernel_return_column_name",
    "paper_kernel_signal_column_name",
]
