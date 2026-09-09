"""C1: audit mixed phase migration without conflating direction and channel quality.

C0 (frequency_v03) is retained byte-for-byte. This correction was motivated by
preselected real-data case_05 and the existing no-cancelling-drift requirement.
It has no future return input and does not search a new threshold.
"""
from __future__ import annotations

import copy
import math

from .frequency_v03 import DirectionEngine as C0Engine
from .models import stable_id

SCHEMA = "two_wave_direction_layer@0.3.1"


def audit_range_record(record: dict, tolerance: float = .15) -> dict:
    """Return a new record; a mixed-phase range is demoted, never relabelled trend."""
    if isinstance(tolerance, bool) or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("tolerance must be finite and positive")
    out = copy.deepcopy(record)
    conflicts = []
    if record["direction_classification"] == "range":
        steps = record["phase_displacements_in_widths"]
        if steps is None or len(steps) != 3 or not all(math.isfinite(v) for v in steps):
            raise ValueError("range requires three finite phase displacements")
        a, b, minority = steps
        if a * b < 0 and min(abs(a), abs(b)) > tolerance:
            conflicts.append("range_contains_opposed_cycle_phase_steps")
        majority = a + b
        if majority * minority < 0 and min(abs(majority), abs(minority)) > tolerance:
            conflicts.append("range_contains_opposed_high_low_migration")
    out.update({
        "schema_version": SCHEMA,
        "source_C0_direction_record_id": record["direction_record_id"],
        "direction_classification_before_range_audit": record["direction_classification"],
        "range_audit_tolerance": tolerance,
        "range_audit_conflicts": conflicts,
        "config_hash": stable_id("direction_cfg", {"schema": SCHEMA,
            "source_config_hash": record["config_hash"], "range_audit_tolerance": tolerance}),
    })
    if conflicts:
        out["direction_classification"] = "uncertain"
        out["direction_rejection_reasons"] += conflicts
    out["direction_record_id"] = stable_id("direction", [out["config_hash"], out["source_structure_id"]])
    return out


class DirectionEngine(C0Engine):
    """Separate C0 source stream and immutable C1 output; no patched global state."""
    def __init__(self, source_config=None, direction_config=None):
        self._c0 = C0Engine(source_config, direction_config)
        self.source = self._c0.source
        self.config = self._c0.config
        self.records: list[dict] = []

    def update(self, bar: dict) -> list[dict]:
        new = [audit_range_record(r, self.config.phase_step_tolerance) for r in self._c0.update(bar)]
        self.records.extend(copy.deepcopy(new))
        return new
