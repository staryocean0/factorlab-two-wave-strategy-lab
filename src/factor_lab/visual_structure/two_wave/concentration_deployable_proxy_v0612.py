"""v0.6.12 audit-only native-5m concentration proxy helpers.

The registered runtime proxy consumes one native OHLC leg only. Supplied 1m,
alternate offsets, counterpart information, direction and outcomes are absent
from this module's proxy interface.
"""
from __future__ import annotations

from typing import Sequence
import numpy as np

SCHEMA = "two_wave_concentration_deployable_proxy@0.6.12"
PRIMARY_PROXY = "native_true_range_concentration"


def _concentration(values: np.ndarray) -> float | None:
    if values.ndim != 1 or len(values) == 0 or not np.isfinite(values).all():
        raise ValueError("finite nonempty one-dimensional movement sequence required")
    if np.any(values < 0):
        raise ValueError("movement magnitudes must be nonnegative")
    total = float(values.sum())
    return float(values.max()) / total if total > 0 else None


def native_concentration_proxy(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
) -> dict:
    """Compute the frozen deployable concentration coordinates for one leg.

    Arrays include the published start-anchor bar through end-anchor bar.
    Transitions therefore use rows 1..end and the previous close from row 0.
    """
    h = np.asarray(highs, dtype=float)
    l = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)
    if any(x.ndim != 1 for x in (h, l, c)) or not (len(h) == len(l) == len(c)) or len(c) < 2:
        raise ValueError("aligned OHLC arrays with at least two bars required")
    if not (np.isfinite(h).all() and np.isfinite(l).all() and np.isfinite(c).all()):
        raise ValueError("finite OHLC values required")
    if np.any(h < l):
        raise ValueError("high must be >= low")

    close_moves = np.abs(np.diff(c))
    bar_ranges = h[1:] - l[1:]
    true_ranges = np.maximum.reduce(
        [bar_ranges, np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])]
    )

    j_close = _concentration(close_moves)
    j_tr = _concentration(true_ranges)
    j_hl = _concentration(bar_ranges)
    values = [x for x in (j_close, j_tr, j_hl) if x is not None]
    if len(values) == 3:
        lower, upper = float(min(values)), float(max(values))
        spread = upper - lower
    else:
        lower = upper = spread = None

    return {
        "schema": SCHEMA,
        "primary_proxy": PRIMARY_PROXY,
        "step_count": int(len(close_moves)),
        "j_close": j_close,
        "j_true_range": j_tr,
        "j_high_low": j_hl,
        "proxy_lower": lower,
        "proxy_upper": upper,
        "proxy_spread": spread,
        "close_move_sum": float(close_moves.sum()),
        "true_range_sum": float(true_ranges.sum()),
        "high_low_sum": float(bar_ranges.sum()),
        "future_outcome_used": False,
        "trade_authority": False,
    }


def empirical_bracket(proxy: dict, oracle_value: float) -> dict:
    """Audit-only empirical coverage check; not a mathematical bound."""
    if proxy.get("proxy_lower") is None or proxy.get("proxy_upper") is None:
        return {"defined": False, "reason": "native_bracket_undefined"}
    oracle = float(oracle_value)
    if not np.isfinite(oracle):
        raise ValueError("finite oracle required")
    lo, hi = float(proxy["proxy_lower"]), float(proxy["proxy_upper"])
    inside = lo <= oracle <= hi
    distance = 0.0 if inside else (lo - oracle if oracle < lo else oracle - hi)
    return {
        "defined": True,
        "inside": bool(inside),
        "below": bool(oracle < lo),
        "above": bool(oracle > hi),
        "width": hi - lo,
        "outside_distance": float(distance),
        "audit_only": True,
    }
