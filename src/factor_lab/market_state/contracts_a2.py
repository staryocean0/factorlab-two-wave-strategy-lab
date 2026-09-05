"""A2 multi-frequency online manifest contract."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar, Self, cast

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.contracts import (
    ONLINE_USAGES,
    FeatureSpecSnapshot,
    PinnedDatasetIdentity,
)

A2_ONLINE_MANIFEST_SCHEMA_ID = "market_state_online_manifest@2.0"
A2_CURRENT_FREQUENCIES = ("1d", "60m")
A2_MANIFEST_LABELS_ZH = {
    "bundle_id": "A2 在线包标识",
    "carrier_id": "载体标识",
    "carrier_definition_version": "载体定义版本",
    "bar_frequencies": "权威 K 线频率",
    "source_datasets": "各频率固定源数据集",
    "feature_snapshot": "完整 V1 特征规格快照",
    "build_mode": "本次构建模式",
    "parent_bundle_id": "增量父包标识",
    "performance_budget_version": "冻结性能预算版本",
    "performance_budget_status": "性能预算状态",
    "artifacts": "在线产物",
}


@dataclass(frozen=True, slots=True)
class OnlineMarketStateManifestA2:
    bundle_id: str
    carrier_id: str
    carrier_definition_version: str
    bar_frequencies: tuple[str, ...]
    source_datasets: Mapping[str, PinnedDatasetIdentity]
    feature_snapshot: FeatureSpecSnapshot
    calendar_id: str
    calendar_version: str
    timezone: str
    session_policy_version: str
    price_adjustment: str
    available_at_policy: str
    build_mode: str
    parent_bundle_id: str | None
    performance_budget_version: str
    performance_budget_status: str
    artifacts: Mapping[str, str]

    schema_id: ClassVar[str] = A2_ONLINE_MANIFEST_SCHEMA_ID
    production_authority: ClassVar[bool] = False
    causal: ClassVar[bool] = True
    uses_future: ClassVar[bool] = False
    allowed_usages: ClassVar[tuple[str, ...]] = ONLINE_USAGES

    def __post_init__(self) -> None:
        for name in (
            "bundle_id",
            "carrier_id",
            "carrier_definition_version",
            "calendar_id",
            "calendar_version",
            "timezone",
            "session_policy_version",
            "price_adjustment",
            "available_at_policy",
            "performance_budget_version",
            "performance_budget_status",
        ):
            if not str(getattr(self, name)).strip():
                raise ValidationError(f"{name} is required")
        if tuple(self.bar_frequencies) != A2_CURRENT_FREQUENCIES:
            raise ValidationError("A2 current frequencies must be exactly 1d and 60m")
        if set(self.source_datasets) != set(A2_CURRENT_FREQUENCIES):
            raise ValidationError("A2 requires one pinned source per current frequency")
        if any(
            not isinstance(value, PinnedDatasetIdentity)
            for value in self.source_datasets.values()
        ):
            raise ValidationError("A2 sources must be pinned DataHub identities")
        if not isinstance(self.feature_snapshot, FeatureSpecSnapshot):
            raise ValidationError("feature_snapshot must be exact")
        if self.build_mode not in {"full", "incremental"}:
            raise ValidationError("A2 build mode must be full or incremental")
        if self.build_mode == "incremental" and not self.parent_bundle_id:
            raise ValidationError("incremental A2 manifest requires parent bundle")
        if self.performance_budget_status != "passed":
            raise ValidationError("A2 current cannot publish without passing its budget")
        if not self.artifacts:
            raise ValidationError("A2 manifest artifacts are required")
        object.__setattr__(
            self, "source_datasets", MappingProxyType(dict(self.source_datasets))
        )
        object.__setattr__(self, "artifacts", MappingProxyType(dict(self.artifacts)))

    def assert_usage(self, usage: str) -> None:
        if usage not in self.allowed_usages:
            raise ValidationError(f"A2 online manifest does not allow usage: {usage}")

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
            "bar_frequencies": list(self.bar_frequencies),
            "source_datasets": {
                key: value.to_dict()
                for key, value in sorted(self.source_datasets.items())
            },
            "feature_snapshot": self.feature_snapshot.to_dict(),
            "calendar_id": self.calendar_id,
            "calendar_version": self.calendar_version,
            "timezone": self.timezone,
            "session_policy_version": self.session_policy_version,
            "price_adjustment": self.price_adjustment,
            "available_at_policy": self.available_at_policy,
            "build_mode": self.build_mode,
            "parent_bundle_id": self.parent_bundle_id,
            "performance_budget_version": self.performance_budget_version,
            "performance_budget_status": self.performance_budget_status,
            "artifacts": dict(self.artifacts),
            "field_labels_zh": dict(A2_MANIFEST_LABELS_ZH),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> Self:
        expected = {
            "schema_id",
            "production_authority",
            "causal",
            "uses_future",
            "allowed_usages",
            "bundle_id",
            "carrier_id",
            "carrier_definition_version",
            "bar_frequencies",
            "source_datasets",
            "feature_snapshot",
            "calendar_id",
            "calendar_version",
            "timezone",
            "session_policy_version",
            "price_adjustment",
            "available_at_policy",
            "build_mode",
            "parent_bundle_id",
            "performance_budget_version",
            "performance_budget_status",
            "artifacts",
            "field_labels_zh",
        }
        if set(payload) != expected:
            raise ValidationError(
                f"A2 manifest fields mismatch: {sorted(set(payload) ^ expected)}"
            )
        if payload.get("schema_id") != cls.schema_id:
            raise ValidationError("A2 manifest schema mismatch")
        if payload.get("production_authority") is not False:
            raise ValidationError("A2 production authority must be false")
        if payload.get("causal") is not True or payload.get("uses_future") is not False:
            raise ValidationError("A2 manifest causal boundary mismatch")
        if payload.get("allowed_usages") != list(ONLINE_USAGES):
            raise ValidationError("A2 allowed usages mismatch")
        if payload.get("field_labels_zh") != A2_MANIFEST_LABELS_ZH:
            raise ValidationError("A2 Chinese field labels mismatch")
        raw_frequencies = payload.get("bar_frequencies")
        if not isinstance(raw_frequencies, list):
            raise ValidationError("A2 bar frequencies must be a list")
        raw_sources = payload.get("source_datasets")
        if not isinstance(raw_sources, Mapping):
            raise ValidationError("A2 source datasets must be an object")
        raw_snapshot = payload.get("feature_snapshot")
        raw_artifacts = payload.get("artifacts")
        if not isinstance(raw_snapshot, Mapping) or not isinstance(raw_artifacts, Mapping):
            raise ValidationError("A2 snapshot and artifacts must be objects")
        return cls(
            bundle_id=str(payload.get("bundle_id", "")),
            carrier_id=str(payload.get("carrier_id", "")),
            carrier_definition_version=str(
                payload.get("carrier_definition_version", "")
            ),
            bar_frequencies=tuple(str(value) for value in raw_frequencies),
            source_datasets={
                str(key): PinnedDatasetIdentity.from_dict(
                    cast(Mapping[str, object], value)
                )
                for key, value in raw_sources.items()
                if isinstance(value, Mapping)
            },
            feature_snapshot=FeatureSpecSnapshot.from_dict(
                cast(Mapping[str, object], raw_snapshot)
            ),
            calendar_id=str(payload.get("calendar_id", "")),
            calendar_version=str(payload.get("calendar_version", "")),
            timezone=str(payload.get("timezone", "")),
            session_policy_version=str(payload.get("session_policy_version", "")),
            price_adjustment=str(payload.get("price_adjustment", "")),
            available_at_policy=str(payload.get("available_at_policy", "")),
            build_mode=str(payload.get("build_mode", "")),
            parent_bundle_id=(
                str(payload["parent_bundle_id"])
                if payload.get("parent_bundle_id") is not None
                else None
            ),
            performance_budget_version=str(
                payload.get("performance_budget_version", "")
            ),
            performance_budget_status=str(
                payload.get("performance_budget_status", "")
            ),
            artifacts={str(key): str(value) for key, value in raw_artifacts.items()},
        )


__all__ = [
    "A2_CURRENT_FREQUENCIES",
    "A2_ONLINE_MANIFEST_SCHEMA_ID",
    "OnlineMarketStateManifestA2",
]
