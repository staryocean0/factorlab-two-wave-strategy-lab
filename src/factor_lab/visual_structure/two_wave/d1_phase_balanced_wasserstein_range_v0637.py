"""v0.6.37 v0.6.25-preserving phase-balanced Wasserstein Range rescue."""
from __future__ import annotations

from typing import Sequence

import numpy as np
from scipy.stats import wasserstein_distance

from .d1_huber_erosion_consensus_v0623 import DECISIVE, SUPPORT_NAMES, endpoint_erosion_anchor_views
from .d1_huber_margin_rescue_v0625 import d1_primary_margin_rescue

SCHEMA = "two_wave_d1_phase_balanced_wasserstein_range@0.6.37"
RANGE_W1_MAX = 0.15
LEG_MASS = 0.5


def _phase_balanced_cycle(
    arr: np.ndarray, start: int, turn: int, end: int
) -> tuple[np.ndarray, np.ndarray, tuple[int, int]]:
    """Return duplicated phase observations with each leg carrying exactly half the mass."""
    leg1 = arr[start : turn + 1]
    leg2 = arr[turn : end + 1]
    if len(leg1) < 2 or len(leg2) < 2:
        raise ValueError("each completed leg requires at least two observations")
    if not np.all(np.isfinite(leg1)) or not np.all(np.isfinite(leg2)):
        raise ValueError("finite completed legs required")

    values = np.concatenate((leg1, leg2))
    weights = np.concatenate(
        (
            np.full(len(leg1), LEG_MASS / len(leg1), dtype=float),
            np.full(len(leg2), LEG_MASS / len(leg2), dtype=float),
        )
    )
    return values, weights, (len(leg1), len(leg2))


def phase_balanced_cycle_wasserstein_distance(
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
    c1, w1, c1_counts = _phase_balanced_cycle(arr, anchors[0], anchors[1], anchors[2])
    c2, w2, c2_counts = _phase_balanced_cycle(arr, anchors[2], anchors[3], anchors[4])

    raw = float(wasserstein_distance(c1, c2, u_weights=w1, v_weights=w2))
    normalized = raw / amp
    return {
        "phase_balanced_cycle_wasserstein_price": raw,
        "normalized_phase_balanced_cycle_wasserstein": float(normalized),
        "cycle_leg_observation_counts": {
            "cycle1": list(c1_counts),
            "cycle2": list(c2_counts),
        },
        "leg_probability_mass": LEG_MASS,
        "range_w1_max": RANGE_W1_MAX,
        "range_w1_pass": bool(normalized <= RANGE_W1_MAX),
    }


def erosion_phase_balanced_cycle_wasserstein(
    closes: Sequence[float], five_occurrence_bars: Sequence[int], amplitude_unit_price: float
) -> dict:
    views = endpoint_erosion_anchor_views(five_occurrence_bars)
    details = {}
    passes = {}
    for name in SUPPORT_NAMES:
        detail = phase_balanced_cycle_wasserstein_distance(closes, views[name], amplitude_unit_price)
        details[name] = detail
        passes[name] = bool(detail["range_w1_pass"])
    return {
        "support_phase_balanced_cycle_wasserstein": details,
        "support_range_w1_pass": passes,
        "all_supports_range_w1_pass": all(passes.values()),
        "max_normalized_phase_balanced_cycle_wasserstein": max(
            detail["normalized_phase_balanced_cycle_wasserstein"] for detail in details.values()
        ),
    }


def d1_primary_phase_balanced_wasserstein_range_rescue(
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
            "all_supports_range_w1_pass": None,
            "max_normalized_phase_balanced_cycle_wasserstein": None,
            "new_range_rescue_applied": False,
        }

    evidence = erosion_phase_balanced_cycle_wasserstein(
        closes, five_occurrence_bars, amplitude_unit_price
    )
    rescue = bool(evidence["all_supports_range_w1_pass"])
    return {
        **base,
        **evidence,
        "schema": SCHEMA,
        "v0625_classification": base_label,
        "classification": "range" if rescue else "uncertain",
        "decision_source": "v0637_phase_balanced_wasserstein_range"
        if rescue
        else "v0625_uncertain_phase_balanced_wasserstein_withheld",
        "new_range_rescue_applied": rescue,
        "D1_decisive_overridden": False,
        "future_outcome_used": False,
        "trade_authority": False,
    }
