from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from factor_lab.core.errors import ValidationError
from factor_lab.market_state import timing_all_frequency_infrastructure as legacy_frequency
from factor_lab.market_state.timing_layer2_all_frequency_measurements import (
    build_rolling_frequency_features,
    diagnose_frequency_panel,
    layer2_all_frequency_measurement_contract,
)
from factor_lab.market_state.timing_layer2_boundary_registry import (
    MIGRATED_TO_LAYER3_ASSETS,
    build_layer2_boundary_registry,
    validate_layer2_boundary_registry,
    validate_layer2_causal_input_columns,
    validate_layer2_runtime_feature_columns,
)
from factor_lab.market_state.timing_layer4_all_frequency_execution import (
    build_execution_transport_ladder,
    layer4_all_frequency_execution_contract,
)
from factor_lab.strategy.research.timing.all_frequency_strategy_diagnostics import (
    all_frequency_strategy_diagnostic_contract,
    strategy_account_diagnostic_registry,
)
from factor_lab.strategy.research.timing.conditional_effect_research import (
    MIGRATED_ASSET_IDS,
    build_tool_conditioned_relationships,
    build_tool_state_affinity_evidence,
    strategy_conditional_effect_research_contract,
)

ROOT = Path(__file__).resolve().parents[2]
LAYER2 = ROOT / "docs/ops/timing_layer2_measurement_plane@2.3.json"
LAYER2_SCHEMA = ROOT / "docs/schemas/json/timing_layer2_measurement_plane@2.3.json"
LAYER3 = ROOT / "docs/ops/timing_layer3_strategy_architecture@2.2.json"
LAYER3_SCHEMA = ROOT / "docs/schemas/json/timing_layer3_strategy_architecture@2.2.json"


def test_layer2_current_registry_classifies_every_asset_once() -> None:
    payload = json.loads(LAYER2.read_text(encoding="utf-8"))
    assert payload == json.loads(json.dumps(build_layer2_boundary_registry()))
    assert validate_layer2_boundary_registry(payload, project_root=ROOT) == {
        "status": "passed",
        "classified_asset_count": 18,
        "causal_provider_count": 10,
        "offline_material_count": 2,
        "definition_compatibility_count": 4,
        "migrated_to_layer3_count": 2,
        "production_authority": False,
    }
    schema = json.loads(LAYER2_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def test_tool_conditioned_assets_are_layer3_not_layer2() -> None:
    layer2 = json.loads(LAYER2.read_text(encoding="utf-8"))
    layer3 = json.loads(LAYER3.read_text(encoding="utf-8"))
    assert tuple(layer2["classes"]["migrated_to_layer3"]["asset_ids"]) == MIGRATED_TO_LAYER3_ASSETS
    assert tuple(layer3["strategy_conditional_effect_research"]["asset_ids"]) == MIGRATED_ASSET_IDS
    assert not set(MIGRATED_TO_LAYER3_ASSETS).intersection(
        layer2["classes"]["causal_feature_provider"]["asset_ids"]
    )
    contract = strategy_conditional_effect_research_contract()
    assert contract["surface_id"] == "StrategyConditionalEffectResearch"
    assert contract["Layer2_measurement_authority"] is False
    assert contract["runtime_installation_authority"] is False
    schema = json.loads(LAYER3_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(layer3)


def test_layer2_causal_provider_rejects_strategy_effect_lineage() -> None:
    validate_layer2_causal_input_columns(["close", "volume", "log_rv_20"])
    for column in (
        "tool_id",
        "strategy_id",
        "target_position",
        "action_role",
        "strategy_return_bp",
        "tool_effect_qvalue",
    ):
        with pytest.raises(ValidationError, match="strategy/tool-effect"):
            validate_layer2_causal_input_columns(["close", column])


def test_offline_targets_cannot_leak_into_runtime_features() -> None:
    validate_layer2_runtime_feature_columns(["rv_20", "path_efficiency_60"])
    for column in ("future_log_variance", "oracle_winner", "target_rv"):
        with pytest.raises(ValidationError, match="offline target/oracle"):
            validate_layer2_runtime_feature_columns([column])


def test_all_frequency_facades_are_identity_preserving_and_disjoint() -> None:
    assert build_rolling_frequency_features is legacy_frequency.build_rolling_frequency_features
    assert diagnose_frequency_panel is legacy_frequency.diagnose_frequency_panel
    assert build_execution_transport_ladder is legacy_frequency.build_execution_transport_ladder
    assert build_tool_conditioned_relationships.__module__.endswith("tool_conditioned_relationships")
    assert build_tool_state_affinity_evidence.__module__.endswith("tool_affinity")

    l2 = layer2_all_frequency_measurement_contract()
    l3 = all_frequency_strategy_diagnostic_contract()
    l4 = layer4_all_frequency_execution_contract()
    assert "execution_transport" in l2["forbidden"]
    assert l3["requires_strategy_account_evidence"] is True
    assert l4["Layer2_measurement_authority"] is False
    assert strategy_account_diagnostic_registry()
    assert not any((l2["production_authority"], l3["production_authority"], l4["production_authority"]))
