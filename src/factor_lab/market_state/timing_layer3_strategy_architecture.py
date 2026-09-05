# pyright: reportAny=false, reportArgumentType=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Historical @1.0 four-category Layer 3 architecture builder.

Current strategy authority is governed by
``factor_lab.governance.timing_strategy_identity_registry``.  Historical
``installed`` labels emitted here have no current registered-use authority.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Literal, cast

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.formula_derived_three_stage_workflow import (
    THREE_STAGE_WORKFLOW_SCHEMA_ID,
)
from factor_lab.market_state.timing_evaluation_platform import (
    SCHEMA_ID as EVALUATION_PLATFORM_SCHEMA_ID,
)
from factor_lab.market_state.tool_registry import DISCOVERED_TOOL_IDS
from factor_lab.market_state.tool_registry_v1_4 import (
    CURRENT_TOOL_IDS as COUPLED_TOOL_IDS,
)
from factor_lab.market_state.tool_registry_v1_4 import (
    PAPER_KERNEL_TOOL_ID,
)
from factor_lab.market_state.tool_registry_v1_5 import (
    CURRENT_TOOL_IDS,
    LAT_TOOL_ID,
    TOOL_REGISTRY_V1_5_SCHEMA_ID,
    TOOL_REGISTRY_V1_5_VERSION,
)

ARCHITECTURE_SCHEMA_ID: Final[str] = "timing_layer3_strategy_architecture@1.0"
ARCHITECTURE_ID: Final[str] = "timing_layer3_four_category_v1"

CategoryId = Literal[
    "strategy_language_identity",
    "research_construction_acceptance",
    "generic_orchestration_kernel",
    "strategy_plugins_exemplars",
]
PluginStatus = Literal[
    "installed_current_owner_profile",
    "research_candidate_not_installed",
    "historical_exemplar_not_current",
]

LANGUAGE_ASSETS: Final[tuple[str, ...]] = (
    "tool_registry_v1_5",
    "tool_relative_coupling",
    "paper_kernel_tool_identity",
    "formula_derived_tool_inversion",
)
RESEARCH_ASSETS: Final[tuple[str, ...]] = (
    "evaluation_platform_v4",
    "formula_derived_joint_state_machine",
)
ORCHESTRATION_ASSETS: Final[tuple[str, ...]] = (
    "volatility_three_state_machine",
    "priority_composition_waterfall",
    "timing_strategy_router_v4",
)
PLUGIN_ASSETS: Final[tuple[str, ...]] = (
    "explosive_layer_v3",
    "crash_rebound_current_best",
    "timing_research_samples_rN",
)
ALL_LAYER3_ASSETS: Final[tuple[str, ...]] = (
    *LANGUAGE_ASSETS,
    *RESEARCH_ASSETS,
    *ORCHESTRATION_ASSETS,
    *PLUGIN_ASSETS,
)


@dataclass(frozen=True, slots=True)
class Layer3Category:
    category_id: CategoryId
    stability: str
    role: str
    asset_ids: tuple[str, ...]
    dependency_predecessors: tuple[str, ...]
    current: bool = True
    production_authority: bool = False

    def __post_init__(self) -> None:
        if not self.role or not self.asset_ids:
            raise ValidationError("Layer 3 category identity is incomplete")
        if self.production_authority:
            raise ValidationError("Layer 3 category cannot grant production authority")


@dataclass(frozen=True, slots=True)
class StrategyPluginIdentity:
    plugin_id: str
    asset_id: str
    status: PluginStatus
    contract_ref: str
    installed_in_router: bool
    generic_core: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.asset_id not in PLUGIN_ASSETS or not self.plugin_id or not self.contract_ref:
            raise ValidationError("Layer 3 plugin identity is invalid")
        if self.status == "installed_current_owner_profile" and not self.installed_in_router:
            raise ValidationError("installed current owner profile must be router-installed")
        if self.status != "installed_current_owner_profile" and self.installed_in_router:
            raise ValidationError("research/historical plugin cannot be router-installed")
        if self.generic_core or self.production_authority:
            raise ValidationError("strategy plugin cannot masquerade as generic core or production")


def layer3_categories() -> tuple[Layer3Category, ...]:
    return (
        Layer3Category(
            "strategy_language_identity",
            "stable",
            "tool identity formula semantics parameter mechanism and compiler coverage",
            LANGUAGE_ASSETS,
            (),
        ),
        Layer3Category(
            "research_construction_acceptance",
            "stable_governance",
            "preregistration evaluation progression promotion and post-training account audit",
            RESEARCH_ASSETS,
            ("strategy_language_identity",),
        ),
        Layer3Category(
            "generic_orchestration_kernel",
            "semi_stable_replaceable",
            "state adapters exclusive claims remainder propagation and conflict arbitration",
            ORCHESTRATION_ASSETS,
            ("strategy_language_identity", "research_construction_acceptance"),
        ),
        Layer3Category(
            "strategy_plugins_exemplars",
            "ephemeral_versioned",
            "installed owner profiles research candidates and explicit historical exemplars",
            PLUGIN_ASSETS,
            ("generic_orchestration_kernel",),
        ),
    )


def strategy_language_contract() -> dict[str, object]:
    current = tuple(CURRENT_TOOL_IDS)
    coupled = tuple(COUPLED_TOOL_IDS)
    formula_supported = tuple(DISCOVERED_TOOL_IDS)
    return {
        "schema_id": "timing_layer3_strategy_language@1.0",
        "tool_registry": TOOL_REGISTRY_V1_5_VERSION,
        "tool_registry_schema": TOOL_REGISTRY_V1_5_SCHEMA_ID,
        "current_tool_count": len(current),
        "current_tool_ids": list(current),
        "coupling_coverage": {
            "covered_count": len(coupled),
            "covered_tool_ids": list(coupled),
            "uncovered_tool_ids": [tool for tool in current if tool not in coupled],
            "status": "partial_explicit_not_complete",
        },
        "formula_compiler_coverage": {
            "covered_count": len(formula_supported),
            "covered_tool_ids": list(formula_supported),
            "uncovered_tool_ids": [tool for tool in current if tool not in formula_supported],
            "status": "historical_13_tool_prefix_explicit",
        },
        "paper_kernel_identity": {
            "tool_id": PAPER_KERNEL_TOOL_ID,
            "registry_lineage_view": True,
            "independent_current_component": False,
        },
        "lat_identity": {
            "tool_id": LAT_TOOL_ID,
            "registry_current": True,
            "coupling_status": "uncovered",
            "formula_compiler_status": "uncovered",
        },
        "strategy_selection_authority": False,
        "routing_authority": False,
        "production_authority": False,
    }


def research_acceptance_contract() -> dict[str, object]:
    return {
        "schema_id": "timing_layer3_research_acceptance@1.0",
        "evaluation_platform": EVALUATION_PLATFORM_SCHEMA_ID,
        "formula_research_engine": THREE_STAGE_WORKFLOW_SCHEMA_ID,
        "progression_contract": "factorlab.strategy_progressive_development@1.0",
        "post_training_account_audit": "factorlab.post_training_account_audit@1.0",
        "required_order": [
            "freeze_language_formula_and_attempt_family",
            "evaluate_hard_validity",
            "retain_hard_valid_progression",
            "apply_candidate_promotion_separately",
            "freeze_score_or_strategy_snapshot",
            "run_A0_A7_post_training_account_audit",
            "handoff_without_automatic_production",
        ],
        "joint_state_machine_runtime_authority": False,
        "progression_may_be_deleted_by_failed_promotion": False,
        "production_authority": False,
    }


def plugin_identities() -> tuple[StrategyPluginIdentity, ...]:
    return (
        StrategyPluginIdentity(
            "high_slope_explosive_owner_v3",
            "explosive_layer_v3",
            "installed_current_owner_profile",
            "src/factor_lab/market_state/timing_explosive_layer_v3.py",
            True,
        ),
        StrategyPluginIdentity(
            "crash_rebound_current_best_research_r1",
            "crash_rebound_current_best",
            "research_candidate_not_installed",
            "src/factor_lab/market_state/timing_crash_rebound_current_best_r1.py",
            False,
        ),
        StrategyPluginIdentity(
            "parallel_annual_clean_room_a12",
            "timing_research_samples_rN",
            "historical_exemplar_not_current",
            "src/factor_lab/market_state/timing_three_specialist_isolated_annual_v7.py",
            False,
        ),
    )


def build_layer3_architecture_registry() -> dict[str, object]:
    categories = layer3_categories()
    return {
        "schema_id": ARCHITECTURE_SCHEMA_ID,
        "architecture_id": ARCHITECTURE_ID,
        "status": "four_category_current_research_only",
        "current": True,
        "category_order": [item.category_id for item in categories],
        "categories": [asdict(item) for item in categories],
        "asset_count": len(ALL_LAYER3_ASSETS),
        "asset_ids": list(ALL_LAYER3_ASSETS),
        "strategy_language": strategy_language_contract(),
        "research_acceptance": research_acceptance_contract(),
        "plugins": [asdict(item) for item in plugin_identities()],
        "generic_dependency_direction": "language_to_research_to_orchestration_to_plugins",
        "formula_mutation": False,
        "strategy_runtime_mutation": False,
        "fresh_oos": False,
        "production_authority": False,
    }


def validate_layer3_architecture_registry(
    payload: Mapping[str, object],
    *,
    project_root: Path,
    frozen_inventory: Mapping[str, object],
) -> dict[str, object]:
    if payload.get("schema_id") != ARCHITECTURE_SCHEMA_ID or payload.get("architecture_id") != ARCHITECTURE_ID:
        raise ValidationError("Layer 3 architecture identity drifted")
    assets = frozen_inventory.get("assets")
    if not isinstance(assets, list):
        raise ValidationError("four-layer inventory assets are missing")
    frozen_ids = tuple(
        str(row.get("asset_id"))
        for row in assets
        if isinstance(row, Mapping) and row.get("owner_lane") == 2 and row.get("layer") in {"strategy_foundation", "strategy_ephemeral"}
    )
    if set(frozen_ids) != set(ALL_LAYER3_ASSETS) or len(frozen_ids) != 12:
        raise ValidationError("Layer 3 frozen denominator drifted")
    categories = payload.get("categories")
    if not isinstance(categories, list) or len(categories) != 4:
        raise ValidationError("Layer 3 requires exactly four categories")
    categorized = tuple(
        str(asset)
        for category in categories
        if isinstance(category, Mapping)
        for asset in cast(list[object], category.get("asset_ids", []))
    )
    if tuple(categorized) != ALL_LAYER3_ASSETS or len(set(categorized)) != 12:
        raise ValidationError("Layer 3 assets must appear exactly once in canonical order")
    language = payload.get("strategy_language")
    if not isinstance(language, Mapping) or (
        language.get("current_tool_count") != 15
        or cast(Mapping[str, object], language.get("coupling_coverage", {})).get("covered_count") != 14
        or cast(Mapping[str, object], language.get("formula_compiler_coverage", {})).get("covered_count") != 13
    ):
        raise ValidationError("Layer 3 15/14/13 coverage contract drifted")
    research = payload.get("research_acceptance")
    if not isinstance(research, Mapping) or (
        research.get("evaluation_platform") != "market_state_timing_evaluation_platform@4.0"
        or research.get("progression_contract") != "factorlab.strategy_progressive_development@1.0"
        or research.get("post_training_account_audit") != "factorlab.post_training_account_audit@1.0"
    ):
        raise ValidationError("Layer 3 research acceptance chain drifted")
    for path in (
        "docs/ops/strategy_progressive_development@1.0.json",
        "docs/ops/post_training_account_audit@1.0.json",
    ):
        if not (project_root / path).is_file():
            raise ValidationError(f"Layer 3 governance contract missing: {path}")
    plugins = payload.get("plugins")
    if not isinstance(plugins, list) or [row.get("status") for row in plugins if isinstance(row, Mapping)] != [
        "installed_current_owner_profile",
        "research_candidate_not_installed",
        "historical_exemplar_not_current",
    ]:
        raise ValidationError("Layer 3 plugin lifecycle drifted")
    if any(payload.get(key) is not False for key in ("formula_mutation", "strategy_runtime_mutation", "fresh_oos", "production_authority")):
        raise ValidationError("Layer 3 architecture overclaimed authority")
    return {
        "status": "passed",
        "category_count": 4,
        "asset_count": 12,
        "tool_count": 15,
        "coupled_count": 14,
        "formula_compiler_count": 13,
        "installed_plugin_count": 1,
        "production_authority": False,
    }


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValidationError(f"Layer 3 JSON must be an object: {path}")
    return cast(dict[str, object], payload)


__all__ = [
    "ALL_LAYER3_ASSETS",
    "ARCHITECTURE_ID",
    "ARCHITECTURE_SCHEMA_ID",
    "LANGUAGE_ASSETS",
    "ORCHESTRATION_ASSETS",
    "PLUGIN_ASSETS",
    "RESEARCH_ASSETS",
    "Layer3Category",
    "StrategyPluginIdentity",
    "build_layer3_architecture_registry",
    "layer3_categories",
    "plugin_identities",
    "research_acceptance_contract",
    "strategy_language_contract",
    "validate_layer3_architecture_registry",
]
