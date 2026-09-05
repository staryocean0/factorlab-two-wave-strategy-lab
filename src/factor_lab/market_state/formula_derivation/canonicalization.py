"""Canonical graph fingerprints and deterministic behavior-equivalence checks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isclose
from typing import cast

from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.formula_derivation.compiler import (
    Scalar,
    execute_formula_graph,
)
from factor_lab.market_state.formula_derivation.models import (
    FormulaComputationGraph,
    FormulaNode,
)


def canonical_graph_fingerprint(graph: FormulaComputationGraph) -> str:
    """Hash algebraic structure while removing node IDs and commutative order."""

    nodes = {node.node_id: node for node in graph.nodes}
    expressions = [_canonical_expression(nodes[node_id], nodes=nodes, cache={}) for node_id in graph.output_node_ids]
    return canonical_digest(
        {
            "tool_id": graph.tool_id,
            "output_expressions": expressions,
            "execution_clock": "after_close_next_bar",
        }
    )


def deduplicate_formula_graphs(
    graphs: Sequence[FormulaComputationGraph],
) -> tuple[FormulaComputationGraph, ...]:
    """Keep the first graph in each canonical algebraic equivalence class."""

    unique: dict[str, FormulaComputationGraph] = {}
    for graph in graphs:
        _ = unique.setdefault(canonical_graph_fingerprint(graph), graph)
    return tuple(unique.values())


def graphs_behaviorally_equivalent(
    left: FormulaComputationGraph,
    right: FormulaComputationGraph,
    *,
    synthetic_rows: Sequence[Mapping[str, Scalar]],
    left_parameters: Mapping[str, Scalar],
    right_parameters: Mapping[str, Scalar],
    absolute_tolerance: float = 1e-12,
) -> bool:
    """Compare outputs on a declared synthetic fixture, never on market rows."""

    if len(left.output_node_ids) != len(right.output_node_ids) or not synthetic_rows:
        return False
    for row in synthetic_rows:
        left_output = tuple(execute_formula_graph(left, kline_fields=row, parameters=left_parameters).values())
        right_output = tuple(execute_formula_graph(right, kline_fields=row, parameters=right_parameters).values())
        for left_value, right_value in zip(left_output, right_output, strict=True):
            if isinstance(left_value, bool) or isinstance(right_value, bool):
                if bool(left_value) != bool(right_value):
                    return False
            elif not isclose(
                cast(float, left_value),
                cast(float, right_value),
                rel_tol=0.0,
                abs_tol=absolute_tolerance,
            ):
                return False
    return True


def _canonical_expression(
    node: FormulaNode,
    *,
    nodes: Mapping[str, FormulaNode],
    cache: dict[str, object],
) -> object:
    cached = cache.get(node.node_id)
    if cached is not None:
        return cached
    if node.operator == "input":
        expression: object = {
            "operator": "input",
            "field": node.kline_field_refs[0],
            "unit": node.unit,
        }
    elif node.operator == "constant":
        expression = {
            "operator": "parameter",
            "parameter_id": node.parameter_refs[0],
            "unit": node.unit,
        }
    else:
        operator = {
            "feature_as_exponent": "power",
        }.get(node.operator, node.operator)
        children = [_canonical_expression(nodes[parent_id], nodes=nodes, cache=cache) for parent_id in node.input_node_ids]
        if operator in {"add", "multiply"}:
            children.sort(key=lambda value: canonical_digest({"expression": value}))
        expression = {
            "operator": operator,
            "inputs": children,
            "unit": node.unit,
            "domain_guard": dict(sorted(node.domain_guard.items())),
        }
    cache[node.node_id] = expression
    return expression


__all__ = [
    "canonical_graph_fingerprint",
    "deduplicate_formula_graphs",
    "graphs_behaviorally_equivalent",
]
