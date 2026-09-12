"""Definition-equivalent exact DP/counting for v0.7.1 F3.

F3 remains the frozen persistence-dominant nonconsecutive quintet. This module
only avoids materializing the full quintet combination space.
"""
from __future__ import annotations

from itertools import product

from .ridge_semantic_objectization_v0701 import causal_survival_levels
from .ridge_semantic_objectization_stream_v0701 import _ridge_level_masks


def _edge_is_dominant(rows, i: int, j: int, survival: dict[str, int]) -> bool:
    left = rows[i]
    right = rows[j]
    if str(left.node.kind) == str(right.node.kind):
        return False
    boundary = min(survival[str(left.ridge_id)], survival[str(right.ridge_id)])
    return all(
        survival[str(skipped.ridge_id)] < boundary
        for skipped in rows[i + 1 : j]
    )


def _dominant_edge_masks(levels, survival) -> dict[tuple[str, str], int]:
    edges: dict[tuple[str, str], int] = {}
    for level, rows in enumerate(levels):
        bit = 1 << level
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                if not _edge_is_dominant(rows, i, j, survival):
                    continue
                key = (str(rows[i].ridge_id), str(rows[j].ridge_id))
                edges[key] = edges.get(key, 0) | bit
    return edges


def _count_unique_f3_objects(ordered, edge_masks) -> int:
    """Count unique ordered five-ridge paths having one common valid level."""
    outgoing: dict[str, list[tuple[str, int]]] = {}
    for (left, right), mask in edge_masks.items():
        outgoing.setdefault(left, []).append((right, int(mask)))

    # dp[length][last_ridge][common_level_mask] = number of unique ridge-ID paths.
    dp: list[dict[str, dict[int, int]]] = [dict() for _ in range(6)]
    for left in ordered:
        for right, mask in outgoing.get(left, []):
            bucket = dp[2].setdefault(right, {})
            bucket[mask] = bucket.get(mask, 0) + 1

    for length in range(3, 6):
        current: dict[str, dict[int, int]] = {}
        for last, states in dp[length - 1].items():
            for nxt, edge_mask in outgoing.get(last, []):
                bucket = current.setdefault(nxt, {})
                for common_mask, count in states.items():
                    new_mask = int(common_mask) & int(edge_mask)
                    if new_mask:
                        bucket[new_mask] = bucket.get(new_mask, 0) + int(count)
        dp[length] = current
    return sum(sum(states.values()) for states in dp[5].values())


def _compatible_f3(levels, survival, cells, kinds, human_bars) -> dict:
    compatible: set[tuple[str, ...]] = set()
    ordinal_exact = [False] * 5
    for rows in levels:
        pos = {str(row.ridge_id): i for i, row in enumerate(rows)}
        choices = []
        for cell, kind in zip(cells, kinds):
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
            positions = [pos[rid] for rid in ids]
            if positions != sorted(positions):
                continue
            if not all(
                _edge_is_dominant(rows, a, b, survival)
                for a, b in zip(positions, positions[1:])
            ):
                continue
            compatible.add(ids)
            for i, node in enumerate(nodes):
                if int(node.node.occurrence_index) == int(human_bars[i]):
                    ordinal_exact[i] = True
    return {
        "compatible_object_count": len(compatible),
        "support": bool(compatible),
        "ordinal_exact_anchor": ordinal_exact,
    }


def evaluate_f3_case_dp(ridge_run, chart_start, cutoff, cells, kinds, human_bars) -> dict:
    levels, ordered, _, _ = _ridge_level_masks(ridge_run, chart_start, cutoff)
    survival = causal_survival_levels(levels)
    edge_masks = _dominant_edge_masks(levels, survival)
    count = _count_unique_f3_objects(ordered, edge_masks)
    compatible = _compatible_f3(levels, survival, cells, kinds, human_bars)
    return {
        "candidate_object_count": int(count),
        **compatible,
    }
