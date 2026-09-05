"""Minimal causal six-axis to timing-tool feedback loop.

The module deliberately provides one frozen linear selector rather than a
model zoo.  It is a research challenger: development data fit the mapping,
later periods decide whether the mapping reduces parameter regret.
"""

# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportCallIssue=false, reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportOperatorIssue=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError

SCHEMA_ID: Final[str] = "market_state_timing_six_axis_tool_loop@0.1"
AXIS_COLUMNS: Final[tuple[str, ...]] = (
    "axis_direction",
    "axis_directional_memory",
    "axis_volatility_level",
    "axis_volatility_memory",
    "axis_path_tail",
    "axis_cross_sectional_coherence",
)


@dataclass(frozen=True, slots=True)
class FrozenSixAxisLinearPolicy:
    """A train-only robust-scaled ridge formula for choosing tool A or B."""

    candidate_a_id: str
    candidate_b_id: str
    forecast_horizon_bars: int
    ridge_penalty: float
    feature_columns: tuple[str, ...]
    feature_medians: tuple[float, ...]
    feature_iqrs: tuple[float, ...]
    intercept: float
    coefficients: tuple[float, ...]
    development_row_count: int

    def __post_init__(self) -> None:
        size = len(self.feature_columns)
        if size != len(self.feature_medians) or size != len(self.feature_iqrs):
            raise ValueError("six-axis policy scaling vectors must align")
        if size != len(self.coefficients) or size == 0:
            raise ValueError("six-axis policy coefficients must align")
        if self.forecast_horizon_bars < 1 or self.development_row_count < size + 2:
            raise ValueError("six-axis policy needs a positive horizon and enough development rows")
        if self.ridge_penalty < 0.0:
            raise ValueError("ridge penalty must be non-negative")
        if not all(value > 0.0 for value in self.feature_iqrs):
            raise ValueError("six-axis policy IQR scales must be positive")

    def as_dict(self) -> dict[str, object]:
        """Return a stable JSON-ready representation."""

        return asdict(self)


def timing_six_axis_tool_loop_contract() -> dict[str, object]:
    """Return the decisive research-loop contract."""

    return {
        "schema_id": SCHEMA_ID,
        "scientific_role": "causal_six_axis_tool_selection_challenger",
        "development_only_fit": True,
        "feature_availability": "decision_eligible_from_next_trading_day",
        "model_family": "single_robust_scaled_ridge_formula",
        "complex_state_machine_search": False,
        "winner_rule": (
            "dynamic_parameter_gap_reduction_must_be_positive_in_repeat_audit_and_aggregate_blackbox"
        ),
        "market_supply_cancels_inside_static_dynamic_pair": True,
        "signal_authority": False,
        "routing_authority": False,
        "parameter_authority": False,
        "production_authority": False,
    }


def fit_frozen_six_axis_policy(
    features: pd.DataFrame,
    relative_forward_value: pd.Series,
    *,
    candidate_a_id: str,
    candidate_b_id: str,
    forecast_horizon_bars: int,
    ridge_penalty: float = 1.0,
) -> FrozenSixAxisLinearPolicy:
    """Fit one frozen robust-scaled ridge formula on development rows only."""

    if tuple(features.columns) != AXIS_COLUMNS:
        raise ValidationError("six-axis selector requires the canonical six headline axes")
    if not features.index.equals(relative_forward_value.index):
        raise ValidationError("six-axis features and relative target must align")
    numeric_features = features.apply(pd.to_numeric, errors="coerce")
    numeric_target = pd.to_numeric(relative_forward_value, errors="coerce")
    if numeric_features.isna().any().any() or numeric_target.isna().any():
        raise ValidationError("development selector rows must be complete and finite")
    values = numeric_features.to_numpy(float)
    target = numeric_target.to_numpy(float)
    if not np.isfinite(values).all() or not np.isfinite(target).all():
        raise ValidationError("development selector rows must be finite")
    if len(values) < len(AXIS_COLUMNS) + 2:
        raise ValidationError("insufficient development rows for the six-axis selector")
    medians = np.median(values, axis=0)
    iqrs = np.quantile(values, 0.75, axis=0) - np.quantile(values, 0.25, axis=0)
    iqrs = np.where(iqrs > 1e-12, iqrs, 1.0)
    standardized = (values - medians) / iqrs
    design = np.column_stack([np.ones(len(standardized)), standardized])
    penalty = np.eye(design.shape[1])
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(
        design.T @ design + ridge_penalty * penalty,
        design.T @ target,
    )
    return FrozenSixAxisLinearPolicy(
        candidate_a_id=candidate_a_id,
        candidate_b_id=candidate_b_id,
        forecast_horizon_bars=forecast_horizon_bars,
        ridge_penalty=ridge_penalty,
        feature_columns=AXIS_COLUMNS,
        feature_medians=tuple(float(value) for value in medians),
        feature_iqrs=tuple(float(value) for value in iqrs),
        intercept=float(coefficients[0]),
        coefficients=tuple(float(value) for value in coefficients[1:]),
        development_row_count=len(values),
    )


def predict_tool_a_advantage(
    policy: FrozenSixAxisLinearPolicy,
    features: pd.DataFrame,
) -> pd.Series:
    """Predict A-minus-B forward value without refitting the frozen policy."""

    if tuple(features.columns) != policy.feature_columns:
        raise ValidationError("prediction features do not match the frozen policy")
    numeric = features.apply(pd.to_numeric, errors="coerce")
    values = numeric.to_numpy(float)
    valid = np.isfinite(values).all(axis=1)
    predictions = np.full(len(features), np.nan, dtype=float)
    if valid.any():
        medians = np.asarray(policy.feature_medians, dtype=float)
        iqrs = np.asarray(policy.feature_iqrs, dtype=float)
        coefficients = np.asarray(policy.coefficients, dtype=float)
        predictions[valid] = policy.intercept + ((values[valid] - medians) / iqrs) @ coefficients
    return pd.Series(predictions, index=features.index, dtype=float)


def build_forward_relative_value(
    candidate_a_net_value: pd.Series,
    candidate_b_net_value: pd.Series,
    *,
    horizon_bars: int,
) -> pd.Series:
    """Build the research label: next-H-bars A net value minus B net value."""

    if horizon_bars < 1:
        raise ValueError("horizon_bars must be positive")
    if not candidate_a_net_value.index.equals(candidate_b_net_value.index):
        raise ValidationError("candidate value paths must align")
    difference = pd.to_numeric(candidate_a_net_value, errors="coerce") - pd.to_numeric(
        candidate_b_net_value, errors="coerce"
    )
    reversed_value = difference.iloc[::-1]
    forward = reversed_value.rolling(horizon_bars, min_periods=horizon_bars).sum().iloc[::-1]
    return pd.Series(forward.to_numpy(float), index=difference.index, dtype=float)


def select_and_lock_candidate_actions(
    predicted_a_advantage: pd.Series,
    candidate_a_actions: pd.Series,
    candidate_b_actions: pd.Series,
    *,
    minimum_holding_bars: int,
) -> pd.Series:
    """Select candidate actions causally, then enforce the shared scale lock."""

    if minimum_holding_bars < 1:
        raise ValueError("minimum_holding_bars must be positive")
    if not (
        predicted_a_advantage.index.equals(candidate_a_actions.index)
        and predicted_a_advantage.index.equals(candidate_b_actions.index)
    ):
        raise ValidationError("selector predictions and candidate actions must align")
    choose_a = predicted_a_advantage.ge(0.0) & predicted_a_advantage.notna()
    proposed = np.where(
        choose_a.to_numpy(bool),
        pd.to_numeric(candidate_a_actions, errors="raise").to_numpy(int),
        pd.to_numeric(candidate_b_actions, errors="raise").to_numpy(int),
    )
    current = 0
    dwell = minimum_holding_bars
    locked = np.zeros(len(proposed), dtype=int)
    for index, value in enumerate(proposed):
        candidate = int(value)
        if candidate != current and dwell >= minimum_holding_bars:
            current = candidate
            dwell = 1
        else:
            dwell = min(minimum_holding_bars, dwell + 1)
        locked[index] = current
    return pd.Series(locked, index=predicted_a_advantage.index, dtype=int)


def summarize_axis_formula(policy: FrozenSixAxisLinearPolicy) -> pd.DataFrame:
    """Report standardized association weights without claiming causality."""

    absolute = np.abs(np.asarray(policy.coefficients, dtype=float))
    total = float(absolute.sum())
    shares = absolute / total if total > 0.0 else np.zeros_like(absolute)
    return pd.DataFrame(
        {
            "axis_id": policy.feature_columns,
            "standardized_coefficient": policy.coefficients,
            "absolute_weight_share": shares,
            "causal_effect_claimed": False,
        }
    ).sort_values("absolute_weight_share", ascending=False, ignore_index=True)


__all__ = [
    "AXIS_COLUMNS",
    "SCHEMA_ID",
    "FrozenSixAxisLinearPolicy",
    "build_forward_relative_value",
    "fit_frozen_six_axis_policy",
    "predict_tool_a_advantage",
    "select_and_lock_candidate_actions",
    "summarize_axis_formula",
    "timing_six_axis_tool_loop_contract",
]
