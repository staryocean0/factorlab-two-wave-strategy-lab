# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from datahub.storage.query.session_offset_contract import (
    BAR_ALIGN_OFFICIAL,
    BAR_ALIGN_WALL_CLOCK,
    DEFAULT_CLOSE_ANCHOR,
    NOON_CLOSE_ANCHOR,
    OFFICIAL_SESSION_CONTRACT_ID,
    SESSION_OFFSET_CONTRACT_ID,
    assign_intraday_bucket_minute,
    hhmm_to_minute,
    minute_to_hhmm,
    normalize_session_offset_request,
    official_60m_labels,
    wall_clock_15m_offset15_labels,
    wall_clock_60m_offset5_labels,
)


def _labels_for_day(minutes: list[int], **kwargs) -> list[str]:
    labels: list[int] = []
    seen: set[int] = set()
    for minute in minutes:
        bucket = assign_intraday_bucket_minute(minute, **kwargs)
        if bucket is None or bucket in seen:
            continue
        seen.add(bucket)
        labels.append(bucket)
    return [minute_to_hhmm(item) for item in labels]


def test_official_request_keeps_v2_contract() -> None:
    request = normalize_session_offset_request(frequency="60m")
    assert request.uses_official_contract
    assert request.construction_contract == OFFICIAL_SESSION_CONTRACT_ID
    assert request.bar_align == BAR_ALIGN_OFFICIAL
    assert request.close_anchor_or_default == DEFAULT_CLOSE_ANCHOR


def test_60m_offset_5_uses_additive_contract() -> None:
    request = normalize_session_offset_request(
        frequency="60m",
        session_offset_minutes=5,
    )
    assert not request.uses_official_contract
    assert request.construction_contract == SESSION_OFFSET_CONTRACT_ID
    assert request.bar_align == BAR_ALIGN_WALL_CLOCK
    assert request.session_offset_minutes == 5


def test_noon_close_daily_uses_additive_contract() -> None:
    request = normalize_session_offset_request(
        frequency="1d",
        close_anchor="11:30",
    )
    assert request.close_anchor == NOON_CLOSE_ANCHOR
    assert request.construction_contract == SESSION_OFFSET_CONTRACT_ID
    assert request.bar_align == BAR_ALIGN_WALL_CLOCK


@pytest.mark.parametrize(
    ("frequency", "kwargs", "message"),
    [
        ("1d", {"session_offset_minutes": 5}, "not valid for frequency=1d"),
        ("60m", {"close_anchor": "11:30"}, "only valid for frequency=1d"),
        ("60m", {"session_offset_minutes": 61}, "must be in \\[0, 60\\]"),
        ("1m", {"session_offset_minutes": 5}, "cannot be applied to frequency=1m"),
        ("1d", {"close_anchor": "10:00"}, "unsupported close_anchor"),
        ("60m", {"bar_align": "hilbert_phase"}, "unsupported bar_align"),
    ],
)
def test_normalize_rejects_illegal_combinations(
    frequency: str,
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        normalize_session_offset_request(frequency=frequency, **kwargs)


def test_official_60m_gold_labels() -> None:
    minutes = list(range(570, 691)) + list(range(780, 901))
    labels = _labels_for_day(minutes, period_minutes=60, offset_minutes=0)
    assert labels == list(official_60m_labels())
    assert "13:00" not in labels


def test_wall_clock_60m_offset5_gold_labels() -> None:
    minutes = list(range(570, 691)) + list(range(780, 901))
    labels = _labels_for_day(minutes, period_minutes=60, offset_minutes=5)
    assert labels == list(wall_clock_60m_offset5_labels())
    assert "10:30" not in labels
    assert "13:00" not in labels
    assert assign_intraday_bucket_minute(570, period_minutes=60, offset_minutes=5) is None
    assert assign_intraday_bucket_minute(575, period_minutes=60, offset_minutes=5) == 635
    assert assign_intraday_bucket_minute(690, period_minutes=60, offset_minutes=5) is None
    assert assign_intraday_bucket_minute(780, period_minutes=60, offset_minutes=5) is None
    assert assign_intraday_bucket_minute(785, period_minutes=60, offset_minutes=5) == 845


def test_wall_clock_15m_offset15_gold_labels() -> None:
    minutes = list(range(570, 691)) + list(range(780, 901))
    labels = _labels_for_day(minutes, period_minutes=15, offset_minutes=15)
    assert labels == list(wall_clock_15m_offset15_labels())
    assert assign_intraday_bucket_minute(570, period_minutes=15, offset_minutes=15) is None
    assert assign_intraday_bucket_minute(585, period_minutes=15, offset_minutes=15) == 600
    assert labels[0] == "10:00"
    assert "09:45" not in labels


def test_include_tail_partial_keeps_incomplete_last_bucket() -> None:
    assert (
        assign_intraday_bucket_minute(
            hhmm_to_minute("11:30"),
            period_minutes=60,
            offset_minutes=5,
            include_tail_partial=True,
        )
        == 690
    )


def test_5m_offset_equal_to_period_is_allowed() -> None:
    request = normalize_session_offset_request(
        frequency="5m",
        session_offset_minutes=5,
    )
    assert request.session_offset_minutes == 5
    assert request.construction_contract == SESSION_OFFSET_CONTRACT_ID
