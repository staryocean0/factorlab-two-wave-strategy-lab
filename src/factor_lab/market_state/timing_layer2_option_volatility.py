# pyright: reportAny=false, reportArgumentType=false, reportIndexIssue=false
# pyright: reportAttributeAccessIssue=false, reportGeneralTypeIssues=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Shared Layer 2 option-implied and historical-volatility measurements.

The provider is available to both Layer 3 and Layer 4.  It measures continuous
market attributes only; it never chooses a strategy, option, parameter, or
account action.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Final, Literal

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.cffex_index_option_black76 import (
    IV_STATUS_OK,
    attach_option_iv_greeks,
    summarize_iv_surface,
)
from factor_lab.market_state.csi1000_instrument_state import (
    MoGreeksSnapshot,
    evaluate_intraday_black76,
)

OPTION_VOLATILITY_PROVIDER_ID: Final = "timing_layer2_option_volatility@1.0"
OPTION_VOLATILITY_PORT_SCHEMA_ID: Final = "OptionVolatilityFeatureProviderPort@1.0"
OPTION_VOLATILITY_BUNDLE_SCHEMA_ID: Final = "OptionVolatilityFeatureBundleReceipt@1.0"
DEFAULT_REALIZED_VOLATILITY_LOOKBACKS: Final = (5, 10, 20, 60)
DEFAULT_ANNUALIZATION_SESSIONS: Final = 252
ALLOWED_CONSUMERS: Final = ("Layer3", "Layer4")
SIGMA_MAX: Final = 5.0
DAILY_IV_AVAILABILITY_POLICY: Final = "next_calendar_day_0000_asia_shanghai_no_same_day_use"
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")

ConsumerRole = Literal["Layer3", "Layer4"]


def _require_digest(value: str) -> None:
    if not _DIGEST.fullmatch(value):
        raise ValidationError("Layer 2 option-volatility digest must be sha256-prefixed")


def _canonical_digest(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def _frame_digest(frame: pd.DataFrame) -> str:
    ordered = frame.reset_index(drop=True).loc[:, sorted(frame.columns)].copy()
    payload = {
        "columns": list(ordered.columns),
        "rows": ordered.astype(object).where(pd.notna(ordered), None).values.tolist(),
    }
    return _canonical_digest(payload)


def _aware_series(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_datetime(frame[column], errors="raise", utc=True)
    if values.isna().any():
        raise ValidationError(f"Layer 2 option-volatility {column} contains missing times")
    return values


def _validate_availability(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["observation_time"] = _aware_series(result, "observation_time")
    result["available_at"] = _aware_series(result, "available_at")
    if result["available_at"].lt(result["observation_time"]).any():
        raise ValidationError("Layer 2 option-volatility output predates its observation")
    return result


@dataclass(frozen=True, slots=True)
class OptionContractImpliedVolatilityPoint:
    """One contract/as-of IV measurement; it has no historical lookback."""

    contract_symbol: str
    product_id: str
    route_time: datetime
    observed_at: datetime
    available_at: datetime
    iv_mid: float
    source_material_digest: str
    lookback_sessions: None = None

    def __post_init__(self) -> None:
        if not self.contract_symbol or not self.product_id:
            raise ValidationError("Layer 2 contract IV identity is incomplete")
        if any(value.tzinfo is None for value in (self.route_time, self.observed_at, self.available_at)):
            raise ValidationError("Layer 2 contract IV times must be timezone-aware")
        if not self.observed_at <= self.available_at <= self.route_time:
            raise ValidationError("Layer 2 contract IV availability is not causal")
        if not math.isfinite(self.iv_mid) or not 0.0 < self.iv_mid <= SIGMA_MAX:
            raise ValidationError("Layer 2 contract IV is outside the Black-76 domain")
        _require_digest(self.source_material_digest)
        if self.lookback_sessions is not None:
            raise ValidationError("implied volatility cannot declare a historical lookback")


@dataclass(frozen=True, slots=True)
class OptionVolatilityFeatureBundleReceipt:
    """A versioned Layer 2 bundle consumable by Layer 3 or Layer 4."""

    provider_id: str
    layer1_coordinate_digest: str
    feature_ids: tuple[str, ...]
    denominator_contract_symbols: tuple[str, ...]
    contract_iv_points: tuple[OptionContractImpliedVolatilityPoint, ...]
    realized_volatility_lookbacks: tuple[int, ...]
    feature_bundle_digest: str
    allowed_consumers: tuple[ConsumerRole, ...] = ALLOWED_CONSUMERS
    strategy_selection_authority: bool = False
    option_selection_authority: bool = False
    parameter_selection_authority: bool = False
    routing_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.provider_id != OPTION_VOLATILITY_PROVIDER_ID or not self.feature_ids:
            raise ValidationError("Layer 2 option-volatility bundle identity drifted")
        for value in (self.layer1_coordinate_digest, self.feature_bundle_digest):
            _require_digest(value)
        if tuple(self.allowed_consumers) != ALLOWED_CONSUMERS:
            raise ValidationError("Layer 2 option-volatility consumers must be Layer 3 and Layer 4")
        if len(set(self.denominator_contract_symbols)) != len(self.denominator_contract_symbols):
            raise ValidationError("Layer 2 option-volatility denominator contains duplicates")
        point_symbols = tuple(point.contract_symbol for point in self.contract_iv_points)
        if len(set(point_symbols)) != len(point_symbols):
            raise ValidationError("Layer 2 contract IV points contain duplicates")
        if not set(point_symbols).issubset(self.denominator_contract_symbols):
            raise ValidationError("Layer 2 contract IV point escaped the frozen denominator")
        if any(value <= 1 for value in self.realized_volatility_lookbacks):
            raise ValidationError("historical volatility lookbacks must exceed one session")
        if tuple(sorted(set(self.realized_volatility_lookbacks))) != self.realized_volatility_lookbacks:
            raise ValidationError("historical volatility lookbacks must be sorted and unique")
        if any(
            (
                self.strategy_selection_authority,
                self.option_selection_authority,
                self.parameter_selection_authority,
                self.routing_authority,
                self.production_authority,
            )
        ):
            raise ValidationError("Layer 2 option-volatility bundle cannot grant strategy authority")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["schema_id"] = OPTION_VOLATILITY_BUNDLE_SCHEMA_ID
        payload["port_schema_id"] = OPTION_VOLATILITY_PORT_SCHEMA_ID
        for item in payload["contract_iv_points"]:
            item["route_time"] = item["route_time"].isoformat()
            item["observed_at"] = item["observed_at"].isoformat()
            item["available_at"] = item["available_at"].isoformat()
        return payload


def measure_contract_option_analytics(**kwargs: object) -> MoGreeksSnapshot:
    """Layer 2 authority facade over the causal Black-76 point measurement."""

    return evaluate_intraday_black76(**kwargs)  # type: ignore[arg-type]


def enrich_option_surface_with_iv(
    options: pd.DataFrame,
    futures: pd.DataFrame,
    *,
    trading_days: set[str] | None = None,
    contract_metadata: pd.DataFrame | None = None,
    risk_free_rates: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Attach same-day Black-76 IV/Greeks and build the daily IV surface."""

    enriched = attach_option_iv_greeks(
        options,
        futures,
        trading_days=trading_days,
        contract_metadata=contract_metadata,
        risk_free_rates=risk_free_rates,
    )
    summary = summarize_iv_surface(enriched)
    if not summary.empty:
        observation = pd.to_datetime(
            summary["trading_day"].astype(str) + " 15:00:00",
            errors="raise",
        ).dt.tz_localize("Asia/Shanghai")
        summary["observation_time"] = observation
        summary["available_at"] = observation.dt.normalize() + pd.Timedelta(days=1)
        summary["availability_policy"] = DAILY_IV_AVAILABILITY_POLICY
    return enriched, summary


def option_iv_ok_ratio(options: pd.DataFrame, *, exclude_status: tuple[str, ...] = ()) -> float:
    if options.empty or "iv_status" not in options.columns:
        return 0.0
    status = options["iv_status"]
    if exclude_status:
        status = status.loc[~status.isin(exclude_status)]
        if status.empty:
            return 0.0
    return float(status.eq(IV_STATUS_OK).mean())


def build_daily_front_atm_implied_volatility(surface: pd.DataFrame) -> pd.DataFrame:
    """Return one same-day front-ATM IV per product, with no rolling lookback."""

    required = {
        "trading_day",
        "product_id",
        "contract_month",
        "front_contract_month",
        "atm_symbol",
        "atm_iv",
        "observation_time",
        "available_at",
    }
    if missing := sorted(required.difference(surface.columns)):
        raise ValidationError(f"daily front-ATM IV input missing columns: {missing}")
    frame = _validate_availability(surface)
    frame = frame.loc[frame["contract_month"].astype(str).eq(frame["front_contract_month"].astype(str))].copy()
    if frame.duplicated(["trading_day", "product_id"]).any():
        raise ValidationError("daily front-ATM IV must contain one row per day and product")
    iv = pd.to_numeric(frame["atm_iv"], errors="coerce")
    if iv.isna().any() or (~iv.between(0.0, SIGMA_MAX, inclusive="right")).any():
        raise ValidationError("daily front-ATM IV is nonfinite or outside the Black-76 domain")
    output = frame[
        [
            "trading_day",
            "product_id",
            "front_contract_month",
            "atm_symbol",
            "observation_time",
            "available_at",
        ]
    ].copy()
    output["implied_volatility_decimal"] = iv.to_numpy(float)
    output["lookback_sessions"] = pd.Series([None] * len(output), dtype="object")
    output["measurement_kind"] = "daily_front_atm_implied_volatility_no_lookback_v1"
    output["measurement_authority"] = True
    output["routing_authority"] = False
    output["production_authority"] = False
    return output.sort_values(["trading_day", "product_id"], kind="mergesort").reset_index(drop=True)


def build_historical_realized_volatility(
    underlying_daily: pd.DataFrame,
    *,
    lookback_sessions: Sequence[int] = DEFAULT_REALIZED_VOLATILITY_LOOKBACKS,
    annualization_sessions: int = DEFAULT_ANNUALIZATION_SESSIONS,
) -> pd.DataFrame:
    """Build annualized close-to-close historical volatility for explicit windows."""

    required = {
        "trading_day",
        "product_id",
        "underlying_index_symbol",
        "underlying_close",
        "observation_time",
        "available_at",
    }
    if missing := sorted(required.difference(underlying_daily.columns)):
        raise ValidationError(f"historical volatility input missing columns: {missing}")
    windows = tuple(sorted(set(int(value) for value in lookback_sessions)))
    if not windows or any(value <= 1 for value in windows):
        raise ValidationError("historical volatility lookbacks must exceed one session")
    if annualization_sessions <= 1:
        raise ValidationError("historical volatility annualization must exceed one session")
    frame = _validate_availability(underlying_daily)
    if frame.duplicated(["trading_day", "product_id"]).any():
        raise ValidationError("historical volatility input contains duplicate day/product coordinates")
    frame["underlying_close"] = pd.to_numeric(frame["underlying_close"], errors="coerce")
    if frame["underlying_close"].isna().any() or frame["underlying_close"].le(0.0).any():
        raise ValidationError("historical volatility requires finite positive closes")
    outputs: list[pd.DataFrame] = []
    for _product_id, group in frame.groupby("product_id", sort=True):
        ordered = group.sort_values(["trading_day", "observation_time"], kind="mergesort").copy()
        log_return = np.log(ordered["underlying_close"]).diff()
        for window in windows:
            result = ordered[
                [
                    "trading_day",
                    "product_id",
                    "underlying_index_symbol",
                    "observation_time",
                    "available_at",
                ]
            ].copy()
            result["lookback_sessions"] = window
            result["annualization_sessions"] = annualization_sessions
            result["historical_realized_volatility_decimal"] = (
                log_return.rolling(window=window, min_periods=window).std(ddof=1)
                * math.sqrt(float(annualization_sessions))
            )
            result["quality_status"] = np.where(
                result["historical_realized_volatility_decimal"].notna(),
                "ready",
                "warmup_unavailable",
            )
            result["measurement_kind"] = "annualized_close_to_close_log_return_historical_volatility_v1"
            result["measurement_authority"] = True
            result["routing_authority"] = False
            result["production_authority"] = False
            outputs.append(result)
    output = pd.concat(outputs, ignore_index=True)
    return output.sort_values(["trading_day", "product_id", "lookback_sessions"], kind="mergesort").reset_index(drop=True)


def build_implied_realized_volatility_relationship(
    daily_iv: pd.DataFrame,
    historical_volatility: pd.DataFrame,
) -> pd.DataFrame:
    """Join same-coordinate IV and HV without turning the relation into a state."""

    iv_required = {
        "trading_day",
        "product_id",
        "implied_volatility_decimal",
        "observation_time",
        "available_at",
    }
    hv_required = {
        "trading_day",
        "product_id",
        "underlying_index_symbol",
        "lookback_sessions",
        "historical_realized_volatility_decimal",
        "observation_time",
        "available_at",
    }
    if missing := sorted(iv_required.difference(daily_iv.columns)):
        raise ValidationError(f"IV-HV relationship missing IV columns: {missing}")
    if missing := sorted(hv_required.difference(historical_volatility.columns)):
        raise ValidationError(f"IV-HV relationship missing HV columns: {missing}")
    iv = daily_iv.rename(
        columns={"observation_time": "iv_observation_time", "available_at": "iv_available_at"}
    )
    hv = historical_volatility.rename(
        columns={"observation_time": "hv_observation_time", "available_at": "hv_available_at"}
    )
    joined = hv.merge(
        iv[["trading_day", "product_id", "implied_volatility_decimal", "iv_observation_time", "iv_available_at"]],
        on=["trading_day", "product_id"],
        how="left",
        validate="many_to_one",
    )
    ready = joined["historical_realized_volatility_decimal"].notna() & joined["implied_volatility_decimal"].notna()
    if not ready.any():
        return pd.DataFrame(
            columns=[
                "trading_day",
                "product_id",
                "underlying_index_symbol",
                "lookback_sessions",
                "implied_volatility_decimal",
                "historical_realized_volatility_decimal",
                "iv_minus_hv",
                "iv_to_hv_ratio",
                "log_iv_to_hv_ratio",
                "variance_risk_premium",
                "observation_time",
                "available_at",
                "measurement_kind",
            ]
        )
    joined = joined.loc[ready].copy()
    hv_values = joined["historical_realized_volatility_decimal"].astype(float)
    iv_values = joined["implied_volatility_decimal"].astype(float)
    if hv_values.le(0.0).any() or iv_values.le(0.0).any():
        raise ValidationError("IV-HV relationship requires positive ready volatilities")
    joined["iv_minus_hv"] = iv_values - hv_values
    joined["iv_to_hv_ratio"] = iv_values / hv_values
    joined["log_iv_to_hv_ratio"] = np.log(iv_values / hv_values)
    joined["variance_risk_premium"] = np.square(iv_values) - np.square(hv_values)
    joined["observation_time"] = joined[["iv_observation_time", "hv_observation_time"]].max(axis=1)
    joined["available_at"] = joined[["iv_available_at", "hv_available_at"]].max(axis=1)
    joined["measurement_kind"] = "daily_implied_vs_historical_volatility_relationship_v1"
    joined["measurement_authority"] = True
    joined["routing_authority"] = False
    joined["production_authority"] = False
    keep = [
        "trading_day",
        "product_id",
        "underlying_index_symbol",
        "lookback_sessions",
        "implied_volatility_decimal",
        "historical_realized_volatility_decimal",
        "iv_minus_hv",
        "iv_to_hv_ratio",
        "log_iv_to_hv_ratio",
        "variance_risk_premium",
        "observation_time",
        "available_at",
        "measurement_kind",
        "measurement_authority",
        "routing_authority",
        "production_authority",
    ]
    return joined[keep].sort_values(["trading_day", "product_id", "lookback_sessions"], kind="mergesort").reset_index(drop=True)


def build_option_contract_iv_points(frame: pd.DataFrame) -> tuple[OptionContractImpliedVolatilityPoint, ...]:
    required = {
        "contract_symbol",
        "product_id",
        "route_time",
        "observed_at",
        "available_at",
        "iv_mid",
        "source_material_digest",
    }
    if missing := sorted(required.difference(frame.columns)):
        raise ValidationError(f"contract IV point input missing columns: {missing}")
    if frame.duplicated(["contract_symbol"]).any():
        raise ValidationError("contract IV point input contains duplicate symbols")
    points = tuple(
        OptionContractImpliedVolatilityPoint(
            contract_symbol=str(row.contract_symbol),
            product_id=str(row.product_id),
            route_time=pd.Timestamp(row.route_time).to_pydatetime(),
            observed_at=pd.Timestamp(row.observed_at).to_pydatetime(),
            available_at=pd.Timestamp(row.available_at).to_pydatetime(),
            iv_mid=float(row.iv_mid),
            source_material_digest=str(row.source_material_digest),
        )
        for row in frame.sort_values("contract_symbol", kind="mergesort").itertuples(index=False)
    )
    return points


def build_option_volatility_feature_bundle(
    *,
    layer1_coordinate_digest: str,
    denominator_contract_symbols: tuple[str, ...],
    contract_iv_points: tuple[OptionContractImpliedVolatilityPoint, ...],
    feature_ids: tuple[str, ...] = ("contract_implied_volatility",),
    realized_volatility_lookbacks: tuple[int, ...] = (),
) -> OptionVolatilityFeatureBundleReceipt:
    payload = {
        "provider_id": OPTION_VOLATILITY_PROVIDER_ID,
        "layer1_coordinate_digest": layer1_coordinate_digest,
        "feature_ids": feature_ids,
        "denominator_contract_symbols": denominator_contract_symbols,
        "contract_iv_points": [asdict(point) for point in contract_iv_points],
        "realized_volatility_lookbacks": realized_volatility_lookbacks,
        "allowed_consumers": ALLOWED_CONSUMERS,
    }
    return OptionVolatilityFeatureBundleReceipt(
        provider_id=OPTION_VOLATILITY_PROVIDER_ID,
        layer1_coordinate_digest=layer1_coordinate_digest,
        feature_ids=feature_ids,
        denominator_contract_symbols=denominator_contract_symbols,
        contract_iv_points=contract_iv_points,
        realized_volatility_lookbacks=realized_volatility_lookbacks,
        feature_bundle_digest=_canonical_digest(payload),
    )


def measurement_frame_digests(
    *, daily_iv: pd.DataFrame, historical_volatility: pd.DataFrame, relationship: pd.DataFrame
) -> dict[str, str]:
    return {
        "daily_iv_digest": _frame_digest(daily_iv),
        "historical_volatility_digest": _frame_digest(historical_volatility),
        "relationship_digest": _frame_digest(relationship),
    }


__all__ = [
    "ALLOWED_CONSUMERS",
    "DEFAULT_ANNUALIZATION_SESSIONS",
    "DEFAULT_REALIZED_VOLATILITY_LOOKBACKS",
    "DAILY_IV_AVAILABILITY_POLICY",
    "OPTION_VOLATILITY_BUNDLE_SCHEMA_ID",
    "OPTION_VOLATILITY_PORT_SCHEMA_ID",
    "OPTION_VOLATILITY_PROVIDER_ID",
    "OptionContractImpliedVolatilityPoint",
    "OptionVolatilityFeatureBundleReceipt",
    "build_daily_front_atm_implied_volatility",
    "build_historical_realized_volatility",
    "build_implied_realized_volatility_relationship",
    "build_option_contract_iv_points",
    "build_option_volatility_feature_bundle",
    "enrich_option_surface_with_iv",
    "measure_contract_option_analytics",
    "measurement_frame_digests",
    "option_iv_ok_ratio",
]
