"""Synthetic hard gates for v0.5.2 extremum-ridge parent identity.

These tests intentionally precede any v0.5.2 real-data result.  They test the
frozen structural change only: immutable single-extremum ridge identity and
exact-five-ridge tuple birth after internal child-ridge death.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np

from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import (
    ExtremumNode,
    RidgeDeath,
    RidgeNode,
    _link_one_phase,
    build_exact_ridge_tuples,
    build_extremum_nodes,
    build_ridge_run,
    identify_tuple_births,
    link_extremum_ridges,
)
from factor_lab.visual_structure.two_wave.multiscale_v050 import ScaleLevel


def _node(level: int, kind: str, occurrence: int, confirmation: int, name: str) -> ExtremumNode:
    sigma = float(2**level)
    return ExtremumNode(
        node_id=f"n_{name}_{level}",
        level=level,
        scale_id=f"s{level}",
        sigma_bars=sigma,
        kind=kind,
        occurrence_index=occurrence,
        confirmation_index=confirmation,
        value=float(occurrence),
        corrected_occurrence=float(occurrence),
    )


def _ridge(level: int, kind: str, occurrence: int, name: str) -> RidgeNode:
    node = _node(level, kind, occurrence, occurrence + 1, name)
    return RidgeNode(node=node, ridge_id=f"r_{name}", root_node_id=f"root_{name}")


def _bars_from_log(log_values: np.ndarray) -> list[dict]:
    start = datetime(2019, 1, 2, 1, 30, tzinfo=UTC)
    values = np.exp(np.asarray(log_values, dtype=float))
    rows = []
    for i, price in enumerate(values):
        stamp = start + timedelta(minutes=5 * i)
        rows.append(
            {
                "timestamp": stamp.isoformat(),
                "available_at": stamp.isoformat(),
                "trading_day": stamp.date().isoformat(),
                "open": float(price),
                "high": float(price),
                "low": float(price),
                "close": float(price),
            }
        )
    return rows


def _ridge_signature(run, cutoff: int):
    nodes = []
    for level_rows in run.ridge_nodes_by_level:
        for row in level_rows:
            if row.node.confirmation_index < cutoff:
                nodes.append(
                    (
                        row.node.level,
                        row.node.node_id,
                        row.ridge_id,
                        row.root_node_id,
                        row.node.occurrence_index,
                        row.node.confirmation_index,
                    )
                )
    edges = sorted(
        (
            row.fine_level,
            row.coarse_level,
            row.fine_node_id,
            row.coarse_node_id,
            row.ridge_id,
            row.confirmation_index,
        )
        for row in run.edges
        if row.confirmation_index < cutoff
    )
    deaths = sorted(
        (
            row.fine_level,
            row.coarse_level,
            row.fine_node_id,
            row.ridge_id,
            row.confirmation_index,
        )
        for row in run.deaths
        if row.confirmation_index < cutoff
    )
    births = sorted(
        (
            row.event_id,
            row.tuple_id,
            row.level,
            row.ridge_ids,
            row.occurrence_indices,
            row.confirmation_index,
        )
        for row in run.tuple_births
        if row.confirmation_index < cutoff
    )
    return sorted(nodes), edges, deaths, births


def test_streaming_same_phase_link_preserves_ancestor_ids_and_emits_only_passed_child_death():
    fine = [
        RidgeNode(_node(0, "low", 10, 11, "p0"), "ridge_p0", "root_p0"),
        RidgeNode(_node(0, "low", 20, 21, "child"), "ridge_child", "root_child"),
        RidgeNode(_node(0, "low", 30, 31, "p1"), "ridge_p1", "root_p1"),
    ]
    coarse = [
        _node(1, "low", 11, 12, "c0"),
        _node(1, "low", 31, 32, "c1"),
    ]

    current, edges, deaths, anomalies = _link_one_phase(fine, coarse, 1)
    assert not anomalies
    assert [row.ridge_id for row in current] == ["ridge_p0", "ridge_p1"]
    assert [row.ridge_id for row in edges] == ["ridge_p0", "ridge_p1"]
    assert [(row.ridge_id, row.confirmation_index) for row in deaths] == [("ridge_child", 32)]

    # Future coarse information may add later continuation/death events, but it
    # must not rewrite the already-confirmed first continuation.
    prefix_current, prefix_edges, prefix_deaths, prefix_anomalies = _link_one_phase(fine[:1], coarse[:1], 1)
    assert not prefix_anomalies
    assert not prefix_deaths
    assert prefix_current[0].ridge_id == current[0].ridge_id
    assert prefix_edges[0] == edges[0]


def test_exact_parent_tuple_birth_requires_same_five_ridges_and_internal_child_death():
    levels = (
        ScaleLevel(0, 1.0, 1.0, 0.0),
        ScaleLevel(1, 2.0, 3.0, 0.0),
    )
    # The five intended parent ridges are r0..r4.  At the finer scale c1/c2
    # sit between r0 and r1, so the parent five are not consecutive.  After the
    # two child ridges die, exactly the same five parent ridge IDs become
    # consecutive at the coarser scale.
    fine = (
        _ridge(0, "low", 10, "r0"),
        _ridge(0, "high", 14, "c1"),
        _ridge(0, "low", 18, "c2"),
        _ridge(0, "high", 30, "r1"),
        _ridge(0, "low", 50, "r2"),
        _ridge(0, "high", 70, "r3"),
        _ridge(0, "low", 90, "r4"),
    )
    coarse = tuple(
        _ridge(1, kind, occurrence, name)
        for kind, occurrence, name in (
            ("low", 11, "r0"),
            ("high", 31, "r1"),
            ("low", 51, "r2"),
            ("high", 71, "r3"),
            ("low", 91, "r4"),
        )
    )
    ridge_levels = (fine, coarse)
    tuples = build_exact_ridge_tuples(ridge_levels, levels)
    parent_ids = tuple(f"r_r{i}" for i in range(5))
    parent_tuple_id = next(row.tuple_id for row in tuples[1] if row.ridge_ids == parent_ids)
    assert parent_tuple_id not in {row.tuple_id for row in tuples[0]}

    deaths = [
        RidgeDeath("r_c1", fine[1].node.node_id, 0, 1, "high", 14, 33),
        RidgeDeath("r_c2", fine[2].node.node_id, 0, 1, "low", 18, 33),
    ]
    births = identify_tuple_births(tuples, ridge_levels, deaths)
    parent_births = [row for row in births if row.tuple_id == parent_tuple_id]
    assert len(parent_births) == 1
    birth = parent_births[0]
    assert birth.level == 1
    assert birth.ridge_ids == parent_ids
    assert {row.ridge_id for row in birth.internal_child_deaths} == {"r_c1", "r_c2"}
    assert birth.prior_internal_ridge_count == 7

    # Without the topology-changing child deaths this is not a parent birth.
    assert not [row for row in identify_tuple_births(tuples, ridge_levels, []) if row.tuple_id == parent_tuple_id]


def test_strict_monotonic_raw_price_has_no_parent_birth_or_raw_two_wave():
    for log_values in (
        5.0 + np.arange(700) * 1e-4,
        5.0 - np.arange(700) * 1e-4,
    ):
        run = build_ridge_run(_bars_from_log(log_values))
        assert run.tuple_births == []
        assert run.evaluated_records == []
        assert run.ledger.selected == []


def test_nested_parent_child_waves_create_topology_births_without_member_sliding():
    # Frozen before real-data observation: three different parent/child ratios.
    settings = (
        (80, 16, 0.30),
        (96, 24, 0.25),
        (64, 16, 0.40),
    )
    n = 1600
    t = np.arange(n, dtype=float)
    for parent_period, child_period, child_ratio in settings:
        signal = (
            5.0
            + 0.020 * np.sin(2 * np.pi * t / parent_period)
            + 0.020 * child_ratio * np.sin(2 * np.pi * t / child_period)
        )
        levels, _, nodes = build_extremum_nodes(signal)
        ridge_levels, _, deaths, anomalies = link_extremum_ridges(nodes)
        tuples = build_exact_ridge_tuples(ridge_levels, levels)
        births = identify_tuple_births(tuples, ridge_levels, deaths)

        assert births, (parent_period, child_period, child_ratio)
        assert all(row.level >= 1 for row in births)
        assert all(len(set(row.ridge_ids)) == 5 for row in births)
        assert all(row.internal_child_deaths for row in births)
        # A tuple ID is exact-ridge identity: every appearance of that ID must
        # have exactly the same ordered ridge members, never a sliding window.
        identity = {}
        for rows in tuples:
            for row in rows:
                prior = identity.setdefault(row.tuple_id, row.ridge_ids)
                assert prior == row.ridge_ids

        # Normal nested waves should not need invented coarse roots as a common
        # mechanism.  Any anomaly is retained, but it may not dominate nodes.
        coarse_node_count = sum(len(rows) for rows in ridge_levels[1:])
        assert len(anomalies) < max(1, coarse_node_count // 100)


def test_chirp_prefix_replay_does_not_rewrite_confirmed_ridges_deaths_or_tuple_births():
    n = 1200
    t = np.arange(n, dtype=float)
    phase = 2 * np.pi * (t / 55.0 + 0.5 * (1 / 32.0 - 1 / 55.0) * t * t / n)
    log_values = 5.0 + 0.018 * np.sin(phase) + 0.004 * np.sin(2.7 * phase)
    bars = _bars_from_log(log_values)
    full = build_ridge_run(bars)

    for fraction in (0.25, 0.50, 0.75):
        cutoff = int(n * fraction)
        prefix = build_ridge_run(bars[:cutoff])
        assert _ridge_signature(prefix, cutoff) == _ridge_signature(full, cutoff)


def test_single_jump_with_small_noise_cannot_become_qualified_parent_two_wave():
    n = 900
    t = np.arange(n, dtype=float)
    log_values = 5.0 + 0.00015 * np.sin(2 * np.pi * t / 13)
    log_values[t >= 450] += 0.08
    run = build_ridge_run(_bars_from_log(log_values))
    assert run.ledger.selected == []
