"""Baylum-owned staged release contract for CloudRidge and market state.

FactorLab A2 ``current`` remains a build-stage pointer.  Production data
publication is authorized only by the single Baylum release receipt written
through this module and orchestrated by the parent Baylum workflow.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Self, cast

import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.bundle import _file_sha256, _fsync_directory, _write_json
from factor_lab.market_state.bundle_a2 import validate_market_state_bundle_a2
from factor_lab.market_state.contracts import PinnedDatasetIdentity
from factor_lab.market_state.contracts_a2 import OnlineMarketStateManifestA2
from factor_lab.market_state.online_loader import OnlineMarketStateLoader

CLOUDRIDGE_STAGE_SCHEMA_ID: Final[str] = "cloudridge_release_stage@1.0"
MARKET_STATE_STAGE_SCHEMA_ID: Final[str] = "market_state_release_stage@1.0"
BAYLUM_RELEASE_SCHEMA_ID: Final[str] = "baylum_release_receipt@1.0"
BAYLUM_RELEASE_VALIDATION_SCHEMA_ID: Final[str] = "baylum_release_validation@1.0"
RELEASE_OWNER: Final[str] = "baylum_data_update_workflow"
SHA256_PATTERN: Final[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

IDENTITY_LABELS_ZH: Final[dict[str, str]] = {
    "source_dataset_version": "精确 DataHub 源数据集版本",
    "source_dataset_hash": "精确 DataHub 源内容摘要",
    "source_watermark": "精确 DataHub 源数据水位",
    "carrier_id": "载体标识",
    "carrier_definition_version": "载体定义版本",
    "carrier_watermark": "CloudRidge 载体实际水位",
}

RELEASE_LABELS_ZH: Final[dict[str, str]] = {
    "release_id": "Baylum 统一发布标识",
    "release_semantic_digest": "统一发布语义摘要",
    "release_identity": "CloudRidge 与市场状态共同身份",
    "components": "同批发布组件",
    "publication_authority": "是否为唯一发布权威",
    "strategy_production_authority": "是否授予策略生产权",
    "compatibility_current_policy": "兼容 current 权威政策",
}


@dataclass(frozen=True, slots=True)
class SharedReleaseIdentity:
    """Exact identity that both staged components must share."""

    source_dataset_version: str
    source_dataset_hash: str
    source_watermark: str
    carrier_id: str
    carrier_definition_version: str
    carrier_watermark: str

    def __post_init__(self) -> None:
        for field in (
            "source_dataset_version",
            "source_dataset_hash",
            "source_watermark",
            "carrier_id",
            "carrier_definition_version",
            "carrier_watermark",
        ):
            if not str(getattr(self, field)).strip():
                raise ValidationError(f"release identity {field} is required")

    @classmethod
    def from_source(
        cls,
        source: PinnedDatasetIdentity,
        *,
        carrier_id: str,
        carrier_definition_version: str,
        carrier_watermark: str,
    ) -> Self:
        return cls(
            source_dataset_version=source.dataset_version,
            source_dataset_hash=source.dataset_hash,
            source_watermark=source.watermark,
            carrier_id=carrier_id,
            carrier_definition_version=carrier_definition_version,
            carrier_watermark=carrier_watermark,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> Self:
        expected = set(IDENTITY_LABELS_ZH) | {"field_labels_zh"}
        if set(payload) != expected:
            raise ValidationError(
                f"release identity fields mismatch: {sorted(set(payload) ^ expected)}"
            )
        if payload.get("field_labels_zh") != IDENTITY_LABELS_ZH:
            raise ValidationError("release identity Chinese labels mismatch")
        return cls(
            source_dataset_version=str(payload.get("source_dataset_version", "")),
            source_dataset_hash=str(payload.get("source_dataset_hash", "")),
            source_watermark=str(payload.get("source_watermark", "")),
            carrier_id=str(payload.get("carrier_id", "")),
            carrier_definition_version=str(
                payload.get("carrier_definition_version", "")
            ),
            carrier_watermark=str(payload.get("carrier_watermark", "")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "source_dataset_version": self.source_dataset_version,
            "source_dataset_hash": self.source_dataset_hash,
            "source_watermark": self.source_watermark,
            "carrier_id": self.carrier_id,
            "carrier_definition_version": self.carrier_definition_version,
            "carrier_watermark": self.carrier_watermark,
            "field_labels_zh": dict(IDENTITY_LABELS_ZH),
        }


@dataclass(frozen=True, slots=True)
class ReleaseStage:
    """One immutable component staged before the unified receipt is committed."""

    schema_id: str
    stage_id: str
    component: str
    component_bundle_id: str
    component_semantic_digest: str
    release_identity: SharedReleaseIdentity
    manifest_ref: str
    artifacts: Mapping[str, str]
    bound_cloudridge_stage_id: str | None

    def __post_init__(self) -> None:
        if self.schema_id not in {
            CLOUDRIDGE_STAGE_SCHEMA_ID,
            MARKET_STATE_STAGE_SCHEMA_ID,
        }:
            raise ValidationError("unsupported release stage schema")
        expected_component = (
            "cloudridge_levels"
            if self.schema_id == CLOUDRIDGE_STAGE_SCHEMA_ID
            else "market_state_online"
        )
        if self.component != expected_component:
            raise ValidationError("release stage component/schema mismatch")
        for field in (
            "stage_id",
            "component_bundle_id",
            "component_semantic_digest",
            "manifest_ref",
        ):
            if not str(getattr(self, field)).strip():
                raise ValidationError(f"release stage {field} is required")
        if not SHA256_PATTERN.fullmatch(self.component_semantic_digest):
            raise ValidationError(
                "release stage component_semantic_digest must be sha256"
            )
        if not isinstance(self.release_identity, SharedReleaseIdentity):
            raise ValidationError("release stage identity must be exact")
        if not self.artifacts or any(
            not str(name).strip()
            or not SHA256_PATTERN.fullmatch(str(digest))
            for name, digest in self.artifacts.items()
        ):
            raise ValidationError("release stage artifacts are required")
        if (
            self.component == "market_state_online"
            and not self.bound_cloudridge_stage_id
        ):
            raise ValidationError("market-state stage must bind a CloudRidge stage")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "stage_id": self.stage_id,
            "component": self.component,
            "component_bundle_id": self.component_bundle_id,
            "component_semantic_digest": self.component_semantic_digest,
            "release_identity": self.release_identity.to_dict(),
            "manifest_ref": self.manifest_ref,
            "artifacts": dict(self.artifacts),
            "bound_cloudridge_stage_id": self.bound_cloudridge_stage_id,
            "publication_authority": False,
            "field_labels_zh": {
                "stage_id": "发布暂存标识",
                "component": "暂存组件",
                "component_bundle_id": "组件不可变包标识",
                "component_semantic_digest": "组件语义摘要",
                "release_identity": "待统一核验的共同身份",
                "manifest_ref": "组件权威清单引用",
                "artifacts": "组件字节摘要",
                "bound_cloudridge_stage_id": "绑定的 CloudRidge 暂存标识",
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> Self:
        expected = {
            "schema_id",
            "stage_id",
            "component",
            "component_bundle_id",
            "component_semantic_digest",
            "release_identity",
            "manifest_ref",
            "artifacts",
            "bound_cloudridge_stage_id",
            "publication_authority",
            "field_labels_zh",
        }
        if set(payload) != expected:
            raise ValidationError(
                f"release stage fields mismatch: {sorted(set(payload) ^ expected)}"
            )
        if payload.get("publication_authority") is not False:
            raise ValidationError("a stage cannot be a publication authority")
        raw_identity = payload.get("release_identity")
        raw_artifacts = payload.get("artifacts")
        if not isinstance(raw_identity, Mapping) or not isinstance(
            raw_artifacts, Mapping
        ):
            raise ValidationError("release stage nested contracts are invalid")
        return cls(
            schema_id=str(payload.get("schema_id", "")),
            stage_id=str(payload.get("stage_id", "")),
            component=str(payload.get("component", "")),
            component_bundle_id=str(payload.get("component_bundle_id", "")),
            component_semantic_digest=str(
                payload.get("component_semantic_digest", "")
            ),
            release_identity=SharedReleaseIdentity.from_dict(
                cast(Mapping[str, object], raw_identity)
            ),
            manifest_ref=str(payload.get("manifest_ref", "")),
            artifacts={
                str(key): str(value) for key, value in raw_artifacts.items()
            },
            bound_cloudridge_stage_id=(
                str(payload["bound_cloudridge_stage_id"])
                if payload.get("bound_cloudridge_stage_id") is not None
                else None
            ),
        )


def cloudridge_panels_from_levels(
    levels_path: Path | str,
) -> dict[str, pd.DataFrame]:
    """Derive exact A2 1d and 60m carrier panels from one staged levels file."""

    path = Path(levels_path).resolve()
    frame = pd.read_csv(path)
    required = {"timestamp", "open", "high", "low", "close"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValidationError(f"CloudRidge levels missing OHLC columns: {missing}")
    if frame.empty:
        raise ValidationError("CloudRidge levels are empty")
    selected = ["timestamp", "open", "high", "low", "close"]
    if "one_minute_count" in frame:
        selected.append("one_minute_count")
    frame = frame.loc[:, selected].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "one_minute_count" in frame:
        frame["one_minute_count"] = pd.to_numeric(
            frame["one_minute_count"], errors="coerce"
        )
    if frame.isna().any(axis=None):
        raise ValidationError("CloudRidge levels contain invalid timestamp/OHLC")
    if bool(frame["timestamp"].duplicated().any()):
        raise ValidationError("CloudRidge levels contain duplicate timestamps")
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    if not frame["timestamp"].is_monotonic_increasing:
        raise ValidationError("CloudRidge levels timestamp identity is invalid")
    invalid_ohlc = (
        (frame["open"] <= 0)
        | (frame["high"] < frame[["open", "close"]].max(axis=1))
        | (frame["low"] > frame[["open", "close"]].min(axis=1))
    )
    if bool(invalid_ohlc.any()):
        raise ValidationError("CloudRidge levels violate OHLC ordering")
    frame["trading_day"] = frame["timestamp"].dt.normalize()
    frame["frequency"] = "60m"

    daily = (
        frame.groupby("trading_day", sort=True)
        .agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
        )
        .reset_index()
        .rename(columns={"trading_day": "timestamp"})
    )
    daily["timestamp"] = daily["timestamp"] + pd.Timedelta(hours=15)
    daily["trading_day"] = daily["timestamp"].dt.normalize()
    daily["frequency"] = "1d"
    return {"1d": daily, "60m": frame}


def build_cloudridge_release_stage(
    levels_path: Path | str,
    *,
    source_dataset: PinnedDatasetIdentity,
    stage_root: Path | str,
    carrier_id: str,
    carrier_definition_version: str,
) -> tuple[ReleaseStage, Path]:
    """Write one immutable CloudRidge stage manifest."""

    path = Path(levels_path).resolve()
    panels = cloudridge_panels_from_levels(path)
    carrier_watermark = str(panels["60m"]["timestamp"].iloc[-1])
    identity = SharedReleaseIdentity.from_source(
        source_dataset,
        carrier_id=carrier_id,
        carrier_definition_version=carrier_definition_version,
        carrier_watermark=carrier_watermark,
    )
    levels_sha = _file_sha256(path)
    semantic_identity: dict[str, object] = {
        "schema_id": CLOUDRIDGE_STAGE_SCHEMA_ID,
        "release_identity": identity.to_dict(),
        "levels_sha256": levels_sha,
        "row_counts": {
            "1d": int(len(panels["1d"])),
            "60m": int(len(panels["60m"])),
        },
    }
    digest = canonical_digest(semantic_identity)
    stage_id = f"cloudridge-stage-{digest.removeprefix('sha256:')[:16]}"
    manifest_path = (
        Path(stage_root).resolve() / "cloudridge" / stage_id / "manifest.json"
    )
    staged_levels_path = manifest_path.parent / "levels.csv"
    _copy_immutable_file(path, staged_levels_path, expected_digest=levels_sha)
    stage = ReleaseStage(
        schema_id=CLOUDRIDGE_STAGE_SCHEMA_ID,
        stage_id=stage_id,
        component="cloudridge_levels",
        component_bundle_id=stage_id,
        component_semantic_digest=digest,
        release_identity=identity,
        manifest_ref=str(staged_levels_path),
        artifacts={"levels_csv": levels_sha},
        bound_cloudridge_stage_id=None,
    )
    _write_immutable_json(manifest_path, stage.to_dict())
    return stage, manifest_path


def build_market_state_release_stage(
    online_manifest_path: Path | str,
    *,
    cloudridge_stage_path: Path | str,
    input_levels_path: Path | str,
    stage_root: Path | str,
) -> tuple[ReleaseStage, Path]:
    """Bind one verified A2 bundle to the exact CloudRidge levels stage."""

    cloudridge = load_release_stage(cloudridge_stage_path)
    if cloudridge.schema_id != CLOUDRIDGE_STAGE_SCHEMA_ID:
        raise ValidationError("market-state stage requires a CloudRidge stage")
    levels_sha = _file_sha256(Path(input_levels_path).resolve())
    if levels_sha != cloudridge.artifacts.get("levels_csv"):
        raise ValidationError("market-state input levels differ from CloudRidge stage")

    online_path = Path(online_manifest_path).resolve()
    validation = validate_market_state_bundle_a2(online_path)
    raw = json.loads(online_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValidationError("A2 online manifest must be an object")
    manifest = OnlineMarketStateLoader().load_manifest(raw, usage="research")
    if not isinstance(manifest, OnlineMarketStateManifestA2):
        raise ValidationError("release stage requires an A2 online manifest")
    identity = cloudridge.release_identity
    if (
        manifest.carrier_id != identity.carrier_id
        or manifest.carrier_definition_version
        != identity.carrier_definition_version
    ):
        raise ValidationError("market-state carrier identity differs from CloudRidge")
    source_identities = tuple(manifest.source_datasets.values())
    if not source_identities:
        raise ValidationError("market-state source identities are missing")
    for source in source_identities:
        if (
            source.dataset_version != identity.source_dataset_version
            or source.dataset_hash != identity.source_dataset_hash
            or source.watermark != identity.source_watermark
        ):
            raise ValidationError(
                "market-state source dataset identity differs from CloudRidge"
            )

    online_sha = _file_sha256(online_path)
    bundle_digest = str(validation["bundle_semantic_digest"])
    semantic_identity: dict[str, object] = {
        "schema_id": MARKET_STATE_STAGE_SCHEMA_ID,
        "release_identity": identity.to_dict(),
        "online_bundle_id": manifest.bundle_id,
        "online_bundle_semantic_digest": bundle_digest,
        "online_manifest_sha256": online_sha,
        "input_levels_sha256": levels_sha,
        "bound_cloudridge_stage_id": cloudridge.stage_id,
    }
    digest = canonical_digest(semantic_identity)
    stage_id = f"market-state-stage-{digest.removeprefix('sha256:')[:16]}"
    stage = ReleaseStage(
        schema_id=MARKET_STATE_STAGE_SCHEMA_ID,
        stage_id=stage_id,
        component="market_state_online",
        component_bundle_id=manifest.bundle_id,
        component_semantic_digest=bundle_digest,
        release_identity=identity,
        manifest_ref=str(online_path),
        artifacts={
            "online_manifest": online_sha,
            "input_levels_csv": levels_sha,
        },
        bound_cloudridge_stage_id=cloudridge.stage_id,
    )
    manifest_path = (
        Path(stage_root).resolve() / "market-state" / stage_id / "manifest.json"
    )
    _write_immutable_json(manifest_path, stage.to_dict())
    return stage, manifest_path


def load_release_stage(path: Path | str) -> ReleaseStage:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValidationError("release stage manifest must be an object")
    return ReleaseStage.from_dict(cast(Mapping[str, object], raw))


def publish_baylum_release(
    *,
    cloudridge_stage_path: Path | str,
    market_state_stage_path: Path | str,
    release_root: Path | str,
    failure_injection_stage: str | None = None,
) -> dict[str, object]:
    """Validate both stages, write a receipt, then atomically advance current."""

    root = Path(release_root).resolve()
    versions = root / "versions"
    current_manifest = root / "current" / "manifest.json"
    versions.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".release.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        _inject(failure_injection_stage, "before_stage_validation")
        cloudridge = load_release_stage(cloudridge_stage_path)
        market_state = load_release_stage(market_state_stage_path)
        _validate_stage_pair(cloudridge, market_state)
        _inject(failure_injection_stage, "after_stage_validation")

        semantic_identity: dict[str, object] = {
            "schema_id": BAYLUM_RELEASE_SCHEMA_ID,
            "release_owner": RELEASE_OWNER,
            "release_identity": cloudridge.release_identity.to_dict(),
            "components": {
                "cloudridge_levels": _component_receipt(
                    cloudridge, Path(cloudridge_stage_path).resolve()
                ),
                "market_state_online": _component_receipt(
                    market_state, Path(market_state_stage_path).resolve()
                ),
            },
            "compatibility_current_policy": (
                "factorlab_internal_currents_are_stage_only;"
                "production_consumers_resolve_only_this_baylum_receipt"
            ),
        }
        digest = canonical_digest(semantic_identity)
        release_id = f"baylum-release-{digest.removeprefix('sha256:')[:16]}"
        receipt: dict[str, object] = {
            **semantic_identity,
            "release_id": release_id,
            "release_semantic_digest": digest,
            "publication_authority": True,
            "strategy_production_authority": False,
            "field_labels_zh": dict(RELEASE_LABELS_ZH),
        }
        staging = versions / f".staging-{release_id}-{os.getpid()}-{uuid.uuid4().hex}"
        staging.mkdir(parents=True, exist_ok=False)
        try:
            staged_manifest = staging / "manifest.json"
            _write_json(staged_manifest, receipt)
            _fsync_directory(staging)
            _inject(failure_injection_stage, "after_receipt_write")
            validate_baylum_release(staged_manifest, require_current=False)
            final_dir = versions / release_id
            reused_existing = final_dir.exists()
            if reused_existing:
                existing = final_dir / "manifest.json"
                if (
                    not existing.is_file()
                    or _file_sha256(existing) != _file_sha256(staged_manifest)
                ):
                    raise ValidationError(
                        "existing Baylum release id has different bytes"
                    )
                shutil.rmtree(staging)
            else:
                os.replace(staging, final_dir)
                _fsync_directory(versions)
            _inject(failure_injection_stage, "after_version_publish")
            _inject(failure_injection_stage, "before_current_commit")
            current_manifest.parent.mkdir(parents=True, exist_ok=True)
            temporary_current = current_manifest.with_name(
                f".manifest.{os.getpid()}.{uuid.uuid4().hex}.tmp"
            )
            shutil.copyfile(final_dir / "manifest.json", temporary_current)
            with temporary_current.open("rb") as handle:
                os.fsync(handle.fileno())
            os.replace(temporary_current, current_manifest)
            _fsync_directory(current_manifest.parent)
            _inject(failure_injection_stage, "after_current_commit")
            validation = validate_baylum_release(
                current_manifest, require_current=True
            )
            return {
                **validation,
                "manifest_path": str(final_dir / "manifest.json"),
                "current_manifest_path": str(current_manifest),
                "reused_existing": reused_existing,
            }
        except Exception:
            if staging.exists():
                shutil.rmtree(staging)
            raise
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def validate_baylum_release(
    manifest_path: Path | str,
    *,
    require_current: bool = False,
) -> dict[str, object]:
    """Recompute receipt identity and all referenced component bytes."""

    path = Path(manifest_path).resolve()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValidationError("Baylum release receipt must be an object")
    required = {
        "schema_id",
        "release_owner",
        "release_identity",
        "components",
        "compatibility_current_policy",
        "release_id",
        "release_semantic_digest",
        "publication_authority",
        "strategy_production_authority",
        "field_labels_zh",
    }
    if set(raw) != required:
        raise ValidationError(
            f"Baylum release fields mismatch: {sorted(set(raw) ^ required)}"
        )
    if raw.get("schema_id") != BAYLUM_RELEASE_SCHEMA_ID:
        raise ValidationError("Baylum release schema mismatch")
    if raw.get("release_owner") != RELEASE_OWNER:
        raise ValidationError("Baylum release owner mismatch")
    if raw.get("publication_authority") is not True:
        raise ValidationError("Baylum release is not the publication authority")
    if raw.get("strategy_production_authority") is not False:
        raise ValidationError("data release cannot grant strategy production authority")
    if raw.get("field_labels_zh") != RELEASE_LABELS_ZH:
        raise ValidationError("Baylum release Chinese labels mismatch")
    if require_current and not (
        path.parent.name == "current" and path.name == "manifest.json"
    ):
        raise ValidationError("production release must resolve from current/manifest.json")

    raw_identity = raw.get("release_identity")
    raw_components = raw.get("components")
    if not isinstance(raw_identity, Mapping) or not isinstance(
        raw_components, Mapping
    ):
        raise ValidationError("Baylum release nested contracts are invalid")
    identity = SharedReleaseIdentity.from_dict(
        cast(Mapping[str, object], raw_identity)
    )
    if set(raw_components) != {"cloudridge_levels", "market_state_online"}:
        raise ValidationError("Baylum release component set mismatch")
    stages: dict[str, ReleaseStage] = {}
    for name, raw_component in raw_components.items():
        if not isinstance(raw_component, Mapping):
            raise ValidationError("Baylum release component must be an object")
        stage_ref = str(raw_component.get("stage_manifest_ref", ""))
        stage_sha = str(raw_component.get("stage_manifest_sha256", ""))
        stage_path = Path(stage_ref)
        if not stage_path.is_file() or _file_sha256(stage_path) != stage_sha:
            raise ValidationError(f"Baylum release stage bytes differ: {name}")
        stage = load_release_stage(stage_path)
        if stage.release_identity != identity:
            raise ValidationError(f"Baylum release stage identity differs: {name}")
        if raw_component != _component_receipt(stage, stage_path.resolve()):
            raise ValidationError(f"Baylum release component receipt differs: {name}")
        _validate_component_manifest_bytes(stage)
        stages[str(name)] = stage
    _validate_stage_pair(
        stages["cloudridge_levels"], stages["market_state_online"]
    )

    semantic_identity = {
        "schema_id": raw["schema_id"],
        "release_owner": raw["release_owner"],
        "release_identity": raw["release_identity"],
        "components": raw["components"],
        "compatibility_current_policy": raw["compatibility_current_policy"],
    }
    digest = canonical_digest(cast(dict[str, object], semantic_identity))
    if digest != raw.get("release_semantic_digest"):
        raise ValidationError("Baylum release semantic digest mismatch")
    release_id = f"baylum-release-{digest.removeprefix('sha256:')[:16]}"
    if release_id != raw.get("release_id"):
        raise ValidationError("Baylum release id mismatch")
    return {
        "schema_id": BAYLUM_RELEASE_VALIDATION_SCHEMA_ID,
        "valid": True,
        "release_id": release_id,
        "release_semantic_digest": digest,
        "source_dataset_version": identity.source_dataset_version,
        "source_watermark": identity.source_watermark,
        "carrier_watermark": identity.carrier_watermark,
        "carrier_definition_version": identity.carrier_definition_version,
        "market_state_bundle_id": stages[
            "market_state_online"
        ].component_bundle_id,
        "field_labels_zh": {
            "source_dataset_version": "共同精确源数据版本",
            "source_watermark": "共同源水位",
            "carrier_watermark": "共同载体水位",
            "market_state_bundle_id": "市场状态不可变包",
        },
    }


class BaylumReleaseLoader:
    """Production-facing resolver that rejects FactorLab internal currents."""

    def load_current(self, manifest_path: Path | str) -> dict[str, object]:
        path = Path(manifest_path).resolve()
        validation = validate_baylum_release(path, require_current=True)
        raw = json.loads(path.read_text(encoding="utf-8"))
        components = cast(dict[str, dict[str, object]], raw["components"])
        market_stage = load_release_stage(
            str(components["market_state_online"]["stage_manifest_ref"])
        )
        online_path = Path(market_stage.manifest_ref)
        bundle_validation = validate_market_state_bundle_a2(online_path)
        if (
            bundle_validation["bundle_id"] != market_stage.component_bundle_id
            or bundle_validation["bundle_semantic_digest"]
            != market_stage.component_semantic_digest
        ):
            raise ValidationError(
                "released market-state bundle identity differs from its stage"
            )
        online_raw = json.loads(online_path.read_text(encoding="utf-8"))
        if not isinstance(online_raw, dict):
            raise ValidationError("released market-state manifest is invalid")
        manifest = OnlineMarketStateLoader().load_manifest(
            online_raw, usage="live_feature"
        )
        if not isinstance(manifest, OnlineMarketStateManifestA2):
            raise ValidationError("released market-state manifest must be A2")
        return {
            **validation,
            "online_manifest_path": str(online_path),
            "online_bundle_id": manifest.bundle_id,
        }


def release_freshness_status(
    *,
    current_manifest_path: Path | str,
    expected_source_dataset_version: str,
    expected_source_watermark: str,
) -> dict[str, object]:
    """Return a check-only stale verdict without silently joining old current."""

    path = Path(current_manifest_path)
    if not path.is_file():
        return {
            "status": "market_state_missing",
            "fresh": False,
            "reason": "Baylum unified release current is missing",
        }
    try:
        validation = validate_baylum_release(path, require_current=True)
    except Exception as exc:  # noqa: BLE001 - fail-closed status boundary
        return {
            "status": "market_state_invalid",
            "fresh": False,
            "reason": str(exc),
        }
    fresh = (
        validation["source_dataset_version"] == expected_source_dataset_version
        and validation["source_watermark"] == expected_source_watermark
    )
    return {
        "status": "ready" if fresh else "market_state_stale",
        "fresh": fresh,
        "release_id": validation["release_id"],
        "released_source_dataset_version": validation[
            "source_dataset_version"
        ],
        "released_source_watermark": validation["source_watermark"],
        "expected_source_dataset_version": expected_source_dataset_version,
        "expected_source_watermark": expected_source_watermark,
    }


def _component_receipt(
    stage: ReleaseStage, stage_path: Path
) -> dict[str, object]:
    return {
        "component": stage.component,
        "stage_id": stage.stage_id,
        "component_bundle_id": stage.component_bundle_id,
        "component_semantic_digest": stage.component_semantic_digest,
        "stage_manifest_ref": str(stage_path),
        "stage_manifest_sha256": _file_sha256(stage_path),
    }


def _validate_component_manifest_bytes(stage: ReleaseStage) -> None:
    """Bind each stage to the exact component file it claims to publish."""

    manifest_path = Path(stage.manifest_ref)
    if not manifest_path.is_file():
        raise ValidationError(
            f"Baylum release component manifest is missing: {stage.component}"
        )
    artifact_name = (
        "levels_csv"
        if stage.component == "cloudridge_levels"
        else "online_manifest"
    )
    expected_digest = stage.artifacts.get(artifact_name)
    if _file_sha256(manifest_path) != expected_digest:
        raise ValidationError(
            f"Baylum release component bytes differ: {stage.component}"
        )


def _validate_stage_pair(
    cloudridge: ReleaseStage, market_state: ReleaseStage
) -> None:
    if cloudridge.schema_id != CLOUDRIDGE_STAGE_SCHEMA_ID:
        raise ValidationError("CloudRidge stage schema mismatch")
    if market_state.schema_id != MARKET_STATE_STAGE_SCHEMA_ID:
        raise ValidationError("market-state stage schema mismatch")
    if cloudridge.release_identity != market_state.release_identity:
        raise ValidationError(
            "CloudRidge and market-state dataset/watermark/carrier identity mismatch"
        )
    if market_state.bound_cloudridge_stage_id != cloudridge.stage_id:
        raise ValidationError("market-state stage binds another CloudRidge stage")
    if (
        cloudridge.artifacts.get("levels_csv")
        != market_state.artifacts.get("input_levels_csv")
    ):
        raise ValidationError("market-state was not built from staged CloudRidge bytes")


def _write_immutable_json(path: Path, payload: dict[str, object]) -> None:
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != payload:
            raise ValidationError(f"immutable release stage differs: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    _write_json(temporary, payload)
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def _copy_immutable_file(
    source: Path,
    destination: Path,
    *,
    expected_digest: str,
) -> None:
    if destination.exists():
        if _file_sha256(destination) != expected_digest:
            raise ValidationError(
                f"immutable release artifact differs: {destination}"
            )
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    try:
        shutil.copyfile(source, temporary)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        if _file_sha256(temporary) != expected_digest:
            raise ValidationError("staged release artifact digest mismatch")
        os.replace(temporary, destination)
        _fsync_directory(destination.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def _inject(requested: str | None, stage: str) -> None:
    if requested == stage:
        raise RuntimeError(f"injected release failure: {stage}")


__all__ = [
    "BAYLUM_RELEASE_SCHEMA_ID",
    "BAYLUM_RELEASE_VALIDATION_SCHEMA_ID",
    "CLOUDRIDGE_STAGE_SCHEMA_ID",
    "MARKET_STATE_STAGE_SCHEMA_ID",
    "BaylumReleaseLoader",
    "ReleaseStage",
    "SharedReleaseIdentity",
    "build_cloudridge_release_stage",
    "build_market_state_release_stage",
    "cloudridge_panels_from_levels",
    "load_release_stage",
    "publish_baylum_release",
    "release_freshness_status",
    "validate_baylum_release",
]
