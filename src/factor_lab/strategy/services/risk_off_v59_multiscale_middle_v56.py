# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
"""V59: W72 base plus multiscale-middle-controlled V56 crash routing.

The P24/P48/P96 low-pass middles are treated as three causal K-line carriers.
Only their one-bar directions are consumed.  The resulting dimensionless
trend coordinates control where V56 acts: entry slope, entry observation age,
and recovery confirmation.  A close-time decision remains executable on the
next bar.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from factor_lab.strategy.services.risk_off_v56_steep_crash_specialist import (
    SteepCrashV56Spec,
    attach_v56_independent_channel_features,
)
from factor_lab.strategy.services.risk_off_v58_frequency_bollinger import (
    causal_lowpass,
)
from factor_lab.strategy.services.risk_off_v58_short_volatility_confirmation import (
    ShortVolatilityConfirmationSpec,
    asymmetric_channel_decision,
    build_asymmetric_position,
    build_short_volatility_channel,
)

FIELD_LABELS_ZH = {
    "middle_direction_p24": "短期P24中轨单棒方向",
    "middle_direction_p48": "中期P48中轨单棒方向",
    "middle_direction_p96": "长期P96中轨单棒方向",
    "normalized_middle_trend_p24": "短期中轨归一化趋势",
    "normalized_middle_trend_p48": "中期中轨归一化趋势",
    "normalized_middle_trend_p96": "长期中轨归一化趋势",
    "middle_bdci_p24": "短期中轨方向连续度",
    "middle_bdci_p48": "中期中轨方向连续度",
    "middle_bdci_p96": "长期中轨方向连续度",
    "middle_trend_activity": "三尺度中轨最大活动度",
    "middle_trend_stable": "三尺度中轨平稳状态",
    "middle_trend_stability_score": "三尺度中轨平稳程度",
    "middle_downside_pressure": "三尺度中轨下压强度",
    "middle_direction_agreement": "三尺度中轨方向一致度",
    "short_rebound_dominance": "短期反弹对中长期下压的优势",
    "dynamic_adoption_slope_threshold": "动态V56下降斜率准入阈值",
    "dynamic_entry_confirmation_bars": "动态V56入场观察棒数",
    "dynamic_recovery_confirmation_bars": "动态V56恢复确认棒数",
    "v59_applied_adoption_slope_threshold": "V59实际采用的下降斜率准入阈值",
    "v59_applied_entry_confirmation_bars": "V59实际采用的入场观察棒数",
    "v59_applied_recovery_confirmation_bars": "V59实际采用的恢复确认棒数",
    "v59_executable_risk_active": "V59当前执行棒空仓",
    "v59_decision_risk_active_for_next_bar": "V59本棒决定下一棒空仓",
    "v59_executable_long_position": "V59当前执行棒多仓",
    "v59_v56_entry_trigger": "V59的V56通道入场触发",
    "v59_v56_exit_trigger": "V59的V56通道恢复触发",
    "v59_v56_reentry_trigger": "W72背景内V56新通道再入场",
}


@dataclass(frozen=True, slots=True)
class V59MultiscaleMiddleV56Spec:
    """Frozen low-freedom V59 formula skeleton."""

    middle_periods_bars: tuple[int, int, int] = (24, 48, 96)
    middle_filter_order: int = 4
    stable_band_half_widths_per_period: float = 1.0
    base_adoption_slope_log_per_15m: float = 0.001
    stable_slope_multiplier_maximum: float = 2.0
    stable_entry_confirmation_bars: int = 2
    active_entry_confirmation_bars: int = 1
    weak_recovery_confirmation_bars: int = 3
    strong_recovery_confirmation_bars: int = 1
    exit_inner_band_fraction: float = 0.5
    channel_windows_bars: tuple[int, ...] = (12, 24, 128, 256)

    def __post_init__(self) -> None:
        if self.middle_periods_bars != (24, 48, 96):
            raise ValueError("V59 middle periods are frozen at P24/P48/P96")
        if self.middle_filter_order < 1:
            raise ValueError("middle filter order must be positive")
        if self.stable_band_half_widths_per_period <= 0.0:
            raise ValueError("stable band must be positive")
        if self.base_adoption_slope_log_per_15m <= 0.0:
            raise ValueError("base adoption slope must be positive")
        if self.stable_slope_multiplier_maximum < 1.0:
            raise ValueError("stable slope multiplier cannot be below one")
        if self.stable_entry_confirmation_bars < 1:
            raise ValueError("stable entry confirmation must be positive")
        if self.active_entry_confirmation_bars < 1:
            raise ValueError("active entry confirmation must be positive")
        if self.weak_recovery_confirmation_bars < 1:
            raise ValueError("weak recovery confirmation must be positive")
        if self.strong_recovery_confirmation_bars < 1:
            raise ValueError("strong recovery confirmation must be positive")
        if not 0.0 <= self.exit_inner_band_fraction <= 1.0:
            raise ValueError("exit inner-band fraction must be in [0, 1]")
        if not self.channel_windows_bars:
            raise ValueError("channel windows cannot be empty")


W72_SPEC = ShortVolatilityConfirmationSpec(72, 1.0, 1)


def build_v59_multiscale_middle_state(
    close: pd.Series,
    spec: V59MultiscaleMiddleV56Spec = V59MultiscaleMiddleV56Spec(),
    *,
    w72_spec: ShortVolatilityConfirmationSpec = W72_SPEC,
) -> pd.DataFrame:
    """Build formula-native P24/P48/P96 direction attributes.

    ``g_P = P * Δmiddle_P / W72_half_width`` has a physical reading: one
    means that, at the current causal speed, the middle would move one current
    W72 half-width over its own period.  The stable interval is therefore
    dimensionless and does not borrow a return percentile from the future.
    """

    numeric = pd.to_numeric(close, errors="coerce").astype(float)
    if numeric.empty or numeric.isna().any() or numeric.le(0.0).any():
        raise ValueError("close must be non-empty, finite, and positive")
    if not numeric.index.is_monotonic_increasing or numeric.index.has_duplicates:
        raise ValueError("close index must be ordered and unique")

    log_close = np.log(numeric)
    channel = build_short_volatility_channel(numeric, w72_spec)
    width = channel["width_log"].astype(float)
    valid_width = channel["valid"].astype(bool) & width.gt(1e-12)
    output = pd.DataFrame(index=numeric.index)
    trend_columns: list[str] = []
    for period in spec.middle_periods_bars:
        middle = causal_lowpass(log_close, period, spec.middle_filter_order)
        direction = middle.diff().fillna(0.0)
        trend = (float(period) * direction / width.where(valid_width)).replace([np.inf, -np.inf], np.nan)
        output[f"middle_log_p{period}"] = middle
        output[f"middle_direction_p{period}"] = direction
        output[f"normalized_middle_trend_p{period}"] = trend
        direction_sign = np.sign(direction).replace(0.0, np.nan)
        valid_pair = direction_sign.notna() & direction_sign.shift(1).notna()
        switches = valid_pair & direction_sign.ne(direction_sign.shift(1))
        opportunities = valid_pair.astype(float).rolling(period, min_periods=period).sum()
        output[f"middle_bdci_p{period}"] = (
            1.0 - switches.astype(float).rolling(period, min_periods=period).sum() / opportunities.replace(0.0, np.nan)
        ).clip(0.0, 1.0)
        trend_columns.append(f"normalized_middle_trend_p{period}")

    trends = output[trend_columns]
    activity = trends.abs().max(axis=1).fillna(np.inf)
    stable_limit = spec.stable_band_half_widths_per_period
    stability_score = (1.0 - activity / stable_limit).clip(0.0, 1.0)
    stable = valid_width & activity.le(stable_limit)
    signs = np.sign(trends.fillna(0.0))
    agreement = signs.sum(axis=1).abs() / float(len(trend_columns))
    short = trends["normalized_middle_trend_p24"].fillna(0.0)
    medium_headwind = (-trends["normalized_middle_trend_p48"].fillna(0.0)).clip(lower=0.0)
    long_headwind = (-trends["normalized_middle_trend_p96"].fillna(0.0)).clip(lower=0.0)
    rebound_dominance = short - 0.5 * (medium_headwind + long_headwind)
    strong_recovery = short.gt(0.0) & rebound_dominance.ge(0.0)

    slope_span = spec.stable_slope_multiplier_maximum - 1.0
    downside_pressure = (-trends.fillna(0.0)).clip(lower=0.0, upper=1.0).mean(axis=1)
    stable_slope_threshold = spec.base_adoption_slope_log_per_15m * (1.0 + slope_span * stability_score)
    active_slope_threshold = spec.base_adoption_slope_log_per_15m / (1.0 + downside_pressure)
    output["middle_trend_activity"] = activity.replace(np.inf, np.nan)
    output["middle_trend_stable"] = stable
    output["middle_trend_stability_score"] = stability_score
    output["middle_downside_pressure"] = downside_pressure
    output["middle_direction_agreement"] = agreement
    output["short_rebound_dominance"] = rebound_dominance
    # A calm market requires a steeper channel and an extra confirmation bar.
    # Outside that calm regime, coherent downside pressure may only make a new
    # independent V56 channel easier to qualify; it never revives prior rails.
    output["dynamic_adoption_slope_threshold"] = np.where(
        stable,
        stable_slope_threshold,
        active_slope_threshold,
    )
    output["dynamic_entry_confirmation_bars"] = np.where(
        stable,
        spec.stable_entry_confirmation_bars,
        spec.active_entry_confirmation_bars,
    ).astype(np.int64)
    output["dynamic_recovery_confirmation_bars"] = np.where(
        strong_recovery,
        spec.strong_recovery_confirmation_bars,
        spec.weak_recovery_confirmation_bars,
    ).astype(np.int64)
    output["runtime_uses_future"] = False
    output["runtime_uses_registered_events"] = False
    return output


def _log_boundary(upper: float, lower: float, fraction: float) -> float:
    return float(np.exp((1.0 - fraction) * np.log(upper) + fraction * np.log(lower)))


def build_v59_multiscale_middle_v56(
    causal_ohlc: pd.DataFrame,
    spec: V59MultiscaleMiddleV56Spec = V59MultiscaleMiddleV56Spec(),
    *,
    w72_spec: ShortVolatilityConfirmationSpec = W72_SPEC,
    w72_recovery_width_fraction: float = 1.0,
    dynamic_parameters: bool = True,
    dynamic_entry_parameters: bool | None = None,
    dynamic_recovery_parameters: bool | None = None,
) -> pd.DataFrame:
    """Build dynamic V59 or its same-state-machine static comparator."""

    required = {"timestamp", "open", "high", "low", "close"}
    missing = sorted(required.difference(causal_ohlc.columns))
    if missing:
        raise KeyError(f"V59 carrier missing columns: {missing}")
    carrier = causal_ohlc.copy().reset_index(drop=True)
    timestamps = pd.DatetimeIndex(pd.to_datetime(carrier["timestamp"]))
    if timestamps.has_duplicates or not timestamps.is_monotonic_increasing:
        raise ValueError("V59 timestamps must be ordered and unique")
    for flag in ("runtime_uses_future", "runtime_uses_registered_events"):
        if flag in carrier and bool(carrier[flag].astype(bool).any()):
            raise ValueError(f"V59 carrier declares forbidden {flag}")
    carrier["runtime_uses_future"] = False
    carrier["runtime_uses_registered_events"] = False

    close = pd.Series(
        pd.to_numeric(carrier["close"], errors="raise").to_numpy(dtype=float),
        index=timestamps,
        name="close",
    )
    middle_state = build_v59_multiscale_middle_state(
        close,
        spec,
        w72_spec=w72_spec,
    )
    fallback_channel = build_short_volatility_channel(close, w72_spec)
    frozen_w72_long_decision = asymmetric_channel_decision(
        fallback_channel,
        w72_spec.downside_confirmation_bars,
        recovery_width_fraction=w72_recovery_width_fraction,
    )
    frozen_w72_long = build_asymmetric_position(
        close,
        w72_spec,
        recovery_width_fraction=w72_recovery_width_fraction,
    )
    channels = attach_v56_independent_channel_features(
        carrier,
        SteepCrashV56Spec(channel_windows_bars=spec.channel_windows_bars),
    )
    size = len(channels)

    entry_dynamic = dynamic_parameters if dynamic_entry_parameters is None else dynamic_entry_parameters
    recovery_dynamic = dynamic_parameters if dynamic_recovery_parameters is None else dynamic_recovery_parameters
    if entry_dynamic:
        slope_threshold = middle_state["dynamic_adoption_slope_threshold"].to_numpy(dtype=float)
        entry_confirmation = middle_state["dynamic_entry_confirmation_bars"].to_numpy(dtype=np.int64)
    else:
        slope_threshold = np.full(size, spec.base_adoption_slope_log_per_15m, dtype=float)
        entry_confirmation = np.full(size, 1, dtype=np.int64)
    recovery_confirmation = (
        middle_state["dynamic_recovery_confirmation_bars"].to_numpy(dtype=np.int64)
        if recovery_dynamic
        else np.full(size, 1, dtype=np.int64)
    )
    # W72 owns the outer background.  Inner V56 parameters must never change
    # when that background opens or closes.
    base_long_decision = frozen_w72_long_decision
    fallback_risk_decision = (~base_long_decision).to_numpy(dtype=bool)
    base_long = base_long_decision.shift(1, fill_value=False).astype(float)
    base_risk = base_long.eq(0.0).to_numpy(dtype=bool)

    windows = spec.channel_windows_bars
    eligible: dict[int, np.ndarray] = {}
    candidate: dict[int, np.ndarray] = {}
    slope: dict[int, np.ndarray] = {}
    upper: dict[int, np.ndarray] = {}
    lower: dict[int, np.ndarray] = {}
    for window in windows:
        prefix = f"exit_channel_w{window}"
        geometry = channels[f"{prefix}_geometry_valid"].to_numpy(dtype=bool)
        local_slope = channels[f"{prefix}_slope_log_per_bar"].to_numpy(dtype=float)
        local_upper = channels[f"{prefix}_upper_rail"].to_numpy(dtype=float)
        local_lower = channels[f"{prefix}_lower_rail"].to_numpy(dtype=float)
        centre = np.sqrt(local_upper * local_lower)
        raw = (
            geometry
            & np.isfinite(local_slope)
            & np.isfinite(local_upper)
            & np.isfinite(local_lower)
            & (local_slope <= -slope_threshold)
            & (close.to_numpy(dtype=float) <= centre)
        )
        run = np.zeros(size, dtype=np.int64)
        for location in range(size):
            run[location] = run[location - 1] + 1 if raw[location] and location else int(raw[location])
        local_eligible = raw & (run >= entry_confirmation)
        prior = np.zeros(size, dtype=bool)
        if size > 1:
            prior[1:] = local_eligible[:-1]
        eligible[window] = local_eligible
        candidate[window] = local_eligible & ~prior
        slope[window] = local_slope
        upper[window] = local_upper
        lower[window] = local_lower

    decision_risk = np.zeros(size, dtype=bool)
    entry_trigger = np.zeros(size, dtype=bool)
    reentry_trigger = np.zeros(size, dtype=bool)
    adoption_trigger = np.zeros(size, dtype=bool)
    authority_update = np.zeros(size, dtype=bool)
    exit_trigger = np.zeros(size, dtype=bool)
    authority_window_values = np.zeros(size, dtype=np.int64)
    live_boundary_values = np.full(size, np.nan, dtype=float)
    release_pending_values = np.zeros(size, dtype=bool)

    active = False
    adopted = False
    released_within_fallback = False
    anchor = -1
    authority_window = 0
    authority_slope = np.nan
    authority_upper = np.nan
    authority_lower = np.nan
    above_boundary_age = 0

    for location in range(size):
        fallback_now = fallback_risk_decision[location]
        prior_fallback = fallback_risk_decision[location - 1] if location else False
        if not fallback_now:
            active = False
            adopted = False
            released_within_fallback = False
            anchor = -1
            authority_window = 0
            authority_slope = np.nan
            authority_upper = np.nan
            authority_lower = np.nan
            above_boundary_age = 0
            decision_risk[location] = False
            release_pending_values[location] = False
            continue
        if not prior_fallback:
            active = True
            adopted = False
            released_within_fallback = False
            anchor = -1
            authority_window = 0
            authority_slope = np.nan
            authority_upper = np.nan
            authority_lower = np.nan
            above_boundary_age = 0

        fresh = [window for window in windows if candidate[window][location]]
        live = [window for window in windows if eligible[window][location]]

        if active and not adopted and live:
            selected = min(live, key=lambda value: slope[value][location])
            adopted = True
            adoption_trigger[location] = True
            anchor = location
            authority_window = selected
            authority_slope = float(slope[selected][location])
            authority_upper = float(upper[selected][location])
            authority_lower = float(lower[selected][location])
            above_boundary_age = 0
        elif active and adopted:
            steeper = [window for window in fresh if slope[window][location] < authority_slope]
            if steeper:
                selected = min(steeper, key=lambda value: slope[value][location])
                authority_update[location] = True
                anchor = location
                authority_window = selected
                authority_slope = float(slope[selected][location])
                authority_upper = float(upper[selected][location])
                authority_lower = float(lower[selected][location])
                above_boundary_age = 0
            elapsed = location - anchor
            projected_upper = authority_upper * np.exp(authority_slope * elapsed)
            projected_lower = authority_lower * np.exp(authority_slope * elapsed)
            boundary = _log_boundary(
                projected_upper,
                projected_lower,
                spec.exit_inner_band_fraction,
            )
            live_boundary_values[location] = boundary
            above_boundary_age = above_boundary_age + 1 if close.iloc[location] > boundary else 0
            if above_boundary_age >= recovery_confirmation[location]:
                active = False
                adopted = False
                released_within_fallback = bool(fallback_now)
                above_boundary_age = 0
                exit_trigger[location] = True
        elif not active and released_within_fallback and fresh:
            selected = min(fresh, key=lambda value: slope[value][location])
            active = True
            adopted = True
            reentry_trigger[location] = True
            released_within_fallback = False
            anchor = location
            authority_window = selected
            authority_slope = float(slope[selected][location])
            authority_upper = float(upper[selected][location])
            authority_lower = float(lower[selected][location])
            above_boundary_age = 0

        decision_risk[location] = active
        release_pending_values[location] = released_within_fallback
        if active and adopted:
            authority_window_values[location] = authority_window
            if not np.isfinite(live_boundary_values[location]):
                live_boundary_values[location] = _log_boundary(authority_upper, authority_lower, spec.exit_inner_band_fraction)

    executable_risk = np.r_[True, decision_risk[:-1]]
    output = middle_state.reset_index(drop=True).copy()
    output.insert(0, "timestamp", timestamps)
    output["w72_fallback_long_position"] = frozen_w72_long.to_numpy(dtype=float)
    output["w72_fallback_risk_active"] = frozen_w72_long.eq(0.0).to_numpy(dtype=bool)
    output["v59_base_long_position"] = base_long.to_numpy(dtype=float)
    output["v59_base_risk_active"] = base_risk
    output["w72_fallback_risk_decision_for_next_bar"] = fallback_risk_decision
    output["v59_dynamic_parameters_enabled"] = entry_dynamic or recovery_dynamic
    output["v59_dynamic_entry_parameters_enabled"] = entry_dynamic
    output["v59_dynamic_recovery_parameters_enabled"] = recovery_dynamic
    output["v59_applied_adoption_slope_threshold"] = slope_threshold
    output["v59_applied_entry_confirmation_bars"] = entry_confirmation
    output["v59_applied_recovery_confirmation_bars"] = recovery_confirmation
    output["v59_v56_adoption_trigger"] = adoption_trigger
    output["v59_v56_authority_update_trigger"] = authority_update
    output["v59_v56_entry_trigger"] = entry_trigger
    output["v59_v56_reentry_trigger"] = reentry_trigger
    output["v59_v56_exit_trigger"] = exit_trigger
    output["v59_v56_authority_window_bars"] = authority_window_values
    output["v59_v56_live_exit_boundary"] = live_boundary_values
    output["v59_release_pending_within_w72"] = release_pending_values
    output["v59_executable_risk_active"] = executable_risk
    output["v59_decision_risk_active_for_next_bar"] = decision_risk
    output["v59_executable_long_position"] = (~executable_risk).astype(float)
    output["runtime_uses_future"] = False
    output["runtime_uses_registered_events"] = False
    return output


def v59_formula_contract(
    spec: V59MultiscaleMiddleV56Spec = V59MultiscaleMiddleV56Spec(),
) -> dict[str, object]:
    """Expose the formula skeleton and Chinese-labelled parameter mapping."""

    return {
        "schema_id": "risk_off_v59_multiscale_middle_v56@1.0",
        "strategy_version": "V59",
        "spec": asdict(spec),
        "base_strategy": "V58_W72_K1_C1_frequency_selective_bollinger",
        "specialist": "V56_independent_descending_channel",
        "middle_trend_formula": "g_P=P*delta(lowpass_P(log_close))/W72_half_width",
        "stable_formula": "max(abs(g24),abs(g48),abs(g96))<=1",
        "dynamic_entry_slope_formula": ("stable?0.001*(1+stability_score):0.001/(1+mean(clip(-g24,-g48,-g96,0,1)))"),
        "dynamic_entry_delay_formula": "v56_new_channel_only:stable?2:1",
        "dynamic_recovery_formula": "short_rebound_dominates_mid_long_headwind?1:3",
        "outer_background_contract": "v56_risk_state_subset_of_frozen_w72_risk_background",
        "execution_semantics": "close_t_decision_open_t_plus_1",
        "field_labels_zh": FIELD_LABELS_ZH,
        "runtime_uses_future": False,
        "runtime_uses_registered_events": False,
        "production_authority": False,
    }


__all__ = [
    "FIELD_LABELS_ZH",
    "V59MultiscaleMiddleV56Spec",
    "W72_SPEC",
    "build_v59_multiscale_middle_state",
    "build_v59_multiscale_middle_v56",
    "v59_formula_contract",
]
