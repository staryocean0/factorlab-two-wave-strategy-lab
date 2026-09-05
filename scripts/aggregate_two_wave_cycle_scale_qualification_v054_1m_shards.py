#!/usr/bin/env python3
"""Aggregate three frozen v0.5.4 1m prefix shards without running a model."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_two_wave_extremum_ridge_v052 import save

EXPECTED = (0.25, 0.50, 0.75)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "cloud_results/two_wave_cycle_scale_qualification_v054_1m_shards/final_summary.json",
    )
    args = parser.parse_args()

    rows = []
    for path in args.input_root.rglob("summary.json"):
        payload = json.loads(path.read_text())
        if payload.get("schema") == "two_wave_cycle_scale_qualification_1m_shard@0.5.4":
            rows.append(payload)
    rows.sort(key=lambda row: row["fraction"])
    assert tuple(row["fraction"] for row in rows) == EXPECTED, [row["fraction"] for row in rows]
    reference = rows[0]
    for row in rows:
        assert row["candidate_identity_exact_match"] is True
        assert row["v052"] == reference["v052"]
        assert row["v054"] == reference["v054"]
        assert row["duration_only_newly_qualified"] == reference["duration_only_newly_qualified"]
        assert row["prefix_check"]["passed"] is True
        assert row["prefix_check"]["confirmed_rewrite_count"] == 0
        assert row["trade_authority"] is False and row["fresh_oos"] is False

    final = {
        "schema": "two_wave_cycle_scale_qualification_1m_parallel_adjudication@0.5.4",
        "status": "one_minute_results_generated_pending_final_adjudication",
        "view": "1m_official",
        "candidate_identity_exact_match": True,
        "v052": reference["v052"],
        "v054": reference["v054"],
        "duration_only_newly_qualified": reference["duration_only_newly_qualified"],
        "prefix_checks": [row["prefix_check"] for row in rows],
        "prefix_zero_rewrite_count": 3,
        "trade_authority": False,
        "fresh_oos": False,
    }
    save(args.output, final)
    print(json.dumps(final, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
