#!/usr/bin/env python3
"""Fail-closed validation for the bounded Two-Wave research repository."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from factor_lab.market_state.tool_registry_v1_5 import (
    CURRENT_TOOL_IDS,
    build_tool_registry_v1_5_payload,
)
from factor_lab.visual_structure.two_wave.repository_consistency import (
    GLOBAL_STATUS,
    validate_current_authority,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_MANIFEST = ROOT / "data/manifest.json"
SOURCE_MANIFEST = ROOT / "docs/governance/source_closure_manifest.json"
SLOT = ROOT / "docs/governance/layer3_tool16_candidate_slot.json"
USAGE = ROOT / "docs/governance/data_usage_declaration.json"
PACKAGE_SCOPE = ROOT / "docs/governance/package_scope.json"
AUTHORITY = ROOT / "experiments/two_wave_m0_authority.json"
COMPONENT_STATUS = ROOT / "docs/governance/repository_component_status.json"
WORKFLOWS = ROOT / ".github/workflows"
MAX_GIT_FILE_BYTES = 100 * 1024 * 1024
FORBIDDEN_PARTS = {
    ".env",
    ".venv",
    ".omx",
    ".local",
    ".runtime",
    "runtime",
    "artifacts",
    "output",
    ".beads",
}
IGNORED_GENERATED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".pyright",
}

# The original seed closure remains immutable except for this explicit current
# control plane. Git history provides the audit trail for these mutable files.
MUTABLE_AUTHORITY_PATHS = {
    "AGENTS.md",
    "README.md",
    "ai-readme.md",
    "docs/00-index.md",
    "docs/INDEX.md",
    "docs/ops/README.md",
    "docs/user/README.md",
    "docs/governance/package_scope.json",
    "docs/governance/data_usage_declaration.json",
    "docs/research/TWO_WAVE_M0_AUTHORITY.md",
    "experiments/two_wave_m0_authority.json",
    "scripts/validate_theme_package.py",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")
    return payload


def validate_source_closure() -> dict[str, int]:
    manifest = _require_json(SOURCE_MANIFEST)
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("source closure is empty")
    checked = 0
    mutable_checked = 0
    manifest_paths: set[str] = set()
    for item in entries:
        if not isinstance(item, dict):
            raise RuntimeError("source closure row must be an object")
        relative = str(item["path"])
        manifest_paths.add(relative)
        path = ROOT / relative
        if relative in MUTABLE_AUTHORITY_PATHS:
            if not path.is_file():
                raise RuntimeError(f"mutable authority entry missing: {relative}")
            mutable_checked += 1
            continue
        if not path.is_file() or _sha256(path) != str(item["sha256"]):
            raise RuntimeError(f"frozen source drifted: {relative}")
        checked += 1

    missing_manifest_mutables = sorted(
        relative
        for relative in MUTABLE_AUTHORITY_PATHS
        if relative in manifest_paths and not (ROOT / relative).is_file()
    )
    if missing_manifest_mutables:
        raise RuntimeError(f"mutable source-closure entries missing: {missing_manifest_mutables}")
    return {
        "source_files_checked": checked,
        "mutable_authority_files_checked": mutable_checked,
    }


def validate_repository_surface() -> dict[str, int]:
    file_count = 0
    maximum_size = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = path.relative_to(ROOT)
        if any(part in IGNORED_GENERATED_PARTS or part.endswith(".egg-info") for part in relative.parts):
            continue
        if any(part in FORBIDDEN_PARTS for part in relative.parts):
            raise RuntimeError(f"forbidden local/runtime path entered package: {relative}")
        size = path.stat().st_size
        if size >= MAX_GIT_FILE_BYTES:
            raise RuntimeError(f"file exceeds regular GitHub limit: {relative}")
        maximum_size = max(maximum_size, size)
        file_count += 1
    return {"repository_file_count": file_count, "maximum_file_bytes": maximum_size}


def validate_data() -> dict[str, object]:
    manifest = _require_json(DATA_MANIFEST)
    products = manifest.get("products")
    if not isinstance(products, list) or not products:
        raise RuntimeError("data manifest has no products")
    total_rows = 0
    minimum_day = "9999-12-31"
    maximum_day = "0000-00-00"
    for item in products:
        if not isinstance(item, dict):
            raise RuntimeError("data product row must be an object")
        relative = str(item["path"])
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != str(item["sha256"]):
            raise RuntimeError(f"data product drifted: {relative}")
        if pq.ParquetFile(path).metadata.num_rows != int(item["row_count"]):
            raise RuntimeError(f"data row count drifted: {relative}")
        frame = pd.read_parquet(path)
        required = {
            "symbol",
            "timestamp",
            "bar_end_shanghai",
            "timestamp_source_serialized",
            "trading_day",
            "open",
            "high",
            "low",
            "close",
            "package_data_role",
        }
        if missing := sorted(required.difference(frame.columns)):
            raise RuntimeError(f"data product missing columns {missing}: {relative}")
        if set(frame["symbol"].astype(str)) != {"000852.SH"}:
            raise RuntimeError(f"non-CSI1000 row entered package: {relative}")
        days = frame["trading_day"].astype(str)
        if days.min() < "2015-01-05" or days.max() > "2020-12-31":
            raise RuntimeError(f"data escaped declared Development interval: {relative}")
        if set(frame["package_data_role"].astype(str)) != {"development_material"}:
            raise RuntimeError(f"data role drifted: {relative}")
        timestamp = pd.to_datetime(frame["timestamp"], errors="raise", utc=True)
        if timestamp.duplicated().any() or not timestamp.is_monotonic_increasing:
            raise RuntimeError(f"timestamps are duplicated or unordered: {relative}")
        ohlc = frame[["open", "high", "low", "close"]].apply(pd.to_numeric, errors="raise")
        if not np.isfinite(ohlc.to_numpy(float)).all() or bool((ohlc <= 0.0).any().any()):
            raise RuntimeError(f"OHLC contains invalid prices: {relative}")
        if bool((ohlc["high"] < ohlc[["open", "close", "low"]].max(axis=1)).any()):
            raise RuntimeError(f"high price invariant failed: {relative}")
        if bool((ohlc["low"] > ohlc[["open", "close", "high"]].min(axis=1)).any()):
            raise RuntimeError(f"low price invariant failed: {relative}")
        total_rows += len(frame)
        minimum_day = min(minimum_day, days.min())
        maximum_day = max(maximum_day, days.max())
    return {
        "data_product_count": len(products),
        "data_row_count": total_rows,
        "minimum_trading_day": minimum_day,
        "maximum_trading_day": maximum_day,
    }


def validate_tool_boundary() -> dict[str, object]:
    payload = build_tool_registry_v1_5_payload()
    slot = _require_json(SLOT)
    usage = _require_json(USAGE)
    candidate = str(slot["candidate_tool_id"])
    if len(CURRENT_TOOL_IDS) != 15 or int(payload["tool_count"]) != 15:
        raise RuntimeError("current tool prefix is not exactly fifteen")
    if candidate in CURRENT_TOOL_IDS:
        raise RuntimeError("candidate tool was installed into the immutable prefix")
    if int(slot["candidate_tool_ordinal"]) != 16:
        raise RuntimeError("candidate slot ordinal drifted")
    if usage.get("economic_strategy_selection_authority") is not False:
        raise RuntimeError("data package overclaimed economic authority")
    return {
        "immutable_tool_count": len(CURRENT_TOOL_IDS),
        "candidate_tool_id": candidate,
        "candidate_installed": False,
    }


def validate_workflow_surface() -> dict[str, object]:
    names = sorted(path.name for path in WORKFLOWS.glob("*.yml"))
    if "ci.yml" not in names:
        raise RuntimeError("long-lived ci.yml workflow is missing")
    unexpected = [name for name in names if name != "ci.yml" and not name.endswith("-once.yml")]
    if unexpected:
        raise RuntimeError(f"unexpected long-lived workflows: {unexpected}")
    return {
        "long_lived_workflows": ["ci.yml"],
        "transient_one_shot_workflow_count": sum(name.endswith("-once.yml") for name in names),
    }


def validate_current_control_plane() -> dict[str, object]:
    authority = _require_json(AUTHORITY)
    try:
        validate_current_authority(authority)
    except AssertionError as exc:
        raise RuntimeError(str(exc)) from exc

    package_scope = _require_json(PACKAGE_SCOPE)
    if package_scope.get("schema_id") != "two_wave_cloud_theme_package_scope@1.1":
        raise RuntimeError("package scope is not current")
    if package_scope.get("private_repository_required") is not False:
        raise RuntimeError("package scope still incorrectly requires a private repository")
    if package_scope.get("production_authority") is not False:
        raise RuntimeError("package scope overclaimed production authority")

    usage = _require_json(USAGE)
    if usage.get("schema_id") != "two_wave_cloud_theme_data_usage@1.1":
        raise RuntimeError("data usage declaration is not current")
    availability = usage.get("current_external_evidence_availability")
    if not isinstance(availability, dict) or availability.get("direction_reopening_condition_satisfied") is not False:
        raise RuntimeError("data usage declaration lost the v0708 external-evidence block")

    component_status = _require_json(COMPONENT_STATUS)
    if component_status.get("authority_schema") != authority.get("schema"):
        raise RuntimeError("component status authority schema drifted")
    if component_status.get("global_status") != authority.get("global_status"):
        raise RuntimeError("component status global status drifted")

    for relative in ("README.md", "docs/INDEX.md", "docs/research/TWO_WAVE_M0_AUTHORITY.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        if GLOBAL_STATUS not in text:
            raise RuntimeError(f"current global status missing from {relative}")

    return {
        "authority_schema": authority["schema"],
        "global_status": authority["global_status"],
        "direction_winner": authority["component_authority"]["parent_direction"]["winner"],
        "morphology_acceptance": authority["morphology_acceptance"],
    }


def main() -> None:
    result: dict[str, object] = {
        "schema_id": "two_wave_cloud_theme_validation@1.1",
        "status": "passed_bounded_repository_current_state_v0708_external_validation_blocked",
        **validate_source_closure(),
        **validate_repository_surface(),
        **validate_data(),
        **validate_tool_boundary(),
        **validate_workflow_surface(),
        **validate_current_control_plane(),
        "fresh_oos": False,
        "registered_use_authority": False,
        "trade_authority": False,
        "production_authority": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
