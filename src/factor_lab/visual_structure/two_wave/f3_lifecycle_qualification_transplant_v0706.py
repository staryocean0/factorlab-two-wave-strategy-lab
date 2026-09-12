"""Frozen v0.7.6 qualification transplant for immutable F3 lifecycle publications."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from statistics import median
from typing import Sequence

from .path_gate_demotion_v0618 import (
    DEMOTED_PATH_REASONS,
    qualify_published_raw_identity_v0618,
)
from .published_identity_qualification_v066 import qualify_published_raw_identity
from .semantic_bridge_counteroffensive_v0700 import five_bars_hit_cells

SCHEMA = "two_wave_f3_lifecycle_qualification_transplant@0.7.6"
EXPECTED_PUBLICATIONS = 1543
EXPECTED_CERTIFIED_OBJECTS = 1478
EXPECTED_FINAL_UNRESOLVED_OBJECTS = 65
EXPECTED_RAW_SEMANTIC_SUPPORT_CASES = 9
SEMANTIC_SUPPORT_GATE_CASES = 8
EXPECTED_ORDINAL_CASES = (11, 11, 11, 11, 10)


class PrefixBars(Sequence):
    """Read-only sequence exposing no source bar after one causal stop."""

    def __init__(self, bars: Sequence[dict], stop: int):
        self._bars = bars
        self._stop = int(stop)
        if self._stop < 0 or self._stop > len(bars):
            raise ValueError("prefix stop outside supplied bars")

    def __len__(self) -> int:
        return self._stop

    def __getitem__(self, item):
        if isinstance(item, slice):
            start, stop, step = item.indices(self._stop)
            return self._bars[start:stop:step]
        idx = int(item)
        if idx < 0:
            idx += self._stop
        if idx < 0 or idx >= self._stop:
            raise IndexError(idx)
        return self._bars[idx]


def publication_identity_payload(publication: dict) -> dict:
    return {
        "object_id": str(publication["object_id"]),
        "object_key": [str(x) for x in publication["object_key"]],
        "publication_id": str(publication["publication_id"]),
        "first_observation_bar": int(publication["first_observation_bar"]),
        "publishing_evidence_bar": int(publication["publishing_evidence_bar"]),
        "publishing_level": int(publication["publishing_level"]),
        "predecessor_ridge_id": str(publication["predecessor_ridge_id"]),
        "phase": str(publication["phase"]),
        "raw_occurrence_bars": [int(x) for x in publication["raw_occurrence_bars"]],
        "pivot_ids": [str(x["pivot_id"]) for x in publication["points"]],
    }


def publication_identity_hash(publication: dict) -> str:
    encoded = json.dumps(
        publication_identity_payload(publication),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def qualification_args(publication: dict, bars: Sequence[dict]):
    confirmation = int(publication["publishing_evidence_bar"])
    raw = tuple(int(x) for x in publication["raw_occurrence_bars"])
    phase = str(publication["phase"])
    if confirmation < 0 or confirmation >= len(bars):
        raise ValueError("publication confirmation outside source bars")
    if len(raw) != 5 or raw[-1] > confirmation:
        raise ValueError("immutable publication anchors outside causal prefix")
    prefix = PrefixBars(bars, confirmation + 1)
    if len(prefix) != confirmation + 1:
        raise AssertionError("causal prefix length drift")
    return phase, raw, confirmation, prefix


def _same_measurements(v054: dict, v0618: dict) -> bool:
    fields = (
        "phase",
        "five_raw_occurrence_bars",
        "publishing_confirmation_bar",
        "v043_scale_rejection_reasons",
        "v054_hard_rejection_reasons",
        "corresponding_leg_duration_diagnostic_triggered",
        "leg_durations",
        "cycle_durations",
        "amplitude_ratio",
        "leg_efficiencies",
        "leg_jump_shares",
        "leg_flat_shares",
        "observed_trading_days",
        "wall_days",
        "confirmation_delay_bars",
    )
    return all(v054.get(field) == v0618.get(field) for field in fields)


def qualification_contract_violations(v054: dict, v0618: dict) -> dict[str, int]:
    violations: Counter[str] = Counter()
    old = [str(x) for x in v054["v054_hard_rejection_reasons"]]
    replay_old = [str(x) for x in v0618["v054_hard_rejection_reasons"]]
    new = [str(x) for x in v0618["v0618_hard_rejection_reasons"]]

    if old != replay_old:
        violations["v054_measurement_or_reason_replay_drift"] += 1
    if not _same_measurements(v054, v0618):
        violations["non_policy_measurement_drift"] += 1
    if any(reason not in old for reason in new):
        violations["v0618_added_hard_reason"] += 1
    removed = set(old) - set(new)
    if not removed.issubset(set(DEMOTED_PATH_REASONS)):
        violations["v0618_removed_non_demoted_reason"] += 1
    expected_new = [reason for reason in old if reason not in DEMOTED_PATH_REASONS]
    if new != expected_new:
        violations["v0618_hard_reason_sequence_not_exact_demotion"] += 1
    if bool(v054["scale_qualified"]) and not bool(v0618["scale_qualified"]):
        violations["v0618_non_monotone_rejection"] += 1
    if bool(v054.get("future_outcome_used")) or bool(v0618.get("future_outcome_used")):
        violations["future_outcome_used"] += 1
    if bool(v054.get("trade_authority")) or bool(v0618.get("trade_authority")):
        violations["trade_authority_granted"] += 1
    return dict(violations)


def qualify_publication(publication: dict, bars: Sequence[dict], cfg=None) -> dict:
    """Qualify one immutable publication on its causal bar prefix only."""
    before = publication_identity_hash(publication)
    phase, raw, confirmation, prefix = qualification_args(publication, bars)
    v054 = qualify_published_raw_identity(phase, raw, confirmation, prefix, cfg=cfg)
    v0618 = qualify_published_raw_identity_v0618(phase, raw, confirmation, prefix, cfg=cfg)
    after = publication_identity_hash(publication)
    return {
        "v054": v054,
        "v0618": v0618,
        "identity_mutated": before != after,
        "identity_hash": before,
        "prefix_stop": confirmation + 1,
        "contract_violations": qualification_contract_violations(v054, v0618),
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


def _policy_summary(rows: Sequence[dict], policy: str) -> dict:
    qualified = [row for row in rows if bool(row[policy]["scale_qualified"])]
    rejected = [row for row in rows if not bool(row[policy]["scale_qualified"])]
    reason_key = "v054_hard_rejection_reasons" if policy == "v054" else "v0618_hard_rejection_reasons"
    reasons: Counter[str] = Counter()
    for row in rows:
        reasons.update(str(x) for x in row[policy][reason_key])

    def measurement_summary(items: Sequence[dict]) -> dict:
        qrows = [x[policy] for x in items]
        cycles = [float(v) for q in qrows for v in q["cycle_durations"]]
        amps = [float(q["amplitude_ratio"]) for q in qrows if q["amplitude_ratio"] is not None]
        delays = [int(q["confirmation_delay_bars"]) for q in qrows]
        return {
            "confirmation_delay_bars": distribution(delays),
            "cycle_durations": distribution(cycles),
            "amplitude_ratio": distribution(amps),
        }

    return {
        "evaluated_count": len(rows),
        "qualified_count": len(qualified),
        "qualified_fraction": len(qualified) / len(rows) if rows else None,
        "rejected_count": len(rejected),
        "hard_reason_counts": dict(sorted(reasons.items())),
        "qualified_measurements": measurement_summary(qualified),
        "rejected_measurements": measurement_summary(rejected),
    }


def summarize_qualification_records(rows: Sequence[dict]) -> dict:
    rows = list(rows)
    strata_names = (
        "already_certified_at_publication",
        "unresolved_at_publication_later_certified",
        "unresolved_at_publication_still_unresolved",
        "final_certified",
        "final_unresolved",
    )
    strata = {}
    for name in strata_names:
        subset = [row for row in rows if bool(row["strata"].get(name))]
        strata[name] = {
            "publication_count": len(subset),
            "v054_qualified_count": sum(bool(x["v054"]["scale_qualified"]) for x in subset),
            "v0618_qualified_count": sum(bool(x["v0618"]["scale_qualified"]) for x in subset),
        }

    transitions: Counter[str] = Counter()
    changed = 0
    for row in rows:
        if not bool(row["v054"]["scale_qualified"]) and bool(row["v0618"]["scale_qualified"]):
            changed += 1
            old = set(str(x) for x in row["v054"]["v054_hard_rejection_reasons"])
            new = set(str(x) for x in row["v0618"]["v0618_hard_rejection_reasons"])
            removed = sorted(old - new)
            transitions["+".join(removed) if removed else "none"] += 1

    contract: Counter[str] = Counter()
    for row in rows:
        contract.update({str(k): int(v) for k, v in row["contract_violations"].items()})

    return {
        "publication_count": len(rows),
        "v054": _policy_summary(rows, "v054"),
        "v0618": _policy_summary(rows, "v0618"),
        "v0618_reject_to_qualified_count": changed,
        "v0618_demotion_transition_counts": dict(sorted(transitions.items())),
        "contract_violation_counts": dict(sorted(contract.items())),
        "contract_violation_count": int(sum(contract.values())),
        "identity_mutation_count": sum(bool(x["identity_mutated"]) for x in rows),
        "lifecycle_strata": strata,
    }


def summarize_case_semantics(
    publication: dict,
    lifecycle: dict,
    qualification_by_key: dict[tuple[str, ...], dict],
    cells,
    kinds,
) -> dict:
    raw_support = False
    v054_support = False
    v0618_support = False
    raw_ordinal = [False] * 5
    v054_ordinal = [False] * 5
    v0618_ordinal = [False] * 5
    final_unresolved_v0618_support = False

    final_live_keys = set(lifecycle["final_live_keys"])
    for key, state in publication["states"].items():
        pub = state["publication"]
        q = qualification_by_key.get(key)
        if pub is None or q is None or key not in final_live_keys:
            continue
        hit, ordinal = five_bars_hit_cells(pub["raw_occurrence_bars"], pub["phase"], cells, kinds)
        raw_support = raw_support or bool(hit)
        raw_ordinal = [a or b for a, b in zip(raw_ordinal, ordinal)]
        if bool(q["v054"]["scale_qualified"]):
            v054_support = v054_support or bool(hit)
            v054_ordinal = [a or b for a, b in zip(v054_ordinal, ordinal)]
        if bool(q["v0618"]["scale_qualified"]):
            v0618_support = v0618_support or bool(hit)
            v0618_ordinal = [a or b for a, b in zip(v0618_ordinal, ordinal)]
            if not bool(lifecycle["objects"][key]["certified"]):
                final_unresolved_v0618_support = final_unresolved_v0618_support or bool(hit)

    return {
        "published_raw_support": bool(raw_support),
        "v054_qualified_semantic_support": bool(v054_support),
        "v0618_qualified_semantic_support": bool(v0618_support),
        "published_raw_ordinal_hits": raw_ordinal,
        "v054_qualified_ordinal_hits": v054_ordinal,
        "v0618_qualified_ordinal_hits": v0618_ordinal,
        "final_unresolved_v0618_qualified_raw_support": bool(final_unresolved_v0618_support),
    }


def summarize_semantic_cases(rows: Sequence[dict]) -> dict:
    rows = list(rows)
    if len(rows) != 11:
        raise ValueError("v0706 frozen anchored universe requires exactly 11 cases")

    def count_flag(name: str) -> int:
        return sum(bool(x[name]) for x in rows)

    def ordinal_counts(name: str) -> list[int]:
        return [sum(bool(row[name][i]) for row in rows) for i in range(5)]

    return {
        "case_count": 11,
        "published_raw_support_cases": count_flag("published_raw_support"),
        "v054_qualified_semantic_support_cases": count_flag("v054_qualified_semantic_support"),
        "v0618_qualified_semantic_support_cases": count_flag("v0618_qualified_semantic_support"),
        "published_raw_ordinal_hit_cases": ordinal_counts("published_raw_ordinal_hits"),
        "v054_qualified_ordinal_hit_cases": ordinal_counts("v054_qualified_ordinal_hits"),
        "v0618_qualified_ordinal_hit_cases": ordinal_counts("v0618_qualified_ordinal_hits"),
        "final_unresolved_v0618_qualified_raw_support_cases": count_flag(
            "final_unresolved_v0618_qualified_raw_support"
        ),
    }


def frozen_decision(
    *,
    upstream: dict,
    interface: dict,
    qualification: dict,
    semantic: dict,
) -> dict:
    upstream_ok = (
        int(upstream["observed_lifecycle_object_count"]) == EXPECTED_PUBLICATIONS
        and int(upstream["published_lifecycle_object_count"]) == EXPECTED_PUBLICATIONS
        and int(upstream["certified_lifecycle_object_count"]) == EXPECTED_CERTIFIED_OBJECTS
        and int(upstream["certified_object_publication_count"]) == EXPECTED_CERTIFIED_OBJECTS
        and int(upstream["final_unresolved_object_count"]) == EXPECTED_FINAL_UNRESOLVED_OBJECTS
        and int(upstream["final_unresolved_published_count"]) == EXPECTED_FINAL_UNRESOLVED_OBJECTS
        and float(upstream["publication_delay_min_bars"]) == 0.0
        and float(upstream["publication_delay_median_bars"]) == 0.0
        and float(upstream["publication_delay_max_bars"]) == 0.0
        and int(upstream["publication_hard_invariant_violation_count"]) == 0
        and int(upstream["published_raw_semantic_support_cases"]) == EXPECTED_RAW_SEMANTIC_SUPPORT_CASES
        and tuple(int(x) for x in upstream["published_raw_ordinal_hit_cases"]) == EXPECTED_ORDINAL_CASES
        and int(upstream["permanent_certificate_gap_case_count"]) == 1
        and int(upstream["gap_same_object_provisional_raw_support_cases"]) == 1
    )

    interface_ok = (
        int(interface["v054_evaluated_count"]) == EXPECTED_PUBLICATIONS
        and int(interface["v0618_evaluated_count"]) == EXPECTED_PUBLICATIONS
        and int(interface["v054_exception_count"]) == 0
        and int(interface["v0618_exception_count"]) == 0
        and int(interface["identity_mutation_count"]) == 0
        and int(interface["future_bar_dependency_violation_count"]) == 0
        and int(interface["future_outcome_or_trade_authority_violation_count"]) == 0
    )
    contract_ok = int(qualification["contract_violation_count"]) == 0
    semantic_count = int(semantic["v0618_qualified_semantic_support_cases"])
    semantic_ok = semantic_count >= SEMANTIC_SUPPORT_GATE_CASES

    if not upstream_ok:
        category = "v0706_upstream_replication_drift_invalid"
    elif not interface_ok:
        category = "v0706_qualification_interface_incompatible"
    elif not contract_ok:
        category = "v0706_v0618_qualification_contract_violation"
    elif semantic_ok:
        category = "v0706_v0618_lifecycle_qualification_transplant_supported"
    else:
        category = "v0706_qualification_interface_clean_but_semantic_support_insufficient"

    return {
        "upstream_replication_ok": bool(upstream_ok),
        "interface_gate_passed": bool(interface_ok),
        "v0618_contract_gate_passed": bool(contract_ok),
        "semantic_support_gate_cases": SEMANTIC_SUPPORT_GATE_CASES,
        "v0618_qualified_semantic_support_cases": semantic_count,
        "semantic_support_gate_passed": bool(semantic_ok),
        "primary_category": category,
    }
