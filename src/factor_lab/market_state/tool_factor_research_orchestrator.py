# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Read-only V2 orchestration for legacy market-state factor research.

This module is intentionally a coordinator, not a search runner.  It joins
the stage-0 truth gate, parameter registration boundary, scale catalog, and
stage-5 factor-potential vocabulary into one reproducible evidence package.
It never rewrites a lane handoff and never opens task4 or a factor attempt.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.causal_scale_ladder import build_causal_scale_ladder_v2
from factor_lab.market_state.research_artifact_truth_gate import (
    LANE_TRUTH_SPECS,
    ResearchReplayBaseline,
    build_research_replay_baseline,
)
from factor_lab.market_state.time_scale_catalog import build_time_scale_catalog_v2
from factor_lab.market_state.tool_formula_surface_audit import (
    build_formula_surface_audit_v2,
)
from factor_lab.market_state.tool_parameter_catalog_v2 import (
    build_tool_parameter_catalog_v2,
)
from factor_lab.market_state.tool_parameter_experiment_registry import (
    build_tool_parameter_experiment_registry,
)

TOOL_FACTOR_RESEARCH_RUN_MANIFEST_SCHEMA_ID: Final[str] = "market_state_tool_factor_research_run_manifest@1.0"
TOOL_FACTOR_RESEARCH_REGISTRATION_AUDIT_SCHEMA_ID: Final[str] = "market_state_tool_factor_research_registration_audit@1.0"
TOOL_FACTOR_RESEARCH_SCALE_REGISTRY_SCHEMA_ID: Final[str] = "market_state_tool_factor_research_scale_registry@1.0"
TOOL_FACTOR_RESEARCH_POTENTIAL_PROJECTION_SCHEMA_ID: Final[str] = "market_state_tool_factor_research_potential_projection@1.0"
TOOL_FACTOR_RESEARCH_SUPERVISOR_HANDOFF_SCHEMA_ID: Final[str] = "market_state_tool_factor_research_supervisor_handoff@1.0"
TOOL_FACTOR_RESEARCH_ORCHESTRATOR_VERSION: Final[str] = "market_state_tool_factor_research_orchestrator_v1"
LEGACY_HANDOFF_SCHEMA_ID: Final[str] = "market_state_tool_attribute_mapping_external_handoff@1.0"
FACTOR_POTENTIAL_SCHEMA_ID: Final[str] = "market_state_factor_potential_assessment@1.0"
PROJECT_MULTIPLICITY_FAMILY_ID: Final[str] = "market_state_v2_legacy_lane_readonly_migration"
_AUTHORITY_KEYS: Final[tuple[str, ...]] = (
    "production_authority",
    "dynamic_parameter_authority",
    "tool_routing_authority",
)
_MIGRATION_STATUSES: Final[frozenset[str]] = frozenset({"invalid_scope_stop", "legacy_diagnostic_only", "legacy_replay_pending"})
_POTENTIAL_PROJECTION_STATUSES: Final[frozenset[str]] = frozenset({"invalid_scope_stop", "legacy_evidence_untyped"})


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _read_json_mapping(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"orchestrator cannot read JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"orchestrator expected a JSON object: {path}")
    return value


def _nonempty_strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    values: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return ()
        values.append(item)
    return tuple(sorted(set(values)))


def _digest_payload(payload: Mapping[str, object], *, key: str = "semantic_digest") -> str:
    normalized = dict(payload)
    _ = normalized.pop(key, None)
    return canonical_digest(normalized)


def _digest_is_valid(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        return False
    try:
        _ = int(value.removeprefix("sha256:"), 16)
    except ValueError:
        return False
    return True


def _count_jsonl_rows(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
    except OSError as exc:
        raise ValidationError(f"orchestrator cannot read attempt ledger: {path}") from exc


@dataclass(frozen=True, slots=True)
class LegacyLanePotentialProjection:
    """A no-upgrade explanation of one V1 lane in the stage-5 vocabulary."""

    lane_id: str
    tool_ids: tuple[str, ...]
    source_handoff_relative_path: str
    source_handoff_sha256: str
    legacy_research_status: str
    truth_status: Literal["truth_gate_passed", "invalid_artifact_chain"]
    legacy_candidate_mapping_count: int
    legacy_attempt_count: int
    migration_status: Literal["invalid_scope_stop", "legacy_diagnostic_only", "legacy_replay_pending"]
    potential_projection_status: Literal["invalid_scope_stop", "legacy_evidence_untyped"]
    stop_reason: str
    truth_gate_blockers: tuple[str, ...]
    f2_eligible: bool = False
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        if not self.lane_id.strip() or not self.tool_ids:
            raise ValidationError("legacy lane projection identity is incomplete")
        if not self.source_handoff_relative_path.endswith("supervisor_handoff.json"):
            raise ValidationError("legacy lane projection must name its source handoff")
        if not _digest_is_valid(self.source_handoff_sha256):
            raise ValidationError("legacy lane projection requires a source handoff digest")
        if self.legacy_candidate_mapping_count < 0 or self.legacy_attempt_count < 0:
            raise ValidationError("legacy lane counts must be non-negative")
        if self.migration_status not in _MIGRATION_STATUSES:
            raise ValidationError("unsupported legacy lane migration status")
        if self.potential_projection_status not in _POTENTIAL_PROJECTION_STATUSES:
            raise ValidationError("unsupported potential projection status")
        if self.truth_status == "invalid_artifact_chain":
            if self.migration_status != "invalid_scope_stop" or self.potential_projection_status != "invalid_scope_stop":
                raise ValidationError("invalid legacy evidence must remain an invalid-scope stop")
        elif self.migration_status == "invalid_scope_stop":
            raise ValidationError("truth-passed legacy evidence cannot claim an invalid-scope stop")
        if self.f2_eligible or self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("legacy V2 migration cannot grant factor or production authority")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": TOOL_FACTOR_RESEARCH_POTENTIAL_PROJECTION_SCHEMA_ID,
            "projection_version": TOOL_FACTOR_RESEARCH_ORCHESTRATOR_VERSION,
            "lane_id": self.lane_id,
            "tool_ids": list(self.tool_ids),
            "source_handoff": {
                "schema_id": LEGACY_HANDOFF_SCHEMA_ID,
                "relative_path": self.source_handoff_relative_path,
                "file_sha256": self.source_handoff_sha256,
            },
            "legacy_research_status": self.legacy_research_status,
            "truth_status": self.truth_status,
            "legacy_candidate_mapping_count": self.legacy_candidate_mapping_count,
            "legacy_attempt_count": self.legacy_attempt_count,
            "migration_status": self.migration_status,
            "potential_assessment": {
                "assessment_schema_id": FACTOR_POTENTIAL_SCHEMA_ID,
                "assessment_emitted": False,
                "assessment_status": self.potential_projection_status,
                "f2_eligible": self.f2_eligible,
                "reason": self.stop_reason,
            },
            "truth_gate_blockers": list(self.truth_gate_blockers),
            "production_authority": self.production_authority,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "field_labels_zh": {
                "legacy_attempt_count": "遗留lane已记录尝试数，仅用于项目级多重性账本",
                "migration_status": "只读V2迁移状态，不改变V1裁决",
                "potential_assessment": "V2因子潜力评估投影；遗留未类型化证据不得构造正式评估",
                "f2_eligible": "是否允许开启第二因子尝试",
            },
        }
        payload["semantic_digest"] = _digest_payload(payload)
        return payload


@dataclass(frozen=True, slots=True)
class ToolFactorResearchOrchestration:
    """All stage-6 artifacts reconstructed from immutable sources."""

    run_manifest: Mapping[str, object]
    registration_audit: Mapping[str, object]
    scale_registry: Mapping[str, object]
    projections: tuple[LegacyLanePotentialProjection, ...]
    supervisor_handoff: Mapping[str, object]

    def artifact_payloads(self) -> dict[str, Mapping[str, object]]:
        return {
            "run_manifest.json": dict(self.run_manifest),
            "registration_audit.json": dict(self.registration_audit),
            "scale_registry.json": dict(self.scale_registry),
            "lane_potential_projections.json": {
                "schema_id": TOOL_FACTOR_RESEARCH_POTENTIAL_PROJECTION_SCHEMA_ID,
                "projection_version": TOOL_FACTOR_RESEARCH_ORCHESTRATOR_VERSION,
                "projections": [item.to_dict() for item in self.projections],
                "field_labels_zh": {"projections": "四条遗留lane的只读V2因子潜力投影"},
            },
            "supervisor_handoff.json": dict(self.supervisor_handoff),
        }


def _projection_for_lane(
    *,
    project_root: Path,
    lane: Mapping[str, object],
) -> LegacyLanePotentialProjection:
    lane_id = str(lane.get("lane_id", ""))
    artifact_root = str(lane.get("artifact_root", ""))
    handoff_relative_path = f"{artifact_root}/supervisor_handoff.json"
    handoff_path = project_root / handoff_relative_path
    handoff = _read_json_mapping(handoff_path)
    if handoff.get("schema_id") != LEGACY_HANDOFF_SCHEMA_ID:
        raise ValidationError(f"legacy handoff schema mismatch: {handoff_relative_path}")
    truth_status_value = lane.get("truth_status")
    if truth_status_value == "truth_gate_passed":
        truth_status: Literal["truth_gate_passed", "invalid_artifact_chain"] = "truth_gate_passed"
    elif truth_status_value == "invalid_artifact_chain":
        truth_status = "invalid_artifact_chain"
    else:
        raise ValidationError(f"legacy lane has an unsupported truth status: {lane_id}")
    tool_ids = _nonempty_strings(lane.get("reported_tool_ids"))
    if not tool_ids:
        raise ValidationError(f"legacy lane has no reported tools: {lane_id}")
    raw_count = handoff.get("candidate_mapping_count")
    if not isinstance(raw_count, int) or raw_count < 0:
        raise ValidationError(f"legacy lane candidate count is invalid: {lane_id}")
    blockers = lane.get("blockers")
    blocker_values = _nonempty_strings(blockers)
    attempts = _count_jsonl_rows(project_root / artifact_root / "attempt_ledger.jsonl")
    reported_status = str(handoff.get("research_status", "missing"))
    if truth_status == "invalid_artifact_chain":
        migration_status: Literal["invalid_scope_stop", "legacy_diagnostic_only", "legacy_replay_pending"] = "invalid_scope_stop"
        potential_status: Literal["invalid_scope_stop", "legacy_evidence_untyped"] = "invalid_scope_stop"
        stop_reason = (
            "repairable stage0 truth failure: reconcile conflicting ready counts, "
            "attach lane-relative event evidence with recomputed metrics, then rebuild "
            "the baseline before V2 potential assessment"
        )
    elif reported_status == "ready_for_supervisor_replay":
        migration_status = "legacy_replay_pending"
        potential_status = "legacy_evidence_untyped"
        stop_reason = "legacy candidate awaits independent V2 replay and typed evidence; F2 remains closed"
    else:
        migration_status = "legacy_diagnostic_only"
        potential_status = "legacy_evidence_untyped"
        stop_reason = "legacy diagnostic evidence is not a typed V2 potential assessment; F2 remains closed"
    return LegacyLanePotentialProjection(
        lane_id=lane_id,
        tool_ids=tool_ids,
        source_handoff_relative_path=handoff_relative_path,
        source_handoff_sha256=_sha256_file(handoff_path),
        legacy_research_status=reported_status,
        truth_status=truth_status,
        legacy_candidate_mapping_count=raw_count,
        legacy_attempt_count=attempts,
        migration_status=migration_status,
        potential_projection_status=potential_status,
        stop_reason=stop_reason,
        truth_gate_blockers=blocker_values,
    )


def _registration_audit(project_root: Path) -> dict[str, object]:
    catalog = build_tool_parameter_catalog_v2().to_dict()
    formula_audit = build_formula_surface_audit_v2(project_root).to_dict()
    registry = build_tool_parameter_experiment_registry(
        project_root=project_root,
        catalog=build_tool_parameter_catalog_v2(),
    ).to_dict()
    private_audit = registry.get("private_parameter_mutation_audit")
    findings = private_audit.get("findings") if isinstance(private_audit, Mapping) else []
    finding_count = len(findings) if isinstance(findings, list) else 0
    audit_status = "blocked_private_parameter_mutation_audit" if finding_count else "passed_no_experiment_registered"
    experiments = registry.get("experiments")
    experiment_count = len(experiments) if isinstance(experiments, list) else 0
    payload: dict[str, object] = {
        "schema_id": TOOL_FACTOR_RESEARCH_REGISTRATION_AUDIT_SCHEMA_ID,
        "contract_version": TOOL_FACTOR_RESEARCH_ORCHESTRATOR_VERSION,
        "audit_status": audit_status,
        "catalog": {
            "schema_id": catalog["schema_id"],
            "semantic_digest": catalog["semantic_digest"],
            "migration_tool_ids": catalog["migration_tool_ids"],
        },
        "formula_surface_audit": {
            "schema_id": formula_audit["schema_id"],
            "semantic_digest": formula_audit["semantic_digest"],
            "audit_status": formula_audit["audit_status"],
        },
        "experiment_registry": {
            "schema_id": registry["schema_id"],
            "semantic_digest": registry["semantic_digest"],
            "experiment_count": experiment_count,
            "private_parameter_mutation_findings": finding_count,
        },
        "new_experiment_authorized": False,
        "reason": (
            "registration is an audit only; no parameter experiment is registered"
            if not finding_count
            else "script-local parameter mutation findings require remediation before any V2 experiment"
        ),
        "production_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
        "field_labels_zh": {
            "audit_status": "登记审计结果，不是实验执行授权",
            "migration_tool_ids": "已完成V2公式表面审计的工具范围",
            "private_parameter_mutation_findings": "脚本私自替换参数字典的发现数",
            "new_experiment_authorized": "是否允许开启新的参数实验",
        },
    }
    payload["semantic_digest"] = _digest_payload(payload)
    return payload


def _scale_registry() -> dict[str, object]:
    catalog = build_time_scale_catalog_v2().to_dict()
    ladder = build_causal_scale_ladder_v2().to_dict()
    scales = catalog.get("scales")
    scale_ids = [str(item.get("scale_id")) for item in scales if isinstance(item, Mapping)] if isinstance(scales, list) else []
    payload: dict[str, object] = {
        "schema_id": TOOL_FACTOR_RESEARCH_SCALE_REGISTRY_SCHEMA_ID,
        "contract_version": TOOL_FACTOR_RESEARCH_ORCHESTRATOR_VERSION,
        "registry_status": "registered_no_experiment_bound",
        "time_scale_catalog": {
            "schema_id": catalog["schema_id"],
            "semantic_digest": catalog["semantic_digest"],
            "factor_scale_ids": scale_ids,
            "multiplicity_family_id": "market_state_v2_factor_lookback",
        },
        "causal_scale_ladder": {
            "schema_id": ladder["schema_id"],
            "semantic_digest": ladder["semantic_digest"],
            "filter_sampling_policy": ladder["filter_sampling_policy"],
        },
        "experiment_bound_scale_ids": [],
        "production_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
        "field_labels_zh": {
            "factor_scale_ids": "已登记的因子物理交易会话观察窗",
            "experiment_bound_scale_ids": "已与参数实验预注册绑定的观察窗；本阶段为空",
            "filter_sampling_policy": "数字滤波仅接受完整因果K线的采样规则",
        },
    }
    payload["semantic_digest"] = _digest_payload(payload)
    return payload


def _project_multiplicity_ledger(
    projections: Sequence[LegacyLanePotentialProjection],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "family_id": PROJECT_MULTIPLICITY_FAMILY_ID,
        "project_attempt_count": sum(item.legacy_attempt_count for item in projections),
        "project_candidate_mapping_count": sum(item.legacy_candidate_mapping_count for item in projections),
        "lane_attempt_counts": {item.lane_id: item.legacy_attempt_count for item in projections},
        "lane_candidate_mapping_counts": {item.lane_id: item.legacy_candidate_mapping_count for item in projections},
        "correction_status": "ledger_only_legacy_untyped",
        "corrected_pvalue_emitted": False,
        "reason": (
            "legacy lanes use heterogeneous, untyped candidate families; counts are merged "
            "for future project-level correction but no p-value is recomputed or upgraded"
        ),
        "field_labels_zh": {
            "project_attempt_count": "四条lane已记录尝试总数",
            "correction_status": "项目级多重性纠错可用性状态",
            "corrected_pvalue_emitted": "是否从遗留证据伪造了新的校正p值",
        },
    }
    payload["semantic_digest"] = _digest_payload(payload)
    return payload


def _run_manifest(
    *,
    baseline: ResearchReplayBaseline,
    registration_audit: Mapping[str, object],
    scale_registry: Mapping[str, object],
    projections: Sequence[LegacyLanePotentialProjection],
    project_multiplicity_ledger: Mapping[str, object],
) -> dict[str, object]:
    baseline_manifest = baseline.manifest
    payload: dict[str, object] = {
        "schema_id": TOOL_FACTOR_RESEARCH_RUN_MANIFEST_SCHEMA_ID,
        "contract_version": TOOL_FACTOR_RESEARCH_ORCHESTRATOR_VERSION,
        "run_id": "market-state-v2-readonly-lane-migration",
        "baseline_manifest": {
            "schema_id": baseline_manifest["schema_id"],
            "manifest_semantic_digest": baseline_manifest["manifest_semantic_digest"],
        },
        "registration_audit_semantic_digest": registration_audit["semantic_digest"],
        "scale_registry_semantic_digest": scale_registry["semantic_digest"],
        "lane_projections": [
            {
                "lane_id": item.lane_id,
                "source_handoff_sha256": item.source_handoff_sha256,
                "projection_semantic_digest": item.to_dict()["semantic_digest"],
            }
            for item in projections
        ],
        "project_multiplicity_ledger": dict(project_multiplicity_ledger),
        "artifacts": [
            "registration_audit.json",
            "scale_registry.json",
            "lane_potential_projections.json",
            "supervisor_handoff.json",
        ],
        "resumption": {
            "mode": "rebuild_from_immutable_v1_artifacts",
            "chat_transcript_required": False,
            "legacy_v1_artifacts_mutated": False,
            "task4_execution_open": False,
        },
        "production_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
        "field_labels_zh": {
            "lane_projections": "四条lane的输入handoff摘要与V2投影摘要",
            "resumption": "中断后不依赖聊天正文的重建规则",
            "project_multiplicity_ledger": "跨lane尝试次数的项目级账本",
        },
    }
    payload["manifest_semantic_digest"] = _digest_payload(payload, key="manifest_semantic_digest")
    return payload


def _supervisor_handoff(
    *,
    run_manifest: Mapping[str, object],
    registration_audit: Mapping[str, object],
    scale_registry: Mapping[str, object],
    projections: Sequence[LegacyLanePotentialProjection],
    project_multiplicity_ledger: Mapping[str, object],
) -> dict[str, object]:
    invalid_lanes = [item.lane_id for item in projections if item.migration_status == "invalid_scope_stop"]
    replay_pending_lanes = [item.lane_id for item in projections if item.migration_status == "legacy_replay_pending"]
    payload: dict[str, object] = {
        "schema_id": TOOL_FACTOR_RESEARCH_SUPERVISOR_HANDOFF_SCHEMA_ID,
        "contract_version": TOOL_FACTOR_RESEARCH_ORCHESTRATOR_VERSION,
        "orchestration_status": "readonly_migration_complete_task4_frozen",
        "run_manifest_semantic_digest": run_manifest["manifest_semantic_digest"],
        "registration_audit_semantic_digest": registration_audit["semantic_digest"],
        "scale_registry_semantic_digest": scale_registry["semantic_digest"],
        "lane_projections": [
            {
                "lane_id": item.lane_id,
                "migration_status": item.migration_status,
                "potential_projection_status": item.potential_projection_status,
                "f2_eligible": item.f2_eligible,
                "projection_semantic_digest": item.to_dict()["semantic_digest"],
            }
            for item in projections
        ],
        "project_multiplicity_ledger": dict(project_multiplicity_ledger),
        "invalid_scope_lanes": invalid_lanes,
        "legacy_replay_pending_lanes": replay_pending_lanes,
        "task4_execution_open": False,
        "next_permitted_action": "repair_or_replay_only_after_a_new_explicit_registration",
        "production_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
        "field_labels_zh": {
            "invalid_scope_lanes": "因真值链失败而不能进入V2因子评估的lane",
            "legacy_replay_pending_lanes": "可等待独立回放但尚未有V2类型化证据的lane",
            "task4_execution_open": "任务4是否已解除冻结",
            "next_permitted_action": "当前证据下唯一允许的后续操作",
        },
    }
    payload["semantic_digest"] = _digest_payload(payload)
    return payload


def build_tool_factor_research_orchestration(
    project_root: Path,
) -> ToolFactorResearchOrchestration:
    """Rebuild all stage-6 artifacts from four immutable V1 lane packages."""

    root = project_root.resolve()
    baseline = build_research_replay_baseline(root)
    lane_rows = baseline.manifest.get("lanes")
    if not isinstance(lane_rows, list) or len(lane_rows) != len(LANE_TRUTH_SPECS):
        raise ValidationError("stage-6 orchestration requires the four stage-0 lane snapshots")
    projections = tuple(_projection_for_lane(project_root=root, lane=lane) for lane in lane_rows if isinstance(lane, Mapping))
    if len(projections) != len(LANE_TRUTH_SPECS):
        raise ValidationError("stage-6 orchestration lane snapshot is malformed")
    registration_audit = _registration_audit(root)
    scale_registry = _scale_registry()
    multiplicity_ledger = _project_multiplicity_ledger(projections)
    run_manifest = _run_manifest(
        baseline=baseline,
        registration_audit=registration_audit,
        scale_registry=scale_registry,
        projections=projections,
        project_multiplicity_ledger=multiplicity_ledger,
    )
    supervisor_handoff = _supervisor_handoff(
        run_manifest=run_manifest,
        registration_audit=registration_audit,
        scale_registry=scale_registry,
        projections=projections,
        project_multiplicity_ledger=multiplicity_ledger,
    )
    result = ToolFactorResearchOrchestration(
        run_manifest=run_manifest,
        registration_audit=registration_audit,
        scale_registry=scale_registry,
        projections=projections,
        supervisor_handoff=supervisor_handoff,
    )
    validate_tool_factor_research_orchestration(result)
    return result


def _require_payload_digest(payload: Mapping[str, object], *, key: str) -> None:
    actual = payload.get(key)
    if not _digest_is_valid(actual) or actual != _digest_payload(payload, key=key):
        raise ValidationError(f"orchestrator payload digest does not reconcile: {key}")


def validate_tool_factor_research_orchestration(
    result: ToolFactorResearchOrchestration,
) -> None:
    """Validate the zero-authority, four-lane, resumable orchestration contract."""

    _require_payload_digest(result.run_manifest, key="manifest_semantic_digest")
    _require_payload_digest(result.registration_audit, key="semantic_digest")
    _require_payload_digest(result.scale_registry, key="semantic_digest")
    _require_payload_digest(result.supervisor_handoff, key="semantic_digest")
    if len(result.projections) != len(LANE_TRUTH_SPECS):
        raise ValidationError("orchestration must contain exactly four legacy lane projections")
    lane_ids = [item.lane_id for item in result.projections]
    expected_lane_ids = [item.lane_id for item in LANE_TRUTH_SPECS]
    if sorted(lane_ids) != sorted(expected_lane_ids) or len(lane_ids) != len(set(lane_ids)):
        raise ValidationError("orchestration lane coverage differs from the stage-0 baseline")
    for projection in result.projections:
        payload = projection.to_dict()
        _require_payload_digest(payload, key="semantic_digest")
        potential_assessment = payload.get("potential_assessment")
        if not isinstance(potential_assessment, Mapping) or potential_assessment.get("f2_eligible") is not False:
            raise ValidationError("legacy projection cannot open F2")
    for payload in (
        result.run_manifest,
        result.registration_audit,
        result.scale_registry,
        result.supervisor_handoff,
    ):
        if any(payload.get(key) is not False for key in _AUTHORITY_KEYS):
            raise ValidationError("stage-6 orchestration cannot grant authority")
    if result.run_manifest.get("resumption") != {
        "mode": "rebuild_from_immutable_v1_artifacts",
        "chat_transcript_required": False,
        "legacy_v1_artifacts_mutated": False,
        "task4_execution_open": False,
    }:
        raise ValidationError("orchestration must be resumable without legacy chat transcripts")
    if result.supervisor_handoff.get("task4_execution_open") is not False:
        raise ValidationError("stage-6 orchestration must keep task4 frozen")
    ledger = result.supervisor_handoff.get("project_multiplicity_ledger")
    if not isinstance(ledger, Mapping):
        raise ValidationError("orchestration requires a project multiplicity ledger")
    if ledger.get("project_attempt_count") != sum(item.legacy_attempt_count for item in result.projections):
        raise ValidationError("project attempt ledger does not reconcile to lane projections")
    if ledger.get("project_candidate_mapping_count") != sum(item.legacy_candidate_mapping_count for item in result.projections):
        raise ValidationError("project candidate ledger does not reconcile to lane projections")
    if ledger.get("corrected_pvalue_emitted") is not False:
        raise ValidationError("legacy migration must not emit a fabricated project p-value")


def _write_json_atomically(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        _ = json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        _ = handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def write_tool_factor_research_orchestration(
    *,
    project_root: Path,
    output_dir: Path,
) -> ToolFactorResearchOrchestration:
    """Write only V2-owned artifacts; V1 lane directories remain untouched."""

    result = build_tool_factor_research_orchestration(project_root)
    target = output_dir.resolve()
    source_root = project_root.resolve() / "output/market-state-foundation/formula-mechanism/external-family-lanes"
    try:
        _ = target.relative_to(source_root)
    except ValueError:
        pass
    else:
        raise ValidationError("stage-6 output directory cannot be inside a legacy lane")
    for filename, payload in result.artifact_payloads().items():
        _write_json_atomically(target / filename, payload)
    return result


__all__ = [
    "FACTOR_POTENTIAL_SCHEMA_ID",
    "LegacyLanePotentialProjection",
    "PROJECT_MULTIPLICITY_FAMILY_ID",
    "TOOL_FACTOR_RESEARCH_ORCHESTRATOR_VERSION",
    "TOOL_FACTOR_RESEARCH_POTENTIAL_PROJECTION_SCHEMA_ID",
    "TOOL_FACTOR_RESEARCH_REGISTRATION_AUDIT_SCHEMA_ID",
    "TOOL_FACTOR_RESEARCH_RUN_MANIFEST_SCHEMA_ID",
    "TOOL_FACTOR_RESEARCH_SCALE_REGISTRY_SCHEMA_ID",
    "TOOL_FACTOR_RESEARCH_SUPERVISOR_HANDOFF_SCHEMA_ID",
    "ToolFactorResearchOrchestration",
    "build_tool_factor_research_orchestration",
    "validate_tool_factor_research_orchestration",
    "write_tool_factor_research_orchestration",
]
