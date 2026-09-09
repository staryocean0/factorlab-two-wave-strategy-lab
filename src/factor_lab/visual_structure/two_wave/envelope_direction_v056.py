"""v0.5.6 D2: parent direction from whole-envelope translation.

The upstream v0.5.2 exact-ridge parent identity and v0.5.4 qualification are
frozen.  This module adds a new direction-version field only.  Historical D0
and D1 remain in each record; record IDs and qualification are preserved.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Iterable

from .characteristic_scale_v051 import CharacteristicExclusiveLedger
from .cycle_scale_qualification_v054 import CycleScaleQualificationRun, build_cycle_scale_qualification_run
from .same_scale_v043 import MaturityConfig

SCHEMA = "two_wave_envelope_direction@0.5.6"
HYPOTHESIS = "whole_parent_upper_lower_envelope_translation_defines_parent_direction"
# Numerical comparison epsilon only.  This is not a research threshold and is
# many orders of magnitude below the frozen 0.15 amplitude-unit boundary.
NUMERIC_EPSILON = 1e-12


@dataclass
class EnvelopeDirectionRun:
    base_run: CycleScaleQualificationRun
    evaluated_records: list[dict]
    ledger: CharacteristicExclusiveLedger


def d2_from_phase_steps(
    phase_steps: list[float] | tuple[float, float, float],
    phase: str,
    cfg: MaturityConfig | None = None,
) -> dict:
    """Classify frozen parent geometry using only whole-envelope translations."""
    c = cfg or MaturityConfig()
    if len(phase_steps) != 3:
        raise ValueError("D2 requires exactly three frozen phase steps")
    s0, s1, s2 = (float(v) for v in phase_steps)
    net = s0 + s1
    if phase == "low":
        lower, upper = net, s2
    elif phase == "high":
        upper, lower = net, s2
    else:
        raise ValueError("phase must be low or high")

    tol = c.phase_tolerance
    eps = NUMERIC_EPSILON
    if upper > tol + eps and lower > tol + eps:
        label = "uptrend"
        reason = "both_parent_envelopes_up"
    elif upper < -tol - eps and lower < -tol - eps:
        label = "downtrend"
        reason = "both_parent_envelopes_down"
    elif abs(upper) <= tol + eps and abs(lower) <= tol + eps:
        label = "range"
        reason = "both_parent_envelopes_low_translation"
    else:
        label = "uncertain"
        reason = "parent_envelope_translation_mixed_or_one_sided"

    return {
        "label": label,
        "reason": reason,
        "upper_envelope_drift": upper,
        "lower_envelope_drift": lower,
        "same_envelope_total_drift": net,
        "other_envelope_drift": s2,
        "phase_tolerance": tol,
        "numeric_epsilon": eps,
    }


def add_d2_to_record(record: dict, cfg: MaturityConfig | None = None) -> dict:
    """Append D2 to one v0.5.4 record without changing upstream identity."""
    c = cfg or MaturityConfig(timeframe=record.get("timeframe", "5m_offset_0"))
    out = copy.deepcopy(record)
    d2 = d2_from_phase_steps(record["phase_steps_in_amplitude_units"], record["phase"], c)
    versions = copy.deepcopy(record.get("direction_versions", {}))
    versions["D2"] = d2["label"]
    versions["D2_reason"] = d2["reason"]
    versions["D2_upper_envelope_drift"] = d2["upper_envelope_drift"]
    versions["D2_lower_envelope_drift"] = d2["lower_envelope_drift"]
    versions["D2_phase_tolerance"] = d2["phase_tolerance"]
    versions["D2_hypothesis"] = HYPOTHESIS
    out["direction_versions"] = versions
    out["direction_schema_version"] = SCHEMA
    out["direction_hypothesis"] = HYPOTHESIS
    out["classification"] = d2["label"] if out["scale_qualified"] else "not_same_scale"
    out["selected"] = False
    out["overlap_suppressed_by"] = None
    out["trade_authority"] = False
    out["future_outcome_used"] = False
    return out


def _identity(record: dict) -> tuple:
    return (
        record["record_id"],
        record["ridge_tuple_id"],
        tuple(record["five_occurrence_bars"]),
        record["birth_scale_id"],
        record["confirmation_bar"],
        record["start_bar"],
        record["end_bar"],
    )


def build_envelope_direction_run(
    bars: list[dict],
    cfg: MaturityConfig | None = None,
    sigmas: Iterable[float] | None = None,
) -> EnvelopeDirectionRun:
    """Build D2 over frozen v0.5.4 records and assert upstream zero drift."""
    c = cfg or MaturityConfig()
    base = build_cycle_scale_qualification_run(bars, cfg=c, sigmas=sigmas)
    evaluated = [add_d2_to_record(record, c) for record in base.ledger.records]

    if [_identity(r) for r in evaluated] != [_identity(r) for r in base.ledger.records]:
        raise AssertionError("D2 changed frozen parent identity")
    if [r["scale_qualified"] for r in evaluated] != [r["scale_qualified"] for r in base.ledger.records]:
        raise AssertionError("D2 changed frozen qualification")
    for before, after in zip(base.ledger.records, evaluated):
        for key in ("D0", "D1", "D0_reason", "D1_reason"):
            if before["direction_versions"].get(key) != after["direction_versions"].get(key):
                raise AssertionError(f"D2 overwrote historical direction field {key}")

    ledger = CharacteristicExclusiveLedger()
    ledger.add_records(evaluated)
    base_selected = [r["record_id"] for r in base.ledger.selected]
    d2_selected = [r["record_id"] for r in ledger.selected]
    if d2_selected != base_selected:
        raise AssertionError("D2 changed deterministic selected record IDs")
    if [tuple(r["five_occurrence_bars"]) for r in ledger.selected] != [
        tuple(r["five_occurrence_bars"]) for r in base.ledger.selected
    ]:
        raise AssertionError("D2 changed deterministic selected intervals")

    return EnvelopeDirectionRun(base_run=base, evaluated_records=evaluated, ledger=ledger)
