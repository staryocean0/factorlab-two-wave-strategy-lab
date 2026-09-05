# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportIndexIssue=false, reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Hierarchical twelve-scale paper-kernel trend state machine V1.

The slow and middle scale groups define a causal macro regime.  The fast group
controls ordinary long/cash timing inside both macro-up and macro-flat regimes.
Macro-down is cash by default and only admits a separately armed fast rebound.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.strategy.services.risk_off_paper_kernel_native_trend import (
    PAPER_SIGNAL_SPANS,
    SCALE_GROUPS,
)

PAPER_VOLATILITY_SPAN_DAYS: Final[int] = 33
DEFAULT_BARS_PER_DAY: Final[int] = 16


@dataclass(frozen=True, slots=True)
class PaperKernelHierarchicalTrendV1Spec:
    """Frozen architecture-prototype parameters in normalized-signal units."""

    bars_per_day: int = DEFAULT_BARS_PER_DAY
    macro_boundary: float = 0.20
    fast_hysteresis: float = 0.50
    rebound_oversold_strength: float = 1.00
    rebound_entry_score: float = 0.25
    rebound_failure_score: float = 0.00

    def __post_init__(self) -> None:
        if self.bars_per_day < 1:
            raise ValueError("bars_per_day must be positive")
        if self.macro_boundary <= 0.0:
            raise ValueError("macro_boundary must be positive")
        if self.fast_hysteresis <= 0.0:
            raise ValueError("fast_hysteresis must be positive")
        if self.rebound_oversold_strength <= self.fast_hysteresis:
            raise ValueError("rebound oversold strength must exceed fast hysteresis")
        if not 0.0 < self.rebound_entry_score <= self.fast_hysteresis:
            raise ValueError("rebound entry must be positive and no wider than fast hysteresis")
        if not self.rebound_failure_score < self.rebound_entry_score:
            raise ValueError("rebound failure must be below rebound entry")


def build_paper_kernel_intraday_scale_state(
    close_price: pd.Series,
    spec: PaperKernelHierarchicalTrendV1Spec | None = None,
) -> pd.DataFrame:
    """Apply the paper's normalized EWMA direction formula at 15-minute scale."""

    spec = spec or PaperKernelHierarchicalTrendV1Spec()
    if (
        close_price.empty
        or not isinstance(close_price.index, pd.DatetimeIndex)
        or close_price.index.has_duplicates
        or not close_price.index.is_monotonic_increasing
    ):
        raise ValueError("close_price must be a non-empty ordered datetime series")
    close = pd.to_numeric(close_price, errors="coerce").astype(float)
    if bool(close.le(0.0).fillna(True).any()):
        raise ValueError("close prices must be finite and positive")
    returns = close.pct_change(fill_method=None)
    volatility_span = PAPER_VOLATILITY_SPAN_DAYS * spec.bars_per_day
    variance = returns.pow(2).ewm(span=volatility_span, adjust=False).mean()
    normalized_return = returns / np.sqrt(variance.shift(1))
    state = pd.DataFrame(
        {"paper_intraday_normalized_return": normalized_return},
        index=close.index,
    )
    for span_days in PAPER_SIGNAL_SPANS:
        span_bars = span_days * spec.bars_per_day
        nu = 1.0 - 2.0 / (span_bars + 1.0)
        loading = math.sqrt((1.0 + nu) / (1.0 - nu))
        state[f"paper_intraday_signal_s{span_days}"] = (
            loading
            * normalized_return.ewm(span=span_bars, adjust=False).mean()
        )
    for group, spans in SCALE_GROUPS.items():
        state[f"paper_{group}_direction_score"] = state[
            [f"paper_intraday_signal_s{span}" for span in spans]
        ].mean(axis=1)
    score_columns = [
        f"paper_{group}_direction_score" for group in SCALE_GROUPS
    ]
    state["paper_intraday_state_valid"] = state[score_columns].notna().all(axis=1)
    state["runtime_uses_future"] = False
    return state


def classify_paper_kernel_macro_regime(
    scale_state: pd.DataFrame,
    spec: PaperKernelHierarchicalTrendV1Spec | None = None,
) -> pd.Series:
    """Classify macro down/flat/up with slow direction plus middle agreement."""

    spec = spec or PaperKernelHierarchicalTrendV1Spec()
    required = {
        "paper_middle_direction_score",
        "paper_slow_direction_score",
        "paper_intraday_state_valid",
    }
    missing = sorted(required.difference(scale_state.columns))
    if missing:
        raise KeyError(f"scale state missing columns: {missing}")
    middle = scale_state["paper_middle_direction_score"]
    slow = scale_state["paper_slow_direction_score"]
    valid = scale_state["paper_intraday_state_valid"].astype(bool)
    down = valid & slow.le(-spec.macro_boundary) & middle.lt(0.0)
    up = valid & slow.ge(spec.macro_boundary) & middle.gt(0.0)
    regime = pd.Series("macro_flat", index=scale_state.index, dtype="object")
    regime.loc[down] = "macro_down"
    regime.loc[up] = "macro_up"
    regime.loc[~valid] = "unavailable"
    return regime


def route_paper_kernel_hierarchical_trend_v1(
    scale_state: pd.DataFrame,
    spec: PaperKernelHierarchicalTrendV1Spec | None = None,
) -> pd.DataFrame:
    """Route the macro regime, fast timing, and armed crash-rebound lifecycle."""

    spec = spec or PaperKernelHierarchicalTrendV1Spec()
    required = {
        "paper_fast_direction_score",
        "paper_middle_direction_score",
        "paper_slow_direction_score",
        "paper_intraday_state_valid",
    }
    missing = sorted(required.difference(scale_state.columns))
    if missing:
        raise KeyError(f"scale state missing columns: {missing}")
    if (
        scale_state.empty
        or not isinstance(scale_state.index, pd.DatetimeIndex)
        or scale_state.index.has_duplicates
        or not scale_state.index.is_monotonic_increasing
    ):
        raise ValueError("scale_state must be a non-empty ordered frame")
    macro_regime = classify_paper_kernel_macro_regime(scale_state, spec)
    fast_long = True
    rebound_armed = False
    rebound_long = False
    decisions: list[float] = []
    states: list[str] = []
    transitions: list[str] = []
    armed_ledger: list[bool] = []
    rebound_ledger: list[bool] = []
    for index, row in enumerate(scale_state.itertuples()):
        transition = "hold_state"
        valid = bool(row.paper_intraday_state_valid)
        fast_score = float(row.paper_fast_direction_score) if valid else math.nan
        regime = str(macro_regime.iloc[index])
        if not valid:
            fast_long = False
            rebound_armed = False
            rebound_long = False
            decision = 0.0
            state = "unavailable_cash"
            transition = "state_unavailable"
        else:
            if fast_score <= -spec.fast_hysteresis:
                fast_long = False
            elif fast_score >= spec.fast_hysteresis:
                fast_long = True
            if regime != "macro_down":
                if rebound_armed or rebound_long:
                    transition = "leave_macro_down"
                rebound_armed = False
                rebound_long = False
                decision = 1.0 if fast_long else 0.0
                state = f"{regime}_fast_{'long' if fast_long else 'cash'}"
            else:
                if fast_score <= -spec.rebound_oversold_strength:
                    if not rebound_armed:
                        transition = "arm_crash_rebound"
                    rebound_armed = True
                    rebound_long = False
                if (
                    rebound_armed
                    and not rebound_long
                    and fast_score >= spec.rebound_entry_score
                ):
                    rebound_long = True
                    rebound_armed = False
                    transition = "enter_crash_rebound"
                if rebound_long and fast_score <= spec.rebound_failure_score:
                    rebound_long = False
                    transition = "fail_crash_rebound"
                decision = 1.0 if rebound_long else 0.0
                state = (
                    "macro_down_rebound_long"
                    if rebound_long
                    else "macro_down_cash"
                )
        decisions.append(decision)
        states.append(state)
        transitions.append(transition)
        armed_ledger.append(rebound_armed)
        rebound_ledger.append(rebound_long)
    decision_series = pd.Series(decisions, index=scale_state.index, dtype=float)
    return pd.DataFrame(
        {
            "paper_macro_regime": macro_regime,
            "paper_hierarchical_state": states,
            "paper_hierarchical_transition": transitions,
            "paper_rebound_armed": armed_ledger,
            "paper_rebound_long": rebound_ledger,
            "decision_long_for_next_bar": decision_series,
            "executable_long_position": decision_series.shift(1, fill_value=0.0),
            "single_execution_shift": True,
            "runtime_uses_future": False,
        },
        index=scale_state.index,
    )


def paper_kernel_hierarchical_trend_v1_contract() -> Mapping[str, object]:
    """Return the frozen V1 architecture-prototype contract."""

    spec = PaperKernelHierarchicalTrendV1Spec()
    return {
        "schema_id": "risk_off_paper_kernel_hierarchical_trend_v1@1.0",
        "strategy_identity": "paper_kernel_hierarchical_trend_v1",
        "paper_signal_spans_days": list(PAPER_SIGNAL_SPANS),
        "bars_per_day": spec.bars_per_day,
        "scale_groups": {
            group: list(spans) for group, spans in SCALE_GROUPS.items()
        },
        "direction_formula": (
            "paper normalized-return EWMA applied causally at span_days*16 bars"
        ),
        "macro_router": (
            "down=slow<=-boundary and middle<0; "
            "up=slow>=boundary and middle>0; otherwise flat"
        ),
        "macro_up_policy": "fast_direction_hysteresis",
        "macro_flat_policy": "fast_direction_hysteresis",
        "macro_down_policy": "cash_except_separately_armed_fast_rebound",
        "frozen_architecture_spec": {
            "macro_boundary": spec.macro_boundary,
            "fast_hysteresis": spec.fast_hysteresis,
            "rebound_oversold_strength": spec.rebound_oversold_strength,
            "rebound_entry_score": spec.rebound_entry_score,
            "rebound_failure_score": spec.rebound_failure_score,
        },
        "single_execution_shift": True,
        "runtime_uses_future": False,
        "w72_is_benchmark_only": True,
        "production_authority": False,
    }


__all__ = [
    "DEFAULT_BARS_PER_DAY",
    "PAPER_VOLATILITY_SPAN_DAYS",
    "PaperKernelHierarchicalTrendV1Spec",
    "build_paper_kernel_intraday_scale_state",
    "classify_paper_kernel_macro_regime",
    "paper_kernel_hierarchical_trend_v1_contract",
    "route_paper_kernel_hierarchical_trend_v1",
]
