# pyright: reportAny=false, reportArgumentType=false, reportIndexIssue=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Research-only V4 timing assembly profile pending four-layer requalification."""

from __future__ import annotations

from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.strategy.research.timing.explosive_v3 import (
    timing_explosive_layer_v3_contract,
)

TIMING_STRATEGY_ROUTER_V4_SCHEMA_ID = "market_state_timing_strategy_router@4.1"
TIMING_STRATEGY_ROUTER_V4_VERSION = "timing_strategy_router_v4"
FOUR_LAYER_ROLE = "layer3_strategy_research"
LIFECYCLE = "research_pending_requalification"


def build_timing_strategy_router_v4_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_id": TIMING_STRATEGY_ROUTER_V4_SCHEMA_ID,
        "router_version": TIMING_STRATEGY_ROUTER_V4_VERSION,
        "four_layer_role": FOUR_LAYER_ROLE,
        "lifecycle": LIFECYCLE,
        "replaceable_by_layer2_measurement": True,
        "long_term_foundation": False,
        "architecture_status": "historical_profile_frozen_pending_requalification",
        "tiers": [
            {
                "tier": 1,
                "tier_id": "high_slope_explosive",
                "status": "research_snapshot_frozen_not_installed",
                "owner_contract": timing_explosive_layer_v3_contract(),
                "output_remainder": "remaining_after_explosive_layer",
            },
            {
                "tier": 2,
                "tier_id": "low_slope_ordinary_trend",
                "status": "owner_not_selected",
                "input_remainder": "remaining_after_explosive_layer",
                "output_remainder": "remaining_after_ordinary_trend_layer",
            },
            {
                "tier": 3,
                "tier_id": "range_scale_drilldown",
                "status": "owner_not_selected",
                "input_remainder": "remaining_after_ordinary_trend_layer",
                "output_remainder": "remaining_after_timing_router",
            },
        ],
        "direction_semantics": "up_down_flat_unassigned_separate_from_position_policy",
        "execution_semantics": "closed_bar_decision_visible_on_next_executable_bar_once",
        "runtime_uses_future": False,
        "runtime_uses_registered_events": False,
        "research_authority": True,
        "registered_use_authority": False,
        "architecture_lock_authority": False,
        "dynamic_parameter_authority": False,
        "tool_selection_authority_for_open_tiers": False,
        "paper_trading_authority": False,
        "live_trading_authority": False,
        "production_authority": False,
        "v62_runtime_modified": False,
    }
    payload["semantic_digest"] = canonical_digest(payload)
    validate_timing_strategy_router_v4_payload(payload)
    return payload


def validate_timing_strategy_router_v4_payload(payload: dict[str, object]) -> None:
    if payload.get("schema_id") != TIMING_STRATEGY_ROUTER_V4_SCHEMA_ID:
        raise ValueError("timing strategy router V4 schema changed")
    if payload.get("router_version") != TIMING_STRATEGY_ROUTER_V4_VERSION:
        raise ValueError("timing strategy router V4 version changed")
    if (
        payload.get("four_layer_role") != FOUR_LAYER_ROLE
        or payload.get("lifecycle") != LIFECYCLE
        or payload.get("replaceable_by_layer2_measurement") is not True
        or payload.get("long_term_foundation") is not False
    ):
        raise ValueError("timing strategy router V4 research lifecycle drifted")
    tiers = payload.get("tiers")
    if not isinstance(tiers, list) or len(tiers) != 3:
        raise ValueError("timing strategy router V4 must contain exactly three tiers")
    if tiers[0].get("status") != "research_snapshot_frozen_not_installed":
        raise ValueError("timing strategy router V4 tier 1 escaped research quarantine")
    if any(tier.get("status") != "owner_not_selected" or "owner_contract" in tier for tier in tiers[1:]):
        raise ValueError("unfinished timing tiers must not receive owners")
    for authority in (
        "registered_use_authority",
        "architecture_lock_authority",
        "dynamic_parameter_authority",
        "tool_selection_authority_for_open_tiers",
        "paper_trading_authority",
        "live_trading_authority",
        "production_authority",
        "v62_runtime_modified",
    ):
        if payload.get(authority) is not False:
            raise ValueError(f"timing strategy router V4 cannot grant {authority}")
    stored = payload.get("semantic_digest")
    unsigned = dict(payload)
    _ = unsigned.pop("semantic_digest", None)
    if stored != canonical_digest(unsigned):
        raise ValueError("timing strategy router V4 semantic digest mismatch")


__all__ = [
    "FOUR_LAYER_ROLE",
    "LIFECYCLE",
    "TIMING_STRATEGY_ROUTER_V4_SCHEMA_ID",
    "TIMING_STRATEGY_ROUTER_V4_VERSION",
    "build_timing_strategy_router_v4_payload",
    "validate_timing_strategy_router_v4_payload",
]
