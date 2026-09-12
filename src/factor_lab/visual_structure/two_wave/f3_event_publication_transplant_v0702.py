"""Frozen v0.7.2 F3 causal event/publication and transplant-precheck helpers."""
from __future__ import annotations

import math
from collections import defaultdict
from statistics import median
from typing import Sequence

import numpy as np

from .models import stable_id
from .ridge_semantic_objectization_v0701 import (
    causal_survival_levels,
    eligible_nodes_by_level,
    object_key,
    realization_matches_human,
)
from .ridge_semantic_objectization_stream_v0701 import (
    _dominant_incremental,
    alternating_quintet_indices,
)
from .semantic_bridge_counteroffensive_v0700 import five_bars_hit_cells

SALVAGE_CASE_THRESHOLD = 8


def _node_sort_key(row) -> tuple[int, int, str]:
    return (
        int(row.node.occurrence_index),
        int(row.node.confirmation_index),
        str(row.node.node_id),
    )


def _last_argextreme(values: np.ndarray, kind: str) -> tuple[int, float]:
    if values.ndim != 1 or not len(values):
        raise ValueError("finite nonempty one-dimensional window required")
    if kind == "high":
        target = float(np.max(values))
    elif kind == "low":
        target = float(np.min(values))
    else:
        raise ValueError("kind must be low/high")
    pos = np.flatnonzero(values == target)
    return int(pos[-1]), target


def _death_index(ridge_run) -> dict[str, object]:
    out: dict[str, object] = {}
    for death in ridge_run.deaths:
        rid = str(death.ridge_id)
        if rid in out:
            raise AssertionError("one ridge ID may have at most one causal death")
        out[rid] = death
    return out


def certify_f3_realization(
    ridge_run,
    eligible_levels: Sequence[Sequence[object]],
    level: int,
    level_rows: Sequence[object],
    idxs: Sequence[int],
    cutoff: int,
) -> dict:
    """Certify an F3 realization using explicit skipped-ridge deaths only."""
    idxs = tuple(int(x) for x in idxs)
    if len(idxs) != 5 or any(b <= a for a, b in zip(idxs, idxs[1:])):
        raise ValueError("five increasing realization indices required")
    nodes = tuple(level_rows[i] for i in idxs)
    event_confirmation = max(int(x.node.confirmation_index) for x in nodes)
    if event_confirmation > int(cutoff):
        return {"certified": False, "reason": "selected_node_after_cutoff"}

    deaths = _death_index(ridge_run)
    level_maps = [
        {str(row.ridge_id): row for row in rows}
        for rows in eligible_levels
    ]
    certificates = []
    for left_pos, right_pos in zip(idxs, idxs[1:]):
        left = level_rows[left_pos]
        right = level_rows[right_pos]
        for skipped in level_rows[left_pos + 1 : right_pos]:
            rid = str(skipped.ridge_id)
            death = deaths.get(rid)
            if death is None:
                return {"certified": False, "reason": "skipped_ridge_has_no_explicit_death", "ridge_id": rid}
            if int(death.fine_level) < int(level):
                return {"certified": False, "reason": "skipped_ridge_death_precedes_realization_level", "ridge_id": rid}
            coarse = int(death.coarse_level)
            if coarse >= len(level_maps):
                return {"certified": False, "reason": "skipped_ridge_death_outside_scale_lattice", "ridge_id": rid}
            if int(death.confirmation_index) > int(cutoff):
                return {"certified": False, "reason": "skipped_ridge_death_not_yet_confirmed", "ridge_id": rid}
            left_survivor = level_maps[coarse].get(str(left.ridge_id))
            right_survivor = level_maps[coarse].get(str(right.ridge_id))
            if left_survivor is None or right_survivor is None:
                return {"certified": False, "reason": "selected_boundary_not_confirmed_beyond_skipped_death", "ridge_id": rid}
            proof_confirmation = max(
                int(death.confirmation_index),
                int(left_survivor.node.confirmation_index),
                int(right_survivor.node.confirmation_index),
            )
            if proof_confirmation > int(cutoff):
                return {"certified": False, "reason": "dominance_proof_after_cutoff", "ridge_id": rid}
            event_confirmation = max(event_confirmation, proof_confirmation)
            certificates.append(
                {
                    "skipped_ridge_id": rid,
                    "death_fine_level": int(death.fine_level),
                    "death_coarse_level": coarse,
                    "death_confirmation_bar": int(death.confirmation_index),
                    "proof_confirmation_bar": proof_confirmation,
                }
            )

    return {
        "certified": True,
        "reason": None,
        "event_confirmation_bar": int(event_confirmation),
        "level": int(level),
        "nodes": nodes,
        "object_key": object_key(nodes),
        "selected_occurrence_bars": [int(x.node.occurrence_index) for x in nodes],
        "certificate_count": len(certificates),
        "certificates": certificates,
    }


def enumerate_f3_objects_with_certification(ridge_run, chart_start: int, cutoff: int) -> dict:
    """Return frozen static F3 objects and the causally certified subset."""
    levels = eligible_nodes_by_level(ridge_run, chart_start, cutoff)
    survival = causal_survival_levels(levels)
    static: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    certified: dict[tuple[str, ...], list[dict]] = defaultdict(list)

    for level, rows in enumerate(levels):
        for idxs in alternating_quintet_indices(rows):
            if not _dominant_incremental(rows, idxs, survival):
                continue
            nodes = tuple(rows[i] for i in idxs)
            key = object_key(nodes)
            static[key].append({"level": int(level), "nodes": nodes})
            cert = certify_f3_realization(ridge_run, levels, level, rows, idxs, cutoff)
            if bool(cert.get("certified")):
                certified[key].append(cert)

    return {
        "static": dict(static),
        "certified": dict(certified),
    }


def event_order_key(realization: dict) -> tuple:
    nodes = tuple(realization["nodes"])
    return (
        int(realization["event_confirmation_bar"]),
        int(realization["level"]),
        tuple(int(x.node.occurrence_index) for x in nodes),
        tuple(str(x.node.node_id) for x in nodes),
    )


def project_f3_realization_with_predecessor(ridge_run, realization: dict, bars: Sequence[dict]) -> dict:
    """Generalize only the v0.6.4 predecessor adapter to a nonconsecutive F3 realization."""
    level = int(realization["level"])
    nodes = tuple(realization["nodes"])
    event_confirmation = int(realization["event_confirmation_bar"])
    if len(nodes) != 5:
        raise ValueError("five F3 nodes required")
    full = sorted(ridge_run.ridge_nodes_by_level[level], key=_node_sort_key)
    positions = {str(row.ridge_id): i for i, row in enumerate(full)}
    ids = [str(x.ridge_id) for x in nodes]
    if any(rid not in positions for rid in ids):
        return {"valid": False, "reason": "selected_ridge_missing_from_realization_level"}
    selected_pos = [positions[rid] for rid in ids]
    if selected_pos != sorted(selected_pos):
        return {"valid": False, "reason": "selected_ridges_not_ordered_at_realization_level"}
    start = selected_pos[0]
    if start == 0:
        return {"valid": False, "reason": "ordinal0_left_censored_no_predecessor"}
    pred = full[start - 1]
    if int(pred.node.confirmation_index) > event_confirmation:
        return {"valid": False, "reason": "predecessor_not_confirmed_by_event"}
    if str(pred.node.kind) == str(nodes[0].node.kind):
        return {"valid": False, "reason": "predecessor_kind_not_opposite"}

    filtered = [int(x.node.occurrence_index) for x in nodes]
    if any(b <= a for a, b in zip(filtered, filtered[1:])):
        return {"valid": False, "reason": "selected_filtered_order_conflict"}
    kinds = [str(x.node.kind) for x in nodes]
    member_confirmation = int(nodes[-1].node.confirmation_index)
    if member_confirmation >= len(bars) or event_confirmation >= len(bars):
        return {"valid": False, "reason": "confirmation_outside_bars"}
    closes = np.asarray([float(x["close"]) for x in bars], dtype=float)
    if closes.ndim != 1 or not np.isfinite(closes).all():
        raise ValueError("finite close series required")

    lo = int(pred.node.occurrence_index) + 1
    uppers = [filtered[1] - 1, filtered[2] - 1, filtered[3] - 1, filtered[4] - 1, member_confirmation]
    occ: list[int] = []
    prices: list[float] = []
    windows = []
    for ordinal, (kind, upper) in enumerate(zip(kinds, uppers)):
        hi = min(int(upper), member_confirmation)
        if lo > hi:
            return {"valid": False, "reason": "raw_projection_empty_phase_window", "phase_ordinal": ordinal}
        rel, price = _last_argextreme(closes[lo : hi + 1], kind)
        idx = lo + rel
        occ.append(idx)
        prices.append(price)
        windows.append({"ordinal": ordinal, "lower_bar": lo, "upper_bar": hi, "selected_raw_bar": idx})
        lo = idx + 1

    if any(a >= b for a, b in zip(occ, occ[1:])):
        return {"valid": False, "reason": "raw_projection_order_conflict"}
    for kind, a, b in zip(kinds, prices, prices[1:]):
        if kind == "low" and not b > a:
            return {"valid": False, "reason": "raw_projection_not_actual_turn"}
        if kind == "high" and not b < a:
            return {"valid": False, "reason": "raw_projection_not_actual_turn"}

    confirmation_time = str(bars[event_confirmation]["timestamp"])
    known = bars[event_confirmation].get("available_at", confirmation_time)
    points = []
    for ordinal, (kind, occurrence, price) in enumerate(zip(kinds, occ, prices)):
        pivot_id = stable_id(
            "f3_transplant_raw_pivot_v0702",
            [ids, event_confirmation, ordinal, kind, occurrence, float(price)],
        )
        points.append(
            {
                "kind": kind,
                "occurrence_bar": occurrence,
                "occurrence_time": str(bars[occurrence]["timestamp"]),
                "price": float(price),
                "log_price": math.log(float(price)),
                "left_censored": False,
                "confirmation_bar": event_confirmation,
                "confirmation_time": confirmation_time,
                "effective_information_time": known,
                "bar_end_assumed": False,
                "pivot_id": pivot_id,
            }
        )

    return {
        "valid": True,
        "reason": None,
        "phase": kinds[0],
        "raw_occurrence_bars": occ,
        "raw_prices": prices,
        "points": points,
        "event_confirmation_bar": event_confirmation,
        "member_confirmation_bar": member_confirmation,
        "predecessor_ridge_id": str(pred.ridge_id),
        "predecessor_occurrence_bar": int(pred.node.occurrence_index),
        "windows": windows,
    }


def publish_first_valid_f3_object(ridge_run, key: tuple[str, ...], realizations: Sequence[dict], bars: Sequence[dict]) -> dict:
    ordered = sorted((dict(x) for x in realizations), key=event_order_key)
    if not ordered:
        raise ValueError("at least one certified realization required")
    object_event_confirmation = int(ordered[0]["event_confirmation_bar"])
    publication = None
    prior_invalid = 0
    later_valid_same = 0
    suppressed = 0
    evidence = []

    for realization in ordered:
        projection = project_f3_realization_with_predecessor(ridge_run, realization, bars)
        if publication is None:
            if not bool(projection.get("valid")):
                prior_invalid += 1
                disposition = "invalid_before_publication"
            else:
                publication = {
                    "object_key": tuple(key),
                    "object_event_confirmation_bar": object_event_confirmation,
                    "publishing_confirmation_bar": int(realization["event_confirmation_bar"]),
                    "publishing_level": int(realization["level"]),
                    "phase": str(projection["phase"]),
                    "raw_occurrence_bars": [int(x) for x in projection["raw_occurrence_bars"]],
                    "points": projection["points"],
                    "predecessor_ridge_id": str(projection["predecessor_ridge_id"]),
                    "prior_invalid_projection_count": prior_invalid,
                }
                disposition = "publishing_evidence"
        else:
            if not bool(projection.get("valid")):
                disposition = "invalid_after_publication"
            elif tuple(int(x) for x in projection["raw_occurrence_bars"]) == tuple(publication["raw_occurrence_bars"]):
                later_valid_same += 1
                disposition = "later_valid_same_identity"
            else:
                suppressed += 1
                disposition = "later_valid_would_rewrite_suppressed"
        evidence.append(
            {
                "event_confirmation_bar": int(realization["event_confirmation_bar"]),
                "level": int(realization["level"]),
                "projection_valid": bool(projection.get("valid")),
                "projection_reason": projection.get("reason"),
                "disposition": disposition,
            }
        )

    return {
        "object_key": tuple(key),
        "object_event_confirmation_bar": object_event_confirmation,
        "publication": publication,
        "prior_invalid_projection_count": prior_invalid,
        "later_valid_same_identity_count": later_valid_same,
        "suppressed_would_be_rewrite_count": suppressed,
        "evidence": evidence,
    }


def summarize_case(
    ridge_run,
    chart_start: int,
    cutoff: int,
    cells,
    kinds,
    human_bars,
    bars: Sequence[dict],
) -> dict:
    stores = enumerate_f3_objects_with_certification(ridge_run, chart_start, cutoff)
    static = stores["static"]
    certified = stores["certified"]

    static_support = False
    for realizations in static.values():
        if any(realization_matches_human(r, cells, kinds, human_bars)[0] for r in realizations):
            static_support = True
            break

    certified_support = False
    event_delays = []
    for realizations in certified.values():
        for realization in realizations:
            node_confirmation = max(int(x.node.confirmation_index) for x in realization["nodes"])
            event_delays.append(int(realization["event_confirmation_bar"]) - node_confirmation)
            if realization_matches_human(realization, cells, kinds, human_bars)[0]:
                certified_support = True

    publications = [
        publish_first_valid_f3_object(ridge_run, key, realizations, bars)
        for key, realizations in certified.items()
    ]
    valid_publications = [x for x in publications if x["publication"] is not None]

    published_raw_support = False
    raw_hits = [False] * 5
    for row in valid_publications:
        pub = row["publication"]
        hit, hits = five_bars_hit_cells(pub["raw_occurrence_bars"], pub["phase"], cells, kinds)
        raw_hits = [a or b for a, b in zip(raw_hits, hits)]
        published_raw_support = published_raw_support or hit

    return {
        "static_object_count": len(static),
        "certified_object_count": len(certified),
        "published_object_count": len(valid_publications),
        "static_support": static_support,
        "certified_support": certified_support,
        "published_raw_support": published_raw_support,
        "published_raw_ordinal_hits": raw_hits,
        "event_delays": event_delays,
        "prior_invalid_projection_count": sum(int(x["prior_invalid_projection_count"]) for x in publications),
        "later_valid_same_identity_count": sum(int(x["later_valid_same_identity_count"]) for x in publications),
        "suppressed_would_be_rewrite_count": sum(int(x["suppressed_would_be_rewrite_count"]) for x in publications),
        "valid_publications": valid_publications,
    }


def _dist(values: Sequence[int | float]) -> dict:
    vals = sorted(float(x) for x in values)
    if not vals:
        return {"count": 0, "median": None, "min": None, "max": None}
    return {
        "count": len(vals),
        "median": float(median(vals)),
        "min": float(vals[0]),
        "max": float(vals[-1]),
    }


def summarize_cases(records: Sequence[dict]) -> dict:
    rows = list(records)
    if len(rows) != 11:
        raise ValueError("frozen v0702 anchored universe requires 11 cases")
    exact = [sum(bool(r["published_raw_ordinal_hits"][i]) for r in rows) for i in range(5)]
    delays = [x for r in rows for x in r["event_delays"]]
    return {
        "case_count": 11,
        "static_f3_support_cases": sum(bool(r["static_support"]) for r in rows),
        "causally_certified_f3_support_cases": sum(bool(r["certified_support"]) for r in rows),
        "published_raw_semantic_support_cases": sum(bool(r["published_raw_support"]) for r in rows),
        "static_object_count": _dist([r["static_object_count"] for r in rows]),
        "certified_object_count": _dist([r["certified_object_count"] for r in rows]),
        "published_object_count": _dist([r["published_object_count"] for r in rows]),
        "event_certification_delay_bars": _dist(delays),
        "prior_invalid_projection_count": sum(int(r["prior_invalid_projection_count"]) for r in rows),
        "later_valid_same_identity_count": sum(int(r["later_valid_same_identity_count"]) for r in rows),
        "suppressed_would_be_rewrite_count": sum(int(r["suppressed_would_be_rewrite_count"]) for r in rows),
        "per_ordinal_published_raw_cell_hit_cases": {str(i): exact[i] for i in range(5)},
    }


def frozen_decision(summary: dict, interface_exception_count: int, d1_decisive_override_count: int) -> dict:
    static = int(summary["static_f3_support_cases"])
    certified = int(summary["causally_certified_f3_support_cases"])
    raw = int(summary["published_raw_semantic_support_cases"])
    if static != 8:
        raise AssertionError(f"v0701 static F3 support drift: {static} != 8")
    if certified < SALVAGE_CASE_THRESHOLD:
        category = "v0702_f3_static_objectization_not_causally_publishable"
    elif raw < SALVAGE_CASE_THRESHOLD:
        category = "v0702_f3_event_salvaged_raw_projection_requires_reconstruction"
    elif int(interface_exception_count) != 0 or int(d1_decisive_override_count) != 0:
        category = "v0702_f3_event_projection_salvaged_downstream_interface_incompatible"
    else:
        category = "v0702_f3_event_projection_publication_transplant_supported_downstream_semantic_retest_next"
    return {
        "salvage_threshold_cases": SALVAGE_CASE_THRESHOLD,
        "static_f3_lineage_verified": static == 8,
        "causal_event_support_pass": certified >= SALVAGE_CASE_THRESHOLD,
        "published_raw_semantic_support_pass": raw >= SALVAGE_CASE_THRESHOLD,
        "downstream_interface_exception_zero": int(interface_exception_count) == 0,
        "d1_decisive_override_zero": int(d1_decisive_override_count) == 0,
        "primary_category": category,
    }
