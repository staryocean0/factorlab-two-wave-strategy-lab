# pyright: reportAny=false, reportArgumentType=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Historical Layer 2/3 split facades retained for compatibility.

The four-layer timing inventory deliberately keeps scientific implementations
in their existing modules.  This module gives the formerly mixed surfaces two
separate public identities:

* Layer 2 measures continuous K-line properties and never emits ownership,
  action, or position decisions.
* Layer 3a registers tools and evaluation exams.
* Layer 3b applies temporary state/remainder policies to Layer 2 measurements.

The facades compose existing formulas; they do not copy or modify them.  Their
3a/3b classification is superseded for strategy authority by
``timing_strategy_identity_registry@2.0``.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final, cast

import numpy as np
import pandas as pd

from factor_lab.cloudridge.paper_kernel import build_paper_kernel_panel
from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_all_frequency_infrastructure import (
    SCHEMA_ID as ALL_FREQUENCY_SCHEMA_ID,
)
from factor_lab.market_state.timing_evaluation_platform import (
    SCHEMA_ID as EVALUATION_PLATFORM_SCHEMA_ID,
)
from factor_lab.market_state.timing_six_axis import build_timing_six_axis_panel
from factor_lab.market_state.tool_registry_v1_5 import (
    CURRENT_TOOL_IDS,
    TOOL_REGISTRY_V1_5_SCHEMA_ID,
    TOOL_REGISTRY_V1_5_VERSION,
)
from factor_lab.market_state.volatility_regime_recognizer_battle import (
    INVALID_STATE,
    apply_confirmation_hysteresis,
    build_volatility_feature_panel,
    quantile_states,
)

REGISTRY_SCHEMA_ID: Final[str] = "timing_layer2_3_registry@1.0"
REGISTRY_ID: Final[str] = "timing_layer2_measurement_layer3_strategy@1.0"
FROZEN_STEP_A_INVENTORY: Final[str] = "docs/ops/timing_infrastructure_four_layer_inventory@1.0.json"

LAYER2_ASSET_IDS: Final[tuple[str, ...]] = (
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
)

LAYER3A_ASSET_IDS: Final[tuple[str, ...]] = (
    "tool_registry_v1_5",
    "tool_relative_coupling",
    "evaluation_platform_v4",
    "paper_kernel_tool_identity",
    "formula_derived_tool_inversion",
)

LAYER3B_ASSET_IDS: Final[tuple[str, ...]] = (
    "priority_composition_waterfall",
    "timing_strategy_router_v4",
    "explosive_layer_v3",
    "crash_rebound_current_best",
    "timing_research_samples_rN",
    "volatility_three_state_machine",
    "formula_derived_joint_state_machine",
)

SPLIT_IDENTITIES: Final[tuple[tuple[str, str, str], ...]] = (
    (
        "six_axis_unified_catalog",
        "six_axis_common_market_state",
        "tool_relative_coupling",
    ),
    ("paper_kernel", "paper_kernel_timeseries", "paper_kernel_tool_identity"),
    (
        "volatility_regime_recognizer_nested_v2",
        "volatility_continuous_features",
        "volatility_three_state_machine",
    ),
    (
        "formula_derived_v3",
        "formula_derived_tool_inversion",
        "formula_derived_joint_state_machine",
    ),
)
ATTRIBUTE_POOL_CROSS_LANE_SPLIT: Final[tuple[str, str, str]] = (
    "attribute_pool_v1",
    "attribute_pool_kline_four_pools",
    "attribute_pool_derivatives_overlay",
)

EPHEMERAL_REPLACEMENT_NOTICE: Final[str] = "replaceable_by_more_complete_layer2_measurement_not_a_long_term_foundation"
_LAYER2_FORBIDDEN_COLUMN_TOKENS: Final[tuple[str, ...]] = (
    "state",
    "position",
    "claim",
    "action",
    "responsible_tool",
)
_LAYER2_FORBIDDEN_EXACT_COLUMNS: Final[frozenset[str]] = frozenset(
    {"future_rv_16", "target", "label", "selected_strategy", "selected_frequency"}
)


def layer2_measurement_contract() -> dict[str, object]:
    """Return the reusable measurement-only public contract."""

    return {
        "schema_id": "timing_layer2_measurement@1.0",
        "registry_id": REGISTRY_ID,
        "four_layer_role": "layer2_kline_measurement",
        "asset_ids": list(LAYER2_ASSET_IDS),
        "outputs": [
            "continuous_attributes",
            "causal_relationships",
            "frequency_surfaces",
            "diagnostics",
        ],
        "ownership_outputs_forbidden": True,
        "position_outputs_forbidden": True,
        "strategy_or_frequency_selection_forbidden": True,
        "measurement_authority": True,
        "routing_authority": False,
        "parameter_authority": False,
        "production_authority": False,
    }


def layer3_strategy_contract() -> dict[str, object]:
    """Return the split 3a foundation / 3b temporary-policy contract."""

    return {
        "schema_id": "timing_layer3_strategy@1.0",
        "registry_id": REGISTRY_ID,
        "strategy_foundation": {
            "role": "layer3a_tool_vocabulary_and_evaluation_exam",
            "asset_ids": list(LAYER3A_ASSET_IDS),
            "current_tool_registry": TOOL_REGISTRY_V1_5_VERSION,
            "current_tool_registry_schema": TOOL_REGISTRY_V1_5_SCHEMA_ID,
            "current_tool_count": len(CURRENT_TOOL_IDS),
            "current_evaluation_platform_schema": EVALUATION_PLATFORM_SCHEMA_ID,
            "routing_authority": False,
        },
        "strategy_ephemeral": {
            "role": "layer3b_remainder_state_machine_and_bucket_policy",
            "asset_ids": list(LAYER3B_ASSET_IDS),
            "lifecycle": EPHEMERAL_REPLACEMENT_NOTICE,
            "replaceable_by_layer2_measurement": True,
            "long_term_foundation": False,
        },
        "measurement_authority": False,
        "parameter_authority": False,
        "production_authority": False,
    }


def build_layer2_six_axis_measurements(
    daily_bars: pd.DataFrame,
    *,
    group_attributes: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Adapt the six-axis implementation to the Layer 2 output boundary."""

    result = build_timing_six_axis_panel(
        daily_bars,
        group_attributes=group_attributes,
    )
    return _mark_and_validate_layer2(result, adapter_id="six_axis_measurement@1.0")


def build_layer2_paper_kernel_measurements(
    daily_bars: pd.DataFrame,
    *,
    drop_warmup: bool = False,
) -> pd.DataFrame:
    """Expose the 16-scale paper-kernel time series without its tool route."""

    result = build_paper_kernel_panel(daily_bars, drop_warmup=drop_warmup)
    return _mark_and_validate_layer2(result, adapter_id="paper_kernel_timeseries@1.0")


def build_layer2_volatility_measurements(bars: pd.DataFrame) -> pd.DataFrame:
    """Expose causal continuous volatility features, never the three-state cut.

    The historical recognizer implementation also materializes an evaluation-
    only future target.  The Layer 2 adapter removes that target together with
    every state/action surface before returning the public measurement panel.
    """

    legacy_panel = build_volatility_feature_panel(bars)
    keep = [
        column
        for column in legacy_panel.columns
        if column not in _LAYER2_FORBIDDEN_EXACT_COLUMNS and not any(token in column.lower() for token in _LAYER2_FORBIDDEN_COLUMN_TOKENS)
    ]
    result = legacy_panel.loc[:, keep].copy()
    return _mark_and_validate_layer2(
        result,
        adapter_id="volatility_continuous_features@1.0",
    )


def build_layer3b_volatility_states(
    measurements: pd.DataFrame,
    *,
    confirmations: int = 1,
    minimum_residence: int = 4,
) -> pd.DataFrame:
    """Cut a separate low/normal/high state surface from Layer 2 measurements."""

    required = {"timestamp", "log_rv_fast", "rv_q_low", "rv_q_high"}
    missing = sorted(required.difference(measurements.columns))
    if missing:
        raise ValidationError(f"Layer 3b volatility adapter missing measurements: {missing}")
    if confirmations < 1 or minimum_residence < 1:
        raise ValidationError("Layer 3b hysteresis parameters must be positive")
    raw = quantile_states(
        measurements["log_rv_fast"].to_numpy(float),
        measurements["rv_q_low"].to_numpy(float),
        measurements["rv_q_high"].to_numpy(float),
    )
    state = apply_confirmation_hysteresis(
        raw,
        confirmations=confirmations,
        minimum_residence=minimum_residence,
    )
    output = pd.DataFrame(
        {
            "timestamp": measurements["timestamp"].to_numpy(copy=True),
            "volatility_state_raw": raw,
            "volatility_state": state,
        },
        index=measurements.index,
    )
    allowed = {INVALID_STATE, 0, 1, 2}
    if not set(np.unique(state)).issubset(allowed):
        raise ValidationError("Layer 3b volatility state escaped the three-state domain")
    output.attrs["timing_layer_contract"] = {
        "adapter_id": "volatility_three_state_machine@1.0",
        "four_layer_role": "layer3b_strategy_ephemeral",
        "source": "volatility_continuous_features@1.0",
        "lifecycle": EPHEMERAL_REPLACEMENT_NOTICE,
        "replaceable_by_layer2_measurement": True,
        "long_term_foundation": False,
        "position_output": False,
        "production_authority": False,
    }
    return output


def validate_layer2_measurement_frame(frame: pd.DataFrame) -> None:
    """Reject Layer 2 frames that contain labels, owners, actions, or positions."""

    if frame.empty:
        raise ValidationError("Layer 2 measurement frame must not be empty")
    lowered = {str(column).lower() for column in frame.columns}
    forbidden = sorted(lowered.intersection(_LAYER2_FORBIDDEN_EXACT_COLUMNS))
    forbidden.extend(sorted(column for column in lowered if any(token in column for token in _LAYER2_FORBIDDEN_COLUMN_TOKENS)))
    if forbidden:
        raise ValidationError(f"Layer 2 measurement frame contains strategy/state outputs: {forbidden}")


def validate_timing_layer2_3_registry(
    registry: Mapping[str, object],
    *,
    project_root: Path,
    frozen_inventory: Mapping[str, object],
) -> dict[str, object]:
    """Validate exact Lane 2 coverage, split identities, versions, and authority."""

    if registry.get("schema_id") != REGISTRY_SCHEMA_ID:
        raise ValidationError("Layer 2/3 registry schema drifted")
    if registry.get("registry_id") != REGISTRY_ID or registry.get("current") is not True:
        raise ValidationError("Layer 2/3 registry identity is not current")
    assets = frozen_inventory.get("assets")
    if not isinstance(assets, list):
        raise ValidationError("frozen four-layer inventory has no asset list")
    frozen_groups: dict[str, tuple[str, ...]] = {}
    for layer in ("measurement", "strategy_foundation", "strategy_ephemeral"):
        frozen_groups[layer] = tuple(
            str(asset["asset_id"])
            for asset in assets
            if isinstance(asset, Mapping) and asset.get("owner_lane") == 2 and asset.get("layer") == layer
        )
    expected_groups = {
        "measurement": LAYER2_ASSET_IDS,
        "strategy_foundation": LAYER3A_ASSET_IDS,
        "strategy_ephemeral": LAYER3B_ASSET_IDS,
    }
    if frozen_groups != expected_groups:
        raise ValidationError("Layer 2/3 registry no longer covers the frozen Lane 2 denominator")
    layers = registry.get("layers")
    if not isinstance(layers, Mapping):
        raise ValidationError("Layer 2/3 registry layers are missing")
    for layer, expected in expected_groups.items():
        section = layers.get(layer)
        if not isinstance(section, Mapping) or tuple(section.get("asset_ids", ())) != expected:
            raise ValidationError(f"Layer 2/3 {layer} asset coverage drifted")
    split_rows = registry.get("split_identities")
    if not isinstance(split_rows, list):
        raise ValidationError("Layer 2/3 split identity rows are missing")
    actual_splits = tuple(
        (
            str(row.get("split_from")),
            str(row.get("measurement_or_foundation_identity")),
            str(row.get("foundation_or_ephemeral_identity")),
        )
        for row in split_rows
        if isinstance(row, Mapping)
    )
    if actual_splits != SPLIT_IDENTITIES:
        raise ValidationError("Layer 2/3 split identities drifted")
    cross_lane = registry.get("attribute_pool_cross_lane_split")
    if (
        not isinstance(cross_lane, Mapping)
        or (
            str(cross_lane.get("split_from")),
            str(cross_lane.get("lane2_identity")),
            str(cross_lane.get("lane3_identity")),
        )
        != ATTRIBUTE_POOL_CROSS_LANE_SPLIT
    ):
        raise ValidationError("attribute-pool cross-lane identity drifted")
    versions = registry.get("current_versions")
    if not isinstance(versions, Mapping) or (
        versions.get("tool_registry") != TOOL_REGISTRY_V1_5_VERSION
        or versions.get("tool_registry_schema") != TOOL_REGISTRY_V1_5_SCHEMA_ID
        or versions.get("tool_count") != 15
        or versions.get("evaluation_platform_schema") != EVALUATION_PLATFORM_SCHEMA_ID
        or versions.get("all_frequency_schema") != ALL_FREQUENCY_SCHEMA_ID
    ):
        raise ValidationError("Layer 2/3 current version pins drifted")
    lifecycle = cast(Mapping[str, object], layers["strategy_ephemeral"])
    if (
        lifecycle.get("lifecycle") != EPHEMERAL_REPLACEMENT_NOTICE
        or lifecycle.get("replaceable_by_layer2_measurement") is not True
        or lifecycle.get("long_term_foundation") is not False
    ):
        raise ValidationError("Layer 3b lifecycle must stay temporary and replaceable")
    authority = registry.get("authority")
    if not isinstance(authority, Mapping) or authority.get("production") is not False:
        raise ValidationError("Layer 2/3 registry cannot grant production authority")
    files = registry.get("owned_files")
    if not isinstance(files, list) or not files:
        raise ValidationError("Layer 2/3 registry owned-file ledger is missing")
    for relative in files:
        if not isinstance(relative, str) or not (project_root / relative).is_file():
            raise ValidationError(f"Layer 2/3 owned file is missing: {relative}")
    return {
        "status": "passed",
        "lane2_asset_count": sum(len(items) for items in expected_groups.values()),
        "measurement_asset_count": len(LAYER2_ASSET_IDS),
        "strategy_foundation_asset_count": len(LAYER3A_ASSET_IDS),
        "strategy_ephemeral_asset_count": len(LAYER3B_ASSET_IDS),
        "split_identity_count": len(SPLIT_IDENTITIES) + 1,
        "current_tool_count": len(CURRENT_TOOL_IDS),
        "formula_mutation": False,
        "production_authority": False,
    }


def _mark_and_validate_layer2(frame: pd.DataFrame, *, adapter_id: str) -> pd.DataFrame:
    validate_layer2_measurement_frame(frame)
    frame.attrs["timing_layer_contract"] = {
        "adapter_id": adapter_id,
        "four_layer_role": "layer2_kline_measurement",
        "measurement_authority": True,
        "routing_authority": False,
        "position_output": False,
        "production_authority": False,
    }
    return frame


__all__ = [
    "ATTRIBUTE_POOL_CROSS_LANE_SPLIT",
    "EPHEMERAL_REPLACEMENT_NOTICE",
    "FROZEN_STEP_A_INVENTORY",
    "LAYER2_ASSET_IDS",
    "LAYER3A_ASSET_IDS",
    "LAYER3B_ASSET_IDS",
    "REGISTRY_ID",
    "REGISTRY_SCHEMA_ID",
    "SPLIT_IDENTITIES",
    "build_layer2_paper_kernel_measurements",
    "build_layer2_six_axis_measurements",
    "build_layer2_volatility_measurements",
    "build_layer3b_volatility_states",
    "layer2_measurement_contract",
    "layer3_strategy_contract",
    "validate_layer2_measurement_frame",
    "validate_timing_layer2_3_registry",
]
