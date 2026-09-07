# -*- coding: utf-8 -*-
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import duckdb

from datahub.core.services.history.tradable_bars import (
    PIT_TRADABLE_VIEW,
    RAW_CANONICAL_VIEW,
    TradableBarsMaterializer,
    normalize_bars_view,
)
from datahub.core.models.dataset import BarsDataset
from datahub.storage.query.bars_deriver import (
    _bars_scan_path as _deriver_bars_scan_path,
)
from datahub.storage.query.bars_deriver import derive_bars_from_1m
from datahub.storage.query.session_offset_contract import (
    SessionOffsetRequest,
    normalize_session_offset_request,
)
from datahub.storage.query.derived_cache import (
    DERIVED_BARS_CACHE,
    SimpleTTLCache,
    derivation_cache_key,
)
from datahub.storage.repositories.data_quality_events import (
    DataQualityError,
    DataQualityEventRepository,
    QUALITY_POLICY_FAIL_ON_UNRESOLVED,
    QUALITY_POLICY_IGNORE,
    normalize_quality_policy,
    quality_summary,
)
from datahub.storage.repositories.dataset_versions import DatasetVersionRepository

T0_QDII_RESEARCH_INSTRUMENT_TYPE = "t0_qdii"
T0_QDII_BAR_INSTRUMENT_TYPES = ("etf", "lof")

# Per-process TTL cache for parquet column sets (the DESCRIBE is
# path-stable; the audit measured it per request on the hot path).
_PARQUET_COLUMNS_CACHE: SimpleTTLCache[frozenset[str]] = SimpleTTLCache(
    ttl_seconds=30.0
)

_thread_local = threading.local()


class BarsQuery:
    def __init__(self, db_path: str | Path) -> None:
        self.dataset_repo = DatasetVersionRepository(db_path=db_path)
        self.quality_events = DataQualityEventRepository(db_path=db_path)

    def query(
        self,
        *,
        symbols: list[str],
        market: str,
        frequency: str,
        start_time: str,
        end_time: str,
        instrument_type: str | None = None,
        quality_policy: str = QUALITY_POLICY_FAIL_ON_UNRESOLVED,
        view: str = RAW_CANONICAL_VIEW,
        dataset_version: str | None = None,
        bar_align: str | None = None,
        session_offset_minutes: int | None = None,
        close_anchor: str | None = None,
        include_tail_partial: bool = False,
    ) -> BarsDataset:
        quality_policy = normalize_quality_policy(quality_policy)
        view = normalize_bars_view(view)
        offset_request = normalize_session_offset_request(
            frequency=frequency,
            bar_align=bar_align,
            session_offset_minutes=session_offset_minutes,
            close_anchor=close_anchor,
            include_tail_partial=include_tail_partial,
        )
        if dataset_version and not offset_request.uses_official_contract:
            raise ValueError(
                "pinned dataset_version cannot be combined with session_offset_minutes "
                "or close_anchor; offset / noon-close views are additive derived products"
            )
        dataset_id = TradableBarsMaterializer.dataset_id_for_view(
            market=market,
            frequency=frequency,
            view=view,
        )
        if dataset_version:
            dataset = self._pinned_dataset(
                dataset_version=dataset_version,
                expected_dataset_id=dataset_id,
                market=market,
                frequency=frequency,
                view=view,
            )
        else:
            dataset = self.dataset_repo.get_latest_ready_by_dataset_id(
                dataset_id=dataset_id,
                market=market,
                frequency=frequency,
            )
            if dataset is None and view == RAW_CANONICAL_VIEW:
                dataset = self.dataset_repo.get_latest_ready(
                    market=market,
                    frequency=frequency,
                )
        if not symbols:
            return BarsDataset(
                dataset_version=dataset["dataset_version"] if dataset else None,
                items=[],
                quality_policy=quality_policy,
                quality=quality_summary(policy=quality_policy, issues=[]),
            )
        quality_issues = self._quality_issues_for_query(
            symbols=symbols,
            market=market,
            frequency=frequency,
            start_time=start_time,
            end_time=end_time,
            instrument_type=instrument_type,
            quality_policy=quality_policy,
        )
        if quality_policy == QUALITY_POLICY_FAIL_ON_UNRESOLVED and quality_issues:
            blocking_issues = [
                item for item in quality_issues if item.get("severity") == "blocking"
            ]
            if blocking_issues:
                raise DataQualityError(policy=quality_policy, issues=blocking_issues)
        # Policy v87: when the pre-materialised version is missing or does not
        # reach the requested end_time, derive on demand from 1m raw
        # canonical.  A pinned dataset_version never triggers derivation.
        # Derivation results are cached per process (TTL-LRU with
        # single-flight); see derived_cache.py.
        force_offset_derivation = (
            dataset_version is None and not offset_request.uses_official_contract
        )
        if dataset is None or force_offset_derivation or (
            dataset_version is None
            and not _dataset_covers(dataset=dataset, end_time=end_time)
        ):
            derived_items = _derive_bars_cached(
                market=market,
                frequency=frequency,
                view=view,
                symbols=symbols,
                start_time=start_time,
                end_time=end_time,
                instrument_type=instrument_type,
                offset_request=offset_request,
            )
            if derived_items is not None:
                # On-demand synthesis must be observable through the HTTP
                # contract: use the v87 marker version instead of None, which
                # the routes layer rejects as dataset_not_found.
                return BarsDataset(
                    dataset_version="derived://1m_raw_canonical",
                    items=derived_items,
                    quality_policy=quality_policy,
                    quality=quality_summary(policy=quality_policy, issues=quality_issues),
                    quality_issues=quality_issues,
                )
        if dataset is None:
            return BarsDataset(
                dataset_version=None,
                items=[],
                quality_policy=quality_policy,
                quality=quality_summary(policy=quality_policy, issues=quality_issues),
            )
        storage_uri = Path(dataset["storage_uri"])
        parquet_path = _bars_scan_path(
            storage_uri, start_time=start_time, end_time=end_time
        )
        placeholders = ",".join(["?"] * len(symbols))
        instrument_type_filter = _bar_instrument_type_filter(instrument_type)
        # NOTE: no ``with`` — ``_connection`` returns the thread-local
        # connection that must survive across requests.
        conn = _connection()
        parquet_columns = _parquet_columns(conn, parquet_path)
        where = [f"symbol IN ({placeholders})", "timestamp >= ?", "timestamp <= ?"]
        params: list[Any] = [parquet_path, *symbols, start_time, end_time]
        if "instrument_type" in parquet_columns and instrument_type_filter:
            type_placeholders = ",".join(["?"] * len(instrument_type_filter))
            where.append(f"instrument_type IN ({type_placeholders})")
            params.extend(instrument_type_filter)
        if view == PIT_TRADABLE_VIEW and "is_tradable" in parquet_columns:
            where.append("is_tradable = true")
        sql = (
            "SELECT * FROM read_parquet(?, hive_partitioning=true, union_by_name=true) WHERE "
            + " AND ".join(where)
            + " ORDER BY timestamp ASC, symbol ASC"
        )
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        columns = [item[0] for item in (cursor.description or ())]
        # Ambiguity guard without a second full-tree scan: when no
        # instrument_type filter is applied, reject any requested symbol
        # whose rows within the query window mix instrument types.
        # (Previously this was a second scan over the whole dataset tree;
        # window-scoped checking guards exactly the response being
        # produced.)
        if (
            not instrument_type_filter
            and "instrument_type" in columns
            and "symbol" in columns
        ):
            ambiguous = _ambiguous_symbols(rows, columns)
            if ambiguous:
                raise ValueError(
                    "instrument_type is required for ambiguous canonical bars symbols: "
                    + ", ".join(ambiguous)
                )
        items = [dict(zip(columns, row, strict=False)) for row in rows]
        return BarsDataset(
            dataset_version=dataset["dataset_version"],
            items=items,
            quality_policy=quality_policy,
            quality=quality_summary(policy=quality_policy, issues=quality_issues),
            quality_issues=quality_issues,
        )

    def _pinned_dataset(
        self,
        *,
        dataset_version: str,
        expected_dataset_id: str,
        market: str,
        frequency: str,
        view: str,
    ) -> dict[str, Any] | None:
        dataset = self.dataset_repo.get(dataset_version)
        if dataset is None:
            return None
        if dataset.get("state") != "READY":
            raise ValueError(f"dataset_version is not READY: {dataset_version}")
        if dataset.get("dataset_kind") != "bars":
            raise ValueError(f"dataset_version is not a bars dataset: {dataset_version}")
        if dataset.get("market") != market or dataset.get("frequency") != frequency:
            raise ValueError(
                "dataset_version market/frequency mismatch: "
                f"{dataset_version} is {dataset.get('market')} {dataset.get('frequency')}"
            )
        if view != RAW_CANONICAL_VIEW and dataset.get("dataset_id") != expected_dataset_id:
            raise ValueError(
                "dataset_version does not match requested bars view: "
                f"{dataset_version} expected dataset_id {expected_dataset_id}"
            )
        return dataset

    def _quality_issues_for_query(
        self,
        *,
        symbols: list[str],
        market: str,
        frequency: str,
        start_time: str,
        end_time: str,
        instrument_type: str | None,
        quality_policy: str,
    ) -> list[dict[str, Any]]:
        if quality_policy == QUALITY_POLICY_IGNORE:
            return []
        start_day = _day_from_timestamp(start_time)
        end_day = _day_from_timestamp(end_time)
        if not start_day or not end_day:
            return []
        events = self.quality_events.list_active_for_scope(
            market=market,
            frequency=frequency,
            symbols=symbols,
            start_day=start_day,
            end_day=end_day,
            instrument_type=None,
        )
        if instrument_type:
            allowed_types = set(
                _bar_instrument_type_filter(instrument_type) or (instrument_type,)
            )
            events = [
                event for event in events if event.instrument_type in allowed_types
            ]
        return [event.to_public_dict() for event in events]


def _bar_instrument_type_filter(instrument_type: str | None) -> tuple[str, ...] | None:
    """Resolve public research aliases to physical bars partitions.

    ``t0_qdii`` is a research universe exposed by Jisilu.  It is not a
    persisted bars partition.  Physical 1m bars for those symbols live under
    the canonical ETF/LOF instrument types.
    """

    normalized = str(instrument_type or "").strip().lower()
    if not normalized:
        return None
    if normalized == T0_QDII_RESEARCH_INSTRUMENT_TYPE:
        return T0_QDII_BAR_INSTRUMENT_TYPES
    return (normalized,)


def _bars_scan_path(
    storage_uri: Path,
    start_time: str | None = None,
    end_time: str | None = None,
) -> str | list[str]:
    """Read path(s) for a bars parquet storage (window-pruned).

    Delegates to the shared implementation in ``bars_deriver``: flat
    ``bars.parquet`` files are used as-is, month-partitioned hive trees
    are pruned to the ``trading_month`` partitions the request time
    window can touch (the 26k/31.8k-file 60m/1d pre-materialised trees
    are the main win here), and anything else falls back to the
    full-tree glob.
    """
    return _deriver_bars_scan_path(
        storage_uri, start_time=start_time, end_time=end_time
    )


def _day_from_timestamp(value: str) -> str:
    text = str(value or "").strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return ""


def _connection() -> duckdb.DuckDBPyConnection:
    """Thread-local duckdb connection reused across requests (in-memory).

    Saves the audit-measured ~18ms per-request connection setup; safe
    because each thread owns its connection exclusively.
    """
    conn = getattr(_thread_local, "duckdb_conn", None)
    if conn is None:
        conn = duckdb.connect(database=":memory:")
        _thread_local.duckdb_conn = conn
    return conn


def _parquet_columns(
    conn: duckdb.DuckDBPyConnection,
    parquet_path: str | list[str],
) -> frozenset[str]:
    """Column names of a parquet scan path, cached per process (TTL).

    The DESCRIBE ran on every pre-materialised query (audit: 0.002s +
    a full footer scan of the glob); the column set is stable per path,
    so cache it.
    """
    key: Any = tuple(parquet_path) if isinstance(parquet_path, list) else parquet_path
    hit, cached = _PARQUET_COLUMNS_CACHE.get_entry(key)
    if hit:
        assert cached is not None
        return cached
    columns = frozenset(
        row[0]
        for row in conn.execute(
            "DESCRIBE SELECT * FROM read_parquet(?, hive_partitioning=true, union_by_name=true)",
            [parquet_path],
        ).fetchall()
    )
    _PARQUET_COLUMNS_CACHE.set(key, columns)
    return columns


def _ambiguous_symbols(
    rows: list[tuple[Any, ...]],
    columns: list[str],
) -> list[str]:
    """Symbols whose fetched rows mix more than one instrument_type."""
    symbol_idx = columns.index("symbol")
    type_idx = columns.index("instrument_type")
    types_by_symbol: dict[str, set[str]] = {}
    for row in rows:
        types_by_symbol.setdefault(str(row[symbol_idx]), set()).add(
            str(row[type_idx])
        )
    return sorted(
        symbol for symbol, types in types_by_symbol.items() if len(types) > 1
    )


def _derive_bars_cached(
    *,
    market: str,
    frequency: str,
    view: str,
    symbols: list[str],
    start_time: str,
    end_time: str,
    instrument_type: str | None,
    offset_request: SessionOffsetRequest | None = None,
) -> list[dict[str, Any]] | None:
    """Derivation entry with process-level TTL-LRU cache + single-flight.

    ``None`` results (unsupported frequency/view) are never cached —
    they are cheap and mean "derivation not applicable", not "no data".
    """
    request = offset_request or normalize_session_offset_request(frequency=frequency)
    key = derivation_cache_key(
        market=market,
        frequency=frequency,
        view=view,
        symbols=symbols,
        start_time=start_time,
        end_time=end_time,
        instrument_type=instrument_type,
        bar_align=request.bar_align,
        session_offset_minutes=request.session_offset_minutes,
        close_anchor=request.close_anchor_or_default,
        include_tail_partial=request.include_tail_partial,
    )
    return DERIVED_BARS_CACHE.get_or_compute(
        key,
        lambda: derive_bars_from_1m(
            market=market,
            frequency=frequency,
            view=view,
            symbols=symbols,
            start_time=start_time,
            end_time=end_time,
            instrument_type=instrument_type,
            offset_request=request,
        ),
    )


def _dataset_covers(*, dataset: dict[str, Any], end_time: str) -> bool:
    """Whether the stored dataset reaches the query end_time.

    Comparison is at trading-day granularity: a stored version whose last
    bar timestamp falls on the same day as the query end is considered to
    cover the request (e.g. a 60m version ending 2026-08-14T14:00Z covers
    a query ending 2026-08-14T15:00Z).  Older stored versions that stop
    before the requested day trigger on-demand derivation.  A missing
    time_range_end never covers.
    """
    stored_end = str((dataset.get("time_range") or {}).get("end_time") or "").strip()
    requested_end = str(end_time or "").strip()
    stored_day = _day_from_timestamp(stored_end)
    requested_day = _day_from_timestamp(requested_end)
    if not stored_day or not requested_day:
        return False
    return stored_day >= requested_day
