"""Frozen contracts for the project-level market-state foundation.

A0 establishes authority and isolation boundaries only:

* ``FeatureSpec`` remains the sole formula/source/PIT authority.
* ``MarketAttributeSpec`` references an exact FeatureSpec version.
* online and retrospective artifacts have separate manifest types.
* DataHub inputs are pinned to a READY immutable identity and pass a
  consumer-scoped FactorLab quality admission.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar, Self, cast

from factor_lab.core.errors import ValidationError
from factor_lab.factor_engine.feature_library import FeatureLibrary, FeatureSpec
from factor_lab.governance.canonicalization import canonical_digest

MARKET_ATTRIBUTE_SPEC_SCHEMA_ID = "market_attribute_spec@1.0"
FEATURE_SPEC_SNAPSHOT_SCHEMA_ID = "feature_spec_snapshot@1.0"
PINNED_DATASET_IDENTITY_SCHEMA_ID = "datahub_pinned_dataset_identity@1.1"
ONLINE_MANIFEST_SCHEMA_ID = "market_state_online_manifest@1.1"
RETRO_MANIFEST_SCHEMA_ID = "market_state_retro_manifest@1.1"
MARKET_STATE_SOURCE_ADMISSION_POLICY = "factorlab_market_state_bars_source_admission@1.0"
MARKET_STATE_MIN_QUALITY_SCORE = 90.0

ONLINE_USAGES = ("research", "backtest_feature", "live_feature")
RETRO_USAGES = ("research", "visualization", "taxonomy")

MARKET_ATTRIBUTE_LABELS_ZH = {
    "attribute_id": "属性标识",
    "physical_attribute_id": "物理属性标识",
    "feature_ref": "特征规格精确引用",
    "attribute_family": "属性族",
    "measurement_scale_id": "测量尺度",
    "state_smoothing_scale_id": "状态平滑尺度",
    "normalization_reference_id": "标准化参考尺度",
    "state_policy_version": "状态政策版本",
}
FEATURE_SNAPSHOT_LABELS_ZH = {
    "specs": "特征规格快照",
    "semantic_digest": "语义摘要",
}
PINNED_DATASET_LABELS_ZH = {
    "dataset_version": "数据集版本",
    "dataset_kind": "数据集类型",
    "state": "数据集状态",
    "dataset_hash": "数据集内容摘要",
    "consumer_admission": "市场状态消费者准入",
    "admission_policy_version": "消费者准入政策版本",
    "quality_report_ref": "DataHub 质量报告引用",
    "quality_score": "DataHub 质量分",
    "manifest_ref": "DataHub 清单引用",
    "watermark": "数据水位",
}
ONLINE_MANIFEST_LABELS_ZH = {
    "bundle_id": "在线包标识",
    "carrier_id": "载体标识",
    "carrier_definition_version": "载体定义版本",
    "bar_frequency": "K线频率",
    "source_dataset": "固定源数据集",
    "feature_snapshot": "特征规格快照",
    "calendar_id": "交易日历",
    "calendar_version": "交易日历版本",
    "timezone": "时区",
    "session_policy_version": "交易时段政策版本",
    "price_adjustment": "价格复权政策",
    "available_at_policy": "可用时间政策",
    "artifacts": "在线产物",
}
RETRO_MANIFEST_LABELS_ZH = {
    "bundle_id": "回溯包标识",
    "online_bundle_id": "对应在线包标识",
    "carrier_id": "载体标识",
    "carrier_definition_version": "载体定义版本",
    "bar_frequency": "K线频率",
    "source_dataset": "固定源数据集",
    "feature_snapshot": "特征规格快照",
    "artifacts": "回溯研究产物",
}


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} is required")


def _require_false(value: object, field_name: str) -> None:
    if value is not False:
        raise ValidationError(f"{field_name} must be false")


def _quality_score(payload: Mapping[str, object], label: str) -> float:
    value = payload.get("quality_score")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{label}.quality_score must be numeric")
    score = float(value)
    if not math.isfinite(score):
        raise ValidationError(f"{label}.quality_score must be finite")
    return score


def _require_matching_quality_score(
    *,
    quality_report: Mapping[str, object],
    quality_summary: Mapping[str, object],
) -> float:
    report_score = _quality_score(quality_report, "quality_report")
    if quality_summary:
        summary_score = _quality_score(quality_summary, "quality_summary")
        if not math.isclose(report_score, summary_score, abs_tol=1e-12):
            raise ValidationError(
                "DataHub quality report and manifest quality scores disagree"
            )
    if report_score < MARKET_STATE_MIN_QUALITY_SCORE:
        raise ValidationError("DataHub dataset quality score is below the A1 floor")
    return report_score


def _nonzero_count(payload: Mapping[str, object], field_name: str) -> bool:
    value = payload.get(field_name, 0)
    return isinstance(value, bool) or not isinstance(value, int) or value != 0


def _require_clean_quality_evidence(
    *,
    quality_report: Mapping[str, object],
    quality_summary: Mapping[str, object],
) -> None:
    if _nonzero_count(quality_report, "duplicate_count"):
        raise ValidationError("DataHub quality report contains duplicate rows")
    if quality_summary and _nonzero_count(quality_summary, "duplicate_count"):
        raise ValidationError("DataHub manifest reports duplicate rows")
    null_counts = quality_report.get("null_counts", {})
    if not isinstance(null_counts, Mapping):
        raise ValidationError("DataHub quality report null_counts must be an object")
    if any(
        isinstance(value, bool)
        or not isinstance(value, int)
        or value != 0
        for value in null_counts.values()
    ):
        raise ValidationError("DataHub quality report contains null rows")
    report_rules = _as_mapping(
        quality_report.get("rule_summary"),
        "DataHub quality report rule_summary",
    )
    _require_text(str(report_rules.get("rule_version", "")), "quality rule_version")
    if quality_summary:
        _require_text(
            str(quality_summary.get("rule_version", "")),
            "quality summary rule_version",
        )


def _require_true(value: object, field_name: str) -> None:
    if value is not True:
        raise ValidationError(f"{field_name} must be true")


def _strict_fields(
    payload: Mapping[str, object],
    allowed: frozenset[str],
    contract_name: str,
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValidationError(f"{contract_name} unknown field(s): {', '.join(unknown)}")


def _as_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be an object")
    return cast(Mapping[str, object], value)


def _as_artifacts(value: object) -> dict[str, str]:
    payload = _as_mapping(value, "artifacts")
    artifacts = {str(key): str(item) for key, item in payload.items()}
    if not artifacts:
        raise ValidationError("artifacts is required")
    for key, item in artifacts.items():
        _require_text(key, "artifact name")
        _require_text(item, f"artifact URI for {key}")
    return artifacts


def _as_string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValidationError(f"{field_name} must be a list")
    items = tuple(str(item) for item in cast(list[object] | tuple[object, ...], value))
    if not items or any(not item.strip() for item in items):
        raise ValidationError(f"{field_name} is required")
    return items


def _freeze_json(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class FeatureSpecRef:
    """Exact version and exact frequency reference to FeatureSpec."""

    feature_id: str
    feature_version: str
    frequency: str

    def __post_init__(self) -> None:
        _require_text(self.feature_id, "feature_id")
        _require_text(self.feature_version, "feature_version")
        _require_text(self.frequency, "frequency")

    def resolve(self, library: FeatureLibrary) -> FeatureSpec:
        spec = library.get_exact(self.feature_id, self.feature_version)
        if spec.frequency != self.frequency:
            raise ValidationError(
                f"FeatureSpec frequency mismatch for {self.feature_id}: reference {self.frequency}, registered {spec.frequency}"
            )
        return spec

    def to_dict(self) -> dict[str, object]:
        return {
            "feature_id": self.feature_id,
            "feature_version": self.feature_version,
            "frequency": self.frequency,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> Self:
        _strict_fields(
            payload,
            frozenset({"feature_id", "feature_version", "frequency"}),
            "FeatureSpecRef",
        )
        return cls(
            feature_id=str(payload.get("feature_id", "")),
            feature_version=str(payload.get("feature_version", "")),
            frequency=str(payload.get("frequency", "")),
        )


@dataclass(frozen=True, slots=True)
class FeatureSpecSnapshot:
    """Deterministic snapshot of the exact FeatureSpecs used by one bundle."""

    specs: tuple[Mapping[str, object], ...]
    semantic_digest: str

    schema_id: ClassVar[str] = FEATURE_SPEC_SNAPSHOT_SCHEMA_ID

    def __post_init__(self) -> None:
        if not self.specs:
            raise ValidationError("FeatureSpecSnapshot specs is required")
        frozen_specs = tuple(cast(Mapping[str, object], _freeze_json(spec)) for spec in self.specs)
        object.__setattr__(self, "specs", frozen_specs)
        _require_text(self.semantic_digest, "semantic_digest")
        thawed_specs = [cast(dict[str, object], _thaw_json(spec)) for spec in frozen_specs]
        expected = canonical_digest({"schema_id": self.schema_id, "specs": thawed_specs})
        if self.semantic_digest != expected:
            raise ValidationError("FeatureSpecSnapshot semantic_digest mismatch")

    @classmethod
    def capture(
        cls,
        library: FeatureLibrary,
        refs: tuple[FeatureSpecRef, ...],
    ) -> Self:
        if not refs:
            raise ValidationError("FeatureSpecSnapshot refs is required")
        for ref in refs:
            ref.resolve(library)
        records = library.export_snapshot_records(tuple((ref.feature_id, ref.feature_version) for ref in refs))
        specs = tuple(records)
        digest = canonical_digest({"schema_id": cls.schema_id, "specs": records})
        return cls(specs=specs, semantic_digest=digest)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "specs": [cast(dict[str, object], _thaw_json(spec)) for spec in self.specs],
            "semantic_digest": self.semantic_digest,
            "field_labels_zh": dict(FEATURE_SNAPSHOT_LABELS_ZH),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> Self:
        _strict_fields(
            payload,
            frozenset({"schema_id", "specs", "semantic_digest", "field_labels_zh"}),
            "FeatureSpecSnapshot",
        )
        if payload.get("schema_id") != cls.schema_id:
            raise ValidationError("FeatureSpecSnapshot schema_id mismatch")
        if payload.get("field_labels_zh") != FEATURE_SNAPSHOT_LABELS_ZH:
            raise ValidationError("FeatureSpecSnapshot field_labels_zh mismatch")
        raw_specs = payload.get("specs")
        if not isinstance(raw_specs, list):
            raise ValidationError("FeatureSpecSnapshot specs must be a list")
        specs: list[dict[str, object]] = []
        for raw_spec in raw_specs:
            specs.append(dict(_as_mapping(raw_spec, "FeatureSpecSnapshot spec")))
        return cls(
            specs=tuple(specs),
            semantic_digest=str(payload.get("semantic_digest", "")),
        )


@dataclass(frozen=True, slots=True)
class MarketAttributeSpec:
    """Physical market attribute bound to one exact FeatureSpec.

    Formula, source and point-in-time semantics are deliberately absent here.
    They remain owned by the referenced FeatureSpec snapshot.
    """

    attribute_id: str
    physical_attribute_id: str
    feature_ref: FeatureSpecRef
    attribute_family: str
    measurement_scale_id: str
    state_smoothing_scale_id: str
    normalization_reference_id: str
    state_policy_version: str

    schema_id: ClassVar[str] = MARKET_ATTRIBUTE_SPEC_SCHEMA_ID

    def __post_init__(self) -> None:
        _require_text(self.attribute_id, "attribute_id")
        _require_text(self.physical_attribute_id, "physical_attribute_id")
        if not isinstance(self.feature_ref, FeatureSpecRef):
            raise ValidationError("feature_ref must be a FeatureSpecRef")
        _require_text(self.attribute_family, "attribute_family")
        _require_text(self.measurement_scale_id, "measurement_scale_id")
        _require_text(self.state_smoothing_scale_id, "state_smoothing_scale_id")
        _require_text(
            self.normalization_reference_id,
            "normalization_reference_id",
        )
        _require_text(self.state_policy_version, "state_policy_version")

    def resolve_feature(self, library: FeatureLibrary) -> FeatureSpec:
        return self.feature_ref.resolve(library)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "attribute_id": self.attribute_id,
            "physical_attribute_id": self.physical_attribute_id,
            "feature_ref": self.feature_ref.to_dict(),
            "attribute_family": self.attribute_family,
            "measurement_scale_id": self.measurement_scale_id,
            "state_smoothing_scale_id": self.state_smoothing_scale_id,
            "normalization_reference_id": self.normalization_reference_id,
            "state_policy_version": self.state_policy_version,
            "field_labels_zh": dict(MARKET_ATTRIBUTE_LABELS_ZH),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> Self:
        _strict_fields(
            payload,
            frozenset(
                {
                    "schema_id",
                    "attribute_id",
                    "physical_attribute_id",
                    "feature_ref",
                    "attribute_family",
                    "measurement_scale_id",
                    "state_smoothing_scale_id",
                    "normalization_reference_id",
                    "state_policy_version",
                    "field_labels_zh",
                }
            ),
            "MarketAttributeSpec",
        )
        if payload.get("schema_id") != cls.schema_id:
            raise ValidationError("MarketAttributeSpec schema_id mismatch")
        if payload.get("field_labels_zh") != MARKET_ATTRIBUTE_LABELS_ZH:
            raise ValidationError("MarketAttributeSpec field_labels_zh mismatch")
        return cls(
            attribute_id=str(payload.get("attribute_id", "")),
            physical_attribute_id=str(payload.get("physical_attribute_id", "")),
            feature_ref=FeatureSpecRef.from_dict(_as_mapping(payload.get("feature_ref"), "feature_ref")),
            attribute_family=str(payload.get("attribute_family", "")),
            measurement_scale_id=str(payload.get("measurement_scale_id", "")),
            state_smoothing_scale_id=str(payload.get("state_smoothing_scale_id", "")),
            normalization_reference_id=str(payload.get("normalization_reference_id", "")),
            state_policy_version=str(payload.get("state_policy_version", "")),
        )


@dataclass(frozen=True, slots=True)
class MarketAttributeObservationKey:
    """Logical identity of one causal physical-attribute observation."""

    carrier_id: str
    carrier_definition_version: str
    bar_frequency: str
    observation_time: str
    feature_id: str
    feature_version: str
    measurement_scale_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "carrier_id",
            "carrier_definition_version",
            "bar_frequency",
            "observation_time",
            "feature_id",
            "feature_version",
            "measurement_scale_id",
        ):
            _require_text(str(getattr(self, field_name)), field_name)

    @property
    def logical_key(self) -> tuple[str, ...]:
        return (
            self.carrier_id,
            self.carrier_definition_version,
            self.bar_frequency,
            self.observation_time,
            self.feature_id,
            self.feature_version,
            self.measurement_scale_id,
        )


@dataclass(frozen=True, slots=True)
class MarketAttributeObservationIdentity:
    """Observation identity plus release-time metadata.

    ``available_at`` is intentionally not part of ``logical_key``.  Changing
    release policy creates a new bundle, not a duplicate logical observation.
    """

    key: MarketAttributeObservationKey
    available_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.key, MarketAttributeObservationKey):
            raise ValidationError("key must be a MarketAttributeObservationKey")
        _require_text(self.available_at, "available_at")

    @property
    def logical_key(self) -> tuple[str, ...]:
        return self.key.logical_key


@dataclass(frozen=True, slots=True)
class MarketStateKey:
    """Logical state identity derived from one physical observation."""

    observation_key: MarketAttributeObservationKey
    state_smoothing_scale_id: str
    normalization_reference_id: str
    normalization_policy_version: str
    state_policy_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.observation_key, MarketAttributeObservationKey):
            raise ValidationError("observation_key must be a MarketAttributeObservationKey")
        _require_text(self.state_smoothing_scale_id, "state_smoothing_scale_id")
        _require_text(
            self.normalization_reference_id,
            "normalization_reference_id",
        )
        _require_text(
            self.normalization_policy_version,
            "normalization_policy_version",
        )
        _require_text(self.state_policy_version, "state_policy_version")

    @property
    def logical_key(self) -> tuple[str, ...]:
        return self.observation_key.logical_key + (
            self.state_smoothing_scale_id,
            self.normalization_reference_id,
            self.normalization_policy_version,
            self.state_policy_version,
        )


@dataclass(frozen=True, slots=True)
class PinnedDatasetIdentity:
    """Immutable evidence for one exact, consumer-admitted DataHub dataset."""

    dataset_version: str
    dataset_kind: str
    state: str
    dataset_hash: str
    consumer_admission: str
    admission_policy_version: str
    quality_report_ref: str
    quality_score: float
    manifest_ref: str
    watermark: str

    schema_id: ClassVar[str] = PINNED_DATASET_IDENTITY_SCHEMA_ID

    def __post_init__(self) -> None:
        _require_text(self.dataset_version, "dataset_version")
        _require_text(self.dataset_kind, "dataset_kind")
        if self.state != "READY":
            raise ValidationError("DataHub dataset state must be READY")
        _require_text(self.dataset_hash, "dataset_hash")
        if self.consumer_admission != "granted":
            raise ValidationError("market-state source admission must be granted")
        if self.admission_policy_version != MARKET_STATE_SOURCE_ADMISSION_POLICY:
            raise ValidationError("market-state source admission policy mismatch")
        _require_text(self.quality_report_ref, "quality_report_ref")
        if self.quality_score < MARKET_STATE_MIN_QUALITY_SCORE:
            raise ValidationError("DataHub dataset quality score is below the A1 floor")
        _require_text(self.manifest_ref, "manifest_ref")
        _require_text(self.watermark, "watermark")

    @classmethod
    def from_datahub_response(
        cls,
        *,
        requested_version: str,
        response: Mapping[str, object],
    ) -> Self:
        _require_text(requested_version, "requested_version")
        raw = _as_mapping(response.get("data", response), "DataHub dataset response")
        manifest_value = raw.get("manifest")
        manifest = (
            _as_mapping(manifest_value, "DataHub dataset manifest")
            if manifest_value is not None
            else raw
        )
        actual_version = str(
            raw.get("dataset_version", manifest.get("dataset_version", ""))
        )
        if actual_version != requested_version:
            raise ValidationError(f"DataHub dataset version mismatch: requested {requested_version}, received {actual_version}")
        if str(manifest.get("dataset_version", actual_version)) != actual_version:
            raise ValidationError("DataHub response and manifest dataset versions disagree")
        state = str(raw.get("state", manifest.get("state", "")))
        if state != "READY":
            raise ValidationError("DataHub dataset state must be READY")
        dataset_kind = str(
            raw.get("dataset_kind", manifest.get("dataset_kind", ""))
        )
        if dataset_kind != "bars":
            raise ValidationError("market-state A1 requires a DataHub bars dataset")
        dataset_hash = str(
            raw.get(
                "dataset_hash",
                raw.get(
                    "content_hash",
                    manifest.get(
                        "dataset_hash",
                        manifest.get("content_hash", ""),
                    ),
                ),
            )
        )
        _require_text(dataset_hash, "dataset_hash")
        quality_report_ref = str(raw.get("quality_report_ref", ""))
        _require_text(quality_report_ref, "quality_report_ref")
        quality_report = _as_mapping(
            raw.get("quality_report"),
            "DataHub dataset quality_report",
        )
        if str(quality_report.get("target_dataset_version", "")) != actual_version:
            raise ValidationError("DataHub quality report targets another dataset")
        quality_summary_value = manifest.get("quality_summary")
        quality_summary = (
            _as_mapping(quality_summary_value, "DataHub manifest quality_summary")
            if quality_summary_value is not None
            else {}
        )
        quality_score = _require_matching_quality_score(
            quality_report=quality_report,
            quality_summary=quality_summary,
        )
        _require_clean_quality_evidence(
            quality_report=quality_report,
            quality_summary=quality_summary,
        )
        time_range_value = raw.get("time_range", manifest.get("time_range"))
        time_range = (
            _as_mapping(time_range_value, "DataHub dataset time_range")
            if time_range_value is not None
            else {}
        )
        watermark = str(
            raw.get(
                "watermark",
                raw.get(
                    "time_range_end",
                    time_range.get("end_time", time_range.get("end", "")),
                ),
            )
        )
        _require_text(watermark, "watermark")
        return cls(
            dataset_version=actual_version,
            dataset_kind=dataset_kind,
            state=state,
            dataset_hash=dataset_hash,
            consumer_admission="granted",
            admission_policy_version=MARKET_STATE_SOURCE_ADMISSION_POLICY,
            quality_report_ref=quality_report_ref,
            quality_score=quality_score,
            manifest_ref=f"datahub://history/datasets/{actual_version}",
            watermark=watermark,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "dataset_version": self.dataset_version,
            "dataset_kind": self.dataset_kind,
            "state": self.state,
            "dataset_hash": self.dataset_hash,
            "consumer_admission": self.consumer_admission,
            "admission_policy_version": self.admission_policy_version,
            "quality_report_ref": self.quality_report_ref,
            "quality_score": self.quality_score,
            "manifest_ref": self.manifest_ref,
            "watermark": self.watermark,
            "field_labels_zh": dict(PINNED_DATASET_LABELS_ZH),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> Self:
        _strict_fields(
            payload,
            frozenset(
                {
                    "schema_id",
                    "dataset_version",
                    "dataset_kind",
                    "state",
                    "dataset_hash",
                    "consumer_admission",
                    "admission_policy_version",
                    "quality_report_ref",
                    "quality_score",
                    "manifest_ref",
                    "watermark",
                    "field_labels_zh",
                }
            ),
            "PinnedDatasetIdentity",
        )
        if payload.get("schema_id") != cls.schema_id:
            raise ValidationError("PinnedDatasetIdentity schema_id mismatch")
        if payload.get("field_labels_zh") != PINNED_DATASET_LABELS_ZH:
            raise ValidationError("PinnedDatasetIdentity field_labels_zh mismatch")
        return cls(
            dataset_version=str(payload.get("dataset_version", "")),
            dataset_kind=str(payload.get("dataset_kind", "")),
            state=str(payload.get("state", "")),
            dataset_hash=str(payload.get("dataset_hash", "")),
            consumer_admission=str(payload.get("consumer_admission", "")),
            admission_policy_version=str(
                payload.get("admission_policy_version", "")
            ),
            quality_report_ref=str(payload.get("quality_report_ref", "")),
            quality_score=_quality_score(payload, "PinnedDatasetIdentity"),
            manifest_ref=str(payload.get("manifest_ref", "")),
            watermark=str(payload.get("watermark", "")),
        )


@dataclass(frozen=True, slots=True)
class OnlineMarketStateManifest:
    """Manifest for strictly causal market-state artifacts."""

    bundle_id: str
    carrier_id: str
    carrier_definition_version: str
    bar_frequency: str
    source_dataset: PinnedDatasetIdentity
    feature_snapshot: FeatureSpecSnapshot
    calendar_id: str
    calendar_version: str
    timezone: str
    session_policy_version: str
    price_adjustment: str
    available_at_policy: str
    artifacts: Mapping[str, str]

    schema_id: ClassVar[str] = ONLINE_MANIFEST_SCHEMA_ID
    production_authority: ClassVar[bool] = False
    causal: ClassVar[bool] = True
    uses_future: ClassVar[bool] = False
    allowed_usages: ClassVar[tuple[str, ...]] = ONLINE_USAGES

    def __post_init__(self) -> None:
        for field_name in (
            "bundle_id",
            "carrier_id",
            "carrier_definition_version",
            "bar_frequency",
            "calendar_id",
            "calendar_version",
            "timezone",
            "session_policy_version",
            "price_adjustment",
            "available_at_policy",
        ):
            _require_text(str(getattr(self, field_name)), field_name)
        if not isinstance(self.source_dataset, PinnedDatasetIdentity):
            raise ValidationError("source_dataset must be a PinnedDatasetIdentity")
        if not isinstance(self.feature_snapshot, FeatureSpecSnapshot):
            raise ValidationError("feature_snapshot must be a FeatureSpecSnapshot")
        object.__setattr__(
            self,
            "artifacts",
            MappingProxyType(_as_artifacts(self.artifacts)),
        )

    def assert_usage(self, usage: str) -> None:
        if usage not in self.allowed_usages:
            raise ValidationError(f"online manifest does not allow usage: {usage}")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "production_authority": self.production_authority,
            "causal": self.causal,
            "uses_future": self.uses_future,
            "allowed_usages": list(self.allowed_usages),
            "bundle_id": self.bundle_id,
            "carrier_id": self.carrier_id,
            "carrier_definition_version": self.carrier_definition_version,
            "bar_frequency": self.bar_frequency,
            "source_dataset": self.source_dataset.to_dict(),
            "feature_snapshot": self.feature_snapshot.to_dict(),
            "calendar_id": self.calendar_id,
            "calendar_version": self.calendar_version,
            "timezone": self.timezone,
            "session_policy_version": self.session_policy_version,
            "price_adjustment": self.price_adjustment,
            "available_at_policy": self.available_at_policy,
            "artifacts": dict(self.artifacts),
            "field_labels_zh": dict(ONLINE_MANIFEST_LABELS_ZH),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> Self:
        _strict_fields(
            payload,
            frozenset(
                {
                    "schema_id",
                    "production_authority",
                    "causal",
                    "uses_future",
                    "allowed_usages",
                    "bundle_id",
                    "carrier_id",
                    "carrier_definition_version",
                    "bar_frequency",
                    "source_dataset",
                    "feature_snapshot",
                    "calendar_id",
                    "calendar_version",
                    "timezone",
                    "session_policy_version",
                    "price_adjustment",
                    "available_at_policy",
                    "artifacts",
                    "field_labels_zh",
                }
            ),
            "online manifest",
        )
        if payload.get("schema_id") != cls.schema_id:
            raise ValidationError("online manifest schema_id mismatch")
        _require_false(payload.get("production_authority"), "production_authority")
        _require_true(payload.get("causal"), "causal")
        _require_false(payload.get("uses_future"), "uses_future")
        if _as_string_tuple(payload.get("allowed_usages"), "allowed_usages") != cls.allowed_usages:
            raise ValidationError("online manifest allowed_usages mismatch")
        if payload.get("field_labels_zh") != ONLINE_MANIFEST_LABELS_ZH:
            raise ValidationError("online manifest field_labels_zh mismatch")
        return cls(
            bundle_id=str(payload.get("bundle_id", "")),
            carrier_id=str(payload.get("carrier_id", "")),
            carrier_definition_version=str(payload.get("carrier_definition_version", "")),
            bar_frequency=str(payload.get("bar_frequency", "")),
            source_dataset=PinnedDatasetIdentity.from_dict(_as_mapping(payload.get("source_dataset"), "source_dataset")),
            feature_snapshot=FeatureSpecSnapshot.from_dict(_as_mapping(payload.get("feature_snapshot"), "feature_snapshot")),
            calendar_id=str(payload.get("calendar_id", "")),
            calendar_version=str(payload.get("calendar_version", "")),
            timezone=str(payload.get("timezone", "")),
            session_policy_version=str(payload.get("session_policy_version", "")),
            price_adjustment=str(payload.get("price_adjustment", "")),
            available_at_policy=str(payload.get("available_at_policy", "")),
            artifacts=_as_artifacts(payload.get("artifacts")),
        )


@dataclass(frozen=True, slots=True)
class RetroMarketStateManifest:
    """Manifest for future-aware retrospective analysis artifacts."""

    bundle_id: str
    online_bundle_id: str
    carrier_id: str
    carrier_definition_version: str
    bar_frequency: str
    source_dataset: PinnedDatasetIdentity
    feature_snapshot: FeatureSpecSnapshot
    artifacts: Mapping[str, str]

    schema_id: ClassVar[str] = RETRO_MANIFEST_SCHEMA_ID
    production_authority: ClassVar[bool] = False
    causal: ClassVar[bool] = False
    uses_future: ClassVar[bool] = True
    allowed_usages: ClassVar[tuple[str, ...]] = RETRO_USAGES

    def __post_init__(self) -> None:
        for field_name in (
            "bundle_id",
            "online_bundle_id",
            "carrier_id",
            "carrier_definition_version",
            "bar_frequency",
        ):
            _require_text(str(getattr(self, field_name)), field_name)
        if not isinstance(self.source_dataset, PinnedDatasetIdentity):
            raise ValidationError("source_dataset must be a PinnedDatasetIdentity")
        if not isinstance(self.feature_snapshot, FeatureSpecSnapshot):
            raise ValidationError("feature_snapshot must be a FeatureSpecSnapshot")
        object.__setattr__(
            self,
            "artifacts",
            MappingProxyType(_as_artifacts(self.artifacts)),
        )

    def assert_usage(self, usage: str) -> None:
        if usage not in self.allowed_usages:
            raise ValidationError(f"retro manifest does not allow usage: {usage}")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "production_authority": self.production_authority,
            "causal": self.causal,
            "uses_future": self.uses_future,
            "allowed_usages": list(self.allowed_usages),
            "bundle_id": self.bundle_id,
            "online_bundle_id": self.online_bundle_id,
            "carrier_id": self.carrier_id,
            "carrier_definition_version": self.carrier_definition_version,
            "bar_frequency": self.bar_frequency,
            "source_dataset": self.source_dataset.to_dict(),
            "feature_snapshot": self.feature_snapshot.to_dict(),
            "artifacts": dict(self.artifacts),
            "field_labels_zh": dict(RETRO_MANIFEST_LABELS_ZH),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> Self:
        _strict_fields(
            payload,
            frozenset(
                {
                    "schema_id",
                    "production_authority",
                    "causal",
                    "uses_future",
                    "allowed_usages",
                    "bundle_id",
                    "online_bundle_id",
                    "carrier_id",
                    "carrier_definition_version",
                    "bar_frequency",
                    "source_dataset",
                    "feature_snapshot",
                    "artifacts",
                    "field_labels_zh",
                }
            ),
            "retro manifest",
        )
        if payload.get("schema_id") != cls.schema_id:
            raise ValidationError("retro manifest schema_id mismatch")
        _require_false(payload.get("production_authority"), "production_authority")
        _require_false(payload.get("causal"), "causal")
        _require_true(payload.get("uses_future"), "uses_future")
        if _as_string_tuple(payload.get("allowed_usages"), "allowed_usages") != cls.allowed_usages:
            raise ValidationError("retro manifest allowed_usages mismatch")
        if payload.get("field_labels_zh") != RETRO_MANIFEST_LABELS_ZH:
            raise ValidationError("retro manifest field_labels_zh mismatch")
        return cls(
            bundle_id=str(payload.get("bundle_id", "")),
            online_bundle_id=str(payload.get("online_bundle_id", "")),
            carrier_id=str(payload.get("carrier_id", "")),
            carrier_definition_version=str(payload.get("carrier_definition_version", "")),
            bar_frequency=str(payload.get("bar_frequency", "")),
            source_dataset=PinnedDatasetIdentity.from_dict(_as_mapping(payload.get("source_dataset"), "source_dataset")),
            feature_snapshot=FeatureSpecSnapshot.from_dict(_as_mapping(payload.get("feature_snapshot"), "feature_snapshot")),
            artifacts=_as_artifacts(payload.get("artifacts")),
        )


__all__ = [
    "FeatureSpecRef",
    "FeatureSpecSnapshot",
    "MarketAttributeObservationIdentity",
    "MarketAttributeObservationKey",
    "MarketAttributeSpec",
    "MarketStateKey",
    "OnlineMarketStateManifest",
    "PinnedDatasetIdentity",
    "RetroMarketStateManifest",
]
