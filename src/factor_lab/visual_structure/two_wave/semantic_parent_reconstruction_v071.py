"""Frozen v0.7.1 ridge-supported semantic-parent object families.

Development representation reconstruction only.  Family membership is defined
without human-anchor distance fitting; frozen human support cells are used only
for post-construction compatibility auditing.
"""
from __future__ import annotations

from itertools import product
from typing import Sequence

from .semantic_bridge_counteroffensive_v0700 import node_matches, tuple_matches

SALVAGE_CASE_THRESHOLD = 8

F0_EXACT = "legacy_exact_consecutive_five_ridge_tuple"
F1_FULL = "same_scale_full_envelope_five_turn"
F2_CORE = "same_scale_core_envelope_five_turn"
F3_SUBSEQUENCE = "same_scale_ordered_alternating_five_ridge_subsequence"
FAMILIES = (F0_EXACT, F1_FULL, F2_CORE, F3_SUBSEQUENCE)
CHALLENGERS = (F1_FULL, F2_CORE, F3_SUBSEQUENCE)


def cutoff_snapshot(nodes: Sequence, chart_start: int, cutoff: int) -> tuple:
    """Return the causal, chart-visible ridge snapshot frozen by v0.7.1."""
    rows = [
        row
        for row in nodes
        if int(row.node.confirmation_index) <= int(cutoff)
        and int(chart_start) <= int(row.node.occurrence_index) <= int(cutoff)
    ]
    rows.sort(
        key=lambda row: (
            int(row.node.occurrence_index),
            int(row.node.confirmation_index),
            str(row.node.node_id),
        )
    )
    return tuple(rows)


def base_five_turn_object(rows: Sequence) -> bool:
    obj = tuple(rows)
    if len(obj) != 5:
        return False
    if len({str(row.ridge_id) for row in obj}) != 5:
        return False
    occurrences = [int(row.node.occurrence_index) for row in obj]
    if any(b <= a for a, b in zip(occurrences, occurrences[1:])):
        return False
    kinds = [str(row.node.kind) for row in obj]
    if any(a == b for a, b in zip(kinds, kinds[1:])):
        return False
    return True


def _phase_winner(kind: str, rows: Sequence):
    candidates = tuple(rows)
    if not candidates:
        raise ValueError("phase winner requires at least one candidate")
    if str(kind) == "low":
        return min(
            candidates,
            key=lambda row: (
                float(row.node.value),
                -int(row.node.occurrence_index),
                str(row.node.node_id),
            ),
        )
    if str(kind) == "high":
        return min(
            candidates,
            key=lambda row: (
                -float(row.node.value),
                -int(row.node.occurrence_index),
                str(row.node.node_id),
            ),
        )
    raise ValueError(f"unsupported ridge kind: {kind}")


def _slot_interval(obj: Sequence, ordinal: int) -> tuple[int, int]:
    occurrence = [int(row.node.occurrence_index) for row in obj]
    if ordinal == 0:
        return occurrence[0], occurrence[1]
    if ordinal == 4:
        return occurrence[3], occurrence[4]
    return occurrence[ordinal - 1], occurrence[ordinal + 1]


def slot_is_envelope_extreme(obj: Sequence, ordinal: int, snapshot: Sequence) -> bool:
    selected = tuple(obj)[int(ordinal)]
    lo, hi = _slot_interval(obj, int(ordinal))
    kind = str(selected.node.kind)
    competitors = [
        row
        for row in snapshot
        if str(row.node.kind) == kind
        and lo <= int(row.node.occurrence_index) <= hi
    ]
    if not competitors:
        return False
    winner = _phase_winner(kind, competitors)
    return str(winner.node.node_id) == str(selected.node.node_id)


def family_member(family: str, obj: Sequence, snapshot: Sequence) -> bool:
    if family not in CHALLENGERS:
        raise ValueError(f"challenger family required, got {family}")
    if not base_five_turn_object(obj):
        return False
    if family == F3_SUBSEQUENCE:
        return True
    if family == F2_CORE:
        return all(slot_is_envelope_extreme(obj, i, snapshot) for i in (1, 2, 3))
    if family == F1_FULL:
        return all(slot_is_envelope_extreme(obj, i, snapshot) for i in range(5))
    raise AssertionError("unreachable family")


def skipped_snapshot_ridges(obj: Sequence, snapshot: Sequence) -> int:
    positions = {str(row.node.node_id): i for i, row in enumerate(snapshot)}
    selected = [positions[str(row.node.node_id)] for row in obj]
    if selected != sorted(selected):
        raise ValueError("object order differs from snapshot order")
    return int(selected[-1] - selected[0] + 1 - len(selected))


def _empty_family_record() -> dict:
    return {
        "supported": False,
        "compatible_object_count": 0,
        "supported_level_count": 0,
        "minimum_skipped_snapshot_ridges": None,
    }


def audit_case_families(
    ridge_run,
    cells: Sequence[tuple[int, int]],
    kinds: Sequence[str],
    chart_start: int,
    cutoff: int,
) -> dict[str, dict]:
    """Audit the frozen family ladder for one human-anchored case.

    Human cells only restrict the compatibility query.  They never alter family
    membership, envelope dominance, skip counts, or ridge snapshot construction.
    """
    out = {family: _empty_family_record() for family in FAMILIES}

    exact_count = 0
    exact_levels: set[int] = set()
    for level, rows in enumerate(ridge_run.tuples_by_level):
        for row in rows:
            if tuple_matches(row, cells, kinds, cutoff):
                exact_count += 1
                exact_levels.add(int(level))
    out[F0_EXACT] = {
        "supported": exact_count > 0,
        "compatible_object_count": exact_count,
        "supported_level_count": len(exact_levels),
        "minimum_skipped_snapshot_ridges": 0 if exact_count else None,
    }

    challenger_counts = {family: 0 for family in CHALLENGERS}
    challenger_levels = {family: set() for family in CHALLENGERS}
    challenger_skips = {family: [] for family in CHALLENGERS}

    for level, level_nodes in enumerate(ridge_run.ridge_nodes_by_level):
        snapshot = cutoff_snapshot(level_nodes, chart_start, cutoff)
        if len(snapshot) < 5:
            continue
        per_cell = [
            [row for row in snapshot if node_matches(row, cell, kind, cutoff)]
            for cell, kind in zip(cells, kinds)
        ]
        if not all(per_cell):
            continue

        for obj in product(*per_cell):
            if not base_five_turn_object(obj):
                continue
            skip_count = skipped_snapshot_ridges(obj, snapshot)
            for family in CHALLENGERS:
                if not family_member(family, obj, snapshot):
                    continue
                challenger_counts[family] += 1
                challenger_levels[family].add(int(level))
                challenger_skips[family].append(int(skip_count))

    for family in CHALLENGERS:
        count = int(challenger_counts[family])
        out[family] = {
            "supported": count > 0,
            "compatible_object_count": count,
            "supported_level_count": len(challenger_levels[family]),
            "minimum_skipped_snapshot_ridges": min(challenger_skips[family]) if challenger_skips[family] else None,
        }
    return out


def distribution(values: Sequence[int | float]) -> dict:
    vals = sorted(float(x) for x in values)
    if not vals:
        return {"count": 0, "median": None, "min": None, "max": None}
    n = len(vals)
    median = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0
    return {"count": n, "median": median, "min": vals[0], "max": vals[-1]}


def summarize_family_records(records: Sequence[dict[str, dict]]) -> dict:
    rows = list(records)
    if len(rows) != 11:
        raise ValueError("v0.7.1 frozen universe requires exactly 11 anchored cases")
    summary: dict[str, dict] = {}
    for family in FAMILIES:
        support = sum(bool(row[family]["supported"]) for row in rows)
        object_counts = [int(row[family]["compatible_object_count"]) for row in rows]
        level_counts = [int(row[family]["supported_level_count"]) for row in rows]
        min_skips = [
            int(row[family]["minimum_skipped_snapshot_ridges"])
            for row in rows
            if row[family]["minimum_skipped_snapshot_ridges"] is not None
        ]
        summary[family] = {
            "support_count": int(support),
            "support_fraction": support / len(rows),
            "passes_development_salvage_threshold": support >= SALVAGE_CASE_THRESHOLD,
            "compatible_object_count": distribution(object_counts),
            "supported_level_count": distribution(level_counts),
            "minimum_skipped_snapshot_ridges_on_supported_cases": distribution(min_skips),
            "aggregate_compatible_object_count": int(sum(object_counts)),
        }
    return summary


def frozen_adjudication(summary: dict[str, dict]) -> dict:
    exact = int(summary[F0_EXACT]["support_count"])
    if exact >= SALVAGE_CASE_THRESHOLD:
        category = "v071_legacy_exact_tuple_control_drift_or_contradiction"
        selected = None
    elif int(summary[F1_FULL]["support_count"]) >= SALVAGE_CASE_THRESHOLD:
        category = "v071_full_envelope_parent_objectization_development_rescue_supported"
        selected = F1_FULL
    elif int(summary[F2_CORE]["support_count"]) >= SALVAGE_CASE_THRESHOLD:
        category = "v071_core_envelope_parent_objectization_development_rescue_supported"
        selected = F2_CORE
    elif int(summary[F3_SUBSEQUENCE]["support_count"]) >= SALVAGE_CASE_THRESHOLD:
        category = "v071_ordered_subsequence_parent_objectization_development_rescue_supported"
        selected = F3_SUBSEQUENCE
    else:
        category = "v071_prespecified_ridge_supported_object_families_do_not_rescue_semantic_parent"
        selected = None
    return {
        "salvage_threshold_cases": SALVAGE_CASE_THRESHOLD,
        "primary_category": category,
        "selected_development_challenger_family": selected,
        "development_challenger_selected": selected is not None,
    }
