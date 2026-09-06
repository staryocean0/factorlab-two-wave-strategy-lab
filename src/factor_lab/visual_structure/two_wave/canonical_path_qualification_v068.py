"""v0.6.8 audit-only canonical fine-path qualification representation.

Only the three frozen path reasons are recomputed on supplied 1m close paths.
No identity, non-path qualification metric, threshold, direction or outcome
logic is changed here.
"""
from __future__ import annotations

from typing import Sequence
import numpy as np

from .raw_projection_identity_v062 import CanonicalPathIndex, to_minutes

SCHEMA = "two_wave_canonical_path_qualification@0.6.8"
CANDIDATE = "supplied_1m_canonical_path_for_path_gates_v068"
PATH_REASONS = ("inefficient_leg", "jump_dominated_leg", "flat_dominated_leg")


def _leg_profile(start_time: object, end_time: object, index: CanonicalPathIndex) -> dict | None:
    lo_t, hi_t = to_minutes(start_time), to_minutes(end_time)
    if lo_t >= hi_t:
        raise ValueError("strictly increasing leg times required")
    lo = int(np.searchsorted(index.minutes, lo_t, side="left"))
    hi = int(np.searchsorted(index.minutes, hi_t, side="right"))
    if lo >= hi or hi - lo < 2:
        return None
    y = np.asarray(index.closes[lo:hi], dtype=float)
    changes = np.abs(np.diff(y))
    length = float(changes.sum())
    return {
        "rows": int(len(y)),
        "first_time": index.timestamps[lo],
        "last_time": index.timestamps[hi - 1],
        "start_endpoint_exact": to_minutes(index.timestamps[lo]) == lo_t,
        "end_endpoint_exact": to_minutes(index.timestamps[hi - 1]) == hi_t,
        "length": length,
        "efficiency": abs(float(y[-1] - y[0])) / length if length else 0.0,
        "jump_share": float(changes.max()) / length if length else 1.0,
        "flat_share": float(np.mean(changes == 0)),
    }


def canonical_path_profile(anchor_times: Sequence[object], index: CanonicalPathIndex) -> dict:
    if len(anchor_times) != 5:
        raise ValueError("five published anchor times required")
    legs = [_leg_profile(a, b, index) for a, b in zip(anchor_times, anchor_times[1:])]
    available = all(row is not None for row in legs)
    return {
        "schema": SCHEMA,
        "available": available,
        "legs": legs,
        "all_anchor_endpoints_exact": bool(
            available and all(row["start_endpoint_exact"] and row["end_endpoint_exact"] for row in legs)
        ),
    }


def candidate_path_reasons(profile: dict) -> list[str]:
    if not profile.get("available"):
        raise ValueError("available canonical path profile required")
    legs = profile["legs"]
    reasons: list[str] = []
    if min(float(row["efficiency"]) for row in legs) < 0.5:
        reasons.append("inefficient_leg")
    if max(float(row["jump_share"]) for row in legs) > 0.5:
        reasons.append("jump_dominated_leg")
    if max(float(row["flat_share"]) for row in legs) > 0.5:
        reasons.append("flat_dominated_leg")
    return reasons


def transform_control_qualification(control: dict, anchor_times: Sequence[object], index: CanonicalPathIndex) -> dict:
    """Replace only path reasons, preserving all frozen non-path audit values."""
    hard = [str(x) for x in control["v054_hard_rejection_reasons"]]
    non_path = [reason for reason in hard if reason not in PATH_REASONS]
    profile = canonical_path_profile(anchor_times, index)
    if not profile["available"]:
        return {
            "schema": SCHEMA,
            "candidate": CANDIDATE,
            "available": False,
            "candidate_hard_rejection_reasons": None,
            "scale_qualified": None,
            "canonical_path_profile": profile,
        }
    path = candidate_path_reasons(profile)
    candidate_hard = [*non_path, *path]
    return {
        "schema": SCHEMA,
        "candidate": CANDIDATE,
        "available": True,
        "control_hard_rejection_reasons": hard,
        "retained_non_path_hard_rejection_reasons": non_path,
        "candidate_path_rejection_reasons": path,
        "candidate_hard_rejection_reasons": candidate_hard,
        "scale_qualified": not candidate_hard,
        "canonical_path_profile": profile,
        "frozen_non_path_values": {
            "leg_durations": list(control["leg_durations"]),
            "cycle_durations": list(control["cycle_durations"]),
            "amplitude_ratio": control["amplitude_ratio"],
            "observed_trading_days": int(control["observed_trading_days"]),
            "wall_days": float(control["wall_days"]),
            "confirmation_delay_bars": int(control["confirmation_delay_bars"]),
        },
        "future_outcome_used": False,
        "trade_authority": False,
    }
