# pyright: reportUnknownArgumentType=false, reportUnusedCallResult=false
"""Frozen handoff contract for the middle mechanism-cognition stage."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Literal, cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest

RESEARCH_DECISION_PACKAGE_SCHEMA_ID: Final[str] = "market_state_research_decision_package@1.0"
RESEARCH_DECISION_PACKAGE_VERSION: Final[str] = "research_decision_package_v1"
ResearchDecision = Literal[
    "single_factor_candidate",
    "second_factor_mandate",
    "change_mechanism",
    "stop",
]
_DECISIONS: Final[frozenset[str]] = frozenset(
    {
        "single_factor_candidate",
        "second_factor_mandate",
        "change_mechanism",
        "stop",
    }
)


@dataclass(frozen=True, slots=True)
class ResearchDecisionPackage:
    """One tool's complete and zero-authority Stage-2 research decision."""

    package_id: str
    tool_id: str
    tool_version: str
    preparation_ref: Mapping[str, object]
    legacy_evidence: Mapping[str, object]
    mechanism_hypothesis: Mapping[str, object]
    factor_representation: Mapping[str, object]
    experiment_registration: Mapping[str, object]
    data_usage_ledger: Mapping[str, object]
    dsr_attribution: Mapping[str, object]
    decision: Mapping[str, object]
    handoff_rule: Mapping[str, object]
    stage3_authorized: bool = False
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (self.package_id, self.tool_id, self.tool_version)):
            raise ValidationError("research decision identity is required")
        _validate_artifact_ref(self.preparation_ref, field="preparation")
        source_ref = self.legacy_evidence.get("source_handoff_ref")
        if not isinstance(source_ref, Mapping):
            raise ValidationError("research decision needs a legacy source reference")
        _validate_artifact_ref(source_ref, field="legacy handoff")
        if self.legacy_evidence.get("f2_eligible") is not False:
            raise ValidationError("legacy evidence cannot open F2")
        if self.legacy_evidence.get("migration_status") != "legacy_diagnostic_only":
            raise ValidationError("legacy evidence migration status changed")
        if self.legacy_evidence.get("potential_projection_status") != "legacy_evidence_untyped":
            raise ValidationError("legacy evidence was silently promoted")
        if self.data_usage_ledger.get("post_2020_rows_used") != 0:
            raise ValidationError("Stage-2 research opened post-2020 detail")
        if self.data_usage_ledger.get("blackbox_detail_opened") is not False:
            raise ValidationError("Stage-2 research opened blackbox detail")
        status = self.decision.get("status")
        if not isinstance(status, str) or status not in _DECISIONS:
            raise ValidationError("research decision status is invalid")
        if self.decision.get("third_factor_eligible") is not False:
            raise ValidationError("Stage-2 package cannot open a third factor")
        handoff_status = self.handoff_rule.get("status")
        expected_handoff = "frozen_rule" if status in {"single_factor_candidate", "second_factor_mandate"} else "no_rule"
        if handoff_status != expected_handoff:
            raise ValidationError("research decision and handoff rule disagree")
        if status == "second_factor_mandate":
            residual_status = cast(Mapping[str, object], self.dsr_attribution.get("r", {})).get("residual_evidence_status")
            if residual_status != "independently_registered_positive":
                raise ValidationError("second-factor mandate requires independently registered residual evidence")
        if status not in {"single_factor_candidate", "second_factor_mandate"}:
            if self.decision.get("f2_eligible") is not False:
                raise ValidationError("a stopped mechanism cannot open F2")
        if self.stage3_authorized or self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("research decision package cannot grant authority")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": RESEARCH_DECISION_PACKAGE_SCHEMA_ID,
            "package_version": RESEARCH_DECISION_PACKAGE_VERSION,
            "package_id": self.package_id,
            "tool_id": self.tool_id,
            "tool_version": self.tool_version,
            "preparation_ref": dict(self.preparation_ref),
            "legacy_evidence": dict(self.legacy_evidence),
            "mechanism_hypothesis": dict(self.mechanism_hypothesis),
            "factor_representation": dict(self.factor_representation),
            "experiment_registration": dict(self.experiment_registration),
            "data_usage_ledger": dict(self.data_usage_ledger),
            "dsr_attribution": dict(self.dsr_attribution),
            "decision": dict(self.decision),
            "handoff_rule": dict(self.handoff_rule),
            "stage3_authorized": self.stage3_authorized,
            "production_authority": self.production_authority,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "field_labels_zh": {
                "mechanism_hypothesis": "可证伪机制、反例与预测",
                "factor_representation": "因子公式、方向、系数、指数、尺度与别名处理",
                "experiment_registration": "数据读取前冻结的有限实验与多重性家族",
                "data_usage_ledger": "已消费、禁止区间与可用时点",
                "dsr_attribution": "D参数差异、S条件增量与R剩余遗憾归因",
                "decision": "单因子、第二因子、换机制或停止的唯一裁决",
                "handoff_rule": "第三段可逐字实现的规则；本包不执行第三段",
            },
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload


def validate_research_decision_package(payload: Mapping[str, object]) -> None:
    """Validate digest, stage boundary, and deterministic decision semantics."""

    if payload.get("schema_id") != RESEARCH_DECISION_PACKAGE_SCHEMA_ID:
        raise ValidationError("research decision package schema changed")
    if payload.get("package_version") != RESEARCH_DECISION_PACKAGE_VERSION:
        raise ValidationError("research decision package version changed")
    digest_payload = dict(payload)
    digest = digest_payload.pop("semantic_digest", None)
    if digest != canonical_digest(digest_payload):
        raise ValidationError("research decision package semantic digest is invalid")
    _ = ResearchDecisionPackage(
        package_id=_required_string(payload, "package_id"),
        tool_id=_required_string(payload, "tool_id"),
        tool_version=_required_string(payload, "tool_version"),
        preparation_ref=_required_mapping(payload, "preparation_ref"),
        legacy_evidence=_required_mapping(payload, "legacy_evidence"),
        mechanism_hypothesis=_required_mapping(payload, "mechanism_hypothesis"),
        factor_representation=_required_mapping(payload, "factor_representation"),
        experiment_registration=_required_mapping(payload, "experiment_registration"),
        data_usage_ledger=_required_mapping(payload, "data_usage_ledger"),
        dsr_attribution=_required_mapping(payload, "dsr_attribution"),
        decision=_required_mapping(payload, "decision"),
        handoff_rule=_required_mapping(payload, "handoff_rule"),
        stage3_authorized=payload.get("stage3_authorized") is True,
        production_authority=payload.get("production_authority") is True,
        dynamic_parameter_authority=payload.get("dynamic_parameter_authority") is True,
        tool_routing_authority=payload.get("tool_routing_authority") is True,
    )


def _validate_artifact_ref(payload: Mapping[str, object], *, field: str) -> None:
    path = payload.get("relative_path")
    digest = payload.get("sha256")
    if not isinstance(path, str) or not path.strip():
        raise ValidationError(f"{field} artifact path is required")
    if not isinstance(digest, str) or not _is_digest(digest):
        raise ValidationError(f"{field} artifact digest is invalid")


def _is_digest(value: str) -> bool:
    if not value.startswith("sha256:") or len(value) != 71:
        return False
    try:
        int(value[7:], 16)
    except ValueError:
        return False
    return True


def _required_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"research decision package requires {key}")
    return value


def _required_mapping(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValidationError(f"research decision package requires {key}")
    return cast(Mapping[str, object], value)


__all__ = [
    "RESEARCH_DECISION_PACKAGE_SCHEMA_ID",
    "RESEARCH_DECISION_PACKAGE_VERSION",
    "ResearchDecision",
    "ResearchDecisionPackage",
    "validate_research_decision_package",
]
