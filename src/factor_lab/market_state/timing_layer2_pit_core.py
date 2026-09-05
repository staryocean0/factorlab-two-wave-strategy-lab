# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Point-in-time Layer 2 core measurements over already-built bars.

The provider consumes Layer 1 bars and reuses the frozen vector formulas from
the annual core.  It does not resample, choose a frequency, or emit a strategy
state.  Annual-only reversal/jump summaries are deliberately not renamed into
point-in-time fields in Phase B1.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.core_kline_attribute_pool import (
    HORIZON_DAYS,
    _rolling_direction_metrics,
    _safe_median,
    _signed_efficiency,
    _signed_ols_t,
)
from factor_lab.market_state.lat_kline_attribute_atlas import (
    _rolling_efficiency,
    _rolling_trend,
)
from factor_lab.market_state.timing_layer2_measurement_plane import (
    BarAuthority,
    GapPolicy,
    Layer2MeasurementCoordinate,
    validate_measurement_output_columns,
)

PIT_CORE_SCHEMA_ID: Final[str] = "timing_layer2_pit_core@1.0"
PIT_CORE_ESTIMATOR_VERSION: Final[str] = "layer2_pit_core_b1_exact_existing_formulas_v1"

PIT_HORIZON_COLUMNS: Final[tuple[str, ...]] = tuple(
    column
    for days in HORIZON_DAYS
    for column in (
        f"efficiency_ratio_{days}d",
        f"ols_slope_t_abs_{days}d",
        f"ols_r2_{days}d",
        f"signed_efficiency_ratio_{days}d",
        f"ols_slope_t_signed_{days}d",
        f"bdci_score_{days}d",
        f"bci_imbalance_{days}d",
        f"wbi_score_{days}d",
        f"dii_score_{days}d",
    )
)

PIT_GEOMETRY_COLUMNS: Final[tuple[str, ...]] = (
    "body_to_range_ratio",
    "upper_wick_share",
    "lower_wick_share",
    "close_location_value",
    "parkinson_log_range_sq",
    "rogers_satchell_variance_term",
)


@dataclass(frozen=True, slots=True)
class PITCoreBinding:
    """Panel-level identity and Layer 1 receipt for point-in-time measurement."""

    carrier_id: str
    view_id: str
    bars_per_day: int
    source_id: str
    source_version: str
    source_receipt_sha256: str
    bar_authority: BarAuthority = "datahub_wall_clock"
    carrier_source_authority: str = "datahub"
    membership_version: str | None = None
    gap_policy: GapPolicy = "fail_closed"
    availability_delay_seconds: int = 0
    estimator_version: str = PIT_CORE_ESTIMATOR_VERSION

    def __post_init__(self) -> None:
        if isinstance(self.bars_per_day, bool) or self.bars_per_day < 1:
            raise ValidationError("PIT core bars_per_day must be positive")
        if self.availability_delay_seconds < 0:
            raise ValidationError("PIT core availability delay cannot be negative")
        if not self.estimator_version.strip():
            raise ValidationError("PIT core estimator version is required")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_pit_core_measurements(
    bars: pd.DataFrame,
    *,
    binding: PITCoreBinding,
    horizon_days: tuple[int, ...] = HORIZON_DAYS,
) -> pd.DataFrame:
    """Build causal rolling measurements with exact frozen formula reuse."""

    if horizon_days != HORIZON_DAYS:
        raise ValidationError("Phase B1 horizon family is frozen at 2/4/8/16 physical days")
    frame = _validated_bars(bars)
    timestamp = pd.DatetimeIndex(frame["timestamp"])
    first_time = timestamp[0].to_pydatetime()
    _ = Layer2MeasurementCoordinate(
        carrier_id=binding.carrier_id,
        view_id=binding.view_id,
        physical_horizon="2d/4d/8d/16d",
        observation_time=first_time,
        available_at=first_time + timedelta(seconds=binding.availability_delay_seconds),
        source_id=binding.source_id,
        source_version=binding.source_version,
        source_receipt_sha256=binding.source_receipt_sha256,
        estimator_id="pit_core",
        estimator_version=binding.estimator_version,
        bar_authority=binding.bar_authority,
        carrier_source_authority=binding.carrier_source_authority,
        membership_version=binding.membership_version,
        gap_policy=binding.gap_policy,
    )
    result = pd.DataFrame(
        {
            "carrier_id": binding.carrier_id,
            "view_id": binding.view_id,
            "observation_time": timestamp,
            "available_at": timestamp + pd.to_timedelta(binding.availability_delay_seconds, unit="s"),
            "continuity_segment_id": frame["continuity_segment_id"].astype(str),
            "quality_status": "ready",
        },
        index=frame.index,
    )
    for _segment, locations in frame.groupby("continuity_segment_id", sort=False).groups.items():
        loc = np.asarray(list(locations), dtype=int)
        part = frame.iloc[loc]
        values = _pointwise_segment(part, bars_per_day=binding.bars_per_day)
        for column, data in values.items():
            if column not in result:
                result[column] = np.nan
            result.loc[loc, column] = data
    validate_measurement_output_columns(result.columns)
    result.attrs["timing_layer_contract"] = {
        "schema_id": PIT_CORE_SCHEMA_ID,
        "four_layer_role": "layer2_kline_measurement",
        "binding": binding.to_dict(),
        "horizon_days": list(horizon_days),
        "annual_only_fields_deferred": ["no_buffer_reversal_rate", "bipower_jump_share"],
        "local_resampling": False,
        "measurement_authority": True,
        "routing_authority": False,
        "production_authority": False,
    }
    return result


def reduce_pit_core_geometry_and_direction_by_year(
    measurements: pd.DataFrame,
) -> pd.DataFrame:
    """Reduce Phase B1 point values to the 30 exactly comparable annual fields."""

    required = {
        "carrier_id",
        "observation_time",
        *PIT_HORIZON_COLUMNS,
        *PIT_GEOMETRY_COLUMNS,
    }
    missing = sorted(required.difference(measurements.columns))
    if missing:
        raise ValidationError(f"PIT core annual reducer missing columns: {missing}")
    timestamps = pd.DatetimeIndex(measurements["observation_time"])
    rows: list[dict[str, object]] = []
    for year in sorted(set(timestamps.year)):
        part = measurements.loc[timestamps.year == year]
        row: dict[str, object] = {
            "carrier": str(part["carrier_id"].iloc[0]),
            "year": int(year),
        }
        for days in HORIZON_DAYS:
            for prefix in (
                "signed_efficiency_ratio",
                "ols_slope_t_signed",
                "bdci_score",
                "bci_imbalance",
                "wbi_score",
                "dii_score",
            ):
                column = f"{prefix}_{days}d"
                row[column] = _safe_median(part[column].to_numpy(float))
        for output, source in (
            ("body_to_range_ratio_median", "body_to_range_ratio"),
            ("upper_wick_share_median", "upper_wick_share"),
            ("lower_wick_share_median", "lower_wick_share"),
            ("close_location_value_median", "close_location_value"),
        ):
            row[output] = _safe_median(part[source].to_numpy(float))
        row["parkinson_volatility"] = math.sqrt(float(part["parkinson_log_range_sq"].mean()) / (4.0 * math.log(2.0)))
        row["rogers_satchell_volatility"] = math.sqrt(max(float(part["rogers_satchell_variance_term"].mean()), 0.0))
        rows.append(row)
    return pd.DataFrame(rows)


def _pointwise_segment(frame: pd.DataFrame, *, bars_per_day: int) -> dict[str, np.ndarray]:
    size = len(frame)
    log_close = np.log(frame["close"].to_numpy(float))
    returns = np.diff(log_close)
    output: dict[str, np.ndarray] = {}
    for days in HORIZON_DAYS:
        window = days * bars_per_day
        output[f"efficiency_ratio_{days}d"] = _align(_rolling_efficiency(log_close, window), size, window)
        trend_abs, r2 = _rolling_trend(log_close, window)
        output[f"ols_slope_t_abs_{days}d"] = _align(trend_abs, size, window - 1)
        output[f"ols_r2_{days}d"] = _align(r2, size, window - 1)
        output[f"signed_efficiency_ratio_{days}d"] = _align(_signed_efficiency(log_close, window), size, window)
        output[f"ols_slope_t_signed_{days}d"] = _align(_signed_ols_t(log_close, window), size, window - 1)
        direction = _rolling_direction_metrics(returns, window)
        for source, prefix in (
            ("bdci", "bdci_score"),
            ("bci", "bci_imbalance"),
            ("wbi", "wbi_score"),
            ("dii", "dii_score"),
        ):
            output[f"{prefix}_{days}d"] = _align(direction[source], size, window)
    open_ = frame["open"].to_numpy(float)
    high = frame["high"].to_numpy(float)
    low = frame["low"].to_numpy(float)
    close = frame["close"].to_numpy(float)
    log_range = np.log(high / low)
    body = np.abs(np.log(close / open_))
    upper = np.log(high / np.maximum(open_, close))
    lower = np.log(np.minimum(open_, close) / low)
    price_range = high - low
    output["body_to_range_ratio"] = _safe_divide(body, log_range)
    output["upper_wick_share"] = _safe_divide(upper, log_range)
    output["lower_wick_share"] = _safe_divide(lower, log_range)
    output["close_location_value"] = _safe_divide(2.0 * close - high - low, price_range)
    output["parkinson_log_range_sq"] = np.square(log_range)
    output["rogers_satchell_variance_term"] = np.log(high / open_) * np.log(high / close) + np.log(low / open_) * np.log(low / close)
    return output


def _validated_bars(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"timestamp", "open", "high", "low", "close"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValidationError(f"PIT core bars missing columns: {missing}")
    result = frame.copy().reset_index(drop=True)
    timestamp = pd.DatetimeIndex(pd.to_datetime(result["timestamp"], errors="raise"))
    if timestamp.tz is None:
        raise ValidationError("PIT core timestamps must be timezone-aware")
    if timestamp.has_duplicates or not timestamp.is_monotonic_increasing:
        raise ValidationError("PIT core timestamps must be unique and ordered")
    result["timestamp"] = timestamp
    for column in ("open", "high", "low", "close"):
        result[column] = pd.to_numeric(result[column], errors="raise").astype(float)
    ohlc = result[["open", "high", "low", "close"]]
    if not np.isfinite(ohlc.to_numpy(float)).all() or bool((ohlc <= 0.0).any().any()):
        raise ValidationError("PIT core OHLC must be finite and positive")
    if bool((result["low"] > result[["open", "close"]].min(axis=1)).any()) or bool(
        (result["high"] < result[["open", "close"]].max(axis=1)).any()
    ):
        raise ValidationError("PIT core OHLC geometry is invalid")
    if "continuity_segment_id" not in result:
        result["continuity_segment_id"] = "segment_0"
    if result["continuity_segment_id"].isna().any():
        raise ValidationError("PIT core continuity segment cannot be missing")
    return result


def _align(values: np.ndarray, size: int, start: int) -> np.ndarray:
    result = np.full(size, np.nan, dtype=float)
    if len(values):
        if start < 0 or start + len(values) != size:
            raise ValidationError("PIT core formula alignment drifted")
        result[start:] = values
    return result


def _safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator, dtype=float),
        where=denominator > 0,
    )


__all__ = [
    "PIT_CORE_ESTIMATOR_VERSION",
    "PIT_CORE_SCHEMA_ID",
    "PIT_GEOMETRY_COLUMNS",
    "PIT_HORIZON_COLUMNS",
    "PITCoreBinding",
    "build_pit_core_measurements",
    "reduce_pit_core_geometry_and_direction_by_year",
]
