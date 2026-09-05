# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Canonical research-decision summary for filter timing workflows.

The upstream chain deliberately keeps descriptive profiling, DII physical
frequency discovery, carrier projection, tool selection, and strategy
backtests separated.  This module adds one final reporting layer that answers
the operator's practical questions without mutating any upstream evidence:

* which physical ``T_days`` / ``f`` candidate was discovered?
* which K-line carrier should execute/backtest that frequency?
* did the candidate carry T+1/execution-risk, cost, or sample warnings?
* which tool and single/dual strategy evidence exists?
* is the candidate exploratory, a validation candidate, or sample-out ready?

It is a synthesis layer only.  It must not feed decisions back into frequency
discovery or tool selection.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Literal, cast

ResearchVerdict = Literal["yes", "candidate", "no", "insufficient"]
DualPeriodNeedVerdict = Literal[
    "preferred_primary",
    "optional_defensive_overlay",
    "not_required_for_primary",
    "insufficient_evidence",
]
StrategyRoute = Literal[
    "single_period_primary",
    "dual_period_primary",
    "single_period_primary_with_dual_defensive_candidate",
    "no_strategy_candidate",
]

_PERIOD_ORDER: dict[str, int] = {
    "1min": 0,
    "5min": 1,
    "15min": 2,
    "30min": 3,
    "60min": 4,
    "day": 5,
    "week": 6,
}

RESEARCH_DECISION_FIELD_LABELS_ZH: dict[str, str] = {
    "cycle_filter_verdict": "是否适合周期滤波",
    "trend_indicator_verdict": "是否适合趋势性指标",
    "mean_reversion_verdict": "是否适合震荡/反向指标",
    "entry_exit_tool": "适合定买卖点的本周期工具",
    "parameter_evidence_strength": "参数频段证据强弱",
    "frequency_candidate_id": "DII物理频率候选ID",
    "center_frequency_cycles_per_day": "物理频率（次/交易日）",
    "dii_bps": "代表点DII（bps）",
    "pre_strategy_tradability_status": "策略前可交易性/执行风险提示状态",
    "dual_period_need_verdict": "是否需要双周期交易结构",
    "direction_gate_period": "若使用双周期，大周期方向门禁K线级别",
    "direction_gate_tool": "若使用双周期，大周期方向门禁工具",
    "strategy_route": "当前策略结构建议",
    "primary_backtest": "当前链路内主候选回测摘要",
    "decision_reason_zh": "中文决策解释",
}


@dataclass(frozen=True, slots=True)
class FilterResearchPeriodDecision:
    """Human-facing answer card for one execution period."""

    period: str
    status: str
    cycle_filter_verdict: ResearchVerdict
    trend_indicator_verdict: ResearchVerdict
    mean_reversion_verdict: ResearchVerdict
    recommended_method_route: str
    entry_exit_tool: str | None
    entry_exit_tool_family: str | None
    parameter_evidence_strength: str | None
    parameter_evidence_strength_label_zh: str | None
    pre_strategy_tradability_status: str | None
    pre_strategy_tradability_reason_zh: str | None
    expected_leg_days: float | None
    direction_gate_period: str | None
    direction_gate_tool: str | None
    direction_gate_tool_family: str | None
    dual_period_need_verdict: DualPeriodNeedVerdict
    strategy_route: StrategyRoute
    primary_strategy_template: str | None
    primary_backtest: dict[str, object] | None
    best_single_period_backtest: dict[str, object] | None
    best_dual_period_backtest: dict[str, object] | None
    decision_reason_zh: str
    evidence: dict[str, object] = field(default_factory=dict)
    risk_notes_zh: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FilterResearchDecision:
    """Canonical synthesis artifact for the whole filter workflow chain."""

    index_ref: str
    status: str
    primary_period: str | None
    primary_plan: dict[str, object] | None
    period_decisions: list[FilterResearchPeriodDecision]
    metadata: dict[str, object]
    frequency_decisions: list[dict[str, object]] = field(default_factory=list)
    primary_frequency_candidate_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "index_ref": self.index_ref,
            "status": self.status,
            "primary_frequency_candidate_id": self.primary_frequency_candidate_id,
            "primary_period": self.primary_period,
            "primary_plan": self.primary_plan,
            "frequency_decisions": self.frequency_decisions,
            "period_decisions": [
                decision.to_dict() for decision in self.period_decisions
            ],
            "metadata": self.metadata,
        }


def build_filter_research_decision(
    *,
    index_ref: str,
    series_characteristics: Mapping[str, object],
    frequency_discovery: Mapping[str, object] | None = None,
    tool_results: Sequence[Mapping[str, object]],
    summary_backtests: Sequence[Mapping[str, object]],
) -> FilterResearchDecision:
    """Build the canonical answer matrix from existing chain artifacts."""

    characteristics_by_period = _characteristics_by_period(series_characteristics)
    tools_by_period = _best_tools_by_period(tool_results)
    backtests_by_period = _backtests_by_period(summary_backtests)
    periods = _ordered_periods(
        set(characteristics_by_period) | set(tools_by_period) | set(backtests_by_period)
    )
    period_decisions = [
        _build_period_decision(
            period=period,
            characteristic=characteristics_by_period.get(period),
            tool=tools_by_period.get(period),
            rows=backtests_by_period.get(period, []),
        )
        for period in periods
    ]
    frequency_decisions = _build_frequency_decisions(
        frequency_discovery=frequency_discovery or {},
        tool_results=tool_results,
        summary_backtests=summary_backtests,
    )
    primary_frequency = _primary_frequency_decision(frequency_decisions)
    primary = _primary_period_decision(period_decisions)
    primary_plan = _primary_frequency_plan(primary_frequency) or _primary_plan(primary)
    return FilterResearchDecision(
        index_ref=index_ref,
        status=(
            "completed"
            if frequency_decisions or period_decisions
            else "insufficient_evidence"
        ),
        primary_period=primary.period if primary is not None else None,
        primary_plan=primary_plan,
        period_decisions=period_decisions,
        frequency_decisions=frequency_decisions,
        primary_frequency_candidate_id=(
            str(primary_frequency.get("frequency_candidate_id"))
            if primary_frequency is not None
            else None
        ),
        metadata={
            "workflow_role": "filter_timing_research_decision_synthesis",
            "decision_contract_version": "filter_research_decision_frequency_first_v2",
            "report_axis": "frequency_candidate_plus_carrier",
            "period_decisions_compatibility": (
                "period_decisions are retained for legacy consumers; "
                "frequency_decisions is the primary report axis."
            ),
            "index_ref": index_ref,
            "field_labels_zh": dict(RESEARCH_DECISION_FIELD_LABELS_ZH),
            "canonical_questions": [
                "是否适合周期滤波",
                "发现的物理周期T_days/频率f是什么，推荐承载K线载体是什么",
                "是否适合趋势性指标",
                "什么工具适合定买卖点",
                "目标滤波周期是否带有A股T+1/日内执行风险提示",
                "单周期交易策略是否足够，还是需要双周期交易策略",
                "若使用双周期，定方向的大周期和工具是什么",
                "最佳方案选出后，回测报告与渲染产物在哪里",
            ],
            "synthesis_policy": (
                "This layer summarizes existing preflight/tool/backtest evidence; "
                "it does not feed PnL back into parameter or tool selection."
            ),
            "synthesis_policy_zh": (
                "研究决策层只汇总既有体检、工具选择和回测证据；不把收益结果"
                "反向写回频率参数或工具质量选择。"
            ),
            "promotion_gates_zh": [
                "周期/趋势/震荡适用性先看时间序列体检，不看收益。",
                "买卖点工具先看本周期工具质量，再看策略阶段样本外/回撤/换手。",
                (
                    "双周期门禁只是风险结构候选；是否升级必须看收益保留、"
                    + "回撤压缩、年度稳定和 walk-forward。"
                ),
                (
                    "若单周期 CAGR <= 0 且双周期 CAGR > 0，收益保留率不可解释；"
                    + "必须改看收益改善、回撤压缩和样本外稳定性。"
                ),
                "参数频段为 weak_candidate 时不能叙述为强候选。",
                (
                    "period 字段表示K线载体权限，不表示滤波目标周期；"
                    + "target_center_days/execution_cycle_days 才是目标滤波周期"
                    + "的交易日等效，center_frequency_cycles_per_day 才是物理频率。"
                ),
                (
                    "若目标滤波周期半周期 <= A股T+1传统风险阈值，只写入"
                    + "执行风险提示；该目标仍进入单周期、双周期和walk-forward"
                    + "验证，由稳定性与成本后结果筛选。"
                ),
                (
                    "研究决策 artifact 不自动创建 CandidateFactor、EffectiveFactor、"
                    + "AdmittedFactor 或真实交易策略。"
                ),
            ],
            "factor_lifecycle_mutation": False,
            "strategy_lifecycle_mutation": False,
        },
    )



def _build_frequency_decisions(
    *,
    frequency_discovery: Mapping[str, object],
    tool_results: Sequence[Mapping[str, object]],
    summary_backtests: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    candidates = _frequency_candidates_by_id(frequency_discovery)
    carriers_by_id = _carrier_candidates_by_id(frequency_discovery)
    tools_by_id = _tools_by_frequency_id(tool_results)
    rows_by_id = _backtests_by_frequency_id(summary_backtests)
    candidate_ids = sorted(
        set(candidates) | set(carriers_by_id) | set(tools_by_id) | set(rows_by_id),
        key=lambda value: _frequency_candidate_sort_key(value, candidates),
    )
    decisions: list[dict[str, object]] = []
    for candidate_id in candidate_ids:
        candidate = candidates.get(candidate_id, {})
        carriers = carriers_by_id.get(candidate_id, [])
        tools = tools_by_id.get(candidate_id, [])
        rows = rows_by_id.get(candidate_id, [])
        best_single = _best_row(
            [
                row
                for row in rows
                if str(row.get("strategy_template", "")).startswith("single_period_")
            ]
        )
        best_dual = _best_row(
            [
                row
                for row in rows
                if row.get("strategy_template")
                == "higher_period_gate_execution_trigger"
            ]
        )
        primary_route, dual_need, primary = _strategy_route(
            best_single=best_single,
            best_dual=best_dual,
        )
        representative = _mapping_or_empty(candidate.get("representative_point"))
        recommended_carrier = _recommended_carrier(carriers, tools, rows)
        tool_winners = _tool_winners_by_mode(tools)
        status, t1_reason, expected_leg_days = _candidate_tradability(tools, rows)
        decision = {
            "frequency_candidate_id": candidate_id,
            "rank": candidate.get("rank"),
            "filter_mode": candidate.get("filter_mode") or _first_non_none(
                [
                    _mapping_or_empty(tool.get("target")).get("filter_mode")
                    for tool in tools
                ]
            ),
            "T_days": candidate.get("center_period_days")
            or _first_non_none(
                [
                    _mapping_or_empty(tool.get("target")).get("target_center_days")
                    for tool in tools
                ]
            ),
            "center_period_days": candidate.get("center_period_days"),
            "center_frequency_cycles_per_day": candidate.get(
                "center_frequency_cycles_per_day"
            )
            or _first_non_none(
                [
                    _mapping_or_empty(tool.get("target")).get(
                        "center_frequency_cycles_per_day"
                    )
                    for tool in tools
                ]
            ),
            "period_lo_days": candidate.get("period_lo_days"),
            "period_hi_days": candidate.get("period_hi_days"),
            "positive_ridge_label": candidate.get("evidence_label")
            or _first_non_none(
                [
                    _mapping_or_empty(tool.get("target")).get(
                        "candidate_evidence_label"
                    )
                    for tool in tools
                ]
            ),
            "positive_ridge_point_count": candidate.get("ridge_point_count"),
            "source_periods": candidate.get("source_periods"),
            "representative_dii_bps": candidate.get("best_dii_bps")
            or representative.get("dii_bps")
            or _first_non_none(
                [
                    _mapping_or_empty(tool.get("target")).get("dii_bps")
                    for tool in tools
                ]
            ),
            "representative_hit_rate": candidate.get("hit_rate")
            or representative.get("hit_rate"),
            "recommended_carrier_period": recommended_carrier.get("period"),
            "recommended_carrier": recommended_carrier,
            "carrier_candidates": carriers,
            "tool_winners_by_filter_mode": tool_winners,
            "pre_strategy_tradability_status": status,
            "pre_strategy_tradability_reason_zh": t1_reason,
            "expected_leg_days": expected_leg_days,
            "single_period_backtest": _backtest_summary(best_single),
            "dual_period_backtest": _backtest_summary(best_dual),
            "strategy_route": primary_route,
            "dual_period_need_verdict": dual_need,
            "primary_strategy_template": _string_or_none(
                primary.get("strategy_template") if primary is not None else None
            ),
            "primary_backtest": _backtest_summary(primary),
            "sample_out_verdict": _sample_out_verdict(
                candidate_label=str(
                    candidate.get("evidence_label")
                    or _first_non_none(
                        [
                            _mapping_or_empty(tool.get("target")).get(
                                "candidate_evidence_label"
                            )
                            for tool in tools
                        ]
                    )
                    or ""
                ),
                primary=primary,
            ),
            "decision_reason_zh": _frequency_decision_reason(
                candidate_id=candidate_id,
                candidate=candidate,
                recommended_carrier=recommended_carrier,
                tool_winners=tool_winners,
                status=status,
                primary=primary,
            ),
        }
        decisions.append(decision)
    return decisions


def _frequency_candidates_by_id(
    frequency_discovery: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    result: dict[str, Mapping[str, object]] = {}
    raw = frequency_discovery.get("frequency_candidates")
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, Mapping) and isinstance(item.get("candidate_id"), str):
                result[str(item["candidate_id"])] = item
    return result


def _carrier_candidates_by_id(
    frequency_discovery: Mapping[str, object],
) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {}
    raw = frequency_discovery.get("carrier_candidates")
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            candidate_id = item.get("candidate_id")
            if isinstance(candidate_id, str):
                result.setdefault(candidate_id, []).append(dict(item))
    for rows in result.values():
        rows.sort(key=_carrier_rank_sort_key)
    return result


def _carrier_rank_sort_key(row: Mapping[str, object]) -> int:
    value = row.get("carrier_rank")
    if isinstance(value, (int, float, str)):
        try:
            return int(value)
        except ValueError:
            return 999999
    return 999999


def _tools_by_frequency_id(
    tool_results: Sequence[Mapping[str, object]],
) -> dict[str, list[Mapping[str, object]]]:
    result: dict[str, list[Mapping[str, object]]] = {}
    for item in tool_results:
        target = _mapping_or_empty(item.get("target"))
        candidate_id = target.get("frequency_candidate_id")
        if isinstance(candidate_id, str):
            result.setdefault(candidate_id, []).append(item)
    return result


def _backtests_by_frequency_id(
    summary_backtests: Sequence[Mapping[str, object]],
) -> dict[str, list[Mapping[str, object]]]:
    result: dict[str, list[Mapping[str, object]]] = {}
    for row in summary_backtests:
        candidate_id = row.get("frequency_candidate_id")
        if isinstance(candidate_id, str):
            result.setdefault(candidate_id, []).append(row)
    return result


def _frequency_candidate_sort_key(
    candidate_id: str,
    candidates: Mapping[str, Mapping[str, object]],
) -> tuple[int, str]:
    rank = _float_or_none(candidates.get(candidate_id, {}).get("rank"))
    return (int(rank or 999999), candidate_id)


def _recommended_carrier(
    carriers: Sequence[Mapping[str, object]],
    tools: Sequence[Mapping[str, object]],
    rows: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    for row in rows:
        period = row.get("execution_period")
        if isinstance(period, str):
            return {"period": period, "source": "primary_backtest_execution_period"}
    selected = [item for item in carriers if item.get("selected_for_backtest") is True]
    if selected:
        return dict(selected[0])
    if carriers:
        return dict(carriers[0])
    for tool in tools:
        target = _mapping_or_empty(tool.get("target"))
        period = target.get("period")
        if isinstance(period, str):
            return {"period": period, "source": "tool_target"}
    return {}


def _tool_winners_by_mode(
    tools: Sequence[Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    winners: dict[str, dict[str, object]] = {}
    for tool in tools:
        if tool.get("status") != "completed":
            continue
        target = _mapping_or_empty(tool.get("target"))
        mode = str(target.get("filter_mode") or "unknown")
        current = winners.get(mode)
        if current is None or _float_value(
            tool.get("selected_tool_quality_score")
        ) > _float_value(current.get("selected_tool_quality_score")):
            winners[mode] = {
                "period": target.get("period"),
                "filter_mode": mode,
                "selected_filter": tool.get("selected_filter"),
                "selected_tool_quality_score": tool.get("selected_tool_quality_score"),
                "target_period_lo_bars": target.get("target_period_lo_bars"),
                "target_period_hi_bars": target.get("target_period_hi_bars"),
            }
    return winners


def _candidate_tradability(
    tools: Sequence[Mapping[str, object]],
    rows: Sequence[Mapping[str, object]],
) -> tuple[str | None, str | None, float | None]:
    if rows:
        first = rows[0]
        return (
            _string_or_none(first.get("pre_strategy_tradability_status")) or "passed",
            _string_or_none(first.get("pre_strategy_tradability_reason_zh")),
            _float_or_none(first.get("expected_leg_days")),
        )
    statuses = []
    for tool in tools:
        target = _mapping_or_empty(tool.get("target"))
        statuses.append(
            (
                _string_or_none(target.get("pre_strategy_tradability_status")),
                _string_or_none(target.get("pre_strategy_tradability_reason_zh")),
                _float_or_none(target.get("expected_leg_days")),
            )
        )
    passed = [item for item in statuses if item[0] == "passed"]
    if passed:
        return passed[0]
    risk_noted = [
        item for item in statuses if item[0] == "passed_with_execution_risk_note"
    ]
    if risk_noted:
        return risk_noted[0]
    return statuses[0] if statuses else (None, None, None)


def _sample_out_verdict(
    *,
    candidate_label: str,
    primary: Mapping[str, object] | None,
) -> str:
    if candidate_label in {"strong", "sample_out_ready"} and primary is not None:
        return "sample_out_ready"
    if candidate_label in {"wide_positive_ridge", "directional_candidate"}:
        return "strategy_validation_candidate"
    return "exploratory_positive_dii"


def _frequency_decision_reason(
    *,
    candidate_id: str,
    candidate: Mapping[str, object],
    recommended_carrier: Mapping[str, object],
    tool_winners: Mapping[str, Mapping[str, object]],
    status: str | None,
    primary: Mapping[str, object] | None,
) -> str:
    t_days = candidate.get("center_period_days")
    freq = candidate.get("center_frequency_cycles_per_day")
    ridge = candidate.get("evidence_label") or "unknown"
    carrier = recommended_carrier.get("period") or "尚未形成承载K线"
    modes = "/".join(sorted(tool_winners)) or "尚未形成工具赢家"
    gate = status or "unknown"
    strategy = (
        str(primary.get("strategy_template"))
        if primary is not None
        else "尚无完成回测"
    )
    return (
        f"{candidate_id}: 物理周期T={t_days}交易日，f={freq}次/交易日；"
        f"正DII山脊标签={ridge}；推荐承载K线={carrier}；"
        f"工具赢家模式={modes}；策略前门禁={gate}；主回测={strategy}。"
    )


def _primary_frequency_decision(
    decisions: Sequence[Mapping[str, object]],
) -> Mapping[str, object] | None:
    completed = [item for item in decisions if item.get("primary_backtest")]
    if completed:
        return max(
            completed,
            key=lambda item: _row_decision_score(
                cast(Mapping[str, object], item.get("primary_backtest"))
            ),
        )
    return decisions[0] if decisions else None


def _primary_frequency_plan(
    decision: Mapping[str, object] | None,
) -> dict[str, object] | None:
    if decision is None:
        return None
    return {
        "frequency_candidate_id": decision.get("frequency_candidate_id"),
        "T_days": decision.get("T_days") or decision.get("center_period_days"),
        "center_frequency_cycles_per_day": decision.get(
            "center_frequency_cycles_per_day"
        ),
        "recommended_carrier_period": decision.get("recommended_carrier_period"),
        "strategy_route": decision.get("strategy_route"),
        "strategy_template": decision.get("primary_strategy_template"),
        "pre_strategy_tradability_status": decision.get(
            "pre_strategy_tradability_status"
        ),
        "sample_out_verdict": decision.get("sample_out_verdict"),
        "backtest": decision.get("primary_backtest"),
        "decision_reason_zh": decision.get("decision_reason_zh"),
    }


def _first_non_none(values: Sequence[object]) -> object | None:
    for value in values:
        if value is not None:
            return value
    return None

def _build_period_decision(
    *,
    period: str,
    characteristic: Mapping[str, object] | None,
    tool: Mapping[str, object] | None,
    rows: Sequence[Mapping[str, object]],
) -> FilterResearchPeriodDecision:
    single_rows = [
        row
        for row in rows
        if row.get("strategy_template") == "single_period_component_trigger"
    ]
    dual_rows = [
        row
        for row in rows
        if row.get("strategy_template") == "higher_period_gate_execution_trigger"
    ]
    best_single = _best_row(single_rows)
    best_dual = _best_row(dual_rows)
    precheck_status, precheck_reason, expected_leg_days = (
        _tool_pre_strategy_tradability(tool)
    )
    strategy_route, dual_need, primary = _strategy_route(
        best_single=best_single,
        best_dual=best_dual,
    )
    entry_source = primary or best_single or _tool_backtest_stub(tool)
    entry_tool = _string_or_none(
        (entry_source or {}).get("execution_filter_name")
        if entry_source is not None
        else None
    )
    if entry_tool is None and tool is not None:
        entry_tool = _selected_filter_name(tool)
    entry_family = _selected_filter_family(tool, preferred_name=entry_tool)
    direction_gate_tool = _string_or_none(
        best_dual.get("higher_filter_name") if best_dual is not None else None
    )
    direction_gate_family = _selected_filter_family(
        tool=None,
        preferred_name=direction_gate_tool,
    )
    if direction_gate_family is None and best_dual is not None:
        direction_gate_family = _family_from_filter_name(direction_gate_tool)
    parameter_strength, parameter_strength_label = _target_evidence_strength(tool)

    cycle_verdict = _gate_verdict(characteristic, category="cycle")
    trend_verdict = _gate_verdict(characteristic, category="trend")
    mean_reversion_verdict = _gate_verdict(
        characteristic,
        category="mean_reversion",
    )
    method_route = _method_route(characteristic)
    status = _decision_status(characteristic, tool, rows)
    reason = _decision_reason(
        period=period,
        cycle_verdict=cycle_verdict,
        trend_verdict=trend_verdict,
        entry_tool=entry_tool,
        parameter_strength=parameter_strength,
        strategy_route=strategy_route,
        dual_need=dual_need,
        best_single=best_single,
        best_dual=best_dual,
    )
    return FilterResearchPeriodDecision(
        period=period,
        status=status,
        cycle_filter_verdict=cycle_verdict,
        trend_indicator_verdict=trend_verdict,
        mean_reversion_verdict=mean_reversion_verdict,
        recommended_method_route=method_route,
        entry_exit_tool=entry_tool,
        entry_exit_tool_family=entry_family,
        parameter_evidence_strength=parameter_strength,
        parameter_evidence_strength_label_zh=parameter_strength_label,
        pre_strategy_tradability_status=precheck_status,
        pre_strategy_tradability_reason_zh=precheck_reason,
        expected_leg_days=expected_leg_days,
        direction_gate_period=_string_or_none(
            best_dual.get("higher_period") if best_dual is not None else None
        ),
        direction_gate_tool=direction_gate_tool,
        direction_gate_tool_family=direction_gate_family,
        dual_period_need_verdict=dual_need,
        strategy_route=strategy_route,
        primary_strategy_template=_string_or_none(
            primary.get("strategy_template") if primary is not None else None
        ),
        primary_backtest=_backtest_summary(primary),
        best_single_period_backtest=_backtest_summary(best_single),
        best_dual_period_backtest=_backtest_summary(best_dual),
        decision_reason_zh=reason,
        evidence=_evidence(
            characteristic=characteristic,
            tool=tool,
            best_single=best_single,
            best_dual=best_dual,
        ),
        risk_notes_zh=_risk_notes(
            strategy_route=strategy_route,
            best_single=best_single,
            best_dual=best_dual,
            parameter_strength=parameter_strength,
        ),
    )


def _strategy_route(
    *,
    best_single: Mapping[str, object] | None,
    best_dual: Mapping[str, object] | None,
) -> tuple[StrategyRoute, DualPeriodNeedVerdict, Mapping[str, object] | None]:
    if best_single is None and best_dual is None:
        return "no_strategy_candidate", "insufficient_evidence", None
    if best_single is None:
        return "dual_period_primary", "preferred_primary", best_dual
    if best_dual is None:
        return "single_period_primary", "not_required_for_primary", best_single

    single_score = _row_decision_score(best_single)
    dual_score = _row_decision_score(best_dual)
    retention = _float_or_none(best_dual.get("reward_retention_vs_single"))
    compression = _float_or_none(best_dual.get("drawdown_compression_vs_single"))
    single_cagr = _float_or_none(best_single.get("cagr"))
    dual_cagr = _float_or_none(best_dual.get("cagr"))
    if (
        single_cagr is not None
        and dual_cagr is not None
        and single_cagr <= 0.0
        and dual_cagr > 0.0
        and dual_score > single_score
    ):
        return "dual_period_primary", "preferred_primary", best_dual
    if dual_score > single_score and (retention is None or retention >= 0.80):
        return "dual_period_primary", "preferred_primary", best_dual
    if (
        compression is not None
        and compression >= 0.20
        and retention is not None
        and retention >= 0.30
    ):
        return (
            "single_period_primary_with_dual_defensive_candidate",
            "optional_defensive_overlay",
            best_single,
        )
    return "single_period_primary", "not_required_for_primary", best_single


def _gate_verdict(
    characteristic: Mapping[str, object] | None,
    *,
    category: str,
) -> ResearchVerdict:
    if characteristic is None or characteristic.get("status") != "completed":
        return "insufficient"
    gates = characteristic.get("direct_use_gates")
    if isinstance(gates, list):
        has_category_gate = False
        any_passed = False
        for item in gates:
            if not isinstance(item, Mapping):
                continue
            if item.get("category") != category:
                continue
            has_category_gate = True
            any_passed = any_passed or bool(item.get("passed"))
        if has_category_gate:
            return "yes" if any_passed else "no"
    categories = characteristic.get("candidate_categories")
    if isinstance(categories, list) and category in [str(item) for item in categories]:
        return "candidate"
    return "insufficient"


def _method_route(characteristic: Mapping[str, object] | None) -> str:
    if characteristic is None:
        return "样本或体检证据不足，不能给出方法路由。"
    value = characteristic.get("recommended_use")
    if isinstance(value, str) and value:
        return value
    label = characteristic.get("use_category_label")
    if isinstance(label, str) and label:
        return label
    return "未形成明确方法路由。"


def _decision_status(
    characteristic: Mapping[str, object] | None,
    tool: Mapping[str, object] | None,
    rows: Sequence[Mapping[str, object]],
) -> str:
    if rows:
        return "strategy_candidate_available"
    if tool is not None:
        return "tool_candidate_available"
    if characteristic is not None and characteristic.get("status") == "completed":
        return "preflight_only"
    return "insufficient_evidence"


def _decision_reason(
    *,
    period: str,
    cycle_verdict: ResearchVerdict,
    trend_verdict: ResearchVerdict,
    entry_tool: str | None,
    parameter_strength: str | None,
    strategy_route: StrategyRoute,
    dual_need: DualPeriodNeedVerdict,
    best_single: Mapping[str, object] | None,
    best_dual: Mapping[str, object] | None,
) -> str:
    cycle_text = _verdict_zh(cycle_verdict)
    trend_text = _verdict_zh(trend_verdict)
    tool_text = entry_tool or "尚未形成可用工具"
    strength_text = _parameter_strength_zh(parameter_strength)
    if strategy_route == "single_period_primary":
        route_text = "当前以单周期模板作为主路线，双周期不是主方案必要条件。"
    elif strategy_route == "single_period_primary_with_dual_defensive_candidate":
        route_text = "当前单周期模板保留为进攻主路线，双周期门禁作为回撤压缩/防守候选。"
    elif strategy_route == "dual_period_primary":
        route_text = "当前双周期门禁在链路内优先，仍需样本外确认。"
    else:
        route_text = "当前没有形成策略候选。"
    single_nav = _metric_text(best_single, "final_nav")
    dual_nav = _metric_text(best_dual, "final_nav")
    return (
        f"{period}：周期滤波={cycle_text}，趋势指标={trend_text}；"
        f"参数证据={strength_text}；买卖点优先工具={tool_text}；"
        f"双周期需求={_dual_need_zh(dual_need)}。"
        f"{route_text}"
        f"单周期NAV={single_nav}，双周期NAV={dual_nav}。"
    )


def _risk_notes(
    *,
    strategy_route: StrategyRoute,
    best_single: Mapping[str, object] | None,
    best_dual: Mapping[str, object] | None,
    parameter_strength: str | None,
) -> list[str]:
    notes = [
        (
            "本决策只汇总链路内证据；正式采用仍需 walk-forward、年度超额、"
            + "参数扰动和成本压力测试。"
        ),
        "前置参数/工具阶段不能用最终收益反向重写。",
    ]
    if strategy_route == "single_period_primary_with_dual_defensive_candidate":
        notes.append(
            "双周期门禁当前是防守候选，不应替代单周期进攻主方案，除非风险预算优先。"
        )
    if strategy_route != "no_strategy_candidate":
        notes.append(
            "T+1/日内执行约束只作为风险提示，不再阻断回测；短周期候选必须用"
            + "walk-forward、成本压力和换手约束继续筛选。"
        )
    if (
        best_dual is not None
        and _float_value(best_dual.get("reward_retention_vs_single")) < 0.50
        and not _dual_turns_loss_to_gain(best_single, best_dual)
    ):
        notes.append("双周期门禁收益保留率偏低，需要确认产品是否愿意用收益换回撤。")
    if _dual_turns_loss_to_gain(best_single, best_dual):
        notes.append(
            "双周期门禁把亏损单周期修正为正收益，不能按普通收益保留率解释；仍需样本外验证。"
        )
    if parameter_strength == "weak_candidate":
        notes.append(
            "参数频段仅为弱候选：略高于随机基线时只允许探索，不应叙述为强候选。"
        )
    if (
        best_single is not None
        and _float_value(best_single.get("turnover_per_year")) > 80
    ):
        notes.append("单周期候选换手较高，必须做交易成本和滑点压力测试。")
    return notes


def _evidence(
    *,
    characteristic: Mapping[str, object] | None,
    tool: Mapping[str, object] | None,
    best_single: Mapping[str, object] | None,
    best_dual: Mapping[str, object] | None,
) -> dict[str, object]:
    return {
        "characteristic": _characteristic_evidence(characteristic),
        "tool": _tool_evidence(tool),
        "best_single_period_row": _backtest_summary(best_single),
        "best_dual_period_row": _backtest_summary(best_dual),
    }


def _characteristic_evidence(
    characteristic: Mapping[str, object] | None,
) -> dict[str, object] | None:
    if characteristic is None:
        return None
    return {
        "sample_start": characteristic.get("sample_start"),
        "sample_end": characteristic.get("sample_end"),
        "sample_count": characteristic.get("sample_count"),
        "use_category": characteristic.get("use_category"),
        "use_category_label": characteristic.get("use_category_label"),
        "stability": characteristic.get("stability"),
        "direct_use_gates": characteristic.get("direct_use_gates"),
    }


def _tool_evidence(tool: Mapping[str, object] | None) -> dict[str, object] | None:
    if tool is None:
        return None
    target = _mapping_or_empty(tool.get("target"))
    return {
        "target_source": target.get("target_source"),
        "target_period_lo_bars": target.get("target_period_lo_bars"),
        "target_period_hi_bars": target.get("target_period_hi_bars"),
        "target_center_days": target.get("target_center_days"),
        "center_frequency_cycles_per_day": target.get(
            "center_frequency_cycles_per_day"
        ),
        "frequency_candidate_id": target.get("frequency_candidate_id"),
        "candidate_evidence_label": target.get("candidate_evidence_label"),
        "dii_bps": target.get("dii_bps"),
        "filter_mode": target.get("filter_mode"),
        "expected_leg_days": target.get("expected_leg_days"),
        "pre_strategy_tradability_status": target.get(
            "pre_strategy_tradability_status"
        ),
        "pre_strategy_tradability_reason_zh": target.get(
            "pre_strategy_tradability_reason_zh"
        ),
        "parameter_evidence_strength": target.get("parameter_evidence_strength"),
        "parameter_evidence_strength_label_zh": target.get(
            "parameter_evidence_strength_label_zh"
        ),
        "selected_filter": tool.get("selected_filter"),
        "selected_tool_quality_score": tool.get("selected_tool_quality_score"),
    }


def _target_evidence_strength(
    tool: Mapping[str, object] | None,
) -> tuple[str | None, str | None]:
    if tool is None:
        return None, None
    target = _mapping_or_empty(tool.get("target"))
    strength = _string_or_none(target.get("parameter_evidence_strength"))
    label = _string_or_none(target.get("parameter_evidence_strength_label_zh"))
    return strength, label


def _tool_pre_strategy_tradability(
    tool: Mapping[str, object] | None,
) -> tuple[str | None, str | None, float | None]:
    if tool is None:
        return None, None, None
    target = _mapping_or_empty(tool.get("target"))
    return (
        _string_or_none(target.get("pre_strategy_tradability_status")),
        _string_or_none(target.get("pre_strategy_tradability_reason_zh")),
        _float_or_none(target.get("expected_leg_days")),
    )


def _backtest_summary(row: Mapping[str, object] | None) -> dict[str, object] | None:
    if row is None:
        return None
    keys = [
        "strategy_template",
        "execution_period",
        "higher_period",
        "execution_filter_name",
        "higher_filter_name",
        "execution_cycle_days",
        "center_frequency_cycles_per_day",
        "frequency_candidate_id",
        "candidate_evidence_label",
        "dii_bps",
        "higher_cycle_days",
        "cycle_ratio",
        "final_nav",
        "cagr",
        "sharpe_like",
        "max_drawdown",
        "trade_count",
        "exposure",
        "turnover_per_year",
        "reward_retention_vs_single",
        "cagr_delta_vs_single",
        "drawdown_compression_vs_single",
        "pareto_frontier",
        "gate_tradeoff_status",
        "gate_tradeoff_note_zh",
        "render_artifacts",
    ]
    return {key: row.get(key) for key in keys if key in row}


def _primary_period_decision(
    decisions: Sequence[FilterResearchPeriodDecision],
) -> FilterResearchPeriodDecision | None:
    candidates = [
        decision for decision in decisions if decision.primary_backtest is not None
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: _row_decision_score(item.primary_backtest))


def _primary_plan(
    decision: FilterResearchPeriodDecision | None,
) -> dict[str, object] | None:
    if decision is None:
        return None
    return {
        "period": decision.period,
        "strategy_route": decision.strategy_route,
        "strategy_template": decision.primary_strategy_template,
        "entry_exit_tool": decision.entry_exit_tool,
        "direction_gate_period": decision.direction_gate_period,
        "direction_gate_tool": decision.direction_gate_tool,
        "pre_strategy_tradability_status": decision.pre_strategy_tradability_status,
        "dual_period_need_verdict": decision.dual_period_need_verdict,
        "backtest": decision.primary_backtest,
        "decision_reason_zh": decision.decision_reason_zh,
    }


def _characteristics_by_period(
    series_characteristics: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    periods = series_characteristics.get("periods")
    result: dict[str, Mapping[str, object]] = {}
    if not isinstance(periods, list):
        return result
    for item in periods:
        if not isinstance(item, Mapping):
            continue
        period = item.get("period")
        if isinstance(period, str):
            result[period] = item
    return result


def _best_tools_by_period(
    tool_results: Sequence[Mapping[str, object]],
) -> dict[str, Mapping[str, object]]:
    result: dict[str, Mapping[str, object]] = {}
    for item in tool_results:
        if item.get("status") != "completed":
            continue
        target = _mapping_or_empty(item.get("target"))
        period = target.get("period")
        if not isinstance(period, str):
            continue
        current = result.get(period)
        if current is None or _float_value(
            item.get("selected_tool_quality_score")
        ) > _float_value(current.get("selected_tool_quality_score")):
            result[period] = item
    return result


def _backtests_by_period(
    summary_backtests: Sequence[Mapping[str, object]],
) -> dict[str, list[Mapping[str, object]]]:
    result: dict[str, list[Mapping[str, object]]] = {}
    for row in summary_backtests:
        period = row.get("execution_period")
        if isinstance(period, str):
            result.setdefault(period, []).append(row)
    return result


def _best_row(
    rows: Sequence[Mapping[str, object]],
) -> Mapping[str, object] | None:
    if not rows:
        return None
    return max(rows, key=_row_decision_score)


def _row_decision_score(row: Mapping[str, object] | None) -> float:
    if row is None:
        return float("-inf")
    cagr = _float_value(row.get("cagr"))
    sharpe = _float_or_none(row.get("sharpe_like")) or 0.0
    drawdown = abs(_float_or_none(row.get("max_drawdown")) or 0.0)
    turnover = _float_or_none(row.get("turnover_per_year")) or 0.0
    return cagr + 0.05 * sharpe - 0.35 * drawdown - 0.002 * math.log1p(turnover)


def _dual_turns_loss_to_gain(
    best_single: Mapping[str, object] | None,
    best_dual: Mapping[str, object] | None,
) -> bool:
    if best_single is None or best_dual is None:
        return False
    single_cagr = _float_or_none(best_single.get("cagr"))
    dual_cagr = _float_or_none(best_dual.get("cagr"))
    if single_cagr is None or dual_cagr is None:
        return False
    return single_cagr <= 0.0 and dual_cagr > 0.0


def _tool_backtest_stub(
    tool: Mapping[str, object] | None,
) -> Mapping[str, object] | None:
    if tool is None:
        return None
    selected = _mapping_or_empty(tool.get("selected_filter"))
    if not selected:
        return None
    return {
        "execution_filter_name": selected.get("name"),
        "strategy_template": None,
    }


def _selected_filter_name(tool: Mapping[str, object] | None) -> str | None:
    if tool is None:
        return None
    selected = _mapping_or_empty(tool.get("selected_filter"))
    return _string_or_none(selected.get("name"))


def _selected_filter_family(
    tool: Mapping[str, object] | None,
    *,
    preferred_name: str | None,
) -> str | None:
    if tool is not None:
        selected = _mapping_or_empty(tool.get("selected_filter"))
        if preferred_name is None or selected.get("name") == preferred_name:
            value = selected.get("family")
            if isinstance(value, str):
                return value
        tool_selection = _mapping_or_empty(tool.get("tool_selection"))
        selected_list = tool_selection.get("selected")
        if isinstance(selected_list, list):
            for item in selected_list:
                if not isinstance(item, Mapping):
                    continue
                spec = _mapping_or_empty(item.get("filter_spec"))
                if preferred_name is not None and spec.get("name") != preferred_name:
                    continue
                family = spec.get("family")
                if isinstance(family, str):
                    return family
    return _family_from_filter_name(preferred_name)


def _family_from_filter_name(name: str | None) -> str | None:
    if not name:
        return None
    lowered = name.lower()
    if "iir" in lowered or "laplace" in lowered:
        return "laplace_iir"
    if "fft" in lowered or "fourier" in lowered:
        return "fourier_rolling"
    if "haar" in lowered or "wavelet" in lowered:
        return "wavelet_haar"
    if "ema" in lowered:
        return "ema_baseline"
    return None


def _ordered_periods(periods: set[str]) -> list[str]:
    return sorted(periods, key=lambda item: (_PERIOD_ORDER.get(item, 99), item))


def _mapping_or_empty(value: object) -> Mapping[str, object]:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else {}


def _float_or_none(value: object) -> float | None:
    if not isinstance(value, int | float | str):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def _float_value(value: object) -> float:
    result = _float_or_none(value)
    return result if result is not None else float("-inf")


def _string_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _verdict_zh(verdict: ResearchVerdict) -> str:
    return {
        "yes": "适合",
        "candidate": "候选",
        "no": "不适合",
        "insufficient": "证据不足",
    }[verdict]


def _dual_need_zh(verdict: DualPeriodNeedVerdict) -> str:
    return {
        "preferred_primary": "双周期主方案候选",
        "optional_defensive_overlay": "可选防守叠加，不是主方案必要条件",
        "not_required_for_primary": "单周期主方案即可",
        "insufficient_evidence": "证据不足",
    }[verdict]


def _parameter_strength_zh(strength: str | None) -> str:
    return {
        "weak_candidate": "弱候选",
        "candidate": "候选",
        "strong_candidate": "强候选",
        None: "未标注",
    }.get(strength, str(strength))


def _metric_text(row: Mapping[str, object] | None, key: str) -> str:
    if row is None:
        return "无"
    value = _float_or_none(row.get(key))
    if value is None:
        return "无"
    return f"{value:.4g}"
