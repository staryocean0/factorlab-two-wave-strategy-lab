# pyright: reportAny=false, reportArgumentType=false
# pyright: reportAssignmentType=false, reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportOperatorIssue=false, reportReturnType=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Causal stage-level ownership between P13 and P36 of one IIR tool.

The default owner is P13.  P36 may own the parameter for a monthly review
interval only when the extra P13-vs-P36 band has elevated energy but does not
produce a commensurate excess of independent position cycles.  The state is
formed exclusively from shifted, past-only distributions and is activated on
the trading day after a month-end review.

This is a research surface.  It grants neither production authority nor
cross-tool routing authority.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.research.causal_filter_iir_competitive_period_temporal_surface_v20 import (
    build_period_panel,
    costed_path,
    enforce_t_plus_one,
    net_column,
)

SCHEMA_ID: Final[str] = "market_state_causal_filter_iir_p13_slow_ownership_regime@3.0"
CODE_VERSION: Final[str] = "causal-filter-iir-p13-slow-ownership-regime-20260811-v3"
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[4]
PREREGISTRATION_PATH: Final[Path] = PROJECT_ROOT / (
    "docs/ops/evidence/"
    "market_state_causal_filter_iir_p13_slow_ownership_regime_"
    "v3_preregistration_20260811.json"
)
PREREGISTRATION_SHA256: Final[str] = (
    "1bcc8889ff80f6186a5f89e87e3829833a323240d0e91ec32d649f9c9c4c0d38"
)

FAST_PERIOD_BARS: Final[int] = 13
SLOW_PERIOD_BARS: Final[int] = 36
Q_VALUE: Final[float] = 0.8
BARS_PER_SESSION: Final[int] = 4
REFERENCE_HISTORY_DAYS: Final[int] = 625
REFERENCE_MINIMUM_DAYS: Final[int] = 312
ENERGY_WINDOW_DAYS: Final[int] = 60
TURNOVER_WINDOW_DAYS: Final[int] = 80
ENERGY_QUANTILE: Final[float] = 0.65
TURNOVER_QUANTILE: Final[float] = 0.15
EVIDENCE_AGGREGATION_DAYS: Final[int] = 40
MINIMUM_EVIDENCE_SHARE: Final[float] = 0.20
PRIMARY_COST_BPS: Final[float] = 7.0
COST_STRESS_BPS: Final[tuple[float, ...]] = (5.0, 7.0, 10.0)
ANNUALIZATION_BARS: Final[float] = 960.0
DEVELOPMENT_START: Final[pd.Timestamp] = pd.Timestamp("2009-01-01")
DEVELOPMENT_END: Final[pd.Timestamp] = pd.Timestamp("2018-01-01")
REPEAT_AUDIT_END: Final[pd.Timestamp] = pd.Timestamp("2021-01-01")
SEALED_START: Final[pd.Timestamp] = pd.Timestamp("2021-01-01")
TIMING_NULL_DRAWS: Final[int] = 512
TIMING_NULL_SEED: Final[int] = 20_260_814


@dataclass(frozen=True, slots=True)
class EvaluationScope:
    scope_id: str
    start: pd.Timestamp
    end: pd.Timestamp


DEVELOPMENT_SCOPES: Final[tuple[EvaluationScope, ...]] = (
    EvaluationScope("wf_2011_2012", pd.Timestamp("2011-01-01"), pd.Timestamp("2013-01-01")),
    EvaluationScope("wf_2013_2014", pd.Timestamp("2013-01-01"), pd.Timestamp("2015-01-01")),
    EvaluationScope("wf_2015_2016", pd.Timestamp("2015-01-01"), pd.Timestamp("2017-01-01")),
    EvaluationScope("wf_2017", pd.Timestamp("2017-01-01"), DEVELOPMENT_END),
)
REPEAT_AUDIT_SCOPE: Final[EvaluationScope] = EvaluationScope(
    "consumed_repeat_audit_2018_2020",
    DEVELOPMENT_END,
    REPEAT_AUDIT_END,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_preregistration() -> dict[str, object]:
    """Fail closed if the frozen experiment contract changes."""

    if not PREREGISTRATION_PATH.is_file():
        raise ValidationError(f"缺少P13慢周期所有权预注册: {PREREGISTRATION_PATH}")
    actual = _sha256(PREREGISTRATION_PATH)
    if actual != PREREGISTRATION_SHA256:
        raise ValidationError(
            "P13慢周期所有权预注册摘要变化: "
            f"expected={PREREGISTRATION_SHA256}, actual={actual}"
        )
    payload = json.loads(PREREGISTRATION_PATH.read_text(encoding="utf-8"))
    if payload.get("research_id") != "iir_p13_slow_ownership_regime_v3":
        raise ValidationError("P13慢周期所有权研究身份变化")
    return payload


def physical_contract() -> dict[str, object]:
    return {
        "fast_period_bars": FAST_PERIOD_BARS,
        "slow_period_bars": SLOW_PERIOD_BARS,
        "fast_period_sessions": FAST_PERIOD_BARS / BARS_PER_SESSION,
        "slow_period_sessions": SLOW_PERIOD_BARS / BARS_PER_SESSION,
        "q": Q_VALUE,
        "component_semantics": "delta_component_direction",
        "reference_history_days": REFERENCE_HISTORY_DAYS,
        "reference_minimum_days": REFERENCE_MINIMUM_DAYS,
        "energy_window_days": ENERGY_WINDOW_DAYS,
        "turnover_window_days": TURNOVER_WINDOW_DAYS,
        "energy_quantile": ENERGY_QUANTILE,
        "turnover_quantile": TURNOVER_QUANTILE,
        "evidence_aggregation_days": EVIDENCE_AGGREGATION_DAYS,
        "minimum_evidence_share": MINIMUM_EVIDENCE_SHARE,
        "review_clock": "calendar_month_end",
        "activation_delay_days": 1,
        "true_t_plus_one": True,
        "default_owner": "p13",
        "conditional_owner": "p36",
        "production_authority": False,
    }


def _validate_bar_boundary(strategy_bars: pd.DataFrame, *, end: pd.Timestamp) -> None:
    if "timestamp" not in strategy_bars.columns:
        raise ValidationError("P13慢周期所有权输入缺少timestamp")
    timestamps = pd.to_datetime(strategy_bars["timestamp"], errors="raise")
    if bool(timestamps.ge(end).any()):
        raise ValidationError(f"输入越过允许数值边界: end={end.date()}")


def _causal_quantile(
    series: pd.Series,
    *,
    history_days: int,
    minimum_days: int,
    quantile: float,
) -> pd.Series:
    return series.shift(1).rolling(
        history_days,
        min_periods=minimum_days,
    ).quantile(quantile)


def _daily_base(panel: pd.DataFrame, components: pd.DataFrame) -> pd.DataFrame:
    index = panel.index
    dates = index.normalize()
    fast_component = pd.to_numeric(components["p13_component"], errors="raise")
    slow_component = pd.to_numeric(components["p36_component"], errors="raise")
    residual = fast_component - slow_component
    intraday = pd.DataFrame(index=index)
    intraday["date"] = dates
    intraday["slow_energy"] = np.square(slow_component.diff())
    intraday["residual_energy"] = np.square(residual.diff())
    intraday["p13_turn"] = (
        pd.to_numeric(panel["p13_desired_position"], errors="raise")
        .diff().abs().fillna(0.0)
    )
    intraday["p36_turn"] = (
        pd.to_numeric(panel["p36_desired_position"], errors="raise")
        .diff().abs().fillna(0.0)
    )
    return intraday.groupby("date").agg(
        slow_energy=("slow_energy", "sum"),
        residual_energy=("residual_energy", "sum"),
        p13_turns=("p13_turn", "sum"),
        p36_turns=("p36_turn", "sum"),
    )


def build_daily_context(
    panel: pd.DataFrame,
    components: pd.DataFrame,
    *,
    reference_history_days: int = REFERENCE_HISTORY_DAYS,
    reference_minimum_days: int | None = None,
    energy_window_days: int = ENERGY_WINDOW_DAYS,
    turnover_window_days: int = TURNOVER_WINDOW_DAYS,
    energy_quantile: float = ENERGY_QUANTILE,
    turnover_quantile: float = TURNOVER_QUANTILE,
    evidence_aggregation_days: int = EVIDENCE_AGGREGATION_DAYS,
    minimum_evidence_share: float = MINIMUM_EVIDENCE_SHARE,
) -> pd.DataFrame:
    """Build shifted past-only ownership evidence and the monthly state."""

    minimum = (
        max(250, reference_history_days // 2)
        if reference_minimum_days is None
        else int(reference_minimum_days)
    )
    daily = _daily_base(panel, components)
    residual_energy = daily["residual_energy"].rolling(
        energy_window_days, min_periods=energy_window_days
    ).sum()
    slow_energy = daily["slow_energy"].rolling(
        energy_window_days, min_periods=energy_window_days
    ).sum()
    daily["residual_energy_share"] = residual_energy.div(
        (residual_energy + slow_energy).replace(0.0, np.nan)
    )
    daily["turnover_excess"] = (
        daily["p13_turns"].rolling(
            turnover_window_days, min_periods=turnover_window_days
        ).sum()
        - daily["p36_turns"].rolling(
            turnover_window_days, min_periods=turnover_window_days
        ).sum()
    ).div(float(turnover_window_days))
    daily["energy_cut"] = _causal_quantile(
        daily["residual_energy_share"],
        history_days=reference_history_days,
        minimum_days=minimum,
        quantile=energy_quantile,
    )
    daily["turnover_cut"] = _causal_quantile(
        daily["turnover_excess"],
        history_days=reference_history_days,
        minimum_days=minimum,
        quantile=turnover_quantile,
    )
    daily["energy_high"] = (
        daily["energy_cut"].notna()
        & daily["residual_energy_share"].ge(daily["energy_cut"])
    )
    daily["turnover_low"] = (
        daily["turnover_cut"].notna()
        & daily["turnover_excess"].le(daily["turnover_cut"])
    )
    daily["daily_ownership_evidence"] = (
        daily["energy_high"] & daily["turnover_low"]
    )
    daily["evidence_share"] = daily["daily_ownership_evidence"].astype(float).rolling(
        evidence_aggregation_days,
        min_periods=evidence_aggregation_days,
    ).mean()
    month = daily.index.to_period("M")
    review = daily.groupby(month)["evidence_share"].last().ge(minimum_evidence_share)
    review_dates = daily.groupby(month).apply(lambda x: x.index[-1], include_groups=False)
    sampled = pd.Series(
        review.to_numpy(bool),
        index=pd.DatetimeIndex(review_dates.to_numpy()),
        dtype=bool,
    )
    daily["p36_owner_state"] = sampled.reindex(daily.index).ffill().eq(True)
    return daily


def expand_owner_to_bars(
    owner_daily: pd.Series,
    bar_index: pd.DatetimeIndex,
    *,
    activation_delay_days: int = 1,
) -> pd.Series:
    """Activate a close-observed daily state only after the requested delay."""

    active = owner_daily.shift(activation_delay_days, fill_value=False)
    return pd.Series(
        active.reindex(bar_index.normalize(), fill_value=False).to_numpy(bool),
        index=bar_index,
        dtype=bool,
        name="p36_owner_active",
    )


def build_route(
    panel: pd.DataFrame,
    daily_context: pd.DataFrame,
    *,
    activation_delay_days: int = 1,
) -> pd.DataFrame:
    """Build one desired path and apply the T+1 state machine exactly once."""

    owner = expand_owner_to_bars(
        daily_context["p36_owner_state"],
        panel.index,
        activation_delay_days=activation_delay_days,
    )
    desired = pd.to_numeric(panel["p13_desired_position"], errors="raise").copy()
    desired.loc[owner] = panel.loc[owner, "p36_desired_position"]
    actual = enforce_t_plus_one(desired)
    result = pd.DataFrame(
        {
            "p36_owner_active": owner,
            "route_desired_position": desired,
            "route_t1_position": actual,
        },
        index=panel.index,
    )
    for cost in COST_STRESS_BPS:
        result[f"route_net_{cost:g}bps"] = costed_path(
            actual,
            panel["forward_market_log_return"],
            cost_bps=cost,
        )
    result["route_gross"] = costed_path(
        actual,
        panel["forward_market_log_return"],
        cost_bps=0.0,
    )
    return result


def _scope_mask(index: pd.DatetimeIndex, scope: EvaluationScope) -> pd.Series:
    return pd.Series((index >= scope.start) & (index < scope.end), index=index)


def path_metrics(
    path: pd.Series,
    position: pd.Series,
    mask: pd.Series,
) -> dict[str, float | int]:
    local = pd.to_numeric(path.loc[mask], errors="raise").dropna()
    pos = pd.to_numeric(position.reindex(local.index), errors="raise").fillna(0.0)
    equity = local.cumsum()
    drawdown = equity - equity.cummax()
    standard_deviation = float(local.std(ddof=0))
    changes = pos.diff().abs().fillna(pos.abs())
    entries = pos.diff().fillna(pos).gt(0.0)
    holds: list[int] = []
    run = 0
    for held in pos.gt(0.0).to_numpy(bool):
        if held:
            run += 1
        elif run:
            holds.append(run)
            run = 0
    if run:
        holds.append(run)
    return {
        "bar_count": int(len(local)),
        "net_log_return": float(local.sum()),
        "annualized_sharpe": (
            float(local.mean() / standard_deviation * math.sqrt(ANNUALIZATION_BARS))
            if standard_deviation > 0.0
            else 0.0
        ),
        "max_log_drawdown": float(drawdown.min()) if len(drawdown) else 0.0,
        "turnover_count": float(changes.sum()),
        "trade_count": int(entries.sum()),
        "average_hold_bars": float(np.mean(holds)) if holds else 0.0,
    }


def evaluate_scope(
    panel: pd.DataFrame,
    route: pd.DataFrame,
    scope: EvaluationScope,
) -> dict[str, object]:
    mask = _scope_mask(panel.index, scope)
    result: dict[str, object] = {
        "scope_id": scope.scope_id,
        "route": path_metrics(
            route[f"route_net_{PRIMARY_COST_BPS:g}bps"],
            route["route_t1_position"],
            mask,
        ),
        "static_p13": path_metrics(
            panel[net_column(FAST_PERIOD_BARS, PRIMARY_COST_BPS)],
            panel["p13_t1_position"],
            mask,
        ),
        "static_p36": path_metrics(
            panel[net_column(SLOW_PERIOD_BARS, PRIMARY_COST_BPS)],
            panel["p36_t1_position"],
            mask,
        ),
        "state_occupancy": float(route.loc[mask, "p36_owner_active"].mean()),
    }
    excess_by_cost = {}
    for cost in COST_STRESS_BPS:
        excess_by_cost[f"{cost:g}bps"] = float(
            (
                route.loc[mask, f"route_net_{cost:g}bps"]
                - panel.loc[mask, net_column(FAST_PERIOD_BARS, cost)]
            ).sum()
        )
    result["route_minus_p13_by_cost"] = excess_by_cost
    result["route_minus_p13_gross"] = float(
        (
            route.loc[mask, "route_gross"]
            - costed_path(
                panel["p13_t1_position"],
                panel["forward_market_log_return"],
                cost_bps=0.0,
            ).loc[mask]
        ).sum()
    )
    return result


def build_context(
    strategy_bars: pd.DataFrame,
    *,
    allowed_end: pd.Timestamp,
    activation_delay_days: int = 1,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    _validate_bar_boundary(strategy_bars, end=allowed_end)
    panel, components = build_period_panel(strategy_bars, periods=(13, 36))
    daily = build_daily_context(panel, components)
    route = build_route(panel, daily, activation_delay_days=activation_delay_days)
    return panel, components, daily, route


def development_fold_metrics(
    panel: pd.DataFrame,
    route: pd.DataFrame,
) -> list[dict[str, object]]:
    return [evaluate_scope(panel, route, scope) for scope in DEVELOPMENT_SCOPES]


def development_episode_ledger(
    panel: pd.DataFrame,
    daily: pd.DataFrame,
    route: pd.DataFrame,
) -> pd.DataFrame:
    effect = (
        route[f"route_net_{PRIMARY_COST_BPS:g}bps"]
        - panel[net_column(FAST_PERIOD_BARS, PRIMARY_COST_BPS)]
    ).groupby(panel.index.normalize()).sum()
    state = daily["p36_owner_state"].fillna(False)
    rows: list[dict[str, object]] = []
    start: int | None = None
    values = state.to_numpy(bool)
    for index, active in enumerate(values):
        if active and start is None:
            start = index
        last = index == len(values) - 1
        if start is not None and ((not active) or last):
            stop = index if not active else index + 1
            dates = state.index[start:stop]
            rows.append(
                {
                    "episode_id": f"slow_owner_{len(rows) + 1:02d}",
                    "start": dates[0],
                    "end": dates[-1],
                    "days": int(len(dates)),
                    "route_minus_p13_7bps": float(
                        effect.reindex(dates, fill_value=0.0).sum()
                    ),
                }
            )
            start = None
    return pd.DataFrame(rows)


def timing_circular_shift_null(
    panel: pd.DataFrame,
    daily: pd.DataFrame,
    *,
    draws: int = TIMING_NULL_DRAWS,
) -> dict[str, float | int]:
    observed_route = build_route(panel, daily)
    observed = sum(
        float(row["route_minus_p13_by_cost"]["7bps"])
        for row in development_fold_metrics(panel, observed_route)
    )
    state = daily["p36_owner_state"].to_numpy(bool)
    rng = np.random.default_rng(TIMING_NULL_SEED)
    values = []
    for shift in rng.integers(20, len(state) - 20, size=draws):
        shifted_daily = daily.copy()
        shifted_daily["p36_owner_state"] = np.roll(state, int(shift))
        shifted_route = build_route(panel, shifted_daily)
        values.append(
            sum(
                float(row["route_minus_p13_by_cost"]["7bps"])
                for row in development_fold_metrics(panel, shifted_route)
            )
        )
    array = np.asarray(values, dtype=float)
    return {
        "draws": int(draws),
        "observed_total_excess_7bps": float(observed),
        "null_mean": float(array.mean()),
        "null_q95": float(np.quantile(array, 0.95)),
        "empirical_p_value": float((1 + np.sum(array >= observed)) / (draws + 1)),
    }


def consumed_repeat_audit_receipt(
    panel: pd.DataFrame,
    route: pd.DataFrame,
) -> dict[str, object]:
    """Return only the preregistered aggregate fields for 2018--2020."""

    result = evaluate_scope(panel, route, REPEAT_AUDIT_SCOPE)
    excess = result["route_minus_p13_by_cost"]
    route_metrics = result["route"]
    p13_metrics = result["static_p13"]
    passed = (
        all(float(excess[f"{cost:g}bps"]) > 0.0 for cost in COST_STRESS_BPS)
        and float(route_metrics["annualized_sharpe"])
        >= float(p13_metrics["annualized_sharpe"])
        and float(result["state_occupancy"]) > 0.0
    )
    return {
        "schema_id": "market_state_timing_consumed_repeat_audit_receipt@1.0",
        "research_id": "iir_p13_slow_ownership_regime_v3",
        "scope_id": REPEAT_AUDIT_SCOPE.scope_id,
        "bar_count": int(route_metrics["bar_count"]),
        "route_metrics": route_metrics,
        "static_p13_metrics": p13_metrics,
        "static_p36_metrics": result["static_p36"],
        "route_minus_p13_by_cost": excess,
        "state_occupancy": float(result["state_occupancy"]),
        "decision_boolean": bool(passed),
        "fresh_holdout_authority": False,
        "production_authority": False,
    }
