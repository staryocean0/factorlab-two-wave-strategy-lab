"""First-pass independent label quality gates frozen by v0.6.48.

This module validates two blinded human/external label sheets and computes only
inter-annotator agreement. It has no access to model predictions or hidden
candidate/control strata.
"""
from __future__ import annotations

import math
import re
from typing import Iterable

import pandas as pd
from sklearn.metrics import cohen_kappa_score

CASE_RE = re.compile(r"^TW-[0-9A-F]{16}$")
PRESENCE = {"yes", "no", "uncertain"}
PARENT_STATE = {"range", "uptrend", "downtrend", "uncertain", "not_applicable"}
CONFIDENCE = {"high", "medium", "low"}
ANCHORS = ("p0", "p1", "p2", "p3", "p4")
REQUIRED_COLUMNS = (
    "case_id",
    "annotator_id",
    "two_complete_same_scale_waves",
    "parent_state",
    *ANCHORS,
    "confidence",
    "notes",
)
EXPECTED_CASES = 240


def _text(value) -> str:
    return "" if pd.isna(value) else str(value).strip()


def validate_label_frame(frame: pd.DataFrame, *, sheet_name: str) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"{sheet_name}: missing columns {missing}")
    if len(frame) != EXPECTED_CASES:
        raise ValueError(f"{sheet_name}: expected {EXPECTED_CASES} rows, got {len(frame)}")

    x = frame.loc[:, REQUIRED_COLUMNS].copy()
    for col in REQUIRED_COLUMNS:
        x[col] = x[col].map(_text)
    if x["case_id"].duplicated().any() or not x["case_id"].map(lambda s: bool(CASE_RE.fullmatch(s))).all():
        raise ValueError(f"{sheet_name}: invalid or duplicate case_id")
    annotators = sorted(set(x["annotator_id"]))
    if len(annotators) != 1 or not annotators[0]:
        raise ValueError(f"{sheet_name}: exactly one nonempty annotator_id required")
    if not x["two_complete_same_scale_waves"].isin(PRESENCE).all():
        raise ValueError(f"{sheet_name}: invalid presence label")
    if not x["parent_state"].isin(PARENT_STATE).all():
        raise ValueError(f"{sheet_name}: invalid parent_state")
    if not x["confidence"].isin(CONFIDENCE).all():
        raise ValueError(f"{sheet_name}: invalid confidence")

    for row in x.to_dict("records"):
        presence = row["two_complete_same_scale_waves"]
        state = row["parent_state"]
        if presence == "no" and state != "not_applicable":
            raise ValueError(f"{sheet_name}: no-presence case must use parent_state=not_applicable")
        if presence == "yes" and state == "not_applicable":
            raise ValueError(f"{sheet_name}: yes-presence case cannot use parent_state=not_applicable")
        anchor_values = [row[a] for a in ANCHORS]
        if any(anchor_values):
            if not all(anchor_values):
                raise ValueError(f"{sheet_name}: anchors must be all blank or all five populated")
            try:
                anchors = [int(v) for v in anchor_values]
            except ValueError as exc:
                raise ValueError(f"{sheet_name}: non-integer anchor") from exc
            if any(v < 0 or v > 95 for v in anchors) or any(b <= a for a, b in zip(anchors, anchors[1:])):
                raise ValueError(f"{sheet_name}: anchors must be strictly increasing integers in 0..95")
            if presence != "yes":
                raise ValueError(f"{sheet_name}: anchors are only allowed when presence=yes")
    return x.sort_values("case_id").reset_index(drop=True)


def _kappa(a: Iterable[str], b: Iterable[str]) -> float | None:
    values_a = list(a)
    values_b = list(b)
    if not values_a:
        return None
    value = float(cohen_kappa_score(values_a, values_b))
    return None if not math.isfinite(value) else value


def compare_first_pass_labels(a: pd.DataFrame, b: pd.DataFrame) -> dict:
    a = validate_label_frame(a, sheet_name="annotator_a")
    b = validate_label_frame(b, sheet_name="annotator_b")
    if a["annotator_id"].iloc[0] == b["annotator_id"].iloc[0]:
        raise ValueError("the two first-pass sheets must have different annotator_id values")
    if a["case_id"].tolist() != b["case_id"].tolist():
        raise ValueError("first-pass sheets must contain the identical 240 case IDs")

    presence_equal = a["two_complete_same_scale_waves"] == b["two_complete_same_scale_waves"]
    presence_exact = float(presence_equal.mean())
    presence_kappa = _kappa(a["two_complete_same_scale_waves"], b["two_complete_same_scale_waves"])

    both_yes = (a["two_complete_same_scale_waves"] == "yes") & (b["two_complete_same_scale_waves"] == "yes")
    state_n = int(both_yes.sum())
    if state_n:
        state_equal = a.loc[both_yes, "parent_state"] == b.loc[both_yes, "parent_state"]
        state_exact = float(state_equal.mean())
        state_kappa = _kappa(a.loc[both_yes, "parent_state"], b.loc[both_yes, "parent_state"])
    else:
        state_exact = 0.0
        state_kappa = None

    disagreement = []
    for idx in range(len(a)):
        presence_disagree = not bool(presence_equal.iloc[idx])
        state_disagree = bool(both_yes.iloc[idx]) and a["parent_state"].iloc[idx] != b["parent_state"].iloc[idx]
        if presence_disagree or state_disagree:
            disagreement.append(a["case_id"].iloc[idx])

    gates = {
        "presence_exact_agreement_at_least_85pct": presence_exact >= 0.85,
        "presence_kappa_at_least_0_70_when_defined": presence_kappa is None or presence_kappa >= 0.70,
        "both_yes_parent_state_exact_at_least_80pct": state_n > 0 and state_exact >= 0.80,
        "parent_state_kappa_at_least_0_70_when_defined": state_kappa is None or state_kappa >= 0.70,
    }
    return {
        "schema": "two_wave_independent_reference_first_pass_quality@0.6.48",
        "annotator_a": a["annotator_id"].iloc[0],
        "annotator_b": b["annotator_id"].iloc[0],
        "cases": len(a),
        "presence_exact_agreement": presence_exact,
        "presence_cohen_kappa": presence_kappa,
        "both_yes_cases": state_n,
        "both_yes_parent_state_exact_agreement": state_exact,
        "parent_state_cohen_kappa": state_kappa,
        "gates": gates,
        "all_label_quality_gates_pass": all(gates.values()),
        "disagreement_case_ids": disagreement,
        "disagreement_count": len(disagreement),
        "adjudication_required": bool(disagreement),
        "hidden_strata_unblinded": False,
        "model_predictions_unblinded": False,
        "model_scoring_allowed": False,
    }
