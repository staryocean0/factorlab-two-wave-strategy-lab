"""v0.6.44 read-only native high/low envelope direction descriptors.

The five parent anchors and their phases are frozen upstream from close pivots.
This module never moves an anchor and never infers intrabar event order. It only
reads the same-bar phase-consistent high/low extreme after the bar is complete.
"""
from __future__ import annotations

import math
from typing import Mapping, Sequence

SCHEMA = "two_wave_native_high_low_envelope_direction@0.6.44"


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


def envelope_anchor_metrics(
    bars: Sequence[Mapping[str, object]],
    five_occurrence_bars: Sequence[int],
    phase: str,
    amplitude_unit_price: float,
) -> dict:
    """Measure same-bar outward excursion and close-vs-envelope migration.

    All indices are frozen close-pivot occurrence bars. High/low are observed on
    those exact bars only; no re-detection, interpolation, or intrabar ordering
    is performed.
    """
    anchors = tuple(int(x) for x in five_occurrence_bars)
    if len(anchors) != 5 or any(b <= a for a, b in zip(anchors, anchors[1:])):
        raise ValueError("five strictly increasing frozen occurrence bars required")
    if anchors[0] < 0 or anchors[-1] >= len(bars):
        raise ValueError("frozen occurrence bars outside supplied bars")
    amp = float(amplitude_unit_price)
    if not math.isfinite(amp) or amp <= 0:
        raise ValueError("positive finite amplitude unit required")

    kinds = anchor_kinds(phase)
    closes: list[float] = []
    extremes: list[float] = []
    excursions: list[float] = []

    for kind, idx in zip(kinds, anchors):
        row = bars[idx]
        close = float(row["close"])
        high = float(row["high"])
        low = float(row["low"])
        if not all(math.isfinite(v) for v in (close, high, low)):
            raise ValueError("finite close/high/low required")
        if low > close or high < close or low > high:
            raise ValueError("valid native high/low envelope required")
        extreme = low if kind == "low" else high
        outward = abs(extreme - close) / amp
        closes.append(close)
        extremes.append(extreme)
        excursions.append(float(outward))

    close_steps = [
        (closes[2] - closes[0]) / amp,
        (closes[4] - closes[2]) / amp,
        (closes[3] - closes[1]) / amp,
    ]
    envelope_steps = [
        (extremes[2] - extremes[0]) / amp,
        (extremes[4] - extremes[2]) / amp,
        (extremes[3] - extremes[1]) / amp,
    ]
    adjustment = [e - c for e, c in zip(envelope_steps, close_steps)]

    return {
        "schema": SCHEMA,
        "phase": str(phase),
        "five_occurrence_bars": list(anchors),
        "anchor_kinds": list(kinds),
        "amplitude_unit_price": amp,
        "anchor_close_prices": closes,
        "anchor_envelope_prices": extremes,
        "anchor_outward_excursions": excursions,
        "mean_anchor_outward_excursion": float(sum(excursions) / len(excursions)),
        "max_anchor_outward_excursion": float(max(excursions)),
        "close_phase_steps_in_amplitude_units": [float(x) for x in close_steps],
        "envelope_phase_steps_in_amplitude_units": [float(x) for x in envelope_steps],
        "envelope_adjustment_vector": [float(x) for x in adjustment],
        "envelope_adjustment_l1": float(sum(abs(x) for x in adjustment) / len(adjustment)),
        "envelope_adjustment_linf": float(max(abs(x) for x in adjustment)),
        "close_migration_l1": float(sum(abs(x) for x in close_steps) / len(close_steps)),
        "envelope_migration_l1": float(sum(abs(x) for x in envelope_steps) / len(envelope_steps)),
        "future_outcome_used": False,
        "trade_authority": False,
    }


def harmless_pair_metrics(main: Mapping[str, object], other: Mapping[str, object]) -> dict:
    """Compare two already matched harmless views without creating a runtime input."""
    main_close = tuple(float(x) for x in main["close_phase_steps_in_amplitude_units"])
    other_close = tuple(float(x) for x in other["close_phase_steps_in_amplitude_units"])
    main_env = tuple(float(x) for x in main["envelope_phase_steps_in_amplitude_units"])
    other_env = tuple(float(x) for x in other["envelope_phase_steps_in_amplitude_units"])
    main_adj = tuple(float(x) for x in main["envelope_adjustment_vector"])
    other_adj = tuple(float(x) for x in other["envelope_adjustment_vector"])

    close_distance = _l1_distance(main_close, other_close)
    envelope_distance = _l1_distance(main_env, other_env)
    adjustment_distance = _l1_distance(main_adj, other_adj)
    mean_excursion_delta = abs(
        float(main["mean_anchor_outward_excursion"])
        - float(other["mean_anchor_outward_excursion"])
    )
    return {
        "close_step_view_distance_l1": close_distance,
        "envelope_step_view_distance_l1": envelope_distance,
        "envelope_stability_gain_l1": float(close_distance - envelope_distance),
        "envelope_adjustment_view_distance_l1": adjustment_distance,
        "mean_anchor_excursion_view_delta": float(mean_excursion_delta),
        "comparison_offsets_runtime_information": False,
    }
