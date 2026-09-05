"""Strategy-neutral matched-attribution math for timing period diagnostics.

This module deliberately knows nothing about V62 states, K-line formulas, or
episode semantics.  A strategy-specific adapter must construct the episode
table, choose causally visible entry attributes, label ex-post lifecycle
attributes, and render domain-specific charts.
"""

# pyright: reportAny=false, reportArgumentType=false
# pyright: reportAttributeAccessIssue=false, reportGeneralTypeIssues=false
# pyright: reportIndexIssue=false, reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

from __future__ import annotations

from itertools import combinations
from math import factorial
from typing import TypeAlias

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

FeatureGroup: TypeAlias = tuple[tuple[str, ...], tuple[str, ...]]


def timing_matched_attribution_contract() -> dict[str, object]:
    """Return the project-level boundary for matched period attribution."""

    return {
        "schema_id": "market_state_timing_matched_attribution@1.0",
        "scope": "independent_bidirectional_timing_strategy_middle_platform",
        "authority": "diagnostic_only_not_runtime_or_parameter_authority",
        "kernel_responsibilities": [
            "reference_period_standardization",
            "exact_group_knn_counterfactual",
            "trimmed_propensity_reweighting",
            "common_support_and_balance",
            "sequential_value_decomposition",
            "order_independent_shapley_mix_decomposition",
            "bootstrap_conditional_residual_interval",
        ],
        "adapter_responsibilities": [
            "strategy_and_state_lifecycle_definition",
            "episode_table_construction",
            "causally_visible_entry_feature_selection",
            "ex_post_lifecycle_feature_labelling",
            "domain_specific_graphical_attribution",
        ],
        "single_universal_episode_definition_forbidden": True,
        "ex_post_features_may_gain_runtime_authority": False,
        "diagnostic_period_may_select_parameters": False,
    }


def _standardized_from_reference(
    development: pd.DataFrame,
    diagnostic: pd.DataFrame,
    features: tuple[str, ...],
) -> tuple[np.ndarray, np.ndarray]:
    if not features:
        raise ValueError("KNN matching requires at least one continuous feature")
    centre = development[list(features)].mean().to_numpy(float)
    scale = development[list(features)].std(ddof=0).to_numpy(float)
    scale = np.where(scale > 1e-12, scale, 1.0)
    dev = (development[list(features)].to_numpy(float) - centre) / scale
    diag = (diagnostic[list(features)].to_numpy(float) - centre) / scale
    return dev, diag


def _exact_key(
    frame: pd.DataFrame,
    columns: tuple[str, ...],
    location: int,
) -> tuple[str, ...]:
    return tuple(str(frame.iloc[location][column]) for column in columns)


def knn_counterfactual_match(
    development: pd.DataFrame,
    diagnostic: pd.DataFrame,
    *,
    features: tuple[str, ...],
    exact: tuple[str, ...],
    outcome_column: str,
    k: int,
    support_quantile: float = 0.95,
) -> dict[str, object]:
    """Match diagnostic episodes to reference episodes inside exact groups."""

    if k < 1:
        raise ValueError("k must be positive")
    if not 0.0 < support_quantile < 1.0:
        raise ValueError("support_quantile must lie strictly between zero and one")
    dev_values, diag_values = _standardized_from_reference(
        development,
        diagnostic,
        features,
    )
    dev_groups: dict[tuple[str, ...], list[int]] = {}
    for location in range(len(development)):
        dev_groups.setdefault(_exact_key(development, exact, location), []).append(
            location
        )
    predictions = np.zeros(len(diagnostic), dtype=float)
    nearest_distances = np.zeros(len(diagnostic), dtype=float)
    first_neighbor = np.zeros(len(diagnostic), dtype=int)
    weights = np.zeros(len(development), dtype=float)
    outcome = development[outcome_column].to_numpy(float)
    for location in range(len(diagnostic)):
        key = _exact_key(diagnostic, exact, location)
        candidates = np.asarray(dev_groups.get(key, []), dtype=int)
        if len(candidates) == 0:
            raise RuntimeError(f"no development common-support group for {key}")
        distances = np.sqrt(
            np.mean(
                (dev_values[candidates] - diag_values[location]) ** 2,
                axis=1,
            )
        )
        order = np.argsort(distances, kind="stable")
        selected = candidates[order[: min(k, len(order))]]
        predictions[location] = float(outcome[selected].mean())
        nearest_distances[location] = float(distances[order[0]])
        first_neighbor[location] = int(selected[0])
        weights[selected] += 1.0 / len(selected)

    self_nearest: list[float] = []
    for members_list in dev_groups.values():
        members = np.asarray(members_list, dtype=int)
        if len(members) < 2:
            continue
        local = dev_values[members]
        distances = np.sqrt(
            np.mean((local[:, None, :] - local[None, :, :]) ** 2, axis=2)
        )
        np.fill_diagonal(distances, np.inf)
        self_nearest.extend(np.min(distances, axis=1).tolist())
    if not self_nearest:
        raise RuntimeError("exact groups need at least one reference pair for support")
    caliper = float(np.quantile(self_nearest, support_quantile))
    coverage = float(np.mean(nearest_distances <= caliper))
    return {
        "predictions": predictions,
        "weights": weights,
        "nearest_distances": nearest_distances,
        "first_neighbor": first_neighbor,
        "common_support_caliper": caliper,
        "common_support_coverage": coverage,
        "counterfactual_outcome_mean": float(predictions.mean()),
        "exact_groups": sorted("|".join(key) for key in dev_groups),
    }


def propensity_counterfactual_weights(
    development: pd.DataFrame,
    diagnostic: pd.DataFrame,
    *,
    features: tuple[str, ...],
    categorical: tuple[str, ...],
    outcome_column: str,
    trim_quantile: float = 0.99,
) -> dict[str, object]:
    """Reweight reference episodes to the diagnostic episode composition."""

    if not 0.0 < trim_quantile <= 1.0:
        raise ValueError("trim_quantile must lie in (0, 1]")
    combined = pd.concat(
        [development.assign(_diagnostic=0), diagnostic.assign(_diagnostic=1)],
        ignore_index=True,
    )
    design_parts: list[pd.DataFrame] = []
    if features:
        continuous = combined[list(features)].copy()
        centre = development[list(features)].mean()
        scale = development[list(features)].std(ddof=0).replace(0.0, 1.0)
        design_parts.append((continuous - centre) / scale)
    if categorical:
        design_parts.append(
            pd.get_dummies(
                combined[list(categorical)].astype(str),
                columns=list(categorical),
                dtype=float,
            )
        )
    if not design_parts:
        raise ValueError("propensity weighting requires at least one feature")
    design = pd.concat(design_parts, axis=1).to_numpy(float)
    label = combined["_diagnostic"].to_numpy(int)
    model = LogisticRegression(C=1.0, max_iter=2000, solver="lbfgs")
    model.fit(design, label)
    propensity = np.clip(model.predict_proba(design)[:, 1], 0.01, 0.99)
    dev_propensity = propensity[: len(development)]
    weights = dev_propensity / (1.0 - dev_propensity)
    trim = float(np.quantile(weights, trim_quantile))
    weights = np.minimum(weights, trim)
    normalized = weights / weights.sum()
    outcome = development[outcome_column].to_numpy(float)
    ess = float(weights.sum() ** 2 / np.square(weights).sum())
    return {
        "weights": weights,
        "propensity": propensity,
        "weight_trim_quantile": trim_quantile,
        "weight_trim_value": trim,
        "effective_sample_size": ess,
        "counterfactual_outcome_mean": float(np.dot(normalized, outcome)),
    }


def weighted_standardized_mean_differences(
    development: pd.DataFrame,
    diagnostic: pd.DataFrame,
    features: tuple[str, ...],
    weights: np.ndarray,
) -> list[dict[str, object]]:
    """Measure continuous-feature balance after reference reweighting."""

    if len(weights) != len(development) or float(weights.sum()) <= 0.0:
        raise ValueError("weights must be positive and align with development rows")
    normalized = weights / weights.sum()
    rows: list[dict[str, object]] = []
    for feature in features:
        dev = development[feature].to_numpy(float)
        diag = diagnostic[feature].to_numpy(float)
        dev_mean = float(np.dot(normalized, dev))
        diag_mean = float(diag.mean())
        dev_var = float(np.dot(normalized, np.square(dev - dev_mean)))
        diag_var = float(np.var(diag))
        pooled = np.sqrt(max((dev_var + diag_var) / 2.0, 1e-12))
        rows.append(
            {
                "feature": feature,
                "standardized_mean_difference": (diag_mean - dev_mean) / pooled,
            }
        )
    return rows


def sequential_unit_value_decomposition(
    development: pd.DataFrame,
    diagnostic: pd.DataFrame,
    *,
    entry_counterfactual_gross: float,
    lifecycle_counterfactual_gross: float,
    method: str,
    net_column: str,
    gross_column: str,
    cost_column: str,
) -> dict[str, object]:
    """Reconcile a net unit-value gap into composition, residual, and cost."""

    dev_net = float(development[net_column].mean())
    diag_net = float(diagnostic[net_column].mean())
    dev_gross = float(development[gross_column].mean())
    diag_gross = float(diagnostic[gross_column].mean())
    dev_cost = float(development[cost_column].mean())
    diag_cost = float(diagnostic[cost_column].mean())
    components = {
        "entry_composition_effect": entry_counterfactual_gross - dev_gross,
        "lifecycle_composition_effect": (
            lifecycle_counterfactual_gross - entry_counterfactual_gross
        ),
        "conditional_capability_residual": (
            diag_gross - lifecycle_counterfactual_gross
        ),
        "cost_effect": diag_cost - dev_cost,
    }
    reconstructed = float(sum(components.values()))
    observed = diag_net - dev_net
    if not np.isclose(reconstructed, observed, atol=1e-12):
        raise RuntimeError("matched decomposition does not reconcile to observed gap")
    return {
        "method": method,
        "development_net_unit_value": dev_net,
        "diagnostic_net_unit_value": diag_net,
        "observed_net_unit_value_gap": observed,
        "development_gross_unit_value": dev_gross,
        "diagnostic_gross_unit_value": diag_gross,
        "entry_counterfactual_gross_unit_value": entry_counterfactual_gross,
        "lifecycle_counterfactual_gross_unit_value": lifecycle_counterfactual_gross,
        **components,
        "reconstructed_gap": reconstructed,
    }


def bootstrap_weighted_residual_interval(
    diagnostic_outcome: np.ndarray,
    development_outcome: np.ndarray,
    development_weights: np.ndarray,
    *,
    repetitions: int,
    random_seed: int,
) -> tuple[float, float]:
    """Bootstrap the diagnostic-minus-weighted-reference residual interval."""

    if repetitions < 100:
        raise ValueError("bootstrap repetitions must be at least 100")
    rng = np.random.default_rng(random_seed)
    probability = development_weights / development_weights.sum()
    values = np.empty(repetitions, dtype=float)
    for repeat in range(repetitions):
        diag_sample = rng.choice(
            diagnostic_outcome,
            size=len(diagnostic_outcome),
            replace=True,
        )
        dev_sample = rng.choice(
            development_outcome,
            size=len(development_outcome),
            replace=True,
            p=probability,
        )
        values[repeat] = float(diag_sample.mean() - dev_sample.mean())
    return float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))


def shapley_from_value_map(
    groups: tuple[str, ...],
    value_map: dict[frozenset[str], float],
) -> dict[str, float]:
    """Return permutation Shapley contributions for a complete subset map."""

    group_count = len(groups)
    if group_count == 0:
        return {}
    denominator = factorial(group_count)
    contributions = {group: 0.0 for group in groups}
    for group in groups:
        others = tuple(candidate for candidate in groups if candidate != group)
        for size in range(len(others) + 1):
            coefficient = factorial(size) * factorial(group_count - size - 1)
            coefficient /= denominator
            for subset_values in combinations(others, size):
                subset = frozenset(subset_values)
                contributions[group] += coefficient * (
                    value_map[subset | {group}] - value_map[subset]
                )
    return contributions


def propensity_shapley_attribution(
    development: pd.DataFrame,
    diagnostic: pd.DataFrame,
    *,
    feature_groups: dict[str, FeatureGroup],
    outcome_column: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Attribute the full propensity composition shift without order bias."""

    groups = tuple(feature_groups)
    development_outcome = float(development[outcome_column].mean())
    value_map: dict[frozenset[str], float] = {frozenset(): development_outcome}
    subset_rows: list[dict[str, object]] = [
        {
            "active_groups": "none",
            "counterfactual_outcome_mean": development_outcome,
            "effective_sample_size": len(development),
        }
    ]
    for size in range(1, len(groups) + 1):
        for subset_values in combinations(groups, size):
            subset = frozenset(subset_values)
            features: list[str] = []
            categorical: list[str] = []
            for group in groups:
                if group not in subset:
                    continue
                local_features, local_categorical = feature_groups[group]
                features.extend(local_features)
                categorical.extend(local_categorical)
            weighted = propensity_counterfactual_weights(
                development,
                diagnostic,
                features=tuple(dict.fromkeys(features)),
                categorical=tuple(dict.fromkeys(categorical)),
                outcome_column=outcome_column,
            )
            value = float(weighted["counterfactual_outcome_mean"])
            value_map[subset] = value
            subset_rows.append(
                {
                    "active_groups": "+".join(sorted(subset)),
                    "counterfactual_outcome_mean": value,
                    "effective_sample_size": weighted["effective_sample_size"],
                }
            )
    contributions = shapley_from_value_map(groups, value_map)
    full_shift = value_map[frozenset(groups)] - value_map[frozenset()]
    if not np.isclose(sum(contributions.values()), full_shift, atol=1e-12):
        raise RuntimeError("Shapley composition attribution does not reconcile")
    contribution_frame = pd.DataFrame(
        [
            {
                "group": group,
                "outcome_mix_effect": value,
                "share_of_full_mix_effect": (
                    value / full_shift if abs(full_shift) > 1e-12 else 0.0
                ),
            }
            for group, value in contributions.items()
        ]
    )
    return contribution_frame, pd.DataFrame(subset_rows)


def classify_matched_attribution(
    decompositions: pd.DataFrame,
    *,
    entry_coverage: float,
    lifecycle_coverage: float,
    propensity_ess: float,
    development_count: int,
) -> str:
    """Classify composition versus conditional capability with support gates."""

    residual = decompositions["conditional_capability_residual"]
    support_ok = bool(
        entry_coverage >= 0.80
        and lifecycle_coverage >= 0.80
        and propensity_ess >= 0.20 * development_count
    )
    sign_consistent = bool((residual < 0.0).all() or (residual > 0.0).all())
    if not support_ok or not sign_consistent:
        return "inconclusive_common_support_or_method_disagreement"
    observed = float(decompositions.iloc[0]["observed_net_unit_value_gap"])
    residual_share = float(abs(residual.median()) / max(abs(observed), 1e-12))
    if bool((residual < 0.0).all()) and residual_share >= 0.25:
        return "mixed_shift_with_material_conditional_capability_drift"
    return "opportunity_and_lifecycle_mix_dominant"


__all__ = [
    "FeatureGroup",
    "bootstrap_weighted_residual_interval",
    "classify_matched_attribution",
    "knn_counterfactual_match",
    "timing_matched_attribution_contract",
    "propensity_counterfactual_weights",
    "propensity_shapley_attribution",
    "sequential_unit_value_decomposition",
    "shapley_from_value_map",
    "weighted_standardized_mean_differences",
]
