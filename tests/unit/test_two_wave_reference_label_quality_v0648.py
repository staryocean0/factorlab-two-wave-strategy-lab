import pandas as pd
import pytest

from factor_lab.visual_structure.two_wave.reference_label_quality_v0648 import (
    REQUIRED_COLUMNS,
    compare_first_pass_labels,
    validate_label_frame,
)


def _sheet(annotator: str, *, disagree_every: int | None = None):
    rows = []
    for i in range(240):
        presence = "yes" if i % 3 else "no"
        state = "uptrend" if i % 2 else "range"
        if presence == "no":
            state = "not_applicable"
        if disagree_every and i % disagree_every == 0:
            presence = "uncertain"
            state = "uncertain"
        rows.append({
            "case_id": f"TW-{i:016X}",
            "annotator_id": annotator,
            "two_complete_same_scale_waves": presence,
            "parent_state": state,
            "p0": "" if presence != "yes" else "10",
            "p1": "" if presence != "yes" else "25",
            "p2": "" if presence != "yes" else "42",
            "p3": "" if presence != "yes" else "61",
            "p4": "" if presence != "yes" else "80",
            "confidence": "high",
            "notes": "",
        })
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


def test_identical_independent_sheets_pass_quality_gates_and_keep_scoring_blocked():
    a = _sheet("annotator_A")
    b = _sheet("annotator_B")
    result = compare_first_pass_labels(a, b)
    assert result["all_label_quality_gates_pass"] is True
    assert result["disagreement_count"] == 0
    assert result["model_scoring_allowed"] is False
    assert result["hidden_strata_unblinded"] is False


def test_disagreements_are_reported_without_model_unblinding():
    a = _sheet("annotator_A")
    b = _sheet("annotator_B", disagree_every=20)
    result = compare_first_pass_labels(a, b)
    assert result["disagreement_count"] > 0
    assert result["adjudication_required"] is True
    assert result["model_predictions_unblinded"] is False
    assert result["model_scoring_allowed"] is False


def test_invalid_parent_state_and_partial_anchors_fail_closed():
    x = _sheet("annotator_A")
    x.loc[0, "parent_state"] = "uptrend"  # row 0 has presence=no
    with pytest.raises(ValueError, match="not_applicable"):
        validate_label_frame(x, sheet_name="x")

    y = _sheet("annotator_A")
    yes_idx = int(y.index[y["two_complete_same_scale_waves"] == "yes"][0])
    y.loc[yes_idx, "p3"] = ""
    with pytest.raises(ValueError, match="all blank or all five"):
        validate_label_frame(y, sheet_name="y")


def test_same_annotator_id_cannot_satisfy_two_independent_passes():
    a = _sheet("same")
    b = _sheet("same")
    with pytest.raises(ValueError, match="different annotator_id"):
        compare_first_pass_labels(a, b)
