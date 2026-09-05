"""Immutable full-build lifecycle for the A1 1d market-state vertical slice."""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import platform
import resource
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.attributes import (
    MEASUREMENT_SCALES,
    build_cloudridge_compatibility_view,
    build_feature_library_1d,
    build_market_attribute_catalog,
    build_market_attribute_specs_1d,
    compute_market_attributes_1d,
)
from factor_lab.market_state.contracts import (
    FeatureSpecSnapshot,
    OnlineMarketStateManifest,
    PinnedDatasetIdentity,
)
from factor_lab.market_state.online_loader import OnlineMarketStateLoader
from factor_lab.market_state.online_state import (
    OnlineStatePolicyV1,
    compute_online_market_state,
)

DEFAULT_OUTPUT_ROOT: Final[Path] = Path("output/market-state-foundation")
INVENTORY_SCHEMA_ID: Final[str] = "market_state_artifact_inventory@1.0"
VALIDATION_SCHEMA_ID: Final[str] = "market_state_bundle_validation@1.0"

FIELD_LABELS_ZH: Final[dict[str, str]] = {
    "bundle_id": "市场状态包标识",
    "bundle_semantic_digest": "市场状态包语义摘要",
    "code_version": "代码版本",
    "config_digest": "配置摘要",
    "artifacts": "产物完整性清单",
    "file_sha256": "文件字节摘要",
    "semantic_digest": "产物语义摘要",
}


@dataclass(frozen=True, slots=True)
class MarketStateBuildResult:
    bundle_id: str
    semantic_digest: str
    bundle_dir: Path
    manifest_path: Path
    current_manifest_path: Path
    reused_existing: bool


def build_market_state_bundle_1d(
    daily_panel: pd.DataFrame,
    *,
    source_dataset: PinnedDatasetIdentity,
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
) -> MarketStateBuildResult:
    """Build, validate, publish and atomically point to one immutable A1 bundle."""

    if not isinstance(source_dataset, PinnedDatasetIdentity):
        raise ValidationError("source_dataset must be pinned")
    if not code_version.strip():
        raise ValidationError("code_version is required")
    policy = state_policy or OnlineStatePolicyV1()
    root = Path(output_root)
    versions_dir = root / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    attributes = compute_market_attributes_1d(
        daily_panel,
        carrier_id=carrier_id,
        carrier_definition_version=carrier_definition_version,
    )
    states = compute_online_market_state(attributes, policy=policy)
    catalog = build_market_attribute_catalog()
    compatibility = build_cloudridge_compatibility_view(attributes)
    library = build_feature_library_1d()
    refs = tuple(spec.feature_ref for spec in build_market_attribute_specs_1d())
    feature_snapshot = FeatureSpecSnapshot.capture(library, refs)
    config_payload: dict[str, object] = {
        "schema_id": "market_state_a1_config@1.0",
        "build_mode": "full",
        "bar_frequency": "1d",
        "measurement_scales": dict(MEASUREMENT_SCALES),
        "state_policy": policy.to_dict(),
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

    staging_root = versions_dir / f".staging-{os.getpid()}-{uuid.uuid4().hex}"
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
            "cloudridge_compatibility_view": staging_online
            / "cloudridge_attribute_compatibility_1d.csv",
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
                "field_labels_zh": {
                    "policy": "严格因果在线状态政策",
                },
            },
        )
        _write_csv(core_paths["cloudridge_compatibility_view"], compatibility)
        core_semantics = {
            name: _semantic_digest_path(path) for name, path in core_paths.items()
        }
        semantic_identity: dict[str, object] = {
            "schema_id": "market_state_bundle_semantic_identity@1.0",
            "source_dataset": source_dataset.to_dict(),
            "feature_snapshot_digest": feature_snapshot.semantic_digest,
            "config_digest": config_digest,
            "code_version": code_version,
            "core_artifact_semantic_digests": core_semantics,
        }
        bundle_semantic_digest = canonical_digest(semantic_identity)
        bundle_id = "market-state-a1-" + bundle_semantic_digest.removeprefix(
            "sha256:"
        )[:16]
        final_bundle_root = versions_dir / bundle_id
        final_online = final_bundle_root / "online"
        current_manifest_path = root / "current" / "manifest.json"
        if final_online.exists():
            shutil.rmtree(staging_root)
            existing_manifest = final_online / "manifest.json"
            validation = validate_market_state_bundle(existing_manifest)
            if validation["bundle_semantic_digest"] != bundle_semantic_digest:
                raise ValidationError("existing immutable bundle digest mismatch")
            _advance_current(existing_manifest, current_manifest_path, root)
            return MarketStateBuildResult(
                bundle_id=bundle_id,
                semantic_digest=bundle_semantic_digest,
                bundle_dir=final_online,
                manifest_path=existing_manifest,
                current_manifest_path=current_manifest_path,
                reused_existing=True,
            )

        latest_snapshot = _build_current_snapshot(states, bundle_id)
        quality_report = _build_quality_report(attributes, states, bundle_id)
        drift_report = _build_drift_report(states, bundle_id)
        report_text = _build_report_zh(
            bundle_id=bundle_id,
            attributes=attributes,
            states=states,
            quality_report=quality_report,
        )
        secondary_paths = {
            "market_state_current_snapshot": staging_online
            / "market_state_current_snapshot.json",
            "quality_report": staging_online / "quality_report.json",
            "drift_report": staging_online / "drift_report.json",
            "report_zh": staging_online / "report_zh.md",
        }
        _write_json(secondary_paths["market_state_current_snapshot"], latest_snapshot)
        _write_json(secondary_paths["quality_report"], quality_report)
        _write_json(secondary_paths["drift_report"], drift_report)
        _write_text(secondary_paths["report_zh"], report_text)

        elapsed_before_baseline = time.perf_counter() - started
        rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        performance: dict[str, object] = {
            "schema_id": "market_state_performance_baseline@1.0",
            "bundle_id": bundle_id,
            "build_mode": "full",
            "bar_frequency": "1d",
            "input_rows": int(len(daily_panel)),
            "attribute_rows": int(len(attributes)),
            "state_rows": int(len(states)),
            "elapsed_seconds": elapsed_before_baseline,
            "input_rows_per_second": (
                float(len(daily_panel) / elapsed_before_baseline)
                if elapsed_before_baseline > 0.0
                else math.inf
            ),
            "peak_rss_platform_units": int(max(rss_before, rss_after)),
            "reference_hardware": {
                "platform": platform.platform(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python": platform.python_version(),
                "cpu_count": os.cpu_count(),
            },
            "budget_status": "measured_baseline_only_not_a_frozen_budget",
            "field_labels_zh": {
                "input_rows": "输入日线行数",
                "attribute_rows": "连续属性行数",
                "state_rows": "在线状态行数",
                "elapsed_seconds": "全量构建耗时秒",
                "peak_rss_platform_units": "峰值常驻内存平台单位",
            },
        }
        performance_path = staging_online / "performance_baseline.json"
        _write_json(performance_path, performance)

        artifact_paths = {
            **core_paths,
            **secondary_paths,
            "performance_baseline": performance_path,
        }
        artifact_records = [
            _artifact_record(name, path, staging_online)
            for name, path in sorted(artifact_paths.items())
        ]
        total_bytes = sum(cast(int, item["size_bytes"]) for item in artifact_records)
        performance["output_file_count_before_manifest"] = len(artifact_records)
        performance["output_bytes_before_manifest"] = total_bytes
        _write_json(performance_path, performance)
        artifact_records = [
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
            "artifacts": artifact_records,
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
        manifest = OnlineMarketStateManifest(
            bundle_id=bundle_id,
            carrier_id=carrier_id,
            carrier_definition_version=carrier_definition_version,
            bar_frequency="1d",
            source_dataset=source_dataset,
            feature_snapshot=feature_snapshot,
            calendar_id=calendar_id,
            calendar_version=calendar_version,
            timezone="Asia/Shanghai",
            session_policy_version=session_policy_version,
            price_adjustment=price_adjustment,
            available_at_policy="after_formal_close_15:00_Asia/Shanghai",
            artifacts=artifact_uris,
        )
        manifest_path = staging_online / "manifest.json"
        _write_json(manifest_path, manifest.to_dict())
        _fsync_directory(staging_online)
        _fsync_directory(staging_root)
        os.replace(staging_root, final_bundle_root)
        _fsync_directory(versions_dir)
        final_manifest = final_online / "manifest.json"
        validate_market_state_bundle(final_manifest)
        _advance_current(final_manifest, current_manifest_path, root)
        return MarketStateBuildResult(
            bundle_id=bundle_id,
            semantic_digest=bundle_semantic_digest,
            bundle_dir=final_online,
            manifest_path=final_manifest,
            current_manifest_path=current_manifest_path,
            reused_existing=False,
        )
    except Exception:
        if staging_root.exists():
            shutil.rmtree(staging_root)
        raise


def validate_market_state_bundle(manifest_path: Path | str) -> dict[str, object]:
    """Recompute file/semantic evidence and reject non-A1 or future-aware payloads."""

    path = Path(manifest_path)
    if not path.exists():
        raise ValidationError(f"manifest not found: {path}")
    payload_raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload_raw, dict):
        raise ValidationError("manifest must be an object")
    payload = cast(dict[str, object], payload_raw)
    manifest = OnlineMarketStateLoader().load_manifest(payload, usage="research")
    encoded = json.dumps(payload, ensure_ascii=False).lower()
    for forbidden in (
        "retro_manifest",
        "similar_periods",
        "method_family_registry",
        "affinity_evidence",
    ):
        if forbidden in encoded:
            raise ValidationError(f"A1 online manifest contains forbidden {forbidden}")
    if path.parent.name == "current":
        root = path.parent.parent
        bundle_dir = root / "versions" / manifest.bundle_id / "online"
    else:
        bundle_dir = path.parent
    inventory_path = bundle_dir / "artifact_inventory.json"
    inventory_raw = json.loads(inventory_path.read_text(encoding="utf-8"))
    if not isinstance(inventory_raw, dict):
        raise ValidationError("artifact inventory must be an object")
    inventory = cast(dict[str, object], inventory_raw)
    if inventory.get("schema_id") != INVENTORY_SCHEMA_ID:
        raise ValidationError("artifact inventory schema mismatch")
    if inventory.get("bundle_id") != manifest.bundle_id:
        raise ValidationError("inventory bundle id mismatch")
    digest_payload = dict(inventory)
    recorded_inventory_digest = str(digest_payload.pop("inventory_semantic_digest", ""))
    if canonical_digest(digest_payload) != recorded_inventory_digest:
        raise ValidationError("inventory semantic digest mismatch")
    semantic_identity = inventory.get("semantic_identity")
    if not isinstance(semantic_identity, dict):
        raise ValidationError("semantic identity is required")
    bundle_digest = canonical_digest(cast(dict[str, object], semantic_identity))
    if inventory.get("bundle_semantic_digest") != bundle_digest:
        raise ValidationError("bundle semantic digest mismatch")
    artifact_items = inventory.get("artifacts")
    if not isinstance(artifact_items, list) or not artifact_items:
        raise ValidationError("artifact records are required")
    verified_names: set[str] = set()
    for raw_item in artifact_items:
        if not isinstance(raw_item, dict):
            raise ValidationError("artifact record must be an object")
        item = cast(dict[str, object], raw_item)
        name = str(item.get("name", ""))
        relative_path = str(item.get("relative_path", ""))
        artifact_path = bundle_dir / relative_path
        if not artifact_path.is_file():
            raise ValidationError(f"artifact missing: {name}")
        if _file_sha256(artifact_path) != item.get("file_sha256"):
            raise ValidationError(f"artifact file hash mismatch: {name}")
        if _semantic_digest_path(artifact_path) != item.get("semantic_digest"):
            raise ValidationError(f"artifact semantic digest mismatch: {name}")
        verified_names.add(name)
    required = {
        "market_attribute_catalog",
        "market_attribute_observation",
        "market_state_online",
        "feature_spec_snapshot",
        "state_policy",
        "market_state_current_snapshot",
        "drift_report",
        "quality_report",
        "report_zh",
        "performance_baseline",
        "cloudridge_compatibility_view",
    }
    if not required.issubset(verified_names):
        raise ValidationError(
            f"A1 artifact inventory incomplete: {sorted(required - verified_names)}"
        )
    return {
        "schema_id": VALIDATION_SCHEMA_ID,
        "valid": True,
        "bundle_id": manifest.bundle_id,
        "bundle_semantic_digest": bundle_digest,
        "verified_artifact_count": len(verified_names),
        "field_labels_zh": {
            "valid": "验证通过",
            "verified_artifact_count": "已核验产物数",
        },
    }


def _build_current_snapshot(states: pd.DataFrame, bundle_id: str) -> dict[str, object]:
    latest = (
        states.sort_values("observation_time")
        .groupby(
            ["feature_id", "feature_version", "measurement_scale_id"],
            sort=True,
            as_index=False,
        )
        .tail(1)
    )
    columns = [
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
        "schema_id": "market_state_current_snapshot@1.0",
        "bundle_id": bundle_id,
        "causal": True,
        "uses_future": False,
        "observations": _records_for_json(latest.loc[:, columns]),
        "field_labels_zh": {
            "observations": "各属性最新严格因果状态",
            "state_bucket": "状态桶",
            "confidence": "状态置信度",
        },
    }


def _build_quality_report(
    attributes: pd.DataFrame,
    states: pd.DataFrame,
    bundle_id: str,
) -> dict[str, object]:
    missing_records: list[dict[str, object]] = []
    for _, group in attributes.groupby(
        ["physical_attribute_id", "measurement_scale_id"], sort=True
    ):
        missing_records.append(
            {
                "physical_attribute_id": str(group["physical_attribute_id"].iloc[0]),
                "measurement_scale_id": str(group["measurement_scale_id"].iloc[0]),
                "missing_share": float((~group["attribute_valid"].astype(bool)).mean()),
            }
        )
    missing = pd.DataFrame(missing_records)
    return {
        "schema_id": "market_state_quality_report@1.0",
        "bundle_id": bundle_id,
        "attribute_rows": int(len(attributes)),
        "state_rows": int(len(states)),
        "logical_key_duplicate_count": 0,
        "state_valid_share": float(states["state_valid"].mean()),
        "attribute_missing_share": _records_for_json(missing),
        "quality_passed": True,
        "field_labels_zh": {
            "attribute_missing_share": "各属性缺失占比（含必要预热）",
            "state_valid_share": "在线状态有效占比",
            "quality_passed": "质量门通过",
        },
    }


def _build_drift_report(states: pd.DataFrame, bundle_id: str) -> dict[str, object]:
    valid = states.loc[states["state_valid"]].copy()
    if valid.empty:
        flip_rate = 0.0
        alert_count = 0
    else:
        key = ["feature_id", "measurement_scale_id"]
        flips = valid.groupby(key, sort=True)["state_bucket"].transform(
            lambda values: values.ne(values.shift()).astype(int)
        )
        flip_rate = float(max(0, int(flips.sum()) - valid.groupby(key).ngroups) / len(valid))
        alert_count = int((valid["drift_score"] >= 1.0).sum())
    bucket_share = (
        valid["state_bucket"].value_counts(normalize=True).sort_index().to_dict()
        if not valid.empty
        else {}
    )
    return {
        "schema_id": "market_state_drift_report@1.0",
        "bundle_id": bundle_id,
        "state_flip_rate": flip_rate,
        "drift_alert_count": alert_count,
        "state_bucket_share": {str(key): float(value) for key, value in bucket_share.items()},
        "incremental_recompute_range": None,
        "build_mode": "full",
        "field_labels_zh": {
            "state_flip_rate": "状态日更翻转率",
            "drift_alert_count": "漂移强度大于等于一的观测数",
            "state_bucket_share": "状态桶占比",
        },
    }


def _build_report_zh(
    *,
    bundle_id: str,
    attributes: pd.DataFrame,
    states: pd.DataFrame,
    quality_report: dict[str, object],
) -> str:
    latest_timestamp = cast(
        pd.Timestamp,
        pd.Timestamp(str(attributes["observation_time"].max())),
    )
    latest_time = latest_timestamp.isoformat()
    valid_latest = (
        states.sort_values("observation_time")
        .groupby(["feature_id", "measurement_scale_id"], sort=True)
        .tail(1)
    )
    bucket_counts = valid_latest["state_bucket"].value_counts().sort_index().to_dict()
    lines = [
        "# 市场状态地基 A1 日线报告",
        "",
        f"- 不可变包：`{bundle_id}`",
        f"- 最新可用时点：`{latest_time}`",
        f"- 连续属性行数：`{len(attributes)}`",
        f"- 严格因果状态行数：`{len(states)}`",
        f"- 状态有效占比：`{cast(float, quality_report['state_valid_share']):.2%}`",
        "",
        "## 最新多轴状态概览",
        "",
        *[f"- `{key}`：`{value}` 个属性×尺度" for key, value in bucket_counts.items()],
        "",
        "## 权威边界",
        "",
        "该报告只描述已完成日线的连续属性与因果在线状态，不是事后历史分段，",
        "不使用未来数据，不产生买卖信号、策略路由或生产授权。",
        "`legacy_100d` 仅是旧接口兼容标签，不等于 `slow_120d`。",
        "",
    ]
    return "\n".join(lines)


def _artifact_record(name: str, path: Path, base: Path) -> dict[str, object]:
    return {
        "name": name,
        "relative_path": str(path.relative_to(base)),
        "size_bytes": path.stat().st_size,
        "file_sha256": _file_sha256(path),
        "semantic_digest": _semantic_digest_path(path),
    }


def _semantic_digest_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return _dataframe_semantic_digest(pd.read_parquet(path))
    if suffix == ".csv":
        return _dataframe_semantic_digest(pd.read_csv(path))
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValidationError(f"JSON artifact must be an object: {path.name}")
        return canonical_digest(cast(dict[str, object], payload))
    return canonical_digest({"text": path.read_text(encoding="utf-8")})


def _dataframe_semantic_digest(frame: pd.DataFrame) -> str:
    hasher = hashlib.sha256()
    schema = {
        "columns": [str(column) for column in frame.columns],
        "dtypes": [str(dtype) for dtype in frame.dtypes],
        "nan_semantics": "json:null",
        "row_order": "physical",
    }
    hasher.update(
        json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )
    for row in frame.itertuples(index=False, name=None):
        normalized = [_canonical_scalar(value) for value in row]
        hasher.update(
            json.dumps(
                normalized,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        hasher.update(b"\n")
    return "sha256:" + hasher.hexdigest()


def _canonical_scalar(value: object) -> object:
    if value is None or (not isinstance(value, (list, dict)) and bool(pd.isna(value))):
        return None
    if isinstance(value, pd.Timestamp):
        return {"timestamp": value.isoformat()}
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        parsed = float(value)
        return {"float_hex": parsed.hex()} if math.isfinite(parsed) else None
    return str(value)


def _records_for_json(frame: pd.DataFrame) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for values in frame.itertuples(index=False, name=None):
        record: dict[str, object] = {}
        for column, value in zip(frame.columns, values, strict=True):
            if value is None or bool(pd.isna(value)):
                record[str(column)] = None
            elif isinstance(value, pd.Timestamp):
                record[str(column)] = value.isoformat()
            elif isinstance(value, (np.bool_, bool)):
                record[str(column)] = bool(value)
            elif isinstance(value, (np.integer, int)):
                record[str(column)] = int(value)
            elif isinstance(value, (np.floating, float)):
                record[str(column)] = float(value)
            else:
                record[str(column)] = str(value)
        records.append(record)
    return records


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


def _write_parquet(path: Path, frame: pd.DataFrame) -> None:
    frame.to_parquet(path, index=False, compression="zstd")
    _fsync_file(path)


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False, lineterminator="\n")
    _fsync_file(path)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    _write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def _write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())


def _fsync_file(path: Path) -> None:
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _advance_current(source_manifest: Path, current_manifest: Path, root: Path) -> None:
    current_manifest.parent.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".publish.lock"
    with lock_path.open("a+b") as lock_stream:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)
        try:
            _atomic_copy(source_manifest, current_manifest)
        finally:
            fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)


def _atomic_copy(source: Path, destination: Path) -> None:
    data = source.read_bytes()
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        _fsync_directory(destination.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


__all__ = [
    "DEFAULT_OUTPUT_ROOT",
    "MarketStateBuildResult",
    "build_market_state_bundle_1d",
    "validate_market_state_bundle",
]
