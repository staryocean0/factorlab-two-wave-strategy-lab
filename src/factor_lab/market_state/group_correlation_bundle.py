# pyright: reportAny=false, reportArgumentType=false
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
# pyright: reportIndexIssue=false, reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Immutable additive market-state pack for group-correlation attributes."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.contracts import FeatureSpecSnapshot
from factor_lab.market_state.group_correlation_attributes import (
    build_group_correlation_attribute_catalog,
    build_group_correlation_attribute_specs,
    build_group_correlation_feature_library,
    materialize_group_correlation_market_attributes,
)

PACK_SCHEMA_VERSION = "market_state_group_correlation_pack@1.1"


def build_group_correlation_market_state_pack(
    group_manifest_paths: tuple[Path | str, ...],
    *,
    output_root: Path | str,
    code_version: str,
    manufacturing_quality_audit_path: Path | str | None = None,
) -> dict[str, object]:
    """Register physical measurements without making strategy-effectiveness claims."""

    if not group_manifest_paths:
        raise ValidationError("at least one group-correlation manifest is required")
    observations: list[pd.DataFrame] = []
    parents: list[dict[str, object]] = []
    universe_ids: list[str] = []
    manufacturing_quality = _manufacturing_quality_context(
        manufacturing_quality_audit_path
    )
    for raw_path in group_manifest_paths:
        path = Path(raw_path)
        manifest = _read_json(path)
        universe = manifest.get("universe")
        if not isinstance(universe, Mapping):
            raise ValidationError("group manifest lacks universe identity")
        universe_id = str(universe.get("universe_id", ""))
        bundle_id = str(manifest.get("bundle_id", ""))
        if not bundle_id:
            raise ValidationError("group manifest lacks bundle_id")
        bundle_dir = path.parent / "versions" / bundle_id if path.name == "current_manifest.json" else path.parent
        attributes_path = bundle_dir / "group_correlation_attributes.parquet"
        if not attributes_path.exists():
            raise ValidationError(f"group attributes not found: {attributes_path}")
        frame = pd.read_parquet(attributes_path)
        if set(frame["universe_id"].astype(str)) != {universe_id}:
            raise ValidationError("group manifest and artifact universe mismatch")
        observations.append(frame)
        universe_ids.append(universe_id)
        parents.append(
            {
                "bundle_id": bundle_id,
                "bundle_semantic_digest": manifest.get("bundle_semantic_digest"),
                "universe_id": universe_id,
                "source": manifest.get("source"),
            }
        )
    if not observations:
        raise ValidationError("no group product passed registration gates")
    unique_universes = tuple(sorted(set(universe_ids)))
    combined = pd.concat(observations, ignore_index=True)
    materialized = materialize_group_correlation_market_attributes(combined)
    library = build_group_correlation_feature_library(universe_ids=unique_universes)
    specs = build_group_correlation_attribute_specs(universe_ids=unique_universes)
    refs = tuple(item.feature_ref for item in specs)
    snapshot = FeatureSpecSnapshot.capture(library, refs)
    catalog = build_group_correlation_attribute_catalog(universe_ids=unique_universes)
    identity = {
        "schema_version": PACK_SCHEMA_VERSION,
        "code_version": code_version,
        "parent_group_products": parents,
        "universe_ids": list(unique_universes),
        "feature_snapshot_digest": snapshot.semantic_digest,
        "production_authority": False,
        "factor_lifecycle_mutation": False,
        "frozen_a2_mutated": False,
        "measurement_registration_policy": (
            "include_pinned_physical_timeseries_without_strategy_effectiveness_gate"
        ),
        "strategy_effectiveness_claim": False,
        "manufacturing_indicator_included": (
            "cn_a_manufacturing_core_v1" in unique_universes
        ),
        "manufacturing_quality_context": manufacturing_quality,
    }
    frame_digest = _frame_digest(materialized)
    bundle_digest = canonical_digest({**identity, "attributes_digest": frame_digest})
    bundle_id = "market-state-group-corr-" + bundle_digest.removeprefix("sha256:")[:16]
    root = Path(output_root)
    versions = root / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    destination = versions / bundle_id
    if not destination.exists():
        staging = versions / f".staging-{os.getpid()}-{uuid.uuid4().hex}"
        staging.mkdir(parents=True, exist_ok=False)
        try:
            materialized.to_parquet(staging / "market_attributes.parquet", index=False)
            catalog.to_parquet(staging / "attribute_catalog.parquet", index=False)
            _write_json(staging / "feature_spec_snapshot.json", snapshot.to_dict())
            inventory = {
                "schema_version": "market_state_group_correlation_inventory@1.0",
                "bundle_id": bundle_id,
                "attributes_semantic_digest": frame_digest,
                "artifacts": {
                    name: {
                        "filename": name,
                        "sha256": _sha256(staging / name),
                    }
                    for name in (
                        "market_attributes.parquet",
                        "attribute_catalog.parquet",
                        "feature_spec_snapshot.json",
                    )
                },
                "field_labels_zh": {
                    "parent_group_products": "父群体相关性产品",
                    "attributes_semantic_digest": "市场属性语义摘要",
                    "production_authority": "生产路由权限",
                },
            }
            _write_json(staging / "artifact_inventory.json", inventory)
            manifest = {
                **identity,
                "bundle_id": bundle_id,
                "bundle_semantic_digest": bundle_digest,
                "attributes_semantic_digest": frame_digest,
                "artifacts": {
                    name: f"artifact://market-state/group-correlation/versions/{bundle_id}/{name}"
                    for name in (
                        "market_attributes.parquet",
                        "attribute_catalog.parquet",
                        "feature_spec_snapshot.json",
                        "artifact_inventory.json",
                    )
                },
            }
            _write_json(staging / "manifest.json", manifest)
            os.replace(staging, destination)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    manifest = _read_json(destination / "manifest.json")
    _write_json(root / "current_manifest.json", manifest)
    return {
        "bundle_id": bundle_id,
        "bundle_dir": destination,
        "manifest_path": root / "current_manifest.json",
        "universe_ids": unique_universes,
        "manufacturing_indicator_included": (
            "cn_a_manufacturing_core_v1" in unique_universes
        ),
    }


def _manufacturing_quality_context(path: Path | str | None) -> dict[str, object]:
    if path is None:
        return {
            "audit_available": False,
            "membership_quality_note": "not_supplied",
            "strategy_effectiveness_claim": False,
        }
    payload = _read_json(Path(path))
    return {
        "audit_available": True,
        "membership_quality_note": payload.get(
            "registration_verdict", "unspecified"
        ),
        "registration_verdict": payload.get("registration_verdict"),
        "legacy_strategy_mapping_gate": payload.get(
            "manufacturing_registration_allowed"
        ),
        "strategy_effectiveness_claim": False,
    }


def _frame_digest(frame: pd.DataFrame) -> str:
    ordered = frame.sort_values(
        ["carrier_id", "observation_time", "measurement_scale_id", "feature_id"]
    ).reset_index(drop=True)
    raw = pd.util.hash_pandas_object(ordered, index=False).to_numpy().tobytes()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValidationError(f"JSON object required: {path}")
    return {str(key): value for key, value in payload.items()}


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    _ = temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["PACK_SCHEMA_VERSION", "build_group_correlation_market_state_pack"]
