"""Definition/property tests, not independent real-market accuracy labels."""
from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from factor_lab.visual_structure.two_wave.candidate_v02 import (
    VARIANTS, CandidateConfig, CandidateEngine, fit_geometry_v02,
)
from factor_lab.visual_structure.two_wave.engine import Engine
from factor_lab.visual_structure.two_wave.geometry import fit_geometry
from factor_lab.visual_structure.two_wave.models import Config


def fixture_geometry(values, times=(0, 10, 20, 30, 40), high_first=False):
    x = np.asarray(values, dtype=float) + 4.0
    rows = [{"log_close": float(v)} for v in np.interp(np.arange(times[-1] + 1), times, x)]
    pivots = [{"occurrence_bar": t, "log_price": float(v),
               "kind": "high" if (i % 2 == 0) == high_first else "low"}
              for i, (t, v) in enumerate(zip(times, x, strict=True))]
    return pivots, rows


def stream_rows():
    # First high is left censored. The next five true extrema have equal
    # detrended width despite different raw cycle ranges and durations.
    t = [0, 2, 3, 4, 23, 24, 26, 40, 55, 70, 90]
    x = [4.05, 4, 4.021, 4.002, 4.041, 4.022, 4.05, 4.0, 4.04, 4.01, 4.06]
    return bars_from_logs(np.interp(np.arange(91), t, x))


def bars_from_logs(logs):
    result = []
    for i, x in enumerate(logs):
        dt = datetime(2015, 1, 5, tzinfo=UTC) + timedelta(minutes=i)
        p = float(np.exp(x))
        result.append({"timestamp": dt.isoformat(), "open": p, "high": p, "low": p, "close": p,
                       "available_at": (dt + timedelta(minutes=2)).isoformat()})
    return result


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("drift,label", [(0, "range"), (.0008, "uptrend"), (-.0008, "downtrend")])
def test_clean_parallel(variant, drift, label):
    t = np.array([0, 10, 20, 30, 40])
    p, b = fixture_geometry(drift * t + np.array([0, .04, 0, .04, 0]))
    g = fit_geometry_v02(p, b, CandidateConfig(geometry_variant=variant))
    assert g["classification"] == label
    assert not g["rejection_reasons"]
    assert g["cycle_detrended_width_ratio"] == pytest.approx(1)


@pytest.mark.parametrize("variant", VARIANTS)
def test_raw_range_counterexample(variant):
    t = np.array([0, 1, 2, 21, 22])
    p, b = fixture_geometry(.001 * t + np.array([0, .02, 0, .02, 0]), tuple(t))
    old = fit_geometry(p, b, Config())
    assert old["attributes"] == ["cycle_amplitude_change"]
    g = fit_geometry_v02(p, b, CandidateConfig(geometry_variant=variant))
    assert g["classification"] == "uptrend"
    assert g["cycle_detrended_width_ratio"] == pytest.approx(1)
    assert g["cycle_amplitude_ratio"] > 1.6
    assert "cycle_amplitude_change" in g["attributes"]
    assert not g["rejection_reasons"]


def test_speed_change_is_explicit_variant_not_global_relaxation():
    p, b = fixture_geometry([0, .021, .002, .027, .012])
    a = fit_geometry_v02(p, b, CandidateConfig())
    c = fit_geometry_v02(p, b, CandidateConfig(geometry_variant="drift_tolerant"))
    assert a["classification"] == "uncertain"
    assert a["rejection_reasons"] == ["uneven_phase_drift"]
    assert c["classification"] == "uptrend"
    assert "uneven_phase_drift" in c["attributes"]
    assert c["rejection_reasons"] == []


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("values", [
    [0, .022, .004, .037, .030],
    [0, .03, .015, .03, -.001],
    [0, .025, 0, .06, 0],
    [0, .04, .01, .02, 0],
])
def test_adversarial_shapes_still_rejected(variant, values):
    p, b = fixture_geometry(values)
    g = fit_geometry_v02(p, b, CandidateConfig(geometry_variant=variant))
    assert g["classification"] == "uncertain"
    assert g["rejection_reasons"]


@pytest.mark.parametrize("variant", VARIANTS)
def test_invalid_width_not_rescued(variant):
    p, b = fixture_geometry([0, 0, 0, 0, 0])
    g = fit_geometry_v02(p, b, CandidateConfig(geometry_variant=variant))
    assert not g["valid"]
    assert g["classification"] == "uncertain"
    assert g["cycle_detrended_width_ratio"] is None


@pytest.mark.parametrize("variant", VARIANTS)
def test_all_closes_not_just_pivots(variant):
    p, b = fixture_geometry([0, .03, 0, .03, 0])
    b[25]["log_close"] += .02
    g = fit_geometry_v02(p, b, CandidateConfig(geometry_variant=variant))
    assert g["cycle_detrended_width_ratio"] > 1
    # Fitter-input stress test; this does not claim these pivots would be
    # produced by the raw reversal detector on the altered path.


@pytest.mark.parametrize("variant", VARIANTS)
def test_no_mutation_or_confirmation_leg_leak(variant):
    p, b = fixture_geometry([0, .021, .002, .027, .012])
    original = copy.deepcopy((p, b))
    cfg = CandidateConfig(geometry_variant=variant)
    g = fit_geometry_v02(p, b, cfg)
    assert (p, b) == original
    assert fit_geometry_v02(p, b + [{"log_close": 1000}], cfg) == g
    assert fit_geometry(p, b, Config())["classification"] == "uncertain"


@pytest.mark.parametrize("variant", VARIANTS)
def test_log_translation_reflection_and_time_unit(variant):
    p, b = fixture_geometry([0, .021, .002, .027, .012])
    cfg = CandidateConfig(geometry_variant=variant)
    g = fit_geometry_v02(p, b, cfg)
    q, rows = copy.deepcopy(p), copy.deepcopy(b)
    for point in q:
        point["log_price"] += 2
    for row in rows:
        row["log_close"] += 2
    shifted = fit_geometry_v02(q, rows, cfg)
    assert shifted["classification"] == g["classification"]
    assert shifted["cycle_detrended_width_ratio"] == pytest.approx(g["cycle_detrended_width_ratio"])
    for point in q:
        point["log_price"] = 12 - point["log_price"]
        point["kind"] = "high" if point["kind"] == "low" else "low"
    for row in rows:
        row["log_close"] = 12 - row["log_close"]
    reflected = fit_geometry_v02(q, rows, cfg)
    expected = {"uptrend": "downtrend", "downtrend": "uptrend"}.get(g["classification"], g["classification"])
    assert reflected["classification"] == expected
    assert reflected["D"] == pytest.approx(-g["D"])
    q, rows = fixture_geometry([0, .021, .002, .027, .012], (0, 20, 40, 60, 80))
    stretched = fit_geometry_v02(q, rows, cfg)
    assert stretched["classification"] == g["classification"]
    assert stretched["D"] == pytest.approx(g["D"])
    assert stretched["cycle_detrended_width_ratio"] == pytest.approx(g["cycle_detrended_width_ratio"])


@pytest.mark.parametrize("variant", VARIANTS)
def test_stream_history_and_each_independent_prefix(variant):
    bars = stream_rows()
    cfg = CandidateConfig(geometry_variant=variant)
    engine = CandidateEngine(cfg)
    emitted, saved = [], []
    for i, bar in enumerate(bars):
        events = engine.update(bar)
        assert all(e["confirmation_bar"] == i for e in events)
        emitted.extend(events)
        saved.append(copy.deepcopy(engine.structures))
    assert emitted == engine.events
    assert engine.structures[0]["classification"] == "uptrend"
    for n in range(1, len(bars) + 1):
        prefix = CandidateEngine(cfg)
        for row in bars[:n]:
            prefix.update(row)
        for field in ("pivots", "cycles", "structures", "events"):
            assert getattr(prefix, field) == [v for v in getattr(engine, field) if v["confirmation_bar"] < n]
        assert saved[n - 1] == prefix.structures
    assert all(e["effective_information_time"] >= e["confirmation_time"] for e in engine.events)
    assert all(not e.get("has_position_or_exit_authority", False) for e in engine.events)


@pytest.mark.parametrize("variant", VARIANTS)
def test_monotonic_raw_price_does_not_invent_cycles(variant):
    engine = CandidateEngine(CandidateConfig(geometry_variant=variant))
    for row in bars_from_logs(4 + .002 * np.arange(200) + .001 * np.sin(np.arange(200))):
        engine.update(row)
    assert not engine.cycles
    assert not engine.structures


def test_instance_isolation_and_version_identity():
    a = CandidateEngine()
    b = CandidateEngine(CandidateConfig(geometry_variant="drift_tolerant"))
    old = Engine()
    assert a.config.scale_id == b.config.scale_id == old.config.scale_id
    assert len({a.config.config_hash, b.config.config_hash, old.config.config_hash}) == 3
    for row in stream_rows():
        a.update(row)
        b.update(row)
        old.update(row)
    assert old.structures[0]["classification"] == "uncertain"
    assert a.structures[0]["classification"] == b.structures[0]["classification"] == "uptrend"
    for engine in (a, b):
        assert [(p["occurrence_bar"], p["confirmation_bar"], p["kind"]) for p in engine.pivots] == [
            (p["occurrence_bar"], p["confirmation_bar"], p["kind"]) for p in old.pivots]
    with pytest.raises(ValueError):
        CandidateConfig(geometry_variant="unknown")
    with pytest.raises(TypeError):
        CandidateEngine(Config())
