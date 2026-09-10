"""v0.6.30 D1-primary v0.6.25-preserving Range evidence intersection."""
from __future__ import annotations

from typing import Sequence

from .d1_cycle_band_range_rescue_v0629 import MIN_IQR_OVERLAP, cycle_iqr_overlap
from .d1_huber_erosion_consensus_v0623 import DECISIVE, erosion_consensus_huber_state
from .d1_huber_margin_rescue_v0625 import d1_primary_margin_rescue
from .d1_huber_state_relative_margin_v0627 import state_relative_margin_pass, state_relative_margin_requirement
from .v0623_residual_attribution_v0624 import consensus_margin_and_span

SCHEMA = "two_wave_d1_range_evidence_intersection_direction@0.6.30"


def d1_primary_range_evidence_intersection(
    d1_label: str,
    closes: Sequence[float],
    five_occurrence_bars: Sequence[int],
    amplitude_unit_price: float,
) -> dict:
    base = d1_primary_margin_rescue(
        d1_label, closes, five_occurrence_bars, amplitude_unit_price
    )
    base_label = str(base["classification"])
    if base_label in DECISIVE:
        return {
            **base,
            "schema": SCHEMA,
            "v0625_classification": base_label,
            "classification": base_label,
            "range_consensus": None,
            "range_margin": None,
            "range_margin_requirement": state_relative_margin_requirement("range"),
            "range_margin_gate_pass": None,
            "cycle_band_overlap_coefficient": None,
            "cycle_band_overlap_gate_pass": None,
            "new_range_rescue_applied": False,
        }

    consensus = erosion_consensus_huber_state(
        closes, five_occurrence_bars, amplitude_unit_price
    )
    state = str(consensus["erosion_consensus_state"])
    if state != "range":
        return {
            **base,
            "schema": SCHEMA,
            "v0625_classification": base_label,
            "classification": "uncertain",
            "range_consensus": False,
            "range_margin": None,
            "range_margin_requirement": state_relative_margin_requirement("range"),
            "range_margin_gate_pass": False,
            "cycle_band_overlap_coefficient": None,
            "cycle_band_overlap_gate_pass": False,
            "new_range_rescue_applied": False,
        }

    robust = consensus_margin_and_span(
        consensus["support_states"], consensus["support_scores"], state
    )
    margin = float(robust["consensus_margin_to_frozen_boundary"])
    margin_pass = state_relative_margin_pass("range", margin)

    band = cycle_iqr_overlap(closes, five_occurrence_bars)
    overlap = float(band["iqr_overlap_coefficient"])
    overlap_pass = overlap + 1e-12 >= MIN_IQR_OVERLAP
    rescue = bool(margin_pass and overlap_pass)

    return {
        **base,
        **consensus,
        **robust,
        **band,
        "schema": SCHEMA,
        "v0625_classification": base_label,
        "classification": "range" if rescue else "uncertain",
        "decision_source": "v0630_range_evidence_intersection" if rescue else "v0625_uncertain_intersection_withheld",
        "range_consensus": True,
        "range_margin": margin,
        "range_margin_requirement": state_relative_margin_requirement("range"),
        "range_margin_gate_pass": bool(margin_pass),
        "cycle_band_overlap_coefficient": overlap,
        "cycle_band_overlap_gate_pass": bool(overlap_pass),
        "new_range_rescue_applied": rescue,
        "future_outcome_used": False,
        "trade_authority": False,
    }
