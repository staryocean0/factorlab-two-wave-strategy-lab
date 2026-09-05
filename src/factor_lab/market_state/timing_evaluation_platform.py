# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportCallIssue=false, reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportAssignmentType=false, reportOperatorIssue=false
# pyright: reportImplicitStringConcatenation=false, reportCallInDefaultInitializer=false
"""Unified project-level evaluation platform for timing strategies.

The platform composes the existing three-layer research gate, routed-account
counterfactuals and matched period attribution.  It adds a fair static versus
causal dynamic parameter comparison without collapsing the result to one
return number or one fitted score.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, cast

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_dynamic_reliability import (
    timing_dynamic_reliability_contract,
    validate_persisted_dynamic_reliability_package,
)
from factor_lab.market_state.timing_evaluation import timing_evaluation_contract
from factor_lab.market_state.timing_event_opportunity_attribution import (
    diagnose_mfbr_period_change,
    summarize_candidate_claims,
    summarize_event_opportunity_capture,
    summarize_mfbr_attribution,
    timing_event_opportunity_attribution_contract,
    validate_candidate_claim_ledger,
    validate_event_capture_ledger,
    validate_event_opportunity_ledger,
    validate_mfbr_ledger,
)
from factor_lab.market_state.timing_factor_failure_gate import (
    timing_factor_failure_gate_contract,
    validate_persisted_factor_failure_gate_package,
)
from factor_lab.market_state.timing_matched_attribution import timing_matched_attribution_contract
from factor_lab.market_state.timing_scale_oracle import timing_scale_oracle_contract
from factor_lab.market_state.timing_strategy_stage_evaluation import timing_strategy_stage_evaluation_contract

SCHEMA_ID: Final[str] = "market_state_timing_evaluation_platform@4.0"
CODE_VERSION: Final[str] = "timing-evaluation-platform-20260813-r9"
DEFAULT_OUTPUT_DIR: Final[Path] = Path("artifacts/market_state/timing_evaluation_platform_v4")
CANONICAL_ENTRYPOINT: Final[str] = "docs/user/market_state_timing_evaluation_platform_workflow.md"

ParameterMode = Literal["static", "causal_dynamic", "six_axis_dynamic"]
DYNAMIC_PARAMETER_MODES: Final[frozenset[str]] = frozenset(
    {"causal_dynamic", "six_axis_dynamic"}
)

IDENTITY_COLUMNS: Final[tuple[str, ...]] = (
    "candidate_id",
    "parameter_mode",
    "period",
    "period_role",
    "period_start",
    "period_end_exclusive",
    "opportunity_side",
    "state_cell_id",
    "opportunity_ledger_digest",
    "execution_semantics_digest",
    "cost_model_digest",
    "parameter_policy_digest",
    "six_axis_manifest_digest",
    "carrier_manifest_digest",
    "ledger_status",
)
MARKET_COLUMNS: Final[tuple[str, ...]] = (
    "elapsed_years",
    "market_opportunity_count",
    "market_opportunity_supply",
    "market_opportunity_bars",
)
ABILITY_COLUMNS: Final[tuple[str, ...]] = (
    "opportunity_capture_rate",
    "opportunity_recall_rate",
    "mean_remaining_opportunity_fraction",
    "gross_value_per_opportunity",
    "net_value_per_opportunity",
    "net_value_per_1000_bars",
    "conversion_efficiency",
    "daily_sharpe",
    "max_drawdown",
    "turnover_cost_per_opportunity",
)
POTENTIAL_COLUMNS: Final[tuple[str, ...]] = (
    "market_scale_oracle_net_value_per_year",
    "tool_family_oracle_net_value_per_year",
    "realized_net_value_per_year",
)
GROUP_COLUMNS: Final[tuple[str, ...]] = (
    "period",
    "period_role",
    "opportunity_side",
    "state_cell_id",
)
FIELD_LABELS_ZH: Final[dict[str, str]] = {
    "market_opportunity_count": "市场行情机会数",
    "market_opportunity_supply": "市场机会总幅度",
    "market_opportunity_bars": "市场趋势机会K线数",
    "opportunity_capture_rate": "机会幅度捕获率",
    "opportunity_recall_rate": "机会事件召回率",
    "mean_remaining_opportunity_fraction": "入场时平均剩余机会比例",
    "gross_value_per_opportunity": "单次机会毛价值",
    "net_value_per_opportunity": "单次机会净价值",
    "net_value_per_1000_bars": "每千根责任K线净价值",
    "conversion_efficiency": "捕获机会到净价值的转化效率",
    "daily_sharpe": "日频夏普",
    "max_drawdown": "最大回撤",
    "turnover_cost_per_opportunity": "单次机会换手成本",
    "market_scale_oracle_net_value_per_year": "该尺度市场事后可执行年均上限",
    "tool_family_oracle_net_value_per_year": "固定参数工具家族事后年均上限",
    "realized_net_value_per_year": "候选策略年均实现净价值",
    "tool_architecture_gap_per_year": "工具架构缺口",
    "parameter_matching_gap_per_year": "参数匹配缺口",
    "parameter_comparison": "静态与六轴动态参数公平对照",
    "market_supply_contribution_per_year": "跨期市场供给贡献",
    "tool_architecture_contribution_per_year": "跨期工具架构缺口贡献",
    "parameter_matching_contribution_per_year": "跨期参数匹配缺口贡献",
    "family_routing_gap_per_year": "工具族内事后路由缺口",
    "current_static_parameter_gap_per_year": "当前固定参数失配缺口",
    "captured_opportunity_supply": "从事件账本复算的已抓机会幅度",
    "missed_opportunity_supply": "从事件账本复算的漏抓机会幅度",
    "unmatched_claim_loss_log": "未匹配真实机会的责任仓损失",
    "dominant_decline_driver": "收益下降主导来源",
}


@dataclass(frozen=True, slots=True)
class TimingPotentialPolicy:
    """Numerical policy only; economic drift thresholds are forbidden."""

    numerical_tolerance: float = 1e-10

    def __post_init__(self) -> None:
        if not 0.0 < self.numerical_tolerance < 1e-4:
            raise ValueError("invalid timing potential evaluation policy")


def timing_evaluation_platform_contract() -> dict[str, object]:
    """Return the single public contract for all timing evaluation stages."""

    return {
        "schema_id": SCHEMA_ID,
        "code_version": CODE_VERSION,
        "infrastructure_owner": "independent_bidirectional_timing_strategy_middle_platform",
        "authority": "evaluation_only_not_signal_route_parameter_or_production_authority",
        "composed_contracts": {
            "scale_constrained_oracle": timing_scale_oracle_contract()["schema_id"],
            "event_opportunity_attribution": timing_event_opportunity_attribution_contract()[
                "schema_id"
            ],
            "component_three_layer": timing_strategy_stage_evaluation_contract()["schema_id"],
            "routed_account_counterfactual": timing_evaluation_contract()["schema_id"],
            "matched_period_attribution": timing_matched_attribution_contract()["schema_id"],
            "dynamic_reliability": timing_dynamic_reliability_contract()["schema_id"],
            "factor_failure_gate": timing_factor_failure_gate_contract()["schema_id"],
        },
        "canonical_evaluation_order": [
            "compute_same_execution_same_cost_scale_constrained_market_oracle",
            "compute_fixed_parameter_tool_family_oracle",
            "verify_strategy_independent_event_market_opportunity_ledger",
            "recompute_captured_partial_missed_supply_from_candidate_x_opportunity_rows",
            "reconcile_candidate_claims_and_unmatched_claim_losses",
            "split_family_oracle_best_registered_static_and_current_parameter_value",
            "evaluate_causal_hit_and_entry",
            "evaluate_complete_trade_lifecycle_when_available",
            "evaluate_fixed_surroundings_bucket_counterfactual_after_routing",
            "reject_full_sample_retrospective_static_oracle_and_bind_predevelopment_static_baseline",
            "reject_local_ablation_as_whole_strategy_and_verify_state_ownership_opportunity_disposition_and_full_path_repricing",
            "screen_candidate_factor_by_carrier_orthogonality_and_extreme_failure_relevance",
            "compare_static_and_dynamic_on_identical_fine_grained_blocks_for_reliability_first",
            "apply_pre_registered_long_run_viability_floor_then_prefer_higher_return",
            "separate_market_potential_supply_from_capture_unit_lifecycle_and_cost_drift",
            "run_matched_root_cause_attribution_when_flagged",
            "accept_authorized_post_2020_aggregate_blackbox_once",
        ],
        "market_potential_rule": (
            "market_supply_is_computed_as_a_scale_constrained_hindsight_account_ceiling_not_a_ratio_threshold"
        ),
        "event_evidence_enforcement": {
            "adapter_supplied_aggregate_capture_ratios_are_not_authoritative": True,
            "complete_candidate_x_opportunity_matrix_required": True,
            "candidate_claim_ledger_required": True,
            "candidate_claim_matches_recomputed_from_event_rows": True,
            "event_level_post_2020_blackbox_details_forbidden": True,
            "raw_event_ledgers_revalidated_after_persistence": True,
        },
        "static_dynamic_fairness": {
            "same_opportunity_ledger_digest_required": True,
            "same_execution_semantics_digest_required": True,
            "same_cost_model_digest_required": True,
            "same_period_side_and_six_axis_state_cells_required": True,
            "dynamic_candidate_must_bind_six_axis_manifest_and_frozen_policy": True,
            "single_weighted_winner_score_forbidden": True,
            "pareto_or_tradeoff_verdict_required": True,
            "market_and_tool_family_oracles_must_be_identical_inside_each_pair": True,
            "full_sample_retrospective_best_static_baseline_forbidden": True,
            "complete_policy_state_ownership_and_full_path_repricing_required": True,
        },
        "stability_first_rule": {
            "block_level_absolute_and_relative_failure_ledger_required_for_new_dynamic_candidates": True,
            "per_block_buy_hold_outperformance_required": False,
            "stability_pareto_before_return_preference": True,
            "pre_registered_long_run_viability_floor_required": True,
            "zero_exposure_pseudo_stability_rejected": True,
            "profitable_but_buy_hold_or_static_lagging_counts_as_relative_failure": True,
        },
        "factor_selection_gate": {
            "carrier_orthogonality_required": True,
            "large_absolute_or_relative_failure_extreme_relevance_required": True,
            "generic_return_correlation_is_insufficient": True,
            "tail_direction_and_threshold_must_be_fit_on_development_only": True,
        },
        "dynamic_evidence_enforcement": {
            "factor_failure_gate_package_required": True,
            "cross_period_reliability_package_required": True,
            "candidate_policy_carrier_ledger_execution_and_cost_bindings_required": True,
            "strategy_completeness_evidence_required": True,
            "missing_evidence_fails_closed": True,
        },
        "aggregate_blackbox_governance": {
            "aggregate_rows_only": True,
            "one_shot_authorization_receipt_required": True,
            "blackbox_input_digest_must_match": True,
            "detail_exposure_must_be_false": True,
        },
        "value_conservation_identity": (
            "realized=market_scale_oracle-tool_architecture_gap-parameter_matching_gap"
        ),
        "event_value_conservation_identity": (
            "R=M-(M-F)-(F-B)-(B-R)"
        ),
        "parameter_optimality_claim_rule": (
            "without_a_preregistered_bounded_fixed_parameter_family_only_parameter_mismatch_space_"
            "may_be_reported;_B_and_F_are_hindsight_diagnostics_and_never_global_optimality_authority"
        ),
        "weak_period_attribution_axes": [
            "market_supply_change",
            "tool_architecture_gap_change",
            "family_routing_gap_change",
            "current_static_parameter_gap_change",
        ],
        "economic_ratio_thresholds_for_drift_classification": "forbidden",
        "overfit_rule": (
            "aggregate_static_dynamic_return_comparison_is_diagnostic_only; "
            "overfit_or_stability_conclusions_require_the_block_level_reliability_ledger"
        ),
        "field_labels_zh": dict(FIELD_LABELS_ZH),
    }


def _parse_period_start_year(period_label: str) -> int | None:
    """Extract the first calendar year from a descriptive period label.

    Labels may start with a role prefix (for example
    ``aggregate_blackbox_2021_2026``) or with the calendar interval itself.
    Returns ``None`` only when no four-digit year is present.
    """

    match = re.search(r"(?<!\d)(?:19|20)\d{2}(?!\d)", str(period_label).strip())
    return int(match.group(0)) if match is not None else None


def validate_nested_potential_scorecard(scorecard: pd.DataFrame) -> None:
    """Validate the scale/family/candidate nesting for arbitrary candidates."""

    required = {*IDENTITY_COLUMNS, *MARKET_COLUMNS, *ABILITY_COLUMNS, *POTENTIAL_COLUMNS}
    missing = required.difference(scorecard.columns)
    if missing:
        raise ValidationError(f"timing comparison scorecard missing columns: {sorted(missing)}")
    if scorecard.empty:
        raise ValidationError("timing comparison scorecard must not be empty")
    if not set(scorecard["parameter_mode"].astype(str)).issubset(
        {"static", *DYNAMIC_PARAMETER_MODES}
    ):
        raise ValidationError("parameter_mode must be static or a registered causal dynamic mode")
    if not set(scorecard["period_role"].astype(str)).issubset(
        {"development", "repeat_audit", "aggregate_blackbox"}
    ):
        raise ValidationError("unsupported period_role")
    period_rows = scorecard[["period", "period_role", "period_start", "period_end_exclusive"]].drop_duplicates()
    if period_rows.groupby("period").size().gt(1).any():
        raise ValidationError("one period label cannot declare multiple roles or boundaries")
    boundaries: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {}
    for row in period_rows.itertuples(index=False):
        start = pd.to_datetime(row.period_start, errors="coerce", utc=True)
        end = pd.to_datetime(row.period_end_exclusive, errors="coerce", utc=True)
        if pd.isna(start) or pd.isna(end):
            raise ValidationError("period boundaries must be parseable timestamps")
        boundaries[str(row.period)] = (start, end)
    validate_period_governance(scorecard, period_boundaries=boundaries)
    # Calendar-boundary guard: aggregate_blackbox is a one-time post-2020
    # aggregate check on unconsumed data.  Any pre-2021 interval labelled
    # aggregate_blackbox is a fraudulent relabelling of in-sample history.
    for label, role in zip(
        scorecard["period"].astype(str), scorecard["period_role"].astype(str), strict=True
    ):
        if role == "aggregate_blackbox":
            start_year = _parse_period_start_year(label)
            if start_year is None or start_year < 2021:
                raise ValidationError(
                    f"aggregate_blackbox period must start in 2021 or later "
                    f"(post-2020 unconsumed data); got period={label}"
                )
    if not set(scorecard["opportunity_side"].astype(str)).issubset({"up", "down"}):
        raise ValidationError("up and down opportunities must remain separate")
    if not scorecard["ledger_status"].astype(str).eq("verified").all():
        raise ValidationError("market opportunity ledger must be verified before candidate comparison")

    numeric = scorecard[[*MARKET_COLUMNS, *ABILITY_COLUMNS, *POTENTIAL_COLUMNS]].apply(
        pd.to_numeric, errors="coerce"
    )
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy(float)).all():
        raise ValidationError("timing comparison metrics must be finite numeric values")
    for column in (
        "opportunity_capture_rate",
        "opportunity_recall_rate",
        "mean_remaining_opportunity_fraction",
        "conversion_efficiency",
    ):
        if not numeric[column].between(0.0, 1.0).all():
            raise ValidationError(f"{column} must lie in [0, 1]")
    if (numeric[["elapsed_years", "market_opportunity_count", "market_opportunity_supply", "market_opportunity_bars"]]
        .le(0.0)
        .any()
        .any()):
        raise ValidationError("market potential denominators must be positive")
    if numeric["turnover_cost_per_opportunity"].lt(0.0).any():
        raise ValidationError("turnover cost must be non-negative")
    if numeric["max_drawdown"].gt(0.0).any():
        raise ValidationError("max_drawdown must use the non-positive return convention")
    tolerance = TimingPotentialPolicy().numerical_tolerance
    if numeric["market_scale_oracle_net_value_per_year"].lt(-tolerance).any():
        raise ValidationError("market scale oracle must be non-negative because flat is available")
    if numeric["tool_family_oracle_net_value_per_year"].lt(-tolerance).any():
        raise ValidationError("tool family oracle must be non-negative because flat is available")
    if (
        numeric["tool_family_oracle_net_value_per_year"]
        > numeric["market_scale_oracle_net_value_per_year"] + tolerance
    ).any():
        raise ValidationError("tool family oracle cannot exceed market scale oracle")
    if (
        numeric["realized_net_value_per_year"]
        > numeric["tool_family_oracle_net_value_per_year"] + tolerance
    ).any():
        raise ValidationError("candidate cannot exceed the registered tool family oracle")

    dynamic = scorecard.loc[
        scorecard["parameter_mode"].astype(str).isin(DYNAMIC_PARAMETER_MODES)
    ]
    for column in ("six_axis_manifest_digest", "carrier_manifest_digest", "parameter_policy_digest"):
        values = dynamic[column].astype(str)
        if values.str.len().eq(0).any() or values.eq("not_applicable").any():
            raise ValidationError(f"dynamic candidate must bind {column}")


def validate_comparison_scorecard(scorecard: pd.DataFrame) -> None:
    """Fail closed unless static and dynamic candidates took the same exam."""

    validate_nested_potential_scorecard(scorecard)
    numeric = scorecard[[*MARKET_COLUMNS, *ABILITY_COLUMNS, *POTENTIAL_COLUMNS]].apply(
        pd.to_numeric, errors="coerce"
    )
    tolerance = TimingPotentialPolicy().numerical_tolerance

    for keys, local in scorecard.groupby(list(GROUP_COLUMNS), sort=False):
        modes = local["parameter_mode"].astype(str).value_counts().to_dict()
        dynamic_modes = [mode for mode in modes if mode in DYNAMIC_PARAMETER_MODES]
        if modes.get("static") != 1 or len(dynamic_modes) != 1 or modes[dynamic_modes[0]] != 1:
            raise ValidationError(f"each evaluation cell needs exactly one static and one dynamic row: {keys}")
        for column in (
            "opportunity_ledger_digest",
            "execution_semantics_digest",
            "cost_model_digest",
        ):
            if local[column].astype(str).nunique() != 1:
                raise ValidationError(f"unfair comparison: {column} differs inside {keys}")
        for column in MARKET_COLUMNS:
            values = numeric.loc[local.index, column].to_numpy(float)
            if not np.allclose(values, values[0], rtol=0.0, atol=1e-12):
                raise ValidationError(f"unfair comparison: market potential {column} differs inside {keys}")
        for column in POTENTIAL_COLUMNS[:2]:
            values = numeric.loc[local.index, column].to_numpy(float)
            if not np.allclose(values, values[0], rtol=0.0, atol=tolerance):
                raise ValidationError(f"unfair comparison: nested oracle {column} differs inside {keys}")


def validate_period_governance(
    scorecard: pd.DataFrame,
    *,
    period_boundaries: Mapping[str, tuple[pd.Timestamp, pd.Timestamp]],
    sealed_cutoff: pd.Timestamp = pd.Timestamp("2021-01-01"),
    development_end_exclusive: pd.Timestamp = pd.Timestamp("2018-01-01"),
) -> None:
    """Fail closed unless each period's calendar range matches its ``period_role``.

    The platform's default ``validate_comparison_scorecard`` only checks that
    ``period_role`` is a member of the enum.  Round-3 of the 波动通道/残差包络/
    状态空间包络工具组 rework requires the platform to also enforce the
    calendar boundary contract so that a pre-2021 slice can never be disguised
    as ``aggregate_blackbox``.

    ``period_boundaries`` maps each distinct ``period`` label in the scorecard
    to a ``(start, end_exclusive)`` pair.  The rules are:

    * ``development`` — ``end_exclusive <= development_end_exclusive``.
    * ``repeat_audit`` — ``start >= development_end_exclusive`` and
      ``end_exclusive <= sealed_cutoff``.
    * ``aggregate_blackbox`` — ``start >= sealed_cutoff``.  Any pre-2021
      slice labelled ``aggregate_blackbox`` fails closed.
    """

    if scorecard.empty:
        raise ValidationError("period governance requires a non-empty scorecard")
    labels = scorecard["period"].astype(str).unique()
    unknown = [str(label) for label in labels if str(label) not in period_boundaries]
    if unknown:
        raise ValidationError(f"period_boundaries missing entries for: {unknown}")
    sealed_cutoff = pd.to_datetime(sealed_cutoff, utc=True)
    development_end_exclusive = pd.to_datetime(development_end_exclusive, utc=True)
    if sealed_cutoff < development_end_exclusive:
        raise ValidationError("sealed_cutoff must not precede development_end_exclusive")
    for row in scorecard[["period", "period_role"]].drop_duplicates().itertuples(index=False):
        period_label = str(row.period)
        period_role = str(row.period_role)
        start, end_exclusive = period_boundaries[period_label]
        start = pd.to_datetime(start, utc=True)
        end_exclusive = pd.to_datetime(end_exclusive, utc=True)
        if start >= end_exclusive:
            raise ValidationError(f"period {period_label} has non-positive span")
        if period_role == "development":
            if end_exclusive > development_end_exclusive:
                raise ValidationError(
                    f"development period {period_label} extends past"
                    f" {development_end_exclusive.date()}"
                )
        elif period_role == "repeat_audit":
            if start < development_end_exclusive:
                raise ValidationError(
                    f"repeat_audit period {period_label} starts before"
                    f" {development_end_exclusive.date()}"
                )
            if end_exclusive > sealed_cutoff:
                raise ValidationError(
                    f"repeat_audit period {period_label} extends past the"
                    f" sealed cutoff {sealed_cutoff.date()}"
                )
        elif period_role == "aggregate_blackbox":
            if start < sealed_cutoff:
                raise ValidationError(
                    f"aggregate_blackbox period {period_label} starts before"
                    f" the sealed cutoff {sealed_cutoff.date()}; pre-2021 data"
                    f" must not be disguised as blackbox"
                )
        else:
            raise ValidationError(f"unsupported period_role: {period_role}")


def summarize_market_potential(scorecard: pd.DataFrame) -> pd.DataFrame:
    """Publish the market exam independently of any candidate's result."""

    validate_comparison_scorecard(scorecard)
    rows: list[dict[str, object]] = []
    for keys, local in scorecard.groupby(list(GROUP_COLUMNS), sort=True):
        first = local.iloc[0]
        years = float(first["elapsed_years"])
        count = float(first["market_opportunity_count"])
        supply = float(first["market_opportunity_supply"])
        bars = float(first["market_opportunity_bars"])
        rows.append(
            {
                **dict(zip(GROUP_COLUMNS, keys, strict=True)),
                "ledger_status": "verified",
                "opportunity_ledger_digest": str(first["opportunity_ledger_digest"]),
                "elapsed_years": years,
                "market_opportunity_count": count,
                "market_opportunities_per_year": count / years,
                "market_opportunity_supply": supply,
                "market_opportunity_supply_per_year": supply / years,
                "mean_market_opportunity_size": supply / count,
                "market_opportunity_bars": bars,
                "mean_market_opportunity_bars": bars / count,
                "performance_pass_fail_semantics": "forbidden",
            }
        )
    return pd.DataFrame(rows)


def summarize_candidate_potential_capture(scorecard: pd.DataFrame) -> pd.DataFrame:
    """Show how much of the verified opportunity ceiling each candidate mined."""

    validate_comparison_scorecard(scorecard)
    rows: list[dict[str, object]] = []
    for row in scorecard.itertuples(index=False):
        captured_supply = float(row.market_opportunity_supply) * float(row.opportunity_capture_rate)
        captured_count = float(row.market_opportunity_count) * float(row.opportunity_recall_rate)
        rows.append(
            {
                "candidate_id": str(row.candidate_id),
                "parameter_mode": str(row.parameter_mode),
                "period": str(row.period),
                "period_role": str(row.period_role),
                "opportunity_side": str(row.opportunity_side),
                "state_cell_id": str(row.state_cell_id),
                "verified_market_opportunity_supply": float(row.market_opportunity_supply),
                "captured_opportunity_supply": captured_supply,
                "missed_opportunity_supply": float(row.market_opportunity_supply) - captured_supply,
                "verified_market_opportunity_count": float(row.market_opportunity_count),
                "captured_opportunity_count": captured_count,
                "missed_opportunity_count": float(row.market_opportunity_count) - captured_count,
                "mean_remaining_opportunity_fraction": float(row.mean_remaining_opportunity_fraction),
                "opportunity_capture_rate": float(row.opportunity_capture_rate),
                "opportunity_recall_rate": float(row.opportunity_recall_rate),
                "performance_pass_fail_semantics": "forbidden",
                "economic_capture_threshold_used": False,
            }
        )
    return pd.DataFrame(rows)


def summarize_nested_potential(scorecard: pd.DataFrame) -> pd.DataFrame:
    """Expose the exact market/family/parameter value-conservation ledger."""

    validate_nested_potential_scorecard(scorecard)
    rows: list[dict[str, object]] = []
    for row in scorecard.itertuples(index=False):
        market = float(row.market_scale_oracle_net_value_per_year)
        family = float(row.tool_family_oracle_net_value_per_year)
        realized = float(row.realized_net_value_per_year)
        architecture_gap = market - family
        parameter_gap = family - realized
        rows.append(
            {
                "candidate_id": str(row.candidate_id),
                "parameter_mode": str(row.parameter_mode),
                "period": str(row.period),
                "period_role": str(row.period_role),
                "opportunity_side": str(row.opportunity_side),
                "state_cell_id": str(row.state_cell_id),
                "market_scale_oracle_net_value_per_year": market,
                "tool_family_oracle_net_value_per_year": family,
                "realized_net_value_per_year": realized,
                "tool_architecture_gap_per_year": architecture_gap,
                "parameter_matching_gap_per_year": parameter_gap,
                "value_conservation_error": realized
                - (market - architecture_gap - parameter_gap),
                "economic_ratio_threshold_used": False,
                "production_authority": False,
            }
        )
    return pd.DataFrame(rows)


def compare_static_and_dynamic(
    scorecard: pd.DataFrame,
    *,
    policy: TimingPotentialPolicy | None = None,
) -> pd.DataFrame:
    """Return Pareto/trade-off evidence instead of one fitted winner score."""

    validate_comparison_scorecard(scorecard)
    tolerance = (policy or TimingPotentialPolicy()).numerical_tolerance
    benefit_metrics = (*ABILITY_COLUMNS[:-1],)
    rows: list[dict[str, object]] = []
    for keys, local in scorecard.groupby(list(GROUP_COLUMNS), sort=True):
        indexed = local.set_index("parameter_mode")
        static = indexed.loc["static"]
        dynamic_modes = [mode for mode in indexed.index.astype(str) if mode in DYNAMIC_PARAMETER_MODES]
        if len(dynamic_modes) != 1:
            raise ValidationError(f"comparison needs one causal dynamic mode: {keys}")
        dynamic_mode = dynamic_modes[0]
        dynamic = indexed.loc[dynamic_mode]
        deltas: dict[str, float] = {}
        dynamic_better: list[bool] = []
        static_better: list[bool] = []
        for metric in benefit_metrics:
            delta = float(dynamic[metric]) - float(static[metric])
            deltas[f"dynamic_minus_static_{metric}"] = delta
            dynamic_better.append(delta >= -tolerance)
            static_better.append(delta <= tolerance)
        cost_delta = float(dynamic["turnover_cost_per_opportunity"]) - float(
            static["turnover_cost_per_opportunity"]
        )
        deltas["dynamic_minus_static_turnover_cost_per_opportunity"] = cost_delta
        dynamic_better.append(cost_delta <= tolerance)
        static_better.append(cost_delta >= -tolerance)
        dynamic_strict = any(value > tolerance for key, value in deltas.items() if "turnover_cost" not in key) or cost_delta < -tolerance
        static_strict = any(value < -tolerance for key, value in deltas.items() if "turnover_cost" not in key) or cost_delta > tolerance
        if all(dynamic_better) and dynamic_strict:
            verdict = f"{dynamic_mode}_pareto_dominates"
        elif all(static_better) and static_strict:
            verdict = "static_pareto_dominates"
        elif not dynamic_strict and not static_strict:
            verdict = "equivalent_on_registered_metrics"
        else:
            verdict = "tradeoff_no_universal_winner"
        static_realized = float(static["realized_net_value_per_year"])
        dynamic_realized = float(dynamic["realized_net_value_per_year"])
        family = float(static["tool_family_oracle_net_value_per_year"])
        static_parameter_gap = family - static_realized
        dynamic_parameter_gap = family - dynamic_realized
        rows.append(
            {
                **dict(zip(GROUP_COLUMNS, keys, strict=True)),
                "static_candidate_id": str(static["candidate_id"]),
                "dynamic_candidate_id": str(dynamic["candidate_id"]),
                "opportunity_ledger_digest": str(static["opportunity_ledger_digest"]),
                "six_axis_manifest_digest": str(dynamic["six_axis_manifest_digest"]),
                "parameter_policy_digest": str(dynamic["parameter_policy_digest"]),
                **deltas,
                "static_realized_net_value_per_year": static_realized,
                "dynamic_realized_net_value_per_year": dynamic_realized,
                "dynamic_minus_static_realized_net_value_per_year": dynamic_realized
                - static_realized,
                "static_parameter_matching_gap_per_year": static_parameter_gap,
                "dynamic_parameter_matching_gap_per_year": dynamic_parameter_gap,
                "dynamic_parameter_gap_reduction_per_year": static_parameter_gap
                - dynamic_parameter_gap,
                "comparison_verdict": verdict,
                "single_weighted_winner_score_used": False,
                "market_supply_cancels_in_paired_comparison": True,
                "parameter_authority": False,
            }
        )
    return pd.DataFrame(rows)


def diagnose_period_weakness(
    scorecard: pd.DataFrame,
    *,
    policy: TimingPotentialPolicy | None = None,
) -> pd.DataFrame:
    """Decompose realized change without fitted economic ratio thresholds."""

    validate_nested_potential_scorecard(scorecard)
    tolerance = (policy or TimingPotentialPolicy()).numerical_tolerance
    rows: list[dict[str, object]] = []
    for (candidate, side, state), local in scorecard.groupby(
        ["candidate_id", "opportunity_side", "state_cell_id"], sort=True
    ):
        reference_rows = local.loc[local["period_role"].astype(str).eq("development")]
        if len(reference_rows) != 1:
            raise ValidationError(f"candidate cell needs one development row: {(candidate, side, state)}")
        reference = reference_rows.iloc[0]
        for row in local.loc[~local["period_role"].astype(str).eq("development")].itertuples(index=False):
            reference_market = float(reference["market_scale_oracle_net_value_per_year"])
            reference_family = float(reference["tool_family_oracle_net_value_per_year"])
            reference_realized = float(reference["realized_net_value_per_year"])
            evaluation_market = float(row.market_scale_oracle_net_value_per_year)
            evaluation_family = float(row.tool_family_oracle_net_value_per_year)
            evaluation_realized = float(row.realized_net_value_per_year)
            reference_architecture_gap = reference_market - reference_family
            evaluation_architecture_gap = evaluation_market - evaluation_family
            reference_parameter_gap = reference_family - reference_realized
            evaluation_parameter_gap = evaluation_family - evaluation_realized
            realized_change = evaluation_realized - reference_realized
            market_contribution = evaluation_market - reference_market
            architecture_contribution = -(evaluation_architecture_gap - reference_architecture_gap)
            parameter_contribution = -(evaluation_parameter_gap - reference_parameter_gap)
            closure_error = realized_change - (
                market_contribution + architecture_contribution + parameter_contribution
            )
            deteriorations = {
                "market_scale_opportunity_supply_decline": max(0.0, -market_contribution),
                "tool_architecture_gap_widening": max(0.0, -architecture_contribution),
                "parameter_matching_gap_widening": max(0.0, -parameter_contribution),
            }
            if realized_change >= -tolerance:
                diagnosis = "no_realized_decline"
            else:
                maximum = max(deteriorations.values())
                leaders = [
                    name for name, value in deteriorations.items() if abs(value - maximum) <= tolerance
                ]
                diagnosis = leaders[0] if len(leaders) == 1 else "mixed_equal_decline_contributors"
            rows.append(
                {
                    "candidate_id": candidate,
                    "parameter_mode": str(row.parameter_mode),
                    "opportunity_side": side,
                    "state_cell_id": state,
                    "reference_period": str(reference["period"]),
                    "evaluation_period": str(row.period),
                    "evaluation_period_role": str(row.period_role),
                    "reference_market_scale_oracle_net_value_per_year": reference_market,
                    "evaluation_market_scale_oracle_net_value_per_year": evaluation_market,
                    "reference_tool_architecture_gap_per_year": reference_architecture_gap,
                    "evaluation_tool_architecture_gap_per_year": evaluation_architecture_gap,
                    "reference_parameter_matching_gap_per_year": reference_parameter_gap,
                    "evaluation_parameter_matching_gap_per_year": evaluation_parameter_gap,
                    "realized_net_value_change_per_year": realized_change,
                    "market_supply_contribution_per_year": market_contribution,
                    "tool_architecture_contribution_per_year": architecture_contribution,
                    "parameter_matching_contribution_per_year": parameter_contribution,
                    "market_supply_deterioration_per_year": deteriorations[
                        "market_scale_opportunity_supply_decline"
                    ],
                    "tool_architecture_deterioration_per_year": deteriorations[
                        "tool_architecture_gap_widening"
                    ],
                    "parameter_matching_deterioration_per_year": deteriorations[
                        "parameter_matching_gap_widening"
                    ],
                    "market_supply_decline_flag": market_contribution < -tolerance,
                    "parameter_drift_flag": parameter_contribution < -tolerance,
                    "dominant_decline_driver": diagnosis,
                    "value_conservation_error": closure_error,
                    "economic_ratio_threshold_used": False,
                }
            )
    return pd.DataFrame(rows)


def classify_parameter_generalization(
    comparison: pd.DataFrame,
    period_diagnosis: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Report aggregate cross-period returns without calling stability or overfit.

    A phase aggregate cannot tell whether a dynamic policy reduced tail losses
    or merely exchanged one extreme block for another.  The block-level
    reliability contract is now the sole authority for that question.  This
    legacy-compatible table remains useful only as a decomposition input.
    """

    _ = period_diagnosis

    required = {
        *GROUP_COLUMNS,
        "dynamic_candidate_id",
        "dynamic_parameter_gap_reduction_per_year",
        "comparison_verdict",
    }
    missing = required.difference(comparison.columns)
    if missing:
        raise ValidationError(f"parameter comparison missing columns: {sorted(missing)}")
    rows: list[dict[str, object]] = []
    for (side, state), local in comparison.groupby(["opportunity_side", "state_cell_id"], sort=True):
        roles = local.set_index("period_role")
        if not {"development", "repeat_audit"}.issubset(set(roles.index.astype(str))):
            raise ValidationError(f"generalization needs development and repeat audit: {(side, state)}")
        development_delta = float(roles.loc["development", "dynamic_parameter_gap_reduction_per_year"])
        audit_delta = float(roles.loc["repeat_audit", "dynamic_parameter_gap_reduction_per_year"])
        has_blackbox = "aggregate_blackbox" in set(roles.index.astype(str))
        blackbox_delta = (
            float(roles.loc["aggregate_blackbox", "dynamic_parameter_gap_reduction_per_year"])
            if has_blackbox
            else float("nan")
        )
        candidate = str(roles.loc["development", "dynamic_candidate_id"])
        tolerance = TimingPotentialPolicy().numerical_tolerance
        repeated_aggregate_weakness = has_blackbox and audit_delta < -tolerance and blackbox_delta < -tolerance
        if development_delta <= tolerance:
            verdict = "aggregate_return_not_superior_in_development_reliability_gate_required"
        elif repeated_aggregate_weakness:
            verdict = "post_development_aggregate_return_weaker_reliability_gate_required"
        elif audit_delta >= -tolerance and (not has_blackbox or blackbox_delta >= -tolerance):
            verdict = "aggregate_return_noninferior_reliability_gate_required"
        else:
            verdict = "cross_period_aggregate_tradeoff_reliability_gate_required"
        rows.append(
            {
                "opportunity_side": side,
                "state_cell_id": state,
                "dynamic_candidate_id": candidate,
                "development_parameter_gap_reduction_per_year": development_delta,
                "repeat_audit_parameter_gap_reduction_per_year": audit_delta,
                "aggregate_blackbox_parameter_gap_reduction_per_year": blackbox_delta,
                "repeated_post_development_aggregate_weakness": repeated_aggregate_weakness,
                "market_supply_cancels_in_paired_comparison": True,
                "aggregate_return_only": True,
                "block_reliability_evidence_required": True,
                "generalization_verdict": verdict,
                "parameter_authority": False,
            }
        )
    return pd.DataFrame(rows)


def build_evaluation_surface_inventory() -> list[dict[str, object]]:
    """Record every known timing-evaluation surface and its migration state."""

    return [
        {
            "surface_id": "event_opportunity_capture_and_mfbr_attribution",
            "owner_before": "aggregate_scorecard_adapters_and_strategy_specific_scripts",
            "canonical_module": (
                "factor_lab.market_state.timing_event_opportunity_attribution"
            ),
            "status": "canonical_common_kernel",
            "capabilities": [
                "strategy_independent_opportunity_ledger",
                "candidate_x_opportunity_capture",
                "candidate_claim_reconciliation",
                "mfbr_value_conservation",
                "weak_period_root_cause",
            ],
        },
        {
            "surface_id": "component_three_layer",
            "owner_before": "market_state",
            "canonical_module": "factor_lab.market_state.timing_strategy_stage_evaluation",
            "status": "canonical_common_kernel",
            "capabilities": ["opportunity", "entry", "trade"],
        },
        {
            "surface_id": "routed_bucket_counterfactual",
            "owner_before": "market_state_with_risk_off_adapters",
            "canonical_module": "factor_lab.market_state.timing_evaluation",
            "status": "canonical_common_kernel",
            "capabilities": ["bucket_counterfactual", "normalized_drift", "acceptance_gate"],
        },
        {
            "surface_id": "cross_period_matched_attribution",
            "owner_before": "risk_off_strategy_service",
            "canonical_module": "factor_lab.market_state.timing_matched_attribution",
            "status": "migrated_to_common_kernel_with_compatibility_adapter",
            "capabilities": ["knn", "propensity", "shapley", "unit_value_decomposition"],
        },
        {
            "surface_id": "risk_off_v62",
            "owner_before": "risk_off_strategy",
            "canonical_module": "strategy_specific_adapter",
            "status": "registered_reference_adapter",
            "capabilities": ["downside_opportunity", "bucket_counterfactual", "matched_attribution"],
        },
        {
            "surface_id": "frozen_explosive_three_bucket_layer",
            "owner_before": "market_state_strategy_research",
            "canonical_module": "strategy_specific_adapter",
            "status": "registered_reference_adapter",
            "capabilities": ["bidirectional_opportunity", "calendar_drift", "aggregate_blackbox"],
        },
        {
            "surface_id": "three_specialist_no_iir_event_sample",
            "owner_before": "market_state_strategy_research",
            "canonical_module": (
                "scripts.evaluate_market_state_three_specialist_no_iir_event_attribution_v1"
            ),
            "status": "registered_reproducible_reference_adapter",
            "capabilities": [
                "event_opportunity_sensitivity_atlas",
                "candidate_claim_reconciliation",
                "mfbr_value_conservation",
                "annual_weak_period_attribution",
                "sealed_post_2020_detail_guard",
            ],
        },
        {
            "surface_id": "single_four_hour_downside",
            "owner_before": "market_state_strategy_research",
            "canonical_module": "strategy_specific_adapter",
            "status": "registered_reference_adapter",
            "capabilities": ["opportunity", "entry", "trade", "aggregate_blackbox"],
        },
        {
            "surface_id": "filter_timing_and_cloudridge_2_5",
            "owner_before": "filtering_strategy",
            "canonical_module": "common_static_dynamic_scorecard_adapter_contract",
            "status": "registered_via_common_scorecard_adapter_contract",
            "capabilities": [
                "static_dynamic",
                "walk_forward",
                "cost_stress",
                "drawdown",
                "visual_review",
                "block_reliability",
                "carrier_orthogonal_failure_gate",
            ],
        },
    ]


def _validate_dynamic_evidence_bindings(
    scorecard: pd.DataFrame,
    *,
    dynamic_reliability_package: Path,
    factor_failure_gate_packages: Sequence[Path],
) -> None:
    """Fail closed unless every dynamic candidate binds both strict evidence gates."""

    validate_persisted_dynamic_reliability_package(dynamic_reliability_package)
    if not factor_failure_gate_packages:
        raise ValidationError("dynamic evaluation requires at least one factor failure gate package")
    for package in factor_failure_gate_packages:
        validate_persisted_factor_failure_gate_package(package)

    dynamic_rows = scorecard.loc[
        scorecard["parameter_mode"].astype(str).isin(DYNAMIC_PARAMETER_MODES)
    ]
    candidate_ids = set(dynamic_rows["candidate_id"].astype(str))
    reliability_manifest = _read_json(dynamic_reliability_package / "manifest.json")
    reliability_candidates = {str(value) for value in reliability_manifest.get("candidate_ids", [])}
    if not candidate_ids.issubset(reliability_candidates):
        raise ValidationError("dynamic reliability package does not cover every dynamic candidate")
    cross_period = pd.read_csv(dynamic_reliability_package / "cross_period_reliability.csv")
    accepted_reliability = set(
        cross_period.loc[cross_period["cross_period_dynamic_is_usable"].astype(bool), "dynamic_candidate_id"].astype(str)
    )
    if not candidate_ids.issubset(accepted_reliability):
        raise ValidationError("a dynamic candidate failed cross-period reliability")
    reliability_policy = _read_json(dynamic_reliability_package / "policy.json").get("policy")
    if not isinstance(reliability_policy, Mapping):
        raise ValidationError("dynamic reliability policy binding is malformed")
    if not dynamic_rows["parameter_policy_digest"].astype(str).eq(
        str(reliability_policy.get("dynamic_policy_digest"))
    ).all():
        raise ValidationError("platform dynamic policy does not match reliability evidence")

    evidence_results = [_read_json(package / "result.json") for package in factor_failure_gate_packages]
    accepted_factor_candidates = {
        str(result.get("candidate_id"))
        for result in evidence_results
        if result.get("accepted_for_low_capacity_hypothesis") is True
    }
    if not candidate_ids.issubset(accepted_factor_candidates):
        raise ValidationError("every dynamic candidate needs an accepted factor failure gate")
    carrier_by_candidate = {
        str(result.get("candidate_id")): str(result.get("carrier_manifest_digest"))
        for result in evidence_results
        if result.get("accepted_for_low_capacity_hypothesis") is True
    }
    for candidate_id, local in dynamic_rows.groupby("candidate_id", sort=False):
        if not local["carrier_manifest_digest"].astype(str).eq(carrier_by_candidate[str(candidate_id)]).all():
            raise ValidationError("factor gate carrier manifest does not match the evaluated strategy")

    nonblackbox = scorecard.loc[~scorecard["period_role"].astype(str).eq("aggregate_blackbox")]
    for scorecard_column, manifest_key in (
        ("opportunity_ledger_digest", "opportunity_ledger_digests"),
        ("execution_semantics_digest", "execution_semantics_digests"),
        ("cost_model_digest", "cost_model_digests"),
    ):
        actual = set(nonblackbox[scorecard_column].astype(str))
        expected = {str(value) for value in reliability_manifest.get(manifest_key, [])}
        if actual != expected:
            raise ValidationError(f"platform and reliability evidence disagree on {scorecard_column}")


def aggregate_blackbox_scorecard_digest(scorecard: pd.DataFrame) -> str:
    """Return the canonical digest bound by a one-shot aggregate receipt.

    The digest deliberately covers only the already-aggregated black-box rows.
    It does not authorize, accept, or persist event-level post-2020 details.
    """

    blackbox = scorecard.loc[
        scorecard["period_role"].astype(str).eq("aggregate_blackbox")
    ].copy()
    if blackbox.empty:
        raise ValidationError("aggregate blackbox digest requires aggregate_blackbox rows")
    blackbox = blackbox.sort_values(
        ["period", "opportunity_side", "state_cell_id", "parameter_mode", "candidate_id"],
        kind="stable",
    ).reset_index(drop=True)
    # Twelve significant digits are enough for aggregate evaluation metrics and
    # remain stable across the package's CSV write/read round trip.  Using the
    # binary float's full 17 digits would make semantically identical receipts
    # fail because a CSV parser may choose the adjacent representable float.
    payload = blackbox.to_csv(index=False, float_format="%.12g", lineterminator="\n").encode()
    return hashlib.sha256(payload).hexdigest()


def _validate_aggregate_blackbox_receipt(
    scorecard: pd.DataFrame,
    receipt: Mapping[str, object] | None,
) -> None:
    """Fail closed when post-2020 aggregate rows lack a bound one-shot receipt."""

    blackbox = scorecard.loc[
        scorecard["period_role"].astype(str).eq("aggregate_blackbox")
    ]
    if blackbox.empty:
        if receipt is not None:
            raise ValidationError("aggregate blackbox receipt supplied without blackbox rows")
        return
    if receipt is None:
        raise ValidationError("aggregate blackbox rows require a one-shot authorization receipt")
    required = {
        "schema_id",
        "periods",
        "aggregate_only",
        "details_exposed",
        "one_shot_authorized",
        "opened_at_utc",
        "authorization_digest",
        "blackbox_scorecard_digest",
    }
    if set(receipt) != required:
        raise ValidationError("aggregate blackbox receipt fields are incomplete or unexpected")
    if receipt.get("schema_id") != "market_state_timing_aggregate_blackbox_receipt@1.0":
        raise ValidationError("aggregate blackbox receipt schema drifted")
    if receipt.get("aggregate_only") is not True or receipt.get("details_exposed") is not False:
        raise ValidationError("blackbox receipt must attest aggregate-only use without detail exposure")
    if receipt.get("one_shot_authorized") is not True:
        raise ValidationError("blackbox receipt lacks one-shot authorization")
    opened = pd.to_datetime(receipt.get("opened_at_utc"), errors="coerce", utc=True)
    if pd.isna(opened):
        raise ValidationError("blackbox receipt opened_at_utc is invalid")
    authorization_digest = str(receipt.get("authorization_digest", ""))
    if re.fullmatch(r"[0-9a-f]{64}", authorization_digest) is None:
        raise ValidationError("blackbox receipt authorization_digest must be sha256")
    expected_periods = sorted(blackbox["period"].astype(str).unique())
    periods = receipt.get("periods")
    if not isinstance(periods, list) or [str(value) for value in periods] != expected_periods:
        raise ValidationError("blackbox receipt does not bind the exact aggregate periods")
    if str(receipt.get("blackbox_scorecard_digest")) != aggregate_blackbox_scorecard_digest(scorecard):
        raise ValidationError("blackbox receipt does not bind the supplied aggregate scorecard")


def run_timing_evaluation_platform(
    *,
    output_dir: Path,
    scorecard: pd.DataFrame | None = None,
    dynamic_reliability_package: Path | None = None,
    factor_failure_gate_packages: Sequence[Path] = (),
    aggregate_blackbox_receipt: Mapping[str, object] | None = None,
    event_opportunity_ledger: pd.DataFrame | None = None,
    event_capture_ledger: pd.DataFrame | None = None,
    candidate_claim_ledger: pd.DataFrame | None = None,
    mfbr_ledger: pd.DataFrame | None = None,
    mfbr_reference_period: str | None = None,
) -> dict[str, object]:
    """Persist the contract and optionally evaluate a prepared common scorecard."""

    contract = timing_evaluation_platform_contract()
    inventory = build_evaluation_surface_inventory()
    tables: dict[str, pd.DataFrame] = {}
    if scorecard is not None:
        if dynamic_reliability_package is None:
            raise ValidationError("dynamic scorecard requires a dynamic reliability evidence package")
        validate_comparison_scorecard(scorecard)
        _validate_aggregate_blackbox_receipt(scorecard, aggregate_blackbox_receipt)
        _validate_dynamic_evidence_bindings(
            scorecard,
            dynamic_reliability_package=dynamic_reliability_package,
            factor_failure_gate_packages=factor_failure_gate_packages,
        )
        potential = summarize_market_potential(scorecard)
        candidate_capture = summarize_candidate_potential_capture(scorecard)
        nested_potential = summarize_nested_potential(scorecard)
        comparison = compare_static_and_dynamic(scorecard)
        diagnosis = diagnose_period_weakness(scorecard)
        generalization = classify_parameter_generalization(comparison, diagnosis)
        tables = {
            "input_scorecard.csv": scorecard,
            "market_potential.csv": potential,
            "candidate_potential_capture.csv": candidate_capture,
            "nested_potential_attribution.csv": nested_potential,
            "static_dynamic_comparison.csv": comparison,
            "period_weakness_attribution.csv": diagnosis,
            "dynamic_parameter_generalization.csv": generalization,
        }

    event_inputs = (
        event_opportunity_ledger,
        event_capture_ledger,
        candidate_claim_ledger,
    )
    if any(frame is not None for frame in event_inputs):
        if any(frame is None for frame in event_inputs):
            raise ValidationError(
                "event-backed evaluation requires opportunity, capture, and claim ledgers together"
            )
        opportunities = cast(pd.DataFrame, event_opportunity_ledger)
        captures = cast(pd.DataFrame, event_capture_ledger)
        claims = cast(pd.DataFrame, candidate_claim_ledger)
        _validate_detailed_event_boundary(opportunities, claims)
        validate_event_opportunity_ledger(opportunities)
        validate_event_capture_ledger(opportunities, captures)
        validate_candidate_claim_ledger(claims, opportunities, captures)
        tables.update(
            {
                "event_opportunity_ledger.csv": opportunities,
                "event_capture_ledger.csv": captures,
                "candidate_claim_ledger.csv": claims,
                "event_opportunity_capture_summary.csv": summarize_event_opportunity_capture(
                    opportunities, captures
                ),
                "candidate_claim_summary.csv": summarize_candidate_claims(
                    claims, opportunities, captures
                ),
            }
        )
    elif mfbr_ledger is not None:
        raise ValidationError("M/F/B/R evidence requires the event-backed opportunity exam")

    if mfbr_ledger is not None:
        validate_mfbr_ledger(mfbr_ledger)
        tables["mfbr_input_ledger.csv"] = mfbr_ledger
        tables["mfbr_attribution.csv"] = summarize_mfbr_attribution(mfbr_ledger)
        if mfbr_reference_period is not None:
            tables["mfbr_period_weakness_attribution.csv"] = diagnose_mfbr_period_change(
                mfbr_ledger,
                reference_period=mfbr_reference_period,
            )

    output = output_dir.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="timing-evaluation-platform-", dir=output.parent) as tmp:
        staging = Path(tmp)
        _write_json(staging / "contract.json", contract)
        _write_json(
            staging / "evaluation_surface_inventory.json",
            {"schema_id": "market_state_timing_evaluation_surface_inventory@1.0", "surfaces": inventory},
        )
        for name, frame in tables.items():
            frame.to_csv(staging / name, index=False, float_format="%.17g")
        if aggregate_blackbox_receipt is not None:
            _write_json(staging / "aggregate_blackbox_receipt.json", aggregate_blackbox_receipt)
        if scorecard is not None and dynamic_reliability_package is not None:
            evidence_root = staging / "evidence"
            _ = evidence_root.mkdir(parents=True, exist_ok=True)
            _ = shutil.copytree(dynamic_reliability_package, evidence_root / "dynamic_reliability")
            factor_root = evidence_root / "factor_failure_gates"
            _ = factor_root.mkdir(parents=True, exist_ok=True)
            for index, package in enumerate(factor_failure_gate_packages):
                _ = shutil.copytree(package, factor_root / f"factor_{index:03d}")
        _ = (staging / "report_zh.md").write_text(
            _build_report(scorecard, tables, inventory), encoding="utf-8"
        )
        manifest = _build_manifest(
            staging,
            scorecard_loaded=scorecard is not None,
            event_evidence_loaded=event_opportunity_ledger is not None,
            mfbr_loaded=mfbr_ledger is not None,
            mfbr_reference_period=mfbr_reference_period,
        )
        _write_json(staging / "manifest.json", manifest)
        if output.exists():
            shutil.rmtree(output)
        _ = shutil.copytree(staging, output)
    validate_persisted_timing_evaluation_platform(output)
    return _read_json(output / "manifest.json")


def _assert_persisted_frame_matches(
    output_dir: Path,
    filename: str,
    expected: pd.DataFrame,
) -> None:
    """Recompute a derived CSV and fail closed on semantic drift."""

    path = output_dir / filename
    if not path.is_file():
        raise ValidationError(f"timing evaluation platform missing derived table: {filename}")
    actual = pd.read_csv(path)
    try:
        pd.testing.assert_frame_equal(
            actual.reset_index(drop=True),
            expected.reset_index(drop=True),
            check_dtype=False,
            check_exact=False,
            rtol=1e-12,
            atol=1e-12,
        )
    except AssertionError as exc:
        raise ValidationError(
            f"timing evaluation platform derived table does not replay: {filename}"
        ) from exc


def validate_persisted_timing_evaluation_platform(output_dir: Path) -> None:
    """Validate contract lineage, authority and artifact hashes."""

    required = {"contract.json", "evaluation_surface_inventory.json", "report_zh.md", "manifest.json"}
    missing = sorted(name for name in required if not (output_dir / name).exists())
    if missing:
        raise ValidationError(f"timing evaluation platform missing files: {missing}")
    contract = _read_json(output_dir / "contract.json")
    if contract.get("schema_id") != SCHEMA_ID:
        raise ValidationError("timing evaluation platform schema drifted")
    if "not_signal_route_parameter_or_production_authority" not in str(contract.get("authority")):
        raise ValidationError("timing evaluation platform gained forbidden authority")
    composed = contract.get("composed_contracts")
    if not isinstance(composed, Mapping) or set(composed) != {
        "scale_constrained_oracle",
        "event_opportunity_attribution",
        "component_three_layer",
        "routed_account_counterfactual",
        "matched_period_attribution",
        "dynamic_reliability",
        "factor_failure_gate",
    }:
        raise ValidationError("timing evaluation platform lost a required evaluation layer")
    event_enforcement = contract.get("event_evidence_enforcement")
    if not isinstance(event_enforcement, Mapping) or not all(
        bool(value) for value in event_enforcement.values()
    ):
        raise ValidationError("timing evaluation platform lost raw event evidence enforcement")
    stability_rule = contract.get("stability_first_rule")
    factor_gate = contract.get("factor_selection_gate")
    evidence_enforcement = contract.get("dynamic_evidence_enforcement")
    blackbox_governance = contract.get("aggregate_blackbox_governance")
    expected_stability_rule = {
        "block_level_absolute_and_relative_failure_ledger_required_for_new_dynamic_candidates": True,
        "per_block_buy_hold_outperformance_required": False,
        "stability_pareto_before_return_preference": True,
        "pre_registered_long_run_viability_floor_required": True,
        "zero_exposure_pseudo_stability_rejected": True,
        "profitable_but_buy_hold_or_static_lagging_counts_as_relative_failure": True,
    }
    if not isinstance(stability_rule, Mapping) or dict(stability_rule) != expected_stability_rule:
        raise ValidationError("timing evaluation platform lost stability-first governance")
    if not isinstance(factor_gate, Mapping) or not all(bool(value) for value in factor_gate.values()):
        raise ValidationError("timing evaluation platform lost factor failure gate")
    if not isinstance(evidence_enforcement, Mapping) or not all(
        bool(value) for value in evidence_enforcement.values()
    ):
        raise ValidationError("timing evaluation platform stopped enforcing dynamic evidence")
    if not isinstance(blackbox_governance, Mapping) or not all(
        bool(value) for value in blackbox_governance.values()
    ):
        raise ValidationError("timing evaluation platform stopped enforcing blackbox receipts")
    manifest = _read_json(output_dir / "manifest.json")
    for item in cast(Sequence[Mapping[str, object]], manifest.get("artifacts", [])):
        path = output_dir / str(item["path"])
        if _sha256(path) != item["sha256"]:
            raise ValidationError(f"timing evaluation platform artifact hash mismatch: {path.name}")
    if manifest.get("scorecard_loaded") is True:
        scorecard = pd.read_csv(output_dir / "input_scorecard.csv")
        receipt_path = output_dir / "aggregate_blackbox_receipt.json"
        receipt = _read_json(receipt_path) if receipt_path.exists() else None
        _validate_aggregate_blackbox_receipt(scorecard, receipt)
        dynamic_package = output_dir / "evidence" / "dynamic_reliability"
        factor_root = output_dir / "evidence" / "factor_failure_gates"
        factor_packages = tuple(sorted(path for path in factor_root.iterdir() if path.is_dir()))
        _validate_dynamic_evidence_bindings(
            scorecard,
            dynamic_reliability_package=dynamic_package,
            factor_failure_gate_packages=factor_packages,
        )
    if manifest.get("event_evidence_loaded") is True:
        opportunities = pd.read_csv(output_dir / "event_opportunity_ledger.csv")
        captures = pd.read_csv(output_dir / "event_capture_ledger.csv")
        claims = pd.read_csv(output_dir / "candidate_claim_ledger.csv")
        _validate_detailed_event_boundary(opportunities, claims)
        validate_event_capture_ledger(opportunities, captures)
        validate_candidate_claim_ledger(claims, opportunities, captures)
        _assert_persisted_frame_matches(
            output_dir,
            "event_opportunity_capture_summary.csv",
            summarize_event_opportunity_capture(opportunities, captures),
        )
        _assert_persisted_frame_matches(
            output_dir,
            "candidate_claim_summary.csv",
            summarize_candidate_claims(claims, opportunities, captures),
        )
    if manifest.get("mfbr_loaded") is True:
        mfbr = pd.read_csv(output_dir / "mfbr_input_ledger.csv")
        validate_mfbr_ledger(mfbr)
        _assert_persisted_frame_matches(
            output_dir,
            "mfbr_attribution.csv",
            summarize_mfbr_attribution(mfbr),
        )
        reference = manifest.get("mfbr_reference_period")
        if reference is not None:
            _assert_persisted_frame_matches(
                output_dir,
                "mfbr_period_weakness_attribution.csv",
                diagnose_mfbr_period_change(mfbr, reference_period=str(reference)),
            )


def _build_report(
    scorecard: pd.DataFrame | None,
    tables: Mapping[str, pd.DataFrame],
    inventory: Sequence[Mapping[str, object]],
) -> str:
    evaluated = scorecard is not None
    event_evaluated = "event_opportunity_ledger.csv" in tables
    mfbr_evaluated = "mfbr_input_ledger.csv" in tables
    return f"""# 择时策略统一评价中台报告

## 状态

- 公共合同：`{SCHEMA_ID}`
- 已盘点评价面：`{len(inventory)}`
- 本次是否载入策略评分表：`{str(evaluated).lower()}`
- 本次是否载入事件级机会/抓取/责任仓账本：`{str(event_evaluated).lower()}`
- 本次是否载入 M/F/B/R 归因：`{str(mfbr_evaluated).lower()}`
- 生产、路由、参数权限：`false`

## 统一尺子

先验证市场机会账本是否忠实，再用完整的候选×机会矩阵重算已抓、部分抓取和漏抓；
不再接受适配器先填的捕获比例作为权威证据。责任仓中没有匹配同向机会的生命周期单独记为假认领。
然后再评价命中入场、完整交易、路由后桶内反事实。
静态和因果动态参数必须使用同一机会账本、执行时钟、成本口径和状态单元。
动态候选可使用六个公共轴及工具类专属正交属性；`causal_dynamic` 是新规范名，
`six_axis_dynamic` 仅作旧制品兼容别名。
静态基线还必须在开发期前冻结，禁止拿全样本事后最优静态参数做动态策略的对手。
新动态候选须额外按相同细粒度时间块统计绝对亏损、相对买入持有跑输、最差块和尾部块。
先用稳定性 Pareto 关系裁决，再检查预注册的长期可生存性下限；禁止用零仓位伪造稳定。
平台只输出 Pareto 占优或存在权衡，禁止用一个加权分数宣布谁更好。

## 因子入口

候选因子不能只因为与收益相关就进入动态参数研究。必须先从载体已使用的趋势输入中做
开发期拟合残差，再以预注册极端方向检查该残差是否在绝对大亏损或相对持有大幅跑输时
稳定出现；普通趋势重命名、事后挑方向和事后挑静态最优基线都会被拒绝。

## 弱期归因

同一尺度、仓位集、最小持有期、执行时钟和成本下，平台强制验证：
`R=M-(M-F)-(F-B)-(B-R)`。`B` 是当期事后最好的已注册固定参数，只用于把工具族内路由空间和
当前固定参数失配分开。没有事前注册的有界参数族，禁止声称“参数已最优”；`F` 和 `B`
都是事后诊断，不产生运行权。跨期收益下降被无阈值地分解为市场供给、工具架构、工具族内路由与当前参数失配四项。
静态/动态同期对照中市场供给天然抵消；但阶段总收益只能报告跨期差异，不能单独判定过拟合或稳定性。
这两项结论必须引用块级稳定性账本。

## 本次输出

`{', '.join(sorted(tables)) if tables else '只生成零市场数据合同与适配器盘点'}`
"""


def _build_manifest(
    staging: Path,
    *,
    scorecard_loaded: bool,
    event_evidence_loaded: bool,
    mfbr_loaded: bool,
    mfbr_reference_period: str | None,
) -> dict[str, object]:
    paths = sorted(path for path in staging.rglob("*") if path.is_file() and path.name != "manifest.json")
    return {
        "schema_id": "market_state_timing_evaluation_platform_manifest@4.0",
        "code_version": CODE_VERSION,
        "canonical_entrypoint": CANONICAL_ENTRYPOINT,
        "scorecard_loaded": scorecard_loaded,
        "event_evidence_loaded": event_evidence_loaded,
        "mfbr_loaded": mfbr_loaded,
        "mfbr_reference_period": mfbr_reference_period,
        "authority": {
            "evaluation_authority": True,
            "signal_authority": False,
            "routing_authority": False,
            "parameter_authority": False,
            "production_authority": False,
        },
        "artifacts": [
            {
                "path": str(path.relative_to(staging)),
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in paths
        ],
    }


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValidationError(f"JSON object required: {path}")
    return {str(key): value for key, value in payload.items()}


def _validate_detailed_event_boundary(
    opportunities: pd.DataFrame,
    claims: pd.DataFrame,
    *,
    sealed_cutoff: pd.Timestamp = pd.Timestamp("2021-01-01", tz="UTC"),
) -> None:
    """Reject event details from the aggregate-only post-2020 lockbox."""

    for frame, timestamp_column, label in (
        (opportunities, "start_timestamp", "opportunity"),
        (claims, "start_timestamp", "claim"),
    ):
        if "period_role" in frame and frame["period_role"].astype(str).eq("aggregate_blackbox").any():
            raise ValidationError(f"event-level {label} rows cannot use aggregate_blackbox role")
        timestamp = pd.to_datetime(frame[timestamp_column], errors="coerce", utc=True)
        if timestamp.isna().any() or timestamp.ge(sealed_cutoff).any():
            raise ValidationError(f"event-level {label} details crossed the sealed cutoff")


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    _ = path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "CANONICAL_ENTRYPOINT",
    "DEFAULT_OUTPUT_DIR",
    "FIELD_LABELS_ZH",
    "SCHEMA_ID",
    "TimingPotentialPolicy",
    "build_evaluation_surface_inventory",
    "classify_parameter_generalization",
    "compare_static_and_dynamic",
    "diagnose_period_weakness",
    "run_timing_evaluation_platform",
    "summarize_candidate_potential_capture",
    "summarize_market_potential",
    "summarize_nested_potential",
    "timing_evaluation_platform_contract",
    "validate_comparison_scorecard",
    "validate_nested_potential_scorecard",
    "validate_mfbr_ledger",
    "validate_period_governance",
    "validate_persisted_timing_evaluation_platform",
]
