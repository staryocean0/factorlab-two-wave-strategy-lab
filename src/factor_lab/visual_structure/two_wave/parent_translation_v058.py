"""v0.5.8 phase-aligned whole-cycle translation (PAWCT) representation.

This module does not identify, qualify, select, or classify a two-wave record.
It only reads an already-confirmed frozen record span and estimates how the
second complete raw-price cycle is translated relative to the first after a
fixed two-leg phase normalization.
"""
from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np

GRID_POINTS_PER_LEG = 65
TOTAL_PHASE_POINTS = 2 * GRID_POINTS_PER_LEG - 1


def _fixed_leg_grid(start: float, end: float) -> np.ndarray:
    return np.linspace(start, end, GRID_POINTS_PER_LEG, dtype=float)


def _interpolate_leg(values: Sequence[float], phase_start: float, phase_end: float) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1 or len(arr) < 2:
        raise ValueError("each PAWCT leg needs at least two raw bars")
    if not np.all(np.isfinite(arr)):
        raise ValueError("PAWCT raw path contains non-finite prices")
    source = np.linspace(phase_start, phase_end, len(arr), dtype=float)
    target = _fixed_leg_grid(phase_start, phase_end)
    return np.interp(target, source, arr)


def phase_aligned_cycle_path(
    closes: Sequence[float],
    start_bar: int,
    opposite_bar: int,
    end_bar: int,
) -> np.ndarray:
    """Map one complete reversal cycle onto the frozen 129-point phase grid."""
    if not (0 <= start_bar < opposite_bar < end_bar < len(closes)):
        raise ValueError("cycle anchors must be strictly increasing and inside the raw path")
    first = _interpolate_leg(closes[start_bar : opposite_bar + 1], 0.0, 1.0)
    second = _interpolate_leg(closes[opposite_bar : end_bar + 1], 1.0, 2.0)
    path = np.concatenate([first, second[1:]])
    if len(path) != TOTAL_PHASE_POINTS:
        raise AssertionError("unexpected PAWCT phase-grid size")
    return path


def phase_aligned_translation_from_closes(
    closes: Sequence[float],
    five_occurrence_bars: Sequence[int],
    amplitude_unit_price: float,
) -> dict:
    """Return the frozen PAWCT continuous parent-translation representation."""
    anchors = [int(x) for x in five_occurrence_bars]
    if len(anchors) != 5 or any(a >= b for a, b in zip(anchors, anchors[1:])):
        raise ValueError("PAWCT requires five strictly increasing occurrence bars")
    amp = float(amplitude_unit_price)
    if not np.isfinite(amp) or amp <= 0:
        raise ValueError("PAWCT amplitude unit must be finite and positive")

    c1 = phase_aligned_cycle_path(closes, anchors[0], anchors[1], anchors[2])
    c2 = phase_aligned_cycle_path(closes, anchors[2], anchors[3], anchors[4])
    delta = c2 - c1
    raw_location = float(np.median(delta))
    normalized = raw_location / amp
    mad = float(np.median(np.abs(delta - raw_location))) / amp
    first_leg = float(np.median(delta[:GRID_POINTS_PER_LEG])) / amp
    second_leg = float(np.median(delta[GRID_POINTS_PER_LEG - 1 :])) / amp
    if not all(np.isfinite(x) for x in (normalized, mad, first_leg, second_leg)):
        raise AssertionError("PAWCT produced a non-finite result")
    eps = 1e-12
    pos = float(np.mean(delta > eps))
    neg = float(np.mean(delta < -eps))
    zero = max(0.0, 1.0 - pos - neg)
    return {
        "schema": "two_wave_parent_translation_v058@1.0",
        "grid_points_per_leg": GRID_POINTS_PER_LEG,
        "total_phase_points": TOTAL_PHASE_POINTS,
        "translation_raw_price": raw_location,
        "translation_in_amplitude_units": normalized,
        "translation_mad_in_amplitude_units": mad,
        "first_leg_median_translation": first_leg,
        "second_leg_median_translation": second_leg,
        "positive_phase_share": pos,
        "negative_phase_share": neg,
        "near_zero_phase_share": zero,
    }


def build_pawct_for_record(record: Mapping, bars: Sequence[Mapping]) -> dict:
    """Read one frozen selected record and compute PAWCT without changing it."""
    closes = [float(bar["close"]) for bar in bars]
    result = phase_aligned_translation_from_closes(
        closes,
        record["five_occurrence_bars"],
        float(record["amplitude_unit_price"]),
    )
    return {
        "record_id": record["record_id"],
        "phase": record["phase"],
        "start_time": str(record["start_time"]),
        "end_time": str(record["end_time"]),
        **result,
    }
