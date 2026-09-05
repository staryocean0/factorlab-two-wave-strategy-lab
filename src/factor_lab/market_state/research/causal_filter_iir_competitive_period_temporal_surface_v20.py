# pyright: reportAny=false, reportArgumentType=false, reportAssignmentType=false
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportOperatorIssue=false
# pyright: reportReturnType=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false

"""Preregistered IIR competitive-envelope and temporal-surface research.

The module separates three claims that older experiments mixed together:
which periods remain economically competitive after A-share T+1, whether the
scale surface can be followed causally, and whether that surface can own an
IIR period out of sample.  Each downstream claim is forbidden when its
prerequisite gate fails.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.filtering.timing_validation import FilterSpec, apply_filter_spec, signal_from_filtered

SCHEMA_ID: Final[str] = "market_state_causal_filter_iir_competitive_period_temporal_surface@20.0"
CODE_VERSION: Final[str] = "causal-filter-iir-competitive-period-temporal-surface-20260811-v20"
PREREGISTRATION_SHA256: Final[str] = "363009f6ec0c40ef73939226bd9a9cec603aa76aff4b041f9d2b1116c8cbbb67"

Q_VALUE: Final[float] = 0.8
PERIOD_CANDIDATES: Final[tuple[int, ...]] = (
    8, 10, 12, 14, 16, 20, 24, 28, 32, 36, 40, 48,
    60, 80, 100, 120, 160, 200, 240, 300, 400, 500, 640, 800,
)
COST_STRESS_BPS: Final[tuple[float, ...]] = (5.0, 7.0, 10.0)
PRIMARY_COST_BPS: Final[float] = 7.0
ANNUALIZATION_BARS: Final[float] = 960.0
WARMUP_START: Final[pd.Timestamp] = pd.Timestamp("2008-01-01")
DEVELOPMENT_START: Final[pd.Timestamp] = pd.Timestamp("2009-01-01")
DEVELOPMENT_END: Final[pd.Timestamp] = pd.Timestamp("2018-01-01")
REPEAT_AUDIT_END: Final[pd.Timestamp] = pd.Timestamp("2021-01-01")
SEALED_START: Final[pd.Timestamp] = pd.Timestamp("2021-01-01")

MATERIAL_QUARTER_WIN: Final[float] = 0.0025
MIN_PRIMARY_WIN_FRACTION: Final[float] = 0.20
MIN_PRIMARY_SCOPE_COVERAGE: Final[int] = 3
MIN_10BPS_WIN_FRACTION: Final[float] = 0.15
MIN_POSITION_MISMATCH: Final[float] = 0.05
MAX_TOP_POSITIVE_QUARTER_SHARE: Final[float] = 0.35
MAX_COMPETITIVE_GAP_RATIO: Final[float] = 2.5

SURFACE_STEP_DAYS: Final[int] = 5
SURFACE_HORIZONS_DAYS: Final[tuple[int, ...]] = (5, 20)
SURFACE_MIN_RHO: Final[float] = 0.60
SURFACE_REQUIRED_SCOPES: Final[int] = 3
OWNERSHIP_STEP_DAYS: Final[int] = 20
RIDGE_LAMBDA: Final[float] = 10.0


@dataclass(frozen=True, slots=True)
class Scope:
    scope_id: str
    start: pd.Timestamp
    end: pd.Timestamp


DEVELOPMENT_SCOPES: Final[tuple[Scope, ...]] = (
    Scope("dev_2009_2012", pd.Timestamp("2009-01-01"), pd.Timestamp("2013-01-01")),
    Scope("dev_2013_2014", pd.Timestamp("2013-01-01"), pd.Timestamp("2015-01-01")),
    Scope("dev_2015_2016", pd.Timestamp("2015-01-01"), pd.Timestamp("2017-01-01")),
    Scope("dev_2017", pd.Timestamp("2017-01-01"), DEVELOPMENT_END),
)


@dataclass(frozen=True, slots=True)
class OwnershipFold:
    fold_id: str
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


OWNERSHIP_FOLDS: Final[tuple[OwnershipFold, ...]] = (
    OwnershipFold(
        "wf_2013_2014", DEVELOPMENT_START, pd.Timestamp("2013-01-01"),
        pd.Timestamp("2013-01-01"), pd.Timestamp("2015-01-01"),
    ),
    OwnershipFold(
        "wf_2015_2016", DEVELOPMENT_START, pd.Timestamp("2015-01-01"),
        pd.Timestamp("2015-01-01"), pd.Timestamp("2017-01-01"),
    ),
    OwnershipFold(
        "wf_2017", DEVELOPMENT_START, pd.Timestamp("2017-01-01"),
        pd.Timestamp("2017-01-01"), DEVELOPMENT_END,
    ),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_preregistration(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = _sha256(path)
    if actual != PREREGISTRATION_SHA256:
        raise ValidationError(
            f"V20 preregistration changed after freeze: expected={PREREGISTRATION_SHA256}, actual={actual}"
        )
    return actual


def desired_column(period: int) -> str:
    return f"p{period}_desired_position"


def t1_column(period: int) -> str:
    return f"p{period}_t1_position"


def net_column(period: int, cost_bps: float) -> str:
    return f"p{period}_net_{cost_bps:g}bps"


def enforce_t_plus_one(desired: pd.Series) -> pd.Series:
    """Apply the A-share same-day sell lock to a binary decision path.

    A 0->1 decision at one 60m close owns the next interval.  A later 1->0
    decision on the same trade date is blocked; the first flat decision on a
    later trade date may close the position.
    """

    if not isinstance(desired.index, pd.DatetimeIndex):
        raise ValidationError("T+1 position requires a DatetimeIndex")
    values = pd.to_numeric(desired, errors="raise").fillna(0.0)
    if not bool(values.isin((0.0, 1.0)).all()):
        raise ValidationError("T+1 desired position must be binary")
    held = False
    entry_date: object | None = None
    actual: list[float] = []
    for timestamp, wanted in values.items():
        trade_date = timestamp.date()
        if not held and wanted > 0.0:
            held = True
            entry_date = trade_date
        elif held and wanted <= 0.0 and entry_date is not None and trade_date != entry_date:
            held = False
            entry_date = None
        actual.append(1.0 if held else 0.0)
    return pd.Series(actual, index=desired.index, dtype=float, name="t1_position")


def costed_path(position: pd.Series, forward_return: pd.Series, *, cost_bps: float) -> pd.Series:
    aligned = pd.concat(
        [
            pd.to_numeric(position, errors="raise").rename("position"),
            pd.to_numeric(forward_return, errors="raise").rename("forward_return"),
        ],
        axis=1,
    )
    turnover = aligned["position"].diff().abs().fillna(aligned["position"].abs())
    return aligned["position"] * aligned["forward_return"] - turnover * (float(cost_bps) / 10_000.0)


def build_period_panel(
    strategy_bars: pd.DataFrame,
    *,
    periods: Sequence[int] = PERIOD_CANDIDATES,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build causal component signals, true T+1 positions and costed paths."""

    required = {"timestamp", "close"}
    if not required.issubset(strategy_bars.columns):
        raise ValidationError(f"V20 strategy bars missing: {sorted(required - set(strategy_bars.columns))}")
    times = pd.DatetimeIndex(pd.to_datetime(strategy_bars["timestamp"], errors="raise"))
    if times.has_duplicates or not times.is_monotonic_increasing:
        raise ValidationError("V20 strategy timestamps must be unique and ordered")
    close = pd.to_numeric(strategy_bars["close"], errors="raise")
    if bool(close.le(0.0).any()):
        raise ValidationError("V20 close must be positive")
    log_close = pd.Series(np.log(close.to_numpy(float)), index=times, name="log_close")
    panel = pd.DataFrame(
        {
            "close": close.to_numpy(float),
            "raw_log_return": log_close.diff(),
            "forward_market_log_return": log_close.shift(-1) - log_close,
        },
        index=times,
    )
    component_columns: dict[str, pd.Series] = {}
    period_columns: dict[str, pd.Series] = {}
    for period in periods:
        component = apply_filter_spec(
            log_close,
            FilterSpec(
                f"iir_bandpass_p{period}_q0_8",
                "laplace_iir",
                "bandpass",
                {"period": int(period), "q": Q_VALUE},
                "component",
            ),
        )
        desired = signal_from_filtered(component, output_kind="component")
        actual = enforce_t_plus_one(desired)
        component_columns[f"p{period}_component"] = component
        period_columns[desired_column(period)] = desired
        period_columns[t1_column(period)] = actual
        for cost in COST_STRESS_BPS:
            period_columns[net_column(period, cost)] = costed_path(
                actual, panel["forward_market_log_return"], cost_bps=cost
            )
    period_panel = pd.DataFrame(period_columns, index=times)
    components = pd.DataFrame(component_columns, index=times)
    return pd.concat([panel, period_panel], axis=1), components


def _path_metrics(path: pd.Series, position: pd.Series) -> dict[str, float | int]:
    local = pd.to_numeric(path, errors="raise").dropna()
    pos = pd.to_numeric(position.reindex(local.index), errors="raise").fillna(0.0)
    equity = local.cumsum()
    drawdown = equity - equity.cummax()
    std = float(local.std(ddof=0))
    changes = pos.diff().abs().fillna(pos.abs())
    return {
        "bar_count": int(len(local)),
        "net_log_return": float(local.sum()),
        "annualized_sharpe": float(local.mean() / std * math.sqrt(ANNUALIZATION_BARS)) if std > 0.0 else 0.0,
        "max_log_drawdown": float(drawdown.min()) if not drawdown.empty else 0.0,
        "turnover_count": float(changes.sum()),
        "position_change_count": int(changes.gt(0.0).sum()),
    }


def static_period_summary(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    scopes = (*DEVELOPMENT_SCOPES, Scope("development_2009_2017", DEVELOPMENT_START, DEVELOPMENT_END))
    for scope in scopes:
        mask = (panel.index >= scope.start) & (panel.index < scope.end)
        for cost in COST_STRESS_BPS:
            for period in PERIOD_CANDIDATES:
                metrics = _path_metrics(panel.loc[mask, net_column(period, cost)], panel.loc[mask, t1_column(period)])
                rows.append({"scope_id": scope.scope_id, "cost_bps": cost, "period_bars": period, **metrics})
    return pd.DataFrame(rows)


def select_robust_anchor(static: pd.DataFrame) -> tuple[int, pd.DataFrame]:
    subscopes = {scope.scope_id for scope in DEVELOPMENT_SCOPES}
    local = static.loc[static["scope_id"].isin(subscopes)].copy()
    local["net_percentile_rank"] = local.groupby(["scope_id", "cost_bps"])["net_log_return"].rank(pct=True, method="average")
    score = (
        local.groupby("period_bars", as_index=False)
        .agg(
            median_net_percentile_rank=("net_percentile_rank", "median"),
            mean_turnover=("turnover_count", "mean"),
            median_sharpe=("annualized_sharpe", "median"),
        )
        .sort_values("period_bars")
    )
    best = float(score["median_net_percentile_rank"].max())
    candidates = score.loc[score["median_net_percentile_rank"].ge(best - 0.01)].copy()
    candidates = candidates.sort_values(["mean_turnover", "period_bars"], ascending=[True, False], kind="mergesort")
    anchor = int(candidates.iloc[0]["period_bars"])
    score["robust_anchor"] = score["period_bars"].eq(anchor)
    return anchor, score


def competitive_envelope(panel: pd.DataFrame, static: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    """Find the operational A-B range without claiming an eternal boundary."""

    anchor, anchor_score = select_robust_anchor(static)
    development = panel.loc[(panel.index >= DEVELOPMENT_START) & (panel.index < DEVELOPMENT_END)].copy()
    quarter = development.index.to_period("Q")
    rows: list[dict[str, object]] = []
    for period in PERIOD_CANDIDATES:
        primary_excess = development[net_column(period, PRIMARY_COST_BPS)] - development[net_column(anchor, PRIMARY_COST_BPS)]
        stress_excess = development[net_column(period, 10.0)] - development[net_column(anchor, 10.0)]
        primary_quarter = primary_excess.groupby(quarter).sum()
        stress_quarter = stress_excess.groupby(quarter).sum()
        primary_wins = primary_quarter.gt(MATERIAL_QUARTER_WIN)
        stress_wins = stress_quarter.gt(MATERIAL_QUARTER_WIN)
        covered_scopes = 0
        for scope in DEVELOPMENT_SCOPES:
            scoped = primary_quarter.loc[
                (primary_quarter.index.start_time >= scope.start)
                & (primary_quarter.index.start_time < scope.end)
            ]
            covered_scopes += int(bool(scoped.gt(MATERIAL_QUARTER_WIN).any()))
        positives = primary_quarter.loc[primary_quarter.gt(0.0)].sort_values(ascending=False)
        top_share = float(positives.iloc[0] / positives.sum()) if not positives.empty else 1.0
        mismatch = float(
            panel.loc[development.index, t1_column(period)].ne(
                panel.loc[development.index, t1_column(anchor)]
            ).mean()
        )
        qualifies = bool(
            period == anchor
            or (
                float(primary_wins.mean()) >= MIN_PRIMARY_WIN_FRACTION
                and covered_scopes >= MIN_PRIMARY_SCOPE_COVERAGE
                and float(stress_wins.mean()) >= MIN_10BPS_WIN_FRACTION
                and mismatch >= MIN_POSITION_MISMATCH
                and top_share <= MAX_TOP_POSITIVE_QUARTER_SHARE
            )
        )
        rows.append(
            {
                "period_bars": period,
                "robust_anchor_period_bars": anchor,
                "position_mismatch_ratio_vs_anchor": mismatch,
                "primary_cost_material_win_quarters": int(primary_wins.sum()),
                "primary_cost_quarter_count": int(len(primary_wins)),
                "primary_cost_material_win_fraction": float(primary_wins.mean()),
                "primary_cost_scope_coverage": covered_scopes,
                "stress_10bps_material_win_fraction": float(stress_wins.mean()),
                "top_positive_quarter_share": top_share,
                "aggregate_primary_excess_vs_anchor": float(primary_excess.sum()),
                "competitive": qualifies,
            }
        )
    detail = pd.DataFrame(rows).merge(anchor_score, on="period_bars", how="left")
    competitive = sorted(detail.loc[detail["competitive"], "period_bars"].astype(int).tolist())
    a = min(competitive)
    b = max(competitive)
    gaps = [right / left for left, right in zip(competitive[:-1], competitive[1:], strict=True)]
    disconnected = bool(gaps and max(gaps) > MAX_COMPETITIVE_GAP_RATIO)
    right_censored = b == max(PERIOD_CANDIDATES)
    passed = bool(not disconnected and not right_censored and len(competitive) >= 2)
    summary: dict[str, object] = {
        "robust_anchor_period_bars": anchor,
        "competitive_periods": competitive,
        "a_period_bars": a,
        "b_period_bars": b,
        "competitive_period_count": len(competitive),
        "maximum_adjacent_competitive_ratio": max(gaps) if gaps else 1.0,
        "disconnected_competitive_set": disconnected,
        "right_censored_at_p800": right_censored,
        "passed": passed,
        "verdict": (
            "competitive_envelope_passed"
            if passed
            else "competitive_envelope_unresolved_or_disconnected"
        ),
    }
    return detail, summary


def build_daily_surface(panel: pd.DataFrame, periods: Sequence[int]) -> pd.DataFrame:
    """Build a causal volatility/realized-autocorrelation-edge term surface."""

    raw = pd.to_numeric(panel["raw_log_return"], errors="raise")
    common_variance = raw.pow(2).ewm(span=132, adjust=False, min_periods=132).mean()
    normalized = raw.div(common_variance.shift(1).pow(0.5).where(common_variance.shift(1).gt(0.0)))
    surface = pd.DataFrame(index=panel.index)
    for period in periods:
        sigma = raw.pow(2).ewm(span=period, adjust=False, min_periods=period).mean().pow(0.5)
        surface[f"vol_p{period}"] = np.log(
            sigma.div(common_variance.pow(0.5).where(common_variance.gt(0.0)))
        )
        nu = 1.0 - 2.0 / (period + 1.0)
        loading = math.sqrt((1.0 + nu) / (1.0 - nu))
        signal = loading * normalized.ewm(span=period, adjust=False, min_periods=period).mean()
        payoff = signal.shift(1) * normalized
        surface[f"edge_p{period}"] = payoff.ewm(span=period, adjust=False, min_periods=period).mean()
    daily = surface.groupby(surface.index.normalize()).last().dropna()
    daily.index = pd.DatetimeIndex(daily.index)
    return daily


def _scope_id(timestamp: pd.Timestamp) -> str | None:
    for scope in DEVELOPMENT_SCOPES:
        if scope.start <= timestamp < scope.end:
            return scope.scope_id
    return None


def _cross_section_rho(left: np.ndarray, right: np.ndarray) -> float:
    if len(left) < 2:
        return 0.0
    left_rank = pd.Series(left).rank(method="average").to_numpy(float)
    right_rank = pd.Series(right).rank(method="average").to_numpy(float)
    value = np.corrcoef(left_rank, right_rank)[0, 1]
    return float(value) if np.isfinite(value) else 0.0


def surface_followability(
    daily_surface: pd.DataFrame,
    periods: Sequence[int],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Compare a causal carry-forward surface forecast with an expanding mean."""

    rows: list[dict[str, object]] = []
    columns_by_axis = {
        "volatility": [f"vol_p{period}" for period in periods],
        "edge": [f"edge_p{period}" for period in periods],
    }
    expanding = {
        axis: daily_surface[columns].expanding(min_periods=60).mean().shift(1)
        for axis, columns in columns_by_axis.items()
    }
    for position in range(60, len(daily_surface), SURFACE_STEP_DAYS):
        timestamp = pd.Timestamp(daily_surface.index[position])
        scope_id = _scope_id(timestamp)
        if scope_id is None:
            continue
        for horizon in SURFACE_HORIZONS_DAYS:
            future_position = position + horizon
            if future_position >= len(daily_surface):
                continue
            future_timestamp = pd.Timestamp(daily_surface.index[future_position])
            if _scope_id(future_timestamp) != scope_id:
                continue
            for axis, columns in columns_by_axis.items():
                current = daily_surface.iloc[position][columns].to_numpy(float)
                future = daily_surface.iloc[future_position][columns].to_numpy(float)
                baseline = expanding[axis].iloc[position][columns].to_numpy(float)
                if not (np.isfinite(current).all() and np.isfinite(future).all() and np.isfinite(baseline).all()):
                    continue
                persistence_mse = float(np.mean((current - future) ** 2))
                baseline_mse = float(np.mean((baseline - future) ** 2))
                rows.append(
                    {
                        "anchor_date": timestamp,
                        "future_date": future_timestamp,
                        "scope_id": scope_id,
                        "axis": axis,
                        "horizon_trading_days": horizon,
                        "cross_period_spearman": _cross_section_rho(current, future),
                        "persistence_mse": persistence_mse,
                        "expanding_mean_mse": baseline_mse,
                        "persistence_mse_improvement": (
                            1.0 - persistence_mse / baseline_mse if baseline_mse > 0.0 else 0.0
                        ),
                    }
                )
    detail = pd.DataFrame(rows)
    aggregate = (
        detail.groupby(["axis", "horizon_trading_days", "scope_id"], as_index=False)
        .agg(
            anchor_count=("anchor_date", "count"),
            median_cross_period_spearman=("cross_period_spearman", "median"),
            mean_persistence_mse=("persistence_mse", "mean"),
            mean_expanding_mean_mse=("expanding_mean_mse", "mean"),
            median_persistence_mse_improvement=("persistence_mse_improvement", "median"),
        )
    )
    aggregate["persistence_beats_mean"] = aggregate["mean_persistence_mse"].lt(aggregate["mean_expanding_mean_mse"])
    aggregate["scope_pass"] = aggregate["median_cross_period_spearman"].ge(SURFACE_MIN_RHO) & aggregate["persistence_beats_mean"]
    axis_results: dict[str, object] = {}
    passing_axes: list[str] = []
    for axis in columns_by_axis:
        primary = aggregate.loc[
            aggregate["axis"].eq(axis)
            & aggregate["horizon_trading_days"].eq(SURFACE_HORIZONS_DAYS[0])
        ]
        passed_scopes = int(primary["scope_pass"].sum())
        passed = passed_scopes >= SURFACE_REQUIRED_SCOPES
        if passed:
            passing_axes.append(axis)
        axis_results[axis] = {
            "passed": passed,
            "passing_scope_count": passed_scopes,
            "required_scope_count": SURFACE_REQUIRED_SCOPES,
        }
    summary = {
        "passed": bool(passing_axes),
        "passing_axes": passing_axes,
        "axis_results": axis_results,
        "verdict": "surface_followability_passed" if passing_axes else "surface_not_causally_followable",
    }
    return detail, aggregate, summary


def ownership_samples(
    daily_surface: pd.DataFrame,
    daily_paths: pd.DataFrame,
    periods: Sequence[int],
    passing_axes: Sequence[str],
) -> pd.DataFrame:
    common = daily_surface.index.intersection(daily_paths.index)
    surface = daily_surface.reindex(common)
    paths = daily_paths.reindex(common)
    rows: list[dict[str, object]] = []
    for position in range(0, len(common), OWNERSHIP_STEP_DAYS):
        future_end = position + OWNERSHIP_STEP_DAYS
        if future_end >= len(common):
            break
        anchor = pd.Timestamp(common[position])
        future_dates = common[position + 1 : future_end + 1]
        for period in periods:
            row: dict[str, object] = {
                "anchor_date": anchor,
                "period_bars": period,
                "future_primary_net_log_return": float(paths.loc[future_dates, f"p{period}"].sum()),
            }
            if "volatility" in passing_axes:
                row["volatility"] = float(surface.at[anchor, f"vol_p{period}"])
            if "edge" in passing_axes:
                row["edge"] = float(surface.at[anchor, f"edge_p{period}"])
            rows.append(row)
    return pd.DataFrame(rows).dropna().reset_index(drop=True)


def _feature_matrix(
    frame: pd.DataFrame,
    passing_axes: Sequence[str],
) -> tuple[np.ndarray, list[str]]:
    log_period = np.log(pd.to_numeric(frame["period_bars"], errors="raise").to_numpy(float))
    values: list[np.ndarray] = [log_period, log_period**2]
    names = ["log_period", "log_period_squared"]
    for axis in passing_axes:
        axis_value = pd.to_numeric(frame[axis], errors="raise").to_numpy(float)
        values.extend([axis_value, log_period * axis_value])
        names.extend([axis, f"log_period_x_{axis}"])
    if set(passing_axes) == {"volatility", "edge"}:
        values.append(
            pd.to_numeric(frame["volatility"], errors="raise").to_numpy(float)
            * pd.to_numeric(frame["edge"], errors="raise").to_numpy(float)
        )
        names.append("volatility_x_edge")
    return np.column_stack(values), names


@dataclass(frozen=True, slots=True)
class RidgeFit:
    mean: np.ndarray
    scale: np.ndarray
    coefficients: np.ndarray
    feature_names: tuple[str, ...]


def fit_ownership_ridge(frame: pd.DataFrame, passing_axes: Sequence[str]) -> RidgeFit:
    x, names = _feature_matrix(frame, passing_axes)
    y = pd.to_numeric(frame["future_primary_net_log_return"], errors="raise").to_numpy(float)
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale == 0.0] = 1.0
    standardized = (x - mean) / scale
    design = np.column_stack([np.ones(len(x)), standardized])
    penalty = np.eye(design.shape[1]) * RIDGE_LAMBDA
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    return RidgeFit(mean=mean, scale=scale, coefficients=coefficients, feature_names=tuple(names))


def predict_ownership(frame: pd.DataFrame, passing_axes: Sequence[str], fit: RidgeFit) -> np.ndarray:
    x, names = _feature_matrix(frame, passing_axes)
    if tuple(names) != fit.feature_names:
        raise ValidationError("V20 ownership feature identity changed")
    design = np.column_stack([np.ones(len(x)), (x - fit.mean) / fit.scale])
    return design @ fit.coefficients


def _route_position(
    panel: pd.DataFrame,
    selections: pd.DataFrame,
    *,
    fallback_period: int,
) -> tuple[pd.Series, pd.Series]:
    anchors = selections.sort_values("anchor_date", kind="mergesort")
    anchor_dates = pd.DatetimeIndex(anchors["anchor_date"])
    anchor_periods = anchors["selected_period_bars"].astype(int).to_numpy()
    chosen: list[int] = []
    for timestamp in panel.index:
        trade_date = timestamp.normalize()
        location = int(anchor_dates.searchsorted(trade_date, side="left") - 1)
        chosen.append(int(anchor_periods[location]) if location >= 0 else fallback_period)
    selected_period = pd.Series(chosen, index=panel.index, dtype=int, name="selected_period_bars")
    desired = pd.Series(0.0, index=panel.index, dtype=float)
    for period in sorted(set(chosen)):
        mask = selected_period.eq(period)
        desired.loc[mask] = panel.loc[mask, desired_column(period)]
    return enforce_t_plus_one(desired), selected_period


def ownership_walk_forward(
    panel: pd.DataFrame,
    samples: pd.DataFrame,
    periods: Sequence[int],
    passing_axes: Sequence[str],
    *,
    anchor_period: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    period_set = {int(period) for period in periods}
    if not period_set or not bool(samples["period_bars"].isin(period_set).all()):
        raise ValidationError("V20 ownership samples contain an unregistered period")
    selection_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    fold_excess: dict[str, float] = {}
    for fold in OWNERSHIP_FOLDS:
        train = samples.loc[
            (samples["anchor_date"] >= fold.train_start)
            & (samples["anchor_date"] < fold.train_end)
        ]
        test = samples.loc[
            (samples["anchor_date"] >= fold.test_start)
            & (samples["anchor_date"] < fold.test_end)
        ].copy()
        if train.empty or test.empty:
            raise ValidationError(f"V20 ownership fold has no rows: {fold.fold_id}")
        fit = fit_ownership_ridge(train, passing_axes)
        test["predicted_future_utility"] = predict_ownership(test, passing_axes, fit)
        selected = (
            test.sort_values(
                ["anchor_date", "predicted_future_utility", "period_bars"],
                ascending=[True, False, True],
                kind="mergesort",
            )
            .groupby("anchor_date", as_index=False)
            .first()[["anchor_date", "period_bars", "predicted_future_utility"]]
            .rename(columns={"period_bars": "selected_period_bars"})
        )
        selected["fold_id"] = fold.fold_id
        selection_rows.extend(selected.to_dict(orient="records"))
        route_position, _ = _route_position(panel, selected, fallback_period=anchor_period)
        scope_mask = (panel.index >= fold.test_start) & (panel.index < fold.test_end)
        for cost in COST_STRESS_BPS:
            dynamic_path = costed_path(route_position, panel["forward_market_log_return"], cost_bps=cost)
            baseline_path = panel[net_column(anchor_period, cost)]
            dynamic_metrics = _path_metrics(dynamic_path.loc[scope_mask], route_position.loc[scope_mask])
            baseline_metrics = _path_metrics(baseline_path.loc[scope_mask], panel.loc[scope_mask, t1_column(anchor_period)])
            excess = float(dynamic_metrics["net_log_return"]) - float(baseline_metrics["net_log_return"])
            metric_rows.append(
                {
                    "fold_id": fold.fold_id,
                    "cost_bps": cost,
                    "dynamic_net_log_return": dynamic_metrics["net_log_return"],
                    "anchor_net_log_return": baseline_metrics["net_log_return"],
                    "dynamic_minus_anchor_net_log_return": excess,
                    "dynamic_annualized_sharpe": dynamic_metrics["annualized_sharpe"],
                    "anchor_annualized_sharpe": baseline_metrics["annualized_sharpe"],
                    "dynamic_max_log_drawdown": dynamic_metrics["max_log_drawdown"],
                    "anchor_max_log_drawdown": baseline_metrics["max_log_drawdown"],
                    "dynamic_turnover_count": dynamic_metrics["turnover_count"],
                    "anchor_turnover_count": baseline_metrics["turnover_count"],
                }
            )
            if cost == PRIMARY_COST_BPS:
                fold_excess[fold.fold_id] = excess
    selections = pd.DataFrame(selection_rows)
    metrics = pd.DataFrame(metric_rows)
    positive_fold_count = sum(value > 0.0 for value in fold_excess.values())
    aggregate_by_cost = metrics.groupby("cost_bps")["dynamic_minus_anchor_net_log_return"].sum().to_dict()
    positive_values = [max(value, 0.0) for value in fold_excess.values()]
    positive_total = sum(positive_values)
    largest_share = max(positive_values) / positive_total if positive_total > 0.0 else 1.0
    minimum_fold = min(fold_excess.values()) if fold_excess else -math.inf
    passed = bool(
        positive_fold_count >= 2
        and all(float(aggregate_by_cost.get(cost, -math.inf)) > 0.0 for cost in COST_STRESS_BPS)
        and minimum_fold >= -0.03
        and largest_share <= 0.70
    )
    summary: dict[str, object] = {
        "passed": passed,
        "positive_primary_cost_fold_count": positive_fold_count,
        "required_positive_fold_count": 2,
        "primary_cost_excess_by_fold": fold_excess,
        "aggregate_excess_by_cost_bps": {str(key): value for key, value in aggregate_by_cost.items()},
        "minimum_primary_cost_fold_excess": minimum_fold,
        "largest_positive_fold_contribution_share": largest_share,
        "selected_periods": sorted(selections["selected_period_bars"].astype(int).unique().tolist()),
        "verdict": "stable_period_ownership_passed" if passed else "surface_does_not_stably_own_iir_period",
    }
    return selections, metrics, summary


def ownership_repeat_audit(
    panel: pd.DataFrame,
    samples: pd.DataFrame,
    passing_axes: Sequence[str],
    *,
    anchor_period: int,
) -> dict[str, object]:
    """Apply one frozen 2009-2017 fit and expose aggregate 2018-2020 only."""

    train = samples.loc[
        (samples["anchor_date"] >= DEVELOPMENT_START)
        & (samples["anchor_date"] < DEVELOPMENT_END)
    ]
    audit = samples.loc[
        (samples["anchor_date"] >= DEVELOPMENT_END)
        & (samples["anchor_date"] < REPEAT_AUDIT_END)
    ].copy()
    if train.empty or audit.empty:
        raise ValidationError("V20 repeat audit lacks train or audit ownership rows")
    fit = fit_ownership_ridge(train, passing_axes)
    audit["predicted_future_utility"] = predict_ownership(audit, passing_axes, fit)
    selected = (
        audit.sort_values(
            ["anchor_date", "predicted_future_utility", "period_bars"],
            ascending=[True, False, True],
            kind="mergesort",
        )
        .groupby("anchor_date", as_index=False)
        .first()[["anchor_date", "period_bars"]]
        .rename(columns={"period_bars": "selected_period_bars"})
    )
    route_position, _ = _route_position(panel, selected, fallback_period=anchor_period)
    mask = (panel.index >= DEVELOPMENT_END) & (panel.index < REPEAT_AUDIT_END)
    metrics: list[dict[str, object]] = []
    for cost in COST_STRESS_BPS:
        dynamic_path = costed_path(route_position, panel["forward_market_log_return"], cost_bps=cost)
        dynamic = _path_metrics(dynamic_path.loc[mask], route_position.loc[mask])
        baseline = _path_metrics(
            panel.loc[mask, net_column(anchor_period, cost)],
            panel.loc[mask, t1_column(anchor_period)],
        )
        metrics.append(
            {
                "cost_bps": cost,
                "dynamic_net_log_return": dynamic["net_log_return"],
                "anchor_net_log_return": baseline["net_log_return"],
                "dynamic_minus_anchor_net_log_return": float(dynamic["net_log_return"])
                - float(baseline["net_log_return"]),
                "dynamic_annualized_sharpe": dynamic["annualized_sharpe"],
                "anchor_annualized_sharpe": baseline["annualized_sharpe"],
                "dynamic_max_log_drawdown": dynamic["max_log_drawdown"],
                "anchor_max_log_drawdown": baseline["max_log_drawdown"],
                "dynamic_turnover_count": dynamic["turnover_count"],
                "anchor_turnover_count": baseline["turnover_count"],
            }
        )
    primary = next(row for row in metrics if row["cost_bps"] == PRIMARY_COST_BPS)
    return {
        "status": "aggregate_repeat_audit_completed",
        "audit_start": str(DEVELOPMENT_END),
        "audit_end_exclusive": str(REPEAT_AUDIT_END),
        "anchor_count": int(selected["anchor_date"].nunique()),
        "selected_period_counts": {
            str(int(period)): int(count)
            for period, count in selected["selected_period_bars"].value_counts().sort_index().items()
        },
        "metrics": metrics,
        "primary_cost_excess_positive": float(primary["dynamic_minus_anchor_net_log_return"]) > 0.0,
        "timestamp_level_rows_exposed": 0,
        "post_2020_numeric_rows_parsed": 0,
    }


__all__ = [
    "CODE_VERSION", "COST_STRESS_BPS", "DEVELOPMENT_END", "DEVELOPMENT_SCOPES",
    "DEVELOPMENT_START", "OWNERSHIP_FOLDS", "PERIOD_CANDIDATES", "PRIMARY_COST_BPS",
    "PREREGISTRATION_SHA256", "Q_VALUE", "REPEAT_AUDIT_END", "SCHEMA_ID", "SEALED_START",
    "WARMUP_START", "assert_preregistration", "build_daily_surface", "build_period_panel",
    "competitive_envelope", "costed_path", "desired_column", "enforce_t_plus_one",
    "net_column", "ownership_repeat_audit", "ownership_samples", "ownership_walk_forward", "select_robust_anchor",
    "static_period_summary", "surface_followability", "t1_column",
]
