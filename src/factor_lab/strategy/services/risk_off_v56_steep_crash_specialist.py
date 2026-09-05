"""Causal independent-channel crash-tip specialist for Risk-Off V56.

V56 owns one narrow job: mark a sharp, already-observable descending channel
until price effectively leaves its latest steeper authority.  W12, W24, W128
and W256 are evaluated independently on every 15-minute bar.  Runtime candidate
generation must never depend on the retired parent/child lifecycle's entry or
upgrade triggers.

All channel geometry at bar ``t`` is fitted from bars strictly before ``t`` by
``build_prior_descending_channel_features``.  A decision made at the close of
bar ``t`` becomes executable on ``t + 1``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from factor_lab.filtering.cloudridge_v6_crash_channel_confirmation import (
    CrashDescendingChannelSpec,
    build_prior_descending_channel_features,
)

FIELD_LABELS_ZH = {
    "steep_crash_candidate_trigger": "独立高斜率主跌通道新候选",
    "steep_crash_qualified_channel_count": "当前独立达标通道数",
    "steep_crash_entry_route": "高斜率主跌入场来源",
    "steep_crash_entry_slope_log_per_15m": "入场通道每15分钟对数斜率",
    "steep_crash_live_upper_rail": "冻结权威通道当前上轨",
    "steep_crash_upward_outside_age_bars": "向上突破通道上轨的连续棒数",
    "steep_crash_threshold_log_per_15m": "高斜率准入阈值",
    "decision_active_for_next_bar": "本棒收盘决定下一棒风险持有",
    "strategy_executable_active": "当前执行棒风险持有",
}


@dataclass(frozen=True, slots=True)
class SteepCrashV56Spec:
    """Low-freedom physical contract for the narrow V56 specialist."""

    channel_windows_bars: tuple[int, ...] = (12, 24, 128, 256)
    minimum_down_slope_log_per_15m: float = 0.001
    exit_inner_band_fraction: float = 0.5
    upward_break_confirmation_bars: int = 1
    channel_minimum_fit_r2: float = 0.10
    channel_minimum_normalized_down_slope: float = 0.75
    channel_band_sigma: float = 1.0

    def __post_init__(self) -> None:
        if not self.channel_windows_bars:
            raise ValueError("channel_windows_bars cannot be empty")
        if len(set(self.channel_windows_bars)) != len(self.channel_windows_bars):
            raise ValueError("channel_windows_bars must be unique")
        if min(self.channel_windows_bars) < 8:
            raise ValueError("every channel window must contain at least 8 bars")
        if self.minimum_down_slope_log_per_15m <= 0.0:
            raise ValueError("minimum_down_slope_log_per_15m must be positive")
        if not 0.0 <= self.exit_inner_band_fraction <= 1.0:
            raise ValueError("exit_inner_band_fraction must be in [0, 1]")
        if self.upward_break_confirmation_bars < 1:
            raise ValueError("upward_break_confirmation_bars must be positive")
        if not 0.0 <= self.channel_minimum_fit_r2 <= 1.0:
            raise ValueError("channel_minimum_fit_r2 must be in [0, 1]")
        if self.channel_minimum_normalized_down_slope <= 0.0:
            raise ValueError(
                "channel_minimum_normalized_down_slope must be positive"
            )
        if self.channel_band_sigma < 0.0:
            raise ValueError("channel_band_sigma cannot be negative")


def attach_v56_independent_channel_features(
    causal_ohlc: pd.DataFrame,
    spec: SteepCrashV56Spec = SteepCrashV56Spec(),
) -> pd.DataFrame:
    """Attach V56's self-owned prior-only channel geometry.

    This deliberately bypasses the old adaptive parent/child lifecycle.  The
    only shared dependency is the proven rolling-OLS geometry engine; it uses
    bars strictly before the decision bar.
    """

    required = {"timestamp", "open", "high", "low", "close"}
    missing = sorted(required.difference(causal_ohlc))
    if missing:
        raise KeyError(f"V56 OHLC carrier missing columns: {missing}")
    if (
        "runtime_uses_future" in causal_ohlc
        and bool(causal_ohlc["runtime_uses_future"].astype(bool).any())
    ):
        raise ValueError("V56 OHLC carrier declares future-dependent rows")
    if (
        "runtime_uses_registered_events" in causal_ohlc
        and bool(
            causal_ohlc["runtime_uses_registered_events"]
            .astype(bool)
            .any()
        )
    ):
        raise ValueError(
            "V56 OHLC carrier declares registered-event dependencies"
        )
    output = causal_ohlc.copy().reset_index(drop=True)
    timestamps = pd.DatetimeIndex(pd.to_datetime(output["timestamp"]))
    if not timestamps.is_monotonic_increasing or timestamps.has_duplicates:
        raise ValueError(
            "V56 OHLC timestamps must be strictly increasing and unique"
        )
    close = pd.to_numeric(output["close"], errors="coerce").to_numpy(
        dtype=float
    )
    if not np.isfinite(close).all() or np.any(close <= 0.0):
        raise ValueError("V56 closes must be finite and positive")
    channel_spec = CrashDescendingChannelSpec(
        channel_windows_bars=tuple(
            sorted(spec.channel_windows_bars, reverse=True)
        ),
        minimum_fit_r2=spec.channel_minimum_fit_r2,
        minimum_normalized_down_slope=(
            spec.channel_minimum_normalized_down_slope
        ),
        channel_band_sigma=spec.channel_band_sigma,
        minimum_half_cycle_bars=2,
        minimum_observed_half_cycle_gaps=1,
        production_authority=False,
    )
    observed = build_prior_descending_channel_features(
        pd.Series(np.log(close), index=timestamps, name="log_close"),
        channel_spec,
    ).reset_index(drop=True)
    for column in observed.columns:
        output[f"exit_{column}"] = observed[column].to_numpy()
    output["runtime_uses_future"] = False
    output["runtime_uses_registered_events"] = False
    return output


def _required_columns(spec: SteepCrashV56Spec) -> set[str]:
    required = {
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "runtime_uses_future",
        "runtime_uses_registered_events",
    }
    for window in spec.channel_windows_bars:
        prefix = f"exit_channel_w{window}"
        required.update(
            {
                f"{prefix}_geometry_valid",
                f"{prefix}_slope_log_per_bar",
                f"{prefix}_upper_rail",
                f"{prefix}_lower_rail",
            }
        )
    return required


def build_v56_steep_crash_specialist(
    causal_channel_ledger: pd.DataFrame,
    spec: SteepCrashV56Spec = SteepCrashV56Spec(),
) -> pd.DataFrame:
    """Build V56 from independent prior-only channel geometry.

    A per-window candidate is emitted when that window changes from
    non-qualified to qualified.  This edge contract prevents an already-broken
    stale fit from reopening the position on every following bar.  While a
    position is active, a newly qualified, steeper independent channel may
    replace the frozen exit authority without creating a second position.
    """

    missing = sorted(_required_columns(spec).difference(causal_channel_ledger))
    if missing:
        raise KeyError(f"causal channel ledger missing columns: {missing}")
    if bool(causal_channel_ledger["runtime_uses_future"].astype(bool).any()):
        raise ValueError("causal channel ledger declares future-dependent rows")
    if bool(
        causal_channel_ledger["runtime_uses_registered_events"].astype(bool).any()
    ):
        raise ValueError(
            "causal channel ledger declares registered-event dependencies"
        )

    panel = causal_channel_ledger.copy().reset_index(drop=True)
    timestamps = pd.to_datetime(panel["timestamp"])
    if not timestamps.is_monotonic_increasing or not timestamps.is_unique:
        raise ValueError(
            "causal channel timestamps must be strictly increasing and unique"
        )

    size = len(panel)
    close = panel["close"].to_numpy(dtype=float)
    windows = tuple(spec.channel_windows_bars)
    qualified_by_window: dict[int, np.ndarray] = {}
    eligible_by_window: dict[int, np.ndarray] = {}
    candidate_by_window: dict[int, np.ndarray] = {}
    slope_by_window: dict[int, np.ndarray] = {}
    upper_by_window: dict[int, np.ndarray] = {}
    lower_by_window: dict[int, np.ndarray] = {}
    for window in windows:
        prefix = f"exit_channel_w{window}"
        geometry_valid = panel[f"{prefix}_geometry_valid"].to_numpy(dtype=bool)
        slope = panel[f"{prefix}_slope_log_per_bar"].to_numpy(dtype=float)
        upper = panel[f"{prefix}_upper_rail"].to_numpy(dtype=float)
        lower = panel[f"{prefix}_lower_rail"].to_numpy(dtype=float)
        qualified = (
            geometry_valid
            & np.isfinite(slope)
            & np.isfinite(upper)
            & np.isfinite(lower)
            & (slope <= -spec.minimum_down_slope_log_per_15m)
        )
        entry_boundary = np.exp(
            (1.0 - spec.exit_inner_band_fraction) * np.log(upper)
            + spec.exit_inner_band_fraction * np.log(lower)
        )
        # A fit may remain steep after price has already rebounded.  Such a
        # stale fit describes the preceding crash but is not a live crash-tip
        # entry.  Requiring the current close to remain inside/below the exit
        # boundary removes the exact "red on the rebound" failure seen in the
        # cloud screenshot.
        eligible = qualified & (close <= entry_boundary)
        prior_qualified = np.zeros(size, dtype=bool)
        if size > 1:
            prior_qualified[1:] = qualified[:-1]
        qualified_by_window[window] = qualified
        eligible_by_window[window] = eligible
        # One independently qualified channel receives one entry opportunity.
        # If price rebounds and later falls while the same fit is still
        # qualified, reopening it would repeatedly paint one old channel and
        # turn V56 into a generic oscillation detector.  A second entry needs
        # a genuinely new qualification edge (or a newly qualified steeper
        # independent window).
        candidate_by_window[window] = eligible & ~prior_qualified
        slope_by_window[window] = slope
        upper_by_window[window] = upper
        lower_by_window[window] = lower

    qualified_count = np.sum(
        np.vstack([qualified_by_window[window] for window in windows]),
        axis=0,
    ).astype(np.int64)
    candidate_trigger = np.any(
        np.vstack([candidate_by_window[window] for window in windows]),
        axis=0,
    )

    decision_active = np.zeros(size, dtype=bool)
    entry_trigger = np.zeros(size, dtype=bool)
    exit_trigger = np.zeros(size, dtype=bool)
    authority_update_trigger = np.zeros(size, dtype=bool)
    episode_id_values = np.zeros(size, dtype=np.int64)
    live_upper_values = np.full(size, np.nan, dtype=float)
    outside_age_values = np.zeros(size, dtype=np.int64)
    entry_slope_values = np.full(size, np.nan, dtype=float)
    entry_route_values = np.full(size, "none", dtype=object)
    authority_source_values = np.full(size, "none", dtype=object)

    active = False
    episode_id = 0
    anchor_position = -1
    authority_slope = np.nan
    authority_upper = np.nan
    authority_lower = np.nan
    authority_window = 0
    upward_outside_age = 0

    for position in range(size):
        new_candidates = [
            window
            for window in windows
            if candidate_by_window[window][position]
        ]
        # Each window is independent.  When several become observable on the
        # same bar, the physically steepest one is the conservative authority.
        selected_window = (
            min(
                new_candidates,
                key=lambda window: slope_by_window[window][position],
            )
            if new_candidates
            else 0
        )

        if (
            active
            and selected_window
            and slope_by_window[selected_window][position] < authority_slope
        ):
            anchor_position = position
            authority_slope = float(
                slope_by_window[selected_window][position]
            )
            authority_upper = float(
                upper_by_window[selected_window][position]
            )
            authority_lower = float(
                lower_by_window[selected_window][position]
            )
            authority_window = int(selected_window)
            upward_outside_age = 0
            authority_update_trigger[position] = True

        if active:
            elapsed = position - anchor_position
            live_upper = authority_upper * np.exp(
                authority_slope * float(elapsed)
            )
            live_lower = authority_lower * np.exp(
                authority_slope * float(elapsed)
            )
            # Interpolate in log-price space.  0 means the outer upper rail;
            # 0.5 the channel centreline; 1 the lower rail.  Sharp-tip V56
            # deliberately uses an inner boundary so a rebound does not stay
            # coloured long after the crash impulse has ended.
            live_exit_boundary = float(
                np.exp(
                    (1.0 - spec.exit_inner_band_fraction)
                    * np.log(live_upper)
                    + spec.exit_inner_band_fraction
                    * np.log(live_lower)
                )
            )
            upward_outside_age = (
                upward_outside_age + 1
                if close[position] > live_exit_boundary
                else 0
            )
            live_upper_values[position] = live_exit_boundary
            outside_age_values[position] = upward_outside_age
            authority_source_values[position] = f"w{authority_window}"
            if (
                upward_outside_age
                >= spec.upward_break_confirmation_bars
            ):
                active = False
                exit_trigger[position] = True
                upward_outside_age = 0

        if not active and selected_window and not exit_trigger[position]:
            active = True
            episode_id += 1
            anchor_position = position
            authority_slope = float(
                slope_by_window[selected_window][position]
            )
            authority_upper = float(
                upper_by_window[selected_window][position]
            )
            authority_lower = float(
                lower_by_window[selected_window][position]
            )
            authority_window = int(selected_window)
            upward_outside_age = 0
            entry_trigger[position] = True
            entry_slope_values[position] = authority_slope
            entry_route_values[position] = (
                f"independent_w{selected_window}_qualification_edge"
            )
            live_upper_values[position] = float(
                np.exp(
                    (1.0 - spec.exit_inner_band_fraction)
                    * np.log(authority_upper)
                    + spec.exit_inner_band_fraction
                    * np.log(authority_lower)
                )
            )
            authority_source_values[position] = f"w{authority_window}"

        decision_active[position] = active
        if active:
            episode_id_values[position] = episode_id

    executable = np.zeros(size, dtype=bool)
    executable_episode_id = np.zeros(size, dtype=np.int64)
    if size > 1:
        executable[1:] = decision_active[:-1]
        executable_episode_id[1:] = episode_id_values[:-1]

    for window in windows:
        panel[f"steep_crash_w{window}_qualified"] = qualified_by_window[
            window
        ]
        panel[f"steep_crash_w{window}_entry_eligible"] = (
            eligible_by_window[window]
        )
        panel[f"steep_crash_w{window}_candidate_trigger"] = (
            candidate_by_window[window]
        )
    panel["steep_crash_candidate_trigger"] = candidate_trigger
    panel["steep_crash_qualified_channel_count"] = qualified_count
    panel["steep_crash_authority_update_trigger"] = (
        authority_update_trigger
    )
    panel["entry_trigger"] = entry_trigger
    panel["exit_trigger"] = exit_trigger
    panel["valid_upward_break_trigger"] = exit_trigger
    panel["valid_downward_break_trigger"] = False
    panel["decision_active_for_next_bar"] = decision_active
    panel["strategy_executable_active"] = executable
    panel["risk_episode_id"] = episode_id_values
    panel["executable_risk_episode_id"] = executable_episode_id
    panel["steep_crash_entry_route"] = entry_route_values
    panel["steep_crash_entry_slope_log_per_15m"] = entry_slope_values
    panel["steep_crash_live_upper_rail"] = live_upper_values
    panel["steep_crash_upward_outside_age_bars"] = outside_age_values
    panel["steep_crash_authority_source"] = authority_source_values
    panel["steep_crash_threshold_log_per_15m"] = (
        spec.minimum_down_slope_log_per_15m
    )
    panel["runtime_uses_future"] = False
    panel["runtime_uses_registered_events"] = False
    panel["action_semantics"] = (
        "bar_t_close_decides_bar_t_plus_1_position"
    )
    panel.attrs["field_labels_zh"] = FIELD_LABELS_ZH
    panel.attrs["formula_contract"] = {
        "scope": "high_slope_crash_tip_only",
        "candidate": (
            "independent per-window qualification edge over prior-only "
            "W12/W24/W128/W256 channel geometry"
        ),
        "candidate_uses_retired_parent_child_triggers": False,
        "low_slope_parent_authority": False,
        "parent_child_hierarchy": False,
        "exit": (
            "current close effectively breaks the frozen latest-steeper "
            "independent channel inner boundary"
        ),
        "execution": "bar_t_close_decides_bar_t_plus_1_position",
    }
    return panel


__all__ = [
    "FIELD_LABELS_ZH",
    "SteepCrashV56Spec",
    "attach_v56_independent_channel_features",
    "build_v56_steep_crash_specialist",
]
