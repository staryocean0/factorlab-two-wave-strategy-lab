"""Causal low-pass centre and independent high-pass thickness for Risk-Off V58.

V58 deliberately replaces the mixed-scale V57 centre with one explicit
causal low-pass.  A separate causal high-pass estimates the fast component
used by the rails.  The raw-minus-mid tracking gap is retained separately:

``log(close) = lowpass_mid_log + tracking_residual_log``.

The tracking residual is not allowed to set rail thickness because it contains
the causal low-pass phase lag.  The rails instead use asymmetric quantiles of
the independent high-pass component plus the observed intrabar wick.  They
are not support/resistance levels and do not have trading authority.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import exp, log

import numpy as np
import pandas as pd
from scipy import signal


@dataclass(frozen=True, slots=True)
class LowpassResidualEnvelopeSpec:
    """Low-freedom physical specification for the V58 geometry prototype."""

    cutoff_period_bars: int = 96
    lowpass_order: int = 4
    thickness_window_bars: int = 64
    thickness_lower_quantile: float = 0.10
    thickness_upper_quantile: float = 0.90
    thickness_smoothing_half_life_bars: float = 6.0
    warmup_bars: int = 512

    def __post_init__(self) -> None:
        if self.cutoff_period_bars < 32:
            raise ValueError("cutoff_period_bars must be at least 32")
        if not 1 <= self.lowpass_order <= 8:
            raise ValueError("lowpass_order must be in [1, 8]")
        if self.thickness_window_bars < 32:
            raise ValueError("thickness_window_bars must be at least 32")
        if not (0.0 < self.thickness_lower_quantile < 0.5 < self.thickness_upper_quantile < 1.0):
            raise ValueError("thickness quantiles must straddle the median")
        if self.thickness_smoothing_half_life_bars <= 1.0:
            raise ValueError("thickness smoothing half-life must exceed one bar")
        if self.warmup_bars < max(
            self.cutoff_period_bars * 2,
            self.thickness_window_bars,
        ):
            raise ValueError("warmup_bars must cover two cutoff periods and the thickness window")


def _validate_ohlc(ohlc: pd.DataFrame) -> pd.DataFrame:
    required = {"timestamp", "open", "high", "low", "close"}
    missing = sorted(required.difference(ohlc.columns))
    if missing:
        raise KeyError(f"V58 OHLC carrier missing columns: {missing}")
    if "runtime_uses_future" in ohlc and ohlc["runtime_uses_future"].astype(bool).any():
        raise ValueError("V58 OHLC carrier declares future-dependent rows")
    if "runtime_uses_registered_events" in ohlc and ohlc["runtime_uses_registered_events"].astype(bool).any():
        raise ValueError("V58 OHLC carrier declares registered-event dependencies")
    output = ohlc.loc[
        :,
        ["timestamp", "open", "high", "low", "close"],
    ].copy()
    output["timestamp"] = pd.to_datetime(output["timestamp"], errors="raise")
    output = output.sort_values("timestamp", kind="stable").reset_index(drop=True)
    if output["timestamp"].duplicated().any():
        raise ValueError("V58 OHLC timestamps must be unique")
    values = output[["open", "high", "low", "close"]].apply(
        pd.to_numeric,
        errors="coerce",
    )
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError("V58 OHLC values must be finite")
    if (values <= 0.0).any().any():
        raise ValueError("V58 OHLC values must be positive")
    if (values["high"] < values[["open", "close", "low"]].max(axis=1)).any() or (
        values["low"] > values[["open", "close", "high"]].min(axis=1)
    ).any():
        raise ValueError("V58 OHLC ordering is invalid")
    output[["open", "high", "low", "close"]] = values
    return output


def lowpass_sos(spec: LowpassResidualEnvelopeSpec) -> np.ndarray:
    """Return the frozen causal low-pass coefficients for ``spec``."""

    return signal.butter(
        spec.lowpass_order,
        1.0 / float(spec.cutoff_period_bars),
        btype="lowpass",
        fs=1.0,
        output="sos",
    )


def highpass_sos(spec: LowpassResidualEnvelopeSpec) -> np.ndarray:
    """Return the matched causal high-pass coefficients for ``spec``."""

    return signal.butter(
        spec.lowpass_order,
        1.0 / float(spec.cutoff_period_bars),
        btype="highpass",
        fs=1.0,
        output="sos",
    )


def _causal_sos_filter(
    values: pd.Series,
    sos: np.ndarray,
    *,
    name: str,
) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").astype(float)
    if numeric.empty or not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError(f"{name} input must be non-empty and finite")
    initial_state = signal.sosfilt_zi(sos) * float(numeric.iloc[0])
    filtered, _final_state = signal.sosfilt(
        sos,
        numeric.to_numpy(dtype=float),
        zi=initial_state,
    )
    return pd.Series(filtered, index=numeric.index, dtype=float, name=name)


def causal_lowpass_log_price(
    log_price: pd.Series,
    spec: LowpassResidualEnvelopeSpec = LowpassResidualEnvelopeSpec(),
) -> pd.Series:
    """Filter one finite log-price path without future observations.

    The initial state is the steady state of a constant path at the first
    observation.  This removes the artificial zero-origin transient without
    using any later row.
    """

    return _causal_sos_filter(
        log_price,
        lowpass_sos(spec),
        name="lowpass_mid_log",
    )


def causal_highpass_log_price(
    log_price: pd.Series,
    spec: LowpassResidualEnvelopeSpec = LowpassResidualEnvelopeSpec(),
) -> pd.Series:
    """Return the independent causal fast component at the matched cutoff."""

    return _causal_sos_filter(
        log_price,
        highpass_sos(spec),
        name="fast_close_component_log",
    )


def build_causal_lowpass_residual_envelope(
    ohlc: pd.DataFrame,
    spec: LowpassResidualEnvelopeSpec = LowpassResidualEnvelopeSpec(),
) -> pd.DataFrame:
    """Build the V58 low-frequency centre and independent fast-thickness rails."""

    output = _validate_ohlc(ohlc)
    count = len(output)
    if not count:
        raise ValueError("V58 OHLC carrier cannot be empty")

    log_high = np.log(output["high"].to_numpy(dtype=float))
    log_low = np.log(output["low"].to_numpy(dtype=float))
    log_close = np.log(output["close"].to_numpy(dtype=float))
    mid_log = causal_lowpass_log_price(
        pd.Series(log_close, dtype=float),
        spec,
    ).to_numpy(dtype=float)
    tracking_residual = log_close - mid_log
    fast_close = causal_highpass_log_price(
        pd.Series(log_close, dtype=float),
        spec,
    ).to_numpy(dtype=float)
    fast_high = fast_close + (log_high - log_close)
    fast_low = fast_close + (log_low - log_close)

    upper_offsets = np.full(count, np.nan, dtype=float)
    lower_offsets = np.full(count, np.nan, dtype=float)
    upper_history: deque[float] = deque(maxlen=spec.thickness_window_bars)
    lower_history: deque[float] = deque(maxlen=spec.thickness_window_bars)
    range_history: deque[float] = deque(maxlen=spec.thickness_window_bars)
    decay = exp(log(0.5) / spec.thickness_smoothing_half_life_bars)
    smoothed_upper = max(float(fast_high[0]), 1e-6)
    smoothed_lower = min(float(fast_low[0]), -1e-6)

    for index in range(count):
        upper_history.append(float(fast_high[index]))
        lower_history.append(float(fast_low[index]))
        range_history.append(float(log_high[index] - log_low[index]))
        raw_upper = float(
            np.quantile(
                np.asarray(upper_history),
                spec.thickness_upper_quantile,
            )
        )
        raw_lower = float(
            np.quantile(
                np.asarray(lower_history),
                spec.thickness_lower_quantile,
            )
        )
        minimum_half_width = 0.5 * float(np.median(np.asarray(range_history)))
        raw_upper = max(raw_upper, minimum_half_width, 1e-6)
        raw_lower = min(raw_lower, -minimum_half_width, -1e-6)
        smoothed_upper = decay * smoothed_upper + (1.0 - decay) * raw_upper
        smoothed_lower = decay * smoothed_lower + (1.0 - decay) * raw_lower
        upper_offsets[index] = smoothed_upper
        lower_offsets[index] = smoothed_lower

    upper_log = mid_log + upper_offsets
    lower_log = mid_log + lower_offsets
    geometry_valid = np.arange(count) + 1 >= spec.warmup_bars
    output["lowpass_mid"] = np.exp(mid_log)
    output["residual_upper"] = np.exp(upper_log)
    output["residual_lower"] = np.exp(lower_log)
    output["lowpass_mid_log"] = mid_log
    output["tracking_residual_log"] = tracking_residual
    output["fast_close_component_log"] = fast_close
    output["fast_high_component_proxy_log"] = fast_high
    output["fast_low_component_proxy_log"] = fast_low
    output["residual_upper_offset_log"] = upper_offsets
    output["residual_lower_offset_log"] = lower_offsets
    output["residual_thickness_log"] = upper_log - lower_log
    output["residual_thickness_pct"] = np.expm1(upper_log - lower_log) * 100.0
    output["lowpass_direction_up"] = pd.Series(mid_log).diff().gt(0.0).fillna(False).to_numpy(dtype=bool)
    output["v58_geometry_valid"] = geometry_valid
    output["runtime_uses_future"] = False
    output["runtime_uses_registered_events"] = False
    output["strategy_version"] = "V58"
    output["strategy_version_id"] = "risk_off_v58_causal_lowpass_residual_envelope"
    output["strategy_method_id"] = "risk_off_v58_butterworth_lowpass_independent_highpass_v1"
    output["research_authority"] = True
    output["production_authority"] = False
    output["action_semantics"] = (
        "geometry_only;no_trade_action;bar_t_uses_observations_through_t;"
        "explicit_causal_lowpass_mid;"
        "independent_matched_causal_highpass_thickness;"
        "tracking_residual_excluded_from_thickness;"
        "asymmetric_fast_component_quantile_envelope"
    )
    return output


__all__ = [
    "LowpassResidualEnvelopeSpec",
    "build_causal_lowpass_residual_envelope",
    "causal_highpass_log_price",
    "causal_lowpass_log_price",
    "highpass_sos",
    "lowpass_sos",
]
