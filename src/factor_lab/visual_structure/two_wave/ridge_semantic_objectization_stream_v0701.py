"""Memory-efficient, definition-equivalent v0.7.1 family enumeration.

This module changes only enumeration/counting implementation. Scientific
family definitions, support conditions, and unique ridge-ID object semantics
are unchanged.
"""
from __future__ import annotations

from itertools import product
from typing import Iterator, Sequence

from .ridge_semantic_objectization_v0701 import (
    _eligible_realization,
    causal_survival_levels,
    eligible_nodes_by_level,
    object_key,
    realization_matches_human,
)


def alternating_quintet_indices(rows: Sequence[object]) -> Iterator[tuple[int, int, int, int, int]]:
    n = len(rows)
    chosen: list[int] = []

    def rec(start: int):
        need = 5 - len(chosen)
        if n - start < need:
            return
        if len(chosen) == 5:
            yield tuple(chosen)
            return
        prev_kind = None if not chosen else str(rows[chosen[-1]].node.kind)
        last_start = n - need
        for idx in range(start, last_start + 1):
            if prev_kind is not None and str(rows[idx].node.kind) == prev_kind:
                continue
            chosen.append(idx)
            yield from rec(idx + 1)
            chosen.pop()

    yield from rec(0)


def _dominant_incremental(rows, idxs, survival) -> bool:
    for left_pos, right_pos in zip(idxs, idxs[1:]):
        boundary = min(
            survival[str(rows[left_pos].ridge_id)],
            survival[str(rows[right_pos].ridge_id)],
        )
        for skipped in rows[left_pos + 1 : right_pos]:
            if survival[str(skipped.ridge_id)] >= boundary:
                return False
    return True


def _collector(cells, kinds, human_bars):
    candidate_keys: set[tuple[str, ...]] = set()
    compatible_keys: set[tuple[str, ...]] = set()
    ordinal_exact = [False] * 5

    def add(level: int, nodes: Sequence[object]):
        key = object_key(nodes)
        candidate_keys.add(key)
        realization = {"level": int(level), "nodes": tuple(nodes)}
        hit, exact = realization_matches_human(realization, cells, kinds, human_bars)
        if hit:
            compatible_keys.add(key)
            for i, value in enumerate(exact):
                ordinal_exact[i] = ordinal_exact[i] or bool(value)

    def result() -> dict:
        return {
            "candidate_object_count": len(candidate_keys),
            "compatible_object_count": len(compatible_keys),
            "support": bool(compatible_keys),
            "ordinal_exact_anchor": ordinal_exact,
        }

    return add, result


def evaluate_f0_case(ridge_run, chart_start, cutoff, cells, kinds, human_bars) -> dict:
    add, result = _collector(cells, kinds, human_bars)
    for level, rows in enumerate(ridge_run.tuples_by_level):
        for row in rows:
            if _eligible_realization(row.nodes, chart_start, cutoff):
                add(level, row.nodes)
    return result()


def _ridge_level_masks(ridge_run, chart_start: int, cutoff: int):
    """Return global ridge order plus eligible-level bit masks.

    With zero lineage anomalies every ridge ID originates at level 0 and ridge
    order is preserved across scales. An F1 ridge-ID quintet exists iff the
    five eligible-level masks have non-empty intersection.
    """
    levels = eligible_nodes_by_level(ridge_run, chart_start, cutoff)
    masks: dict[str, int] = {}
    kinds: dict[str, str] = {}
    for level, rows in enumerate(levels):
        bit = 1 << level
        for row in rows:
            rid = str(row.ridge_id)
            masks[rid] = masks.get(rid, 0) | bit
            kinds.setdefault(rid, str(row.node.kind))
            if kinds[rid] != str(row.node.kind):
                raise AssertionError("ridge kind changed across scale")

    global_rows = sorted(
        ridge_run.ridge_nodes_by_level[0],
        key=lambda x: (int(x.node.occurrence_index), int(x.node.confirmation_index), str(x.node.node_id)),
    )
    ordered = [str(row.ridge_id) for row in global_rows if masks.get(str(row.ridge_id), 0)]
    if len(ordered) != len(set(ordered)):
        raise AssertionError("level-0 ridge IDs must be unique")
    if set(ordered) != set(masks):
        raise AssertionError("eligible higher-level ridge lacks level-0 root identity")
    return levels, ordered, masks, kinds


def _count_f1_unique_objects(ordered, masks, kinds) -> int:
    # DP state: number of unique ordered ridge-ID sequences of a given length,
    # last kind and exact common-eligible-level mask. Each ridge ID is processed
    # once in global order, so every ridge-ID object contributes exactly once.
    dp = [{"low": {}, "high": {}} for _ in range(6)]
    for rid in ordered:
        mask = int(masks[rid])
        kind = str(kinds[rid])
        other = "high" if kind == "low" else "low"
        for length in range(5, 1, -1):
            for prev_mask, count in list(dp[length - 1][other].items()):
                common = int(prev_mask) & mask
                if common:
                    dp[length][kind][common] = dp[length][kind].get(common, 0) + int(count)
        dp[1][kind][mask] = dp[1][kind].get(mask, 0) + 1
    return sum(dp[5][kind].values() for kind in ("low", "high"))


def _f1_compatible_summary(levels, cells, required_kinds, human_bars) -> dict:
    compatible_keys: set[tuple[str, ...]] = set()
    ordinal_exact = [False] * 5
    for level, rows in enumerate(levels):
        choices = []
        for cell, kind in zip(cells, required_kinds):
            matches = [
                row for row in rows
                if str(row.node.kind) == str(kind)
                and int(cell[0]) <= int(row.node.occurrence_index) <= int(cell[1])
            ]
            choices.append(matches)
        if not all(choices):
            continue
        for nodes in product(*choices):
            ids = tuple(str(x.ridge_id) for x in nodes)
            if len(set(ids)) != 5:
                continue
            # Frozen cells are ordered/non-overlapping, so occurrence order is automatic.
            compatible_keys.add(ids)
            for i, node in enumerate(nodes):
                if int(node.node.occurrence_index) == int(human_bars[i]):
                    ordinal_exact[i] = True
    return {
        "compatible_object_count": len(compatible_keys),
        "support": bool(compatible_keys),
        "ordinal_exact_anchor": ordinal_exact,
    }


def evaluate_f1_case(ridge_run, chart_start, cutoff, cells, kinds, human_bars) -> dict:
    levels, ordered, masks, ridge_kinds = _ridge_level_masks(ridge_run, chart_start, cutoff)
    candidate_count = _count_f1_unique_objects(ordered, masks, ridge_kinds)
    compatible = _f1_compatible_summary(levels, cells, kinds, human_bars)
    return {
        "candidate_object_count": int(candidate_count),
        **compatible,
    }


def evaluate_f2_case(ridge_run, chart_start, cutoff, cells, kinds, human_bars) -> dict:
    add, result = _collector(cells, kinds, human_bars)
    levels = eligible_nodes_by_level(ridge_run, chart_start, cutoff)
    for level in range(len(levels) - 1):
        next_ids = {str(x.ridge_id) for x in levels[level + 1]}
        survivors = [x for x in levels[level] if str(x.ridge_id) in next_ids]
        for i in range(max(0, len(survivors) - 4)):
            nodes = tuple(survivors[i : i + 5])
            if all(str(a.node.kind) != str(b.node.kind) for a, b in zip(nodes, nodes[1:])):
                add(level, nodes)
    return result()


def evaluate_f3_case(ridge_run, chart_start, cutoff, cells, kinds, human_bars) -> dict:
    add, result = _collector(cells, kinds, human_bars)
    levels = eligible_nodes_by_level(ridge_run, chart_start, cutoff)
    survival = causal_survival_levels(levels)
    for level, rows in enumerate(levels):
        for idxs in alternating_quintet_indices(rows):
            if _dominant_incremental(rows, idxs, survival):
                add(level, tuple(rows[i] for i in idxs))
    return result()
