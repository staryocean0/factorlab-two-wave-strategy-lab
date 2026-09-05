# pyright: reportAny=false, reportArgumentType=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Read-only Layer 2 adapters for governed strategy research consumers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_layer2_measurement_plane import validate_measurement_output_columns

CONSUMER_ADAPTER_SCHEMA_ID: Final[str] = "timing_layer2_read_only_consumer_adapter@1.0"
CONSUMER_IDS: Final[tuple[str, ...]] = (
    "reaka",
    "cloudridge_greenwave",
    "residual_risk_off",
    "csi1000_lat",
    "t0",
)


def build_read_only_consumer_bundle(
    frames: Mapping[str, pd.DataFrame],
    *,
    consumer_id: str,
    fields_by_family: Mapping[str, tuple[str, ...]],
) -> dict[str, pd.DataFrame]:
    if consumer_id not in CONSUMER_IDS:
        raise ValidationError(f"unknown Layer 2 consumer: {consumer_id}")
    if not fields_by_family:
        raise ValidationError("Layer 2 consumer request cannot be empty")
    bundle: dict[str, pd.DataFrame] = {}
    for family, fields in fields_by_family.items():
        if family not in frames or not fields or len(set(fields)) != len(fields):
            raise ValidationError(f"Layer 2 consumer family request is invalid: {family}")
        source = frames[family]
        identity = tuple(column for column in ("observation_time", "available_at", "carrier_id", "view_id") if column in source)
        columns = (*identity, *fields)
        missing = sorted(set(columns).difference(source.columns))
        if missing:
            raise ValidationError(f"Layer 2 consumer fields are missing: {missing}")
        validate_measurement_output_columns(columns)
        output = source.loc[:, list(columns)].copy(deep=True)
        output.attrs["timing_layer_contract"] = {
            "schema_id": CONSUMER_ADAPTER_SCHEMA_ID,
            "consumer_id": consumer_id,
            "family": family,
            "read_only": True,
            "value_transformation": False,
            "thresholds": False,
            "strategy_mutation": False,
            "production_authority": False,
        }
        bundle[family] = output
    return bundle


__all__ = ["CONSUMER_ADAPTER_SCHEMA_ID", "CONSUMER_IDS", "build_read_only_consumer_bundle"]
