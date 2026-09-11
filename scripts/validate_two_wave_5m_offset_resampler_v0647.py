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


def source_context(one: pd.DataFrame, timestamp: str | None) -> list[dict]:
    if not timestamp:
        return []
    target = pd.Timestamp(timestamp)
    stamp = pd.to_datetime(one["timestamp"], utc=True, errors="raise")
    mask = (stamp >= target - pd.Timedelta(minutes=8)) & (stamp <= target + pd.Timedelta(minutes=2))
    rows = one.loc[mask, ["timestamp", "open", "high", "low", "close"]].copy()
    rows["timestamp"] = pd.to_datetime(rows["timestamp"], utc=True).astype(str)
    return rows.to_dict("records")


def timestamp_set_delta(candidate: pd.DataFrame, reference: pd.DataFrame) -> dict:
    c = set(pd.to_datetime(candidate["timestamp"], utc=True).astype("int64").tolist())
    r = set(pd.to_datetime(reference["timestamp"], utc=True).astype("int64").tolist())
    def to_iso(value: int) -> str:
        return pd.Timestamp(value, unit="ns", tz="UTC").isoformat()
    return {
        "candidate_only_count": len(c - r),
        "reference_only_count": len(r - c),
        "candidate_only_first": [to_iso(x) for x in sorted(c - r)[:10]],
        "reference_only_first": [to_iso(x) for x in sorted(r - c)[:10]],
    }


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
        if not result["exact"]:
            mismatch = result.get("first_mismatch") or {}
            ts = None
            if isinstance(mismatch.get("reference"), dict):
                ts = mismatch["reference"].get("timestamp")
            result["timestamp_set_delta"] = timestamp_set_delta(candidate, ref)
            result["source_context"] = source_context(one, ts)
            result["reference_head"] = (
                ref.loc[:, ["timestamp", "open", "high", "low", "close"]]
                .head(3)
                .assign(timestamp=lambda x: pd.to_datetime(x["timestamp"], utc=True).astype(str))
                .to_dict("records")
            )
            result["candidate_head"] = (
                candidate.loc[:, ["timestamp", "open", "high", "low", "close"]]
                .head(3)
                .assign(timestamp=lambda x: pd.to_datetime(x["timestamp"], utc=True).astype(str))
                .to_dict("records")
            )
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
