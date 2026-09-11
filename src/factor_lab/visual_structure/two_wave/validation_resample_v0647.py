"""Deterministic session-aware 1m -> five harmless 5m offset views for v0.6.47.

This module is validation infrastructure only.  Its semantics must reproduce the
shipped 2015-2020 five-offset development products exactly before any external
2024+ morphology result may be inspected.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

VIEWS = tuple(f"5m_offset_{i}" for i in range(5))
PRICE_FIELDS = ("open", "high", "low", "close")


def _minute_index(local: pd.Series) -> pd.Series:
    """Return 0..119 index inside the two canonical A-share minute sessions.

    Input timestamps are bar-end instants converted to Asia/Shanghai.  Morning
    one-minute bars end 09:31..11:30; afternoon bars end 13:01..15:00.
    Rows outside those intervals fail closed.
    """
    minute = local.dt.hour * 60 + local.dt.minute
    morning0 = 9 * 60 + 31
    afternoon0 = 13 * 60 + 1
    out = pd.Series(np.full(len(local), -1, dtype=np.int64), index=local.index)
    morning = (minute >= morning0) & (minute <= 11 * 60 + 30)
    afternoon = (minute >= afternoon0) & (minute <= 15 * 60)
    out.loc[morning] = (minute.loc[morning] - morning0).astype(np.int64)
    out.loc[afternoon] = (minute.loc[afternoon] - afternoon0).astype(np.int64)
    if (out < 0).any() or (out > 119).any():
        bad = local.loc[(out < 0) | (out > 119)].astype(str).head(5).tolist()
        raise ValueError(f"timestamps outside canonical A-share minute sessions: {bad}")
    return out


def resample_five_minute_offset(frame: pd.DataFrame, offset: int) -> pd.DataFrame:
    """Aggregate one frozen 1m frame into one offset view.

    For each trading day and AM/PM session, use fixed wall-clock minute slots.
    A 5m bar exists only when all five consecutive source minutes for its bin
    are present.  Partial bins and session-edge fragments are discarded.
    Output timestamp is the final source bar-end timestamp.
    """
    if isinstance(offset, bool) or not isinstance(offset, int) or offset not in range(5):
        raise ValueError("offset must be integer 0..4")
    required = {"timestamp", "trading_day", *PRICE_FIELDS}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"missing required columns: {missing}")
    if frame.empty:
        raise ValueError("empty 1m frame")

    x = frame.loc[:, ["timestamp", "trading_day", *PRICE_FIELDS]].copy()
    stamp = pd.to_datetime(x["timestamp"], utc=True, errors="raise")
    if stamp.isna().any() or stamp.duplicated().any() or not stamp.is_monotonic_increasing:
        raise ValueError("1m timestamps must be ordered, unique and non-null")
    prices = x.loc[:, PRICE_FIELDS].to_numpy(dtype=float)
    if not np.isfinite(prices).all():
        raise ValueError("finite OHLC required")

    local = stamp.dt.tz_convert("Asia/Shanghai")
    local_day = local.dt.strftime("%Y-%m-%d")
    trading_day = pd.to_datetime(x["trading_day"], errors="raise").dt.strftime("%Y-%m-%d")
    if not np.array_equal(local_day.to_numpy(), trading_day.to_numpy()):
        raise ValueError("trading_day disagrees with Shanghai timestamp date")

    idx = _minute_index(local)
    session = np.where(local.dt.hour < 12, "AM", "PM")
    work = x.copy()
    work["_stamp"] = stamp
    work["_day"] = trading_day
    work["_session"] = session
    work["_minute"] = idx.to_numpy()

    # Offset-r bins start at source minute index r. A full 5-row bin has fixed
    # expected minute indices r+5g .. r+5g+4. Session-edge fragments vanish.
    eligible = work["_minute"] >= offset
    work = work.loc[eligible].copy()
    work["_group"] = ((work["_minute"] - offset) // 5).astype(np.int64)

    rows: list[dict] = []
    for (day, sess, group), g in work.groupby(["_day", "_session", "_group"], sort=False):
        start = offset + 5 * int(group)
        expected = list(range(start, start + 5))
        if expected[-1] > 119:
            continue
        actual = g["_minute"].astype(int).tolist()
        if actual != expected:
            # Native validation semantics require a complete source five-pack;
            # missing/duplicated source minutes do not create a partial 5m bar.
            continue
        rows.append(
            {
                "timestamp": g["_stamp"].iloc[-1],
                "trading_day": str(day),
                "open": float(g["open"].iloc[0]),
                "high": float(g["high"].max()),
                "low": float(g["low"].min()),
                "close": float(g["close"].iloc[-1]),
            }
        )
    out = pd.DataFrame(rows, columns=["timestamp", "trading_day", *PRICE_FIELDS])
    if not out.empty and (out["timestamp"].duplicated().any() or not out["timestamp"].is_monotonic_increasing):
        raise AssertionError("resampled timestamps are not unique/increasing")
    return out


def exact_ohlc_timestamp_equivalence(candidate: pd.DataFrame, reference: pd.DataFrame) -> dict:
    """Demand row-for-row timestamp + OHLC equality; report the first mismatch."""
    required = ["timestamp", *PRICE_FIELDS]
    for name, frame in (("candidate", candidate), ("reference", reference)):
        missing = [c for c in required if c not in frame.columns]
        if missing:
            raise ValueError(f"{name} missing {missing}")

    c = candidate.loc[:, required].copy()
    r = reference.loc[:, required].copy()
    c["timestamp"] = pd.to_datetime(c["timestamp"], utc=True, errors="raise")
    r["timestamp"] = pd.to_datetime(r["timestamp"], utc=True, errors="raise")
    same_rows = len(c) == len(r)
    ts_equal = bool(same_rows and np.array_equal(c["timestamp"].astype("int64").to_numpy(), r["timestamp"].astype("int64").to_numpy()))
    price_equal = {}
    max_abs = {}
    for field in PRICE_FIELDS:
        if same_rows:
            ca = c[field].to_numpy(dtype=float)
            ra = r[field].to_numpy(dtype=float)
            price_equal[field] = bool(np.array_equal(ca, ra))
            max_abs[field] = float(np.max(np.abs(ca - ra))) if len(ca) else 0.0
        else:
            price_equal[field] = False
            max_abs[field] = None

    exact = bool(same_rows and ts_equal and all(price_equal.values()))
    first_mismatch = None
    if not exact:
        n = min(len(c), len(r))
        for i in range(n):
            if c["timestamp"].iloc[i] != r["timestamp"].iloc[i] or any(float(c[f].iloc[i]) != float(r[f].iloc[i]) for f in PRICE_FIELDS):
                first_mismatch = {
                    "row": i,
                    "candidate": {k: str(c[k].iloc[i]) if k == "timestamp" else float(c[k].iloc[i]) for k in required},
                    "reference": {k: str(r[k].iloc[i]) if k == "timestamp" else float(r[k].iloc[i]) for k in required},
                }
                break
        if first_mismatch is None and len(c) != len(r):
            first_mismatch = {"row": n, "reason": "length_mismatch"}
    return {
        "exact": exact,
        "candidate_rows": int(len(c)),
        "reference_rows": int(len(r)),
        "timestamp_equal": ts_equal,
        "price_equal": price_equal,
        "max_abs_price_difference": max_abs,
        "first_mismatch": first_mismatch,
    }
