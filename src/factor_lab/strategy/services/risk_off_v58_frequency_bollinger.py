"""Strictly causal frequency-specific Bollinger channels for V58 research.

The centre and the channel thickness have separate physical jobs:

* a clean causal low-pass estimates the background at cutoff period ``P``;
* an independently filtered high-pass or ``P/2..P`` band-pass estimates the
  amplitude that the channel must absorb;
* the close of bar ``t`` may only decide the position opened on bar ``t+1``.

This module is a bounded research carrier.  It has no production authority and
does not inspect registered events or future observations.
"""

# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportCallIssue=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd
from scipy import signal

PERIODS: tuple[int, ...] = (48, 96, 192, 384)
THICKNESS_SOURCES: tuple[str, ...] = ("highpass", "bandpass")
WINDOW_MULTIPLIERS: tuple[float, ...] = (0.5, 1.0, 2.0)
WIDTH_MULTIPLIERS: tuple[float, ...] = (1.0, 1.5, 2.0)
ACTIONS: tuple[str, ...] = ("trend_breakout", "mean_repair")
# A bounded, formula-native sweep used by ``FrequencyBollingerSpec``.  This is
# an experiment menu, not the mathematical domain of the generic component.
# Keeping the lower cutoff fixed at 1/P isolates the width of the *existing*
# band-pass component rather than silently changing the centre.
BAND_UPPER_FREQUENCY_RATIOS: tuple[float, ...] = (1.5, 2.0, 2.5)


@dataclass(frozen=True, slots=True)
class FrequencyBollingerSpec:
    """One member of the pre-registered Phase5K candidate family."""

    period_bars: int
    thickness_source: str
    window_multiplier: float
    width_multiplier: float
    action: str
    filter_order: int = 4
    band_upper_frequency_ratio: float = 2.0

    def __post_init__(self) -> None:
        if self.period_bars not in PERIODS:
            raise ValueError(f"period_bars must be one of {PERIODS}")
        if self.thickness_source not in THICKNESS_SOURCES:
            raise ValueError(f"unknown thickness_source: {self.thickness_source}")
        if self.window_multiplier not in WINDOW_MULTIPLIERS:
            raise ValueError(f"window_multiplier must be one of {WINDOW_MULTIPLIERS}")
        if self.width_multiplier not in WIDTH_MULTIPLIERS:
            raise ValueError(f"width_multiplier must be one of {WIDTH_MULTIPLIERS}")
        if self.action not in ACTIONS:
            raise ValueError(f"unknown action: {self.action}")
        if not 1 <= self.filter_order <= 8:
            raise ValueError("filter_order must be in [1, 8]")
        if self.band_upper_frequency_ratio not in BAND_UPPER_FREQUENCY_RATIOS:
            raise ValueError(
                "band_upper_frequency_ratio must be one of "
                f"{BAND_UPPER_FREQUENCY_RATIOS}"
            )
        if self.thickness_source == "highpass" and self.band_upper_frequency_ratio != 2.0:
            raise ValueError(
                "band_upper_frequency_ratio applies only to the bandpass thickness source"
            )

    @property
    def window_bars(self) -> int:
        return max(8, int(round(self.period_bars * self.window_multiplier)))

    @property
    def candidate_id(self) -> str:
        window = str(self.window_multiplier).replace(".", "p")
        width = str(self.width_multiplier).replace(".", "p")
        candidate = (
            f"p{self.period_bars}_{self.thickness_source}"
            f"_w{window}_k{width}_{self.action}"
        )
        if self.band_upper_frequency_ratio != 2.0:
            ratio = str(self.band_upper_frequency_ratio).replace(".", "p")
            candidate += f"_bandupper{ratio}"
        return candidate


def candidate_catalog() -> tuple[FrequencyBollingerSpec, ...]:
    """Return the complete finite family (4 × 2 × 3 × 3 × 2 = 144)."""

    return tuple(
        FrequencyBollingerSpec(
            period_bars=period,
            thickness_source=source,
            window_multiplier=window,
            width_multiplier=width,
            action=action,
        )
        for period, source, window, width, action in product(
            PERIODS,
            THICKNESS_SOURCES,
            WINDOW_MULTIPLIERS,
            WIDTH_MULTIPLIERS,
            ACTIONS,
        )
    )


def _finite_log_price(close: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(close, errors="coerce").astype(float)
    if numeric.empty or numeric.isna().any() or numeric.le(0.0).any():
        raise ValueError("close must be non-empty, finite, and positive")
    if not numeric.index.is_monotonic_increasing or numeric.index.has_duplicates:
        raise ValueError("close index must be ordered and unique")
    return np.log(numeric).rename("log_close")


def _causal_sos(values: pd.Series, sos: np.ndarray, name: str) -> pd.Series:
    array = values.to_numpy(dtype=float)
    initial = signal.sosfilt_zi(sos) * float(array[0])
    filtered, _ = signal.sosfilt(sos, array, zi=initial)
    return pd.Series(filtered, index=values.index, name=name, dtype=float)


def causal_lowpass(log_close: pd.Series, period_bars: int, order: int = 4) -> pd.Series:
    sos = signal.butter(
        order,
        1.0 / float(period_bars),
        btype="lowpass",
        fs=1.0,
        output="sos",
    )
    return _causal_sos(log_close, sos, "middle_log")


def causal_thickness_component(
    log_close: pd.Series,
    *,
    period_bars: int,
    source: str,
    order: int = 4,
    band_upper_frequency_ratio: float = 2.0,
) -> pd.Series:
    """Return an independent component; never ``raw - lowpass``."""

    if period_bars <= 2:
        raise ValueError("period_bars must place 1/P strictly below Nyquist")
    if not np.isfinite(band_upper_frequency_ratio):
        raise ValueError("band_upper_frequency_ratio must be finite")
    if source == "highpass":
        if band_upper_frequency_ratio != 2.0:
            raise ValueError(
                "band_upper_frequency_ratio applies only to the bandpass thickness source"
            )
        sos = signal.butter(
            order,
            1.0 / float(period_bars),
            btype="highpass",
            fs=1.0,
            output="sos",
        )
    elif source == "bandpass":
        if band_upper_frequency_ratio <= 1.0:
            raise ValueError(
                "band_upper_frequency_ratio must be greater than 1 for an ordered band"
            )
        upper_frequency = band_upper_frequency_ratio / float(period_bars)
        if upper_frequency >= 0.5:
            raise ValueError(
                "band_upper_frequency_ratio / period_bars must be strictly below Nyquist"
            )
        sos = signal.butter(
            order,
            (
                1.0 / float(period_bars),
                upper_frequency,
            ),
            btype="bandpass",
            fs=1.0,
            output="sos",
        )
    else:
        raise ValueError(f"unknown thickness source: {source}")
    return _causal_sos(log_close, sos, "thickness_component_log")


def build_frequency_bollinger(
    close: pd.Series,
    spec: FrequencyBollingerSpec,
) -> pd.DataFrame:
    """Build one strictly causal channel in log-price space."""

    log_close = _finite_log_price(close)
    middle = causal_lowpass(log_close, spec.period_bars, spec.filter_order)
    component = causal_thickness_component(
        log_close,
        period_bars=spec.period_bars,
        source=spec.thickness_source,
        order=spec.filter_order,
        band_upper_frequency_ratio=spec.band_upper_frequency_ratio,
    )
    raw_rms = component.pow(2).rolling(
        spec.window_bars,
        min_periods=spec.window_bars,
    ).mean().pow(0.5)
    # Smooth only the volatility estimate.  The middle remains the explicitly
    # tested clean low-pass, so a positive result cannot be attributed to an
    # undeclared second centre filter.
    half_life = max(2.0, spec.window_bars / 8.0)
    width = raw_rms.ewm(halflife=half_life, adjust=False).mean()
    width = width * spec.width_multiplier
    warmup = max(spec.period_bars * 2, spec.window_bars)
    valid = pd.Series(
        np.arange(len(close)) >= warmup,
        index=close.index,
        name="valid",
    ) & width.notna()
    return pd.DataFrame(
        {
            "log_close": log_close,
            "middle_log": middle,
            "component_log": component,
            "raw_rms_log": raw_rms,
            "width_log": width,
            "upper_log": middle + width,
            "lower_log": middle - width,
            "valid": valid,
        },
        index=close.index,
    )


def channel_decision(channel: pd.DataFrame, action: str) -> pd.Series:
    """Return the close-of-bar long decision for the requested action."""

    required = {"log_close", "middle_log", "upper_log", "lower_log", "valid"}
    missing = sorted(required.difference(channel.columns))
    if missing:
        raise KeyError(f"channel missing columns: {missing}")
    if action not in ACTIONS:
        raise ValueError(f"unknown action: {action}")

    close = channel["log_close"].to_numpy(dtype=float)
    middle = channel["middle_log"].to_numpy(dtype=float)
    upper = channel["upper_log"].to_numpy(dtype=float)
    lower = channel["lower_log"].to_numpy(dtype=float)
    valid = channel["valid"].to_numpy(dtype=bool)
    decision = np.zeros(len(channel), dtype=bool)
    holding = False
    armed = False

    for index in range(len(channel)):
        if not valid[index]:
            holding = False
            armed = False
            continue
        if action == "trend_breakout":
            if not holding and close[index] > upper[index]:
                holding = True
            elif holding and close[index] < lower[index]:
                holding = False
        else:
            if not holding:
                if close[index] < lower[index]:
                    armed = True
                elif armed and close[index] >= lower[index]:
                    holding = True
                    armed = False
            elif close[index] >= middle[index]:
                holding = False
        decision[index] = holding
    return pd.Series(
        decision,
        index=channel.index,
        name="decision_long_for_next_bar",
    )


def executable_position(channel: pd.DataFrame, action: str) -> pd.Series:
    """Apply the frozen next-bar execution lag."""

    return (
        channel_decision(channel, action)
        .shift(1, fill_value=False)
        .astype(float)
        .rename("executable_long_position")
    )


def lowpass_baseline_position(channel: pd.DataFrame) -> pd.Series:
    decision = channel["middle_log"].diff().gt(0.0) & channel["valid"].astype(bool)
    return (
        decision.shift(1, fill_value=False)
        .astype(float)
        .rename("lowpass_baseline_position")
    )


def centre_continuity(channel: pd.DataFrame) -> dict[str, float | int]:
    """Describe, rather than trade around, centre-line direction churn."""

    direction = np.sign(channel.loc[channel["valid"], "middle_log"].diff()).dropna()
    direction = direction.loc[direction.ne(0.0)]
    if direction.empty:
        return {
            "direction_observation_count": 0,
            "switch_count": 0,
            "switch_rate": 0.0,
            "bdci": 100.0,
            "median_run_length_bars": 0.0,
        }
    switches = direction.ne(direction.shift()).fillna(False)
    switches.iloc[0] = False
    run_id = switches.cumsum()
    run_lengths = direction.groupby(run_id).size()
    switch_rate = float(switches.mean())
    return {
        "direction_observation_count": int(len(direction)),
        "switch_count": int(switches.sum()),
        "switch_rate": switch_rate,
        "bdci": 100.0 * (1.0 - switch_rate),
        "median_run_length_bars": float(run_lengths.median()),
    }


def frequency_bollinger_contract() -> dict[str, object]:
    return {
        "schema_id": "risk_off_v58_phase5k_frequency_bollinger@1.0",
        "research_only": True,
        "production_authority": False,
        "runtime_uses_future": False,
        "runtime_uses_registered_events": False,
        "execution_semantics": "close_t_decision_open_t_plus_1",
        "candidate_count": len(candidate_catalog()),
        "centre_role": "causal_clean_lowpass",
        "thickness_role": "independent_highpass_or_adjacent_bandpass_rms",
    }


__all__ = [
    "ACTIONS",
    "BAND_UPPER_FREQUENCY_RATIOS",
    "PERIODS",
    "THICKNESS_SOURCES",
    "WINDOW_MULTIPLIERS",
    "WIDTH_MULTIPLIERS",
    "FrequencyBollingerSpec",
    "build_frequency_bollinger",
    "candidate_catalog",
    "causal_lowpass",
    "causal_thickness_component",
    "centre_continuity",
    "channel_decision",
    "executable_position",
    "frequency_bollinger_contract",
    "lowpass_baseline_position",
]
