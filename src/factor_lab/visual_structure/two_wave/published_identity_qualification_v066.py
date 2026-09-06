"""v0.6.6 audit-only qualification of immutable v0.6.5 published raw identity."""
from __future__ import annotations

import math
from typing import Sequence

from .models import stable_id
from .same_scale_v04 import evaluate_pair
from .same_scale_v043 import MaturityConfig

SCHEMA = "two_wave_published_identity_qualification@0.6.6"
DIAGNOSTIC_ONLY_REASON = "corresponding_leg_duration_mismatch"


def v054_hard_reasons(v043_reasons: Sequence[str]) -> list[str]:
    return [str(reason) for reason in v043_reasons if str(reason) != DIAGNOSTIC_ONLY_REASON]


def qualify_published_raw_identity(
    phase: str,
    five_raw_occurrence_bars: Sequence[int],
    publishing_confirmation_bar: int,
    bars: Sequence[dict],
    cfg: MaturityConfig | None = None,
) -> dict:
    if phase not in {"low", "high"}:
        raise ValueError("phase must be low or high")
    raw = tuple(int(x) for x in five_raw_occurrence_bars)
    if len(raw) != 5 or any(b <= a for a, b in zip(raw, raw[1:])):
        raise ValueError("five strictly increasing raw occurrence bars required")
    confirmation = int(publishing_confirmation_bar)
    if raw[0] < 0 or raw[-1] >= len(bars) or confirmation < raw[-1] or confirmation >= len(bars):
        raise ValueError("published anchors/confirmation outside supplied bars")
    cfg = cfg or MaturityConfig()
    kinds = [phase, "high" if phase == "low" else "low", phase, "high" if phase == "low" else "low", phase]
    confirmation_time = str(bars[confirmation]["timestamp"])
    points = []
    for ordinal, (kind, occurrence) in enumerate(zip(kinds, raw)):
        price = float(bars[occurrence]["close"])
        if not math.isfinite(price) or price <= 0:
            raise ValueError("published raw close must be finite positive")
        points.append(
            {
                "kind": kind,
                "occurrence_bar": occurrence,
                "occurrence_time": str(bars[occurrence]["timestamp"]),
                "price": price,
                "log_price": math.log(price),
                "left_censored": False,
                "confirmation_bar": confirmation,
                "confirmation_time": confirmation_time,
                "bar_end_assumed": False,
                "pivot_id": stable_id(
                    "v066_published_raw_pivot",
                    [cfg.timeframe, phase, list(raw), confirmation, ordinal, occurrence, price],
                ),
            }
        )
    record = evaluate_pair(points, list(bars), cfg, source="v065_published_raw_identity_v066_audit")
    v043 = [str(x) for x in record["scale_rejection_reasons"]]
    hard = v054_hard_reasons(v043)
    return {
        "schema": SCHEMA,
        "phase": phase,
        "five_raw_occurrence_bars": list(raw),
        "publishing_confirmation_bar": confirmation,
        "v043_scale_rejection_reasons": v043,
        "v054_hard_rejection_reasons": hard,
        "corresponding_leg_duration_diagnostic_triggered": DIAGNOSTIC_ONLY_REASON in v043,
        "scale_qualified": not hard,
        "leg_durations": list(record["leg_durations"]),
        "cycle_durations": list(record["cycle_durations"]),
        "amplitude_ratio": record["amplitude_ratio"],
        "leg_efficiencies": [float(x["efficiency"]) for x in record["leg_paths"]],
        "leg_jump_shares": [float(x["jump_share"]) for x in record["leg_paths"]],
        "leg_flat_shares": [float(x["flat_share"]) for x in record["leg_paths"]],
        "observed_trading_days": int(record["observed_trading_days"]),
        "wall_days": float(record["wall_days"]),
        "confirmation_delay_bars": int(record["confirmation_delay_bars"]),
        "future_outcome_used": False,
        "trade_authority": False,
    }
