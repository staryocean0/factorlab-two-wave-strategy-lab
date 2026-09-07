"""v0.6.15 native-OHLC structural outer bounds for hidden fine concentration.

The registered bound API consumes one closed native OHLC leg only. It returns
mathematical outer intervals and accepts no fine/oracle/counterpart data.
"""
from __future__ import annotations

import itertools
import math
from typing import Sequence

import numpy as np

SCHEMA = "two_wave_fine_concentration_identifiability@0.6.15"
FINE_STEPS_PER_NATIVE_BAR = 5


def _profile_from_weights(weights: np.ndarray) -> tuple[float, float, float]:
    w = np.asarray(weights, dtype=float)
    if w.ndim != 1 or len(w) < 2 or np.any(w < 0) or not np.isfinite(w).all():
        raise ValueError("finite nonnegative probability vector required")
    s = float(w.sum())
    if s <= 0:
        raise ValueError("positive probability mass required")
    w = w / s
    pos = w[w > 0]
    n = len(w)
    return (
        math.log(n * float(w.max())),
        math.log(n) + float(np.sum(pos * np.log(pos))),
        math.log(n * float(np.sum(w * w))),
    )


def bar_tv_upper(prev_close: float, low: float, high: float, close: float) -> float:
    """Exact max close-path TV over four hidden minute closes in [low,high]."""
    vals = [float(prev_close), float(low), float(high), float(close)]
    if not all(math.isfinite(x) for x in vals):
        raise ValueError("finite prices required")
    if high < low:
        raise ValueError("high must be >= low")
    if close < low or close > high:
        raise ValueError("current close must lie in [low,high]")
    best = 0.0
    for hidden in itertools.product((float(low), float(high)), repeat=4):
        path = (float(prev_close),) + hidden + (float(close),)
        tv = sum(abs(b - a) for a, b in zip(path, path[1:]))
        if tv > best:
            best = tv
    return float(best)


def bar_step_upper(prev_close: float, low: float, high: float, close: float) -> float:
    if high < low or close < low or close > high:
        raise ValueError("valid native bar range required")
    return float(max(abs(low-prev_close), abs(high-prev_close), high-low, abs(low-close), abs(high-close)))


def _simplex_profile_bounds(n: int, j_low: float, j_high: float) -> dict:
    if n < 2 or not (1.0/n - 1e-12 <= j_low <= j_high <= 1.0 + 1e-12):
        raise ValueError("valid max-weight bounds required")
    j_low = max(1.0/n, min(1.0, float(j_low)))
    j_high = max(j_low, min(1.0, float(j_high)))

    c_inf_low = math.log(n*j_low)
    c_inf_high = math.log(n*j_high)

    if j_low <= 1.0/n + 1e-15:
        c1_low = c2_low = 0.0
    else:
        q = (1.0-j_low)/(n-1)
        low_vec = np.asarray([j_low] + [q]*(n-1), dtype=float)
        _, c1_low, c2_low = _profile_from_weights(low_vec)

    remaining = 1.0
    upper_weights = []
    for _ in range(n):
        if remaining <= 1e-15:
            break
        w = min(j_high, remaining)
        upper_weights.append(w)
        remaining -= w
    if remaining > 1e-10:
        raise ValueError("failed to construct capped simplex extremizer")
    if len(upper_weights) < n:
        upper_weights.extend([0.0]*(n-len(upper_weights)))
    _, c1_high, c2_high = _profile_from_weights(np.asarray(upper_weights, dtype=float))

    return {
        "c_inf_low": float(max(0.0, c_inf_low)),
        "c_inf_high": float(min(math.log(n), c_inf_high)),
        "c_1_low": float(max(0.0, c1_low)),
        "c_1_high": float(min(math.log(n), c1_high)),
        "c_2_low": float(max(0.0, c2_low)),
        "c_2_high": float(min(math.log(n), c2_high)),
    }


def native_ohlc_concentration_bounds(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
) -> dict:
    """Return native-information outer bounds for one published native leg.

    Arrays include the published start-anchor row through end-anchor row.
    Transitions use current-bar high/low/close at rows 1..end.
    """
    h = np.asarray(highs, dtype=float)
    l = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)
    if any(x.ndim != 1 for x in (h,l,c)) or not (len(h)==len(l)==len(c)) or len(c)<2:
        raise ValueError("aligned OHLC arrays with at least two rows required")
    if not (np.isfinite(h).all() and np.isfinite(l).all() and np.isfinite(c).all()):
        raise ValueError("finite OHLC required")

    b = len(c)-1
    n = FINE_STEPS_PER_NATIVE_BAR*b
    tv_low = 0.0
    tv_high = 0.0
    m_low = 0.0
    m_high = 0.0
    for j in range(1, len(c)):
        if h[j] < l[j] or c[j] < l[j] or c[j] > h[j]:
            raise ValueError("invalid native bar OHLC envelope")
        d = abs(float(c[j]-c[j-1]))
        tv_low += d
        tv_high += bar_tv_upper(float(c[j-1]), float(l[j]), float(h[j]), float(c[j]))
        m_low = max(m_low, d/FINE_STEPS_PER_NATIVE_BAR)
        m_high = max(m_high, bar_step_upper(float(c[j-1]), float(l[j]), float(h[j]), float(c[j])))

    if tv_high <= 0 or m_high <= 0:
        return {
            "schema": SCHEMA,
            "defined": False,
            "reason": "no_positive_hidden_movement_possible",
            "native_transition_count": b,
            "fine_step_count": n,
            "future_outcome_used": False,
            "trade_authority": False,
        }

    j_low = max(1.0/n, m_low/tv_high)
    j_high = min(1.0, m_high/tv_low) if tv_low > 0 else 1.0
    if j_high < j_low:
        raise ValueError("inconsistent structural J bounds")
    prof = _simplex_profile_bounds(n, j_low, j_high)
    return {
        "schema": SCHEMA,
        "defined": True,
        "reason": None,
        "native_transition_count": b,
        "fine_step_count": n,
        "tv_low": float(tv_low),
        "tv_high": float(tv_high),
        "m_low": float(m_low),
        "m_high": float(m_high),
        "j_low": float(j_low),
        "j_high": float(j_high),
        **prof,
        "future_outcome_used": False,
        "trade_authority": False,
    }
