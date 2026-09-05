"""Low-freedom FDA-triggered multiscale channel research prototype.

The entry gate follows the mechanism in the FDA TSMOM paper: a causal local
quadratic estimate supplies endpoint velocity and acceleration, and a strong
direction requires both derivatives to share a sign.  That gate may *start* a
position but never ends one.  The position lifecycle belongs to one of two
explicit channel mechanisms:

* ``opposite_rail``: hold until price crosses the channel's opposite rail;
* ``extreme_retracement``: hold until price gives back one entry-time channel
  width from the subsequent high/low.

The module is research-only and deliberately has no V62 runtime authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

import numpy as np
import pandas as pd

from factor_lab.strategy.services.risk_off_v58_frequency_bollinger import (
    FrequencyBollingerSpec,
    build_frequency_bollinger,
)

Lifecycle = Literal["opposite_rail", "extreme_retracement"]
PERIOD_BARS = (48, 96, 192, 384)
LIFECYCLES: tuple[Lifecycle, ...] = ("opposite_rail", "extreme_retracement")


@dataclass(frozen=True, slots=True)
class FDAExplosiveChannelSpec:
    """One member of the fixed 4-scale by 2-lifecycle prototype family."""

    period_bars: int
    lifecycle: Lifecycle

    def __post_init__(self) -> None:
        if self.period_bars not in PERIOD_BARS:
            raise ValueError(f"period_bars must be one of {PERIOD_BARS}")
        if self.lifecycle not in LIFECYCLES:
            raise ValueError(f"lifecycle must be one of {LIFECYCLES}")

    @property
    def derivative_window_bars(self) -> int:
        """Keep the derivative horizon formula-bound at one quarter scale."""

        return self.period_bars // 4

    @property
    def candidate_id(self) -> str:
        return f"fda_p{self.period_bars}_{self.lifecycle}"


def prototype_catalog() -> tuple[FDAExplosiveChannelSpec, ...]:
    """Return the complete, pre-declared eight-member family."""

    return tuple(
        FDAExplosiveChannelSpec(period_bars=period, lifecycle=lifecycle)
        for period in PERIOD_BARS
        for lifecycle in LIFECYCLES
    )


def rolling_endpoint_derivatives(
    log_close: pd.Series,
    window_bars: int,
) -> tuple[pd.Series, pd.Series]:
    """Estimate causal endpoint derivatives with a local quadratic projection."""

    if window_bars < 5:
        raise ValueError("window_bars must be at least five")
    values = pd.to_numeric(log_close, errors="raise").to_numpy(float)
    if not np.isfinite(values).all():
        raise ValueError("log_close must be finite")
    x = np.arange(-(window_bars - 1), 1, dtype=float)
    design = np.column_stack((np.ones(window_bars), x, x * x))
    inverse = np.linalg.pinv(design)
    velocity_weights = inverse[1]
    acceleration_weights = 2.0 * inverse[2]
    velocity = np.full(len(values), np.nan, dtype=float)
    acceleration = np.full(len(values), np.nan, dtype=float)
    if len(values) >= window_bars:
        velocity[window_bars - 1 :] = np.convolve(
            values,
            velocity_weights[::-1],
            mode="valid",
        )
        acceleration[window_bars - 1 :] = np.convolve(
            values,
            acceleration_weights[::-1],
            mode="valid",
        )
    return (
        pd.Series(velocity, index=log_close.index, name="fda_velocity_log_per_bar"),
        pd.Series(
            acceleration,
            index=log_close.index,
            name="fda_acceleration_log_per_bar2",
        ),
    )


# Compatibility alias for the original V0 research scripts.  New durable
# formulas should import the public name above.
_rolling_endpoint_derivatives = rolling_endpoint_derivatives


def _channel_spec(spec: FDAExplosiveChannelSpec) -> FrequencyBollingerSpec:
    """Freeze the carrier geometry; only scale and lifecycle may vary."""

    return FrequencyBollingerSpec(
        period_bars=spec.period_bars,
        thickness_source="bandpass",
        window_multiplier=2.0,
        width_multiplier=1.0,
        action="trend_breakout",
        filter_order=2,
    )


def build_fda_explosive_channel(
    close: pd.Series,
    spec: FDAExplosiveChannelSpec,
) -> pd.DataFrame:
    """Build a symmetric causal long/short state machine for one candidate."""

    numeric = pd.to_numeric(close, errors="raise").astype(float)
    if numeric.empty or numeric.isna().any() or numeric.le(0.0).any():
        raise ValueError("close must be non-empty, finite, and positive")
    if numeric.index.has_duplicates or not numeric.index.is_monotonic_increasing:
        raise ValueError("close index must be ordered and unique")

    channel = build_frequency_bollinger(numeric, _channel_spec(spec))
    velocity, acceleration = rolling_endpoint_derivatives(
        channel["log_close"],
        spec.derivative_window_bars,
    )
    log_close = channel["log_close"].to_numpy(float)
    upper = channel["upper_log"].to_numpy(float)
    lower = channel["lower_log"].to_numpy(float)
    width = channel["width_log"].to_numpy(float)
    valid = (
        channel["valid"].to_numpy(bool)
        & velocity.notna().to_numpy(bool)
        & acceleration.notna().to_numpy(bool)
    )
    velocity_values = velocity.to_numpy(float)
    acceleration_values = acceleration.to_numpy(float)
    strong_up = valid & (velocity_values > 0.0) & (acceleration_values > 0.0)
    strong_down = valid & (velocity_values < 0.0) & (acceleration_values < 0.0)
    entry_up = strong_up & (log_close > upper)
    entry_down = strong_down & (log_close < lower)

    decision = np.zeros(len(numeric), dtype=np.int8)
    entry_trigger = np.zeros(len(numeric), dtype=np.int8)
    exit_trigger = np.zeros(len(numeric), dtype=bool)
    running_extreme = np.full(len(numeric), np.nan, dtype=float)
    live_boundary = np.full(len(numeric), np.nan, dtype=float)
    holding = 0
    extreme = np.nan
    entry_width = np.nan

    for location in range(len(numeric)):
        if not valid[location]:
            holding = 0
            continue
        if holding == 0:
            if entry_up[location]:
                holding = 1
                extreme = log_close[location]
                entry_width = width[location]
                entry_trigger[location] = 1
            elif entry_down[location]:
                holding = -1
                extreme = log_close[location]
                entry_width = width[location]
                entry_trigger[location] = -1
        elif holding == 1:
            extreme = max(extreme, log_close[location])
            boundary = (
                lower[location]
                if spec.lifecycle == "opposite_rail"
                else extreme - entry_width
            )
            live_boundary[location] = boundary
            if log_close[location] < boundary:
                holding = 0
                exit_trigger[location] = True
        else:
            extreme = min(extreme, log_close[location])
            boundary = (
                upper[location]
                if spec.lifecycle == "opposite_rail"
                else extreme + entry_width
            )
            live_boundary[location] = boundary
            if log_close[location] > boundary:
                holding = 0
                exit_trigger[location] = True
        if holding != 0:
            running_extreme[location] = extreme
            if np.isnan(live_boundary[location]):
                live_boundary[location] = (
                    lower[location]
                    if holding == 1 and spec.lifecycle == "opposite_rail"
                    else upper[location]
                    if holding == -1 and spec.lifecycle == "opposite_rail"
                    else extreme - entry_width
                    if holding == 1
                    else extreme + entry_width
                )
        decision[location] = holding

    executable = np.zeros(len(decision), dtype=np.int8)
    executable[1:] = decision[:-1]
    output = channel.assign(
        fda_velocity_log_per_bar=velocity,
        fda_acceleration_log_per_bar2=acceleration,
        fda_strong_up=strong_up,
        fda_strong_down=strong_down,
        fda_entry_up=entry_up,
        fda_entry_down=entry_down,
        entry_trigger_direction=entry_trigger,
        exit_trigger=exit_trigger,
        running_extreme_log=running_extreme,
        live_exit_boundary_log=live_boundary,
        decision_position_for_next_bar=decision,
        executable_position=executable,
        candidate_id=spec.candidate_id,
        runtime_uses_future=False,
        runtime_uses_registered_events=False,
        research_authority=True,
        production_authority=False,
    )
    output.attrs["formula_contract"] = fda_explosive_channel_contract(spec)
    return output


def fda_explosive_channel_contract(
    spec: FDAExplosiveChannelSpec,
) -> dict[str, object]:
    """Expose formula identity and authority boundaries."""

    return {
        "schema_id": "market_state_fda_explosive_channel_prototype@1.0",
        "candidate_id": spec.candidate_id,
        "spec": asdict(spec),
        "candidate_family": {
            "period_bars": list(PERIOD_BARS),
            "lifecycles": list(LIFECYCLES),
            "candidate_count": len(prototype_catalog()),
        },
        "entry_formula": (
            "outer_rail_break AND causal_local_quadratic_endpoint_velocity_and_"
            "acceleration_share_direction"
        ),
        "entry_gate_has_exit_authority": False,
        "carrier_formula": {
            "middle": "second_order_causal_lowpass",
            "width": "adjacent_bandpass_RMS_2x_period_window",
            "width_multiplier": 1.0,
        },
        "lifecycle_formula": spec.lifecycle,
        "execution_semantics": "close_t_decision_open_t_plus_1",
        "runtime_uses_future": False,
        "runtime_uses_registered_events": False,
        "research_authority": True,
        "production_authority": False,
        "v62_runtime_modified": False,
    }


__all__ = [
    "FDAExplosiveChannelSpec",
    "LIFECYCLES",
    "PERIOD_BARS",
    "build_fda_explosive_channel",
    "fda_explosive_channel_contract",
    "prototype_catalog",
    "rolling_endpoint_derivatives",
]
