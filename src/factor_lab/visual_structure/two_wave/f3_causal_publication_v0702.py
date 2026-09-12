"""Frozen v0.7.2 causal event/publication semantics for the v0.7.1 F3 object.

The v0.7.1 F3 family remains unchanged.  This module adds a prefix-causal
first-known event and append-only publication representation keyed by the
ordered five ridge IDs.  Human labels are not inputs.
"""
from __future__ import annotations

import hashlib
import json
from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from statistics import median
from typing import Iterable, Sequence

from .ridge_semantic_objectization_f3dp_v0701 import (
    _count_unique_f3_objects,
    _dominant_edge_masks,
)
from .ridge_semantic_objectization_stream_v0701 import _ridge_level_masks
from .ridge_semantic_objectization_v0701 import (
    causal_survival_levels,
    eligible_nodes_by_level,
)

SCHEMA = "two_wave_f3_causal_publication@0.7.2"


def _stable_id(namespace: str, payload: object) -> str:
    raw = json.dumps([namespace, payload], sort_keys=True, separators=(",", ":"), allow_nan=False)
    return f"{namespace}_{hashlib.sha256(raw.encode()).hexdigest()[:20]}"


def _row_sort_key(row) -> tuple[int, int, str]:
    return (
        int(row.node.occurrence_index),
        int(row.node.confirmation_index),
        str(row.node.node_id),
    )


def _alternating_kinds(kinds: Sequence[str]) -> bool:
    return len(kinds) == 5 and all(a != b for a, b in zip(kinds, kinds[1:]))


def f3_publication_id(identity: Sequence[str]) -> str:
    ids = tuple(str(x) for x in identity)
    if len(ids) != 5 or len(set(ids)) != 5:
        raise ValueError("F3 identity requires five distinct ordered ridge IDs")
    return _stable_id("f3_parent_publication_v0702", list(ids))


def enumerate_checkpoint_f3_objects(ridge_run, chart_start: int, cutoff: int) -> dict[tuple[str, ...], int]:
    """Enumerate exact frozen-v0.7.1 F3 identities at one 96-bar checkpoint.

    Values are common-level bit masks for the identity.  The graph/path
    enumeration is definition-equivalent to the exact DP used by v0.7.1.
    """
    levels, ordered, _, _ = _ridge_level_masks(ridge_run, chart_start, cutoff)
    survival = causal_survival_levels(levels)
    edge_masks = _dominant_edge_masks(levels, survival)
    rank = {rid: i for i, rid in enumerate(ordered)}
    outgoing: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for (left, right), mask in edge_masks.items():
        if rank.get(left, -1) >= rank.get(right, -1):
            raise AssertionError("F3 dominant edge violates global ridge order")
        outgoing[left].append((right, int(mask)))
    for left in outgoing:
        outgoing[left].sort(key=lambda x: rank[x[0]])

    objects: dict[tuple[str, ...], int] = {}

    def extend(path: tuple[str, ...], common_mask: int | None) -> None:
        if len(path) == 5:
            if common_mask is None or not common_mask:
                raise AssertionError("five-ridge F3 path requires a common level")
            objects[path] = int(common_mask)
            return
        last = path[-1]
        for nxt, edge_mask in outgoing.get(last, []):
            if nxt in path:
                continue
            new_mask = int(edge_mask) if common_mask is None else int(common_mask) & int(edge_mask)
            if not new_mask:
                continue
            extend(path + (nxt,), new_mask)

    for rid in ordered:
        extend((rid,), None)

    expected = _count_unique_f3_objects(ordered, edge_masks)
    if len(objects) != int(expected):
        raise AssertionError(f"F3 enumeration drift: {len(objects)} != {expected}")
    return objects


@dataclass(frozen=True)
class RidgeLineageIndex:
    levels: tuple[tuple[object, ...], ...]
    by_level_ridge: tuple[dict[str, object], ...]
    representations: dict[str, tuple[tuple[int, object], ...]]
    survival_confirmations: dict[str, tuple[int, ...]]
    survival_prefix_max_level: dict[str, tuple[int, ...]]
    kinds: dict[str, tuple[str, ...]]


def build_lineage_index(ridge_run) -> RidgeLineageIndex:
    levels: list[tuple[object, ...]] = []
    by_level: list[dict[str, object]] = []
    reps: dict[str, list[tuple[int, object]]] = defaultdict(list)
    kinds: dict[str, set[str]] = defaultdict(set)

    for level, raw_rows in enumerate(ridge_run.ridge_nodes_by_level):
        rows = tuple(sorted(raw_rows, key=_row_sort_key))
        seen: dict[str, object] = {}
        for row in rows:
            rid = str(row.ridge_id)
            if rid in seen:
                raise AssertionError(f"duplicate ridge ID {rid} at level {level}")
            seen[rid] = row
            reps[rid].append((int(level), row))
            kinds[rid].add(str(row.node.kind))
        levels.append(rows)
        by_level.append(seen)

    confirmations: dict[str, tuple[int, ...]] = {}
    prefix_levels: dict[str, tuple[int, ...]] = {}
    frozen_reps: dict[str, tuple[tuple[int, object], ...]] = {}
    frozen_kinds: dict[str, tuple[str, ...]] = {}
    for rid, rows in reps.items():
        ordered = sorted(
            rows,
            key=lambda x: (
                int(x[1].node.confirmation_index),
                int(x[0]),
                str(x[1].node.node_id),
            ),
        )
        frozen_reps[rid] = tuple(ordered)
        conf = []
        pref = []
        current = -1
        for level, row in ordered:
            conf.append(int(row.node.confirmation_index))
            current = max(current, int(level))
            pref.append(current)
        confirmations[rid] = tuple(conf)
        prefix_levels[rid] = tuple(pref)
        frozen_kinds[rid] = tuple(sorted(kinds[rid]))

    return RidgeLineageIndex(
        levels=tuple(levels),
        by_level_ridge=tuple(by_level),
        representations=frozen_reps,
        survival_confirmations=confirmations,
        survival_prefix_max_level=prefix_levels,
        kinds=frozen_kinds,
    )


def survival_level_at(index: RidgeLineageIndex, ridge_id: str, cutoff: int) -> int:
    rid = str(ridge_id)
    conf = index.survival_confirmations.get(rid, ())
    if not conf:
        return -1
    pos = bisect_right(conf, int(cutoff)) - 1
    if pos < 0:
        return -1
    return int(index.survival_prefix_max_level[rid][pos])


def _identity_candidate_levels(index: RidgeLineageIndex, identity: Sequence[str]) -> tuple[int, ...]:
    ids = tuple(str(x) for x in identity)
    levels = []
    for level, mapping in enumerate(index.by_level_ridge):
        if not all(rid in mapping for rid in ids):
            continue
        rows = [mapping[rid] for rid in ids]
        occ = [int(x.node.occurrence_index) for x in rows]
        kinds = [str(x.node.kind) for x in rows]
        if all(a < b for a, b in zip(occ, occ[1:])) and _alternating_kinds(kinds):
            levels.append(int(level))
    return tuple(levels)


def _level_realization_at(index: RidgeLineageIndex, identity: Sequence[str], level: int, cutoff: int) -> dict | None:
    ids = tuple(str(x) for x in identity)
    mapping = index.by_level_ridge[int(level)]
    selected = tuple(mapping[rid] for rid in ids)
    if any(int(row.node.confirmation_index) > int(cutoff) for row in selected):
        return None
    occurrences = tuple(int(row.node.occurrence_index) for row in selected)
    kinds = tuple(str(row.node.kind) for row in selected)
    if not all(a < b for a, b in zip(occurrences, occurrences[1:])) or not _alternating_kinds(kinds):
        return None

    full_rows = index.levels[int(level)]
    positions = {str(row.ridge_id): pos for pos, row in enumerate(full_rows)}
    pos = tuple(positions[rid] for rid in ids)
    if not all(a < b for a, b in zip(pos, pos[1:])):
        return None

    selected_survival = tuple(survival_level_at(index, rid, cutoff) for rid in ids)
    for ordinal, (left_pos, right_pos) in enumerate(zip(pos, pos[1:])):
        boundary = min(selected_survival[ordinal], selected_survival[ordinal + 1])
        if boundary < 0:
            return None
        for skipped in full_rows[left_pos + 1 : right_pos]:
            if int(skipped.node.confirmation_index) > int(cutoff):
                continue
            skipped_survival = survival_level_at(index, str(skipped.ridge_id), cutoff)
            if skipped_survival >= boundary:
                return None

    return {
        "level": int(level),
        "ridge_ids": list(ids),
        "occurrence_bars": list(occurrences),
        "node_ids": [str(row.node.node_id) for row in selected],
        "node_confirmation_bars": [int(row.node.confirmation_index) for row in selected],
        "kinds": list(kinds),
        "survival_levels": list(selected_survival),
    }


def valid_realizations_at(index: RidgeLineageIndex, identity: Sequence[str], cutoff: int) -> list[dict]:
    out = []
    for level in _identity_candidate_levels(index, identity):
        realization = _level_realization_at(index, identity, level, cutoff)
        if realization is not None:
            out.append(realization)
    out.sort(
        key=lambda x: (
            int(x["level"]),
            tuple(int(v) for v in x["occurrence_bars"]),
            tuple(str(v) for v in x["node_ids"]),
        )
    )
    return out


def _relevant_ridge_ids(index: RidgeLineageIndex, identity: Sequence[str]) -> set[str]:
    ids = tuple(str(x) for x in identity)
    relevant = set(ids)
    for level in _identity_candidate_levels(index, ids):
        full_rows = index.levels[level]
        positions = {str(row.ridge_id): pos for pos, row in enumerate(full_rows)}
        pos = [positions[rid] for rid in ids]
        for left, right in zip(pos, pos[1:]):
            for row in full_rows[left + 1 : right]:
                relevant.add(str(row.ridge_id))
    return relevant


def relevant_confirmation_cutoffs(index: RidgeLineageIndex, identity: Sequence[str], max_cutoff: int) -> tuple[int, ...]:
    cutoffs = set()
    for rid in _relevant_ridge_ids(index, identity):
        for _, row in index.representations.get(rid, ()):
            confirmation = int(row.node.confirmation_index)
            if confirmation <= int(max_cutoff):
                cutoffs.add(confirmation)
    return tuple(sorted(cutoffs))


def _kind_sequence(index: RidgeLineageIndex, identity: Sequence[str]) -> tuple[str, ...] | None:
    kinds = []
    for rid in identity:
        values = index.kinds.get(str(rid), ())
        if len(values) != 1:
            return None
        kinds.append(values[0])
    return tuple(kinds)


def trace_f3_identity(
    index: RidgeLineageIndex,
    identity: Sequence[str],
    observed_checkpoints: Sequence[int],
) -> dict:
    """Trace one F3 identity to its immutable first-known causal publication."""
    ids = tuple(str(x) for x in identity)
    if len(ids) != 5 or len(set(ids)) != 5:
        raise ValueError("five distinct ordered ridge IDs required")
    checkpoints = tuple(sorted({int(x) for x in observed_checkpoints}))
    if not checkpoints:
        raise ValueError("at least one observed checkpoint required")
    max_cutoff = max(checkpoints)
    event_cutoffs = relevant_confirmation_cutoffs(index, ids, max_cutoff)
    kind_sequence = _kind_sequence(index, ids)
    kind_stable = kind_sequence is not None and _alternating_kinds(kind_sequence)

    first_event = None
    valid_cutoff_count = 0
    valid_representation_count = 0
    distinct_occurrences: set[tuple[int, ...]] = set()
    validity_series: list[tuple[int, bool]] = []

    for cutoff in event_cutoffs:
        realizations = valid_realizations_at(index, ids, cutoff) if kind_stable else []
        valid = bool(realizations)
        validity_series.append((int(cutoff), valid))
        if not valid:
            continue
        valid_cutoff_count += 1
        valid_representation_count += len(realizations)
        for realization in realizations:
            distinct_occurrences.add(tuple(int(x) for x in realization["occurrence_bars"]))
        if first_event is None:
            publishing = realizations[0]
            first_event = {
                "schema": SCHEMA,
                "publication_event_id": f3_publication_id(ids),
                "ridge_ids": list(ids),
                "first_known_confirmation_bar": int(cutoff),
                "publishing_level": int(publishing["level"]),
                "published_filtered_occurrence_bars": list(publishing["occurrence_bars"]),
                "publishing_node_ids": list(publishing["node_ids"]),
                "kind_sequence": list(publishing["kinds"]),
                "publishing_survival_levels": list(publishing["survival_levels"]),
                "valid_realization_count_at_publication": len(realizations),
                "future_outcome_used": False,
                "trade_authority": False,
            }

    checkpoint_validity = {}
    for cutoff in checkpoints:
        checkpoint_validity[str(cutoff)] = bool(valid_realizations_at(index, ids, cutoff)) if kind_stable else False

    published_tuple = (
        tuple(int(x) for x in first_event["published_filtered_occurrence_bars"])
        if first_event is not None
        else None
    )
    rewrite_pressure = bool(
        published_tuple is not None and any(value != published_tuple for value in distinct_occurrences)
    )

    seen_true = False
    seen_false_after_true = False
    validity_gap = False
    for _, valid in validity_series:
        if valid:
            if seen_false_after_true:
                validity_gap = True
            seen_true = True
        elif seen_true:
            seen_false_after_true = True

    first_bar = int(first_event["first_known_confirmation_bar"]) if first_event is not None else None
    gate_a = bool(first_event is not None and all(first_bar <= cutoff for cutoff in checkpoints))
    gate_b = all(checkpoint_validity.values())
    gate_c = bool(kind_stable)
    gate_d = bool(first_event is not None)

    return {
        "ridge_ids": list(ids),
        "publication_event_id": f3_publication_id(ids),
        "kind_sequence_stable_and_alternating": bool(kind_stable),
        "observed_checkpoint_count": len(checkpoints),
        "first_observed_checkpoint": min(checkpoints),
        "last_observed_checkpoint": max(checkpoints),
        "relevant_confirmation_cutoff_count": len(event_cutoffs),
        "valid_evidence_cutoff_count": int(valid_cutoff_count),
        "valid_realization_evidence_count": int(valid_representation_count),
        "distinct_valid_filtered_occurrence_representation_count": len(distinct_occurrences),
        "would_rewrite_filtered_coordinates": rewrite_pressure,
        "validity_gap_after_publication": validity_gap,
        "checkpoint_validity": checkpoint_validity,
        "first_event": first_event,
        "gates": {
            "A_causal_reconstruction": gate_a,
            "B_checkpoint_continuity": gate_b,
            "C_stable_identity": gate_c,
            "D_deterministic_first_publication": gate_d,
        },
    }


def _dist(values: Iterable[int]) -> dict:
    vals = sorted(int(x) for x in values)
    if not vals:
        return {"count": 0, "median": None, "min": None, "max": None}
    return {
        "count": len(vals),
        "median": float(median(vals)),
        "min": int(vals[0]),
        "max": int(vals[-1]),
    }


def summarize_publication_precheck(
    checkpoint_object_counts: Sequence[int],
    traces: Sequence[dict],
) -> dict:
    rows = list(traces)
    ids = [tuple(row["ridge_ids"]) for row in rows]
    publication_ids = [str(row["publication_event_id"]) for row in rows]
    identity_collision = len(ids) != len(set(ids)) or len(publication_ids) != len(set(publication_ids))

    gate_failures = {key: 0 for key in (
        "A_causal_reconstruction",
        "B_checkpoint_continuity",
        "C_stable_identity",
        "D_deterministic_first_publication",
    )}
    for row in rows:
        for key in gate_failures:
            if not bool(row["gates"][key]):
                gate_failures[key] += 1

    publication_fanout: dict[int, int] = defaultdict(int)
    for row in rows:
        event = row.get("first_event")
        if event is not None:
            publication_fanout[int(event["first_known_confirmation_bar"])] += 1

    all_gates_pass = not identity_collision and all(value == 0 for value in gate_failures.values())
    category = (
        "v0702_f3_append_only_event_publication_structurally_transplantable"
        if all_gates_pass
        else "v0702_f3_causal_event_publication_precheck_failed"
    )

    return {
        "checkpoint_count": len(checkpoint_object_counts),
        "checkpoint_f3_object_count": _dist(checkpoint_object_counts),
        "union_unique_f3_identity_count": len(rows),
        "identity_or_publication_id_collision": bool(identity_collision),
        "gate_failure_identity_counts": gate_failures,
        "all_hard_gates_pass": bool(all_gates_pass),
        "first_publication_fanout_per_confirmation_bar": _dist(publication_fanout.values()),
        "identities_with_later_filtered_coordinate_rewrite_pressure": sum(
            bool(row["would_rewrite_filtered_coordinates"]) for row in rows
        ),
        "identities_with_validity_gap_after_publication": sum(
            bool(row["validity_gap_after_publication"]) for row in rows
        ),
        "distinct_valid_filtered_representation_count": _dist(
            row["distinct_valid_filtered_occurrence_representation_count"] for row in rows
        ),
        "valid_realization_count_at_first_publication": _dist(
            row["first_event"]["valid_realization_count_at_publication"]
            for row in rows
            if row.get("first_event") is not None
        ),
        "relevant_confirmation_cutoff_count_per_identity": _dist(
            row["relevant_confirmation_cutoff_count"] for row in rows
        ),
        "primary_category": category,
    }
