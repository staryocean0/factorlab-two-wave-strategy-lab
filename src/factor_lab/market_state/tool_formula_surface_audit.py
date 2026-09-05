# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Fail-closed V2 audit across V1 benchmarks, adapters, formulas, and source."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.tool_formula_mechanisms import (
    TOOL_FORMULA_SURFACE_AUDIT_V2_SCHEMA_ID,
    build_tool_formula_mechanism_bundle,
    formula_surface_audit_v2_reference,
)
from factor_lab.market_state.tool_parameter_catalog_v2 import (
    TOOL_PARAMETER_CATALOG_V2_SCHEMA_ID,
    ToolParameterCatalogV2,
    build_tool_parameter_catalog_v2,
)
from factor_lab.market_state.tool_registry import (
    V2_PARAMETER_CATALOG_MIGRATION_TOOL_IDS,
    tool_benchmark_specs,
)

_ADAPTER_SOURCE: Final[str] = "src/factor_lab/market_state/tool_benchmark_adapters.py"
_ADAPTER_TOKENS: Final[Mapping[str, str]] = {
    "laplace_iir_mixed_bandpass": ('"laplace_iir_mixed_bandpass": _iir_bandpass_target,'),
    "laplace_iir_lowpass": '"laplace_iir_lowpass": _iir_lowpass_target,',
    "rolling_fourier_bandpass": ('"rolling_fourier_bandpass": _fourier_bandpass_target,'),
    "causal_haar_wavelet_bandpass": ('"causal_haar_wavelet_bandpass": _haar_wavelet_bandpass_target,'),
    "r3_nested_moving_average_component": ('"r3_nested_moving_average_component": _r3_component_target,'),
    "bollinger_volatility_channel": ('"bollinger_volatility_channel": _volatility_channel_target,'),
    "frequency_selective_bollinger_channel": ('"frequency_selective_bollinger_channel": _frequency_bollinger_target,'),
    "butterworth_clean_bandpass": ('"butterworth_clean_bandpass": _butterworth_target,'),
    "butterworth_lowpass_residual_envelope": ('"butterworth_lowpass_residual_envelope": _lowpass_residual_target,'),
    "causal_asymmetric_arc_state_space_envelope": ('"causal_asymmetric_arc_state_space_envelope": _asymmetric_arc_target,'),
    "donchian_price_channel": ('"donchian_price_channel": _price_channel_target,'),
    "causal_trendline_channel": ('"causal_trendline_channel": _trendline_channel_target,'),
    "simple_moving_average_trend": ('"simple_moving_average_trend": _moving_average_target,'),
}
_LEGACY_HIDDEN_SURFACE_IDS: Final[Mapping[str, frozenset[str]]] = {
    "frequency_selective_bollinger_channel": frozenset(
        {
            "band_upper_frequency_ratio",
            "width_smoothing_half_life_ratio",
            "warmup_multiplier",
            "minimum_window_bars",
            "sampling_frequency",
            "filter_initialization_policy",
        }
    ),
    "butterworth_clean_bandpass": frozenset(
        {
            "sampling_frequency",
            "initialization_policy",
            "warmup_period_bars",
            "minimum_short_period_bars",
            "nyquist_frequency",
        }
    ),
    "butterworth_lowpass_residual_envelope": frozenset(
        {
            "matched_highpass_cutoff_period_bars",
            "warmup_cutoff_multiplier",
            "minimum_cutoff_period_bars",
            "minimum_thickness_window_bars",
            "quantile_median",
            "minimum_half_width_ratio",
            "minimum_offset_log",
            "filter_initialization_policy",
        }
    ),
}
_SPECTRAL_FOUNDATION_REQUIRED_IDS: Final[Mapping[str, frozenset[str]]] = {
    "laplace_iir_mixed_bandpass": frozenset(
        {
            "input_transform",
            "carrier_bar_interval",
            "component_delta_order",
            "flat_delta_policy",
            "position_mapping",
            "execution_lag_bars",
            "cost_bps",
            "period_bars",
            "q",
            "omega0",
            "alpha",
            "numerator_coefficients",
            "denominator_poles",
            "effective_bandwidth",
            "group_delay_and_settling",
            "filter_order",
            "bandpass_topology",
            "causal_anchor_policy",
            "initial_state",
            "warmup_multiplier",
        }
    ),
    "butterworth_clean_bandpass": frozenset(
        {
            "input_transform",
            "carrier_bar_interval",
            "component_delta_order",
            "flat_delta_policy",
            "position_mapping",
            "execution_lag_bars",
            "cost_bps",
            "short_period_bars",
            "long_period_bars",
            "order",
            "lower_frequency_edge",
            "upper_frequency_edge",
            "geometric_center_period",
            "relative_bandwidth_q",
            "effective_bandpass_order",
            "prototype_family",
            "realization_form",
            "critical_edge_convention",
            "causal_anchor_policy",
            "sos_initial_state",
            "warmup_bars",
        }
    ),
    "rolling_fourier_bandpass": frozenset(
        {
            "input_transform",
            "carrier_bar_interval",
            "component_delta_order",
            "flat_delta_policy",
            "position_mapping",
            "execution_lag_bars",
            "cost_bps",
            "window_bars",
            "low_period_bars",
            "high_period_bars",
            "frequency_resolution",
            "selected_bin_set",
            "effective_quantized_edges",
            "window_function",
            "detrend_operator",
            "mask_shape",
            "dc_policy",
            "reconstruction_point",
            "rolling_stride",
            "spectral_normalization",
            "boundary_extension",
            "warmup_bars",
        }
    ),
    "causal_haar_wavelet_bandpass": frozenset(
        {
            "input_transform",
            "carrier_bar_interval",
            "component_delta_order",
            "flat_delta_policy",
            "position_mapping",
            "execution_lag_bars",
            "cost_bps",
            "window_bars",
            "level",
            "slow_level",
            "fast_scale_bars",
            "slow_scale_bars",
            "scale_ratio",
            "wavelet_basis",
            "normalization_convention",
            "block_alignment",
            "reconstruction_rule",
            "detail_threshold",
            "boundary_extension",
            "level_constraint",
            "warmup_bars",
        }
    ),
}


@dataclass(frozen=True, slots=True)
class ToolFormulaSurfaceAuditResult:
    """One tool's independent cross-surface audit result."""

    tool_id: str
    v1_benchmark_keys: tuple[str, ...]
    formula_effect_keys: tuple[str, ...]
    catalog_v1_keys: tuple[str, ...]
    unclassified_surface_ids: tuple[str, ...]
    unexpected_surface_ids: tuple[str, ...]
    missing_formula_effect_keys: tuple[str, ...]
    unexpected_formula_effect_keys: tuple[str, ...]
    source_token_failures: tuple[str, ...]
    adapter_token_present: bool

    @property
    def passed(self) -> bool:
        return (
            not self.unclassified_surface_ids
            and not self.unexpected_surface_ids
            and not self.missing_formula_effect_keys
            and not self.unexpected_formula_effect_keys
            and not self.source_token_failures
            and self.adapter_token_present
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "tool_id": self.tool_id,
            "v1_benchmark_keys": list(self.v1_benchmark_keys),
            "formula_effect_keys": list(self.formula_effect_keys),
            "catalog_v1_keys": list(self.catalog_v1_keys),
            "unclassified_surface_ids": list(self.unclassified_surface_ids),
            "unexpected_surface_ids": list(self.unexpected_surface_ids),
            "missing_formula_effect_keys": list(self.missing_formula_effect_keys),
            "unexpected_formula_effect_keys": list(self.unexpected_formula_effect_keys),
            "source_token_failures": list(self.source_token_failures),
            "adapter_token_present": self.adapter_token_present,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class FormulaSurfaceAuditV2:
    """No-authority audit of the initial V2 formula-surface migration."""

    catalog_semantic_digest: str
    results: tuple[ToolFormulaSurfaceAuditResult, ...]
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    @property
    def audit_status(self) -> str:
        return "passed" if all(item.passed for item in self.results) else "failed"

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": TOOL_FORMULA_SURFACE_AUDIT_V2_SCHEMA_ID,
            "catalog_schema_id": TOOL_PARAMETER_CATALOG_V2_SCHEMA_ID,
            "catalog_semantic_digest": self.catalog_semantic_digest,
            "migration_tool_ids": list(V2_PARAMETER_CATALOG_MIGRATION_TOOL_IDS),
            "audit_status": self.audit_status,
            "results": [item.to_dict() for item in self.results],
            "production_authority": self.production_authority,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "field_labels_zh": {
                "results": "逐工具公式表面覆盖审计",
                "unclassified_surface_ids": "源码影响量中未分类的表面",
                "source_token_failures": "源码见证缺失",
                "adapter_token_present": "V1适配器入口仍存在",
            },
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload


def _source_text(project_root: Path, relative_path: str) -> str:
    try:
        return (project_root / relative_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"formula surface source is unavailable: {relative_path}") from exc


def _formula_effect_keys(tool_id: str) -> set[str]:
    bundle = build_tool_formula_mechanism_bundle()
    formula = next(
        (item for item in bundle.tool_formulas if item.tool_id == tool_id),
        None,
    )
    if formula is None:
        raise ValidationError(f"migrated tool is absent from formula bundle: {tool_id}")
    return {item.parameter_id for item in formula.parameter_effects}


def _benchmark_keys(tool_id: str) -> set[str]:
    benchmark = next(
        (item for item in tool_benchmark_specs() if item.tool_id == tool_id),
        None,
    )
    if benchmark is None:
        raise ValidationError(f"migrated tool is absent from V1 benchmarks: {tool_id}")
    return {key for values in benchmark.parameters_by_frequency.values() for key in values}


def audit_formula_surface(
    *,
    project_root: Path,
    catalog: ToolParameterCatalogV2,
) -> FormulaSurfaceAuditV2:
    """Cross-check the catalog against independent V1 and source surfaces."""

    reference = formula_surface_audit_v2_reference()
    raw_scope = reference.get("migration_tool_ids")
    if (
        not isinstance(raw_scope, list)
        or not all(isinstance(item, str) for item in raw_scope)
        or tuple(raw_scope) != V2_PARAMETER_CATALOG_MIGRATION_TOOL_IDS
    ):
        raise ValidationError("formula V2 audit scope disagrees with registry scope")
    if reference["parameter_experiment_authority"] is not False:
        raise ValidationError("formula audit cannot grant experiment authority")

    adapter_source = _source_text(project_root, _ADAPTER_SOURCE)
    catalog_payload = catalog.to_dict()
    results: list[ToolFormulaSurfaceAuditResult] = []
    for tool_id in V2_PARAMETER_CATALOG_MIGRATION_TOOL_IDS:
        parameters = catalog.parameters_for(tool_id)
        catalog_ids = {item.parameter_id for item in parameters}
        v1_keys = _benchmark_keys(tool_id)
        catalog_v1_keys = {item.v1_parameter_key for item in parameters if item.v1_parameter_key is not None}
        formula_keys = _formula_effect_keys(tool_id)
        required_ids = (
            formula_keys
            | _LEGACY_HIDDEN_SURFACE_IDS.get(tool_id, frozenset())
            | _SPECTRAL_FOUNDATION_REQUIRED_IDS.get(tool_id, frozenset())
        )
        source_failures: list[str] = []
        for item in parameters:
            for assertion in item.source_assertions:
                source_text = _source_text(project_root, assertion.implementation_ref)
                if assertion.required_token not in source_text:
                    source_failures.append(f"{item.parameter_id}:{assertion.implementation_ref}")
        results.append(
            ToolFormulaSurfaceAuditResult(
                tool_id=tool_id,
                v1_benchmark_keys=tuple(sorted(v1_keys)),
                formula_effect_keys=tuple(sorted(formula_keys)),
                catalog_v1_keys=tuple(sorted(catalog_v1_keys)),
                unclassified_surface_ids=tuple(sorted(required_ids - catalog_ids)),
                unexpected_surface_ids=tuple(sorted(catalog_ids - required_ids)),
                missing_formula_effect_keys=tuple(sorted(v1_keys - formula_keys)),
                unexpected_formula_effect_keys=tuple(sorted(formula_keys - v1_keys)),
                source_token_failures=tuple(sorted(source_failures)),
                adapter_token_present=_ADAPTER_TOKENS[tool_id] in adapter_source,
            )
        )
    return FormulaSurfaceAuditV2(
        catalog_semantic_digest=str(catalog_payload["semantic_digest"]),
        results=tuple(results),
    )


def build_formula_surface_audit_v2(project_root: Path) -> FormulaSurfaceAuditV2:
    """Build and fail closed on the deterministic initial V2 audit."""

    audit = audit_formula_surface(
        project_root=project_root,
        catalog=build_tool_parameter_catalog_v2(),
    )
    validate_formula_surface_audit_v2(audit)
    return audit


def validate_formula_surface_audit_v2(audit: FormulaSurfaceAuditV2) -> None:
    """Reject any missing classification or authority-bearing audit."""

    if audit.production_authority or audit.dynamic_parameter_authority or audit.tool_routing_authority:
        raise ValidationError("formula surface audit cannot grant authority")
    if audit.audit_status != "passed":
        failed = [item.tool_id for item in audit.results if not item.passed]
        raise ValidationError(f"formula surface audit failed: {failed}")


__all__ = [
    "FormulaSurfaceAuditV2",
    "ToolFormulaSurfaceAuditResult",
    "audit_formula_surface",
    "build_formula_surface_audit_v2",
    "validate_formula_surface_audit_v2",
]
