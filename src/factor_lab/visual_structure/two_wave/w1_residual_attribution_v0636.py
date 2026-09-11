"""v0.6.36 read-only attribution helpers for v0.6.35 W1 residuals."""
from __future__ import annotations

from typing import Iterable

import numpy as np

SCHEMA = "two_wave_w1_residual_attribution@0.6.36"
BOUNDARY_SLACK = 0.03


def semantic_class(old_pair: tuple[str, str], new_pair: tuple[str, str]) -> str:
    old_exact = old_pair[0] == old_pair[1]
    new_exact = new_pair[0] == new_pair[1]
    if old_exact and not new_exact:
        return "introduced_harm"
    if not old_exact and new_exact:
        return "repaired_old_nonexact"
    if not old_exact and not new_exact:
        return "persistent_nonexact"
    return "retained_exact"


def summarize_slacks(values: Iterable[float]) -> dict:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return {
            "count": 0,
            "median": None,
            "q25": None,
            "q75": None,
            "fraction_le_0_03": None,
        }
    if not np.all(np.isfinite(arr)):
        raise ValueError("finite W1 slacks required")
    return {
        "count": int(arr.size),
        "median": float(np.median(arr)),
        "q25": float(np.quantile(arr, 0.25)),
        "q75": float(np.quantile(arr, 0.75)),
        "fraction_le_0_03": float(np.mean(arr <= BOUNDARY_SLACK)),
    }


def margin_authorized(group_stats: dict[str, dict]) -> tuple[bool, dict[str, bool]]:
    harm = group_stats.get("introduced_harm", {})
    repair = group_stats.get("repaired_old_nonexact", {})
    gates = {
        "introduced_harm_n_at_least_20": int(harm.get("count") or 0) >= 20,
        "repaired_n_at_least_20": int(repair.get("count") or 0) >= 20,
        "harm_median_at_least_0_03_smaller": False,
        "harm_near_boundary_fraction_at_least_70pct": False,
        "repair_near_boundary_fraction_at_most_40pct": False,
    }
    if harm.get("median") is not None and repair.get("median") is not None:
        gates["harm_median_at_least_0_03_smaller"] = float(harm["median"]) <= float(repair["median"]) - BOUNDARY_SLACK
    if harm.get("fraction_le_0_03") is not None:
        gates["harm_near_boundary_fraction_at_least_70pct"] = float(harm["fraction_le_0_03"]) >= 0.70
    if repair.get("fraction_le_0_03") is not None:
        gates["repair_near_boundary_fraction_at_most_40pct"] = float(repair["fraction_le_0_03"]) <= 0.40
    return all(gates.values()), gates
