"""Layer 4 facade for all-frequency execution transport and option costs."""

from __future__ import annotations

from typing import Final

from factor_lab.market_state.timing_all_frequency_infrastructure import (
    OptionAskBidRoundTripCostV3,
    OptionFeeScheduleV2,
    OptionPriceObservation,
    TimingHorizonContract,
    build_execution_transport_ladder,
    price_long_option_round_trip_ask_bid_v3,
    resolve_first_visible_bar_close,
    unbound_option_fee_schedule,
)

CONTRACT_ID: Final = "timing_layer4_all_frequency_execution@1.0"


def layer4_all_frequency_execution_contract() -> dict[str, object]:
    return {
        "schema_id": CONTRACT_ID,
        "legacy_implementation": "timing_all_frequency_infrastructure.py",
        "provides": [
            "price_availability_and_fill_semantics",
            "option_fee_schedules",
            "synchronized_L1_ask_entry_bid_exit_round_trip",
            "execution_transport_ladder",
        ],
        "Layer2_measurement_authority": False,
        "strategy_direction_authority": False,
        "parameter_selection_authority": False,
        "production_authority": False,
    }


__all__ = [
    "CONTRACT_ID",
    "OptionAskBidRoundTripCostV3",
    "OptionFeeScheduleV2",
    "OptionPriceObservation",
    "TimingHorizonContract",
    "build_execution_transport_ladder",
    "layer4_all_frequency_execution_contract",
    "price_long_option_round_trip_ask_bid_v3",
    "resolve_first_visible_bar_close",
    "unbound_option_fee_schedule",
]
