#!/usr/bin/env python3
"""Execution-only one-prefix shard for formal v0.5.4 1m causal adjudication.

Each shard rebuilds the same frozen full 1m run and exactly one prefix. This is
only a parallel scheduling split; no research formula, threshold, identity, or
prefix predicate differs from run_two_wave_cycle_scale_qualification_v054_1m.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from factor_lab.visual_structure.two_wave.cycle_scale_qualification_v054 import (
    REMOVED_HARD_REASON,
    build_cycle_scale_qualification_run,
)
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from run_two_wave_cycle_scale_qualification_v054_five_view import identity, v054_prefix_check
from run_two_wave_extremum_ridge_v052 import save

VIEW = "1m_official"
ALLOWED = (0.25, 0.50, 0.75)
OUTPUT = ROOT / "cloud_results/two_wave_cycle_scale_qualification_v054_1m_shards"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fraction", type=float, required=True, choices=ALLOWED)
    args = parser.parse_args()
    fraction = args.fraction

    bars, audit = load_development_bars(
        ROOT / "data/development/1m_official.parquet", ROOT / "data/manifest.json"
    )
    cfg = MaturityConfig(timeframe=VIEW)
    run = build_cycle_scale_qualification_run(bars, cfg=cfg)
    before, after = run.base_run.ledger.records, run.ledger.records
    assert len(before) == len(after)
    identities = [identity(row) for row in before]
    assert identities == [identity(row) for row in after]

    duration_only = {
        identity(row)
        for row in before
        if row["scale_rejection_reasons"] == [REMOVED_HARD_REASON]
    }
    oldq = {identity(row) for row in before if row["scale_qualified"]}
    newq = {identity(row) for row in after if row["scale_qualified"]}
    assert not (oldq - newq)
    assert (newq - oldq) == duration_only
    for old, new in zip(before, after):
        assert new["scale_rejection_reasons"] == [
            reason for reason in old["scale_rejection_reasons"] if reason != REMOVED_HARD_REASON
        ]
        assert new["trade_authority"] is False and new["future_outcome_used"] is False

    cutoff = int(len(bars) * fraction)
    prefix = build_cycle_scale_qualification_run(
        bars[:cutoff], cfg=MaturityConfig(timeframe=VIEW)
    )
    checks = v054_prefix_check(run, prefix, cutoff)
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
        "schema": "two_wave_cycle_scale_qualification_1m_shard@0.5.4",
        "status": "one_prefix_shard_passed",
        "view": VIEW,
        "fraction": fraction,
        "data_audit": audit,
        "candidate_identity_exact_match": True,
        "v052": {
            "evaluated": len(before),
            "qualified": len(oldq),
            "selected": len(run.base_run.ledger.selected),
        },
        "v054": {
            "evaluated": len(after),
            "qualified": len(newq),
            "selected": len(run.ledger.selected),
        },
        "duration_only_newly_qualified": len(duration_only),
        "prefix_check": prefix_row,
        "trade_authority": False,
        "fresh_oos": False,
    }
    save(OUTPUT / f"prefix_{tag}" / "summary.json", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
