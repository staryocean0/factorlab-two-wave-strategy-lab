"""v0.6.29 D1-primary v0.6.25-preserving cycle-band Range rescue."""
from __future__ import annotations

from typing import Sequence

import numpy as np

from .d1_huber_erosion_consensus_v0623 import DECISIVE, erosion_consensus_huber_state
from .d1_huber_margin_rescue_v0625 import d1_primary_margin_rescue

SCHEMA = "two_wave_d1_cycle_band_range_rescue_direction@0.6.29"
MIN_IQR_OVERLAP = 0.50
EPS = 1e-12


def cycle_iqr_overlap(
    closes: Sequence[float], five_occurrence_bars: Sequence[int]
) -> dict:
    anchors = tuple(int(x) for x in five_occurrence_bars)
    if len(anchors) != 5 or any(b <= a for a, b in zip(anchors, anchors[1:])):
        raise ValueError("five strictly increasing occurrence bars required")
    if anchors[0] < 0 or anchors[-1] >= len(closes):
        raise ValueError("occurrence bars outside supplied closes")
    arr = np.asarray(closes, dtype=float)
    if not np.all(np.isfinite(arr[anchors[0] : anchors[-1] + 1])):
        raise ValueError("finite completed parent window required")

    c1 = arr[anchors[0] : anchors[2] + 1]
    c2 = arr[anchors[2] : anchors[4] + 1]
    q1 = np.quantile(c1, [0.25, 0.75], method="linear")
    q2 = np.quantile(c2, [0.25, 0.75], method="linear")
    w1 = float(q1[1] - q1[0])
    w2 = float(q2[1] - q2[0])
    if min(w1, w2) <= EPS:
        overlap = 0.0
    else:
        intersection = max(0.0, min(float(q1[1]), float(q2[1])) - max(float(q1[0]), float(q2[0])))
        overlap = intersection / min(w1, w2)
    return {
        "cycle1_q25": float(q1[0]),
        "cycle1_q75": float(q1[1]),
        "cycle2_q25": float(q2[0]),
        "cycle2_q75": float(q2[1]),
        "cycle1_iqr": w1,
        "cycle2_iqr": w2,
        "iqr_overlap_coefficient": float(overlap),
    }


def d1_primary_cycle_band_range_rescue(
    d1_label: str,
    closes: Sequence[float],
    five_occurrence_bars: Sequence[int],
    amplitude_unit_price: float,
) -> dict:
    base = d1_primary_margin_rescue(
        d1_label, closes, five_occurrence_bars, amplitude_unit_price
    )
    base_label = str(base["classification"])
    if base_label in DECISIVE:
        return {
            **base,
            "schema": SCHEMA,
            "v0625_classification": base_label,
            "classification": base_label,
            "cycle_band_checked": False,
            "cycle_band_overlap_coefficient": None,
            "cycle_band_overlap_gate_pass": None,
            "minimum_iqr_overlap": MIN_IQR_OVERLAP,
            "new_range_rescue_applied": False,
        }

    consensus = erosion_consensus_huber_state(
        closes, five_occurrence_bars, amplitude_unit_price
    )
    state = str(consensus["erosion_consensus_state"])
    if state != "range":
        return {
            **base,
            "schema": SCHEMA,
            "v0625_classification": base_label,
            "classification": "uncertain",
            "cycle_band_checked": False,
            "cycle_band_overlap_coefficient": None,
            "cycle_band_overlap_gate_pass": False,
            "minimum_iqr_overlap": MIN_IQR_OVERLAP,
            "new_range_rescue_applied": False,
        }

    band = cycle_iqr_overlap(closes, five_occurrence_bars)
    passed = float(band["iqr_overlap_coefficient"]) + EPS >= MIN_IQR_OVERLAP
    return {
        **base,
        **band,
        "schema": SCHEMA,
        "v0625_classification": base_label,
        "classification": "range" if passed else "uncertain",
        "decision_source": "v0629_cycle_band_range" if passed else "v0625_uncertain_cycle_band_withheld",
        "cycle_band_checked": True,
        "cycle_band_overlap_coefficient": float(band["iqr_overlap_coefficient"]),
        "cycle_band_overlap_gate_pass": passed,
        "minimum_iqr_overlap": MIN_IQR_OVERLAP,
        "new_range_rescue_applied": passed,
        "future_outcome_used": False,
        "trade_authority": False,
    }
