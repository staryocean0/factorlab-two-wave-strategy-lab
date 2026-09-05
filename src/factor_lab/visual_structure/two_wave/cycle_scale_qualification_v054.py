"""v0.5.4 qualification ablation: full-cycle period defines scale.

Parent representation and candidate identity are frozen to v0.5.2 exact-ridge
births.  The only qualification change is that
``corresponding_leg_duration_mismatch`` becomes diagnostic-only.  Complete
cycle duration checks and every other frozen v0.4.3 qualification rule remain
hard gates with unchanged numerical thresholds.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Iterable

from .characteristic_scale_v051 import CharacteristicExclusiveLedger
from .extremum_ridge_v052 import RidgeRun, build_ridge_run
from .models import stable_id
from .same_scale_v043 import MaturityConfig

SCHEMA = "two_wave_cycle_scale_qualification@0.5.4"
REMOVED_HARD_REASON = "corresponding_leg_duration_mismatch"
HYPOTHESIS = "full_cycle_period_defines_scale_phase_leg_allocation_is_diagnostic"


@dataclass
class CycleScaleQualificationRun:
    base_run: RidgeRun
    evaluated_records: list[dict]
    ledger: CharacteristicExclusiveLedger


def corresponding_leg_duration_ratios(record: dict) -> list[float]:
    legs = [float(x) for x in record["leg_durations"]]
    if len(legs) != 4 or any(x <= 0 for x in legs):
        raise ValueError("four positive leg durations required")
    ratios = []
    for a, b in ((legs[0], legs[2]), (legs[1], legs[3])):
        ratios.append(max(a, b) / min(a, b))
    return ratios


def requalify_record(record: dict) -> dict:
    """Remove exactly one hard reason while preserving its diagnostic value."""
    out = copy.deepcopy(record)
    old_reasons = list(record["scale_rejection_reasons"])
    ratios = corresponding_leg_duration_ratios(record)
    new_reasons = [reason for reason in old_reasons if reason != REMOVED_HARD_REASON]

    out["schema_version"] = SCHEMA
    out["source"] = "TCSS_v052_exact_ridge_birth_v054_cycle_scale_qualification"
    out["qualification_hypothesis"] = HYPOTHESIS
    out["qualification_parent_identity_schema"] = record.get("schema_version")
    out["corresponding_leg_duration_diagnostic"] = {
        "hard_gate": False,
        "frozen_v052_triggered": REMOVED_HARD_REASON in old_reasons,
        "ratios": ratios,
        "max_ratio": max(ratios),
    }
    out["frozen_v052_scale_rejection_reasons"] = old_reasons
    out["scale_rejection_reasons"] = new_reasons
    out["scale_qualified"] = not new_reasons
    out["classification"] = out["direction_versions"]["D1"] if not new_reasons else "not_same_scale"
    out["record_id"] = stable_id(
        "tcss_exact_ridge_pair_v054",
        {
            "ridge_tuple_id": out["ridge_tuple_id"],
            "raw_occurrences": out["five_occurrence_bars"],
            "birth_scale_id": out["birth_scale_id"],
            "hypothesis": HYPOTHESIS,
        },
    )
    out["selected"] = False
    out["overlap_suppressed_by"] = None
    out["trade_authority"] = False
    out["future_outcome_used"] = False
    return out


def build_cycle_scale_qualification_run(
    bars: list[dict],
    cfg: MaturityConfig | None = None,
    sigmas: Iterable[float] | None = None,
) -> CycleScaleQualificationRun:
    """Reuse v0.5.2 identities and demote one frozen reason to diagnostic-only."""
    cfg = cfg or MaturityConfig()
    base = build_ridge_run(bars, cfg=cfg, sigmas=sigmas)
    evaluated = [requalify_record(record) for record in base.evaluated_records]
    ledger = CharacteristicExclusiveLedger()
    ledger.add_records(evaluated)
    return CycleScaleQualificationRun(base_run=base, evaluated_records=evaluated, ledger=ledger)
