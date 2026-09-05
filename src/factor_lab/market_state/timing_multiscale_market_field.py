"""Causal, tool-neutral multiscale market-field measurements.

The market field separates three quantities that were historically mixed in
timing research:

* clean-band power says where absolute market motion lives;
* raw-price scale statistics say whether motion at that horizon persists;
* cumulative high-pass volatility says how much motion exists below a chosen
  physical scale, without pretending that it belongs to one narrower band.

Filtered-component continuity is retained only as a phase/geometry diagnostic.
It must not be treated as evidence that the unfiltered market is trendable.

The module is measurement infrastructure.  It neither selects a timing tool
nor grants parameter, routing, signal, or production authority.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Final

import numpy as np
import pandas as pd
from scipy import signal

from factor_lab.core.errors import ValidationError
from factor_lab.filtering.cloudridge_3_0_hybrid_filter_bank import (
    butterworth_bandpass_component,
)

SCHEMA_ID: Final[str] = "market_state_timing_multiscale_market_field@1.0"
CALCULATION_VERSION: Final[str] = "timing_multiscale_market_field_v1"
DEFAULT_CENTER_SESSIONS: Final[tuple[float, ...]] = (
    0.5,
    1.0,
    2.0,
    4.0,
    8.0,
    16.0,
    32.0,
    64.0,
    128.0,
    256.0,
)
DEFAULT_EVALUATION_PERIODS: Final[tuple[tuple[str, pd.Timestamp, pd.Timestamp], ...]] = (
    (
        "development_2009_2017",
        pd.Timestamp("2009-01-01"),
        pd.Timestamp("2018-01-01"),
    ),
    (
        "repeat_audit_2018_2020",
        pd.Timestamp("2018-01-01"),
        pd.Timestamp("2021-01-01"),
    ),
    (
        "aggregate_blackbox_2021_2026",
        pd.Timestamp("2021-01-01"),
        pd.Timestamp("2027-01-01"),
    ),
)
EPSILON: Final[float] = 1e-18


@dataclass(frozen=True, slots=True)
class MultiscaleMarketFieldSpec:
    """Frozen physical-scale definition for one completed-bar carrier."""

    bar_frequency: str = "15m"
    bars_per_session: int = 16
    annual_sessions: float = 252.0
    center_sessions: tuple[float, ...] = DEFAULT_CENTER_SESSIONS
    butterworth_order: int = 4
    power_ewm_cycles: float = 1.0
    baseline_cycles: int = 8
    baseline_min_cycles: int = 4

    def __post_init__(self) -> None:
        centers = np.asarray(self.center_sessions, dtype=float)
        if len(centers) < 3 or not np.isfinite(centers).all():
            raise ValueError("market field requires at least three finite centers")
        if bool(np.any(centers <= 0.0)) or bool(np.any(np.diff(centers) <= 0.0)):
            raise ValueError("market-field centers must be positive and increasing")
        if bool(np.any(centers[1:] / centers[:-1] < 1.5)):
            raise ValueError("adjacent market-field centers must differ by at least 1.5x")
        if self.bars_per_session < 1 or self.annual_sessions <= 0.0:
            raise ValueError("carrier scale must be positive")
        if self.butterworth_order < 1 or self.power_ewm_cycles <= 0.0:
            raise ValueError("filter order and power smoothing must be positive")
        if not 2 <= self.baseline_min_cycles <= self.baseline_cycles:
            raise ValueError("baseline cycles must satisfy 2 <= min <= full")
        first_center_bars = centers[0] * self.bars_per_session
        first_ratio = centers[1] / centers[0]
        if round(first_center_bars / math.sqrt(first_ratio)) < 3:
            raise ValueError("fastest band violates the sampled-bar Nyquist guard")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MultiscaleMarketField:
    """Daily public tables produced by the causal field calculator."""

    band_catalog: pd.DataFrame
    band_timeseries: pd.DataFrame
    scale_trend_timeseries: pd.DataFrame
    highpass_timeseries: pd.DataFrame
    spectral_summary: pd.DataFrame


def _scale_tag(value: float) -> str:
    text = f"{value:g}".replace(".", "p")
    return f"d{text}"


def build_band_catalog(
    spec: MultiscaleMarketFieldSpec = MultiscaleMarketFieldSpec(),
) -> pd.DataFrame:
    """Return adjacent logarithmic bands with shared physical boundaries."""

    centers = np.asarray(spec.center_sessions, dtype=float)
    edges = [centers[0] / math.sqrt(centers[1] / centers[0])]
    edges.extend(math.sqrt(left * right) for left, right in zip(centers[:-1], centers[1:], strict=True))
    edges.append(centers[-1] * math.sqrt(centers[-1] / centers[-2]))
    edge_bars = [int(round(value * spec.bars_per_session)) for value in edges]
    if any(left >= right for left, right in zip(edge_bars[:-1], edge_bars[1:], strict=True)):
        raise ValidationError("rounded market-field band boundaries are not ordered")
    if edge_bars[0] < 3:
        raise ValidationError("fastest market-field boundary is above Nyquist")
    rows: list[dict[str, object]] = []
    for location, center in enumerate(centers):
        center_bars = int(round(center * spec.bars_per_session))
        short_bars = edge_bars[location]
        long_bars = edge_bars[location + 1]
        rows.append(
            {
                "band_id": f"band_{_scale_tag(float(center))}",
                "center_sessions": float(center),
                "center_bars": center_bars,
                "short_boundary_sessions": short_bars / spec.bars_per_session,
                "long_boundary_sessions": long_bars / spec.bars_per_session,
                "short_period_bars": short_bars,
                "long_period_bars": long_bars,
                "bar_frequency": spec.bar_frequency,
                "bars_per_session": spec.bars_per_session,
                "measurement_filter": "causal_butterworth_bandpass",
                "butterworth_order": spec.butterworth_order,
            }
        )
    result = pd.DataFrame(rows)
    if not bool(
        np.array_equal(
            result["long_period_bars"].iloc[:-1].to_numpy(int),
            result["short_period_bars"].iloc[1:].to_numpy(int),
        )
    ):
        raise RuntimeError("market-field adjacent bands do not share boundaries")
    return result


def past_only_zscore(
    values: pd.Series,
    *,
    window: int,
    min_periods: int,
) -> pd.Series:
    """Standardize the current observation against a window ending at t-1."""

    if window < 2 or not 2 <= min_periods <= window:
        raise ValueError("past-only z-score window is invalid")
    numeric = pd.to_numeric(values, errors="coerce").astype(float)
    history = numeric.shift(1)
    mean = history.rolling(window, min_periods=min_periods).mean()
    std = history.rolling(window, min_periods=min_periods).std(ddof=0)
    return ((numeric - mean) / std.where(std.gt(EPSILON))).astype(float)


def _validate_log_close(log_close: pd.Series) -> pd.Series:
    values = pd.to_numeric(log_close, errors="coerce").astype(float)
    if not isinstance(values.index, pd.DatetimeIndex):
        raise TypeError("market field requires a DatetimeIndex")
    if values.index.empty or values.index.has_duplicates or not values.index.is_monotonic_increasing:
        raise ValidationError("market-field timestamps must be non-empty, unique, and increasing")
    if values.isna().any() or not np.isfinite(values.to_numpy(float)).all():
        raise ValidationError("market-field log close must be finite")
    if len(values) < 32:
        raise ValidationError("market-field source is too short")
    return values


def _causal_highpass_component(
    log_close: pd.Series,
    *,
    cutoff_period_bars: int,
    order: int,
) -> pd.Series:
    if cutoff_period_bars < 3:
        raise ValueError("high-pass cutoff must be at least three bars")
    sos = signal.butter(
        order,
        1.0 / float(cutoff_period_bars),
        btype="highpass",
        fs=1.0,
        output="sos",
    )
    source = log_close.to_numpy(float)
    filtered = signal.sosfilt(sos, source - source[0])
    result = pd.Series(filtered, index=log_close.index, dtype=float)
    result.iloc[: min(len(result), 3 * cutoff_period_bars)] = np.nan
    return result


def _rolling_path_metrics(values: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    net = values.rolling(window, min_periods=window).sum()
    gross = values.abs().rolling(window, min_periods=window).sum()
    signed = net.div(gross.where(gross.gt(0.0))).clip(-1.0, 1.0)
    return signed, signed.abs()


def _rolling_bdci(values: pd.Series, window: int) -> pd.Series:
    if window < 3:
        return pd.Series(np.nan, index=values.index, dtype=float)
    signs = np.sign(values).replace(0.0, np.nan)
    valid = signs.notna() & signs.shift(1).notna()
    switches = valid & signs.ne(signs.shift(1))
    pairs = valid.astype(float).rolling(window - 1, min_periods=window - 1).sum()
    count = switches.astype(float).rolling(window - 1, min_periods=window - 1).sum()
    return (100.0 * (1.0 - count.div(pairs.where(pairs.gt(0.0))))).clip(0.0, 100.0)


def _daily_last(frame: pd.DataFrame) -> pd.DataFrame:
    day = frame.index.normalize()
    result = frame.groupby(day, sort=True).tail(1).copy()
    result.insert(0, "trading_day", pd.DatetimeIndex(result.index).normalize())
    result.insert(1, "available_at", pd.DatetimeIndex(result.index))
    return result.reset_index(drop=True)


def _decision_dates(days: pd.DatetimeIndex) -> pd.Series:
    values = pd.Series(days, index=np.arange(len(days)), dtype="datetime64[ns]")
    return values.shift(-1)


def build_multiscale_market_field(
    log_close: pd.Series,
    spec: MultiscaleMarketFieldSpec = MultiscaleMarketFieldSpec(),
) -> MultiscaleMarketField:
    """Build clean-band, cumulative-high-pass and summary time series."""

    close = _validate_log_close(log_close)
    raw_return = close.diff()
    catalog = build_band_catalog(spec)
    daily_band_frames: list[pd.DataFrame] = []
    daily_scale_frames: list[pd.DataFrame] = []
    daily_highpass_frames: list[pd.DataFrame] = []
    for row in catalog.itertuples(index=False):
        center_bars = int(row.center_bars)
        component = butterworth_bandpass_component(
            close,
            short_period_bars=int(row.short_period_bars),
            long_period_bars=int(row.long_period_bars),
            order=spec.butterworth_order,
        )
        component_delta = component.diff()
        power_span = max(2, int(round(center_bars * spec.power_ewm_cycles)))
        power = (
            component.pow(2)
            .ewm(
                span=power_span,
                adjust=False,
                min_periods=center_bars,
            )
            .mean()
        )
        log_power = np.log(power.clip(lower=EPSILON))
        component_signed_efficiency, component_path_efficiency = _rolling_path_metrics(component_delta, center_bars)
        acf1 = component_delta.rolling(center_bars, min_periods=center_bars).corr(component_delta.shift(1))
        heat = past_only_zscore(
            log_power,
            window=spec.baseline_cycles * center_bars,
            min_periods=spec.baseline_min_cycles * center_bars,
        )
        band_frame = pd.DataFrame(
            {
                "power": power,
                "rms_amplitude": power.pow(0.5),
                "absolute_power_heat": heat,
                "power_log_change_1cycle": log_power - log_power.shift(center_bars),
                "component_signed_path_efficiency": component_signed_efficiency,
                "component_phase_path_efficiency": component_path_efficiency,
                "component_delta_acf1": acf1,
                "component_delta_bdci": _rolling_bdci(component_delta, center_bars),
            },
            index=close.index,
        )
        daily_band = _daily_last(band_frame)
        daily_band.insert(2, "band_id", str(row.band_id))
        daily_band.insert(3, "center_sessions", float(row.center_sessions))
        daily_band_frames.append(daily_band)

        scale_signed_efficiency, scale_path_efficiency = _rolling_path_metrics(raw_return, center_bars)
        memory_window = spec.baseline_cycles * center_bars
        memory_min_periods = spec.baseline_min_cycles * center_bars
        scale_return = close.diff(center_bars)
        scale_return_variance = scale_return.rolling(memory_window, min_periods=memory_min_periods).var(ddof=0)
        raw_return_variance = raw_return.rolling(memory_window, min_periods=memory_min_periods).var(ddof=0)
        scale_frame = pd.DataFrame(
            {
                "scale_signed_path_efficiency": scale_signed_efficiency,
                "scale_path_efficiency": scale_path_efficiency,
                "scale_adjacent_return_autocorrelation": scale_return.rolling(memory_window, min_periods=memory_min_periods).corr(
                    scale_return.shift(center_bars)
                ),
                "scale_variance_ratio": scale_return_variance.div(center_bars * raw_return_variance.where(raw_return_variance.gt(0.0))),
            },
            index=close.index,
        )
        daily_scale = _daily_last(scale_frame)
        daily_scale.insert(2, "scale_id", f"scale_{_scale_tag(float(row.center_sessions))}")
        daily_scale.insert(3, "center_sessions", float(row.center_sessions))
        daily_scale_frames.append(daily_scale)

        highpass = _causal_highpass_component(
            close,
            cutoff_period_bars=center_bars,
            order=spec.butterworth_order,
        )
        highpass_delta = highpass.diff()
        highpass_return_power = (
            highpass_delta.pow(2)
            .ewm(
                span=center_bars,
                adjust=False,
                min_periods=center_bars,
            )
            .mean()
        )
        highpass_displacement_power = (
            highpass.pow(2)
            .ewm(
                span=center_bars,
                adjust=False,
                min_periods=center_bars,
            )
            .mean()
        )
        highpass_log_power = np.log(highpass_return_power.clip(lower=EPSILON))
        highpass_signed, highpass_efficiency = _rolling_path_metrics(highpass_delta, center_bars)
        highpass_frame = pd.DataFrame(
            {
                "cumulative_highpass_return_power": highpass_return_power,
                "cumulative_highpass_annualized_volatility": highpass_return_power.pow(0.5)
                * math.sqrt(spec.annual_sessions * spec.bars_per_session),
                "cumulative_highpass_displacement_amplitude": highpass_displacement_power.pow(0.5),
                "cumulative_highpass_power_heat": past_only_zscore(
                    highpass_log_power,
                    window=spec.baseline_cycles * center_bars,
                    min_periods=spec.baseline_min_cycles * center_bars,
                ),
                "cumulative_highpass_component_signed_path_efficiency": highpass_signed,
                "cumulative_highpass_component_path_efficiency": highpass_efficiency,
            },
            index=close.index,
        )
        daily_highpass = _daily_last(highpass_frame)
        daily_highpass.insert(2, "cutoff_id", f"highpass_lt_{_scale_tag(float(row.center_sessions))}")
        daily_highpass.insert(3, "cutoff_sessions", float(row.center_sessions))
        daily_highpass_frames.append(daily_highpass)

    bands = pd.concat(daily_band_frames, ignore_index=True)
    scales = pd.concat(daily_scale_frames, ignore_index=True)
    highpass = pd.concat(daily_highpass_frames, ignore_index=True)
    days = pd.DatetimeIndex(sorted(bands["trading_day"].unique()))
    next_dates = _decision_dates(days)
    next_by_day = dict(zip(days, next_dates, strict=True))
    bands["decision_eligible_date"] = bands["trading_day"].map(next_by_day)
    scales["decision_eligible_date"] = scales["trading_day"].map(next_by_day)
    highpass["decision_eligible_date"] = highpass["trading_day"].map(next_by_day)

    matched_scale = scales.rename(columns={"scale_id": "matched_scale_id"})
    bands = bands.merge(
        matched_scale[
            [
                "trading_day",
                "center_sessions",
                "matched_scale_id",
                "scale_signed_path_efficiency",
                "scale_path_efficiency",
                "scale_adjacent_return_autocorrelation",
                "scale_variance_ratio",
            ]
        ],
        on=["trading_day", "center_sessions"],
        how="left",
        validate="one_to_one",
    )

    power = bands.pivot(index="trading_day", columns="band_id", values="power")
    path = bands.pivot(index="trading_day", columns="band_id", values="scale_path_efficiency")
    signed_path = bands.pivot(index="trading_day", columns="band_id", values="scale_signed_path_efficiency")
    heat = bands.pivot(index="trading_day", columns="band_id", values="absolute_power_heat")
    power_change = bands.pivot(index="trading_day", columns="band_id", values="power_log_change_1cycle")
    band_order = catalog["band_id"].tolist()
    power = power.reindex(columns=band_order)
    path = path.reindex(columns=band_order)
    signed_path = signed_path.reindex(columns=band_order)
    heat = heat.reindex(columns=band_order)
    power_change = power_change.reindex(columns=band_order)
    total_power = power.sum(axis=1, min_count=len(band_order))
    shares = power.div(total_power.where(total_power.gt(0.0)), axis=0)
    share_long = (
        shares.stack(future_stack=True).rename("registered_band_power_share").rename_axis(index=["trading_day", "band_id"]).reset_index()
    )
    trendable_share_long = (
        (shares * path)
        .stack(future_stack=True)
        .rename("registered_band_trendable_power_share")
        .rename_axis(index=["trading_day", "band_id"])
        .reset_index()
    )
    bands = bands.merge(share_long, on=["trading_day", "band_id"], how="left", validate="one_to_one")
    bands = bands.merge(
        trendable_share_long,
        on=["trading_day", "band_id"],
        how="left",
        validate="one_to_one",
    )
    bands["power_change_direction"] = np.sign(bands["power_log_change_1cycle"])
    bands["measurement_authority"] = True
    bands["routing_authority"] = False
    bands["parameter_authority"] = False
    bands["production_authority"] = False
    scales["measurement_authority"] = True
    scales["routing_authority"] = False
    scales["parameter_authority"] = False
    scales["production_authority"] = False

    centers = catalog.set_index("band_id")["center_sessions"].reindex(band_order)
    log_centers = np.log(centers.to_numpy(float))
    centroid = np.exp(shares.mul(log_centers, axis=1).sum(axis=1, min_count=len(band_order)))
    valid = shares.notna().all(axis=1)
    dominant_share = pd.Series(pd.NA, index=shares.index, dtype="string")
    dominant_heat = pd.Series(pd.NA, index=shares.index, dtype="string")
    dominant_share.loc[valid] = shares.loc[valid].idxmax(axis=1).astype(str)
    heat_valid = heat.notna().all(axis=1)
    dominant_heat.loc[heat_valid] = heat.loc[heat_valid].idxmax(axis=1).astype(str)
    change_valid = power_change.notna().all(axis=1)
    strongest_heating = pd.Series(pd.NA, index=shares.index, dtype="string")
    strongest_cooling = pd.Series(pd.NA, index=shares.index, dtype="string")
    heating_valid = change_valid & power_change.max(axis=1, skipna=False).gt(0.0)
    cooling_valid = change_valid & power_change.min(axis=1, skipna=False).lt(0.0)
    strongest_heating.loc[heating_valid] = power_change.loc[heating_valid].idxmax(axis=1).astype(str)
    strongest_cooling.loc[cooling_valid] = power_change.loc[cooling_valid].idxmin(axis=1).astype(str)
    summary = pd.DataFrame(index=shares.index)
    summary["available_at"] = bands.groupby("trading_day", sort=True)["available_at"].max()
    summary["decision_eligible_date"] = summary.index.map(next_by_day)
    summary["total_registered_band_power"] = total_power
    summary["total_registered_band_rms_amplitude"] = total_power.pow(0.5)
    summary["trendable_registered_band_power"] = (power * path).sum(axis=1, min_count=len(band_order))
    summary["trendable_power_fraction"] = (shares * path).sum(axis=1, min_count=len(band_order))
    summary["weighted_signed_path_efficiency"] = (shares * signed_path).sum(axis=1, min_count=len(band_order))
    summary["spectral_centroid_period_sessions"] = centroid.where(valid)
    summary["registered_band_participation_ratio"] = 1.0 / shares.pow(2).sum(axis=1, min_count=len(band_order))
    summary["absolute_hot_band_count"] = heat.gt(0.0).sum(axis=1).where(heat_valid)
    summary["rising_band_count_1cycle"] = power_change.gt(0.0).sum(axis=1).where(change_valid)
    summary["falling_band_count_1cycle"] = power_change.lt(0.0).sum(axis=1).where(change_valid)
    summary["dominant_band_by_power_share"] = dominant_share
    summary["dominant_band_by_absolute_heat"] = dominant_heat
    summary["strongest_heating_band_1cycle"] = strongest_heating
    summary["strongest_cooling_band_1cycle"] = strongest_cooling
    for group_id, group_mask in {
        "fast": centers.le(4.0),
        "middle": centers.gt(4.0) & centers.le(32.0),
        "slow": centers.gt(32.0),
    }.items():
        columns = centers.index[group_mask].tolist()
        summary[f"{group_id}_power_share"] = shares[columns].sum(axis=1, min_count=len(columns))
        summary[f"{group_id}_mean_absolute_heat"] = heat[columns].mean(axis=1, skipna=False)
        summary[f"{group_id}_mean_power_log_change_1cycle"] = power_change[columns].mean(axis=1, skipna=False)
        summary[f"{group_id}_trendable_power_share"] = (shares[columns] * path[columns]).sum(axis=1, min_count=len(columns))
    total_log_power = np.log(total_power.clip(lower=EPSILON))
    largest_center_days = int(round(float(max(spec.center_sessions))))
    summary["total_power_heat"] = past_only_zscore(
        total_log_power,
        window=spec.baseline_cycles * largest_center_days,
        min_periods=spec.baseline_min_cycles * largest_center_days,
    )
    summary["measurement_authority"] = True
    summary["routing_authority"] = False
    summary["parameter_authority"] = False
    summary["production_authority"] = False
    summary = summary.rename_axis("trading_day").reset_index()

    highpass["measurement_authority"] = True
    highpass["routing_authority"] = False
    highpass["parameter_authority"] = False
    highpass["production_authority"] = False
    return MultiscaleMarketField(
        band_catalog=catalog,
        band_timeseries=bands.sort_values(["trading_day", "center_sessions"], kind="mergesort").reset_index(drop=True),
        scale_trend_timeseries=scales.sort_values(["trading_day", "center_sessions"], kind="mergesort").reset_index(drop=True),
        highpass_timeseries=highpass.sort_values(["trading_day", "cutoff_sessions"], kind="mergesort").reset_index(drop=True),
        spectral_summary=summary.sort_values("trading_day", kind="mergesort").reset_index(drop=True),
    )


def summarize_field_periods(
    field: MultiscaleMarketField,
    periods: tuple[tuple[str, pd.Timestamp, pd.Timestamp], ...],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Aggregate field, band and cumulative-high-pass states by fixed periods."""

    overall_rows: list[dict[str, object]] = []
    band_rows: list[dict[str, object]] = []
    scale_rows: list[dict[str, object]] = []
    highpass_rows: list[dict[str, object]] = []
    summary = field.spectral_summary.copy()
    summary["trading_day"] = pd.to_datetime(summary["trading_day"], errors="raise")
    bands = field.band_timeseries.copy()
    bands["trading_day"] = pd.to_datetime(bands["trading_day"], errors="raise")
    scales = field.scale_trend_timeseries.copy()
    scales["trading_day"] = pd.to_datetime(scales["trading_day"], errors="raise")
    highpass = field.highpass_timeseries.copy()
    highpass["trading_day"] = pd.to_datetime(highpass["trading_day"], errors="raise")
    overall_metrics = (
        "total_registered_band_power",
        "trendable_power_fraction",
        "weighted_signed_path_efficiency",
        "spectral_centroid_period_sessions",
        "registered_band_participation_ratio",
        "absolute_hot_band_count",
        "rising_band_count_1cycle",
        "falling_band_count_1cycle",
        "fast_power_share",
        "middle_power_share",
        "slow_power_share",
        "fast_trendable_power_share",
        "middle_trendable_power_share",
        "slow_trendable_power_share",
        "fast_mean_power_log_change_1cycle",
        "middle_mean_power_log_change_1cycle",
        "slow_mean_power_log_change_1cycle",
        "total_power_heat",
    )
    for period_id, start, end in periods:
        local_summary = summary.loc[summary["trading_day"].ge(start) & summary["trading_day"].lt(end)]
        row: dict[str, object] = {
            "period_id": period_id,
            "start": start,
            "end_exclusive": end,
            "trading_day_count": int(len(local_summary)),
        }
        for metric in overall_metrics:
            values = pd.to_numeric(local_summary[metric], errors="coerce")
            row[f"mean_{metric}"] = float(values.mean())
            row[f"valid_{metric}_observation_count"] = int(values.notna().sum())
        overall_rows.append(row)
        local_bands = bands.loc[bands["trading_day"].ge(start) & bands["trading_day"].lt(end)]
        for (band_id, center), group in local_bands.groupby(["band_id", "center_sessions"], sort=False):
            band_rows.append(
                {
                    "period_id": period_id,
                    "band_id": band_id,
                    "center_sessions": float(center),
                    "observation_count": int(len(group)),
                    "valid_power_observation_count": int(group["power"].notna().sum()),
                    "valid_absolute_heat_observation_count": int(group["absolute_power_heat"].notna().sum()),
                    "mean_power": float(group["power"].mean()),
                    "mean_rms_amplitude": float(group["rms_amplitude"].mean()),
                    "mean_absolute_power_heat": float(group["absolute_power_heat"].mean()),
                    "mean_power_log_change_1cycle": float(group["power_log_change_1cycle"].mean()),
                    "mean_component_phase_path_efficiency": float(group["component_phase_path_efficiency"].mean()),
                    "mean_matched_scale_path_efficiency": float(group["scale_path_efficiency"].mean()),
                    "mean_matched_scale_variance_ratio": float(group["scale_variance_ratio"].mean()),
                    "mean_component_delta_acf1": float(group["component_delta_acf1"].mean()),
                    "mean_component_delta_bdci": float(group["component_delta_bdci"].mean()),
                    "mean_registered_band_power_share": float(group["registered_band_power_share"].mean()),
                    "mean_registered_band_trendable_power_share": float(group["registered_band_trendable_power_share"].mean()),
                }
            )
        local_scales = scales.loc[scales["trading_day"].ge(start) & scales["trading_day"].lt(end)]
        for (scale_id, center), group in local_scales.groupby(["scale_id", "center_sessions"], sort=False):
            scale_rows.append(
                {
                    "period_id": period_id,
                    "scale_id": scale_id,
                    "center_sessions": float(center),
                    "observation_count": int(len(group)),
                    "valid_path_observation_count": int(group["scale_path_efficiency"].notna().sum()),
                    "valid_variance_ratio_observation_count": int(group["scale_variance_ratio"].notna().sum()),
                    "mean_scale_path_efficiency": float(group["scale_path_efficiency"].mean()),
                    "mean_scale_signed_path_efficiency": float(group["scale_signed_path_efficiency"].mean()),
                    "mean_scale_adjacent_return_autocorrelation": float(group["scale_adjacent_return_autocorrelation"].mean()),
                    "mean_scale_variance_ratio": float(group["scale_variance_ratio"].mean()),
                }
            )
        local_highpass = highpass.loc[highpass["trading_day"].ge(start) & highpass["trading_day"].lt(end)]
        for (cutoff_id, cutoff), group in local_highpass.groupby(["cutoff_id", "cutoff_sessions"], sort=False):
            highpass_rows.append(
                {
                    "period_id": period_id,
                    "cutoff_id": cutoff_id,
                    "cutoff_sessions": float(cutoff),
                    "observation_count": int(len(group)),
                    "valid_volatility_observation_count": int(group["cumulative_highpass_annualized_volatility"].notna().sum()),
                    "valid_heat_observation_count": int(group["cumulative_highpass_power_heat"].notna().sum()),
                    "mean_cumulative_highpass_annualized_volatility": float(group["cumulative_highpass_annualized_volatility"].mean()),
                    "mean_cumulative_highpass_power_heat": float(group["cumulative_highpass_power_heat"].mean()),
                    "mean_cumulative_highpass_component_path_efficiency": float(
                        group["cumulative_highpass_component_path_efficiency"].mean()
                    ),
                }
            )
    return (
        pd.DataFrame(overall_rows),
        pd.DataFrame(band_rows),
        pd.DataFrame(scale_rows),
        pd.DataFrame(highpass_rows),
    )


def summarize_field_state_persistence(
    field: MultiscaleMarketField,
    periods: tuple[tuple[str, pd.Timestamp, pd.Timestamp], ...],
    *,
    lags: tuple[int, ...] = (1, 5, 20),
) -> pd.DataFrame:
    """Measure state persistence without treating it as payoff predictability."""

    if not lags or any(lag < 1 for lag in lags):
        raise ValueError("persistence lags must be positive")
    table_specs = (
        (
            "clean_band_energy",
            field.band_timeseries,
            "band_id",
            {
                "log_band_power": lambda frame: np.log(frame["power"].clip(lower=EPSILON)),
                "absolute_power_heat": lambda frame: frame["absolute_power_heat"],
            },
        ),
        (
            "raw_market_scale_trend",
            field.scale_trend_timeseries,
            "scale_id",
            {
                "scale_path_efficiency": lambda frame: frame["scale_path_efficiency"],
                "scale_variance_ratio": lambda frame: frame["scale_variance_ratio"],
            },
        ),
        (
            "cumulative_highpass_volatility",
            field.highpass_timeseries,
            "cutoff_id",
            {
                "log_cumulative_highpass_return_power": lambda frame: np.log(frame["cumulative_highpass_return_power"].clip(lower=EPSILON)),
                "cumulative_highpass_power_heat": lambda frame: frame["cumulative_highpass_power_heat"],
            },
        ),
    )
    rows: list[dict[str, object]] = []
    for surface_id, raw_frame, state_column, metrics in table_specs:
        frame = raw_frame.copy()
        frame["trading_day"] = pd.to_datetime(frame["trading_day"], errors="raise")
        for period_id, start, end in periods:
            local = frame.loc[frame["trading_day"].ge(start) & frame["trading_day"].lt(end)]
            for state_id, group in local.groupby(state_column, sort=False):
                ordered = group.sort_values("trading_day", kind="mergesort")
                for metric_id, selector in metrics.items():
                    values = pd.to_numeric(selector(ordered), errors="coerce").dropna()
                    for lag in lags:
                        rows.append(
                            {
                                "period_id": period_id,
                                "surface_id": surface_id,
                                "state_id": str(state_id),
                                "metric_id": metric_id,
                                "lag_sessions": int(lag),
                                "observation_count": int(len(values)),
                                "autocorrelation": float(values.autocorr(lag=lag)),
                                "interpretation": ("state_tracking_persistence_not_payoff_forecast"),
                                "measurement_authority": True,
                                "routing_authority": False,
                                "parameter_authority": False,
                                "production_authority": False,
                            }
                        )
    return pd.DataFrame(rows)


def multiscale_market_field_contract(
    spec: MultiscaleMarketFieldSpec = MultiscaleMarketFieldSpec(),
) -> dict[str, object]:
    """Return the machine-readable semantics and authority boundary."""

    return {
        "schema_id": SCHEMA_ID,
        "calculation_version": CALCULATION_VERSION,
        "spec": spec.to_dict(),
        "scientific_role": "causal_tool_neutral_multiscale_market_measurement",
        "band_power_formula": "EWM_1cycle(clean_bandpass(log_price)^2)",
        "band_amplitude_formula": "sqrt(band_power)",
        "band_component_phase_formula": ("sum(delta(clean_band_component))/sum(abs(delta(clean_band_component))) over one center cycle"),
        "band_component_continuity_formula": "acf1 and BDCI of delta(clean_band_component)",
        "scale_trend_formula": (
            "raw-return path efficiency over one physical scale plus adjacent scale-return "
            "autocorrelation and variance ratio over a past-only multi-cycle window"
        ),
        "component_continuity_warning": (
            "filtered-component continuity partly reflects filter geometry and is not the "
            "market trend axis; matched-scale raw-return metrics own that role"
        ),
        "absolute_heat_formula": "past-only zscore(log(band_power)); baseline excludes current observation",
        "cumulative_highpass_formula": "causal Butterworth highpass below each physical cutoff",
        "cumulative_highpass_continuity_warning": (
            "highpass-component path metrics diagnose the filtered residual only; they are not the matched-scale market trend axis"
        ),
        "power_share_warning": (
            "registered-band shares are compositional ownership descriptors; they cannot prove absolute heating or crowding out"
        ),
        "power_amplitude_alias": "rms_amplitude^2 == power",
        "opportunity_execution_separation": ("active opportunity frequency does not automatically own the same-named trading parameter"),
        "availability": "completed bar t; daily field eligible from next observed trading day",
        "state_persistence_warning": (
            "rolling and filtered states overlap mechanically; persistence supports tracking "
            "but does not by itself prove future payoff ownership"
        ),
        "runtime_uses_future": False,
        "measurement_authority": True,
        "signal_authority": False,
        "routing_authority": False,
        "parameter_authority": False,
        "production_authority": False,
    }


__all__ = [
    "CALCULATION_VERSION",
    "DEFAULT_CENTER_SESSIONS",
    "DEFAULT_EVALUATION_PERIODS",
    "EPSILON",
    "SCHEMA_ID",
    "MultiscaleMarketField",
    "MultiscaleMarketFieldSpec",
    "build_band_catalog",
    "build_multiscale_market_field",
    "multiscale_market_field_contract",
    "past_only_zscore",
    "summarize_field_periods",
    "summarize_field_state_persistence",
]
