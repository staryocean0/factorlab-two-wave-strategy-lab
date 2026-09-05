"""PIT instrument snapshots, ETF/MO legality, intraday Greeks, and carrier rows."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Final, Literal

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.cffex_index_option_black76 import (
    IV_STATUS_OK,
    black76_discounted,
    invert_black76_iv,
)
from factor_lab.market_state.csi1000_trade_opportunity import OpportunityForecast

INFRASTRUCTURE_ID: Final[str] = "csi1000_trade_instrument_router_v1"
PIT_SNAPSHOT_CONTRACT: Final[str] = "PITMarketSnapshot@1.0"
UNIVERSE_CONTRACT: Final[str] = "InstrumentUniverseSnapshot@1.0"
CARRIER_CONTRACT: Final[str] = "CarrierEvaluation@1.0"

BASELINE_ETF_SYMBOL: Final[str] = "512100.SH"
BASELINE_ETF_LISTING_DATE: Final[date] = date(2016, 11, 4)
ETF_COMMISSION_BPS_PER_SIDE: Final[float] = 1.0
ETF_STAMP_TAX_BPS: Final[float] = 0.0

MO_PRODUCT: Final[str] = "MO"
IM_PRODUCT: Final[str] = "IM"
MO_CONTRACT_MULTIPLIER: Final[int] = 100
MO_ROUND_TRIP_FEE_YUAN: Final[float] = 28.0
MO_MIN_ABS_DELTA: Final[float] = 0.05

CarrierType = Literal["etf", "mo", "no_trade"]
QuoteStatus = Literal[
    "ok",
    "quote_unavailable",
    "crossed_market",
    "future_quote",
    "missing_forward",
    "forward_month_mismatch",
    "solver_failed",
    "delta_below_minimum",
    "impact_unidentified",
    "execution_quality_unresolved",
    "quote_identity_mismatch",
    "stale_quote",
]


@dataclass(frozen=True, slots=True)
class PITField:
    value: float | None
    observed_at: datetime
    available_at: datetime
    source: str
    status: str
    staleness_seconds: float

    def __post_init__(self) -> None:
        _require_aware(self.observed_at, name="PITField.observed_at")
        _require_aware(self.available_at, name="PITField.available_at")
        if self.staleness_seconds < 0.0 or not math.isfinite(self.staleness_seconds):
            raise ValidationError("PITField staleness must be finite and non-negative")
        if self.status == "ok":
            if self.value is None or not math.isfinite(self.value):
                raise ValidationError("ok PITField requires a finite value")
        elif self.value is not None:
            raise ValidationError("non-ok PITField cannot carry a value")


@dataclass(frozen=True, slots=True)
class InstrumentIdentity:
    instrument_id: str
    carrier_type: CarrierType
    symbol: str
    listed: bool
    listing_date: date | None
    expiry_date: date | None
    contract_month: str | None
    option_type: Literal["call", "put"] | None
    strike: float | None
    multiplier: int

    def __post_init__(self) -> None:
        if not self.instrument_id or not self.symbol or self.multiplier <= 0:
            raise ValidationError("instrument identity is incomplete")
        if self.carrier_type == "mo" and (
            self.contract_month is None
            or self.option_type not in {"call", "put"}
            or self.strike is None
            or self.strike <= 0.0
        ):
            raise ValidationError("MO identity requires expiry, month, type and strike")


@dataclass(frozen=True, slots=True)
class QuoteSnapshot:
    instrument_id: str
    bid: float | None
    ask: float | None
    mid: float | None
    bid_size: float | None
    ask_size: float | None
    observed_at: datetime
    available_at: datetime
    bucket_end: datetime
    source: str
    status: QuoteStatus

    def __post_init__(self) -> None:
        for name in ("observed_at", "available_at", "bucket_end"):
            _require_aware(getattr(self, name), name=f"QuoteSnapshot.{name}")
        if self.status == "ok":
            if self.bid is None or self.ask is None or not 0.0 < self.bid <= self.ask:
                raise ValidationError("ok quote requires positive non-crossed bid and ask")
            if self.mid is None or not math.isfinite(self.mid):
                raise ValidationError("ok quote requires a finite midpoint")


@dataclass(frozen=True, slots=True)
class PITMarketSnapshot:
    """Versioned causal market snapshot bound to explicit route timing."""

    contract_id: str
    infrastructure_id: str
    signal_time: datetime
    route_time: datetime
    order_submission_time: datetime | None
    fill_time: datetime | None
    forward_by_month: Mapping[str, PITField]
    risk_free_rate: PITField
    quotes: tuple[QuoteSnapshot, ...]
    snapshot_digest: str

    def __post_init__(self) -> None:
        if self.contract_id != PIT_SNAPSHOT_CONTRACT:
            raise ValidationError(f"unsupported PIT snapshot contract: {self.contract_id}")
        for name in ("signal_time", "route_time"):
            moment = getattr(self, name)
            if moment.tzinfo is None:
                raise ValidationError(f"{name} must be timezone-aware")
        if self.signal_time > self.route_time:
            raise ValidationError("signal_time cannot exceed route_time")
        if not self.snapshot_digest:
            raise ValidationError("snapshot_digest is required")
        if self.risk_free_rate.available_at > self.route_time:
            raise ValidationError("risk_free_rate leaks future information")
        if self.risk_free_rate.observed_at > self.route_time:
            raise ValidationError("risk_free_rate observed after route_time")
        for month, field in self.forward_by_month.items():
            if field.available_at > self.route_time:
                raise ValidationError(f"forward {month} leaks future information")
            if field.observed_at > self.route_time:
                raise ValidationError(f"forward {month} observed after route_time")
        quote_ids: list[str] = []
        for quote in self.quotes:
            if quote.available_at > self.route_time or quote.bucket_end > self.route_time:
                raise ValidationError(f"quote {quote.instrument_id} leaks future information")
            quote_ids.append(quote.instrument_id)
        if len(quote_ids) != len(set(quote_ids)):
            raise ValidationError("PIT snapshot requires at most one quote per instrument")


@dataclass(frozen=True, slots=True)
class InstrumentUniverseSnapshot:
    """Full denominator universe; identities are conserved regardless of quotes."""

    contract_id: str
    infrastructure_id: str
    asof_time: datetime
    identities: tuple[InstrumentIdentity, ...]
    universe_digest: str

    def __post_init__(self) -> None:
        if self.contract_id != UNIVERSE_CONTRACT:
            raise ValidationError(f"unsupported universe contract: {self.contract_id}")
        if self.asof_time.tzinfo is None:
            raise ValidationError("asof_time must be timezone-aware")
        if not self.universe_digest:
            raise ValidationError("universe_digest is required")
        ids = [item.instrument_id for item in self.identities]
        if len(ids) != len(set(ids)):
            raise ValidationError("instrument identities must be unique")

    def verify_conservation(self, expected: Sequence[InstrumentIdentity]) -> None:
        expected_ids = {item.instrument_id for item in expected}
        actual_ids = {item.instrument_id for item in self.identities}
        if expected_ids != actual_ids:
            raise ValidationError("universe snapshot does not conserve instrument identities")


@dataclass(frozen=True, slots=True)
class EtfAccountState:
    shares_held: float = 0.0
    shares_bought_today: float = 0.0
    short_borrow_authority: bool = False
    borrowable_shares: float = 0.0

    def __post_init__(self) -> None:
        if min(self.shares_held, self.shares_bought_today, self.borrowable_shares) < 0.0:
            raise ValidationError("ETF account share quantities cannot be negative")
        if self.shares_bought_today > self.shares_held:
            raise ValidationError("shares_bought_today cannot exceed shares_held")


@dataclass(frozen=True, slots=True)
class EtfCostBreakdown:
    commission_bps_per_side: float
    stamp_tax_bps: float
    half_spread_bps: float
    slippage_bps: float
    impact_bps: float
    tracking_or_basis_bps: float
    execution_quality_status: QuoteStatus

    def __post_init__(self) -> None:
        values = (
            self.commission_bps_per_side,
            self.stamp_tax_bps,
            self.half_spread_bps,
            self.slippage_bps,
            self.impact_bps,
            self.tracking_or_basis_bps,
        )
        if any(not math.isfinite(value) or value < 0.0 for value in values):
            raise ValidationError("ETF cost components must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class MoGreeksSnapshot:
    forward: float
    forward_month: str
    risk_free_rate: float
    seconds_to_expiry: float
    years_to_expiry: float
    iv_bid: float | None
    iv_mid: float | None
    iv_ask: float | None
    delta_forward: float | None
    gamma_forward: float | None
    vega: float | None
    theta_per_year: float | None
    iv_status: str
    forward_status: str


@dataclass(frozen=True, slots=True)
class AllInHurdleBP:
    spread_bps: float | None
    fee_bps: float | None
    impact_bps: float | None
    theta_bps: float | None
    identified_subtotal_bps: float | None
    total_bps: float | None
    spread_status: QuoteStatus
    fee_status: QuoteStatus
    impact_status: QuoteStatus
    theta_status: QuoteStatus
    complete_cost_ready: bool


@dataclass(frozen=True, slots=True)
class CarrierEvaluation:
    contract_id: str
    infrastructure_id: str
    carrier_id: str
    carrier_type: CarrierType
    instrument_id: str
    eligible: bool
    rejection_codes: tuple[str, ...]
    expected_net_pnl: float
    cvar: float
    liquidity_uncertainty: float
    tracking_or_basis_penalty: float
    spread_bps: float
    fee_bps: float
    impact_bps: float
    eas_full_spread_bp: float | None
    all_in_hurdle_bp: AllInHurdleBP | None
    actual_units: float
    delta_equivalent_notional: float
    risk_budget_id: str
    risk_budget_cash: float
    risk_sizing_ready: bool
    complete_cost_ready: bool
    formula_digest: str

    def __post_init__(self) -> None:
        cash_values = (
            self.expected_net_pnl,
            self.cvar,
            self.liquidity_uncertainty,
            self.tracking_or_basis_penalty,
        )
        if any(not math.isfinite(value) for value in cash_values):
            raise ValidationError("carrier cash metrics must be finite")
        if min(self.cvar, self.liquidity_uncertainty, self.tracking_or_basis_penalty) < 0.0:
            raise ValidationError("carrier risk penalties cannot be negative")
        if (
            self.actual_units < 0.0
            or self.delta_equivalent_notional < 0.0
            or self.risk_budget_cash < 0.0
        ):
            raise ValidationError("carrier quantities cannot be negative")
        if not self.risk_budget_id:
            raise ValidationError("carrier risk_budget_id is required")
        if self.risk_sizing_ready and self.carrier_type != "no_trade":
            tolerance = max(1.0e-9, 0.01 * self.risk_budget_cash)
            if self.risk_budget_cash <= 0.0 or abs(self.cvar - self.risk_budget_cash) > tolerance:
                raise ValidationError("ready risk sizing must match the common CVaR cash budget")
        if not self.formula_digest:
            raise ValidationError("carrier formula_digest is required")


_MO_SYMBOL_RE = re.compile(
    r"^(?P<product>MO)(?P<yy>\d{2})(?P<mm>\d{2})-(?P<cp>[CP])-(?P<strike>\d+(?:\.\d+)?)$"
)


def _require_aware(moment: datetime, *, name: str) -> datetime:
    if moment.tzinfo is None:
        raise ValidationError(f"{name} must be timezone-aware")
    return moment


def _bps_to_cash(bps: float, notional: float) -> float:
    return notional * bps / 10_000.0


def contract_month_from_symbol(symbol: str) -> str | None:
    match = _MO_SYMBOL_RE.match(symbol)
    if match is None:
        return None
    return f"20{match.group('yy')}{match.group('mm')}"


def parse_mo_identity(symbol: str, *, listed: bool = True, expiry_date: date | None = None) -> InstrumentIdentity:
    match = _MO_SYMBOL_RE.match(symbol)
    if match is None:
        raise ValidationError(f"unsupported MO symbol: {symbol}")
    option_type: Literal["call", "put"] = "call" if match.group("cp") == "C" else "put"
    return InstrumentIdentity(
        instrument_id=f"mo:{symbol}",
        carrier_type="mo",
        symbol=symbol,
        listed=listed,
        listing_date=None,
        expiry_date=expiry_date,
        contract_month=contract_month_from_symbol(symbol),
        option_type=option_type,
        strike=float(match.group("strike")),
        multiplier=MO_CONTRACT_MULTIPLIER,
    )


def baseline_etf_identity() -> InstrumentIdentity:
    return InstrumentIdentity(
        instrument_id=f"etf:{BASELINE_ETF_SYMBOL}",
        carrier_type="etf",
        symbol=BASELINE_ETF_SYMBOL,
        listed=True,
        listing_date=BASELINE_ETF_LISTING_DATE,
        expiry_date=None,
        contract_month=None,
        option_type=None,
        strike=None,
        multiplier=1,
    )


def enumerate_instrument_universe(
    *,
    mo_symbols: Sequence[str],
    mo_metadata: Mapping[str, Mapping[str, object]] | None = None,
    include_baseline_etf: bool = True,
) -> tuple[InstrumentIdentity, ...]:
    """Return the full denominator universe, including no-quote MO identities."""

    identities: list[InstrumentIdentity] = []
    if include_baseline_etf:
        identities.append(baseline_etf_identity())
    metadata = mo_metadata or {}
    for symbol in mo_symbols:
        meta = metadata.get(symbol, {})
        expiry = meta.get("expiry_date")
        expiry_date = date.fromisoformat(str(expiry)) if expiry is not None else None
        listed = bool(meta.get("listed", True))
        identities.append(parse_mo_identity(symbol, listed=listed, expiry_date=expiry_date))
    return tuple(identities)


def build_instrument_universe_snapshot(
    *,
    asof_time: datetime,
    mo_symbols: Sequence[str],
    mo_metadata: Mapping[str, Mapping[str, object]] | None = None,
    include_baseline_etf: bool = True,
    universe_digest: str = "universe_v1",
) -> InstrumentUniverseSnapshot:
    identities = enumerate_instrument_universe(
        mo_symbols=mo_symbols,
        mo_metadata=mo_metadata,
        include_baseline_etf=include_baseline_etf,
    )
    return InstrumentUniverseSnapshot(
        contract_id=UNIVERSE_CONTRACT,
        infrastructure_id=INFRASTRUCTURE_ID,
        asof_time=_require_aware(asof_time, name="asof_time"),
        identities=identities,
        universe_digest=universe_digest,
    )


def snapshot_asof(
    quotes: Sequence[Mapping[str, object]],
    route_time: datetime,
    *,
    instrument_id: str,
    max_lookback_seconds: int,
) -> QuoteSnapshot | None:
    """Select the latest causal quote for one contract identity.

    Caller must supply max_lookback_seconds explicitly.  Both bid and ask are
    required for an ok quote; one-sided rows are quote_unavailable.  Rows whose
    instrument_id does not match the requested identity are ignored.
    """

    route_time = _require_aware(route_time, name="route_time")
    if max_lookback_seconds <= 0:
        raise ValidationError("max_lookback_seconds must be positive")
    eligible: list[QuoteSnapshot] = []
    for row in quotes:
        row_instrument = str(row.get("instrument_id", ""))
        if row_instrument != instrument_id:
            continue
        bucket_end = pd.Timestamp(row["bucket_end"]).to_pydatetime()
        available_at = pd.Timestamp(row["available_at"]).to_pydatetime()
        observed_at = pd.Timestamp(row["observed_at"]).to_pydatetime()
        if bucket_end > route_time or available_at > route_time:
            continue
        age_seconds = (route_time - bucket_end).total_seconds()
        if age_seconds > max_lookback_seconds:
            continue
        bid = row.get("bid")
        ask = row.get("ask")
        bid_value = None if bid is None else float(bid)
        ask_value = None if ask is None else float(ask)
        if bid_value is None or ask_value is None:
            status: QuoteStatus = "quote_unavailable"
            mid = None
        elif bid_value <= 0.0 or ask_value <= 0.0:
            status = "quote_unavailable"
            mid = None
        elif ask_value < bid_value:
            status = "crossed_market"
            mid = None
        else:
            status = "ok"
            mid = 0.5 * (bid_value + ask_value)
        eligible.append(
            QuoteSnapshot(
                instrument_id=instrument_id,
                bid=bid_value,
                ask=ask_value,
                mid=mid,
                bid_size=None if row.get("bid_size") is None else float(row["bid_size"]),
                ask_size=None if row.get("ask_size") is None else float(row["ask_size"]),
                observed_at=observed_at,
                available_at=available_at,
                bucket_end=bucket_end,
                source=str(row.get("source", "synthetic")),
                status=status,
            )
        )
    if not eligible:
        return None
    return max(eligible, key=lambda item: (item.bucket_end, item.available_at, item.observed_at))


def etf_route_legality(
    *,
    route_time: datetime,
    direction: int,
    account: EtfAccountState,
    shares_to_trade: float,
    expected_holding_seconds: float | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Enforce listing date, T+1, long-only, borrow authority and same-day round trips."""

    route_time = _require_aware(route_time, name="route_time")
    route_day = route_time.date()
    codes: list[str] = []
    if route_day < BASELINE_ETF_LISTING_DATE:
        codes.append("ETF_CARRIER_UNAVAILABLE")
    if shares_to_trade <= 0.0:
        codes.append("NONPOSITIVE_TRADE_SIZE")
    if direction > 0 and expected_holding_seconds is not None:
        exit_time = route_time + timedelta(seconds=expected_holding_seconds)
        if exit_time.date() == route_day:
            codes.append("ETF_SAME_DAY_ROUND_TRIP_BLOCKED")
    if direction < 0:
        if not account.short_borrow_authority:
            codes.append("ETF_SHORT_WITHOUT_BORROW")
        if shares_to_trade > account.borrowable_shares:
            codes.append("ETF_INSUFFICIENT_BORROWABLE_SHARES")
    return (len(codes) == 0, tuple(codes))


def mo_option_matches_forecast(
    forecast_direction: int,
    option_type: Literal["call", "put"],
) -> bool:
    if forecast_direction > 0 and option_type == "put":
        return False
    if forecast_direction < 0 and option_type == "call":
        return False
    return True


def etf_cost_breakdown(
    *,
    half_spread_bps: float,
    slippage_bps: float = 0.0,
    impact_bps: float = 0.0,
    tracking_or_basis_bps: float = 0.0,
    execution_quality_status: QuoteStatus = "execution_quality_unresolved",
) -> EtfCostBreakdown:
    return EtfCostBreakdown(
        commission_bps_per_side=ETF_COMMISSION_BPS_PER_SIDE,
        stamp_tax_bps=ETF_STAMP_TAX_BPS,
        half_spread_bps=float(half_spread_bps),
        slippage_bps=float(slippage_bps),
        impact_bps=float(impact_bps),
        tracking_or_basis_bps=float(tracking_or_basis_bps),
        execution_quality_status=execution_quality_status,
    )


def etf_round_trip_cost_bps(cost: EtfCostBreakdown) -> float:
    return (
        2.0 * cost.commission_bps_per_side
        + cost.stamp_tax_bps
        + 2.0 * cost.half_spread_bps
        + cost.slippage_bps
        + cost.impact_bps
    )


def compute_eas_full_spread_bp(
    *,
    bid: float,
    ask: float,
    delta_forward: float,
    forward: float,
    min_abs_delta: float = MO_MIN_ABS_DELTA,
) -> tuple[float | None, QuoteStatus]:
    if forward <= 0.0:
        return None, "missing_forward"
    if abs(delta_forward) < min_abs_delta:
        return None, "delta_below_minimum"
    if ask < bid:
        return None, "crossed_market"
    spread = ask - bid
    eas = spread / (abs(delta_forward) * forward)
    return 10_000.0 * eas, "ok"


def mo_fee_points() -> float:
    return MO_ROUND_TRIP_FEE_YUAN / float(MO_CONTRACT_MULTIPLIER)


def compute_all_in_hurdle_bp(
    *,
    entry_half_spread_points: float,
    exit_half_spread_points: float,
    fee_points: float,
    impact_points: float | None,
    delta_forward: float,
    forward: float,
    theta_points: float = 0.0,
    include_theta_in_hurdle: bool = False,
    min_abs_delta: float = MO_MIN_ABS_DELTA,
) -> AllInHurdleBP:
    if forward <= 0.0:
        return AllInHurdleBP(
            spread_bps=None,
            fee_bps=None,
            impact_bps=None,
            theta_bps=None,
            identified_subtotal_bps=None,
            total_bps=None,
            spread_status="missing_forward",
            fee_status="missing_forward",
            impact_status="impact_unidentified",
            theta_status="missing_forward",
            complete_cost_ready=False,
        )
    if abs(delta_forward) < min_abs_delta:
        return AllInHurdleBP(
            spread_bps=None,
            fee_bps=None,
            impact_bps=None,
            theta_bps=None,
            identified_subtotal_bps=None,
            total_bps=None,
            spread_status="delta_below_minimum",
            fee_status="delta_below_minimum",
            impact_status="impact_unidentified",
            theta_status="delta_below_minimum",
            complete_cost_ready=False,
        )
    denominator = abs(delta_forward) * forward
    spread_points = entry_half_spread_points + exit_half_spread_points
    spread_bps = 10_000.0 * spread_points / denominator
    fee_bps = 10_000.0 * fee_points / denominator
    identified_subtotal_bps = spread_bps + fee_bps
    impact_status: QuoteStatus = "impact_unidentified"
    impact_bps = None
    if impact_points is not None:
        impact_bps = 10_000.0 * impact_points / denominator
        impact_status = "ok"
    theta_bps = None
    theta_status: QuoteStatus = "ok"
    if include_theta_in_hurdle:
        theta_bps = 10_000.0 * theta_points / denominator
    total_bps = None
    complete = impact_points is not None
    if complete:
        total_points = spread_points + fee_points + impact_points
        if include_theta_in_hurdle:
            total_points += theta_points
        total_bps = 10_000.0 * total_points / denominator
    return AllInHurdleBP(
        spread_bps=spread_bps,
        fee_bps=fee_bps,
        impact_bps=impact_bps,
        theta_bps=theta_bps,
        identified_subtotal_bps=identified_subtotal_bps,
        total_bps=total_bps,
        spread_status="ok",
        fee_status="ok",
        impact_status=impact_status,
        theta_status=theta_status,
        complete_cost_ready=complete,
    )


def evaluate_intraday_black76(
    *,
    route_time: datetime,
    expiry_time: datetime,
    option_symbol: str,
    bid_premium: float | None,
    mid_premium: float | None,
    ask_premium: float | None,
    forward_price: float,
    forward_month: str,
    risk_free_rate: float,
    forward_available_at: datetime,
    rate_available_at: datetime,
    quote_available_at: datetime,
) -> MoGreeksSnapshot:
    """Intraday wrapper over the shared Black-76 primitives."""

    route_time = _require_aware(route_time, name="route_time")
    expiry_time = _require_aware(expiry_time, name="expiry_time")
    option_month = contract_month_from_symbol(option_symbol)
    if option_month is None:
        raise ValidationError(f"cannot parse MO month from {option_symbol}")

    forward_status = "ok"
    if option_month != forward_month:
        forward_status = "forward_month_mismatch"
    for name, moment in (
        ("forward_available_at", forward_available_at),
        ("rate_available_at", rate_available_at),
        ("quote_available_at", quote_available_at),
    ):
        _require_aware(moment, name=name)
    if forward_available_at > route_time:
        forward_status = "future_quote"
    if rate_available_at > route_time:
        forward_status = "future_quote"
    if quote_available_at > route_time:
        forward_status = "future_quote"
    if forward_price <= 0.0 or not math.isfinite(forward_price):
        forward_status = "missing_forward"
    if not math.isfinite(risk_free_rate):
        forward_status = "missing_forward"

    seconds = (expiry_time - route_time).total_seconds()
    if seconds <= 0.0:
        forward_status = "missing_forward"
    years = seconds / (365.25 * 86_400.0)

    identity = parse_mo_identity(option_symbol)
    strike = identity.strike
    if strike is None:
        raise ValidationError("MO strike is required")
    is_call = np.asarray([identity.option_type == "call"])
    rate = np.asarray([risk_free_rate], dtype=float)
    forward = np.asarray([forward_price], dtype=float)
    strike_arr = np.asarray([strike], dtype=float)
    years_arr = np.asarray([years], dtype=float)

    def _invert(premium: float | None) -> tuple[float | None, str]:
        if (
            premium is None
            or forward_price <= 0.0
            or forward_status != "ok"
            or years <= 0.0
            or not math.isfinite(premium)
            or premium <= 0.0
        ):
            return None, "solver_failed"
        sigma, status = invert_black76_iv(
            np.asarray([premium], dtype=float),
            forward,
            strike_arr,
            years_arr,
            is_call,
            rate,
        )
        iv = float(sigma[0])
        if status[0] != IV_STATUS_OK or not math.isfinite(iv):
            return None, str(status[0])
        return iv, IV_STATUS_OK

    iv_bid, bid_status = _invert(bid_premium)
    iv_mid, mid_status = _invert(mid_premium)
    iv_ask, ask_status = _invert(ask_premium)

    all_iv_ok = all(
        status == IV_STATUS_OK for status in (bid_status, mid_status, ask_status)
    )
    monotone_iv = (
        iv_bid is not None
        and iv_mid is not None
        and iv_ask is not None
        and iv_bid <= iv_mid <= iv_ask
    )
    reference_iv = iv_mid if all_iv_ok and monotone_iv else None
    iv_status = IV_STATUS_OK if reference_iv is not None else "incomplete_bid_mid_ask_iv"
    if reference_iv is None:
        return MoGreeksSnapshot(
            forward=forward_price,
            forward_month=forward_month,
            risk_free_rate=risk_free_rate,
            seconds_to_expiry=seconds,
            years_to_expiry=years,
            iv_bid=iv_bid,
            iv_mid=iv_mid,
            iv_ask=iv_ask,
            delta_forward=None,
            gamma_forward=None,
            vega=None,
            theta_per_year=None,
            iv_status=iv_status,
            forward_status=forward_status,
        )
    sigma = np.asarray([reference_iv], dtype=float)
    _price, delta, gamma, vega, theta, _rho = black76_discounted(
        forward,
        strike_arr,
        years_arr,
        sigma,
        is_call,
        rate,
    )
    return MoGreeksSnapshot(
        forward=forward_price,
        forward_month=forward_month,
        risk_free_rate=risk_free_rate,
        seconds_to_expiry=seconds,
        years_to_expiry=years,
        iv_bid=iv_bid,
        iv_mid=iv_mid,
        iv_ask=iv_ask,
        delta_forward=float(delta[0]),
        gamma_forward=float(gamma[0]),
        vega=float(vega[0]),
        theta_per_year=float(theta[0]),
        iv_status=IV_STATUS_OK,
        forward_status=forward_status,
    )


def build_etf_carrier_evaluation(
    *,
    forecast: OpportunityForecast,
    notional: float,
    etf_price: float,
    cost: EtfCostBreakdown,
    account: EtfAccountState,
    shares_to_trade: float,
    expected_beta: float = 1.0,
    liquidity_uncertainty_bps: float = 0.0,
    formula_digest: str = "etf_v1",
) -> CarrierEvaluation:
    del etf_price  # reserved for future share sizing audits
    expected_holding = forecast.minimum_holding_seconds
    legal, rejection_codes = etf_route_legality(
        route_time=forecast.route_time,
        direction=forecast.direction,
        account=account,
        shares_to_trade=shares_to_trade,
        expected_holding_seconds=expected_holding,
    )
    expected_index_bp = forecast.expected_underlying_return_mean_bp.value or 0.0
    gross = notional * expected_beta * expected_index_bp / 10_000.0
    round_trip_bps = etf_round_trip_cost_bps(cost)
    expected_net = gross - _bps_to_cash(round_trip_bps, notional)
    cvar = _bps_to_cash(
        max(0.0, -(forecast.expected_underlying_return_p10_bp.value or 0.0)),
        notional,
    )
    spread_bps_diag = 2.0 * cost.half_spread_bps
    fee_bps_diag = 2.0 * cost.commission_bps_per_side + cost.stamp_tax_bps
    liquidity_cash = _bps_to_cash(liquidity_uncertainty_bps, notional)
    tracking_cash = _bps_to_cash(cost.tracking_or_basis_bps, notional)
    complete = cost.execution_quality_status == "ok"
    return CarrierEvaluation(
        contract_id=CARRIER_CONTRACT,
        infrastructure_id=INFRASTRUCTURE_ID,
        carrier_id=BASELINE_ETF_SYMBOL,
        carrier_type="etf",
        instrument_id=f"etf:{BASELINE_ETF_SYMBOL}",
        eligible=legal and forecast.direction != 0,
        rejection_codes=rejection_codes,
        expected_net_pnl=expected_net,
        cvar=cvar,
        liquidity_uncertainty=liquidity_cash,
        tracking_or_basis_penalty=tracking_cash,
        spread_bps=spread_bps_diag,
        fee_bps=fee_bps_diag,
        impact_bps=cost.impact_bps,
        eas_full_spread_bp=None,
        all_in_hurdle_bp=None,
        actual_units=shares_to_trade,
        delta_equivalent_notional=notional,
        risk_budget_id="UNRESOLVED_COMMON_CVAR",
        risk_budget_cash=0.0,
        risk_sizing_ready=False,
        complete_cost_ready=complete,
        formula_digest=formula_digest,
    )


def build_mo_carrier_evaluation(
    *,
    forecast: OpportunityForecast,
    option_symbol: str,
    contracts: int,
    greeks: MoGreeksSnapshot,
    quote: QuoteSnapshot | None,
    impact_points: float | None = None,
    max_quote_staleness_seconds: int,
    liquidity_uncertainty_bps: float = 0.0,
    formula_digest: str = "mo_v1",
) -> CarrierEvaluation:
    rejection_codes: list[str] = []
    if max_quote_staleness_seconds <= 0:
        raise ValidationError("max_quote_staleness_seconds must be positive")
    identity = parse_mo_identity(option_symbol)
    expected_instrument_id = f"mo:{option_symbol}"

    if contracts <= 0:
        rejection_codes.append("NONPOSITIVE_CONTRACT_COUNT")
    if not mo_option_matches_forecast(forecast.direction, identity.option_type or "call"):
        rejection_codes.append("MO_OPTION_DIRECTION_MISMATCH")
    if greeks.forward_status != "ok":
        rejection_codes.append("FORWARD_MONTH_MISMATCH")
    if greeks.iv_status != IV_STATUS_OK or greeks.delta_forward is None:
        rejection_codes.append("GREEKS_UNAVAILABLE")
    if quote is None:
        rejection_codes.append("QUOTE_UNAVAILABLE")
    elif quote.instrument_id != expected_instrument_id:
        rejection_codes.append("QUOTE_IDENTITY_MISMATCH")
    elif quote.status != "ok" or quote.bid is None or quote.ask is None:
        rejection_codes.append("QUOTE_UNAVAILABLE")
    elif quote.available_at > forecast.route_time or quote.bucket_end > forecast.route_time:
        rejection_codes.append("NONCAUSAL_QUOTE")
    else:
        age = (forecast.route_time - quote.bucket_end).total_seconds()
        if age < 0.0 or age > max_quote_staleness_seconds:
            rejection_codes.append("STALE_QUOTE")

    delta = greeks.delta_forward or 0.0
    forward = greeks.forward
    eas_bp = None
    eas_status: QuoteStatus = "quote_unavailable"
    if quote is not None and quote.bid is not None and quote.ask is not None:
        eas_bp, eas_status = compute_eas_full_spread_bp(
            bid=quote.bid,
            ask=quote.ask,
            delta_forward=delta,
            forward=forward,
        )
    if eas_status != "ok":
        rejection_codes.append(eas_status.upper())
    half_spread = 0.0
    if quote is not None and quote.bid is not None and quote.ask is not None:
        half_spread = 0.5 * (quote.ask - quote.bid)
    hurdle = compute_all_in_hurdle_bp(
        entry_half_spread_points=half_spread,
        exit_half_spread_points=half_spread,
        fee_points=mo_fee_points(),
        impact_points=impact_points,
        delta_forward=delta,
        forward=forward,
        include_theta_in_hurdle=False,
    )
    if not hurdle.complete_cost_ready:
        rejection_codes.append("INCOMPLETE_COST")
    expected_index_bp = forecast.expected_underlying_return_mean_bp.value or 0.0
    delta_notional = abs(delta) * forward * MO_CONTRACT_MULTIPLIER * contracts
    expected_net = delta_notional * expected_index_bp / 10_000.0
    if hurdle.total_bps is not None:
        expected_net -= _bps_to_cash(hurdle.total_bps, delta_notional)
    cvar = _bps_to_cash(
        max(0.0, -(forecast.expected_underlying_return_p10_bp.value or 0.0)),
        delta_notional,
    )
    liquidity_cash = _bps_to_cash(liquidity_uncertainty_bps, delta_notional)
    return CarrierEvaluation(
        contract_id=CARRIER_CONTRACT,
        infrastructure_id=INFRASTRUCTURE_ID,
        carrier_id=option_symbol,
        carrier_type="mo",
        instrument_id=expected_instrument_id,
        eligible=len(rejection_codes) == 0 and forecast.direction != 0,
        rejection_codes=tuple(rejection_codes),
        expected_net_pnl=expected_net,
        cvar=cvar,
        liquidity_uncertainty=liquidity_cash,
        tracking_or_basis_penalty=0.0,
        spread_bps=hurdle.spread_bps or 0.0,
        fee_bps=hurdle.fee_bps or 0.0,
        impact_bps=hurdle.impact_bps or 0.0,
        eas_full_spread_bp=eas_bp,
        all_in_hurdle_bp=hurdle,
        actual_units=float(contracts),
        delta_equivalent_notional=delta_notional,
        risk_budget_id="UNRESOLVED_COMMON_CVAR",
        risk_budget_cash=0.0,
        risk_sizing_ready=False,
        complete_cost_ready=hurdle.complete_cost_ready,
        formula_digest=formula_digest,
    )


def no_trade_carrier_evaluation(*, formula_digest: str = "no_trade_v1") -> CarrierEvaluation:
    return CarrierEvaluation(
        contract_id=CARRIER_CONTRACT,
        infrastructure_id=INFRASTRUCTURE_ID,
        carrier_id="NO_TRADE",
        carrier_type="no_trade",
        instrument_id="no_trade",
        eligible=True,
        rejection_codes=(),
        expected_net_pnl=0.0,
        cvar=0.0,
        liquidity_uncertainty=0.0,
        tracking_or_basis_penalty=0.0,
        spread_bps=0.0,
        fee_bps=0.0,
        impact_bps=0.0,
        eas_full_spread_bp=None,
        all_in_hurdle_bp=None,
        actual_units=0.0,
        delta_equivalent_notional=0.0,
        risk_budget_id="NO_TRADE",
        risk_budget_cash=0.0,
        risk_sizing_ready=True,
        complete_cost_ready=True,
        formula_digest=formula_digest,
    )


__all__ = [
    "AllInHurdleBP",
    "BASELINE_ETF_LISTING_DATE",
    "BASELINE_ETF_SYMBOL",
    "CARRIER_CONTRACT",
    "CarrierEvaluation",
    "CarrierType",
    "ETF_COMMISSION_BPS_PER_SIDE",
    "ETF_STAMP_TAX_BPS",
    "EtfAccountState",
    "EtfCostBreakdown",
    "INFRASTRUCTURE_ID",
    "InstrumentIdentity",
    "InstrumentUniverseSnapshot",
    "MO_MIN_ABS_DELTA",
    "MO_ROUND_TRIP_FEE_YUAN",
    "MoGreeksSnapshot",
    "PITMarketSnapshot",
    "PIT_SNAPSHOT_CONTRACT",
    "PITField",
    "QuoteSnapshot",
    "QuoteStatus",
    "UNIVERSE_CONTRACT",
    "baseline_etf_identity",
    "build_etf_carrier_evaluation",
    "build_instrument_universe_snapshot",
    "build_mo_carrier_evaluation",
    "compute_all_in_hurdle_bp",
    "compute_eas_full_spread_bp",
    "enumerate_instrument_universe",
    "etf_cost_breakdown",
    "etf_route_legality",
    "etf_round_trip_cost_bps",
    "evaluate_intraday_black76",
    "mo_fee_points",
    "mo_option_matches_forecast",
    "no_trade_carrier_evaluation",
    "parse_mo_identity",
    "snapshot_asof",
]
