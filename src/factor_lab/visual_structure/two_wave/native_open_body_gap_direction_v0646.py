"""v0.6.46 read-only native open/body/gap direction descriptors.

The five parent anchors, phase and qualification are frozen upstream from close
pivots. This module never moves an anchor and never classifies. It reads native
open/close and the immediately preceding observed close on those fixed bars.
"""
from __future__ import annotations

import math
from typing import Mapping, Sequence

SCHEMA = "two_wave_native_open_body_gap_direction@0.6.46"


def _l1_distance(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or not a:
        raise ValueError("aligned non-empty vectors required")
    return float(sum(abs(float(x) - float(y)) for x, y in zip(a, b)) / len(a))


def anchor_kinds(phase: str) -> tuple[str, ...]:
    p = str(phase)
    if p not in {"low", "high"}:
        raise ValueError("phase must be low or high")
    other = "high" if p == "low" else "low"
    return (p, other, p, other, p)


def open_anchor_metrics(
    bars: Sequence[Mapping[str, object]],
    five_occurrence_bars: Sequence[int],
    phase: str,
    amplitude_unit_price: float,
) -> dict:
    """Measure native open/body/gap geometry on frozen parent anchors only."""
    anchors = tuple(int(x) for x in five_occurrence_bars)
    if len(anchors) != 5 or any(b <= a for a, b in zip(anchors, anchors[1:])):
        raise ValueError("five strictly increasing frozen occurrence bars required")
    if anchors[0] <= 0 or anchors[-1] >= len(bars):
        raise ValueError("every frozen anchor requires an immediately preceding observed row")
    amp = float(amplitude_unit_price)
    if not math.isfinite(amp) or amp <= 0:
        raise ValueError("positive finite amplitude unit required")

    kinds = anchor_kinds(phase)
    opens: list[float] = []
    closes: list[float] = []
    bodies: list[float] = []
    oriented_bodies: list[float] = []
    gaps: list[float] = []

    for kind, idx in zip(kinds, anchors):
        row = bars[idx]
        prev = bars[idx - 1]
        op = float(row["open"])
        close = float(row["close"])
        prev_close = float(prev["close"])
        if not all(math.isfinite(v) for v in (op, close, prev_close)):
            raise ValueError("finite open/close/preceding-close required")
        if min(op, close, prev_close) <= 0:
            raise ValueError("positive prices required")
        body = (close - op) / amp
        orient = -1.0 if kind == "low" else 1.0
        oriented = orient * body
        gap = (op - prev_close) / amp
        opens.append(op)
        closes.append(close)
        bodies.append(float(body))
        oriented_bodies.append(float(oriented))
        gaps.append(float(gap))

    close_steps = [
        (closes[2] - closes[0]) / amp,
        (closes[4] - closes[2]) / amp,
        (closes[3] - closes[1]) / amp,
    ]
    open_steps = [
        (opens[2] - opens[0]) / amp,
        (opens[4] - opens[2]) / amp,
        (opens[3] - opens[1]) / amp,
    ]
    adjustment = [o - c for o, c in zip(open_steps, close_steps)]

    return {
        "schema": SCHEMA,
        "phase": str(phase),
        "five_occurrence_bars": list(anchors),
        "anchor_kinds": list(kinds),
        "amplitude_unit_price": amp,
        "anchor_open_prices": opens,
        "anchor_close_prices": closes,
        "anchor_body_in_amplitude_units": bodies,
        "anchor_oriented_body_in_amplitude_units": oriented_bodies,
        "anchor_gap_in_amplitude_units": gaps,
        "mean_abs_anchor_body": float(sum(abs(x) for x in bodies) / len(bodies)),
        "max_abs_anchor_body": float(max(abs(x) for x in bodies)),
        "mean_oriented_anchor_body": float(sum(oriented_bodies) / len(oriented_bodies)),
        "positive_oriented_body_fraction": float(sum(x > 0 for x in oriented_bodies) / len(oriented_bodies)),
        "mean_abs_anchor_gap": float(sum(abs(x) for x in gaps) / len(gaps)),
        "max_abs_anchor_gap": float(max(abs(x) for x in gaps)),
        "close_phase_steps_in_amplitude_units": [float(x) for x in close_steps],
        "open_phase_steps_in_amplitude_units": [float(x) for x in open_steps],
        "open_adjustment_vector": [float(x) for x in adjustment],
        "open_adjustment_l1": float(sum(abs(x) for x in adjustment) / len(adjustment)),
        "open_adjustment_linf": float(max(abs(x) for x in adjustment)),
        "close_migration_l1": float(sum(abs(x) for x in close_steps) / len(close_steps)),
        "open_migration_l1": float(sum(abs(x) for x in open_steps) / len(open_steps)),
        "future_outcome_used": False,
        "trade_authority": False,
    }


def harmless_pair_metrics(main: Mapping[str, object], other: Mapping[str, object]) -> dict:
    """Compare matched harmless views; comparison identity is never runtime input."""
    main_close = tuple(float(x) for x in main["close_phase_steps_in_amplitude_units"])
    other_close = tuple(float(x) for x in other["close_phase_steps_in_amplitude_units"])
    main_open = tuple(float(x) for x in main["open_phase_steps_in_amplitude_units"])
    other_open = tuple(float(x) for x in other["open_phase_steps_in_amplitude_units"])
    main_adj = tuple(float(x) for x in main["open_adjustment_vector"])
    other_adj = tuple(float(x) for x in other["open_adjustment_vector"])

    close_distance = _l1_distance(main_close, other_close)
    open_distance = _l1_distance(main_open, other_open)
    return {
        "close_step_view_distance_l1": close_distance,
        "open_step_view_distance_l1": open_distance,
        "open_stability_gain_l1": float(close_distance - open_distance),
        "open_adjustment_view_distance_l1": _l1_distance(main_adj, other_adj),
        "mean_abs_body_view_delta": abs(float(main["mean_abs_anchor_body"]) - float(other["mean_abs_anchor_body"])),
        "mean_oriented_body_view_delta": abs(float(main["mean_oriented_anchor_body"]) - float(other["mean_oriented_anchor_body"])),
        "mean_abs_gap_view_delta": abs(float(main["mean_abs_anchor_gap"]) - float(other["mean_abs_anchor_gap"])),
        "comparison_offsets_runtime_information": False,
    }
