"""Strategy-neutral evaluation kernel for routed timing systems.

The kernel deliberately does not know how a strategy names states, detects an
opportunity, or draws a domain chart.  Strategy adapters supply those facts;
this module owns the comparable counterfactual, normalization, drift-screening,
and acceptance rules.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import numpy as np
import pandas as pd

TimingAction = Literal["long", "flat", "cash", "short"]
TimingValueAction = Literal["long", "flat", "cash", "short", "routed_direction"]

ACTION_POSITION: dict[TimingAction, float] = {
    "long": 1.0,
    "flat": 0.0,
    "cash": 0.0,
    "short": -1.0,
}

VALUE_ACTIONS: frozenset[str] = frozenset({*ACTION_POSITION, "routed_direction"})

FIELD_LABELS_ZH: dict[str, str] = {
    "strategy_id": "策略标识",
    "level": "状态层级",
    "bucket": "状态桶",
    "period": "评价区间",
    "assigned_action": "当前分配动作",
    "counterfactual_action": "反事实对照动作",
    "bar_count": "责任K线数",
    "episode_count": "责任事件数",
    "assigned_action_net_log_value": "当前动作净对数价值",
    "assigned_action_relative_wealth_effect": "当前动作相对财富影响",
    "value_sign": "价值正负",
    "opportunities_per_year": "年均机会数",
    "opportunity_supply_per_year": "年均机会供给",
    "positive_net_value_rate": "正净价值机会占比",
    "opportunity_capture_rate": "机会能量捕获率",
    "mean_net_value_per_opportunity": "单次机会平均净价值",
    "episodes_per_year": "年均责任事件数",
    "mean_bars_per_episode": "单次责任事件平均K线数",
    "mean_value_per_episode": "单次责任事件平均净价值",
    "assigned_value_per_1000_bars": "每1000根责任K线净价值",
    "incremental_cost_per_episode": "单次责任事件增量成本",
    "requires_matched_attribution": "是否需要第二层匹配归因",
}


@dataclass(frozen=True, slots=True)
class TimingEvaluationProfile:
    """Frozen workflow metadata supplied by one timing-strategy adapter."""

    strategy_id: str
    development_period: str
    diagnostic_period: str
    bucket_audit_schema: str
    opportunity_attribution_schema: str
    matched_kernel_schema: str
    sealed_row_field: str = "sealed_rows_loaded"

    def __post_init__(self) -> None:
        values = (
            self.strategy_id,
            self.development_period,
            self.diagnostic_period,
            self.bucket_audit_schema,
            self.opportunity_attribution_schema,
            self.matched_kernel_schema,
            self.sealed_row_field,
        )
        if any(not value.strip() for value in values):
            raise ValueError("timing evaluation profile values must be non-empty")
        if self.development_period == self.diagnostic_period:
            raise ValueError("development and diagnostic periods must differ")


def elapsed_years(index: pd.DatetimeIndex) -> float:
    """Return the common elapsed-year denominator for normalized metrics."""

    if len(index) < 2:
        return 1.0 / 365.2425
    return max(
        (index[-1] - index[0]).total_seconds() / (365.2425 * 86_400.0),
        1.0 / 365.2425,
    )


def timing_evaluation_contract() -> dict[str, object]:
    """Return the project-level authority and adapter boundary."""

    return {
        "schema_id": "market_state_timing_evaluation@1.0",
        "authority": "evaluation_only_not_runtime_signal_parameter_or_production_authority",
        "supported_position_policies": ["long_flat", "short_flat", "long_short"],
        "required_after_every_optimization_round": True,
        "stage_order": [
            "fixed_surroundings_bucket_counterfactual",
            "opportunity_supply_and_unit_skill",
            "matched_root_cause_when_flagged",
            "authorized_post_2020_one_shot_aggregate_blackbox",
        ],
        "kernel_responsibilities": [
            "target_bucket_only_counterfactual",
            "assigned_action_positive_sign_convention",
            "per_year_per_opportunity_per_episode_per_bar_normalization",
            "cross_period_inconsistency_screening",
            "matched_attribution_coverage_gate",
            "optimization_lock_recommendation",
            "authorized_post_2020_aggregate_drift_screening",
        ],
        "adapter_responsibilities": [
            "strategy_bucket_partition",
            "assigned_and_counterfactual_actions",
            "account_ledger_with_real_costs",
            "opportunity_event_definition",
            "episode_lifecycle_definition",
            "causally_visible_matching_features",
            "domain_specific_graphical_attribution",
            "sealed_data_boundary",
            "bidirectional_side_responsibility_split_before_sealed_boundary",
            "calendar_year_attribution_before_sealed_boundary",
            "diagnostic_only_post_2020_authority",
        ],
        "single_universal_opportunity_definition_forbidden": True,
        "bucket_cagr_is_authoritative": False,
        "isolated_bucket_with_outside_flat_is_authoritative": False,
        "values_additive_across_counterfactual_buckets": False,
        "continuous_account_ledger_required_for_additive_contribution": True,
        "diagnostic_period_may_select_parameters": False,
        "post_2020_diagnostic_contract": {
            "aggregate_only_when_authorized": True,
            "one_shot_real_data_execution": True,
            "per_year_side_event_path_and_chart_views_forbidden": True,
            "opportunity_scarcity_must_be_separated_from_unit_skill_drift": True,
            "root_cause_attribution_must_use_pre_2021_rows": True,
            "canonical_and_local_seals_required": True,
            "authorized_post_2020_rows_may_select_parameters": False,
        },
        "field_labels_zh": dict(FIELD_LABELS_ZH),
    }


def assert_exhaustive_exclusive_partition(
    buckets: Mapping[str, pd.Series],
    *,
    expected_index: pd.Index,
) -> None:
    """Fail closed unless every row belongs to exactly one strategy bucket."""

    if not buckets:
        raise ValueError("bucket partition must not be empty")
    normalized: dict[str, pd.Series] = {}
    for name, mask in buckets.items():
        if not name:
            raise ValueError("bucket names must be non-empty")
        if not mask.index.equals(expected_index):
            raise ValueError(f"bucket {name!r} does not share the expected index")
        if mask.isna().any():
            raise ValueError(f"bucket {name!r} contains missing values")
        normalized[name] = mask.astype(bool)
    coverage = pd.DataFrame(normalized, index=expected_index).sum(axis=1)
    if not coverage.eq(1).all():
        raise ValueError("bucket partition must be exhaustive and exclusive")


def override_position_inside_bucket(
    current_position: pd.Series,
    bucket_mask: pd.Series,
    action: TimingAction,
    *,
    allowed_positions: Sequence[float] = (-1.0, 0.0, 1.0),
) -> pd.Series:
    """Replace one bucket action while preserving all surrounding routes."""

    if action not in ACTION_POSITION:
        raise ValueError(f"unsupported timing action: {action}")
    if not current_position.index.equals(bucket_mask.index):
        raise ValueError("current_position and bucket_mask must share an exact index")
    numeric = pd.to_numeric(current_position, errors="coerce").astype(float)
    allowed = tuple(float(value) for value in allowed_positions)
    if numeric.isna().any() or not numeric.isin(allowed).all():
        raise ValueError(f"current_position must contain only {allowed}")
    if bucket_mask.isna().any():
        raise ValueError("bucket_mask must not contain missing values")
    mask = bucket_mask.astype(bool)
    result = numeric.mask(mask, ACTION_POSITION[action])
    if not result.loc[~mask].equals(numeric.loc[~mask]):
        raise RuntimeError("bucket override changed an out-of-bucket position")
    return result.rename(f"{action}_inside_bucket_position")


def counterfactual_action_value_table(bucket_metrics: pd.DataFrame) -> pd.DataFrame:
    """Give every action pair one sign: positive means the assigned action helps."""

    required = {
        "level",
        "bucket",
        "period",
        "assigned_action",
        "counterfactual_action",
        "bar_count",
        "episode_count",
        "assigned_minus_counterfactual_net_log_return_delta",
    }
    missing = required.difference(bucket_metrics.columns)
    if missing:
        raise ValueError(f"bucket_metrics missing required columns: {sorted(missing)}")
    actions = set(bucket_metrics["assigned_action"].astype(str)) | set(bucket_metrics["counterfactual_action"].astype(str))
    if not actions.issubset(VALUE_ACTIONS):
        raise ValueError(f"unsupported timing value actions: {sorted(actions.difference(VALUE_ACTIONS))}")
    result = bucket_metrics.loc[:, sorted(required)].copy()
    value = pd.to_numeric(
        result["assigned_minus_counterfactual_net_log_return_delta"],
        errors="raise",
    ).astype(float)
    result["assigned_action_net_log_value"] = value
    result["assigned_action_relative_wealth_ratio"] = np.exp(value)
    result["assigned_action_relative_wealth_effect"] = np.expm1(value)
    result["value_sign"] = np.where(
        value.gt(0.0),
        "positive",
        np.where(value.lt(0.0), "negative", "zero"),
    )
    result["interpretation_zh"] = np.where(
        value.gt(0.0),
        "当前分配动作有价值",
        np.where(value.lt(0.0), "当前分配动作伤害账户", "与反事实动作持平"),
    )
    result["out_of_bucket_router_frozen"] = True
    result["values_additive_across_buckets"] = False
    return result


def summarize_timing_opportunity_events(
    events: pd.DataFrame,
    *,
    group_columns: Sequence[str] = ("period", "threshold"),
) -> pd.DataFrame:
    """Normalize an adapter-built opportunity ledger by time and event supply."""

    required = {
        *group_columns,
        "elapsed_years",
        "event_bar_count",
        "opportunity_size",
        "opportunity_supply",
        "positive_net_value",
        "captured_opportunity",
        "missed_favorable_move",
        "strategy_cost",
        "net_opportunity_value",
    }
    missing = required.difference(events.columns)
    if missing:
        raise ValueError(f"opportunity events missing required columns: {sorted(missing)}")
    rows: list[dict[str, object]] = []
    for keys, local in events.groupby(list(group_columns), sort=True):
        normalized_keys = keys if isinstance(keys, tuple) else (keys,)
        years = float(local["elapsed_years"].iloc[0])
        supply = float(local["opportunity_supply"].sum())
        captured = float(local["captured_opportunity"].sum())
        net_value = float(local["net_opportunity_value"].sum())
        row: dict[str, object] = dict(zip(group_columns, normalized_keys, strict=True))
        row.update(
            {
                "elapsed_years": years,
                "opportunity_count": len(local),
                "opportunities_per_year": len(local) / years,
                "mean_opportunity_size": float(local["opportunity_size"].mean()),
                "median_opportunity_size": float(local["opportunity_size"].median()),
                "opportunity_supply_total": supply,
                "opportunity_supply_per_year": supply / years,
                "positive_net_value_count": int(local["positive_net_value"].sum()),
                "positive_net_value_rate": float(local["positive_net_value"].mean()),
                "captured_opportunity_total": captured,
                "opportunity_capture_rate": (captured / supply if supply > 0.0 else 0.0),
                "missed_favorable_move_total": float(local["missed_favorable_move"].sum()),
                "strategy_cost_total": float(local["strategy_cost"].sum()),
                "net_opportunity_value_total": net_value,
                "net_opportunity_value_per_year": net_value / years,
                "mean_net_value_per_opportunity": float(local["net_opportunity_value"].mean()),
                "mean_event_bars": float(local["event_bar_count"].mean()),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_bucket_episodes(episodes: pd.DataFrame) -> pd.DataFrame:
    """Normalize assigned-action episode value by year, event, and bar."""

    required = {
        "period",
        "bucket",
        "assigned_action",
        "elapsed_years",
        "bar_count",
        "positive_value",
        "assigned_action_gross_log_value",
        "assigned_action_incremental_cost",
        "assigned_action_net_log_value",
    }
    missing = required.difference(episodes.columns)
    if missing:
        raise ValueError(f"bucket episodes missing required columns: {sorted(missing)}")
    rows: list[dict[str, object]] = []
    for (period, bucket), local in episodes.groupby(["period", "bucket"], sort=True):
        years = float(local["elapsed_years"].iloc[0])
        value = float(local["assigned_action_net_log_value"].sum())
        gross_value = float(local["assigned_action_gross_log_value"].sum())
        incremental_cost = float(local["assigned_action_incremental_cost"].sum())
        bars = int(local["bar_count"].sum())
        rows.append(
            {
                "period": period,
                "bucket": bucket,
                "assigned_action": str(local["assigned_action"].iloc[0]),
                "elapsed_years": years,
                "episode_count": len(local),
                "episodes_per_year": len(local) / years,
                "positive_episode_count": int(local["positive_value"].sum()),
                "positive_episode_rate": float(local["positive_value"].mean()),
                "total_bars": bars,
                "bars_per_year": bars / years,
                "mean_bars_per_episode": float(local["bar_count"].mean()),
                "median_bars_per_episode": float(local["bar_count"].median()),
                "assigned_gross_value_total": gross_value,
                "assigned_incremental_cost_total": incremental_cost,
                "assigned_value_total": value,
                "assigned_value_per_year": value / years,
                "mean_value_per_episode": float(local["assigned_action_net_log_value"].mean()),
                "median_value_per_episode": float(local["assigned_action_net_log_value"].median()),
                "assigned_value_per_bar": value / bars if bars else 0.0,
                "assigned_value_per_1000_bars": (1000.0 * value / bars if bars else 0.0),
                "incremental_cost_per_episode": incremental_cost / len(local),
                "incremental_cost_per_1000_bars": (1000.0 * incremental_cost / bars if bars else 0.0),
            }
        )
    return pd.DataFrame(rows)


def period_shift_table(
    summary: pd.DataFrame,
    *,
    entity: str,
    metrics: Sequence[str],
    development_period: str,
    diagnostic_period: str,
) -> pd.DataFrame:
    """Compare normalized metrics without confusing unequal period lengths."""

    development = summary.loc[summary["period"].eq(development_period)].set_index(entity)
    diagnostic = summary.loc[summary["period"].eq(diagnostic_period)].set_index(entity)
    rows: list[dict[str, object]] = []
    for key in development.index.intersection(diagnostic.index):
        row: dict[str, object] = {entity: key}
        for metric in metrics:
            dev_value = float(development.loc[key, metric])
            diag_value = float(diagnostic.loc[key, metric])
            row[f"development_{metric}"] = dev_value
            row[f"diagnostic_{metric}"] = diag_value
            row[f"diagnostic_minus_development_{metric}"] = diag_value - dev_value
            row[f"diagnostic_over_development_{metric}"] = diag_value / dev_value if dev_value != 0.0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def classify_bucket_period_stability(
    summary: pd.DataFrame,
    *,
    development_period: str,
    diagnostic_period: str,
) -> pd.DataFrame:
    """Screen sign instability and unit-skill deterioration across two periods."""

    required = {"period", "bucket", "assigned_value_total", "mean_value_per_episode"}
    missing = required.difference(summary.columns)
    if missing:
        raise ValueError(f"bucket summary missing required columns: {sorted(missing)}")
    development = summary.loc[summary["period"].eq(development_period)].set_index("bucket")
    diagnostic = summary.loc[summary["period"].eq(diagnostic_period)].set_index("bucket")
    rows: list[dict[str, object]] = []
    for bucket in development.index.intersection(diagnostic.index):
        dev_value = float(development.loc[bucket, "assigned_value_total"])
        diag_value = float(diagnostic.loc[bucket, "assigned_value_total"])
        dev_unit = float(development.loc[bucket, "mean_value_per_episode"])
        diag_unit = float(diagnostic.loc[bucket, "mean_value_per_episode"])
        if dev_value > 0.0 and diag_value <= 0.0:
            classification = "structural_instability_positive_to_nonpositive"
        elif dev_value < 0.0 and diag_value < 0.0:
            classification = "persistent_wrong_assignment"
        elif dev_value <= 0.0 < diag_value:
            classification = "diagnostic_improvement_negative_to_positive"
        else:
            classification = "cross_period_positive_assignment"
        needs_follow_up = classification in {
            "structural_instability_positive_to_nonpositive",
            "persistent_wrong_assignment",
        }
        rows.append(
            {
                "bucket": bucket,
                "development_assigned_value_total": dev_value,
                "diagnostic_assigned_value_total": diag_value,
                "development_mean_value_per_episode": dev_unit,
                "diagnostic_mean_value_per_episode": diag_unit,
                "diagnostic_minus_development_mean_value_per_episode": diag_unit - dev_unit,
                "classification": classification,
                "requires_follow_up": needs_follow_up,
                "requires_matched_attribution": bool(needs_follow_up or diag_unit < dev_unit),
            }
        )
    return pd.DataFrame(rows)


def classify_multi_period_drift(
    summary: pd.DataFrame,
    *,
    reference_period: str,
    evaluation_periods: Sequence[str],
    value_metric: str = "assigned_value_per_year",
    unit_metric: str = "mean_value_per_episode",
    supply_metric: str = "opportunity_supply_per_year",
    scarcity_ratio: float = 0.75,
    severe_unit_ratio: float = 0.50,
) -> pd.DataFrame:
    """Separate opportunity scarcity from unit-skill drift after development."""

    if not 0.0 < severe_unit_ratio <= scarcity_ratio < 1.0:
        raise ValueError("drift ratios must satisfy 0 < severe_unit <= scarcity < 1")
    required = {
        "period",
        "bucket",
        value_metric,
        unit_metric,
        supply_metric,
    }
    missing = required.difference(summary.columns)
    if missing:
        raise ValueError(f"drift summary missing required columns: {sorted(missing)}")
    reference = summary.loc[summary["period"].eq(reference_period)].set_index("bucket")
    rows: list[dict[str, object]] = []
    for period in evaluation_periods:
        evaluated = summary.loc[summary["period"].eq(period)].set_index("bucket")
        for bucket in reference.index.intersection(evaluated.index):
            ref_value = float(reference.loc[bucket, value_metric])
            value = float(evaluated.loc[bucket, value_metric])
            ref_unit = float(reference.loc[bucket, unit_metric])
            unit = float(evaluated.loc[bucket, unit_metric])
            ref_supply = float(reference.loc[bucket, supply_metric])
            supply = float(evaluated.loc[bucket, supply_metric])
            unit_ratio = unit / ref_unit if ref_unit > 0.0 else np.nan
            supply_ratio = supply / ref_supply if ref_supply > 0.0 else np.nan
            scarce = bool(np.isfinite(supply_ratio) and supply_ratio < scarcity_ratio)
            severe_unit_drift = bool(np.isfinite(unit_ratio) and unit_ratio < severe_unit_ratio)
            if ref_value <= 0.0:
                classification = "reference_assignment_not_positive"
            elif (value <= 0.0 or unit <= 0.0) and scarce:
                classification = "mixed_opportunity_scarcity_and_capability_sign_drift"
            elif value <= 0.0 or unit <= 0.0:
                classification = "structural_capability_sign_drift"
            elif scarce and not severe_unit_drift:
                classification = "opportunity_scarcity_with_unit_skill_retained"
            elif severe_unit_drift and not scarce:
                classification = "possible_capability_drift_with_supply_present"
            elif severe_unit_drift and scarce:
                classification = "mixed_opportunity_scarcity_and_capability_drift"
            else:
                classification = "positive_generalization_no_material_drift"
            rows.append(
                {
                    "bucket": bucket,
                    "reference_period": reference_period,
                    "evaluation_period": period,
                    "reference_value_per_year": ref_value,
                    "evaluation_value_per_year": value,
                    "reference_unit_value": ref_unit,
                    "evaluation_unit_value": unit,
                    "unit_value_ratio_to_reference": unit_ratio,
                    "reference_opportunity_supply_per_year": ref_supply,
                    "evaluation_opportunity_supply_per_year": supply,
                    "opportunity_supply_ratio_to_reference": supply_ratio,
                    "classification": classification,
                    "capability_drift_flag": classification
                    in {
                        "structural_capability_sign_drift",
                        "mixed_opportunity_scarcity_and_capability_sign_drift",
                        "possible_capability_drift_with_supply_present",
                        "mixed_opportunity_scarcity_and_capability_drift",
                    },
                    "opportunity_scarcity_flag": classification
                    in {
                        "opportunity_scarcity_with_unit_skill_retained",
                        "mixed_opportunity_scarcity_and_capability_sign_drift",
                        "mixed_opportunity_scarcity_and_capability_drift",
                    },
                }
            )
    return pd.DataFrame(rows)


def classify_overfit_evidence(
    drift: pd.DataFrame,
    *,
    repeat_audit_period: str,
    post_2020_period: str,
) -> pd.DataFrame:
    """Require repeated failure before labelling an overfit suspicion."""

    required = {
        "bucket",
        "evaluation_period",
        "classification",
        "evaluation_value_per_year",
    }
    missing = required.difference(drift.columns)
    if missing:
        raise ValueError(f"drift table missing required columns: {sorted(missing)}")
    rows: list[dict[str, object]] = []
    for bucket, local in drift.groupby("bucket", sort=True):
        periods = local.set_index("evaluation_period")
        if repeat_audit_period not in periods.index or post_2020_period not in periods.index:
            continue
        repeat_value = float(periods.loc[repeat_audit_period, "evaluation_value_per_year"])
        external_value = float(periods.loc[post_2020_period, "evaluation_value_per_year"])
        reference_value = float(periods.loc[repeat_audit_period, "reference_value_per_year"])
        repeat_class = str(periods.loc[repeat_audit_period, "classification"])
        external_class = str(periods.loc[post_2020_period, "classification"])
        repeated_failure = repeat_value <= 0.0 and external_value <= 0.0
        repeated_failure_confounded_by_scarcity = bool(
            repeated_failure
            and periods.loc[
                [repeat_audit_period, post_2020_period],
                "opportunity_scarcity_flag",
            ]
            .astype(bool)
            .any()
        )
        any_capability_drift = any("capability" in value or "sign_drift" in value for value in (repeat_class, external_class))
        if reference_value <= 0.0:
            verdict = "reference_assignment_not_positive_not_an_overfit_test"
        elif repeated_failure_confounded_by_scarcity:
            verdict = "repeated_failure_confounded_by_opportunity_scarcity"
        elif repeated_failure:
            verdict = "strong_overfit_suspicion_repeated_post_development_failure"
        elif repeat_value <= 0.0 or external_value <= 0.0:
            verdict = "cross_period_instability_not_enough_to_call_overfit"
        elif any_capability_drift:
            verdict = "possible_drift_but_no_repeated_sign_failure"
        else:
            verdict = "no_overfit_signal_across_both_post_development_periods"
        rows.append(
            {
                "bucket": bucket,
                "repeat_audit_period": repeat_audit_period,
                "post_2020_period": post_2020_period,
                "repeat_audit_classification": repeat_class,
                "post_2020_classification": external_class,
                "repeat_audit_value_per_year": repeat_value,
                "post_2020_value_per_year": external_value,
                "repeated_post_development_failure": repeated_failure,
                "repeated_failure_confounded_by_opportunity_scarcity": (repeated_failure_confounded_by_scarcity),
                "overfit_verdict": verdict,
            }
        )
    return pd.DataFrame(rows)


def classify_calendar_year_weakness(
    yearly: pd.DataFrame,
    *,
    reference_year_end: int,
    diagnosis_year_start: int,
    value_metric: str = "assigned_value_total",
    unit_metric: str = "mean_value_per_episode",
    supply_metric: str = "opportunity_supply_per_year",
    scarcity_ratio: float = 0.50,
) -> pd.DataFrame:
    """Explain pre-seal weak years against development-era opportunity supply.

    Strategy adapters must not call this helper on a sealed aggregate-only black-box
    interval. Annualization prevents a partial pre-seal calendar year from being
    labelled scarce merely because it contains fewer months.
    """

    required = {"bucket", "year", value_metric, unit_metric, supply_metric}
    missing = required.difference(yearly.columns)
    if missing:
        raise ValueError(f"yearly summary missing required columns: {sorted(missing)}")
    reference = yearly.loc[yearly["year"].le(reference_year_end)]
    medians = reference.groupby("bucket")[[unit_metric, supply_metric]].median()
    rows: list[dict[str, object]] = []
    for row in yearly.loc[yearly["year"].ge(diagnosis_year_start)].itertuples(index=False):
        bucket = str(row.bucket)
        if bucket not in medians.index:
            continue
        value = float(getattr(row, value_metric))
        unit = float(getattr(row, unit_metric))
        supply = float(getattr(row, supply_metric))
        reference_supply = float(medians.loc[bucket, supply_metric])
        reference_unit = float(medians.loc[bucket, unit_metric])
        supply_ratio = supply / reference_supply if reference_supply > 0.0 else np.nan
        scarce = bool(np.isfinite(supply_ratio) and supply_ratio < scarcity_ratio)
        if value > 0.0:
            explanation = "positive_year"
        elif scarce and supply <= 0.0:
            explanation = "weak_year_likely_opportunity_scarcity"
        elif scarce and unit <= 0.0:
            explanation = "weak_year_mixed_scarcity_and_capability_failure"
        elif scarce:
            explanation = "weak_year_likely_opportunity_scarcity"
        elif unit <= 0.0:
            explanation = "weak_year_capability_failure_with_opportunity_present"
        else:
            explanation = "weak_year_mixed_or_cost_boundary_effect"
        rows.append(
            {
                "bucket": bucket,
                "year": int(row.year),
                "assigned_value_total": value,
                "mean_value_per_episode": unit,
                "opportunity_supply_total": float(getattr(row, "opportunity_supply_total", supply)),
                "opportunity_supply_per_year": float(getattr(row, "opportunity_supply_per_year", supply)),
                "assessed_opportunity_supply_metric": supply_metric,
                "development_median_unit_value": reference_unit,
                "development_median_annualized_opportunity_supply": reference_supply,
                "opportunity_supply_ratio_to_development_median": supply_ratio,
                "partial_calendar_year": bool(getattr(row, "partial_calendar_year", False)),
                "year_explanation": explanation,
            }
        )
    return pd.DataFrame(rows)


def build_timing_acceptance_manifest(
    *,
    profile: TimingEvaluationProfile,
    bucket_result: Mapping[str, object],
    opportunity_result: Mapping[str, object],
    matched_results: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Combine both evaluation layers without knowing strategy event semantics."""

    if bucket_result.get("schema_id") != profile.bucket_audit_schema:
        raise ValueError("unexpected state bucket audit schema")
    if opportunity_result.get("schema_id") != profile.opportunity_attribution_schema:
        raise ValueError("unexpected opportunity attribution schema")
    if opportunity_result.get(profile.sealed_row_field) != 0:
        raise ValueError("sealed rows were loaded")
    flags = opportunity_result.get("bucket_diagnostic_flags")
    if not isinstance(flags, list):
        raise TypeError("bucket_diagnostic_flags must be a list")
    follow_up = [row for row in flags if isinstance(row, dict) and bool(row.get("requires_follow_up"))]
    targets = {str(row["bucket"]) for row in flags if isinstance(row, dict) and bool(row.get("requires_matched_attribution"))}
    registered: list[dict[str, object]] = []
    for bucket, result in matched_results.items():
        kernel = result.get("math_kernel_contract")
        if not isinstance(kernel, Mapping) or kernel.get("schema_id") != profile.matched_kernel_schema:
            raise ValueError(f"missing matched attribution kernel contract for {bucket}")
        adapter_id = result.get("adapter_id")
        if not isinstance(adapter_id, str) or not adapter_id:
            raise ValueError(f"missing matched attribution adapter id for {bucket}")
        if result.get(profile.sealed_row_field) != 0:
            raise ValueError("matched attribution loaded sealed rows")
        if result.get("runtime_or_parameter_authority") is not False:
            raise ValueError("matched attribution gained forbidden authority")
        result_schema = result.get("schema_id")
        if not isinstance(result_schema, str) or not result_schema:
            raise ValueError(f"missing matched attribution schema for {bucket}")
        registered.append(
            {
                "bucket": bucket,
                "adapter_id": adapter_id,
                "verdict": result.get("verdict"),
                "schema_id": result_schema,
            }
        )
    covered = {str(row["bucket"]) for row in registered}
    uncovered = sorted(targets.difference(covered))
    attribution_follow_up = [row for row in registered if row["verdict"] != "opportunity_and_lifecycle_mix_dominant"]
    lock_blocked = bool(follow_up or uncovered or attribution_follow_up)
    return {
        "schema_id": "market_state_timing_evaluation_acceptance@1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "strategy_id": profile.strategy_id,
        "workflow_completed": True,
        "required_after_every_optimization_round": True,
        "infrastructure_contract": timing_evaluation_contract()["schema_id"],
        "evaluation_periods": {
            "development": profile.development_period,
            "diagnostic": profile.diagnostic_period,
        },
        "evaluations": {
            "fixed_surroundings_bucket_value": profile.bucket_audit_schema,
            "opportunity_supply_and_unit_skill": profile.opportunity_attribution_schema,
            "matched_root_cause_adapters": registered,
        },
        "follow_up_buckets": follow_up,
        "matched_attribution_targets": sorted(targets),
        "registered_matched_attributions": registered,
        "uncovered_matched_attribution_targets": uncovered,
        "matched_attribution_coverage_complete": not uncovered,
        "matched_attribution_follow_up": attribution_follow_up,
        "optimization_lock_recommendation": ("do_not_lock_follow_up_required" if lock_blocked else "eligible_for_lock_review"),
        "overfit_interpretation": (
            "separate_opportunity_supply_from_normalized_unit_skill; sign_instability_is_stronger_evidence_than_raw_cumulative_return"
        ),
        "runtime_or_parameter_authority": False,
        profile.sealed_row_field: 0,
        "field_labels_zh": dict(FIELD_LABELS_ZH),
    }


__all__ = [
    "ACTION_POSITION",
    "FIELD_LABELS_ZH",
    "TimingAction",
    "TimingValueAction",
    "TimingEvaluationProfile",
    "VALUE_ACTIONS",
    "assert_exhaustive_exclusive_partition",
    "build_timing_acceptance_manifest",
    "classify_bucket_period_stability",
    "classify_calendar_year_weakness",
    "classify_multi_period_drift",
    "classify_overfit_evidence",
    "counterfactual_action_value_table",
    "elapsed_years",
    "override_position_inside_bucket",
    "period_shift_table",
    "summarize_bucket_episodes",
    "summarize_timing_opportunity_events",
    "timing_evaluation_contract",
]
