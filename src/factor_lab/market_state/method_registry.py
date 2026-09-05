# pyright: reportArgumentType=false
"""Frozen mathematical-method ontology and V1-C benchmark registry.

The registry deliberately separates a mathematical method from a product
strategy.  Benchmarks are transparent research probes, not production trading
authorities and not parameter searches.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from factor_lab.core.errors import ValidationError

METHOD_REGISTRY_SCHEMA_ID = "market_state_method_family_registry@1.0"
METHOD_REGISTRY_VERSION = "method_family_registry_v1"

REQUIRED_METHOD_FAMILIES = (
    "causal_lowpass_state",
    "causal_bandpass_mixed",
    "causal_bandpass_clean",
    "state_space_filter",
    "multiscale_basis",
    "volatility_channel",
    "price_channel",
    "graph_structure",
    "moving_average_trend",
    "tail_event_specialist",
    "hybrid_router",
)

REQUIRED_BENCHMARK_IDS = (
    "causal_bandpass_filter_benchmark_v1",
    "volatility_channel_benchmark_v1",
    "price_channel_benchmark_v1",
    "moving_average_trend_benchmark_v1",
)


@dataclass(frozen=True, slots=True)
class MethodFamilySpec:
    method_family_id: str
    name_zh: str
    aliases: tuple[str, ...]
    mathematical_object: str
    production_authority: bool = False

    def __post_init__(self) -> None:
        if not self.method_family_id.strip() or not self.name_zh.strip():
            raise ValidationError("method family id and Chinese name are required")
        if not self.mathematical_object.strip():
            raise ValidationError("mathematical_object is required")
        if self.production_authority:
            raise ValidationError("V1-C method families cannot be production authorities")

    def to_dict(self) -> dict[str, object]:
        return {
            "method_family_id": self.method_family_id,
            "name_zh": self.name_zh,
            "aliases": list(self.aliases),
            "mathematical_object": self.mathematical_object,
            "production_authority": self.production_authority,
        }


@dataclass(frozen=True, slots=True)
class BenchmarkSpec:
    benchmark_id: str
    method_family_id: str
    name_zh: str
    action_role: str
    effect_metric_id: str
    comparator_method_id: str
    signal_semantics: str
    parameters_by_frequency: Mapping[str, Mapping[str, float | int]]
    source_prior_ref: str
    production_authority: bool = False

    def __post_init__(self) -> None:
        for value, label in (
            (self.benchmark_id, "benchmark_id"),
            (self.method_family_id, "method_family_id"),
            (self.name_zh, "name_zh"),
            (self.action_role, "action_role"),
            (self.effect_metric_id, "effect_metric_id"),
            (self.comparator_method_id, "comparator_method_id"),
            (self.signal_semantics, "signal_semantics"),
            (self.source_prior_ref, "source_prior_ref"),
        ):
            if not value.strip():
                raise ValidationError(f"{label} is required")
        if self.method_family_id not in REQUIRED_METHOD_FAMILIES:
            raise ValidationError(f"unregistered method family: {self.method_family_id}")
        params = {
            str(frequency): MappingProxyType(dict(values))
            for frequency, values in self.parameters_by_frequency.items()
        }
        if set(params) != {"1d", "60m"}:
            raise ValidationError("every C benchmark must freeze both 1d and 60m parameters")
        object.__setattr__(self, "parameters_by_frequency", MappingProxyType(params))
        if self.production_authority:
            raise ValidationError("V1-C benchmarks cannot be production authorities")

    def to_dict(self) -> dict[str, object]:
        return {
            "benchmark_id": self.benchmark_id,
            "method_family_id": self.method_family_id,
            "name_zh": self.name_zh,
            "action_role": self.action_role,
            "effect_metric_id": self.effect_metric_id,
            "comparator_method_id": self.comparator_method_id,
            "signal_semantics": self.signal_semantics,
            "parameters_by_frequency": {
                frequency: dict(values)
                for frequency, values in sorted(self.parameters_by_frequency.items())
            },
            "source_prior_ref": self.source_prior_ref,
            "production_authority": self.production_authority,
        }


def method_family_specs() -> tuple[MethodFamilySpec, ...]:
    """Return the frozen V1 ontology in stable order."""

    rows = (
        ("causal_lowpass_state", "因果低通状态", ("低通",), "causal low-pass level and slope"),
        (
            "causal_bandpass_mixed",
            "因果混合带通",
            ("IIR", "混合带通"),
            "causal oscillatory component with non-ideal frequency response",
        ),
        (
            "causal_bandpass_clean",
            "因果干净带通",
            ("巴特沃斯带通",),
            "causal band-pass component with explicit pass band",
        ),
        (
            "state_space_filter",
            "状态空间滤波",
            ("卡尔曼",),
            "latent-state estimator with causal measurement updates",
        ),
        ("multiscale_basis", "多尺度基底", ("小波",), "multiscale basis decomposition"),
        (
            "volatility_channel",
            "波动通道",
            ("布林", "Bollinger"),
            "rolling location plus volatility-scaled envelope",
        ),
        (
            "price_channel",
            "价格通道",
            ("Donchian",),
            "rolling observable-price extrema envelope",
        ),
        (
            "graph_structure",
            "图形结构",
            ("通道结构",),
            "causal geometric pivots, channels and breaks",
        ),
        (
            "moving_average_trend",
            "均线趋势",
            ("均线",),
            "relative ordering of causal rolling price averages",
        ),
        (
            "tail_event_specialist",
            "尾部事件专家",
            ("暴跌/暴涨专家",),
            "rare-event detector and event-specific action",
        ),
        (
            "hybrid_router",
            "混合路由",
            ("状态机",),
            "conditional allocation between method authorities",
        ),
    )
    return tuple(
        MethodFamilySpec(
            method_family_id=method_id,
            name_zh=name_zh,
            aliases=aliases,
            mathematical_object=mathematical_object,
        )
        for method_id, name_zh, aliases, mathematical_object in rows
    )


def benchmark_specs() -> tuple[BenchmarkSpec, ...]:
    """Return four fixed, causal, next-bar long/cash research probes."""

    common = {
        "action_role": "long_capture",
        "effect_metric_id": "net_log_return_per_decision_bar",
        "comparator_method_id": "cash_zero_return",
        "source_prior_ref": "docs/ops/factor_strategy_affinity_whitepaper.md",
    }
    return (
        BenchmarkSpec(
            benchmark_id="causal_bandpass_filter_benchmark_v1",
            method_family_id="causal_bandpass_mixed",
            name_zh="固定参数因果带通基准",
            signal_semantics="sign(delta(component)); signal at bar close, execute next bar",
            parameters_by_frequency={
                "1d": {"period_bars": 40, "q": 1.0, "cost_bps": 7.0},
                "60m": {"period_bars": 160, "q": 1.0, "cost_bps": 7.0},
            },
            **common,
        ),
        BenchmarkSpec(
            benchmark_id="volatility_channel_benchmark_v1",
            method_family_id="volatility_channel",
            name_zh="固定参数波动通道基准",
            signal_semantics=(
                "enter above prior rolling mean + 2 sigma; exit below prior mean; "
                "execute next bar"
            ),
            parameters_by_frequency={
                "1d": {"window_bars": 20, "width_sigma": 2.0, "cost_bps": 7.0},
                "60m": {"window_bars": 80, "width_sigma": 2.0, "cost_bps": 7.0},
            },
            **common,
        ),
        BenchmarkSpec(
            benchmark_id="price_channel_benchmark_v1",
            method_family_id="price_channel",
            name_zh="固定参数价格通道基准",
            signal_semantics=(
                "enter above prior rolling high; exit below prior rolling low; "
                "execute next bar"
            ),
            parameters_by_frequency={
                "1d": {"entry_window_bars": 20, "exit_window_bars": 10, "cost_bps": 7.0},
                "60m": {"entry_window_bars": 80, "exit_window_bars": 40, "cost_bps": 7.0},
            },
            **common,
        ),
        BenchmarkSpec(
            benchmark_id="moving_average_trend_benchmark_v1",
            method_family_id="moving_average_trend",
            name_zh="固定参数均线趋势基准",
            signal_semantics="fast SMA above slow SMA; signal at bar close, execute next bar",
            parameters_by_frequency={
                "1d": {"fast_window_bars": 20, "slow_window_bars": 60, "cost_bps": 7.0},
                "60m": {"fast_window_bars": 80, "slow_window_bars": 240, "cost_bps": 7.0},
            },
            **common,
        ),
    )


def build_method_registry_payload() -> dict[str, object]:
    families = method_family_specs()
    benchmarks = benchmark_specs()
    if tuple(item.method_family_id for item in families) != REQUIRED_METHOD_FAMILIES:
        raise ValidationError("method family registry is incomplete or reordered")
    if tuple(item.benchmark_id for item in benchmarks) != REQUIRED_BENCHMARK_IDS:
        raise ValidationError("benchmark registry is incomplete or reordered")
    return {
        "schema_id": METHOD_REGISTRY_SCHEMA_ID,
        "registry_version": METHOD_REGISTRY_VERSION,
        "production_authority": False,
        "families": [item.to_dict() for item in families],
        "benchmarks": [item.to_dict() for item in benchmarks],
        "field_labels_zh": {
            "families": "数学方法家族",
            "benchmarks": "冻结的非生产基准适配器",
            "action_role": "经济动作职责",
            "effect_metric_id": "效果指标",
            "comparator_method_id": "比较器",
            "production_authority": "生产授权",
        },
    }


__all__ = [
    "METHOD_REGISTRY_SCHEMA_ID",
    "METHOD_REGISTRY_VERSION",
    "REQUIRED_BENCHMARK_IDS",
    "REQUIRED_METHOD_FAMILIES",
    "BenchmarkSpec",
    "MethodFamilySpec",
    "benchmark_specs",
    "build_method_registry_payload",
    "method_family_specs",
]
