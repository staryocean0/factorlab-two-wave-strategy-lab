#!/usr/bin/env python3
"""One native-5m view shard for formal v0.5.6 D2 multiview adjudication.

Research logic is imported unchanged from the frozen v0.5.6 implementation.
Each shard rebuilds one full native view plus 25/50/75% prefixes, proving both
upstream v0.5.4 causality and confirmed D2 classification prefix invariance.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.envelope_direction_v056 import build_envelope_direction_run
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from run_two_wave_cycle_scale_qualification_v054_five_view import v054_prefix_check
from run_two_wave_extremum_ridge_v052 import PREFIX_FRACTIONS, save

VIEWS = [f"5m_offset_{i}" for i in range(5)]
DEFAULT_OUTPUT = ROOT / "cloud_results/two_wave_envelope_direction_v056_views"


def frozen_identity(row: dict) -> tuple:
    return (
        row["record_id"],
        row["ridge_tuple_id"],
        tuple(row["five_occurrence_bars"]),
        row["birth_scale_id"],
        row["birth_scale_level"],
        row["confirmation_bar"],
        row["start_bar"],
        row["end_bar"],
        row["scale_qualified"],
        tuple(row["scale_rejection_reasons"]),
    )


def d2_signature(row: dict) -> tuple:
    dv = row["direction_versions"]
    return (
        frozen_identity(row),
        dv.get("D0"),
        dv.get("D1"),
        dv.get("D1_reason"),
        dv.get("D2"),
        dv.get("D2_reason"),
        float(dv["D2_upper_envelope_drift"]),
        float(dv["D2_lower_envelope_drift"]),
        row["classification"],
        row["selected"],
        row["overlap_suppressed_by"],
    )


def signatures(records, cutoff: int):
    return [d2_signature(row) for row in records if row["confirmation_bar"] < cutoff]


def v056_prefix_check(full, prefix, cutoff: int) -> dict:
    upstream = v054_prefix_check(full.base_run, prefix.base_run, cutoff)
    checks = {
        "d2_evaluated_records": signatures(prefix.ledger.records, cutoff)
        == signatures(full.ledger.records, cutoff),
        "d2_selected_records": signatures(prefix.ledger.selected, cutoff)
        == signatures(full.ledger.selected, cutoff),
    }
    if not all(checks.values()):
        failed = [name for name, ok in checks.items() if not ok]
        raise AssertionError(f"v0.5.6 D2 prefix rewrite at cutoff={cutoff}: {failed}")
    return {**{f"upstream_{name}": ok for name, ok in upstream.items()}, **checks}


def selected_intervals(records, label_version: str):
    out = []
    for row in records:
        if label_version == "D1":
            label = row["direction_versions"]["D1"]
        elif label_version == "D2":
            label = row["direction_versions"]["D2"]
        else:
            raise ValueError(label_version)
        out.append(
            {
                "start_time": str(row["start_time"]),
                "end_time": str(row["end_time"]),
                "classification": label,
                "record_id": row["record_id"],
                "five_occurrence_bars": list(row["five_occurrence_bars"]),
            }
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--view", required=True, choices=VIEWS)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    view = args.view
    out = args.output_root / view

    bars, audit = load_development_bars(
        ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json"
    )
    cfg = MaturityConfig(timeframe=view)
    run = build_envelope_direction_run(bars, cfg=cfg)
    base = run.base_run

    assert [frozen_identity(row) for row in base.ledger.records] == [
        frozen_identity(row) for row in run.ledger.records
    ]
    assert [row["record_id"] for row in base.ledger.selected] == [
        row["record_id"] for row in run.ledger.selected
    ]
    assert [tuple(row["five_occurrence_bars"]) for row in base.ledger.selected] == [
        tuple(row["five_occurrence_bars"]) for row in run.ledger.selected
    ]
    assert all(not row.get("future_outcome_used", False) for row in run.ledger.records)
    assert all(not row.get("trade_authority", False) for row in run.ledger.records)

    summary = {
        "schema": "two_wave_envelope_direction_native5m_view@0.5.6",
        "status": "running_not_prejudged",
        "view": view,
        "data_audit": audit,
        "upstream": "v0.5.2_exact_ridge_plus_v0.5.4_full_cycle_qualification",
        "changed_component_only": "D2_whole_parent_envelope_translation",
        "upstream_identity_exact_match": True,
        "selected_record_ids_exact_match": True,
        "selected_intervals_exact_match": True,
        "counts": {
            "evaluated": len(run.ledger.records),
            "qualified": sum(row["scale_qualified"] for row in run.ledger.records),
            "selected": len(run.ledger.selected),
            "D1_qualified": dict(Counter(row["direction_versions"]["D1"] for row in run.ledger.records if row["scale_qualified"])),
            "D2_qualified": dict(Counter(row["direction_versions"]["D2"] for row in run.ledger.records if row["scale_qualified"])),
            "D1_selected": dict(Counter(row["direction_versions"]["D1"] for row in run.ledger.selected)),
            "D2_selected": dict(Counter(row["direction_versions"]["D2"] for row in run.ledger.selected)),
        },
        "prefix_checks": [],
        "trade_authority": False,
        "fresh_oos": False,
    }
    save(out / "summary.json", summary)

    for fraction in PREFIX_FRACTIONS:
        cutoff = int(len(bars) * fraction)
        prefix = build_envelope_direction_run(
            bars[:cutoff], cfg=MaturityConfig(timeframe=view)
        )
        checks = v056_prefix_check(run, prefix, cutoff)
        row = {
            "view": view,
            "fraction": fraction,
            "bars": cutoff,
            **checks,
            "confirmed_rewrite_count": 0,
            "passed": True,
        }
        summary["prefix_checks"].append(row)
        save(out / "summary.json", summary)

    assert len(summary["prefix_checks"]) == 3
    assert all(row["passed"] and row["confirmed_rewrite_count"] == 0 for row in summary["prefix_checks"])

    coverage = {
        "schema": "two_wave_envelope_direction_native5m_coverage@0.5.6",
        "view": view,
        "D1": selected_intervals(run.ledger.selected, "D1"),
        "D2": selected_intervals(run.ledger.selected, "D2"),
    }
    assert [row["record_id"] for row in coverage["D1"]] == [row["record_id"] for row in coverage["D2"]]
    assert [(row["start_time"], row["end_time"]) for row in coverage["D1"]] == [
        (row["start_time"], row["end_time"]) for row in coverage["D2"]
    ]
    save(out / "coverage.json", coverage)
    summary["status"] = "native5m_view_passed_pending_aggregation"
    save(out / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
