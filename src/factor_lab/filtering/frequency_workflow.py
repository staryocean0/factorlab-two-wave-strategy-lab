# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportMissingTypeStubs=false
"""Frequency-first DII discovery for the filter workflow chain.

This module is the new main routing surface for ``workflow-chain``.  It scans
one canonical physical-frequency axis (``T_days`` / ``f=1/T``) across all
allowed K-line carriers, clusters every positive DII ridge representative, and
then projects each representative back to a practical carrier for tool
selection and strategy backtesting.

``period`` therefore means "sampling/execution carrier permission" only.  The
research object is always the physical cycle/trend horizon in trading-day
equivalent units.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Literal

import numpy as np
import pandas as pd

from factor_lab.filtering.directional_information import (
    DirectionalInformationStrength,
    DirectionalInformationSurfaceConfig,
    DirectionalInformationSurfacePoint,
    run_directional_information_surface,
)
from factor_lab.filtering.parameter_workflow import (
    DEFAULT_WORKFLOW_PERIODS,
    PERIOD_BARS_PER_DAY,
    PERIOD_FINE_TO_COARSE_RANK,
    ParameterEvidenceStrength,
)
from factor_lab.filtering.timing_validation import (
    FilterMode,
    PeriodName,
    TimingValidationConfig,
    resample_close_frame,
)

DEFAULT_DII_MIN_BARS_PER_CYCLE = 8.0
DEFAULT_DII_MAX_BARS_PER_CYCLE = 1024.0
DEFAULT_DII_FREQUENCY_GRID_POINTS = 72
DEFAULT_DII_Q_VALUES = (0.707, 1.0, 1.4)
DEFAULT_DII_HORIZON_FRACTIONS = (0.125, 0.25, 0.5)
DEFAULT_DII_FILTER_MODES: tuple[FilterMode, ...] = ("bandpass", "lowpass")
DEFAULT_DII_POSITIVE_ENTRY_THRESHOLD_BPS = 0.0
DEFAULT_DII_MIN_SAMPLE_CYCLES = 3.0
DEFAULT_CARRIER_TARGET_BARS_PER_CYCLE = 40.0

FrequencyCandidateLabel = Literal[
    "thin_exploratory",
    "wide_positive_ridge",
    "sample_out_ready",
    "strong",
]


@dataclass(frozen=True, slots=True)
class DiiFrequencyDiscoveryConfig:
    """Configuration for the frequency-first DII discovery stage."""

    allowed_periods: tuple[PeriodName, ...] = DEFAULT_WORKFLOW_PERIODS
    timestamp_column: str = "timestamp"
    close_column: str = "close"
    min_center_days: float | None = None
    max_center_days: float | None = None
    frequency_grid_points: int = DEFAULT_DII_FREQUENCY_GRID_POINTS
    q_values: tuple[float, ...] = DEFAULT_DII_Q_VALUES
    horizon_fractions: tuple[float, ...] = DEFAULT_DII_HORIZON_FRACTIONS
    filter_modes: tuple[FilterMode, ...] = DEFAULT_DII_FILTER_MODES
    min_bars_per_cycle: float = DEFAULT_DII_MIN_BARS_PER_CYCLE
    max_bars_per_cycle: float = DEFAULT_DII_MAX_BARS_PER_CYCLE
    positive_entry_threshold_bps: float = DEFAULT_DII_POSITIVE_ENTRY_THRESHOLD_BPS
    min_sample_cycles: float = DEFAULT_DII_MIN_SAMPLE_CYCLES
    min_observations: int = 120
    robust_quantile: float = 0.25
    robust_period_neighborhood_pct: float = 0.15
    robust_q_neighborhood_ratio: float = 1.50
    robust_horizon_neighborhood_pct: float = 0.30
    min_edge_bps: float = 5.0
    min_robust_edge_bps: float = 2.0
    min_hit_rate: float = 0.51
    min_abs_direction_corr: float = 0.015
    min_positive_window_share: float = 0.65
    min_stability_windows_for_strong: int = 6
    carrier_target_bars_per_cycle: float = DEFAULT_CARRIER_TARGET_BARS_PER_CYCLE
    single_point_bandwidth_pct: float = 0.15
    enable_tradable_band_consolidation: bool = True
    tradable_band_merge_ratio: float = 1.35

    def __post_init__(self) -> None:
        if not self.allowed_periods:
            raise ValueError("allowed_periods must not be empty")
        for period in self.allowed_periods:
            if period not in PERIOD_FINE_TO_COARSE_RANK:
                raise ValueError(f"Unsupported period: {period}")
        if self.frequency_grid_points <= 1:
            raise ValueError("frequency_grid_points must be > 1")
        if not self.q_values:
            raise ValueError("q_values must not be empty")
        if any(value <= 0.0 or not math.isfinite(value) for value in self.q_values):
            raise ValueError("q_values must be finite and > 0")
        if not self.horizon_fractions:
            raise ValueError("horizon_fractions must not be empty")
        if any(
            value <= 0.0 or not math.isfinite(value) for value in self.horizon_fractions
        ):
            raise ValueError("horizon_fractions must be finite and > 0")
        if not self.filter_modes:
            raise ValueError("filter_modes must not be empty")
        for mode in self.filter_modes:
            if mode not in {"bandpass", "lowpass"}:
                raise ValueError(
                    "frequency discovery supports bandpass and lowpass modes"
                )
        if self.min_bars_per_cycle <= 2.0:
            raise ValueError("min_bars_per_cycle must be > 2")
        if self.max_bars_per_cycle < self.min_bars_per_cycle:
            raise ValueError("max_bars_per_cycle must be >= min_bars_per_cycle")
        if self.min_sample_cycles <= 0.0:
            raise ValueError("min_sample_cycles must be > 0")
        if self.min_observations < 30:
            raise ValueError("min_observations must be >= 30")
        if self.min_center_days is not None and self.min_center_days <= 0.0:
            raise ValueError("min_center_days must be > 0 when provided")
        if self.max_center_days is not None and self.max_center_days <= 0.0:
            raise ValueError("max_center_days must be > 0 when provided")
        if (
            self.min_center_days is not None
            and self.max_center_days is not None
            and self.max_center_days < self.min_center_days
        ):
            raise ValueError("max_center_days must be >= min_center_days")
        if self.carrier_target_bars_per_cycle <= 0.0:
            raise ValueError("carrier_target_bars_per_cycle must be > 0")
        if self.single_point_bandwidth_pct <= 0.0:
            raise ValueError("single_point_bandwidth_pct must be > 0")
        if self.tradable_band_merge_ratio < 1.0:
            raise ValueError("tradable_band_merge_ratio must be >= 1")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DiiFrequencySurfaceProjection:
    """One DII surface projected onto one sampling carrier and filter mode."""

    period: str
    filter_mode: str
    status: str
    center_period_days: list[float]
    center_period_bars: list[float]
    sample_count: int
    bars_per_trading_day: float
    surface: dict[str, object] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DiiFrequencyCandidate:
    """Positive DII ridge representative in canonical physical-frequency space."""

    candidate_id: str
    rank: int
    filter_mode: str
    center_period_days: float
    center_frequency_cycles_per_day: float
    period_lo_days: float
    period_hi_days: float
    best_dii_bps: float
    hit_rate: float
    evidence_strength: DirectionalInformationStrength
    evidence_label: FrequencyCandidateLabel
    parameter_evidence_strength: ParameterEvidenceStrength
    parameter_evidence_strength_label_zh: str
    ridge_point_count: int
    source_periods: list[str]
    source_surface_count: int
    representative_point: dict[str, object]
    tradable_band_member_count: int = 1
    tradable_band_member_ids: tuple[str, ...] = ()
    tradable_band_member_center_days: tuple[float, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DiiCarrierCandidate:
    """A frequency candidate projected to one actual K-line carrier."""

    candidate_id: str
    carrier_rank: int
    period: str
    filter_mode: str
    target_period_lo_bars: float
    target_period_hi_bars: float
    target_center_days: float
    center_frequency_cycles_per_day: float
    center_period_bars: float
    bars_per_trading_day: float
    sample_count: int
    sample_cycles: float
    carrier_score: float
    selected_for_backtest: bool
    best_dii_bps: float
    hit_rate: float
    candidate_evidence_label: FrequencyCandidateLabel
    dii_evidence_strength: DirectionalInformationStrength
    parameter_evidence_strength: ParameterEvidenceStrength
    parameter_evidence_strength_label_zh: str
    pre_strategy_note_zh: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DiiFrequencyWorkflowResult:
    """Reusable artifact for frequency-first DII discovery."""

    index_ref: str
    frequency_surfaces: list[DiiFrequencySurfaceProjection]
    frequency_candidates: list[DiiFrequencyCandidate]
    carrier_candidates: list[DiiCarrierCandidate]
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "index_ref": self.index_ref,
            "frequency_surfaces": [item.to_dict() for item in self.frequency_surfaces],
            "frequency_candidates": [
                item.to_dict() for item in self.frequency_candidates
            ],
            "carrier_candidates": [item.to_dict() for item in self.carrier_candidates],
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class _PeriodSample:
    period: PeriodName
    sample_count: int
    sample_start: str
    sample_end: str
    bars_per_day: float


@dataclass(frozen=True, slots=True)
class _PositivePoint:
    period: str
    filter_mode: str
    point: DirectionalInformationSurfacePoint


def run_dii_full_spectrum_frequency_discovery(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: DiiFrequencyDiscoveryConfig | None = None,
    index_ref: str = "index_series",
) -> DiiFrequencyWorkflowResult:
    """Run DII full-spectrum discovery and carrier projection."""

    cfg = config or DiiFrequencyDiscoveryConfig()
    sample_by_period = _period_samples(rows, config=cfg)
    min_days, max_days = _resolve_frequency_range(sample_by_period, config=cfg)
    grid = _physical_period_grid(
        min_days=min_days,
        max_days=max_days,
        points=cfg.frequency_grid_points,
    )
    surfaces: list[DiiFrequencySurfaceProjection] = []
    positive_points: list[_PositivePoint] = []
    for period in cfg.allowed_periods:
        sample = sample_by_period.get(period)
        if sample is None:
            for mode in cfg.filter_modes:
                surfaces.append(
                    DiiFrequencySurfaceProjection(
                        period=period,
                        filter_mode=mode,
                        status="skipped",
                        center_period_days=[],
                        center_period_bars=[],
                        sample_count=0,
                        bars_per_trading_day=PERIOD_BARS_PER_DAY[period],
                        error="not_enough_observations_for_carrier",
                    )
                )
            continue
        valid_days = [
            days for days in grid if _carrier_valid_for_days(days, sample, config=cfg)
        ]
        center_bars = [days * sample.bars_per_day for days in valid_days]
        for mode in cfg.filter_modes:
            if not valid_days:
                surfaces.append(
                    DiiFrequencySurfaceProjection(
                        period=period,
                        filter_mode=mode,
                        status="skipped",
                        center_period_days=[],
                        center_period_bars=[],
                        sample_count=sample.sample_count,
                        bars_per_trading_day=sample.bars_per_day,
                        error="no_center_period_days_valid_for_carrier",
                    )
                )
                continue
            try:
                surface = run_directional_information_surface(
                    rows,
                    index_ref=index_ref,
                    config=DirectionalInformationSurfaceConfig(
                        period=period,
                        timestamp_column=cfg.timestamp_column,
                        close_column=cfg.close_column,
                        min_observations=max(
                            30,
                            min(cfg.min_observations, sample.sample_count),
                        ),
                        filter_mode=mode,
                        center_period_days=tuple(valid_days),
                        q_values=cfg.q_values,
                        horizon_fractions=cfg.horizon_fractions,
                        robust_quantile=cfg.robust_quantile,
                        robust_period_neighborhood_pct=(
                            cfg.robust_period_neighborhood_pct
                        ),
                        robust_q_neighborhood_ratio=cfg.robust_q_neighborhood_ratio,
                        robust_horizon_neighborhood_pct=(
                            cfg.robust_horizon_neighborhood_pct
                        ),
                        min_edge_bps=cfg.min_edge_bps,
                        min_robust_edge_bps=cfg.min_robust_edge_bps,
                        min_hit_rate=cfg.min_hit_rate,
                        min_abs_direction_corr=cfg.min_abs_direction_corr,
                        min_positive_window_share=cfg.min_positive_window_share,
                        min_stability_windows_for_strong=(
                            cfg.min_stability_windows_for_strong
                        ),
                        top_n=max(
                            1,
                            len(valid_days)
                            * len(cfg.q_values)
                            * len(cfg.horizon_fractions),
                        ),
                    ),
                )
                surface_payload = surface.to_dict()
                surfaces.append(
                    DiiFrequencySurfaceProjection(
                        period=period,
                        filter_mode=mode,
                        status="completed",
                        center_period_days=[float(value) for value in valid_days],
                        center_period_bars=[float(value) for value in center_bars],
                        sample_count=sample.sample_count,
                        bars_per_trading_day=sample.bars_per_day,
                        surface=surface_payload,
                    )
                )
                for point in surface.points:
                    if point.dii_bps > cfg.positive_entry_threshold_bps:
                        positive_points.append(
                            _PositivePoint(
                                period=period,
                                filter_mode=mode,
                                point=point,
                            )
                        )
            except Exception as exc:
                surfaces.append(
                    DiiFrequencySurfaceProjection(
                        period=period,
                        filter_mode=mode,
                        status="failed",
                        center_period_days=[float(value) for value in valid_days],
                        center_period_bars=[float(value) for value in center_bars],
                        sample_count=sample.sample_count,
                        bars_per_trading_day=sample.bars_per_day,
                        error=str(exc),
                    )
                )

    ridge_representatives = _cluster_positive_points(
        positive_points,
        min_days=min_days,
        max_days=max_days,
        config=cfg,
    )
    frequency_candidates = _consolidate_frequency_candidates_into_tradable_bands(
        ridge_representatives,
        config=cfg,
    )
    carrier_candidates = _project_candidates_to_carriers(
        frequency_candidates,
        sample_by_period=sample_by_period,
        config=cfg,
    )
    selected_carriers = [
        item for item in carrier_candidates if item.selected_for_backtest
    ]
    return DiiFrequencyWorkflowResult(
        index_ref=index_ref,
        frequency_surfaces=surfaces,
        frequency_candidates=frequency_candidates,
        carrier_candidates=carrier_candidates,
        metadata={
            "workflow_role": "dii_full_spectrum_frequency_discovery",
            "workflow_version": "frequency_first_dii_v1",
            "index_ref": index_ref,
            "allowed_periods": list(cfg.allowed_periods),
            "frequency_grid": {
                "min_center_days": min_days,
                "max_center_days": max_days,
                "grid_points": cfg.frequency_grid_points,
                "q_values": list(cfg.q_values),
                "horizon_fractions": list(cfg.horizon_fractions),
                "filter_modes": list(cfg.filter_modes),
            },
            "ridge_representative_count_before_band_consolidation": len(
                ridge_representatives
            ),
            "tradable_band_consolidation_policy": {
                "enabled": cfg.enable_tradable_band_consolidation,
                "merge_ratio": cfg.tradable_band_merge_ratio,
                "policy_zh": (
                    "DII 全扫输出的是频谱采样点/山脊代表，不是最终可交易因子；"
                    "进入工具选择和回测前，相邻同 mode 的正山脊代表会合并为"
                    "可交易频段。bandpass 和 lowpass 语义不同，默认不互相合并，"
                    "而是在同一物理频率家族下作为不同表达方式并列验证。"
                ),
            },
            "unit_policy": {
                "canonical_axis": "T_days / f_cycles_per_day",
                "frequency_formula": "f = 1 / T_days",
                "bars_are": "sampling_implementation_coordinate_not_research_object",
                "carrier_formula": "P_bars = T_days * bars_per_trading_day(period)",
                "period_semantics": "allowed_sampling_execution_carriers_only",
                "bars_per_trading_day": dict(PERIOD_BARS_PER_DAY),
            },
            "carrier_validity_policy": {
                "min_bars_per_cycle": cfg.min_bars_per_cycle,
                "max_bars_per_cycle": cfg.max_bars_per_cycle,
                "min_sample_cycles": cfg.min_sample_cycles,
                "carrier_target_bars_per_cycle": cfg.carrier_target_bars_per_cycle,
            },
            "positive_entry_policy": {
                "threshold_bps": cfg.positive_entry_threshold_bps,
                "all_positive_ridge_representatives_enter_band_consolidation": True,
                "downstream_targets_are_tradable_frequency_bands": (
                    cfg.enable_tradable_band_consolidation
                ),
                "strength_changes_reporting_label_not_backtest_eligibility": True,
            },
            "sample_by_period": {
                period: asdict(sample) for period, sample in sample_by_period.items()
            },
            "surface_count": len(surfaces),
            "surface_completed_count": len(
                [item for item in surfaces if item.status == "completed"]
            ),
            "positive_point_count": len(positive_points),
            "frequency_candidate_count": len(frequency_candidates),
            "carrier_candidate_count": len(carrier_candidates),
            "selected_carrier_count": len(selected_carriers),
            "factor_lifecycle_mutation": False,
            "strategy_lifecycle_mutation": False,
        },
    )


def _period_samples(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: DiiFrequencyDiscoveryConfig,
) -> dict[PeriodName, _PeriodSample]:
    samples: dict[PeriodName, _PeriodSample] = {}
    for period in config.allowed_periods:
        try:
            close = resample_close_frame(
                rows,
                config=TimingValidationConfig(
                    period=period,
                    timestamp_column=config.timestamp_column,
                    close_column=config.close_column,
                    min_observations=3,
                ),
            )
        except Exception:
            continue
        if len(close) < max(3, min(config.min_observations, 30)):
            continue
        samples[period] = _PeriodSample(
            period=period,
            sample_count=int(len(close)),
            sample_start=str(close.index[0]),
            sample_end=str(close.index[-1]),
            bars_per_day=PERIOD_BARS_PER_DAY[period],
        )
    return samples


def _resolve_frequency_range(
    samples: Mapping[PeriodName, _PeriodSample],
    *,
    config: DiiFrequencyDiscoveryConfig,
) -> tuple[float, float]:
    if not samples:
        raise ValueError("No allowed periods have enough observations for DII")
    observable_min = min(
        config.min_bars_per_cycle / sample.bars_per_day for sample in samples.values()
    )
    observable_max = max(
        min(
            config.max_bars_per_cycle / sample.bars_per_day,
            sample.sample_count / (sample.bars_per_day * config.min_sample_cycles),
        )
        for sample in samples.values()
    )
    min_days = config.min_center_days or observable_min
    max_days = config.max_center_days or observable_max
    min_days = max(min_days, observable_min)
    max_days = min(max_days, observable_max)
    if max_days < min_days:
        raise ValueError(
            "DII physical frequency range is empty after carrier observability gates"
        )
    return float(min_days), float(max_days)


def _physical_period_grid(
    *,
    min_days: float,
    max_days: float,
    points: int,
) -> tuple[float, ...]:
    if math.isclose(min_days, max_days):
        return (float(min_days),)
    values = np.geomspace(min_days, max_days, num=points)
    return tuple(float(value) for value in values)


def _carrier_valid_for_days(
    center_days: float,
    sample: _PeriodSample,
    *,
    config: DiiFrequencyDiscoveryConfig,
) -> bool:
    center_bars = center_days * sample.bars_per_day
    if center_bars < config.min_bars_per_cycle:
        return False
    if center_bars > config.max_bars_per_cycle:
        return False
    if sample.sample_count / center_bars < config.min_sample_cycles:
        return False
    max_horizon_fraction = max(config.horizon_fractions)
    required_valid = max(30.0, config.min_observations / 4.0)
    # The causal IIR implementation drops roughly 3*P warmup bars and the DII
    # label drops h=phi*P future bars.  Exclude periods that would make any
    # point in the surface abort the entire carrier/mode scan.
    remaining = sample.sample_count - center_bars * (3.0 + max_horizon_fraction)
    return remaining >= required_valid


def _cluster_positive_points(
    points: Sequence[_PositivePoint],
    *,
    min_days: float,
    max_days: float,
    config: DiiFrequencyDiscoveryConfig,
) -> list[DiiFrequencyCandidate]:
    if not points:
        return []
    log_step = (
        (math.log(max_days) - math.log(min_days))
        / max(config.frequency_grid_points - 1, 1)
        if max_days > min_days
        else 0.0
    )
    gap_threshold = max(
        math.log(1.25),
        1.6 * log_step,
        config.robust_period_neighborhood_pct,
    )
    candidates: list[DiiFrequencyCandidate] = []
    for mode in config.filter_modes:
        mode_points = [item for item in points if item.filter_mode == mode]
        mode_points.sort(key=lambda item: item.point.center_period_days)
        positive_runs: list[list[_PositivePoint]] = []
        current: list[_PositivePoint] = []
        previous_days: float | None = None
        for item in mode_points:
            days = item.point.center_period_days
            if (
                previous_days is None
                or abs(math.log(days) - math.log(previous_days)) <= gap_threshold
            ):
                current.append(item)
            else:
                positive_runs.append(current)
                current = [item]
            previous_days = days
        if current:
            positive_runs.append(current)
        for run in positive_runs:
            for representative, cluster in _representative_ridge_slices(run):
                point = representative.point
                period_lo_days, period_hi_days = _cluster_bounds_days(
                    cluster,
                    center_days=point.center_period_days,
                    config=config,
                )
                label = _candidate_label(cluster, point)
                parameter_strength, parameter_label = _parameter_strength_from_dii(
                    point.evidence_strength
                )
                candidates.append(
                    DiiFrequencyCandidate(
                        candidate_id="",
                        rank=0,
                        filter_mode=mode,
                        center_period_days=point.center_period_days,
                        center_frequency_cycles_per_day=(
                            point.center_frequency_cycles_per_day
                        ),
                        period_lo_days=period_lo_days,
                        period_hi_days=period_hi_days,
                        best_dii_bps=point.dii_bps,
                        hit_rate=point.hit_rate,
                        evidence_strength=point.evidence_strength,
                        evidence_label=label,
                        parameter_evidence_strength=parameter_strength,
                        parameter_evidence_strength_label_zh=parameter_label,
                        ridge_point_count=len(cluster),
                        source_periods=sorted({item.period for item in cluster}),
                        source_surface_count=len(
                            {(item.period, item.filter_mode) for item in cluster}
                        ),
                        representative_point=point.to_dict(),
                    )
                )
    candidates = sorted(
        candidates,
        key=lambda item: (
            _label_rank(item.evidence_label),
            _strength_rank(item.evidence_strength),
            item.best_dii_bps,
            item.ridge_point_count,
        ),
        reverse=True,
    )
    return [
        DiiFrequencyCandidate(
            candidate_id=f"freq_{rank:03d}_{candidate.filter_mode}",
            rank=rank,
            filter_mode=candidate.filter_mode,
            center_period_days=candidate.center_period_days,
            center_frequency_cycles_per_day=candidate.center_frequency_cycles_per_day,
            period_lo_days=candidate.period_lo_days,
            period_hi_days=candidate.period_hi_days,
            best_dii_bps=candidate.best_dii_bps,
            hit_rate=candidate.hit_rate,
            evidence_strength=candidate.evidence_strength,
            evidence_label=candidate.evidence_label,
            parameter_evidence_strength=candidate.parameter_evidence_strength,
            parameter_evidence_strength_label_zh=(
                candidate.parameter_evidence_strength_label_zh
            ),
            ridge_point_count=candidate.ridge_point_count,
            source_periods=candidate.source_periods,
            source_surface_count=candidate.source_surface_count,
            representative_point=candidate.representative_point,
        )
        for rank, candidate in enumerate(candidates, start=1)
    ]


def _consolidate_frequency_candidates_into_tradable_bands(
    candidates: Sequence[DiiFrequencyCandidate],
    *,
    config: DiiFrequencyDiscoveryConfig,
) -> list[DiiFrequencyCandidate]:
    """Convert ridge representatives into tradable frequency bands.

    DII full-spectrum scanning deliberately over-samples the physical frequency
    axis.  The positive points and local ridge representatives are evidence
    samples, not final factors.  Before carrier projection and tool selection we
    consolidate adjacent representatives with the same filter mode into one
    tradable band, because the downstream object is a filter passband / cutoff
    region rather than an isolated mathematical frequency point.
    """

    if not candidates or not config.enable_tradable_band_consolidation:
        return list(candidates)
    grouped: list[DiiFrequencyCandidate] = []
    for mode in config.filter_modes:
        mode_candidates = sorted(
            [item for item in candidates if item.filter_mode == mode],
            key=lambda item: item.center_period_days,
        )
        current: list[DiiFrequencyCandidate] = []
        current_hi = -math.inf
        for item in mode_candidates:
            if not current:
                current = [item]
                current_hi = item.period_hi_days
                continue
            adjacent = (
                item.period_lo_days <= current_hi * config.tradable_band_merge_ratio
            )
            close_center = (
                item.center_period_days / current[-1].center_period_days
                <= config.tradable_band_merge_ratio
            )
            if adjacent or close_center:
                current.append(item)
                current_hi = max(current_hi, item.period_hi_days)
            else:
                grouped.append(_merge_frequency_band(current))
                current = [item]
                current_hi = item.period_hi_days
        if current:
            grouped.append(_merge_frequency_band(current))
    grouped = sorted(
        grouped,
        key=lambda item: (
            _label_rank(item.evidence_label),
            _strength_rank(item.evidence_strength),
            item.best_dii_bps,
            item.ridge_point_count,
        ),
        reverse=True,
    )
    return [
        DiiFrequencyCandidate(
            candidate_id=f"freq_{rank:03d}_{candidate.filter_mode}",
            rank=rank,
            filter_mode=candidate.filter_mode,
            center_period_days=candidate.center_period_days,
            center_frequency_cycles_per_day=1.0 / candidate.center_period_days,
            period_lo_days=candidate.period_lo_days,
            period_hi_days=candidate.period_hi_days,
            best_dii_bps=candidate.best_dii_bps,
            hit_rate=candidate.hit_rate,
            evidence_strength=candidate.evidence_strength,
            evidence_label=candidate.evidence_label,
            parameter_evidence_strength=candidate.parameter_evidence_strength,
            parameter_evidence_strength_label_zh=(
                candidate.parameter_evidence_strength_label_zh
            ),
            ridge_point_count=candidate.ridge_point_count,
            source_periods=candidate.source_periods,
            source_surface_count=candidate.source_surface_count,
            representative_point=candidate.representative_point,
            tradable_band_member_count=candidate.tradable_band_member_count,
            tradable_band_member_ids=candidate.tradable_band_member_ids,
            tradable_band_member_center_days=(
                candidate.tradable_band_member_center_days
            ),
        )
        for rank, candidate in enumerate(grouped, start=1)
    ]


def _merge_frequency_band(
    members: Sequence[DiiFrequencyCandidate],
) -> DiiFrequencyCandidate:
    if not members:
        raise ValueError("members must not be empty")
    best = max(
        members,
        key=lambda item: (
            _label_rank(item.evidence_label),
            _strength_rank(item.evidence_strength),
            item.best_dii_bps,
            item.ridge_point_count,
        ),
    )
    lo_days = min(item.period_lo_days for item in members)
    hi_days = max(item.period_hi_days for item in members)
    center_days = math.sqrt(lo_days * hi_days)
    label = max((item.evidence_label for item in members), key=_label_rank)
    strength = max((item.evidence_strength for item in members), key=_strength_rank)
    parameter_strength, parameter_label = _parameter_strength_from_dii(strength)
    source_periods = sorted(
        {period for item in members for period in item.source_periods}
    )
    source_surface_count = len(
        {
            (period, item.filter_mode)
            for item in members
            for period in item.source_periods
        }
    )
    return DiiFrequencyCandidate(
        candidate_id="",
        rank=0,
        filter_mode=best.filter_mode,
        center_period_days=center_days,
        center_frequency_cycles_per_day=1.0 / center_days,
        period_lo_days=lo_days,
        period_hi_days=hi_days,
        best_dii_bps=max(item.best_dii_bps for item in members),
        hit_rate=best.hit_rate,
        evidence_strength=strength,
        evidence_label=label,
        parameter_evidence_strength=parameter_strength,
        parameter_evidence_strength_label_zh=parameter_label,
        ridge_point_count=sum(item.ridge_point_count for item in members),
        source_periods=source_periods,
        source_surface_count=source_surface_count,
        representative_point=best.representative_point,
        tradable_band_member_count=len(members),
        tradable_band_member_ids=tuple(item.candidate_id for item in members),
        tradable_band_member_center_days=tuple(
            float(item.center_period_days) for item in members
        ),
    )


def _representative_ridge_slices(
    run: Sequence[_PositivePoint],
) -> list[tuple[_PositivePoint, list[_PositivePoint]]]:
    """Split one connected positive run into local-ridge representatives.

    A broad positive DII plateau can contain multiple economically distinct
    peaks.  The workflow contract says every positive frequency ridge
    representative should enter downstream validation, so a long sign-connected
    interval must not collapse into only the global maximum.
    """

    if not run:
        return []
    best_by_day: dict[float, _PositivePoint] = {}
    for item in run:
        day = float(item.point.center_period_days)
        incumbent = best_by_day.get(day)
        if incumbent is None or _positive_point_sort_key(
            item
        ) > _positive_point_sort_key(incumbent):
            best_by_day[day] = item
    envelope = sorted(
        best_by_day.values(),
        key=lambda item: item.point.center_period_days,
    )
    if len(envelope) <= 2:
        representative = max(run, key=_positive_point_sort_key)
        return [(representative, list(run))]

    peak_items: list[_PositivePoint] = []
    for index, item in enumerate(envelope):
        score = _ridge_peak_score(item)
        left = _ridge_peak_score(envelope[index - 1]) if index > 0 else -math.inf
        right = (
            _ridge_peak_score(envelope[index + 1])
            if index + 1 < len(envelope)
            else -math.inf
        )
        if score >= left and score >= right:
            peak_items.append(item)
    if not peak_items:
        representative = max(run, key=_positive_point_sort_key)
        return [(representative, list(run))]

    peak_items = sorted(peak_items, key=lambda item: item.point.center_period_days)
    slices: list[tuple[_PositivePoint, list[_PositivePoint]]] = []
    for index, peak in enumerate(peak_items):
        center_days = float(peak.point.center_period_days)
        if index == 0:
            lo_days = min(item.point.center_period_days for item in run)
        else:
            previous_peak_days = float(peak_items[index - 1].point.center_period_days)
            lo_days = math.sqrt(previous_peak_days * center_days)
        if index + 1 == len(peak_items):
            hi_days = max(item.point.center_period_days for item in run)
        else:
            next_peak_days = float(peak_items[index + 1].point.center_period_days)
            hi_days = math.sqrt(center_days * next_peak_days)
        cluster = [
            item
            for item in run
            if lo_days <= float(item.point.center_period_days) <= hi_days
        ]
        if not cluster:
            cluster = [peak]
        representative = max(cluster, key=_positive_point_sort_key)
        slices.append((representative, cluster))
    return slices


def _ridge_peak_score(item: _PositivePoint) -> float:
    point = item.point
    robust = (
        point.robust_dii_quantile_bps
        if point.robust_dii_quantile_bps is not None
        else point.dii_bps
    )
    return float(max(point.dii_bps, robust))


def _positive_point_sort_key(item: _PositivePoint) -> tuple[int, float, float, float]:
    point = item.point
    robust = (
        point.robust_dii_quantile_bps
        if point.robust_dii_quantile_bps is not None
        else -math.inf
    )
    return (
        _strength_rank(point.evidence_strength),
        robust,
        point.dii_bps,
        point.positive_window_share or 0.0,
    )


def _cluster_bounds_days(
    cluster: Sequence[_PositivePoint],
    *,
    center_days: float,
    config: DiiFrequencyDiscoveryConfig,
) -> tuple[float, float]:
    values = [item.point.center_period_days for item in cluster]
    if len(values) == 1:
        return (
            center_days * (1.0 - config.single_point_bandwidth_pct),
            center_days * (1.0 + config.single_point_bandwidth_pct),
        )
    return (min(values), max(values))


def _candidate_label(
    cluster: Sequence[_PositivePoint],
    representative: DirectionalInformationSurfacePoint,
) -> FrequencyCandidateLabel:
    if (
        representative.evidence_strength == "strong_directional_candidate"
        and len(cluster) >= 3
    ):
        return "strong"
    if representative.evidence_strength == "directional_candidate":
        return "sample_out_ready"
    if len(cluster) >= 3:
        return "wide_positive_ridge"
    return "thin_exploratory"


def _parameter_strength_from_dii(
    strength: DirectionalInformationStrength,
) -> tuple[ParameterEvidenceStrength, str]:
    if strength == "strong_directional_candidate":
        return "strong_candidate", "强候选：DII 正山脊宽厚且稳定性较强。"
    if strength == "directional_candidate":
        return "candidate", "候选：DII 正山脊通过基础方向信息门槛。"
    return "weak_candidate", "弱候选：DII 为正但较薄或稳定性不足，仅允许探索。"


def _project_candidates_to_carriers(
    candidates: Sequence[DiiFrequencyCandidate],
    *,
    sample_by_period: Mapping[PeriodName, _PeriodSample],
    config: DiiFrequencyDiscoveryConfig,
) -> list[DiiCarrierCandidate]:
    carriers: list[DiiCarrierCandidate] = []
    for candidate in candidates:
        projected: list[DiiCarrierCandidate] = []
        for period in config.allowed_periods:
            sample = sample_by_period.get(period)
            if sample is None:
                continue
            if not _carrier_valid_for_days(
                candidate.center_period_days,
                sample,
                config=config,
            ):
                continue
            center_bars = candidate.center_period_days * sample.bars_per_day
            lo_bars = max(
                config.min_bars_per_cycle,
                candidate.period_lo_days * sample.bars_per_day,
            )
            hi_bars = min(
                config.max_bars_per_cycle,
                max(lo_bars, candidate.period_hi_days * sample.bars_per_day),
            )
            sample_cycles = sample.sample_count / center_bars
            projected.append(
                DiiCarrierCandidate(
                    candidate_id=candidate.candidate_id,
                    carrier_rank=0,
                    period=period,
                    filter_mode=candidate.filter_mode,
                    target_period_lo_bars=lo_bars,
                    target_period_hi_bars=hi_bars,
                    target_center_days=candidate.center_period_days,
                    center_frequency_cycles_per_day=(
                        candidate.center_frequency_cycles_per_day
                    ),
                    center_period_bars=center_bars,
                    bars_per_trading_day=sample.bars_per_day,
                    sample_count=sample.sample_count,
                    sample_cycles=sample_cycles,
                    carrier_score=_carrier_score(center_bars, sample_cycles, config),
                    selected_for_backtest=False,
                    best_dii_bps=candidate.best_dii_bps,
                    hit_rate=candidate.hit_rate,
                    candidate_evidence_label=candidate.evidence_label,
                    dii_evidence_strength=candidate.evidence_strength,
                    parameter_evidence_strength=candidate.parameter_evidence_strength,
                    parameter_evidence_strength_label_zh=(
                        candidate.parameter_evidence_strength_label_zh
                    ),
                    pre_strategy_note_zh=(
                        f"{period} 只是承载K线；物理周期 T="
                        f"{candidate.center_period_days:.4g} 交易日，"
                        f"实现为约 {center_bars:.2f} 根K线。"
                    ),
                )
            )
        projected = sorted(
            projected,
            key=lambda item: (
                item.carrier_score,
                -PERIOD_FINE_TO_COARSE_RANK[item.period],
            ),
            reverse=True,
        )
        for rank, item in enumerate(projected, start=1):
            carriers.append(
                DiiCarrierCandidate(
                    candidate_id=item.candidate_id,
                    carrier_rank=rank,
                    period=item.period,
                    filter_mode=item.filter_mode,
                    target_period_lo_bars=item.target_period_lo_bars,
                    target_period_hi_bars=item.target_period_hi_bars,
                    target_center_days=item.target_center_days,
                    center_frequency_cycles_per_day=item.center_frequency_cycles_per_day,
                    center_period_bars=item.center_period_bars,
                    bars_per_trading_day=item.bars_per_trading_day,
                    sample_count=item.sample_count,
                    sample_cycles=item.sample_cycles,
                    carrier_score=item.carrier_score,
                    selected_for_backtest=rank == 1,
                    best_dii_bps=item.best_dii_bps,
                    hit_rate=item.hit_rate,
                    candidate_evidence_label=item.candidate_evidence_label,
                    dii_evidence_strength=item.dii_evidence_strength,
                    parameter_evidence_strength=item.parameter_evidence_strength,
                    parameter_evidence_strength_label_zh=(
                        item.parameter_evidence_strength_label_zh
                    ),
                    pre_strategy_note_zh=item.pre_strategy_note_zh,
                )
            )
    return carriers


def _carrier_score(
    center_bars: float,
    sample_cycles: float,
    config: DiiFrequencyDiscoveryConfig,
) -> float:
    bar_score = math.exp(
        -abs(math.log(center_bars / config.carrier_target_bars_per_cycle))
    )
    sample_score = min(1.0, sample_cycles / max(config.min_sample_cycles * 2.0, 1.0))
    return float(bar_score * (0.75 + 0.25 * sample_score))


def _strength_rank(strength: DirectionalInformationStrength) -> int:
    return {
        "no_directional_edge": 0,
        "thin_directional_edge": 1,
        "directional_candidate": 2,
        "strong_directional_candidate": 3,
    }[strength]


def _label_rank(label: FrequencyCandidateLabel) -> int:
    return {
        "thin_exploratory": 0,
        "wide_positive_ridge": 1,
        "sample_out_ready": 2,
        "strong": 3,
    }[label]


def carrier_targets_for_backtest(
    result: DiiFrequencyWorkflowResult,
) -> list[DiiCarrierCandidate]:
    """Return selected carrier candidates in frequency-candidate rank order."""

    return [item for item in result.carrier_candidates if item.selected_for_backtest]
