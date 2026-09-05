# pyright: reportAny=false, reportArgumentType=false
# pyright: reportAssignmentType=false, reportAttributeAccessIssue=false
# pyright: reportCallIssue=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false
# pyright: reportOperatorIssue=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Legacy implementation backend for Layer 3 tool-conditioned effects.

The current public authority is
``factor_lab.strategy.research.timing.conditional_effect_research``.  This
module remains at its historical path for source/digest and import compatibility;
it is not a Layer 2 measurement provider.

The preceding R2 layer asks whether a formula-derived factor can explain the
relative utility of two parameter profiles.  This module adds the missing
middle layer: it asks whether the relationship is stable *inside one concrete
tool* and whether the two mirrored parameter perturbations tell the same
directional story.

The implementation deliberately does not search new parameters or factors.
It consumes the pre-registered 3x3 parameter surface and out-of-time R2 fold
evidence.  Long-capture and cash-avoidance are algebraically duplicate views
of the same position disagreement and are therefore collapsed into one vote.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import product
from typing import ClassVar, Final, cast

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.time_scale_catalog import build_time_scale_catalog_v2
from factor_lab.market_state.tool_registry import DISCOVERED_TOOL_IDS

TOOL_CONDITIONED_RELATIONSHIP_SCHEMA_ID: Final[str] = "market_state_tool_conditioned_relationship_research@1.0"
TOOL_CONDITIONED_RELATIONSHIP_POLICY_VERSION: Final[str] = "tool_conditioned_mirrored_parameter_oos_v1"
EXPECTED_OUTER_FOLDS: Final[tuple[str, ...]] = (
    "outer_2013_2014",
    "outer_2015_2016",
    "outer_2017_2018",
    "outer_2019_2020",
)
EXPECTED_VALIDATION_YEARS: Final[tuple[int, ...]] = tuple(range(2013, 2021))
V2_RELATIONSHIP_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "parameter_axis_id",
    "experiment_id",
    "scale_id",
)


@dataclass(frozen=True, slots=True)
class MonotoneCoefficientExponentAlias:
    """Canonical vote identity for ``a * signed_power(F, b)`` variants."""

    coefficient: float
    exponent: float
    direction_sign: int
    alias_id: str
    representative_coefficient: float
    representative_exponent: float = 1.0
    independent_vote_count: int = 1

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "coefficient": self.coefficient,
            "exponent": self.exponent,
            "direction_sign": self.direction_sign,
            "alias_id": self.alias_id,
            "representative_coefficient": self.representative_coefficient,
            "representative_exponent": self.representative_exponent,
            "independent_vote_count": self.independent_vote_count,
        }


def normalize_coefficient_exponent_alias(
    coefficient: float,
    exponent: float,
) -> MonotoneCoefficientExponentAlias:
    """Collapse deterministic signed-power rescalings into one directional vote."""

    if (
        isinstance(coefficient, bool)
        or isinstance(exponent, bool)
        or not math.isfinite(float(coefficient))
        or not math.isfinite(float(exponent))
        or float(coefficient) == 0.0
        or float(exponent) <= 0.0
    ):
        raise ValidationError("coefficient/exponent alias requires a finite nonzero coefficient and positive exponent")
    direction_sign = 1 if coefficient > 0.0 else -1
    return MonotoneCoefficientExponentAlias(
        coefficient=float(coefficient),
        exponent=float(exponent),
        direction_sign=direction_sign,
        alias_id=("signed_power_monotone_increasing" if direction_sign > 0 else "signed_power_monotone_decreasing"),
        representative_coefficient=float(direction_sign),
    )


@dataclass(frozen=True, slots=True)
class ParameterExperimentRelationshipKey:
    """V2 relationship identity, replacing V1's abstract 3x3 coordinates.

    Existing V1 result artifacts continue to use ``timescale_level`` and
    ``shape_level`` so they can replay byte-for-byte.  New V2 evidence must
    use this key after its explicit experiment registration and, in stage 4,
    its causal scale binding are available.
    """

    parameter_axis_id: str
    experiment_id: str
    scale_id: str

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (self.parameter_axis_id, self.experiment_id, self.scale_id)):
            raise ValidationError("V2 relationship identity fields are required")
        if not self.experiment_id.startswith("parameter-experiment:"):
            raise ValidationError("V2 relationship key requires a registered parameter experiment")
        scale = build_time_scale_catalog_v2().scale(self.scale_id)
        if scale.scale_id != self.scale_id:
            raise ValidationError("V2 relationship key requires a canonical factor scale id")

    def to_dict(self) -> dict[str, str]:
        return {
            "parameter_axis_id": self.parameter_axis_id,
            "experiment_id": self.experiment_id,
            "scale_id": self.scale_id,
        }


@dataclass(frozen=True, slots=True)
class ToolConditionedRelationshipPolicy:
    """Frozen gates for one-tool, one-axis relationship certification."""

    minimum_adequate_outer_folds: int = 3
    minimum_direction_consistent_outer_folds: int = 3
    minimum_positive_uplift_outer_folds: int = 3
    minimum_coefficient_consistent_outer_folds: int = 3
    minimum_shape_family_consistent_outer_folds: int = 3
    required_validation_years: int = 8
    maximum_positive_contribution_concentration: float = 0.70
    maximum_material_reverse_fraction: float = 0.10
    maximum_material_reverse_outer_folds: int = 1
    minimum_single_factor_conditional_hit_rate: float = 0.70
    moderate_single_factor_conditional_hit_rate: float = 0.80
    strong_single_factor_conditional_hit_rate: float = 0.90
    very_strong_single_factor_conditional_hit_rate: float = 0.95
    minimum_selector_nonzero_decisions: int = 20
    minimum_selector_decision_outer_folds: int = 3
    minimum_validation_years_for_partial_association: int = 6
    minimum_positive_validation_year_fraction: float = 0.70
    mirror_replication_pvalue: float = 0.10
    within_tool_fdr_level: float = 0.10
    tool_omnibus_fdr_level: float = 0.10
    diagonal_minimum_eligible_candidates: int = 3
    diagonal_systematic_contradiction_fraction: float = 0.75
    role_equivalence_tolerance: float = 1e-12

    def __post_init__(self) -> None:
        integer_gates = (
            self.minimum_adequate_outer_folds,
            self.minimum_direction_consistent_outer_folds,
            self.minimum_positive_uplift_outer_folds,
            self.minimum_coefficient_consistent_outer_folds,
            self.minimum_shape_family_consistent_outer_folds,
        )
        if any(value < 3 for value in integer_gates):
            raise ValidationError("tool-conditioned fold gates must be at least 3/4")
        if self.required_validation_years != len(EXPECTED_VALIDATION_YEARS):
            raise ValidationError("tool-conditioned layer requires all 8 OOS years")
        for value in (
            self.maximum_positive_contribution_concentration,
            self.maximum_material_reverse_fraction,
            self.minimum_positive_validation_year_fraction,
            self.mirror_replication_pvalue,
            self.within_tool_fdr_level,
            self.tool_omnibus_fdr_level,
            self.diagonal_systematic_contradiction_fraction,
        ):
            if not 0.0 < value < 1.0:
                raise ValidationError("tool-conditioned probability gates must be in (0,1)")
        if self.diagonal_minimum_eligible_candidates < 3:
            raise ValidationError("diagonal challenge requires at least three candidates")
        if self.maximum_material_reverse_outer_folds not in {0, 1}:
            raise ValidationError("single-factor layer may tolerate at most one bad fold")
        consistency_thresholds = (
            self.minimum_single_factor_conditional_hit_rate,
            self.moderate_single_factor_conditional_hit_rate,
            self.strong_single_factor_conditional_hit_rate,
            self.very_strong_single_factor_conditional_hit_rate,
        )
        if tuple(sorted(consistency_thresholds)) != consistency_thresholds:
            raise ValidationError("single-factor consistency tiers must be ordered")
        if not all(0.5 < value < 1.0 for value in consistency_thresholds):
            raise ValidationError("single-factor consistency tiers must be in (0.5,1)")
        if self.minimum_selector_nonzero_decisions < 20:
            raise ValidationError("single-factor association needs at least 20 decisions")
        if self.minimum_selector_decision_outer_folds < 3:
            raise ValidationError("single-factor decisions must span at least 3 folds")
        if self.minimum_validation_years_for_partial_association < 6:
            raise ValidationError("single-factor association needs at least 6 OOS years")

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_version": TOOL_CONDITIONED_RELATIONSHIP_POLICY_VERSION,
            "research_range": ["2009-01-01", "2020-12-31"],
            "sealed_blackbox": ["2021-01-01", "2026-12-31"],
            "primary_comparison": ("same_tool_same_frequency_axis_pure_mirror_vs_frozen_baseline"),
            "primary_axes": ["timescale", "shape"],
            "primary_axis_coordinates": [
                [-1, 0],
                [1, 0],
                [0, -1],
                [0, 1],
            ],
            "diagonal_coordinates_are_challenge_only": True,
            "action_role_vote_rule": ("long_capture_and_cash_avoidance_are_one_algebraic_vote"),
            "canonical_action_role": "long_capture",
            "outer_fold_ids": list(EXPECTED_OUTER_FOLDS),
            "validation_calendar_years": list(EXPECTED_VALIDATION_YEARS),
            "minimum_adequate_outer_folds": self.minimum_adequate_outer_folds,
            "minimum_direction_consistent_outer_folds": (self.minimum_direction_consistent_outer_folds),
            "minimum_positive_uplift_outer_folds": (self.minimum_positive_uplift_outer_folds),
            "minimum_coefficient_consistent_outer_folds": (self.minimum_coefficient_consistent_outer_folds),
            "minimum_shape_family_consistent_outer_folds": (self.minimum_shape_family_consistent_outer_folds),
            "required_validation_years": self.required_validation_years,
            "maximum_positive_contribution_concentration": (self.maximum_positive_contribution_concentration),
            "maximum_material_reverse_fraction": (self.maximum_material_reverse_fraction),
            "maximum_material_reverse_outer_folds": (self.maximum_material_reverse_outer_folds),
            "single_factor_inference_contract": {
                "unobserved_factor_interference_is_expected": True,
                "minimum_conditional_hit_rate": (self.minimum_single_factor_conditional_hit_rate),
                "consistency_tiers": {
                    "partial_70_80": [
                        self.minimum_single_factor_conditional_hit_rate,
                        self.moderate_single_factor_conditional_hit_rate,
                    ],
                    "moderate_80_90": [
                        self.moderate_single_factor_conditional_hit_rate,
                        self.strong_single_factor_conditional_hit_rate,
                    ],
                    "strong_90_95": [
                        self.strong_single_factor_conditional_hit_rate,
                        self.very_strong_single_factor_conditional_hit_rate,
                    ],
                    "very_strong_95_plus": [
                        self.very_strong_single_factor_conditional_hit_rate,
                        1.0,
                    ],
                },
                "minimum_selector_nonzero_decisions": (self.minimum_selector_nonzero_decisions),
                "minimum_selector_decision_outer_folds": (self.minimum_selector_decision_outer_folds),
                "minimum_validation_years": (self.minimum_validation_years_for_partial_association),
                "minimum_positive_validation_year_fraction": (self.minimum_positive_validation_year_fraction),
                "perfect_event_prediction_required": False,
            },
            "future_multifactor_contract": {
                "all_exceptions_must_be_accounted_for": True,
                "perfect_event_prediction_required": False,
                "irreducible_noise_must_remain_explicit": True,
            },
            "mirror_replication_pvalue": self.mirror_replication_pvalue,
            "within_tool_fdr_level": self.within_tool_fdr_level,
            "tool_omnibus_fdr_level": self.tool_omnibus_fdr_level,
            "diagonal_minimum_eligible_candidates": (self.diagonal_minimum_eligible_candidates),
            "diagonal_systematic_contradiction_fraction": (self.diagonal_systematic_contradiction_fraction),
            "role_equivalence_tolerance": self.role_equivalence_tolerance,
            "relationship_rule": (
                "single-factor event consistency is tiered at 70/80/90/95; "
                "two mirrored sides agree; annual OOS sign-flip passes; "
                "within-tool BH and across-tool omnibus BH pass"
            ),
            "dynamic_parameter_authority": False,
            "tool_routing_authority": False,
            "production_authority": False,
        }


@dataclass(frozen=True, slots=True)
class ToolConditionedRelationshipResult:
    """Complete evidence bundle for the tool-conditioned middle layer."""

    policy: ToolConditionedRelationshipPolicy
    role_deduplication_audit: pd.DataFrame
    role_deduplicated_fold_evidence: pd.DataFrame
    hypothesis_fold_evidence: pd.DataFrame
    primary_side_summary: pd.DataFrame
    diagonal_candidate_summary: pd.DataFrame
    diagonal_challenge_summary: pd.DataFrame
    relationship_matrix: pd.DataFrame
    tool_summary: pd.DataFrame
    hypothesis_registry: tuple[Mapping[str, object], ...]
    data_usage_ledger: Mapping[str, object]

    schema_id: ClassVar[str] = TOOL_CONDITIONED_RELATIONSHIP_SCHEMA_ID

    def __post_init__(self) -> None:
        if self.data_usage_ledger.get("post_2020_rows_used") != 0:
            raise ValidationError("tool-conditioned layer opened the blackbox")
        if set(self.tool_summary["tool_id"]) != set(DISCOVERED_TOOL_IDS):
            raise ValidationError("tool-conditioned layer does not cover all 13 tools")
        if not bool(self.role_deduplication_audit["roles_equivalent"].all()):
            raise ValidationError("dual action roles were counted as independent votes")
        if self.relationship_matrix.empty:
            raise ValidationError("tool-conditioned relationship matrix is empty")

    def authority_payload(self) -> dict[str, object]:
        statuses = self.relationship_matrix["relationship_status"].value_counts()
        stable = self.relationship_matrix.loc[self.relationship_matrix["relationship_status"].eq("stable_tool_conditioned_relation")]
        supported_primary_sides = int(self.primary_side_summary["candidate_gate_pass"].sum())
        mirror_base_gate_count = int(self.relationship_matrix["mirror_base_gate_pass"].sum())
        mirror_replication_gate_count = int(self.relationship_matrix["mirror_replication_gate_pass"].sum())
        one_side_clue_count = int(self.relationship_matrix["one_side_supported_only"].sum())
        supported_diagonal_candidates = int(self.diagonal_candidate_summary["candidate_gate_pass"].sum())
        tier_counts = self.primary_side_summary["single_factor_consistency_tier"].value_counts()
        qualified_sides = self.primary_side_summary.loc[self.primary_side_summary["candidate_gate_pass"].eq(True)]
        return {
            "schema_id": self.schema_id,
            "research_status": "completed_tool_conditioned_relationship_audit",
            "policy": self.policy.to_dict(),
            "tool_count": int(self.tool_summary["tool_id"].nunique()),
            "tool_frequency_lens_count": int(self.relationship_matrix[["tool_id", "carrier_frequency"]].drop_duplicates().shape[0]),
            "hypothesis_count": len(self.relationship_matrix),
            "stable_relationship_count": len(stable),
            "stable_tool_count": int(stable["tool_id"].nunique()),
            "qualified_single_factor_side_association_count": len(qualified_sides),
            "independent_qualified_side_association_count": int(qualified_sides["association_evidence_id"].nunique()),
            "failure_stage_counts": {
                "primary_side_candidate_count": len(self.primary_side_summary),
                "supported_primary_side_count": supported_primary_sides,
                "no_supported_side_relationship_count": int(self.relationship_matrix["supported_mirror_side_count"].eq(0).sum()),
                "one_supported_side_only_relationship_count": (one_side_clue_count),
                "two_supported_sides_relationship_count": int(self.relationship_matrix["supported_mirror_side_count"].eq(2).sum()),
                "mirror_base_gate_count": mirror_base_gate_count,
                "mirror_replication_gate_count": (mirror_replication_gate_count),
                "supported_diagonal_candidate_count": (supported_diagonal_candidates),
                "stable_relationship_count": len(stable),
            },
            "single_factor_consistency_tier_counts": {str(key): int(value) for key, value in tier_counts.items()},
            "status_counts": {str(key): int(value) for key, value in statuses.items()},
            "tool_summary": self.tool_summary.to_dict(orient="records"),
            "data_usage_ledger": dict(self.data_usage_ledger),
            "field_labels_zh": {
                "tool_id": "择时工具",
                "carrier_frequency": "载体周期",
                "parameter_axis": "参数语义轴",
                "factor_id": "K线属性",
                "primary_scale_id": "属性尺度",
                "coefficient_relation_direction": "稳定方向",
                "annual_oos_uplift_mean": "逐年样本外改善",
                "single_factor_conditional_hit_rate": "单因子条件命中率",
                "single_factor_consistency_tier": "单因子一致率层级",
                "association_evidence_id": "独立决策证据标识",
                "within_tool_qvalue": "工具内多重检验q值",
                "tool_omnibus_qvalue": "13工具总检验q值",
                "relationship_status": "关系结论",
            },
            "relationship_evidence_is_not_routing_rule": True,
            "dynamic_parameter_authority": False,
            "tool_routing_authority": False,
            "production_authority": False,
        }


def _json_object(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return {}
    parsed = json.loads(str(value))
    if not isinstance(parsed, dict):
        raise ValidationError("expected a JSON object")
    return cast(dict[str, object], parsed)


def _shape_family(shape: str) -> str:
    if shape in {"absolute", "square"}:
        return "magnitude"
    if shape in {
        "linear",
        "signed_square_root",
        "signed_logarithmic",
        "signed_square",
        "cube",
        "saturation",
    }:
        return "signed_monotone"
    return "unknown"


def single_factor_consistency_tier(
    hit_rate: float,
    *,
    policy: ToolConditionedRelationshipPolicy | None = None,
) -> str:
    """Classify empirical OOS decisions without demanding perfect prediction."""

    cfg = policy or ToolConditionedRelationshipPolicy()
    if not math.isfinite(hit_rate):
        return "insufficient"
    if hit_rate >= cfg.very_strong_single_factor_conditional_hit_rate:
        return "very_strong_95_plus"
    if hit_rate >= cfg.strong_single_factor_conditional_hit_rate:
        return "strong_90_95"
    if hit_rate >= cfg.moderate_single_factor_conditional_hit_rate:
        return "moderate_80_90"
    if hit_rate >= cfg.minimum_single_factor_conditional_hit_rate:
        return "partial_70_80"
    return "below_70"


def exact_sign_flip_pvalue(values: Sequence[float]) -> float:
    """One-sided complete sign enumeration over independent time blocks."""

    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if len(finite) == 0 or float(np.mean(finite)) <= 0.0:
        return 1.0
    observed = float(np.mean(finite))
    exceed = 0
    total = 0
    for signs in product((-1.0, 1.0), repeat=len(finite)):
        total += 1
        candidate = float(np.mean(finite * np.asarray(signs, dtype=float)))
        if candidate >= observed - 1e-15:
            exceed += 1
    return float(exceed / total)


def bh_qvalues(pvalues: pd.Series) -> pd.Series:
    """Benjamini-Hochberg correction preserving the original row index."""

    if pvalues.empty:
        return pd.Series(dtype=float, index=pvalues.index)
    values = pvalues.fillna(1.0).clip(0.0, 1.0).to_numpy(dtype=float)
    order = np.argsort(values)
    ordered = values[order]
    adjusted = np.empty(len(values), dtype=float)
    running = 1.0
    for position in range(len(values) - 1, -1, -1):
        running = min(
            running,
            ordered[position] * len(values) / (position + 1),
        )
        adjusted[position] = running
    result = np.empty(len(values), dtype=float)
    result[order] = adjusted
    return pd.Series(result, index=pvalues.index)


def simes_pvalue(values: Sequence[float]) -> float:
    """Simes omnibus p-value for one pre-registered tool family."""

    pvalues = np.sort(np.clip(np.asarray(values, dtype=float), 0.0, 1.0))
    if len(pvalues) == 0:
        return 1.0
    ranks = np.arange(1, len(pvalues) + 1, dtype=float)
    return float(min(1.0, np.min(pvalues * len(pvalues) / ranks)))


def _semantic_pair_id(row: Mapping[str, object]) -> str:
    body = {
        "pair_type": str(row["pair_type"]),
        "candidate_a_id": str(row["candidate_a_id"]),
        "candidate_b_id": str(row["candidate_b_id"]),
        "carrier_frequency": str(row["carrier_frequency"]),
    }
    return "semantic-pair:" + canonical_digest(body).removeprefix("sha256:")[:24]


def _parameter_pair_frame(
    pair_registry: Sequence[Mapping[str, object]],
    candidates: Sequence[Mapping[str, object]],
) -> pd.DataFrame:
    pairs = pd.DataFrame([dict(item) for item in pair_registry])
    pairs = pairs.loc[pairs["pair_type"].eq("parameter")].copy()
    if pairs.empty:
        raise ValidationError("tool-conditioned layer requires parameter pairs")
    pairs["semantic_pair_id"] = [_semantic_pair_id(cast(Mapping[str, object], row)) for row in pairs.to_dict(orient="records")]
    candidate_frame = pd.DataFrame([dict(item) for item in candidates])
    required = {
        "candidate_id",
        "tool_id",
        "carrier_frequency",
        "timescale_level",
        "shape_level",
        "timescale_semantics",
        "shape_semantics",
        "parameters",
        "baseline",
    }
    if not required.issubset(candidate_frame.columns):
        raise ValidationError("fixed candidate dictionary is incomplete")
    candidate_a = candidate_frame.add_prefix("candidate_a_")
    candidate_b = candidate_frame.add_prefix("candidate_b_")
    pairs = pairs.merge(
        candidate_a,
        left_on="candidate_a_id",
        right_on="candidate_a_candidate_id",
        how="left",
        validate="many_to_one",
    ).merge(
        candidate_b,
        left_on="candidate_b_id",
        right_on="candidate_b_candidate_id",
        how="left",
        validate="many_to_one",
    )
    if (
        pairs["candidate_a_tool_id"].isna().any()
        or not bool(pairs["candidate_b_baseline"].eq(True).all())
        or not bool(pairs["candidate_b_timescale_level"].eq(0).all())
        or not bool(pairs["candidate_b_shape_level"].eq(0).all())
    ):
        raise ValidationError("parameter pairs are not anchored to the baseline")
    return pairs


def _role_deduplication_audit(
    events: pd.DataFrame,
    pairs: pd.DataFrame,
    *,
    policy: ToolConditionedRelationshipPolicy,
) -> pd.DataFrame:
    pair_lookup = pairs[["pair_id", "semantic_pair_id", "action_role"]].drop_duplicates()
    selected = events.merge(
        pair_lookup,
        on=["pair_id", "action_role"],
        how="inner",
        validate="many_to_one",
    )
    rows: list[dict[str, object]] = []
    for semantic_pair_id, group in selected.groupby(
        "semantic_pair_id",
        sort=True,
    ):
        by_role = {
            str(role): role_frame.sort_values(["event_start_time", "event_end_time"]).reset_index(drop=True)
            for role, role_frame in group.groupby("action_role", sort=True)
        }
        long_frame = by_role.get("long_capture", pd.DataFrame())
        cash_frame = by_role.get("cash_avoidance", pd.DataFrame())
        boundaries_equal = bool(
            len(long_frame) == len(cash_frame)
            and long_frame[["event_start_time", "event_end_time"]].equals(cash_frame[["event_start_time", "event_end_time"]])
        )
        max_target_difference = math.inf
        if boundaries_equal and len(long_frame):
            difference = pd.to_numeric(
                long_frame["event_net_delta_a_minus_b"],
                errors="coerce",
            ).to_numpy(dtype=float) - pd.to_numeric(
                cash_frame["event_net_delta_a_minus_b"],
                errors="coerce",
            ).to_numpy(dtype=float)
            max_target_difference = float(np.nanmax(np.abs(difference)))
        elif boundaries_equal:
            max_target_difference = 0.0
        equivalent = bool(boundaries_equal and max_target_difference <= policy.role_equivalence_tolerance)
        rows.append(
            {
                "semantic_pair_id": str(semantic_pair_id),
                "long_capture_event_count": len(long_frame),
                "cash_avoidance_event_count": len(cash_frame),
                "event_boundaries_equal": boundaries_equal,
                "maximum_target_difference": max_target_difference,
                "roles_equivalent": equivalent,
                "independent_vote_count_after_collapse": 1,
                "production_authority": False,
            }
        )
    audit = pd.DataFrame(rows)
    expected = set(pairs["semantic_pair_id"])
    observed = set(audit["semantic_pair_id"]) if not audit.empty else set()
    for semantic_pair_id in sorted(expected - observed):
        rows.append(
            {
                "semantic_pair_id": str(semantic_pair_id),
                "long_capture_event_count": 0,
                "cash_avoidance_event_count": 0,
                "event_boundaries_equal": True,
                "maximum_target_difference": 0.0,
                "roles_equivalent": True,
                "independent_vote_count_after_collapse": 1,
                "production_authority": False,
            }
        )
    audit = pd.DataFrame(rows)
    if set(audit["semantic_pair_id"]) != expected:
        raise ValidationError("role audit does not cover every parameter comparison")
    if not bool(audit["roles_equivalent"].all()):
        raise ValidationError("long/cash event targets are not algebraically equivalent")
    return audit


def _values_equivalent(
    group: pd.DataFrame,
    column: str,
    *,
    tolerance: float,
) -> bool:
    values = group[column]
    if column.endswith("_json") or column == "selected_shapes":
        payloads = [_json_object(value) for value in values]
        if not payloads:
            return True
        if any(set(payload) != set(payloads[0]) for payload in payloads[1:]):
            return False
        for key in payloads[0]:
            key_values = [payload[key] for payload in payloads]
            if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in key_values):
                if not bool(
                    np.allclose(
                        np.asarray(key_values, dtype=float),
                        np.repeat(float(key_values[0]), len(key_values)),
                        atol=tolerance,
                        rtol=0.0,
                        equal_nan=True,
                    )
                ):
                    return False
            elif len({str(value) for value in key_values}) != 1:
                return False
        return True
    if pd.api.types.is_numeric_dtype(values):
        numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
        return bool(
            np.allclose(
                numeric,
                np.repeat(numeric[:1], len(numeric)),
                atol=tolerance,
                rtol=0.0,
                equal_nan=True,
            )
        )

    def normalized_value(value: object) -> str:
        return json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)

    normalized = values.map(normalized_value)
    return bool(normalized.nunique(dropna=False) == 1)


def _collapse_action_roles(
    folds: pd.DataFrame,
    pairs: pd.DataFrame,
    materialization: pd.DataFrame,
    *,
    policy: ToolConditionedRelationshipPolicy,
) -> pd.DataFrame:
    required = {
        "train_factor_coefficients_json",
        "train_factor_coefficient_signs_json",
        "validation_year_uplift_mean_json",
        "selected_shapes",
        "validation_direction_correct_count",
        "validation_fixed_champion_correct_count",
        "validation_direction_accuracy_lift",
        "validation_selector_decision_count",
        "validation_selector_nonzero_decision_count",
        "validation_selector_correct_decision_count",
        "validation_selector_incorrect_decision_count",
        "validation_selector_decision_coverage",
    }
    if not required.issubset(folds.columns):
        raise ValidationError("R2 fold evidence predates coefficient persistence")
    pair_columns = [
        "pair_id",
        "semantic_pair_id",
        "candidate_a_id",
        "candidate_b_id",
        "candidate_a_timescale_level",
        "candidate_a_shape_level",
        "candidate_a_timescale_semantics",
        "candidate_a_shape_semantics",
        "candidate_a_parameters",
        "candidate_b_parameters",
    ]
    joined = folds.merge(
        pairs[pair_columns],
        on="pair_id",
        how="inner",
        validate="many_to_one",
    ).merge(
        materialization[
            [
                "mechanism_id",
                "factor_id",
                "proxy_family_id",
                "expected_relation",
                "primary_scale_id",
            ]
        ],
        on=["mechanism_id", "factor_id"],
        how="left",
        validate="many_to_one",
    )
    if bool(joined["primary_scale_id"].isna().any()):
        raise ValidationError("factor evidence is missing formula materialization")
    identity = [
        "semantic_pair_id",
        "outer_fold_id",
        "mechanism_id",
        "factor_id",
    ]
    # Model fits are intentionally not compared here.  The event-level audit
    # above proves that both roles have the same target.  Re-fitting that same
    # target twice can still choose different shapes at numerical ties; using
    # either fit as a second vote would be pseudo-replication.  We therefore
    # verify only the raw fold support and select long_capture as the single
    # canonical fit.
    evidence_columns = [
        "adequate_support",
        "train_event_count",
        "validation_event_count",
        "validation_target_abs_mean",
    ]
    rows: list[dict[str, object]] = []
    for _, group in joined.groupby(identity, sort=True, dropna=False):
        if set(group["action_role"]) != {"long_capture", "cash_avoidance"}:
            raise ValidationError("an R2 fold does not contain both action roles")
        if not all(
            _values_equivalent(
                group,
                column,
                tolerance=policy.role_equivalence_tolerance,
            )
            for column in evidence_columns
        ):
            raise ValidationError("dual action roles disagree in R2 fold evidence")
        canonical = group.loc[group["action_role"].eq("long_capture")].iloc[0]
        row = canonical.to_dict()
        row["pair_ids_json"] = json.dumps(
            sorted(str(value) for value in group["pair_id"].unique()),
            ensure_ascii=True,
        )
        row["action_role"] = "role_collapsed"
        row["role_duplicate_verified"] = True
        rows.append(row)
    result = pd.DataFrame(rows)
    if result.empty:
        raise ValidationError("role-deduplicated fold evidence is empty")
    return result


def _collapse_duplicate_formula_mappings(
    folds: pd.DataFrame,
    *,
    policy: ToolConditionedRelationshipPolicy,
) -> pd.DataFrame:
    identity = [
        "semantic_pair_id",
        "outer_fold_id",
        "factor_id",
        "primary_scale_id",
    ]
    evidence_columns = [
        "adequate_support",
        "selected_shapes",
        "train_factor_coefficients_json",
        "train_factor_coefficient_signs_json",
        "validation_year_uplift_mean_json",
        "validation_rank_correlation",
        "validation_direction_correct_count",
        "validation_fixed_champion_correct_count",
        "validation_fixed_champion_direction_accuracy",
        "validation_direction_accuracy_lift",
        "validation_net_uplift_mean",
        "validation_selector_decision_count",
        "validation_selector_nonzero_decision_count",
        "validation_selector_correct_decision_count",
        "validation_selector_incorrect_decision_count",
        "validation_selector_decision_coverage",
        "validation_positive_contribution_concentration",
        "validation_target_abs_mean",
        "simple_close_to_flexible",
    ]
    rows: list[dict[str, object]] = []
    for _, group in folds.groupby(identity, sort=True, dropna=False):
        if not all(
            _values_equivalent(
                group,
                column,
                tolerance=policy.role_equivalence_tolerance,
            )
            for column in evidence_columns
        ):
            raise ValidationError("duplicate mechanism mappings disagree for one factor/scale")
        row = group.iloc[0].to_dict()
        row["mechanism_ids_json"] = json.dumps(
            sorted(str(value) for value in group["mechanism_id"].unique()),
            ensure_ascii=True,
        )
        row["proxy_family_ids_json"] = json.dumps(
            sorted(str(value) for value in group["proxy_family_id"].unique()),
            ensure_ascii=True,
        )
        row["expected_relations_json"] = json.dumps(
            sorted(str(value) for value in group["expected_relation"].unique()),
            ensure_ascii=True,
        )
        row["formula_mapping_vote_count_after_collapse"] = 1
        rows.append(row)
    return pd.DataFrame(rows)


def _dominant_value(values: Sequence[object]) -> tuple[object, int]:
    counts: dict[object, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    if not counts:
        return "", 0
    return sorted(counts.items(), key=lambda item: (-item[1], str(item[0])))[0]


def _candidate_summary(
    folds: pd.DataFrame,
    *,
    policy: ToolConditionedRelationshipPolicy,
) -> pd.DataFrame:
    identity = [
        "tool_a_id",
        "carrier_frequency",
        "semantic_pair_id",
        "candidate_a_id",
        "candidate_b_id",
        "factor_id",
        "primary_scale_id",
    ]
    rows: list[dict[str, object]] = []
    for values, group in folds.groupby(identity, sort=True, dropna=False):
        key = dict(zip(identity, cast(tuple[object, ...], values), strict=True))
        if set(group["outer_fold_id"]) != set(EXPECTED_OUTER_FOLDS):
            raise ValidationError("candidate relationship does not cover four folds")
        adequate = group.loc[group["adequate_support"].eq(True)].copy()
        coefficient_signs: list[int] = []
        shapes: list[str] = []
        shape_families: list[str] = []
        years: dict[int, float] = {}
        for _, fold in adequate.iterrows():
            factor_id = str(fold["factor_id"])
            sign_payload = _json_object(fold["train_factor_coefficient_signs_json"])
            coefficient_signs.append(int(sign_payload.get(factor_id, 0)))
            shape_payload = _json_object(fold["selected_shapes"])
            shape = str(shape_payload.get(factor_id, "unknown"))
            shapes.append(shape)
            shape_families.append(_shape_family(shape))
            for raw_year, raw_uplift in _json_object(fold["validation_year_uplift_mean_json"]).items():
                years[int(raw_year)] = float(raw_uplift)
        nonzero_signs = [value for value in coefficient_signs if value != 0]
        dominant_sign_raw, coefficient_consistent = _dominant_value(nonzero_signs)
        dominant_shape, shape_count = _dominant_value(shapes)
        dominant_shape_family, shape_family_count = _dominant_value(shape_families)
        correlations = pd.to_numeric(
            adequate["validation_rank_correlation"],
            errors="coerce",
        )
        uplifts = pd.to_numeric(
            adequate["validation_net_uplift_mean"],
            errors="coerce",
        )
        targets = pd.to_numeric(
            adequate["validation_target_abs_mean"],
            errors="coerce",
        )
        concentrations = pd.to_numeric(
            adequate["validation_positive_contribution_concentration"],
            errors="coerce",
        )
        validation_event_count = int(
            pd.to_numeric(
                adequate["validation_event_count"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )
        direction_correct_count = int(
            pd.to_numeric(
                adequate["validation_direction_correct_count"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )
        fixed_direction_correct_count = int(
            pd.to_numeric(
                adequate["validation_fixed_champion_correct_count"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )
        selector_decision_count = int(
            pd.to_numeric(
                adequate["validation_selector_decision_count"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )
        selector_nonzero_decision_count = int(
            pd.to_numeric(
                adequate["validation_selector_nonzero_decision_count"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )
        selector_correct_decision_count = int(
            pd.to_numeric(
                adequate["validation_selector_correct_decision_count"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )
        selector_incorrect_decision_count = int(
            pd.to_numeric(
                adequate["validation_selector_incorrect_decision_count"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )
        selector_decision_outer_fold_count = int(
            pd.to_numeric(
                adequate["validation_selector_nonzero_decision_count"],
                errors="coerce",
            )
            .fillna(0)
            .gt(0)
            .sum()
        )
        conditional_hit_rate = (
            float(selector_correct_decision_count / selector_nonzero_decision_count) if selector_nonzero_decision_count else math.nan
        )
        direction_accuracy = float(direction_correct_count / validation_event_count) if validation_event_count else math.nan
        fixed_direction_accuracy = float(fixed_direction_correct_count / validation_event_count) if validation_event_count else math.nan
        direction_accuracy_lift = (
            direction_accuracy - fixed_direction_accuracy
            if math.isfinite(direction_accuracy) and math.isfinite(fixed_direction_accuracy)
            else math.nan
        )
        validation_year_count = len(years)
        positive_validation_year_count = sum(value > 0.0 for value in years.values())
        positive_validation_year_fraction = (
            float(positive_validation_year_count / validation_year_count) if validation_year_count else math.nan
        )
        consistency_tier = single_factor_consistency_tier(
            conditional_hit_rate,
            policy=policy,
        )
        material_reverse = uplifts.lt(-policy.maximum_material_reverse_fraction * targets.clip(lower=1e-12))
        direction_count = int(correlations.gt(0.0).sum())
        positive_count = int(uplifts.gt(0.0).sum())
        simple_count = int(adequate["simple_close_to_flexible"].eq(True).sum())
        candidate_gate = bool(
            len(adequate) >= policy.minimum_adequate_outer_folds
            and positive_count >= policy.minimum_positive_uplift_outer_folds
            and float(uplifts.median()) > 0.0
            and int(material_reverse.sum()) <= policy.maximum_material_reverse_outer_folds
            and (concentrations.dropna().empty or float(concentrations.median()) <= policy.maximum_positive_contribution_concentration)
            and simple_count >= policy.minimum_direction_consistent_outer_folds
            and coefficient_consistent >= policy.minimum_coefficient_consistent_outer_folds
            and shape_family_count >= policy.minimum_shape_family_consistent_outer_folds
            and selector_nonzero_decision_count >= policy.minimum_selector_nonzero_decisions
            and selector_decision_outer_fold_count >= policy.minimum_selector_decision_outer_folds
            and conditional_hit_rate >= policy.minimum_single_factor_conditional_hit_rate
            and direction_accuracy_lift > 0.0
            and validation_year_count >= policy.minimum_validation_years_for_partial_association
            and positive_validation_year_fraction >= policy.minimum_positive_validation_year_fraction
        )
        first = group.iloc[0]
        rows.append(
            {
                **key,
                "timescale_level": int(first["candidate_a_timescale_level"]),
                "shape_level": int(first["candidate_a_shape_level"]),
                "timescale_semantics": str(first["candidate_a_timescale_semantics"]),
                "shape_semantics": str(first["candidate_a_shape_semantics"]),
                "candidate_parameters_json": json.dumps(
                    _json_object(first["candidate_a_parameters"]),
                    ensure_ascii=True,
                    sort_keys=True,
                ),
                "baseline_parameters_json": json.dumps(
                    _json_object(first["candidate_b_parameters"]),
                    ensure_ascii=True,
                    sort_keys=True,
                ),
                "mechanism_ids_json": str(first["mechanism_ids_json"]),
                "proxy_family_ids_json": str(first["proxy_family_ids_json"]),
                "expected_relations_json": str(first["expected_relations_json"]),
                "adequate_outer_fold_count": len(adequate),
                "direction_consistent_outer_fold_count": direction_count,
                "positive_uplift_outer_fold_count": positive_count,
                "simple_close_outer_fold_count": simple_count,
                "material_reverse_outer_fold_count": int(material_reverse.sum()),
                "coefficient_nonzero_outer_fold_count": len(nonzero_signs),
                "coefficient_consistent_outer_fold_count": int(coefficient_consistent),
                "dominant_raw_coefficient_sign": int(dominant_sign_raw or 0),
                "dominant_selected_shape": str(dominant_shape),
                "selected_shape_consistent_outer_fold_count": int(shape_count),
                "dominant_shape_family": str(dominant_shape_family),
                "shape_family_consistent_outer_fold_count": int(shape_family_count),
                "median_validation_rank_correlation": (float(correlations.median()) if len(correlations) else math.nan),
                "median_validation_net_uplift_mean": (float(uplifts.median()) if len(uplifts) else math.nan),
                "median_positive_contribution_concentration": (
                    float(concentrations.median()) if len(concentrations.dropna()) else math.nan
                ),
                "validation_event_count_total": validation_event_count,
                "validation_direction_correct_count_total": (direction_correct_count),
                "validation_fixed_champion_correct_count_total": (fixed_direction_correct_count),
                "validation_direction_accuracy": direction_accuracy,
                "validation_fixed_champion_direction_accuracy": (fixed_direction_accuracy),
                "validation_direction_accuracy_lift": (direction_accuracy_lift),
                "selector_decision_count_total": selector_decision_count,
                "selector_nonzero_decision_count_total": (selector_nonzero_decision_count),
                "selector_correct_decision_count_total": (selector_correct_decision_count),
                "selector_incorrect_decision_count_total": (selector_incorrect_decision_count),
                "selector_decision_outer_fold_count": (selector_decision_outer_fold_count),
                "selector_decision_coverage": (
                    float(selector_decision_count / validation_event_count) if validation_event_count else math.nan
                ),
                "single_factor_conditional_hit_rate": conditional_hit_rate,
                "single_factor_consistency_tier": consistency_tier,
                "validation_year_count": validation_year_count,
                "positive_validation_year_count": (positive_validation_year_count),
                "positive_validation_year_fraction": (positive_validation_year_fraction),
                "annual_oos_uplift_mean_json": json.dumps(
                    {str(year): years[year] for year in sorted(years)},
                    ensure_ascii=True,
                    sort_keys=True,
                ),
                "candidate_gate_pass": candidate_gate,
                "candidate_status": (
                    "single_factor_partial_association"
                    if candidate_gate
                    else ("insufficient_support" if len(adequate) < policy.minimum_adequate_outer_folds else "candidate_rejected")
                ),
                "production_authority": False,
            }
        )
    result = pd.DataFrame(rows)

    def evidence_signature(row: pd.Series) -> str:
        def rounded(value: object) -> float | None:
            numeric = float(value)
            return round(numeric, 12) if math.isfinite(numeric) else None

        payload = {
            "tool_id": str(row["tool_a_id"]),
            "carrier_frequency": str(row["carrier_frequency"]),
            "candidate_a_id": str(row["candidate_a_id"]),
            "candidate_b_id": str(row["candidate_b_id"]),
            "primary_scale_id": str(row["primary_scale_id"]),
            "adequate_outer_fold_count": int(row["adequate_outer_fold_count"]),
            "dominant_raw_coefficient_sign": int(row["dominant_raw_coefficient_sign"]),
            "dominant_selected_shape": str(row["dominant_selected_shape"]),
            "selector_nonzero_decision_count_total": int(row["selector_nonzero_decision_count_total"]),
            "selector_correct_decision_count_total": int(row["selector_correct_decision_count_total"]),
            "selector_incorrect_decision_count_total": int(row["selector_incorrect_decision_count_total"]),
            "selector_decision_outer_fold_count": int(row["selector_decision_outer_fold_count"]),
            "single_factor_conditional_hit_rate": rounded(row["single_factor_conditional_hit_rate"]),
            "positive_validation_year_fraction": rounded(row["positive_validation_year_fraction"]),
            "validation_direction_accuracy_lift": rounded(row["validation_direction_accuracy_lift"]),
            "annual_oos_uplift_mean": {key: rounded(value) for key, value in _json_object(row["annual_oos_uplift_mean_json"]).items()},
        }
        return "association-evidence:" + canonical_digest(payload).removeprefix("sha256:")[:24]

    result["association_evidence_id"] = result.apply(
        evidence_signature,
        axis=1,
    )
    return result


def _axis_projection(
    candidates: pd.DataFrame,
    *,
    primary_only: bool,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, candidate in candidates.iterrows():
        timescale = int(candidate["timescale_level"])
        shape = int(candidate["shape_level"])
        axes: list[tuple[str, int]] = []
        if timescale != 0 and (shape == 0 or not primary_only):
            axes.append(("timescale", timescale))
        if shape != 0 and (timescale == 0 or not primary_only):
            axes.append(("shape", shape))
        for axis, side in axes:
            row = candidate.to_dict()
            raw_sign = int(row["dominant_raw_coefficient_sign"])
            row["parameter_axis"] = axis
            row["axis_side"] = side
            row["normalized_coefficient_sign"] = raw_sign * side
            row["axis_semantics"] = str(row["timescale_semantics" if axis == "timescale" else "shape_semantics"])
            rows.append(row)
    return pd.DataFrame(rows)


def _relationship_id(row: Mapping[str, object]) -> str:
    body = {
        key: row[key]
        for key in (
            "tool_a_id",
            "carrier_frequency",
            "parameter_axis",
            "factor_id",
            "primary_scale_id",
        )
    }
    return "tool-relation:" + canonical_digest(body).removeprefix("sha256:")[:24]


def _mirror_relationships(
    sides: pd.DataFrame,
    *,
    policy: ToolConditionedRelationshipPolicy,
) -> pd.DataFrame:
    identity = [
        "tool_a_id",
        "carrier_frequency",
        "parameter_axis",
        "factor_id",
        "primary_scale_id",
    ]
    rows: list[dict[str, object]] = []
    for values, group in sides.groupby(identity, sort=True, dropna=False):
        key = dict(zip(identity, cast(tuple[object, ...], values), strict=True))
        side_index = {int(row["axis_side"]): row for row in group.to_dict(orient="records")}
        negative = side_index.get(-1)
        positive = side_index.get(1)
        side_count = int(negative is not None) + int(positive is not None)
        supported_count = sum(bool(item["candidate_gate_pass"]) for item in (negative, positive) if item is not None)
        signs = [
            int(item["normalized_coefficient_sign"])
            for item in (negative, positive)
            if item is not None and bool(item["candidate_gate_pass"])
        ]
        sign_agreement = bool(len(signs) == 2 and signs[0] != 0 and signs[0] == signs[1])
        shape_families = [
            str(item["dominant_shape_family"]) for item in (negative, positive) if item is not None and bool(item["candidate_gate_pass"])
        ]
        shape_family_agreement = bool(
            len(shape_families) == 2 and shape_families[0] == shape_families[1] and shape_families[0] != "unknown"
        )
        side_hit_rates = {
            side: float(item["single_factor_conditional_hit_rate"])
            for side, item in ((-1, negative), (1, positive))
            if item is not None and math.isfinite(float(item["single_factor_conditional_hit_rate"]))
        }
        supported_hit_rates = [
            float(item["single_factor_conditional_hit_rate"])
            for item in (negative, positive)
            if item is not None and bool(item["candidate_gate_pass"])
        ]
        relationship_hit_rate_floor = min(supported_hit_rates) if supported_hit_rates else math.nan
        annual_values: dict[int, list[float]] = {}
        for item in (negative, positive):
            if item is None:
                continue
            for raw_year, raw_value in _json_object(item["annual_oos_uplift_mean_json"]).items():
                annual_values.setdefault(int(raw_year), []).append(float(raw_value))
        annual_median = {
            year: float(np.median(values_for_year)) for year, values_for_year in sorted(annual_values.items()) if values_for_year
        }
        complete_years = set(annual_median) == set(EXPECTED_VALIDATION_YEARS)
        block_values = np.asarray(
            [annual_median.get(year, math.nan) for year in EXPECTED_VALIDATION_YEARS],
            dtype=float,
        )
        positive_values = block_values[np.isfinite(block_values) & (block_values > 0.0)]
        block_concentration = (
            float(np.max(positive_values) / np.sum(positive_values))
            if len(positive_values) and float(np.sum(positive_values)) > 0.0
            else 0.0
        )
        base_gate = bool(
            side_count == 2
            and supported_count == 2
            and sign_agreement
            and shape_family_agreement
            and complete_years
            and block_concentration <= policy.maximum_positive_contribution_concentration
        )
        pvalue = exact_sign_flip_pvalue(block_values) if base_gate else 1.0
        replication_gate = bool(base_gate and pvalue <= policy.mirror_replication_pvalue)
        normalized_sign = signs[0] if sign_agreement else 0
        shape_family = shape_families[0] if shape_family_agreement else "mixed"
        relation_subject = "factor_magnitude" if shape_family == "magnitude" else "factor_level"
        relation_direction = (
            f"{relation_subject}_increase_favors_axis_increase"
            if normalized_sign > 0
            else (f"{relation_subject}_increase_favors_axis_decrease" if normalized_sign < 0 else "undetermined")
        )
        exemplar = negative or positive
        if exemplar is None:
            raise ValidationError("mirror hypothesis has no parameter side")
        relation_id = _relationship_id(key)
        rows.append(
            {
                "relationship_id": relation_id,
                "tool_id": key["tool_a_id"],
                "carrier_frequency": key["carrier_frequency"],
                "parameter_axis": key["parameter_axis"],
                "axis_semantics": str(exemplar["axis_semantics"]),
                "factor_id": key["factor_id"],
                "primary_scale_id": key["primary_scale_id"],
                "mechanism_ids_json": str(exemplar["mechanism_ids_json"]),
                "proxy_family_ids_json": str(exemplar["proxy_family_ids_json"]),
                "expected_relations_json": str(exemplar["expected_relations_json"]),
                "negative_candidate_id": (str(negative["candidate_a_id"]) if negative is not None else ""),
                "positive_candidate_id": (str(positive["candidate_a_id"]) if positive is not None else ""),
                "baseline_candidate_id": str(exemplar["candidate_b_id"]),
                "mirror_side_count": side_count,
                "supported_mirror_side_count": supported_count,
                "mirror_coefficient_sign_agreement": sign_agreement,
                "mirror_shape_family_agreement": shape_family_agreement,
                "negative_side_conditional_hit_rate": side_hit_rates.get(
                    -1,
                    math.nan,
                ),
                "positive_side_conditional_hit_rate": side_hit_rates.get(
                    1,
                    math.nan,
                ),
                "supported_side_conditional_hit_rate_floor": (relationship_hit_rate_floor),
                "single_factor_consistency_tier": (
                    single_factor_consistency_tier(
                        relationship_hit_rate_floor,
                        policy=policy,
                    )
                ),
                "dominant_shape_family": shape_family,
                "normalized_coefficient_sign": normalized_sign,
                "coefficient_relation_direction": relation_direction,
                "validation_year_count": int(np.isfinite(block_values).sum()),
                "positive_validation_year_count": int(np.sum(block_values > 0.0)),
                "annual_oos_uplift_mean": float(np.nanmean(block_values)) if bool(np.isfinite(block_values).any()) else math.nan,
                "annual_oos_uplift_median": float(np.nanmedian(block_values)) if bool(np.isfinite(block_values).any()) else math.nan,
                "annual_oos_uplift_json": json.dumps(
                    {str(year): annual_median[year] for year in sorted(annual_median)},
                    ensure_ascii=True,
                    sort_keys=True,
                ),
                "positive_year_contribution_concentration": (block_concentration),
                "one_sided_exact_sign_flip_pvalue": pvalue,
                "mirror_base_gate_pass": base_gate,
                "mirror_replication_gate_pass": replication_gate,
                "one_side_supported_only": supported_count == 1,
                "production_authority": False,
            }
        )
    return pd.DataFrame(rows)


def _diagonal_challenges(
    relationships: pd.DataFrame,
    diagonal_candidates: pd.DataFrame,
    *,
    policy: ToolConditionedRelationshipPolicy,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, relation in relationships.iterrows():
        candidates = diagonal_candidates.loc[
            diagonal_candidates["tool_a_id"].eq(relation["tool_id"])
            & diagonal_candidates["carrier_frequency"].eq(relation["carrier_frequency"])
            & diagonal_candidates["parameter_axis"].eq(relation["parameter_axis"])
            & diagonal_candidates["factor_id"].eq(relation["factor_id"])
            & diagonal_candidates["primary_scale_id"].eq(relation["primary_scale_id"])
        ]
        eligible = candidates.loc[candidates["candidate_gate_pass"].eq(True)]
        primary_sign = int(relation["normalized_coefficient_sign"])
        contradiction = (
            eligible["normalized_coefficient_sign"].eq(-primary_sign)
            if primary_sign
            else pd.Series(
                False,
                index=eligible.index,
            )
        )
        contradiction_count = int(contradiction.sum())
        fraction = float(contradiction_count / len(eligible)) if len(eligible) else 0.0
        systematic = bool(
            len(eligible) >= policy.diagonal_minimum_eligible_candidates and fraction >= policy.diagonal_systematic_contradiction_fraction
        )
        rows.append(
            {
                "relationship_id": str(relation["relationship_id"]),
                "diagonal_candidate_count": len(candidates),
                "eligible_diagonal_candidate_count": len(eligible),
                "contradicting_diagonal_candidate_count": contradiction_count,
                "contradicting_diagonal_candidate_fraction": fraction,
                "systematic_diagonal_contradiction": systematic,
                "diagonal_challenge_status": (
                    "systematic_contradiction"
                    if systematic
                    else (
                        "no_systematic_contradiction"
                        if len(eligible) >= policy.diagonal_minimum_eligible_candidates
                        else "insufficient_challenge_evidence"
                    )
                ),
                "production_authority": False,
            }
        )
    return pd.DataFrame(rows)


def _apply_multiplicity_and_status(
    relationships: pd.DataFrame,
    challenges: pd.DataFrame,
    *,
    policy: ToolConditionedRelationshipPolicy,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    matrix = relationships.merge(
        challenges,
        on="relationship_id",
        how="left",
        validate="one_to_one",
        suffixes=("", "_challenge"),
    )
    matrix["within_tool_qvalue"] = 1.0
    for _, index in matrix.groupby("tool_id", sort=True).groups.items():
        selected = list(index)
        matrix.loc[selected, "within_tool_qvalue"] = bh_qvalues(matrix.loc[selected, "one_sided_exact_sign_flip_pvalue"])
    matrix["global_qvalue"] = bh_qvalues(matrix["one_sided_exact_sign_flip_pvalue"])
    tool_rows: list[dict[str, object]] = []
    for tool_id in DISCOVERED_TOOL_IDS:
        group = matrix.loc[matrix["tool_id"].eq(tool_id)]
        omnibus = simes_pvalue(group["one_sided_exact_sign_flip_pvalue"].to_numpy(dtype=float))
        tool_rows.append(
            {
                "tool_id": tool_id,
                "hypothesis_count": len(group),
                "mirror_replication_gate_count": int(group["mirror_replication_gate_pass"].sum()),
                "tool_omnibus_simes_pvalue": omnibus,
                "production_authority": False,
            }
        )
    tools = pd.DataFrame(tool_rows)
    tools["tool_omnibus_qvalue"] = bh_qvalues(tools["tool_omnibus_simes_pvalue"])
    matrix = matrix.merge(
        tools[["tool_id", "tool_omnibus_qvalue"]],
        on="tool_id",
        how="left",
        validate="many_to_one",
    )

    def status(row: pd.Series) -> str:
        if bool(row["systematic_diagonal_contradiction"]):
            return "rejected"
        if bool(row["mirror_replication_gate_pass"]):
            if (
                float(row["within_tool_qvalue"]) <= policy.within_tool_fdr_level
                and float(row["tool_omnibus_qvalue"]) <= policy.tool_omnibus_fdr_level
            ):
                return "stable_tool_conditioned_relation"
            return "replicated_but_multiplicity_unconfirmed"
        if bool(row["one_side_supported_only"]):
            return "one_sided_single_factor_association"
        if int(row["supported_mirror_side_count"]) == 0:
            return "insufficient_support"
        return "rejected"

    matrix["relationship_status"] = matrix.apply(status, axis=1)
    matrix["relationship_evidence_authority"] = False
    matrix["dynamic_parameter_authority"] = False
    matrix["tool_routing_authority"] = False
    matrix["production_authority"] = False
    stable_counts = matrix["relationship_status"].eq("stable_tool_conditioned_relation").groupby(matrix["tool_id"]).sum()
    replicated_counts = matrix["mirror_replication_gate_pass"].groupby(matrix["tool_id"]).sum()
    tools["stable_relationship_count"] = tools["tool_id"].map(stable_counts).fillna(0).astype(int)
    tools["replicated_relationship_count"] = tools["tool_id"].map(replicated_counts).fillna(0).astype(int)
    tools["tool_conditioned_relationship_authority"] = False
    tools["tool_routing_authority"] = False
    return matrix.sort_values(["tool_id", "carrier_frequency", "parameter_axis", "factor_id"]).reset_index(drop=True), tools


def _hypothesis_registry(
    matrix: pd.DataFrame,
    sides: pd.DataFrame,
) -> tuple[Mapping[str, object], ...]:
    rows: list[Mapping[str, object]] = []
    for _, relation in matrix.iterrows():
        selected = sides.loc[
            sides["tool_a_id"].eq(relation["tool_id"])
            & sides["carrier_frequency"].eq(relation["carrier_frequency"])
            & sides["parameter_axis"].eq(relation["parameter_axis"])
            & sides["factor_id"].eq(relation["factor_id"])
            & sides["primary_scale_id"].eq(relation["primary_scale_id"])
        ]
        by_side = {int(row["axis_side"]): row for row in selected.to_dict(orient="records")}
        exemplar = next(iter(by_side.values()))
        rows.append(
            {
                "relationship_id": str(relation["relationship_id"]),
                "tool_id": str(relation["tool_id"]),
                "carrier_frequency": str(relation["carrier_frequency"]),
                "parameter_axis": str(relation["parameter_axis"]),
                "axis_semantics": str(relation["axis_semantics"]),
                "factor_id": str(relation["factor_id"]),
                "primary_scale_id": str(relation["primary_scale_id"]),
                "mechanism_ids": list(_json_object(exemplar["mechanism_ids_json"]).values())
                if str(exemplar["mechanism_ids_json"]).startswith("{")
                else json.loads(str(exemplar["mechanism_ids_json"])),
                "proxy_family_ids": json.loads(str(exemplar["proxy_family_ids_json"])),
                "negative_candidate": (
                    {
                        "candidate_id": str(by_side[-1]["candidate_a_id"]),
                        "parameters": _json_object(by_side[-1]["candidate_parameters_json"]),
                    }
                    if -1 in by_side
                    else None
                ),
                "baseline_candidate": {
                    "candidate_id": str(exemplar["candidate_b_id"]),
                    "parameters": _json_object(exemplar["baseline_parameters_json"]),
                },
                "positive_candidate": (
                    {
                        "candidate_id": str(by_side[1]["candidate_a_id"]),
                        "parameters": _json_object(by_side[1]["candidate_parameters_json"]),
                    }
                    if 1 in by_side
                    else None
                ),
                "hypothesis_frozen_before_tool_conditioned_testing": True,
                "production_authority": False,
            }
        )
    return tuple(rows)


def build_tool_conditioned_relationships(
    *,
    pair_registry: Sequence[Mapping[str, object]],
    candidates: Sequence[Mapping[str, object]],
    event_panel: pd.DataFrame,
    factor_materialization: pd.DataFrame,
    individual_fold_evidence: pd.DataFrame,
    policy: ToolConditionedRelationshipPolicy | None = None,
) -> ToolConditionedRelationshipResult:
    """Build the missing tool-specific relationship-certification layer."""

    cfg = policy or ToolConditionedRelationshipPolicy()
    pairs = _parameter_pair_frame(pair_registry, candidates)
    role_audit = _role_deduplication_audit(
        event_panel,
        pairs,
        policy=cfg,
    )
    role_dedup = _collapse_action_roles(
        individual_fold_evidence,
        pairs,
        factor_materialization,
        policy=cfg,
    )
    hypothesis_folds = _collapse_duplicate_formula_mappings(
        role_dedup,
        policy=cfg,
    )
    candidate_summary = _candidate_summary(
        hypothesis_folds,
        policy=cfg,
    )
    primary_mask = candidate_summary["timescale_level"].ne(0) ^ candidate_summary["shape_level"].ne(0)
    diagonal_mask = candidate_summary["timescale_level"].ne(0) & candidate_summary["shape_level"].ne(0)
    primary_sides = _axis_projection(
        candidate_summary.loc[primary_mask].copy(),
        primary_only=True,
    )
    diagonal_candidates = _axis_projection(
        candidate_summary.loc[diagonal_mask].copy(),
        primary_only=False,
    )
    relationships = _mirror_relationships(primary_sides, policy=cfg)
    challenges = _diagonal_challenges(
        relationships,
        diagonal_candidates,
        policy=cfg,
    )
    matrix, tool_summary = _apply_multiplicity_and_status(
        relationships,
        challenges,
        policy=cfg,
    )
    registry = _hypothesis_registry(matrix, primary_sides)
    ledger = {
        "schema_id": "market_state_tool_conditioned_data_usage@1.0",
        "research_start": "2009-01-01",
        "research_end_exclusive": "2021-01-01",
        "base_r2_event_rows_consumed": len(event_panel),
        "base_r2_fold_rows_consumed": len(individual_fold_evidence),
        "derived_market_data_rows_read": 0,
        "post_2020_rows_used": 0,
        "blackbox_detail_opened": False,
        "production_authority": False,
    }
    return ToolConditionedRelationshipResult(
        policy=cfg,
        role_deduplication_audit=role_audit,
        role_deduplicated_fold_evidence=role_dedup,
        hypothesis_fold_evidence=hypothesis_folds,
        primary_side_summary=primary_sides,
        diagonal_candidate_summary=diagonal_candidates,
        diagonal_challenge_summary=challenges,
        relationship_matrix=matrix,
        tool_summary=tool_summary,
        hypothesis_registry=registry,
        data_usage_ledger=ledger,
    )
