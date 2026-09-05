"""Simultaneous multiscale authority channel with channel-native slope exits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from factor_lab.market_state.fda_explosive_channel_prototype import (
    PERIOD_BARS,
    FDAExplosiveChannelSpec,
    _channel_spec,
    _rolling_endpoint_derivatives,
)
from factor_lab.strategy.services.risk_off_v58_frequency_bollinger import (
    build_frequency_bollinger,
)

ExitMode = Literal["opposite_rail", "middle_velocity_turn", "middle_slowdown"]
EXIT_MODES: tuple[ExitMode, ...] = (
    "opposite_rail",
    "middle_velocity_turn",
    "middle_slowdown",
)
SLOWDOWN_NORMALIZED_SPEED = 1.0

FIELD_LABELS_ZH = {
    "decision_position_for_next_bar": "本棒决定下一棒的多空仓位",
    "executable_position": "当前执行棒多空仓位",
    "decision_authority_period_bars": "本棒权威通道周期",
    "executable_authority_period_bars": "当前执行棒权威通道周期",
    "entry_trigger_direction": "入场触发方向",
    "entry_trigger_period_bars": "入场触发通道周期",
    "promotion_trigger": "权威尺度是否向上晋升",
    "exit_trigger": "是否触发退出",
    "exit_reason": "退出原因",
    "cross_scale_entry_conflict": "跨尺度入场方向冲突",
    "exit_mode": "退出机制",
    "runtime_uses_future": "运行时是否使用未来数据",
    "runtime_uses_registered_events": "运行时是否使用事后注册事件",
    "research_authority": "研究权限",
    "production_authority": "生产权限",
}


@dataclass(frozen=True, slots=True)
class FDAMultiscaleChannelSpec:
    """One exit member over an explicitly bounded authority-scale ladder."""

    exit_mode: ExitMode
    period_bars: tuple[int, ...] = PERIOD_BARS

    def __post_init__(self) -> None:
        if self.exit_mode not in EXIT_MODES:
            raise ValueError(f"exit_mode must be one of {EXIT_MODES}")
        if not self.period_bars:
            raise ValueError("period_bars must not be empty")
        if tuple(sorted(set(self.period_bars))) != self.period_bars:
            raise ValueError("period_bars must be strictly increasing and unique")
        if not set(self.period_bars).issubset(PERIOD_BARS):
            raise ValueError(f"period_bars must be drawn from {PERIOD_BARS}")

    @property
    def ladder_id(self) -> str:
        return "_".join(f"p{period}" for period in self.period_bars)

    @property
    def candidate_id(self) -> str:
        return f"fda_multiscale_{self.ladder_id}_{self.exit_mode}"


def _scale_frames(
    close: pd.Series,
    period_bars: tuple[int, ...],
) -> dict[int, pd.DataFrame]:
    frames: dict[int, pd.DataFrame] = {}
    for period in period_bars:
        base_spec = FDAExplosiveChannelSpec(period, "opposite_rail")
        channel = build_frequency_bollinger(close, _channel_spec(base_spec))
        entry_velocity, entry_acceleration = _rolling_endpoint_derivatives(
            channel["log_close"],
            base_spec.derivative_window_bars,
        )
        middle_velocity, middle_acceleration = _rolling_endpoint_derivatives(
            channel["middle_log"],
            base_spec.derivative_window_bars,
        )
        valid = (
            channel["valid"].astype(bool)
            & entry_velocity.notna()
            & entry_acceleration.notna()
            & middle_velocity.notna()
            & middle_acceleration.notna()
        )
        entry_up = (
            valid
            & entry_velocity.gt(0.0)
            & entry_acceleration.gt(0.0)
            & channel["log_close"].gt(channel["upper_log"])
        )
        entry_down = (
            valid
            & entry_velocity.lt(0.0)
            & entry_acceleration.lt(0.0)
            & channel["log_close"].lt(channel["lower_log"])
        )
        frames[period] = channel.assign(
            entry_velocity_log_per_bar=entry_velocity,
            entry_acceleration_log_per_bar2=entry_acceleration,
            middle_velocity_log_per_bar=middle_velocity,
            middle_acceleration_log_per_bar2=middle_acceleration,
            normalized_middle_speed=(
                middle_velocity.abs() * float(period) / channel["width_log"]
            ),
            entry_up=entry_up,
            entry_down=entry_down,
            fresh_entry_up=(entry_up & ~entry_up.shift(1, fill_value=False)),
            fresh_entry_down=(entry_down & ~entry_down.shift(1, fill_value=False)),
            valid_multiscale=valid,
        )
    return frames


def _should_exit(
    *,
    frame: pd.DataFrame,
    location: int,
    direction: int,
    mode: ExitMode,
) -> bool:
    close = float(frame.iloc[location]["log_close"])
    middle_velocity = float(frame.iloc[location]["middle_velocity_log_per_bar"])
    middle_acceleration = float(frame.iloc[location]["middle_acceleration_log_per_bar2"])
    normalized_speed = float(frame.iloc[location]["normalized_middle_speed"])
    if mode == "opposite_rail":
        boundary = float(
            frame.iloc[location]["lower_log" if direction == 1 else "upper_log"]
        )
        return close < boundary if direction == 1 else close > boundary
    if mode == "middle_velocity_turn":
        return middle_velocity <= 0.0 if direction == 1 else middle_velocity >= 0.0
    decelerating = middle_acceleration < 0.0 if direction == 1 else middle_acceleration > 0.0
    still_directional_or_turned = middle_velocity >= 0.0 if direction == 1 else middle_velocity <= 0.0
    return bool(
        decelerating
        and still_directional_or_turned
        and normalized_speed <= SLOWDOWN_NORMALIZED_SPEED
    )


def build_fda_multiscale_channel(
    close: pd.Series,
    spec: FDAMultiscaleChannelSpec,
) -> pd.DataFrame:
    """Run four channels in shadow and expose one monotone authority scale."""

    numeric = pd.to_numeric(close, errors="raise").astype(float)
    if numeric.empty or numeric.isna().any() or numeric.le(0.0).any():
        raise ValueError("close must be non-empty, finite, and positive")
    if numeric.index.has_duplicates or not numeric.index.is_monotonic_increasing:
        raise ValueError("close index must be ordered and unique")
    frames = _scale_frames(numeric, spec.period_bars)
    row_count = len(numeric)
    decision = np.zeros(row_count, dtype=np.int8)
    authority = np.zeros(row_count, dtype=np.int16)
    entry_direction = np.zeros(row_count, dtype=np.int8)
    entry_period = np.zeros(row_count, dtype=np.int16)
    promotion = np.zeros(row_count, dtype=bool)
    exit_trigger = np.zeros(row_count, dtype=bool)
    exit_reason = np.full(row_count, "none", dtype=object)
    conflict = np.zeros(row_count, dtype=bool)
    holding = 0
    authority_period = 0

    for location in range(row_count):
        up_scales = [
            period
            for period, frame in frames.items()
            if bool(frame.iloc[location]["fresh_entry_up"])
        ]
        down_scales = [
            period
            for period, frame in frames.items()
            if bool(frame.iloc[location]["fresh_entry_down"])
        ]
        if up_scales and down_scales:
            conflict[location] = True

        if holding == 0:
            up_period = max(up_scales, default=0)
            down_period = max(down_scales, default=0)
            if up_period > down_period:
                holding = 1
                authority_period = up_period
            elif down_period > up_period:
                holding = -1
                authority_period = down_period
            if holding != 0:
                entry_direction[location] = holding
                entry_period[location] = authority_period
        else:
            same_direction_scales = up_scales if holding == 1 else down_scales
            higher = [period for period in same_direction_scales if period > authority_period]
            if higher:
                authority_period = max(higher)
                promotion[location] = True
            authority_frame = frames[authority_period]
            if _should_exit(
                frame=authority_frame,
                location=location,
                direction=holding,
                mode=spec.exit_mode,
            ):
                holding = 0
                authority_period = 0
                exit_trigger[location] = True
                exit_reason[location] = spec.exit_mode

        decision[location] = holding
        authority[location] = authority_period

    executable = np.zeros(row_count, dtype=np.int8)
    executable_authority = np.zeros(row_count, dtype=np.int16)
    if row_count > 1:
        executable[1:] = decision[:-1]
        executable_authority[1:] = authority[:-1]

    columns: dict[str, object] = {
        "decision_position_for_next_bar": decision,
        "executable_position": executable,
        "decision_authority_period_bars": authority,
        "executable_authority_period_bars": executable_authority,
        "entry_trigger_direction": entry_direction,
        "entry_trigger_period_bars": entry_period,
        "promotion_trigger": promotion,
        "exit_trigger": exit_trigger,
        "exit_reason": exit_reason,
        "cross_scale_entry_conflict": conflict,
        "exit_mode": np.full(row_count, spec.exit_mode, dtype=object),
        "runtime_uses_future": False,
        "runtime_uses_registered_events": False,
        "research_authority": True,
        "production_authority": False,
    }
    for period, frame in frames.items():
        for field in (
            "middle_log",
            "width_log",
            "upper_log",
            "lower_log",
            "entry_velocity_log_per_bar",
            "entry_acceleration_log_per_bar2",
            "middle_velocity_log_per_bar",
            "middle_acceleration_log_per_bar2",
            "normalized_middle_speed",
            "entry_up",
            "entry_down",
            "fresh_entry_up",
            "fresh_entry_down",
            "valid_multiscale",
        ):
            columns[f"p{period}_{field}"] = frame[field].to_numpy()
    output = pd.DataFrame(columns, index=numeric.index)
    output.attrs["field_labels_zh"] = {
        column: FIELD_LABELS_ZH.get(column, f"多尺度通道字段：{column}")
        for column in output.columns
    }
    output.attrs["formula_contract"] = fda_multiscale_channel_contract(spec)
    return output


def fda_multiscale_channel_contract(
    spec: FDAMultiscaleChannelSpec,
) -> dict[str, object]:
    return {
        "schema_id": "market_state_fda_multiscale_channel_v1@1.0",
        "candidate_id": spec.candidate_id,
        "period_bars": list(spec.period_bars),
        "maximum_authority_period_bars": max(spec.period_bars),
        "entry_formula_frozen_from_v0": True,
        "entry_formula": "raw_log_price_FDA_velocity_and_acceleration_same_direction_AND_outer_rail_break",
        "middle_derivative_formula": "causal_local_quadratic_endpoint_derivatives_of_each_channel_middle",
        "authority_formula": (
            "largest_same_direction_freshly_established_scale; "
            "authority_may_only_promote_on_a_later_fresh_edge_until_exit"
        ),
        "cross_scale_flat_entry_conflict": "larger_qualified_scale_wins; equal_scale_conflict_fails_closed",
        "exit_mode": spec.exit_mode,
        "slowdown_normalized_speed_formula": "abs(middle_velocity)*period/width",
        "slowdown_normalized_speed_boundary": SLOWDOWN_NORMALIZED_SPEED,
        "execution_semantics": "close_t_decision_open_t_plus_1",
        "runtime_uses_future": False,
        "runtime_uses_registered_events": False,
        "research_authority": True,
        "architecture_lock_authority": False,
        "parameter_authority": False,
        "production_authority": False,
        "v62_runtime_modified": False,
        "field_labels_zh": FIELD_LABELS_ZH,
    }


__all__ = [
    "EXIT_MODES",
    "FIELD_LABELS_ZH",
    "SLOWDOWN_NORMALIZED_SPEED",
    "FDAMultiscaleChannelSpec",
    "build_fda_multiscale_channel",
    "fda_multiscale_channel_contract",
]
