"""Model-blind adjudication and final reference freeze primitives for v0.6.48.

No hidden stratum, model prediction, harmless offset, future outcome or PnL is
accepted by this module. Two first-pass sheets are frozen/compared first; only
protocol-defined disagreements may be supplied to a distinct third annotator.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

import pandas as pd

from .reference_label_quality_v0648 import (
    ANCHORS,
    CASE_RE,
    CONFIDENCE,
    EXPECTED_CASES,
    PARENT_STATE,
    PRESENCE,
    REQUIRED_COLUMNS,
    compare_first_pass_labels,
    validate_label_frame,
)

ADJUDICATOR_ATTESTATIONS = (
    "independent_of_first_pass_annotators",
    "blinded_to_model",
    "completed_at",
)
FINAL_COLUMNS = (
    "case_id",
    "two_complete_same_scale_waves",
    "parent_state",
    *ANCHORS,
    "label_source",
)


def _text(value) -> str:
    return "" if pd.isna(value) else str(value).strip()


def _true(value) -> bool:
    if isinstance(value, bool):
        return value
    return _text(value).lower() == "true"


def _timezone_aware(value: str) -> bool:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is not None
    except (TypeError, ValueError):
        return False


def _validate_semantics(row: dict[str, str], *, sheet_name: str) -> None:
    presence = row["two_complete_same_scale_waves"]
    state = row["parent_state"]
    if presence not in PRESENCE or state not in PARENT_STATE or row["confidence"] not in CONFIDENCE:
        raise ValueError(f"{sheet_name}: invalid label enum")
    if presence == "no" and state != "not_applicable":
        raise ValueError(f"{sheet_name}: no-presence requires parent_state=not_applicable")
    if presence == "yes" and state == "not_applicable":
        raise ValueError(f"{sheet_name}: yes-presence cannot use parent_state=not_applicable")
    values = [row[a] for a in ANCHORS]
    if any(values):
        if not all(values):
            raise ValueError(f"{sheet_name}: anchors must be all blank or all five populated")
        try:
            anchors = [int(v) for v in values]
        except ValueError as exc:
            raise ValueError(f"{sheet_name}: non-integer anchor") from exc
        if any(v < 0 or v > 95 for v in anchors) or any(b <= a for a, b in zip(anchors, anchors[1:])):
            raise ValueError(f"{sheet_name}: anchors must be strictly increasing integers in 0..95")
        if presence != "yes":
            raise ValueError(f"{sheet_name}: anchors only allowed when presence=yes")


def first_pass_context(a: pd.DataFrame, b: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    quality = compare_first_pass_labels(a, b)
    va = validate_label_frame(a, sheet_name="annotator_a")
    vb = validate_label_frame(b, sheet_name="annotator_b")
    return quality, va, vb


def adjudication_tables(a: pd.DataFrame, b: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """Return frozen first-pass comparison rows and a blank third-review sheet."""
    quality, va, vb = first_pass_context(a, b)
    ids = quality["disagreement_case_ids"]
    by_a = va.set_index("case_id")
    by_b = vb.set_index("case_id")
    first_rows = []
    blank_rows = []
    for case_id in ids:
        ra, rb = by_a.loc[case_id], by_b.loc[case_id]
        row = {"case_id": case_id}
        for prefix, source in (("a", ra), ("b", rb)):
            row[f"{prefix}_annotator_id"] = source["annotator_id"]
            row[f"{prefix}_two_complete_same_scale_waves"] = source["two_complete_same_scale_waves"]
            row[f"{prefix}_parent_state"] = source["parent_state"]
            for anchor in ANCHORS:
                row[f"{prefix}_{anchor}"] = source[anchor]
            row[f"{prefix}_confidence"] = source["confidence"]
            row[f"{prefix}_notes"] = source["notes"]
        first_rows.append(row)
        blank_rows.append({
            "case_id": case_id,
            "annotator_id": "",
            "two_complete_same_scale_waves": "",
            "parent_state": "",
            **{anchor: "" for anchor in ANCHORS},
            "confidence": "",
            "notes": "",
            "independent_of_first_pass_annotators": "",
            "blinded_to_model": "",
            "completed_at": "",
        })
    return quality, pd.DataFrame(first_rows), pd.DataFrame(blank_rows)


def validate_adjudicator_frame(
    frame: pd.DataFrame,
    *,
    expected_case_ids: Iterable[str],
    forbidden_annotator_ids: Iterable[str],
) -> pd.DataFrame:
    expected = sorted(set(str(x) for x in expected_case_ids))
    required = (*REQUIRED_COLUMNS, *ADJUDICATOR_ATTESTATIONS)
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError(f"adjudicator: missing columns {missing}")
    if len(frame) != len(expected):
        raise ValueError(f"adjudicator: expected {len(expected)} rows, got {len(frame)}")
    x = frame.loc[:, required].copy()
    for col in required:
        x[col] = x[col].map(_text)
    if x["case_id"].duplicated().any() or not x["case_id"].map(lambda s: bool(CASE_RE.fullmatch(s))).all():
        raise ValueError("adjudicator: invalid or duplicate case_id")
    if sorted(x["case_id"].tolist()) != expected:
        raise ValueError("adjudicator: sheet must contain exactly the frozen disagreement case IDs")
    annotators = sorted(set(x["annotator_id"]))
    if len(annotators) != 1 or not annotators[0]:
        raise ValueError("adjudicator: exactly one nonempty annotator_id required")
    if annotators[0] in set(forbidden_annotator_ids):
        raise ValueError("adjudicator must be distinct from both first-pass annotators")
    if not x["independent_of_first_pass_annotators"].map(_true).all():
        raise ValueError("adjudicator must attest independence from both first-pass annotators")
    if not x["blinded_to_model"].map(_true).all():
        raise ValueError("adjudicator must attest model blinding")
    if not x["completed_at"].map(_timezone_aware).all():
        raise ValueError("adjudicator completed_at must be timezone-aware ISO-8601")
    for row in x.to_dict("records"):
        _validate_semantics(row, sheet_name="adjudicator")
    return x.sort_values("case_id").reset_index(drop=True)


def _normalized_reference_label(row: pd.Series) -> tuple[str, str, list[str]]:
    presence = str(row["two_complete_same_scale_waves"])
    if presence == "no":
        return presence, "not_applicable", [""] * len(ANCHORS)
    if presence == "uncertain":
        return presence, "uncertain", [""] * len(ANCHORS)
    return presence, str(row["parent_state"]), [str(row[a]) for a in ANCHORS]


def freeze_final_reference(
    a: pd.DataFrame,
    b: pd.DataFrame,
    adjudicator: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Freeze the final semantic labels without accessing any model information."""
    quality, va, vb = first_pass_context(a, b)
    disagreement_ids = sorted(quality["disagreement_case_ids"])
    a_id, b_id = quality["annotator_a"], quality["annotator_b"]
    third = None
    if disagreement_ids:
        if adjudicator is None:
            raise ValueError("third independent adjudication is required for every disagreement case")
        third = validate_adjudicator_frame(
            adjudicator,
            expected_case_ids=disagreement_ids,
            forbidden_annotator_ids=(a_id, b_id),
        ).set_index("case_id")
    elif adjudicator is not None and len(adjudicator):
        raise ValueError("no adjudicator rows are allowed when first-pass disagreement count is zero")

    by_a = va.set_index("case_id")
    by_b = vb.set_index("case_id")
    disagreements = set(disagreement_ids)
    rows = []
    for case_id in va["case_id"]:
        if case_id in disagreements:
            assert third is not None
            presence, state, anchors = _normalized_reference_label(third.loc[case_id])
            source = "third_independent_adjudication"
        else:
            ra, rb = by_a.loc[case_id], by_b.loc[case_id]
            if ra["two_complete_same_scale_waves"] != rb["two_complete_same_scale_waves"]:
                raise AssertionError("untracked first-pass presence disagreement")
            if ra["two_complete_same_scale_waves"] == "yes" and ra["parent_state"] != rb["parent_state"]:
                raise AssertionError("untracked first-pass state disagreement")
            presence = str(ra["two_complete_same_scale_waves"])
            if presence == "yes":
                state = str(ra["parent_state"])
                aa = [str(ra[x]) for x in ANCHORS]
                bb = [str(rb[x]) for x in ANCHORS]
                anchors = aa if aa == bb and all(aa) else [""] * len(ANCHORS)
            elif presence == "no":
                state, anchors = "not_applicable", [""] * len(ANCHORS)
            else:
                state, anchors = "uncertain", [""] * len(ANCHORS)
            source = "first_pass_agreement"
        rows.append({
            "case_id": case_id,
            "two_complete_same_scale_waves": presence,
            "parent_state": state,
            **dict(zip(ANCHORS, anchors)),
            "label_source": source,
        })

    final = pd.DataFrame(rows, columns=FINAL_COLUMNS).sort_values("case_id").reset_index(drop=True)
    if len(final) != EXPECTED_CASES or final["case_id"].duplicated().any():
        raise AssertionError("final reference set must contain exactly 240 unique cases")
    audit = {
        "schema": "two_wave_independent_reference_final_freeze@0.6.48",
        "first_pass_quality": quality,
        "first_pass_label_quality_pass": bool(quality["all_label_quality_gates_pass"]),
        "required_adjudication_cases": len(disagreement_ids),
        "completed_adjudication_cases": len(disagreement_ids),
        "unresolved_disagreements": 0,
        "final_reference_cases": len(final),
        "hidden_strata_unblinded": False,
        "model_predictions_unblinded": False,
        "model_scoring_allowed": bool(quality["all_label_quality_gates_pass"]),
    }
    return final, audit


def validate_final_reference_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in FINAL_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"final_reference: missing columns {missing}")
    if len(frame) != EXPECTED_CASES:
        raise ValueError(f"final_reference: expected {EXPECTED_CASES} rows, got {len(frame)}")
    x = frame.loc[:, FINAL_COLUMNS].copy()
    for col in FINAL_COLUMNS:
        x[col] = x[col].map(_text)
    if x["case_id"].duplicated().any() or not x["case_id"].map(lambda s: bool(CASE_RE.fullmatch(s))).all():
        raise ValueError("final_reference: invalid or duplicate case_id")
    if not x["two_complete_same_scale_waves"].isin(PRESENCE).all():
        raise ValueError("final_reference: invalid presence label")
    if not x["parent_state"].isin(PARENT_STATE).all():
        raise ValueError("final_reference: invalid parent_state")
    if not x["label_source"].isin({"first_pass_agreement", "third_independent_adjudication"}).all():
        raise ValueError("final_reference: invalid label_source")
    for row in x.to_dict("records"):
        presence, state = row["two_complete_same_scale_waves"], row["parent_state"]
        if presence == "no" and state != "not_applicable":
            raise ValueError("final_reference: no-presence requires not_applicable")
        if presence == "uncertain" and state != "uncertain":
            raise ValueError("final_reference: uncertain presence is normalized to uncertain state")
        if presence == "yes" and state == "not_applicable":
            raise ValueError("final_reference: yes-presence cannot use not_applicable")
    return x.sort_values("case_id").reset_index(drop=True)
