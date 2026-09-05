"""Layer 2 public facade for strategy-independent all-frequency measurements."""

from __future__ import annotations

from typing import Final

from factor_lab.market_state.timing_all_frequency_infrastructure import (
    FrequencyContract,
    TimingHorizonContract,
    arbitrary_prebucketed_frequency_contract,
    build_rolling_frequency_features,
    diagnose_frequency_panel,
    registered_frequency_contracts,
)

CONTRACT_ID: Final = "timing_layer2_all_frequency_measurements@1.0"


def layer2_all_frequency_measurement_contract() -> dict[str, object]:
    return {
        "schema_id": CONTRACT_ID,
        "legacy_implementation": "timing_all_frequency_infrastructure.py",
        "provides": [
            "frequency_identity",
            "simple_and_log_returns",
            "realized_and_annualized_volatility",
            "return_abs_squared_autocorrelation",
            "synchronous_covariance_and_correlation",
            "path_efficiency_variance_ratio_and_direction_runs",
            "high_frequency_bounce_and_gap_diagnostics",
        ],
        "forbidden": [
            "strategy_account_metrics",
            "tool_conditioned_effects",
            "execution_transport",
            "strategy_selection",
        ],
        "measurement_authority": True,
        "strategy_selection_authority": False,
        "routing_authority": False,
        "production_authority": False,
    }


__all__ = [
    "CONTRACT_ID",
    "FrequencyContract",
    "TimingHorizonContract",
    "arbitrary_prebucketed_frequency_contract",
    "build_rolling_frequency_features",
    "diagnose_frequency_panel",
    "layer2_all_frequency_measurement_contract",
    "registered_frequency_contracts",
]

