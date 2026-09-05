"""Pure OLS explosive-channel lifecycle with OLS-native exits.

The entry geometry is the frozen context-free regression carrier.  This
module deliberately adds no frequency/Bollinger lifecycle: the same W12/W24
OLS family that qualifies a high-slope event also owns its exit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

OLSExitMode = Literal[
    "qualification_reset",
    "first_opposite_close",
    "two_opposite_closes",
    "prior_extreme_break",
    "frozen_midline_break",
]
OLS_EXIT_MODES: tuple[OLSExitMode, ...] = (
    "qualification_reset",
    "first_opposite_close",
    "two_opposite_closes",
    "prior_extreme_break",
    "frozen_midline_break",
)

FIELD_LABELS_ZH = {
    "decision_position_for_next_bar": "本棒决定下一棒的OLS多空仓位",
    "executable_position": "当前执行棒OLS多空仓位",
    "decision_authority_window_bars": "本棒OLS权威窗口",
    "executable_authority_window_bars": "当前执行棒OLS权威窗口",
    "entry_trigger_direction": "OLS新入场方向",
    "entry_trigger_window_bars": "OLS新入场窗口",
    "exit_trigger": "OLS原生退出触发",
    "exit_reason": "OLS原生退出原因",
    "direction_conflict": "双向OLS生命周期冲突",
    "exit_mode": "OLS退出语义",
    "runtime_uses_future": "运行时是否使用未来数据",
    "runtime_uses_registered_events": "运行时是否使用事后注册事件",
    "research_authority": "研究权限",
    "production_authority": "生产权限",
}


@dataclass(frozen=True, slots=True)
class OLSExplosiveChannelSpec:
    exit_mode: OLSExitMode
    windows_bars: tuple[int, ...] = (12, 24)

    def __post_init__(self) -> None:
        if self.exit_mode not in OLS_EXIT_MODES:
            raise ValueError(f"exit_mode must be one of {OLS_EXIT_MODES}")
        if self.windows_bars != (12, 24):
            raise ValueError("V1 freezes the OLS fast family to W12/W24")

    @property
    def candidate_id(self) -> str:
        return f"ols_w12_w24_{self.exit_mode}"


def _validate_inputs(
    causal_ohlc: pd.DataFrame,
    regression_features: pd.DataFrame,
    windows: tuple[int, ...],
) -> pd.DataFrame:
    required_price = {"timestamp", "open", "high", "low", "close"}
    missing_price = sorted(required_price.difference(causal_ohlc.columns))
    if missing_price:
        raise KeyError(f"OLS lifecycle missing price columns: {missing_price}")
    if len(causal_ohlc) != len(regression_features):
        raise ValueError("price and regression feature rows must match")
    timestamp = pd.DatetimeIndex(pd.to_datetime(causal_ohlc["timestamp"], errors="raise"))
    if timestamp.has_duplicates or not timestamp.is_monotonic_increasing:
        raise ValueError("OLS lifecycle timestamps must be ordered and unique")
    required_features = {
        f"context_free_explosive_{side}_w{window}_{field}"
        for side in ("up", "down")
        for window in windows
        for field in (
            "path_efficiency",
            "fit_r2",
            "slope_log_per_15m",
            "upper_rail",
            "lower_rail",
            "qualified",
            "candidate_trigger",
        )
    }
    missing_features = sorted(required_features.difference(regression_features.columns))
    if missing_features:
        raise KeyError(f"OLS lifecycle missing regression features: {missing_features}")
    for flag in ("runtime_uses_future", "runtime_uses_registered_events"):
        if flag in regression_features and bool(regression_features[flag].astype(bool).any()):
            raise ValueError(f"regression features declare forbidden {flag}")
    carrier = causal_ohlc.loc[:, ["timestamp", "open", "high", "low", "close"]].copy()
    for column in ("open", "high", "low", "close"):
        values = pd.to_numeric(carrier[column], errors="raise").to_numpy(float)
        if not np.isfinite(values).all() or bool((values <= 0.0).any()):
            raise ValueError(f"OLS lifecycle {column} must be finite and positive")
        carrier[column] = values
    return carrier.reset_index(drop=True)


def _opposite_confirmation(
    *,
    mode: OLSExitMode,
    side: str,
    location: int,
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
) -> bool:
    if mode == "qualification_reset":
        return True
    if mode == "first_opposite_close":
        return bool(
            location > 0
            and (close[location] < close[location - 1] if side == "up" else close[location] > close[location - 1])
        )
    if mode == "two_opposite_closes":
        return bool(
            location > 1
            and (
                close[location] < close[location - 1] < close[location - 2]
                if side == "up"
                else close[location] > close[location - 1] > close[location - 2]
            )
        )
    if mode == "prior_extreme_break":
        return bool(
            location > 0
            and (close[location] < low[location - 1] if side == "up" else close[location] > high[location - 1])
        )
    return False


def _direction_lifecycle(
    carrier: pd.DataFrame,
    features: pd.DataFrame,
    spec: OLSExplosiveChannelSpec,
    side: str,
) -> dict[str, np.ndarray]:
    size = len(carrier)
    close = carrier["close"].to_numpy(float)
    high = carrier["high"].to_numpy(float)
    low = carrier["low"].to_numpy(float)
    sign = 1 if side == "up" else -1
    decision = np.zeros(size, dtype=bool)
    entry_trigger = np.zeros(size, dtype=bool)
    entry_window = np.zeros(size, dtype=np.int16)
    exit_trigger = np.zeros(size, dtype=bool)
    exit_reason = np.full(size, "none", dtype=object)
    authority_window = np.zeros(size, dtype=np.int16)
    live_boundary = np.full(size, np.nan, dtype=float)
    active = False
    window = 0
    anchor = -1
    slope = np.nan
    upper = np.nan
    lower = np.nan

    def field(local_window: int, name: str) -> np.ndarray:
        return features[
            f"context_free_explosive_{side}_w{local_window}_{name}"
        ].to_numpy()

    qualified = {w: field(w, "qualified").astype(bool) for w in spec.windows_bars}
    candidate = {w: field(w, "candidate_trigger").astype(bool) for w in spec.windows_bars}
    local_slope = {w: field(w, "slope_log_per_15m").astype(float) for w in spec.windows_bars}
    local_upper = {w: field(w, "upper_rail").astype(float) for w in spec.windows_bars}
    local_lower = {w: field(w, "lower_rail").astype(float) for w in spec.windows_bars}
    efficiency = {w: field(w, "path_efficiency").astype(float) for w in spec.windows_bars}
    fit_r2 = {w: field(w, "fit_r2").astype(float) for w in spec.windows_bars}

    for location in range(size):
        exited_now = False
        live = [w for w in spec.windows_bars if qualified[w][location]]
        if active:
            elapsed = location - anchor
            projected_upper = upper * np.exp(slope * elapsed)
            projected_lower = lower * np.exp(slope * elapsed)
            boundary = float(np.sqrt(projected_upper * projected_lower))
            live_boundary[location] = boundary
            boundary_break = close[location] < boundary if side == "up" else close[location] > boundary
            family_reset = not live
            shape_confirmed = _opposite_confirmation(
                mode=spec.exit_mode,
                side=side,
                location=location,
                close=close,
                high=high,
                low=low,
            )
            reset_exit = bool(
                spec.exit_mode != "frozen_midline_break"
                and family_reset
                and shape_confirmed
            )
            if boundary_break or reset_exit:
                active = False
                window = 0
                anchor = -1
                slope = np.nan
                upper = np.nan
                lower = np.nan
                exit_trigger[location] = True
                exit_reason[location] = (
                    "frozen_ols_midline_break" if boundary_break else spec.exit_mode
                )
                exited_now = True

        if not active and not exited_now:
            fresh = [w for w in spec.windows_bars if candidate[w][location]]
            if fresh:
                scores = {
                    local_window: float(
                        abs(local_slope[local_window][location])
                        * float(local_window - 1)
                        * max(efficiency[local_window][location], 0.0)
                        * max(fit_r2[local_window][location], 0.0)
                    )
                    for local_window in fresh
                }
                selected = max(fresh, key=scores.__getitem__)
                active = True
                window = selected
                anchor = location
                slope = float(local_slope[selected][location])
                upper = float(local_upper[selected][location])
                lower = float(local_lower[selected][location])
                entry_trigger[location] = True
                entry_window[location] = selected

        decision[location] = active
        authority_window[location] = window

    return {
        "decision": decision,
        "entry_trigger": entry_trigger,
        "entry_window": entry_window,
        "exit_trigger": exit_trigger,
        "exit_reason": exit_reason,
        "authority_window": authority_window,
        "live_boundary": live_boundary,
        "sign": np.full(size, sign, dtype=np.int8),
    }


def build_ols_explosive_channel_from_features(
    causal_ohlc: pd.DataFrame,
    regression_features: pd.DataFrame,
    spec: OLSExplosiveChannelSpec,
) -> pd.DataFrame:
    """Replay one OLS-native exit over one frozen regression feature carrier."""

    carrier = _validate_inputs(causal_ohlc, regression_features, spec.windows_bars)
    up = _direction_lifecycle(carrier, regression_features, spec, "up")
    down = _direction_lifecycle(carrier, regression_features, spec, "down")
    raw_up = up["decision"].astype(bool)
    raw_down = down["decision"].astype(bool)
    conflict = raw_up & raw_down
    decision = raw_up.astype(np.int8) - raw_down.astype(np.int8)
    decision[conflict] = 0
    authority = np.where(
        decision == 1,
        up["authority_window"],
        np.where(decision == -1, down["authority_window"], 0),
    ).astype(np.int16)
    entry_direction = up["entry_trigger"].astype(np.int8) - down["entry_trigger"].astype(np.int8)
    entry_direction[conflict] = 0
    entry_window = np.where(
        entry_direction == 1,
        up["entry_window"],
        np.where(entry_direction == -1, down["entry_window"], 0),
    ).astype(np.int16)
    executable = np.zeros(len(carrier), dtype=np.int8)
    executable_authority = np.zeros(len(carrier), dtype=np.int16)
    if len(carrier) > 1:
        executable[1:] = decision[:-1]
        executable_authority[1:] = authority[:-1]
    exit_trigger = up["exit_trigger"].astype(bool) | down["exit_trigger"].astype(bool)
    exit_reason = np.where(
        up["exit_trigger"],
        np.char.add("up:", up["exit_reason"].astype(str)),
        np.where(
            down["exit_trigger"],
            np.char.add("down:", down["exit_reason"].astype(str)),
            "none",
        ),
    )
    output = pd.DataFrame(
        {
            "decision_position_for_next_bar": decision,
            "executable_position": executable,
            "decision_authority_window_bars": authority,
            "executable_authority_window_bars": executable_authority,
            "entry_trigger_direction": entry_direction,
            "entry_trigger_window_bars": entry_window,
            "exit_trigger": exit_trigger,
            "exit_reason": exit_reason,
            "direction_conflict": conflict,
            "up_decision_active": raw_up,
            "down_decision_active": raw_down,
            "up_live_ols_midline": up["live_boundary"],
            "down_live_ols_midline": down["live_boundary"],
            "exit_mode": spec.exit_mode,
            "runtime_uses_future": False,
            "runtime_uses_registered_events": False,
            "research_authority": True,
            "production_authority": False,
        },
        index=pd.DatetimeIndex(carrier["timestamp"]),
    )
    output.attrs["field_labels_zh"] = {
        column: FIELD_LABELS_ZH.get(column, f"OLS爆发行情字段：{column}")
        for column in output.columns
    }
    output.attrs["formula_contract"] = ols_explosive_channel_contract(spec)
    return output


def ols_explosive_channel_contract(spec: OLSExplosiveChannelSpec) -> dict[str, object]:
    return {
        "schema_id": "market_state_ols_explosive_channel_v1@1.0",
        "candidate_id": spec.candidate_id,
        "entry": "fresh_W12_or_W24_OLS_high_slope_high_path_efficiency_qualification",
        "authority_windows_bars": list(spec.windows_bars),
        "exit_mode": spec.exit_mode,
        "common_failsafe_exit": "frozen_authority_OLS_midline_break",
        "frequency_channel_used": False,
        "execution_semantics": "close_t_decision_open_t_plus_1",
        "runtime_uses_future": False,
        "runtime_uses_registered_events": False,
        "research_authority": True,
        "architecture_lock_authority": False,
        "parameter_authority": False,
        "production_authority": False,
        "field_labels_zh": FIELD_LABELS_ZH,
    }


__all__ = [
    "FIELD_LABELS_ZH",
    "OLS_EXIT_MODES",
    "OLSExplosiveChannelSpec",
    "build_ols_explosive_channel_from_features",
    "ols_explosive_channel_contract",
]
