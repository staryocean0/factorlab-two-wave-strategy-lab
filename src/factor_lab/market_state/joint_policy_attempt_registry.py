"""Hash-bound registration of every complete policy expression in a family."""

# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from itertools import product
from math import isfinite
from typing import Final, cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.formula_derivation.validation import require_digest
from factor_lab.market_state.joint_policy_family_registry import (
    JointPolicyFamily,
    JointPolicyFamilyRegistry,
)

PolicyExpression = Mapping[str, object]

_STRUCTURAL_EXPRESSION_OPERATORS: Final[frozenset[str]] = frozenset({"atom", "constant", "previous_action"})
_BINARY_EXPRESSION_OPERATORS: Final[frozenset[str]] = frozenset(
    {"add", "subtract", "multiply", "feature_as_coefficient"}
)
ATTEMPT_LABELS_ZH: Final[dict[str, str]] = {
    "schema_id": "Schema标识",
    "family_id": "联合策略家族标识",
    "family_semantic_digest": "联合策略家族语义摘要",
    "complete_policy_attempts": "事前冻结的完整策略公式尝试",
    "registered_policy_attempt_count": "完整策略尝试数",
    "raw_coordinate_count": "代数规范化前原始坐标数",
    "algebraic_alias_collapse_count": "事前折叠的精确代数别名数",
    "multiplicity_denominator": "完整家族多重性分母",
    "search_axes": "事前冻结的具体搜索轴",
    "coefficients": "系数搜索轴",
    "exponents": "指数搜索轴",
    "branches": "条件分支搜索轴",
    "thresholds": "阈值搜索轴",
    "scales": "尺度搜索轴",
    "state_memory_bars": "状态记忆K线数搜索轴",
    "data_rows_used": "注册阶段使用市场数据行数",
    "return_label_rows_used": "注册阶段使用收益标签行数",
    "production_authority": "生产权限",
    "dynamic_parameter_authority": "动态参数权限",
    "tool_routing_authority": "工具路由权限",
    "field_labels_zh": "中文字段标签",
    "semantic_digest": "语义摘要",
    "policy_id": "完整策略标识",
    "expression": "完整策略表达式树",
    "complexity": "策略家族复杂度轴计数",
    "derived_expression_topology": "从表达式重算的拓扑",
    "coefficient_count": "系数轴取值数",
    "exponent_count": "指数轴取值数",
    "branch_count": "分支轴取值数",
    "threshold_count": "阈值轴取值数",
    "scale_count": "尺度轴取值数",
    "state_memory_count": "状态记忆轴取值数",
    "node_count": "表达式节点数",
    "maximum_depth": "表达式最大深度",
    "operator_counts": "表达式运算符计数",
    "unique_atom_ids": "表达式唯一属性原子",
    "coefficient_literal_count": "表达式常数节点数",
    "exponent_node_count": "指数节点数",
    "branch_node_count": "分支节点数",
    "threshold_literal_count": "阈值字面量数",
    "scale_atom_count": "参与尺度的唯一属性数",
    "state_memory_node_count": "状态记忆节点数",
    "state_memory_bars_used": "表达式实际使用的状态记忆K线数",
    "memory_bars": "状态动作滞后K线数",
    "op": "表达式运算符",
    "id": "表达式原子标识",
    "value": "表达式常数值",
    "minimum_abs_denominator": "最小绝对分母",
    "maximum_abs_exponent": "最大绝对指数",
    "threshold": "条件阈值",
    "args": "表达式子节点",
}


@dataclass(frozen=True, slots=True)
class JointPolicyCandidate:
    """One fully specified policy attempt within a pre-registered family."""

    policy_id: str
    family_id: str
    expression: PolicyExpression
    coefficient_count: int
    exponent_count: int
    branch_count: int
    threshold_count: int
    scale_count: int
    state_memory_count: int

    def __post_init__(self) -> None:
        if not self.policy_id.strip() or not self.family_id.strip() or not self.expression:
            raise ValidationError("joint-policy candidate identity/expression is required")
        if (
            min(
                self.coefficient_count,
                self.exponent_count,
                self.branch_count,
                self.threshold_count,
                self.scale_count,
                self.state_memory_count,
            )
            < 1
        ):
            raise ValidationError("joint-policy candidate complexity counts must be positive")
        validate_policy_expression(self.expression)

    @property
    def semantic_digest(self) -> str:
        return canonical_digest(self.to_dict())

    @property
    def derived_expression_topology(self) -> dict[str, object]:
        """Recompute structural complexity from the expression tree itself."""

        return _derive_expression_topology(self.expression)

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "family_id": self.family_id,
            "expression": dict(self.expression),
            "complexity": {
                "coefficient_count": self.coefficient_count,
                "exponent_count": self.exponent_count,
                "branch_count": self.branch_count,
                "threshold_count": self.threshold_count,
                "scale_count": self.scale_count,
                "state_memory_count": self.state_memory_count,
            },
            "derived_expression_topology": self.derived_expression_topology,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> JointPolicyCandidate:
        allowed_keys = {"policy_id", "family_id", "expression", "complexity"}
        if set(payload) not in (allowed_keys, allowed_keys | {"derived_expression_topology"}):
            raise ValidationError("joint-policy candidate fields changed")
        complexity = payload.get("complexity")
        expression = payload.get("expression")
        if not isinstance(complexity, Mapping) or not isinstance(expression, Mapping):
            raise ValidationError("joint-policy candidate payload is incomplete")
        typed_complexity = cast(Mapping[str, object], complexity)
        if set(typed_complexity) != {
            "coefficient_count", "exponent_count", "branch_count",
            "threshold_count", "scale_count", "state_memory_count",
        }:
            raise ValidationError("joint-policy candidate complexity fields changed")
        candidate = cls(
            policy_id=_required_text(payload, "policy_id"),
            family_id=_required_text(payload, "family_id"),
            expression=cast(PolicyExpression, expression),
            coefficient_count=_required_count(typed_complexity, "coefficient_count"),
            exponent_count=_required_count(typed_complexity, "exponent_count"),
            branch_count=_required_count(typed_complexity, "branch_count"),
            threshold_count=_required_count(typed_complexity, "threshold_count"),
            scale_count=_required_count(typed_complexity, "scale_count"),
            state_memory_count=_required_count(typed_complexity, "state_memory_count"),
        )
        supplied = payload.get("derived_expression_topology")
        if supplied is not None and supplied != candidate.derived_expression_topology:
            raise ValidationError("joint-policy derived expression topology drifted")
        return candidate


def validate_policy_expression(expression: PolicyExpression) -> None:
    """Fail closed on every recursive expression key, arity, and literal domain."""

    operator = expression.get("op")
    if not isinstance(operator, str):
        raise ValidationError("joint-policy expression operator is missing")
    if operator == "atom":
        if set(expression) != {"op", "id"} or not isinstance(expression.get("id"), str) or not str(expression["id"]).strip():
            raise ValidationError("joint-policy atom shape is invalid")
        return
    if operator == "constant":
        if set(expression) != {"op", "value"}:
            raise ValidationError("joint-policy constant shape is invalid")
        _ = _finite_expression_number(expression.get("value"), "constant")
        return
    if operator == "previous_action":
        if set(expression) not in ({"op"}, {"op", "memory_bars"}):
            raise ValidationError("joint-policy previous_action shape is invalid")
        memory = expression.get("memory_bars", 1)
        if isinstance(memory, bool) or not isinstance(memory, int) or memory < 1:
            raise ValidationError("joint-policy previous_action memory is invalid")
        return
    expected_keys = {"op", "args"}
    expected_arity = 2
    if operator == "safe_divide":
        expected_keys.add("minimum_abs_denominator")
        if _finite_expression_number(expression.get("minimum_abs_denominator"), "minimum denominator") <= 0.0:
            raise ValidationError("joint-policy minimum denominator must be positive")
    elif operator in {"power", "feature_as_exponent"}:
        expected_keys.add("maximum_abs_exponent")
        if _finite_expression_number(expression.get("maximum_abs_exponent"), "maximum exponent") <= 0.0:
            raise ValidationError("joint-policy maximum exponent must be positive")
    elif operator in {"threshold_branch", "state_transition"}:
        expected_keys.add("threshold")
        expected_arity = 3
        _ = _finite_expression_number(expression.get("threshold"), "threshold")
    elif operator not in _BINARY_EXPRESSION_OPERATORS:
        raise ValidationError(f"joint-policy expression operator is invalid: {operator}")
    if set(expression) != expected_keys:
        raise ValidationError(f"joint-policy expression {operator} fields changed")
    children = expression.get("args")
    if not isinstance(children, list) or len(children) != expected_arity:
        raise ValidationError(f"joint-policy expression {operator} arity is invalid")
    for child in cast(list[object], children):
        if not isinstance(child, Mapping):
            raise ValidationError("joint-policy expression child is invalid")
        validate_policy_expression(cast(PolicyExpression, child))


def _finite_expression_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise ValidationError(f"joint-policy expression {field} must be finite")
    return float(value)


class JointPolicyAttemptRegistry:
    """Bind the complete candidate manifest before any market labels are evaluated."""

    def __init__(self, family_registry: JointPolicyFamilyRegistry) -> None:
        self._family_registry: JointPolicyFamilyRegistry = family_registry
        self._attempt_sets: dict[str, dict[str, object]] = {}

    def register(
        self,
        family: JointPolicyFamily,
        candidates: Sequence[JointPolicyCandidate],
    ) -> str:
        registered_family = self._family_registry.get(family.family_id)
        if registered_family.to_dict() != family.to_dict():
            raise ValidationError("joint-policy family registry content drifted")
        _validate_candidate_manifest(family, candidates)
        _require_exact_registered_family_topology(family, candidates)
        manifest = _candidate_manifest(family, candidates)
        digest = require_digest(manifest["semantic_digest"], field="attempt-set digest")
        existing = self._attempt_sets.get(family.family_id)
        if existing is not None and existing != manifest:
            raise ValidationError("registered joint-policy attempt set cannot be mutated")
        self._attempt_sets[family.family_id] = manifest
        return digest

    def require_registered(
        self,
        family: JointPolicyFamily,
        candidates: Sequence[JointPolicyCandidate],
    ) -> str:
        manifest = _candidate_manifest(family, candidates)
        if self._attempt_sets.get(family.family_id) != manifest:
            raise ValidationError("complete joint-policy attempt set was not pre-registered")
        return require_digest(manifest["semantic_digest"], field="joint-policy attempt-set digest")

    def manifest(self, family_id: str) -> dict[str, object]:
        try:
            return deepcopy(self._attempt_sets[family_id])
        except KeyError as exc:
            raise ValidationError("joint-policy attempt set is not registered") from exc


def enumerate_registered_policy_candidates(
    family: JointPolicyFamily,
) -> tuple[JointPolicyCandidate, ...]:
    """Instantiate the frozen axes and collapse exact algebraic aliases pre-data."""

    candidates = _identifiable_candidates(_raw_policy_candidates(family))
    _validate_candidate_manifest(family, candidates)
    return candidates


def identifiable_policy_attempt_count(family: JointPolicyFamily) -> int:
    """Count canonical hypotheses without reading market rows or labels."""

    return len(_identifiable_candidates(_raw_policy_candidates(family)))


def canonical_policy_expression_fingerprint(expression: PolicyExpression) -> str:
    """Fingerprint exact policy algebra independently of coordinate spelling."""

    return canonical_digest({"canonical_policy_expression": _canonical_policy_expression(expression)})


def _identifiable_candidates(
    candidates: Sequence[JointPolicyCandidate],
) -> tuple[JointPolicyCandidate, ...]:
    unique: dict[str, JointPolicyCandidate] = {}
    for candidate in candidates:
        fingerprint = canonical_policy_expression_fingerprint(candidate.expression)
        _ = unique.setdefault(fingerprint, candidate)
    return tuple(unique.values())


def _raw_policy_candidates(
    family: JointPolicyFamily,
) -> tuple[JointPolicyCandidate, ...]:

    axes = family.search_axes
    coefficients = tuple(float(str(value)) for value in cast(Sequence[object], axes["coefficients"]))
    exponents = tuple(int(str(value)) for value in cast(Sequence[object], axes["exponents"]))
    branches = tuple(str(value) for value in cast(Sequence[object], axes["branches"]))
    thresholds = tuple(float(str(value)) for value in cast(Sequence[object], axes["thresholds"]))
    scales = tuple(int(str(value)) for value in cast(Sequence[object], axes["scales"]))
    memories = tuple(int(str(value)) for value in cast(Sequence[object], axes["state_memory_bars"]))
    candidates: list[JointPolicyCandidate] = []
    coordinates = product(
        enumerate(family.allowed_operators),
        enumerate(coefficients),
        enumerate(exponents),
        enumerate(branches),
        enumerate(thresholds),
        enumerate(scales),
        enumerate(memories),
    )
    for sequence, coordinate in enumerate(coordinates, start=1):
        indexed = tuple(item[0] for item in coordinate)
        values = tuple(item[1] for item in coordinate)
        operator, coefficient, exponent, branch, threshold, scale, memory = values
        expression = _candidate_expression(
            family=family,
            operator=str(operator),
            coefficient=float(coefficient),
            exponent=int(str(exponent)),
            branch=str(branch),
            threshold=float(threshold),
            scale=float(scale),
            state_memory_bars=int(memory),
        )
        coordinate_id = "-".join(f"{value + 1:02d}" for value in indexed)
        budget = family.complexity_budget
        candidates.append(
            JointPolicyCandidate(
                policy_id=f"policy:{family.tool_id}:{sequence:04d}:{coordinate_id}",
                family_id=family.family_id,
                expression=expression,
                coefficient_count=budget.coefficient_count,
                exponent_count=budget.exponent_count,
                branch_count=budget.branch_count,
                threshold_count=budget.threshold_count,
                scale_count=budget.scale_count,
                state_memory_count=budget.state_memory_count,
            )
        )
    return tuple(candidates)


def _canonical_policy_expression(expression: PolicyExpression) -> object:
    operator = str(expression.get("op", ""))
    if operator == "constant":
        raw_value = expression.get("value")
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            raise ValidationError("joint-policy canonical constant is invalid")
        value = float(raw_value)
        if not isfinite(value):
            raise ValidationError("joint-policy canonical constant is invalid")
        return {"op": "constant", "value": 0.0 if value == 0.0 else value}
    if operator == "atom":
        return {"op": "atom", "id": str(expression.get("id", ""))}
    if operator == "previous_action":
        return {"op": "previous_action", "memory_bars": int(str(expression.get("memory_bars", 1)))}
    children = [_canonical_policy_expression(child) for child in _expression_children(expression)]
    if operator == "multiply":
        flattened: list[object] = []
        constant_product = 1.0
        for child in children:
            if isinstance(child, Mapping) and child.get("op") == "multiply":
                flattened.extend(cast(list[object], child["args"]))
            elif isinstance(child, Mapping) and child.get("op") == "constant":
                constant_product *= float(str(child["value"]))
            else:
                flattened.append(child)
        if constant_product == 0.0:
            return {"op": "constant", "value": 0.0}
        if constant_product != 1.0 or not flattened:
            flattened.append({"op": "constant", "value": constant_product})
        flattened.sort(key=lambda value: canonical_digest({"term": value}))
        if len(flattened) == 1:
            return flattened[0]
        return {"op": "multiply", "args": flattened}
    if operator in {"threshold_branch", "state_transition"}:
        threshold = float(str(expression.get("threshold", 0.0)))
        if threshold == 0.0 and children:
            children[0] = _canonical_zero_threshold_predicate(children[0])
    normalized: dict[str, object] = {"op": operator, "args": children}
    for field in ("threshold", "minimum_abs_denominator", "maximum_abs_exponent"):
        if field in expression:
            normalized[field] = float(str(expression[field]))
    return normalized


def _canonical_zero_threshold_predicate(expression: object) -> object:
    """Collapse only exact positive scaling under a zero-threshold predicate."""

    if not isinstance(expression, Mapping) or expression.get("op") != "multiply":
        return expression
    terms = list(cast(Sequence[object], expression.get("args", [])))
    sign = 1.0
    non_constants: list[object] = []
    for term in terms:
        if isinstance(term, Mapping) and term.get("op") == "constant":
            value = float(str(term.get("value")))
            if value == 0.0:
                return {"op": "constant", "value": 0.0}
            sign *= -1.0 if value < 0.0 else 1.0
        else:
            non_constants.append(term)
    if sign < 0.0 or not non_constants:
        non_constants.append({"op": "constant", "value": sign})
    non_constants.sort(key=lambda value: canonical_digest({"term": value}))
    if len(non_constants) == 1:
        return non_constants[0]
    return {"op": "multiply", "args": non_constants}


def _expression_children(expression: PolicyExpression) -> tuple[PolicyExpression, ...]:
    raw = expression.get("args", [])
    if not isinstance(raw, list) or any(not isinstance(child, Mapping) for child in raw):
        raise ValidationError("joint-policy canonical expression children are invalid")
    return tuple(cast(PolicyExpression, child) for child in cast(list[object], raw))


def _validate_candidate_manifest(
    family: JointPolicyFamily,
    candidates: Sequence[JointPolicyCandidate],
) -> None:
    if len(candidates) != family.registered_policy_attempt_count:
        raise ValidationError("every registered whole-policy attempt must be instantiated")
    if len({candidate.policy_id for candidate in candidates}) != len(candidates):
        raise ValidationError("joint-policy candidate identities must be unique")
    budget = family.complexity_budget
    for candidate in candidates:
        if candidate.family_id != family.family_id:
            raise ValidationError("joint-policy candidate belongs to another family")
        if (
            candidate.coefficient_count != budget.coefficient_count
            or candidate.exponent_count != budget.exponent_count
            or candidate.branch_count != budget.branch_count
            or candidate.threshold_count != budget.threshold_count
            or candidate.scale_count != budget.scale_count
            or candidate.state_memory_count != budget.state_memory_count
        ):
            raise ValidationError("joint-policy candidate does not carry the registered family budget")
        topology = candidate.derived_expression_topology
        atom_ids = set(cast(Sequence[str], topology["unique_atom_ids"]))
        if not atom_ids.issubset(family.atom_attribute_ids):
            raise ValidationError("joint-policy expression uses an atom outside the registered family")
        operator_counts = cast(Mapping[str, object], topology["operator_counts"])
        expression_operators = set(operator_counts) - _STRUCTURAL_EXPRESSION_OPERATORS
        if not expression_operators.issubset(family.allowed_operators):
            raise ValidationError("joint-policy expression uses an operator outside the registered family")
        if (
            int(str(topology["node_count"])) > 64
            or int(str(topology["maximum_depth"])) > 12
            or int(str(topology["branch_node_count"])) > budget.branch_count
            or int(str(topology["threshold_literal_count"])) > budget.threshold_count
            or int(str(topology["state_memory_node_count"])) > budget.state_memory_count
        ):
            raise ValidationError("joint-policy expression exceeds derived topology bounds")


def _candidate_manifest(
    family: JointPolicyFamily,
    candidates: Sequence[JointPolicyCandidate],
) -> dict[str, object]:
    candidate_payloads = [candidate.to_dict() for candidate in sorted(candidates, key=lambda item: item.policy_id)]
    labels = dict(ATTEMPT_LABELS_ZH)
    for candidate_payload in candidate_payloads:
        for machine_key in _recursive_mapping_keys(candidate_payload):
            _ = labels.setdefault(machine_key, f"完整策略表达式字段：{machine_key}")
    payload: dict[str, object] = {
        "schema_id": "market_state_joint_policy_attempt_manifest@1.0",
        "family_id": family.family_id,
        "family_semantic_digest": family.to_dict()["semantic_digest"],
        "complete_policy_attempts": candidate_payloads,
        "raw_coordinate_count": family.complexity_budget.complete_attempt_count,
        "algebraic_alias_collapse_count": (family.complexity_budget.complete_attempt_count - len(candidates)),
        "registered_policy_attempt_count": len(candidates),
        "multiplicity_denominator": family.multiplicity_denominator,
        "search_axes": {key: list(cast(Sequence[object], value)) for key, value in sorted(family.search_axes.items())},
        "data_rows_used": 0,
        "return_label_rows_used": 0,
        "production_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
        "field_labels_zh": labels,
    }
    payload["semantic_digest"] = canonical_digest(payload)
    return payload


def _recursive_mapping_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        typed_value = cast(Mapping[object, object], value)
        keys.update(str(key) for key in typed_value)
        for nested in typed_value.values():
            keys.update(_recursive_mapping_keys(nested))
    elif isinstance(value, list):
        for nested in cast(list[object], value):
            keys.update(_recursive_mapping_keys(nested))
    return keys


def validate_joint_policy_attempt_manifest(
    payload: Mapping[str, object],
    *,
    family: JointPolicyFamily,
) -> None:
    """Recompute every frozen expression and reject post-Stage1 axis drift."""

    if payload.get("schema_id") != "market_state_joint_policy_attempt_manifest@1.0":
        raise ValidationError("joint-policy attempt manifest schema changed")
    raw = payload.get("complete_policy_attempts")
    if not isinstance(raw, list):
        raise ValidationError("joint-policy attempt manifest rows are missing")
    candidates = tuple(
        JointPolicyCandidate.from_dict(cast(Mapping[str, object], row)) for row in cast(list[object], raw) if isinstance(row, Mapping)
    )
    typed_raw = cast(list[object], raw)
    if len(candidates) != len(typed_raw):
        raise ValidationError("joint-policy attempt manifest contains an invalid row")
    _validate_candidate_manifest(family, candidates)
    _require_exact_registered_family_topology(family, candidates)
    if _candidate_manifest(family, candidates) != dict(payload):
        raise ValidationError("joint-policy attempt manifest is not reproducible")


def require_candidate_in_registered_attempt_manifest(
    *,
    payload: Mapping[str, object],
    family: JointPolicyFamily,
    candidate: JointPolicyCandidate,
    expected_attempt_set_digest: str,
) -> None:
    """Prove a frozen Stage-3 candidate was present in the zero-data attempt set."""

    validate_joint_policy_attempt_manifest(payload, family=family)
    manifest_digest = require_digest(payload.get("semantic_digest"), field="attempt manifest semantic_digest")
    if manifest_digest != expected_attempt_set_digest:
        raise ValidationError("frozen candidate attempt-set digest does not match Stage 1")
    if candidate.family_id != family.family_id:
        raise ValidationError("frozen candidate belongs to another registered family")
    raw_attempts = cast(list[object], payload["complete_policy_attempts"])
    matches: list[Mapping[str, object]] = []
    for row in raw_attempts:
        if not isinstance(row, Mapping):
            continue
        typed_row = cast(Mapping[str, object], row)
        if typed_row.get("policy_id") == candidate.policy_id and dict(typed_row) == candidate.to_dict():
            matches.append(typed_row)
    if len(matches) != 1:
        raise ValidationError("frozen candidate was not present in the registered Stage-1 attempt set")


def _require_exact_registered_family_topology(
    family: JointPolicyFamily,
    candidates: Sequence[JointPolicyCandidate],
) -> None:
    """For real tools, bind every expression to the frozen Cartesian axes."""

    if family.tool_id.startswith("synthetic_"):
        return
    expected = enumerate_registered_policy_candidates(family)
    supplied_payloads = [candidate.to_dict() for candidate in sorted(candidates, key=lambda item: item.policy_id)]
    expected_payloads = [candidate.to_dict() for candidate in sorted(expected, key=lambda item: item.policy_id)]
    if supplied_payloads != expected_payloads:
        raise ValidationError("joint-policy attempts do not exactly instantiate the registered search axes")


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"joint-policy candidate requires {key}")
    return value


def _required_count(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValidationError(f"joint-policy candidate requires positive {key}")
    return value


def _derive_expression_topology(expression: PolicyExpression) -> dict[str, object]:
    operators: dict[str, int] = {}
    atoms: set[str] = set()
    constant_count = 0
    branch_count = 0
    threshold_count = 0
    exponent_count = 0
    state_memory_count = 0
    state_memory_bars_used: set[int] = set()
    node_count = 0
    maximum_depth = 0

    def visit(node: PolicyExpression, depth: int) -> None:
        nonlocal constant_count, branch_count, threshold_count
        nonlocal exponent_count, state_memory_count, node_count, maximum_depth
        operator = str(node.get("op", ""))
        if not operator:
            raise ValidationError("joint-policy expression operator is required")
        operators[operator] = operators.get(operator, 0) + 1
        node_count += 1
        maximum_depth = max(maximum_depth, depth)
        if operator == "atom":
            atom_id = str(node.get("id", ""))
            if not atom_id:
                raise ValidationError("joint-policy expression atom is unnamed")
            atoms.add(atom_id)
        if operator == "constant":
            constant_count += 1
        if operator in {"threshold_branch", "state_transition"}:
            branch_count += 1
            if "threshold" in node:
                threshold_count += 1
        if operator in {"power", "feature_as_exponent"}:
            exponent_count += 1
        if operator == "previous_action":
            state_memory_count += 1
            memory_bars = node.get("memory_bars", 1)
            if isinstance(memory_bars, bool) or not isinstance(memory_bars, int) or memory_bars < 1:
                raise ValidationError("joint-policy previous_action memory_bars must be positive")
            state_memory_bars_used.add(memory_bars)
        raw_children: object = node.get("args", [])
        if not isinstance(raw_children, list):
            raise ValidationError("joint-policy expression args must be a list")
        for child in cast(list[object], raw_children):
            if not isinstance(child, Mapping):
                raise ValidationError("joint-policy expression child is invalid")
            visit(cast(PolicyExpression, child), depth + 1)

    visit(expression, 1)
    return {
        "node_count": node_count,
        "maximum_depth": maximum_depth,
        "operator_counts": dict(sorted(operators.items())),
        "unique_atom_ids": sorted(atoms),
        "coefficient_literal_count": constant_count,
        "exponent_node_count": exponent_count,
        "branch_node_count": branch_count,
        "threshold_literal_count": threshold_count,
        "scale_atom_count": len(atoms),
        "state_memory_node_count": state_memory_count,
        "state_memory_bars_used": sorted(state_memory_bars_used),
    }


def _candidate_expression(
    *,
    family: JointPolicyFamily,
    operator: str,
    coefficient: float,
    exponent: int,
    branch: str,
    threshold: float,
    scale: float,
    state_memory_bars: int,
) -> PolicyExpression:
    atom_ids = family.atom_attribute_ids
    if branch not in {"enter_hold", "exit_hold"}:
        raise ValidationError("registered joint branch axis is invalid")
    if scale == 0.0 or state_memory_bars < 1:
        raise ValidationError("registered joint scale/memory axes are invalid")
    pairs = ((0, 1), (1, 0)) if len(atom_ids) == 2 else ((0, 1), (0, 2))
    pair_index = 0 if scale < 0.0 else 1
    left_index, right_index = pairs[pair_index]
    left = _scaled_power(_atom(atom_ids[left_index]), coefficient, exponent)
    right = _scaled_power(_atom(atom_ids[right_index]), 1.0, 4 - exponent)
    negative_right = _multiply(_constant(-1.0), right)
    if operator in {"multiply", "feature_as_coefficient"}:
        combined: PolicyExpression = {"op": operator, "args": [left, right]}
    elif operator == "safe_divide":
        combined = {
            "op": "safe_divide",
            "args": [left, right],
            "minimum_abs_denominator": 1e-12,
        }
    elif operator == "power":
        combined = {
            "op": "power",
            "args": [
                _multiply(left, left),
                {
                    "op": "threshold_branch",
                    "args": [right, _constant(float(exponent)), _constant(1.0)],
                    "threshold": threshold,
                },
            ],
            "maximum_abs_exponent": 3.0,
        }
    elif operator == "threshold_branch":
        combined = {
            "op": "threshold_branch",
            "args": [left, right, negative_right],
            "threshold": threshold,
        }
    elif operator == "state_transition":
        combined = {
            "op": "state_transition",
            "args": [left, right, {"op": "previous_action"}],
            "threshold": threshold,
        }
    else:
        raise ValidationError(f"unsupported registered joint operator: {operator}")
    scaled_combined = _multiply(_constant(scale), combined)
    memory: PolicyExpression = {"op": "previous_action", "memory_bars": state_memory_bars}
    true_leaf = _constant(1.0) if branch == "enter_hold" else memory
    false_leaf = memory if branch == "enter_hold" else _constant(-1.0)
    return {
        "op": "state_transition",
        "args": [scaled_combined, true_leaf, false_leaf],
        "threshold": threshold,
    }


def _scaled_power(
    atom: PolicyExpression,
    coefficient: float,
    exponent: int,
) -> PolicyExpression:
    powered = atom
    for _ in range(1, exponent):
        powered = _multiply(powered, atom)
    return _multiply(_constant(coefficient), powered)


def _atom(atom_id: str) -> PolicyExpression:
    return {"op": "atom", "id": atom_id}


def _constant(value: float) -> PolicyExpression:
    return {"op": "constant", "value": value}


def _multiply(left: PolicyExpression, right: PolicyExpression) -> PolicyExpression:
    return {"op": "multiply", "args": [left, right]}


__all__ = [
    "JointPolicyAttemptRegistry",
    "JointPolicyCandidate",
    "PolicyExpression",
    "enumerate_registered_policy_candidates",
    "require_candidate_in_registered_attempt_manifest",
    "validate_policy_expression",
    "validate_joint_policy_attempt_manifest",
]
