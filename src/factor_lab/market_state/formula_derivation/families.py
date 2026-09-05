# pyright: reportImportCycles=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Five source-backed formula-family strategies for representative timing tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Final, TypeAlias, cast

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.factor_engine.base_factor_catalog import (
    BASE_FACTOR_UNIVERSE_VERSION,
    list_base_factor_definitions,
)
from factor_lab.factor_engine.models.factor_spec import FactorSpec
from factor_lab.factor_engine.repositories.spec_registry import spec_registry
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.formula_derivation.attribute_contracts import (
    FormulaNativeAttributeBlueprint,
    attribute_blueprints_for_tool,
)
from factor_lab.market_state.formula_derivation.compiler import (
    FormulaProgramSpec,
    compile_formula_program,
)
from factor_lab.market_state.formula_derivation.materialization import (
    SourceFormulaGraphPanel,
    execute_source_formula_graph_panel,
)
from factor_lab.market_state.formula_derivation.models import (
    FormulaComputationGraph,
    FormulaDerivationPackage,
    FormulaNativeAttributeSpec,
    FormulaNode,
    FormulaOperator,
    InteractionStateMachineTemplate,
    ParameterContrastDerivation,
)
from factor_lab.market_state.joint_policy_attempt_registry import (
    JointPolicyAttemptRegistry,
    enumerate_registered_policy_candidates,
    identifiable_policy_attempt_count,
)
from factor_lab.market_state.joint_policy_family_registry import (
    JointPolicyComplexityBudget,
    JointPolicyFamily,
    JointPolicyFamilyRegistry,
)
from factor_lab.market_state.tool_formula_mechanisms import (
    ToolFormulaSpec,
    build_tool_formula_mechanism_bundle,
)
from factor_lab.market_state.tool_registry import tool_benchmark_specs

FORMULA_FAMILY_COUNTS: Final[dict[str, int]] = {
    "spectral_bandpass_component_filters": 4,
    "lowpass_background_adaptive_centerlines": 3,
    "moving_average_kernel_components_trends": 2,
    "volatility_adaptive_breakout_channels": 2,
    "price_extrema_regression_geometry_channels": 2,
}

_SINGLE_FREQUENCY_CONTRASTS: Final[Mapping[str, tuple[str, object]]] = {
    "frequency_selective_bollinger_channel": ("period_bars", 96),
    "butterworth_lowpass_residual_envelope": ("cutoff_period_bars", 192),
    "causal_asymmetric_arc_state_space_envelope": (
        "round_top_sharp_bottom_ratio",
        0.20,
    ),
}

REPRESENTATIVE_TOOL_BY_FAMILY: Final[dict[str, str]] = {
    "spectral_bandpass_component_filters": "laplace_iir_mixed_bandpass",
    "lowpass_background_adaptive_centerlines": "laplace_iir_lowpass",
    "moving_average_kernel_components_trends": "simple_moving_average_trend",
    "volatility_adaptive_breakout_channels": "bollinger_volatility_channel",
    "price_extrema_regression_geometry_channels": "causal_trendline_channel",
}

TOOL_FAMILY_MEMBERS: Final[dict[str, tuple[str, ...]]] = {
    "spectral_bandpass_component_filters": (
        "laplace_iir_mixed_bandpass",
        "butterworth_clean_bandpass",
        "rolling_fourier_bandpass",
        "causal_haar_wavelet_bandpass",
    ),
    "lowpass_background_adaptive_centerlines": (
        "laplace_iir_lowpass",
        "butterworth_lowpass_residual_envelope",
        "causal_asymmetric_arc_state_space_envelope",
    ),
    "moving_average_kernel_components_trends": (
        "simple_moving_average_trend",
        "r3_nested_moving_average_component",
    ),
    "volatility_adaptive_breakout_channels": (
        "bollinger_volatility_channel",
        "frequency_selective_bollinger_channel",
    ),
    "price_extrema_regression_geometry_channels": (
        "donchian_price_channel",
        "causal_trendline_channel",
    ),
}

_SEARCH_EPSILON_BY_TOOL: Final[Mapping[str, float]] = {
    **{
        tool_id: 1e-8
        for tool_id in (
            *TOOL_FAMILY_MEMBERS["spectral_bandpass_component_filters"],
            *TOOL_FAMILY_MEMBERS["lowpass_background_adaptive_centerlines"],
            "causal_trendline_channel",
        )
    },
    **{
        tool_id: 1e-6
        for tool_id in (
            *TOOL_FAMILY_MEMBERS["moving_average_kernel_components_trends"],
            *TOOL_FAMILY_MEMBERS["volatility_adaptive_breakout_channels"],
            "donchian_price_channel",
        )
    },
}


@dataclass(frozen=True, slots=True)
class RepresentativeFormulaDerivation:
    """One complete representative Stage-1 handoff and registration snapshot."""

    formula_family_id: str
    family_tool_count: int
    source_formula: ToolFormulaSpec
    package: FormulaDerivationPackage
    joint_policy_family: JointPolicyFamily
    registered_factor_specs: tuple[FactorSpec, ...]
    registered_policy_attempt_manifest: Mapping[str, object]
    factor_pool_query_digest: str
    factor_pool_version: str = BASE_FACTOR_UNIVERSE_VERSION
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        if self.family_tool_count != FORMULA_FAMILY_COUNTS[self.formula_family_id]:
            raise ValueError("representative formula-family count changed")
        if (
            self.source_formula.tool_id not in TOOL_FAMILY_MEMBERS[self.formula_family_id]
            or self.package.graph.tool_id != self.source_formula.tool_id
        ):
            raise ValueError("formula derivation is attached to the wrong tool family")
        registered_ids = {spec.spec_id for spec in self.registered_factor_specs}
        package_ids = {
            item.factor_spec_id for item in self.package.formula_native_attributes if item.factor_registration_status != "blocked"
        }
        if registered_ids != package_ids:
            raise ValueError("formula-native attributes do not match FactorSpec registrations")
        if (
            self.registered_policy_attempt_manifest.get("family_id") != self.joint_policy_family.family_id
            or self.registered_policy_attempt_manifest.get("registered_policy_attempt_count")
            != self.joint_policy_family.registered_policy_attempt_count
        ):
            raise ValueError("Stage-1 joint-policy attempt manifest is incomplete")
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValueError("representative derivation cannot grant authority")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "formula_family_id": self.formula_family_id,
            "family_tool_count": self.family_tool_count,
            "tool_id": self.source_formula.tool_id,
            "factor_pool_version": self.factor_pool_version,
            "factor_pool_query_digest": self.factor_pool_query_digest,
            "registered_factor_specs": [spec.to_dict() for spec in self.registered_factor_specs],
            "formula_derivation_package": self.package.to_dict(),
            "joint_policy_family": self.joint_policy_family.to_dict(),
            "registered_policy_attempt_manifest": dict(self.registered_policy_attempt_manifest),
            "production_authority": self.production_authority,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "field_labels_zh": {
                "formula_family_id": "公式工具大类标识",
                "family_tool_count": "大类工具数量",
                "tool_id": "工具标识",
                "factor_pool_query_digest": "内部因子池查询摘要",
                "registered_factor_specs": "内部FactorSpec注册快照",
                "formula_derivation_package": "公式派生包",
                "joint_policy_family": "完整联合策略家族",
                "registered_policy_attempt_manifest": "事前冻结的完整策略公式清单",
            },
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload


FamilyBuilder: TypeAlias = Callable[
    [ToolFormulaSpec],
    tuple[
        FormulaComputationGraph,
        tuple[FormulaNativeAttributeBlueprint, ...],
        ParameterContrastDerivation,
    ],
]
FamilyStrategy: TypeAlias = tuple[
    FamilyBuilder,
    tuple[FormulaOperator, ...],
    Mapping[str, object],
]


def build_representative_formula_derivations(
    *,
    persist_factor_registration: bool = True,
) -> tuple[RepresentativeFormulaDerivation, ...]:
    """Build exactly one representative for each of the five formula families."""

    formulas = {item.tool_id: item for item in build_tool_formula_mechanism_bundle().tool_formulas}
    return tuple(
        build_formula_derivation_for_tool(
            formulas[tool_id],
            formula_family_id=family_id,
            persist_factor_registration=persist_factor_registration,
        )
        for family_id, tool_id in REPRESENTATIVE_TOOL_BY_FAMILY.items()
    )


def build_formula_derivation_for_tool(
    source: ToolFormulaSpec,
    *,
    formula_family_id: str,
    persist_factor_registration: bool = True,
) -> RepresentativeFormulaDerivation:
    """Apply one of the five shared strategies to a registered tool formula."""

    if source.tool_id not in TOOL_FAMILY_MEMBERS.get(formula_family_id, ()):
        raise ValueError("tool is not registered in the requested formula family")
    builder, operators, topology = _family_strategy(
        formula_family_id,
        tool_id=source.tool_id,
    )
    graph, attribute_blueprints, contrast = builder(source)
    pool_digest, factor_specs, attributes = _register_formula_native_attributes(
        source,
        attribute_blueprints,
        persist_factor_registration=persist_factor_registration,
    )
    template = InteractionStateMachineTemplate(
        template_id=f"template:{source.tool_id}:joint-state",
        atom_attribute_ids=tuple(item.attribute_id for item in attributes),
        allowed_operators=operators,
        heredity_requirement="none",
        marginal_admission_required=False,
        complexity_budget={
            "operator_count": len(operators),
            "coefficient_count": 3,
            "exponent_count": 3,
            "branch_count": 2,
            "threshold_count": 3,
            "scale_count": 2,
            "state_memory_count": 2,
        },
        state_topology=topology,
    )
    package = FormulaDerivationPackage(
        package_id=f"formula-derivation:{source.tool_id}:v1",
        graph=graph,
        parameter_contrasts=(contrast,),
        formula_native_attributes=attributes,
        interaction_state_machine_templates=(template,),
        source_artifact_digests={
            "tool_formula_spec": canonical_digest(source.to_dict()),
            "base_factor_universe_query": pool_digest,
        },
    )
    budget = template.complexity_budget
    complexity = JointPolicyComplexityBudget(
        operator_count=budget["operator_count"],
        coefficient_count=budget["coefficient_count"],
        exponent_count=budget["exponent_count"],
        branch_count=budget["branch_count"],
        threshold_count=budget["threshold_count"],
        scale_count=budget["scale_count"],
        state_memory_count=budget["state_memory_count"],
    )
    joint_family = JointPolicyFamily(
        family_id=f"joint-family:{source.tool_id}:v1",
        tool_id=source.tool_id,
        derivation_package_digest=str(package.to_dict()["semantic_digest"]),
        formula_graph_digest=str(graph.to_dict()["semantic_digest"]),
        atom_attribute_ids=template.atom_attribute_ids,
        allowed_operators=operators,
        heredity_requirement="none",
        marginal_admission_required=False,
        complexity_budget=complexity,
        registered_policy_attempt_count=complexity.complete_attempt_count,
        multiplicity_denominator=complexity.complete_attempt_count,
        state_topology=topology,
        domain_guards={
            "finite_only": True,
            "safe_divide": "explicit_minimum_denominator",
            "power": "bounded_real_domain",
            "execution_clock": "after_close_next_bar",
        },
        search_axes={
            "coefficients": [-1.0, 0.5, 1.0],
            "exponents": [1, 2, 3],
            "branches": ["enter_hold", "exit_hold"],
            "thresholds": [
                -_SEARCH_EPSILON_BY_TOOL[source.tool_id],
                0.0,
                _SEARCH_EPSILON_BY_TOOL[source.tool_id],
            ],
            "scales": [-1, 1],
            "state_memory_bars": [1, 2],
        },
    )
    identifiable_count = identifiable_policy_attempt_count(joint_family)
    joint_family = replace(
        joint_family,
        registered_policy_attempt_count=identifiable_count,
        multiplicity_denominator=identifiable_count,
    )
    family_registry = JointPolicyFamilyRegistry()
    _ = family_registry.register(joint_family)
    attempt_registry = JointPolicyAttemptRegistry(family_registry)
    candidates = enumerate_registered_policy_candidates(joint_family)
    _ = attempt_registry.register(joint_family, candidates)
    attempt_manifest = attempt_registry.manifest(joint_family.family_id)
    return RepresentativeFormulaDerivation(
        formula_family_id=formula_family_id,
        family_tool_count=FORMULA_FAMILY_COUNTS[formula_family_id],
        source_formula=source,
        package=package,
        joint_policy_family=joint_family,
        registered_factor_specs=factor_specs,
        registered_policy_attempt_manifest=attempt_manifest,
        factor_pool_query_digest=pool_digest,
    )


def _family_strategy(
    family_id: str,
    *,
    tool_id: str,
) -> FamilyStrategy:
    strategies = {
        "spectral_bandpass_component_filters": (
            _build_bandpass,
            ("multiply", "threshold_branch", "state_transition"),
            {"state": "component_direction", "diagnostic_only": "BDCI"},
        ),
        "lowpass_background_adaptive_centerlines": (
            _build_lowpass,
            ("multiply", "safe_divide", "threshold_branch", "state_transition"),
            {"state": "centerline_direction_x_innovation", "memory_bars": [1, 2]},
        ),
        "moving_average_kernel_components_trends": (
            _build_moving_average,
            ("multiply", "power", "threshold_branch", "state_transition"),
            {"state": "kernel_gap_x_path_noise", "execution": "next_bar"},
        ),
        "volatility_adaptive_breakout_channels": (
            _build_volatility_channel,
            ("multiply", "feature_as_coefficient", "threshold_branch", "state_transition"),
            {"state": "rail_margin_x_width_x_center_direction", "branches": ["enter", "exit"]},
        ),
        "price_extrema_regression_geometry_channels": (
            _build_regression_geometry,
            ("multiply", "safe_divide", "power", "threshold_branch", "state_transition"),
            {"state": "slope_gap_x_scale_ratio_x_rail_margin", "windows": [40, 160]},
        ),
    }
    if tool_id == "donchian_price_channel":
        return cast(
            FamilyStrategy,
            (
                _build_donchian,
                strategies[family_id][1],
                {
                    "state": "entry_margin_x_exit_margin_x_channel_width",
                    "entry_window": "registered_parameter",
                    "exit_window": "registered_parameter",
                },
            ),
        )
    if tool_id == "r3_nested_moving_average_component":
        return cast(
            FamilyStrategy,
            (
                _build_r3_component,
                strategies[family_id][1],
                {"state": "nested_component_delta_x_energy", "execution": "next_bar"},
            ),
        )
    return cast(FamilyStrategy, strategies[family_id])


def _register_formula_native_attributes(
    source: ToolFormulaSpec,
    blueprints: tuple[FormulaNativeAttributeBlueprint, ...],
    *,
    persist_factor_registration: bool,
) -> tuple[str, tuple[FactorSpec, ...], tuple[FormulaNativeAttributeSpec, ...]]:
    existing = tuple(
        sorted(
            (
                definition.factor_id,
                definition.dsl_expression,
                definition.required_fields,
            )
            for definition in list_base_factor_definitions()
        )
    )
    query_digest = canonical_digest(
        {
            "base_factor_universe_version": BASE_FACTOR_UNIVERSE_VERSION,
            "existing_definitions": existing,
            "requested_formulas": [item.formula for item in blueprints],
        }
    )
    factor_specs: list[FactorSpec] = []
    attributes: list[FormulaNativeAttributeSpec] = []
    for blueprint in blueprints:
        factor_spec_id = f"market-state-formula-native:{source.tool_id}:{blueprint.attribute_id}:v2"
        expression_digest = canonical_digest(
            {
                "tool_formula_id": source.formula_id,
                "attribute_id": blueprint.attribute_id,
                "causal_formula": blueprint.formula,
            }
        )
        requested = FactorSpec(
            spec_id=factor_spec_id,
            spec_version=factor_spec_id,
            name=blueprint.attribute_id,
            description=(
                "Formula-native structural research factor. Registered after the base_factor_universe query; not strategy-validated."
            ),
            factor_type="python_callable",
            callable_ref=("factor_lab.market_state.formula_derivation.materialization:materialize_registered_formula_factor"),
            input_schema={
                "required_fields": ["timestamp", "open", "high", "low", "close"],
                "tool_id": source.tool_id,
                "attribute_id": blueprint.attribute_id,
            },
            output_schema={
                "unit": blueprint.unit,
                "availability": "after_close",
                "causal": True,
            },
            parameters={
                "causal_formula": blueprint.formula,
                "tool_formula_id": source.formula_id,
                "factor_pool_query_digest": query_digest,
                "attribute_id": blueprint.attribute_id,
            },
            source_refs=[source.implementation_ref, *source.native_source_refs],
            input_field_lineage={field: f"raw_kline.{field}" for field in ("timestamp", "open", "high", "low", "close")},
            expression_hash=expression_digest,
            normalized_ast={
                "op": "source_backed_tool_formula_attribute",
                "tool_id": source.tool_id,
                "attribute_id": blueprint.attribute_id,
                "formula": blueprint.formula,
            },
            operator_list=["source_backed_tool_formula_attribute"],
            complexity_score=1.0,
            field_refs=["timestamp", "open", "high", "low", "close"],
            nan_policy="warmup_or_domain_guard_failure_yields_null",
            tags={
                "library": "internal_market_state_research",
                "lifecycle_state": "ResearchFactor",
                "evidence_level": "structural_dependency",
                "effectiveness": "not_strategy_validated",
                "production_authority": "false",
            },
        )
        existing_spec = (
            spec_registry.get_factor_spec_sync(factor_spec_id)
            if persist_factor_registration
            else None
        )
        if existing_spec is not None and existing_spec.to_dict() != requested.to_dict():
            raise ValueError(f"registered formula-native FactorSpec drifted: {factor_spec_id}")
        if persist_factor_registration:
            # Re-register an identical in-memory hit so a changed DataHome still
            # receives the durable custom-spec snapshot.  The read-only rebuild
            # path never enters this branch.
            factor_spec = spec_registry.register_factor_spec_sync(
                existing_spec or requested
            )
        else:
            factor_spec = requested
        factor_specs.append(factor_spec)
        attributes.append(
            FormulaNativeAttributeSpec(
                attribute_id=blueprint.attribute_id,
                upstream_node_ids=(blueprint.output_node_id,),
                causal_formula=blueprint.formula,
                unit=blueprint.unit,
                availability="after_close",
                factor_registration_status="bound_existing",
                factor_spec_id=factor_spec_id,
            )
        )
    return query_digest, tuple(factor_specs), tuple(attributes)


def _build_bandpass(
    source: ToolFormulaSpec,
) -> tuple[FormulaComputationGraph, tuple[FormulaNativeAttributeBlueprint, ...], ParameterContrastDerivation]:
    attributes = attribute_blueprints_for_tool(source.tool_id)
    graph = _closed_source_graph(source, attributes)
    return graph, attributes, _contrast(source, graph, "period_q_profile", "Δfrequency_response_and_Δcomponent")


def _build_lowpass(
    source: ToolFormulaSpec,
) -> tuple[FormulaComputationGraph, tuple[FormulaNativeAttributeBlueprint, ...], ParameterContrastDerivation]:
    attributes = attribute_blueprints_for_tool(source.tool_id)
    graph = _closed_source_graph(source, attributes)
    return graph, attributes, _contrast(source, graph, "period_q_profile", "Δcenterline_and_Δinnovation")


def _build_moving_average(
    source: ToolFormulaSpec,
) -> tuple[FormulaComputationGraph, tuple[FormulaNativeAttributeBlueprint, ...], ParameterContrastDerivation]:
    attributes = attribute_blueprints_for_tool(source.tool_id)
    graph = _closed_source_graph(source, attributes)
    return graph, attributes, _contrast(source, graph, "fast_slow_window_profile", "Δexact_kernel_weights")


def _build_r3_component(
    source: ToolFormulaSpec,
) -> tuple[FormulaComputationGraph, tuple[FormulaNativeAttributeBlueprint, ...], ParameterContrastDerivation]:
    attributes = attribute_blueprints_for_tool(source.tool_id)
    graph = _closed_source_graph(source, attributes)
    return graph, attributes, _contrast(source, graph, "fast_slow_window_profile", "Δnested_component")


def _build_volatility_channel(
    source: ToolFormulaSpec,
) -> tuple[FormulaComputationGraph, tuple[FormulaNativeAttributeBlueprint, ...], ParameterContrastDerivation]:
    attributes = attribute_blueprints_for_tool(source.tool_id)
    graph = _closed_source_graph(source, attributes)
    return graph, attributes, _contrast(source, graph, "window_width_profile", "Δentry_exit_branch_margins")


def _build_regression_geometry(
    source: ToolFormulaSpec,
) -> tuple[FormulaComputationGraph, tuple[FormulaNativeAttributeBlueprint, ...], ParameterContrastDerivation]:
    attributes = attribute_blueprints_for_tool(source.tool_id)
    graph = _closed_source_graph(source, attributes)
    return graph, attributes, _contrast(source, graph, "window_40_160", "ΔOLS_lag_weight_expansion")


def _build_donchian(
    source: ToolFormulaSpec,
) -> tuple[FormulaComputationGraph, tuple[FormulaNativeAttributeBlueprint, ...], ParameterContrastDerivation]:
    attributes = attribute_blueprints_for_tool(source.tool_id)
    graph = _closed_source_graph(source, attributes)
    return graph, attributes, _contrast(source, graph, "entry_exit_window_profile", "Δextrema_expiry_geometry")


def _closed_source_graph(
    source: ToolFormulaSpec,
    attributes: tuple[FormulaNativeAttributeBlueprint, ...],
) -> FormulaComputationGraph:
    raw_nodes = tuple(
        _input(
            source,
            f"raw_{field}",
            field,
            "timestamp" if field == "timestamp" else "price",
        )
        for field in ("timestamp", "open", "high", "low", "close")
    )
    raw_ids = tuple(node.node_id for node in raw_nodes)
    attribute_nodes = tuple(
        FormulaNode(
            node_id=item.output_node_id,
            operator="source_attribute",
            input_node_ids=raw_ids,
            kline_field_refs=(),
            parameter_refs=(),
            unit=item.unit,
            availability="after_close",
            warmup_bars=0,
            missing_policy="source_warmup_or_domain_guard_yields_null",
            domain_guard={
                "attribute_id": item.attribute_id,
                "causal_formula": item.formula,
            },
            source_witness=_witness(source),
        )
        for item in attributes
    )
    target = FormulaNode(
        node_id="target_position",
        operator="source_target_position",
        input_node_ids=raw_ids,
        kline_field_refs=(),
        parameter_refs=(),
        unit="dimensionless",
        availability="after_close",
        warmup_bars=0,
        missing_policy="frozen_source_validity_then_cash",
        domain_guard={"signal_formula": source.signal_formula},
        source_witness=_witness(source),
    )
    cost_parameter = FormulaNode(
        node_id="cost_bps",
        operator="constant",
        input_node_ids=(),
        kline_field_refs=(),
        parameter_refs=("cost_bps",),
        unit="bps",
        availability="static",
        warmup_bars=0,
        missing_policy="fail_closed",
        domain_guard={},
        source_witness=_witness(source),
    )
    next_bar = FormulaNode(
        node_id="next_bar_position",
        operator="execution_lag",
        input_node_ids=("target_position",),
        kline_field_refs=(),
        parameter_refs=(),
        unit="dimensionless",
        availability="after_close",
        warmup_bars=0,
        missing_policy="cash_until_decision_available",
        domain_guard={"lag_bars": 1},
        source_witness=_witness(source),
    )
    transaction_cost = FormulaNode(
        node_id="transaction_cost",
        operator="transaction_cost",
        input_node_ids=("target_position", "next_bar_position", "cost_bps"),
        kline_field_refs=(),
        parameter_refs=(),
        unit="log_return",
        availability="after_close",
        warmup_bars=0,
        missing_policy="fail_closed",
        domain_guard={"formula": "abs(position_t-position_(t-1))*cost_bps/10000"},
        source_witness=_witness(source),
    )
    nodes = (
        *raw_nodes,
        *attribute_nodes,
        target,
        cost_parameter,
        next_bar,
        transaction_cost,
    )
    outputs = (
        *(item.output_node_id for item in attributes),
        "target_position",
        "next_bar_position",
        "transaction_cost",
    )
    return compile_formula_program(
        source,
        FormulaProgramSpec(
            program_id=f"formula-graph:{source.tool_id}:v1",
            tool_id=source.tool_id,
            tool_version="v1_benchmark",
            formula_id=source.formula_id,
            nodes=nodes,
            output_node_ids=outputs,
            parameter_units={"cost_bps": "bps"},
        ),
    )


def _input(source: ToolFormulaSpec, node_id: str, field: str, unit: str) -> FormulaNode:
    return FormulaNode(
        node_id=node_id,
        operator="input",
        input_node_ids=(),
        kline_field_refs=(field,),
        parameter_refs=(),
        unit=unit,
        availability="after_close",
        warmup_bars=0,
        missing_policy="warmup_or_missing_is_null",
        domain_guard={},
        source_witness=_witness(source),
    )


def _witness(source: ToolFormulaSpec) -> dict[str, str]:
    return {
        "formula_id": source.formula_id,
        "implementation_ref": source.implementation_ref,
    }


def _contrast(
    source: ToolFormulaSpec,
    graph: FormulaComputationGraph,
    profile_axis: str,
    delta_expression: str,
) -> ParameterContrastDerivation:
    benchmarks = {item.tool_id: item for item in tool_benchmark_specs()}
    benchmark = benchmarks[source.tool_id]
    frequencies = tuple(sorted(benchmark.parameters_by_frequency))
    baseline_frequency = "1d" if "1d" in frequencies else frequencies[0]
    baseline = dict(benchmark.parameters_by_frequency[baseline_frequency])
    if len(frequencies) > 1:
        candidate_frequency = next(item for item in frequencies if item != baseline_frequency)
        candidate = dict(benchmark.parameters_by_frequency[candidate_frequency])
    else:
        candidate_frequency = f"{baseline_frequency}-catalog-contrast"
        candidate = dict(baseline)
        parameter_id, candidate_value = _SINGLE_FREQUENCY_CONTRASTS[source.tool_id]
        candidate[parameter_id] = candidate_value
    fixture = _synthetic_formula_fixture()
    baseline_panel = execute_source_formula_graph_panel(
        graph=graph,
        bars=fixture,
        benchmark=benchmark,
        frequency=baseline_frequency,
        parameters=baseline,
    )
    candidate_panel = execute_source_formula_graph_panel(
        graph=graph,
        bars=fixture,
        benchmark=benchmark,
        frequency=baseline_frequency,
        parameters=candidate,
    )
    baseline_digest, baseline_actions, baseline_outputs = _panel_signature(baseline_panel)
    candidate_digest, candidate_actions, candidate_outputs = _panel_signature(candidate_panel)
    if len(baseline_outputs) != len(candidate_outputs):
        raise ValidationError("formula contrast output widths differ")
    delta_outputs = tuple(
        candidate_value - baseline_value for baseline_value, candidate_value in zip(baseline_outputs, candidate_outputs, strict=True)
    )
    disagreements = tuple(left != right for left, right in zip(baseline_actions, candidate_actions, strict=True))
    delta_output_digest = canonical_digest({"delta_outputs": list(delta_outputs)})
    action_disagreement_digest = canonical_digest({"action_disagreements": list(disagreements)})
    disagreement_count = sum(disagreements)
    reconciliation_fields = {
        "baseline_output_digest": baseline_digest,
        "candidate_output_digest": candidate_digest,
        "delta_output_digest": delta_output_digest,
        "action_disagreement_digest": action_disagreement_digest,
        "output_count": len(delta_outputs),
        "action_disagreement_count": disagreement_count,
        "maximum_delta_identity_error": 0.0,
    }
    return ParameterContrastDerivation(
        contrast_id=f"contrast:{source.tool_id}:{profile_axis}",
        baseline_profile_id=f"{source.tool_id}:{baseline_frequency}",
        candidate_profile_id=f"{source.tool_id}:{candidate_frequency}",
        delta_output_expression=delta_expression,
        delta_parameter_expression=profile_axis,
        action_disagreement_predicate="frozen_baseline_action != frozen_candidate_action",
        boundary_margin_expression="signed_distance_to_relevant_frozen_boundary",
        atomic_contributions={effect.parameter_id: effect.formula_term for effect in source.parameter_effects},
        exactness="deterministic_numeric",
        baseline_parameters=baseline,
        candidate_parameters=candidate,
        synthetic_fixture_digest=canonical_digest(
            {
                "fixture_id": "formula-graph-contrast-v1",
                "row_count": len(fixture),
                "raw_kline_fields": ["timestamp", "open", "high", "low", "close"],
            }
        ),
        baseline_output_digest=baseline_digest,
        candidate_output_digest=candidate_digest,
        delta_output_digest=delta_output_digest,
        action_disagreement_digest=action_disagreement_digest,
        numeric_reconciliation_digest=canonical_digest(reconciliation_fields),
        output_count=len(delta_outputs),
        maximum_delta_identity_error=0.0,
        action_disagreement_count=disagreement_count,
        graph_execution_verified=True,
    )


def _synthetic_formula_fixture(row_count: int = 2600) -> pd.DataFrame:
    index = np.arange(row_count, dtype=float)
    close = 100.0 + 0.02 * index + 3.5 * np.sin(index / 17.0) + np.sin(index / 5.0)
    return pd.DataFrame(
        {
            "timestamp": pd.bdate_range("2010-01-04", periods=row_count),
            "open": close * 0.999,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
        }
    )


def _panel_signature(
    panel: SourceFormulaGraphPanel,
) -> tuple[str, tuple[float, ...], tuple[float, ...]]:
    # Kept local so Stage 1 persists only digests, never synthetic row detail.
    feature_frame = panel.feature_frame
    target = panel.target_position
    cost = panel.transaction_cost
    valid = cast(pd.Series, feature_frame.notna().all(axis=1))
    positions = np.flatnonzero(valid.to_numpy(dtype=bool))[-128:]
    if len(positions) < 32:
        raise ValueError("formula contrast fixture did not produce enough complete rows")
    selected = feature_frame.iloc[positions]
    actions = tuple(float(value) for value in target.iloc[positions])
    costs = tuple(float(value) for value in cost.iloc[positions])
    numeric_outputs = tuple(float(value) for value in selected.to_numpy(dtype=float).ravel()) + actions + costs
    return (
        canonical_digest({"numeric_outputs": list(numeric_outputs)}),
        actions,
        numeric_outputs,
    )


__all__ = [
    "FORMULA_FAMILY_COUNTS",
    "REPRESENTATIVE_TOOL_BY_FAMILY",
    "TOOL_FAMILY_MEMBERS",
    "RepresentativeFormulaDerivation",
    "build_formula_derivation_for_tool",
    "build_representative_formula_derivations",
]
