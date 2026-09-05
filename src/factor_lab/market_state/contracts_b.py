"""B-stage contracts for retrospective maps and causal similar periods."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar, Self, cast

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.contracts import (
    RETRO_USAGES,
    FeatureSpecSnapshot,
    PinnedDatasetIdentity,
)

B_RETRO_MANIFEST_SCHEMA_ID = "market_state_retro_manifest@2.0"
B_SEGMENTATION_POLICY_VERSION = "retro_segmentation_policy_v1"
B_SIMILARITY_POLICY_VERSION = "similarity_policy_v1"
B_RETRO_ARTIFACT_NAMES = frozenset(
    {
        "retro_segments",
        "similar_periods",
        "similarity_sensitivity",
        "retro_report_zh",
        "artifact_inventory",
    }
)

B_RETRO_LABELS_ZH = {
    "bundle_id": "回溯研究包标识",
    "online_bundle_id": "对应在线父包标识",
    "online_bundle_semantic_digest": "在线父包语义摘要",
    "bar_frequencies": "K线频率集合",
    "source_datasets": "固定源数据集集合",
    "feature_snapshot": "特征规格快照",
    "segmentation_policy_version": "事后分段政策版本",
    "similarity_policy_version": "因果相似期政策版本",
    "artifacts": "回溯研究产物",
}


def _require_text(value: object, field: str) -> str:
    text = str(value)
    if not text.strip():
        raise ValidationError(f"{field} is required")
    return text


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


@dataclass(frozen=True, slots=True)
class RetroMarketStateManifestB:
    """Physically isolated B research manifest bound to one A2 online bundle."""

    bundle_id: str
    online_bundle_id: str
    online_bundle_semantic_digest: str
    carrier_id: str
    carrier_definition_version: str
    bar_frequencies: tuple[str, ...]
    source_datasets: Mapping[str, PinnedDatasetIdentity]
    feature_snapshot: FeatureSpecSnapshot
    segmentation_policy_version: str
    similarity_policy_version: str
    artifacts: Mapping[str, str]

    schema_id: ClassVar[str] = B_RETRO_MANIFEST_SCHEMA_ID
    production_authority: ClassVar[bool] = False
    causal: ClassVar[bool] = False
    uses_future: ClassVar[bool] = True
    allowed_usages: ClassVar[tuple[str, ...]] = RETRO_USAGES

    def __post_init__(self) -> None:
        for field in (
            "bundle_id",
            "online_bundle_id",
            "online_bundle_semantic_digest",
            "carrier_id",
            "carrier_definition_version",
            "segmentation_policy_version",
            "similarity_policy_version",
        ):
            _require_text(getattr(self, field), field)
        if not self.online_bundle_semantic_digest.startswith("sha256:"):
            raise ValidationError("online_bundle_semantic_digest must be sha256")
        frequencies = tuple(str(item) for item in self.bar_frequencies)
        if not frequencies or len(set(frequencies)) != len(frequencies):
            raise ValidationError("bar_frequencies must be unique and non-empty")
        object.__setattr__(self, "bar_frequencies", frequencies)
        sources = dict(self.source_datasets)
        if set(sources) != set(frequencies):
            raise ValidationError("source_datasets must match bar_frequencies")
        if not all(isinstance(item, PinnedDatasetIdentity) for item in sources.values()):
            raise ValidationError("source_datasets must contain pinned identities")
        object.__setattr__(self, "source_datasets", MappingProxyType(sources))
        if not isinstance(self.feature_snapshot, FeatureSpecSnapshot):
            raise ValidationError("feature_snapshot must be a FeatureSpecSnapshot")
        artifacts = {str(key): _require_text(value, f"artifact {key}") for key, value in self.artifacts.items()}
        if not artifacts:
            raise ValidationError("artifacts is required")
        if set(artifacts) != B_RETRO_ARTIFACT_NAMES:
            raise ValidationError("B retro artifacts must match the frozen artifact set")
        object.__setattr__(self, "artifacts", MappingProxyType(artifacts))

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
            "online_bundle_semantic_digest": self.online_bundle_semantic_digest,
            "carrier_id": self.carrier_id,
            "carrier_definition_version": self.carrier_definition_version,
            "bar_frequencies": list(self.bar_frequencies),
            "source_datasets": {
                key: value.to_dict() for key, value in sorted(self.source_datasets.items())
            },
            "feature_snapshot": self.feature_snapshot.to_dict(),
            "segmentation_policy_version": self.segmentation_policy_version,
            "similarity_policy_version": self.similarity_policy_version,
            "artifacts": dict(self.artifacts),
            "field_labels_zh": dict(B_RETRO_LABELS_ZH),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> Self:
        allowed = {
            "schema_id",
            "production_authority",
            "causal",
            "uses_future",
            "allowed_usages",
            "bundle_id",
            "online_bundle_id",
            "online_bundle_semantic_digest",
            "carrier_id",
            "carrier_definition_version",
            "bar_frequencies",
            "source_datasets",
            "feature_snapshot",
            "segmentation_policy_version",
            "similarity_policy_version",
            "artifacts",
            "field_labels_zh",
        }
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ValidationError(f"B retro manifest unknown field(s): {', '.join(unknown)}")
        if payload.get("schema_id") != cls.schema_id:
            raise ValidationError("B retro manifest schema mismatch")
        if payload.get("production_authority") is not False or payload.get("causal") is not False:
            raise ValidationError("B retro manifest must be non-production and non-causal")
        if payload.get("uses_future") is not True:
            raise ValidationError("B retro manifest must declare uses_future=true")
        usages = payload.get("allowed_usages")
        if not isinstance(usages, list) or tuple(str(item) for item in usages) != cls.allowed_usages:
            raise ValidationError("B retro manifest allowed_usages mismatch")
        if payload.get("field_labels_zh") != B_RETRO_LABELS_ZH:
            raise ValidationError("B retro manifest field_labels_zh mismatch")
        frequencies_raw = payload.get("bar_frequencies")
        if not isinstance(frequencies_raw, list):
            raise ValidationError("bar_frequencies must be a list")
        sources_raw = _mapping(payload.get("source_datasets"), "source_datasets")
        artifacts_raw = _mapping(payload.get("artifacts"), "artifacts")
        return cls(
            bundle_id=_require_text(payload.get("bundle_id"), "bundle_id"),
            online_bundle_id=_require_text(payload.get("online_bundle_id"), "online_bundle_id"),
            online_bundle_semantic_digest=_require_text(
                payload.get("online_bundle_semantic_digest"), "online_bundle_semantic_digest"
            ),
            carrier_id=_require_text(payload.get("carrier_id"), "carrier_id"),
            carrier_definition_version=_require_text(
                payload.get("carrier_definition_version"), "carrier_definition_version"
            ),
            bar_frequencies=tuple(str(item) for item in frequencies_raw),
            source_datasets={
                str(key): PinnedDatasetIdentity.from_dict(_mapping(value, f"source_datasets.{key}"))
                for key, value in sources_raw.items()
            },
            feature_snapshot=FeatureSpecSnapshot.from_dict(
                _mapping(payload.get("feature_snapshot"), "feature_snapshot")
            ),
            segmentation_policy_version=_require_text(
                payload.get("segmentation_policy_version"), "segmentation_policy_version"
            ),
            similarity_policy_version=_require_text(
                payload.get("similarity_policy_version"), "similarity_policy_version"
            ),
            artifacts={str(key): str(value) for key, value in artifacts_raw.items()},
        )


__all__ = [
    "B_RETRO_MANIFEST_SCHEMA_ID",
    "B_RETRO_ARTIFACT_NAMES",
    "B_SEGMENTATION_POLICY_VERSION",
    "B_SIMILARITY_POLICY_VERSION",
    "RetroMarketStateManifestB",
]
