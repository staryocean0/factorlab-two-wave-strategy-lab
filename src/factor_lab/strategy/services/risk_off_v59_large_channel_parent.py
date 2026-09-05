# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportCallInDefaultInitializer=false, reportIndexIssue=false
"""V59 prototype: top-priority multiscale descending-channel authority.

The prototype separates two causal jobs:

* W12/W24 high-slope channels may start protection quickly; and
* W128/W256 parent channels qualify by total fitted displacement rather than
  by reusing the short-channel per-bar slope floor.

Once a parent channel takes authority, the end of a short child channel does
not release protection.  Every fit and path attribute at bar ``t`` uses bars
strictly before ``t``.  The close of ``t`` decides the position at ``t + 1``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

import numpy as np
import pandas as pd

from factor_lab.strategy.services.risk_off_v56_steep_crash_specialist import (
    SteepCrashV56Spec,
    attach_v56_independent_channel_features,
)
from factor_lab.strategy.services.risk_off_v58_short_volatility_confirmation import (
    ShortVolatilityConfirmationSpec,
)
from factor_lab.strategy.services.risk_off_v59_multiscale_middle_v56 import (
    W72_SPEC,
    V59MultiscaleMiddleV56Spec,
    build_v59_multiscale_middle_v56,
)

FIELD_LABELS_ZH = {
    "large_channel_fast_qualified_count": "大通道短尺度高斜率达标数",
    "large_channel_parent_qualified_count": "大通道长尺度父通道达标数",
    "large_channel_entry_trigger": "大通道独立入场触发",
    "large_channel_entry_route": "大通道入场路径",
    "large_channel_failed_rebound_reentry_trigger": "反弹失败新低重建通道触发",
    "large_channel_parent_promotion_trigger": "短通道升级为父通道触发",
    "large_channel_exit_trigger": "大通道权威向上破轨退出触发",
    "large_channel_exit_route": "大通道退出路径",
    "large_channel_authority_family": "大通道当前权威层级",
    "large_channel_authority_window_bars": "大通道当前权威窗口",
    "large_channel_live_exit_boundary": "大通道冻结权威实时退出边界",
    "large_channel_rebound_watch_active": "暴跌后反弹观察态",
    "large_channel_rebound_watch_floor": "反弹观察的前脉冲最低点",
    "large_channel_rebound_watch_success_boundary": "反弹成功的旧通道中轨边界",
    "large_channel_decision_risk_active_for_next_bar": "大通道本棒决定下一棒空仓",
    "large_channel_executable_risk_active": "大通道当前执行棒空仓",
    "v59_large_channel_route_added_risk": "大通道在W72之外新增空仓",
    "v59_large_channel_decision_risk_active_for_next_bar": "V59大通道路由本棒决定下一棒空仓",
    "v59_large_channel_executable_long_position": "V59大通道路由当前执行棒多仓",
    "path_efficiency": "严格历史同尺度路径效率",
    "tail_decline_dominance": "严格历史单棒下跌尾部占比",
    "sign_flip_rate": "严格历史方向翻转率",
    "fitted_total_down_displacement": "拟合窗口累计下行位移",
}


@dataclass(frozen=True, slots=True)
class V59LargeChannelParentSpec:
    """Low-freedom physical contract for the architecture prototype."""

    fast_windows_bars: tuple[int, ...] = (12, 24)
    parent_windows_bars: tuple[int, ...] = (128, 256)
    fast_minimum_down_slope_log_per_15m: float = 0.001
    fast_minimum_path_efficiency: float = 0.30
    fast_minimum_fit_r2: float = 0.10
    parent_minimum_total_down_displacement_log: float = 0.06
    parent_minimum_scale_adjusted_path_efficiency: float = 0.25
    parent_minimum_fit_r2: float = 0.60
    maximum_single_bar_decline_share: float = 0.50
    parent_path_sampling_stride_bars: int = 4
    parent_requires_fast_seed: bool = True
    parent_promotion_enabled: bool = True
    # Disabled by default so the first parent-prototype evidence package stays
    # reproducible.  The crash-rebound handoff version enables this switch and
    # treats a full W12/W24 qualification reset as the end of the current
    # independent pulse.  A later qualification edge must build a new channel.
    fast_family_reset_release_enabled: bool = False
    fast_family_reset_release_mode: Literal[
        "first_up_close",
        "two_up_closes",
        "prior_high_break",
    ] = "first_up_close"
    fast_failed_rebound_reentry_enabled: bool = False
    fast_failed_rebound_reentry_mode: Literal[
        "pulse_trough_break",
        "prior_low_break",
    ] = "pulse_trough_break"
    fast_exit_inner_band_fraction: float = 0.50
    # A structural parent remains the re-entry context, but cash authority
    # ends when price breaks its centreline.  Waiting for the outer upper rail
    # reproduced the exact 2015-07 rebound miss that this prototype must not
    # hide behind a lower maximum drawdown.
    parent_exit_inner_band_fraction: float = 0.50
    upward_break_confirmation_bars: int = 1

    def __post_init__(self) -> None:
        windows = self.fast_windows_bars + self.parent_windows_bars
        if not self.fast_windows_bars or not self.parent_windows_bars:
            raise ValueError("fast and parent channel families must be non-empty")
        if len(set(windows)) != len(windows) or min(windows) < 8:
            raise ValueError("channel windows must be unique and at least 8 bars")
        if max(self.fast_windows_bars) >= min(self.parent_windows_bars):
            raise ValueError("fast windows must be shorter than parent windows")
        if self.fast_minimum_down_slope_log_per_15m <= 0.0:
            raise ValueError("fast slope floor must be positive")
        if self.parent_minimum_total_down_displacement_log <= 0.0:
            raise ValueError("parent displacement floor must be positive")
        for name, value in (
            ("fast path efficiency", self.fast_minimum_path_efficiency),
            ("parent path efficiency", self.parent_minimum_scale_adjusted_path_efficiency),
            ("fast fit r2", self.fast_minimum_fit_r2),
            ("parent fit r2", self.parent_minimum_fit_r2),
            ("single-bar decline share", self.maximum_single_bar_decline_share),
            ("fast exit fraction", self.fast_exit_inner_band_fraction),
            ("parent exit fraction", self.parent_exit_inner_band_fraction),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.parent_path_sampling_stride_bars < 1:
            raise ValueError("parent path sampling stride must be positive")
        if self.upward_break_confirmation_bars < 1:
            raise ValueError("upward break confirmation must be positive")
        if self.fast_family_reset_release_mode not in {
            "first_up_close",
            "two_up_closes",
            "prior_high_break",
        }:
            raise ValueError("unsupported fast family reset release mode")
        if self.fast_failed_rebound_reentry_mode not in {
            "pulse_trough_break",
            "prior_low_break",
        }:
            raise ValueError("unsupported failed rebound re-entry mode")


def _prior_path_attributes(
    log_close: np.ndarray,
    *,
    window: int,
    stride: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return prior-only PE, one-bar tail share, and sign-flip rate."""

    size = len(log_close)
    efficiency = np.full(size, np.nan, dtype=float)
    tail_share = np.full(size, np.nan, dtype=float)
    sign_flip = np.full(size, np.nan, dtype=float)
    for location in range(window, size):
        full = log_close[location - window : location]
        sampled = full[::stride]
        if sampled[-1] != full[-1]:
            sampled = np.r_[sampled, full[-1]]
        sampled_returns = np.diff(sampled)
        gross = float(np.abs(sampled_returns).sum())
        net_down = float(sampled[0] - sampled[-1])
        if gross > 0.0:
            efficiency[location] = abs(net_down) / gross
        full_returns = np.diff(full)
        if net_down > np.finfo(float).eps:
            tail_share[location] = float(np.maximum(-full_returns, 0.0).max(initial=0.0) / net_down)
        signs = np.sign(sampled_returns)
        signs = signs[signs != 0.0]
        if len(signs) > 1:
            sign_flip[location] = float(np.mean(signs[1:] != signs[:-1]))
    return efficiency, tail_share, sign_flip


def _log_boundary(upper: float, lower: float, fraction: float) -> float:
    return float(np.exp((1.0 - fraction) * np.log(upper) + fraction * np.log(lower)))


def build_v59_large_channel_parent(
    causal_ohlc: pd.DataFrame,
    spec: V59LargeChannelParentSpec = V59LargeChannelParentSpec(),
    *,
    base_spec: V59MultiscaleMiddleV56Spec = V59MultiscaleMiddleV56Spec(),
    w72_spec: ShortVolatilityConfirmationSpec = W72_SPEC,
    w72_recovery_width_fraction: float = 1.0,
) -> pd.DataFrame:
    """Compose static V59 with an independent top-priority channel route."""

    required = {"timestamp", "open", "high", "low", "close"}
    missing = sorted(required.difference(causal_ohlc.columns))
    if missing:
        raise KeyError(f"large-channel carrier missing columns: {missing}")
    carrier = causal_ohlc.copy().reset_index(drop=True)
    timestamps = pd.DatetimeIndex(pd.to_datetime(carrier["timestamp"]))
    if timestamps.has_duplicates or not timestamps.is_monotonic_increasing:
        raise ValueError("large-channel timestamps must be ordered and unique")
    for flag in ("runtime_uses_future", "runtime_uses_registered_events"):
        if flag in carrier and bool(carrier[flag].astype(bool).any()):
            raise ValueError(f"large-channel carrier declares forbidden {flag}")
    carrier["runtime_uses_future"] = False
    carrier["runtime_uses_registered_events"] = False
    close = pd.to_numeric(carrier["close"], errors="raise").to_numpy(dtype=float)
    high = pd.to_numeric(carrier["high"], errors="raise").to_numpy(dtype=float)
    low = pd.to_numeric(carrier["low"], errors="raise").to_numpy(dtype=float)
    if not np.isfinite(close).all() or np.any(close <= 0.0):
        raise ValueError("large-channel closes must be finite and positive")

    baseline = build_v59_multiscale_middle_v56(
        carrier,
        base_spec,
        w72_spec=w72_spec,
        w72_recovery_width_fraction=w72_recovery_width_fraction,
        dynamic_parameters=False,
    )
    windows = spec.fast_windows_bars + spec.parent_windows_bars
    channel = attach_v56_independent_channel_features(
        carrier,
        SteepCrashV56Spec(
            channel_windows_bars=windows,
            channel_minimum_fit_r2=min(
                spec.fast_minimum_fit_r2,
                spec.parent_minimum_fit_r2,
            ),
        ),
    )
    log_close = np.log(close)
    size = len(carrier)

    qualified: dict[int, np.ndarray] = {}
    candidate: dict[int, np.ndarray] = {}
    slope: dict[int, np.ndarray] = {}
    upper: dict[int, np.ndarray] = {}
    lower: dict[int, np.ndarray] = {}
    score: dict[int, np.ndarray] = {}
    family: dict[int, str] = {}

    for window in windows:
        prefix = f"exit_channel_w{window}"
        local_slope = channel[f"{prefix}_slope_log_per_bar"].to_numpy(dtype=float)
        local_r2 = channel[f"{prefix}_fit_r2"].to_numpy(dtype=float)
        local_upper = channel[f"{prefix}_upper_rail"].to_numpy(dtype=float)
        local_lower = channel[f"{prefix}_lower_rail"].to_numpy(dtype=float)
        stride = 1 if window in spec.fast_windows_bars else spec.parent_path_sampling_stride_bars
        efficiency, tail_share, sign_flip = _prior_path_attributes(
            log_close,
            window=window,
            stride=stride,
        )
        total_down = -local_slope * float(window - 1)
        centre = np.sqrt(local_upper * local_lower)
        common = (
            np.isfinite(local_slope)
            & np.isfinite(local_r2)
            & np.isfinite(local_upper)
            & np.isfinite(local_lower)
            & np.isfinite(efficiency)
            & np.isfinite(tail_share)
            & (local_slope < 0.0)
            & (tail_share <= spec.maximum_single_bar_decline_share)
            & (close <= centre)
        )
        if window in spec.fast_windows_bars:
            local_family = "fast"
            local_qualified = (
                common
                & (local_slope <= -spec.fast_minimum_down_slope_log_per_15m)
                & (local_r2 >= spec.fast_minimum_fit_r2)
                & (efficiency >= spec.fast_minimum_path_efficiency)
            )
        else:
            local_family = "parent"
            local_qualified = (
                common
                & (total_down >= spec.parent_minimum_total_down_displacement_log)
                & (local_r2 >= spec.parent_minimum_fit_r2)
                & (efficiency >= spec.parent_minimum_scale_adjusted_path_efficiency)
            )
        prior = np.zeros(size, dtype=bool)
        if size > 1:
            prior[1:] = local_qualified[:-1]
        qualified[window] = local_qualified
        candidate[window] = local_qualified & ~prior
        slope[window] = local_slope
        upper[window] = local_upper
        lower[window] = local_lower
        score[window] = total_down * efficiency * np.maximum(local_r2, 0.0)
        family[window] = local_family
        baseline[f"large_channel_w{window}_path_efficiency"] = efficiency
        baseline[f"large_channel_w{window}_tail_decline_dominance"] = tail_share
        baseline[f"large_channel_w{window}_sign_flip_rate"] = sign_flip
        baseline[f"large_channel_w{window}_fit_r2"] = local_r2
        baseline[f"large_channel_w{window}_slope_log_per_15m"] = local_slope
        baseline[f"large_channel_w{window}_upper_rail"] = local_upper
        baseline[f"large_channel_w{window}_lower_rail"] = local_lower
        baseline[f"large_channel_w{window}_fitted_total_down_displacement"] = total_down
        baseline[f"large_channel_w{window}_qualified"] = local_qualified
        baseline[f"large_channel_w{window}_candidate_trigger"] = candidate[window]

    decision_risk = np.zeros(size, dtype=bool)
    entry_trigger = np.zeros(size, dtype=bool)
    failed_rebound_reentry_trigger = np.zeros(size, dtype=bool)
    entry_route_values = np.full(size, "none", dtype=object)
    promotion_trigger = np.zeros(size, dtype=bool)
    exit_trigger = np.zeros(size, dtype=bool)
    exit_route_values = np.full(size, "none", dtype=object)
    authority_family_values = np.full(size, "none", dtype=object)
    authority_window_values = np.zeros(size, dtype=np.int64)
    live_boundary_values = np.full(size, np.nan, dtype=float)
    rebound_watch_active_values = np.zeros(size, dtype=bool)
    rebound_watch_floor_values = np.full(size, np.nan, dtype=float)
    rebound_watch_success_boundary_values = np.full(size, np.nan, dtype=float)
    active = False
    authority_family = "none"
    authority_window = 0
    authority_slope = np.nan
    authority_upper = np.nan
    authority_lower = np.nan
    anchor = -1
    above_boundary_age = 0
    pulse_trough_close = np.inf
    rebound_watch_active = False
    rebound_watch_floor = np.nan
    rebound_watch_anchor = -1
    rebound_watch_slope = np.nan
    rebound_watch_upper = np.nan
    rebound_watch_lower = np.nan

    def adopt(location: int, window: int, target_family: str) -> None:
        nonlocal active, authority_family, authority_window
        nonlocal authority_slope, authority_upper, authority_lower
        nonlocal anchor, above_boundary_age
        nonlocal pulse_trough_close, rebound_watch_active
        nonlocal rebound_watch_floor, rebound_watch_anchor
        nonlocal rebound_watch_slope, rebound_watch_upper, rebound_watch_lower
        active = True
        authority_family = target_family
        authority_window = int(window)
        authority_slope = float(slope[window][location])
        authority_upper = float(upper[window][location])
        authority_lower = float(lower[window][location])
        anchor = location
        above_boundary_age = 0
        pulse_trough_close = float(close[location])
        rebound_watch_active = False
        rebound_watch_floor = np.nan
        rebound_watch_anchor = -1
        rebound_watch_slope = np.nan
        rebound_watch_upper = np.nan
        rebound_watch_lower = np.nan

    for location in range(size):
        parent_live = [window for window in spec.parent_windows_bars if qualified[window][location]]
        fast_live = [window for window in spec.fast_windows_bars if qualified[window][location]]
        exited_now = False
        if active and authority_family == "fast" and spec.parent_promotion_enabled and parent_live:
            selected = max(parent_live, key=lambda item: score[item][location])
            adopt(location, selected, "parent")
            promotion_trigger[location] = True

        if active:
            if authority_family == "fast":
                pulse_trough_close = min(
                    pulse_trough_close,
                    float(close[location]),
                )
            elapsed = location - anchor
            projected_upper = authority_upper * np.exp(authority_slope * elapsed)
            projected_lower = authority_lower * np.exp(authority_slope * elapsed)
            fraction = spec.fast_exit_inner_band_fraction if authority_family == "fast" else spec.parent_exit_inner_band_fraction
            boundary = _log_boundary(projected_upper, projected_lower, fraction)
            live_boundary_values[location] = boundary
            above_boundary_age = above_boundary_age + 1 if close[location] > boundary else 0
            if spec.fast_family_reset_release_mode == "first_up_close":
                rebound_confirmed = location > 0 and close[location] > close[location - 1]
            elif spec.fast_family_reset_release_mode == "two_up_closes":
                rebound_confirmed = location > 1 and close[location] > close[location - 1] and close[location - 1] > close[location - 2]
            else:
                rebound_confirmed = location > 0 and close[location] > high[location - 1]
            family_reset_release = bool(
                authority_family == "fast" and spec.fast_family_reset_release_enabled and not fast_live and rebound_confirmed
            )
            boundary_release = above_boundary_age >= spec.upward_break_confirmation_bars
            if family_reset_release or boundary_release:
                released_fast_pulse = authority_family == "fast"
                released_anchor = anchor
                released_slope = authority_slope
                released_upper = authority_upper
                released_lower = authority_lower
                released_floor = pulse_trough_close
                active = False
                authority_family = "none"
                authority_window = 0
                authority_slope = np.nan
                authority_upper = np.nan
                authority_lower = np.nan
                anchor = -1
                above_boundary_age = 0
                exit_trigger[location] = True
                exit_route_values[location] = "fast_family_reset_release" if family_reset_release else "frozen_channel_boundary_break"
                if released_fast_pulse and spec.fast_failed_rebound_reentry_enabled:
                    rebound_watch_active = True
                    rebound_watch_floor = released_floor
                    rebound_watch_anchor = released_anchor
                    rebound_watch_slope = released_slope
                    rebound_watch_upper = released_upper
                    rebound_watch_lower = released_lower
                exited_now = True

        if not active and not exited_now:
            failed_rebound_fresh: list[int] = []
            if rebound_watch_active:
                watch_elapsed = location - rebound_watch_anchor
                watch_upper = rebound_watch_upper * np.exp(rebound_watch_slope * watch_elapsed)
                watch_lower = rebound_watch_lower * np.exp(rebound_watch_slope * watch_elapsed)
                watch_boundary = _log_boundary(
                    watch_upper,
                    watch_lower,
                    0.50,
                )
                rebound_watch_success_boundary_values[location] = watch_boundary
                rebound_failed = False
                if close[location] > watch_boundary:
                    rebound_watch_active = False
                elif spec.fast_failed_rebound_reentry_mode == "pulse_trough_break":
                    rebound_failed = location > 0 and close[location] < rebound_watch_floor and close[location] < close[location - 1]
                else:
                    rebound_failed = location > 0 and close[location] < low[location - 1]
                if rebound_watch_active and rebound_failed:
                    failed_rebound_fresh = [
                        window
                        for window in spec.fast_windows_bars
                        if np.isfinite(slope[window][location])
                        and slope[window][location] < 0.0
                        and np.isfinite(upper[window][location])
                        and np.isfinite(lower[window][location])
                    ]
            parent_fresh = [window for window in spec.parent_windows_bars if candidate[window][location]]
            fast_fresh = [window for window in spec.fast_windows_bars if candidate[window][location]]
            if parent_fresh and not spec.parent_requires_fast_seed:
                selected = max(parent_fresh, key=lambda item: score[item][location])
                adopt(location, selected, "parent")
                entry_trigger[location] = True
                entry_route_values[location] = "parent_fresh_edge"
            elif failed_rebound_fresh:
                selected = min(
                    failed_rebound_fresh,
                    key=lambda item: slope[item][location],
                )
                adopt(location, selected, "fast")
                entry_trigger[location] = True
                failed_rebound_reentry_trigger[location] = True
                entry_route_values[location] = "failed_rebound_prior_low_break"
            elif fast_fresh:
                selected = max(fast_fresh, key=lambda item: score[item][location])
                adopt(location, selected, "fast")
                entry_trigger[location] = True
                entry_route_values[location] = "fast_fresh_edge"

        decision_risk[location] = active
        rebound_watch_active_values[location] = rebound_watch_active
        if rebound_watch_active:
            rebound_watch_floor_values[location] = rebound_watch_floor
        if active:
            authority_family_values[location] = authority_family
            authority_window_values[location] = authority_window
            if not np.isfinite(live_boundary_values[location]):
                fraction = spec.fast_exit_inner_band_fraction if authority_family == "fast" else spec.parent_exit_inner_band_fraction
                live_boundary_values[location] = _log_boundary(
                    authority_upper,
                    authority_lower,
                    fraction,
                )

    executable_risk = np.r_[True, decision_risk[:-1]]
    baseline_decision = baseline["v59_decision_risk_active_for_next_bar"].to_numpy(dtype=bool)
    combined_decision = baseline_decision | decision_risk
    combined_executable = np.r_[True, combined_decision[:-1]]
    fast_stack = np.vstack([qualified[window] for window in spec.fast_windows_bars])
    parent_stack = np.vstack([qualified[window] for window in spec.parent_windows_bars])
    baseline["large_channel_fast_qualified_count"] = fast_stack.sum(axis=0)
    baseline["large_channel_parent_qualified_count"] = parent_stack.sum(axis=0)
    baseline["large_channel_entry_trigger"] = entry_trigger
    baseline["large_channel_entry_route"] = entry_route_values
    baseline["large_channel_failed_rebound_reentry_trigger"] = failed_rebound_reentry_trigger
    baseline["large_channel_parent_promotion_trigger"] = promotion_trigger
    baseline["large_channel_exit_trigger"] = exit_trigger
    baseline["large_channel_exit_route"] = exit_route_values
    baseline["large_channel_authority_family"] = authority_family_values
    baseline["large_channel_authority_window_bars"] = authority_window_values
    baseline["large_channel_live_exit_boundary"] = live_boundary_values
    baseline["large_channel_rebound_watch_active"] = rebound_watch_active_values
    baseline["large_channel_rebound_watch_floor"] = rebound_watch_floor_values
    baseline["large_channel_rebound_watch_success_boundary"] = rebound_watch_success_boundary_values
    baseline["large_channel_decision_risk_active_for_next_bar"] = decision_risk
    baseline["large_channel_executable_risk_active"] = executable_risk
    baseline["v59_large_channel_route_added_risk"] = decision_risk & ~baseline_decision
    baseline["v59_large_channel_decision_risk_active_for_next_bar"] = combined_decision
    baseline["v59_large_channel_executable_risk_active"] = combined_executable
    baseline["v59_large_channel_executable_long_position"] = (~combined_executable).astype(float)
    baseline["runtime_uses_future"] = False
    baseline["runtime_uses_registered_events"] = False
    baseline.attrs["field_labels_zh"] = {
        **baseline.attrs.get("field_labels_zh", {}),
        **FIELD_LABELS_ZH,
    }
    baseline.attrs["formula_contract"] = v59_large_channel_formula_contract(spec)
    return baseline


def v59_large_channel_formula_contract(
    spec: V59LargeChannelParentSpec = V59LargeChannelParentSpec(),
) -> dict[str, object]:
    """Expose the formula, parameter, K-line attribute, and authority graph."""

    return {
        "schema_id": "risk_off_v59_large_channel_parent@1.0",
        "strategy_version": "V59_large_channel_parent_prototype",
        "base_strategy": "V59_static_parameters",
        "spec": asdict(spec),
        "formula_computation_graph": {
            "prior_channel": "OLS(log_close[t-W:t])",
            "slope_per_trading_day": "16*OLS_slope_log_per_15m",
            "fitted_total_down_displacement": "-OLS_slope*(W-1)",
            "path_efficiency": "abs(sum(r))/sum(abs(r)) on prior same-scale path",
            "tail_decline_dominance": "max(-r,0)/prior_net_down_displacement",
            "fast_qualification": "W12/W24 steep slope AND PE AND R2 AND tail gate",
            "parent_qualification": "W128/W256 total displacement AND scale-adjusted PE AND R2 AND tail gate",
            "authority": "fast causally seeds protection; parent may promote and retain until frozen parent centreline break",
            "crash_rebound_handoff": (
                "when enabled, an upward bar while all W12/W24 qualifications are reset "
                "ends the current pulse; "
                "a later fresh qualification edge creates a new independent channel"
            ),
            "failed_rebound_reentry": (
                "after release, the old frozen centreline only bounds a rebound-watch context; "
                "a close below the completed pulse trough starts a newly fitted fast channel"
            ),
            "composition": "V59_static_risk OR independent_large_channel_risk",
            "execution_lag_bars": 1,
        },
        "parameter_to_kline_attribute_mapping": [
            {
                "parameter": "fast_minimum_down_slope_log_per_15m",
                "attributes": ["direction_slope", "downside_impulse"],
                "role": "短尺度是否足够陡",
            },
            {
                "parameter": "parent_minimum_total_down_displacement_log",
                "attributes": ["direction_slope", "directional_run_age"],
                "role": "低斜率长周期是否形成足够累计位移",
            },
            {
                "parameter": "parent_requires_fast_seed",
                "attributes": ["breakout_followthrough", "directional_run_age"],
                "role": "父通道只接管已被短尺度下跌因果启动的风险，不独立预测终局级别",
            },
            {
                "parameter": "parent_promotion_enabled",
                "attributes": ["group_delay_to_run_age", "breakout_followthrough"],
                "role": "架构消融开关；验证父通道接管是否优于短通道独立执行",
            },
            {
                "parameter": "fast_family_reset_release_enabled",
                "attributes": [
                    "multi_window_qualification_reset",
                    "bar_direction",
                    "breakout_followthrough",
                ],
                "role": "W12/W24全家族复位后的首根上涨K线结束本次暴跌脉冲；再下跌必须新建通道",
            },
            {
                "parameter": "fast_family_reset_release_mode",
                "attributes": [
                    "bar_direction",
                    "consecutive_direction",
                    "prior_high_break",
                ],
                "role": "只比较无数值参数的反弹图形确认语义",
            },
            {
                "parameter": "fast_failed_rebound_reentry_enabled",
                "attributes": [
                    "prior_pulse_trough_break",
                    "prior_low_break",
                    "frozen_channel_reclaim",
                    "direction_slope",
                ],
                "role": "反弹未突破旧中轨前再创新低，立即以当时K线新建快速通道",
            },
            {
                "parameter": "fast_failed_rebound_reentry_mode",
                "attributes": [
                    "prior_pulse_trough_break",
                    "prior_low_break",
                ],
                "role": "只比较反弹失败的无数值图形语义",
            },
            {
                "parameter": "*_minimum_path_efficiency",
                "attributes": ["path_efficiency", "noise_ratio", "sign_flip_rate"],
                "role": "通道是否会被来回切碎；同源量只计一票",
            },
            {
                "parameter": "*_minimum_fit_r2",
                "attributes": ["rolling_regression_r2", "regression_residual_autocorrelation"],
                "role": "OLS通道是否为可信的主路径",
            },
            {
                "parameter": "maximum_single_bar_decline_share",
                "attributes": ["tail_energy_concentration", "jrr"],
                "role": "排除单棒跳变主导且容易尖底反转的伪通道",
            },
        ],
        "runtime_uses_future": False,
        "runtime_uses_registered_events": False,
        "production_authority": False,
        "sealed_2021_plus_authority": False,
    }


__all__ = [
    "FIELD_LABELS_ZH",
    "V59LargeChannelParentSpec",
    "build_v59_large_channel_parent",
    "v59_large_channel_formula_contract",
]
