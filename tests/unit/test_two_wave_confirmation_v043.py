"""v0.4.3 confirmation-kernel ablation tests; no economic outcomes."""
from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from factor_lab.visual_structure.two_wave.same_scale_v04 import ScaleConfig, TimeEngine, direction_versions
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig, TemporalMaturityEngine


def bars_for(values):
    start = datetime(2019, 1, 1, 1, 30, tzinfo=UTC)
    out = []
    for i, price in enumerate(values):
        t = start + timedelta(minutes=5 * i)
        out.append({
            "timestamp": t.isoformat(),
            "available_at": (t + timedelta(hours=6)).isoformat(),
            "open": float(price), "high": float(price), "low": float(price), "close": float(price),
        })
    return out


def replay(engine_cls, values, cfg=None):
    engine = engine_cls(cfg) if cfg is not None else engine_cls()
    for bar in bars_for(values):
        engine.update(bar)
    return engine


@pytest.mark.parametrize("field,value", [
    ("min_leg", 2.5), ("duration_ratio", float("nan")), ("amplitude_ratio", .5),
    ("max_jump_share", 1.1), ("min_cycle", 4), ("timeframe", ""),
    ("confirmation_mode", "other"),
])
def test_invalid_configuration(field, value):
    with pytest.raises(ValueError):
        MaturityConfig(**{field: value})


def test_target_scale_periodic_waves_and_no_short_leg_rejections():
    values = 100 + 2 * np.sin(np.arange(240) * 2 * np.pi / 24)
    engine = replay(TemporalMaturityEngine, values)
    assert engine.ledger.selected
    usable = [p for p in engine.pivots if not p["left_censored"]]
    assert all(b["occurrence_bar"] - a["occurrence_bar"] >= 4 for a, b in zip(usable, usable[1:]))
    assert all("short_leg" not in r["scale_rejection_reasons"] for r in engine.ledger.records)
    assert all(r["confirmation_kernel"] == "opposite_extremum_min_leg_maturity" for r in engine.ledger.records)


def test_three_bar_crash_no_longer_confirms_fake_second_leg():
    values = [100, 102, 104, 106, 110, 105, 100, 95, 102, 108, 111, 112, 113, 114]
    strict3 = replay(TimeEngine, values)
    mature = replay(TemporalMaturityEngine, values)
    assert any(p["kind"] == "high" and p["occurrence_bar"] == 4 and not p["left_censored"] for p in strict3.pivots)
    assert not any(p["kind"] == "high" and p["occurrence_bar"] == 4 and not p["left_censored"] for p in mature.pivots)


def test_nonconsecutive_counter_moves_can_confirm_a_mature_leg():
    values = [100, 102, 104, 106, 110, 108, 109, 106, 107, 104, 105, 102, 103,
              111, 109, 110, 107, 108, 105]
    strict3 = replay(TimeEngine, values)
    mature = replay(TemporalMaturityEngine, values)
    assert any(p["kind"] == "high" and p["occurrence_bar"] == 4 and not p["left_censored"] for p in mature.pivots)
    assert not any(p["kind"] == "high" and p["occurrence_bar"] == 4 and not p["left_censored"] for p in strict3.pivots)


@pytest.mark.parametrize("values", [np.ones(200) * 100, 100 + np.arange(200), 300 - np.arange(200)])
def test_constant_and_monotonic_paths_do_not_fabricate_complete_pairs(values):
    assert replay(TemporalMaturityEngine, values).ledger.records == []


def test_prefix_append_invariance_and_copied_outputs():
    bars = bars_for(100 + 2 * np.sin(np.arange(100) * 2 * np.pi / 24))
    online = TemporalMaturityEngine()
    for i, bar in enumerate(bars):
        before = copy.deepcopy(online.ledger.closed_partition)
        returned = online.update(bar)
        if returned:
            returned[0]["classification"] = "tampered"
        oracle = TemporalMaturityEngine()
        for prefix_bar in bars[:i + 1]:
            oracle.update(prefix_bar)
        assert online.ledger.records == oracle.ledger.records
        assert online.pivots == oracle.pivots
        assert online.resets == oracle.resets
        assert online.ledger.closed_partition[:len(before)] == before


def test_direction_rule_is_literally_frozen_d1_logic():
    cfg_old = ScaleConfig()
    cfg_new = MaturityConfig()
    cases = [
        ([-.2335380601, -.2638717691, -.3512174141], [.4974098292, .3512174141]),
        ([.3, .3, .02], [.6, .02]), ([.3, -.3, .2], [.3, .2]), ([.01, -.02, .03], [.02, .03]),
    ]
    for steps, spans in cases:
        assert direction_versions(steps, spans, cfg_old) == direction_versions(steps, spans, cfg_new)
