# pyright: reportAny=false, reportImplicitStringConcatenation=false
# pyright: reportUnusedCallResult=false
"""Formula-first mechanism contracts for market-state tool research.

This module deliberately performs no market-data research.  It starts from the
implemented benchmark equations, traces their parameters to primitive market
drivers, and freezes falsifiable directions before any empirical test is
allowed.  A formula is a prior over *where to look*, never evidence that a
trading relationship has passed validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.attributes_v1 import ATTRIBUTE_DEFINITIONS_V1
from factor_lab.market_state.tool_registry import (
    DISCOVERED_TOOL_IDS,
    REQUIRED_ACTION_ROLES,
    V2_PARAMETER_CATALOG_MIGRATION_TOOL_IDS,
    tool_benchmark_specs,
    tool_specs,
)

TOOL_FORMULA_MECHANISM_SCHEMA_ID: Final[str] = (
    "market_state_tool_formula_mechanism_bundle@1.0"
)
TOOL_FORMULA_MECHANISM_VERSION: Final[str] = "tool_formula_mechanism_bundle_v1"
TOOL_FORMULA_SURFACE_AUDIT_V2_SCHEMA_ID: Final[str] = (
    "market_state_tool_formula_surface_audit@2.0"
)
TOOL_FORMULA_BLACKBOX_EXCLUSION: Final[tuple[str, str]] = (
    "2021-01-01",
    "2026-12-31",
)

EVIDENCE_LEVELS: Final[tuple[str, ...]] = (
    "algebraic_identity",
    "implementation_identity",
    "model_implication",
    "empirical_hypothesis",
)
SIGNAL_RELEVANCE: Final[tuple[str, ...]] = (
    "direct",
    "validity_only",
    "geometry_only",
)
EFFECT_DIRECTIONS: Final[tuple[str, ...]] = (
    "positive",
    "negative",
    "conditional",
    "non_monotone",
)
RELATIVE_TARGETS: Final[tuple[str, ...]] = (
    "parameter_loss_delta",
    "tool_loss_delta",
)

PERFORMANCE_METRIC_IDS: Final[tuple[str, ...]] = (
    "positive_return_rate",
    "gain_loss_ratio",
    "trade_win_rate",
    "trade_payoff_ratio",
    "trade_expectancy",
    "net_log_return_per_decision_bar",
    "turnover_per_decision_bar",
)


def _required_text(value: str, field: str) -> str:
    if not value.strip():
        raise ValidationError(f"{field} is required")
    return value


@dataclass(frozen=True, slots=True)
class PerformanceIdentitySpec:
    """One exact accounting identity shared by all timing tools."""

    identity_id: str
    action_role: str
    net_value_formula: str
    win_rate_formula: str
    mean_gain_formula: str
    mean_loss_formula: str
    payoff_ratio_formula: str
    expectancy_formula: str
    variable_definitions: tuple[str, ...]
    evidence_level: str = "algebraic_identity"

    def __post_init__(self) -> None:
        for field in (
            "identity_id",
            "action_role",
            "net_value_formula",
            "win_rate_formula",
            "mean_gain_formula",
            "mean_loss_formula",
            "payoff_ratio_formula",
            "expectancy_formula",
        ):
            _required_text(str(getattr(self, field)), field)
        if self.action_role not in REQUIRED_ACTION_ROLES:
            raise ValidationError(f"unknown performance role: {self.action_role}")
        if self.evidence_level != "algebraic_identity":
            raise ValidationError("performance identities must be algebraic identities")
        if not self.variable_definitions:
            raise ValidationError("performance identity variables are required")

    def to_dict(self) -> dict[str, object]:
        return {
            "identity_id": self.identity_id,
            "action_role": self.action_role,
            "net_value_formula": self.net_value_formula,
            "win_rate_formula": self.win_rate_formula,
            "mean_gain_formula": self.mean_gain_formula,
            "mean_loss_formula": self.mean_loss_formula,
            "payoff_ratio_formula": self.payoff_ratio_formula,
            "expectancy_formula": self.expectancy_formula,
            "variable_definitions": list(self.variable_definitions),
            "evidence_level": self.evidence_level,
        }


@dataclass(frozen=True, slots=True)
class ParameterFormulaEffect:
    """How one exposed parameter enters the implemented benchmark equation."""

    parameter_id: str
    formula_term: str
    physical_meaning: str
    benchmark_signal_relevance: str
    expected_tradeoff: str
    evidence_level: str = "implementation_identity"

    def __post_init__(self) -> None:
        for field in (
            "parameter_id",
            "formula_term",
            "physical_meaning",
            "expected_tradeoff",
        ):
            _required_text(str(getattr(self, field)), field)
        if self.benchmark_signal_relevance not in SIGNAL_RELEVANCE:
            raise ValidationError(
                f"invalid signal relevance: {self.benchmark_signal_relevance}"
            )
        if self.evidence_level != "implementation_identity":
            raise ValidationError("parameter effects must be implementation identities")

    def to_dict(self) -> dict[str, object]:
        return {
            "parameter_id": self.parameter_id,
            "formula_term": self.formula_term,
            "physical_meaning": self.physical_meaning,
            "benchmark_signal_relevance": self.benchmark_signal_relevance,
            "expected_tradeoff": self.expected_tradeoff,
            "evidence_level": self.evidence_level,
        }


@dataclass(frozen=True, slots=True)
class ToolFormulaSpec:
    """The implemented transform and decision equation for one registered tool."""

    formula_id: str
    tool_id: str
    transform_formula: str
    signal_formula: str
    execution_formula: str
    implementation_ref: str
    native_source_refs: tuple[str, ...]
    parameter_effects: tuple[ParameterFormulaEffect, ...]
    mechanism_ids: tuple[str, ...]
    evidence_level: str = "implementation_identity"

    def __post_init__(self) -> None:
        for field in (
            "formula_id",
            "tool_id",
            "transform_formula",
            "signal_formula",
            "execution_formula",
            "implementation_ref",
        ):
            _required_text(str(getattr(self, field)), field)
        if self.evidence_level != "implementation_identity":
            raise ValidationError("tool formulas must be implementation identities")
        if not self.native_source_refs:
            raise ValidationError("native source references are required")
        parameter_ids = [item.parameter_id for item in self.parameter_effects]
        if len(parameter_ids) != len(set(parameter_ids)):
            raise ValidationError(f"duplicate parameter effect for {self.tool_id}")
        if not self.mechanism_ids:
            raise ValidationError(f"tool {self.tool_id} needs at least one mechanism")

    def to_dict(self) -> dict[str, object]:
        return {
            "formula_id": self.formula_id,
            "tool_id": self.tool_id,
            "transform_formula": self.transform_formula,
            "signal_formula": self.signal_formula,
            "execution_formula": self.execution_formula,
            "implementation_ref": self.implementation_ref,
            "native_source_refs": list(self.native_source_refs),
            "parameter_effects": [
                item.to_dict() for item in self.parameter_effects
            ],
            "mechanism_ids": list(self.mechanism_ids),
            "evidence_level": self.evidence_level,
        }


@dataclass(frozen=True, slots=True)
class MetricMechanismEffect:
    """A signed, conditional and falsifiable implication for one metric."""

    metric_id: str
    direction: str
    rationale: str
    condition: str

    def __post_init__(self) -> None:
        if self.metric_id not in PERFORMANCE_METRIC_IDS:
            raise ValidationError(f"unsupported mechanism metric: {self.metric_id}")
        if self.direction not in EFFECT_DIRECTIONS:
            raise ValidationError(f"unsupported effect direction: {self.direction}")
        _required_text(self.rationale, "mechanism rationale")
        _required_text(self.condition, "mechanism condition")

    def to_dict(self) -> dict[str, object]:
        return {
            "metric_id": self.metric_id,
            "direction": self.direction,
            "rationale": self.rationale,
            "condition": self.condition,
        }


@dataclass(frozen=True, slots=True)
class MechanismSpec:
    """One formula-derived primitive mechanism, not an empirical conclusion."""

    mechanism_id: str
    name_zh: str
    primitive_driver: str
    causal_chain: tuple[str, ...]
    metric_effects: tuple[MetricMechanismEffect, ...]
    relative_targets: tuple[str, ...]
    applicable_tool_ids: tuple[str, ...]
    assumptions: tuple[str, ...]
    failure_conditions: tuple[str, ...]
    evidence_level: str = "model_implication"

    def __post_init__(self) -> None:
        for field in ("mechanism_id", "name_zh", "primitive_driver"):
            _required_text(str(getattr(self, field)), field)
        if len(self.causal_chain) < 3:
            raise ValidationError("mechanism causal chain must contain at least 3 links")
        if not self.metric_effects:
            raise ValidationError("mechanism metric effects are required")
        if not self.relative_targets or not set(self.relative_targets).issubset(
            RELATIVE_TARGETS
        ):
            raise ValidationError("mechanism relative target is invalid")
        if not self.applicable_tool_ids:
            raise ValidationError("mechanism must apply to at least one tool")
        if not self.assumptions or not self.failure_conditions:
            raise ValidationError("mechanism assumptions and failure conditions are required")
        if self.evidence_level not in {"model_implication", "empirical_hypothesis"}:
            raise ValidationError("mechanism evidence level is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "mechanism_id": self.mechanism_id,
            "name_zh": self.name_zh,
            "primitive_driver": self.primitive_driver,
            "causal_chain": list(self.causal_chain),
            "metric_effects": [item.to_dict() for item in self.metric_effects],
            "relative_targets": list(self.relative_targets),
            "applicable_tool_ids": list(self.applicable_tool_ids),
            "assumptions": list(self.assumptions),
            "failure_conditions": list(self.failure_conditions),
            "evidence_level": self.evidence_level,
        }


@dataclass(frozen=True, slots=True)
class ProposedFactorSpec:
    """A missing causal measurement derived from a formula term."""

    factor_id: str
    name_zh: str
    causal_formula: str
    required_history: str
    source_mechanism_ids: tuple[str, ...]
    proxy_family_id: str
    status: str = "proposed"
    inclusion_authority: bool = False

    def __post_init__(self) -> None:
        for field in (
            "factor_id",
            "name_zh",
            "causal_formula",
            "required_history",
            "proxy_family_id",
        ):
            _required_text(str(getattr(self, field)), field)
        if not self.source_mechanism_ids:
            raise ValidationError("proposed factor needs a source mechanism")
        if self.status != "proposed" or self.inclusion_authority:
            raise ValidationError("missing factors must remain unapproved proposals")

    def to_dict(self) -> dict[str, object]:
        return {
            "factor_id": self.factor_id,
            "name_zh": self.name_zh,
            "causal_formula": self.causal_formula,
            "required_history": self.required_history,
            "source_mechanism_ids": list(self.source_mechanism_ids),
            "proxy_family_id": self.proxy_family_id,
            "status": self.status,
            "inclusion_authority": self.inclusion_authority,
        }


@dataclass(frozen=True, slots=True)
class FactorFormulaMapping:
    """Map one mechanism driver to an existing or proposed measurement."""

    mapping_id: str
    mechanism_id: str
    factor_id: str
    factor_status: str
    relation_to_driver: str
    expected_relation: str
    proxy_family_id: str
    rationale: str
    evidence_level: str = "empirical_hypothesis"

    def __post_init__(self) -> None:
        for field in (
            "mapping_id",
            "mechanism_id",
            "factor_id",
            "relation_to_driver",
            "proxy_family_id",
            "rationale",
        ):
            _required_text(str(getattr(self, field)), field)
        if self.factor_status not in {"existing", "proposed"}:
            raise ValidationError("factor mapping status is invalid")
        if self.expected_relation not in EFFECT_DIRECTIONS:
            raise ValidationError("factor mapping direction is invalid")
        if self.evidence_level != "empirical_hypothesis":
            raise ValidationError("factor mappings must remain empirical hypotheses")

    def to_dict(self) -> dict[str, object]:
        return {
            "mapping_id": self.mapping_id,
            "mechanism_id": self.mechanism_id,
            "factor_id": self.factor_id,
            "factor_status": self.factor_status,
            "relation_to_driver": self.relation_to_driver,
            "expected_relation": self.expected_relation,
            "proxy_family_id": self.proxy_family_id,
            "rationale": self.rationale,
            "evidence_level": self.evidence_level,
        }


@dataclass(frozen=True, slots=True)
class ToolFormulaMechanismBundle:
    """Complete R2F contract-only evidence bundle."""

    tool_formulas: tuple[ToolFormulaSpec, ...]
    performance_identities: tuple[PerformanceIdentitySpec, ...]
    mechanisms: tuple[MechanismSpec, ...]
    factor_mappings: tuple[FactorFormulaMapping, ...]
    proposed_factors: tuple[ProposedFactorSpec, ...]
    blackbox_exclusion: tuple[str, str] = TOOL_FORMULA_BLACKBOX_EXCLUSION
    market_data_rows_read: int = 0
    research_executed: bool = False
    routing_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        _validate_bundle(self)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": TOOL_FORMULA_MECHANISM_SCHEMA_ID,
            "registry_version": TOOL_FORMULA_MECHANISM_VERSION,
            "method": "formula_first_reverse_derivation",
            "formula_is_not_empirical_evidence": True,
            "blind_factor_scan_allowed": False,
            "blackbox_exclusion": list(self.blackbox_exclusion),
            "market_data_rows_read": self.market_data_rows_read,
            "field_labels_zh": {
                "tool_formulas": "工具公式注册表",
                "performance_identities": "做多与空仓绩效恒等式",
                "mechanisms": "公式推导的绩效机制",
                "factor_mappings": "机制与因果属性映射",
                "proposed_factors": "待实现因果因子",
                "research_executed": "是否已执行行情实证",
                "routing_authority": "是否拥有工具路由权",
                "production_authority": "是否拥有生产权",
            },
            "tool_formulas": [item.to_dict() for item in self.tool_formulas],
            "performance_identities": [
                item.to_dict() for item in self.performance_identities
            ],
            "mechanisms": [item.to_dict() for item in self.mechanisms],
            "factor_mappings": [item.to_dict() for item in self.factor_mappings],
            "proposed_factors": [item.to_dict() for item in self.proposed_factors],
            "research_executed": self.research_executed,
            "routing_authority": self.routing_authority,
            "production_authority": self.production_authority,
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload


def _effect(
    parameter_id: str,
    formula_term: str,
    physical_meaning: str,
    expected_tradeoff: str,
    relevance: str = "direct",
) -> ParameterFormulaEffect:
    return ParameterFormulaEffect(
        parameter_id=parameter_id,
        formula_term=formula_term,
        physical_meaning=physical_meaning,
        benchmark_signal_relevance=relevance,
        expected_tradeoff=expected_tradeoff,
    )


def _cost_effect() -> ParameterFormulaEffect:
    return _effect(
        "cost_bps",
        "c = cost_bps / 10000",
        "每次仓位变化的单边对数收益扣减",
        "成本单调降低净交易期望；高切换工具受损更大",
    )


def performance_identity_specs() -> tuple[PerformanceIdentitySpec, ...]:
    """Return exact role-specific accounting identities."""

    variable_definitions = (
        "z_t: decision at bar t, 1=long and 0=cash",
        "r_(t+1): next-bar market log return",
        "c: one-way cost in log-return units",
        "|z_t-z_(t-1)|: decision turnover",
        "p_plus=P(Y_t>0), p_minus=P(Y_t<0), p_zero=P(Y_t=0)",
    )
    return (
        PerformanceIdentitySpec(
            identity_id="long_capture_accounting",
            action_role="long_capture",
            net_value_formula="Y^L_t = z_t*r_(t+1) - c*|z_t-z_(t-1)|",
            win_rate_formula=(
                "bar positive rate=p_plus/(p_plus+p_minus); "
                "episode win rate=P(E_episode>0)"
            ),
            mean_gain_formula="G = E[Y_t | Y_t > 0]",
            mean_loss_formula="L = E[-Y_t | Y_t < 0]",
            payoff_ratio_formula="Q = G / L",
            expectancy_formula="E[Y_t] = p_plus*G - p_minus*L",
            variable_definitions=variable_definitions,
        ),
        PerformanceIdentitySpec(
            identity_id="cash_avoidance_accounting",
            action_role="cash_avoidance",
            net_value_formula=(
                "Y^C_t = -(1-z_t)*r_(t+1) - c*|z_t-z_(t-1)|"
            ),
            win_rate_formula=(
                "bar positive rate=p_plus/(p_plus+p_minus); "
                "episode win rate=P(E_episode>0)"
            ),
            mean_gain_formula="G = E[Y_t | Y_t > 0]",
            mean_loss_formula="L = E[-Y_t | Y_t < 0]",
            payoff_ratio_formula="Q = G / L",
            expectancy_formula="E[Y_t] = p_plus*G - p_minus*L",
            variable_definitions=variable_definitions,
        ),
    )


def _metric(
    metric_id: str,
    direction: str,
    rationale: str,
    condition: str,
) -> MetricMechanismEffect:
    return MetricMechanismEffect(
        metric_id=metric_id,
        direction=direction,
        rationale=rationale,
        condition=condition,
    )


def mechanism_specs() -> tuple[MechanismSpec, ...]:
    """Return formula-derived mechanisms shared by the registered tools."""

    filters = (
        "laplace_iir_mixed_bandpass",
        "butterworth_clean_bandpass",
        "rolling_fourier_bandpass",
        "causal_haar_wavelet_bandpass",
        "frequency_selective_bollinger_channel",
        "causal_asymmetric_arc_state_space_envelope",
    )
    smoothers = (
        "laplace_iir_mixed_bandpass",
        "laplace_iir_lowpass",
        "butterworth_clean_bandpass",
        "rolling_fourier_bandpass",
        "causal_haar_wavelet_bandpass",
        "r3_nested_moving_average_component",
        "butterworth_lowpass_residual_envelope",
        "causal_asymmetric_arc_state_space_envelope",
        "simple_moving_average_trend",
    )
    all_tools = DISCOVERED_TOOL_IDS
    return (
        MechanismSpec(
            mechanism_id="spectral_scale_match",
            name_zh="工具频响与当前能量尺度匹配",
            primitive_driver=(
                "当前价格增量能量在工具有效频响内、边缘及邻频的分配"
            ),
            causal_chain=(
                "频带能量分配改变",
                "工具输出的信号幅度与信噪比改变",
                "参数/工具间方向识别与误切换差改变",
                "相对胜率、盈亏比和换手改变",
            ),
            metric_effects=(
                _metric(
                    "positive_return_rate",
                    "positive",
                    "目标频带能量越集中，输出方向越可能对应可持续价格方向",
                    "目标频带方向具有非零持续性",
                ),
                _metric(
                    "gain_loss_ratio",
                    "positive",
                    "频带匹配提高信号段相对邻频噪声的幅度",
                    "邻频泄漏没有同时同比放大",
                ),
                _metric(
                    "turnover_per_decision_bar",
                    "negative",
                    "目标频带占优时零交叉和方向翻转相对减少",
                    "目标频带并非高频白噪声",
                ),
            ),
            relative_targets=RELATIVE_TARGETS,
            applicable_tool_ids=filters,
            assumptions=(
                "过去窗口内的能量分配对下一段具有有限持续性",
                "两个被比较画像的频响确实不同",
            ),
            failure_conditions=(
                "宽带冲击同时激活所有频段",
                "频带能量高但方向完全随机",
            ),
        ),
        MechanismSpec(
            mechanism_id="delay_duration_tradeoff",
            name_zh="识别延迟与行情持续时间权衡",
            primitive_driver="工具有效延迟相对于当前同向行情剩余寿命的比例",
            causal_chain=(
                "窗口/截止周期/滤波阶数决定有效延迟",
                "行情驻留时间决定可收获的剩余区间",
                "延迟占比改变入场损失与反转回吐",
                "参数/工具相对交易期望改变",
            ),
            metric_effects=(
                _metric(
                    "trade_payoff_ratio",
                    "negative",
                    "延迟占行情寿命越高，可拿到的有利段越短且回吐占比越高",
                    "行情最终发生方向转换",
                ),
                _metric(
                    "trade_win_rate",
                    "conditional",
                    "更慢工具可减少噪声误切换，但可能错过短趋势",
                    "结果由噪声寿命与真实趋势寿命的分离度决定",
                ),
                _metric(
                    "turnover_per_decision_bar",
                    "negative",
                    "更长时间尺度通常压低方向翻转频率",
                    "滤波器保持稳定且无边界重估跳变",
                ),
            ),
            relative_targets=RELATIVE_TARGETS,
            applicable_tool_ids=smoothers,
            assumptions=(
                "行情具有可定义的驻留时间或相关长度",
                "工具延迟可由公式或脉冲响应估计",
            ),
            failure_conditions=(
                "突发跳变主导且无可预见驻留结构",
                "窗口重估造成的非线性跳变压过线性延迟",
            ),
        ),
        MechanismSpec(
            mechanism_id="path_noise_false_switch",
            name_zh="路径噪声导致的虚假方向切换",
            primitive_driver="决策变量相对其短期扰动尺度的边际以及方向翻转压力",
            causal_chain=(
                "低路径效率或高翻转率提高决策变量过零/越轨次数",
                "工具产生短命仓位与反复切换",
                "成本和错误方向棒累积",
                "胜率、交易期望下降且换手上升",
            ),
            metric_effects=(
                _metric(
                    "positive_return_rate",
                    "negative",
                    "边界附近噪声使下一棒方向与刚产生的信号弱相关",
                    "决策变量没有足够边际",
                ),
                _metric(
                    "trade_expectancy",
                    "negative",
                    "短命假信号同时增加小亏损与交易成本",
                    "成本非零且没有更大右尾补偿",
                ),
                _metric(
                    "turnover_per_decision_bar",
                    "positive",
                    "方向翻转直接增加仓位变化次数",
                    "信号没有额外驻留或滞回",
                ),
            ),
            relative_targets=RELATIVE_TARGETS,
            applicable_tool_ids=all_tools,
            assumptions=(
                "历史路径噪声对近期边界穿越风险有条件预测力",
                "被比较画像的平滑或边界敏感度不同",
            ),
            failure_conditions=(
                "单次大趋势收益完全支配大量小额误切换",
                "工具另有未登记滞回把翻转隔离",
            ),
        ),
        MechanismSpec(
            mechanism_id="volatility_width_adaptation",
            name_zh="波动估计与通道宽度适配",
            primitive_driver="真实短期扰动尺度与当前轨宽估计之间的响应差",
            causal_chain=(
                "波动扩张/收缩速度改变",
                "历史波动估计相对真实扰动过窄或过宽",
                "越轨概率、确认延迟与持仓宽容度改变",
                "通道参数间胜率和盈亏比排序改变",
            ),
            metric_effects=(
                _metric(
                    "trade_win_rate",
                    "conditional",
                    "过窄轨增加假突破，过宽轨增加漏命中和迟入",
                    "存在中间稳定宽度平台",
                ),
                _metric(
                    "trade_payoff_ratio",
                    "conditional",
                    "宽度决定入场价格与容忍回撤，两端均可能恶化盈亏比",
                    "后续行情幅度不是恒定值",
                ),
                _metric(
                    "turnover_per_decision_bar",
                    "negative",
                    "更宽或更慢的轨通常减少穿越次数",
                    "中轨自身没有同步快速追价",
                ),
            ),
            relative_targets=RELATIVE_TARGETS,
            applicable_tool_ids=(
                "bollinger_volatility_channel",
                "frequency_selective_bollinger_channel",
                "butterworth_lowpass_residual_envelope",
                "causal_asymmetric_arc_state_space_envelope",
                "causal_trendline_channel",
            ),
            assumptions=(
                "轨宽估计来自有限历史且存在响应半衰期",
                "被比较参数改变宽度或宽度响应速度",
            ),
            failure_conditions=(
                "当前 benchmark 根本不使用上下轨产生信号",
                "跳空远大于所有候选轨宽",
            ),
        ),
        MechanismSpec(
            mechanism_id="breakout_follow_through",
            name_zh="突破后的方向延续",
            primitive_driver="越过公式边界后的方向连续度、边际和驻留时间",
            causal_chain=(
                "价格越过通道/极值/回归轨",
                "突破后方向延续或快速回归",
                "状态机获得趋势段或承担假突破",
                "胜率和单笔盈亏比改变",
            ),
            metric_effects=(
                _metric(
                    "trade_win_rate",
                    "positive",
                    "突破后的同向延续直接提高事件盈利概率",
                    "入场在突破后且没有严重执行延迟",
                ),
                _metric(
                    "trade_payoff_ratio",
                    "positive",
                    "持续突破扩大有利行程并相对固定止退距离",
                    "退出规则能保留主要延续段",
                ),
            ),
            relative_targets=RELATIVE_TARGETS,
            applicable_tool_ids=(
                "bollinger_volatility_channel",
                "frequency_selective_bollinger_channel",
                "donchian_price_channel",
                "causal_trendline_channel",
            ),
            assumptions=(
                "突破行为存在状态依赖的持续性",
                "候选画像的边界位置或确认速度不同",
            ),
            failure_conditions=(
                "消息跳空后立即均值回归",
                "边界随价格同步移动导致名义突破没有相同含义",
            ),
        ),
        MechanismSpec(
            mechanism_id="tail_jump_asymmetry",
            name_zh="上下行尾部与跳变不对称",
            primitive_driver="正负尾部能量、单棒跳变和反转风险的不对称",
            causal_chain=(
                "尖底/圆顶或正负跳变概率改变",
                "对称工具的延迟和轨宽错误变得方向不对称",
                "做多与空仓账本承受不同漏损和误判",
                "角色条件下的胜率和盈亏比改变",
            ),
            metric_effects=(
                _metric(
                    "positive_return_rate",
                    "conditional",
                    "快速反转利于灵敏工具但伤害慢工具；持续跳变结论相反",
                    "必须区分跳变后反转与跳变后延续",
                ),
                _metric(
                    "gain_loss_ratio",
                    "conditional",
                    "尾部方向决定右尾捕获或左尾暴露",
                    "做多与空仓角色分账本评估",
                ),
            ),
            relative_targets=RELATIVE_TARGETS,
            applicable_tool_ids=(
                "causal_haar_wavelet_bandpass",
                "bollinger_volatility_channel",
                "frequency_selective_bollinger_channel",
                "butterworth_lowpass_residual_envelope",
                "causal_asymmetric_arc_state_space_envelope",
                "donchian_price_channel",
            ),
            assumptions=(
                "尾部形态在相邻时期存在条件稳定性",
                "被比较工具对跳变和圆滑变化的响应不同",
            ),
            failure_conditions=(
                "尾部事件太稀少而无法跨期验证",
                "正负尾部被聚合成一个无方向波动率",
            ),
        ),
        MechanismSpec(
            mechanism_id="linear_channel_fit_quality",
            name_zh="线性通道拟合质量",
            primitive_driver="窗口内线性趋势解释度及残差的相关与异方差结构",
            causal_chain=(
                "价格路径偏离或贴合线性通道",
                "OLS 斜率与残差轨的估计误差改变",
                "下轨穿越和斜率翻转的可靠性改变",
                "趋势线参数的相对胜率与退出损失改变",
            ),
            metric_effects=(
                _metric(
                    "trade_win_rate",
                    "positive",
                    "高解释度下斜率方向与轨道边界更有结构意义",
                    "残差没有强自相关和突变方差",
                ),
                _metric(
                    "trade_payoff_ratio",
                    "negative",
                    "残差强相关会使一次越轨扩展为连续不利段",
                    "退出依赖固定残差倍数",
                ),
            ),
            relative_targets=RELATIVE_TARGETS,
            applicable_tool_ids=("causal_trendline_channel",),
            assumptions=(
                "窗口内局部线性近似有意义",
                "不同窗口确实产生不同拟合偏差",
            ),
            failure_conditions=(
                "强曲率或多拐点路径",
                "残差分布快速变宽且轨宽来不及更新",
            ),
        ),
        MechanismSpec(
            mechanism_id="extrema_memory",
            name_zh="滚动极值记忆与刷新速度",
            primitive_driver="滚动高低点的年龄、刷新方向及区间位置",
            causal_chain=(
                "窗口长度决定历史极值保留多久",
                "极值刷新速度决定突破门槛远近",
                "入场和退出延迟及假突破概率改变",
                "Donchian 参数相对表现改变",
            ),
            metric_effects=(
                _metric(
                    "trade_win_rate",
                    "conditional",
                    "持续单向刷新利于突破；交替刷新对应震荡假信号",
                    "高低极值年龄具有方向结构",
                ),
                _metric(
                    "trade_payoff_ratio",
                    "conditional",
                    "长窗口门槛更远、信号少但可能对应更大行情",
                    "行情幅度能覆盖迟入损失",
                ),
            ),
            relative_targets=RELATIVE_TARGETS,
            applicable_tool_ids=("donchian_price_channel",),
            assumptions=(
                "极值年龄含有行情阶段信息",
                "候选窗口覆盖不同的极值记忆尺度",
            ),
            failure_conditions=(
                "无上下文的单棒跳空",
                "极值窗口在所有候选中包含同一个权威高低点",
            ),
        ),
        MechanismSpec(
            mechanism_id="state_space_innovation_fit",
            name_zh="状态空间创新项与模型歧义",
            primitive_driver="模型创新项的白噪声程度及候选周期权重熵",
            causal_chain=(
                "候选弧形周期对当前路径的预测误差改变",
                "创新方差和模型评分改变",
                "中轨权重、方向稳定性与转向速度改变",
                "弧形参数相对胜率、盈亏比和换手改变",
            ),
            metric_effects=(
                _metric(
                    "trade_win_rate",
                    "positive",
                    "创新接近白噪声且权重集中时，中轨方向更可信",
                    "状态空间过程模型与真实路径近似相容",
                ),
                _metric(
                    "turnover_per_decision_bar",
                    "positive",
                    "高权重熵或相关创新使模型选择与中轨方向更易抖动",
                    "模型权重半衰期较短",
                ),
            ),
            relative_targets=RELATIVE_TARGETS,
            applicable_tool_ids=("causal_asymmetric_arc_state_space_envelope",),
            assumptions=(
                "创新诊断能反映模型错配而非单纯价格波动",
                "候选周期集合覆盖真实主导尺度附近",
            ),
            failure_conditions=(
                "全部候选模型同源错配",
                "评分温度或权重半衰期把差异完全抹平",
            ),
        ),
        MechanismSpec(
            mechanism_id="moving_average_separation",
            name_zh="均值尺度分离与价差有效边际",
            primitive_driver="快慢均值或嵌套均值分量相对路径噪声的间距",
            causal_chain=(
                "均值窗口组合决定频率权重",
                "趋势持续性决定快慢均值间距",
                "间距相对噪声决定交叉/分量转向稳定性",
                "均值参数相对胜率和换手改变",
            ),
            metric_effects=(
                _metric(
                    "trade_win_rate",
                    "positive",
                    "均值间距高于扰动尺度时，交叉后的方向更不易立即反转",
                    "间距来自持续趋势而非单棒跳变",
                ),
                _metric(
                    "turnover_per_decision_bar",
                    "negative",
                    "更高有效边际降低边界附近反复交叉",
                    "窗口没有同步剧烈变化",
                ),
            ),
            relative_targets=RELATIVE_TARGETS,
            applicable_tool_ids=(
                "r3_nested_moving_average_component",
                "simple_moving_average_trend",
            ),
            assumptions=(
                "快慢尺度具有可分离的记忆长度",
                "被比较窗口组合的频率权重不同",
            ),
            failure_conditions=(
                "跳空同时移动快慢均值",
                "长期横盘使间距始终接近零",
            ),
        ),
        MechanismSpec(
            mechanism_id="switch_cost_burden",
            name_zh="切换成本负担",
            primitive_driver="仓位翻转率与单次成本相对于毛收益边际的比例",
            causal_chain=(
                "工具公式产生仓位变化",
                "每次变化按 cost_bps 扣减",
                "高翻转画像累积更多确定性成本",
                "净胜率、净盈亏比和净交易期望下降",
            ),
            metric_effects=(
                _metric(
                    "net_log_return_per_decision_bar",
                    "negative",
                    "成本项 c*|Δz| 是逐棒净价值的确定性扣减",
                    "cost_bps > 0",
                ),
                _metric(
                    "positive_return_rate",
                    "negative",
                    "靠近零的毛盈利棒会被成本推为净亏损",
                    "毛收益分布在零附近有质量",
                ),
            ),
            relative_targets=RELATIVE_TARGETS,
            applicable_tool_ids=all_tools,
            assumptions=("两个画像使用相同成本口径",),
            failure_conditions=(
                "cost_bps 为零",
                "被比较画像的仓位路径完全相同",
            ),
        ),
    )


def proposed_factor_specs() -> tuple[ProposedFactorSpec, ...]:
    """Return missing formula-native measurements, all unapproved."""

    return (
        ProposedFactorSpec(
            factor_id="transfer_weighted_energy_share",
            name_zh="工具频响加权能量占比",
            causal_formula=(
                "sum_f |H_theta(f)|^2 I_t(f) / "
                "sum_f I_t(f), using a trailing-only spectrum"
            ),
            required_history="至少覆盖工具最长有效周期的严格历史窗口",
            source_mechanism_ids=("spectral_scale_match",),
            proxy_family_id="spectral_ownership",
        ),
        ProposedFactorSpec(
            factor_id="spectral_edge_leakage",
            name_zh="频带边缘泄漏压力",
            causal_formula=(
                "energy in adjacent edge bands divided by transfer-weighted "
                "in-band energy"
            ),
            required_history="与目标频带一致的严格历史窗口",
            source_mechanism_ids=("spectral_scale_match",),
            proxy_family_id="spectral_ownership",
        ),
        ProposedFactorSpec(
            factor_id="group_delay_to_run_age",
            name_zh="群延迟与同向段年龄比",
            causal_formula=(
                "tool group delay at the causal dominant frequency / "
                "max(directional_run_age, 1)"
            ),
            required_history="工具系数加当前严格因果主频/同向段年龄",
            source_mechanism_ids=("delay_duration_tradeoff",),
            proxy_family_id="memory_duration",
        ),
        ProposedFactorSpec(
            factor_id="signal_margin_to_noise",
            name_zh="决策边际信噪比",
            causal_formula=(
                "absolute distance of the tool decision variable from its "
                "switch boundary / robust trailing scale of its increments"
            ),
            required_history="工具决策变量和其严格历史增量",
            source_mechanism_ids=("path_noise_false_switch",),
            proxy_family_id="path_noise",
        ),
        ProposedFactorSpec(
            factor_id="width_response_gap",
            name_zh="轨宽响应缺口",
            causal_formula=(
                "abs(fast realized scale - current channel width scale) / "
                "(current channel width scale + epsilon)"
            ),
            required_history="快波动窗口和当前轨宽估计的全部既有历史",
            source_mechanism_ids=("volatility_width_adaptation",),
            proxy_family_id="volatility_transition",
        ),
        ProposedFactorSpec(
            factor_id="standardized_breakout_margin",
            name_zh="标准化突破边际",
            causal_formula=(
                "signed distance from close to the active causal boundary / "
                "trailing residual scale"
            ),
            required_history="决策棒收盘、决策前边界和历史残差尺度",
            source_mechanism_ids=("breakout_follow_through",),
            proxy_family_id="breakout_persistence",
        ),
        ProposedFactorSpec(
            factor_id="prior_breakout_followthrough",
            name_zh="既往突破延续率",
            causal_formula=(
                "rolling outcome rate of only previously completed comparable "
                "breakouts; current and future events excluded"
            ),
            required_history="当前时点前已完整结束的同口径突破事件",
            source_mechanism_ids=("breakout_follow_through",),
            proxy_family_id="breakout_persistence",
        ),
        ProposedFactorSpec(
            factor_id="rolling_regression_r2",
            name_zh="滚动线性通道解释度",
            causal_formula=(
                "1 - sum(previous-window OLS residual^2) / "
                "sum((log_close-mean)^2)"
            ),
            required_history="与趋势线窗口完全一致的决策前历史",
            source_mechanism_ids=("linear_channel_fit_quality",),
            proxy_family_id="linear_fit_quality",
        ),
        ProposedFactorSpec(
            factor_id="regression_residual_autocorrelation",
            name_zh="通道残差自相关",
            causal_formula=(
                "lag-one correlation of previous-window OLS residuals"
            ),
            required_history="与趋势线窗口完全一致的决策前残差",
            source_mechanism_ids=("linear_channel_fit_quality",),
            proxy_family_id="linear_fit_quality",
        ),
        ProposedFactorSpec(
            factor_id="extrema_age_imbalance",
            name_zh="高低极值年龄差",
            causal_formula=(
                "(age_since_rolling_high - age_since_rolling_low) / window"
            ),
            required_history="Donchian 候选窗口内的历史高低点",
            source_mechanism_ids=("extrema_memory",),
            proxy_family_id="extrema_memory",
        ),
        ProposedFactorSpec(
            factor_id="innovation_whiteness",
            name_zh="状态空间创新白噪声度",
            causal_formula=(
                "1 - max absolute autocorrelation of standardized innovations "
                "over registered lags"
            ),
            required_history="当前时点前的模型创新项和创新方差",
            source_mechanism_ids=("state_space_innovation_fit",),
            proxy_family_id="state_space_fit",
        ),
        ProposedFactorSpec(
            factor_id="model_weight_entropy",
            name_zh="候选周期权重熵",
            causal_formula=(
                "-sum_j w_j log(w_j) / log(number_of_candidate_models)"
            ),
            required_history="当前决策时点已更新的候选模型权重",
            source_mechanism_ids=("state_space_innovation_fit",),
            proxy_family_id="state_space_fit",
        ),
        ProposedFactorSpec(
            factor_id="ma_spread_to_noise",
            name_zh="均值尺度间距信噪比",
            causal_formula=(
                "abs(fast_mean - slow_mean or nested_component) / "
                "robust trailing return scale"
            ),
            required_history="均值窗口及同长度严格历史波动尺度",
            source_mechanism_ids=("moving_average_separation",),
            proxy_family_id="memory_duration",
        ),
    )


def _mapping(
    mechanism_id: str,
    factor_id: str,
    status: str,
    relation: str,
    direction: str,
    family: str,
    rationale: str,
) -> FactorFormulaMapping:
    return FactorFormulaMapping(
        mapping_id=f"mapping:{mechanism_id}:{factor_id}",
        mechanism_id=mechanism_id,
        factor_id=factor_id,
        factor_status=status,
        relation_to_driver=relation,
        expected_relation=direction,
        proxy_family_id=family,
        rationale=rationale,
    )


def factor_formula_mappings() -> tuple[FactorFormulaMapping, ...]:
    """Return pre-registered factor directions; no data are inspected."""

    rows = (
        _mapping(
            "spectral_scale_match",
            "own_scale_activation",
            "existing",
            "本尺度能量相对自身历史基准的代理",
            "positive",
            "spectral_ownership",
            "本尺度被激活时，匹配该尺度的工具输出信噪比应上升",
        ),
        _mapping(
            "spectral_scale_match",
            "neighbor_activation_ratio",
            "existing",
            "邻频相对本频能量的代理",
            "conditional",
            "spectral_ownership",
            "邻频可能提供方向共振，也可能形成泄漏，需结合方向一致性",
        ),
        _mapping(
            "spectral_scale_match",
            "cross_scale_direction_agreement",
            "existing",
            "邻频共振方向的代理",
            "positive",
            "spectral_ownership",
            "相邻尺度同向时，宽频响应工具相对窄频工具可能获益",
        ),
        _mapping(
            "spectral_scale_match",
            "transfer_weighted_energy_share",
            "proposed",
            "直接测量工具频响内能量",
            "positive",
            "spectral_ownership",
            "这是公式原生量，可区分不同频响参数",
        ),
        _mapping(
            "spectral_scale_match",
            "spectral_edge_leakage",
            "proposed",
            "直接测量频带边缘外能量",
            "negative",
            "spectral_ownership",
            "边缘能量高时窗口和阶数差异更可能改变工具排序",
        ),
        _mapping(
            "delay_duration_tradeoff",
            "directional_run_age",
            "existing",
            "已观察同向段寿命",
            "positive",
            "memory_duration",
            "更长同向段给慢工具留下更大可收获空间",
        ),
        _mapping(
            "delay_duration_tradeoff",
            "residence_fraction",
            "existing",
            "方向驻留概率代理",
            "positive",
            "memory_duration",
            "高驻留降低慢工具确认后的立即反转风险",
        ),
        _mapping(
            "delay_duration_tradeoff",
            "bdci",
            "existing",
            "方向连续度代理",
            "positive",
            "memory_duration",
            "连续度高时延迟换取降噪更可能划算",
        ),
        _mapping(
            "delay_duration_tradeoff",
            "lag4_autocorrelation",
            "existing",
            "多棒方向记忆代理",
            "positive",
            "memory_duration",
            "较长记忆支持较慢时间尺度",
        ),
        _mapping(
            "delay_duration_tradeoff",
            "group_delay_to_run_age",
            "proposed",
            "直接比较公式延迟与行情年龄",
            "negative",
            "memory_duration",
            "比值越高，慢参数越可能在剩余行情不足时失效",
        ),
        _mapping(
            "path_noise_false_switch",
            "path_efficiency",
            "existing",
            "净位移相对总路径长度",
            "negative",
            "path_noise",
            "高效率意味着更低虚假切换压力",
        ),
        _mapping(
            "path_noise_false_switch",
            "noise_ratio",
            "existing",
            "路径效率的代数反向代理",
            "positive",
            "path_noise",
            "与 path_efficiency 同源，只能保留一票",
        ),
        _mapping(
            "path_noise_false_switch",
            "sign_flip_rate",
            "existing",
            "原始收益方向翻转压力",
            "positive",
            "path_noise",
            "翻转越频繁，边界附近工具越容易切碎",
        ),
        _mapping(
            "path_noise_false_switch",
            "variance_ratio_4",
            "existing",
            "多棒扩散相对单棒扩散",
            "conditional",
            "path_noise",
            "偏离随机游走可来自趋势或均值回归，必须结合方向量",
        ),
        _mapping(
            "path_noise_false_switch",
            "signal_margin_to_noise",
            "proposed",
            "直接测量决策边际",
            "negative",
            "path_noise",
            "边际越高，虚假穿越压力越低",
        ),
        _mapping(
            "volatility_width_adaptation",
            "volatility_expansion",
            "existing",
            "快波动相对慢基准的变化",
            "positive",
            "volatility_transition",
            "扩张越快，滞后的历史轨宽越可能失配",
        ),
        _mapping(
            "volatility_width_adaptation",
            "fast_slow_volatility_ratio",
            "existing",
            "快慢波动比",
            "positive",
            "volatility_transition",
            "与 volatility_expansion 同源，不能重复投票",
        ),
        _mapping(
            "volatility_width_adaptation",
            "volatility_of_volatility",
            "existing",
            "波动估计不稳定度",
            "positive",
            "volatility_transition",
            "高波动的波动使固定窗口宽度更易落后",
        ),
        _mapping(
            "volatility_width_adaptation",
            "width_response_gap",
            "proposed",
            "直接比较短期扰动与当前轨宽",
            "positive",
            "volatility_transition",
            "该量能区分窗口和半衰期参数的响应误差",
        ),
        _mapping(
            "breakout_follow_through",
            "bdci",
            "existing",
            "突破前方向连续度",
            "positive",
            "breakout_persistence",
            "连续路径比单棒刺穿更可能延续",
        ),
        _mapping(
            "breakout_follow_through",
            "path_efficiency",
            "existing",
            "突破前路径效率",
            "positive",
            "breakout_persistence",
            "高效率降低区间内来回穿轨概率",
        ),
        _mapping(
            "breakout_follow_through",
            "directional_run_age",
            "existing",
            "突破前同向段年龄",
            "conditional",
            "breakout_persistence",
            "成熟趋势可能延续，也可能接近衰竭，需要边际共同判断",
        ),
        _mapping(
            "breakout_follow_through",
            "standardized_breakout_margin",
            "proposed",
            "直接测量越轨幅度",
            "positive",
            "breakout_persistence",
            "越轨边际可区分碰轨与实质突破",
        ),
        _mapping(
            "breakout_follow_through",
            "prior_breakout_followthrough",
            "proposed",
            "严格历史的同类突破基准",
            "positive",
            "breakout_persistence",
            "只用既往完成事件估计当前结构的延续倾向",
        ),
        _mapping(
            "tail_jump_asymmetry",
            "downside_semivolatility",
            "existing",
            "下行尾部能量",
            "conditional",
            "tail_asymmetry",
            "对空仓有利、对做多不利，且需区分反转或延续",
        ),
        _mapping(
            "tail_jump_asymmetry",
            "upside_semivolatility",
            "existing",
            "上行尾部能量",
            "conditional",
            "tail_asymmetry",
            "对做多和空仓账本方向相反",
        ),
        _mapping(
            "tail_jump_asymmetry",
            "tail_energy_concentration",
            "existing",
            "少数极端棒占总能量比例",
            "conditional",
            "tail_asymmetry",
            "可区分圆滑趋势与跳变主导路径",
        ),
        _mapping(
            "tail_jump_asymmetry",
            "jrr",
            "existing",
            "跳变后反转风险",
            "conditional",
            "tail_asymmetry",
            "它区分跳变延续和尖底/尖顶反转",
        ),
        _mapping(
            "linear_channel_fit_quality",
            "path_efficiency",
            "existing",
            "线性可解释性的粗代理",
            "positive",
            "linear_fit_quality",
            "高路径效率通常降低 OLS 残差，但不等同于 R²",
        ),
        _mapping(
            "linear_channel_fit_quality",
            "rolling_regression_r2",
            "proposed",
            "直接测量 OLS 解释度",
            "positive",
            "linear_fit_quality",
            "它与趋势线公式完全同窗同源",
        ),
        _mapping(
            "linear_channel_fit_quality",
            "regression_residual_autocorrelation",
            "proposed",
            "直接测量残差连续偏离",
            "negative",
            "linear_fit_quality",
            "相关残差使固定 sigma 轨低估连续破位风险",
        ),
        _mapping(
            "extrema_memory",
            "price_position",
            "existing",
            "当前价格在滚动区间的位置",
            "conditional",
            "extrema_memory",
            "接近边界是突破必要条件但不是延续充分条件",
        ),
        _mapping(
            "extrema_memory",
            "rolling_range",
            "existing",
            "高低极值间距",
            "conditional",
            "extrema_memory",
            "区间宽度改变触发距离与迟入代价",
        ),
        _mapping(
            "extrema_memory",
            "extrema_age_imbalance",
            "proposed",
            "直接测量哪个方向的极值更近期",
            "conditional",
            "extrema_memory",
            "高低极值年龄差可区分单向刷新与交替震荡",
        ),
        _mapping(
            "state_space_innovation_fit",
            "lag1_autocorrelation",
            "existing",
            "创新错配的粗代理",
            "negative",
            "state_space_fit",
            "价格自相关不等于创新自相关，只能作为弱代理",
        ),
        _mapping(
            "state_space_innovation_fit",
            "volatility_of_volatility",
            "existing",
            "观测方差非平稳代理",
            "negative",
            "state_space_fit",
            "方差快速变化会破坏固定半衰期更新",
        ),
        _mapping(
            "state_space_innovation_fit",
            "innovation_whiteness",
            "proposed",
            "直接诊断模型创新",
            "positive",
            "state_space_fit",
            "创新接近白噪声是状态空间模型相容性的必要诊断",
        ),
        _mapping(
            "state_space_innovation_fit",
            "model_weight_entropy",
            "proposed",
            "直接测量候选周期歧义",
            "negative",
            "state_space_fit",
            "高熵表示没有权威周期，参数切换更不可靠",
        ),
        _mapping(
            "moving_average_separation",
            "path_efficiency",
            "existing",
            "均值间距形成的趋势性代理",
            "positive",
            "memory_duration",
            "高效率更可能形成稳定快慢均值分离",
        ),
        _mapping(
            "moving_average_separation",
            "lag4_autocorrelation",
            "existing",
            "多棒记忆代理",
            "positive",
            "memory_duration",
            "正向多棒记忆支持慢均值确认后的延续",
        ),
        _mapping(
            "moving_average_separation",
            "ma_spread_to_noise",
            "proposed",
            "直接测量交叉边际",
            "positive",
            "memory_duration",
            "间距相对噪声越高，参数间胜负越可能由延迟而非抖动决定",
        ),
        _mapping(
            "switch_cost_burden",
            "sign_flip_rate",
            "existing",
            "潜在切换压力代理",
            "positive",
            "switch_cost",
            "翻转越频繁，高灵敏工具的确定性成本负担越大",
        ),
        _mapping(
            "switch_cost_burden",
            "path_efficiency",
            "existing",
            "低换手环境的反向代理",
            "negative",
            "switch_cost",
            "高效率路径通常减少短命反向切换",
        ),
    )
    return tuple(sorted(rows, key=lambda item: item.mapping_id))


def tool_formula_specs() -> tuple[ToolFormulaSpec, ...]:
    """Return formulas matching every frozen benchmark adapter."""

    adapter = "src/factor_lab/market_state/tool_benchmark_adapters.py"
    cost = _cost_effect
    return (
        ToolFormulaSpec(
            formula_id="formula:laplace_iir_mixed_bandpass",
            tool_id="laplace_iir_mixed_bandpass",
            transform_formula=(
                "y_t=b0*x_t+b1*x_(t-1)+b2*x_(t-2)-a1*y_(t-1)-a2*y_(t-2); "
                "omega=2*pi/P; alpha=sin(omega)/(2Q); "
                "bandpass b=(alpha,0,-alpha)/(1+alpha)"
            ),
            signal_formula="z_t = 1[carried_sign(y_t-y_(t-1)) > 0]",
            execution_formula="decision at close t earns r_(t+1); one-bar lag",
            implementation_ref=f"{adapter}:_iir_bandpass_target",
            native_source_refs=(
                "src/factor_lab/filtering/timing_validation.py",
            ),
            parameter_effects=(
                _effect(
                    "period_bars",
                    "omega=2*pi/period_bars",
                    "中心时间尺度",
                    "更长周期降低响应速度并移动频响中心",
                ),
                _effect(
                    "q",
                    "alpha=sin(omega)/(2*q)",
                    "阻尼与有效带宽",
                    "更高 Q 收窄频响但可能延长振铃",
                ),
                cost(),
            ),
            mechanism_ids=(
                "spectral_scale_match",
                "delay_duration_tradeoff",
                "path_noise_false_switch",
                "switch_cost_burden",
            ),
        ),
        ToolFormulaSpec(
            formula_id="formula:laplace_iir_lowpass",
            tool_id="laplace_iir_lowpass",
            transform_formula=(
                "same biquad recurrence; omega=2*pi/P; alpha=sin(omega)/(2Q); "
                "lowpass b=((1-cos omega)/2,1-cos omega,(1-cos omega)/2)/(1+alpha)"
            ),
            signal_formula="z_t = 1[y_t-y_(t-1) > 0]",
            execution_formula="decision at close t earns r_(t+1); one-bar lag",
            implementation_ref=f"{adapter}:_iir_lowpass_target",
            native_source_refs=(
                "src/factor_lab/filtering/"
                "cloudridge_greenwave_v6_adaptive_super_bull.py",
            ),
            parameter_effects=(
                _effect(
                    "period_bars",
                    "omega=2*pi/period_bars",
                    "低通截止时间尺度",
                    "更长周期更平滑但转向更慢",
                ),
                _effect(
                    "q",
                    "alpha=sin(omega)/(2*q)",
                    "截止附近阻尼与峰化",
                    "改变截止附近增益、超调和延迟",
                ),
                cost(),
            ),
            mechanism_ids=(
                "delay_duration_tradeoff",
                "path_noise_false_switch",
                "switch_cost_burden",
            ),
        ),
        ToolFormulaSpec(
            formula_id="formula:butterworth_clean_bandpass",
            tool_id="butterworth_clean_bandpass",
            transform_formula=(
                "y = SOSFILT(Butterworth(order, "
                "[1/long_period_bars,1/short_period_bars], bandpass), log_close)"
            ),
            signal_formula="z_t = 1[carried_sign(y_t-y_(t-1)) > 0]",
            execution_formula="decision at close t earns r_(t+1); one-bar lag",
            implementation_ref=f"{adapter}:_butterworth_target",
            native_source_refs=(
                "src/factor_lab/filtering/cloudridge_3_0_hybrid_filter_bank.py",
            ),
            parameter_effects=(
                _effect(
                    "short_period_bars",
                    "upper frequency edge=1/short_period_bars",
                    "通带高频边界",
                    "更短边界纳入更多高频并提高灵敏度",
                ),
                _effect(
                    "long_period_bars",
                    "lower frequency edge=1/long_period_bars",
                    "通带低频边界",
                    "更长边界纳入更慢背景并增加延迟",
                ),
                _effect(
                    "order",
                    "Butterworth SOS order",
                    "频响滚降阶数",
                    "更高阶边界更干净但群延迟和瞬态更强",
                ),
                cost(),
            ),
            mechanism_ids=(
                "spectral_scale_match",
                "delay_duration_tradeoff",
                "path_noise_false_switch",
                "switch_cost_burden",
            ),
        ),
        ToolFormulaSpec(
            formula_id="formula:rolling_fourier_bandpass",
            tool_id="rolling_fourier_bandpass",
            transform_formula=(
                "for trailing W: X=FFT(x-mean(x)); "
                "M(f)=1[1/P_high<=|f|<=1/P_low]; y_t=IFFT(M*X)[-1]"
            ),
            signal_formula="z_t = 1[carried_sign(y_t-y_(t-1)) > 0]",
            execution_formula="decision at close t earns r_(t+1); one-bar lag",
            implementation_ref=f"{adapter}:_fourier_bandpass_target",
            native_source_refs=(
                "src/factor_lab/filtering/timing_validation.py",
            ),
            parameter_effects=(
                _effect(
                    "window_bars",
                    "trailing DFT length W",
                    "频率分辨率与局部平稳窗口",
                    "更长窗提高分辨率但加大非平稳和边缘响应",
                ),
                _effect(
                    "low_period_bars",
                    "upper frequency edge=1/low_period_bars",
                    "通带高频边界",
                    "决定纳入的最快尺度",
                ),
                _effect(
                    "high_period_bars",
                    "lower frequency edge=1/high_period_bars",
                    "通带低频边界",
                    "决定纳入的最慢尺度",
                ),
                cost(),
            ),
            mechanism_ids=(
                "spectral_scale_match",
                "delay_duration_tradeoff",
                "path_noise_false_switch",
                "switch_cost_burden",
            ),
        ),
        ToolFormulaSpec(
            formula_id="formula:causal_haar_wavelet_bandpass",
            tool_id="causal_haar_wavelet_bandpass",
            transform_formula=(
                "for trailing W: y_t=L_level(x)[-1]-L_slow_level(x)[-1], "
                "where L_j is Haar j-level lowpass reconstruction"
            ),
            signal_formula="z_t = 1[carried_sign(y_t-y_(t-1)) > 0]",
            execution_formula="decision at close t earns r_(t+1); one-bar lag",
            implementation_ref=f"{adapter}:_haar_wavelet_bandpass_target",
            native_source_refs=(
                "src/factor_lab/filtering/timing_validation.py",
            ),
            parameter_effects=(
                _effect(
                    "window_bars",
                    "trailing dyadic transform length W",
                    "局部估计窗口与边界定位",
                    "更长窗增加历史稳定性但可能稀释新尺度",
                ),
                _effect(
                    "level",
                    "fast Haar approximation level",
                    "通带快尺度",
                    "更高层移除更多高频",
                ),
                _effect(
                    "slow_level",
                    "slow Haar approximation level",
                    "通带慢尺度",
                    "与 level 的层级差决定离散频带宽度",
                ),
                cost(),
            ),
            mechanism_ids=(
                "spectral_scale_match",
                "delay_duration_tradeoff",
                "path_noise_false_switch",
                "tail_jump_asymmetry",
                "switch_cost_burden",
            ),
        ),
        ToolFormulaSpec(
            formula_id="formula:r3_nested_moving_average_component",
            tool_id="r3_nested_moving_average_component",
            transform_formula=(
                "y_t=SMA_slow(log_close-SMA_fast(log_close))"
            ),
            signal_formula="z_t = 1[carried_sign(y_t-y_(t-1)) > 0]",
            execution_formula="decision at close t earns r_(t+1); one-bar lag",
            implementation_ref=f"{adapter}:_r3_component_target",
            native_source_refs=(
                "src/factor_lab/filtering/independent_long_experts.py",
            ),
            parameter_effects=(
                _effect(
                    "fast_window_bars",
                    "inner SMA_fast",
                    "局部基准移除尺度",
                    "更长快窗改变被保留的邻近频带",
                ),
                _effect(
                    "slow_window_bars",
                    "outer SMA_slow",
                    "分量平滑与记忆长度",
                    "更长慢窗减少抖动但增加转向延迟",
                ),
                cost(),
            ),
            mechanism_ids=(
                "moving_average_separation",
                "delay_duration_tradeoff",
                "path_noise_false_switch",
                "switch_cost_burden",
            ),
        ),
        ToolFormulaSpec(
            formula_id="formula:bollinger_volatility_channel",
            tool_id="bollinger_volatility_channel",
            transform_formula=(
                "mu_t=SMA_W(close)_(t-1); sigma_t=STD_W(close)_(t-1); "
                "upper=mu+k*sigma"
            ),
            signal_formula=(
                "state enters long when close>upper; exits to cash when close<mu"
            ),
            execution_formula="decision at close t earns r_(t+1); one-bar lag",
            implementation_ref=f"{adapter}:_volatility_channel_target",
            native_source_refs=(
                "src/factor_lab/strategy/services/"
                "risk_off_v58_bollinger_cash_entry_tuning.py",
            ),
            parameter_effects=(
                _effect(
                    "window_bars",
                    "mu and sigma trailing window W",
                    "中轨与宽度记忆长度",
                    "更长窗降低轨道灵敏度但加大波动转场失配",
                ),
                _effect(
                    "width_sigma",
                    "upper=mu+width_sigma*sigma",
                    "突破轨宽",
                    "更宽轨减少假突破但增加漏命中与迟入",
                ),
                cost(),
            ),
            mechanism_ids=(
                "volatility_width_adaptation",
                "breakout_follow_through",
                "path_noise_false_switch",
                "tail_jump_asymmetry",
                "switch_cost_burden",
            ),
        ),
        ToolFormulaSpec(
            formula_id="formula:frequency_selective_bollinger_channel",
            tool_id="frequency_selective_bollinger_channel",
            transform_formula=(
                "m=ButterworthLowpass(P,order)(log_close); "
                "h=ButterworthHigh/Bandpass(P,order)(log_close); "
                "w=width_multiplier*EWMA(sqrt(SMA_W(h^2))); rails=m+/-w"
            ),
            signal_formula=(
                "trend_breakout: enter close>upper, exit close<lower; "
                "mean_repair: arm close<lower, enter on recovery, exit close>=middle"
            ),
            execution_formula="decision at close t earns r_(t+1); one-bar lag",
            implementation_ref=f"{adapter}:_frequency_bollinger_target",
            native_source_refs=(
                "src/factor_lab/strategy/services/"
                "risk_off_v58_frequency_bollinger.py",
            ),
            parameter_effects=(
                _effect(
                    "period_bars",
                    "Butterworth cutoff=1/period_bars",
                    "中轨和厚度分量的目标尺度",
                    "更长周期平滑中轨并移动厚度频段",
                ),
                _effect(
                    "thickness_source",
                    "highpass or [1/P,2/P] bandpass component",
                    "轨宽能量来源",
                    "选择宽带噪声或邻近频带振幅",
                ),
                _effect(
                    "window_multiplier",
                    "W=round(period_bars*window_multiplier)",
                    "RMS 宽度估计窗口",
                    "更长窗降低轨宽响应速度",
                ),
                _effect(
                    "width_multiplier",
                    "w=width_multiplier*smoothed_RMS",
                    "轨宽倍数",
                    "更宽轨降低假突破并增加迟入",
                ),
                _effect(
                    "action",
                    "state transition family",
                    "趋势突破或均值回归语义",
                    "直接改变入场与退出条件，必须视为不同画像",
                ),
                _effect(
                    "filter_order",
                    "Butterworth order",
                    "频响滚降与延迟",
                    "更高阶降低泄漏但增加瞬态和群延迟",
                ),
                cost(),
            ),
            mechanism_ids=(
                "spectral_scale_match",
                "volatility_width_adaptation",
                "breakout_follow_through",
                "path_noise_false_switch",
                "tail_jump_asymmetry",
                "switch_cost_burden",
            ),
        ),
        ToolFormulaSpec(
            formula_id="formula:butterworth_lowpass_residual_envelope",
            tool_id="butterworth_lowpass_residual_envelope",
            transform_formula=(
                "mid=ButterworthLowpass(P,order)(log_close); residual rails are "
                "quantiles of an independent highpass, but benchmark target uses mid only"
            ),
            signal_formula="z_t = 1[mid_t-mid_(t-1)>0 and warmup_valid]",
            execution_formula="decision at close t earns r_(t+1); one-bar lag",
            implementation_ref=f"{adapter}:_lowpass_residual_target",
            native_source_refs=(
                "src/factor_lab/strategy/services/"
                "risk_off_v58_lowpass_residual_envelope.py",
            ),
            parameter_effects=(
                _effect(
                    "cutoff_period_bars",
                    "lowpass cutoff=1/cutoff_period_bars",
                    "中轨截止尺度",
                    "更长截止更平滑但转向更慢",
                ),
                _effect(
                    "lowpass_order",
                    "Butterworth lowpass order",
                    "中轨滚降与延迟",
                    "更高阶减少高频泄漏但增加瞬态和延迟",
                ),
                _effect(
                    "thickness_window_bars",
                    "rail residual quantile window",
                    "几何轨宽历史长度",
                    "当前 benchmark 不用轨道产生仓位",
                    "geometry_only",
                ),
                _effect(
                    "thickness_lower_quantile",
                    "lower residual quantile",
                    "下轨尾部分位",
                    "当前 benchmark 不用轨道产生仓位",
                    "geometry_only",
                ),
                _effect(
                    "thickness_upper_quantile",
                    "upper residual quantile",
                    "上轨尾部分位",
                    "当前 benchmark 不用轨道产生仓位",
                    "geometry_only",
                ),
                _effect(
                    "thickness_smoothing_half_life_bars",
                    "rail EWMA half-life",
                    "轨宽平滑速度",
                    "当前 benchmark 不用轨道产生仓位",
                    "geometry_only",
                ),
                _effect(
                    "warmup_bars",
                    "valid when t+1 >= warmup_bars",
                    "信号有效起点",
                    "只影响样本起始有效性，不改变有效期内方向",
                    "validity_only",
                ),
                cost(),
            ),
            mechanism_ids=(
                "delay_duration_tradeoff",
                "path_noise_false_switch",
                "switch_cost_burden",
            ),
        ),
        ToolFormulaSpec(
            formula_id="formula:causal_asymmetric_arc_state_space_envelope",
            tool_id="causal_asymmetric_arc_state_space_envelope",
            transform_formula=(
                "model_j: m_j=level+a*(cos(phi)-rho*cos(2phi)); "
                "phi_(t+1)=phi_t+2*pi/P_j; EKF update; "
                "mid=sum_j w_j*m_j with score-softmax smoothed weights"
            ),
            signal_formula="z_t = 1[arc_mid_t-arc_mid_(t-1)>0 and warmup_valid]",
            execution_formula="decision at close t earns r_(t+1); one-bar lag",
            implementation_ref=f"{adapter}:_asymmetric_arc_target",
            native_source_refs=(
                "src/factor_lab/strategy/services/"
                "risk_off_v57_asymmetric_arc_envelope.py",
            ),
            parameter_effects=(
                *tuple(
                    _effect(
                        f"candidate_period_{index}",
                        f"phi step for model {index}=2*pi/P_{index}",
                        f"候选弧形周期 {index}",
                        "改变可被模型集合表达的主导尺度",
                    )
                    for index in range(1, 5)
                ),
                _effect(
                    "round_top_sharp_bottom_ratio",
                    "cos(phi)-rho*cos(2phi)",
                    "圆顶尖底曲率不对称",
                    "改变顶部与底部转向的局部曲率",
                ),
                _effect(
                    "initial_amplitude_log",
                    "initial log-amplitude state",
                    "初始波幅先验",
                    "主要影响早期收敛和评分",
                ),
                _effect(
                    "initial_observation_sigma_log",
                    "initial observation variance",
                    "初始观测噪声先验",
                    "主要影响早期卡尔曼增益",
                ),
                _effect(
                    "score_half_life_bars",
                    "EWMA half-life of normalized surprise",
                    "模型评分记忆",
                    "更长记忆降低模型排名跳变但适应更慢",
                ),
                _effect(
                    "model_weight_half_life_bars",
                    "EWMA half-life of model weights",
                    "模型权重惯性",
                    "更长半衰期降低中轨切换抖动但增加错配驻留",
                ),
                _effect(
                    "model_score_temperature",
                    "softmax(-score/temperature)",
                    "模型权重集中度",
                    "更高温度分散权重、更低温度放大胜者切换",
                ),
                _effect(
                    "observation_variance_half_life_bars",
                    "EWMA half-life of innovation square",
                    "观测方差适应速度",
                    "决定冲击后卡尔曼增益恢复速度",
                ),
                _effect(
                    "thickness_window_bars",
                    "rail residual quantile window",
                    "几何轨宽窗口",
                    "当前 benchmark 只交易中轨方向",
                    "geometry_only",
                ),
                _effect(
                    "thickness_lower_quantile",
                    "lower innovation quantile",
                    "下轨分位",
                    "当前 benchmark 只交易中轨方向",
                    "geometry_only",
                ),
                _effect(
                    "thickness_upper_quantile",
                    "upper innovation quantile",
                    "上轨分位",
                    "当前 benchmark 只交易中轨方向",
                    "geometry_only",
                ),
                _effect(
                    "thickness_smoothing_half_life_bars",
                    "rail offset EWMA half-life",
                    "轨宽平滑",
                    "当前 benchmark 只交易中轨方向",
                    "geometry_only",
                ),
                _effect(
                    "warmup_bars",
                    "valid when t+1 >= warmup_bars",
                    "信号有效起点",
                    "只影响有效期起点",
                    "validity_only",
                ),
                cost(),
            ),
            mechanism_ids=(
                "spectral_scale_match",
                "state_space_innovation_fit",
                "delay_duration_tradeoff",
                "path_noise_false_switch",
                "tail_jump_asymmetry",
                "switch_cost_burden",
            ),
        ),
        ToolFormulaSpec(
            formula_id="formula:donchian_price_channel",
            tool_id="donchian_price_channel",
            transform_formula=(
                "upper_t=max(high_(t-W_entry:t-1)); "
                "lower_t=min(low_(t-W_exit:t-1))"
            ),
            signal_formula=(
                "state enters long when close>upper; exits when close<lower"
            ),
            execution_formula="decision at close t earns r_(t+1); one-bar lag",
            implementation_ref=f"{adapter}:_price_channel_target",
            native_source_refs=(
                "src/factor_lab/filtering/independent_long_experts.py",
            ),
            parameter_effects=(
                _effect(
                    "entry_window_bars",
                    "rolling prior high window",
                    "入场极值记忆",
                    "更长窗口减少突破次数但增加迟入距离",
                ),
                _effect(
                    "exit_window_bars",
                    "rolling prior low window",
                    "退出极值记忆",
                    "更长窗口延迟退出并可能扩大单次回吐",
                ),
                cost(),
            ),
            mechanism_ids=(
                "breakout_follow_through",
                "extrema_memory",
                "path_noise_false_switch",
                "tail_jump_asymmetry",
                "switch_cost_burden",
            ),
        ),
        ToolFormulaSpec(
            formula_id="formula:causal_trendline_channel",
            tool_id="causal_trendline_channel",
            transform_formula=(
                "OLS on previous W log-closes: prediction=alpha+beta*W; "
                "lower=prediction-rail_sigma*std(residual)"
            ),
            signal_formula=(
                "enter when beta>0 and log_close>=lower; "
                "exit when beta<=0 or log_close<lower"
            ),
            execution_formula="decision at close t earns r_(t+1); one-bar lag",
            implementation_ref=f"{adapter}:_trendline_channel_target",
            native_source_refs=(
                "src/factor_lab/filtering/"
                "cloudridge_v6_crash_channel_confirmation.py",
            ),
            parameter_effects=(
                _effect(
                    "window_bars",
                    "OLS history length W",
                    "趋势线拟合尺度",
                    "更长窗稳定斜率但可能跨越结构转折",
                ),
                _effect(
                    "rail_sigma",
                    "lower=prediction-rail_sigma*residual_sigma",
                    "退出轨宽",
                    "更宽轨减少误退但扩大失败损失",
                ),
                cost(),
            ),
            mechanism_ids=(
                "linear_channel_fit_quality",
                "breakout_follow_through",
                "volatility_width_adaptation",
                "path_noise_false_switch",
                "switch_cost_burden",
            ),
        ),
        ToolFormulaSpec(
            formula_id="formula:simple_moving_average_trend",
            tool_id="simple_moving_average_trend",
            transform_formula=(
                "fast_t=SMA_fast(close); slow_t=SMA_slow(close)"
            ),
            signal_formula="z_t = 1[fast_t > slow_t]",
            execution_formula="decision at close t earns r_(t+1); one-bar lag",
            implementation_ref=f"{adapter}:_moving_average_target",
            native_source_refs=(
                "src/factor_lab/filtering/timing_validation.py",
            ),
            parameter_effects=(
                _effect(
                    "fast_window_bars",
                    "fast SMA length",
                    "短记忆尺度",
                    "更短快窗更灵敏且更易被噪声翻转",
                ),
                _effect(
                    "slow_window_bars",
                    "slow SMA length",
                    "背景记忆尺度",
                    "更长慢窗提高尺度分离并增加滞后",
                ),
                cost(),
            ),
            mechanism_ids=(
                "moving_average_separation",
                "delay_duration_tradeoff",
                "path_noise_false_switch",
                "switch_cost_burden",
            ),
        ),
    )


def _validate_bundle(bundle: ToolFormulaMechanismBundle) -> None:
    if bundle.blackbox_exclusion != TOOL_FORMULA_BLACKBOX_EXCLUSION:
        raise ValidationError("formula bundle blackbox exclusion changed")
    if (
        bundle.market_data_rows_read != 0
        or bundle.research_executed
        or bundle.routing_authority
        or bundle.production_authority
    ):
        raise ValidationError("R2F is formula-only and cannot claim research authority")

    tool_ids = [item.tool_id for item in bundle.tool_formulas]
    if tuple(tool_ids) != DISCOVERED_TOOL_IDS:
        raise ValidationError("formula coverage differs from the registered tool universe")
    if len({item.formula_id for item in bundle.tool_formulas}) != len(tool_ids):
        raise ValidationError("formula ids must be unique")

    mechanism_by_id = {item.mechanism_id: item for item in bundle.mechanisms}
    if len(mechanism_by_id) != len(bundle.mechanisms):
        raise ValidationError("mechanism ids must be unique")
    for formula in bundle.tool_formulas:
        unknown = set(formula.mechanism_ids) - set(mechanism_by_id)
        if unknown:
            raise ValidationError(
                f"tool {formula.tool_id} references unknown mechanisms: {unknown}"
            )
        for mechanism_id in formula.mechanism_ids:
            if formula.tool_id not in mechanism_by_id[mechanism_id].applicable_tool_ids:
                raise ValidationError(
                    f"tool {formula.tool_id} is absent from mechanism {mechanism_id}"
                )

    benchmarks = {item.tool_id: item for item in tool_benchmark_specs()}
    for formula in bundle.tool_formulas:
        expected_parameters = {
            parameter_id
            for values in benchmarks[formula.tool_id].parameters_by_frequency.values()
            for parameter_id in values
        }
        actual_parameters = {
            item.parameter_id for item in formula.parameter_effects
        }
        if actual_parameters != expected_parameters:
            raise ValidationError(
                f"formula parameter coverage mismatch for {formula.tool_id}: "
                f"expected={sorted(expected_parameters)}, "
                f"actual={sorted(actual_parameters)}"
            )

    registry_sources = {
        item.tool_id: set(item.source_strategy_refs) for item in tool_specs()
    }
    for formula in bundle.tool_formulas:
        if not set(formula.native_source_refs).issubset(
            registry_sources[formula.tool_id]
        ):
            raise ValidationError(
                f"formula source is outside registry provenance: {formula.tool_id}"
            )

    existing_factor_ids = {
        item.physical_attribute_id for item in ATTRIBUTE_DEFINITIONS_V1
    }
    proposed_by_id = {item.factor_id: item for item in bundle.proposed_factors}
    if len(proposed_by_id) != len(bundle.proposed_factors):
        raise ValidationError("proposed factor ids must be unique")
    if existing_factor_ids & set(proposed_by_id):
        raise ValidationError("proposed factors collide with existing attributes")

    mapping_ids = {item.mapping_id for item in bundle.factor_mappings}
    if len(mapping_ids) != len(bundle.factor_mappings):
        raise ValidationError("factor mapping ids must be unique")
    mapped_mechanisms: set[str] = set()
    for mapping in bundle.factor_mappings:
        if mapping.mechanism_id not in mechanism_by_id:
            raise ValidationError("factor mapping references an unknown mechanism")
        mapped_mechanisms.add(mapping.mechanism_id)
        if (
            mapping.factor_status == "existing"
            and mapping.factor_id not in existing_factor_ids
        ):
            raise ValidationError(
                f"mapping references unknown existing factor: {mapping.factor_id}"
            )
        if (
            mapping.factor_status == "proposed"
            and mapping.factor_id not in proposed_by_id
        ):
            raise ValidationError(
                f"mapping references unknown proposed factor: {mapping.factor_id}"
            )
    if mapped_mechanisms != set(mechanism_by_id):
        raise ValidationError("every mechanism must have at least one factor mapping")
    for factor in bundle.proposed_factors:
        if not set(factor.source_mechanism_ids).issubset(mechanism_by_id):
            raise ValidationError("proposed factor references unknown mechanisms")

    identity_roles = tuple(item.action_role for item in bundle.performance_identities)
    if identity_roles != REQUIRED_ACTION_ROLES:
        raise ValidationError("performance identities must cover both ledgers")


def build_tool_formula_mechanism_bundle() -> ToolFormulaMechanismBundle:
    """Build the deterministic R2F formula-only authority bundle."""

    return ToolFormulaMechanismBundle(
        tool_formulas=tool_formula_specs(),
        performance_identities=performance_identity_specs(),
        mechanisms=mechanism_specs(),
        factor_mappings=factor_formula_mappings(),
        proposed_factors=proposed_factor_specs(),
    )


def formula_surface_audit_v2_reference() -> dict[str, object]:
    """Expose the V2 audit slice without altering the V1 formula bundle."""

    return {
        "schema_id": TOOL_FORMULA_SURFACE_AUDIT_V2_SCHEMA_ID,
        "migration_tool_ids": list(V2_PARAMETER_CATALOG_MIGRATION_TOOL_IDS),
        "formula_bundle_is_v1_compatible": True,
        "parameter_experiment_authority": False,
    }


__all__ = [
    "EVIDENCE_LEVELS",
    "TOOL_FORMULA_BLACKBOX_EXCLUSION",
    "TOOL_FORMULA_MECHANISM_SCHEMA_ID",
    "TOOL_FORMULA_MECHANISM_VERSION",
    "TOOL_FORMULA_SURFACE_AUDIT_V2_SCHEMA_ID",
    "FactorFormulaMapping",
    "MechanismSpec",
    "ParameterFormulaEffect",
    "PerformanceIdentitySpec",
    "ProposedFactorSpec",
    "ToolFormulaMechanismBundle",
    "ToolFormulaSpec",
    "build_tool_formula_mechanism_bundle",
    "factor_formula_mappings",
    "formula_surface_audit_v2_reference",
    "mechanism_specs",
    "performance_identity_specs",
    "proposed_factor_specs",
    "tool_formula_specs",
]
