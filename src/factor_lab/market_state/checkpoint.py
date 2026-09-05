"""Trusted A2 checkpoints and exact incremental online-state continuation."""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.horizons import STANDARD_SESSION_MINUTES
from factor_lab.market_state.normalization import empirical_location, robust_scale
from factor_lab.market_state.online_state import (
    NORMALIZATION_POLICY_VERSION,
    STATE_OUTPUT_COLUMNS,
    OnlineStatePolicyV1,
)

CHECKPOINT_SCHEMA_ID: Final[str] = "market_state_checkpoint@1.0"
SERIES_KEY_COLUMNS: Final[tuple[str, ...]] = (
    "carrier_id",
    "carrier_definition_version",
    "bar_frequency",
    "feature_id",
    "feature_version",
    "measurement_scale_id",
)


@dataclass(frozen=True, slots=True)
class CheckpointBindings:
    parent_bundle_id: str
    code_version: str
    config_digest: str
    source_prefix_hashes: Mapping[str, str]
    state_policy_version: str

    def __post_init__(self) -> None:
        for name in (
            "parent_bundle_id",
            "code_version",
            "config_digest",
            "state_policy_version",
        ):
            if not str(getattr(self, name)).strip():
                raise ValidationError(f"checkpoint binding {name} is required")
        if not self.source_prefix_hashes or any(
            not str(key).strip() or not str(value).strip()
            for key, value in self.source_prefix_hashes.items()
        ):
            raise ValidationError("checkpoint source prefix hashes are required")


def build_market_state_checkpoint(
    attributes: pd.DataFrame,
    states: pd.DataFrame,
    *,
    bindings: CheckpointBindings,
    policy: OnlineStatePolicyV1 | None = None,
) -> dict[str, object]:
    """Capture every recursive and rolling quantity needed for exact append."""

    cfg = policy or OnlineStatePolicyV1()
    if bindings.state_policy_version != cfg.version:
        raise ValidationError("checkpoint state policy binding mismatch")
    series_records: list[dict[str, object]] = []
    for key_values, group in attributes.groupby(
        list(SERIES_KEY_COLUMNS), sort=True, dropna=False
    ):
        raw_key = key_values if isinstance(key_values, tuple) else (key_values,)
        key = {
            column: str(value)
            for column, value in zip(SERIES_KEY_COLUMNS, raw_key, strict=True)
        }
        ordered = group.sort_values("observation_time", kind="mergesort").reset_index(
            drop=True
        )
        matching = states.copy()
        for column, value in key.items():
            matching = matching.loc[matching[column] == value]
        matching = matching.sort_values("observation_time", kind="mergesort")
        if len(matching) != len(ordered) or matching.empty:
            raise ValidationError("checkpoint attributes and states are not aligned")
        values = np.asarray(ordered["raw_value"], dtype=np.float64)
        valid = np.asarray(ordered["attribute_valid"], dtype=np.bool_) & np.isfinite(
            values
        )
        durations = _durations(ordered)
        fast, slow = _terminal_ewmas(values, valid, durations, cfg)
        references = _reference_records(ordered, cfg.reference_window_days)
        latest_state = matching.iloc[-1]
        series_records.append(
            {
                "key": key,
                "physical_attribute_id": str(ordered["physical_attribute_id"].iloc[-1]),
                "attribute_family": str(ordered["attribute_family"].iloc[-1]),
                "reference_observations": references,
                "fast_ewma": fast if math.isfinite(fast) else None,
                "slow_ewma": slow if math.isfinite(slow) else None,
                "active_bucket": str(latest_state["state_bucket"]),
                "active_age_days": float(latest_state["state_age"]),
                "last_observation_time": str(
                    pd.Timestamp(str(ordered["observation_time"].iloc[-1]))
                ),
                "last_available_at": str(
                    pd.Timestamp(str(ordered["available_at"].iloc[-1]))
                ),
            }
        )
    payload_without_digest: dict[str, object] = {
        "schema_id": CHECKPOINT_SCHEMA_ID,
        "parent_bundle_id": bindings.parent_bundle_id,
        "code_version": bindings.code_version,
        "config_digest": bindings.config_digest,
        "source_prefix_hashes": dict(sorted(bindings.source_prefix_hashes.items())),
        "state_policy_version": bindings.state_policy_version,
        "normalization_policy_version": cfg.normalization_policy_version,
        "series": series_records,
        "field_labels_zh": {
            "source_prefix_hashes": "各频率上游历史前缀摘要",
            "reference_observations": "严格因果滚动参考样本",
            "fast_ewma": "快半衰递推值",
            "slow_ewma": "慢半衰递推值",
            "active_bucket": "当前状态桶",
            "active_age_days": "当前状态驻留交易日",
        },
    }
    return {
        **payload_without_digest,
        "checkpoint_digest": canonical_digest(payload_without_digest),
    }


def validate_checkpoint_bindings(
    checkpoint: Mapping[str, object],
    *,
    expected: CheckpointBindings,
) -> None:
    """Fail closed unless every identity that affects recursion is unchanged."""

    if checkpoint.get("schema_id") != CHECKPOINT_SCHEMA_ID:
        raise ValidationError("checkpoint schema mismatch")
    recorded = str(checkpoint.get("checkpoint_digest", ""))
    digest_payload = dict(checkpoint)
    digest_payload.pop("checkpoint_digest", None)
    if canonical_digest(cast(dict[str, object], digest_payload)) != recorded:
        raise ValidationError("checkpoint semantic digest mismatch")
    comparisons = {
        "parent bundle": (checkpoint.get("parent_bundle_id"), expected.parent_bundle_id),
        "code version": (checkpoint.get("code_version"), expected.code_version),
        "config digest": (checkpoint.get("config_digest"), expected.config_digest),
        "state policy": (
            checkpoint.get("state_policy_version"),
            expected.state_policy_version,
        ),
        "source prefix hash": (
            checkpoint.get("source_prefix_hashes"),
            dict(sorted(expected.source_prefix_hashes.items())),
        ),
    }
    for label, (actual, wanted) in comparisons.items():
        if actual != wanted:
            raise ValidationError(f"checkpoint {label} mismatch")


def compute_online_market_state_incremental(
    new_attributes: pd.DataFrame,
    *,
    checkpoint: Mapping[str, object],
    bindings: CheckpointBindings,
    policy: OnlineStatePolicyV1 | None = None,
) -> pd.DataFrame:
    """Continue online states from a validated parent without replaying history."""

    cfg = policy or OnlineStatePolicyV1()
    validate_checkpoint_bindings(checkpoint, expected=bindings)
    raw_series = checkpoint.get("series")
    if not isinstance(raw_series, list) or not raw_series:
        raise ValidationError("checkpoint series are required")
    by_key: dict[tuple[str, ...], Mapping[str, object]] = {}
    for raw in raw_series:
        if not isinstance(raw, Mapping):
            raise ValidationError("checkpoint series record must be an object")
        key_payload = raw.get("key")
        if not isinstance(key_payload, Mapping):
            raise ValidationError("checkpoint series key is required")
        key = tuple(str(key_payload.get(column, "")) for column in SERIES_KEY_COLUMNS)
        by_key[key] = cast(Mapping[str, object], raw)
    chunks: list[pd.DataFrame] = []
    for key_values, group in new_attributes.groupby(
        list(SERIES_KEY_COLUMNS), sort=True, dropna=False
    ):
        raw_key = key_values if isinstance(key_values, tuple) else (key_values,)
        key = tuple(str(value) for value in raw_key)
        prior = by_key.get(key)
        if prior is None:
            raise ValidationError(f"checkpoint missing attribute series: {key}")
        chunks.append(_continue_one_series(group, prior, cfg))
    if not chunks:
        return pd.DataFrame(columns=pd.Index(STATE_OUTPUT_COLUMNS))
    return pd.concat(chunks, ignore_index=True).loc[:, STATE_OUTPUT_COLUMNS].sort_values(
        [*SERIES_KEY_COLUMNS, "observation_time"], kind="mergesort"
    ).reset_index(drop=True)


def _continue_one_series(
    observations: pd.DataFrame,
    checkpoint: Mapping[str, object],
    policy: OnlineStatePolicyV1,
) -> pd.DataFrame:
    ordered = observations.sort_values("observation_time", kind="mergesort").reset_index(
        drop=True
    )
    if ordered.empty:
        return pd.DataFrame(columns=pd.Index(STATE_OUTPUT_COLUMNS))
    last_time = pd.Timestamp(str(checkpoint.get("last_observation_time", "")))
    if bool((pd.to_datetime(ordered["observation_time"], utc=True) <= last_time).any()):
        raise ValidationError("incremental observations must be a strict tail append")
    references_raw = checkpoint.get("reference_observations")
    if not isinstance(references_raw, list):
        raise ValidationError("checkpoint reference observations are required")
    references: deque[dict[str, object]] = deque(
        cast(list[dict[str, object]], references_raw)
    )
    fast = _optional_float(checkpoint.get("fast_ewma"))
    slow = _optional_float(checkpoint.get("slow_ewma"))
    active_bucket = str(checkpoint.get("active_bucket", "invalid"))
    if active_bucket == "invalid":
        active_bucket = ""
    active_age = _optional_float(checkpoint.get("active_age_days", 0.0))
    rows: list[dict[str, object]] = []
    for _, base in ordered.iterrows():
        raw = _optional_float(base["raw_value"])
        current_valid = bool(base["attribute_valid"]) and math.isfinite(raw)
        trading_day = pd.Timestamp(
            str(base.get("trading_day", base["observation_time"]))
        )
        day_text = str(trading_day.tz_localize(None).date())
        _trim_reference_sessions(references, day_text, policy.reference_window_days)
        prior_values = np.asarray(
            [
                _optional_float(item["raw_value"])
                for item in references
                if bool(item["attribute_valid"])
                and math.isfinite(_optional_float(item["raw_value"]))
            ],
            dtype=float,
        )
        valid_sessions = {
            str(item["trading_day"])
            for item in references
            if bool(item["attribute_valid"])
            and math.isfinite(_optional_float(item["raw_value"]))
        }
        state_valid = current_valid and len(valid_sessions) >= policy.minimum_history_days
        location = empirical_location(raw, prior_values) if state_valid else math.nan
        scale, scale_method = robust_scale(
            prior_values,
            iqr_divisor=policy.iqr_divisor,
            mad_multiplier=policy.mad_multiplier,
        )
        duration = _row_duration(base)
        if current_valid:
            fast = _ewma_update(fast, raw, duration, policy.fast_half_life_days)
            slow = _ewma_update(slow, raw, duration, policy.slow_half_life_days)
        if state_valid and scale > 0.0 and math.isfinite(fast) and math.isfinite(slow):
            gap = (fast - slow) / scale
        elif state_valid:
            gap = 0.0
        else:
            gap = math.nan
        if not state_valid:
            trend = "invalid"
        elif gap > policy.trend_flat_threshold:
            trend = "rising"
        elif gap < -policy.trend_flat_threshold:
            trend = "falling"
        else:
            trend = "flat"
        if state_valid:
            candidate = _initial_bucket(location, policy) if not active_bucket else _next_bucket(
                active_bucket, location, policy
            )
            if not active_bucket:
                active_bucket = candidate
                active_age = duration / STANDARD_SESSION_MINUTES
            elif candidate != active_bucket and active_age >= policy.minimum_residence_days:
                active_bucket = candidate
                active_age = duration / STANDARD_SESSION_MINUTES
            else:
                active_age += duration / STANDARD_SESSION_MINUTES
            bucket = active_bucket
            state_age = active_age
        else:
            bucket = "invalid"
            state_age = 0.0
        history_confidence = min(
            1.0, len(valid_sessions) / float(policy.reference_window_days)
        )
        data_confidence = (
            float(len(prior_values) / len(references)) if references else 0.0
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
        rows.append(
            {
                "carrier_id": base["carrier_id"],
                "carrier_definition_version": base["carrier_definition_version"],
                "bar_frequency": base["bar_frequency"],
                "observation_time": base["observation_time"],
                "available_at": base["available_at"],
                "feature_id": base["feature_id"],
                "feature_version": base["feature_version"],
                "physical_attribute_id": base["physical_attribute_id"],
                "attribute_family": base["attribute_family"],
                "measurement_scale_id": base["measurement_scale_id"],
                "state_smoothing_scale_id": "ewma_gap_20d_60d",
                "normalization_reference_id": "structural_252d",
                "normalization_policy_version": NORMALIZATION_POLICY_VERSION,
                "state_policy_version": policy.version,
                "raw_value": raw,
                "causal_location": location,
                "causal_trend": trend,
                "trend_strength": abs(gap) if state_valid else math.nan,
                "state_bucket": bucket,
                "state_age": state_age,
                "drift_score": abs(gap) if state_valid else math.nan,
                "history_confidence": history_confidence,
                "data_confidence": data_confidence,
                "boundary_confidence": boundary_confidence,
                "confidence": confidence,
                "state_valid": state_valid,
                "robust_scale_method": scale_method if state_valid else "invalid",
            }
        )
        references.append(
            {
                "trading_day": day_text,
                "raw_value": raw,
                "attribute_valid": current_valid,
            }
        )
    return pd.DataFrame(rows)


def _reference_records(
    ordered: pd.DataFrame, reference_window_days: int
) -> list[dict[str, object]]:
    source = (
        ordered["trading_day"]
        if "trading_day" in ordered
        else ordered["observation_time"]
    )
    trading_days = pd.to_datetime(source, errors="coerce").dt.tz_localize(
        None
    ).dt.normalize()
    unique_days = pd.Index(trading_days.drop_duplicates())
    keep = set(unique_days[-reference_window_days:])
    records = []
    for index, row in ordered.iterrows():
        day = trading_days.iloc[index]
        if day in keep:
            raw = _optional_float(row["raw_value"])
            records.append(
                {
                    "trading_day": str(day.date()),
                    "raw_value": raw if math.isfinite(raw) else None,
                    "attribute_valid": bool(row["attribute_valid"])
                    and math.isfinite(raw),
                }
            )
    return records


def _terminal_ewmas(
    values: np.ndarray,
    valid: np.ndarray,
    durations: np.ndarray,
    policy: OnlineStatePolicyV1,
) -> tuple[float, float]:
    fast = math.nan
    slow = math.nan
    for raw, is_valid, duration in zip(values, valid, durations, strict=True):
        if not bool(is_valid):
            continue
        fast = _ewma_update(fast, float(raw), float(duration), policy.fast_half_life_days)
        slow = _ewma_update(slow, float(raw), float(duration), policy.slow_half_life_days)
    return fast, slow


def _ewma_update(current: float, raw: float, duration: float, half_life_days: float) -> float:
    if not math.isfinite(current):
        return raw
    alpha = 1.0 - math.exp(
        -math.log(2.0) * duration / (half_life_days * STANDARD_SESSION_MINUTES)
    )
    return (1.0 - alpha) * current + alpha * raw


def _durations(frame: pd.DataFrame) -> np.ndarray:
    if "bar_duration_minutes" not in frame:
        return np.full(len(frame), STANDARD_SESSION_MINUTES, dtype=float)
    values = np.asarray(
        pd.to_numeric(frame["bar_duration_minutes"], errors="coerce"), dtype=float
    )
    return np.where(
        np.isfinite(values) & (values > 0.0), values, STANDARD_SESSION_MINUTES
    )


def _row_duration(row: pd.Series) -> float:
    value = _optional_float(row.get("bar_duration_minutes", STANDARD_SESSION_MINUTES))
    return value if math.isfinite(value) and value > 0.0 else STANDARD_SESSION_MINUTES


def _optional_float(value: object) -> float:
    if value is None:
        return math.nan
    parsed = float(str(value))
    return parsed if math.isfinite(parsed) else math.nan


def _trim_reference_sessions(
    references: deque[dict[str, object]],
    current_day: str,
    window_days: int,
) -> None:
    days = list(dict.fromkeys([str(item["trading_day"]) for item in references] + [current_day]))
    keep = set(days[-window_days:])
    while references and str(references[0]["trading_day"]) not in keep:
        references.popleft()


def _initial_bucket(location: float, policy: OnlineStatePolicyV1) -> str:
    if location <= policy.low_enter:
        return "low"
    if location >= policy.high_enter:
        return "high"
    return "normal"


def _next_bucket(current: str, location: float, policy: OnlineStatePolicyV1) -> str:
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
    "CHECKPOINT_SCHEMA_ID",
    "CheckpointBindings",
    "build_market_state_checkpoint",
    "compute_online_market_state_incremental",
    "validate_checkpoint_bindings",
]
