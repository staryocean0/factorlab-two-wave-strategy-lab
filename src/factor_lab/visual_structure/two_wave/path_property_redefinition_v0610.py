"""v0.6.10 audit-only threshold-free path-property descriptors.

No qualification threshold or recognizer behavior is changed.  The module
separates fine-path roughness, hidden variation, concentration and 5m-origin
aliasing uncertainty using supplied path samples only.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Sequence

import numpy as np

SCHEMA = "two_wave_path_property_redefinition@0.6.10"


def _epoch_minute(value: object) -> int:
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, float):
        if not float(value).is_integer():
            raise ValueError("minute coordinate must be integral")
        return int(value)
    return int(round(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() / 60.0))


def path_stats(values: Sequence[float]) -> dict:
    y = np.asarray(values, dtype=float)
    if y.ndim != 1 or len(y) < 2:
        raise ValueError("at least two path values required")
    if not np.isfinite(y).all():
        raise ValueError("finite path values required")
    changes = np.abs(np.diff(y))
    tv = float(changes.sum())
    displacement = abs(float(y[-1] - y[0]))
    max_step = float(changes.max())
    return {
        "rows": int(len(y)),
        "total_variation": tv,
        "net_displacement": displacement,
        "max_step": max_step,
        "efficiency": displacement / tv if tv else 0.0,
        "jump_share": max_step / tv if tv else 1.0,
        "flat_share": float(np.mean(changes == 0)),
    }


def property_components(native_values: Sequence[float], fine_values: Sequence[float]) -> dict:
    native = path_stats(native_values)
    fine = path_stats(fine_values)
    d = fine["net_displacement"]
    if abs(d - native["net_displacement"]) > 1e-12:
        raise ValueError("native and fine path endpoints must have equal displacement")
    return {
        "schema": SCHEMA,
        "native": native,
        "fine": fine,
        "fine_roughness": math.log(fine["total_variation"] / d) if d > 0 and fine["total_variation"] > 0 else None,
        "hidden_variation": math.log(fine["total_variation"] / native["total_variation"]) if fine["total_variation"] > 0 and native["total_variation"] > 0 else None,
        "fine_concentration": fine["jump_share"],
        "max_step_refinement": math.log(fine["max_step"] / native["max_step"]) if fine["max_step"] > 0 and native["max_step"] > 0 else None,
    }


def efficiency_identity_error(native_values: Sequence[float], fine_values: Sequence[float]) -> float | None:
    out = property_components(native_values, fine_values)
    a, b = out["native"], out["fine"]
    if a["efficiency"] <= 0 or b["efficiency"] <= 0 or a["total_variation"] <= 0 or b["total_variation"] <= 0:
        return None
    return math.log(b["efficiency"] / a["efficiency"]) + math.log(b["total_variation"] / a["total_variation"])


def jump_identity_error(native_values: Sequence[float], fine_values: Sequence[float]) -> float | None:
    out = property_components(native_values, fine_values)
    a, b = out["native"], out["fine"]
    if min(a["jump_share"], b["jump_share"], a["max_step"], b["max_step"], a["total_variation"], b["total_variation"]) <= 0:
        return None
    left = math.log(b["jump_share"] / a["jump_share"])
    right = math.log(b["max_step"] / a["max_step"]) - math.log(b["total_variation"] / a["total_variation"])
    return left - right


@dataclass(frozen=True)
class OriginEnsemble:
    origins: tuple[dict, ...]
    origin_log_tv_ratio_median: float | None
    origin_log_tv_ratio_range: float | None
    origin_jump_median: float | None
    origin_jump_range: float | None


def origin_ensemble(minutes: Sequence[object], closes: Sequence[float]) -> OriginEnsemble:
    if len(minutes) != len(closes) or len(minutes) < 2:
        raise ValueError("aligned minute/close path required")
    mm = [_epoch_minute(x) for x in minutes]
    if any(b <= a for a, b in zip(mm, mm[1:])):
        raise ValueError("minutes must increase strictly")
    y = [float(x) for x in closes]
    fine = path_stats(y)
    rows = []
    log_ratios = []
    jumps = []
    for r in range(5):
        indices = {0, len(mm) - 1}
        indices.update(i for i in range(1, len(mm) - 1) if mm[i] % 5 == r)
        idx = sorted(indices)
        stats = path_stats([y[i] for i in idx])
        log_ratio = (
            math.log(fine["total_variation"] / stats["total_variation"])
            if fine["total_variation"] > 0 and stats["total_variation"] > 0
            else None
        )
        rows.append({"origin": r, "indices": idx, "stats": stats, "log_tv_ratio": log_ratio})
        if log_ratio is not None:
            log_ratios.append(log_ratio)
        jumps.append(stats["jump_share"])
    return OriginEnsemble(
        origins=tuple(rows),
        origin_log_tv_ratio_median=float(np.median(log_ratios)) if log_ratios else None,
        origin_log_tv_ratio_range=float(max(log_ratios) - min(log_ratios)) if log_ratios else None,
        origin_jump_median=float(np.median(jumps)) if jumps else None,
        origin_jump_range=float(max(jumps) - min(jumps)) if jumps else None,
    )


def descriptor(native_values: Sequence[float], fine_minutes: Sequence[object], fine_values: Sequence[float]) -> dict:
    out = property_components(native_values, fine_values)
    ensemble = origin_ensemble(fine_minutes, fine_values)
    return {
        "schema": SCHEMA,
        "fine_roughness": out["fine_roughness"],
        "hidden_variation": out["hidden_variation"],
        "fine_concentration": out["fine_concentration"],
        "max_step_refinement": out["max_step_refinement"],
        "origin_log_tv_ratio_median": ensemble.origin_log_tv_ratio_median,
        "origin_log_tv_ratio_range": ensemble.origin_log_tv_ratio_range,
        "origin_jump_median": ensemble.origin_jump_median,
        "origin_jump_range": ensemble.origin_jump_range,
        "future_outcome_used": False,
        "trade_authority": False,
    }
