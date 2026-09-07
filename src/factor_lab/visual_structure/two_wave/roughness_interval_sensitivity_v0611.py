"""v0.6.11 audit-only endpoint/interval-sensitivity helpers.

The registered candidate is a single-view inward erosion ensemble.  Common
support uses counterpart information and is explicitly audit-only.  No
qualification threshold or recognizer behavior is defined here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Sequence

import numpy as np

SCHEMA = "two_wave_roughness_interval_sensitivity@0.6.11"
MAX_EROSION_MINUTES = 4


def _minute(value: object) -> int:
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, float):
        if not float(value).is_integer():
            raise ValueError("minute coordinate must be integral")
        return int(value)
    return int(round(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() / 60.0))


@dataclass(frozen=True)
class MinutePathIndex:
    minutes: np.ndarray
    closes: np.ndarray

    def __post_init__(self) -> None:
        mm = np.asarray(self.minutes)
        yy = np.asarray(self.closes, dtype=float)
        if mm.ndim != 1 or yy.ndim != 1 or len(mm) != len(yy) or len(mm) < 2:
            raise ValueError("aligned one-dimensional minute/close arrays required")
        if not np.isfinite(yy).all():
            raise ValueError("finite closes required")
        if any(int(b) <= int(a) for a, b in zip(mm, mm[1:])):
            raise ValueError("minutes must increase strictly")


def path_roughness(values: Sequence[float]) -> dict:
    y = np.asarray(values, dtype=float)
    if y.ndim != 1 or len(y) < 2 or not np.isfinite(y).all():
        raise ValueError("at least two finite path values required")
    changes = np.abs(np.diff(y))
    tv = float(changes.sum())
    displacement = abs(float(y[-1] - y[0]))
    roughness = math.log(tv / displacement) if tv > 0 and displacement > 0 else None
    return {
        "total_variation": tv,
        "net_displacement": displacement,
        "roughness": roughness,
        "rows": int(len(y)),
    }


def exact_interval(index: MinutePathIndex, start: object, end: object) -> tuple[np.ndarray | None, str | None]:
    lo_t, hi_t = _minute(start), _minute(end)
    if lo_t >= hi_t:
        return None, "interval_collapse"
    mm = np.asarray(index.minutes)
    lo = int(np.searchsorted(mm, lo_t, side="left"))
    hi = int(np.searchsorted(mm, hi_t, side="left"))
    if lo >= len(mm) or int(mm[lo]) != lo_t:
        return None, "missing_shifted_start"
    if hi >= len(mm) or int(mm[hi]) != hi_t:
        return None, "missing_shifted_end"
    if hi <= lo:
        return None, "interval_collapse"
    return np.asarray(index.closes[lo : hi + 1], dtype=float), None


def interval_roughness(index: MinutePathIndex, start: object, end: object) -> dict:
    y, reason = exact_interval(index, start, end)
    if y is None:
        return {"defined": False, "reason": reason, "stats": None}
    stats = path_roughness(y)
    if stats["total_variation"] <= 0:
        return {"defined": False, "reason": "zero_total_variation", "stats": stats}
    if stats["net_displacement"] <= 0:
        return {"defined": False, "reason": "zero_net_displacement", "stats": stats}
    return {"defined": True, "reason": None, "stats": stats}


def erosion_roughness_ensemble(
    index: MinutePathIndex,
    start: object,
    end: object,
    *,
    max_erosion_minutes: int = MAX_EROSION_MINUTES,
) -> dict:
    """Registered single-view candidate; uses no counterpart information."""
    if max_erosion_minutes != MAX_EROSION_MINUTES:
        raise ValueError("v0.6.11 freezes max erosion at four minutes")
    t0, t1 = _minute(start), _minute(end)
    cells = []
    values = []
    reasons: dict[str, int] = {}
    for s in range(MAX_EROSION_MINUTES + 1):
        for e in range(MAX_EROSION_MINUTES + 1):
            a, b = t0 + s, t1 - e
            row = interval_roughness(index, a, b)
            value = row["stats"]["roughness"] if row["defined"] else None
            cells.append({
                "start_erosion_minutes": s,
                "end_erosion_minutes": e,
                "start_minute": a,
                "end_minute": b,
                "defined": row["defined"],
                "reason": row["reason"],
                "roughness": value,
            })
            if value is not None:
                values.append(float(value))
            elif row["reason"] is not None:
                reasons[str(row["reason"])] = reasons.get(str(row["reason"]), 0) + 1
    return {
        "schema": SCHEMA,
        "candidate": "single_view_inward_erosion_roughness_ensemble",
        "cells": cells,
        "attempted_count": 25,
        "defined_count": len(values),
        "undefined_reasons": dict(sorted(reasons.items())),
        "erosion_roughness_median": float(np.median(values)) if values else None,
        "erosion_roughness_range": float(max(values) - min(values)) if values else None,
        "future_outcome_used": False,
        "trade_authority": False,
    }


def pair_roughness_decomposition(stats_a: dict, stats_b: dict) -> dict:
    for row in (stats_a, stats_b):
        if row.get("roughness") is None or row.get("total_variation", 0) <= 0 or row.get("net_displacement", 0) <= 0:
            raise ValueError("two defined positive roughness-stat rows required")
    delta_r = float(stats_a["roughness"] - stats_b["roughness"])
    delta_log_tv = math.log(float(stats_a["total_variation"])) - math.log(float(stats_b["total_variation"]))
    delta_log_d = math.log(float(stats_a["net_displacement"])) - math.log(float(stats_b["net_displacement"]))
    error = delta_r - (delta_log_tv - delta_log_d)
    return {
        "delta_roughness": delta_r,
        "delta_log_total_variation": delta_log_tv,
        "delta_log_net_displacement": delta_log_d,
        "identity_error": error,
    }


def common_support_oracle(
    index: MinutePathIndex,
    start_a: object,
    end_a: object,
    start_b: object,
    end_b: object,
) -> dict:
    """Audit-only counterpart-dependent oracle. Never the registered candidate."""
    start = max(_minute(start_a), _minute(start_b))
    end = min(_minute(end_a), _minute(end_b))
    out = interval_roughness(index, start, end)
    return {
        "schema": SCHEMA,
        "audit_only": True,
        "uses_counterpart_information": True,
        "common_start_minute": start,
        "common_end_minute": end,
        "defined": out["defined"],
        "reason": out["reason"],
        "stats": out["stats"],
        "trade_authority": False,
    }


def boundary_sliver_diagnostics(index: MinutePathIndex, start: object, end: object) -> dict:
    t0, t1 = _minute(start), _minute(end)
    original = interval_roughness(index, t0, t1)
    left = interval_roughness(index, t0 + 4, t1)
    right = interval_roughness(index, t0, t1 - 4)
    both = interval_roughness(index, t0 + 4, t1 - 4)

    def compact(row: dict) -> dict:
        if row["stats"] is None:
            return {"defined": False, "reason": row["reason"], "roughness": None, "tv": None, "displacement": None}
        return {
            "defined": row["defined"],
            "reason": row["reason"],
            "roughness": row["stats"]["roughness"],
            "tv": row["stats"]["total_variation"],
            "displacement": row["stats"]["net_displacement"],
        }

    rows = {"original": compact(original), "left4": compact(left), "right4": compact(right), "both4": compact(both)}
    orig = rows["original"]
    for name in ("left4", "right4", "both4"):
        row = rows[name]
        if orig["tv"] is not None and orig["tv"] > 0 and row["tv"] is not None:
            row["removed_tv_fraction"] = float((orig["tv"] - row["tv"]) / orig["tv"])
        else:
            row["removed_tv_fraction"] = None
        if orig["displacement"] is not None and row["displacement"] is not None:
            row["displacement_change"] = float(row["displacement"] - orig["displacement"])
        else:
            row["displacement_change"] = None
    return {"schema": SCHEMA, **rows, "future_outcome_used": False, "trade_authority": False}
