"""Frozen helpers for v0.7.0 semantic-bridge counteroffensive / salvage staircase."""
from __future__ import annotations

from collections import Counter
from typing import Sequence

import numpy as np

LOOKBACK_BARS = 96
SALVAGE_CASE_THRESHOLD = 8


def infer_human_kinds(human_bars: Sequence[int], closes: Sequence[float]) -> list[str]:
    h = [int(x) for x in human_bars]
    if len(h) != 5 or any(b <= a for a, b in zip(h, h[1:])):
        raise ValueError("five strictly increasing human anchors required")
    x = [float(closes[i]) for i in h]
    if any(a == b for a, b in zip(x, x[1:])):
        raise ValueError("adjacent human anchor prices must differ")
    first = "low" if x[1] > x[0] else "high"
    kinds = [first if i % 2 == 0 else ("high" if first == "low" else "low") for i in range(5)]
    for i in range(4):
        if kinds[i] == "low" and not x[i + 1] > x[i]:
            raise ValueError("human anchors do not form alternating price turns")
        if kinds[i] == "high" and not x[i + 1] < x[i]:
            raise ValueError("human anchors do not form alternating price turns")
    return kinds


def human_support_cells(human_bars: Sequence[int], chart_start: int, cutoff: int) -> list[tuple[int, int]]:
    h = [int(x) for x in human_bars]
    if len(h) != 5 or any(b <= a for a, b in zip(h, h[1:])):
        raise ValueError("five strictly increasing human anchors required")
    if chart_start > h[0] or cutoff < h[-1]:
        raise ValueError("human anchors must lie in chart")
    cells: list[tuple[int, int]] = []
    for i in range(5):
        if i == 0:
            left = max(chart_start, h[0] - (h[1] - h[0]) // 2)
        else:
            left = (h[i - 1] + h[i]) // 2 + 1
        if i == 4:
            right = min(cutoff, h[4] + (h[4] - h[3]) // 2)
        else:
            right = (h[i] + h[i + 1]) // 2
        if not (left <= h[i] <= right):
            raise AssertionError("human anchor escaped deterministic support cell")
        if cells and left <= cells[-1][1]:
            raise AssertionError("support cells overlap")
        cells.append((left, right))
    return cells


def in_cell(bar: int, cell: tuple[int, int]) -> bool:
    return int(cell[0]) <= int(bar) <= int(cell[1])


def raw_cell_extreme(cell: tuple[int, int], kind: str, closes: Sequence[float]) -> int:
    lo, hi = map(int, cell)
    vals = np.asarray([float(x) for x in closes[lo : hi + 1]], dtype=float)
    if vals.ndim != 1 or not len(vals) or not np.isfinite(vals).all():
        raise ValueError("finite nonempty close cell required")
    target = float(np.min(vals)) if kind == "low" else float(np.max(vals))
    pos = np.flatnonzero(vals == target)
    return lo + int(pos[-1])


def node_matches(node, cell: tuple[int, int], kind: str, cutoff: int) -> bool:
    return (
        str(node.node.kind) == str(kind)
        and in_cell(int(node.node.occurrence_index), cell)
        and int(node.node.confirmation_index) <= int(cutoff)
    )


def common_scale_support(ridge_run, cells: Sequence[tuple[int, int]], kinds: Sequence[str], cutoff: int) -> dict:
    common_levels: list[int] = []
    nearest_distances = [None] * 5
    for level, nodes in enumerate(ridge_run.ridge_nodes_by_level):
        per_ordinal = []
        for i, (cell, kind) in enumerate(zip(cells, kinds)):
            matches = [row for row in nodes if node_matches(row, cell, kind, cutoff)]
            per_ordinal.append(matches)
        if all(per_ordinal):
            common_levels.append(level)
            for i, matches in enumerate(per_ordinal):
                anchor_center = None
                # caller later replaces the nearest-distance placeholder using human anchor bars.
                if nearest_distances[i] is None:
                    nearest_distances[i] = []
                nearest_distances[i].extend(int(x.node.occurrence_index) for x in matches)
    return {"common_levels": common_levels, "occurrences_by_ordinal": nearest_distances}


def tuple_matches(row, cells: Sequence[tuple[int, int]], kinds: Sequence[str], cutoff: int) -> bool:
    if len(row.nodes) != 5:
        return False
    for node, cell, kind in zip(row.nodes, cells, kinds):
        if not node_matches(node, cell, kind, cutoff):
            return False
    return True


def count_exact_tuple_support(ridge_run, cells, kinds, cutoff: int) -> int:
    count = 0
    for level_rows in ridge_run.tuples_by_level:
        for row in level_rows:
            if tuple_matches(row, cells, kinds, cutoff):
                count += 1
    return count


def count_tuple_birth_support(ridge_run, cells, kinds, cutoff: int) -> int:
    count = 0
    for birth in ridge_run.tuple_births:
        if int(birth.confirmation_index) > int(cutoff):
            continue
        if len(birth.nodes) != 5:
            continue
        if all(
            str(node.node.kind) == str(kind)
            and in_cell(int(node.node.occurrence_index), cell)
            and int(node.node.confirmation_index) <= int(cutoff)
            for node, cell, kind in zip(birth.nodes, cells, kinds)
        ):
            count += 1
    return count


def five_bars_hit_cells(bars: Sequence[int], first_kind: str, cells, kinds) -> tuple[bool, list[bool]]:
    values = [int(x) for x in bars]
    if len(values) != 5:
        raise ValueError("five bars required")
    model_kinds = [first_kind if i % 2 == 0 else ("high" if first_kind == "low" else "low") for i in range(5)]
    hits = [
        model_kinds[i] == str(kinds[i]) and in_cell(values[i], cells[i])
        for i in range(5)
    ]
    return all(hits), hits


def summarize_cases(records: Sequence[dict]) -> dict:
    rows = list(records)
    if len(rows) != 11:
        raise ValueError("v0700 frozen universe requires exactly 11 cases")
    layer_counts = {key: sum(bool(r[key]) for r in rows) for key in ("L0", "L1", "L2", "L3", "L4", "L5")}
    raw_exact = [sum(bool(r["raw_anchor_exact"][i]) for r in rows) for i in range(5)]
    l4_hits = [sum(bool(r["L4_hits"][i]) for r in rows) for i in range(5)]
    l5_hits = [sum(bool(r["L5_hits"][i]) for r in rows) for i in range(5)]
    nearest = [[] for _ in range(5)]
    common_scale_counts = []
    exact_tuple_counts = []
    birth_counts = []
    for row in rows:
        common_scale_counts.append(int(row["common_scale_level_count"]))
        exact_tuple_counts.append(int(row["exact_tuple_match_count"]))
        birth_counts.append(int(row["tuple_birth_match_count"]))
        for i, value in enumerate(row["nearest_common_scale_ridge_distance"]):
            if value is not None:
                nearest[i].append(int(value))

    def dist(values):
        vals = sorted(float(x) for x in values)
        if not vals:
            return {"count": 0, "median": None, "min": None, "max": None}
        n = len(vals)
        return {
            "count": n,
            "median": vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0,
            "min": vals[0],
            "max": vals[-1],
        }

    transitions = {
        "L1_true_L2_false": sum(bool(r["L1"]) and not bool(r["L2"]) for r in rows),
        "L2_true_L3_false": sum(bool(r["L2"]) and not bool(r["L3"]) for r in rows),
        "L3_true_L4_false": sum(bool(r["L3"]) and not bool(r["L4"]) for r in rows),
        "L4_true_L5_false": sum(bool(r["L4"]) and not bool(r["L5"]) for r in rows),
    }
    return {
        "case_count": len(rows),
        "layer_support_counts": layer_counts,
        "layer_support_fraction": {k: v / len(rows) for k, v in layer_counts.items()},
        "per_ordinal_human_anchor_exact_raw_argextreme_count": {str(i): raw_exact[i] for i in range(5)},
        "per_ordinal_nearest_common_scale_ridge_distance": {str(i): dist(nearest[i]) for i in range(5)},
        "common_scale_level_count": dist(common_scale_counts),
        "exact_tuple_match_count": dist(exact_tuple_counts),
        "tuple_birth_match_count": dist(birth_counts),
        "L4_filtered_per_ordinal_cell_hit_count": {str(i): l4_hits[i] for i in range(5)},
        "L5_raw_per_ordinal_cell_hit_count": {str(i): l5_hits[i] for i in range(5)},
        "transitions": transitions,
    }


def frozen_decision(summary: dict) -> dict:
    counts = summary["layer_support_counts"]
    if int(counts["L0"]) != 11:
        category = "v0700_human_anchor_raw_turn_sanity_failed"
    elif int(counts["L1"]) < SALVAGE_CASE_THRESHOLD:
        category = "v0700_ridge_state_space_not_sufficiently_aligned_with_reference_parent"
    elif int(counts["L2"]) < SALVAGE_CASE_THRESHOLD:
        category = "v0700_ridge_infrastructure_salvage_supported_exact_tuple_objectization_breaks_semantic_bridge"
    elif int(counts["L3"]) < SALVAGE_CASE_THRESHOLD:
        category = "v0700_exact_tuple_support_salvaged_tuple_birth_rule_breaks_semantic_bridge"
    elif int(counts["L4"]) < SALVAGE_CASE_THRESHOLD:
        category = "v0700_tuple_birth_support_salvaged_legacy_identity_selection_breaks_semantic_bridge"
    elif int(counts["L5"]) < SALVAGE_CASE_THRESHOLD:
        category = "v0700_filtered_identity_salvaged_raw_projection_breaks_semantic_bridge"
    else:
        category = "v0700_structural_identity_and_projection_salvaged_semantic_completion_or_qualification_bridge_remains"

    retention = {
        "data_clock_source_replay_governance": "retain_without_semantic_change",
        "tcss_extrema_ridge_infrastructure": (
            "retain_as_support_infrastructure_but_not_parent_authority"
            if int(counts["L1"]) >= SALVAGE_CASE_THRESHOLD
            else "requires_reconstruction_or_revalidation"
        ),
        "exact_ridge_five_tuple_objectization": (
            "retain_as_support_infrastructure_but_not_parent_authority"
            if int(counts["L2"]) >= SALVAGE_CASE_THRESHOLD
            else "requires_reconstruction_or_revalidation"
        ),
        "tuple_birth_causal_adjacency_rule": (
            "retain_as_support_infrastructure_but_not_parent_authority"
            if int(counts["L3"]) >= SALVAGE_CASE_THRESHOLD
            else "requires_reconstruction_or_revalidation"
        ),
        "legacy_filtered_parent_identity": (
            "retain_as_support_infrastructure_but_not_parent_authority"
            if int(counts["L4"]) >= SALVAGE_CASE_THRESHOLD
            else "requires_reconstruction_or_revalidation"
        ),
        "raw_projection_v064_v065": (
            "retain_as_support_infrastructure_but_not_parent_authority"
            if int(counts["L5"]) >= SALVAGE_CASE_THRESHOLD
            else "requires_reconstruction_or_revalidation"
        ),
        "same_scale_v054_and_qualification_v0618": "downstream_component_not_yet_retested",
        "direction_D1_v0625": "downstream_component_not_yet_retested",
    }
    return {
        "salvage_threshold_cases": SALVAGE_CASE_THRESHOLD,
        "primary_category": category,
        "component_retention_map": retention,
    }
