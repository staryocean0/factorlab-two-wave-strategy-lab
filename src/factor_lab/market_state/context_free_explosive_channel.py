# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportMissingTypeStubs=false, reportOperatorIssue=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Bidirectional, context-free explosive channel for the first route slot.

The downside is the exact independent large-channel lifecycle used by V62.
The upside runs that same causal geometry on reciprocal OHLC prices.  A
reciprocal transform negates log returns while preserving the information set,
so it mirrors direction without inventing a second formula or looking ahead.

Only the independent ``large_channel_*`` outputs are consumed from the V62
builder.  W72, V56, and V60 outputs have no authority in this tool.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict

import numpy as np
import pandas as pd

from factor_lab.market_state.timing_strategy_routing import TimingRouteClaim
from factor_lab.strategy.services.risk_off_v59_crash_rebound_handoff import (
    V59_CRASH_REBOUND_HANDOFF_SPEC,
)
from factor_lab.strategy.services.risk_off_v59_large_channel_parent import (
    V59LargeChannelParentSpec,
    build_v59_large_channel_parent,
)

CONTEXT_FREE_EXPLOSIVE_CHANNEL_SCHEMA_ID = "market_state_context_free_explosive_channel@1.0"
CONTEXT_FREE_EXPLOSIVE_CHANNEL_VERSION = "context_free_explosive_channel_v0"
ROUTE_SLOT_ID = "explosive_context_free_channel"
TOOL_ID = "causal_trendline_channel"
TOOL_PROFILE_ID = "large_scale_high_slope_high_path_efficiency_channel"

FIELD_LABELS_ZH = {
    "timestamp": "K线时间",
    "open": "K线开盘价",
    "high": "K线最高价",
    "low": "K线最低价",
    "close": "K线收盘价",
    "context_free_explosive_down_decision_for_next_bar": "无上下文暴跌本棒决定下一棒生效",
    "context_free_explosive_up_decision_for_next_bar": "无上下文暴涨本棒决定下一棒生效",
    "context_free_explosive_down_executable": "无上下文暴跌当前执行棒生效",
    "context_free_explosive_up_executable": "无上下文暴涨当前执行棒生效",
    "context_free_explosive_direction_conflict_for_next_bar": "无上下文暴涨暴跌同棒原始冲突",
    "context_free_explosive_direction_for_next_bar": "无上下文爆发方向事实",
    "context_free_explosive_route_up_eligible": "第一责任位上涨方向可认领",
    "context_free_explosive_route_down_eligible": "第一责任位下跌方向可认领",
    "context_free_explosive_up_entry_trigger": "无上下文暴涨独立入场触发",
    "context_free_explosive_down_entry_trigger": "无上下文暴跌独立入场触发",
    "context_free_explosive_up_exit_trigger": "无上下文暴涨独立退出触发",
    "context_free_explosive_down_exit_trigger": "无上下文暴跌独立退出触发",
    "context_free_explosive_up_authority_window_bars": "无上下文暴涨当前权威窗口",
    "context_free_explosive_down_authority_window_bars": "无上下文暴跌当前权威窗口",
    "context_free_explosive_up_live_exit_boundary": "无上下文暴涨当前退出边界",
    "context_free_explosive_down_live_exit_boundary": "无上下文暴跌当前退出边界",
    "strategy_version": "策略版本",
    "research_authority": "研究权限",
    "production_authority": "生产权限",
    "runtime_uses_future": "运行时是否使用未来数据",
    "runtime_uses_registered_events": "运行时是否使用注册事件",
}


def _inferred_directional_label_zh(column: str) -> str:
    prefix = "context_free_explosive_"
    if not column.startswith(prefix):
        return FIELD_LABELS_ZH.get(column, f"无上下文通道字段：{column}")
    remainder = column.removeprefix(prefix)
    side, _, suffix = remainder.partition("_")
    side_zh = {"up": "暴涨", "down": "暴跌"}.get(side, "双向")
    replacements = {
        "path_efficiency": "严格历史路径效率",
        "tail_advance_dominance": "单根K线上涨尾部占比",
        "tail_decline_dominance": "单根K线下跌尾部占比",
        "sign_flip_rate": "方向翻转率",
        "fit_r2": "通道回归拟合度",
        "slope_log_per_15m": "15分钟对数斜率",
        "upper_rail": "通道上轨",
        "lower_rail": "通道下轨",
        "fitted_total_up_displacement": "拟合累计上行位移",
        "fitted_total_down_displacement": "拟合累计下行位移",
        "qualified": "是否达标",
        "candidate_trigger": "新候选触发",
        "decision_risk_active_for_next_bar": "本棒决定下一棒生效",
        "executable_risk_active": "当前执行棒生效",
    }
    suffix_zh = suffix
    for token, label in replacements.items():
        if suffix.endswith(token):
            leading = suffix.removesuffix(token).strip("_")
            suffix_zh = f"{leading} {label}" if leading else label
            break
    return f"无上下文{side_zh}{suffix_zh}"


def _complete_field_labels_zh(columns: Iterable[object]) -> dict[str, str]:
    return {
        str(column): FIELD_LABELS_ZH.get(
            str(column),
            _inferred_directional_label_zh(str(column)),
        )
        for column in columns
    }


def _validated_carrier(causal_ohlc: pd.DataFrame) -> pd.DataFrame:
    required = ("timestamp", "open", "high", "low", "close")
    missing = [column for column in required if column not in causal_ohlc]
    if missing:
        raise KeyError(f"context-free explosive channel missing columns: {missing}")
    for flag in ("runtime_uses_future", "runtime_uses_registered_events"):
        if flag in causal_ohlc and bool(causal_ohlc[flag].astype(bool).any()):
            raise ValueError(f"context-free explosive channel declares forbidden {flag}")
    carrier = causal_ohlc.loc[:, required].copy().reset_index(drop=True)
    timestamp = pd.DatetimeIndex(pd.to_datetime(carrier["timestamp"], errors="raise"))
    if timestamp.has_duplicates or not timestamp.is_monotonic_increasing:
        raise ValueError("context-free explosive channel timestamps must be ordered and unique")
    for column in required[1:]:
        values = pd.to_numeric(carrier[column], errors="raise").to_numpy(float)
        if not np.isfinite(values).all() or bool((values <= 0.0).any()):
            raise ValueError(f"context-free explosive channel {column} must be finite and positive")
        carrier[column] = values
    invalid_bar = (carrier["low"] > carrier["high"]) | (
        carrier["open"].lt(carrier["low"])
        | carrier["open"].gt(carrier["high"])
        | carrier["close"].lt(carrier["low"])
        | carrier["close"].gt(carrier["high"])
    )
    if bool(invalid_bar.any()):
        raise ValueError("context-free explosive channel received invalid OHLC bars")
    return carrier


def _reciprocal_ohlc(carrier: pd.DataFrame) -> pd.DataFrame:
    """Return the exact positive-price mirror while preserving OHLC ordering."""

    mirrored = carrier.copy()
    mirrored["open"] = 1.0 / carrier["open"].to_numpy(float)
    mirrored["close"] = 1.0 / carrier["close"].to_numpy(float)
    mirrored["high"] = 1.0 / carrier["low"].to_numpy(float)
    mirrored["low"] = 1.0 / carrier["high"].to_numpy(float)
    return mirrored


def _neutral_execution_shift(decision: np.ndarray) -> np.ndarray:
    executable = np.zeros(len(decision), dtype=bool)
    if len(decision) > 1:
        executable[1:] = decision[:-1]
    return executable


def build_context_free_explosive_channel(
    causal_ohlc: pd.DataFrame,
    spec: V59LargeChannelParentSpec = V59_CRASH_REBOUND_HANDOFF_SPEC,
) -> pd.DataFrame:
    """Build symmetric up/down signals without any directional context input."""

    carrier = _validated_carrier(causal_ohlc)
    down = build_v59_large_channel_parent(carrier, spec)
    mirrored = _reciprocal_ohlc(carrier)
    mirrored_down = build_v59_large_channel_parent(mirrored, spec)

    down_decision = down["large_channel_decision_risk_active_for_next_bar"].to_numpy(bool)
    up_decision = mirrored_down["large_channel_decision_risk_active_for_next_bar"].to_numpy(bool)
    conflict = down_decision & up_decision
    route_down = down_decision & ~conflict
    route_up = up_decision & ~conflict

    direction = np.full(len(carrier), "none", dtype=object)
    direction[route_down] = "down"
    direction[route_up] = "up"
    direction[conflict] = "conflict"

    directional_columns: dict[str, np.ndarray] = {}
    for side, source in (("down", down), ("up", mirrored_down)):
        source_prefix = "large_channel_"
        target_prefix = f"context_free_explosive_{side}_"
        for column in source.columns:
            if not column.startswith(source_prefix):
                continue
            suffix = column.removeprefix(source_prefix)
            values = source[column].copy()
            if side == "up":
                if suffix.endswith("_upper_rail"):
                    suffix = suffix.removesuffix("_upper_rail") + "_lower_rail"
                    values = 1.0 / pd.to_numeric(values, errors="coerce")
                elif suffix.endswith("_lower_rail"):
                    suffix = suffix.removesuffix("_lower_rail") + "_upper_rail"
                    values = 1.0 / pd.to_numeric(values, errors="coerce")
                elif suffix in {
                    "live_exit_boundary",
                    "rebound_watch_floor",
                    "rebound_watch_success_boundary",
                }:
                    values = 1.0 / pd.to_numeric(values, errors="coerce")
                elif suffix.endswith("_slope_log_per_15m"):
                    values = -pd.to_numeric(values, errors="coerce")
                elif suffix.endswith("_fitted_total_down_displacement"):
                    suffix = suffix.replace(
                        "_fitted_total_down_displacement",
                        "_fitted_total_up_displacement",
                    )
                suffix = suffix.replace("tail_decline_dominance", "tail_advance_dominance")
            directional_columns[f"{target_prefix}{suffix}"] = values.to_numpy()

    directional_columns.update(
        {
            "context_free_explosive_down_decision_for_next_bar": down_decision,
            "context_free_explosive_up_decision_for_next_bar": up_decision,
            "context_free_explosive_direction_conflict_for_next_bar": conflict,
            "context_free_explosive_direction_for_next_bar": direction,
            "context_free_explosive_route_down_eligible": route_down,
            "context_free_explosive_route_up_eligible": route_up,
            "context_free_explosive_down_executable": _neutral_execution_shift(route_down),
            "context_free_explosive_up_executable": _neutral_execution_shift(route_up),
            "strategy_version": np.full(len(carrier), CONTEXT_FREE_EXPLOSIVE_CHANNEL_VERSION, dtype=object),
            "research_authority": np.ones(len(carrier), dtype=bool),
            "production_authority": np.zeros(len(carrier), dtype=bool),
            "runtime_uses_future": np.zeros(len(carrier), dtype=bool),
            "runtime_uses_registered_events": np.zeros(len(carrier), dtype=bool),
        }
    )
    output = pd.concat(
        [carrier, pd.DataFrame(directional_columns, index=carrier.index)],
        axis=1,
    )
    output.attrs["field_labels_zh"] = _complete_field_labels_zh(output.columns)
    output.attrs["formula_contract"] = context_free_explosive_channel_contract(spec)
    return output


def context_free_explosive_channel_claims(
    frame: pd.DataFrame,
) -> tuple[TimingRouteClaim, TimingRouteClaim]:
    """Adapt the tool output to the first slot of the shared timing router."""

    required = {
        "context_free_explosive_route_up_eligible",
        "context_free_explosive_route_down_eligible",
    }
    missing = sorted(required.difference(frame))
    if missing:
        raise KeyError(f"context-free explosive channel claims missing columns: {missing}")
    return (
        TimingRouteClaim(
            slot_id=ROUTE_SLOT_ID,
            direction_id="up",
            tool_id=TOOL_ID,
            tool_profile_id=TOOL_PROFILE_ID,
            state_id="context_free_explosive_up",
            eligible=frame["context_free_explosive_route_up_eligible"].astype(bool),
        ),
        TimingRouteClaim(
            slot_id=ROUTE_SLOT_ID,
            direction_id="down",
            tool_id=TOOL_ID,
            tool_profile_id=TOOL_PROFILE_ID,
            state_id="context_free_explosive_down",
            eligible=frame["context_free_explosive_route_down_eligible"].astype(bool),
        ),
    )


def context_free_explosive_channel_contract(
    spec: V59LargeChannelParentSpec = V59_CRASH_REBOUND_HANDOFF_SPEC,
) -> dict[str, object]:
    """Expose the low-freedom formula, routing, and authority contract."""

    return {
        "schema_id": CONTEXT_FREE_EXPLOSIVE_CHANNEL_SCHEMA_ID,
        "strategy_version": CONTEXT_FREE_EXPLOSIVE_CHANNEL_VERSION,
        "route_slot_id": ROUTE_SLOT_ID,
        "tool_id": TOOL_ID,
        "tool_profile_id": TOOL_PROFILE_ID,
        "spec": asdict(spec),
        "directional_formula": {
            "down": "V62 independent large-channel lifecycle on prior-only OHLC",
            "up": "the same lifecycle on reciprocal OHLC: O'=1/O, H'=1/L, L'=1/H, C'=1/C",
            "economic_value": "measured independently on original-market forward returns; never inferred by sign inversion",
        },
        "context_contract": {
            "required_context": False,
            "consumed_inputs": ["timestamp", "open", "high", "low", "close"],
            "w72_v56_v60_authority": False,
        },
        "conflict_contract": {
            "same_bar_up_down_priority": None,
            "conflict_is_explicit": True,
            "conflict_claimed_by_first_slot": False,
            "conflict_falls_through_to_lower_route": True,
        },
        "execution_semantics": "close_t_decision_open_t_plus_1",
        "runtime_uses_future": False,
        "runtime_uses_registered_events": False,
        "field_labels_zh": FIELD_LABELS_ZH,
        "dynamic_field_label_contract": ("every materialized output column receives a Chinese label in DataFrame.attrs"),
        "authority": {
            "research_authority": True,
            "architecture_lock_authority": False,
            "tool_routing_authority": False,
            "parameter_authority": False,
            "production_authority": False,
            "sealed_2021_plus_authority": False,
        },
    }


__all__ = [
    "CONTEXT_FREE_EXPLOSIVE_CHANNEL_SCHEMA_ID",
    "CONTEXT_FREE_EXPLOSIVE_CHANNEL_VERSION",
    "FIELD_LABELS_ZH",
    "ROUTE_SLOT_ID",
    "TOOL_ID",
    "TOOL_PROFILE_ID",
    "build_context_free_explosive_channel",
    "context_free_explosive_channel_claims",
    "context_free_explosive_channel_contract",
]
