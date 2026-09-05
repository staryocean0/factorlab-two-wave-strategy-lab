# pyright: reportAny=false, reportArgumentType=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Concrete timing-tool dictionary for market-state affinity research.

Strategies are discovery provenance only.  The stable identity is ``tool_id``:
one mathematical tool can be reused by many strategies without becoming a new
dictionary entry, and two tools in the same family remain separate evidence
subjects.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.method_registry import method_family_specs

TOOL_REGISTRY_SCHEMA_ID = "market_state_tool_registry@1.2"
TOOL_REGISTRY_VERSION = "tool_registry_v1_2"
TOOL_SOURCE_DISCOVERY_SCHEMA_ID = "market_state_tool_source_inventory@1.2"

DISCOVERED_TOOL_IDS = (
    "laplace_iir_mixed_bandpass",
    "laplace_iir_lowpass",
    "butterworth_clean_bandpass",
    "rolling_fourier_bandpass",
    "causal_haar_wavelet_bandpass",
    "r3_nested_moving_average_component",
    "bollinger_volatility_channel",
    "frequency_selective_bollinger_channel",
    "butterworth_lowpass_residual_envelope",
    "causal_asymmetric_arc_state_space_envelope",
    "donchian_price_channel",
    "causal_trendline_channel",
    "simple_moving_average_trend",
)

# C1.2 closes the old 15m deferral.  Discovery, registration, benchmark and
# evidence coverage are now the same frozen 13-tool universe.
REQUIRED_TOOL_IDS = DISCOVERED_TOOL_IDS

# The V2 ontology now classifies the complete frozen V1.2 tool universe.
# Registration/audit coverage still grants no parameter-search, routing, or
# production authority.
V2_PARAMETER_CATALOG_MIGRATION_TOOL_IDS = DISCOVERED_TOOL_IDS

TOOL_DISCOVERY_SOURCES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "laplace_iir_mixed_bandpass": (
            "src/factor_lab/filtering/timing_validation.py",
            "src/factor_lab/filtering/cloudridge_3_0_frequency_trade_quality.py",
        ),
        "laplace_iir_lowpass": (
            "src/factor_lab/filtering/cloudridge_greenwave_v6_adaptive_super_bull.py",
            "src/factor_lab/filtering/cloudridge_lowpass_force_long.py",
        ),
        "butterworth_clean_bandpass": (
            "src/factor_lab/filtering/cloudridge_3_0_hybrid_filter_bank.py",
            "src/factor_lab/filtering/cloudridge_3_0_frequency_trade_quality.py",
        ),
        "rolling_fourier_bandpass": (
            "src/factor_lab/filtering/timing_validation.py",
            "src/factor_lab/filtering/opportunity_density.py",
        ),
        "causal_haar_wavelet_bandpass": (
            "src/factor_lab/filtering/timing_validation.py",
            "src/factor_lab/filtering/opportunity_density.py",
        ),
        "r3_nested_moving_average_component": (
            "src/factor_lab/filtering/independent_long_experts.py",
            "src/factor_lab/filtering/cloudridge_iir_bar_expert_migration_adapters_v2.py",
        ),
        "bollinger_volatility_channel": ("src/factor_lab/strategy/services/risk_off_v58_bollinger_cash_entry_tuning.py",),
        "frequency_selective_bollinger_channel": (
            "src/factor_lab/strategy/services/risk_off_v58_frequency_bollinger.py",
            "src/factor_lab/strategy/services/risk_off_v58_channel_inertia_width.py",
        ),
        "butterworth_lowpass_residual_envelope": ("src/factor_lab/strategy/services/risk_off_v58_lowpass_residual_envelope.py",),
        "causal_asymmetric_arc_state_space_envelope": ("src/factor_lab/strategy/services/risk_off_v57_asymmetric_arc_envelope.py",),
        "donchian_price_channel": (
            "src/factor_lab/filtering/independent_long_experts.py",
            "src/factor_lab/filtering/cloudridge_greenwave_v5_effective_channel_break.py",
        ),
        "causal_trendline_channel": (
            "src/factor_lab/filtering/cloudridge_v6_crash_channel_confirmation.py",
            "src/factor_lab/strategy/services/risk_off_v56_steep_crash_specialist.py",
        ),
        "simple_moving_average_trend": ("src/factor_lab/filtering/timing_validation.py",),
    }
)

REQUIRED_ACTION_ROLES = ("long_capture", "cash_avoidance")

REQUIRED_EFFECT_METRICS = (
    "net_log_return_per_decision_bar",
    "positive_return_rate",
    "gain_loss_ratio",
    "turnover_per_decision_bar",
    "trade_win_rate",
    "trade_payoff_ratio",
    "trade_expectancy",
)

# ``specialist`` is admitted for append-only registry extensions.  The frozen
# V1.2 payload still emits only its original three categories and 13 tools.
TOOL_CATEGORY_IDS = ("filtering", "channel", "trend", "specialist")


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """One concrete, reusable mathematical timing tool."""

    tool_id: str
    tool_category_id: str
    method_family_id: str
    name_zh: str
    aliases: tuple[str, ...]
    mathematical_object: str
    input_semantics: str
    output_semantics: str
    supported_action_roles: tuple[str, ...]
    benchmark_status: str
    status_reason: str
    source_strategy_refs: tuple[str, ...]
    production_authority: bool = False

    def __post_init__(self) -> None:
        text_fields = {
            "tool_id": self.tool_id,
            "tool_category_id": self.tool_category_id,
            "method_family_id": self.method_family_id,
            "name_zh": self.name_zh,
            "mathematical_object": self.mathematical_object,
            "input_semantics": self.input_semantics,
            "output_semantics": self.output_semantics,
            "benchmark_status": self.benchmark_status,
        }
        for field, value in text_fields.items():
            if not value.strip():
                raise ValidationError(f"tool {field} is required")
        if self.tool_category_id not in TOOL_CATEGORY_IDS:
            raise ValidationError(f"unsupported tool category: {self.tool_category_id}")
        families = {item.method_family_id for item in method_family_specs()}
        if self.method_family_id not in families:
            raise ValidationError(f"unregistered method family: {self.method_family_id}")
        if self.benchmark_status not in {"benchmarked", "deferred", "rejected"}:
            raise ValidationError("tool benchmark_status is invalid")
        if self.benchmark_status != "benchmarked" and not self.status_reason.strip():
            raise ValidationError("non-benchmarked tool requires status_reason")
        if tuple(self.supported_action_roles) != REQUIRED_ACTION_ROLES:
            raise ValidationError("V1.1 tools must expose long and cash-avoidance lenses")
        if not self.aliases or any(not item.strip() for item in self.aliases):
            raise ValidationError("tool aliases are required")
        if not self.source_strategy_refs or any(not item.strip() for item in self.source_strategy_refs):
            raise ValidationError("tool source_strategy_refs are required")
        if self.production_authority:
            raise ValidationError("tool dictionary cannot grant production authority")

    def to_dict(self) -> dict[str, object]:
        return {
            "tool_id": self.tool_id,
            "tool_category_id": self.tool_category_id,
            "method_family_id": self.method_family_id,
            "name_zh": self.name_zh,
            "aliases": list(self.aliases),
            "mathematical_object": self.mathematical_object,
            "input_semantics": self.input_semantics,
            "output_semantics": self.output_semantics,
            "supported_action_roles": list(self.supported_action_roles),
            "benchmark_status": self.benchmark_status,
            "status_reason": self.status_reason,
            "source_strategy_refs": list(self.source_strategy_refs),
            "source_refs_are_identity": False,
            "production_authority": self.production_authority,
        }


@dataclass(frozen=True, slots=True)
class ToolBenchmarkSpec:
    """Frozen causal probe for one concrete tool."""

    benchmark_id: str
    tool_id: str
    method_family_id: str
    name_zh: str
    signal_semantics: str
    parameters_by_frequency: Mapping[str, Mapping[str, float | int | str]]
    action_roles: tuple[str, ...] = REQUIRED_ACTION_ROLES
    effect_metric_ids: tuple[str, ...] = REQUIRED_EFFECT_METRICS
    comparator_method_id: str = "cash_zero_return"
    production_authority: bool = False

    def __post_init__(self) -> None:
        for field in (
            "benchmark_id",
            "tool_id",
            "method_family_id",
            "name_zh",
            "signal_semantics",
            "comparator_method_id",
        ):
            if not str(getattr(self, field)).strip():
                raise ValidationError(f"benchmark {field} is required")
        tools = {item.tool_id: item for item in tool_specs()}
        if self.tool_id not in tools:
            raise ValidationError(f"benchmark tool is unregistered: {self.tool_id}")
        if tools[self.tool_id].method_family_id != self.method_family_id:
            raise ValidationError("benchmark method family does not match tool")
        if tuple(self.action_roles) != REQUIRED_ACTION_ROLES:
            raise ValidationError("benchmark action-role coverage is incomplete")
        if tuple(self.effect_metric_ids) != REQUIRED_EFFECT_METRICS:
            raise ValidationError("benchmark metric coverage is incomplete")
        params = {str(frequency): MappingProxyType(dict(values)) for frequency, values in self.parameters_by_frequency.items()}
        supported_frequencies = {"1d", "60m", "15m"}
        if not params or not set(params).issubset(supported_frequencies):
            raise ValidationError("tool benchmark must freeze at least one supported carrier frequency")
        if any(float(values.get("cost_bps", -1.0)) < 0.0 for values in params.values()):
            raise ValidationError("tool benchmark cost_bps must be non-negative")
        object.__setattr__(self, "parameters_by_frequency", MappingProxyType(params))
        if self.production_authority:
            raise ValidationError("tool benchmark cannot grant production authority")

    def to_dict(self) -> dict[str, object]:
        return {
            "benchmark_id": self.benchmark_id,
            "tool_id": self.tool_id,
            "method_family_id": self.method_family_id,
            "name_zh": self.name_zh,
            "signal_semantics": self.signal_semantics,
            "parameters_by_frequency": {frequency: dict(values) for frequency, values in sorted(self.parameters_by_frequency.items())},
            "action_roles": list(self.action_roles),
            "effect_metric_ids": list(self.effect_metric_ids),
            "comparator_method_id": self.comparator_method_id,
            "production_authority": self.production_authority,
        }


def tool_specs() -> tuple[ToolSpec, ...]:
    """Return the governed V1.2 core tool dictionary."""

    roles = REQUIRED_ACTION_ROLES
    return (
        ToolSpec(
            tool_id="laplace_iir_mixed_bandpass",
            tool_category_id="filtering",
            method_family_id="causal_bandpass_mixed",
            name_zh="Laplace/IIR 混合带通",
            aliases=("IIR", "Laplace", "RIR", "IARR", "混合带通"),
            mathematical_object="causal second-order biquad band-pass component",
            input_semantics="log close sampled at the carrier bar frequency",
            output_semantics="long while the causal component delta is positive",
            supported_action_roles=roles,
            benchmark_status="benchmarked",
            status_reason="",
            source_strategy_refs=(
                "src/factor_lab/filtering/timing_validation.py",
                "src/factor_lab/filtering/cloudridge_3_0_frequency_trade_quality.py",
            ),
        ),
        ToolSpec(
            tool_id="laplace_iir_lowpass",
            tool_category_id="filtering",
            method_family_id="causal_lowpass_state",
            name_zh="Laplace/IIR 低通背景",
            aliases=("IIR低通", "Laplace低通", "P300低通", "lowpass IIR"),
            mathematical_object="causal second-order biquad low-pass level",
            input_semantics="log close sampled at the carrier bar frequency",
            output_semantics="long while the causal low-pass level slope is positive",
            supported_action_roles=roles,
            benchmark_status="benchmarked",
            status_reason="",
            source_strategy_refs=(
                "src/factor_lab/filtering/cloudridge_greenwave_v6_adaptive_super_bull.py",
                "src/factor_lab/filtering/cloudridge_lowpass_force_long.py",
            ),
        ),
        ToolSpec(
            tool_id="butterworth_clean_bandpass",
            tool_category_id="filtering",
            method_family_id="causal_bandpass_clean",
            name_zh="巴特沃斯干净带通",
            aliases=("Butterworth", "巴特沃斯", "干净带通", "clean bandpass"),
            mathematical_object="causal SOS Butterworth filter with explicit band edges",
            input_semantics="log close sampled at the carrier bar frequency",
            output_semantics="long while the causal component delta is positive",
            supported_action_roles=roles,
            benchmark_status="benchmarked",
            status_reason="",
            source_strategy_refs=(
                "src/factor_lab/filtering/cloudridge_3_0_hybrid_filter_bank.py",
                "src/factor_lab/filtering/cloudridge_3_0_frequency_trade_quality.py",
            ),
        ),
        ToolSpec(
            tool_id="rolling_fourier_bandpass",
            tool_category_id="filtering",
            method_family_id="multiscale_basis",
            name_zh="滚动傅里叶带通",
            aliases=("Fourier", "傅里叶", "滚动频谱", "Fourier bandpass"),
            mathematical_object=("strictly causal rolling discrete Fourier projection over a frozen pass band"),
            input_semantics="log close sampled at the carrier bar frequency",
            output_semantics="long while the reconstructed component delta is positive",
            supported_action_roles=roles,
            benchmark_status="benchmarked",
            status_reason="",
            source_strategy_refs=TOOL_DISCOVERY_SOURCES["rolling_fourier_bandpass"],
        ),
        ToolSpec(
            tool_id="causal_haar_wavelet_bandpass",
            tool_category_id="filtering",
            method_family_id="multiscale_basis",
            name_zh="因果 Haar 小波带通",
            aliases=("Haar", "小波", "Haar wavelet", "小波带通"),
            mathematical_object=("strictly causal rolling Haar approximation difference between two frozen levels"),
            input_semantics="log close sampled at the carrier bar frequency",
            output_semantics="long while the reconstructed component delta is positive",
            supported_action_roles=roles,
            benchmark_status="benchmarked",
            status_reason="",
            source_strategy_refs=TOOL_DISCOVERY_SOURCES["causal_haar_wavelet_bandpass"],
        ),
        ToolSpec(
            tool_id="r3_nested_moving_average_component",
            tool_category_id="filtering",
            method_family_id="causal_bandpass_mixed",
            name_zh="R3 嵌套均线分量",
            aliases=("R3", "嵌套均线", "SMA64残差", "nested SMA component"),
            mathematical_object=("slow SMA of log price minus its fast SMA, forming a mixed finite-response band component"),
            input_semantics="log close sampled at the carrier bar frequency",
            output_semantics="long while the nested component delta is positive",
            supported_action_roles=roles,
            benchmark_status="benchmarked",
            status_reason="",
            source_strategy_refs=TOOL_DISCOVERY_SOURCES["r3_nested_moving_average_component"],
        ),
        ToolSpec(
            tool_id="bollinger_volatility_channel",
            tool_category_id="channel",
            method_family_id="volatility_channel",
            name_zh="布林波动通道",
            aliases=("Bollinger", "布林", "波动通道", "volatility channel"),
            mathematical_object="causal rolling location plus volatility envelope",
            input_semantics="observable close and strictly prior rolling envelope",
            output_semantics="enter above prior upper rail and exit below prior centre",
            supported_action_roles=roles,
            benchmark_status="benchmarked",
            status_reason="",
            source_strategy_refs=TOOL_DISCOVERY_SOURCES["bollinger_volatility_channel"],
        ),
        ToolSpec(
            tool_id="frequency_selective_bollinger_channel",
            tool_category_id="channel",
            method_family_id="volatility_channel",
            name_zh="频率选择性布林通道",
            aliases=("频率布林", "V58布林", "frequency Bollinger"),
            mathematical_object=("causal low-pass centre with independently estimated high-pass/band-pass RMS thickness"),
            input_semantics="15m log close and frozen frequency-selective components",
            output_semantics="channel state from centre direction and residual rails",
            supported_action_roles=roles,
            benchmark_status="benchmarked",
            status_reason="",
            source_strategy_refs=TOOL_DISCOVERY_SOURCES["frequency_selective_bollinger_channel"],
        ),
        ToolSpec(
            tool_id="butterworth_lowpass_residual_envelope",
            tool_category_id="channel",
            method_family_id="volatility_channel",
            name_zh="巴特沃斯低通残差包络",
            aliases=("低通残差包络", "V58残差轨", "residual envelope"),
            mathematical_object=(
                "causal Butterworth low-pass centre plus independently estimated asymmetric high-pass residual quantile rails"
            ),
            input_semantics="15m log close with frozen low/high frequency separation",
            output_semantics=("causal low-pass centre and asymmetric residual rails; geometry declares no native trade action"),
            supported_action_roles=roles,
            benchmark_status="benchmarked",
            status_reason="",
            source_strategy_refs=TOOL_DISCOVERY_SOURCES["butterworth_lowpass_residual_envelope"],
        ),
        ToolSpec(
            tool_id="causal_asymmetric_arc_state_space_envelope",
            tool_category_id="filtering",
            method_family_id="state_space_filter",
            name_zh="因果非对称弧形状态空间包络",
            aliases=("V57", "弧形包络", "EKF弧形", "asymmetric arc"),
            mathematical_object=(
                "nonlinear causal state-space oscillator with rounded-top/sharp-bottom geometry and innovation-quantile envelope"
            ),
            input_semantics="15m log close and causal nonlinear state updates",
            output_semantics=("latent centre and asymmetric innovation rails; geometry declares no native trade action"),
            supported_action_roles=roles,
            benchmark_status="benchmarked",
            status_reason="",
            source_strategy_refs=TOOL_DISCOVERY_SOURCES["causal_asymmetric_arc_state_space_envelope"],
        ),
        ToolSpec(
            tool_id="donchian_price_channel",
            tool_category_id="channel",
            method_family_id="price_channel",
            name_zh="Donchian 价格通道",
            aliases=("Donchian", "价格通道", "price channel", "突破通道"),
            mathematical_object="causal rolling observable-price extrema envelope",
            input_semantics="OHLC and strictly prior rolling extrema",
            output_semantics="enter above prior high and exit below prior low",
            supported_action_roles=roles,
            benchmark_status="benchmarked",
            status_reason="",
            source_strategy_refs=(
                "src/factor_lab/filtering/independent_long_experts.py",
                "src/factor_lab/filtering/cloudridge_greenwave_v5_effective_channel_break.py",
            ),
        ),
        ToolSpec(
            tool_id="causal_trendline_channel",
            tool_category_id="channel",
            method_family_id="graph_structure",
            name_zh="因果趋势线回归通道",
            aliases=("trendline", "趋势线", "图形通道", "回归通道"),
            mathematical_object="strictly-prior rolling OLS centreline and residual rail",
            input_semantics="log close observations strictly before the decision bar",
            output_semantics="long when prior slope is positive and close holds above lower rail",
            supported_action_roles=roles,
            benchmark_status="benchmarked",
            status_reason="",
            source_strategy_refs=TOOL_DISCOVERY_SOURCES["causal_trendline_channel"],
        ),
        ToolSpec(
            tool_id="simple_moving_average_trend",
            tool_category_id="trend",
            method_family_id="moving_average_trend",
            name_zh="双均线趋势",
            aliases=("moving average", "均线", "SMA", "双均线"),
            mathematical_object="ordering of causal fast and slow simple moving averages",
            input_semantics="close observations through the decision bar",
            output_semantics="long while fast SMA is above slow SMA",
            supported_action_roles=roles,
            benchmark_status="benchmarked",
            status_reason="",
            source_strategy_refs=("src/factor_lab/filtering/timing_validation.py",),
        ),
    )


def tool_benchmark_specs() -> tuple[ToolBenchmarkSpec, ...]:
    """Return one frozen benchmark for every core tool."""

    return (
        ToolBenchmarkSpec(
            benchmark_id="causal_bandpass_filter_benchmark_v1",
            tool_id="laplace_iir_mixed_bandpass",
            method_family_id="causal_bandpass_mixed",
            name_zh="固定参数 Laplace/IIR 混合带通基准",
            signal_semantics="component delta direction; signal at close, execute next bar",
            parameters_by_frequency={
                "1d": {"period_bars": 40, "q": 1.0, "cost_bps": 7.0},
                "60m": {"period_bars": 160, "q": 1.0, "cost_bps": 7.0},
            },
        ),
        ToolBenchmarkSpec(
            benchmark_id="causal_lowpass_filter_benchmark_v1",
            tool_id="laplace_iir_lowpass",
            method_family_id="causal_lowpass_state",
            name_zh="固定参数 Laplace/IIR 低通背景基准",
            signal_semantics="low-pass level slope; signal at close, execute next bar",
            parameters_by_frequency={
                "1d": {"period_bars": 75, "q": 1.0, "cost_bps": 7.0},
                "60m": {"period_bars": 300, "q": 1.0, "cost_bps": 7.0},
            },
        ),
        ToolBenchmarkSpec(
            benchmark_id="butterworth_clean_bandpass_benchmark_v1",
            tool_id="butterworth_clean_bandpass",
            method_family_id="causal_bandpass_clean",
            name_zh="固定通带巴特沃斯基准",
            signal_semantics="component delta direction; signal at close, execute next bar",
            parameters_by_frequency={
                "1d": {
                    "short_period_bars": 28,
                    "long_period_bars": 57,
                    "order": 4,
                    "cost_bps": 7.0,
                },
                "60m": {
                    "short_period_bars": 113,
                    "long_period_bars": 226,
                    "order": 4,
                    "cost_bps": 7.0,
                },
            },
        ),
        ToolBenchmarkSpec(
            benchmark_id="rolling_fourier_bandpass_benchmark_v1",
            tool_id="rolling_fourier_bandpass",
            method_family_id="multiscale_basis",
            name_zh="固定通带滚动傅里叶基准",
            signal_semantics=("rolling Fourier component delta direction; signal at close, execute next bar"),
            parameters_by_frequency={
                "1d": {
                    "window_bars": 256,
                    "low_period_bars": 20,
                    "high_period_bars": 80,
                    "cost_bps": 7.0,
                },
                "60m": {
                    "window_bars": 1024,
                    "low_period_bars": 80,
                    "high_period_bars": 320,
                    "cost_bps": 7.0,
                },
            },
        ),
        ToolBenchmarkSpec(
            benchmark_id="causal_haar_wavelet_bandpass_benchmark_v1",
            tool_id="causal_haar_wavelet_bandpass",
            method_family_id="multiscale_basis",
            name_zh="固定层级因果 Haar 小波带通基准",
            signal_semantics=("rolling Haar level-difference component direction; signal at close, execute next bar"),
            parameters_by_frequency={
                "1d": {
                    "window_bars": 128,
                    "level": 2,
                    "slow_level": 5,
                    "cost_bps": 7.0,
                },
                "60m": {
                    "window_bars": 512,
                    "level": 2,
                    "slow_level": 5,
                    "cost_bps": 7.0,
                },
            },
        ),
        ToolBenchmarkSpec(
            benchmark_id="r3_nested_moving_average_component_benchmark_v1",
            tool_id="r3_nested_moving_average_component",
            method_family_id="causal_bandpass_mixed",
            name_zh="固定参数 R3 嵌套均线分量基准",
            signal_semantics=("delta of slow-SMA(logP-fast-SMA(logP)); signal at close, execute next bar"),
            parameters_by_frequency={
                "1d": {
                    "fast_window_bars": 2,
                    "slow_window_bars": 16,
                    "cost_bps": 7.0,
                },
                "60m": {
                    "fast_window_bars": 8,
                    "slow_window_bars": 64,
                    "cost_bps": 7.0,
                },
            },
        ),
        ToolBenchmarkSpec(
            benchmark_id="volatility_channel_benchmark_v1",
            tool_id="bollinger_volatility_channel",
            method_family_id="volatility_channel",
            name_zh="固定参数布林波动通道基准",
            signal_semantics="enter above prior mean + 2 sigma; exit below prior mean",
            parameters_by_frequency={
                "1d": {"window_bars": 20, "width_sigma": 2.0, "cost_bps": 7.0},
                "60m": {"window_bars": 80, "width_sigma": 2.0, "cost_bps": 7.0},
            },
        ),
        ToolBenchmarkSpec(
            benchmark_id="frequency_selective_bollinger_benchmark_v1",
            tool_id="frequency_selective_bollinger_channel",
            method_family_id="volatility_channel",
            name_zh="15分钟频率选择性布林通道原生基准",
            signal_semantics=("V58原实现：P48低通中轨、P24-P48带通厚度、趋势突破状态；收盘判定，下一根15分钟K线计收益"),
            parameters_by_frequency={
                "15m": {
                    "period_bars": 48,
                    "thickness_source": "bandpass",
                    "window_multiplier": 2.0,
                    "width_multiplier": 1.0,
                    "action": "trend_breakout",
                    "filter_order": 4,
                    "cost_bps": 7.0,
                }
            },
        ),
        ToolBenchmarkSpec(
            benchmark_id="lowpass_residual_envelope_benchmark_v1",
            tool_id="butterworth_lowpass_residual_envelope",
            method_family_id="volatility_channel",
            name_zh="15分钟巴特沃斯低通残差包络原生基准",
            signal_semantics=("V58原生几何的低通中轨方向探针；包络本身不虚构交易规则，收盘中轨方向判定，下一根15分钟K线计收益"),
            parameters_by_frequency={
                "15m": {
                    "cutoff_period_bars": 96,
                    "lowpass_order": 4,
                    "thickness_window_bars": 64,
                    "thickness_lower_quantile": 0.10,
                    "thickness_upper_quantile": 0.90,
                    "thickness_smoothing_half_life_bars": 6.0,
                    "warmup_bars": 512,
                    "cost_bps": 7.0,
                }
            },
        ),
        ToolBenchmarkSpec(
            benchmark_id="asymmetric_arc_state_space_envelope_benchmark_v1",
            tool_id="causal_asymmetric_arc_state_space_envelope",
            method_family_id="state_space_filter",
            name_zh="15分钟因果非对称弧形状态空间包络原生基准",
            signal_semantics=("V57原生四模型弧形中轨方向探针；收盘中轨方向判定，下一根15分钟K线计收益"),
            parameters_by_frequency={
                "15m": {
                    "candidate_period_1": 64,
                    "candidate_period_2": 128,
                    "candidate_period_3": 256,
                    "candidate_period_4": 512,
                    "round_top_sharp_bottom_ratio": 0.15,
                    "initial_amplitude_log": 0.012,
                    "initial_observation_sigma_log": 0.004,
                    "score_half_life_bars": 96.0,
                    "model_weight_half_life_bars": 12.0,
                    "model_score_temperature": 0.20,
                    "observation_variance_half_life_bars": 64.0,
                    "thickness_window_bars": 64,
                    "thickness_lower_quantile": 0.10,
                    "thickness_upper_quantile": 0.90,
                    "thickness_smoothing_half_life_bars": 6.0,
                    "warmup_bars": 512,
                    "cost_bps": 7.0,
                }
            },
        ),
        ToolBenchmarkSpec(
            benchmark_id="price_channel_benchmark_v1",
            tool_id="donchian_price_channel",
            method_family_id="price_channel",
            name_zh="固定参数价格通道基准",
            signal_semantics="enter above prior high; exit below prior low",
            parameters_by_frequency={
                "1d": {
                    "entry_window_bars": 20,
                    "exit_window_bars": 10,
                    "cost_bps": 7.0,
                },
                "60m": {
                    "entry_window_bars": 80,
                    "exit_window_bars": 40,
                    "cost_bps": 7.0,
                },
            },
        ),
        ToolBenchmarkSpec(
            benchmark_id="causal_trendline_channel_benchmark_v1",
            tool_id="causal_trendline_channel",
            method_family_id="graph_structure",
            name_zh="固定参数因果趋势线回归通道基准",
            signal_semantics="strictly-prior OLS slope positive and close above lower rail",
            parameters_by_frequency={
                "1d": {"window_bars": 40, "rail_sigma": 1.5, "cost_bps": 7.0},
                "60m": {"window_bars": 160, "rail_sigma": 1.5, "cost_bps": 7.0},
            },
        ),
        ToolBenchmarkSpec(
            benchmark_id="moving_average_trend_benchmark_v1",
            tool_id="simple_moving_average_trend",
            method_family_id="moving_average_trend",
            name_zh="固定参数双均线趋势基准",
            signal_semantics="fast SMA above slow SMA; signal at close, execute next bar",
            parameters_by_frequency={
                "1d": {
                    "fast_window_bars": 20,
                    "slow_window_bars": 60,
                    "cost_bps": 7.0,
                },
                "60m": {
                    "fast_window_bars": 80,
                    "slow_window_bars": 240,
                    "cost_bps": 7.0,
                },
            },
        ),
    )


def build_tool_registry_payload() -> dict[str, object]:
    """Return the complete dictionary and its frozen benchmark coverage."""

    tools = tool_specs()
    benchmarks = tool_benchmark_specs()
    if tuple(item.tool_id for item in tools) != DISCOVERED_TOOL_IDS:
        raise ValidationError("discovered tool registry is incomplete or reordered")
    if tuple(item.tool_id for item in benchmarks) != REQUIRED_TOOL_IDS:
        raise ValidationError("core tool benchmark coverage is incomplete or reordered")
    return {
        "schema_id": TOOL_REGISTRY_SCHEMA_ID,
        "registry_version": TOOL_REGISTRY_VERSION,
        "dictionary_identity": "tool_id",
        "strategy_refs_are_provenance_only": True,
        "production_authority": False,
        "tool_categories": [
            {"tool_category_id": "filtering", "name_zh": "滤波工具"},
            {"tool_category_id": "channel", "name_zh": "通道与图形工具"},
            {"tool_category_id": "trend", "name_zh": "趋势工具"},
        ],
        "method_families": [item.to_dict() for item in method_family_specs()],
        "tools": [item.to_dict() for item in tools],
        "benchmarks": [item.to_dict() for item in benchmarks],
        "required_effect_metrics": list(REQUIRED_EFFECT_METRICS),
        "field_labels_zh": {
            "tools": "具体择时工具",
            "source_strategy_refs": "发现来源（不参与工具身份）",
            "benchmarks": "冻结的非生产工具基准",
            "required_effect_metrics": "最低绩效指标集合",
            "production_authority": "生产授权",
        },
    }


def build_tool_source_inventory_payload() -> dict[str, object]:
    """Return the independent repo-source discovery ledger.

    This payload deliberately does not call :func:`tool_specs`.  Its job is to
    stop the registry from proving its own completeness: source discovery and
    registry coverage are reconciled only after both artifacts exist.
    """

    if tuple(TOOL_DISCOVERY_SOURCES) != DISCOVERED_TOOL_IDS:
        raise ValidationError("tool source discovery inventory is incomplete or reordered")
    return {
        "schema_id": TOOL_SOURCE_DISCOVERY_SCHEMA_ID,
        "discovery_version": "repo_tool_source_scan_v1_2",
        "discovery_scope": [
            "src/factor_lab/filtering",
            "src/factor_lab/strategy/services",
        ],
        "identity_policy": ("concrete mathematical tool; strategy/version paths are provenance only"),
        "discovered_tools": [
            {
                "tool_id": tool_id,
                "source_strategy_refs": list(TOOL_DISCOVERY_SOURCES[tool_id]),
                "discovery_basis": "repo source implementation and authority narrative",
            }
            for tool_id in DISCOVERED_TOOL_IDS
        ],
        "production_authority": False,
    }


def build_tool_coverage_report(
    source_inventory: Mapping[str, object],
    registry: Mapping[str, object],
    *,
    evidence_tool_ids: set[str],
    evidence_metric_ids: set[str],
    evidence_action_roles: set[str],
) -> dict[str, object]:
    """Reconcile discovered, registered, benchmarked and evidenced tools."""

    raw_discovered = source_inventory.get("discovered_tools")
    if not isinstance(raw_discovered, list):
        raise ValidationError("tool source inventory is missing discovered_tools")
    discovered_rows = [item for item in raw_discovered if isinstance(item, dict)]
    discovered = {str(item.get("tool_id", "")) for item in discovered_rows}
    raw_tools = registry.get("tools")
    if not isinstance(raw_tools, list):
        raise ValidationError("tool registry payload is missing tools")
    rows = [item for item in raw_tools if isinstance(item, dict)]
    registered = {str(item.get("tool_id", "")) for item in rows}
    benchmarked = {str(item.get("tool_id", "")) for item in rows if item.get("benchmark_status") == "benchmarked"}
    deferred = {str(item.get("tool_id", "")) for item in rows if item.get("benchmark_status") == "deferred"}
    required_tools: set[str] = {str(item) for item in REQUIRED_TOOL_IDS}
    required_metrics: set[str] = {str(item) for item in REQUIRED_EFFECT_METRICS}
    required_roles: set[str] = {str(item) for item in REQUIRED_ACTION_ROLES}
    missing_evidence = benchmarked - evidence_tool_ids
    missing_metrics = required_metrics - evidence_metric_ids
    missing_roles = required_roles - evidence_action_roles
    unregistered_discovered = discovered - registered
    undiscovered_registered = registered - discovered
    unexpected_benchmarks = benchmarked - required_tools
    unexpected_evidence = evidence_tool_ids - benchmarked
    deferred_with_evidence = deferred & evidence_tool_ids
    valid = (
        discovered == set(DISCOVERED_TOOL_IDS)
        and registered == discovered
        and benchmarked == required_tools
        and evidence_tool_ids == benchmarked
        and not missing_evidence
        and not missing_metrics
        and not missing_roles
        and not deferred
        and not deferred_with_evidence
    )
    return {
        "schema_id": "market_state_tool_coverage_report@1.2",
        "valid": valid,
        "strategy_refs_are_provenance_only": True,
        "required_core_tool_count": len(REQUIRED_TOOL_IDS),
        "discovered_tool_count": len(discovered),
        "registered_tool_count": len(registered),
        "benchmarked_tool_count": len(benchmarked),
        "deferred_tool_count": len(deferred),
        "evidenced_tool_count": len(evidence_tool_ids),
        "required_metric_count": len(REQUIRED_EFFECT_METRICS),
        "evidenced_metric_count": len(evidence_metric_ids),
        "required_action_role_count": len(REQUIRED_ACTION_ROLES),
        "evidenced_action_role_count": len(evidence_action_roles),
        "missing_tool_ids": sorted(required_tools - registered),
        "missing_evidence_tool_ids": sorted(missing_evidence),
        "missing_metric_ids": sorted(missing_metrics),
        "missing_action_roles": sorted(missing_roles),
        "unregistered_discovered_tool_ids": sorted(unregistered_discovered),
        "undiscovered_registered_tool_ids": sorted(undiscovered_registered),
        "unexpected_benchmark_tool_ids": sorted(unexpected_benchmarks),
        "unexpected_evidence_tool_ids": sorted(unexpected_evidence),
        "deferred_with_evidence_tool_ids": sorted(deferred_with_evidence),
        "deferred_tool_ids": sorted(deferred),
        "tools": [
            {
                "tool_id": str(item.get("tool_id", "")),
                "benchmark_status": str(item.get("benchmark_status", "")),
                "status_reason": str(item.get("status_reason", "")),
                "source_strategy_refs": list(item.get("source_strategy_refs", [])),
                "evidence_present": str(item.get("tool_id", "")) in evidence_tool_ids,
            }
            for item in rows
        ],
    }


__all__ = [
    "DISCOVERED_TOOL_IDS",
    "REQUIRED_ACTION_ROLES",
    "REQUIRED_EFFECT_METRICS",
    "REQUIRED_TOOL_IDS",
    "TOOL_DISCOVERY_SOURCES",
    "TOOL_REGISTRY_SCHEMA_ID",
    "TOOL_REGISTRY_VERSION",
    "TOOL_SOURCE_DISCOVERY_SCHEMA_ID",
    "V2_PARAMETER_CATALOG_MIGRATION_TOOL_IDS",
    "ToolBenchmarkSpec",
    "ToolSpec",
    "build_tool_coverage_report",
    "build_tool_registry_payload",
    "build_tool_source_inventory_payload",
    "tool_benchmark_specs",
    "tool_specs",
]
