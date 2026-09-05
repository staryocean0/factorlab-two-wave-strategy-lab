# pyright: reportAny=false, reportArgumentType=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Generic Layer 3 state-adapter and owner-waterfall orchestration kernel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_priority_composition import (
    TIMING_PRIORITY_SIDE_IDS,
    TimingPriorityClaim,
    apply_timing_priority_waterfall,
)
from factor_lab.market_state.tool_registry_v1_5 import CURRENT_TOOL_IDS

ORCHESTRATION_SCHEMA_ID: Final[str] = "timing_layer3_orchestration_kernel@1.0"


@dataclass(frozen=True, slots=True)
class StateAdapterContract:
    adapter_id: str
    input_measurement_refs: tuple[str, ...]
    output_state_domain: tuple[str, ...]
    parameter_contract_ref: str
    replaceable_by_layer2_measurement: bool = True
    position_output: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if not self.adapter_id or not self.input_measurement_refs or not self.output_state_domain:
            raise ValidationError("Layer 3 state adapter identity is incomplete")
        if not self.parameter_contract_ref or self.position_output or self.production_authority:
            raise ValidationError("Layer 3 state adapter cannot emit position or production authority")


@dataclass(frozen=True, slots=True)
class OwnerProfile:
    profile_id: str
    strategy_plugin_id: str
    claim_tool_id: str
    side_id: str
    priority_rank: int
    state_adapter_id: str
    formula_contract_ref: str
    formula_digest: str
    installed: bool
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.claim_tool_id not in CURRENT_TOOL_IDS:
            raise ValidationError("Layer 3 owner profile tool is outside the 15-tool language")
        if self.side_id not in TIMING_PRIORITY_SIDE_IDS or self.priority_rank < 1:
            raise ValidationError("Layer 3 owner profile side/rank is invalid")
        if not all(
            value.strip()
            for value in (
                self.profile_id,
                self.strategy_plugin_id,
                self.state_adapter_id,
                self.formula_contract_ref,
                self.formula_digest,
            )
        ):
            raise ValidationError("Layer 3 owner profile identity is incomplete")
        if self.production_authority:
            raise ValidationError("Layer 3 owner profile cannot grant production authority")


def apply_layer3_owner_waterfall(
    index: pd.Index,
    *,
    side_id: str,
    profiles: tuple[OwnerProfile, ...],
    eligibility_by_profile: dict[str, pd.Series],
) -> pd.DataFrame:
    """Apply installed profiles without importing any concrete strategy formula."""

    installed = tuple(profile for profile in profiles if profile.installed)
    if not installed:
        return _empty_result(index, side_id=side_id)
    profile_ids = tuple(profile.profile_id for profile in installed)
    if len(set(profile_ids)) != len(profile_ids) or set(eligibility_by_profile) != set(profile_ids):
        raise ValidationError("Layer 3 installed profiles and eligibility inputs differ")
    tool_ids = tuple(profile.claim_tool_id for profile in installed)
    if len(set(tool_ids)) != len(tool_ids):
        raise ValidationError("Layer 3 installed owner profiles must have unique claim tools per side")
    claims = tuple(
        TimingPriorityClaim(
            tool_id=profile.claim_tool_id,
            side_id=profile.side_id,
            priority_rank=profile.priority_rank,
            state_id=profile.state_adapter_id,
            eligible=eligibility_by_profile[profile.profile_id],
        )
        for profile in installed
    )
    result = apply_timing_priority_waterfall(index, side_id=side_id, claims=claims)
    plugin_by_tool = {profile.claim_tool_id: profile.strategy_plugin_id for profile in installed}
    profile_by_tool = {profile.claim_tool_id: profile.profile_id for profile in installed}
    result["responsible_plugin_id"] = result["responsible_tool_id"].map(plugin_by_tool).fillna("unassigned")
    result["responsible_profile_id"] = result["responsible_tool_id"].map(profile_by_tool).fillna("unassigned")
    result.attrs["timing_layer_contract"] = orchestration_contract()
    return result


def orchestration_contract() -> dict[str, object]:
    return {
        "schema_id": ORCHESTRATION_SCHEMA_ID,
        "imports_concrete_strategy_implementations": False,
        "outputs": [
            "responsible_tool_id",
            "responsible_plugin_id",
            "responsible_profile_id",
            "claimed",
            "remaining_unassigned",
        ],
        "position_output": False,
        "strategy_formula_mutation": False,
        "production_authority": False,
    }


def _empty_result(index: pd.Index, *, side_id: str) -> pd.DataFrame:
    if side_id not in TIMING_PRIORITY_SIDE_IDS or index.empty or index.has_duplicates:
        raise ValidationError("Layer 3 empty orchestration input is invalid")
    result = pd.DataFrame(
        {
            "priority_side_id": side_id,
            "responsible_tool_id": "unassigned",
            "responsible_state_id": "unassigned",
            "responsible_priority_rank": pd.Series(pd.NA, index=index, dtype="Int64"),
            "claimed": False,
            "remaining_unassigned": True,
            "responsible_plugin_id": "unassigned",
            "responsible_profile_id": "unassigned",
        },
        index=index,
    )
    result.attrs["timing_layer_contract"] = orchestration_contract()
    return result


__all__ = [
    "ORCHESTRATION_SCHEMA_ID",
    "OwnerProfile",
    "StateAdapterContract",
    "apply_layer3_owner_waterfall",
    "orchestration_contract",
]
