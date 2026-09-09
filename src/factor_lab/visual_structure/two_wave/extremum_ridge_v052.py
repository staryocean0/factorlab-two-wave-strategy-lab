"""v0.5.2 causal extremum trajectories and exact-ridge tuple births.

Research component only.  The frozen change from v0.5.1 is structural identity:
individual confirmed TCSS extrema are linked across adjacent scales before any
five-point parent candidate is constructed.  A parent event is the first scale
where the *same five ridge IDs* become consecutive after every intervening
child ridge has a causally certified death in that scale transition.
Qualification, D1, raw projection, outcomes and trading are not redefined here.
"""
from __future__ import annotations

import bisect
import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .characteristic_scale_v051 import (
    CandidateFeature,
    CharacteristicEvent,
    CharacteristicExclusiveLedger,
    project_event_to_raw,
)
from .characteristic_scale_v051_fast import bars_with_prefix_information_clock
from .models import stable_id
from .multiscale_v050 import (
    ConfirmedExtremum,
    ScaleLevel,
    TwoWaveCandidate,
    build_scale_levels,
    confirmed_extrema,
    default_scale_sigmas,
    time_causal_scale_space,
)
from .same_scale_v04 import evaluate_pair
from .same_scale_v043 import MaturityConfig

SCHEMA = "two_wave_extremum_ridge@0.5.2"
REPRESENTATION = "tcss_extremum_trajectory_exact_ridge_tuple_birth"
STRUCTURAL_SCALE_RULE = "exact_ridge_tuple_birth_scale"
RAW_PROJECTION = "sequential_raw_close_extreme_inside_filtered_phase_bounds"


@dataclass(frozen=True)
class ExtremumNode:
    node_id: str
    level: int
    scale_id: str
    sigma_bars: float
    kind: str
    occurrence_index: int
    confirmation_index: int
    value: float
    corrected_occurrence: float


@dataclass(frozen=True)
class RidgeNode:
    node: ExtremumNode
    ridge_id: str
    root_node_id: str


@dataclass(frozen=True)
class RidgeEdge:
    ridge_id: str
    fine_node_id: str
    coarse_node_id: str
    fine_level: int
    coarse_level: int
    confirmation_index: int
    corrected_occurrence_distance: float


@dataclass(frozen=True)
class RidgeDeath:
    ridge_id: str
    fine_node_id: str
    fine_level: int
    coarse_level: int
    kind: str
    occurrence_index: int
    confirmation_index: int
    reason: str = "ordered_coarse_continuation_passed_unmatched_fine_node"


@dataclass(frozen=True)
class LineageAnomaly:
    coarse_node_id: str
    coarse_level: int
    kind: str
    occurrence_index: int
    confirmation_index: int
    reason: str


@dataclass(frozen=True)
class RidgeTupleAtScale:
    tuple_id: str
    level: int
    scale_id: str
    sigma_bars: float
    ridge_ids: tuple[str, ...]
    nodes: tuple[RidgeNode, ...]

    @property
    def occurrence_indices(self) -> tuple[int, ...]:
        return tuple(row.node.occurrence_index for row in self.nodes)

    @property
    def member_confirmation_index(self) -> int:
        return max(row.node.confirmation_index for row in self.nodes)


@dataclass(frozen=True)
class RidgeTupleBirth:
    event_id: str
    tuple_id: str
    level: int
    scale_id: str
    sigma_bars: float
    ridge_ids: tuple[str, ...]
    nodes: tuple[RidgeNode, ...]
    internal_child_deaths: tuple[RidgeDeath, ...]
    confirmation_index: int
    prior_internal_ridge_count: int

    @property
    def occurrence_indices(self) -> tuple[int, ...]:
        return tuple(row.node.occurrence_index for row in self.nodes)


@dataclass
class RidgeRun:
    scale_levels: tuple[ScaleLevel, ...]
    nodes_by_level: tuple[tuple[ExtremumNode, ...], ...]
    ridge_nodes_by_level: tuple[tuple[RidgeNode, ...], ...]
    edges: list[RidgeEdge]
    deaths: list[RidgeDeath]
    lineage_anomalies: list[LineageAnomaly]
    tuples_by_level: tuple[tuple[RidgeTupleAtScale, ...], ...]
    tuple_births: list[RidgeTupleBirth]
    projection_audit: list[dict]
    evaluated_records: list[dict]
    ledger: CharacteristicExclusiveLedger


def kernel_mean_ages(levels: Iterable[ScaleLevel]) -> tuple[float, ...]:
    out = []
    total = 0.0
    for level in levels:
        if level.pole:
            total += level.pole / (1.0 - level.pole)
        out.append(total)
    return tuple(out)


def build_extremum_nodes(
    values: Iterable[float],
    sigmas: Iterable[float] | None = None,
) -> tuple[tuple[ScaleLevel, ...], dict[str, np.ndarray], tuple[tuple[ExtremumNode, ...], ...]]:
    levels = build_scale_levels(default_scale_sigmas() if sigmas is None else sigmas)
    scale_space = time_causal_scale_space(values, [level.sigma_bars for level in levels])
    ages = kernel_mean_ages(levels)
    out = []
    for level in levels:
        extrema = confirmed_extrema(scale_space[level.scale_id], level.scale_id)
        rows = []
        for point in extrema:
            node_id = stable_id(
                "tcss_extremum_node_v052",
                {
                    "schema": SCHEMA,
                    "scale": level.scale_id,
                    "kind": point.kind,
                    "occurrence": point.occurrence_index,
                    "confirmation": point.confirmation_index,
                },
            )
            rows.append(
                ExtremumNode(
                    node_id=node_id,
                    level=level.level,
                    scale_id=level.scale_id,
                    sigma_bars=level.sigma_bars,
                    kind=point.kind,
                    occurrence_index=point.occurrence_index,
                    confirmation_index=point.confirmation_index,
                    value=point.value,
                    corrected_occurrence=float(point.occurrence_index) - ages[level.level],
                )
            )
        out.append(tuple(rows))
    return levels, scale_space, tuple(out)


def _root_ridge_id(node: ExtremumNode) -> str:
    return stable_id("tcss_extremum_ridge_v052", {"root_node_id": node.node_id})


def _link_one_phase(
    fine_nodes: list[RidgeNode],
    coarse_nodes: list[ExtremumNode],
    coarse_level: int,
) -> tuple[list[RidgeNode], list[RidgeEdge], list[RidgeDeath], list[LineageAnomaly]]:
    """Streaming monotone one-to-one continuation for one extremum phase.

    A fine node becomes causally known to have died only when a later ordered
    coarse node matches a fine ancestor to its right.  Trailing unmatched fine
    nodes remain provisional and are therefore not emitted as deaths.
    """

    fine = sorted(
        fine_nodes,
        key=lambda row: (row.node.corrected_occurrence, row.node.confirmation_index, row.node.node_id),
    )
    coarse = sorted(
        coarse_nodes,
        key=lambda row: (row.confirmation_index, row.corrected_occurrence, row.node_id),
    )
    centers = [row.node.corrected_occurrence for row in fine]
    confirmations = [row.node.confirmation_index for row in fine]
    if any(a > b for a, b in zip(centers, centers[1:])):
        raise ValueError("fine corrected occurrences must be ordered")
    if any(a > b for a, b in zip(confirmations, confirmations[1:])):
        raise ValueError("fine confirmations must be ordered within one phase")

    current: list[RidgeNode] = []
    edges: list[RidgeEdge] = []
    deaths: list[RidgeDeath] = []
    anomalies: list[LineageAnomaly] = []
    last_used = -1

    for coarse_node in coarse:
        hi = bisect.bisect_right(confirmations, coarse_node.confirmation_index)
        lo = last_used + 1
        if lo >= hi:
            anomalies.append(
                LineageAnomaly(
                    coarse_node_id=coarse_node.node_id,
                    coarse_level=coarse_level,
                    kind=coarse_node.kind,
                    occurrence_index=coarse_node.occurrence_index,
                    confirmation_index=coarse_node.confirmation_index,
                    reason="no_confirmed_order_preserving_fine_ancestor",
                )
            )
            continue

        pos = bisect.bisect_left(centers, coarse_node.corrected_occurrence, lo, hi)
        options = []
        for idx in (pos - 1, pos):
            if lo <= idx < hi:
                distance = abs(centers[idx] - coarse_node.corrected_occurrence)
                options.append((distance, confirmations[idx], fine[idx].node.node_id, idx))
        if not options:
            anomalies.append(
                LineageAnomaly(
                    coarse_node_id=coarse_node.node_id,
                    coarse_level=coarse_level,
                    kind=coarse_node.kind,
                    occurrence_index=coarse_node.occurrence_index,
                    confirmation_index=coarse_node.confirmation_index,
                    reason="nearest_ancestor_search_empty",
                )
            )
            continue

        distance, _, _, chosen = min(options)
        for idx in range(last_used + 1, chosen):
            row = fine[idx]
            deaths.append(
                RidgeDeath(
                    ridge_id=row.ridge_id,
                    fine_node_id=row.node.node_id,
                    fine_level=row.node.level,
                    coarse_level=coarse_level,
                    kind=row.node.kind,
                    occurrence_index=row.node.occurrence_index,
                    confirmation_index=coarse_node.confirmation_index,
                )
            )
        ancestor = fine[chosen]
        current.append(
            RidgeNode(
                node=coarse_node,
                ridge_id=ancestor.ridge_id,
                root_node_id=ancestor.root_node_id,
            )
        )
        edges.append(
            RidgeEdge(
                ridge_id=ancestor.ridge_id,
                fine_node_id=ancestor.node.node_id,
                coarse_node_id=coarse_node.node_id,
                fine_level=ancestor.node.level,
                coarse_level=coarse_level,
                confirmation_index=coarse_node.confirmation_index,
                corrected_occurrence_distance=float(distance),
            )
        )
        last_used = chosen

    return current, edges, deaths, anomalies


def link_extremum_ridges(
    nodes_by_level: tuple[tuple[ExtremumNode, ...], ...],
) -> tuple[tuple[tuple[RidgeNode, ...], ...], list[RidgeEdge], list[RidgeDeath], list[LineageAnomaly]]:
    if not nodes_by_level:
        raise ValueError("at least one scale level is required")
    first = tuple(
        RidgeNode(node=node, ridge_id=_root_ridge_id(node), root_node_id=node.node_id)
        for node in nodes_by_level[0]
    )
    all_levels: list[tuple[RidgeNode, ...]] = [first]
    edges: list[RidgeEdge] = []
    deaths: list[RidgeDeath] = []
    anomalies: list[LineageAnomaly] = []

    previous = list(first)
    for level in range(1, len(nodes_by_level)):
        current: list[RidgeNode] = []
        for kind in ("low", "high"):
            fine_phase = [row for row in previous if row.node.kind == kind]
            coarse_phase = [row for row in nodes_by_level[level] if row.kind == kind]
            phase_current, phase_edges, phase_deaths, phase_anomalies = _link_one_phase(
                fine_phase,
                coarse_phase,
                level,
            )
            current.extend(phase_current)
            edges.extend(phase_edges)
            deaths.extend(phase_deaths)
            anomalies.extend(phase_anomalies)
        current.sort(key=lambda row: (row.node.occurrence_index, row.node.confirmation_index, row.node.node_id))
        all_levels.append(tuple(current))
        previous = current

    return tuple(all_levels), edges, deaths, anomalies


def build_exact_ridge_tuples(
    ridge_nodes_by_level: tuple[tuple[RidgeNode, ...], ...],
    levels: tuple[ScaleLevel, ...],
) -> tuple[tuple[RidgeTupleAtScale, ...], ...]:
    if len(ridge_nodes_by_level) != len(levels):
        raise ValueError("ridge levels must match scale levels")
    all_rows = []
    for level, nodes in zip(levels, ridge_nodes_by_level):
        ordered = sorted(nodes, key=lambda row: (row.node.occurrence_index, row.node.confirmation_index))
        rows = []
        for i in range(len(ordered) - 4):
            window = tuple(ordered[i : i + 5])
            if any(a.node.kind == b.node.kind for a, b in zip(window, window[1:])):
                continue
            ridge_ids = tuple(row.ridge_id for row in window)
            if len(set(ridge_ids)) != 5:
                raise ValueError("one exact tuple requires five distinct ridges")
            tuple_id = stable_id("tcss_exact_ridge_tuple_v052", {"ridges": ridge_ids})
            rows.append(
                RidgeTupleAtScale(
                    tuple_id=tuple_id,
                    level=level.level,
                    scale_id=level.scale_id,
                    sigma_bars=level.sigma_bars,
                    ridge_ids=ridge_ids,
                    nodes=window,
                )
            )
        all_rows.append(tuple(rows))
    return tuple(all_rows)


def identify_tuple_births(
    tuples_by_level: tuple[tuple[RidgeTupleAtScale, ...], ...],
    ridge_nodes_by_level: tuple[tuple[RidgeNode, ...], ...],
    deaths: Iterable[RidgeDeath],
) -> list[RidgeTupleBirth]:
    deaths_by_transition: dict[int, list[RidgeDeath]] = {}
    for death in deaths:
        deaths_by_transition.setdefault(death.coarse_level, []).append(death)

    births: list[RidgeTupleBirth] = []
    for level in range(1, len(tuples_by_level)):
        previous_tuple_ids = {row.tuple_id for row in tuples_by_level[level - 1]}
        previous_nodes = sorted(
            ridge_nodes_by_level[level - 1],
            key=lambda row: (row.node.occurrence_index, row.node.confirmation_index),
        )
        prev_by_ridge = {row.ridge_id: row for row in previous_nodes}
        prev_positions = {row.ridge_id: i for i, row in enumerate(previous_nodes)}
        transition_deaths = deaths_by_transition.get(level, [])
        death_by_ridge: dict[str, RidgeDeath] = {}
        for death in transition_deaths:
            if death.ridge_id in death_by_ridge:
                raise ValueError("one ridge may die at most once in one adjacent-scale transition")
            death_by_ridge[death.ridge_id] = death

        for row in tuples_by_level[level]:
            if row.tuple_id in previous_tuple_ids:
                continue
            if any(ridge_id not in prev_by_ridge for ridge_id in row.ridge_ids):
                continue
            positions = [prev_positions[ridge_id] for ridge_id in row.ridge_ids]
            if positions != sorted(positions):
                continue
            lo_pos, hi_pos = positions[0], positions[-1]
            prior_internal = previous_nodes[lo_pos : hi_pos + 1]
            if len(prior_internal) <= 5:
                continue
            parent_ids = set(row.ridge_ids)
            expected_child_ids = tuple(
                node.ridge_id for node in prior_internal if node.ridge_id not in parent_ids
            )
            if not expected_child_ids:
                continue
            # Causal adjacency certification: the tuple cannot be published
            # merely because the currently visible coarse list looks adjacent.
            # Every finer-scale ridge that previously lay between the five
            # parents must already have an explicit death in this transition.
            # If even one remains provisional, future coarse information could
            # still enlarge the child-death set and rewrite the birth event.
            if any(ridge_id not in death_by_ridge for ridge_id in expected_child_ids):
                continue
            child_deaths = tuple(death_by_ridge[ridge_id] for ridge_id in expected_child_ids)
            confirmation = max(
                [node.node.confirmation_index for node in row.nodes]
                + [death.confirmation_index for death in child_deaths]
            )
            event_id = stable_id(
                "tcss_exact_ridge_tuple_birth_v052",
                {
                    "tuple_id": row.tuple_id,
                    "level": level,
                    "ridges": row.ridge_ids,
                    "confirmation": confirmation,
                },
            )
            births.append(
                RidgeTupleBirth(
                    event_id=event_id,
                    tuple_id=row.tuple_id,
                    level=level,
                    scale_id=row.scale_id,
                    sigma_bars=row.sigma_bars,
                    ridge_ids=row.ridge_ids,
                    nodes=row.nodes,
                    internal_child_deaths=child_deaths,
                    confirmation_index=confirmation,
                    prior_internal_ridge_count=len(prior_internal),
                )
            )
    births.sort(key=lambda row: (row.confirmation_index, row.level, row.occurrence_indices, row.event_id))
    return births


def _projection_adapter(birth: RidgeTupleBirth) -> CharacteristicEvent:
    extrema = tuple(
        ConfirmedExtremum(
            scale_id=birth.scale_id,
            kind=row.node.kind,
            occurrence_index=row.node.occurrence_index,
            confirmation_index=row.node.confirmation_index,
            value=row.node.value,
        )
        for row in birth.nodes
    )
    candidate = TwoWaveCandidate(birth.scale_id, extrema)
    occurrences = candidate.occurrence_indices
    feature = CandidateFeature(
        level=birth.level,
        scale_id=birth.scale_id,
        sigma_bars=birth.sigma_bars,
        phase=extrema[0].kind,
        occurrence_indices=occurrences,
        confirmation_index=candidate.confirmation_index,
        corrected_center=float(occurrences[2]),
        common_response=None,
        candidate=candidate,
        member_id=stable_id(
            "tcss_exact_ridge_birth_projection_member_v052",
            {"tuple_id": birth.tuple_id, "level": birth.level, "occurrences": occurrences},
        ),
    )
    return CharacteristicEvent(
        event_id=birth.event_id,
        family_id=birth.tuple_id,
        level=birth.level,
        scale_id=birth.scale_id,
        sigma_bars=birth.sigma_bars,
        feature=feature,
        finer_feature=feature,
        coarser_feature=feature,
        confirmation_index=birth.confirmation_index,
        scale_selection_delay_bars=birth.confirmation_index - feature.confirmation_index,
    )


def build_ridge_run(
    bars: list[dict],
    cfg: MaturityConfig | None = None,
    sigmas: Iterable[float] | None = None,
) -> RidgeRun:
    if not bars:
        raise ValueError("bars are required")
    cfg = cfg or MaturityConfig()
    closes = np.asarray([bar["close"] for bar in bars], dtype=float)
    if not np.isfinite(closes).all() or np.any(closes <= 0):
        raise ValueError("positive finite closes required")
    levels, _, nodes_by_level = build_extremum_nodes(np.log(closes), sigmas)
    ridge_nodes_by_level, edges, deaths, anomalies = link_extremum_ridges(nodes_by_level)
    tuples_by_level = build_exact_ridge_tuples(ridge_nodes_by_level, levels)
    births = identify_tuple_births(tuples_by_level, ridge_nodes_by_level, deaths)

    evaluation_bars = bars_with_prefix_information_clock(bars)
    projection_audit: list[dict] = []
    evaluated: list[dict] = []
    for birth in births:
        adapter = _projection_adapter(birth)
        projection = project_event_to_raw(adapter, bars, closes)
        audit = {
            "event_id": birth.event_id,
            "tuple_id": birth.tuple_id,
            "birth_level": birth.level,
            "birth_scale_id": birth.scale_id,
            "birth_sigma_bars": birth.sigma_bars,
            "ridge_ids": list(birth.ridge_ids),
            "filtered_occurrence_bars": list(birth.occurrence_indices),
            "birth_confirmation_bar": birth.confirmation_index,
            "internal_child_death_count": len(birth.internal_child_deaths),
            "internal_child_ridge_ids": [row.ridge_id for row in birth.internal_child_deaths],
            "prior_internal_ridge_count": birth.prior_internal_ridge_count,
            "projection_valid": bool(projection["valid"]),
            "projection_reason": projection.get("reason"),
        }
        if projection["valid"]:
            audit["raw_occurrence_bars"] = list(projection["raw_occurrence_indices"])
            try:
                record = evaluate_pair(
                    list(projection["points"]),
                    evaluation_bars,
                    cfg,
                    source="TCSS_v052_exact_ridge_birth",
                )
            except ValueError as exc:
                audit["projection_valid"] = False
                audit["projection_reason"] = f"evaluate_pair_invalid:{exc}"
            else:
                record["schema_version"] = SCHEMA
                record["record_id"] = stable_id(
                    "tcss_exact_ridge_pair_v052",
                    {
                        "event_id": birth.event_id,
                        "tuple_id": birth.tuple_id,
                        "raw_occurrences": projection["raw_occurrence_indices"],
                        "cfg": cfg.config_hash,
                    },
                )
                record["source"] = "TCSS_v052_exact_ridge_birth"
                record["ridge_tuple_id"] = birth.tuple_id
                record["ridge_ids"] = list(birth.ridge_ids)
                record["birth_scale_level"] = birth.level
                record["birth_scale_id"] = birth.scale_id
                record["birth_sigma_bars"] = birth.sigma_bars
                # Compatibility aliases only: the frozen v0.5.1 ledger sorts
                # qualified records by these names.  Values are identical to
                # the v0.5.2 birth-scale fields and do not change research logic.
                record["characteristic_scale_level"] = birth.level
                record["characteristic_scale_id"] = birth.scale_id
                record["characteristic_sigma_bars"] = birth.sigma_bars
                record["filtered_occurrence_bars"] = list(birth.occurrence_indices)
                record["tuple_birth_confirmation_bar"] = birth.confirmation_index
                record["tuple_birth_delay_bars"] = birth.confirmation_index - adapter.feature.confirmation_index
                record["internal_child_death_count"] = len(birth.internal_child_deaths)
                record["internal_child_ridge_ids"] = [row.ridge_id for row in birth.internal_child_deaths]
                record["prior_internal_ridge_count"] = birth.prior_internal_ridge_count
                record["raw_projection_method"] = RAW_PROJECTION
                record["raw_projection_frozen_at_member_confirmation_bar"] = projection[
                    "projection_frozen_at_member_confirmation_bar"
                ]
                record["trade_authority"] = False
                record["future_outcome_used"] = False
                evaluated.append(record)
        projection_audit.append(audit)

    ledger = CharacteristicExclusiveLedger()
    ledger.add_records(evaluated)
    return RidgeRun(
        scale_levels=levels,
        nodes_by_level=nodes_by_level,
        ridge_nodes_by_level=ridge_nodes_by_level,
        edges=edges,
        deaths=deaths,
        lineage_anomalies=anomalies,
        tuples_by_level=tuples_by_level,
        tuple_births=births,
        projection_audit=projection_audit,
        evaluated_records=evaluated,
        ledger=ledger,
    )
