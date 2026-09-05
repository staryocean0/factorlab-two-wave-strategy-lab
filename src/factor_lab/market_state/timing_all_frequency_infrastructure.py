# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportOperatorIssue=false, reportReturnType=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownLambdaType=false, reportUnknownVariableType=false
# ruff: noqa: E501
"""Legacy mixed all-frequency implementation retained for compatibility.

Current public ownership is split across
``timing_layer2_all_frequency_measurements``,
``strategy.research.timing.all_frequency_strategy_diagnostics``, and
``timing_layer4_all_frequency_execution``.  This module retains unchanged
implementation functions and historical imports but is not one current layer.

The module separates four identities that older timing paths often mixed:

* bar frequency and decision cadence;
* signal lookback and maximum holding horizon;
* descriptive statistics and strategy selection;
* reference prices and actually visible/executable prices.

It accepts any already-governed, pre-bucketed frequency.  Frequency classes
are descriptive labels only and may never select a formula or strategy route.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Literal

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.data.session_offset_defaults import unified_kline_variants_v3

SCHEMA_ID = "market_state_all_frequency_timing_infrastructure@2.1"
INFRASTRUCTURE_ID = "market_state_all_frequency_timing_infrastructure_v2_1"
MO_CONTRACT_MULTIPLIER = 100
INDEX_OPTION_FEE_RMB_PER_CONTRACT_SIDE = 14.0

TimestampSemantics = Literal["bar_start", "bar_end", "explicit_start_end"]
SessionBoundaryPolicy = Literal["reset", "include_overnight"]
SessionBreakPolicy = Literal["cn_equity_lunch", "none"]
SourceKind = Literal[
    "native_trade",
    "native_bar",
    "derived_offset_bar",
    "daily_decision_view",
    "arbitrary_prebucketed",
]
OptionFamily = Literal["index_option", "futures_option", "etf_option"]
FeeStatus = Literal["bound", "unbound"]


def _timestamp_value(value: pd.Timestamp | str) -> int:
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        raise ValidationError("timestamp must not be NaT")
    return int(timestamp.value)


@dataclass(frozen=True, slots=True)
class FrequencyContract:
    """Physical sampling identity independent of any timing formula."""

    view_id: str
    bar_duration_seconds: int
    decision_cadence_seconds: int
    observations_per_session: int
    sessions_per_year: int
    timestamp_semantics: TimestampSemantics
    session_boundary_policy: SessionBoundaryPolicy
    session_break_policy: SessionBreakPolicy
    source_kind: SourceKind
    registered_view: bool = True
    research_only: bool = True
    production_authority: bool = False

    def __post_init__(self) -> None:
        if not self.view_id:
            raise ValidationError("frequency view_id must not be empty")
        positive = (
            self.bar_duration_seconds,
            self.decision_cadence_seconds,
            self.observations_per_session,
            self.sessions_per_year,
        )
        if any(value <= 0 for value in positive):
            raise ValidationError("frequency durations and observation counts must be positive")
        if self.timestamp_semantics not in {"bar_start", "bar_end", "explicit_start_end"}:
            raise ValidationError("unsupported timestamp semantics")
        if self.session_boundary_policy not in {"reset", "include_overnight"}:
            raise ValidationError("unsupported session-boundary policy")
        if self.session_break_policy not in {"cn_equity_lunch", "none"}:
            raise ValidationError("unsupported session-break policy")
        if self.production_authority:
            raise ValidationError("all-frequency V1 cannot grant production authority")

    @property
    def annualization_observations(self) -> int:
        return self.observations_per_session * self.sessions_per_year

    @property
    def frequency_class(self) -> str:
        """Diagnostic label only; it has zero routing authority."""

        if self.bar_duration_seconds <= 60:
            return "microstructure"
        if self.bar_duration_seconds <= 30 * 60:
            return "high_frequency"
        if self.bar_duration_seconds < 24 * 60 * 60:
            return "intraday_normal"
        return "interday_normal"

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "annualization_observations": self.annualization_observations,
            "frequency_class": self.frequency_class,
            "frequency_class_routing_authority": False,
            "overlapping_decision_grid": (
                self.decision_cadence_seconds < self.bar_duration_seconds
            ),
        }


@dataclass(frozen=True, slots=True)
class TimingHorizonContract:
    """Signal span and holding horizon; neither is inferred from the other."""

    horizon_id: str
    frequency: FrequencyContract
    signal_span_bars: int
    maximum_holding_bars: int
    allow_overnight: bool
    force_flat_clock: str | None

    def __post_init__(self) -> None:
        if not self.horizon_id:
            raise ValidationError("timing horizon_id must not be empty")
        if self.signal_span_bars < 1 or self.maximum_holding_bars < 1:
            raise ValidationError("signal and holding bars must be positive")
        if not self.allow_overnight and self.force_flat_clock is None:
            raise ValidationError("intraday-only horizon must declare a force-flat clock")

    @property
    def signal_span_seconds(self) -> int:
        return self.signal_span_bars * self.frequency.bar_duration_seconds

    @property
    def maximum_holding_seconds(self) -> int:
        return self.maximum_holding_bars * self.frequency.bar_duration_seconds

    def to_dict(self) -> dict[str, object]:
        return {
            "horizon_id": self.horizon_id,
            "frequency_view_id": self.frequency.view_id,
            "signal_span_bars": self.signal_span_bars,
            "signal_span_seconds": self.signal_span_seconds,
            "maximum_holding_bars": self.maximum_holding_bars,
            "maximum_holding_seconds": self.maximum_holding_seconds,
            "allow_overnight": self.allow_overnight,
            "force_flat_clock": self.force_flat_clock,
            "signal_span_equals_holding_horizon": (
                self.signal_span_seconds == self.maximum_holding_seconds
            ),
        }


@dataclass(frozen=True, slots=True)
class OptionFeeScheduleV2:
    """Dated, option-family-specific fee identity."""

    option_family: OptionFamily = "index_option"
    product_id: str = "MO"
    contract_multiplier: int | None = MO_CONTRACT_MULTIPLIER
    fee_rmb_per_contract_side: float | None = INDEX_OPTION_FEE_RMB_PER_CONTRACT_SIDE
    fee_status: FeeStatus = "bound"
    effective_from: str = "2022-07-22"
    effective_to: str | None = None
    source_reference: str = "user_authorized_index_option_cost_contract_20260828"

    def __post_init__(self) -> None:
        if self.option_family not in {"index_option", "futures_option", "etf_option"}:
            raise ValidationError("unsupported option family")
        if self.fee_status == "bound":
            if self.fee_rmb_per_contract_side is None or self.fee_rmb_per_contract_side < 0.0:
                raise ValidationError("bound option fee must be non-negative")
            if self.contract_multiplier is None or self.contract_multiplier <= 0:
                raise ValidationError("bound option fee requires a contract multiplier")
        elif self.fee_status == "unbound":
            if self.fee_rmb_per_contract_side is not None:
                raise ValidationError("unbound option family cannot carry a fee value")
        else:
            raise ValidationError("unsupported option fee status")
        if self.option_family == "index_option" and (
            self.product_id != "MO"
            or self.contract_multiplier != 100
            or self.fee_status != "bound"
            or self.fee_rmb_per_contract_side != 14.0
        ):
            raise ValidationError("current MO index-option fee identity must remain CNY14")
        if self.option_family in {"futures_option", "etf_option"} and self.fee_status != "unbound":
            raise ValidationError("futures/ETF option fees remain unbound")
        if not self.effective_from or not self.source_reference:
            raise ValidationError("fee schedule requires date and provenance")
        start = _timestamp_value(self.effective_from)
        if self.effective_to is not None and _timestamp_value(self.effective_to) < start:
            raise ValidationError("fee schedule effective interval is invalid")

    @property
    def total_fee_rmb_per_contract_side(self) -> float | None:
        return self.fee_rmb_per_contract_side

    def applies_at(self, timestamp: pd.Timestamp | str) -> bool:
        value = _timestamp_value(timestamp)
        start = _timestamp_value(self.effective_from)
        end = (
            _timestamp_value(self.effective_to)
            if self.effective_to is not None
            else None
        )
        return value >= start and (end is None or value <= end)

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "total_fee_rmb_per_contract_side": self.total_fee_rmb_per_contract_side,
            "fee_value_authority": self.fee_status == "bound",
        }


def unbound_option_fee_schedule(
    *,
    option_family: Literal["futures_option", "etf_option"],
    product_id: str,
    contract_multiplier: int | None,
) -> OptionFeeScheduleV2:
    return OptionFeeScheduleV2(
        option_family=option_family,
        product_id=product_id,
        contract_multiplier=contract_multiplier,
        fee_rmb_per_contract_side=None,
        fee_status="unbound",
        effective_from="2026-08-28",
        source_reference="user_declared_fee_pending_20260828",
    )


@dataclass(frozen=True, slots=True)
class OptionPriceObservation:
    """Exact quote or declared spread proxy available at a known time."""

    reference_price: float
    available_at: str
    source_id: str
    contract_symbol: str
    bid_price: float | None = None
    ask_price: float | None = None
    estimated_half_spread_rate: float | None = None
    synchronized_l1: bool = False

    def __post_init__(self) -> None:
        if (
            self.reference_price <= 0.0
            or not self.available_at
            or not self.source_id
            or not self.contract_symbol
        ):
            raise ValidationError("option observation requires positive price, time and source")
        try:
            _ = _timestamp_value(self.available_at)
        except (TypeError, ValueError) as exc:
            raise ValidationError("option observation available_at is invalid") from exc
        exact = self.bid_price is not None or self.ask_price is not None
        if exact:
            if self.bid_price is None or self.ask_price is None:
                raise ValidationError("exact option quote requires both bid and ask")
            if not 0.0 < self.bid_price <= self.ask_price:
                raise ValidationError("option quote must satisfy 0 < bid <= ask")
            if self.estimated_half_spread_rate is not None:
                raise ValidationError("exact quote and spread proxy are mutually exclusive")
            if not self.synchronized_l1:
                raise ValidationError("bid/ask quote must declare synchronized_l1")
        else:
            spread = self.estimated_half_spread_rate
            if spread is None or not 0.0 <= spread < 1.0:
                raise ValidationError("proxy observation requires a valid half-spread rate")
            if self.synchronized_l1:
                raise ValidationError("spread proxy cannot claim synchronized L1")

    @property
    def quality(self) -> str:
        return "exact_synchronized_l1" if self.synchronized_l1 else "declared_spread_proxy"

    def buyer_entry_price(self) -> float:
        if self.ask_price is not None:
            return self.ask_price
        assert self.estimated_half_spread_rate is not None
        return self.reference_price * (1.0 + self.estimated_half_spread_rate)

    def buyer_exit_price(self) -> float:
        if self.bid_price is not None:
            return self.bid_price
        assert self.estimated_half_spread_rate is not None
        return self.reference_price * (1.0 - self.estimated_half_spread_rate)


@dataclass(frozen=True, slots=True)
class OptionRoundTripCostV2:
    entry_executable_price: float
    exit_executable_price: float
    contracts: int
    contract_multiplier: int
    premium_cash_rmb: float
    gross_return: float
    transaction_drag_bp: float
    fixed_fee_rmb: float
    fixed_fee_tax_bp: float
    net_return: float
    theta_attribution_bp: float
    entry_quality: str
    exit_quality: str
    impact_model: str
    theta_double_subtracted: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OptionAskBidRoundTripCostV3:
    """One authoritative long-option replay: buy ASK, sell BID, then pay fees."""

    entry_ask_price: float
    exit_bid_price: float
    contracts: int
    contract_multiplier: int
    premium_cash_rmb: float
    reference_return: float
    ask_bid_return_before_fee: float
    ask_bid_execution_difference_bp: float
    fixed_fee_rmb: float
    fixed_fee_tax_bp: float
    net_return: float
    theta_attribution_bp: float
    execution_method: str = "synchronized_l1_ask_entry_bid_exit"
    explicit_cost_components: tuple[str, ...] = ("fixed_fee",)
    proxy_spread_applied: bool = False
    market_impact_applied: bool = False
    theta_double_subtracted: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def price_long_option_round_trip_v2(
    *,
    entry: OptionPriceObservation,
    exit_: OptionPriceObservation,
    fees: OptionFeeScheduleV2,
    contracts: int,
    market_impact_bp_per_side: float,
    market_impact_model: str,
    theta_attribution_bp: float,
) -> OptionRoundTripCostV2:
    """Historical proxy/impact path, revoked from current backtest authority."""

    _ = (
        entry,
        exit_,
        fees,
        contracts,
        market_impact_bp_per_side,
        market_impact_model,
        theta_attribution_bp,
    )
    message = "price_long_option_round_trip_v2 is historical-only and revoked;"
    message += " use price_long_option_round_trip_ask_bid_v3"
    raise ValidationError(message)


def price_long_option_round_trip_ask_bid_v3(
    *,
    entry: OptionPriceObservation,
    exit_: OptionPriceObservation,
    fees: OptionFeeScheduleV2,
    contracts: int,
    theta_attribution_bp: float,
) -> OptionAskBidRoundTripCostV3:
    """Buy at synchronized ASK, sell at synchronized BID, and deduct only fees.

    Bid/ask movement already contains spread, volatility and time-value changes.
    No proxy spread, additional market impact or theta charge is accepted here.
    """

    if contracts < 1:
        raise ValidationError("option contracts must be positive")
    if theta_attribution_bp < 0.0:
        raise ValidationError("theta attribution must be non-negative")
    if entry.quality != "exact_synchronized_l1" or exit_.quality != "exact_synchronized_l1":
        raise ValidationError("current option backtest requires synchronized L1 ASK/BID")
    entry_time = _timestamp_value(entry.available_at)
    exit_time = _timestamp_value(exit_.available_at)
    if exit_time <= entry_time:
        raise ValidationError("option exit must be visible after entry")
    if entry.contract_symbol != exit_.contract_symbol:
        raise ValidationError("option round trip must freeze one contract identity")
    fee_per_side = fees.total_fee_rmb_per_contract_side
    if fee_per_side is None:
        raise ValidationError("option-family fee is unbound; net pricing must fail closed")
    multiplier = fees.contract_multiplier
    if multiplier is None:
        raise ValidationError("bound option-family fee requires a contract multiplier")
    if not fees.applies_at(entry.available_at) or not fees.applies_at(exit_.available_at):
        raise ValidationError("option fee schedule does not cover the round trip")
    assert entry.ask_price is not None
    assert exit_.bid_price is not None
    entry_ask = entry.ask_price
    exit_bid = exit_.bid_price
    units = multiplier * contracts
    premium_cash = entry_ask * units
    reference_return = exit_.reference_price / entry.reference_price - 1.0
    ask_bid_return = exit_bid / entry_ask - 1.0
    fixed_fee = 2.0 * fee_per_side * contracts
    fixed_fee_tax_bp = fixed_fee / premium_cash * 10_000.0
    return OptionAskBidRoundTripCostV3(
        entry_ask_price=entry_ask,
        exit_bid_price=exit_bid,
        contracts=contracts,
        contract_multiplier=multiplier,
        premium_cash_rmb=premium_cash,
        reference_return=reference_return,
        ask_bid_return_before_fee=ask_bid_return,
        ask_bid_execution_difference_bp=(reference_return - ask_bid_return) * 10_000.0,
        fixed_fee_rmb=fixed_fee,
        fixed_fee_tax_bp=fixed_fee_tax_bp,
        net_return=ask_bid_return - fixed_fee / premium_cash,
        theta_attribution_bp=theta_attribution_bp,
    )


def resolve_first_visible_bar_close(
    bars: pd.DataFrame,
    *,
    decision_time: pd.Timestamp | str,
    decision_trading_day: str,
    max_wait_seconds: int,
    require_positive_volume: bool = True,
) -> dict[str, object] | None:
    """Resolve by price availability, not by a strict bar-start comparison.

    A bar starting exactly at the decision is eligible because its close is
    used only at the later ``bar_end``.  A bar that began before the decision
    is ineligible because its close mixes pre-decision transactions.
    """

    required = {"bar_start", "bar_end", "trading_day", "close", "volume"}
    missing = sorted(required.difference(bars.columns))
    if missing:
        raise ValidationError(f"visible-bar input missing columns: {missing}")
    if max_wait_seconds < 1:
        raise ValidationError("max_wait_seconds must be positive")
    decision = pd.Timestamp(decision_time)
    frame = bars.copy()
    frame["bar_start"] = pd.to_datetime(frame["bar_start"], errors="raise")
    frame["bar_end"] = pd.to_datetime(frame["bar_end"], errors="raise")
    frame["close"] = pd.to_numeric(frame["close"], errors="raise")
    frame["volume"] = pd.to_numeric(frame["volume"], errors="raise")
    frame["trading_day"] = frame["trading_day"].astype(str)
    deadline = decision + pd.Timedelta(seconds=max_wait_seconds)
    mask = (
        frame["bar_start"].ge(decision)
        & frame["bar_end"].gt(decision)
        & frame["bar_end"].le(deadline)
        & frame["trading_day"].eq(str(decision_trading_day))
        & frame["close"].gt(0.0)
    )
    if require_positive_volume:
        mask &= frame["volume"].gt(0.0)
    eligible = frame.loc[mask].sort_values(
        ["bar_end", "bar_start"], kind="mergesort"
    )
    if eligible.empty:
        return None
    row = eligible.iloc[0]
    available_at = pd.Timestamp(row["bar_end"])
    return {
        "fill_bar_start": pd.Timestamp(row["bar_start"]),
        "fill_available_at": available_at,
        "fill_price": float(row["close"]),
        "fill_volume": float(row["volume"]),
        "latency_seconds": float((available_at - decision).total_seconds()),
        "price_semantics": "bar_close_visible_at_bar_end",
    }


def arbitrary_prebucketed_frequency_contract(
    *,
    view_id: str,
    bar_duration_seconds: int,
    decision_cadence_seconds: int,
    observations_per_session: int,
    session_boundary_policy: SessionBoundaryPolicy,
    session_break_policy: SessionBreakPolicy = "cn_equity_lunch",
    timestamp_semantics: TimestampSemantics = "bar_end",
    sessions_per_year: int = 244,
) -> FrequencyContract:
    """Construct a governed custom view without local resampling authority."""

    return FrequencyContract(
        view_id=view_id,
        bar_duration_seconds=bar_duration_seconds,
        decision_cadence_seconds=decision_cadence_seconds,
        observations_per_session=observations_per_session,
        sessions_per_year=sessions_per_year,
        timestamp_semantics=timestamp_semantics,
        session_boundary_policy=session_boundary_policy,
        session_break_policy=session_break_policy,
        source_kind="arbitrary_prebucketed",
        registered_view=False,
    )


def registered_frequency_contracts() -> tuple[FrequencyContract, ...]:
    """Return 3-second execution plus every governed V3 K-line view."""

    result = [
        FrequencyContract(
            view_id="3s_native_trade",
            bar_duration_seconds=3,
            decision_cadence_seconds=3,
            observations_per_session=4_800,
            sessions_per_year=244,
            timestamp_semantics="explicit_start_end",
            session_boundary_policy="reset",
            session_break_policy="cn_equity_lunch",
            source_kind="native_trade",
        )
    ]
    duration_by_frequency = {
        "1m": 60,
        "5m": 5 * 60,
        "15m": 15 * 60,
        "30m": 30 * 60,
        "60m": 60 * 60,
    }
    for raw in unified_kline_variants_v3():
        view_id = str(raw["view_id"])
        close_times = tuple(raw.get("close_times", ()))
        if view_id.startswith("daily_"):
            duration = 24 * 60 * 60
            observations = 1
            boundary: SessionBoundaryPolicy = "include_overnight"
            break_policy: SessionBreakPolicy = "none"
            source_kind: SourceKind = "daily_decision_view"
        else:
            frequency = str(raw["frequency"])
            duration = duration_by_frequency[frequency]
            observations = len(close_times)
            boundary = "reset"
            break_policy = "cn_equity_lunch"
            source_kind = "native_bar" if view_id == "1m_official" else "derived_offset_bar"
        result.append(
            FrequencyContract(
                view_id=view_id,
                bar_duration_seconds=duration,
                decision_cadence_seconds=duration,
                observations_per_session=observations,
                sessions_per_year=244,
                timestamp_semantics="bar_end",
                session_boundary_policy=boundary,
                session_break_policy=break_policy,
                source_kind=source_kind,
            )
        )
    return tuple(result)


def _numeric_price_panel(prices: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(prices.index, pd.DatetimeIndex):
        raise ValidationError("price panel requires a DatetimeIndex")
    if prices.empty or prices.shape[1] < 1:
        raise ValidationError("price panel must be non-empty")
    if prices.index.has_duplicates or not prices.index.is_monotonic_increasing:
        raise ValidationError("price panel timestamps must be unique and ordered")
    numeric = prices.apply(pd.to_numeric, errors="raise").astype(float)
    finite_or_missing = np.isfinite(numeric.to_numpy()) | numeric.isna().to_numpy()
    if not bool(finite_or_missing.all()):
        raise ValidationError("price panel contains non-finite values")
    if bool(numeric.le(0.0).any().any()):
        raise ValidationError("price panel values must be positive")
    return numeric


def _return_panels(
    prices: pd.DataFrame,
    *,
    contract: FrequencyContract,
    trading_day: pd.Series | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    numeric = _numeric_price_panel(prices)
    if contract.session_boundary_policy == "reset":
        if trading_day is None:
            raise ValidationError("session-reset returns require trading_day")
        days = trading_day.reindex(numeric.index)
        if days.isna().any():
            raise ValidationError("trading_day must cover every price timestamp")
        prior = numeric.groupby(days, sort=False).shift(1)
        simple = numeric / prior - 1.0
        log_return = np.log(numeric) - np.log(prior)
    else:
        simple = numeric.pct_change(fill_method=None)
        log_return = np.log(numeric).diff()
    return simple, log_return


def _lagged_series(
    series: pd.Series,
    *,
    lag: int,
    contract: FrequencyContract,
    trading_day: pd.Series | None,
) -> pd.Series:
    if contract.session_boundary_policy == "reset":
        assert trading_day is not None
        return series.groupby(trading_day.reindex(series.index), sort=False).shift(lag)
    return series.shift(lag)


def _rolling_autocorrelation(
    series: pd.Series,
    *,
    window: int,
    lag: int,
    contract: FrequencyContract,
    trading_day: pd.Series | None,
) -> pd.Series:
    lagged = _lagged_series(
        series,
        lag=lag,
        contract=contract,
        trading_day=trading_day,
    )
    pair = pd.concat([series, lagged], axis=1).dropna()
    result = pair.iloc[:, 0].rolling(window, min_periods=window).corr(pair.iloc[:, 1])
    return result.reindex(series.index)


def build_rolling_frequency_features(
    prices: pd.DataFrame,
    *,
    contract: FrequencyContract,
    trading_day: pd.Series | None,
    lookback_bars: int,
    autocorrelation_lags: tuple[int, ...] = (1, 2, 4),
) -> pd.DataFrame:
    """Build prefix-causal returns, volatility, autocorrelation and covariance."""

    if lookback_bars < 4:
        raise ValidationError("lookback_bars must be at least four")
    if not autocorrelation_lags or min(autocorrelation_lags) < 1:
        raise ValidationError("autocorrelation lags must be positive")
    if max(autocorrelation_lags) + 3 > lookback_bars:
        raise ValidationError("lookback is too short for requested autocorrelation lag")
    simple, returns = _return_panels(
        prices, contract=contract, trading_day=trading_day
    )
    features = pd.DataFrame(index=prices.index)
    annualization = float(contract.annualization_observations)
    for column in returns.columns:
        series = returns[column]
        features[f"simple_return__{column}"] = simple[column]
        features[f"log_return__{column}"] = series
        valid = series.dropna()
        features[f"annualized_volatility__{column}"] = (
            valid.rolling(lookback_bars, min_periods=lookback_bars).std(ddof=1)
            * math.sqrt(annualization)
        ).reindex(features.index)
        for lag in autocorrelation_lags:
            features[f"return_autocorr_lag{lag}__{column}"] = _rolling_autocorrelation(
                series,
                window=lookback_bars,
                lag=lag,
                contract=contract,
                trading_day=trading_day,
            )
            features[f"abs_return_autocorr_lag{lag}__{column}"] = (
                _rolling_autocorrelation(
                    series.abs(),
                    window=lookback_bars,
                    lag=lag,
                    contract=contract,
                    trading_day=trading_day,
                )
            )
            features[f"squared_return_autocorr_lag{lag}__{column}"] = (
                _rolling_autocorrelation(
                    series.pow(2),
                    window=lookback_bars,
                    lag=lag,
                    contract=contract,
                    trading_day=trading_day,
                )
            )
    columns = list(returns.columns)
    for left_index, left in enumerate(columns):
        for right in columns[left_index:]:
            pair = pd.concat([returns[left], returns[right]], axis=1).dropna()
            rolling_left = pair.iloc[:, 0].rolling(
                lookback_bars, min_periods=lookback_bars
            )
            features[f"annualized_covariance__{left}__{right}"] = (
                rolling_left.cov(pair.iloc[:, 1]) * annualization
            ).reindex(features.index)
            features[f"correlation__{left}__{right}"] = rolling_left.corr(
                pair.iloc[:, 1]
            ).reindex(features.index)
    features.attrs["schema_id"] = SCHEMA_ID
    features.attrs["frequency_view_id"] = contract.view_id
    features.attrs["lookback_bars"] = lookback_bars
    features.attrs["future_values_used"] = False
    features.attrs["alignment_policy"] = "exact_timestamp_no_forward_fill"
    return features


def _autocorrelation(
    series: pd.Series,
    lag: int,
    *,
    contract: FrequencyContract,
    trading_day: pd.Series | None,
) -> float | None:
    lagged = _lagged_series(
        series,
        lag=lag,
        contract=contract,
        trading_day=trading_day,
    )
    pair = pd.concat([series, lagged], axis=1).dropna()
    if len(pair) < 3:
        return None
    left = pair.iloc[:, 0].to_numpy(float)
    right = pair.iloc[:, 1].to_numpy(float)
    if np.std(left) <= 0.0 or np.std(right) <= 0.0:
        return None
    return float(np.corrcoef(left, right)[0, 1])


def _sign_persistence(
    series: pd.Series,
    *,
    contract: FrequencyContract,
    trading_day: pd.Series | None,
) -> float | None:
    signs = np.sign(series).replace(0.0, np.nan)
    prior = _lagged_series(
        signs,
        lag=1,
        contract=contract,
        trading_day=trading_day,
    )
    pair = pd.concat([signs, prior], axis=1).dropna()
    if pair.empty:
        return None
    return float((pair.iloc[:, 0] == pair.iloc[:, 1]).mean())


def _path_efficiency(series: pd.Series) -> float:
    clean = pd.to_numeric(series, errors="raise").dropna().astype(float)
    gross_path = float(clean.abs().sum())
    return float(abs(clean.sum()) / gross_path) if gross_path > 0.0 else 0.0


def _variance_ratio(
    series: pd.Series,
    *,
    horizon_bars: int,
    contract: FrequencyContract,
    trading_day: pd.Series | None,
) -> float | None:
    if horizon_bars < 2:
        raise ValidationError("variance-ratio horizon must be at least two")
    numeric = pd.to_numeric(series, errors="raise").astype(float)
    one_bar = numeric.dropna()
    if len(one_bar) < max(8, horizon_bars + 2):
        return None
    if contract.session_boundary_policy == "reset":
        assert trading_day is not None
        days = trading_day.reindex(numeric.index)
        aggregate = pd.DataFrame({"value": numeric, "day": days}).groupby(
            "day", sort=False
        )["value"].transform(
            lambda values: values.rolling(horizon_bars, min_periods=horizon_bars).sum()
        )
    else:
        aggregate = numeric.rolling(
            horizon_bars, min_periods=horizon_bars
        ).sum()
    aggregate = aggregate.dropna()
    one_variance = float(one_bar.var(ddof=1))
    if len(aggregate) < 3 or one_variance <= 0.0:
        return None
    return float(aggregate.var(ddof=1) / (horizon_bars * one_variance))


def _directional_run_mean(
    series: pd.Series,
    *,
    contract: FrequencyContract,
    trading_day: pd.Series | None,
) -> float | None:
    signs = pd.Series(
        np.sign(pd.to_numeric(series, errors="raise").to_numpy(float)),
        index=series.index,
        dtype=float,
    ).replace(0.0, np.nan)
    if contract.session_boundary_policy == "reset":
        assert trading_day is not None
        parts = [
            values
            for _day, values in signs.groupby(
                trading_day.reindex(signs.index), sort=False
            )
        ]
    else:
        parts = [signs]
    lengths: list[int] = []
    for values in parts:
        clean = values.dropna().to_numpy(float)
        if len(clean) == 0:
            continue
        run = 1
        for prior, current in zip(clean[:-1], clean[1:], strict=True):
            if current == prior:
                run += 1
            else:
                lengths.append(run)
                run = 1
        lengths.append(run)
    return float(np.mean(lengths)) if lengths else None


def build_execution_transport_ladder(
    layer_returns: dict[str, pd.Series],
) -> dict[str, object]:
    """Attribute sequential edge loss without granting strategy authority."""

    if len(layer_returns) < 2:
        raise ValidationError("execution transport requires at least two layers")
    names = list(layer_returns)
    if any(not name for name in names) or len(names) != len(set(names)):
        raise ValidationError("execution transport layer names must be unique")
    parts: list[pd.Series] = []
    for name in names:
        source = layer_returns[name]
        parts.append(
            pd.Series(
                pd.to_numeric(source, errors="raise").to_numpy(float),
                index=source.index,
                name=name,
                dtype=float,
            )
        )
    aligned = pd.concat(
        parts,
        axis=1,
        join="inner",
    ).dropna()
    if aligned.empty or not np.isfinite(aligned.to_numpy(float)).all():
        raise ValidationError("execution transport has no finite common observations")
    layers: list[dict[str, object]] = []
    prior_mean: float | None = None
    for name in names:
        mean_return = float(aligned[name].mean())
        layers.append(
            {
                "layer_id": name,
                "mean_return_bp": mean_return * 10_000.0,
                "win_rate": float(aligned[name].gt(0.0).mean()),
                "delta_from_prior_bp": (
                    None
                    if prior_mean is None
                    else (mean_return - prior_mean) * 10_000.0
                ),
            }
        )
        prior_mean = mean_return
    return {
        "observation_count": len(aligned),
        "layers": layers,
        "alignment_policy": "exact_index_inner_join_no_forward_fill",
        "standalone_profitability_gate_authority": False,
        "strategy_selection_authorized": False,
        "production_authority": False,
    }


def _subsampled_realized_variance(
    prices: pd.Series,
    *,
    stride_bars: int,
    contract: FrequencyContract,
    trading_day: pd.Series | None,
) -> float:
    if stride_bars < 1:
        raise ValidationError("subsample stride must be positive")
    log_price = np.log(pd.to_numeric(prices, errors="raise").astype(float))
    if contract.session_boundary_policy == "reset":
        assert trading_day is not None
        groups = (
            part
            for _day, part in log_price.groupby(
                trading_day.reindex(log_price.index), sort=False
            )
        )
    else:
        groups = iter((log_price,))
    total = 0.0
    for part in groups:
        phase_variances: list[float] = []
        for offset in range(stride_bars):
            sparse = part.iloc[offset::stride_bars].diff().dropna()
            if not sparse.empty:
                phase_variances.append(float(np.square(sparse).sum()))
        if phase_variances:
            total += float(np.mean(phase_variances))
    return total


def _matrix_payload(matrix: pd.DataFrame) -> dict[str, object]:
    return {
        "columns": [str(value) for value in matrix.columns],
        "values": [
            [float(value) for value in row]
            for row in matrix.to_numpy(dtype=float)
        ],
    }


def _missing_intervals(
    index: pd.DatetimeIndex,
    *,
    trading_day: pd.Series | None,
    contract: FrequencyContract,
) -> int:
    if trading_day is None:
        return 0
    days = trading_day.reindex(index)
    missing = 0
    for _day, positions in pd.Series(np.arange(len(index)), index=index).groupby(
        days, sort=False
    ):
        timestamps = index[positions.to_numpy(int)]
        for prior, current in zip(timestamps[:-1], timestamps[1:], strict=True):
            if (
                contract.session_break_policy == "cn_equity_lunch"
                and prior.strftime("%H:%M") <= "11:30"
                and current.strftime("%H:%M") >= "13:00"
            ):
                continue
            seconds = float((current - prior).total_seconds())
            missing += max(
                int(round(seconds / contract.decision_cadence_seconds)) - 1,
                0,
            )
    return missing


def diagnose_frequency_panel(
    prices: pd.DataFrame,
    *,
    contract: FrequencyContract,
    trading_day: pd.Series | None,
    lookback_bars: int,
    minimum_observations: int,
    autocorrelation_lags: tuple[int, ...] = (1, 2, 4),
) -> dict[str, object]:
    """Return a JSON-ready, listwise-synchronous diagnostic snapshot."""

    if minimum_observations < 4 or lookback_bars < minimum_observations:
        raise ValidationError("diagnostic lookback/minimum observations are invalid")
    _, returns = _return_panels(prices, contract=contract, trading_day=trading_day)
    window = returns.iloc[-lookback_bars:]
    listwise = window.dropna(how="any")
    if len(listwise) < minimum_observations:
        raise ValidationError("insufficient synchronous returns for diagnostics")
    covariance = listwise.cov(ddof=1)
    annualized_covariance = covariance * contract.annualization_observations
    correlation = listwise.corr()
    symmetric = (annualized_covariance + annualized_covariance.T) / 2.0
    eigenvalues = np.linalg.eigvalsh(symmetric.to_numpy(float))
    per_instrument: dict[str, object] = {}
    days_window = trading_day.reindex(window.index) if trading_day is not None else None
    price_window = prices.iloc[-(lookback_bars + 1) :]
    price_days = (
        trading_day.reindex(price_window.index) if trading_day is not None else None
    )
    subsample_stride = max(
        1,
        int(round(60 / contract.bar_duration_seconds)),
    )
    for column in listwise.columns:
        series = window[column]
        clean = series.dropna()
        lag1 = _autocorrelation(
            series,
            1,
            contract=contract,
            trading_day=days_window,
        )
        prior_absolute = _lagged_series(
            series.abs(),
            lag=1,
            contract=contract,
            trading_day=days_window,
        )
        bipower_pairs = pd.concat([series.abs(), prior_absolute], axis=1).dropna()
        realized_variance = float(np.square(clean).sum())
        bipower_variation = float(
            (math.pi / 2.0)
            * (bipower_pairs.iloc[:, 0] * bipower_pairs.iloc[:, 1]).sum()
        )
        subsampled_variance = _subsampled_realized_variance(
            price_window[column],
            stride_bars=subsample_stride,
            contract=contract,
            trading_day=price_days,
        )
        sign_persistence = _sign_persistence(
            series,
            contract=contract,
            trading_day=days_window,
        )
        per_instrument[str(column)] = {
            "observation_count": len(clean),
            "mean_log_return_per_bar": float(clean.mean()),
            "standard_deviation_per_bar": float(clean.std(ddof=1)),
            "realized_volatility_window": float(math.sqrt(realized_variance)),
            "bipower_variation_window": bipower_variation,
            "jump_variation_share": (
                max(realized_variance - bipower_variation, 0.0) / realized_variance
                if realized_variance > 0.0
                else 0.0
            ),
            "subsample_stride_bars": subsample_stride,
            "subsampled_realized_volatility_window": float(
                math.sqrt(max(subsampled_variance, 0.0))
            ),
            "microstructure_noise_ratio": (
                max(realized_variance - subsampled_variance, 0.0)
                / realized_variance
                if realized_variance > 0.0
                else 0.0
            ),
            "annualized_volatility": float(
                clean.std(ddof=1)
                * math.sqrt(contract.annualization_observations)
            ),
            "zero_return_share": float(clean.abs().lt(1e-12).mean()),
            "path_efficiency_window": _path_efficiency(series),
            "sign_persistence": sign_persistence,
            "direction_reversal_rate": (
                None if sign_persistence is None else 1.0 - sign_persistence
            ),
            "directional_run_mean_bars": _directional_run_mean(
                series,
                contract=contract,
                trading_day=days_window,
            ),
            "variance_ratio": {
                str(horizon): _variance_ratio(
                    series,
                    horizon_bars=horizon,
                    contract=contract,
                    trading_day=days_window,
                )
                for horizon in (4, 8, 16)
            },
            "return_autocorrelation": {
                str(lag): _autocorrelation(
                    series,
                    lag,
                    contract=contract,
                    trading_day=days_window,
                )
                for lag in autocorrelation_lags
            },
            "absolute_return_autocorrelation": {
                str(lag): _autocorrelation(
                    series.abs(),
                    lag,
                    contract=contract,
                    trading_day=days_window,
                )
                for lag in autocorrelation_lags
            },
            "squared_return_autocorrelation": {
                str(lag): _autocorrelation(
                    series.pow(2),
                    lag,
                    contract=contract,
                    trading_day=days_window,
                )
                for lag in autocorrelation_lags
            },
            "bid_ask_bounce_lag1": lag1,
            "bid_ask_bounce_warning": bool(
                contract.frequency_class in {"microstructure", "high_frequency"}
                and lag1 is not None
                and lag1 <= -0.10
            ),
        }
    return {
        "schema_id": SCHEMA_ID,
        "frequency": contract.to_dict(),
        "lookback_bars": lookback_bars,
        "window_start": str(window.index.min()),
        "window_end": str(window.index.max()),
        "synchronous_observation_count": len(listwise),
        "synchronous_coverage": float(len(listwise) / max(len(window), 1)),
        "missing_interval_count": _missing_intervals(
            pd.DatetimeIndex(prices.index),
            trading_day=trading_day,
            contract=contract,
        ),
        "alignment_policy": "exact_timestamp_listwise_no_forward_fill",
        "per_instrument": per_instrument,
        "annualized_covariance": _matrix_payload(annualized_covariance),
        "correlation": _matrix_payload(correlation),
        "covariance_symmetric": bool(
            np.allclose(
                annualized_covariance.to_numpy(float),
                annualized_covariance.to_numpy(float).T,
                atol=1e-12,
            )
        ),
        "covariance_minimum_eigenvalue": float(eigenvalues.min()),
        "covariance_psd": bool(eigenvalues.min() >= -1e-12),
        "covariance_microstructure_warning": any(
            bool(item["bid_ask_bounce_warning"])
            for item in per_instrument.values()
            if isinstance(item, dict)
        ),
        "future_values_used": False,
        "strategy_selection_authorized": False,
        "production_authority": False,
    }


def timing_profitability_attribute_registry() -> dict[str, dict[str, object]]:
    """Evidence-bound interpretation; no single attribute becomes a trade gate."""

    evidence = (
        "docs/ops/evidence/"
        "csi1000_1m_vs_15m_trend_noise_attribution_v1_20260828/"
        "controller_acceptance.json"
    )
    common = {
        "evidence_reference": evidence,
        "standalone_profitability_gate_authority": False,
        "automatic_strategy_routing_authority": False,
    }
    return {
        "path_efficiency": {
            **common,
            "layer": "market_path",
            "implementation_status": "ready_generic_snapshot",
            "profit_relationship": "material_when_paired",
            "evaluation": "Lower physical-horizon efficiency means zigzag consumes displacement; compare on the same physical horizon and pair with signed edge.",
        },
        "jump_variation_share": {
            **common,
            "layer": "market_path",
            "implementation_status": "ready_generic_snapshot",
            "profit_relationship": "material_when_paired",
            "evaluation": "Higher jump share is a material noise burden only relative to path efficiency and edge thickness; noise presence alone is insufficient.",
        },
        "faster_cost_to_positive_revenue": {
            **common,
            "layer": "strategy_account",
            "implementation_status": "strategy_context_required",
            "profit_relationship": "material_when_paired",
            "evaluation": "Strong discriminator of buffer compression, but it requires exact strategy PnL role decomposition and is not a raw-series factor.",
        },
        "mean_trade_edge_thickness": {
            **common,
            "layer": "strategy_account",
            "implementation_status": "strategy_context_required",
            "profit_relationship": "material_when_paired",
            "evaluation": "Per-trade signed edge must be thick enough for execution; aggregate gross or trade count cannot substitute for it.",
        },
        "executable_signed_edge": {
            **common,
            "layer": "execution_transport",
            "implementation_status": "ready_generic_transport_ladder",
            "profit_relationship": "material_when_paired",
            "evaluation": "Measure direction edge again on the executable subset before attributing loss to derivative costs.",
        },
        "execution_transport_ladder": {
            **common,
            "layer": "execution_transport",
            "implementation_status": "ready_generic_transport_ladder",
            "profit_relationship": "material_when_paired",
            "evaluation": "Separate signal/index edge, derivative reference transport and executable ASK-BID; do not collapse them into one cost number.",
        },
        "variance_ratio": {
            **common,
            "layer": "market_path",
            "implementation_status": "ready_generic_snapshot",
            "profit_relationship": "conditional_diagnostic",
            "evaluation": "Persistence or mean reversion clue only; it requires physical-scale and counterexample checks.",
        },
        "microstructure_noise_ratio": {
            **common,
            "layer": "market_path",
            "implementation_status": "ready_generic_snapshot",
            "profit_relationship": "conditional_diagnostic",
            "evaluation": "Useful for identifying fine-grid contamination, but high noise does not imply an unprofitable slower policy.",
        },
        "component_direction_bdci": {
            **common,
            "layer": "signal_state",
            "implementation_status": "implemented_filtering_provider_not_all_frequency",
            "profit_relationship": "conditional_diagnostic",
            "evaluation": "Measures component-state continuity; it must be paired with realized signed edge and trade thickness.",
        },
        "return_autocorrelation": {
            **common,
            "layer": "market_path",
            "implementation_status": "ready_generic_rolling_and_snapshot",
            "profit_relationship": "weak_or_misleading_standalone",
            "evaluation": "Unconditional lag autocorrelation can be higher at an unprofitable frequency and cannot stand in for trend profitability.",
        },
        "raw_sign_persistence": {
            **common,
            "layer": "market_path",
            "implementation_status": "ready_generic_snapshot",
            "profit_relationship": "weak_or_misleading_standalone",
            "evaluation": "High raw sign persistence can coexist with low path efficiency and negative executable edge.",
        },
        "static_neighbor_energy_ratio": {
            **common,
            "layer": "multiscale_energy",
            "implementation_status": "implemented_multiscale_provider",
            "profit_relationship": "weak_or_misleading_standalone",
            "evaluation": "Similar static energy ratios can occur at profitable and unprofitable frequencies; phase propagation and signed payoff are missing.",
        },
        "raw_volatility_level": {
            **common,
            "layer": "market_path",
            "implementation_status": "ready_generic_rolling_and_snapshot",
            "profit_relationship": "weak_or_misleading_standalone",
            "evaluation": "Volatility measures opportunity width, not direction, path cleanliness or executable edge.",
        },
        "component_body_contraction": {
            **common,
            "layer": "signal_state",
            "implementation_status": "research_adapter_only",
            "profit_relationship": "weak_or_misleading_standalone",
            "evaluation": "Late-phase contraction is real hindsight morphology, but causal small bodies also occur at starts and pauses and did not make P128 positive.",
        },
        "trade_count": {
            **common,
            "layer": "strategy_account",
            "implementation_status": "strategy_context_required",
            "profit_relationship": "weak_or_misleading_standalone",
            "evaluation": "More events can increase aggregate idealized gross while reducing edge thickness and execution survivability.",
        },
    }


def build_all_frequency_infrastructure_contract() -> dict[str, object]:
    contracts = registered_frequency_contracts()
    index_option_fee = OptionFeeScheduleV2()
    futures_option_fee = unbound_option_fee_schedule(
        option_family="futures_option",
        product_id="UNBOUND_FUTURES_OPTION",
        contract_multiplier=None,
    )
    etf_option_fee = unbound_option_fee_schedule(
        option_family="etf_option",
        product_id="UNBOUND_ETF_OPTION",
        contract_multiplier=None,
    )
    capabilities = {
        "frequency_identity": "ready",
        "signal_vs_holding_horizon_separation": "ready",
        "simple_and_log_returns": "ready",
        "realized_and_annualized_volatility": "ready",
        "subsampled_and_bipower_high_frequency_volatility": "ready",
        "synchronous_covariance_and_correlation": "ready",
        "return_abs_squared_autocorrelation": "ready",
        "path_efficiency_variance_ratio_and_direction_runs": "ready",
        "profitability_attribute_evaluation_registry": "ready_evidence_bound_no_routing",
        "execution_transport_ladder": "ready_no_strategy_authority",
        "high_frequency_bounce_and_gap_diagnostics": "ready",
        "price_availability_fill_semantics": "ready",
        "index_option_current_CNY14_fee_schedule": "ready",
        "futures_option_fee_schedule": "blocked_user_input",
        "ETF_option_fee_schedule": "blocked_user_input",
        "synchronized_L1_ask_bid_option_backtest": "ready_fail_closed",
        "proxy_spread_option_backtest": "forbidden",
        "additional_market_impact_option_backtest": "forbidden",
        "theta_cost_subtraction_for_observed_option_prices": "forbidden",
        "automatic_strategy_frequency_selection": "forbidden",
    }
    return {
        "schema_id": SCHEMA_ID,
        "infrastructure_id": INFRASTRUCTURE_ID,
        "architecture_role": "layer2_frequency_neutral_timing_measurement",
        "four_layer_role": "layer2_kline_measurement",
        "measurement_authority": True,
        "routing_authority": False,
        "position_output": False,
        "registered_frequency_contracts": [item.to_dict() for item in contracts],
        "registered_view_count": len(contracts),
        "arbitrary_prebucketed_contract_supported": True,
        "local_resampling_authority": False,
        "frequency_class_routing_authority": False,
        "current_option_fee_schedule": index_option_fee.to_dict(),
        "option_fee_family_registry": {
            "index_option": index_option_fee.to_dict(),
            "futures_option": futures_option_fee.to_dict(),
            "etf_option": etf_option_fee.to_dict(),
        },
        "current_option_backtest_contract": {
            "method_id": "synchronized_l1_ask_entry_bid_exit@1.0",
            "entry_price": "ask_price_1",
            "exit_price": "bid_price_1",
            "explicit_cost_components": ["fixed_fee"],
            "proxy_spread_allowed": False,
            "additional_market_impact_allowed": False,
            "theta_subtraction_allowed": False,
            "missing_synchronized_L1_policy": "fail_closed",
        },
        "revoked_current_option_backtest_methods": [
            "minute_trade_close_plus_global_median_spread_proxy",
            "minute_trade_close_plus_proxy_spread_plus_market_impact_stress",
            "trade_print_fee_only_as_execution_truth",
        ],
        "capabilities": capabilities,
        "profitability_attribute_registry": timing_profitability_attribute_registry(),
        "profitability_evaluation_protocol": {
            "required_order": [
                "full_population_signed_trend_supply",
                "path_noise_relative_to_edge_thickness",
                "executable_subset_signed_edge",
                "derivative_and_ask_bid_transport",
                "profitable_counterexample_challenge",
            ],
            "single_attribute_profitability_inference_forbidden": True,
            "same_physical_horizon_required": True,
            "same_carrier_and_execution_required_for_final_economic_comparison": True,
            "strategy_selection_authorized": False,
        },
        "historical_contracts_preserved": [
            "unified_kline_attribute_infrastructure_v3",
            "derivatives_hf_bilateral_timing_infrastructure@1.0",
            "market_state_all_frequency_timing_infrastructure@1.0",
        ],
        "strategy_selection_authorized": False,
        "fresh_oos": False,
        "production_authority": False,
    }


__all__ = [
    "INFRASTRUCTURE_ID",
    "INDEX_OPTION_FEE_RMB_PER_CONTRACT_SIDE",
    "SCHEMA_ID",
    "FrequencyContract",
    "OptionFeeScheduleV2",
    "OptionAskBidRoundTripCostV3",
    "OptionPriceObservation",
    "TimingHorizonContract",
    "arbitrary_prebucketed_frequency_contract",
    "build_all_frequency_infrastructure_contract",
    "build_rolling_frequency_features",
    "build_execution_transport_ladder",
    "diagnose_frequency_panel",
    "price_long_option_round_trip_ask_bid_v3",
    "registered_frequency_contracts",
    "resolve_first_visible_bar_close",
    "unbound_option_fee_schedule",
    "timing_profitability_attribute_registry",
]
