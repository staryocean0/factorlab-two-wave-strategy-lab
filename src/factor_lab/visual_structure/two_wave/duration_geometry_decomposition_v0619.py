"""v0.6.19 read-only duration-geometry disagreement decomposition.

This helper changes no recognizer or qualification rule. It classifies the
remaining v0.6.18 qualification disagreements and computes preregistered
one-native-bar boundary diagnostics from already-published raw identities.
"""
from __future__ import annotations

from typing import Sequence

SCHEMA = "two_wave_duration_geometry_decomposition@0.6.19"

LOCAL_DURATION_REASONS = frozenset({"short_leg", "short_cycle", "cycle_duration_mismatch"})
AMPLITUDE_REASONS = frozenset({"amplitude_mismatch"})
CONFIRMATION_REASONS = frozenset({"confirmation_too_late"})
LONG_SPAN_REASONS = frozenset({"long_cycle", "long_pair", "too_many_observed_days", "wall_span_too_long"})

FAMILIES = {
    "local_duration": LOCAL_DURATION_REASONS,
    "amplitude": AMPLITUDE_REASONS,
    "confirmation": CONFIRMATION_REASONS,
    "long_span": LONG_SPAN_REASONS,
}
KNOWN_REASONS = frozenset().union(*FAMILIES.values())


def duration_metrics(five_raw_occurrence_bars: Sequence[int]) -> dict:
    raw = tuple(int(x) for x in five_raw_occurrence_bars)
    if len(raw) != 5 or any(b <= a for a, b in zip(raw, raw[1:])):
        raise ValueError("five strictly increasing raw bars required")
    legs = tuple(b - a for a, b in zip(raw, raw[1:]))
    cycles = (raw[2] - raw[0], raw[4] - raw[2])
    return {
        "legs": list(legs),
        "cycles": list(cycles),
        "min_leg": min(legs),
        "min_cycle": min(cycles),
        "cycle_duration_ratio": max(cycles) / min(cycles),
    }


def classify_rejected_reasons(reasons: Sequence[str]) -> dict:
    reason_set = frozenset(str(x) for x in reasons)
    if not reason_set:
        raise ValueError("rejected side must have at least one hard reason")
    unknown = sorted(reason_set - KNOWN_REASONS)
    if unknown:
        raise ValueError(f"unknown v0.6.18 hard reasons: {unknown}")
    involved = tuple(name for name, members in FAMILIES.items() if reason_set & members)
    if len(involved) == 1 and reason_set <= FAMILIES[involved[0]]:
        primary = f"{involved[0]}_only"
    else:
        primary = "mixed_multi_family"
    return {
        "primary_family": primary,
        "involved_families": list(involved),
        "hard_reasons": sorted(reason_set),
    }


def local_duration_boundary_diagnostics(
    rejected_raw_bars: Sequence[int],
    qualified_raw_bars: Sequence[int],
    rejected_reasons: Sequence[str],
) -> dict:
    rejected = duration_metrics(rejected_raw_bars)
    qualified = duration_metrics(qualified_raw_bars)
    local = frozenset(str(x) for x in rejected_reasons) & LOCAL_DURATION_REASONS

    flags: dict[str, bool] = {}
    if "short_leg" in local:
        flags["short_leg_one_bar_boundary"] = (
            rejected["min_leg"] == 3 and qualified["min_leg"] >= 4
        )
    if "short_cycle" in local:
        flags["short_cycle_one_bar_boundary"] = (
            rejected["min_cycle"] == 11 and qualified["min_cycle"] >= 12
        )
    if "cycle_duration_mismatch" in local:
        flags["cycle_ratio_one_bar_boundary"] = (
            rejected["cycle_duration_ratio"] > 2.0
            and qualified["cycle_duration_ratio"] <= 2.0
            and all(abs(a - b) <= 1 for a, b in zip(rejected["cycles"], qualified["cycles"]))
        )

    return {
        "rejected": rejected,
        "qualified": qualified,
        "local_duration_reasons": sorted(local),
        "max_abs_leg_duration_delta": max(
            abs(a - b) for a, b in zip(rejected["legs"], qualified["legs"])
        ),
        "max_abs_cycle_duration_delta": max(
            abs(a - b) for a, b in zip(rejected["cycles"], qualified["cycles"])
        ),
        "boundary_flags": flags,
        "simple_one_bar_boundary_case": bool(local) and all(flags.values()),
    }


def interpretation_category(total_disagreements: int, local_involved: int, local_only: int, local_only_simple: int) -> str:
    if total_disagreements <= 0:
        raise ValueError("positive disagreement denominator required")
    involved_fraction = local_involved / total_disagreements
    simple_fraction = local_only_simple / local_only if local_only else 0.0
    if involved_fraction >= 0.50:
        if simple_fraction >= 0.60:
            return "v0619_local_duration_boundary_sensitivity_dominant"
        return "v0619_local_duration_geometry_material_not_simple_boundary"
    return "v0619_duration_not_dominant_after_v0618"
