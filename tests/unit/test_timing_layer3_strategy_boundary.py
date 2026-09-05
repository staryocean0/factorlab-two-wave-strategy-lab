# pyright: reportAny=false, reportArgumentType=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import numpy as np
import pandas as pd

from factor_lab.market_state.timing_all_frequency_infrastructure import (
    build_all_frequency_infrastructure_contract,
)
from factor_lab.market_state.timing_crash_rebound_current_best_r1 import (
    current_best_contract,
)
from factor_lab.market_state.timing_evaluation_platform import (
    timing_evaluation_platform_contract,
)
from factor_lab.market_state.timing_explosive_layer_v3 import (
    timing_explosive_layer_v3_contract,
)
from factor_lab.market_state.timing_layer2_3_contracts import (
    EPHEMERAL_REPLACEMENT_NOTICE,
    LAYER3A_ASSET_IDS,
    LAYER3B_ASSET_IDS,
    build_layer2_volatility_measurements,
    build_layer3b_volatility_states,
    layer3_strategy_contract,
)
from factor_lab.market_state.timing_priority_composition import (
    build_timing_priority_composition_payload,
)
from factor_lab.market_state.timing_strategy_routing_v4 import (
    build_timing_strategy_router_v4_payload,
)
from factor_lab.market_state.tool_registry_v1_5 import (
    CURRENT_TOOL_IDS,
    TOOL_REGISTRY_V1_5_VERSION,
)


def _bars(rows: int = 1_200) -> pd.DataFrame:
    index = np.arange(rows, dtype=float)
    close = 100.0 * np.exp(np.cumsum(0.00002 + 0.001 * np.sin(index / 13.0)))
    timestamp = pd.date_range("2015-01-05 09:35", periods=rows, freq="5min")
    return pd.DataFrame(
        {
            "timestamp": timestamp,
            "trading_day": timestamp.strftime("%Y-%m-%d"),
            "segment_id": 0,
            "close": close,
        }
    )


def test_layer3a_keeps_current_15_tool_registry_and_platform_v4() -> None:
    contract = layer3_strategy_contract()
    foundation = contract["strategy_foundation"]

    assert tuple(foundation["asset_ids"]) == LAYER3A_ASSET_IDS
    assert foundation["current_tool_registry"] == TOOL_REGISTRY_V1_5_VERSION
    assert foundation["current_tool_count"] == len(CURRENT_TOOL_IDS) == 15
    assert foundation["current_evaluation_platform_schema"] == ("market_state_timing_evaluation_platform@4.0")
    assert timing_evaluation_platform_contract()["schema_id"] == ("market_state_timing_evaluation_platform@4.0")


def test_volatility_measurement_and_three_state_are_separate_public_apis() -> None:
    measurements = build_layer2_volatility_measurements(_bars())
    states = build_layer3b_volatility_states(measurements)

    assert set(states.columns) == {
        "timestamp",
        "volatility_state_raw",
        "volatility_state",
    }
    assert "volatility_state" not in measurements
    assert "log_rv_fast" not in states
    assert set(states["volatility_state"].unique()).issubset({-1, 0, 1, 2})
    metadata = states.attrs["timing_layer_contract"]
    assert metadata["four_layer_role"] == "layer3b_strategy_ephemeral"
    assert metadata["lifecycle"] == EPHEMERAL_REPLACEMENT_NOTICE
    assert metadata["position_output"] is False
    assert metadata["production_authority"] is False


def test_legacy_layer3b_assets_and_migrated_strategies_are_nonproduction() -> None:
    category = layer3_strategy_contract()["strategy_ephemeral"]
    assert tuple(category["asset_ids"]) == LAYER3B_ASSET_IDS
    assert category["lifecycle"] == EPHEMERAL_REPLACEMENT_NOTICE
    assert category["replaceable_by_layer2_measurement"] is True
    assert category["long_term_foundation"] is False

    infrastructure_contract = build_timing_priority_composition_payload()
    assert infrastructure_contract["four_layer_role"] == "layer3b_strategy_ephemeral"
    assert infrastructure_contract["lifecycle"] == EPHEMERAL_REPLACEMENT_NOTICE

    contracts = (
        build_timing_strategy_router_v4_payload(),
        timing_explosive_layer_v3_contract(),
        current_best_contract(),
    )
    for contract in contracts:
        assert contract["four_layer_role"] == "layer3_strategy_research"
        assert contract["lifecycle"] == "research_pending_requalification"
        assert contract["replaceable_by_layer2_measurement"] is True
        assert contract["long_term_foundation"] is False
        authority = contract.get("authority", contract)
        assert authority["registered_use_authority"] is False
        assert authority["paper_trading_authority"] is False
        assert authority["live_trading_authority"] is False
        assert authority["production_authority"] is False


def test_full_frequency_v2_1_is_measurement_not_a_selector() -> None:
    contract = build_all_frequency_infrastructure_contract()

    assert contract["schema_id"] == ("market_state_all_frequency_timing_infrastructure@2.1")
    assert contract["four_layer_role"] == "layer2_kline_measurement"
    assert contract["measurement_authority"] is True
    assert contract["routing_authority"] is False
    assert contract["position_output"] is False
    assert contract["strategy_selection_authorized"] is False
    assert contract["capabilities"]["automatic_strategy_frequency_selection"] == ("forbidden")
    assert contract["production_authority"] is False


def test_priority_waterfall_uses_current_15_without_preselecting_any_claim() -> None:
    contract = build_timing_priority_composition_payload()

    assert contract["tool_registry_version"] == TOOL_REGISTRY_V1_5_VERSION
    assert contract["tool_count"] == 15
    assert tuple(contract["eligible_tool_ids"]) == CURRENT_TOOL_IDS
    assert contract["side_contracts"]["upside_capture"]["priority_ladder"] == []
    assert contract["side_contracts"]["downside_protection"]["priority_ladder"] == []
    assert contract["tool_routing_authority"] is False
