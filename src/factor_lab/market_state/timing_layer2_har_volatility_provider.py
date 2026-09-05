# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportIndexIssue=false, reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
"""Read-only Layer 2 HAR realized-volatility forecast cards for Layer 3 consumers."""

from __future__ import annotations

from typing import Final

import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_layer2_attribute_followability import (
    FOLLOWABILITY_ID,
    PRIMARY_HORIZON_BARS,
    FittedLinearFollower,
    build_har_features,
    fit_har_follower,
    forecast_linear_follower_frame,
)
from factor_lab.market_state.timing_layer2_consumer_adapters import build_read_only_consumer_bundle
from factor_lab.market_state.timing_layer2_future_path_provider_v2 import build_future_path_target
from factor_lab.market_state.timing_layer2_measurement_plane import validate_measurement_output_columns

HAR_PROVIDER_ID: Final[str] = "timing_layer2_har_volatility_provider@1.0"
HAR_FAMILY: Final[str] = "har_volatility_forecast"
HAR_FIELDS: Final[tuple[str, ...]] = (
    "har_rv_mean",
    "har_rv_q10",
    "har_rv_q50",
    "har_rv_q90",
    "har_rv_abstained",
)


def fit_har_volatility_provider(
    close: pd.Series,
    *,
    carrier_id: str,
    view_id: str,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
    horizon_bars: int = PRIMARY_HORIZON_BARS,
) -> FittedLinearFollower:
    if close.index.tz is None:
        raise ValidationError("HAR volatility provider requires timezone-aware bars")
    target = build_future_path_target(
        close, target_id="future_log_realized_variance", horizon_bars=horizon_bars
    )
    fitted = fit_har_follower(
        close,
        target,
        target_id="future_log_realized_variance",
        horizon_bars=horizon_bars,
        train_end=train_end,
        calibration_end=calibration_end,
    )
    if fitted.production_authority or fitted.direction_forecast:
        raise ValidationError("HAR volatility provider cannot grant authority")
    return fitted


def build_har_volatility_forecast_frame(
    close: pd.Series,
    fitted: FittedLinearFollower,
    *,
    carrier_id: str,
    view_id: str,
    available_at: pd.Series | None = None,
) -> pd.DataFrame:
    if fitted.method_id != "har" or fitted.target_id != "future_log_realized_variance":
        raise ValidationError("HAR volatility provider fit identity drifted")
    cards = forecast_linear_follower_frame(fitted, build_har_features(close, target_id=fitted.target_id))
    observation = pd.DatetimeIndex(close.index)
    availability = available_at.reindex(close.index) if available_at is not None else observation
    output = pd.DataFrame(
        {
            "carrier_id": carrier_id,
            "view_id": view_id,
            "observation_time": observation,
            "available_at": availability,
            "har_rv_mean": cards["mean"],
            "har_rv_q10": cards["q10"],
            "har_rv_q50": cards["q50"],
            "har_rv_q90": cards["q90"],
            "har_rv_abstained": cards["abstained"],
            "provider_id": HAR_PROVIDER_ID,
            "followability_id": FOLLOWABILITY_ID,
            "horizon_bars": fitted.horizon_bars,
        },
        index=close.index,
    )
    validate_measurement_output_columns(output.columns)
    output.attrs["timing_layer_contract"] = {
        "schema_id": HAR_PROVIDER_ID,
        "family": HAR_FAMILY,
        "runtime_feature_future_reads": 0,
        "direction_forecast": False,
        "read_only": True,
        "strategy_mutation": False,
        "routing_authority": False,
        "production_authority": False,
    }
    return output


def build_har_volatility_consumer_bundle(
    frame: pd.DataFrame,
    *,
    consumer_id: str,
) -> dict[str, pd.DataFrame]:
    return build_read_only_consumer_bundle(
        {HAR_FAMILY: frame},
        consumer_id=consumer_id,
        fields_by_family={HAR_FAMILY: HAR_FIELDS},
    )


__all__ = [
    "HAR_FAMILY",
    "HAR_FIELDS",
    "HAR_PROVIDER_ID",
    "build_har_volatility_consumer_bundle",
    "build_har_volatility_forecast_frame",
    "fit_har_volatility_provider",
]
