"""Layer-1 identity ledger for clock-aligned timing artifacts.

This is not an attribute formula module. Old official-session packs stay
read-only. Dual-scale remakes must write a new variant_id and keep the
parent artifact untouched. Layer-2 measurement consumes the remade clocks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from factor_lab.data.session_offset_defaults import (
    LEGACY_OFFICIAL_1500_QFQ,
    OFFICIAL_SESSION_CONTRACT,
    optional_remake_variants,
)

LEGACY_CLOUDRIDGE_1D = (
    "output/baylum-data-update/current/"
    "cloudridge_1d_qfq_service_confirmed_19940307_20260626_levels.csv"
)
LEGACY_CLOUDRIDGE_60M = (
    "output/baylum-data-update/current/"
    "cloudridge_60m_qfq_1m_path_19901219_20260624_levels.csv"
)
LEGACY_CLOUDRIDGE_15M = (
    "output/cloudridge_15m_qfq_1m_path_20260722/"
    "cloudridge_15m_qfq_1m_path_20080101_20260624_levels.csv"
)


@dataclass(frozen=True, slots=True)
class TimingArtifactIdentity:
    artifact_id: str
    native_frequency: str
    data_contract: str
    execution_window: str
    source_path: str
    role: str
    remake_variant_ids: tuple[str, ...]
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["remake_variant_ids"] = list(self.remake_variant_ids)
        return payload


def _variant_ids(native_frequency: str) -> tuple[str, ...]:
    return tuple(
        str(item["variant_id"]) for item in optional_remake_variants(native_frequency)
    )


TIMING_INFRASTRUCTURE_ARTIFACTS: tuple[TimingArtifactIdentity, ...] = (
    TimingArtifactIdentity(
        artifact_id="cloudridge_1d_qfq_official_1500",
        native_frequency="1d",
        data_contract=OFFICIAL_SESSION_CONTRACT,
        execution_window="next_session",
        source_path=LEGACY_CLOUDRIDGE_1D,
        role="legacy_readonly",
        remake_variant_ids=_variant_ids("1d"),
        notes="Official 15:00 daily CloudRidge levels. Do not overwrite.",
    ),
    TimingArtifactIdentity(
        artifact_id="cloudridge_60m_qfq_official_0930",
        native_frequency="60m",
        data_contract=OFFICIAL_SESSION_CONTRACT,
        execution_window="next_tradable_after_bar_close",
        source_path=LEGACY_CLOUDRIDGE_60M,
        role="legacy_readonly",
        remake_variant_ids=_variant_ids("60m"),
        notes="Official 09:30 60m CloudRidge levels. Do not overwrite.",
    ),
    TimingArtifactIdentity(
        artifact_id="cloudridge_15m_qfq_official_0930",
        native_frequency="15m",
        data_contract=OFFICIAL_SESSION_CONTRACT,
        execution_window="next_tradable_after_bar_close",
        source_path=LEGACY_CLOUDRIDGE_15M,
        role="legacy_readonly",
        remake_variant_ids=_variant_ids("15m"),
        notes="Official 09:45-labeled 15m CloudRidge levels. Do not overwrite.",
    ),
    TimingArtifactIdentity(
        artifact_id="factorlab_v9_1d_qfq_official_1500",
        native_frequency="1d",
        data_contract=LEGACY_OFFICIAL_1500_QFQ,
        execution_window="next_session",
        source_path=LEGACY_OFFICIAL_1500_QFQ,
        role="legacy_readonly",
        remake_variant_ids=_variant_ids("1d"),
        notes="Pinned FactorLab 2009-2025 official 15:00 qfq daily.",
    ),
)


def timing_artifact_ledger() -> list[dict[str, Any]]:
    return [item.to_dict() for item in TIMING_INFRASTRUCTURE_ARTIFACTS]


def identity_for_artifact(artifact_id: str) -> TimingArtifactIdentity:
    for item in TIMING_INFRASTRUCTURE_ARTIFACTS:
        if item.artifact_id == artifact_id:
            return item
    raise KeyError(f"unknown timing artifact: {artifact_id}")


def assert_legacy_not_overwritten(
    *,
    output_path: str,
    parent: Mapping[str, Any] | None = None,
) -> None:
    """Fail closed if a remake tries to write back onto a legacy source."""

    output = str(output_path or "").replace("\\", "/")
    for item in TIMING_INFRASTRUCTURE_ARTIFACTS:
        if item.role == "legacy_readonly" and output.endswith(item.source_path):
            raise ValueError(
                f"refusing to overwrite legacy artifact {item.artifact_id}: {item.source_path}"
            )
    if parent and str(parent.get("role") or "") == "legacy_readonly":
        parent_path = str(parent.get("source_path") or "").replace("\\", "/")
        if parent_path and output.endswith(parent_path):
            raise ValueError("remake output must not equal the legacy parent path")
