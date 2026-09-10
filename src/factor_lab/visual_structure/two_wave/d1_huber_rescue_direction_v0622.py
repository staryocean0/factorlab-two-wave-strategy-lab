"""v0.6.22 D1-primary Huber-rescue parent-state decision.

The rule is intentionally minimal: never override a decisive D1 state; use the
frozen v0.6.21 whole-window Huber label only when D1 abstains.
"""
from __future__ import annotations

VALID = frozenset({"range", "uptrend", "downtrend", "uncertain"})
DECISIVE = frozenset({"range", "uptrend", "downtrend"})
SCHEMA = "two_wave_d1_huber_rescue_direction@0.6.22"


def rescue_direction(d1_label: str, huber_label: str) -> dict:
    d1 = str(d1_label)
    huber = str(huber_label)
    if d1 not in VALID or huber not in VALID:
        raise ValueError("unknown direction label")
    if d1 in DECISIVE:
        output = d1
        source = "D1_primary"
    elif huber in DECISIVE:
        output = huber
        source = "Huber_rescue"
    else:
        output = "uncertain"
        source = "abstain"
    return {
        "schema": SCHEMA,
        "D1": d1,
        "Huber": huber,
        "classification": output,
        "source": source,
        "D1_decisive_overridden": bool(d1 in DECISIVE and output != d1),
        "future_outcome_used": False,
        "trade_authority": False,
    }
