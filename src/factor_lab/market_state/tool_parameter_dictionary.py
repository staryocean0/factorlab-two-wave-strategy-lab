# pyright: reportAny=false, reportArgumentType=false
# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false
"""Frozen two-axis parameter surfaces for fixed tool-capability research.

Every tool-frequency lens receives exactly nine candidate profiles: three
physically meaningful time-scale settings crossed with three tool-specific
shape/responsiveness settings.  The equal 3x3 budget prevents a complicated
tool from winning merely because it was searched more aggressively.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from itertools import product
from types import MappingProxyType
from typing import ClassVar, cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.tool_capability_contracts import (
    ParameterDomainSpec,
    ParameterResearchContract,
    Primitive,
    ToolProfileSpec,
    make_parameter_contract_id,
    make_profile_id,
)
from factor_lab.market_state.tool_registry import (
    REQUIRED_ACTION_ROLES,
    ToolBenchmarkSpec,
    tool_benchmark_specs,
)

FIXED_PARAMETER_DICTIONARY_SCHEMA_ID = "market_state_tool_fixed_parameter_dictionary@1.0"
FIXED_PARAMETER_DICTIONARY_VERSION = "tool_fixed_parameter_dictionary_v1"
FIXED_CANDIDATES_PER_LENS = 9
AXIS_LEVELS = (-1, 0, 1)

_SCALE_075 = {-1: 0.75, 0: 1.0, 1: 4.0 / 3.0}
_SCALE_080 = {-1: 0.8, 0: 1.0, 1: 1.25}
_SCALE_050 = {-1: 0.5, 0: 1.0, 1: 2.0}

_PARAMETER_NAMES_ZH = {
    "action": "动作语义",
    "candidate_period_1": "候选周期一",
    "candidate_period_2": "候选周期二",
    "candidate_period_3": "候选周期三",
    "candidate_period_4": "候选周期四",
    "cutoff_period_bars": "截止周期",
    "entry_window_bars": "入场观察窗",
    "exit_window_bars": "出场观察窗",
    "fast_window_bars": "快速观察窗",
    "filter_order": "滤波阶数",
    "high_period_bars": "通带高周期边界",
    "initial_amplitude_log": "初始对数振幅",
    "initial_observation_sigma_log": "初始观测对数标准差",
    "level": "小波层级",
    "long_period_bars": "长周期边界",
    "low_period_bars": "通带低周期边界",
    "lowpass_order": "低通阶数",
    "model_score_temperature": "模型评分温度",
    "model_weight_half_life_bars": "模型权重半衰期",
    "observation_variance_half_life_bars": "观测方差半衰期",
    "order": "滤波阶数",
    "period_bars": "中心周期",
    "q": "品质因数",
    "rail_sigma": "通道轨道标准差倍数",
    "round_top_sharp_bottom_ratio": "圆顶尖底不对称比例",
    "score_half_life_bars": "评分半衰期",
    "short_period_bars": "短周期边界",
    "slow_level": "慢速小波层级",
    "slow_window_bars": "慢速观察窗",
    "thickness_lower_quantile": "厚度下分位数",
    "thickness_smoothing_half_life_bars": "厚度平滑半衰期",
    "thickness_source": "厚度来源",
    "thickness_upper_quantile": "厚度上分位数",
    "thickness_window_bars": "厚度观察窗",
    "warmup_bars": "预热长度",
    "width_multiplier": "通道宽度倍数",
    "width_sigma": "通道标准差倍数",
    "window_bars": "观察窗",
    "window_multiplier": "观察窗倍数",
}


@dataclass(frozen=True, slots=True)
class FixedParameterCandidate:
    """One point on a tool-specific, pre-registered 3x3 semantic surface."""

    candidate_id: str
    benchmark_id: str
    tool_id: str
    carrier_frequency: str
    timescale_level: int
    shape_level: int
    timescale_semantics: str
    shape_semantics: str
    parameters: Mapping[str, Primitive]
    baseline: bool

    def __post_init__(self) -> None:
        if self.timescale_level not in AXIS_LEVELS or self.shape_level not in AXIS_LEVELS:
            raise ValidationError("candidate semantic levels must be -1, 0 or 1")
        if not self.timescale_semantics.strip() or not self.shape_semantics.strip():
            raise ValidationError("candidate semantic axes require explanations")
        parameters = MappingProxyType(dict(sorted(self.parameters.items())))
        if not parameters:
            raise ValidationError("fixed parameter candidate cannot be empty")
        expected = _candidate_id(
            benchmark_id=self.benchmark_id,
            tool_id=self.tool_id,
            carrier_frequency=self.carrier_frequency,
            timescale_level=self.timescale_level,
            shape_level=self.shape_level,
            parameters=parameters,
        )
        if self.candidate_id != expected:
            raise ValidationError("fixed parameter candidate id does not match content")
        if self.baseline != (self.timescale_level == 0 and self.shape_level == 0):
            raise ValidationError("only the centre of the 3x3 surface is baseline")
        object.__setattr__(self, "parameters", parameters)

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "benchmark_id": self.benchmark_id,
            "tool_id": self.tool_id,
            "carrier_frequency": self.carrier_frequency,
            "timescale_level": self.timescale_level,
            "shape_level": self.shape_level,
            "timescale_semantics": self.timescale_semantics,
            "shape_semantics": self.shape_semantics,
            "parameters": dict(self.parameters),
            "baseline": self.baseline,
            "production_authority": False,
        }


@dataclass(frozen=True, slots=True)
class FixedParameterDictionary:
    """Complete frozen search authority for all 23 tool-frequency lenses."""

    candidates: tuple[FixedParameterCandidate, ...]
    contracts: tuple[ParameterResearchContract, ...]
    baseline_profiles: tuple[ToolProfileSpec, ...]

    schema_id: ClassVar[str] = FIXED_PARAMETER_DICTIONARY_SCHEMA_ID
    dictionary_version: ClassVar[str] = FIXED_PARAMETER_DICTIONARY_VERSION
    production_authority: ClassVar[bool] = False

    def __post_init__(self) -> None:
        candidates = tuple(self.candidates)
        contracts = tuple(self.contracts)
        profiles = tuple(self.baseline_profiles)
        lens_keys = {(item.benchmark_id, item.carrier_frequency) for item in candidates}
        expected_lenses = {(spec.benchmark_id, frequency) for spec in tool_benchmark_specs() for frequency in spec.parameters_by_frequency}
        if lens_keys != expected_lenses:
            raise ValidationError("fixed candidate dictionary has incomplete lens coverage")
        for key in lens_keys:
            surface = [item for item in candidates if (item.benchmark_id, item.carrier_frequency) == key]
            if len(surface) != FIXED_CANDIDATES_PER_LENS:
                raise ValidationError("every tool-frequency lens must expose nine candidates")
            coordinates = {(item.timescale_level, item.shape_level) for item in surface}
            if coordinates != set(product(AXIS_LEVELS, AXIS_LEVELS)):
                raise ValidationError("candidate surface is not a complete 3x3 grid")
            if sum(item.baseline for item in surface) != 1:
                raise ValidationError("candidate surface must contain one baseline")
        expected_role_lenses = len(expected_lenses) * len(REQUIRED_ACTION_ROLES)
        if len(contracts) != expected_role_lenses or len(profiles) != expected_role_lenses:
            raise ValidationError("fixed parameter contracts do not cover both roles")
        if any(
            item.search_space_status != "frozen_grid" or item.maximum_candidate_profiles != FIXED_CANDIDATES_PER_LENS for item in contracts
        ):
            raise ValidationError("fixed parameter contracts must use the equal nine-point budget")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "contracts", contracts)
        object.__setattr__(self, "baseline_profiles", profiles)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "dictionary_version": self.dictionary_version,
            "equal_search_budget": True,
            "candidate_profiles_per_tool_frequency": FIXED_CANDIDATES_PER_LENS,
            "candidate_generation_rule": "tool_specific_semantic_3x3_surface_v1",
            "research_range": ["2009-01-01", "2020-12-31"],
            "sealed_blackbox": ["2021-01-01", "2026-12-31"],
            "candidates": [item.to_dict() for item in self.candidates],
            "parameter_contracts": [item.to_dict() for item in self.contracts],
            "baseline_profiles": [item.to_dict() for item in self.baseline_profiles],
            "production_authority": self.production_authority,
        }


def _candidate_id(
    *,
    benchmark_id: str,
    tool_id: str,
    carrier_frequency: str,
    timescale_level: int,
    shape_level: int,
    parameters: Mapping[str, Primitive],
) -> str:
    digest = canonical_digest(
        {
            "benchmark_id": benchmark_id,
            "tool_id": tool_id,
            "carrier_frequency": carrier_frequency,
            "timescale_level": timescale_level,
            "shape_level": shape_level,
            "parameters": dict(sorted(parameters.items())),
        }
    ).removeprefix("sha256:")[:24]
    return f"fixed-candidate:{digest}"


def _rounded(value: float, *, minimum: int = 1) -> int:
    return max(minimum, int(round(value)))


def _scaled(value: Primitive, factor: float, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("numeric scale requested for a non-numeric parameter")
    return _rounded(float(value) * factor, minimum=minimum)


def _surface_parameters(
    tool_id: str,
    baseline: Mapping[str, Primitive],
    timescale_level: int,
    shape_level: int,
) -> tuple[dict[str, Primitive], str, str]:
    """Map semantic coordinates to one coherent tool-native parameter vector."""

    values = dict(baseline)
    if tool_id in {"laplace_iir_mixed_bandpass", "laplace_iir_lowpass"}:
        values["period_bars"] = _scaled(baseline["period_bars"], _SCALE_075[timescale_level], minimum=4)
        values["q"] = {-1: 0.7, 0: 1.0, 1: 1.4}[shape_level]
        return values, "中心周期缩短/基准/拉长", "低Q宽响应/基准/高Q窄响应"

    if tool_id in {"butterworth_clean_bandpass", "rolling_fourier_bandpass"}:
        scale = _SCALE_080[timescale_level]
        low_key = "short_period_bars" if "short_period_bars" in baseline else "low_period_bars"
        high_key = "long_period_bars" if "long_period_bars" in baseline else "high_period_bars"
        low = _scaled(baseline[low_key], scale, minimum=4)
        high = _scaled(baseline[high_key], scale, minimum=low + 2)
        low_factor = {-1: 0.85, 0: 1.0, 1: 1.15}[shape_level]
        high_factor = {-1: 1.15, 0: 1.0, 1: 0.90}[shape_level]
        low = _rounded(low * low_factor, minimum=4)
        high = _rounded(high * high_factor, minimum=low + 2)
        values[low_key] = low
        values[high_key] = high
        if "window_bars" in values:
            values["window_bars"] = max(
                _scaled(baseline["window_bars"], scale, minimum=high * 2),
                high * 2,
            )
        return values, "通带整体移向高频/基准/低频", "宽通带/基准/窄通带"

    if tool_id == "causal_haar_wavelet_bandpass":
        # The rolling Haar executor reads only the final reconstructed point.
        # Changing the outer window alone therefore changes warmup but not the
        # common-valid response kernel.  Move both levels with the timescale
        # axis so short/registered/long are genuinely different filters; use
        # the fast/slow level gap as the independent band-width shape axis.
        level = 2 + timescale_level
        level_gap = {-1: 4, 0: 3, 1: 2}[shape_level]
        slow_level = level + level_gap
        window = _scaled(baseline["window_bars"], _SCALE_050[timescale_level], minimum=32)
        minimum_window = 2**slow_level
        window = max(window, minimum_window)
        if window % minimum_window != 0:
            window = ((window + minimum_window - 1) // minimum_window) * minimum_window
        values["window_bars"] = window
        values["level"] = level
        values["slow_level"] = slow_level
        return (
            values,
            "快速与慢速Haar层级同步移向高频/基准/低频",
            "宽通带/基准/窄通带",
        )

    if tool_id == "r3_nested_moving_average_component":
        slow = _scaled(baseline["slow_window_bars"], _SCALE_075[timescale_level], minimum=4)
        ratio = {-1: 0.0625, 0: 0.125, 1: 0.25}[shape_level]
        values["slow_window_bars"] = slow
        values["fast_window_bars"] = min(slow - 1, _rounded(slow * ratio))
        return values, "慢分量周期缩短/基准/拉长", "快慢间隔宽/基准/窄"

    if tool_id == "bollinger_volatility_channel":
        values["window_bars"] = _scaled(baseline["window_bars"], _SCALE_050[timescale_level], minimum=5)
        values["width_sigma"] = {-1: 1.5, 0: 2.0, 1: 2.5}[shape_level]
        return values, "波动统计窗缩短/基准/拉长", "窄轨/基准/宽轨"

    if tool_id == "frequency_selective_bollinger_channel":
        # The native V58 carrier only admits P48/P96/P192/P384 and width
        # multipliers 1/1.5/2.  P48 and width=1 are boundary values, so a
        # symmetric numeric perturbation would silently invent an unsupported
        # tool.  Keep P48 as the centre and use the two registered slower
        # branches; use filter order for the genuinely ordered response axis.
        values["period_bars"] = {-1: 96, 0: 48, 1: 192}[timescale_level]
        values["filter_order"] = {-1: 2, 0: 4, 1: 6}[shape_level]
        return (
            values,
            "P96邻级/P48原生/P192更慢邻级",
            "滤波响应快/基准/平滑",
        )

    if tool_id == "butterworth_lowpass_residual_envelope":
        scale = _SCALE_075[timescale_level]
        cutoff = _scaled(baseline["cutoff_period_bars"], scale, minimum=16)
        values["cutoff_period_bars"] = cutoff
        values["thickness_window_bars"] = _scaled(baseline["thickness_window_bars"], scale, minimum=16)
        values["warmup_bars"] = max(int(baseline["warmup_bars"]), cutoff * 4)
        smoothing = {-1: 3.0, 0: 6.0, 1: 12.0}[shape_level]
        values["thickness_smoothing_half_life_bars"] = smoothing
        return values, "低通截止与厚度窗缩短/基准/拉长", "厚度响应快/基准/慢"

    if tool_id == "causal_asymmetric_arc_state_space_envelope":
        scale = _SCALE_075[timescale_level]
        periods: list[int] = []
        for index in range(1, 5):
            key = f"candidate_period_{index}"
            period = _scaled(baseline[key], scale, minimum=16)
            values[key] = period
            periods.append(period)
        response = {
            -1: (64.0, 6.0, 0.25, 32.0),
            0: (96.0, 12.0, 0.20, 64.0),
            1: (144.0, 24.0, 0.15, 96.0),
        }[shape_level]
        values["score_half_life_bars"] = response[0]
        values["model_weight_half_life_bars"] = response[1]
        values["model_score_temperature"] = response[2]
        values["observation_variance_half_life_bars"] = response[3]
        values["warmup_bars"] = max(int(baseline["warmup_bars"]), max(periods))
        return values, "弧形候选周期缩短/基准/拉长", "模型响应快/基准/慢"

    if tool_id == "donchian_price_channel":
        entry = _scaled(baseline["entry_window_bars"], _SCALE_050[timescale_level], minimum=4)
        exit_ratio = {-1: 0.25, 0: 0.5, 1: 0.75}[shape_level]
        values["entry_window_bars"] = entry
        values["exit_window_bars"] = min(entry - 1, _rounded(entry * exit_ratio))
        return values, "突破观察窗缩短/基准/拉长", "退出快/基准/慢"

    if tool_id == "causal_trendline_channel":
        values["window_bars"] = _scaled(baseline["window_bars"], _SCALE_050[timescale_level], minimum=8)
        values["rail_sigma"] = {-1: 1.0, 0: 1.5, 1: 2.0}[shape_level]
        return values, "回归窗口缩短/基准/拉长", "窄轨/基准/宽轨"

    if tool_id == "simple_moving_average_trend":
        slow = _scaled(baseline["slow_window_bars"], _SCALE_050[timescale_level], minimum=6)
        ratio = {-1: 0.2, 0: 1.0 / 3.0, 1: 0.5}[shape_level]
        values["slow_window_bars"] = slow
        values["fast_window_bars"] = min(slow - 1, _rounded(slow * ratio))
        return values, "慢均线窗口缩短/基准/拉长", "快慢间隔宽/基准/窄"

    raise ValidationError(f"unregistered fixed parameter surface: {tool_id}")


def _parameter_kind(value: Primitive) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return "categorical"


def _parameter_unit(parameter_id: str) -> str:
    if parameter_id.endswith("_bars") or parameter_id.startswith("candidate_period_"):
        return "K线根数"
    if parameter_id in {"filter_order", "lowpass_order", "order", "level", "slow_level"}:
        return "阶/层"
    if parameter_id in {"initial_amplitude_log", "initial_observation_sigma_log"}:
        return "对数价格"
    if parameter_id in {"action", "thickness_source"}:
        return "类别"
    return "无量纲"


def _unique(values: list[Primitive]) -> tuple[Primitive, ...]:
    result: list[Primitive] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)


def _build_surface(
    benchmark: ToolBenchmarkSpec,
    frequency: str,
) -> tuple[FixedParameterCandidate, ...]:
    raw = benchmark.parameters_by_frequency[frequency]
    baseline = {str(key): cast(Primitive, value) for key, value in raw.items() if key != "cost_bps"}
    rows: list[FixedParameterCandidate] = []
    for timescale_level, shape_level in product(AXIS_LEVELS, AXIS_LEVELS):
        parameters, timescale_semantics, shape_semantics = _surface_parameters(
            benchmark.tool_id,
            baseline,
            timescale_level,
            shape_level,
        )
        candidate_id = _candidate_id(
            benchmark_id=benchmark.benchmark_id,
            tool_id=benchmark.tool_id,
            carrier_frequency=frequency,
            timescale_level=timescale_level,
            shape_level=shape_level,
            parameters=parameters,
        )
        rows.append(
            FixedParameterCandidate(
                candidate_id=candidate_id,
                benchmark_id=benchmark.benchmark_id,
                tool_id=benchmark.tool_id,
                carrier_frequency=frequency,
                timescale_level=timescale_level,
                shape_level=shape_level,
                timescale_semantics=timescale_semantics,
                shape_semantics=shape_semantics,
                parameters=parameters,
                baseline=timescale_level == 0 and shape_level == 0,
            )
        )
    return tuple(rows)


def build_fixed_parameter_dictionary() -> FixedParameterDictionary:
    """Build the pre-performance, equal-budget parameter research authority."""

    candidates: list[FixedParameterCandidate] = []
    contracts: list[ParameterResearchContract] = []
    profiles: list[ToolProfileSpec] = []
    for benchmark in tool_benchmark_specs():
        for frequency, raw in sorted(benchmark.parameters_by_frequency.items()):
            surface = _build_surface(benchmark, frequency)
            candidates.extend(surface)
            baseline_candidate = next(item for item in surface if item.baseline)
            cost_bps = float(raw["cost_bps"])
            for action_role in REQUIRED_ACTION_ROLES:
                baseline_profile_id = make_profile_id(
                    tool_id=benchmark.tool_id,
                    benchmark_id=benchmark.benchmark_id,
                    action_role=action_role,
                    carrier_frequency=frequency,
                    parameters=baseline_candidate.parameters,
                    signal_semantics=benchmark.signal_semantics,
                    execution_lag_bars=1,
                    cost_bps=cost_bps,
                )
                domains = tuple(
                    ParameterDomainSpec(
                        parameter_id=parameter_id,
                        name_zh=_PARAMETER_NAMES_ZH[parameter_id],
                        value_kind=_parameter_kind(default_value),
                        unit=_parameter_unit(parameter_id),
                        default_value=default_value,
                        candidate_values=_unique([item.parameters[parameter_id] for item in surface]),
                        tunable=len(_unique([item.parameters[parameter_id] for item in surface])) > 1,
                        rationale=("仅由预登记3×3语义曲面生成；未出现在候选注册表中的笛卡尔组合禁止搜索"),
                    )
                    for parameter_id, default_value in sorted(baseline_candidate.parameters.items())
                )
                constraints = (
                    "只允许候选注册表中九个完整向量，禁止独立拼接参数值",
                    "时间尺度与形状轴各三档；每个工具频率搜索预算完全相同",
                    "成本固定在benchmark外层，信号语义和下一根执行不得调参",
                )
                contract_id = make_parameter_contract_id(
                    tool_id=benchmark.tool_id,
                    benchmark_id=benchmark.benchmark_id,
                    action_role=action_role,
                    carrier_frequency=frequency,
                    baseline_profile_id=baseline_profile_id,
                    baseline_parameters=baseline_candidate.parameters,
                    parameter_domains=domains,
                    cross_parameter_constraints=constraints,
                    objective_metric_ids=(
                        "net_log_return_per_decision_bar",
                        "trade_expectancy",
                    ),
                    risk_constraint_metric_ids=("turnover_per_decision_bar",),
                    search_space_status="frozen_grid",
                    maximum_candidate_profiles=FIXED_CANDIDATES_PER_LENS,
                    inner_selection_policy_id="annual_rank_robust_train_only_v1",
                    outer_validation_policy_id="expanding_four_fold_purged_2009_2020_v1",
                    stable_plateau_policy_id="two_axis_neighbor_plateau_v1",
                )
                contracts.append(
                    ParameterResearchContract(
                        contract_id=contract_id,
                        tool_id=benchmark.tool_id,
                        benchmark_id=benchmark.benchmark_id,
                        action_role=action_role,
                        carrier_frequency=frequency,
                        baseline_profile_id=baseline_profile_id,
                        baseline_parameters=baseline_candidate.parameters,
                        parameter_domains=domains,
                        cross_parameter_constraints=constraints,
                        objective_metric_ids=(
                            "net_log_return_per_decision_bar",
                            "trade_expectancy",
                        ),
                        risk_constraint_metric_ids=("turnover_per_decision_bar",),
                        search_space_status="frozen_grid",
                        maximum_candidate_profiles=FIXED_CANDIDATES_PER_LENS,
                        inner_selection_policy_id="annual_rank_robust_train_only_v1",
                        outer_validation_policy_id="expanding_four_fold_purged_2009_2020_v1",
                        stable_plateau_policy_id="two_axis_neighbor_plateau_v1",
                    )
                )
                profiles.append(
                    ToolProfileSpec(
                        profile_id=baseline_profile_id,
                        tool_id=benchmark.tool_id,
                        benchmark_id=benchmark.benchmark_id,
                        action_role=action_role,
                        carrier_frequency=frequency,
                        parameter_contract_id=contract_id,
                        parameters=baseline_candidate.parameters,
                        signal_semantics=benchmark.signal_semantics,
                        execution_lag_bars=1,
                        cost_bps=cost_bps,
                    )
                )
    return FixedParameterDictionary(
        candidates=tuple(candidates),
        contracts=tuple(contracts),
        baseline_profiles=tuple(profiles),
    )


__all__ = [
    "AXIS_LEVELS",
    "FIXED_CANDIDATES_PER_LENS",
    "FIXED_PARAMETER_DICTIONARY_SCHEMA_ID",
    "FIXED_PARAMETER_DICTIONARY_VERSION",
    "FixedParameterCandidate",
    "FixedParameterDictionary",
    "build_fixed_parameter_dictionary",
]
