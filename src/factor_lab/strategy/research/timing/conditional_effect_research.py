# pyright: reportAny=false, reportUnknownMemberType=false
"""Layer 3 authority for strategy/tool effects conditioned on Layer 2 attributes."""

from __future__ import annotations

from typing import Final

from factor_lab.market_state.tool_affinity import (
    ToolAffinityPolicy,
    build_tool_state_affinity_evidence,
    tool_evidence_semantic_digest,
    tool_fold_evidence_semantic_digest,
)
from factor_lab.market_state.tool_conditioned_relationships import (
    ToolConditionedRelationshipPolicy,
    ToolConditionedRelationshipResult,
    build_tool_conditioned_relationships,
)

CONTRACT_ID: Final = "timing_layer3_strategy_conditional_effect_research@1.0"
MIGRATED_ASSET_IDS: Final = (
    "tool_conditioned_relationships",
    "tool_attribute_relationship_maps",
)


def strategy_conditional_effect_research_contract() -> dict[str, object]:
    return {
        "schema_id": CONTRACT_ID,
        "surface_id": "StrategyConditionalEffectResearch",
        "migrated_asset_ids": list(MIGRATED_ASSET_IDS),
        "required_inputs": [
            "Layer2 causal attribute bundle or sealed offline attribute material",
            "one named strategy/tool identity",
            "strategy decision/position/action-role/account-effect evidence",
            "result-free hypothesis and multiplicity contract",
        ],
        "research_questions": [
            "which Layer2 attributes condition one strategy or tool effect",
            "whether mirrored parameter effects are stable within one tool",
            "whether a conditional effect survives chronological validation",
        ],
        "forbidden_outputs": [
            "Layer2 market measurement",
            "automatic runtime route",
            "selected final parameter",
            "registered usable strategy",
        ],
        "legacy_implementation_sources": [
            "src/factor_lab/market_state/tool_conditioned_relationships.py",
            "src/factor_lab/market_state/tool_affinity.py",
        ],
        "Layer2_measurement_authority": False,
        "strategy_research_authority": True,
        "runtime_installation_authority": False,
        "parameter_selection_authority": False,
        "paper_trading_authority": False,
        "live_trading_authority": False,
        "production_authority": False,
    }


__all__ = [
    "CONTRACT_ID",
    "MIGRATED_ASSET_IDS",
    "ToolAffinityPolicy",
    "ToolConditionedRelationshipPolicy",
    "ToolConditionedRelationshipResult",
    "build_tool_conditioned_relationships",
    "build_tool_state_affinity_evidence",
    "strategy_conditional_effect_research_contract",
    "tool_evidence_semantic_digest",
    "tool_fold_evidence_semantic_digest",
]
