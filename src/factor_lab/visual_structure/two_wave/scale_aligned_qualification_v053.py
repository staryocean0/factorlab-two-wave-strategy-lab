"""v0.5.3 scale-aligned leg-efficiency qualification ablation.

The parent representation/candidate identity is frozen to v0.5.2 exact-ridge
births.  This module changes exactly one qualification component: leg path
efficiency is measured on the causal TCSS series at each tuple's already-known
birth scale rather than on every raw close.  The numerical threshold remains
0.5 through ``MaturityConfig.min_leg_efficiency``.  All raw reversal, duration,
amplitude, jump, flat, clock, D1 and ledger rules remain frozen.

No outcome, return, P&L, case label or offset IoU enters qualification.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .characteristic_scale_v051 import CharacteristicExclusiveLedger
from .extremum_ridge_v052 import RidgeRun, build_ridge_run
from .models import stable_id
from .multiscale_v050 import default_scale_sigmas, time_causal_scale_space
from .same_scale_v043 import MaturityConfig

SCHEMA = "two_wave_scale_aligned_qualification@0.5.3"
QUALIFICATION_COMPONENT = "birth_scale_causal_tcss_leg_efficiency"
FROZEN_NUMERICAL_THRESHOLD = 0.5


@dataclass
class ScaleAlignedQualificationRun:
    base_run: RidgeRun
    evaluated_records: list[dict]
    ledger: CharacteristicExclusiveLedger


def scale_aligned_leg_paths(record: dict, series: np.ndarray) -> list[dict]:
    """Measure four parent legs on an unshifted causal TCSS log-price series."""
    ids = list(record["five_occurrence_bars"])
    if len(ids) != 5 or any(a >= b for a, b in zip(ids, ids[1:])):
        raise ValueError("five strictly ordered raw occurrence bars required")
    if series.ndim != 1 or ids[0] < 0 or ids[-1] >= len(series):
        raise ValueError("TCSS series must cover the full raw parent interval")
    out = []
    for a, b in zip(ids, ids[1:]):
        y = np.asarray(series[a : b + 1], dtype=float)
        if len(y) < 2 or not np.isfinite(y).all():
            raise ValueError("finite TCSS path with at least two samples required")
        changes = np.abs(np.diff(y))
        length = float(changes.sum())
        out.append(
            {
                "efficiency": abs(float(y[-1] - y[0])) / length if length else 0.0,
                "path_length_log_price": length,
                "endpoint_displacement_log_price": abs(float(y[-1] - y[0])),
            }
        )
    return out


def requalify_record(record: dict, series: np.ndarray, cfg: MaturityConfig) -> dict:
    """Replace only ``inefficient_leg`` using birth-scale TCSS path quality."""
    if abs(float(cfg.min_leg_efficiency) - FROZEN_NUMERICAL_THRESHOLD) > 1e-12:
        raise ValueError("v0.5.3 freezes min_leg_efficiency at 0.5")
    out = copy.deepcopy(record)
    paths = scale_aligned_leg_paths(out, series)
    reasons = [reason for reason in out["scale_rejection_reasons"] if reason != "inefficient_leg"]
    if min(path["efficiency"] for path in paths) < cfg.min_leg_efficiency:
        reasons.append("inefficient_leg")
    # Preserve the original deterministic reason order by placing the changed
    # component where the frozen v0.4.x rule places it: after amplitude checks
    # and before jump/flat checks.
    frozen_order = [
        "short_leg",
        "short_cycle",
        "long_cycle",
        "long_pair",
        "cycle_duration_mismatch",
        "corresponding_leg_duration_mismatch",
        "invalid_amplitude",
        "amplitude_mismatch",
        "inefficient_leg",
        "jump_dominated_leg",
        "flat_dominated_leg",
        "too_many_observed_days",
        "wall_span_too_long",
        "confirmation_too_late",
    ]
    present = set(reasons)
    reasons = [reason for reason in frozen_order if reason in present]
    out["schema_version"] = SCHEMA
    out["source"] = "TCSS_v052_exact_ridge_birth_v053_scale_aligned_efficiency"
    out["qualification_component"] = QUALIFICATION_COMPONENT
    out["qualification_parent_identity_schema"] = record.get("schema_version")
    out["raw_leg_paths_frozen_v043"] = copy.deepcopy(record["leg_paths"])
    out["scale_aligned_leg_paths"] = paths
    out["scale_aligned_min_leg_efficiency"] = min(path["efficiency"] for path in paths)
    out["min_leg_efficiency_threshold"] = float(cfg.min_leg_efficiency)
    out["scale_rejection_reasons"] = reasons
    out["scale_qualified"] = not reasons
    out["classification"] = out["direction_versions"]["D1"] if not reasons else "not_same_scale"
    out["record_id"] = stable_id(
        "tcss_exact_ridge_pair_v053",
        {
            "ridge_tuple_id": out["ridge_tuple_id"],
            "raw_occurrences": out["five_occurrence_bars"],
            "birth_scale_id": out["birth_scale_id"],
            "cfg": cfg.config_hash,
            "qualification": QUALIFICATION_COMPONENT,
        },
    )
    out["selected"] = False
    out["overlap_suppressed_by"] = None
    out["trade_authority"] = False
    out["future_outcome_used"] = False
    return out


def build_scale_aligned_qualification_run(
    bars: list[dict],
    cfg: MaturityConfig | None = None,
    sigmas: Iterable[float] | None = None,
) -> ScaleAlignedQualificationRun:
    """Reuse v0.5.2 identity, then ablate only the leg-efficiency measurement scale."""
    cfg = cfg or MaturityConfig()
    if abs(float(cfg.min_leg_efficiency) - FROZEN_NUMERICAL_THRESHOLD) > 1e-12:
        raise ValueError("v0.5.3 freezes min_leg_efficiency at 0.5")
    base = build_ridge_run(bars, cfg=cfg, sigmas=sigmas)
    closes = np.asarray([bar["close"] for bar in bars], dtype=float)
    if not np.isfinite(closes).all() or np.any(closes <= 0):
        raise ValueError("positive finite closes required")
    sigma_values = tuple(default_scale_sigmas() if sigmas is None else sigmas)
    scale_space = time_causal_scale_space(np.log(closes), sigma_values)
    evaluated = []
    for record in base.evaluated_records:
        scale_id = record["birth_scale_id"]
        if scale_id not in scale_space:
            raise ValueError(f"missing birth-scale TCSS series: {scale_id}")
        evaluated.append(requalify_record(record, scale_space[scale_id], cfg))
    ledger = CharacteristicExclusiveLedger()
    ledger.add_records(evaluated)
    return ScaleAlignedQualificationRun(base_run=base, evaluated_records=evaluated, ledger=ledger)
