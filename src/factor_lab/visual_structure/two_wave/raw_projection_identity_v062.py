"""v0.6.2 audit-only helpers for raw-projection financial identity.

No recognizer behavior is changed here.  The module reproduces the frozen
v0.5.1/v0.5.2 projection, exposes its phase windows for audit, and provides
read-only cross-view / 1m diagnostics.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence

import numpy as np

from .characteristic_scale_v051 import project_event_to_raw

SCHEMA = "two_wave_raw_projection_identity_audit@0.6.2"
NOMINAL_BAR_MINUTES = 5.0


def to_minutes(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() / 60.0


def strict_time_tuple_match(
    phase_a: str,
    times_a: Sequence[object],
    phase_b: str,
    times_b: Sequence[object],
    nominal_bar_minutes: float = NOMINAL_BAR_MINUTES,
) -> bool:
    if phase_a != phase_b:
        return False
    if len(times_a) != 5 or len(times_b) != 5:
        raise ValueError("exactly five times required")
    return all(
        abs(to_minutes(a) - to_minutes(b)) <= nominal_bar_minutes
        for a, b in zip(times_a, times_b)
    )


def _last_argextreme(values: np.ndarray, kind: str) -> tuple[int, float, int]:
    if values.ndim != 1 or not len(values):
        raise ValueError("nonempty one-dimensional values required")
    if kind == "high":
        target = float(np.max(values))
    elif kind == "low":
        target = float(np.min(values))
    else:
        raise ValueError("kind must be high or low")
    positions = np.flatnonzero(values == target)
    if not len(positions):
        raise ValueError("extreme position missing")
    return int(positions[-1]), target, int(len(positions))


def audit_projection_event(event, bars: Sequence[dict], closes: np.ndarray | None = None) -> dict:
    """Expose the exact frozen projection windows and assert output equivalence."""
    frozen = project_event_to_raw(event, list(bars), closes)
    if not frozen.get("valid"):
        return {
            "schema": SCHEMA,
            "event_id": str(event.event_id),
            "valid": False,
            "reason": frozen.get("reason"),
            "raw_occurrence_bars": None,
            "windows": [],
        }

    filtered = tuple(int(x) for x in event.feature.occurrence_indices)
    member_confirmation = int(event.feature.confirmation_index)
    if closes is None:
        closes = np.asarray([float(bar["close"]) for bar in bars], dtype=float)
    if closes.ndim != 1 or len(closes) != len(bars):
        raise ValueError("closes must align one-to-one with bars")

    kinds = tuple(point.kind for point in event.feature.candidate.extrema)
    left = max(0, 2 * filtered[0] - filtered[1])
    uppers = (
        filtered[1] - 1,
        filtered[2] - 1,
        filtered[3] - 1,
        filtered[4] - 1,
        member_confirmation,
    )
    selected: list[int] = []
    windows: list[dict] = []
    lo = left
    for ordinal, (kind, hi0) in enumerate(zip(kinds, uppers)):
        hi = min(int(hi0), member_confirmation)
        if lo > hi:
            raise AssertionError("frozen valid projection cannot have empty reconstructed window")
        rel, price, tie_count = _last_argextreme(closes[lo : hi + 1], kind)
        occurrence = int(lo + rel)
        selected.append(occurrence)
        lo_time = str(bars[lo]["timestamp"])
        hi_time = str(bars[hi]["timestamp"])
        occurrence_time = str(bars[occurrence]["timestamp"])
        filtered_time = str(bars[filtered[ordinal]]["timestamp"])
        windows.append(
            {
                "ordinal": ordinal,
                "kind": kind,
                "filtered_occurrence_bar": filtered[ordinal],
                "filtered_occurrence_time": filtered_time,
                "lower_bar": lo,
                "lower_time": lo_time,
                "upper_bar": hi,
                "upper_time": hi_time,
                "selected_raw_bar": occurrence,
                "selected_raw_time": occurrence_time,
                "selected_raw_close": price,
                "exact_extreme_tie_count": tie_count,
                "distance_from_lower_bars": occurrence - lo,
                "distance_from_upper_bars": hi - occurrence,
                "distance_from_lower_minutes": to_minutes(occurrence_time) - to_minutes(lo_time),
                "distance_from_upper_minutes": to_minutes(hi_time) - to_minutes(occurrence_time),
                "selected_minus_filtered_minutes": to_minutes(occurrence_time) - to_minutes(filtered_time),
                "tail_extension_from_filtered_e4_bars": (
                    member_confirmation - filtered[4] if ordinal == 4 else None
                ),
                "tail_extension_from_filtered_e4_minutes": (
                    to_minutes(bars[member_confirmation]["timestamp"]) - to_minutes(bars[filtered[4]]["timestamp"])
                    if ordinal == 4
                    else None
                ),
            }
        )
        lo = occurrence + 1

    frozen_selected = tuple(int(x) for x in frozen["raw_occurrence_indices"])
    if tuple(selected) != frozen_selected:
        raise AssertionError(
            f"v0.6.2 audit reconstruction drift: {tuple(selected)} != {frozen_selected}"
        )
    return {
        "schema": SCHEMA,
        "event_id": str(event.event_id),
        "valid": True,
        "reason": None,
        "raw_occurrence_bars": list(selected),
        "raw_occurrence_times": [str(bars[i]["timestamp"]) for i in selected],
        "windows": windows,
    }


def changed_ordinals(raw_tuples: Iterable[Sequence[int]]) -> list[int]:
    rows = [tuple(int(x) for x in row) for row in raw_tuples]
    if len(rows) <= 1:
        return []
    if any(len(row) != 5 for row in rows):
        raise ValueError("five raw anchors required")
    return [i for i in range(5) if len({row[i] for row in rows}) > 1]


def summarize_projection_group(member_rows: Sequence[dict]) -> dict:
    """Summarize all tuple-birth projection evidence without choosing a best member."""
    if not member_rows:
        raise ValueError("projection members required")
    valid = [row for row in member_rows if bool(row.get("projection_valid"))]
    invalid = [row for row in member_rows if not bool(row.get("projection_valid"))]
    raw_tuples = {
        tuple(int(x) for x in row["raw_occurrence_bars"])
        for row in valid
        if row.get("raw_occurrence_bars") is not None
    }
    if not valid:
        status = "no_valid_projection"
    elif len(raw_tuples) == 1:
        status = "single_valued_projection"
    else:
        status = "multi_valued_projection"
    invalid_reasons = Counter(str(row.get("projection_reason")) for row in invalid)
    levels = sorted({int(row["birth_level"]) for row in member_rows})
    confirmations = sorted({int(row["birth_confirmation_bar"]) for row in member_rows})
    return {
        "schema": SCHEMA,
        "status": status,
        "member_count": len(member_rows),
        "projection_valid_count": len(valid),
        "projection_invalid_count": len(invalid),
        "projection_invalid_reasons": dict(sorted(invalid_reasons.items())),
        "distinct_valid_raw_identity_count": len(raw_tuples),
        "valid_raw_identities": [list(x) for x in sorted(raw_tuples)],
        "changed_raw_ordinals": changed_ordinals(raw_tuples),
        "birth_levels": levels,
        "birth_confirmation_bars": confirmations,
    }


def earliest_valid_member(member_rows: Sequence[dict]) -> dict | None:
    valid = [row for row in member_rows if bool(row.get("projection_valid"))]
    if not valid:
        return None
    return min(
        valid,
        key=lambda row: (
            int(row["birth_confirmation_bar"]),
            int(row["birth_level"]),
            str(row["event_id"]),
        ),
    )


@dataclass(frozen=True)
class CanonicalPathIndex:
    timestamps: tuple[str, ...]
    minutes: np.ndarray
    closes: np.ndarray

    @classmethod
    def from_bars(cls, bars: Sequence[dict]) -> "CanonicalPathIndex":
        timestamps = tuple(str(row["timestamp"]) for row in bars)
        minutes = np.asarray([to_minutes(x) for x in timestamps], dtype=float)
        closes = np.asarray([float(row["close"]) for row in bars], dtype=float)
        if len(minutes) != len(closes) or not len(minutes):
            raise ValueError("canonical path bars required")
        if np.any(np.diff(minutes) <= 0):
            raise ValueError("canonical path timestamps must increase strictly")
        return cls(timestamps=timestamps, minutes=minutes, closes=closes)

    def project_window(self, lower_time: object, upper_time: object, kind: str) -> dict | None:
        lo_t, hi_t = to_minutes(lower_time), to_minutes(upper_time)
        if lo_t > hi_t:
            raise ValueError("lower time after upper time")
        lo = int(np.searchsorted(self.minutes, lo_t, side="left"))
        hi_exclusive = int(np.searchsorted(self.minutes, hi_t, side="right"))
        if lo >= hi_exclusive:
            return None
        rel, price, tie_count = _last_argextreme(self.closes[lo:hi_exclusive], kind)
        idx = lo + rel
        return {
            "occurrence_index": idx,
            "occurrence_time": self.timestamps[idx],
            "close": price,
            "tie_count": tie_count,
        }


def one_minute_projection_from_windows(windows: Sequence[dict], index: CanonicalPathIndex) -> dict:
    if len(windows) != 5:
        raise ValueError("five windows required")
    rows = []
    for window in windows:
        projected = index.project_window(window["lower_time"], window["upper_time"], window["kind"])
        if projected is None:
            return {"available": False, "rows": rows, "times": None}
        rows.append(projected)
    return {
        "available": True,
        "rows": rows,
        "times": [row["occurrence_time"] for row in rows],
    }


def raw_pair_displacement(times_a: Sequence[object], times_b: Sequence[object]) -> dict:
    if len(times_a) != 5 or len(times_b) != 5:
        raise ValueError("five raw times required")
    deltas = [abs(to_minutes(a) - to_minutes(b)) for a, b in zip(times_a, times_b)]
    displaced = [i for i, delta in enumerate(deltas) if delta > NOMINAL_BAR_MINUTES]
    first = displaced[0] if displaced else None
    suffix = bool(displaced) and displaced == list(range(first, 5))
    return {
        "deltas_minutes": deltas,
        "first_displaced_ordinal": first,
        "displaced_ordinal_count": len(displaced),
        "displaced_ordinals": displaced,
        "displaced_is_suffix": suffix,
        "strict_match": not displaced,
    }


def _inside(value: object, lower: object, upper: object) -> bool:
    x, lo, hi = to_minutes(value), to_minutes(lower), to_minutes(upper)
    return lo <= x <= hi


def paired_window_diagnostics(windows_a: Sequence[dict], windows_b: Sequence[dict]) -> dict:
    if len(windows_a) != 5 or len(windows_b) != 5:
        raise ValueError("five windows required")
    rows = []
    for a, b in zip(windows_a, windows_b):
        if int(a["ordinal"]) != int(b["ordinal"]):
            raise ValueError("window ordinals must align")
        rows.append(
            {
                "ordinal": int(a["ordinal"]),
                "lower_bound_delta_minutes": abs(to_minutes(a["lower_time"]) - to_minutes(b["lower_time"])),
                "upper_bound_delta_minutes": abs(to_minutes(a["upper_time"]) - to_minutes(b["upper_time"])),
                "a_selected_inside_b_window": _inside(a["selected_raw_time"], b["lower_time"], b["upper_time"]),
                "b_selected_inside_a_window": _inside(b["selected_raw_time"], a["lower_time"], a["upper_time"]),
                "either_exact_tie": int(a["exact_extreme_tie_count"]) > 1 or int(b["exact_extreme_tie_count"]) > 1,
                "a_exact_tie_count": int(a["exact_extreme_tie_count"]),
                "b_exact_tie_count": int(b["exact_extreme_tie_count"]),
            }
        )
    return {"rows": rows, "any_exact_tie": any(row["either_exact_tie"] for row in rows)}
