# -*- coding: utf-8 -*-
"""On-demand bars derivation from 1m raw canonical source (policy v87).

When a requested frequency/view (1m/5m/15m/30m/60m/1d raw/qfq/hfq) is not
pre-materialised in the lake — or the pre-materialised version does not
reach the requested ``end_time`` — derive it on-the-fly from the 1m raw
canonical bars using duckdb OHLCV aggregation and adjustment-factor
application.  No pre-materialisation is required for high frequencies;
adjusted (qfq/hfq) views of every frequency, including 1m, are
synthesised.

Bucketing contract: ``cn_a_session_end_label_no_noon_partial_v2`` (the
same contract as ``scripts/derive_intraday_bars_from_1m_canonical.py``).
Bars are end-labeled per session window: the first bucket of each
session is [session_start, session_start + period] labeled
session_start + period; subsequent buckets are ceil-based; the last
bucket is capped at session_end; the 13:00 lunch minute is merged into
the first afternoon bucket (a standalone 13:00 pseudo-bar is forbidden,
README line 144 / 2026-06-27 Baylum incident).  For cn_a stock the
morning session is [09:30, 11:30] and the afternoon session is
[13:00, 15:00] (inclusive endpoint minutes).

Adjustment-factor semantics: aggregation happens first (same session
bucketing as raw), then factors are applied per instrument type —
stock uses the XDXR multiplier contract (``price * multiplier``), etf/lof
uses the Sina affine contract (``price * scale_multiplier + price_offset``).
Factors carry forward: the latest factor row whose ``trading_day <=`` the
bar's trading_day applies.  Bars without any factor row pass through raw
(existing fail-safe semantics: never fabricate factors, never silently
return wrong adjusted values).

Performance contract (see the on-demand-derivation performance audit and
docs/architecture/performance-optimization.md §7): the source scan is pruned deterministically from the
request time window to the ``trading_month=YYYY-MM`` hive partitions it
can touch, instead of glob-ing the whole dataset tree; the whole
pipeline (scan → VARCHAR temp table → aggregation → factor carry-forward)
runs inside a single duckdb session with no Python row round-trips
(``CREATE TABLE AS SELECT COLUMNS(*)::VARCHAR`` replaces the previous
fetchall → executemany ingestion, and the factor carry-forward is one
ASOF LEFT JOIN instead of arg_max + re-join + UPDATE); the
adjustment-factor read pushes the requested symbols down into the
parquet scan (the factor table is sorted by symbol, so this drops a
363M-row table scan to a handful of row groups); the duckdb connection
is reused per thread; the source directory and factor-column lookups
are cached with a TTL.  Together these bring a single-symbol single-day
derivation to a few hundred ms and a 20-symbol six-month 60m qfq
derivation from ~295s (old pipeline) to ~1.4s, value-identical.
"""

from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Any

import duckdb

from datahub.core.services.history.adjustment_factor_authority import (
    current_factor_authority_path,
)

from datahub.core.services.history.tradable_bars import (
    HFQ_CANONICAL_VIEW,
    QFQ_CANONICAL_VIEW,
    RAW_CANONICAL_VIEW,
)

from datahub.storage.query.derived_cache import SimpleTTLCache
from datahub.storage.query.session_offset_contract import (
    NOON_CLOSE_ANCHOR,
    SessionOffsetRequest,
    construction_fields,
    hhmm_to_minute,
    normalize_session_offset_request,
)

# Frequency → minutes per bar.  "1d" is derived by trading_day grouping,
# not by a fixed minute period (a 1440-minute bucket would cross nights).
_PERIOD_MINUTES: dict[str, int] = {
    "5m": 5, "15m": 15, "30m": 30, "60m": 60,
}
SUPPORTED_DERIVED_FREQUENCIES = ("5m", "15m", "30m", "60m", "1d")
DERIVATION_SUPPORTED_VIEWS = (RAW_CANONICAL_VIEW, QFQ_CANONICAL_VIEW, HFQ_CANONICAL_VIEW)

# cn_a_session_end_label_no_noon_partial_v2 session windows (minutes of day,
# inclusive endpoints): morning [09:30, 11:30], afternoon [13:00, 15:00].
CN_A_SESSION_CONTRACT_ID = "cn_a_session_end_label_no_noon_partial_v2"
CN_A_MORNING_WINDOW = (570, 690)
CN_A_AFTERNOON_WINDOW = (780, 900)
CN_A_SESSION_WINDOWS = (CN_A_MORNING_WINDOW, CN_A_AFTERNOON_WINDOW)

# Combined factor authority: stock=XDXR multiplier semantics,
# etf/lof=Sina affine semantics (scale_multiplier/price_offset).
COMBINED_FACTOR_VERSION = "adjust_factors_cn_a_combined_stock_xdxr_v10_fund_sina_p0_20260816"

# Bar column order shared by every output path; keeps BarsDataset items
# compatible with pre-materialised canonical bars.
_BAR_COLUMNS = (
    "symbol", "market", "instrument_type", "timestamp", "trading_day",
    "open", "high", "low", "close", "volume", "amount",
    "available_at", "ingested_at", "source_kind", "dataset_version",
)

_LAKE_DIR = Path(__file__).resolve().parents[4] / ".runtime" / "live" / "lake"

# hive month-partition leaf names: instrument_type=<type>/trading_month=YYYY-MM
_MONTH_PARTITION_RE = re.compile(r"^trading_month=(\d{4}-\d{2})$")

# Per-process TTL caches for slow-changing lookups (see audit note: the
# query service is rebuilt per request, so caches must be module-level).
_SOURCE_LOOKUP_CACHE: SimpleTTLCache[Path | None] = SimpleTTLCache(
    ttl_seconds=30.0
)
_FACTOR_COLUMNS_CACHE: SimpleTTLCache[frozenset[str]] = SimpleTTLCache(
    ttl_seconds=30.0
)

_thread_local = threading.local()


def _find_1m_raw_source(market: str) -> Path | None:
    """Locate the latest 1m raw canonical parquet storage for derivation.

    Only datasets of the requested market are considered (the lake also
    holds ``*_derivatives_*`` minute datasets that must never be used).
    Cached per process with a TTL: the result changes only when a new
    dataset version is published, so the per-request full-tree rglob
    walk (audit: ~10ms) is paid at most once per TTL window.
    """
    hit, cached = _SOURCE_LOOKUP_CACHE.get_entry(market)
    if hit:
        return cached
    pattern = f"dataset_version=*_{market}_*1m_raw_canonical*"
    candidates = sorted(
        _LAKE_DIR.joinpath("bars").glob(pattern),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    found: Path | None = None
    for storage in candidates:
        if storage.is_dir() and any(storage.rglob("*.parquet")):
            found = storage
            break
    # Cache misses too: a missing source stays missing until the TTL
    # expires (publishing a source then triggers one extra glob round).
    _SOURCE_LOOKUP_CACHE.set(market, found)
    return found


def derive_bars_from_1m(
    *,
    market: str,
    frequency: str,
    view: str,
    symbols: list[str],
    start_time: str,
    end_time: str,
    instrument_type: str | None = None,
    bar_align: str | None = None,
    session_offset_minutes: int | None = None,
    close_anchor: str | None = None,
    include_tail_partial: bool = False,
    offset_request: SessionOffsetRequest | None = None,
) -> list[dict[str, Any]] | None:
    """Derive bars at target frequency/view from 1m raw canonical source.

    Returns list of bar dicts, or None if derivation is not possible for
    the requested frequency/view combination.  Official session labels stay
    the default; offset / noon-close products are additive and explicit.
    """
    request = offset_request or normalize_session_offset_request(
        frequency=frequency,
        bar_align=bar_align,
        session_offset_minutes=session_offset_minutes,
        close_anchor=close_anchor,
        include_tail_partial=include_tail_partial,
    )
    if view not in DERIVATION_SUPPORTED_VIEWS:
        return None
    if frequency == "1m":
        # 1m raw is the source itself; 1m adjusted views apply factors
        # directly to 1m rows without aggregation (policy v87: adjusted
        # views of every frequency, including 1m, are synthesised).
        if view == RAW_CANONICAL_VIEW:
            pass
    elif frequency not in SUPPORTED_DERIVED_FREQUENCIES:
        return None

    source = _find_1m_raw_source(market)
    if source is None:
        return None

    source_paths = _bars_scan_path(source, start_time=start_time, end_time=end_time)
    placeholders = ",".join(["?"] * len(symbols))
    params: list[Any] = [source_paths, *symbols, start_time, end_time]

    # NOTE: no ``with`` here — ``_connection`` returns the thread-local
    # connection that must survive across requests; closing it per call
    # would defeat the reuse.
    conn = _connection()
    where = [
        f"symbol IN ({placeholders})",
        "timestamp >= ?",
        "timestamp <= ?",
    ]
    if instrument_type:
        where.append("instrument_type = ?")
        params.append(instrument_type)

    # Perf contract 2026-08-17: the source scan materialises straight into
    # the all-VARCHAR temp table inside duckdb (``COLUMNS(*)::VARCHAR``
    # keeps the canonical wire shape regardless of the physical parquet
    # types).  The previous fetchall -> executemany round-trip through
    # Python capped throughput at ~10^5 rows/s; this single CTAS removes it.
    conn.execute(
        "CREATE OR REPLACE TEMP TABLE source_bars AS "
        "SELECT COLUMNS(*)::VARCHAR FROM read_parquet(?, hive_partitioning=true, union_by_name=true) "
        "WHERE " + " AND ".join(where),
        params,
    )
    count_row = conn.execute("SELECT COUNT(*) FROM source_bars").fetchone()
    row_count = int(count_row[0]) if count_row is not None else 0
    if not row_count:
        return []
    columns = [
        str(row[0])
        for row in conn.execute("DESCRIBE source_bars").fetchall()
    ]

    if frequency == "1m":
        if view == RAW_CANONICAL_VIEW:
            return _rows_as_dicts(conn, columns)
        # 1m qfq/hfq: apply factors directly to 1m rows (no aggregation).
        return _apply_adjustment_factors(
            conn=conn,
            table="source_bars",
            columns=columns,
            view=view,
            market=market,
            instrument_type=instrument_type,
        )

    table_name = _aggregate_bars_table(
        conn=conn,
        frequency=frequency,
        offset_request=request,
    )
    if view == RAW_CANONICAL_VIEW:
        rows = _rows_as_dicts(conn, list(_BAR_COLUMNS), table=table_name)
    else:
        rows = _apply_adjustment_factors(
            conn=conn,
            table=table_name,
            columns=list(_BAR_COLUMNS),
            view=view,
            market=market,
            instrument_type=instrument_type,
        )
    return _attach_construction_fields(rows, request)


def _rows_as_dicts(
    conn: duckdb.DuckDBPyConnection,
    columns: list[str],
    table: str = "source_bars",
) -> list[dict[str, Any]]:
    selected = ", ".join(_quote_identifier(column) for column in columns)
    rows = conn.execute(
        f"SELECT {selected} FROM {table} ORDER BY timestamp ASC, symbol ASC"
    ).fetchall()
    return [dict(zip(columns, row, strict=True)) for row in rows]


def _minute_of_day_expr() -> str:
    return (
        "CAST(substr(timestamp, 12, 2) AS INTEGER) * 60 "
        "+ CAST(substr(timestamp, 15, 2) AS INTEGER)"
    )


def _session_filter_expr() -> str:
    """Keep only rows whose minute-of-day falls inside a session window.

    The window set is the stock cn_a contract
    (``cn_a_session_end_label_no_noon_partial_v2``); it is also the
    authoritative fallback for other cn_a instrument types.
    """
    mod = _minute_of_day_expr()
    conditions = []
    for start, end in CN_A_SESSION_WINDOWS:
        conditions.append(f"({mod} BETWEEN {start} AND {end})")
    return "(" + " OR ".join(conditions) + ")"


def _morning_session_filter_expr() -> str:
    """Keep only the official morning session for noon-close daily bars."""
    mod = _minute_of_day_expr()
    start, end = CN_A_MORNING_WINDOW
    return f"({mod} BETWEEN {start} AND {end})"


def _wall_clock_bucket_case(
    *,
    period_minutes: int,
    offset_minutes: int,
    include_tail_partial: bool,
) -> str:
    """SQL CASE for additive wall-clock offset buckets.

    Each session starts its grid at ``session_start + offset``.  Minutes
    before that grid and incomplete tails are dropped unless
    ``include_tail_partial`` is set.  13:00 never becomes a standalone bar.
    """
    period = int(period_minutes)
    offset = int(offset_minutes)
    tail = "TRUE" if include_tail_partial else "FALSE"
    segments: list[str] = []
    for start, end in CN_A_SESSION_WINDOWS:
        grid = start + offset
        segments.append(
            f"""
            WHEN mod BETWEEN {start} AND {end} THEN
              CASE
                WHEN mod < {grid} THEN NULL
                WHEN {grid} + CAST(ceil(GREATEST(mod - {grid}, 1)::DOUBLE / {period}) AS INTEGER) * {period} <= {end}
                  THEN {grid} + CAST(ceil(GREATEST(mod - {grid}, 1)::DOUBLE / {period}) AS INTEGER) * {period}
                WHEN {tail} THEN {end}
                ELSE NULL
              END
            """
        )
    return "CASE " + "".join(segments) + " ELSE NULL END"


def _session_bucket_case(period_minutes: int) -> str:
    """SQL CASE computing the end-labeled session bucket minute-of-day.

    Mirrors ``_bucket_minute_expr`` of
    ``scripts/derive_intraday_bars_from_1m_canonical.py``: first bucket
    [start, start+period] labeled start+period; subsequent ceil buckets;
    last bucket capped at session end.  13:00 (minute 780) lands in the
    first afternoon bucket, never a standalone bar.
    """
    period = int(period_minutes)
    segments: list[str] = []
    for start, end in CN_A_SESSION_WINDOWS:
        segments.append(
            f"""
            WHEN mod BETWEEN {start} AND {end} THEN
              CASE
                WHEN mod <= {start} + {period} THEN {start} + {period}
                ELSE LEAST(
                  {end},
                  {start} + {period}
                    + CAST(ceil((mod - ({start} + {period}))::DOUBLE / {period}) AS INTEGER)
                      * {period}
                )
              END
            """
        )
    return "CASE " + "".join(segments) + " ELSE NULL END"


def _bucket_timestamp_expr() -> str:
    return (
        "trading_day || 'T' || "
        "lpad(CAST(CAST(floor(bucket_minute / 60) AS INTEGER) AS VARCHAR), 2, '0') || ':' || "
        "lpad(CAST(bucket_minute % 60 AS VARCHAR), 2, '0') || ':00Z'"
    )


def _ohlcv_select(ts_expr: str) -> str:
    return f"""
        SELECT
            symbol,
            market,
            instrument_type,
            {ts_expr} AS timestamp,
            MIN(trading_day) AS trading_day,
            CAST(arg_min(CAST(open AS DOUBLE), timestamp) AS VARCHAR) AS open,
            CAST(max(greatest(
                CAST(open AS DOUBLE), CAST(high AS DOUBLE),
                CAST(low AS DOUBLE), CAST(close AS DOUBLE)
            )) AS VARCHAR) AS high,
            CAST(min(least(
                CAST(open AS DOUBLE), CAST(high AS DOUBLE),
                CAST(low AS DOUBLE), CAST(close AS DOUBLE)
            )) AS VARCHAR) AS low,
            CAST(arg_max(CAST(close AS DOUBLE), timestamp) AS VARCHAR) AS close,
            CAST(SUM(CAST(volume AS DOUBLE)) AS VARCHAR) AS volume,
            CAST(SUM(CAST(amount AS DOUBLE)) AS VARCHAR) AS amount,
            MAX(available_at) AS available_at,
            MAX(ingested_at) AS ingested_at,
            MIN(source_kind) AS source_kind,
            MIN(dataset_version) AS dataset_version
    """


def _aggregate_bars_table(
    *,
    conn: duckdb.DuckDBPyConnection,
    frequency: str,
    offset_request: SessionOffsetRequest | None = None,
) -> str:
    """Aggregate the 1m source table into the target frequency.

    Materialises the aggregated rows into the ``aggregated_bars`` temp
    table (one duckdb-side pass; the caller reads it back for raw views or
    applies factors to it for adjusted views — no Python round-trip in
    between).  Intraday frequencies use the session end-label contract by
    default; additive wall-clock offset / noon-close daily use a separate
    construction contract.  1d groups by trading_day (never by a fixed
    1440-minute bucket that would cross nights).
    """
    request = offset_request or normalize_session_offset_request(frequency=frequency)
    if frequency == "1d":
        if request.close_anchor_or_default == NOON_CLOSE_ANCHOR:
            session_filter = _morning_session_filter_expr()
            ts_expr = "trading_day || 'T11:30:00Z'"
        else:
            session_filter = _session_filter_expr()
            ts_expr = "trading_day || 'T15:00:00Z'"
        agg_sql = (
            f"""
            CREATE OR REPLACE TEMP TABLE aggregated_bars AS
            WITH session_rows AS (
              SELECT * FROM source_bars
              WHERE substr(timestamp, 1, 10) = trading_day
                AND {session_filter}
            )
            {_ohlcv_select(ts_expr)}
            FROM session_rows
            GROUP BY symbol, market, instrument_type, trading_day
            """
        )
        conn.execute(agg_sql)
        return "aggregated_bars"

    period = _PERIOD_MINUTES[frequency]
    bucket_case = (
        _session_bucket_case(period)
        if request.uses_official_contract
        else _wall_clock_bucket_case(
            period_minutes=period,
            offset_minutes=request.session_offset_minutes,
            include_tail_partial=request.include_tail_partial,
        )
    )
    agg_sql = (
        f"""
        CREATE OR REPLACE TEMP TABLE aggregated_bars AS
        WITH source_min AS (
          SELECT *,
            {_minute_of_day_expr()} AS mod
          FROM source_bars
          WHERE substr(timestamp, 1, 10) = trading_day
        ),
        bucketed AS (
          SELECT *,
            {bucket_case} AS bucket_minute
          FROM source_min
        ),
        labeled AS (
          SELECT *,
            {_bucket_timestamp_expr()} AS bucket_timestamp
          FROM bucketed
          WHERE bucket_minute IS NOT NULL
        )
        {_ohlcv_select('MIN(bucket_timestamp)')}
        FROM labeled
        GROUP BY symbol, market, instrument_type, bucket_timestamp
        """
    )
    conn.execute(agg_sql)
    return "aggregated_bars"


def _apply_adjustment_factors(
    *,
    conn: duckdb.DuckDBPyConnection,
    table: str,
    columns: list[str],
    view: str,
    market: str,
    instrument_type: str | None,
) -> list[dict[str, Any]]:
    """Apply the pinned adjustment-factor authority to a bars temp table.

    stock rows use the XDXR multiplier contract; etf/lof rows use the Sina
    affine contract (scale_multiplier/price_offset).  Factors carry forward
    per (instrument_type, symbol): the latest factor row whose
    trading_day <= the bar's trading_day applies (a single ASOF LEFT JOIN
    replaces the previous arg_max + re-join + UPDATE chain).  Bars without
    any factor row pass through raw (fail-safe: never fabricate factors).
    """
    factor_dir = _resolve_factor_dir(market=market, instrument_type=instrument_type)
    factor_path = factor_dir / "factors.parquet"
    if not factor_path.exists():
        raise FileNotFoundError(
            f"adjustment factor authority is missing: {factor_dir}"
        )
    factor_type = "qfq" if view == QFQ_CANONICAL_VIEW else "hfq"

    # No bars to adjust: nothing to do (also avoids an empty symbol list
    # in the factor read push-down below).
    count_row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    row_count = int(count_row[0]) if count_row is not None else 0
    if not row_count:
        return []

    factor_columns = _factor_parquet_columns(conn, factor_path)
    has_scale = "scale_multiplier" in factor_columns
    has_offset = "price_offset" in factor_columns
    has_ingested = "ingested_at" in factor_columns
    if "price_multiplier" not in factor_columns:
        raise RuntimeError(
            f"adjustment factor authority has no price_multiplier column: {factor_dir}"
        )
    scale_expr = (
        "CAST(scale_multiplier AS DOUBLE)"
        if has_scale
        else "CAST(NULL AS DOUBLE)"
    )
    offset_expr = (
        "CAST(price_offset AS DOUBLE)" if has_offset else "CAST(0.0 AS DOUBLE)"
    )
    ingested_expr = "ingested_at" if has_ingested else "CAST(NULL AS VARCHAR)"
    # Symbol push-down: the factor table is sorted by symbol with valid
    # row-group stats, so scanning only the requested symbols turns the
    # audit-measured 363M-row table scan (~1.26s) into a few row-group
    # reads (~0.03s).
    symbols = [
        str(row[0])
        for row in conn.execute(f"SELECT DISTINCT symbol FROM {table}").fetchall()
    ]
    symbol_placeholders = ",".join(["?"] * len(symbols))
    conn.execute("DROP TABLE IF EXISTS factors")
    conn.execute(
        "CREATE TEMP TABLE factors AS "
        "SELECT * EXCLUDE rn FROM ("
        "  SELECT "
        "    CAST(symbol AS VARCHAR) AS symbol, "
        "    CAST(COALESCE(instrument_type, 'stock') AS VARCHAR) AS instrument_type, "
        "    CAST(trading_day AS VARCHAR) AS trading_day, "
        "    CAST(price_multiplier AS DOUBLE) AS price_multiplier, "
        f"    COALESCE({scale_expr}, CAST(price_multiplier AS DOUBLE)) AS scale_multiplier, "
        f"    COALESCE({offset_expr}, 0.0) AS price_offset, "
        f"    {ingested_expr} AS ingested_at, "
        "    row_number() OVER ("
        "      PARTITION BY instrument_type, symbol, trading_day "
        "      ORDER BY ingested_at DESC"
        "    ) AS rn "
        "  FROM ("
        "    SELECT * FROM read_parquet(?, hive_partitioning=true, union_by_name=true) "
        "    WHERE market = ? AND factor_type = ? AND symbol IN (" + symbol_placeholders + ")"
        "  ) raw"
        ") WHERE rn = 1",
        [str(factor_path), market, factor_type, *symbols],
    )
    # Carry-forward + adjustment in one pass: ASOF LEFT JOIN picks, per
    # bar row, the latest factor row with trading_day <= the bar's day —
    # exactly the previous arg_max carry-forward semantics (the factors
    # table is already deduplicated per instrument_type/symbol/trading_day,
    # so the ASOF match is unique).  Unmatched bars keep raw OHLC.
    select_parts: list[str] = []
    for column in columns:
        quoted = _quote_identifier(column)
        if column in ("open", "high", "low", "close"):
            select_parts.append(
                f"CASE WHEN f.price_multiplier IS NOT NULL "
                f"THEN CAST(CAST(b.{quoted} AS DOUBLE) * f.scale_multiplier + f.price_offset AS VARCHAR) "
                f"ELSE b.{quoted} END AS {quoted}"
            )
        else:
            select_parts.append(f"b.{quoted} AS {quoted}")
    adjusted_sql = (
        f"SELECT {', '.join(select_parts)} "
        f"FROM {table} b ASOF LEFT JOIN factors f "
        "  ON b.symbol = f.symbol "
        " AND b.instrument_type = f.instrument_type "
        " AND f.trading_day <= b.trading_day "
        "ORDER BY b.timestamp ASC, b.symbol ASC"
    )
    rows = conn.execute(adjusted_sql).fetchall()
    return [dict(zip(columns, row, strict=True)) for row in rows]



def _attach_construction_fields(
    rows: list[dict[str, Any]],
    request: SessionOffsetRequest,
) -> list[dict[str, Any]]:
    """Attach additive construction metadata without mutating official v2 rows."""
    if request.uses_official_contract:
        return rows
    attached: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        trading_day = str(item.get("trading_day") or "")[:10]
        timestamp = str(item.get("timestamp") or "")
        close_minute = None
        if len(timestamp) >= 16 and timestamp[10] == "T":
            close_minute = hhmm_to_minute(timestamp[11:16])
        elif request.frequency == "1d":
            close_minute = hhmm_to_minute(request.close_anchor_or_default)
        item.update(
            construction_fields(
                request,
                trading_day=trading_day,
                bar_close_minute=close_minute,
            )
        )
        attached.append(item)
    return attached


def _factor_parquet_columns(
    conn: duckdb.DuckDBPyConnection,
    factor_path: Path,
) -> frozenset[str]:
    """Column names of the factor authority parquet, cached per process (TTL)."""
    key = str(factor_path)
    hit, cached = _FACTOR_COLUMNS_CACHE.get_entry(key)
    if hit and cached is not None:
        return cached
    columns = frozenset(
        str(row[0])
        for row in conn.execute(
            "DESCRIBE SELECT * FROM read_parquet(?, hive_partitioning=true, union_by_name=true)",
            [str(factor_path)],
        ).fetchall()
    )
    _FACTOR_COLUMNS_CACHE.set(key, columns)
    return columns


def _resolve_factor_dir(*, market: str, instrument_type: str | None) -> Path:
    """Pick the factor authority for the requested instrument scope.

    stock → pinned V10 XDXR authority (multiplier semantics).
    etf/lof → combined authority (Sina affine semantics).
    Other/unknown instrument types → combined authority when present,
    else the pinned V10 authority (bars without factor rows then pass
    through raw, preserving the fail-safe contract).
    """
    v10_dir = current_factor_authority_path(_LAKE_DIR)
    combined_dir = (
        _LAKE_DIR / "adjustment_factors" / f"dataset_version={COMBINED_FACTOR_VERSION}"
    )
    if instrument_type == "stock":
        return v10_dir
    if instrument_type in ("etf", "lof"):
        return combined_dir
    if (combined_dir / "factors.parquet").exists():
        return combined_dir
    return v10_dir


def _quote_identifier(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _connection() -> duckdb.DuckDBPyConnection:
    """Thread-local duckdb connection (in-memory, reused across requests).

    Each thread owns one connection, opened lazily on first use; duckdb
    :memory: connections are serialised per connection, so this is safe
    as long as one connection is never used by two threads concurrently
    (guaranteed by threading.local).  Saves the audit-measured ~18ms
    per-request connection setup.
    """
    conn = getattr(_thread_local, "duckdb_conn", None)
    if conn is None:
        conn = duckdb.connect(database=":memory:")
        _thread_local.duckdb_conn = conn
    return conn


def _month_partitions_for_window(
    *,
    storage_uri: Path,
    start_time: str | None = None,
    end_time: str | None = None,
) -> list[Path]:
    """Deterministic window→hive-partition mapping for month-partitioned trees.

    Returns ``instrument_type=<type>/trading_month=YYYY-MM`` directories
    whose month falls within the [start_time, end_time] window (inclusive,
    with one month of slack on the start side because a month partition
    may span several trading days and query start/end timestamps land
    mid-month).  Returns an empty list when the time window cannot be
    parsed — callers must then fall back to the full-tree glob to
    preserve correctness.
    """
    month_pattern = _month_pattern_from_window(
        start_time=start_time, end_time=end_time
    )
    if month_pattern is None:
        return []
    matches: list[Path] = []
    for type_dir in storage_uri.iterdir():
        if not type_dir.name.startswith("instrument_type="):
            continue
        for month_dir in type_dir.iterdir():
            if _MONTH_PARTITION_RE.fullmatch(month_dir.name) and month_pattern.match(
                month_dir.name
            ):
                matches.append(month_dir)
    return matches


def _month_pattern_from_window(
    *, start_time: str | None = None, end_time: str | None = None
) -> re.Pattern[str] | None:
    """Compile a trading_month pattern covering [start, end], or None."""
    start_month = _month_from_timestamp(start_time)
    end_month = _month_from_timestamp(end_time)
    if start_month is None or end_month is None:
        return None
    if start_month == end_month:
        return re.compile(re.escape(f"trading_month={start_month}"))
    return re.compile(
        "|".join(
            re.escape(f"trading_month={month}")
            for month in _months_between(start_month, end_month)
        )
    )


def _months_between(start_month: str, end_month: str) -> list[str]:
    """Inclusive month list between ``YYYY-MM`` values (supports years)."""
    start_year, start_month_no = (int(part) for part in start_month.split("-"))
    end_year, end_month_no = (int(part) for part in end_month.split("-"))
    if (start_year, start_month_no) > (end_year, end_month_no):
        return []
    months: list[str] = []
    year, month = start_year, start_month_no
    while (year, month) <= (end_year, end_month_no):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            year += 1
            month = 1
    return months


def _month_from_timestamp(value: str | None) -> str | None:
    """Extract ``YYYY-MM`` from an ISO-ish timestamp, or None."""
    text = str(value or "").strip()
    if len(text) >= 7 and text[4] == "-":
        return text[:7]
    return None


def _bars_scan_path(
    storage_uri: Path,
    start_time: str | None = None,
    end_time: str | None = None,
) -> str | list[str]:
    """Read path(s) for a bars parquet storage.

    ``bars.parquet`` flat files are used as-is.  Month-partitioned hive
    trees (``instrument_type=<type>/trading_month=YYYY-MM/data_0.parquet``)
    are pruned deterministically from the request time window: only the
    month partitions the window can touch are scanned, which cuts the
    footer-enumeration fan-out of the full-tree glob (audit: 863 files
    → ~0.93s vs. a single partition ~0.09s; the pre-materialised 60m/1d
    trees with 26k/31.8k files get the same treatment).  A window that
    cannot be parsed, a month list that finds no partition, or any other
    layout falls back to the full-tree glob so correctness is preserved.
    """
    root_file = storage_uri / "bars.parquet"
    if root_file.exists():
        return str(root_file)
    pruned = _month_partitions_for_window(
        storage_uri=storage_uri,
        start_time=start_time,
        end_time=end_time,
    )
    if pruned:
        return [str(month_dir / "*.parquet") for month_dir in sorted(pruned)]
    if storage_uri.exists() and any(storage_uri.rglob("*.parquet")):
        return str(storage_uri / "**" / "*.parquet")
    return str(root_file)
