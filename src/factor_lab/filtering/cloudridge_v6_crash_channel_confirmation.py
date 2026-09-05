"""Causal descending-channel confirmation for the GreenWave V6 crash watch.

The crash watch answers only whether a material decline deserves observation.
This module answers a different question: has the *latest* descending channel
been left for long enough to call the move a rebound rather than a one-bar
bounce?

Every channel at bar ``t`` is fitted with bars strictly before ``t``.  A wide
64-bar channel is preferred initially.  A valid 32/16-bar channel may take
over only when it is materially steeper, which represents acceleration.  An
upside departure becomes a confirmation only after it remains above the
projected upper rail for a frozen fraction of the channel's own causal
within-channel oscillation half-cycle.  The centreline-detrended residual is
only the mathematical carrier used to estimate that clock.  The decision at
``t`` is executable on ``t + 1``.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Final, cast

import numpy as np
import pandas as pd

from factor_lab.filtering._cloudridge_causal_channel_math import (
    _prior_rolling_ols,
)

LAYER_ID: Final = "cloudridge_v6_crash_descending_channel_confirmation"
LAYER_VERSION: Final = "1.3-research-channel-maturity"


@dataclass(frozen=True, slots=True)
class CrashDescendingChannelSpec:
    """Low-freedom geometry for a crash-watch rebound confirmation."""

    channel_windows_bars: tuple[int, ...] = (64, 32, 16)
    minimum_fit_r2: float = 0.10
    minimum_normalized_down_slope: float = 0.75
    channel_band_sigma: float = 1.0
    cycle_deadband_sigma: float = 0.35
    minimum_half_cycle_bars: int = 4
    maximum_half_cycle_fraction: float = 0.50
    minimum_observed_half_cycle_gaps: int = 2
    minimum_slope_upgrade_ratio: float = 1.15
    minimum_promotion_age_bars: int = 1
    minimum_promotion_age_fraction_of_window: float = 0.0
    minimum_recovery_channel_widths_before_rearm: float = 1.0
    effective_break_fraction_of_half_cycle: float = 1.0
    production_authority: bool = False

    def __post_init__(self) -> None:
        if tuple(sorted(self.channel_windows_bars, reverse=True)) != self.channel_windows_bars:
            raise ValueError("channel windows must be unique and ordered wide to narrow")
        if len(set(self.channel_windows_bars)) != len(self.channel_windows_bars):
            raise ValueError("channel windows must be unique")
        if not self.channel_windows_bars or min(self.channel_windows_bars) < 8:
            raise ValueError("every channel window must contain at least 8 bars")
        if not 0.0 <= self.minimum_fit_r2 <= 1.0:
            raise ValueError("minimum_fit_r2 must be in [0, 1]")
        if self.minimum_normalized_down_slope <= 0.0:
            raise ValueError("minimum normalized down slope must be positive")
        if self.channel_band_sigma < 0.0:
            raise ValueError("channel band sigma cannot be negative")
        if self.minimum_half_cycle_bars < 2:
            raise ValueError("minimum half cycle must be at least two bars")
        if not 0.0 < self.maximum_half_cycle_fraction <= 0.5:
            raise ValueError("maximum half-cycle fraction must be in (0, 0.5]")
        if self.minimum_observed_half_cycle_gaps < 1:
            raise ValueError("a visible channel needs at least one observed half-cycle gap")
        if self.minimum_slope_upgrade_ratio <= 1.0:
            raise ValueError("slope upgrade ratio must exceed one")
        if self.minimum_promotion_age_bars < 1:
            raise ValueError("minimum promotion age must be positive")
        if not 0.0 <= self.minimum_promotion_age_fraction_of_window <= 1.0:
            raise ValueError("promotion age fraction must be in [0, 1]")
        if self.minimum_recovery_channel_widths_before_rearm < 0.0:
            raise ValueError("rearm recovery width multiple cannot be negative")
        if not 0.0 < self.effective_break_fraction_of_half_cycle <= 1.0:
            raise ValueError("effective break fraction must be in (0, 1]")
        if self.production_authority:
            raise ValueError("decision-death channel research cannot hold production authority")

    @property
    def spec_id(self) -> str:
        windows = "_".join(str(value) for value in self.channel_windows_bars)
        fraction = f"{self.effective_break_fraction_of_half_cycle:.4f}".rstrip("0").rstrip(".")
        return f"ols_w{windows}_effective_{fraction}_half_cycle"

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload.update(layer_id=LAYER_ID, version=LAYER_VERSION, spec_id=self.spec_id)
        return payload


def _estimate_prior_observed_half_cycle(
    values: np.ndarray,
    *,
    window_bars: int,
    slope: np.ndarray,
    prediction: np.ndarray,
    residual_sigma: np.ndarray,
    spec: CrashDescendingChannelSpec,
) -> tuple[np.ndarray, np.ndarray]:
    """Estimate a cycle only when the prior path visibly oscillated.

    The generic channel engine deliberately has a neutral ``window / 4``
    fallback for risk-state continuity.  That fallback is not admissible for
    this visual rebound experiment: if alternating residual swings were not
    observed, the code is not allowed to claim that a channel cycle exists.
    """

    half_cycle = np.full(len(values), np.nan, dtype=float)
    observed_gaps = np.zeros(len(values), dtype=np.int64)
    x = np.arange(window_bars, dtype=float)
    maximum = max(
        spec.minimum_half_cycle_bars,
        int(np.floor(window_bars * spec.maximum_half_cycle_fraction)),
    )
    for position in range(window_bars, len(values)):
        current_slope = slope[position]
        current_prediction = prediction[position]
        sigma = residual_sigma[position]
        if not (
            np.isfinite(current_slope)
            and np.isfinite(current_prediction)
            and np.isfinite(sigma)
        ):
            continue
        segment = values[position - window_bars : position]
        fitted = current_prediction + current_slope * (
            x - float(window_bars)
        )
        residual = segment - fitted
        deadband = max(float(sigma) * spec.cycle_deadband_sigma, 1e-12)
        state = 0
        crossings: list[int] = []
        for offset, value in enumerate(residual):
            next_state = 1 if value >= deadband else (-1 if value <= -deadband else 0)
            if next_state == 0:
                continue
            if state and next_state != state:
                crossings.append(offset)
            state = next_state
        gaps = np.diff(np.asarray(crossings, dtype=float))
        gaps = gaps[gaps >= 1.0]
        observed_gaps[position] = len(gaps)
        if len(gaps) < spec.minimum_observed_half_cycle_gaps:
            continue
        estimate = float(np.median(gaps[-4:]))
        half_cycle[position] = float(
            np.clip(
                round(estimate),
                spec.minimum_half_cycle_bars,
                maximum,
            )
        )
    return half_cycle, observed_gaps


def build_prior_descending_channel_features(
    log_close: pd.Series,
    spec: CrashDescendingChannelSpec = CrashDescendingChannelSpec(),
) -> pd.DataFrame:
    """Return prior-only regression channels and their own oscillation clocks."""

    if not isinstance(log_close.index, pd.DatetimeIndex):
        raise TypeError("log_close must use a DatetimeIndex")
    values = cast(pd.Series, pd.to_numeric(log_close, errors="coerce"))
    if values.isna().any() or not np.isfinite(values.to_numpy(float)).all():
        raise ValueError("log_close must be finite")
    array = values.to_numpy(float)
    output = pd.DataFrame(index=values.index)
    for window in spec.channel_windows_bars:
        fit = _prior_rolling_ols(array, window)
        sigma = np.maximum(fit.residual_sigma, np.finfo(float).eps)
        normalized = fit.slope * float(window - 1) / sigma
        half_cycle, observed_cycle_gaps = _estimate_prior_observed_half_cycle(
            array,
            window_bars=window,
            slope=fit.slope,
            prediction=fit.prediction,
            residual_sigma=fit.residual_sigma,
            spec=spec,
        )
        geometry_valid = (
            np.isfinite(fit.prediction)
            & np.isfinite(fit.slope)
            & np.isfinite(fit.r2)
            & (fit.slope < 0.0)
            & (fit.r2 >= spec.minimum_fit_r2)
            & (normalized <= -spec.minimum_normalized_down_slope)
        )
        cycle_qualified = geometry_valid & np.isfinite(half_cycle)
        prefix = f"channel_w{window}"
        # Geometry and confirmation clock are deliberately separate.  A
        # smooth decline can have a perfectly valid descending channel while
        # the current carrier does not expose enough residual oscillation to
        # estimate its half-cycle.  Calling that case "no channel" confuses a
        # carrier/clock limitation with missing price geometry.
        output[f"{prefix}_geometry_valid"] = geometry_valid
        output[f"{prefix}_cycle_qualified"] = cycle_qualified
        # Backward-compatible alias used by the confirmation lifecycle.  An
        # entry cannot be confirmed until both geometry and a causal clock are
        # available.
        output[f"{prefix}_valid"] = cycle_qualified
        output[f"{prefix}_slope_log_per_bar"] = fit.slope
        output[f"{prefix}_fit_r2"] = fit.r2
        output[f"{prefix}_normalized_slope_span"] = normalized
        output[f"{prefix}_upper_rail"] = np.exp(
            fit.prediction + spec.channel_band_sigma * sigma
        )
        output[f"{prefix}_lower_rail"] = np.exp(
            fit.prediction - spec.channel_band_sigma * sigma
        )
        output[f"{prefix}_half_cycle_bars"] = half_cycle
        # User-facing alias: this is the half-cycle of price oscillation
        # around the descending channel centreline.  ``residual`` is only the
        # mathematical detrending step used to observe that oscillation.
        output[f"{prefix}_oscillation_half_cycle_bars"] = half_cycle
        output[f"{prefix}_observed_half_cycle_gaps"] = observed_cycle_gaps
    output.attrs.update(
        no_lookahead=True,
        formula_contract="bar_t_channel_uses_only_bars_strictly_before_t",
        layer_id=LAYER_ID,
        version=LAYER_VERSION,
    )
    return output


def build_latest_descending_channel_confirmation(
    close: pd.Series,
    crash_watch_active: pd.Series,
    channel_features: pd.DataFrame,
    spec: CrashDescendingChannelSpec = CrashDescendingChannelSpec(),
    crash_rearm_trigger: pd.Series | None = None,
) -> pd.DataFrame:
    """Track the latest accelerating down-channel and confirm its valid break."""

    if not close.index.equals(crash_watch_active.index) or not close.index.equals(channel_features.index):
        raise ValueError("close, crash watch, and channel features must align exactly")
    prices = cast(pd.Series, pd.to_numeric(close, errors="coerce"))
    if prices.isna().any() or prices.le(0.0).any():
        raise ValueError("close must be finite and positive")
    watch = crash_watch_active.fillna(False).astype(bool).to_numpy(bool)
    if crash_rearm_trigger is None:
        alerts = np.zeros(len(close), dtype=bool)
    else:
        if not close.index.equals(crash_rearm_trigger.index):
            raise ValueError("crash rearm trigger must align with close")
        alerts = crash_rearm_trigger.fillna(False).astype(bool).to_numpy(bool)
    price_values = prices.to_numpy(float)
    size = len(prices)

    confirmation = np.zeros(size, dtype=bool)
    channel_available = np.zeros(size, dtype=bool)
    geometry_available = np.zeros(size, dtype=bool)
    promotion = np.zeros(size, dtype=bool)
    promotion_candidate_window = np.zeros(size, dtype=np.int64)
    promotion_candidate_age = np.zeros(size, dtype=np.int64)
    promotion_required_age = np.zeros(size, dtype=np.int64)
    refit = np.zeros(size, dtype=bool)
    rearm = np.zeros(size, dtype=bool)
    departure_onset = np.zeros(size, dtype=bool)
    departure_failed = np.zeros(size, dtype=bool)
    departure_attempt_ordinal = np.zeros(size, dtype=np.int64)
    channel_episode = np.zeros(size, dtype=np.int64)
    confirmation_ordinal = np.zeros(size, dtype=np.int64)
    active_window = np.zeros(size, dtype=np.int64)
    active_slope = np.full(size, np.nan, dtype=float)
    active_upper = np.full(size, np.nan, dtype=float)
    active_lower = np.full(size, np.nan, dtype=float)
    active_half_cycle = np.zeros(size, dtype=np.int64)
    outside_age = np.zeros(size, dtype=np.int64)
    required_age = np.zeros(size, dtype=np.int64)

    active = False
    emitted = False
    current_window = 0
    current_slope = float("nan")
    anchor_upper = float("nan")
    anchor_lower = float("nan")
    current_half_cycle = 0
    anchor_position = -1
    current_outside_age = 0
    current_channel_episode = 0
    current_confirmation_ordinal = 0
    current_departure_attempt_ordinal = 0
    last_confirmation_position = -1
    rearm_pending = False
    last_confirmation_price = float("nan")
    last_confirmation_channel_width_log = float("nan")
    recovery_high_after_confirmation = float("nan")
    pending_promotion_window = 0
    pending_promotion_age = 0

    def candidate_valid(position: int, window: int) -> bool:
        return bool(channel_features[f"channel_w{window}_valid"].iloc[position])

    def geometry_valid(position: int, window: int) -> bool:
        column = f"channel_w{window}_geometry_valid"
        if column not in channel_features:
            # Compatibility for hand-built/synthetic feature frames and old
            # frozen ledgers.  New production research always emits the
            # explicit geometry column.
            column = f"channel_w{window}_valid"
        return bool(channel_features[column].iloc[position])

    def activate(
        position: int,
        window: int,
        *,
        is_promotion: bool,
        is_refit: bool = False,
    ) -> None:
        nonlocal active, current_window, current_slope, anchor_upper, anchor_lower
        nonlocal current_half_cycle, anchor_position, current_outside_age
        active = True
        current_window = window
        current_slope = float(
            channel_features[f"channel_w{window}_slope_log_per_bar"].iloc[position]
        )
        anchor_upper = float(
            channel_features[f"channel_w{window}_upper_rail"].iloc[position]
        )
        anchor_lower = float(
            channel_features[f"channel_w{window}_lower_rail"].iloc[position]
        )
        current_half_cycle = int(
            round(channel_features[f"channel_w{window}_half_cycle_bars"].iloc[position])
        )
        anchor_position = position
        current_outside_age = 0
        promotion[position] = is_promotion
        refit[position] = is_refit

    for position in range(size):
        if not watch[position]:
            active = False
            emitted = False
            current_window = 0
            current_outside_age = 0
            current_confirmation_ordinal = 0
            current_departure_attempt_ordinal = 0
            last_confirmation_position = -1
            rearm_pending = False
            last_confirmation_price = float("nan")
            last_confirmation_channel_width_log = float("nan")
            recovery_high_after_confirmation = float("nan")
            pending_promotion_window = 0
            pending_promotion_age = 0
            continue
        if position == 0 or not watch[position - 1]:
            active = False
            emitted = False
            current_window = 0
            current_outside_age = 0
            current_confirmation_ordinal = 0
            current_departure_attempt_ordinal = 0
            last_confirmation_position = -1
            rearm_pending = False
            last_confirmation_price = float("nan")
            last_confirmation_channel_width_log = float("nan")
            recovery_high_after_confirmation = float("nan")
            pending_promotion_window = 0
            pending_promotion_age = 0

        geometry_available[position] = any(
            geometry_valid(position, window)
            for window in spec.channel_windows_bars
        )

        if emitted and np.isfinite(last_confirmation_price):
            recovery_high_after_confirmation = (
                price_values[position]
                if not np.isfinite(recovery_high_after_confirmation)
                else max(recovery_high_after_confirmation, price_values[position])
            )
        recovery_widths = 0.0
        if (
            emitted
            and np.isfinite(recovery_high_after_confirmation)
            and np.isfinite(last_confirmation_channel_width_log)
            and last_confirmation_channel_width_log > 0.0
        ):
            recovery_widths = (
                math.log(
                    recovery_high_after_confirmation / last_confirmation_price
                )
                / last_confirmation_channel_width_log
            )

        if (
            emitted
            and last_confirmation_position >= 0
            and price_values[position] < price_values[last_confirmation_position]
            and recovery_widths
            >= spec.minimum_recovery_channel_widths_before_rearm
        ):
            rearm_pending = True

        candidates = [
            window
            for window in spec.channel_windows_bars
            if candidate_valid(position, window)
        ]
        if not active and not emitted and candidates:
            # Start with the widest observable channel.  Acceleration must earn
            # a promotion to a shorter, steeper geometry.
            activate(position, max(candidates), is_promotion=False)
            current_channel_episode += 1
        elif not active and emitted and rearm_pending:
            elapsed_after_confirmation = position - last_confirmation_position
            rebuilt = [
                window
                for window in candidates
                if window <= elapsed_after_confirmation
            ]
            if rebuilt:
                # Every bar in the refitted channel must be newer than the
                # prior confirmation; otherwise an old crash can be counted
                # repeatedly as several new channels.
                emitted = False
                rearm_pending = False
                rearm[position] = True
                activate(position, max(rebuilt), is_promotion=False)
                current_channel_episode += 1
        elif active:
            # A channel is a live description of the decline, not a line
            # frozen at the first bar where it became observable.  Keep
            # refitting the same scale while price has not begun an upside
            # departure.  Once the first outside close appears, freeze the
            # last intact channel so the rail cannot chase the rebound.
            if current_outside_age == 0:
                steeper = [
                    window
                    for window in candidates
                    if window < current_window
                    and float(
                        channel_features[
                            f"channel_w{window}_slope_log_per_bar"
                        ].iloc[position]
                    )
                    <= current_slope * spec.minimum_slope_upgrade_ratio
                ]
                if steeper:
                    # Promote one adjacent observable scale at a time.  This
                    # avoids letting a single noisy fine fit erase the
                    # established channel.  The proposed finer channel must
                    # also persist for its scale-aware maturity horizon;
                    # until then the established wider channel remains the
                    # authoritative break boundary.
                    proposed_window = max(steeper)
                    if proposed_window == pending_promotion_window:
                        pending_promotion_age += 1
                    else:
                        pending_promotion_window = proposed_window
                        pending_promotion_age = 1
                    required_promotion_age = max(
                        spec.minimum_promotion_age_bars,
                        int(
                            math.ceil(
                                proposed_window
                                * spec.minimum_promotion_age_fraction_of_window
                            )
                        ),
                    )
                    promotion_candidate_window[position] = proposed_window
                    promotion_candidate_age[position] = pending_promotion_age
                    promotion_required_age[position] = required_promotion_age
                    if pending_promotion_age >= required_promotion_age:
                        activate(position, proposed_window, is_promotion=True)
                        pending_promotion_window = 0
                        pending_promotion_age = 0
                    elif current_window in candidates:
                        activate(
                            position,
                            current_window,
                            is_promotion=False,
                            is_refit=True,
                        )
                elif current_window in candidates:
                    pending_promotion_window = 0
                    pending_promotion_age = 0
                    activate(
                        position,
                        current_window,
                        is_promotion=False,
                        is_refit=True,
                    )
                else:
                    pending_promotion_window = 0
                    pending_promotion_age = 0

        if not active:
            continue
        elapsed = position - anchor_position
        live_upper = anchor_upper * math.exp(current_slope * float(elapsed))
        live_lower = anchor_lower * math.exp(current_slope * float(elapsed))
        required = max(
            1,
            int(
                math.ceil(
                    current_half_cycle
                    * spec.effective_break_fraction_of_half_cycle
                )
            ),
        )
        prior_outside_age = current_outside_age
        if price_values[position] > live_upper:
            current_outside_age += 1
            departure_onset[position] = prior_outside_age == 0
            if departure_onset[position]:
                current_departure_attempt_ordinal += 1
            departure_attempt_ordinal[position] = current_departure_attempt_ordinal
        else:
            current_outside_age = 0
            departure_failed[position] = prior_outside_age > 0
            if departure_failed[position]:
                departure_attempt_ordinal[position] = (
                    current_departure_attempt_ordinal
                )
        channel_available[position] = True
        active_window[position] = current_window
        active_slope[position] = current_slope
        active_upper[position] = live_upper
        active_lower[position] = live_lower
        active_half_cycle[position] = current_half_cycle
        channel_episode[position] = current_channel_episode
        confirmation_ordinal[position] = current_confirmation_ordinal
        outside_age[position] = current_outside_age
        required_age[position] = required
        if current_outside_age >= required and not emitted:
            confirmation[position] = True
            emitted = True
            active = False
            current_confirmation_ordinal += 1
            confirmation_ordinal[position] = current_confirmation_ordinal
            last_confirmation_position = position
            last_confirmation_price = price_values[position]
            last_confirmation_channel_width_log = max(
                math.log(anchor_upper / anchor_lower),
                np.finfo(float).eps,
            )
            recovery_high_after_confirmation = price_values[position]
            pending_promotion_window = 0
            pending_promotion_age = 0

    output = channel_features.copy()
    output["crash_route_onset"] = alerts
    output["descending_channel_geometry_available"] = geometry_available
    output["cycle_qualified_descending_channel_available"] = channel_available
    # Historical name retained as an explicit compatibility alias.  It means
    # "usable by the cycle-confirmation engine", not merely geometric.
    output["descending_channel_available"] = channel_available
    output["channel_promotion_trigger"] = promotion
    output["channel_promotion_candidate_window_bars"] = promotion_candidate_window
    output["channel_promotion_candidate_age_bars"] = promotion_candidate_age
    output["channel_promotion_required_age_bars"] = promotion_required_age
    output["channel_refit_trigger"] = refit
    output["channel_rearm_trigger"] = rearm
    output["channel_episode_id"] = channel_episode
    output["confirmation_ordinal_in_watch"] = confirmation_ordinal
    output["active_channel_window_bars"] = active_window
    output["active_channel_slope_log_per_bar"] = active_slope
    output["active_channel_upper_rail"] = active_upper
    output["active_channel_lower_rail"] = active_lower
    output["active_channel_half_cycle_bars"] = active_half_cycle
    output["active_channel_oscillation_half_cycle_bars"] = active_half_cycle
    output["upside_channel_departure_onset"] = departure_onset
    output["upside_channel_departure_failed"] = departure_failed
    output["departure_attempt_ordinal_in_watch"] = departure_attempt_ordinal
    output["upside_outside_age_bars"] = outside_age
    output["effective_break_required_bars"] = required_age
    output["effective_upside_channel_break"] = confirmation
    output.attrs.update(
        no_lookahead=True,
        action_semantics="bar_t_close_confirms_bar_t_plus_1_execution",
        effective_break_definition=(
            "continuous closes above frozen latest-channel upper rail >= "
            "frozen fraction of its causal within-channel oscillation half-cycle"
        ),
        descending_channel_available_semantics=(
            "deprecated alias of cycle_qualified_descending_channel_available"
        ),
    )
    return output


__all__ = [
    "CrashDescendingChannelSpec",
    "LAYER_ID",
    "LAYER_VERSION",
    "build_latest_descending_channel_confirmation",
    "build_prior_descending_channel_features",
]
