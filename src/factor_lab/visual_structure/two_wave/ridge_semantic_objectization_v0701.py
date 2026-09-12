"""Frozen v0.7.1 ridge-supported semantic objectization families."""
from __future__ import annotations

from itertools import combinations
from statistics import median
from typing import Sequence

SALVAGE_CASE_THRESHOLD = 8


def _node_sort_key(row) -> tuple[int, int, str]:
    return (
        int(row.node.occurrence_index),
        int(row.node.confirmation_index),
        str(row.node.node_id),
    )


def eligible_nodes_by_level(ridge_run, chart_start: int, cutoff: int) -> list[list[object]]:
    out: list[list[object]] = []
    for rows in ridge_run.ridge_nodes_by_level:
        eligible = [
            row
            for row in rows
            if int(chart_start) <= int(row.node.occurrence_index) <= int(cutoff)
            and int(row.node.confirmation_index) <= int(cutoff)
        ]
        eligible.sort(key=_node_sort_key)
        out.append(eligible)
    return out


def causal_survival_levels(eligible_levels: Sequence[Sequence[object]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for level, rows in enumerate(eligible_levels):
        for row in rows:
            rid = str(row.ridge_id)
            out[rid] = max(level, out.get(rid, -1))
    return out


def alternating(nodes: Sequence[object]) -> bool:
    return len(nodes) == 5 and all(
        str(a.node.kind) != str(b.node.kind) for a, b in zip(nodes, nodes[1:])
    )


def object_key(nodes: Sequence[object]) -> tuple[str, ...]:
    if len(nodes) != 5:
        raise ValueError("five nodes required")
    ids = tuple(str(x.ridge_id) for x in nodes)
    if len(set(ids)) != 5:
        raise ValueError("five distinct ridge IDs required")
    return ids


def _add(store: dict, level: int, nodes: Sequence[object]) -> None:
    nodes = tuple(nodes)
    if not alternating(nodes):
        return
    key = object_key(nodes)
    store.setdefault(key, []).append({"level": int(level), "nodes": nodes})


def _eligible_realization(nodes: Sequence[object], chart_start: int, cutoff: int) -> bool:
    return all(
        int(chart_start) <= int(x.node.occurrence_index) <= int(cutoff)
        and int(x.node.confirmation_index) <= int(cutoff)
        for x in nodes
    )


def family_f0_legacy_exact(ridge_run, chart_start: int, cutoff: int) -> dict:
    store: dict = {}
    for level, rows in enumerate(ridge_run.tuples_by_level):
        for row in rows:
            if _eligible_realization(row.nodes, chart_start, cutoff):
                _add(store, level, row.nodes)
    return store


def family_f1_ordered_common_scale(ridge_run, chart_start: int, cutoff: int) -> dict:
    store: dict = {}
    levels = eligible_nodes_by_level(ridge_run, chart_start, cutoff)
    for level, rows in enumerate(levels):
        for idxs in combinations(range(len(rows)), 5):
            nodes = tuple(rows[i] for i in idxs)
            if alternating(nodes):
                _add(store, level, nodes)
    return store


def family_f2_one_step_survivor(ridge_run, chart_start: int, cutoff: int) -> dict:
    store: dict = {}
    levels = eligible_nodes_by_level(ridge_run, chart_start, cutoff)
    for level in range(len(levels) - 1):
        next_ids = {str(x.ridge_id) for x in levels[level + 1]}
        survivors = [x for x in levels[level] if str(x.ridge_id) in next_ids]
        for i in range(max(0, len(survivors) - 4)):
            nodes = tuple(survivors[i : i + 5])
            if alternating(nodes):
                _add(store, level, nodes)
    return store


def _persistence_dominant(
    rows: Sequence[object], idxs: Sequence[int], survival: dict[str, int]
) -> bool:
    for left_pos, right_pos in zip(idxs, idxs[1:]):
        left = rows[left_pos]
        right = rows[right_pos]
        boundary = min(survival[str(left.ridge_id)], survival[str(right.ridge_id)])
        for skipped in rows[left_pos + 1 : right_pos]:
            if survival[str(skipped.ridge_id)] >= boundary:
                return False
    return True


def family_f3_persistence_dominant(ridge_run, chart_start: int, cutoff: int) -> dict:
    store: dict = {}
    levels = eligible_nodes_by_level(ridge_run, chart_start, cutoff)
    survival = causal_survival_levels(levels)
    for level, rows in enumerate(levels):
        for idxs in combinations(range(len(rows)), 5):
            nodes = tuple(rows[i] for i in idxs)
            if not alternating(nodes):
                continue
            if _persistence_dominant(rows, idxs, survival):
                _add(store, level, nodes)
    return store


def realization_matches_human(realization: dict, cells, kinds, human_bars=None) -> tuple[bool, list[bool]]:
    nodes = realization["nodes"]
    hits = []
    exact = []
    for i, (node, cell, kind) in enumerate(zip(nodes, cells, kinds)):
        occ = int(node.node.occurrence_index)
        hit = (
            int(cell[0]) <= occ <= int(cell[1])
            and str(node.node.kind) == str(kind)
        )
        hits.append(hit)
        if human_bars is not None:
            exact.append(hit and occ == int(human_bars[i]))
    return all(hits), exact


def summarize_family_case(objects: dict, cells, kinds, human_bars) -> dict:
    compatible = []
    ordinal_exact = [False] * 5
    for key, realizations in objects.items():
        key_hit = False
        key_exact = [False] * 5
        for realization in realizations:
            hit, exact = realization_matches_human(realization, cells, kinds, human_bars)
            if hit:
                key_hit = True
                key_exact = [a or b for a, b in zip(key_exact, exact)]
        if key_hit:
            compatible.append(key)
            ordinal_exact = [a or b for a, b in zip(ordinal_exact, key_exact)]
    return {
        "candidate_object_count": len(objects),
        "compatible_object_count": len(compatible),
        "support": bool(compatible),
        "ordinal_exact_anchor": ordinal_exact,
    }


def _dist(values: Sequence[int]) -> dict:
    vals = sorted(int(x) for x in values)
    if not vals:
        return {"count": 0, "median": None, "min": None, "max": None}
    return {
        "count": len(vals),
        "median": float(median(vals)),
        "min": int(vals[0]),
        "max": int(vals[-1]),
    }


def summarize_family_records(records: Sequence[dict]) -> dict:
    rows = list(records)
    if len(rows) != 11:
        raise ValueError("v0701 frozen anchored universe requires exactly 11 cases")
    support = sum(bool(x["support"]) for x in rows)
    compatible_counts = [int(x["compatible_object_count"]) for x in rows]
    candidate_counts = [int(x["candidate_object_count"]) for x in rows]
    exact = [sum(bool(row["ordinal_exact_anchor"][i]) for row in rows) for i in range(5)]
    return {
        "case_count": 11,
        "support_case_count": support,
        "support_fraction": support / 11.0,
        "candidate_object_count": _dist(candidate_counts),
        "compatible_object_count": _dist(compatible_counts),
        "exactly_one_compatible_object_cases": sum(x == 1 for x in compatible_counts),
        "per_ordinal_exact_anchor_case_count": {str(i): exact[i] for i in range(5)},
    }


def frozen_decision(families: dict[str, dict]) -> dict:
    f0 = int(families["F0"]["support_case_count"])
    f1 = int(families["F1"]["support_case_count"])
    f2 = int(families["F2"]["support_case_count"])
    f3 = int(families["F3"]["support_case_count"])
    if f0 != 3:
        raise AssertionError(f"F0 lineage drift: {f0} != 3")
    if f1 != 10:
        raise AssertionError(f"F1 salvage-universe drift: {f1} != 10")
    if f2 >= SALVAGE_CASE_THRESHOLD:
        category = "v0701_one_step_survivor_objectization_candidate_supported"
        selected = "F2_one_step_survivor_skeleton"
    elif f3 >= SALVAGE_CASE_THRESHOLD:
        category = "v0701_persistence_dominant_objectization_candidate_supported"
        selected = "F3_persistence_dominant_nonconsecutive_quintet"
    else:
        category = "v0701_ridge_support_salvaged_but_frozen_objectization_families_insufficient"
        selected = None
    return {
        "salvage_threshold_cases": SALVAGE_CASE_THRESHOLD,
        "primary_category": category,
        "selected_reconstruction_family": selected,
        "F0_lineage_continuity_verified": f0 == 3,
        "F1_upper_bound_continuity_verified": f1 == 10,
        "F2_supported": f2 >= SALVAGE_CASE_THRESHOLD,
        "F3_supported": f3 >= SALVAGE_CASE_THRESHOLD,
    }
