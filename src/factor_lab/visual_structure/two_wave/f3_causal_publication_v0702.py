"""Frozen helpers for v0.7.2 F3 causal event/publication precheck."""
from __future__ import annotations

from statistics import median
from typing import Sequence

from .ridge_semantic_objectization_f3dp_v0701 import (
    _count_unique_f3_objects,
    _dominant_edge_masks,
    _edge_is_dominant,
)
from .ridge_semantic_objectization_stream_v0701 import _ridge_level_masks
from .ridge_semantic_objectization_v0701 import (
    causal_survival_levels,
    eligible_nodes_by_level,
)

CERTIFICATE_COVERAGE_THRESHOLD = 0.80


def distribution(values: Sequence[float]) -> dict:
    vals = sorted(float(x) for x in values)
    if not vals:
        return {"count": 0, "median": None, "q1": None, "q3": None, "min": None, "max": None}

    def quantile(p: float) -> float:
        if len(vals) == 1:
            return vals[0]
        pos = (len(vals) - 1) * p
        lo = int(pos)
        hi = min(lo + 1, len(vals) - 1)
        frac = pos - lo
        return vals[lo] * (1.0 - frac) + vals[hi] * frac

    return {
        "count": len(vals),
        "median": float(median(vals)),
        "q1": float(quantile(0.25)),
        "q3": float(quantile(0.75)),
        "min": float(vals[0]),
        "max": float(vals[-1]),
    }


def enumerate_f3_object_masks(ridge_run, chart_start: int, cutoff: int) -> tuple[dict[tuple[str, ...], int], list[list[object]]]:
    """Enumerate unique frozen F3 ridge-ID objects and their valid-level masks."""
    levels, ordered, _, _ = _ridge_level_masks(ridge_run, chart_start, cutoff)
    survival = causal_survival_levels(levels)
    edge_masks = _dominant_edge_masks(levels, survival)
    outgoing: dict[str, list[tuple[str, int]]] = {}
    for (left, right), mask in edge_masks.items():
        outgoing.setdefault(str(left), []).append((str(right), int(mask)))

    order_pos = {rid: i for i, rid in enumerate(ordered)}
    for rid, rows in outgoing.items():
        rows.sort(key=lambda x: order_pos[x[0]])

    objects: dict[tuple[str, ...], int] = {}

    def rec(path: tuple[str, ...], common_mask: int | None) -> None:
        if len(path) == 5:
            if common_mask is None or common_mask == 0:
                raise AssertionError("completed F3 path lacks common valid level")
            objects[path] = objects.get(path, 0) | int(common_mask)
            return
        last = path[-1]
        for nxt, edge_mask in outgoing.get(last, []):
            if nxt in path:
                continue
            new_mask = int(edge_mask) if common_mask is None else int(common_mask) & int(edge_mask)
            if not new_mask:
                continue
            rec(path + (nxt,), new_mask)

    for first in ordered:
        rec((str(first),), None)

    expected = _count_unique_f3_objects(ordered, edge_masks)
    if len(objects) != expected:
        raise AssertionError(f"F3 enumeration drift: {len(objects)} != {expected}")
    return objects, levels


def _level_maps(levels: Sequence[Sequence[object]]) -> list[dict[str, object]]:
    return [{str(row.ridge_id): row for row in rows} for rows in levels]


def _death_map(ridge_run) -> dict[str, list[object]]:
    out: dict[str, list[object]] = {}
    for death in ridge_run.deaths:
        out.setdefault(str(death.ridge_id), []).append(death)
    for rows in out.values():
        rows.sort(key=lambda x: (int(x.coarse_level), int(x.confirmation_index)))
    return out


def _death_by_witness(rows: Sequence[object], witness_level: int, cutoff: int):
    eligible = [
        row for row in rows
        if int(row.coarse_level) <= int(witness_level)
        and int(row.confirmation_index) <= int(cutoff)
    ]
    return eligible[0] if eligible else None


def certificate_realization(
    ridge_run,
    levels: Sequence[Sequence[object]],
    object_key: Sequence[str],
    level: int,
    cutoff: int,
) -> dict | None:
    """Return the frozen monotone death certificate for one final F3 realization."""
    key = tuple(str(x) for x in object_key)
    maps = _level_maps(levels)
    if level < 0 or level >= len(maps) or any(rid not in maps[level] for rid in key):
        return None
    rows = list(levels[level])
    pos = {str(row.ridge_id): i for i, row in enumerate(rows)}
    positions = [pos[rid] for rid in key]
    if positions != sorted(positions):
        return None
    nodes = [maps[level][rid] for rid in key]
    if any(str(a.node.kind) == str(b.node.kind) for a, b in zip(nodes, nodes[1:])):
        return None

    survival = causal_survival_levels(levels)
    if any(not _edge_is_dominant(rows, a, b, survival) for a, b in zip(positions, positions[1:])):
        return None

    deaths = _death_map(ridge_run)
    base_confirmation = max(int(node.node.confirmation_index) for node in nodes)
    gap_times: list[int] = []
    used_death_witness = False

    for left_pos, right_pos, left_rid, right_rid in zip(
        positions, positions[1:], key, key[1:]
    ):
        skipped = rows[left_pos + 1 : right_pos]
        if not skipped:
            gap_times.append(
                max(
                    int(maps[level][left_rid].node.confirmation_index),
                    int(maps[level][right_rid].node.confirmation_index),
                )
            )
            continue

        used_death_witness = True
        witness = None
        for k in range(level + 1, len(maps)):
            if left_rid not in maps[k] or right_rid not in maps[k]:
                continue
            left_k = maps[k][left_rid]
            right_k = maps[k][right_rid]
            if int(left_k.node.confirmation_index) > cutoff or int(right_k.node.confirmation_index) > cutoff:
                continue
            required_deaths = []
            valid = True
            for skipped_row in skipped:
                death = _death_by_witness(deaths.get(str(skipped_row.ridge_id), []), k, cutoff)
                if death is None:
                    valid = False
                    break
                required_deaths.append(death)
            if not valid:
                continue
            certificate_time = max(
                [int(left_k.node.confirmation_index), int(right_k.node.confirmation_index)]
                + [int(d.confirmation_index) for d in required_deaths]
            )
            witness = {
                "witness_level": int(k),
                "certificate_time": int(certificate_time),
                "skipped_count": len(skipped),
            }
            break
        if witness is None:
            return None
        gap_times.append(int(witness["certificate_time"]))

    cert_time = max([base_confirmation] + gap_times)
    if cert_time > int(cutoff):
        return None
    return {
        "level": int(level),
        "certificate_time": int(cert_time),
        "base_realization_confirmation": int(base_confirmation),
        "certificate_delay_bars": int(cert_time - base_confirmation),
        "used_death_witness": bool(used_death_witness),
    }


def object_valid_at_time(ridge_run, chart_start: int, cutoff: int, object_key: Sequence[str]) -> bool:
    key = tuple(str(x) for x in object_key)
    levels = eligible_nodes_by_level(ridge_run, chart_start, cutoff)
    survival = causal_survival_levels(levels)
    for rows in levels:
        pos = {str(row.ridge_id): i for i, row in enumerate(rows)}
        if any(rid not in pos for rid in key):
            continue
        positions = [pos[rid] for rid in key]
        if positions != sorted(positions):
            continue
        nodes = [rows[p] for p in positions]
        if any(str(a.node.kind) == str(b.node.kind) for a, b in zip(nodes, nodes[1:])):
            continue
        if all(_edge_is_dominant(rows, a, b, survival) for a, b in zip(positions, positions[1:])):
            return True
    return False


def certificate_object(
    ridge_run,
    chart_start: int,
    cutoff: int,
    object_key: Sequence[str],
    level_mask: int,
    levels: Sequence[Sequence[object]],
) -> dict | None:
    candidates = []
    for level in range(len(levels)):
        if not (int(level_mask) & (1 << level)):
            continue
        cert = certificate_realization(ridge_run, levels, object_key, level, cutoff)
        if cert is not None:
            candidates.append(cert)
    if not candidates:
        return None
    best = min(candidates, key=lambda x: (int(x["certificate_time"]), int(x["level"])))
    if not object_valid_at_time(ridge_run, chart_start, int(best["certificate_time"]), object_key):
        raise AssertionError("death-certified F3 object is not causally valid at certificate time")
    return best


def frozen_decision(summary: dict) -> dict:
    object_fraction = float(summary["certified_object_fraction"])
    cutoff_fraction = float(summary["certified_presence_fraction_given_f3_positive_cutoff"])
    gate_a = (
        object_fraction >= CERTIFICATE_COVERAGE_THRESHOLD
        and cutoff_fraction >= CERTIFICATE_COVERAGE_THRESHOLD
        and int(summary["certificate_replay_failure_count"]) == 0
    )
    certified_dist = summary["certified_object_count_per_f3_positive_cutoff"]
    gate_b = bool(
        gate_a
        and certified_dist["median"] is not None
        and certified_dist["q3"] is not None
        and float(certified_dist["median"]) <= 1.0
        and float(certified_dist["q3"]) <= 2.0
    )
    if not gate_a:
        category = "v0702_f3_death_certificate_coverage_insufficient_event_semantics_not_frozen"
    elif not gate_b:
        category = "v0702_f3_immutable_event_certificate_supported_append_only_concept_salvaged_object_selection_unresolved"
    else:
        category = "v0702_f3_immutable_event_and_single_parent_publication_precheck_supported"
    return {
        "certificate_coverage_threshold": CERTIFICATE_COVERAGE_THRESHOLD,
        "gate_A_causal_certificate_coverage": gate_a,
        "gate_B_direct_single_parent_publication_identifiability": gate_b,
        "primary_category": category,
    }
