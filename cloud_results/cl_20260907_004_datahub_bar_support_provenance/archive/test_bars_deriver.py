# -*- coding: utf-8 -*-
"""Tests for on-demand bars derivation from 1m raw canonical (policy v87).

All tests run on in-memory duckdb with synthetic 1m rows — no dependency
on the live lake.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import datahub.storage.query.bars_deriver as bars_deriver
import datahub.storage.query.bars_query as bars_query

REPO = Path(__file__).resolve().parents[3]


def _write_1m_parquet(path: Path, rows: list[dict]) -> Path:
    """Write a 1m raw canonical style parquet file."""
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def _minute_bar(
    symbol: str = "000001",
    minute: str = "09:31",
    day: str = "2024-01-02",
    price: float = 10.0,
    volume: float = 100.0,
    amount: float = 1000.0,
    instrument_type: str = "stock",
) -> dict:
    return {
        "symbol": symbol,
        "market": "cn_a",
        "instrument_type": instrument_type,
        "timestamp": f"{day}T{minute}:00Z",
        "trading_day": day,
        "open": price,
        "high": price + 0.5,
        "low": price - 0.5,
        "close": price + 0.1,
        "volume": volume,
        "amount": amount,
        "available_at": "2026-08-16T00:00:00+00:00",
        "ingested_at": "2026-08-16T00:00:00+00:00",
        "source_kind": "test_synthetic",
        "dataset_version": "bars_cn_a_1m_raw_canonical_test",
    }


@pytest.fixture()
def one_minute_source(tmp_path, monkeypatch):
    """Point the deriver at a synthetic 1m parquet source."""
    source_path = _write_1m_parquet(tmp_path / "lake" / "bars" / "bars.parquet", [])
    monkeypatch.setattr(
        bars_deriver,
        "_find_1m_raw_source",
        lambda market: source_path.parent,
    )
    return source_path


def _minutes(start_hhmm: str, end_hhmm: str) -> list[str]:
    """Inclusive minute labels between two HH:MM values."""

    def to_total(value: str) -> int:
        hour, minute = value.split(":")
        return int(hour) * 60 + int(minute)

    def to_label(total: int) -> str:
        return f"{total // 60:02d}:{total % 60:02d}"

    return [
        to_label(total)
        for total in range(to_total(start_hhmm), to_total(end_hhmm) + 1)
    ]


def _derive(
    frequency: str,
    view: str,
    symbol: str = "000001",
    start_time: str = "2024-01-02T00:00:00Z",
    end_time: str = "2024-01-02T23:59:59Z",
    instrument_type: str | None = None,
    session_offset_minutes: int | None = None,
    close_anchor: str | None = None,
    include_tail_partial: bool = False,
) -> list[dict]:
    return bars_deriver.derive_bars_from_1m(
        market="cn_a",
        frequency=frequency,
        view=view,
        symbols=[symbol],
        start_time=start_time,
        end_time=end_time,
        instrument_type=instrument_type,
        session_offset_minutes=session_offset_minutes,
        close_anchor=close_anchor,
        include_tail_partial=include_tail_partial,
    ) or []


class TestSessionEndLabelBucketing:
    def test_60m_session_end_labels(self, tmp_path, monkeypatch):
        """60m bars must be end-labeled per cn_a_session_end_label_no_noon_partial_v2.

        - [09:31, 10:30] minutes → single 60m bar labeled 10:30
        - [10:31, 11:30] → 11:30 (capped at session end)
        - [13:01, 14:00] → 14:00 (13:00 lunch minute merged into the
          first afternoon bucket, never a standalone 13:00 bar)
        """
        rows: list[dict] = []
        price = 10.0
        for minute in _minutes("09:31", "09:39"):
            rows.append(_minute_bar(minute=minute, price=price))
            price += 0.1
        for minute in _minutes("10:31", "11:30"):
            rows.append(_minute_bar(minute=minute, price=price))
            price += 0.1
        # 13:00 lunch minute plus 13:01..14:00: one bar labeled 14:00.
        rows.append(_minute_bar(minute="13:00", price=price))
        price += 0.1
        for minute in _minutes("13:01", "14:00"):
            rows.append(_minute_bar(minute=minute, price=price))
            price += 0.1
        source_path = _write_1m_parquet(tmp_path / "bars.parquet", rows)
        monkeypatch.setattr(
            bars_deriver, "_find_1m_raw_source", lambda market: source_path.parent
        )

        bars = _derive(frequency="60m", view="raw_canonical")
        assert bars is not None
        labels = [bar["timestamp"] for bar in bars]
        assert labels == [
            "2024-01-02T10:30:00Z",
            "2024-01-02T11:30:00Z",
            "2024-01-02T14:00:00Z",
        ]
        assert "13:00" not in " ".join(labels)

        # First bar aggregates 09:31..09:39 (all inside the first bucket).
        first = bars[0]
        assert first["open"] == "10.0"
        assert float(first["close"]) == pytest.approx(10.9)
        assert float(first["volume"]) == 900.0
        # Lunch minute is merged into the afternoon bar: open comes from the
        # 13:00 row (70th row, price = 10.0 + 0.1 * 69 ≈ 16.9).
        assert float(bars[2]["open"]) == pytest.approx(16.9)

    def test_5m_raw_aggregation_granularity(self, tmp_path, monkeypatch):
        """5m raw must return 5m bars (not 1m passthrough)."""
        rows = [
            _minute_bar(minute=m, price=10.0 + i)
            for i, m in enumerate(_minutes("09:31", "09:40"))
        ]
        source_path = _write_1m_parquet(tmp_path / "bars.parquet", rows)
        monkeypatch.setattr(
            bars_deriver, "_find_1m_raw_source", lambda market: source_path.parent
        )

        bars = _derive(frequency="5m", view="raw_canonical")
        assert [bar["timestamp"] for bar in bars] == [
            "2024-01-02T09:35:00Z",
            "2024-01-02T09:40:00Z",
        ]
        assert float(bars[0]["volume"]) == 500.0


class TestAdjustmentFactorApplication:
    def _factor_parquet(
        self, path: Path, rows: list[dict], columns: list[str] | None = None
    ) -> Path:
        df = pd.DataFrame(rows)
        if columns is not None:
            df = df[columns]
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)
        return path

    def test_qfq_1m_applies_factors_without_aggregation(self, tmp_path, monkeypatch):
        """1m qfq: factors apply directly to 1m rows; no aggregation."""
        rows = [
            _minute_bar(minute="09:31", price=10.0),
            _minute_bar(minute="09:32", price=10.5),
        ]
        source_path = _write_1m_parquet(tmp_path / "bars.parquet", rows)
        monkeypatch.setattr(
            bars_deriver, "_find_1m_raw_source", lambda market: source_path.parent
        )
        factor_path = self._factor_parquet(
            tmp_path / "factors" / "factors.parquet",
            [
                {
                    "symbol": "000001",
                    "market": "cn_a",
                    "instrument_type": "stock",
                    "trading_day": "2024-01-02",
                    "factor_type": "qfq",
                    "price_multiplier": 2.0,
                    "ingested_at": "2026-08-16T00:00:00+00:00",
                }
            ],
        )
        monkeypatch.setattr(
            bars_deriver,
            "_resolve_factor_dir",
            lambda market, instrument_type: factor_path.parent,
        )

        bars = _derive(frequency="1m", view="qfq_canonical")
        # 1m granularity preserved: two bars, both factor-applied.
        assert [bar["timestamp"] for bar in bars] == [
            "2024-01-02T09:31:00Z",
            "2024-01-02T09:32:00Z",
        ]
        assert float(bars[0]["open"]) == 20.0
        assert float(bars[1]["open"]) == 21.0

    def test_qfq_5m_multiplier_stock(self, tmp_path, monkeypatch):
        """stock qfq: aggregate to 5m first, then apply price_multiplier."""
        rows = [
            _minute_bar(minute=m, price=10.0)
            for m in _minutes("09:31", "09:35")
        ]
        source_path = _write_1m_parquet(tmp_path / "bars.parquet", rows)
        monkeypatch.setattr(
            bars_deriver, "_find_1m_raw_source", lambda market: source_path.parent
        )
        factor_path = self._factor_parquet(
            tmp_path / "factors" / "factors.parquet",
            [
                {
                    "symbol": "000001",
                    "market": "cn_a",
                    "instrument_type": "stock",
                    "trading_day": "2024-01-02",
                    "factor_type": "qfq",
                    "price_multiplier": 2.0,
                    "ingested_at": "2026-08-16T00:00:00+00:00",
                }
            ],
        )
        monkeypatch.setattr(
            bars_deriver,
            "_resolve_factor_dir",
            lambda market, instrument_type: factor_path.parent,
        )

        bars = _derive(frequency="5m", view="qfq_canonical")
        assert len(bars) == 1
        bar = bars[0]
        # 5m granularity preserved, multiplier applied to OHLC.
        assert bar["timestamp"] == "2024-01-02T09:35:00Z"
        assert float(bar["open"]) == 20.0
        assert float(bar["close"]) == pytest.approx(20.2)
        assert float(bar["high"]) == pytest.approx(21.0)
        assert float(bar["low"]) == pytest.approx(19.0)

    def test_qfq_5m_affine_etf(self, tmp_path, monkeypatch):
        """etf/lof qfq: Sina affine semantics price*scale+offset."""
        rows = [
            _minute_bar(
                symbol="159915", minute=m, price=10.0, instrument_type="etf"
            )
            for m in _minutes("09:31", "09:35")
        ]
        source_path = _write_1m_parquet(tmp_path / "bars.parquet", rows)
        monkeypatch.setattr(
            bars_deriver, "_find_1m_raw_source", lambda market: source_path.parent
        )
        factor_path = self._factor_parquet(
            tmp_path / "factors" / "factors.parquet",
            [
                {
                    "symbol": "159915",
                    "market": "cn_a",
                    "instrument_type": "etf",
                    "trading_day": "2024-01-02",
                    "factor_type": "qfq",
                    "price_multiplier": 1.0,
                    "scale_multiplier": 0.5,
                    "price_offset": 1.0,
                    "ingested_at": "2026-08-16T00:00:00+00:00",
                }
            ],
        )
        monkeypatch.setattr(
            bars_deriver,
            "_resolve_factor_dir",
            lambda market, instrument_type: factor_path.parent,
        )

        bars = _derive(
            frequency="5m", view="qfq_canonical", symbol="159915",
            instrument_type="etf",
        )
        assert len(bars) == 1
        bar = bars[0]
        assert float(bar["open"]) == pytest.approx(10.0 * 0.5 + 1.0)
        assert float(bar["close"]) == pytest.approx(10.1 * 0.5 + 1.0)

    def test_carry_forward_and_missing_factor_passthrough(self, tmp_path, monkeypatch):
        """Latest factor with trading_day <= bar day applies; missing → raw."""
        rows = [
            _minute_bar(symbol="000001", minute="09:31", day="2024-01-02", price=10.0),
            _minute_bar(symbol="000001", minute="09:32", day="2024-01-02", price=10.1),
            _minute_bar(symbol="000002", minute="09:31", day="2024-01-02", price=20.0),
        ]
        source_path = _write_1m_parquet(tmp_path / "bars.parquet", rows)
        monkeypatch.setattr(
            bars_deriver, "_find_1m_raw_source", lambda market: source_path.parent
        )
        factor_path = self._factor_parquet(
            tmp_path / "factors" / "factors.parquet",
            [
                {
                    "symbol": "000001",
                    "market": "cn_a",
                    "instrument_type": "stock",
                    "trading_day": "2024-01-01",
                    "factor_type": "hfq",
                    "price_multiplier": 3.0,
                    "ingested_at": "2026-08-16T00:00:00+00:00",
                }
            ],
        )
        monkeypatch.setattr(
            bars_deriver,
            "_resolve_factor_dir",
            lambda market, instrument_type: factor_path.parent,
        )

        bars = _derive(
            frequency="5m", view="hfq_canonical", symbol="000001",
        )
        # carry-forward: 2024-01-01 factor applies to 2024-01-02 bars.
        # Both minutes fall into the first 5m bucket (end label 09:35).
        assert [float(bar["open"]) for bar in bars] == [30.0]
        bars_missing = _derive(
            frequency="5m", view="hfq_canonical", symbol="000002",
        )
        # no factor row → raw passthrough (fail-safe).
        assert [float(bar["open"]) for bar in bars_missing] == [20.0]


class TestDailyAggregation:
    def test_1d_groups_by_trading_day(self, tmp_path, monkeypatch):
        """1d bars group by trading_day and never cross nights."""
        rows = [
            _minute_bar(minute="09:31", day="2024-01-02", price=10.0),
            _minute_bar(minute="15:00", day="2024-01-02", price=11.0),
            _minute_bar(minute="09:31", day="2024-01-03", price=20.0),
            _minute_bar(minute="15:00", day="2024-01-03", price=21.0),
        ]
        source_path = _write_1m_parquet(tmp_path / "bars.parquet", rows)
        monkeypatch.setattr(
            bars_deriver, "_find_1m_raw_source", lambda market: source_path.parent
        )

        bars = _derive(
            frequency="1d", view="raw_canonical",
            end_time="2024-01-04T00:00:00Z",
        )
        assert [bar["timestamp"] for bar in bars] == [
            "2024-01-02T15:00:00Z",
            "2024-01-03T15:00:00Z",
        ]
        assert bars[0]["trading_day"] == "2024-01-02"
        assert bars[0]["open"] == "10.0"
        assert bars[0]["close"] == "11.1"
        assert bars[1]["open"] == "20.0"
        assert bars[1]["close"] == "21.1"
        assert float(bars[0]["volume"]) == 200.0


class TestFrequencySupportMatrix:
    def test_frequency_support_matrix(self):
        assert "5m" in bars_deriver.SUPPORTED_DERIVED_FREQUENCIES
        assert "15m" in bars_deriver.SUPPORTED_DERIVED_FREQUENCIES
        assert "30m" in bars_deriver.SUPPORTED_DERIVED_FREQUENCIES
        assert "60m" in bars_deriver.SUPPORTED_DERIVED_FREQUENCIES
        assert "1d" in bars_deriver.SUPPORTED_DERIVED_FREQUENCIES
        # 1m is the source, not a minute-period derived frequency.
        assert "1m" not in bars_deriver.SUPPORTED_DERIVED_FREQUENCIES
        assert "1d" not in bars_deriver._PERIOD_MINUTES
        assert bars_deriver._PERIOD_MINUTES["60m"] == 60

    def test_derive_returns_none_for_unsupported_frequency(self):
        result = bars_deriver.derive_bars_from_1m(
            market="cn_a", frequency="3m", view="raw_canonical",
            symbols=["000001"], start_time="2024-01-01", end_time="2024-01-02",
        )
        assert result is None

    def test_derive_returns_none_for_unsupported_view(self):
        result = bars_deriver.derive_bars_from_1m(
            market="cn_a", frequency="5m", view="pit_tradable",
            symbols=["000001"], start_time="2024-01-01", end_time="2024-01-02",
        )
        assert result is None


class _FakeDatasetRepo:
    def __init__(self, dataset: dict | None) -> None:
        self.dataset = dataset

    def get_latest_ready_by_dataset_id(self, **kwargs) -> dict | None:
        return self.dataset

    def get_latest_ready(self, **kwargs) -> dict | None:
        return self.dataset

    def get(self, dataset_version: str) -> dict | None:
        return self.dataset


def _make_query(tmp_path: Path, monkeypatch, dataset: dict | None):
    db_path = tmp_path / "meta.sqlite3"
    db_path.touch()
    query = bars_query.BarsQuery(db_path=db_path)
    monkeypatch.setattr(query, "dataset_repo", _FakeDatasetRepo(dataset))
    return query


class TestBarsQueryDerivationTrigger:
    def test_derives_when_stored_version_is_stale(self, tmp_path, monkeypatch):
        """Stored time_range_end before query end → on-demand derivation."""
        dataset = {
            "dataset_version": "bars_cn_a_5m_qfq_canonical_old",
            "dataset_id": "bars_cn_a_5m_qfq_canonical",
            "state": "READY",
            "market": "cn_a",
            "frequency": "5m",
            "time_range": {
                "start_time": "2000-06-09T09:35:00Z",
                "end_time": "2026-06-24T15:00:00Z",
            },
            "storage_uri": str(tmp_path / "stored"),
        }
        query = _make_query(tmp_path, monkeypatch, dataset)
        derived = [{"symbol": "000001", "timestamp": "2026-08-14T09:35:00Z"}]
        calls: list[dict] = []

        def fake_derive(**kwargs):
            calls.append(kwargs)
            return derived

        monkeypatch.setattr(bars_query, "derive_bars_from_1m", fake_derive)

        result = query.query(
            symbols=["000001"],
            market="cn_a",
            frequency="5m",
            start_time="2026-08-14T00:00:00Z",
            end_time="2026-08-14T15:00:00Z",
            instrument_type="stock",
            quality_policy="ignore",
            view="qfq_canonical",
        )
        assert len(calls) == 1
        assert calls[0]["frequency"] == "5m"
        assert calls[0]["view"] == "qfq_canonical"
        assert calls[0]["end_time"] == "2026-08-14T15:00:00Z"
        assert result.items == derived
        assert result.dataset_version == "derived://1m_raw_canonical"

    def test_no_derivation_when_stored_version_covers(self, tmp_path, monkeypatch):
        """Stored version reaching the query day → hit the store."""
        _write_1m_parquet(
            tmp_path / "stored" / "bars.parquet",
            [
                {
                    "symbol": "000001",
                    "market": "cn_a",
                    "instrument_type": "stock",
                    "timestamp": "2026-08-14T10:30:00Z",
                    "trading_day": "2026-08-14",
                    "open": "1.0", "high": "1.0", "low": "1.0", "close": "1.0",
                    "volume": "1.0", "amount": "1.0",
                    "available_at": "", "ingested_at": "",
                    "source_kind": "test", "dataset_version": "v1",
                }
            ],
        )
        dataset = {
            "dataset_version": "bars_cn_a_60m_raw_canonical_new",
            "dataset_id": "bars_cn_a_60m_raw_canonical",
            "state": "READY",
            "market": "cn_a",
            "frequency": "60m",
            "time_range": {
                "start_time": "2000-06-09T10:30:00Z",
                "end_time": "2026-08-14T14:00:00Z",
            },
            "storage_uri": str(tmp_path / "stored"),
        }
        query = _make_query(tmp_path, monkeypatch, dataset)
        calls: list[dict] = []

        def fake_derive(**kwargs):
            calls.append(kwargs)
            return [{"symbol": "derived"}]

        monkeypatch.setattr(bars_query, "derive_bars_from_1m", fake_derive)

        result = query.query(
            symbols=["000001"],
            market="cn_a",
            frequency="60m",
            start_time="2026-08-14T00:00:00Z",
            end_time="2026-08-14T15:00:00Z",
            instrument_type="stock",
            quality_policy="ignore",
            view="raw_canonical",
        )
        assert calls == []
        assert result.dataset_version == "bars_cn_a_60m_raw_canonical_new"
        assert [item["timestamp"] for item in result.items] == [
            "2026-08-14T10:30:00Z"
        ]

    def test_derives_when_no_stored_version(self, tmp_path, monkeypatch):
        query = _make_query(tmp_path, monkeypatch, None)
        calls: list[dict] = []

        def fake_derive(**kwargs):
            calls.append(kwargs)
            return []

        monkeypatch.setattr(bars_query, "derive_bars_from_1m", fake_derive)

        result = query.query(
            symbols=["000001"],
            market="cn_a",
            frequency="15m",
            start_time="2026-08-14T00:00:00Z",
            end_time="2026-08-14T15:00:00Z",
            quality_policy="ignore",
            view="raw_canonical",
        )
        assert len(calls) == 1
        assert result.items == []

    def test_pinned_version_never_derives(self, tmp_path, monkeypatch):
        _write_1m_parquet(
            tmp_path / "stored" / "bars.parquet",
            [
                {
                    "symbol": "000001",
                    "market": "cn_a",
                    "instrument_type": "stock",
                    "timestamp": "2026-08-14T10:30:00Z",
                    "trading_day": "2026-08-14",
                    "open": "1.0", "high": "1.0", "low": "1.0", "close": "1.0",
                    "volume": "1.0", "amount": "1.0",
                    "available_at": "", "ingested_at": "",
                    "source_kind": "test", "dataset_version": "pinned",
                }
            ],
        )
        dataset = {
            "dataset_version": "bars_cn_a_60m_raw_canonical_pinned",
            "dataset_id": "bars_cn_a_60m_raw_canonical",
            "dataset_kind": "bars",
            "state": "READY",
            "market": "cn_a",
            "frequency": "60m",
            "time_range": {
                "start_time": "2000-06-09T10:30:00Z",
                "end_time": "2026-06-26T14:00:00Z",
            },
            "storage_uri": str(tmp_path / "stored"),
        }
        query = _make_query(tmp_path, monkeypatch, dataset)
        calls: list[dict] = []

        def fake_derive(**kwargs):
            calls.append(kwargs)
            return []

        monkeypatch.setattr(bars_query, "derive_bars_from_1m", fake_derive)

        result = query.query(
            symbols=["000001"],
            market="cn_a",
            frequency="60m",
            start_time="2026-08-14T00:00:00Z",
            end_time="2026-08-14T15:00:00Z",
            instrument_type="stock",
            quality_policy="ignore",
            view="raw_canonical",
            dataset_version="bars_cn_a_60m_raw_canonical_pinned",
        )
        assert calls == []
        assert result.dataset_version == "bars_cn_a_60m_raw_canonical_pinned"

    def test_offset_query_derives_even_when_official_version_covers(self, tmp_path, monkeypatch):
        dataset = {
            "dataset_version": "bars_cn_a_60m_raw_canonical_new",
            "dataset_id": "bars_cn_a_60m_raw_canonical",
            "state": "READY",
            "market": "cn_a",
            "frequency": "60m",
            "time_range": {
                "start_time": "2000-06-09T10:30:00Z",
                "end_time": "2026-08-14T15:00:00Z",
            },
            "storage_uri": str(tmp_path / "stored"),
        }
        query = _make_query(tmp_path, monkeypatch, dataset)
        calls: list[dict] = []

        def fake_derive(**kwargs):
            calls.append(kwargs)
            return [{"symbol": "000001", "timestamp": "2026-08-14T10:35:00Z"}]

        monkeypatch.setattr(bars_query, "derive_bars_from_1m", fake_derive)
        result = query.query(
            symbols=["000001"],
            market="cn_a",
            frequency="60m",
            start_time="2026-08-14T00:00:00Z",
            end_time="2026-08-14T15:00:00Z",
            quality_policy="ignore",
            view="raw_canonical",
            session_offset_minutes=5,
        )
        assert len(calls) == 1
        assert calls[0]["offset_request"].session_offset_minutes == 5
        assert result.dataset_version == "derived://1m_raw_canonical"

    def test_pinned_version_plus_offset_fails_closed(self, tmp_path, monkeypatch):
        dataset = {
            "dataset_version": "bars_cn_a_1d_qfq_canonical_xdxr_v9_factorlab_2009_2025_20260814",
            "dataset_id": "bars_cn_a_1d_qfq_canonical",
            "state": "READY",
            "market": "cn_a",
            "frequency": "1d",
            "time_range": {"start_time": "2009-01-05T15:00:00Z", "end_time": "2025-12-31T15:00:00Z"},
            "storage_uri": str(tmp_path / "stored"),
        }
        query = _make_query(tmp_path, monkeypatch, dataset)
        with pytest.raises(ValueError, match="pinned dataset_version"):
            query.query(
                symbols=["000001"],
                market="cn_a",
                frequency="1d",
                start_time="2014-01-01T00:00:00Z",
                end_time="2014-12-31T15:00:00Z",
                quality_policy="ignore",
                view="qfq_canonical",
                dataset_version=dataset["dataset_version"],
                close_anchor="11:30",
            )





def _full_session_minutes() -> list[str]:
    return _minutes("09:30", "11:30") + _minutes("13:00", "15:00")



class TestSessionWallClockOffsetDerivation:
    def test_60m_offset_5_uses_0935_grid_and_drops_short_tails(self, tmp_path, monkeypatch):
        rows = [
            _minute_bar(minute=minute, price=10.0 + index * 0.01)
            for index, minute in enumerate(_full_session_minutes())
        ]
        source_path = _write_1m_parquet(tmp_path / "bars.parquet", rows)
        monkeypatch.setattr(
            bars_deriver, "_find_1m_raw_source", lambda market: source_path.parent
        )

        bars = _derive(
            frequency="60m",
            view="raw_canonical",
            session_offset_minutes=5,
        )
        labels = [bar["timestamp"] for bar in bars]
        assert labels == [
            "2024-01-02T10:35:00Z",
            "2024-01-02T14:05:00Z",
        ]
        assert "13:00" not in " ".join(labels)
        assert bars[0]["construction_contract"] == "cn_a_session_wall_clock_offset_v1"
        assert bars[0]["session_offset_minutes"] == 5
        assert bars[0]["first_tradable_slot"] == "2024-01-02T10:35:00Z"
        assert bars[1]["first_tradable_slot"] == "2024-01-02T14:05:00Z"
        # Official v2 path must stay unchanged on the same source.
        official = _derive(frequency="60m", view="raw_canonical")
        assert [bar["timestamp"] for bar in official] == [
            "2024-01-02T10:30:00Z",
            "2024-01-02T11:30:00Z",
            "2024-01-02T14:00:00Z",
            "2024-01-02T15:00:00Z",
        ]
        assert "construction_contract" not in official[0]

    def test_15m_offset_15_starts_at_0945_grid(self, tmp_path, monkeypatch):
        rows = [
            _minute_bar(minute=minute, price=10.0)
            for minute in _full_session_minutes()
        ]
        source_path = _write_1m_parquet(tmp_path / "bars.parquet", rows)
        monkeypatch.setattr(
            bars_deriver, "_find_1m_raw_source", lambda market: source_path.parent
        )
        bars = _derive(
            frequency="15m",
            view="raw_canonical",
            session_offset_minutes=15,
        )
        labels = [bar["timestamp"][11:16] for bar in bars]
        assert labels[0] == "10:00"
        assert "09:45" not in labels
        assert "13:15" not in labels
        assert labels[labels.index("11:30") + 1] == "13:30"

    def test_noon_close_daily_excludes_afternoon_minutes(self, tmp_path, monkeypatch):
        rows = []
        for minute in _minutes("09:30", "11:30"):
            rows.append(_minute_bar(minute=minute, price=10.0))
        for minute in _minutes("13:00", "15:00"):
            rows.append(_minute_bar(minute=minute, price=20.0))
        source_path = _write_1m_parquet(tmp_path / "bars.parquet", rows)
        monkeypatch.setattr(
            bars_deriver, "_find_1m_raw_source", lambda market: source_path.parent
        )

        official = _derive(frequency="1d", view="raw_canonical")
        assert official[0]["timestamp"] == "2024-01-02T15:00:00Z"
        assert float(official[0]["close"]) == pytest.approx(20.1)

        noon = _derive(frequency="1d", view="raw_canonical", close_anchor="11:30")
        assert noon[0]["timestamp"] == "2024-01-02T11:30:00Z"
        assert float(noon[0]["open"]) == pytest.approx(10.0)
        assert float(noon[0]["close"]) == pytest.approx(10.1)
        assert noon[0]["close_anchor"] == "11:30"
        assert noon[0]["first_tradable_slot"] == "2024-01-02T13:00:00Z"
        assert noon[0]["construction_contract"] == "cn_a_session_wall_clock_offset_v1"
