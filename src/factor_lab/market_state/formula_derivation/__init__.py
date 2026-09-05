"""Dependency-neutral formula-derived contracts for market-state research V3.

The package initializer intentionally exposes only the leaf contract/compiler
surfaces.  Family construction and persistence import the joint-policy modules,
so importing them here would make the public registry import order-dependent.
Callers that need orchestration should import ``families`` or ``preparation``
directly.
"""

from factor_lab.market_state.formula_derivation.canonicalization import (
    canonical_graph_fingerprint,
    deduplicate_formula_graphs,
    graphs_behaviorally_equivalent,
)
from factor_lab.market_state.formula_derivation.compiler import (
    FormulaProgramSpec,
    compile_formula_program,
    execute_formula_graph,
)
from factor_lab.market_state.formula_derivation.contrasts import (
    ParameterContrastEvaluation,
    ParameterProfile,
    derive_parameter_contrast,
)
from factor_lab.market_state.formula_derivation.models import (
    FormulaComputationGraph,
    FormulaDerivationPackage,
    FormulaNativeAttributeSpec,
    FormulaNode,
    InteractionStateMachineTemplate,
    ParameterContrastDerivation,
)
from factor_lab.market_state.formula_derivation.validation import (
    validate_formula_computation_graph,
    validate_formula_derivation_package,
)

__all__ = [
    "FormulaProgramSpec",
    "FormulaComputationGraph",
    "FormulaDerivationPackage",
    "FormulaNativeAttributeSpec",
    "FormulaNode",
    "InteractionStateMachineTemplate",
    "ParameterContrastEvaluation",
    "ParameterContrastDerivation",
    "ParameterProfile",
    "canonical_graph_fingerprint",
    "compile_formula_program",
    "deduplicate_formula_graphs",
    "derive_parameter_contrast",
    "execute_formula_graph",
    "graphs_behaviorally_equivalent",
    "validate_formula_computation_graph",
    "validate_formula_derivation_package",
]
