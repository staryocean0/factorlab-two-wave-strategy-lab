#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CL-20260907-004 identity diagnostic.

Uses DataHub's committed assign_intraday_bucket_minute against the frozen
cn_index 1m dataset_version. Does not write replacement 5m products and does
not read 2021+.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

from datahub.storage.query.session_offset_contract import (
    PERIOD_MINUTES,
    SESSION_OFFSET_CONTRACT_ID,
    assign_intraday_bucket_minute,
    construction_fields,
    hhmm_to_minute,
    minute_to_hhmm,
    normalize_session_offset_request,
)

OUT = Path(__file__).resolve().parent
FROZEN_DIR = Path(
    "/home/starryocean/桌面/量化/factorlab-two-wave-strategy-lab/data/development"
)
LAKE_1M = Path(
    "/home/starryocean/桌面/量化/unified_datahub/.runtime/live/lake/bars/"
    "dataset_version=bars_cn_index_1m_raw_canonical_market_index_baidu_3s_"
    "20000714_20260821_factorlab_unified_missing_day_repaired_v8_20260824/"
    "instrument_type=market_index"
)
EXPECTED_VERSION = (
    "bars_cn_index_1m_raw_canonical_market_index_baidu_3s_20000714_20260821_"
    "factorlab_unified_missing_day_repaired_v8_20260824"
)
SYMBOL = "000852.SH"
START_DAY = "2015-01-05"
END_DAY = "2020-12-31"
FROZEN_COUNTS = {
    0: 70114,
    1: 67192,
    2: 67192,
    3: 67193,
    4: 67191,
}
SAMPLE_DAYS = ("2015-01-05", "2020-12-31")
SESSION_MINUTES = list(range(570, 691)) + list(range(780, 901))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def intended_minutes(close_minute: int, offset: int) -> list[int]:
    return [
        minute
        for minute in SESSION_MINUTES
        if assign_intraday_bucket_minute(
            minute, period_minutes=5, offset_minutes=offset
        )
        == close_minute
    ]


def load_frozen(offset: int):
    path = FROZEN_DIR / f"5m_offset_{offset}.parquet"
    table = pq.read_table(path)
    df = table.to_pandas()
    labels = set(df["timestamp_source_serialized"].astype(str))
    by_day = defaultdict(list)
    for rec in df[
        ["timestamp_source_serialized", "trading_day", "open", "high", "low", "close"]
    ].itertuples(index=False, name=None):
        by_day[str(rec[1])].append(
            {
                "label": str(rec[0]),
                "open": rec[2],
                "high": rec[3],
                "low": rec[4],
                "close": rec[5],
            }
        )
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "rows": int(len(df)),
        "labels": labels,
        "by_day": by_day,
        "data_contract": sorted(df["data_contract"].astype(str).unique().tolist()),
        "source_kind": sorted(df["source_kind"].astype(str).unique().tolist()),
        "dataset_version": sorted(df["dataset_version"].astype(str).unique().tolist()),
        "source_minute_count_all_null": bool(df["source_minute_count"].isna().all()),
    }


def main() -> None:
    months = [
        f"{year}-{month:02d}"
        for year in range(2015, 2021)
        for month in range(1, 13)
    ]
    files = [
        str(LAKE_1M / f"trading_month={month}" / "*.parquet")
        for month in months
        if (LAKE_1M / f"trading_month={month}").exists()
    ]
    con = duckdb.connect()
    src = con.execute(
        """
        SELECT timestamp, trading_day, open, high, low, close, volume, amount,
               source_kind, dataset_version, available_at
        FROM read_parquet(?, hive_partitioning=true, union_by_name=true)
        WHERE symbol = ?
          AND trading_day BETWEEN ? AND ?
          AND dataset_version = ?
        ORDER BY timestamp
        """,
        [files, SYMBOL, START_DAY, END_DAY, EXPECTED_VERSION],
    ).fetchdf()

    source_identity = {
        "symbol": SYMBOL,
        "role": "development_material_source_only",
        "date_range": [START_DAY, END_DAY],
        "dataset_version_filter": EXPECTED_VERSION,
        "lake_path": str(LAKE_1M),
        "source_rows": int(len(src)),
        "source_kind_values": sorted(src["source_kind"].astype(str).unique().tolist()),
        "dataset_version_values": sorted(
            src["dataset_version"].astype(str).unique().tolist()
        ),
        "min_timestamp": None if src.empty else str(src["timestamp"].min()),
        "max_timestamp": None if src.empty else str(src["timestamp"].max()),
        "unique_trading_days": int(src["trading_day"].nunique()) if not src.empty else 0,
        "future_2021_plus_rows_loaded": 0,
    }

    occupancy = {offset: defaultdict(list) for offset in range(5)}
    derived_labels = {offset: set() for offset in range(5)}
    ohlc = {offset: {} for offset in range(5)}
    for rec in src.itertuples(index=False):
        ts = str(rec.timestamp)
        day = str(rec.trading_day)
        minute = hhmm_to_minute(ts[11:16])
        for offset in range(5):
            bucket = assign_intraday_bucket_minute(
                minute, period_minutes=5, offset_minutes=offset
            )
            if bucket is None:
                continue
            label = f"{day}T{minute_to_hhmm(bucket)}:00Z"
            derived_labels[offset].add(label)
            occupancy[offset][label].append(ts)
            bucket_ohlc = ohlc[offset].setdefault(
                label,
                {
                    "open": rec.open,
                    "high": rec.high,
                    "low": rec.low,
                    "close": rec.close,
                    "n": 0,
                },
            )
            if bucket_ohlc["n"] == 0:
                bucket_ohlc["open"] = rec.open
            bucket_ohlc["high"] = max(bucket_ohlc["high"], rec.high)
            bucket_ohlc["low"] = min(bucket_ohlc["low"], rec.low)
            bucket_ohlc["close"] = rec.close
            bucket_ohlc["n"] += 1

    view_stats = {}
    frozen = {}
    for offset in range(5):
        frozen[offset] = load_frozen(offset)
        derived = derived_labels[offset]
        expected = frozen[offset]["labels"]
        counts = [len(v) for v in occupancy[offset].values()]
        ohlc_mismatch = 0
        compared = 0
        for label, derived_bar in ohlc[offset].items():
            day = label[:10]
            matches = [
                item for item in frozen[offset]["by_day"].get(day, []) if item["label"] == label
            ]
            if not matches:
                continue
            compared += 1
            frozen_bar = matches[0]
            if any(
                abs(float(derived_bar[field]) - float(frozen_bar[field])) > 1e-8
                for field in ("open", "high", "low", "close")
            ):
                ohlc_mismatch += 1
        view_stats[f"5m_offset_{offset}"] = {
            "frozen_rows": frozen[offset]["rows"],
            "frozen_expected_rows": FROZEN_COUNTS[offset],
            "frozen_row_count_match": frozen[offset]["rows"] == FROZEN_COUNTS[offset],
            "derived_nonzero_occupancy_labels": len(derived),
            "labels_only_in_frozen": sorted(expected - derived)[:20],
            "labels_only_in_derived": sorted(derived - expected)[:20],
            "n_labels_only_in_frozen": len(expected - derived),
            "n_labels_only_in_derived": len(derived - expected),
            "occupancy_min": min(counts) if counts else None,
            "occupancy_max": max(counts) if counts else None,
            "occupancy_mean": (sum(counts) / len(counts)) if counts else None,
            "full_intended_occupancy_6_or_5": {
                "n_bars": len(counts),
                "n_with_6": sum(c == 6 for c in counts),
                "n_with_5": sum(c == 5 for c in counts),
                "n_other": sum(c not in {5, 6} for c in counts),
            },
            "ohlc_compared_matching_labels": compared,
            "ohlc_mismatch_matching_labels": ohlc_mismatch,
            "frozen_data_contract": frozen[offset]["data_contract"],
            "frozen_source_kind": frozen[offset]["source_kind"],
            "frozen_dataset_version": frozen[offset]["dataset_version"],
            "frozen_source_minute_count_all_null": frozen[offset][
                "source_minute_count_all_null"
            ],
            "frozen_sha256": frozen[offset]["sha256"],
        }

    samples = []
    for day in SAMPLE_DAYS:
        day_src = [str(ts) for ts in src.loc[src["trading_day"] == day, "timestamp"]]
        present = {hhmm_to_minute(ts[11:16]) for ts in day_src}
        next_day_src = src.loc[src["trading_day"] > day, "trading_day"]
        next_day = None if next_day_src.empty else str(next_day_src.min())
        for offset in range(5):
            request = normalize_session_offset_request(
                frequency="5m", session_offset_minutes=offset
            )
            labels_for_day = sorted(
                item["label"] for item in frozen[offset]["by_day"].get(day, [])
            )
            if not labels_for_day:
                continue
            picks = [
                ("first_complete_morning", labels_for_day[0]),
                ("last_complete_before_lunch", next(x for x in reversed(labels_for_day) if x[11:13] < "13")),
                ("first_complete_after_lunch", next(x for x in labels_for_day if x[11:13] >= "13")),
                ("last_complete_afternoon", labels_for_day[-1]),
            ]
            for name, label in picks:
                close_minute = hhmm_to_minute(label[11:16])
                intended = intended_minutes(close_minute, offset)
                actual = occupancy[offset].get(label, [])
                meta = construction_fields(
                    request, trading_day=day, bar_close_minute=close_minute
                )
                samples.append(
                    {
                        "day": day,
                        "offset": offset,
                        "spot": name,
                        "frozen_label": label,
                        "construction_contract": request.construction_contract,
                        "uses_official_contract": request.uses_official_contract,
                        "intended_support_1m_end_labels": [
                            f"{day}T{minute_to_hhmm(m)}:00Z" for m in intended
                        ],
                        "intended_count": len(intended),
                        "actual_source_timestamps": actual,
                        "actual_source_minute_count": len(actual),
                        "missing_intended_minutes": [
                            f"{day}T{minute_to_hhmm(m)}:00Z"
                            for m in intended
                            if m not in present
                        ],
                        "bar_open_ts_metadata": meta.get("bar_open_ts"),
                        "bar_close_ts_metadata": meta.get("bar_close_ts"),
                        "first_tradable_slot_metadata": meta.get("first_tradable_slot"),
                        "frozen_available_at_note": "frozen/lake available_at is 15:30+08:00 session batch field, not first_tradable_slot",
                        "min_actual_source": actual[0] if actual else None,
                        "max_actual_source": actual[-1] if actual else None,
                        "bar_open_ts_equals_min_actual_source": (
                            meta.get("bar_open_ts") == actual[0] if actual else None
                        ),
                    }
                )
            samples.append(
                {
                    "day": day,
                    "offset": offset,
                    "spot": "overnight_transition_to_next_trading_day",
                    "last_bar_this_day": labels_for_day[-1],
                    "next_trading_day": next_day,
                    "next_day_first_bar": (
                        frozen[offset]["by_day"].get(next_day, [{}])[0].get("label")
                        if next_day in frozen[offset]["by_day"]
                        else None
                    ),
                    "note": "CN-A/index session windows contain no overnight minutes; bars never cross 15:00 to next 09:30.",
                }
            )

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "route": "A_plus_C_with_identity_diagnostic_not_replacement_export",
        "period_minutes": PERIOD_MINUTES["5m"],
        "construction_contract_id": SESSION_OFFSET_CONTRACT_ID,
        "source_identity": source_identity,
        "view_stats": view_stats,
        "prohibited_actions_not_done": [
            "no_morphology_version",
            "no_1m_official_local_resample_replacement_5m",
            "no_2021_plus_read_into_diagnostic_frame",
            "no_H_end_5_promotion",
        ],
    }
    (OUT / "identity_diagnostic.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "session_boundary_samples.json").write_text(
        json.dumps(samples, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"source_rows": source_identity["source_rows"], "views": {
        k: {
            "frozen": v["frozen_rows"],
            "derived": v["derived_nonzero_occupancy_labels"],
            "only_frozen": v["n_labels_only_in_frozen"],
            "only_derived": v["n_labels_only_in_derived"],
            "ohlc_mismatch": v["ohlc_mismatch_matching_labels"],
        }
        for k, v in view_stats.items()
    }}, indent=2))


if __name__ == "__main__":
    main()
