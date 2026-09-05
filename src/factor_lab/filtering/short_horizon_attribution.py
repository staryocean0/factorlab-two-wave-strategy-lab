"""Failure attribution helpers for short-horizon filter timing candidates.

The workflow uses this layer after walk-forward validation and signal-governance
review.  Its purpose is diagnostic rather than exploratory: explain *why* a
1min/5min candidate was parked or downgraded before governance thresholds are
tuned from the evidence.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd

ShortHorizonRootCause = Literal[
    "microstructure_noise",
    "overnight_gap_risk",
    "payoff_or_winrate_defect",
    "cost_amplified_overtrading",
    "execution_overlay_candidate",
]

GovernanceLoopAction = Literal[
    "retry_with_governance_experiments",
    "promote_to_execution_overlay",
    "park_or_abandon",
]

TradeBucketKind = Literal[
    "overnight_gap_loss",
    "micro_whipsaw_loss",
    "adverse_excursion_loss",
    "slow_bleed_loss",
    "ordinary_loss",
    "trend_capture_win",
    "overnight_gap_win",
    "quick_reversal_win",
    "ordinary_win",
]


@dataclass(frozen=True, slots=True)
class TradeAttributionRow:
    """One completed long/cash interval."""

    entry_time: str
    exit_time: str
    gross_return: float
    net_return_estimate: float
    hold_bars: int
    is_win: bool
    is_whipsaw: bool
    is_overnight: bool
    worst_adverse_excursion: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ShortHorizonFailureAttribution:
    """Summary card for one short-horizon timing candidate."""

    candidate_id: str
    period: str
    filter_mode: str
    center_period_days: float | None
    sample_start: str
    sample_end: str
    trade_count: int
    win_rate: float | None
    avg_win: float | None
    avg_loss: float | None
    payoff_ratio: float | None
    expectancy: float | None
    median_hold_bars: float | None
    turnover_per_year_estimate: float | None
    whipsaw_loss_share: float
    overnight_loss_share: float
    cost_drag_return_sum: float
    gross_return_sum: float
    net_return_sum_estimate: float
    root_cause: ShortHorizonRootCause
    root_cause_zh: str
    optimization_hypotheses_zh: list[str]
    top_losses: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GovernanceFeedbackLoopConfig:
    """Stop conditions for attribution-driven governance loops.

    The loop is deliberately bounded.  Attribution may suggest new governance
    experiments, but each experiment must be portable across similar short
    horizon candidates and must be re-validated by walk-forward.
    """

    max_iterations: int = 3
    min_oos_cagr: float = 0.05
    max_oos_mdd: float = -0.25
    min_win_rate: float = 0.42
    min_payoff_ratio: float = 1.25
    max_turnover_per_year: float = 800.0
    max_whipsaw_loss_share: float = 0.25
    max_overnight_loss_share: float = 0.08

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GovernanceFeedbackLoopDecision:
    """Decision for the next governance-loop iteration."""

    action: GovernanceLoopAction
    iteration: int
    rationale_zh: str
    proposed_experiments_zh: list[str]
    stop_reasons_zh: list[str]
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TradeAttributionBucket:
    """Aggregated PnL bucket for loss-first/profit-preserving optimization."""

    bucket: TradeBucketKind
    side: Literal["loss", "profit"]
    trade_count: int
    gross_return_sum: float
    gross_return_mean: float
    share_of_side_abs_pnl: float
    representative_trades: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LossProfitOptimizationPlan:
    """Plan that suppresses dominant loss buckets while preserving profit buckets."""

    loss_buckets: list[dict[str, object]]
    profit_buckets: list[dict[str, object]]
    target_loss_buckets: list[str]
    preserve_profit_buckets: list[str]
    experiments_zh: list[str]
    guardrails_zh: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def analyze_short_horizon_position_frame(
    frame: pd.DataFrame,
    *,
    candidate_id: str,
    period: str,
    filter_mode: str,
    center_period_days: float | None = None,
    bars_per_year: float,
    buy_cost_bps: float = 1.0,
    sell_cost_bps: float = 6.0,
    whipsaw_bars: int = 5,
    top_loss_count: int = 8,
) -> ShortHorizonFailureAttribution:
    """Attribute why a short-horizon candidate is fragile.

    ``frame`` must contain ``timestamp``, ``close`` and ``position``.  Position
    is interpreted as the already-executed long/cash state.  Costs are estimated
    per completed round-trip; this is intentionally a diagnostic approximation,
    not a replacement for the canonical backtester.
    """

    required = {"timestamp", "close", "position"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"position frame missing required columns: {sorted(missing)}")

    work = frame.loc[:, ["timestamp", "close", "position"]].copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"])
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    work["position"] = pd.to_numeric(work["position"], errors="coerce").fillna(0.0)
    work = work.dropna(subset=["timestamp", "close"]).sort_values("timestamp")
    if work.empty:
        raise ValueError("position frame has no usable rows")

    trades = extract_long_cash_trades(
        work,
        buy_cost_bps=buy_cost_bps,
        sell_cost_bps=sell_cost_bps,
        whipsaw_bars=whipsaw_bars,
    )
    returns = np.array([row.gross_return for row in trades], dtype=float)
    net_returns = np.array([row.net_return_estimate for row in trades], dtype=float)
    wins = returns[returns > 0.0]
    losses = returns[returns <= 0.0]
    years = len(work) / bars_per_year if bars_per_year > 0 else 0.0
    cost_drag = returns - net_returns
    whipsaw_loss_count = sum(1 for row in trades if (not row.is_win) and row.is_whipsaw)
    overnight_loss_count = sum(
        1 for row in trades if (not row.is_win) and row.is_overnight
    )
    trade_count = len(trades)
    win_rate = float(len(wins) / trade_count) if trade_count else None
    avg_win = float(wins.mean()) if len(wins) else None
    avg_loss = float(losses.mean()) if len(losses) else None
    payoff = (
        float(avg_win / abs(avg_loss))
        if avg_win is not None and avg_loss is not None and avg_loss < 0.0
        else None
    )
    expectancy = float(returns.mean()) if trade_count else None
    turnover = float((trade_count * 2.0) / years) if years > 0.0 else None
    root_cause = classify_short_horizon_root_cause(
        trade_count=trade_count,
        win_rate=win_rate,
        payoff_ratio=payoff,
        whipsaw_loss_share=whipsaw_loss_count / trade_count if trade_count else 0.0,
        overnight_loss_share=overnight_loss_count / trade_count if trade_count else 0.0,
        turnover_per_year=turnover,
        cost_drag_return_sum=float(cost_drag.sum()) if trade_count else 0.0,
        gross_return_sum=float(returns.sum()) if trade_count else 0.0,
    )
    return ShortHorizonFailureAttribution(
        candidate_id=candidate_id,
        period=period,
        filter_mode=filter_mode,
        center_period_days=center_period_days,
        sample_start=str(work["timestamp"].iloc[0]),
        sample_end=str(work["timestamp"].iloc[-1]),
        trade_count=trade_count,
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        payoff_ratio=payoff,
        expectancy=expectancy,
        median_hold_bars=(
            float(np.median([row.hold_bars for row in trades])) if trades else None
        ),
        turnover_per_year_estimate=turnover,
        whipsaw_loss_share=whipsaw_loss_count / trade_count if trade_count else 0.0,
        overnight_loss_share=overnight_loss_count / trade_count if trade_count else 0.0,
        cost_drag_return_sum=float(cost_drag.sum()) if trade_count else 0.0,
        gross_return_sum=float(returns.sum()) if trade_count else 0.0,
        net_return_sum_estimate=float(net_returns.sum()) if trade_count else 0.0,
        root_cause=root_cause,
        root_cause_zh=root_cause_label_zh(root_cause),
        optimization_hypotheses_zh=optimization_hypotheses(root_cause),
        top_losses=[
            row.to_dict()
            for row in sorted(trades, key=lambda item: item.gross_return)[
                :top_loss_count
            ]
        ],
    )


def extract_long_cash_trades(
    frame: pd.DataFrame,
    *,
    buy_cost_bps: float,
    sell_cost_bps: float,
    whipsaw_bars: int,
) -> list[TradeAttributionRow]:
    """Extract completed long intervals from an executed position frame."""

    pos = frame["position"].fillna(0.0).clip(0.0, 1.0).to_numpy(dtype=float)
    close = frame["close"].to_numpy(dtype=float)
    times = pd.to_datetime(frame["timestamp"]).to_numpy()
    rows: list[TradeAttributionRow] = []
    in_position = False
    entry_idx = 0
    round_trip_cost = (buy_cost_bps + sell_cost_bps) / 10000.0
    for idx, value in enumerate(pos):
        if not in_position and value > 0.5:
            in_position = True
            entry_idx = idx
        elif in_position and value <= 0.5:
            rows.append(
                _trade_row(
                    entry_idx,
                    idx,
                    close=close,
                    times=times,
                    round_trip_cost=round_trip_cost,
                    whipsaw_bars=whipsaw_bars,
                )
            )
            in_position = False
    if in_position and len(frame) > entry_idx:
        rows.append(
            _trade_row(
                entry_idx,
                len(frame) - 1,
                close=close,
                times=times,
                round_trip_cost=round_trip_cost,
                whipsaw_bars=whipsaw_bars,
            )
        )
    return rows


def classify_short_horizon_root_cause(
    *,
    trade_count: int,
    win_rate: float | None,
    payoff_ratio: float | None,
    whipsaw_loss_share: float,
    overnight_loss_share: float,
    turnover_per_year: float | None,
    cost_drag_return_sum: float,
    gross_return_sum: float,
) -> ShortHorizonRootCause:
    """Classify the dominant failure mode using portable thresholds."""

    if trade_count == 0:
        return "payoff_or_winrate_defect"
    if overnight_loss_share >= 0.08:
        return "overnight_gap_risk"
    if whipsaw_loss_share >= 0.25:
        return "microstructure_noise"
    if (
        turnover_per_year is not None
        and turnover_per_year >= 500.0
        and cost_drag_return_sum >= max(0.25 * abs(gross_return_sum), 0.05)
    ):
        return "cost_amplified_overtrading"
    if (win_rate is not None and win_rate < 0.40) or (
        payoff_ratio is not None and payoff_ratio < 1.2
    ):
        return "payoff_or_winrate_defect"
    return "execution_overlay_candidate"


def root_cause_label_zh(root_cause: ShortHorizonRootCause) -> str:
    labels = {
        "microstructure_noise": "微结构/横盘噪声导致反复小亏。",
        "overnight_gap_risk": "隔夜或开盘跳空风险重写了短周期信号。",
        "payoff_or_winrate_defect": "胜率或盈亏比结构不足，信号本身偏薄。",
        "cost_amplified_overtrading": "高换手把原本很薄的毛优势放大为成本问题。",
        "execution_overlay_candidate": "不适合独立定方向，但可能适合作为执行微调层。",
    }
    return labels[root_cause]


def optimization_hypotheses(root_cause: ShortHorizonRootCause) -> list[str]:
    common = [
        "不得只针对单个频点调参；治理规则必须能迁移到同类短周期候选。",
        "优化后必须重跑 walk-forward，并保留优化前图形和逐笔归因作为对照。",
    ]
    by_cause = {
        "microstructure_noise": [
            "增加零轴附近不交易/组件强度阈值，过滤 bandpass component 的毛边翻转。",
            "增加统一冷却期或最小持仓，减少 1–5 根K内反复买卖。",
            "若独立仓位层仍持续失败，转入 role_conversion_test：" +
            "只作为高一级趋势下的执行 overlay 测试边际贡献。",
        ],
        "overnight_gap_risk": [
            "测试 session_risk_governance：不隔夜、尾盘降仓/不新开仓、" +
            "开盘前N根K等待重新确认。",
            "短周期执行层接受高一级 lowpass/bandpass 方向门禁后再入场。",
        ],
        "payoff_or_winrate_defect": [
            "先引入高一级趋势门禁提高胜率，再评估是否牺牲过多盈亏比。",
            "用交易图检查买点是否系统性滞后，必要时测试低滞后确认而非缩短周期。",
            "若胜率/盈亏比无法同时改善，转入 role_conversion_test，" +
            "而不是继续独立仓位层单点调参。",
        ],
        "cost_amplified_overtrading": [
            "把该候选降级为小权重执行 overlay，或加入换手预算后重新排序。",
            "测试成本压力场景；若毛收益主要来自高换手微利，直接删除。",
        ],
        "execution_overlay_candidate": [
            "不作为独立仓位层；仅在 60min 主方向允许时优化买卖点。",
            "与主组合做边际贡献测试：只看是否改善入场/退出，不单看独立 CAGR。",
        ],
    }
    return by_cause[root_cause] + common


def summarize_attribution_cards(
    cards: Sequence[ShortHorizonFailureAttribution],
) -> list[dict[str, Any]]:
    """Return compact rows suitable for Markdown/CSV reports."""

    rows: list[dict[str, Any]] = []
    for card in cards:
        rows.append(
            {
                "candidate_id": card.candidate_id,
                "period": card.period,
                "mode": card.filter_mode,
                "T_days": card.center_period_days,
                "trades": card.trade_count,
                "win_rate": card.win_rate,
                "avg_win": card.avg_win,
                "avg_loss": card.avg_loss,
                "payoff": card.payoff_ratio,
                "median_hold_bars": card.median_hold_bars,
                "turnover_est": card.turnover_per_year_estimate,
                "whipsaw_loss_share": card.whipsaw_loss_share,
                "overnight_loss_share": card.overnight_loss_share,
                "root_cause": card.root_cause,
                "root_cause_zh": card.root_cause_zh,
            }
        )
    return rows


def build_loss_profit_optimization_plan(
    trades: Sequence[TradeAttributionRow],
    *,
    top_loss_bucket_count: int = 3,
    top_profit_bucket_count: int = 2,
) -> LossProfitOptimizationPlan:
    """Build a loss-first, profit-preserving governance plan.

    The workflow should first identify which buckets produce the largest
    losses, then propose portable interventions for those buckets.  Each
    intervention is paired with guardrails that protect the dominant profit
    buckets, so optimization does not simply delete the trades that make the
    factor valuable.
    """

    buckets = bucket_trade_attributions(trades)
    loss_buckets = [item for item in buckets if item.side == "loss"]
    profit_buckets = [item for item in buckets if item.side == "profit"]
    loss_buckets = sorted(
        loss_buckets, key=lambda item: item.share_of_side_abs_pnl, reverse=True
    )
    profit_buckets = sorted(
        profit_buckets, key=lambda item: item.share_of_side_abs_pnl, reverse=True
    )
    target_losses = loss_buckets[:top_loss_bucket_count]
    preserve_profits = profit_buckets[:top_profit_bucket_count]
    experiments: list[str] = []
    for bucket in target_losses:
        experiments.extend(_experiments_for_loss_bucket(bucket.bucket))
    guardrails = [
        "任何治理实验必须同时报告目标亏损桶压缩幅度和主要盈利桶保留率。",
        "若盈利桶保留率低于 70%，即使总回撤改善，也不得直接升级为生产规则。",
        "治理实验必须跨同类短周期候选复用；不得只为单个最大亏损交易定制规则。",
    ]
    for bucket in preserve_profits:
        guardrails.extend(_guardrails_for_profit_bucket(bucket.bucket))
    return LossProfitOptimizationPlan(
        loss_buckets=[item.to_dict() for item in loss_buckets],
        profit_buckets=[item.to_dict() for item in profit_buckets],
        target_loss_buckets=[item.bucket for item in target_losses],
        preserve_profit_buckets=[item.bucket for item in preserve_profits],
        experiments_zh=list(dict.fromkeys(experiments)),
        guardrails_zh=list(dict.fromkeys(guardrails)),
    )


def bucket_trade_attributions(
    trades: Sequence[TradeAttributionRow],
    *,
    whipsaw_bars: int = 5,
    trend_hold_bars: int = 30,
    adverse_excursion_threshold: float = -0.01,
) -> list[TradeAttributionBucket]:
    """Aggregate trades into interpretable loss and profit buckets."""

    grouped: dict[TradeBucketKind, list[TradeAttributionRow]] = {}
    for trade in trades:
        grouped.setdefault(
            classify_trade_bucket(
                trade,
                whipsaw_bars=whipsaw_bars,
                trend_hold_bars=trend_hold_bars,
                adverse_excursion_threshold=adverse_excursion_threshold,
            ),
            [],
        ).append(trade)

    loss_abs_total = sum(
        abs(trade.gross_return) for trade in trades if trade.gross_return <= 0.0
    )
    profit_total = sum(
        trade.gross_return for trade in trades if trade.gross_return > 0.0
    )
    buckets: list[TradeAttributionBucket] = []
    for bucket, items in grouped.items():
        gross_sum = float(sum(item.gross_return for item in items))
        side: Literal["loss", "profit"] = "profit" if gross_sum > 0.0 else "loss"
        denominator = profit_total if side == "profit" else loss_abs_total
        buckets.append(
            TradeAttributionBucket(
                bucket=bucket,
                side=side,
                trade_count=len(items),
                gross_return_sum=gross_sum,
                gross_return_mean=float(gross_sum / len(items)) if items else 0.0,
                share_of_side_abs_pnl=(
                    abs(gross_sum) / denominator if denominator > 0.0 else 0.0
                ),
                representative_trades=[
                    item.to_dict()
                    for item in sorted(
                        items,
                        key=lambda row: abs(row.gross_return),
                        reverse=True,
                    )[:5]
                ],
            )
        )
    return sorted(
        buckets,
        key=lambda item: (item.side, item.share_of_side_abs_pnl),
        reverse=True,
    )


def classify_trade_bucket(
    trade: TradeAttributionRow,
    *,
    whipsaw_bars: int = 5,
    trend_hold_bars: int = 30,
    adverse_excursion_threshold: float = -0.01,
) -> TradeBucketKind:
    """Classify one trade into a loss/profit attribution bucket."""

    if trade.gross_return <= 0.0:
        if trade.is_overnight:
            return "overnight_gap_loss"
        if trade.hold_bars <= whipsaw_bars:
            return "micro_whipsaw_loss"
        if trade.worst_adverse_excursion <= adverse_excursion_threshold:
            return "adverse_excursion_loss"
        if trade.hold_bars >= trend_hold_bars:
            return "slow_bleed_loss"
        return "ordinary_loss"
    if trade.is_overnight:
        return "overnight_gap_win"
    if trade.hold_bars >= trend_hold_bars:
        return "trend_capture_win"
    if trade.hold_bars <= whipsaw_bars:
        return "quick_reversal_win"
    return "ordinary_win"


def decide_governance_feedback_loop(
    attribution: ShortHorizonFailureAttribution,
    *,
    oos_cagr: float | None = None,
    oos_mdd: float | None = None,
    iteration: int = 0,
    config: GovernanceFeedbackLoopConfig | None = None,
) -> GovernanceFeedbackLoopDecision:
    """Decide whether to run another attribution-driven governance iteration."""

    cfg = config or GovernanceFeedbackLoopConfig()
    stop_reasons: list[str] = []
    if iteration >= cfg.max_iterations:
        stop_reasons.append("达到治理循环最大迭代次数，避免无限调参。")
    if oos_cagr is not None and oos_cagr >= cfg.min_oos_cagr:
        if oos_mdd is None or oos_mdd >= cfg.max_oos_mdd:
            if (
                attribution.win_rate is not None
                and attribution.win_rate >= cfg.min_win_rate
                and attribution.payoff_ratio is not None
                and attribution.payoff_ratio >= cfg.min_payoff_ratio
                and (
                    attribution.turnover_per_year_estimate is None
                    or attribution.turnover_per_year_estimate
                    <= cfg.max_turnover_per_year
                )
            ):
                return GovernanceFeedbackLoopDecision(
                    action="promote_to_execution_overlay",
                    iteration=iteration,
                    rationale_zh=(
                        "样本外收益、回撤、胜率/盈亏比和换手均达到短周期观察层要求，"
                        "可从失败修复循环转入执行 overlay 验证。"
                    ),
                    proposed_experiments_zh=[],
                    stop_reasons_zh=["达到短周期执行层升级门槛。"],
                    metadata={
                        "policy": cfg.to_dict(),
                        "oos_cagr": oos_cagr,
                        "oos_mdd": oos_mdd,
                        "attribution": attribution.to_dict(),
                    },
                )

    if attribution.root_cause == "execution_overlay_candidate":
        return GovernanceFeedbackLoopDecision(
            action="promote_to_execution_overlay",
            iteration=iteration,
            rationale_zh=(
                "失败归因未显示明确的独立仓位缺陷；更合理的下一步是作为高一级"
                "趋势下的执行 overlay 做边际贡献验证。"
            ),
            proposed_experiments_zh=optimization_hypotheses(attribution.root_cause),
            stop_reasons_zh=[],
            metadata={
                "policy": cfg.to_dict(),
                "oos_cagr": oos_cagr,
                "oos_mdd": oos_mdd,
                "attribution": attribution.to_dict(),
            },
        )

    if stop_reasons:
        return GovernanceFeedbackLoopDecision(
            action="park_or_abandon",
            iteration=iteration,
            rationale_zh=(
                "候选仍未满足升级条件，且治理循环已触达停止条件；应暂停或放弃，"
                "避免把失败样本调成过拟合。"
            ),
            proposed_experiments_zh=[],
            stop_reasons_zh=stop_reasons,
            metadata={
                "policy": cfg.to_dict(),
                "oos_cagr": oos_cagr,
                "oos_mdd": oos_mdd,
                "attribution": attribution.to_dict(),
            },
        )

    experiments = optimization_hypotheses(attribution.root_cause)
    if attribution.whipsaw_loss_share <= cfg.max_whipsaw_loss_share:
        experiments = [
            item
            for item in experiments
            if "冷却" not in item and "最小持仓" not in item
        ]
    if attribution.overnight_loss_share <= cfg.max_overnight_loss_share:
        experiments = [
            item
            for item in experiments
            if "不隔夜" not in item and "开盘" not in item and "尾盘" not in item
        ]
    return GovernanceFeedbackLoopDecision(
        action="retry_with_governance_experiments",
        iteration=iteration,
        rationale_zh=(
            "候选尚未满足升级条件，但失败原因可解释且存在可迁移治理实验；"
            "应生成下一轮治理配置，重跑 walk-forward 和图形归因。"
        ),
        proposed_experiments_zh=experiments,
        stop_reasons_zh=[],
        metadata={
            "policy": cfg.to_dict(),
            "oos_cagr": oos_cagr,
            "oos_mdd": oos_mdd,
            "attribution": attribution.to_dict(),
        },
    )


def _experiments_for_loss_bucket(bucket: TradeBucketKind) -> list[str]:
    mapping: dict[TradeBucketKind, list[str]] = {
        "overnight_gap_loss": [
            "测试 session_risk_governance：不隔夜、尾盘不新开仓/收盘前清仓、" +
            "开盘等待重新确认。",
            "把短周期信号改为日内执行 overlay；隔夜仓位只由更高一级趋势层决定。",
        ],
        "micro_whipsaw_loss": [
            "测试 deadband/斜率阈值：滤波分量接近零轴或斜率不足时不交易。",
            "测试统一冷却期和最小持仓，减少 1–5 根K内反复买卖。",
        ],
        "adverse_excursion_loss": [
            "测试入场后不利波动预算：若短期最大不利波动超过统一阈值则等待重新确认。",
            "测试高一级方向门禁，避免逆主趋势时承受快速不利波动。",
        ],
        "slow_bleed_loss": [
            "测试时间止损或趋势失效确认：持仓多根K仍无利润时降低仓位或等待重新触发。",
            "测试高一级波动/趋势状态过滤，避免弱趋势慢性磨损。",
        ],
        "ordinary_loss": [
            "复核亏损是否分散；若无主导桶，不应继续定制治理，优先角色转换或放弃。",
        ],
        "trend_capture_win": [],
        "overnight_gap_win": [],
        "quick_reversal_win": [],
        "ordinary_win": [],
    }
    return mapping[bucket]


def _guardrails_for_profit_bucket(bucket: TradeBucketKind) -> list[str]:
    mapping: dict[TradeBucketKind, list[str]] = {
        "trend_capture_win": [
            "保护长持仓趋势盈利桶：不允许治理规则把主要趋势盈利保留率压到 70% 以下。",
            "若增加不隔夜会明显删除趋势盈利，必须改为高一级趋势层负责隔夜仓位，而非简单全清。",
        ],
        "overnight_gap_win": [
            "保护隔夜跳空盈利桶：不隔夜实验必须单独报告隔夜盈利损失，不能只看亏损压缩。",
            "若隔夜盈利是主要利润来源，应把隔夜风险交给更高一级 gate，" +
            "而不是短周期层一刀切。",
        ],
        "quick_reversal_win": [
            "保护快速反转盈利桶：deadband/冷却不能完全删除短周期少数高质量快进快出交易。",
        ],
        "ordinary_win": [
            "保护普通盈利桶：报告治理后总盈利桶保留率，防止规则只通过降低交易数改善回撤。",
        ],
        "overnight_gap_loss": [],
        "micro_whipsaw_loss": [],
        "adverse_excursion_loss": [],
        "slow_bleed_loss": [],
        "ordinary_loss": [],
    }
    return mapping[bucket]


def _trade_row(
    entry_idx: int,
    exit_idx: int,
    *,
    close: np.ndarray[Any, np.dtype[np.float64]],
    times: np.ndarray[Any, np.dtype[Any]],
    round_trip_cost: float,
    whipsaw_bars: int,
) -> TradeAttributionRow:
    entry_price = float(close[entry_idx])
    exit_price = float(close[exit_idx])
    gross_return = exit_price / entry_price - 1.0 if entry_price > 0 else 0.0
    path = close[entry_idx : exit_idx + 1]
    worst_adverse = (
        float(np.nanmin(path) / entry_price - 1.0)
        if len(path) and entry_price > 0
        else 0.0
    )
    entry_ts = pd.Timestamp(times[entry_idx])
    exit_ts = pd.Timestamp(times[exit_idx])
    hold_bars = int(exit_idx - entry_idx)
    return TradeAttributionRow(
        entry_time=str(entry_ts),
        exit_time=str(exit_ts),
        gross_return=gross_return,
        net_return_estimate=gross_return - round_trip_cost,
        hold_bars=hold_bars,
        is_win=gross_return > 0.0,
        is_whipsaw=hold_bars <= whipsaw_bars,
        is_overnight=entry_ts.date() != exit_ts.date(),
        worst_adverse_excursion=worst_adverse,
    )
