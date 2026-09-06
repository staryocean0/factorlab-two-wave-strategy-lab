"""v0.6.1 audit-only helpers for unmatched identity decomposition.

These helpers do not alter the two-wave recognizer.  They only trace a frozen
v0.6.0 unmatched identity through pre-existing v0.5.2/v0.5.4 layers.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence

SCHEMA = "two_wave_unmatched_identity_decomposition@0.6.1"
NOMINAL_BAR_MINUTES = 5.0
SESSION_BOUNDARY_UTC_MINUTES = (90, 210, 300, 420)


def to_minutes(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() / 60.0


def attach_times(indices: Iterable[int], bars: Sequence[dict]) -> list[str]:
    out = []
    for value in indices:
        idx = int(value)
        if idx < 0 or idx >= len(bars):
            raise ValueError("occurrence index outside supplied bars")
        out.append(str(bars[idx]["timestamp"]))
    if len(out) != 5:
        raise ValueError("exactly five occurrence times required")
    return out


def alternating_kinds(phase: str) -> tuple[str, str, str, str, str]:
    if phase not in {"low", "high"}:
        raise ValueError("phase must be low or high")
    other = "high" if phase == "low" else "low"
    return (phase, other, phase, other, phase)


def canonicalize_evaluated_records(records: Iterable[dict], bars: Sequence[dict]) -> list[dict]:
    """Group all evaluated v0.5.4 records by raw financial identity.

    Qualification is retained as evidence and is not a grouping key.
    """
    groups: dict[tuple[str, tuple[int, ...]], list[dict]] = defaultdict(list)
    for record in records:
        phase = str(record["phase"])
        if phase not in {"low", "high"}:
            raise ValueError("phase must be low or high")
        raw = tuple(int(x) for x in record["five_occurrence_bars"])
        if len(raw) != 5 or any(b <= a for a, b in zip(raw, raw[1:])):
            raise ValueError("five strictly increasing raw occurrence bars required")
        groups[(phase, raw)].append(record)

    out = []
    for (phase, raw), members in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        reasons = sorted(
            {
                str(reason)
                for member in members
                for reason in member.get("scale_rejection_reasons", [])
            }
        )
        levels = sorted(
            {
                int(member["birth_scale_level"])
                for member in members
                if member.get("birth_scale_level") is not None
            }
        )
        out.append(
            {
                "schema": SCHEMA,
                "phase": phase,
                "five_occurrence_bars": list(raw),
                "five_occurrence_times": attach_times(raw, bars),
                "member_record_ids": sorted(str(m["record_id"]) for m in members),
                "member_count": len(members),
                "qualified_any": any(bool(m.get("scale_qualified")) for m in members),
                "rejection_reasons_union": reasons,
                "birth_scale_levels": levels,
                "trade_authority": False,
            }
        )
    return out


def canonicalize_tuple_births(tuple_births: Iterable[object], bars: Sequence[dict]) -> list[dict]:
    """Group exact-ridge tuple births by filtered five-anchor identity."""
    groups: dict[tuple[str, tuple[int, ...]], list[object]] = defaultdict(list)
    for birth in tuple_births:
        nodes = tuple(getattr(birth, "nodes"))
        if len(nodes) != 5:
            raise ValueError("tuple birth must contain five nodes")
        phase = str(nodes[0].node.kind)
        filtered = tuple(int(x) for x in getattr(birth, "occurrence_indices"))
        if len(filtered) != 5 or any(b <= a for a, b in zip(filtered, filtered[1:])):
            raise ValueError("five strictly increasing filtered occurrence bars required")
        groups[(phase, filtered)].append(birth)

    out = []
    for (phase, filtered), members in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        out.append(
            {
                "schema": SCHEMA,
                "phase": phase,
                "five_filtered_occurrence_bars": list(filtered),
                "five_filtered_occurrence_times": attach_times(filtered, bars),
                "member_event_ids": sorted(str(getattr(m, "event_id")) for m in members),
                "member_count": len(members),
                "birth_scale_levels": sorted({int(getattr(m, "level")) for m in members}),
                "trade_authority": False,
            }
        )
    return out


def anchor_edge(
    a: dict,
    b: dict,
    *,
    time_field: str,
    nominal_bar_minutes: float = NOMINAL_BAR_MINUTES,
    require_phase: bool = True,
) -> dict | None:
    if nominal_bar_minutes <= 0:
        raise ValueError("positive nominal bar width required")
    if require_phase and a["phase"] != b["phase"]:
        return None
    ta, tb = a.get(time_field), b.get(time_field)
    if ta is None or tb is None or len(ta) != 5 or len(tb) != 5:
        raise ValueError(f"five times required in {time_field}")
    deltas = [abs(to_minutes(x) - to_minutes(y)) for x, y in zip(ta, tb)]
    if max(deltas) > nominal_bar_minutes:
        return None
    return {
        "max_delta_minutes": max(deltas),
        "sum_delta_minutes": sum(deltas),
        "deltas_minutes": deltas,
    }


@dataclass(frozen=True)
class EdgeGraph:
    a_edges: tuple[tuple[int, ...], ...]
    b_edges: tuple[tuple[int, ...], ...]
    mutual_unique_matches: tuple[tuple[int, int], ...]

    def mutual_partner_a(self, idx: int) -> int | None:
        for i, j in self.mutual_unique_matches:
            if i == idx:
                return j
        return None


def build_edge_graph(
    events_a: Sequence[dict],
    events_b: Sequence[dict],
    *,
    time_field: str,
    nominal_bar_minutes: float = NOMINAL_BAR_MINUTES,
    require_phase: bool = True,
) -> EdgeGraph:
    """Build the exact strict-edge graph with a first-anchor locality index.

    Any legal five-anchor edge must already satisfy |e0_a-e0_b| <= the nominal
    bar width. Restricting candidate enumeration by that necessary condition is
    exactly equivalent to the quadratic definition, while keeping the 36k--38k
    evaluated/tuple layers tractable.
    """
    if nominal_bar_minutes <= 0:
        raise ValueError("positive nominal bar width required")

    a_vectors = []
    for event in events_a:
        values = event.get(time_field)
        if values is None or len(values) != 5:
            raise ValueError(f"five times required in {time_field}")
        a_vectors.append(tuple(to_minutes(x) for x in values))
    b_vectors = []
    for event in events_b:
        values = event.get(time_field)
        if values is None or len(values) != 5:
            raise ValueError(f"five times required in {time_field}")
        b_vectors.append(tuple(to_minutes(x) for x in values))

    ordered_b = sorted((vec[0], j) for j, vec in enumerate(b_vectors))
    b_first = [row[0] for row in ordered_b]
    a_edges: list[list[int]] = [[] for _ in events_a]
    b_edges: list[list[int]] = [[] for _ in events_b]

    for i, (a, avec) in enumerate(zip(events_a, a_vectors)):
        lo = bisect_left(b_first, avec[0] - nominal_bar_minutes)
        hi = bisect_right(b_first, avec[0] + nominal_bar_minutes)
        for _, j in ordered_b[lo:hi]:
            b = events_b[j]
            if require_phase and a["phase"] != b["phase"]:
                continue
            bvec = b_vectors[j]
            if all(abs(x - y) <= nominal_bar_minutes for x, y in zip(avec, bvec)):
                a_edges[i].append(j)
                b_edges[j].append(i)

    matches = []
    for i, js in enumerate(a_edges):
        if len(js) == 1:
            j = js[0]
            if len(b_edges[j]) == 1:
                matches.append((i, j))
    return EdgeGraph(
        a_edges=tuple(tuple(x) for x in a_edges),
        b_edges=tuple(tuple(x) for x in b_edges),
        mutual_unique_matches=tuple(matches),
    )


def level_anchor_survival(
    main_filtered_times: Sequence[object],
    phase: str,
    other_nodes: Sequence[object],
    other_bars: Sequence[dict],
    nominal_bar_minutes: float = NOMINAL_BAR_MINUTES,
) -> dict:
    if len(main_filtered_times) != 5:
        raise ValueError("five main filtered times required")
    kinds = alternating_kinds(phase)
    counts = []
    candidates = []
    for target_time, kind in zip(main_filtered_times, kinds):
        target = to_minutes(target_time)
        rows = []
        for node in other_nodes:
            if str(getattr(node, "kind")) != kind:
                continue
            occurrence = int(getattr(node, "occurrence_index"))
            if occurrence < 0 or occurrence >= len(other_bars):
                raise ValueError("other extremum occurrence outside bars")
            delta = abs(target - to_minutes(other_bars[occurrence]["timestamp"]))
            if delta <= nominal_bar_minutes:
                rows.append(
                    {
                        "occurrence_bar": occurrence,
                        "occurrence_time": str(other_bars[occurrence]["timestamp"]),
                        "delta_minutes": delta,
                    }
                )
        counts.append(len(rows))
        candidates.append(rows)
    return {
        "candidate_counts": counts,
        "unique_anchor_count": sum(x == 1 for x in counts),
        "missing_anchor_count": sum(x == 0 for x in counts),
        "ambiguous_anchor_count": sum(x > 1 for x in counts),
        "all_unique": all(x == 1 for x in counts),
        "candidates": candidates,
    }


def any_level_anchor_survival(
    main_filtered_times: Sequence[object],
    phase: str,
    nodes_by_level: Sequence[Sequence[object]],
    other_bars: Sequence[dict],
    nominal_bar_minutes: float = NOMINAL_BAR_MINUTES,
) -> dict:
    levels = []
    max_unique = 0
    per_level = []
    for level, nodes in enumerate(nodes_by_level):
        row = level_anchor_survival(
            main_filtered_times,
            phase,
            nodes,
            other_bars,
            nominal_bar_minutes,
        )
        per_level.append(
            {
                "level": level,
                "candidate_counts": row["candidate_counts"],
                "unique_anchor_count": row["unique_anchor_count"],
                "missing_anchor_count": row["missing_anchor_count"],
                "ambiguous_anchor_count": row["ambiguous_anchor_count"],
                "all_unique": row["all_unique"],
            }
        )
        max_unique = max(max_unique, int(row["unique_anchor_count"]))
        if row["all_unique"]:
            levels.append(level)
    return {
        "all_unique_levels": levels,
        "max_unique_anchor_count": max_unique,
        "per_level": per_level,
    }


def session_boundary_overlay(
    raw_times: Sequence[object],
    filtered_times: Sequence[object],
    nominal_bar_minutes: float = NOMINAL_BAR_MINUTES,
) -> dict:
    hits = []
    for source, values in (("raw", raw_times), ("filtered", filtered_times)):
        for pos, value in enumerate(values):
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            minute_of_day = dt.hour * 60 + dt.minute + dt.second / 60.0
            for boundary in SESSION_BOUNDARY_UTC_MINUTES:
                delta = abs(minute_of_day - boundary)
                if delta <= nominal_bar_minutes:
                    hits.append(
                        {
                            "source": source,
                            "anchor_position": pos,
                            "boundary_utc_minute": boundary,
                            "delta_minutes": delta,
                        }
                    )
    return {"boundary_tagged": bool(hits), "hits": hits}


def local_envelope_overlap_diagnostic(main_event: dict, other_events: Sequence[dict]) -> dict:
    main_times = main_event["five_occurrence_times"]
    lo, hi = to_minutes(main_times[0]), to_minutes(main_times[-1])
    rows = []
    for j, other in enumerate(other_events):
        if other["phase"] != main_event["phase"]:
            continue
        times = other["five_occurrence_times"]
        olo, ohi = to_minutes(times[0]), to_minutes(times[-1])
        if max(lo, olo) > min(hi, ohi):
            continue
        deltas = [abs(to_minutes(a) - to_minutes(b)) for a, b in zip(main_times, times)]
        rows.append((j, max(deltas)))
    if not rows:
        return {
            "candidate_count": 0,
            "minimum_max_delta_minutes": None,
            "minimum_tie_count": 0,
        }
    minimum = min(value for _, value in rows)
    return {
        "candidate_count": len(rows),
        "minimum_max_delta_minutes": minimum,
        "minimum_tie_count": sum(value == minimum for _, value in rows),
    }
