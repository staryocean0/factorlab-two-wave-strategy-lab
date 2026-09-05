# pyright: reportAny=false, reportArgumentType=false, reportIndexIssue=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Current Layer 2 measurement-plane contracts and capability validation.

The module describes what FactorLab can measure.  It never selects a timing
tool, frequency, action, or position.  Existing scientific implementations
remain in their owning modules; this is the common coordinate and discovery
surface for their V2 successors.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, Literal, cast

from factor_lab.core.errors import ValidationError

MEASUREMENT_PLANE_SCHEMA_ID: Final[str] = "timing_layer2_measurement_plane@2.0"
MEASUREMENT_PLANE_ID: Final[str] = "timing_layer2_measurement_plane_v2"
COORDINATE_SCHEMA_ID: Final[str] = "Layer2MeasurementCoordinate@1.0"
CAPABILITY_SCHEMA_ID: Final[str] = "Layer2Capability@1.0"

QualityStatus = Literal["ready", "partial", "unavailable", "compatibility"]
BarAuthority = Literal["datahub_wall_clock", "factorlab_shifted_session_clock"]
GapPolicy = Literal[
    "fail_closed",
    "explicit_gap_rows",
    "session_reset",
    "trusted_causal_fill_with_receipt",
]

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

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_OUTPUT_TOKENS: Final[tuple[str, ...]] = (
    "position",
    "claim",
    "action",
    "selected_",
    "tool_owner",
    "responsible_tool",
)


@dataclass(frozen=True, slots=True)
class Layer2MeasurementCoordinate:
    """One causal measurement coordinate with Layer 1 bar authority bound."""

    carrier_id: str
    view_id: str
    physical_horizon: str
    observation_time: datetime
    available_at: datetime
    source_id: str
    source_version: str
    source_receipt_sha256: str
    estimator_id: str
    estimator_version: str
    bar_authority: BarAuthority = "datahub_wall_clock"
    carrier_source_authority: str = "datahub"
    membership_version: str | None = None
    gap_policy: GapPolicy = "fail_closed"
    quality_status: QualityStatus = "ready"
    measurement_authority: bool = True
    routing_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        required = (
            self.carrier_id,
            self.view_id,
            self.physical_horizon,
            self.source_id,
            self.source_version,
            self.estimator_id,
            self.estimator_version,
            self.carrier_source_authority,
        )
        if any(not value.strip() for value in required):
            raise ValidationError("Layer 2 coordinate identity fields must be non-empty")
        if self.observation_time.tzinfo is None or self.available_at.tzinfo is None:
            raise ValidationError("Layer 2 coordinate times must be timezone-aware")
        if self.available_at < self.observation_time:
            raise ValidationError("Layer 2 measurement cannot be available before observation")
        if not _HEX64.fullmatch(self.source_receipt_sha256):
            raise ValidationError("Layer 2 source receipt must be a lowercase SHA-256")
        if self.bar_authority == "factorlab_shifted_session_clock":
            if not self.view_id.startswith("shifted_session_clock"):
                raise ValidationError("FactorLab bar authority is limited to shifted session clock")
        elif self.view_id.startswith("shifted_session_clock"):
            raise ValidationError("shifted session clock must declare its FactorLab exception")
        if self.routing_authority or self.production_authority or not self.measurement_authority:
            raise ValidationError("Layer 2 coordinate cannot grant routing or production authority")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["schema_id"] = COORDINATE_SCHEMA_ID
        payload["observation_time"] = self.observation_time.isoformat()
        payload["available_at"] = self.available_at.isoformat()
        return payload


@dataclass(frozen=True, slots=True)
class Layer2Capability:
    """Machine-readable coverage and gap declaration for one frozen asset."""

    asset_id: str
    family: str
    current_version: str
    granularity: str
    carriers: tuple[str, ...]
    views: tuple[str, ...]
    horizons: tuple[str, ...]
    point_in_time: bool
    incremental: bool
    status: QualityStatus
    known_gaps: tuple[str, ...]
    successor_phase: str
    source_refs: tuple[str, ...]
    measurement_authority: bool = True
    routing_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.asset_id not in LAYER2_ASSET_IDS:
            raise ValidationError(f"unknown Layer 2 capability asset: {self.asset_id}")
        if not self.family or not self.current_version or not self.granularity:
            raise ValidationError("Layer 2 capability identity is incomplete")
        if not self.carriers or not self.views or not self.horizons or not self.source_refs:
            raise ValidationError(f"Layer 2 capability coverage is incomplete: {self.asset_id}")
        if self.status != "ready" and not self.known_gaps:
            raise ValidationError(f"non-ready capability must declare gaps: {self.asset_id}")
        if self.routing_authority or self.production_authority or not self.measurement_authority:
            raise ValidationError("Layer 2 capability cannot grant routing or production authority")

    def to_dict(self) -> dict[str, object]:
        return {"schema_id": CAPABILITY_SCHEMA_ID, **asdict(self)}


def layer2_capabilities() -> tuple[Layer2Capability, ...]:
    """Return the exact frozen 17-asset denominator with honest current gaps."""

    common_views = ("registered_layer1_views",)
    return (
        Layer2Capability(
            "unified_kline_attribute_v3",
            "core_kline_measurement",
            "unified_kline_attribute_v3",
            "annual_carrier_view_atlas",
            ("cloudridge", "six_market_indices"),
            common_views,
            ("2d", "4d", "8d", "16d", "annual"),
            False,
            False,
            "partial",
            (
                "annual_atlas_not_rolling_pit_provider",
                "successor_must_bind_layer1_datahub_bar_receipts",
                "spectral_columns_embedded_in_transitional_v3",
            ),
            "B",
            (
                "docs/ops/market_state_unified_kline_attribute_infrastructure_whitepaper.md",
                "artifacts/market_state/unified_kline_attribute_infrastructure_v3_20260824/attribute_atlas/manifest.json",
            ),
        ),
        Layer2Capability(
            "all_frequency_timing_v2_1",
            "frequency_neutral_diagnostics",
            "market_state_all_frequency_timing_infrastructure@2.1",
            "on_demand_panel_diagnostics",
            ("generic_price_panel",),
            ("3s", "1m", "5m", "15m", "30m", "60m", "daily"),
            ("caller_declared",),
            True,
            False,
            "partial",
            (
                "strategy_ledger_metrics_not_generic_price_features",
                "component_bdci_not_in_raw_price_panel",
                "execution_preflight_metadata_must_not_become_layer2_routing",
            ),
            "B",
            ("src/factor_lab/market_state/timing_all_frequency_infrastructure.py",),
        ),
        Layer2Capability(
            "cross_frequency_opportunity_v2",
            "cross_frequency_research_atlas",
            "market_state_cross_frequency_opportunity@2.0",
            "retrospective_opportunity_and_stability_atlas",
            ("csi1000",),
            ("continuous_5m_grid",),
            ("P16_to_P3840_25_coordinates",),
            False,
            False,
            "partial",
            (
                "oracle_products_are_not_runtime_features",
                "causal_phase_graph_not_exposed_as_streaming_provider",
                "single_carrier_scope",
            ),
            "D",
            ("docs/ops/cross_frequency_opportunity_stability_registry@2.0.json",),
        ),
        Layer2Capability(
            "future_kline_property_provider",
            "future_path_distribution",
            "csi1000_future_kline_property_provider@1.0",
            "prefix_fit_forecast_card",
            ("csi1000",),
            ("1m", "5m"),
            ("caller_declared",),
            True,
            True,
            "partial",
            (
                "future_path_efficiency_unsupported",
                "single_carrier_scope",
                "normal_residual_quantiles_not_full_calibration",
            ),
            "E",
            ("docs/ops/csi1000_future_kline_property_provider@1.0.json",),
        ),
        Layer2Capability(
            "paper_kernel_timeseries",
            "paper_kernel_response",
            "cloudridge_paper_kernel_multiscale_timeseries@1.2",
            "daily_point_timeseries_and_partial_cross_carrier_pool",
            ("cloudridge", "partial_seven_carrier"),
            ("daily", "partial_15m"),
            ("s1_s2_s3_s4_s5_s10_s15_s20_s30_s60_s100_s150_s200_s300_s400_s500",),
            True,
            False,
            "partial",
            ("full_seven_by_fourteen_expansion_open", "legacy_offset_products_read_only"),
            "D",
            (
                "src/factor_lab/cloudridge/paper_kernel.py",
                "artifacts/market_state/attribute_pool_infrastructure_v1/current.json",
            ),
        ),
        Layer2Capability(
            "market_state_foundation_facts",
            "foundation_fact_bundle",
            "market_state_foundation_A0_D",
            "daily_and_60m_fact_bundle",
            ("cloudridge",),
            ("1d", "60m"),
            ("registered_foundation_windows",),
            True,
            True,
            "partial",
            ("single_carrier_legacy_scope", "not_on_common_layer2_coordinate"),
            "A",
            ("docs/ops/market_state_foundation_whitepaper.md",),
        ),
        Layer2Capability(
            "empirical_formula_registry",
            "empirical_measurement_identity",
            "market_state_empirical_formula_registry@1.0",
            "contract_only",
            ("generic",),
            ("formula_declared",),
            ("formula_declared",),
            False,
            False,
            "partial",
            ("only_one_registered_formula", "not_a_materialized_measurement_provider"),
            "F",
            ("src/factor_lab/market_state/empirical_formula_registry.py",),
        ),
        Layer2Capability(
            "six_axis_common_market_state",
            "semantic_market_state_projection",
            "market_state_timing_six_axis@1.0",
            "daily_point_timeseries",
            ("cloudridge", "optional_group_context"),
            ("daily",),
            ("20d", "50d", "60d", "100d", "120d", "250d", "500d"),
            True,
            True,
            "partial",
            ("daily_cloudridge_centric", "duplicates_core_measurement_formulas"),
            "B",
            ("src/factor_lab/market_state/timing_six_axis.py",),
        ),
        Layer2Capability(
            "tool_conditioned_relationships",
            "measurement_relationship_research",
            "market_state_tool_conditioned_relationship_research@1.0",
            "oos_research_bundle",
            ("registered_research_carriers",),
            ("study_specific",),
            ("study_specific",),
            False,
            False,
            "partial",
            ("research_bundle_not_runtime_measurement", "tool_conditioning_is_consumer_specific"),
            "F",
            ("src/factor_lab/market_state/tool_conditioned_relationships.py",),
        ),
        Layer2Capability(
            "tool_attribute_relationship_maps",
            "static_relationship_map",
            "market_state_tool_affinity_v1",
            "contract_only",
            ("generic",),
            ("static",),
            ("static",),
            False,
            False,
            "partial",
            ("static_map_not_observed_measurement", "current_15_tool_alignment_pending"),
            "F",
            ("src/factor_lab/market_state/tool_affinity.py",),
        ),
        Layer2Capability(
            "group_correlation_market_attributes",
            "cross_sectional_common_mode",
            "market_state_group_correlation_current",
            "daily_point_timeseries",
            ("all_market", "fixed_manufacturing_core"),
            ("daily",),
            ("20d", "60d", "120d"),
            True,
            True,
            "ready",
            (),
            "C",
            ("docs/ops/group_correlation_market_state_whitepaper.md",),
        ),
        Layer2Capability(
            "trend_continuity_diagnostic",
            "trend_continuity",
            "market_state_trend_continuity_regime@1.0",
            "daily_point_timeseries",
            ("cloudridge",),
            ("daily",),
            ("100d_to_500d_authority_250d",),
            True,
            True,
            "partial",
            ("cloudridge_authority_not_cross_carrier_constant", "diagnostic_window_not_general_provider"),
            "B",
            ("src/factor_lab/market_state/trend_continuity_regime.py",),
        ),
        Layer2Capability(
            "kline_indicators_bdci",
            "direction_continuity_primitive",
            "bar_direction_continuity_v1",
            "on_demand_series_primitive",
            ("generic",),
            ("caller_declared",),
            ("caller_declared",),
            True,
            True,
            "partial",
            ("close_to_close_only", "component_direction_provider_missing"),
            "D",
            ("src/factor_lab/indicators/bar_direction_continuity.py",),
        ),
        Layer2Capability(
            "visual_structure_endpoint_channel",
            "causal_price_geometry",
            "endpoint_channel_primitive",
            "on_demand_visual_primitive",
            ("generic",),
            ("caller_declared",),
            ("caller_declared",),
            True,
            False,
            "partial",
            ("five_in_one_governance_incomplete", "terminal_visual_guard_requires_prefix_contract"),
            "C",
            ("src/factor_lab/visual_structure/endpoint_channel.py",),
        ),
        Layer2Capability(
            "volatility_continuous_features",
            "continuous_volatility",
            "volatility_continuous_features@1.0",
            "intraday_point_timeseries_adapter",
            ("generic",),
            ("caller_declared",),
            ("16bar", "64bar", "512bar_reference"),
            True,
            True,
            "partial",
            ("fixed_bar_windows_not_physical_horizon", "historical_implementation_coupled_to_state_battle"),
            "B",
            ("src/factor_lab/market_state/timing_layer2_3_contracts.py",),
        ),
        Layer2Capability(
            "cloudridge_daily_attributes_legacy",
            "legacy_daily_attribute_compatibility",
            "cloudridge_daily_attributes_legacy",
            "daily_legacy_panel",
            ("cloudridge",),
            ("daily",),
            ("20d", "50d", "100d", "200d", "300d", "400d", "500d"),
            True,
            False,
            "compatibility",
            ("legacy_single_carrier_contract", "must_not_parent_new_measurement_families"),
            "F",
            ("src/factor_lab/cloudridge/attributes.py",),
        ),
        Layer2Capability(
            "attribute_pool_kline_four_pools",
            "source_discovery_and_snapshot",
            "market_state_attribute_pool_registry@1.0",
            "content_addressed_source_catalog",
            ("registered_sources",),
            ("source_declared",),
            ("source_declared",),
            False,
            True,
            "partial",
            (
                "source_catalog_not_feature_capability_matrix",
                "documentation_current_snapshot_and_source_count_drift",
                "three_measurement_pools_remain_partial",
            ),
            "A",
            (
                "docs/ops/market_state_attribute_pool_registry@1.0.json",
                "artifacts/market_state/attribute_pool_infrastructure_v1/current.json",
            ),
        ),
    )


def build_measurement_plane_registry(
    *,
    current_snapshot_id: str,
    current_snapshot_catalog: str,
    current_source_count: int,
) -> dict[str, object]:
    capabilities = layer2_capabilities()
    return {
        "schema_id": MEASUREMENT_PLANE_SCHEMA_ID,
        "measurement_plane_id": MEASUREMENT_PLANE_ID,
        "status": "phase_a_current_common_root_ready",
        "current": True,
        "asset_count": len(capabilities),
        "asset_ids": [item.asset_id for item in capabilities],
        "coordinate_contract": {
            "schema_id": COORDINATE_SCHEMA_ID,
            "bar_authority_default": "datahub_wall_clock",
            "factorlab_bar_exception": "shifted_session_clock_only",
            "available_at_required": True,
            "source_receipt_sha256_required": True,
        },
        "capabilities": [item.to_dict() for item in capabilities],
        "current_reconciliation": {
            "attribute_pool_snapshot_id": current_snapshot_id,
            "attribute_pool_catalog": current_snapshot_catalog,
            "attribute_pool_source_count": current_source_count,
            "documentation_reconciliation_status": "shared_entry_update_pending_controller_merge",
            "recorded_documentation_drift": [
                "ai-readme_reports_63_sources",
                "attribute_pool_workflow_reports_snapshot_d2b8282253fcf2fe",
                "attribute_pool_whitepaper_reports_snapshot_d2b8282253fcf2fe_and_69_sources",
            ],
        },
        "successor_phases": ["A", "B", "C", "D", "E", "F"],
        "forbidden_output_tokens": list(_FORBIDDEN_OUTPUT_TOKENS),
        "authority": {
            "measurement": True,
            "strategy_selection": False,
            "parameter_selection": False,
            "routing": False,
            "production": False,
        },
    }


def validate_measurement_output_columns(columns: Sequence[object]) -> None:
    lowered = tuple(str(column).lower() for column in columns)
    forbidden_words = {"position", "claim", "claimed", "action", "selected"}
    forbidden = sorted(
        column
        for column in lowered
        if forbidden_words.intersection(column.split("_")) or "tool_owner" in column or "responsible_tool" in column
    )
    if forbidden:
        raise ValidationError(f"Layer 2 output contains strategy fields: {forbidden}")


def validate_measurement_plane_registry(
    payload: Mapping[str, object],
    *,
    project_root: Path,
    frozen_inventory: Mapping[str, object],
    require_current: bool = False,
) -> dict[str, object]:
    if payload.get("schema_id") != MEASUREMENT_PLANE_SCHEMA_ID:
        raise ValidationError("Layer 2 measurement-plane schema drifted")
    if payload.get("measurement_plane_id") != MEASUREMENT_PLANE_ID:
        raise ValidationError("Layer 2 measurement-plane identity drifted")
    if payload.get("status") != "phase_a_current_common_root_ready" or payload.get("current") is not True:
        raise ValidationError("Layer 2 measurement-plane status is not current Phase A")
    inventory_assets = frozen_inventory.get("assets")
    if not isinstance(inventory_assets, list):
        raise ValidationError("four-layer inventory asset list is missing")
    frozen_ids = tuple(
        str(asset.get("asset_id"))
        for asset in inventory_assets
        if isinstance(asset, Mapping) and asset.get("owner_lane") == 2 and asset.get("layer") == "measurement"
    )
    if frozen_ids != LAYER2_ASSET_IDS:
        raise ValidationError("Layer 2 measurement-plane denominator drifted")
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, list) or len(capabilities) != len(LAYER2_ASSET_IDS):
        raise ValidationError("Layer 2 capability matrix must cover exactly 17 assets")
    capability_ids = tuple(str(row.get("asset_id")) for row in capabilities if isinstance(row, Mapping))
    if capability_ids != LAYER2_ASSET_IDS:
        raise ValidationError("Layer 2 capability ordering or identity drifted")
    for row in capabilities:
        if not isinstance(row, Mapping):
            raise ValidationError("Layer 2 capability row must be an object")
        if row.get("schema_id") != CAPABILITY_SCHEMA_ID:
            raise ValidationError("Layer 2 capability schema drifted")
        if row.get("measurement_authority") is not True:
            raise ValidationError("Layer 2 capability lost measurement authority")
        if row.get("routing_authority") is not False or row.get("production_authority") is not False:
            raise ValidationError("Layer 2 capability overclaimed authority")
        if row.get("status") != "ready" and not row.get("known_gaps"):
            raise ValidationError("non-ready Layer 2 capability omitted its gaps")
    authority = payload.get("authority")
    if not isinstance(authority, Mapping) or (
        authority.get("measurement") is not True
        or any(authority.get(key) is not False for key in ("strategy_selection", "parameter_selection", "routing", "production"))
    ):
        raise ValidationError("Layer 2 measurement-plane authority drifted")
    reconciliation = payload.get("current_reconciliation")
    if not isinstance(reconciliation, Mapping):
        raise ValidationError("Layer 2 snapshot reconciliation is missing")
    snapshot_id = _required_text(reconciliation, "attribute_pool_snapshot_id")
    catalog_relative = _required_text(reconciliation, "attribute_pool_catalog")
    catalog = _read_json(project_root / catalog_relative)
    sources = catalog.get("sources")
    if not isinstance(sources, list) or reconciliation.get("attribute_pool_source_count") != len(sources):
        raise ValidationError("Layer 2 current pointer/source count reconciliation drifted")
    if require_current:
        current = _read_json(
            project_root
            / "artifacts/market_state/attribute_pool_infrastructure_v1/current.json"
        )
        if current.get("snapshot_id") != snapshot_id:
            raise ValidationError("Layer 2 registry is historical, not current")
    drift = reconciliation.get("recorded_documentation_drift")
    if not isinstance(drift, list) or len(drift) != 3:
        raise ValidationError("Layer 2 known current-documentation drift is not explicit")
    return {
        "status": "passed",
        "asset_count": len(capabilities),
        "ready_count": sum(row.get("status") == "ready" for row in capabilities if isinstance(row, Mapping)),
        "partial_count": sum(row.get("status") == "partial" for row in capabilities if isinstance(row, Mapping)),
        "compatibility_count": sum(row.get("status") == "compatibility" for row in capabilities if isinstance(row, Mapping)),
        "attribute_pool_snapshot_id": snapshot_id,
        "attribute_pool_source_count": len(sources),
        "production_authority": False,
    }


def _read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValidationError(f"Layer 2 required JSON is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValidationError(f"Layer 2 JSON must be an object: {path}")
    return cast(dict[str, object], payload)


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Layer 2 contract requires {key}")
    return value


__all__ = [
    "CAPABILITY_SCHEMA_ID",
    "COORDINATE_SCHEMA_ID",
    "LAYER2_ASSET_IDS",
    "MEASUREMENT_PLANE_ID",
    "MEASUREMENT_PLANE_SCHEMA_ID",
    "Layer2Capability",
    "Layer2MeasurementCoordinate",
    "build_measurement_plane_registry",
    "layer2_capabilities",
    "validate_measurement_output_columns",
    "validate_measurement_plane_registry",
]
