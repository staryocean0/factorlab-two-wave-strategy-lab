"""Constructed fixtures test audit mechanics, never real morphology accuracy."""

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from factor_lab.visual_structure.two_wave.adjudication import (
    decision_template,
    prepare_review_document,
    reconcile_annotations,
    reviewer_template,
)
from factor_lab.visual_structure.two_wave.annotations import validate_annotation_document


def review(name="reviewer_A", **changes):
    result = reviewer_template()
    result.update(
        reviewer=name,
        config_id="product_config_sha",
        timeframe="vendor_5m_offset0",
        scale_id="reversal_log_0.01",
        provenance={
            "source_type": "independent_human",
            "reference_version": "fixture_only_v1",
            "completed_at": "2026-09-05T09:00:00+00:00",
            "blinded_to_algorithm": True,
            "independent_of_other_reviewer": True,
            "future_exposed": False,
            "online_clock": "bar_end",
        },
        annotations=[{
            "annotation_id": f"{name}_1", "kind": "structure", "phase": "low",
            "pivot_indices": [10, 20, 30, 40, 50], "visible_cutoff": 100,
            "label": "range", "reason": "Constructed test fixture, not a market reference", "confidence": 0.8,
        }],
        review_windows=[{"start_index": 45, "end_index": 100, "visible_cutoff": 100, "complete_reviewed": True}],
    )
    result.update(changes)
    return result


def signed(result, action="accept_a"):
    document = decision_template(result)
    for decision in document["decisions"]:
        decision.update(action=action, adjudicator="fixture_adjudicator", decided_at="2026-09-05T10:00:00Z",
                        reason="Explicit synthetic fixture decision exercising the audit workflow")
    return document


def test_templates_never_assert_real_work():
    template = reviewer_template()
    assert template["annotations"] == template["review_windows"] == []
    assert template["provenance"]["source_type"] == ""
    assert template["provenance"]["blinded_to_algorithm"] is None


def test_prepare_existing_replay_export_leaves_truth_assertions_unsigned():
    export = review()
    export.pop("provenance")
    export["annotations"][0].pop("reason")
    export["annotations"][0].pop("confidence")
    export["annotations"][0]["algorithm_visible"] = True
    before = deepcopy(export)
    prepared = prepare_review_document(export)
    assert export == before
    assert prepared["provenance"]["source_type"] == ""
    assert prepared["provenance"]["blinded_to_algorithm"] is None
    assert prepared["annotations"][0]["algorithm_visible"] is True
    assert prepared["annotations"][0]["reason"] == ""
    assert prepared["annotations"][0]["confidence"] is None
    assert len(prepared["source_export_sha256"]) == 64


def test_agreement_is_retained_but_never_automatic_truth():
    a, b = review(), review("reviewer_B")
    before = deepcopy((a, b))
    result = reconcile_annotations(a, b)
    assert (a, b) == before
    assert result["cases"][0]["comparison"] == ["double_review_agreement"]
    assert result["counts"]["unresolved_cases"] == 1
    assert result["counts"]["adjudicated_reference_count"] == 0
    assert result["counts"]["primary_scoring_window_count"] == 0
    assert result["status"] == "morphology_replication_not_yet_accepted"


def test_explicit_decision_exports_valid_reference_and_fifth_point_scope():
    a, b = review(), review("reviewer_B")
    initial = reconcile_annotations(a, b)
    result = reconcile_annotations(a, b, signed(initial))
    doc = validate_annotation_document(result["adjudicated_reference"])
    assert len(doc["annotations"]) == len(doc["review_windows"]) == 1
    assert doc["annotations"][0]["adjudication"]["source_document_sha256"] == initial["source_document_sha256"]
    assert doc["review_windows"][0]["start_index"] == 45
    assert doc["review_windows"][0]["double_reviewers"] == ["reviewer_A", "reviewer_B"]
    assert result["counts"]["unresolved_cases"] == 0
    assert result["status"] == "morphology_replication_not_yet_accepted"


def test_frozen_tolerance_every_extremum_and_class_blind_matching():
    a, b = review(), review("reviewer_B")
    b["annotations"][0].update(pivot_indices=[12, 22, 32, 42, 52], label="uptrend")
    result = reconcile_annotations(a, b)
    assert len(result["cases"]) == 1
    assert result["cases"][0]["comparison"] == ["classification_disagreement", "geometry_variation_within_frozen_tolerance"]
    b["annotations"][0]["pivot_indices"][2] = 33
    result = reconcile_annotations(a, b)
    assert len(result["cases"]) == 2
    assert {tuple(c["comparison"]) for c in result["cases"]} == {
        ("missing_reviewer_a_object",), ("missing_reviewer_b_object",),
    }


@pytest.mark.parametrize("field,value", [
    ("instrument", "other_index"), ("config_id", "different_config"),
    ("timeframe", "vendor_5m_offset1"), ("scale_id", "reversal_log_0.012"),
    ("reference_mode", "online"),
])
def test_no_cross_product_scale_or_reference_mode_matching(field, value):
    assert len(reconcile_annotations(review(), review("reviewer_B", **{field: value}))["cases"]) == 2


def test_phase_cutoff_and_clock_are_distinct_observations():
    a, b = review(reference_mode="online"), review("reviewer_B", reference_mode="online")
    b["annotations"][0]["phase"] = "high"
    assert len(reconcile_annotations(a, b)["cases"]) == 2
    b["annotations"][0]["phase"] = "low"
    b["annotations"][0]["visible_cutoff"] = 101
    assert len(reconcile_annotations(a, b)["cases"]) == 2
    b["annotations"][0]["visible_cutoff"] = 100
    b["provenance"]["online_clock"] = "information_available_time"
    assert len(reconcile_annotations(a, b)["cases"]) == 2


@pytest.mark.parametrize("change,issue", [
    ({"source_type": "algorithm"}, "source_type_not_independent_human"),
    ({"source_type": "synthetic"}, "source_type_not_independent_human"),
    ({"blinded_to_algorithm": False}, "algorithm_blinding_not_attested"),
    ({"independent_of_other_reviewer": False}, "independent_double_review_not_attested"),
    ({"completed_at": "2026-09-05T09:00:00"}, "missing_timezone_aware_completion_time"),
])
def test_provenance_problems_are_visible_and_cannot_be_signed_away(change, issue):
    a, b = review(), review("reviewer_B")
    a["provenance"].update(change)
    result = reconcile_annotations(a, b)
    assert issue in result["cases"][0]["provenance_issues"]["a"]
    with pytest.raises(ValueError, match="Cannot accept"):
        reconcile_annotations(a, b, signed(result, "accept_a"))


def test_future_exposed_online_record_cannot_be_accepted():
    a, b = review(reference_mode="online"), review("reviewer_B", reference_mode="online")
    a["provenance"]["future_exposed"] = True
    result = reconcile_annotations(a, b)
    assert "online_future_blinding_not_attested" in result["cases"][0]["provenance_issues"]["a"]
    with pytest.raises(ValueError, match="Cannot accept"):
        reconcile_annotations(a, b, signed(result))


def test_malformed_provenance_is_retained_without_crashing_online_matching():
    a, b = review(reference_mode="online"), review("reviewer_B", reference_mode="online")
    a["provenance"] = "invalid"
    result = reconcile_annotations(a, b)
    assert result["counts"]["records_with_provenance_issues"] == 1
    assert result["counts"]["adjudicated_reference_count"] == 0


def test_ambiguous_decision_stays_in_audit_and_blocks_full_window():
    a, b = review(), review("reviewer_B")
    initial = reconcile_annotations(a, b)
    result = reconcile_annotations(a, b, signed(initial, "ambiguous"))
    assert result["cases"][0]["status"] == "ambiguous"
    assert result["counts"]["unresolved_fraction"] == 1
    assert result["adjudicated_reference"]["review_windows"] == []


def test_explicit_rejection_keeps_negative_window_and_does_not_delete_case():
    a, b = review(), review("reviewer_B")
    initial = reconcile_annotations(a, b)
    result = reconcile_annotations(a, b, signed(initial, "reject_both"))
    assert len(result["cases"]) == 1
    assert result["adjudicated_reference"]["annotations"] == []
    assert len(result["adjudicated_reference"]["review_windows"]) == 1


def test_two_empty_human_complete_reviews_can_record_zero_objects():
    result = reconcile_annotations(review(annotations=[]), review("reviewer_B", annotations=[]))
    assert result["counts"]["cases"] == 0
    assert result["counts"]["primary_scoring_window_count"] == 1
    assert result["counts"]["unresolved_fraction"] is None


def test_unmatched_or_duplicate_windows_cannot_create_false_precision_scope():
    a, b = review(annotations=[]), review("reviewer_B", annotations=[])
    b["review_windows"][0]["start_index"] = 46
    assert reconcile_annotations(a, b)["counts"]["primary_scoring_window_count"] == 0
    b["review_windows"][0]["start_index"] = 45
    b["review_windows"].append(deepcopy(b["review_windows"][0]))
    assert reconcile_annotations(a, b)["counts"]["primary_scoring_window_count"] == 0


def test_all_kind_window_does_not_hide_pending_structure():
    a, b = review(), review("reviewer_B")
    for doc in (a, b):
        doc["review_windows"][0]["kind"] = "all"
    result = reconcile_annotations(a, b)
    assert result["counts"]["primary_scoring_window_count"] == 0
    assert result["review_window_audit"][0]["unresolved_case_ids"]


@pytest.mark.parametrize("complete", [False, 1])
def test_conflicting_or_nonboolean_complete_window_flags_block_scoring(complete):
    a, b = review(annotations=[]), review("reviewer_B", annotations=[])
    a["review_windows"][0].update(complete_reviewed=complete, fully_reviewed=True)
    result = reconcile_annotations(a, b)
    assert result["counts"]["primary_scoring_window_count"] == 0
    assert result["review_window_audit"][0]["exclusion_reasons"]


@pytest.mark.parametrize("field", ["algorithm_visible", "independent_reference", "ambiguous"])
def test_string_boolean_flags_do_not_get_normalized_into_independent_truth(field):
    a, b = review(), review("reviewer_B")
    a["annotations"][0][field] = "false"
    with pytest.raises(ValueError, match="must be boolean"):
        reconcile_annotations(a, b)


def test_clean_selected_reference_does_not_certify_contaminated_double_review_window():
    a, b = review(), review("reviewer_B")
    a["annotations"][0]["algorithm_visible"] = True
    initial = reconcile_annotations(a, b)
    result = reconcile_annotations(a, b, signed(initial, "accept_b"))
    assert result["counts"]["adjudicated_reference_count"] == 1
    assert result["counts"]["primary_scoring_window_count"] == 0


def test_duplicate_source_geometry_is_not_extra_reference_truth():
    a, b = review(), review("reviewer_B")
    extra = deepcopy(a["annotations"][0])
    extra["annotation_id"] = "duplicate_screenshot"
    a["annotations"].append(extra)
    result = reconcile_annotations(a, b)
    assert result["counts"]["records_with_provenance_issues"] == 2
    with pytest.raises(ValueError, match="Cannot accept"):
        reconcile_annotations(a, b, signed(result))


def test_cross_source_choices_cannot_duplicate_final_geometry():
    a, b = review(), review("reviewer_B")
    for doc, offset in ((a, 2), (b, -2)):
        extra = deepcopy(doc["annotations"][0])
        extra["annotation_id"] += "_other"
        extra["pivot_indices"] = [point + offset for point in extra["pivot_indices"]]
        doc["annotations"].append(extra)
    initial = reconcile_annotations(a, b)
    decisions = signed(initial)
    by_id = {case["case_id"]: case for case in initial["cases"]}
    for decision in decisions["decisions"]:
        case = by_id[decision["case_id"]]
        decision["action"] = "accept_a" if case["reviewer_a_record"]["pivot_indices"][0] == 10 else "accept_b"
    with pytest.raises(ValueError, match="duplicate reference geometry"):
        reconcile_annotations(a, b, decisions)


@pytest.mark.parametrize("field,value", [("adjudicator", "model"), ("decided_at", ""), ("reason", "")])
def test_decisions_require_explicit_human_signature(field, value):
    a, b = review(), review("reviewer_B")
    initial = reconcile_annotations(a, b)
    decisions = signed(initial)
    decisions["decisions"][0][field] = value
    with pytest.raises(ValueError):
        reconcile_annotations(a, b, decisions)


def test_decisions_bound_to_exact_sources_and_timestamp_order():
    a, b = review(), review("reviewer_B")
    initial = reconcile_annotations(a, b)
    decisions = signed(initial)
    a["annotations"][0]["label"] = "uptrend"
    with pytest.raises(ValueError, match="source_document_sha256"):
        reconcile_annotations(a, b, decisions)
    a["annotations"][0]["label"] = "range"
    decisions["decisions"][0]["decided_at"] = "2026-09-05T08:00:00Z"
    with pytest.raises(ValueError, match="precede"):
        reconcile_annotations(a, b, decisions)


def test_same_reviewer_cannot_be_double_review():
    with pytest.raises(ValueError, match="two different"):
        reconcile_annotations(review(), review("Reviewer_A"))


def test_cli_empty_templates_and_no_overwrite(tmp_path):
    root = Path(__file__).resolve().parents[2]
    command = [sys.executable, str(root / "scripts/reconcile_two_wave_annotations.py"), "--empty-templates", "--output", str(tmp_path)]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)["human_reference_count"] == 0
    assert json.loads((tmp_path / "reviewer_a_empty.json").read_text())["annotations"] == []
    assert subprocess.run(command, capture_output=True).returncode != 0


def test_cli_reconciliation_end_to_end(tmp_path):
    root = Path(__file__).resolve().parents[2]
    for name, doc in (("a", review()), ("b", review("reviewer_B"))):
        (tmp_path / f"{name}.json").write_text(json.dumps(doc))
    output = tmp_path / "audit"
    command = [sys.executable, str(root / "scripts/reconcile_two_wave_annotations.py"),
               "--reviewer-a", str(tmp_path / "a.json"), "--reviewer-b", str(tmp_path / "b.json"), "--output", str(output)]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)["unresolved_cases"] == 1
    assert json.loads((output / "adjudicated_reference.json").read_text())["annotations"] == []
    decision_path = tmp_path / "signed_fixture_decisions.json"
    decision_path.write_text(json.dumps(signed(json.loads((output / "reconciliation.json").read_text()))))
    command[-1] = str(tmp_path / "resolved")
    result = subprocess.run(command + ["--decisions", str(decision_path)], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)["adjudicated_reference_count"] == 1
