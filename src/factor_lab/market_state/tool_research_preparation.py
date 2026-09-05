"""Fail-closed preparation packets before tool-specific factor research.

This layer deliberately stops before an assistant selects a mechanism, a
coefficient/exponent form, a parameter vector, or an S/R residual explanation.
It makes the deterministic prerequisites for all frozen timing tools visible in
one place, while retaining older lane results as read-only diagnostic evidence.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.attributes_v1 import ATTRIBUTE_DEFINITIONS_V1
from factor_lab.market_state.causal_scale_ladder import build_causal_scale_ladder_v2
from factor_lab.market_state.cross_round_infrastructure import build_cross_round_infrastructure
from factor_lab.market_state.time_scale_catalog import build_time_scale_catalog_v2
from factor_lab.market_state.tool_capability_contracts import build_tool_capability_contract_bundle
from factor_lab.market_state.tool_factor_research_orchestrator import (
    LegacyLanePotentialProjection,
    build_tool_factor_research_orchestration,
)
from factor_lab.market_state.tool_formula_mechanisms import (
    FactorFormulaMapping,
    build_tool_formula_mechanism_bundle,
)
from factor_lab.market_state.tool_formula_surface_audit import build_formula_surface_audit_v2
from factor_lab.market_state.tool_parameter_catalog_v2 import build_tool_parameter_catalog_v2
from factor_lab.market_state.tool_parameter_experiment_registry import build_tool_parameter_experiment_registry
from factor_lab.market_state.tool_registry import REQUIRED_TOOL_IDS, tool_specs

TOOL_RESEARCH_PREPARATION_SCHEMA_ID: Final[str] = "market_state_tool_research_preparation@1.0"
TOOL_RESEARCH_PREPARATION_VERSION: Final[str] = "tool_research_preparation_v1"
PRE_COGNITIVE_STATUS: Final[str] = "ready_for_cognitive_design"
COGNITIVE_DESIGN_BOUNDARY: Final[str] = "select_mechanism_representation_and_register_experiment"
_SPECTRAL_MEASUREMENT_TOOLS: Final[frozenset[str]] = frozenset(
    {
        "laplace_iir_mixed_bandpass",
        "butterworth_clean_bandpass",
        "rolling_fourier_bandpass",
        "causal_haar_wavelet_bandpass",
    }
)
_SOURCE_FILES: Final[tuple[str, ...]] = (
    "src/factor_lab/market_state/attributes_v1.py",
    "src/factor_lab/market_state/causal_scale_ladder.py",
    "src/factor_lab/market_state/cross_round_infrastructure.py",
    "src/factor_lab/market_state/spectral_kline_attribute_measurement.py",
    "src/factor_lab/market_state/time_scale_catalog.py",
    "src/factor_lab/market_state/tool_capability_contracts.py",
    "src/factor_lab/market_state/tool_factor_research_orchestrator.py",
    "src/factor_lab/market_state/tool_formula_mechanisms.py",
    "src/factor_lab/market_state/tool_formula_surface_audit.py",
    "src/factor_lab/market_state/tool_parameter_catalog_v2.py",
    "src/factor_lab/market_state/tool_parameter_experiment_registry.py",
    "src/factor_lab/market_state/tool_research_preparation.py",
    "src/factor_lab/market_state/tool_registry.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(payload: Mapping[str, object]) -> str:
    return canonical_digest(dict(payload))


def _required_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field} must be an integer")
    return value


@dataclass(frozen=True, slots=True)
class ToolResearchPreparationPacket:
    """One tool's deterministic handoff to the cognitive-design boundary."""

    tool_id: str
    name_zh: str
    tool_category_id: str
    source_strategy_refs: tuple[str, ...]
    formula_id: str
    formula_mechanism_ids: tuple[str, ...]
    catalog_surface_ids: tuple[str, ...]
    same_tool_parameter_ids: tuple[str, ...]
    frozen_profile_ids: tuple[str, ...]
    carrier_frequencies: tuple[str, ...]
    generic_existing_factor_ids: tuple[str, ...]
    spectral_measurement_factor_ids: tuple[str, ...]
    formula_native_factor_ids: tuple[str, ...]
    legacy_lane_evidence: tuple[Mapping[str, object], ...]
    preparation_status: str = PRE_COGNITIVE_STATUS
    cognitive_design_boundary: str = COGNITIVE_DESIGN_BOUNDARY
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        if not self.tool_id or not self.name_zh or not self.formula_id:
            raise ValidationError("tool preparation identity is incomplete")
        if not self.source_strategy_refs or not self.formula_mechanism_ids:
            raise ValidationError("tool preparation requires formula provenance and mechanisms")
        if not self.catalog_surface_ids or not self.frozen_profile_ids or not self.carrier_frequencies:
            raise ValidationError("tool preparation is missing deterministic foundation coverage")
        if self.preparation_status != PRE_COGNITIVE_STATUS:
            raise ValidationError("tool preparation cannot claim an empirical or factor status")
        if self.cognitive_design_boundary != COGNITIVE_DESIGN_BOUNDARY:
            raise ValidationError("tool preparation cognitive boundary changed")
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("tool preparation cannot grant authority")
        if set(self.spectral_measurement_factor_ids) & set(self.formula_native_factor_ids):
            raise ValidationError("a formula-native factor cannot be both integrated and pending design")

    def to_dict(self) -> dict[str, object]:
        return {
            "tool_id": self.tool_id,
            "name_zh": self.name_zh,
            "tool_category_id": self.tool_category_id,
            "source_strategy_refs": list(self.source_strategy_refs),
            "formula_id": self.formula_id,
            "formula_mechanism_ids": list(self.formula_mechanism_ids),
            "catalog_surface_ids": list(self.catalog_surface_ids),
            "same_tool_parameter_ids": list(self.same_tool_parameter_ids),
            "frozen_profile_ids": list(self.frozen_profile_ids),
            "carrier_frequencies": list(self.carrier_frequencies),
            "generic_existing_factor_ids": list(self.generic_existing_factor_ids),
            "spectral_measurement_factor_ids": list(self.spectral_measurement_factor_ids),
            "formula_native_factor_ids": list(self.formula_native_factor_ids),
            "legacy_lane_evidence": [dict(item) for item in self.legacy_lane_evidence],
            "preparation_status": self.preparation_status,
            "cognitive_design_boundary": self.cognitive_design_boundary,
            "production_authority": self.production_authority,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "field_labels_zh": {
                "same_tool_parameter_ids": "可被正式预注册实验引用的同工具参数；当前未获实验权",
                "generic_existing_factor_ids": "已由通用严格因果K线属性层计算的公式候选属性",
                "spectral_measurement_factor_ids": "已接入频谱专用严格因果测量层的公式候选属性",
                "formula_native_factor_ids": "须由后续认知设计决定是否实现的公式原生属性，不是有效因子",
                "legacy_lane_evidence": "既有外部AI产物的只读证据定位，不提升其结论",
                "cognitive_design_boundary": "开始选择机制、表示、系数/指数形式和参数实验的位置",
            },
        }


@dataclass(frozen=True, slots=True)
class ToolResearchPreparationBundle:
    """Complete 13-tool preparation state, with no empirical research claim."""

    packets: tuple[ToolResearchPreparationPacket, ...]
    source_digests: Mapping[str, str]
    semantic_digests: Mapping[str, str]
    generic_attribute_ids: tuple[str, ...]
    generic_attribute_calculator: str
    cognitive_design_boundary: str = COGNITIVE_DESIGN_BOUNDARY
    registered_experiment_count: int = 0
    market_data_rows_read: int = 0
    empirical_validation_executed: bool = False
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        packet_ids = tuple(item.tool_id for item in self.packets)
        if packet_ids != REQUIRED_TOOL_IDS:
            raise ValidationError("preparation packet coverage differs from the frozen 13-tool universe")
        if self.cognitive_design_boundary != COGNITIVE_DESIGN_BOUNDARY:
            raise ValidationError("preparation bundle cognitive boundary changed")
        if self.registered_experiment_count != 0:
            raise ValidationError("pre-cognitive preparation cannot contain a parameter experiment")
        if self.market_data_rows_read != 0 or self.empirical_validation_executed:
            raise ValidationError("pre-cognitive preparation cannot perform empirical research")
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("pre-cognitive preparation cannot grant authority")
        if set(self.generic_attribute_ids) != {item.physical_attribute_id for item in ATTRIBUTE_DEFINITIONS_V1}:
            raise ValidationError("generic attribute preparation coverage drifted")
        if not self.source_digests or not self.semantic_digests:
            raise ValidationError("preparation bundle must bind source and semantic identities")

    @property
    def counts(self) -> dict[str, int]:
        return {
            "tool_count": len(self.packets),
            "formula_surface_count": sum(len(item.catalog_surface_ids) for item in self.packets),
            "frozen_profile_count": sum(len(item.frozen_profile_ids) for item in self.packets),
            "generic_attribute_count": len(self.generic_attribute_ids),
            "spectral_tool_count": sum(item.tool_id in _SPECTRAL_MEASUREMENT_TOOLS for item in self.packets),
            "legacy_evidence_tool_count": sum(bool(item.legacy_lane_evidence) for item in self.packets),
            "cognitive_design_required_tool_count": len(self.packets),
            "registered_experiment_count": self.registered_experiment_count,
        }

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": TOOL_RESEARCH_PREPARATION_SCHEMA_ID,
            "preparation_version": TOOL_RESEARCH_PREPARATION_VERSION,
            "counts": self.counts,
            "source_digests": dict(sorted(self.source_digests.items())),
            "semantic_digests": dict(sorted(self.semantic_digests.items())),
            "generic_attribute_ids": list(self.generic_attribute_ids),
            "generic_attribute_calculator": self.generic_attribute_calculator,
            "cognitive_design_boundary": self.cognitive_design_boundary,
            "cognitive_design_tasks": [
                "从公式候选中选择可证伪机制，而非无约束扫因子",
                "选择因子表示与系数/指数变体，并将同向单调别名合并计票",
                "登记明确参数候选、物理尺度、基线和多重性族",
                "仅在冻结基线下解释D、S和R残差，再决定是否开启F2",
            ],
            "packets": [item.to_dict() for item in self.packets],
            "registered_experiment_count": self.registered_experiment_count,
            "market_data_rows_read": self.market_data_rows_read,
            "empirical_validation_executed": self.empirical_validation_executed,
            "production_authority": self.production_authority,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "field_labels_zh": {
                "packets": "13个工具的统一前期研究准备包",
                "generic_attribute_ids": "通用严格因果K线属性目录",
                "registered_experiment_count": "本准备层登记的参数实验数，必须为零",
                "empirical_validation_executed": "是否已做因子有效性实证，准备层必须为否",
                "cognitive_design_tasks": "仅在此边界后由高认知研究助手承担的判断任务",
            },
        }
        payload["semantic_digest"] = _digest(payload)
        return payload


def _legacy_evidence_for(
    tool_id: str,
    projections: tuple[LegacyLanePotentialProjection, ...],
) -> tuple[Mapping[str, object], ...]:
    rows: list[Mapping[str, object]] = []
    for projection in projections:
        if tool_id not in projection.tool_ids:
            continue
        rows.append(
            {
                "lane_id": projection.lane_id,
                "source_handoff_relative_path": projection.source_handoff_relative_path,
                "source_handoff_sha256": projection.source_handoff_sha256,
                "truth_status": projection.truth_status,
                "migration_status": projection.migration_status,
                "potential_projection_status": projection.potential_projection_status,
                "f2_eligible": projection.f2_eligible,
            }
        )
    return tuple(sorted(rows, key=lambda item: str(item["lane_id"])))


def build_tool_research_preparation(project_root: Path | str) -> ToolResearchPreparationBundle:
    """Assemble every deterministic prerequisite without starting factor mining."""

    root = Path(project_root).resolve()
    catalog = build_tool_parameter_catalog_v2()
    formula_audit = build_formula_surface_audit_v2(root)
    formula_bundle = build_tool_formula_mechanism_bundle()
    capabilities = build_tool_capability_contract_bundle()
    time_scale_catalog = build_time_scale_catalog_v2()
    causal_scale_ladder = build_causal_scale_ladder_v2()
    experiment_registry = build_tool_parameter_experiment_registry()
    orchestration = build_tool_factor_research_orchestration(root)
    cross_round = build_cross_round_infrastructure(root)

    if formula_audit.audit_status != "passed":
        raise ValidationError("tool preparation requires a passed formula-surface audit")
    if tuple(item.tool_id for item in formula_bundle.tool_formulas) != REQUIRED_TOOL_IDS:
        raise ValidationError("formula bundle does not cover every frozen tool")
    if len(experiment_registry.experiments) != 0:
        raise ValidationError("tool preparation must begin before any experiment registration")

    formula_by_tool = {item.tool_id: item for item in formula_bundle.tool_formulas}
    mappings_by_mechanism: dict[str, list[FactorFormulaMapping]] = {}
    for mapping in formula_bundle.factor_mappings:
        mappings_by_mechanism.setdefault(mapping.mechanism_id, []).append(mapping)
    generic_ids = {item.physical_attribute_id for item in ATTRIBUTE_DEFINITIONS_V1}
    try:
        from factor_lab.market_state.spectral_kline_attribute_measurement import ATTRIBUTE_CONTRACT_BY_ID
    except ImportError as exc:  # pragma: no cover - imported package is project-local
        raise ValidationError("spectral measurement contract is unavailable") from exc

    packets: list[ToolResearchPreparationPacket] = []
    for spec in tool_specs():
        formula = formula_by_tool.get(spec.tool_id)
        if formula is None:
            raise ValidationError(f"missing formula preparation for {spec.tool_id}")
        relevant_mappings: tuple[FactorFormulaMapping, ...] = tuple(
            mapping for mechanism_id in formula.mechanism_ids for mapping in mappings_by_mechanism[mechanism_id]
        )
        existing = tuple(sorted({item.factor_id for item in relevant_mappings if item.factor_status == "existing"}))
        if not set(existing).issubset(generic_ids):
            raise ValidationError(f"formula mapping has an uncomputable existing factor: {spec.tool_id}")
        proposed = tuple(sorted({item.factor_id for item in relevant_mappings if item.factor_status == "proposed"}))
        spectral = tuple(
            factor_id
            for factor_id in proposed
            if spec.tool_id in _SPECTRAL_MEASUREMENT_TOOLS
            and factor_id in ATTRIBUTE_CONTRACT_BY_ID
            and spec.tool_id in ATTRIBUTE_CONTRACT_BY_ID[factor_id].applicable_tools
        )
        native = tuple(sorted(set(proposed) - set(spectral)))
        parameters = catalog.parameters_for(spec.tool_id)
        profiles = tuple(item for item in capabilities.profiles if item.tool_id == spec.tool_id)
        if not profiles:
            raise ValidationError(f"frozen profile coverage is missing: {spec.tool_id}")
        packets.append(
            ToolResearchPreparationPacket(
                tool_id=spec.tool_id,
                name_zh=spec.name_zh,
                tool_category_id=spec.tool_category_id,
                source_strategy_refs=spec.source_strategy_refs,
                formula_id=formula.formula_id,
                formula_mechanism_ids=tuple(sorted(formula.mechanism_ids)),
                catalog_surface_ids=tuple(sorted(item.parameter_id for item in parameters)),
                same_tool_parameter_ids=tuple(
                    sorted(item.parameter_id for item in parameters if item.identity_effect == "same_tool_parameter")
                ),
                frozen_profile_ids=tuple(sorted(item.profile_id for item in profiles)),
                carrier_frequencies=tuple(sorted({item.carrier_frequency for item in profiles})),
                generic_existing_factor_ids=existing,
                spectral_measurement_factor_ids=spectral,
                formula_native_factor_ids=native,
                legacy_lane_evidence=_legacy_evidence_for(spec.tool_id, orchestration.projections),
            )
        )

    source_digests = {relative_path: _sha256(root / relative_path) for relative_path in _SOURCE_FILES}
    capability_payload = capabilities.to_dict()
    semantic_digests = {
        "causal_scale_ladder": str(causal_scale_ladder.to_dict()["semantic_digest"]),
        "cross_round_infrastructure": str(cross_round.to_dict()["semantic_digest"]),
        "formula_mechanism_bundle": str(formula_bundle.to_dict()["semantic_digest"]),
        "formula_surface_audit": str(formula_audit.to_dict()["semantic_digest"]),
        "parameter_catalog": str(catalog.to_dict()["semantic_digest"]),
        "parameter_experiment_registry": str(experiment_registry.to_dict()["semantic_digest"]),
        "tool_capability_contract_bundle": canonical_digest(capability_payload),
        "tool_factor_research_orchestrator": str(orchestration.supervisor_handoff["semantic_digest"]),
        "time_scale_catalog": str(time_scale_catalog.to_dict()["semantic_digest"]),
    }
    bundle = ToolResearchPreparationBundle(
        packets=tuple(packets),
        source_digests=source_digests,
        semantic_digests=semantic_digests,
        generic_attribute_ids=tuple(sorted(generic_ids)),
        generic_attribute_calculator="src/factor_lab/market_state/attributes_v1.py:compute_market_attributes_v1",
        registered_experiment_count=len(experiment_registry.experiments),
    )
    validate_tool_research_preparation(bundle)
    return bundle


def validate_tool_research_preparation(bundle: ToolResearchPreparationBundle) -> None:
    """Reject accidental promotion of preparation evidence into research authority."""

    if bundle.counts["tool_count"] != len(REQUIRED_TOOL_IDS):
        raise ValidationError("preparation tool count is incomplete")
    if bundle.counts["formula_surface_count"] != 153:
        raise ValidationError("preparation formula surface count drifted")
    if bundle.counts["frozen_profile_count"] != 46:
        raise ValidationError("preparation frozen profile count drifted")
    if bundle.counts["generic_attribute_count"] != len(ATTRIBUTE_DEFINITIONS_V1):
        raise ValidationError("preparation generic attribute count drifted")
    if bundle.counts["registered_experiment_count"] != 0:
        raise ValidationError("preparation cannot include an experiment")
    for packet in bundle.packets:
        if packet.preparation_status != PRE_COGNITIVE_STATUS:
            raise ValidationError("preparation packet was promoted beyond the cognitive boundary")
        if any(item.get("f2_eligible") is not False for item in packet.legacy_lane_evidence):
            raise ValidationError("legacy evidence cannot open F2 from the preparation layer")


def validate_tool_research_preparation_payload(payload: Mapping[str, object]) -> None:
    """Check serialized integrity and no-authority claims for persisted artifacts."""

    if payload.get("schema_id") != TOOL_RESEARCH_PREPARATION_SCHEMA_ID:
        raise ValidationError("tool preparation schema id changed")
    if payload.get("preparation_version") != TOOL_RESEARCH_PREPARATION_VERSION:
        raise ValidationError("tool preparation version changed")
    digest_payload = dict(payload)
    digest = digest_payload.pop("semantic_digest", None)
    if digest != _digest(digest_payload):
        raise ValidationError("tool preparation semantic digest is invalid")
    raw_counts = payload.get("counts")
    raw_packets = payload.get("packets")
    if not isinstance(raw_counts, Mapping) or not isinstance(raw_packets, list):
        raise ValidationError("tool preparation payload is malformed")
    counts = cast(Mapping[str, object], raw_counts)
    raw_packet_items = cast(list[object], raw_packets)
    if not all(isinstance(item, Mapping) for item in raw_packet_items):
        raise ValidationError("tool preparation packet is not an object")
    packets = tuple(cast(Mapping[str, object], item) for item in raw_packet_items)
    if _required_int(counts.get("tool_count"), field="tool_count") != len(REQUIRED_TOOL_IDS) or len(packets) != len(REQUIRED_TOOL_IDS):
        raise ValidationError("tool preparation payload has incomplete tool coverage")
    if (
        _required_int(
            counts.get("registered_experiment_count"),
            field="registered_experiment_count",
        )
        != 0
        or payload.get("registered_experiment_count") != 0
    ):
        raise ValidationError("tool preparation payload cannot contain an experiment")
    if payload.get("market_data_rows_read") != 0 or payload.get("empirical_validation_executed") is not False:
        raise ValidationError("tool preparation payload cannot claim empirical work")
    if any(payload.get(key) is not False for key in ("production_authority", "dynamic_parameter_authority", "tool_routing_authority")):
        raise ValidationError("tool preparation payload cannot grant authority")
    packet_ids = tuple(str(item.get("tool_id", "")) for item in packets)
    if packet_ids != REQUIRED_TOOL_IDS:
        raise ValidationError("tool preparation payload order or coverage drifted")
    for packet in packets:
        if packet.get("preparation_status") != PRE_COGNITIVE_STATUS:
            raise ValidationError("tool preparation packet was promoted beyond readiness")
        if packet.get("cognitive_design_boundary") != COGNITIVE_DESIGN_BOUNDARY:
            raise ValidationError("tool preparation packet cognitive boundary changed")
        if any(packet.get(key) is not False for key in ("production_authority", "dynamic_parameter_authority", "tool_routing_authority")):
            raise ValidationError("tool preparation packet cannot grant authority")


def write_tool_research_preparation(
    *,
    project_root: Path | str,
    output_dir: Path | str,
) -> ToolResearchPreparationBundle:
    """Persist a deterministic preparation contract and its data-isolation ledger."""

    bundle = build_tool_research_preparation(project_root)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    payload = bundle.to_dict()
    _ = (root / "tool_research_preparation.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    ledger = {
        "schema_id": "market_state_tool_research_preparation_data_usage@1.0",
        "market_data_rows_read": 0,
        "post_2020_rows_read": 0,
        "blackbox_detail_opened": False,
        "empirical_validation_executed": False,
        "source_kind": "contracts_formula_audits_and_readonly_legacy_handoffs",
    }
    _ = (root / "data_usage_ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifacts = ("tool_research_preparation.json", "data_usage_ledger.json")
    manifest: dict[str, object] = {
        "schema_id": "market_state_tool_research_preparation_manifest@1.0",
        "contract_semantic_digest": payload["semantic_digest"],
        "source_digests": payload["source_digests"],
        "artifacts": [
            {
                "path": name,
                "sha256": _sha256(root / name),
                "bytes": (root / name).stat().st_size,
            }
            for name in artifacts
        ],
        "production_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
    }
    manifest["manifest_semantic_digest"] = canonical_digest(manifest)
    _ = (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return bundle


__all__ = [
    "COGNITIVE_DESIGN_BOUNDARY",
    "PRE_COGNITIVE_STATUS",
    "TOOL_RESEARCH_PREPARATION_SCHEMA_ID",
    "TOOL_RESEARCH_PREPARATION_VERSION",
    "ToolResearchPreparationBundle",
    "ToolResearchPreparationPacket",
    "build_tool_research_preparation",
    "validate_tool_research_preparation",
    "validate_tool_research_preparation_payload",
    "write_tool_research_preparation",
]
