"""Strictly causal 1d representative attributes for market-state A1.

The module materializes a deliberately small vertical slice.  Formula, source,
frequency and availability authority is captured in exact ``FeatureSpec``
records; ``MarketAttributeSpec`` only adds ontology and scale policy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, cast

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.factor_engine.feature_library import FeatureLibrary, FeatureSpec
from factor_lab.market_state.contracts import FeatureSpecRef, MarketAttributeSpec

BAR_FREQUENCY: Final[str] = "1d"
FEATURE_VERSION: Final[str] = "1.0"
STATE_POLICY_VERSION: Final[str] = "state_policy_v1"
STATE_SMOOTHING_SCALE_ID: Final[str] = "ewma_gap_20d_60d"
NORMALIZATION_REFERENCE_ID: Final[str] = "structural_252d"
TIMEZONE: Final[str] = "Asia/Shanghai"

MEASUREMENT_SCALES: Final[dict[str, int]] = {
    "fast_20d": 20,
    "medium_60d": 60,
    "slow_120d": 120,
}
LEGACY_SCALE_LABELS: Final[dict[str, int]] = {"legacy_100d": 100}


@dataclass(frozen=True, slots=True)
class _AttributeDefinition:
    physical_attribute_id: str
    chinese_name: str
    english_name: str
    attribute_family: str
    legacy_column_prefix: str | None = None


_DEFINITIONS: Final[tuple[_AttributeDefinition, ...]] = (
    _AttributeDefinition(
        "bdci", "方向连续度", "bar direction continuity", "direction",
        "bdci",
    ),
    _AttributeDefinition(
        "bci_imbalance", "涨跌日净偏斜", "bar color imbalance", "direction",
        "bci_imbalance",
    ),
    _AttributeDefinition(
        "wbi", "幅度加权方向压力", "weighted bar imbalance", "direction",
        "wbi",
    ),
    _AttributeDefinition(
        "path_efficiency", "路径效率", "path efficiency", "path_geometry",
        "path_efficiency",
    ),
    _AttributeDefinition(
        "mean_abs_return", "平均绝对收益", "mean absolute return", "amplitude",
        "mean_abs_return",
    ),
    _AttributeDefinition(
        "realized_volatility", "实现波动", "realized volatility", "volatility",
        "volatility",
    ),
    _AttributeDefinition(
        "volatility_of_volatility", "波动的波动", "volatility of volatility",
        "volatility", "vol_of_vol",
    ),
    _AttributeDefinition(
        "downside_semivolatility", "下行半波动", "downside semivolatility",
        "tail_asymmetry",
    ),
    _AttributeDefinition(
        "upside_semivolatility", "上行半波动", "upside semivolatility",
        "tail_asymmetry",
    ),
    _AttributeDefinition(
        "tail_energy_concentration", "尾部能量集中度", "tail energy concentration",
        "tail_asymmetry",
    ),
    _AttributeDefinition(
        "lag1_autocorrelation", "一阶收益自相关", "lag-one return autocorrelation",
        "memory", "lag1_autocorr",
    ),
)

ATTRIBUTE_OUTPUT_COLUMNS: Final[tuple[str, ...]] = (
    "carrier_id",
    "carrier_definition_version",
    "bar_frequency",
    "observation_time",
    "available_at",
    "feature_id",
    "feature_version",
    "physical_attribute_id",
    "attribute_family",
    "measurement_scale_id",
    "raw_value",
    "attribute_valid",
)


def build_feature_library_1d() -> FeatureLibrary:
    """Return the exact A1 FeatureSpec authority for representative 1d fields."""

    specs: list[FeatureSpec] = []
    for definition in _DEFINITIONS:
        for scale_id, window in MEASUREMENT_SCALES.items():
            feature_id = _feature_id(definition.physical_attribute_id, scale_id)
            specs.append(
                FeatureSpec(
                    feature_id=feature_id,
                    chinese_name=f"{window}日{definition.chinese_name}",
                    english_name=f"{window}-day {definition.english_name}",
                    formula=_formula(definition.physical_attribute_id, window),
                    data_sources=("datahub:cloudridge:1d:close",),
                    frequency=BAR_FREQUENCY,
                    realtime_available=True,
                    lookahead_risk=False,
                    available_at="after_formal_close_15:00_Asia/Shanghai",
                    usages=("production", "training", "diagnostic"),
                    applicable_scope="project market-state carrier with trusted daily close",
                    disabled_boundaries=(
                        f"fewer than {window} completed daily observations",
                        "non-positive or missing close",
                    ),
                    evidence_status="computable_market_fact_not_strategy_signal",
                    feature_version=FEATURE_VERSION,
                    provenance={
                        "owner": "factor_lab.market_state",
                        "implementation": "factor_lab.market_state.attributes",
                    },
                    metadata={
                        "physical_attribute_id": definition.physical_attribute_id,
                        "attribute_family": definition.attribute_family,
                        "measurement_scale_id": scale_id,
                        "measurement_window_trading_days": window,
                    },
                )
            )
    return FeatureLibrary(tuple(specs))


def build_market_attribute_specs_1d() -> tuple[MarketAttributeSpec, ...]:
    """Project the A1 ontology from exact FeatureSpec references."""

    library = build_feature_library_1d()
    specs: list[MarketAttributeSpec] = []
    for definition in _DEFINITIONS:
        for scale_id in MEASUREMENT_SCALES:
            feature_id = _feature_id(definition.physical_attribute_id, scale_id)
            spec = MarketAttributeSpec(
                attribute_id=f"{definition.physical_attribute_id}_{scale_id}_1d",
                physical_attribute_id=definition.physical_attribute_id,
                feature_ref=FeatureSpecRef(feature_id, FEATURE_VERSION, BAR_FREQUENCY),
                attribute_family=definition.attribute_family,
                measurement_scale_id=scale_id,
                state_smoothing_scale_id=STATE_SMOOTHING_SCALE_ID,
                normalization_reference_id=NORMALIZATION_REFERENCE_ID,
                state_policy_version=STATE_POLICY_VERSION,
            )
            spec.resolve_feature(library)
            specs.append(spec)
    return tuple(specs)


def build_market_attribute_catalog() -> pd.DataFrame:
    """Materialize the catalog from FeatureSpec + MarketAttributeSpec authority."""

    records: list[dict[str, object]] = []
    for spec in build_market_attribute_specs_1d():
        records.append(
            {
                "attribute_id": spec.attribute_id,
                "physical_attribute_id": spec.physical_attribute_id,
                "attribute_family": spec.attribute_family,
                "feature_id": spec.feature_ref.feature_id,
                "feature_version": spec.feature_ref.feature_version,
                "bar_frequency": spec.feature_ref.frequency,
                "measurement_scale_id": spec.measurement_scale_id,
                "measurement_window_trading_days": MEASUREMENT_SCALES[
                    spec.measurement_scale_id
                ],
                "state_smoothing_scale_id": spec.state_smoothing_scale_id,
                "normalization_reference_id": spec.normalization_reference_id,
                "state_policy_version": spec.state_policy_version,
                "production_authority": False,
            }
        )
    return pd.DataFrame(records).sort_values(
        ["attribute_family", "physical_attribute_id", "measurement_window_trading_days"]
    ).reset_index(drop=True)


def compute_market_attributes_1d(
    daily_panel: pd.DataFrame,
    *,
    carrier_id: str = "cloudridge",
    carrier_definition_version: str = "cloudridge@1",
) -> pd.DataFrame:
    """Compute the A1 representative long-form attribute table.

    Every rolling computation is backward-looking and includes only the current
    completed daily close.  No normalization or state bucket is mixed into this
    factual layer.
    """

    frame = _normalize_daily_panel(daily_panel)
    close = frame["close"]
    log_return = np.log(close / close.shift(1))
    sign = np.sign(log_return).replace(0.0, np.nan)
    computations: dict[tuple[str, str], pd.Series] = {}
    for scale_id, window in MEASUREMENT_SCALES.items():
        up_share = (log_return > 0.0).rolling(window).mean()
        down_share = (log_return < 0.0).rolling(window).mean()
        path_abs = log_return.abs().rolling(window).sum()
        net = log_return.rolling(window).sum()
        volatility = log_return.rolling(window).std()
        valid_pair = sign.notna() & sign.shift(1).notna()
        switch = valid_pair & sign.ne(sign.shift(1))
        denominator = valid_pair.astype(float).rolling(window).sum()
        computations.update(
            {
                ("bdci", scale_id): 100.0
                * (
                    1.0
                    - switch.astype(float).rolling(window).sum()
                    / denominator.replace(0.0, np.nan)
                ),
                ("bci_imbalance", scale_id): up_share - down_share,
                ("wbi", scale_id): net / path_abs.replace(0.0, np.nan),
                ("path_efficiency", scale_id): net.abs()
                / path_abs.replace(0.0, np.nan),
                ("mean_abs_return", scale_id): log_return.abs().rolling(window).mean(),
                ("realized_volatility", scale_id): volatility,
                ("volatility_of_volatility", scale_id): volatility.rolling(window).std(),
                ("downside_semivolatility", scale_id): (
                    log_return.clip(upper=0.0).pow(2).rolling(window).mean().pow(0.5)
                ),
                ("upside_semivolatility", scale_id): (
                    log_return.clip(lower=0.0).pow(2).rolling(window).mean().pow(0.5)
                ),
                ("tail_energy_concentration", scale_id): log_return.pow(2)
                .rolling(window)
                .apply(_largest_energy_share, raw=True),
                ("lag1_autocorrelation", scale_id): log_return.rolling(window).corr(
                    log_return.shift(1)
                ),
            }
        )

    definition_by_id = {item.physical_attribute_id: item for item in _DEFINITIONS}
    records: list[pd.DataFrame] = []
    for spec in build_market_attribute_specs_1d():
        values = computations[(spec.physical_attribute_id, spec.measurement_scale_id)]
        raw_array = np.asarray(values, dtype=np.float64)
        definition = definition_by_id[spec.physical_attribute_id]
        records.append(
            pd.DataFrame(
                {
                    "carrier_id": carrier_id,
                    "carrier_definition_version": carrier_definition_version,
                    "bar_frequency": BAR_FREQUENCY,
                    "observation_time": frame["timestamp"],
                    "available_at": frame["timestamp"],
                    "feature_id": spec.feature_ref.feature_id,
                    "feature_version": spec.feature_ref.feature_version,
                    "physical_attribute_id": spec.physical_attribute_id,
                    "attribute_family": definition.attribute_family,
                    "measurement_scale_id": spec.measurement_scale_id,
                    "raw_value": raw_array,
                    "attribute_valid": np.isfinite(raw_array),
                }
            )
        )
    result = pd.concat(records, ignore_index=True)
    result = result.loc[:, ATTRIBUTE_OUTPUT_COLUMNS].sort_values(
        [
            "carrier_id",
            "carrier_definition_version",
            "bar_frequency",
            "feature_id",
            "measurement_scale_id",
            "observation_time",
        ],
        kind="mergesort",
    )
    logical_key = [
        "carrier_id",
        "carrier_definition_version",
        "bar_frequency",
        "observation_time",
        "feature_id",
        "feature_version",
        "measurement_scale_id",
    ]
    if result.duplicated(logical_key).any():
        raise ValidationError("market attribute logical key is not unique")
    return result.reset_index(drop=True)


def build_cloudridge_compatibility_view(attributes: pd.DataFrame) -> pd.DataFrame:
    """Return the deprecated legacy-width projection for overlapping formulas."""

    required = {
        "observation_time",
        "physical_attribute_id",
        "measurement_scale_id",
        "raw_value",
    }
    missing = required - set(attributes)
    if missing:
        raise ValidationError(f"attribute table missing fields: {sorted(missing)}")
    base_times = pd.Series(pd.unique(attributes["observation_time"])).sort_values()
    view = pd.DataFrame({"timestamp": base_times.reset_index(drop=True)})
    view["trading_day"] = pd.to_datetime(view["timestamp"]).dt.tz_localize(None).dt.normalize()
    for definition in _DEFINITIONS:
        if definition.legacy_column_prefix is None:
            continue
        for scale_id, window in MEASUREMENT_SCALES.items():
            rows = attributes.loc[
                (attributes["physical_attribute_id"] == definition.physical_attribute_id)
                & (attributes["measurement_scale_id"] == scale_id),
                ["observation_time", "raw_value"],
            ]
            column = f"{definition.legacy_column_prefix}_w{window}"
            mapping = rows.set_index("observation_time")["raw_value"]
            view[column] = view["timestamp"].map(mapping)
    view = cast(
        pd.DataFrame,
        view[
            [
                "trading_day",
                "timestamp",
                *[c for c in view if c not in {"trading_day", "timestamp"}],
            ]
        ],
    )
    view["timestamp"] = pd.to_datetime(view["timestamp"]).dt.tz_localize(None)
    view.attrs.update(
        {
            "deprecated": True,
            "replacement": "market_attribute_observation.parquet",
            "legacy_100d_policy": "legacy_100d is compatibility-only and is not slow_120d",
        }
    )
    return view


def assert_decision_time_available(
    observations: pd.DataFrame,
    decision_time: pd.Timestamp | str,
) -> None:
    """Fail closed when a consumer asks before any selected row is available."""

    if "available_at" not in observations or observations.empty:
        raise ValidationError("available_at observations are required")
    decision = _as_shanghai_timestamp(decision_time)
    latest_required = max(
        _as_shanghai_timestamp(value) for value in observations["available_at"]
    )
    if decision < latest_required:
        raise ValidationError(
            f"market-state observation is not available at decision time {decision.isoformat()}"
        )


def _normalize_daily_panel(daily_panel: pd.DataFrame) -> pd.DataFrame:
    required = {"trading_day", "timestamp", "close"}
    missing = required - set(daily_panel)
    if missing:
        raise ValidationError(f"daily_panel missing columns: {sorted(missing)}")
    frame = daily_panel.copy()
    frame["trading_day"] = pd.to_datetime(frame["trading_day"], errors="coerce")
    frame["timestamp"] = frame["timestamp"].map(_as_shanghai_timestamp)
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["trading_day", "timestamp", "close"])
    frame = frame.loc[frame["close"] > 0.0].sort_values(
        ["trading_day", "timestamp"], kind="mergesort"
    )
    frame = frame.drop_duplicates("trading_day", keep="last").reset_index(drop=True)
    if frame.empty:
        raise ValidationError("daily_panel has no valid rows")
    before_close = frame["timestamp"].map(
        lambda value: (value.hour, value.minute, value.second) < (15, 0, 0)
    )
    if bool(before_close.any()):
        raise ValidationError("daily observation timestamp is before formal close")
    return frame


def _as_shanghai_timestamp(value: object) -> pd.Timestamp:
    parsed = pd.Timestamp(str(value))
    if not isinstance(parsed, pd.Timestamp):
        raise ValidationError("timestamp is required")
    if parsed.tzinfo is None:
        return cast(pd.Timestamp, parsed.tz_localize(TIMEZONE))
    return cast(pd.Timestamp, parsed.tz_convert(TIMEZONE))


def _largest_energy_share(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return math.nan
    energy = finite * finite
    total = float(energy.sum())
    if total <= 0.0:
        return 0.0
    return float(energy.max() / total)


def _feature_id(physical_attribute_id: str, scale_id: str) -> str:
    return f"market_state.{physical_attribute_id}.{scale_id}.1d"


def _formula(physical_attribute_id: str, window: int) -> str:
    formulas = {
        "bdci": f"100 * (1 - direction_switch_rate(close_to_close_log_return, {window}d))",
        "bci_imbalance": f"mean(return > 0, {window}d) - mean(return < 0, {window}d)",
        "wbi": f"sum(log_return, {window}d) / sum(abs(log_return), {window}d)",
        "path_efficiency": f"abs(sum(log_return, {window}d)) / sum(abs(log_return), {window}d)",
        "mean_abs_return": f"mean(abs(log_return), {window}d)",
        "realized_volatility": f"sample_std(log_return, {window}d)",
        "volatility_of_volatility": f"sample_std(sample_std(log_return, {window}d), {window}d)",
        "downside_semivolatility": f"sqrt(mean(min(log_return, 0)^2, {window}d))",
        "upside_semivolatility": f"sqrt(mean(max(log_return, 0)^2, {window}d))",
        "tail_energy_concentration": f"max(log_return^2, {window}d) / sum(log_return^2, {window}d)",
        "lag1_autocorrelation": f"corr(log_return[t], log_return[t-1], {window}d)",
    }
    return formulas[physical_attribute_id]


__all__ = [
    "LEGACY_SCALE_LABELS",
    "MEASUREMENT_SCALES",
    "assert_decision_time_available",
    "build_cloudridge_compatibility_view",
    "build_feature_library_1d",
    "build_market_attribute_catalog",
    "build_market_attribute_specs_1d",
    "compute_market_attributes_1d",
]
