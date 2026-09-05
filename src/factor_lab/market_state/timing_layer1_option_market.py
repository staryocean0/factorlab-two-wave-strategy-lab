# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportIndexIssue=false, reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Layer 1 causal market-coordinate contract for option-volatility consumers."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Final

import pandas as pd

from factor_lab.core.errors import ValidationError

OPTION_MARKET_PORT_SCHEMA_ID: Final = "OptionMarketCoordinatePort@1.0"
OPTION_MARKET_RECEIPT_SCHEMA_ID: Final = "OptionMarketCoordinateReceipt@1.0"
REQUIRED_COORDINATES: Final = (
    "option_quote_or_settlement",
    "matching_month_future_forward",
    "pit_risk_free_rate",
    "contract_expiry_identity",
    "underlying_daily_close",
)
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
FUTURES_UNDERLYING: Final = {
    "IF": "000300.SH",
    "IH": "000016.SH",
    "IC": "000905.SH",
    "IM": "000852.SH",
}
OPTIONS_UNDERLYING: Final = {
    "IO": "000300.SH",
    "HO": "000016.SH",
    "MO": "000852.SH",
}
INDEX_DERIVATIVE_PRODUCTS: Final = tuple((*FUTURES_UNDERLYING, *OPTIONS_UNDERLYING))


def _require_digest(value: str) -> None:
    if not _DIGEST.fullmatch(value):
        raise ValidationError("Layer 1 option-market digest must be sha256-prefixed")


def _digest(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def _contract_month(symbol: str, product_id: str) -> str:
    match = re.match(rf"^{re.escape(product_id)}(\d{{2}})(\d{{2}})", symbol)
    if not match:
        raise ValidationError(f"cannot parse CFFEX contract month: {symbol}")
    return f"{2000 + int(match.group(1)):04d}-{int(match.group(2)):02d}"


def normalize_cffex_index_derivatives(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize raw CFFEX daily rows into a causal Layer 1 coordinate table."""

    required = {
        "exchange",
        "trading_day",
        "symbol",
        "instrument_type",
        "product_id",
        "open",
        "high",
        "low",
        "close",
        "settlement",
        "pre_settlement",
        "volume",
        "turnover",
        "open_interest",
        "open_interest_change",
        "delta",
        "option_type",
        "strike_price",
        "source_kind",
        "source_url",
    }
    if missing := sorted(required.difference(frame.columns)):
        raise ValidationError(f"CFFEX derivative columns missing: {missing}")
    result = frame.loc[
        frame["exchange"].astype(str).eq("CFFEX")
        & frame["product_id"].astype(str).isin(INDEX_DERIVATIVE_PRODUCTS)
    ].copy()
    result["trading_day"] = pd.to_datetime(result["trading_day"], errors="raise").dt.date.astype(str)
    result["underlying_index_symbol"] = result["product_id"].map({**FUTURES_UNDERLYING, **OPTIONS_UNDERLYING})
    result["contract_month"] = [
        _contract_month(str(symbol), str(product))
        for symbol, product in zip(result["symbol"], result["product_id"], strict=True)
    ]
    result["dataset_precedence"] = pd.to_numeric(result.get("dataset_precedence", 0), errors="raise")
    result = result.sort_values(["trading_day", "symbol", "dataset_precedence", "ingested_at"]).drop_duplicates(
        ["trading_day", "symbol"], keep="last"
    )
    if result.duplicated(["trading_day", "symbol"]).any():
        raise ValidationError("duplicate CFFEX derivative coordinates remain")
    return result.reset_index(drop=True)


@dataclass(frozen=True, slots=True)
class OptionMarketCoordinateReceipt:
    """Bind raw causal coordinates before any IV/HV measurement is computed."""

    provider_id: str
    observation_time: datetime
    available_at: datetime
    source_versions: tuple[str, ...]
    source_receipt_digests: tuple[str, ...]
    contract_denominator_count: int
    coordinate_digest: str
    provides: tuple[str, ...] = REQUIRED_COORDINATES
    local_resampling: bool = False
    implied_volatility_computed: bool = False
    historical_volatility_computed: bool = False
    strategy_authority: bool = False
    routing_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id or not self.source_versions or not self.source_receipt_digests:
            raise ValidationError("Layer 1 option-market identity is incomplete")
        if self.observation_time.tzinfo is None or self.available_at.tzinfo is None:
            raise ValidationError("Layer 1 option-market times must be timezone-aware")
        if self.available_at < self.observation_time:
            raise ValidationError("Layer 1 option-market data cannot be available before observation")
        if self.contract_denominator_count < 0:
            raise ValidationError("Layer 1 option denominator cannot be negative")
        if len(set(self.source_versions)) != len(self.source_versions):
            raise ValidationError("Layer 1 option-market source versions must be unique")
        for value in (*self.source_receipt_digests, self.coordinate_digest):
            _require_digest(value)
        if tuple(self.provides) != REQUIRED_COORDINATES:
            raise ValidationError("Layer 1 option-market coordinate set drifted")
        if any(
            (
                self.local_resampling,
                self.implied_volatility_computed,
                self.historical_volatility_computed,
                self.strategy_authority,
                self.routing_authority,
                self.production_authority,
            )
        ):
            raise ValidationError("Layer 1 option-market port cannot derive volatility or grant authority")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["schema_id"] = OPTION_MARKET_RECEIPT_SCHEMA_ID
        payload["port_schema_id"] = OPTION_MARKET_PORT_SCHEMA_ID
        payload["observation_time"] = self.observation_time.isoformat()
        payload["available_at"] = self.available_at.isoformat()
        return payload


def build_option_market_coordinate_receipt(
    *,
    provider_id: str,
    observation_time: datetime,
    available_at: datetime,
    source_versions: tuple[str, ...],
    source_receipt_digests: tuple[str, ...],
    contract_denominator_count: int,
) -> OptionMarketCoordinateReceipt:
    unsigned = {
        "provider_id": provider_id,
        "observation_time": observation_time.isoformat(),
        "available_at": available_at.isoformat(),
        "source_versions": source_versions,
        "source_receipt_digests": source_receipt_digests,
        "contract_denominator_count": contract_denominator_count,
        "provides": REQUIRED_COORDINATES,
    }
    return OptionMarketCoordinateReceipt(
        provider_id=provider_id,
        observation_time=observation_time,
        available_at=available_at,
        source_versions=source_versions,
        source_receipt_digests=source_receipt_digests,
        contract_denominator_count=contract_denominator_count,
        coordinate_digest=_digest(unsigned),
    )


__all__ = [
    "FUTURES_UNDERLYING",
    "INDEX_DERIVATIVE_PRODUCTS",
    "OPTION_MARKET_PORT_SCHEMA_ID",
    "OPTION_MARKET_RECEIPT_SCHEMA_ID",
    "OPTIONS_UNDERLYING",
    "REQUIRED_COORDINATES",
    "OptionMarketCoordinateReceipt",
    "build_option_market_coordinate_receipt",
    "normalize_cffex_index_derivatives",
]
