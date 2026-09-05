"""Chronologically constrained V4 of the three-specialist IIR sample.

V4 is an infrastructure research sample, not a production strategy.  It
keeps the V2 residual IIR owner, specialist priority, costs and signed T+1
account semantics.  The three specialist formulas were admitted one
two-year block at a time: a later condition is legal only when the complete
account remains non-negative in every earlier block and the condition fixes
the newly revealed residual relative to its frozen parent.

The module owns the frozen causal formula only.  Progressive selection and
holdout admission live in :mod:`timing_progressive_block_constraint`.
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

SCHEMA_ID: Final[str] = "market_state_timing_three_bucket_iir_reference@4.0"
REFERENCE_VERSION: Final[str] = "timing_three_bucket_iir_reference_v4"
BUCKET_PRIORITY_V4: Final[tuple[str, ...]] = (
    "crash_rebound_progressive_breadth",
    "paper_progressive_up",
    "ols_progressive_down",
    "dynamic_iir_v2_residual",
)


@dataclass(frozen=True, slots=True)
class TimingSpecialistProgressiveRouteSpec:
    """Frozen low-capacity formula admitted through the 2017--2018 block."""

    reference_history_days: int = 625
    reference_minimum_days: int = 312
    crash_default_breadth_minimum: float = 0.35
    crash_strict_breadth_minimum: float = 0.40
    paper_default_trend_days: int = 2
    paper_alternate_trend_days: int = 3
    paper_tail_quantile: float = 0.925
    paper_band_heat_minimum: float = 0.0
    paper_signed_path_efficiency_minimum: float = 0.0
    paper_fast_band_change_minimum: float = 0.0
    ols_default_jump_minimum: float = 0.19
    ols_relaxed_jump_minimum: float = 0.14
    ols_band_change_minimum: float = 0.0
    ols_signed_path_efficiency_maximum: float = 0.0

    def __post_init__(self) -> None:
        if self.reference_history_days < 250:
            raise ValueError("V4 reference history must be at least 250 trading days")
        if not 1 <= self.reference_minimum_days <= self.reference_history_days:
            raise ValueError("V4 reference minimum must lie inside its history")
        for threshold in (
            self.crash_default_breadth_minimum,
            self.crash_strict_breadth_minimum,
            self.ols_default_jump_minimum,
            self.ols_relaxed_jump_minimum,
        ):
            if not 0.0 < threshold < 1.0:
                raise ValueError("V4 entry thresholds must lie in (0, 1)")
        if self.crash_strict_breadth_minimum <= self.crash_default_breadth_minimum:
            raise ValueError("V4 strict crash breadth must exceed its default")
        if self.ols_relaxed_jump_minimum >= self.ols_default_jump_minimum:
            raise ValueError("V4 relaxed OLS jump threshold must be below its default")
        if min(self.paper_default_trend_days, self.paper_alternate_trend_days) < 1:
            raise ValueError("V4 paper horizons must be positive")
        if not 0.5 < self.paper_tail_quantile < 1.0:
            raise ValueError("V4 paper tail quantile must lie in (0.5, 1)")


REQUIRED_V4_FIELD_COLUMNS: Final[tuple[str, ...]] = (
    "trading_day",
    "decision_eligible_date",
    "trend_scale_path_efficiency_d2p0",
    "trend_scale_signed_path_efficiency_d0p5",
    "trend_scale_signed_path_efficiency_d2p0",
    "trend_scale_signed_path_efficiency_d4p0",
    "band_absolute_power_heat_d4",
    "band_power_log_change_1cycle_d1",
    "band_power_log_change_1cycle_d2",
)


FIELD_LABELS_ZH: Final[dict[str, str]] = {
    "v2_combo_t1_position": "V2三桶动态IIR真实T+1基准仓位",
    "path_efficiency_d2": "严格可用2日路径效率",
    "path_efficiency_d2_past_median": "仅用过去625日的2日路径效率中位数",
    "crash_rebound_entry_threshold": "暴跌反弹完整生命周期入场宽度线",
    "crash_rebound_progressive": "两年递进宽度门后暴跌反弹生命周期",
    "paper_alternate_state": "中频向上且近端能量继续增长状态",
    "paper_requested_candidate_id": "论文核新入场请求参数",
    "paper_routed_candidate_id": "论文核生命周期冻结参数",
    "paper_progressive_executable_position": "论文核真实T+1执行仓位",
    "ols_relaxed_state": "下跌能量增长、多尺度同向且路径效率偏低状态",
    "ols_entry_threshold": "OLS完整生命周期入场跳变线",
    "ols_progressive_executable_position": "OLS下跌真实T+1执行仓位",
    "crash_rebound_claim": "暴跌反弹第一优先责任",
    "paper_up_claim": "论文核上涨严格余集责任",
    "ols_down_claim": "OLS下跌严格余集责任",
    "residual_iir_claim": "三桶后V2动态IIR剩余责任",
    "combo_desired_position": "V4三桶加V2动态IIR目标仓位",
    "combo_desired_owner": "V4三桶加V2动态IIR目标责任人",
    "combo_t1_position": "V4三桶加V2动态IIR真实T+1仓位",
    "combo_t1_owner": "V4三桶加V2动态IIR真实T+1持仓责任人",
}


def prepare_progressive_specialist_field(
    market_field_daily: pd.DataFrame,
    *,
    allowed_end_exclusive: pd.Timestamp,
    spec: TimingSpecialistProgressiveRouteSpec = TimingSpecialistProgressiveRouteSpec(),
) -> pd.DataFrame:
    """Validate raw causal measurements and derive the shifted past median."""

    missing = sorted(set(REQUIRED_V4_FIELD_COLUMNS).difference(market_field_daily.columns))
    if missing:
        raise KeyError(f"V4 market field is missing columns: {missing}")
    frame = market_field_daily.loc[:, REQUIRED_V4_FIELD_COLUMNS].copy()
    frame["trading_day"] = pd.to_datetime(frame["trading_day"], errors="raise")
    frame["decision_eligible_date"] = pd.to_datetime(
        frame["decision_eligible_date"], errors="raise"
    )
    frame = frame.sort_values("trading_day").reset_index(drop=True)
    if frame.empty or frame["trading_day"].duplicated().any():
        raise ValueError("V4 market field needs exactly one row per trading day")
    if frame["decision_eligible_date"].duplicated().any():
        raise ValueError("V4 market field decision dates must be unique")
    if bool(frame["decision_eligible_date"].le(frame["trading_day"]).any()):
        raise ValueError("V4 field values must become eligible after their trading day")
    if bool(frame["decision_eligible_date"].ge(allowed_end_exclusive).any()):
        raise RuntimeError("V4 market field crossed the caller's allowed boundary")
    for column in REQUIRED_V4_FIELD_COLUMNS[2:]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    path = cast(pd.Series, frame["trend_scale_path_efficiency_d2p0"])
    frame["trend_scale_path_efficiency_d2p0_past_median"] = (
        path.shift(1)
        .rolling(spec.reference_history_days, min_periods=spec.reference_minimum_days)
        .median()
    )
    frame.attrs["runtime_uses_future"] = False
    frame.attrs["reference_statistic"] = "shift1_rolling625_min312_median"
    return frame


def _raw_ewma_score(close: pd.Series, *, span_bars: int) -> pd.Series:
    returns = close.pct_change(fill_method=None)
    return math.sqrt(span_bars) * returns.ewm(span=span_bars, adjust=False).mean()


def build_three_bucket_iir_reference_v4(
    causal_15m_ohlc: pd.DataFrame,
    causal_60m_ohlc: pd.DataFrame,
    market_field_daily_v2: pd.DataFrame,
    market_field_daily_v4: pd.DataFrame,
    *,
    frozen_crash_rebound_executable: pd.Series,
    rebound_breadth_by_completed_bar: pd.Series,
    allowed_end_exclusive: pd.Timestamp,
    account_spec: TimingThreeBucketIIRReferenceSpec = TimingThreeBucketIIRReferenceSpec(),
    residual_field_spec: TimingMarketFieldIIRSupplementSpec = TimingMarketFieldIIRSupplementSpec(),
    specialist_spec: TimingSpecialistProgressiveRouteSpec = TimingSpecialistProgressiveRouteSpec(),
) -> pd.DataFrame:
    """Build the frozen V4 specialist routes over the unchanged V2 residual."""

    index = pd.DatetimeIndex(pd.to_datetime(causal_15m_ohlc["timestamp"], errors="raise"))
    if index.empty or index.has_duplicates or not index.is_monotonic_increasing:
        raise ValueError("V4 15m timestamps must be non-empty, unique and ordered")
    if index.max() >= allowed_end_exclusive:
        raise RuntimeError("V4 15m carrier crossed the caller's allowed boundary")
    if not frozen_crash_rebound_executable.index.equals(index):
        raise ValueError("frozen crash rebound does not align to V4 carrier")
    if not rebound_breadth_by_completed_bar.index.equals(index):
        raise ValueError("rebound breadth does not align to V4 carrier")

    v2 = build_three_bucket_iir_reference_v2(
        causal_15m_ohlc,
        causal_60m_ohlc,
        market_field_daily_v2,
        frozen_crash_rebound_executable=frozen_crash_rebound_executable,
        rebound_breadth_by_completed_bar=rebound_breadth_by_completed_bar,
        allowed_end_exclusive=allowed_end_exclusive,
        account_spec=account_spec,
        field_spec=residual_field_spec,
    )
    daily = prepare_progressive_specialist_field(
        market_field_daily_v4,
        allowed_end_exclusive=allowed_end_exclusive,
        spec=specialist_spec,
    )
    expanded = expand_decision_eligible_daily_state(
        daily,
        index,
        value_columns=(
            "trend_scale_path_efficiency_d2p0",
            "trend_scale_path_efficiency_d2p0_past_median",
            "trend_scale_signed_path_efficiency_d0p5",
            "trend_scale_signed_path_efficiency_d2p0",
            "trend_scale_signed_path_efficiency_d4p0",
            "band_absolute_power_heat_d4",
            "band_power_log_change_1cycle_d1",
            "band_power_log_change_1cycle_d2",
        ),
    )
    path_d2 = pd.to_numeric(expanded["trend_scale_path_efficiency_d2p0"], errors="coerce")
    path_d2_median = pd.to_numeric(
        expanded["trend_scale_path_efficiency_d2p0_past_median"], errors="coerce"
    )
    path_d2_low = path_d2.lt(path_d2_median)

    crash_threshold = pd.Series(
        np.where(
            path_d2_low.fillna(False),
            specialist_spec.crash_strict_breadth_minimum,
            specialist_spec.crash_default_breadth_minimum,
        ),
        index=index,
        dtype=float,
    )
    prior_breadth = pd.to_numeric(rebound_breadth_by_completed_bar, errors="coerce").shift(1)
    crash_route = gate_complete_lifecycle_by_entry_threshold(
        frozen_crash_rebound_executable.astype(bool),
        prior_breadth,
        crash_threshold,
    )
    crash_position = cast(pd.Series, crash_route["gated_lifecycle"]).astype(float)

    close = pd.Series(
        pd.to_numeric(causal_15m_ohlc["close"], errors="raise").to_numpy(float),
        index=index,
        name="close",
    )
    default_bars = specialist_spec.paper_default_trend_days * 16
    alternate_bars = specialist_spec.paper_alternate_trend_days * 16
    paper_decisions = {
        "paper_s2_raw": build_paper_tail_decision(
            _raw_ewma_score(close, span_bars=default_bars),
            side="up",
            quantile=specialist_spec.paper_tail_quantile,
        ),
        "paper_s3_matched": build_paper_tail_decision(
            build_lagged_matched_volatility_ewma_score(close, span_bars=alternate_bars),
            side="up",
            quantile=specialist_spec.paper_tail_quantile,
        ),
    }
    paper_state = (
        pd.to_numeric(expanded["band_absolute_power_heat_d4"], errors="coerce").gt(
            specialist_spec.paper_band_heat_minimum
        )
        & pd.to_numeric(
            expanded["trend_scale_signed_path_efficiency_d0p5"], errors="coerce"
        ).gt(specialist_spec.paper_signed_path_efficiency_minimum)
        & pd.to_numeric(expanded["band_power_log_change_1cycle_d1"], errors="coerce").gt(
            specialist_spec.paper_fast_band_change_minimum
        )
    )
    requested_paper = pd.Series(
        np.where(paper_state.fillna(False), "paper_s3_matched", "paper_s2_raw"),
        index=index,
        dtype="string",
    )
    paper_route = route_complete_lifecycle_by_entry(paper_decisions, requested_paper)
    paper_position = enforce_true_t_plus_one(
        cast(pd.Series, paper_route["routed_decision_active"]),
        side="up",
    ).astype(float)

    ols_state = (
        pd.to_numeric(expanded["band_power_log_change_1cycle_d2"], errors="coerce").gt(
            specialist_spec.ols_band_change_minimum
        )
        & pd.to_numeric(
            expanded["trend_scale_signed_path_efficiency_d4p0"], errors="coerce"
        ).lt(specialist_spec.ols_signed_path_efficiency_maximum)
        & path_d2_low
        & pd.to_numeric(
            expanded["trend_scale_signed_path_efficiency_d2p0"], errors="coerce"
        ).lt(specialist_spec.ols_signed_path_efficiency_maximum)
    )
    ols_threshold = pd.Series(
        np.where(
            ols_state.fillna(False),
            specialist_spec.ols_relaxed_jump_minimum,
            specialist_spec.ols_default_jump_minimum,
        ),
        index=index,
        dtype=float,
    )
    ols_route = gate_complete_lifecycle_by_entry_threshold(
        cast(pd.Series, v2["ols_down_decision"]).astype(bool),
        pd.to_numeric(v2["downside_jump_concentration_h12"], errors="coerce"),
        ols_threshold,
    )
    ols_position = enforce_true_t_plus_one(
        cast(pd.Series, ols_route["gated_lifecycle"]),
        side="down",
    ).astype(float)

    claims = compose_ordered_specialist_claims(
        cast(pd.Series, v2["dynamic_iir_desired_position"]),
        {
            "crash_rebound": crash_position,
            "paper_up": paper_position,
            "ols_down": ols_position,
        },
    )
    output = pd.DataFrame(
        {
            "v2_combo_t1_position": v2["combo_t1_position"],
            "dynamic_iir_desired_position": v2["dynamic_iir_desired_position"],
            "v2_crash_rebound_gated": v2["crash_rebound_gated"],
            "v2_paper_s2_up_q925": v2["paper_s2_up_q925"],
            "v2_ols_down_gated": v2["ols_down_gated"],
            "path_efficiency_d2": path_d2,
            "path_efficiency_d2_past_median": path_d2_median,
            "crash_rebound_prior_breadth": prior_breadth,
            "crash_rebound_entry_threshold": crash_threshold,
            "crash_rebound_progressive": crash_route["gated_lifecycle"],
            "paper_alternate_state": paper_state,
            "paper_requested_candidate_id": requested_paper,
            "paper_routed_candidate_id": paper_route["routed_candidate_id"],
            "paper_routed_decision_active": paper_route["routed_decision_active"],
            "paper_progressive_executable_position": paper_position,
            "ols_relaxed_state": ols_state,
            "ols_entry_threshold": ols_threshold,
            "ols_progressive_decision_active": ols_route["gated_lifecycle"],
            "ols_progressive_executable_position": ols_position,
            "crash_rebound_claim": claims["crash_rebound_claim"],
            "paper_up_claim": claims["paper_up_claim"],
            "ols_down_claim": claims["ols_down_claim"],
            "residual_iir_claim": claims["residual_claim"],
            "combo_desired_position": claims["combo_desired_position"],
            "combo_desired_owner": claims["combo_desired_owner"],
            "combo_t1_position": claims["combo_t1_position"],
            "combo_t1_owner": claims["combo_t1_owner"],
            "reference_version": REFERENCE_VERSION,
            "runtime_uses_future": False,
            "research_authority": True,
            "production_authority": False,
        },
        index=index,
    )
    output.attrs["field_labels_zh"] = FIELD_LABELS_ZH
    output.attrs["formula_contract"] = three_bucket_iir_reference_v4_contract(
        account_spec=account_spec,
        residual_field_spec=residual_field_spec,
        specialist_spec=specialist_spec,
    )
    return output


def build_v4_bucket_counterfactual_positions(positions: pd.DataFrame) -> pd.DataFrame:
    """Reprice each V4 bucket alone while holding every other V2 owner fixed."""

    required = {
        "v2_combo_t1_position",
        "dynamic_iir_desired_position",
        "v2_crash_rebound_gated",
        "v2_paper_s2_up_q925",
        "v2_ols_down_gated",
        "crash_rebound_progressive",
        "paper_progressive_executable_position",
        "ols_progressive_executable_position",
        "combo_t1_position",
    }
    missing = sorted(required.difference(positions.columns))
    if missing:
        raise KeyError(f"V4 counterfactual positions are missing columns: {missing}")
    index = positions.index
    residual = cast(pd.Series, positions["dynamic_iir_desired_position"])
    v2_specialists = {
        "crash_rebound": cast(pd.Series, positions["v2_crash_rebound_gated"]).astype(float),
        "paper_up": cast(pd.Series, positions["v2_paper_s2_up_q925"]).astype(float),
        "ols_down": pd.Series(
            np.where(cast(pd.Series, positions["v2_ols_down_gated"]).astype(bool), -1.0, 0.0),
            index=index,
            dtype=float,
        ),
    }
    v4_specialists = {
        "crash_rebound": cast(pd.Series, positions["crash_rebound_progressive"]).astype(float),
        "paper_up": cast(pd.Series, positions["paper_progressive_executable_position"]).astype(float),
        "ols_down": cast(pd.Series, positions["ols_progressive_executable_position"]).astype(float),
    }

    def compose(overrides: dict[str, pd.Series]) -> pd.Series:
        specialists = {**v2_specialists, **overrides}
        frame = compose_ordered_specialist_claims(residual, specialists)
        return cast(pd.Series, frame["combo_t1_position"])

    recomposed_v2 = compose({})
    if not recomposed_v2.equals(cast(pd.Series, positions["v2_combo_t1_position"])):
        raise RuntimeError("V4 counterfactual failed to reproduce the V2 baseline")
    combined = compose(v4_specialists)
    if not combined.equals(cast(pd.Series, positions["combo_t1_position"])):
        raise RuntimeError("V4 counterfactual failed to reproduce the combined formula")
    return pd.DataFrame(
        {
            "v2_reference": recomposed_v2,
            "crash_rebound_only": compose({"crash_rebound": v4_specialists["crash_rebound"]}),
            "paper_up_only": compose({"paper_up": v4_specialists["paper_up"]}),
            "ols_down_only": compose({"ols_down": v4_specialists["ols_down"]}),
            "combined_v4": combined,
        },
        index=index,
    )


def aggregate_v4_comparison(
    open_price: pd.Series,
    positions: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end_exclusive: pd.Timestamp,
    account_spec: TimingThreeBucketIIRReferenceSpec = TimingThreeBucketIIRReferenceSpec(),
) -> dict[str, object]:
    """Compare V4 with V2 on one complete, identically priced account."""

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
    net_delta = float(candidate["net_log_return"]) - float(baseline["net_log_return"])
    comparison = {
        "net_log_return_delta": net_delta,
        "terminal_wealth_lift": math.exp(net_delta) - 1.0,
        "annualized_return_delta": float(candidate["annualized_return"])
        - float(baseline["annualized_return"]),
        "annualized_sharpe_delta": float(candidate["annualized_sharpe"])
        - float(baseline["annualized_sharpe"]),
        "max_drawdown_improvement": float(candidate["max_drawdown"])
        - float(baseline["max_drawdown"]),
        "turnover_units_delta": float(candidate["turnover_units"])
        - float(baseline["turnover_units"]),
    }
    return {
        "schema_id": "market_state_three_bucket_iir_v4_aggregate_comparison@1.0",
        "aggregate_only": True,
        "details_exposed": False,
        "v2_reference": baseline,
        "v4_progressive_reference": candidate,
        "comparison": comparison,
        "verdict": {
            "return_improved": net_delta > 0.0,
            "sharpe_improved": comparison["annualized_sharpe_delta"] > 0.0,
            "drawdown_not_worse": comparison["max_drawdown_improvement"] >= -1e-12,
            "research_signal_survives": net_delta >= -1e-12,
            "production_gate_passed": False,
        },
    }


def three_bucket_iir_reference_v4_contract(
    *,
    account_spec: TimingThreeBucketIIRReferenceSpec = TimingThreeBucketIIRReferenceSpec(),
    residual_field_spec: TimingMarketFieldIIRSupplementSpec = TimingMarketFieldIIRSupplementSpec(),
    specialist_spec: TimingSpecialistProgressiveRouteSpec = TimingSpecialistProgressiveRouteSpec(),
) -> dict[str, object]:
    """Return the frozen V4 formula and authority boundary."""

    return {
        "schema_id": SCHEMA_ID,
        "reference_version": REFERENCE_VERSION,
        "reference_role": "infrastructure_level_progressive_specialist_sample",
        "parent_reference": "timing_three_bucket_iir_reference_v2",
        "market_field_version": MARKET_FIELD_VERSION,
        "bucket_priority": list(BUCKET_PRIORITY_V4),
        "account_spec": asdict(account_spec),
        "residual_field_spec": asdict(residual_field_spec),
        "specialist_spec": asdict(specialist_spec),
        "formula": {
            "crash_rebound": {
                "strict_when": "causal_d2_path_efficiency_below_shifted_past_median",
                "strict_breadth": specialist_spec.crash_strict_breadth_minimum,
                "otherwise_breadth": specialist_spec.crash_default_breadth_minimum,
                "ownership": "entry_only_then_complete_lifecycle",
            },
            "paper_up": {
                "alternate_when": [
                    "causal_d4_band_heat_gt_0",
                    "causal_d0p5_signed_path_efficiency_gt_0",
                    "causal_d1_band_power_change_gt_0",
                ],
                "alternate": "S3_matched_volatility_q0.925",
                "otherwise": "S2_raw_q0.925",
                "ownership": "entry_only_then_complete_lifecycle",
            },
            "ols_down": {
                "relaxed_when": [
                    "causal_d2_band_power_change_gt_0",
                    "causal_d4_signed_path_efficiency_lt_0",
                    "causal_d2_path_efficiency_below_shifted_past_median",
                    "causal_d2_signed_path_efficiency_lt_0",
                ],
                "relaxed_jump": specialist_spec.ols_relaxed_jump_minimum,
                "otherwise_jump": specialist_spec.ols_default_jump_minimum,
                "ownership": "entry_only_then_complete_lifecycle",
            },
        },
        "progressive_governance": {
            "development_blocks": [
                "2009-2010",
                "2011-2012",
                "2013-2014",
                "2015-2016",
                "2017-2018",
            ],
            "final_validation": "2019-2020_one_shot",
            "post_2020_rows_read": 0,
            "pooled_total_can_override_failed_bucket": False,
            "candidate_vs_parent_counterfactual_required": True,
            "full_account_and_bucket_responsibility_ledgers_required": True,
            "chronological_parent_inheritance_required": True,
            "block_boundary_isolation_required": True,
            "final_validation_can_rank_or_retune": False,
            "no_opportunity_counts_as_positive_evidence": False,
        },
        "known_reproducibility_boundary": {
            "frozen_rebound_artifact_sha256": FROZEN_REBOUND_ARTIFACT_SHA256,
            "policy": "fail_closed_on_artifact_field_preregistration_or_freeze_change",
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
    "BUCKET_PRIORITY_V4",
    "FIELD_LABELS_ZH",
    "REFERENCE_VERSION",
    "REQUIRED_V4_FIELD_COLUMNS",
    "SCHEMA_ID",
    "TimingSpecialistProgressiveRouteSpec",
    "aggregate_v4_comparison",
    "build_v4_bucket_counterfactual_positions",
    "build_three_bucket_iir_reference_v4",
    "prepare_progressive_specialist_field",
    "three_bucket_iir_reference_v4_contract",
]
