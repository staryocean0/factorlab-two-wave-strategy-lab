#!/usr/bin/env python3
"""Validate v0.6.47 1m->5m offset construction on 2015-2020 Development only."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.validation_resample_v0647 import (
    VIEWS,
    exact_ohlc_timestamp_equivalence,
    resample_five_minute_offset,
)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    one = pd.read_parquet(ROOT / "data/development/1m_official.parquet")
    results = {}
    all_exact = True
    for offset, view in enumerate(VIEWS):
        ref = pd.read_parquet(ROOT / f"data/development/{view}.parquet")
        candidate = resample_five_minute_offset(one, offset)
        result = exact_ohlc_timestamp_equivalence(candidate, ref)
        results[view] = result
        all_exact = all_exact and bool(result["exact"])
        print(json.dumps({"view": view, **result}, ensure_ascii=False, sort_keys=True), flush=True)

    report = {
        "schema": "two_wave_v0647_resampler_equivalence@1.0",
        "scope": "development_only_2015_2020",
        "all_five_offsets_exact": all_exact,
        "views": results,
        "external_validation_rows_read": 0,
        "validation_score_computed": False,
    }
    (args.output / "resampler_equivalence.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    if not all_exact:
        raise AssertionError("v0647 resampler does not exactly reproduce all five shipped Development offsets")


if __name__ == "__main__":
    main()
