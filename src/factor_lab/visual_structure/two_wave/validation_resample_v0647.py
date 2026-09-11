"""Deterministic session-aware 1m -> five harmless 5m offset views for v0.6.47.

This module is validation infrastructure only. Its semantics must reproduce the
shipped 2015-2020 five-offset Development products exactly before any external
2024+ morphology result may be inspected.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

VIEWS = tuple(f"5m_offset_{i}" for i in range(5))
PRICE_FIELDS = ("open", "high", "low", "close")


def _minute_index(local: pd.Series) -> pd.Series:
    """Return 0..119 wall-clock index inside each canonical A-share session."""
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


def _group_number(minute_index: int, offset: int) -> int | None:
    """DataHub wall-clock group for one source endpoint.

    The first shifted window includes its explicit left-boundary endpoint:
    offset r>0 uses indices r-1..r+4 (six point observations) for group 0.
    Offset 0 has no 09:30/13:00 source endpoint, so group 0 is 0..4. All later
    groups are non-overlapping five-row endpoint blocks.
    """
    m = int(minute_index)
    r = int(offset)
    first_start = max(0, r - 1)
    first_end = r + 4
    if m < first_start:
        return None
    if m <= first_end:
        return 0
    return 1 + (m - (r + 5)) // 5


def _group_endpoint(group: int, offset: int) -> int:
    return int(offset) + 4 + 5 * int(group)


def resample_five_minute_offset(frame: pd.DataFrame, offset: int) -> pd.DataFrame:
    """Aggregate a frozen 1m frame with DataHub wall-clock offset semantics.

    Bins are fixed by session wall-clock endpoints. Causal flat-fill rows keep
    the clock complete but are excluded from OHLC aggregation. A bin is emitted
    when at least one non-flat source observation exists; timestamp remains the
    nominal endpoint. The first shifted bin includes its left-boundary endpoint.
    """
    if isinstance(offset, bool) or not isinstance(offset, int) or offset not in range(5):
        raise ValueError("offset must be integer 0..4")
    required = {"timestamp", "trading_day", "causal_flat_fill", *PRICE_FIELDS}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"missing required columns: {missing}")
    if frame.empty:
        raise ValueError("empty 1m frame")

    keep = ["timestamp", "trading_day", "causal_flat_fill", *PRICE_FIELDS]
    for optional in ("amount", "volume"):
        if optional in frame.columns:
            keep.append(optional)
    x = frame.loc[:, keep].copy()
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
    work["_group"] = [_group_number(int(m), offset) for m in work["_minute"]]
    work = work.loc[work["_group"].notna()].copy()
    work["_group"] = work["_group"].astype(np.int64)

    rows: list[dict] = []
    for (day, sess, group), g in work.groupby(["_day", "_session", "_group"], sort=False):
        endpoint = _group_endpoint(int(group), offset)
        if endpoint > 119:
            continue
        endpoint_rows = g.loc[g["_minute"] == endpoint]
        if len(endpoint_rows) != 1:
            raise ValueError(f"missing or duplicate nominal endpoint for {day} {sess} group {group}")
        real = g.loc[~g["causal_flat_fill"].astype(bool)]
        if real.empty:
            continue
        row = {
            "timestamp": endpoint_rows["_stamp"].iloc[0],
            "trading_day": str(day),
            "open": float(real["open"].iloc[0]),
            "high": float(real["high"].max()),
            "low": float(real["low"].min()),
            "close": float(real["close"].iloc[-1]),
        }
        if "amount" in real.columns:
            row["amount"] = float(real["amount"].fillna(0.0).sum())
        if "volume" in real.columns:
            values = real["volume"]
            row["volume"] = None if values.isna().all() else float(values.fillna(0.0).sum())
        rows.append(row)

    columns = ["timestamp", "trading_day", *PRICE_FIELDS]
    for optional in ("amount", "volume"):
        if optional in x.columns:
            columns.append(optional)
    out = pd.DataFrame(rows, columns=columns)
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
