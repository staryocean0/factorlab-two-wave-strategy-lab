"""Layer-1 CSI1000 session-clock gate. It does not compute attributes.

This module freezes overnight-gap / session-ownership / IM-basis /
MO-premium maps as a reference overlay. Gates may reduce size, delay
entry, or exit early; they must not flip direction. Index, IM, and MO
maps are not interchangeable. Layer-2 measurement consumes the clock;
this module grants no production authority.
"""

from __future__ import annotations

from typing import Final, Literal

from factor_lab.core.errors import ValidationError

SCHEMA_ID: Final[str] = "factorlab.market_state_session_clock_reference@1.0"
CARRIER_INDEX: Final[str] = "000852.SH"
CARRIER_FUTURE: Final[str] = "IM"
CARRIER_OPTION: Final[str] = "MO"

Direction = Literal[-1, 0, 1]
ClockName = Literal[
    "overnight",
    "first30",
    "morning",
    "early_afternoon",
    "late_afternoon",
    "afternoon",
]

INDEX_WINDOW: Final[dict[str, str]] = {
    "start": "2014-10-17",
    "end_exclusive": "2025-01-01",
    "unread": "2025+",
}
FUTURES_WINDOW: Final[dict[str, str]] = {
    "start": "2022-07-22",
    "end_exclusive": "2025-01-01",
    "unread": "2025+",
}

# China-session labels. Index 1-minute timestamps in the pinned DataHub
# product are session labels stored with a Z suffix.
CLOCKS: Final[dict[str, dict[str, str]]] = {
    "overnight": {
        "start": "15:00 previous close",
        "end": "09:31 next open",
        "owns": "gap between sessions",
    },
    "first30": {"start": "09:31", "end": "10:00", "owns": "opening hour body"},
    "morning": {"start": "09:31", "end": "11:30", "owns": "continuous morning"},
    "early_afternoon": {"start": "13:01", "end": "14:00", "owns": "first afternoon hour"},
    "late_afternoon": {"start": "14:00", "end": "15:00", "owns": "last afternoon hour"},
    "afternoon": {"start": "13:01", "end": "15:00", "owns": "continuous afternoon"},
}

MINIMUM_WINDOW: Final[dict[str, object]] = {
    "month": "sensitivity_only_about_20_days",
    "quarter": "smallest_decision_support_grain_about_60_days",
    "rolling_63d": "latest_state_view_overlapping_not_independent",
    "year": "primary_reporting_grain",
    "usable_sign_rule": "n>=40 and abs(mean) >= standard_error",
}

# Unconditional index priors, CSI1000 2014-10-17 to 2024, 2025 unread.
# Signs are research materials, not runtime calendar rules.
INDEX_PRIORS: Final[dict[str, dict[str, object]]] = {
    "overnight": {
        "sign": "negative",
        "note": "about 60% of opens are down versus previous close; this is a cost if long overnight",
        "default_gate": "do_not_hold_overnight_unconditionally",
    },
    "first30": {
        "sign": "positive",
        "note": "most of the average daily drift is in 09:31-10:00; 2023 thinned this piece",
        "default_gate": "gain_candidate_for_longs_not_a_standalone_long",
    },
    "morning": {
        "sign": "positive",
        "note": "09:31-11:30 is the main up piece on the index",
        "default_gate": "preferred_unconditional_index_ownership_if_no_overnight",
    },
    "early_afternoon": {
        "sign": "negative_after_2021",
        "note": "13:00-14:00 is the cleanest down hour after 2021; 2014-2020 was mixed/slightly positive",
        "default_gate": "longs_skip_candidate_shorts_keep_candidate",
    },
    "late_afternoon": {
        "sign": "mixed",
        "note": "14:00-14:30 slightly negative; 14:30-15:00 slightly positive. Not a pure last-hour down.",
        "default_gate": "do_not_bind_to_early_afternoon",
    },
}

# IM 2022-07-22 to 2024. Overnight is NOT the index overnight.
FUTURES_PRIORS: Final[dict[str, dict[str, object]]] = {
    "overnight": {
        "sign": "positive_on_IM",
        "index_sign": "negative",
        "driver": "basis_recovery_of_persistent_backwardation",
        "default_gate": "do_not_copy_index_short_overnight_onto_IM",
    },
    "first30": {
        "sign": "positive_but_weaker_than_index",
        "driver": "index_open_up_minus_slightly_deeper_discount",
        "default_gate": "gain_candidate_with_direction_filter",
    },
    "early_afternoon": {
        "sign": "negative",
        "driver": "index_path_almost_one_to_one_basis_almost_still",
        "default_gate": "cleanest_IM_inventory_gate_longs_skip_shorts_keep",
    },
}

OPTION_PRIORS: Final[dict[str, dict[str, object]]] = {
    "implied_vol": "already_inside_the_premium_path_not_a_missing_term",
    "first30_long_atm_call": "does_not_harvest_the_index_up_piece_on_average",
    "early_afternoon_long_atm_put": "weak_positive_follow_through_to_the_down_piece",
    "early_afternoon_short_atm_call": "stronger_statistical_follow_through_but_seller_risk_unpriced",
    "deep_otm": "out_of_scope",
    "l1": "absent_no_net_executable_claim",
}

AUTHORITY: Final[dict[str, bool]] = {
    "research_infrastructure": True,
    "strategy_selection": False,
    "parameter_selection": False,
    "routing": False,
    "production": False,
    "standalone_session_strategy": False,
}


def inventory_gate(
    desired_direction: int,
    clock: ClockName,
    *,
    instrument: Literal["index", "IM"] = "IM",
) -> int:
    """Return a 0/1 inventory multiplier. Never flips sign.

    `desired_direction` is the incumbent timing sign. The session clock may
    only keep or flatten it. Overnight flattening on the 1-minute LAT successor
    is a no-op because that spec already flats by 14:55.
    """

    if desired_direction not in (-1, 0, 1):
        raise ValidationError("desired_direction must be -1, 0 or 1")
    if clock not in CLOCKS:
        raise ValidationError(f"unknown session clock: {clock}")
    if instrument not in {"index", "IM"}:
        raise ValidationError("instrument must be index or IM")
    if desired_direction == 0:
        return 0
    if clock == "overnight":
        return 0
    if clock == "early_afternoon" and desired_direction > 0:
        return 0
    if clock == "first30" and desired_direction < 0 and instrument == "IM":
        # IM first-hour is a long-gain candidate, not a short-gain candidate.
        return 1
    return 1


def gated_position(desired_direction: int, clock: ClockName, *, instrument: Literal["index", "IM"] = "IM") -> int:
    """Apply the inventory gate without flipping the incumbent direction."""

    pos = int(desired_direction) * inventory_gate(desired_direction, clock, instrument=instrument)
    if pos != 0 and desired_direction != 0 and (pos > 0) != (desired_direction > 0):
        raise ValidationError("session clock gate flipped incumbent direction")
    return pos


def fusion_order() -> tuple[str, ...]:
    return (
        "keep_incumbent_direction",
        "do_not_hold_overnight_unconditionally_on_index_or_IM",
        "longs_skip_13_00_to_14_00_on_IM",
        "treat_09_31_to_10_00_as_optional_long_gain_gate_with_rolling_63d_health",
        "do_not_translate_index_overnight_short_to_IM_or_to_long_calls",
        "ablate_Vn_versus_Vn_plus_gate_on_the_incumbent_account",
    )


def build_reference_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_id": SCHEMA_ID,
        "carrier_index": CARRIER_INDEX,
        "carrier_future": CARRIER_FUTURE,
        "carrier_option": CARRIER_OPTION,
        "index_window": dict(INDEX_WINDOW),
        "futures_window": dict(FUTURES_WINDOW),
        "clocks": dict(CLOCKS),
        "minimum_window": dict(MINIMUM_WINDOW),
        "index_priors": dict(INDEX_PRIORS),
        "futures_priors": dict(FUTURES_PRIORS),
        "option_priors": dict(OPTION_PRIORS),
        "authority": dict(AUTHORITY),
        "fusion_order": list(fusion_order()),
        "temporary_sources": [
            "tmp/overnight_gap_session_option_iv_probe_v1",
            "tmp/overnight_gap_direction_overlay_probe_v1",
            "tmp/overnight_gap_conditional_state_probe_v1",
            "tmp/intraday_session_ownership_probe_v1",
            "tmp/im_session_ownership_probe_v1",
            "tmp/im_lat_futures_gate_v1",
            "tmp/session_rhythm_rolling_probe_v1",
            "tmp/mo_session_piece_option_probe_v1",
        ],
        "scientific_status": "frozen_research_reference_waiting_for_incumbent_ablation",
    }
    if payload["authority"]["production"] or payload["authority"]["standalone_session_strategy"]:
        raise ValidationError("session-clock reference cannot carry strategy or production authority")
    return payload
