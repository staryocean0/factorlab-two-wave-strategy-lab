"""Compatibility import for the migrated research-only Explosive V3 strategy.

The canonical implementation lives in
``factor_lab.strategy.research.timing.explosive_v3``. This path remains only
to preserve historical imports and grants no infrastructure or trading status.
"""

from factor_lab.strategy.research.timing.explosive_v3 import (
    BUCKET_ORDER,
    FIELD_LABELS_ZH,
    FOUR_LAYER_ROLE,
    LIFECYCLE,
    TIMING_EXPLOSIVE_LAYER_V3_SCHEMA_ID,
    TIMING_EXPLOSIVE_LAYER_V3_VERSION,
    build_timing_explosive_layer_v3,
    timing_explosive_layer_v3_contract,
)

__all__ = [
    "BUCKET_ORDER",
    "FIELD_LABELS_ZH",
    "FOUR_LAYER_ROLE",
    "LIFECYCLE",
    "TIMING_EXPLOSIVE_LAYER_V3_SCHEMA_ID",
    "TIMING_EXPLOSIVE_LAYER_V3_VERSION",
    "build_timing_explosive_layer_v3",
    "timing_explosive_layer_v3_contract",
]
