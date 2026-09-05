"""Complete A2 V1 causal market attributes.

This module extends the A1 representative slice without changing the A1 API.
Every measurement window is expressed in physical trading sessions through
``market_state.horizons``; formulas never assume a fixed bars-per-day count.
The current A2 online bundle remains 1d/60m.  C1.2 may use the same frozen
formulas on a governed 15m research supplement without changing A2 authority.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, cast

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.factor_engine.feature_library import FeatureLibrary, FeatureSpec
from factor_lab.market_state.attributes import (
    MEASUREMENT_SCALES,
    NORMALIZATION_REFERENCE_ID,
    STATE_POLICY_VERSION,
    STATE_SMOOTHING_SCALE_ID,
)
from factor_lab.market_state.contracts import FeatureSpecRef, MarketAttributeSpec
from factor_lab.market_state.horizons import (
    NormalizedBarPanel,
    apply_full_horizon,
    normalize_bar_panel,
    rolling_by_sessions,
)

FEATURE_VERSION: Final[str] = "2.0"
SUPPORTED_CURRENT_FREQUENCIES: Final[tuple[str, ...]] = ("1d", "60m")
SUPPORTED_ATTRIBUTE_FREQUENCIES: Final[tuple[str, ...]] = ("1d", "60m", "15m")


@dataclass(frozen=True, slots=True)
class AttributeDefinitionV1:
    physical_attribute_id: str
    chinese_name: str
    english_name: str
    attribute_family: str


ATTRIBUTE_DEFINITIONS_V1: Final[tuple[AttributeDefinitionV1, ...]] = (
    AttributeDefinitionV1("bdci", "方向连续度", "bar direction continuity", "direction"),
    AttributeDefinitionV1("bci_imbalance", "涨跌净偏斜", "bar color imbalance", "direction"),
    AttributeDefinitionV1("up_share", "上涨占比", "up-bar share", "direction"),
    AttributeDefinitionV1("down_share", "下跌占比", "down-bar share", "direction"),
    AttributeDefinitionV1("wbi", "幅度加权方向压力", "weighted bar imbalance", "direction"),
    AttributeDefinitionV1("direction_slope", "方向斜率", "log-price direction slope", "direction"),
    AttributeDefinitionV1("dii", "方向冲量", "directional impulse", "direction"),
    AttributeDefinitionV1("mean_abs_return", "平均绝对收益", "mean absolute return", "amplitude"),
    AttributeDefinitionV1("rolling_range", "滚动真实区间", "rolling high-low range", "amplitude"),
    AttributeDefinitionV1("body_to_true_range", "实体真实区间比", "body to true-range ratio", "amplitude"),
    AttributeDefinitionV1("dii_energy", "方向冲量能量", "directional impulse energy", "amplitude"),
    AttributeDefinitionV1("path_efficiency", "路径效率", "path efficiency", "path_geometry"),
    AttributeDefinitionV1("noise_ratio", "路径噪声比", "path noise ratio", "path_geometry"),
    AttributeDefinitionV1("sign_flip_rate", "方向翻转率", "return sign-flip rate", "path_geometry"),
    AttributeDefinitionV1("price_position", "区间价格位置", "rolling price position", "path_geometry"),
    AttributeDefinitionV1("drawdown", "滚动回撤", "rolling drawdown", "path_geometry"),
    AttributeDefinitionV1("realized_volatility", "实现波动", "realized volatility", "volatility"),
    AttributeDefinitionV1("volatility_of_volatility", "波动的波动", "volatility of volatility", "volatility"),
    AttributeDefinitionV1("fast_slow_volatility_ratio", "快慢波动比", "fast-slow volatility ratio", "volatility"),
    AttributeDefinitionV1("volatility_expansion", "波动扩张率", "volatility expansion", "volatility"),
    AttributeDefinitionV1("downside_semivolatility", "下行半波动", "downside semivolatility", "tail_asymmetry"),
    AttributeDefinitionV1("upside_semivolatility", "上行半波动", "upside semivolatility", "tail_asymmetry"),
    AttributeDefinitionV1("tail_energy_concentration", "尾部能量集中度", "tail energy concentration", "tail_asymmetry"),
    AttributeDefinitionV1("max_standardized_bar", "最大标准化单棒", "maximum standardized bar", "tail_asymmetry"),
    AttributeDefinitionV1("return_skewness", "收益偏度", "return skewness", "tail_asymmetry"),
    AttributeDefinitionV1("jrr", "跳变反转风险", "jump reversal risk", "tail_asymmetry"),
    AttributeDefinitionV1("lag1_autocorrelation", "一阶收益自相关", "lag-one return autocorrelation", "memory"),
    AttributeDefinitionV1("lag4_autocorrelation", "四阶收益自相关", "lag-four return autocorrelation", "memory"),
    AttributeDefinitionV1("variance_ratio_4", "四阶方差比", "four-lag variance ratio", "memory"),
    AttributeDefinitionV1("directional_run_age", "同向段年龄", "directional run age", "memory"),
    AttributeDefinitionV1("residence_fraction", "同向驻留占比", "directional residence fraction", "memory"),
    AttributeDefinitionV1("own_scale_activation", "本尺度激活", "own-scale activation", "scale_coupling"),
    AttributeDefinitionV1("neighbor_activation_ratio", "邻尺度激活比", "neighbor-scale activation ratio", "scale_coupling"),
    AttributeDefinitionV1("cross_scale_direction_agreement", "跨尺度方向一致", "cross-scale direction agreement", "scale_coupling"),
)

ATTRIBUTE_OUTPUT_COLUMNS_V1: Final[tuple[str, ...]] = (
    "carrier_id",
    "carrier_definition_version",
    "bar_frequency",
    "trading_day",
    "observation_time",
    "available_at",
    "bar_duration_minutes",
    "feature_id",
    "feature_version",
    "physical_attribute_id",
    "attribute_family",
    "measurement_scale_id",
    "raw_value",
    "attribute_valid",
)


def build_feature_library_v1(
    *, frequencies: tuple[str, ...] = SUPPORTED_CURRENT_FREQUENCIES
) -> FeatureLibrary:
    specs: list[FeatureSpec] = []
    for frequency in frequencies:
        _require_frequency(frequency)
        for definition in ATTRIBUTE_DEFINITIONS_V1:
            for scale_id, window in MEASUREMENT_SCALES.items():
                specs.append(
                    FeatureSpec(
                        feature_id=_feature_id(
                            definition.physical_attribute_id, scale_id, frequency
                        ),
                        chinese_name=f"{window}交易日{definition.chinese_name}",
                        english_name=f"{window}-session {definition.english_name}",
                        formula=_formula(definition.physical_attribute_id, window),
                        data_sources=(f"datahub:cloudridge:{frequency}:ohlc",),
                        frequency=frequency,
                        realtime_available=True,
                        lookahead_risk=False,
                        available_at="at_completed_bar_timestamp_Asia/Shanghai",
                        usages=("production", "training", "diagnostic"),
                        applicable_scope=(
                            "project market-state carrier with trusted completed OHLC bars"
                        ),
                        disabled_boundaries=(
                            f"fewer than {window} observed trading sessions",
                            "non-positive or missing OHLC",
                        ),
                        evidence_status="computable_market_fact_not_strategy_signal",
                        feature_version=FEATURE_VERSION,
                        provenance={
                            "owner": "factor_lab.market_state",
                            "implementation": "factor_lab.market_state.attributes_v1",
                        },
                        metadata={
                            "physical_attribute_id": definition.physical_attribute_id,
                            "attribute_family": definition.attribute_family,
                            "measurement_scale_id": scale_id,
                            "measurement_window_trading_days": window,
                            "bars_per_day_assumption": None,
                        },
                    )
                )
    return FeatureLibrary(tuple(specs))


def build_market_attribute_specs_v1(
    *, frequencies: tuple[str, ...] = SUPPORTED_CURRENT_FREQUENCIES
) -> tuple[MarketAttributeSpec, ...]:
    library = build_feature_library_v1(frequencies=frequencies)
    result: list[MarketAttributeSpec] = []
    for frequency in frequencies:
        for definition in ATTRIBUTE_DEFINITIONS_V1:
            for scale_id in MEASUREMENT_SCALES:
                item = MarketAttributeSpec(
                    attribute_id=(
                        f"{definition.physical_attribute_id}_{scale_id}_{frequency}"
                    ),
                    physical_attribute_id=definition.physical_attribute_id,
                    feature_ref=FeatureSpecRef(
                        _feature_id(
                            definition.physical_attribute_id, scale_id, frequency
                        ),
                        FEATURE_VERSION,
                        frequency,
                    ),
                    attribute_family=definition.attribute_family,
                    measurement_scale_id=scale_id,
                    state_smoothing_scale_id=STATE_SMOOTHING_SCALE_ID,
                    normalization_reference_id=NORMALIZATION_REFERENCE_ID,
                    state_policy_version=STATE_POLICY_VERSION,
                )
                item.resolve_feature(library)
                result.append(item)
    return tuple(result)


def build_market_attribute_catalog_v1(
    *, frequencies: tuple[str, ...] = SUPPORTED_CURRENT_FREQUENCIES
) -> pd.DataFrame:
    rows = []
    for spec in build_market_attribute_specs_v1(frequencies=frequencies):
        rows.append(
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
    return pd.DataFrame(rows).sort_values(
        ["bar_frequency", "attribute_family", "physical_attribute_id", "measurement_window_trading_days"],
        kind="mergesort",
    ).reset_index(drop=True)


def compute_market_attributes_v1(
    panel: pd.DataFrame,
    *,
    frequency: str,
    carrier_id: str = "cloudridge",
    carrier_definition_version: str = "cloudridge@1",
) -> pd.DataFrame:
    """Compute the complete V1 factual layer for one completed-bar frequency."""

    normalized = normalize_bar_panel(panel, frequency=frequency)
    frame = normalized.frame
    close = cast(pd.Series, frame["close"]).astype(float)
    open_ = cast(pd.Series, frame["open"]).astype(float)
    high = cast(pd.Series, frame["high"]).astype(float)
    low = cast(pd.Series, frame["low"]).astype(float)
    log_close = pd.Series(
        np.log(close.to_numpy(dtype=float)), index=close.index, dtype=float
    )
    log_return = log_close.diff()
    sign = pd.Series(
        np.sign(log_return.to_numpy(dtype=float)), index=log_return.index, dtype=float
    ).replace(0.0, np.nan)
    true_range = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    body_ratio = (close - open_).abs() / true_range.replace(0.0, np.nan)
    run_age = _directional_run_age(sign)
    computations: dict[tuple[str, str], pd.Series] = {}

    for scale_id, window in MEASUREMENT_SCALES.items():
        rolling_return = rolling_by_sessions(
            log_return, normalized, window_sessions=window
        )
        rolling_abs = rolling_by_sessions(
            log_return.abs(), normalized, window_sessions=window
        )
        rolling_close = rolling_by_sessions(close, normalized, window_sessions=window)
        rolling_high = rolling_by_sessions(high, normalized, window_sessions=window)
        rolling_low = rolling_by_sessions(low, normalized, window_sessions=window)
        up_share = rolling_by_sessions(
            (log_return > 0.0).astype(float), normalized, window_sessions=window
        ).mean()
        down_share = rolling_by_sessions(
            (log_return < 0.0).astype(float), normalized, window_sessions=window
        ).mean()
        path_abs = rolling_abs.sum()
        net = rolling_return.sum()
        volatility = rolling_return.std(ddof=1)
        energy = rolling_by_sessions(
            log_return.pow(2), normalized, window_sessions=window
        ).sum()
        valid_pair = sign.notna() & sign.shift(1).notna()
        switches = valid_pair & sign.ne(sign.shift(1))
        switch_count = rolling_by_sessions(
            switches.astype(float), normalized, window_sessions=window
        ).sum()
        pair_count = rolling_by_sessions(
            valid_pair.astype(float), normalized, window_sessions=window
        ).sum()
        path_efficiency = net.abs() / path_abs.replace(0.0, np.nan)
        short_window = max(2, window // 3)
        short_vol = rolling_by_sessions(
            log_return, normalized, window_sessions=short_window
        ).std(ddof=1)
        prior_vol = volatility.shift(1)
        abrupt = log_return.shift(1).abs() > prior_vol.shift(1).fillna(np.inf)
        reversal = sign.ne(sign.shift(1)) & (
            log_return.abs() >= 0.5 * log_return.shift(1).abs()
        )
        jrr_event = (abrupt & reversal).astype(float)
        rolling_max = rolling_high.max()
        rolling_min = rolling_low.min()
        base: dict[str, pd.Series] = {
            "bdci": 100.0 * (1.0 - switch_count / pair_count.replace(0.0, np.nan)),
            "bci_imbalance": up_share - down_share,
            "up_share": up_share,
            "down_share": down_share,
            "wbi": net / path_abs.replace(0.0, np.nan),
            "direction_slope": rolling_by_sessions(
                log_close, normalized, window_sessions=window
            ).apply(_endpoint_slope, raw=True),
            "dii": (net / energy.pow(0.5).replace(0.0, np.nan))
            * (0.5 + 0.5 * path_efficiency),
            "mean_abs_return": rolling_abs.mean(),
            "rolling_range": np.log(
                rolling_max / rolling_min.replace(0.0, np.nan)
            ),
            "body_to_true_range": rolling_by_sessions(
                body_ratio, normalized, window_sessions=window
            ).mean(),
            "dii_energy": energy,
            "path_efficiency": path_efficiency,
            "noise_ratio": 1.0 - path_efficiency,
            "sign_flip_rate": switch_count / pair_count.replace(0.0, np.nan),
            "price_position": (close - rolling_min)
            / (rolling_max - rolling_min).replace(0.0, np.nan),
            "drawdown": close / rolling_close.max().replace(0.0, np.nan) - 1.0,
            "realized_volatility": volatility,
            "volatility_of_volatility": rolling_by_sessions(
                volatility, normalized, window_sessions=window
            ).std(ddof=1),
            "fast_slow_volatility_ratio": short_vol
            / volatility.replace(0.0, np.nan),
            "volatility_expansion": short_vol
            / volatility.replace(0.0, np.nan)
            - 1.0,
            "downside_semivolatility": rolling_by_sessions(
                log_return.clip(upper=0.0).pow(2),
                normalized,
                window_sessions=window,
            ).mean().pow(0.5),
            "upside_semivolatility": rolling_by_sessions(
                log_return.clip(lower=0.0).pow(2),
                normalized,
                window_sessions=window,
            ).mean().pow(0.5),
            "tail_energy_concentration": rolling_by_sessions(
                log_return.pow(2), normalized, window_sessions=window
            ).apply(_largest_share, raw=True),
            "max_standardized_bar": rolling_abs.max()
            / volatility.replace(0.0, np.nan),
            "return_skewness": rolling_return.skew(),
            "jrr": rolling_by_sessions(
                jrr_event, normalized, window_sessions=window
            ).mean(),
            "lag1_autocorrelation": rolling_return.corr(log_return.shift(1)),
            "lag4_autocorrelation": rolling_return.corr(log_return.shift(4)),
            "variance_ratio_4": rolling_return.apply(_variance_ratio_four, raw=True),
            "directional_run_age": run_age,
            "residence_fraction": run_age / float(window),
        }
        for physical_id, values in base.items():
            required_window = 2 * window if physical_id == "volatility_of_volatility" else window
            computations[(physical_id, scale_id)] = apply_full_horizon(
                values,
                normalized,
                window_sessions=required_window,
            )

    _add_scale_coupling(computations, normalized)
    definition_by_id = {
        definition.physical_attribute_id: definition
        for definition in ATTRIBUTE_DEFINITIONS_V1
    }
    records: list[pd.DataFrame] = []
    for spec in build_market_attribute_specs_v1(frequencies=(frequency,)):
        values = computations[(spec.physical_attribute_id, spec.measurement_scale_id)]
        raw = np.asarray(values, dtype=np.float64)
        definition = definition_by_id[spec.physical_attribute_id]
        records.append(
            pd.DataFrame(
                {
                    "carrier_id": carrier_id,
                    "carrier_definition_version": carrier_definition_version,
                    "bar_frequency": frequency,
                    "trading_day": frame["trading_day"],
                    "observation_time": frame["timestamp"],
                    "available_at": frame["available_at"],
                    "bar_duration_minutes": frame["bar_duration_minutes"],
                    "feature_id": spec.feature_ref.feature_id,
                    "feature_version": spec.feature_ref.feature_version,
                    "physical_attribute_id": spec.physical_attribute_id,
                    "attribute_family": definition.attribute_family,
                    "measurement_scale_id": spec.measurement_scale_id,
                    "raw_value": raw,
                    "attribute_valid": np.isfinite(raw),
                }
            )
        )
    result = pd.concat(records, ignore_index=True).loc[:, ATTRIBUTE_OUTPUT_COLUMNS_V1]
    result = result.sort_values(
        [
            "carrier_id",
            "carrier_definition_version",
            "bar_frequency",
            "feature_id",
            "measurement_scale_id",
            "observation_time",
        ],
        kind="mergesort",
    ).reset_index(drop=True)
    logical_key = [
        "carrier_id",
        "carrier_definition_version",
        "bar_frequency",
        "observation_time",
        "feature_id",
        "feature_version",
        "measurement_scale_id",
    ]
    if bool(result.duplicated(logical_key).any()):
        raise ValidationError("market attribute V1 logical key is not unique")
    return result


def _add_scale_coupling(
    computations: dict[tuple[str, str], pd.Series],
    normalized: NormalizedBarPanel,
) -> None:
    scales = list(MEASUREMENT_SCALES)
    rv = {
        scale: computations[("realized_volatility", scale)] for scale in scales
    }
    direction = {scale: computations[("wbi", scale)] for scale in scales}
    structural_window = 252
    for index, scale in enumerate(scales):
        historical_median = rolling_by_sessions(
            cast(pd.Series, rv[scale].shift(1)),
            normalized,
            window_sessions=structural_window,
        ).median()
        own = rv[scale] / historical_median.replace(0.0, np.nan)
        computations[("own_scale_activation", scale)] = apply_full_horizon(
            own, normalized, window_sessions=structural_window
        )
        neighbor = scales[index + 1] if index + 1 < len(scales) else scales[index - 1]
        ratio = rv[scale] / rv[neighbor].replace(0.0, np.nan)
        computations[("neighbor_activation_ratio", scale)] = apply_full_horizon(
            ratio,
            normalized,
            window_sessions=max(MEASUREMENT_SCALES[scale], MEASUREMENT_SCALES[neighbor]),
        )
        agreement = pd.Series(
            (
                np.sign(direction[scale].to_numpy(dtype=float))
                == np.sign(direction[neighbor].to_numpy(dtype=float))
            ).astype(float),
            index=direction[scale].index,
            dtype=float,
        )
        agreement = agreement.where(direction[scale].notna() & direction[neighbor].notna())
        computations[("cross_scale_direction_agreement", scale)] = apply_full_horizon(
            agreement,
            normalized,
            window_sessions=max(MEASUREMENT_SCALES[scale], MEASUREMENT_SCALES[neighbor]),
        )


def _directional_run_age(sign: pd.Series) -> pd.Series:
    values = np.asarray(sign, dtype=np.float64)
    ages = np.full(len(values), np.nan, dtype=np.float64)
    age = 0
    previous = math.nan
    for index, value in enumerate(values):
        if not math.isfinite(value):
            age = 0
            previous = math.nan
            continue
        age = age + 1 if value == previous else 1
        ages[index] = float(age)
        previous = value
    return pd.Series(ages, index=sign.index, dtype=float)


def _endpoint_slope(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if finite.size < 2:
        return math.nan
    return float((finite[-1] - finite[0]) / (finite.size - 1))


def _largest_share(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return math.nan
    total = float(finite.sum())
    return 0.0 if total <= 0.0 else float(finite.max() / total)


def _variance_ratio_four(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if finite.size < 8:
        return math.nan
    one = float(np.var(finite, ddof=1))
    if one <= 0.0:
        return 0.0
    four = np.convolve(finite, np.ones(4, dtype=float), mode="valid")
    return float(np.var(four, ddof=1) / (4.0 * one)) if four.size > 1 else math.nan


def _feature_id(physical_id: str, scale_id: str, frequency: str) -> str:
    return f"market_state.{physical_id}.{scale_id}.{frequency}"


def _require_frequency(frequency: str) -> None:
    if frequency not in SUPPORTED_ATTRIBUTE_FREQUENCIES:
        raise ValidationError(
            f"market-state attributes do not support frequency: {frequency}"
        )


def _formula(physical_id: str, window: int) -> str:
    common = f"over latest {window} observed trading sessions"
    formulas = {
        "bdci": f"100 * (1 - close-return sign-switch rate) {common}",
        "bci_imbalance": f"mean(r>0)-mean(r<0) {common}",
        "up_share": f"mean(r>0) {common}",
        "down_share": f"mean(r<0) {common}",
        "wbi": f"sum(r)/sum(abs(r)) {common}",
        "direction_slope": f"endpoint slope of log(close) {common}",
        "dii": f"sum(r)/sqrt(sum(r^2)) * (0.5+0.5*path_efficiency) {common}",
        "mean_abs_return": f"mean(abs(r)) {common}",
        "rolling_range": f"log(max(high)/min(low)) {common}",
        "body_to_true_range": f"mean(abs(close-open)/true_range) {common}",
        "dii_energy": f"sum(r^2) {common}",
        "path_efficiency": f"abs(sum(r))/sum(abs(r)) {common}",
        "noise_ratio": f"1-path_efficiency {common}",
        "sign_flip_rate": f"close-return sign-switch rate {common}",
        "price_position": f"(close-min(low))/(max(high)-min(low)) {common}",
        "drawdown": f"close/max(close)-1 {common}",
        "realized_volatility": f"sample_std(r) {common}",
        "volatility_of_volatility": f"sample_std(realized_volatility) {common}",
        "fast_slow_volatility_ratio": f"std(r,{max(2, window // 3)}d)/std(r,{window}d)",
        "volatility_expansion": f"std(r,{max(2, window // 3)}d)/std(r,{window}d)-1",
        "downside_semivolatility": f"sqrt(mean(min(r,0)^2)) {common}",
        "upside_semivolatility": f"sqrt(mean(max(r,0)^2)) {common}",
        "tail_energy_concentration": f"max(r^2)/sum(r^2) {common}",
        "max_standardized_bar": f"max(abs(r))/std(r) {common}",
        "return_skewness": f"skew(r) {common}",
        "jrr": f"mean(prior-volatility-scaled no-buffer reversal event) {common}",
        "lag1_autocorrelation": f"corr(r[t],r[t-1]) {common}",
        "lag4_autocorrelation": f"corr(r[t],r[t-4]) {common}",
        "variance_ratio_4": f"var(sum_4(r))/(4*var(r)) {common}",
        "directional_run_age": "current consecutive close-return sign age",
        "residence_fraction": f"directional_run_age/{window}",
        "own_scale_activation": "current scale volatility / prior 252-session median",
        "neighbor_activation_ratio": "current scale volatility / adjacent scale volatility",
        "cross_scale_direction_agreement": "indicator(sign(WBI_current)==sign(WBI_adjacent))",
    }
    return formulas[physical_id]


__all__ = [
    "ATTRIBUTE_DEFINITIONS_V1",
    "FEATURE_VERSION",
    "SUPPORTED_ATTRIBUTE_FREQUENCIES",
    "SUPPORTED_CURRENT_FREQUENCIES",
    "build_feature_library_v1",
    "build_market_attribute_catalog_v1",
    "build_market_attribute_specs_v1",
    "compute_market_attributes_v1",
]
