"""Read-only v0.6.41 cycle-drift sign-topology helpers."""
from __future__ import annotations

import math
from collections import Counter
from typing import Iterable

SCHEMA = "two_wave_cycle_drift_sign_topology@0.6.41"
NUMERIC_ZERO_EPS = 1e-12


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
