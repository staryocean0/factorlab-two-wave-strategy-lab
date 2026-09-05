"""Whole-family registration and multiplicity accounting for V3 research."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import prod
from typing import Final, Literal, cast

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.formula_derivation.models import (
    FormulaOperator,
    HeredityRequirement,
)
from factor_lab.market_state.formula_derivation.validation import (
    attach_semantic_digest,
    require_digest,
    require_field_labels,
    require_mapping,
    require_sequence,
    require_text,
    require_zero_authority,
    validate_semantic_digest,
)

JOINT_POLICY_FAMILY_SCHEMA_ID: Final[str] = "market_state_joint_policy_family@1.0"

FAMILY_LABELS_ZH: Final[dict[str, str]] = {
    "schema_id": "Schema标识",
    "family_id": "联合策略家族标识",
    "tool_id": "择时工具标识",
    "derivation_package_digest": "公式派生包语义摘要",
    "formula_graph_digest": "公式计算图语义摘要",
    "atom_attribute_ids": "公式原生属性原子",
    "allowed_operators": "允许的联合运算符",
    "heredity_requirement": "遗传性要求",
    "marginal_admission_required": "是否要求边际因子先晋级",
    "complexity_budget": "完整联合策略复杂度预算",
    "operator_count": "运算符轴取值数",
    "coefficient_count": "系数轴取值数",
    "exponent_count": "指数轴取值数",
    "branch_count": "分支轴取值数",
    "threshold_count": "阈值轴取值数",
    "scale_count": "尺度轴取值数",
    "state_memory_count": "状态记忆轴取值数",
    "registered_policy_attempt_count": "事前登记完整策略尝试数",
    "raw_coordinate_count": "代数规范化前原始笛卡尔坐标数",
    "algebraic_alias_collapse_count": "事前折叠的精确代数别名数",
    "multiplicity_denominator": "多重性校正分母",
    "state_topology": "冻结状态拓扑",
    "domain_guards": "定义域与数值保护",
    "search_axes": "事前冻结的具体搜索轴",
    "coefficients": "系数搜索轴",
    "exponents": "指数搜索轴",
    "branches": "条件分支搜索轴",
    "thresholds": "阈值搜索轴",
    "scales": "尺度搜索轴",
    "state_memory_bars": "状态记忆K线数搜索轴",
    "production_authority": "生产权限",
    "dynamic_parameter_authority": "动态参数权限",
    "tool_routing_authority": "工具路由权限",
    "field_labels_zh": "中文字段标签",
    "semantic_digest": "语义摘要",
}

_BUDGET_FIELDS: Final[tuple[str, ...]] = (
    "operator_count",
    "coefficient_count",
    "exponent_count",
    "branch_count",
    "threshold_count",
    "scale_count",
    "state_memory_count",
)
_JOINT_OPERATORS: Final[frozenset[str]] = frozenset(
    {
        "add",
        "subtract",
        "multiply",
        "safe_divide",
        "power",
        "feature_as_coefficient",
        "feature_as_exponent",
        "threshold_branch",
        "state_transition",
    }
)
_SEARCH_AXIS_FIELDS: Final[tuple[str, ...]] = (
    "coefficients",
    "exponents",
    "branches",
    "thresholds",
    "scales",
    "state_memory_bars",
)


def _empty_search_axes() -> dict[str, object]:
    return {}


@dataclass(frozen=True, slots=True)
class JointPolicyComplexityBudget:
    """Finite cartesian budget whose product is the attempt denominator."""

    operator_count: int
    coefficient_count: int
    exponent_count: int
    branch_count: int
    threshold_count: int
    scale_count: int
    state_memory_count: int

    def __post_init__(self) -> None:
        if any(isinstance(value, bool) or value < 1 for value in self.as_tuple()):
            raise ValidationError("joint-policy complexity counts must be positive integers")

    def as_tuple(self) -> tuple[int, ...]:
        return (
            self.operator_count,
            self.coefficient_count,
            self.exponent_count,
            self.branch_count,
            self.threshold_count,
            self.scale_count,
            self.state_memory_count,
        )

    @property
    def complete_attempt_count(self) -> int:
        return prod(self.as_tuple())

    def to_dict(self) -> dict[str, int]:
        return dict(zip(_BUDGET_FIELDS, self.as_tuple(), strict=True))

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> JointPolicyComplexityBudget:
        values: dict[str, int] = {}
        if set(payload) != set(_BUDGET_FIELDS):
            raise ValidationError("joint-policy complexity budget fields changed")
        for key in _BUDGET_FIELDS:
            value = payload.get(key)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError(f"joint-policy budget {key} must be an integer")
            values[key] = value
        return cls(**values)


@dataclass(frozen=True, slots=True)
class JointPolicyFamily:
    """One complete, bounded, pre-registered joint-policy family."""

    family_id: str
    tool_id: str
    derivation_package_digest: str
    formula_graph_digest: str
    atom_attribute_ids: tuple[str, ...]
    allowed_operators: tuple[FormulaOperator, ...]
    heredity_requirement: HeredityRequirement
    marginal_admission_required: bool
    complexity_budget: JointPolicyComplexityBudget
    registered_policy_attempt_count: int
    multiplicity_denominator: int
    state_topology: Mapping[str, object]
    domain_guards: Mapping[str, object]
    search_axes: Mapping[str, object] = field(default_factory=_empty_search_axes)
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        if not self.family_id.strip() or not self.tool_id.strip():
            raise ValidationError("joint-policy family identity is required")
        _ = require_digest(
            self.derivation_package_digest,
            field="derivation_package_digest",
        )
        _ = require_digest(self.formula_graph_digest, field="formula_graph_digest")
        if len(self.atom_attribute_ids) < 1 or len(self.atom_attribute_ids) != len(set(self.atom_attribute_ids)):
            raise ValidationError("joint-policy atoms must be non-empty and unique")
        if not self.allowed_operators or any(operator not in _JOINT_OPERATORS for operator in self.allowed_operators):
            raise ValidationError("joint-policy family operator is invalid")
        if self.heredity_requirement not in {"none", "weak", "strong"}:
            raise ValidationError("joint-policy heredity requirement is invalid")
        if self.marginal_admission_required:
            raise ValidationError("V3 joint families cannot require marginal admission")
        expected = self.complexity_budget.complete_attempt_count
        if not 1 <= self.registered_policy_attempt_count <= expected:
            raise ValidationError("registered identifiable policy count exceeds the complete raw budget")
        if self.multiplicity_denominator != self.registered_policy_attempt_count:
            raise ValidationError("multiplicity denominator cannot omit registered whole-policy attempts")
        if not self.state_topology or not self.domain_guards:
            raise ValidationError("joint-policy topology and domain guards are required")
        if not self.search_axes:
            counts = self.complexity_budget.as_tuple()[1:]
            object.__setattr__(
                self,
                "search_axes",
                {
                    field_name: (
                        [f"branch_{index + 1}" for index in range(count)]
                        if field_name == "branches"
                        else (
                            [float(index) for index in range(count)]
                            if field_name in {"coefficients", "thresholds"}
                            else [index + 1 for index in range(count)]
                        )
                    )
                    for field_name, count in zip(_SEARCH_AXIS_FIELDS, counts, strict=True)
                },
            )
        if set(self.search_axes) != set(_SEARCH_AXIS_FIELDS):
            raise ValidationError("joint-policy concrete search axes are incomplete")
        axis_values: list[tuple[object, ...]] = []
        for axis_field in _SEARCH_AXIS_FIELDS:
            raw = self.search_axes[axis_field]
            if not isinstance(raw, (list, tuple)) or not raw:
                raise ValidationError(f"joint-policy search axis {axis_field} is empty")
            values = tuple(cast(tuple[object, ...] | list[object], raw))
            if len(values) != len({repr(value) for value in values}):
                raise ValidationError(f"joint-policy search axis {axis_field} is not unique")
            axis_values.append(values)
        expected_axes = (
            len(self.allowed_operators),
            *(len(values) for values in axis_values),
        )
        if self.complexity_budget.as_tuple() != expected_axes:
            raise ValidationError("joint-policy budget does not match concrete search axes")
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("joint-policy family cannot grant authority")

    def to_dict(self) -> dict[str, object]:
        labels = dict(FAMILY_LABELS_ZH)
        for machine_key in (
            *self.state_topology,
            *self.domain_guards,
        ):
            _ = labels.setdefault(str(machine_key), f"联合策略配置字段：{machine_key}")
        return attach_semantic_digest(
            {
                "schema_id": JOINT_POLICY_FAMILY_SCHEMA_ID,
                "family_id": self.family_id,
                "tool_id": self.tool_id,
                "derivation_package_digest": self.derivation_package_digest,
                "formula_graph_digest": self.formula_graph_digest,
                "atom_attribute_ids": list(self.atom_attribute_ids),
                "allowed_operators": list(self.allowed_operators),
                "heredity_requirement": self.heredity_requirement,
                "marginal_admission_required": self.marginal_admission_required,
                "complexity_budget": self.complexity_budget.to_dict(),
                "raw_coordinate_count": self.complexity_budget.complete_attempt_count,
                "algebraic_alias_collapse_count": (
                    self.complexity_budget.complete_attempt_count
                    - self.registered_policy_attempt_count
                ),
                "registered_policy_attempt_count": self.registered_policy_attempt_count,
                "multiplicity_denominator": self.multiplicity_denominator,
                "state_topology": dict(self.state_topology),
                "domain_guards": dict(self.domain_guards),
                "search_axes": {key: list(cast(tuple[object, ...] | list[object], self.search_axes[key])) for key in _SEARCH_AXIS_FIELDS},
                "production_authority": self.production_authority,
                "dynamic_parameter_authority": self.dynamic_parameter_authority,
                "tool_routing_authority": self.tool_routing_authority,
                "field_labels_zh": labels,
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> JointPolicyFamily:
        return cls(
            family_id=require_text(payload, "family_id"),
            tool_id=require_text(payload, "tool_id"),
            derivation_package_digest=require_text(payload, "derivation_package_digest"),
            formula_graph_digest=require_text(payload, "formula_graph_digest"),
            atom_attribute_ids=tuple(str(value) for value in require_sequence(payload, "atom_attribute_ids")),
            allowed_operators=tuple(cast(FormulaOperator, str(value)) for value in require_sequence(payload, "allowed_operators")),
            heredity_requirement=cast(
                Literal["none", "weak", "strong"],
                require_text(payload, "heredity_requirement"),
            ),
            marginal_admission_required=payload.get("marginal_admission_required") is True,
            complexity_budget=JointPolicyComplexityBudget.from_dict(require_mapping(payload, "complexity_budget")),
            registered_policy_attempt_count=_integer(payload, "registered_policy_attempt_count"),
            multiplicity_denominator=_integer(payload, "multiplicity_denominator"),
            state_topology=require_mapping(payload, "state_topology"),
            domain_guards=require_mapping(payload, "domain_guards"),
            search_axes=require_mapping(payload, "search_axes"),
            production_authority=payload.get("production_authority") is True,
            dynamic_parameter_authority=payload.get("dynamic_parameter_authority") is True,
            tool_routing_authority=payload.get("tool_routing_authority") is True,
        )


class JointPolicyFamilyRegistry:
    """In-memory registry that rejects identity mutation and digest drift."""

    def __init__(self) -> None:
        self._families: dict[str, JointPolicyFamily] = {}

    def register(self, family: JointPolicyFamily) -> str:
        payload = family.to_dict()
        digest = require_digest(payload["semantic_digest"], field="family semantic_digest")
        existing = self._families.get(family.family_id)
        if existing is not None and existing.to_dict() != payload:
            raise ValidationError("joint-policy family identity cannot be mutated")
        self._families[family.family_id] = family
        return digest

    def get(self, family_id: str) -> JointPolicyFamily:
        try:
            return self._families[family_id]
        except KeyError as exc:
            raise ValidationError("joint-policy family is not registered") from exc

    @property
    def registered_policy_attempt_count(self) -> int:
        return sum(family.registered_policy_attempt_count for family in self._families.values())


def validate_joint_policy_family(payload: Mapping[str, object]) -> None:
    if payload.get("schema_id") != JOINT_POLICY_FAMILY_SCHEMA_ID:
        raise ValidationError("joint-policy family schema changed")
    require_zero_authority(payload)
    require_field_labels(payload, set(FAMILY_LABELS_ZH))
    validate_semantic_digest(payload)
    family = JointPolicyFamily.from_dict(payload)
    if family.to_dict() != dict(payload):
        raise ValidationError("joint-policy family does not round-trip canonically")


def _integer(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{key} must be an integer")
    return value


__all__ = [
    "JOINT_POLICY_FAMILY_SCHEMA_ID",
    "JointPolicyComplexityBudget",
    "JointPolicyFamily",
    "JointPolicyFamilyRegistry",
    "validate_joint_policy_family",
]
