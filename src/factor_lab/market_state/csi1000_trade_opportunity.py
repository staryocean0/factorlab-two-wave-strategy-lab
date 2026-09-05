"""Carrier-neutral CSI1000 opportunity forecast contracts.

The forecast layer predicts index opportunity only.  It must not encode ETF
symbols, MO moneyness, expiry months, or option-return expectations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Final, Literal

from factor_lab.core.errors import ValidationError

CONTRACT_ID: Final[str] = "IndexOpportunityForecast@1.0"
UNDERLYING_SYMBOL: Final[str] = "000852.SH"

PITStatus = Literal["ok", "missing", "stale", "unavailable", "unknown"]
CalibrationStatus = Literal["calibrated", "unknown", "insufficient_support"]


@dataclass(frozen=True, slots=True)
class PITValue:
    """Point-in-time scalar with explicit observation and availability semantics."""

    value: float | None
    observed_at: datetime
    available_at: datetime
    source: str
    status: PITStatus
    staleness_seconds: float

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None:
            raise ValidationError("PITValue.observed_at must be timezone-aware")
        if self.available_at.tzinfo is None:
            raise ValidationError("PITValue.available_at must be timezone-aware")
        if self.staleness_seconds < 0.0:
            raise ValidationError("staleness_seconds cannot be negative")
        if self.status == "ok":
            if self.value is None:
                raise ValidationError("ok PITValue requires a finite value")
            if not math.isfinite(self.value):
                raise ValidationError("ok PITValue value must be finite")
        if self.status != "ok" and self.value is not None:
            raise ValidationError("non-ok PITValue must not carry a value")


@dataclass(frozen=True, slots=True)
class ForecastFrequencySignature:
    """FrequencySignature-equivalent routing metadata bound to the forecast."""

    signature_id: str
    observation_clock: str
    update_days: int
    evidence_horizon_days: int
    rebalance_days: int
    decision_time: str
    target_definition: str
    execution_price_view: str
    cost_model_id: str
    holding_policy: str

    def __post_init__(self) -> None:
        required = (
            self.signature_id,
            self.observation_clock,
            self.decision_time,
            self.target_definition,
            self.execution_price_view,
            self.cost_model_id,
            self.holding_policy,
        )
        if not all(required):
            raise ValidationError("ForecastFrequencySignature requires all string fields")
        if min(self.update_days, self.evidence_horizon_days, self.rebalance_days) < 1:
            raise ValidationError("frequency day counts must be positive")
        if self.evidence_horizon_days < self.update_days:
            raise ValidationError("evidence_horizon_days must be >= update_days")


@dataclass(frozen=True, slots=True)
class OpportunityForecast:
    """Versioned, carrier-neutral index opportunity distribution."""

    contract_id: str
    strategy_id: str
    strategy_version: str
    opportunity_id: str
    signal_time: datetime
    available_at: datetime
    valid_until: datetime
    route_time: datetime
    underlying_symbol: str
    direction: int
    frequency: ForecastFrequencySignature
    source_period_bars: int
    minimum_holding_seconds: float
    maximum_holding_seconds: float
    expected_underlying_return_mean_bp: PITValue
    expected_underlying_return_p10_bp: PITValue
    expected_underlying_return_p50_bp: PITValue
    expected_underlying_return_p90_bp: PITValue
    probability_direction_correct: PITValue
    expected_holding_seconds: PITValue
    calibration_status: CalibrationStatus
    source_material_digest: str

    def __post_init__(self) -> None:
        if self.contract_id != CONTRACT_ID:
            raise ValidationError(f"unsupported contract_id: {self.contract_id}")
        if self.underlying_symbol != UNDERLYING_SYMBOL:
            raise ValidationError("forecast must target 000852.SH only")
        if self.direction not in {-1, 0, 1}:
            raise ValidationError("direction must be -1, 0, or +1")
        for name in ("signal_time", "available_at", "valid_until", "route_time"):
            moment = getattr(self, name)
            if moment.tzinfo is None:
                raise ValidationError(f"{name} must be timezone-aware")
        if self.valid_until <= self.signal_time:
            raise ValidationError("valid_until must be after signal_time")
        if self.source_period_bars < 1:
            raise ValidationError("source_period_bars must be positive")
        if (
            not math.isfinite(self.minimum_holding_seconds)
            or not math.isfinite(self.maximum_holding_seconds)
            or self.minimum_holding_seconds <= 0.0
            or self.maximum_holding_seconds < self.minimum_holding_seconds
        ):
            raise ValidationError("holding bounds must be finite, positive and ordered")
        if not self.source_material_digest:
            raise ValidationError("source_material_digest is required")


def validate_pit_value_against_route_time(
    field: PITValue,
    route_time: datetime,
    *,
    field_name: str,
    require_ok: bool = True,
) -> None:
    """Fail closed when a PIT field is unavailable or leaks future information."""

    if route_time.tzinfo is None:
        raise ValidationError("route_time must be timezone-aware")
    if field.available_at > route_time:
        raise ValidationError(
            f"{field_name} leaks future information: available_at={field.available_at!s} "
            f"> route_time={route_time!s}"
        )
    if field.observed_at > route_time:
        raise ValidationError(
            f"{field_name} observed after route_time: observed_at={field.observed_at!s}"
        )
    if require_ok and field.status != "ok":
        raise ValidationError(f"{field_name} status must be ok, got {field.status!r}")
    if require_ok and field.value is None:
        raise ValidationError(f"{field_name} value is required when status is ok")


def validate_opportunity_forecast(
    forecast: OpportunityForecast,
    *,
    require_calibrated: bool = True,
) -> None:
    """Validate causal timing and carrier-neutral forecast semantics."""

    if forecast.available_at > forecast.route_time:
        raise ValidationError("forecast.available_at cannot exceed route_time")
    if forecast.signal_time > forecast.route_time:
        raise ValidationError("forecast.signal_time cannot exceed route_time")
    if forecast.route_time > forecast.valid_until:
        raise ValidationError("route_time cannot exceed valid_until")
    if require_calibrated and forecast.calibration_status != "calibrated":
        raise ValidationError("calibration_status must be calibrated for routing")
    pit_fields = (
        ("expected_underlying_return_mean_bp", forecast.expected_underlying_return_mean_bp),
        ("expected_underlying_return_p10_bp", forecast.expected_underlying_return_p10_bp),
        ("expected_underlying_return_p50_bp", forecast.expected_underlying_return_p50_bp),
        ("expected_underlying_return_p90_bp", forecast.expected_underlying_return_p90_bp),
        ("probability_direction_correct", forecast.probability_direction_correct),
        ("expected_holding_seconds", forecast.expected_holding_seconds),
    )
    for name, field in pit_fields:
        validate_pit_value_against_route_time(field, forecast.route_time, field_name=name)
    p10 = forecast.expected_underlying_return_p10_bp.value
    p50 = forecast.expected_underlying_return_p50_bp.value
    mean = forecast.expected_underlying_return_mean_bp.value
    p90 = forecast.expected_underlying_return_p90_bp.value
    if (
        p10 is not None
        and p50 is not None
        and p90 is not None
        and not (p10 <= p50 <= p90)
    ):
        raise ValidationError("return quantiles must satisfy p10 <= p50 <= p90")
    if p10 is not None and mean is not None and p90 is not None and not (p10 <= mean <= p90):
        raise ValidationError("return quantiles must satisfy p10 <= mean <= p90")
    probability = forecast.probability_direction_correct.value
    if probability is not None and not 0.0 <= probability <= 1.0:
        raise ValidationError("probability_direction_correct must lie in [0, 1]")
    holding = forecast.expected_holding_seconds.value
    if holding is not None:
        if holding <= 0.0 or not math.isfinite(holding):
            raise ValidationError("expected_holding_seconds must be positive and finite")
        if holding > forecast.maximum_holding_seconds:
            raise ValidationError("expected_holding_seconds exceeds maximum_holding_seconds")
        if holding < forecast.minimum_holding_seconds:
            raise ValidationError("expected_holding_seconds is below minimum_holding_seconds")


def pit_value_from_float(
    value: float,
    *,
    observed_at: datetime,
    available_at: datetime,
    source: str,
    staleness_seconds: float = 0.0,
) -> PITValue:
    return PITValue(
        value=float(value),
        observed_at=observed_at,
        available_at=available_at,
        source=source,
        status="ok",
        staleness_seconds=float(staleness_seconds),
    )


def default_forecast_frequency() -> ForecastFrequencySignature:
    return ForecastFrequencySignature(
        signature_id="CSI1000_1M_GENERIC_FORECAST",
        observation_clock="1m_official_bar_close",
        update_days=1,
        evidence_horizon_days=1,
        rebalance_days=1,
        decision_time="strategy_declared_bar_close",
        target_definition="strategy_declared_index_return_distribution",
        execution_price_view="carrier_specific_raw_or_l1",
        cost_model_id="csi1000_trade_instrument_router_v1",
        holding_policy="forecast_declared_seconds",
    )


__all__ = [
    "CONTRACT_ID",
    "CalibrationStatus",
    "ForecastFrequencySignature",
    "OpportunityForecast",
    "PITStatus",
    "PITValue",
    "UNDERLYING_SYMBOL",
    "default_forecast_frequency",
    "pit_value_from_float",
    "validate_opportunity_forecast",
    "validate_pit_value_against_route_time",
]
