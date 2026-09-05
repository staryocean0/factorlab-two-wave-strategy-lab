"""Authoritative formula-native attribute contracts for all thirteen tools.

The formula strings are versioned semantic witnesses.  They are not parsed as a
portable DSL: execution is deliberately bound to the registered panel executor,
which validates these witnesses before dispatching the corresponding callable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from factor_lab.core.errors import ValidationError


@dataclass(frozen=True, slots=True)
class FormulaNativeAttributeBlueprint:
    """One implementation-bound formula-native output contract."""

    attribute_id: str
    output_node_id: str
    formula: str
    unit: str


_BANDPASS: Final[tuple[FormulaNativeAttributeBlueprint, ...]] = (
    FormulaNativeAttributeBlueprint(
        "component_direction_delta",
        "component_direction_delta",
        "component_t-component_(t-1)",
        "price",
    ),
    FormulaNativeAttributeBlueprint(
        "target_band_energy",
        "target_band_energy",
        "sum(target_band_component^2)",
        "price_squared",
    ),
)
_LOWPASS: Final[tuple[FormulaNativeAttributeBlueprint, ...]] = (
    FormulaNativeAttributeBlueprint(
        "lowpass_center_slope",
        "lowpass_center_slope",
        "center_t-center_(t-1)",
        "price",
    ),
    FormulaNativeAttributeBlueprint(
        "normalized_innovation",
        "normalized_innovation",
        "innovation/innovation_scale",
        "dimensionless",
    ),
)
_SIMPLE_MOVING_AVERAGE: Final[tuple[FormulaNativeAttributeBlueprint, ...]] = (
    FormulaNativeAttributeBlueprint(
        "exact_sma_kernel_gap",
        "exact_sma_kernel_gap",
        "sum((w_fast-w_slow)*close_lag)",
        "price",
    ),
    FormulaNativeAttributeBlueprint(
        "kernel_path_noise",
        "kernel_path_noise",
        "path_noise_under_exact_kernel_support",
        "dimensionless",
    ),
)
_R3_COMPONENT: Final[tuple[FormulaNativeAttributeBlueprint, ...]] = (
    FormulaNativeAttributeBlueprint(
        "r3_component_delta",
        "r3_component_delta",
        "component_t-component_(t-1)",
        "log_price",
    ),
    FormulaNativeAttributeBlueprint(
        "r3_component_energy",
        "r3_component_energy",
        "rolling_mean(component^2)",
        "log_price_squared",
    ),
)
_VOLATILITY_CHANNEL: Final[tuple[FormulaNativeAttributeBlueprint, ...]] = (
    FormulaNativeAttributeBlueprint(
        "signed_upper_rail_margin",
        "signed_upper_rail_margin",
        "close-(center+width)",
        "price",
    ),
    FormulaNativeAttributeBlueprint(
        "channel_width",
        "channel_width",
        "width_sigma*trailing_volatility",
        "price",
    ),
    FormulaNativeAttributeBlueprint(
        "channel_center_direction",
        "channel_center_direction",
        "center_t-center_(t-1)",
        "price",
    ),
)
_REGRESSION_GEOMETRY: Final[tuple[FormulaNativeAttributeBlueprint, ...]] = (
    FormulaNativeAttributeBlueprint(
        "ols_slope_gap_40_160",
        "ols_slope_gap_40_160",
        "slope_40-slope_160",
        "price_per_bar",
    ),
    FormulaNativeAttributeBlueprint(
        "ols_residual_scale_ratio_40_160",
        "ols_residual_scale_ratio_40_160",
        "residual_sigma_40/residual_sigma_160",
        "dimensionless",
    ),
    FormulaNativeAttributeBlueprint(
        "ols_rail_margin_40",
        "ols_rail_margin_40",
        "close-relevant_rail_40",
        "price",
    ),
)
_DONCHIAN: Final[tuple[FormulaNativeAttributeBlueprint, ...]] = (
    FormulaNativeAttributeBlueprint(
        "donchian_entry_margin",
        "donchian_entry_margin",
        "close-prior_entry_high",
        "price",
    ),
    FormulaNativeAttributeBlueprint(
        "donchian_exit_margin",
        "donchian_exit_margin",
        "close-prior_exit_low",
        "price",
    ),
    FormulaNativeAttributeBlueprint(
        "donchian_channel_width",
        "donchian_channel_width",
        "prior_entry_high-prior_exit_low",
        "price",
    ),
)

ATTRIBUTE_BLUEPRINTS_BY_TOOL: Final[
    dict[str, tuple[FormulaNativeAttributeBlueprint, ...]]
] = {
    **{
        tool_id: _BANDPASS
        for tool_id in (
            "laplace_iir_mixed_bandpass",
            "butterworth_clean_bandpass",
            "rolling_fourier_bandpass",
            "causal_haar_wavelet_bandpass",
        )
    },
    **{
        tool_id: _LOWPASS
        for tool_id in (
            "laplace_iir_lowpass",
            "butterworth_lowpass_residual_envelope",
            "causal_asymmetric_arc_state_space_envelope",
        )
    },
    "simple_moving_average_trend": _SIMPLE_MOVING_AVERAGE,
    "r3_nested_moving_average_component": _R3_COMPONENT,
    **{
        tool_id: _VOLATILITY_CHANNEL
        for tool_id in (
            "bollinger_volatility_channel",
            "frequency_selective_bollinger_channel",
        )
    },
    "causal_trendline_channel": _REGRESSION_GEOMETRY,
    "donchian_price_channel": _DONCHIAN,
}


def attribute_blueprints_for_tool(
    tool_id: str,
) -> tuple[FormulaNativeAttributeBlueprint, ...]:
    """Return the complete immutable attribute contract for one tool."""

    try:
        return ATTRIBUTE_BLUEPRINTS_BY_TOOL[tool_id]
    except KeyError as exc:
        raise ValidationError(
            f"formula-native attribute contract does not support tool {tool_id}"
        ) from exc


__all__ = [
    "ATTRIBUTE_BLUEPRINTS_BY_TOOL",
    "FormulaNativeAttributeBlueprint",
    "attribute_blueprints_for_tool",
]
