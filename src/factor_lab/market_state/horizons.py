"""Physical trading-session horizons for the A2 market-state core.

The helpers in this module deliberately avoid the common ``N * bars_per_day``
shortcut.  A window covers the latest N observed trading sessions and includes
only bars that actually completed in those sessions.  Missing bars remain
missing; they are never replaced by older observations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, cast

import numpy as np
import pandas as pd
from pandas.api.indexers import BaseIndexer

from factor_lab.core.errors import ValidationError

TIMEZONE: Final[str] = "Asia/Shanghai"
STANDARD_SESSION_MINUTES: Final[float] = 240.0
SUPPORTED_FREQUENCIES: Final[frozenset[str]] = frozenset({"1d", "60m", "15m"})


class TradingSessionIndexer(BaseIndexer):
    """Variable rolling bounds covering N physical trading sessions."""

    def __init__(self, session_ordinals: np.ndarray, window_sessions: int) -> None:
        super().__init__()
        if window_sessions < 1:
            raise ValidationError("window_sessions must be positive")
        ordinals = np.asarray(session_ordinals, dtype=np.int64)
        if ordinals.ndim != 1 or ordinals.size == 0:
            raise ValidationError("session ordinals must be a non-empty vector")
        if bool(np.any(np.diff(ordinals) < 0)):
            raise ValidationError("session ordinals must be monotone")
        self.session_ordinals = ordinals
        self.window_sessions = int(window_sessions)

    def get_window_bounds(
        self,
        num_values: int = 0,
        min_periods: int | None = None,
        center: bool | None = None,
        closed: str | None = None,
        step: int | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        del min_periods, center, closed
        if num_values != len(self.session_ordinals):
            raise ValidationError("rolling input length does not match session ordinals")
        positions = np.arange(num_values, dtype=np.int64)
        if step not in (None, 1):
            positions = positions[::step]
        ordinals = self.session_ordinals[positions]
        first_allowed = np.maximum(0, ordinals - self.window_sessions + 1)
        starts = np.searchsorted(self.session_ordinals, first_allowed, side="left")
        ends = positions + 1
        return starts.astype(np.int64), ends.astype(np.int64)


@dataclass(frozen=True, slots=True)
class NormalizedBarPanel:
    """Causal bars plus explicit physical-time coordinates."""

    frame: pd.DataFrame
    frequency: str
    session_ordinals: np.ndarray
    completed_session_counts: np.ndarray

    def indexer(self, window_sessions: int) -> TradingSessionIndexer:
        return TradingSessionIndexer(self.session_ordinals, window_sessions)

    def full_horizon_mask(self, window_sessions: int) -> np.ndarray:
        return self.completed_session_counts >= window_sessions


def normalize_bar_panel(
    panel: pd.DataFrame,
    *,
    frequency: str,
) -> NormalizedBarPanel:
    """Validate completed bars and attach session/elapsed-minute coordinates."""

    if frequency not in SUPPORTED_FREQUENCIES:
        raise ValidationError(f"unsupported market-state frequency: {frequency}")
    required = {"trading_day", "timestamp", "close"}
    missing = required - set(panel)
    if missing:
        raise ValidationError(f"bar panel missing columns: {sorted(missing)}")
    frame = panel.copy()
    frame["trading_day"] = pd.to_datetime(
        frame["trading_day"], errors="coerce"
    ).dt.normalize()
    frame["timestamp"] = frame["timestamp"].map(_as_shanghai_timestamp)
    for column in ("open", "high", "low", "close"):
        if column not in frame:
            frame[column] = frame["close"]
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(
        subset=["trading_day", "timestamp", "open", "high", "low", "close"]
    )
    frame = frame.loc[
        (frame[["open", "high", "low", "close"]] > 0.0).all(axis=1)
    ].sort_values(["trading_day", "timestamp"], kind="mergesort")
    if frequency == "1d":
        frame = frame.drop_duplicates("trading_day", keep="last")
    else:
        frame = frame.drop_duplicates(["trading_day", "timestamp"], keep="last")
    frame = frame.reset_index(drop=True)
    if frame.empty:
        raise ValidationError("bar panel has no valid completed observations")
    timestamp_day = pd.to_datetime(frame["timestamp"].map(lambda value: value.date()))
    if not bool((timestamp_day.to_numpy() == frame["trading_day"].to_numpy()).all()):
        raise ValidationError("bar timestamp must belong to its ending trading session")
    if frequency == "1d":
        before_close = frame["timestamp"].map(
            lambda value: (value.hour, value.minute, value.second) < (15, 0, 0)
        )
        if bool(before_close.any()):
            raise ValidationError("daily observation timestamp is before formal close")
        frame["bar_duration_minutes"] = STANDARD_SESSION_MINUTES
    else:
        duration_source = (
            np.asarray(
                pd.to_numeric(frame["one_minute_count"], errors="coerce"),
                dtype=float,
            )
            if "one_minute_count" in frame
            else np.full(len(frame), np.nan, dtype=float)
        )
        default_minutes = 60.0 if frequency == "60m" else 15.0
        frame["bar_duration_minutes"] = np.clip(
            np.where(
                np.isfinite(duration_source) & (duration_source > 0.0),
                duration_source,
                default_minutes,
            ),
            a_min=0.0,
            a_max=STANDARD_SESSION_MINUTES,
        )
    sessions = pd.Index(frame["trading_day"].drop_duplicates())
    ordinal_by_day = {day: index for index, day in enumerate(sessions)}
    session_ordinals = np.asarray(
        [ordinal_by_day[value] for value in frame["trading_day"]], dtype=np.int64
    )
    frame["session_ordinal"] = session_ordinals
    frame["completed_session_count"] = session_ordinals + 1
    frame["available_at"] = frame["timestamp"]
    return NormalizedBarPanel(
        frame=frame,
        frequency=frequency,
        session_ordinals=session_ordinals,
        completed_session_counts=session_ordinals + 1,
    )


def rolling_by_sessions(
    values: pd.Series,
    normalized: NormalizedBarPanel,
    *,
    window_sessions: int,
) -> Any:
    """Return a causal rolling object using physical session bounds."""

    if len(values) != len(normalized.frame):
        raise ValidationError("rolling values must align with normalized bars")
    return values.rolling(
        window=normalized.indexer(window_sessions),
        min_periods=1,
    )


def apply_full_horizon(
    values: pd.Series,
    normalized: NormalizedBarPanel,
    *,
    window_sessions: int,
) -> pd.Series:
    """Invalidate warmup rows before N distinct sessions have been observed."""

    result = values.astype(float).copy()
    result.loc[~normalized.full_horizon_mask(window_sessions)] = np.nan
    return result


def trading_minute_offsets(normalized: NormalizedBarPanel) -> np.ndarray:
    """Cumulative completed trading minutes, excluding overnight/calendar gaps."""

    durations = np.asarray(
        normalized.frame["bar_duration_minutes"], dtype=np.float64
    )
    durations = np.where(np.isfinite(durations) & (durations > 0.0), durations, 0.0)
    return np.cumsum(durations)


def _as_shanghai_timestamp(value: object) -> pd.Timestamp:
    parsed = pd.Timestamp(str(value))
    if not isinstance(parsed, pd.Timestamp) or pd.isna(parsed):
        raise ValidationError("timestamp is required")
    if parsed.tzinfo is None:
        return cast(pd.Timestamp, parsed.tz_localize(TIMEZONE))
    return cast(pd.Timestamp, parsed.tz_convert(TIMEZONE))


__all__ = [
    "NormalizedBarPanel",
    "STANDARD_SESSION_MINUTES",
    "TIMEZONE",
    "TradingSessionIndexer",
    "apply_full_horizon",
    "normalize_bar_panel",
    "rolling_by_sessions",
    "trading_minute_offsets",
]
