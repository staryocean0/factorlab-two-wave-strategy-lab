#!/usr/bin/env python3
"""Fail-closed validation for the bounded two-wave cloud theme package."""

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

ROOT = Path(__file__).resolve().parents[1]
DATA_MANIFEST = ROOT / "data/manifest.json"
SOURCE_MANIFEST = ROOT / "docs/governance/source_closure_manifest.json"
SLOT = ROOT / "docs/governance/layer3_tool16_candidate_slot.json"
USAGE = ROOT / "docs/governance/current/data_usage_declaration.json"
MAX_GIT_FILE_BYTES = 100 * 1024 * 1024
FORBIDDEN_PARTS = {
    ".env", ".venv", ".omx", ".local", ".runtime", "runtime", "artifacts", "output", ".beads",
}
IGNORED_GENERATED_PARTS = {
    "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".pyright",
}
# These four control-plane entries remain mutable, as in the original validator.
# Do not expand this set to waive source or data integrity.
MUTABLE_AUTHORITY_PATHS = {
    "AGENTS.md", "README.md", "docs/INDEX.md", "scripts/validate_theme_package.py",
}
# A relocation is NOT a hash exemption. The original seed bytes must still match
# the unchanged seed manifest at this exact archive path. All other entries retain
# their original path and hash. Current CI is independently checked for manual opt-in.
FROZEN_SOURCE_RELOCATIONS = {
    ".github/workflows/ci.yml": "docs/archive/repository_consistency_20260912/ci.yml",
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
    relocated_checked = 0
    for item in entries:
        if not isinstance(item, dict):
            raise RuntimeError("source closure row must be an object")
        relative = str(item["path"])
        path = ROOT / FROZEN_SOURCE_RELOCATIONS.get(relative, relative)
        if relative in MUTABLE_AUTHORITY_PATHS:
            if not path.is_file():
                raise RuntimeError(f"mutable authority entry missing: {relative}")
            mutable_checked += 1
            continue
        if not path.is_file() or _sha256(path) != str(item["sha256"]):
            raise RuntimeError(f"frozen source drifted: {relative}")
        if relative in FROZEN_SOURCE_RELOCATIONS:
            if not (ROOT / relative).is_file():
                raise RuntimeError(f"current replacement missing: {relative}")
            relocated_checked += 1
        checked += 1
    missing_authority = sorted(
        relative for relative in MUTABLE_AUTHORITY_PATHS if not (ROOT / relative).is_file()
    )
    if missing_authority:
        raise RuntimeError(f"mutable authority entries missing: {missing_authority}")
    return {
        "source_files_checked": checked,
        "mutable_authority_files_checked": mutable_checked,
        "relocated_frozen_entries_checked": relocated_checked,
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
            "symbol", "timestamp", "bar_end_shanghai", "timestamp_source_serialized",
            "trading_day", "open", "high", "low", "close", "package_data_role",
        }
        if missing := sorted(required.difference(frame.columns)):
            raise RuntimeError(f"data product missing columns {missing}: {relative}")
        if set(frame["symbol"].astype(str)) != {"000852.SH"}:
            raise RuntimeError(f"non-CSI1000 row entered package: {relative}")
        days = frame["trading_day"].astype(str)
        if days.min() < "2015-01-05" or days.max() > "2020-12-31":
            raise RuntimeError(f"data escaped declared development interval: {relative}")
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
        "data_product_count": len(products), "data_row_count": total_rows,
        "minimum_trading_day": minimum_day, "maximum_trading_day": maximum_day,
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
    return {"immutable_tool_count": len(CURRENT_TOOL_IDS), "candidate_tool_id": candidate, "candidate_installed": False}


def validate_current_declarations() -> dict[str, object]:
    """Keep current package/data metadata aligned without rewriting seed evidence."""
    scope = _require_json(ROOT / "docs/governance/current/package_scope.json")
    usage = _require_json(USAGE)
    authority = _require_json(ROOT / "experiments/two_wave_m0_authority.json")
    expected_authority = "experiments/two_wave_m0_authority.json"
    if scope.get("schema_id") != "two_wave_cloud_theme_package_scope@1.1" or usage.get("schema_id") != "two_wave_cloud_theme_data_usage@1.1":
        raise RuntimeError("current declaration schema drift")
    if scope.get("current_machine_authority") != expected_authority or usage.get("current_machine_authority") != expected_authority:
        raise RuntimeError("current declarations point at competing authority")
    if scope.get("repository_visibility") != "public" or scope.get("private_repository_required") is not False:
        raise RuntimeError("current scope misstates repository visibility")
    for key in ("morphology_acceptance", "trade_authority", "production_authority", "authoritative_local_registry_mutation"):
        if scope.get(key) is not False:
            raise RuntimeError(f"scope overclaims authority: {key}")
    for key in ("trade_fill_authority", "local_resampling_authority", "economic_strategy_selection_authority", "fresh_oos", "paper_trading_authority", "production_authority"):
        if usage.get(key) is not False:
            raise RuntimeError(f"data declaration overclaims authority: {key}")
    expected_interval = {"start": "2015-01-05", "end": "2020-12-31", "instrument": "000852.SH"}
    if scope.get("shipped_development_data_interval") != expected_interval or usage.get("instrument") != "000852.SH":
        raise RuntimeError("current shipped data scope drift")
    intervals = usage.get("shipped_development_intervals", [])
    if len(intervals) != 1 or any(intervals[0].get(key) != expected_interval[key] for key in ("start", "end")):
        raise RuntimeError("current Development interval drift")
    if intervals[0].get("fresh_evidence") is not False or usage.get("allowed_uses_are_not_current_execution_authorization") is not True:
        raise RuntimeError("data availability became execution or fresh-evidence authority")
    history = usage["external_temporal_validation_history"]
    slices = [(x["start"], x["end"], x["role"]) for x in history["consumed_slices"]]
    expected_slices = [("2024-01-02", "2024-12-31", "consumed_external_temporal_replication"),
                       ("2025-01-02", "2025-12-31", "consumed_external_temporal_replication"),
                       ("2026-01-05", "2026-08-21", "consumed_external_temporal_replication")]
    if slices != expected_slices or history.get("raw_rows_shipped_in_this_repository") is not False:
        raise RuntimeError("consumed external evidence or shipped rows misstated")
    if history.get("already_consumed_evidence_may_be_reused_as_new_external_validation") is not False:
        raise RuntimeError("consumed evidence relabelled as new")
    ref = usage["independent_reference_history"]
    for key, metric in (("v0648_candidate_cases", "v0648_candidate_cases"),
                        ("v0648_reference_confirmed_candidate_count", "v0648_reference_confirmed_candidates"),
                        ("v0648_complete_anchor_cases", "anchored_development_cases")):
        if type(ref.get(key)) is not int or ref[key] != authority["metrics"][metric]:
            raise RuntimeError(f"reference declaration/M0 count mismatch: {key}")
    available = usage["current_external_evidence_availability"]
    for key in ("post_2026_08_21_CSI1000_minute_extension_available", "new_independent_two_wave_reference_labels_available", "direction_reopening_condition_satisfied"):
        if available.get(key) is not False:
            raise RuntimeError(f"unavailable external evidence promoted: {key}")
    if scope["external_validation_policy"].get("current_new_external_evidence_available") is not False:
        raise RuntimeError("scope reopens external evidence")
    if ref.get("new_independent_reference_label_pack_currently_available") is not False:
        raise RuntimeError("reference labels fabricated")
    if authority.get("temporal_trigger_A_satisfied") is not False or authority.get("independent_reference_trigger_B_satisfied") is not False:
        raise RuntimeError("declarations/M0 external availability conflict")
    return {"current_governance_declarations_checked": 2, "consumed_external_slices_declared": len(slices)}


def main() -> None:
    result: dict[str, object] = {
        "schema_id": "two_wave_cloud_theme_validation@1.0",
        "status": "passed_bounded_cloud_theme_ready_for_morphology_research",
        **validate_source_closure(), **validate_repository_surface(), **validate_data(), **validate_tool_boundary(),
        **validate_current_declarations(),
        "fresh_oos": False, "registered_use_authority": False, "production_authority": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
