"""Equivalence gates for the v0.5.1 information-clock performance wrapper."""
from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

import numpy as np

from factor_lab.visual_structure.two_wave.characteristic_scale_v051 import build_characteristic_run
from factor_lab.visual_structure.two_wave.characteristic_scale_v051_fast import (
    bars_with_prefix_information_clock,
    build_characteristic_run_fast,
)


def bars_for(values):
    start = datetime(2019, 1, 2, 1, 30, tzinfo=UTC)
    out = []
    for i, price in enumerate(values):
        t = start + timedelta(minutes=5 * i)
        out.append(
            {
                "timestamp": t.isoformat(),
                "available_at": t.isoformat(),
                "trading_day": "2019-01-02",
                "open": float(price),
                "high": float(price),
                "low": float(price),
                "close": float(price),
            }
        )
    return out


def test_prefix_clock_exactly_matches_frozen_naive_fallback_and_preserves_input():
    bars = bars_for([100, 101, 99, 102, 98])
    # Make availability non-monotone so this is not merely current-row time.
    bars[0]["available_at"] = (datetime.fromisoformat(bars[0]["timestamp"]) + timedelta(minutes=30)).isoformat()
    bars[3]["effective_information_time"] = "2099-01-01T00:00:00+00:00"
    before = copy.deepcopy(bars)
    prepared = bars_with_prefix_information_clock(bars)
    assert bars == before
    for i, row in enumerate(prepared):
        if before[i].get("effective_information_time"):
            assert row["effective_information_time"] == before[i]["effective_information_time"]
        else:
            expected = max(v.get("available_at", v["timestamp"]) for v in before[: i + 1])
            assert row["effective_information_time"] == expected


def test_fast_build_is_field_for_field_equivalent_to_frozen_build():
    n = 700
    t = np.arange(n)
    values = 100 + 7 * np.sin(2 * np.pi * t / 24) + 1.5 * np.sin(2 * np.pi * t / 7)
    bars = bars_for(values)
    # One delayed early bar forces the frozen fallback to use a prefix maximum.
    bars[10]["available_at"] = (
        datetime.fromisoformat(bars[10]["timestamp"]) + timedelta(hours=4)
    ).isoformat()
    before = copy.deepcopy(bars)

    frozen = build_characteristic_run(bars)
    fast = build_characteristic_run_fast(bars)

    assert bars == before
    assert fast.scale_levels == frozen.scale_levels
    assert fast.features_by_level == frozen.features_by_level
    assert fast.family_members == frozen.family_members
    assert fast.characteristic_events == frozen.characteristic_events
    assert fast.projection_audit == frozen.projection_audit
    assert fast.evaluated_records == frozen.evaluated_records
    assert fast.ledger.records == frozen.ledger.records
    assert fast.ledger.selected == frozen.ledger.selected
    assert fast.ledger.events == frozen.ledger.events
