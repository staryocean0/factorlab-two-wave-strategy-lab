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


def _jsonable(value):
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return str(value) if not isinstance(value, (str, int, float, bool, type(None))) else value


def frame_rows(frame: pd.DataFrame, mask, columns: list[str]) -> list[dict]:
    rows = []
    for rec in frame.loc[mask, columns].to_dict("records"):
        rows.append({k: _jsonable(v) for k, v in rec.items()})
    return rows


def source_context(one: pd.DataFrame, timestamp: str | None) -> list[dict]:
    if not timestamp:
        return []
    target = pd.Timestamp(timestamp)
    stamp = pd.to_datetime(one["timestamp"], utc=True, errors="raise")
    mask = (stamp >= target - pd.Timedelta(minutes=8)) & (stamp <= target + pd.Timedelta(minutes=2))
    return frame_rows(one, mask, list(one.columns))


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


def first_day_metadata(frame: pd.DataFrame, n: int = 8) -> list[dict]:
    return frame_rows(frame, frame.index.isin(frame.index[:n]), list(frame.columns))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    one = pd.read_parquet(ROOT / "data/development/1m_official.parquet")
    print(json.dumps({
        "development_1m_columns": list(one.columns),
        "development_1m_dtypes": {k: str(v) for k, v in one.dtypes.items()},
        "development_1m_first_rows_full_metadata": first_day_metadata(one),
    }, ensure_ascii=False, sort_keys=True), flush=True)

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
            result["source_context_full_metadata"] = source_context(one, ts)
            result["reference_columns"] = list(ref.columns)
            result["reference_first_rows_full_metadata"] = first_day_metadata(ref, 3)
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
