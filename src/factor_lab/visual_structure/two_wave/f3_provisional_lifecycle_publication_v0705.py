"""Frozen v0.7.5 provisional lifecycle raw-projection / immutable-publication helpers."""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from statistics import median
from typing import Sequence

import numpy as np

from .f3_prefix_causal_lifecycle_v0704 import (
    build_lifecycle_for_case,
    enumerate_static_f3_at_prefix,
    lifecycle_event_bars,
)
from .models import stable_id
from .ridge_semantic_objectization_v0701 import realization_matches_human
from .semantic_bridge_counteroffensive_v0700 import five_bars_hit_cells

SCHEMA = "two_wave_f3_provisional_lifecycle_publication@0.7.5"
HISTORICAL_RAW_SUPPORT_CASES = 9
HISTORICAL_ORDINAL_CASES = (11, 11, 11, 11, 10)
EXPECTED_OBSERVED_OBJECTS = 1543
EXPECTED_CERTIFIED_OBJECTS = 1478


def _node_sort_key(row) -> tuple[int, int, str]:
    return (
        int(row.node.occurrence_index),
        int(row.node.confirmation_index),
        str(row.node.node_id),
    )


def _realization_key(realization: dict) -> tuple[int, tuple[str, ...]]:
    return (
        int(realization["level"]),
        tuple(str(x.node.node_id) for x in realization["nodes"]),
    )


def _realization_order(realization: dict) -> tuple:
    nodes = tuple(realization["nodes"])
    return (
        int(realization["level"]),
        tuple(int(x.node.occurrence_index) for x in nodes),
        tuple(str(x.node.node_id) for x in nodes),
    )


def prefix_predecessor(ridge_run, realization: dict, evidence_bar: int) -> dict:
    """Return the nearest same-level predecessor known at the publication prefix."""
    level = int(realization["level"])
    nodes = tuple(realization["nodes"])
    if len(nodes) != 5:
        raise ValueError("five F3 nodes required")
    prefix_rows = sorted(
        (
            row
            for row in ridge_run.ridge_nodes_by_level[level]
            if int(row.node.confirmation_index) <= int(evidence_bar)
        ),
        key=_node_sort_key,
    )
    ids = [str(x.ridge_id) for x in nodes]
    positions: dict[str, int] = {}
    for i, row in enumerate(prefix_rows):
        rid = str(row.ridge_id)
        if rid in positions:
            raise AssertionError("ridge ID duplicated within one scale prefix")
        positions[rid] = i
    if any(rid not in positions for rid in ids):
        return {
            "valid": False,
            "reason": "selected_ridge_missing_from_prefix_level",
            "predecessor": None,
            "predecessor_ridge_id": None,
        }
    selected_pos = [positions[rid] for rid in ids]
    if selected_pos != sorted(selected_pos):
        return {
            "valid": False,
            "reason": "selected_ridges_not_ordered_at_prefix_level",
            "predecessor": None,
            "predecessor_ridge_id": None,
        }
    start = int(selected_pos[0])
    if start == 0:
        return {
            "valid": False,
            "reason": "ordinal0_left_censored_no_predecessor",
            "predecessor": None,
            "predecessor_ridge_id": None,
        }
    pred = prefix_rows[start - 1]
    if int(pred.node.confirmation_index) > int(evidence_bar):
        raise AssertionError("prefix predecessor must be confirmed by evidence bar")
    if int(pred.node.occurrence_index) >= int(nodes[0].node.occurrence_index):
        return {
            "valid": False,
            "reason": "predecessor_not_earlier_than_ordinal0",
            "predecessor": pred,
            "predecessor_ridge_id": str(pred.ridge_id),
        }
    if str(pred.node.kind) == str(nodes[0].node.kind):
        return {
            "valid": False,
            "reason": "predecessor_kind_not_opposite",
            "predecessor": pred,
            "predecessor_ridge_id": str(pred.ridge_id),
        }
    return {
        "valid": True,
        "reason": None,
        "predecessor": pred,
        "predecessor_ridge_id": str(pred.ridge_id),
    }


def _last_argextreme(values: np.ndarray, kind: str) -> tuple[int, float]:
    if values.ndim != 1 or not len(values):
        raise ValueError("finite nonempty one-dimensional window required")
    target = float(np.max(values)) if kind == "high" else float(np.min(values))
    pos = np.flatnonzero(values == target)
    return int(pos[-1]), target


def _publication_id(object_id: str, phase: str, raw_occurrence_bars: Sequence[int]) -> str:
    return stable_id(
        "f3_lifecycle_publication_v0705",
        {
            "schema": SCHEMA,
            "object_id": str(object_id),
            "phase": str(phase),
            "raw_occurrence_bars": [int(x) for x in raw_occurrence_bars],
        },
    )


def _pivot_id(object_id: str, ordinal: int, kind: str, occurrence: int, price: float) -> str:
    return stable_id(
        "f3_lifecycle_raw_pivot_v0705",
        {
            "schema": SCHEMA,
            "object_id": str(object_id),
            "ordinal": int(ordinal),
            "kind": str(kind),
            "occurrence_bar": int(occurrence),
            "price": float(price),
        },
    )


def project_prefix_realization(
    ridge_run,
    realization: dict,
    evidence_bar: int,
    bars: Sequence[dict],
    closes: np.ndarray,
    predecessor: dict | None = None,
    object_id: str | None = None,
) -> dict:
    """Apply the frozen sequential raw projection using only prefix evidence."""
    evidence_bar = int(evidence_bar)
    nodes = tuple(realization["nodes"])
    if len(nodes) != 5:
        raise ValueError("five F3 nodes required")
    if any(int(x.node.confirmation_index) > evidence_bar for x in nodes):
        return {"valid": False, "reason": "selected_node_after_evidence_bar"}
    pred_info = predecessor if predecessor is not None else prefix_predecessor(ridge_run, realization, evidence_bar)
    if not bool(pred_info.get("valid")):
        return {
            "valid": False,
            "reason": str(pred_info.get("reason")),
            "predecessor_ridge_id": pred_info.get("predecessor_ridge_id"),
        }
    pred = pred_info["predecessor"]
    if int(pred.node.confirmation_index) > evidence_bar:
        return {"valid": False, "reason": "predecessor_after_evidence_bar"}

    filtered = [int(x.node.occurrence_index) for x in nodes]
    if any(b <= a for a, b in zip(filtered, filtered[1:])):
        return {"valid": False, "reason": "selected_filtered_order_conflict"}
    kinds = [str(x.node.kind) for x in nodes]
    if any(kind not in {"low", "high"} for kind in kinds):
        raise ValueError("selected node kind must be low/high")
    member_confirmation = int(nodes[-1].node.confirmation_index)
    if member_confirmation > evidence_bar:
        return {"valid": False, "reason": "member_confirmation_after_evidence_bar"}
    if member_confirmation >= len(bars) or evidence_bar >= len(bars):
        return {"valid": False, "reason": "confirmation_outside_bars"}

    lo = int(pred.node.occurrence_index) + 1
    uppers = [filtered[1] - 1, filtered[2] - 1, filtered[3] - 1, filtered[4] - 1, member_confirmation]
    occ: list[int] = []
    prices: list[float] = []
    windows = []
    for ordinal, (kind, upper) in enumerate(zip(kinds, uppers)):
        hi = min(int(upper), member_confirmation, evidence_bar)
        if lo > hi:
            return {
                "valid": False,
                "reason": "raw_projection_empty_phase_window",
                "phase_ordinal": int(ordinal),
                "predecessor_ridge_id": str(pred.ridge_id),
            }
        rel, price = _last_argextreme(closes[lo : hi + 1], kind)
        idx = lo + rel
        if idx > evidence_bar:
            raise AssertionError("raw projection selected future bar")
        occ.append(int(idx))
        prices.append(float(price))
        windows.append(
            {
                "ordinal": int(ordinal),
                "lower_bar": int(lo),
                "upper_bar": int(hi),
                "selected_raw_bar": int(idx),
            }
        )
        lo = int(idx) + 1

    if any(a >= b for a, b in zip(occ, occ[1:])):
        return {"valid": False, "reason": "raw_projection_order_conflict", "predecessor_ridge_id": str(pred.ridge_id)}
    for kind, a, b in zip(kinds, prices, prices[1:]):
        if kind == "low" and not b > a:
            return {"valid": False, "reason": "raw_projection_not_actual_turn", "predecessor_ridge_id": str(pred.ridge_id)}
        if kind == "high" and not b < a:
            return {"valid": False, "reason": "raw_projection_not_actual_turn", "predecessor_ridge_id": str(pred.ridge_id)}

    phase = str(kinds[0])
    raw_identity = (phase, tuple(int(x) for x in occ))
    oid = str(object_id) if object_id is not None else stable_id("f3_lifecycle_object_v0705_test", [str(x.ridge_id) for x in nodes])
    confirmation_time = str(bars[evidence_bar]["timestamp"])
    known = bars[evidence_bar].get("available_at", confirmation_time)
    points = []
    for ordinal, (kind, occurrence, price) in enumerate(zip(kinds, occ, prices)):
        points.append(
            {
                "kind": str(kind),
                "occurrence_bar": int(occurrence),
                "occurrence_time": str(bars[occurrence]["timestamp"]),
                "price": float(price),
                "log_price": math.log(float(price)),
                "left_censored": False,
                "confirmation_bar": evidence_bar,
                "confirmation_time": confirmation_time,
                "effective_information_time": known,
                "bar_end_assumed": False,
                "pivot_id": _pivot_id(oid, ordinal, kind, occurrence, price),
            }
        )

    return {
        "valid": True,
        "reason": None,
        "phase": phase,
        "raw_identity": raw_identity,
        "raw_occurrence_bars": [int(x) for x in occ],
        "raw_prices": [float(x) for x in prices],
        "points": points,
        "event_confirmation_bar": evidence_bar,
        "member_confirmation_bar": member_confirmation,
        "predecessor_ridge_id": str(pred.ridge_id),
        "predecessor_occurrence_bar": int(pred.node.occurrence_index),
        "windows": windows,
    }


def cache_prefix_static_stores(ridge_run, chart_start: int, cutoff: int) -> list[tuple[int, dict]]:
    return [
        (int(t), enumerate_static_f3_at_prefix(ridge_run, chart_start, int(t)))
        for t in lifecycle_event_bars(ridge_run, chart_start, cutoff)
    ]


def _candidate_order(evidence_bar: int, realization: dict, predecessor_ridge_id: str | None) -> tuple:
    nodes = tuple(realization["nodes"])
    return (
        int(evidence_bar),
        int(realization["level"]),
        tuple(int(x.node.occurrence_index) for x in nodes),
        tuple(str(x.node.node_id) for x in nodes),
        "" if predecessor_ridge_id is None else str(predecessor_ridge_id),
    )


def _status_at(obj: dict, evidence_bar: int) -> str:
    cert = obj.get("certification_bar")
    if cert is not None and int(cert) <= int(evidence_bar):
        return "certified"
    return "observed_live_unresolved"


def _publication_signature(publications: dict[tuple[str, ...], dict]) -> str:
    rows = []
    for key in sorted(publications):
        pub = publications[key].get("publication")
        if pub is None:
            continue
        rows.append(
            {
                "object_id": str(pub["object_id"]),
                "publication_id": str(pub["publication_id"]),
                "object_key": list(key),
                "publishing_evidence_bar": int(pub["publishing_evidence_bar"]),
                "predecessor_ridge_id": str(pub["predecessor_ridge_id"]),
                "phase": str(pub["phase"]),
                "raw_occurrence_bars": [int(x) for x in pub["raw_occurrence_bars"]],
                "pivot_ids": [str(x["pivot_id"]) for x in pub["points"]],
            }
        )
    encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def replay_publications_from_cache(
    ridge_run,
    lifecycle: dict,
    prefix_frames: Sequence[tuple[int, dict]],
    bars: Sequence[dict],
) -> dict:
    """Replay first-valid immutable publication over frozen lifecycle prefixes."""
    closes = np.asarray([float(x["close"]) for x in bars], dtype=float)
    if closes.ndim != 1 or not np.isfinite(closes).all():
        raise ValueError("finite close series required")

    states: dict[tuple[str, ...], dict] = {}
    violations: Counter[str] = Counter()
    invalid_reasons: Counter[str] = Counter()
    prefix_predecessor_change_evidence_count = 0

    for key, obj in lifecycle["objects"].items():
        states[key] = {
            "object_id": str(obj["object_id"]),
            "first_observation_bar": int(obj["first_observation_bar"]),
            "publication": None,
            "prior_invalid_projection_count": 0,
            "invalid_after_publication_count": 0,
            "later_valid_same_identity_count": 0,
            "later_valid_would_rewrite_suppressed_count": 0,
            "evidence_count": 0,
            "last_predecessor_by_realization": {},
            "seen_realizations": set(),
        }

    for evidence_bar, current in prefix_frames:
        evidence_bar = int(evidence_bar)
        current_keys = set(current)
        for key in sorted(current_keys):
            obj = lifecycle["objects"].get(key)
            state = states.get(key)
            if obj is None or state is None:
                violations["live_static_object_missing_lifecycle_identity"] += 1
                continue
            if evidence_bar < int(obj["first_observation_bar"]):
                violations["projection_evidence_before_observation"] += 1
                continue

            candidates = []
            for realization in sorted(current[key], key=_realization_order):
                rkey = _realization_key(realization)
                pred = prefix_predecessor(ridge_run, realization, evidence_bar)
                pred_id = pred.get("predecessor_ridge_id")
                first_seen = rkey not in state["seen_realizations"]
                previous = state["last_predecessor_by_realization"].get(rkey, object())
                pred_changed = (not first_seen) and previous != pred_id
                if not first_seen and not pred_changed:
                    continue
                if pred_changed:
                    prefix_predecessor_change_evidence_count += 1
                state["seen_realizations"].add(rkey)
                state["last_predecessor_by_realization"][rkey] = pred_id
                candidates.append((_candidate_order(evidence_bar, realization, pred_id), realization, pred))

            for _, realization, pred in sorted(candidates, key=lambda x: x[0]):
                state["evidence_count"] += 1
                projection = project_prefix_realization(
                    ridge_run,
                    realization,
                    evidence_bar,
                    bars,
                    closes,
                    predecessor=pred,
                    object_id=state["object_id"],
                )
                pub = state["publication"]
                if pub is None:
                    if not bool(projection.get("valid")):
                        state["prior_invalid_projection_count"] += 1
                        invalid_reasons[str(projection.get("reason"))] += 1
                        continue
                    if evidence_bar < int(obj["first_observation_bar"]):
                        violations["publication_before_observation"] += 1
                    raw_identity = projection["raw_identity"]
                    publication_id = _publication_id(
                        state["object_id"],
                        raw_identity[0],
                        raw_identity[1],
                    )
                    state["publication"] = {
                        "object_id": state["object_id"],
                        "object_key": tuple(key),
                        "publication_id": publication_id,
                        "first_observation_bar": int(obj["first_observation_bar"]),
                        "publishing_evidence_bar": evidence_bar,
                        "publishing_level": int(realization["level"]),
                        "predecessor_ridge_id": str(projection["predecessor_ridge_id"]),
                        "phase": str(projection["phase"]),
                        "raw_identity": raw_identity,
                        "raw_occurrence_bars": [int(x) for x in projection["raw_occurrence_bars"]],
                        "points": projection["points"],
                        "status_at_publication": _status_at(obj, evidence_bar),
                    }
                else:
                    if not bool(projection.get("valid")):
                        state["invalid_after_publication_count"] += 1
                        continue
                    if tuple(projection["raw_identity"]) == tuple(pub["raw_identity"]):
                        state["later_valid_same_identity_count"] += 1
                    else:
                        state["later_valid_would_rewrite_suppressed_count"] += 1

    # Immutable-publication / status-append invariants.
    publication_ids: set[str] = set()
    unresolved_then_certified = 0
    published_still_unresolved = 0
    already_certified_publications = 0
    certified_total = 0
    certified_published = 0
    final_unresolved_total = 0
    final_unresolved_published = 0

    for key, obj in lifecycle["objects"].items():
        state = states[key]
        pub = state["publication"]
        final_certified = bool(obj["certified"])
        if final_certified:
            certified_total += 1
        else:
            final_unresolved_total += 1
        if pub is None:
            continue
        if str(pub["object_id"]) != str(obj["object_id"]):
            violations["publication_lifecycle_object_id_mismatch"] += 1
        if int(pub["publishing_evidence_bar"]) < int(obj["first_observation_bar"]):
            violations["publication_before_observation"] += 1
        if pub["publication_id"] in publication_ids:
            violations["duplicate_publication_id"] += 1
        publication_ids.add(str(pub["publication_id"]))
        expected_pub_id = _publication_id(
            str(pub["object_id"]),
            str(pub["phase"]),
            pub["raw_occurrence_bars"],
        )
        if str(expected_pub_id) != str(pub["publication_id"]):
            violations["publication_id_not_stable"] += 1
        for ordinal, point in enumerate(pub["points"]):
            expected_pivot = _pivot_id(
                str(pub["object_id"]),
                ordinal,
                str(point["kind"]),
                int(point["occurrence_bar"]),
                float(point["price"]),
            )
            if str(expected_pivot) != str(point["pivot_id"]):
                violations["pivot_id_not_stable"] += 1
            if int(point["occurrence_bar"]) > int(pub["publishing_evidence_bar"]):
                violations["publication_uses_future_raw_bar"] += 1
        if final_certified:
            certified_published += 1
        else:
            final_unresolved_published += 1
        status = str(pub["status_at_publication"])
        cert_bar = obj.get("certification_bar")
        if status == "observed_live_unresolved":
            if cert_bar is not None and int(cert_bar) > int(pub["publishing_evidence_bar"]):
                unresolved_then_certified += 1
                # Status append must not change the immutable identity.
                if str(expected_pub_id) != str(pub["publication_id"]):
                    violations["certification_status_append_rewrites_publication"] += 1
            elif cert_bar is None:
                published_still_unresolved += 1
        elif status == "certified":
            already_certified_publications += 1
            if cert_bar is None or int(cert_bar) > int(pub["publishing_evidence_bar"]):
                violations["publication_status_uses_future_certification"] += 1
        else:
            violations["unknown_publication_lifecycle_status"] += 1

    publications = states
    signature = _publication_signature(publications)
    evidence_counts = [int(x["evidence_count"]) for x in states.values()]
    delays = [
        int(x["publication"]["publishing_evidence_bar"]) - int(x["first_observation_bar"])
        for x in states.values()
        if x["publication"] is not None
    ]
    return {
        "states": states,
        "publication_count": sum(x["publication"] is not None for x in states.values()),
        "certified_object_count": int(certified_total),
        "certified_published_count": int(certified_published),
        "final_unresolved_object_count": int(final_unresolved_total),
        "final_unresolved_published_count": int(final_unresolved_published),
        "unresolved_then_certified_publication_count": int(unresolved_then_certified),
        "published_still_unresolved_count": int(published_still_unresolved),
        "already_certified_publication_count": int(already_certified_publications),
        "prior_invalid_projection_count": sum(int(x["prior_invalid_projection_count"]) for x in states.values()),
        "prior_invalid_projection_reason_counts": dict(sorted(invalid_reasons.items())),
        "invalid_after_publication_count": sum(int(x["invalid_after_publication_count"]) for x in states.values()),
        "later_valid_same_identity_count": sum(int(x["later_valid_same_identity_count"]) for x in states.values()),
        "later_valid_would_rewrite_suppressed_count": sum(
            int(x["later_valid_would_rewrite_suppressed_count"]) for x in states.values()
        ),
        "prefix_predecessor_change_evidence_count": int(prefix_predecessor_change_evidence_count),
        "publication_delay_bars_from_observation": distribution(delays),
        "projection_evidence_count_per_object": distribution(evidence_counts),
        "aggregate_publication_identity_sha256": signature,
        "hard_invariant_violation_counts": dict(sorted(violations.items())),
        "hard_invariant_violation_count": int(sum(violations.values())),
    }


def summarize_case_semantics(publication: dict, lifecycle: dict, cells, kinds, human_bars) -> dict:
    """Score frozen human cells only after label-free publication construction."""
    overall_support = False
    unresolved_at_pub_support = False
    certified_at_pub_support = False
    final_certified_support = False
    final_unresolved_support = False
    ordinal_hits = [False] * 5

    final_live_keys = set(lifecycle["final_live_keys"])
    compatible_live_keys: set[tuple[str, ...]] = set()
    for key, realizations in lifecycle["final_static_store"].items():
        if any(realization_matches_human(r, cells, kinds, human_bars)[0] for r in realizations):
            compatible_live_keys.add(key)

    gap_same_object_provisional_raw_support = False
    for key, state in publication["states"].items():
        pub = state["publication"]
        if pub is None or key not in final_live_keys:
            continue
        hit, hits = five_bars_hit_cells(pub["raw_occurrence_bars"], pub["phase"], cells, kinds)
        ordinal_hits = [a or b for a, b in zip(ordinal_hits, hits)]
        overall_support = overall_support or bool(hit)
        if str(pub["status_at_publication"]) == "observed_live_unresolved":
            unresolved_at_pub_support = unresolved_at_pub_support or bool(hit)
        else:
            certified_at_pub_support = certified_at_pub_support or bool(hit)
        if bool(lifecycle["objects"][key]["certified"]):
            final_certified_support = final_certified_support or bool(hit)
        else:
            final_unresolved_support = final_unresolved_support or bool(hit)
            if key in compatible_live_keys and bool(hit):
                gap_same_object_provisional_raw_support = True

    static_support = bool(compatible_live_keys)
    certified_semantic_support = any(
        key in compatible_live_keys and bool(lifecycle["objects"][key]["certified"])
        for key in compatible_live_keys
    )
    gap_case = static_support and not certified_semantic_support
    return {
        "published_raw_support": bool(overall_support),
        "published_raw_ordinal_hits": ordinal_hits,
        "published_while_unresolved_support": bool(unresolved_at_pub_support),
        "published_when_certified_support": bool(certified_at_pub_support),
        "final_certified_published_raw_support": bool(final_certified_support),
        "final_unresolved_published_raw_support": bool(final_unresolved_support),
        "static_support": static_support,
        "certified_semantic_support": bool(certified_semantic_support),
        "permanent_certificate_gap_case": bool(gap_case),
        "gap_same_object_provisional_raw_support": bool(gap_same_object_provisional_raw_support),
    }


def distribution(values: Sequence[int | float]) -> dict:
    vals = sorted(float(x) for x in values)
    if not vals:
        return {"count": 0, "median": None, "min": None, "max": None}
    return {
        "count": len(vals),
        "median": float(median(vals)),
        "min": vals[0],
        "max": vals[-1],
    }


def summarize_cases(records: Sequence[dict]) -> dict:
    rows = list(records)
    if len(rows) != 11:
        raise ValueError("v0705 frozen anchored universe requires exactly 11 cases")

    observed_total = sum(len(r["lifecycle"]["objects"]) for r in rows)
    certified_total = sum(sum(bool(x["certified"]) for x in r["lifecycle"]["objects"].values()) for r in rows)
    lifecycle_violations: Counter[str] = Counter()
    publication_violations: Counter[str] = Counter()
    for r in rows:
        lifecycle_violations.update({str(k): int(v) for k, v in r["lifecycle"]["violations"].items()})
        publication_violations.update(
            {str(k): int(v) for k, v in r["publication"]["hard_invariant_violation_counts"].items()}
        )

    semantics = [r["semantics"] for r in rows]
    ordinal = [sum(bool(x["published_raw_ordinal_hits"][i]) for x in semantics) for i in range(5)]
    gap_rows = [x for x in semantics if bool(x["permanent_certificate_gap_case"])]

    publication_count = sum(int(r["publication"]["publication_count"]) for r in rows)
    certified_published = sum(int(r["publication"]["certified_published_count"]) for r in rows)
    unresolved_total = sum(int(r["publication"]["final_unresolved_object_count"]) for r in rows)
    unresolved_published = sum(int(r["publication"]["final_unresolved_published_count"]) for r in rows)

    return {
        "case_count": 11,
        "upstream_replication": {
            "observed_lifecycle_object_count": int(observed_total),
            "certified_lifecycle_object_count": int(certified_total),
            "lifecycle_hard_invariant_violation_count": int(sum(lifecycle_violations.values())),
            "lifecycle_hard_invariant_violation_counts": dict(sorted(lifecycle_violations.items())),
            "objects_with_dormant_transition": sum(
                any(str(e["kind"]) == "dormant" for e in obj["events"])
                for r in rows for obj in r["lifecycle"]["objects"].values()
            ),
            "objects_with_reobserved_transition": sum(
                any(str(e["kind"]) == "reobserved" for e in obj["events"])
                for r in rows for obj in r["lifecycle"]["objects"].values()
            ),
            "static_f3_support_cases": sum(bool(x["static_support"]) for x in semantics),
            "c1_certified_support_cases": sum(bool(x["certified_semantic_support"]) for x in semantics),
        },
        "publication": {
            "published_lifecycle_object_count": int(publication_count),
            "certified_object_publication_count": int(certified_published),
            "certified_object_publication_expected": EXPECTED_CERTIFIED_OBJECTS,
            "final_unresolved_object_count": int(unresolved_total),
            "final_unresolved_published_count": int(unresolved_published),
            "final_unresolved_unpublished_count": int(unresolved_total - unresolved_published),
            "prior_invalid_projection_count": sum(int(r["publication"]["prior_invalid_projection_count"]) for r in rows),
            "prior_invalid_projection_reason_counts": dict(sorted(sum_counters(
                r["publication"]["prior_invalid_projection_reason_counts"] for r in rows
            ).items())),
            "invalid_after_publication_count": sum(int(r["publication"]["invalid_after_publication_count"]) for r in rows),
            "later_valid_same_identity_count": sum(int(r["publication"]["later_valid_same_identity_count"]) for r in rows),
            "later_valid_would_rewrite_suppressed_count": sum(
                int(r["publication"]["later_valid_would_rewrite_suppressed_count"]) for r in rows
            ),
            "prefix_predecessor_change_evidence_count": sum(
                int(r["publication"]["prefix_predecessor_change_evidence_count"]) for r in rows
            ),
            "unresolved_then_certified_publication_count": sum(
                int(r["publication"]["unresolved_then_certified_publication_count"]) for r in rows
            ),
            "published_still_unresolved_count": sum(
                int(r["publication"]["published_still_unresolved_count"]) for r in rows
            ),
            "already_certified_publication_count": sum(
                int(r["publication"]["already_certified_publication_count"]) for r in rows
            ),
            "publication_delay_bars_from_observation": distribution([
                int(state["publication"]["publishing_evidence_bar"]) - int(state["first_observation_bar"])
                for r in rows for state in r["publication"]["states"].values()
                if state["publication"] is not None
            ]),
            "projection_evidence_count_per_object": distribution([
                int(state["evidence_count"])
                for r in rows for state in r["publication"]["states"].values()
            ]),
            "aggregate_case_publication_identity_sha256": aggregate_case_hashes(
                [str(r["publication"]["aggregate_publication_identity_sha256"]) for r in rows]
            ),
            "hard_invariant_violation_count": int(sum(publication_violations.values())),
            "hard_invariant_violation_counts": dict(sorted(publication_violations.items())),
        },
        "semantic_continuity": {
            "published_raw_semantic_support_cases": sum(bool(x["published_raw_support"]) for x in semantics),
            "per_ordinal_published_raw_cell_hit_cases": {str(i): int(ordinal[i]) for i in range(5)},
            "published_while_unresolved_support_cases": sum(
                bool(x["published_while_unresolved_support"]) for x in semantics
            ),
            "published_when_certified_support_cases": sum(
                bool(x["published_when_certified_support"]) for x in semantics
            ),
            "final_certified_published_raw_support_cases": sum(
                bool(x["final_certified_published_raw_support"]) for x in semantics
            ),
            "final_unresolved_published_raw_support_cases": sum(
                bool(x["final_unresolved_published_raw_support"]) for x in semantics
            ),
            "permanent_certificate_gap_case_count": len(gap_rows),
            "gap_same_object_provisional_raw_support_cases": sum(
                bool(x["gap_same_object_provisional_raw_support"]) for x in gap_rows
            ),
        },
    }


def sum_counters(rows) -> Counter[str]:
    out: Counter[str] = Counter()
    for row in rows:
        out.update({str(k): int(v) for k, v in row.items()})
    return out


def aggregate_case_hashes(case_hashes: Sequence[str]) -> str:
    encoded = json.dumps([str(x) for x in case_hashes], separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def frozen_decision(summary: dict, deterministic_replay_ok: bool) -> dict:
    upstream = summary["upstream_replication"]
    pub = summary["publication"]
    sem = summary["semantic_continuity"]

    if int(upstream["observed_lifecycle_object_count"]) != EXPECTED_OBSERVED_OBJECTS:
        raise AssertionError("v0704 observed lifecycle object count drift")
    if int(upstream["certified_lifecycle_object_count"]) != EXPECTED_CERTIFIED_OBJECTS:
        raise AssertionError("v0704 certified lifecycle object count drift")
    if int(upstream["static_f3_support_cases"]) != 8:
        raise AssertionError("v0704 static F3 support drift")
    if int(upstream["c1_certified_support_cases"]) != 7:
        raise AssertionError("v0704 C1 support drift")
    if int(upstream["objects_with_dormant_transition"]) != 0 or int(upstream["objects_with_reobserved_transition"]) != 0:
        raise AssertionError("v0704 lifecycle transition census drift")

    invariant_count = (
        int(upstream["lifecycle_hard_invariant_violation_count"])
        + int(pub["hard_invariant_violation_count"])
        + (0 if bool(deterministic_replay_ok) else 1)
    )
    coverage_ok = int(pub["certified_object_publication_count"]) == EXPECTED_CERTIFIED_OBJECTS
    raw_support = int(sem["published_raw_semantic_support_cases"])
    ordinal = tuple(int(sem["per_ordinal_published_raw_cell_hit_cases"][str(i)]) for i in range(5))
    semantic_ok = raw_support >= HISTORICAL_RAW_SUPPORT_CASES and all(
        got >= need for got, need in zip(ordinal, HISTORICAL_ORDINAL_CASES)
    )
    if int(sem["permanent_certificate_gap_case_count"]) != 1:
        raise AssertionError("v0704 permanent-certificate semantic gap count drift")
    gap_ok = int(sem["gap_same_object_provisional_raw_support_cases"]) == 1

    if invariant_count:
        category = "v0705_provisional_publication_append_only_or_causal_invariant_failed"
    elif not coverage_ok:
        category = "v0705_certified_publication_coverage_regressed"
    elif not semantic_ok:
        category = "v0705_provisional_lifecycle_raw_projection_semantic_support_insufficient"
    elif not gap_ok:
        category = "v0705_live_unresolved_gap_not_transplantable_to_raw_publication"
    else:
        category = "v0705_f3_provisional_lifecycle_publication_transplant_supported"

    return {
        "upstream_lifecycle_replication_ok": True,
        "hard_invariant_violation_zero": invariant_count == 0,
        "deterministic_replay_ok": bool(deterministic_replay_ok),
        "certified_publication_coverage_ok": coverage_ok,
        "historical_raw_semantic_support_no_degradation": semantic_ok,
        "live_unresolved_gap_same_object_raw_support": gap_ok,
        "primary_category": category,
    }
