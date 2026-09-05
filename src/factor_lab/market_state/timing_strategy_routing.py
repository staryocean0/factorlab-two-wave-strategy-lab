# pyright: reportAny=false, reportArgumentType=false
# pyright: reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Three-tier, bidirectional timing-strategy routing infrastructure.

The router classifies causal bars before a consumer chooses a position policy.
It separates directional evidence (up/down/flat) from portfolio intent
(long/short/flat/hold), so Risk-Off, long-only, short-only, and long-short
consumers can reuse the same mutually exclusive route buckets.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.tool_registry_v1_4 import CURRENT_TOOL_IDS

TIMING_STRATEGY_ROUTER_SCHEMA_ID = "market_state_timing_strategy_router@1.0"
TIMING_STRATEGY_ROUTER_VERSION = "timing_strategy_router_v1"

ROUTE_TIER_IDS = (
    "explosive_move",
    "ordinary_trend",
    "flat_scale_downshift",
)
ROUTE_SLOT_IDS = (
    "explosive_context_free_channel",
    "explosive_context_conditioned_channel",
    "explosive_crash_rebound",
    "ordinary_trend",
    "flat_scale_downshift",
)
ROUTE_SLOT_PRIORITY = MappingProxyType(
    {
        "explosive_context_free_channel": 1,
        "explosive_context_conditioned_channel": 2,
        "explosive_crash_rebound": 3,
        "ordinary_trend": 4,
        "flat_scale_downshift": 5,
    }
)
ROUTE_SLOT_TIER = MappingProxyType(
    {
        "explosive_context_free_channel": "explosive_move",
        "explosive_context_conditioned_channel": "explosive_move",
        "explosive_crash_rebound": "explosive_move",
        "ordinary_trend": "ordinary_trend",
        "flat_scale_downshift": "flat_scale_downshift",
    }
)
ROUTE_DIRECTION_IDS = ("up", "down", "flat")
POLICY_DIRECTION_IDS = (*ROUTE_DIRECTION_IDS, "unassigned")

ROUTE_FIELD_LABELS_ZH = MappingProxyType(
    {
        "route_tier_id": "路由层级",
        "route_slot_id": "顺序责任位",
        "route_direction_id": "方向事实",
        "responsible_tool_id": "责任工具",
        "responsible_tool_profile_id": "责任工具Profile",
        "responsible_state_id": "责任状态",
        "context_tool_id": "上下文工具",
        "context_profile_id": "上下文Profile",
        "route_slot_priority": "责任位优先级",
        "claimed": "是否已认领",
        "remaining_unassigned": "是否仍未认领",
        "decision_clock": "决策执行时钟",
    }
)
POSITION_FIELD_LABELS_ZH = MappingProxyType(
    {
        "position_policy_id": "仓位组合策略",
        "route_direction_id": "方向事实",
        "decision_target_position_for_next_bar": "本棒决定的下一棒目标仓位",
        "decision_transition_action": "本棒决定的仓位转换动作",
        "executable_position": "当前执行棒仓位",
        "single_execution_shift": "是否仅执行一次移位",
    }
)


@dataclass(frozen=True, slots=True)
class TimingRouteClaim:
    """One selected directional tool profile and its causal bar mask."""

    slot_id: str
    direction_id: str
    tool_id: str
    tool_profile_id: str
    state_id: str
    eligible: pd.Series
    context_tool_id: str | None = None
    context_profile_id: str | None = None

    def __post_init__(self) -> None:
        if self.slot_id not in ROUTE_SLOT_IDS:
            raise ValidationError(f"unsupported route slot: {self.slot_id}")
        if self.direction_id not in ROUTE_DIRECTION_IDS:
            raise ValidationError(f"unsupported route direction: {self.direction_id}")
        if self.slot_id != "flat_scale_downshift" and self.direction_id == "flat":
            raise ValidationError("only the final scale-downshift slot may claim flat bars")
        if self.tool_id not in CURRENT_TOOL_IDS:
            raise ValidationError(f"route tool is not in current 14: {self.tool_id}")
        if not self.tool_profile_id.strip() or not self.state_id.strip():
            raise ValidationError("route tool_profile_id and state_id are required")
        if self.eligible.empty or self.eligible.index.has_duplicates:
            raise ValidationError("route eligibility must be non-empty with unique index")
        if self.eligible.isna().any() or not pd.api.types.is_bool_dtype(self.eligible.dtype):
            raise ValidationError("route eligibility must be a complete boolean series")
        needs_context = self.slot_id in {
            "explosive_context_conditioned_channel",
            "explosive_crash_rebound",
        }
        context_complete = bool(self.context_tool_id) and bool(self.context_profile_id)
        if needs_context and not context_complete:
            raise ValidationError("context-dependent explosive route requires a complete context owner")
        if not needs_context and (self.context_tool_id is not None or self.context_profile_id is not None):
            raise ValidationError("only context-dependent explosive routes may declare context ownership")
        if self.context_tool_id is not None and self.context_tool_id not in CURRENT_TOOL_IDS:
            raise ValidationError("context tool is not in the current 14-tool registry")
        if self.slot_id == "explosive_crash_rebound" and self.direction_id != "up":
            raise ValidationError("the frozen crash-rebound route is up-only")


@dataclass(frozen=True, slots=True)
class PositionPolicySpec:
    """Map direction evidence to a target position without changing the router."""

    policy_id: str
    name_zh: str
    target_by_direction: Mapping[str, float | None]

    def __post_init__(self) -> None:
        if not self.policy_id.strip() or not self.name_zh.strip():
            raise ValidationError("position policy id and Chinese name are required")
        mapping = {str(key): value for key, value in self.target_by_direction.items()}
        if tuple(mapping) != POLICY_DIRECTION_IDS:
            raise ValidationError("position policy must map up/down/flat/unassigned in order")
        allowed = {-1.0, 0.0, 1.0, None}
        if any(value not in allowed for value in mapping.values()):
            raise ValidationError("position targets must be -1, 0, 1, or hold(None)")
        object.__setattr__(self, "target_by_direction", MappingProxyType(mapping))

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "name_zh": self.name_zh,
            "target_by_direction": dict(self.target_by_direction),
            "position_semantics": {"long": 1.0, "flat": 0.0, "short": -1.0, "hold": None},
            "production_authority": False,
        }


def default_position_policy_specs() -> tuple[PositionPolicySpec, ...]:
    """Return reusable examples; consumers may register a separate custom policy."""

    return (
        PositionPolicySpec(
            policy_id="long_short",
            name_zh="上涨做多、下跌做空",
            target_by_direction={"up": 1.0, "down": -1.0, "flat": 0.0, "unassigned": None},
        ),
        PositionPolicySpec(
            policy_id="long_flat",
            name_zh="上涨做多、下跌平多仓",
            target_by_direction={"up": 1.0, "down": 0.0, "flat": 0.0, "unassigned": None},
        ),
        PositionPolicySpec(
            policy_id="short_flat",
            name_zh="下跌做空、上涨平空头仓位",
            target_by_direction={"up": 0.0, "down": -1.0, "flat": 0.0, "unassigned": None},
        ),
    )


def _candidate(
    candidate_id: str,
    tool_id: str,
    tool_profile_id: str,
    status: str,
    *,
    notes_zh: str,
) -> dict[str, object]:
    if tool_id not in CURRENT_TOOL_IDS:
        raise ValidationError(f"architecture candidate is not in current 14: {tool_id}")
    return {
        "candidate_id": candidate_id,
        "tool_id": tool_id,
        "tool_profile_id": tool_profile_id,
        "status": status,
        "notes_zh": notes_zh,
    }


def _architecture_tiers() -> list[dict[str, object]]:
    context_candidates = [
        _candidate(
            "w72_context",
            "frequency_selective_bollinger_channel",
            "w72_frequency_bollinger_context",
            "not_selected_for_second_slot_v0",
            notes_zh=(
                "V62当前W72上下文仅作基准；开发期三档后验波段方向还原均值"
                "低于论文核快组，不用策略收益反选。"
            ),
        ),
        _candidate(
            "paper_fast_direction_context",
            "paper_kernel_multiscale_trend_router",
            "paper_fast_group_direction_hysteresis_0p05",
            "superseded_by_user_selected_s20_shared_parent",
            notes_zh=(
                "5/10/15/20日方向快组在2009—2017的4%/8%/12%后验波段"
                "方向还原均值最高；保留为V0对照，不再是当前父背景。"
            ),
        ),
        _candidate(
            "paper_s20_shared_parent",
            "paper_kernel_multiscale_trend_router",
            "paper_s20_single_scale_parent_boundary_0p05",
            "selected_shared_parent_prototype_not_locked",
            notes_zh=(
                "用户在S5跨尺度Battle后选定S20；同一S20 up/down/flat父桶"
                "同时供给第二责任位背景与普通趋势分桶。±0.05平区边界"
                "未优化，S20下跌桶没有打赢S5的历史限制保留。"
            ),
        ),
    ]
    return [
        {
            "tier_id": "explosive_move",
            "priority": 1,
            "meaning_zh": "先于所有普通趋势工具认领暴涨与暴跌K线。",
            "slots": [
                {
                    "slot_id": "explosive_context_free_channel",
                    "slot_priority": 1,
                    "requires_external_context": False,
                    "required_directions": ["up", "down"],
                    "execution_candidates": [
                        _candidate(
                            "symmetric_large_channel",
                            "causal_trendline_channel",
                            "large_scale_high_slope_high_path_efficiency_channel",
                            "bidirectional_bucket_architecture_locked_parameters_not_authorized",
                            notes_zh=(
                                "down复用V62独立大通道，up在价格对数镜像上运行同一公式；"
                                "2009—2017与2018—2020的双向单边价值均为正，但大行情覆盖偏窄，"
                                "因此是可执行原型而非已锁定胜者。"
                            ),
                        )
                    ],
                    "context_candidates": [],
                },
                {
                    "slot_id": "explosive_context_conditioned_channel",
                    "slot_priority": 2,
                    "requires_external_context": True,
                    "required_directions": ["up", "down"],
                    "execution_candidates": [
                        _candidate(
                            "fresh_context_channel",
                            "causal_trendline_channel",
                            "background_aligned_fast_acceleration_channel",
                            "bidirectional_bucket_architecture_locked_parameters_not_authorized",
                            notes_zh=(
                                "背景负责持续方向，局部仅用W12/W24新鲜加速通道；"
                                "S20父背景在开发和冻结复播均优于反向背景，并降低裸通道回撤。"
                            ),
                        )
                    ],
                    "context_candidates": context_candidates,
                    "context_selection_status": (
                        "paper_s20_shared_parent_architecture_locked_parameters_not_authorized"
                    ),
                },
                {
                    "slot_id": "explosive_crash_rebound",
                    "slot_priority": 3,
                    "requires_external_context": True,
                    "required_directions": ["up"],
                    "fixed_parent_bucket": "sharp_turn_morphology_classifier_v0/sharp_reversal/up",
                    "retired_directions": ["down"],
                    "execution_candidates": [
                        _candidate(
                            "sharp_reversal_up_arc_envelope",
                            "causal_asymmetric_arc_state_space_envelope",
                            "registered_v1_4_frozen_benchmark_15m_inside_sharp_reversal_up",
                            "research_formula_frozen_architecture_bucket_locked",
                            notes_zh=(
                                "只保留S20下跌背景后的暴跌反弹方向；15分钟非对称圆弧包络"
                                "通过开发三折和2018—2020重复审计。冲高回落方向已按图形归因"
                                "撤销，不再形成独立桶、观察态或后续Battle。"
                            ),
                        )
                    ],
                    "context_candidates": [
                        _candidate(
                            "paper_s20_down_parent",
                            "paper_kernel_multiscale_trend_router",
                            "paper_s20_single_scale_parent_boundary_0p05",
                            "frozen_parent_context_for_crash_rebound",
                            notes_zh="暴跌反弹只允许来自S20下跌父背景中的反向上涨通道。",
                        )
                    ],
                    "selection_status": "up_only_bucket_and_research_owner_frozen",
                },
            ],
        },
        {
            "tier_id": "ordinary_trend",
            "priority": 2,
            "meaning_zh": "只处理两类暴涨暴跌通道都没有认领的普通趋势。",
            "slots": [
                {
                    "slot_id": "ordinary_trend",
                    "slot_priority": 4,
                    "requires_external_context": False,
                    "required_directions": ["up", "down"],
                    "parent_bucket_classifier": {
                        "tool_id": "paper_kernel_multiscale_trend_router",
                        "tool_profile_id": "paper_s20_single_scale_parent_boundary_0p05",
                        "up_bucket": "paper_s20_parent_up_for_next_bar",
                        "down_bucket": "paper_s20_parent_down_for_next_bar",
                        "flat_bucket_passes_to_next_slot": True,
                        "execution_owner_selected": False,
                    },
                    "execution_candidates": [
                        _candidate(
                            "w72_ordinary_trend",
                            "frequency_selective_bollinger_channel",
                            "w72_frequency_bollinger_trend",
                            "current_v62_downside_fallback_not_stable_winner",
                            notes_zh="V62有下跌兜底与正式恢复示例，但W72参数稳定性未通过。",
                        ),
                        _candidate(
                            "paper_multiscale_ordinary_trend",
                            "paper_kernel_multiscale_trend_router",
                            "hierarchical_multiscale_direction",
                            "battle_required",
                            notes_zh="第14工具是普通双向趋势候选，尚未打赢W72或锁定内部尺度。",
                        ),
                    ],
                    "selection_status": "ordinary_up_owner_open_flat_then_down_battles_pending",
                }
            ],
        },
        {
            "tier_id": "flat_scale_downshift",
            "priority": 3,
            "meaning_zh": "父级横盘无法盈利时，下钻较短尺度重新输出up/down/flat。",
            "slots": [
                {
                    "slot_id": "flat_scale_downshift",
                    "slot_priority": 5,
                    "requires_external_context": False,
                    "parent_regime": "paper_s20_parent_flat_for_next_bar",
                    "required_directions": ["up", "down", "flat"],
                    "execution_candidates": [
                        _candidate(
                            "iir_component_direction",
                            "laplace_iir_mixed_bandpass",
                            "delta_component_direction",
                            "battle_required",
                            notes_zh=(
                                "把滤波分量视作分量K线，方向只用Δcomponent；不用分量正负、"
                                "零轴或相位峰谷。"
                            ),
                        ),
                        _candidate(
                            "paper_s5_direction",
                            "paper_kernel_multiscale_trend_router",
                            "s5_direction",
                            "battle_required",
                            notes_zh="这里是5日论文核尺度，不是5分钟K线。",
                        ),
                    ],
                    "selection_status": "iir_delta_component_vs_paper_s5_battle_required",
                }
            ],
        },
    ]


def build_timing_strategy_router_payload() -> dict[str, object]:
    """Build the no-market-data architecture and V62 example contract."""

    payload: dict[str, object] = {
        "schema_id": TIMING_STRATEGY_ROUTER_SCHEMA_ID,
        "router_version": TIMING_STRATEGY_ROUTER_VERSION,
        "tool_registry_version": "tool_registry_v1_4",
        "architecture_status": "explosive_three_bucket_architecture_locked_ordinary_owners_open",
        "route_tier_ids": list(ROUTE_TIER_IDS),
        "route_slot_ids": list(ROUTE_SLOT_IDS),
        "routing_formula": (
            "for slot in fixed_priority: claim=remaining AND selected_causal_mask; "
            "remaining=remaining AND NOT claim"
        ),
        "tiers": _architecture_tiers(),
        "bidirectional_development_contract": {
            "required_direction_outputs": ["up", "down"],
            "required_evaluation_lenses": [
                "up_long_value",
                "down_short_value",
                "down_close_long_value",
                "up_close_short_value",
                "turnover_and_transition_cost",
            ],
            "flat_is_parent_or_no_direction_state": True,
            "new_tools_should_develop_up_and_down_together": True,
            "approved_directional_exceptions": {
                "explosive_crash_rebound": {
                    "active_directions": ["up"],
                    "retired_directions": ["down"],
                    "reason": "down direction retired after fixed-bucket graphical handoff attribution",
                }
            },
            "route_output_is_position_neutral": True,
            "decision_clock": "closed_bar_decision_next_bar_execution",
        },
        "position_policy_examples": [spec.to_dict() for spec in default_position_policy_specs()],
        "custom_position_policy_contract": {
            "required_direction_keys": list(POLICY_DIRECTION_IDS),
            "allowed_targets": [-1.0, 0.0, 1.0, None],
            "none_semantics": "hold_previous_position",
            "consumer_must_register_separate_policy_id": True,
        },
        "position_action_separation": {
            "target_positions": {"long": 1.0, "flat": 0.0, "short": -1.0},
            "transition_actions": [
                "open_long",
                "close_long",
                "open_short",
                "close_short",
                "reverse_long_to_short",
                "reverse_short_to_long",
                "hold_long",
                "hold_short",
                "hold_flat",
            ],
            "rule_zh": "平仓是仓位变化动作，flat是变化后的无仓位目标状态；两者不得混称。",
        },
        "v62_example": {
            "consumer_policy": "long_flat",
            "context_free_down_example": "large_channel_cash",
            "context_conditioned_down_example": (
                "V62 retains W72 -> fresh V56; infrastructure prototype uses "
                "paper-S20 parent -> fresh W12/W24 acceleration"
            ),
            "ordinary_down_example": "W72 fallback cash",
            "upside_examples_status": (
                "context_free_and_context_conditioned_up_v0_developed_"
                "ordinary_and_flat_slots_open"
            ),
            "v62_runtime_modified": False,
        },
        "explosive_bucket_freeze": {
            "bucket_order": [
                "explosive_context_free_channel",
                "explosive_context_conditioned_channel",
                "explosive_crash_rebound",
            ],
            "active_direction_contract": {
                "explosive_context_free_channel": ["up", "down"],
                "explosive_context_conditioned_channel": ["up", "down"],
                "explosive_crash_rebound": ["up"],
            },
            "retired_bucket": "sharp_reversal/down",
            "retired_bucket_has_route_or_watch_authority": False,
            "architecture_lock_authority": True,
            "parameter_authority": False,
            "production_authority": False,
        },
        "first_slot_evidence": {
            "profile_id": "large_scale_high_slope_high_path_efficiency_channel",
            "development_period": "2009_2017",
            "repeat_audit_period": "2018_2020",
            "up_net_log_value": {
                "development": 0.8943469732882892,
                "repeat_audit": 0.17807891383113061,
            },
            "down_net_log_value": {
                "development": 1.259854076982231,
                "repeat_audit": 0.12806010062583995,
            },
            "raw_direction_conflict_bars": 0,
            "formula_search_count": 0,
            "verdict": "bidirectional_bucket_responsibility_and_order_locked",
            "v62_runtime_modified": False,
        },
        "second_slot_evidence": {
            "profile_id": "background_aligned_fast_acceleration_channel",
            "context_profile_id": "paper_s20_single_scale_parent_boundary_0p05",
            "background_selection_target": "shared_parent_after_s5_pairwise_battle",
            "flat_boundary_selected_by_strategy_return": False,
            "development_period": "2009_2017",
            "repeat_audit_period": "2018_2020",
            "combined_net_log_value": {
                "development": 0.4434279433113068,
                "repeat_audit": 0.221742359931336,
            },
            "combined_maximum_drawdown": {
                "development": -0.0663434070935393,
                "repeat_audit": -0.0414374592279669,
            },
            "combined_positive_episode_rate": {
                "development": 0.5157894736842106,
                "repeat_audit": 0.5913978494623656,
            },
            "aligned_beats_opposed_in_both_periods": True,
            "old_fast_group_preserved_as_comparison": True,
            "verdict": "s20_shared_parent_bidirectional_bucket_responsibility_and_order_locked",
            "v62_runtime_modified": False,
        },
        "third_slot_evidence": {
            "fixed_parent_bucket": "sharp_turn_morphology_classifier_v0/sharp_reversal/up",
            "retired_parent_bucket": "sharp_turn_morphology_classifier_v0/sharp_reversal/down",
            "selected_candidate": "registered:causal_asymmetric_arc_state_space_envelope:15m",
            "development_period": "2009_2017",
            "repeat_audit_period": "2018_2020",
            "net_log_value": {
                "development": 0.2125547201,
                "repeat_audit": 0.038397532,
            },
            "maximum_drawdown": {
                "development": -0.059635458,
                "repeat_audit": -0.0211894484,
            },
            "opportunity_value_capture_rate": {
                "development": 0.6700689615,
                "repeat_audit": 0.6612790773,
            },
            "repeat_audit_positive_year_count": 3,
            "repeat_audit_double_cost_net_positive": True,
            "down_retirement_reason": (
                "valuable sharp-reversal/down events are the leading segment of the higher-priority "
                "context-free down channel; orphan events are negative in both periods"
            ),
            "verdict": "crash_rebound_up_only_bucket_locked_down_route_retired",
            "v62_runtime_modified": False,
        },
        "s20_parent_bucket_evidence": {
            "tool_profile_id": "paper_s20_single_scale_parent_boundary_0p05",
            "development_period": "2009_2017",
            "repeat_audit_period": "2018_2020",
            "directional_gross_log_value": {
                "development_up": 1.6526530830384654,
                "development_down": 0.1921745894507071,
                "repeat_audit_up": 0.1268560222154703,
                "repeat_audit_down": 0.2005701399764805,
            },
            "remaining_bar_share": {
                "development_up": 0.4912020109689214,
                "development_down": 0.3243258683729433,
                "development_flat": 0.0230804387568555,
                "repeat_audit_up": 0.4092816165767617,
                "repeat_audit_down": 0.4247795187944173,
                "repeat_audit_flat": 0.0324514085110026,
            },
            "all_up_down_period_directional_gross_positive": True,
            "flat_boundary_status": "provisional_inherited_not_optimized",
            "ordinary_execution_owner_selected": False,
            "direct_bucket_as_strategy_cost_gate_passed": False,
            "verdict": "parent_direction_buckets_viable_execution_owner_still_open",
            "v62_runtime_modified": False,
        },
        "ordinary_up_bucket_battle_evidence": {
            "fixed_bucket": "ordinary_s20_up_executable",
            "single_tool_candidate_count": 16,
            "development_selected_candidate": "paper_s5_zero_cross",
            "development_selected_net_log_value": 1.0438254248351309,
            "repeat_audit_selected_net_log_value": 0.0036558194696251,
            "repeat_audit_single_tool_survivors": ["w72_k1_c1_r1"],
            "cross_period_survivors": [],
            "post_attribution_shadow_candidate": "paper_s5_and_w72",
            "shadow_development_net_log_value": 0.9329099611600543,
            "shadow_repeat_audit_net_log_value": 0.1011220179686627,
            "shadow_candidate_audit_contaminated": True,
            "owner_selected": False,
            "verdict": "single_tool_battle_no_winner_keep_up_owner_open",
            "v62_runtime_modified": False,
        },
        "ordinary_up_bucket_orthogonality_evidence": {
            "fixed_bucket": "ordinary_s20_up_executable",
            "registered_tool_identity_count": 14,
            "profile_count": 27,
            "residual_gross_positive_both_periods": True,
            "development_residual_gross_log_value": 1.6526530830384654,
            "repeat_audit_residual_gross_log_value": 0.1268560222154703,
            "longer_period_monotonic_law_supported": False,
            "lower_channel_phi_monotonic_law_supported": False,
            "logic_consistent_shadow_candidate": (
                "registered:bollinger_volatility_channel:60m"
            ),
            "shadow_effective_period_15m_bars": 320,
            "shadow_development_net_log_value": 0.740557439662866,
            "shadow_repeat_audit_net_log_value": 0.1102419480655491,
            "shadow_development_double_cost_net_log_value": 0.433257439662866,
            "shadow_repeat_audit_double_cost_net_log_value": 0.0325419480655491,
            "shadow_candidate_selected_after_repeat_audit_inspection": True,
            "owner_selected": False,
            "v62_runtime_modified": False,
        },
        "open_battles": [
            "ordinary_up_owner:no_cross_period_single_tool_survivor",
            "flat_child_owner:not_started_iir_delta_component_vs_paper_s5",
            "ordinary_down_owner:not_started",
        ],
        "unclaimed_bar_policy": "remain_unassigned_for_gap_review",
        "selection_data_rows_read": 0,
        "return_rows_read": 0,
        "production_authority": False,
        "dynamic_parameter_authority": False,
        "tool_selection_authority": False,
        "tool_routing_authority": False,
        "field_labels_zh": {
            "route_tier_ids": "三级择时路由",
            "route_slot_ids": "五个顺序责任位",
            "bidirectional_development_contract": "多空同时开发合同",
            "position_policy_examples": "仓位组合示例",
            "position_action_separation": "仓位状态与平仓动作分离",
            "first_slot_evidence": "无上下文暴涨暴跌第一责任位原型证据",
            "second_slot_evidence": "有上下文暴涨暴跌第二责任位消融证据",
            "third_slot_evidence": "暴跌反弹单向第三责任位证据",
            "explosive_bucket_freeze": "三个顶层爆发行情责任桶冻结合同",
            "s20_parent_bucket_evidence": "S20共享父级上涨下跌横盘分桶证据",
            "ordinary_up_bucket_battle_evidence": "S20普通上涨桶执行工具擂台证据",
            "ordinary_up_bucket_orthogonality_evidence": "S20普通上涨剩余桶工具周期正交性证据",
            "open_battles": "尚未决出的工具与上下文擂台",
            "unclaimed_bar_policy": "未认领K线处理方式",
            "runtime_route_fields": dict(ROUTE_FIELD_LABELS_ZH),
            "position_policy_fields": dict(POSITION_FIELD_LABELS_ZH),
        },
    }
    payload["semantic_digest"] = canonical_digest(payload)
    validate_timing_strategy_router_payload(payload)
    return payload


def validate_timing_strategy_router_payload(payload: dict[str, object]) -> None:
    """Fail closed on reordered tiers, hidden winner selection, or authority."""

    if payload.get("schema_id") != TIMING_STRATEGY_ROUTER_SCHEMA_ID:
        raise ValidationError("timing strategy router schema changed")
    if payload.get("router_version") != TIMING_STRATEGY_ROUTER_VERSION:
        raise ValidationError("timing strategy router version changed")
    if payload.get("architecture_status") != (
        "explosive_three_bucket_architecture_locked_ordinary_owners_open"
    ):
        raise ValidationError("timing strategy architecture status changed")
    if tuple(payload.get("route_tier_ids", ())) != ROUTE_TIER_IDS:
        raise ValidationError("timing route tiers changed")
    if tuple(payload.get("route_slot_ids", ())) != ROUTE_SLOT_IDS:
        raise ValidationError("timing route slots changed")
    tiers = payload.get("tiers")
    if not isinstance(tiers, list) or len(tiers) != 3:
        raise ValidationError("timing router must contain exactly three tiers")
    tier_rows = cast(list[dict[str, object]], tiers)
    flattened_slots: list[dict[str, object]] = []
    for tier in tier_rows:
        slots = tier.get("slots")
        if not isinstance(slots, list):
            raise ValidationError("every timing tier requires slots")
        flattened_slots.extend(cast(list[dict[str, object]], slots))
    if tuple(str(slot.get("slot_id")) for slot in flattened_slots) != ROUTE_SLOT_IDS:
        raise ValidationError("timing route slot order is inconsistent with the contract")
    if tuple(int(slot.get("slot_priority", -1)) for slot in flattened_slots) != (1, 2, 3, 4, 5):
        raise ValidationError("timing route slot priorities must be 1/2/3/4/5")
    if tier_rows != _architecture_tiers():
        raise ValidationError("timing route candidates cannot change outside a new contract version")
    expected_policies = [spec.to_dict() for spec in default_position_policy_specs()]
    if payload.get("position_policy_examples") != expected_policies:
        raise ValidationError("default position policy examples changed")
    development = payload.get("bidirectional_development_contract")
    expected_directional_exception = {
        "explosive_crash_rebound": {
            "active_directions": ["up"],
            "retired_directions": ["down"],
            "reason": "down direction retired after fixed-bucket graphical handoff attribution",
        }
    }
    if not isinstance(development, dict) or development.get(
        "approved_directional_exceptions"
    ) != expected_directional_exception:
        raise ValidationError("the approved up-only crash-rebound exception changed")
    custom_policy = payload.get("custom_position_policy_contract")
    expected_custom_policy = {
        "required_direction_keys": list(POLICY_DIRECTION_IDS),
        "allowed_targets": [-1.0, 0.0, 1.0, None],
        "none_semantics": "hold_previous_position",
        "consumer_must_register_separate_policy_id": True,
    }
    if custom_policy != expected_custom_policy:
        raise ValidationError("custom position policy contract is incomplete")
    if payload.get("open_battles") != [
        "ordinary_up_owner:no_cross_period_single_tool_survivor",
        "flat_child_owner:not_started_iir_delta_component_vs_paper_s5",
        "ordinary_down_owner:not_started",
    ]:
        raise ValidationError("open tool battles cannot be silently resolved")
    freeze = payload.get("explosive_bucket_freeze")
    expected_freeze = {
        "bucket_order": [
            "explosive_context_free_channel",
            "explosive_context_conditioned_channel",
            "explosive_crash_rebound",
        ],
        "active_direction_contract": {
            "explosive_context_free_channel": ["up", "down"],
            "explosive_context_conditioned_channel": ["up", "down"],
            "explosive_crash_rebound": ["up"],
        },
        "retired_bucket": "sharp_reversal/down",
        "retired_bucket_has_route_or_watch_authority": False,
        "architecture_lock_authority": True,
        "parameter_authority": False,
        "production_authority": False,
    }
    if freeze != expected_freeze:
        raise ValidationError("the three explosive route buckets cannot be changed without a new contract")
    v62 = payload.get("v62_example")
    if not isinstance(v62, dict) or v62.get("v62_runtime_modified") is not False:
        raise ValidationError("infrastructure cannot mutate V62 runtime")
    if payload.get("selection_data_rows_read") != 0 or payload.get("return_rows_read") != 0:
        raise ValidationError("architecture contract cannot read selection or return rows")
    for authority in (
        "production_authority",
        "dynamic_parameter_authority",
        "tool_selection_authority",
        "tool_routing_authority",
    ):
        if payload.get(authority) is not False:
            raise ValidationError(f"timing strategy router cannot grant {authority}")
    stored_digest = payload.get("semantic_digest")
    unsigned = dict(payload)
    _ = unsigned.pop("semantic_digest", None)
    if stored_digest != canonical_digest(unsigned):
        raise ValidationError("timing strategy router semantic digest mismatch")


def apply_timing_strategy_route(
    index: pd.Index,
    claims: tuple[TimingRouteClaim, ...],
) -> pd.DataFrame:
    """Assign each bar to at most one selected route slot and direction."""

    if index.empty or index.has_duplicates:
        raise ValidationError("timing route index must be non-empty and unique")
    if any(not claim.eligible.index.equals(index) for claim in claims):
        raise ValidationError("every route mask must exactly match the route index")
    keys = [(claim.slot_id, claim.direction_id) for claim in claims]
    if len(keys) != len(set(keys)):
        raise ValidationError("one selected route may have only one claim per slot and direction")

    result = pd.DataFrame(
        {
            "route_tier_id": "unassigned",
            "route_slot_id": "unassigned",
            "route_direction_id": "unassigned",
            "responsible_tool_id": "unassigned",
            "responsible_tool_profile_id": "unassigned",
            "responsible_state_id": "unassigned",
            "context_tool_id": "none",
            "context_profile_id": "none",
            "route_slot_priority": pd.Series(pd.NA, index=index, dtype="Int64"),
            "claimed": False,
        },
        index=index,
    )
    remaining = pd.Series(True, index=index, dtype=bool)
    for slot_id in ROUTE_SLOT_IDS:
        slot_claims = [claim for claim in claims if claim.slot_id == slot_id]
        if not slot_claims:
            continue
        overlap_count = sum(
            (claim.eligible.astype(int) for claim in slot_claims),
            start=pd.Series(0, index=index, dtype=int),
        )
        if bool(((overlap_count > 1) & remaining).any()):
            raise ValidationError(f"same-slot directional overlap requires arbitration: {slot_id}")
        for claim in slot_claims:
            newly_claimed = remaining & claim.eligible
            result.loc[newly_claimed, "route_tier_id"] = ROUTE_SLOT_TIER[slot_id]
            result.loc[newly_claimed, "route_slot_id"] = slot_id
            result.loc[newly_claimed, "route_direction_id"] = claim.direction_id
            result.loc[newly_claimed, "responsible_tool_id"] = claim.tool_id
            result.loc[newly_claimed, "responsible_tool_profile_id"] = claim.tool_profile_id
            result.loc[newly_claimed, "responsible_state_id"] = claim.state_id
            result.loc[newly_claimed, "context_tool_id"] = claim.context_tool_id or "none"
            result.loc[newly_claimed, "context_profile_id"] = claim.context_profile_id or "none"
            result.loc[newly_claimed, "route_slot_priority"] = ROUTE_SLOT_PRIORITY[slot_id]
            result.loc[newly_claimed, "claimed"] = True
            remaining.loc[newly_claimed] = False
    result["remaining_unassigned"] = remaining
    result["decision_clock"] = "closed_bar_for_next_bar"
    result.attrs["field_labels_zh"] = dict(ROUTE_FIELD_LABELS_ZH)
    return result


def _transition_action(previous: float, target: float) -> str:
    if previous == target:
        return {1.0: "hold_long", 0.0: "hold_flat", -1.0: "hold_short"}[target]
    transitions = {
        (0.0, 1.0): "open_long",
        (1.0, 0.0): "close_long",
        (0.0, -1.0): "open_short",
        (-1.0, 0.0): "close_short",
        (1.0, -1.0): "reverse_long_to_short",
        (-1.0, 1.0): "reverse_short_to_long",
    }
    return transitions[(previous, target)]


def apply_position_policy(
    route_result: pd.DataFrame,
    policy: PositionPolicySpec,
    *,
    initial_position: float = 0.0,
) -> pd.DataFrame:
    """Convert position-neutral route directions into next-bar target positions."""

    if initial_position not in {-1.0, 0.0, 1.0}:
        raise ValidationError("initial position must be -1, 0, or 1")
    if "route_direction_id" not in route_result.columns or route_result.index.has_duplicates:
        raise ValidationError("route result must contain unique indexed route directions")
    directions = route_result["route_direction_id"].astype(str)
    if not set(directions).issubset(POLICY_DIRECTION_IDS):
        raise ValidationError("route result contains a direction outside the policy contract")
    previous = initial_position
    targets: list[float] = []
    actions: list[str] = []
    for direction in directions:
        mapped = policy.target_by_direction[str(direction)]
        target = previous if mapped is None else float(mapped)
        targets.append(target)
        actions.append(_transition_action(previous, target))
        previous = target
    decision_target = pd.Series(targets, index=route_result.index, dtype=float)
    position_result = pd.DataFrame(
        {
            "position_policy_id": policy.policy_id,
            "route_direction_id": directions,
            "decision_target_position_for_next_bar": decision_target,
            "decision_transition_action": actions,
            "executable_position": decision_target.shift(1, fill_value=initial_position),
            "single_execution_shift": True,
        },
        index=route_result.index,
    )
    position_result.attrs["field_labels_zh"] = dict(POSITION_FIELD_LABELS_ZH)
    return position_result


__all__ = [
    "POLICY_DIRECTION_IDS",
    "POSITION_FIELD_LABELS_ZH",
    "ROUTE_DIRECTION_IDS",
    "ROUTE_FIELD_LABELS_ZH",
    "ROUTE_SLOT_IDS",
    "ROUTE_SLOT_PRIORITY",
    "ROUTE_TIER_IDS",
    "TIMING_STRATEGY_ROUTER_SCHEMA_ID",
    "TIMING_STRATEGY_ROUTER_VERSION",
    "PositionPolicySpec",
    "TimingRouteClaim",
    "apply_position_policy",
    "apply_timing_strategy_route",
    "build_timing_strategy_router_payload",
    "default_position_policy_specs",
    "validate_timing_strategy_router_payload",
]
