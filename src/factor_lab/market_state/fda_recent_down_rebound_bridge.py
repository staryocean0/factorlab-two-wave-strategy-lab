# pyright: reportAny=false, reportArgumentType=false, reportAssignmentType=false
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
# pyright: reportCallInDefaultInitializer=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportOperatorIssue=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Paper-derived entry-quality gate for the crash-rebound route.

The route lifecycle and recent completed-down context are intentionally kept
identical to the superseded path-efficiency bridge.  At the first bar of each
registered causal arc, a rebound is accepted only when a strictly prior local
quadratic estimate has both positive endpoint velocity and acceleration.
Eligibility is frozen for the complete parent lifecycle.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from factor_lab.market_state.fda_explosive_channel_prototype import (
    rolling_endpoint_derivatives,
)

FDA_RECENT_DOWN_REBOUND_SCHEMA_ID = "market_state_fda_recent_down_rebound_bridge@1.0"
FDA_RECENT_DOWN_REBOUND_VERSION = "fda_recent_down_rebound_bridge_v1"


@dataclass(frozen=True, slots=True)
class FDARecentDownReboundSpec:
    """Formula-anchored values; the derivative window is P48 / 4."""

    maximum_down_context_age_bars: int = 14
    derivative_window_bars: int = 12

    def __post_init__(self) -> None:
        if self.maximum_down_context_age_bars < 1:
            raise ValueError("maximum_down_context_age_bars must be positive")
        if self.derivative_window_bars < 5:
            raise ValueError("derivative_window_bars must be at least five")


def build_fda_recent_down_rebound_bridge(
    close: pd.Series,
    rebound_parent: pd.Series,
    rebound_candidate_position: pd.Series,
    down_channel_context: pd.Series,
    context_free_up_channel: pd.Series,
    spec: FDARecentDownReboundSpec = FDARecentDownReboundSpec(),
) -> pd.DataFrame:
    """Apply a causal FDA gate while retaining the parent's full lifecycle."""

    inputs = (
        rebound_parent,
        rebound_candidate_position,
        down_channel_context,
        context_free_up_channel,
    )
    if any(not close.index.equals(value.index) for value in inputs):
        raise ValueError("all FDA rebound inputs must share the exact index")
    numeric = pd.to_numeric(close, errors="raise").astype(float)
    if numeric.empty or numeric.isna().any() or numeric.le(0.0).any():
        raise ValueError("close must be finite, non-empty, and positive")
    if not rebound_candidate_position.fillna(0.0).isin((0.0, 1.0)).all():
        raise ValueError("rebound_candidate_position must contain only 0 or 1")

    parent = rebound_parent.fillna(False).to_numpy(bool)
    candidate = rebound_candidate_position.fillna(0.0).to_numpy(float) > 0.5
    down = down_channel_context.fillna(False).to_numpy(bool)
    persistent_up = context_free_up_channel.fillna(False).to_numpy(bool)
    velocity, acceleration = rolling_endpoint_derivatives(
        np.log(numeric),
        spec.derivative_window_bars,
    )
    # The signal measured at decision bar t may first affect executable bar
    # t+1.  Parent-start eligibility therefore reads the shifted measurement.
    executable_velocity = velocity.shift(1)
    executable_acceleration = acceleration.shift(1)
    size = len(numeric)

    context_age = np.full(size, np.nan, dtype=float)
    entry_velocity = np.full(size, np.nan, dtype=float)
    entry_acceleration = np.full(size, np.nan, dtype=float)
    eligible = np.zeros(size, dtype=bool)
    reason = np.full(size, "outside_rebound_parent", dtype=object)
    last_down_location = -1
    event_eligible = False
    event_age = np.nan
    event_velocity = np.nan
    event_acceleration = np.nan
    event_reason = "outside_rebound_parent"

    for location in range(size):
        if down[location]:
            last_down_location = location
        starts = parent[location] and (location == 0 or not parent[location - 1])
        if starts:
            event_age = (
                float(location - last_down_location)
                if last_down_location >= 0
                else np.inf
            )
            event_velocity = float(executable_velocity.iloc[location])
            event_acceleration = float(executable_acceleration.iloc[location])
            recent_context = 0.0 < event_age <= float(
                spec.maximum_down_context_age_bars
            )
            strong_up = bool(
                np.isfinite(event_velocity)
                and np.isfinite(event_acceleration)
                and event_velocity > 0.0
                and event_acceleration > 0.0
            )
            event_eligible = recent_context and strong_up
            if not recent_context:
                event_reason = "stale_or_missing_down_context"
            elif not strong_up:
                event_reason = "fda_velocity_acceleration_not_both_positive"
            else:
                event_reason = "recent_down_fda_strong_up_bridge"
        elif not parent[location]:
            event_eligible = False
            event_age = np.nan
            event_velocity = np.nan
            event_acceleration = np.nan
            event_reason = "outside_rebound_parent"

        if parent[location]:
            context_age[location] = event_age
            entry_velocity[location] = event_velocity
            entry_acceleration[location] = event_acceleration
            eligible[location] = event_eligible
            reason[location] = event_reason

    bridge_position = candidate & eligible & ~persistent_up
    owner = np.full(size, "none", dtype=object)
    owner[parent & ~eligible] = "rebound_rejected"
    owner[bridge_position] = "fda_rebound_bridge"
    owner[persistent_up] = "context_free_up_channel"
    handoff = np.zeros(size, dtype=bool)
    if size > 1:
        handoff[1:] = persistent_up[1:] & bridge_position[:-1]

    return pd.DataFrame(
        {
            "recent_down_context_age_at_rebound_entry_bars": context_age,
            "fda_entry_velocity_log_per_bar": entry_velocity,
            "fda_entry_acceleration_log_per_bar2": entry_acceleration,
            "fda_recent_down_rebound_eligible": eligible,
            "fda_recent_down_rebound_reason": reason,
            "fda_recent_down_rebound_position": bridge_position.astype(float),
            "fda_recent_down_rebound_handoff_to_up_channel": handoff,
            "fda_recent_down_rebound_owner": owner,
            "strategy_version": FDA_RECENT_DOWN_REBOUND_VERSION,
            "runtime_uses_future": False,
            "runtime_uses_registered_events": False,
            "research_authority": True,
            "production_authority": False,
        },
        index=numeric.index,
    )


def fda_recent_down_rebound_contract(
    spec: FDARecentDownReboundSpec = FDARecentDownReboundSpec(),
) -> dict[str, object]:
    """Expose the formula lineage and the deliberately frozen boundaries."""

    return {
        "schema_id": FDA_RECENT_DOWN_REBOUND_SCHEMA_ID,
        "profile_version": FDA_RECENT_DOWN_REBOUND_VERSION,
        "spec": asdict(spec),
        "paper_mechanism": (
            "causal local-quadratic endpoint first and second derivatives; "
            "strong up requires both positive"
        ),
        "paper_source": "Time Series Momentum Strategies Using Financial Data Analysis",
        "derivative_window_derivation": "P48_base_channel_period / 4 = 12 bars",
        "entry_formula": (
            "registered_arc_parent_start AND recent_completed_W12_W24_down_context "
            "AND prior_velocity>0 AND prior_acceleration>0"
        ),
        "lifecycle": "registered causal asymmetric-arc lifecycle unchanged",
        "replaces_only": "four_bar_path_efficiency_entry_quality_gate",
        "held_fixed": [
            "maximum_down_context_age_14_bars",
            "registered_arc_parent_and_lifecycle",
            "crash_rebound_first_route_priority",
            "P48_to_P96_channel_strict_remainder",
        ],
        "runtime_uses_future": False,
        "runtime_uses_registered_events": False,
        "research_authority": True,
        "production_authority": False,
    }


__all__ = [
    "FDA_RECENT_DOWN_REBOUND_SCHEMA_ID",
    "FDA_RECENT_DOWN_REBOUND_VERSION",
    "FDARecentDownReboundSpec",
    "build_fda_recent_down_rebound_bridge",
    "fda_recent_down_rebound_contract",
]
