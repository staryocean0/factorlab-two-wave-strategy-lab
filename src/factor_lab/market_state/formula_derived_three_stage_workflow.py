"""Hash-bound V3 Stage-1 -> Stage-2 -> Stage-3 workflow handoff."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.formula_derivation.preparation import (
    validate_formula_derivation_preparation_payload,
)
from factor_lab.market_state.formula_derivation.validation import (
    require_digest,
    validate_semantic_digest,
)
from factor_lab.market_state.frozen_joint_policy_replay import (
    BacktestAcceptancePackage,
    validate_backtest_acceptance_package,
)
from factor_lab.market_state.joint_policy_attempt_registry import (
    JointPolicyCandidate,
    require_candidate_in_registered_attempt_manifest,
    validate_joint_policy_attempt_manifest,
)
from factor_lab.market_state.joint_policy_family_registry import JointPolicyFamily
from factor_lab.market_state.joint_research_decision_package import (
    JointResearchDecisionPackage,
    read_legacy_research_decision_as_diagnostic,
    validate_joint_research_decision_package,
)

THREE_STAGE_WORKFLOW_SCHEMA_ID: Final[str] = "market_state_formula_derived_three_stage_workflow@1.0"
FOUR_LAYER_ROLE: Final[str] = "layer3b_strategy_ephemeral"
LIFECYCLE: Final[str] = (
    "replaceable_by_more_complete_layer2_measurement_not_a_long_term_foundation"
)
_STAGE1_REF_KEYS: Final[frozenset[str]] = frozenset({"artifact_id", "semantic_digest", "status"})
_DOWNSTREAM_REF_KEYS: Final[frozenset[str]] = frozenset(
    {"artifact_id", "semantic_digest", "parent_semantic_digest", "status"}
)
_LEGACY_DIAGNOSTIC_KEYS: Final[frozenset[str]] = frozenset(
    {
        "source_schema_id", "source_package_id", "source_semantic_digest",
        "legacy_decision_status", "v3_diagnostic_status", "v3_migration_status",
        "accepted_joint_policy", "promotion_allowed", "stage3_handoff_eligible",
        "stage3_authorized", "production_authority", "dynamic_parameter_authority",
        "tool_routing_authority", "field_labels_zh", "semantic_digest",
    }
)
WorkflowStatus = Literal[
    "stage1_ready",
    "stage2_decided",
    "stage3_replayed",
    "returned_to_formula_derivation",
]


@dataclass(frozen=True, slots=True)
class FormulaDerivedThreeStageWorkflow:
    """Immutable cross-stage digest ledger with diagnostic-only legacy links."""

    workflow_id: str
    stage1_ref: Mapping[str, object]
    stage2_ref: Mapping[str, object]
    stage3_ref: Mapping[str, object]
    legacy_diagnostics: tuple[Mapping[str, object], ...]
    workflow_status: WorkflowStatus
    data_usage_ledger: Mapping[str, object]
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        if not self.workflow_id.strip():
            raise ValidationError("three-stage workflow identity is required")
        _validate_ref(self.stage1_ref, "stage1_ref")
        if self.stage2_ref:
            _validate_ref(self.stage2_ref, "stage2_ref")
        if self.stage3_ref:
            _validate_ref(self.stage3_ref, "stage3_ref")
        expected_status: WorkflowStatus = "stage1_ready"
        if self.stage2_ref:
            expected_status = "stage2_decided"
        if self.stage3_ref:
            replay_status = self.stage3_ref.get("status")
            expected_status = "stage3_replayed" if replay_status == "accepted_frozen_replay" else "returned_to_formula_derivation"
        if self.workflow_status != expected_status:
            raise ValidationError("three-stage workflow status disagrees with stage refs")
        if self.stage3_ref and not self.stage2_ref:
            raise ValidationError("Stage 3 cannot exist without a Stage-2 decision")
        if self.stage2_ref and self.stage2_ref.get("parent_semantic_digest") != self.stage1_ref.get("semantic_digest"):
            raise ValidationError("Stage-2 workflow ref lost its Stage-1 parent binding")
        if self.stage3_ref and self.stage3_ref.get("parent_semantic_digest") != self.stage2_ref.get("semantic_digest"):
            raise ValidationError("Stage-3 workflow ref lost its Stage-2 parent binding")
        expected_workflow_id = _workflow_id(
            stage1_ref=self.stage1_ref,
            stage2_ref=self.stage2_ref,
            stage3_ref=self.stage3_ref,
            legacy_diagnostics=self.legacy_diagnostics,
        )
        if self.workflow_id != expected_workflow_id:
            raise ValidationError("three-stage workflow identity lost its cross-stage binding")
        for item in self.legacy_diagnostics:
            if set(item) != set(_LEGACY_DIAGNOSTIC_KEYS):
                raise ValidationError("legacy diagnostic fields changed")
            validate_semantic_digest(item)
            if (
                item.get("promotion_allowed") is not False
                or item.get("accepted_joint_policy") is not False
                or item.get("stage3_handoff_eligible") is not False
                or item.get("stage3_authorized") is not False
            ):
                raise ValidationError("legacy diagnostic was promoted")
        if self.data_usage_ledger.get("post_2020_rows_used") != 0:
            raise ValidationError("three-stage workflow opened the sealed interval")
        if self.data_usage_ledger.get("action_detail_exposed") is not False:
            raise ValidationError("three-stage workflow exposed trade-level detail")
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("three-stage workflow cannot grant authority")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": THREE_STAGE_WORKFLOW_SCHEMA_ID,
            "workflow_id": self.workflow_id,
            "stage1_ref": dict(self.stage1_ref),
            "stage2_ref": dict(self.stage2_ref),
            "stage3_ref": dict(self.stage3_ref),
            "legacy_diagnostics": [dict(item) for item in self.legacy_diagnostics],
            "workflow_status": self.workflow_status,
            "data_usage_ledger": dict(self.data_usage_ledger),
            "production_authority": self.production_authority,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "field_labels_zh": {
                "stage1_ref": "第一段公式派生准备包引用",
                "stage2_ref": "第二段完整联合策略决定引用",
                "stage3_ref": "第三段冻结规则机械重放引用",
                "legacy_diagnostics": "旧版裁决只读诊断映射",
                "workflow_status": "三段工作流状态",
                "data_usage_ledger": "跨段数据使用与细节密封台账",
            },
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload


def build_three_stage_workflow(
    *,
    stage1_preparation: Mapping[str, object],
    decision: JointResearchDecisionPackage | None = None,
    backtest: BacktestAcceptancePackage | None = None,
    legacy_packages: Sequence[Mapping[str, object]] = (),
) -> FormulaDerivedThreeStageWorkflow:
    """Bind validated stage artifacts without changing any upstream decision."""

    validate_formula_derivation_preparation_payload(stage1_preparation)
    stage1_digest = require_digest(
        stage1_preparation.get("semantic_digest"),
        field="stage1 preparation semantic_digest",
    )
    stage1_ref: dict[str, object] = {
        "artifact_id": "formula-derivation-preparation:v1",
        "semantic_digest": stage1_digest,
        "status": "ready_for_joint_mechanism_identification",
    }
    stage2_ref: dict[str, object] = {}
    stage3_ref: dict[str, object] = {}
    if decision is not None:
        decision_payload = decision.to_dict()
        validate_joint_research_decision_package(decision_payload)
        _validate_decision_against_stage1(stage1_preparation, decision)
        stage2_ref = {
            "artifact_id": decision.package_id,
            "semantic_digest": require_digest(
                decision_payload.get("semantic_digest"),
                field="stage2 decision semantic_digest",
            ),
            "parent_semantic_digest": stage1_digest,
            "status": decision.decision_status,
        }
    if backtest is not None:
        if decision is None:
            raise ValidationError("Stage 3 cannot bind without a Stage-2 decision")
        backtest_payload = backtest.to_dict()
        validate_backtest_acceptance_package(backtest_payload)
        decision_ref = backtest.decision_package_ref
        if decision_ref.get("semantic_digest") != stage2_ref.get("semantic_digest"):
            raise ValidationError("Stage-3 replay does not bind the Stage-2 decision")
        stage3_ref = {
            "artifact_id": backtest.package_id,
            "semantic_digest": require_digest(
                backtest_payload.get("semantic_digest"),
                field="stage3 backtest semantic_digest",
            ),
            "parent_semantic_digest": stage2_ref["semantic_digest"],
            "status": backtest.replay_status,
        }
    diagnostics = tuple(read_legacy_research_decision_as_diagnostic(payload) for payload in legacy_packages)
    status: WorkflowStatus = "stage1_ready"
    if stage2_ref:
        status = "stage2_decided"
    if stage3_ref:
        status = "stage3_replayed" if stage3_ref["status"] == "accepted_frozen_replay" else "returned_to_formula_derivation"
    ledger = {
        "stage1_market_rows_read": 0,
        "stage1_return_rows_read": 0,
        "post_2020_rows_used": 0,
        "sealed_interval": "2021-01-01/2026-12-31",
        "action_detail_exposed": False,
        "stage3_rule_modification_count": 0,
    }
    workflow = FormulaDerivedThreeStageWorkflow(
        workflow_id=_workflow_id(
            stage1_ref=stage1_ref,
            stage2_ref=stage2_ref,
            stage3_ref=stage3_ref,
            legacy_diagnostics=diagnostics,
        ),
        stage1_ref=stage1_ref,
        stage2_ref=stage2_ref,
        stage3_ref=stage3_ref,
        legacy_diagnostics=diagnostics,
        workflow_status=status,
        data_usage_ledger=ledger,
    )
    validate_three_stage_workflow(workflow.to_dict())
    return workflow


def validate_three_stage_workflow(payload: Mapping[str, object]) -> None:
    if payload.get("schema_id") != THREE_STAGE_WORKFLOW_SCHEMA_ID:
        raise ValidationError("three-stage workflow schema changed")
    validate_semantic_digest(payload)
    _reject_forbidden_authority(payload)
    workflow = FormulaDerivedThreeStageWorkflow(
        workflow_id=_required_text(payload, "workflow_id"),
        stage1_ref=_required_mapping(payload, "stage1_ref"),
        stage2_ref=_required_mapping(payload, "stage2_ref"),
        stage3_ref=_required_mapping(payload, "stage3_ref"),
        legacy_diagnostics=_required_mapping_sequence(payload, "legacy_diagnostics"),
        workflow_status=cast(WorkflowStatus, _required_text(payload, "workflow_status")),
        data_usage_ledger=_required_mapping(payload, "data_usage_ledger"),
        production_authority=payload.get("production_authority") is True,
        dynamic_parameter_authority=payload.get("dynamic_parameter_authority") is True,
        tool_routing_authority=payload.get("tool_routing_authority") is True,
    )
    if workflow.to_dict() != dict(payload):
        raise ValidationError("three-stage workflow does not round-trip canonically")


def write_three_stage_workflow(path: Path | str, workflow: FormulaDerivedThreeStageWorkflow) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _ = target.write_text(
        json.dumps(workflow.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_three_stage_workflow(path: Path | str) -> dict[str, object]:
    payload = cast(
        dict[str, object],
        json.loads(Path(path).read_text(encoding="utf-8")),
    )
    validate_three_stage_workflow(payload)
    return payload


def _validate_decision_against_stage1(
    stage1: Mapping[str, object],
    decision: JointResearchDecisionPackage,
) -> None:
    raw_tools = stage1.get("tools")
    if not isinstance(raw_tools, list):
        raise ValidationError("Stage-1 preparation has no tool rows")
    for raw in cast(list[object], raw_tools):
        if not isinstance(raw, Mapping):
            continue
        row = cast(Mapping[str, object], raw)
        if row.get("tool_id") != decision.tool_id:
            continue
        derivation = _required_mapping(row, "formula_derivation_package")
        family_payload = _required_mapping(row, "joint_policy_family")
        family = JointPolicyFamily.from_dict(family_payload)
        attempt_manifest = _required_mapping(row, "registered_policy_attempt_manifest")
        validate_joint_policy_attempt_manifest(attempt_manifest, family=family)
        attempt_digest = require_digest(attempt_manifest.get("semantic_digest"), field="Stage-1 attempt manifest digest")
        outer_attempt_digest = decision.assessment.joint_outer_oos_evidence.get("attempt_set_digest")
        multiplicity_attempt_digest = decision.assessment.multiplicity_evidence.get("attempt_set_digest")
        if (
            derivation.get("semantic_digest") != decision.derivation_package_ref.get("semantic_digest")
            or family_payload.get("semantic_digest") != decision.joint_policy_family_ref.get("semantic_digest")
            or derivation.get("semantic_digest") != decision.feature_materialization_ref.get("derivation_package_digest")
            or _required_mapping(derivation, "graph").get("semantic_digest") != decision.feature_materialization_ref.get("graph_digest")
            or attempt_digest != outer_attempt_digest
            or attempt_digest != multiplicity_attempt_digest
        ):
            raise ValidationError("Stage-2 decision refs do not match the Stage-1 tool artifacts")
        if decision.decision_status == "accepted_joint_policy":
            candidate_payload = decision.frozen_joint_policy.get("candidate")
            if not isinstance(candidate_payload, Mapping):
                raise ValidationError("accepted Stage-2 decision lacks a frozen candidate")
            if decision.frozen_joint_policy.get("attempt_set_digest") != attempt_digest:
                raise ValidationError("accepted Stage-2 decision lost its Stage-1 attempt binding")
            require_candidate_in_registered_attempt_manifest(
                payload=attempt_manifest,
                family=family,
                candidate=JointPolicyCandidate.from_dict(cast(Mapping[str, object], candidate_payload)),
                expected_attempt_set_digest=attempt_digest,
            )
        return
    raise ValidationError("Stage-2 decision tool is absent from Stage 1")


def _validate_ref(payload: Mapping[str, object], field: str) -> None:
    expected_keys = _STAGE1_REF_KEYS if field == "stage1_ref" else _DOWNSTREAM_REF_KEYS
    if set(payload) != set(expected_keys):
        raise ValidationError(f"three-stage workflow {field} fields changed")
    _ = _required_text(payload, "artifact_id")
    _ = require_digest(payload.get("semantic_digest"), field=f"{field}.semantic_digest")
    _ = _required_text(payload, "status")
    if field != "stage1_ref":
        _ = require_digest(payload.get("parent_semantic_digest"), field=f"{field}.parent_semantic_digest")


def _workflow_id(
    *,
    stage1_ref: Mapping[str, object],
    stage2_ref: Mapping[str, object],
    stage3_ref: Mapping[str, object],
    legacy_diagnostics: Sequence[Mapping[str, object]],
) -> str:
    return (
        "formula-derived-three-stage:"
        + canonical_digest(
            {
                "stage1": dict(stage1_ref),
                "stage2": dict(stage2_ref),
                "stage3": dict(stage3_ref),
                "legacy_diagnostics": [dict(item) for item in legacy_diagnostics],
            }
        ).removeprefix("sha256:")[:24]
    )


def _reject_forbidden_authority(value: object) -> None:
    if isinstance(value, Mapping):
        for raw_key, nested in cast(Mapping[object, object], value).items():
            key = str(raw_key)
            if key == "field_labels_zh":
                continue
            if (key.endswith("authority") or key == "stage3_authorized") and nested is not False:
                raise ValidationError("three-stage workflow nested authority changed")
            _reject_forbidden_authority(nested)
    elif isinstance(value, list):
        for nested in cast(list[object], value):
            _reject_forbidden_authority(nested)


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"three-stage workflow requires {key}")
    return value


def _required_mapping(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValidationError(f"three-stage workflow requires {key}")
    return cast(Mapping[str, object], value)


def _required_mapping_sequence(payload: Mapping[str, object], key: str) -> tuple[Mapping[str, object], ...]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValidationError(f"three-stage workflow requires {key}")
    items = cast(list[object], value)
    if any(not isinstance(item, Mapping) for item in items):
        raise ValidationError(f"three-stage workflow requires {key}")
    return tuple(cast(Mapping[str, object], item) for item in items)


__all__ = [
    "FOUR_LAYER_ROLE",
    "LIFECYCLE",
    "THREE_STAGE_WORKFLOW_SCHEMA_ID",
    "FormulaDerivedThreeStageWorkflow",
    "WorkflowStatus",
    "build_three_stage_workflow",
    "load_three_stage_workflow",
    "validate_three_stage_workflow",
    "write_three_stage_workflow",
]
