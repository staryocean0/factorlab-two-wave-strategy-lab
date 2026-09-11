"""Read-only v0.6.40 leg-asymmetry and harmless-slicing stability helpers."""
from __future__ import annotations

from collections import Counter
from typing import Mapping, Sequence

import numpy as np

SCHEMA = "two_wave_leg_asymmetry_stability@0.6.40"


def leg_asymmetry(descriptors: Mapping[str, float]) -> dict:
    """Return the frozen signed first-minus-second leg shape asymmetries."""
    first_l1 = float(descriptors["first_leg_progress_l1"])
    second_l1 = float(descriptors["second_leg_progress_l1"])
    first_linf = float(descriptors["first_leg_progress_linf"])
    second_linf = float(descriptors["second_leg_progress_linf"])
    vals = np.asarray([first_l1, second_l1, first_linf, second_linf], dtype=float)
    if not np.all(np.isfinite(vals)):
        raise ValueError("finite progress-shape descriptors required")
    return {
        "schema": SCHEMA,
        "A_L1": float(first_l1 - second_l1),
        "A_Linf": float(first_linf - second_linf),
        "future_outcome_used": False,
        "trade_authority": False,
    }


def sign_bucket(value: float, *, atol: float = 1e-12) -> str:
    """Classify relative asymmetry around the structural equality boundary zero."""
    x = float(value)
    if not np.isfinite(x):
        raise ValueError("finite value required")
    if x > atol:
        return "positive"
    if x < -atol:
        return "negative"
    return "zero"


def sign_fractions(values: Sequence[float]) -> dict:
    if len(values) == 0:
        raise ValueError("non-empty values required")
    counts = Counter(sign_bucket(float(v)) for v in values)
    n = float(len(values))
    return {
        "count": int(len(values)),
        "positive": float(counts["positive"] / n),
        "zero": float(counts["zero"] / n),
        "negative": float(counts["negative"] / n),
    }


def greater_probability(left: Sequence[float], right: Sequence[float]) -> float:
    """Return P(left > right) + 0.5 P(left == right), with no fitted threshold."""
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if len(a) == 0 or len(b) == 0 or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise ValueError("non-empty finite vectors required")
    diff = a[:, None] - b[None, :]
    return float((np.sum(diff > 0) + 0.5 * np.sum(diff == 0)) / diff.size)
