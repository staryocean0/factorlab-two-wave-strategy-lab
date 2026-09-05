# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnusedCallResult=false, reportMissingTypeArgument=false
"""Whole-market correlation diagnostics and equal-weight core index artifacts.

The service deliberately stays outside the Candidate/Effective/Admitted factor
lifecycle.  It creates research/index artifacts only:

- stock_correlation_distribution_report
- correlation_core_index_definition
- correlation_core_index_rebalance
- correlation_core_index_constituent_frame
- correlation_core_index_level_frame
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Final, Literal, cast

from factor_lab.core.errors import NotFoundError, ValidationError
from factor_lab.core.hashing import sha256_hash
from factor_lab.core.runtime_records import (
    artifact_payload,
    get_record,
    materialize_artifact,
    upsert_record,
    utcnow,
)
from factor_lab.core.runtime_state import runtime_state_store
from factor_lab.governance.services.event_store import event_store

MARKET_CORRELATION_SCHEMA_VERSION: Final[str] = "market_correlation_core_index@1.0"
MARKET_CORRELATION_ENGINE_VERSION: Final[str] = "market_corr_core@1.0"
DEFAULT_MIN_PERIODS: Final[int] = 3
DEFAULT_DENSE_UNIVERSE_CAP: Final[int] = 100
DEFAULT_TOP_PAIR_COUNT: Final[int] = 10
DEFAULT_BASE_LEVEL: Final[float] = 1000.0
DEFAULT_STREAMING_SAMPLE_LIMIT: Final[int] = 5_000
DEFAULT_CENTRALITY_EXPORT_LIMIT: Final[int] = 1_000
DEFAULT_SELECTION_DIAGNOSTIC_LIMIT: Final[int] = 1_000
DEFAULT_RANDOM_BASKET_COUNT: Final[int] = 100
DEFAULT_RANDOM_SEED: Final[int] = 0
DEFAULT_SENSITIVITY_MAX_SCENARIOS: Final[int] = 5

CorrelationMode = Literal["exact_dense", "exact_streaming"]


@dataclass(slots=True)
class _AssetReturns:
    asset_id: str
    symbol: str
    returns_by_date: dict[str, float]
    close_by_date: dict[str, float]
    industry: str = ""
    sector: str = ""
    size_bucket: str = ""
    observation_count: int = 0
    excluded_rows: int = 0


@dataclass(slots=True)
class _ReportComputation:
    assets: dict[str, _AssetReturns]
    eligible_asset_ids: list[str]
    correlations: list[float]
    correlation_sum: float
    correlation_sum_squares: float
    correlation_min: float | None
    correlation_max: float | None
    correlation_sample_truncated: bool
    histogram_counts: list[int]
    ratio_counts: dict[str, int]
    top_positive_pairs: list[dict[str, object]]
    top_negative_pairs: list[dict[str, object]]
    centrality_scores: list[dict[str, object]]
    centrality_score_count: int
    centrality_scores_truncated: bool
    pair_count_total: int
    pair_count_evaluated: int
    pair_count_skipped: int
    skipped_pair_diagnostics: list[dict[str, object]]
    row_diagnostics: dict[str, object]
    mode: CorrelationMode


def _string(value: object) -> str:
    return str(value or "").strip()


def _asset_id(row: Mapping[str, object]) -> str:
    value = _string(row.get("asset_id")) or _string(row.get("symbol"))
    if not value:
        raise ValidationError("row missing asset_id/symbol")
    return value


def _date_key(value: object, *, field_name: str = "timestamp") -> str:
    text = _string(value)
    if not text:
        raise ValidationError(f"{field_name} is required")
    raw_date = text.split("T", maxsplit=1)[0]
    try:
        parsed = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be ISO date YYYY-MM-DD") from exc
    if raw_date != parsed.isoformat():
        raise ValidationError(f"{field_name} must be normalized ISO date YYYY-MM-DD")
    return parsed.isoformat()


def _row_date(row: Mapping[str, object]) -> str:
    value = row.get("timestamp") or row.get("date") or row.get("asof_date")
    return _date_key(value, field_name="timestamp/date")


def _instant_key(value: object, *, end_of_day: bool = False) -> datetime:
    text = _string(value)
    if not text:
        return datetime.min
    if "T" not in text and len(text) == 10:
        text = f"{text}T{'23:59:59' if end_of_day else '00:00:00'}"
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError("timestamp/available_at must be ISO-8601") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    if parsed.time() == time.min and end_of_day and "T" not in _string(value):
        parsed = parsed.replace(hour=23, minute=59, second=59)
    return parsed


def _row_available_at(row: Mapping[str, object]) -> str:
    return (
        _string(row.get("available_at"))
        or _string(row.get("timestamp"))
        or _string(row.get("date"))
    )


def _time_after(left: object, right: object) -> bool:
    return _instant_key(left) > _instant_key(right, end_of_day=True)


def _optional_float(value: object) -> float | None:
    if value is None or _string(value) == "":
        return None
    try:
        number = float(str(value))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


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


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _quantile(sorted_values: Sequence[float], probability: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return round(sorted_values[0], 10)
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(sorted_values[lower], 10)
    weight = position - lower
    value = sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
    return round(value, 10)


def _pearson(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = _mean(left)
    right_mean = _mean(right)
    numerator = sum(
        (x - left_mean) * (y - right_mean) for x, y in zip(left, right, strict=True)
    )
    left_var = sum((x - left_mean) ** 2 for x in left)
    right_var = sum((y - right_mean) ** 2 for y in right)
    denominator = math.sqrt(left_var * right_var)
    if denominator <= 0.0:
        return None
    return max(min(numerator / denominator, 1.0), -1.0)


def _load_dataset_rows(dataset_version: str) -> list[dict[str, object]]:
    for artifact in runtime_state_store.load()["artifacts"].values():
        payload = artifact_payload(artifact)
        if str(payload.get("dataset_version", "")) != dataset_version:
            continue
        for key in ("rows", "records"):
            raw_rows = payload.get(key, [])
            if isinstance(raw_rows, list) and raw_rows:
                return [
                    dict(cast(Mapping[str, object], item))
                    for item in raw_rows
                    if isinstance(item, Mapping)
                ]
        snapshot = payload.get("dataset_snapshot")
        if isinstance(snapshot, Mapping):
            for key in ("rows", "records"):
                raw_rows = snapshot.get(key, [])
                if isinstance(raw_rows, list) and raw_rows:
                    return [
                        dict(cast(Mapping[str, object], item))
                        for item in raw_rows
                        if isinstance(item, Mapping)
                    ]
    raise NotFoundError(f"Published dataset artifact not found: {dataset_version}")


def _resolve_rows(
    *, rows: Sequence[Mapping[str, object]] | None, dataset_version: str | None
) -> tuple[list[dict[str, object]], str, str]:
    if rows is not None:
        working_rows = [dict(row) for row in rows]
        if not working_rows:
            raise ValidationError("rows must not be empty")
        return (
            working_rows,
            dataset_version or "inline_market_correlation_rows@adhoc",
            "rows",
        )
    if not dataset_version:
        raise ValidationError("rows or dataset_version is required")
    return _load_dataset_rows(dataset_version), dataset_version, "dataset_version"


def _price_value(row: Mapping[str, object], price_column: str) -> float | None:
    for key in (price_column, "adj_close", "adjusted_close", "close"):
        if key in row:
            return _optional_float(row.get(key))
    return None


def _return_value(row: Mapping[str, object], return_column: str) -> float | None:
    for key in (return_column, "return", "daily_return", "ret"):
        if key in row:
            return _optional_float(row.get(key))
    return None


def _tradable(row: Mapping[str, object]) -> bool:
    if row.get("pit_available") is False:
        return False
    if row.get("is_tradable") is False:
        return False
    if row.get("suspended") is True:
        return False
    if str(row.get("trade_status", "")).lower() in {"halted", "suspended"}:
        return False
    return True


def _asset_metadata(row: Mapping[str, object]) -> dict[str, str]:
    return {
        "symbol": _string(row.get("symbol")) or _string(row.get("asset_id")),
        "industry": _string(row.get("industry")),
        "sector": _string(row.get("sector")),
        "size_bucket": _string(row.get("size_bucket")),
    }


def _size_bucket(row: Mapping[str, object]) -> str:
    explicit = _string(row.get("size_bucket"))
    if explicit:
        return explicit
    market_cap = _optional_float(row.get("market_cap"))
    if market_cap is None:
        return "unknown"
    if market_cap >= 100_000_000_000:
        return "large"
    if market_cap >= 20_000_000_000:
        return "mid"
    return "small"


def _build_asset_returns(
    *,
    rows: Sequence[Mapping[str, object]],
    as_of_date: str | None,
    lookback_window: int | None,
    return_column: str,
    price_column: str,
    enforce_pit: bool,
) -> tuple[dict[str, _AssetReturns], dict[str, object]]:
    rows_by_asset: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    excluded = {
        "after_as_of": 0,
        "available_after_as_of": 0,
        "not_tradable": 0,
        "missing_price_or_return": 0,
        "bad_rows": 0,
    }
    latest_meta: dict[str, dict[str, str]] = {}
    for raw_row in rows:
        row = dict(raw_row)
        try:
            asset_id = _asset_id(row)
            date = _row_date(row)
        except ValidationError:
            excluded["bad_rows"] += 1
            continue
        if as_of_date and date > as_of_date:
            excluded["after_as_of"] += 1
            continue
        if (
            enforce_pit
            and as_of_date
            and _time_after(_row_available_at(row), as_of_date)
        ):
            excluded["available_after_as_of"] += 1
            continue
        if not _tradable(row):
            excluded["not_tradable"] += 1
            continue
        if (
            _return_value(row, return_column) is None
            and _price_value(row, price_column) is None
        ):
            excluded["missing_price_or_return"] += 1
            continue
        rows_by_asset[asset_id][date] = row
        latest_meta[asset_id] = _asset_metadata(row)
        latest_meta[asset_id]["size_bucket"] = _size_bucket(row)

    assets: dict[str, _AssetReturns] = {}
    all_return_dates: set[str] = set()
    for asset_id, by_date in rows_by_asset.items():
        ordered_dates = sorted(by_date)
        closes_by_date: dict[str, float] = {}
        returns_by_date: dict[str, float] = {}
        previous_close: float | None = None
        for date in ordered_dates:
            row = by_date[date]
            close = _price_value(row, price_column)
            if close is not None:
                closes_by_date[date] = close
            explicit_return = _return_value(row, return_column)
            if explicit_return is not None:
                returns_by_date[date] = explicit_return
            elif (
                previous_close is not None
                and close is not None
                and previous_close > 0.0
            ):
                returns_by_date[date] = close / previous_close - 1.0
            if close is not None:
                previous_close = close
        if lookback_window is not None:
            keep_dates = sorted(returns_by_date)[-lookback_window:]
            returns_by_date = {date: returns_by_date[date] for date in keep_dates}
        all_return_dates.update(returns_by_date)
        meta = latest_meta.get(asset_id, {})
        assets[asset_id] = _AssetReturns(
            asset_id=asset_id,
            symbol=meta.get("symbol", asset_id),
            returns_by_date=returns_by_date,
            close_by_date=closes_by_date,
            industry=meta.get("industry", ""),
            sector=meta.get("sector", ""),
            size_bucket=meta.get("size_bucket", "unknown") or "unknown",
            observation_count=len(returns_by_date),
        )
    diagnostics: dict[str, object] = {
        "input_row_count": len(rows),
        "asset_count_raw": len(rows_by_asset),
        "asset_count_with_returns": len(assets),
        "return_date_count": len(all_return_dates),
        "excluded_rows": excluded,
        "pit_cutoff_date": as_of_date or "",
        "lookback_window": lookback_window or 0,
    }
    return assets, diagnostics


def _aligned_returns(
    left: _AssetReturns, right: _AssetReturns
) -> tuple[list[float], list[float], int]:
    dates = sorted(set(left.returns_by_date) & set(right.returns_by_date))
    return (
        [left.returns_by_date[date] for date in dates],
        [right.returns_by_date[date] for date in dates],
        len(dates),
    )


def _histogram_index(value: float, bucket_count: int) -> int:
    width = 2.0 / bucket_count
    return min(bucket_count - 1, max(0, int((value + 1.0) / width)))


def _histogram_from_counts(counts: Sequence[int]) -> list[dict[str, object]]:
    if not counts:
        raise ValidationError("histogram_bucket_count must be positive")
    bucket_count = len(counts)
    width = 2.0 / bucket_count
    total = sum(counts)
    rows: list[dict[str, object]] = []
    for index, count in enumerate(counts):
        start = -1.0 + index * width
        end = start + width
        rows.append(
            {
                "bin_start": round(start, 6),
                "bin_end": round(end, 6),
                "count": count,
                "ratio": round(count / total, 10) if total else 0.0,
            }
        )
    return rows


def _summary_from_stats(
    *,
    values_sample: Sequence[float],
    count: int,
    total: float,
    total_squares: float,
    minimum: float | None,
    maximum: float | None,
    sample_truncated: bool,
) -> dict[str, object]:
    ordered = sorted(values_sample)
    mean = total / count if count else 0.0
    variance = max(total_squares / count - mean**2, 0.0) if count else 0.0
    return {
        "count": count,
        "sample_count": len(ordered),
        "sample_truncated": sample_truncated,
        "quantile_method": "bounded_sample" if sample_truncated else "exact",
        "mean": round(mean, 10),
        "std": round(math.sqrt(variance), 10),
        "median": _quantile(ordered, 0.5) if ordered else None,
        "min": round(minimum, 10) if minimum is not None else None,
        "max": round(maximum, 10) if maximum is not None else None,
        "quantiles": {
            "q01": _quantile(ordered, 0.01),
            "q05": _quantile(ordered, 0.05),
            "q25": _quantile(ordered, 0.25),
            "q50": _quantile(ordered, 0.50),
            "q75": _quantile(ordered, 0.75),
            "q95": _quantile(ordered, 0.95),
            "q99": _quantile(ordered, 0.99),
        },
    }


def _ratio_counts(value: float) -> dict[str, int]:
    return {
        "near_zero_ratio": int(abs(value) < 0.10),
        "weak_ratio": int(abs(value) < 0.20),
        "moderate_positive_ratio": int(value >= 0.30),
        "strong_positive_ratio": int(value >= 0.50),
        "very_strong_positive_ratio": int(value >= 0.70),
        "negative_ratio": int(value < 0.0),
        "strong_negative_ratio": int(value <= -0.30),
    }


def _ratio_summary_from_counts(
    counts: Mapping[str, int], *, total: int
) -> dict[str, object]:
    return {
        key: round(value / total, 10) if total else 0.0 for key, value in counts.items()
    }


def _safe_float(value: object, default: float = 0.0) -> float:
    parsed = _optional_float(value)
    return parsed if parsed is not None else default


def _latest_market_caps(
    rows: Sequence[Mapping[str, object]], *, effective_date: str
) -> dict[str, float]:
    candidates: dict[str, tuple[str, float]] = {}
    for raw_row in rows:
        try:
            asset_id = _asset_id(raw_row)
            row_date = _row_date(raw_row)
        except ValidationError:
            continue
        if row_date > effective_date or not _tradable(raw_row):
            continue
        market_cap = _optional_float(raw_row.get("market_cap"))
        if market_cap is None or market_cap <= 0.0:
            continue
        current = candidates.get(asset_id)
        if current is None or row_date >= current[0]:
            candidates[asset_id] = (row_date, market_cap)
    return {asset_id: value for asset_id, (_row_date, value) in candidates.items()}


def _clean_sensitivity_values(
    values: Sequence[int] | None,
    *,
    default_values: Sequence[int],
    minimum: int,
    field_name: str,
) -> list[int]:
    raw_values = list(default_values if not values else values)
    cleaned: list[int] = []
    for value in raw_values:
        if value < minimum:
            raise ValidationError(f"{field_name} values must be >= {minimum}")
        if value not in cleaned:
            cleaned.append(value)
    return cleaned[:DEFAULT_SENSITIVITY_MAX_SCENARIOS]


def _interpretation(
    summary: Mapping[str, object], ratios: Mapping[str, object]
) -> dict[str, object]:
    median_value = _optional_float(summary.get("median")) or 0.0
    near_zero = _optional_float(ratios.get("near_zero_ratio")) or 0.0
    strong_positive = _optional_float(ratios.get("strong_positive_ratio")) or 0.0
    fragmented = median_value < 0.10 and near_zero >= 0.50
    synchronized = median_value >= 0.30 or strong_positive >= 0.30
    if fragmented:
        regime = "fragmented_market"
        message = (
            "Market correlations are weak/fragmented; "
            "backbone-index meaning is reduced."
        )
    elif synchronized:
        regime = "synchronized_market"
        message = (
            "Market correlations show a broad common movement; "
            "backbone index is meaningful."
        )
    else:
        regime = "mixed_market"
        message = (
            "Market correlations are mixed; interpret the core index with diagnostics."
        )
    return {
        "regime": regime,
        "fragmented_market_warning": fragmented,
        "synchronized_market_signal": synchronized,
        "message": message,
    }


def _cap_top_pairs(
    rows: list[dict[str, object]], limit: int, *, positive: bool
) -> list[dict[str, object]]:
    ordered = sorted(
        rows,
        key=lambda item: (
            -float(str(item["correlation"]))
            if positive
            else float(str(item["correlation"])),
            str(item["asset_id_left"]),
            str(item["asset_id_right"]),
        ),
    )
    return ordered[:limit]


def _list_records(collection: str) -> list[dict[str, object]]:
    raw = runtime_state_store.load().get(collection, {})
    if not isinstance(raw, Mapping):
        return []
    return [dict(cast(Mapping[str, object], value)) for value in raw.values()]


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


class MarketCorrelationCoreService:
    """Build market correlation reports and correlation-core index artifacts."""

    def create_report(
        self,
        *,
        rows: Sequence[Mapping[str, object]] | None = None,
        dataset_version: str | None = None,
        universe_ref: str,
        as_of_date: str,
        lookback_window: int,
        min_periods: int = DEFAULT_MIN_PERIODS,
        return_column: str = "return",
        price_column: str = "close",
        dense_universe_cap: int = DEFAULT_DENSE_UNIVERSE_CAP,
        top_pair_count: int = DEFAULT_TOP_PAIR_COUNT,
        histogram_bucket_count: int = 20,
        streaming_sample_limit: int = DEFAULT_STREAMING_SAMPLE_LIMIT,
        centrality_export_limit: int = DEFAULT_CENTRALITY_EXPORT_LIMIT,
        generated_by: str = "local_read",
    ) -> dict[str, object]:
        as_of_date = _date_key(as_of_date, field_name="as_of_date")
        if not universe_ref.strip():
            raise ValidationError("universe_ref is required")
        if lookback_window < 2:
            raise ValidationError("lookback_window must be >= 2")
        if min_periods < 2:
            raise ValidationError("min_periods must be >= 2")
        if dense_universe_cap < 1:
            raise ValidationError("dense_universe_cap must be positive")
        if histogram_bucket_count < 1:
            raise ValidationError("histogram_bucket_count must be positive")
        if streaming_sample_limit < 1:
            raise ValidationError("streaming_sample_limit must be positive")
        if centrality_export_limit < 1:
            raise ValidationError("centrality_export_limit must be positive")
        working_rows, resolved_dataset_version, source_mode = _resolve_rows(
            rows=rows,
            dataset_version=dataset_version,
        )
        computation = self._compute_report(
            rows=working_rows,
            as_of_date=as_of_date,
            lookback_window=lookback_window,
            min_periods=min_periods,
            return_column=return_column,
            price_column=price_column,
            dense_universe_cap=dense_universe_cap,
            top_pair_count=top_pair_count,
            histogram_bucket_count=histogram_bucket_count,
            streaming_sample_limit=streaming_sample_limit,
            centrality_export_limit=centrality_export_limit,
        )
        if computation.pair_count_evaluated == 0:
            raise ValidationError("correlation report produced no evaluated pairs")
        summary = _summary_from_stats(
            values_sample=computation.correlations,
            count=computation.pair_count_evaluated,
            total=computation.correlation_sum,
            total_squares=computation.correlation_sum_squares,
            minimum=computation.correlation_min,
            maximum=computation.correlation_max,
            sample_truncated=computation.correlation_sample_truncated,
        )
        ratios = _ratio_summary_from_counts(
            computation.ratio_counts,
            total=computation.pair_count_evaluated,
        )
        histogram = _histogram_from_counts(computation.histogram_counts)
        report_id = (
            "mcorrrep_"
            + sha256_hash(
                {
                    "universe_ref": universe_ref,
                    "dataset_version": resolved_dataset_version,
                    "as_of_date": as_of_date,
                    "lookback_window": lookback_window,
                    "min_periods": min_periods,
                    "centrality_scores": computation.centrality_scores,
                    "pair_count_evaluated": computation.pair_count_evaluated,
                }
            )[:20]
        )
        payload = {
            "schema_version": MARKET_CORRELATION_SCHEMA_VERSION,
            "engine_version": MARKET_CORRELATION_ENGINE_VERSION,
            "record_type": "stock_correlation_distribution_report",
            "report_id": report_id,
            "universe_ref": universe_ref,
            "dataset_version": resolved_dataset_version,
            "source_mode": source_mode,
            "as_of_date": as_of_date,
            "lookback_window": lookback_window,
            "min_periods": min_periods,
            "return_column": return_column,
            "price_column": price_column,
            "correlation_method": "pearson",
            "neutralization_mode": "raw",
            "mode": computation.mode,
            "universe_size": len(computation.eligible_asset_ids),
            "pair_count_total": computation.pair_count_total,
            "pair_count_evaluated": computation.pair_count_evaluated,
            "pair_count_skipped": computation.pair_count_skipped,
            "correlation_summary": summary,
            "correlation_histogram": histogram,
            "ratio_summary": ratios,
            "top_positive_pairs": computation.top_positive_pairs,
            "top_negative_pairs": computation.top_negative_pairs,
            "centrality_scores": computation.centrality_scores,
            "centrality_score_count": computation.centrality_score_count,
            "centrality_scores_truncated": computation.centrality_scores_truncated,
            "centrality_export_limit": centrality_export_limit,
            "data_quality": {
                **computation.row_diagnostics,
                "correlation_sample_size": len(computation.correlations),
                "correlation_sample_truncated": (
                    computation.correlation_sample_truncated
                ),
                "skipped_pair_diagnostics": computation.skipped_pair_diagnostics[:100],
            },
            "interpretation": _interpretation(summary, ratios),
            "auto_action_taken": False,
            "factor_lifecycle_mutation": False,
            "generated_by": generated_by,
            "generated_at": utcnow(),
        }
        artifact = materialize_artifact(
            report_id, "stock_correlation_distribution_report", payload
        )
        record: dict[str, object] = {
            **payload,
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "storage_uri": artifact.storage_uri,
        }
        upsert_record("stock_correlation_distribution_reports", report_id, record)
        _ = event_store.append(
            event_type="stock_correlation_distribution_report.created",
            payload={
                "report_id": report_id,
                "universe_size": len(computation.eligible_asset_ids),
            },
            run_id=report_id,
        )
        return record

    def list_reports(
        self, *, universe_ref: str | None = None, as_of_date: str | None = None
    ) -> list[dict[str, object]]:
        if as_of_date:
            as_of_date = _date_key(as_of_date, field_name="as_of_date")
        reports = _list_records("stock_correlation_distribution_reports")
        filtered = []
        for report in reports:
            if universe_ref and str(report.get("universe_ref")) != universe_ref:
                continue
            if as_of_date and str(report.get("as_of_date")) != as_of_date:
                continue
            filtered.append(report)
        return sorted(
            filtered, key=lambda item: str(item.get("generated_at", "")), reverse=True
        )

    def get_report(self, report_id: str) -> dict[str, object]:
        record = get_record("stock_correlation_distribution_reports", report_id)
        if record is None:
            raise NotFoundError(f"market correlation report not found: {report_id}")
        return dict(record)

    def create_index_definition(
        self,
        *,
        name: str,
        universe_ref: str,
        lookback_window: int,
        selection_count: int,
        weighting_method: str = "equal_weight",
        min_periods: int = DEFAULT_MIN_PERIODS,
        return_column: str = "return",
        price_column: str = "close",
        description: str = "",
        created_by: str = "local_write",
    ) -> dict[str, object]:
        if not name.strip():
            raise ValidationError("name is required")
        if not universe_ref.strip():
            raise ValidationError("universe_ref is required")
        if lookback_window < 2:
            raise ValidationError("lookback_window must be >= 2")
        if selection_count < 1:
            raise ValidationError("selection_count must be >= 1")
        if min_periods < 2:
            raise ValidationError("min_periods must be >= 2")
        if weighting_method != "equal_weight":
            raise ValidationError(
                "only equal_weight correlation core indexes are supported"
            )
        index_id = (
            "corridx_"
            + sha256_hash(
                {
                    "name": name,
                    "universe_ref": universe_ref,
                    "lookback_window": lookback_window,
                    "selection_count": selection_count,
                    "weighting_method": weighting_method,
                    "min_periods": min_periods,
                }
            )[:20]
        )
        payload = {
            "schema_version": MARKET_CORRELATION_SCHEMA_VERSION,
            "record_type": "correlation_core_index_definition",
            "index_id": index_id,
            "name": name,
            "description": description,
            "universe_ref": universe_ref,
            "lookback_window": lookback_window,
            "selection_count": selection_count,
            "weighting_method": weighting_method,
            "selection_method": "mean_positive_raw_return_correlation_topk",
            "score_formula": "mean(max(corr(i,j), 0))",
            "rebalance_rule": "daily_pure_topk_no_buffer",
            "min_periods": min_periods,
            "return_column": return_column,
            "price_column": price_column,
            "base_level": DEFAULT_BASE_LEVEL,
            "asset_kind": "correlation_core_index",
            "auto_action_taken": False,
            "factor_lifecycle_mutation": False,
            "created_by": created_by,
            "created_at": utcnow(),
        }
        artifact = materialize_artifact(
            index_id, "correlation_core_index_definition", payload
        )
        record: dict[str, object] = {
            **payload,
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "storage_uri": artifact.storage_uri,
        }
        upsert_record("correlation_core_index_definitions", index_id, record)
        _ = event_store.append(
            event_type="correlation_core_index_definition.created",
            payload={"index_id": index_id, "selection_count": selection_count},
            run_id=index_id,
        )
        return record

    def list_index_definitions(self) -> list[dict[str, object]]:
        return sorted(
            _list_records("correlation_core_index_definitions"),
            key=lambda item: str(item.get("created_at", "")),
            reverse=True,
        )

    def get_index_definition(self, index_id: str) -> dict[str, object]:
        record = get_record("correlation_core_index_definitions", index_id)
        if record is None:
            raise NotFoundError(f"correlation core index not found: {index_id}")
        return dict(record)

    def rebalance_index(
        self,
        *,
        index_id: str,
        rows: Sequence[Mapping[str, object]] | None = None,
        dataset_version: str | None = None,
        as_of_date: str,
        effective_date: str,
        report_id: str | None = None,
        random_basket_count: int = DEFAULT_RANDOM_BASKET_COUNT,
        random_seed: int = DEFAULT_RANDOM_SEED,
        lookback_sensitivity_windows: Sequence[int] | None = None,
        selection_count_sensitivity_values: Sequence[int] | None = None,
        generated_by: str = "local_write",
    ) -> dict[str, object]:
        definition = self.get_index_definition(index_id)
        if not as_of_date:
            raise ValidationError("as_of_date is required")
        if not effective_date:
            raise ValidationError("effective_date is required")
        as_of_date = _date_key(as_of_date, field_name="as_of_date")
        effective_date = _date_key(effective_date, field_name="effective_date")
        if effective_date <= as_of_date:
            raise ValidationError("effective_date must be after formation/as_of_date")
        if random_basket_count < 0 or random_basket_count > 1_000:
            raise ValidationError("random_basket_count must be between 0 and 1000")
        working_rows, resolved_dataset_version, _source_mode = _resolve_rows(
            rows=rows,
            dataset_version=dataset_version,
        )
        if report_id:
            report = self.get_report(report_id)
            if str(report.get("universe_ref")) != str(definition["universe_ref"]):
                raise ValidationError(
                    "report universe_ref does not match index definition"
                )
            if _int_value(report.get("lookback_window")) != _int_value(
                definition.get("lookback_window")
            ):
                raise ValidationError(
                    "report lookback_window does not match index definition"
                )
            if str(report.get("as_of_date", "")) != as_of_date:
                raise ValidationError(
                    "report as_of_date does not match rebalance as_of_date"
                )
            if _int_value(report.get("min_periods")) != _int_value(
                definition.get("min_periods")
            ):
                raise ValidationError(
                    "report min_periods does not match index definition"
                )
            if str(report.get("return_column", "")) != str(definition["return_column"]):
                raise ValidationError(
                    "report return_column does not match index definition"
                )
            if str(report.get("price_column", "")) != str(definition["price_column"]):
                raise ValidationError(
                    "report price_column does not match index definition"
                )
        else:
            report = self.create_report(
                rows=working_rows,
                dataset_version=resolved_dataset_version,
                universe_ref=str(definition["universe_ref"]),
                as_of_date=as_of_date,
                lookback_window=_int_value(definition.get("lookback_window")),
                min_periods=_int_value(definition.get("min_periods")),
                return_column=str(definition["return_column"]),
                price_column=str(definition["price_column"]),
                centrality_export_limit=max(
                    DEFAULT_CENTRALITY_EXPORT_LIMIT,
                    _int_value(definition.get("selection_count")),
                ),
                generated_by=generated_by,
            )
        selected, selection_rows = self._select_topk(
            report,
            selection_count=_int_value(definition.get("selection_count")),
        )
        previous_constituents = self._previous_constituents(
            index_id, before_date=effective_date
        )
        rebalance_id = (
            "corrrebal_"
            + sha256_hash(
                {
                    "index_id": definition["index_id"],
                    "report_id": report["report_id"],
                    "effective_date": effective_date,
                }
            )[:20]
        )
        constituent_frame = self._materialize_constituent_frame(
            definition=definition,
            report=report,
            rebalance_id=rebalance_id,
            selected=selected,
            selection_rows=selection_rows,
            as_of_date=as_of_date,
            effective_date=effective_date,
            generated_by=generated_by,
        )
        level_frame = self._materialize_level_frame(
            definition=definition,
            report=report,
            rebalance_id=rebalance_id,
            constituent_frame=constituent_frame,
            selected=selected,
            rows=working_rows,
            dataset_version=resolved_dataset_version,
            effective_date=effective_date,
            previous_constituents=previous_constituents,
            generated_by=generated_by,
        )
        rebalance = self._materialize_rebalance(
            definition=definition,
            report=report,
            rebalance_id=rebalance_id,
            constituent_frame=constituent_frame,
            level_frame=level_frame,
            selected=selected,
            previous_constituents=previous_constituents,
            rows=working_rows,
            as_of_date=as_of_date,
            effective_date=effective_date,
            random_basket_count=random_basket_count,
            random_seed=random_seed,
            lookback_sensitivity_windows=lookback_sensitivity_windows,
            selection_count_sensitivity_values=selection_count_sensitivity_values,
            generated_by=generated_by,
        )
        return {
            "index": definition,
            "report": report,
            "rebalance": rebalance,
            "constituent_frame": constituent_frame,
            "level_frame": level_frame,
            "research_diagnostics": rebalance.get("research_diagnostics", {}),
        }

    def list_rebalances(self, index_id: str) -> list[dict[str, object]]:
        return sorted(
            [
                record
                for record in _list_records("correlation_core_index_rebalances")
                if str(record.get("index_id")) == index_id
            ],
            key=lambda item: str(item.get("effective_date", "")),
            reverse=True,
        )

    def list_level_frames(self, index_id: str) -> list[dict[str, object]]:
        return sorted(
            [
                record
                for record in _list_records("correlation_core_index_level_frames")
                if str(record.get("index_id")) == index_id
            ],
            key=lambda item: str(item.get("end_date", "")),
        )

    def list_constituent_frames(self, index_id: str) -> list[dict[str, object]]:
        return sorted(
            [
                record
                for record in _list_records("correlation_core_index_constituent_frames")
                if str(record.get("index_id")) == index_id
            ],
            key=lambda item: str(item.get("effective_date", "")),
        )

    def level_rows(self, index_id: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for frame in self.list_level_frames(index_id):
            payload_rows = frame.get("rows", [])
            if isinstance(payload_rows, Sequence) and not isinstance(payload_rows, str):
                rows.extend(
                    dict(cast(Mapping[str, object], row))
                    for row in payload_rows
                    if isinstance(row, Mapping)
                )
        return sorted(rows, key=lambda row: str(row.get("date", "")))

    def constituent_rows(self, index_id: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for frame in self.list_constituent_frames(index_id):
            payload_rows = frame.get("rows", [])
            if isinstance(payload_rows, Sequence) and not isinstance(payload_rows, str):
                rows.extend(
                    dict(cast(Mapping[str, object], row))
                    for row in payload_rows
                    if isinstance(row, Mapping)
                )
        return sorted(
            rows,
            key=lambda row: (
                str(row.get("effective_date", "")),
                _int_value(row.get("rank")),
            ),
        )

    def _compute_report(
        self,
        *,
        rows: Sequence[Mapping[str, object]],
        as_of_date: str,
        lookback_window: int,
        min_periods: int,
        return_column: str,
        price_column: str,
        dense_universe_cap: int,
        top_pair_count: int,
        histogram_bucket_count: int,
        streaming_sample_limit: int,
        centrality_export_limit: int,
    ) -> _ReportComputation:
        assets, row_diagnostics = _build_asset_returns(
            rows=rows,
            as_of_date=as_of_date,
            lookback_window=lookback_window,
            return_column=return_column,
            price_column=price_column,
            enforce_pit=True,
        )
        eligible = sorted(
            [
                asset_id
                for asset_id, asset in assets.items()
                if asset.observation_count >= min_periods
            ]
        )
        if len(eligible) < 2:
            raise ValidationError(
                "correlation report requires at least two eligible assets"
            )
        mode: CorrelationMode = (
            "exact_dense" if len(eligible) <= dense_universe_cap else "exact_streaming"
        )
        pair_count_total = len(eligible) * (len(eligible) - 1) // 2
        correlations: list[float] = []
        positive_pairs: list[dict[str, object]] = []
        negative_pairs: list[dict[str, object]] = []
        skipped: list[dict[str, object]] = []
        score_sum: dict[str, float] = {asset_id: 0.0 for asset_id in eligible}
        score_count: dict[str, int] = {asset_id: 0 for asset_id in eligible}
        abs_sum: dict[str, float] = {asset_id: 0.0 for asset_id in eligible}
        pair_count_evaluated = 0
        pair_count_skipped = 0
        correlation_sum = 0.0
        correlation_sum_squares = 0.0
        correlation_min: float | None = None
        correlation_max: float | None = None
        correlation_sample_truncated = False
        histogram_counts = [0 for _ in range(histogram_bucket_count)]
        ratio_counts = {key: 0 for key in _ratio_counts(0.0)}
        for left_index, left_id in enumerate(eligible):
            left = assets[left_id]
            for right_id in eligible[left_index + 1 :]:
                right = assets[right_id]
                left_values, right_values, overlap = _aligned_returns(left, right)
                if overlap < min_periods:
                    pair_count_skipped += 1
                    if len(skipped) < 100:
                        skipped.append(
                            {
                                "asset_id_left": left_id,
                                "asset_id_right": right_id,
                                "reason_code": "E_INSUFFICIENT_OVERLAP",
                                "overlap": overlap,
                                "min_periods": min_periods,
                            }
                        )
                    continue
                corr = _pearson(left_values, right_values)
                if corr is None:
                    pair_count_skipped += 1
                    if len(skipped) < 100:
                        skipped.append(
                            {
                                "asset_id_left": left_id,
                                "asset_id_right": right_id,
                                "reason_code": "E_ZERO_VARIANCE_OR_INVALID_CORRELATION",
                                "overlap": overlap,
                                "min_periods": min_periods,
                            }
                        )
                    continue
                pair_count_evaluated += 1
                if mode == "exact_dense" or len(correlations) < streaming_sample_limit:
                    correlations.append(corr)
                else:
                    correlation_sample_truncated = True
                correlation_sum += corr
                correlation_sum_squares += corr * corr
                correlation_min = (
                    corr if correlation_min is None else min(correlation_min, corr)
                )
                correlation_max = (
                    corr if correlation_max is None else max(correlation_max, corr)
                )
                histogram_counts[_histogram_index(corr, histogram_bucket_count)] += 1
                for key, count in _ratio_counts(corr).items():
                    ratio_counts[key] += count
                positive_component = max(corr, 0.0)
                score_sum[left_id] += positive_component
                score_sum[right_id] += positive_component
                abs_sum[left_id] += abs(corr)
                abs_sum[right_id] += abs(corr)
                score_count[left_id] += 1
                score_count[right_id] += 1
                pair_row: dict[str, object] = {
                    "asset_id_left": left_id,
                    "asset_id_right": right_id,
                    "symbol_left": left.symbol,
                    "symbol_right": right.symbol,
                    "correlation": round(corr, 10),
                    "overlap": overlap,
                }
                if corr >= 0.0:
                    positive_pairs.append(pair_row)
                    positive_pairs = _cap_top_pairs(
                        positive_pairs, top_pair_count, positive=True
                    )
                else:
                    negative_pairs.append(pair_row)
                    negative_pairs = _cap_top_pairs(
                        negative_pairs, top_pair_count, positive=False
                    )
        centrality: list[dict[str, object]] = []
        for asset_id in eligible:
            asset = assets[asset_id]
            evaluated = score_count[asset_id]
            centrality.append(
                {
                    "asset_id": asset_id,
                    "symbol": asset.symbol,
                    "score": round(score_sum[asset_id] / evaluated, 10)
                    if evaluated
                    else 0.0,
                    "positive_pair_count": evaluated,
                    "evaluated_pair_count": evaluated,
                    "mean_abs_correlation": round(abs_sum[asset_id] / evaluated, 10)
                    if evaluated
                    else 0.0,
                    "observation_count": asset.observation_count,
                    "industry": asset.industry,
                    "sector": asset.sector,
                    "size_bucket": asset.size_bucket,
                }
            )
        centrality.sort(
            key=lambda item: (-float(str(item["score"])), str(item["asset_id"]))
        )
        centrality_score_count = len(centrality)
        centrality_scores_truncated = centrality_score_count > centrality_export_limit
        centrality = centrality[:centrality_export_limit]
        row_diagnostics = {
            **row_diagnostics,
            "eligible_asset_count": len(eligible),
            "ineligible_assets": [
                {
                    "asset_id": asset_id,
                    "reason_code": "E_INSUFFICIENT_OBSERVATIONS",
                    "observation_count": asset.observation_count,
                    "min_periods": min_periods,
                }
                for asset_id, asset in sorted(assets.items())
                if asset_id not in eligible
            ],
        }
        return _ReportComputation(
            assets=assets,
            eligible_asset_ids=eligible,
            correlations=correlations,
            correlation_sum=correlation_sum,
            correlation_sum_squares=correlation_sum_squares,
            correlation_min=correlation_min,
            correlation_max=correlation_max,
            correlation_sample_truncated=correlation_sample_truncated,
            histogram_counts=histogram_counts,
            ratio_counts=ratio_counts,
            top_positive_pairs=_cap_top_pairs(
                positive_pairs, top_pair_count, positive=True
            ),
            top_negative_pairs=_cap_top_pairs(
                negative_pairs, top_pair_count, positive=False
            ),
            centrality_scores=centrality,
            centrality_score_count=centrality_score_count,
            centrality_scores_truncated=centrality_scores_truncated,
            pair_count_total=pair_count_total,
            pair_count_evaluated=pair_count_evaluated,
            pair_count_skipped=pair_count_skipped,
            skipped_pair_diagnostics=skipped,
            row_diagnostics=row_diagnostics,
            mode=mode,
        )

    def _select_topk(
        self, report: Mapping[str, object], *, selection_count: int
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        raw_scores = report.get("centrality_scores", [])
        if not isinstance(raw_scores, Sequence) or isinstance(raw_scores, str):
            raise ValidationError("report missing centrality_scores")
        candidates = [
            dict(cast(Mapping[str, object], item))
            for item in raw_scores
            if isinstance(item, Mapping)
        ]
        if len(candidates) < selection_count:
            if bool(report.get("centrality_scores_truncated", False)):
                raise ValidationError(
                    "selection_count exceeds persisted centrality export limit"
                )
            raise ValidationError("insufficient eligible assets for selection_count")
        ranked = sorted(
            candidates,
            key=lambda item: (
                -float(str(item.get("score", 0.0))),
                str(item.get("asset_id", "")),
            ),
        )
        selected_ids = {str(item.get("asset_id")) for item in ranked[:selection_count]}
        selection_rows: list[dict[str, object]] = []
        selected: list[dict[str, object]] = []
        for rank, item in enumerate(ranked, start=1):
            asset_id = str(item.get("asset_id"))
            is_selected = asset_id in selected_ids
            row = {
                **item,
                "rank": rank,
                "selected": is_selected,
                "reason_code": "selected_topk" if is_selected else "below_topk",
            }
            if is_selected or len(selection_rows) < DEFAULT_SELECTION_DIAGNOSTIC_LIMIT:
                selection_rows.append(row)
            if is_selected:
                selected.append(row)
        return selected, selection_rows

    def _previous_constituents(
        self, index_id: str, *, before_date: str
    ) -> list[dict[str, object]]:
        frames = self.list_constituent_frames(index_id)
        previous = _latest_by_date(
            frames, date_key="effective_date", before_date=before_date
        )
        rows = previous.get("rows", [])
        if not isinstance(rows, Sequence) or isinstance(rows, str):
            return []
        return [
            dict(cast(Mapping[str, object], row))
            for row in rows
            if isinstance(row, Mapping)
        ]

    def _materialize_constituent_frame(
        self,
        *,
        definition: Mapping[str, object],
        report: Mapping[str, object],
        rebalance_id: str,
        selected: Sequence[Mapping[str, object]],
        selection_rows: Sequence[Mapping[str, object]],
        as_of_date: str,
        effective_date: str,
        generated_by: str,
    ) -> dict[str, object]:
        selected_count = len(selected)
        target_weight = 1.0 / selected_count if selected_count else 0.0
        rows: list[dict[str, object]] = [
            {
                "index_id": definition["index_id"],
                "report_id": report["report_id"],
                "formation_date": as_of_date,
                "effective_date": effective_date,
                "asset_id": str(item.get("asset_id")),
                "symbol": str(item.get("symbol") or item.get("asset_id")),
                "rank": _int_value(item.get("rank")),
                "score": float(str(item.get("score", 0.0))),
                "target_weight": round(target_weight, 12),
                "weighting_method": "equal_weight",
                "reason_code": str(item.get("reason_code", "selected_topk")),
                "industry": str(item.get("industry", "")),
                "sector": str(item.get("sector", "")),
                "size_bucket": str(item.get("size_bucket", "unknown")),
            }
            for item in selected
        ]
        frame_id = (
            "corrconst_"
            + sha256_hash(
                {
                    "index_id": definition["index_id"],
                    "report_id": report["report_id"],
                    "rows": rows,
                }
            )[:20]
        )
        payload = {
            "schema_version": MARKET_CORRELATION_SCHEMA_VERSION,
            "record_type": "correlation_core_index_constituent_frame",
            "constituent_frame_id": frame_id,
            "index_id": definition["index_id"],
            "report_id": report["report_id"],
            "rebalance_id": rebalance_id,
            "formation_date": as_of_date,
            "effective_date": effective_date,
            "weighting_method": "equal_weight",
            "selected_count": selected_count,
            "rows": rows,
            "selection_diagnostics": {
                "selection_count_requested": definition["selection_count"],
                "candidate_count": report.get("centrality_score_count", 0),
                "selection_rows_exported": len(selection_rows),
                "selection_rows_truncated": (
                    len(selection_rows)
                    < _int_value(report.get("centrality_score_count"))
                ),
                "selection_rows": [dict(row) for row in selection_rows],
            },
            "auto_action_taken": False,
            "factor_lifecycle_mutation": False,
            "generated_by": generated_by,
            "generated_at": utcnow(),
        }
        artifact = materialize_artifact(
            frame_id, "correlation_core_index_constituent_frame", payload
        )
        record: dict[str, object] = {
            **payload,
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "storage_uri": artifact.storage_uri,
        }
        upsert_record("correlation_core_index_constituent_frames", frame_id, record)
        return record

    def _return_for_effective_date(
        self, *, asset: _AssetReturns | None, effective_date: str
    ) -> float | None:
        if asset is None:
            return None
        if effective_date in asset.returns_by_date:
            return asset.returns_by_date[effective_date]
        close = asset.close_by_date.get(effective_date)
        previous_dates = [date for date in asset.close_by_date if date < effective_date]
        if close is None or not previous_dates:
            return None
        previous = asset.close_by_date[max(previous_dates)]
        if previous <= 0.0:
            return None
        return close / previous - 1.0

    def _latest_level(self, index_id: str, *, before_date: str) -> float:
        rows = [
            row
            for row in self.level_rows(index_id)
            if str(row.get("date", "")) < before_date
        ]
        if not rows:
            return DEFAULT_BASE_LEVEL
        latest = max(rows, key=lambda row: str(row.get("date", "")))
        return float(str(latest.get("index_level", DEFAULT_BASE_LEVEL)))

    def _materialize_level_frame(
        self,
        *,
        definition: Mapping[str, object],
        report: Mapping[str, object],
        rebalance_id: str,
        constituent_frame: Mapping[str, object],
        selected: Sequence[Mapping[str, object]],
        rows: Sequence[Mapping[str, object]],
        dataset_version: str,
        effective_date: str,
        previous_constituents: Sequence[Mapping[str, object]],
        generated_by: str,
    ) -> dict[str, object]:
        selected_ids = [str(item.get("asset_id")) for item in selected]
        level_assets, level_row_diagnostics = _build_asset_returns(
            rows=rows,
            as_of_date=None,
            lookback_window=None,
            return_column=str(definition["return_column"]),
            price_column=str(definition["price_column"]),
            enforce_pit=False,
        )
        returns: dict[str, float] = {}
        missing: list[str] = []
        for asset_id in selected_ids:
            value = self._return_for_effective_date(
                asset=level_assets.get(asset_id),
                effective_date=effective_date,
            )
            if value is None:
                missing.append(asset_id)
            else:
                returns[asset_id] = value
        if not returns:
            raise ValidationError(
                "index level calculation has no valid constituent returns"
            )
        available_count = len(returns)
        coverage_ratio = available_count / len(selected_ids) if selected_ids else 0.0
        renormalized_weight = 1.0 / available_count
        daily_return = sum(value * renormalized_weight for value in returns.values())
        raw_contributions = {
            asset_id: value * renormalized_weight
            for asset_id, value in sorted(returns.items())
        }
        absolute_contribution_total = sum(
            abs(value) for value in raw_contributions.values()
        )
        return_contributions = [
            {
                "asset_id": asset_id,
                "return": round(returns[asset_id], 10),
                "normalized_weight": round(renormalized_weight, 12),
                "contribution": round(contribution, 10),
                "abs_contribution_share": round(
                    abs(contribution) / absolute_contribution_total, 10
                )
                if absolute_contribution_total > 0.0
                else 0.0,
            }
            for asset_id, contribution in raw_contributions.items()
        ]
        previous_level = self._latest_level(
            str(definition["index_id"]), before_date=effective_date
        )
        level = previous_level * (1.0 + daily_return)
        previous_ids = {str(item.get("asset_id")) for item in previous_constituents}
        current_ids = set(selected_ids)
        added = sorted(current_ids - previous_ids)
        dropped = sorted(previous_ids - current_ids)
        turnover = self._turnover(previous_constituents, selected)
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
            "missing_constituents": missing,
            "available_constituents": sorted(returns),
            "renormalized_available_weight": round(renormalized_weight, 12),
            "return_contributions": return_contributions,
            "turnover": round(turnover, 10),
            "added_constituents": added,
            "dropped_constituents": dropped,
        }
        frame_id = (
            "corrlvl_"
            + sha256_hash(
                {
                    "index_id": definition["index_id"],
                    "report_id": report["report_id"],
                    "row": row,
                }
            )[:20]
        )
        payload = {
            "schema_version": MARKET_CORRELATION_SCHEMA_VERSION,
            "record_type": "correlation_core_index_level_frame",
            "level_frame_id": frame_id,
            "index_id": definition["index_id"],
            "report_id": report["report_id"],
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
                "missing_constituents": missing,
                "renormalized": bool(missing),
                "policy": "available_constituent_equal_weight_renormalization@1.0",
                "level_row_diagnostics": level_row_diagnostics,
            },
            "auto_action_taken": False,
            "factor_lifecycle_mutation": False,
            "generated_by": generated_by,
            "generated_at": utcnow(),
        }
        artifact = materialize_artifact(
            frame_id, "correlation_core_index_level_frame", payload
        )
        record: dict[str, object] = {
            **payload,
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "storage_uri": artifact.storage_uri,
        }
        upsert_record("correlation_core_index_level_frames", frame_id, record)
        return record

    def _turnover(
        self,
        previous_constituents: Sequence[Mapping[str, object]],
        selected: Sequence[Mapping[str, object]],
    ) -> float:
        current_count = len(selected)
        if current_count == 0:
            return 0.0
        current = {str(item.get("asset_id")): 1.0 / current_count for item in selected}
        if not previous_constituents:
            return 1.0
        previous = {
            str(item.get("asset_id")): _optional_float(item.get("target_weight")) or 0.0
            for item in previous_constituents
        }
        keys = set(previous) | set(current)
        return 0.5 * sum(
            abs(current.get(key, 0.0) - previous.get(key, 0.0)) for key in keys
        )

    def _effective_returns(
        self,
        *,
        rows: Sequence[Mapping[str, object]],
        definition: Mapping[str, object],
        effective_date: str,
    ) -> dict[str, float]:
        assets, _diagnostics = _build_asset_returns(
            rows=rows,
            as_of_date=None,
            lookback_window=None,
            return_column=str(definition["return_column"]),
            price_column=str(definition["price_column"]),
            enforce_pit=False,
        )
        returns: dict[str, float] = {}
        for asset_id, asset in sorted(assets.items()):
            value = self._return_for_effective_date(
                asset=asset,
                effective_date=effective_date,
            )
            if value is not None:
                returns[asset_id] = value
        return returns

    def _bucket_concentration(
        self, counts: Mapping[str, int]
    ) -> dict[str, object]:
        ordered = dict(sorted(counts.items()))
        total = sum(ordered.values())
        ratios = {
            key: round(value / total, 10) if total else 0.0
            for key, value in ordered.items()
        }
        max_bucket = max(ordered, key=lambda key: ordered[key], default="")
        max_bucket_ratio = ratios.get(max_bucket, 0.0) if max_bucket else 0.0
        hhi = sum(value**2 for value in ratios.values())
        return {
            "counts": ordered,
            "ratios": ratios,
            "bucket_count": len(ordered),
            "max_bucket": max_bucket,
            "max_bucket_ratio": round(max_bucket_ratio, 10),
            "hhi": round(hhi, 10),
            "concentration_warning": max_bucket_ratio >= 0.50 and total >= 2,
        }

    def _distribution_stability(
        self, *, report: Mapping[str, object]
    ) -> dict[str, object]:
        def metrics(source: Mapping[str, object]) -> dict[str, float | None]:
            summary = _mapping(source.get("correlation_summary"))
            ratios = _mapping(source.get("ratio_summary"))
            return {
                "mean": _optional_float(summary.get("mean")),
                "median": _optional_float(summary.get("median")),
                "std": _optional_float(summary.get("std")),
                "strong_positive_ratio": _optional_float(
                    ratios.get("strong_positive_ratio")
                ),
                "near_zero_ratio": _optional_float(ratios.get("near_zero_ratio")),
                "negative_ratio": _optional_float(ratios.get("negative_ratio")),
            }

        universe_ref = str(report.get("universe_ref", ""))
        as_of_date = str(report.get("as_of_date", ""))
        lookback_window = _int_value(report.get("lookback_window"))
        min_periods = _int_value(report.get("min_periods"))
        current_metrics = metrics(report)
        previous_reports = [
            candidate
            for candidate in self.list_reports(universe_ref=universe_ref)
            if str(candidate.get("as_of_date", "")) < as_of_date
            and _int_value(candidate.get("lookback_window")) == lookback_window
            and _int_value(candidate.get("min_periods")) == min_periods
        ]
        previous = _latest_by_date(
            previous_reports,
            date_key="as_of_date",
            before_date=as_of_date,
        )
        if not previous:
            return {
                "status": "insufficient_history",
                "as_of_date": as_of_date,
                "current": current_metrics,
                "previous_as_of_date": "",
                "deltas": {},
            }
        previous_metrics = metrics(previous)
        deltas: dict[str, float] = {}
        for key, current_value in current_metrics.items():
            previous_value = previous_metrics.get(key)
            if current_value is None or previous_value is None:
                continue
            deltas[key] = round(current_value - previous_value, 10)
        return {
            "status": "computed",
            "as_of_date": as_of_date,
            "previous_as_of_date": previous.get("as_of_date", ""),
            "current": current_metrics,
            "previous": previous_metrics,
            "deltas": deltas,
        }

    def _turnover_stability(
        self,
        *,
        index_id: str,
        effective_date: str,
        turnover: float,
        added: Sequence[str],
        dropped: Sequence[str],
    ) -> dict[str, object]:
        previous_rebalances = [
            row
            for row in self.list_rebalances(index_id)
            if str(row.get("effective_date", "")) < effective_date
        ]
        history = [
            _safe_float(row.get("turnover"))
            for row in previous_rebalances
            if _optional_float(row.get("turnover")) is not None
        ]
        values = [*history, turnover]
        return {
            "turnover": round(turnover, 10),
            "latest_turnover": round(turnover, 10),
            "history_count": len(values),
            "previous_rebalance_count": len(previous_rebalances),
            "mean_turnover": round(_mean(values), 10) if values else 0.0,
            "max_turnover": round(max(values), 10) if values else 0.0,
            "added_count": len(added),
            "dropped_count": len(dropped),
        }

    def _cap_weight_benchmark_comparison(
        self,
        *,
        rows: Sequence[Mapping[str, object]],
        definition: Mapping[str, object],
        effective_returns: Mapping[str, float],
        level_frame: Mapping[str, object],
        effective_date: str,
    ) -> dict[str, object]:
        market_caps = _latest_market_caps(rows, effective_date=effective_date)
        eligible = {
            asset_id: (return_value, market_caps[asset_id])
            for asset_id, return_value in effective_returns.items()
            if asset_id in market_caps and market_caps[asset_id] > 0.0
        }
        if not eligible:
            return {
                "status": "missing_market_cap",
                "message": "No positive market_cap values available for benchmark.",
                "core_daily_return": self._level_daily_return(level_frame),
                "benchmark_asset_count": 0,
                "universe_return_count": len(effective_returns),
            }
        total_cap = sum(cap for _return_value, cap in eligible.values())
        benchmark_return = sum(
            return_value * cap / total_cap
            for return_value, cap in eligible.values()
        )
        core_return = self._level_daily_return(level_frame)
        return {
            "status": "computed",
            "benchmark": "cap_weighted_available_universe",
            "effective_date": effective_date,
            "index_id": definition.get("index_id", ""),
            "core_daily_return": round(core_return, 10),
            "cap_weight_benchmark_return": round(benchmark_return, 10),
            "excess_return": round(core_return - benchmark_return, 10),
            "benchmark_asset_count": len(eligible),
            "universe_return_count": len(effective_returns),
            "market_cap_coverage_ratio": round(
                len(eligible) / len(effective_returns), 10
            )
            if effective_returns
            else 0.0,
        }

    def _random_basket_comparison(
        self,
        *,
        effective_returns: Mapping[str, float],
        selected: Sequence[Mapping[str, object]],
        level_frame: Mapping[str, object],
        random_basket_count: int,
        random_seed: int,
    ) -> dict[str, object]:
        selected_count = len(selected)
        candidate_ids = sorted(effective_returns)
        if random_basket_count == 0:
            return {
                "status": "disabled",
                "basket_count_requested": random_basket_count,
            }
        if selected_count <= 0 or len(candidate_ids) < selected_count:
            return {
                "status": "insufficient_universe",
                "basket_count_requested": random_basket_count,
                "basket_size": selected_count,
                "candidate_count": len(candidate_ids),
            }
        rng = random.Random(random_seed)
        basket_returns: list[float] = []
        for _index in range(random_basket_count):
            basket = rng.sample(candidate_ids, selected_count)
            basket_returns.append(
                _mean([effective_returns[asset_id] for asset_id in basket])
            )
        ordered = sorted(basket_returns)
        core_return = self._level_daily_return(level_frame)
        percentile = (
            sum(1 for value in ordered if value <= core_return) / len(ordered)
            if ordered
            else 0.0
        )
        random_mean = _mean(ordered)
        return {
            "status": "computed",
            "basket_count_requested": random_basket_count,
            "basket_count_evaluated": len(ordered),
            "basket_size": selected_count,
            "candidate_count": len(candidate_ids),
            "random_seed": random_seed,
            "random_return_mean": round(random_mean, 10),
            "random_return_median": _quantile(ordered, 0.5),
            "random_return_q05": _quantile(ordered, 0.05),
            "random_return_q95": _quantile(ordered, 0.95),
            "core_daily_return": round(core_return, 10),
            "core_minus_random_mean": round(core_return - random_mean, 10),
            "core_percentile_vs_random": round(percentile, 10),
        }

    def _level_daily_return(self, level_frame: Mapping[str, object]) -> float:
        rows = level_frame.get("rows", [])
        if not isinstance(rows, Sequence) or isinstance(rows, str) or not rows:
            return 0.0
        first_row = rows[0]
        if not isinstance(first_row, Mapping):
            return 0.0
        return _safe_float(first_row.get("daily_return"))

    def _contribution_concentration(
        self,
        *,
        selected: Sequence[Mapping[str, object]],
        level_frame: Mapping[str, object],
    ) -> dict[str, object]:
        rows = level_frame.get("rows", [])
        first_row: dict[str, object] = {}
        if isinstance(rows, Sequence) and not isinstance(rows, str) and rows:
            first_row = _mapping(rows[0])
        raw_contributions = first_row.get("return_contributions", [])
        contributions = [
            dict(cast(Mapping[str, object], item))
            for item in raw_contributions
            if isinstance(item, Mapping)
        ] if isinstance(raw_contributions, Sequence) and not isinstance(
            raw_contributions, str
        ) else []
        if contributions:
            abs_shares = [
                _safe_float(item.get("abs_contribution_share"))
                for item in contributions
            ]
            top = sorted(
                contributions,
                key=lambda item: abs(_safe_float(item.get("contribution"))),
                reverse=True,
            )[:10]
            return {
                "status": "computed_from_effective_returns",
                "contribution_count": len(contributions),
                "max_abs_contribution_share": round(max(abs_shares), 10),
                "hhi_abs_contribution_share": round(
                    sum(value**2 for value in abs_shares),
                    10,
                ),
                "top_contributors": top,
            }
        score_values = [float(str(item.get("score", 0.0))) for item in selected]
        total_score = sum(score_values)
        score_concentration = (
            max(score_values) / total_score
            if total_score > 0.0 and score_values
            else 0.0
        )
        return {
            "status": "score_fallback_no_effective_return_contributions",
            "contribution_count": len(score_values),
            "max_abs_contribution_share": round(score_concentration, 10),
            "hhi_abs_contribution_share": 0.0,
            "top_contributors": [],
        }

    def _lookback_sensitivity(
        self,
        *,
        rows: Sequence[Mapping[str, object]],
        definition: Mapping[str, object],
        base_selected_ids: Sequence[str],
        as_of_date: str,
        lookback_sensitivity_windows: Sequence[int] | None,
    ) -> dict[str, object]:
        base_window = _int_value(definition.get("lookback_window"))
        selection_count = _int_value(definition.get("selection_count"))
        default_windows = [
            max(2, base_window // 2),
            base_window,
            max(2, base_window * 2),
        ]
        windows = _clean_sensitivity_values(
            lookback_sensitivity_windows,
            default_values=default_windows,
            minimum=2,
            field_name="lookback_sensitivity_windows",
        )
        base_set = set(base_selected_ids)
        scenario_rows: list[dict[str, object]] = []
        for window in windows:
            try:
                computation = self._compute_report(
                    rows=rows,
                    as_of_date=as_of_date,
                    lookback_window=window,
                    min_periods=_int_value(definition.get("min_periods")),
                    return_column=str(definition["return_column"]),
                    price_column=str(definition["price_column"]),
                    dense_universe_cap=DEFAULT_DENSE_UNIVERSE_CAP,
                    top_pair_count=DEFAULT_TOP_PAIR_COUNT,
                    histogram_bucket_count=20,
                    streaming_sample_limit=DEFAULT_STREAMING_SAMPLE_LIMIT,
                    centrality_export_limit=max(
                        DEFAULT_CENTRALITY_EXPORT_LIMIT,
                        selection_count,
                    ),
                )
                temp_report = {
                    "centrality_scores": computation.centrality_scores,
                    "centrality_score_count": computation.centrality_score_count,
                    "centrality_scores_truncated": (
                        computation.centrality_scores_truncated
                    ),
                }
                scenario_selected, _selection_rows = self._select_topk(
                    temp_report,
                    selection_count=selection_count,
                )
                scenario_ids = [str(item.get("asset_id")) for item in scenario_selected]
                overlap_count = len(base_set & set(scenario_ids))
                scenario_rows.append(
                    {
                        "lookback_window": window,
                        "status": "computed",
                        "selected_asset_ids": scenario_ids,
                        "overlap_count": overlap_count,
                        "overlap_ratio": round(
                            overlap_count / len(base_set), 10
                        )
                        if base_set
                        else 0.0,
                        "correlation_mean": round(
                            computation.correlation_sum
                            / computation.pair_count_evaluated,
                            10,
                        )
                        if computation.pair_count_evaluated
                        else 0.0,
                        "pair_count_evaluated": computation.pair_count_evaluated,
                    }
                )
            except ValidationError as exc:
                scenario_rows.append(
                    {
                        "lookback_window": window,
                        "status": "error",
                        "message": str(exc),
                    }
                )
        computed = [row for row in scenario_rows if row.get("status") == "computed"]
        return {
            "status": "computed" if computed else "error",
            "base_lookback_window": base_window,
            "scenario_count": len(scenario_rows),
            "scenarios": scenario_rows,
        }

    def _selection_count_sensitivity(
        self,
        *,
        report: Mapping[str, object],
        base_selected_ids: Sequence[str],
        selection_count_sensitivity_values: Sequence[int] | None,
    ) -> dict[str, object]:
        base_count = len(base_selected_ids)
        default_counts = [max(1, base_count // 2), base_count, max(1, base_count * 2)]
        counts = _clean_sensitivity_values(
            selection_count_sensitivity_values,
            default_values=default_counts,
            minimum=1,
            field_name="selection_count_sensitivity_values",
        )
        base_set = set(base_selected_ids)
        scenario_rows: list[dict[str, object]] = []
        for count in counts:
            try:
                scenario_selected, _selection_rows = self._select_topk(
                    report,
                    selection_count=count,
                )
                scenario_ids = [str(item.get("asset_id")) for item in scenario_selected]
                overlap_count = len(base_set & set(scenario_ids))
                scenario_rows.append(
                    {
                        "selection_count": count,
                        "status": "computed",
                        "selected_asset_ids": scenario_ids,
                        "overlap_count": overlap_count,
                        "overlap_ratio": round(
                            overlap_count / len(base_set), 10
                        )
                        if base_set
                        else 0.0,
                        "mean_selected_score": round(
                            _mean(
                                [
                                    float(str(item.get("score", 0.0)))
                                    for item in scenario_selected
                                ]
                            ),
                            10,
                        ),
                    }
                )
            except ValidationError as exc:
                scenario_rows.append(
                    {
                        "selection_count": count,
                        "status": "error",
                        "message": str(exc),
                    }
                )
        computed = [row for row in scenario_rows if row.get("status") == "computed"]
        return {
            "status": "computed" if computed else "error",
            "base_selection_count": base_count,
            "scenario_count": len(scenario_rows),
            "scenarios": scenario_rows,
        }

    def _materialize_rebalance(
        self,
        *,
        definition: Mapping[str, object],
        report: Mapping[str, object],
        rebalance_id: str,
        constituent_frame: Mapping[str, object],
        level_frame: Mapping[str, object],
        selected: Sequence[Mapping[str, object]],
        previous_constituents: Sequence[Mapping[str, object]],
        rows: Sequence[Mapping[str, object]],
        as_of_date: str,
        effective_date: str,
        random_basket_count: int,
        random_seed: int,
        lookback_sensitivity_windows: Sequence[int] | None,
        selection_count_sensitivity_values: Sequence[int] | None,
        generated_by: str,
    ) -> dict[str, object]:
        previous_ids = {str(item.get("asset_id")) for item in previous_constituents}
        current_ids = {str(item.get("asset_id")) for item in selected}
        added = sorted(current_ids - previous_ids)
        dropped = sorted(previous_ids - current_ids)
        turnover = self._turnover(previous_constituents, selected)
        research_diagnostics = self._research_diagnostics(
            definition=definition,
            report=report,
            selected=selected,
            level_frame=level_frame,
            rows=rows,
            previous_constituents=previous_constituents,
            turnover=turnover,
            added=added,
            dropped=dropped,
            as_of_date=as_of_date,
            effective_date=effective_date,
            random_basket_count=random_basket_count,
            random_seed=random_seed,
            lookback_sensitivity_windows=lookback_sensitivity_windows,
            selection_count_sensitivity_values=selection_count_sensitivity_values,
        )
        payload = {
            "schema_version": MARKET_CORRELATION_SCHEMA_VERSION,
            "record_type": "correlation_core_index_rebalance",
            "rebalance_id": rebalance_id,
            "index_id": definition["index_id"],
            "report_id": report["report_id"],
            "constituent_frame_id": constituent_frame["constituent_frame_id"],
            "level_frame_id": level_frame["level_frame_id"],
            "formation_date": as_of_date,
            "effective_date": effective_date,
            "selection_count": len(selected),
            "selection_method": definition["selection_method"],
            "weighting_method": "equal_weight",
            "turnover": round(turnover, 10),
            "added_constituents": added,
            "dropped_constituents": dropped,
            "coverage_diagnostics": level_frame.get("coverage_diagnostics", {}),
            "research_diagnostics": research_diagnostics,
            "auto_action_taken": False,
            "factor_lifecycle_mutation": False,
            "generated_by": generated_by,
            "generated_at": utcnow(),
        }
        artifact = materialize_artifact(
            rebalance_id, "correlation_core_index_rebalance", payload
        )
        record: dict[str, object] = {
            **payload,
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "storage_uri": artifact.storage_uri,
        }
        upsert_record("correlation_core_index_rebalances", rebalance_id, record)
        _ = event_store.append(
            event_type="correlation_core_index_rebalance.created",
            payload={"rebalance_id": rebalance_id, "index_id": definition["index_id"]},
            run_id=rebalance_id,
        )
        return record

    def _research_diagnostics(
        self,
        *,
        definition: Mapping[str, object],
        report: Mapping[str, object],
        selected: Sequence[Mapping[str, object]],
        level_frame: Mapping[str, object],
        rows: Sequence[Mapping[str, object]],
        previous_constituents: Sequence[Mapping[str, object]],
        turnover: float,
        added: Sequence[str],
        dropped: Sequence[str],
        as_of_date: str,
        effective_date: str,
        random_basket_count: int,
        random_seed: int,
        lookback_sensitivity_windows: Sequence[int] | None,
        selection_count_sensitivity_values: Sequence[int] | None,
    ) -> dict[str, object]:
        industries: dict[str, int] = defaultdict(int)
        sectors: dict[str, int] = defaultdict(int)
        size_buckets: dict[str, int] = defaultdict(int)
        for item in selected:
            industries[str(item.get("industry", "unknown")) or "unknown"] += 1
            sectors[str(item.get("sector", "unknown")) or "unknown"] += 1
            size_buckets[str(item.get("size_bucket", "unknown")) or "unknown"] += 1
        selected_ids = [str(item.get("asset_id")) for item in selected]
        effective_returns = self._effective_returns(
            rows=rows,
            definition=definition,
            effective_date=effective_date,
        )
        contribution_diagnostics = self._contribution_concentration(
            selected=selected,
            level_frame=level_frame,
        )
        interpretation = report.get("interpretation", {})
        fragmented = bool(
            _mapping(interpretation).get("fragmented_market_warning", False)
        )
        return {
            "raw_correlation_distribution_stability": self._distribution_stability(
                report=report
            ),
            "fragmented_market_warning": fragmented,
            "fragmented_market_diagnostics": {
                "warning": fragmented,
                "regime": _mapping(interpretation).get("regime", ""),
                "index_meaning_degraded": fragmented,
                "message": _mapping(interpretation).get("message", ""),
                "recommended_action": (
                    "Treat the core index as a weak-signal diagnostic until "
                    + "market-wide correlation strengthens."
                    if fragmented
                    else "Core index diagnostics are usable under the current "
                    + "correlation regime."
                ),
            },
            "turnover_stability": self._turnover_stability(
                index_id=str(definition["index_id"]),
                effective_date=effective_date,
                turnover=turnover,
                added=added,
                dropped=dropped,
            ),
            "sector_concentration": dict(sorted(sectors.items())),
            "industry_concentration": dict(sorted(industries.items())),
            "size_concentration": dict(sorted(size_buckets.items())),
            "sector_concentration_diagnostics": self._bucket_concentration(sectors),
            "industry_concentration_diagnostics": self._bucket_concentration(
                industries
            ),
            "size_concentration_diagnostics": self._bucket_concentration(size_buckets),
            "contribution_concentration": contribution_diagnostics[
                "max_abs_contribution_share"
            ],
            "contribution_concentration_diagnostics": contribution_diagnostics,
            "equal_weight_core_vs_cap_weight_benchmark": (
                self._cap_weight_benchmark_comparison(
                    rows=rows,
                    definition=definition,
                    effective_returns=effective_returns,
                    level_frame=level_frame,
                    effective_date=effective_date,
                )
            ),
            "random_equal_weight_basket_comparison": self._random_basket_comparison(
                effective_returns=effective_returns,
                selected=selected,
                level_frame=level_frame,
                random_basket_count=random_basket_count,
                random_seed=random_seed,
            ),
            "lookback_sensitivity": self._lookback_sensitivity(
                rows=rows,
                definition=definition,
                base_selected_ids=selected_ids,
                as_of_date=as_of_date,
                lookback_sensitivity_windows=lookback_sensitivity_windows,
            ),
            "selection_count_sensitivity": self._selection_count_sensitivity(
                report=report,
                base_selected_ids=selected_ids,
                selection_count_sensitivity_values=selection_count_sensitivity_values,
            ),
            "research_parameterization": {
                "random_basket_count": random_basket_count,
                "random_seed": random_seed,
                "lookback_sensitivity_windows": list(
                    lookback_sensitivity_windows or []
                ),
                "selection_count_sensitivity_values": list(
                    selection_count_sensitivity_values or []
                ),
                "previous_constituent_count": len(previous_constituents),
            },
        }


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value)) if isinstance(value, Mapping) else {}


market_correlation_core_service = MarketCorrelationCoreService()
