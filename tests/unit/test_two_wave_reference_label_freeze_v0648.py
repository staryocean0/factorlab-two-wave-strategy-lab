from __future__ import annotations

import pandas as pd
import pytest

from factor_lab.visual_structure.two_wave.reference_label_freeze_v0648 import (
    ANCHORS,
    adjudication_tables,
    freeze_final_reference,
    validate_adjudicator_frame,
    validate_final_reference_frame,
)
from factor_lab.visual_structure.two_wave.reference_label_scoring_v0648 import (
    score_by_year,
    score_reference_cases,
)


def _sheet(annotator: str) -> pd.DataFrame:
    rows = []
    states = ("range", "uptrend", "downtrend", "uncertain")
    for i in range(240):
        presence = ("yes", "no", "uncertain")[i % 3]
        if presence == "yes":
            state = states[(i // 3) % len(states)]
        elif presence == "no":
            state = "not_applicable"
        else:
            state = "uncertain"
        rows.append({
            "case_id": f"TW-{i:016X}",
            "annotator_id": annotator,
            "two_complete_same_scale_waves": presence,
            "parent_state": state,
            **{a: "" for a in ANCHORS},
            "confidence": "high",
            "notes": "",
        })
    return pd.DataFrame(rows)


def _third(case_id: str, annotator: str = "third-reviewer") -> pd.DataFrame:
    return pd.DataFrame([{
        "case_id": case_id,
        "annotator_id": annotator,
        "two_complete_same_scale_waves": "yes",
        "parent_state": "range",
        **{a: "" for a in ANCHORS},
        "confidence": "high",
        "notes": "independent adjudication",
        "independent_of_first_pass_annotators": "true",
        "blinded_to_model": "true",
        "completed_at": "2026-09-12T12:00:00+00:00",
    }])


def test_all_agreement_freezes_without_third_and_authorizes_scoring():
    a, b = _sheet("A"), _sheet("B")
    final, audit = freeze_final_reference(a, b)
    assert len(final) == 240
    assert audit["unresolved_disagreements"] == 0
    assert audit["first_pass_label_quality_pass"] is True
    assert audit["model_scoring_allowed"] is True
    assert set(final["label_source"]) == {"first_pass_agreement"}
    validate_final_reference_frame(final)


def test_only_protocol_disagreement_enters_third_packet_and_final_freeze():
    a, b = _sheet("A"), _sheet("B")
    case_id = a.loc[0, "case_id"]
    b.loc[0, "two_complete_same_scale_waves"] = "no"
    b.loc[0, "parent_state"] = "not_applicable"
    quality, first_pass, blank = adjudication_tables(a, b)
    assert quality["disagreement_case_ids"] == [case_id]
    assert first_pass["case_id"].tolist() == [case_id]
    assert blank["case_id"].tolist() == [case_id]
    final, audit = freeze_final_reference(a, b, _third(case_id))
    row = final.set_index("case_id").loc[case_id]
    assert row["two_complete_same_scale_waves"] == "yes"
    assert row["parent_state"] == "range"
    assert row["label_source"] == "third_independent_adjudication"
    assert audit["unresolved_disagreements"] == 0
    assert audit["model_scoring_allowed"] is True


def test_third_adjudicator_must_be_distinct_and_attest_blinding():
    a, b = _sheet("A"), _sheet("B")
    case_id = a.loc[0, "case_id"]
    b.loc[0, "two_complete_same_scale_waves"] = "no"
    b.loc[0, "parent_state"] = "not_applicable"
    with pytest.raises(ValueError, match="distinct"):
        validate_adjudicator_frame(
            _third(case_id, annotator="A"),
            expected_case_ids=[case_id],
            forbidden_annotator_ids=["A", "B"],
        )
    third = _third(case_id)
    third.loc[0, "blinded_to_model"] = "false"
    with pytest.raises(ValueError, match="model blinding"):
        freeze_final_reference(a, b, third)


def test_final_uncertain_presence_normalizes_state_and_has_no_anchors():
    a, b = _sheet("A"), _sheet("B")
    case_id = a.loc[2, "case_id"]
    a.loc[2, "parent_state"] = "range"
    b.loc[2, "parent_state"] = "downtrend"
    final, _ = freeze_final_reference(a, b)
    row = final.set_index("case_id").loc[case_id]
    assert row["two_complete_same_scale_waves"] == "uncertain"
    assert row["parent_state"] == "uncertain"
    assert all(row[x] == "" for x in ANCHORS)


def _scoring_records() -> list[dict]:
    records = []
    for year in range(2015, 2021):
        for j in range(20):
            i = (year - 2015) * 20 + j
            ref_state = ("range", "uptrend", "downtrend", "uncertain")[i % 4]
            pred = ref_state
            if i == 0:
                ref_state, pred = "uptrend", "downtrend"
            elif 1 <= i <= 4:
                pred = "uncertain"
            records.append({
                "year": year,
                "stratum": "candidate",
                "reference_presence": "yes",
                "reference_state": ref_state,
                "v0625": pred,
                "D1": "uncertain",
            })
        for j in range(20):
            i = (year - 2015) * 20 + j
            records.append({
                "year": year,
                "stratum": "control",
                "reference_presence": "yes" if i < 20 else "no",
                "reference_state": "range" if i < 20 else "not_applicable",
                "v0625": None,
                "D1": None,
            })
    return records


def test_frozen_scoring_denominators_and_gates():
    result = score_reference_cases(_scoring_records())
    assert result["candidate_reference_confirmed_presence_fraction"] == 1.0
    assert result["human_positive_control_miss_fraction"] == pytest.approx(20 / 120)
    assert result["primary_v0625"]["opposite_trend_conflict_count"] == 1
    assert result["primary_v0625"]["opposite_trend_conflict_rate"] == pytest.approx(1 / 120)
    assert result["primary_v0625"]["parent_state_exact_agreement"] == pytest.approx(115 / 120)
    assert result["all_calibration_support_gates_pass"] is True
    by_year = score_by_year(_scoring_records())
    assert sorted(by_year) == [str(y) for y in range(2015, 2021)]
    assert all(row["descriptive_only"] for row in by_year.values())
