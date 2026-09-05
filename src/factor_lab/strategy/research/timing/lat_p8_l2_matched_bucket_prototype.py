"""Unfinished CSI1000 P8 Layer-2-conditioned LAT prototype.

This is strategy research / a semi-finished prototype. It is not Layer 2
infrastructure, not a Layer 3 installed plugin, and not a registered usable
strategy. Layer 4 may consume its result-free family through
StrategyForecastBundle@2.0; this module does not select contracts or a winner.
"""

from __future__ import annotations

from typing import Final, Literal

from factor_lab.core.errors import ValidationError

SCHEMA_ID: Final[str] = "csi1000_lat_p8_l2_matched_bucket_prototype@1.1"
PARENT_SCHEMA_ID: Final[str] = "csi1000_lat_p8_l2_matched_bucket_prototype@1.0"
STRATEGY_ID: Final[str] = "csi1000_lat_p8_l2_matched_bucket_prototype"
STRATEGY_VERSION: Final[str] = "1.1"
FOUR_LAYER_ROLE: Final[str] = "layer3_strategy_research"
LIFECYCLE: Final[str] = "unfinished_strategy_prototype"
POOL: Final[str] = "semi_finished_strategy_research"
COMMON_ROOT: Final[str] = "P8_bilateral__lifecycle_root"
CARRIER_ID: Final[str] = "000852.SH"
CLOCK: Final[str] = "1m_official"
FILL_RULE: Final[str] = "next_tradable_after_bar_close"
PARAMETER_FAMILY_ID: Final[str] = "csi1000_lat_p8_l2_matched_bucket_family_v1"
RETURN_MAX_ID: Final[str] = "csi1000_lat_p8_l2_return_max_v1"
MEAN_TRADE_MAX_ID: Final[str] = "csi1000_lat_p8_l2_mean_trade_max_v1"
PARAMETER_CANDIDATE_IDS: Final[tuple[str, str]] = (RETURN_MAX_ID, MEAN_TRADE_MAX_ID)
RECOMMENDED_GRID: Final[tuple[int, int, int]] = (3, 2, 2)
HIGH_VOL_BIN: Final[int] = 2
LOW_LONG_BIN: Final[int] = 0
CUTPOINT_FREEZE: Final[str] = "2016-12-31"
DEVELOPMENT_INTERVAL: Final[str] = "2015-01-05/2023-12-31"
UNREAD_AFTER: Final[str] = "2023-12-31"
LAYER4_ADAPTER_SOURCE: Final[str] = (
    "src/factor_lab/strategy/research/timing/lat_p8_l2_matched_bucket_layer4_adapter.py"
)
LAYER4_ASSEMBLY: Final[str] = (
    "docs/ops/csi1000_lat_p8_l2_matched_bucket_four_layer_reference_assembly@1.0.json"
)
ExitMode = Literal["centre", "opposite_rail", "fast_adverse_turn"]

# Frozen 3x2x2 cutpoints from the consumed 2015-2023 V3 materials.
# Volatility uses the 3-bin sensitivity edges; long-efficiency and reversal
# keep the 2-bin primary edges. These are entry-time state, not calendar rules.
FROZEN_EDGES: Final[dict[str, tuple[float, ...]]] = {
    "vol": (0.0005309756594784494, 0.0012328865841901844),
    "long_pe": (0.5612507836180223,),
    "reversal_pe": (0.18629238938293718,),
}


def expected_cell_ids() -> tuple[str, ...]:
    return tuple(
        f"V{vol}L{long_bin}R{reversal}"
        for vol in range(RECOMMENDED_GRID[0])
        for long_bin in range(RECOMMENDED_GRID[1])
        for reversal in range(RECOMMENDED_GRID[2])
    )


def cell_id(vol_bin: int, long_bin: int, reversal_bin: int) -> str:
    if not (0 <= vol_bin < RECOMMENDED_GRID[0]):
        raise ValidationError("volatility bin escaped the frozen 3x2x2 grid")
    if not (0 <= long_bin < RECOMMENDED_GRID[1]):
        raise ValidationError("long-efficiency bin escaped the frozen 3x2x2 grid")
    if not (0 <= reversal_bin < RECOMMENDED_GRID[2]):
        raise ValidationError("reversal bin escaped the frozen 3x2x2 grid")
    return f"V{vol_bin}L{long_bin}R{reversal_bin}"


def return_max_exit_mode(vol_bin: int, long_bin: int) -> ExitMode:
    """Width 0.75 is the default; fast adverse exit is only that one cell."""

    if vol_bin == HIGH_VOL_BIN and long_bin == LOW_LONG_BIN:
        return "fast_adverse_turn"
    return "centre"


def candidate_formula(candidate_id: str) -> dict[str, object]:
    if candidate_id == RETURN_MAX_ID:
        return {
            "candidate_id": RETURN_MAX_ID,
            "objective": "ReturnMax",
            "common_root": COMMON_ROOT,
            "width_scale_on_root": 0.75,
            "default_exit_mode": "centre",
            "state_conditioned_exit": {
                "cell_predicate": "vol_bin==2 and long_bin==0",
                "exit_mode": "fast_adverse_turn",
                "reversal_bin_has_runtime_authority": False,
            },
            "twelve_buckets_are": "entry_time_state_only",
            "calendar_runtime_rules": False,
        }
    if candidate_id == MEAN_TRADE_MAX_ID:
        return {
            "candidate_id": MEAN_TRADE_MAX_ID,
            "objective": "MeanTradeMax",
            "common_root": COMMON_ROOT,
            "width_scale_on_root": 1.0,
            "default_exit_mode": "opposite_rail",
            "state_conditioned_exit": None,
            "twelve_buckets_are": "entry_time_state_only",
            "calendar_runtime_rules": False,
        }
    raise ValidationError(f"unknown P8 bucket candidate: {candidate_id}")


def prototype_contract() -> dict[str, object]:
    return {
        "schema_id": SCHEMA_ID,
        "parent_schema_id": PARENT_SCHEMA_ID,
        "strategy_id": STRATEGY_ID,
        "strategy_version": STRATEGY_VERSION,
        "four_layer_role": FOUR_LAYER_ROLE,
        "lifecycle": LIFECYCLE,
        "pool": POOL,
        "layer2_infrastructure": False,
        "layer2_measurement_authority": False,
        "runtime_installation_allowed": False,
        "layer3_plugin_installed": False,
        "common_root": COMMON_ROOT,
        "carrier_id": CARRIER_ID,
        "clock": CLOCK,
        "fill_rule": FILL_RULE,
        "cost_model": "cost_free_index_gross_log",
        "lookback_ladder": {"vol_over_P": 1.0, "reversal_over_P": 8.0, "long_pe_over_P": 80.0},
        "recommended_grid": list(RECOMMENDED_GRID),
        "frozen_edges": {key: list(value) for key, value in FROZEN_EDGES.items()},
        "parameter_family_id": PARAMETER_FAMILY_ID,
        "parameter_candidate_ids": list(PARAMETER_CANDIDATE_IDS),
        "selected_parameter_id": None,
        "specified_contract_symbol": None,
        "candidate_formulas": [candidate_formula(item) for item in PARAMETER_CANDIDATE_IDS],
        "scoring_interval": DEVELOPMENT_INTERVAL,
        "cutpoint_freeze": CUTPOINT_FREEZE,
        "unread_after": UNREAD_AFTER,
        "data_roles": {
            "2015-01-05/2023-12-31": "development_material",
            "2024-01-01/2024-12-31": "unread_reserved_challenge",
            "2025-01-01/2026-12-31": "sealed_aggregate_lockbox",
        },
        "layer4_adapter_source": LAYER4_ADAPTER_SOURCE,
        "layer4_assembly": LAYER4_ASSEMBLY,
        "layer4_forecast_contract": "StrategyForecastBundle@2.0",
        "layer4_instrument": "MO",
        "layer4_may_specify_contract": False,
        "layer4_economic_session_authorized": False,
        "fresh_oos": False,
        "registered_use_authority": False,
        "parameter_selection_authority": False,
        "paper_trading_authority": False,
        "live_trading_authority": False,
        "production_authority": False,
        "evidence": {
            "v1_clock_mismatch": "docs/ops/evidence/market_state_lat_hf_l2_triple_bucket_dual_objective_v1_20260903/",
            "v2_matched": "docs/ops/evidence/market_state_lat_hf_l2_matched_bucket_dual_objective_v2_20260903/",
            "v3_2015_2023": "docs/ops/evidence/market_state_lat_hf_l2_matched_bucket_dual_objective_v3_2015_2023_20260903/",
            "layer4_adapter": "docs/ops/evidence/csi1000_lat_p8_l2_matched_bucket_layer4_adapter_v1_20260903/",
        },
        "handoff_prompt": "docs/user/csi1000_lat_p8_l2_matched_bucket_prototype_external_ai_prompt.md",
        "layer4_adapter_workflow": "docs/user/csi1000_lat_p8_l2_matched_bucket_layer4_adapter_workflow.md",
        "layer4_mo_account_prompt": "docs/user/csi1000_lat_p8_l2_matched_bucket_layer4_mo_account_external_ai_prompt.md",
    }


__all__ = [
    "CARRIER_ID",
    "CLOCK",
    "COMMON_ROOT",
    "CUTPOINT_FREEZE",
    "DEVELOPMENT_INTERVAL",
    "FILL_RULE",
    "FOUR_LAYER_ROLE",
    "FROZEN_EDGES",
    "HIGH_VOL_BIN",
    "LAYER4_ADAPTER_SOURCE",
    "LAYER4_ASSEMBLY",
    "LIFECYCLE",
    "LOW_LONG_BIN",
    "MEAN_TRADE_MAX_ID",
    "PARAMETER_CANDIDATE_IDS",
    "PARAMETER_FAMILY_ID",
    "PARENT_SCHEMA_ID",
    "POOL",
    "RECOMMENDED_GRID",
    "RETURN_MAX_ID",
    "SCHEMA_ID",
    "STRATEGY_ID",
    "STRATEGY_VERSION",
    "UNREAD_AFTER",
    "candidate_formula",
    "cell_id",
    "expected_cell_ids",
    "prototype_contract",
    "return_max_exit_mode",
]
