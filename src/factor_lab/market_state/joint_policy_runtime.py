"""Causal runtime for frozen joint-policy expression trees."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite, pow
from typing import Final, cast

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.joint_policy_attempt_registry import (
    JointPolicyCandidate,
    PolicyExpression,
)

_EXPRESSION_OPERATORS: Final[frozenset[str]] = frozenset(
    {
        "atom",
        "constant",
        "previous_action",
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


def evaluate_joint_policy(
    candidate: JointPolicyCandidate,
    feature_rows: Sequence[Mapping[str, float]],
    *,
    initial_previous_action: float = 0.0,
    initial_action_history: Sequence[float] = (),
) -> tuple[float, ...]:
    """Causally evaluate a frozen expression with explicitly lagged action memory."""

    actions: list[float] = []
    if not isfinite(initial_previous_action):
        raise ValidationError("joint-policy initial previous action must be finite")
    history = [float(value) for value in initial_action_history]
    if any(not isfinite(value) for value in history):
        raise ValidationError("joint-policy initial action history must be finite")
    for row in feature_rows:
        value = evaluate_expression(
            candidate.expression,
            row=row,
            previous_action=(history[-1] if history else initial_previous_action),
            action_history=history,
            initial_previous_action=initial_previous_action,
        )
        if not isfinite(value):
            raise ValidationError("joint-policy expression produced a non-finite action")
        action = max(-1.0, min(1.0, value))
        actions.append(action)
        history.append(action)
    return tuple(actions)


def expression_inventory(expression: PolicyExpression) -> tuple[set[str], set[str]]:
    operator = str(expression.get("op", ""))
    if operator not in _EXPRESSION_OPERATORS:
        raise ValidationError(f"joint-policy expression operator is invalid: {operator}")
    atoms: set[str] = set()
    operators = {operator}
    if operator == "atom":
        atom_id = str(expression.get("id", ""))
        if not atom_id:
            raise ValidationError("joint-policy atom identity is required")
        atoms.add(atom_id)
    for child in expression_children(expression):
        child_atoms, child_operators = expression_inventory(child)
        atoms.update(child_atoms)
        operators.update(child_operators)
    return atoms, operators


def evaluate_expression(
    expression: PolicyExpression,
    *,
    row: Mapping[str, float],
    previous_action: float,
    action_history: Sequence[float] | None = None,
    initial_previous_action: float = 0.0,
) -> float:
    operator = str(expression.get("op", ""))
    if operator == "atom":
        atom_id = str(expression.get("id", ""))
        try:
            return float(row[atom_id])
        except KeyError as exc:
            raise ValidationError(f"joint-policy row is missing atom {atom_id}") from exc
    if operator == "constant":
        return finite_number(expression.get("value"), "constant")
    if operator == "previous_action":
        lag_value = expression.get("memory_bars", 1)
        if isinstance(lag_value, bool) or not isinstance(lag_value, int) or lag_value < 1:
            raise ValidationError("joint-policy previous_action memory_bars must be positive")
        if action_history is None:
            return previous_action if lag_value == 1 else initial_previous_action
        history = tuple(action_history)
        return history[-lag_value] if len(history) >= lag_value else initial_previous_action
    children = expression_children(expression)
    values = tuple(
        evaluate_expression(
            child,
            row=row,
            previous_action=previous_action,
            action_history=action_history,
            initial_previous_action=initial_previous_action,
        )
        for child in children
    )
    if operator == "add":
        _require_arity(operator, values, 2)
        return values[0] + values[1]
    if operator == "subtract":
        _require_arity(operator, values, 2)
        return values[0] - values[1]
    if operator == "multiply":
        _require_arity(operator, values, 2)
        return values[0] * values[1]
    if operator == "feature_as_coefficient":
        _require_arity(operator, values, 2)
        bounded_coefficient = 0.5 + 0.5 * max(-1.0, min(1.0, values[0]))
        return bounded_coefficient * values[1]
    if operator == "safe_divide":
        _require_arity(operator, values, 2)
        minimum = finite_number(expression.get("minimum_abs_denominator"), "minimum denominator")
        if minimum <= 0.0:
            raise ValidationError("joint-policy minimum denominator must be positive")
        return 0.0 if abs(values[1]) < minimum else values[0] / values[1]
    if operator in {"power", "feature_as_exponent"}:
        _require_arity(operator, values, 2)
        maximum = finite_number(expression.get("maximum_abs_exponent"), "maximum exponent")
        if maximum <= 0.0:
            raise ValidationError("joint-policy maximum exponent must be positive")
        if abs(values[1]) > maximum or (values[0] < 0.0 and values[1] != round(values[1])):
            raise ValidationError("joint-policy power domain is invalid")
        return pow(values[0], values[1])
    if operator in {"threshold_branch", "state_transition"}:
        _require_arity(operator, values, 3)
        threshold = finite_number(expression.get("threshold"), "branch threshold")
        return values[1] if values[0] >= threshold else values[2]
    raise ValidationError(f"joint-policy expression is not executable: {operator}")


def expression_children(expression: PolicyExpression) -> tuple[PolicyExpression, ...]:
    raw = expression.get("args", [])
    if not isinstance(raw, list):
        raise ValidationError("joint-policy expression args must be a list")
    children: list[PolicyExpression] = []
    for item in cast(list[object], raw):
        if not isinstance(item, Mapping):
            raise ValidationError("joint-policy expression child is invalid")
        children.append(cast(PolicyExpression, item))
    return tuple(children)


def finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise ValidationError(f"joint-policy {field} must be finite")
    return float(value)


def branch_nodes(expression: PolicyExpression) -> tuple[PolicyExpression, ...]:
    nodes: list[PolicyExpression] = []
    if expression.get("op") in {"threshold_branch", "state_transition"}:
        nodes.append(expression)
    for child in expression_children(expression):
        nodes.extend(branch_nodes(child))
    return tuple(nodes)


def _require_arity(operator: str, values: tuple[float, ...], expected: int) -> None:
    if len(values) != expected:
        raise ValidationError(f"joint-policy {operator} requires {expected} arguments")


__all__ = [
    "branch_nodes",
    "evaluate_expression",
    "evaluate_joint_policy",
    "expression_children",
    "expression_inventory",
    "finite_number",
]
