# pyright: reportAny=false, reportArgumentType=false
# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false
# pyright: reportUnusedCallResult=false
"""Governed contracts for tool parameters, profiles and capability evidence.

This module is intentionally a contract layer.  It converts the frozen tool
benchmarks into complete, comparable profiles, but it does not tune parameters,
claim capability, route tools or grant production authority.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar, Self, TypeAlias, cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.tool_registry import (
    REQUIRED_ACTION_ROLES,
    REQUIRED_EFFECT_METRICS,
    tool_benchmark_specs,
)

Primitive: TypeAlias = str | int | float | bool

TOOL_CAPABILITY_CONTRACT_SCHEMA_ID = "market_state_tool_capability_contract_registry@1.0"
TOOL_CAPABILITY_CONTRACT_VERSION = "tool_capability_contract_registry_v1"
TOOL_CAPABILITY_BLACKBOX_EXCLUSION = ("2021-01-01", "2026-12-31")
TOOL_CAPABILITY_FREQUENCIES = ("1d", "60m", "15m")
TOOL_CERTIFICATION_STATUSES = (
    "contract_only",
    "certified_fixed",
    "certified_dynamic",
    "rejected",
)
TOOL_CAPABILITY_METRIC_IDS = (
    *REQUIRED_EFFECT_METRICS,
    "max_drawdown",
    "excess_max_drawdown",
    "opportunity_coverage",
    "risk_drawdown_coverage",
    "net_return_per_holding_bar",
    "holding_bar_count",
    "switch_count",
    "outer_validation_net_uplift_vs_baseline",
    "oracle_gap_net_log_return_per_decision_bar",
)

TOOL_CAPABILITY_LABELS_ZH = {
    "profiles": "冻结的完整工具画像",
    "parameter_contracts": "参数研究合同",
    "capability_certificates": "工具能力证书",
    "tool_id": "数学工具标识",
    "action_role": "行为角色",
    "carrier_frequency": "载体K线频率",
    "parameters": "参数向量",
    "signal_semantics": "信号与执行语义",
    "execution_lag_bars": "执行滞后K线数",
    "cost_bps": "单次换手成本（基点）",
    "certification_status": "能力认证状态",
    "blackbox_exclusion": "封存黑箱区间",
    "production_authority": "生产授权",
}

_PARAMETER_LABELS_ZH = {
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


def _parameter_unit(parameter_id: str) -> str:
    if parameter_id.endswith("_bars") or parameter_id.startswith("candidate_period_"):
        return "K线根数"
    if parameter_id in {
        "filter_order",
        "lowpass_order",
        "order",
        "level",
        "slow_level",
    }:
        return "阶/层"
    if parameter_id in {"initial_amplitude_log", "initial_observation_sigma_log"}:
        return "对数价格"
    if parameter_id in {"action", "thickness_source"}:
        return "类别"
    return "无量纲"


def _text(value: object, field: str) -> str:
    text = str(value)
    if not text.strip():
        raise ValidationError(f"{field} is required")
    return text


def _primitive(value: object, field: str) -> Primitive:
    if not isinstance(value, (str, int, float, bool)):
        raise ValidationError(f"{field} must be a JSON primitive")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValidationError(f"{field} must be finite")
    if isinstance(value, str) and not value.strip():
        raise ValidationError(f"{field} cannot be blank")
    return value


def _parameters(
    values: Mapping[str, object],
    field: str,
) -> Mapping[str, Primitive]:
    result: dict[str, Primitive] = {}
    for key, value in values.items():
        parameter_id = _text(key, f"{field} parameter id")
        if parameter_id == "cost_bps":
            raise ValidationError(f"{field} must keep cost_bps outside the parameter vector")
        result[parameter_id] = _primitive(value, f"{field}.{parameter_id}")
    if not result:
        raise ValidationError(f"{field} cannot be empty")
    return MappingProxyType(dict(sorted(result.items())))


def _string_mapping(
    values: Mapping[str, object],
    field: str,
) -> Mapping[str, str]:
    return MappingProxyType({_text(key, f"{field} key"): _text(value, f"{field}.{key}") for key, value in sorted(values.items())})


def _metric_mapping(
    values: Mapping[str, object],
    field: str,
) -> Mapping[str, float]:
    result: dict[str, float] = {}
    for key, value in sorted(values.items()):
        metric_id = _text(key, f"{field} metric id")
        if metric_id not in TOOL_CAPABILITY_METRIC_IDS:
            raise ValidationError(f"{field} contains an unsupported metric: {metric_id}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(f"{field}.{metric_id} must be numeric")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValidationError(f"{field}.{metric_id} must be finite")
        result[metric_id] = numeric
    return MappingProxyType(result)


def _short_digest(prefix: str, payload: Mapping[str, object]) -> str:
    suffix = canonical_digest(dict(payload)).removeprefix("sha256:")[:24]
    return f"{prefix}:{suffix}"


def _profile_identity(
    *,
    tool_id: str,
    benchmark_id: str,
    action_role: str,
    carrier_frequency: str,
    parameters: Mapping[str, Primitive],
    signal_semantics: str,
    execution_lag_bars: int,
    cost_bps: float,
) -> dict[str, object]:
    return {
        "tool_id": tool_id,
        "benchmark_id": benchmark_id,
        "action_role": action_role,
        "carrier_frequency": carrier_frequency,
        "parameters": dict(sorted(parameters.items())),
        "signal_semantics": signal_semantics,
        "execution_lag_bars": execution_lag_bars,
        "cost_bps": cost_bps,
    }


def make_profile_id(
    *,
    tool_id: str,
    benchmark_id: str,
    action_role: str,
    carrier_frequency: str,
    parameters: Mapping[str, Primitive],
    signal_semantics: str,
    execution_lag_bars: int,
    cost_bps: float,
) -> str:
    """Return the content identity of one complete tool profile."""

    return _short_digest(
        "profile",
        _profile_identity(
            tool_id=tool_id,
            benchmark_id=benchmark_id,
            action_role=action_role,
            carrier_frequency=carrier_frequency,
            parameters=parameters,
            signal_semantics=signal_semantics,
            execution_lag_bars=execution_lag_bars,
            cost_bps=cost_bps,
        ),
    )


@dataclass(frozen=True, slots=True)
class ParameterDomainSpec:
    """One parameter's frozen semantics and candidate domain."""

    parameter_id: str
    name_zh: str
    value_kind: str
    unit: str
    default_value: Primitive
    candidate_values: tuple[Primitive, ...]
    tunable: bool
    rationale: str

    def __post_init__(self) -> None:
        for field in ("parameter_id", "name_zh", "value_kind", "unit", "rationale"):
            _text(getattr(self, field), field)
        if self.value_kind not in {"integer", "number", "categorical", "boolean"}:
            raise ValidationError(f"unsupported parameter value_kind: {self.value_kind}")
        default = _primitive(self.default_value, f"{self.parameter_id}.default_value")
        candidates = tuple(_primitive(item, f"{self.parameter_id}.candidate_values") for item in self.candidate_values)
        if not candidates:
            raise ValidationError("parameter candidate_values cannot be empty")
        if len(set(candidates)) != len(candidates):
            raise ValidationError("parameter candidate_values must be unique")
        if default not in candidates:
            raise ValidationError("parameter default_value must be a candidate")
        if not self.tunable and candidates != (default,):
            raise ValidationError("non-tunable parameter must expose only its default")
        for value in candidates:
            if self.value_kind == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
                raise ValidationError("integer parameter has a non-integer candidate")
            if self.value_kind == "number" and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise ValidationError("number parameter has a non-numeric candidate")
            if self.value_kind == "categorical" and not isinstance(value, str):
                raise ValidationError("categorical parameter has a non-string candidate")
            if self.value_kind == "boolean" and not isinstance(value, bool):
                raise ValidationError("boolean parameter has a non-boolean candidate")
        object.__setattr__(self, "default_value", default)
        object.__setattr__(self, "candidate_values", candidates)

    def to_dict(self) -> dict[str, object]:
        return {
            "parameter_id": self.parameter_id,
            "name_zh": self.name_zh,
            "value_kind": self.value_kind,
            "unit": self.unit,
            "default_value": self.default_value,
            "candidate_values": list(self.candidate_values),
            "tunable": self.tunable,
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> Self:
        candidates = payload.get("candidate_values")
        if not isinstance(candidates, list):
            raise ValidationError("candidate_values must be a list")
        return cls(
            parameter_id=_text(payload.get("parameter_id"), "parameter_id"),
            name_zh=_text(payload.get("name_zh"), "name_zh"),
            value_kind=_text(payload.get("value_kind"), "value_kind"),
            unit=_text(payload.get("unit"), "unit"),
            default_value=_primitive(payload.get("default_value"), "default_value"),
            candidate_values=tuple(_primitive(item, "candidate_values") for item in candidates),
            tunable=payload.get("tunable") is True,
            rationale=_text(payload.get("rationale"), "rationale"),
        )


def _parameter_contract_identity(
    *,
    tool_id: str,
    benchmark_id: str,
    action_role: str,
    carrier_frequency: str,
    baseline_profile_id: str,
    baseline_parameters: Mapping[str, Primitive],
    parameter_domains: tuple[ParameterDomainSpec, ...],
    cross_parameter_constraints: tuple[str, ...],
    objective_metric_ids: tuple[str, ...],
    risk_constraint_metric_ids: tuple[str, ...],
    search_space_status: str,
    maximum_candidate_profiles: int,
    inner_selection_policy_id: str,
    outer_validation_policy_id: str,
    stable_plateau_policy_id: str,
) -> dict[str, object]:
    return {
        "tool_id": tool_id,
        "benchmark_id": benchmark_id,
        "action_role": action_role,
        "carrier_frequency": carrier_frequency,
        "baseline_profile_id": baseline_profile_id,
        "baseline_parameters": dict(sorted(baseline_parameters.items())),
        "parameter_domains": [item.to_dict() for item in parameter_domains],
        "cross_parameter_constraints": list(cross_parameter_constraints),
        "objective_metric_ids": list(objective_metric_ids),
        "risk_constraint_metric_ids": list(risk_constraint_metric_ids),
        "search_space_status": search_space_status,
        "maximum_candidate_profiles": maximum_candidate_profiles,
        "inner_selection_policy_id": inner_selection_policy_id,
        "outer_validation_policy_id": outer_validation_policy_id,
        "stable_plateau_policy_id": stable_plateau_policy_id,
        "blackbox_exclusion": list(TOOL_CAPABILITY_BLACKBOX_EXCLUSION),
    }


def make_parameter_contract_id(
    *,
    tool_id: str,
    benchmark_id: str,
    action_role: str,
    carrier_frequency: str,
    baseline_profile_id: str,
    baseline_parameters: Mapping[str, Primitive],
    parameter_domains: tuple[ParameterDomainSpec, ...],
    cross_parameter_constraints: tuple[str, ...],
    objective_metric_ids: tuple[str, ...],
    risk_constraint_metric_ids: tuple[str, ...],
    search_space_status: str,
    maximum_candidate_profiles: int,
    inner_selection_policy_id: str,
    outer_validation_policy_id: str,
    stable_plateau_policy_id: str,
) -> str:
    """Return the content identity of one pre-registered parameter contract."""

    return _short_digest(
        "parameter-contract",
        _parameter_contract_identity(
            tool_id=tool_id,
            benchmark_id=benchmark_id,
            action_role=action_role,
            carrier_frequency=carrier_frequency,
            baseline_profile_id=baseline_profile_id,
            baseline_parameters=baseline_parameters,
            parameter_domains=parameter_domains,
            cross_parameter_constraints=cross_parameter_constraints,
            objective_metric_ids=objective_metric_ids,
            risk_constraint_metric_ids=risk_constraint_metric_ids,
            search_space_status=search_space_status,
            maximum_candidate_profiles=maximum_candidate_profiles,
            inner_selection_policy_id=inner_selection_policy_id,
            outer_validation_policy_id=outer_validation_policy_id,
            stable_plateau_policy_id=stable_plateau_policy_id,
        ),
    )


@dataclass(frozen=True, slots=True)
class ParameterResearchContract:
    """Pre-registered parameter study contract for exactly one tool profile."""

    contract_id: str
    tool_id: str
    benchmark_id: str
    action_role: str
    carrier_frequency: str
    baseline_profile_id: str
    baseline_parameters: Mapping[str, Primitive]
    parameter_domains: tuple[ParameterDomainSpec, ...]
    cross_parameter_constraints: tuple[str, ...]
    objective_metric_ids: tuple[str, ...]
    risk_constraint_metric_ids: tuple[str, ...]
    search_space_status: str
    maximum_candidate_profiles: int
    inner_selection_policy_id: str
    outer_validation_policy_id: str
    stable_plateau_policy_id: str
    blackbox_exclusion: tuple[str, str] = TOOL_CAPABILITY_BLACKBOX_EXCLUSION
    production_authority: bool = False

    research_executed: ClassVar[bool] = False

    def __post_init__(self) -> None:
        for field in (
            "contract_id",
            "tool_id",
            "benchmark_id",
            "action_role",
            "carrier_frequency",
            "baseline_profile_id",
            "inner_selection_policy_id",
            "outer_validation_policy_id",
            "stable_plateau_policy_id",
        ):
            _text(getattr(self, field), field)
        if self.action_role not in REQUIRED_ACTION_ROLES:
            raise ValidationError(f"unsupported action role: {self.action_role}")
        if self.carrier_frequency not in TOOL_CAPABILITY_FREQUENCIES:
            raise ValidationError(f"unsupported carrier frequency: {self.carrier_frequency}")
        baseline = _parameters(self.baseline_parameters, "baseline_parameters")
        domains = tuple(self.parameter_domains)
        if not domains:
            raise ValidationError("parameter_domains cannot be empty")
        domain_ids = tuple(item.parameter_id for item in domains)
        if len(set(domain_ids)) != len(domain_ids):
            raise ValidationError("parameter domain ids must be unique")
        if set(domain_ids) != set(baseline):
            raise ValidationError("parameter domains must exactly cover baseline parameters")
        for domain in domains:
            if baseline[domain.parameter_id] != domain.default_value:
                raise ValidationError("parameter default must match baseline parameters")
        constraints = tuple(_text(item, "cross_parameter_constraints") for item in self.cross_parameter_constraints)
        objectives = tuple(self.objective_metric_ids)
        risks = tuple(self.risk_constraint_metric_ids)
        if not objectives:
            raise ValidationError("objective_metric_ids cannot be empty")
        if not set(objectives + risks).issubset(REQUIRED_EFFECT_METRICS):
            raise ValidationError("parameter contract contains unsupported metrics")
        if self.search_space_status not in {"baseline_only", "frozen_grid"}:
            raise ValidationError("search_space_status is invalid")
        grid_size = math.prod(len(item.candidate_values) for item in domains)
        if self.search_space_status == "baseline_only":
            if any(item.tunable for item in domains) or grid_size != 1:
                raise ValidationError("baseline_only contract cannot expose tunable values")
            if self.maximum_candidate_profiles != 1:
                raise ValidationError("baseline_only contract has exactly one profile")
        else:
            if not any(item.tunable for item in domains) or grid_size < 2:
                raise ValidationError("frozen_grid contract requires a tunable domain")
            if not 1 < self.maximum_candidate_profiles <= grid_size:
                raise ValidationError("maximum_candidate_profiles exceeds frozen grid")
        if self.blackbox_exclusion != TOOL_CAPABILITY_BLACKBOX_EXCLUSION:
            raise ValidationError("parameter contract blackbox range is not frozen")
        if self.production_authority:
            raise ValidationError("parameter contract cannot grant production authority")
        expected_id = _short_digest(
            "parameter-contract",
            _parameter_contract_identity(
                tool_id=self.tool_id,
                benchmark_id=self.benchmark_id,
                action_role=self.action_role,
                carrier_frequency=self.carrier_frequency,
                baseline_profile_id=self.baseline_profile_id,
                baseline_parameters=baseline,
                parameter_domains=domains,
                cross_parameter_constraints=constraints,
                objective_metric_ids=objectives,
                risk_constraint_metric_ids=risks,
                search_space_status=self.search_space_status,
                maximum_candidate_profiles=self.maximum_candidate_profiles,
                inner_selection_policy_id=self.inner_selection_policy_id,
                outer_validation_policy_id=self.outer_validation_policy_id,
                stable_plateau_policy_id=self.stable_plateau_policy_id,
            ),
        )
        if self.contract_id != expected_id:
            raise ValidationError("parameter contract id does not match its content")
        object.__setattr__(self, "baseline_parameters", baseline)
        object.__setattr__(self, "parameter_domains", domains)
        object.__setattr__(self, "cross_parameter_constraints", constraints)
        object.__setattr__(self, "objective_metric_ids", objectives)
        object.__setattr__(self, "risk_constraint_metric_ids", risks)

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_id": self.contract_id,
            "tool_id": self.tool_id,
            "benchmark_id": self.benchmark_id,
            "action_role": self.action_role,
            "carrier_frequency": self.carrier_frequency,
            "baseline_profile_id": self.baseline_profile_id,
            "baseline_parameters": dict(self.baseline_parameters),
            "parameter_domains": [item.to_dict() for item in self.parameter_domains],
            "cross_parameter_constraints": list(self.cross_parameter_constraints),
            "objective_metric_ids": list(self.objective_metric_ids),
            "risk_constraint_metric_ids": list(self.risk_constraint_metric_ids),
            "search_space_status": self.search_space_status,
            "maximum_candidate_profiles": self.maximum_candidate_profiles,
            "inner_selection_policy_id": self.inner_selection_policy_id,
            "outer_validation_policy_id": self.outer_validation_policy_id,
            "stable_plateau_policy_id": self.stable_plateau_policy_id,
            "blackbox_exclusion": list(self.blackbox_exclusion),
            "research_executed": self.research_executed,
            "production_authority": self.production_authority,
        }


@dataclass(frozen=True, slots=True)
class ToolProfileSpec:
    """Complete and cost-aware profile; the minimum unit allowed to battle."""

    profile_id: str
    tool_id: str
    benchmark_id: str
    action_role: str
    carrier_frequency: str
    parameter_contract_id: str
    parameters: Mapping[str, Primitive]
    signal_semantics: str
    execution_lag_bars: int
    cost_bps: float
    production_authority: bool = False

    def __post_init__(self) -> None:
        for field in (
            "profile_id",
            "tool_id",
            "benchmark_id",
            "action_role",
            "carrier_frequency",
            "parameter_contract_id",
            "signal_semantics",
        ):
            _text(getattr(self, field), field)
        benchmark_index = {item.benchmark_id: item for item in tool_benchmark_specs()}
        benchmark = benchmark_index.get(self.benchmark_id)
        if benchmark is None or benchmark.tool_id != self.tool_id:
            raise ValidationError("profile benchmark does not match its tool")
        if self.action_role not in REQUIRED_ACTION_ROLES:
            raise ValidationError(f"unsupported action role: {self.action_role}")
        if self.carrier_frequency not in benchmark.parameters_by_frequency:
            raise ValidationError("profile frequency is not benchmarked for this tool")
        parameters = _parameters(self.parameters, "profile parameters")
        if isinstance(self.execution_lag_bars, bool) or self.execution_lag_bars < 1:
            raise ValidationError("profile execution_lag_bars must be at least one")
        if not math.isfinite(float(self.cost_bps)) or self.cost_bps < 0.0:
            raise ValidationError("profile cost_bps must be finite and non-negative")
        expected_id = make_profile_id(
            tool_id=self.tool_id,
            benchmark_id=self.benchmark_id,
            action_role=self.action_role,
            carrier_frequency=self.carrier_frequency,
            parameters=parameters,
            signal_semantics=self.signal_semantics,
            execution_lag_bars=self.execution_lag_bars,
            cost_bps=float(self.cost_bps),
        )
        if self.profile_id != expected_id:
            raise ValidationError("profile id does not match its complete content")
        if self.production_authority:
            raise ValidationError("tool profile cannot grant production authority")
        object.__setattr__(self, "parameters", parameters)
        object.__setattr__(self, "cost_bps", float(self.cost_bps))

    def to_dict(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "tool_id": self.tool_id,
            "benchmark_id": self.benchmark_id,
            "action_role": self.action_role,
            "carrier_frequency": self.carrier_frequency,
            "parameter_contract_id": self.parameter_contract_id,
            "parameters": dict(self.parameters),
            "signal_semantics": self.signal_semantics,
            "execution_lag_bars": self.execution_lag_bars,
            "cost_bps": self.cost_bps,
            "production_authority": self.production_authority,
        }


def _capability_certificate_identity(
    *,
    profile_id: str,
    parameter_contract_id: str,
    certification_status: str,
    profile_kind: str,
    research_executed: bool,
    outer_validation_completed: bool,
    outer_fold_count: int,
    positive_outer_fold_count: int,
    stable_plateau_validated: bool,
    conditional_rank_reversal_validated: bool,
    state_axis_registry_digest: str,
    fixed_fallback_profile_id: str,
    support_domain_ids: tuple[str, ...],
    failure_domain_ids: tuple[str, ...],
    metric_summary: Mapping[str, float],
    oracle_upper_bound_summary: Mapping[str, float],
    evidence_refs: Mapping[str, str],
) -> dict[str, object]:
    return {
        "profile_id": profile_id,
        "parameter_contract_id": parameter_contract_id,
        "certification_status": certification_status,
        "profile_kind": profile_kind,
        "research_executed": research_executed,
        "outer_validation_completed": outer_validation_completed,
        "outer_fold_count": outer_fold_count,
        "positive_outer_fold_count": positive_outer_fold_count,
        "stable_plateau_validated": stable_plateau_validated,
        "conditional_rank_reversal_validated": (conditional_rank_reversal_validated),
        "state_axis_registry_digest": state_axis_registry_digest,
        "fixed_fallback_profile_id": fixed_fallback_profile_id,
        "support_domain_ids": list(support_domain_ids),
        "failure_domain_ids": list(failure_domain_ids),
        "metric_summary": dict(sorted(metric_summary.items())),
        "oracle_upper_bound_summary": dict(sorted(oracle_upper_bound_summary.items())),
        "evidence_refs": dict(sorted(evidence_refs.items())),
    }


@dataclass(frozen=True, slots=True)
class ToolCapabilityCertificate:
    """Evidence-gated certificate; contract-only records make no performance claim."""

    certificate_id: str
    profile_id: str
    parameter_contract_id: str
    certification_status: str
    profile_kind: str
    research_executed: bool
    outer_validation_completed: bool
    outer_fold_count: int
    positive_outer_fold_count: int
    stable_plateau_validated: bool
    conditional_rank_reversal_validated: bool
    state_axis_registry_digest: str
    fixed_fallback_profile_id: str
    support_domain_ids: tuple[str, ...]
    failure_domain_ids: tuple[str, ...]
    metric_summary: Mapping[str, float]
    oracle_upper_bound_summary: Mapping[str, float]
    evidence_refs: Mapping[str, str]
    blackbox_exclusion: tuple[str, str] = TOOL_CAPABILITY_BLACKBOX_EXCLUSION
    production_authority: bool = False

    oracle_is_training_only: ClassVar[bool] = True

    def __post_init__(self) -> None:
        for field in ("certificate_id", "profile_id", "parameter_contract_id"):
            _text(getattr(self, field), field)
        if self.certification_status not in TOOL_CERTIFICATION_STATUSES:
            raise ValidationError("capability certification_status is invalid")
        if self.profile_kind not in {"fixed", "dynamic"}:
            raise ValidationError("capability profile_kind is invalid")
        if self.outer_fold_count < 0:
            raise ValidationError("outer_fold_count cannot be negative")
        if not 0 <= self.positive_outer_fold_count <= self.outer_fold_count:
            raise ValidationError("positive_outer_fold_count is invalid")
        support = tuple(_text(item, "support_domain_ids") for item in self.support_domain_ids)
        failure = tuple(_text(item, "failure_domain_ids") for item in self.failure_domain_ids)
        if set(support).intersection(failure):
            raise ValidationError("support and failure domains cannot overlap")
        metrics = _metric_mapping(self.metric_summary, "metric_summary")
        oracle = _metric_mapping(
            self.oracle_upper_bound_summary,
            "oracle_upper_bound_summary",
        )
        evidence = _string_mapping(self.evidence_refs, "evidence_refs")
        if self.certification_status == "contract_only":
            if (
                self.research_executed
                or self.outer_validation_completed
                or self.outer_fold_count
                or self.positive_outer_fold_count
                or self.stable_plateau_validated
                or self.conditional_rank_reversal_validated
                or self.state_axis_registry_digest
                or self.fixed_fallback_profile_id
                or support
                or failure
                or metrics
                or oracle
                or evidence
            ):
                raise ValidationError("contract_only certificate cannot contain evidence")
        elif self.certification_status in {"certified_fixed", "certified_dynamic"}:
            if (
                not self.research_executed
                or not self.outer_validation_completed
                or self.outer_fold_count < 3
                or self.positive_outer_fold_count <= self.outer_fold_count / 2
                or not self.stable_plateau_validated
                or not metrics
                or not evidence
            ):
                raise ValidationError("certified capability lacks outer-fold evidence")
            if self.certification_status == "certified_dynamic":
                if (
                    self.profile_kind != "dynamic"
                    or not self.conditional_rank_reversal_validated
                    or not self.state_axis_registry_digest.startswith("sha256:")
                    or not self.fixed_fallback_profile_id
                ):
                    raise ValidationError("dynamic certificate lacks state/fallback evidence")
            elif (
                self.profile_kind != "fixed"
                or self.conditional_rank_reversal_validated
                or self.state_axis_registry_digest
                or self.fixed_fallback_profile_id
            ):
                raise ValidationError("fixed certificate cannot claim dynamic evidence")
        elif not self.research_executed or not evidence:
            raise ValidationError("rejected capability must retain its failed evidence")
        if self.blackbox_exclusion != TOOL_CAPABILITY_BLACKBOX_EXCLUSION:
            raise ValidationError("capability certificate blackbox range is not frozen")
        if self.production_authority:
            raise ValidationError("capability certificate cannot grant production authority")
        identity = _capability_certificate_identity(
            profile_id=self.profile_id,
            parameter_contract_id=self.parameter_contract_id,
            certification_status=self.certification_status,
            profile_kind=self.profile_kind,
            research_executed=self.research_executed,
            outer_validation_completed=self.outer_validation_completed,
            outer_fold_count=self.outer_fold_count,
            positive_outer_fold_count=self.positive_outer_fold_count,
            stable_plateau_validated=self.stable_plateau_validated,
            conditional_rank_reversal_validated=(self.conditional_rank_reversal_validated),
            state_axis_registry_digest=self.state_axis_registry_digest,
            fixed_fallback_profile_id=self.fixed_fallback_profile_id,
            support_domain_ids=support,
            failure_domain_ids=failure,
            metric_summary=metrics,
            oracle_upper_bound_summary=oracle,
            evidence_refs=evidence,
        )
        expected_id = _short_digest("capability-certificate", identity)
        if self.certificate_id != expected_id:
            raise ValidationError("capability certificate id does not match its content")
        object.__setattr__(self, "support_domain_ids", support)
        object.__setattr__(self, "failure_domain_ids", failure)
        object.__setattr__(self, "metric_summary", metrics)
        object.__setattr__(self, "oracle_upper_bound_summary", oracle)
        object.__setattr__(self, "evidence_refs", evidence)

    def to_dict(self) -> dict[str, object]:
        return {
            "certificate_id": self.certificate_id,
            "profile_id": self.profile_id,
            "parameter_contract_id": self.parameter_contract_id,
            "certification_status": self.certification_status,
            "profile_kind": self.profile_kind,
            "research_executed": self.research_executed,
            "outer_validation_completed": self.outer_validation_completed,
            "outer_fold_count": self.outer_fold_count,
            "positive_outer_fold_count": self.positive_outer_fold_count,
            "stable_plateau_validated": self.stable_plateau_validated,
            "conditional_rank_reversal_validated": (self.conditional_rank_reversal_validated),
            "state_axis_registry_digest": self.state_axis_registry_digest,
            "fixed_fallback_profile_id": self.fixed_fallback_profile_id,
            "support_domain_ids": list(self.support_domain_ids),
            "failure_domain_ids": list(self.failure_domain_ids),
            "metric_summary": dict(self.metric_summary),
            "oracle_upper_bound_summary": dict(self.oracle_upper_bound_summary),
            "oracle_is_training_only": self.oracle_is_training_only,
            "evidence_refs": dict(self.evidence_refs),
            "blackbox_exclusion": list(self.blackbox_exclusion),
            "production_authority": self.production_authority,
        }


def make_capability_certificate(
    *,
    profile_id: str,
    parameter_contract_id: str,
    certification_status: str,
    profile_kind: str,
    research_executed: bool,
    outer_validation_completed: bool,
    outer_fold_count: int,
    positive_outer_fold_count: int,
    stable_plateau_validated: bool,
    conditional_rank_reversal_validated: bool = False,
    state_axis_registry_digest: str = "",
    fixed_fallback_profile_id: str = "",
    support_domain_ids: tuple[str, ...] = (),
    failure_domain_ids: tuple[str, ...] = (),
    metric_summary: Mapping[str, float] | None = None,
    oracle_upper_bound_summary: Mapping[str, float] | None = None,
    evidence_refs: Mapping[str, str] | None = None,
) -> ToolCapabilityCertificate:
    """Build a certificate whose identity is derived from its evidence payload."""

    metrics = dict(metric_summary or {})
    oracle = dict(oracle_upper_bound_summary or {})
    evidence = dict(evidence_refs or {})
    identity = _capability_certificate_identity(
        profile_id=profile_id,
        parameter_contract_id=parameter_contract_id,
        certification_status=certification_status,
        profile_kind=profile_kind,
        research_executed=research_executed,
        outer_validation_completed=outer_validation_completed,
        outer_fold_count=outer_fold_count,
        positive_outer_fold_count=positive_outer_fold_count,
        stable_plateau_validated=stable_plateau_validated,
        conditional_rank_reversal_validated=conditional_rank_reversal_validated,
        state_axis_registry_digest=state_axis_registry_digest,
        fixed_fallback_profile_id=fixed_fallback_profile_id,
        support_domain_ids=support_domain_ids,
        failure_domain_ids=failure_domain_ids,
        metric_summary=metrics,
        oracle_upper_bound_summary=oracle,
        evidence_refs=evidence,
    )
    return ToolCapabilityCertificate(
        certificate_id=_short_digest("capability-certificate", identity),
        profile_id=profile_id,
        parameter_contract_id=parameter_contract_id,
        certification_status=certification_status,
        profile_kind=profile_kind,
        research_executed=research_executed,
        outer_validation_completed=outer_validation_completed,
        outer_fold_count=outer_fold_count,
        positive_outer_fold_count=positive_outer_fold_count,
        stable_plateau_validated=stable_plateau_validated,
        conditional_rank_reversal_validated=conditional_rank_reversal_validated,
        state_axis_registry_digest=state_axis_registry_digest,
        fixed_fallback_profile_id=fixed_fallback_profile_id,
        support_domain_ids=support_domain_ids,
        failure_domain_ids=failure_domain_ids,
        metric_summary=metrics,
        oracle_upper_bound_summary=oracle,
        evidence_refs=evidence,
    )


@dataclass(frozen=True, slots=True)
class ToolCapabilityContractBundle:
    """Cross-reference-complete R0 bundle for all frozen tool benchmarks."""

    profiles: tuple[ToolProfileSpec, ...]
    parameter_contracts: tuple[ParameterResearchContract, ...]
    capability_certificates: tuple[ToolCapabilityCertificate, ...]
    blackbox_exclusion: tuple[str, str] = TOOL_CAPABILITY_BLACKBOX_EXCLUSION

    schema_id: ClassVar[str] = TOOL_CAPABILITY_CONTRACT_SCHEMA_ID
    registry_version: ClassVar[str] = TOOL_CAPABILITY_CONTRACT_VERSION
    research_executed: ClassVar[bool] = False
    routing_authority: ClassVar[bool] = False
    production_authority: ClassVar[bool] = False

    def __post_init__(self) -> None:
        profiles = tuple(self.profiles)
        contracts = tuple(self.parameter_contracts)
        certificates = tuple(self.capability_certificates)
        if not profiles or len(profiles) != len(contracts) or len(profiles) != len(certificates):
            raise ValidationError("capability contract bundle has incomplete coverage")
        for items, field in (
            (profiles, "profile_id"),
            (contracts, "contract_id"),
            (certificates, "certificate_id"),
        ):
            values = [str(getattr(item, field)) for item in items]
            if len(set(values)) != len(values):
                raise ValidationError(f"capability bundle has duplicate {field}")
        profile_index = {item.profile_id: item for item in profiles}
        contract_index = {item.contract_id: item for item in contracts}
        for profile in profiles:
            contract = contract_index.get(profile.parameter_contract_id)
            if (
                contract is None
                or contract.baseline_profile_id != profile.profile_id
                or contract.tool_id != profile.tool_id
                or contract.action_role != profile.action_role
                or contract.carrier_frequency != profile.carrier_frequency
                or dict(contract.baseline_parameters) != dict(profile.parameters)
            ):
                raise ValidationError("profile and parameter contract do not match")
        for certificate in certificates:
            profile = profile_index.get(certificate.profile_id)
            if profile is None or certificate.parameter_contract_id != profile.parameter_contract_id:
                raise ValidationError("capability certificate does not match its profile")
        expected = {
            (spec.benchmark_id, frequency, action_role)
            for spec in tool_benchmark_specs()
            for frequency in spec.parameters_by_frequency
            for action_role in REQUIRED_ACTION_ROLES
        }
        actual = {(item.benchmark_id, item.carrier_frequency, item.action_role) for item in profiles}
        if len(profiles) != len(expected) or actual != expected:
            raise ValidationError("capability bundle does not cover every benchmark lens")
        if self.blackbox_exclusion != TOOL_CAPABILITY_BLACKBOX_EXCLUSION:
            raise ValidationError("capability bundle blackbox range is not frozen")
        object.__setattr__(self, "profiles", profiles)
        object.__setattr__(self, "parameter_contracts", contracts)
        object.__setattr__(self, "capability_certificates", certificates)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "registry_version": self.registry_version,
            "research_executed": self.research_executed,
            "routing_authority": self.routing_authority,
            "production_authority": self.production_authority,
            "blackbox_exclusion": list(self.blackbox_exclusion),
            "profiles": [item.to_dict() for item in self.profiles],
            "parameter_contracts": [item.to_dict() for item in self.parameter_contracts],
            "capability_certificates": [item.to_dict() for item in self.capability_certificates],
            "field_labels_zh": dict(TOOL_CAPABILITY_LABELS_ZH),
        }


def _parameter_kind(value: Primitive) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return "categorical"


def _contract_only_certificate(
    profile_id: str,
    parameter_contract_id: str,
) -> ToolCapabilityCertificate:
    identity = _capability_certificate_identity(
        profile_id=profile_id,
        parameter_contract_id=parameter_contract_id,
        certification_status="contract_only",
        profile_kind="fixed",
        research_executed=False,
        outer_validation_completed=False,
        outer_fold_count=0,
        positive_outer_fold_count=0,
        stable_plateau_validated=False,
        conditional_rank_reversal_validated=False,
        state_axis_registry_digest="",
        fixed_fallback_profile_id="",
        support_domain_ids=(),
        failure_domain_ids=(),
        metric_summary={},
        oracle_upper_bound_summary={},
        evidence_refs={},
    )
    return ToolCapabilityCertificate(
        certificate_id=_short_digest("capability-certificate", identity),
        profile_id=profile_id,
        parameter_contract_id=parameter_contract_id,
        certification_status="contract_only",
        profile_kind="fixed",
        research_executed=False,
        outer_validation_completed=False,
        outer_fold_count=0,
        positive_outer_fold_count=0,
        stable_plateau_validated=False,
        conditional_rank_reversal_validated=False,
        state_axis_registry_digest="",
        fixed_fallback_profile_id="",
        support_domain_ids=(),
        failure_domain_ids=(),
        metric_summary={},
        oracle_upper_bound_summary={},
        evidence_refs={},
    )


def build_tool_capability_contract_bundle() -> ToolCapabilityContractBundle:
    """Convert every frozen benchmark lens into an honest contract-only profile."""

    # V2 is a read-only completeness check over the selected V1 baselines.  It
    # deliberately does not make a V1 baseline parameter searchable.
    from factor_lab.market_state.tool_parameter_catalog_v2 import (
        build_tool_parameter_catalog_v2,
    )

    build_tool_parameter_catalog_v2()
    profiles: list[ToolProfileSpec] = []
    contracts: list[ParameterResearchContract] = []
    certificates: list[ToolCapabilityCertificate] = []
    for benchmark in tool_benchmark_specs():
        for frequency, raw_values in sorted(benchmark.parameters_by_frequency.items()):
            cost_bps = float(raw_values["cost_bps"])
            baseline = {str(key): cast(Primitive, value) for key, value in raw_values.items() if key != "cost_bps"}
            domains = tuple(
                ParameterDomainSpec(
                    parameter_id=parameter_id,
                    name_zh=_PARAMETER_LABELS_ZH[parameter_id],
                    value_kind=_parameter_kind(value),
                    unit=_parameter_unit(parameter_id),
                    default_value=value,
                    candidate_values=(value,),
                    tunable=False,
                    rationale="现有冻结基准值；正式可调范围由工具前台另行登记",
                )
                for parameter_id, value in sorted(baseline.items())
            )
            for action_role in REQUIRED_ACTION_ROLES:
                profile_id = make_profile_id(
                    tool_id=benchmark.tool_id,
                    benchmark_id=benchmark.benchmark_id,
                    action_role=action_role,
                    carrier_frequency=frequency,
                    parameters=baseline,
                    signal_semantics=benchmark.signal_semantics,
                    execution_lag_bars=1,
                    cost_bps=cost_bps,
                )
                contract_id = make_parameter_contract_id(
                    tool_id=benchmark.tool_id,
                    benchmark_id=benchmark.benchmark_id,
                    action_role=action_role,
                    carrier_frequency=frequency,
                    baseline_profile_id=profile_id,
                    baseline_parameters=baseline,
                    parameter_domains=domains,
                    cross_parameter_constraints=(),
                    objective_metric_ids=(
                        "trade_expectancy",
                        "net_log_return_per_decision_bar",
                    ),
                    risk_constraint_metric_ids=("turnover_per_decision_bar",),
                    search_space_status="baseline_only",
                    maximum_candidate_profiles=1,
                    inner_selection_policy_id="nested_time_inner_train_only_v1",
                    outer_validation_policy_id="purged_time_outer_fold_v1",
                    stable_plateau_policy_id="neighbor_plateau_not_point_optimum_v1",
                )
                profile = ToolProfileSpec(
                    profile_id=profile_id,
                    tool_id=benchmark.tool_id,
                    benchmark_id=benchmark.benchmark_id,
                    action_role=action_role,
                    carrier_frequency=frequency,
                    parameter_contract_id=contract_id,
                    parameters=baseline,
                    signal_semantics=benchmark.signal_semantics,
                    execution_lag_bars=1,
                    cost_bps=cost_bps,
                )
                contract = ParameterResearchContract(
                    contract_id=contract_id,
                    tool_id=benchmark.tool_id,
                    benchmark_id=benchmark.benchmark_id,
                    action_role=action_role,
                    carrier_frequency=frequency,
                    baseline_profile_id=profile_id,
                    baseline_parameters=baseline,
                    parameter_domains=domains,
                    cross_parameter_constraints=(),
                    objective_metric_ids=(
                        "trade_expectancy",
                        "net_log_return_per_decision_bar",
                    ),
                    risk_constraint_metric_ids=("turnover_per_decision_bar",),
                    search_space_status="baseline_only",
                    maximum_candidate_profiles=1,
                    inner_selection_policy_id="nested_time_inner_train_only_v1",
                    outer_validation_policy_id="purged_time_outer_fold_v1",
                    stable_plateau_policy_id="neighbor_plateau_not_point_optimum_v1",
                )
                profiles.append(profile)
                contracts.append(contract)
                certificates.append(_contract_only_certificate(profile_id, contract_id))
    return ToolCapabilityContractBundle(
        profiles=tuple(profiles),
        parameter_contracts=tuple(contracts),
        capability_certificates=tuple(certificates),
    )


__all__ = [
    "TOOL_CAPABILITY_BLACKBOX_EXCLUSION",
    "TOOL_CAPABILITY_CONTRACT_SCHEMA_ID",
    "TOOL_CAPABILITY_CONTRACT_VERSION",
    "TOOL_CAPABILITY_LABELS_ZH",
    "TOOL_CAPABILITY_METRIC_IDS",
    "TOOL_CERTIFICATION_STATUSES",
    "ParameterDomainSpec",
    "ParameterResearchContract",
    "ToolCapabilityCertificate",
    "ToolCapabilityContractBundle",
    "ToolProfileSpec",
    "build_tool_capability_contract_bundle",
    "make_capability_certificate",
    "make_parameter_contract_id",
    "make_profile_id",
]
