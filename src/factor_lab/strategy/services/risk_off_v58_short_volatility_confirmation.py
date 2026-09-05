"""Short volatility memory with asymmetric downside confirmation."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd

from factor_lab.strategy.services.risk_off_v58_channel_inertia_width import (
    FILTER_ORDER,
    MIDDLE_PERIOD_BARS,
    THICKNESS_PERIOD_BARS,
    WIDTH_MULTIPLIERS,
)
from factor_lab.strategy.services.risk_off_v58_frequency_bollinger import (
    causal_lowpass,
    causal_thickness_component,
)

VOLATILITY_MEMORY_BARS: tuple[int, ...] = (24, 48, 72, 96)
DOWNSIDE_CONFIRMATION_BARS: tuple[int, ...] = tuple(range(1, 9))


@dataclass(frozen=True, slots=True)
class ShortVolatilityConfirmationSpec:
    """One member of the frozen W × K × C-down surface."""

    volatility_memory_bars: int
    width_multiplier: float
    downside_confirmation_bars: int

    def __post_init__(self) -> None:
        if self.volatility_memory_bars not in VOLATILITY_MEMORY_BARS:
            raise ValueError(
                f"volatility_memory_bars must be one of {VOLATILITY_MEMORY_BARS}",
            )
        if self.width_multiplier not in WIDTH_MULTIPLIERS:
            raise ValueError(
                f"width_multiplier must be one of {WIDTH_MULTIPLIERS}",
            )
        if self.downside_confirmation_bars not in DOWNSIDE_CONFIRMATION_BARS:
            raise ValueError(
                f"downside_confirmation_bars must be one of {DOWNSIDE_CONFIRMATION_BARS}",
            )

    @property
    def width_half_life_bars(self) -> float:
        return max(2.0, self.volatility_memory_bars / 8.0)

    @property
    def candidate_id(self) -> str:
        width = str(self.width_multiplier).replace(".", "p")
        return f"short_vol_w{self.volatility_memory_bars}_k{width}_down_confirm_{self.downside_confirmation_bars}"


def candidate_catalog() -> tuple[ShortVolatilityConfirmationSpec, ...]:
    """Return the frozen 4 × 4 × 8 candidate family."""

    return tuple(
        ShortVolatilityConfirmationSpec(memory, width, confirmation)
        for memory, width, confirmation in product(
            VOLATILITY_MEMORY_BARS,
            WIDTH_MULTIPLIERS,
            DOWNSIDE_CONFIRMATION_BARS,
        )
    )


def _finite_log_close(close: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(close, errors="coerce").astype(float)
    if numeric.empty or numeric.isna().any() or numeric.le(0.0).any():
        raise ValueError("close must be non-empty, finite, and positive")
    if not numeric.index.is_monotonic_increasing or numeric.index.has_duplicates:
        raise ValueError("close index must be ordered and unique")
    return np.log(numeric).rename("log_close")


def build_short_volatility_channel(
    close: pd.Series,
    spec: ShortVolatilityConfirmationSpec,
) -> pd.DataFrame:
    """Build a P48 channel whose width reacts on the shorter W horizon."""

    log_close = _finite_log_close(close)
    middle = causal_lowpass(
        log_close,
        MIDDLE_PERIOD_BARS,
        FILTER_ORDER,
    )
    component = causal_thickness_component(
        log_close,
        period_bars=THICKNESS_PERIOD_BARS,
        source="bandpass",
        order=FILTER_ORDER,
    )
    raw_rms = (
        component.pow(2)
        .rolling(
            spec.volatility_memory_bars,
            min_periods=spec.volatility_memory_bars,
        )
        .mean()
        .pow(0.5)
    )
    width = (
        raw_rms.ewm(
            halflife=spec.width_half_life_bars,
            adjust=False,
        ).mean()
        * spec.width_multiplier
    )
    warmup = max(
        2 * MIDDLE_PERIOD_BARS,
        spec.volatility_memory_bars,
    )
    valid = (
        pd.Series(
            np.arange(len(close)) >= warmup,
            index=close.index,
            name="valid",
        )
        & width.notna()
    )
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


def asymmetric_channel_decision(
    channel: pd.DataFrame,
    downside_confirmation_bars: int,
    *,
    recovery_width_fraction: float = 1.0,
) -> pd.Series:
    """Confirm cash entry and recover above a parameterized upper-side line.

    ``recovery_width_fraction=1`` exactly preserves the historical upper-rail
    recovery.  Values below one recover between the middle and upper rail;
    values above one require an overshoot beyond the live upper rail.  The
    state machine and next-bar execution semantics do not change.
    """

    if downside_confirmation_bars not in DOWNSIDE_CONFIRMATION_BARS:
        raise ValueError(
            f"downside_confirmation_bars must be one of {DOWNSIDE_CONFIRMATION_BARS}",
        )
    if not 0.0 <= recovery_width_fraction <= 2.0:
        raise ValueError("recovery_width_fraction must be in [0, 2]")
    required = {"log_close", "upper_log", "lower_log", "valid"}
    missing = sorted(required.difference(channel.columns))
    if missing:
        raise KeyError(f"channel missing columns: {missing}")

    close = channel["log_close"].to_numpy(dtype=float)
    upper = channel["upper_log"].to_numpy(dtype=float)
    lower = channel["lower_log"].to_numpy(dtype=float)
    recovery = 0.5 * ((1.0 + recovery_width_fraction) * upper + (1.0 - recovery_width_fraction) * lower)
    valid = channel["valid"].to_numpy(dtype=bool)
    decision = np.zeros(len(channel), dtype=bool)
    holding = False
    downside_run = 0

    for index in range(len(channel)):
        if not valid[index]:
            holding = False
            downside_run = 0
            continue
        if holding:
            downside_run = downside_run + 1 if close[index] < lower[index] else 0
            if downside_run >= downside_confirmation_bars:
                holding = False
                downside_run = 0
        elif close[index] > recovery[index]:
            holding = True
        decision[index] = holding

    return pd.Series(
        decision,
        index=channel.index,
        name="asymmetric_long_decision_for_next_bar",
    )


def build_asymmetric_position(
    close: pd.Series,
    spec: ShortVolatilityConfirmationSpec,
    *,
    recovery_width_fraction: float = 1.0,
) -> pd.Series:
    """Build the channel and apply the frozen next-bar execution lag."""

    channel = build_short_volatility_channel(close, spec)
    return (
        asymmetric_channel_decision(
            channel,
            spec.downside_confirmation_bars,
            recovery_width_fraction=recovery_width_fraction,
        )
        .shift(1, fill_value=False)
        .astype(float)
        .rename("asymmetric_executable_long_position")
    )


def short_volatility_confirmation_contract() -> dict[str, object]:
    return {
        "schema_id": "risk_off_v58_short_volatility_confirmation@1.0",
        "candidate_count": len(candidate_catalog()),
        "volatility_memory_bars": list(VOLATILITY_MEMORY_BARS),
        "width_multipliers": list(WIDTH_MULTIPLIERS),
        "downside_confirmation_bars": list(
            DOWNSIDE_CONFIRMATION_BARS,
        ),
        "middle_period_bars": MIDDLE_PERIOD_BARS,
        "thickness_period_bars": THICKNESS_PERIOD_BARS,
        "upside_recovery_confirmation_bars": 1,
        "downside_confirmation_rule": ("consecutive closes below each bar's causal live lower rail"),
        "position_domain": [0, 1],
        "runtime_uses_future": False,
        "execution_semantics": "close_t_decision_open_t_plus_1",
    }


__all__ = [
    "DOWNSIDE_CONFIRMATION_BARS",
    "VOLATILITY_MEMORY_BARS",
    "ShortVolatilityConfirmationSpec",
    "asymmetric_channel_decision",
    "build_asymmetric_position",
    "build_short_volatility_channel",
    "candidate_catalog",
    "short_volatility_confirmation_contract",
]
