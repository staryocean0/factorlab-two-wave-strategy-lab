# pyright: reportAny=false, reportArgumentType=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
"""Strategy-neutral priority composition for timing tools.

Each side owns an independent waterfall.  A higher-priority tool claims only
eligible bars that are still unassigned; lower-priority tools can see only the
remainder.  This module intentionally defines no concrete priority order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.tool_registry_v1_5 import CURRENT_TOOL_IDS

TIMING_PRIORITY_SCHEMA_ID = "market_state_timing_priority_composition@1.1"
TIMING_PRIORITY_FRAMEWORK_VERSION = "timing_priority_composition_v1_1"
TIMING_PRIORITY_SIDE_IDS = ("upside_capture", "downside_protection")
FOUR_LAYER_ROLE = "layer3b_strategy_ephemeral"
LIFECYCLE = "replaceable_by_more_complete_layer2_measurement_not_a_long_term_foundation"


@dataclass(frozen=True, slots=True)
class TimingPriorityClaim:
    """One candidate tool responsibility over a causal eligibility mask."""

    tool_id: str
    side_id: str
    priority_rank: int
    state_id: str
    eligible: pd.Series

    def __post_init__(self) -> None:
        if self.tool_id not in CURRENT_TOOL_IDS:
            raise ValidationError(f"priority claim tool is not in current 15: {self.tool_id}")
        if self.side_id not in TIMING_PRIORITY_SIDE_IDS:
            raise ValidationError(f"unsupported timing priority side: {self.side_id}")
        if self.priority_rank < 1:
            raise ValidationError("priority rank must be positive")
        if not self.state_id.strip():
            raise ValidationError("priority claim state_id is required")
        if self.eligible.empty or self.eligible.index.has_duplicates:
            raise ValidationError("priority eligibility must be non-empty with unique index")
        if self.eligible.isna().any() or not pd.api.types.is_bool_dtype(self.eligible.dtype):
            raise ValidationError("priority eligibility must be a complete boolean series")


def build_timing_priority_composition_payload() -> dict[str, object]:
    """Build the empty, governed framework before any order is selected."""

    payload: dict[str, object] = {
        "schema_id": TIMING_PRIORITY_SCHEMA_ID,
        "framework_version": TIMING_PRIORITY_FRAMEWORK_VERSION,
        "tool_registry_version": "tool_registry_v1_5",
        "tool_count": len(CURRENT_TOOL_IDS),
        "eligible_tool_ids": list(CURRENT_TOOL_IDS),
        "four_layer_role": FOUR_LAYER_ROLE,
        "lifecycle": LIFECYCLE,
        "replaceable_by_layer2_measurement": True,
        "long_term_foundation": False,
        "composition_semantics": "first_eligible_claims_remaining_bars",
        "waterfall_formula": (
            "R0=eligible_universe; Ck=R(k-1)∩E(tool_k,side); Rk=R(k-1)\\Ck"
        ),
        "side_contracts": {
            "upside_capture": {
                "meaning": "tools compete to own upward opportunity bars",
                "consumer_action_mapping": "consumer_defined_long_or_hold",
                "priority_ladder": [],
            },
            "downside_protection": {
                "meaning": "tools compete to own downward risk bars",
                "consumer_action_mapping": "consumer_defined_cash_hedge_or_short",
                "priority_ladder": [],
            },
        },
        "cross_side_arbitration": "not_defined_in_framework_v1",
        "unclaimed_bar_policy": "remain_unassigned_no_default_action",
        "priority_selection_status": "framework_only_no_priority_selected",
        "selection_data_rows_read": 0,
        "return_rows_read": 0,
        "production_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
        "field_labels_zh": {
            "eligible_tool_ids": "可参与组合的十五个择时工具",
            "composition_semantics": "优先级组合语义",
            "side_contracts": "做多捕获与下跌防护两侧合同",
            "priority_ladder": "待研究的工具优先级阶梯",
            "unclaimed_bar_policy": "尚未认领K线处理方式",
            "priority_selection_status": "优先级选择状态",
        },
    }
    payload["semantic_digest"] = canonical_digest(payload)
    validate_timing_priority_composition_payload(payload)
    return payload


def validate_timing_priority_composition_payload(payload: dict[str, object]) -> None:
    """Ensure the scaffold stays empty and cannot silently become a route."""

    if payload.get("schema_id") != TIMING_PRIORITY_SCHEMA_ID:
        raise ValidationError("timing priority schema changed")
    if payload.get("framework_version") != TIMING_PRIORITY_FRAMEWORK_VERSION:
        raise ValidationError("timing priority framework version changed")
    if tuple(payload.get("eligible_tool_ids", ())) != CURRENT_TOOL_IDS:
        raise ValidationError("timing priority framework must use current 15-tool registry")
    if (
        payload.get("tool_registry_version") != "tool_registry_v1_5"
        or payload.get("four_layer_role") != FOUR_LAYER_ROLE
        or payload.get("lifecycle") != LIFECYCLE
        or payload.get("replaceable_by_layer2_measurement") is not True
        or payload.get("long_term_foundation") is not False
    ):
        raise ValidationError("timing priority Layer 3b lifecycle drifted")
    sides = payload.get("side_contracts")
    if not isinstance(sides, dict) or tuple(sides) != TIMING_PRIORITY_SIDE_IDS:
        raise ValidationError("timing priority sides are incomplete or reordered")
    side_contracts = cast(dict[str, object], sides)
    for side_id in TIMING_PRIORITY_SIDE_IDS:
        side = side_contracts.get(side_id)
        if not isinstance(side, dict) or side.get("priority_ladder") != []:
            raise ValidationError("framework V1 cannot preselect a priority ladder")
    if payload.get("priority_selection_status") != "framework_only_no_priority_selected":
        raise ValidationError("framework V1 cannot claim priority selection")
    if payload.get("selection_data_rows_read") != 0 or payload.get("return_rows_read") != 0:
        raise ValidationError("empty framework must not read selection or return rows")
    for authority in (
        "production_authority",
        "dynamic_parameter_authority",
        "tool_routing_authority",
    ):
        if payload.get(authority) is not False:
            raise ValidationError(f"timing priority framework cannot grant {authority}")
    stored_digest = payload.get("semantic_digest")
    unsigned = dict(payload)
    _ = unsigned.pop("semantic_digest", None)
    if stored_digest != canonical_digest(unsigned):
        raise ValidationError("timing priority semantic digest mismatch")


def apply_timing_priority_waterfall(
    index: pd.Index,
    *,
    side_id: str,
    claims: tuple[TimingPriorityClaim, ...],
) -> pd.DataFrame:
    """Apply an already-frozen priority ladder to mutually exclusive bar claims."""

    if side_id not in TIMING_PRIORITY_SIDE_IDS:
        raise ValidationError(f"unsupported timing priority side: {side_id}")
    if index.empty or index.has_duplicates:
        raise ValidationError("priority waterfall index must be non-empty and unique")
    if not claims:
        return pd.DataFrame(
            {
                "priority_side_id": side_id,
                "responsible_tool_id": "unassigned",
                "responsible_state_id": "unassigned",
                "responsible_priority_rank": pd.Series(pd.NA, index=index, dtype="Int64"),
                "claimed": False,
                "remaining_unassigned": True,
            },
            index=index,
        )
    ranks = [claim.priority_rank for claim in claims]
    if len(ranks) != len(set(ranks)):
        raise ValidationError("priority ranks must be unique within one side")
    if any(claim.side_id != side_id for claim in claims):
        raise ValidationError("cross-side claims cannot share one waterfall")
    if any(not claim.eligible.index.equals(index) for claim in claims):
        raise ValidationError("every eligibility mask must exactly match the waterfall index")

    result = pd.DataFrame(
        {
            "priority_side_id": side_id,
            "responsible_tool_id": "unassigned",
            "responsible_state_id": "unassigned",
            "responsible_priority_rank": pd.Series(pd.NA, index=index, dtype="Int64"),
            "claimed": False,
        },
        index=index,
    )
    remaining = pd.Series(True, index=index, dtype=bool)
    for claim in sorted(claims, key=lambda item: item.priority_rank):
        newly_claimed = remaining & claim.eligible
        result.loc[newly_claimed, "responsible_tool_id"] = claim.tool_id
        result.loc[newly_claimed, "responsible_state_id"] = claim.state_id
        result.loc[newly_claimed, "responsible_priority_rank"] = claim.priority_rank
        result.loc[newly_claimed, "claimed"] = True
        remaining.loc[newly_claimed] = False
    result["remaining_unassigned"] = remaining
    return result


__all__ = [
    "FOUR_LAYER_ROLE",
    "LIFECYCLE",
    "TIMING_PRIORITY_FRAMEWORK_VERSION",
    "TIMING_PRIORITY_SCHEMA_ID",
    "TIMING_PRIORITY_SIDE_IDS",
    "TimingPriorityClaim",
    "apply_timing_priority_waterfall",
    "build_timing_priority_composition_payload",
    "validate_timing_priority_composition_payload",
]
