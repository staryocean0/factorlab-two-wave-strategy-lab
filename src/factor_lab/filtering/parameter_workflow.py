# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportMissingTypeStubs=false
"""Closed workflow for opportunity-density based filter parameter evidence.

This module upgrades the lower-level opportunity-density helpers into the
user-facing workflow: given one index/portfolio close series, evaluate every
supported bar period, run long rolling equal-opportunity density windows, and
return evidence-backed filter-frequency parameter recommendations plus their
change trend over time.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Literal, cast

import numpy as np
import pandas as pd

from factor_lab.filtering.opportunity_density import (
    CycleOpportunityBand,
    CycleOpportunityDensityConfig,
    CycleOpportunityPeak,
    RollingOpportunityDensityConfig,
    RollingOpportunityDensityResult,
    RollingOpportunityDensityStabilityRow,
    compute_rolling_cycle_opportunity_density,
    filter_specs_from_opportunity_period_interval,
)
from factor_lab.filtering.scale_hierarchy import FilterScaleHierarchyConfig
from factor_lab.filtering.timing_validation import FilterMode, FilterSpec, PeriodName

DEFAULT_WORKFLOW_WINDOW_YEARS = 3
DEFAULT_WORKFLOW_STEP_YEARS = 1
DEFAULT_WORKFLOW_MIN_OBSERVATIONS = 500
DEFAULT_WORKFLOW_NPERSEG = 1024
DEFAULT_WORKFLOW_RANDOM_BASELINE_COUNT = 40
DEFAULT_WORKFLOW_MIN_CYCLE_OBSERVATIONS = 8.0

DEFAULT_WORKFLOW_PERIODS: tuple[PeriodName, ...] = (
    "week",
    "day",
    "60min",
    "30min",
    "15min",
    "5min",
    "1min",
)

PERIOD_SECONDS: dict[str, float] = {
    "1min": 60.0,
    "5min": 5.0 * 60.0,
    "15min": 15.0 * 60.0,
    "30min": 30.0 * 60.0,
    "60min": 60.0 * 60.0,
    "day": 24.0 * 60.0 * 60.0,
    "week": 7.0 * 24.0 * 60.0 * 60.0,
}

PERIOD_BARS_PER_DAY: dict[str, float] = {
    "1min": 240.0,
    "5min": 48.0,
    "15min": 16.0,
    "30min": 8.0,
    "60min": 4.0,
    "day": 1.0,
    "week": 0.2,
}

PERIOD_FINE_TO_COARSE_RANK: dict[str, int] = {
    "1min": 0,
    "5min": 1,
    "15min": 2,
    "30min": 3,
    "60min": 4,
    "day": 5,
    "week": 6,
}

TrendDirection = Literal["rising", "falling", "stable", "mixed"]
ParameterEvidenceStrength = Literal["weak_candidate", "candidate", "strong_candidate"]
PeriodWorkflowStatus = Literal["completed", "skipped"]
OwnershipStatus = Literal[
    "owned",
    "reassigned_to_responsible_period",
    "outside_responsibility_domain",
    "dropped_boundary_dust",
]


@dataclass(frozen=True, slots=True)
class _RecommendationPeakSummary:
    center_period_bars: float
    left_period_bars: float
    right_period_bars: float
    window_share: float
    bin_sensitivity_score: float | None
    source: str
    filter_mode: FilterMode
    left_boundary_source: str
    right_boundary_source: str


@dataclass(frozen=True, slots=True)
class FilterParameterPeriodPolicy:
    """Per-bar-period workload and responsibility policy.

    The workflow should not ask minute bars to explain the same cycle horizon
    as daily bars.  Each period gets its own training-window length, trend-step
    cadence, minimum sample count, FFT segment size, random baseline budget and
    maximum responsible cycle band.
    """

    window_months: int
    step_months: int
    min_observations: int
    nperseg: int
    random_baseline_count: int
    min_cycle_observations: float
    max_period_bars: float
    rationale: str

    def __post_init__(self) -> None:
        if self.window_months <= 0:
            raise ValueError("window_months must be > 0")
        if self.step_months <= 0:
            raise ValueError("step_months must be > 0")
        if self.min_observations < 32:
            raise ValueError("min_observations must be >= 32")
        if self.nperseg < 32:
            raise ValueError("nperseg must be >= 32")
        if self.random_baseline_count <= 0:
            raise ValueError("random_baseline_count must be > 0")
        if self.min_cycle_observations <= 0.0:
            raise ValueError("min_cycle_observations must be > 0")
        if self.max_period_bars <= 2.0:
            raise ValueError("max_period_bars must be > 2")

    def to_dict(self) -> dict[str, object]:
        return asdict(self) | {
            "windowing_mode": (
                "blocked"
                if self.step_months >= self.window_months
                else "rolling_overlap"
            )
        }


DEFAULT_PERIOD_POLICIES: dict[PeriodName, FilterParameterPeriodPolicy] = {
    "week": FilterParameterPeriodPolicy(
        window_months=60,
        step_months=12,
        min_observations=120,
        nperseg=256,
        random_baseline_count=24,
        min_cycle_observations=8.0,
        max_period_bars=260.0,
        rationale="周线样本最少，用五年窗口逐年滚动，只负责日线之上的慢方向门禁。",
    ),
    "day": FilterParameterPeriodPolicy(
        window_months=36,
        step_months=12,
        min_observations=500,
        nperseg=512,
        random_baseline_count=40,
        min_cycle_observations=8.0,
        max_period_bars=610.0,
        rationale="日线样本少，用三年窗口逐年滚动，负责中长期趋势波段。",
    ),
    "60min": FilterParameterPeriodPolicy(
        window_months=12,
        step_months=6,
        min_observations=700,
        nperseg=512,
        random_baseline_count=30,
        min_cycle_observations=8.0,
        max_period_bars=144.0,
        rationale="小时线用一年窗口半年步长，承接日线与日内之间的中短周期。",
    ),
    "30min": FilterParameterPeriodPolicy(
        window_months=6,
        step_months=6,
        min_observations=700,
        nperseg=512,
        random_baseline_count=24,
        min_cycle_observations=8.0,
        max_period_bars=144.0,
        rationale="30分钟线数据量更大，按半年块状分段观察趋势。",
    ),
    "15min": FilterParameterPeriodPolicy(
        window_months=3,
        step_months=3,
        min_observations=700,
        nperseg=512,
        random_baseline_count=20,
        min_cycle_observations=8.0,
        max_period_bars=144.0,
        rationale="15分钟线按季度块状分段，主要负责数小时到数日波动。",
    ),
    "5min": FilterParameterPeriodPolicy(
        window_months=1,
        step_months=1,
        min_observations=700,
        nperseg=512,
        random_baseline_count=16,
        min_cycle_observations=8.0,
        max_period_bars=233.0,
        rationale="5分钟线按月分段，避免把分钟数据用于过长周期解释。",
    ),
    "1min": FilterParameterPeriodPolicy(
        window_months=1,
        step_months=1,
        min_observations=3000,
        nperseg=1024,
        random_baseline_count=12,
        min_cycle_observations=8.0,
        max_period_bars=377.0,
        rationale="1分钟线只负责高频到约一两日内波动，按月分段控制算力。",
    ),
}


@dataclass(frozen=True, slots=True)
class FilterParameterWorkflowConfig:
    """Configuration for the closed filter-parameter evidence workflow."""

    periods: tuple[PeriodName, ...] = DEFAULT_WORKFLOW_PERIODS
    timestamp_column: str = "timestamp"
    close_column: str = "close"
    window_years: int = DEFAULT_WORKFLOW_WINDOW_YEARS
    step_years: int = DEFAULT_WORKFLOW_STEP_YEARS
    min_observations: int = DEFAULT_WORKFLOW_MIN_OBSERVATIONS
    nperseg: int = DEFAULT_WORKFLOW_NPERSEG
    random_baseline_count: int = DEFAULT_WORKFLOW_RANDOM_BASELINE_COUNT
    random_seed: int = 20260521
    min_cycle_observations: float = DEFAULT_WORKFLOW_MIN_CYCLE_OBSERVATIONS
    top_band_count: int = 3
    max_recommendations_per_period: int = 3
    min_vs_random_median: float = 1.0
    min_stability_share: float = 0.50
    min_continuous_peak_window_share: float = 0.50
    require_above_random_95: bool = False
    max_fourier_window: int = 512
    max_wavelet_window: int = 512
    minimum_supported_frequency_ratio: float = 1.25
    use_period_specific_defaults: bool = True
    period_policies: Mapping[str, FilterParameterPeriodPolicy] | None = None

    def __post_init__(self) -> None:
        if not self.periods:
            raise ValueError("periods must not be empty")
        for period in self.periods:
            if period not in PERIOD_SECONDS:
                raise ValueError(f"Unsupported workflow period: {period}")
        if self.window_years <= 0:
            raise ValueError("window_years must be > 0")
        if self.step_years <= 0:
            raise ValueError("step_years must be > 0")
        if self.min_observations < 32:
            raise ValueError("min_observations must be >= 32")
        if self.nperseg < 32:
            raise ValueError("nperseg must be >= 32")
        if self.random_baseline_count <= 0:
            raise ValueError("random_baseline_count must be > 0 for workflow evidence")
        if self.min_cycle_observations <= 0.0:
            raise ValueError("min_cycle_observations must be > 0")
        if self.top_band_count <= 0:
            raise ValueError("top_band_count must be > 0")
        if self.max_recommendations_per_period <= 0:
            raise ValueError("max_recommendations_per_period must be > 0")
        if self.min_vs_random_median <= 0.0:
            raise ValueError("min_vs_random_median must be > 0")
        if not 0.0 <= self.min_stability_share <= 1.0:
            raise ValueError("min_stability_share must be in [0, 1]")
        if not 0.0 <= self.min_continuous_peak_window_share <= 1.0:
            raise ValueError("min_continuous_peak_window_share must be in [0, 1]")
        if self.max_fourier_window < 64:
            raise ValueError("max_fourier_window must be >= 64")
        if self.max_wavelet_window < 64:
            raise ValueError("max_wavelet_window must be >= 64")
        if self.minimum_supported_frequency_ratio <= 0.0:
            raise ValueError("minimum_supported_frequency_ratio must be > 0")
        if self.period_policies:
            for period in self.period_policies:
                if period not in PERIOD_SECONDS:
                    raise ValueError(f"Unsupported period policy key: {period}")


@dataclass(frozen=True, slots=True)
class FilterParameterTrendPoint:
    """Dominant recommended band in one rolling training window."""

    window_label: str
    sample_start: str
    sample_end: str
    period_band_bars: str | None
    density_share_vs_random_median: float | None
    opportunity_normalized_share: float | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FilterParameterRecommendation:
    """One evidence-backed filter-frequency parameter recommendation."""

    rank: int
    period: str
    period_band_bars: str
    period_lo_bars: float
    period_hi_bars: float
    period_mid_bars: float
    period_mid_days_equiv: float | None
    center_period_bars: float
    center_period_days_equiv: float | None
    continuous_peak_period_bars: float | None
    continuous_peak_lo_bars: float | None
    continuous_peak_hi_bars: float | None
    continuous_peak_window_share: float
    retained_period_lo_bars: float
    retained_period_hi_bars: float
    retained_period_lo_days_equiv: float | None
    retained_period_hi_days_equiv: float | None
    retained_frequency_low_cycles_per_bar: float
    retained_frequency_high_cycles_per_bar: float
    filter_mode: str
    left_boundary_source: str
    right_boundary_source: str
    bin_sensitivity_score: float | None
    decision_source: str
    median_vs_random: float
    mean_vs_random: float
    above_1_share: float
    above_12_share: float
    above_15_share: float
    above_random_95_share: float | None
    top1_share: float
    coefficient_of_variation: float | None
    trend_slope_per_window: float | None
    trend_relative_slope: float | None
    trend_direction: TrendDirection
    recommendation_score: float
    evidence_strength: ParameterEvidenceStrength
    evidence_strength_label_zh: str
    evidence_window_count: int
    filter_specs: list[dict[str, object]]
    interpretation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FilterParameterOwnedInterval:
    """One retained interval after smaller-period ownership assignment.

    The same trading-day-equivalent band can be detected from a period that is
    too fine or too coarse for execution.  Responsibility is assigned by K-line
    count: choose the display/execution period whose bars-per-cycle is closest
    to the target bar count.
    """

    assigned_period: str
    period: str
    source_rank: int
    segment_index: int
    ownership_status: OwnershipStatus
    responsibility_domain_lo_days: float
    responsibility_domain_hi_days: float | None
    original_period_lo_days: float
    original_period_hi_days: float
    assigned_period_lo_days: float | None
    assigned_period_hi_days: float | None
    filter_mode: str
    center_period_days: float | None
    median_vs_random: float
    continuous_peak_window_share: float
    evidence_strength: ParameterEvidenceStrength
    evidence_strength_label_zh: str
    reassigned_from_period: str | None
    responsibility_rule: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FilterParameterMergedOwnedInterval:
    """One final per-period filter design target after ownership merging.

    `owned_intervals` keeps the diagnostic slices created by different dense
    peaks and source periods.  Those slices are useful evidence, but they should
    not automatically become multiple filters on the same K-line period.  Once a
    cycle slice is assigned to a period, downstream tool selection receives one
    merged band per `assigned_period`: the finite union from the lowest assigned
    boundary to the highest assigned boundary.
    """

    assigned_period: str
    source_interval_count: int
    source_periods: list[str]
    source_ranks: list[int]
    ownership_statuses: list[str]
    assigned_period_lo_days: float
    assigned_period_hi_days: float
    assigned_period_lo_bars: float
    assigned_period_hi_bars: float
    center_period_days: float
    center_period_bars: float
    filter_mode: str
    median_vs_random_max: float
    median_vs_random_mean: float
    continuous_peak_window_share_max: float
    continuous_peak_window_share_mean: float
    evidence_strength: ParameterEvidenceStrength
    evidence_strength_label_zh: str
    responsibility_rule: str
    merge_rule: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FilterParameterPeriodWorkflowResult:
    """Workflow result for one bar period."""

    period: str
    status: PeriodWorkflowStatus
    skip_reason: str | None
    recommendations: list[FilterParameterRecommendation]
    trend_points: list[FilterParameterTrendPoint]
    rolling_density: RollingOpportunityDensityResult | None
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "period": self.period,
            "status": self.status,
            "skip_reason": self.skip_reason,
            "recommendations": [item.to_dict() for item in self.recommendations],
            "trend_points": [item.to_dict() for item in self.trend_points],
            "rolling_density": (
                self.rolling_density.to_dict() if self.rolling_density else None
            ),
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class FilterParameterWorkflowResult:
    """Closed multi-period filter-parameter workflow result."""

    index_ref: str
    periods: list[FilterParameterPeriodWorkflowResult]
    summary_recommendations: list[FilterParameterRecommendation]
    owned_intervals: list[FilterParameterOwnedInterval]
    merged_owned_intervals: list[FilterParameterMergedOwnedInterval]
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "index_ref": self.index_ref,
            "periods": [period.to_dict() for period in self.periods],
            "summary_recommendations": [
                item.to_dict() for item in self.summary_recommendations
            ],
            "owned_intervals": [item.to_dict() for item in self.owned_intervals],
            "merged_owned_intervals": [
                item.to_dict() for item in self.merged_owned_intervals
            ],
            "metadata": self.metadata,
        }


def run_filter_parameter_workflow(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: FilterParameterWorkflowConfig | None = None,
    index_ref: str = "index_series",
) -> FilterParameterWorkflowResult:
    """Run the closed opportunity-density workflow for an index time series.

    The workflow deliberately stops at filter-frequency parameter evidence.  It
    does not claim a trading strategy and it does not mutate factor/strategy
    lifecycle state.  Downstream `run_filter_timing_validation` still has to
    battle the seeded filters under the next-bar execution protocol.
    """

    cfg = config or FilterParameterWorkflowConfig()
    frame = _input_frame(rows, timestamp_column=cfg.timestamp_column)
    source_median_seconds = _median_source_interval_seconds(
        frame,
        timestamp_column=cfg.timestamp_column,
    )
    period_results: list[FilterParameterPeriodWorkflowResult] = []
    for period in cfg.periods:
        if not _period_supported_by_source(
            period,
            source_median_seconds=source_median_seconds,
            tolerance_ratio=cfg.minimum_supported_frequency_ratio,
        ):
            period_results.append(
                _skipped_period_result(
                    period=period,
                    reason=(
                        "input_frequency_too_coarse_for_period; provide real "
                        f"{period} or finer bars instead of resampling slower data"
                    ),
                    source_median_seconds=source_median_seconds,
                    config=cfg,
                )
            )
            continue
        try:
            rolling = _rolling_for_period(frame, period=period, config=cfg)
        except ValueError as exc:
            period_results.append(
                _skipped_period_result(
                    period=period,
                    reason=str(exc),
                    source_median_seconds=source_median_seconds,
                    config=cfg,
                )
            )
            continue
        recommendations = _recommendations_from_rolling(
            rolling,
            max_recommendations=cfg.max_recommendations_per_period,
            min_vs_random_median=cfg.min_vs_random_median,
            min_stability_share=cfg.min_stability_share,
            min_continuous_peak_window_share=cfg.min_continuous_peak_window_share,
            require_above_random_95=cfg.require_above_random_95,
            max_fourier_window=cfg.max_fourier_window,
            max_wavelet_window=cfg.max_wavelet_window,
        )
        period_policy = _policy_for_period(period, cfg)
        period_results.append(
            FilterParameterPeriodWorkflowResult(
                period=period,
                status="completed",
                skip_reason=None,
                recommendations=recommendations,
                trend_points=_trend_points_from_rolling(rolling),
                rolling_density=rolling,
                metadata={
                    "window_count": len(rolling.windows),
                    "recommended_band_count": len(recommendations),
                    "sample_start": rolling.metadata.get("sample_start"),
                    "sample_end": rolling.metadata.get("sample_end"),
                    "bars_per_day": PERIOD_BARS_PER_DAY[period],
                    "period_window_policy": period_policy.to_dict(),
                },
            )
        )

    summary = sorted(
        [rec for period in period_results for rec in period.recommendations],
        key=lambda rec: rec.recommendation_score,
        reverse=True,
    )[: cfg.max_recommendations_per_period]
    owned_intervals = assign_filter_interval_ownership(
        [rec for period in period_results for rec in period.recommendations]
    )
    merged_owned_intervals = merge_filter_interval_ownership(owned_intervals)
    return FilterParameterWorkflowResult(
        index_ref=index_ref,
        periods=period_results,
        summary_recommendations=summary,
        owned_intervals=owned_intervals,
        merged_owned_intervals=merged_owned_intervals,
        metadata={
            "workflow_role": "filter_parameter_recommendation_workflow",
            "workflow_version": "opportunity_density_rolling_valley_ownership_v3",
            "index_ref": index_ref,
            "periods_requested": list(cfg.periods),
            "periods_completed": [
                period.period
                for period in period_results
                if period.status == "completed"
            ],
            "periods_skipped": [
                {
                    "period": period.period,
                    "skip_reason": period.skip_reason,
                }
                for period in period_results
                if period.status == "skipped"
            ],
            "source_median_interval_seconds": source_median_seconds,
            "period_window_policy": {
                period: _policy_for_period(cast(PeriodName, period), cfg).to_dict()
                for period in cfg.periods
            },
            "random_baseline_count": cfg.random_baseline_count,
            "density_formula": (
                "cycle_opportunity_density = PSD / frequency = PSD * period"
            ),
            "parameter_boundary_formula": (
                "detect dense peaks, then use adjacent smoothed-density valleys "
                "as retained-interval cutoffs for lowpass/highpass/bandpass"
            ),
            "interval_ownership_rule": (
                "split retained trading-day-equivalent intervals by bar-count "
                "responsibility domains; assign each slice to the period whose "
                "bars-per-cycle is closest to 32 bars, with 8 bars as the "
                "minimum finest-period display floor"
            ),
            "days_equiv_policy": {
                "meaning": "trading_day_equivalent_not_24h_clock_day",
                "bars_per_day": dict(PERIOD_BARS_PER_DAY),
            },
            "evidence_strength_policy": {
                "weak_candidate": (
                    "median_vs_random just above 1.0 is exploratory only; do "
                    "not narrate as a strong parameter candidate"
                ),
                "candidate": "moderate non-PnL frequency evidence",
                "strong_candidate": (
                    "strong non-PnL frequency evidence across random-baseline "
                    "and rolling-stability checks"
                ),
            },
            "merged_interval_rule": (
                "before designing filters, merge all active owned intervals with "
                "the same assigned_period into one continuous band; frequency "
                "peaks remain evidence, not separate same-level filters"
            ),
            "scale_hierarchy_policy": FilterScaleHierarchyConfig().to_dict(),
            "scale_hierarchy_role": (
                "bar-count ownership assigns display/execution responsibility; "
                "higher-level direction gates must still pass the cycle-ratio "
                "hierarchy policy instead of using merely larger calendar periods"
            ),
            "owned_interval_schema_version": "bar_count_responsibility_v2",
            "canonical_output_sections": [
                "metadata",
                "periods",
                "summary_recommendations",
                "owned_intervals",
                "merged_owned_intervals",
            ],
            "artifact_contract": (
                "output-json is the reusable workflow artifact; rendered charts "
                "or markdown summaries are derived views and must not be treated "
                "as the only source of truth"
            ),
            "rerun_policy": (
                "rerun when the input series, adjustment data vintage, requested "
                "periods, or window policy changes; compare trend_points and "
                "owned_intervals across runs before freezing filter parameters"
            ),
            "parameter_selection_role": (
                "long_rolling_frequency_evidence_not_profit_optimization"
            ),
            "adjustment_manifest_required": True,
            "factor_lifecycle_mutation": False,
            "strategy_lifecycle_mutation": False,
        },
    )


def assign_filter_interval_ownership(
    recommendations: Sequence[FilterParameterRecommendation],
    *,
    min_segment_width_days: float = 0.05,
    target_bars_per_cycle: float = 32.0,
    min_bars_per_cycle: float = 8.0,
    responsibility_periods: Sequence[str] | None = None,
) -> list[FilterParameterOwnedInterval]:
    """Assign retained intervals to the period with the best K-line count.

    A cycle should be displayed on the bar period where it spans a useful number
    of bars.  The default responsibility domain boundary between two adjacent
    periods is where their bars-per-cycle are equally far from the target count
    on a log scale.
    """

    if min_segment_width_days < 0.0:
        raise ValueError("min_segment_width_days must be >= 0")
    if target_bars_per_cycle <= 0.0:
        raise ValueError("target_bars_per_cycle must be > 0")
    if min_bars_per_cycle <= 0.0:
        raise ValueError("min_bars_per_cycle must be > 0")
    owned: list[FilterParameterOwnedInterval] = []
    periods = _responsibility_periods(recommendations, responsibility_periods)
    domains = _responsibility_domains(
        periods,
        target_bars_per_cycle=target_bars_per_cycle,
        min_bars_per_cycle=min_bars_per_cycle,
    )
    sorted_recommendations = sorted(
        recommendations,
        key=lambda rec: (
            rec.retained_period_lo_days_equiv or math.inf,
            PERIOD_FINE_TO_COARSE_RANK.get(rec.period, 999),
            rec.rank,
        ),
    )
    for rec in sorted_recommendations:
        if (
            rec.retained_period_lo_days_equiv is None
            or rec.retained_period_hi_days_equiv is None
        ):
            continue
        original_lo = float(rec.retained_period_lo_days_equiv or 0.0)
        original_hi = float(rec.retained_period_hi_days_equiv or 0.0)
        if not (
            math.isfinite(original_lo)
            and math.isfinite(original_hi)
            and original_hi > original_lo
        ):
            continue
        segment_index = 0
        matched_any = False
        for assigned_period, domain_lo, domain_hi in domains:
            clipped_lo = max(original_lo, domain_lo)
            clipped_hi = (
                original_hi if domain_hi is None else min(original_hi, domain_hi)
            )
            if clipped_hi <= clipped_lo:
                continue
            if (clipped_hi - clipped_lo) < min_segment_width_days:
                continue
            matched_any = True
            segment_index += 1
            owned.append(
                FilterParameterOwnedInterval(
                    assigned_period=assigned_period,
                    period=rec.period,
                    source_rank=rec.rank,
                    segment_index=segment_index,
                    ownership_status=(
                        "owned"
                        if assigned_period == rec.period
                        else "reassigned_to_responsible_period"
                    ),
                    responsibility_domain_lo_days=domain_lo,
                    responsibility_domain_hi_days=domain_hi,
                    original_period_lo_days=original_lo,
                    original_period_hi_days=original_hi,
                    assigned_period_lo_days=clipped_lo,
                    assigned_period_hi_days=clipped_hi,
                    filter_mode="bandpass",
                    center_period_days=rec.center_period_days_equiv,
                    median_vs_random=rec.median_vs_random,
                    continuous_peak_window_share=rec.continuous_peak_window_share,
                    evidence_strength=rec.evidence_strength,
                    evidence_strength_label_zh=rec.evidence_strength_label_zh,
                    reassigned_from_period=(
                        None if assigned_period == rec.period else rec.period
                    ),
                    responsibility_rule=_ownership_rule_text(
                        target_bars_per_cycle=target_bars_per_cycle,
                        min_bars_per_cycle=min_bars_per_cycle,
                    ),
                )
            )
        if not matched_any:
            assigned_period = _responsible_period_for_interval_midpoint(
                original_lo,
                original_hi,
                domains,
            )
            domain_lo, domain_hi = _domain_for_period(assigned_period, domains)
            owned.append(
                FilterParameterOwnedInterval(
                    assigned_period=assigned_period,
                    period=rec.period,
                    source_rank=rec.rank,
                    segment_index=0,
                    ownership_status="outside_responsibility_domain",
                    responsibility_domain_lo_days=domain_lo,
                    responsibility_domain_hi_days=domain_hi,
                    original_period_lo_days=original_lo,
                    original_period_hi_days=original_hi,
                    assigned_period_lo_days=None,
                    assigned_period_hi_days=None,
                    filter_mode="bandpass",
                    center_period_days=rec.center_period_days_equiv,
                    median_vs_random=rec.median_vs_random,
                    continuous_peak_window_share=rec.continuous_peak_window_share,
                    evidence_strength=rec.evidence_strength,
                    evidence_strength_label_zh=rec.evidence_strength_label_zh,
                    reassigned_from_period=(
                        None if assigned_period == rec.period else rec.period
                    ),
                    responsibility_rule=_ownership_rule_text(
                        target_bars_per_cycle=target_bars_per_cycle,
                        min_bars_per_cycle=min_bars_per_cycle,
                    ),
                )
            )
    return owned


def merge_filter_interval_ownership(
    owned_intervals: Sequence[FilterParameterOwnedInterval],
) -> list[FilterParameterMergedOwnedInterval]:
    """Merge active ownership slices into one final design band per period.

    Frequency analysis may identify several nearby dense peaks inside the same
    K-line period's responsibility domain.  Those peaks should remain in the
    diagnostic `owned_intervals`, but downstream filter design should receive a
    single band for that period so it does not create several same-level filters
    that are really adjacent views of one regime.
    """

    active = [
        item
        for item in owned_intervals
        if item.assigned_period_lo_days is not None
        and item.assigned_period_hi_days is not None
        and item.assigned_period_hi_days > item.assigned_period_lo_days
    ]
    by_period: dict[str, list[FilterParameterOwnedInterval]] = {}
    for item in active:
        by_period.setdefault(item.assigned_period, []).append(item)
    merged: list[FilterParameterMergedOwnedInterval] = []
    for assigned_period, items in sorted(
        by_period.items(),
        key=lambda pair: PERIOD_FINE_TO_COARSE_RANK.get(pair[0], 999),
    ):
        lo_days = min(cast(float, item.assigned_period_lo_days) for item in items)
        hi_days = max(cast(float, item.assigned_period_hi_days) for item in items)
        if not (
            math.isfinite(lo_days) and math.isfinite(hi_days) and hi_days > lo_days
        ):
            continue
        bars_per_day = _bars_per_day_for_responsibility_period(assigned_period)
        center_days = math.sqrt(lo_days * hi_days)
        medians = [item.median_vs_random for item in items]
        peak_shares = [item.continuous_peak_window_share for item in items]
        evidence_strength = classify_parameter_evidence_strength(
            median_vs_random=max(medians),
            continuous_peak_window_share=max(peak_shares),
            above_1_share=max(peak_shares),
        )
        source_periods = sorted(
            set(item.period for item in items),
            key=lambda period: PERIOD_FINE_TO_COARSE_RANK.get(period, 999),
        )
        source_ranks = sorted({item.source_rank for item in items})
        ownership_statuses = sorted({item.ownership_status for item in items})
        merged.append(
            FilterParameterMergedOwnedInterval(
                assigned_period=assigned_period,
                source_interval_count=len(items),
                source_periods=source_periods,
                source_ranks=source_ranks,
                ownership_statuses=ownership_statuses,
                assigned_period_lo_days=lo_days,
                assigned_period_hi_days=hi_days,
                assigned_period_lo_bars=lo_days * bars_per_day,
                assigned_period_hi_bars=hi_days * bars_per_day,
                center_period_days=center_days,
                center_period_bars=center_days * bars_per_day,
                filter_mode="bandpass",
                median_vs_random_max=max(medians),
                median_vs_random_mean=float(sum(medians) / len(medians)),
                continuous_peak_window_share_max=max(peak_shares),
                continuous_peak_window_share_mean=float(
                    sum(peak_shares) / len(peak_shares)
                ),
                evidence_strength=evidence_strength,
                evidence_strength_label_zh=parameter_evidence_strength_label_zh(
                    evidence_strength
                ),
                responsibility_rule=items[0].responsibility_rule,
                merge_rule=(
                    "merge_all_active_owned_intervals_for_same_assigned_period_"
                    "into_one_filter_design_band"
                ),
            )
        )
    return merged


def _ownership_rule_text(
    *,
    target_bars_per_cycle: float,
    min_bars_per_cycle: float,
) -> str:
    return (
        "assign_each_interval_slice_to_the_period_whose_bars_per_cycle_is_"
        f"closest_to_{target_bars_per_cycle:g}_bars; ignore_slices_below_"
        f"{min_bars_per_cycle:g}_bars_on_the_finest_period"
    )


def _responsibility_periods(
    recommendations: Sequence[FilterParameterRecommendation],
    explicit_periods: Sequence[str] | None,
) -> list[str]:
    known = set(PERIOD_BARS_PER_DAY) | {"week"}
    if explicit_periods is not None:
        periods = [period for period in explicit_periods if period in known]
    else:
        periods = [period for period in PERIOD_FINE_TO_COARSE_RANK if period in known]
        recommendation_periods = {rec.period for rec in recommendations}
        periods = [
            period
            for period in periods
            if period in recommendation_periods or period == "week"
        ]
    return sorted(
        dict.fromkeys(periods),
        key=lambda period: PERIOD_FINE_TO_COARSE_RANK.get(period, 999),
    )


def _responsibility_domains(
    periods: Sequence[str],
    *,
    target_bars_per_cycle: float,
    min_bars_per_cycle: float,
) -> list[tuple[str, float, float | None]]:
    if not periods:
        return []
    domains: list[tuple[str, float, float | None]] = []
    for index, period in enumerate(periods):
        bars_per_day = _bars_per_day_for_responsibility_period(period)
        if index == 0:
            lower = min_bars_per_cycle / bars_per_day
        else:
            finer_bars = _bars_per_day_for_responsibility_period(periods[index - 1])
            lower = target_bars_per_cycle / math.sqrt(finer_bars * bars_per_day)
        if index == len(periods) - 1:
            upper = None
        else:
            coarser_bars = _bars_per_day_for_responsibility_period(periods[index + 1])
            upper = target_bars_per_cycle / math.sqrt(bars_per_day * coarser_bars)
        domains.append((period, lower, upper))
    return domains


def _bars_per_day_for_responsibility_period(period: str) -> float:
    if period == "week":
        return 0.2
    return PERIOD_BARS_PER_DAY[period]


def _responsible_period_for_interval_midpoint(
    lo: float,
    hi: float,
    domains: Sequence[tuple[str, float, float | None]],
) -> str:
    midpoint = math.sqrt(lo * hi)
    for period, domain_lo, domain_hi in domains:
        if midpoint < domain_lo:
            continue
        if domain_hi is not None and midpoint >= domain_hi:
            continue
        return period
    return domains[-1][0]


def _domain_for_period(
    period: str,
    domains: Sequence[tuple[str, float, float | None]],
) -> tuple[float, float | None]:
    for candidate, lo, hi in domains:
        if candidate == period:
            return lo, hi
    raise KeyError(period)


def _rolling_for_period(
    frame: pd.DataFrame,
    *,
    period: PeriodName,
    config: FilterParameterWorkflowConfig,
) -> RollingOpportunityDensityResult:
    policy = _policy_for_period(period, config)
    density_config = CycleOpportunityDensityConfig(
        period=period,
        timestamp_column=config.timestamp_column,
        close_column=config.close_column,
        nperseg=policy.nperseg,
        period_bands=_period_bands_for_policy(policy),
        random_baseline_count=policy.random_baseline_count,
        random_seed=config.random_seed + _period_seed_offset(period),
        min_cycle_observations=policy.min_cycle_observations,
    )
    return compute_rolling_cycle_opportunity_density(
        frame,
        config=RollingOpportunityDensityConfig(
            density_config=density_config,
            window_years=config.window_years,
            step_years=config.step_years,
            window_months=policy.window_months,
            step_months=policy.step_months,
            min_observations=policy.min_observations,
            top_band_count=config.top_band_count,
            min_vs_random_median=config.min_vs_random_median,
            require_above_random_95=config.require_above_random_95,
            bars_per_day=PERIOD_BARS_PER_DAY[period],
        ),
    )


def _policy_for_period(
    period: PeriodName,
    config: FilterParameterWorkflowConfig,
) -> FilterParameterPeriodPolicy:
    explicit = config.period_policies or {}
    base = explicit.get(period) or DEFAULT_PERIOD_POLICIES[period]
    if not config.use_period_specific_defaults:
        base = FilterParameterPeriodPolicy(
            window_months=config.window_years * 12,
            step_months=config.step_years * 12,
            min_observations=config.min_observations,
            nperseg=config.nperseg,
            random_baseline_count=config.random_baseline_count,
            min_cycle_observations=config.min_cycle_observations,
            max_period_bars=base.max_period_bars,
            rationale=("显式 uniform policy：所有周期共用 legacy 窗口和计算参数。"),
        )
    else:
        base = _policy_with_global_overrides(base, config)
    return base


def _policy_with_global_overrides(
    policy: FilterParameterPeriodPolicy,
    config: FilterParameterWorkflowConfig,
) -> FilterParameterPeriodPolicy:
    window_months = policy.window_months
    step_months = policy.step_months
    min_observations = policy.min_observations
    nperseg = policy.nperseg
    random_baseline_count = policy.random_baseline_count
    min_cycle_observations = policy.min_cycle_observations
    if config.window_years != DEFAULT_WORKFLOW_WINDOW_YEARS:
        window_months = config.window_years * 12
    if config.step_years != DEFAULT_WORKFLOW_STEP_YEARS:
        step_months = config.step_years * 12
    if config.min_observations != DEFAULT_WORKFLOW_MIN_OBSERVATIONS:
        min_observations = config.min_observations
    if config.nperseg != DEFAULT_WORKFLOW_NPERSEG:
        nperseg = config.nperseg
    if config.random_baseline_count != DEFAULT_WORKFLOW_RANDOM_BASELINE_COUNT:
        random_baseline_count = config.random_baseline_count
    if config.min_cycle_observations != DEFAULT_WORKFLOW_MIN_CYCLE_OBSERVATIONS:
        min_cycle_observations = config.min_cycle_observations
    return FilterParameterPeriodPolicy(
        window_months=window_months,
        step_months=step_months,
        min_observations=min_observations,
        nperseg=nperseg,
        random_baseline_count=random_baseline_count,
        min_cycle_observations=min_cycle_observations,
        max_period_bars=policy.max_period_bars,
        rationale=policy.rationale,
    )


def _period_bands_for_policy(
    policy: FilterParameterPeriodPolicy,
) -> tuple[tuple[float, float], ...]:
    bands = tuple(
        (lower, upper)
        for lower, upper in CycleOpportunityDensityConfig().period_bands
        if lower < policy.max_period_bars
    )
    if not bands:
        raise ValueError("period policy leaves no period bands")
    last_lower, last_upper = bands[-1]
    if last_upper > policy.max_period_bars:
        bands = (*bands[:-1], (last_lower, policy.max_period_bars))
    return bands


def _recommendations_from_rolling(
    rolling: RollingOpportunityDensityResult,
    *,
    max_recommendations: int,
    min_vs_random_median: float,
    min_stability_share: float,
    min_continuous_peak_window_share: float,
    require_above_random_95: bool,
    max_fourier_window: int,
    max_wavelet_window: int,
) -> list[FilterParameterRecommendation]:
    window_count = max(1, len(rolling.windows))
    rows: list[tuple[float, RollingOpportunityDensityStabilityRow]] = []
    for row in rolling.stability:
        if row.median_ratio < min_vs_random_median:
            continue
        if row.above_1_share < min_stability_share:
            continue
        if require_above_random_95 and (row.above_random_95_share or 0.0) <= 0.0:
            continue
        peak_summary = _peak_summary_for_band(rolling, row)
        if peak_summary is None:
            continue
        if peak_summary.window_share < min_continuous_peak_window_share:
            continue
        score = _recommendation_score(
            row,
            rolling=rolling,
            window_count=window_count,
            peak_summary=peak_summary,
        )
        rows.append((score, row))
    rows.sort(key=lambda item: item[0], reverse=True)

    recommendations: list[FilterParameterRecommendation] = []
    for rank, (score, row) in enumerate(rows[:max_recommendations], start=1):
        slope, rel_slope, direction = _trend_for_band(rolling, row.period_band_bars)
        peak_summary = _peak_summary_for_band(rolling, row)
        if peak_summary is None:
            continue
        filter_specs = _filter_spec_payloads(
            filter_specs_from_opportunity_period_interval(
                period_lo_bars=peak_summary.left_period_bars,
                period_hi_bars=peak_summary.right_period_bars,
                mode=peak_summary.filter_mode,
                max_fourier_window=max_fourier_window,
                max_wavelet_window=max_wavelet_window,
            )
        )
        bars_per_day_float = _optional_finite_float(
            rolling.metadata.get("bars_per_day")
        )
        evidence_strength = classify_parameter_evidence_strength(
            median_vs_random=row.median_ratio,
            continuous_peak_window_share=peak_summary.window_share,
            above_1_share=row.above_1_share,
        )
        recommendations.append(
            FilterParameterRecommendation(
                rank=rank,
                period=rolling.period,
                period_band_bars=row.period_band_bars,
                period_lo_bars=row.period_lo_bars,
                period_hi_bars=row.period_hi_bars,
                period_mid_bars=row.period_mid_bars,
                period_mid_days_equiv=row.period_mid_days_equiv,
                center_period_bars=peak_summary.center_period_bars,
                center_period_days_equiv=(
                    peak_summary.center_period_bars / bars_per_day_float
                    if bars_per_day_float is not None
                    else None
                ),
                continuous_peak_period_bars=peak_summary.center_period_bars,
                continuous_peak_lo_bars=peak_summary.left_period_bars,
                continuous_peak_hi_bars=peak_summary.right_period_bars,
                continuous_peak_window_share=peak_summary.window_share,
                retained_period_lo_bars=peak_summary.left_period_bars,
                retained_period_hi_bars=peak_summary.right_period_bars,
                retained_period_lo_days_equiv=(
                    peak_summary.left_period_bars / bars_per_day_float
                    if bars_per_day_float is not None
                    else None
                ),
                retained_period_hi_days_equiv=(
                    peak_summary.right_period_bars / bars_per_day_float
                    if bars_per_day_float is not None
                    else None
                ),
                retained_frequency_low_cycles_per_bar=(
                    1.0 / peak_summary.right_period_bars
                ),
                retained_frequency_high_cycles_per_bar=(
                    1.0 / peak_summary.left_period_bars
                ),
                filter_mode=peak_summary.filter_mode,
                left_boundary_source=peak_summary.left_boundary_source,
                right_boundary_source=peak_summary.right_boundary_source,
                bin_sensitivity_score=peak_summary.bin_sensitivity_score,
                decision_source=peak_summary.source,
                median_vs_random=row.median_ratio,
                mean_vs_random=row.mean_ratio,
                above_1_share=row.above_1_share,
                above_12_share=row.above_12_share,
                above_15_share=row.above_15_share,
                above_random_95_share=row.above_random_95_share,
                top1_share=rolling.top1_counts.get(row.period_band_bars, 0)
                / window_count,
                coefficient_of_variation=row.coefficient_of_variation,
                trend_slope_per_window=slope,
                trend_relative_slope=rel_slope,
                trend_direction=direction,
                recommendation_score=score,
                evidence_strength=evidence_strength,
                evidence_strength_label_zh=parameter_evidence_strength_label_zh(
                    evidence_strength
                ),
                evidence_window_count=row.window_count,
                filter_specs=filter_specs,
                interpretation=_recommendation_interpretation(
                    row,
                    direction,
                    peak_summary,
                ),
            )
        )
    return recommendations


def classify_parameter_evidence_strength(
    *,
    median_vs_random: float,
    continuous_peak_window_share: float,
    above_1_share: float | None = None,
) -> ParameterEvidenceStrength:
    """Classify parameter evidence strength without using strategy PnL.

    `median_vs_random` just above 1.0 is enough to keep an exploratory parameter
    candidate, but it should not be narrated as a strong candidate.  The
    thresholds are intentionally descriptive and sit before tool/strategy PnL:
    they only describe frequency-evidence strength.
    """

    stable_share = continuous_peak_window_share
    above_share = stable_share if above_1_share is None else above_1_share
    if median_vs_random >= 1.35 and stable_share >= 0.65 and above_share >= 0.65:
        return "strong_candidate"
    if median_vs_random >= 1.15 and stable_share >= 0.55 and above_share >= 0.55:
        return "candidate"
    return "weak_candidate"


def parameter_evidence_strength_label_zh(
    strength: ParameterEvidenceStrength,
) -> str:
    return {
        "weak_candidate": (
            "弱候选：仅略高于随机基线，只能进入探索/对照，不应叙述为强候选。"
        ),
        "candidate": (
            "候选：相对随机基线和滚动稳定性具备中等证据，可进入工具/策略候选比较。"
        ),
        "strong_candidate": (
            "强候选：相对随机基线和滚动稳定性均较强，可作为优先研究频段。"
        ),
    }[strength]


def _optional_finite_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def _peak_summary_for_band(
    rolling: RollingOpportunityDensityResult,
    row: RollingOpportunityDensityStabilityRow,
) -> _RecommendationPeakSummary | None:
    peaks: list[CycleOpportunityPeak] = []
    for window in rolling.windows:
        candidates = [
            peak
            for peak in window.top_peaks
            if peak.containing_band_bars == row.period_band_bars
        ]
        if candidates:
            peaks.append(candidates[0])
    if not peaks:
        return None

    centers = np.asarray([peak.center_period_bars for peak in peaks], dtype=np.float64)
    lefts = np.asarray([peak.left_period_bars for peak in peaks], dtype=np.float64)
    rights = np.asarray([peak.right_period_bars for peak in peaks], dtype=np.float64)
    sensitivities = np.asarray(
        [peak.bin_sensitivity_score for peak in peaks],
        dtype=np.float64,
    )
    left_sources = [peak.left_boundary_source for peak in peaks]
    right_sources = [peak.right_boundary_source for peak in peaks]
    center = float(np.median(centers))
    left = float(np.median(lefts))
    right = float(np.median(rights))
    left = min(left, center, row.period_hi_bars)
    right = max(right, center, row.period_lo_bars)
    left_source = _majority_label(left_sources)
    right_source = _majority_label(right_sources)
    return _RecommendationPeakSummary(
        center_period_bars=center,
        left_period_bars=max(2.0, left),
        right_period_bars=max(left + 1e-9, right),
        window_share=float(len(peaks) / max(1, len(rolling.windows))),
        bin_sensitivity_score=float(np.median(sensitivities)),
        source="continuous_peak",
        filter_mode=_filter_mode_from_boundaries(left_source, right_source),
        left_boundary_source=left_source,
        right_boundary_source=right_source,
    )


def _majority_label(values: Sequence[str]) -> str:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    if not counts:
        return "unknown"
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _filter_mode_from_boundaries(
    left_boundary_source: str,
    right_boundary_source: str,
) -> FilterMode:
    left_is_edge = left_boundary_source == "edge"
    right_is_edge = right_boundary_source == "edge"
    if left_is_edge and not right_is_edge:
        return "highpass"
    if right_is_edge and not left_is_edge:
        return "lowpass"
    return "bandpass"


def _recommendation_score(
    row: RollingOpportunityDensityStabilityRow,
    *,
    rolling: RollingOpportunityDensityResult,
    window_count: int,
    peak_summary: _RecommendationPeakSummary,
) -> float:
    top1_share = rolling.top1_counts.get(row.period_band_bars, 0) / window_count
    cv = row.coefficient_of_variation or 0.0
    cv_penalty = 1.0 / (1.0 + max(0.0, cv))
    random95 = row.above_random_95_share
    random95_boost = 1.0 if random95 is None else 0.75 + 0.25 * random95
    _slope, rel_slope, direction = _trend_for_band(rolling, row.period_band_bars)
    trend_boost = 1.0
    if direction == "rising":
        trend_boost = 1.05
    elif direction == "falling" and rel_slope is not None and rel_slope < -0.10:
        trend_boost = 0.90
    stability_boost = 0.50 + 0.25 * row.above_1_share + 0.20 * row.above_12_share
    top_boost = 0.85 + 0.15 * top1_share
    peak_boost = 0.85 + 0.15 * peak_summary.window_share
    sensitivity = peak_summary.bin_sensitivity_score
    sensitivity_boost = 1.0 if sensitivity is None else 0.85 + 0.15 * sensitivity
    return float(
        row.median_ratio
        * stability_boost
        * top_boost
        * peak_boost
        * sensitivity_boost
        * cv_penalty
        * random95_boost
        * trend_boost
    )


def _trend_for_band(
    rolling: RollingOpportunityDensityResult,
    band_label: str,
) -> tuple[float | None, float | None, TrendDirection]:
    ratios: list[float] = []
    for window in rolling.windows:
        band = _band_in_window(window.bands, band_label)
        if band is None or band.density_share_vs_random_median is None:
            continue
        ratios.append(float(band.density_share_vs_random_median))
    if len(ratios) < 2:
        return None, None, "mixed"
    x = np.arange(len(ratios), dtype=np.float64)
    y = np.asarray(ratios, dtype=np.float64)
    slope = float(np.polyfit(x, y, 1)[0])
    median = float(np.median(y))
    relative = slope / median if median != 0.0 else None
    if relative is None:
        direction: TrendDirection = "mixed"
    elif abs(relative) < 0.05:
        direction = "stable"
    elif relative > 0.0:
        direction = "rising"
    else:
        direction = "falling"
    return slope, relative, direction


def _trend_points_from_rolling(
    rolling: RollingOpportunityDensityResult,
) -> list[FilterParameterTrendPoint]:
    points: list[FilterParameterTrendPoint] = []
    for window in rolling.windows:
        top = window.top_bands[0] if window.top_bands else None
        points.append(
            FilterParameterTrendPoint(
                window_label=window.window_label,
                sample_start=window.sample_start,
                sample_end=window.sample_end,
                period_band_bars=top.period_band_bars if top else None,
                density_share_vs_random_median=(
                    top.density_share_vs_random_median if top else None
                ),
                opportunity_normalized_share=(
                    top.opportunity_normalized_share if top else None
                ),
            )
        )
    return points


def _filter_spec_payloads(specs: Sequence[FilterSpec]) -> list[dict[str, object]]:
    return [
        {
            "name": spec.name,
            "family": spec.family,
            "mode": spec.mode,
            "params": dict(spec.params),
            "output_kind": spec.output_kind,
        }
        for spec in specs
    ]


def _recommendation_interpretation(
    row: RollingOpportunityDensityStabilityRow,
    direction: TrendDirection,
    peak_summary: _RecommendationPeakSummary,
) -> str:
    days = row.period_mid_days_equiv
    day_text = f"，分箱中点约 {days:.2f} 个交易日" if days is not None else ""
    center_text = (
        f"密度峰中心≈{peak_summary.center_period_bars:.2f}根K线；"
        f"相邻低谷给出的保留周期区间≈{peak_summary.left_period_bars:.2f}-"
        f"{peak_summary.right_period_bars:.2f}根；"
        f"滤波模式={peak_summary.filter_mode}"
    )
    sensitivity_text = (
        f"，分箱敏感性={peak_summary.bin_sensitivity_score:.2f}"
        if peak_summary.bin_sensitivity_score is not None
        else ""
    )
    return (
        f"{row.period_band_bars} 根K线周期段在滚动窗口中反复呈现单位机会密集"
        f"（相对随机中位数={row.median_ratio:.3g}，"
        f"高于随机中位数窗口占比={row.above_1_share:.0%}{day_text}）；"
        f"{center_text}{sensitivity_text}；趋势方向={direction}。"
        "分箱只作解释标签，应优先用连续曲线的低谷作为高通/低通/带通边界，"
        "再进入下一根K线执行的滤波择时验证。"
    )


def _band_in_window(
    bands: Sequence[CycleOpportunityBand],
    band_label: str,
) -> CycleOpportunityBand | None:
    for band in bands:
        if band.period_band_bars == band_label:
            return band
    return None


def _input_frame(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    timestamp_column: str,
) -> pd.DataFrame:
    frame = (
        pd.DataFrame(rows).copy() if not isinstance(rows, pd.DataFrame) else rows.copy()
    )
    if timestamp_column not in frame.columns:
        raise ValueError(f"Missing timestamp column: {timestamp_column}")
    frame[timestamp_column] = pd.to_datetime(frame[timestamp_column])
    frame = frame.sort_values(timestamp_column)
    return frame


def _median_source_interval_seconds(
    frame: pd.DataFrame,
    *,
    timestamp_column: str,
) -> float | None:
    timestamps = pd.DatetimeIndex(pd.to_datetime(frame[timestamp_column])).sort_values()
    if len(timestamps) < 2:
        return None
    seconds = np.diff(timestamps.view("int64")).astype(np.float64) / 1_000_000_000.0
    seconds = seconds[np.isfinite(seconds) & (seconds > 0.0)]
    if len(seconds) == 0:
        return None
    return float(np.median(seconds))


def _period_supported_by_source(
    period: PeriodName,
    *,
    source_median_seconds: float | None,
    tolerance_ratio: float,
) -> bool:
    if period == "day":
        return True
    if source_median_seconds is None:
        return False
    return source_median_seconds <= PERIOD_SECONDS[period] * tolerance_ratio


def _skipped_period_result(
    *,
    period: PeriodName,
    reason: str,
    source_median_seconds: float | None,
    config: FilterParameterWorkflowConfig,
) -> FilterParameterPeriodWorkflowResult:
    return FilterParameterPeriodWorkflowResult(
        period=period,
        status="skipped",
        skip_reason=reason,
        recommendations=[],
        trend_points=[],
        rolling_density=None,
        metadata={
            "source_median_interval_seconds": source_median_seconds,
            "period_window_policy": _policy_for_period(period, config).to_dict(),
        },
    )


def _period_seed_offset(period: PeriodName) -> int:
    return cast(int, list(DEFAULT_WORKFLOW_PERIODS).index(period) * 10_000)
