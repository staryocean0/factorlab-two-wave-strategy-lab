"""v0.6.34 v0.6.25-preserving direct two-cycle Range distribution intersection."""
from __future__ import annotations

from typing import Sequence

from .d1_cycle_band_range_rescue_v0629 import MIN_IQR_OVERLAP, cycle_iqr_overlap
from .d1_huber_erosion_consensus_v0623 import DECISIVE, SUPPORT_NAMES, endpoint_erosion_anchor_views
from .d1_huber_margin_rescue_v0625 import d1_primary_margin_rescue
from .d1_two_cycle_median_shift_range_v0633 import RANGE_LOCATION_SHIFT_MAX, cycle_median_shift

SCHEMA = "two_wave_d1_two_cycle_distribution_intersection@0.6.34"
EPS = 1e-12


def erosion_two_cycle_distribution_evidence(
    closes: Sequence[float], five_occurrence_bars: Sequence[int], amplitude_unit_price: float
) -> dict:
    views = endpoint_erosion_anchor_views(five_occurrence_bars)
    details = {}
    support_pass = {}
    for name in SUPPORT_NAMES:
        shift = cycle_median_shift(closes, views[name], amplitude_unit_price)
        overlap = cycle_iqr_overlap(closes, views[name])
        passed = bool(
            shift["normalized_cycle_median_shift"] <= RANGE_LOCATION_SHIFT_MAX
            and overlap["iqr_overlap_coefficient"] + EPS >= MIN_IQR_OVERLAP
        )
        details[name] = {
            "normalized_cycle_median_shift": float(shift["normalized_cycle_median_shift"]),
            "iqr_overlap_coefficient": float(overlap["iqr_overlap_coefficient"]),
            "location_shift_pass": bool(shift["range_location_pass"]),
            "iqr_overlap_pass": bool(overlap["iqr_overlap_coefficient"] + EPS >= MIN_IQR_OVERLAP),
            "joint_pass": passed,
        }
        support_pass[name] = passed
    return {
        "support_distribution_evidence": details,
        "support_distribution_pass": support_pass,
        "all_supports_distribution_pass": all(support_pass.values()),
        "range_location_shift_max": RANGE_LOCATION_SHIFT_MAX,
        "minimum_iqr_overlap": MIN_IQR_OVERLAP,
    }


def d1_primary_two_cycle_distribution_range_rescue(
    d1_label: str,
    closes: Sequence[float],
    five_occurrence_bars: Sequence[int],
    amplitude_unit_price: float,
) -> dict:
    base = d1_primary_margin_rescue(d1_label, closes, five_occurrence_bars, amplitude_unit_price)
    base_label = str(base["classification"])
    if base_label in DECISIVE:
        return {
            **base,
            "schema": SCHEMA,
            "v0625_classification": base_label,
            "classification": base_label,
            "all_supports_distribution_pass": None,
            "new_range_rescue_applied": False,
        }
    evidence = erosion_two_cycle_distribution_evidence(
        closes, five_occurrence_bars, amplitude_unit_price
    )
    rescue = bool(evidence["all_supports_distribution_pass"])
    return {
        **base,
        **evidence,
        "schema": SCHEMA,
        "v0625_classification": base_label,
        "classification": "range" if rescue else "uncertain",
        "decision_source": "v0634_two_cycle_distribution_range" if rescue else "v0625_uncertain_distribution_withheld",
        "new_range_rescue_applied": rescue,
        "D1_decisive_overridden": False,
        "future_outcome_used": False,
        "trade_authority": False,
    }
