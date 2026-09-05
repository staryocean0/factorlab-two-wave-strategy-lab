# pyright: reportAny=false, reportUnknownArgumentType=false
"""Execution-cost assumptions for long/cash filter timing research."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

DEFAULT_COMMISSION_BPS = 1.0
DEFAULT_STAMP_TAX_BPS = 5.0
DEFAULT_COST_MODEL_NAME = "cn_a_commission_both_sides_stamp_sell_side"
LEGACY_SYMMETRIC_COST_MODEL_NAME = "legacy_symmetric_turnover_bps"

# Resolved one-sided cost constants: buy pays commission only, sell pays
# commission plus stamp tax. These match the authoritative IIR baseline
# (buy 1bp / sell 6bp) and are exposed for modules that need the resolved
# values without constructing a ``LongCashCostModel``.
DEFAULT_BUY_COST_BPS = DEFAULT_COMMISSION_BPS
DEFAULT_SELL_COST_BPS = DEFAULT_COMMISSION_BPS + DEFAULT_STAMP_TAX_BPS


@dataclass(frozen=True, slots=True)
class LongCashCostModel:
    """Resolved long/cash transaction-cost model.

    `symmetric_cost_bps` is retained only as an explicit legacy override.  When
    it is omitted, A-share style research defaults are used: commission on both
    buy and sell, plus stamp tax on sells only.
    """

    commission_bps: float = DEFAULT_COMMISSION_BPS
    stamp_tax_bps: float = DEFAULT_STAMP_TAX_BPS
    symmetric_cost_bps: float | None = None

    @property
    def buy_cost_bps(self) -> float:
        if self.symmetric_cost_bps is not None:
            return self.symmetric_cost_bps
        return self.commission_bps

    @property
    def sell_cost_bps(self) -> float:
        if self.symmetric_cost_bps is not None:
            return self.symmetric_cost_bps
        return self.commission_bps + self.stamp_tax_bps

    @property
    def cost_bps(self) -> float:
        """Backward-compatible average per one-sided turnover bps."""

        return (self.buy_cost_bps + self.sell_cost_bps) / 2.0

    @property
    def cost_model(self) -> str:
        if self.symmetric_cost_bps is not None:
            return LEGACY_SYMMETRIC_COST_MODEL_NAME
        return DEFAULT_COST_MODEL_NAME

    def to_dict(self) -> dict[str, object]:
        return asdict(self) | {
            "buy_cost_bps": self.buy_cost_bps,
            "sell_cost_bps": self.sell_cost_bps,
            "average_one_sided_cost_bps": self.cost_bps,
            "cost_model": self.cost_model,
            "interpretation": (
                "buy pays commission; sell pays commission plus stamp tax; "
                "symmetric_cost_bps overrides both sides only for legacy tests"
            ),
        }


def resolve_long_cash_cost_model(
    *,
    cost_bps: float | None = None,
    commission_bps: float = DEFAULT_COMMISSION_BPS,
    stamp_tax_bps: float = DEFAULT_STAMP_TAX_BPS,
) -> LongCashCostModel:
    """Validate and resolve the long/cash cost assumption."""

    for name, value in {
        "commission_bps": commission_bps,
        "stamp_tax_bps": stamp_tax_bps,
    }.items():
        if value < 0.0 or not math.isfinite(value):
            raise ValueError(f"{name} must be finite and >= 0")
    if cost_bps is not None and (cost_bps < 0.0 or not math.isfinite(cost_bps)):
        raise ValueError("cost_bps must be finite and >= 0")
    return LongCashCostModel(
        commission_bps=commission_bps,
        stamp_tax_bps=stamp_tax_bps,
        symmetric_cost_bps=cost_bps,
    )
