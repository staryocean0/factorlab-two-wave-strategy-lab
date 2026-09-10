"""v0.6.33 v0.6.25-preserving two-cycle median-shift Range rescue."""
from __future__ import annotations

from typing import Sequence

import numpy as np

from .d1_huber_erosion_consensus_v0623 import DECISIVE, SUPPORT_NAMES, endpoint_erosion_anchor_views
from .d1_huber_margin_rescue_v0625 import d1_primary_margin_rescue

SCHEMA = "two_wave_d1_two_cycle_median_shift_range@0.6.33"
RANGE_LOCATION_SHIFT_MAX = 0.15


def cycle_median_shift(
    closes: Sequence[float], five_occurrence_bars: Sequence[int], amplitude_unit_price: float
) -> dict:
    anchors = tuple(int(x) for x in five_occurrence_bars)
    if len(anchors) != 5 or any(b <= a for a, b in zip(anchors, anchors[1:])):
        raise ValueError("five strictly increasing occurrence bars required")
    if anchors[0] < 0 or anchors[-1] >= len(closes):
        raise ValueError("occurrence bars outside supplied closes")
    amp = float(amplitude_unit_price)
    if not np.isfinite(amp) or amp <= 0:
        raise ValueError("positive finite amplitude unit required")
    arr = np.asarray(closes, dtype=float)
    c1 = arr[anchors[0] : anchors[2] + 1]
    c2 = arr[anchors[2] : anchors[4] + 1]
    if len(c1) < 2 or len(c2) < 2 or not np.all(np.isfinite(c1)) or not np.all(np.isfinite(c2)):
        raise ValueError("finite completed cycles required")
    m1 = float(np.median(c1))
    m2 = float(np.median(c2))
    shift = abs(m2 - m1) / amp
    return {
        "cycle1_median_price": m1,
        "cycle2_median_price": m2,
        "normalized_cycle_median_shift": float(shift),
        "range_location_shift_max": RANGE_LOCATION_SHIFT_MAX,
        "range_location_pass": bool(shift <= RANGE_LOCATION_SHIFT_MAX),
    }


def erosion_cycle_median_shift(
    closes: Sequence[float], five_occurrence_bars: Sequence[int], amplitude_unit_price: float
) -> dict:
    views = endpoint_erosion_anchor_views(five_occurrence_bars)
    details = {}
    passes = {}
    for name in SUPPORT_NAMES:
        detail = cycle_median_shift(closes, views[name], amplitude_unit_price)
        details[name] = detail
        passes[name] = bool(detail["range_location_pass"])
    return {
        "support_cycle_median_shift": details,
        "support_range_location_pass": passes,
        "all_supports_range_location_pass": all(passes.values()),
        "max_normalized_cycle_median_shift": max(
            detail["normalized_cycle_median_shift"] for detail in details.values()
        ),
    }


def d1_primary_two_cycle_median_shift_range_rescue(
    d1_label: str,
    closes: Sequence[float],
    five_occurrence_bars: Sequence[int],
    amplitude_unit_price: float,
) -> dict:
    base = d1_primary_margin_rescue(d1_label, closes, five_occurrence_bars, amplitude_unit_price)
    base_label = str(base["classification"])
    if base_label in DECISIVE:
        return {
            **base,
            "schema": SCHEMA,
            "v0625_classification": base_label,
            "classification": base_label,
            "all_supports_range_location_pass": None,
            "max_normalized_cycle_median_shift": None,
            "new_range_rescue_applied": False,
        }
    measurement = erosion_cycle_median_shift(closes, five_occurrence_bars, amplitude_unit_price)
    rescue = bool(measurement["all_supports_range_location_pass"])
    return {
        **base,
        **measurement,
        "schema": SCHEMA,
        "v0625_classification": base_label,
        "classification": "range" if rescue else "uncertain",
        "decision_source": "v0633_two_cycle_median_shift_range" if rescue else "v0625_uncertain_median_shift_withheld",
        "new_range_rescue_applied": rescue,
        "D1_decisive_overridden": False,
        "future_outcome_used": False,
        "trade_authority": False,
    }
