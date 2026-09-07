# -*- coding: utf-8 -*-
"""Session-offset / close-anchor bar construction contract.

This is the additive DataHub product for wall-clock phase-offset bars.
It is not Hilbert/IIR filter phase, and it is not the 3s transaction
``session_phase`` label.

Default queries keep ``cn_a_session_end_label_no_noon_partial_v2``.
Offset / noon-close products must be requested explicitly and must use a
new construction contract id.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

OFFICIAL_SESSION_CONTRACT_ID = "cn_a_session_end_label_no_noon_partial_v2"
SESSION_OFFSET_CONTRACT_ID = "cn_a_session_wall_clock_offset_v1"
BAR_ALIGN_OFFICIAL = "session_end_label_v2"
BAR_ALIGN_WALL_CLOCK = "session_wall_clock"
SUPPORTED_BAR_ALIGNS = (BAR_ALIGN_OFFICIAL, BAR_ALIGN_WALL_CLOCK)
DEFAULT_CLOSE_ANCHOR = "15:00"
NOON_CLOSE_ANCHOR = "11:30"
SUPPORTED_CLOSE_ANCHORS = (DEFAULT_CLOSE_ANCHOR, NOON_CLOSE_ANCHOR)
SUPPORTED_INTRADAY_FREQUENCIES = ("5m", "15m", "30m", "60m")
SUPPORTED_DERIVED_FREQUENCIES = (*SUPPORTED_INTRADAY_FREQUENCIES, "1d")
PERIOD_MINUTES = {"5m": 5, "15m": 15, "30m": 30, "60m": 60}
CN_A_MORNING_WINDOW = (570, 690)
CN_A_AFTERNOON_WINDOW = (780, 900)
CN_A_SESSION_WINDOWS = (CN_A_MORNING_WINDOW, CN_A_AFTERNOON_WINDOW)
MORNING_OPEN_LABEL = "09:30"
AFTERNOON_OPEN_LABEL = "13:00"
DEFAULT_RESEARCH_OFFSETS = {
    "60m": 5,
    "15m": 15,
}


@dataclass(frozen=True, slots=True)
class SessionOffsetRequest:
    frequency: str
    bar_align: str = BAR_ALIGN_OFFICIAL
    session_offset_minutes: int = 0
    close_anchor: str | None = None
    include_tail_partial: bool = False

    @property
    def close_anchor_or_default(self) -> str:
        return self.close_anchor or DEFAULT_CLOSE_ANCHOR

    @property
    def uses_official_contract(self) -> bool:
        return (
            self.bar_align == BAR_ALIGN_OFFICIAL
            and self.session_offset_minutes == 0
            and self.close_anchor_or_default == DEFAULT_CLOSE_ANCHOR
            and not self.include_tail_partial
        )

    @property
    def construction_contract(self) -> str:
        if self.uses_official_contract:
            return OFFICIAL_SESSION_CONTRACT_ID
        return SESSION_OFFSET_CONTRACT_ID


def hhmm_to_minute(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def minute_to_hhmm(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def normalize_session_offset_request(
    *,
    frequency: str,
    bar_align: str | None = None,
    session_offset_minutes: int | None = None,
    close_anchor: str | None = None,
    include_tail_partial: bool = False,
) -> SessionOffsetRequest:
    """Fail-closed normalizer for additive query parameters."""

    freq = str(frequency or "").strip()
    align = str(bar_align or BAR_ALIGN_OFFICIAL).strip() or BAR_ALIGN_OFFICIAL
    if align in {"", "official", "v2", OFFICIAL_SESSION_CONTRACT_ID}:
        align = BAR_ALIGN_OFFICIAL
    if align not in SUPPORTED_BAR_ALIGNS:
        raise ValueError(
            f"unsupported bar_align={bar_align!r}; "
            f"must be one of {SUPPORTED_BAR_ALIGNS}"
        )

    offset = 0 if session_offset_minutes is None else int(session_offset_minutes)
    anchor = None if close_anchor in (None, "") else str(close_anchor).strip()
    if anchor in {"15:00:00", "T15:00", "T15:00:00Z"}:
        anchor = DEFAULT_CLOSE_ANCHOR
    if anchor in {"11:30:00", "T11:30", "T11:30:00Z"}:
        anchor = NOON_CLOSE_ANCHOR
    if anchor is not None and anchor not in SUPPORTED_CLOSE_ANCHORS:
        raise ValueError(
            f"unsupported close_anchor={close_anchor!r}; "
            f"must be one of {SUPPORTED_CLOSE_ANCHORS}"
        )

    if freq == "1d":
        if offset != 0:
            raise ValueError(
                "session_offset_minutes is not valid for frequency=1d; "
                "use close_anchor=11:30 or close_anchor=15:00"
            )
        if include_tail_partial:
            raise ValueError("include_tail_partial is not valid for frequency=1d")
        if align == BAR_ALIGN_WALL_CLOCK and (anchor or DEFAULT_CLOSE_ANCHOR) == DEFAULT_CLOSE_ANCHOR:
            # Wall-clock daily without a noon anchor is just the official day.
            align = BAR_ALIGN_OFFICIAL
        if (anchor or DEFAULT_CLOSE_ANCHOR) == NOON_CLOSE_ANCHOR:
            align = BAR_ALIGN_WALL_CLOCK
        return SessionOffsetRequest(
            frequency=freq,
            bar_align=align,
            session_offset_minutes=0,
            close_anchor=anchor or DEFAULT_CLOSE_ANCHOR,
            include_tail_partial=False,
        )

    if freq == "1m":
        if offset != 0 or (anchor not in (None, DEFAULT_CLOSE_ANCHOR)):
            raise ValueError(
                "session offset / close_anchor cannot be applied to frequency=1m"
            )
        return SessionOffsetRequest(frequency=freq)

    if freq not in SUPPORTED_INTRADAY_FREQUENCIES:
        if offset != 0 or (anchor not in (None, DEFAULT_CLOSE_ANCHOR)) or align == BAR_ALIGN_WALL_CLOCK:
            raise ValueError(
                f"session offset / close_anchor is not defined for frequency={freq!r}"
            )
        return SessionOffsetRequest(frequency=freq)

    if anchor not in (None, DEFAULT_CLOSE_ANCHOR):
        raise ValueError(
            "close_anchor is only valid for frequency=1d; "
            "intraday frequencies use session_offset_minutes"
        )
    period = PERIOD_MINUTES[freq]
    if not 0 <= offset <= period:
        raise ValueError(
            f"session_offset_minutes must be in [0, {period}] for frequency={freq}"
        )
    if offset == period and freq not in {"5m", "15m", "30m", "60m"}:
        raise ValueError(
            f"session_offset_minutes={offset} equals the full period for frequency={freq}"
        )
    if offset != 0:
        align = BAR_ALIGN_WALL_CLOCK
    return SessionOffsetRequest(
        frequency=freq,
        bar_align=align,
        session_offset_minutes=offset,
        close_anchor=DEFAULT_CLOSE_ANCHOR,
        include_tail_partial=bool(include_tail_partial),
    )


def assign_intraday_bucket_minute(
    minute_of_day: int,
    *,
    period_minutes: int,
    offset_minutes: int = 0,
    include_tail_partial: bool = False,
) -> int | None:
    """Return the end-label minute for one 1m observation, or None to drop it."""

    for session_start, session_end in CN_A_SESSION_WINDOWS:
        if not session_start <= minute_of_day <= session_end:
            continue
        if offset_minutes == 0 and not include_tail_partial:
            # Official v2: first bucket [start, start+period], later ceil,
            # last bucket capped at session_end.  13:00 stays in the first
            # afternoon bucket.
            first_end = session_start + period_minutes
            if minute_of_day <= first_end:
                return first_end if first_end <= session_end else session_end
            raw = session_start + period_minutes * int(
                -(-int(minute_of_day - session_start) // period_minutes)
            )
            return min(session_end, raw)

        grid_start = session_start + offset_minutes
        if minute_of_day < grid_start:
            return None
        elapsed = minute_of_day - grid_start
        bucket_index = -(-elapsed // period_minutes)  # ceil, 1-based for elapsed>0
        if elapsed == 0:
            bucket_index = 1
        label = grid_start + bucket_index * period_minutes
        if label <= session_end:
            return label
        if include_tail_partial:
            return session_end
        return None
    return None


def first_tradable_slot(*, trading_day: str, bar_close_minute: int) -> str:
    """First tradable clock time after a completed bar."""

    if bar_close_minute < CN_A_MORNING_WINDOW[1]:
        return f"{trading_day}T{minute_to_hhmm(bar_close_minute)}:00Z"
    if bar_close_minute == CN_A_MORNING_WINDOW[1]:
        return f"{trading_day}T{AFTERNOON_OPEN_LABEL}:00Z"
    if bar_close_minute < CN_A_AFTERNOON_WINDOW[1]:
        return f"{trading_day}T{minute_to_hhmm(bar_close_minute)}:00Z"
    return f"{trading_day}T{minute_to_hhmm(CN_A_AFTERNOON_WINDOW[1])}:00Z"


def construction_fields(
    request: SessionOffsetRequest,
    *,
    trading_day: str,
    bar_close_minute: int | None,
) -> dict[str, Any]:
    """Metadata attached only to additive offset / noon-close bars."""

    payload: dict[str, Any] = {
        "bar_align": request.bar_align,
        "session_offset_minutes": request.session_offset_minutes,
        "close_anchor": request.close_anchor_or_default,
        "construction_contract": request.construction_contract,
        "include_tail_partial": request.include_tail_partial,
    }
    if bar_close_minute is None:
        return payload
    close_label = minute_to_hhmm(bar_close_minute)
    payload["bar_close_ts"] = f"{trading_day}T{close_label}:00Z"
    if request.frequency == "1d":
        payload["bar_open_ts"] = f"{trading_day}T{MORNING_OPEN_LABEL}:00Z"
        if request.close_anchor_or_default == NOON_CLOSE_ANCHOR:
            payload["first_tradable_slot"] = f"{trading_day}T{AFTERNOON_OPEN_LABEL}:00Z"
        else:
            payload["first_tradable_slot"] = first_tradable_slot(
                trading_day=trading_day, bar_close_minute=bar_close_minute
            )
        return payload

    period = PERIOD_MINUTES[request.frequency]
    open_minute = bar_close_minute - period
    # Incomplete tail is labeled at session end; open is the last complete
    # grid point, not session_end - period across lunch.
    if open_minute < CN_A_AFTERNOON_WINDOW[0] <= bar_close_minute:
        open_minute = CN_A_AFTERNOON_WINDOW[0] + request.session_offset_minutes
    if open_minute < CN_A_MORNING_WINDOW[0] and bar_close_minute <= CN_A_MORNING_WINDOW[1]:
        open_minute = CN_A_MORNING_WINDOW[0] + request.session_offset_minutes
    payload["bar_open_ts"] = f"{trading_day}T{minute_to_hhmm(open_minute)}:00Z"
    payload["first_tradable_slot"] = first_tradable_slot(
        trading_day=trading_day, bar_close_minute=bar_close_minute
    )
    return payload


def official_60m_labels() -> tuple[str, ...]:
    return ("10:30", "11:30", "14:00", "15:00")


def wall_clock_60m_offset5_labels() -> tuple[str, ...]:
    return ("10:35", "14:05")


def wall_clock_15m_offset15_labels() -> tuple[str, ...]:
    morning = tuple(minute_to_hhmm(minute) for minute in range(600, 691, 15))
    afternoon = tuple(minute_to_hhmm(minute) for minute in range(810, 901, 15))
    return morning + afternoon
