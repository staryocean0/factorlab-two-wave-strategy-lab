"""Frozen v0.7.4 prefix-causal lifecycle helpers for F3 objects."""
from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median
from typing import Sequence

from .f3_causal_certificate_gap_v0703 import analyze_realization_certificate
from .models import stable_id
from .ridge_semantic_objectization_v0701 import (
    causal_survival_levels,
    eligible_nodes_by_level,
    object_key,
    realization_matches_human,
)

SCHEMA = "two_wave_f3_prefix_causal_lifecycle@0.7.4"


def _node_sort_key(row) -> tuple[int, int, str]:
    return (
        int(row.node.occurrence_index),
        int(row.node.confirmation_index),
        str(row.node.node_id),
    )


def lifecycle_event_bars(ridge_run, chart_start: int, cutoff: int) -> list[int]:
    """Return the frozen prefix event clock for one fixed case window."""
    chart_start = int(chart_start)
    cutoff = int(cutoff)
    window_rids: set[str] = set()
    bars = {cutoff}
    for rows in ridge_run.ridge_nodes_by_level:
        for row in rows:
            occ = int(row.node.occurrence_index)
            conf = int(row.node.confirmation_index)
            if chart_start <= occ <= cutoff:
                window_rids.add(str(row.ridge_id))
                if conf <= cutoff:
                    bars.add(conf)
    for death in ridge_run.deaths:
        if str(death.ridge_id) in window_rids and int(death.confirmation_index) <= cutoff:
            bars.add(int(death.confirmation_index))
    return sorted(int(x) for x in bars if int(x) <= cutoff)


def dominant_quintet_indices(rows: Sequence[object], survival: dict[str, int]):
    """Enumerate exactly the frozen F3 persistence-dominant alternating quintets.

    The pairwise F3 condition defines a forward visibility edge i->j when the
    endpoint kinds differ and every skipped ridge has survival strictly below
    both endpoints. F3 quintets are exactly increasing paths of five vertices.
    This avoids brute-force 5-combinations without changing the definition.
    """
    n = len(rows)
    if n < 5:
        return
    successors: list[list[int]] = [[] for _ in range(n)]
    surv = [int(survival[str(row.ridge_id)]) for row in rows]
    kinds = [str(row.node.kind) for row in rows]
    for i in range(n):
        interior_max = -1
        for j in range(i + 1, n):
            if j > i + 1:
                interior_max = max(interior_max, surv[j - 1])
            if kinds[i] == kinds[j]:
                continue
            boundary = min(surv[i], surv[j])
            if interior_max < boundary:
                successors[i].append(j)

    chosen: list[int] = []

    def rec(idx: int):
        chosen.append(idx)
        if len(chosen) == 5:
            yield tuple(chosen)
        else:
            for nxt in successors[idx]:
                yield from rec(nxt)
        chosen.pop()

    for start in range(n):
        yield from rec(start)


def enumerate_static_f3_at_prefix(ridge_run, chart_start: int, cutoff: int) -> dict[tuple[str, ...], list[dict]]:
    """Return all frozen static F3 realizations known at a prefix."""
    levels = eligible_nodes_by_level(ridge_run, chart_start, cutoff)
    survival = causal_survival_levels(levels)
    store: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for level, rows in enumerate(levels):
        for idxs in dominant_quintet_indices(rows, survival):
            nodes = tuple(rows[i] for i in idxs)
            key = object_key(nodes)
            store[key].append(
                {
                    "level": int(level),
                    "nodes": nodes,
                    "idxs": tuple(int(x) for x in idxs),
                    "level_rows": rows,
                }
            )
    return dict(store)


def _witness_order(realization: dict) -> tuple:
    nodes = tuple(realization["nodes"])
    return (
        max(int(x.node.confirmation_index) for x in nodes),
        int(realization["level"]),
        tuple(int(x.node.occurrence_index) for x in nodes),
        tuple(str(x.node.node_id) for x in nodes),
    )


def _event_payload(kind: str, bar: int, object_id: str, key: tuple[str, ...], witness: dict | None = None) -> dict:
    row = {
        "kind": str(kind),
        "event_bar": int(bar),
        "object_id": str(object_id),
        "object_key": tuple(str(x) for x in key),
    }
    if witness is not None:
        nodes = tuple(witness["nodes"])
        row.update(
            {
                "witness_level": int(witness["level"]),
                "witness_node_ids": tuple(str(x.node.node_id) for x in nodes),
                "witness_occurrence_bars": tuple(int(x.node.occurrence_index) for x in nodes),
            }
        )
    return row


def _certification_candidates(ridge_run, realizations: Sequence[dict], cutoff: int) -> list[tuple[tuple, dict, dict]]:
    out = []
    for realization in realizations:
        audit = analyze_realization_certificate(
            ridge_run,
            realization["level_rows"],
            realization["idxs"],
            int(realization["level"]),
            int(cutoff),
        )
        if not bool(audit["c1_ok"]):
            continue
        nodes = tuple(realization["nodes"])
        order = (
            int(audit["c1_confirmation_bar"]),
            int(realization["level"]),
            tuple(int(x.node.occurrence_index) for x in nodes),
            tuple(str(x.node.node_id) for x in nodes),
        )
        out.append((order, realization, audit))
    return sorted(out, key=lambda x: x[0])


def build_lifecycle_for_case(ridge_run, chart_start: int, cutoff: int) -> dict:
    """Replay one case into an append-only F3 object lifecycle ledger."""
    event_bars = lifecycle_event_bars(ridge_run, chart_start, cutoff)
    objects: dict[tuple[str, ...], dict] = {}
    id_to_key: dict[str, tuple[str, ...]] = {}
    violations: Counter[str] = Counter()
    final_store: dict[tuple[str, ...], list[dict]] = {}
    observation_witness_multiplicity: list[int] = []

    for t in event_bars:
        current = enumerate_static_f3_at_prefix(ridge_run, chart_start, t)
        current_keys = set(current)
        final_store = current

        # Historical observations are emitted exactly once.
        for key in sorted(current_keys):
            if key in objects:
                continue
            object_id = stable_id("f3_lifecycle_object_v0704", {"schema": SCHEMA, "object_key": key})
            prior_key = id_to_key.get(object_id)
            if prior_key is not None and prior_key != key:
                violations["object_id_collision"] += 1
            id_to_key[object_id] = key
            witness = min(current[key], key=_witness_order)
            observation_witness_multiplicity.append(len(current[key]))
            objects[key] = {
                "object_id": object_id,
                "first_observation_bar": int(t),
                "first_witness_order": _witness_order(witness),
                "first_witness": witness,
                "state": "observed_live_unresolved",
                "certified": False,
                "certification_bar": None,
                "events": [_event_payload("observed", t, object_id, key, witness)],
            }

        # Unresolved live objects may become dormant; dormant objects may return.
        for key, obj in objects.items():
            if bool(obj["certified"]):
                if key not in current_keys:
                    violations["certified_object_absent_from_later_static_set"] += 1
                continue
            if key in current_keys:
                if obj["state"] == "observed_dormant_unresolved":
                    obj["events"].append(_event_payload("reobserved", t, obj["object_id"], key))
                    obj["state"] = "observed_live_unresolved"
            else:
                if obj["state"] == "observed_live_unresolved":
                    obj["events"].append(_event_payload("dormant", t, obj["object_id"], key))
                    obj["state"] = "observed_dormant_unresolved"

        # Certification is a terminal append-only transition and uses frozen C1.
        for key in sorted(current_keys):
            obj = objects[key]
            if bool(obj["certified"]):
                continue
            candidates = _certification_candidates(ridge_run, current[key], t)
            if not candidates:
                continue
            _, witness, audit = candidates[0]
            cert_bar = int(audit["c1_confirmation_bar"])
            if cert_bar > int(t):
                violations["certification_uses_future_evidence"] += 1
                continue
            if cert_bar < int(obj["first_observation_bar"]):
                violations["certification_before_observation"] += 1
            obj["events"].append(_event_payload("certified", t, obj["object_id"], key, witness))
            obj["state"] = "certified"
            obj["certified"] = True
            obj["certification_bar"] = int(t)
            obj["certification_proof_bar"] = cert_bar

    # Frozen ledger invariants.
    for key, obj in objects.items():
        events = list(obj["events"])
        if sum(str(x["kind"]) == "observed" for x in events) != 1:
            violations["observed_event_count_not_one"] += 1
        event_times = [int(x["event_bar"]) for x in events]
        if any(b < a for a, b in zip(event_times, event_times[1:])):
            violations["event_time_not_nondecreasing"] += 1
        if tuple(obj["first_witness_order"]) != tuple(_witness_order(obj["first_witness"])):
            violations["first_observation_witness_rewritten"] += 1
        if any(str(x["object_id"]) != str(obj["object_id"]) for x in events):
            violations["object_identity_rewritten"] += 1
        if bool(obj["certified"]):
            cert_positions = [i for i, x in enumerate(events) if str(x["kind"]) == "certified"]
            if len(cert_positions) != 1:
                violations["certified_event_count_not_one"] += 1
            elif any(str(x["kind"]) in {"dormant", "reobserved"} for x in events[cert_positions[0] + 1 :]):
                violations["transition_after_certification"] += 1

    final_keys = set(final_store)
    derived_live = {
        key
        for key, obj in objects.items()
        if (
            (bool(obj["certified"]) and key in final_keys)
            or (not bool(obj["certified"]) and obj["state"] == "observed_live_unresolved")
        )
    }
    if derived_live != final_keys:
        violations["final_live_static_object_key_set_mismatch"] += len(derived_live ^ final_keys) or 1

    return {
        "event_bars": event_bars,
        "objects": objects,
        "final_static_store": final_store,
        "final_live_keys": derived_live,
        "violations": dict(sorted(violations.items())),
        "observation_witness_multiplicity": observation_witness_multiplicity,
    }


def _ordinal_cell_hits(realizations: Sequence[dict], cells, kinds) -> list[bool]:
    hits = [False] * 5
    for realization in realizations:
        for i, (node, cell, kind) in enumerate(zip(realization["nodes"], cells, kinds)):
            occ = int(node.node.occurrence_index)
            if int(cell[0]) <= occ <= int(cell[1]) and str(node.node.kind) == str(kind):
                hits[i] = True
    return hits


def summarize_case_semantics(lifecycle: dict, ridge_run, cutoff: int, cells, kinds, human_bars) -> dict:
    """Score only final-cutoff semantic continuity after label-free lifecycle construction."""
    store = lifecycle["final_static_store"]
    static_support = False
    live_support = False
    certified_support = False
    live_unresolved_support = False
    ordinal_hits = [False] * 5

    for key, realizations in store.items():
        compatible = [
            r for r in realizations
            if realization_matches_human(r, cells, kinds, human_bars)[0]
        ]
        if compatible:
            static_support = True
            if key in lifecycle["final_live_keys"]:
                live_support = True
            if not bool(lifecycle["objects"][key]["certified"]):
                live_unresolved_support = True

        for realization in compatible:
            audit = analyze_realization_certificate(
                ridge_run,
                realization["level_rows"],
                realization["idxs"],
                int(realization["level"]),
                int(cutoff),
            )
            if bool(audit["c1_ok"]):
                certified_support = True

        hits = _ordinal_cell_hits(realizations, cells, kinds)
        ordinal_hits = [a or b for a, b in zip(ordinal_hits, hits)]

    return {
        "static_support": bool(static_support),
        "lifecycle_live_support": bool(live_support),
        "certified_support": bool(certified_support),
        "live_unresolved_support": bool(live_unresolved_support),
        "ordinal_live_cell_hits": ordinal_hits,
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


def summarize_lifecycle_cases(records: Sequence[dict]) -> dict:
    rows = list(records)
    if len(rows) != 11:
        raise ValueError("v0704 frozen anchored universe requires exactly 11 cases")

    observed_counts = []
    certified_counts = []
    live_unresolved_counts = []
    dormant_counts = []
    transition_counts = []
    cert_delays = []
    witness_mult = []
    dormant_objects = 0
    reobserved_objects = 0
    violation_counts: Counter[str] = Counter()

    for row in rows:
        life = row["lifecycle"]
        objects = life["objects"]
        observed_counts.append(len(objects))
        certified_counts.append(sum(bool(x["certified"]) for x in objects.values()))
        live_unresolved_counts.append(
            sum((not bool(x["certified"])) and x["state"] == "observed_live_unresolved" for x in objects.values())
        )
        dormant_counts.append(
            sum((not bool(x["certified"])) and x["state"] == "observed_dormant_unresolved" for x in objects.values())
        )
        witness_mult.extend(int(x) for x in life["observation_witness_multiplicity"])
        violation_counts.update({str(k): int(v) for k, v in life["violations"].items()})
        for obj in objects.values():
            events = list(obj["events"])
            transition_counts.append(len(events))
            kinds = [str(x["kind"]) for x in events]
            dormant_objects += int("dormant" in kinds)
            reobserved_objects += int("reobserved" in kinds)
            if bool(obj["certified"]):
                cert_delays.append(int(obj["certification_bar"]) - int(obj["first_observation_bar"]))

    semantics = [r["semantics"] for r in rows]
    exact = [sum(bool(r["ordinal_live_cell_hits"][i]) for r in semantics) for i in range(5)]
    static_support = sum(bool(r["static_support"]) for r in semantics)
    live_support = sum(bool(r["lifecycle_live_support"]) for r in semantics)
    certified_support = sum(bool(r["certified_support"]) for r in semantics)
    unresolved_support = sum(bool(r["live_unresolved_support"]) for r in semantics)
    gap_rows = [r for r in semantics if bool(r["static_support"]) and not bool(r["certified_support"])]

    return {
        "case_count": 11,
        "semantic_continuity": {
            "static_f3_support_cases": static_support,
            "lifecycle_live_support_cases": live_support,
            "certified_support_cases": certified_support,
            "live_unresolved_support_cases": unresolved_support,
            "static_supported_certified_unsupported_cases": len(gap_rows),
            "all_permanent_certificate_gap_cases_live_unresolved": bool(gap_rows) and all(
                bool(r["live_unresolved_support"]) for r in gap_rows
            ),
            "per_ordinal_live_cell_hit_cases": {str(i): int(exact[i]) for i in range(5)},
        },
        "mechanics": {
            "observed_object_count_per_case": distribution(observed_counts),
            "certified_object_count_per_case": distribution(certified_counts),
            "live_unresolved_object_count_at_cutoff_per_case": distribution(live_unresolved_counts),
            "dormant_unresolved_object_count_at_cutoff_per_case": distribution(dormant_counts),
            "objects_with_dormant_transition": int(dormant_objects),
            "objects_with_reobserved_transition": int(reobserved_objects),
            "observation_to_certification_delay_bars": distribution(cert_delays),
            "lifecycle_event_count_per_object": distribution(transition_counts),
            "first_observation_witness_multiplicity": distribution(witness_mult),
            "suppressed_attempted_identity_rewrites": 0,
        },
        "hard_invariant_violation_counts": dict(sorted(violation_counts.items())),
        "hard_invariant_violation_count": int(sum(violation_counts.values())),
    }


def frozen_decision(summary: dict) -> dict:
    continuity = summary["semantic_continuity"]
    violations = int(summary["hard_invariant_violation_count"])
    static_support = int(continuity["static_f3_support_cases"])
    live_support = int(continuity["lifecycle_live_support_cases"])
    certified_support = int(continuity["certified_support_cases"])

    if static_support != 8:
        raise AssertionError(f"v0701 static F3 support drift: {static_support} != 8")
    if certified_support != 7:
        raise AssertionError(f"v0703 C1 certified support drift: {certified_support} != 7")

    if violations:
        category = "v0704_f3_lifecycle_append_only_or_causal_invariant_failed"
    elif live_support != 8:
        category = "v0704_f3_lifecycle_does_not_preserve_static_semantics"
    elif certified_support != 7:
        category = "v0704_f3_lifecycle_certification_lineage_drift"
    else:
        category = "v0704_f3_prefix_causal_lifecycle_representation_supported"

    return {
        "static_support_replication_ok": static_support == 8,
        "certified_support_replication_ok": certified_support == 7,
        "lifecycle_live_support_preserved": live_support == 8,
        "hard_invariant_violation_zero": violations == 0,
        "permanent_certificate_gap_live_unresolved": bool(
            continuity["all_permanent_certificate_gap_cases_live_unresolved"]
        ),
        "primary_category": category,
    }
