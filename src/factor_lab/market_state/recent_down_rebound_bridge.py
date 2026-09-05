"""Causal recent-down context bridge for the frozen sharp-up reversal route.

The bridge is intentionally small: a completed down-channel arms the route for
a finite number of bars, and a fresh sharp-up parent may participate only when
its strictly-prior four-bar path is efficient enough.  A context-free upward
channel always has higher authority and therefore preempts the bridge.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import cast

import numpy as np
import pandas as pd

from factor_lab.market_state.timing_strategy_routing import TimingRouteClaim

RECENT_DOWN_REBOUND_BRIDGE_SCHEMA_ID = "market_state_recent_down_rebound_bridge@1.0"
RECENT_DOWN_REBOUND_BRIDGE_VERSION = "recent_down_rebound_bridge_v0"
ROUTE_SLOT_ID = "explosive_crash_rebound"
TOOL_ID = "causal_asymmetric_arc_state_space_envelope"
TOOL_PROFILE_ID = "registered_v1_4_frozen_benchmark_15m_recent_down_bridge"
CONTEXT_TOOL_ID = "causal_trendline_channel"
CONTEXT_PROFILE_ID = "completed_context_free_or_s20_conditioned_down_channel"


@dataclass(frozen=True)
class RecentDownReboundBridgeSpec:
    """Frozen research-candidate values selected without using 2018-2020."""

    maximum_down_context_age_bars: int = 14
    rebound_path_lookback_bars: int = 4
    minimum_rebound_path_efficiency: float = 0.7533253477706635

    def __post_init__(self) -> None:
        if self.maximum_down_context_age_bars < 1:
            raise ValueError("maximum_down_context_age_bars must be positive")
        if self.rebound_path_lookback_bars < 2:
            raise ValueError("rebound_path_lookback_bars must be at least two")
        if not 0.0 <= self.minimum_rebound_path_efficiency <= 1.0:
            raise ValueError("minimum_rebound_path_efficiency must be in [0, 1]")


def _path_efficiency(values: np.ndarray) -> float:
    if len(values) < 2 or not np.isfinite(values).all():
        return 0.0
    travel = float(np.abs(np.diff(values)).sum())
    return abs(float(values[-1] - values[0])) / travel if travel > 0.0 else 0.0


def build_recent_down_rebound_bridge(
    close: pd.Series,
    rebound_parent: pd.Series,
    rebound_candidate_position: pd.Series,
    down_channel_context: pd.Series,
    context_free_up_channel: pd.Series,
    spec: RecentDownReboundBridgeSpec = RecentDownReboundBridgeSpec(),
) -> pd.DataFrame:
    """Build a causal bridge while preserving context-free channel priority.

    Every entry feature excludes the current executable bar.  Event eligibility
    is frozen at the first rebound-parent bar and retained until that parent
    lifecycle ends; later prices cannot rewrite the entry decision.
    """

    series = (
        close,
        rebound_parent,
        rebound_candidate_position,
        down_channel_context,
        context_free_up_channel,
    )
    if any(not close.index.equals(value.index) for value in series[1:]):
        raise ValueError("all bridge inputs must share the exact index")
    if close.empty or close.isna().any() or not np.isfinite(close.to_numpy(float)).all():
        raise ValueError("close must be finite and non-empty")
    if not rebound_candidate_position.fillna(0.0).isin((0.0, 1.0)).all():
        raise ValueError("rebound_candidate_position must contain only 0 or 1")

    parent = rebound_parent.fillna(False).to_numpy(bool)
    candidate = rebound_candidate_position.fillna(0.0).to_numpy(float) > 0.5
    down = down_channel_context.fillna(False).to_numpy(bool)
    persistent_up = context_free_up_channel.fillna(False).to_numpy(bool)
    log_close = np.log(close.to_numpy(float))
    size = len(close)

    context_age = np.full(size, np.nan, dtype=float)
    entry_efficiency = np.full(size, np.nan, dtype=float)
    eligible = np.zeros(size, dtype=bool)
    reason = np.full(size, "outside_rebound_parent", dtype=object)
    last_down_location = -1
    event_eligible = False
    event_age = np.nan
    event_efficiency = np.nan
    event_reason = "outside_rebound_parent"

    for location in range(size):
        if down[location]:
            last_down_location = location
        starts = parent[location] and (location == 0 or not parent[location - 1])
        if starts:
            event_age = float(location - last_down_location) if last_down_location >= 0 else np.inf
            left = max(0, location - spec.rebound_path_lookback_bars)
            event_efficiency = _path_efficiency(log_close[left:location])
            recent_context = 0.0 < event_age <= float(spec.maximum_down_context_age_bars)
            sufficient_quality = event_efficiency >= spec.minimum_rebound_path_efficiency
            event_eligible = bool(recent_context and sufficient_quality)
            if not recent_context:
                event_reason = "stale_or_missing_down_context"
            elif not sufficient_quality:
                event_reason = "low_rebound_path_efficiency"
            else:
                event_reason = "recent_down_high_quality_bridge"
        elif not parent[location]:
            event_eligible = False
            event_age = np.nan
            event_efficiency = np.nan
            event_reason = "outside_rebound_parent"

        if parent[location]:
            context_age[location] = event_age
            entry_efficiency[location] = event_efficiency
            eligible[location] = event_eligible
            reason[location] = event_reason

    bridge_position = candidate & eligible & ~persistent_up
    owner = np.full(size, "none", dtype=object)
    owner[parent & ~eligible] = "rebound_rejected"
    owner[bridge_position] = "rebound_bridge"
    owner[persistent_up] = "context_free_up_channel"

    handoff = np.zeros(size, dtype=bool)
    if size > 1:
        handoff[1:] = persistent_up[1:] & bridge_position[:-1]

    return pd.DataFrame(
        {
            "recent_down_context_age_at_rebound_entry_bars": context_age,
            "rebound_entry_path_efficiency": entry_efficiency,
            "recent_down_rebound_bridge_eligible": eligible,
            "recent_down_rebound_bridge_reason": reason,
            "recent_down_rebound_bridge_position": bridge_position.astype(float),
            "recent_down_rebound_handoff_to_context_free_up": handoff,
            "recent_down_rebound_owner": owner,
            "strategy_version": RECENT_DOWN_REBOUND_BRIDGE_VERSION,
            "runtime_uses_future": False,
            "runtime_uses_registered_events": False,
            "research_authority": True,
            "production_authority": False,
        },
        index=close.index,
    )


def recent_down_rebound_bridge_contract(
    spec: RecentDownReboundBridgeSpec = RecentDownReboundBridgeSpec(),
) -> dict[str, object]:
    return {
        "schema_id": RECENT_DOWN_REBOUND_BRIDGE_SCHEMA_ID,
        "profile_version": RECENT_DOWN_REBOUND_BRIDGE_VERSION,
        "spec": asdict(spec),
        "context": "bars_since_last_context_free_or_context_conditioned_down_channel_bar",
        "entry_quality": "strictly_prior_close_path_efficiency",
        "authority_priority": ["context_free_up_channel", "rebound_bridge", "rejected_or_remainder"],
        "handoff": "context_free upward channel preempts the bridge without an opposing position",
        "research_authority": True,
        "production_authority": False,
        "runtime_uses_future": False,
        "runtime_uses_registered_events": False,
        "field_labels_zh": {
            "maximum_down_context_age_bars": "最近真实下跌通道上下文最大有效K线数",
            "rebound_path_lookback_bars": "反弹入场前路径效率观察K线数",
            "minimum_rebound_path_efficiency": "反弹入场前最低路径效率",
        },
        "route_contract": {
            "route_slot_id": ROUTE_SLOT_ID,
            "direction_id": "up",
            "tool_id": TOOL_ID,
            "tool_profile_id": TOOL_PROFILE_ID,
            "context_tool_id": CONTEXT_TOOL_ID,
            "context_profile_id": CONTEXT_PROFILE_ID,
            "retired_direction": "down",
            "rejected_events_fall_through": True,
        },
    }


def recent_down_rebound_bridge_claim(frame: pd.DataFrame) -> TimingRouteClaim:
    """Adapt the frozen bridge position to the third shared route slot."""

    column = "recent_down_rebound_bridge_position"
    if column not in frame:
        raise KeyError(f"recent-down rebound bridge claim missing column: {column}")
    eligible = cast(pd.Series, frame[column]).fillna(0.0)
    if not bool(eligible.isin((0.0, 1.0)).all()):
        raise ValueError("recent-down rebound bridge position must contain only 0 or 1")
    return TimingRouteClaim(
        slot_id=ROUTE_SLOT_ID,
        direction_id="up",
        tool_id=TOOL_ID,
        tool_profile_id=TOOL_PROFILE_ID,
        state_id="recent_down_high_quality_rebound_bridge",
        eligible=eligible.astype(bool),
        context_tool_id=CONTEXT_TOOL_ID,
        context_profile_id=CONTEXT_PROFILE_ID,
    )


__all__ = [
    "CONTEXT_PROFILE_ID",
    "CONTEXT_TOOL_ID",
    "RECENT_DOWN_REBOUND_BRIDGE_SCHEMA_ID",
    "RECENT_DOWN_REBOUND_BRIDGE_VERSION",
    "ROUTE_SLOT_ID",
    "TOOL_ID",
    "TOOL_PROFILE_ID",
    "RecentDownReboundBridgeSpec",
    "build_recent_down_rebound_bridge",
    "recent_down_rebound_bridge_claim",
    "recent_down_rebound_bridge_contract",
]
