# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportMissingTypeStubs=false
"""Cycle-opportunity normalized frequency-density diagnostics.

This module is the "calculate first, tune second" front door for filtering
research.  It does **not** rank filters by backtest results.  Instead it asks:
which periods are dense after correcting for the fact that long cycles have fewer
opportunities to appear inside the same sample length?
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from typing import Literal, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from factor_lab.filtering.timing_validation import (
    FilterMode,
    FilterSpec,
    PeriodName,
    TimingValidationConfig,
    resample_close_frame,
)

DEFAULT_CYCLE_PERIOD_BANDS: tuple[tuple[float, float], ...] = (
    (2.0, 3.0),
    (3.0, 5.0),
    (5.0, 8.0),
    (8.0, 13.0),
    (13.0, 21.0),
    (21.0, 34.0),
    (34.0, 55.0),
    (55.0, 89.0),
    (89.0, 144.0),
    (144.0, 233.0),
    (233.0, 377.0),
    (377.0, 610.0),
)


@dataclass(frozen=True, slots=True)
class CycleOpportunityDensityConfig:
    """Protocol for opportunity-normalized frequency-density analysis."""

    period: PeriodName = "day"
    timestamp_column: str = "timestamp"
    close_column: str = "close"
    nperseg: int = 1024
    overlap: float = 0.5
    period_bands: tuple[tuple[float, float], ...] = field(
        default_factory=lambda: DEFAULT_CYCLE_PERIOD_BANDS
    )
    random_baseline_count: int = 0
    random_seed: int = 20260520
    min_cycle_observations: float = 8.0

    def __post_init__(self) -> None:
        if self.nperseg < 32:
            raise ValueError("nperseg must be >= 32")
        if not 0.0 <= self.overlap < 1.0:
            raise ValueError("overlap must be in [0, 1)")
        if self.random_baseline_count < 0:
            raise ValueError("random_baseline_count must be >= 0")
        if self.min_cycle_observations <= 0.0:
            raise ValueError("min_cycle_observations must be > 0")
        for lower, upper in self.period_bands:
            if lower <= 0.0 or upper <= lower:
                raise ValueError("period_bands must be positive increasing ranges")


@dataclass(frozen=True, slots=True)
class CycleOpportunityBand:
    """Opportunity-normalized density summary for one period band."""

    period_band_bars: str
    period_lo_bars: float
    period_hi_bars: float
    frequency_low: float
    frequency_high: float
    raw_power_share: float
    opportunity_normalized_share: float
    density_share_vs_random_median: float | None
    random_q05_share: float | None
    random_median_share: float | None
    random_q95_share: float | None
    above_random_95: bool | None
    below_random_05: bool | None
    eligible_by_min_cycles: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CycleOpportunityPeak:
    """Continuous opportunity-density peak independent of display bins.

    The peak center is the densest representative cycle.  Its left/right
    boundaries are not display-bin edges; they are the nearest smoothed-density
    valleys when available.  Those valleys are the filter cut-off evidence:
    between two valleys we have one retained frequency/period interval.
    """

    rank: int
    center_period_bars: float
    left_period_bars: float
    right_period_bars: float
    peak_density: float
    prominence_ratio: float
    containing_band_bars: str
    bin_sensitivity_score: float
    bin_labels: dict[str, str]
    eligible_by_min_cycles: bool
    left_boundary_source: str = "valley"
    right_boundary_source: str = "valley"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CycleOpportunityValley:
    """Continuous opportunity-density valley used as a filter boundary."""

    rank: int
    period_bars: float
    frequency_cycles_per_bar: float
    valley_density: float
    left_peak_period_bars: float | None
    right_peak_period_bars: float | None
    separation_depth_ratio: float | None
    containing_band_bars: str
    eligible_by_min_cycles: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CycleOpportunityDensityResult:
    """Frequency-density diagnostic result.

    `opportunity_normalized_share` is not the same as total volatility/power
    contribution.  It is computed from `PSD / frequency` so that a four-bar
    cycle is compared against a two-bar cycle after correcting for the fact that
    the four-bar cycle has half as many opportunities to occur in a fixed sample.
    """

    period: str
    bands: list[CycleOpportunityBand]
    peaks: list[CycleOpportunityPeak]
    valleys: list[CycleOpportunityValley]
    spectrum: pd.DataFrame
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "period": self.period,
            "bands": [item.to_dict() for item in self.bands],
            "peaks": [item.to_dict() for item in self.peaks],
            "valleys": [item.to_dict() for item in self.valleys],
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class RollingOpportunityDensityConfig:
    """Rolling-window protocol for opportunity-density stability checks.

    The caller supplies the intended price-adjustment mode in `rows` (for
    example QFQ/adjusted closes) and records it in the research manifest.  This
    object only fixes the statistical protocol.
    """

    density_config: CycleOpportunityDensityConfig = field(
        default_factory=lambda: CycleOpportunityDensityConfig(random_baseline_count=40)
    )
    window_years: int = 3
    step_years: int = 1
    window_months: int | None = None
    step_months: int | None = None
    min_observations: int = 500
    top_band_count: int = 3
    min_vs_random_median: float = 1.0
    require_above_random_95: bool = False
    bars_per_day: float | None = None
    random_seed_step: int = 1
    include_partial_latest: bool = False

    def __post_init__(self) -> None:
        if self.window_years <= 0:
            raise ValueError("window_years must be > 0")
        if self.step_years <= 0:
            raise ValueError("step_years must be > 0")
        if self.window_months is not None and self.window_months <= 0:
            raise ValueError("window_months must be > 0 when provided")
        if self.step_months is not None and self.step_months <= 0:
            raise ValueError("step_months must be > 0 when provided")
        if self.min_observations < 32:
            raise ValueError("min_observations must be >= 32")
        if self.top_band_count <= 0:
            raise ValueError("top_band_count must be > 0")
        if self.min_vs_random_median <= 0.0:
            raise ValueError("min_vs_random_median must be > 0")
        if self.bars_per_day is not None and self.bars_per_day <= 0.0:
            raise ValueError("bars_per_day must be > 0 when provided")


@dataclass(frozen=True, slots=True)
class RollingOpportunityDensityWindow:
    """One rolling training-window opportunity-density result."""

    window_label: str
    start_year: int
    end_year: int
    sample_start: str
    sample_end: str
    sample_count: int
    return_count: int
    bands: list[CycleOpportunityBand]
    top_bands: list[CycleOpportunityBand]
    peaks: list[CycleOpportunityPeak]
    top_peaks: list[CycleOpportunityPeak]
    valleys: list[CycleOpportunityValley]
    top_valleys: list[CycleOpportunityValley]

    def to_dict(self) -> dict[str, object]:
        return {
            "window_label": self.window_label,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "sample_start": self.sample_start,
            "sample_end": self.sample_end,
            "sample_count": self.sample_count,
            "return_count": self.return_count,
            "bands": [band.to_dict() for band in self.bands],
            "top_bands": [band.to_dict() for band in self.top_bands],
            "peaks": [peak.to_dict() for peak in self.peaks],
            "top_peaks": [peak.to_dict() for peak in self.top_peaks],
            "valleys": [valley.to_dict() for valley in self.valleys],
            "top_valleys": [valley.to_dict() for valley in self.top_valleys],
        }


@dataclass(frozen=True, slots=True)
class RollingOpportunityDensityStabilityRow:
    """Cross-window stability summary for one period band."""

    period_band_bars: str
    period_lo_bars: float
    period_hi_bars: float
    period_mid_bars: float
    window_count: int
    mean_ratio: float
    median_ratio: float
    std_ratio: float
    min_ratio: float
    max_ratio: float
    above_1_share: float
    above_12_share: float
    above_15_share: float
    above_random_95_share: float | None
    coefficient_of_variation: float | None
    period_mid_days_equiv: float | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RollingOpportunityDensityResult:
    """Rolling opportunity-density workflow result."""

    period: str
    windows: list[RollingOpportunityDensityWindow]
    stability: list[RollingOpportunityDensityStabilityRow]
    top1_counts: dict[str, int]
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "period": self.period,
            "windows": [window.to_dict() for window in self.windows],
            "stability": [row.to_dict() for row in self.stability],
            "top1_counts": dict(self.top1_counts),
            "metadata": self.metadata,
        }


def compute_cycle_opportunity_density(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: CycleOpportunityDensityConfig | None = None,
) -> CycleOpportunityDensityResult:
    """Compute same-opportunity wave density before filter parameter tuning.

    The core correction is:

    ```text
    opportunities(period tau) ~= sample_length / tau
    density(tau) = observed_wave_power(tau) / opportunities(tau)
                 ∝ PSD(tau) * tau
                 = PSD(f) / f
    ```

    This intentionally differs from a plain frequency-band power-share report.
    """

    cfg = config or CycleOpportunityDensityConfig()
    close = resample_close_frame(
        rows,
        config=TimingValidationConfig(
            period=cfg.period,
            timestamp_column=cfg.timestamp_column,
            close_column=cfg.close_column,
            min_observations=32,
        ),
    )
    if len(close) < 32:
        raise ValueError("Not enough observations for cycle opportunity density")

    log_returns = _log_returns(close)
    freq, psd = _welch_power_spectrum(
        log_returns,
        nperseg=cfg.nperseg,
        overlap=cfg.overlap,
    )
    opportunity_density = psd / freq
    raw_bands = _band_density_rows(
        freq=freq,
        raw_power=psd,
        opportunity_density=opportunity_density,
        period_bands=cfg.period_bands,
        sample_count=len(log_returns),
        min_cycle_observations=cfg.min_cycle_observations,
    )
    bands = _with_random_baseline(raw_bands, log_returns, freq=freq, config=cfg)
    peaks, valleys = _continuous_opportunity_structure(
        freq=freq,
        opportunity_density=opportunity_density,
        period_bands=cfg.period_bands,
        sample_count=len(log_returns),
        min_cycle_observations=cfg.min_cycle_observations,
    )
    spectrum = pd.DataFrame(
        {
            "frequency_cycles_per_bar": freq,
            "period_bars": 1.0 / freq,
            "power_spectral_density": psd,
            "cycle_opportunity_density": opportunity_density,
        }
    )
    return CycleOpportunityDensityResult(
        period=cfg.period,
        bands=bands,
        peaks=peaks,
        valleys=valleys,
        spectrum=spectrum,
        metadata={
            "sample_start": _series_date_label(close, boundary="min"),
            "sample_end": _series_date_label(close, boundary="max"),
            "sample_count": len(close),
            "return_count": len(log_returns),
            "nperseg": min(cfg.nperseg, len(log_returns)),
            "overlap": cfg.overlap,
            "random_baseline_count": cfg.random_baseline_count,
            "density_formula": (
                "cycle_opportunity_density = PSD / frequency = PSD * period"
            ),
            "continuous_peak_selection": (
                "smooth cycle_opportunity_density over log(period), detect local "
                "maxima, then use adjacent local minima/valleys as filter "
                "cut-off boundaries; bins are labels/sensitivity checks only"
            ),
            "continuous_valley_selection": (
                "local minima between dense peaks are the frequency boundaries "
                "for low-pass/high-pass/band-pass retained intervals"
            ),
            "interpretation": (
                "not total power share; corrects for unequal cycle opportunities"
            ),
            "workflow_role": "filter_parameter_frequency_diagnostic",
            "parameter_selection_role": (
                "pre_backtest_candidate_seeding_not_profit_optimization"
            ),
            "factor_lifecycle_mutation": False,
            "strategy_lifecycle_mutation": False,
        },
    )


def compute_rolling_cycle_opportunity_density(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: RollingOpportunityDensityConfig | None = None,
) -> RollingOpportunityDensityResult:
    """Compute opportunity-density stability across rolling calendar windows.

    This is a pre-backtest research artifact: it finds which cycle bands are
    repeatedly dense under equal-opportunity normalization, then later filter
    validation decides whether those candidate parameters are useful.
    """

    cfg = config or RollingOpportunityDensityConfig()
    density_cfg = cfg.density_config
    close = resample_close_frame(
        rows,
        config=TimingValidationConfig(
            period=density_cfg.period,
            timestamp_column=density_cfg.timestamp_column,
            close_column=density_cfg.close_column,
            min_observations=32,
        ),
    )
    if len(close) < cfg.min_observations:
        raise ValueError("Not enough observations for rolling opportunity density")

    window_months = cfg.window_months or cfg.window_years * 12
    step_months = cfg.step_months or cfg.step_years * 12
    windows: list[RollingOpportunityDensityWindow] = []
    window_index = 0
    for window_start, window_end_exclusive in _calendar_windows(
        close,
        window_months=window_months,
        step_months=step_months,
        include_partial_latest=cfg.include_partial_latest,
    ):
        sample = close[
            (close.index >= window_start) & (close.index < window_end_exclusive)
        ]
        if len(sample) < cfg.min_observations:
            window_index += 1
            continue

        window_density_cfg = replace(
            density_cfg,
            random_seed=density_cfg.random_seed + window_index * cfg.random_seed_step,
        )
        density_result = compute_cycle_opportunity_density(
            pd.DataFrame(
                {
                    density_cfg.timestamp_column: sample.index,
                    density_cfg.close_column: sample.to_numpy(dtype=np.float64),
                }
            ),
            config=window_density_cfg,
        )
        top_bands = suggest_opportunity_dense_bands(
            density_result,
            min_vs_random_median=cfg.min_vs_random_median,
            require_above_random_95=cfg.require_above_random_95,
        )[: cfg.top_band_count]
        top_peaks = density_result.peaks[: cfg.top_band_count]
        top_valleys = density_result.valleys[: cfg.top_band_count]
        windows.append(
            RollingOpportunityDensityWindow(
                window_label=_window_label(window_start, window_end_exclusive),
                start_year=int(window_start.year),
                end_year=int((window_end_exclusive - pd.Timedelta(days=1)).year),
                sample_start=str(density_result.metadata["sample_start"]),
                sample_end=str(density_result.metadata["sample_end"]),
                sample_count=int(density_result.metadata["sample_count"]),
                return_count=int(density_result.metadata["return_count"]),
                bands=density_result.bands,
                top_bands=top_bands,
                peaks=density_result.peaks,
                top_peaks=top_peaks,
                valleys=density_result.valleys,
                top_valleys=top_valleys,
            )
        )
        window_index += 1

    if not windows:
        raise ValueError("No rolling opportunity-density windows had enough data")

    return RollingOpportunityDensityResult(
        period=density_cfg.period,
        windows=windows,
        stability=_rolling_stability_rows(windows, bars_per_day=cfg.bars_per_day),
        top1_counts=_rolling_top1_counts(windows),
        metadata={
            "workflow_role": "rolling_filter_parameter_frequency_diagnostic",
            "parameter_selection_role": (
                "pre_backtest_candidate_seeding_not_profit_optimization"
            ),
            "window_years": cfg.window_years,
            "step_years": cfg.step_years,
            "window_months": window_months,
            "step_months": step_months,
            "windowing_mode": (
                "blocked" if step_months >= window_months else "rolling_overlap"
            ),
            "min_observations": cfg.min_observations,
            "top_band_count": cfg.top_band_count,
            "min_vs_random_median": cfg.min_vs_random_median,
            "require_above_random_95": cfg.require_above_random_95,
            "bars_per_day": cfg.bars_per_day,
            "random_seed_step": cfg.random_seed_step,
            "include_partial_latest": cfg.include_partial_latest,
            "window_count": len(windows),
            "sample_start": _series_date_label(close, boundary="min"),
            "sample_end": _series_date_label(close, boundary="max"),
            "density_formula": (
                "cycle_opportunity_density = PSD / frequency = PSD * period"
            ),
            "adjustment_manifest_required": True,
            "adjustment_policy": (
                "caller_supplied_adjusted_or_raw_close; QFQ/adjusted closes "
                "are the default for CloudRidge production research, raw daily "
                "is legacy background evidence only"
            ),
            "factor_lifecycle_mutation": False,
            "strategy_lifecycle_mutation": False,
        },
    )


def _calendar_windows(
    close: pd.Series,
    *,
    window_months: int,
    step_months: int,
    include_partial_latest: bool,
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    first = pd.Timestamp(close.index.min())
    last = pd.Timestamp(close.index.max())
    start = pd.Timestamp(year=first.year, month=first.month, day=1)
    windows: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    while start <= last:
        end = start + pd.DateOffset(months=window_months)
        if not include_partial_latest and end > last + pd.Timedelta(days=1):
            break
        if end <= first:
            start = start + pd.DateOffset(months=step_months)
            continue
        windows.append((start, cast(pd.Timestamp, end)))
        start = start + pd.DateOffset(months=step_months)
    return windows


def _window_label(
    window_start: pd.Timestamp,
    window_end_exclusive: pd.Timestamp,
) -> str:
    end = window_end_exclusive - pd.Timedelta(days=1)
    if window_start.month == 1 and end.month == 12:
        return f"{window_start.year}-{end.year}"
    return f"{window_start:%Y-%m}_{end:%Y-%m}"


def _continuous_opportunity_structure(
    *,
    freq: NDArray[np.float64],
    opportunity_density: NDArray[np.float64],
    period_bands: tuple[tuple[float, float], ...],
    sample_count: int,
    min_cycle_observations: float,
    max_peaks: int = 5,
) -> tuple[list[CycleOpportunityPeak], list[CycleOpportunityValley]]:
    """Detect peaks and boundary valleys on a smoothed continuous density curve.

    Band rows remain useful for summaries, but peak centers should come from the
    continuous curve.  Filter pass intervals should be bounded by local minima
    (valleys), not by human-chosen display bins.
    """

    if len(freq) == 0:
        return [], []
    period = 1.0 / freq
    min_period = min(lower for lower, _upper in period_bands)
    max_period = max(upper for _lower, upper in period_bands)
    eligible = (
        np.isfinite(period)
        & np.isfinite(opportunity_density)
        & (opportunity_density > 0.0)
        & (period >= min_period)
        & (period <= max_period)
        & ((sample_count / period) >= min_cycle_observations)
    )
    if int(np.sum(eligible)) < 3:
        return [], []

    sorted_index = np.argsort(period[eligible])
    period_sorted = period[eligible][sorted_index]
    density_sorted = opportunity_density[eligible][sorted_index]
    log_period = np.log(period_sorted)
    if len(np.unique(log_period)) < 3:
        return [], []

    grid_count = max(64, min(512, int(len(log_period) * 2)))
    grid = np.linspace(float(log_period.min()), float(log_period.max()), grid_count)
    interpolated = np.interp(grid, log_period, density_sorted)
    smoothed = _smooth_curve(interpolated)
    if not np.any(np.isfinite(smoothed)) or float(np.nanmax(smoothed)) <= 0.0:
        return [], []

    finite_positive = smoothed[np.isfinite(smoothed) & (smoothed > 0.0)]
    baseline = float(np.median(finite_positive)) if len(finite_positive) else 0.0
    local_maxima = [
        index
        for index in range(1, len(smoothed) - 1)
        if smoothed[index] >= smoothed[index - 1]
        and smoothed[index] >= smoothed[index + 1]
    ]
    if not local_maxima:
        local_maxima = [int(np.argmax(smoothed))]
    local_minima = [
        index
        for index in range(1, len(smoothed) - 1)
        if smoothed[index] <= smoothed[index - 1]
        and smoothed[index] <= smoothed[index + 1]
    ]
    local_maxima = sorted(
        local_maxima,
        key=lambda index: float(smoothed[index]),
        reverse=True,
    )

    valleys = _continuous_valleys_from_curve(
        grid=grid,
        smoothed=smoothed,
        local_maxima=local_maxima,
        local_minima=local_minima,
        period_bands=period_bands,
    )

    selected: list[CycleOpportunityPeak] = []
    for index in local_maxima:
        center = float(math.exp(grid[index]))
        if any(
            _periods_too_close(center, peak.center_period_bars)
            for peak in selected
        ):
                continue
        peak_density = float(smoothed[index])
        left_candidates = [
            candidate for candidate in local_minima if candidate < index
        ]
        right_candidates = [
            candidate for candidate in local_minima if candidate > index
        ]
        left_index = left_candidates[-1] if left_candidates else 0
        right_index = right_candidates[0] if right_candidates else len(smoothed) - 1
        labels, sensitivity = _bin_sensitivity_for_period(
            center,
            period_bands=period_bands,
        )
        selected.append(
            CycleOpportunityPeak(
                rank=len(selected) + 1,
                center_period_bars=center,
                left_period_bars=float(math.exp(grid[left_index])),
                right_period_bars=float(math.exp(grid[right_index])),
                peak_density=peak_density,
                prominence_ratio=(
                    peak_density / baseline if baseline > 0.0 else math.inf
                ),
                containing_band_bars=labels["default"],
                bin_sensitivity_score=sensitivity,
                bin_labels=labels,
                eligible_by_min_cycles=True,
                left_boundary_source="valley" if left_candidates else "edge",
                right_boundary_source="valley" if right_candidates else "edge",
            )
        )
        if len(selected) >= max_peaks:
            break
    return selected, valleys


def _continuous_valleys_from_curve(
    *,
    grid: NDArray[np.float64],
    smoothed: NDArray[np.float64],
    local_maxima: Sequence[int],
    local_minima: Sequence[int],
    period_bands: tuple[tuple[float, float], ...],
) -> list[CycleOpportunityValley]:
    valleys: list[CycleOpportunityValley] = []
    maxima_by_position = sorted(local_maxima)
    for index in local_minima:
        left_maxima = [
            candidate for candidate in maxima_by_position if candidate < index
        ]
        right_maxima = [
            candidate for candidate in maxima_by_position if candidate > index
        ]
        left_peak_index = left_maxima[-1] if left_maxima else None
        right_peak_index = right_maxima[0] if right_maxima else None
        valley_density = float(smoothed[index])
        if left_peak_index is not None and right_peak_index is not None:
            adjacent_peak_density = min(
                float(smoothed[left_peak_index]),
                float(smoothed[right_peak_index]),
            )
            separation_depth_ratio = (
                valley_density / adjacent_peak_density
                if adjacent_peak_density > 0.0
                else None
            )
        else:
            separation_depth_ratio = None
        period = float(math.exp(grid[index]))
        labels, _sensitivity = _bin_sensitivity_for_period(
            period,
            period_bands=period_bands,
        )
        valleys.append(
            CycleOpportunityValley(
                rank=0,
                period_bars=period,
                frequency_cycles_per_bar=1.0 / period,
                valley_density=valley_density,
                left_peak_period_bars=(
                    float(math.exp(grid[left_peak_index]))
                    if left_peak_index is not None
                    else None
                ),
                right_peak_period_bars=(
                    float(math.exp(grid[right_peak_index]))
                    if right_peak_index is not None
                    else None
                ),
                separation_depth_ratio=separation_depth_ratio,
                containing_band_bars=labels["default"],
                eligible_by_min_cycles=True,
            )
        )
    ranked = sorted(
        valleys,
        key=lambda item: (
            item.separation_depth_ratio
            if item.separation_depth_ratio is not None
            else math.inf,
            item.period_bars,
        ),
    )
    return [
        CycleOpportunityValley(
            rank=rank,
            period_bars=item.period_bars,
            frequency_cycles_per_bar=item.frequency_cycles_per_bar,
            valley_density=item.valley_density,
            left_peak_period_bars=item.left_peak_period_bars,
            right_peak_period_bars=item.right_peak_period_bars,
            separation_depth_ratio=item.separation_depth_ratio,
            containing_band_bars=item.containing_band_bars,
            eligible_by_min_cycles=item.eligible_by_min_cycles,
        )
        for rank, item in enumerate(ranked, start=1)
    ]


def _smooth_curve(values: NDArray[np.float64]) -> NDArray[np.float64]:
    window = max(3, min(21, int(len(values) * 0.03)))
    if window % 2 == 0:
        window += 1
    if len(values) < window:
        return values.astype(np.float64, copy=True)
    kernel = np.ones(window, dtype=np.float64) / float(window)
    padded = np.pad(values, (window // 2, window // 2), mode="edge")
    return cast(NDArray[np.float64], np.convolve(padded, kernel, mode="valid"))


def _periods_too_close(left: float, right: float) -> bool:
    ratio = max(left, right) / max(1e-12, min(left, right))
    return ratio < 1.18


def _bin_sensitivity_for_period(
    period: float,
    *,
    period_bands: tuple[tuple[float, float], ...],
) -> tuple[dict[str, str], float]:
    min_period = min(lower for lower, _upper in period_bands)
    max_period = max(upper for _lower, upper in period_bands)
    grids = {
        "default": period_bands,
        "log_equal": _log_period_grid(min_period, max_period, len(period_bands)),
        "log_shifted": _shifted_log_period_grid(
            min_period,
            max_period,
            len(period_bands),
        ),
        "log_fine": _log_period_grid(min_period, max_period, len(period_bands) * 2),
    }
    labels: dict[str, str] = {}
    margins: list[float] = []
    for name, grid in grids.items():
        lower, upper = _containing_interval(period, grid)
        labels[name] = _period_band_label(lower, upper)
        margins.append(_boundary_margin_score(period, lower=lower, upper=upper))
    return labels, float(np.mean(np.asarray(margins, dtype=np.float64)))


def _log_period_grid(
    min_period: float,
    max_period: float,
    bin_count: int,
) -> tuple[tuple[float, float], ...]:
    edges = np.exp(
        np.linspace(math.log(min_period), math.log(max_period), bin_count + 1)
    )
    return tuple(
        (float(edges[index]), float(edges[index + 1])) for index in range(bin_count)
    )


def _shifted_log_period_grid(
    min_period: float,
    max_period: float,
    bin_count: int,
) -> tuple[tuple[float, float], ...]:
    ratio = (max_period / min_period) ** (1.0 / float(bin_count))
    shifted_min = min_period / math.sqrt(ratio)
    shifted_max = max_period * math.sqrt(ratio)
    return _log_period_grid(shifted_min, shifted_max, bin_count)


def _containing_interval(
    period: float,
    bands: tuple[tuple[float, float], ...],
) -> tuple[float, float]:
    for lower, upper in bands:
        if lower <= period < upper:
            return lower, upper
    if period < bands[0][0]:
        return bands[0]
    return bands[-1]


def _boundary_margin_score(period: float, *, lower: float, upper: float) -> float:
    if not lower < period < upper or lower <= 0.0 or upper <= lower:
        return 0.0
    half_width = 0.5 * math.log(upper / lower)
    if half_width <= 0.0:
        return 0.0
    margin = min(math.log(period / lower), math.log(upper / period))
    return float(np.clip(margin / half_width, 0.0, 1.0))


def _period_band_label(lower: float, upper: float) -> str:
    return f"{lower:g}-{upper:g}"


def suggest_opportunity_dense_bands(
    result: CycleOpportunityDensityResult,
    *,
    min_vs_random_median: float = 1.0,
    require_above_random_95: bool = False,
) -> list[CycleOpportunityBand]:
    """Return bands that should seed filter parameters before backtest battle."""

    candidates: list[CycleOpportunityBand] = []
    for band in result.bands:
        if not band.eligible_by_min_cycles:
            continue
        ratio = band.density_share_vs_random_median
        if ratio is None or ratio < min_vs_random_median:
            continue
        if require_above_random_95 and band.above_random_95 is not True:
            continue
        candidates.append(band)
    return sorted(
        candidates,
        key=lambda item: item.density_share_vs_random_median or -math.inf,
        reverse=True,
    )


def filter_specs_from_opportunity_bands(
    bands: Sequence[CycleOpportunityBand],
    *,
    min_vs_random_median: float = 1.0,
    require_above_random_95: bool = False,
    include_ema: bool = True,
    include_fourier: bool = True,
    include_iir: bool = True,
    include_wavelet: bool = True,
    min_fourier_window: int = 64,
    max_fourier_window: int = 512,
    max_wavelet_window: int = 512,
) -> list[FilterSpec]:
    """Create first-pass filter specs from opportunity-dense period bands.

    This is intentionally a seeding function, not a validation result.  It
    converts statistically dense period bands into causal EMA baseline,
    rolling-Fourier, IIR, and Haar-wavelet candidates; `run_filter_timing_validation`
    must still evaluate them with the normal next-bar execution protocol.
    """

    specs: list[FilterSpec] = []
    seen_names: set[str] = set()
    for band in bands:
        if not band.eligible_by_min_cycles:
            continue
        ratio = band.density_share_vs_random_median
        if ratio is not None and ratio < min_vs_random_median:
            continue
        if require_above_random_95 and band.above_random_95 is not True:
            continue
        low_period = max(2, int(round(band.period_lo_bars)))
        high_period = max(low_period + 1, int(round(band.period_hi_bars)))
        center_period = max(2, int(round(math.sqrt(low_period * high_period))))
        if include_ema:
            _append_unique_filter_spec(
                specs,
                seen_names,
                FilterSpec(
                    f"opp_ema_lp_s{center_period}",
                    "ema_baseline",
                    "lowpass",
                    {"span": center_period},
                ),
            )
        if include_fourier:
            window = _bounded_power_of_two(
                max(min_fourier_window, int(math.ceil(high_period * 4.0))),
                lower=min_fourier_window,
                upper=max_fourier_window,
            )
            if high_period <= window:
                _append_unique_filter_spec(
                    specs,
                    seen_names,
                    FilterSpec(
                        f"opp_fft_bp_w{window}_p{low_period}_{high_period}",
                        "fourier_rolling",
                        "bandpass",
                        {
                            "window": window,
                            "low_period": low_period,
                            "high_period": high_period,
                        },
                        "component",
                    )
                )
        if include_iir:
            _append_unique_filter_spec(
                specs,
                seen_names,
                FilterSpec(
                    f"opp_iir_bp_p{center_period}_q1p0",
                    "laplace_iir",
                    "bandpass",
                    {"period": center_period, "q": 1.0},
                    "component",
                )
            )
        if include_wavelet:
            wavelet_spec = _wavelet_spec_for_period_band(
                low_period=low_period,
                high_period=high_period,
                max_window=max_wavelet_window,
            )
            if wavelet_spec is not None:
                _append_unique_filter_spec(specs, seen_names, wavelet_spec)
    return specs


def filter_specs_from_opportunity_period_interval(
    *,
    period_lo_bars: float,
    period_hi_bars: float,
    mode: FilterMode,
    include_ema: bool = True,
    include_fourier: bool = True,
    include_iir: bool = True,
    include_wavelet: bool = True,
    min_fourier_window: int = 64,
    max_fourier_window: int = 512,
    max_wavelet_window: int = 512,
) -> list[FilterSpec]:
    """Create filter specs from a valley-bounded retained period interval.

    Periods are in bars.  `lowpass` preserves long periods at/above
    `period_lo_bars`; `highpass` preserves short periods at/below
    `period_hi_bars`; `bandpass` preserves periods between both valley
    boundaries.
    """

    if period_lo_bars <= 0.0 or period_hi_bars <= 0.0:
        raise ValueError("period interval must be positive")
    if period_hi_bars < period_lo_bars:
        raise ValueError("period_hi_bars must be >= period_lo_bars")
    specs: list[FilterSpec] = []
    seen_names: set[str] = set()
    low_period = max(2, int(round(period_lo_bars)))
    high_period = max(low_period + 1, int(round(period_hi_bars)))
    center_period = max(2, int(round(math.sqrt(low_period * high_period))))
    if mode == "bandpass":
        band = CycleOpportunityBand(
            period_band_bars=f"{period_lo_bars:g}-{period_hi_bars:g}",
            period_lo_bars=period_lo_bars,
            period_hi_bars=period_hi_bars,
            frequency_low=1.0 / period_hi_bars,
            frequency_high=1.0 / period_lo_bars,
            raw_power_share=0.0,
            opportunity_normalized_share=0.0,
            density_share_vs_random_median=1.0,
            random_q05_share=None,
            random_median_share=None,
            random_q95_share=None,
            above_random_95=None,
            below_random_05=None,
            eligible_by_min_cycles=True,
        )
        return filter_specs_from_opportunity_bands(
            [band],
            include_ema=include_ema,
            include_fourier=include_fourier,
            include_iir=include_iir,
            include_wavelet=include_wavelet,
            min_fourier_window=min_fourier_window,
            max_fourier_window=max_fourier_window,
            max_wavelet_window=max_wavelet_window,
        )

    cutoff_period = low_period if mode == "lowpass" else high_period
    if include_ema and mode == "lowpass":
        _append_unique_filter_spec(
            specs,
            seen_names,
            FilterSpec(
                f"opp_ema_lp_s{cutoff_period}",
                "ema_baseline",
                "lowpass",
                {"span": cutoff_period},
            ),
        )
    if include_fourier:
        window = _bounded_power_of_two(
            max(min_fourier_window, int(math.ceil(cutoff_period * 4.0))),
            lower=min_fourier_window,
            upper=max_fourier_window,
        )
        _append_unique_filter_spec(
            specs,
            seen_names,
            FilterSpec(
                f"opp_fft_{'lp' if mode == 'lowpass' else 'hp'}"
                f"_w{window}_p{cutoff_period}",
                "fourier_rolling",
                mode,
                {"window": window, "cutoff_period": cutoff_period},
                "level" if mode == "lowpass" else "component",
            ),
        )
    if include_iir:
        _append_unique_filter_spec(
            specs,
            seen_names,
            FilterSpec(
                f"opp_iir_{'lp' if mode == 'lowpass' else 'hp'}_p{cutoff_period}",
                "laplace_iir",
                mode,
                {"period": cutoff_period, "q": 1.0 / math.sqrt(2.0)},
                "level" if mode == "lowpass" else "component",
            ),
        )
    if include_wavelet:
        wavelet_spec = _wavelet_spec_for_cutoff(
            cutoff_period=cutoff_period,
            mode=mode,
            max_window=max_wavelet_window,
        )
        if wavelet_spec is not None:
            _append_unique_filter_spec(specs, seen_names, wavelet_spec)
    # For broad edge-bounded intervals center_period is still useful for payload
    # readability; keep it referenced to avoid silently drifting from bandpass
    # naming semantics.
    _ = center_period
    return specs


def _append_unique_filter_spec(
    specs: list[FilterSpec], seen_names: set[str], spec: FilterSpec
) -> None:
    if spec.name in seen_names:
        return
    seen_names.add(spec.name)
    specs.append(spec)


def _wavelet_spec_for_period_band(
    *, low_period: int, high_period: int, max_window: int
) -> FilterSpec | None:
    if max_window < 64:
        raise ValueError("max_wavelet_window must be >= 64")
    fast_level = max(1, int(math.floor(math.log2(max(2, low_period)))))
    slow_level = max(fast_level + 1, int(math.ceil(math.log2(max(3, high_period)))))
    slow_scale = 2**slow_level
    if slow_scale > max_window:
        return None
    window = _bounded_power_of_two(
        max(64, slow_scale * 4),
        lower=64,
        upper=max_window,
    )
    return FilterSpec(
        f"opp_haar_bp_l{fast_level}_l{slow_level}_w{window}",
        "wavelet_haar",
        "bandpass",
        {"window": window, "level": fast_level, "slow_level": slow_level},
        "component",
    )


def _wavelet_spec_for_cutoff(
    *, cutoff_period: int, mode: FilterMode, max_window: int
) -> FilterSpec | None:
    if mode == "bandpass":
        raise ValueError("bandpass cutoff should use _wavelet_spec_for_period_band")
    if max_window < 64:
        raise ValueError("max_wavelet_window must be >= 64")
    level = max(1, int(round(math.log2(max(2, cutoff_period)))))
    scale = 2**level
    if scale > max_window:
        return None
    window = _bounded_power_of_two(
        max(64, scale * 4),
        lower=64,
        upper=max_window,
    )
    label = "lp" if mode == "lowpass" else "hp"
    return FilterSpec(
        f"opp_haar_{label}_l{level}_w{window}",
        "wavelet_haar",
        mode,
        {"window": window, "level": level},
        "level" if mode == "lowpass" else "component",
    )


def _rolling_stability_rows(
    windows: Sequence[RollingOpportunityDensityWindow],
    *,
    bars_per_day: float | None,
) -> list[RollingOpportunityDensityStabilityRow]:
    band_order = [
        band.period_band_bars
        for band in windows[0].bands
        if band.density_share_vs_random_median is not None
    ]
    rows: list[RollingOpportunityDensityStabilityRow] = []
    for band_label in band_order:
        band_samples = [
            band
            for window in windows
            for band in window.bands
            if (
                band.period_band_bars == band_label
                and band.eligible_by_min_cycles
                and band.density_share_vs_random_median is not None
            )
        ]
        if not band_samples:
            continue
        ratios = np.asarray(
            [
                band.density_share_vs_random_median
                for band in band_samples
                if band.density_share_vs_random_median is not None
            ],
            dtype=np.float64,
        )
        if len(ratios) == 0:
            continue
        first = band_samples[0]
        period_mid_bars = math.sqrt(first.period_lo_bars * first.period_hi_bars)
        mean_ratio = float(np.mean(ratios))
        std_ratio = float(np.std(ratios, ddof=0))
        above_random_flags = [
            band.above_random_95
            for band in band_samples
            if band.above_random_95 is not None
        ]
        rows.append(
            RollingOpportunityDensityStabilityRow(
                period_band_bars=band_label,
                period_lo_bars=first.period_lo_bars,
                period_hi_bars=first.period_hi_bars,
                period_mid_bars=period_mid_bars,
                window_count=len(ratios),
                mean_ratio=mean_ratio,
                median_ratio=float(np.median(ratios)),
                std_ratio=std_ratio,
                min_ratio=float(np.min(ratios)),
                max_ratio=float(np.max(ratios)),
                above_1_share=float(np.mean(ratios >= 1.0)),
                above_12_share=float(np.mean(ratios >= 1.2)),
                above_15_share=float(np.mean(ratios >= 1.5)),
                above_random_95_share=(
                    float(np.mean(np.asarray(above_random_flags, dtype=bool)))
                    if above_random_flags
                    else None
                ),
                coefficient_of_variation=(
                    std_ratio / abs(mean_ratio) if mean_ratio != 0.0 else None
                ),
                period_mid_days_equiv=(
                    period_mid_bars / bars_per_day
                    if bars_per_day is not None
                    else None
                ),
            )
        )
    return sorted(
        rows,
        key=lambda item: (
            item.median_ratio,
            item.above_12_share,
            -item.period_mid_bars,
        ),
        reverse=True,
    )


def _rolling_top1_counts(
    windows: Sequence[RollingOpportunityDensityWindow],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for window in windows:
        if not window.top_bands:
            continue
        band_label = window.top_bands[0].period_band_bars
        counts[band_label] = counts.get(band_label, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _log_returns(close: pd.Series) -> NDArray[np.float64]:
    log_close = np.log(close.to_numpy(dtype=np.float64))
    returns = np.diff(log_close)
    return cast(NDArray[np.float64], returns[np.isfinite(returns)])


def _welch_power_spectrum(
    values: NDArray[np.float64],
    *,
    nperseg: int,
    overlap: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    if len(values) < 32:
        raise ValueError("Not enough values for Welch spectrum")
    segment_length = min(nperseg, len(values))
    step = max(1, int(segment_length * (1.0 - overlap)))
    starts = list(range(0, len(values) - segment_length + 1, step)) or [0]
    window = np.hanning(segment_length)
    scale = float(np.sum(window**2))
    spectra: list[NDArray[np.float64]] = []
    for start in starts:
        segment = values[start : start + segment_length]
        segment = segment - float(np.mean(segment))
        transformed = np.fft.rfft(segment * window)
        power = ((np.abs(transformed) ** 2) / scale).astype(np.float64, copy=False)
        spectra.append(power)
    freq = np.asarray(np.fft.rfftfreq(segment_length, d=1.0), dtype=np.float64)
    average = np.asarray(np.mean(np.vstack(spectra), axis=0), dtype=np.float64)
    return freq[1:], average[1:]


def _band_density_rows(
    *,
    freq: NDArray[np.float64],
    raw_power: NDArray[np.float64],
    opportunity_density: NDArray[np.float64],
    period_bands: tuple[tuple[float, float], ...],
    sample_count: int,
    min_cycle_observations: float,
) -> list[CycleOpportunityBand]:
    dfreq = _frequency_step(freq)
    raw_total = float(np.sum(raw_power) * dfreq)
    density_total = float(np.sum(opportunity_density) * dfreq)
    rows: list[CycleOpportunityBand] = []
    for lower_period, upper_period in period_bands:
        frequency_low = 1.0 / upper_period
        frequency_high = 1.0 / lower_period
        mask = (freq >= frequency_low) & (freq < frequency_high)
        raw_share = _share(raw_power, mask=mask, total=raw_total, dfreq=dfreq)
        density_share = _share(
            opportunity_density,
            mask=mask,
            total=density_total,
            dfreq=dfreq,
        )
        representative_period = math.sqrt(lower_period * upper_period)
        eligible = (sample_count / representative_period) >= min_cycle_observations
        rows.append(
            CycleOpportunityBand(
                period_band_bars=f"{lower_period:g}-{upper_period:g}",
                period_lo_bars=lower_period,
                period_hi_bars=upper_period,
                frequency_low=frequency_low,
                frequency_high=frequency_high,
                raw_power_share=raw_share,
                opportunity_normalized_share=density_share,
                density_share_vs_random_median=None,
                random_q05_share=None,
                random_median_share=None,
                random_q95_share=None,
                above_random_95=None,
                below_random_05=None,
                eligible_by_min_cycles=eligible,
            )
        )
    return rows


def _with_random_baseline(
    raw_bands: list[CycleOpportunityBand],
    log_returns: NDArray[np.float64],
    *,
    freq: NDArray[np.float64],
    config: CycleOpportunityDensityConfig,
) -> list[CycleOpportunityBand]:
    if config.random_baseline_count == 0:
        return raw_bands
    rng = np.random.default_rng(config.random_seed)
    random_shares: list[NDArray[np.float64]] = []
    for _ in range(config.random_baseline_count):
        shuffled = rng.permutation(log_returns)
        shuffled_freq, shuffled_psd = _welch_power_spectrum(
            shuffled,
            nperseg=config.nperseg,
            overlap=config.overlap,
        )
        if len(shuffled_freq) != len(freq) or not np.allclose(shuffled_freq, freq):
            raise RuntimeError("Random baseline frequency grid mismatch")
        shuffled_density = shuffled_psd / shuffled_freq
        shuffled_bands = _band_density_rows(
            freq=shuffled_freq,
            raw_power=shuffled_psd,
            opportunity_density=shuffled_density,
            period_bands=config.period_bands,
            sample_count=len(log_returns),
            min_cycle_observations=config.min_cycle_observations,
        )
        random_shares.append(
            np.array(
                [band.opportunity_normalized_share for band in shuffled_bands],
                dtype=np.float64,
            )
        )
    random_matrix = np.vstack(random_shares)
    q05 = np.quantile(random_matrix, 0.05, axis=0)
    q50 = np.quantile(random_matrix, 0.50, axis=0)
    q95 = np.quantile(random_matrix, 0.95, axis=0)
    enriched: list[CycleOpportunityBand] = []
    for index, band in enumerate(raw_bands):
        median = float(q50[index])
        ratio = band.opportunity_normalized_share / median if median > 0.0 else None
        enriched.append(
            CycleOpportunityBand(
                period_band_bars=band.period_band_bars,
                period_lo_bars=band.period_lo_bars,
                period_hi_bars=band.period_hi_bars,
                frequency_low=band.frequency_low,
                frequency_high=band.frequency_high,
                raw_power_share=band.raw_power_share,
                opportunity_normalized_share=band.opportunity_normalized_share,
                density_share_vs_random_median=ratio,
                random_q05_share=float(q05[index]),
                random_median_share=median,
                random_q95_share=float(q95[index]),
                above_random_95=(band.opportunity_normalized_share > float(q95[index])),
                below_random_05=(band.opportunity_normalized_share < float(q05[index])),
                eligible_by_min_cycles=band.eligible_by_min_cycles,
            )
        )
    return enriched


def _bounded_power_of_two(value: int, *, lower: int, upper: int) -> int:
    if lower <= 0 or upper < lower:
        raise ValueError("invalid Fourier window bounds")
    power = 1
    while power < value:
        power *= 2
    return min(upper, max(lower, power))


def _share(
    values: NDArray[np.float64],
    *,
    mask: NDArray[np.bool_],
    total: float,
    dfreq: float,
) -> float:
    if total <= 0.0 or not bool(mask.any()):
        return 0.0
    return float(np.sum(values[mask]) * dfreq / total)


def _frequency_step(freq: NDArray[np.float64]) -> float:
    if len(freq) < 2:
        return 1.0
    return float(np.median(np.diff(freq)))


def _series_date_label(series: pd.Series, *, boundary: Literal["min", "max"]) -> str:
    raw_value = series.index.min() if boundary == "min" else series.index.max()
    return str(pd.Timestamp(str(raw_value)).date())
