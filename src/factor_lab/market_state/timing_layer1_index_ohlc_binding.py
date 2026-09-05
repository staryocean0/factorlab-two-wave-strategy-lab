# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Layer 1 DataHub noon-close OHLC binding for market-index carriers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.data.adapters.datahub_client import DataHubClient
from factor_lab.data.session_offset_defaults import apply_fetch_defaults

BINDING_ID: Final[str] = "timing_layer1_index_ohlc_1d_noon@1.0"
MARKET: Final[str] = "cn_index"
FREQUENCY: Final[str] = "1d"
INDEX_SYMBOLS: Final[tuple[str, ...]] = ("000852.SH", "000300.SH")
WALL_CLOCK_TZ: Final[str] = "Asia/Shanghai"


@dataclass(frozen=True, slots=True)
class Layer1IndexOHLCReceipt:
    binding_id: str
    market: str
    frequency: str
    view_id: str
    close_anchor: str
    bar_align: str
    construction_contract: str
    signal_view: str
    fill_view: str
    query_dataset_version: str
    row_source_dataset_version: str
    source_kind: str
    wall_clock_mode: str
    quality_status: str
    symbols: tuple[str, ...]
    start: str
    end: str
    row_count: int
    parquet_sha256: str
    production_authority: bool = False
    local_resampling: bool = False
    bar_construction_owner: str = "datahub"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def normalize_index_noon_ohlc(items: list[Mapping[str, Any]]) -> pd.DataFrame:
    if not items:
        raise ValidationError("Layer 1 index OHLC response is empty")
    frame = pd.DataFrame(list(items))
    required = {"symbol", "timestamp", "trading_day", "open", "high", "low", "close", "available_at"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValidationError(f"Layer 1 index OHLC missing columns: {missing}")
    local = frame.copy()
    parent_time = pd.to_datetime(local["timestamp"], errors="raise", utc=True)
    wall = parent_time.dt.tz_localize(None).dt.tz_localize(WALL_CLOCK_TZ)
    local["observation_time"] = wall
    local["trading_day"] = local["trading_day"].astype(str)
    if not wall.dt.strftime("%Y-%m-%d").eq(local["trading_day"]).all():
        raise ValidationError("Layer 1 index observation date differs from trading_day")
    if not wall.dt.strftime("%H:%M").eq("11:30").all():
        raise ValidationError("Layer 1 index bars are not 1d@11:30")
    for column in ("open", "high", "low", "close"):
        local[column] = pd.to_numeric(local[column], errors="raise").astype(float)
    if local[["open", "high", "low", "close"]].le(0.0).any().any():
        raise ValidationError("Layer 1 index OHLC must be positive")
    if bool((local["low"] > local[["open", "close"]].min(axis=1)).any()) or bool(
        (local["high"] < local[["open", "close"]].max(axis=1)).any()
    ):
        raise ValidationError("Layer 1 index OHLC envelope is inconsistent")
    local["available_at"] = pd.to_datetime(local["available_at"], errors="raise")
    if local["available_at"].dt.tz is None:
        raise ValidationError("Layer 1 available_at must be timezone-aware")
    local["continuity_segment_id"] = local["symbol"].astype(str)
    local = local.sort_values(["symbol", "observation_time"], kind="mergesort").reset_index(drop=True)
    if local.duplicated(["symbol", "observation_time"]).any():
        raise ValidationError("Layer 1 index timestamps must be unique per symbol")
    return local


def fetch_index_noon_ohlc(
    *,
    symbols: tuple[str, ...] = INDEX_SYMBOLS,
    start_time: str,
    end_time: str,
    client: DataHubClient | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    if any(symbol not in INDEX_SYMBOLS for symbol in symbols):
        raise ValidationError("Layer 1 index binding only admits 000852.SH and 000300.SH")
    defaults = apply_fetch_defaults(
        frequency=FREQUENCY,
        view="raw_canonical",
        close_anchor=None,
        session_offset_minutes=None,
        bar_align=None,
    )
    hub = client or DataHubClient()
    response = hub.get_history_bars(
        symbols=list(symbols),
        market=MARKET,
        frequency=FREQUENCY,
        start_time=start_time,
        end_time=end_time,
        view=str(defaults["view"]),
        close_anchor=str(defaults["close_anchor"]),
        bar_align=str(defaults.get("bar_align") or "session_wall_clock"),
    )
    payload = response.get("data") if isinstance(response, dict) else None
    if not isinstance(payload, dict):
        raise ValidationError("Layer 1 index OHLC envelope is invalid")
    quality = payload.get("quality") if isinstance(payload.get("quality"), dict) else {}
    if str(quality.get("status") or "") != "clean" or int(quality.get("blocking_issue_count") or 0) != 0:
        raise ValidationError("Layer 1 index OHLC quality is not clean")
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValidationError("Layer 1 index OHLC items are missing")
    bars = normalize_index_noon_ohlc(items)
    if set(bars["symbol"].astype(str).unique()) != set(symbols):
        raise ValidationError("Layer 1 index OHLC symbol set drifted")
    return bars, response


def build_layer1_index_receipt(
    bars: pd.DataFrame,
    response: Mapping[str, object],
    *,
    parquet_bytes: bytes,
) -> Layer1IndexOHLCReceipt:
    payload = response.get("data") if isinstance(response.get("data"), dict) else {}
    row_versions = sorted({str(value) for value in bars.get("dataset_version", pd.Series(dtype=str)).dropna().unique()})
    source_kinds = sorted({str(value) for value in bars.get("source_kind", pd.Series(dtype=str)).dropna().unique()})
    contracts = sorted({str(value) for value in bars.get("construction_contract", pd.Series(dtype=str)).dropna().unique()})
    if len(row_versions) != 1 or len(source_kinds) != 1 or len(contracts) != 1:
        raise ValidationError("Layer 1 index OHLC source identity is not unique")
    return Layer1IndexOHLCReceipt(
        binding_id=BINDING_ID,
        market=MARKET,
        frequency=FREQUENCY,
        view_id="daily_noon_close_1130",
        close_anchor="11:30",
        bar_align="session_wall_clock",
        construction_contract=contracts[0],
        signal_view="raw_canonical",
        fill_view="raw_canonical",
        query_dataset_version=str(payload.get("dataset_version") or ""),
        row_source_dataset_version=row_versions[0],
        source_kind=source_kinds[0],
        wall_clock_mode="schedule_bound_literal_z",
        quality_status="clean",
        symbols=tuple(sorted(str(value) for value in bars["symbol"].astype(str).unique())),
        start=str(bars["observation_time"].min()),
        end=str(bars["observation_time"].max()),
        row_count=int(len(bars)),
        parquet_sha256=_sha256_bytes(parquet_bytes),
    )


def write_layer1_index_binding(
    bars: pd.DataFrame,
    receipt: Layer1IndexOHLCReceipt,
    *,
    destination: Path,
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    parquet_path = destination / "index_1d_noon_ohlc.parquet"
    receipt_path = destination / "layer1_receipt.json"
    output = bars[
        [
            "symbol",
            "observation_time",
            "available_at",
            "trading_day",
            "open",
            "high",
            "low",
            "close",
            "continuity_segment_id",
            "dataset_version",
            "source_kind",
            "construction_contract",
        ]
    ].copy()
    output.to_parquet(parquet_path, index=False)
    parquet_bytes = parquet_path.read_bytes()
    frozen = Layer1IndexOHLCReceipt(**{**receipt.to_dict(), "parquet_sha256": _sha256_bytes(parquet_bytes)})
    receipt_path.write_text(json.dumps(frozen.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


__all__ = [
    "BINDING_ID",
    "INDEX_SYMBOLS",
    "Layer1IndexOHLCReceipt",
    "build_layer1_index_receipt",
    "fetch_index_noon_ohlc",
    "normalize_index_noon_ohlc",
    "write_layer1_index_binding",
]
