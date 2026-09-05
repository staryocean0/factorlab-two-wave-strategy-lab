"""Latest timing-infrastructure layer 1: crash rebound plus true channels.

The historical W12/W24 continuation route is intentionally not reused.  It is
only evaluated inside the frozen crash-rebound builder as that tool's intrinsic
first-leg context.  General high-slope up/down ownership belongs to the
evidence-backed P48->P96 FDA channel with opposite-rail exits.
"""

from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from factor_lab.market_state.context_free_explosive_two_bucket import (
    CRASH_REBOUND_BUCKET,
    build_context_free_explosive_two_bucket_v1,
    compose_context_free_explosive_two_bucket_v1,
    context_free_explosive_two_bucket_v1_contract,
)
from factor_lab.market_state.fda_multiscale_channel_v1 import (
    FDAMultiscaleChannelSpec,
    build_fda_multiscale_channel,
    fda_multiscale_channel_contract,
)
from factor_lab.market_state.recent_down_rebound_bridge import (
    RecentDownReboundBridgeSpec,
)

TIMING_EXPLOSIVE_LAYER_V2_SCHEMA_ID = "market_state_timing_explosive_layer@2.0"
TIMING_EXPLOSIVE_LAYER_V2_VERSION = "timing_explosive_layer_v2"
HIGH_SLOPE_CHANNEL_BUCKET = "explosive_p48_p96_true_channel"
BUCKET_ORDER = (CRASH_REBOUND_BUCKET, HIGH_SLOPE_CHANNEL_BUCKET)
HIGH_SLOPE_CHANNEL_SPEC = FDAMultiscaleChannelSpec("opposite_rail", (48, 96))

FIELD_LABELS_ZH = {
    "crash_rebound_raw": "暴跌反弹原始执行信号",
    "crash_rebound_executable": "暴跌反弹当前执行棒生效",
    "channel_up_raw": "P48→P96高斜率上涨真通道原始信号",
    "channel_down_raw": "P48→P96高斜率下跌真通道原始信号",
    "channel_up_executable": "反弹余集P48→P96上涨真通道",
    "channel_down_executable": "反弹余集P48→P96下跌真通道",
    "high_slope_channel_position_before_routing": "路由前P48→P96通道多空仓位",
    "high_slope_channel_authority_period_bars": "P48→P96通道当前权威周期",
    "crash_rebound_to_channel_up_handoff": "暴跌反弹向上涨真通道交接",
    "crash_rebound_to_channel_down_handoff": "暴跌反弹失败后向下跌真通道交接",
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
}


def _validated_close(causal_ohlc: pd.DataFrame) -> pd.Series:
    required = {"timestamp", "open", "high", "low", "close"}
    missing = sorted(required.difference(causal_ohlc))
    if missing:
        raise KeyError(f"timing explosive layer V2 missing OHLC columns: {missing}")
    index = pd.DatetimeIndex(pd.to_datetime(causal_ohlc["timestamp"], errors="raise"))
    if index.empty or index.has_duplicates or not index.is_monotonic_increasing:
        raise ValueError("timing explosive layer V2 requires ordered unique timestamps")
    close = pd.Series(
        pd.to_numeric(causal_ohlc["close"], errors="raise").to_numpy(float),
        index=index,
        name="close",
    )
    if close.isna().any() or close.le(0.0).any():
        raise ValueError("timing explosive layer V2 requires finite positive closes")
    return close


def build_timing_explosive_layer_v2(
    causal_ohlc: pd.DataFrame,
    rebound_spec: RecentDownReboundBridgeSpec = RecentDownReboundBridgeSpec(),
) -> pd.DataFrame:
    """Build the latest first layer and expose the exact layer-2 remainder."""

    close = _validated_close(causal_ohlc)
    index = close.index

    # Preserve the already-validated crash-rebound formula exactly.  Its old
    # W12/W24 channel is intrinsic context only and receives no final route.
    historical_layer = build_context_free_explosive_two_bucket_v1(
        causal_ohlc,
        rebound_spec,
    )
    crash_rebound = pd.Series(
        historical_layer["crash_rebound_raw"].to_numpy(bool),
        index=index,
        dtype=bool,
    )

    channel = build_fda_multiscale_channel(close, HIGH_SLOPE_CHANNEL_SPEC)
    channel_position = channel["executable_position"].astype(int)
    channel_up = channel_position.eq(1)
    channel_down = channel_position.eq(-1)
    routed = compose_context_free_explosive_two_bucket_v1(
        index,
        crash_rebound_raw=crash_rebound,
        channel_up_raw=channel_up,
        channel_down_raw=channel_down,
    )
    routed["strategy_version"] = TIMING_EXPLOSIVE_LAYER_V2_VERSION
    routed["explosive_route_slot_id"] = routed["explosive_route_slot_id"].replace(
        {"explosive_w12_w24_continuation": HIGH_SLOPE_CHANNEL_BUCKET}
    )

    detail = pd.DataFrame(
        {
            "high_slope_channel_position_before_routing": channel_position,
            "high_slope_channel_authority_period_bars": channel[
                "executable_authority_period_bars"
            ].astype(int),
        },
        index=index,
    )
    output = pd.concat([routed, detail], axis=1)
    output.attrs["field_labels_zh"] = {
        column: FIELD_LABELS_ZH.get(column, f"第一层字段：{column}")
        for column in output.columns
    }
    output.attrs["formula_contract"] = timing_explosive_layer_v2_contract(
        rebound_spec
    )
    return output


def timing_explosive_layer_v2_contract(
    rebound_spec: RecentDownReboundBridgeSpec = RecentDownReboundBridgeSpec(),
) -> dict[str, object]:
    """Return the latest infrastructure authority contract for layer 1."""

    historical = context_free_explosive_two_bucket_v1_contract(rebound_spec)
    return {
        "schema_id": TIMING_EXPLOSIVE_LAYER_V2_SCHEMA_ID,
        "strategy_version": TIMING_EXPLOSIVE_LAYER_V2_VERSION,
        "supersedes_infrastructure_version": historical["strategy_version"],
        "bucket_order": list(BUCKET_ORDER),
        "active_directions": {
            CRASH_REBOUND_BUCKET: ["up"],
            HIGH_SLOPE_CHANNEL_BUCKET: ["up", "down"],
        },
        "crash_rebound_formula": historical["crash_rebound_formula"],
        "crash_rebound_spec": asdict(rebound_spec),
        "high_slope_channel_formula": fda_multiscale_channel_contract(
            HIGH_SLOPE_CHANNEL_SPEC
        ),
        "retired_general_route": "explosive_w12_w24_continuation",
        "retired_route_retained_only_as": (
            "intrinsic_recent_down_first_leg_for_frozen_crash_rebound"
        ),
        "routing_formula": (
            "crash_rebound first; P48->P96 opposite-rail true channel consumes "
            "the strict remainder in both directions"
        ),
        "remainder_field": "remaining_after_explosive_layer",
        "next_layer": "low_slope_ordinary_trend_owner_open",
        "execution_semantics": "closed_bar_decision_visible_on_next_executable_bar",
        "development_period": "2009-2017",
        "repeat_audit_period": "2018-2020",
        "external_validation_period": "2021-2026_frozen_replay_only",
        "runtime_uses_future": False,
        "runtime_uses_registered_events": False,
        "research_authority": True,
        "architecture_lock_authority": True,
        "parameter_authority": False,
        "production_authority": False,
        "v62_runtime_modified": False,
        "field_labels_zh": FIELD_LABELS_ZH,
    }


__all__ = [
    "BUCKET_ORDER",
    "FIELD_LABELS_ZH",
    "HIGH_SLOPE_CHANNEL_BUCKET",
    "HIGH_SLOPE_CHANNEL_SPEC",
    "TIMING_EXPLOSIVE_LAYER_V2_SCHEMA_ID",
    "TIMING_EXPLOSIVE_LAYER_V2_VERSION",
    "build_timing_explosive_layer_v2",
    "timing_explosive_layer_v2_contract",
]
