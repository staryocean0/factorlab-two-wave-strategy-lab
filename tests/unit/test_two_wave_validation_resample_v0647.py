import pandas as pd
import pytest

from factor_lab.visual_structure.two_wave.validation_resample_v0647 import (
    exact_ohlc_timestamp_equivalence,
    resample_five_minute_offset,
)


def _session(day: str, start: str, rows: int = 10):
    ts = pd.date_range(f"{day} {start}", periods=rows, freq="1min", tz="Asia/Shanghai").tz_convert("UTC")
    out = []
    for i, t in enumerate(ts):
        base = 100.0 + i
        out.append({
            "timestamp": t,
            "trading_day": day,
            "open": base,
            "high": base + 2.0,
            "low": base - 1.0,
            "close": base + 1.0,
        })
    return out


def test_offset0_uses_complete_five_minute_packs_and_last_timestamp():
    frame = pd.DataFrame(_session("2024-01-02", "09:31", 10))
    out = resample_five_minute_offset(frame, 0)
    assert len(out) == 2
    assert out.iloc[0]["open"] == 100.0
    assert out.iloc[0]["high"] == 106.0
    assert out.iloc[0]["low"] == 99.0
    assert out.iloc[0]["close"] == 105.0
    assert out.iloc[0]["timestamp"] == frame.iloc[4]["timestamp"]


def test_offset1_discards_session_edge_fragments():
    frame = pd.DataFrame(_session("2024-01-02", "09:31", 10))
    out = resample_five_minute_offset(frame, 1)
    assert len(out) == 1
    assert out.iloc[0]["timestamp"] == frame.iloc[5]["timestamp"]
    assert out.iloc[0]["open"] == frame.iloc[1]["open"]
    assert out.iloc[0]["close"] == frame.iloc[5]["close"]


def test_lunch_sessions_are_independent():
    frame = pd.DataFrame(
        _session("2024-01-02", "09:31", 5) + _session("2024-01-02", "13:01", 5)
    )
    out = resample_five_minute_offset(frame, 0)
    assert len(out) == 2
    assert out.iloc[0]["timestamp"] == frame.iloc[4]["timestamp"]
    assert out.iloc[1]["timestamp"] == frame.iloc[9]["timestamp"]


def test_missing_source_minute_discards_only_affected_pack():
    rows = _session("2024-01-02", "09:31", 10)
    del rows[2]
    frame = pd.DataFrame(rows)
    out = resample_five_minute_offset(frame, 0)
    assert len(out) == 1
    assert out.iloc[0]["timestamp"] == frame.iloc[-1]["timestamp"]


def test_equivalence_is_strict_on_timestamp_and_every_ohlc_field():
    frame = pd.DataFrame(_session("2024-01-02", "09:31", 5))
    a = resample_five_minute_offset(frame, 0)
    b = a.copy()
    assert exact_ohlc_timestamp_equivalence(a, b)["exact"] is True
    b.loc[0, "high"] += 0.01
    result = exact_ohlc_timestamp_equivalence(a, b)
    assert result["exact"] is False
    assert result["price_equal"]["high"] is False


def test_outside_session_fails_closed():
    frame = pd.DataFrame(_session("2024-01-02", "09:30", 5))
    with pytest.raises(ValueError, match="outside canonical"):
        resample_five_minute_offset(frame, 0)
