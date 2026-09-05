"""Causal long/flat battle helpers for the V57 arc and P300 low-pass.

The line observed at the close of bar ``t`` decides the position opened at the
open of bar ``t + 1``.  V56 is already expressed in executable-bar semantics;
when it is active the conservative combination routes the long sleeve to cash.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def direction_decision(line: pd.Series, *, valid: pd.Series | None = None) -> pd.Series:
    """Return the close-of-bar long decision from the line's one-bar direction."""

    numeric = pd.to_numeric(line, errors="coerce").astype(float)
    decision = numeric.diff().gt(0.0) & numeric.notna()
    if valid is not None:
        if not valid.index.equals(line.index):
            raise ValueError("valid mask must share the line index")
        decision &= valid.astype(bool)
    return decision.rename("decision_long_for_next_bar")


def next_bar_position(decision: pd.Series) -> pd.Series:
    """Shift a close-of-bar decision into the next bar's executable position."""

    numeric = decision.astype(bool)
    return numeric.shift(1, fill_value=False).astype(float).rename("executable_long_position")


def apply_v56_cash_veto(
    base_position: pd.Series,
    v56_executable_risk: pd.Series,
) -> pd.Series:
    """Route a long sleeve to cash while the V56 crash-tip expert is active."""

    if not base_position.index.equals(v56_executable_risk.index):
        raise ValueError("base position and V56 risk must share the exact index")
    return (base_position.astype(float) * (~v56_executable_risk.astype(bool)).astype(float)).rename("v56_vetoed_long_position")


def backtest_open_to_open(
    open_price: pd.Series,
    position: pd.Series,
    *,
    buy_cost_bps: float = 1.0,
    sell_cost_bps: float = 6.0,
) -> pd.DataFrame:
    """Backtest binary long/flat positions with next-open execution economics."""

    if not open_price.index.equals(position.index):
        raise ValueError("open price and position must share the exact index")
    price = pd.to_numeric(open_price, errors="coerce").astype(float)
    pos = pd.to_numeric(position, errors="coerce").fillna(0.0).astype(float)
    if not pos.isin((0.0, 1.0)).all():
        raise ValueError("position must be binary long/flat")
    if price.isna().any() or price.le(0.0).any():
        raise ValueError("open prices must be finite and positive")

    forward_log_return = np.log(price.shift(-1) / price)
    change = pos.diff().fillna(pos)
    cost = change.clip(lower=0.0) * (buy_cost_bps / 10_000.0) + (-change.clip(upper=0.0)) * (sell_cost_bps / 10_000.0)
    gross = pos * forward_log_return
    net = gross - cost
    return pd.DataFrame(
        {
            "open": price,
            "position": pos,
            "forward_open_log_return": forward_log_return,
            "gross_log_return": gross,
            "cost_log_return": cost,
            "net_log_return": net,
            "entry": change.gt(0.0),
            "exit": change.lt(0.0),
        },
        index=open_price.index,
    )


def _maximum_drawdown(net_log_return: pd.Series) -> float:
    nav = np.exp(net_log_return.fillna(0.0).cumsum())
    return float((nav / nav.cummax() - 1.0).min())


def _episode_metrics(ledger: pd.DataFrame) -> dict[str, float | int]:
    active = ledger["position"].gt(0.0)
    prior_active = active.shift(fill_value=False)
    episode = (active & ~prior_active).cumsum()
    # The sell cost is booked on the first flat row.  Include that row in the
    # preceding episode; otherwise win rate, profit factor and average trade
    # silently omit every exit cost even though total return includes it.
    scored = active | ledger["exit"].astype(bool)
    returns = ledger.loc[scored].groupby(episode.loc[scored], sort=True)["net_log_return"].sum()
    wins = returns.loc[returns > 0.0]
    losses = returns.loc[returns < 0.0]
    loss_sum = float(-losses.sum())
    return {
        "trade_count": int(len(returns)),
        "win_rate": float((returns > 0.0).mean()) if len(returns) else 0.0,
        "profit_factor": (float(wins.sum() / loss_sum) if loss_sum > 0.0 else (math.inf if float(wins.sum()) > 0.0 else 0.0)),
        "average_trade_log_return": float(returns.mean()) if len(returns) else 0.0,
    }


def summarize_period(
    ledger: pd.DataFrame,
    *,
    start: str,
    end: str,
) -> dict[str, float | int | str]:
    """Summarize one predeclared time block without exposing event details."""

    scope = ledger.loc[pd.Timestamp(start) : pd.Timestamp(end)].copy()
    scope = scope.loc[scope["forward_open_log_return"].notna()]
    if scope.empty:
        raise ValueError(f"empty evaluation block: {start}/{end}")
    elapsed_years = max(
        (scope.index[-1] - scope.index[0]).total_seconds() / (365.2425 * 24.0 * 60.0 * 60.0),
        1.0 / 365.2425,
    )
    net_sum = float(scope["net_log_return"].sum())
    gross_sum = float(scope["gross_log_return"].sum())
    periods_per_year = len(scope) / elapsed_years
    volatility = float(scope["net_log_return"].std(ddof=0))
    episode = _episode_metrics(scope)
    return {
        "start": start,
        "end": end,
        "bar_count": int(len(scope)),
        "gross_total_return": float(np.exp(gross_sum) - 1.0),
        "net_total_return": float(np.exp(net_sum) - 1.0),
        "net_cagr": float(np.exp(net_sum / elapsed_years) - 1.0),
        "maximum_drawdown": _maximum_drawdown(scope["net_log_return"]),
        "sharpe": (float(scope["net_log_return"].mean() / volatility * math.sqrt(periods_per_year)) if volatility > 0.0 else 0.0),
        "exposure": float(scope["position"].mean()),
        "turnover_count": int(scope["entry"].sum() + scope["exit"].sum()),
        "cost_log_return_sum": float(scope["cost_log_return"].sum()),
        **episode,
    }


__all__ = [
    "apply_v56_cash_veto",
    "backtest_open_to_open",
    "direction_decision",
    "next_bar_position",
    "summarize_period",
]
