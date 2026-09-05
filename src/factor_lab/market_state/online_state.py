"""Strictly causal multi-axis online state for market-state A1."""

from __future__ import annotations

import math
from bisect import bisect_left, bisect_right, insort
from dataclasses import asdict, dataclass
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.attributes import (
    NORMALIZATION_REFERENCE_ID,
    STATE_SMOOTHING_SCALE_ID,
)
from factor_lab.market_state.horizons import STANDARD_SESSION_MINUTES

NORMALIZATION_POLICY_VERSION: Final[str] = "robust_empirical_rank_v1"


@dataclass(frozen=True, slots=True)
class OnlineStatePolicyV1:
    """Versioned policy; no state threshold is hidden in implementation code."""

    version: str = "state_policy_v1"
    normalization_policy_version: str = NORMALIZATION_POLICY_VERSION
    reference_window_days: int = 252
    minimum_history_days: int = 120
    fast_half_life_days: float = 20.0
    slow_half_life_days: float = 60.0
    iqr_divisor: float = 1.349
    mad_multiplier: float = 1.4826
    trend_flat_threshold: float = 0.10
    low_enter: float = 0.20
    low_exit: float = 0.25
    high_exit: float = 0.75
    high_enter: float = 0.80
    minimum_residence_days: int = 5
    boundary_confidence_width: float = 0.10

    def __post_init__(self) -> None:
        if self.version != "state_policy_v1":
            raise ValidationError("unsupported state policy version")
        if self.reference_window_days < self.minimum_history_days:
            raise ValidationError("reference window must cover minimum history")
        if not (
            0.0
            <= self.low_enter
            < self.low_exit
            < self.high_exit
            < self.high_enter
            <= 1.0
        ):
            raise ValidationError("state bucket thresholds are not ordered")
        if self.minimum_residence_days < 1:
            raise ValidationError("minimum residence must be positive")
        if min(
            self.fast_half_life_days,
            self.slow_half_life_days,
            self.iqr_divisor,
            self.mad_multiplier,
            self.boundary_confidence_width,
        ) <= 0.0:
            raise ValidationError("state policy scale values must be positive")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


STATE_OUTPUT_COLUMNS: Final[tuple[str, ...]] = (
    "carrier_id",
    "carrier_definition_version",
    "bar_frequency",
    "observation_time",
    "available_at",
    "feature_id",
    "feature_version",
    "physical_attribute_id",
    "attribute_family",
    "measurement_scale_id",
    "state_smoothing_scale_id",
    "normalization_reference_id",
    "normalization_policy_version",
    "state_policy_version",
    "raw_value",
    "causal_location",
    "causal_trend",
    "trend_strength",
    "state_bucket",
    "state_age",
    "drift_score",
    "history_confidence",
    "data_confidence",
    "boundary_confidence",
    "confidence",
    "state_valid",
    "robust_scale_method",
)


def compute_online_market_state(
    attributes: pd.DataFrame,
    *,
    policy: OnlineStatePolicyV1 | None = None,
) -> pd.DataFrame:
    """Derive online states independently for each exact attribute/scale series."""

    cfg = policy or OnlineStatePolicyV1()
    required = {
        "carrier_id",
        "carrier_definition_version",
        "bar_frequency",
        "observation_time",
        "available_at",
        "feature_id",
        "feature_version",
        "physical_attribute_id",
        "attribute_family",
        "measurement_scale_id",
        "raw_value",
        "attribute_valid",
    }
    missing = required - set(attributes)
    if missing:
        raise ValidationError(f"attribute table missing fields: {sorted(missing)}")
    key = [
        "carrier_id",
        "carrier_definition_version",
        "bar_frequency",
        "feature_id",
        "feature_version",
        "measurement_scale_id",
    ]
    chunks: list[pd.DataFrame] = []
    for _, group in attributes.groupby(key, sort=True, dropna=False):
        chunks.append(_compute_one_series(group, cfg))
    result = pd.concat(chunks, ignore_index=True)
    return result.loc[:, STATE_OUTPUT_COLUMNS].sort_values(
        [*key, "observation_time"], kind="mergesort"
    ).reset_index(drop=True)


def _compute_one_series(
    observations: pd.DataFrame,
    policy: OnlineStatePolicyV1,
) -> pd.DataFrame:
    ordered = observations.sort_values("observation_time", kind="mergesort").reset_index(
        drop=True
    )
    values = np.asarray(ordered["raw_value"], dtype=np.float64)
    declared_valid = np.asarray(ordered["attribute_valid"], dtype=np.bool_)
    valid_values = declared_valid & np.isfinite(values)
    session_ordinals, cumulative_minutes, durations = _physical_coordinates(ordered)
    fast = _causal_ewma(
        values,
        valid_values,
        policy.fast_half_life_days,
        cumulative_minutes=cumulative_minutes,
    )
    slow = _causal_ewma(
        values,
        valid_values,
        policy.slow_half_life_days,
        cumulative_minutes=cumulative_minutes,
    )
    count = len(ordered)
    location_values = np.full(count, np.nan, dtype=float)
    trend_values = np.full(count, "invalid", dtype=object)
    strength_values = np.full(count, np.nan, dtype=float)
    bucket_values = np.full(count, "invalid", dtype=object)
    age_values = np.zeros(count, dtype=float)
    history_confidence_values = np.zeros(count, dtype=float)
    data_confidence_values = np.zeros(count, dtype=float)
    boundary_confidence_values = np.zeros(count, dtype=float)
    confidence_values = np.zeros(count, dtype=float)
    state_valid_values = np.zeros(count, dtype=bool)
    scale_method_values = np.full(count, "invalid", dtype=object)

    # Maintain the strict-prior 252-session reference as an order-statistics
    # window.  The former implementation rebuilt and rescanned the whole
    # window at every bar; this is mathematically identical but makes 15m
    # research feasible without changing the state policy.
    sorted_prior: list[float] = []
    session_valid_counts: dict[int, int] = {}
    left = 0
    active_bucket: str | None = None
    active_age = 0.0
    for index, raw in enumerate(values):
        earliest_session = max(
            0, int(session_ordinals[index]) - policy.reference_window_days + 1
        )
        while left < index and int(session_ordinals[left]) < earliest_session:
            old_value = float(values[left])
            if math.isfinite(old_value):
                position = bisect_left(sorted_prior, old_value)
                if (
                    position >= len(sorted_prior)
                    or sorted_prior[position] != old_value
                ):
                    raise ValidationError("online state rolling window diverged")
                sorted_prior.pop(position)
                old_session = int(session_ordinals[left])
                remaining = session_valid_counts[old_session] - 1
                if remaining:
                    session_valid_counts[old_session] = remaining
                else:
                    del session_valid_counts[old_session]
            left += 1
        n_valid = len(sorted_prior)
        n_valid_sessions = len(session_valid_counts)
        current_valid = bool(valid_values[index])
        state_valid = (
            current_valid and n_valid_sessions >= policy.minimum_history_days
        )
        if state_valid:
            location = bisect_right(sorted_prior, float(raw)) / float(n_valid)
            scale, scale_method = _robust_scale_sorted(
                sorted_prior,
                iqr_divisor=policy.iqr_divisor,
                mad_multiplier=policy.mad_multiplier,
            )
        else:
            location = math.nan
            scale = 0.0
            scale_method = "invalid"
        if state_valid and scale > 0.0 and np.isfinite(fast[index]) and np.isfinite(slow[index]):
            standardized_gap = float((fast[index] - slow[index]) / scale)
        elif state_valid:
            standardized_gap = 0.0
        else:
            standardized_gap = math.nan
        strength = abs(standardized_gap) if state_valid else math.nan
        if not state_valid:
            trend = "invalid"
        elif standardized_gap > policy.trend_flat_threshold:
            trend = "rising"
        elif standardized_gap < -policy.trend_flat_threshold:
            trend = "falling"
        else:
            trend = "flat"

        if state_valid:
            if active_bucket is None:
                active_bucket = _initial_bucket(location, policy)
                active_age = float(durations[index] / STANDARD_SESSION_MINUTES)
            else:
                candidate = _next_bucket(active_bucket, location, policy)
                if candidate != active_bucket and active_age >= policy.minimum_residence_days:
                    active_bucket = candidate
                    active_age = float(durations[index] / STANDARD_SESSION_MINUTES)
                else:
                    active_age += float(durations[index] / STANDARD_SESSION_MINUTES)
            bucket = active_bucket
            state_age = active_age
        else:
            bucket = "invalid"
            state_age = 0

        history_confidence = min(
            1.0, n_valid_sessions / float(policy.reference_window_days)
        )
        prior_slot_count = index - left
        data_confidence = (
            float(n_valid / prior_slot_count) if prior_slot_count > 0 else 0.0
        )
        if state_valid and scale_method != "zero":
            nearest = min(
                abs(location - boundary)
                for boundary in (
                    policy.low_enter,
                    policy.low_exit,
                    policy.high_exit,
                    policy.high_enter,
                )
            )
            boundary_confidence = min(
                1.0, nearest / policy.boundary_confidence_width
            )
        else:
            boundary_confidence = 0.0
        confidence = min(
            history_confidence, data_confidence, boundary_confidence
        )
        location_values[index] = location
        trend_values[index] = trend
        strength_values[index] = strength
        bucket_values[index] = bucket
        age_values[index] = state_age
        history_confidence_values[index] = history_confidence
        data_confidence_values[index] = data_confidence
        boundary_confidence_values[index] = boundary_confidence
        confidence_values[index] = confidence
        state_valid_values[index] = state_valid
        scale_method_values[index] = scale_method if state_valid else "invalid"

        # The original algorithm admitted every finite raw value to later
        # reference windows, including rows whose declared attribute_valid flag
        # was false.  Preserve that exact historical behavior.
        if math.isfinite(float(raw)):
            insort(sorted_prior, float(raw))
            current_session = int(session_ordinals[index])
            session_valid_counts[current_session] = (
                session_valid_counts.get(current_session, 0) + 1
            )

    output = pd.DataFrame(
        {
            "carrier_id": ordered["carrier_id"].to_numpy(),
            "carrier_definition_version": ordered[
                "carrier_definition_version"
            ].to_numpy(),
            "bar_frequency": ordered["bar_frequency"].to_numpy(),
            "observation_time": ordered["observation_time"].to_numpy(),
            "available_at": ordered["available_at"].to_numpy(),
            "feature_id": ordered["feature_id"].to_numpy(),
            "feature_version": ordered["feature_version"].to_numpy(),
            "physical_attribute_id": ordered[
                "physical_attribute_id"
            ].to_numpy(),
            "attribute_family": ordered["attribute_family"].to_numpy(),
            "measurement_scale_id": ordered["measurement_scale_id"].to_numpy(),
            "state_smoothing_scale_id": STATE_SMOOTHING_SCALE_ID,
            "normalization_reference_id": NORMALIZATION_REFERENCE_ID,
            "normalization_policy_version": policy.normalization_policy_version,
            "state_policy_version": policy.version,
            "raw_value": values,
            "causal_location": location_values,
            "causal_trend": trend_values,
            "trend_strength": strength_values,
            "state_bucket": bucket_values,
            "state_age": age_values,
            "drift_score": strength_values,
            "history_confidence": history_confidence_values,
            "data_confidence": data_confidence_values,
            "boundary_confidence": boundary_confidence_values,
            "confidence": confidence_values,
            "state_valid": state_valid_values,
            "robust_scale_method": scale_method_values,
        }
    )
    return output


def _robust_scale_sorted(
    values: list[float],
    *,
    iqr_divisor: float,
    mad_multiplier: float,
) -> tuple[float, str]:
    """Exact ``numpy.quantile(method='linear')`` scale on sorted values."""

    if not values:
        return 0.0, "zero"
    q25 = _linear_quantile_sorted(values, 0.25)
    q75 = _linear_quantile_sorted(values, 0.75)
    scale = (q75 - q25) / iqr_divisor
    if math.isfinite(scale) and scale > 0.0:
        return float(scale), "iqr"
    median = _linear_quantile_sorted(values, 0.5)
    deviations = sorted(abs(value - median) for value in values)
    mad_scale = _linear_quantile_sorted(deviations, 0.5) * mad_multiplier
    if math.isfinite(mad_scale) and mad_scale > 0.0:
        return float(mad_scale), "mad"
    return 0.0, "zero"


def _linear_quantile_sorted(values: list[float], quantile: float) -> float:
    position = (len(values) - 1) * quantile
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(values[lower])
    weight = position - lower
    return float(values[lower] * (1.0 - weight) + values[upper] * weight)


def _causal_ewma(
    values: np.ndarray,
    valid: np.ndarray,
    half_life_days: float,
    *,
    cumulative_minutes: np.ndarray | None = None,
) -> np.ndarray:
    result = np.full(len(values), np.nan, dtype=float)
    current = math.nan
    last_valid_index: int | None = None
    for index, value in enumerate(values):
        if not bool(valid[index]):
            result[index] = current
            continue
        if last_valid_index is None or not math.isfinite(current):
            current = float(value)
        else:
            if cumulative_minutes is None:
                delta_days = float(index - last_valid_index)
            else:
                delta_days = float(
                    (
                        cumulative_minutes[index]
                        - cumulative_minutes[last_valid_index]
                    )
                    / STANDARD_SESSION_MINUTES
                )
            alpha = 1.0 - math.exp(-math.log(2.0) * delta_days / half_life_days)
            current = (1.0 - alpha) * current + alpha * float(value)
        last_valid_index = index
        result[index] = current
    return result


def _physical_coordinates(
    observations: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if "trading_day" in observations:
        sessions = pd.to_datetime(
            observations["trading_day"], errors="coerce"
        ).dt.normalize()
    else:
        sessions = pd.to_datetime(
            observations["observation_time"], errors="coerce", utc=True
        ).dt.tz_convert("Asia/Shanghai").dt.tz_localize(None).dt.normalize()
    if bool(sessions.isna().any()):
        raise ValidationError("online state requires valid trading sessions")
    session_codes, _ = pd.factorize(sessions, sort=True)
    ordinals = np.asarray(session_codes, dtype=np.int64)
    if "bar_duration_minutes" in observations:
        duration_values = np.asarray(
            pd.to_numeric(observations["bar_duration_minutes"], errors="coerce"),
            dtype=float,
        )
        durations = np.where(
            np.isfinite(duration_values) & (duration_values > 0.0),
            duration_values,
            STANDARD_SESSION_MINUTES,
        )
    else:
        durations = np.full(len(observations), STANDARD_SESSION_MINUTES, dtype=float)
    return ordinals, np.cumsum(durations), durations


def _initial_bucket(location: float, policy: OnlineStatePolicyV1) -> str:
    if location <= policy.low_enter:
        return "low"
    if location >= policy.high_enter:
        return "high"
    return "normal"


def _next_bucket(
    current: str,
    location: float,
    policy: OnlineStatePolicyV1,
) -> str:
    if current == "low":
        return "normal" if location > policy.low_exit else "low"
    if current == "high":
        return "normal" if location < policy.high_exit else "high"
    if location <= policy.low_enter:
        return "low"
    if location >= policy.high_enter:
        return "high"
    return "normal"


__all__ = [
    "NORMALIZATION_POLICY_VERSION",
    "OnlineStatePolicyV1",
    "compute_online_market_state",
]
