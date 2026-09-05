"""Policy-free causal matched-volatility timing signals.

Research packages may deliberately seal a date range.  Runtime evaluation must
not copy that policy into the mathematical formula, otherwise a frozen formula
cannot be evaluated on a later aggregate black box.  This module owns only the
causal transformation; dataset and evidence boundaries stay with callers.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def build_lagged_matched_volatility_ewma_score(
    close_price: pd.Series,
    *,
    span_bars: int,
) -> pd.Series:
    """Normalize returns by prior EWMA volatility and smooth at the same span."""

    if span_bars < 2:
        raise ValueError("matched-volatility span must be at least two bars")
    if not isinstance(close_price.index, pd.DatetimeIndex):
        raise TypeError("matched-volatility close requires a DatetimeIndex")
    if close_price.empty or close_price.index.has_duplicates or not close_price.index.is_monotonic_increasing:
        raise ValueError("matched-volatility close must be non-empty and ordered")
    close = pd.to_numeric(close_price, errors="raise").astype(float)
    if bool(close.le(0.0).any()):
        raise ValueError("matched-volatility close values must be positive")
    returns = close.pct_change(fill_method=None)
    lagged_variance = returns.pow(2).ewm(span=span_bars, adjust=False).mean().shift(1)
    normalized = returns / np.sqrt(lagged_variance.where(lagged_variance.gt(0.0)))
    score = (
        math.sqrt(span_bars)
        * normalized.ewm(
            span=span_bars,
            adjust=False,
        ).mean()
    )
    score.name = f"matched_volatility_ewma_s{span_bars}"
    score.attrs["runtime_uses_future"] = False
    score.attrs["normalization"] = "same_span_lagged_ewma_variance"
    return score


__all__ = ["build_lagged_matched_volatility_ewma_score"]
