#!/usr/bin/env python3
"""Supply/alignment-only audit for T1 transitory intraday shock theory intake.

This program intentionally does NOT construct or read any post-event reversal /
continuation outcome. It identifies causally completed extreme native 5m bars,
checks their own completed 1m support, and reports supply/alignment metadata only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIVE_MINUTE_PATH = ROOT / "data/development/5m_offset_0.parquet"
ONE_MINUTE_PATH = ROOT / "data/development/1m_official.parquet"
FIVE_MINUTE_SHA256 = "bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48"
ONE_MINUTE_SHA256 = "755217afce9dec383e48cd46d591402fa90dc50897abeb3dc7097c9a18a109d4"
SYMBOL = "000852.SH"
REFERENCE_BARS = 960
EXTREME_Z = 5.0
MINIMUMS = {"BUILD": 150, "CHECK_2019": 50, "CHECK_2020": 50}
RTOL = 1e-12
ATOL = 1e-10


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def robust_z_from_past_window(values: np.ndarray, window: int = REFERENCE_BARS) -> np.ndarray:
    """Causal robust z-score using exactly the preceding `window` observations."""
    values = np.asarray(values, dtype=float)
    out = np.full(values.shape, np.nan, dtype=float)
    for i in range(window, len(values)):
        hist = values[i - window : i]
        if not np.isfinite(hist).all():
            continue
        median = float(np.median(hist))
        mad = float(np.median(np.abs(hist - median)))
        scale = 1.4826 * mad
        if not math.isfinite(scale) or scale <= 0.0:
            continue
        out[i] = (values[i] - median) / scale
    return out


def partition_for_day(day: str) -> str | None:
    if "2015-01-05" <= day <= "2018-12-31":
        return "BUILD"
    if "2019-01-01" <= day <= "2019-12-31":
        return "CHECK_2019"
    if "2020-01-01" <= day <= "2020-12-31":
        return "CHECK_2020"
    return None


def within_bar_retrace_fraction(native_open: float, native_close: float, one_minute_closes: np.ndarray) -> float:
    """Completed-event path symptom available exactly at native 5m close."""
    native_open = float(native_open)
    native_close = float(native_close)
    closes = np.asarray(one_minute_closes, dtype=float)
    if native_open <= 0.0 or native_close <= 0.0 or len(closes) == 0 or np.any(closes <= 0.0):
        raise ValueError("prices must be finite and positive")
    p0 = math.log(native_open)
    terminal = math.log(native_close) - p0
    if terminal == 0.0:
        raise ValueError("zero terminal displacement is not an extreme event")
    sign = 1.0 if terminal > 0.0 else -1.0
    directed = sign * (np.log(closes) - p0)
    peak = float(np.max(directed))
    terminal_directed = abs(float(terminal))
    if not math.isfinite(peak) or peak <= 0.0 or terminal_directed <= 0.0:
        raise ValueError("invalid directed displacement")
    value = max(0.0, peak - terminal_directed) / peak
    return float(min(1.0, max(0.0, value)))


def _timestamp_column(frame: pd.DataFrame) -> str:
    if "bar_end_shanghai" in frame.columns:
        return "bar_end_shanghai"
    if "timestamp" in frame.columns:
        return "timestamp"
    raise RuntimeError("no admitted timestamp column")


def _validate_frame(frame: pd.DataFrame, *, kind: str) -> tuple[pd.DataFrame, str]:
    required = {"symbol", "trading_day", "open", "close"} if kind == "5m" else {"symbol", "trading_day", "close"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise RuntimeError(f"{kind} missing columns: {missing}")
    if set(frame["symbol"].astype(str)) != {SYMBOL}:
        raise RuntimeError(f"{kind} symbol identity mismatch")
    days = frame["trading_day"].astype(str)
    if days.min() < "2015-01-05" or days.max() > "2020-12-31":
        raise RuntimeError(f"{kind} escaped admitted development interval")
    time_col = _timestamp_column(frame)
    out = frame.copy()
    out[time_col] = pd.to_datetime(out[time_col], errors="raise")
    if out[time_col].duplicated().any():
        raise RuntimeError(f"{kind} duplicate timestamps")
    if not out[time_col].is_monotonic_increasing:
        out = out.sort_values(time_col, kind="stable").reset_index(drop=True)
        if out[time_col].duplicated().any() or not out[time_col].is_monotonic_increasing:
            raise RuntimeError(f"{kind} timestamps are not strictly orderable")
    for column in ("open", "close") if kind == "5m" else ("close",):
        numeric = pd.to_numeric(out[column], errors="raise").astype(float)
        if not np.isfinite(numeric.to_numpy()).all() or bool((numeric <= 0.0).any()):
            raise RuntimeError(f"{kind} invalid {column}")
        out[column] = numeric
    out["trading_day"] = out["trading_day"].astype(str)
    return out, time_col


def _minute_day_index(one: pd.DataFrame, time_col: str) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    index: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for day, group in one.groupby("trading_day", sort=False):
        group = group.sort_values(time_col, kind="stable")
        times = group[time_col].to_numpy(dtype="datetime64[ns]")
        closes = group["close"].to_numpy(dtype=float)
        if len(times) != len(np.unique(times)):
            raise RuntimeError(f"1m duplicate timestamps inside {day}")
        index[str(day)] = (times, closes)
    return index


def aligned_one_minute_closes(
    minute_index: dict[str, tuple[np.ndarray, np.ndarray]],
    *,
    day: str,
    native_end: pd.Timestamp,
) -> tuple[np.ndarray | None, str | None]:
    payload = minute_index.get(day)
    if payload is None:
        return None, "missing_trading_day"
    times, closes = payload
    end64 = np.datetime64(native_end.to_datetime64())
    start64 = np.datetime64((native_end - pd.Timedelta(minutes=5)).to_datetime64())
    left = int(np.searchsorted(times, start64, side="right"))
    right = int(np.searchsorted(times, end64, side="right"))
    selected_times = times[left:right]
    selected_closes = closes[left:right]
    if len(selected_times) != 5:
        return None, f"support_count_{len(selected_times)}"
    if len(np.unique(selected_times)) != 5 or np.any(selected_times[1:] <= selected_times[:-1]):
        return None, "support_timestamp_order_or_duplicate"
    return selected_closes.astype(float), None


def _describe(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None, "min": None, "max": None}
    arr = np.asarray(values, dtype=float)
    return {
        "n": int(len(arr)),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p25": float(np.quantile(arr, 0.25)),
        "p75": float(np.quantile(arr, 0.75)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def run_audit(five_path: Path = FIVE_MINUTE_PATH, one_path: Path = ONE_MINUTE_PATH) -> dict[str, Any]:
    actual_five_sha = sha256_file(five_path)
    actual_one_sha = sha256_file(one_path)
    if actual_five_sha != FIVE_MINUTE_SHA256:
        raise RuntimeError(f"5m SHA256 mismatch: {actual_five_sha}")
    if actual_one_sha != ONE_MINUTE_SHA256:
        raise RuntimeError(f"1m SHA256 mismatch: {actual_one_sha}")

    five = pd.read_parquet(five_path, columns=["symbol", "trading_day", "open", "close", "bar_end_shanghai"])
    one = pd.read_parquet(one_path, columns=["symbol", "trading_day", "close", "bar_end_shanghai"])
    five, five_time_col = _validate_frame(five, kind="5m")
    one, one_time_col = _validate_frame(one, kind="1m")

    log_return = np.log(five["close"].to_numpy(dtype=float) / five["open"].to_numpy(dtype=float))
    robust_z = robust_z_from_past_window(log_return, REFERENCE_BARS)
    minute_index = _minute_day_index(one, one_time_col)

    counts: dict[str, dict[str, Any]] = {
        key: {"extreme_events": 0, "aligned_events": 0, "rejections": {}, "retrace_values": []}
        for key in MINIMUMS
    }

    event_indices = np.flatnonzero(np.isfinite(robust_z) & (np.abs(robust_z) >= EXTREME_Z))
    for idx in event_indices:
        day = str(five.iloc[idx]["trading_day"])
        partition = partition_for_day(day)
        if partition is None:
            continue
        bucket = counts[partition]
        bucket["extreme_events"] += 1
        native_end = pd.Timestamp(five.iloc[idx][five_time_col])
        closes, reason = aligned_one_minute_closes(minute_index, day=day, native_end=native_end)
        if reason is not None or closes is None:
            bucket["rejections"][reason or "unknown_alignment_failure"] = bucket["rejections"].get(reason or "unknown_alignment_failure", 0) + 1
            continue
        native_close = float(five.iloc[idx]["close"])
        if not np.isclose(float(closes[-1]), native_close, rtol=RTOL, atol=ATOL):
            reason = "last_1m_close_native_5m_close_mismatch"
            bucket["rejections"][reason] = bucket["rejections"].get(reason, 0) + 1
            continue
        try:
            retrace = within_bar_retrace_fraction(float(five.iloc[idx]["open"]), native_close, closes)
        except ValueError as exc:
            reason = f"invalid_retrace:{type(exc).__name__}"
            bucket["rejections"][reason] = bucket["rejections"].get(reason, 0) + 1
            continue
        bucket["aligned_events"] += 1
        bucket["retrace_values"].append(retrace)

    partitions: dict[str, Any] = {}
    all_pass = True
    for key, minimum in MINIMUMS.items():
        bucket = counts[key]
        passed = int(bucket["aligned_events"]) >= int(minimum)
        all_pass = all_pass and passed
        partitions[key] = {
            "extreme_events": int(bucket["extreme_events"]),
            "aligned_events": int(bucket["aligned_events"]),
            "minimum_aligned_required": int(minimum),
            "supply_pass": bool(passed),
            "rejections": dict(sorted(bucket["rejections"].items())),
            "within_bar_retrace_fraction": _describe(bucket["retrace_values"]),
        }

    return {
        "schema_id": "factorlab_broad_rmr_T1_supply_receipt@1.0",
        "research_identity": "T1_transitory_component_after_extreme_intraday_shock_v1",
        "stage": "supply_and_alignment_only",
        "source_identity": {
            "symbol": SYMBOL,
            "five_minute_path": str(five_path),
            "five_minute_sha256": actual_five_sha,
            "five_minute_rows": int(len(five)),
            "one_minute_path": str(one_path),
            "one_minute_sha256": actual_one_sha,
            "one_minute_rows": int(len(one)),
            "minimum_trading_day": str(min(five["trading_day"].min(), one["trading_day"].min())),
            "maximum_trading_day": str(max(five["trading_day"].max(), one["trading_day"].max())),
        },
        "event_contract": {
            "reference_bars": REFERENCE_BARS,
            "extreme_abs_robust_z": EXTREME_Z,
            "return": "log(close/open)",
            "current_bar_excluded_from_reference": True,
        },
        "partitions": partitions,
        "supply_gate_status": (
            "T1_supply_passed_outcomes_still_sealed_pending_cloud_review_and_separate_authorization"
            if all_pass
            else "T1_current_data_event_supply_insufficient"
        ),
        "post_event_outcomes_read": False,
        "future_return_read": False,
        "reversal_or_continuation_label_read": False,
        "PnL_read": False,
        "post_2020_rows_read": False,
        "outcome_execution_authorized": False,
        "production_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--five-minute", type=Path, default=FIVE_MINUTE_PATH)
    parser.add_argument("--one-minute", type=Path, default=ONE_MINUTE_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_audit(args.five_minute, args.one_minute)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(text)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
