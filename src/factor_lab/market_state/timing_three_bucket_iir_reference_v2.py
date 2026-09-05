"""Market-field-conditioned V2 of the three-bucket IIR reference sample.

V2 keeps every V1 specialist, priority, account rule, and the proven V1
P13/P36 ownership state.  It adds one conservative same-tool P36 ownership
state derived from the generic multiscale market field.  The new state is a
supplement (logical OR), never a veto of the frozen V1 owner.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Final, cast

import pandas as pd

from factor_lab.market_state.research.causal_filter_iir_p13_slow_ownership_regime_v3 import (
    build_context as build_dynamic_iir_context,
)
from factor_lab.market_state.timing_three_bucket_iir_reference_v1 import (
    BUCKET_PRIORITY,
    FROZEN_REBOUND_ARTIFACT_SHA256,
    TimingThreeBucketIIRReferenceSpec,
    aggregate_account_metrics,
    align_strictly_prior_60m_desired_to_15m,
    build_three_bucket_iir_reference,
    compose_three_bucket_iir_reference,
)

SCHEMA_ID: Final[str] = "market_state_timing_three_bucket_iir_reference@2.0"
REFERENCE_VERSION: Final[str] = "timing_three_bucket_iir_reference_v2"
MARKET_FIELD_VERSION: Final[str] = "timing_multiscale_market_field_v1"


@dataclass(frozen=True, slots=True)
class TimingMarketFieldIIRSupplementSpec:
    """Frozen low-capacity field-to-P36 ownership rule."""

    reference_history_days: int = 625
    reference_minimum_days: int = 312
    variance_ratio_scale_days: float = 4.0
    variance_ratio_quantile: float = 0.80
    path_efficiency_scale_days: float = 8.0
    path_efficiency_quantile: float = 0.50
    highpass_cutoff_days: float = 4.0
    highpass_power_heat_maximum: float = 1.0
    review_clock: str = "calendar_month_end"

    def __post_init__(self) -> None:
        if self.reference_history_days < 250:
            raise ValueError("reference history must be at least 250 trading days")
        if not 1 <= self.reference_minimum_days <= self.reference_history_days:
            raise ValueError("reference minimum must lie inside the history window")
        if not 0.5 < self.variance_ratio_quantile < 1.0:
            raise ValueError("variance-ratio quantile must lie in (0.5, 1)")
        if not 0.0 < self.path_efficiency_quantile < 1.0:
            raise ValueError("path-efficiency quantile must lie in (0, 1)")
        if self.review_clock != "calendar_month_end":
            raise ValueError("V2 only supports calendar-month-end review")


FIELD_LABELS_ZH: Final[dict[str, str]] = {
    "v1_combo_t1_position": "V1三桶加动态IIR真实T+1基准仓位",
    "v1_p36_owner_active": "V1原生P36所有权状态",
    "market_field_p36_supplement_active": "场谱补充P36所有权状态",
    "combined_p36_owner_active": "V2合并P36所有权状态",
    "dynamic_iir_desired_position": "V2动态IIR严格先验目标仓位",
    "dynamic_iir_t1_position": "V2纯动态IIR真实T+1仓位",
    "combo_desired_position": "V2三桶加动态IIR组合目标仓位",
    "combo_t1_position": "V2三桶加动态IIR真实T+1仓位",
    "reference_version": "基础设施样板版本",
    "runtime_uses_future": "运行时是否使用未来数据",
    "research_authority": "研究样板权限",
    "production_authority": "生产权限",
}

REQUIRED_DAILY_FIELD_COLUMNS: Final[tuple[str, ...]] = (
    "trading_day",
    "decision_eligible_date",
    "scale_variance_ratio_d4",
    "scale_path_efficiency_d8",
    "cumulative_highpass_power_heat_d4",
)


def build_market_field_p36_supplement(
    daily_field: pd.DataFrame,
    *,
    spec: TimingMarketFieldIIRSupplementSpec = TimingMarketFieldIIRSupplementSpec(),
) -> pd.DataFrame:
    """Build a causal daily P36 supplement from the generic market field.

    Rows describe completed ``trading_day`` observations.  Ownership becomes
    eligible only at ``decision_eligible_date``.  Historical quantiles exclude
    the current row and the state is reviewed only on the last completed
    trading day of each calendar month.
    """

    missing = sorted(set(REQUIRED_DAILY_FIELD_COLUMNS).difference(daily_field.columns))
    if missing:
        raise KeyError(f"market field daily input is missing columns: {missing}")
    frame = daily_field.loc[:, REQUIRED_DAILY_FIELD_COLUMNS].copy()
    frame["trading_day"] = pd.to_datetime(frame["trading_day"], errors="raise")
    frame["decision_eligible_date"] = pd.to_datetime(frame["decision_eligible_date"], errors="raise")
    frame = frame.sort_values("trading_day").reset_index(drop=True)
    if frame["trading_day"].duplicated().any():
        raise ValueError("market field must have exactly one row per trading day")
    if frame["decision_eligible_date"].duplicated().any():
        raise ValueError("market field decision-eligible dates must be unique")
    if bool(frame["decision_eligible_date"].le(frame["trading_day"]).any()):
        raise ValueError("market field values must become eligible after trading_day")

    variance_ratio = cast(
        pd.Series,
        pd.to_numeric(frame["scale_variance_ratio_d4"], errors="raise"),
    )
    path_efficiency = cast(
        pd.Series,
        pd.to_numeric(frame["scale_path_efficiency_d8"], errors="raise"),
    )
    highpass_heat = cast(
        pd.Series,
        pd.to_numeric(frame["cumulative_highpass_power_heat_d4"], errors="raise"),
    )
    variance_cut = (
        variance_ratio.shift(1)
        .rolling(
            spec.reference_history_days,
            min_periods=spec.reference_minimum_days,
        )
        .quantile(spec.variance_ratio_quantile)
    )
    path_cut = (
        path_efficiency.shift(1)
        .rolling(
            spec.reference_history_days,
            min_periods=spec.reference_minimum_days,
        )
        .quantile(spec.path_efficiency_quantile)
    )
    evidence = variance_ratio.ge(variance_cut) & path_efficiency.ge(path_cut) & highpass_heat.le(spec.highpass_power_heat_maximum)
    review = frame.groupby(frame["trading_day"].dt.to_period("M")).tail(1).index
    review_evidence = pd.Series(False, index=frame.index, dtype=bool)
    review_evidence.loc[review] = evidence.loc[review].to_numpy(bool)
    review_state = pd.Series(pd.NA, index=frame.index, dtype="boolean")
    review_state.loc[review] = review_evidence.loc[review].astype("boolean")
    owner_state = review_state.ffill().fillna(False).astype(bool)

    return pd.DataFrame(
        {
            "trading_day": frame["trading_day"],
            "decision_eligible_date": frame["decision_eligible_date"],
            "scale_variance_ratio_d4": variance_ratio,
            "scale_variance_ratio_d4_cut": variance_cut,
            "scale_path_efficiency_d8": path_efficiency,
            "scale_path_efficiency_d8_cut": path_cut,
            "cumulative_highpass_power_heat_d4": highpass_heat,
            "daily_supplement_evidence": evidence,
            "month_end_review": frame.index.isin(review),
            "market_field_p36_supplement_active": owner_state,
        }
    )


def expand_daily_supplement_to_60m(
    supplement_daily: pd.DataFrame,
    bar_index: pd.DatetimeIndex,
) -> pd.Series:
    """Expose each month-end field decision on its eligible trading day."""

    if bar_index.has_duplicates or not bar_index.is_monotonic_increasing:
        raise ValueError("60m execution index must be unique and ordered")
    owner = pd.Series(
        supplement_daily["market_field_p36_supplement_active"].to_numpy(bool),
        index=pd.DatetimeIndex(supplement_daily["decision_eligible_date"]),
        dtype=bool,
    )
    normalized_index = pd.DatetimeIndex(
        [cast(pd.Timestamp, pd.Timestamp(value)).normalize() for value in bar_index]
    )
    expanded = owner.reindex(normalized_index).astype("boolean").fillna(False)
    return pd.Series(
        expanded.to_numpy(bool),
        index=bar_index,
        dtype=bool,
        name="market_field_p36_supplement_active",
    )


def build_three_bucket_iir_reference_v2(
    causal_15m_ohlc: pd.DataFrame,
    causal_60m_ohlc: pd.DataFrame,
    market_field_daily: pd.DataFrame,
    *,
    frozen_crash_rebound_executable: pd.Series,
    rebound_breadth_by_completed_bar: pd.Series,
    allowed_end_exclusive: pd.Timestamp,
    account_spec: TimingThreeBucketIIRReferenceSpec = TimingThreeBucketIIRReferenceSpec(),
    field_spec: TimingMarketFieldIIRSupplementSpec = TimingMarketFieldIIRSupplementSpec(),
) -> pd.DataFrame:
    """Build V2 while preserving the complete V1 specialist/account policy."""

    v1 = build_three_bucket_iir_reference(
        causal_15m_ohlc,
        causal_60m_ohlc,
        frozen_crash_rebound_executable=frozen_crash_rebound_executable,
        rebound_breadth_by_completed_bar=rebound_breadth_by_completed_bar,
        allowed_end_exclusive=allowed_end_exclusive,
        spec=account_spec,
    )
    panel60, _, _, route60 = build_dynamic_iir_context(
        causal_60m_ohlc,
        allowed_end=allowed_end_exclusive,
    )
    supplement_daily = build_market_field_p36_supplement(
        market_field_daily,
        spec=field_spec,
    )
    panel60_index = pd.DatetimeIndex(panel60.index)
    supplement60 = expand_daily_supplement_to_60m(supplement_daily, panel60_index)
    v1_owner60 = cast(pd.Series, route60["p36_owner_active"]).astype(bool)
    combined_owner60 = v1_owner60 | supplement60
    desired60 = cast(pd.Series, panel60["p13_desired_position"]).copy()
    p36_desired60 = cast(pd.Series, panel60["p36_desired_position"])
    desired60.loc[combined_owner60] = p36_desired60.loc[combined_owner60]
    index15 = pd.DatetimeIndex(pd.to_datetime(causal_15m_ohlc["timestamp"], errors="raise"))
    desired15 = align_strictly_prior_60m_desired_to_15m(index15, desired60)
    result = compose_three_bucket_iir_reference(
        dynamic_iir_desired=desired15,
        crash_rebound_raw=frozen_crash_rebound_executable,
        rebound_breadth_by_completed_bar=rebound_breadth_by_completed_bar,
        paper_up_executable=cast(pd.Series, v1["paper_s2_up_q925"]).astype(float),
        ols_down_decision=cast(pd.Series, v1["ols_down_decision"]),
        downside_jump_concentration=cast(
            pd.Series,
            v1["downside_jump_concentration_h12"],
        ),
        spec=account_spec,
    )
    v1_owner15 = align_strictly_prior_60m_desired_to_15m(index15, v1_owner60.astype(float)).gt(0.5)
    supplement15 = align_strictly_prior_60m_desired_to_15m(index15, supplement60.astype(float)).gt(0.5)
    combined15 = v1_owner15 | supplement15
    result.insert(
        0,
        "v1_combo_t1_position",
        cast(pd.Series, v1["combo_t1_position"]),
    )
    result.insert(1, "v1_p36_owner_active", v1_owner15)
    result.insert(2, "market_field_p36_supplement_active", supplement15)
    result.insert(3, "combined_p36_owner_active", combined15)
    result["reference_version"] = REFERENCE_VERSION
    result.attrs["field_labels_zh"] = {
        **v1.attrs.get("field_labels_zh", {}),
        **FIELD_LABELS_ZH,
    }
    result.attrs["formula_contract"] = three_bucket_iir_reference_v2_contract(
        account_spec=account_spec,
        field_spec=field_spec,
    )
    return result


def aggregate_v2_comparison(
    open_price: pd.Series,
    positions: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end_exclusive: pd.Timestamp,
    account_spec: TimingThreeBucketIIRReferenceSpec = TimingThreeBucketIIRReferenceSpec(),
) -> dict[str, object]:
    """Compare V2 with the complete V1 sample on the identical account."""

    baseline = aggregate_account_metrics(
        open_price,
        cast(pd.Series, positions["v1_combo_t1_position"]),
        start=start,
        end_exclusive=end_exclusive,
        spec=account_spec,
    )
    candidate = aggregate_account_metrics(
        open_price,
        cast(pd.Series, positions["combo_t1_position"]),
        start=start,
        end_exclusive=end_exclusive,
        spec=account_spec,
    )
    net_delta = float(candidate["net_log_return"]) - float(baseline["net_log_return"])
    comparison = {
        "net_log_return_delta": net_delta,
        "terminal_wealth_lift": math.exp(net_delta) - 1.0,
        "annualized_return_delta": float(candidate["annualized_return"]) - float(baseline["annualized_return"]),
        "annualized_sharpe_delta": float(candidate["annualized_sharpe"]) - float(baseline["annualized_sharpe"]),
        "max_drawdown_improvement": float(candidate["max_drawdown"]) - float(baseline["max_drawdown"]),
        "turnover_units_delta": float(candidate["turnover_units"]) - float(baseline["turnover_units"]),
    }
    return {
        "schema_id": "market_state_three_bucket_iir_v2_aggregate_comparison@1.0",
        "aggregate_only": True,
        "details_exposed": False,
        "v1_reference": baseline,
        "v2_market_field_reference": candidate,
        "comparison": comparison,
        "verdict": {
            "return_improved": net_delta > 0.0,
            "sharpe_improved": comparison["annualized_sharpe_delta"] > 0.0,
            "drawdown_not_worse": comparison["max_drawdown_improvement"] >= -1e-12,
            "research_candidate_positive": (
                net_delta > 0.0 and comparison["annualized_sharpe_delta"] > 0.0 and comparison["max_drawdown_improvement"] >= -1e-12
            ),
            "production_gate_passed": False,
        },
    }


def three_bucket_iir_reference_v2_contract(
    *,
    account_spec: TimingThreeBucketIIRReferenceSpec = TimingThreeBucketIIRReferenceSpec(),
    field_spec: TimingMarketFieldIIRSupplementSpec = TimingMarketFieldIIRSupplementSpec(),
) -> dict[str, object]:
    """Return the reproducibility, evidence, and authority contract for V2."""

    return {
        "schema_id": SCHEMA_ID,
        "reference_version": REFERENCE_VERSION,
        "reference_role": "infrastructure_level_bidirectional_iteration_sample",
        "parent_reference": "timing_three_bucket_iir_reference_v1",
        "market_field_version": MARKET_FIELD_VERSION,
        "does_not_supersede": [
            "timing_strategy_router_v4",
            "timing_explosive_layer_v3",
            "timing_three_bucket_iir_reference_v1",
        ],
        "bucket_priority": list(BUCKET_PRIORITY),
        "account_spec": asdict(account_spec),
        "field_supplement_spec": asdict(field_spec),
        "field_supplement_mechanism": {
            "state": "medium_scale_persistent_and_fast_subscale_not_extremely_hot",
            "conditions": [
                "d4_variance_ratio_at_or_above_shifted_past_q0.80",
                "d8_path_efficiency_at_or_above_shifted_past_q0.50",
                "below_d4_highpass_power_heat_at_or_below_plus_1_sigma",
            ],
            "action": "supplement_p36_owner",
            "v1_owner_can_be_vetoed": False,
            "combination": "v1_p36_owner OR market_field_p36_supplement",
        },
        "selection_evidence": {
            "development_period": "2009-2017",
            "development_fold_net_log_delta_vs_v1": [
                0.03484842274038444,
                0.08338796677842193,
                0.14333141098381424,
                -0.001124229698160722,
            ],
            "development_total_net_log_delta_vs_v1": 0.2732314886353082,
            "local_neighbor_count": 24,
            "local_neighbor_development_positive_count": 24,
            "local_neighbor_near_zero_worst_fold_count": 20,
            "repeat_audit_2018_2020_consumed": True,
            "repeat_audit_net_log_delta_vs_v1": 0.024187313651328785,
            "repeat_audit_local_neighbor_positive_count": 24,
            "repeat_audit_local_neighbor_count": 24,
        },
        "evaluation": {
            "development_period": "2009-2017",
            "repeat_audit_period": "2018-2020_consumed_not_fresh",
            "aggregate_blackbox_period": "2021-2026",
            "aggregate_blackbox_details_forbidden": True,
            "comparison_baseline": "complete_timing_three_bucket_iir_reference_v1",
            "full_continuous_path_repricing_required": True,
            "additive_static_period_approximation_forbidden": True,
        },
        "known_reproducibility_boundary": {
            "frozen_rebound_artifact_sha256": FROZEN_REBOUND_ARTIFACT_SHA256,
            "frozen_rebound_artifact_is_authoritative": True,
            "current_source_rematerialization_matches_frozen_artifact": False,
            "policy": "fail_closed_on_artifact_or_market_field_digest_change",
        },
        "field_labels_zh": FIELD_LABELS_ZH,
        "runtime_uses_future": False,
        "runtime_uses_registered_events": False,
        "research_authority": True,
        "architecture_lock_authority": False,
        "parameter_authority": False,
        "production_authority": False,
        "v62_runtime_modified": False,
    }


__all__ = [
    "FIELD_LABELS_ZH",
    "MARKET_FIELD_VERSION",
    "REFERENCE_VERSION",
    "REQUIRED_DAILY_FIELD_COLUMNS",
    "SCHEMA_ID",
    "TimingMarketFieldIIRSupplementSpec",
    "aggregate_v2_comparison",
    "build_market_field_p36_supplement",
    "build_three_bucket_iir_reference_v2",
    "expand_daily_supplement_to_60m",
    "three_bucket_iir_reference_v2_contract",
]
