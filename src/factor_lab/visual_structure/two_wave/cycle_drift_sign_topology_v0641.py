"""Read-only v0.6.41 cycle-drift sign-topology helpers."""
from __future__ import annotations

import math
from collections import Counter
from typing import Iterable, Sequence

SCHEMA = "two_wave_cycle_drift_sign_topology@0.6.41"
NUMERIC_ZERO_EPS = 1e-12


def reconstruct_phase_steps(
    closes: Sequence[float], five_occurrence_bars: Sequence[int]
) -> list[float]:
    """Rebuild the frozen D1 phase steps from published pivots only.

    The v0.6.18 replay artifacts publish the five raw occurrence bars but omit
    the derived ``phase_steps_in_amplitude_units`` field.  This function uses
    exactly the frozen v0.4 D1 formula from ``same_scale_v04.evaluate_pair``;
    it does not redetect pivots, smooth prices, or introduce a new parameter.
    """
    ids = tuple(int(x) for x in five_occurrence_bars)
    if len(ids) != 5 or any(b <= a for a, b in zip(ids, ids[1:])):
        raise ValueError("five strictly increasing published occurrence bars required")
    if ids[0] < 0 or ids[-1] >= len(closes):
        raise ValueError("published occurrence bars outside supplied closes")

    x = [float(closes[i]) for i in ids]
    if not all(math.isfinite(v) for v in x):
        raise ValueError("finite published pivot closes required")

    legs = [b - a for a, b in zip(ids, ids[1:])]
    cycles = [ids[2] - ids[0], ids[4] - ids[2]]
    amplitudes = [
        abs(x[k + 1] - (x[k] + (x[k + 2] - x[k]) * legs[k] / cycles[k // 2]))
        for k in (0, 2)
    ]
    unit = sum(amplitudes) / 2.0
    if not math.isfinite(unit) or unit <= 0:
        raise ValueError("positive finite frozen amplitude unit required")

    return [
        float((x[2] - x[0]) / unit),
        float((x[4] - x[2]) / unit),
        float((x[3] - x[1]) / unit),
    ]


def strict_sign(value: float, *, eps: float = NUMERIC_ZERO_EPS) -> str:
    x = float(value)
    if not math.isfinite(x):
        raise ValueError("finite phase step required")
    if x > eps:
        return "positive"
    if x < -eps:
        return "negative"
    return "zero"


def cycle_drift_topology(phase_steps: Iterable[float]) -> dict:
    steps = tuple(float(x) for x in phase_steps)
    if len(steps) != 3 or not all(math.isfinite(x) for x in steps):
        raise ValueError("three finite phase steps required")
    s0, s1, s2 = steps
    signs = tuple(strict_sign(x) for x in steps)
    a, b, c = signs

    if "zero" in (a, b):
        relation = "contains_zero"
    elif a == b:
        relation = "same_direction"
    else:
        relation = "opposite_direction"

    all_three = a != "zero" and a == b == c
    if relation == "same_direction":
        if c == "zero":
            opposite_agrees = None
        else:
            opposite_agrees = c == a
    else:
        opposite_agrees = None

    return {
        "schema": SCHEMA,
        "phase_steps": [s0, s1, s2],
        "signs": list(signs),
        "cycle_drift_relation": relation,
        "all_three_same_direction": bool(all_three),
        "opposite_envelope_agrees_when_cycles_coherent": opposite_agrees,
        "future_outcome_used": False,
        "trade_authority": False,
    }


def categorical_summary(values: Iterable[str]) -> dict:
    vals = list(values)
    if not vals:
        raise ValueError("non-empty categorical values required")
    counts = Counter(vals)
    n = len(vals)
    return {
        "count": n,
        "counts": dict(sorted(counts.items())),
        "rates": {k: float(v / n) for k, v in sorted(counts.items())},
    }


def true_rate(values: Iterable[bool]) -> float:
    vals = [bool(v) for v in values]
    if not vals:
        raise ValueError("non-empty bool values required")
    return float(sum(vals) / len(vals))
