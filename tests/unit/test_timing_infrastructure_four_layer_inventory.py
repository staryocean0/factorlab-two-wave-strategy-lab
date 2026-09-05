from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "docs/ops/timing_infrastructure_four_layer_inventory@1.0.json"
SCHEMA = ROOT / "docs/schemas/json/timing_infrastructure_four_layer_inventory@1.0.json"
LIVE_INDEXES = [
    ROOT / "ai-readme.md",
    ROOT / "README.md",
    ROOT / "docs/00-index.md",
    ROOT / "docs/user/README.md",
    ROOT / "docs/ops/README.md",
]


def _inventory() -> dict[str, Any]:
    payload = json.loads(INVENTORY.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def test_inventory_matches_schema() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(_inventory()))
    assert errors == []


def test_no_mixed_layer_and_no_measurement_plus_routing() -> None:
    inventory = _inventory()
    ids: list[str] = []
    for asset in inventory["assets"]:
        ids.append(asset["asset_id"])
        assert asset["layer"] != "mixed"
        assert not (asset["measurement_authority"] and asset["routing_authority"])
        assert asset["production_authority"] is False
        assert asset["owner_lane"] in {1, 2, 3}
        if asset["owner_lane"] == 1:
            joined = " ".join(asset["write_allowlist"])
            assert "timing_explosive" not in joined
            assert "csi1000_trade_instrument_router" not in joined
            assert "core_kline_attribute_pool.py" not in joined
        if asset["owner_lane"] == 3:
            joined = " ".join(asset["write_allowlist"])
            assert "tool_registry_v1_5.py" not in joined
            assert "timing_evaluation_platform.py" not in joined
            assert "core_kline_attribute_pool.py" not in joined
    assert len(ids) == len(set(ids))
    assert len(ids) >= 40


def test_required_splits_are_two_identities() -> None:
    inventory = _inventory()
    by_id = {asset["asset_id"]: asset for asset in inventory["assets"]}
    for item in inventory["split_required"]:
        left, right = item["into"]
        assert left in by_id
        assert right in by_id
        assert by_id[left]["split_from"] == item["from"]
        assert by_id[right]["split_from"] == item["from"]
        assert by_id[left]["layer"] != by_id[right]["layer"]


def test_lane_write_allowlists_are_disjoint_except_named_overlays() -> None:
    inventory = _inventory()
    by_lane: dict[int, set[str]] = defaultdict(set)
    for asset in inventory["assets"]:
        by_lane[int(asset["owner_lane"])].update(asset["write_allowlist"])
    exceptions = {item["path"] for item in inventory["allowlist_intersection_exceptions"]}
    assert exceptions
    assert all("overlay" in path and "attribute_pool" in path for path in exceptions)
    for left, right in ((1, 2), (1, 3), (2, 3)):
        inter = by_lane[left] & by_lane[right]
        assert inter <= exceptions


def test_shared_frozen_covers_indexes_filtering_and_attribute_pool_framework() -> None:
    frozen = set(_inventory()["shared_frozen"])
    for path in (
        "docs/ops/timing_infrastructure_four_layer_inventory@1.0.json",
        "ai-readme.md",
        "docs/00-index.md",
        "src/factor_lab/filtering/",
        "src/factor_lab/market_state/attribute_pool_infrastructure.py",
    ):
        assert path in frozen


def test_live_indexes_have_four_layer_nav_shell() -> None:
    for path in LIVE_INDEXES:
        text = path.read_text(encoding="utf-8")
        assert "timing_infrastructure_four_layer_inventory@1.0.json" in text
        assert "数据时钟" in text
        assert "K线测量" in text or "K 线测量" in text
        assert "执行标的" in text
