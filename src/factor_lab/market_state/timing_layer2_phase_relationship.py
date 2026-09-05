# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportOperatorIssue=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Layer 2 component phase-age and rolling carrier-relationship providers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_layer2_measurement_plane import (
    validate_measurement_output_columns,
)
from factor_lab.market_state.timing_layer2_pit_core import PITCoreBinding

PHASE_RELATIONSHIP_SCHEMA_ID: Final[str] = "timing_layer2_phase_relationship@1.0"
RELATIONSHIP_HORIZON_DAYS: Final[tuple[int, ...]] = (20, 60, 120)


@dataclass(frozen=True, slots=True)
class ComponentMeasurementSpec:
    component_id: str
    column: str
    period_bars: int
    source_estimator: str
    source_version: str

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (
                self.component_id,
                self.column,
                self.source_estimator,
                self.source_version,
            )
        ):
            raise ValidationError("component measurement identity is incomplete")
        if isinstance(self.period_bars, bool) or self.period_bars < 2:
            raise ValidationError("component period_bars must be at least two")


def build_component_phase_age_measurements(
    panel: pd.DataFrame,
    *,
    specs: tuple[ComponentMeasurementSpec, ...],
    binding: PITCoreBinding,
) -> pd.DataFrame:
    """Measure component slope, acceleration, energy, and causal phase age."""

    if not specs or len({item.component_id for item in specs}) != len(specs):
        raise ValidationError("component specs must be non-empty with unique ids")
    required = {"timestamp", *(item.column for item in specs)}
    missing = sorted(required.difference(panel.columns))
    if missing:
        raise ValidationError(f"component phase panel missing columns: {missing}")
    frame = panel.copy().reset_index(drop=True)
    timestamp = _validated_timestamp(frame["timestamp"], label="component phase")
    frame["timestamp"] = timestamp
    output = pd.DataFrame(
        {
            "carrier_id": binding.carrier_id,
            "view_id": binding.view_id,
            "observation_time": timestamp,
            "available_at": timestamp + pd.to_timedelta(binding.availability_delay_seconds, unit="s"),
        }
    )
    energy_columns: list[tuple[int, str]] = []
    for spec in specs:
        values = pd.to_numeric(frame[spec.column], errors="raise").astype(float)
        if not np.isfinite(values.to_numpy(float)).all():
            raise ValidationError(f"component values must be finite: {spec.component_id}")
        slope = values.diff()
        acceleration = slope.diff()
        direction = np.sign(slope.fillna(0.0)).astype(int)
        phase_age = _age_since_change(direction.to_numpy(int))
        zero_side = np.sign(values).astype(int)
        zero_cross_age = _age_since_change(zero_side.to_numpy(int))
        energy_column = f"{spec.component_id}__energy_rms"
        output[f"{spec.component_id}__value"] = values
        output[f"{spec.component_id}__slope"] = slope
        output[f"{spec.component_id}__acceleration"] = acceleration
        output[f"{spec.component_id}__direction"] = direction
        output[f"{spec.component_id}__phase_age_bars"] = phase_age
        output[f"{spec.component_id}__zero_cross_age_bars"] = zero_cross_age
        output[energy_column] = values.pow(2).rolling(spec.period_bars, min_periods=spec.period_bars).mean().pow(0.5)
        energy_columns.append((spec.period_bars, energy_column))
    energies = output[[column for _, column in energy_columns]].pow(2)
    total = energies.sum(axis=1, min_count=1)
    weighted = sum(float(period) * energies[column] for period, column in energy_columns)
    output["energy_weighted_period_bars"] = weighted / total.replace(0.0, np.nan)
    shares = energies.div(total.replace(0.0, np.nan), axis=0)
    output["energy_concentration"] = shares.pow(2).sum(axis=1, min_count=1)
    output["energy_support_count"] = energies.notna().sum(axis=1)
    validate_measurement_output_columns(output.columns)
    output.attrs["timing_layer_contract"] = {
        "schema_id": PHASE_RELATIONSHIP_SCHEMA_ID,
        "family": "component_phase_age",
        "component_specs": [asdict(item) for item in specs],
        "continuous_dominant_period_only": True,
        "discrete_frequency_winner": False,
        "local_resampling": False,
        "measurement_authority": True,
        "routing_authority": False,
        "production_authority": False,
    }
    return output


def build_rolling_carrier_relationships(
    panel: pd.DataFrame,
    *,
    carrier_columns: tuple[str, ...],
    binding: PITCoreBinding,
    horizon_days: tuple[int, ...] = RELATIONSHIP_HORIZON_DAYS,
) -> pd.DataFrame:
    """Build symmetric rolling pair relations without choosing a leading carrier."""

    if horizon_days != RELATIONSHIP_HORIZON_DAYS:
        raise ValidationError("carrier relationship horizons are frozen at 20/60/120 days")
    if len(carrier_columns) < 2 or len(set(carrier_columns)) != len(carrier_columns):
        raise ValidationError("carrier relationship needs at least two unique carriers")
    required = {"timestamp", *carrier_columns}
    missing = sorted(required.difference(panel.columns))
    if missing:
        raise ValidationError(f"carrier relationship panel missing columns: {missing}")
    frame = panel.copy().reset_index(drop=True)
    timestamp = _validated_timestamp(frame["timestamp"], label="carrier relationship")
    returns = frame.loc[:, list(carrier_columns)].apply(pd.to_numeric, errors="raise").astype(float)
    if not np.isfinite(returns.to_numpy(float)).all():
        raise ValidationError("carrier relationship returns must be finite")
    rows: list[pd.DataFrame] = []
    ordered = tuple(sorted(carrier_columns))
    for left_index, left in enumerate(ordered[:-1]):
        for right in ordered[left_index + 1 :]:
            left_values = returns[left]
            right_values = returns[right]
            for days in horizon_days:
                window = days * binding.bars_per_day
                covariance = left_values.rolling(window, min_periods=window).cov(right_values, ddof=0)
                left_variance = left_values.rolling(window, min_periods=window).var(ddof=0)
                right_variance = right_values.rolling(window, min_periods=window).var(ddof=0)
                correlation = left_values.rolling(window, min_periods=window).corr(right_values)
                beta_left_on_right = covariance / right_variance.replace(0.0, np.nan)
                beta_right_on_left = covariance / left_variance.replace(0.0, np.nan)
                left_q10 = left_values.rolling(window, min_periods=window).quantile(0.1).shift(1)
                right_q10 = right_values.rolling(window, min_periods=window).quantile(0.1).shift(1)
                co_tail = ((left_values < left_q10) & (right_values < right_q10)).astype(float).rolling(window, min_periods=window).mean()
                relationship = pd.DataFrame(
                    {
                        "observation_time": timestamp,
                        "available_at": timestamp + pd.to_timedelta(binding.availability_delay_seconds, unit="s"),
                        "view_id": binding.view_id,
                        "left_carrier_id": left,
                        "right_carrier_id": right,
                        "horizon_days": days,
                        "correlation": correlation,
                        "beta_left_on_right": beta_left_on_right,
                        "beta_right_on_left": beta_right_on_left,
                        "residual_left_on_right": left_values - beta_left_on_right * right_values,
                        "residual_right_on_left": right_values - beta_right_on_left * left_values,
                        "relative_strength": (left_values - right_values).rolling(window, min_periods=window).sum(),
                        "left_now_vs_right_lag1_corr": left_values.rolling(window, min_periods=window).corr(right_values.shift(1)),
                        "right_now_vs_left_lag1_corr": right_values.rolling(window, min_periods=window).corr(left_values.shift(1)),
                        "joint_left_tail_frequency": co_tail,
                    }
                )
                numeric = relationship.select_dtypes(include=[np.number]).columns
                relationship[numeric] = relationship[numeric].replace([np.inf, -np.inf], np.nan)
                rows.append(relationship)
    result = pd.concat(rows, ignore_index=True)
    result = result.sort_values(
        ["left_carrier_id", "right_carrier_id", "horizon_days", "observation_time"],
        kind="mergesort",
    ).reset_index(drop=True)
    validate_measurement_output_columns(result.columns)
    result.attrs["timing_layer_contract"] = {
        "schema_id": PHASE_RELATIONSHIP_SCHEMA_ID,
        "family": "rolling_carrier_relationship",
        "horizon_days": list(horizon_days),
        "canonical_pair_order": True,
        "both_lag_directions_reported": True,
        "leading_carrier_winner": False,
        "membership_version": binding.membership_version,
        "measurement_authority": True,
        "routing_authority": False,
        "production_authority": False,
    }
    return result


def _validated_timestamp(values: pd.Series, *, label: str) -> pd.DatetimeIndex:
    timestamp = pd.DatetimeIndex(pd.to_datetime(values, errors="raise"))
    if timestamp.tz is None or timestamp.has_duplicates or not timestamp.is_monotonic_increasing:
        raise ValidationError(f"{label} timestamps must be timezone-aware, unique, ordered")
    return timestamp


def _age_since_change(values: np.ndarray) -> np.ndarray:
    output = np.zeros(len(values), dtype=int)
    for index in range(1, len(values)):
        output[index] = 0 if values[index] != values[index - 1] else output[index - 1] + 1
    return output


__all__ = [
    "PHASE_RELATIONSHIP_SCHEMA_ID",
    "RELATIONSHIP_HORIZON_DAYS",
    "ComponentMeasurementSpec",
    "build_component_phase_age_measurements",
    "build_rolling_carrier_relationships",
]
