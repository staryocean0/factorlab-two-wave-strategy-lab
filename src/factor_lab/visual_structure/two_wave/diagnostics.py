"""Descriptive audits of frozen rejection flags; no recognizer or rule selection."""

from __future__ import annotations

import math
from collections import Counter
from itertools import combinations

import numpy as np

REJECTION_RULES = (
    "poor_pivot_fit",
    "phase_lines_cross_or_collapse",
    "expanding",
    "converging",
    "high_low_direction_conflict",
    "within_phase_direction_conflict",
    "phase_slope_disagreement",
    "uneven_phase_drift",
    "cycle_amplitude_change",
    "large_envelope_expansion",
)
INVALID_RULES = ("invalid_regression", "nonpositive_or_tiny_width")
# These overlapping groups describe mechanisms. They are not candidate configs.
RULE_GROUPS = {
    "local_drift_and_cycle_amplitude": ("uneven_phase_drift", "cycle_amplitude_change"),
    "parallel_fit_and_drift_consistency": ("poor_pivot_fit", "phase_slope_disagreement", "uneven_phase_drift"),
    "phase_width_and_slope": ("phase_lines_cross_or_collapse", "expanding", "converging", "phase_slope_disagreement"),
    "amplitude_and_envelope": ("cycle_amplitude_change", "large_envelope_expansion"),
    "direction_conflicts": ("high_low_direction_conflict", "within_phase_direction_conflict"),
    "all_morphology_rejections": REJECTION_RULES,
}


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def distribution(values: list[float]) -> dict:
    finite = [float(value) for value in values if value is not None and math.isfinite(value)]
    return {
        "n": len(finite),
        "quantiles": {str(q): float(np.quantile(finite, q)) for q in (0, 0.25, 0.5, 0.75, 0.9, 0.95, 1)} if finite else None,
    }


def diagnostic_features(structure: dict, pivots: list[dict]) -> dict:
    """Decompose already-fitted diagnostics, without fitting a replacement model.

    The two remaining residual dimensions of the five-point parallel model are
    majority-phase curvature and the difference between high/low line slopes.
    Their squared errors add exactly, with time-dependent weights.
    """
    if len(pivots) != 5 or [p["pivot_id"] for p in pivots] != structure["pivot_ids"]:
        raise ValueError("five member pivots must match the frozen structure order")
    t = np.asarray([p["occurrence_bar"] for p in pivots], dtype=float)
    if np.any(np.diff(t) <= 0):
        raise ValueError("member occurrence bars must increase strictly")
    t -= t[0]
    durations = np.diff(t[::2])
    fractions = durations / t[-1]
    g = structure["geometry"]
    result = {
        "cycle_duration_bars": durations.astype(int).tolist(),
        "cycle_duration_ratio": float(max(durations) / min(durations)),
        "cycle_duration_fractions": fractions.tolist(),
    }
    if not g["valid"]:
        return result
    x = np.asarray([p["log_price"] for p in pivots])
    width = g["width"]
    steps = np.diff(x[::2]) / width
    slopes = steps / fractions
    u = float(abs(slopes[0] - slopes[1]))
    phase_difference = g["phase_lines"]["high"]["normalized_drift"] - g["phase_lines"]["low"]["normalized_drift"]
    r, s = (float(value) for value in fractions)
    curvature_sse = (r * s) ** 2 / (2 * (r * r + r * s + s * s)) * u * u
    tau = t / t[-1]
    mask = np.asarray([p["kind"] == "high" for p in pivots])
    sumsq_high = float(np.sum((tau[mask] - tau[mask].mean()) ** 2))
    sumsq_low = float(np.sum((tau[~mask] - tau[~mask].mean()) ** 2))
    phase_sse = sumsq_high * sumsq_low / (sumsq_high + sumsq_low) * phase_difference**2
    reconstructed_error = math.sqrt((curvature_sse + phase_sse) / 5)
    detrended = x - g["b"] * t
    detrended_amplitudes = [float(np.ptp(detrended[:3])), float(np.ptp(detrended[2:]))]
    result.update(
        {
            "majority_step_displacements": steps.tolist(),
            "majority_local_normalized_slopes": slopes.tolist(),
            "uneven_phase_drift_value": u,
            "equal_duration_drift_difference_diagnostic_only": float(2 * abs(steps[0] - steps[1])),
            "opposite_majority_displacement_signs_without_tolerance": bool(steps[0] * steps[1] < 0),
            "phase_slope_disagreement_value": abs(phase_difference),
            "E": g["E"],
            "D": g["D"],
            "E_reconstructed": reconstructed_error,
            "E_reconstruction_absolute_error": abs(reconstructed_error - g["E"]),
            "curvature_share_of_pivot_SSE": curvature_sse / (curvature_sse + phase_sse) if curvature_sse + phase_sse else None,
            "cycle_amplitude_ratio": g["cycle_amplitude_ratio"],
            "frozen_drift_removed_pivot_amplitudes": detrended_amplitudes,
            "frozen_drift_removed_amplitude_ratio_diagnostic_only": max(detrended_amplitudes) / min(detrended_amplitudes)
            if min(detrended_amplitudes) > 0
            else None,
            "phase_width_ratio": g["phase_width_ratio"],
            "envelope_to_model_width_ratio": g["envelope_to_model_width_ratio"],
        }
    )
    return result


def validate_records(rows: list[dict]) -> None:
    seen = set()
    known = set(REJECTION_RULES + INVALID_RULES)
    for row in rows:
        key = (row["run_id"], row["structure_id"])
        if key in seen:
            raise ValueError(f"duplicate structure identity: {key}")
        seen.add(key)
        attributes = row["attributes"]
        if set(attributes) - known or len(attributes) != len(set(attributes)):
            raise ValueError("unknown or duplicated rejection rules")
        if row["classification"] != row["geometry"]["classification"] or attributes != row["geometry"]["attributes"]:
            raise ValueError("structure and geometry classifications disagree")
        g = row["geometry"]
        if g["valid"]:
            if not all(isinstance(g[k], (int, float)) and math.isfinite(g[k]) for k in ("D", "E", "width")) or g["width"] <= 0:
                raise ValueError("valid geometry must have finite diagnostics and positive width")
            threshold = row["drift_threshold"]
            if not math.isfinite(threshold) or threshold <= 0:
                raise ValueError("finite positive frozen drift threshold required")
            expected = "uncertain" if attributes else "range" if abs(g["D"]) <= threshold else "uptrend" if g["D"] > 0 else "downtrend"
            if row["classification"] != expected:
                raise ValueError("classification inconsistent with frozen drift and flags")
        elif row["classification"] != "uncertain":
            raise ValueError("invalid geometry cannot have a clear classification")


def counterfactual_removal(rows: list[dict], removed: tuple[str, ...]) -> dict:
    """Boolean blocker removal on unchanged objects, not an alternative replay.

    Invalid geometry is never recovered, even if callers ask to remove its flag.
    No label quality, new event, or economic effect is estimated here.
    """
    removed_set = set(removed)
    baseline = sum(row["classification"] != "uncertain" for row in rows)
    recovered = []
    for row in rows:
        if row["classification"] == "uncertain" and row["geometry"]["valid"] and not (set(row["attributes"]) - removed_set):
            recovered.append(row)
    classes = Counter()
    for row in recovered:
        d = row["geometry"]["D"]
        classes["range" if abs(d) <= row["drift_threshold"] else "uptrend" if d > 0 else "downtrend"] += 1
    return {
        "removed_rules": list(removed),
        "recovered_count": len(recovered),
        "clear_count_if_flags_removed": baseline + len(recovered),
        "clear_fraction_if_flags_removed": ratio(baseline + len(recovered), len(rows)),
        "coverage_gain_percentage_points": ratio(100 * len(recovered), len(rows)),
        "recovered_frozen_D_classes_not_truth": dict(sorted(classes.items())),
    }


def rejection_summary(rows: list[dict], *, pairwise: bool = True) -> dict:
    validate_records(rows)
    n = len(rows)
    flags = [set(row["attributes"]) for row in rows]
    counts = Counter(attribute for attributes in flags for attribute in attributes)
    sole = Counter(next(iter(attributes)) for attributes in flags if len(attributes) == 1)
    patterns = Counter(tuple(sorted(attributes)) for attributes in flags)
    clear = sum(row["classification"] != "uncertain" for row in rows)
    output = {
        "structures": n,
        "clear_count": clear,
        "uncertain_count": n - clear,
        "invalid_geometry_count": sum(not row["geometry"]["valid"] for row in rows),
        "classification_counts": dict(sorted(Counter(row["classification"] for row in rows).items())),
        "clear_fraction": ratio(clear, n),
        "rules": {
            rule: {"triggered": counts[rule], "sole_blocker": sole[rule], "trigger_fraction": ratio(counts[rule], n)}
            for rule in REJECTION_RULES + INVALID_RULES
        },
        "joint_patterns": [
            {"rules": list(pattern), "count": count} for pattern, count in sorted(patterns.items(), key=lambda x: (-x[1], x[0]))
        ],
        "rule_count_distribution": dict(sorted(Counter(len(attributes) for attributes in flags).items())),
        "single_rule_removals": {rule: counterfactual_removal(rows, (rule,)) for rule in REJECTION_RULES},
        "group_removals": {name: counterfactual_removal(rows, rules) for name, rules in RULE_GROUPS.items()},
    }
    if pairwise:
        output["pairwise_flags"] = []
        for a, b in combinations(REJECTION_RULES, 2):
            both = sum(a in attributes and b in attributes for attributes in flags)
            output["pairwise_flags"].append(
                {
                    "a": a,
                    "b": b,
                    "both": both,
                    "a_without_b": counts[a] - both,
                    "b_without_a": counts[b] - both,
                    "b_given_a": ratio(both, counts[a]),
                    "a_given_b": ratio(both, counts[b]),
                    "jaccard": ratio(both, counts[a] + counts[b] - both),
                }
            )
    return output


def mechanism_summary(rows: list[dict]) -> dict:
    valid = [row for row in rows if row["geometry"]["valid"]]
    uneven = [row for row in valid if "uneven_phase_drift" in row["attributes"]]
    amplitude = [row for row in valid if "cycle_amplitude_change" in row["attributes"]]
    # Ratios are descriptive bins fixed in this diagnostic, not trading filters.
    duration_bins = []
    for lower, upper in ((1, 1.5), (1.5, 2), (2, 3), (3, 5), (5, math.inf)):
        subset = [row for row in valid if lower <= row["diagnostics"]["cycle_duration_ratio"] < upper]
        flagged = sum("uneven_phase_drift" in row["attributes"] for row in subset)
        duration_bins.append(
            {
                "lower_inclusive": lower,
                "upper_exclusive": upper if math.isfinite(upper) else None,
                "n": len(subset),
                "uneven_count": flagged,
                "uneven_fraction": ratio(flagged, len(subset)),
            }
        )
    return {
        "valid_geometry_n": len(valid),
        "E_reconstruction_absolute_error": distribution([row["diagnostics"]["E_reconstruction_absolute_error"] for row in valid]),
        "duration_ratio_bins_descriptive_only": duration_bins,
        "uneven_rule_n": len(uneven),
        "uneven_without_majority_sign_reversal_n": sum(
            not row["diagnostics"]["opposite_majority_displacement_signs_without_tolerance"] for row in uneven
        ),
        "uneven_while_equal_duration_counterfactual_below_threshold_n": sum(
            row["diagnostics"]["equal_duration_drift_difference_diagnostic_only"] <= row["max_slope_disagreement"] for row in uneven
        ),
        "amplitude_rule_n": len(amplitude),
        "amplitude_rule_while_frozen_drift_removed_ratio_within_threshold_n": sum(
            row["diagnostics"]["frozen_drift_removed_amplitude_ratio_diagnostic_only"] is not None
            and row["diagnostics"]["frozen_drift_removed_amplitude_ratio_diagnostic_only"] <= row["max_width_ratio"]
            for row in amplitude
        ),
        "interpretation": (
            "Correlated development candidates; arithmetic diagnostics and counterfactual flag removal do not measure correctness."
        ),
    }
