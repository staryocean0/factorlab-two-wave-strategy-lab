# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Explicit, zero-authority V2 registrations for parameter experiments.

The V1 fixed dictionary mixes an old equal 3x3 comparison surface with its
candidate-generation mechanism.  This module deliberately does neither: it
records a concrete experiment before any evaluator may consume it, keeps the
full formula parameter vector content-addressed, and makes parameter changes
auditable as either one declared axis or one declared coupled bundle.

Registration is not execution permission.  In particular, this module cannot
grant dynamic parameter, tool-routing, or production authority.
"""

from __future__ import annotations

import ast
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, Literal, TypeAlias

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.time_scale_catalog import (
    TimeScaleCatalog,
    build_time_scale_catalog_v2,
)
from factor_lab.market_state.tool_formula_surface_audit import audit_formula_surface
from factor_lab.market_state.tool_parameter_catalog_v2 import (
    Primitive,
    ToolParameterCatalogV2,
    ToolParameterSpecV2,
    build_tool_parameter_catalog_v2,
)
from factor_lab.market_state.tool_registry import tool_benchmark_specs

TOOL_PARAMETER_EXPERIMENT_SCHEMA_ID: Final[str] = "market_state_tool_parameter_experiment@1.0"
TOOL_PARAMETER_EXPERIMENT_REGISTRY_VERSION: Final[str] = "tool_parameter_experiment_registry_v2"
MAXIMUM_CANDIDATES_PER_EXPERIMENT: Final[int] = 9
_PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[3]

AxisKind: TypeAlias = Literal["single_parameter", "coupled_parameters"]
AdapterBindingStatus: TypeAlias = Literal["v1_adapter_complete", "adapter_extension_required"]


def _primitive(value: object, *, field: str) -> Primitive:
    if not isinstance(value, (str, int, float, bool)):
        raise ValidationError(f"{field} must be a JSON primitive")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValidationError(f"{field} must be finite")
    if isinstance(value, str) and not value.strip():
        raise ValidationError(f"{field} cannot be blank")
    return value


def _parameter_vector(values: Mapping[str, object], *, field: str) -> Mapping[str, Primitive]:
    result: dict[str, Primitive] = {}
    for raw_key, raw_value in values.items():
        key = str(raw_key)
        if not key.strip() or key == "cost_bps":
            raise ValidationError(f"{field} contains an invalid parameter key")
        result[key] = _primitive(raw_value, field=f"{field}.{key}")
    if not result:
        raise ValidationError(f"{field} cannot be empty")
    return MappingProxyType(dict(sorted(result.items())))


def parameter_vector_digest(parameters: Mapping[str, object]) -> str:
    """Return the immutable content identity of a full formula parameter vector."""

    normalized = _parameter_vector(parameters, field="parameter vector")
    return canonical_digest({"parameters": dict(normalized)})


def _parameter_axis_id(tool_id: str, parameter_ids: Sequence[str]) -> str:
    normalized = tuple(sorted(parameter_ids))
    if len(normalized) == 1:
        return f"{tool_id}:{normalized[0]}"
    return f"{tool_id}:coupled:" + "+".join(normalized)


def _experiment_id(
    *,
    tool_id: str,
    carrier_frequency: str,
    parameter_axis_id: str,
    parameter_ids: Sequence[str],
    baseline_parameters: Mapping[str, Primitive],
    candidate_parameters: Sequence[Mapping[str, Primitive]],
    multiplicity_family_id: str,
    axis_kind: AxisKind,
    coupling_rationale: str,
    factor_scale_ids: Sequence[str],
    time_scale_catalog_semantic_digest: str,
) -> str:
    body = {
        "tool_id": tool_id,
        "carrier_frequency": carrier_frequency,
        "parameter_axis_id": parameter_axis_id,
        "parameter_ids": list(parameter_ids),
        "baseline_parameters": dict(baseline_parameters),
        "candidate_parameter_vector_digests": [parameter_vector_digest(item) for item in candidate_parameters],
        "multiplicity_family_id": multiplicity_family_id,
        "axis_kind": axis_kind,
        "coupling_rationale": coupling_rationale,
        "factor_scale_ids": list(factor_scale_ids),
        "time_scale_catalog_semantic_digest": time_scale_catalog_semantic_digest,
    }
    return "parameter-experiment:" + canonical_digest(body).removeprefix("sha256:")[:24]


@dataclass(frozen=True, slots=True)
class ParameterExperimentCandidate:
    """A fully specified candidate vector registered before evaluation."""

    candidate_id: str
    experiment_id: str
    parameters: Mapping[str, Primitive]
    parameter_vector_digest: str
    is_baseline: bool

    def __post_init__(self) -> None:
        parameters = _parameter_vector(self.parameters, field="candidate parameters")
        digest = parameter_vector_digest(parameters)
        if self.parameter_vector_digest != digest:
            raise ValidationError("candidate parameter vector digest does not match content")
        expected_id = (
            "parameter-candidate:"
            + canonical_digest({"experiment_id": self.experiment_id, "parameter_vector_digest": digest}).removeprefix("sha256:")[:24]
        )
        if self.candidate_id != expected_id:
            raise ValidationError("candidate id does not match its registered parameter vector")
        object.__setattr__(self, "parameters", parameters)

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "experiment_id": self.experiment_id,
            "parameters": dict(self.parameters),
            "parameter_vector_digest": self.parameter_vector_digest,
            "is_baseline": self.is_baseline,
        }


@dataclass(frozen=True, slots=True)
class ToolParameterExperiment:
    """A pre-registered parameter axis; it remains non-executable by design."""

    experiment_id: str
    tool_id: str
    carrier_frequency: str
    parameter_axis_id: str
    parameter_ids: tuple[str, ...]
    axis_kind: AxisKind
    coupling_rationale: str
    multiplicity_family_id: str
    maximum_candidate_count: int
    baseline_parameters: Mapping[str, Primitive]
    candidates: tuple[ParameterExperimentCandidate, ...]
    adapter_binding_status: AdapterBindingStatus
    factor_scale_ids: tuple[str, ...]
    time_scale_catalog_semantic_digest: str
    scale_binding_status: str = "time_scale_catalog_v2_bound"
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if not self.tool_id or not self.carrier_frequency or not self.parameter_axis_id:
            raise ValidationError("parameter experiment identity is required")
        parameter_ids = tuple(sorted(set(self.parameter_ids)))
        if not parameter_ids:
            raise ValidationError("parameter experiment requires at least one axis parameter")
        if self.axis_kind not in {"single_parameter", "coupled_parameters"}:
            raise ValidationError("unsupported experiment axis kind")
        if self.axis_kind == "single_parameter" and len(parameter_ids) != 1:
            raise ValidationError("a single parameter axis may change exactly one parameter")
        if self.axis_kind == "coupled_parameters":
            if len(parameter_ids) < 2 or not self.coupling_rationale.strip():
                raise ValidationError("a coupled axis requires two parameters and a rationale")
        if not self.multiplicity_family_id.strip():
            raise ValidationError("parameter experiment multiplicity family is required")
        if not 1 <= self.maximum_candidate_count <= MAXIMUM_CANDIDATES_PER_EXPERIMENT:
            raise ValidationError("parameter experiment candidate budget must be in [1, 9]")
        baseline = _parameter_vector(self.baseline_parameters, field="experiment baseline")
        candidates = tuple(self.candidates)
        if not candidates or len(candidates) > self.maximum_candidate_count:
            raise ValidationError("registered candidate count exceeds its pre-registered budget")
        if len({item.candidate_id for item in candidates}) != len(candidates):
            raise ValidationError("parameter experiment contains duplicate candidate identities")
        if len({item.parameter_vector_digest for item in candidates}) != len(candidates):
            raise ValidationError("parameter experiment contains duplicate parameter vectors")
        if any(item.experiment_id != self.experiment_id for item in candidates):
            raise ValidationError("candidate belongs to a different experiment")
        baselines = [item for item in candidates if item.is_baseline]
        if len(baselines) != 1 or dict(baselines[0].parameters) != dict(baseline):
            raise ValidationError("parameter experiment requires exactly one unchanged baseline candidate")
        for candidate in candidates:
            if set(candidate.parameters) != set(baseline):
                raise ValidationError("candidate must retain the full registered formula parameter vector")
            changed = tuple(key for key in baseline if candidate.parameters[key] != baseline[key])
            if candidate.is_baseline:
                if changed:
                    raise ValidationError("baseline candidate cannot change a parameter")
            elif self.axis_kind == "single_parameter":
                if changed != parameter_ids:
                    raise ValidationError("single parameter candidate changed an undeclared quantity")
            elif set(changed) != set(parameter_ids):
                raise ValidationError("coupled candidate must change every declared coupled quantity")
        if self.adapter_binding_status not in {"v1_adapter_complete", "adapter_extension_required"}:
            raise ValidationError("unsupported adapter binding status")
        if self.scale_binding_status != "time_scale_catalog_v2_bound":
            raise ValidationError("parameter experiment must bind the formal time-scale catalog")
        factor_scale_ids = tuple(sorted(set(self.factor_scale_ids)))
        if not factor_scale_ids or any(not value.startswith("factor_") for value in factor_scale_ids):
            raise ValidationError("parameter experiment requires canonical factor scale ids")
        if not self.time_scale_catalog_semantic_digest.startswith("sha256:"):
            raise ValidationError("parameter experiment requires the time-scale catalog digest")
        if self.dynamic_parameter_authority or self.tool_routing_authority or self.production_authority:
            raise ValidationError("parameter experiment registration cannot grant authority")
        object.__setattr__(self, "parameter_ids", parameter_ids)
        object.__setattr__(self, "baseline_parameters", baseline)
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "factor_scale_ids", factor_scale_ids)

    def to_dict(self) -> dict[str, object]:
        return {
            "experiment_id": self.experiment_id,
            "tool_id": self.tool_id,
            "carrier_frequency": self.carrier_frequency,
            "parameter_axis_id": self.parameter_axis_id,
            "parameter_ids": list(self.parameter_ids),
            "axis_kind": self.axis_kind,
            "coupling_rationale": self.coupling_rationale,
            "multiplicity_family_id": self.multiplicity_family_id,
            "maximum_candidate_count": self.maximum_candidate_count,
            "baseline_parameters": dict(self.baseline_parameters),
            "baseline_parameter_vector_digest": parameter_vector_digest(self.baseline_parameters),
            "candidates": [item.to_dict() for item in self.candidates],
            "adapter_binding_status": self.adapter_binding_status,
            "factor_scale_ids": list(self.factor_scale_ids),
            "time_scale_catalog_semantic_digest": self.time_scale_catalog_semantic_digest,
            "scale_binding_status": self.scale_binding_status,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "production_authority": self.production_authority,
        }


@dataclass(frozen=True, slots=True)
class DecisionBehaviorObservation:
    """One candidate's observed decision sequence, submitted after evaluation."""

    candidate_id: str
    experiment_id: str
    multiplicity_family_id: str
    behavior_digest: str

    def __post_init__(self) -> None:
        if not all(
            str(value).strip()
            for value in (
                self.candidate_id,
                self.experiment_id,
                self.multiplicity_family_id,
                self.behavior_digest,
            )
        ):
            raise ValidationError("behavior observation identity is required")
        if not self.behavior_digest.startswith("sha256:"):
            raise ValidationError("behavior observation requires a canonical digest")


@dataclass(frozen=True, slots=True)
class BehaviorDeduplicationResult:
    """One representative vote per multiplicity-family decision behavior."""

    rows: tuple[Mapping[str, object], ...]

    def __post_init__(self) -> None:
        rows = tuple(MappingProxyType(dict(item)) for item in self.rows)
        keys = {(str(item["multiplicity_family_id"]), str(item["behavior_digest"])) for item in rows}
        if len(keys) != len(rows):
            raise ValidationError("behavior deduplication result contains duplicate behavior groups")
        for item in rows:
            vote_weight = item.get("vote_weight")
            if isinstance(vote_weight, bool) or not isinstance(vote_weight, int) or vote_weight != 1:
                raise ValidationError("decision-equivalent candidates must contribute one vote")
        object.__setattr__(self, "rows", rows)

    def to_dict(self) -> dict[str, object]:
        return {
            "rows": [dict(item) for item in self.rows],
            "behavior_group_count": len(self.rows),
            "field_labels_zh": {
                "behavior_digest": "决策行为指纹",
                "representative_candidate_id": "等价行为代表候选",
                "equivalent_candidate_ids": "决策等价候选集合",
                "vote_weight": "多重检验中的独立投票权重",
            },
        }


@dataclass(frozen=True, slots=True)
class PrivateParameterMutationFinding:
    """A script-local replacement of the benchmark parameter mapping."""

    relative_path: str
    line_number: int
    call_name: str

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "line_number": self.line_number,
            "call_name": self.call_name,
        }


@dataclass(frozen=True, slots=True)
class PrivateParameterMutationAudit:
    """Static gate for unauthorized script-local parameter dictionaries."""

    findings: tuple[PrivateParameterMutationFinding, ...]

    @property
    def audit_status(self) -> str:
        return "passed" if not self.findings else "blocked"

    def to_dict(self) -> dict[str, object]:
        return {
            "audit_status": self.audit_status,
            "findings": [item.to_dict() for item in self.findings],
            "field_labels_zh": {
                "findings": "脚本绕过显式实验注册的参数字典替换",
                "line_number": "源码行号",
            },
        }


@dataclass(frozen=True, slots=True)
class ToolParameterExperimentRegistry:
    """A catalog-bound registry; empty is valid and remains the default."""

    catalog_semantic_digest: str
    time_scale_catalog_semantic_digest: str
    experiments: tuple[ToolParameterExperiment, ...]
    private_parameter_mutation_audit: PrivateParameterMutationAudit
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        if not self.catalog_semantic_digest.startswith("sha256:"):
            raise ValidationError("parameter experiment registry requires the catalog digest")
        if not self.time_scale_catalog_semantic_digest.startswith("sha256:"):
            raise ValidationError("parameter experiment registry requires the time-scale catalog digest")
        experiments = tuple(self.experiments)
        if len({item.experiment_id for item in experiments}) != len(experiments):
            raise ValidationError("parameter experiment registry has duplicate experiment identities")
        if any(item.time_scale_catalog_semantic_digest != self.time_scale_catalog_semantic_digest for item in experiments):
            raise ValidationError("parameter experiment registry contains an experiment from a different time-scale catalog")
        if any(item.dynamic_parameter_authority or item.tool_routing_authority or item.production_authority for item in experiments):
            raise ValidationError("parameter experiment registry cannot contain authorized experiments")
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("parameter experiment registry cannot grant authority")
        object.__setattr__(self, "experiments", experiments)

    def experiment(self, experiment_id: str) -> ToolParameterExperiment:
        for item in self.experiments:
            if item.experiment_id == experiment_id:
                return item
        raise ValidationError(f"unregistered parameter experiment: {experiment_id}")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": TOOL_PARAMETER_EXPERIMENT_SCHEMA_ID,
            "registry_version": TOOL_PARAMETER_EXPERIMENT_REGISTRY_VERSION,
            "catalog_semantic_digest": self.catalog_semantic_digest,
            "time_scale_catalog_semantic_digest": self.time_scale_catalog_semantic_digest,
            "candidate_budget_cap": MAXIMUM_CANDIDATES_PER_EXPERIMENT,
            "experiments": [item.to_dict() for item in self.experiments],
            "private_parameter_mutation_audit": self.private_parameter_mutation_audit.to_dict(),
            "scale_catalog_binding": "time_scale_catalog_v2_bound",
            "production_authority": self.production_authority,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "field_labels_zh": {
                "parameter_axis_id": "参数轴标识",
                "parameter_ids": "参数轴所含公式量",
                "axis_kind": "单轴或显式耦合轴",
                "parameter_vector_digest": "完整公式参数向量指纹",
                "adapter_binding_status": "现有适配器映射状态",
                "scale_binding_status": "时间尺度目录绑定状态",
                "factor_scale_ids": "正式因子尺度标识集合",
                "time_scale_catalog_semantic_digest": "正式时间尺度目录摘要",
            },
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload


def _catalog_parameter(
    catalog: ToolParameterCatalogV2,
    *,
    tool_id: str,
    parameter_id: str,
) -> ToolParameterSpecV2:
    parameter = catalog.parameter(tool_id, parameter_id)
    if parameter.identity_effect != "same_tool_parameter":
        raise ValidationError("only same-tool formula parameters may enter an experiment axis")
    if parameter.registration_status != "registered" or parameter.tunable_status != "not_searchable_yet":
        raise ValidationError("parameter is not eligible for explicit experiment registration")
    return parameter


def _baseline_parameter_vector(
    catalog: ToolParameterCatalogV2,
    *,
    tool_id: str,
    carrier_frequency: str,
    parameter_ids: Sequence[str],
) -> tuple[Mapping[str, Primitive], AdapterBindingStatus]:
    benchmark = next((item for item in tool_benchmark_specs() if item.tool_id == tool_id), None)
    if benchmark is None or carrier_frequency not in benchmark.parameters_by_frequency:
        raise ValidationError("experiment carrier frequency is not benchmarked for this tool")
    baseline = {
        key: _primitive(value, field=f"benchmark.{key}")
        for key, value in benchmark.parameters_by_frequency[carrier_frequency].items()
        if key != "cost_bps"
    }
    requires_adapter_extension = False
    for parameter_id in parameter_ids:
        parameter = _catalog_parameter(catalog, tool_id=tool_id, parameter_id=parameter_id)
        vector_key = parameter.v1_parameter_key or parameter.parameter_id
        if parameter.v1_parameter_key is None:
            requires_adapter_extension = True
        _ = baseline.setdefault(vector_key, parameter.native_default)
    return (
        _parameter_vector(baseline, field="benchmark baseline"),
        "adapter_extension_required" if requires_adapter_extension else "v1_adapter_complete",
    )


def _validated_candidate_value(parameter: ToolParameterSpecV2, value: object) -> Primitive:
    normalized = _primitive(value, field=f"{parameter.surface_id} candidate")
    if normalized not in parameter.allowed_domain:
        raise ValidationError(f"candidate is outside the registered domain: {parameter.surface_id}")
    return normalized


def _build_experiment(
    *,
    catalog: ToolParameterCatalogV2,
    tool_id: str,
    carrier_frequency: str,
    parameter_ids: tuple[str, ...],
    axis_kind: AxisKind,
    candidate_vectors: Sequence[Mapping[str, Primitive]],
    multiplicity_family_id: str,
    factor_scale_ids: Sequence[str],
    time_scale_catalog: TimeScaleCatalog | None = None,
    coupling_rationale: str = "",
) -> ToolParameterExperiment:
    active_time_scale_catalog = time_scale_catalog or build_time_scale_catalog_v2()
    canonical_scale_ids = tuple(sorted({active_time_scale_catalog.scale(scale_id).scale_id for scale_id in factor_scale_ids}))
    if not canonical_scale_ids:
        raise ValidationError("parameter experiment requires a registered factor scale")
    time_scale_catalog_digest = str(active_time_scale_catalog.to_dict()["semantic_digest"])
    baseline, adapter_binding_status = _baseline_parameter_vector(
        catalog,
        tool_id=tool_id,
        carrier_frequency=carrier_frequency,
        parameter_ids=parameter_ids,
    )
    parameter_axis_id = _parameter_axis_id(tool_id, parameter_ids)
    vectors = [baseline, *candidate_vectors]
    normalized_vectors = [_parameter_vector(item, field="registered candidate vector") for item in vectors]
    experiment_id = _experiment_id(
        tool_id=tool_id,
        carrier_frequency=carrier_frequency,
        parameter_axis_id=parameter_axis_id,
        parameter_ids=parameter_ids,
        baseline_parameters=baseline,
        candidate_parameters=normalized_vectors,
        multiplicity_family_id=multiplicity_family_id,
        axis_kind=axis_kind,
        coupling_rationale=coupling_rationale,
        factor_scale_ids=canonical_scale_ids,
        time_scale_catalog_semantic_digest=time_scale_catalog_digest,
    )
    candidates = tuple(
        ParameterExperimentCandidate(
            candidate_id="parameter-candidate:"
            + canonical_digest(
                {
                    "experiment_id": experiment_id,
                    "parameter_vector_digest": parameter_vector_digest(vector),
                }
            ).removeprefix("sha256:")[:24],
            experiment_id=experiment_id,
            parameters=vector,
            parameter_vector_digest=parameter_vector_digest(vector),
            is_baseline=index == 0,
        )
        for index, vector in enumerate(normalized_vectors)
    )
    return ToolParameterExperiment(
        experiment_id=experiment_id,
        tool_id=tool_id,
        carrier_frequency=carrier_frequency,
        parameter_axis_id=parameter_axis_id,
        parameter_ids=parameter_ids,
        axis_kind=axis_kind,
        coupling_rationale=coupling_rationale,
        multiplicity_family_id=multiplicity_family_id,
        maximum_candidate_count=MAXIMUM_CANDIDATES_PER_EXPERIMENT,
        baseline_parameters=baseline,
        candidates=candidates,
        adapter_binding_status=adapter_binding_status,
        factor_scale_ids=canonical_scale_ids,
        time_scale_catalog_semantic_digest=time_scale_catalog_digest,
    )


def register_single_parameter_experiment(
    *,
    catalog: ToolParameterCatalogV2,
    tool_id: str,
    carrier_frequency: str,
    parameter_id: str,
    candidate_values: Sequence[object],
    multiplicity_family_id: str,
    factor_scale_ids: Sequence[str],
    time_scale_catalog: TimeScaleCatalog | None = None,
) -> ToolParameterExperiment:
    """Create one explicit axis registration without granting execution rights."""

    parameter = _catalog_parameter(catalog, tool_id=tool_id, parameter_id=parameter_id)
    baseline, _adapter_status = _baseline_parameter_vector(
        catalog,
        tool_id=tool_id,
        carrier_frequency=carrier_frequency,
        parameter_ids=(parameter_id,),
    )
    vector_key = parameter.v1_parameter_key or parameter.parameter_id
    baseline_value = baseline[vector_key]
    values: list[Primitive] = []
    for raw_value in (baseline_value, *candidate_values):
        value = _validated_candidate_value(parameter, raw_value)
        if value not in values:
            values.append(value)
    if len(values) > MAXIMUM_CANDIDATES_PER_EXPERIMENT:
        raise ValidationError("single parameter registration exceeds the nine-candidate budget")
    candidates: list[Mapping[str, Primitive]] = []
    for value in values[1:]:
        vector = dict(baseline)
        vector[vector_key] = value
        candidates.append(vector)
    return _build_experiment(
        catalog=catalog,
        tool_id=tool_id,
        carrier_frequency=carrier_frequency,
        parameter_ids=(parameter_id,),
        axis_kind="single_parameter",
        candidate_vectors=candidates,
        multiplicity_family_id=multiplicity_family_id,
        factor_scale_ids=factor_scale_ids,
        time_scale_catalog=time_scale_catalog,
    )


def register_coupled_parameter_experiment(
    *,
    catalog: ToolParameterCatalogV2,
    tool_id: str,
    carrier_frequency: str,
    parameter_ids: Sequence[str],
    candidate_values: Sequence[Mapping[str, object]],
    multiplicity_family_id: str,
    coupling_rationale: str,
    factor_scale_ids: Sequence[str],
    time_scale_catalog: TimeScaleCatalog | None = None,
) -> ToolParameterExperiment:
    """Create a traceable multi-quantity registration; partial coupling is rejected."""

    axis_ids = tuple(sorted(set(parameter_ids)))
    if len(axis_ids) < 2:
        raise ValidationError("coupled registration needs at least two parameter ids")
    baseline, _adapter_status = _baseline_parameter_vector(
        catalog,
        tool_id=tool_id,
        carrier_frequency=carrier_frequency,
        parameter_ids=axis_ids,
    )
    if len(candidate_values) + 1 > MAXIMUM_CANDIDATES_PER_EXPERIMENT:
        raise ValidationError("coupled registration exceeds the nine-candidate budget")
    vectors: list[Mapping[str, Primitive]] = []
    for raw_values in candidate_values:
        if set(raw_values) != set(axis_ids):
            raise ValidationError("coupled candidate must name every and only declared parameter")
        vector = dict(baseline)
        for parameter_id in axis_ids:
            parameter = _catalog_parameter(catalog, tool_id=tool_id, parameter_id=parameter_id)
            vector[parameter.v1_parameter_key or parameter.parameter_id] = _validated_candidate_value(
                parameter,
                raw_values[parameter_id],
            )
        vectors.append(vector)
    return _build_experiment(
        catalog=catalog,
        tool_id=tool_id,
        carrier_frequency=carrier_frequency,
        parameter_ids=axis_ids,
        axis_kind="coupled_parameters",
        candidate_vectors=vectors,
        multiplicity_family_id=multiplicity_family_id,
        coupling_rationale=coupling_rationale,
        factor_scale_ids=factor_scale_ids,
        time_scale_catalog=time_scale_catalog,
    )


def build_tool_parameter_experiment_registry(
    *,
    project_root: Path | None = None,
    catalog: ToolParameterCatalogV2 | None = None,
    time_scale_catalog: TimeScaleCatalog | None = None,
) -> ToolParameterExperimentRegistry:
    """Build the empty V2 authority boundary after the formula audit passes.

    Deliberately no candidate is pre-registered here.  Selecting an axis or a
    candidate value is a later, explicit research decision; the registry only
    provides the fail-closed API for recording one.
    """

    root = project_root or _PROJECT_ROOT
    active_catalog = catalog or build_tool_parameter_catalog_v2()
    active_time_scale_catalog = time_scale_catalog or build_time_scale_catalog_v2()
    audit = audit_formula_surface(project_root=root, catalog=active_catalog)
    if audit.audit_status != "passed":
        raise ValidationError("formula surface audit must pass before experiment registration")
    return ToolParameterExperimentRegistry(
        catalog_semantic_digest=str(active_catalog.to_dict()["semantic_digest"]),
        time_scale_catalog_semantic_digest=str(active_time_scale_catalog.to_dict()["semantic_digest"]),
        experiments=(),
        private_parameter_mutation_audit=audit_private_parameter_mutations(root),
    )


def add_registered_experiment(
    registry: ToolParameterExperimentRegistry,
    experiment: ToolParameterExperiment,
    *,
    catalog: ToolParameterCatalogV2 | None = None,
    time_scale_catalog: TimeScaleCatalog | None = None,
) -> ToolParameterExperimentRegistry:
    """Add one explicit registration while preserving the zero-authority boundary."""

    if experiment.experiment_id in {item.experiment_id for item in registry.experiments}:
        raise ValidationError("parameter experiment is already registered")
    active_catalog = catalog or build_tool_parameter_catalog_v2()
    active_time_scale_catalog = time_scale_catalog or build_time_scale_catalog_v2()
    if str(active_catalog.to_dict()["semantic_digest"]) != registry.catalog_semantic_digest:
        raise ValidationError("parameter experiment registry is bound to a different catalog")
    if str(active_time_scale_catalog.to_dict()["semantic_digest"]) != registry.time_scale_catalog_semantic_digest:
        raise ValidationError("parameter experiment registry is bound to a different time-scale catalog")
    validate_registered_parameter_experiment(
        catalog=active_catalog,
        experiment=experiment,
        time_scale_catalog=active_time_scale_catalog,
    )
    return ToolParameterExperimentRegistry(
        catalog_semantic_digest=registry.catalog_semantic_digest,
        time_scale_catalog_semantic_digest=registry.time_scale_catalog_semantic_digest,
        experiments=(*registry.experiments, experiment),
        private_parameter_mutation_audit=registry.private_parameter_mutation_audit,
    )


def validate_registered_parameter_experiment(
    *,
    catalog: ToolParameterCatalogV2,
    experiment: ToolParameterExperiment,
    time_scale_catalog: TimeScaleCatalog | None = None,
) -> None:
    """Recheck a proposed registration against the audited catalog boundary."""

    expected_axis_id = _parameter_axis_id(experiment.tool_id, experiment.parameter_ids)
    if experiment.parameter_axis_id != expected_axis_id:
        raise ValidationError("experiment parameter axis identity does not match its declared parameters")
    expected_baseline, expected_adapter_status = _baseline_parameter_vector(
        catalog,
        tool_id=experiment.tool_id,
        carrier_frequency=experiment.carrier_frequency,
        parameter_ids=experiment.parameter_ids,
    )
    if dict(experiment.baseline_parameters) != dict(expected_baseline):
        raise ValidationError("experiment baseline was not sourced from the frozen benchmark")
    if experiment.adapter_binding_status != expected_adapter_status:
        raise ValidationError("experiment adapter binding status disagrees with its catalog mapping")
    active_time_scale_catalog = time_scale_catalog or build_time_scale_catalog_v2()
    expected_scale_catalog_digest = str(active_time_scale_catalog.to_dict()["semantic_digest"])
    if experiment.time_scale_catalog_semantic_digest != expected_scale_catalog_digest:
        raise ValidationError("experiment is bound to a different time-scale catalog")
    canonical_scale_ids = tuple(sorted({active_time_scale_catalog.scale(scale_id).scale_id for scale_id in experiment.factor_scale_ids}))
    if canonical_scale_ids != experiment.factor_scale_ids:
        raise ValidationError("experiment factor scale ids are not canonical")
    expected_experiment_id = _experiment_id(
        tool_id=experiment.tool_id,
        carrier_frequency=experiment.carrier_frequency,
        parameter_axis_id=experiment.parameter_axis_id,
        parameter_ids=experiment.parameter_ids,
        baseline_parameters=experiment.baseline_parameters,
        candidate_parameters=[item.parameters for item in experiment.candidates],
        multiplicity_family_id=experiment.multiplicity_family_id,
        axis_kind=experiment.axis_kind,
        coupling_rationale=experiment.coupling_rationale,
        factor_scale_ids=experiment.factor_scale_ids,
        time_scale_catalog_semantic_digest=experiment.time_scale_catalog_semantic_digest,
    )
    if experiment.experiment_id != expected_experiment_id:
        raise ValidationError("experiment identity does not match its registered content")
    for parameter_id in experiment.parameter_ids:
        parameter = _catalog_parameter(catalog, tool_id=experiment.tool_id, parameter_id=parameter_id)
        vector_key = parameter.v1_parameter_key or parameter.parameter_id
        for candidate in experiment.candidates:
            if not candidate.is_baseline and candidate.parameters[vector_key] not in parameter.allowed_domain:
                raise ValidationError("experiment candidate is outside the audited parameter domain")


def decision_behavior_digest(
    decision_records: Sequence[Mapping[str, object]],
) -> str:
    """Fingerprint a time-indexed target-position sequence, not performance."""

    normalized: list[dict[str, object]] = []
    seen_times: set[str] = set()
    for record in decision_records:
        decision_time = str(record.get("decision_time", ""))
        position = record.get("target_position")
        if not decision_time.strip() or decision_time in seen_times:
            raise ValidationError("behavior digest requires unique non-empty decision times")
        if isinstance(position, bool) or not isinstance(position, (int, float)) or not math.isfinite(float(position)):
            raise ValidationError("behavior digest requires finite numeric target positions")
        seen_times.add(decision_time)
        normalized.append({"decision_time": decision_time, "target_position": float(position)})
    if not normalized:
        raise ValidationError("behavior digest requires at least one decision record")
    return canonical_digest({"decision_records": sorted(normalized, key=lambda item: str(item["decision_time"]))})


def deduplicate_decision_behaviors(
    observations: Iterable[DecisionBehaviorObservation],
) -> BehaviorDeduplicationResult:
    """Compress behavior-equivalent parameter vectors to one vote per family."""

    grouped: dict[tuple[str, str], list[DecisionBehaviorObservation]] = {}
    for observation in observations:
        grouped.setdefault((observation.multiplicity_family_id, observation.behavior_digest), []).append(observation)
    rows: list[Mapping[str, object]] = []
    for (family_id, behavior_digest), group in sorted(grouped.items()):
        candidate_ids = tuple(sorted(item.candidate_id for item in group))
        rows.append(
            MappingProxyType(
                {
                    "multiplicity_family_id": family_id,
                    "behavior_digest": behavior_digest,
                    "representative_candidate_id": candidate_ids[0],
                    "equivalent_candidate_ids": list(candidate_ids),
                    "source_experiment_ids": sorted({item.experiment_id for item in group}),
                    "vote_weight": 1,
                }
            )
        )
    return BehaviorDeduplicationResult(rows=tuple(rows))


def _call_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return "unknown"


def audit_private_parameter_mutations(project_root: Path) -> PrivateParameterMutationAudit:
    """Detect script-local ``replace(..., parameters_by_frequency=...)`` bypasses."""

    findings: list[PrivateParameterMutationFinding] = []
    scripts_dir = project_root / "scripts"
    for path in sorted(scripts_dir.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            raise ValidationError(f"unable to audit script parameter mutation: {path}") from exc
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if any(keyword.arg == "parameters_by_frequency" for keyword in node.keywords):
                findings.append(
                    PrivateParameterMutationFinding(
                        relative_path=str(path.relative_to(project_root)),
                        line_number=node.lineno,
                        call_name=_call_name(node.func),
                    )
                )
    return PrivateParameterMutationAudit(findings=tuple(findings))


def validate_no_private_parameter_mutations(project_root: Path) -> None:
    """Fail closed if a script bypasses the explicit V2 registration surface."""

    audit = audit_private_parameter_mutations(project_root)
    if audit.findings:
        locations = ", ".join(f"{item.relative_path}:{item.line_number}" for item in audit.findings)
        raise ValidationError(f"script-local parameters_by_frequency mutation is blocked: {locations}")


__all__ = [
    "AdapterBindingStatus",
    "BehaviorDeduplicationResult",
    "DecisionBehaviorObservation",
    "MAXIMUM_CANDIDATES_PER_EXPERIMENT",
    "ParameterExperimentCandidate",
    "PrivateParameterMutationAudit",
    "PrivateParameterMutationFinding",
    "TOOL_PARAMETER_EXPERIMENT_REGISTRY_VERSION",
    "TOOL_PARAMETER_EXPERIMENT_SCHEMA_ID",
    "ToolParameterExperiment",
    "ToolParameterExperimentRegistry",
    "add_registered_experiment",
    "audit_private_parameter_mutations",
    "build_tool_parameter_experiment_registry",
    "decision_behavior_digest",
    "deduplicate_decision_behaviors",
    "parameter_vector_digest",
    "register_coupled_parameter_experiment",
    "register_single_parameter_experiment",
    "validate_registered_parameter_experiment",
    "validate_no_private_parameter_mutations",
]
