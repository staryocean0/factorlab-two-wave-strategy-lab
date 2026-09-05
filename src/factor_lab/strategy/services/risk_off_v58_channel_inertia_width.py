"""Bounded channel-inertia and width surface for V58 Phase5V."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd

from factor_lab.strategy.services.risk_off_v58_frequency_bollinger import (
    causal_lowpass,
    causal_thickness_component,
    executable_position,
)

MEMORY_BARS: tuple[int, ...] = (96, 144, 192, 288, 384)
WIDTH_MULTIPLIERS: tuple[float, ...] = (1.0, 1.25, 1.5, 2.0)
THICKNESS_PERIOD_BARS = 48
MIDDLE_PERIOD_BARS = 48
FILTER_ORDER = 4


@dataclass(frozen=True, slots=True)
class ChannelInertiaWidthSpec:
    """One member of the pre-registered 5 × 4 surface."""

    memory_bars: int
    width_multiplier: float

    def __post_init__(self) -> None:
        if self.memory_bars not in MEMORY_BARS:
            raise ValueError(f"memory_bars must be one of {MEMORY_BARS}")
        if self.width_multiplier not in WIDTH_MULTIPLIERS:
            raise ValueError(
                f"width_multiplier must be one of {WIDTH_MULTIPLIERS}",
            )

    @property
    def middle_period_bars(self) -> int:
        return MIDDLE_PERIOD_BARS

    @property
    def width_half_life_bars(self) -> float:
        return self.memory_bars / 8.0

    @property
    def candidate_id(self) -> str:
        width = str(self.width_multiplier).replace(".", "p")
        return f"channel_memory_{self.memory_bars}_width_{width}"


def candidate_catalog() -> tuple[ChannelInertiaWidthSpec, ...]:
    return tuple(
        ChannelInertiaWidthSpec(memory, width)
        for memory, width in product(MEMORY_BARS, WIDTH_MULTIPLIERS)
    )


def _finite_log_close(close: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(close, errors="coerce").astype(float)
    if numeric.empty or numeric.isna().any() or numeric.le(0.0).any():
        raise ValueError("close must be non-empty, finite, and positive")
    if not numeric.index.is_monotonic_increasing or numeric.index.has_duplicates:
        raise ValueError("close index must be ordered and unique")
    return np.log(numeric).rename("log_close")


def build_channel_inertia_width(
    close: pd.Series,
    spec: ChannelInertiaWidthSpec,
) -> pd.DataFrame:
    """Build one strictly causal channel with tied physical inertia."""

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
    raw_rms = component.pow(2).rolling(
        spec.memory_bars,
        min_periods=spec.memory_bars,
    ).mean().pow(0.5)
    width = raw_rms.ewm(
        halflife=spec.width_half_life_bars,
        adjust=False,
    ).mean() * spec.width_multiplier
    valid = pd.Series(
        np.arange(len(close)) >= spec.memory_bars,
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


def build_common_inertia_ablation(
    close: pd.Series,
    spec: ChannelInertiaWidthSpec,
) -> pd.DataFrame:
    """Change the middle period to N/2 for diagnosis, never selection."""

    log_close = _finite_log_close(close)
    middle = causal_lowpass(
        log_close,
        spec.memory_bars // 2,
        FILTER_ORDER,
    )
    component = causal_thickness_component(
        log_close,
        period_bars=THICKNESS_PERIOD_BARS,
        source="bandpass",
        order=FILTER_ORDER,
    )
    raw_rms = component.pow(2).rolling(
        spec.memory_bars,
        min_periods=spec.memory_bars,
    ).mean().pow(0.5)
    width = raw_rms.ewm(
        halflife=spec.width_half_life_bars,
        adjust=False,
    ).mean() * spec.width_multiplier
    valid = pd.Series(
        np.arange(len(close)) >= spec.memory_bars,
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


def build_channel_inertia_position(
    close: pd.Series,
    spec: ChannelInertiaWidthSpec,
) -> pd.Series:
    return executable_position(
        build_channel_inertia_width(close, spec),
        "trend_breakout",
    )


def channel_inertia_width_contract() -> dict[str, object]:
    return {
        "schema_id": "risk_off_v58_channel_inertia_width@1.0",
        "candidate_count": len(candidate_catalog()),
        "memory_bars": list(MEMORY_BARS),
        "width_multipliers": list(WIDTH_MULTIPLIERS),
        "middle_period_bars": MIDDLE_PERIOD_BARS,
        "thickness_period_bars": THICKNESS_PERIOD_BARS,
        "width_rms_window_rule": "memory_bars",
        "width_half_life_rule": "memory_bars / 8",
        "common_inertia_ablation_middle_rule": "memory_bars / 2",
        "common_inertia_ablation_selectable": False,
        "position_domain": [0, 1],
        "runtime_uses_future": False,
        "execution_semantics": "close_t_decision_open_t_plus_1",
    }


__all__ = [
    "FILTER_ORDER",
    "MEMORY_BARS",
    "MIDDLE_PERIOD_BARS",
    "THICKNESS_PERIOD_BARS",
    "WIDTH_MULTIPLIERS",
    "ChannelInertiaWidthSpec",
    "build_channel_inertia_position",
    "build_channel_inertia_width",
    "build_common_inertia_ablation",
    "candidate_catalog",
    "channel_inertia_width_contract",
]
