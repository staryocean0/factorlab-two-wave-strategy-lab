"""Read immutable, manifest-backed development bars without filling or resampling."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def audit_frame(frame: pd.DataFrame) -> dict[str, Any]:
    """Fail closed on input defects; retain clock and missing-volume caveats."""
    required = {
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "symbol",
        "trading_day",
        "export_view_id",
        "export_frequency",
        "package_data_role",
        "available_at",
    }
    absent = sorted(required.difference(frame.columns))
    if absent:
        raise ValueError(f"missing required columns: {absent}")
    if frame.empty:
        raise ValueError("empty bar view")
    stamp = frame["timestamp"]
    if not isinstance(stamp.dtype, pd.DatetimeTZDtype) or str(stamp.dt.tz) != "UTC":
        raise ValueError("timestamp must be timezone-aware UTC, not reinterpreted local time")
    if stamp.isna().any() or stamp.duplicated().any() or not stamp.is_monotonic_increasing:
        raise ValueError("timestamps must be non-null, unique and strictly increasing; no implicit sort")
    prices = frame[["open", "high", "low", "close"]].to_numpy(dtype=float)
    if not np.isfinite(prices).all() or not (prices > 0).all():
        raise ValueError("OHLC must be finite and positive; missing prices are not filled")
    o, h, low, c = prices.T
    if ((low > np.minimum(o, c)) | (h < np.maximum(o, c)) | (low > h)).any():
        raise ValueError("invalid OHLC ordering")
    if set(frame["symbol"].unique()) != {"000852.SH"}:
        raise ValueError("this workflow accepts only the shipped CSI1000 index signal data")
    if set(frame["package_data_role"].unique()) != {"development_material"}:
        raise ValueError("data role must be development_material")
    days = pd.to_datetime(frame["trading_day"], errors="raise")
    if days.isna().any() or (days < "2015-01-05").any() or (days > "2020-12-31").any():
        raise ValueError("rows outside the declared 2015-2020 development interval")
    local_days = stamp.dt.tz_convert("Asia/Shanghai").dt.strftime("%Y-%m-%d")
    if not (local_days.to_numpy() == days.dt.strftime("%Y-%m-%d").to_numpy()).all():
        raise ValueError("trading_day disagrees with the Shanghai bar-end calendar date")
    if frame["export_view_id"].nunique(dropna=False) != 1 or frame["export_frequency"].nunique(dropna=False) != 1:
        raise ValueError("each input must be one supplied DataHub bar view")
    if "bar_end_shanghai" in frame:
        local = pd.to_datetime(frame["bar_end_shanghai"], utc=True)
        if not local.equals(stamp):
            raise ValueError("bar_end_shanghai is not the same instant as timestamp")
    availability = pd.to_datetime(frame["available_at"], utc=True, errors="raise")
    if availability.isna().any():
        raise ValueError("available_at must be present and parseable")
    delays = (availability - stamp).dt.total_seconds() / 60
    if (delays < 0).any():
        raise ValueError("available_at precedes bar end")
    volume_missing = int(frame["volume"].isna().sum()) if "volume" in frame else len(frame)
    gaps = stamp.diff().dt.total_seconds().dropna() / 60

    def quantiles(values):
        return {str(q): float(values.quantile(q)) for q in (0, 0.5, 0.9, 0.99, 1)}

    return {
        "rows": len(frame),
        "columns": len(frame.columns),
        "instrument": "000852.SH",
        "view_id": str(frame["export_view_id"].iloc[0]),
        "export_frequency": str(frame["export_frequency"].iloc[0]),
        "minimum_trading_day": days.min().strftime("%Y-%m-%d"),
        "maximum_trading_day": days.max().strftime("%Y-%m-%d"),
        "rows_by_year": {str(k): int(v) for k, v in days.dt.year.value_counts().sort_index().items()},
        "timestamp_timezone": "UTC",
        "timestamp_semantics": "bar_end",
        "volume_missing_rows": volume_missing,
        "invalid_ohlc_rows": 0,
        "duplicate_timestamp_rows": 0,
        "rows_after_2020": 0,
        "available_at_after_bar_end_rows": int((delays > 0).sum()),
        "availability_delay_minutes_quantiles": quantiles(delays),
        "adjacent_timestamp_gap_minutes_quantiles": quantiles(gaps) if len(gaps) else None,
        "historical_bar_end_realtime_availability_proven": False,
        "availability_note": (
            "Replay is bar-order morphology. available_at is preserved; bar-end realtime availability and execution are not asserted."
        ),
        "gaps_note": "Gaps are observed, not filled; no exchange calendar completeness claim is made.",
        "daily_view_note": "daily_proxy views select supplied intraday bars; their OHLC is not full-day OHLC.",
        "data_role": "development_material",
        "local_resampling_performed": False,
        "trade_fill_authority": False,
        "fresh_oos": False,
    }


def load_development_bars(
    path: str | Path,
    manifest_path: str | Path,
    *,
    max_bars: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Verify an unchanged shipped product before exposing any price rows."""
    path, manifest_path = Path(path), Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    matches = [entry for entry in manifest["products"] if Path(entry["path"]).name == path.name]
    if len(matches) != 1:
        raise ValueError("input must identify exactly one shipped manifest product")
    entry = matches[0]
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != entry["sha256"] or len(payload) != entry["file_bytes"]:
        raise ValueError("input bytes do not match the frozen data manifest")
    frame = pd.read_parquet(path)
    audit = audit_frame(frame)
    if len(frame) != entry["row_count"] or len(frame.columns) != entry["column_count"]:
        raise ValueError("input shape does not match the frozen data manifest")
    if audit["minimum_trading_day"] != entry["minimum_trading_day"] or audit["maximum_trading_day"] != entry["maximum_trading_day"]:
        raise ValueError("input date coverage does not match the frozen data manifest")
    if max_bars is not None:
        if max_bars <= 0:
            raise ValueError("max_bars must be positive")
        frame = frame.iloc[:max_bars]
    records: list[dict[str, Any]] = []
    for row in frame.to_dict("records"):
        records.append(
            {
                "timestamp": row["timestamp"].isoformat(),
                **{field: float(row[field]) for field in ("open", "high", "low", "close")},
                "volume": None if pd.isna(row.get("volume")) else float(row["volume"]),
                "available_at": pd.Timestamp(row["available_at"]).isoformat(),
                "timestamp_source_serialized": row.get("timestamp_source_serialized"),
                "trading_day": str(row["trading_day"]),
            }
        )
    audit.update(
        {
            "path": entry["path"],
            "file_bytes": len(payload),
            "sha256": digest,
            "git_blob_sha": hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest(),
            "manifest_verified": True,
            "processed_rows": len(records),
            "processed_minimum_timestamp": records[0]["timestamp"],
            "processed_maximum_timestamp": records[-1]["timestamp"],
            "max_bars": max_bars,
        }
    )
    return records, audit
