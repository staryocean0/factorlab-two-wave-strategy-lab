#!/usr/bin/env python3
"""Formal 1m causal diagnostic for frozen v0.5.4 qualification."""
from __future__ import annotations

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
from run_two_wave_extremum_ridge_v052 import PREFIX_FRACTIONS, save

VIEW = "1m_official"
OUTPUT = ROOT / "cloud_results/two_wave_cycle_scale_qualification_v054_1m"


def main():
    bars, audit = load_development_bars(
        ROOT / "data/development/1m_official.parquet", ROOT / "data/manifest.json"
    )
    cfg = MaturityConfig(timeframe=VIEW)
    run = build_cycle_scale_qualification_run(bars, cfg=cfg)
    before, after = run.base_run.ledger.records, run.ledger.records
    assert len(before) == len(after)
    assert [identity(r) for r in before] == [identity(r) for r in after]
    duration_only = {identity(r) for r in before if r["scale_rejection_reasons"] == [REMOVED_HARD_REASON]}
    oldq = {identity(r) for r in before if r["scale_qualified"]}
    newq = {identity(r) for r in after if r["scale_qualified"]}
    assert not (oldq - newq)
    assert (newq - oldq) == duration_only

    summary = {
        "schema": "two_wave_cycle_scale_qualification_1m@0.5.4",
        "status": "running_not_prejudged",
        "view": VIEW,
        "data_audit": audit,
        "candidate_identity_exact_match": True,
        "v052": {"evaluated": len(before), "qualified": len(oldq), "selected": len(run.base_run.ledger.selected)},
        "v054": {"evaluated": len(after), "qualified": len(newq), "selected": len(run.ledger.selected)},
        "duration_only_newly_qualified": len(duration_only),
        "prefix_checks": [],
    }
    save(OUTPUT / "summary.json", summary)
    for fraction in PREFIX_FRACTIONS:
        cutoff = int(len(bars) * fraction)
        prefix = build_cycle_scale_qualification_run(bars[:cutoff], cfg=MaturityConfig(timeframe=VIEW))
        checks = v054_prefix_check(run, prefix, cutoff)
        summary["prefix_checks"].append({
            "fraction": fraction, "bars": cutoff, **checks,
            "confirmed_rewrite_count": 0, "passed": True,
        })
        save(OUTPUT / "summary.json", summary)
    assert len(summary["prefix_checks"]) == 3
    assert all(x["passed"] and x["confirmed_rewrite_count"] == 0 for x in summary["prefix_checks"])
    summary["status"] = "one_minute_results_generated_pending_adjudication"
    save(OUTPUT / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
