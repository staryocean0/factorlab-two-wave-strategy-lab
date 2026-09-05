# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Authoritative three-class identity registry for timing infrastructure and strategies.

The registry is intentionally fail-closed after the four-layer infrastructure
rebuild: historical ``installed`` or ``current`` labels do not grant current
registered-use, paper-trading, live-trading, or production authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Literal, cast

from factor_lab.core.errors import ValidationError

REGISTRY_SCHEMA_ID: Final[str] = "timing_strategy_identity_registry@2.2"
CLASS_ORDER: Final[tuple[str, ...]] = (
    "infrastructure",
    "strategy_research",
    "registered_usable_strategy",
)

StrategyResearchStatus = Literal[
    "research_pending_requalification",
    "unfinished_strategy_prototype",
    "active_research_candidate",
    "historical_closed",
]

INFRASTRUCTURE_ASSET_IDS: Final[tuple[str, ...]] = (
    "tool_registry_v1_5",
    "tool_relative_coupling",
    "paper_kernel_tool_identity",
    "formula_derived_tool_inversion",
    "evaluation_platform_v4",
    "formula_derived_joint_state_machine",
    "volatility_three_state_machine",
    "priority_composition_waterfall",
    "tool_conditioned_relationships",
    "tool_attribute_relationship_maps",
)


@dataclass(frozen=True, slots=True)
class StrategyResearchIdentity:
    strategy_id: str
    asset_id: str
    status: StrategyResearchStatus
    canonical_source: str
    legacy_compatibility_source: str | None
    requalification_required: bool
    historical_labels_revoked: tuple[str, ...] = ()
    registered_use_authority: bool = False
    parameter_selection_authority: bool = False
    paper_trading_authority: bool = False
    live_trading_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if not self.strategy_id or not self.asset_id or not self.canonical_source:
            raise ValidationError("timing strategy research identity is incomplete")
        if self.status == "historical_closed" and self.requalification_required:
            raise ValidationError("closed historical evidence cannot be pending requalification")
        if any(
            (
                self.registered_use_authority,
                self.parameter_selection_authority,
                self.paper_trading_authority,
                self.live_trading_authority,
                self.production_authority,
            )
        ):
            raise ValidationError("strategy research assets cannot carry usable or trading authority")


def strategy_research_identities() -> tuple[StrategyResearchIdentity, ...]:
    """Return every concrete timing strategy under the reset authority."""

    return (
        StrategyResearchIdentity(
            strategy_id="timing_strategy_router_v4",
            asset_id="timing_strategy_router_v4",
            status="research_pending_requalification",
            canonical_source="src/factor_lab/strategy/research/timing/router_v4.py",
            legacy_compatibility_source="src/factor_lab/market_state/timing_strategy_routing_v4.py",
            requalification_required=True,
            historical_labels_revoked=("installed_router_profile", "architecture_locked"),
        ),
        StrategyResearchIdentity(
            strategy_id="high_slope_explosive_owner_v3",
            asset_id="explosive_layer_v3",
            status="research_pending_requalification",
            canonical_source="src/factor_lab/strategy/research/timing/explosive_v3.py",
            legacy_compatibility_source="src/factor_lab/market_state/timing_explosive_layer_v3.py",
            requalification_required=True,
            historical_labels_revoked=("installed_current_owner_profile",),
        ),
        StrategyResearchIdentity(
            strategy_id="crash_rebound_current_best_research_r1",
            asset_id="crash_rebound_current_best",
            status="research_pending_requalification",
            canonical_source="src/factor_lab/strategy/research/timing/crash_rebound_r1.py",
            legacy_compatibility_source="src/factor_lab/market_state/timing_crash_rebound_current_best_r1.py",
            requalification_required=True,
            historical_labels_revoked=("current_best", "fresh_oos_authority"),
        ),
        StrategyResearchIdentity(
            strategy_id="csi1000_lat_p8_l2_matched_bucket_prototype",
            asset_id="csi1000_lat_p8_l2_matched_bucket_prototype",
            status="unfinished_strategy_prototype",
            canonical_source="src/factor_lab/strategy/research/timing/lat_p8_l2_matched_bucket_prototype.py",
            legacy_compatibility_source=None,
            requalification_required=True,
            historical_labels_revoked=(
                "layer2_infrastructure",
                "installed_plugin",
                "registered_usable_strategy",
            ),
        ),
        StrategyResearchIdentity(
            strategy_id="parallel_annual_clean_room_a12",
            asset_id="timing_research_samples_rN",
            status="historical_closed",
            canonical_source="src/factor_lab/market_state/timing_three_specialist_isolated_annual_v7.py",
            legacy_compatibility_source=None,
            requalification_required=False,
            historical_labels_revoked=("current_research_exemplar",),
        ),
    )


def build_timing_strategy_identity_registry() -> dict[str, object]:
    research = strategy_research_identities()
    return {
        "schema_id": REGISTRY_SCHEMA_ID,
        "status": "current_unfinished_p8_bucket_prototype_added",
        "class_order": list(CLASS_ORDER),
        "classes": {
            "infrastructure": {
                "asset_ids": list(INFRASTRUCTURE_ASSET_IDS),
                "strategy_identity": False,
                "position_output_authority": False,
                "registered_use_authority": False,
                "trading_authority": False,
                "production_authority": False,
                "essential_surfaces": [
                    "StrategyLanguageRegistry",
                    "ResearchAcceptanceGovernance",
                    "GenericOrchestrationKernel",
                    "PluginLifecycleRegistry",
                    "StrategyConditionalEffectResearch",
                ],
            },
            "strategy_research": {
                "assets": [asdict(item) for item in research],
                "research_backtest_allowed": True,
                "runtime_installation_allowed": False,
                "registered_use_authority": False,
                "trading_authority": False,
                "production_authority": False,
            },
            "registered_usable_strategy": {
                "assets": [],
                "registration_requires_explicit_receipt": True,
                "paper_live_production_authorities_are_separate": True,
            },
        },
        "infrastructure_asset_count": len(INFRASTRUCTURE_ASSET_IDS),
        "strategy_research_asset_count": len(research),
        "registered_usable_strategy_count": 0,
        "legacy_installed_labels_have_current_authority": False,
        "requalification_contract": {
            "four_layer_assembly_manifest_required": True,
            "layer4_parameter_selection_receipt_required": True,
            "strategy_slice_rebuild_required_for_behavior_change": True,
            "post_training_account_audit_A0_A7_required": True,
            "genuinely_unseen_challenge_required": True,
            "explicit_registration_receipt_required": True,
        },
        "registered_use_authority": False,
        "paper_trading_authority": False,
        "live_trading_authority": False,
        "production_authority": False,
    }


def validate_timing_strategy_identity_registry(
    payload: Mapping[str, object], *, project_root: Path
) -> dict[str, object]:
    """Validate exclusivity, physical sources, and the fail-closed reset."""

    if payload.get("schema_id") != REGISTRY_SCHEMA_ID:
        raise ValidationError("timing strategy identity schema drifted")
    if tuple(cast(list[object], payload.get("class_order", []))) != CLASS_ORDER:
        raise ValidationError("timing strategy identity class order drifted")
    classes = payload.get("classes")
    if not isinstance(classes, Mapping) or set(classes) != set(CLASS_ORDER):
        raise ValidationError("timing strategy identity requires exactly three classes")

    infrastructure = classes.get("infrastructure")
    research = classes.get("strategy_research")
    registered = classes.get("registered_usable_strategy")
    if not isinstance(infrastructure, Mapping) or not isinstance(research, Mapping) or not isinstance(registered, Mapping):
        raise ValidationError("timing strategy identity class payload is invalid")
    infrastructure_ids = tuple(cast(list[object], infrastructure.get("asset_ids", [])))
    research_assets = research.get("assets")
    registered_assets = registered.get("assets")
    if infrastructure_ids != INFRASTRUCTURE_ASSET_IDS:
        raise ValidationError("timing infrastructure denominator drifted")
    if not isinstance(research_assets, list) or len(research_assets) != 5:
        raise ValidationError("timing research denominator drifted")
    if registered_assets != [] or payload.get("registered_usable_strategy_count") != 0:
        raise ValidationError("legacy timing strategies must not survive the authority reset")

    research_ids: list[str] = []
    for item in research_assets:
        if not isinstance(item, Mapping):
            raise ValidationError("timing strategy research entry is invalid")
        research_ids.append(str(item.get("asset_id")))
        for authority in (
            "registered_use_authority",
            "parameter_selection_authority",
            "paper_trading_authority",
            "live_trading_authority",
            "production_authority",
        ):
            if item.get(authority) is not False:
                raise ValidationError(f"strategy research entry overclaims {authority}")
        source = project_root / str(item.get("canonical_source"))
        if not source.is_file():
            raise ValidationError(f"canonical strategy research source missing: {source}")
        legacy = item.get("legacy_compatibility_source")
        if legacy and not (project_root / str(legacy)).is_file():
            raise ValidationError(f"legacy strategy compatibility source missing: {legacy}")

    all_ids = (*infrastructure_ids, *research_ids)
    if len(all_ids) != 15 or len(set(all_ids)) != 15:
        raise ValidationError("all fifteen current timing assets must have one exclusive identity")
    if payload.get("legacy_installed_labels_have_current_authority") is not False:
        raise ValidationError("legacy installed labels cannot retain current authority")
    for authority in (
        "registered_use_authority",
        "paper_trading_authority",
        "live_trading_authority",
        "production_authority",
    ):
        if payload.get(authority) is not False:
            raise ValidationError(f"timing authority reset overclaims {authority}")
    return {
        "status": "passed",
        "class_count": 3,
        "infrastructure_asset_count": 10,
        "strategy_research_asset_count": 5,
        "registered_usable_strategy_count": 0,
        "production_authority": False,
    }


__all__ = [
    "CLASS_ORDER",
    "INFRASTRUCTURE_ASSET_IDS",
    "REGISTRY_SCHEMA_ID",
    "StrategyResearchIdentity",
    "build_timing_strategy_identity_registry",
    "strategy_research_identities",
    "validate_timing_strategy_identity_registry",
]
