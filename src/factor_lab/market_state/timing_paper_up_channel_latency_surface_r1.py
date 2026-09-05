"""Parameterized frequency-channel builder and latency math for the latency surface.

This module belongs to the latency-surface branch
``market_state_paper_up_channel_latency_surface_r1``.  It reuses the frozen
causal Butterworth functions from the V58 frequency-selective channel and
parameterizes only the post-filter width statistics (RMS window W, EWMA
smoothing half-life HL, width multiplier k) plus the centre cutoff P and the
filter order N.  It also computes the analytical group delays of every
configuration and measures the empirical step-response half-crossing time,
so the reported latency claims are mathematically verifiable.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd
from scipy.signal import butter, group_delay, sos2tf

PHASE1_AXES: Final[dict[str, tuple[int, ...]]] = {
    "centre_period_bars_P": (48, 64, 96),
    "filter_order_N": (1, 2, 4),
    "thickness_rms_window_W": (48, 96, 192),
    "thickness_smoothing_half_life_HL": (4, 8, 24),
}
PHASE2_WIDTH_MULTIPLIERS: Final[tuple[float, ...]] = (0.5, 1.0, 1.5, 2.0)
BAND_UPPER_FREQUENCY_RATIO: Final[float] = 2.0
BARS_PER_TRADING_DAY: Final[float] = 16.0


@dataclass(frozen=True, slots=True)
class FrequencyChannelSpec:
    """One latency-surface channel configuration."""

    centre_period_bars: int
    filter_order: int
    thickness_rms_window: int
    thickness_smoothing_half_life: float
    width_multiplier: float = 1.0
    thickness_source: str = "bandpass"
    band_upper_frequency_ratio: float = BAND_UPPER_FREQUENCY_RATIO

    def __post_init__(self) -> None:
        if self.centre_period_bars < 32:
            raise ValueError("centre_period_bars must be at least 32")
        if not 1 <= self.filter_order <= 8:
            raise ValueError("filter_order must be in [1, 8]")
        if self.thickness_rms_window < 16:
            raise ValueError("thickness_rms_window must be at least 16")
        if self.thickness_smoothing_half_life <= 1.0:
            raise ValueError("thickness smoothing half-life must exceed one bar")
        if self.width_multiplier <= 0.0:
            raise ValueError("width_multiplier must be positive")
        if self.thickness_source not in ("highpass", "bandpass"):
            raise ValueError(f"unknown thickness_source: {self.thickness_source}")
        if not 1.0 < self.band_upper_frequency_ratio <= 3.0:
            raise ValueError("band_upper_frequency_ratio must be in (1, 3]")

    @property
    def candidate_id(self) -> str:
        width = str(self.width_multiplier).replace(".", "p")
        return (
            f"lat_P{self.centre_period_bars}_N{self.filter_order}"
            f"_W{self.thickness_rms_window}_HL{int(self.thickness_smoothing_half_life)}"
            f"_k{width}"
        )

    @property
    def warmup_bars(self) -> int:
        return max(self.centre_period_bars * 2, self.thickness_rms_window)


def phase1_grid() -> tuple[FrequencyChannelSpec, ...]:
    """All 81 phase-1 latency configurations with width multiplier fixed at 1.0."""

    return tuple(
        FrequencyChannelSpec(
            centre_period_bars=P,
            filter_order=N,
            thickness_rms_window=W,
            thickness_smoothing_half_life=float(HL),
            width_multiplier=1.0,
        )
        for P, N, W, HL in itertools.product(
            PHASE1_AXES["centre_period_bars_P"],
            PHASE1_AXES["filter_order_N"],
            PHASE1_AXES["thickness_rms_window_W"],
            PHASE1_AXES["thickness_smoothing_half_life_HL"],
        )
    )


def analytical_delay_bars(spec: FrequencyChannelSpec) -> dict[str, float]:
    """Compute the analytical group delays of one channel configuration."""

    sos_lp = butter(
        spec.filter_order,
        1.0 / float(spec.centre_period_bars),
        btype="lowpass",
        fs=1.0,
        output="sos",
    )
    b_lp, a_lp = sos2tf(sos_lp)
    _, gd_lp = group_delay((b_lp, a_lp), fs=1.0)
    centre_delay = float(gd_lp[0])

    if spec.thickness_source == "bandpass":
        sos_bp = butter(
            spec.filter_order,
            (
                1.0 / float(spec.centre_period_bars),
                spec.band_upper_frequency_ratio / float(spec.centre_period_bars),
            ),
            btype="bandpass",
            fs=1.0,
            output="sos",
        )
        b_bp, a_bp = sos2tf(sos_bp)
        w_bp, gd_bp = group_delay((b_bp, a_bp), fs=1.0)
        centre_frequency = 1.5 / float(spec.centre_period_bars)
        index = int(np.argmin(np.abs(w_bp - centre_frequency)))
        band_delay = float(gd_bp[index])
    else:
        sos_hp = butter(
            spec.filter_order,
            1.0 / float(spec.centre_period_bars),
            btype="highpass",
            fs=1.0,
            output="sos",
        )
        b_hp, a_hp = sos2tf(sos_hp)
        _, gd_hp = group_delay((b_hp, a_hp), fs=1.0)
        band_delay = float(gd_hp[-1])

    rms_window_delay = (spec.thickness_rms_window - 1.0) / 2.0
    smoothing_delay = float(spec.thickness_smoothing_half_life)
    thickness_path_delay = band_delay + rms_window_delay + smoothing_delay
    return {
        "centre_group_delay_bars": centre_delay,
        "bandpass_group_delay_bars": band_delay,
        "rms_window_delay_bars": rms_window_delay,
        "smoothing_delay_bars": smoothing_delay,
        "thickness_path_total_delay_bars": thickness_path_delay,
        "total_channel_latency_bars": centre_delay + thickness_path_delay,
        "centre_group_delay_trading_days": centre_delay / BARS_PER_TRADING_DAY,
        "thickness_path_total_delay_trading_days": thickness_path_delay / BARS_PER_TRADING_DAY,
    }


def step_response_half_crossing_bars(spec: FrequencyChannelSpec) -> float:
    """Empirical latency: bars until the centre crosses the half-way level of a unit step.

    A synthetic log-price path is flat at 0.0, then jumps to 1.0 at bar 500
    and stays there.  The measured latency is the number of bars after the
    step until the causal low-pass centre first reaches 0.5.  This is the
    deterministic, data-free verification of the analytical group delay.
    """

    close = np.exp(np.concatenate([np.zeros(500), np.ones(400)]))
    series = pd.Series(close)
    log_close = np.log(series)
    from factor_lab.strategy.services.risk_off_v58_frequency_bollinger import (
        causal_lowpass,
    )

    centre = causal_lowpass(
        log_close, spec.centre_period_bars, spec.filter_order
    ).to_numpy(float)
    step_location = 500
    target = 0.5
    reached = np.flatnonzero(centre[step_location:] >= target)
    if not len(reached):
        return float("inf")
    return float(reached[0])


def build_channel_rails_frequency_param(
    close: pd.Series,
    spec: FrequencyChannelSpec,
) -> pd.DataFrame:
    """Build strictly causal centre/upper/lower rails for one configuration."""

    from factor_lab.strategy.services.risk_off_v58_frequency_bollinger import (
        causal_lowpass,
        causal_thickness_component,
    )

    if not isinstance(close.index, pd.DatetimeIndex):
        raise TypeError("channel rails require a DatetimeIndex")
    if close.empty or close.index.has_duplicates or not close.index.is_monotonic_increasing:
        raise ValueError("channel rails require unique ordered close prices")
    numeric = pd.to_numeric(close, errors="coerce").astype(float)
    if bool(numeric.le(0.0).any()):
        raise ValueError("close values must be positive")
    log_close = pd.Series(np.log(numeric.to_numpy(float)), index=close.index)

    middle = causal_lowpass(
        log_close, spec.centre_period_bars, spec.filter_order
    )
    component = causal_thickness_component(
        log_close,
        period_bars=spec.centre_period_bars,
        source=spec.thickness_source,
        order=spec.filter_order,
        band_upper_frequency_ratio=spec.band_upper_frequency_ratio,
    )
    raw_rms = (
        component.pow(2)
        .rolling(spec.thickness_rms_window, min_periods=spec.thickness_rms_window)
        .mean()
        .pow(0.5)
    )
    width = (
        raw_rms.ewm(halflife=spec.thickness_smoothing_half_life, adjust=False)
        .mean()
        * spec.width_multiplier
    )
    warmup = np.arange(len(close)) >= spec.warmup_bars
    valid = pd.Series(warmup, index=close.index) & width.notna() & middle.notna()
    upper = middle + width
    lower = middle - width
    return pd.DataFrame(
        {
            "log_close": log_close,
            "middle_log": middle,
            "width_log": width,
            "upper_log": upper,
            "lower_log": lower,
            "valid": valid,
        },
        index=close.index,
    )


def fold_hold_state(
    rails: pd.DataFrame,
) -> pd.Series:
    """Fold close-vs-rails into a strictly causal hold state (no future peeking)."""

    close = rails["log_close"].to_numpy(float)
    upper = rails["upper_log"].to_numpy(float)
    centre = rails["middle_log"].to_numpy(float)
    valid = rails["valid"].to_numpy(bool)
    holding = False
    state = np.zeros(len(rails), dtype=bool)
    for location in range(len(rails)):
        if not bool(valid[location]):
            holding = False
        elif not holding:
            if close[location] > upper[location]:
                holding = True
        else:
            if close[location] < centre[location]:
                holding = False
        state[location] = holding
    return pd.Series(state, index=rails.index, dtype=bool)


__all__ = [
    "BARS_PER_TRADING_DAY",
    "FrequencyChannelSpec",
    "PHASE1_AXES",
    "PHASE2_WIDTH_MULTIPLIERS",
    "analytical_delay_bars",
    "build_channel_rails_frequency_param",
    "fold_hold_state",
    "phase1_grid",
    "step_response_half_crossing_bars",
]
