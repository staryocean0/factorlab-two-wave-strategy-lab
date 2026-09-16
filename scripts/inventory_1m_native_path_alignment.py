#!/usr/bin/env python3
"""Inventory-only audit for native 1m data and timestamp alignment to official 5m endpoints.

No future-return or signal/outcome calculations are performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ONE_MIN = ROOT / "data" / "development" / "1m_official.parquet"
FIVE_MIN = ROOT / "data" / "development" / "5m_offset_0.parquet"
ONE_MIN_SHA = "755217afce9dec383e48cd46d591402fa90dc50897abeb3dc7097c9a18a109d4"
FIVE_MIN_SHA = "bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path) -> pd.DataFrame:
    x = pd.read_parquet(path)
    required = {"symbol", "trading_day", "bar_end_shanghai", "close"}
    missing = sorted(required - set(x.columns))
    if missing:
        raise RuntimeError(f"missing required columns: {missing}")
    x = x.copy()
    x["bar_end_shanghai"] = pd.to_datetime(x["bar_end_shanghai"], errors="raise")
    x["trading_day"] = x["trading_day"].astype(str)
    return x


def run(one_min_path: Path = ONE_MIN, five_min_path: Path = FIVE_MIN) -> dict[str, Any]:
    one = _load(one_min_path)
    five = _load(five_min_path)

    one_key = ["symbol", "bar_end_shanghai"]
    five_key = ["symbol", "bar_end_shanghai"]
    one_dups = int(one.duplicated(one_key).sum())
    five_dups = int(five.duplicated(five_key).sum())

    one_sorted = one.sort_values(["symbol", "bar_end_shanghai"]).reset_index(drop=True)
    dt = one_sorted["bar_end_shanghai"].diff()
    same_day = one_sorted["trading_day"].eq(one_sorted["trading_day"].shift(1))
    exact1 = same_day & dt.eq(pd.Timedelta(minutes=1))
    same_day_transitions = int(same_day.sum())
    exact1_transitions = int(exact1.sum())

    daily = one.groupby("trading_day", sort=True).size().astype(int)
    daily_summary = {
        "days": int(len(daily)),
        "min_rows": int(daily.min()),
        "median_rows": float(daily.median()),
        "max_rows": int(daily.max()),
        "p01_rows": float(daily.quantile(0.01)),
        "p99_rows": float(daily.quantile(0.99)),
        "days_with_240_rows": int((daily == 240).sum()),
    }

    one_idx = one.set_index(["symbol", "bar_end_shanghai"], drop=False)
    matched = five[["symbol", "trading_day", "bar_end_shanghai", "close"]].copy()
    matched["one_min_endpoint_present"] = [
        (sym, ts) in one_idx.index for sym, ts in zip(matched["symbol"], matched["bar_end_shanghai"], strict=True)
    ]
    endpoint_present = int(matched["one_min_endpoint_present"].sum())

    # For each official 5m endpoint, verify that endpoint and the four preceding native 1m timestamps exist.
    full_chain = []
    endpoint_close_abs_diff = []
    for row in matched.itertuples(index=False):
        keys = [(row.symbol, row.bar_end_shanghai - pd.Timedelta(minutes=k)) for k in range(5)]
        ok = all(key in one_idx.index for key in keys)
        if ok:
            days = {str(one_idx.loc[key, "trading_day"]) for key in keys}
            ok = days == {str(row.trading_day)}
        full_chain.append(bool(ok))
        if (row.symbol, row.bar_end_shanghai) in one_idx.index:
            one_close = float(one_idx.loc[(row.symbol, row.bar_end_shanghai), "close"])
            endpoint_close_abs_diff.append(abs(float(row.close) - one_close))
    matched["full_native_5x1m_chain"] = full_chain

    aligned_days = matched.groupby("trading_day")["full_native_5x1m_chain"].agg(["sum", "count"])
    aligned_days["fraction"] = aligned_days["sum"] / aligned_days["count"]

    return {
        "schema_id": "factorlab_1m_native_path_alignment_inventory@1.0",
        "inventory_only": True,
        "future_return_read": False,
        "PnL_read": False,
        "BLACKBOX_read": False,
        "post_2020_read": False,
        "one_min": {
            "path": str(one_min_path.relative_to(ROOT)),
            "sha256": sha256(one_min_path),
            "sha256_expected": ONE_MIN_SHA,
            "rows": int(len(one)),
            "columns": [str(c) for c in one.columns],
            "symbol_values": sorted(one["symbol"].astype(str).unique().tolist()),
            "min_day": str(one["trading_day"].min()),
            "max_day": str(one["trading_day"].max()),
            "duplicate_symbol_timestamp_rows": one_dups,
            "same_day_transitions": same_day_transitions,
            "exact_1m_same_day_transitions": exact1_transitions,
            "exact_1m_transition_fraction": float(exact1_transitions / same_day_transitions) if same_day_transitions else None,
            "daily_rows": daily_summary,
        },
        "five_min_reference": {
            "path": str(five_min_path.relative_to(ROOT)),
            "sha256": sha256(five_min_path),
            "sha256_expected": FIVE_MIN_SHA,
            "rows": int(len(five)),
            "duplicate_symbol_timestamp_rows": five_dups,
        },
        "alignment": {
            "five_min_endpoints": int(len(matched)),
            "one_min_endpoint_present": endpoint_present,
            "endpoint_presence_fraction": float(endpoint_present / len(matched)) if len(matched) else None,
            "full_native_5x1m_chain_count": int(np.sum(full_chain)),
            "full_native_5x1m_chain_fraction": float(np.mean(full_chain)) if full_chain else None,
            "days_all_5m_endpoints_have_full_chain": int((aligned_days["fraction"] == 1.0).sum()),
            "days_with_any_missing_chain": int((aligned_days["fraction"] < 1.0).sum()),
            "endpoint_close_abs_diff_max": float(max(endpoint_close_abs_diff)) if endpoint_close_abs_diff else None,
            "endpoint_close_abs_diff_nonzero_count": int(np.sum(np.asarray(endpoint_close_abs_diff) > 0.0)),
        },
        "authority": {
            "local_resampling_performed": False,
            "signal_or_outcome_screen_performed": False,
            "production_authority": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
