# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportCallIssue=false, reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportOperatorIssue=false
# pyright: reportUnannotatedClassAttribute=false, reportUnknownLambdaType=false
# pyright: reportReturnType=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnusedCallResult=false
"""Cross-frequency opportunity and stability measurement infrastructure.

This module deliberately stops before strategy construction.  It measures a
single raw market path on fixed physical scales, builds hindsight opportunity
ceilings, dependency-aware platforms and two Pareto surfaces.  A ceiling is a
denominator, never an expected return; the stability surface is not Sharpe.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Final, Literal

import numpy as np
import pandas as pd
from scipy.special import ndtr

from factor_lab.core.errors import ValidationError
from factor_lab.filtering.cloudridge_3_0_hybrid_filter_bank import (
    butterworth_bandpass_component,
)

SCHEMA_ID: Final[str] = "market_state_cross_frequency_opportunity@2.0"
INFRASTRUCTURE_ID: Final[str] = "cross_frequency_opportunity_stability_v2"
DEFAULT_PERIODS: Final[tuple[int, ...]] = (
    16,
    24,
    32,
    48,
    60,
    64,
    96,
    128,
    181,
    256,
    362,
    512,
    570,
    645,
    720,
    735,
    795,
    840,
    960,
    1200,
    1800,
    1920,
    2400,
    3000,
    3840,
)
COMMON_COST_GRID_BPS: Final[tuple[float, ...]] = (
    0.0,
    1.0,
    2.0,
    3.0,
    5.0,
    7.0,
    10.0,
    15.0,
    20.0,
    30.0,
    50.0,
    75.0,
    100.0,
    150.0,
    200.0,
    300.0,
)
ROUNDTRIP_STRESS_BPS: Final[float] = 7.0
BARS_PER_SESSION: Final[int] = 240
SESSIONS_PER_YEAR: Final[int] = 252
DEPENDENCY_LINK_THRESHOLD: Final[float] = 0.75
OPPORTUNITY_OFFSET_FRACTIONS: Final[tuple[float, ...]] = (0.0, 0.25, 0.5, 0.75)
CURVE_MATERIALITY_ABSOLUTE_PCT: Final[float] = 1.0
CURVE_MATERIALITY_RELATIVE_FRACTION: Final[float] = 0.01
EPSILON: Final[float] = 1e-18
PHYSICAL_15M_REFERENCE_ALIASES: Final[dict[int, str]] = {
    60: "15m_P4",
    570: "15m_P38",
    645: "15m_P43",
    735: "15m_P49",
    795: "15m_P53",
    840: "15m_P56",
}

FrequencyClass = Literal["ultra_high", "high", "medium", "low"]


@dataclass(frozen=True, slots=True)
class CrossFrequencyCoordinate:
    """One physical-scale identity with no strategy or parameter authority."""

    period_bars: int
    bars_per_session: int = BARS_PER_SESSION
    raw_parent_frequency: str = "1m"
    allow_overnight: bool = True
    opportunity_cost_stress_bps: float = ROUNDTRIP_STRESS_BPS

    def __post_init__(self) -> None:
        if self.period_bars < 8:
            raise ValidationError("period_bars must be an integer >= 8")
        if self.bars_per_session < 1:
            raise ValidationError("bars_per_session must be positive")
        if self.opportunity_cost_stress_bps < 0.0:
            raise ValidationError("opportunity cost stress must be non-negative")

    @property
    def period_id(self) -> str:
        return f"P{self.period_bars}"

    @property
    def period_sessions(self) -> float:
        return self.period_bars / self.bars_per_session

    @property
    def opportunity_horizon_bars(self) -> int:
        return (self.period_bars + 1) // 2

    @property
    def frequency_class(self) -> FrequencyClass:
        if self.period_bars <= 64:
            return "ultra_high"
        if self.period_bars <= 256:
            return "high"
        if self.period_bars <= 960:
            return "medium"
        return "low"

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "period_id": self.period_id,
            "period_sessions": self.period_sessions,
            "equivalent_15m_bars": self.period_bars / 15.0,
            "physical_15m_reference_alias": PHYSICAL_15M_REFERENCE_ALIASES.get(
                self.period_bars
            ),
            "signal_span_bars": self.period_bars,
            "opportunity_horizon_bars": self.opportunity_horizon_bars,
            "decision_cadence_bars": self.opportunity_horizon_bars,
            "minimum_holding_bars": self.opportunity_horizon_bars,
            "maximum_holding_bars": self.opportunity_horizon_bars,
            "frequency_class": self.frequency_class,
            "position_alphabet": "-1|0|1",
            "event_overlap": False,
            "lookahead_opportunity_only": True,
            "strategy_authority": False,
            "production_authority": False,
        }


@dataclass(frozen=True, slots=True)
class CrossFrequencyMarketProducts:
    """Market-side products prior to execution-feasibility binding."""

    coordinate_registry: pd.DataFrame
    attribute_cube: pd.DataFrame
    opportunity_events: pd.DataFrame
    opportunity_atlas: pd.DataFrame
    interference_burden_matrix: pd.DataFrame
    phase_propagation_graph: pd.DataFrame
    dependency_matrix: pd.DataFrame
    platform_dependency: pd.DataFrame
    annual_and_rolling_stability: pd.DataFrame
    period_summary: pd.DataFrame
    cost_sensitivity_surface: pd.DataFrame
    frequency_curve_shape: pd.DataFrame
    offset_sensitivity_surface: pd.DataFrame
    offset_peak_stability: pd.DataFrame
    rademacher_sensitivity: pd.DataFrame


def default_coordinates() -> tuple[CrossFrequencyCoordinate, ...]:
    """Return the frozen half-octave-to-octave cross-frequency grid."""

    return tuple(CrossFrequencyCoordinate(value) for value in DEFAULT_PERIODS)


def build_coordinate_registry(
    coordinates: tuple[CrossFrequencyCoordinate, ...] | None = None,
) -> pd.DataFrame:
    """Materialize signal, opportunity, holding and authority axes separately."""

    selected = coordinates or default_coordinates()
    periods = [item.period_bars for item in selected]
    if periods != sorted(set(periods)):
        raise ValidationError("cross-frequency periods must be unique and increasing")
    rows: list[dict[str, object]] = []
    edges = _geometric_band_edges(periods)
    for index, item in enumerate(selected):
        rows.append(
            {
                **item.to_dict(),
                "short_band_boundary_bars": edges[index],
                "long_band_boundary_bars": edges[index + 1],
                "measurement_filter": "causal_butterworth_bandpass_order4",
                "band_response_semantics": "nominally_partitioned_but_response_overlapping",
                "band_power_cross_grid_comparable": False,
                "band_power_pareto_authority": False,
                "execution_carrier": "MO_near_ATM_representative_feasibility_only",
                "execution_economics_authority": False,
            }
        )
    return pd.DataFrame(rows)


def _geometric_band_edges(periods: list[int]) -> list[int]:
    if len(periods) < 3 or any(value <= 0 for value in periods):
        raise ValidationError("at least three positive periods are required")
    edges = [int(round(periods[0] / math.sqrt(periods[1] / periods[0])))]
    edges.extend(
        int(round(math.sqrt(left * right)))
        for left, right in zip(periods[:-1], periods[1:], strict=True)
    )
    edges.append(int(round(periods[-1] * math.sqrt(periods[-1] / periods[-2]))))
    if edges[0] < 3 or any(left >= right for left, right in zip(edges[:-1], edges[1:], strict=True)):
        raise ValidationError("geometric frequency-band boundaries are invalid")
    return edges


def _validated_market_inputs(
    log_close: pd.Series,
    trading_day: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    close = pd.to_numeric(log_close, errors="coerce").astype(float)
    if not isinstance(close.index, pd.DatetimeIndex):
        raise TypeError("log_close must use a DatetimeIndex")
    if close.empty or close.index.has_duplicates or not close.index.is_monotonic_increasing:
        raise ValidationError("market timestamps must be non-empty, unique and increasing")
    if close.isna().any() or not np.isfinite(close.to_numpy(float)).all():
        raise ValidationError("log_close must be finite")
    if not trading_day.index.equals(close.index):
        raise ValidationError("trading_day must align exactly with log_close")
    days = pd.to_datetime(trading_day, errors="raise").dt.normalize()
    if days.isna().any() or not days.is_monotonic_increasing:
        raise ValidationError("trading_day must be finite and increasing")
    return close, days


def _rolling_path(values: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    net = values.rolling(window, min_periods=window).sum()
    gross = values.abs().rolling(window, min_periods=window).sum()
    signed = net.div(gross.where(gross.gt(EPSILON))).clip(-1.0, 1.0)
    return signed, signed.abs()


def _rolling_bdci(values: pd.Series, window: int) -> pd.Series:
    sign = np.sign(values).replace(0.0, np.nan)
    valid = sign.notna() & sign.shift(1).notna()
    switches = valid & sign.ne(sign.shift(1))
    pairs = valid.astype(float).rolling(window - 1, min_periods=window - 1).sum()
    count = switches.astype(float).rolling(window - 1, min_periods=window - 1).sum()
    return (100.0 * (1.0 - count.div(pairs.where(pairs.gt(0.0))))).clip(0.0, 100.0)


def _run_age(values: pd.Series) -> pd.Series:
    sign = np.sign(values).replace(0.0, np.nan)
    carried = sign.ffill()
    groups = carried.ne(carried.shift(1)).cumsum()
    age = carried.groupby(groups).cumcount().add(1).astype(float)
    age.loc[sign.isna()] = np.nan
    return age


def _daily_last(frame: pd.DataFrame, days: pd.Series) -> pd.DataFrame:
    local = frame.copy()
    local.insert(0, "trading_day", days.to_numpy())
    return local.groupby("trading_day", sort=True).tail(1).reset_index(names="available_at")


def build_attribute_cube(
    log_close: pd.Series,
    trading_day: pd.Series,
    coordinates: tuple[CrossFrequencyCoordinate, ...] | None = None,
) -> pd.DataFrame:
    """Build a causal date x physical-period attribute cube on one raw parent."""

    close, days = _validated_market_inputs(log_close, trading_day)
    selected = coordinates or default_coordinates()
    segment = _contiguous_segments(close.index)
    segment_ids = np.unique(segment)
    if len(segment_ids) > 1:
        pieces: list[pd.DataFrame] = []
        for segment_id in segment_ids:
            locations = np.flatnonzero(segment == segment_id)
            piece = build_attribute_cube(
                close.iloc[locations],
                days.iloc[locations],
                selected,
            )
            piece["market_segment_id"] = int(segment_id)
            pieces.append(piece)
        return pd.concat(pieces, ignore_index=True).sort_values(
            ["trading_day", "period_bars"]
        ).reset_index(drop=True)
    registry = build_coordinate_registry(selected)
    raw_return = close.diff()
    daily_parts: list[pd.DataFrame] = []
    for row in registry.itertuples(index=False):
        period = int(row.period_bars)
        component = butterworth_bandpass_component(
            close,
            short_period_bars=int(row.short_band_boundary_bars),
            long_period_bars=int(row.long_band_boundary_bars),
            order=4,
        )
        delta = component.diff()
        raw_signed, raw_efficiency = _rolling_path(raw_return, period)
        component_signed, component_efficiency = _rolling_path(delta, period)
        memory = 8 * period
        scale_return = close.diff(period)
        raw_variance = raw_return.rolling(memory, min_periods=4 * period).var(ddof=0)
        scale_variance = scale_return.rolling(memory, min_periods=4 * period).var(ddof=0)
        power = component.pow(2).ewm(span=period, adjust=False, min_periods=period).mean()
        raw_scale_sigma = raw_return.pow(2).rolling(period, min_periods=period).sum().pow(0.5)
        scale_normalized_efficiency = close.diff(period).abs().div(
            (math.sqrt(2.0 / math.pi) * raw_scale_sigma).where(raw_scale_sigma.gt(EPSILON))
        )
        daily = _daily_last(
            pd.DataFrame(
                {
                    "band_power": power,
                    "raw_scale_signed_path_efficiency": raw_signed,
                    "raw_scale_path_efficiency": raw_efficiency,
                    "scale_normalized_path_efficiency": scale_normalized_efficiency,
                    "raw_scale_variance_ratio": scale_variance.div(
                        period * raw_variance.where(raw_variance.gt(EPSILON))
                    ),
                    "component_signed_path_efficiency": component_signed,
                    "component_path_efficiency": component_efficiency,
                    "component_bdci": _rolling_bdci(delta, period),
                    "component_direction_run_age": _run_age(delta),
                    "component_one_cycle_move": component - component.shift(period),
                },
                index=close.index,
            ),
            days,
        )
        daily.insert(2, "period_id", str(row.period_id))
        daily.insert(3, "period_bars", period)
        daily.insert(4, "period_sessions", float(row.period_sessions))
        daily_parts.append(daily)
    cube = pd.concat(daily_parts, ignore_index=True)
    power = cube.pivot(index="trading_day", columns="period_id", values="band_power")
    order = [item.period_id for item in selected]
    power = power.reindex(columns=order)
    total = power.sum(axis=1, min_count=len(order))
    share = power.div(total.where(total.gt(EPSILON)), axis=0)
    share_long = (
        share.stack(future_stack=True)
        .rename("band_power_share")
        .rename_axis(index=["trading_day", "period_id"])
        .reset_index()
    )
    faster_rows: list[pd.DataFrame] = []
    for index, period_id in enumerate(order):
        faster = power.iloc[:, :index].sum(axis=1, min_count=index) if index else pd.Series(0.0, index=power.index)
        burden = faster.div((faster + power[period_id]).where((faster + power[period_id]).gt(EPSILON)))
        faster_rows.append(
            burden.rename("cumulative_faster_power_burden")
            .rename_axis("trading_day")
            .reset_index()
            .assign(period_id=period_id)
        )
    cube = cube.merge(share_long, on=["trading_day", "period_id"], how="left", validate="one_to_one")
    cube = cube.merge(
        pd.concat(faster_rows, ignore_index=True),
        on=["trading_day", "period_id"],
        how="left",
        validate="one_to_one",
    )
    cube["trendable_power_share"] = cube["band_power_share"] * cube["raw_scale_path_efficiency"]
    cube["noise_adjusted_trendable_power_share"] = cube["band_power_share"] * (
        cube["scale_normalized_path_efficiency"] - 1.0
    ).clip(lower=0.0)
    cube["measurement_authority"] = True
    cube["market_segment_id"] = 0
    cube["band_power_cross_grid_comparable"] = False
    cube["band_power_pareto_authority"] = False
    cube["strategy_authority"] = False
    cube["production_authority"] = False
    return cube.sort_values(["trading_day", "period_bars"]).reset_index(drop=True)


def _contiguous_segments(index: pd.DatetimeIndex) -> np.ndarray:
    gaps = pd.Series(index).diff().gt(pd.Timedelta(days=30)).fillna(False)
    return gaps.cumsum().to_numpy(int)


def _folded_normal_call_expectation(sigma: np.ndarray, cost: float) -> np.ndarray:
    """Return E[(abs(N(0,sigma^2))-cost)+] without Monte Carlo noise."""

    result = np.zeros(len(sigma), dtype=float)
    valid = sigma > EPSILON
    ratio = np.zeros(len(sigma), dtype=float)
    np.divide(cost, sigma, out=ratio, where=valid)
    density = np.exp(-0.5 * np.square(ratio)) / math.sqrt(2.0 * math.pi)
    result[valid] = 2.0 * (
        sigma[valid] * density[valid] - cost * ndtr(-ratio[valid])
    )
    return np.maximum(result, 0.0)


@lru_cache(maxsize=8)
def _rademacher_patterns(horizon: int) -> np.ndarray:
    if not 1 <= horizon <= 16:
        raise ValueError("exact Rademacher patterns support horizons 1 through 16")
    values = np.arange(1 << horizon, dtype=np.uint32)[:, None]
    bits = (values >> np.arange(horizon, dtype=np.uint32)) & 1
    return (1.0 - 2.0 * bits.astype(float)).T


def _exact_rademacher_call_expectation(
    magnitudes: np.ndarray,
    cost: float,
    *,
    batch_size: int = 256,
) -> np.ndarray:
    """Return exact E[(abs(sum(epsilon_i*a_i))-cost)+] for small horizons."""

    if magnitudes.ndim != 2 or magnitudes.shape[1] > 16:
        raise ValueError("exact Rademacher input must be two-dimensional with <=16 increments")
    patterns = _rademacher_patterns(int(magnitudes.shape[1]))
    result = np.empty(len(magnitudes), dtype=float)
    for start in range(0, len(magnitudes), batch_size):
        stop = min(len(magnitudes), start + batch_size)
        draws = np.abs(magnitudes[start:stop] @ patterns)
        result[start:stop] = np.maximum(draws - cost, 0.0).mean(axis=1)
    return result


def _chronological_roles(days: pd.Series) -> pd.Series:
    years = pd.to_datetime(days).dt.year
    return pd.Series(
        np.select(
            [years.eq(2014), years.between(2015, 2020), years.between(2022, 2024)],
            ["warmup", "development", "repeat_audit"],
            default="excluded",
        ),
        index=days.index,
        dtype="string",
    )


def build_opportunity_events(
    log_close: pd.Series,
    trading_day: pd.Series,
    coordinates: tuple[CrossFrequencyCoordinate, ...] | None = None,
    *,
    evaluation_start: str = "2015-01-01",
    offset_fraction: float = 0.0,
    exact_rademacher_max_horizon: int = 12,
) -> pd.DataFrame:
    """Build non-overlapping fixed-horizon long/short-or-flat hindsight events."""

    close, days = _validated_market_inputs(log_close, trading_day)
    if not 0.0 <= offset_fraction < 1.0:
        raise ValidationError("offset_fraction must satisfy 0 <= offset < 1")
    selected = coordinates or default_coordinates()
    roles = _chronological_roles(days)
    gap = pd.Series(close.index, index=close.index).diff().gt(pd.Timedelta(days=30))
    role_change = roles.ne(roles.shift(1))
    segment = (gap | role_change).fillna(True).cumsum().to_numpy(int)
    one_minute_return = close.diff().fillna(0.0).to_numpy(float)
    cumulative_abs = np.concatenate(([0.0], np.cumsum(np.abs(one_minute_return))))
    cumulative_square = np.concatenate(([0.0], np.cumsum(np.square(one_minute_return))))
    rows: list[pd.DataFrame] = []
    for coordinate in selected:
        horizon = coordinate.opportunity_horizon_bars
        for segment_id in np.unique(segment):
            locations = np.flatnonzero(segment == segment_id)
            segment_role = str(roles.iloc[locations[0]])
            if segment_role not in {"development", "repeat_audit"}:
                continue
            if len(locations) <= horizon:
                continue
            offset_bars = min(horizon - 1, int(round(offset_fraction * horizon)))
            starts = locations[
                np.arange(offset_bars, len(locations) - horizon, horizon, dtype=int)
            ]
            if not len(starts):
                continue
            ends = starts + horizon
            block_return = close.iloc[ends].to_numpy(float) - close.iloc[starts].to_numpy(float)
            gross = np.abs(block_return)
            stress = np.maximum(gross - coordinate.opportunity_cost_stress_bps / 10_000.0, 0.0)
            event_path = np.empty(len(starts), dtype=float)
            path = cumulative_abs[ends + 1] - cumulative_abs[starts + 1]
            sigma = np.sqrt(cumulative_square[ends + 1] - cumulative_square[starts + 1])
            magnitudes = np.stack(
                [
                    np.abs(one_minute_return[start + 1 : end + 1])
                    for start, end in zip(starts, ends, strict=True)
                ]
            )
            maximum_increment_share = magnitudes.max(axis=1) / np.maximum(sigma, EPSILON)
            null_gross = sigma * math.sqrt(2.0 / math.pi)
            stress_rate = coordinate.opportunity_cost_stress_bps / 10_000.0
            null_stress = _folded_normal_call_expectation(sigma, stress_rate)
            excess_gross = gross - null_gross
            excess_stress = stress - null_stress
            exact_available = horizon <= exact_rademacher_max_horizon
            exact_gross = np.full(len(starts), np.nan, dtype=float)
            exact_stress = np.full(len(starts), np.nan, dtype=float)
            if exact_available:
                exact_gross = _exact_rademacher_call_expectation(magnitudes, 0.0)
                exact_stress = _exact_rademacher_call_expectation(
                    magnitudes,
                    stress_rate,
                )
            np.divide(gross, path, out=event_path, where=path > EPSILON)
            event_path[path <= EPSILON] = np.nan
            rows.append(
                pd.DataFrame(
                    {
                        "period_id": coordinate.period_id,
                        "period_bars": coordinate.period_bars,
                        "frequency_class": coordinate.frequency_class,
                        "segment_id": segment_id,
                        "offset_fraction": offset_fraction,
                        "offset_bars": offset_bars,
                        "event_start": close.index[starts],
                        "event_end": close.index[ends],
                        "event_start_trading_day": days.iloc[starts].to_numpy(),
                        "event_end_trading_day": days.iloc[ends].to_numpy(),
                        "horizon_bars": horizon,
                        "signed_block_log_return": block_return,
                        "gross_opportunity_log_value": gross,
                        "net_opportunity_log_value_7bp": stress,
                        "conditional_random_sign_sigma_log": sigma,
                        "null_model_id": "conditional_gaussian_folded_normal_approximation",
                        "maximum_increment_sigma_share": maximum_increment_share,
                        "null_gross_opportunity_log_value": null_gross,
                        "null_net_opportunity_log_value_7bp": null_stress,
                        "exact_rademacher_available": exact_available,
                        "exact_rademacher_null_gross_log_value": exact_gross,
                        "exact_rademacher_null_net_7bp_log_value": exact_stress,
                        "gaussian_minus_exact_null_gross_log_value": null_gross
                        - exact_gross,
                        "gaussian_minus_exact_null_net_7bp_log_value": null_stress
                        - exact_stress,
                        "excess_gross_opportunity_log_value": excess_gross,
                        "excess_net_opportunity_log_value_7bp": excess_stress,
                        "gross_opportunity_bps": gross * 10_000.0,
                        "net_opportunity_bps_7bp": stress * 10_000.0,
                        "null_gross_opportunity_bps": null_gross * 10_000.0,
                        "null_net_opportunity_bps_7bp": null_stress * 10_000.0,
                        "excess_gross_opportunity_bps": excess_gross * 10_000.0,
                        "excess_net_opportunity_bps_7bp": excess_stress * 10_000.0,
                        "event_path_efficiency": event_path,
                        "lookahead_only": True,
                        "strategy_authority": False,
                        "chronological_role": segment_role,
                    }
                )
            )
    if not rows:
        raise ValidationError("no opportunity events could be built")
    events = pd.concat(rows, ignore_index=True)
    events = events.loc[
        events["event_start_trading_day"].ge(pd.Timestamp(evaluation_start))
        & events["event_end_trading_day"].ge(pd.Timestamp(evaluation_start))
    ].copy()
    events["natural_year"] = pd.to_datetime(events["event_end_trading_day"]).dt.year
    return events.sort_values(["period_bars", "event_end"]).reset_index(drop=True)


def build_opportunity_atlas(events: pd.DataFrame) -> pd.DataFrame:
    """Summarize the non-tradable opportunity ceiling by scope and scale."""

    required = {
        "period_id",
        "period_bars",
        "natural_year",
        "chronological_role",
        "gross_opportunity_log_value",
        "net_opportunity_log_value_7bp",
        "excess_gross_opportunity_log_value",
        "excess_net_opportunity_log_value_7bp",
        "gross_opportunity_bps",
        "net_opportunity_bps_7bp",
        "excess_gross_opportunity_bps",
        "excess_net_opportunity_bps_7bp",
        "event_path_efficiency",
    }
    if missing := sorted(required.difference(events.columns)):
        raise ValidationError(f"opportunity events missing columns: {missing}")
    rows: list[dict[str, object]] = []
    scopes: list[tuple[str, pd.DataFrame]] = [
        ("development_2015_2020", events.loc[events["chronological_role"].eq("development")]),
        ("repeat_audit_2022_2024", events.loc[events["chronological_role"].eq("repeat_audit")]),
        ("pooled_consumed_history", events),
    ]
    scopes.extend(
        (f"year_{year}", events.loc[events["natural_year"].eq(year)])
        for year in sorted(events["natural_year"].unique())
    )
    for scope_id, scoped in scopes:
        if scoped.empty:
            continue
        years = max(1, int(scoped["natural_year"].nunique()))
        for (period_id, period_bars), group in scoped.groupby(["period_id", "period_bars"], sort=True):
            net = group["net_opportunity_log_value_7bp"].to_numpy(float)
            gross = group["gross_opportunity_log_value"].to_numpy(float)
            excess_net = group["excess_net_opportunity_log_value_7bp"].to_numpy(float)
            excess_gross = group["excess_gross_opportunity_log_value"].to_numpy(float)
            positive = net[net > 0.0]
            top_count = max(1, int(math.ceil(0.05 * len(net))))
            top_share = float(np.sort(net)[-top_count:].sum() / net.sum()) if net.sum() > EPSILON else 1.0
            absolute_excess = np.abs(excess_net)
            excess_concentration = (
                float(np.sort(absolute_excess)[-top_count:].sum() / absolute_excess.sum())
                if absolute_excess.sum() > EPSILON
                else 1.0
            )
            rows.append(
                {
                    "scope_id": scope_id,
                    "period_id": period_id,
                    "period_bars": int(period_bars),
                    "event_count": len(group),
                    "natural_year_count": years,
                    "annualized_gross_opportunity_pct": float(gross.sum() * 100.0 / years),
                    "annualized_net_opportunity_pct_7bp": float(net.sum() * 100.0 / years),
                    "annualized_excess_gross_opportunity_pct": float(excess_gross.sum() * 100.0 / years),
                    "annualized_excess_net_opportunity_pct_7bp": float(excess_net.sum() * 100.0 / years),
                    "median_gross_event_bps": float(np.median(group["gross_opportunity_bps"])),
                    "median_net_event_bps_7bp": float(np.median(group["net_opportunity_bps_7bp"])),
                    "median_excess_gross_event_bps": float(np.median(group["excess_gross_opportunity_bps"])),
                    "median_excess_net_event_bps_7bp": float(
                        np.median(group["excess_net_opportunity_bps_7bp"])
                    ),
                    "mean_event_path_efficiency": float(group["event_path_efficiency"].mean()),
                    "cost_surviving_event_fraction_7bp": float(np.mean(net > 0.0)),
                    "top_5pct_net_event_concentration": top_share,
                    "top_5pct_absolute_excess_concentration": excess_concentration,
                    "positive_excess_net_event_fraction_7bp": float(np.mean(excess_net > 0.0)),
                    "positive_net_event_mean_bps": float(positive.mean() * 10_000.0) if len(positive) else 0.0,
                    "lookahead_only": True,
                    "expected_return_authority": False,
                    "sharpe_authority": False,
                }
            )
    return pd.DataFrame(rows).sort_values(["scope_id", "period_bars"]).reset_index(drop=True)


def build_rademacher_sensitivity(events: pd.DataFrame) -> pd.DataFrame:
    """Compare the Gaussian null with exact small-horizon random-sign values."""

    exact = events.loc[events["exact_rademacher_available"].astype(bool)].copy()
    rows: list[dict[str, object]] = []
    for (period_id, period_bars, horizon), group in exact.groupby(
        ["period_id", "period_bars", "horizon_bars"], sort=True
    ):
        gaussian0 = group["null_gross_opportunity_log_value"].sum()
        exact0 = group["exact_rademacher_null_gross_log_value"].sum()
        gaussian7 = group["null_net_opportunity_log_value_7bp"].sum()
        exact7 = group["exact_rademacher_null_net_7bp_log_value"].sum()
        actual7 = group["net_opportunity_log_value_7bp"].sum()
        gaussian_excess7 = actual7 - gaussian7
        exact_excess7 = actual7 - exact7
        rows.append(
            {
                "period_id": period_id,
                "period_bars": int(period_bars),
                "horizon_bars": int(horizon),
                "event_count": len(group),
                "exact_sign_pattern_count": 1 << int(horizon),
                "gaussian_null_gross_sum": float(gaussian0),
                "exact_rademacher_null_gross_sum": float(exact0),
                "gaussian_null_gross_relative_error": float(
                    (gaussian0 - exact0) / max(abs(exact0), EPSILON)
                ),
                "gaussian_null_7bp_sum": float(gaussian7),
                "exact_rademacher_null_7bp_sum": float(exact7),
                "gaussian_null_7bp_relative_error": float(
                    (gaussian7 - exact7) / max(abs(exact7), EPSILON)
                ),
                "gaussian_excess_7bp_sum": float(gaussian_excess7),
                "exact_rademacher_excess_7bp_sum": float(exact_excess7),
                "gaussian_excess_7bp_relative_error": float(
                    (gaussian_excess7 - exact_excess7)
                    / max(abs(exact_excess7), EPSILON)
                ),
                "null_model_exactness_authority": False,
                "strategy_authority": False,
            }
        )
    return pd.DataFrame(rows)


def build_opportunity_cost_sensitivity(
    events: pd.DataFrame,
    *,
    cost_grid_bps: tuple[float, ...] = COMMON_COST_GRID_BPS,
) -> pd.DataFrame:
    """Measure noise-adjusted opportunity over a frozen common-index cost grid."""

    if tuple(sorted(set(cost_grid_bps))) != cost_grid_bps or min(cost_grid_bps) < 0.0:
        raise ValidationError("cost grid must be unique, increasing and non-negative")
    required = {
        "period_id",
        "period_bars",
        "natural_year",
        "chronological_role",
        "gross_opportunity_log_value",
        "conditional_random_sign_sigma_log",
    }
    if missing := sorted(required.difference(events.columns)):
        raise ValidationError(f"cost sensitivity events missing columns: {missing}")
    rows: list[dict[str, object]] = []
    scopes = (
        ("development_2015_2020", "development"),
        ("repeat_audit_2022_2024", "repeat_audit"),
        ("pooled_consumed_history", None),
    )
    for cost_bps in cost_grid_bps:
        cost = cost_bps / 10_000.0
        gross = events["gross_opportunity_log_value"].to_numpy(float)
        sigma = events["conditional_random_sign_sigma_log"].to_numpy(float)
        actual_net = np.maximum(gross - cost, 0.0)
        null_net = _folded_normal_call_expectation(sigma, cost)
        local = events[
            ["period_id", "period_bars", "natural_year", "chronological_role"]
        ].copy()
        local["actual_net"] = actual_net
        local["null_net"] = null_net
        local["excess_net"] = actual_net - null_net
        for scope_id, role in scopes:
            scoped = local if role is None else local.loc[local["chronological_role"].eq(role)]
            years = int(scoped["natural_year"].nunique())
            for (period_id, period_bars), group in scoped.groupby(
                ["period_id", "period_bars"], sort=True
            ):
                annual_excess = (
                    group.groupby("natural_year")["excess_net"].sum() * 100.0
                )
                absolute_excess = group["excess_net"].abs().to_numpy(float)
                top_count = max(1, int(math.ceil(0.05 * len(absolute_excess))))
                absolute_total = float(absolute_excess.sum())
                concentration = (
                    float(np.sort(absolute_excess)[-top_count:].sum() / absolute_total)
                    if absolute_total > EPSILON
                    else 1.0
                )
                annual_mean = float(annual_excess.mean())
                annual_std = float(annual_excess.std(ddof=1))
                rows.append(
                    {
                        "scope_id": scope_id,
                        "roundtrip_cost_bps": cost_bps,
                        "period_id": period_id,
                        "period_bars": int(period_bars),
                        "event_count": len(group),
                        "natural_year_count": years,
                        "annualized_actual_net_opportunity_pct": float(
                            group["actual_net"].sum() * 100.0 / years
                        ),
                        "annualized_null_net_opportunity_pct": float(
                            group["null_net"].sum() * 100.0 / years
                        ),
                        "annualized_excess_net_opportunity_pct": float(
                            group["excess_net"].sum() * 100.0 / years
                        ),
                        "natural_year_excess_floor_pct": float(annual_excess.min()),
                        "natural_year_excess_mean_pct": annual_mean,
                        "natural_year_excess_std_pct": annual_std,
                        "natural_year_excess_coefficient_of_variation": annual_std
                        / max(abs(annual_mean), EPSILON),
                        "natural_year_excess_positive_fraction": float(
                            annual_excess.gt(0.0).mean()
                        ),
                        "top_5pct_absolute_excess_concentration": concentration,
                        "median_excess_net_event_bps": float(
                            group["excess_net"].median() * 10_000.0
                        ),
                        "cost_surviving_event_fraction": float(
                            group["actual_net"].gt(0.0).mean()
                        ),
                        "lookahead_only": True,
                        "expected_return_authority": False,
                    }
                )
    return pd.DataFrame(rows).sort_values(
        ["scope_id", "roundtrip_cost_bps", "period_bars"]
    ).reset_index(drop=True)


def build_opportunity_offset_sensitivity(
    log_close: pd.Series,
    trading_day: pd.Series,
    coordinates: tuple[CrossFrequencyCoordinate, ...] | None = None,
    *,
    offset_fractions: tuple[float, ...] = OPPORTUNITY_OFFSET_FRACTIONS,
    cost_grid_bps: tuple[float, ...] = COMMON_COST_GRID_BPS,
) -> pd.DataFrame:
    """Build correlated offset boundary views; none is an independent vote."""

    selected = coordinates or default_coordinates()
    pieces: list[pd.DataFrame] = []
    for offset_fraction in offset_fractions:
        events = build_opportunity_events(
            log_close,
            trading_day,
            selected,
            offset_fraction=offset_fraction,
            exact_rademacher_max_horizon=0,
        )
        surface = build_opportunity_cost_sensitivity(
            events,
            cost_grid_bps=cost_grid_bps,
        )
        surface.insert(1, "offset_fraction", offset_fraction)
        surface["independent_evidence_vote"] = False
        pieces.append(surface)
    return pd.concat(pieces, ignore_index=True).sort_values(
        ["scope_id", "roundtrip_cost_bps", "period_bars", "offset_fraction"]
    ).reset_index(drop=True)


def build_offset_peak_stability(offset_surface: pd.DataFrame) -> pd.DataFrame:
    """Report point-peak fragility across frozen event-grid offsets."""

    pooled = offset_surface.loc[
        offset_surface["scope_id"].eq("pooled_consumed_history")
    ]
    rows: list[dict[str, object]] = []
    for cost_bps, cost_group in pooled.groupby("roundtrip_cost_bps", sort=True):
        peaks: list[tuple[float, str, int, float]] = []
        for offset_fraction, group in cost_group.groupby("offset_fraction", sort=True):
            winner = group.loc[group["annualized_excess_net_opportunity_pct"].idxmax()]
            peaks.append(
                (
                    float(offset_fraction),
                    str(winner["period_id"]),
                    int(winner["period_bars"]),
                    float(winner["annualized_excess_net_opportunity_pct"]),
                )
            )
        period_ids = [item[1] for item in peaks]
        period_bars = [item[2] for item in peaks]
        rows.append(
            {
                "roundtrip_cost_bps": float(cost_bps),
                "offset_count": len(peaks),
                "offset_peak_period_ids": "|".join(period_ids),
                "unique_peak_period_ids": "|".join(dict.fromkeys(period_ids)),
                "unique_peak_count": len(set(period_ids)),
                "minimum_peak_period_bars": min(period_bars),
                "maximum_peak_period_bars": max(period_bars),
                "point_peak_offset_stable": len(set(period_ids)) == 1,
                "minimum_peak_value_pct": min(item[3] for item in peaks),
                "maximum_peak_value_pct": max(item[3] for item in peaks),
                "independent_evidence_vote": False,
                "strategy_selection_authority": False,
            }
        )
    return pd.DataFrame(rows)


def build_frequency_curve_shape(cost_sensitivity: pd.DataFrame) -> pd.DataFrame:
    """Report monotonicity and peak location for every frozen cost stress."""

    rows: list[dict[str, object]] = []
    pooled = cost_sensitivity.loc[
        cost_sensitivity["scope_id"].eq("pooled_consumed_history")
    ]
    development = cost_sensitivity.loc[
        cost_sensitivity["scope_id"].eq("development_2015_2020")
    ]
    repeat = cost_sensitivity.loc[
        cost_sensitivity["scope_id"].eq("repeat_audit_2022_2024")
    ]
    for cost_bps, group in pooled.groupby("roundtrip_cost_bps", sort=True):
        ordered = group.sort_values("period_bars")
        values = ordered["annualized_excess_net_opportunity_pct"].to_numpy(float)
        difference = np.diff(values)
        tolerance = max(
            CURVE_MATERIALITY_ABSOLUTE_PCT,
            CURVE_MATERIALITY_RELATIVE_FRACTION * float(np.max(np.abs(values))),
        )
        increase_count = int(np.sum(difference > tolerance))
        decrease_count = int(np.sum(difference < -tolerance))
        if increase_count and not decrease_count:
            direction = "monotonic_increasing"
        elif decrease_count and not increase_count:
            direction = "monotonic_decreasing"
        elif not increase_count and not decrease_count:
            direction = "flat"
        else:
            direction = "nonmonotonic"
        sign = np.sign(difference[np.abs(difference) > tolerance])
        sign_changes = int(np.sum(sign[1:] != sign[:-1])) if len(sign) > 1 else 0
        peak_index = int(np.argmax(values))
        dev_group = development.loc[
            development["roundtrip_cost_bps"].eq(cost_bps)
        ].sort_values("period_bars")
        repeat_group = repeat.loc[
            repeat["roundtrip_cost_bps"].eq(cost_bps)
        ].sort_values("period_bars")
        dev_peak = dev_group.loc[
            dev_group["annualized_excess_net_opportunity_pct"].idxmax()
        ]
        repeat_peak = repeat_group.loc[
            repeat_group["annualized_excess_net_opportunity_pct"].idxmax()
        ]
        best_floor = ordered.loc[ordered["natural_year_excess_floor_pct"].idxmax()]
        best_consistency = ordered.loc[
            ordered["natural_year_excess_coefficient_of_variation"].idxmin()
        ]
        rows.append(
            {
                "roundtrip_cost_bps": float(cost_bps),
                "metric_id": "annualized_excess_net_opportunity_pct",
                "period_count": len(ordered),
                "economic_materiality_tolerance_pct": tolerance,
                "adjacent_increase_count": increase_count,
                "adjacent_decrease_count": decrease_count,
                "slope_sign_change_count": sign_changes,
                "monotonic_direction": direction,
                "peak_period_id": str(ordered.iloc[peak_index]["period_id"]),
                "peak_period_bars": int(ordered.iloc[peak_index]["period_bars"]),
                "peak_value_pct": float(values[peak_index]),
                "peak_is_interior": 0 < peak_index < len(ordered) - 1,
                "development_peak_period_id": str(dev_peak["period_id"]),
                "repeat_peak_period_id": str(repeat_peak["period_id"]),
                "development_repeat_peak_same": str(dev_peak["period_id"])
                == str(repeat_peak["period_id"]),
                "maximum_natural_year_floor_period_id": str(best_floor["period_id"]),
                "minimum_natural_year_cv_period_id": str(best_consistency["period_id"]),
                "minimum_natural_year_cv": float(
                    best_consistency["natural_year_excess_coefficient_of_variation"]
                ),
                "positive_period_count": int(np.sum(values > 0.0)),
                "strategy_selection_authority": False,
            }
        )
    return pd.DataFrame(rows)


def build_interference_burden_matrix(attribute_cube: pd.DataFrame) -> pd.DataFrame:
    """Measure all adjacent and nonadjacent cross-band interference pairs."""

    power = attribute_cube.pivot(index="trading_day", columns="period_id", values="band_power")
    move = attribute_cube.pivot(index="trading_day", columns="period_id", values="component_one_cycle_move")
    burden = attribute_cube.pivot(
        index="trading_day", columns="period_id", values="cumulative_faster_power_burden"
    )
    periods = (
        attribute_cube[["period_id", "period_bars"]]
        .drop_duplicates()
        .sort_values("period_bars")
        .reset_index(drop=True)
    )
    rows: list[dict[str, object]] = []
    for target_index, target in periods.iterrows():
        target_id = str(target["period_id"])
        for source_index, source in periods.iterrows():
            source_id = str(source["period_id"])
            joined = pd.concat(
                [
                    power[target_id].rename("target_power"),
                    power[source_id].rename("source_power"),
                    move[target_id].rename("target_move"),
                    move[source_id].rename("source_move"),
                ],
                axis=1,
            ).dropna()
            target_sign = np.sign(joined["target_move"])
            source_sign = np.sign(joined["source_move"])
            rows.append(
                {
                    "target_period_id": target_id,
                    "target_period_bars": int(target["period_bars"]),
                    "interferer_period_id": source_id,
                    "interferer_period_bars": int(source["period_bars"]),
                    "relationship": (
                        "current"
                        if target_index == source_index
                        else "faster"
                        if source_index < target_index
                        else "slower"
                    ),
                    "adjacent": abs(source_index - target_index) == 1,
                    "pair_observation_count": len(joined),
                    "relative_power_ratio": float(joined["source_power"].mean() / joined["target_power"].mean())
                    if len(joined) and joined["target_power"].mean() > EPSILON
                    else np.nan,
                    "signed_move_spearman": float(joined["source_move"].corr(joined["target_move"], method="spearman"))
                    if len(joined) > 2
                    else np.nan,
                    "direction_alignment": float((source_sign == target_sign).mean()) if len(joined) else np.nan,
                    "direction_reversal_rate": float((source_sign != target_sign).mean()) if len(joined) else np.nan,
                    "target_cumulative_faster_power_burden": float(burden[target_id].mean()),
                    "strategy_authority": False,
                }
            )
    return pd.DataFrame(rows)


def build_phase_propagation_graph(
    attribute_cube: pd.DataFrame,
    *,
    candidate_leads: tuple[int, ...] = (0, 1, 2, 3, 4, 5),
) -> pd.DataFrame:
    """Build historical lead/acceptance diagnostics from causal band nodes."""

    local_cube = attribute_cube.copy()
    if "market_segment_id" not in local_cube:
        local_cube["market_segment_id"] = 0
    move_by_segment = {
        int(segment_id): group.pivot(
            index="trading_day",
            columns="period_id",
            values="component_one_cycle_move",
        )
        for segment_id, group in local_cube.groupby("market_segment_id", sort=True)
    }
    age = attribute_cube.pivot(index="trading_day", columns="period_id", values="component_direction_run_age")
    periods = (
        attribute_cube[["period_id", "period_bars"]]
        .drop_duplicates()
        .sort_values("period_bars")
        .reset_index(drop=True)
    )
    rows: list[dict[str, object]] = []
    for _, source in periods.iterrows():
        for _, target in periods.iterrows():
            source_id = str(source["period_id"])
            target_id = str(target["period_id"])
            candidates: list[tuple[float, int, float, float, int]] = []
            for lead in candidate_leads:
                segment_pairs: list[pd.DataFrame] = []
                for move in move_by_segment.values():
                    segment_pairs.append(
                        pd.concat(
                            [
                                move[source_id].rename("source"),
                                move[target_id].shift(-lead).rename(
                                    "future_target"
                                ),
                            ],
                            axis=1,
                        ).dropna()
                    )
                joined = pd.concat(segment_pairs, ignore_index=True)
                correlation = float(joined["source"].corr(joined["future_target"], method="spearman")) if len(joined) > 2 else np.nan
                alignment = float((np.sign(joined["source"]) == np.sign(joined["future_target"])).mean()) if len(joined) else np.nan
                objective = abs(correlation) if math.isfinite(correlation) else -np.inf
                candidates.append((objective, -lead, correlation, alignment, len(joined)))
            best = max(candidates)
            best_lead = -best[1]
            rows.append(
                {
                    "source_period_id": source_id,
                    "source_period_bars": int(source["period_bars"]),
                    "target_period_id": target_id,
                    "target_period_bars": int(target["period_bars"]),
                    "best_lead_sessions": best_lead,
                    "signed_spearman": best[2],
                    "direction_alignment": best[3],
                    "pair_observation_count": best[4],
                    "market_segment_count": len(move_by_segment),
                    "cross_segment_pair_count": 0,
                    "mean_source_run_age": float(age[source_id].mean()),
                    "source_available_before_target": best_lead > 0,
                    "historical_relationship_only": True,
                    "routing_authority": False,
                }
            )
    return pd.DataFrame(rows)


class _DisjointSet:
    def __init__(self, values: list[str]) -> None:
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def _effective_count(correlation: np.ndarray) -> float:
    matrix = np.nan_to_num(correlation, nan=0.0)
    np.fill_diagonal(matrix, 1.0)
    eigenvalues = np.clip(np.linalg.eigvalsh(matrix), 0.0, None)
    denominator = float(np.square(eigenvalues).sum())
    return float(eigenvalues.sum() ** 2 / denominator) if denominator > EPSILON else 1.0


def build_dependency_products(
    events: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str], dict[str, float]]:
    """Build cross-scale dependence, effective samples and adjacent platforms."""

    daily = (
        events.groupby(["event_end_trading_day", "period_id"], as_index=False)[
            "excess_gross_opportunity_bps"
        ]
        .sum()
        .pivot(
            index="event_end_trading_day",
            columns="period_id",
            values="excess_gross_opportunity_bps",
        )
    )
    periods = (
        events[["period_id", "period_bars"]]
        .drop_duplicates()
        .sort_values("period_bars")
        .reset_index(drop=True)
    )
    order = periods["period_id"].astype(str).tolist()
    correlation = daily.reindex(columns=order).corr(method="spearman", min_periods=30)
    dsu = _DisjointSet(order)
    for left, right in zip(order[:-1], order[1:], strict=True):
        value = correlation.loc[left, right]
        if pd.notna(value) and float(value) >= DEPENDENCY_LINK_THRESHOLD:
            dsu.union(left, right)
    groups: dict[str, list[str]] = {}
    for value in order:
        groups.setdefault(dsu.find(value), []).append(value)
    platform_by_period: dict[str, str] = {}
    for number, members in enumerate(groups.values(), start=1):
        platform_id = f"platform_{number:02d}_{members[0]}_{members[-1]}"
        platform_by_period.update(dict.fromkeys(members, platform_id))
    time_effective: dict[str, float] = {}
    pair_rows: list[dict[str, object]] = []
    global_effective = _effective_count(correlation.to_numpy(float))
    for left in order:
        series = daily[left].dropna()
        rho1 = float(series.autocorr(1)) if len(series) > 2 else 0.0
        rho1 = float(np.clip(rho1 if math.isfinite(rho1) else 0.0, -0.99, 0.99))
        effective = float(np.clip(len(series) * (1.0 - rho1) / (1.0 + rho1), 1.0, len(series)))
        time_effective[left] = effective
        for right in order:
            pair = pd.concat([daily[left], daily[right]], axis=1).dropna()
            pair_rows.append(
                {
                    "left_period_id": left,
                    "right_period_id": right,
                    "pair_observation_count": len(pair),
                    "excess_gross_opportunity_spearman": float(correlation.loc[left, right]),
                    "same_platform": platform_by_period[left] == platform_by_period[right],
                    "left_time_effective_sample_count": effective,
                    "global_effective_scale_count": global_effective,
                    "adjacent_periods_independent_votes": False,
                }
            )
    platform_rows: list[dict[str, object]] = []
    bars_by_id = dict(zip(periods["period_id"].astype(str), periods["period_bars"].astype(int), strict=True))
    for platform_id in dict.fromkeys(platform_by_period.values()):
        members = [value for value in order if platform_by_period[value] == platform_id]
        local = correlation.loc[members, members].to_numpy(float)
        off_diagonal = local[~np.eye(len(local), dtype=bool)]
        platform_rows.append(
            {
                "platform_id": platform_id,
                "member_period_ids": "|".join(members),
                "member_count": len(members),
                "minimum_period_bars": min(bars_by_id[value] for value in members),
                "maximum_period_bars": max(bars_by_id[value] for value in members),
                "mean_within_platform_spearman": float(np.nanmean(off_diagonal)) if len(off_diagonal) else 1.0,
                "effective_scale_count": _effective_count(local),
                "independent_platform_vote": True,
            }
        )
    return pd.DataFrame(pair_rows), pd.DataFrame(platform_rows), platform_by_period, time_effective


def build_annual_and_rolling_stability(events: pd.DataFrame) -> pd.DataFrame:
    """Build natural-year evidence and 12m/step-6m boundary sensitivity."""

    rows: list[dict[str, object]] = []
    for (period_id, period_bars, year), group in events.groupby(
        ["period_id", "period_bars", "natural_year"], sort=True
    ):
        rows.append(
            {
                "window_kind": "natural_year",
                "window_id": str(year),
                "start": f"{year}-01-01",
                "end_exclusive": f"{year + 1}-01-01",
                "period_id": period_id,
                "period_bars": int(period_bars),
                "event_count": len(group),
                "gross_opportunity_pct": float(group["gross_opportunity_log_value"].sum() * 100.0),
                "net_opportunity_pct_7bp": float(group["net_opportunity_log_value_7bp"].sum() * 100.0),
                "excess_gross_opportunity_pct": float(
                    group["excess_gross_opportunity_log_value"].sum() * 100.0
                ),
                "excess_net_opportunity_pct_7bp": float(
                    group["excess_net_opportunity_log_value_7bp"].sum() * 100.0
                ),
                "median_net_event_bps_7bp": float(group["net_opportunity_bps_7bp"].median()),
                "median_excess_net_event_bps_7bp": float(
                    group["excess_net_opportunity_bps_7bp"].median()
                ),
                "independent_evidence_vote": True,
            }
        )
    monthly = events.copy()
    monthly["month"] = pd.to_datetime(monthly["event_end_trading_day"]).dt.to_period("M")
    segments = (
        ("development", pd.Period("2015-01", freq="M"), pd.Period("2020-12", freq="M")),
        ("repeat_audit", pd.Period("2022-01", freq="M"), pd.Period("2024-12", freq="M")),
    )
    for role, first, last in segments:
        starts = pd.period_range(first, last - 11, freq="M")[::6]
        for start in starts:
            end = start + 12
            scoped = monthly.loc[
                monthly["chronological_role"].eq(role)
                & monthly["month"].ge(start)
                & monthly["month"].lt(end)
            ]
            for (period_id, period_bars), group in scoped.groupby(["period_id", "period_bars"], sort=True):
                rows.append(
                    {
                        "window_kind": "rolling_12m_step6m",
                        "window_id": f"{start}_{end - 1}",
                        "start": str(start.start_time.date()),
                        "end_exclusive": str(end.start_time.date()),
                        "period_id": period_id,
                        "period_bars": int(period_bars),
                        "event_count": len(group),
                        "gross_opportunity_pct": float(group["gross_opportunity_log_value"].sum() * 100.0),
                        "net_opportunity_pct_7bp": float(group["net_opportunity_log_value_7bp"].sum() * 100.0),
                        "excess_gross_opportunity_pct": float(
                            group["excess_gross_opportunity_log_value"].sum() * 100.0
                        ),
                        "excess_net_opportunity_pct_7bp": float(
                            group["excess_net_opportunity_log_value_7bp"].sum() * 100.0
                        ),
                        "median_net_event_bps_7bp": float(group["net_opportunity_bps_7bp"].median()),
                        "median_excess_net_event_bps_7bp": float(
                            group["excess_net_opportunity_bps_7bp"].median()
                        ),
                        "independent_evidence_vote": False,
                    }
                )
    return pd.DataFrame(rows).sort_values(["period_bars", "start", "window_kind"]).reset_index(drop=True)


def build_period_summary(
    attribute_cube: pd.DataFrame,
    atlas: pd.DataFrame,
    stability: pd.DataFrame,
    time_effective: dict[str, float],
) -> pd.DataFrame:
    """Combine causal attributes, opportunity ceilings and stability diagnostics."""

    pooled = atlas.loc[atlas["scope_id"].eq("pooled_consumed_history")].copy()
    development = atlas.loc[
        atlas["scope_id"].eq("development_2015_2020"),
        [
            "period_id",
            "annualized_net_opportunity_pct_7bp",
            "annualized_excess_net_opportunity_pct_7bp",
        ],
    ].rename(
        columns={
            "annualized_net_opportunity_pct_7bp": "development_annualized_net_opportunity_pct_7bp",
            "annualized_excess_net_opportunity_pct_7bp": (
                "development_annualized_excess_net_opportunity_pct_7bp"
            ),
        }
    )
    repeat = atlas.loc[
        atlas["scope_id"].eq("repeat_audit_2022_2024"),
        [
            "period_id",
            "annualized_net_opportunity_pct_7bp",
            "annualized_excess_net_opportunity_pct_7bp",
        ],
    ].rename(
        columns={
            "annualized_net_opportunity_pct_7bp": "repeat_annualized_net_opportunity_pct_7bp",
            "annualized_excess_net_opportunity_pct_7bp": (
                "repeat_annualized_excess_net_opportunity_pct_7bp"
            ),
        }
    )
    attribute = (
        attribute_cube.groupby(["period_id", "period_bars"], as_index=False)
        .agg(
            mean_raw_path_efficiency=("raw_scale_path_efficiency", "mean"),
            mean_scale_normalized_path_efficiency=("scale_normalized_path_efficiency", "mean"),
            mean_raw_variance_ratio=("raw_scale_variance_ratio", "mean"),
            mean_component_bdci=("component_bdci", "mean"),
            mean_trendable_power_share=("trendable_power_share", "mean"),
            mean_noise_adjusted_trendable_power_share=(
                "noise_adjusted_trendable_power_share",
                "mean",
            ),
            mean_cumulative_faster_burden=("cumulative_faster_power_burden", "mean"),
            valid_attribute_day_count=("raw_scale_path_efficiency", "count"),
        )
    )
    natural = stability.loc[stability["window_kind"].eq("natural_year")]
    natural_stats = (
        natural.groupby("period_id", as_index=False)
        .agg(
            natural_year_count=("window_id", "count"),
            natural_year_net_opportunity_mean_pct=("net_opportunity_pct_7bp", "mean"),
            natural_year_net_opportunity_floor_pct=("net_opportunity_pct_7bp", "min"),
            natural_year_net_opportunity_std_pct=("net_opportunity_pct_7bp", "std"),
            natural_year_excess_net_opportunity_mean_pct=(
                "excess_net_opportunity_pct_7bp",
                "mean",
            ),
            natural_year_excess_net_opportunity_floor_pct=(
                "excess_net_opportunity_pct_7bp",
                "min",
            ),
            natural_year_excess_net_opportunity_std_pct=(
                "excess_net_opportunity_pct_7bp",
                "std",
            ),
        )
    )
    natural_stats["natural_year_coefficient_of_variation"] = natural_stats[
        "natural_year_net_opportunity_std_pct"
    ].div(natural_stats["natural_year_net_opportunity_mean_pct"].where(lambda value: value.gt(EPSILON)))
    natural_stats["natural_year_excess_coefficient_of_variation"] = natural_stats[
        "natural_year_excess_net_opportunity_std_pct"
    ].div(natural_stats["natural_year_excess_net_opportunity_mean_pct"].abs().clip(lower=EPSILON))
    rolling = stability.loc[stability["window_kind"].eq("rolling_12m_step6m")]
    rolling_floor = (
        rolling.groupby("period_id", as_index=False)
        .agg(
            rolling_12m_net_opportunity_floor_pct=("net_opportunity_pct_7bp", "min"),
            rolling_12m_excess_net_opportunity_floor_pct=(
                "excess_net_opportunity_pct_7bp",
                "min",
            ),
        )
    )
    result = (
        pooled.merge(attribute, on=["period_id", "period_bars"], validate="one_to_one")
        .merge(development, on="period_id", validate="one_to_one")
        .merge(repeat, on="period_id", validate="one_to_one")
        .merge(natural_stats, on="period_id", validate="one_to_one")
        .merge(rolling_floor, on="period_id", validate="one_to_one")
    )
    result["effective_event_count"] = result["period_id"].map(time_effective)
    result["development_repeat_relative_gap"] = 2.0 * (
        result["repeat_annualized_excess_net_opportunity_pct_7bp"]
        - result["development_annualized_excess_net_opportunity_pct_7bp"]
    ).abs().div(
        (
            result["repeat_annualized_excess_net_opportunity_pct_7bp"].abs()
            + result["development_annualized_excess_net_opportunity_pct_7bp"].abs()
        ).clip(lower=EPSILON)
    )
    result["uncertainty_penalty"] = 1.0 / np.sqrt(result["effective_event_count"].clip(lower=1.0)) + result[
        "development_repeat_relative_gap"
    ]
    return result.sort_values("period_bars").reset_index(drop=True)


def build_cross_frequency_market_products(
    log_close: pd.Series,
    trading_day: pd.Series,
    coordinates: tuple[CrossFrequencyCoordinate, ...] | None = None,
) -> CrossFrequencyMarketProducts:
    """Build all market-side products without positions or a strategy PnL path."""

    selected = coordinates or default_coordinates()
    registry = build_coordinate_registry(selected)
    cube = build_attribute_cube(log_close, trading_day, selected)
    events = build_opportunity_events(log_close, trading_day, selected)
    atlas = build_opportunity_atlas(events)
    rademacher = build_rademacher_sensitivity(events)
    burden = build_interference_burden_matrix(cube)
    phase = build_phase_propagation_graph(cube)
    dependency, platforms, _, time_effective = build_dependency_products(events)
    stability = build_annual_and_rolling_stability(events)
    summary = build_period_summary(cube, atlas, stability, time_effective)
    cost_sensitivity = build_opportunity_cost_sensitivity(events)
    curve_shape = build_frequency_curve_shape(cost_sensitivity)
    offset_sensitivity = build_opportunity_offset_sensitivity(
        log_close,
        trading_day,
        selected,
    )
    offset_peaks = build_offset_peak_stability(offset_sensitivity)
    offset_7 = offset_sensitivity.loc[
        offset_sensitivity["scope_id"].eq("pooled_consumed_history")
        & offset_sensitivity["roundtrip_cost_bps"].eq(7.0)
    ]
    offset_summary = (
        offset_7.groupby(["period_id", "period_bars"], as_index=False)
        .agg(
            offset_7bp_excess_mean_pct=(
                "annualized_excess_net_opportunity_pct",
                "mean",
            ),
            offset_7bp_excess_std_pct=(
                "annualized_excess_net_opportunity_pct",
                "std",
            ),
            offset_7bp_excess_floor_pct=(
                "annualized_excess_net_opportunity_pct",
                "min",
            ),
            offset_7bp_excess_ceiling_pct=(
                "annualized_excess_net_opportunity_pct",
                "max",
            ),
        )
    )
    offset_summary["offset_7bp_excess_coefficient_of_variation"] = offset_summary[
        "offset_7bp_excess_std_pct"
    ].div(offset_summary["offset_7bp_excess_mean_pct"].abs().clip(lower=EPSILON))
    concentration = (
        events.groupby(["period_id", "period_bars"], as_index=False)
        .agg(
            mean_maximum_increment_sigma_share=(
                "maximum_increment_sigma_share",
                "mean",
            ),
            p95_maximum_increment_sigma_share=(
                "maximum_increment_sigma_share",
                lambda values: values.quantile(0.95),
            ),
        )
    )
    summary = summary.merge(
        offset_summary,
        on=["period_id", "period_bars"],
        validate="one_to_one",
    ).merge(
        concentration,
        on=["period_id", "period_bars"],
        validate="one_to_one",
    )
    summary["null_and_offset_uncertainty_penalty"] = (
        summary["uncertainty_penalty"]
        + summary["offset_7bp_excess_coefficient_of_variation"]
        + summary["p95_maximum_increment_sigma_share"]
    )
    return CrossFrequencyMarketProducts(
        coordinate_registry=registry,
        attribute_cube=cube,
        opportunity_events=events,
        opportunity_atlas=atlas,
        interference_burden_matrix=burden,
        phase_propagation_graph=phase,
        dependency_matrix=dependency,
        platform_dependency=platforms,
        annual_and_rolling_stability=stability,
        period_summary=summary,
        cost_sensitivity_surface=cost_sensitivity,
        frequency_curve_shape=curve_shape,
        offset_sensitivity_surface=offset_sensitivity,
        offset_peak_stability=offset_peaks,
        rademacher_sensitivity=rademacher,
    )


def summarize_execution_feasibility(
    endpoint_inventory: pd.DataFrame,
    *,
    denominator_panel: pd.DataFrame | None = None,
    period_bindings: dict[str, int] | None = None,
    target_periods: tuple[int, ...] = DEFAULT_PERIODS,
) -> pd.DataFrame:
    """Summarize exact quote/latency/depth feasibility; returns are forbidden."""

    forbidden = {"return", "pnl", "sharpe"}
    if any(any(token in str(column).lower() for token in forbidden) for column in endpoint_inventory.columns):
        raise ValidationError("execution feasibility input must not contain return, PnL or Sharpe columns")
    required = {
        "family",
        "period_minutes",
        "trade_uid",
        "entry_decision_time",
        "exit_decision_time",
        "entry_quote_available_at",
        "exit_quote_available_at",
        "entry_bid_price",
        "entry_ask_price",
        "exit_bid_price",
        "exit_ask_price",
        "entry_ask_volume",
        "exit_bid_volume",
        "resolved",
    }
    if missing := sorted(required.difference(endpoint_inventory.columns)):
        raise ValidationError(f"execution feasibility input missing columns: {missing}")
    if denominator_panel is None:
        denominator_rows: list[dict[str, object]] = []
        for period, group in endpoint_inventory.groupby("period_minutes", sort=True):
            denominator_rows.append(
                {
                    "scope_id": "pooled_repeat_audit",
                    "period_minutes": int(period),
                    "expected_episode_count": len(group),
                    "upstream_resolved_trade_count": len(group),
                }
            )
            years = pd.to_datetime(group["entry_decision_time"], utc=True).dt.year
            for year, count in years.value_counts().sort_index().items():
                denominator_rows.append(
                    {
                        "scope_id": f"year_{int(year)}",
                        "period_minutes": int(period),
                        "expected_episode_count": int(count),
                        "upstream_resolved_trade_count": int(count),
                    }
                )
        denominators = pd.DataFrame(denominator_rows)
    else:
        denominators = denominator_panel.copy()
    denominator_required = {
        "scope_id",
        "period_minutes",
        "expected_episode_count",
        "upstream_resolved_trade_count",
    }
    if missing := sorted(denominator_required.difference(denominators.columns)):
        raise ValidationError(f"execution denominator panel missing columns: {missing}")
    bindings = period_bindings or {f"P{period}": period for period in target_periods}
    rows: list[dict[str, object]] = []
    for target in target_periods:
        period_id = f"P{target}"
        source_period = int(bindings.get(period_id, target))
        group = endpoint_inventory.loc[endpoint_inventory["period_minutes"].eq(source_period)].copy()
        resolved = group.loc[group["resolved"].astype(bool)].copy()
        pooled_denominator = denominators.loc[
            denominators["scope_id"].eq("pooled_repeat_audit")
            & denominators["period_minutes"].eq(source_period)
        ]
        if len(pooled_denominator) != 1:
            raise ValidationError(f"execution denominator missing pooled period {source_period}")
        expected_episode_count = int(pooled_denominator["expected_episode_count"].iloc[0])
        upstream_resolved_count = int(
            pooled_denominator["upstream_resolved_trade_count"].iloc[0]
        )
        if upstream_resolved_count != len(group):
            raise ValidationError(
                f"upstream resolved denominator drifted for period {source_period}"
            )
        mapping_error = abs(source_period - target) / target
        for frame in (group, resolved):
            for column in ("entry_decision_time", "exit_decision_time", "entry_quote_available_at", "exit_quote_available_at"):
                frame[column] = pd.to_datetime(frame[column], utc=True, errors="coerce")
        entry_mid = (resolved["entry_bid_price"] + resolved["entry_ask_price"]) / 2.0
        exit_mid = (resolved["exit_bid_price"] + resolved["exit_ask_price"]) / 2.0
        entry_spread = (resolved["entry_ask_price"] - resolved["entry_bid_price"]).div(entry_mid.where(entry_mid.gt(0.0))) * 10_000.0
        exit_spread = (resolved["exit_ask_price"] - resolved["exit_bid_price"]).div(exit_mid.where(exit_mid.gt(0.0))) * 10_000.0
        entry_latency = (resolved["entry_quote_available_at"] - resolved["entry_decision_time"]).dt.total_seconds()
        exit_latency = (resolved["exit_quote_available_at"] - resolved["exit_decision_time"]).dt.total_seconds()
        holding = (resolved["exit_decision_time"] - resolved["entry_decision_time"]).dt.total_seconds() / 60.0
        horizon = (target + 1) // 2
        endpoint_latency = pd.concat([entry_latency, exit_latency])
        minimum_capacity = pd.concat(
            [resolved["entry_ask_volume"], resolved["exit_bid_volume"]], axis=1
        ).min(axis=1)
        maximum_wait = pd.concat([entry_latency, exit_latency], axis=1).max(axis=1)
        annual_end_to_end: list[float] = []
        annual_conditional: list[float] = []
        entry_year = pd.to_datetime(group["entry_decision_time"], utc=True).dt.year
        resolved_year = pd.to_datetime(resolved["entry_decision_time"], utc=True).dt.year
        for year in (2022, 2023, 2024):
            annual_denominator = denominators.loc[
                denominators["scope_id"].eq(f"year_{year}")
                & denominators["period_minutes"].eq(source_period)
            ]
            if len(annual_denominator) != 1:
                raise ValidationError(
                    f"execution denominator missing year {year}, period {source_period}"
                )
            annual_expected = int(annual_denominator["expected_episode_count"].iloc[0])
            annual_upstream = int(
                annual_denominator["upstream_resolved_trade_count"].iloc[0]
            )
            actual_upstream = int(entry_year.eq(year).sum())
            if annual_upstream != actual_upstream:
                raise ValidationError(
                    f"annual upstream denominator drifted for {year}, period {source_period}"
                )
            annual_exact = int(resolved_year.eq(year).sum())
            annual_end_to_end.append(annual_exact / annual_expected)
            annual_conditional.append(
                annual_exact / annual_upstream if annual_upstream else np.nan
            )
        rows.append(
            {
                "period_id": period_id,
                "period_bars": target,
                "execution_source_period_minutes": source_period,
                "mapping_quality": "exact"
                if mapping_error == 0.0
                else "nearest_within_12pct"
                if mapping_error <= 0.12
                else "unsupported",
                "relative_scale_mapping_error": mapping_error,
                "requested_trade_count": expected_episode_count,
                "expected_episode_count": expected_episode_count,
                "upstream_resolved_trade_count": upstream_resolved_count,
                "upstream_resolution_coverage": upstream_resolved_count
                / expected_episode_count,
                "conditional_quote_denominator_count": len(group),
                "resolved_trade_count": len(resolved),
                "conditional_both_endpoint_exact_l1_coverage": len(resolved)
                / upstream_resolved_count,
                "end_to_end_both_endpoint_exact_l1_coverage": len(resolved)
                / expected_episode_count,
                "annual_end_to_end_exact_l1_coverage_std": float(
                    np.std(annual_end_to_end, ddof=0)
                ),
                "annual_end_to_end_exact_l1_coverage_range": float(
                    max(annual_end_to_end) - min(annual_end_to_end)
                ),
                "annual_conditional_exact_l1_coverage_std": float(
                    np.nanstd(annual_conditional, ddof=0)
                ),
                "mean_entry_quote_latency_seconds": float(entry_latency.mean()) if len(resolved) else np.nan,
                "mean_exit_quote_latency_seconds": float(exit_latency.mean()) if len(resolved) else np.nan,
                "p95_endpoint_quote_latency_seconds": float(endpoint_latency.quantile(0.95)) if len(resolved) else np.nan,
                "mean_entry_quoted_spread_bps": float(entry_spread.mean()) if len(resolved) else np.nan,
                "mean_exit_quoted_spread_bps": float(exit_spread.mean()) if len(resolved) else np.nan,
                "median_minimum_roundtrip_l1_contract_capacity": float(minimum_capacity.median())
                if len(resolved)
                else np.nan,
                "median_holding_clock_minutes": float(holding.median()) if len(resolved) else np.nan,
                "median_wait_to_opportunity_horizon_ratio": float(maximum_wait.median() / (horizon * 60.0))
                if len(resolved)
                else np.nan,
                "representative_frozen_event_only": True,
                "execution_outcome_consumed": False,
                "execution_economics_authority": False,
            }
        )
    return pd.DataFrame(rows)


def pareto_flags(
    frame: pd.DataFrame,
    *,
    maximize: tuple[str, ...],
    minimize: tuple[str, ...],
    tolerance: float = 1e-12,
) -> pd.Series:
    """Return non-dominated flags without manufacturing a scalar score."""

    columns = [*maximize, *minimize]
    if missing := sorted(set(columns).difference(frame.columns)):
        raise ValidationError(f"Pareto columns missing: {missing}")
    values = frame[columns].apply(pd.to_numeric, errors="coerce")
    eligible = values.notna().all(axis=1)
    result = pd.Series(False, index=frame.index, dtype=bool)
    for index in frame.index[eligible]:
        candidate = values.loc[index]
        dominated = False
        for other_index in frame.index[eligible]:
            if other_index == index:
                continue
            other = values.loc[other_index]
            no_worse = all(other[column] >= candidate[column] - tolerance for column in maximize) and all(
                other[column] <= candidate[column] + tolerance for column in minimize
            )
            strictly_better = any(other[column] > candidate[column] + tolerance for column in maximize) or any(
                other[column] < candidate[column] - tolerance for column in minimize
            )
            if no_worse and strictly_better:
                dominated = True
                break
        result.loc[index] = not dominated
    return result


def build_pareto_surfaces(
    period_summary: pd.DataFrame,
    execution_feasibility: pd.DataFrame,
    platform_dependency: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build separate platform-level return-opportunity and stability Pareto sets."""

    summary = period_summary.merge(
        execution_feasibility[
            [
                "period_id",
                "conditional_both_endpoint_exact_l1_coverage",
                "end_to_end_both_endpoint_exact_l1_coverage",
                "annual_end_to_end_exact_l1_coverage_std",
                "p95_endpoint_quote_latency_seconds",
                "mean_entry_quoted_spread_bps",
                "mean_exit_quoted_spread_bps",
                "relative_scale_mapping_error",
            ]
        ],
        on="period_id",
        how="left",
        validate="one_to_one",
    )
    membership: dict[str, str] = {}
    for row in platform_dependency.itertuples(index=False):
        for period_id in str(row.member_period_ids).split("|"):
            membership[period_id] = str(row.platform_id)
    summary["platform_id"] = summary["period_id"].map(membership)
    representative_rows: list[pd.Series] = []
    for platform_id, group in summary.groupby("platform_id", sort=True):
        ordered = group.sort_values("period_bars")
        minimum = int(ordered["period_bars"].min())
        maximum = int(ordered["period_bars"].max())
        geometric_midpoint = math.sqrt(minimum * maximum)
        distance = np.abs(np.log(ordered["period_bars"] / geometric_midpoint))
        representative = ordered.loc[distance.idxmin()].copy()
        representative["platform_id"] = platform_id
        representative["member_period_ids"] = "|".join(
            ordered["period_id"].astype(str)
        )
        representative["member_count"] = len(ordered)
        representative["minimum_period_bars"] = minimum
        representative["maximum_period_bars"] = maximum
        representative["representative_period_id"] = str(representative["period_id"])
        representative["platform_aggregation"] = "log_period_medoid"
        representative_rows.append(representative)
    aggregated = pd.DataFrame(representative_rows).reset_index(drop=True)
    aggregated["representative_end_to_end_exact_l1_coverage"] = aggregated[
        "end_to_end_both_endpoint_exact_l1_coverage"
    ]
    aggregated["execution_coverage_variation"] = aggregated[
        "annual_end_to_end_exact_l1_coverage_std"
    ]
    return_surface = aggregated.copy()
    return_surface["pareto_nondominated"] = pareto_flags(
        return_surface,
        maximize=(
            "annualized_excess_net_opportunity_pct_7bp",
            "median_excess_net_event_bps_7bp",
            "mean_scale_normalized_path_efficiency",
            "representative_end_to_end_exact_l1_coverage",
        ),
        minimize=(
            "null_and_offset_uncertainty_penalty",
            "relative_scale_mapping_error",
        ),
    )
    return_surface["actual_expected_return_claim"] = False
    return_surface["scalar_score"] = pd.NA
    stability_surface = aggregated.copy()
    stability_surface["pareto_nondominated"] = pareto_flags(
        stability_surface,
        maximize=(
            "natural_year_excess_net_opportunity_floor_pct",
            "rolling_12m_excess_net_opportunity_floor_pct",
            "effective_event_count",
            "representative_end_to_end_exact_l1_coverage",
        ),
        minimize=(
            "natural_year_excess_coefficient_of_variation",
            "top_5pct_absolute_excess_concentration",
            "execution_coverage_variation",
            "offset_7bp_excess_coefficient_of_variation",
            "relative_scale_mapping_error",
        ),
    )
    stability_surface["actual_sharpe_claim"] = False
    stability_surface["scalar_score"] = pd.NA
    return return_surface, stability_surface


def infrastructure_contract() -> dict[str, object]:
    """Return the machine-readable authority and product contract."""

    return {
        "schema_id": SCHEMA_ID,
        "infrastructure_id": INFRASTRUCTURE_ID,
        "products": [
            "cross_frequency_coordinate_registry@2.0",
            "cross_frequency_attribute_cube@2.0",
            "frequency_interference_burden_matrix@2.0",
            "causal_phase_propagation_graph@2.0",
            "scale_opportunity_ceiling_atlas@2.0",
            "cross_frequency_execution_feasibility_cube@2.0",
            "frequency_dependency_effective_sample_matrix@2.0",
            "return_and_stability_potential_protocol@2.0",
            "opportunity_offset_sensitivity@2.0",
            "gaussian_null_rademacher_sensitivity@2.0",
        ],
        "null_model": "conditional_gaussian_folded_normal_approximation",
        "null_model_exact_random_sign_authority": False,
        "exact_rademacher_small_horizon_audit": True,
        "causal_state_resets_at_declared_data_gaps": True,
        "execution_coverage_denominator": "all_expected_episodes",
        "band_power_cross_grid_comparable": False,
        "band_power_pareto_authority": False,
        "offset_views_independent_votes": False,
        "same_raw_parent_required": True,
        "strategy_signal_constructed": False,
        "strategy_position_constructed": False,
        "expected_return_without_policy_forbidden": True,
        "sharpe_without_policy_forbidden": True,
        "overlapping_windows_independent_votes": False,
        "adjacent_periods_independent_votes": False,
        "scalar_frequency_score_forbidden": True,
        "oracle_lookahead_only": True,
        "measurement_authority": True,
        "strategy_authority": False,
        "routing_authority": False,
        "production_authority": False,
    }


__all__ = [
    "BARS_PER_SESSION",
    "COMMON_COST_GRID_BPS",
    "CURVE_MATERIALITY_ABSOLUTE_PCT",
    "DEFAULT_PERIODS",
    "DEPENDENCY_LINK_THRESHOLD",
    "INFRASTRUCTURE_ID",
    "ROUNDTRIP_STRESS_BPS",
    "SCHEMA_ID",
    "CrossFrequencyCoordinate",
    "CrossFrequencyMarketProducts",
    "build_annual_and_rolling_stability",
    "build_attribute_cube",
    "build_coordinate_registry",
    "build_cross_frequency_market_products",
    "build_dependency_products",
    "build_interference_burden_matrix",
    "build_frequency_curve_shape",
    "build_offset_peak_stability",
    "build_opportunity_atlas",
    "build_opportunity_cost_sensitivity",
    "build_opportunity_events",
    "build_opportunity_offset_sensitivity",
    "build_pareto_surfaces",
    "build_phase_propagation_graph",
    "build_period_summary",
    "build_rademacher_sensitivity",
    "default_coordinates",
    "infrastructure_contract",
    "pareto_flags",
    "summarize_execution_feasibility",
]
