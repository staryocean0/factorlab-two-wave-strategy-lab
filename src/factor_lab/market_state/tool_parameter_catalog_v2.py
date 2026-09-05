# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""V2 ontology for formula-surface quantities of selected timing tools.

This catalog deliberately separates the existence of an implemented quantity
from permission to search it.  It is a read-only bridge over V1 benchmarks:
no entry here mutates a benchmark, changes its decision sequence, or creates
a parameter-experiment authorization.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeAlias

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.tool_formula_mechanisms import (
    build_tool_formula_mechanism_bundle,
)
from factor_lab.market_state.tool_registry import (
    V2_PARAMETER_CATALOG_MIGRATION_TOOL_IDS,
    tool_benchmark_specs,
)

Primitive: TypeAlias = str | int | float | bool
IdentityEffect: TypeAlias = Literal[
    "same_tool_parameter",
    "tool_variant",
    "signal_policy",
    "validity_only",
    "execution_profile",
    "derived",
    "numerical_invariant",
    "new_tool_version",
]
RegistrationStatus: TypeAlias = Literal["registered", "derived", "frozen"]
TunableStatus: TypeAlias = Literal[
    "not_searchable_yet",
    "not_tunable",
    "derived_only",
    "frozen",
]
ValueKind: TypeAlias = Literal["integer", "number", "categorical", "boolean"]

TOOL_PARAMETER_CATALOG_V2_SCHEMA_ID: Final[str] = "market_state_tool_parameter_catalog@2.0"
TOOL_PARAMETER_CATALOG_V2_VERSION: Final[str] = "tool_parameter_catalog_v2"
_IDENTITY_EFFECTS: Final[frozenset[str]] = frozenset(
    {
        "same_tool_parameter",
        "tool_variant",
        "signal_policy",
        "validity_only",
        "execution_profile",
        "derived",
        "numerical_invariant",
        "new_tool_version",
    }
)
_REGISTRATION_STATUSES: Final[frozenset[str]] = frozenset({"registered", "derived", "frozen"})
_TUNABLE_STATUSES: Final[frozenset[str]] = frozenset({"not_searchable_yet", "not_tunable", "derived_only", "frozen"})
_VALUE_KINDS: Final[frozenset[str]] = frozenset({"integer", "number", "categorical", "boolean"})

# The immutable V1 benchmark is intentionally a single baseline profile.  A
# small number of its already-versioned research dictionaries expose a
# bounded, source-backed same-tool neighbourhood around that profile.  V2
# records those values as an *admissible registration domain*; it does not
# make the parameter searchable, dynamic, or production-authorized.
_REGISTERED_RESEARCH_DOMAINS: Final[Mapping[tuple[str, str], tuple[Primitive, ...]]] = {
    ("bollinger_volatility_channel", "width_sigma"): (1.5, 2.0, 2.5),
}


@dataclass(frozen=True, slots=True)
class SourceSurfaceAssertion:
    """A literal source witness for one registered formula-surface quantity."""

    implementation_ref: str
    required_token: str

    def __post_init__(self) -> None:
        if not self.implementation_ref.startswith("src/"):
            raise ValidationError("surface assertion must name a repository source file")
        if not self.required_token.strip():
            raise ValidationError("surface assertion token is required")

    def to_dict(self) -> dict[str, str]:
        return {
            "implementation_ref": self.implementation_ref,
            "required_token": self.required_token,
        }


_RESEARCH_DOMAIN_SOURCE_ASSERTIONS: Final[Mapping[tuple[str, str], SourceSurfaceAssertion]] = {
    (
        "bollinger_volatility_channel",
        "width_sigma",
    ): SourceSurfaceAssertion(
        implementation_ref="src/factor_lab/market_state/tool_parameter_dictionary.py",
        required_token='values["width_sigma"] = {-1: 1.5, 0: 2.0, 1: 2.5}',
    ),
}


@dataclass(frozen=True, slots=True)
class ToolParameterSpecV2:
    """One classified formula, validity, policy, or execution quantity."""

    tool_id: str
    parameter_id: str
    name_zh: str
    semantic_role: str
    identity_effect: IdentityEffect
    affects_layers: tuple[str, ...]
    value_kind: ValueKind
    unit: str
    time_basis: str
    native_default: Primitive
    allowed_domain: tuple[Primitive, ...]
    derived_from: tuple[str, ...]
    cross_parameter_constraints: tuple[str, ...]
    registration_status: RegistrationStatus
    tunable_status: TunableStatus
    formula_term: str
    implementation_refs: tuple[str, ...]
    invariant_reason: str
    v1_parameter_key: str | None
    source_assertions: tuple[SourceSurfaceAssertion, ...]

    def __post_init__(self) -> None:
        if not self.tool_id or not self.parameter_id or not self.name_zh:
            raise ValidationError("V2 parameter identity fields are required")
        if self.identity_effect not in _IDENTITY_EFFECTS:
            raise ValidationError("unsupported V2 parameter identity effect")
        if self.registration_status not in _REGISTRATION_STATUSES:
            raise ValidationError("unsupported V2 registration status")
        if self.tunable_status not in _TUNABLE_STATUSES:
            raise ValidationError("unsupported V2 tunable status")
        if self.value_kind not in _VALUE_KINDS:
            raise ValidationError("unsupported V2 parameter value kind")
        if not self.affects_layers or not self.unit or not self.time_basis:
            raise ValidationError("V2 parameter semantics are incomplete")
        if not self.allowed_domain:
            raise ValidationError("V2 parameter allowed domain is required")
        if not self.formula_term or not self.implementation_refs:
            raise ValidationError("V2 parameter formula provenance is required")
        if not self.source_assertions:
            raise ValidationError("V2 parameter must have a source assertion")
        if self.identity_effect == "derived":
            if self.registration_status != "derived" or not self.derived_from:
                raise ValidationError("derived quantity requires derivation provenance")
            if self.tunable_status != "derived_only":
                raise ValidationError("derived quantity cannot be directly tunable")
        elif self.registration_status == "derived":
            raise ValidationError("only derived quantities may use derived status")
        if self.identity_effect == "numerical_invariant":
            if self.registration_status != "frozen" or self.tunable_status != "frozen":
                raise ValidationError("numerical invariant must be frozen")
            if not self.invariant_reason:
                raise ValidationError("numerical invariant needs a freezing reason")
        if (
            self.identity_effect
            in {
                "tool_variant",
                "signal_policy",
                "validity_only",
                "execution_profile",
                "new_tool_version",
            }
            and self.tunable_status != "not_tunable"
        ):
            raise ValidationError("non-axis V2 quantity cannot be directly tunable")

    @property
    def surface_id(self) -> str:
        return f"{self.tool_id}:{self.parameter_id}"

    def to_dict(self) -> dict[str, object]:
        return {
            "tool_id": self.tool_id,
            "parameter_id": self.parameter_id,
            "name_zh": self.name_zh,
            "semantic_role": self.semantic_role,
            "identity_effect": self.identity_effect,
            "affects_layers": list(self.affects_layers),
            "value_kind": self.value_kind,
            "unit": self.unit,
            "time_basis": self.time_basis,
            "native_default": self.native_default,
            "allowed_domain": list(self.allowed_domain),
            "derived_from": list(self.derived_from),
            "cross_parameter_constraints": list(self.cross_parameter_constraints),
            "registration_status": self.registration_status,
            "tunable_status": self.tunable_status,
            "formula_term": self.formula_term,
            "implementation_refs": list(self.implementation_refs),
            "invariant_reason": self.invariant_reason,
            "v1_parameter_key": self.v1_parameter_key,
            "source_assertions": [item.to_dict() for item in self.source_assertions],
        }


def _source(path: str, token: str) -> tuple[SourceSurfaceAssertion, ...]:
    return (SourceSurfaceAssertion(path, token),)


def _parameter(
    tool_id: str,
    parameter_id: str,
    name_zh: str,
    identity_effect: IdentityEffect,
    value_kind: ValueKind,
    native_default: Primitive,
    allowed_domain: Sequence[Primitive],
    formula_term: str,
    source_path: str,
    source_token: str,
    *,
    semantic_role: str = "公式表面量",
    affects_layers: tuple[str, ...] = ("transform",),
    unit: str = "bars",
    time_basis: str = "decision_bar",
    derived_from: tuple[str, ...] = (),
    cross_parameter_constraints: tuple[str, ...] = (),
    registration_status: RegistrationStatus = "registered",
    tunable_status: TunableStatus = "not_searchable_yet",
    invariant_reason: str = "",
    v1_parameter_key: str | None = None,
) -> ToolParameterSpecV2:
    return ToolParameterSpecV2(
        tool_id=tool_id,
        parameter_id=parameter_id,
        name_zh=name_zh,
        semantic_role=semantic_role,
        identity_effect=identity_effect,
        affects_layers=affects_layers,
        value_kind=value_kind,
        unit=unit,
        time_basis=time_basis,
        native_default=native_default,
        allowed_domain=tuple(allowed_domain),
        derived_from=derived_from,
        cross_parameter_constraints=cross_parameter_constraints,
        registration_status=registration_status,
        tunable_status=tunable_status,
        formula_term=formula_term,
        implementation_refs=(source_path,),
        invariant_reason=invariant_reason,
        v1_parameter_key=v1_parameter_key,
        source_assertions=_source(source_path, source_token),
    )


_FREQUENCY_SOURCE: Final[str] = "src/factor_lab/strategy/services/risk_off_v58_frequency_bollinger.py"
_BUTTERWORTH_SOURCE: Final[str] = "src/factor_lab/filtering/cloudridge_3_0_hybrid_filter_bank.py"
_LOWPASS_SOURCE: Final[str] = "src/factor_lab/strategy/services/risk_off_v58_lowpass_residual_envelope.py"
_ADAPTER_SOURCE: Final[str] = "src/factor_lab/market_state/tool_benchmark_adapters.py"
_REGISTRY_SOURCE: Final[str] = "src/factor_lab/market_state/tool_registry.py"
_FORMULA_SOURCE: Final[str] = "src/factor_lab/market_state/tool_formula_mechanisms.py"
_TIMING_SOURCE: Final[str] = "src/factor_lab/filtering/timing_validation.py"


@dataclass(frozen=True, slots=True)
class _BroadSurfaceSeed:
    parameter_id: str
    name_zh: str
    parameter_kind: str
    formula_term: str
    source_path: str
    source_token: str
    derived_from: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()


def _shared_component_surface_seeds(
    *,
    implementation_path: str,
    implementation_token: str,
) -> tuple[_BroadSurfaceSeed, ...]:
    return (
        _BroadSurfaceSeed(
            "input_transform",
            "输入价格变换",
            "fixed_design",
            "x_t=log(close_t)",
            _ADAPTER_SOURCE,
            "def _log_close",
        ),
        _BroadSurfaceSeed(
            "carrier_bar_interval",
            "载体K线间隔",
            "fixed_design",
            "digital frequency uses one carrier bar as the sampling interval",
            implementation_path,
            implementation_token,
        ),
        _BroadSurfaceSeed(
            "component_delta_order",
            "分量方向差分阶数",
            "decision_semantics",
            "delta_component_t=component_t-component_(t-1)",
            _TIMING_SOURCE,
            "def signal_from_filtered",
        ),
        _BroadSurfaceSeed(
            "flat_delta_policy",
            "零变动处理",
            "decision_semantics",
            "zero delta carries the latest non-zero component direction",
            _TIMING_SOURCE,
            "def _component_delta_direction_state",
        ),
        _BroadSurfaceSeed(
            "position_mapping",
            "方向到仓位映射",
            "decision_semantics",
            "positive component delta maps to long; negative maps to cash",
            _TIMING_SOURCE,
            "def signal_from_filtered",
        ),
        _BroadSurfaceSeed(
            "execution_lag_bars",
            "执行滞后K线数",
            "execution_semantics",
            "decision at close t earns return at t+1",
            _FORMULA_SOURCE,
            "def performance_identity_specs",
        ),
        _BroadSurfaceSeed(
            "cost_bps",
            "单边/换手成本口径",
            "external_execution",
            "cost=turnover*cost_bps/10000",
            _REGISTRY_SOURCE,
            "def tool_benchmark_specs",
        ),
    )


_LAPLACE_BROAD_SEEDS: Final[tuple[_BroadSurfaceSeed, ...]] = (
    *_shared_component_surface_seeds(
        implementation_path=_TIMING_SOURCE,
        implementation_token="def _iir_biquad_filter",
    ),
    _BroadSurfaceSeed(
        "period_bars",
        "中心周期",
        "exposed_runtime",
        "omega0=2*pi/period_bars",
        _TIMING_SOURCE,
        "def _iir_biquad_filter",
        constraints=("period_bars>0", "center frequency below Nyquist"),
    ),
    _BroadSurfaceSeed(
        "q",
        "品质因数Q",
        "exposed_runtime",
        "alpha=sin(omega0)/(2*q)",
        _TIMING_SOURCE,
        "def _biquad_coefficients",
        constraints=("q>0 and finite",),
    ),
    _BroadSurfaceSeed(
        "omega0",
        "数字中心角频率",
        "derived_formula",
        "omega0=2*pi/period_bars",
        _TIMING_SOURCE,
        "def _biquad_coefficients",
        ("period_bars", "carrier_bar_interval"),
    ),
    _BroadSurfaceSeed(
        "alpha",
        "阻尼中间量",
        "derived_formula",
        "alpha=sin(omega0)/(2*q)",
        _TIMING_SOURCE,
        "def _biquad_coefficients",
        ("omega0", "q"),
    ),
    _BroadSurfaceSeed(
        "numerator_coefficients",
        "分子系数",
        "derived_formula",
        "b=(alpha,0,-alpha)/(1+alpha)",
        _TIMING_SOURCE,
        "def _biquad_coefficients",
        ("alpha",),
    ),
    _BroadSurfaceSeed(
        "denominator_poles",
        "分母极点",
        "derived_formula",
        "a1=-2*cos(omega0)/(1+alpha);a2=(1-alpha)/(1+alpha)",
        _TIMING_SOURCE,
        "def _biquad_coefficients",
        ("omega0", "alpha"),
    ),
    _BroadSurfaceSeed(
        "effective_bandwidth",
        "有效带宽",
        "derived_formula",
        "effective bandwidth is determined by period_bars and q",
        _TIMING_SOURCE,
        "def _biquad_coefficients",
        ("period_bars", "q"),
    ),
    _BroadSurfaceSeed(
        "group_delay_and_settling",
        "群延迟与稳定时间",
        "derived_formula",
        "group delay and settling are determined by denominator poles",
        _TIMING_SOURCE,
        "def _biquad_coefficients",
        ("denominator_poles",),
    ),
    _BroadSurfaceSeed(
        "filter_order",
        "递归滤波阶数",
        "fixed_design",
        "second-order biquad",
        _TIMING_SOURCE,
        "def _iir_biquad_filter",
    ),
    _BroadSurfaceSeed(
        "bandpass_topology",
        "带通拓扑",
        "fixed_design",
        "constant peak-gain biquad bandpass",
        _TIMING_SOURCE,
        "def _biquad_coefficients",
    ),
    _BroadSurfaceSeed(
        "causal_anchor_policy",
        "因果锚定方式",
        "initialization_boundary",
        "subtract the first observable log close",
        _TIMING_SOURCE,
        "def _iir_biquad_filter",
    ),
    _BroadSurfaceSeed(
        "initial_state",
        "递归初始状态",
        "initialization_boundary",
        "x1=x2=y1=y2=0",
        _TIMING_SOURCE,
        "def _iir_biquad_filter",
    ),
    _BroadSurfaceSeed(
        "warmup_multiplier",
        "预热倍数",
        "initialization_boundary",
        "warmup=max(5,3*period_bars)",
        _TIMING_SOURCE,
        "def _iir_biquad_filter",
        ("period_bars",),
    ),
)

_BUTTERWORTH_BROAD_SEEDS: Final[tuple[_BroadSurfaceSeed, ...]] = (
    *_shared_component_surface_seeds(
        implementation_path=_BUTTERWORTH_SOURCE,
        implementation_token="def butterworth_bandpass_component",
    ),
    _BroadSurfaceSeed(
        "short_period_bars",
        "短周期通带边界",
        "exposed_runtime",
        "upper_frequency=1/short_period_bars",
        _BUTTERWORTH_SOURCE,
        "def butterworth_bandpass_component",
        constraints=("short_period_bars>=3",),
    ),
    _BroadSurfaceSeed(
        "long_period_bars",
        "长周期通带边界",
        "exposed_runtime",
        "lower_frequency=1/long_period_bars",
        _BUTTERWORTH_SOURCE,
        "def butterworth_bandpass_component",
        constraints=("long_period_bars>short_period_bars",),
    ),
    _BroadSurfaceSeed(
        "order",
        "巴特沃斯原型阶数",
        "exposed_runtime",
        "Butterworth(order)",
        _BUTTERWORTH_SOURCE,
        "def butterworth_bandpass_component",
        constraints=("order>=1",),
    ),
    _BroadSurfaceSeed(
        "lower_frequency_edge",
        "低频边界",
        "derived_formula",
        "lower_frequency_edge=1/long_period_bars",
        _BUTTERWORTH_SOURCE,
        "def butterworth_bandpass_component",
        ("long_period_bars", "carrier_bar_interval"),
    ),
    _BroadSurfaceSeed(
        "upper_frequency_edge",
        "高频边界",
        "derived_formula",
        "upper_frequency_edge=1/short_period_bars",
        _BUTTERWORTH_SOURCE,
        "def butterworth_bandpass_component",
        ("short_period_bars", "carrier_bar_interval"),
    ),
    _BroadSurfaceSeed(
        "geometric_center_period",
        "几何中心周期",
        "derived_formula",
        "sqrt(short_period_bars*long_period_bars)",
        _BUTTERWORTH_SOURCE,
        "def butterworth_bandpass_component",
        ("short_period_bars", "long_period_bars"),
    ),
    _BroadSurfaceSeed(
        "relative_bandwidth_q",
        "相对带宽/等效Q",
        "derived_formula",
        "Q is derived from the lower and upper frequency edges",
        _BUTTERWORTH_SOURCE,
        "def butterworth_bandpass_component",
        ("lower_frequency_edge", "upper_frequency_edge"),
    ),
    _BroadSurfaceSeed(
        "effective_bandpass_order",
        "变换后的有效带通阶数",
        "derived_formula",
        "effective_bandpass_order=2*order",
        _BUTTERWORTH_SOURCE,
        "def butterworth_bandpass_component",
        ("order",),
    ),
    _BroadSurfaceSeed(
        "prototype_family",
        "模拟原型家族",
        "fixed_design",
        "Butterworth maximally-flat magnitude",
        _BUTTERWORTH_SOURCE,
        "def butterworth_bandpass_component",
    ),
    _BroadSurfaceSeed(
        "realization_form",
        "数值实现形式",
        "fixed_design",
        "second-order sections with causal sosfilt",
        _BUTTERWORTH_SOURCE,
        "def butterworth_bandpass_component",
    ),
    _BroadSurfaceSeed(
        "critical_edge_convention",
        "临界边界增益约定",
        "fixed_design",
        "Butterworth critical edges are approximately -3dB",
        _BUTTERWORTH_SOURCE,
        "def butterworth_bandpass_component",
    ),
    _BroadSurfaceSeed(
        "causal_anchor_policy",
        "因果锚定方式",
        "initialization_boundary",
        "subtract the first observable log close",
        _BUTTERWORTH_SOURCE,
        "def butterworth_bandpass_component",
    ),
    _BroadSurfaceSeed(
        "sos_initial_state",
        "SOS初始状态",
        "initialization_boundary",
        "causal sosfilt default zero state",
        _BUTTERWORTH_SOURCE,
        "def butterworth_bandpass_component",
    ),
    _BroadSurfaceSeed(
        "warmup_bars",
        "预热长度",
        "initialization_boundary",
        "warmup_bars=long_period_bars",
        _BUTTERWORTH_SOURCE,
        "def butterworth_bandpass_component",
        ("long_period_bars",),
    ),
)

_FOURIER_BROAD_SEEDS: Final[tuple[_BroadSurfaceSeed, ...]] = (
    *_shared_component_surface_seeds(
        implementation_path=_TIMING_SOURCE,
        implementation_token="def _rolling_fourier_filter",
    ),
    _BroadSurfaceSeed(
        "window_bars",
        "滚动DFT窗口",
        "exposed_runtime",
        "frequency grid spacing=1/window_bars",
        _TIMING_SOURCE,
        "def _rolling_fourier_filter",
        constraints=("window_bars>0",),
    ),
    _BroadSurfaceSeed(
        "low_period_bars",
        "最快保留周期",
        "exposed_runtime",
        "upper frequency edge=1/low_period_bars",
        _TIMING_SOURCE,
        "def _fourier_mask",
    ),
    _BroadSurfaceSeed(
        "high_period_bars",
        "最慢保留周期",
        "exposed_runtime",
        "lower frequency edge=1/high_period_bars",
        _TIMING_SOURCE,
        "def _fourier_mask",
        constraints=("high_period_bars>low_period_bars",),
    ),
    _BroadSurfaceSeed(
        "frequency_resolution",
        "频率分辨率",
        "derived_formula",
        "frequency_resolution=1/window_bars",
        _TIMING_SOURCE,
        "def _rolling_fourier_filter",
        ("window_bars", "carrier_bar_interval"),
    ),
    _BroadSurfaceSeed(
        "selected_bin_set",
        "被保留的频率格点",
        "derived_formula",
        "{k:1/high_period<=abs(k/W)<=1/low_period}",
        _TIMING_SOURCE,
        "def _fourier_mask",
        ("window_bars", "low_period_bars", "high_period_bars"),
    ),
    _BroadSurfaceSeed(
        "effective_quantized_edges",
        "量化后的实际边界",
        "derived_formula",
        "min/max selected Fourier bins",
        _TIMING_SOURCE,
        "def _fourier_mask",
        ("selected_bin_set",),
    ),
    _BroadSurfaceSeed(
        "window_function",
        "频谱窗函数",
        "fixed_design",
        "rectangular window",
        _TIMING_SOURCE,
        "def _rolling_fourier_filter",
    ),
    _BroadSurfaceSeed(
        "detrend_operator",
        "窗口去趋势规则",
        "fixed_design",
        "subtract the trailing-window mean",
        _TIMING_SOURCE,
        "def _rolling_fourier_filter",
    ),
    _BroadSurfaceSeed(
        "mask_shape",
        "通带掩码形状",
        "fixed_design",
        "hard binary mask",
        _TIMING_SOURCE,
        "def _fourier_mask",
    ),
    _BroadSurfaceSeed(
        "dc_policy",
        "零频处理",
        "fixed_design",
        "bandpass rejects the DC bin",
        _TIMING_SOURCE,
        "def _fourier_mask",
    ),
    _BroadSurfaceSeed(
        "reconstruction_point",
        "重建取样位置",
        "fixed_design",
        "IFFT(filtered_spectrum)[-1]",
        _TIMING_SOURCE,
        "def _rolling_fourier_filter",
    ),
    _BroadSurfaceSeed(
        "rolling_stride",
        "窗口更新步长",
        "fixed_design",
        "recompute at every carrier bar",
        _TIMING_SOURCE,
        "def _rolling_fourier_filter",
    ),
    _BroadSurfaceSeed(
        "spectral_normalization",
        "频谱归一化",
        "fixed_design",
        "NumPy FFT/IFFT default normalization",
        _TIMING_SOURCE,
        "def _rolling_fourier_filter",
    ),
    _BroadSurfaceSeed(
        "boundary_extension",
        "窗口边界假设",
        "fixed_design",
        "DFT periodic extension without padding",
        _TIMING_SOURCE,
        "def _rolling_fourier_filter",
    ),
    _BroadSurfaceSeed(
        "warmup_bars",
        "预热长度",
        "initialization_boundary",
        "first output after window_bars observations",
        _TIMING_SOURCE,
        "def _rolling_fourier_filter",
        ("window_bars",),
    ),
)

_HAAR_BROAD_SEEDS: Final[tuple[_BroadSurfaceSeed, ...]] = (
    *_shared_component_surface_seeds(
        implementation_path=_TIMING_SOURCE,
        implementation_token="def _rolling_haar_filter",
    ),
    _BroadSurfaceSeed(
        "window_bars",
        "拖尾小波窗口",
        "exposed_runtime",
        "trailing Haar analysis window",
        _TIMING_SOURCE,
        "def _rolling_haar_filter",
        constraints=("window divisible by 2**slow_level",),
    ),
    _BroadSurfaceSeed(
        "level",
        "快速Haar层级",
        "exposed_runtime",
        "fast_scale_bars=2**level",
        _TIMING_SOURCE,
        "def _rolling_haar_filter",
        constraints=("level>0",),
    ),
    _BroadSurfaceSeed(
        "slow_level",
        "慢速Haar层级",
        "exposed_runtime",
        "slow_scale_bars=2**slow_level",
        _TIMING_SOURCE,
        "def _rolling_haar_filter",
        constraints=("slow_level>level",),
    ),
    _BroadSurfaceSeed(
        "fast_scale_bars",
        "快速块长度",
        "derived_formula",
        "fast_scale_bars=2**level",
        _TIMING_SOURCE,
        "def _haar_lowpass_reconstruction",
        ("level",),
    ),
    _BroadSurfaceSeed(
        "slow_scale_bars",
        "慢速块长度",
        "derived_formula",
        "slow_scale_bars=2**slow_level",
        _TIMING_SOURCE,
        "def _haar_lowpass_reconstruction",
        ("slow_level",),
    ),
    _BroadSurfaceSeed(
        "scale_ratio",
        "快慢尺度比",
        "derived_formula",
        "scale_ratio=2**(slow_level-level)",
        _TIMING_SOURCE,
        "def _rolling_haar_filter",
        ("level", "slow_level"),
    ),
    _BroadSurfaceSeed(
        "wavelet_basis",
        "小波基函数",
        "fixed_design",
        "Haar piecewise-constant basis",
        _TIMING_SOURCE,
        "def _haar_lowpass_reconstruction",
    ),
    _BroadSurfaceSeed(
        "normalization_convention",
        "Haar归一化约定",
        "fixed_design",
        "analysis averages and half-differences",
        _TIMING_SOURCE,
        "def _haar_lowpass_reconstruction",
    ),
    _BroadSurfaceSeed(
        "block_alignment",
        "块对齐方式",
        "fixed_design",
        "trailing window right edge aligns with current t",
        _TIMING_SOURCE,
        "def _rolling_haar_filter",
    ),
    _BroadSurfaceSeed(
        "reconstruction_rule",
        "带通重建规则",
        "fixed_design",
        "L_level(x)[-1]-L_slow_level(x)[-1]",
        _TIMING_SOURCE,
        "def _rolling_haar_filter",
    ),
    _BroadSurfaceSeed(
        "detail_threshold",
        "小波细节阈值",
        "fixed_design",
        "no detail thresholding or shrinkage",
        _TIMING_SOURCE,
        "def _rolling_haar_filter",
    ),
    _BroadSurfaceSeed(
        "boundary_extension",
        "边界扩展",
        "fixed_design",
        "no padding; window divisibility required",
        _TIMING_SOURCE,
        "def _rolling_haar_filter",
    ),
    _BroadSurfaceSeed(
        "level_constraint",
        "层级合法域",
        "fixed_design",
        "window%(2**level)==0 and slow_level>level",
        _TIMING_SOURCE,
        "def _rolling_haar_filter",
    ),
    _BroadSurfaceSeed(
        "warmup_bars",
        "预热长度",
        "initialization_boundary",
        "first output after window_bars observations",
        _TIMING_SOURCE,
        "def _rolling_haar_filter",
        ("window_bars",),
    ),
)

SPECTRAL_FOUNDATION_SURFACE_IDS: Final[Mapping[str, frozenset[str]]] = {
    "laplace_iir_mixed_bandpass": frozenset(item.parameter_id for item in _LAPLACE_BROAD_SEEDS),
    "butterworth_clean_bandpass": frozenset(item.parameter_id for item in _BUTTERWORTH_BROAD_SEEDS),
    "rolling_fourier_bandpass": frozenset(item.parameter_id for item in _FOURIER_BROAD_SEEDS),
    "causal_haar_wavelet_bandpass": frozenset(item.parameter_id for item in _HAAR_BROAD_SEEDS),
}


def _frequency_selective_bollinger_parameters() -> tuple[ToolParameterSpecV2, ...]:
    tool = "frequency_selective_bollinger_channel"
    return (
        _parameter(
            tool,
            "period_bars",
            "中心滤波周期",
            "same_tool_parameter",
            "integer",
            48,
            (48, 96, 192, 384),
            "lowpass cutoff=1/P",
            _FREQUENCY_SOURCE,
            "period_bars: int",
            v1_parameter_key="period_bars",
        ),
        _parameter(
            tool,
            "thickness_source",
            "轨宽分量来源",
            "tool_variant",
            "categorical",
            "bandpass",
            ("highpass", "bandpass"),
            "highpass or [1/P,2/P] component",
            _FREQUENCY_SOURCE,
            "THICKNESS_SOURCES",
            semantic_role="轨宽拓扑选择",
            unit="category",
            time_basis="not_applicable",
            affects_layers=("transform", "signal_geometry"),
            tunable_status="not_tunable",
            v1_parameter_key="thickness_source",
        ),
        _parameter(
            tool,
            "window_multiplier",
            "轨宽RMS窗倍数",
            "same_tool_parameter",
            "number",
            2.0,
            (0.5, 1.0, 2.0),
            "W=round(P*window_multiplier)",
            _FREQUENCY_SOURCE,
            "window_multiplier: float",
            unit="period_ratio",
            v1_parameter_key="window_multiplier",
        ),
        _parameter(
            tool,
            "width_multiplier",
            "轨宽倍数",
            "same_tool_parameter",
            "number",
            1.0,
            (1.0, 1.5, 2.0),
            "width=RMS*width_multiplier",
            _FREQUENCY_SOURCE,
            "width_multiplier: float",
            unit="multiplier",
            time_basis="not_applicable",
            affects_layers=("signal_geometry", "decision"),
            v1_parameter_key="width_multiplier",
        ),
        _parameter(
            tool,
            "action",
            "动作状态机",
            "signal_policy",
            "categorical",
            "trend_breakout",
            ("trend_breakout", "mean_repair"),
            "channel_decision(action)",
            _FREQUENCY_SOURCE,
            "def channel_decision",
            semantic_role="动作表示",
            unit="category",
            time_basis="decision_bar",
            affects_layers=("decision",),
            tunable_status="not_tunable",
            v1_parameter_key="action",
        ),
        _parameter(
            tool,
            "filter_order",
            "滤波阶数",
            "same_tool_parameter",
            "integer",
            4,
            tuple(range(1, 9)),
            "Butterworth(order)",
            _FREQUENCY_SOURCE,
            "filter_order: int = 4",
            unit="order",
            time_basis="not_applicable",
            v1_parameter_key="filter_order",
        ),
        _parameter(
            tool,
            "cost_bps",
            "单边交易成本",
            "execution_profile",
            "number",
            7.0,
            (7.0,),
            "cost=turnover*cost_bps/10000",
            _ADAPTER_SOURCE,
            'params["cost_bps"]',
            semantic_role="执行成本",
            unit="bps",
            time_basis="execution_bar",
            affects_layers=("execution", "evaluation"),
            tunable_status="not_tunable",
            v1_parameter_key="cost_bps",
        ),
        _parameter(
            tool,
            "band_upper_frequency_ratio",
            "带通上边界频率比",
            "same_tool_parameter",
            "number",
            2.0,
            (1.5, 2.0, 2.5),
            "bandpass=[1/P, band_upper_frequency_ratio/P]",
            _FREQUENCY_SOURCE,
            "band_upper_frequency_ratio: float = 2.0",
            unit="ratio",
            time_basis="not_applicable",
            v1_parameter_key="band_upper_frequency_ratio",
        ),
        _parameter(
            tool,
            "width_smoothing_half_life_ratio",
            "轨宽平滑半衰期比例",
            "same_tool_parameter",
            "number",
            0.125,
            (0.125,),
            "half_life=max(2, W*ratio)",
            _FREQUENCY_SOURCE,
            "spec.window_bars / 8.0",
            unit="window_ratio",
            time_basis="not_applicable",
        ),
        _parameter(
            tool,
            "warmup_multiplier",
            "预热周期倍数",
            "validity_only",
            "integer",
            2,
            (2,),
            "warmup=max(P*multiplier,W)",
            _FREQUENCY_SOURCE,
            "spec.period_bars * 2",
            semantic_role="有效性门",
            unit="period_ratio",
            time_basis="decision_bar",
            affects_layers=("validity",),
            tunable_status="not_tunable",
        ),
        _parameter(
            tool,
            "minimum_window_bars",
            "最小轨宽窗口",
            "numerical_invariant",
            "integer",
            8,
            (8,),
            "W=max(minimum_window_bars,round(P*multiplier))",
            _FREQUENCY_SOURCE,
            "max(8, int(round(",
            semantic_role="数值稳定下限",
            unit="bars",
            time_basis="not_applicable",
            affects_layers=("validity",),
            registration_status="frozen",
            tunable_status="frozen",
            invariant_reason="保证RMS窗口具有最小可定义长度",
        ),
        _parameter(
            tool,
            "sampling_frequency",
            "数字滤波采样频率",
            "numerical_invariant",
            "number",
            1.0,
            (1.0,),
            "Butterworth(...,fs=sampling_frequency)",
            _FREQUENCY_SOURCE,
            "fs=1.0",
            semantic_role="离散滤波归一化",
            unit="cycles_per_bar",
            time_basis="not_applicable",
            registration_status="frozen",
            tunable_status="frozen",
            invariant_reason="V1固定为每根载体K线一个规则样本",
        ),
        _parameter(
            tool,
            "filter_initialization_policy",
            "滤波初态政策",
            "new_tool_version",
            "categorical",
            "steady_state_at_first_observation",
            ("steady_state_at_first_observation",),
            "sosfilt_zi(sos)*first_observation",
            _FREQUENCY_SOURCE,
            "signal.sosfilt_zi(sos) * float(array[0])",
            semantic_role="递推初态",
            unit="category",
            time_basis="first_observation",
            affects_layers=("transform",),
            tunable_status="not_tunable",
        ),
    )


def _butterworth_bandpass_parameters() -> tuple[ToolParameterSpecV2, ...]:
    tool = "butterworth_clean_bandpass"
    return (
        _parameter(
            tool,
            "short_period_bars",
            "通带短周期边界",
            "same_tool_parameter",
            "integer",
            28,
            (28,),
            "upper_frequency=1/short_period_bars",
            _BUTTERWORTH_SOURCE,
            "short_period_bars: int",
            v1_parameter_key="short_period_bars",
        ),
        _parameter(
            tool,
            "long_period_bars",
            "通带长周期边界",
            "same_tool_parameter",
            "integer",
            57,
            (57,),
            "lower_frequency=1/long_period_bars",
            _BUTTERWORTH_SOURCE,
            "long_period_bars: int",
            v1_parameter_key="long_period_bars",
        ),
        _parameter(
            tool,
            "order",
            "巴特沃斯阶数",
            "same_tool_parameter",
            "integer",
            4,
            (4,),
            "Butterworth(order)",
            _BUTTERWORTH_SOURCE,
            "order: int = DEFAULT_BUTTER_ORDER",
            unit="order",
            time_basis="not_applicable",
            v1_parameter_key="order",
        ),
        _parameter(
            tool,
            "cost_bps",
            "单边交易成本",
            "execution_profile",
            "number",
            7.0,
            (7.0,),
            "cost=turnover*cost_bps/10000",
            _ADAPTER_SOURCE,
            'params["cost_bps"]',
            semantic_role="执行成本",
            unit="bps",
            time_basis="execution_bar",
            affects_layers=("execution", "evaluation"),
            tunable_status="not_tunable",
            v1_parameter_key="cost_bps",
        ),
        _parameter(
            tool,
            "sampling_frequency",
            "数字滤波采样频率",
            "numerical_invariant",
            "number",
            1.0,
            (1.0,),
            "Butterworth(...,fs=sampling_frequency)",
            _BUTTERWORTH_SOURCE,
            "fs=1.0",
            semantic_role="离散滤波归一化",
            unit="cycles_per_bar",
            time_basis="not_applicable",
            registration_status="frozen",
            tunable_status="frozen",
            invariant_reason="V1按规则样本逐K线递推",
        ),
        _parameter(
            tool,
            "initialization_policy",
            "带通启动锚定",
            "new_tool_version",
            "categorical",
            "subtract_first_observation",
            ("subtract_first_observation",),
            "SOSFILT(x-x_0)",
            _BUTTERWORTH_SOURCE,
            "source - source[0]",
            semantic_role="启动瞬态政策",
            unit="category",
            time_basis="first_observation",
            affects_layers=("transform",),
            tunable_status="not_tunable",
        ),
        _parameter(
            tool,
            "warmup_period_bars",
            "带通预热长度",
            "derived",
            "integer",
            57,
            (57,),
            "warmup=long_period_bars",
            _BUTTERWORTH_SOURCE,
            "min(len(result), long_period_bars)",
            semantic_role="有效性派生量",
            unit="bars",
            time_basis="decision_bar",
            affects_layers=("validity",),
            derived_from=("long_period_bars",),
            registration_status="derived",
            tunable_status="derived_only",
        ),
        _parameter(
            tool,
            "minimum_short_period_bars",
            "短周期下限",
            "numerical_invariant",
            "integer",
            3,
            (3,),
            "short_period_bars>=minimum_short_period_bars",
            _BUTTERWORTH_SOURCE,
            "short_period_bars < 3",
            semantic_role="频率可定义下限",
            unit="bars",
            time_basis="not_applicable",
            affects_layers=("validity",),
            registration_status="frozen",
            tunable_status="frozen",
            invariant_reason="保证通带边界位于Nyquist以下的有效整数域",
        ),
        _parameter(
            tool,
            "nyquist_frequency",
            "Nyquist频率上限",
            "numerical_invariant",
            "number",
            0.5,
            (0.5,),
            "upper_frequency<nyquist_frequency",
            _BUTTERWORTH_SOURCE,
            "high_frequency >= 0.5",
            semantic_role="数字滤波频率上限",
            unit="cycles_per_bar",
            time_basis="not_applicable",
            affects_layers=("validity",),
            registration_status="frozen",
            tunable_status="frozen",
            invariant_reason="离散每K线采样的理论上限",
        ),
    )


def _lowpass_residual_parameters() -> tuple[ToolParameterSpecV2, ...]:
    tool = "butterworth_lowpass_residual_envelope"
    return (
        _parameter(
            tool,
            "cutoff_period_bars",
            "低通截止周期",
            "same_tool_parameter",
            "integer",
            96,
            (96,),
            "lowpass cutoff=1/cutoff_period_bars",
            _LOWPASS_SOURCE,
            "cutoff_period_bars: int = 96",
            v1_parameter_key="cutoff_period_bars",
        ),
        _parameter(
            tool,
            "lowpass_order",
            "低通滤波阶数",
            "same_tool_parameter",
            "integer",
            4,
            (4,),
            "Butterworth(lowpass_order)",
            _LOWPASS_SOURCE,
            "lowpass_order: int = 4",
            unit="order",
            time_basis="not_applicable",
            v1_parameter_key="lowpass_order",
        ),
        _parameter(
            tool,
            "thickness_window_bars",
            "残差轨宽历史窗",
            "tool_variant",
            "integer",
            64,
            (64,),
            "rail quantile history window",
            _LOWPASS_SOURCE,
            "thickness_window_bars: int = 64",
            semantic_role="轨宽几何",
            affects_layers=("signal_geometry",),
            tunable_status="not_tunable",
            v1_parameter_key="thickness_window_bars",
        ),
        _parameter(
            tool,
            "thickness_lower_quantile",
            "下轨残差分位数",
            "tool_variant",
            "number",
            0.10,
            (0.10,),
            "lower rail residual quantile",
            _LOWPASS_SOURCE,
            "thickness_lower_quantile: float = 0.10",
            semantic_role="轨宽几何",
            unit="quantile",
            time_basis="not_applicable",
            affects_layers=("signal_geometry",),
            tunable_status="not_tunable",
            v1_parameter_key="thickness_lower_quantile",
        ),
        _parameter(
            tool,
            "thickness_upper_quantile",
            "上轨残差分位数",
            "tool_variant",
            "number",
            0.90,
            (0.90,),
            "upper rail residual quantile",
            _LOWPASS_SOURCE,
            "thickness_upper_quantile: float = 0.90",
            semantic_role="轨宽几何",
            unit="quantile",
            time_basis="not_applicable",
            affects_layers=("signal_geometry",),
            tunable_status="not_tunable",
            v1_parameter_key="thickness_upper_quantile",
        ),
        _parameter(
            tool,
            "thickness_smoothing_half_life_bars",
            "轨宽平滑半衰期",
            "tool_variant",
            "number",
            6.0,
            (6.0,),
            "rail EWMA half-life",
            _LOWPASS_SOURCE,
            "thickness_smoothing_half_life_bars: float = 6.0",
            semantic_role="轨宽几何",
            unit="bars",
            time_basis="decision_bar",
            affects_layers=("signal_geometry",),
            tunable_status="not_tunable",
            v1_parameter_key="thickness_smoothing_half_life_bars",
        ),
        _parameter(
            tool,
            "warmup_bars",
            "有效信号预热长度",
            "validity_only",
            "integer",
            512,
            (512,),
            "valid when t+1>=warmup_bars",
            _LOWPASS_SOURCE,
            "warmup_bars: int = 512",
            semantic_role="有效性门",
            unit="bars",
            time_basis="decision_bar",
            affects_layers=("validity",),
            tunable_status="not_tunable",
            v1_parameter_key="warmup_bars",
        ),
        _parameter(
            tool,
            "cost_bps",
            "单边交易成本",
            "execution_profile",
            "number",
            7.0,
            (7.0,),
            "cost=turnover*cost_bps/10000",
            _ADAPTER_SOURCE,
            'params["cost_bps"]',
            semantic_role="执行成本",
            unit="bps",
            time_basis="execution_bar",
            affects_layers=("execution", "evaluation"),
            tunable_status="not_tunable",
            v1_parameter_key="cost_bps",
        ),
        _parameter(
            tool,
            "matched_highpass_cutoff_period_bars",
            "匹配高通截止周期",
            "derived",
            "integer",
            96,
            (96,),
            "highpass cutoff=1/cutoff_period_bars",
            _LOWPASS_SOURCE,
            "1.0 / float(spec.cutoff_period_bars)",
            semantic_role="轨宽分量派生尺度",
            unit="bars",
            time_basis="decision_bar",
            affects_layers=("transform", "signal_geometry"),
            derived_from=("cutoff_period_bars",),
            registration_status="derived",
            tunable_status="derived_only",
        ),
        _parameter(
            tool,
            "warmup_cutoff_multiplier",
            "最低预热截止周期倍数",
            "validity_only",
            "integer",
            2,
            (2,),
            "warmup>=max(multiplier*cutoff,thickness_window)",
            _LOWPASS_SOURCE,
            "self.cutoff_period_bars * 2",
            semantic_role="有效性约束",
            unit="period_ratio",
            time_basis="decision_bar",
            affects_layers=("validity",),
            tunable_status="not_tunable",
        ),
        _parameter(
            tool,
            "minimum_cutoff_period_bars",
            "截止周期下限",
            "numerical_invariant",
            "integer",
            32,
            (32,),
            "cutoff_period_bars>=minimum_cutoff_period_bars",
            _LOWPASS_SOURCE,
            "cutoff_period_bars < 32",
            semantic_role="数值稳定下限",
            unit="bars",
            time_basis="not_applicable",
            affects_layers=("validity",),
            registration_status="frozen",
            tunable_status="frozen",
            invariant_reason="V58低通物理定义的最短有效尺度",
        ),
        _parameter(
            tool,
            "minimum_thickness_window_bars",
            "轨宽窗下限",
            "numerical_invariant",
            "integer",
            32,
            (32,),
            "thickness_window_bars>=minimum_thickness_window_bars",
            _LOWPASS_SOURCE,
            "thickness_window_bars < 32",
            semantic_role="数值稳定下限",
            unit="bars",
            time_basis="not_applicable",
            affects_layers=("validity",),
            registration_status="frozen",
            tunable_status="frozen",
            invariant_reason="保证分位轨宽的最小历史支持",
        ),
        _parameter(
            tool,
            "quantile_median",
            "分位数中位界",
            "numerical_invariant",
            "number",
            0.5,
            (0.5,),
            "lower_quantile<quantile_median<upper_quantile",
            _LOWPASS_SOURCE,
            "0.0 < self.thickness_lower_quantile < 0.5",
            semantic_role="分位数不变量",
            unit="quantile",
            time_basis="not_applicable",
            affects_layers=("validity",),
            registration_status="frozen",
            tunable_status="frozen",
            invariant_reason="上下轨必须跨越中位数",
        ),
        _parameter(
            tool,
            "minimum_half_width_ratio",
            "最小半轨宽比例",
            "numerical_invariant",
            "number",
            0.5,
            (0.5,),
            "minimum_half_width=ratio*median(range)",
            _LOWPASS_SOURCE,
            "minimum_half_width = 0.5",
            semantic_role="轨宽防塌缩",
            unit="range_ratio",
            time_basis="decision_bar",
            affects_layers=("signal_geometry",),
            registration_status="frozen",
            tunable_status="frozen",
            invariant_reason="避免独立高通轨宽在低振幅时塌缩为零",
        ),
        _parameter(
            tool,
            "minimum_offset_log",
            "最小对数轨宽偏移",
            "numerical_invariant",
            "number",
            1e-6,
            (1e-6,),
            "offset>=minimum_offset_log",
            _LOWPASS_SOURCE,
            "1e-6",
            semantic_role="对数空间数值稳定",
            unit="log_return",
            time_basis="not_applicable",
            affects_layers=("signal_geometry",),
            registration_status="frozen",
            tunable_status="frozen",
            invariant_reason="保证上下轨严格分离",
        ),
        _parameter(
            tool,
            "filter_initialization_policy",
            "滤波初态政策",
            "new_tool_version",
            "categorical",
            "steady_state_at_first_observation",
            ("steady_state_at_first_observation",),
            "sosfilt_zi(sos)*first_observation",
            _LOWPASS_SOURCE,
            "signal.sosfilt_zi(sos) * float(numeric.iloc[0])",
            semantic_role="递推初态",
            unit="category",
            time_basis="first_observation",
            affects_layers=("transform",),
            tunable_status="not_tunable",
        ),
    )


def _benchmark_values(tool_id: str) -> Mapping[str, tuple[Primitive, ...]]:
    benchmark = next(item for item in tool_benchmark_specs() if item.tool_id == tool_id)
    values: dict[str, list[Primitive]] = {}
    for frequency_parameters in benchmark.parameters_by_frequency.values():
        for parameter_id, value in frequency_parameters.items():
            bucket = values.setdefault(parameter_id, [])
            if value not in bucket:
                bucket.append(value)
    return {key: tuple(items) for key, items in values.items()}


def _seed_default_and_domain(
    seed: _BroadSurfaceSeed,
    *,
    benchmark_values: Mapping[str, tuple[Primitive, ...]],
) -> tuple[Primitive, tuple[Primitive, ...]]:
    exposed = benchmark_values.get(seed.parameter_id)
    if exposed:
        return exposed[0], exposed
    fixed_defaults: Mapping[str, Primitive] = {
        "input_transform": "log_close",
        "carrier_bar_interval": "carrier_frequency",
        "component_delta_order": 1,
        "flat_delta_policy": "carry_last_nonzero_direction",
        "position_mapping": "positive_delta_long_negative_delta_cash",
        "execution_lag_bars": 1,
    }
    default = fixed_defaults.get(seed.parameter_id, seed.formula_term)
    return default, (default,)


def _parameter_from_broad_seed(
    tool_id: str,
    seed: _BroadSurfaceSeed,
    *,
    benchmark_values: Mapping[str, tuple[Primitive, ...]],
) -> ToolParameterSpecV2:
    native_default, allowed_domain = _seed_default_and_domain(
        seed,
        benchmark_values=benchmark_values,
    )
    value_kind: ValueKind
    if isinstance(native_default, bool):
        value_kind = "boolean"
    elif isinstance(native_default, int):
        value_kind = "integer"
    elif isinstance(native_default, float):
        value_kind = "number"
    else:
        value_kind = "categorical"

    if seed.parameter_kind == "derived_formula":
        identity_effect: IdentityEffect = "derived"
        registration_status: RegistrationStatus = "derived"
        tunable_status: TunableStatus = "derived_only"
        affects_layers = ("transform",)
        semantic_role = "公式派生表面"
        invariant_reason = ""
    elif seed.parameter_kind == "fixed_design":
        identity_effect = "new_tool_version"
        registration_status = "registered"
        tunable_status = "not_tunable"
        affects_layers = ("transform",)
        semantic_role = "固定设计选择"
        invariant_reason = ""
    elif seed.parameter_kind == "decision_semantics":
        identity_effect = "signal_policy"
        registration_status = "registered"
        tunable_status = "not_tunable"
        affects_layers = ("decision",)
        semantic_role = "决策语义"
        invariant_reason = ""
    elif seed.parameter_kind == "execution_semantics":
        identity_effect = "execution_profile"
        registration_status = "registered"
        tunable_status = "not_tunable"
        affects_layers = ("execution",)
        semantic_role = "执行时点语义"
        invariant_reason = ""
    elif seed.parameter_kind == "external_execution":
        identity_effect = "execution_profile"
        registration_status = "registered"
        tunable_status = "not_tunable"
        affects_layers = ("execution", "evaluation")
        semantic_role = "外部执行成本"
        invariant_reason = ""
    elif seed.parameter_kind == "initialization_boundary":
        if seed.parameter_id.startswith("warmup"):
            identity_effect = "validity_only"
            affects_layers = ("validity",)
            semantic_role = "预热有效性边界"
        else:
            identity_effect = "new_tool_version"
            affects_layers = ("transform",)
            semantic_role = "因果初始化边界"
        registration_status = "registered"
        tunable_status = "not_tunable"
        invariant_reason = ""
    else:
        identity_effect = "same_tool_parameter"
        registration_status = "registered"
        tunable_status = "not_searchable_yet"
        affects_layers = ("transform",)
        semantic_role = "已暴露运行时参数"
        invariant_reason = ""

    return ToolParameterSpecV2(
        tool_id=tool_id,
        parameter_id=seed.parameter_id,
        name_zh=seed.name_zh,
        semantic_role=semantic_role,
        identity_effect=identity_effect,
        affects_layers=affects_layers,
        value_kind=value_kind,
        unit="category" if value_kind == "categorical" else "bars",
        time_basis=("execution_bar" if seed.parameter_kind in {"execution_semantics", "external_execution"} else "decision_bar"),
        native_default=native_default,
        allowed_domain=allowed_domain,
        derived_from=seed.derived_from,
        cross_parameter_constraints=seed.constraints,
        registration_status=registration_status,
        tunable_status=tunable_status,
        formula_term=seed.formula_term,
        implementation_refs=(seed.source_path,),
        invariant_reason=invariant_reason,
        v1_parameter_key=(seed.parameter_id if seed.parameter_id in benchmark_values else None),
        source_assertions=_source(seed.source_path, seed.source_token),
    )


def _spectral_foundation_parameters() -> tuple[ToolParameterSpecV2, ...]:
    seeds_by_tool = {
        "laplace_iir_mixed_bandpass": _LAPLACE_BROAD_SEEDS,
        "butterworth_clean_bandpass": _BUTTERWORTH_BROAD_SEEDS,
        "rolling_fourier_bandpass": _FOURIER_BROAD_SEEDS,
        "causal_haar_wavelet_bandpass": _HAAR_BROAD_SEEDS,
    }
    rows: list[ToolParameterSpecV2] = []
    for tool_id in V2_PARAMETER_CATALOG_MIGRATION_TOOL_IDS:
        seeds = seeds_by_tool.get(tool_id)
        if seeds is None:
            continue
        benchmark_values = _benchmark_values(tool_id)
        rows.extend(
            _parameter_from_broad_seed(
                tool_id,
                seed,
                benchmark_values=benchmark_values,
            )
            for seed in seeds
        )
    return tuple(rows)


def _remaining_formula_parameters(
    *,
    already_registered: frozenset[str],
) -> tuple[ToolParameterSpecV2, ...]:
    """Classify V1 formula effects not covered by rich or spectral contracts."""

    formulas = {item.tool_id: item for item in build_tool_formula_mechanism_bundle().tool_formulas}
    rows: list[ToolParameterSpecV2] = []
    for tool_id in V2_PARAMETER_CATALOG_MIGRATION_TOOL_IDS:
        if any(surface.startswith(f"{tool_id}:") for surface in already_registered):
            continue
        benchmark_values = _benchmark_values(tool_id)
        formula = formulas[tool_id]
        for effect in formula.parameter_effects:
            values = benchmark_values[effect.parameter_id]
            default = values[0]
            domain_key = (tool_id, effect.parameter_id)
            registered_domain = _REGISTERED_RESEARCH_DOMAINS.get(domain_key)
            if registered_domain is not None:
                if default not in registered_domain:
                    raise ValidationError("registered research domain must retain the immutable baseline")
                values = registered_domain
            if effect.parameter_id == "cost_bps":
                identity_effect: IdentityEffect = "execution_profile"
                tunable_status: TunableStatus = "not_tunable"
                affects_layers = ("execution", "evaluation")
            elif effect.benchmark_signal_relevance == "geometry_only":
                identity_effect = "tool_variant"
                tunable_status = "not_tunable"
                affects_layers = ("signal_geometry",)
            elif effect.benchmark_signal_relevance == "validity_only":
                identity_effect = "validity_only"
                tunable_status = "not_tunable"
                affects_layers = ("validity",)
            else:
                identity_effect = "same_tool_parameter"
                tunable_status = "not_searchable_yet"
                affects_layers = ("transform", "decision")
            value_kind: ValueKind
            if isinstance(default, bool):
                value_kind = "boolean"
            elif isinstance(default, int):
                value_kind = "integer"
            elif isinstance(default, float):
                value_kind = "number"
            else:
                value_kind = "categorical"
            domain_source_assertion = _RESEARCH_DOMAIN_SOURCE_ASSERTIONS.get(domain_key)
            source_assertions = list(_source(_REGISTRY_SOURCE, f'"{effect.parameter_id}"'))
            implementation_refs = [_REGISTRY_SOURCE]
            if domain_source_assertion is not None:
                source_assertions.append(domain_source_assertion)
                implementation_refs.append(domain_source_assertion.implementation_ref)
            rows.append(
                ToolParameterSpecV2(
                    tool_id=tool_id,
                    parameter_id=effect.parameter_id,
                    name_zh=effect.physical_meaning,
                    semantic_role=effect.physical_meaning,
                    identity_effect=identity_effect,
                    affects_layers=affects_layers,
                    value_kind=value_kind,
                    unit=("bps" if effect.parameter_id == "cost_bps" else "category" if value_kind == "categorical" else "bars"),
                    time_basis=("execution_bar" if effect.parameter_id == "cost_bps" else "decision_bar"),
                    native_default=default,
                    allowed_domain=values,
                    derived_from=(),
                    cross_parameter_constraints=(),
                    registration_status="registered",
                    tunable_status=tunable_status,
                    formula_term=effect.formula_term,
                    implementation_refs=tuple(implementation_refs),
                    invariant_reason="",
                    v1_parameter_key=effect.parameter_id,
                    source_assertions=tuple(source_assertions),
                )
            )
    return tuple(rows)


def _catalog_parameters() -> tuple[ToolParameterSpecV2, ...]:
    rich_parameters = (
        *_frequency_selective_bollinger_parameters(),
        *_butterworth_bandpass_parameters(),
        *_lowpass_residual_parameters(),
    )
    registered = {item.surface_id for item in rich_parameters}
    spectral_parameters = tuple(item for item in _spectral_foundation_parameters() if item.surface_id not in registered)
    registered.update(item.surface_id for item in spectral_parameters)
    return (
        *rich_parameters,
        *spectral_parameters,
        *_remaining_formula_parameters(
            already_registered=frozenset(registered),
        ),
    )


@dataclass(frozen=True, slots=True)
class ToolParameterCatalogV2:
    """Read-only V2 catalog for the complete 13-tool timing universe."""

    parameters: tuple[ToolParameterSpecV2, ...]
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("V2 parameter catalog cannot grant authority")
        keys = [(item.tool_id, item.parameter_id) for item in self.parameters]
        if len(keys) != len(set(keys)):
            raise ValidationError("V2 parameter catalog contains duplicate identities")
        catalog_tools = {item.tool_id for item in self.parameters}
        if catalog_tools != set(V2_PARAMETER_CATALOG_MIGRATION_TOOL_IDS):
            raise ValidationError("V2 parameter catalog migration scope is incomplete")
        validate_v1_benchmark_parameter_projection(self)

    def parameters_for(self, tool_id: str) -> tuple[ToolParameterSpecV2, ...]:
        return tuple(item for item in self.parameters if item.tool_id == tool_id)

    def parameter(self, tool_id: str, parameter_id: str) -> ToolParameterSpecV2:
        for item in self.parameters_for(tool_id):
            if item.parameter_id == parameter_id:
                return item
        raise ValidationError(f"unregistered V2 surface: {tool_id}:{parameter_id}")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": TOOL_PARAMETER_CATALOG_V2_SCHEMA_ID,
            "catalog_version": TOOL_PARAMETER_CATALOG_V2_VERSION,
            "migration_tool_ids": list(V2_PARAMETER_CATALOG_MIGRATION_TOOL_IDS),
            "parameters": [item.to_dict() for item in self.parameters],
            "production_authority": self.production_authority,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "field_labels_zh": {
                "parameters": "V2公式表面参数目录",
                "identity_effect": "是否保持同一工具身份",
                "registration_status": "公式表面登记状态",
                "tunable_status": "是否已获实验搜索许可",
                "source_assertions": "源码常量或构造器的可审计见证",
            },
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload


def build_tool_parameter_catalog_v2() -> ToolParameterCatalogV2:
    """Build the fixed V2 ontology without creating an experiment."""

    return ToolParameterCatalogV2(parameters=_catalog_parameters())


def validate_v1_benchmark_parameter_projection(
    catalog: ToolParameterCatalogV2,
) -> None:
    """Require every V1 key to be classified without hiding V2 adapter fields.

    A V2 formula field may be connected to the native adapter before the
    immutable V1 benchmark dictionary is expanded.  The projection therefore
    proves that V1 has no unclassified exposed key; it does not require the
    V2 catalog to be limited to that historical dictionary.
    """

    benchmarks = {item.tool_id: item for item in tool_benchmark_specs() if item.tool_id in V2_PARAMETER_CATALOG_MIGRATION_TOOL_IDS}
    if set(benchmarks) != set(V2_PARAMETER_CATALOG_MIGRATION_TOOL_IDS):
        raise ValidationError("V2 migration tool lacks a V1 benchmark")
    for tool_id, benchmark in benchmarks.items():
        exposed = {key for values in benchmark.parameters_by_frequency.values() for key in values}
        mapped = {item.v1_parameter_key: item for item in catalog.parameters_for(tool_id) if item.v1_parameter_key is not None}
        classified = set(mapped)
        missing = exposed - classified
        if missing:
            details = f"missing={sorted(missing)} classified={sorted(classified)}"
            raise ValidationError(f"V1 benchmark projection mismatch for {tool_id}: {details}")


def validate_no_direct_derived_assignment(
    catalog: ToolParameterCatalogV2,
    *,
    tool_id: str,
    assignment: Mapping[str, Primitive],
) -> None:
    """Reject an attempted direct assignment to a derived V2 quantity."""

    for parameter_id in assignment:
        parameter = catalog.parameter(tool_id, parameter_id)
        if parameter.identity_effect == "derived":
            raise ValidationError(f"derived quantity cannot be assigned directly: {parameter.surface_id}")


def catalog_source_files(catalog: ToolParameterCatalogV2) -> tuple[Path, ...]:
    """Expose source paths for the separate formula-surface truth audit."""

    return tuple(
        sorted({Path(assertion.implementation_ref) for parameter in catalog.parameters for assertion in parameter.source_assertions})
    )


__all__ = [
    "IdentityEffect",
    "Primitive",
    "SPECTRAL_FOUNDATION_SURFACE_IDS",
    "SourceSurfaceAssertion",
    "TOOL_PARAMETER_CATALOG_V2_SCHEMA_ID",
    "TOOL_PARAMETER_CATALOG_V2_VERSION",
    "ToolParameterCatalogV2",
    "ToolParameterSpecV2",
    "build_tool_parameter_catalog_v2",
    "catalog_source_files",
    "validate_no_direct_derived_assignment",
    "validate_v1_benchmark_parameter_projection",
]
