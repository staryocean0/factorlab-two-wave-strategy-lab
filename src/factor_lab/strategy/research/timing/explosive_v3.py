# pyright: reportAny=false, reportArgumentType=false, reportAssignmentType=false
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
# pyright: reportCallInDefaultInitializer=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportOperatorIssue=false
# pyright: reportPrivateUsage=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Research-only FDA crash-rebound and P48->P96 explosive strategy.

This is the canonical source after the timing strategy authority reset.  The
formula is preserved from V3, but the strategy is pending current four-layer
requalification and has no registered-use or trading authority.
"""

from __future__ import annotations

import pandas as pd

from factor_lab.market_state.context_free_explosive_channel import (
    build_context_free_explosive_channel,
)
from factor_lab.market_state.context_free_explosive_two_bucket import (
    CRASH_REBOUND_BUCKET,
    _registered_arc_position,
    compose_context_free_explosive_two_bucket_v1,
)
from factor_lab.market_state.fda_multiscale_channel_v1 import (
    build_fda_multiscale_channel,
    fda_multiscale_channel_contract,
)
from factor_lab.market_state.fda_recent_down_rebound_bridge import (
    FDARecentDownReboundSpec,
    build_fda_recent_down_rebound_bridge,
    fda_recent_down_rebound_contract,
)
from factor_lab.market_state.timing_explosive_layer_v2 import (
    HIGH_SLOPE_CHANNEL_BUCKET,
    HIGH_SLOPE_CHANNEL_SPEC,
    TIMING_EXPLOSIVE_LAYER_V2_VERSION,
)

TIMING_EXPLOSIVE_LAYER_V3_SCHEMA_ID = "market_state_timing_explosive_layer@3.1"
TIMING_EXPLOSIVE_LAYER_V3_VERSION = "timing_explosive_layer_v3"
FOUR_LAYER_ROLE = "layer3_strategy_research"
LIFECYCLE = "research_pending_requalification"
BUCKET_ORDER = (CRASH_REBOUND_BUCKET, HIGH_SLOPE_CHANNEL_BUCKET)

FIELD_LABELS_ZH = {
    "crash_rebound_raw": "FDA暴跌反弹原始执行信号",
    "crash_rebound_executable": "FDA暴跌反弹当前执行棒生效",
    "channel_up_raw": "P48→P96高斜率上涨真通道原始信号",
    "channel_down_raw": "P48→P96高斜率下跌真通道原始信号",
    "channel_up_executable": "反弹余集P48→P96上涨真通道",
    "channel_down_executable": "反弹余集P48→P96下跌真通道",
    "high_slope_channel_position_before_routing": "路由前P48→P96通道多空仓位",
    "high_slope_channel_authority_period_bars": "P48→P96通道当前权威周期",
    "crash_rebound_to_channel_up_handoff": "FDA暴跌反弹向上涨真通道交接",
    "crash_rebound_to_channel_down_handoff": "FDA暴跌反弹失败后向下跌真通道交接",
    "explosive_route_slot_id": "第一层高斜率责任桶",
    "explosive_route_direction_id": "第一层方向",
    "explosive_route_claimed": "第一层是否认领",
    "remaining_after_explosive_layer": "交给第二层低斜率趋势的剩余K线",
    "explosive_route_position_long_short": "第一层多空仓位",
    "strategy_version": "第一层策略版本",
    "runtime_uses_future": "运行时是否使用未来数据",
    "runtime_uses_registered_events": "运行时是否使用事后事件",
    "research_authority": "研究权限",
    "production_authority": "生产权限",
    "fda_rebound_entry_velocity_log_per_bar": "反弹入场FDA速度",
    "fda_rebound_entry_acceleration_log_per_bar2": "反弹入场FDA加速度",
    "fda_rebound_entry_eligible": "反弹入场FDA门是否通过",
    "fda_rebound_entry_reason": "反弹入场FDA门原因",
    "crash_rebound_arc_candidate_executable": "暴跌反弹弧线父工具执行候选",
    "crash_rebound_down_context_executable": "暴跌反弹最近下跌第一腿上下文",
}


def _validated_close(causal_ohlc: pd.DataFrame) -> pd.Series:
    required = {"timestamp", "open", "high", "low", "close"}
    missing = sorted(required.difference(causal_ohlc))
    if missing:
        raise KeyError(f"timing explosive layer V3 missing OHLC columns: {missing}")
    index = pd.DatetimeIndex(pd.to_datetime(causal_ohlc["timestamp"], errors="raise"))
    if index.empty or index.has_duplicates or not index.is_monotonic_increasing:
        raise ValueError("timing explosive layer V3 requires ordered unique timestamps")
    close = pd.Series(
        pd.to_numeric(causal_ohlc["close"], errors="raise").to_numpy(float),
        index=index,
        name="close",
    )
    if close.isna().any() or close.le(0.0).any():
        raise ValueError("timing explosive layer V3 requires finite positive closes")
    return close


def build_timing_explosive_layer_v3(
    causal_ohlc: pd.DataFrame,
    rebound_spec: FDARecentDownReboundSpec = FDARecentDownReboundSpec(),
) -> pd.DataFrame:
    """Build the research strategy and expose its exact remainder."""

    close = _validated_close(causal_ohlc)
    index = close.index
    historical_channel = build_context_free_explosive_channel(causal_ohlc)
    historical_down = pd.Series(
        historical_channel["context_free_explosive_down_executable"].to_numpy(bool),
        index=index,
        dtype=bool,
    )
    arc = _registered_arc_position(causal_ohlc, index)
    rebound_detail = build_fda_recent_down_rebound_bridge(
        close=close,
        rebound_parent=arc.gt(0.5),
        rebound_candidate_position=arc,
        down_channel_context=historical_down,
        context_free_up_channel=pd.Series(False, index=index, dtype=bool),
        spec=rebound_spec,
    )
    crash_rebound = rebound_detail["fda_recent_down_rebound_position"].astype(bool)
    channel = build_fda_multiscale_channel(close, HIGH_SLOPE_CHANNEL_SPEC)
    channel_position = channel["executable_position"].astype(int)
    routed = compose_context_free_explosive_two_bucket_v1(
        index,
        crash_rebound_raw=crash_rebound,
        channel_up_raw=channel_position.eq(1),
        channel_down_raw=channel_position.eq(-1),
    )
    routed["strategy_version"] = TIMING_EXPLOSIVE_LAYER_V3_VERSION
    routed["explosive_route_slot_id"] = routed["explosive_route_slot_id"].replace(
        {"explosive_w12_w24_continuation": HIGH_SLOPE_CHANNEL_BUCKET}
    )
    detail = pd.DataFrame(
        {
            "high_slope_channel_position_before_routing": channel_position,
            "high_slope_channel_authority_period_bars": channel[
                "executable_authority_period_bars"
            ].astype(int),
            "fda_rebound_entry_velocity_log_per_bar": rebound_detail[
                "fda_entry_velocity_log_per_bar"
            ],
            "fda_rebound_entry_acceleration_log_per_bar2": rebound_detail[
                "fda_entry_acceleration_log_per_bar2"
            ],
            "fda_rebound_entry_eligible": rebound_detail[
                "fda_recent_down_rebound_eligible"
            ].astype(bool),
            "fda_rebound_entry_reason": rebound_detail[
                "fda_recent_down_rebound_reason"
            ].astype(str),
            "crash_rebound_arc_candidate_executable": arc.astype(float),
            "crash_rebound_down_context_executable": historical_down,
        },
        index=index,
    )
    output = pd.concat([routed, detail], axis=1)
    output.attrs["field_labels_zh"] = {
        column: FIELD_LABELS_ZH.get(column, f"第一层V3字段：{column}")
        for column in output.columns
    }
    output.attrs["formula_contract"] = timing_explosive_layer_v3_contract(rebound_spec)
    return output


def timing_explosive_layer_v3_contract(
    rebound_spec: FDARecentDownReboundSpec = FDARecentDownReboundSpec(),
) -> dict[str, object]:
    return {
        "schema_id": TIMING_EXPLOSIVE_LAYER_V3_SCHEMA_ID,
        "strategy_version": TIMING_EXPLOSIVE_LAYER_V3_VERSION,
        "four_layer_role": FOUR_LAYER_ROLE,
        "lifecycle": LIFECYCLE,
        "replaceable_by_layer2_measurement": True,
        "long_term_foundation": False,
        "supersedes_infrastructure_version": TIMING_EXPLOSIVE_LAYER_V2_VERSION,
        "bucket_order": list(BUCKET_ORDER),
        "active_directions": {
            CRASH_REBOUND_BUCKET: ["up"],
            HIGH_SLOPE_CHANNEL_BUCKET: ["up", "down"],
        },
        "crash_rebound_formula": fda_recent_down_rebound_contract(rebound_spec),
        "high_slope_channel_formula": fda_multiscale_channel_contract(HIGH_SLOPE_CHANNEL_SPEC),
        "replacement_scope": "crash_rebound_entry_quality_gate_only",
        "superseded_gate": "four_bar_path_efficiency_threshold",
        "unchanged_boundaries": [
            "registered_arc_parent_and_lifecycle",
            "recent_completed_W12_W24_down_first_leg",
            "crash_rebound_first_priority",
            "P48_to_P96_opposite_rail_channel_remainder",
        ],
        "retired_general_route": "explosive_w12_w24_continuation",
        "retired_route_retained_only_as": "intrinsic_recent_down_first_leg_for_crash_rebound",
        "routing_formula": (
            "FDA-qualified crash rebound first; P48->P96 opposite-rail true "
            "channel consumes the strict remainder in both directions"
        ),
        "remainder_field": "remaining_after_explosive_layer",
        "next_layer": "low_slope_ordinary_trend_owner_open",
        "execution_semantics": "closed_bar_decision_visible_on_next_executable_bar",
        "development_period": "2009-2017",
        "repeat_audit_period": "2018-2020",
        "external_validation_period": "2021-2026_frozen_aggregate_replay_only",
        "runtime_uses_future": False,
        "runtime_uses_registered_events": False,
        "research_authority": True,
        "registered_use_authority": False,
        "architecture_lock_authority": False,
        "parameter_authority": False,
        "paper_trading_authority": False,
        "live_trading_authority": False,
        "production_authority": False,
        "v62_runtime_modified": False,
        "field_labels_zh": FIELD_LABELS_ZH,
    }


__all__ = [
    "BUCKET_ORDER",
    "FIELD_LABELS_ZH",
    "FOUR_LAYER_ROLE",
    "LIFECYCLE",
    "TIMING_EXPLOSIVE_LAYER_V3_SCHEMA_ID",
    "TIMING_EXPLOSIVE_LAYER_V3_VERSION",
    "build_timing_explosive_layer_v3",
    "timing_explosive_layer_v3_contract",
]
