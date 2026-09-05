# pyright: reportAny=false, reportArgumentType=false
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
# pyright: reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportOperatorIssue=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Strictly causal daily group-correlation time-series materialization."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from collections.abc import Callable, Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from types import ModuleType
from typing import Final, cast

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_correlation.contracts_group_timeseries import (
    FIELD_LABELS_ZH,
    GROUP_CORRELATION_MANIFEST_SCHEMA_VERSION,
    GROUP_CORRELATION_SCHEMA_VERSION,
    GroupCorrelationConfig,
    GroupCorrelationSourceIdentity,
    GroupUniverseIdentity,
)
from factor_lab.market_correlation.services.correlation_matrix_engine import (
    compute_correlation_matrix,
    summarize_correlation_matrix,
)

METRIC_IDS: Final[tuple[str, ...]] = (
    "group_corr_level",
    "group_corr_dispersion",
    "group_common_mode_share",
)


def adapt_datahub_qfq_daily_bars(bars: pd.DataFrame) -> pd.DataFrame:
    """Separate historical bar completion from later dataset materialization.

    DataHub's immutable qfq parquet records when the *dataset artifact* became
    available. A completed exchange daily bar itself was observable at its
    trading-day close. This adapter preserves both facts and makes the latter
    the causal observation availability used by the market-state calculator.
    It is valid only for a pinned qfq-canonical daily product.
    """

    required = {
        "symbol",
        "trading_day",
        "close",
        "available_at",
        "dataset_version",
    }
    missing = required - set(bars.columns)
    if missing:
        raise ValidationError(f"DataHub qfq bars missing columns: {sorted(missing)}")
    versions = set(bars["dataset_version"].dropna().astype(str))
    if len(versions) != 1 or "qfq_canonical" not in next(iter(versions), ""):
        raise ValidationError("adapter requires one pinned qfq_canonical dataset version")
    result = bars[["symbol", "trading_day", "close", "available_at", "dataset_version"]].copy()
    result = result.rename(
        columns={
            "trading_day": "date",
            "available_at": "source_materialized_at",
        }
    )
    result["available_date"] = result["date"]
    result["availability_policy"] = "completed_exchange_daily_bar_at_close"
    result["price_view"] = "qfq_canonical"
    return result


def normalize_group_price_panel(
    bars: pd.DataFrame,
    *,
    member_symbols: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Normalize long qfq bars and require explicit PIT availability."""

    required = {"symbol", "date", "close"}
    missing = required - set(bars.columns)
    if missing:
        raise ValidationError(f"bars missing columns: {sorted(missing)}")
    availability_column = (
        "available_at"
        if "available_at" in bars.columns
        else "available_date" if "available_date" in bars.columns else None
    )
    if availability_column is None:
        raise ValidationError("bars require available_at or available_date")
    working = bars[["symbol", "date", "close", availability_column]].copy()
    working.columns = ["symbol", "date", "close", "available_at"]
    working["symbol"] = working["symbol"].astype(str).str.strip()
    working["date"] = pd.to_datetime(working["date"], errors="coerce").dt.normalize()
    working["available_at"] = pd.to_datetime(
        working["available_at"], errors="coerce"
    ).dt.normalize()
    working["close"] = pd.to_numeric(working["close"], errors="coerce")
    working = working.dropna(subset=["symbol", "date", "available_at", "close"])
    working = working[working["close"] > 0]
    if member_symbols is not None:
        members = frozenset(str(symbol).strip() for symbol in member_symbols)
        if not members:
            raise ValidationError("member_symbols must not be empty")
        working = working[working["symbol"].isin(members)]
    working = (
        working.sort_values(["symbol", "date", "available_at"])
        .drop_duplicates(["symbol", "date"], keep="last")
        .reset_index(drop=True)
    )
    if working.empty or working["symbol"].nunique() < 2:
        raise ValidationError("normalized bars require at least two assets")
    return working


def compute_group_correlation_timeseries(
    bars: pd.DataFrame,
    *,
    universe: GroupUniverseIdentity,
    config: GroupCorrelationConfig | None = None,
    member_symbols: Iterable[str] | None = None,
    observation_dates: Iterable[object] | None = None,
    cupy_module: ModuleType | None = None,
    progress_callback: Callable[[int, int, pd.Timestamp], None] | None = None,
) -> pd.DataFrame:
    """Compute long-form physical attributes from completed daily closes."""

    selected_config = config or GroupCorrelationConfig()
    working = normalize_group_price_panel(bars, member_symbols=member_symbols)
    all_dates = pd.DatetimeIndex(sorted(working["date"].unique()))
    if observation_dates is None:
        selected_dates = all_dates
    else:
        requested = pd.DatetimeIndex(pd.to_datetime(list(observation_dates))).normalize()
        selected_dates = all_dates.intersection(requested)
    if selected_dates.empty:
        raise ValidationError("no observation dates overlap the price panel")

    # The pinned DataHub daily adapter exposes completed exchange bars with
    # ``available_at == date``.  In that common path the wide close/return
    # panel is causal and immutable, so construct it once rather than
    # repeatedly filtering and pivoting the full history for every day.  A
    # delayed-observation input keeps the slower reference path below because
    # a bar becoming visible later can change the then-visible return panel.
    completed_bar_fast_path = bool((working["available_at"] <= working["date"]).all())
    close_panel: pd.DataFrame | None = None
    return_panel: pd.DataFrame | None = None
    if completed_bar_fast_path:
        close_panel = working.pivot(
            index="date", columns="symbol", values="close"
        ).sort_index()
        return_panel = close_panel.pct_change(fill_method=None)

    def compute_window(
        returns: pd.DataFrame,
        window: int,
    ) -> tuple[int, dict[str, object]] | None:
        lookback = returns.tail(window)
        min_periods = max(2, int(np.ceil(window * selected_config.min_coverage_ratio)))
        counts = lookback.count(axis=0)
        eligible = sorted(str(symbol) for symbol in counts[counts >= min_periods].index)
        if len(eligible) < 2:
            return None
        matrix = compute_correlation_matrix(
            lookback[eligible],
            min_periods=min_periods,
            backend=cast(object, selected_config.compute_backend),  # type: ignore[arg-type]
            cupy_module=cupy_module,
        )
        summary = summarize_correlation_matrix(
            matrix,
            lookback_returns=lookback[eligible],
            consume_matrix=True,
        )
        return window, summary.to_dict()

    rows: list[dict[str, object]] = []
    completed_observation_count = 0
    total_observation_count = len(selected_dates)
    executor = (
        ThreadPoolExecutor(max_workers=selected_config.parallel_workers)
        if selected_config.parallel_workers > 1
        else None
    )
    try:
        for position, observation_date in enumerate(all_dates):
            if observation_date not in selected_dates:
                continue
            actionable_from = (
                all_dates[position + 1].strftime("%Y-%m-%d")
                if position + 1 < len(all_dates)
                else None
            )
            if return_panel is not None:
                returns = return_panel.iloc[: position + 1]
            else:
                visible = working[
                    (working["date"] <= observation_date)
                    & (working["available_at"] <= observation_date)
                ]
                close = visible.pivot(
                    index="date", columns="symbol", values="close"
                ).sort_index()
                returns = close.pct_change(fill_method=None)
            if executor is None:
                window_results = [
                    compute_window(returns, window) for window in selected_config.windows
                ]
            else:
                window_results = list(
                    executor.map(
                        partial(compute_window, returns),
                        selected_config.windows,
                    )
                )
            for window_result in window_results:
                if window_result is None:
                    continue
                window, summary_payload = window_result
                common = {
                    "schema_version": GROUP_CORRELATION_SCHEMA_VERSION,
                    "universe_id": universe.universe_id,
                    "universe_version": universe.universe_version,
                    "observation_date": observation_date.strftime("%Y-%m-%d"),
                    "observation_time": observation_date.strftime("%Y-%m-%dT15:00:00+08:00"),
                    "available_at": observation_date.strftime("%Y-%m-%dT15:30:00+08:00"),
                    "actionable_from": actionable_from,
                    "lookback_window": window,
                    "estimator_version": selected_config.estimator_version,
                    "pit_grade": universe.pit_grade,
                    "membership_semantics": universe.membership_semantics,
                    "single_stock_authorized": False,
                    "strict_first_release_pit": universe.strict_first_release_pit,
                    "production_authority": False,
                    "factor_lifecycle_mutation": False,
                    **summary_payload,
                }
                for metric_id in METRIC_IDS:
                    rows.append(
                        {
                            **common,
                            "metric_id": metric_id,
                            "raw_value": float(summary_payload[metric_id]),
                        }
                    )
            completed_observation_count += 1
            if progress_callback is not None:
                progress_callback(
                    completed_observation_count,
                    total_observation_count,
                    cast(pd.Timestamp, observation_date),
                )
    finally:
        if executor is not None:
            executor.shutdown(wait=True)
    if not rows:
        raise ValidationError("no group-correlation observations passed coverage")
    result = pd.DataFrame(rows).sort_values(
        ["observation_date", "lookback_window", "metric_id"]
    ).reset_index(drop=True)
    logical_key = [
        "universe_id",
        "universe_version",
        "observation_date",
        "lookback_window",
        "metric_id",
        "estimator_version",
    ]
    if result.duplicated(logical_key).any():
        raise ValidationError("duplicate group-correlation logical keys")
    return result


def build_group_correlation_bundle(
    bars: pd.DataFrame,
    *,
    universe: GroupUniverseIdentity,
    source: GroupCorrelationSourceIdentity,
    output_root: Path | str,
    config: GroupCorrelationConfig | None = None,
    member_symbols: Iterable[str] | None = None,
    code_version: str,
    force_full: bool = False,
    cupy_module: ModuleType | None = None,
    progress_callback: Callable[[int, int, pd.Timestamp], None] | None = None,
) -> dict[str, object]:
    """Build an immutable bundle; use trusted-tail computation when possible."""

    selected_config = config or GroupCorrelationConfig()
    normalized = normalize_group_price_panel(bars, member_symbols=member_symbols)
    root = Path(output_root)
    versions = root / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    current_path = root / "current_manifest.json"
    build_mode = "full"
    parent_bundle_id: str | None = None
    previous = pd.DataFrame()
    observation_dates: Iterable[object] | None = None
    if current_path.exists() and not force_full:
        parent_manifest = _read_json(current_path)
        parent_bundle_id = str(parent_manifest.get("bundle_id", "")) or None
        trusted = _trusted_parent(
            parent_manifest,
            universe=universe,
            source=source,
            config=selected_config,
            code_version=code_version,
            normalized=normalized,
            root=root,
        )
        if trusted is not None:
            previous, last_date = trusted
            tail_dates = pd.DatetimeIndex(sorted(normalized["date"].unique()))
            observation_dates = tail_dates[tail_dates > pd.Timestamp(last_date)]
            if len(cast(object, observation_dates)) == 0:
                return {
                    "bundle_id": parent_bundle_id,
                    "manifest_path": current_path,
                    "build_mode": "reused",
                    "reused_existing": True,
                }
            build_mode = "incremental"
    computed = compute_group_correlation_timeseries(
        normalized,
        universe=universe,
        config=selected_config,
        observation_dates=observation_dates,
        cupy_module=cupy_module,
        progress_callback=progress_callback,
    )
    if not previous.empty:
        first_tail_date = str(computed["observation_date"].min())
        previous_last_date = str(previous["observation_date"].max())
        previous = previous.copy()
        previous.loc[
            (previous["observation_date"] == previous_last_date)
            & previous["actionable_from"].isna(),
            "actionable_from",
        ] = first_tail_date
    attributes = (
        pd.concat([previous, computed], ignore_index=True)
        if not previous.empty
        else computed
    )
    attributes = attributes.sort_values(
        ["observation_date", "lookback_window", "metric_id"]
    ).reset_index(drop=True)
    last_date = str(attributes["observation_date"].max())
    prefix_digest = _panel_digest(normalized[normalized["date"] <= pd.Timestamp(last_date)])
    identity = {
        "schema_version": GROUP_CORRELATION_MANIFEST_SCHEMA_VERSION,
        "universe": universe.to_dict(),
        "source": source.to_dict(),
        "config": selected_config.to_dict(),
        "code_version": code_version,
        "last_observation_date": last_date,
        "source_prefix_digest": prefix_digest,
        "production_authority": False,
        "factor_lifecycle_mutation": False,
    }
    semantic_digest = _frame_digest(attributes)
    bundle_digest = canonical_digest({**identity, "attributes_digest": semantic_digest})
    bundle_id = "group-correlation-" + bundle_digest.removeprefix("sha256:")[:16]
    staging = versions / f".staging-{os.getpid()}-{uuid.uuid4().hex}"
    staging.mkdir(parents=True, exist_ok=False)
    try:
        attributes_path = staging / "group_correlation_attributes.parquet"
        attributes.to_parquet(attributes_path, index=False)
        inventory = {
            "schema_version": "group_correlation_inventory@1.0",
            "bundle_id": bundle_id,
            "attributes_semantic_digest": semantic_digest,
            "artifacts": {
                "group_correlation_attributes": {
                    "filename": attributes_path.name,
                    "sha256": _file_sha256(attributes_path),
                    "row_count": int(len(attributes)),
                }
            },
            "field_labels_zh": FIELD_LABELS_ZH,
        }
        _write_json(staging / "artifact_inventory.json", inventory)
        manifest = {
            **identity,
            "bundle_id": bundle_id,
            "bundle_semantic_digest": bundle_digest,
            "attributes_semantic_digest": semantic_digest,
            "build_mode": build_mode,
            "parent_bundle_id": parent_bundle_id,
            "artifacts": {
                "group_correlation_attributes": (
                    "artifact://group-correlation/versions/"
                    f"{bundle_id}/{attributes_path.name}"
                ),
                "artifact_inventory": (
                    "artifact://group-correlation/versions/"
                    f"{bundle_id}/artifact_inventory.json"
                ),
            },
            "field_labels_zh": FIELD_LABELS_ZH,
        }
        _write_json(staging / "manifest.json", manifest)
        destination = versions / bundle_id
        if destination.exists():
            shutil.rmtree(staging)
        else:
            os.replace(staging, destination)
        _write_json(current_path, manifest)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {
        "bundle_id": bundle_id,
        "manifest_path": current_path,
        "bundle_dir": versions / bundle_id,
        "build_mode": build_mode,
        "reused_existing": False,
    }


def _trusted_parent(
    manifest: Mapping[str, object],
    *,
    universe: GroupUniverseIdentity,
    source: GroupCorrelationSourceIdentity,
    config: GroupCorrelationConfig,
    code_version: str,
    normalized: pd.DataFrame,
    root: Path,
) -> tuple[pd.DataFrame, str] | None:
    if manifest.get("schema_version") != GROUP_CORRELATION_MANIFEST_SCHEMA_VERSION:
        return None
    if manifest.get("universe") != universe.to_dict():
        return None
    manifest_source = manifest.get("source")
    if not isinstance(manifest_source, Mapping):
        return None
    if manifest_source.get("view") != source.view:
        return None
    if manifest_source.get("frequency") != source.frequency:
        return None
    if manifest.get("config") != config.to_dict():
        return None
    if manifest.get("code_version") != code_version:
        return None
    bundle_id = str(manifest.get("bundle_id", ""))
    last_date = str(manifest.get("last_observation_date", ""))
    if not bundle_id or not last_date:
        return None
    parent_file = root / "versions" / bundle_id / "group_correlation_attributes.parquet"
    if not parent_file.exists():
        return None
    prefix = normalized[normalized["date"] <= pd.Timestamp(last_date)]
    if _panel_digest(prefix) != manifest.get("source_prefix_digest"):
        return None
    return pd.read_parquet(parent_file), last_date


def _panel_digest(frame: pd.DataFrame) -> str:
    ordered = frame.sort_values(["symbol", "date", "available_at"]).reset_index(drop=True)
    hashes = pd.util.hash_pandas_object(ordered, index=False).to_numpy(dtype=np.uint64)
    return "sha256:" + hashlib.sha256(hashes.tobytes()).hexdigest()


def _frame_digest(frame: pd.DataFrame) -> str:
    ordered = frame.sort_values(
        ["universe_id", "observation_date", "lookback_window", "metric_id"]
    ).reset_index(drop=True)
    hashes = pd.util.hash_pandas_object(ordered, index=False).to_numpy(dtype=np.uint64)
    return "sha256:" + hashlib.sha256(hashes.tobytes()).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValidationError(f"JSON object required: {path}")
    return {str(key): value for key, value in payload.items()}


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    _ = temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


__all__ = [
    "METRIC_IDS",
    "adapt_datahub_qfq_daily_bars",
    "build_group_correlation_bundle",
    "compute_group_correlation_timeseries",
    "normalize_group_price_panel",
]
