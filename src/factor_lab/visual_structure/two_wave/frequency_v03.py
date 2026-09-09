"""Frequency diagnostics and a separate causal direction layer; no trading authority."""
from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass

import numpy as np

from .candidate_v02 import CandidateConfig, CandidateEngine
from .models import stable_id

SCHEMA = "two_wave_direction_layer@0.3.0"


def path_metrics(log_prices: np.ndarray, horizon: int) -> dict[str, np.ndarray]:
    """Trailing n RETURNS (n+1 closes); undefined warmup remains NaN."""
    x = np.asarray(log_prices, dtype=float)
    if x.ndim != 1 or not np.isfinite(x).all():
        raise ValueError("finite one-dimensional log prices required")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be a positive integer")
    out = {k: np.full(len(x), np.nan) for k in ("er", "signed_er", "rms_return", "signed_rms_slope")}
    if len(x) <= horizon:
        return out
    r = np.diff(x)
    total = np.r_[0.0, np.cumsum(np.abs(r))]
    squared = np.r_[0.0, np.cumsum(r * r)]
    distance = x[horizon:] - x[:-horizon]
    length = total[horizon:] - total[:-horizon]
    energy = np.maximum(squared[horizon:] - squared[:-horizon], 0.0)
    signed = np.divide(distance, length, out=np.zeros_like(distance), where=length > 0)
    if np.max(np.abs(signed), initial=0) > 1 + 1e-7:
        raise ArithmeticError("path efficiency outside mathematical bound")
    signed = np.clip(signed, -1, 1)
    out["signed_er"][horizon:] = signed
    out["er"][horizon:] = np.abs(signed)
    out["rms_return"][horizon:] = np.sqrt(energy / horizon)
    denom = np.sqrt(horizon * energy)
    out["signed_rms_slope"][horizon:] = np.divide(distance, denom, out=np.zeros_like(distance), where=denom > 0)
    return out


def describe_er(values: np.ndarray) -> dict:
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    if not len(a):
        return {"n": 0}
    return {
        "n": len(a), "mean": float(a.mean()), "std": float(a.std()),
        "p10": float(np.quantile(a, .1)), "p50": float(np.quantile(a, .5)),
        "p90": float(np.quantile(a, .9)),
        "low_fraction": float(np.mean(a <= .2)),
        "high_fraction": float(np.mean(a >= .6)),
        "mixed_fraction": float(np.mean((a > .2) & (a < .6))),
    }


def coarse_fine_path(fine_x: np.ndarray, coarse_x: np.ndarray, fine_indices: np.ndarray, horizon: int) -> dict:
    """Compare ORIGINAL supplied closes on identical endpoints. No bars created.

    fine_indices is the exact timestamp lookup of every original coarse row;
    -1 means unmatched. Windows containing unmatched rows are invalid.
    """
    f, c = np.asarray(fine_x, float), np.asarray(coarse_x, float)
    idx = np.asarray(fine_indices, int)
    if len(c) != len(idx) or not np.isfinite(f).all() or not np.isfinite(c).all():
        raise ValueError("inconsistent or nonfinite input")
    if horizon < 1 or len(c) <= horizon or np.any(idx >= len(f)) or np.any(idx < -1):
        raise ValueError("invalid horizon or index")
    present = idx >= 0
    if np.any(np.diff(idx[present]) <= 0):
        raise ValueError("matched timestamps must increase")
    end = np.arange(horizon, len(c)); start = end - horizon
    cum_bad = np.r_[0, np.cumsum(~present)]
    valid = (cum_bad[end + 1] - cum_bad[start]) == 0
    safe = np.maximum(idx, 0)
    cum_l = np.r_[0.0, np.cumsum(np.abs(np.diff(f)))]
    fine_l = cum_l[safe[end]] - cum_l[safe[start]]
    fine_net = f[safe[end]] - f[safe[start]]
    fine_er = np.divide(np.abs(fine_net), fine_l, out=np.zeros_like(fine_l), where=fine_l > 0)
    match_price = present & np.isclose(c, f[safe], rtol=0, atol=1e-10)
    bad_price = np.r_[0, np.cumsum(~match_price)]
    all_prices_match = (bad_price[end + 1] - bad_price[start]) == 0
    coarse_er = path_metrics(c, horizon)["er"][end]
    return {"start": start, "end": end, "valid": valid,
            "all_prices_match": all_prices_match, "fine_er": fine_er,
            "coarse_er": coarse_er, "fine_return_count": safe[end] - safe[start]}


@dataclass(frozen=True)
class DirectionConfig:
    """Thresholds inherited semantically from v0.1; no fitted parameters."""
    drift_threshold: float = .5
    phase_step_tolerance: float = .15

    def __post_init__(self) -> None:
        for v in asdict(self).values():
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
                raise ValueError("thresholds must be finite positive numbers")

    @property
    def config_hash(self) -> str:
        return stable_id("direction_cfg", {"schema": SCHEMA, **asdict(self)})


def direction_record(structure: dict, points: list[dict], bars: list[dict], config: DirectionConfig | None = None) -> dict:
    """Two-cycle D plus THREE actual same-phase displacements, not screen angle.

    This layer does not replace the A channel or grant its boundary suitability.
    Complete-cycle occurrence data only; confirmation leg never enters fitting.
    """
    cfg = config or DirectionConfig()
    if len(points) != 5 or [p["pivot_id"] for p in points] != structure["pivot_ids"]:
        raise ValueError("five exact source pivots required")
    if len(structure["cycle_ids"]) != 2:
        raise ValueError("exactly two source cycles required")
    indices = [p["occurrence_bar"] for p in points]
    if any(a >= b for a, b in zip(indices, indices[1:])) or any(a["kind"] == b["kind"] for a, b in zip(points, points[1:])):
        raise ValueError("strictly ordered alternating pivots required")
    if indices[-1] > structure["confirmation_bar"] or any(p["confirmation_bar"] > structure["confirmation_bar"] for p in points):
        raise ValueError("unconfirmed pivot in direction input")
    g = structure["geometry"]
    label, reasons, steps, er, spans = "uncertain", [], None, None, None
    if not g["valid"] or not math.isfinite(g["width"]) or g["width"] <= 0 or not math.isfinite(g["D"]):
        reasons = ["invalid_geometry"]
    else:
        x = [p["log_price"] for p in points]
        steps = [(x[2]-x[0])/g["width"], (x[4]-x[2])/g["width"], (x[3]-x[1])/g["width"]]
        spans = [(max(x[::2])-min(x[::2]))/g["width"], abs(steps[2])]
        d = g["D"]
        if abs(d) <= cfg.drift_threshold:
            if max(spans) <= cfg.drift_threshold:
                label = "range"
            else:
                reasons = ["small_net_drift_but_large_phase_migration"]
        else:
            sign = 1 if d > 0 else -1
            if min(sign*q for q in steps) > cfg.phase_step_tolerance:
                label = "uptrend" if sign > 0 else "downtrend"
            else:
                reasons = ["not_all_three_phase_steps_clearly_codirectional"]
        segment = np.asarray([b["log_close"] for b in bars[indices[0]:indices[-1]+1]], float)
        if len(segment) != indices[-1]-indices[0]+1:
            raise ValueError("all completed cycle closes required")
        length = float(np.abs(np.diff(segment)).sum())
        er = abs(float(segment[-1]-segment[0]))/length if length > 0 else 0.0
    record = {
        "schema_version": SCHEMA, "config_hash": cfg.config_hash,
        "source_structure_id": structure["structure_id"],
        "pivot_ids": list(structure["pivot_ids"]), "cycle_ids": list(structure["cycle_ids"]),
        "phase": structure["phase"], "five_occurrence_bars": indices,
        "timeframe": structure["timeframe"], "scale_id": structure["scale_id"],
        "start_bar": structure["start_bar"], "end_bar": structure["end_bar"],
        "confirmation_bar": structure["confirmation_bar"], "confirmation_time": structure["confirmation_time"],
        "effective_information_time": structure["effective_information_time"],
        "direction_classification": label, "direction_rejection_reasons": reasons,
        "phase_displacements_in_widths": steps, "phase_spans_in_widths": spans, "D": g["D"], "E": g["E"],
        "path_er": er, "channel_classification_A": structure["classification"],
        "channel_rejection_reasons_A": list(g["rejection_reasons"]),
        "channel_accepted_by_A": not bool(g["rejection_reasons"]) and g["valid"],
        "morphology_attributes": list(structure["attributes"]),
        "boundary_basis": "unchanged_A_diagnostic_only", "trade_authority": False,
        "human_reference": False, "future_outcome_used": False,
    }
    record["direction_record_id"] = stable_id("direction", [cfg.config_hash, record["source_structure_id"]])
    return record


class DirectionEngine:
    """Append-only sidecar on the unmodified A engine; future rows cannot revise it."""
    def __init__(self, source_config: CandidateConfig | None = None, direction_config: DirectionConfig | None = None):
        source_config = source_config or CandidateConfig(geometry_variant="detrended_width")
        if source_config.geometry_variant != "detrended_width":
            raise ValueError("v0.3 source must be frozen candidate A")
        self.source = CandidateEngine(source_config)
        self.config = direction_config or DirectionConfig()
        self.records: list[dict] = []
        self._pivots: dict[str, dict] = {}

    def update(self, bar: dict) -> list[dict]:
        before_p, before_s = len(self.source.pivots), len(self.source.structures)
        self.source.update(bar)
        for p in self.source.pivots[before_p:]:
            self._pivots[p["pivot_id"]] = p
        out = []
        for s in self.source.structures[before_s:]:
            record = direction_record(s, [self._pivots[k] for k in s["pivot_ids"]], self.source.bars, self.config)
            self.records.append(record)
            out.append(copy.deepcopy(record))
        return out
