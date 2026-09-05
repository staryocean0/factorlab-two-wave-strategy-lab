"""v0.5.1 characteristic-scale morphology hard gates; no outcomes or trading."""
from __future__ import annotations

import copy
from collections import Counter
from datetime import UTC, datetime, timedelta

import numpy as np

from factor_lab.visual_structure.two_wave.characteristic_scale_v051 import (
    CharacteristicExclusiveLedger,
    build_candidate_features,
    build_characteristic_run,
    characteristic_events,
    link_candidate_families,
    project_event_to_raw,
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


def characteristic_for(values):
    levels, _, features = build_candidate_features(np.log(np.asarray(values, float)))
    members = link_candidate_families(features, levels)
    return levels, characteristic_events(members)


def event_key(event):
    return (
        event.event_id,
        event.family_id,
        event.level,
        event.scale_id,
        event.feature.occurrence_indices,
        event.feature.confirmation_index,
        event.confirmation_index,
        event.scale_selection_delay_bars,
    )


def interior_mode_level(events, period, length):
    interior = [
        event.level
        for event in events
        if 4 * period <= event.feature.occurrence_indices[2] <= length - 4 * period
    ]
    assert interior
    return Counter(interior).most_common(1)[0][0]


def test_strictly_monotonic_raw_price_has_no_characteristic_two_wave():
    for values in (100 + np.arange(600), 1000 - np.arange(600) * 0.5):
        _, events = characteristic_for(values)
        assert events == []


def test_characteristic_scale_tracks_sine_wavelength_before_any_12_48_qualification():
    n = 1600
    t = np.arange(n)
    chosen = []
    for period in (24, 32, 40, 64):
        values = 100 + 5 * np.sin(2 * np.pi * t / period)
        levels, events = characteristic_for(values)
        level = interior_mode_level(events, period, n)
        assert 0 < level < len(levels) - 1
        chosen.append(level)
    assert chosen == sorted(chosen)
    assert len(set(chosen)) >= 3
    assert chosen[0] < chosen[-1]


def test_parent_and_child_oscillations_can_produce_distinct_characteristic_scales():
    n = 1800
    t = np.arange(n)
    values = 100 + 6 * np.sin(2 * np.pi * t / 64) + 1.5 * np.sin(2 * np.pi * t / 8)
    levels, events = characteristic_for(values)
    interior = [event for event in events if 300 <= event.feature.occurrence_indices[2] <= 1500]
    assert interior
    occupied = sorted({event.level for event in interior})
    assert occupied[0] > 0
    assert occupied[-1] < len(levels) - 1
    assert occupied[-1] - occupied[0] >= 5


def test_raw_projection_returns_exact_observed_close_extrema_in_order():
    n = 900
    t = np.arange(n)
    values = 100 + 8 * np.sin(2 * np.pi * t / 32)
    _, events = characteristic_for(values)
    event = next(e for e in events if 250 <= e.feature.occurrence_indices[2] <= 650)
    bars = bars_for(values)
    projected = project_event_to_raw(event, bars)
    assert projected["valid"] is True
    points = projected["points"]
    assert len(points) == 5
    assert all(a["occurrence_bar"] < b["occurrence_bar"] for a, b in zip(points, points[1:]))
    for point in points:
        assert point["price"] == bars[point["occurrence_bar"]]["close"]
        assert point["confirmation_bar"] == event.confirmation_index
    for a, b in zip(points, points[1:]):
        if a["kind"] == "low":
            assert b["price"] > a["price"]
        else:
            assert b["price"] < a["price"]


def test_characteristic_events_and_raw_projection_are_prefix_invariant():
    n = 1200
    cut = 850
    t = np.arange(n)
    values = 100 + 6 * np.sin(2 * np.pi * t / 40) + 0.8 * np.sin(2 * np.pi * t / 9)

    full_levels, _, full_features = build_candidate_features(np.log(values))
    full_members = link_candidate_families(full_features, full_levels)
    full_events = characteristic_events(full_members)

    prefix_levels, _, prefix_features = build_candidate_features(np.log(values[:cut]))
    prefix_members = link_candidate_families(prefix_features, prefix_levels)
    prefix_events = characteristic_events(prefix_members)

    expected = [event_key(event) for event in full_events if event.confirmation_index < cut]
    assert [event_key(event) for event in prefix_events] == expected

    full_bars = bars_for(values)
    prefix_bars = full_bars[:cut]
    expected_projection = []
    for event in full_events:
        if event.confirmation_index < cut:
            projected = project_event_to_raw(event, full_bars)
            expected_projection.append(
                (
                    event.event_id,
                    projected["valid"],
                    projected.get("reason"),
                    projected.get("raw_occurrence_indices"),
                    projected.get("raw_prices"),
                )
            )
    actual_projection = []
    for event in prefix_events:
        projected = project_event_to_raw(event, prefix_bars)
        actual_projection.append(
            (
                event.event_id,
                projected["valid"],
                projected.get("reason"),
                projected.get("raw_occurrence_indices"),
                projected.get("raw_prices"),
            )
        )
    assert actual_projection == expected_projection


def _mock_record(record_id, scale_level, start, end, confirmation, qualified=True):
    return {
        "record_id": record_id,
        "characteristic_scale_level": scale_level,
        "characteristic_scale_id": f"scale_{scale_level}",
        "confirmation_bar": confirmation,
        "confirmation_time": f"2019-01-01T00:{confirmation:02d}:00+00:00",
        "known_at": f"2019-01-01T00:{confirmation:02d}:00+00:00",
        "start_bar": start,
        "end_bar": end,
        "classification": "uncertain",
        "scale_qualified": qualified,
        "selected": False,
        "overlap_suppressed_by": None,
    }


def test_same_time_multiscale_conflict_uses_finer_scale_not_label_or_fit():
    ledger = CharacteristicExclusiveLedger()
    coarse = _mock_record("coarse", 7, 10, 40, 50)
    fine = _mock_record("fine", 5, 12, 38, 50)
    unqualified = _mock_record("unqualified", 2, 0, 9, 49, qualified=False)
    ledger.add_records([coarse, unqualified, fine])
    assert [row["record_id"] for row in ledger.selected] == ["fine"]
    by_id = {row["record_id"]: row for row in ledger.records}
    assert by_id["coarse"]["overlap_suppressed_by"] == "fine"
    assert by_id["unqualified"]["selected"] is False


def test_end_to_end_run_keeps_projection_and_frozen_qualification_separate():
    n = 700
    t = np.arange(n)
    values = 100 + 7 * np.sin(2 * np.pi * t / 24)
    run = build_characteristic_run(bars_for(values))
    assert run.characteristic_events
    assert run.projection_audit
    assert run.evaluated_records
    for record in run.evaluated_records:
        assert record["source"] == "TCSS_v051_characteristic"
        assert record["characteristic_scale_id"].startswith("tcss_sigma_")
        assert record["future_outcome_used"] is False
        assert record["trade_authority"] is False
        assert all(
            point["price"] == values[point["occurrence_bar"]]
            for point in record["points"]
        )


def test_returned_ledger_records_are_not_mutated_by_external_changes():
    ledger = CharacteristicExclusiveLedger()
    record = _mock_record("a", 4, 0, 20, 30)
    ledger.add_records([record])
    snapshot = copy.deepcopy(ledger.selected)
    record["classification"] = "tampered"
    assert ledger.selected == snapshot
