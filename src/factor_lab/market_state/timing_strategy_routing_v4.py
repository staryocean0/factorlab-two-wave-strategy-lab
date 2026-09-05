"""Compatibility import for the migrated research-only V4 router profile."""

from factor_lab.strategy.research.timing.router_v4 import (
    FOUR_LAYER_ROLE,
    LIFECYCLE,
    TIMING_STRATEGY_ROUTER_V4_SCHEMA_ID,
    TIMING_STRATEGY_ROUTER_V4_VERSION,
    build_timing_strategy_router_v4_payload,
    validate_timing_strategy_router_v4_payload,
)

__all__ = [
    "FOUR_LAYER_ROLE",
    "LIFECYCLE",
    "TIMING_STRATEGY_ROUTER_V4_SCHEMA_ID",
    "TIMING_STRATEGY_ROUTER_V4_VERSION",
    "build_timing_strategy_router_v4_payload",
    "validate_timing_strategy_router_v4_payload",
]
