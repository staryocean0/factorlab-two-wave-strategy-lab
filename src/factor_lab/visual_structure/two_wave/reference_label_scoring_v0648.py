"""Pre-frozen v0.6.48 aggregate scoring metrics.

The primary gated model is v0.6.25. D1 is descriptive only. This module works
on already-unblinded case records only after final reference labels are frozen.
"""
from __future__ import annotations

from collections import Counter

LABELS = ("range", "uptrend", "downtrend", "uncertain")


def _candidate_model_metrics(rows: list[dict], model_key: str) -> dict:
    positives = [r for r in rows if r["reference_presence"] == "yes"]
    n_pos = len(positives)
    exact = sum(r[model_key] == r["reference_state"] for r in positives)
    opposite = sum({r[model_key], r["reference_state"]} == {"uptrend", "downtrend"} for r in positives)
    confusion = {ref: {pred: 0 for pred in LABELS} for ref in LABELS}
    for row in positives:
        ref = row["reference_state"]
        pred = row[model_key]
        if ref not in LABELS or pred not in LABELS:
            raise ValueError("reference/model state outside frozen four-state vocabulary")
        confusion[ref][pred] += 1
    return {
        "reference_confirmed_cases": n_pos,
        "parent_state_exact_count": exact,
        "parent_state_exact_agreement": exact / n_pos if n_pos else 0.0,
        "opposite_trend_conflict_count": opposite,
        "opposite_trend_conflict_rate": opposite / n_pos if n_pos else 0.0,
        "uncertain_count_all_candidates": sum(r[model_key] == "uncertain" for r in rows),
        "uncertain_rate_all_candidates": sum(r[model_key] == "uncertain" for r in rows) / len(rows) if rows else 0.0,
        "uncertain_count_reference_confirmed": sum(r[model_key] == "uncertain" for r in positives),
        "uncertain_rate_reference_confirmed": (
            sum(r[model_key] == "uncertain" for r in positives) / n_pos if n_pos else 0.0
        ),
        "confusion_matrix_reference_rows_model_columns": confusion,
    }


def score_reference_cases(records: list[dict]) -> dict:
    candidate = [r for r in records if r["stratum"] == "candidate"]
    control = [r for r in records if r["stratum"] == "control"]
    if len(candidate) != 120 or len(control) != 120:
        raise ValueError("frozen v0.6.48 scoring requires exactly 120 candidate + 120 control cases")
    candidate_positive = sum(r["reference_presence"] == "yes" for r in candidate)
    control_positive = sum(r["reference_presence"] == "yes" for r in control)
    v0625 = _candidate_model_metrics(candidate, "v0625")
    d1 = _candidate_model_metrics(candidate, "D1")
    presence_fraction = candidate_positive / len(candidate)
    control_miss = control_positive / len(control)
    gates = {
        "candidate_reference_confirmed_presence_at_least_80pct": presence_fraction >= 0.80,
        "v0625_parent_state_exact_at_least_85pct": v0625["parent_state_exact_agreement"] >= 0.85,
        "v0625_opposite_trend_conflict_at_most_2pct": v0625["opposite_trend_conflict_rate"] <= 0.02,
        "human_positive_control_miss_at_most_20pct": control_miss <= 0.20,
    }
    return {
        "candidate_cases": len(candidate),
        "control_cases": len(control),
        "candidate_reference_presence_counts": dict(Counter(r["reference_presence"] for r in candidate)),
        "control_reference_presence_counts": dict(Counter(r["reference_presence"] for r in control)),
        "candidate_reference_confirmed_presence_fraction": presence_fraction,
        "human_positive_control_miss_fraction": control_miss,
        "primary_v0625": v0625,
        "descriptive_D1": d1,
        "gates": gates,
        "all_calibration_support_gates_pass": all(gates.values()),
    }


def score_by_year(records: list[dict]) -> dict:
    out = {}
    for year in range(2015, 2021):
        subset = [r for r in records if int(r["year"]) == year]
        candidate = [r for r in subset if r["stratum"] == "candidate"]
        control = [r for r in subset if r["stratum"] == "control"]
        if len(candidate) != 20 or len(control) != 20:
            raise ValueError(f"year {year}: expected 20 candidate + 20 control cases")
        pos = sum(r["reference_presence"] == "yes" for r in candidate)
        ctrl = sum(r["reference_presence"] == "yes" for r in control)
        out[str(year)] = {
            "candidate_cases": 20,
            "control_cases": 20,
            "candidate_reference_confirmed_presence_fraction": pos / 20,
            "human_positive_control_miss_fraction": ctrl / 20,
            "primary_v0625": _candidate_model_metrics(candidate, "v0625"),
            "descriptive_D1": _candidate_model_metrics(candidate, "D1"),
            "descriptive_only": True,
        }
    return out
