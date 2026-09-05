"""Deterministic parameter-profile contrasts over synthetic formula fixtures."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isclose, isfinite

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.formula_derivation.compiler import (
    Scalar,
    execute_formula_graph,
)
from factor_lab.market_state.formula_derivation.models import (
    FormulaComputationGraph,
    ParameterContrastDerivation,
)


@dataclass(frozen=True, slots=True)
class ParameterProfile:
    """One frozen formula parameter profile."""

    profile_id: str
    values: Mapping[str, Scalar]

    def __post_init__(self) -> None:
        if not self.profile_id.strip() or not self.values:
            raise ValidationError("parameter profile identity and values are required")
        if any(not key.strip() for key in self.values):
            raise ValidationError("parameter profile keys are invalid")
        if any(isinstance(value, float) and not isfinite(value) for value in self.values.values()):
            raise ValidationError("parameter profile values must be finite")

    @property
    def semantic_digest(self) -> str:
        return canonical_digest(
            {"profile_id": self.profile_id, "values": dict(sorted(self.values.items()))}
        )


@dataclass(frozen=True, slots=True)
class ParameterContrastEvaluation:
    """Direct ΔY/ΔP, action disagreement, margin, and atomic contributions."""

    baseline_outputs: tuple[float, ...]
    candidate_outputs: tuple[float, ...]
    delta_outputs: tuple[float, ...]
    delta_parameters: Mapping[str, float]
    action_disagreements: tuple[bool, ...]
    candidate_boundary_margins: tuple[float, ...]
    atomic_contributions: Mapping[str, tuple[float, ...]]
    synthetic_fixture_row_count: int
    market_data_rows_read: int = 0
    return_rows_read: int = 0

    def __post_init__(self) -> None:
        width = self.synthetic_fixture_row_count
        series = (
            self.baseline_outputs,
            self.candidate_outputs,
            self.delta_outputs,
            self.action_disagreements,
            self.candidate_boundary_margins,
        )
        if width < 1 or any(len(values) != width for values in series):
            raise ValidationError("parameter contrast series do not reconcile to fixture rows")
        if any(len(values) != width for values in self.atomic_contributions.values()):
            raise ValidationError("parameter contrast atomic contribution width changed")
        if self.market_data_rows_read != 0 or self.return_rows_read != 0:
            raise ValidationError("parameter contrasts can use synthetic fixtures only")
        for baseline, candidate, delta in zip(
            self.baseline_outputs,
            self.candidate_outputs,
            self.delta_outputs,
            strict=True,
        ):
            if not isclose(candidate - baseline, delta, rel_tol=0.0, abs_tol=1e-12):
                raise ValidationError("parameter contrast ΔY does not reconcile")

    def to_dict(self) -> dict[str, object]:
        return {
            "baseline_outputs": list(self.baseline_outputs),
            "candidate_outputs": list(self.candidate_outputs),
            "delta_outputs": list(self.delta_outputs),
            "delta_parameters": dict(sorted(self.delta_parameters.items())),
            "action_disagreements": list(self.action_disagreements),
            "candidate_boundary_margins": list(self.candidate_boundary_margins),
            "atomic_contributions": {
                key: list(values) for key, values in sorted(self.atomic_contributions.items())
            },
            "synthetic_fixture_row_count": self.synthetic_fixture_row_count,
            "market_data_rows_read": self.market_data_rows_read,
            "return_rows_read": self.return_rows_read,
        }


def derive_parameter_contrast(
    graph: FormulaComputationGraph,
    *,
    baseline: ParameterProfile,
    candidate: ParameterProfile,
    synthetic_rows: Sequence[Mapping[str, Scalar]],
    action_threshold: float = 0.0,
) -> tuple[ParameterContrastDerivation, ParameterContrastEvaluation]:
    """Compute an auditable profile contrast without reading empirical rows."""

    if len(graph.output_node_ids) != 1:
        raise ValidationError("parameter contrast currently requires one graph output")
    if not synthetic_rows:
        raise ValidationError("parameter contrast requires a deterministic synthetic fixture")
    if set(baseline.values) != set(candidate.values):
        raise ValidationError("parameter contrast profiles must share the same parameter keys")
    if not isfinite(action_threshold):
        raise ValidationError("parameter contrast action threshold must be finite")

    baseline_outputs = _outputs(graph, synthetic_rows, baseline.values)
    candidate_outputs = _outputs(graph, synthetic_rows, candidate.values)
    deltas = tuple(
        candidate_value - baseline_value
        for baseline_value, candidate_value in zip(
            baseline_outputs, candidate_outputs, strict=True
        )
    )
    delta_parameters = {
        key: _numeric(candidate.values[key]) - _numeric(baseline.values[key])
        for key in baseline.values
        if candidate.values[key] != baseline.values[key]
    }
    atomic: dict[str, tuple[float, ...]] = {}
    for parameter_id in delta_parameters:
        hybrid = dict(baseline.values)
        hybrid[parameter_id] = candidate.values[parameter_id]
        hybrid_outputs = _outputs(graph, synthetic_rows, hybrid)
        atomic[parameter_id] = tuple(
            hybrid_value - baseline_value
            for baseline_value, hybrid_value in zip(
                baseline_outputs, hybrid_outputs, strict=True
            )
        )
    disagreements = tuple(
        (baseline_value >= action_threshold) != (candidate_value >= action_threshold)
        for baseline_value, candidate_value in zip(
            baseline_outputs, candidate_outputs, strict=True
        )
    )
    margins = tuple(abs(value - action_threshold) for value in candidate_outputs)
    contrast = ParameterContrastDerivation(
        contrast_id=(
            "contrast:"
            + canonical_digest(
                {
                    "graph": graph.to_dict()["semantic_digest"],
                    "baseline": baseline.semantic_digest,
                    "candidate": candidate.semantic_digest,
                    "threshold": action_threshold,
                }
            ).removeprefix("sha256:")[:24]
        ),
        baseline_profile_id=baseline.profile_id,
        candidate_profile_id=candidate.profile_id,
        delta_output_expression="candidate_output-baseline_output",
        delta_parameter_expression="candidate_parameters-baseline_parameters",
        action_disagreement_predicate=f"(baseline>={action_threshold})!=(candidate>={action_threshold})",
        boundary_margin_expression=f"abs(candidate-{action_threshold})",
        atomic_contributions={
            parameter_id: "one-at-a-time candidate substitution over frozen baseline"
            for parameter_id in atomic
        },
        exactness="deterministic_numeric",
    )
    evaluation = ParameterContrastEvaluation(
        baseline_outputs=baseline_outputs,
        candidate_outputs=candidate_outputs,
        delta_outputs=deltas,
        delta_parameters=delta_parameters,
        action_disagreements=disagreements,
        candidate_boundary_margins=margins,
        atomic_contributions=atomic,
        synthetic_fixture_row_count=len(synthetic_rows),
    )
    return contrast, evaluation


def _outputs(
    graph: FormulaComputationGraph,
    rows: Sequence[Mapping[str, Scalar]],
    parameters: Mapping[str, Scalar],
) -> tuple[float, ...]:
    output_id = graph.output_node_ids[0]
    return tuple(
        _numeric(
            execute_formula_graph(
                graph,
                kline_fields=row,
                parameters=parameters,
            )[output_id]
        )
        for row in rows
    )


def _numeric(value: Scalar) -> float:
    return float(value)


__all__ = [
    "ParameterContrastEvaluation",
    "ParameterProfile",
    "derive_parameter_contrast",
]
