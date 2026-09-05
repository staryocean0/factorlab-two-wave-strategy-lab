# pyright: reportAny=false, reportArgumentType=false
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
# pyright: reportIndexIssue=false, reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownLambdaType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""FeatureSpec and MarketAttributeSpec authority for group correlations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.factor_engine.feature_library import FeatureLibrary, FeatureSpec
from factor_lab.market_state.contracts import FeatureSpecRef, MarketAttributeSpec

FEATURE_VERSION: Final[str] = "1.0"
BAR_FREQUENCY: Final[str] = "1d"
WINDOWS: Final[tuple[int, ...]] = (20, 60, 120)
SUPPORTED_UNIVERSES: Final[dict[str, dict[str, object]]] = {
    "cn_a_all_market": {
        "chinese_name": "全市场",
        "pit_grade": "strict_market_pit",
        "lookahead_risk": False,
    },
    "cn_a_manufacturing_core_v1": {
        "chinese_name": "制造业核心池",
        "pit_grade": "index_construction_only",
        "lookahead_risk": True,
    },
}


@dataclass(frozen=True, slots=True)
class _MetricDefinition:
    metric_id: str
    chinese_name: str
    english_name: str
    formula: str


METRICS: Final[tuple[_MetricDefinition, ...]] = (
    _MetricDefinition(
        "group_corr_level",
        "群体同步水平",
        "group correlation level",
        "tanh(mean_{i<j}(arctanh(clip(corr(r_i,r_j),-0.999999,0.999999))))",
    ),
    _MetricDefinition(
        "group_corr_dispersion",
        "群体同步离散度",
        "group correlation dispersion",
        "IQR_i(mean_j(arctanh(clip(corr(r_i,r_j),-0.999999,0.999999))))",
    ),
    _MetricDefinition(
        "group_common_mode_share",
        "共同模式占比",
        "group common-mode share",
        "largest_eigenvalue(standardized_return_gram_psd)/sum_eigenvalues",
    ),
)


def feature_id(universe_id: str, metric_id: str, window: int) -> str:
    return f"market_group_corr_{universe_id}_{metric_id}_{window}d"


def build_group_correlation_feature_library(
    *,
    universe_ids: tuple[str, ...] = ("cn_a_all_market",),
) -> FeatureLibrary:
    specs: list[FeatureSpec] = []
    for universe_id in universe_ids:
        universe = SUPPORTED_UNIVERSES.get(universe_id)
        if universe is None:
            raise ValidationError(f"unsupported group-correlation universe: {universe_id}")
        for metric in METRICS:
            for window in WINDOWS:
                specs.append(
                    FeatureSpec(
                        feature_id=feature_id(universe_id, metric.metric_id, window),
                        chinese_name=f"{universe['chinese_name']}{window}日{metric.chinese_name}",
                        english_name=(
                            f"{universe_id} {window}-day {metric.english_name}"
                        ),
                        formula=metric.formula,
                        data_sources=(
                            f"group-correlation:{universe_id}:1d:qfq_canonical",
                        ),
                        frequency=BAR_FREQUENCY,
                        realtime_available=True,
                        lookahead_risk=bool(universe["lookahead_risk"]),
                        available_at="after_formal_close_15:30_Asia/Shanghai; actionable_next_trading_point",
                        usages=("training", "diagnostic"),
                        applicable_scope=(
                            "aggregate market-state measurement; not a single-stock signal "
                            "and not an effectiveness claim"
                        ),
                        disabled_boundaries=(
                            f"fewer than {window} completed daily return observations",
                            "fewer than two eligible group members",
                            "source or universe version is not pinned",
                        ),
                        evidence_status="computable_market_measurement_no_effectiveness_claim",
                        feature_version=FEATURE_VERSION,
                        provenance={
                            "owner": "factor_lab.market_correlation",
                            "implementation": (
                                "factor_lab.market_correlation.services."
                                "group_correlation_timeseries_service"
                            ),
                        },
                        metadata={
                            "universe_id": universe_id,
                            "pit_grade": universe["pit_grade"],
                            "physical_attribute_id": metric.metric_id,
                            "measurement_scale_id": f"{window}d",
                            "measurement_window_trading_days": window,
                            "production_authority": False,
                            "factor_lifecycle_mutation": False,
                            "single_stock_authorized": False,
                            "measurement_registration": True,
                            "strategy_effectiveness_claim": False,
                        },
                    )
                )
    return FeatureLibrary(tuple(specs))


def build_group_correlation_attribute_specs(
    *,
    universe_ids: tuple[str, ...] = ("cn_a_all_market",),
) -> tuple[MarketAttributeSpec, ...]:
    library = build_group_correlation_feature_library(universe_ids=universe_ids)
    result: list[MarketAttributeSpec] = []
    for universe_id in universe_ids:
        for metric in METRICS:
            for window in WINDOWS:
                item = MarketAttributeSpec(
                    attribute_id=f"{universe_id}_{metric.metric_id}_{window}d_1d",
                    physical_attribute_id=metric.metric_id,
                    feature_ref=FeatureSpecRef(
                        feature_id(universe_id, metric.metric_id, window),
                        FEATURE_VERSION,
                        BAR_FREQUENCY,
                    ),
                    attribute_family="cross_sectional_group_structure",
                    measurement_scale_id=f"{window}d",
                    state_smoothing_scale_id="none_raw_group_panel",
                    normalization_reference_id="universe_window_native",
                    state_policy_version="research_only_no_route_v1",
                )
                _ = item.resolve_feature(library)
                result.append(item)
    return tuple(result)


def build_group_correlation_attribute_catalog(
    *, universe_ids: tuple[str, ...] = ("cn_a_all_market",)
) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for item in build_group_correlation_attribute_specs(universe_ids=universe_ids):
        spec = item.resolve_feature(
            build_group_correlation_feature_library(universe_ids=universe_ids)
        )
        records.append(
            {
                **item.to_dict(),
                "universe_id": spec.metadata["universe_id"],
                "pit_grade": spec.metadata["pit_grade"],
                "lookahead_risk": spec.lookahead_risk,
                "production_authority": False,
                "factor_lifecycle_mutation": False,
                "single_stock_authorized": False,
                "measurement_registration": True,
                "strategy_effectiveness_claim": False,
            }
        )
    return pd.DataFrame(records).sort_values(
        ["universe_id", "physical_attribute_id", "measurement_scale_id"]
    ).reset_index(drop=True)


def materialize_group_correlation_market_attributes(
    observations: pd.DataFrame,
) -> pd.DataFrame:
    required = {
        "universe_id",
        "universe_version",
        "observation_time",
        "available_at",
        "actionable_from",
        "lookback_window",
        "metric_id",
        "raw_value",
    }
    missing = required - set(observations.columns)
    if missing:
        raise ValidationError(f"group observations missing columns: {sorted(missing)}")
    result = observations.copy()
    result["carrier_id"] = result["universe_id"]
    result["carrier_definition_version"] = result["universe_version"]
    result["bar_frequency"] = BAR_FREQUENCY
    result["feature_id"] = result.apply(
        lambda row: feature_id(
            str(row["universe_id"]),
            str(row["metric_id"]),
            int(row["lookback_window"]),
        ),
        axis=1,
    )
    result["feature_version"] = FEATURE_VERSION
    result["physical_attribute_id"] = result["metric_id"]
    result["attribute_family"] = "cross_sectional_group_structure"
    result["measurement_scale_id"] = result["lookback_window"].map(
        lambda value: f"{int(value)}d"
    )
    result["attribute_valid"] = pd.to_numeric(
        result["raw_value"], errors="coerce"
    ).notna()
    result["production_authority"] = False
    result["factor_lifecycle_mutation"] = False
    result["measurement_registration"] = True
    result["strategy_effectiveness_claim"] = False
    return result


__all__ = [
    "BAR_FREQUENCY",
    "FEATURE_VERSION",
    "METRICS",
    "SUPPORTED_UNIVERSES",
    "WINDOWS",
    "build_group_correlation_attribute_catalog",
    "build_group_correlation_attribute_specs",
    "build_group_correlation_feature_library",
    "feature_id",
    "materialize_group_correlation_market_attributes",
]
