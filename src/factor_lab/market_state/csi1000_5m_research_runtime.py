"""Layer-1 CSI1000 5-minute signal clock and next-1m fill coordinate.

This is not an attribute or direction module. Layer-2 measurement consumes
the pinned 5m_offset_0 clock; fills stay next tradable 1m raw open.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from factor_lab.core.errors import ValidationError

CONTRACT_ID = "csi1000_5m_research_runtime@1.0"
VIEW_ID = "5m_offset_0"


@dataclass(frozen=True, slots=True)
class FiveMinuteExecutionCoordinate:
    signal_time: pd.Timestamp
    execution_time: pd.Timestamp
    execution_open: float
    trading_day: str

    def __post_init__(self) -> None:
        if self.execution_time <= self.signal_time or self.execution_open <= 0.0:
            raise ValidationError("5m execution coordinate is not strictly causal")


def normalize_literal_wall_clock(
    frame: pd.DataFrame,
    *,
    expected_view_id: str,
) -> pd.DataFrame:
    required = {"timestamp", "trading_day", "open", "close"}
    if missing := sorted(required.difference(frame.columns)):
        raise ValidationError(f"5m runtime input missing columns: {missing}")
    local = frame.copy()
    if "export_view_id" in local and not local["export_view_id"].astype(str).eq(expected_view_id).all():
        raise ValidationError("5m runtime view identity drifted")
    literal = pd.to_datetime(local["timestamp"], errors="raise", utc=True).dt.tz_localize(None)
    local["event_time"] = literal.dt.tz_localize("Asia/Shanghai").dt.tz_convert("UTC")
    local["trading_day"] = local["trading_day"].astype(str)
    for column in ("open", "close"):
        local[column] = pd.to_numeric(local[column], errors="raise").astype(float)
    if local[["open", "close"]].le(0.0).any().any():
        raise ValidationError("5m runtime prices must be positive")
    shanghai = local["event_time"].dt.tz_convert("Asia/Shanghai")
    minute = shanghai.dt.hour * 60 + shanghai.dt.minute
    if expected_view_id == VIEW_ID:
        valid = minute.between(9 * 60 + 35, 11 * 60 + 30) | minute.between(13 * 60 + 5, 15 * 60)
        if not valid.all() or not minute.mod(5).eq(0).all():
            raise ValidationError("5m runtime rows escaped the offset-0 session grid")
    elif expected_view_id == "1m_official":
        valid = minute.between(9 * 60 + 31, 11 * 60 + 30) | minute.between(13 * 60 + 1, 15 * 60)
        if not valid.all():
            raise ValidationError("1m execution rows escaped the official session grid")
    else:
        raise ValidationError("unsupported K-line runtime view")
    if local["event_time"].duplicated().any():
        raise ValidationError("5m runtime event times must be unique")
    return local.sort_values("event_time", kind="mergesort").reset_index(drop=True)


def attach_next_one_minute_open(
    signals: pd.DataFrame,
    one_minute: pd.DataFrame,
) -> pd.DataFrame:
    """Attach the first completed 1m bar beginning after each 5m signal close."""

    signal = normalize_literal_wall_clock(signals, expected_view_id=VIEW_ID)
    minute = normalize_literal_wall_clock(one_minute, expected_view_id="1m_official")
    right = minute[["event_time", "trading_day", "open"]].rename(columns={"event_time": "execution_time", "open": "execution_open"})
    merged = pd.merge_asof(
        signal.sort_values("event_time"),
        right.sort_values("execution_time"),
        left_on="event_time",
        right_on="execution_time",
        direction="forward",
        allow_exact_matches=False,
    )
    if merged[["execution_time", "execution_open"]].isna().any().any():
        raise ValidationError("5m runtime lacks a next tradable 1m open")
    if not merged["execution_time"].gt(merged["event_time"]).all():
        raise ValidationError("5m runtime execution is not after signal close")
    merged["contract_id"] = CONTRACT_ID
    merged["signal_view_id"] = VIEW_ID
    merged["fill_view_id"] = "1m_official_raw_pit"
    return merged


__all__ = [
    "CONTRACT_ID",
    "VIEW_ID",
    "FiveMinuteExecutionCoordinate",
    "attach_next_one_minute_open",
    "normalize_literal_wall_clock",
]
