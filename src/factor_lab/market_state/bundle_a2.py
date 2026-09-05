"""A2 multi-frequency full/incremental immutable bundle lifecycle."""

from __future__ import annotations

import fcntl
import json
import math
import os
import platform
import resource
import shutil
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.attributes import MEASUREMENT_SCALES
from factor_lab.market_state.attributes_v1 import (
    ATTRIBUTE_DEFINITIONS_V1,
    build_feature_library_v1,
    build_market_attribute_catalog_v1,
    build_market_attribute_specs_v1,
    compute_market_attributes_v1,
)
from factor_lab.market_state.bundle import (
    DEFAULT_OUTPUT_ROOT,
    FIELD_LABELS_ZH,
    INVENTORY_SCHEMA_ID,
    _artifact_record,
    _atomic_copy,
    _dataframe_semantic_digest,
    _file_sha256,
    _fsync_directory,
    _records_for_json,
    _semantic_digest_path,
    _write_csv,
    _write_json,
    _write_parquet,
    _write_text,
)
from factor_lab.market_state.checkpoint import (
    CheckpointBindings,
    build_market_state_checkpoint,
    compute_online_market_state_incremental,
)
from factor_lab.market_state.contracts import FeatureSpecSnapshot, PinnedDatasetIdentity
from factor_lab.market_state.contracts_a2 import (
    A2_CURRENT_FREQUENCIES,
    A2_ONLINE_MANIFEST_SCHEMA_ID,
    OnlineMarketStateManifestA2,
)
from factor_lab.market_state.horizons import normalize_bar_panel
from factor_lab.market_state.online_loader import OnlineMarketStateLoader
from factor_lab.market_state.online_state import (
    OnlineStatePolicyV1,
    compute_online_market_state,
)
from factor_lab.market_state.performance import (
    A2_PERFORMANCE_BUDGET_VERSION,
    PerformanceBudgetA2,
    assert_performance_budget_passed,
)

A2_VALIDATION_SCHEMA_ID: Final[str] = "market_state_a2_bundle_validation@1.0"
A2_CONFIG_SCHEMA_ID: Final[str] = "market_state_a2_config@1.0"
SOURCE_TAIL_SESSIONS: Final[int] = 512


@dataclass(frozen=True, slots=True)
class MarketStateBuildResultA2:
    bundle_id: str
    semantic_digest: str
    bundle_dir: Path
    manifest_path: Path
    current_manifest_path: Path
    build_mode: str
    reused_existing: bool
    incremental_reason: str


def build_market_state_bundle_a2(
    panels: Mapping[str, pd.DataFrame],
    *,
    source_datasets: Mapping[str, PinnedDatasetIdentity],
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    code_version: str,
    carrier_id: str = "cloudridge",
    carrier_definition_version: str = "cloudridge@1",
    carrier_constituent_manifest_ref: str = "internal://cloudridge/constituents",
    carrier_constituent_hash: str = "sha256:not-applicable-synthetic-index",
    carrier_rebalance_policy_version: str = "cloudridge-rebalance@1",
    calendar_id: str = "cn_a_trading_calendar",
    calendar_version: str = "cn_a_trading_calendar@1",
    session_policy_version: str = "cn_a_regular@1",
    price_adjustment: str = "index_level",
    state_policy: OnlineStatePolicyV1 | None = None,
    performance_budget: PerformanceBudgetA2 | None = None,
    force_full: bool = False,
) -> MarketStateBuildResultA2:
    """Build A2 and use incremental continuation only for a verified tail append."""

    if tuple(sorted(panels)) != tuple(sorted(A2_CURRENT_FREQUENCIES)):
        raise ValidationError("A2 requires exact 1d and 60m input panels")
    if tuple(sorted(source_datasets)) != tuple(sorted(A2_CURRENT_FREQUENCIES)):
        raise ValidationError("A2 requires exact 1d and 60m source identities")
    if any(
        not isinstance(value, PinnedDatasetIdentity)
        for value in source_datasets.values()
    ):
        raise ValidationError("A2 source datasets must be pinned")
    if not code_version.strip():
        raise ValidationError("code_version is required")
    policy = state_policy or OnlineStatePolicyV1()
    budget = performance_budget or PerformanceBudgetA2()
    root = Path(output_root)
    versions_dir = root / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)
    current_manifest_path = root / "current" / "manifest.json"
    expected_current_bundle_id = _read_current_bundle_id(current_manifest_path)
    normalized_panels = {
        frequency: normalize_bar_panel(panels[frequency], frequency=frequency).frame
        for frequency in A2_CURRENT_FREQUENCIES
    }
    config_payload: dict[str, object] = {
        "schema_id": A2_CONFIG_SCHEMA_ID,
        "bar_frequencies": list(A2_CURRENT_FREQUENCIES),
        "measurement_scales": dict(MEASUREMENT_SCALES),
        "physical_attributes": [
            definition.physical_attribute_id
            for definition in ATTRIBUTE_DEFINITIONS_V1
        ],
        "state_policy": policy.to_dict(),
        "performance_budget_version": budget.version,
        "carrier_id": carrier_id,
        "carrier_definition_version": carrier_definition_version,
        "carrier_constituent_manifest_ref": carrier_constituent_manifest_ref,
        "carrier_constituent_hash": carrier_constituent_hash,
        "carrier_rebalance_policy_version": carrier_rebalance_policy_version,
        "calendar_id": calendar_id,
        "calendar_version": calendar_version,
        "session_policy_version": session_policy_version,
        "price_adjustment": price_adjustment,
    }
    config_digest = canonical_digest(config_payload)
    started = time.perf_counter()
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    build_mode = "full"
    incremental_reason = "forced_full" if force_full else "no_trusted_a2_parent"
    parent_bundle_id: str | None = None
    attributes: pd.DataFrame | None = None
    states: pd.DataFrame | None = None

    parent = (
        _load_parent_a2(current_manifest_path, root)
        if current_manifest_path.exists() and not force_full
        else None
    )
    if parent is not None:
        parent_manifest, parent_dir, parent_inventory = parent
        parent_bundle_id = parent_manifest.bundle_id
        parent_code = str(parent_inventory.get("code_version", ""))
        parent_config = str(parent_inventory.get("config_digest", ""))
        if parent_code != code_version:
            incremental_reason = "code_version_changed_force_full"
        elif parent_config != config_digest:
            incremental_reason = "config_changed_force_full"
        else:
            incremental = _attempt_incremental(
                normalized_panels,
                parent_manifest=parent_manifest,
                parent_dir=parent_dir,
                code_version=code_version,
                config_digest=config_digest,
                policy=policy,
            )
            if incremental is not None:
                attributes, states = incremental
                build_mode = "incremental"
                incremental_reason = "trusted_tail_append"
            else:
                incremental_reason = "history_revision_or_non_append_force_full"
    if build_mode == "full":
        attribute_parts = [
            compute_market_attributes_v1(
                normalized_panels[frequency],
                frequency=frequency,
                carrier_id=carrier_id,
                carrier_definition_version=carrier_definition_version,
            )
            for frequency in A2_CURRENT_FREQUENCIES
        ]
        attributes = pd.concat(attribute_parts, ignore_index=True)
        states = compute_online_market_state(attributes, policy=policy)

    if attributes is None or states is None:
        raise ValidationError("A2 build produced no attributes or states")
    attributes = _sort_attributes(attributes)
    states = _sort_states(states)
    catalog = build_market_attribute_catalog_v1()
    library = build_feature_library_v1()
    refs = tuple(spec.feature_ref for spec in build_market_attribute_specs_v1())
    feature_snapshot = FeatureSpecSnapshot.capture(library, refs)
    source_prefix_hashes = {
        frequency: _dataframe_semantic_digest(normalized_panels[frequency])
        for frequency in A2_CURRENT_FREQUENCIES
    }
    source_tail = _build_source_tail(normalized_panels)

    staging_root = versions_dir / f".staging-a2-{os.getpid()}-{uuid.uuid4().hex}"
    staging_online = staging_root / "online"
    staging_online.mkdir(parents=True, exist_ok=False)
    try:
        core_paths = {
            "market_attribute_catalog": staging_online
            / "market_attribute_catalog.csv",
            "market_attribute_observation": staging_online
            / "market_attribute_observation.parquet",
            "market_state_online": staging_online / "market_state_online.parquet",
            "feature_spec_snapshot": staging_online / "feature_spec_snapshot.json",
            "state_policy": staging_online / "state_policy.json",
            "checkpoint_source_tail": staging_online
            / "checkpoint_source_tail.parquet",
        }
        _write_csv(core_paths["market_attribute_catalog"], catalog)
        _write_parquet(core_paths["market_attribute_observation"], attributes)
        _write_parquet(core_paths["market_state_online"], states)
        _write_json(core_paths["feature_spec_snapshot"], feature_snapshot.to_dict())
        _write_json(
            core_paths["state_policy"],
            {
                "schema_id": "market_state_online_state_policy@1.0",
                "policy": policy.to_dict(),
                "field_labels_zh": {"policy": "严格因果在线状态政策"},
            },
        )
        _write_parquet(core_paths["checkpoint_source_tail"], source_tail)
        core_semantics = {
            name: _semantic_digest_path(path) for name, path in core_paths.items()
        }
        semantic_identity: dict[str, object] = {
            "schema_id": "market_state_a2_bundle_semantic_identity@1.0",
            "source_datasets": {
                key: value.to_dict()
                for key, value in sorted(source_datasets.items())
            },
            "feature_snapshot_digest": feature_snapshot.semantic_digest,
            "config_digest": config_digest,
            "code_version": code_version,
            "core_artifact_semantic_digests": core_semantics,
        }
        bundle_semantic_digest = canonical_digest(semantic_identity)
        bundle_id = "market-state-a2-" + bundle_semantic_digest.removeprefix(
            "sha256:"
        )[:16]
        checkpoint = build_market_state_checkpoint(
            attributes,
            states,
            bindings=CheckpointBindings(
                parent_bundle_id=bundle_id,
                code_version=code_version,
                config_digest=config_digest,
                source_prefix_hashes=source_prefix_hashes,
                state_policy_version=policy.version,
            ),
            policy=policy,
        )
        checkpoint_path = staging_online / "checkpoint.json"
        _write_json(checkpoint_path, checkpoint)
        budget_path = staging_online / "performance_budget.json"
        _write_json(budget_path, budget.to_dict())
        snapshot = _build_current_snapshot_a2(states, bundle_id)
        quality = _build_quality_report_a2(attributes, states, bundle_id)
        drift = _build_drift_report_a2(
            states, bundle_id, build_mode, incremental_reason
        )
        report = _build_report_a2(
            bundle_id=bundle_id,
            attributes=attributes,
            states=states,
            build_mode=build_mode,
            incremental_reason=incremental_reason,
        )
        secondary_paths = {
            "market_state_current_snapshot": staging_online
            / "market_state_current_snapshot.json",
            "quality_report": staging_online / "quality_report.json",
            "drift_report": staging_online / "drift_report.json",
            "report_zh": staging_online / "report_zh.md",
            "checkpoint": checkpoint_path,
            "performance_budget": budget_path,
        }
        _write_json(secondary_paths["market_state_current_snapshot"], snapshot)
        _write_json(secondary_paths["quality_report"], quality)
        _write_json(secondary_paths["drift_report"], drift)
        _write_text(secondary_paths["report_zh"], report)
        artifact_paths_without_performance = {**core_paths, **secondary_paths}
        preliminary_records = [
            _artifact_record(name, path, staging_online)
            for name, path in sorted(artifact_paths_without_performance.items())
        ]
        output_bytes = sum(
            int(size)
            for item in preliminary_records
            if isinstance((size := item.get("size_bytes")), int)
        )
        elapsed = time.perf_counter() - started
        rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        evaluation = budget.evaluate(
            input_rows=sum(len(value) for value in panels.values()),
            output_rows=len(attributes) + len(states),
            elapsed_seconds=elapsed,
            peak_rss_platform_units=int(max(rss_before, rss_after)),
            output_bytes=output_bytes,
        )
        assert_performance_budget_passed(evaluation)
        performance: dict[str, object] = {
            "schema_id": "market_state_a2_performance_report@1.0",
            "bundle_id": bundle_id,
            "build_mode": build_mode,
            "incremental_reason": incremental_reason,
            "evaluation": evaluation,
            "reference_hardware": {
                "platform": platform.platform(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python": platform.python_version(),
                "cpu_count": os.cpu_count(),
            },
            "field_labels_zh": {
                "build_mode": "构建模式",
                "incremental_reason": "增量或全量原因",
                "evaluation": "冻结预算评估",
            },
        }
        performance_path = staging_online / "performance_report.json"
        _write_json(performance_path, performance)
        artifact_paths = {
            **artifact_paths_without_performance,
            "performance_report": performance_path,
        }
        records = [
            _artifact_record(name, path, staging_online)
            for name, path in sorted(artifact_paths.items())
        ]
        inventory_without_digest: dict[str, object] = {
            "schema_id": INVENTORY_SCHEMA_ID,
            "bundle_id": bundle_id,
            "bundle_semantic_digest": bundle_semantic_digest,
            "semantic_identity": semantic_identity,
            "code_version": code_version,
            "config_digest": config_digest,
            "artifacts": records,
            "field_labels_zh": FIELD_LABELS_ZH,
        }
        inventory = {
            **inventory_without_digest,
            "inventory_semantic_digest": canonical_digest(inventory_without_digest),
        }
        inventory_path = staging_online / "artifact_inventory.json"
        _write_json(inventory_path, inventory)
        artifact_names = {
            **{name: path.name for name, path in artifact_paths.items()},
            "artifact_inventory": inventory_path.name,
        }
        artifact_uris = {
            name: f"artifact://market-state-foundation/versions/{bundle_id}/online/{filename}"
            for name, filename in artifact_names.items()
        }
        manifest = OnlineMarketStateManifestA2(
            bundle_id=bundle_id,
            carrier_id=carrier_id,
            carrier_definition_version=carrier_definition_version,
            bar_frequencies=A2_CURRENT_FREQUENCIES,
            source_datasets=source_datasets,
            feature_snapshot=feature_snapshot,
            calendar_id=calendar_id,
            calendar_version=calendar_version,
            timezone="Asia/Shanghai",
            session_policy_version=session_policy_version,
            price_adjustment=price_adjustment,
            available_at_policy="at_completed_bar_timestamp_Asia/Shanghai",
            build_mode=build_mode,
            parent_bundle_id=parent_bundle_id if build_mode == "incremental" else None,
            performance_budget_version=A2_PERFORMANCE_BUDGET_VERSION,
            performance_budget_status="passed",
            artifacts=artifact_uris,
        )
        manifest_path = staging_online / "manifest.json"
        _write_json(manifest_path, manifest.to_dict())
        _fsync_directory(staging_online)
        _fsync_directory(staging_root)
        # A candidate must prove internal consistency before it is allowed to
        # change the shared ``current`` pointer.
        validate_market_state_bundle_a2(manifest_path)
        final_online, reused = _publish_a2(
            staging_root=staging_root,
            versions_dir=versions_dir,
            bundle_id=bundle_id,
            current_manifest_path=current_manifest_path,
            root=root,
            expected_current_bundle_id=expected_current_bundle_id,
        )
        final_manifest = final_online / "manifest.json"
        validation = validate_market_state_bundle_a2(final_manifest)
        if validation["bundle_semantic_digest"] != bundle_semantic_digest:
            raise ValidationError("published A2 semantic digest mismatch")
        return MarketStateBuildResultA2(
            bundle_id=bundle_id,
            semantic_digest=bundle_semantic_digest,
            bundle_dir=final_online,
            manifest_path=final_manifest,
            current_manifest_path=current_manifest_path,
            build_mode=build_mode,
            reused_existing=reused,
            incremental_reason=incremental_reason,
        )
    except Exception:
        if staging_root.exists():
            shutil.rmtree(staging_root)
        raise


def validate_market_state_bundle_a2(
    manifest_path: Path | str,
) -> dict[str, object]:
    path = Path(manifest_path)
    payload_raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload_raw, dict):
        raise ValidationError("A2 manifest must be an object")
    manifest = OnlineMarketStateLoader().load_manifest(
        cast(dict[str, object], payload_raw), usage="research"
    )
    if not isinstance(manifest, OnlineMarketStateManifestA2):
        raise ValidationError("manifest is not A2")
    encoded = json.dumps(payload_raw, ensure_ascii=False).lower()
    if any(value in encoded for value in ("retro_manifest", "similar_periods", "affinity_evidence")):
        raise ValidationError("A2 online manifest exposes a later-stage artifact")
    if path.parent.name == "current":
        root = path.parent.parent
        bundle_dir = root / "versions" / manifest.bundle_id / "online"
    else:
        bundle_dir = path.parent
    inventory_raw = json.loads(
        (bundle_dir / "artifact_inventory.json").read_text(encoding="utf-8")
    )
    if not isinstance(inventory_raw, dict):
        raise ValidationError("A2 inventory must be an object")
    inventory = cast(dict[str, object], inventory_raw)
    if inventory.get("schema_id") != INVENTORY_SCHEMA_ID:
        raise ValidationError("A2 inventory schema mismatch")
    digest_payload = dict(inventory)
    recorded_inventory_digest = str(digest_payload.pop("inventory_semantic_digest", ""))
    if canonical_digest(digest_payload) != recorded_inventory_digest:
        raise ValidationError("A2 inventory semantic digest mismatch")
    semantic_identity = inventory.get("semantic_identity")
    if not isinstance(semantic_identity, dict):
        raise ValidationError("A2 semantic identity is required")
    bundle_digest = canonical_digest(cast(dict[str, object], semantic_identity))
    if bundle_digest != inventory.get("bundle_semantic_digest"):
        raise ValidationError("A2 bundle semantic digest mismatch")
    items = inventory.get("artifacts")
    if not isinstance(items, list) or not items:
        raise ValidationError("A2 artifact records are required")
    names: set[str] = set()
    for raw_item in items:
        if not isinstance(raw_item, dict):
            raise ValidationError("A2 artifact record must be an object")
        item = cast(dict[str, object], raw_item)
        name = str(item.get("name", ""))
        artifact_path = bundle_dir / str(item.get("relative_path", ""))
        if not artifact_path.is_file():
            raise ValidationError(f"A2 artifact missing: {name}")
        if _file_sha256(artifact_path) != item.get("file_sha256"):
            raise ValidationError(f"A2 artifact file hash mismatch: {name}")
        if _semantic_digest_path(artifact_path) != item.get("semantic_digest"):
            raise ValidationError(f"A2 artifact semantic digest mismatch: {name}")
        names.add(name)
    required = {
        "market_attribute_catalog",
        "market_attribute_observation",
        "market_state_online",
        "feature_spec_snapshot",
        "state_policy",
        "checkpoint_source_tail",
        "checkpoint",
        "performance_budget",
        "performance_report",
        "market_state_current_snapshot",
        "quality_report",
        "drift_report",
        "report_zh",
    }
    if not required.issubset(names):
        raise ValidationError(f"A2 artifacts incomplete: {sorted(required - names)}")
    checkpoint = json.loads((bundle_dir / "checkpoint.json").read_text(encoding="utf-8"))
    if checkpoint.get("parent_bundle_id") != manifest.bundle_id:
        raise ValidationError("A2 continuation checkpoint is not bound to its bundle")
    performance = json.loads(
        (bundle_dir / "performance_report.json").read_text(encoding="utf-8")
    )
    evaluation = performance.get("evaluation", {})
    if not isinstance(evaluation, dict):
        raise ValidationError("A2 performance evaluation is required")
    assert_performance_budget_passed(cast(dict[str, object], evaluation))
    return {
        "schema_id": A2_VALIDATION_SCHEMA_ID,
        "valid": True,
        "bundle_id": manifest.bundle_id,
        "bundle_semantic_digest": bundle_digest,
        "verified_artifact_count": len(names),
        "build_mode": manifest.build_mode,
        "performance_budget_status": manifest.performance_budget_status,
        "field_labels_zh": {
            "verified_artifact_count": "已核验 A2 产物数",
            "performance_budget_status": "冻结性能预算状态",
        },
    }


def _attempt_incremental(
    normalized_panels: Mapping[str, pd.DataFrame],
    *,
    parent_manifest: OnlineMarketStateManifestA2,
    parent_dir: Path,
    code_version: str,
    config_digest: str,
    policy: OnlineStatePolicyV1,
) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    checkpoint_raw = json.loads((parent_dir / "checkpoint.json").read_text(encoding="utf-8"))
    source_tail = pd.read_parquet(parent_dir / "checkpoint_source_tail.parquet")
    prefix_hashes = checkpoint_raw.get("source_prefix_hashes")
    if not isinstance(prefix_hashes, dict):
        return None
    appended: dict[str, pd.DataFrame] = {}
    for frequency in A2_CURRENT_FREQUENCIES:
        parent_tail = source_tail.loc[source_tail["frequency"] == frequency]
        if parent_tail.empty:
            return None
        last_time = pd.Timestamp(parent_tail["timestamp"].max())
        current = normalized_panels[frequency]
        prefix = current.loc[current["timestamp"] <= last_time]
        if prefix.empty or _dataframe_semantic_digest(prefix) != prefix_hashes.get(frequency):
            return None
        new_rows = current.loc[current["timestamp"] > last_time].copy()
        if new_rows.empty:
            return None
        appended[frequency] = new_rows
    parent_attributes = pd.read_parquet(
        parent_dir / "market_attribute_observation.parquet"
    )
    parent_states = pd.read_parquet(parent_dir / "market_state_online.parquet")
    new_attribute_parts: list[pd.DataFrame] = []
    for frequency in A2_CURRENT_FREQUENCIES:
        parent_tail = source_tail.loc[source_tail["frequency"] == frequency].drop(
            columns=["frequency"]
        )
        combined = pd.concat([parent_tail, appended[frequency]], ignore_index=True)
        computed = compute_market_attributes_v1(combined, frequency=frequency)
        first_new = pd.Timestamp(str(appended[frequency]["timestamp"].min()))
        new_attribute_parts.append(
            computed.loc[computed["observation_time"] >= first_new].copy()
        )
    new_attributes = pd.concat(new_attribute_parts, ignore_index=True)
    _continue_directional_run_attributes(
        parent_attributes, new_attributes, normalized_panels, source_tail
    )
    bindings = CheckpointBindings(
        parent_bundle_id=parent_manifest.bundle_id,
        code_version=code_version,
        config_digest=config_digest,
        source_prefix_hashes={str(key): str(value) for key, value in prefix_hashes.items()},
        state_policy_version=policy.version,
    )
    new_states = compute_online_market_state_incremental(
        new_attributes,
        checkpoint=checkpoint_raw,
        bindings=bindings,
        policy=policy,
    )
    return (
        pd.concat([parent_attributes, new_attributes], ignore_index=True),
        pd.concat([parent_states, new_states], ignore_index=True),
    )


def _continue_directional_run_attributes(
    parent_attributes: pd.DataFrame,
    new_attributes: pd.DataFrame,
    normalized_panels: Mapping[str, pd.DataFrame],
    source_tail: pd.DataFrame,
) -> None:
    for frequency in A2_CURRENT_FREQUENCIES:
        parent_run = parent_attributes.loc[
            (parent_attributes["bar_frequency"] == frequency)
            & (parent_attributes["physical_attribute_id"] == "directional_run_age")
            & (parent_attributes["measurement_scale_id"] == "fast_20d")
        ].sort_values("observation_time")
        age = float(parent_run.iloc[-1]["raw_value"])
        parent_tail = source_tail.loc[source_tail["frequency"] == frequency]
        previous_close = float(parent_tail.sort_values("timestamp").iloc[-1]["close"])
        previous_sign = math.nan
        if len(parent_tail) >= 2:
            ordered_parent = parent_tail.sort_values("timestamp")
            previous_sign = float(
                np.sign(
                    math.log(float(ordered_parent.iloc[-1]["close"]) / float(ordered_parent.iloc[-2]["close"]))
                )
            )
        current = normalized_panels[frequency]
        last_parent_time = pd.Timestamp(parent_tail["timestamp"].max())
        appended = current.loc[current["timestamp"] > last_parent_time].sort_values(
            "timestamp"
        )
        ages: dict[object, float] = {}
        for _, row in appended.iterrows():
            close = float(row["close"])
            sign = float(np.sign(math.log(close / previous_close)))
            age = age + 1.0 if sign != 0.0 and sign == previous_sign else 1.0
            timestamp = pd.Timestamp(str(row["timestamp"]))
            ages[timestamp] = age
            previous_close = close
            previous_sign = sign
        mask = (new_attributes["bar_frequency"] == frequency) & (
            new_attributes["physical_attribute_id"] == "directional_run_age"
        )
        mapped = new_attributes.loc[mask, "observation_time"].map(ages)
        new_attributes.loc[mask, "raw_value"] = mapped.to_numpy()
        new_attributes.loc[mask, "attribute_valid"] = mapped.notna().to_numpy()
        for scale_id, window in MEASUREMENT_SCALES.items():
            residence = (new_attributes["bar_frequency"] == frequency) & (
                new_attributes["physical_attribute_id"] == "residence_fraction"
            ) & (new_attributes["measurement_scale_id"] == scale_id)
            mapped_age = new_attributes.loc[residence, "observation_time"].map(ages)
            new_attributes.loc[residence, "raw_value"] = (
                mapped_age / float(window)
            ).to_numpy()
            new_attributes.loc[residence, "attribute_valid"] = mapped_age.notna().to_numpy()


def _build_source_tail(normalized_panels: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    parts = []
    for frequency in A2_CURRENT_FREQUENCIES:
        frame = normalized_panels[frequency]
        sessions = pd.Index(frame["trading_day"].drop_duplicates())
        keep = list(sessions[-SOURCE_TAIL_SESSIONS:])
        tail = frame.loc[frame["trading_day"].isin(keep)].copy()
        # Canonical source exports may already carry a descriptive frequency
        # column.  The checkpoint owns this field and must bind it to the
        # requested panel key instead of attempting a duplicate insertion.
        tail["frequency"] = frequency
        tail = tail[["frequency", *[column for column in tail if column != "frequency"]]]
        parts.append(tail)
    return pd.concat(parts, ignore_index=True).sort_values(
        ["frequency", "timestamp"], kind="mergesort"
    ).reset_index(drop=True)


def _sort_attributes(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(
        [
            "carrier_id",
            "carrier_definition_version",
            "bar_frequency",
            "feature_id",
            "measurement_scale_id",
            "observation_time",
        ],
        kind="mergesort",
    ).reset_index(drop=True)


def _sort_states(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(
        [
            "carrier_id",
            "carrier_definition_version",
            "bar_frequency",
            "feature_id",
            "feature_version",
            "measurement_scale_id",
            "observation_time",
        ],
        kind="mergesort",
    ).reset_index(drop=True)


def _load_parent_a2(
    current_manifest_path: Path, root: Path
) -> tuple[OnlineMarketStateManifestA2, Path, dict[str, object]] | None:
    raw = json.loads(current_manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_id") != A2_ONLINE_MANIFEST_SCHEMA_ID:
        return None
    manifest = OnlineMarketStateManifestA2.from_dict(cast(dict[str, object], raw))
    parent_dir = root / "versions" / manifest.bundle_id / "online"
    validate_market_state_bundle_a2(parent_dir / "manifest.json")
    inventory_raw = json.loads(
        (parent_dir / "artifact_inventory.json").read_text(encoding="utf-8")
    )
    if not isinstance(inventory_raw, dict):
        raise ValidationError("parent A2 inventory must be an object")
    return manifest, parent_dir, cast(dict[str, object], inventory_raw)


def _read_current_bundle_id(path: Path) -> str | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return str(raw.get("bundle_id", "")) if isinstance(raw, dict) else None


def compare_and_swap_current_manifest(
    *,
    candidate_manifest_path: Path,
    current_manifest_path: Path,
    lock_path: Path,
    expected_current_bundle_id: str | None,
) -> None:
    """Atomically publish one already-validated A2 candidate manifest."""

    candidate_bundle_id = _read_current_bundle_id(candidate_manifest_path)
    if not candidate_bundle_id:
        raise ValidationError("A2 candidate manifest bundle_id is required")
    current_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            _compare_and_swap_current_manifest_unlocked(
                candidate_manifest_path=candidate_manifest_path,
                current_manifest_path=current_manifest_path,
                expected_current_bundle_id=expected_current_bundle_id,
                candidate_bundle_id=candidate_bundle_id,
            )
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _compare_and_swap_current_manifest_unlocked(
    *,
    candidate_manifest_path: Path,
    current_manifest_path: Path,
    expected_current_bundle_id: str | None,
    candidate_bundle_id: str,
) -> None:
    actual_current = _read_current_bundle_id(current_manifest_path)
    if actual_current not in {expected_current_bundle_id, candidate_bundle_id}:
        raise ValidationError("A2 current compare-and-swap parent changed")
    _atomic_copy(candidate_manifest_path, current_manifest_path)


def _publish_a2(
    *,
    staging_root: Path,
    versions_dir: Path,
    bundle_id: str,
    current_manifest_path: Path,
    root: Path,
    expected_current_bundle_id: str | None,
) -> tuple[Path, bool]:
    current_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    final_root = versions_dir / bundle_id
    final_online = final_root / "online"
    lock_path = root / ".publish.lock"
    reused = False
    with lock_path.open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            if final_online.exists():
                shutil.rmtree(staging_root)
                validate_market_state_bundle_a2(final_online / "manifest.json")
                reused = True
            else:
                os.replace(staging_root, final_root)
                _fsync_directory(versions_dir)
            _compare_and_swap_current_manifest_unlocked(
                candidate_manifest_path=final_online / "manifest.json",
                current_manifest_path=current_manifest_path,
                expected_current_bundle_id=expected_current_bundle_id,
                candidate_bundle_id=bundle_id,
            )
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    return final_online, reused


def _build_current_snapshot_a2(states: pd.DataFrame, bundle_id: str) -> dict[str, object]:
    latest = (
        states.sort_values("observation_time")
        .groupby(
            ["bar_frequency", "feature_id", "feature_version", "measurement_scale_id"],
            sort=True,
            as_index=False,
        )
        .tail(1)
    )
    columns = [
        "bar_frequency",
        "observation_time",
        "available_at",
        "feature_id",
        "feature_version",
        "physical_attribute_id",
        "attribute_family",
        "measurement_scale_id",
        "raw_value",
        "causal_location",
        "causal_trend",
        "trend_strength",
        "state_bucket",
        "state_age",
        "drift_score",
        "confidence",
        "state_valid",
    ]
    return {
        "schema_id": "market_state_current_snapshot@2.0",
        "bundle_id": bundle_id,
        "causal": True,
        "uses_future": False,
        "observations": _records_for_json(latest.loc[:, columns]),
        "field_labels_zh": {"observations": "1d 与 60m 最新严格因果状态"},
    }


def _build_quality_report_a2(
    attributes: pd.DataFrame, states: pd.DataFrame, bundle_id: str
) -> dict[str, object]:
    key = [
        "carrier_id",
        "carrier_definition_version",
        "bar_frequency",
        "observation_time",
        "feature_id",
        "feature_version",
        "measurement_scale_id",
    ]
    duplicates = int(attributes.duplicated(key).sum())
    return {
        "schema_id": "market_state_quality_report@2.0",
        "bundle_id": bundle_id,
        "attribute_rows": len(attributes),
        "state_rows": len(states),
        "logical_key_duplicate_count": duplicates,
        "state_valid_share": float(states["state_valid"].mean()),
        "quality_passed": duplicates == 0,
        "frequencies": sorted(attributes["bar_frequency"].unique().tolist()),
        "field_labels_zh": {
            "logical_key_duplicate_count": "逻辑键重复数",
            "state_valid_share": "在线状态有效占比",
        },
    }


def _build_drift_report_a2(
    states: pd.DataFrame, bundle_id: str, build_mode: str, reason: str
) -> dict[str, object]:
    return {
        "schema_id": "market_state_drift_report@2.0",
        "bundle_id": bundle_id,
        "build_mode": build_mode,
        "incremental_reason": reason,
        "drift_alert_count": int(
            ((states["state_valid"]) & (states["drift_score"] >= 1.0)).sum()
        ),
        "field_labels_zh": {
            "incremental_reason": "增量或强制全量原因",
            "drift_alert_count": "漂移强度大于等于一的观测数",
        },
    }


def _build_report_a2(
    *,
    bundle_id: str,
    attributes: pd.DataFrame,
    states: pd.DataFrame,
    build_mode: str,
    incremental_reason: str,
) -> str:
    counts = attributes.groupby("bar_frequency").size().to_dict()
    lines = [
        "# 市场状态地基 A2 因果核心报告",
        "",
        f"- 不可变包：`{bundle_id}`",
        f"- 构建模式：`{build_mode}`（`{incremental_reason}`）",
        f"- 完整 V1 物理属性：`{len(ATTRIBUTE_DEFINITIONS_V1)}` 个",
        f"- 连续属性行数：`{len(attributes)}`",
        f"- 在线状态行数：`{len(states)}`",
        *[f"- `{frequency}` 属性行数：`{count}`" for frequency, count in sorted(counts.items())],
        "",
        "A2 使用交易 session 和有效交易分钟，不把 60m 的 N 日窗口写成固定 N×4 根。",
        "该产物仍只描述市场事实，`production_authority=false`，不做策略路由。",
        "",
    ]
    return "\n".join(lines)


__all__ = [
    "MarketStateBuildResultA2",
    "build_market_state_bundle_a2",
    "validate_market_state_bundle_a2",
]
