# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportCallInDefaultInitializer=false, reportMissingTypeStubs=false
# pyright: reportOperatorIssue=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnusedCallResult=false
"""Reproducible infrastructure sample: three specialist buckets over dynamic IIR.

The sample is intentionally separate from ``timing_strategy_router_v4``.  It
demonstrates how a future strategy may compose mutually ordered specialists
with one residual owner, apply one signed T+1 state machine, and compare the
result with the residual owner on an identical account ledger.  It grants no
production or canonical-router authority.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.market_state.downside_entry_orthogonal_veto import (
    downside_entry_jump_concentration,
)
from factor_lab.market_state.research.causal_filter_iir_p13_slow_ownership_regime_v3 import (
    build_context as build_dynamic_iir_context,
)
from factor_lab.market_state.research.ols_paper_explosive_bucket_battle_v1 import (
    build_candidate_paths,
    enforce_true_t_plus_one,
)

SCHEMA_ID: Final[str] = "market_state_timing_three_bucket_iir_reference@1.0"
REFERENCE_VERSION: Final[str] = "timing_three_bucket_iir_reference_v1"
FROZEN_REBOUND_ARTIFACT_SHA256: Final[str] = (
    "76ce3b26657a9662636e6640557ac3dc0d1f8a515c972186c18ad080247405f9"
)
BUCKET_PRIORITY: Final[tuple[str, ...]] = (
    "crash_rebound_breadth_gated",
    "paper_s2_up_q925",
    "ols_w12_w24_down_jump_gated",
    "dynamic_iir_residual",
)


@dataclass(frozen=True, slots=True)
class TimingThreeBucketIIRReferenceSpec:
    """Frozen parameters used by the V1 infrastructure sample."""

    rebound_breadth_minimum: float = 0.35
    paper_up_tail_quantile: float = 0.925
    downside_jump_lookback_bars: int = 12
    downside_jump_minimum: float = 0.19
    buy_cost_bps: float = 1.0
    sell_cost_bps: float = 6.0
    annual_trading_days: float = 252.0

    def __post_init__(self) -> None:
        if not 0.0 < self.rebound_breadth_minimum < 1.0:
            raise ValueError("rebound breadth minimum must lie in (0, 1)")
        if not 0.5 < self.paper_up_tail_quantile < 1.0:
            raise ValueError("paper up tail quantile must lie in (0.5, 1)")
        if self.downside_jump_lookback_bars < 3:
            raise ValueError("downside jump lookback must be at least three bars")
        if not 0.0 < self.downside_jump_minimum < 1.0:
            raise ValueError("downside jump minimum must lie in (0, 1)")
        if min(self.buy_cost_bps, self.sell_cost_bps) < 0.0:
            raise ValueError("transaction costs must be non-negative")


FIELD_LABELS_ZH: Final[dict[str, str]] = {
    "dynamic_iir_desired_position": "动态IIR严格先验目标仓位",
    "dynamic_iir_t1_position": "纯动态IIR真实T+1仓位",
    "crash_rebound_raw": "冻结暴跌反弹原始执行生命周期",
    "crash_rebound_prior_breadth": "暴跌反弹入场前一棒强上涨股票占比",
    "crash_rebound_gated": "截面宽度门后的完整暴跌反弹生命周期",
    "paper_s2_up_q925": "论文核S2上行Q0.925完整执行生命周期",
    "ols_down_decision": "OLS W12/W24下行收盘决策生命周期",
    "downside_jump_concentration_h12": "下行入场12棒跳变集中度",
    "ols_down_gated": "跳变集中度门后的OLS下行执行生命周期",
    "crash_rebound_claim": "暴跌反弹第一优先责任",
    "paper_up_claim": "论文核上涨严格余集责任",
    "ols_down_claim": "OLS下跌严格余集责任",
    "residual_iir_claim": "三桶后动态IIR剩余责任",
    "combo_desired_position": "三桶加动态IIR组合目标仓位",
    "combo_t1_position": "三桶加动态IIR真实T+1仓位",
    "reference_version": "基础设施样板版本",
    "runtime_uses_future": "运行时是否使用未来数据",
    "research_authority": "研究样板权限",
    "production_authority": "生产权限",
}


def _validated_index(causal_ohlc: pd.DataFrame, *, name: str) -> pd.DatetimeIndex:
    required = {"timestamp", "open", "high", "low", "close"}
    missing = sorted(required.difference(causal_ohlc.columns))
    if missing:
        raise KeyError(f"{name} missing OHLC columns: {missing}")
    index = pd.DatetimeIndex(pd.to_datetime(causal_ohlc["timestamp"], errors="raise"))
    if index.empty or index.has_duplicates or not index.is_monotonic_increasing:
        raise ValueError(f"{name} timestamps must be non-empty, unique, and ordered")
    return index


def align_strictly_prior_60m_desired_to_15m(
    execution_index: pd.DatetimeIndex,
    desired_60m: pd.Series,
) -> pd.Series:
    """Expose a 60m close decision only on a strictly later 15m open."""

    if execution_index.empty or execution_index.has_duplicates or not execution_index.is_monotonic_increasing:
        raise ValueError("execution index must be non-empty, unique, and ordered")
    if not isinstance(desired_60m.index, pd.DatetimeIndex):
        raise TypeError("60m desired position must use a DatetimeIndex")
    if desired_60m.index.has_duplicates or not desired_60m.index.is_monotonic_increasing:
        raise ValueError("60m desired index must be unique and ordered")
    source = (
        pd.to_numeric(desired_60m, errors="raise")
        .rename("desired_position")
        .rename_axis("decision_timestamp")
        .reset_index()
    )
    aligned = pd.merge_asof(
        pd.DataFrame({"execution_timestamp": execution_index}),
        source,
        left_on="execution_timestamp",
        right_on="decision_timestamp",
        direction="backward",
        allow_exact_matches=False,
    )
    return pd.Series(
        aligned["desired_position"].fillna(0.0).clip(-1.0, 1.0).to_numpy(float),
        index=execution_index,
        name="dynamic_iir_desired_position",
    )


def enforce_signed_true_t_plus_one(executable_target: pd.Series) -> pd.Series:
    """Apply one A-share same-session exit lock to a signed target path."""

    owner = pd.Series("target", index=executable_target.index, dtype="string")
    return enforce_signed_true_t_plus_one_with_owner(executable_target, owner)["t1_position"]


def enforce_signed_true_t_plus_one_with_owner(
    executable_target: pd.Series,
    target_owner: pd.Series,
) -> pd.DataFrame:
    """Apply the signed T+1 lock while carrying causal position provenance.

    An owner hand-off that keeps the same signed target needs no transaction and
    therefore becomes effective immediately.  A flat/reversal request that is
    blocked by the same-session T+1 rule retains both the held position and its
    previous owner until the transition is executable.
    """

    if not isinstance(executable_target.index, pd.DatetimeIndex):
        raise TypeError("signed T+1 target must use a DatetimeIndex")
    if not executable_target.index.equals(target_owner.index):
        raise ValueError("signed T+1 target and owner indexes must match")
    target = pd.to_numeric(executable_target, errors="raise").fillna(0.0).clip(-1.0, 1.0)
    owners = target_owner.astype("string").fillna("none")
    invalid_owner = target.ne(0.0) & owners.str.strip().isin(["", "none"])
    if bool(invalid_owner.any()):
        raise ValueError("every non-flat signed target must have a non-empty owner")
    current = 0.0
    entry_date: object | None = None
    values = np.zeros(len(target), dtype=float)
    owner_values = np.full(len(target), "none", dtype=object)
    current_owner = "none"
    for location, ((timestamp, wanted_value), wanted_owner_value) in enumerate(
        zip(target.items(), owners.to_numpy(), strict=True)
    ):
        wanted = float(wanted_value)
        wanted_owner = str(wanted_owner_value)
        trade_date = timestamp.date()
        if wanted == current:
            current_owner = wanted_owner if current != 0.0 else "none"
        else:
            if current == 0.0:
                current = wanted
                entry_date = trade_date if current != 0.0 else None
                current_owner = wanted_owner if current != 0.0 else "none"
            elif entry_date != trade_date:
                current = wanted
                entry_date = trade_date if current != 0.0 else None
                current_owner = wanted_owner if current != 0.0 else "none"
        values[location] = current
        owner_values[location] = current_owner
    return pd.DataFrame(
        {
            "t1_position": pd.Series(values, index=target.index, dtype=float),
            "t1_owner": pd.Series(owner_values, index=target.index, dtype="string"),
        },
        index=target.index,
    )


def gate_complete_lifecycle_by_entry(
    active: pd.Series,
    entry_keep: pd.Series,
) -> pd.Series:
    """Keep or reject a complete lifecycle using only its entry observation."""

    if not active.index.equals(entry_keep.index):
        raise ValueError("lifecycle and entry gate indexes must match")
    lifecycle = active.astype(bool)
    starts = lifecycle & ~lifecycle.shift(1, fill_value=False)
    groups = starts.cumsum()
    accepted_at_start = pd.Series(
        np.where(starts.to_numpy(bool), entry_keep.to_numpy(bool), False),
        index=lifecycle.index,
        dtype=bool,
    )
    accepted = accepted_at_start.groupby(groups).transform("max").astype(bool)
    return (lifecycle & accepted).rename("gated_lifecycle")


def compose_three_bucket_iir_reference(
    *,
    dynamic_iir_desired: pd.Series,
    crash_rebound_raw: pd.Series,
    rebound_breadth_by_completed_bar: pd.Series,
    paper_up_executable: pd.Series,
    ols_down_decision: pd.Series,
    downside_jump_concentration: pd.Series,
    spec: TimingThreeBucketIIRReferenceSpec = TimingThreeBucketIIRReferenceSpec(),
) -> pd.DataFrame:
    """Compose frozen specialist inputs in priority order over dynamic IIR."""

    index = dynamic_iir_desired.index
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError("reference composition requires a DatetimeIndex")
    inputs = {
        "crash_rebound_raw": crash_rebound_raw,
        "rebound_breadth_by_completed_bar": rebound_breadth_by_completed_bar,
        "paper_up_executable": paper_up_executable,
        "ols_down_decision": ols_down_decision,
        "downside_jump_concentration": downside_jump_concentration,
    }
    for name, series in inputs.items():
        if not series.index.equals(index):
            raise ValueError(f"{name} does not share the reference index")

    crash_raw = crash_rebound_raw.astype(bool)
    crash_starts = crash_raw & ~crash_raw.shift(1, fill_value=False)
    prior_breadth = pd.to_numeric(
        rebound_breadth_by_completed_bar, errors="coerce"
    ).shift(1)
    crash_entry_keep = crash_starts & prior_breadth.ge(
        spec.rebound_breadth_minimum
    )
    crash_gated = gate_complete_lifecycle_by_entry(crash_raw, crash_entry_keep)

    down_decision = ols_down_decision.astype(bool)
    down_starts = down_decision & ~down_decision.shift(1, fill_value=False)
    jump = pd.to_numeric(downside_jump_concentration, errors="coerce")
    down_entry_keep = down_starts & jump.ge(spec.downside_jump_minimum)
    down_decision_gated = gate_complete_lifecycle_by_entry(
        down_decision,
        down_entry_keep,
    )
    down_executable = enforce_true_t_plus_one(down_decision_gated, side="down")
    up_executable = pd.to_numeric(paper_up_executable, errors="raise").gt(0.0)

    crash_claim = crash_gated
    up_claim = up_executable & ~crash_claim
    down_claim = down_executable.lt(0.0) & ~crash_claim & ~up_claim
    residual_claim = ~(crash_claim | up_claim | down_claim)

    combo_desired = pd.to_numeric(dynamic_iir_desired, errors="raise").copy()
    combo_desired.loc[down_claim] = -1.0
    combo_desired.loc[up_claim] = 1.0
    combo_desired.loc[crash_claim] = 1.0
    baseline_position = enforce_signed_true_t_plus_one(dynamic_iir_desired)
    combo_position = enforce_signed_true_t_plus_one(combo_desired)

    owner_count = (
        crash_claim.astype(int) + up_claim.astype(int) + down_claim.astype(int)
    )
    if bool(owner_count.gt(1).any()):
        raise RuntimeError("three specialist bucket claims overlap")
    if not residual_claim.equals(owner_count.eq(0)):
        raise RuntimeError("residual IIR claim is not the specialist complement")

    output = pd.DataFrame(
        {
            "dynamic_iir_desired_position": dynamic_iir_desired,
            "dynamic_iir_t1_position": baseline_position,
            "crash_rebound_raw": crash_raw,
            "crash_rebound_prior_breadth": prior_breadth,
            "crash_rebound_gated": crash_gated,
            "paper_s2_up_q925": up_executable,
            "ols_down_decision": down_decision,
            "downside_jump_concentration_h12": jump,
            "ols_down_gated": down_executable.lt(0.0),
            "crash_rebound_claim": crash_claim,
            "paper_up_claim": up_claim,
            "ols_down_claim": down_claim,
            "residual_iir_claim": residual_claim,
            "combo_desired_position": combo_desired,
            "combo_t1_position": combo_position,
            "reference_version": REFERENCE_VERSION,
            "runtime_uses_future": False,
            "research_authority": True,
            "production_authority": False,
        },
        index=index,
    )
    output.attrs["field_labels_zh"] = {
        column: FIELD_LABELS_ZH[column] for column in output.columns
    }
    output.attrs["formula_contract"] = three_bucket_iir_reference_contract(spec)
    return output


def build_three_bucket_iir_reference(
    causal_15m_ohlc: pd.DataFrame,
    causal_60m_ohlc: pd.DataFrame,
    *,
    frozen_crash_rebound_executable: pd.Series,
    rebound_breadth_by_completed_bar: pd.Series,
    allowed_end_exclusive: pd.Timestamp,
    spec: TimingThreeBucketIIRReferenceSpec = TimingThreeBucketIIRReferenceSpec(),
) -> pd.DataFrame:
    """Build the complete sample from frozen upstreams and causal market data."""

    index_15m = _validated_index(causal_15m_ohlc, name="15m carrier")
    _validated_index(causal_60m_ohlc, name="60m carrier")
    if not frozen_crash_rebound_executable.index.equals(index_15m):
        raise ValueError("frozen crash rebound upstream does not align to 15m")
    if not rebound_breadth_by_completed_bar.index.equals(index_15m):
        raise ValueError("rebound breadth does not align to 15m")

    _, _, _, route_60m = build_dynamic_iir_context(
        causal_60m_ohlc,
        allowed_end=allowed_end_exclusive,
    )
    dynamic_iir_desired = align_strictly_prior_60m_desired_to_15m(
        index_15m,
        route_60m["route_desired_position"],
    )
    paths, _, _, _ = build_candidate_paths(
        causal_15m_ohlc,
        tail_quantiles=(spec.paper_up_tail_quantile,),
        maximum_timestamp_exclusive=allowed_end_exclusive,
    )
    suffix = f"q{int(round(spec.paper_up_tail_quantile * 1000)):03d}"
    paper_up = paths[f"paper_native_up_{suffix}"].executable_position
    ols_down = paths["ols_native_down"].decision_active
    jump = downside_entry_jump_concentration(
        causal_15m_ohlc,
        lookback_bars=spec.downside_jump_lookback_bars,
    ).reindex(index_15m)
    return compose_three_bucket_iir_reference(
        dynamic_iir_desired=dynamic_iir_desired,
        crash_rebound_raw=frozen_crash_rebound_executable.astype(bool),
        rebound_breadth_by_completed_bar=rebound_breadth_by_completed_bar,
        paper_up_executable=paper_up,
        ols_down_decision=ols_down,
        downside_jump_concentration=jump,
        spec=spec,
    )


def signed_position_ledger(
    open_price: pd.Series,
    position: pd.Series,
    *,
    spec: TimingThreeBucketIIRReferenceSpec = TimingThreeBucketIIRReferenceSpec(),
) -> pd.DataFrame:
    """Return one common next-open ledger for signed positions."""

    if not open_price.index.equals(position.index):
        raise ValueError("open price and position indexes must match")
    forward = np.log(open_price.shift(-1) / open_price)
    change = pd.to_numeric(position, errors="raise").diff().fillna(position)
    cost = change.clip(lower=0.0) * (spec.buy_cost_bps / 10_000.0) + (
        -change.clip(upper=0.0)
    ) * (spec.sell_cost_bps / 10_000.0)
    gross = position * forward
    return pd.DataFrame(
        {
            "position": position,
            "forward_open_log_return": forward,
            "gross_log_return": gross,
            "cost_log_return": cost,
            "net_log_return": gross - cost,
            "turnover_units": change.abs(),
        },
        index=open_price.index,
    )


def _completed_trade_metrics(
    open_price: pd.Series,
    position: pd.Series,
    *,
    scope_start: pd.Timestamp,
    scope_end_exclusive: pd.Timestamp,
    spec: TimingThreeBucketIIRReferenceSpec,
) -> dict[str, float | int]:
    positions = position.to_numpy(float)
    opens = open_price.to_numpy(float)
    logs: list[float] = []
    holds: list[int] = []
    active_sign = 0.0
    start_location = -1
    for location, sign in enumerate(positions):
        if sign == active_sign:
            continue
        if (
            active_sign != 0.0
            and start_location >= 0
            and position.index[start_location] >= scope_start
            and position.index[location] < scope_end_exclusive
        ):
            gross = active_sign * math.log(
                opens[location] / opens[start_location]
            )
            logs.append(
                gross - (spec.buy_cost_bps + spec.sell_cost_bps) / 10_000.0
            )
            holds.append(location - start_location)
        active_sign = sign
        start_location = location if sign != 0.0 else -1
    wins = [value for value in logs if value > 0.0]
    losses = [value for value in logs if value < 0.0]
    return {
        "completed_trade_count": len(logs),
        "win_rate": len(wins) / len(logs) if logs else 0.0,
        "average_trade_log_return": float(np.mean(logs)) if logs else 0.0,
        "payoff_ratio": (
            float(np.mean(wins)) / abs(float(np.mean(losses)))
            if wins and losses
            else 0.0
        ),
        "average_hold_15m_bars": float(np.mean(holds)) if holds else 0.0,
    }


def aggregate_account_metrics(
    open_price: pd.Series,
    position: pd.Series,
    *,
    start: pd.Timestamp,
    end_exclusive: pd.Timestamp,
    spec: TimingThreeBucketIIRReferenceSpec = TimingThreeBucketIIRReferenceSpec(),
    isolate_end_boundary: bool = False,
) -> dict[str, float | int | str]:
    """Compute aggregate-only account metrics without calendar decomposition.

    ``isolate_end_boundary`` excludes a return whose starting bar lies inside
    the interval but whose next open lies at or beyond ``end_exclusive``.  It
    makes a chronological block invariant to whether the caller has already
    loaded the following block.  The default remains backward compatible for
    previously published whole-period packages.
    """

    ledger = signed_position_ledger(open_price, position, spec=spec)
    mask = (
        ledger.index.to_series().ge(start)
        & ledger.index.to_series().lt(end_exclusive)
        & ledger["forward_open_log_return"].notna()
    )
    if isolate_end_boundary:
        next_timestamp = pd.Series(ledger.index, index=ledger.index).shift(-1)
        mask &= next_timestamp.lt(end_exclusive)
    local = ledger.loc[mask]
    if local.empty:
        raise ValueError("aggregate evaluation scope is empty")
    daily = local["net_log_return"].groupby(local.index.normalize()).sum()
    daily_standard_deviation = float(daily.std(ddof=0))
    equity_log = local["net_log_return"].cumsum()
    drawdown = np.exp(equity_log - equity_log.cummax()) - 1.0
    elapsed_years = max(
        (local.index[-1] - local.index[0]).total_seconds()
        / (365.2425 * 86_400.0),
        1.0 / 365.2425,
    )
    net_log_return = float(local["net_log_return"].sum())
    local_position = local["position"]
    return {
        "evaluation_start": str(local.index[0]),
        "evaluation_end": str(local.index[-1]),
        "trading_days": int(len(daily)),
        "net_log_return": net_log_return,
        "cumulative_return": math.exp(net_log_return) - 1.0,
        "annualized_return": math.exp(net_log_return / elapsed_years) - 1.0,
        "annualized_sharpe": (
            float(
                daily.mean()
                / daily_standard_deviation
                * math.sqrt(spec.annual_trading_days)
            )
            if daily_standard_deviation > 0.0
            else 0.0
        ),
        "max_drawdown": float(drawdown.min()),
        "gross_log_return": float(local["gross_log_return"].sum()),
        "transaction_cost_log": float(local["cost_log_return"].sum()),
        "exposure_share": float(local_position.ne(0.0).mean()),
        "long_exposure_share": float(local_position.gt(0.0).mean()),
        "short_exposure_share": float(local_position.lt(0.0).mean()),
        "turnover_units": float(local["turnover_units"].sum()),
        **_completed_trade_metrics(
            open_price,
            position,
            scope_start=start,
            scope_end_exclusive=end_exclusive,
            spec=spec,
        ),
    }


def aggregate_reference_comparison(
    open_price: pd.Series,
    position_panel: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end_exclusive: pd.Timestamp,
    spec: TimingThreeBucketIIRReferenceSpec = TimingThreeBucketIIRReferenceSpec(),
) -> dict[str, object]:
    """Compare pure dynamic IIR and the complete reference on one ledger."""

    baseline = aggregate_account_metrics(
        open_price,
        position_panel["dynamic_iir_t1_position"],
        start=start,
        end_exclusive=end_exclusive,
        spec=spec,
    )
    combo = aggregate_account_metrics(
        open_price,
        position_panel["combo_t1_position"],
        start=start,
        end_exclusive=end_exclusive,
        spec=spec,
    )
    net_delta = float(combo["net_log_return"]) - float(baseline["net_log_return"])
    comparison = {
        "net_log_return_delta": net_delta,
        "terminal_wealth_lift": math.exp(net_delta) - 1.0,
        "annualized_return_delta": float(combo["annualized_return"])
        - float(baseline["annualized_return"]),
        "annualized_sharpe_delta": float(combo["annualized_sharpe"])
        - float(baseline["annualized_sharpe"]),
        "max_drawdown_improvement": float(combo["max_drawdown"])
        - float(baseline["max_drawdown"]),
        "exposure_share_delta": float(combo["exposure_share"])
        - float(baseline["exposure_share"]),
        "completed_trade_count_delta": int(combo["completed_trade_count"])
        - int(baseline["completed_trade_count"]),
    }
    return {
        "schema_id": "market_state_three_bucket_iir_aggregate_comparison@1.0",
        "aggregate_only": True,
        "details_exposed": False,
        "pure_dynamic_iir": baseline,
        "three_bucket_plus_dynamic_iir": combo,
        "comparison": comparison,
        "verdict": {
            "return_improved": net_delta > 0.0,
            "sharpe_improved": comparison["annualized_sharpe_delta"] > 0.0,
            "drawdown_improved": comparison["max_drawdown_improvement"] > 0.0,
            "infrastructure_sample_positive": (
                net_delta > 0.0
                and comparison["annualized_sharpe_delta"] > 0.0
            ),
            "production_gate_passed": False,
        },
    }


def three_bucket_iir_reference_contract(
    spec: TimingThreeBucketIIRReferenceSpec = TimingThreeBucketIIRReferenceSpec(),
) -> dict[str, object]:
    """Return the complete reproducibility and authority contract."""

    return {
        "schema_id": SCHEMA_ID,
        "reference_version": REFERENCE_VERSION,
        "reference_role": "infrastructure_level_strategy_composition_sample",
        "does_not_supersede": [
            "timing_strategy_router_v4",
            "timing_explosive_layer_v3",
        ],
        "bucket_priority": list(BUCKET_PRIORITY),
        "spec": asdict(spec),
        "components": {
            "crash_rebound_breadth_gated": {
                "upstream": "timing_explosive_layer_v3.crash_rebound_executable",
                "frozen_upstream_artifact_sha256": FROZEN_REBOUND_ARTIFACT_SHA256,
                "entry_gate": "strictly_prior_intraday_bar_strong_up_share >= 0.35",
                "gate_scope": "entry_only_then_keep_or_reject_complete_lifecycle",
                "side": "up",
            },
            "paper_s2_up_q925": {
                "upstream": "ols_paper_explosive_bucket_battle_v1.paper_native_up_q925",
                "score": "sqrt(32)*EWM32(raw_15m_return)",
                "threshold": "lagged_33_session_rolling_abs_score_quantile_0.925",
                "exit": "directional_score_zero_cross",
                "side": "up",
            },
            "ols_w12_w24_down_jump_gated": {
                "upstream": "ols_paper_explosive_bucket_battle_v1.ols_native_down",
                "entry_gate": "max_abs_log_return_h12/sum_abs_log_return_h12 >= 0.19",
                "gate_scope": "entry_only_then_keep_or_reject_complete_lifecycle",
                "exit": "two_opposite_closes_outside_frozen_OLS_channel",
                "side": "down",
            },
            "dynamic_iir_residual": {
                "upstream": "causal_filter_iir_p13_slow_ownership_regime_v3",
                "periods": [13, 36],
                "q": 0.8,
                "carrier": "60m",
                "alignment": "strictly_prior_60m_close_to_current_15m_open",
            },
        },
        "composition": (
            "crash rebound first; paper S2 up on its residual; gated OLS down "
            "on the second residual; all remaining bars return to dynamic IIR"
        ),
        "execution": {
            "carrier": "15m",
            "return_clock": "current_open_to_next_open",
            "true_t_plus_one": True,
            "signed_position": True,
            "buy_cost_bps": spec.buy_cost_bps,
            "sell_cost_bps": spec.sell_cost_bps,
            "single_final_t1_state_machine": True,
        },
        "evaluation": {
            "development_period": "2009-2017",
            "repeat_audit_period": "2018-2020",
            "aggregate_blackbox_period": "2021-2026",
            "aggregate_blackbox_details_forbidden": True,
            "comparison_baseline": "pure_dynamic_iir_p13_p36",
        },
        "known_reproducibility_boundary": {
            "frozen_rebound_artifact_is_authoritative": True,
            "current_source_rematerialization_matches_frozen_artifact": False,
            "policy": "fail_closed_on_artifact_digest_change",
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
    "BUCKET_PRIORITY",
    "FIELD_LABELS_ZH",
    "FROZEN_REBOUND_ARTIFACT_SHA256",
    "REFERENCE_VERSION",
    "SCHEMA_ID",
    "TimingThreeBucketIIRReferenceSpec",
    "aggregate_account_metrics",
    "aggregate_reference_comparison",
    "align_strictly_prior_60m_desired_to_15m",
    "build_three_bucket_iir_reference",
    "compose_three_bucket_iir_reference",
    "enforce_signed_true_t_plus_one",
    "gate_complete_lifecycle_by_entry",
    "signed_position_ledger",
    "three_bucket_iir_reference_contract",
]
