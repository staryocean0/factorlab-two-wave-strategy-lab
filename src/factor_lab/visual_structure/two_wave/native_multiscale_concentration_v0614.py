"""v0.6.14 audit-only native multiscale concentration response.

Only one closed native close path is accepted. Fine/oracle/counterpart data are
not part of the registered response interface.
"""
from __future__ import annotations

from typing import Sequence
import numpy as np

from .step_count_normalized_concentration_v0613 import concentration_profile

SCHEMA = "two_wave_native_multiscale_concentration@0.6.14"
STRIDES = (1, 2, 3, 4)
COMPONENTS = ("c_inf", "c_1", "c_2")


def subpartition_indices(point_count: int, stride: int, phase: int) -> tuple[int, ...]:
    if isinstance(point_count, bool) or not isinstance(point_count, int) or point_count < 2:
        raise ValueError("point_count must be integer >=2")
    if stride not in STRIDES:
        raise ValueError("stride must be one of 1,2,3,4")
    if isinstance(phase, bool) or not isinstance(phase, int) or not 0 <= phase < stride:
        raise ValueError("phase must lie in [0,stride)")
    last = point_count - 1
    idx = {0, last}
    idx.update(i for i in range(1, last) if i % stride == phase)
    return tuple(sorted(idx))


def _profile_selected(y: np.ndarray, idx: tuple[int, ...]) -> dict:
    selected = y[np.asarray(idx, dtype=int)]
    return concentration_profile(np.abs(np.diff(selected)))


def native_multiscale_response(closes: Sequence[float]) -> dict:
    y = np.asarray(closes, dtype=float)
    if y.ndim != 1 or len(y) < 2 or not np.isfinite(y).all():
        raise ValueError("at least two finite native closes required")

    strides = {}
    for stride in STRIDES:
        rows = []
        for phase in range(stride):
            idx = subpartition_indices(len(y), stride, phase)
            prof = _profile_selected(y, idx)
            rows.append({"phase": phase, "indices": list(idx), "profile": prof})
        comp = {}
        for name in COMPONENTS:
            vals = [float(row["profile"][name]) for row in rows if row["profile"][name] is not None]
            comp[name] = {
                "defined_phase_count": len(vals),
                "phase_median": float(np.median(vals)) if vals else None,
                "phase_range": float(max(vals) - min(vals)) if vals else None,
            }
        strides[str(stride)] = {"phases": rows, "components": comp}

    response = {}
    for name in COMPONENTS:
        base = strides["1"]["components"][name]["phase_median"]
        response[name] = {"native_value": base}
        for stride in (2, 3, 4):
            med = strides[str(stride)]["components"][name]["phase_median"]
            response[name][f"delta_{stride}"] = (float(med - base) if med is not None and base is not None else None)
            response[name][f"range_{stride}"] = strides[str(stride)]["components"][name]["phase_range"]
            response[name][f"defined_phase_count_{stride}"] = strides[str(stride)]["components"][name]["defined_phase_count"]

    return {
        "schema": SCHEMA,
        "strides": strides,
        "response": response,
        "future_outcome_used": False,
        "trade_authority": False,
    }
