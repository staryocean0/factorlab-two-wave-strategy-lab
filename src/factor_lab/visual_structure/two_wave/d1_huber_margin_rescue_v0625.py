"""v0.6.25 D1-primary erosion-consensus Huber margin rescue."""
from __future__ import annotations

from typing import Sequence

from .d1_huber_erosion_consensus_v0623 import DECISIVE, erosion_consensus_huber_state
from .v0623_residual_attribution_v0624 import consensus_margin_and_span

SCHEMA = "two_wave_d1_huber_margin_rescue_direction@0.6.25"
MIN_CONSENSUS_MARGIN = 0.10
BOUNDARY_EPS = 1e-12
VALID_D1 = DECISIVE | {"uncertain"}


def d1_primary_margin_rescue(
    d1_label: str,
    closes: Sequence[float],
    five_occurrence_bars: Sequence[int],
    amplitude_unit_price: float,
) -> dict:
    d1 = str(d1_label)
    if d1 not in VALID_D1:
        raise ValueError(f"unsupported D1 label: {d1}")
    if d1 in DECISIVE:
        return {
            "schema": SCHEMA,
            "classification": d1,
            "decision_source": "D1",
            "D1_decisive_overridden": False,
            "v0623_consensus_decisive": None,
            "consensus_margin_to_frozen_boundary": None,
            "margin_gate_pass": None,
            "rescue_applied": False,
            "future_outcome_used": False,
            "trade_authority": False,
        }

    consensus = erosion_consensus_huber_state(
        closes, five_occurrence_bars, amplitude_unit_price
    )
    state = str(consensus["erosion_consensus_state"])
    if state not in DECISIVE:
        return {
            **consensus,
            "schema": SCHEMA,
            "classification": "uncertain",
            "decision_source": "D1_uncertain_no_v0623_consensus",
            "D1_decisive_overridden": False,
            "v0623_consensus_decisive": False,
            "consensus_margin_to_frozen_boundary": None,
            "margin_gate_pass": False,
            "rescue_applied": False,
        }

    robust = consensus_margin_and_span(
        consensus["support_states"], consensus["support_scores"], state
    )
    margin = float(robust["consensus_margin_to_frozen_boundary"])
    # The protocol's boundary is inclusive (margin >= 0.10).  The epsilon only
    # prevents binary floating-point representation from turning a mathematical
    # equality such as 0.60 - 0.50 into a false rejection; it does not change
    # the frozen 0.10 threshold.
    passed = margin + BOUNDARY_EPS >= MIN_CONSENSUS_MARGIN
    return {
        **consensus,
        **robust,
        "schema": SCHEMA,
        "classification": state if passed else "uncertain",
        "decision_source": "v0625_margin_gated_Huber" if passed else "D1_uncertain_margin_withheld",
        "D1_decisive_overridden": False,
        "v0623_consensus_decisive": True,
        "margin_gate_pass": passed,
        "rescue_applied": passed,
        "minimum_consensus_margin": MIN_CONSENSUS_MARGIN,
    }
