from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from factor_lab.governance.timing_strategy_identity_registry import (
    build_timing_strategy_identity_registry,
    validate_timing_strategy_identity_registry,
)
from factor_lab.market_state.timing_crash_rebound_current_best_r1 import (
    current_best_contract as legacy_crash_contract,
)
from factor_lab.market_state.timing_explosive_layer_v3 import (
    build_timing_explosive_layer_v3 as legacy_explosive_builder,
)
from factor_lab.market_state.timing_strategy_routing_v4 import (
    build_timing_strategy_router_v4_payload as legacy_router_builder,
)
from factor_lab.strategy.research.timing.crash_rebound_r1 import (
    current_best_contract as canonical_crash_contract,
)
from factor_lab.strategy.research.timing.explosive_v3 import (
    build_timing_explosive_layer_v3 as canonical_explosive_builder,
)
from factor_lab.strategy.research.timing.router_v4 import (
    build_timing_strategy_router_v4_payload as canonical_router_builder,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs/ops/timing_strategy_identity_registry@2.2.json"
SCHEMA = ROOT / "docs/schemas/json/timing_strategy_identity_registry@2.2.json"


def test_three_classes_are_exclusive_and_registered_set_is_empty() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert payload == json.loads(json.dumps(build_timing_strategy_identity_registry()))
    assert validate_timing_strategy_identity_registry(payload, project_root=ROOT) == {
        "status": "passed",
        "class_count": 3,
        "infrastructure_asset_count": 10,
        "strategy_research_asset_count": 5,
        "registered_usable_strategy_count": 0,
        "production_authority": False,
    }
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(payload)
    assert payload["classes"]["infrastructure"]["essential_surfaces"][-1] == (
        "StrategyConditionalEffectResearch"
    )


def test_all_migrated_strategies_are_fail_closed() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assets = payload["classes"]["strategy_research"]["assets"]
    assert [item["status"] for item in assets] == [
        "research_pending_requalification",
        "research_pending_requalification",
        "research_pending_requalification",
        "unfinished_strategy_prototype",
        "historical_closed",
    ]
    for item in assets:
        assert item["registered_use_authority"] is False
        assert item["paper_trading_authority"] is False
        assert item["live_trading_authority"] is False
        assert item["production_authority"] is False


def test_legacy_python_paths_are_thin_aliases_to_research_sources() -> None:
    assert legacy_explosive_builder is canonical_explosive_builder
    assert legacy_router_builder is canonical_router_builder
    assert legacy_crash_contract is canonical_crash_contract


def test_strategy_contracts_cannot_recreate_revoked_authority() -> None:
    router = canonical_router_builder()
    crash = canonical_crash_contract()
    assert router["architecture_lock_authority"] is False
    assert router["registered_use_authority"] is False
    assert router["paper_trading_authority"] is False
    assert router["live_trading_authority"] is False
    authority = crash["authority"]
    assert authority["fresh_oos"] is False
    assert authority["registered_use_authority"] is False
    assert authority["paper_trading_authority"] is False
    assert authority["live_trading_authority"] is False


def test_p8_bucket_prototype_is_strategy_research_not_infrastructure() -> None:
    from factor_lab.strategy.research.timing.lat_p8_l2_matched_bucket_prototype import (
        LIFECYCLE,
        prototype_contract,
    )

    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    asset = next(
        item
        for item in payload["classes"]["strategy_research"]["assets"]
        if item["strategy_id"] == "csi1000_lat_p8_l2_matched_bucket_prototype"
    )
    assert asset["status"] == "unfinished_strategy_prototype"
    assert asset["canonical_source"].endswith("lat_p8_l2_matched_bucket_prototype.py")
    assert "layer2_infrastructure" in asset["historical_labels_revoked"]
    assert asset["strategy_id"] not in payload["classes"]["infrastructure"]["asset_ids"]
    contract = prototype_contract()
    assert contract["lifecycle"] == LIFECYCLE
    assert contract["layer2_infrastructure"] is False
    assert contract["production_authority"] is False
