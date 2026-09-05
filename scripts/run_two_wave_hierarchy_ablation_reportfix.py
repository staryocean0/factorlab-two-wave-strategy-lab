#!/usr/bin/env python3
"""Reporting-only compatibility shim for the frozen v0.4.4 ablation runner.

The first formal run completed all six view computations but failed while
serializing a v0.4.3 record because the shared compact formatter required a
v0.4.4-only lineage field. This shim changes only that formatter: common fields
remain required, while the v0.4.4-only collapsed-pivot count is emitted when
present. No detector, hierarchy, qualification, D1, clock, ledger, or threshold
logic is changed.
"""
from __future__ import annotations

import run_two_wave_hierarchy_ablation as study


_COMMON_FIELDS = (
    "record_id",
    "classification",
    "five_occurrence_bars",
    "leg_durations",
    "cycle_durations",
    "confirmation_bar",
    "scale_qualified",
    "scale_rejection_reasons",
)


def compact_record_compatible(record):
    row = {key: record[key] for key in _COMMON_FIELDS}
    if "collapsed_local_pivots_in_two_cycles" in record:
        row["collapsed_local_pivots_in_two_cycles"] = record[
            "collapsed_local_pivots_in_two_cycles"
        ]
    return row


study.compact_record = compact_record_compatible


if __name__ == "__main__":
    study.main()
