# pyright: reportAny=false, reportArgumentType=false, reportAssignmentType=false
# pyright: reportAttributeAccessIssue=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportOperatorIssue=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Legacy backend for Layer 3 strategy/tool conditional-effect evidence.

The current public authority is
``factor_lab.strategy.research.timing.conditional_effect_research``.  This
historical path no longer grants Layer 2 measurement identity.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import cast

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.tool_benchmark_adapters import run_tool_benchmark
from factor_lab.market_state.tool_registry import (
    REQUIRED_ACTION_ROLES,
    REQUIRED_EFFECT_METRICS,
    ToolBenchmarkSpec,
)

TOOL_AFFINITY_EVIDENCE_SCHEMA_ID = "tool_state_affinity_evidence@1.2"
TOOL_AFFINITY_FOLD_EVIDENCE_SCHEMA_ID = "tool_state_affinity_fold_evidence@1.2"
TOOL_AFFINITY_POLICY_VERSION = "qualitative_multi_period_tool_affinity_v1_2"
DISCOVERY_START = pd.Timestamp("2009-01-01")
DISCOVERY_END = pd.Timestamp("2014-12-31 23:59:59")
AUDIT_START = pd.Timestamp("2015-01-01")
AUDIT_END = pd.Timestamp("2020-12-31 23:59:59")
BLACKBOX_START = pd.Timestamp("2021-01-01")


@dataclass(frozen=True, slots=True)
class ValidationFold:
    fold_id: str
    start: pd.Timestamp
    end: pd.Timestamp


VALIDATION_FOLDS = (
    ValidationFold(
        "validation_1",
        pd.Timestamp("2015-01-01"),
        pd.Timestamp("2016-12-31 23:59:59"),
    ),
    ValidationFold(
        "validation_2",
        pd.Timestamp("2017-01-01"),
        pd.Timestamp("2018-12-31 23:59:59"),
    ),
    ValidationFold(
        "validation_3",
        pd.Timestamp("2019-01-01"),
        pd.Timestamp("2020-12-31 23:59:59"),
    ),
)

TOOL_EVIDENCE_COLUMNS = (
    "evidence_schema_id",
    "evidence_id",
    "tool_id",
    "method_family_id",
    "benchmark_id",
    "action_role",
    "carrier_frequency",
    "target_horizon",
    "attribute_id",
    "attribute_family",
    "measurement_scale_id",
    "attribute_state_semantics",
    "effect_metric_id",
    "effect_unit",
    "favorable_direction",
    "comparator_method_id",
    "association_shape",
    "direction_semantics",
    "conclusion",
    "mechanism_status",
    "mechanism",
    "evidence_level",
    "discovery_start",
    "discovery_end",
    "audit_start",
    "audit_end",
    "overlap_status",
    "discovery_sample_count",
    "audit_sample_count",
    "discovery_low_count",
    "discovery_normal_count",
    "discovery_high_count",
    "audit_low_count",
    "audit_normal_count",
    "audit_high_count",
    "discovery_low_metric_value",
    "discovery_normal_metric_value",
    "discovery_high_metric_value",
    "audit_low_metric_value",
    "audit_normal_metric_value",
    "audit_high_metric_value",
    "discovery_effect_value",
    "audit_effect_value",
    "discovery_standardized_effect",
    "audit_standardized_effect",
    "discovery_block_sign_consistency",
    "audit_block_sign_consistency",
    "validation_fold_count",
    "validation_fold_pass_count",
    "validation_all_folds_pass",
    "validation_weakest_standardized_effect",
    "validation_weakest_block_sign_consistency",
    "validation_min_bucket_sample_count",
    "tests_executed",
    "insufficient_reason",
    "limitations",
    "source_evidence_digest",
    "rejected_formula_not_rejected_factor",
    "production_authority",
)

TOOL_FOLD_EVIDENCE_COLUMNS = (
    "fold_evidence_schema_id",
    "fold_evidence_id",
    "evidence_id",
    "tool_id",
    "benchmark_id",
    "action_role",
    "carrier_frequency",
    "effect_metric_id",
    "attribute_id",
    "attribute_family",
    "measurement_scale_id",
    "validation_fold_id",
    "validation_start",
    "validation_end",
    "selected_candidate",
    "association_shape",
    "sample_count",
    "low_count",
    "normal_count",
    "high_count",
    "low_metric_value",
    "normal_metric_value",
    "high_metric_value",
    "effect_value",
    "standardized_effect",
    "block_sign_consistency",
    "sign_matches_discovery",
    "shape_valid",
    "adequate_counts",
    "passed",
    "failure_reason",
    "source_evidence_digest",
    "production_authority",
)


@dataclass(frozen=True, slots=True)
class ToolAffinityPolicy:
    """Frozen qualitative-first thresholds; validation never tunes them."""

    version: str = TOOL_AFFINITY_POLICY_VERSION
    minimum_standardized_effect: float = 0.03
    minimum_discovery_block_consistency: float = 0.60
    minimum_validation_block_consistency: float = 0.50
    minimum_daily_bucket_discovery: int = 50
    minimum_daily_bucket_audit: int = 20
    minimum_hourly_bucket_discovery: int = 200
    minimum_hourly_bucket_audit: int = 80
    minimum_daily_trade_bucket_discovery: int = 8
    minimum_daily_trade_bucket_audit: int = 4
    minimum_hourly_trade_bucket_discovery: int = 24
    minimum_hourly_trade_bucket_audit: int = 10


@dataclass(frozen=True, slots=True)
class _PreparedPeriod:
    state_buckets: dict[str, pd.DataFrame]
    annual_state_buckets: tuple[dict[str, pd.DataFrame], ...]


def build_tool_state_affinity_evidence(
    *,
    bars_by_frequency: dict[str, pd.DataFrame],
    online_states: pd.DataFrame,
    benchmarks: tuple[ToolBenchmarkSpec, ...],
    policy: ToolAffinityPolicy | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    """Build one row per tool, role, metric, frequency, attribute and scale."""

    cfg = policy or ToolAffinityPolicy()
    _assert_research_ranges()
    required_frequencies = {
        frequency
        for benchmark in benchmarks
        for frequency in benchmark.parameters_by_frequency
    }
    if set(bars_by_frequency) != required_frequencies:
        raise ValidationError(
            "tool dictionary bars must exactly match benchmark carrier frequencies"
        )
    states = _validated_states(online_states)
    panels: dict[str, pd.DataFrame] = {}
    rows: list[dict[str, object]] = []
    fold_rows: list[dict[str, object]] = []
    panel_columns = [
        "decision_time",
        "target_position",
        "turnover",
        "long_capture_value",
        "cash_avoidance_value",
        "long_trade_outcome",
        "cash_episode_outcome",
    ]
    research_bars = {
        frequency: _research_bars(bars_by_frequency[frequency])
        for frequency in sorted(required_frequencies)
    }
    state_slices: dict[str, pd.DataFrame] = {}
    for frequency in sorted(required_frequencies):
        state_slice = states.loc[states["bar_frequency"].eq(frequency)].copy()
        if state_slice.empty:
            raise ValidationError(f"online states missing frequency: {frequency}")
        state_slice["decision_time"] = _naive_datetime(
            state_slice["observation_time"]
        )
        state_slices[frequency] = state_slice
    for benchmark in benchmarks:
        for frequency in benchmark.parameters_by_frequency:
            panel = run_tool_benchmark(
                research_bars[frequency],
                benchmark,
                frequency=frequency,
            )
            panel_key = f"{benchmark.tool_id}:{frequency}"
            panels[panel_key] = panel
            merged = state_slices[frequency].merge(
                panel.loc[:, panel_columns],
                on="decision_time",
                how="inner",
                validate="many_to_one",
            )
            if merged.empty:
                raise ValidationError(f"tool/state alignment is empty: {panel_key}")
            conditions = [
                merged["decision_time"].between(
                    DISCOVERY_START, DISCOVERY_END, inclusive="both"
                )
            ]
            choices = ["discovery"]
            for fold in VALIDATION_FOLDS:
                conditions.append(
                    merged["decision_time"].between(
                        fold.start, fold.end, inclusive="both"
                    )
                )
                choices.append(fold.fold_id)
            merged["_research_period"] = np.select(
                conditions, choices, default="excluded"
            )
            merged["_decision_year"] = merged["decision_time"].dt.year.astype(
                "int16"
            )
            grouped = merged.groupby(
                ["physical_attribute_id", "attribute_family", "measurement_scale_id"],
                sort=True,
                observed=True,
            )
            for _, group in grouped:
                discovery = group.loc[
                    group["_research_period"].eq("discovery")
                ]
                validations = {
                    fold.fold_id: group.loc[
                        group["_research_period"].eq(fold.fold_id)
                    ]
                    for fold in VALIDATION_FOLDS
                }
                audit = group.loc[
                    group["_research_period"].isin(
                        tuple(fold.fold_id for fold in VALIDATION_FOLDS)
                    )
                ]
                if (
                    discovery.empty
                    or audit.empty
                    or any(frame.empty for frame in validations.values())
                ):
                    raise ValidationError(
                        "every tool relation must execute discovery and all validation folds"
                    )
                discovery_prepared = _prepare_period(discovery)
                audit_prepared = _prepare_period(audit)
                validation_prepared = {
                    fold_id: _prepare_period(frame)
                    for fold_id, frame in validations.items()
                }
                for action_role in REQUIRED_ACTION_ROLES:
                    for metric_id in REQUIRED_EFFECT_METRICS:
                        relation, relation_folds = _relation_row(
                            group,
                            discovery=discovery_prepared,
                            audit=audit_prepared,
                            validations=validation_prepared,
                            benchmark=benchmark,
                            frequency=frequency,
                            action_role=action_role,
                            metric_id=metric_id,
                            policy=cfg,
                        )
                        rows.append(relation)
                        fold_rows.extend(relation_folds)
    evidence = pd.DataFrame(rows, columns=TOOL_EVIDENCE_COLUMNS)
    fold_evidence = pd.DataFrame(fold_rows, columns=TOOL_FOLD_EVIDENCE_COLUMNS)
    _validate_tool_evidence(
        evidence,
        fold_evidence,
        expected_tool_ids={item.tool_id for item in benchmarks},
    )
    order = [
        "tool_id",
        "action_role",
        "effect_metric_id",
        "carrier_frequency",
        "attribute_family",
        "attribute_id",
        "measurement_scale_id",
    ]
    return (
        evidence.sort_values(order).reset_index(drop=True),
        fold_evidence.sort_values(
            [*order, "validation_fold_id"]
        ).reset_index(drop=True),
        panels,
    )


def _assert_research_ranges() -> None:
    previous_end = DISCOVERY_END
    for fold in VALIDATION_FOLDS:
        if previous_end >= fold.start:
            raise ValidationError("tool discovery/validation ranges overlap")
        if fold.start > fold.end:
            raise ValidationError("tool validation range is inverted")
        previous_end = fold.end
    if previous_end != AUDIT_END:
        raise ValidationError("validation folds must cover the frozen audit horizon")
    if AUDIT_END >= BLACKBOX_START:
        raise ValidationError("2021-2026 is sealed from tool affinity research")


def _validated_states(states: pd.DataFrame) -> pd.DataFrame:
    required = {
        "bar_frequency",
        "observation_time",
        "physical_attribute_id",
        "attribute_family",
        "measurement_scale_id",
        "state_bucket",
        "state_valid",
    }
    missing = sorted(required - set(states.columns))
    if missing:
        raise ValidationError(f"online states missing columns: {missing}")
    out = states.loc[:, sorted(required)].copy()
    out["observation_time"] = pd.to_datetime(out["observation_time"], errors="coerce")
    out = out.loc[
        out["state_valid"].eq(True)
        & out["state_bucket"].isin(("low", "normal", "high"))
    ].copy()
    times = _naive_datetime(out["observation_time"])
    out = out.loc[times.between(DISCOVERY_START, AUDIT_END, inclusive="both")].copy()
    if out.empty:
        raise ValidationError("no valid 2009-2020 online states")
    if _naive_datetime(out["observation_time"]).max() >= BLACKBOX_START:
        raise ValidationError("blackbox state entered tool research")
    return out


def _research_bars(bars: pd.DataFrame) -> pd.DataFrame:
    if "timestamp" not in bars:
        raise ValidationError("tool benchmark bars require timestamp")
    times = _naive_datetime(bars["timestamp"])
    mask = times <= AUDIT_END
    out = bars.loc[mask].copy()
    out["timestamp"] = times.loc[mask].to_numpy()
    if out.empty or out["timestamp"].max() >= BLACKBOX_START:
        raise ValidationError("blackbox bar entered tool research")
    return out


def _relation_row(
    group: pd.DataFrame,
    *,
    discovery: _PreparedPeriod,
    audit: _PreparedPeriod,
    validations: dict[str, _PreparedPeriod],
    benchmark: ToolBenchmarkSpec,
    frequency: str,
    action_role: str,
    metric_id: str,
    policy: ToolAffinityPolicy,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    discovery_stats = _shape_statistics(
        discovery, action_role=action_role, metric_id=metric_id
    )
    validation_stats = {
        fold_id: _shape_statistics(
            period, action_role=action_role, metric_id=metric_id
        )
        for fold_id, period in validations.items()
    }
    # The old audit columns remain as a compatibility summary over all three
    # validation folds.  They are descriptive only; they are not the pass gate.
    audit_stats = _shape_statistics(
        audit, action_role=action_role, metric_id=metric_id
    )
    shape, candidate = _select_discovery_shape(discovery_stats)
    minimum_discovery, minimum_validation = _minimum_bucket_counts(
        frequency=frequency, metric_id=metric_id, policy=policy
    )
    discovery_counts = cast(dict[str, int], discovery_stats["counts"])
    audit_counts = cast(dict[str, int], audit_stats["counts"])
    discovery_candidate = cast(dict[str, object], discovery_stats[candidate])
    audit_candidate = cast(dict[str, object], audit_stats[candidate])
    discovery_effect = float(discovery_candidate["effect"])
    audit_effect = float(audit_candidate["effect"])
    discovery_standardized = float(discovery_candidate["standardized"])
    audit_standardized = float(audit_candidate["standardized"])
    discovery_consistency = float(discovery_candidate["block_consistency"])
    audit_consistency = float(audit_candidate["block_consistency"])
    discovery_finite = all(
        math.isfinite(item)
        for item in (discovery_effect, discovery_standardized)
    )
    discovery_signal = (
        discovery_finite
        and min(discovery_counts.values()) >= minimum_discovery
        and abs(discovery_standardized) >= policy.minimum_standardized_effect
        and discovery_consistency >= policy.minimum_discovery_block_consistency
        and bool(discovery_candidate["shape_valid"])
    )
    evidence_key = "|".join(
        (
            benchmark.tool_id,
            action_role,
            metric_id,
            frequency,
            str(group["physical_attribute_id"].iloc[0]),
            str(group["measurement_scale_id"].iloc[0]),
        )
    )
    evidence_id = "tool-aff-" + hashlib.sha256(evidence_key.encode()).hexdigest()[:20]
    fold_rows: list[dict[str, object]] = []
    fold_passes: list[bool] = []
    fold_standardized: list[float] = []
    fold_consistencies: list[float] = []
    fold_min_bucket_counts: list[int] = []
    for fold in VALIDATION_FOLDS:
        stats = validation_stats[fold.fold_id]
        candidate_stats = cast(dict[str, object], stats[candidate])
        counts = cast(dict[str, int], stats["counts"])
        values = cast(dict[str, float], stats["values"])
        effect = float(candidate_stats["effect"])
        standardized = float(candidate_stats["standardized"])
        consistency = float(candidate_stats["block_consistency"])
        finite = math.isfinite(effect) and math.isfinite(standardized)
        sign_matches = (
            finite
            and discovery_finite
            and np.sign(discovery_effect) != 0.0
            and np.sign(discovery_effect) == np.sign(effect)
        )
        shape_valid = bool(candidate_stats["shape_valid"])
        adequate = min(counts.values()) >= minimum_validation
        passed = bool(
            discovery_signal
            and adequate
            and sign_matches
            and abs(standardized) >= policy.minimum_standardized_effect
            and consistency >= policy.minimum_validation_block_consistency
            and shape_valid
        )
        fold_passes.append(passed)
        fold_standardized.append(abs(standardized) if finite else math.nan)
        fold_consistencies.append(consistency)
        fold_min_bucket_counts.append(min(counts.values()))
        fold_payload = {
            "policy_version": policy.version,
            "evidence_id": evidence_id,
            "fold_id": fold.fold_id,
            "selected_candidate": candidate,
            "statistics": stats,
            "passed": passed,
        }
        fold_digest = canonical_digest(fold_payload)
        fold_rows.append(
            {
                "fold_evidence_schema_id": TOOL_AFFINITY_FOLD_EVIDENCE_SCHEMA_ID,
                "fold_evidence_id": f"{evidence_id}-{fold.fold_id}",
                "evidence_id": evidence_id,
                "tool_id": benchmark.tool_id,
                "benchmark_id": benchmark.benchmark_id,
                "action_role": action_role,
                "carrier_frequency": frequency,
                "effect_metric_id": metric_id,
                "attribute_id": str(group["physical_attribute_id"].iloc[0]),
                "attribute_family": str(group["attribute_family"].iloc[0]),
                "measurement_scale_id": str(
                    group["measurement_scale_id"].iloc[0]
                ),
                "validation_fold_id": fold.fold_id,
                "validation_start": fold.start,
                "validation_end": fold.end.normalize(),
                "selected_candidate": candidate,
                "association_shape": shape,
                "sample_count": sum(counts.values()),
                "low_count": counts["low"],
                "normal_count": counts["normal"],
                "high_count": counts["high"],
                "low_metric_value": values["low"],
                "normal_metric_value": values["normal"],
                "high_metric_value": values["high"],
                "effect_value": effect,
                "standardized_effect": standardized,
                "block_sign_consistency": consistency,
                "sign_matches_discovery": sign_matches,
                "shape_valid": shape_valid,
                "adequate_counts": adequate,
                "passed": passed,
                "failure_reason": _fold_failure_reason(
                    discovery_signal=discovery_signal,
                    adequate_counts=adequate,
                    finite=finite,
                    sign_matches=sign_matches,
                    strong_enough=(
                        finite
                        and abs(standardized)
                        >= policy.minimum_standardized_effect
                    ),
                    consistent=(
                        consistency
                        >= policy.minimum_validation_block_consistency
                    ),
                    shape_valid=shape_valid,
                ),
                "source_evidence_digest": fold_digest,
                "production_authority": False,
            }
        )
    all_folds_pass = bool(fold_passes) and all(fold_passes)
    supported = discovery_signal and all_folds_pass
    if supported:
        association_shape = shape
        conclusion = "supported"
        evidence_level = "frozen_discovery_plus_three_disjoint_validations"
        insufficient_reason = ""
        mechanism_status = "plausible_and_multi_period_supported"
    else:
        association_shape = "unknown" if discovery_signal else "none"
        conclusion = "rejected" if discovery_signal else "unknown"
        evidence_level = "multi_period_tested_insufficient"
        mechanism_status = "hypothesis_not_established"
        insufficient_reason = _insufficient_reason_v12(
            discovery_signal=discovery_signal,
            fold_passes=fold_passes,
        )
    attribute_id = str(group["physical_attribute_id"].iloc[0])
    attribute_family = str(group["attribute_family"].iloc[0])
    scale = str(group["measurement_scale_id"].iloc[0])
    effect_unit, favorable_direction = _metric_semantics(metric_id)
    comparator = (
        "cash_zero_return"
        if action_role == "long_capture"
        else "fully_invested_market"
    )
    direction_semantics = _direction_semantics(
        association_shape=association_shape,
        effect=discovery_effect,
        metric_id=metric_id,
        favorable_direction=favorable_direction,
    )
    mechanism = _mechanism_text(
        tool_id=benchmark.tool_id,
        attribute_family=attribute_family,
        action_role=action_role,
        supported=supported,
    )
    tests = (
        "metric-specific low/normal/high aggregation; annual-block sign consistency; "
        "2009-2014 discovery frozen before three disjoint validations "
        "(2015-2016, 2017-2018, 2019-2020); every validation must independently "
        "preserve direction, minimum strength and shape; 2021+ rows excluded before "
        "benchmark execution"
    )
    source_payload = {
        "policy_version": policy.version,
        "benchmark_id": benchmark.benchmark_id,
        "tool_id": benchmark.tool_id,
        "frequency": frequency,
        "action_role": action_role,
        "effect_metric_id": metric_id,
        "attribute_id": attribute_id,
        "measurement_scale_id": scale,
        "discovery": discovery_stats,
        "combined_validation_summary": audit_stats,
        "validation_folds": validation_stats,
        "selected_candidate": candidate,
    }
    digest = canonical_digest(source_payload)
    discovery_values = cast(dict[str, float], discovery_stats["values"])
    audit_values = cast(dict[str, float], audit_stats["values"])
    row: dict[str, object] = {
        "evidence_schema_id": TOOL_AFFINITY_EVIDENCE_SCHEMA_ID,
        "evidence_id": evidence_id,
        "tool_id": benchmark.tool_id,
        "method_family_id": benchmark.method_family_id,
        "benchmark_id": benchmark.benchmark_id,
        "action_role": action_role,
        "carrier_frequency": frequency,
        "target_horizon": (
            "completed_episode" if metric_id.startswith("trade_") else "next_1_bar"
        ),
        "attribute_id": attribute_id,
        "attribute_family": attribute_family,
        "measurement_scale_id": scale,
        "attribute_state_semantics": "causal online low < normal < high",
        "effect_metric_id": metric_id,
        "effect_unit": effect_unit,
        "favorable_direction": favorable_direction,
        "comparator_method_id": comparator,
        "association_shape": association_shape,
        "direction_semantics": direction_semantics,
        "conclusion": conclusion,
        "mechanism_status": mechanism_status,
        "mechanism": mechanism,
        "evidence_level": evidence_level,
        "discovery_start": DISCOVERY_START,
        "discovery_end": DISCOVERY_END.normalize(),
        "audit_start": AUDIT_START,
        "audit_end": AUDIT_END.normalize(),
        "overlap_status": "disjoint",
        "discovery_sample_count": sum(discovery_counts.values()),
        "audit_sample_count": sum(audit_counts.values()),
        "discovery_low_count": discovery_counts["low"],
        "discovery_normal_count": discovery_counts["normal"],
        "discovery_high_count": discovery_counts["high"],
        "audit_low_count": audit_counts["low"],
        "audit_normal_count": audit_counts["normal"],
        "audit_high_count": audit_counts["high"],
        "discovery_low_metric_value": discovery_values["low"],
        "discovery_normal_metric_value": discovery_values["normal"],
        "discovery_high_metric_value": discovery_values["high"],
        "audit_low_metric_value": audit_values["low"],
        "audit_normal_metric_value": audit_values["normal"],
        "audit_high_metric_value": audit_values["high"],
        "discovery_effect_value": discovery_effect,
        "audit_effect_value": audit_effect,
        "discovery_standardized_effect": discovery_standardized,
        "audit_standardized_effect": audit_standardized,
        "discovery_block_sign_consistency": discovery_consistency,
        "audit_block_sign_consistency": audit_consistency,
        "validation_fold_count": len(VALIDATION_FOLDS),
        "validation_fold_pass_count": sum(fold_passes),
        "validation_all_folds_pass": all_folds_pass,
        "validation_weakest_standardized_effect": _finite_min(
            fold_standardized
        ),
        "validation_weakest_block_sign_consistency": _finite_min(
            fold_consistencies
        ),
        "validation_min_bucket_sample_count": min(fold_min_bucket_counts),
        "tests_executed": tests,
        "insufficient_reason": insufficient_reason,
        "limitations": (
            "single CloudRidge carrier; fixed transparent tool probe; association "
            "does not authorize routing, parameter optimization or production use"
        ),
        "source_evidence_digest": digest,
        "rejected_formula_not_rejected_factor": bool(not supported),
        "production_authority": False,
    }
    return row, fold_rows


def _shape_statistics(
    period: _PreparedPeriod,
    *,
    action_role: str,
    metric_id: str,
) -> dict[str, object]:
    values: dict[str, float] = {}
    counts: dict[str, int] = {}
    for state in ("low", "normal", "high"):
        bucket = period.state_buckets[state]
        value, count = _aggregate_metric(
            bucket, action_role=action_role, metric_id=metric_id
        )
        values[state] = value
        counts[state] = count
    annual_bucket_values: list[float] = []
    linear_blocks: list[float] = []
    curved_blocks: list[float] = []
    for block in period.annual_state_buckets:
        block_values: dict[str, float] = {}
        for state in ("low", "normal", "high"):
            value, _ = _aggregate_metric(
                block[state],
                action_role=action_role,
                metric_id=metric_id,
            )
            block_values[state] = value
            if math.isfinite(value):
                annual_bucket_values.append(value)
        if all(math.isfinite(value) for value in block_values.values()):
            linear_blocks.append(block_values["high"] - block_values["low"])
            curved_blocks.append(
                (block_values["high"] + block_values["low"]) / 2.0
                - block_values["normal"]
            )
    pooled_scale = (
        float(np.std(annual_bucket_values, ddof=0))
        if annual_bucket_values
        else math.nan
    )
    if not math.isfinite(pooled_scale) or pooled_scale <= 1e-12:
        pooled_scale = 1.0
    finite_values = all(math.isfinite(value) for value in values.values())
    if finite_values:
        linear = values["high"] - values["low"]
        curved = (values["high"] + values["low"]) / 2.0 - values["normal"]
    else:
        linear = math.nan
        curved = math.nan
    curved_valid = bool(
        finite_values
        and np.sign(values["high"] - values["normal"])
        == np.sign(values["low"] - values["normal"])
        and np.sign(values["high"] - values["normal"]) != 0.0
    )
    return {
        "counts": counts,
        "values": values,
        "linear": {
            "effect": linear,
            "standardized": linear / pooled_scale,
            "block_consistency": _sign_consistency(linear_blocks, linear),
            "shape_valid": finite_values,
        },
        "curved": {
            "effect": curved,
            "standardized": curved / pooled_scale,
            "block_consistency": _sign_consistency(curved_blocks, curved),
            "shape_valid": curved_valid,
        },
    }


def _prepare_period(frame: pd.DataFrame) -> _PreparedPeriod:
    states = ("low", "normal", "high")
    state_buckets = {
        state: frame.loc[frame["state_bucket"].eq(state)] for state in states
    }
    annual_state_buckets = tuple(
        {
            state: block.loc[block["state_bucket"].eq(state)]
            for state in states
        }
        for _, block in frame.groupby("_decision_year", sort=True)
    )
    return _PreparedPeriod(
        state_buckets=state_buckets,
        annual_state_buckets=annual_state_buckets,
    )


def _aggregate_metric(
    frame: pd.DataFrame,
    *,
    action_role: str,
    metric_id: str,
) -> tuple[float, int]:
    value_column = (
        "long_capture_value"
        if action_role == "long_capture"
        else "cash_avoidance_value"
    )
    trade_column = (
        "long_trade_outcome"
        if action_role == "long_capture"
        else "cash_episode_outcome"
    )
    if metric_id == "turnover_per_decision_bar":
        values = _finite_series(frame["turnover"])
        return (_safe_mean(values), len(values))
    if metric_id.startswith("trade_"):
        values = _finite_series(frame[trade_column])
        if metric_id == "trade_win_rate":
            return (_positive_rate(values), len(values))
        if metric_id == "trade_payoff_ratio":
            return (_gain_loss_ratio(values), len(values))
        return (_safe_mean(values), len(values))
    values = _finite_series(frame[value_column])
    if metric_id == "net_log_return_per_decision_bar":
        return (_safe_mean(values), len(values))
    nonzero = values.loc[values.ne(0.0)]
    if metric_id == "positive_return_rate":
        return (_positive_rate(nonzero), len(nonzero))
    if metric_id == "gain_loss_ratio":
        return (_gain_loss_ratio(nonzero), len(nonzero))
    raise ValidationError(f"unsupported effect metric: {metric_id}")


def _finite_series(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").astype(float)
    return cast(pd.Series, numeric.loc[np.isfinite(numeric.to_numpy(dtype=float))])


def _safe_mean(values: pd.Series) -> float:
    return float(values.mean()) if not values.empty else math.nan


def _positive_rate(values: pd.Series) -> float:
    return float(values.gt(0.0).mean()) if not values.empty else math.nan


def _gain_loss_ratio(values: pd.Series) -> float:
    wins = values.loc[values > 0.0]
    losses = values.loc[values < 0.0]
    if wins.empty or losses.empty:
        return math.nan
    denominator = float((-losses).mean())
    return float(wins.mean()) / denominator if denominator > 0.0 else math.nan


def _sign_consistency(blocks: list[float], pooled: float) -> float:
    if not blocks or not math.isfinite(pooled) or pooled == 0.0:
        return 0.0
    target = np.sign(pooled)
    return float(np.mean([np.sign(value) == target for value in blocks]))


def _select_discovery_shape(stats: dict[str, object]) -> tuple[str, str]:
    linear = cast(dict[str, object], stats["linear"])
    curved = cast(dict[str, object], stats["curved"])
    linear_score = abs(float(linear["standardized"])) * float(
        linear["block_consistency"]
    )
    curved_score = abs(float(curved["standardized"])) * float(
        curved["block_consistency"]
    )
    if bool(curved["shape_valid"]) and curved_score > linear_score:
        effect = float(curved["effect"])
        return ("u_shaped" if effect > 0.0 else "inverted_u", "curved")
    effect = float(linear["effect"])
    if not math.isfinite(effect):
        return "unknown", "linear"
    return ("positive" if effect > 0.0 else "negative", "linear")


def _minimum_bucket_counts(
    *,
    frequency: str,
    metric_id: str,
    policy: ToolAffinityPolicy,
) -> tuple[int, int]:
    if metric_id.startswith("trade_"):
        return (
            (
                policy.minimum_daily_trade_bucket_discovery,
                policy.minimum_daily_trade_bucket_audit,
            )
            if frequency == "1d"
            else (
                policy.minimum_hourly_trade_bucket_discovery,
                policy.minimum_hourly_trade_bucket_audit,
            )
        )
    return (
        (
            policy.minimum_daily_bucket_discovery,
            policy.minimum_daily_bucket_audit,
        )
        if frequency == "1d"
        else (
            policy.minimum_hourly_bucket_discovery,
            policy.minimum_hourly_bucket_audit,
        )
    )


def _metric_semantics(metric_id: str) -> tuple[str, str]:
    if metric_id in {
        "positive_return_rate",
        "trade_win_rate",
    }:
        return "ratio_0_1", "higher_is_better"
    if metric_id in {"gain_loss_ratio", "trade_payoff_ratio"}:
        return "positive_ratio", "higher_is_better"
    if metric_id == "turnover_per_decision_bar":
        return "position_change_per_bar", "lower_is_better"
    return "log_return", "higher_is_better"


def _direction_semantics(
    *,
    association_shape: str,
    effect: float,
    metric_id: str,
    favorable_direction: str,
) -> str:
    if association_shape in {"none", "unknown"} or not math.isfinite(effect):
        return f"no audited direction established for {metric_id}"
    if association_shape in {"u_shaped", "inverted_u"}:
        raw = "extreme states exceed normal" if effect > 0.0 else "normal exceeds extremes"
    else:
        raw = "metric rises with attribute state" if effect > 0.0 else "metric falls with attribute state"
    return f"{raw}; {favorable_direction}"


def _mechanism_text(
    *,
    tool_id: str,
    attribute_family: str,
    action_role: str,
    supported: bool,
) -> str:
    family_hypotheses = {
        "direction_continuity": (
            "direction persistence changes the usable holding length and false-switch rate"
        ),
        "path_geometry": (
            "path efficiency separates directed displacement from oscillatory travel"
        ),
        "volatility": (
            "volatility changes rail width, filter transient size and transaction timing"
        ),
        "tail_structure": (
            "tail concentration changes whether a method captures or avoids rare large bars"
        ),
        "multiscale_activation": (
            "scale activation changes which tool frequency is aligned with the carrier"
        ),
        "bar_geometry": (
            "body, range and gap geometry change breakout confirmation and reversal risk"
        ),
    }
    hypothesis = family_hypotheses.get(
        attribute_family,
        "the attribute changes signal persistence, noise or opportunity geometry",
    )
    status = (
        "all frozen validation periods support the direction"
        if supported
        else "direction remains unestablished"
    )
    return (
        f"For {tool_id} under {action_role}, {hypothesis}; {status}. "
        "This is a mechanism-qualified association, not causal production authority."
    )


def _fold_failure_reason(
    *,
    discovery_signal: bool,
    adequate_counts: bool,
    finite: bool,
    sign_matches: bool,
    strong_enough: bool,
    consistent: bool,
    shape_valid: bool,
) -> str:
    reasons: list[str] = []
    if not discovery_signal:
        reasons.append("discovery relation did not pass the frozen gate")
    if not adequate_counts:
        reasons.append("metric-specific bucket sample count below frozen minimum")
    if not finite:
        reasons.append("metric undefined in at least one state bucket")
    if finite and not sign_matches:
        reasons.append("validation direction did not match discovery")
    if finite and not strong_enough:
        reasons.append("validation standardized effect below frozen minimum")
    if not consistent:
        reasons.append("validation annual-block consistency below frozen minimum")
    if not shape_valid:
        reasons.append("selected discovery shape did not reproduce")
    return "; ".join(reasons)


def _insufficient_reason_v12(
    *,
    discovery_signal: bool,
    fold_passes: list[bool],
) -> str:
    if not discovery_signal:
        return "discovery effect/count/shape/annual consistency below frozen gate"
    failed = [
        fold.fold_id
        for fold, passed in zip(VALIDATION_FOLDS, fold_passes, strict=True)
        if not passed
    ]
    return (
        "frozen relation failed independent validation: " + ", ".join(failed)
        if failed
        else "frozen evidence gate not met"
    )


def _finite_min(values: list[float]) -> float:
    finite = [float(value) for value in values if math.isfinite(value)]
    return min(finite) if finite else math.nan


def _validate_tool_evidence(
    evidence: pd.DataFrame,
    fold_evidence: pd.DataFrame,
    *,
    expected_tool_ids: set[str],
) -> None:
    if evidence.empty or tuple(evidence.columns) != TOOL_EVIDENCE_COLUMNS:
        raise ValidationError("tool affinity evidence schema is incomplete")
    if set(evidence["tool_id"]) != expected_tool_ids:
        raise ValidationError("tool affinity evidence did not execute every tool")
    if set(evidence["effect_metric_id"]) != set(REQUIRED_EFFECT_METRICS):
        raise ValidationError("tool affinity evidence metric coverage is incomplete")
    if set(evidence["action_role"]) != set(REQUIRED_ACTION_ROLES):
        raise ValidationError("tool affinity evidence action-role coverage is incomplete")
    if bool(evidence["production_authority"].any()):
        raise ValidationError("tool evidence cannot have production authority")
    if pd.to_datetime(evidence["audit_end"]).max() >= BLACKBOX_START:
        raise ValidationError("tool evidence opened the sealed blackbox")
    if bool(evidence["evidence_id"].duplicated().any()):
        raise ValidationError("tool affinity evidence ids are not unique")
    if (
        fold_evidence.empty
        or tuple(fold_evidence.columns) != TOOL_FOLD_EVIDENCE_COLUMNS
    ):
        raise ValidationError("tool fold evidence schema is incomplete")
    if bool(fold_evidence["fold_evidence_id"].duplicated().any()):
        raise ValidationError("tool fold evidence ids are not unique")
    if set(fold_evidence["evidence_id"]) != set(evidence["evidence_id"]):
        raise ValidationError("tool fold evidence does not cover every relation")
    expected_fold_ids = {fold.fold_id for fold in VALIDATION_FOLDS}
    grouped_fold_ids = fold_evidence.groupby("evidence_id")[
        "validation_fold_id"
    ].agg(lambda values: set(values))
    if any(value != expected_fold_ids for value in grouped_fold_ids):
        raise ValidationError("tool relation does not have every validation fold")
    if pd.to_datetime(fold_evidence["validation_end"]).max() >= BLACKBOX_START:
        raise ValidationError("tool fold evidence opened the sealed blackbox")
    if bool(fold_evidence["production_authority"].any()):
        raise ValidationError("tool fold evidence cannot have production authority")
    passes = fold_evidence.groupby("evidence_id")["passed"].agg(
        ["sum", "all", "count"]
    )
    indexed = evidence.set_index("evidence_id")
    if not bool(
        indexed["validation_fold_count"].astype(int).eq(
            passes["count"].astype(int)
        ).all()
    ):
        raise ValidationError("tool fold count summary mismatch")
    if not bool(
        indexed["validation_fold_pass_count"].astype(int).eq(
            passes["sum"].astype(int)
        ).all()
    ):
        raise ValidationError("tool fold pass-count summary mismatch")
    if not bool(
        indexed["validation_all_folds_pass"].astype(bool).eq(
            passes["all"].astype(bool)
        ).all()
    ):
        raise ValidationError("tool all-fold summary mismatch")
    minimum_bucket_counts = fold_evidence.groupby("evidence_id")[
        ["low_count", "normal_count", "high_count"]
    ].min().min(axis=1)
    if not bool(
        indexed["validation_min_bucket_sample_count"]
        .astype(int)
        .eq(minimum_bucket_counts.astype(int))
        .all()
    ):
        raise ValidationError("tool fold minimum bucket-count summary mismatch")
    supported = indexed["conclusion"].eq("supported")
    if bool((supported & ~passes["all"].astype(bool)).any()):
        raise ValidationError("supported relation failed a validation fold")
    unknown = evidence["association_shape"].isin(("none", "unknown"))
    if bool(evidence.loc[unknown, "tests_executed"].str.len().eq(0).any()):
        raise ValidationError("untested tool relation was emitted")
    if bool(evidence.loc[unknown, "insufficient_reason"].str.len().eq(0).any()):
        raise ValidationError("insufficient tool relation lacks a reason")


def tool_evidence_semantic_digest(frame: pd.DataFrame) -> str:
    """Return a stable digest independent of parquet byte encoding."""

    ordered = frame.loc[:, TOOL_EVIDENCE_COLUMNS].copy()
    for column in ordered.select_dtypes(include=["datetime", "datetimetz"]).columns:
        ordered[column] = ordered[column].astype(str)
    records = json.loads(ordered.to_json(orient="records", date_format="iso"))
    return canonical_digest(
        {
            "schema_id": TOOL_AFFINITY_EVIDENCE_SCHEMA_ID,
            "columns": list(TOOL_EVIDENCE_COLUMNS),
            "records": records,
        }
    )


def tool_fold_evidence_semantic_digest(frame: pd.DataFrame) -> str:
    """Return the stable digest for per-fold validation evidence."""

    ordered = frame.loc[:, TOOL_FOLD_EVIDENCE_COLUMNS].copy()
    for column in ordered.select_dtypes(include=["datetime", "datetimetz"]).columns:
        ordered[column] = ordered[column].astype(str)
    records = json.loads(ordered.to_json(orient="records", date_format="iso"))
    return canonical_digest(
        {
            "schema_id": TOOL_AFFINITY_FOLD_EVIDENCE_SCHEMA_ID,
            "columns": list(TOOL_FOLD_EVIDENCE_COLUMNS),
            "records": records,
        }
    )


def _naive_datetime(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, errors="coerce")
    if parsed.dt.tz is not None:
        return parsed.dt.tz_convert("Asia/Shanghai").dt.tz_localize(None)
    return parsed


__all__ = [
    "AUDIT_END",
    "BLACKBOX_START",
    "DISCOVERY_END",
    "DISCOVERY_START",
    "TOOL_AFFINITY_EVIDENCE_SCHEMA_ID",
    "TOOL_AFFINITY_FOLD_EVIDENCE_SCHEMA_ID",
    "TOOL_AFFINITY_POLICY_VERSION",
    "TOOL_EVIDENCE_COLUMNS",
    "TOOL_FOLD_EVIDENCE_COLUMNS",
    "VALIDATION_FOLDS",
    "ToolAffinityPolicy",
    "ValidationFold",
    "build_tool_state_affinity_evidence",
    "tool_evidence_semantic_digest",
    "tool_fold_evidence_semantic_digest",
]
