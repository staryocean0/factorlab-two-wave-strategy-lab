# pyright: reportAny=false, reportArgumentType=false
# pyright: reportImplicitStringConcatenation=false, reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Fail-closed bridge between parameter governance and K-line measurements.

The first infrastructure round governs tool formula surfaces, experiment
identities, and physical time scales.  The second round materializes causal
K-line attributes for four spectral tools.  This module is the executable
foreign-key boundary between those two layers.  It grants no experiment,
factor, routing, dynamic-parameter, or production authority.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, cast

import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.causal_scale_ladder import build_causal_scale_ladder_v2
from factor_lab.market_state.spectral_kline_attribute_measurement import (
    ATTRIBUTE_CONTRACT_BY_ID,
    ATTRIBUTE_CONTRACTS,
    HYPOTHESIS_STATUS,
    load_formula_hypotheses,
)
from factor_lab.market_state.time_scale_catalog import build_time_scale_catalog_v2
from factor_lab.market_state.tool_parameter_catalog_v2 import (
    ToolParameterSpecV2,
    build_tool_parameter_catalog_v2,
)
from factor_lab.market_state.tool_parameter_experiment_registry import (
    build_tool_parameter_experiment_registry,
)
from factor_lab.market_state.tool_registry import REQUIRED_TOOL_IDS

CROSS_ROUND_SCHEMA_ID: Final[str] = "market_state_cross_round_infrastructure@1.0"
CROSS_ROUND_VERSION: Final[str] = "market_state_cross_round_infrastructure_v1"
FOUNDATION_RELATIVE_DIR: Final[Path] = Path(
    "output/market-state-foundation/formula-mechanism/external-family-lanes/01_spectral_bandpass_components/00_formula_parameter_foundation"
)

_BROAD_KIND_ALLOWED_EFFECTS: Final[dict[str, frozenset[str]]] = {
    "exposed_runtime": frozenset({"same_tool_parameter"}),
    "derived_formula": frozenset({"derived"}),
    "decision_semantics": frozenset({"signal_policy"}),
    "execution_semantics": frozenset({"execution_profile"}),
    "external_execution": frozenset({"execution_profile"}),
    "initialization_boundary": frozenset({"validity_only", "new_tool_version"}),
    "fixed_design": frozenset({"tool_variant", "numerical_invariant", "new_tool_version", "validity_only"}),
}

HANDOFF_STATUS_REGISTRATION_REQUIRED: Final[str] = "registration_required"
HANDOFF_STATUS_DIAGNOSTIC_ONLY: Final[str] = "diagnostic_only"
HANDOFF_STATUS_EXPERIMENT_BOUND: Final[str] = "experiment_bound"


@dataclass(frozen=True, slots=True)
class CrossRoundCheck:
    check_id: str
    passed: bool
    evidence_zh: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CrossRoundInfrastructure:
    registered_tool_ids: tuple[str, ...]
    source_digests: Mapping[str, str]
    parameter_bridge: tuple[Mapping[str, object], ...]
    hypothesis_handoffs: tuple[Mapping[str, object], ...]
    checks: tuple[CrossRoundCheck, ...]
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False
    empirical_validation_executed: bool = False

    @property
    def infrastructure_gap_count(self) -> int:
        return sum(not item.passed for item in self.checks)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": CROSS_ROUND_SCHEMA_ID,
            "contract_version": CROSS_ROUND_VERSION,
            "source_digests": dict(self.source_digests),
            "counts": {
                "registered_tool_count": len(self.registered_tool_ids),
                "broad_parameter_count": len(self.parameter_bridge),
                "mapped_parameter_count": sum(str(item["mapping_status"]) == "catalog_exact" for item in self.parameter_bridge),
                "hypothesis_handoff_count": len(self.hypothesis_handoffs),
                "attribute_contract_count": len(ATTRIBUTE_CONTRACTS),
                "infrastructure_gap_count": self.infrastructure_gap_count,
            },
            "parameter_bridge": [dict(item) for item in self.parameter_bridge],
            "hypothesis_handoffs": [dict(item) for item in self.hypothesis_handoffs],
            "checks": [item.to_dict() for item in self.checks],
            "production_authority": self.production_authority,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "empirical_validation_executed": self.empirical_validation_executed,
            "field_labels_zh": {
                "parameter_bridge": "广义参数到V2参数本体的外键桥",
                "hypothesis_handoffs": "待实证公式假说到参数实验层的失败关闭交接",
                "source_digests": "跨轮权威输入与可执行目录摘要",
                "checks": "独立计算的基础设施验收检查",
                "infrastructure_gap_count": "由失败检查计算的基础设施缺口数",
            },
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _catalog_parameter_by_pair() -> dict[tuple[str, str], ToolParameterSpecV2]:
    catalog = build_tool_parameter_catalog_v2()
    return {(item.tool_id, item.parameter_id): item for item in catalog.parameters}


def _parameter_bridge(broad: pd.DataFrame) -> tuple[Mapping[str, object], ...]:
    required = {
        "tool_id",
        "parameter_id",
        "parameter_kind",
        "independently_adjustable",
        "evidence_level",
    }
    missing = required - set(broad)
    if missing:
        raise ValidationError(f"broad parameter table missing fields: {sorted(missing)}")
    catalog_by_pair = _catalog_parameter_by_pair()
    rows: list[Mapping[str, object]] = []
    for item in broad.to_dict(orient="records"):
        tool_id = str(item["tool_id"])
        parameter_id = str(item["parameter_id"])
        kind = str(item["parameter_kind"])
        parameter = catalog_by_pair.get((tool_id, parameter_id))
        allowed_effects = _BROAD_KIND_ALLOWED_EFFECTS.get(kind)
        status = "catalog_exact" if parameter is not None else "unresolved"
        identity_effect = None if parameter is None else parameter.identity_effect
        semantic_match = bool(parameter is not None and allowed_effects is not None and parameter.identity_effect in allowed_effects)
        rows.append(
            {
                "tool_id": tool_id,
                "broad_parameter_id": parameter_id,
                "canonical_parameter_id": parameter_id if parameter is not None else "",
                "parameter_kind": kind,
                "identity_effect": identity_effect or "",
                "registration_status": "" if parameter is None else parameter.registration_status,
                "tunable_status": "" if parameter is None else parameter.tunable_status,
                "mapping_status": status,
                "semantic_classification_match": semantic_match,
                "evidence_level": str(item["evidence_level"]),
            }
        )
    return tuple(sorted(rows, key=lambda row: (str(row["tool_id"]), str(row["broad_parameter_id"]))))


def _hypothesis_handoffs(
    hypotheses: pd.DataFrame,
    *,
    bridge: tuple[Mapping[str, object], ...],
    source_digests: Mapping[str, str],
) -> tuple[Mapping[str, object], ...]:
    bridge_by_pair = {(str(item["tool_id"]), str(item["broad_parameter_id"])): item for item in bridge}
    rows: list[Mapping[str, object]] = []
    for item in hypotheses.to_dict(orient="records"):
        tool_id = str(item["tool_id"])
        parameter_id = str(item["parameter_id"])
        mapped = bridge_by_pair.get((tool_id, parameter_id))
        if mapped is None:
            raise ValidationError(f"formula hypothesis lacks broad-parameter bridge: {tool_id}:{parameter_id}")
        identity_effect = str(mapped["identity_effect"])
        status = HANDOFF_STATUS_REGISTRATION_REQUIRED if identity_effect == "same_tool_parameter" else HANDOFF_STATUS_DIAGNOSTIC_ONLY
        parameter_axis_id = f"{tool_id}:parameter-axis:{parameter_id}"
        rows.append(
            {
                "hypothesis_id": str(item["hypothesis_id"]),
                "tool_id": tool_id,
                "canonical_parameter_id": str(mapped["canonical_parameter_id"]),
                "attribute_id": str(item["attribute_id"]),
                "parameter_axis_id": parameter_axis_id,
                "experiment_id": "",
                "factor_scale_id": "factor_120d",
                "parameter_vector_digest": "",
                "baseline_model_digest": "",
                "data_batch_digest": "",
                "tool_catalog_digest": source_digests["tool_parameter_catalog_v2"],
                "foundation_digest": source_digests["foundation_bundle.json"],
                "hypothesis_status": str(item["hypothesis_status"]),
                "handoff_status": status,
                "production_authority": False,
                "dynamic_parameter_authority": False,
                "tool_routing_authority": False,
            }
        )
    return tuple(sorted(rows, key=lambda row: str(row["hypothesis_id"])))


def build_cross_round_infrastructure(
    project_root: Path | str,
) -> CrossRoundInfrastructure:
    root = Path(project_root)
    foundation_dir = root / FOUNDATION_RELATIVE_DIR
    broad_path = foundation_dir / "broad_parameters.csv"
    links_path = foundation_dir / "parameter_attribute_links.csv"
    bundle_path = foundation_dir / "foundation_bundle.json"
    for path in (broad_path, links_path, bundle_path):
        if not path.is_file():
            raise ValidationError(f"cross-round authority input missing: {path}")

    broad = pd.read_csv(broad_path, dtype=str, keep_default_na=False)
    hypotheses = load_formula_hypotheses(links_path)
    catalog_payload = build_tool_parameter_catalog_v2().to_dict()
    time_payload = build_time_scale_catalog_v2().to_dict()
    ladder_payload = build_causal_scale_ladder_v2().to_dict()
    experiment_payload = build_tool_parameter_experiment_registry().to_dict()
    source_digests = {
        "foundation_bundle.json": _sha256(bundle_path),
        "broad_parameters.csv": _sha256(broad_path),
        "parameter_attribute_links.csv": _sha256(links_path),
        "src/factor_lab/market_state/tool_parameter_catalog_v2.py": _sha256(
            root / "src/factor_lab/market_state/tool_parameter_catalog_v2.py"
        ),
        "src/factor_lab/market_state/causal_scale_ladder.py": _sha256(root / "src/factor_lab/market_state/causal_scale_ladder.py"),
        "src/factor_lab/market_state/spectral_kline_attribute_measurement.py": _sha256(
            root / "src/factor_lab/market_state/spectral_kline_attribute_measurement.py"
        ),
        "src/factor_lab/market_state/tool_parameter_experiment_registry.py": _sha256(
            root / "src/factor_lab/market_state/tool_parameter_experiment_registry.py"
        ),
        "tool_parameter_catalog_v2": str(catalog_payload["semantic_digest"]),
        "time_scale_catalog_v2": str(time_payload["semantic_digest"]),
        "causal_scale_ladder_v2": str(ladder_payload["semantic_digest"]),
        "tool_parameter_experiment_registry": str(experiment_payload["semantic_digest"]),
        "attribute_contract_catalog": canonical_digest([item.to_dict() for item in ATTRIBUTE_CONTRACTS]),
    }
    bridge = _parameter_bridge(broad)
    handoffs = _hypothesis_handoffs(hypotheses, bridge=bridge, source_digests=source_digests)

    catalog_tools = {item.tool_id for item in build_tool_parameter_catalog_v2().parameters}
    bridge_pairs = {(str(item["tool_id"]), str(item["broad_parameter_id"])) for item in bridge}
    hypothesis_pairs = set(zip(hypotheses["tool_id"], hypotheses["parameter_id"], strict=True))
    applicable = all(
        str(row["tool_id"]) in ATTRIBUTE_CONTRACT_BY_ID[str(row["attribute_id"])].applicable_tools
        for row in hypotheses.to_dict(orient="records")
    )
    scale_binding = str(experiment_payload.get("scale_catalog_binding", ""))
    checks = (
        CrossRoundCheck(
            "all_13_tools_catalogued",
            catalog_tools == set(REQUIRED_TOOL_IDS),
            f"V2目录工具={len(catalog_tools)}，要求={len(REQUIRED_TOOL_IDS)}",
        ),
        CrossRoundCheck(
            "all_84_broad_parameters_mapped",
            len(bridge) == 84 and all(item["mapping_status"] == "catalog_exact" for item in bridge),
            f"广义参数={len(bridge)}，精确目录映射={sum(item['mapping_status'] == 'catalog_exact' for item in bridge)}",
        ),
        CrossRoundCheck(
            "broad_parameter_semantics_classified",
            all(bool(item["semantic_classification_match"]) for item in bridge),
            "每个广义参数类型必须与V2 identity_effect一致",
        ),
        CrossRoundCheck(
            "all_108_hypotheses_have_parameter_foreign_keys",
            len(hypotheses) == 108 and hypothesis_pairs <= bridge_pairs,
            f"公式假说={len(hypotheses)}，参数外键覆盖={len(hypothesis_pairs & bridge_pairs)}",
        ),
        CrossRoundCheck(
            "hypothesis_attribute_applicability_enforced",
            applicable,
            "108条假说的工具—属性组合必须满足属性合同",
        ),
        CrossRoundCheck(
            "all_hypotheses_pending_empirical_validation",
            set(hypotheses["hypothesis_status"]) == {HYPOTHESIS_STATUS},
            "公式假说不得越权升级",
        ),
        CrossRoundCheck(
            "experiment_registry_bound_to_time_scale_catalog",
            scale_binding not in {"", "pending_stage4_time_scale_catalog"},
            f"实验注册表尺度绑定={scale_binding or 'missing'}",
        ),
        CrossRoundCheck(
            "pending_handoff_is_fail_closed",
            all(
                str(item["handoff_status"]) in {HANDOFF_STATUS_REGISTRATION_REQUIRED, HANDOFF_STATUS_DIAGNOSTIC_ONLY}
                and not str(item["experiment_id"])
                and not bool(item["production_authority"])
                for item in handoffs
            ),
            "未注册实验的假说只能进入失败关闭交接层",
        ),
    )
    result = CrossRoundInfrastructure(
        registered_tool_ids=tuple(sorted(catalog_tools)),
        source_digests=source_digests,
        parameter_bridge=bridge,
        hypothesis_handoffs=handoffs,
        checks=checks,
    )
    validate_cross_round_infrastructure(result)
    return result


def validate_cross_round_infrastructure(
    infrastructure: CrossRoundInfrastructure | Mapping[str, object],
) -> None:
    payload = infrastructure.to_dict() if isinstance(infrastructure, CrossRoundInfrastructure) else dict(infrastructure)
    if payload.get("schema_id") != CROSS_ROUND_SCHEMA_ID:
        raise ValidationError("unexpected cross-round infrastructure schema")
    for field in (
        "production_authority",
        "dynamic_parameter_authority",
        "tool_routing_authority",
        "empirical_validation_executed",
    ):
        if bool(payload.get(field, True)):
            raise ValidationError(f"cross-round infrastructure cannot grant {field}")
    counts = cast(Mapping[str, object], payload.get("counts", {}))
    gap_count = int(str(counts.get("infrastructure_gap_count", -1)))
    checks = cast(list[Mapping[str, object]], payload.get("checks", []))
    calculated = sum(not bool(item.get("passed")) for item in checks)
    if gap_count != calculated:
        raise ValidationError("cross-round gap count must be calculated from checks")
    if gap_count:
        failed = [str(item.get("check_id")) for item in checks if not item.get("passed")]
        raise ValidationError(f"cross-round infrastructure gaps remain: {failed}")


def require_experiment_bound_handoff(handoff: Mapping[str, object]) -> None:
    """Block pending formula hypotheses from entering factor evidence or F2."""

    required = (
        "experiment_id",
        "factor_scale_id",
        "parameter_vector_digest",
        "baseline_model_digest",
        "data_batch_digest",
    )
    if handoff.get("handoff_status") != HANDOFF_STATUS_EXPERIMENT_BOUND:
        raise ValidationError("formula hypothesis is not bound to a registered experiment")
    missing = [field for field in required if not str(handoff.get(field, "")).strip()]
    if missing:
        raise ValidationError(f"experiment-bound handoff missing fields: {missing}")
    if handoff.get("hypothesis_status") != HYPOTHESIS_STATUS:
        raise ValidationError("experiment binding cannot upgrade empirical hypothesis status")


__all__ = [
    "CROSS_ROUND_SCHEMA_ID",
    "CROSS_ROUND_VERSION",
    "CrossRoundInfrastructure",
    "build_cross_round_infrastructure",
    "require_experiment_bound_handoff",
    "validate_cross_round_infrastructure",
]
