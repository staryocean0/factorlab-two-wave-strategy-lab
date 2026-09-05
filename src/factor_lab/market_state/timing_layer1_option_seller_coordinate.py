"""Layer 1 additive seller-margin coordinates.  No IV, HV, or seller action."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_layer1_option_market import (
    OPTION_MARKET_PORT_SCHEMA_ID,
    REQUIRED_COORDINATES,
)

SELLER_COORDINATE_PORT: Final = "OptionMarketCoordinatePort@1.1"
SELLER_COORDINATE_RECEIPT: Final = "OptionSellerMarketCoordinateReceipt@1.0"
SELLER_REQUIRED_COORDINATES: Final = (
    *REQUIRED_COORDINATES,
    "option_previous_and_current_settlement",
    "underlying_previous_and_current_close",
    "intraday_bid_ask_depth_staleness",
    "trading_calendar_expiry_delivery_limit",
    "exchange_rule_parameter_receipt_identity",
)


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class OptionSellerMarketCoordinateReceipt:
    provider_id: str
    observation_time: datetime
    available_at: datetime
    exchange_parameter_receipt_id: str
    receipt_digest: str
    provides: tuple[str, ...] = SELLER_REQUIRED_COORDINATES
    implied_volatility_computed: bool = False
    historical_volatility_computed: bool = False
    seller_action_computed: bool = False
    margin_computed: bool = False
    strategy_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id or not self.exchange_parameter_receipt_id:
            raise ValidationError("Layer 1 seller-margin coordinate identity is incomplete")
        if self.observation_time.tzinfo is None or self.available_at.tzinfo is None:
            raise ValidationError("Layer 1 seller-margin times must be timezone-aware")
        if self.available_at < self.observation_time:
            raise ValidationError("Layer 1 seller-margin data cannot be available before observation")
        if tuple(self.provides) != SELLER_REQUIRED_COORDINATES:
            raise ValidationError("Layer 1 seller-margin coordinate set drifted")
        expected = _digest(
            {
                "provider_id": self.provider_id,
                "observation_time": self.observation_time.isoformat(),
                "available_at": self.available_at.isoformat(),
                "exchange_parameter_receipt_id": self.exchange_parameter_receipt_id,
                "provides": list(self.provides),
            }
        )
        if self.receipt_digest != expected:
            raise ValidationError("Layer 1 seller-coordinate receipt digest is unverified")
        if any(
            (
                self.implied_volatility_computed,
                self.historical_volatility_computed,
                self.seller_action_computed,
                self.margin_computed,
                self.strategy_authority,
                self.production_authority,
            )
        ):
            raise ValidationError("Layer 1 seller coordinates cannot compute IV, margin, or seller actions")


def issue_option_seller_market_coordinate_receipt(
    *,
    provider_id: str,
    observation_time: datetime,
    available_at: datetime,
    exchange_parameter_receipt_id: str,
) -> OptionSellerMarketCoordinateReceipt:
    digest = _digest(
        {
            "provider_id": provider_id,
            "observation_time": observation_time.isoformat(),
            "available_at": available_at.isoformat(),
            "exchange_parameter_receipt_id": exchange_parameter_receipt_id,
            "provides": list(SELLER_REQUIRED_COORDINATES),
        }
    )
    return OptionSellerMarketCoordinateReceipt(
        provider_id=provider_id,
        observation_time=observation_time,
        available_at=available_at,
        exchange_parameter_receipt_id=exchange_parameter_receipt_id,
        receipt_digest=digest,
    )


def parent_option_market_port() -> str:
    return OPTION_MARKET_PORT_SCHEMA_ID


__all__ = [
    "SELLER_COORDINATE_PORT",
    "SELLER_COORDINATE_RECEIPT",
    "SELLER_REQUIRED_COORDINATES",
    "OptionSellerMarketCoordinateReceipt",
    "issue_option_seller_market_coordinate_receipt",
    "parent_option_market_port",
]
