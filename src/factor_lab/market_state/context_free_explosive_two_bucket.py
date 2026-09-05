# pyright: reportAny=false, reportArgumentType=false, reportAssignmentType=false
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
# pyright: reportCallInDefaultInitializer=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportOperatorIssue=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Context-free explosive two-bucket research lineage.

V0 tested a symmetric sharp-reversal bridge and retained its failed
spike-reversal evidence. Frozen V1 removes that route and keeps two
independently calculated responsibilities:

1. an upward crash-rebound bridge; and
2. bidirectional W12/W24 continuation channels on the strict remainder.

"Context-free" means that no external market-regime classifier authorizes an
entry. The crash rebound still contains its intrinsic first leg: a recently
completed W12/W24 down channel. Both tools are calculated before routing, so
handoff cannot create a signal gap.
"""

from __future__ import annotations

from dataclasses import asdict

import numpy as np
import pandas as pd

from factor_lab.market_state.context_free_explosive_channel import (
    build_context_free_explosive_channel,
    context_free_explosive_channel_contract,
)
from factor_lab.market_state.recent_down_rebound_bridge import (
    RecentDownReboundBridgeSpec,
    build_recent_down_rebound_bridge,
)
from factor_lab.market_state.tool_benchmark_adapters import run_tool_benchmark
from factor_lab.market_state.tool_registry import tool_benchmark_specs

CONTEXT_FREE_EXPLOSIVE_TWO_BUCKET_SCHEMA_ID = "market_state_context_free_explosive_two_bucket@1.0"
CONTEXT_FREE_EXPLOSIVE_TWO_BUCKET_VERSION = "context_free_explosive_two_bucket_v0"
CONTEXT_FREE_EXPLOSIVE_TWO_BUCKET_V1_SCHEMA_ID = "market_state_context_free_explosive_two_bucket@1.1"
CONTEXT_FREE_EXPLOSIVE_TWO_BUCKET_V1_VERSION = "context_free_explosive_crash_rebound_channel_v1"
REVERSAL_BUCKET = "explosive_sharp_reversal"
CRASH_REBOUND_BUCKET = "explosive_crash_rebound"
CHANNEL_BUCKET = "explosive_w12_w24_continuation"
BUCKET_ORDER = (REVERSAL_BUCKET, CHANNEL_BUCKET)
BUCKET_ORDER_V1 = (CRASH_REBOUND_BUCKET, CHANNEL_BUCKET)
ARC_TOOL_ID = "causal_asymmetric_arc_state_space_envelope"

FIELD_LABELS_ZH = {
    "timestamp": "K线时间",
    "open": "K线开盘价",
    "high": "K线最高价",
    "low": "K线最低价",
    "close": "K线收盘价",
    "reversal_up_raw": "无外部背景暴跌反弹原始信号",
    "reversal_down_raw": "无外部背景冲高回落原始信号",
    "reversal_direction_conflict": "双向反转信号冲突",
    "reversal_up_executable": "暴跌反弹当前执行棒生效",
    "reversal_down_executable": "冲高回落当前执行棒生效",
    "channel_up_raw": "无背景W12/W24上涨通道原始信号",
    "channel_down_raw": "无背景W12/W24下跌通道原始信号",
    "channel_up_executable": "反转余集W12/W24上涨通道",
    "channel_down_executable": "反转余集W12/W24下跌通道",
    "reversal_to_channel_up_handoff": "暴跌反弹向上涨通道无缝交接",
    "reversal_to_channel_down_handoff": "冲高回落向下跌通道无缝交接",
    "explosive_route_slot_id": "爆发层责任桶",
    "explosive_route_direction_id": "爆发层方向",
    "explosive_route_claimed": "爆发层是否认领",
    "remaining_after_explosive_layer": "爆发层后剩余K线",
    "explosive_route_position_long_short": "爆发层多空仓位",
    "strategy_version": "策略版本",
    "runtime_uses_future": "运行时是否使用未来数据",
    "runtime_uses_registered_events": "运行时是否使用事后注册事件",
    "research_authority": "研究权限",
    "production_authority": "生产权限",
    "crash_rebound_raw": "无外部背景暴跌反弹原始信号",
    "crash_rebound_executable": "暴跌反弹当前执行棒生效",
    "crash_rebound_to_channel_up_handoff": "暴跌反弹向上涨通道无缝交接",
    "crash_rebound_to_channel_down_handoff": "暴跌反弹失败后向下跌通道无缝交接",
}


def _validated_index(causal_ohlc: pd.DataFrame) -> pd.DatetimeIndex:
    required = {"timestamp", "open", "high", "low", "close"}
    missing = sorted(required.difference(causal_ohlc))
    if missing:
        raise KeyError(f"two-bucket explosive layer missing OHLC columns: {missing}")
    index = pd.DatetimeIndex(pd.to_datetime(causal_ohlc["timestamp"], errors="raise"))
    if index.empty or index.has_duplicates or not index.is_monotonic_increasing:
        raise ValueError("two-bucket explosive layer requires ordered unique timestamps")
    return index


def _reciprocal_ohlc(causal_ohlc: pd.DataFrame) -> pd.DataFrame:
    mirrored = causal_ohlc.loc[:, ["timestamp", "open", "high", "low", "close"]].copy()
    mirrored["open"] = 1.0 / pd.to_numeric(causal_ohlc["open"], errors="raise")
    mirrored["close"] = 1.0 / pd.to_numeric(causal_ohlc["close"], errors="raise")
    mirrored["high"] = 1.0 / pd.to_numeric(causal_ohlc["low"], errors="raise")
    mirrored["low"] = 1.0 / pd.to_numeric(causal_ohlc["high"], errors="raise")
    mirrored["runtime_uses_future"] = False
    mirrored["runtime_uses_registered_events"] = False
    return mirrored


def _registered_arc_position(
    causal_ohlc: pd.DataFrame,
    index: pd.DatetimeIndex,
) -> pd.Series:
    specs = [spec for spec in tool_benchmark_specs() if spec.tool_id == ARC_TOOL_ID]
    if len(specs) != 1:
        raise RuntimeError("registered asymmetric-arc benchmark is missing or ambiguous")
    panel = run_tool_benchmark(causal_ohlc, specs[0], frequency="15m")
    decisions = pd.DataFrame(
        {
            "decision_time": pd.to_datetime(panel["decision_time"], errors="raise"),
            "target_position": pd.to_numeric(panel["target_position"], errors="raise"),
        }
    ).sort_values("decision_time")
    aligned = pd.merge_asof(
        pd.DataFrame({"timestamp": index}),
        decisions,
        left_on="timestamp",
        right_on="decision_time",
        direction="backward",
        allow_exact_matches=False,
    )
    return pd.Series(
        aligned["target_position"].fillna(0.0).clip(0.0, 1.0).to_numpy(float),
        index=index,
    )


def compose_context_free_explosive_two_bucket(
    index: pd.Index,
    *,
    reversal_up_raw: pd.Series,
    reversal_down_raw: pd.Series,
    channel_up_raw: pd.Series,
    channel_down_raw: pd.Series,
) -> pd.DataFrame:
    """Assign reversal first and continuation second without hiding conflicts."""

    masks = {
        "reversal_up_raw": reversal_up_raw,
        "reversal_down_raw": reversal_down_raw,
        "channel_up_raw": channel_up_raw,
        "channel_down_raw": channel_down_raw,
    }
    for name, mask in masks.items():
        if not mask.index.equals(index):
            raise ValueError(f"{name} does not share the two-bucket index")
        if mask.isna().any() or not pd.api.types.is_bool_dtype(mask.dtype):
            raise ValueError(f"{name} must be a complete boolean series")
    if bool((channel_up_raw & channel_down_raw).any()):
        raise RuntimeError("raw W12/W24 continuation directions overlap")

    reversal_conflict = reversal_up_raw & reversal_down_raw
    reversal_up = reversal_up_raw & ~reversal_conflict
    reversal_down = reversal_down_raw & ~reversal_conflict
    reversal_claimed = reversal_up | reversal_down
    channel_up = channel_up_raw & ~reversal_claimed
    channel_down = channel_down_raw & ~reversal_claimed

    owner_count = reversal_up.astype(int) + reversal_down.astype(int) + channel_up.astype(int) + channel_down.astype(int)
    if bool(owner_count.gt(1).any()):
        raise RuntimeError("two-bucket explosive route ownership overlaps")

    slot = np.full(len(index), "unassigned", dtype=object)
    direction = np.full(len(index), "unassigned", dtype=object)
    for mask, bucket, side in (
        (reversal_up, REVERSAL_BUCKET, "up"),
        (reversal_down, REVERSAL_BUCKET, "down"),
        (channel_up, CHANNEL_BUCKET, "up"),
        (channel_down, CHANNEL_BUCKET, "down"),
    ):
        values = mask.to_numpy(bool)
        slot[values] = bucket
        direction[values] = side

    prior_reversal_up = reversal_up.shift(1, fill_value=False)
    prior_reversal_down = reversal_down.shift(1, fill_value=False)
    claimed = owner_count.gt(0)
    return pd.DataFrame(
        {
            "reversal_up_raw": reversal_up_raw,
            "reversal_down_raw": reversal_down_raw,
            "reversal_direction_conflict": reversal_conflict,
            "reversal_up_executable": reversal_up,
            "reversal_down_executable": reversal_down,
            "channel_up_raw": channel_up_raw,
            "channel_down_raw": channel_down_raw,
            "channel_up_executable": channel_up,
            "channel_down_executable": channel_down,
            "reversal_to_channel_up_handoff": prior_reversal_up & channel_up,
            "reversal_to_channel_down_handoff": prior_reversal_down & channel_down,
            "explosive_route_slot_id": slot,
            "explosive_route_direction_id": direction,
            "explosive_route_claimed": claimed,
            "remaining_after_explosive_layer": ~claimed,
            "explosive_route_position_long_short": (
                reversal_up.astype(float) - reversal_down.astype(float) + channel_up.astype(float) - channel_down.astype(float)
            ),
            "strategy_version": CONTEXT_FREE_EXPLOSIVE_TWO_BUCKET_VERSION,
            "runtime_uses_future": False,
            "runtime_uses_registered_events": False,
            "research_authority": True,
            "production_authority": False,
        },
        index=index,
    )


def build_context_free_explosive_two_bucket(
    causal_ohlc: pd.DataFrame,
    reversal_spec: RecentDownReboundBridgeSpec = RecentDownReboundBridgeSpec(),
) -> pd.DataFrame:
    """Build the symmetric reversal-first, continuation-second V0 prototype."""

    index = _validated_index(causal_ohlc)
    channel = build_context_free_explosive_channel(causal_ohlc)
    channel_up = pd.Series(channel["context_free_explosive_up_executable"].to_numpy(bool), index=index)
    channel_down = pd.Series(channel["context_free_explosive_down_executable"].to_numpy(bool), index=index)
    close = pd.Series(
        pd.to_numeric(causal_ohlc["close"], errors="raise").to_numpy(float),
        index=index,
    )
    arc_up = _registered_arc_position(causal_ohlc, index)
    empty_preemption = pd.Series(False, index=index)
    up_bridge = build_recent_down_rebound_bridge(
        close=close,
        rebound_parent=arc_up.gt(0.5),
        rebound_candidate_position=arc_up,
        down_channel_context=channel_down,
        context_free_up_channel=empty_preemption,
        spec=reversal_spec,
    )

    mirrored = _reciprocal_ohlc(causal_ohlc)
    reciprocal_close = pd.Series(
        pd.to_numeric(mirrored["close"], errors="raise").to_numpy(float),
        index=index,
    )
    arc_down = _registered_arc_position(mirrored, index)
    down_bridge = build_recent_down_rebound_bridge(
        close=reciprocal_close,
        rebound_parent=arc_down.gt(0.5),
        rebound_candidate_position=arc_down,
        down_channel_context=channel_up,
        context_free_up_channel=empty_preemption,
        spec=reversal_spec,
    )

    output = compose_context_free_explosive_two_bucket(
        index,
        reversal_up_raw=up_bridge["recent_down_rebound_bridge_position"].astype(bool),
        reversal_down_raw=down_bridge["recent_down_rebound_bridge_position"].astype(bool),
        channel_up_raw=channel_up,
        channel_down_raw=channel_down,
    )
    output.attrs["field_labels_zh"] = {column: FIELD_LABELS_ZH.get(column, f"无背景爆发双桶字段：{column}") for column in output.columns}
    output.attrs["formula_contract"] = context_free_explosive_two_bucket_contract(reversal_spec)
    return output


def context_free_explosive_two_bucket_contract(
    reversal_spec: RecentDownReboundBridgeSpec = RecentDownReboundBridgeSpec(),
) -> dict[str, object]:
    """Return the V0 formula, routing, and research-authority contract."""

    return {
        "schema_id": CONTEXT_FREE_EXPLOSIVE_TWO_BUCKET_SCHEMA_ID,
        "strategy_version": CONTEXT_FREE_EXPLOSIVE_TWO_BUCKET_VERSION,
        "bucket_order": list(BUCKET_ORDER),
        "active_directions": {
            REVERSAL_BUCKET: ["up", "down"],
            CHANNEL_BUCKET: ["up", "down"],
        },
        "external_context_gate": None,
        "s20_context_used": False,
        "context_conditioned_channel_used": False,
        "reversal_formula": {
            "up": "registered causal arc turns up after a recent completed raw W12/W24 down channel",
            "down": "exact reciprocal-price mirror of the up formula",
            "intrinsic_first_leg": "recent opposite raw W12/W24 channel only",
            "spec": asdict(reversal_spec),
        },
        "continuation_formula": context_free_explosive_channel_contract(),
        "routing_formula": "sharp_reversal first; raw W12/W24 continuation consumes exact remainder",
        "same_direction_handoff": "both tools run in shadow; channel may own the first bar after reversal release without re-entry",
        "opposite_direction_conflict": "sharp reversal owns; dual-reversal ambiguity fails closed",
        "execution_semantics": "closed-bar decision visible on next executable bar",
        "development_period": "2009-2017",
        "repeat_audit_period": "2018-2020",
        "sealed_period": "2021-2026",
        "runtime_uses_future": False,
        "runtime_uses_registered_events": False,
        "research_authority": True,
        "architecture_lock_authority": False,
        "parameter_authority": False,
        "production_authority": False,
        "field_labels_zh": FIELD_LABELS_ZH,
    }


def compose_context_free_explosive_two_bucket_v1(
    index: pd.Index,
    *,
    crash_rebound_raw: pd.Series,
    channel_up_raw: pd.Series,
    channel_down_raw: pd.Series,
) -> pd.DataFrame:
    """Assign crash rebound first and both continuation directions second."""

    masks = {
        "crash_rebound_raw": crash_rebound_raw,
        "channel_up_raw": channel_up_raw,
        "channel_down_raw": channel_down_raw,
    }
    for name, mask in masks.items():
        if not mask.index.equals(index):
            raise ValueError(f"{name} does not share the V1 two-bucket index")
        if mask.isna().any() or not pd.api.types.is_bool_dtype(mask.dtype):
            raise ValueError(f"{name} must be a complete boolean series")
    if bool((channel_up_raw & channel_down_raw).any()):
        raise RuntimeError("raw W12/W24 continuation directions overlap")

    crash_rebound = crash_rebound_raw
    channel_up = channel_up_raw & ~crash_rebound
    channel_down = channel_down_raw & ~crash_rebound
    owner_count = crash_rebound.astype(int) + channel_up.astype(int) + channel_down.astype(int)
    if bool(owner_count.gt(1).any()):
        raise RuntimeError("V1 two-bucket explosive route ownership overlaps")

    slot = np.full(len(index), "unassigned", dtype=object)
    direction = np.full(len(index), "unassigned", dtype=object)
    for mask, bucket, side in (
        (crash_rebound, CRASH_REBOUND_BUCKET, "up"),
        (channel_up, CHANNEL_BUCKET, "up"),
        (channel_down, CHANNEL_BUCKET, "down"),
    ):
        values = mask.to_numpy(bool)
        slot[values] = bucket
        direction[values] = side

    prior_rebound = crash_rebound.shift(1, fill_value=False)
    claimed = owner_count.gt(0)
    return pd.DataFrame(
        {
            "crash_rebound_raw": crash_rebound_raw,
            "crash_rebound_executable": crash_rebound,
            "channel_up_raw": channel_up_raw,
            "channel_down_raw": channel_down_raw,
            "channel_up_executable": channel_up,
            "channel_down_executable": channel_down,
            "crash_rebound_to_channel_up_handoff": prior_rebound & channel_up,
            "crash_rebound_to_channel_down_handoff": prior_rebound & channel_down,
            "explosive_route_slot_id": slot,
            "explosive_route_direction_id": direction,
            "explosive_route_claimed": claimed,
            "remaining_after_explosive_layer": ~claimed,
            "explosive_route_position_long_short": (crash_rebound.astype(float) + channel_up.astype(float) - channel_down.astype(float)),
            "strategy_version": CONTEXT_FREE_EXPLOSIVE_TWO_BUCKET_V1_VERSION,
            "runtime_uses_future": False,
            "runtime_uses_registered_events": False,
            "research_authority": True,
            "production_authority": False,
        },
        index=index,
    )


def build_context_free_explosive_two_bucket_v1(
    causal_ohlc: pd.DataFrame,
    reversal_spec: RecentDownReboundBridgeSpec = RecentDownReboundBridgeSpec(),
) -> pd.DataFrame:
    """Build the frozen crash-rebound-first, bidirectional-channel V1."""

    index = _validated_index(causal_ohlc)
    channel = build_context_free_explosive_channel(causal_ohlc)
    channel_up = pd.Series(channel["context_free_explosive_up_executable"].to_numpy(bool), index=index)
    channel_down = pd.Series(channel["context_free_explosive_down_executable"].to_numpy(bool), index=index)
    close = pd.Series(
        pd.to_numeric(causal_ohlc["close"], errors="raise").to_numpy(float),
        index=index,
    )
    arc_up = _registered_arc_position(causal_ohlc, index)
    empty_preemption = pd.Series(False, index=index)
    up_bridge = build_recent_down_rebound_bridge(
        close=close,
        rebound_parent=arc_up.gt(0.5),
        rebound_candidate_position=arc_up,
        down_channel_context=channel_down,
        context_free_up_channel=empty_preemption,
        spec=reversal_spec,
    )
    output = compose_context_free_explosive_two_bucket_v1(
        index,
        crash_rebound_raw=up_bridge["recent_down_rebound_bridge_position"].astype(bool),
        channel_up_raw=channel_up,
        channel_down_raw=channel_down,
    )
    output.attrs["field_labels_zh"] = {column: FIELD_LABELS_ZH.get(column, f"无背景爆发双桶V1字段：{column}") for column in output.columns}
    output.attrs["formula_contract"] = context_free_explosive_two_bucket_v1_contract(reversal_spec)
    return output


def context_free_explosive_two_bucket_v1_contract(
    reversal_spec: RecentDownReboundBridgeSpec = RecentDownReboundBridgeSpec(),
) -> dict[str, object]:
    """Return the architecture-locked V1 research contract."""

    return {
        "schema_id": CONTEXT_FREE_EXPLOSIVE_TWO_BUCKET_V1_SCHEMA_ID,
        "strategy_version": CONTEXT_FREE_EXPLOSIVE_TWO_BUCKET_V1_VERSION,
        "supersedes_research_version": CONTEXT_FREE_EXPLOSIVE_TWO_BUCKET_VERSION,
        "bucket_order": list(BUCKET_ORDER_V1),
        "active_directions": {
            CRASH_REBOUND_BUCKET: ["up"],
            CHANNEL_BUCKET: ["up", "down"],
        },
        "retired_route": "spike_reversal_down",
        "retirement_reason": "repeat-audit profit factor 0.73 and short false-turn concentration",
        "external_context_gate": None,
        "s20_context_used": False,
        "crash_rebound_formula": {
            "entry": "registered causal arc turns up after a recent completed raw W12/W24 down channel",
            "intrinsic_first_leg": "recent raw W12/W24 down channel only",
            "spec": asdict(reversal_spec),
        },
        "continuation_formula": context_free_explosive_channel_contract(),
        "routing_formula": "crash rebound first; raw bidirectional W12/W24 continuation consumes exact remainder",
        "same_direction_handoff": "both tools run in shadow; either channel direction may own the first bar after rebound release",
        "execution_semantics": "closed-bar decision visible on next executable bar",
        "development_period": "2009-2017",
        "repeat_audit_period": "2018-2020",
        "sealed_period": "2021-2026",
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
    "ARC_TOOL_ID",
    "BUCKET_ORDER",
    "CHANNEL_BUCKET",
    "CRASH_REBOUND_BUCKET",
    "CONTEXT_FREE_EXPLOSIVE_TWO_BUCKET_SCHEMA_ID",
    "CONTEXT_FREE_EXPLOSIVE_TWO_BUCKET_VERSION",
    "CONTEXT_FREE_EXPLOSIVE_TWO_BUCKET_V1_SCHEMA_ID",
    "CONTEXT_FREE_EXPLOSIVE_TWO_BUCKET_V1_VERSION",
    "FIELD_LABELS_ZH",
    "REVERSAL_BUCKET",
    "BUCKET_ORDER_V1",
    "build_context_free_explosive_two_bucket",
    "build_context_free_explosive_two_bucket_v1",
    "compose_context_free_explosive_two_bucket",
    "compose_context_free_explosive_two_bucket_v1",
    "context_free_explosive_two_bucket_contract",
    "context_free_explosive_two_bucket_v1_contract",
]
