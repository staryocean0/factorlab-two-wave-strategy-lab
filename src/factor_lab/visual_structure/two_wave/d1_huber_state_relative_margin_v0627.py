"""v0.6.27 D1-primary erosion-consensus Huber state-relative margin rescue."""
from __future__ import annotations

from typing import Sequence

from .d1_huber_erosion_consensus_v0623 import DECISIVE, erosion_consensus_huber_state
from .v0623_residual_attribution_v0624 import consensus_margin_and_span

SCHEMA = "two_wave_d1_huber_state_relative_margin_direction@0.6.27"
RELATIVE_MARGIN_FRACTION = 0.20
TREND_BOUNDARY_SCALE = 0.50
RANGE_BOUNDARY_SCALE = 0.15
BOUNDARY_EPS = 1e-12
VALID_D1 = DECISIVE | {"uncertain"}


def state_relative_margin_requirement(state: str) -> float:
    s = str(state)
    if s in {"uptrend", "downtrend"}:
        return RELATIVE_MARGIN_FRACTION * TREND_BOUNDARY_SCALE
    if s == "range":
        return RELATIVE_MARGIN_FRACTION * RANGE_BOUNDARY_SCALE
    raise ValueError(f"unsupported decisive state: {s}")


def state_relative_margin_pass(state: str, margin: float) -> bool:
    requirement = state_relative_margin_requirement(state)
    return float(margin) + BOUNDARY_EPS >= requirement


def d1_primary_state_relative_margin_rescue(
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
            "required_absolute_margin": None,
            "relative_margin_fraction": RELATIVE_MARGIN_FRACTION,
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
            "required_absolute_margin": None,
            "relative_margin_fraction": RELATIVE_MARGIN_FRACTION,
            "margin_gate_pass": False,
            "rescue_applied": False,
        }

    robust = consensus_margin_and_span(
        consensus["support_states"], consensus["support_scores"], state
    )
    margin = float(robust["consensus_margin_to_frozen_boundary"])
    requirement = state_relative_margin_requirement(state)
    passed = state_relative_margin_pass(state, margin)
    return {
        **consensus,
        **robust,
        "schema": SCHEMA,
        "classification": state if passed else "uncertain",
        "decision_source": (
            "v0627_state_relative_margin_Huber"
            if passed else "D1_uncertain_state_relative_margin_withheld"
        ),
        "D1_decisive_overridden": False,
        "v0623_consensus_decisive": True,
        "required_absolute_margin": requirement,
        "relative_margin_fraction": RELATIVE_MARGIN_FRACTION,
        "margin_gate_pass": passed,
        "rescue_applied": passed,
        "future_outcome_used": False,
        "trade_authority": False,
    }
