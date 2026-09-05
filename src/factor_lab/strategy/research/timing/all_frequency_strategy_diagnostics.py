"""Layer 3 facade for strategy-conditioned all-frequency diagnostics."""

from __future__ import annotations

from typing import Final

from factor_lab.market_state.timing_all_frequency_infrastructure import (
    timing_profitability_attribute_registry,
)

CONTRACT_ID: Final = "timing_layer3_all_frequency_strategy_diagnostics@1.0"


def strategy_account_diagnostic_registry() -> dict[str, dict[str, object]]:
    """Return only diagnostics that require strategy/account evidence."""

    return {
        key: value
        for key, value in timing_profitability_attribute_registry().items()
        if value.get("layer") == "strategy_account"
    }


def all_frequency_strategy_diagnostic_contract() -> dict[str, object]:
    diagnostics = strategy_account_diagnostic_registry()
    return {
        "schema_id": CONTRACT_ID,
        "legacy_implementation": "timing_all_frequency_infrastructure.py",
        "diagnostic_ids": sorted(diagnostics),
        "requires_named_strategy_or_tool": True,
        "requires_strategy_account_evidence": True,
        "Layer2_measurement_authority": False,
        "automatic_strategy_selection_authority": False,
        "parameter_selection_authority": False,
        "production_authority": False,
    }


__all__ = [
    "CONTRACT_ID",
    "all_frequency_strategy_diagnostic_contract",
    "strategy_account_diagnostic_registry",
]

