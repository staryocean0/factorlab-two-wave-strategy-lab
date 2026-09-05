# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportMissingTypeArgument=false, reportPrivateUsage=false
"""Dominant Beta Strength Cloud scan utilities.

The current productized selector is intentionally not a threshold-connected graph
algorithm.  It computes each stock's average Fisher-z transformed correlation to
all other eligible stocks, treats that cross-section as the daily market beta
cloud, and selects the names at or to the right of the left shoulder.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from factor_lab.core.errors import ValidationError
from factor_lab.market_correlation.services.market_correlation_core_service import (
    _aligned_returns,
    _AssetReturns,
    _build_asset_returns,
    _date_key,
    _load_dataset_rows,
    _pearson,
)

DEFAULT_DOMINANT_BETA_CLOUD_COVERAGE_FLOOR = 0.50
DOMINANT_BETA_CLOUD_SELECTION_RULE = (
    "dominant_beta_cloud_avg_fisher_z_strength_left_shoulder_v3_floor_50"
)


def load_rows_from_json_payload(payload: object) -> list[dict[str, object]]:
    """Extract row records from common Factor Lab artifact JSON payloads."""

    if isinstance(payload, list):
        return [
            dict(cast(Mapping[str, object], row))
            for row in payload
            if isinstance(row, Mapping)
        ]
    if not isinstance(payload, Mapping):
        raise ValidationError("rows payload must be a JSON array or object")
    for key in ("rows", "records"):
        raw_rows = payload.get(key)
        if isinstance(raw_rows, list):
            return [
                dict(cast(Mapping[str, object], row))
                for row in raw_rows
                if isinstance(row, Mapping)
            ]
    for nested_key in ("dataset_snapshot", "payload"):
        nested = payload.get(nested_key)
        if isinstance(nested, Mapping):
            for key in ("rows", "records"):
                raw_rows = nested.get(key)
                if isinstance(raw_rows, list):
                    return [
                        dict(cast(Mapping[str, object], row))
                        for row in raw_rows
                        if isinstance(row, Mapping)
                    ]
    raise ValidationError("rows payload does not contain rows/records")


def load_rows_from_json_file(path: str | Path) -> list[dict[str, object]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = load_rows_from_json_payload(payload)
    if not rows:
        raise ValidationError("rows file contains no row records")
    return rows


def _asset_member(asset: _AssetReturns) -> dict[str, object]:
    return {
        "asset_id": asset.asset_id,
        "symbol": asset.symbol,
        "industry": asset.industry,
        "sector": asset.sector,
        "size_bucket": asset.size_bucket,
        "observation_count": asset.observation_count,
    }


def _object_float(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    return 0.0


def _summary_stats(values: Sequence[float]) -> dict[str, object]:
    if not values:
        return {
            "count": 0,
            "mean": 0.0,
            "min": None,
            "max": None,
            "q50": None,
            "q95": None,
            "q99": None,
        }
    ordered = sorted(values)

    def quantile(probability: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        position = (len(ordered) - 1) * probability
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1 - weight) + ordered[upper] * weight

    return {
        "count": len(values),
        "mean": round(sum(values) / len(values), 10),
        "min": round(ordered[0], 10),
        "max": round(ordered[-1], 10),
        "q50": round(quantile(0.50), 10),
        "q95": round(quantile(0.95), 10),
        "q99": round(quantile(0.99), 10),
    }


def _distribution_stats(values: Sequence[float]) -> dict[str, object]:
    if not values:
        return {
            "count": 0,
            "mean": 0.0,
            "std": 0.0,
            "min": None,
            "max": None,
            "q01": None,
            "q05": None,
            "q25": None,
            "q50": None,
            "q75": None,
            "q95": None,
            "q99": None,
            "skew": None,
            "excess_kurtosis": None,
        }
    ordered = sorted(values)

    def quantile(probability: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        position = (len(ordered) - 1) * probability
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1 - weight) + ordered[upper] * weight

    mean = sum(ordered) / len(ordered)
    variance = sum((value - mean) ** 2 for value in ordered) / len(ordered)
    std = math.sqrt(max(0.0, variance))
    if std > 0.0:
        skew = sum(((value - mean) / std) ** 3 for value in ordered) / len(ordered)
        excess_kurtosis = (
            sum(((value - mean) / std) ** 4 for value in ordered) / len(ordered) - 3.0
        )
    else:
        skew = 0.0
        excess_kurtosis = 0.0
    return {
        "count": len(values),
        "mean": round(mean, 10),
        "std": round(std, 10),
        "min": round(ordered[0], 10),
        "max": round(ordered[-1], 10),
        "q01": round(quantile(0.01), 10),
        "q05": round(quantile(0.05), 10),
        "q25": round(quantile(0.25), 10),
        "q50": round(quantile(0.50), 10),
        "q75": round(quantile(0.75), 10),
        "q95": round(quantile(0.95), 10),
        "q99": round(quantile(0.99), 10),
        "skew": round(skew, 10),
        "excess_kurtosis": round(excess_kurtosis, 10),
    }


def _fisher_z(value: float) -> float:
    clipped = min(max(value, -0.999999), 0.999999)
    return 0.5 * math.log((1.0 + clipped) / (1.0 - clipped))


def _corr_from_fisher_z(value: float) -> float:
    if value >= 20.0:
        return 1.0
    if value <= -20.0:
        return -1.0
    exp_value = math.exp(2.0 * value)
    return (exp_value - 1.0) / (exp_value + 1.0)


def _strength_curve_rows(
    *,
    sorted_rows: Sequence[Mapping[str, object]],
    left_shoulder_z: float,
    selected_count: int,
) -> list[dict[str, object]]:
    universe_size = len(sorted_rows)
    if universe_size == 0:
        return []
    stride = max(1, universe_size // 100)
    ranks = set(range(1, universe_size + 1, stride))
    ranks.add(universe_size)
    ranks.add(max(1, min(universe_size, selected_count)))
    curve: list[dict[str, object]] = []
    for rank in sorted(ranks):
        row = sorted_rows[rank - 1]
        threshold_z = _object_float(row.get("beta_strength_z"))
        threshold = _object_float(row.get("beta_strength"))
        curve.append(
            {
                "rank_cutoff": rank,
                "strength_threshold": round(threshold, 10),
                "strength_threshold_z": round(threshold_z, 10),
                "left_shoulder_z": round(left_shoulder_z, 10),
                "distance_to_left_shoulder_z": round(
                    threshold_z - left_shoulder_z, 10
                ),
                "selected_count": rank,
                "coverage_ratio": round(rank / universe_size, 10),
                "selected_boundary": rank == selected_count,
            }
        )
    return curve


def _strength_histogram_rows(
    *,
    values: Sequence[float],
    bin_count: int = 40,
) -> list[dict[str, object]]:
    if not values:
        return []
    ordered = sorted(values)
    lower = ordered[0]
    upper = ordered[-1]
    if lower == upper:
        return [
            {
                "bin": 1,
                "lower": round(lower, 10),
                "upper": round(upper, 10),
                "count": len(values),
                "density": 1.0,
            }
        ]
    count = max(5, min(bin_count, int(math.sqrt(len(values))) * 2))
    width = (upper - lower) / count
    bins = [0 for _ in range(count)]
    for value in values:
        index = min(count - 1, max(0, int((value - lower) / width)))
        bins[index] += 1
    total = len(values)
    return [
        {
            "bin": index + 1,
            "lower": round(lower + index * width, 10),
            "upper": round(lower + (index + 1) * width, 10),
            "count": bin_value,
            "density": round(bin_value / total, 10),
        }
        for index, bin_value in enumerate(bins)
    ]


def select_dominant_beta_strength_cloud(
    strength_rows: Sequence[Mapping[str, object]],
    *,
    coverage_floor: float = DEFAULT_DOMINANT_BETA_CLOUD_COVERAGE_FLOOR,
    shoulder_sigma_multiplier: float = 1.0,
) -> dict[str, object]:
    """Select stocks inside the full-market beta-strength left shoulder."""

    if not math.isfinite(coverage_floor) or not 0.0 <= coverage_floor <= 1.0:
        raise ValidationError("coverage_floor must be in [0, 1]")
    if not math.isfinite(shoulder_sigma_multiplier) or shoulder_sigma_multiplier < 0:
        raise ValidationError("shoulder_sigma_multiplier must be non-negative")
    rows = [
        dict(row)
        for row in strength_rows
        if math.isfinite(_object_float(row.get("beta_strength_z")))
    ]
    if not rows:
        return {
            "selection_rule": DOMINANT_BETA_CLOUD_SELECTION_RULE,
            "status": "no_strength_rows",
            "coverage_floor": round(coverage_floor, 10),
            "curve": [],
            "component": {},
        }
    rows = sorted(
        rows,
        key=lambda row: (
            -_object_float(row.get("beta_strength_z")),
            str(row.get("asset_id") or ""),
        ),
    )
    universe_size = len(rows)
    values = [_object_float(row["beta_strength_z"]) for row in rows]
    mean_z = sum(values) / universe_size
    variance = sum((value - mean_z) ** 2 for value in values) / universe_size
    sigma_z = math.sqrt(max(0.0, variance))
    left_shoulder_z = mean_z - shoulder_sigma_multiplier * sigma_z
    effective_threshold_z = left_shoulder_z
    threshold_adjusted_to_floor = False
    minimum_count = max(
        2 if universe_size >= 2 else 1,
        math.ceil(coverage_floor * universe_size),
    )
    selected = [
        row for row in rows if _object_float(row["beta_strength_z"]) >= left_shoulder_z
    ]
    if len(selected) < minimum_count:
        threshold_adjusted_to_floor = True
        effective_threshold_z = _object_float(
            rows[minimum_count - 1]["beta_strength_z"]
        )
        selected = [
            row
            for row in rows
            if _object_float(row["beta_strength_z"]) >= effective_threshold_z
        ]
    selected_count = len(selected)
    selected_cutoff_z = (
        min(_object_float(row["beta_strength_z"]) for row in selected)
        if selected
        else effective_threshold_z
    )
    selected_members: list[dict[str, object]] = []
    selected_ids = {str(row.get("asset_id") or "") for row in selected}
    for rank, row in enumerate(rows, start=1):
        if str(row.get("asset_id") or "") not in selected_ids:
            continue
        member = dict(row)
        member["beta_strength_rank"] = rank
        selected_members.append(member)
    coverage = selected_count / universe_size if universe_size else 0.0
    raw_values = [_object_float(row.get("avg_corr")) for row in rows]
    curve = _strength_curve_rows(
        sorted_rows=rows,
        left_shoulder_z=left_shoulder_z,
        selected_count=selected_count,
    )
    return {
        "selection_rule": DOMINANT_BETA_CLOUD_SELECTION_RULE,
        "status": "selected" if selected_count >= minimum_count else "below_floor",
        "coverage_floor": round(coverage_floor, 10),
        "selection_metric": "avg_fisher_z_strength_distribution_left_shoulder",
        "strength_threshold": round(_corr_from_fisher_z(effective_threshold_z), 10),
        "strength_threshold_z": round(effective_threshold_z, 10),
        "strength_selected_cutoff": round(_corr_from_fisher_z(selected_cutoff_z), 10),
        "strength_selected_cutoff_z": round(selected_cutoff_z, 10),
        "strength_mean_z": round(mean_z, 10),
        "strength_sigma_z": round(sigma_z, 10),
        "strength_left_shoulder_z": round(left_shoulder_z, 10),
        "strength_mean": round(_corr_from_fisher_z(mean_z), 10),
        "strength_left_shoulder": round(_corr_from_fisher_z(left_shoulder_z), 10),
        "shoulder_sigma_multiplier": round(shoulder_sigma_multiplier, 10),
        "threshold_adjusted_to_coverage_floor": threshold_adjusted_to_floor,
        "normal_left_shoulder_coverage_expected": 0.8413447461
        if shoulder_sigma_multiplier == 1.0
        else None,
        "selected_count": selected_count,
        "coverage_ratio": round(coverage, 10),
        "eligible_asset_count": universe_size,
        "distribution_summary_z": _distribution_stats(values),
        "distribution_summary_corr": _distribution_stats(raw_values),
        "histogram": _strength_histogram_rows(values=values),
        "curve": curve,
        "component": {
            "rank": 1,
            "component_id": "dominant_beta_strength_cloud",
            "size": selected_count,
            "coverage_ratio": round(coverage, 10),
            "members": selected_members,
            "members_truncated": False,
            "selection_semantics": "avg_fisher_z_strength_at_or_right_of_left_shoulder",
        },
    }


def scan_beta_strength_cloud(
    *,
    rows: Sequence[Mapping[str, object]] | None = None,
    dataset_version: str | None = None,
    universe_ref: str,
    as_of_date: str,
    lookback_window: int,
    min_periods: int,
    return_column: str = "return",
    price_column: str = "close",
    enforce_pit: bool = True,
    coverage_floor: float | None = None,
) -> dict[str, object]:
    """Compute the current beta-strength cloud from row-oriented market data."""

    if not universe_ref.strip():
        raise ValidationError("universe_ref is required")
    as_of_date = _date_key(as_of_date, field_name="as_of_date")
    if lookback_window < 2:
        raise ValidationError("lookback_window must be >= 2")
    if min_periods < 2:
        raise ValidationError("min_periods must be >= 2")
    resolved_coverage_floor = (
        DEFAULT_DOMINANT_BETA_CLOUD_COVERAGE_FLOOR
        if coverage_floor is None
        else coverage_floor
    )
    if not math.isfinite(resolved_coverage_floor) or not (
        0.0 <= resolved_coverage_floor <= 1.0
    ):
        raise ValidationError("coverage_floor must be in [0, 1]")
    if rows is None:
        if not dataset_version:
            raise ValidationError("rows or dataset_version is required")
        working_rows = _load_dataset_rows(dataset_version)
        source_mode = "dataset_version"
        resolved_dataset_version = dataset_version
    else:
        working_rows = [dict(row) for row in rows]
        if not working_rows:
            raise ValidationError("rows must not be empty")
        source_mode = "rows"
        resolved_dataset_version = dataset_version or "inline_market_rows@adhoc"

    assets, row_diagnostics = _build_asset_returns(
        rows=working_rows,
        as_of_date=as_of_date,
        lookback_window=lookback_window,
        return_column=return_column,
        price_column=price_column,
        enforce_pit=enforce_pit,
    )
    eligible = sorted(
        asset_id
        for asset_id, asset in assets.items()
        if asset.observation_count >= min_periods
    )
    if len(eligible) < 2:
        raise ValidationError("pool scan requires at least two eligible assets")

    skipped: list[dict[str, object]] = []
    correlations: list[float] = []
    strength_corr_sums = {asset_id: 0.0 for asset_id in eligible}
    strength_fisher_z_sums = {asset_id: 0.0 for asset_id in eligible}
    strength_abs_corr_sums = {asset_id: 0.0 for asset_id in eligible}
    strength_pair_counts = {asset_id: 0 for asset_id in eligible}
    pair_count_total = len(eligible) * (len(eligible) - 1) // 2
    pair_count_evaluated = 0
    pair_count_skipped = 0

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
            correlations.append(corr)
            fisher_z_corr = _fisher_z(corr)
            strength_corr_sums[left_id] += corr
            strength_corr_sums[right_id] += corr
            strength_fisher_z_sums[left_id] += fisher_z_corr
            strength_fisher_z_sums[right_id] += fisher_z_corr
            strength_abs_corr_sums[left_id] += abs(corr)
            strength_abs_corr_sums[right_id] += abs(corr)
            strength_pair_counts[left_id] += 1
            strength_pair_counts[right_id] += 1

    strength_rows: list[dict[str, object]] = []
    for asset_id in eligible:
        pair_count = strength_pair_counts[asset_id]
        avg_corr = strength_corr_sums[asset_id] / pair_count if pair_count else 0.0
        avg_fisher_z = (
            strength_fisher_z_sums[asset_id] / pair_count if pair_count else 0.0
        )
        beta_strength = _corr_from_fisher_z(avg_fisher_z)
        abs_avg_corr = (
            strength_abs_corr_sums[asset_id] / pair_count if pair_count else 0.0
        )
        strength_rows.append(
            {
                **_asset_member(assets[asset_id]),
                "pair_count": pair_count,
                "corr_sum": round(strength_corr_sums[asset_id], 10),
                "avg_corr": round(avg_corr, 10),
                "fisher_z_sum": round(strength_fisher_z_sums[asset_id], 10),
                "beta_strength_z": round(avg_fisher_z, 10),
                "beta_strength": round(beta_strength, 10),
                "abs_corr_sum": round(strength_abs_corr_sums[asset_id], 10),
                "abs_avg_corr": round(abs_avg_corr, 10),
            }
        )
    strength_rows = sorted(
        strength_rows,
        key=lambda row: (
            -_object_float(row.get("beta_strength_z")),
            str(row.get("asset_id") or ""),
        ),
    )
    for rank, row in enumerate(strength_rows, start=1):
        row["beta_strength_rank"] = rank

    dominant_beta_cloud = select_dominant_beta_strength_cloud(
        strength_rows,
        coverage_floor=resolved_coverage_floor,
    )
    universe_size = len(eligible)
    return {
        "schema_version": "market_correlation_beta_strength_cloud_scan@2.0",
        "record_type": "market_correlation_beta_strength_cloud_scan",
        "universe_ref": universe_ref,
        "dataset_version": resolved_dataset_version,
        "source_mode": source_mode,
        "as_of_date": as_of_date,
        "lookback_window": lookback_window,
        "min_periods": min_periods,
        "return_column": return_column,
        "price_column": price_column,
        "correlation_method": "pearson_avg_fisher_z_strength",
        "neutralization_mode": "raw",
        "universe_size": universe_size,
        "pair_count_total": pair_count_total,
        "pair_count_evaluated": pair_count_evaluated,
        "pair_count_skipped": pair_count_skipped,
        "correlation_summary": _summary_stats(correlations),
        "beta_strength_summary": _distribution_stats(
            [_object_float(row.get("beta_strength")) for row in strength_rows]
        ),
        "beta_strength_z_summary": _distribution_stats(
            [_object_float(row.get("beta_strength_z")) for row in strength_rows]
        ),
        "beta_strength_rows": strength_rows,
        "dominant_beta_cloud": dominant_beta_cloud,
        "data_quality": {
            **row_diagnostics,
            "eligible_asset_count": universe_size,
            "ineligible_asset_count": len(assets) - universe_size,
            "skipped_pair_diagnostics": skipped,
        },
        "auto_action_taken": False,
        "factor_lifecycle_mutation": False,
    }
