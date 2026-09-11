"""Read-only v0.6.39 within-leg phase-progress shape descriptors."""
from __future__ import annotations

from typing import Sequence

import numpy as np

SCHEMA = "two_wave_order_sensitive_residual_shape@0.6.39"
GRID_POINTS_PER_LEG = 65


def phase_progress_curve(values: Sequence[float]) -> np.ndarray:
    """Interpolate one leg to the frozen phase grid and normalize endpoints to 0 -> 1."""
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1 or len(arr) < 2:
        raise ValueError("each leg requires at least two observations")
    if not np.all(np.isfinite(arr)):
        raise ValueError("finite leg observations required")
    source = np.linspace(0.0, 1.0, len(arr), dtype=float)
    target = np.linspace(0.0, 1.0, GRID_POINTS_PER_LEG, dtype=float)
    path = np.interp(target, source, arr)
    displacement = float(path[-1] - path[0])
    if not np.isfinite(displacement) or abs(displacement) <= 1e-12:
        raise ValueError("non-zero finite leg endpoint displacement required")
    progress = (path - path[0]) / displacement
    if not np.all(np.isfinite(progress)):
        raise AssertionError("non-finite progress curve")
    if abs(float(progress[0])) > 1e-12 or abs(float(progress[-1]) - 1.0) > 1e-12:
        raise AssertionError("progress endpoints must normalize to 0 and 1")
    return progress


def progress_shape_descriptors(
    closes: Sequence[float], five_occurrence_bars: Sequence[int]
) -> dict:
    anchors = tuple(int(x) for x in five_occurrence_bars)
    if len(anchors) != 5 or any(b <= a for a, b in zip(anchors, anchors[1:])):
        raise ValueError("five strictly increasing occurrence bars required")
    if anchors[0] < 0 or anchors[-1] >= len(closes):
        raise ValueError("occurrence bars outside supplied closes")
    arr = np.asarray(closes, dtype=float)

    c1_first = phase_progress_curve(arr[anchors[0] : anchors[1] + 1])
    c1_second = phase_progress_curve(arr[anchors[1] : anchors[2] + 1])
    c2_first = phase_progress_curve(arr[anchors[2] : anchors[3] + 1])
    c2_second = phase_progress_curve(arr[anchors[3] : anchors[4] + 1])

    d_first = np.abs(c1_first - c2_first)
    d_second = np.abs(c1_second - c2_second)
    first_l1 = float(np.mean(d_first))
    second_l1 = float(np.mean(d_second))
    first_linf = float(np.max(d_first))
    second_linf = float(np.max(d_second))
    return {
        "schema": SCHEMA,
        "grid_points_per_leg": GRID_POINTS_PER_LEG,
        "first_leg_progress_l1": first_l1,
        "second_leg_progress_l1": second_l1,
        "first_leg_progress_linf": first_linf,
        "second_leg_progress_linf": second_linf,
        "mean_leg_progress_l1": float((first_l1 + second_l1) / 2.0),
        "max_leg_progress_l1": float(max(first_l1, second_l1)),
        "mean_leg_progress_linf": float((first_linf + second_linf) / 2.0),
        "max_leg_progress_linf": float(max(first_linf, second_linf)),
        "future_outcome_used": False,
        "trade_authority": False,
    }


def numeric_summary(values: Sequence[float]) -> dict:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1 or len(arr) == 0 or not np.all(np.isfinite(arr)):
        raise ValueError("non-empty finite numeric vector required")
    return {
        "count": int(len(arr)),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "q25": float(np.quantile(arr, 0.25)),
        "q75": float(np.quantile(arr, 0.75)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def harm_greater_probability(harm: Sequence[float], repair: Sequence[float]) -> float:
    h = np.asarray(harm, dtype=float)
    r = np.asarray(repair, dtype=float)
    if len(h) == 0 or len(r) == 0 or not np.all(np.isfinite(h)) or not np.all(np.isfinite(r)):
        raise ValueError("non-empty finite harm and repair vectors required")
    diff = h[:, None] - r[None, :]
    return float((np.sum(diff > 0) + 0.5 * np.sum(diff == 0)) / diff.size)
