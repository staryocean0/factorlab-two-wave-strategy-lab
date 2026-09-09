"""v0.5.3 qualification overlay: retire legacy raw-ER rejection only.

The parent representation, tuple birth, raw projection, all other frozen
qualification diagnostics, D1 geometry and exclusive ledger policy remain those
of v0.5.2/v0.5.1.  Raw path-efficiency values are retained for audit; the only
research change is that `inefficient_leg` no longer rejects a parent-scale
candidate after the exact-ridge hierarchy has defined the parent legs.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from .characteristic_scale_v051 import CharacteristicExclusiveLedger
from .extremum_ridge_v052 import RidgeRun, build_ridge_run
from .same_scale_v043 import MaturityConfig

SCHEMA = "two_wave_legacy_er_overlay_v053@0.5.3"
CHANGED_COMPONENT = "remove_legacy_raw_er_from_parent_scale_qualification"
REMOVED_REASON = "inefficient_leg"


@dataclass
class LegacyEROverlayRun:
    """Frozen v0.5.2 structural run plus the v0.5.3 qualification overlay."""

    base_run: RidgeRun
    evaluated_records: list[dict]
    ledger: CharacteristicExclusiveLedger


def adjust_v052_record_for_v053(record: dict) -> dict:
    """Deep-copy one v0.5.2 record and remove only legacy raw-ER rejection.

    This function deliberately does not recompute path efficiency.  The raw
    values remain attached to `leg_paths` for audit and can therefore be
    compared byte-for-byte with v0.5.2 diagnostics.
    """

    out = copy.deepcopy(record)
    original_reasons = list(out["scale_rejection_reasons"])
    remaining_reasons = [reason for reason in original_reasons if reason != REMOVED_REASON]

    out["scale_rejection_reasons"] = remaining_reasons
    out["scale_qualified"] = not remaining_reasons
    out["classification"] = (
        out["geometric_direction_diagnostic"] if out["scale_qualified"] else "not_same_scale"
    )
    out["schema_version_v053_overlay"] = SCHEMA
    out["qualification_overlay"] = CHANGED_COMPONENT
    out["legacy_raw_er_parent_gate_active"] = False
    out["legacy_raw_er_original_reasons"] = original_reasons
    out["legacy_raw_er_audit_values"] = [float(path["efficiency"]) for path in out["leg_paths"]]
    out["future_outcome_used"] = False
    out["trade_authority"] = False
    return out


def build_legacy_er_run_v053(
    bars: list[dict],
    cfg: MaturityConfig | None = None,
) -> LegacyEROverlayRun:
    """Run frozen v0.5.2, then apply exactly one v0.5.3 qualification overlay."""

    base = build_ridge_run(bars, cfg)
    evaluated = [adjust_v052_record_for_v053(row) for row in base.evaluated_records]
    ledger = CharacteristicExclusiveLedger()
    ledger.add_records(evaluated)
    return LegacyEROverlayRun(base_run=base, evaluated_records=evaluated, ledger=ledger)
