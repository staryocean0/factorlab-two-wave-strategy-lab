"""Deterministic compiler and executor for frozen formula-program adapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isclose, isfinite
from math import pow as math_pow
from typing import Final

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.formula_derivation.models import (
    FormulaComputationGraph,
    FormulaNode,
)
from factor_lab.market_state.tool_formula_mechanisms import ToolFormulaSpec

Scalar = float | bool

SOURCE_PANEL_EXECUTOR_REF: Final[str] = (
    "factor_lab.market_state.formula_derivation.materialization:"
    "execute_source_formula_graph_panel"
)

_BINARY_OPERATORS: Final[frozenset[str]] = frozenset(
    {
        "add",
        "subtract",
        "multiply",
        "safe_divide",
        "power",
        "feature_as_coefficient",
        "feature_as_exponent",
    }
)


@dataclass(frozen=True, slots=True)
class FormulaProgramSpec:
    """A source-backed adapter from a frozen formula surface into graph IR."""

    program_id: str
    tool_id: str
    tool_version: str
    formula_id: str
    nodes: tuple[FormulaNode, ...]
    output_node_ids: tuple[str, ...]
    parameter_units: Mapping[str, str]

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (
                self.program_id,
                self.tool_id,
                self.tool_version,
                self.formula_id,
            )
        ):
            raise ValidationError("formula program identity is required")
        if not self.nodes or not self.output_node_ids:
            raise ValidationError("formula program needs nodes and outputs")
        if any(not key.strip() or not value.strip() for key, value in self.parameter_units.items()):
            raise ValidationError("formula program parameter units are incomplete")


def compile_formula_program(
    source_formula: ToolFormulaSpec,
    program: FormulaProgramSpec,
) -> FormulaComputationGraph:
    """Compile one explicit adapter after source, parameter, unit, and guard checks."""

    if program.tool_id != source_formula.tool_id or program.formula_id != source_formula.formula_id:
        raise ValidationError("formula program does not match its frozen ToolFormulaSpec")
    source_parameters = {effect.parameter_id for effect in source_formula.parameter_effects}
    referenced_parameters = {parameter_id for node in program.nodes for parameter_id in node.parameter_refs}
    if not referenced_parameters.issubset(source_parameters):
        raise ValidationError("formula program references an unregistered source parameter")
    if not referenced_parameters.issubset(program.parameter_units):
        raise ValidationError("formula program lacks parameter-unit declarations")
    for node in program.nodes:
        _validate_arity_and_guards(node)
        witness = node.source_witness
        if witness.get("formula_id") != source_formula.formula_id:
            raise ValidationError("formula node source witness changed formula identity")
        if witness.get("implementation_ref") != source_formula.implementation_ref:
            raise ValidationError("formula node source witness changed implementation reference")
    _validate_units(program.nodes, parameter_units=program.parameter_units)
    return FormulaComputationGraph(
        graph_id=program.program_id,
        tool_id=program.tool_id,
        tool_version=program.tool_version,
        nodes=program.nodes,
        output_node_ids=program.output_node_ids,
        raw_kline_input_fields=("timestamp", "open", "high", "low", "close"),
        source_formula_contract=source_formula.to_dict(),
        source_materializer_ref=SOURCE_PANEL_EXECUTOR_REF,
        decision_output_id="target_position",
        execution_lag_bars=1,
        cost_parameter_id="cost_bps",
    )


def execute_formula_graph(
    graph: FormulaComputationGraph,
    *,
    kline_fields: Mapping[str, Scalar],
    parameters: Mapping[str, Scalar],
) -> dict[str, Scalar]:
    """Execute one scalar graph; source-backed panel nodes use the panel executor."""

    values: dict[str, Scalar] = {}
    for node in graph.nodes:
        inputs = tuple(values[node_id] for node_id in node.input_node_ids)
        value = _evaluate_node(
            node,
            inputs=inputs,
            kline_fields=kline_fields,
            parameters=parameters,
        )
        if isinstance(value, float) and not isfinite(value):
            raise ValidationError(f"formula node {node.node_id} produced a non-finite value")
        values[node.node_id] = value
    return {node_id: values[node_id] for node_id in graph.output_node_ids}


def _evaluate_node(
    node: FormulaNode,
    *,
    inputs: tuple[Scalar, ...],
    kline_fields: Mapping[str, Scalar],
    parameters: Mapping[str, Scalar],
) -> Scalar:
    if node.operator == "input":
        field = node.kline_field_refs[0]
        try:
            return kline_fields[field]
        except KeyError as exc:
            raise ValidationError(f"missing synthetic K-line field: {field}") from exc
    if node.operator == "constant":
        parameter_id = node.parameter_refs[0]
        try:
            return parameters[parameter_id]
        except KeyError as exc:
            raise ValidationError(f"missing formula parameter: {parameter_id}") from exc
    if node.operator == "add":
        return _number(inputs[0]) + _number(inputs[1])
    if node.operator == "subtract":
        return _number(inputs[0]) - _number(inputs[1])
    if node.operator == "multiply":
        return _number(inputs[0]) * _number(inputs[1])
    if node.operator == "feature_as_coefficient":
        coefficient = 0.5 + 0.5 * max(-1.0, min(1.0, _number(inputs[0])))
        return coefficient * _number(inputs[1])
    if node.operator == "safe_divide":
        numerator, denominator = (_number(value) for value in inputs)
        minimum = _guard_number(node, "minimum_abs_denominator")
        if abs(denominator) < minimum:
            policy = node.domain_guard.get("zero_denominator_policy")
            if policy == "return_zero":
                return 0.0
            raise ValidationError(f"formula node {node.node_id} hit a protected denominator")
        return numerator / denominator
    if node.operator in {"power", "feature_as_exponent"}:
        base, exponent = (_number(value) for value in inputs)
        maximum_exponent = _guard_number(node, "maximum_abs_exponent")
        if abs(exponent) > maximum_exponent:
            raise ValidationError(f"formula node {node.node_id} exponent exceeds its guard")
        if base < 0.0 and not isclose(exponent, round(exponent), abs_tol=1e-12):
            raise ValidationError(f"formula node {node.node_id} power domain is undefined")
        if base == 0.0 and exponent < 0.0:
            raise ValidationError(f"formula node {node.node_id} power domain is undefined")
        return math_pow(base, exponent)
    if node.operator in {"threshold_branch", "state_transition"}:
        threshold = _guard_number(node, "threshold")
        return inputs[1] if _number(inputs[0]) >= threshold else inputs[2]
    if node.operator in {
        "source_attribute",
        "source_target_position",
        "execution_lag",
        "transaction_cost",
    }:
        raise ValidationError(f"formula node {node.node_id} requires execute_source_formula_graph_panel")
    raise ValidationError(f"formula operator is not executable: {node.operator}")


def _validate_arity_and_guards(node: FormulaNode) -> None:
    if node.operator == "input":
        if len(node.kline_field_refs) != 1 or node.input_node_ids or node.parameter_refs:
            raise ValidationError("input node must reference exactly one K-line field")
        return
    if node.operator == "constant":
        if len(node.parameter_refs) != 1 or node.input_node_ids or node.kline_field_refs:
            raise ValidationError("constant node must reference exactly one parameter")
        return
    if node.operator in {"source_attribute", "source_target_position"}:
        if len(node.input_node_ids) != 5 or node.kline_field_refs or node.parameter_refs:
            raise ValidationError(f"{node.operator} must consume the five raw K-line nodes")
        return
    if node.operator == "execution_lag":
        if len(node.input_node_ids) != 1 or node.kline_field_refs or node.parameter_refs:
            raise ValidationError("execution_lag must consume target_position")
        if node.domain_guard.get("lag_bars") != 1:
            raise ValidationError("execution_lag must freeze one next-bar lag")
        return
    if node.operator == "transaction_cost":
        if len(node.input_node_ids) != 3 or node.kline_field_refs or node.parameter_refs:
            raise ValidationError("transaction_cost must consume decision, position, and cost")
        return
    if node.operator in _BINARY_OPERATORS and len(node.input_node_ids) != 2:
        raise ValidationError(f"{node.operator} node requires exactly two inputs")
    if node.operator in {"threshold_branch", "state_transition"} and len(node.input_node_ids) != 3:
        raise ValidationError(f"{node.operator} node requires condition/true/false inputs")
    if node.kline_field_refs or node.parameter_refs:
        raise ValidationError("operation nodes must consume graph inputs, not hidden direct references")
    if node.operator == "safe_divide":
        _ = _guard_number(node, "minimum_abs_denominator")
        if node.domain_guard.get("zero_denominator_policy") not in {"fail_closed", "return_zero"}:
            raise ValidationError("safe_divide zero-denominator policy is invalid")
    if node.operator in {"power", "feature_as_exponent"}:
        _ = _guard_number(node, "maximum_abs_exponent")
    if node.operator in {"threshold_branch", "state_transition"}:
        _ = _guard_number(node, "threshold")


def _validate_units(
    nodes: tuple[FormulaNode, ...],
    *,
    parameter_units: Mapping[str, str],
) -> None:
    units: dict[str, str] = {}
    for node in nodes:
        input_units = tuple(units[node_id] for node_id in node.input_node_ids)
        if node.operator == "constant":
            expected = parameter_units[node.parameter_refs[0]]
        elif node.operator == "input":
            expected = node.unit
        elif node.operator == "source_attribute":
            expected = node.unit
        elif node.operator in {"source_target_position", "execution_lag"}:
            expected = "dimensionless"
        elif node.operator == "transaction_cost":
            expected = "log_return"
        elif node.operator in {"add", "subtract"}:
            if input_units[0] != input_units[1]:
                raise ValidationError(f"{node.operator} requires equal units")
            expected = input_units[0]
        elif node.operator == "multiply":
            expected = _multiply_unit(input_units[0], input_units[1])
        elif node.operator == "feature_as_coefficient":
            if input_units[0] != "dimensionless":
                raise ValidationError("formula feature coefficient must be dimensionless")
            expected = input_units[1]
        elif node.operator == "safe_divide":
            expected = _divide_unit(input_units[0], input_units[1])
        elif node.operator in {"power", "feature_as_exponent"}:
            if input_units[1] != "dimensionless":
                raise ValidationError("formula exponent must be dimensionless")
            expected = node.unit
        elif node.operator in {"threshold_branch", "state_transition"}:
            if input_units[1] != input_units[2]:
                raise ValidationError("formula branch outputs must have equal units")
            expected = input_units[1]
        else:
            raise ValidationError(f"cannot infer unit for operator {node.operator}")
        if node.unit != expected:
            raise ValidationError(f"formula node {node.node_id} declares unit {node.unit}, expected {expected}")
        units[node.node_id] = node.unit


def _multiply_unit(left: str, right: str) -> str:
    if left == "dimensionless":
        return right
    if right == "dimensionless":
        return left
    return f"({left}*{right})"


def _divide_unit(left: str, right: str) -> str:
    if right == "dimensionless":
        return left
    if left == right:
        return "dimensionless"
    return f"({left}/{right})"


def _number(value: Scalar) -> float:
    if isinstance(value, bool):
        return float(value)
    return value


def _guard_number(node: FormulaNode, key: str) -> float:
    value = node.domain_guard.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise ValidationError(f"formula node {node.node_id} requires finite guard {key}")
    return float(value)


__all__ = [
    "FormulaProgramSpec",
    "SOURCE_PANEL_EXECUTOR_REF",
    "Scalar",
    "compile_formula_program",
    "execute_formula_graph",
]
