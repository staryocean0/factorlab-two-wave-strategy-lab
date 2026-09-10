"""v0.6.21 robust whole-parent-window direction/state research component.

This module changes no identity or qualification rule. It consumes one already
completed parent window and estimates a robust low-frequency centerline using
all closes in that span. No cross-view or future-outcome information is used.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

SCHEMA = "two_wave_whole_window_huber_direction@0.6.21"
HUBER_C = 1.345
IRLS_ITERATIONS = 8
MAD_SCALE = 1.4826
EPS = 1e-12
RANGE_TOLERANCE = 0.15
STRONG_DRIFT = 0.50


def huber_centerline_score(
    closes: Sequence[float],
    five_occurrence_bars: Sequence[int],
    amplitude_unit_price: float,
) -> dict:
    anchors = tuple(int(x) for x in five_occurrence_bars)
    if len(anchors) != 5 or any(b <= a for a, b in zip(anchors, anchors[1:])):
        raise ValueError("five strictly increasing occurrence bars required")
    if anchors[0] < 0 or anchors[-1] >= len(closes):
        raise ValueError("occurrence bars outside supplied closes")
    amp = float(amplitude_unit_price)
    if not np.isfinite(amp) or amp <= 0:
        raise ValueError("positive finite amplitude unit required")

    y = np.asarray(closes[anchors[0] : anchors[-1] + 1], dtype=float)
    if len(y) < 3 or not np.all(np.isfinite(y)):
        raise ValueError("finite completed parent window required")
    x = np.linspace(-0.5, 0.5, len(y), dtype=float)
    X = np.column_stack([np.ones(len(y), dtype=float), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)

    for _ in range(IRLS_ITERATIONS):
        resid = y - X @ beta
        center = float(np.median(resid))
        scale = MAD_SCALE * float(np.median(np.abs(resid - center)))
        scale = max(scale, EPS)
        u = np.abs(resid) / (HUBER_C * scale)
        weights = np.ones_like(u)
        mask = u > 1.0
        weights[mask] = 1.0 / u[mask]
        root = np.sqrt(weights)
        beta, *_ = np.linalg.lstsq(X * root[:, None], y * root, rcond=None)

    intercept = float(beta[0])
    total_drift = float(beta[1])
    score = total_drift / amp
    if not all(np.isfinite(v) for v in (intercept, total_drift, score)):
        raise AssertionError("non-finite v0.6.21 Huber result")
    return {
        "schema": SCHEMA,
        "window_start_bar": anchors[0],
        "window_end_bar": anchors[-1],
        "window_bars": len(y),
        "huber_c": HUBER_C,
        "irls_iterations": IRLS_ITERATIONS,
        "centerline_intercept_price": intercept,
        "centerline_total_drift_price": total_drift,
        "normalized_parent_drift": score,
    }


def classify_normalized_parent_drift(score: float) -> str:
    value = float(score)
    if not np.isfinite(value):
        raise ValueError("finite normalized parent drift required")
    if value >= STRONG_DRIFT:
        return "uptrend"
    if value <= -STRONG_DRIFT:
        return "downtrend"
    if abs(value) <= RANGE_TOLERANCE:
        return "range"
    return "uncertain"


def classify_parent_window(
    closes: Sequence[float],
    five_occurrence_bars: Sequence[int],
    amplitude_unit_price: float,
) -> dict:
    out = huber_centerline_score(closes, five_occurrence_bars, amplitude_unit_price)
    out["classification"] = classify_normalized_parent_drift(out["normalized_parent_drift"])
    out["future_outcome_used"] = False
    out["trade_authority"] = False
    return out
