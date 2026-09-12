"""Memory-efficient, definition-equivalent v0.7.1 family enumeration.

This module changes only the enumeration implementation: it streams scale
realizations into unique ridge-ID sets instead of materializing every
realization in nested dictionaries. Scientific family definitions are unchanged.
"""
from __future__ import annotations

from typing import Iterator, Sequence

from .ridge_semantic_objectization_v0701 import (
    _eligible_realization,
    _node_sort_key,
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


def evaluate_f1_case(ridge_run, chart_start, cutoff, cells, kinds, human_bars) -> dict:
    add, result = _collector(cells, kinds, human_bars)
    levels = eligible_nodes_by_level(ridge_run, chart_start, cutoff)
    for level, rows in enumerate(levels):
        for idxs in alternating_quintet_indices(rows):
            add(level, tuple(rows[i] for i in idxs))
    return result()


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
