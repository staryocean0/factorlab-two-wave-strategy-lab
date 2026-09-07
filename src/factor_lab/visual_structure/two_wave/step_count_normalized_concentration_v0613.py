"""v0.6.13 audit-only step-count normalized concentration profile.

The primitive consumes one nonnegative movement vector only. It defines no
qualification threshold, recognizer decision, counterpart relation or oracle.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np

SCHEMA = "two_wave_step_count_normalized_concentration@0.6.13"


def concentration_profile(movements: Sequence[float]) -> dict:
    x = np.asarray(movements, dtype=float)
    if x.ndim != 1 or not np.isfinite(x).all():
        raise ValueError("finite one-dimensional movement vector required")
    if np.any(x < 0):
        raise ValueError("movement magnitudes must be nonnegative")
    n = int(len(x))
    total = float(x.sum())
    if n < 2:
        return {
            "schema": SCHEMA,
            "defined": False,
            "reason": "fewer_than_two_movements",
            "step_count": n,
            "total_movement": total,
            "c_inf": None,
            "c_1": None,
            "c_2": None,
            "future_outcome_used": False,
            "trade_authority": False,
        }
    if total <= 0:
        return {
            "schema": SCHEMA,
            "defined": False,
            "reason": "zero_total_movement",
            "step_count": n,
            "total_movement": total,
            "c_inf": None,
            "c_1": None,
            "c_2": None,
            "future_outcome_used": False,
            "trade_authority": False,
        }

    w = x / total
    positive = w[w > 0]
    c_inf = math.log(float(n) * float(w.max()))
    entropy = -float(np.sum(positive * np.log(positive)))
    c_1 = math.log(float(n)) - entropy
    c_2 = math.log(float(n) * float(np.sum(w * w)))
    return {
        "schema": SCHEMA,
        "defined": True,
        "reason": None,
        "step_count": n,
        "total_movement": total,
        "c_inf": float(c_inf),
        "c_1": float(c_1),
        "c_2": float(c_2),
        "raw_max_share": float(w.max()),
        "future_outcome_used": False,
        "trade_authority": False,
    }


def uniformly_subdivide(movements: Sequence[float], k: int) -> np.ndarray:
    """Synthetic-test helper: split each movement into k equal children."""
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("positive integer k required")
    x = np.asarray(movements, dtype=float)
    if x.ndim != 1 or not np.isfinite(x).all() or np.any(x < 0):
        raise ValueError("finite nonnegative one-dimensional movement vector required")
    return np.repeat(x / float(k), k)


def profile_from_closes(closes: Sequence[float]) -> dict:
    """Convenience audit wrapper for a closed path; still single-view only."""
    y = np.asarray(closes, dtype=float)
    if y.ndim != 1 or len(y) < 2 or not np.isfinite(y).all():
        raise ValueError("at least two finite closes required")
    return concentration_profile(np.abs(np.diff(y)))
