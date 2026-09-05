# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportMissingTypeStubs=false
"""Quality-only filter tool selection workflow.

The workflow assumes the retained frequency/period interval has already been
chosen by the opportunity-density parameter workflow.  It evaluates candidate
filter *families* on signal quality only: frequency fit, lag, continuity,
fidelity, volatility retention and interpretability.  Strategy PnL is not used
for tool selection.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Literal, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from factor_lab.filtering.opportunity_density import (
    filter_specs_from_opportunity_period_interval,
)
from factor_lab.filtering.timing_validation import (
    FilterMode,
    FilterSpec,
    PeriodName,
    TimingValidationConfig,
    evaluate_filter_quality,
    resample_close_frame,
)

SelectionStatus = Literal["selected", "candidate", "rejected"]


@dataclass(frozen=True, slots=True)
class FilterToolSelectionWeights:
    """Weights for quality-only filter tool scoring."""

    frequency_fit: float = 0.30
    low_lag: float = 0.20
    continuity: float = 0.20
    fidelity: float = 0.15
    volatility_retention: float = 0.10
    interpretability: float = 0.05

    def __post_init__(self) -> None:
        weights = [
            self.frequency_fit,
            self.low_lag,
            self.continuity,
            self.fidelity,
            self.volatility_retention,
            self.interpretability,
        ]
        if any(weight < 0.0 or not math.isfinite(weight) for weight in weights):
            raise ValueError("filter tool selection weights must be finite and >= 0")
        if sum(weights) <= 0.0:
            raise ValueError("at least one filter tool selection weight must be > 0")

    def normalized(self) -> FilterToolSelectionWeights:
        total = (
            self.frequency_fit
            + self.low_lag
            + self.continuity
            + self.fidelity
            + self.volatility_retention
            + self.interpretability
        )
        return FilterToolSelectionWeights(
            frequency_fit=self.frequency_fit / total,
            low_lag=self.low_lag / total,
            continuity=self.continuity / total,
            fidelity=self.fidelity / total,
            volatility_retention=self.volatility_retention / total,
            interpretability=self.interpretability / total,
        )

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FilterToolSelectionConfig:
    """Configuration for quality-only filter tool selection."""

    period: PeriodName = "day"
    target_period_lo_bars: float = 20.0
    target_period_hi_bars: float = 80.0
    target_filter_mode: FilterMode = "bandpass"
    timestamp_column: str = "timestamp"
    close_column: str = "close"
    min_observations: int = 30
    max_acceptable_lag_bars: int = 20
    include_ema: bool = True
    include_fourier: bool = True
    include_iir: bool = True
    include_wavelet: bool = True
    max_fourier_window: int = 512
    max_wavelet_window: int = 512
    top_n: int = 3
    min_tool_quality_score: float = 0.45
    weights: FilterToolSelectionWeights = field(
        default_factory=FilterToolSelectionWeights
    )

    def __post_init__(self) -> None:
        if self.target_period_lo_bars <= 0.0:
            raise ValueError("target_period_lo_bars must be > 0")
        if self.target_period_hi_bars < self.target_period_lo_bars:
            raise ValueError("target_period_hi_bars must be >= target_period_lo_bars")
        if self.min_observations < 3:
            raise ValueError("min_observations must be >= 3")
        if self.max_acceptable_lag_bars <= 0:
            raise ValueError("max_acceptable_lag_bars must be > 0")
        if self.top_n <= 0:
            raise ValueError("top_n must be > 0")
        if not 0.0 <= self.min_tool_quality_score <= 1.0:
            raise ValueError("min_tool_quality_score must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class FilterToolEvaluation:
    """Quality-only evaluation for one candidate filter tool."""

    filter_name: str
    family: str
    mode: str
    output_kind: str
    filter_spec: dict[str, object]
    frequency_fit_score: float | None
    target_power_share: float | None
    out_of_band_leakage: float | None
    low_lag_score: float
    continuity_score: float
    fidelity_score: float
    volatility_retention_score: float
    interpretability_score: float
    tool_quality_score: float
    selection_status: SelectionStatus
    role_guidance: str
    quality_metrics: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FilterToolSelectionResult:
    """Reusable artifact for filter tool selection."""

    period: str
    target_interval: dict[str, object]
    evaluations: list[FilterToolEvaluation]
    selected: list[FilterToolEvaluation]
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "period": self.period,
            "target_interval": self.target_interval,
            "evaluations": [item.to_dict() for item in self.evaluations],
            "selected": [item.to_dict() for item in self.selected],
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class MultiPeriodFilterToolSelectionResult:
    """Reusable artifact for period-independent filter tool selection.

    Each period is evaluated by its own `FilterToolSelectionConfig`, so day,
    60min, 5min and 1min can select different tools and different target
    intervals without sharing a global winner.
    """

    index_ref: str
    period_results: list[FilterToolSelectionResult]
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "index_ref": self.index_ref,
            "period_results": [item.to_dict() for item in self.period_results],
            "selected_by_period": {
                item.period: [selected.to_dict() for selected in item.selected]
                for item in self.period_results
            },
            "metadata": self.metadata,
        }


def filter_spec_to_dict(spec: FilterSpec) -> dict[str, object]:
    """Serialize a filter spec for JSON artifacts and CLI handoff."""

    return {
        "name": spec.name,
        "family": spec.family,
        "mode": spec.mode,
        "params": dict(spec.params),
        "output_kind": spec.output_kind,
    }


def filter_spec_from_dict(payload: Mapping[str, object]) -> FilterSpec:
    """Deserialize a filter spec from a JSON object."""

    raw_params = payload.get("params")
    if not isinstance(raw_params, Mapping):
        raise ValueError("filter spec params must be an object")
    params: dict[str, float | int] = {}
    for key, value in raw_params.items():
        if not isinstance(key, str):
            raise ValueError("filter spec param keys must be strings")
        if not isinstance(value, (int, float)):
            raise ValueError("filter spec param values must be numeric")
        params[key] = value
    return FilterSpec(
        name=str(payload.get("name") or "filter"),
        family=cast(str, payload.get("family")),
        mode=cast(str, payload.get("mode")),
        params=params,
        output_kind=cast(str, payload.get("output_kind") or "level"),
    )


def run_filter_tool_selection(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    config: FilterToolSelectionConfig | None = None,
    filter_specs: Sequence[FilterSpec] | None = None,
    index_ref: str = "index_series",
) -> FilterToolSelectionResult:
    """Select filter tools using quality metrics, not strategy returns."""

    cfg = config or FilterToolSelectionConfig()
    close = resample_close_frame(
        rows,
        config=TimingValidationConfig(
            period=cfg.period,
            min_observations=cfg.min_observations,
            timestamp_column=cfg.timestamp_column,
            close_column=cfg.close_column,
        ),
    )
    if len(close) < cfg.min_observations:
        raise ValueError("Not enough observations for filter tool selection")
    log_close = pd.Series(np.log(close.to_numpy(dtype=np.float64)), index=close.index)
    raw_returns = log_close.diff().dropna()
    specs = list(filter_specs) if filter_specs is not None else _default_specs(cfg)
    evaluations: list[FilterToolEvaluation] = []
    for spec in specs:
        quality = evaluate_filter_quality(
            spec,
            log_close=log_close,
            raw_returns=raw_returns,
        )
        if quality is None or quality.sample_count < cfg.min_observations:
            continue
        filtered = _apply_for_power(log_close, spec)
        target_share = _target_power_share(
            filtered,
            target_period_lo_bars=cfg.target_period_lo_bars,
            target_period_hi_bars=cfg.target_period_hi_bars,
            mode=cfg.target_filter_mode,
        )
        freq_score = target_share
        low_lag = _lag_score(quality.lag_bars_est, cfg.max_acceptable_lag_bars)
        continuity = _bounded01((quality.bdci_or_component_continuity or 0.0) / 100.0)
        fidelity = _bounded01(
            max(0.0, quality.best_lag_corr or quality.same_bar_corr or 0.0)
        )
        vol_score = _volatility_retention_score(quality.volatility_retention)
        interp = _interpretability_score(spec.family)
        tool_score = _tool_quality_score(
            frequency_fit=freq_score,
            low_lag=low_lag,
            continuity=continuity,
            fidelity=fidelity,
            volatility_retention=vol_score,
            interpretability=interp,
            weights=cfg.weights,
        )
        evaluations.append(
            FilterToolEvaluation(
                filter_name=spec.name,
                family=spec.family,
                mode=spec.mode,
                output_kind=spec.output_kind,
                filter_spec=filter_spec_to_dict(spec),
                frequency_fit_score=freq_score,
                target_power_share=target_share,
                out_of_band_leakage=(
                    None if target_share is None else 1.0 - target_share
                ),
                low_lag_score=low_lag,
                continuity_score=continuity,
                fidelity_score=fidelity,
                volatility_retention_score=vol_score,
                interpretability_score=interp,
                tool_quality_score=tool_score,
                selection_status="candidate",
                role_guidance=_role_guidance(spec.family),
                quality_metrics=quality.to_dict(),
            )
        )
    ranked = sorted(evaluations, key=lambda item: item.tool_quality_score, reverse=True)
    selected_names = {
        item.filter_name
        for item in ranked[: cfg.top_n]
        if item.tool_quality_score >= cfg.min_tool_quality_score
    }
    finalized = [
        _with_status(
            item,
            "selected" if item.filter_name in selected_names else "rejected",
        )
        for item in ranked
    ]
    selected = [item for item in finalized if item.selection_status == "selected"]
    return FilterToolSelectionResult(
        period=cfg.period,
        target_interval={
            "target_period_lo_bars": cfg.target_period_lo_bars,
            "target_period_hi_bars": cfg.target_period_hi_bars,
            "target_filter_mode": cfg.target_filter_mode,
        },
        evaluations=finalized,
        selected=selected,
        metadata={
            "workflow_role": "filter_tool_selection_workflow",
            "workflow_version": "quality_only_v1",
            "index_ref": index_ref,
            "sample_start": _series_date_label(close, boundary="min"),
            "sample_end": _series_date_label(close, boundary="max"),
            "sample_count": len(close),
            "score_formula": (
                "quality_only: frequency_fit, low_lag, continuity, fidelity, "
                "volatility_retention, interpretability; no return backtest is used"
            ),
            "weights": cfg.weights.normalized().to_dict(),
            "parameter_source_required": (
                "target interval should come from frequency-first DII ridge "
                "discovery (or the standalone diagnostic parameter workflow), "
                "not from PnL optimization"
            ),
            "factor_lifecycle_mutation": False,
            "strategy_lifecycle_mutation": False,
        },
    )


def run_multi_period_filter_tool_selection(
    rows: pd.DataFrame | Sequence[Mapping[str, object]],
    *,
    configs: Sequence[FilterToolSelectionConfig],
    filter_specs_by_period: Mapping[str, Sequence[FilterSpec]] | None = None,
    index_ref: str = "index_series",
) -> MultiPeriodFilterToolSelectionResult:
    """Run independent quality-only tool selection for each requested period."""

    if not configs:
        raise ValueError("configs must not be empty")
    period_results: list[FilterToolSelectionResult] = []
    for cfg in configs:
        period_results.append(
            run_filter_tool_selection(
                rows,
                config=cfg,
                filter_specs=(
                    None
                    if filter_specs_by_period is None
                    else filter_specs_by_period.get(cfg.period)
                ),
                index_ref=index_ref,
            )
        )
    return MultiPeriodFilterToolSelectionResult(
        index_ref=index_ref,
        period_results=period_results,
        metadata={
            "workflow_role": "multi_period_filter_tool_selection_workflow",
            "workflow_version": "period_independent_quality_only_v1",
            "index_ref": index_ref,
            "periods_requested": [cfg.period for cfg in configs],
            "period_independence_contract": (
                "each period owns its target interval, candidate roster, sample "
                "scope, scores, and selected filter_spec; no global filter winner "
                "is reused across periods"
            ),
            "score_policy": (
                "quality_only_per_period; no return backtest is used for tool "
                "selection"
            ),
            "factor_lifecycle_mutation": False,
            "strategy_lifecycle_mutation": False,
        },
    )


def _default_specs(config: FilterToolSelectionConfig) -> list[FilterSpec]:
    return filter_specs_from_opportunity_period_interval(
        period_lo_bars=config.target_period_lo_bars,
        period_hi_bars=config.target_period_hi_bars,
        mode=config.target_filter_mode,
        include_ema=config.include_ema,
        include_fourier=config.include_fourier,
        include_iir=config.include_iir,
        include_wavelet=config.include_wavelet,
        max_fourier_window=config.max_fourier_window,
        max_wavelet_window=config.max_wavelet_window,
    )


def _apply_for_power(log_close: pd.Series, spec: FilterSpec) -> pd.Series:
    from factor_lab.filtering.timing_validation import apply_filter_spec

    return apply_filter_spec(log_close, spec).dropna()


def _target_power_share(
    filtered: pd.Series,
    *,
    target_period_lo_bars: float,
    target_period_hi_bars: float,
    mode: FilterMode,
) -> float | None:
    values = filtered.dropna().diff().dropna().to_numpy(dtype=np.float64)
    if len(values) < 8:
        return None
    values = values - float(np.mean(values))
    spectrum = np.fft.rfft(values)
    freqs = np.fft.rfftfreq(len(values), d=1.0)
    power = np.abs(spectrum) ** 2
    positive = freqs > 0.0
    if not np.any(positive):
        return None
    freqs = freqs[positive]
    power = power[positive]
    total_power = float(np.sum(power))
    if total_power <= 0.0 or not math.isfinite(total_power):
        return None
    periods = 1.0 / freqs
    mask = _target_period_mask(
        periods,
        target_period_lo_bars=target_period_lo_bars,
        target_period_hi_bars=target_period_hi_bars,
        mode=mode,
    )
    return _bounded01(float(np.sum(power[mask]) / total_power))


def _target_period_mask(
    periods: NDArray[np.float64],
    *,
    target_period_lo_bars: float,
    target_period_hi_bars: float,
    mode: FilterMode,
) -> NDArray[np.bool_]:
    if mode == "bandpass":
        return cast(
            NDArray[np.bool_],
            (periods >= target_period_lo_bars) & (periods <= target_period_hi_bars),
        )
    if mode == "lowpass":
        return cast(NDArray[np.bool_], periods >= target_period_lo_bars)
    return cast(NDArray[np.bool_], periods <= target_period_hi_bars)


def _lag_score(lag_bars: int | None, max_acceptable_lag_bars: int) -> float:
    if lag_bars is None:
        return 0.0
    return _bounded01(1.0 - abs(lag_bars) / max_acceptable_lag_bars)


def _volatility_retention_score(retention: float | None) -> float:
    if retention is None or retention <= 0.0 or not math.isfinite(retention):
        return 0.0
    # Too little retention means over-smoothing; too much means the tool failed
    # to suppress noise.  Values around 0.35 are preferred for first-pass tools.
    target = 0.35
    distance = abs(math.log(retention / target))
    return _bounded01(math.exp(-distance))


def _interpretability_score(family: str) -> float:
    return {
        "ema_baseline": 1.0,
        "laplace_iir": 0.85,
        "fourier_rolling": 0.75,
        "wavelet_haar": 0.70,
    }.get(family, 0.50)


def _tool_quality_score(
    *,
    frequency_fit: float | None,
    low_lag: float,
    continuity: float,
    fidelity: float,
    volatility_retention: float,
    interpretability: float,
    weights: FilterToolSelectionWeights,
) -> float:
    w = weights.normalized()
    return _bounded01(
        (frequency_fit or 0.0) * w.frequency_fit
        + low_lag * w.low_lag
        + continuity * w.continuity
        + fidelity * w.fidelity
        + volatility_retention * w.volatility_retention
        + interpretability * w.interpretability
    )


def _role_guidance(family: str) -> str:
    if family == "fourier_rolling":
        return "frequency_explicit_when_target_band_is_stable"
    if family == "laplace_iir":
        return "online_low_latency_engineering_default"
    if family == "wavelet_haar":
        return "time_local_multiscale_nonstationary_check"
    if family == "ema_baseline":
        return "simple_causal_baseline_not_final_frequency_tool"
    return "custom_filter_family"


def _with_status(
    item: FilterToolEvaluation,
    status: SelectionStatus,
) -> FilterToolEvaluation:
    return FilterToolEvaluation(
        filter_name=item.filter_name,
        family=item.family,
        mode=item.mode,
        output_kind=item.output_kind,
        filter_spec=item.filter_spec,
        frequency_fit_score=item.frequency_fit_score,
        target_power_share=item.target_power_share,
        out_of_band_leakage=item.out_of_band_leakage,
        low_lag_score=item.low_lag_score,
        continuity_score=item.continuity_score,
        fidelity_score=item.fidelity_score,
        volatility_retention_score=item.volatility_retention_score,
        interpretability_score=item.interpretability_score,
        tool_quality_score=item.tool_quality_score,
        selection_status=status,
        role_guidance=item.role_guidance,
        quality_metrics=item.quality_metrics,
    )


def _bounded01(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return min(1.0, max(0.0, value))


def _series_date_label(series: pd.Series, *, boundary: Literal["min", "max"]) -> str:
    raw_value = series.index.min() if boundary == "min" else series.index.max()
    return str(pd.Timestamp(str(raw_value)).date())
