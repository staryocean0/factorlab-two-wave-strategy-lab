# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportMissingTypeArgument=false, reportPrivateUsage=false
"""Rolling Dominant Beta Cloud index service.

This service intentionally does not reuse the TopK ``correlation_core_index``
semantics.  It productizes the market-wide beta cloud as a dedicated index
family whose constituents are selected from the cross-sectional distribution of
each stock's average Fisher-z correlation strength to the full eligible market.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Final, cast

from factor_lab.core.errors import NotFoundError, ValidationError
from factor_lab.core.hashing import sha256_hash
from factor_lab.core.runtime_records import (
    get_record,
    materialize_artifact,
    upsert_record,
    utcnow,
)
from factor_lab.core.runtime_state import runtime_state_store
from factor_lab.governance.services.event_store import event_store
from factor_lab.market_correlation.services.beta_strength_cloud_scan_service import (
    DEFAULT_DOMINANT_BETA_CLOUD_COVERAGE_FLOOR,
    DOMINANT_BETA_CLOUD_SELECTION_RULE,
    scan_beta_strength_cloud,
)
from factor_lab.market_correlation.services.cloudridge_beta_index_rendering import (
    render_cloudridge_beta_index_chart_png,
    write_cloudridge_beta_index_render_artifacts,
)
from factor_lab.market_correlation.services.market_correlation_core_service import (
    DEFAULT_BASE_LEVEL,
    _AssetReturns,
    _build_asset_returns,
    _date_key,
    _optional_float,
    _resolve_rows,
)

CLOUDRIDGE_BETA_INDEX_SCHEMA_VERSION: Final[str] = "cloudridge_beta_index@1.0"
CLOUDRIDGE_BETA_INDEX_ENGINE_VERSION: Final[str] = "cloudridge_beta_strength_cloud@2.0"
DEFAULT_LOOKBACK_WINDOW: Final[int] = 120
DEFAULT_MIN_COVERAGE_WARNING: Final[float] = DEFAULT_DOMINANT_BETA_CLOUD_COVERAGE_FLOOR
DEFAULT_SELECTION_METHOD: Final[str] = (
    "dominant_beta_cloud_avg_fisher_z_strength_left_shoulder"
)
PRICE_NEUTRAL_RETURN_POLICY: Final[str] = "equal_weight_return_only_price_neutral@1.0"
AVAILABLE_CONSTITUENT_RENORMALIZATION_POLICY: Final[str] = (
    "available_constituent_equal_weight_renormalization@1.0"
)

_PUBLIC_CLOUDRIDGE_STRING_RENAMES: Final[dict[str, str]] = dict(
    [
        (
            "correlation_threshold_pool_index_threshold_scan",
            "cloudridge_beta_index_strength_scan",
        ),
        (
            "correlation_threshold_pool_index_constituent_frame",
            "cloudridge_beta_index_constituent_frame",
        ),
        (
            "correlation_threshold_pool_index_level_frame",
            "cloudridge_beta_index_level_frame",
        ),
        (
            "correlation_threshold_pool_index_rebalance",
            "cloudridge_beta_index_rebalance",
        ),
        (
            "correlation_threshold_pool_index_definition",
            "cloudridge_beta_index_definition",
        ),
        ("correlation_threshold_pool_index", "cloudridge_beta_index"),
        ("corr_threshold_pool", "cloudridge_beta_strength_cloud"),
        ("cloudridge_beta_index_strength_scan", "cloudridge_beta_index_strength_scan"),
        (
            "cloudridge_beta_index_constituent_frame",
            "cloudridge_beta_index_constituent_frame",
        ),
        ("cloudridge_beta_index_level_frame", "cloudridge_beta_index_level_frame"),
        ("cloudridge_beta_index_rebalance", "cloudridge_beta_index_rebalance"),
        ("cloudridge_beta_index_definition", "cloudridge_beta_index_definition"),
        ("cloudridge_beta_index", "cloudridge_beta_index"),
        ("cloudridge_beta_strength_cloud", "cloudridge_beta_strength_cloud"),
    ]
)
_PUBLIC_CLOUDRIDGE_KEY_RENAMES: Final[dict[str, str]] = {
    "threshold_scan_id": "strength_scan_id",
    "strength_scan_id": "strength_scan_id",
}
_LEGACY_CLOUDRIDGE_COLLECTIONS: Final[dict[str, str]] = {
    "cloudridge_beta_index_definitions": "correlation_threshold_pool_index_definitions",
    "cloudridge_beta_index_strength_scans": (
        "correlation_threshold_pool_index_threshold_scans"
    ),
    "cloudridge_beta_index_rebalances": "correlation_threshold_pool_index_rebalances",
    "cloudridge_beta_index_constituent_frames": (
        "correlation_threshold_pool_index_constituent_frames"
    ),
    "cloudridge_beta_index_level_frames": (
        "correlation_threshold_pool_index_level_frames"
    ),
}


def default_cloudridge_beta_min_periods(lookback_window: int) -> int:
    if lookback_window < 2:
        raise ValidationError("lookback_window must be >= 2")
    return max(60, math.ceil(0.8 * lookback_window))


def public_cloudridge_payload(value: object) -> object:
    """Return the public CloudRidge vocabulary for persisted internal records."""
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for raw_key, raw_value in value.items():
            key = _PUBLIC_CLOUDRIDGE_KEY_RENAMES.get(str(raw_key), str(raw_key))
            result[key] = public_cloudridge_payload(raw_value)
        return result
    if isinstance(value, list):
        return [public_cloudridge_payload(item) for item in value]
    if isinstance(value, tuple):
        return [public_cloudridge_payload(item) for item in value]
    if isinstance(value, str):
        public_value = value
        for old, new in _PUBLIC_CLOUDRIDGE_STRING_RENAMES.items():
            public_value = public_value.replace(old, new)
        return public_value
    return value


def _string(value: object) -> str:
    return str(value or "").strip()


def _int_value(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _float_value(value: object, default: float = 0.0) -> float:
    parsed = _optional_float(value)
    return parsed if parsed is not None else default


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value)) if isinstance(value, Mapping) else {}


def _record_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [
        dict(cast(Mapping[str, object], row))
        for row in value
        if isinstance(row, Mapping)
    ]


def _collection_records(collection: str) -> dict[str, dict[str, object]]:
    raw = runtime_state_store.load().get(collection, {})
    if not isinstance(raw, Mapping):
        return {}
    return {
        str(record_id): dict(cast(Mapping[str, object], value))
        for record_id, value in raw.items()
        if isinstance(value, Mapping)
    }


def _list_records(collection: str) -> list[dict[str, object]]:
    records = _collection_records(collection)
    legacy_collection = _LEGACY_CLOUDRIDGE_COLLECTIONS.get(collection)
    if legacy_collection:
        for record_id, record in _collection_records(legacy_collection).items():
            records.setdefault(record_id, record)
    return list(records.values())


def _get_cloudridge_record(collection: str, record_id: str) -> dict[str, object] | None:
    record = get_record(collection, record_id)
    if record is not None:
        return dict(record)
    legacy_collection = _LEGACY_CLOUDRIDGE_COLLECTIONS.get(collection)
    if legacy_collection is None:
        return None
    legacy_record = get_record(legacy_collection, record_id)
    return dict(legacy_record) if legacy_record is not None else None


def _cloudridge_legacy_to_current_collections() -> dict[str, str]:
    return {
        legacy_collection: current_collection
        for current_collection, legacy_collection in (
            _LEGACY_CLOUDRIDGE_COLLECTIONS.items()
        )
    }


def migrate_legacy_cloudridge_runtime_records(
    *, dry_run: bool = False
) -> dict[str, object]:
    """Physically move legacy CloudRidge records into current collections.

    Historical runtime databases may still contain records under the retired
    ``correlation_threshold_pool_index_*`` collections.  New code reads those
    collections as a fallback, but the active runtime should not keep writing or
    carrying old collection names.  This migration copies absent legacy records
    into their ``cloudridge_beta_index_*`` collection, normalizes the public
    payload vocabulary, then removes the migrated legacy rows.

    Conflicting records are not overwritten and remain in the legacy collection
    so the migration is lossless and retryable after manual review.
    """

    state = runtime_state_store.load()
    collection_reports: list[dict[str, object]] = []
    total_migrated = 0
    total_duplicates = 0
    total_conflicts = 0
    total_remaining_legacy = 0

    for legacy_collection, current_collection in (
        _cloudridge_legacy_to_current_collections().items()
    ):
        legacy_records = cast(
            dict[str, dict[str, object]], state.get(legacy_collection, {})
        )
        current_records = cast(
            dict[str, dict[str, object]], state.get(current_collection, {})
        )
        legacy_record_count = len(legacy_records)
        migrated_ids: list[str] = []
        duplicate_ids: list[str] = []
        conflict_ids: list[str] = []

        for record_id, record in legacy_records.items():
            normalized = public_cloudridge_payload(record)
            normalized_record = (
                dict(cast(Mapping[str, object], normalized))
                if isinstance(normalized, Mapping)
                else dict(record)
            )
            existing_record = current_records.get(record_id)
            if existing_record is not None:
                if existing_record == normalized_record:
                    duplicate_ids.append(record_id)
                else:
                    conflict_ids.append(record_id)
                continue

            migrated_ids.append(record_id)
            if not dry_run:
                current_records[record_id] = normalized_record

        if not dry_run:
            for record_id in migrated_ids + duplicate_ids:
                legacy_records.pop(record_id, None)

        remaining_legacy = len(legacy_records) - (
            0 if not dry_run else len(migrated_ids) + len(duplicate_ids)
        )
        remaining_legacy = max(0, remaining_legacy)
        collection_report = {
            "legacy_collection": legacy_collection,
            "current_collection": current_collection,
            "legacy_record_count": legacy_record_count,
            "migrated_count": len(migrated_ids),
            "duplicate_count": len(duplicate_ids),
            "conflict_count": len(conflict_ids),
            "remaining_legacy_count": remaining_legacy,
            "migrated_ids": migrated_ids,
            "duplicate_ids": duplicate_ids,
            "conflict_ids": conflict_ids,
        }
        collection_reports.append(collection_report)
        total_migrated += len(migrated_ids)
        total_duplicates += len(duplicate_ids)
        total_conflicts += len(conflict_ids)
        total_remaining_legacy += remaining_legacy

    report: dict[str, object] = {
        "migration": "cloudridge_beta_index_runtime_collection_migration",
        "schema_version": CLOUDRIDGE_BETA_INDEX_SCHEMA_VERSION,
        "dry_run": dry_run,
        "migrated_count": total_migrated,
        "duplicate_count": total_duplicates,
        "conflict_count": total_conflicts,
        "remaining_legacy_count": total_remaining_legacy,
        "collections": collection_reports,
    }

    if not dry_run:
        runtime_state_store.save(state)
        _ = event_store.append(
            event_type="cloudridge_beta_index_runtime_collections.migrated",
            payload={
                "migrated_count": total_migrated,
                "duplicate_count": total_duplicates,
                "conflict_count": total_conflicts,
                "remaining_legacy_count": total_remaining_legacy,
            },
        )

    return report


def _row_date(row: Mapping[str, object]) -> str | None:
    value = row.get("timestamp") or row.get("date") or row.get("asof_date")
    if value is None or not _string(value):
        return None
    try:
        return _date_key(value, field_name="timestamp/date")
    except ValidationError:
        return None


def _next_calendar_day(raw_date: str) -> str:
    return (date.fromisoformat(raw_date) + timedelta(days=1)).isoformat()


def _resolve_effective_date(
    *,
    rows: Sequence[Mapping[str, object]],
    as_of_date: str,
    effective_date: str | None,
) -> str:
    if effective_date:
        resolved = _date_key(effective_date, field_name="effective_date")
        if resolved <= as_of_date:
            raise ValidationError("effective_date must be after formation/as_of_date")
        return resolved
    dates = sorted({row_date for row in rows if (row_date := _row_date(row))})
    inferred = next((candidate for candidate in dates if candidate > as_of_date), None)
    return inferred or _next_calendar_day(as_of_date)


def _return_for_effective_date(
    *,
    asset: _AssetReturns | None,
    effective_date: str,
) -> float | None:
    if asset is None:
        return None
    if effective_date in asset.returns_by_date:
        return asset.returns_by_date[effective_date]
    close = asset.close_by_date.get(effective_date)
    previous_dates = [
        row_date for row_date in asset.close_by_date if row_date < effective_date
    ]
    if close is None or not previous_dates:
        return None
    previous = asset.close_by_date[max(previous_dates)]
    if previous <= 0.0:
        return None
    return close / previous - 1.0


def _member_rows(component: Mapping[str, object]) -> list[dict[str, object]]:
    members = _record_rows(component.get("members", []))
    if not members:
        return []
    return sorted(
        members,
        key=lambda row: (
            _int_value(row.get("beta_strength_rank"), 1_000_000_000),
            _string(row.get("asset_id")),
        ),
    )


def _latest_by_date(
    records: Sequence[Mapping[str, object]],
    *,
    date_key: str,
    before_date: str | None = None,
) -> dict[str, object]:
    candidates: list[dict[str, object]] = []
    for record in records:
        value = _string(record.get(date_key))
        if before_date and value >= before_date:
            continue
        candidates.append(dict(record))
    return max(candidates, key=lambda item: _string(item.get(date_key)), default={})


class CloudRidgeBetaIndexService:
    """Create, rebalance, and read rolling beta-strength-cloud indexes."""

    def create_index_definition(
        self,
        *,
        name: str,
        universe_ref: str,
        lookback_window: int = DEFAULT_LOOKBACK_WINDOW,
        min_periods: int | None = None,
        peak_strategy: str = DOMINANT_BETA_CLOUD_SELECTION_RULE,
        weighting_method: str = "equal_weight",
        return_column: str = "return",
        price_column: str = "close",
        base_level: float = DEFAULT_BASE_LEVEL,
        min_coverage_warning: float = DEFAULT_MIN_COVERAGE_WARNING,
        coverage_floor: float | None = None,
        data_source_ref: str = "datahub_pit_daily_bars_or_inline_rows",
        description: str = "",
        created_by: str = "local_write",
    ) -> dict[str, object]:
        if not name.strip():
            raise ValidationError("name is required")
        if not universe_ref.strip():
            raise ValidationError("universe_ref is required")
        if lookback_window < 2:
            raise ValidationError("lookback_window must be >= 2")
        resolved_min_periods = (
            default_cloudridge_beta_min_periods(lookback_window)
            if min_periods is None
            else min_periods
        )
        if resolved_min_periods < 2:
            raise ValidationError("min_periods must be >= 2")
        if weighting_method != "equal_weight":
            raise ValidationError(
                "only equal_weight CloudRidge Beta indexes are supported"
            )
        if base_level <= 0.0 or not math.isfinite(base_level):
            raise ValidationError("base_level must be positive")
        resolved_coverage_floor = (
            DEFAULT_MIN_COVERAGE_WARNING if coverage_floor is None else coverage_floor
        )
        if not 0.0 <= resolved_coverage_floor <= 1.0:
            raise ValidationError("coverage_floor must be in [0, 1]")
        index_id = (
            "cldrgidx_"
            + sha256_hash(
                {
                    "name": name,
                    "universe_ref": universe_ref,
                    "lookback_window": lookback_window,
                    "min_periods": resolved_min_periods,
                    "peak_strategy": peak_strategy,
                    "coverage_floor": round(resolved_coverage_floor, 10),
                    "weighting_method": weighting_method,
                }
            )[:20]
        )
        payload = {
            "schema_version": CLOUDRIDGE_BETA_INDEX_SCHEMA_VERSION,
            "engine_version": CLOUDRIDGE_BETA_INDEX_ENGINE_VERSION,
            "record_type": "cloudridge_beta_index_definition",
            "index_id": index_id,
            "name": name,
            "description": description,
            "universe_ref": universe_ref,
            "data_source_ref": data_source_ref,
            "lookback_window": lookback_window,
            "min_periods": resolved_min_periods,
            "correlation_method": "pearson_avg_fisher_z_strength",
            "neutralization_mode": "raw",
            "selection_method": DEFAULT_SELECTION_METHOD,
            "peak_strategy": peak_strategy,
            "weighting_method": weighting_method,
            "index_return_policy": PRICE_NEUTRAL_RETURN_POLICY,
            "absolute_price_neutral": True,
            "rebalance_rule": "daily_pit_as_of_next_trading_day_effective",
            "coverage_floor": round(resolved_coverage_floor, 10),
            "min_coverage_warning": round(min_coverage_warning, 10),
            "strength_distribution_role": "authoritative_index_selection",
            "dominant_beta_cloud_formula": (
                "score_i=tanh(mean_j(arctanh(corr_ij))); "
                "select score_i at or right of the cross-sectional left shoulder "
                "mu_z - sigma_z, with coverage_floor hard fallback"
            ),
            "return_column": return_column,
            "price_column": price_column,
            "base_level": round(base_level, 10),
            "asset_kind": "cloudridge_beta_index",
            "auto_action_taken": False,
            "factor_lifecycle_mutation": False,
            "created_by": created_by,
            "created_at": utcnow(),
        }
        artifact = materialize_artifact(
            index_id, "cloudridge_beta_index_definition", payload
        )
        record: dict[str, object] = {
            **payload,
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "storage_uri": artifact.storage_uri,
        }
        upsert_record("cloudridge_beta_index_definitions", index_id, record)
        _ = event_store.append(
            event_type="cloudridge_beta_index_definition.created",
            payload={"index_id": index_id},
            run_id=index_id,
        )
        return record

    def list_index_definitions(
        self, *, universe_ref: str | None = None
    ) -> list[dict[str, object]]:
        return sorted(
            [
                record
                for record in _list_records(
                    "cloudridge_beta_index_definitions"
                )
                if universe_ref is None
                or _string(record.get("universe_ref")) == universe_ref
            ],
            key=lambda item: _string(item.get("created_at")),
            reverse=True,
        )

    def get_index_definition(self, index_id: str) -> dict[str, object]:
        record = _get_cloudridge_record("cloudridge_beta_index_definitions", index_id)
        if record is None:
            raise NotFoundError(
                f"CloudRidge Beta index not found: {index_id}"
            )
        return dict(record)

    def rebalance_index(
        self,
        *,
        index_id: str,
        rows: Sequence[Mapping[str, object]] | None = None,
        dataset_version: str | None = None,
        as_of_date: str,
        effective_date: str | None = None,
        force: bool = False,
        generated_by: str = "local_write",
    ) -> dict[str, object]:
        definition = self.get_index_definition(index_id)
        as_of_date = _date_key(as_of_date, field_name="as_of_date")
        working_rows, resolved_dataset_version, source_mode = _resolve_rows(
            rows=rows,
            dataset_version=dataset_version,
        )
        resolved_effective_date = _resolve_effective_date(
            rows=working_rows,
            as_of_date=as_of_date,
            effective_date=effective_date,
        )
        existing = self._existing_rebalance(index_id=index_id, as_of_date=as_of_date)
        if existing and not force:
            result = self._rebalance_result(existing)
            result["idempotent_skip"] = True
            result["idempotency_key"] = f"{index_id}:{as_of_date}"
            return result

        scan = scan_beta_strength_cloud(
            rows=working_rows,
            dataset_version=resolved_dataset_version,
            universe_ref=_string(definition["universe_ref"]),
            as_of_date=as_of_date,
            lookback_window=_int_value(definition.get("lookback_window")),
            min_periods=_int_value(definition.get("min_periods")),
            return_column=_string(definition.get("return_column")) or "return",
            price_column=_string(definition.get("price_column")) or "close",
            coverage_floor=_float_value(
                definition.get("coverage_floor"),
                _float_value(
                    definition.get("min_coverage_warning"), DEFAULT_MIN_COVERAGE_WARNING
                ),
            ),
        )
        strength_scan = self._materialize_strength_scan(
            definition=definition,
            scan=scan,
            as_of_date=as_of_date,
            generated_by=generated_by,
        )
        selection = _mapping(scan.get("dominant_beta_cloud"))
        if _string(selection.get("status")) != "selected":
            coverage_floor = selection.get("coverage_floor")
            message = (
                "dominant beta strength cloud requires selected coverage "
                f">= {coverage_floor}"
            )
            raise ValidationError(message)
        component = _mapping(selection.get("component"))
        selected_members = _member_rows(component)
        if len(selected_members) < 2:
            raise ValidationError("dominant beta strength cloud produced no pool")

        previous_constituents = self._previous_constituents(
            index_id=index_id,
            before_date=resolved_effective_date,
        )
        rebalance_id = (
            "cldrgrebal_"
            + sha256_hash({"index_id": index_id, "as_of_date": as_of_date})[:20]
        )
        constituent_frame = self._materialize_constituent_frame(
            definition=definition,
            scan=strength_scan,
            rebalance_id=rebalance_id,
            selected_members=selected_members,
            selection=selection,
            as_of_date=as_of_date,
            effective_date=resolved_effective_date,
            generated_by=generated_by,
        )
        level_frame = self._materialize_level_frame(
            definition=definition,
            scan=strength_scan,
            rebalance_id=rebalance_id,
            constituent_frame=constituent_frame,
            selected_members=selected_members,
            rows=working_rows,
            dataset_version=resolved_dataset_version,
            effective_date=resolved_effective_date,
            previous_constituents=previous_constituents,
            generated_by=generated_by,
        )
        rebalance = self._materialize_rebalance(
            definition=definition,
            scan=strength_scan,
            rebalance_id=rebalance_id,
            constituent_frame=constituent_frame,
            level_frame=level_frame,
            selected_members=selected_members,
            previous_constituents=previous_constituents,
            as_of_date=as_of_date,
            effective_date=resolved_effective_date,
            dataset_version=resolved_dataset_version,
            source_mode=source_mode,
            selection=selection,
            force=force,
            generated_by=generated_by,
        )
        return {
            "index": public_cloudridge_payload(definition),
            "strength_scan": public_cloudridge_payload(strength_scan),
            "rebalance": public_cloudridge_payload(rebalance),
            "constituent_frame": public_cloudridge_payload(constituent_frame),
            "level_frame": public_cloudridge_payload(level_frame),
            "idempotent_skip": False,
            "idempotency_key": f"{index_id}:{as_of_date}",
        }

    def rebalance_range(
        self,
        *,
        index_id: str,
        rows: Sequence[Mapping[str, object]] | None = None,
        dataset_version: str | None = None,
        start_date: str,
        end_date: str,
        force: bool = False,
        generated_by: str = "local_write",
    ) -> dict[str, object]:
        definition = self.get_index_definition(index_id)
        start_date = _date_key(start_date, field_name="start_date")
        end_date = _date_key(end_date, field_name="end_date")
        if end_date < start_date:
            raise ValidationError("end_date must be >= start_date")
        working_rows, resolved_dataset_version, _source_mode = _resolve_rows(
            rows=rows,
            dataset_version=dataset_version,
        )
        all_dates = sorted(
            {row_date for row in working_rows if (row_date := _row_date(row))}
        )
        as_of_dates = [
            row_date for row_date in all_dates if start_date <= row_date <= end_date
        ]
        if not as_of_dates:
            raise ValidationError("rebalance range contains no row dates")
        results: list[dict[str, object]] = []
        errors: list[dict[str, object]] = []
        for formation_date in as_of_dates:
            next_effective = next(
                (candidate for candidate in all_dates if candidate > formation_date),
                None,
            )
            if next_effective is None:
                errors.append(
                    {
                        "as_of_date": formation_date,
                        "status": "skipped",
                        "message": "no later effective trading date in rows",
                    }
                )
                continue
            try:
                results.append(
                    self.rebalance_index(
                        index_id=index_id,
                        rows=working_rows,
                        dataset_version=resolved_dataset_version,
                        as_of_date=formation_date,
                        effective_date=next_effective,
                        force=force,
                        generated_by=generated_by,
                    )
                )
            except ValidationError as exc:
                errors.append(
                    {
                        "as_of_date": formation_date,
                        "status": "error",
                        "message": str(exc),
                    }
                )
        if not results:
            raise ValidationError("rebalance range produced no successful rebalances")
        return {
            "index": public_cloudridge_payload(definition),
            "start_date": start_date,
            "end_date": end_date,
            "dataset_version": resolved_dataset_version,
            "results": results,
            "rebalances": [result["rebalance"] for result in results],
            "errors": errors,
            "total": len(results),
            "error_count": len(errors),
            "force": force,
        }

    def list_rebalances(
        self,
        index_id: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, object]]:
        if start_date:
            start_date = _date_key(start_date, field_name="start_date")
        if end_date:
            end_date = _date_key(end_date, field_name="end_date")
        return sorted(
            [
                record
                for record in _list_records(
                    "cloudridge_beta_index_rebalances"
                )
                if _string(record.get("index_id")) == index_id
                and (
                    start_date is None
                    or _string(record.get("formation_date")) >= start_date
                )
                and (
                    end_date is None
                    or _string(record.get("formation_date")) <= end_date
                )
            ],
            key=lambda item: _string(item.get("formation_date")),
            reverse=True,
        )

    def list_level_frames(self, index_id: str) -> list[dict[str, object]]:
        return sorted(
            [
                record
                for record in _list_records(
                    "cloudridge_beta_index_level_frames"
                )
                if _string(record.get("index_id")) == index_id
            ],
            key=lambda item: _string(item.get("end_date")),
        )

    def list_constituent_frames(self, index_id: str) -> list[dict[str, object]]:
        return sorted(
            [
                record
                for record in _list_records(
                    "cloudridge_beta_index_constituent_frames"
                )
                if _string(record.get("index_id")) == index_id
            ],
            key=lambda item: _string(item.get("effective_date")),
        )

    def level_rows(self, index_id: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for frame in self.list_level_frames(index_id):
            rows.extend(_record_rows(frame.get("rows", [])))
        return sorted(rows, key=lambda row: _string(row.get("date")))

    def constituent_rows(self, index_id: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for frame in self.list_constituent_frames(index_id):
            rows.extend(_record_rows(frame.get("rows", [])))
        return sorted(
            rows,
            key=lambda row: (
                _string(row.get("effective_date")),
                _int_value(row.get("rank")),
            ),
        )

    def render_index(
        self,
        *,
        index_id: str,
        output_prefix: str | Path,
        price_scale: str = "linear",
    ) -> dict[str, object]:
        _ = self.get_index_definition(index_id)
        level_rows = self.level_rows(index_id)
        constituent_rows = self.constituent_rows(index_id)
        if not level_rows:
            raise ValidationError("CloudRidge Beta index has no level rows to render")
        prefix = Path(output_prefix)
        chart_png = render_cloudridge_beta_index_chart_png(
            index_id=index_id,
            level_rows=level_rows,
            output_path=prefix.with_suffix(".kline.png"),
            price_scale=price_scale,
        )
        return write_cloudridge_beta_index_render_artifacts(
            index_id=index_id,
            level_rows=level_rows,
            constituent_rows=constituent_rows,
            output_prefix=prefix,
            chart_png=chart_png,
            price_scale=price_scale,
        )

    def _existing_rebalance(
        self, *, index_id: str, as_of_date: str
    ) -> dict[str, object]:
        return next(
            (
                record
                for record in self.list_rebalances(index_id)
                if _string(record.get("formation_date")) == as_of_date
            ),
            {},
        )

    def _rebalance_result(self, rebalance: Mapping[str, object]) -> dict[str, object]:
        index_id = _string(rebalance.get("index_id"))
        scan_id = _string(
            rebalance.get("strength_scan_id") or rebalance.get("threshold_scan_id")
        )
        constituent_frame_id = _string(rebalance.get("constituent_frame_id"))
        level_frame_id = _string(rebalance.get("level_frame_id"))
        return {
            "index": public_cloudridge_payload(self.get_index_definition(index_id)),
            "strength_scan": public_cloudridge_payload(
                dict(
                    _get_cloudridge_record(
                        "cloudridge_beta_index_strength_scans", scan_id
                    )
                    or {}
                )
            ),
            "rebalance": public_cloudridge_payload(dict(rebalance)),
            "constituent_frame": public_cloudridge_payload(
                dict(
                    _get_cloudridge_record(
                        "cloudridge_beta_index_constituent_frames",
                        constituent_frame_id,
                    )
                    or {}
                )
            ),
            "level_frame": public_cloudridge_payload(
                dict(
                    _get_cloudridge_record(
                        "cloudridge_beta_index_level_frames", level_frame_id
                    )
                    or {}
                )
            ),
        }

    def _previous_constituents(
        self,
        *,
        index_id: str,
        before_date: str,
    ) -> list[dict[str, object]]:
        previous = _latest_by_date(
            self.list_constituent_frames(index_id),
            date_key="effective_date",
            before_date=before_date,
        )
        return _record_rows(previous.get("rows", []))

    def _latest_level(self, index_id: str, *, before_date: str) -> float:
        rows = [
            row
            for row in self.level_rows(index_id)
            if _string(row.get("date")) < before_date
        ]
        if not rows:
            definition = self.get_index_definition(index_id)
            return _float_value(definition.get("base_level"), DEFAULT_BASE_LEVEL)
        latest = max(rows, key=lambda row: _string(row.get("date")))
        return _float_value(latest.get("index_level"), DEFAULT_BASE_LEVEL)

    def _turnover(
        self,
        previous_constituents: Sequence[Mapping[str, object]],
        selected_members: Sequence[Mapping[str, object]],
    ) -> float:
        current_count = len(selected_members)
        if current_count == 0:
            return 0.0
        current = {
            _string(item.get("asset_id")): 1.0 / current_count
            for item in selected_members
        }
        if not previous_constituents:
            return 1.0
        previous = {
            _string(item.get("asset_id")): _float_value(item.get("target_weight"))
            for item in previous_constituents
        }
        keys = set(previous) | set(current)
        return 0.5 * sum(
            abs(current.get(key, 0.0) - previous.get(key, 0.0)) for key in keys
        )

    def _materialize_strength_scan(
        self,
        *,
        definition: Mapping[str, object],
        scan: Mapping[str, object],
        as_of_date: str,
        generated_by: str,
    ) -> dict[str, object]:
        scan_id = (
            "cldrgscan_"
            + sha256_hash(
                {
                    "index_id": definition["index_id"],
                    "dataset_version": scan.get("dataset_version"),
                    "as_of_date": as_of_date,
                    "selection": scan.get("dominant_beta_cloud"),
                }
            )[:20]
        )
        payload = {
            **dict(scan),
            "schema_version": CLOUDRIDGE_BETA_INDEX_SCHEMA_VERSION,
            "engine_version": CLOUDRIDGE_BETA_INDEX_ENGINE_VERSION,
            "record_type": "cloudridge_beta_index_strength_scan",
            "strength_scan_id": scan_id,
            "index_id": definition["index_id"],
            "generated_by": generated_by,
            "generated_at": utcnow(),
        }
        artifact = materialize_artifact(
            scan_id, "cloudridge_beta_index_strength_scan", payload
        )
        record: dict[str, object] = {
            **payload,
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "storage_uri": artifact.storage_uri,
        }
        upsert_record(
            "cloudridge_beta_index_strength_scans", scan_id, record
        )
        return record

    def _materialize_constituent_frame(
        self,
        *,
        definition: Mapping[str, object],
        scan: Mapping[str, object],
        rebalance_id: str,
        selected_members: Sequence[Mapping[str, object]],
        selection: Mapping[str, object],
        as_of_date: str,
        effective_date: str,
        generated_by: str,
    ) -> dict[str, object]:
        selected_count = len(selected_members)
        target_weight = 1.0 / selected_count if selected_count else 0.0
        selected_strength_threshold = _float_value(selection.get("strength_threshold"))
        selected_cutoff = _float_value(
            selection.get("strength_selected_cutoff"), selected_strength_threshold
        )
        rows = [
            {
                "index_id": definition["index_id"],
                "strength_scan_id": scan["strength_scan_id"],
                "rebalance_id": rebalance_id,
                "formation_date": as_of_date,
                "effective_date": effective_date,
                "asset_id": _string(item.get("asset_id")),
                "symbol": _string(item.get("symbol")) or _string(item.get("asset_id")),
                "rank": rank,
                "selected_strength_threshold": round(selected_strength_threshold, 10),
                "selected_strength_cutoff": round(selected_cutoff, 10),
                "target_weight": round(target_weight, 12),
                "weighting_method": "equal_weight",
                "reason_code": "selected_dominant_beta_strength_left_shoulder",
                "beta_strength_rank": _int_value(item.get("beta_strength_rank")),
                "beta_strength": round(_float_value(item.get("beta_strength")), 10),
                "beta_strength_z": round(
                    _float_value(item.get("beta_strength_z")), 10
                ),
                "avg_corr": round(_float_value(item.get("avg_corr")), 10),
                "corr_sum": round(_float_value(item.get("corr_sum")), 10),
                "pair_count": _int_value(item.get("pair_count")),
                "industry": _string(item.get("industry")),
                "sector": _string(item.get("sector")),
                "size_bucket": _string(item.get("size_bucket")) or "unknown",
                "observation_count": _int_value(item.get("observation_count")),
            }
            for rank, item in enumerate(selected_members, start=1)
        ]
        frame_id = (
            "cldrgconst_"
            + sha256_hash(
                {
                    "index_id": definition["index_id"],
                    "as_of_date": as_of_date,
                    "rows": rows,
                }
            )[:20]
        )
        payload = {
            "schema_version": CLOUDRIDGE_BETA_INDEX_SCHEMA_VERSION,
            "engine_version": CLOUDRIDGE_BETA_INDEX_ENGINE_VERSION,
            "record_type": "cloudridge_beta_index_constituent_frame",
            "constituent_frame_id": frame_id,
            "index_id": definition["index_id"],
            "strength_scan_id": scan["strength_scan_id"],
            "rebalance_id": rebalance_id,
            "formation_date": as_of_date,
            "effective_date": effective_date,
            "selected_strength_threshold": round(selected_strength_threshold, 10),
            "selected_strength_cutoff": round(selected_cutoff, 10),
            "weighting_method": "equal_weight",
            "selected_count": selected_count,
            "rows": rows,
            "selection_diagnostics": {
                "peak_strategy": definition.get("peak_strategy"),
                "selection_method": definition.get("selection_method"),
                "dominant_beta_cloud": dict(selection),
                "component_members_truncated": bool(
                    _mapping(selection.get("component")).get("members_truncated", False)
                ),
            },
            "auto_action_taken": False,
            "factor_lifecycle_mutation": False,
            "generated_by": generated_by,
            "generated_at": utcnow(),
        }
        artifact = materialize_artifact(
            frame_id, "cloudridge_beta_index_constituent_frame", payload
        )
        record: dict[str, object] = {
            **payload,
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "storage_uri": artifact.storage_uri,
        }
        upsert_record(
            "cloudridge_beta_index_constituent_frames", frame_id, record
        )
        return record

    def _materialize_level_frame(
        self,
        *,
        definition: Mapping[str, object],
        scan: Mapping[str, object],
        rebalance_id: str,
        constituent_frame: Mapping[str, object],
        selected_members: Sequence[Mapping[str, object]],
        rows: Sequence[Mapping[str, object]],
        dataset_version: str,
        effective_date: str,
        previous_constituents: Sequence[Mapping[str, object]],
        generated_by: str,
    ) -> dict[str, object]:
        selected_ids = [_string(item.get("asset_id")) for item in selected_members]
        level_assets, level_row_diagnostics = _build_asset_returns(
            rows=rows,
            as_of_date=None,
            lookback_window=None,
            return_column=_string(definition.get("return_column")) or "return",
            price_column=_string(definition.get("price_column")) or "close",
            enforce_pit=False,
        )
        returns: dict[str, float] = {}
        missing: list[str] = []
        for asset_id in selected_ids:
            value = _return_for_effective_date(
                asset=level_assets.get(asset_id),
                effective_date=effective_date,
            )
            if value is None:
                missing.append(asset_id)
            else:
                returns[asset_id] = value
        if not returns:
            raise ValidationError(
                "CloudRidge Beta index level calculation has no valid "
                "constituent returns"
            )
        available_count = len(returns)
        coverage_ratio = available_count / len(selected_ids) if selected_ids else 0.0
        renormalized_weight = 1.0 / available_count
        daily_return = sum(value * renormalized_weight for value in returns.values())
        previous_level = self._latest_level(
            _string(definition["index_id"]), before_date=effective_date
        )
        level = previous_level * (1.0 + daily_return)
        previous_ids = {_string(item.get("asset_id")) for item in previous_constituents}
        current_ids = set(selected_ids)
        turnover = self._turnover(previous_constituents, selected_members)
        return_contributions = [
            {
                "asset_id": asset_id,
                "return": round(return_value, 10),
                "normalized_weight": round(renormalized_weight, 12),
                "contribution": round(return_value * renormalized_weight, 10),
            }
            for asset_id, return_value in sorted(returns.items())
        ]
        row = {
            "index_id": definition["index_id"],
            "date": effective_date,
            "formation_date": constituent_frame["formation_date"],
            "effective_date": effective_date,
            "daily_return": round(daily_return, 10),
            "index_level": round(level, 10),
            "previous_level": round(previous_level, 10),
            "coverage_ratio": round(coverage_ratio, 10),
            "selected_count": len(selected_ids),
            "available_return_count": available_count,
            "index_return_policy": PRICE_NEUTRAL_RETURN_POLICY,
            "absolute_price_neutral": True,
            "missing_constituents": sorted(missing),
            "available_constituents": sorted(returns),
            "return_contributions": return_contributions,
            "turnover": round(turnover, 10),
            "added_constituents": sorted(current_ids - previous_ids),
            "dropped_constituents": sorted(previous_ids - current_ids),
        }
        frame_id = (
            "cldrglvl_"
            + sha256_hash(
                {
                    "index_id": definition["index_id"],
                    "scan_id": scan["strength_scan_id"],
                    "row": row,
                }
            )[:20]
        )
        payload = {
            "schema_version": CLOUDRIDGE_BETA_INDEX_SCHEMA_VERSION,
            "engine_version": CLOUDRIDGE_BETA_INDEX_ENGINE_VERSION,
            "record_type": "cloudridge_beta_index_level_frame",
            "level_frame_id": frame_id,
            "index_id": definition["index_id"],
            "strength_scan_id": scan["strength_scan_id"],
            "rebalance_id": rebalance_id,
            "constituent_frame_id": constituent_frame["constituent_frame_id"],
            "price_dataset_version": dataset_version,
            "start_date": effective_date,
            "end_date": effective_date,
            "row_count": 1,
            "rows": [row],
            "summary": {
                "latest_level": round(level, 10),
                "latest_daily_return": round(daily_return, 10),
                "min_coverage_ratio": round(coverage_ratio, 10),
                "missing_constituent_count": len(missing),
            },
            "coverage_diagnostics": {
                "coverage_ratio": round(coverage_ratio, 10),
                "missing_constituents": sorted(missing),
                "renormalized": bool(missing),
                "policy": AVAILABLE_CONSTITUENT_RENORMALIZATION_POLICY,
                "return_policy": PRICE_NEUTRAL_RETURN_POLICY,
                "absolute_price_neutral": True,
                "level_row_diagnostics": level_row_diagnostics,
            },
            "auto_action_taken": False,
            "factor_lifecycle_mutation": False,
            "generated_by": generated_by,
            "generated_at": utcnow(),
        }
        artifact = materialize_artifact(
            frame_id, "cloudridge_beta_index_level_frame", payload
        )
        record: dict[str, object] = {
            **payload,
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "storage_uri": artifact.storage_uri,
        }
        upsert_record("cloudridge_beta_index_level_frames", frame_id, record)
        return record

    def _materialize_rebalance(
        self,
        *,
        definition: Mapping[str, object],
        scan: Mapping[str, object],
        rebalance_id: str,
        constituent_frame: Mapping[str, object],
        level_frame: Mapping[str, object],
        selected_members: Sequence[Mapping[str, object]],
        previous_constituents: Sequence[Mapping[str, object]],
        as_of_date: str,
        effective_date: str,
        dataset_version: str,
        source_mode: str,
        selection: Mapping[str, object],
        force: bool,
        generated_by: str,
    ) -> dict[str, object]:
        previous_ids = {_string(item.get("asset_id")) for item in previous_constituents}
        current_ids = {_string(item.get("asset_id")) for item in selected_members}
        turnover = self._turnover(previous_constituents, selected_members)
        coverage = _float_value(selection.get("coverage_ratio"))
        min_coverage = _float_value(
            definition.get("coverage_floor"),
            _float_value(
                definition.get("min_coverage_warning"), DEFAULT_MIN_COVERAGE_WARNING
            ),
        )
        warnings = []
        if coverage < min_coverage:
            warnings.append(
                {
                    "code": "W_LOW_BETA_STRENGTH_CLOUD_COVERAGE",
                    "message": (
                        "selected beta strength cloud coverage is below "
                        "warning threshold"
                    ),
                    "coverage_ratio": round(coverage, 10),
                    "min_coverage_warning": round(min_coverage, 10),
                }
            )
        payload = {
            "schema_version": CLOUDRIDGE_BETA_INDEX_SCHEMA_VERSION,
            "engine_version": CLOUDRIDGE_BETA_INDEX_ENGINE_VERSION,
            "record_type": "cloudridge_beta_index_rebalance",
            "rebalance_id": rebalance_id,
            "index_id": definition["index_id"],
            "strength_scan_id": scan["strength_scan_id"],
            "constituent_frame_id": constituent_frame["constituent_frame_id"],
            "level_frame_id": level_frame["level_frame_id"],
            "dataset_version": dataset_version,
            "source_mode": source_mode,
            "formation_date": as_of_date,
            "as_of_date": as_of_date,
            "effective_date": effective_date,
            "selected_strength_threshold": round(
                _float_value(selection.get("strength_threshold")), 10
            ),
            "selected_strength_threshold_z": selection.get("strength_threshold_z"),
            "selected_strength_cutoff": selection.get("strength_selected_cutoff"),
            "selected_strength_cutoff_z": selection.get("strength_selected_cutoff_z"),
            "coverage_floor": selection.get("coverage_floor"),
            "dominant_beta_cloud_selection_metric": selection.get("selection_metric"),
            "dominant_beta_cloud_strength_mean": selection.get("strength_mean"),
            "dominant_beta_cloud_strength_mean_z": selection.get("strength_mean_z"),
            "dominant_beta_cloud_strength_sigma_z": selection.get("strength_sigma_z"),
            "dominant_beta_cloud_strength_left_shoulder": selection.get(
                "strength_left_shoulder"
            ),
            "dominant_beta_cloud_strength_left_shoulder_z": selection.get(
                "strength_left_shoulder_z"
            ),
            "dominant_beta_cloud_threshold_adjusted_to_coverage_floor": (
                selection.get("threshold_adjusted_to_coverage_floor")
            ),
            "dominant_beta_cloud_distribution_summary_z": selection.get(
                "distribution_summary_z"
            ),
            "dominant_beta_cloud_distribution_summary_corr": selection.get(
                "distribution_summary_corr"
            ),
            "beta_strength_cloud_coverage_ratio": round(coverage, 10),
            "selected_count": len(selected_members),
            "eligible_asset_count": scan.get("universe_size", 0),
            "pair_count_evaluated": scan.get("pair_count_evaluated", 0),
            "selection_method": definition.get("selection_method"),
            "peak_strategy": definition.get("peak_strategy"),
            "weighting_method": "equal_weight",
            "turnover": round(turnover, 10),
            "added_constituents": sorted(current_ids - previous_ids),
            "dropped_constituents": sorted(previous_ids - current_ids),
            "coverage_curve": selection.get("curve", []),
            "coverage_diagnostics": {
                "beta_strength_cloud_coverage_ratio": round(coverage, 10),
                "warning_count": len(warnings),
                "warnings": warnings,
                "level_coverage_diagnostics": level_frame.get(
                    "coverage_diagnostics", {}
                ),
            },
            "warnings": warnings,
            "forced": force,
            "auto_action_taken": False,
            "factor_lifecycle_mutation": False,
            "generated_by": generated_by,
            "generated_at": utcnow(),
        }
        artifact = materialize_artifact(
            rebalance_id, "cloudridge_beta_index_rebalance", payload
        )
        record: dict[str, object] = {
            **payload,
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "storage_uri": artifact.storage_uri,
        }
        upsert_record(
            "cloudridge_beta_index_rebalances", rebalance_id, record
        )
        _ = event_store.append(
            event_type="cloudridge_beta_index_rebalance.created",
            payload={
                "rebalance_id": rebalance_id,
                "index_id": definition["index_id"],
                "selected_strength_threshold": payload["selected_strength_threshold"],
            },
            run_id=rebalance_id,
        )
        return record


cloudridge_beta_index_service = CloudRidgeBetaIndexService()
