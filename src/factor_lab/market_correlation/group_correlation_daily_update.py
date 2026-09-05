# pyright: reportAny=false, reportArgumentType=false
# pyright: reportIndexIssue=false, reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Daily orchestration for physical group-correlation measurements."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import pandas as pd
import pyarrow.dataset as ds

from factor_lab.core.errors import ValidationError
from factor_lab.market_correlation.contracts_group_timeseries import (
    GroupCorrelationConfig,
    GroupCorrelationSourceIdentity,
    GroupUniverseIdentity,
)
from factor_lab.market_correlation.services.group_correlation_timeseries_service import (
    adapt_datahub_qfq_daily_bars,
    build_group_correlation_bundle,
)
from factor_lab.market_state.group_correlation_bundle import (
    build_group_correlation_market_state_pack,
)

DATASET_ID: Final[str] = "bars_cn_a_1d_qfq_canonical"
DEFAULT_CODE_VERSION: Final[str] = "group-correlation-timeseries-20260804-r3"


@dataclass(frozen=True, slots=True)
class DailyBarsSnapshot:
    dataset_version: str
    dataset_hash: str
    storage_path: Path
    time_range_start: str
    time_range_end: str


def resolve_latest_qfq_daily_snapshot(datahub_root: Path) -> DailyBarsSnapshot:
    database = datahub_root / ".runtime/live/meta/metadata.sqlite3"
    if not database.exists():
        raise ValidationError(f"DataHub metadata database not found: {database}")
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            """
            SELECT dataset_version, time_range_start, time_range_end, storage_uri
            FROM dataset_versions
            WHERE dataset_id = ? AND state = 'READY'
            ORDER BY time_range_end DESC, created_at DESC
            LIMIT 1
            """,
            (DATASET_ID,),
        ).fetchone()
        if row is None:
            raise ValidationError(f"no READY DataHub dataset for {DATASET_ID}")
        version = str(row["dataset_version"])
        digest_row = connection.execute(
            """
            SELECT logical_hash
            FROM dataset_manifests_v2
            WHERE dataset_version = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (version,),
        ).fetchone()
    finally:
        connection.close()
    if digest_row is None or not str(digest_row["logical_hash"] or "").strip():
        raise ValidationError(f"DataHub dataset lacks logical hash: {version}")
    storage = Path(str(row["storage_uri"]))
    if not storage.is_absolute():
        storage = datahub_root / storage
    if not storage.is_dir():
        raise ValidationError(f"DataHub bars storage not found: {storage}")
    return DailyBarsSnapshot(
        dataset_version=version,
        dataset_hash="sha256:" + str(digest_row["logical_hash"]),
        storage_path=storage,
        time_range_start=str(row["time_range_start"]),
        time_range_end=str(row["time_range_end"]),
    )


def run_group_correlation_daily_update(
    *,
    datahub_root: Path,
    manufacturing_members_path: Path,
    output_root: Path,
    market_state_output_root: Path,
    code_version: str = DEFAULT_CODE_VERSION,
    start_date: str = "2009-01-01",
    windows: tuple[int, ...] = (20, 60, 120),
    min_coverage_ratio: float = 0.80,
    parallel_workers: int = 3,
    manufacturing_quality_audit_path: Path | None = None,
    force_full: bool = False,
) -> dict[str, object]:
    """Update both measurement series, then publish one additive indicator pack."""

    snapshot = resolve_latest_qfq_daily_snapshot(datahub_root)
    all_root = output_root / "all-market"
    manufacturing_root = output_root / "manufacturing-core"
    if not force_full and _outputs_are_current(
        (all_root, manufacturing_root), snapshot=snapshot, code_version=code_version
    ):
        pack = _ensure_measurement_pack(
            all_root=all_root,
            manufacturing_root=manufacturing_root,
            market_state_output_root=market_state_output_root,
            code_version=code_version,
            manufacturing_quality_audit_path=manufacturing_quality_audit_path,
        )
        return {
            "status": "reused",
            "source": _snapshot_payload(snapshot),
            "all_market": _reused_result(all_root),
            "manufacturing": _reused_result(manufacturing_root),
            "market_state_pack": pack,
        }

    members_payload = _read_json(manufacturing_members_path)
    raw_members = members_payload.get("members")
    if not isinstance(raw_members, list):
        raise ValidationError("manufacturing definition lacks members list")
    member_symbols = tuple(
        str(cast(dict[str, object], row).get("symbol", "")).strip()
        for row in raw_members
        if isinstance(row, dict) and str(row.get("symbol", "")).strip()
    )
    if len(member_symbols) < 2:
        raise ValidationError("manufacturing definition requires at least two members")

    bars = _read_daily_bars(snapshot.storage_path, start_date=start_date)
    bars = adapt_datahub_qfq_daily_bars(bars)
    config = GroupCorrelationConfig(
        windows=windows,
        min_coverage_ratio=min_coverage_ratio,
        parallel_workers=parallel_workers,
    )
    source = GroupCorrelationSourceIdentity(
        dataset_version=snapshot.dataset_version,
        dataset_hash=snapshot.dataset_hash,
    )
    all_result = build_group_correlation_bundle(
        bars,
        universe=GroupUniverseIdentity(
            universe_id="cn_a_all_market",
            universe_version="daily_eligible_market_v1",
            pit_grade="strict_market_pit",
            membership_semantics="daily_eligible_market",
        ),
        source=source,
        output_root=all_root,
        config=config,
        code_version=code_version,
        force_full=force_full,
    )
    manufacturing_result = build_group_correlation_bundle(
        bars,
        universe=GroupUniverseIdentity(
            universe_id=str(
                members_payload.get("universe_id", "cn_a_manufacturing_core_v1")
            ),
            universe_version=str(
                members_payload.get("universe_version", "manufacturing_core_v1")
            ),
            pit_grade=str(
                members_payload.get("pit_grade", "index_construction_only")
            ),
            membership_semantics=str(
                members_payload.get(
                    "membership_semantics",
                    "fixed_version_index_construction_backcast",
                )
            ),
            metadata={
                "measurement_role": "market_group_indicator",
                "strategy_effectiveness_claim": False,
            },
        ),
        source=source,
        output_root=manufacturing_root,
        config=config,
        member_symbols=member_symbols,
        code_version=code_version,
        force_full=force_full,
    )
    pack = _ensure_measurement_pack(
        all_root=all_root,
        manufacturing_root=manufacturing_root,
        market_state_output_root=market_state_output_root,
        code_version=code_version,
        manufacturing_quality_audit_path=manufacturing_quality_audit_path,
    )
    return {
        "status": "updated",
        "source": _snapshot_payload(snapshot),
        "all_market": all_result,
        "manufacturing": manufacturing_result,
        "market_state_pack": pack,
    }


def _read_daily_bars(storage: Path, *, start_date: str) -> pd.DataFrame:
    parquet_files = sorted(storage.rglob("*.parquet"))
    if not parquet_files:
        raise ValidationError(f"DataHub qfq dataset has no parquet files: {storage}")
    dataset = ds.dataset(
        [str(path) for path in parquet_files], format="parquet", partitioning=None
    )
    expression = ds.field("trading_day") >= start_date
    if "instrument_type" in dataset.schema.names:
        expression = expression & (ds.field("instrument_type") == "stock")
    columns = [
        "symbol",
        "trading_day",
        "close",
        "available_at",
        "dataset_version",
    ]
    missing = set(columns) - set(dataset.schema.names)
    if missing:
        raise ValidationError(f"DataHub qfq dataset missing columns: {sorted(missing)}")
    return dataset.to_table(columns=columns, filter=expression).to_pandas(
        strings_to_categorical=True
    )


def _outputs_are_current(
    roots: tuple[Path, Path], *, snapshot: DailyBarsSnapshot, code_version: str
) -> bool:
    expected_last = snapshot.time_range_end[:10]
    for root in roots:
        path = root / "current_manifest.json"
        if not path.exists():
            return False
        payload = _read_json(path)
        source = payload.get("source")
        if not isinstance(source, dict):
            return False
        if source.get("dataset_version") != snapshot.dataset_version:
            return False
        if source.get("dataset_hash") != snapshot.dataset_hash:
            return False
        if payload.get("last_observation_date") != expected_last:
            return False
        if payload.get("code_version") != code_version:
            return False
    return True


def _ensure_measurement_pack(
    *,
    all_root: Path,
    manufacturing_root: Path,
    market_state_output_root: Path,
    code_version: str,
    manufacturing_quality_audit_path: Path | None,
) -> dict[str, object]:
    return build_group_correlation_market_state_pack(
        (
            all_root / "current_manifest.json",
            manufacturing_root / "current_manifest.json",
        ),
        output_root=market_state_output_root,
        code_version=code_version,
        manufacturing_quality_audit_path=manufacturing_quality_audit_path,
    )


def _reused_result(root: Path) -> dict[str, object]:
    manifest = _read_json(root / "current_manifest.json")
    return {
        "bundle_id": manifest["bundle_id"],
        "manifest_path": root / "current_manifest.json",
        "build_mode": "reused",
        "reused_existing": True,
    }


def _snapshot_payload(snapshot: DailyBarsSnapshot) -> dict[str, object]:
    return {
        "dataset_id": DATASET_ID,
        "dataset_version": snapshot.dataset_version,
        "dataset_hash": snapshot.dataset_hash,
        "storage_path": snapshot.storage_path,
        "time_range_start": snapshot.time_range_start,
        "time_range_end": snapshot.time_range_end,
    }


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValidationError(f"JSON object required: {path}")
    return {str(key): value for key, value in payload.items()}


__all__ = [
    "DEFAULT_CODE_VERSION",
    "DailyBarsSnapshot",
    "resolve_latest_qfq_daily_snapshot",
    "run_group_correlation_daily_update",
]
