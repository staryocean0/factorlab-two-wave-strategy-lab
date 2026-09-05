"""Synthetic implementation checks; none of these supplies real-market labels."""

import copy
import json
import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from factor_lab.visual_structure.two_wave import Config, Engine, run_bars
from factor_lab.visual_structure.two_wave.geometry import fit_geometry


def make_bars(log_prices):
    start = datetime(2016, 1, 4, 1, 35, tzinfo=UTC)
    result = []
    for i, value in enumerate(log_prices):
        price = math.exp(4.6 + float(value))
        result.append(
            {"timestamp": (start + timedelta(minutes=5 * i)).isoformat(), "open": price, "high": price, "low": price, "close": price}
        )
    return result


def triangle_bars(slope=0.0, cycles=6):
    indices = np.arange(cycles * 20 + 1)
    triangle = np.interp(indices, np.arange(0, cycles * 20 + 1, 10), [0.02 * (i % 2) for i in range(cycles * 2 + 1)])
    return make_bars(triangle + slope * indices)


@pytest.mark.parametrize("slope,expected", [(0.0, "range"), (0.0004, "uptrend"), (-0.0004, "downtrend")])
def test_two_complete_cycles_and_symmetric_phase_classification(slope, expected):
    engine = run_bars(triangle_bars(slope), Config(reversal_log=0.005))
    assert len(engine.structures) >= 2
    assert {s["phase"] for s in engine.structures} == {"high", "low"}
    assert {s["classification"] for s in engine.structures} == {expected}
    for structure in engine.structures:
        assert len(structure["pivot_ids"]) == 5
        assert len(structure["cycle_ids"]) == 2
        assert structure["confirmation_bar"] > structure["end_bar"]
        assert structure["geometry"]["fit_end_bar"] == structure["end_bar"]
        assert structure["geometry"]["envelope_coverage"] == 1.0
    censored = engine.pivots[0]
    assert censored["left_censored"]
    assert all(censored["pivot_id"] not in c["pivot_ids"] for c in engine.cycles)


def test_strong_raw_drift_has_no_fabricated_cycles():
    t = np.arange(300)
    engine = run_bars(make_bars(0.002 * t + 0.01 * np.sin(0.1 * t)), Config(reversal_log=0.005))
    assert len(engine.pivots) == 1
    assert engine.pivots[0]["left_censored"]
    assert engine.cycles == []
    assert engine.structures == []
    assert engine.snapshot()["warmup_status"] == "insufficient_confirmed_reversals"


def test_constant_price_and_first_extreme_on_plateau():
    assert run_bars(make_bars([0] * 80)).pivots == []
    engine = run_bars(make_bars([0, 0.02, 0.02, 0.02, 0, -0.02, -0.02, 0]))
    high = next(p for p in engine.pivots if p["kind"] == "high")
    low = engine.pivots[-1]
    assert high["occurrence_bar"] == 1
    assert high["confirmation_bar"] == 4
    assert low["occurrence_bar"] == 5


def geometry_from_values(values, middle_closes=None):
    full = []
    for i, value in enumerate(values):
        if i:
            full.append((values[i - 1] + value) / 2 if middle_closes is None else middle_closes[i - 1])
        full.append(value)
    bars = [{"log_close": value} for value in full]
    pivots = [{"occurrence_bar": i * 2, "log_price": value, "kind": "low" if i % 2 == 0 else "high"} for i, value in enumerate(values)]
    return fit_geometry(pivots, bars, Config())


@pytest.mark.parametrize(
    "values,attribute",
    [
        ([0, 0.03, 0.015, 0.03, 0], "within_phase_direction_conflict"),
        ([0, 0.04, 0.01, 0.03, 0.02], "converging"),
        ([0, 0.02, -0.01, 0.03, -0.02], "expanding"),
        ([0, 0.03, 0, 0.08, 0.05], "uneven_phase_drift"),
    ],
)
def test_conflicts_convergence_expansion_and_jump_are_not_flattened_to_range(values, attribute):
    geometry = geometry_from_values(values)
    assert geometry["classification"] == "uncertain"
    assert attribute in geometry["attributes"]


def test_negative_width_is_invalid_and_full_bar_coverage_is_separately_reported():
    invalid = geometry_from_values([1, 0, 1, 0, 1])
    assert invalid["width"] < 0
    assert invalid["valid"] is False
    assert invalid["D"] is None
    geometry = geometry_from_values([0, 0.02, 0, 0.02, 0], [0.03, 0.01, 0.01, 0.01])
    assert geometry["nominal_coverage"] < 1.0
    assert geometry["envelope_coverage"] == 1.0
    assert geometry["envelope_width"] > geometry["width"]


def test_confirmation_leg_excluded_and_already_outside_not_backdated():
    # The first low is censored. The fifth usable high at bar 5 needs bar 6
    # to confirm; its large confirming fall is already below the old envelope.
    engine = run_bars(make_bars([0, 0.02, 0, 0.02, 0, 0.02, -0.08]))
    structure = engine.structures[0]
    event = next(e for e in engine.events if e["type"] == "structure_breakout")
    assert structure["end_bar"] == 5
    assert structure["geometry"]["fit_bar_count"] == 5
    assert structure["geometry"]["envelope_width"] == pytest.approx(0.02)
    assert event["confirmation_already_outside"] is True
    assert event["confirmation_bar"] == 6
    assert event["direction"] == "down"
    assert event["has_position_or_exit_authority"] is False


def test_old_structure_age_does_not_reset_and_alive_end_is_censored():
    engine = run_bars(triangle_bars(cycles=8), Config(reversal_log=0.005))
    first = engine.structures[0]
    state = engine.snapshot()["structure_states"][first["structure_id"]]
    assert state["cycle_count"] >= 6
    assert state["geometry_alive"] is True
    assert state["right_censored_at_observation_end"] is True
    assert first["initial_cycle_count"] == 2
    assert not any(e["type"] == "structure_breakout" for e in engine.events)
    assert len({s["structure_id"] for s in engine.structures}) == len(engine.structures)


def test_every_prefix_stream_batch_agrees_and_future_never_rewrites_records():
    bars = triangle_bars(cycles=3) + make_bars([])
    config = Config(reversal_log=0.005)
    streaming = Engine(config)
    snapshots = []
    for count, bar in enumerate(bars, 1):
        streaming.update(bar)
        full = streaming.export()
        assert full == run_bars(bars[:count], config).export()
        snapshots.append(full)
    final = streaming.export()
    for prefix in snapshots:
        for field in ("pivots", "cycles", "structures", "events"):
            assert final[field][: len(prefix[field])] == prefix[field]
    json.dumps(final, allow_nan=False)
    detached = streaming.export()
    detached["pivots"][0]["price"] = 123
    assert streaming.pivots[0]["price"] != 123


def test_availability_clock_is_prefix_max_and_not_bar_end_time():
    bars = make_bars([0, 0.02, 0, 0.02, 0, 0.02, 0])
    late = "2016-01-04T07:30:00+00:00"
    bars[0]["available_at"] = late
    engine = run_bars(bars)
    assert all(e["information_available_time"] == late for e in engine.events)
    assert engine.events[0]["confirmation_time"] < late
    assert engine.structures[0]["effective_information_time"] == late
    assert engine.snapshot()["bar_end_assumed"] is True


@pytest.mark.parametrize(
    "mutation",
    [
        {"timestamp": "2016-01-04T10:00:00"},
        {"close": float("nan")},
        {"low": 200},
        {"open": -1},
        {"available_at": "2015-01-01T00:00:00+00:00"},
    ],
)
def test_bad_rows_are_rejected_without_mutating_engine(mutation):
    bar = make_bars([0])[0]
    engine = Engine()
    original = copy.deepcopy(engine.export())
    bar.update(mutation)
    with pytest.raises(ValueError):
        engine.update(bar)
    assert engine.export() == original


def test_timestamp_duplicates_are_rejected_and_gaps_are_not_filled():
    bars = make_bars([0, 0.02])
    bars[-1]["timestamp"] = "2016-01-05T01:35:00+00:00"
    engine = run_bars(bars)
    assert len(engine.bars) == 2
    assert engine.bars[-1]["bar_index"] == 1
    with pytest.raises(ValueError, match="strictly increasing"):
        engine.update(bars[-1])


def test_scale_identity_is_independent_of_classification_thresholds():
    first, second = Config(), Config(drift_threshold=0.6)
    assert first.scale_id == second.scale_id
    assert first.config_hash != second.config_hash
    with pytest.raises(AttributeError):
        Engine(first).config = second
    with pytest.raises(ValueError):
        Config(reversal_log=0)
