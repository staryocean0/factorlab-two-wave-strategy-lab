"""Read-only v0.6.28 attribution helpers for v0.6.27 Range rescues."""
from __future__ import annotations

from typing import Iterable

import numpy as np

SCHEMA = "two_wave_v0627_range_rescue_attribution@0.6.28"
RANGE_SCALE = 0.15


def exactness_transition(before_a: str, before_b: str, after_a: str, after_b: str) -> str:
    before = str(before_a) == str(before_b)
    after = str(after_a) == str(after_b)
    if before and after:
        return "retained_exact"
    if before and not after:
        return "introduced_harm"
    if not before and after:
        return "repaired_v0625_nonexact"
    return "persistent_nonexact"


def changed_to_range(before: str, after: str) -> bool:
    return str(before) == "uncertain" and str(after) == "range"


def pair_range_topology(before_a: str, before_b: str, after_a: str, after_b: str) -> str:
    ca = changed_to_range(before_a, after_a)
    cb = changed_to_range(before_b, after_b)
    if ca and cb:
        return "both_sides_new_range"
    if ca:
        return "main_only_new_range" if str(before_b) == "uncertain" else "one_side_new_range_other_already_decisive"
    if cb:
        return "other_only_new_range" if str(before_a) == "uncertain" else "one_side_new_range_other_already_decisive"
    return "no_new_range"


def summarize(values: Iterable[float]) -> dict:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return {"n": 0, "min": None, "p25": None, "median": None, "p75": None, "p90": None, "max": None}
    if not np.all(np.isfinite(arr)):
        raise ValueError("finite diagnostic values required")
    return {
        "n": int(arr.size),
        "min": float(np.min(arr)),
        "p25": float(np.quantile(arr, 0.25)),
        "median": float(np.median(arr)),
        "p75": float(np.quantile(arr, 0.75)),
        "p90": float(np.quantile(arr, 0.90)),
        "max": float(np.max(arr)),
    }


def normalized_range_support_dispersion(consensus_score_span: float) -> float:
    value = float(consensus_score_span)
    if not np.isfinite(value) or value < 0:
        raise ValueError("nonnegative finite consensus score span required")
    return value / RANGE_SCALE
