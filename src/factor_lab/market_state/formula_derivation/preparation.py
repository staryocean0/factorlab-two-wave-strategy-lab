"""Thirteen-tool Stage-1 orchestration, V1 adapter, persistence, and validation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from factor_lab.candidate_assets.services.candidate_asset_service import (
    CandidateAssetService,
)
from factor_lab.core.errors import ValidationError
from factor_lab.factor_engine.base_factor_catalog import (
    BASE_FACTOR_UNIVERSE_VERSION,
    list_base_factor_definitions,
)
from factor_lab.factor_engine.models.factor_spec import FactorSpec
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.governance.search_scope_registry import register_search_scope_run
from factor_lab.governance.temporal_governance_repository import (
    TemporalGovernanceRepository,
)
from factor_lab.market_state.formula_derivation.families import (
    FORMULA_FAMILY_COUNTS,
    TOOL_FAMILY_MEMBERS,
    RepresentativeFormulaDerivation,
    build_formula_derivation_for_tool,
)
from factor_lab.market_state.formula_derivation.validation import (
    require_digest,
    validate_formula_derivation_package,
    validate_semantic_digest,
)
from factor_lab.market_state.joint_policy_attempt_registry import (
    validate_joint_policy_attempt_manifest,
)
from factor_lab.market_state.joint_policy_family_registry import (
    JointPolicyFamily,
    validate_joint_policy_family,
)
from factor_lab.market_state.tool_formula_mechanisms import (
    build_tool_formula_mechanism_bundle,
)
from factor_lab.market_state.tool_research_preparation import (
    validate_tool_research_preparation_payload,
)

FORMULA_DERIVATION_PREPARATION_SCHEMA_ID: Final[str] = "market_state_formula_derivation_preparation@1.1"
FORMULA_DERIVATION_PREPARATION_VERSION: Final[str] = "formula_derivation_preparation_v1"
FORMULA_DERIVATION_SEARCH_SCOPE_RUN_ID: Final[str] = "thirteen-tools-zero-data-registration-v8"
EXPECTED_V1_PREPARATION_SEMANTIC_DIGEST: Final[str] = (
    "sha256:0ea7dcda15b7f32b3cb64c3d1edbbfe9df051d12a92f3b7161ce668e729f9721"
)
FROZEN_V1_PREPARATION_RELATIVE_PATH: Final[Path] = (
    Path("output/market-state-foundation/infrastructure-v2/pre-cognitive-preparation")
    / "tool_research_preparation.json"
)
EXPECTED_V1_PREPARATION_FILE_SHA256: Final[str] = (
    "sha256:bbfbfd3b5ac298b3fa3f900a6295744fb616bf34ad2b3ac9c57068eaa4916a65"
)
_PREPARATION_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_id",
        "preparation_version",
        "v1_preparation_ref",
        "counts",
        "tools",
        "registration_ledger",
        "data_usage_ledger",
        "production_authority",
        "dynamic_parameter_authority",
        "tool_routing_authority",
        "field_labels_zh",
        "semantic_digest",
    }
)
_TOOL_ROW_KEYS: Final[frozenset[str]] = frozenset(
    {
        "formula_family_id",
        "family_tool_count",
        "tool_id",
        "factor_pool_version",
        "factor_pool_query_digest",
        "registered_factor_specs",
        "formula_derivation_package",
        "joint_policy_family",
        "registered_policy_attempt_manifest",
        "production_authority",
        "dynamic_parameter_authority",
        "tool_routing_authority",
        "field_labels_zh",
        "semantic_digest",
    }
)
_FACTOR_SPEC_KEYS: Final[frozenset[str]] = frozenset(
    {
        "spec_id",
        "spec_version",
        "factor_spec_version",
        "name",
        "description",
        "factor_type",
        "callable_ref",
        "dsl_expression",
        "materialized_frame_ref",
        "value_column",
        "preprocess_spec_version",
        "input_schema",
        "output_schema",
        "parameters",
        "source_family",
        "source_refs",
        "input_field_lineage",
        "dsl_ast_version",
        "operator_set_version",
        "expression_hash",
        "complexity_score",
        "field_refs",
        "window_refs",
        "nan_policy",
        "normalized_ast",
        "operator_list",
        "tags",
        "feature_refs",
    }
)
_EXPECTED_FACTOR_SPEC_TAGS: Final[Mapping[str, str]] = {
    "library": "internal_market_state_research",
    "lifecycle_state": "ResearchFactor",
    "evidence_level": "structural_dependency",
    "effectiveness": "not_strategy_validated",
    "production_authority": "false",
}
_PREPARATION_MANIFEST_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_id", "contract_semantic_digest", "counts", "artifacts",
        "production_authority", "dynamic_parameter_authority",
        "tool_routing_authority", "manifest_semantic_digest",
    }
)
_PREPARATION_ARTIFACT_KEYS: Final[frozenset[str]] = frozenset(
    {"relative_path", "sha256", "bytes"}
)


@dataclass(frozen=True, slots=True)
class FormulaDerivationPreparation:
    """All 13 deterministic Stage-1 derivations plus their V1 read-only parent."""

    derivations: tuple[RepresentativeFormulaDerivation, ...]
    v1_preparation_semantic_digest: str
    v1_packet_count: int
    registration_ledger: Mapping[str, object]
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        expected = {tool_id: family_id for family_id, tool_ids in TOOL_FAMILY_MEMBERS.items() for tool_id in tool_ids}
        actual = {item.source_formula.tool_id: item.formula_family_id for item in self.derivations}
        if actual != expected or len(self.derivations) != 13:
            raise ValidationError("formula derivation preparation must cover 13 tools exactly once")
        if (
            self.v1_packet_count != 13
            or self.v1_preparation_semantic_digest != EXPECTED_V1_PREPARATION_SEMANTIC_DIGEST
        ):
            raise ValidationError("formula derivation preparation lost its V1 parent")
        if (
            self.registration_ledger.get("factor_spec_count") != 30
            or self.registration_ledger.get("candidate_asset_count") != 30
            or self.registration_ledger.get("search_scope_status") != "registered"
            or self.registration_ledger.get("search_scope_run_id") != FORMULA_DERIVATION_SEARCH_SCOPE_RUN_ID
        ):
            raise ValidationError("formula derivation registration chain is incomplete")
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("formula derivation preparation cannot grant authority")

    @property
    def counts(self) -> dict[str, object]:
        return {
            "tool_count": len(self.derivations),
            "formula_family_counts": dict(FORMULA_FAMILY_COUNTS),
            "formula_graph_count": len(self.derivations),
            "formula_native_attribute_count": sum(len(item.package.formula_native_attributes) for item in self.derivations),
            "registered_factor_spec_count": sum(len(item.registered_factor_specs) for item in self.derivations),
            "candidate_asset_count": self.registration_ledger["candidate_asset_count"],
            "joint_policy_family_count": len(self.derivations),
            "raw_policy_coordinate_count": sum(
                item.joint_policy_family.complexity_budget.complete_attempt_count for item in self.derivations
            ),
            "algebraic_alias_collapse_count": sum(
                item.joint_policy_family.complexity_budget.complete_attempt_count - item.joint_policy_family.registered_policy_attempt_count
                for item in self.derivations
            ),
            "registered_whole_policy_attempt_count": sum(
                item.joint_policy_family.registered_policy_attempt_count for item in self.derivations
            ),
        }

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": FORMULA_DERIVATION_PREPARATION_SCHEMA_ID,
            "preparation_version": FORMULA_DERIVATION_PREPARATION_VERSION,
            "v1_preparation_ref": {
                "schema_id": "market_state_tool_research_preparation@1.0",
                "semantic_digest": self.v1_preparation_semantic_digest,
                "packet_count": self.v1_packet_count,
                "migration_policy": "read_only_no_promotion",
            },
            "counts": self.counts,
            "tools": [item.to_dict() for item in self.derivations],
            "registration_ledger": dict(self.registration_ledger),
            "data_usage_ledger": {
                "market_data_rows_read": 0,
                "return_rows_read": 0,
                "post_2020_rows_read": 0,
                "post_2020_rows_used": 0,
                "sealed_interval": "2021-01-01/2026-12-31",
                "blackbox_detail_opened": False,
                "empirical_validation_executed": False,
            },
            "production_authority": self.production_authority,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "field_labels_zh": {
                "v1_preparation_ref": "V1准备包只读父引用",
                "counts": "13工具公式派生计数",
                "tools": "逐工具公式派生与联合家族",
                "registration_ledger": "FactorSpec、CandidateAsset与SearchScope注册链",
                "data_usage_ledger": "数据使用台账",
                "production_authority": "生产权限",
                "dynamic_parameter_authority": "动态参数权限",
                "tool_routing_authority": "工具路由权限",
            },
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload


def build_formula_derivation_preparation(
    project_root: Path | str,
) -> FormulaDerivationPreparation:
    """Build V3 from frozen registries while retaining the V1 parent digest."""

    derivations, v1 = _derive_formula_preparation_components(
        project_root,
        persist_factor_registration=True,
    )
    registration_ledger = _register_formula_factor_infrastructure(derivations)
    preparation = FormulaDerivationPreparation(
        derivations=derivations,
        v1_preparation_semantic_digest=EXPECTED_V1_PREPARATION_SEMANTIC_DIGEST,
        v1_packet_count=int(str(cast(Mapping[str, object], v1["counts"])["tool_count"])),
        registration_ledger=registration_ledger,
    )
    validate_formula_derivation_preparation_payload(preparation.to_dict())
    return preparation


def rebuild_formula_derivation_preparation_read_only(
    project_root: Path | str,
) -> FormulaDerivationPreparation:
    """Reconstruct Stage 1 without registry lookup, registration, or filesystem writes."""

    derivations, v1 = _derive_formula_preparation_components(
        project_root,
        persist_factor_registration=False,
    )
    preparation = FormulaDerivationPreparation(
        derivations=derivations,
        v1_preparation_semantic_digest=EXPECTED_V1_PREPARATION_SEMANTIC_DIGEST,
        v1_packet_count=int(str(cast(Mapping[str, object], v1["counts"])["tool_count"])),
        registration_ledger=_expected_formula_factor_infrastructure(derivations),
    )
    validate_formula_derivation_preparation_payload(preparation.to_dict())
    return preparation


def _derive_formula_preparation_components(
    project_root: Path | str,
    *,
    persist_factor_registration: bool,
) -> tuple[tuple[RepresentativeFormulaDerivation, ...], Mapping[str, object]]:
    """Rebuild deterministic Stage-1 objects without touching durable registries."""

    root = Path(project_root).resolve()
    v1 = _load_frozen_v1_parent(root)
    formulas = {item.tool_id: item for item in build_tool_formula_mechanism_bundle().tool_formulas}
    derivations = tuple(
        build_formula_derivation_for_tool(
            formulas[tool_id],
            formula_family_id=family_id,
            persist_factor_registration=persist_factor_registration,
        )
        for family_id, tool_ids in TOOL_FAMILY_MEMBERS.items()
        for tool_id in tool_ids
    )
    return derivations, v1


def validate_formula_derivation_preparation_payload(
    payload: Mapping[str, object],
) -> None:
    """Validate counts, nested contracts, data isolation, digest, and authorities."""

    if payload.get("schema_id") != FORMULA_DERIVATION_PREPARATION_SCHEMA_ID:
        raise ValidationError("formula derivation preparation schema changed")
    if payload.get("preparation_version") != FORMULA_DERIVATION_PREPARATION_VERSION:
        raise ValidationError("formula derivation preparation version changed")
    if set(payload) != set(_PREPARATION_PAYLOAD_KEYS):
        raise ValidationError("formula derivation preparation fields changed")
    validate_semantic_digest(payload)
    _reject_non_false_authority(payload)
    if any(
        payload.get(field) is not False
        for field in (
            "production_authority",
            "dynamic_parameter_authority",
            "tool_routing_authority",
        )
    ):
        raise ValidationError("formula derivation preparation authority changed")
    ledger = _mapping(payload, "data_usage_ledger")
    expected_ledger = {
        "market_data_rows_read": 0,
        "return_rows_read": 0,
        "post_2020_rows_read": 0,
        "post_2020_rows_used": 0,
        "sealed_interval": "2021-01-01/2026-12-31",
        "blackbox_detail_opened": False,
        "empirical_validation_executed": False,
    }
    if dict(ledger) != expected_ledger:
        raise ValidationError("formula derivation preparation data ledger changed")
    raw_tools = payload.get("tools")
    if not isinstance(raw_tools, list):
        raise ValidationError("formula derivation preparation tool coverage is incomplete")
    tools = cast(list[object], raw_tools)
    if len(tools) != 13:
        raise ValidationError("formula derivation preparation tool coverage is incomplete")
    tool_ids: set[str] = set()
    family_counts: dict[str, int] = {}
    total_attempts = 0
    for raw in tools:
        if not isinstance(raw, Mapping):
            raise ValidationError("formula derivation preparation tool row is invalid")
        row = cast(Mapping[str, object], raw)
        if set(row) != set(_TOOL_ROW_KEYS):
            raise ValidationError("formula derivation preparation tool row fields changed")
        validate_semantic_digest(row)
        tool_id = str(row.get("tool_id", ""))
        family_id = str(row.get("formula_family_id", ""))
        if tool_id not in TOOL_FAMILY_MEMBERS.get(family_id, ()) or tool_id in tool_ids:
            raise ValidationError("formula derivation preparation family mapping is invalid")
        tool_ids.add(tool_id)
        family_counts[family_id] = family_counts.get(family_id, 0) + 1
        package = _mapping(row, "formula_derivation_package")
        family = _mapping(row, "joint_policy_family")
        attempt_manifest = _mapping(row, "registered_policy_attempt_manifest")
        validate_formula_derivation_package(package)
        validate_joint_policy_family(family)
        validate_joint_policy_attempt_manifest(
            attempt_manifest,
            family=JointPolicyFamily.from_dict(family),
        )
        registrations = row.get("registered_factor_specs")
        if not isinstance(registrations, list) or not cast(list[object], registrations):
            raise ValidationError("formula derivation preparation has an unregistered attribute")
        registration_rows = cast(list[object], registrations)
        registered_ids: set[str] = set()
        for raw_spec in registration_rows:
            if not isinstance(raw_spec, Mapping):
                raise ValidationError("formula derivation preparation FactorSpec fields changed")
            spec = cast(Mapping[str, object], raw_spec)
            if set(spec) != set(_FACTOR_SPEC_KEYS):
                raise ValidationError("formula derivation preparation FactorSpec fields changed")
            spec_id = str(spec.get("spec_id", ""))
            if not spec_id or spec.get("spec_version") != spec_id or spec.get("factor_spec_version") != spec_id:
                raise ValidationError("formula derivation preparation FactorSpec identity changed")
            tags = _mapping(spec, "tags")
            if dict(tags) != dict(_EXPECTED_FACTOR_SPEC_TAGS):
                raise ValidationError("formula derivation preparation FactorSpec tags changed")
            registered_ids.add(spec_id)
        attributes = package.get("formula_native_attributes")
        if not isinstance(attributes, list):
            raise ValidationError("formula derivation preparation attributes are missing")
        attribute_rows = cast(list[object], attributes)
        attribute_formulas = [
            str(cast(Mapping[str, object], item).get("causal_formula", ""))
            for item in attribute_rows
            if isinstance(item, Mapping)
        ]
        expected_query_digest = canonical_digest(
            {
                "base_factor_universe_version": BASE_FACTOR_UNIVERSE_VERSION,
                "existing_definitions": tuple(
                    sorted(
                        (
                            definition.factor_id,
                            definition.dsl_expression,
                            definition.required_fields,
                        )
                        for definition in list_base_factor_definitions()
                    )
                ),
                "requested_formulas": attribute_formulas,
            }
        )
        source_digests = _mapping(package, "source_artifact_digests")
        graph = _mapping(package, "graph")
        source_formula = _mapping(graph, "source_formula_contract")
        if (
            row.get("factor_pool_version") != BASE_FACTOR_UNIVERSE_VERSION
            or row.get("factor_pool_query_digest") != expected_query_digest
            or source_digests.get("base_factor_universe_query") != expected_query_digest
            or source_digests.get("tool_formula_spec") != canonical_digest(source_formula)
        ):
            raise ValidationError("formula derivation preparation factor-pool/source binding changed")
        spec_by_id = {
            str(cast(Mapping[str, object], item).get("spec_id", "")): cast(Mapping[str, object], item)
            for item in registration_rows
            if isinstance(item, Mapping)
        }
        expected_ids: set[str] = set()
        for raw_attribute in attribute_rows:
            if not isinstance(raw_attribute, Mapping):
                raise ValidationError("formula derivation preparation attribute row is invalid")
            attribute = cast(Mapping[str, object], raw_attribute)
            if attribute.get("factor_registration_status") != "blocked":
                factor_spec_id = str(attribute.get("factor_spec_id", ""))
                expected_ids.add(factor_spec_id)
                spec = spec_by_id.get(factor_spec_id)
                if spec is None or dict(spec) != _expected_factor_spec(
                    tool_id=tool_id,
                    source_formula=source_formula,
                    attribute=attribute,
                    factor_pool_query_digest=expected_query_digest,
                ):
                    raise ValidationError("formula derivation preparation FactorSpec semantics changed")
        if registered_ids != expected_ids or len(registered_ids) != len(registration_rows):
            raise ValidationError("formula derivation preparation FactorSpecs do not bind the attributes")
        total_attempts += int(str(family["registered_policy_attempt_count"]))
    if family_counts != FORMULA_FAMILY_COUNTS:
        raise ValidationError("formula derivation preparation 4/3/2/2/2 counts changed")
    counts = _mapping(payload, "counts")
    if (
        counts.get("tool_count") != 13
        or counts.get("formula_graph_count") != 13
        or counts.get("joint_policy_family_count") != 13
        or counts.get("raw_policy_coordinate_count") != 10800
        or counts.get("algebraic_alias_collapse_count") != 1368
        or counts.get("registered_whole_policy_attempt_count") != total_attempts
        or counts.get("candidate_asset_count") != 30
    ):
        raise ValidationError("formula derivation preparation summary does not reconcile")
    v1_ref = _mapping(payload, "v1_preparation_ref")
    if set(v1_ref) != {"schema_id", "semantic_digest", "packet_count", "migration_policy"}:
        raise ValidationError("formula derivation preparation V1 adapter fields changed")
    if (
        v1_ref.get("schema_id") != "market_state_tool_research_preparation@1.0"
        or v1_ref.get("semantic_digest") != EXPECTED_V1_PREPARATION_SEMANTIC_DIGEST
        or v1_ref.get("packet_count") != 13
        or v1_ref.get("migration_policy") != "read_only_no_promotion"
    ):
        raise ValidationError("formula derivation preparation V1 adapter changed")
    registration = _mapping(payload, "registration_ledger")
    if (
        registration.get("factor_spec_count") != 30
        or registration.get("candidate_asset_count") != 30
        or registration.get("search_scope_status") != "registered"
        or registration.get("search_scope_run_id") != FORMULA_DERIVATION_SEARCH_SCOPE_RUN_ID
        or len(cast(list[object], registration.get("factor_spec_versions", []))) != 30
        or len(cast(list[object], registration.get("candidate_asset_ids", []))) != 30
    ):
        raise ValidationError("formula derivation registration ledger is incomplete")


def _register_formula_factor_infrastructure(
    derivations: tuple[RepresentativeFormulaDerivation, ...],
) -> dict[str, object]:
    """Resolve FactorSpecs, CandidateAssets, and one zero-data SearchScope."""

    specs = tuple(spec for derivation in derivations for spec in derivation.registered_factor_specs)
    if len(specs) != 30 or len({spec.spec_version for spec in specs}) != 30:
        raise ValidationError("formula-native FactorSpec registration count changed")
    service = CandidateAssetService()
    candidate_ids: list[str] = []
    for spec in specs:
        resolved = service.upsert_candidate_from_spec(
            spec=spec.to_dict(),
            source_family="price_volume",
            source_refs=list(spec.source_refs),
            source_run_id="market-state-formula-derived-v3-stage1",
            candidate_batch_id="market-state-formula-derived-v3-zero-data",
            created_by="market_state_formula_derivation_preparation",
            pool_status="discovered",
            screening={
                "latest_discovery_score": 0.0,
                "formula_only_no_market_rows": True,
            },
        )
        candidate_id = str(resolved.get("candidate_factor_id", ""))
        if not candidate_id or resolved.get("factor_spec_version") != spec.spec_version:
            raise ValidationError("formula-native CandidateAsset registration failed")
        candidate_ids.append(candidate_id)
    search_space_hash = canonical_digest(
        {
            "factor_spec_digests": [canonical_digest(spec.to_dict()) for spec in specs],
            "registered_policy_attempt_manifest_digests": [
                require_digest(
                    derivation.registered_policy_attempt_manifest.get("semantic_digest"),
                    field="registered policy attempt manifest digest",
                )
                for derivation in derivations
            ],
        }
    )
    search = register_search_scope_run(
        TemporalGovernanceRepository(),
        campaign_id="market-state-formula-derived-v3-stage1",
        run_id=FORMULA_DERIVATION_SEARCH_SCOPE_RUN_ID,
        candidate_count=len(specs),
        parameter_config_count=1,
        protocol_count=1,
        attempted_evaluation_count=len(specs),
        dataset_ref="formula-only://no-market-data",
        window_ref="no-market-rows",
        search_space_hash=search_space_hash,
        metadata={
            "stage": 1,
            "market_data_rows_read": 0,
            "return_rows_read": 0,
            "production_authority": False,
        },
    )
    if search.get("status") not in {"created", "existing", "registered", "idempotent"}:
        raise ValidationError("formula-native SearchScope registration failed")
    return {
        "registration_chain": "FactorSpec->CandidateAsset->SearchScope",
        "factor_spec_count": len(specs),
        "factor_spec_versions": sorted(spec.spec_version for spec in specs),
        "candidate_asset_count": len(candidate_ids),
        "candidate_asset_ids": sorted(candidate_ids),
        "search_scope_status": "registered",
        "search_scope_run_id": FORMULA_DERIVATION_SEARCH_SCOPE_RUN_ID,
        "search_space_hash": search_space_hash,
        "market_data_rows_read": 0,
        "return_rows_read": 0,
        "production_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
    }


def _expected_formula_factor_infrastructure(
    derivations: tuple[RepresentativeFormulaDerivation, ...],
) -> dict[str, object]:
    """Reconstruct the registration ledger without performing any upsert."""

    specs = tuple(spec for derivation in derivations for spec in derivation.registered_factor_specs)
    if len(specs) != 30 or len({spec.spec_version for spec in specs}) != 30:
        raise ValidationError("formula-native FactorSpec registration count changed")
    service = CandidateAssetService()
    identities = tuple(
        service.candidate_identity_from_spec(
            spec=spec.to_dict(),
            source_family="price_volume",
        )
        for spec in specs
    )
    search_space_hash = canonical_digest(
        {
            "factor_spec_digests": [canonical_digest(spec.to_dict()) for spec in specs],
            "registered_policy_attempt_manifest_digests": [
                require_digest(
                    derivation.registered_policy_attempt_manifest.get("semantic_digest"),
                    field="registered policy attempt manifest digest",
                )
                for derivation in derivations
            ],
        }
    )
    return {
        "registration_chain": "FactorSpec->CandidateAsset->SearchScope",
        "factor_spec_count": len(specs),
        "factor_spec_versions": sorted(spec.spec_version for spec in specs),
        "candidate_asset_count": len(identities),
        "candidate_asset_ids": sorted(item["candidate_factor_id"] for item in identities),
        "search_scope_status": "registered",
        "search_scope_run_id": FORMULA_DERIVATION_SEARCH_SCOPE_RUN_ID,
        "search_space_hash": search_space_hash,
        "market_data_rows_read": 0,
        "return_rows_read": 0,
        "production_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
    }


def write_formula_derivation_preparation(
    *,
    project_root: Path | str,
    output_dir: Path | str,
) -> dict[str, object]:
    """Persist deterministic per-tool packages and a hash-bound manifest."""

    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    preparation = build_formula_derivation_preparation(project_root)
    artifacts: list[dict[str, object]] = []
    for item in preparation.derivations:
        tool_root = root / "tools" / item.source_formula.tool_id
        tool_root.mkdir(parents=True, exist_ok=True)
        payloads = {
            "formula_derivation_package.json": item.package.to_dict(),
            "joint_policy_family.json": item.joint_policy_family.to_dict(),
            "joint_policy_attempt_manifest.json": dict(item.registered_policy_attempt_manifest),
            "factor_registration_snapshot.json": {
                "tool_id": item.source_formula.tool_id,
                "factor_pool_version": item.factor_pool_version,
                "factor_pool_query_digest": item.factor_pool_query_digest,
                "registered_factor_specs": [spec.to_dict() for spec in item.registered_factor_specs],
                "production_authority": False,
            },
        }
        for name, payload in payloads.items():
            path = tool_root / name
            _write_json(path, payload)
            artifacts.append(_artifact(root, path))
    preparation_payload = preparation.to_dict()
    _write_json(root / "formula_derivation_preparation.json", preparation_payload)
    _write_json(
        root / "data_usage_ledger.json",
        cast(dict[str, object], preparation_payload["data_usage_ledger"]),
    )
    artifacts.extend(
        (
            _artifact(root, root / "formula_derivation_preparation.json"),
            _artifact(root, root / "data_usage_ledger.json"),
        )
    )
    manifest: dict[str, object] = {
        "schema_id": "market_state_formula_derivation_preparation_manifest@1.0",
        "contract_semantic_digest": preparation_payload["semantic_digest"],
        "counts": preparation.counts,
        "artifacts": sorted(artifacts, key=lambda item: str(item["relative_path"])),
        "production_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
    }
    manifest["manifest_semantic_digest"] = canonical_digest(manifest)
    _write_json(root / "manifest.json", manifest)
    return manifest


def validate_persisted_formula_derivation_preparation(
    *,
    project_root: Path | str,
    output_dir: Path | str,
) -> dict[str, object]:
    """Independently rebuild and verify every persisted Stage-1 artifact."""

    root = Path(output_dir).resolve()
    manifest = _load_json(root / "manifest.json")
    if set(manifest) != set(_PREPARATION_MANIFEST_KEYS):
        raise ValidationError("formula derivation preparation manifest fields changed")
    if manifest.get("schema_id") != "market_state_formula_derivation_preparation_manifest@1.0":
        raise ValidationError("formula derivation preparation manifest schema changed")
    manifest_body = dict(manifest)
    manifest_digest = manifest_body.pop("manifest_semantic_digest", None)
    if manifest_digest != canonical_digest(manifest_body):
        raise ValidationError("formula derivation preparation manifest digest is invalid")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValidationError("formula derivation preparation artifact inventory is missing")
    artifact_paths: set[str] = set()
    for raw in cast(list[object], artifacts):
        if not isinstance(raw, Mapping):
            raise ValidationError("formula derivation preparation artifact row is invalid")
        row = cast(Mapping[str, object], raw)
        if set(row) != set(_PREPARATION_ARTIFACT_KEYS):
            raise ValidationError("formula derivation preparation artifact fields changed")
        relative_path = str(row.get("relative_path", ""))
        path = (root / relative_path).resolve()
        if not path.is_relative_to(root) or relative_path in artifact_paths:
            raise ValidationError("formula derivation preparation artifact path is invalid")
        artifact_paths.add(relative_path)
        if _sha256(path) != row.get("sha256") or path.stat().st_size != row.get("bytes"):
            raise ValidationError("formula derivation preparation artifact integrity failed")
    persisted = _load_json(root / "formula_derivation_preparation.json")
    validate_formula_derivation_preparation_payload(persisted)
    rebuilt_preparation = rebuild_formula_derivation_preparation_read_only(project_root)
    derivations = rebuilt_preparation.derivations
    rebuilt = rebuilt_preparation.to_dict()
    if persisted != rebuilt:
        raise ValidationError("persisted formula derivation preparation differs from rebuild")
    if manifest.get("contract_semantic_digest") != rebuilt.get("semantic_digest"):
        raise ValidationError("formula derivation manifest lost its contract binding")
    expected_artifacts: dict[str, Mapping[str, object]] = {
        "formula_derivation_preparation.json": rebuilt,
        "data_usage_ledger.json": cast(Mapping[str, object], rebuilt["data_usage_ledger"]),
    }
    for item in derivations:
        prefix = f"tools/{item.source_formula.tool_id}"
        expected_artifacts.update(
            {
                f"{prefix}/formula_derivation_package.json": item.package.to_dict(),
                f"{prefix}/joint_policy_family.json": item.joint_policy_family.to_dict(),
                f"{prefix}/joint_policy_attempt_manifest.json": dict(item.registered_policy_attempt_manifest),
                f"{prefix}/factor_registration_snapshot.json": {
                    "tool_id": item.source_formula.tool_id,
                    "factor_pool_version": item.factor_pool_version,
                    "factor_pool_query_digest": item.factor_pool_query_digest,
                    "registered_factor_specs": [spec.to_dict() for spec in item.registered_factor_specs],
                    "production_authority": False,
                },
            }
        )
    if artifact_paths != set(expected_artifacts):
        raise ValidationError("formula derivation preparation artifact inventory is incomplete")
    for relative_path, expected in expected_artifacts.items():
        if _load_json(root / relative_path) != expected:
            raise ValidationError("formula derivation preparation standalone artifact differs from rebuild")
    return rebuilt


def _mapping(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValidationError(f"formula derivation preparation requires {key}")
    return cast(Mapping[str, object], value)


def _reject_non_false_authority(value: object, *, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for raw_key, nested in cast(Mapping[object, object], value).items():
            key = str(raw_key)
            if key == "field_labels_zh":
                continue
            metadata_false = (
                len(path) == 5
                and path[0] == "tools"
                and path[1].isdigit()
                and path[2] == "registered_factor_specs"
                and path[3].isdigit()
                and path[4] == "tags"
                and nested == "false"
            )
            if (key.endswith("authority") or key == "stage3_authorized") and nested is not False and not metadata_false:
                raise ValidationError("formula derivation preparation nested authority changed")
            _reject_non_false_authority(nested, path=(*path, key))
    elif isinstance(value, list):
        for index, nested in enumerate(cast(list[object], value)):
            _reject_non_false_authority(nested, path=(*path, str(index)))


def _expected_factor_spec(
    *,
    tool_id: str,
    source_formula: Mapping[str, object],
    attribute: Mapping[str, object],
    factor_pool_query_digest: str,
) -> dict[str, object]:
    attribute_id = str(attribute.get("attribute_id", ""))
    causal_formula = str(attribute.get("causal_formula", ""))
    unit = str(attribute.get("unit", ""))
    formula_id = str(source_formula.get("formula_id", ""))
    implementation_ref = str(source_formula.get("implementation_ref", ""))
    native_refs = source_formula.get("native_source_refs")
    if not attribute_id or not causal_formula or not unit or not formula_id or not implementation_ref:
        raise ValidationError("formula derivation preparation FactorSpec source binding is incomplete")
    if not isinstance(native_refs, list) or any(not isinstance(item, str) for item in cast(list[object], native_refs)):
        raise ValidationError("formula derivation preparation FactorSpec source refs changed")
    factor_spec_id = f"market-state-formula-native:{tool_id}:{attribute_id}:v2"
    expression_digest = canonical_digest(
        {
            "tool_formula_id": formula_id,
            "attribute_id": attribute_id,
            "causal_formula": causal_formula,
        }
    )
    return FactorSpec(
        spec_id=factor_spec_id,
        spec_version=factor_spec_id,
        name=attribute_id,
        description=(
            "Formula-native structural research factor. Registered after the "
            "base_factor_universe query; not strategy-validated."
        ),
        factor_type="python_callable",
        callable_ref=(
            "factor_lab.market_state.formula_derivation.materialization:"
            "materialize_registered_formula_factor"
        ),
        input_schema={
            "required_fields": ["timestamp", "open", "high", "low", "close"],
            "tool_id": tool_id,
            "attribute_id": attribute_id,
        },
        output_schema={
            "unit": unit,
            "availability": attribute.get("availability"),
            "causal": True,
        },
        parameters={
            "causal_formula": causal_formula,
            "tool_formula_id": formula_id,
            "factor_pool_query_digest": factor_pool_query_digest,
            "attribute_id": attribute_id,
        },
        source_refs=[implementation_ref, *cast(list[str], native_refs)],
        input_field_lineage={
            field: f"raw_kline.{field}"
            for field in ("timestamp", "open", "high", "low", "close")
        },
        expression_hash=expression_digest,
        normalized_ast={
            "op": "source_backed_tool_formula_attribute",
            "tool_id": tool_id,
            "attribute_id": attribute_id,
            "formula": causal_formula,
        },
        operator_list=["source_backed_tool_formula_attribute"],
        complexity_score=1.0,
        field_refs=["timestamp", "open", "high", "low", "close"],
        nan_policy="warmup_or_domain_guard_failure_yields_null",
        tags=dict(_EXPECTED_FACTOR_SPEC_TAGS),
    ).to_dict()


def _load_frozen_v1_parent(project_root: Path) -> dict[str, object]:
    path = (project_root / FROZEN_V1_PREPARATION_RELATIVE_PATH).resolve()
    if (
        not path.is_relative_to(project_root)
        or not path.is_file()
        or _sha256(path) != EXPECTED_V1_PREPARATION_FILE_SHA256
    ):
        raise ValidationError("frozen V1 parent artifact is missing or byte-drifted")
    payload = _load_json(path)
    validate_tool_research_preparation_payload(payload)
    if payload.get("semantic_digest") != EXPECTED_V1_PREPARATION_SEMANTIC_DIGEST:
        raise ValidationError("frozen V1 parent semantic identity changed")
    counts = _mapping(payload, "counts")
    if counts.get("tool_count") != 13:
        raise ValidationError("frozen V1 parent no longer covers 13 tools")
    return payload


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    _ = path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact(root: Path, path: Path) -> dict[str, object]:
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


__all__ = [
    "EXPECTED_V1_PREPARATION_SEMANTIC_DIGEST",
    "EXPECTED_V1_PREPARATION_FILE_SHA256",
    "FROZEN_V1_PREPARATION_RELATIVE_PATH",
    "FORMULA_DERIVATION_PREPARATION_SCHEMA_ID",
    "FORMULA_DERIVATION_PREPARATION_VERSION",
    "FormulaDerivationPreparation",
    "build_formula_derivation_preparation",
    "rebuild_formula_derivation_preparation_read_only",
    "validate_formula_derivation_preparation_payload",
    "validate_persisted_formula_derivation_preparation",
    "write_formula_derivation_preparation",
]
