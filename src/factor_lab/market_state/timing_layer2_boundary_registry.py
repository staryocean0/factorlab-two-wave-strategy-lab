# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Current Layer 2 causal/offline boundary after strategy-effect migration."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, cast

from factor_lab.core.errors import ValidationError

SCHEMA_ID: Final = "timing_layer2_measurement_plane@2.3"
CLASS_ORDER: Final = (
    "causal_feature_provider",
    "offline_target_or_research_material",
    "definition_compatibility_discovery",
    "migrated_to_layer3",
)

LEGACY_AND_CURRENT_ASSET_IDS: Final = (
    "unified_kline_attribute_v3",
    "all_frequency_timing_v2_1",
    "cross_frequency_opportunity_v2",
    "future_kline_property_provider",
    "paper_kernel_timeseries",
    "market_state_foundation_facts",
    "empirical_formula_registry",
    "six_axis_common_market_state",
    "tool_conditioned_relationships",
    "tool_attribute_relationship_maps",
    "group_correlation_market_attributes",
    "trend_continuity_diagnostic",
    "kline_indicators_bdci",
    "visual_structure_endpoint_channel",
    "volatility_continuous_features",
    "cloudridge_daily_attributes_legacy",
    "attribute_pool_kline_four_pools",
    "timing_layer2_option_volatility",
)

CAUSAL_PROVIDER_ASSETS: Final = (
    "future_kline_property_provider",
    "paper_kernel_timeseries",
    "market_state_foundation_facts",
    "six_axis_common_market_state",
    "group_correlation_market_attributes",
    "trend_continuity_diagnostic",
    "kline_indicators_bdci",
    "visual_structure_endpoint_channel",
    "volatility_continuous_features",
    "timing_layer2_option_volatility",
)
OFFLINE_MATERIAL_ASSETS: Final = (
    "unified_kline_attribute_v3",
    "cross_frequency_opportunity_v2",
)
DEFINITION_COMPATIBILITY_ASSETS: Final = (
    "all_frequency_timing_v2_1",
    "empirical_formula_registry",
    "cloudridge_daily_attributes_legacy",
    "attribute_pool_kline_four_pools",
)
MIGRATED_TO_LAYER3_ASSETS: Final = (
    "tool_conditioned_relationships",
    "tool_attribute_relationship_maps",
)

CAUSAL_PROVIDER_FORBIDDEN_EXACT_FIELDS: Final = frozenset(
    {
        "strategy_id",
        "tool_id",
        "target_position",
        "action_role",
        "long_capture_value",
        "cash_avoidance_value",
        "long_trade_outcome",
        "cash_episode_outcome",
        "selected_strategy",
        "selected_tool",
    }
)
CAUSAL_PROVIDER_FORBIDDEN_TOKENS: Final = (
    "strategy_pnl",
    "strategy_return",
    "account_pnl",
    "profitability_gate",
    "tool_effect",
)
RUNTIME_FEATURE_FORBIDDEN_TOKENS: Final = (
    "future_",
    "oracle",
    "target",
    "winner",
    "lookahead",
)


def build_layer2_boundary_registry() -> dict[str, object]:
    return {
        "schema_id": SCHEMA_ID,
        "measurement_plane_id": "timing_layer2_measurement_plane_v2_causal_offline_split",
        "status": "current_strategy_independent_measurement_and_attribute_forecast_only",
        "parent": "timing_layer2_measurement_plane@2.2",
        "class_order": list(CLASS_ORDER),
        "classes": {
            "causal_feature_provider": {
                "asset_ids": list(CAUSAL_PROVIDER_ASSETS),
                "successor_components": ["timing_layer2_all_frequency_measurements@1.0"],
                "runtime_feature_output_allowed": True,
                "strategy_or_tool_effect_inputs_allowed": False,
                "strategy_selection_authority": False,
            },
            "offline_target_or_research_material": {
                "asset_ids": list(OFFLINE_MATERIAL_ASSETS),
                "runtime_feature_output_allowed": False,
                "may_train_strategy_independent_attribute_forecast": True,
                "oracle_or_future_columns_must_remain_offline": True,
                "strategy_selection_authority": False,
            },
            "definition_compatibility_discovery": {
                "asset_ids": list(DEFINITION_COMPATIBILITY_ASSETS),
                "runtime_feature_output_allowed": False,
                "current_successor_for_all_frequency": "timing_layer2_all_frequency_measurements@1.0",
                "strategy_selection_authority": False,
            },
            "migrated_to_layer3": {
                "asset_ids": list(MIGRATED_TO_LAYER3_ASSETS),
                "destination": "timing_layer3_strategy_conditional_effect_research@1.0",
                "Layer2_authority": False,
            },
        },
        "future_property_split": {
            "offline_training_targets": [
                "future_log_realized_variance",
                "future_log_close_path_range",
                "future_log_noise_inflation_1m_to_5m",
                "future_log_path_inefficiency",
                "future_log_jump_burden",
            ],
            "causal_runtime_output": "FuturePathForecastCardV2",
            "runtime_future_reads": 0,
            "direction_or_strategy_forecast": False,
        },
        "all_frequency_split": {
            "legacy_mixed_asset": "all_frequency_timing_v2_1",
            "layer2": "timing_layer2_all_frequency_measurements@1.0",
            "layer3": "timing_layer3_all_frequency_strategy_diagnostics@1.0",
            "layer4": "timing_layer4_all_frequency_execution@1.0",
            "legacy_formula_mutation": False,
        },
        "legacy_asset_count": len(LEGACY_AND_CURRENT_ASSET_IDS),
        "strategy_formula_mutation": False,
        "strategy_runtime_mutation": False,
        "fresh_oos": False,
        "authority": {
            "measurement": True,
            "strategy_selection": False,
            "parameter_selection": False,
            "routing": False,
            "production": False,
        },
    }


def validate_layer2_causal_input_columns(columns: Sequence[str]) -> None:
    lowered = tuple(str(column).lower() for column in columns)
    forbidden = sorted(
        column
        for column in lowered
        if column in CAUSAL_PROVIDER_FORBIDDEN_EXACT_FIELDS
        or any(token in column for token in CAUSAL_PROVIDER_FORBIDDEN_TOKENS)
    )
    if forbidden:
        raise ValidationError(f"Layer 2 causal provider consumed strategy/tool-effect fields: {forbidden}")


def validate_layer2_runtime_feature_columns(columns: Sequence[str]) -> None:
    forbidden = sorted(
        str(column)
        for column in columns
        if any(token in str(column).lower() for token in RUNTIME_FEATURE_FORBIDDEN_TOKENS)
    )
    if forbidden:
        raise ValidationError(f"Layer 2 runtime output leaked offline target/oracle fields: {forbidden}")


def validate_layer2_boundary_registry(
    payload: Mapping[str, object], *, project_root: Path
) -> dict[str, object]:
    if payload.get("schema_id") != SCHEMA_ID:
        raise ValidationError("Layer 2 boundary registry schema drifted")
    if tuple(cast(list[object], payload.get("class_order", []))) != CLASS_ORDER:
        raise ValidationError("Layer 2 boundary class order drifted")
    classes = payload.get("classes")
    if not isinstance(classes, Mapping) or set(classes) != set(CLASS_ORDER):
        raise ValidationError("Layer 2 boundary requires four exclusive classes")
    categorized: list[str] = []
    for class_id in CLASS_ORDER:
        item = classes.get(class_id)
        if not isinstance(item, Mapping):
            raise ValidationError(f"Layer 2 boundary class is invalid: {class_id}")
        assets = item.get("asset_ids")
        if not isinstance(assets, list) or not all(isinstance(value, str) for value in assets):
            raise ValidationError(f"Layer 2 boundary asset list is invalid: {class_id}")
        categorized.extend(cast(list[str], assets))
    if len(categorized) != len(LEGACY_AND_CURRENT_ASSET_IDS) or set(categorized) != set(LEGACY_AND_CURRENT_ASSET_IDS):
        raise ValidationError("Layer 2 boundary does not classify the complete 18-asset denominator once")
    if len(set(categorized)) != len(categorized):
        raise ValidationError("Layer 2 boundary classes overlap")
    if set(MIGRATED_TO_LAYER3_ASSETS).intersection(CAUSAL_PROVIDER_ASSETS):
        raise ValidationError("strategy-conditional assets remain Layer 2 causal providers")
    for relative in (
        "src/factor_lab/market_state/timing_layer2_all_frequency_measurements.py",
        "src/factor_lab/strategy/research/timing/conditional_effect_research.py",
        "src/factor_lab/strategy/research/timing/all_frequency_strategy_diagnostics.py",
        "src/factor_lab/market_state/timing_layer4_all_frequency_execution.py",
    ):
        if not (project_root / relative).is_file():
            raise ValidationError(f"Layer 2/3 boundary successor source missing: {relative}")
    authority = payload.get("authority")
    if not isinstance(authority, Mapping) or authority.get("measurement") is not True:
        raise ValidationError("Layer 2 measurement authority is missing")
    if any(bool(value) for key, value in authority.items() if key != "measurement"):
        raise ValidationError("Layer 2 boundary opened non-measurement authority")
    return {
        "status": "passed",
        "classified_asset_count": len(categorized),
        "causal_provider_count": len(CAUSAL_PROVIDER_ASSETS),
        "offline_material_count": len(OFFLINE_MATERIAL_ASSETS),
        "definition_compatibility_count": len(DEFINITION_COMPATIBILITY_ASSETS),
        "migrated_to_layer3_count": len(MIGRATED_TO_LAYER3_ASSETS),
        "production_authority": False,
    }


__all__ = [
    "CAUSAL_PROVIDER_ASSETS",
    "CLASS_ORDER",
    "LEGACY_AND_CURRENT_ASSET_IDS",
    "MIGRATED_TO_LAYER3_ASSETS",
    "SCHEMA_ID",
    "build_layer2_boundary_registry",
    "validate_layer2_boundary_registry",
    "validate_layer2_causal_input_columns",
    "validate_layer2_runtime_feature_columns",
]
