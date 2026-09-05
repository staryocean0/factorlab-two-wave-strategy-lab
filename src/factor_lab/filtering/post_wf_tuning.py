# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Post walk-forward tuning diagnostics for filter timing candidates.

This layer sits after DII discovery, tool selection, strategy backtests, and
walk-forward validation.  It does not mine new frequencies or optimize
candidate-specific parameters.  Its job is to turn positive walk-forward
candidates into production-readiness review cards:

* classify whether the candidate is stable, exploratory, or should be parked;
* read rendered signal CSVs and quantify visible trade phenomena such as missed
  upside while flat and downside held while long;
* produce cross-cycle tuning recommendations that can be applied as policy
  constraints, not as one-off curve-fit edits.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True, slots=True)
class SignalPhenomenonSummary:
    """Visual-chart companion metrics derived from a rendered signal CSV."""

    signal_csv: str
    sample_count: int
    trade_count: int
    final_nav: float
    captured_upside_share: float | None
    avoided_downside_share: float | None
    missed_upside_bps: float
    held_downside_bps: float
    largest_flat_rally_pct: float
    largest_held_drawdown_pct: float
    whipsaw_trade_share_5bars: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PostWalkForwardTuningCard:
    """One candidate card for post-WF production-readiness review."""

    candidate_id: str
    candidate_set: str
    verdict: str
    tuning_priority: str
    primary_issue: str
    tuning_actions_zh: list[str]
    guardrails_zh: list[str]
    walk_forward: dict[str, object]
    signal_phenomena: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def classify_walk_forward_candidate(row: Mapping[str, object]) -> str:
    """Classify one walk-forward summary row without using chart hindsight."""

    status = str(row.get("status") or "")
    if status != "completed":
        return "delete_or_park_insufficient_wf"
    candidate_set = str(row.get("set") or "")
    cagr = _float(row.get("selected_oos_cagr"))
    best_cagr = _float(row.get("best_fixed_cagr"))
    folds = int(_float(row.get("fold_count")))
    positive_folds = int(_float(row.get("positive_fold_count")))
    positive_share = positive_folds / folds if folds > 0 else 0.0
    target_days = _float(row.get("T_days"))

    if candidate_set == "subday":
        if cagr > 0.10 and target_days >= 0.70:
            return "preliminary_keep_for_more_oos"
        if cagr > 0.0:
            return "exploratory_keep_low_priority"
        return "delete_overfit_or_unstable_subday"
    if cagr >= 0.18 and positive_share >= 0.75:
        return "stable_value_signal"
    if cagr >= 0.10 and positive_share >= 0.65:
        return "keep_for_oos_validation"
    if best_cagr >= 0.25 and cagr > 0.0:
        return "tool_selection_mismatch_review"
    if cagr > 0.0:
        return "weak_positive_watchlist"
    return "delete_overfit_or_unstable"


def analyze_rendered_signal_csv(path: str | Path) -> SignalPhenomenonSummary:
    """Summarize missed/held PnL phenomena from render artifact CSV."""

    frame = pd.read_csv(path)
    required = {"close", "position", "strategy_nav", "trade_marker"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"signal CSV missing required columns: {sorted(missing)}")
    close = pd.to_numeric(frame["close"], errors="coerce")
    position = pd.to_numeric(frame["position"], errors="coerce").fillna(0.0).clip(0, 1)
    log_returns = close.apply(math.log).diff().fillna(0.0)
    upside = log_returns.clip(lower=0.0)
    downside = (-log_returns.clip(upper=0.0))
    captured_upside = (upside * position).sum()
    missed_upside = (upside * (1.0 - position)).sum()
    held_downside = (downside * position).sum()
    avoided_downside = (downside * (1.0 - position)).sum()
    total_upside = upside.sum()
    total_downside = downside.sum()
    nav = pd.to_numeric(frame["strategy_nav"], errors="coerce").dropna()
    markers = frame["trade_marker"].fillna("").astype(str)
    trade_indexes = [
        idx for idx, value in enumerate(markers) if value in {"buy", "sell"}
    ]
    whipsaw = 0
    for left, right in zip(trade_indexes, trade_indexes[1:], strict=False):
        if right - left <= 5:
            whipsaw += 1
    trade_count = len(trade_indexes)
    return SignalPhenomenonSummary(
        signal_csv=str(path),
        sample_count=int(len(frame)),
        trade_count=trade_count,
        final_nav=float(nav.iloc[-1]) if not nav.empty else 1.0,
        captured_upside_share=(
            float(captured_upside / total_upside) if total_upside > 0 else None
        ),
        avoided_downside_share=(
            float(avoided_downside / total_downside) if total_downside > 0 else None
        ),
        missed_upside_bps=float(missed_upside * 10000.0),
        held_downside_bps=float(held_downside * 10000.0),
        largest_flat_rally_pct=_largest_run_return(log_returns, position <= 0.0),
        largest_held_drawdown_pct=_largest_run_return(-downside, position > 0.0),
        whipsaw_trade_share_5bars=(whipsaw / trade_count if trade_count else 0.0),
    )


def build_post_wf_tuning_card(
    wf_row: Mapping[str, object],
    *,
    signal_summary: SignalPhenomenonSummary | None = None,
) -> PostWalkForwardTuningCard:
    """Build a production-readiness tuning card from WF and chart evidence."""

    verdict = str(wf_row.get("wf_verdict") or classify_walk_forward_candidate(wf_row))
    cagr = _float(wf_row.get("selected_oos_cagr"))
    turnover = _float(wf_row.get("selected_oos_turnover"))
    best_cagr = _float(wf_row.get("best_fixed_cagr"))
    selected_cagr = _float(wf_row.get("selected_oos_cagr"))
    candidate_set = str(wf_row.get("set") or "")
    priority = "park"
    issue = "证据不足或不稳定。"
    actions: list[str] = []
    guardrails = [
        "不得用单个候选的图形手工移动周期边界；任何调优必须形成跨周期通用规则。",
        "调优后必须重新跑 walk-forward，并保留原始候选作为对照。",
        "工具选择阶段仍不得读取策略PnL；PnL只能用于验证阶段的候选升降级。",
    ]

    if verdict in {"stable_value_signal", "keep_for_oos_validation"}:
        priority = "high"
        issue = "WF为正且跨折稳定，进入生产就绪调优队列。"
        actions.append(
            "保留原频率中心，先做成本压力、参数扰动和年度分解，" +
            "不做个别点位重拟合。"
        )
    elif verdict == "tool_selection_mismatch_review":
        priority = "high"
        issue = "训练质量赢家与固定收益赢家错位。"
        actions.append(
            "增加验证阶段challenger工具报告：质量赢家保留，" +
            "固定IIR/EMA等收益赢家作为OOS challenger并列展示。"
        )
    elif verdict == "preliminary_keep_for_more_oos":
        priority = "medium"
        issue = "sub-day样本外折数不足但首折为正。"
        actions.append(
            "补更长分钟历史；在未形成多折证据前只作为探索性子频段，" +
            "不进入生产主权重。"
        )
    elif cagr > 0.0:
        priority = "low"
        issue = "WF弱正，暂入观察池。"
        actions.append("只做低成本复核；若年度或新增样本不稳定则删除。")

    if turnover > 100.0:
        actions.append("加入跨周期统一换手惩罚/冷却期实验，例如信号翻转后至少持有N根或要求连续两根斜率同向。")
    if best_cagr - selected_cagr > 0.15:
        actions.append("检查工具质量权重是否过度偏向低滞后/平滑质量；在验证层增加best-fixed-vs-quality-winner差异报告。")
    if signal_summary is not None:
        if (
            signal_summary.captured_upside_share is not None
            and signal_summary.captured_upside_share < 0.45
        ):
            actions.append("图形诊断显示踏空上涨较多：测试通用的低滞后确认规则，而不是单独缩短该候选周期。")
        if (
            signal_summary.avoided_downside_share is not None
            and signal_summary.avoided_downside_share < 0.45
        ):
            actions.append("图形诊断显示下跌规避不足：测试高一级频率门禁或波动状态过滤。")
        if signal_summary.whipsaw_trade_share_5bars > 0.15:
            actions.append("短间隔反复交易偏多：测试统一滞回/冷却规则并重新WF。")
    return PostWalkForwardTuningCard(
        candidate_id=str(wf_row.get("candidate_id") or ""),
        candidate_set=candidate_set,
        verdict=verdict,
        tuning_priority=priority,
        primary_issue=issue,
        tuning_actions_zh=actions,
        guardrails_zh=guardrails,
        walk_forward=dict(wf_row),
        signal_phenomena=signal_summary.to_dict() if signal_summary else None,
    )


def build_post_wf_tuning_cards(
    rows: Sequence[Mapping[str, object]],
    *,
    render_manifest_by_candidate: Mapping[str, Mapping[str, object]] | None = None,
) -> list[PostWalkForwardTuningCard]:
    """Build tuning cards for a collection of WF rows."""

    manifest = render_manifest_by_candidate or {}
    cards: list[PostWalkForwardTuningCard] = []
    for row in rows:
        candidate_id = str(row.get("candidate_id") or "")
        signal_summary = None
        render = manifest.get(candidate_id)
        if render is not None and render.get("signal_csv"):
            signal_summary = analyze_rendered_signal_csv(str(render["signal_csv"]))
        cards.append(build_post_wf_tuning_card(row, signal_summary=signal_summary))
    return cards


def _largest_run_return(log_returns: pd.Series, mask: pd.Series) -> float:
    best = 0.0
    current = 0.0
    for value, active in zip(log_returns.to_numpy(), mask.to_numpy(), strict=True):
        if active:
            current += float(value)
            best = max(best, current)
        else:
            current = 0.0
    return float(math.exp(best) - 1.0) if best > 0 else 0.0


def _float(value: object) -> float:
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return result if math.isfinite(result) else 0.0


def read_csv_dicts(path: str | Path) -> list[dict[str, object]]:
    """Read a CSV summary as dictionaries for CLI/report scripts."""

    with Path(path).open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]
