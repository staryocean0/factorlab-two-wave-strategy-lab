"""v0.6.31 D1-primary v0.6.25-preserving mutual-median Range rescue."""
from __future__ import annotations

from typing import Sequence

import numpy as np

from .d1_huber_erosion_consensus_v0623 import (
    DECISIVE,
    SUPPORT_NAMES,
    endpoint_erosion_anchor_views,
    erosion_consensus_huber_state,
)
from .d1_huber_margin_rescue_v0625 import d1_primary_margin_rescue
from .d1_huber_state_relative_margin_v0627 import (
    state_relative_margin_pass,
    state_relative_margin_requirement,
)
from .v0623_residual_attribution_v0624 import consensus_margin_and_span

SCHEMA = "two_wave_d1_mutual_median_range_rescue_direction@0.6.31"
EPS = 1e-12


def cycle_mutual_median_containment(
    closes: Sequence[float], five_occurrence_bars: Sequence[int]
) -> dict:
    anchors = tuple(int(x) for x in five_occurrence_bars)
    if len(anchors) != 5 or any(b <= a for a, b in zip(anchors, anchors[1:])):
        raise ValueError("five strictly increasing occurrence bars required")
    if anchors[0] < 0 or anchors[-1] >= len(closes):
        raise ValueError("occurrence bars outside supplied closes")
    arr = np.asarray(closes, dtype=float)
    parent = arr[anchors[0] : anchors[-1] + 1]
    if len(parent) < 5 or not np.all(np.isfinite(parent)):
        raise ValueError("finite completed parent window required")

    c1 = arr[anchors[0] : anchors[2] + 1]
    c2 = arr[anchors[2] : anchors[4] + 1]
    q1 = np.quantile(c1, [0.25, 0.50, 0.75], method="linear")
    q2 = np.quantile(c2, [0.25, 0.50, 0.75], method="linear")
    w1 = float(q1[2] - q1[0])
    w2 = float(q2[2] - q2[0])
    valid = min(w1, w2) > EPS
    c1_median_in_c2_iqr = valid and float(q2[0]) <= float(q1[1]) <= float(q2[2])
    c2_median_in_c1_iqr = valid and float(q1[0]) <= float(q2[1]) <= float(q1[2])
    passed = bool(c1_median_in_c2_iqr and c2_median_in_c1_iqr)
    return {
        "cycle1_q25": float(q1[0]),
        "cycle1_median": float(q1[1]),
        "cycle1_q75": float(q1[2]),
        "cycle2_q25": float(q2[0]),
        "cycle2_median": float(q2[1]),
        "cycle2_q75": float(q2[2]),
        "cycle1_iqr": w1,
        "cycle2_iqr": w2,
        "cycle1_median_in_cycle2_iqr": bool(c1_median_in_c2_iqr),
        "cycle2_median_in_cycle1_iqr": bool(c2_median_in_c1_iqr),
        "mutual_median_containment": passed,
    }


def erosion_mutual_median_containment(
    closes: Sequence[float], five_occurrence_bars: Sequence[int]
) -> dict:
    views = endpoint_erosion_anchor_views(five_occurrence_bars)
    support_pass: dict[str, bool] = {}
    support_details: dict[str, dict] = {}
    for name in SUPPORT_NAMES:
        detail = cycle_mutual_median_containment(closes, views[name])
        support_details[name] = detail
        support_pass[name] = bool(detail["mutual_median_containment"])
    return {
        "support_mutual_median_containment": support_pass,
        "support_containment_details": support_details,
        "all_supports_mutual_median_containment": all(support_pass.values()),
    }


def d1_primary_mutual_median_range_rescue(
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
            "range_consensus": None,
            "range_margin": None,
            "range_margin_requirement": state_relative_margin_requirement("range"),
            "range_margin_gate_pass": None,
            "all_supports_mutual_median_containment": None,
            "new_range_rescue_applied": False,
        }

    consensus = erosion_consensus_huber_state(
        closes, five_occurrence_bars, amplitude_unit_price
    )
    state = str(consensus["erosion_consensus_state"])
    if state != "range":
        return {
            **base,
            **consensus,
            "schema": SCHEMA,
            "v0625_classification": base_label,
            "classification": "uncertain",
            "range_consensus": False,
            "range_margin": None,
            "range_margin_requirement": state_relative_margin_requirement("range"),
            "range_margin_gate_pass": False,
            "all_supports_mutual_median_containment": False,
            "new_range_rescue_applied": False,
        }

    robust = consensus_margin_and_span(
        consensus["support_states"], consensus["support_scores"], state
    )
    margin = float(robust["consensus_margin_to_frozen_boundary"])
    margin_pass = state_relative_margin_pass("range", margin)
    containment = erosion_mutual_median_containment(closes, five_occurrence_bars)
    containment_pass = bool(containment["all_supports_mutual_median_containment"])
    rescue = bool(margin_pass and containment_pass)

    return {
        **base,
        **consensus,
        **robust,
        **containment,
        "schema": SCHEMA,
        "v0625_classification": base_label,
        "classification": "range" if rescue else "uncertain",
        "decision_source": "v0631_mutual_median_range" if rescue else "v0625_uncertain_mutual_median_withheld",
        "range_consensus": True,
        "range_margin": margin,
        "range_margin_requirement": state_relative_margin_requirement("range"),
        "range_margin_gate_pass": bool(margin_pass),
        "new_range_rescue_applied": rescue,
        "future_outcome_used": False,
        "trade_authority": False,
    }
