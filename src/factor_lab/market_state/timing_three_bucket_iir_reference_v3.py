"""Market-field-conditioned specialist V3 over the V2 residual IIR sample.

V3 is an infrastructure research sample, not a production strategy.  It keeps
the V2 residual-IIR route and the frozen specialist priority, then applies the
two pre-2021 findings that survived complete-account repricing:

* the crash-rebound breadth gate moves onto the stable 0.40--0.425 plateau;
* the paper up specialist uses matched-horizon volatility normalization and
  switches from S3 to S2 only when the causal 2D band is hot and the original
  market has positive 1D signed path efficiency.

The OLS down specialist remains unchanged because its field-conditioned
relaxation did not pass every development fold.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Final, cast

import numpy as np
import pandas as pd

from factor_lab.market_state.research.ols_paper_explosive_bucket_battle_v1 import (
    build_paper_tail_decision,
    enforce_true_t_plus_one,
)
from factor_lab.market_state.timing_lifecycle_parameter_router import (
    compose_ordered_specialist_claims,
    expand_decision_eligible_daily_state,
    gate_complete_lifecycle_by_entry_threshold,
    route_complete_lifecycle_by_entry,
)
from factor_lab.market_state.timing_matched_volatility_signal import (
    build_lagged_matched_volatility_ewma_score,
)
from factor_lab.market_state.timing_three_bucket_iir_reference_v1 import (
    FROZEN_REBOUND_ARTIFACT_SHA256,
    TimingThreeBucketIIRReferenceSpec,
    aggregate_account_metrics,
)
from factor_lab.market_state.timing_three_bucket_iir_reference_v2 import (
    MARKET_FIELD_VERSION,
    TimingMarketFieldIIRSupplementSpec,
    build_three_bucket_iir_reference_v2,
)

SCHEMA_ID: Final[str] = "market_state_timing_three_bucket_iir_reference@3.0"
REFERENCE_VERSION: Final[str] = "timing_three_bucket_iir_reference_v3"
BUCKET_PRIORITY_V3: Final[tuple[str, ...]] = (
    "crash_rebound_breadth_0425",
    "paper_matched_volatility_s2_s3_up",
    "ols_w12_w24_down_jump_019",
    "dynamic_iir_v2_residual",
)


@dataclass(frozen=True, slots=True)
class TimingSpecialistMarketFieldRouteSpec:
    """Frozen low-capacity V3 specialist formula."""

    rebound_breadth_minimum: float = 0.425
    paper_default_trend_days: int = 3
    paper_default_tail_quantile: float = 0.925
    paper_fast_trend_days: int = 2
    paper_fast_tail_quantile: float = 0.950
    paper_fast_band_days: float = 2.0
    paper_fast_band_heat_minimum: float = 0.0
    paper_direction_scale_days: float = 1.0
    paper_signed_path_efficiency_minimum: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 < self.rebound_breadth_minimum < 1.0:
            raise ValueError("rebound breadth minimum must lie in (0, 1)")
        if min(self.paper_default_trend_days, self.paper_fast_trend_days) < 1:
            raise ValueError("paper trend horizons must be positive")
        for quantile in (
            self.paper_default_tail_quantile,
            self.paper_fast_tail_quantile,
        ):
            if not 0.5 < quantile < 1.0:
                raise ValueError("paper tail quantiles must lie in (0.5, 1)")


REQUIRED_V3_FIELD_COLUMNS: Final[tuple[str, ...]] = (
    "trading_day",
    "decision_eligible_date",
    "band_absolute_power_heat_d2",
    "scale_signed_path_efficiency_d1",
)


FIELD_LABELS_ZH: Final[dict[str, str]] = {
    "v2_combo_t1_position": "V2场谱剩余IIR样板真实T+1基准仓位",
    "crash_rebound_prior_breadth": "暴跌反弹入场前一棒强上涨股票占比",
    "crash_rebound_breadth_0425": "0.425宽度门后的完整暴跌反弹生命周期",
    "paper_band_heat_d2": "严格可用的2日清洁频段热度",
    "paper_signed_path_efficiency_d1": "严格可用的1日原行情有向路径效率",
    "paper_fast_state": "2日升温且1日方向向上的S2所有权状态",
    "paper_requested_candidate_id": "本棒若新入场时请求的论文核参数",
    "paper_routed_candidate_id": "完整生命周期内冻结的论文核参数",
    "paper_routed_decision_active": "论文核路由收盘决策生命周期",
    "paper_routed_executable_position": "论文核路由真实T+1执行仓位",
    "crash_rebound_claim": "暴跌反弹第一优先责任",
    "paper_up_claim": "论文核上涨严格余集责任",
    "ols_down_claim": "OLS下跌严格余集责任",
    "residual_iir_claim": "三桶后V2动态IIR剩余责任",
    "combo_desired_position": "V3三桶加V2动态IIR组合目标仓位",
    "combo_t1_position": "V3三桶加V2动态IIR真实T+1仓位",
    "reference_version": "基础设施样板版本",
    "runtime_uses_future": "运行时是否使用未来数据",
    "research_authority": "研究样板权限",
    "production_authority": "生产权限",
}


def build_paper_market_field_route(
    causal_15m_ohlc: pd.DataFrame,
    market_field_daily: pd.DataFrame,
    *,
    spec: TimingSpecialistMarketFieldRouteSpec = TimingSpecialistMarketFieldRouteSpec(),
) -> pd.DataFrame:
    """Build the causal matched-volatility S2/S3 complete-lifecycle route."""

    required_price = {"timestamp", "close"}
    missing_price = sorted(required_price.difference(causal_15m_ohlc.columns))
    if missing_price:
        raise KeyError(f"V3 paper route missing price columns: {missing_price}")
    index = pd.DatetimeIndex(pd.to_datetime(causal_15m_ohlc["timestamp"], errors="raise"))
    if index.empty or index.has_duplicates or not index.is_monotonic_increasing:
        raise ValueError("V3 paper route timestamps must be non-empty and ordered")
    close = pd.Series(
        pd.to_numeric(causal_15m_ohlc["close"], errors="raise").to_numpy(float),
        index=index,
        name="close",
    )
    if bool(close.le(0.0).any()):
        raise ValueError("V3 paper route closes must be positive")
    default_signal_id = f"trend_s{spec.paper_default_trend_days}__matched_volatility"
    fast_signal_id = f"trend_s{spec.paper_fast_trend_days}__matched_volatility"
    default_score = build_lagged_matched_volatility_ewma_score(
        close,
        span_bars=spec.paper_default_trend_days * 16,
    )
    fast_score = build_lagged_matched_volatility_ewma_score(
        close,
        span_bars=spec.paper_fast_trend_days * 16,
    )
    default_decision = build_paper_tail_decision(
        default_score,
        side="up",
        quantile=spec.paper_default_tail_quantile,
    )
    fast_decision = build_paper_tail_decision(
        fast_score,
        side="up",
        quantile=spec.paper_fast_tail_quantile,
    )
    field = expand_decision_eligible_daily_state(
        market_field_daily,
        index,
        value_columns=(
            "band_absolute_power_heat_d2",
            "scale_signed_path_efficiency_d1",
        ),
    )
    heat = pd.to_numeric(field["band_absolute_power_heat_d2"], errors="coerce")
    direction = pd.to_numeric(field["scale_signed_path_efficiency_d1"], errors="coerce")
    fast_state = heat.gt(spec.paper_fast_band_heat_minimum) & direction.gt(spec.paper_signed_path_efficiency_minimum)
    requested = pd.Series(
        np.where(fast_state.fillna(False), "paper_fast_s2", "paper_default_s3"),
        index=index,
        dtype="string",
    )
    route = route_complete_lifecycle_by_entry(
        {
            "paper_fast_s2": fast_decision,
            "paper_default_s3": default_decision,
        },
        requested,
    )
    executable = enforce_true_t_plus_one(
        cast(pd.Series, route["routed_decision_active"]),
        side="up",
    )
    output = pd.DataFrame(
        {
            "paper_band_heat_d2": heat,
            "paper_signed_path_efficiency_d1": direction,
            "paper_fast_state": fast_state,
            "paper_requested_candidate_id": requested,
            "paper_routed_candidate_id": route["routed_candidate_id"],
            "paper_routed_entry_trigger": route["routed_entry_trigger"],
            "paper_routed_exit_trigger": route["routed_exit_trigger"],
            "paper_routed_decision_active": route["routed_decision_active"],
            "paper_routed_executable_position": executable,
            "runtime_uses_future": False,
        },
        index=index,
    )
    output.attrs["formula_contract"] = {
        "default": f"{default_signal_id}_q{spec.paper_default_tail_quantile}",
        "fast": f"{fast_signal_id}_q{spec.paper_fast_tail_quantile}",
        "fast_state": ("band_absolute_power_heat_d2_gt_0 AND scale_signed_path_efficiency_d1_gt_0"),
        "ownership": "entry_only_then_freeze_complete_lifecycle",
    }
    return output


def build_three_bucket_iir_reference_v3(
    causal_15m_ohlc: pd.DataFrame,
    causal_60m_ohlc: pd.DataFrame,
    market_field_daily: pd.DataFrame,
    *,
    frozen_crash_rebound_executable: pd.Series,
    rebound_breadth_by_completed_bar: pd.Series,
    allowed_end_exclusive: pd.Timestamp,
    account_spec: TimingThreeBucketIIRReferenceSpec = TimingThreeBucketIIRReferenceSpec(),
    residual_field_spec: TimingMarketFieldIIRSupplementSpec = TimingMarketFieldIIRSupplementSpec(),
    specialist_spec: TimingSpecialistMarketFieldRouteSpec = TimingSpecialistMarketFieldRouteSpec(),
) -> pd.DataFrame:
    """Build V3 over the complete, unchanged V2 residual owner."""

    index = pd.DatetimeIndex(pd.to_datetime(causal_15m_ohlc["timestamp"], errors="raise"))
    if not frozen_crash_rebound_executable.index.equals(index):
        raise ValueError("frozen crash rebound does not align to V3 carrier")
    if not rebound_breadth_by_completed_bar.index.equals(index):
        raise ValueError("rebound breadth does not align to V3 carrier")
    v2 = build_three_bucket_iir_reference_v2(
        causal_15m_ohlc,
        causal_60m_ohlc,
        market_field_daily,
        frozen_crash_rebound_executable=frozen_crash_rebound_executable,
        rebound_breadth_by_completed_bar=rebound_breadth_by_completed_bar,
        allowed_end_exclusive=allowed_end_exclusive,
        account_spec=account_spec,
        field_spec=residual_field_spec,
    )
    prior_breadth = pd.to_numeric(rebound_breadth_by_completed_bar, errors="coerce").shift(1)
    crash_gate = gate_complete_lifecycle_by_entry_threshold(
        frozen_crash_rebound_executable.astype(bool),
        prior_breadth,
        specialist_spec.rebound_breadth_minimum,
    )
    paper_route = build_paper_market_field_route(
        causal_15m_ohlc,
        market_field_daily,
        spec=specialist_spec,
    )
    crash_position = cast(pd.Series, crash_gate["gated_lifecycle"]).astype(float)
    paper_position = cast(pd.Series, paper_route["paper_routed_executable_position"]).astype(float)
    ols_down_position = pd.Series(
        np.where(cast(pd.Series, v2["ols_down_gated"]).astype(bool), -1.0, 0.0),
        index=index,
        dtype=float,
    )
    claims = compose_ordered_specialist_claims(
        cast(pd.Series, v2["dynamic_iir_desired_position"]),
        {
            "crash_rebound": crash_position,
            "paper_up": paper_position,
            "ols_down": ols_down_position,
        },
    )
    output = pd.DataFrame(
        {
            "v2_combo_t1_position": v2["combo_t1_position"],
            "dynamic_iir_desired_position": v2["dynamic_iir_desired_position"],
            "crash_rebound_prior_breadth": prior_breadth,
            "crash_rebound_breadth_0425": crash_gate["gated_lifecycle"],
            "paper_band_heat_d2": paper_route["paper_band_heat_d2"],
            "paper_signed_path_efficiency_d1": paper_route["paper_signed_path_efficiency_d1"],
            "paper_fast_state": paper_route["paper_fast_state"],
            "paper_requested_candidate_id": paper_route["paper_requested_candidate_id"],
            "paper_routed_candidate_id": paper_route["paper_routed_candidate_id"],
            "paper_routed_decision_active": paper_route["paper_routed_decision_active"],
            "paper_routed_executable_position": paper_position,
            "ols_down_gated": v2["ols_down_gated"],
            "crash_rebound_claim": claims["crash_rebound_claim"],
            "paper_up_claim": claims["paper_up_claim"],
            "ols_down_claim": claims["ols_down_claim"],
            "residual_iir_claim": claims["residual_claim"],
            "combo_desired_position": claims["combo_desired_position"],
            "combo_t1_position": claims["combo_t1_position"],
            "reference_version": REFERENCE_VERSION,
            "runtime_uses_future": False,
            "research_authority": True,
            "production_authority": False,
        },
        index=index,
    )
    output.attrs["field_labels_zh"] = FIELD_LABELS_ZH
    output.attrs["formula_contract"] = three_bucket_iir_reference_v3_contract(
        account_spec=account_spec,
        residual_field_spec=residual_field_spec,
        specialist_spec=specialist_spec,
    )
    return output


def aggregate_v3_comparison(
    open_price: pd.Series,
    positions: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end_exclusive: pd.Timestamp,
    account_spec: TimingThreeBucketIIRReferenceSpec = TimingThreeBucketIIRReferenceSpec(),
) -> dict[str, object]:
    """Compare V3 with the complete V2 path on one aggregate account."""

    baseline = aggregate_account_metrics(
        open_price,
        cast(pd.Series, positions["v2_combo_t1_position"]),
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
    delta = {
        "net_log_return": float(candidate["net_log_return"]) - float(baseline["net_log_return"]),
        "terminal_wealth_lift": math.exp(float(candidate["net_log_return"]) - float(baseline["net_log_return"])) - 1.0,
        "annualized_return": float(candidate["annualized_return"]) - float(baseline["annualized_return"]),
        "annualized_sharpe": float(candidate["annualized_sharpe"]) - float(baseline["annualized_sharpe"]),
        "max_drawdown_improvement": float(candidate["max_drawdown"]) - float(baseline["max_drawdown"]),
        "turnover_units": float(candidate["turnover_units"]) - float(baseline["turnover_units"]),
    }
    return {
        "schema_id": "market_state_three_bucket_iir_v3_aggregate_comparison@1.0",
        "aggregate_only": True,
        "details_exposed": False,
        "v2_reference": baseline,
        "v3_specialist_market_field_reference": candidate,
        "comparison": delta,
        "verdict": {
            "return_improved": delta["net_log_return"] > 0.0,
            "sharpe_improved": delta["annualized_sharpe"] > 0.0,
            "drawdown_not_worse": delta["max_drawdown_improvement"] >= -1e-12,
            "research_signal_survives": (delta["net_log_return"] > 0.0 and delta["annualized_sharpe"] > 0.0),
            "complete_gate_passed": (
                delta["net_log_return"] > 0.0 and delta["annualized_sharpe"] > 0.0 and delta["max_drawdown_improvement"] >= -1e-12
            ),
            "production_gate_passed": False,
        },
    }


def three_bucket_iir_reference_v3_contract(
    *,
    account_spec: TimingThreeBucketIIRReferenceSpec = TimingThreeBucketIIRReferenceSpec(),
    residual_field_spec: TimingMarketFieldIIRSupplementSpec = TimingMarketFieldIIRSupplementSpec(),
    specialist_spec: TimingSpecialistMarketFieldRouteSpec = TimingSpecialistMarketFieldRouteSpec(),
) -> dict[str, object]:
    """Return the frozen V3 formula, evidence, and authority boundary."""

    return {
        "schema_id": SCHEMA_ID,
        "reference_version": REFERENCE_VERSION,
        "reference_role": "infrastructure_level_specialist_field_iteration_sample",
        "parent_reference": "timing_three_bucket_iir_reference_v2",
        "market_field_version": MARKET_FIELD_VERSION,
        "bucket_priority": list(BUCKET_PRIORITY_V3),
        "account_spec": asdict(account_spec),
        "residual_field_spec": asdict(residual_field_spec),
        "specialist_field_spec": asdict(specialist_spec),
        "specialist_changes": {
            "crash_rebound": {
                "action": "tighten_entry_breadth_on_stable_plateau",
                "old_minimum": 0.35,
                "new_minimum": specialist_spec.rebound_breadth_minimum,
                "dynamic_field_route_supported": False,
            },
            "paper_up": {
                "normalization": "lagged_same_horizon_ewma_volatility",
                "default": "S3_q0.925",
                "fast": "S2_q0.950",
                "fast_state": [
                    "causal_2d_band_absolute_power_heat_gt_0",
                    "causal_1d_signed_path_efficiency_gt_0",
                ],
                "ownership": "entry_only_then_freeze_complete_lifecycle",
            },
            "ols_down": {
                "action": "unchanged",
                "reason": "field_relaxation_failed_one_of_three_development_folds",
            },
        },
        "selection_evidence": {
            "development_period": "2009-2017",
            "development_fold_net_log_delta_vs_v2": [
                0.03803255149152962,
                0.025746602575026145,
                0.06289536973059473,
            ],
            "development_total_net_log_delta_vs_v2": 0.12667452379715094,
            "development_sharpe_delta_vs_v2": 0.08627031537844365,
            "development_best_year_removed_delta": 0.07040486388577262,
            "development_positive_year_count": 6,
            "development_negative_year_count": 3,
            "one_extra_15m_bar_delay_net_log_delta": 0.07570887129195825,
            "repeat_audit_2018_2020_consumed": True,
            "repeat_audit_net_log_delta_vs_v2": 0.05741914079076649,
            "repeat_audit_sharpe_delta_vs_v2": 0.12764999096103358,
            "repeat_audit_drawdown_improvement_vs_v2": -0.0013303574276083419,
        },
        "evaluation": {
            "development_period": "2009-2017",
            "repeat_audit_period": "2018-2020_consumed_after_formula_freeze",
            "aggregate_blackbox_period": "2021-2026",
            "aggregate_blackbox_details_forbidden": True,
            "comparison_baseline": "complete_timing_three_bucket_iir_reference_v2",
            "full_continuous_path_repricing_required": True,
            "complete_lifecycle_parameter_ownership_required": True,
            "single_final_t1_state_machine_required": True,
        },
        "known_limitations": {
            "repeat_audit_drawdown_gate_passed": False,
            "repeat_audit_drawdown_worsening_percentage_points": 0.1330357427608342,
            "down_specialist_dynamic_parameter_authorized": False,
            "crash_specialist_dynamic_parameter_authorized": False,
        },
        "known_reproducibility_boundary": {
            "frozen_rebound_artifact_sha256": FROZEN_REBOUND_ARTIFACT_SHA256,
            "policy": "fail_closed_on_artifact_market_field_or_preregistration_change",
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
    "BUCKET_PRIORITY_V3",
    "FIELD_LABELS_ZH",
    "REFERENCE_VERSION",
    "REQUIRED_V3_FIELD_COLUMNS",
    "SCHEMA_ID",
    "TimingSpecialistMarketFieldRouteSpec",
    "aggregate_v3_comparison",
    "build_paper_market_field_route",
    "build_three_bucket_iir_reference_v3",
    "three_bucket_iir_reference_v3_contract",
]
