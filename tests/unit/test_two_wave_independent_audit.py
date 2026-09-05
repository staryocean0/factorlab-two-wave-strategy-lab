"""Independent adversarial checks of research causality and geometry contracts.

These fixtures express path-level properties rather than recalculate the
implementation's formulas; they are not independent market morphology labels.
"""

import math
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from factor_lab.visual_structure.two_wave.engine import Engine, run_bars
from factor_lab.visual_structure.two_wave.geometry import fit_geometry
from factor_lab.visual_structure.two_wave.models import Config


def _bars(logs):
    start = datetime(2020, 1, 2, 1, 30, tzinfo=UTC)
    return [
        {"timestamp": (start + timedelta(minutes=i)).isoformat(), **dict.fromkeys(("open", "high", "low", "close"), math.exp(x))}
        for i, x in enumerate(logs)
    ]


def _triangle_path(cycles=7, drift=0.0):
    # Each full raw-price cycle has six legs of known bar duration. A warmup
    # extremum is deliberately present and must not become a full-cycle start.
    return [5 + drift * i + 0.04 * (i % 6 if i % 6 <= 3 else 6 - i % 6) / 3 for i in range(cycles * 6 + 2)]


def _geometry_fixture(values, times=None):
    times = [0, 2, 4, 6, 8] if times is None else times
    pivots = [
        {"occurrence_bar": t, "kind": "low" if i % 2 == 0 else "high", "log_price": x}
        for i, (t, x) in enumerate(zip(times, values, strict=True))
    ]
    interpolated = np.interp(np.arange(times[-1] + 1), times, values)
    return pivots, [{"log_close": float(x)} for x in interpolated]


@pytest.mark.parametrize("drift,expected", [(0.0, "range"), (0.004, "uptrend"), (-0.004, "downtrend")])
def test_known_parallel_channels_have_expected_dimensionless_drift(drift, expected):
    values = [5 + drift * t + (0.04 if i % 2 else 0) for i, t in enumerate([0, 2, 4, 6, 8])]
    pivots, bars = _geometry_fixture(values)
    geometry = fit_geometry(pivots, bars, Config())
    assert geometry["valid"]
    assert geometry["classification"] == expected
    assert geometry["width"] == pytest.approx(0.04)
    assert geometry["D"] == pytest.approx(drift * 8 / 0.04)
    assert geometry["envelope_coverage"] == 1


def test_confirmation_leg_cannot_change_completed_interval_fit():
    pivots, bars = _geometry_fixture([5, 5.04, 5.008, 5.048, 5.016])
    before = fit_geometry(pivots, bars, Config())
    after = fit_geometry(pivots, bars + [{"log_close": 100}, {"log_close": -100}], Config())
    assert before == after
    assert before["fit_end_bar"] == 8
    assert before["fit_bar_count"] == 9


@pytest.mark.parametrize("values", [[5.04, 5, 5.04, 5, 5.04], [5, 5, 5, 5, 5]])
def test_negative_or_zero_regression_width_is_rejected(values):
    pivots, bars = _geometry_fixture(values)
    geometry = fit_geometry(pivots, bars, Config())
    assert not geometry["valid"]
    assert geometry["classification"] == "uncertain"
    assert geometry["D"] is None


def test_zero_net_drift_does_not_hide_opposing_cycle_displacements():
    pivots, bars = _geometry_fixture([5, 5.05, 5.02, 5.05, 5])
    geometry = fit_geometry(pivots, bars, Config())
    assert abs(geometry["D"]) < 1e-10
    assert geometry["classification"] == "uncertain"
    assert "within_phase_direction_conflict" in geometry["attributes"]


def test_frozen_envelope_contains_every_completed_close():
    pivots, bars = _geometry_fixture([5, 5.05, 5.01, 5.08, 5.02], [0, 3, 5, 8, 10])
    geometry = fit_geometry(pivots, bars, Config())
    for i, row in enumerate(bars):
        assert geometry["lower_offset"] + geometry["b"] * i - 1e-12 <= row["log_close"]
        assert row["log_close"] <= geometry["upper_offset"] + geometry["b"] * i + 1e-12


def test_all_confirmed_records_equal_every_truncated_batch_and_stream():
    rows = _bars(_triangle_path(7) + [5.2, 5.05, 4.9])
    # Append a discontinuity and a late delayed record to exercise event order
    # as well as immutable history across very different future suffixes.
    rows[8]["available_at"] = "2020-01-04T00:00:00+00:00"
    full = run_bars(rows).export()
    streaming = Engine()
    for cutoff, row in enumerate(rows):
        streaming.update(row)
        prefix = run_bars(rows[: cutoff + 1]).export()
        assert streaming.export() == prefix
        for field in ("pivots", "cycles", "structures", "events"):
            expected = [r for r in full[field] if r["confirmation_bar"] <= cutoff]
            assert prefix[field] == expected, (field, cutoff)


def test_information_time_never_precedes_any_consumed_bar_availability():
    rows = _bars(_triangle_path())
    rows[5]["available_at"] = "2020-01-04T00:00:00+00:00"
    rows[20]["available_at"] = "2020-01-03T00:00:00+00:00"
    export = run_bars(rows).export()
    available = [datetime.fromisoformat(r.get("available_at", r["timestamp"])) for r in rows]
    for field in ("pivots", "cycles", "structures", "events"):
        for record in export[field]:
            expected = max(available[: record["confirmation_bar"] + 1])
            assert datetime.fromisoformat(record["information_available_time"]) == expected


def test_warmup_extremum_is_not_counted_as_a_complete_wave():
    export = run_bars(_bars(_triangle_path())).export()
    first = export["pivots"][0]
    assert first["left_censored"]
    assert all(first["pivot_id"] not in x["pivot_ids"] for x in export["cycles"] + export["structures"])
    assert all(len(x["pivot_ids"]) == 3 for x in export["cycles"])
    assert all(len(x["pivot_ids"]) == 5 and len(x["cycle_ids"]) == 2 for x in export["structures"])
    cycle_map = {x["cycle_id"]: x for x in export["cycles"]}
    for structure in export["structures"]:
        left, right = [cycle_map[key] for key in structure["cycle_ids"]]
        assert left["pivot_ids"][-1] == right["pivot_ids"][0]
        assert left["phase"] == right["phase"] == structure["phase"]
        assert left["scale_id"] == right["scale_id"] == structure["scale_id"]


def test_overlapping_phase_candidates_do_not_reset_existing_structure_age():
    export = run_bars(_bars(_triangle_path(9))).export()
    states = export["state"]["structure_states"]
    for phase in ("high", "low"):
        first = next(s for s in export["structures"] if s["phase"] == phase)
        state = states[first["structure_id"]]
        assert state["cycle_count"] >= 6
        assert state["right_censored_at_observation_end"]
        assert state["age_bars_since_confirmation"] == len(export["bars"]) - 1 - first["confirmation_bar"]
        counts = [
            e["cycle_count"]
            for e in export["events"]
            if e.get("structure_id") == first["structure_id"] and e["type"] == "structure_cycle_confirmed"
        ]
        assert counts == list(range(3, state["cycle_count"] + 1))
    assert not [e for e in export["events"] if e["type"] == "structure_breakout"]


def test_strong_drift_cannot_manufacture_raw_price_cycles():
    # b > A*omega ensures a strictly increasing continuous path, while the
    # detrended sinusoid has more than twelve cycles.
    logs = [5 + 0.004 * i + 0.01 * math.sin(0.3 * i) for i in range(260)]
    assert all(a < b for a, b in zip(logs, logs[1:], strict=False))
    export = run_bars(_bars(logs)).export()
    assert not export["cycles"]
    assert not export["structures"]


def test_last_mutable_candidate_and_export_copies_cannot_rewrite_past():
    rows = _bars(_triangle_path())
    engine = run_bars(rows[:25])
    snapshot = engine.export()
    frozen = deepcopy(snapshot)
    snapshot["pivots"][0]["price"] = -999
    snapshot["events"].clear()
    assert engine.export() == frozen
    for row in rows[25:]:
        engine.update(row)
    actual = engine.export()
    for field in ("pivots", "cycles", "structures", "events"):
        assert actual[field][: len(frozen[field])] == frozen[field]


def test_invalid_input_is_atomic_and_does_not_poison_subsequent_replay():
    rows = _bars(_triangle_path())
    engine = run_bars(rows[:10])
    frozen = engine.export()
    invalid = dict(rows[10], low=rows[10]["high"] + 1)
    with pytest.raises(ValueError):
        engine.update(invalid)
    assert engine.export() == frozen
    engine.update(rows[10])
    assert engine.export() == run_bars(rows[:11]).export()


def test_fifth_extremum_confirmation_can_already_be_outside_frozen_channel():
    export = run_bars(_bars([5, 5.04, 5, 5.04, 5, 5.04, 5, 5.12])).export()
    structure = next(s for s in export["structures"] if s["confirmation_bar"] == 7)
    assert structure["end_bar"] == 6
    assert structure["geometry"]["fit_end_bar"] == 6
    assert structure["geometry"]["upper_offset"] == pytest.approx(5.04)
    events = [e for e in export["events"] if e.get("structure_id") == structure["structure_id"]]
    assert [e["type"] for e in events] == ["structure_confirmed", "structure_breakout"]
    breakout = events[-1]
    assert breakout["confirmation_already_outside"]
    assert breakout["occurrence_bar"] == breakout["confirmation_bar"] == 7
    assert not breakout["has_position_or_exit_authority"]
    assert export["state"]["structure_states"][structure["structure_id"]]["first_breakout_bar"] == 7


def test_intrabar_high_low_order_is_not_assumed_by_close_baseline():
    rows = _bars([5] * 30)
    for i, row in enumerate(rows):
        row["high"] *= 1 + 0.1 * (i % 3 + 1)
        row["low"] *= 0.8
    export = run_bars(rows).export()
    assert export["pivots"] == export["cycles"] == export["structures"] == []


def test_equal_price_plateau_uses_first_extremum_and_late_confirmation():
    export = run_bars(_bars([5, 5.04, 5.04, 5.04, 5, 5, 5, 5.04])).export()
    high = next(p for p in export["pivots"] if p["kind"] == "high")
    assert high["occurrence_bar"] == 1
    assert high["confirmation_bar"] == 4
    assert high["confirmation_delay_bars"] == 3
    low = export["pivots"][-1]
    assert low["occurrence_bar"] == 4
    assert low["confirmation_bar"] == 7
