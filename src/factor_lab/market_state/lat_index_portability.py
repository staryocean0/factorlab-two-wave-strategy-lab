"""Annual-session primitives for LAT portability across market indices.

The module evaluates one preregistered seamless LAT family.  It deliberately
does not batch annual scientific decisions or implement the later six-bucket
branch; each caller opens one natural-year session and seals one receipt.
"""

from __future__ import annotations

import itertools
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from factor_lab.strategy.services.risk_off_v58_frequency_bollinger import (
    causal_lowpass,
    causal_thickness_component,
)

BARS_PER_DAY = 14
SESSION_YEARS = tuple(range(2009, 2021))
CENTRE_DAYS = (2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0)
FILTER_ORDERS = (1, 2)
RMS_RATIOS = (0.5, 0.75, 1.0)
SMOOTHING_RATIOS = (0.0625, 0.125, 0.25)
WIDTH_MULTIPLIERS = (0.5, 1.0, 1.5, 2.0)
ANNUAL_MATERIALITY = 0.001
QUARTERLY_MATERIALITY = 0.00025
ENTRY_COST_RATE = 0.0001
EXIT_COST_RATE = 0.0006

Direction = Literal["long", "short"]


@dataclass(frozen=True, slots=True)
class LatCandidate:
    centre_period_days: float
    centre_period_bars: int
    filter_order: int
    rms_window_ratio: float
    rms_window_bars: int
    smoothing_ratio: float
    smoothing_half_life_bars: float
    width_multiplier: float

    @property
    def candidate_id(self) -> str:
        def token(value: float) -> str:
            return f"{value:g}".replace(".", "p")

        return (
            f"lat_days{token(self.centre_period_days)}"
            f"_P{self.centre_period_bars}_N{self.filter_order}"
            f"_Wr{token(self.rms_window_ratio)}_W{self.rms_window_bars}"
            f"_HLr{token(self.smoothing_ratio)}"
            f"_HL{token(self.smoothing_half_life_bars)}"
            f"_k{token(self.width_multiplier)}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "candidate_id": self.candidate_id}


def candidate_family(bars_per_day: int = BARS_PER_DAY) -> tuple[LatCandidate, ...]:
    candidates: list[LatCandidate] = []
    for days, order, rms_ratio, smoothing_ratio, k in itertools.product(
        CENTRE_DAYS,
        FILTER_ORDERS,
        RMS_RATIOS,
        SMOOTHING_RATIOS,
        WIDTH_MULTIPLIERS,
    ):
        period = int(round(float(days) * int(bars_per_day)))
        rms_window = max(16, int(round(rms_ratio * period)))
        half_life = max(2.0, smoothing_ratio * period)
        candidates.append(
            LatCandidate(
                centre_period_days=float(days),
                centre_period_bars=period,
                filter_order=int(order),
                rms_window_ratio=float(rms_ratio),
                rms_window_bars=rms_window,
                smoothing_ratio=float(smoothing_ratio),
                smoothing_half_life_bars=float(half_life),
                width_multiplier=float(k),
            )
        )
    return tuple(candidates)


def common_root_candidate(direction: Direction) -> LatCandidate:
    return LatCandidate(
        centre_period_days=4.0,
        centre_period_bars=56,
        filter_order=1,
        rms_window_ratio=0.75,
        rms_window_bars=42,
        smoothing_ratio=0.125,
        smoothing_half_life_bars=7.0,
        width_multiplier=1.5 if direction == "long" else 1.0,
    )


def fold_direction_state(
    *,
    log_close: pd.Series,
    middle: pd.Series,
    width: pd.Series,
    valid: pd.Series,
    direction: Direction,
) -> pd.Series:
    close_values = log_close.to_numpy(float)
    middle_values = middle.to_numpy(float)
    width_values = width.to_numpy(float)
    valid_values = valid.to_numpy(bool)
    state = np.zeros(len(log_close), dtype=bool)
    holding = False
    for location in range(len(log_close)):
        if not valid_values[location]:
            holding = False
        elif direction == "long":
            if not holding and close_values[location] > middle_values[location] + width_values[location]:
                holding = True
            elif holding and close_values[location] < middle_values[location]:
                holding = False
        else:
            if not holding and close_values[location] < middle_values[location] - width_values[location]:
                holding = True
            elif holding and close_values[location] > middle_values[location]:
                holding = False
        state[location] = holding
    return pd.Series(state, index=log_close.index, dtype=bool)


def signed_position(decision: pd.Series, *, direction: Direction) -> pd.Series:
    delayed = decision.astype(float).shift(1, fill_value=0.0)
    return delayed if direction == "long" else -delayed


def evaluate_open_fill_path(
    *,
    decision: pd.Series,
    raw_open: pd.Series,
    direction: Direction,
    entry_cost_rate: float = ENTRY_COST_RATE,
    exit_cost_rate: float = EXIT_COST_RATE,
) -> pd.Series:
    if not decision.index.equals(raw_open.index):
        raise ValueError("decision and raw_open indices must match")
    if bool(pd.to_numeric(raw_open, errors="coerce").le(0.0).any()):
        raise ValueError("raw fill opens must be positive")
    position = signed_position(decision, direction=direction)
    forward = np.log(raw_open.shift(-1) / raw_open)
    absolute = position.abs()
    change = absolute.diff().fillna(absolute)
    cost = change.clip(lower=0.0) * float(entry_cost_rate)
    cost += (-change.clip(upper=0.0)) * float(exit_cost_rate)
    path = position * forward - cost
    return pd.Series(path, index=decision.index, dtype=float).fillna(0.0)


def attribute_trade_segments(path: pd.DataFrame) -> list[dict[str, Any]]:
    """Allocate every annual bar-ledger return to an auditable trade segment.

    A policy can enter a year flat while the first in-year bar books the exit
    cost of a position closed by the prior year's final decision.  That cost is
    a real part of the annual account but has no in-year active-position bar.
    Preserve it as a carry-in exit event instead of silently dropping it.
    """

    required = {"timestamp", "position", "bar_net"}
    missing = required - set(path.columns)
    if missing:
        raise ValueError(f"trade attribution path missing columns: {sorted(missing)}")
    active = path["position"].abs().to_numpy(float) > 0.5
    bar_net = pd.to_numeric(path["bar_net"], errors="raise").to_numpy(float)
    trades: list[dict[str, Any]] = []
    start: int | None = None
    for location, is_active in enumerate(active):
        if is_active and start is None:
            start = location
        if start is not None and (not is_active or location == len(active) - 1):
            end = location
            segment = path.iloc[start : end + 1]
            trades.append(
                {
                    "entry_timestamp": str(segment["timestamp"].iloc[0]),
                    "exit_timestamp": str(segment["timestamp"].iloc[-1]),
                    "bars_held": int(active[start : end + 1].sum()),
                    "net_log_return": float(segment["bar_net"].sum()),
                    "attribution_type": (
                        "open_at_year_end"
                        if is_active and location == len(active) - 1
                        else "round_trip"
                    ),
                }
            )
            start = None
        elif start is None and not is_active and not np.isclose(bar_net[location], 0.0):
            timestamp = str(path["timestamp"].iloc[location])
            trades.append(
                {
                    "entry_timestamp": timestamp,
                    "exit_timestamp": timestamp,
                    "bars_held": 0,
                    "net_log_return": float(bar_net[location]),
                    "attribution_type": "carry_in_exit",
                }
            )
    allocated_net = float(sum(float(item["net_log_return"]) for item in trades))
    path_net = float(bar_net.sum())
    if not np.isclose(allocated_net, path_net, atol=1e-12):
        raise RuntimeError(
            f"trade attribution does not reconcile: trades={allocated_net}, path={path_net}"
        )
    return trades


def performance_metrics(path: pd.Series) -> dict[str, float | int]:
    clean = pd.to_numeric(path, errors="coerce").fillna(0.0).astype(float)
    if clean.empty:
        return {
            "net_log_return": 0.0,
            "cagr": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "bar_count": 0,
        }
    years = max(1.0, (clean.index[-1] - clean.index[0]).days / 365.25)
    net = float(clean.sum())
    standard_deviation = float(clean.std(ddof=1))
    sharpe = 0.0
    if standard_deviation > 0.0:
        sharpe = float(clean.mean() / standard_deviation * math.sqrt(BARS_PER_DAY * 244.0))
    cumulative = clean.cumsum()
    drawdown = cumulative - cumulative.cummax()
    return {
        "net_log_return": net,
        "cagr": float(math.exp(net / years) - 1.0),
        "sharpe": sharpe,
        "max_drawdown": float(drawdown.min()),
        "bar_count": int(len(clean)),
    }


def period_sums(path: pd.Series) -> tuple[dict[str, float], dict[str, float]]:
    clean = pd.to_numeric(path, errors="coerce").fillna(0.0).astype(float)
    yearly = {
        str(int(year)): float(values.sum())
        for year, values in clean.groupby(clean.index.year)
    }
    quarter_index = clean.index
    if quarter_index.tz is not None:
        quarter_index = quarter_index.tz_localize(None)
    quarter_keys = quarter_index.to_period("Q")
    quarterly = {
        str(period): float(values.sum())
        for period, values in clean.groupby(quarter_keys)
    }
    return yearly, quarterly


def distribution_gate(
    candidate: Mapping[str, float],
    root: Mapping[str, float],
    *,
    materiality: float,
    minimum_periods: int,
    minimum_years: int = 1,
) -> dict[str, Any]:
    keys = sorted(set(candidate) & set(root))
    deltas = {key: float(candidate[key]) - float(root[key]) for key in keys}
    affected = {key: value for key, value in deltas.items() if abs(value) >= materiality}
    values = list(affected.values())
    positive = sum(value > 0.0 for value in values)
    years = {key[:4] for key in affected}
    enough = len(values) >= minimum_periods and len(years) >= minimum_years
    positive_share = positive / len(values) if values else 0.0
    median = float(np.median(values)) if values else 0.0
    total = float(sum(values))
    return {
        "affected_count": len(values),
        "affected_year_count": len(years),
        "positive_count": positive,
        "positive_share": positive_share,
        "median_delta": median,
        "total_delta": total,
        "enough_periods": enough,
        "passed": bool(
            enough and positive_share >= 0.60 and median >= 0.0 and total > 0.0
        ),
        "deltas": deltas,
    }


def evaluate_family(
    frame: pd.DataFrame,
    *,
    direction: Direction,
    session_year: int,
    development_start_year: int = 2009,
) -> list[dict[str, Any]]:
    required = {"timestamp", "close", "open", "trading_day"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing bars columns: {sorted(missing)}")
    ordered = frame.copy()
    ordered["timestamp"] = pd.to_datetime(ordered["timestamp"], errors="raise")
    ordered = ordered.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    index = pd.DatetimeIndex(ordered["timestamp"])
    close = pd.Series(pd.to_numeric(ordered["close"], errors="raise").to_numpy(float), index=index)
    raw_open = pd.Series(pd.to_numeric(ordered["open"], errors="raise").to_numpy(float), index=index)
    log_close = pd.Series(np.log(close.to_numpy(float)), index=index)
    cumulative_mask = (index.year >= int(development_start_year)) & (
        index.year <= int(session_year)
    )
    current_mask = index.year == int(session_year)
    if not bool(current_mask.any()):
        raise ValueError(f"no observations for session year {session_year}")

    family = candidate_family(BARS_PER_DAY)
    middle_cache: dict[tuple[int, int], pd.Series] = {}
    component_cache: dict[tuple[int, int], pd.Series] = {}
    width_cache: dict[tuple[int, int, int, float], pd.Series] = {}
    results: list[dict[str, Any]] = []

    for candidate in family:
        filter_key = (candidate.centre_period_bars, candidate.filter_order)
        if filter_key not in middle_cache:
            middle_cache[filter_key] = causal_lowpass(
                log_close,
                candidate.centre_period_bars,
                candidate.filter_order,
            )
            component_cache[filter_key] = causal_thickness_component(
                log_close,
                period_bars=candidate.centre_period_bars,
                source="bandpass",
                order=candidate.filter_order,
                band_upper_frequency_ratio=2.0,
            )
        width_key = (
            candidate.centre_period_bars,
            candidate.filter_order,
            candidate.rms_window_bars,
            candidate.smoothing_half_life_bars,
        )
        if width_key not in width_cache:
            raw_rms = (
                component_cache[filter_key]
                .pow(2)
                .rolling(
                    candidate.rms_window_bars,
                    min_periods=candidate.rms_window_bars,
                )
                .mean()
                .pow(0.5)
            )
            width_cache[width_key] = raw_rms.ewm(
                halflife=candidate.smoothing_half_life_bars,
                adjust=False,
            ).mean()
        middle = middle_cache[filter_key]
        width = width_cache[width_key] * candidate.width_multiplier
        warmup = max(candidate.centre_period_bars * 2, candidate.rms_window_bars)
        valid = (
            pd.Series(np.arange(len(index)) >= warmup, index=index)
            & middle.notna()
            & width.notna()
        )
        decision = fold_direction_state(
            log_close=log_close,
            middle=middle,
            width=width,
            valid=valid,
            direction=direction,
        )
        path = evaluate_open_fill_path(
            decision=decision,
            raw_open=raw_open,
            direction=direction,
        )
        cumulative_path = path.loc[cumulative_mask]
        yearly, quarterly = period_sums(cumulative_path)
        position = signed_position(decision, direction=direction)
        changes = position.abs().diff().fillna(position.abs())
        results.append(
            {
                "candidate": candidate.to_dict(),
                "metrics": performance_metrics(cumulative_path),
                "current_year_metrics": performance_metrics(path.loc[current_mask]),
                "yearly": yearly,
                "quarterly": quarterly,
                "trade_count": int((changes.loc[cumulative_mask] > 0.0).sum()),
            }
        )
    return results


def decision_for_candidate(
    frame: pd.DataFrame,
    *,
    candidate: LatCandidate,
    direction: Direction,
) -> pd.Series:
    ordered = frame.copy()
    ordered["timestamp"] = pd.to_datetime(ordered["timestamp"], errors="raise")
    ordered = ordered.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    index = pd.DatetimeIndex(ordered["timestamp"])
    close = pd.Series(pd.to_numeric(ordered["close"], errors="raise").to_numpy(float), index=index)
    log_close = pd.Series(np.log(close.to_numpy(float)), index=index)
    middle = causal_lowpass(
        log_close,
        candidate.centre_period_bars,
        candidate.filter_order,
    )
    component = causal_thickness_component(
        log_close,
        period_bars=candidate.centre_period_bars,
        source="bandpass",
        order=candidate.filter_order,
        band_upper_frequency_ratio=2.0,
    )
    raw_rms = (
        component.pow(2)
        .rolling(candidate.rms_window_bars, min_periods=candidate.rms_window_bars)
        .mean()
        .pow(0.5)
    )
    width = raw_rms.ewm(
        halflife=candidate.smoothing_half_life_bars,
        adjust=False,
    ).mean() * candidate.width_multiplier
    warmup = max(candidate.centre_period_bars * 2, candidate.rms_window_bars)
    valid = (
        pd.Series(np.arange(len(index)) >= warmup, index=index)
        & middle.notna()
        & width.notna()
    )
    return fold_direction_state(
        log_close=log_close,
        middle=middle,
        width=width,
        valid=valid,
        direction=direction,
    )

def rails_for_candidate(
    frame: pd.DataFrame,
    *,
    candidate: LatCandidate,
) -> pd.DataFrame:
    ordered = frame.copy()
    ordered["timestamp"] = pd.to_datetime(ordered["timestamp"], errors="raise")
    ordered = ordered.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    index = pd.DatetimeIndex(ordered["timestamp"])
    close = pd.Series(pd.to_numeric(ordered["close"], errors="raise").to_numpy(float), index=index)
    log_close = pd.Series(np.log(close.to_numpy(float)), index=index)
    middle = causal_lowpass(
        log_close,
        candidate.centre_period_bars,
        candidate.filter_order,
    )
    component = causal_thickness_component(
        log_close,
        period_bars=candidate.centre_period_bars,
        source="bandpass",
        order=candidate.filter_order,
        band_upper_frequency_ratio=2.0,
    )
    raw_rms = (
        component.pow(2)
        .rolling(candidate.rms_window_bars, min_periods=candidate.rms_window_bars)
        .mean()
        .pow(0.5)
    )
    width = raw_rms.ewm(
        halflife=candidate.smoothing_half_life_bars,
        adjust=False,
    ).mean() * candidate.width_multiplier
    return pd.DataFrame({"close": close, "middle": np.exp(middle), "width_log": width}, index=index)


def _candidate_lookup(results: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {
        str(item["candidate"]["candidate_id"]): item
        for item in results
    }


def independent_distribution_gates_pass(
    annual_gate: Mapping[str, Any],
    quarterly_gate: Mapping[str, Any],
) -> bool:
    """Require each distribution gate independently once its sample is ready."""

    return bool(
        (not bool(annual_gate["enough_periods"]) or bool(annual_gate["passed"]))
        and (
            not bool(quarterly_gate["enough_periods"])
            or bool(quarterly_gate["passed"])
        )
    )


def select_platform_candidate(
    results: Sequence[Mapping[str, Any]],
    *,
    direction: Direction,
    session_year: int,
) -> dict[str, Any]:
    lookup = _candidate_lookup(results)
    root_id = common_root_candidate(direction).candidate_id
    root = lookup[root_id]
    root_net = float(root["metrics"]["net_log_return"])
    root_sharpe = float(root["metrics"]["sharpe"])
    family = candidate_family(BARS_PER_DAY)
    periods = sorted({item.centre_period_bars for item in family})
    multipliers = sorted({item.width_multiplier for item in family})

    enriched: list[dict[str, Any]] = []
    for item in results:
        candidate = item["candidate"]
        net = float(item["metrics"]["net_log_return"])
        sharpe = float(item["metrics"]["sharpe"])
        economic = net > root_net and sharpe > root_sharpe
        annual = distribution_gate(
            item["yearly"],
            root["yearly"],
            materiality=ANNUAL_MATERIALITY,
            minimum_periods=3,
        )
        quarterly = distribution_gate(
            item["quarterly"],
            root["quarterly"],
            materiality=QUARTERLY_MATERIALITY,
            minimum_periods=12,
            minimum_years=3,
        )
        enriched.append(
            {
                **item,
                "economic_pass": economic,
                "annual_gate": annual,
                "quarterly_gate": quarterly,
            }
        )

    by_axes: dict[tuple[int, int, float, float, float], dict[str, Any]] = {}
    for item in enriched:
        candidate = item["candidate"]
        by_axes[
            (
                int(candidate["centre_period_bars"]),
                int(candidate["filter_order"]),
                float(candidate["rms_window_ratio"]),
                float(candidate["smoothing_ratio"]),
                float(candidate["width_multiplier"]),
            )
        ] = item

    eligible: list[dict[str, Any]] = []
    for item in enriched:
        candidate = item["candidate"]
        p = int(candidate["centre_period_bars"])
        k = float(candidate["width_multiplier"])
        p_index = periods.index(p)
        k_index = multipliers.index(k)
        p_neighbors = [
            periods[index]
            for index in (p_index - 1, p_index + 1)
            if 0 <= index < len(periods)
        ]
        k_neighbors = [
            multipliers[index]
            for index in (k_index - 1, k_index + 1)
            if 0 <= index < len(multipliers)
        ]
        shared = (
            int(candidate["filter_order"]),
            float(candidate["rms_window_ratio"]),
            float(candidate["smoothing_ratio"]),
        )
        p_platform = any(
            by_axes[(neighbor, *shared, k)]["economic_pass"] for neighbor in p_neighbors
        )
        k_platform = any(
            by_axes[(p, *shared, neighbor)]["economic_pass"] for neighbor in k_neighbors
        )
        distribution_pass = independent_distribution_gates_pass(
            item["annual_gate"],
            item["quarterly_gate"],
        )
        item["platform_pass"] = bool(p_platform and k_platform)
        item["selection_eligible"] = bool(
            item["economic_pass"] and item["platform_pass"] and distribution_pass
        )
        if item["selection_eligible"]:
            eligible.append(item)

    if not eligible:
        return {
            "verdict": "no_incremental_successor",
            "selected": root,
            "root": root,
            "eligible_count": 0,
            "multiplicity_count": len(results),
            "top_candidates": [],
        }
    selected = max(
        eligible,
        key=lambda item: (
            float(item["metrics"]["net_log_return"]) - root_net,
            float(item["metrics"]["sharpe"]) - root_sharpe,
        ),
    )
    top_candidates = [
        {
            "candidate": item["candidate"],
            "metrics": item["metrics"],
            "current_year_metrics": item["current_year_metrics"],
            "trade_count": item["trade_count"],
            "economic_pass": item["economic_pass"],
            "platform_pass": item["platform_pass"],
            "annual_gate": {
                key: value
                for key, value in item["annual_gate"].items()
                if key != "deltas"
            },
            "quarterly_gate": {
                key: value
                for key, value in item["quarterly_gate"].items()
                if key != "deltas"
            },
        }
        for item in sorted(
            eligible,
            key=lambda row: (
                float(row["metrics"]["net_log_return"]) - root_net,
                float(row["metrics"]["sharpe"]) - root_sharpe,
            ),
            reverse=True,
        )[:20]
    ]
    return {
        "verdict": "provisional_complete_policy",
        "selected": selected,
        "root": root,
        "eligible_count": len(eligible),
        "multiplicity_count": len(results),
        "top_candidates": top_candidates,
    }


def chain_digest(payload: Mapping[str, Any], *, prior_digest: str) -> str:
    body = json.dumps(
        {"prior_receipt_digest": prior_digest, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(body.encode("utf-8")).hexdigest()


def validate_prior_receipt(
    path: Path,
    *,
    symbol: str,
    session_year: int,
) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("symbol") != symbol:
        raise ValueError("prior receipt symbol mismatch")
    if int(receipt.get("session_year", 0)) != int(session_year) - 1:
        raise ValueError("prior receipt must be from the immediately preceding year")
    if not str(receipt.get("receipt_digest") or ""):
        raise ValueError("prior receipt digest missing")
    return receipt


__all__ = [
    "ANNUAL_MATERIALITY",
    "BARS_PER_DAY",
    "ENTRY_COST_RATE",
    "EXIT_COST_RATE",
    "LatCandidate",
    "QUARTERLY_MATERIALITY",
    "SESSION_YEARS",
    "candidate_family",
    "chain_digest",
    "common_root_candidate",
    "distribution_gate",
    "decision_for_candidate",
    "evaluate_family",
    "evaluate_open_fill_path",
    "fold_direction_state",
    "rails_for_candidate",
    "independent_distribution_gates_pass",
    "performance_metrics",
    "period_sums",
    "select_platform_candidate",
    "signed_position",
    "validate_prior_receipt",
]
