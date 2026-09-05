# pyright: reportAny=false, reportArgumentType=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Necessity and Layer 2 material-migration registry for Layer 3 assets."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final, Literal

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_layer3_strategy_architecture import (
    ALL_LAYER3_ASSETS,
)

NECESSITY_SCHEMA_ID: Final[str] = "timing_layer3_necessity_registry@1.0"
Necessity = Literal[
    "essential_core",
    "conditional_operator",
    "merged_lineage",
    "replaceable_compatibility",
    "strategy_plugin",
    "research_candidate",
    "historical_only",
]
MigrationStatus = Literal[
    "already_in_layer2",
    "migrated_now",
    "not_layer2_policy_material",
    "no_attribute_material",
]


@dataclass(frozen=True, slots=True)
class AssetNecessity:
    asset_id: str
    necessity: Necessity
    current_standalone: bool
    retained_as: str
    reason: str

    def __post_init__(self) -> None:
        if self.asset_id not in ALL_LAYER3_ASSETS or not self.retained_as or not self.reason:
            raise ValidationError("Layer 3 necessity identity is invalid")


@dataclass(frozen=True, slots=True)
class ResearchMaterialAudit:
    material_id: str
    source_asset_id: str
    material_kind: str
    migration_status: MigrationStatus
    layer2_destination: str | None
    retained_layer3_material: str | None

    def __post_init__(self) -> None:
        if self.source_asset_id not in ALL_LAYER3_ASSETS or not self.material_id:
            raise ValidationError("Layer 3 material audit identity is invalid")
        if self.migration_status in {"already_in_layer2", "migrated_now"} and not self.layer2_destination:
            raise ValidationError("migrated Layer 3 material requires a Layer 2 destination")
        if self.migration_status == "not_layer2_policy_material" and not self.retained_layer3_material:
            raise ValidationError("policy material must retain its Layer 3 destination")


def asset_necessities() -> tuple[AssetNecessity, ...]:
    return (
        AssetNecessity("tool_registry_v1_5", "essential_core", True, "StrategyLanguageRegistry", "unique_15_tool_identity_truth"),
        AssetNecessity(
            "tool_relative_coupling",
            "conditional_operator",
            False,
            "versioned_language_relation_view",
            "relations_change_when_layer2_knowledge_improves",
        ),
        AssetNecessity(
            "paper_kernel_tool_identity", "merged_lineage", False, "tool_registry_v1_5_lineage", "already_the_14th_registry_tool"
        ),
        AssetNecessity(
            "formula_derived_tool_inversion",
            "conditional_operator",
            False,
            "formula_compiler_service",
            "auditable_structural_compilation_not_runtime_state",
        ),
        AssetNecessity(
            "evaluation_platform_v4",
            "essential_core",
            True,
            "ResearchAcceptanceGovernance",
            "measurement_cannot_replace_strategy_evaluation",
        ),
        AssetNecessity(
            "formula_derived_joint_state_machine",
            "conditional_operator",
            False,
            "research_family_engine",
            "specific_state_templates_are_candidates_not_runtime_core",
        ),
        AssetNecessity(
            "volatility_three_state_machine",
            "replaceable_compatibility",
            False,
            "compatibility_state_adapter",
            "lossy_bucket_of_layer2_continuous_volatility",
        ),
        AssetNecessity(
            "priority_composition_waterfall",
            "merged_lineage",
            False,
            "GenericOrchestrationKernel",
            "capability_retained_but_standalone_asset_merged",
        ),
        AssetNecessity(
            "timing_strategy_router_v4",
            "strategy_plugin",
            False,
            "installed_router_profile_v4",
            "specific_three_tier_taxonomy_is_replaceable",
        ),
        AssetNecessity(
            "explosive_layer_v3", "strategy_plugin", False, "installed_owner_profile_v3", "current_prior_policy_not_generic_infrastructure"
        ),
        AssetNecessity(
            "crash_rebound_current_best",
            "research_candidate",
            False,
            "uninstalled_research_plugin",
            "candidate_name_does_not_grant_installation",
        ),
        AssetNecessity(
            "timing_research_samples_rN",
            "historical_only",
            False,
            "explicit_A12_historical_exemplar",
            "wildcard_market_state_directory_is_not_an_asset",
        ),
    )


def research_material_audit() -> tuple[ResearchMaterialAudit, ...]:
    return (
        ResearchMaterialAudit(
            "volatility_continuous_rv_bipower_jump",
            "volatility_three_state_machine",
            "continuous_measurement",
            "already_in_layer2",
            "timing_layer2_measurement_plane@2.1:context_and_extended_volatility",
            None,
        ),
        ResearchMaterialAudit(
            "volatility_quantile_thresholds_hysteresis_residence",
            "volatility_three_state_machine",
            "bucket_and_memory_policy",
            "not_layer2_policy_material",
            None,
            "compatibility_state_adapter",
        ),
        ResearchMaterialAudit(
            "formula_native_continuous_attributes",
            "formula_derived_joint_state_machine",
            "structural_continuous_measurement",
            "migrated_now",
            "timing_layer2_state_machine_research_material@1.0:formula_native_projection",
            None,
        ),
        ResearchMaterialAudit(
            "formula_interaction_state_templates",
            "formula_derived_joint_state_machine",
            "candidate_state_topology",
            "not_layer2_policy_material",
            None,
            "research_family_engine",
        ),
        ResearchMaterialAudit(
            "fda_local_quadratic_velocity_acceleration",
            "explosive_layer_v3",
            "continuous_path_kinematics",
            "migrated_now",
            "timing_layer2_state_machine_research_material@1.0:local_quadratic_kinematics",
            None,
        ),
        ResearchMaterialAudit(
            "multiscale_component_phase_energy",
            "explosive_layer_v3",
            "continuous_phase_measurement",
            "already_in_layer2",
            "timing_layer2_phase_relationship@1.0",
            None,
        ),
        ResearchMaterialAudit(
            "authority_period_arc_parent_down_context",
            "explosive_layer_v3",
            "owner_and_lifecycle_policy",
            "not_layer2_policy_material",
            None,
            "installed_owner_profile_v3",
        ),
        ResearchMaterialAudit(
            "ema_h4_continuous_velocity_axis",
            "crash_rebound_current_best",
            "continuous_momentum_measurement",
            "migrated_now",
            "timing_layer2_state_machine_research_material@1.0:ema_velocity",
            None,
        ),
        ResearchMaterialAudit(
            "ema_boundaries_k_mapping_entry_exit",
            "crash_rebound_current_best",
            "threshold_route_and_lifecycle_policy",
            "not_layer2_policy_material",
            None,
            "uninstalled_research_plugin",
        ),
        ResearchMaterialAudit(
            "priority_and_remainder_semantics",
            "priority_composition_waterfall",
            "orchestration_policy",
            "no_attribute_material",
            None,
            "GenericOrchestrationKernel",
        ),
        ResearchMaterialAudit(
            "three_tier_owner_taxonomy",
            "timing_strategy_router_v4",
            "routing_profile",
            "no_attribute_material",
            None,
            "installed_router_profile_v4",
        ),
        ResearchMaterialAudit(
            "annual_rebuild_evidence_and_counterexamples",
            "timing_research_samples_rN",
            "historical_strategy_evidence",
            "no_attribute_material",
            None,
            "explicit_A12_historical_exemplar",
        ),
    )


def build_necessity_registry() -> dict[str, object]:
    necessities = asset_necessities()
    materials = research_material_audit()
    return {
        "schema_id": NECESSITY_SCHEMA_ID,
        "status": "material_migration_complete_demotion_ready",
        "parent_architecture": "timing_layer3_strategy_architecture@1.0",
        "asset_count": len(necessities),
        "assets": [asdict(item) for item in necessities],
        "material_count": len(materials),
        "materials": [asdict(item) for item in materials],
        "essential_surfaces": [
            "StrategyLanguageRegistry",
            "ResearchAcceptanceGovernance",
            "GenericOrchestrationKernel",
            "PluginLifecycleRegistry",
        ],
        "physical_deletion": False,
        "formula_mutation": False,
        "strategy_runtime_mutation": False,
        "production_authority": False,
    }


def validate_necessity_registry(payload: dict[str, object]) -> None:
    if payload.get("schema_id") != NECESSITY_SCHEMA_ID or payload.get("asset_count") != 12:
        raise ValidationError("Layer 3 necessity registry identity drifted")
    assets = payload.get("assets")
    if not isinstance(assets, list) or {row.get("asset_id") for row in assets if isinstance(row, dict)} != set(ALL_LAYER3_ASSETS):
        raise ValidationError("Layer 3 necessity registry does not cover 12 assets")
    materials = payload.get("materials")
    if not isinstance(materials, list) or len(materials) != 12:
        raise ValidationError("Layer 3 research material audit is incomplete")
    migrated = [row for row in materials if isinstance(row, dict) and row.get("migration_status") == "migrated_now"]
    if len(migrated) != 3 or any(not row.get("layer2_destination") for row in migrated):
        raise ValidationError("Layer 3 missing research materials were not migrated")
    if any(
        payload.get(key) is not False
        for key in ("physical_deletion", "formula_mutation", "strategy_runtime_mutation", "production_authority")
    ):
        raise ValidationError("Layer 3 demotion overclaimed mutation or authority")


__all__ = [
    "NECESSITY_SCHEMA_ID",
    "AssetNecessity",
    "ResearchMaterialAudit",
    "asset_necessities",
    "build_necessity_registry",
    "research_material_audit",
    "validate_necessity_registry",
]
