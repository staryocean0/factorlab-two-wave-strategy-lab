# pyright: reportAny=false, reportArgumentType=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false
from __future__ import annotations

import json
from pathlib import Path

from factor_lab.market_state.timing_layer3_necessity import (
    build_necessity_registry,
    validate_necessity_registry,
)

ROOT = Path(__file__).resolve().parents[2]


def test_necessity_registry_covers_assets_and_migrates_missing_materials() -> None:
    payload = json.loads((ROOT / "docs/ops/timing_layer3_necessity_registry@1.0.json").read_text(encoding="utf-8"))
    validate_necessity_registry(payload)
    assert payload == json.loads(json.dumps(build_necessity_registry()))
    migrated = [item for item in payload["materials"] if item["migration_status"] == "migrated_now"]
    assert {item["material_id"] for item in migrated} == {
        "formula_native_continuous_attributes",
        "fda_local_quadratic_velocity_acceleration",
        "ema_h4_continuous_velocity_axis",
    }
    assert all(item["layer2_destination"] for item in migrated)


def test_replaceable_assets_are_demoted_without_physical_deletion() -> None:
    payload = json.loads((ROOT / "docs/ops/timing_layer3_necessity_registry@1.0.json").read_text(encoding="utf-8"))
    by_id = {item["asset_id"]: item for item in payload["assets"]}
    assert by_id["volatility_three_state_machine"]["necessity"] == ("replaceable_compatibility")
    assert by_id["volatility_three_state_machine"]["current_standalone"] is False
    assert by_id["explosive_layer_v3"]["necessity"] == "strategy_plugin"
    assert by_id["crash_rebound_current_best"]["necessity"] == "research_candidate"
    assert by_id["timing_research_samples_rN"]["necessity"] == "historical_only"
    assert payload["physical_deletion"] is False


def test_current_architecture_and_plugin_registry_point_to_demotion_successors() -> None:
    architecture = json.loads((ROOT / "docs/ops/timing_layer3_strategy_architecture@2.2.json").read_text(encoding="utf-8"))
    plugins = json.loads((ROOT / "docs/ops/timing_layer3_strategy_plugin_registry@2.1.json").read_text(encoding="utf-8"))
    versions = json.loads((ROOT / "docs/ops/timing_layer3_strategy_architecture_version_registry@1.0.json").read_text(encoding="utf-8"))
    assert versions["current"] == "timing_layer3_strategy_architecture@2.2"
    assert architecture["identity_registry"] == "timing_strategy_identity_registry@2.2"
    assert architecture["registered_usable_strategy_count"] == 0
    assert architecture["strategy_conditional_effect_research"]["asset_ids"] == [
        "tool_conditioned_relationships",
        "tool_attribute_relationship_maps",
    ]
    assert plugins["installed_profiles"] == []
    assert plugins["automatic_plugin_replacement"] is False
