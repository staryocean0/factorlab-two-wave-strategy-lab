"""Frozen helpers for v0.7.3 F3 causal-certificate gap attribution."""
from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Sequence

from .f3_event_publication_transplant_v0702 import _death_index


def _level_maps_confirmed(ridge_run, cutoff: int) -> list[dict[str, object]]:
    out = []
    for rows in ridge_run.ridge_nodes_by_level:
        out.append(
            {
                str(row.ridge_id): row
                for row in rows
                if int(row.node.confirmation_index) <= int(cutoff)
            }
        )
    return out


def _level_maps_all(ridge_run) -> list[dict[str, object]]:
    return [
        {str(row.ridge_id): row for row in rows}
        for rows in ridge_run.ridge_nodes_by_level
    ]


def analyze_realization_certificate(
    ridge_run,
    level_rows: Sequence[object],
    idxs: Sequence[int],
    level: int,
    cutoff: int,
) -> dict:
    """Return C0 blockers and the preregistered minimal explicit-death C1 proof.

    Blockers are attributed under the frozen cutoff.  Full-lineage inspection is
    used only to distinguish evidence absent by cutoff from evidence that exists
    but confirms later; it never changes C1 eligibility at the cutoff.
    """
    idxs = tuple(int(x) for x in idxs)
    if len(idxs) != 5 or any(b <= a for a, b in zip(idxs, idxs[1:])):
        raise ValueError("five increasing selected positions required")
    nodes = tuple(level_rows[i] for i in idxs)
    if any(int(x.node.confirmation_index) > int(cutoff) for x in nodes):
        raise AssertionError("static F3 realization contains node unknown at cutoff")

    confirmed = _level_maps_confirmed(ridge_run, cutoff)
    full = _level_maps_all(ridge_run)
    deaths = _death_index(ridge_run)
    blockers: list[str] = []
    c1_confirmation = max(int(x.node.confirmation_index) for x in nodes)
    skipped_count = 0
    c1_ok = True

    for left_pos, right_pos in zip(idxs, idxs[1:]):
        left = level_rows[left_pos]
        right = level_rows[right_pos]
        left_id, right_id = str(left.ridge_id), str(right.ridge_id)
        for skipped in level_rows[left_pos + 1 : right_pos]:
            skipped_count += 1
            rid = str(skipped.ridge_id)
            death = deaths.get(rid)
            if death is None:
                blockers.append("missing_explicit_death_by_cutoff")
                c1_ok = False
                continue
            if int(death.confirmation_index) > int(cutoff):
                blockers.append("missing_explicit_death_by_cutoff")
                blockers.append("proof_confirmation_after_cutoff")
                c1_ok = False
                continue
            if int(death.fine_level) < int(level):
                blockers.append("death_transition_before_realization_level")
                c1_ok = False
                continue

            k = int(death.coarse_level)
            if k >= len(confirmed):
                blockers.append("other_contract_blocker")
                c1_ok = False
                continue

            exact_left = confirmed[k].get(left_id)
            exact_right = confirmed[k].get(right_id)

            left_candidates = []
            right_candidates = []
            left_future = []
            right_future = []
            for higher in range(k, len(confirmed)):
                lrow = confirmed[higher].get(left_id)
                rrow = confirmed[higher].get(right_id)
                if lrow is not None:
                    left_candidates.append((int(lrow.node.confirmation_index), higher, lrow))
                if rrow is not None:
                    right_candidates.append((int(rrow.node.confirmation_index), higher, rrow))
                lfull = full[higher].get(left_id)
                rfull = full[higher].get(right_id)
                if lfull is not None and int(lfull.node.confirmation_index) > int(cutoff):
                    left_future.append((int(lfull.node.confirmation_index), higher, lfull))
                if rfull is not None and int(rfull.node.confirmation_index) > int(cutoff):
                    right_future.append((int(rfull.node.confirmation_index), higher, rfull))

            if exact_left is None:
                if left_candidates:
                    blockers.append("exact_coarse_boundary_representation_missing_but_coarser_confirmed_survival_exists")
                else:
                    blockers.append("left_boundary_not_proven_past_death_by_cutoff")
                    if left_future:
                        blockers.append("proof_confirmation_after_cutoff")
            if exact_right is None:
                if right_candidates:
                    blockers.append("exact_coarse_boundary_representation_missing_but_coarser_confirmed_survival_exists")
                else:
                    blockers.append("right_boundary_not_proven_past_death_by_cutoff")
                    if right_future:
                        blockers.append("proof_confirmation_after_cutoff")

            if not left_candidates:
                c1_ok = False
            if not right_candidates:
                c1_ok = False
            if left_candidates and right_candidates:
                # Use the earliest qualifying confirmed representation at any level >= k.
                left_proof = min(left_candidates)
                right_proof = min(right_candidates)
                proof_confirmation = max(
                    int(death.confirmation_index),
                    int(left_proof[0]),
                    int(right_proof[0]),
                )
                if proof_confirmation > int(cutoff):
                    blockers.append("proof_confirmation_after_cutoff")
                    c1_ok = False
                else:
                    c1_confirmation = max(c1_confirmation, proof_confirmation)

    # C0 passes exactly when no C0-contract blocker is present.  Future-evidence
    # attribution labels are descriptive and only occur together with a C0
    # failure mode above.
    c0_ok = not blockers
    return {
        "c0_ok": c0_ok,
        "c1_ok": bool(c1_ok),
        "c1_confirmation_bar": int(c1_confirmation) if c1_ok else None,
        "c1_confirmation_delay_from_selected_nodes": (
            int(c1_confirmation) - max(int(x.node.confirmation_index) for x in nodes)
            if c1_ok
            else None
        ),
        "skipped_ridge_count": skipped_count,
        "blockers": blockers,
        "blocker_counts": dict(Counter(blockers)),
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


def frozen_decision(
    *,
    static_support_cases: int,
    c0_support_cases: int,
    gap_case_count: int,
    c1_support_cases: int,
    gap_realization_blocker_sets: Sequence[Sequence[str]],
) -> dict:
    if int(static_support_cases) != 8:
        raise AssertionError(f"v0701 static F3 support drift: {static_support_cases} != 8")
    if int(c0_support_cases) != 7:
        raise AssertionError(f"v0702 C0 causal support drift: {c0_support_cases} != 7")
    if int(gap_case_count) != 1:
        raise AssertionError(f"v0702 gap-case count drift: {gap_case_count} != 1")

    blocker_sets = [set(str(x) for x in row) for row in gap_realization_blocker_sets]
    if not blocker_sets:
        raise AssertionError("gap case must have at least one human-compatible static F3 realization")

    every_missing_death = all("missing_explicit_death_by_cutoff" in row for row in blocker_sets)
    boundary_names = {
        "left_boundary_not_proven_past_death_by_cutoff",
        "right_boundary_not_proven_past_death_by_cutoff",
    }
    every_boundary_unavailable = all(bool(row & boundary_names) for row in blocker_sets)
    every_after_cutoff = all("proof_confirmation_after_cutoff" in row for row in blocker_sets)

    if int(c1_support_cases) >= 8:
        category = "v0703_minimal_explicit_death_certificate_restores_f3_causal_support"
    elif every_missing_death:
        category = "v0703_gap_requires_explicit_death_evidence_unavailable_at_cutoff"
    elif every_boundary_unavailable:
        category = "v0703_gap_requires_boundary_survival_evidence_unavailable_at_cutoff"
    elif every_after_cutoff:
        category = "v0703_gap_is_causal_confirmation_maturity_shortfall"
    else:
        category = "v0703_causal_certificate_gap_mixed_or_unresolved"

    return {
        "static_support_replication_ok": True,
        "c0_support_replication_ok": True,
        "gap_case_count_replication_ok": True,
        "c1_support_cases": int(c1_support_cases),
        "c1_restores_salvage_threshold": int(c1_support_cases) >= 8,
        "every_gap_realization_missing_explicit_death": every_missing_death,
        "every_gap_realization_boundary_survival_unavailable": every_boundary_unavailable,
        "every_gap_realization_proof_after_cutoff": every_after_cutoff,
        "primary_category": category,
    }
