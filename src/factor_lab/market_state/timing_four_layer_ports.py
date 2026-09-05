"""Decoupled four-layer ports with shared L1/L2 consumers and L4-only selection."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from typing import Final, Literal

from factor_lab.core.errors import ValidationError

PORT_CONTRACT_SCHEMA_ID: Final[str] = "timing_four_layer_port_contracts@1.2"
AssemblyMode = Literal["reference_identity_migration", "layer4_selected_strategy"]
PreStrategyConsumerLayer = Literal["Layer3", "Layer4"]
PRESTRATEGY_CONSUMERS: Final = ("Layer3", "Layer4")


@dataclass(frozen=True, slots=True)
class PortCapability:
    component_id: str
    port_schema_id: str
    provides: tuple[str, ...]
    component_digest: str
    allowed_consumer_layers: tuple[PreStrategyConsumerLayer, ...] = PRESTRATEGY_CONSUMERS

    def __post_init__(self) -> None:
        if not self.component_id or not self.port_schema_id or not self.provides:
            raise ValidationError("port capability identity is incomplete")
        _require_digest(self.component_digest)
        if tuple(self.allowed_consumer_layers) != PRESTRATEGY_CONSUMERS:
            raise ValidationError("Layer 1/2 capabilities must be available to Layer 3 and Layer 4")


@dataclass(frozen=True, slots=True)
class PortRequirement:
    consumer_id: str
    port_schema_id: str
    requires: tuple[str, ...]
    consumer_layer: PreStrategyConsumerLayer | None = None


def match_port(capability: PortCapability, requirement: PortRequirement) -> dict[str, object]:
    missing = sorted(set(requirement.requires).difference(capability.provides))
    consumer_allowed = (
        requirement.consumer_layer is None
        or requirement.consumer_layer in capability.allowed_consumer_layers
    )
    return {
        "compatible": capability.port_schema_id == requirement.port_schema_id and not missing and consumer_allowed,
        "missing_capabilities": missing,
        "consumer_layer_allowed": consumer_allowed,
        "provider": capability.component_id,
        "consumer": requirement.consumer_id,
    }


@dataclass(frozen=True, slots=True)
class BarViewPortReceipt:
    provider_id: str
    bar_view_id: str
    frequency_signature: str
    source_digest: str
    signal_price_view: str
    fill_price_view: str
    local_resampling: bool = False
    strategy_authority: bool = False

    def __post_init__(self) -> None:
        _require_digest(self.source_digest)
        if self.local_resampling or self.strategy_authority:
            raise ValidationError("Layer 1 PreStrategy port cannot resample locally or grant strategy authority")


@dataclass(frozen=True, slots=True)
class FeatureBundlePortReceipt:
    provider_id: str
    bar_view_digest: str
    feature_schema_id: str
    feature_bundle_digest: str
    allowed_consumers: tuple[PreStrategyConsumerLayer, ...] = PRESTRATEGY_CONSUMERS
    available_at_bound: bool = True
    parameter_selection_authority: bool = False

    def __post_init__(self) -> None:
        _require_digest(self.bar_view_digest)
        _require_digest(self.feature_bundle_digest)
        if tuple(self.allowed_consumers) != PRESTRATEGY_CONSUMERS:
            raise ValidationError("Layer 2 features must be consumable by Layer 3 and Layer 4")
        if not self.available_at_bound or self.parameter_selection_authority:
            raise ValidationError("Layer 2 PreStrategy port cannot select parameters")


@dataclass(frozen=True, slots=True)
class StrategyPolicyFamilyPortReceipt:
    strategy_id: str
    strategy_formula_digest: str
    feature_bundle_digest: str
    parameter_family_id: str
    parameter_candidate_ids: tuple[str, ...]
    parameter_family_digest: str
    selected_parameter_id: None = None
    specified_contract_symbol: None = None
    parameter_selection_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        for digest in (
            self.strategy_formula_digest,
            self.feature_bundle_digest,
            self.parameter_family_digest,
        ):
            _require_digest(digest)
        if not self.parameter_candidate_ids or len(set(self.parameter_candidate_ids)) != len(self.parameter_candidate_ids):
            raise ValidationError("Layer 3 must freeze a complete unique parameter family")
        if self.specified_contract_symbol is not None:
            raise ValidationError("Layer 3 cannot specify a contract")
        if self.selected_parameter_id is not None or self.parameter_selection_authority or self.production_authority:
            raise ValidationError("Layer 3 cannot select final parameters before Layer 4")


@dataclass(frozen=True, slots=True)
class Layer4AccountFamilyRequest:
    request_id: str
    strategy_family_digest: str
    parameter_candidate_ids: tuple[str, ...]
    account_engine_id: str
    instrument_id: str
    cost_contract_id: str
    account_policy_id: str
    full_cartesian_family: bool = True
    results_opened: bool = False

    def __post_init__(self) -> None:
        _require_digest(self.strategy_family_digest)
        if not self.full_cartesian_family or self.results_opened:
            raise ValidationError("Layer 4 account family request must freeze before results")


@dataclass(frozen=True, slots=True)
class Layer4RecentLiquidityReferencePortReceipt:
    port_schema_id: str
    snapshot_id: str
    snapshot_digest: str
    reference_end: date
    window_start: date
    window_end: date
    asset_classes: tuple[str, ...]
    actual_pit_price_path_required: bool = True
    historical_same_event_depth_used: bool = False
    parameter_selection_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.port_schema_id != "Layer4RecentOneYearLiquidityImpactReferencePort@1.0":
            raise ValidationError("unsupported Layer 4 recent-liquidity reference port")
        if not self.snapshot_id:
            raise ValidationError("Layer 4 recent-liquidity reference identity is incomplete")
        _require_digest(self.snapshot_digest)
        if (self.window_end - self.window_start).days != 364 or self.window_end != self.reference_end:
            raise ValidationError("Layer 4 recent-liquidity reference must cover one inclusive year")
        required = {"equity", "ETF", "LOF", "convertible_bond", "futures", "options"}
        if set(self.asset_classes) != required:
            raise ValidationError("Layer 4 recent-liquidity reference lost a carrier class")
        if (
            not self.actual_pit_price_path_required
            or self.historical_same_event_depth_used
            or self.parameter_selection_authority
            or self.production_authority
        ):
            raise ValidationError("Layer 4 recent-liquidity reference overclaims authority")


@dataclass(frozen=True, slots=True)
class Layer4ParameterSelectionReceipt:
    request_digest: str
    evaluated_parameter_ids: tuple[str, ...]
    selected_parameter_id: str | None
    account_result_digest: str
    selection_status: Literal["selected", "no_winner"]
    parameter_selection_authority: bool = True
    production_authority: bool = False

    def __post_init__(self) -> None:
        _require_digest(self.request_digest)
        _require_digest(self.account_result_digest)
        if self.selection_status == "selected" and self.selected_parameter_id not in self.evaluated_parameter_ids:
            raise ValidationError("Layer 4 selected parameter was not evaluated")
        if self.selection_status == "no_winner" and self.selected_parameter_id is not None:
            raise ValidationError("Layer 4 no-winner receipt cannot select a parameter")
        if not self.parameter_selection_authority or self.production_authority:
            raise ValidationError("Layer 4 research selection receipt authority is invalid")


@dataclass(frozen=True, slots=True)
class StrategyAssemblyManifest:
    strategy_id: str
    assembly_mode: AssemblyMode
    layer1_component_id: str
    layer2_component_id: str
    layer3_component_id: str
    layer4_component_id: str | None
    selected_parameter_id: str | None
    parameter_selection_receipt_digest: str | None
    current_pointer_changed: bool
    strategy_behavior_changed: bool
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.assembly_mode == "layer4_selected_strategy":
            if not self.layer4_component_id or not self.selected_parameter_id or not self.parameter_selection_receipt_digest:
                raise ValidationError("final selected strategy requires a Layer 4 selection receipt")
            _require_digest(self.parameter_selection_receipt_digest)
        elif self.current_pointer_changed or self.strategy_behavior_changed:
            raise ValidationError("reference identity migration cannot change behavior or pointer")
        if self.production_authority:
            raise ValidationError("assembly manifest cannot grant production authority")


def build_layer4_account_request(
    family: StrategyPolicyFamilyPortReceipt,
    *,
    request_id: str,
    account_engine_id: str,
    instrument_id: str,
    cost_contract_id: str,
    account_policy_id: str,
) -> Layer4AccountFamilyRequest:
    return Layer4AccountFamilyRequest(
        request_id=request_id,
        strategy_family_digest=_digest(asdict(family)),
        parameter_candidate_ids=family.parameter_candidate_ids,
        account_engine_id=account_engine_id,
        instrument_id=instrument_id,
        cost_contract_id=cost_contract_id,
        account_policy_id=account_policy_id,
    )


def build_layer4_selection_receipt(
    request: Layer4AccountFamilyRequest,
    *,
    evaluated_parameter_ids: tuple[str, ...],
    selected_parameter_id: str | None,
    account_result_digest: str,
) -> Layer4ParameterSelectionReceipt:
    if tuple(evaluated_parameter_ids) != tuple(request.parameter_candidate_ids):
        raise ValidationError("Layer 4 must evaluate the complete frozen parameter family")
    return Layer4ParameterSelectionReceipt(
        request_digest=_digest(asdict(request)),
        evaluated_parameter_ids=evaluated_parameter_ids,
        selected_parameter_id=selected_parameter_id,
        account_result_digest=account_result_digest,
        selection_status="selected" if selected_parameter_id else "no_winner",
    )


def _digest(payload: object) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _require_digest(value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValidationError("port contract digest is invalid")


__all__ = [
    "PORT_CONTRACT_SCHEMA_ID",
    "PRESTRATEGY_CONSUMERS",
    "BarViewPortReceipt",
    "FeatureBundlePortReceipt",
    "Layer4AccountFamilyRequest",
    "Layer4ParameterSelectionReceipt",
    "Layer4RecentLiquidityReferencePortReceipt",
    "PortCapability",
    "PortRequirement",
    "StrategyAssemblyManifest",
    "StrategyPolicyFamilyPortReceipt",
    "build_layer4_account_request",
    "build_layer4_selection_receipt",
    "match_port",
]
