"""Bounded empirical formulas discovered while researching timing tools.

This registry is deliberately separate from the Feature/Factor Library and from
the 13-tool parameter registry.  An empirical formula records a reproducible
relationship and its falsification boundary; it cannot authorize a factor,
dynamic parameter, tool route, or production action.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Literal, cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest

EMPIRICAL_FORMULA_REGISTRY_SCHEMA_ID: Final[str] = (
    "market_state_empirical_formula_registry@1.0"
)
EMPIRICAL_FORMULA_REGISTRY_VERSION: Final[str] = (
    "market_state_empirical_formula_registry_v1"
)
SHORT_SCALE_CROSSOVER_FORMULA_ID: Final[str] = (
    "short_scale_relative_churn_crossover_u_shape_v1"
)

FormulaStatus = Literal["bounded_empirical_formula"]

FIELD_LABELS_ZH: Final[dict[str, str]] = {
    "schema_id": "Schema标识",
    "registry_version": "注册表版本",
    "registry_id": "注册表标识",
    "entries": "经验公式条目",
    "formula_id": "经验公式标识",
    "formula_version": "经验公式版本",
    "title_zh": "中文标题",
    "status": "证据状态",
    "knowledge_kind": "知识资产类型",
    "domain": "适用领域",
    "claim_zh": "有界经验陈述",
    "accounting_identity": "逐对会计恒等式",
    "discrete_notch_test": "离散凹坑判据",
    "failure_set": "失败频段集合",
    "break_even_cost_multiplier": "盈亏平衡成本倍数",
    "mechanism_steps_zh": "机制解释",
    "applicability": "适用边界",
    "base_scale_scope": "基准频段范围",
    "target_scale_rule": "目标频段规则",
    "carrier_frequency": "承载K线频率",
    "signal_family": "信号公式家族",
    "execution_clock": "执行时钟",
    "required_comparison_protocol": "必需比较口径",
    "observed_surfaces": "已观察切片",
    "surface_id": "切片标识",
    "sample_interval": "样本区间",
    "hysteresis": "共同滞回阈值",
    "buy_cost_bps": "买入成本基点",
    "sell_cost_bps": "卖出成本基点",
    "rows": "逐目标频段结果",
    "target_span_days": "目标频段日数",
    "gross_direction_value": "毛方向价值",
    "relative_extra_cost": "相对额外成本",
    "net_value": "净相对价值",
    "interpretation_zh": "切片解释",
    "candidate_enhancement": "候选增强路由",
    "eligibility_predicate": "候选启用前提",
    "target_up_owner": "目标上涨桶责任方",
    "target_flat_or_down_owner": "目标横盘或下跌桶责任方",
    "stability_gate": "稳定性门",
    "limitations_zh": "反例与限制",
    "evidence_refs": "证据引用",
    "market_data_rows_read_by_registry": "注册表构建读取行情行数",
    "return_rows_read_by_registry": "注册表构建读取收益行数",
    "factor_registration_authority": "因子注册权限",
    "dynamic_parameter_authority": "动态参数权限",
    "tool_routing_authority": "工具路由权限",
    "production_authority": "生产权限",
    "field_labels_zh": "中文字段标签",
    "semantic_digest": "语义摘要",
}


@dataclass(frozen=True, slots=True)
class ScaleBattleObservation:
    """One same-protocol base-versus-target observation."""

    target_span_days: int
    gross_direction_value: float
    relative_extra_cost: float
    net_value: float

    def __post_init__(self) -> None:
        if self.target_span_days <= 0:
            raise ValidationError("target span must be positive")
        error = abs(
            self.gross_direction_value - self.relative_extra_cost - self.net_value
        )
        if error > 1e-6:
            raise ValidationError("scale battle accounting identity does not reconcile")

    def to_dict(self) -> dict[str, object]:
        return {
            "target_span_days": self.target_span_days,
            "gross_direction_value": self.gross_direction_value,
            "relative_extra_cost": self.relative_extra_cost,
            "net_value": self.net_value,
        }


def _short_scale_formula_entry() -> dict[str, object]:
    forward_rows = (
        ScaleBattleObservation(10, 0.092694, 0.049300, 0.043394),
        ScaleBattleObservation(15, -0.070621, 0.063500, -0.134121),
        ScaleBattleObservation(20, 0.008866, 0.067500, -0.058634),
        ScaleBattleObservation(25, 0.251170, 0.065200, 0.185970),
        ScaleBattleObservation(30, 0.331186, 0.065100, 0.266086),
    )
    return {
        "formula_id": SHORT_SCALE_CROSSOVER_FORMULA_ID,
        "formula_version": "1.0",
        "title_zh": "短周期跨尺度相对换手凹坑经验公式",
        "status": "bounded_empirical_formula",
        "knowledge_kind": "empirical_formula_not_factor_not_strategy",
        "domain": "timing.scale_routing.research",
        "claim_zh": (
            "对一个短周期基准频段b，使用完全相同的信号、滞回、执行和成本口径，"
            "逐个比较更慢目标频段t的上涨桶时，净相对价值F_b(t)有时呈现近端共享"
            "转向、局部失败、远端重新占优的离散凹坑；凹坑必须逐b实测，不能由"
            "固定周期倍数假定，也不是每个频段必然存在。"
        ),
        "accounting_identity": (
            "F_b(t,m)=G_b(t)-m*C_b(t); "
            "G_b(t)=-sum[1(T_t=up and B_b=cash)*r_next_open]; "
            "C_b(t)=cost_b_within_target_up-cost_t_within_target_up"
        ),
        "discrete_notch_test": (
            "exists t1<t2<t3: F_b(t1)>0 and F_b(t2)<=0 and F_b(t3)>0"
        ),
        "failure_set": "I_b(m)={t>b:F_b(t,m)<=0}",
        "break_even_cost_multiplier": "m_star(b,t)=G_b(t)/C_b(t), when C_b(t)>0",
        "mechanism_steps_zh": [
            "近端频段共享大量转向，必须比较相对额外成本，而不是比较各自绝对手续费。",
            "进入中间频段后，目标慢线过滤掉更多小反复，基准线仍切换，相对额外成本快速增大。",
            "再向更慢频段移动时，相对额外成本趋于饱和；若基准线规避的大回撤价值继续增大，净值重新转正。",
            "毛方向价值G也可能转负，因此凹坑既可能是换手成本型，也可能是方向关系型，不能只看手续费。",
        ],
        "applicability": {
            "base_scale_scope": "优先研究5—60日短中周期；每个基准频段独立验证",
            "target_scale_rule": "t>b，且必须包含近邻、中间和更慢目标",
            "carrier_frequency": "当前证据为15分钟K线，日数按16根/日映射",
            "signal_family": "论文原式归一化EWMA核的同族尺度信号",
            "execution_clock": "信号收线后，下一根15分钟开盘到开盘记账",
            "required_comparison_protocol": (
                "基准与目标必须使用同一滞回、同一成本、同一目标上涨桶和同一执行时钟"
            ),
        },
        "observed_surfaces": [
            {
                "surface_id": "s5_target_up_forward_h020",
                "sample_interval": "2014-01-01/2017-12-31",
                "hysteresis": 0.20,
                "buy_cost_bps": 1.0,
                "sell_cost_bps": 6.0,
                "rows": [row.to_dict() for row in forward_rows],
                "interpretation_zh": (
                    "同口径切片中S10为正、S15/S20为负、S25/S30重新为正，展示"
                    "离散凹坑；这只是机制见证，不是0.20阈值选择或跨期稳定证明。"
                ),
            },
        ],
        "candidate_enhancement": {
            "eligibility_predicate": (
                "某一(b,t)失败关系经过预注册的跨期稳定门，且失败桶可由当时信息识别"
            ),
            "target_up_owner": "target_scale",
            "target_flat_or_down_owner": "base_scale",
            "stability_gate": (
                "至少在开发、前向和成本/滞回压力面保持同方向；失败则不创建路由"
            ),
        },
        "limitations_zh": [
            "147组频段对的审计否决了任意基准频段都存在单一局部失败带的普遍命题。",
            "只有S10与S20在开发期和前向期同时满足严格的单一失败前缀定义。",
            "周期比值约2.14或2.56的低自由度公式前向准确率低于简单基线，不能用固定倍数选目标。",
            "当前S5凹坑形状会随滞回和成本移动，且0.20切片的训练期并非同形。",
            "候选增强只是研究模板；它不修改V1、V62或任何运行时默认值。",
        ],
        "evidence_refs": [
            "docs/ops/evidence/risk_off_paper_kernel_s5_higher_scale_uptrend_battle_20260802.md",
            "docs/ops/evidence/risk_off_paper_kernel_universal_scale_crossover_20260802.md",
            "scripts/research_risk_off_paper_kernel_s5_higher_scale_uptrend_battle.py",
            "scripts/research_risk_off_paper_kernel_universal_scale_crossover.py",
        ],
        "factor_registration_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
        "production_authority": False,
    }


def build_empirical_formula_registry() -> dict[str, object]:
    """Build the deterministic, machine-readable empirical-formula registry."""

    payload: dict[str, object] = {
        "schema_id": EMPIRICAL_FORMULA_REGISTRY_SCHEMA_ID,
        "registry_version": EMPIRICAL_FORMULA_REGISTRY_VERSION,
        "registry_id": "market-state-timing-empirical-formulas",
        "entries": [_short_scale_formula_entry()],
        "market_data_rows_read_by_registry": 0,
        "return_rows_read_by_registry": 0,
        "factor_registration_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
        "production_authority": False,
        "field_labels_zh": dict(FIELD_LABELS_ZH),
    }
    payload["semantic_digest"] = canonical_digest(payload)
    validate_empirical_formula_registry(payload)
    return payload


def validate_empirical_formula_registry(payload: Mapping[str, object]) -> None:
    """Fail closed on identity, authority, arithmetic, and formula boundaries."""

    if payload.get("schema_id") != EMPIRICAL_FORMULA_REGISTRY_SCHEMA_ID:
        raise ValidationError("empirical formula registry schema changed")
    if payload.get("registry_version") != EMPIRICAL_FORMULA_REGISTRY_VERSION:
        raise ValidationError("empirical formula registry version changed")
    if any(
        payload.get(field) is not False
        for field in (
            "factor_registration_authority",
            "dynamic_parameter_authority",
            "tool_routing_authority",
            "production_authority",
        )
    ):
        raise ValidationError("empirical formula registry cannot grant authority")
    if payload.get("market_data_rows_read_by_registry") != 0:
        raise ValidationError("registry construction cannot read market rows")
    if payload.get("return_rows_read_by_registry") != 0:
        raise ValidationError("registry construction cannot read return rows")
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) != 1:
        raise ValidationError("empirical formula registry entries changed")
    entry_value = cast(list[object], entries)[0]
    if not isinstance(entry_value, Mapping):
        raise ValidationError("empirical formula entry must be an object")
    entry = cast(Mapping[str, object], entry_value)
    if entry.get("formula_id") != SHORT_SCALE_CROSSOVER_FORMULA_ID:
        raise ValidationError("short-scale empirical formula is missing")
    if any(
        entry.get(field) is not False
        for field in (
            "factor_registration_authority",
            "dynamic_parameter_authority",
            "tool_routing_authority",
            "production_authority",
        )
    ):
        raise ValidationError("empirical formula entry cannot grant authority")
    surfaces = entry.get("observed_surfaces")
    if not isinstance(surfaces, list) or len(surfaces) != 1:
        raise ValidationError("empirical formula requires its observed surface")
    surface_value = cast(list[object], surfaces)[0]
    if not isinstance(surface_value, Mapping):
        raise ValidationError("observed surface must be an object")
    surface = cast(Mapping[str, object], surface_value)
    rows = surface.get("rows")
    if not isinstance(rows, list) or len(rows) != 5:
        raise ValidationError("observed surface rows changed")
    net_signs: list[bool] = []
    for row_value in cast(list[object], rows):
        if not isinstance(row_value, Mapping):
            raise ValidationError("observed row must be an object")
        row = cast(Mapping[str, object], row_value)
        observation = ScaleBattleObservation(
            target_span_days=_required_int(row, "target_span_days"),
            gross_direction_value=_required_number(row, "gross_direction_value"),
            relative_extra_cost=_required_number(row, "relative_extra_cost"),
            net_value=_required_number(row, "net_value"),
        )
        net_signs.append(observation.net_value > 0.0)
    if net_signs != [True, False, False, True, True]:
        raise ValidationError("observed short-scale notch witness changed")
    labels = payload.get("field_labels_zh")
    if not isinstance(labels, Mapping) or not all(
        isinstance(key, str)
        and isinstance(value, str)
        and key.strip()
        and value.strip()
        for key, value in cast(Mapping[object, object], labels).items()
    ):
        raise ValidationError("empirical formula Chinese labels are incomplete")
    supplied_digest = payload.get("semantic_digest")
    if not isinstance(supplied_digest, str):
        raise ValidationError("empirical formula semantic digest is missing")
    digest_payload = dict(payload)
    _ = digest_payload.pop("semantic_digest", None)
    if canonical_digest(digest_payload) != supplied_digest:
        raise ValidationError("empirical formula semantic digest is invalid")


def get_empirical_formula(formula_id: str) -> dict[str, object]:
    """Return one registered formula by exact identity."""

    registry = build_empirical_formula_registry()
    entries = registry["entries"]
    if not isinstance(entries, list):
        raise ValidationError("empirical formula registry entries are invalid")
    for entry in cast(list[object], entries):
        if isinstance(entry, dict) and entry.get("formula_id") == formula_id:
            return cast(dict[str, object], dict(entry))
    raise KeyError(formula_id)


def _required_number(payload: Mapping[str, object], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{field} must be numeric")
    return float(value)


def _required_int(payload: Mapping[str, object], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field} must be an integer")
    return value
