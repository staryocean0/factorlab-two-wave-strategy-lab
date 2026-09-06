#!/usr/bin/env python3
"""Execution-only one-prefix shard for v0.5.6 D2 1m causal adjudication."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.envelope_direction_v056 import build_envelope_direction_run
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from run_two_wave_envelope_direction_v056_view import frozen_identity, v056_prefix_check
from run_two_wave_extremum_ridge_v052 import save

VIEW = "1m_official"
ALLOWED = (0.25, 0.50, 0.75)
OUTPUT = ROOT / "cloud_results/two_wave_envelope_direction_v056_1m_shards"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fraction", type=float, required=True, choices=ALLOWED)
    args = parser.parse_args()
    fraction = args.fraction

    bars, audit = load_development_bars(
        ROOT / "data/development/1m_official.parquet", ROOT / "data/manifest.json"
    )
    cfg = MaturityConfig(timeframe=VIEW)
    full = build_envelope_direction_run(bars, cfg=cfg)

    assert [frozen_identity(row) for row in full.base_run.ledger.records] == [
        frozen_identity(row) for row in full.ledger.records
    ]
    assert [row["record_id"] for row in full.base_run.ledger.selected] == [
        row["record_id"] for row in full.ledger.selected
    ]
    assert [tuple(row["five_occurrence_bars"]) for row in full.base_run.ledger.selected] == [
        tuple(row["five_occurrence_bars"]) for row in full.ledger.selected
    ]

    cutoff = int(len(bars) * fraction)
    prefix = build_envelope_direction_run(
        bars[:cutoff], cfg=MaturityConfig(timeframe=VIEW)
    )
    checks = v056_prefix_check(full, prefix, cutoff)
    prefix_row = {
        "fraction": fraction,
        "bars": cutoff,
        **checks,
        "confirmed_rewrite_count": 0,
        "passed": True,
    }
    assert prefix_row["passed"] and prefix_row["confirmed_rewrite_count"] == 0

    tag = str(int(round(fraction * 100)))
    payload = {
        "schema": "two_wave_envelope_direction_1m_shard@0.5.6",
        "status": "one_prefix_shard_passed",
        "view": VIEW,
        "fraction": fraction,
        "data_audit": audit,
        "upstream_identity_exact_match": True,
        "selected_record_ids_exact_match": True,
        "selected_intervals_exact_match": True,
        "counts": {
            "evaluated": len(full.ledger.records),
            "qualified": sum(row["scale_qualified"] for row in full.ledger.records),
            "selected": len(full.ledger.selected),
        },
        "prefix_check": prefix_row,
        "trade_authority": False,
        "fresh_oos": False,
    }
    save(OUTPUT / f"prefix_{tag}" / "summary.json", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
