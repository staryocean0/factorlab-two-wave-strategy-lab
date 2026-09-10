"""v0.6.23 D1-primary endpoint-erosion-consensus Huber rescue.

This is one causal single-view parent-state decision function.  It never
changes identity or qualification and never overrides a decisive D1 output.
For D1 uncertainty it reuses the frozen v0.6.21 Huber classifier on four fixed
support windows and requires unanimous decisive state before rescue.
"""
from __future__ import annotations

from typing import Sequence

from .whole_window_huber_direction_v0621 import classify_parent_window

SCHEMA = "two_wave_d1_huber_erosion_consensus_direction@0.6.23"
DECISIVE = frozenset({"range", "uptrend", "downtrend"})
VALID_D1 = DECISIVE | {"uncertain"}
SUPPORT_NAMES = ("full", "left_eroded_1", "right_eroded_1", "both_eroded_1")


def endpoint_erosion_anchor_views(five_occurrence_bars: Sequence[int]) -> dict[str, tuple[int, ...]]:
    anchors = tuple(int(x) for x in five_occurrence_bars)
    if len(anchors) != 5 or any(b <= a for a, b in zip(anchors, anchors[1:])):
        raise ValueError("five strictly increasing occurrence bars required")
    a0, a1, a2, a3, a4 = anchors
    views = {
        "full": anchors,
        "left_eroded_1": (a0 + 1, a1, a2, a3, a4),
        "right_eroded_1": (a0, a1, a2, a3, a4 - 1),
        "both_eroded_1": (a0 + 1, a1, a2, a3, a4 - 1),
    }
    for name, view in views.items():
        if any(b <= a for a, b in zip(view, view[1:])):
            raise ValueError(f"one-bar endpoint erosion collapses parent support: {name}")
    return views


def erosion_consensus_huber_state(
    closes: Sequence[float],
    five_occurrence_bars: Sequence[int],
    amplitude_unit_price: float,
) -> dict:
    views = endpoint_erosion_anchor_views(five_occurrence_bars)
    states: dict[str, str] = {}
    scores: dict[str, float] = {}
    for name in SUPPORT_NAMES:
        out = classify_parent_window(closes, views[name], amplitude_unit_price)
        states[name] = str(out["classification"])
        scores[name] = float(out["normalized_parent_drift"])
    unique = set(states.values())
    consensus = next(iter(unique)) if len(unique) == 1 and next(iter(unique)) in DECISIVE else "uncertain"
    return {
        "schema": SCHEMA,
        "support_states": states,
        "support_scores": scores,
        "erosion_consensus_state": consensus,
        "consensus_decisive": consensus in DECISIVE,
        "future_outcome_used": False,
        "trade_authority": False,
    }


def d1_primary_erosion_consensus_rescue(
    d1_label: str,
    closes: Sequence[float],
    five_occurrence_bars: Sequence[int],
    amplitude_unit_price: float,
) -> dict:
    d1 = str(d1_label)
    if d1 not in VALID_D1:
        raise ValueError(f"unsupported D1 label: {d1}")
    if d1 in DECISIVE:
        return {
            "schema": SCHEMA,
            "classification": d1,
            "decision_source": "D1",
            "D1_decisive_overridden": False,
            "rescue_applied": False,
            "erosion_consensus_state": None,
            "future_outcome_used": False,
            "trade_authority": False,
        }

    consensus = erosion_consensus_huber_state(closes, five_occurrence_bars, amplitude_unit_price)
    rescue = str(consensus["erosion_consensus_state"])
    applied = rescue in DECISIVE
    return {
        **consensus,
        "classification": rescue if applied else "uncertain",
        "decision_source": "v0623_erosion_consensus_Huber" if applied else "D1_uncertain_unrescued",
        "D1_decisive_overridden": False,
        "rescue_applied": applied,
    }
