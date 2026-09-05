"""v0.4.4 hierarchical candidate-construction tests; no outcomes or trading."""
from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

import numpy as np

from factor_lab.visual_structure.two_wave.same_scale_v04 import evaluate_pair
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig, TemporalMaturityEngine
from factor_lab.visual_structure.two_wave.same_scale_v044 import (
    H16_ROLE,
    HIERARCHY_MODE,
    HierarchicalCycleEngine,
)


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


def triangular_values(turns):
    """Linear close path through exact (bar, price) turning points."""
    last = turns[-1][0]
    out = np.empty(last + 1, dtype=float)
    for (a, pa), (b, pb) in zip(turns, turns[1:]):
        out[a:b + 1] = np.linspace(pa, pb, b - a + 1)
    return out


def micro_cycle_path():
    turns = [
        (0, 100), (4, 110), (8, 100), (12, 109), (16, 99),
        (20, 108), (24, 98), (28, 107), (32, 97), (36, 106),
        (40, 96), (44, 105), (48, 95), (52, 104), (56, 94),
        (60, 103), (64, 93), (68, 102), (72, 92),
    ]
    return triangular_values(turns)


def test_v044_wraps_v043_local_detector_verbatim():
    values = 100 + 2 * np.sin(np.arange(240) * 2 * np.pi / 24)
    baseline = replay(TemporalMaturityEngine, values)
    hierarchy = replay(HierarchicalCycleEngine, values)
    assert hierarchy.local_pivots == baseline.pivots
    assert hierarchy.resets == baseline.resets
    assert hierarchy.local.ledger.records == baseline.ledger.records


def test_subscale_same_phase_returns_are_skipped_without_reanchoring():
    hierarchy = replay(HierarchicalCycleEngine, micro_cycle_path())
    assert hierarchy.parent_cycles
    assert all(
        hierarchy.shape_config.min_cycle <= c["duration_bars"] <= hierarchy.shape_config.max_cycle
        for c in hierarchy.parent_cycles
    )
    assert any(r["reason"] == "same_phase_return_before_min_cycle" for r in hierarchy.skipped_local_pivots)
    assert any(
        r["reason"] == "opposite_extreme_replaced_before_parent_close"
        for r in hierarchy.skipped_local_pivots
    )
    first = hierarchy.parent_cycles[0]
    assert first["duration_bars"] == 16
    assert first["occurrence_bars"][0] == 4
    assert first["occurrence_bars"][-1] == 20
    assert first["collapsed_local_pivot_count"] >= 2
    assert hierarchy.ledger.records


def test_parent_candidates_are_exact_v043_local_extrema_and_frozen_pair_logic():
    hierarchy = replay(HierarchicalCycleEngine, micro_cycle_path())
    local_ids = {p["pivot_id"] for p in hierarchy.local_pivots}
    cfg = hierarchy.shape_config
    for parent in hierarchy.parent_pivots:
        assert parent["source_local_pivot_id"] in local_ids
    for record in hierarchy.ledger.records:
        assert record["candidate_constructor"] == HIERARCHY_MODE
        assert record["local_confirmation_kernel"] == cfg.confirmation_mode
        assert all(pid in local_ids for pid in record["source_local_pivot_ids"])
        baseline = evaluate_pair(record["points"], hierarchy.bars, cfg)
        assert record["scale_qualified"] == baseline["scale_qualified"]
        assert record["scale_rejection_reasons"] == baseline["scale_rejection_reasons"]
        assert record["direction_versions"] == baseline["direction_versions"]
        assert record["classification"] == baseline["classification"]


def test_h16_remains_diagnostic_not_a_structural_configuration_field():
    hierarchy = HierarchicalCycleEngine()
    assert H16_ROLE == "diagnostic_only_not_structural_gate"
    assert not hasattr(hierarchy.shape_config, "parent_h16")
    assert hierarchy.shape_config.min_cycle == 12
    assert hierarchy.shape_config.max_cycle == 48


def test_prefix_append_invariance_for_parent_lineage_and_candidates():
    bars = bars_for(micro_cycle_path())
    online = HierarchicalCycleEngine()
    for i, bar in enumerate(bars):
        before_partition = copy.deepcopy(online.ledger.closed_partition)
        returned = online.update(bar)
        if returned:
            returned[0]["classification"] = "tampered"
        if i % 5 == 0 or i == len(bars) - 1:
            oracle = HierarchicalCycleEngine()
            for prefix_bar in bars[:i + 1]:
                oracle.update(prefix_bar)
            assert online.local_pivots == oracle.local_pivots
            assert online.parent_pivots == oracle.parent_pivots
            assert online.parent_cycles == oracle.parent_cycles
            assert online.skipped_local_pivots == oracle.skipped_local_pivots
            assert online.hierarchy_resets == oracle.hierarchy_resets
            assert online.ledger.records == oracle.ledger.records
            assert online.ledger.closed_partition == oracle.ledger.closed_partition
        assert online.ledger.closed_partition[:len(before_partition)] == before_partition


def test_constant_and_monotonic_paths_do_not_fabricate_parent_pairs():
    for values in (np.ones(200) * 100, 100 + np.arange(200), 300 - np.arange(200)):
        hierarchy = replay(HierarchicalCycleEngine, values)
        assert hierarchy.ledger.records == []
        assert hierarchy.parent_cycles == []


def test_no_parent_candidate_crosses_a_v043_epoch_reset():
    values = np.concatenate([
        100 + 2 * np.sin(np.arange(80) * 2 * np.pi / 24),
        np.linspace(100, 180, 90),
    ])
    hierarchy = replay(HierarchicalCycleEngine, values)
    assert hierarchy.resets
    assert any(r["reason"] == "local_v043_epoch_reset" for r in hierarchy.hierarchy_resets)
    for record in hierarchy.ledger.records:
        assert len({p["epoch"] for p in record["points"]}) == 1
