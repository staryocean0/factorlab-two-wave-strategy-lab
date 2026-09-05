"""Reference-label boundaries and matching tests, without generated truth."""

import base64
import gzip
import json
import re
from copy import deepcopy

import pytest

from factor_lab.visual_structure.two_wave.annotations import (
    SCHEMA_VERSION,
    annotation_template,
    evaluate_annotations,
    maximum_matching,
    validate_annotation_document,
)
from factor_lab.visual_structure.two_wave.replay import write_replay, write_replay_bundle


def reference(points=None, **changes):
    result = {
        "annotation_id": "human1",
        "kind": "structure",
        "reviewer": "independent_reviewer_A",
        "reference_mode": "offline",
        "config_id": "cfg",
        "timeframe": "5m",
        "scale_id": "scale",
        "phase": "low",
        "pivot_indices": points or [10, 20, 30, 40, 50],
        "label": "range",
        "visible_cutoff": 100,
    }
    result.update(changes)
    return result


def document(refs=None, windows=True):
    result = {
        "schema_version": SCHEMA_VERSION,
        "reviewer": "independent_reviewer_A",
        "reference_mode": "offline",
        "config_id": "cfg",
        "timeframe": "5m",
        "scale_id": "scale",
        "annotations": refs if refs is not None else [reference()],
        "review_windows": [],
    }
    if windows:
        result["review_windows"] = [{"start_index": 0, "end_index": 100, "visible_cutoff": 100, "fully_reviewed": True}]
    return result


def export_fixture():
    return {
        "config": {"timeframe": "5m"},
        "config_hash": "cfg",
        "scale_id": "scale",
        "pivots": [{"pivot_id": "p" + str(i), "occurrence_bar": p} for i, p in enumerate([10, 20, 30, 40, 50])],
        "structures": [
            {
                "structure_id": "s",
                "phase": "low",
                "pivot_ids": ["p" + str(i) for i in range(5)],
                "confirmation_bar": 55,
                "classification": "uptrend",
            }
        ],
        "cycles": [{"cycle_id": "c", "phase": "low", "pivot_ids": ["p0", "p1", "p2"], "confirmation_bar": 35}],
        "events": [],
    }


def prediction(points, identity="p", **changes):
    r = reference(points)
    r.update(prediction_id=identity, confirmation_bar=60)
    r.update(changes)
    return r


def test_no_reference_never_claims_accuracy_or_acceptance():
    result = evaluate_annotations(export_fixture())
    assert result["status"] == "morphology_replication_not_yet_accepted"
    assert all(result[k] is None for k in ("accuracy", "precision", "recall", "macro_f1", "classification_coverage"))
    assert result["historical_point_in_time_status"] == "historical_PIT_not_verified"
    assert annotation_template(export_fixture())["annotations"] == []


@pytest.mark.parametrize("reviewer", ["", "algorithm", "Algorithm", "engine", "算法"])
def test_explicit_algorithm_or_unattributed_labels_rejected(reviewer):
    with pytest.raises(ValueError, match="human reviewer"):
        validate_annotation_document(document([reference(reviewer=reviewer)]))


def test_cannot_annotate_future_point_or_pair_two_legs_as_two_cycles():
    with pytest.raises(ValueError, match="visible_cutoff"):
        validate_annotation_document(document([reference(visible_cutoff=49)]))
    with pytest.raises(ValueError, match="five extrema"):
        validate_annotation_document(document([reference([10, 20, 30])]))


def test_matching_uses_augmenting_paths_not_greedy():
    # First reference can match either prediction; second can match only p0.
    # Class-blind nearest-first greedily occupies p0, then must be reassigned.
    p0 = prediction([10, 20, 30, 40, 50], "p0")
    p1 = prediction([12, 22, 32, 42, 52], "p1")
    refs = [reference(), reference([8, 18, 28, 38, 48], annotation_id="human2")]
    result = maximum_matching([p0, p1], refs, tolerance_bars=2)
    assert len(result["pairs"]) == 2
    assert {p["annotation_id"]: p["prediction_id"] for p in result["pairs"]} == {"human1": "p1", "human2": "p0"}


def test_matching_minimizes_global_distance_at_maximum_cardinality():
    preds = [prediction([10, 20, 30, 40, 50], "p0"), prediction([12, 22, 32, 42, 52], "p1")]
    refs = [reference([11, 21, 31, 41, 51]), reference(annotation_id="human2")]
    result = maximum_matching(preds, refs, tolerance_bars=2)
    assert len(result["pairs"]) == 2
    assert result["total_absolute_extremum_error_bars"] == 5
    assert {p["annotation_id"]: p["prediction_id"] for p in result["pairs"]} == {"human1": "p1", "human2": "p0"}


@pytest.mark.parametrize("changes", [{"phase": "high"}, {"config_id": "different"}, {"timeframe": "15m"}, {"scale_id": "other"}])
def test_matching_respects_identity_phase_and_timeframe(changes):
    assert maximum_matching([prediction([10, 20, 30, 40, 50], **changes)], [reference()])["pairs"] == []


def test_all_five_extrema_must_match():
    assert maximum_matching([prediction([10, 20, 33, 40, 50])], [reference()])["pairs"] == []


def test_online_match_cannot_use_future_confirmation():
    ref = reference(visible_cutoff=54, reference_mode="online")
    pred = prediction([10, 20, 30, 40, 50], confirmation_bar=55)
    assert not maximum_matching([pred], [ref], online=True)["pairs"]
    assert len(maximum_matching([pred], [ref], online=False)["pairs"]) == 1


def test_algorithm_visibility_excludes_reference():
    result = evaluate_annotations(export_fixture(), document([reference(algorithm_visible=True)]))
    assert result["reference_count"] == 0
    assert result["excluded_nonindependent_reference_count"] == 1
    assert result["accuracy"] is None


def test_no_false_precision_from_sparse_annotations():
    result = evaluate_annotations(export_fixture(), document(windows=False))
    structure = result["modes"]["offline"]["structure"]
    assert structure["precision"] is None
    assert structure["recall"] is None
    assert len(structure["sparse_reference_matching"]["pairs"]) == 1


def test_confusion_class_blind_matching_and_incomplete_acceptance():
    result = evaluate_annotations(export_fixture(), document())
    structure = result["modes"]["offline"]["structure"]
    assert structure["precision"] == structure["recall"] == 1
    assert structure["classification_accuracy"] == 0
    assert structure["confusion_matrix"]["range"]["uptrend"] == 1
    assert not result["modes"]["offline"]["accepted"]
    assert result["status"] == "morphology_replication_not_yet_accepted"


def test_complete_three_point_cycle_matching_requires_separate_review_scope():
    doc = document([reference([10, 20, 30], kind="cycle", label=None)])
    doc["review_windows"][0]["kind"] = "cycle"
    result = evaluate_annotations(export_fixture(), doc)
    assert result["modes"]["offline"]["cycle"]["precision"] == 1
    assert result["modes"]["offline"]["cycle"]["recall"] == 1
    assert result["modes"]["offline"]["structure"]["precision"] is None


def test_fifth_extremum_owns_scoring_window_earlier_points_may_be_context():
    doc = document()
    doc["review_windows"][0]["start_index"] = 45
    doc["review_windows"][0].pop("fully_reviewed")
    doc["review_windows"][0]["complete_reviewed"] = True
    result = evaluate_annotations(export_fixture(), doc)
    assert result["modes"]["offline"]["structure"]["matched_count"] == 1


def test_later_online_reference_cannot_become_earlier_window_false_negative():
    doc = document([reference(reference_mode="online", visible_cutoff=100)])
    doc["reference_mode"] = "online"
    doc["review_windows"][0].update(end_index=50, visible_cutoff=50)
    result = evaluate_annotations(export_fixture(), doc)
    assert result["modes"]["online"]["structure"]["reviewed_reference_count"] == 0
    assert result["modes"]["online"]["structure"]["missed_count"] == 0


def test_primary_f1_counts_unmatched_references_and_predictions():
    exp = export_fixture()
    exp["structures"][0]["classification"] = "range"
    exp["structures"].append(
        {"structure_id": "wrong", "phase": "low", "pivot_indices": [60, 65, 70, 75, 80], "classification": "range", "confirmation_bar": 85}
    )
    refs = [reference(), reference([15, 25, 35, 45, 55], annotation_id="missed")]
    result = evaluate_annotations(exp, document(refs))["modes"]["offline"]["structure"]
    assert result["confusion_matrix"]["range"]["not_detected"] == 1
    assert result["unmatched_prediction_class_counts"]["range"] == 1
    assert result["per_class"]["range"]["precision"] == 0.5
    assert result["per_class"]["range"]["recall"] == 0.5
    assert result["macro_f1"] == pytest.approx(1 / 6)
    assert result["matched_only_macro_f1"] == pytest.approx(1 / 3)


def test_reference_validation_does_not_mutate_user_document():
    doc = document()
    before = deepcopy(doc)
    normalized = validate_annotation_document(doc)
    assert doc == before
    assert normalized["review_windows"][0]["timeframe"] == "5m"


def test_replay_is_self_contained_escaped_and_multi_scale(tmp_path):
    bars = [{"timestamp": "2015-01-05T01:35:00+00:00", "open": 100, "high": 101, "low": 99, "close": 100}]
    exp = export_fixture()
    exp["bars"] = bars
    path = write_replay_bundle(
        tmp_path / "replay.html",
        [
            {"name": "</script><script>alert(1)</script>", "bars": bars, "export": exp},
            {"name": "second_scale", "bars": bars, "export": exp},
        ],
    )
    html = path.read_text()
    assert "<script>alert(1)</script>" not in html
    assert 'src="http' not in html
    data = re.search(
        r'<script id="replayData" type="application/octet-stream" data-encoding="base64-gzip">(.*?)</script>', html, re.S
    ).group(1)
    runs = json.loads(gzip.decompress(base64.b64decode(data)))
    assert len(runs) == 2
    assert "bars" not in runs[0]["export"]
    assert 'id="overlay" checked' not in html
    assert "historical_PIT_not_verified" in html
    assert "highestSeenByInstrument" in html
    assert "time<seen)fullExposed=true" in html


def test_replay_refuses_missing_bars(tmp_path):
    with pytest.raises(ValueError, match="at least one"):
        write_replay(tmp_path / "empty.html", [], export_fixture())
