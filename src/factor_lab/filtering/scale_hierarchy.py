# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Cycle-scale hierarchy rules for multi-period filter strategies.

Bar period coarseness (day vs 60min) is not enough to decide whether one
filtered cycle can govern another.  A 1.5-day cycle and a 1-day cycle are close
in scale even if they appear on different bar periods.  This module defines the
cycle-ratio contract used to decide whether a candidate cycle is a valid
structural higher-level candidate for an execution cycle.

The ratio window is a research prior, not an optimizer.  Final higher-gate
parameters must be selected downstream with train/validation/test or
walk-forward evidence and a收益/回撤 trade-off objective.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Literal

ScaleRelation = Literal[
    "lower_or_equal",
    "same_level",
    "transition_buffer",
    "higher_level",
    "too_far",
]

DEFAULT_SAME_LEVEL_MAX_RATIO = 2.0
DEFAULT_MIN_HIGHER_CYCLE_RATIO = 3.0
DEFAULT_MAX_HIGHER_CYCLE_RATIO = 8.0
GATE_RATIO_POLICY_ROLE = "structural_prior_candidate_window_not_final_optimizer"
GATE_RATIO_SELECTION_PROTOCOL = (
    "use the ratio window only to admit structurally plausible higher-cycle "
    "candidates; choose the final gate ratio with walk-forward or "
    "train/validation/test Pareto trade-off evidence, never by full-sample PnL "
    "curve fitting"
)


@dataclass(frozen=True, slots=True)
class FilterScaleHierarchyConfig:
    """Scale-ratio policy for higher-period direction-gate candidates.

    The defaults are expressed in log-scale / octave terms:
    - below 2x: effectively the same scale;
    - 2x to 3x: transition buffer, too close for a hard hierarchy;
    - 3x to 8x: adjacent higher scale suitable for candidate gating research;
    - above 8x: too slow/distant for the current execution cycle by default.

    Suitability means "allowed into the research set"; it does not mean
    "optimal".  The final gate ratio is a收益/回撤 preference decision and must
    be picked by walk-forward/Pareto evidence.
    """

    same_level_max_ratio: float = DEFAULT_SAME_LEVEL_MAX_RATIO
    min_higher_cycle_ratio: float = DEFAULT_MIN_HIGHER_CYCLE_RATIO
    max_higher_cycle_ratio: float = DEFAULT_MAX_HIGHER_CYCLE_RATIO

    def __post_init__(self) -> None:
        if self.same_level_max_ratio <= 1.0:
            raise ValueError("same_level_max_ratio must be > 1")
        if self.min_higher_cycle_ratio <= self.same_level_max_ratio:
            raise ValueError("min_higher_cycle_ratio must exceed same_level_max_ratio")
        if self.max_higher_cycle_ratio <= self.min_higher_cycle_ratio:
            raise ValueError(
                "max_higher_cycle_ratio must exceed min_higher_cycle_ratio"
            )

    def to_dict(self) -> dict[str, object]:
        return asdict(self) | {
            "policy_role": GATE_RATIO_POLICY_ROLE,
            "rationale": (
                "same scale below 2x; 2x-3x is a buffer; 3x-8x is the "
                "default adjacent higher-level candidate range; above 8x is "
                "too distant"
            ),
            "selection_protocol": GATE_RATIO_SELECTION_PROTOCOL,
            "selection_metrics": [
                "out_of_sample_cagr",
                "out_of_sample_max_drawdown",
                "reward_retention_vs_single",
                "drawdown_compression_vs_single",
                "annual_excess_stability",
                "turnover_and_exposure",
            ],
        }


@dataclass(frozen=True, slots=True)
class FilterScaleHierarchyAssessment:
    """Relationship between an execution cycle and a candidate gate cycle."""

    execution_cycle_days: float
    candidate_cycle_days: float
    ratio: float
    log2_ratio: float
    relation: ScaleRelation
    usable_as_direction_gate: bool
    influence_score: float
    policy: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def assess_filter_scale_relation(
    *,
    execution_cycle_days: float,
    candidate_cycle_days: float,
    config: FilterScaleHierarchyConfig | None = None,
) -> FilterScaleHierarchyAssessment:
    """Assess whether candidate_cycle_days is a valid higher-level gate."""

    if execution_cycle_days <= 0.0 or not math.isfinite(execution_cycle_days):
        raise ValueError("execution_cycle_days must be finite and > 0")
    if candidate_cycle_days <= 0.0 or not math.isfinite(candidate_cycle_days):
        raise ValueError("candidate_cycle_days must be finite and > 0")
    cfg = config or FilterScaleHierarchyConfig()
    ratio = candidate_cycle_days / execution_cycle_days
    relation = _scale_relation(ratio, cfg)
    return FilterScaleHierarchyAssessment(
        execution_cycle_days=execution_cycle_days,
        candidate_cycle_days=candidate_cycle_days,
        ratio=ratio,
        log2_ratio=math.log2(ratio) if ratio > 0.0 else -math.inf,
        relation=relation,
        usable_as_direction_gate=relation == "higher_level",
        influence_score=_influence_score(ratio, cfg),
        policy=cfg.to_dict(),
    )


def cycle_midpoint_days(period_lo_days: float, period_hi_days: float) -> float:
    """Return geometric midpoint of a retained cycle interval in days."""

    if period_lo_days <= 0.0 or period_hi_days <= 0.0:
        raise ValueError("cycle interval bounds must be > 0")
    if period_hi_days < period_lo_days:
        raise ValueError("period_hi_days must be >= period_lo_days")
    return math.sqrt(period_lo_days * period_hi_days)


def _scale_relation(ratio: float, config: FilterScaleHierarchyConfig) -> ScaleRelation:
    if ratio <= 1.0:
        return "lower_or_equal"
    if ratio < config.same_level_max_ratio:
        return "same_level"
    if ratio < config.min_higher_cycle_ratio:
        return "transition_buffer"
    if ratio <= config.max_higher_cycle_ratio:
        return "higher_level"
    return "too_far"


def _influence_score(ratio: float, config: FilterScaleHierarchyConfig) -> float:
    if ratio < config.same_level_max_ratio:
        return 0.0
    if ratio < config.min_higher_cycle_ratio:
        span = config.min_higher_cycle_ratio - config.same_level_max_ratio
        return (ratio - config.same_level_max_ratio) / span
    if ratio <= config.max_higher_cycle_ratio:
        return 1.0
    return 0.0
