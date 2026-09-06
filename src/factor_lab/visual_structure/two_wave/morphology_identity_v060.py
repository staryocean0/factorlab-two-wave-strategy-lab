"""v0.6.0 morphology identity audit helpers.

This module deliberately separates a *qualified two-wave financial identity*
from any later non-overlap packing decision. No outcomes, returns or trading
logic are present. Cross-view helpers are audit-only and must never be used by
a single-view recognizer.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from typing import Iterable, Sequence

SCHEMA = "two_wave_morphology_identity@0.6.0"


def _stable_id(namespace: str, payload: object) -> str:
    raw = json.dumps([namespace, payload], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{namespace}_{hashlib.sha256(raw.encode()).hexdigest()[:20]}"


def _five_bars(record: dict) -> tuple[int, int, int, int, int]:
    bars = tuple(int(x) for x in record["five_occurrence_bars"])
    if len(bars) != 5 or any(b <= a for a, b in zip(bars, bars[1:])):
        raise ValueError("five strictly increasing occurrence bars required")
    return bars  # type: ignore[return-value]


def _d1(record: dict):
    if "D1" in record:
        return record["D1"]
    dv = record.get("direction_versions")
    return dv.get("D1") if isinstance(dv, dict) else record.get("classification")


def canonicalize_qualified_records(records: Iterable[dict]) -> list[dict]:
    """Collapse only exact same-financial-event duplicates across scale evidence.

    Financial identity is `(phase, five raw occurrence bars)`. Birth scale is
    evidence about that identity, not part of the identity. Different rolling
    two-wave windows remain separate even when their intervals overlap.
    """
    groups: dict[tuple[str, tuple[int, ...]], list[dict]] = defaultdict(list)
    for record in records:
        if not bool(record.get("scale_qualified")):
            continue
        phase = str(record["phase"])
        if phase not in {"low", "high"}:
            raise ValueError("phase must be low or high")
        bars = _five_bars(record)
        groups[(phase, bars)].append(record)

    out = []
    for (phase, bars), members in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        d1s = {_d1(r) for r in members if _d1(r) is not None}
        if len(d1s) > 1:
            raise ValueError("same financial identity has conflicting D1 labels")
        phase_steps = {
            tuple(round(float(x), 12) for x in r["phase_steps_in_amplitude_units"])
            for r in members
            if r.get("phase_steps_in_amplitude_units") is not None
        }
        # v0.5.5 diagnostic artifacts expose s0/s1/s2 instead of the source list.
        diag_steps = {
            (
                round(float(r["s0_same_phase_first"]), 12),
                round(float(r["s1_same_phase_second"]), 12),
                round(float(r["s2_opposite_envelope"]), 12),
            )
            for r in members
            if all(
                k in r
                for k in (
                    "s0_same_phase_first",
                    "s1_same_phase_second",
                    "s2_opposite_envelope",
                )
            )
        }
        if len(phase_steps) > 1 or len(diag_steps) > 1:
            raise ValueError("same financial identity has conflicting direction geometry")
        record_ids = sorted(str(r["record_id"]) for r in members)
        selected_ids = sorted(str(r["record_id"]) for r in members if bool(r.get("selected")))
        levels = sorted(
            {
                int(r["birth_scale_level"])
                for r in members
                if r.get("birth_scale_level") is not None
            }
        )
        out.append(
            {
                "schema": SCHEMA,
                "canonical_identity_id": _stable_id(
                    "two_wave_financial_identity_v060", [phase, list(bars)]
                ),
                "phase": phase,
                "five_occurrence_bars": list(bars),
                "start_bar": bars[0],
                "end_bar": bars[-1],
                "member_record_ids": record_ids,
                "member_count": len(members),
                "birth_scale_levels": levels,
                "selected_member_ids": selected_ids,
                "selected_any": bool(selected_ids),
                "D1": next(iter(d1s)) if d1s else None,
                "trade_authority": False,
            }
        )
    return out


def causal_publish_qualified_identities(records: Iterable[dict]) -> dict:
    """Publish immutable financial identities plus append-only scale evidence.

    The first confirmed qualified member publishes the identity. Later members
    with the same `(phase, five_occurrence_bars)` add evidence records only; the
    already-published identity event is never rewritten.
    """
    qualified = [r for r in records if bool(r.get("scale_qualified"))]
    for r in qualified:
        if r.get("confirmation_bar") is None:
            raise ValueError("confirmation_bar required for causal publication")
    ordered = sorted(
        qualified,
        key=lambda r: (
            int(r["confirmation_bar"]),
            int(r.get("birth_scale_level", 10**9)),
            _five_bars(r)[0],
            _five_bars(r)[-1],
            str(r["record_id"]),
        ),
    )
    published: dict[tuple[str, tuple[int, ...]], dict] = {}
    identities: list[dict] = []
    evidence: list[dict] = []
    geometry_by_key: dict[tuple[str, tuple[int, ...]], tuple | None] = {}
    d1_by_key: dict[tuple[str, tuple[int, ...]], object] = {}
    for r in ordered:
        phase = str(r["phase"])
        bars = _five_bars(r)
        key = (phase, bars)
        identity_id = _stable_id("two_wave_financial_identity_v060", [phase, list(bars)])
        d1 = _d1(r)
        if r.get("phase_steps_in_amplitude_units") is not None:
            geom = tuple(round(float(x), 12) for x in r["phase_steps_in_amplitude_units"])
        elif all(
            k in r
            for k in (
                "s0_same_phase_first",
                "s1_same_phase_second",
                "s2_opposite_envelope",
            )
        ):
            geom = (
                round(float(r["s0_same_phase_first"]), 12),
                round(float(r["s1_same_phase_second"]), 12),
                round(float(r["s2_opposite_envelope"]), 12),
            )
        else:
            geom = None
        if key in published:
            if d1_by_key[key] is not None and d1 is not None and d1_by_key[key] != d1:
                raise ValueError("same financial identity has conflicting D1 labels")
            if geometry_by_key[key] is not None and geom is not None and geometry_by_key[key] != geom:
                raise ValueError("same financial identity has conflicting direction geometry")
        else:
            event = {
                "schema": SCHEMA,
                "canonical_identity_id": identity_id,
                "phase": phase,
                "five_occurrence_bars": list(bars),
                "start_bar": bars[0],
                "end_bar": bars[-1],
                "first_record_id": str(r["record_id"]),
                "confirmation_bar": int(r["confirmation_bar"]),
                "D1": d1,
                "trade_authority": False,
            }
            published[key] = event
            identities.append(event)
            geometry_by_key[key] = geom
            d1_by_key[key] = d1
        evidence.append(
            {
                "schema": SCHEMA,
                "canonical_identity_id": identity_id,
                "record_id": str(r["record_id"]),
                "confirmation_bar": int(r["confirmation_bar"]),
                "birth_scale_level": (
                    int(r["birth_scale_level"])
                    if r.get("birth_scale_level") is not None
                    else None
                ),
                "selected_legacy": bool(r.get("selected")),
                "trade_authority": False,
            }
        )
    return {"identity_events": identities, "evidence_events": evidence}


def _to_minutes(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("Z", "+00:00")
    return datetime.fromisoformat(text).timestamp() / 60.0


def strict_anchor_edge(a: dict, b: dict, nominal_bar_minutes: float = 5.0) -> dict | None:
    """Audit-only same-event edge using one nominal-bar locality, no fitted tolerance."""
    if nominal_bar_minutes <= 0:
        raise ValueError("positive nominal bar width required")
    if a["phase"] != b["phase"]:
        return None
    ta = a.get("five_occurrence_times")
    tb = b.get("five_occurrence_times")
    if ta is None or tb is None or len(ta) != 5 or len(tb) != 5:
        raise ValueError("five occurrence times required for cross-view audit")
    deltas = [abs(_to_minutes(x) - _to_minutes(y)) for x, y in zip(ta, tb)]
    if max(deltas) > nominal_bar_minutes:
        return None
    return {
        "max_delta_minutes": max(deltas),
        "sum_delta_minutes": sum(deltas),
        "deltas_minutes": deltas,
    }


@dataclass(frozen=True)
class StrictIdentityAudit:
    matches: tuple[tuple[int, int], ...]
    ambiguous_a: tuple[int, ...]
    ambiguous_b: tuple[int, ...]
    unmatched_a: tuple[int, ...]
    unmatched_b: tuple[int, ...]


def mutual_unique_strict_matches(
    events_a: Sequence[dict],
    events_b: Sequence[dict],
    nominal_bar_minutes: float = 5.0,
) -> StrictIdentityAudit:
    """Return only mutual-unique strict event matches; never resolves ambiguity post hoc."""
    a_edges: dict[int, list[int]] = defaultdict(list)
    b_edges: dict[int, list[int]] = defaultdict(list)
    for i, a in enumerate(events_a):
        for j, b in enumerate(events_b):
            if strict_anchor_edge(a, b, nominal_bar_minutes) is not None:
                a_edges[i].append(j)
                b_edges[j].append(i)
    matches = []
    for i, js in a_edges.items():
        if len(js) != 1:
            continue
        j = js[0]
        if len(b_edges[j]) == 1:
            matches.append((i, j))
    matched_a = {i for i, _ in matches}
    matched_b = {j for _, j in matches}
    ambiguous_a = tuple(sorted(i for i, js in a_edges.items() if len(js) > 1))
    ambiguous_b = tuple(sorted(j for j, is_ in b_edges.items() if len(is_) > 1))
    unmatched_a = tuple(
        sorted(i for i in range(len(events_a)) if i not in matched_a and i not in ambiguous_a)
    )
    unmatched_b = tuple(
        sorted(j for j in range(len(events_b)) if j not in matched_b and j not in ambiguous_b)
    )
    return StrictIdentityAudit(
        tuple(sorted(matches)),
        ambiguous_a,
        ambiguous_b,
        unmatched_a,
        unmatched_b,
    )
