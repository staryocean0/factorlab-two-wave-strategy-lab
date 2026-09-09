"""v0.6.9 audit-only helpers for path-metric sampling-resolution response."""
from __future__ import annotations

from typing import Sequence
import numpy as np

SCHEMA = "two_wave_path_metric_resolution_response@0.6.9"


def path_metrics(values: Sequence[float]) -> dict:
    y = np.asarray(values, dtype=float)
    if y.ndim != 1 or len(y) < 2:
        raise ValueError("at least two path values required")
    if not np.isfinite(y).all():
        raise ValueError("finite path values required")
    changes = np.abs(np.diff(y))
    tv = float(changes.sum())
    return {
        "rows": int(len(y)),
        "total_variation": tv,
        "net_displacement": abs(float(y[-1] - y[0])),
        "efficiency": abs(float(y[-1] - y[0])) / tv if tv else 0.0,
        "jump_share": float(changes.max()) / tv if tv else 1.0,
        "flat_share": float(np.mean(changes == 0)),
    }


def resolution_response(native_values: Sequence[float], fine_values: Sequence[float]) -> dict:
    coarse = path_metrics(native_values)
    fine = path_metrics(fine_values)
    return {
        "schema": SCHEMA,
        "native": coarse,
        "fine": fine,
        "tv_refinement_ratio": fine["total_variation"] / coarse["total_variation"] if coarse["total_variation"] > 0 else None,
        "efficiency_ratio": fine["efficiency"] / coarse["efficiency"] if coarse["efficiency"] > 0 else None,
        "efficiency_delta": fine["efficiency"] - coarse["efficiency"],
        "jump_share_delta": fine["jump_share"] - coarse["jump_share"],
        "flat_share_delta": fine["flat_share"] - coarse["flat_share"],
        "tv_monotonicity_holds": fine["total_variation"] + 1e-12 >= coarse["total_variation"],
        "efficiency_nonincrease_holds": fine["efficiency"] <= coarse["efficiency"] + 1e-12,
    }


def threshold_transition(native_value: float, fine_value: float, *, metric: str) -> str:
    if metric == "efficiency":
        a, b = float(native_value) >= 0.5, float(fine_value) >= 0.5
    elif metric in {"jump_share", "flat_share"}:
        a, b = float(native_value) <= 0.5, float(fine_value) <= 0.5
    else:
        raise ValueError("metric must be efficiency, jump_share or flat_share")
    return f"{'pass' if a else 'fail'}->{'pass' if b else 'fail'}"


def duration_bin(native_leg_duration_bars: int) -> str:
    n = int(native_leg_duration_bars)
    if n <= 0:
        raise ValueError("positive native leg duration required")
    if n <= 3:
        return "1-3"
    if n <= 5:
        return "4-5"
    if n <= 11:
        return "6-11"
    if n <= 23:
        return "12-23"
    return "24+"
