from factor_lab.visual_structure.two_wave.scale_invariant_predecessor_publication_v065 import (
    evidence_order_key,
    publish_first_valid_candidate,
)


def member(eid, confirm, level, valid=True, raw=None, reason=None):
    return {
        "event_id": eid,
        "birth_confirmation_bar": confirm,
        "birth_level": level,
        "valid": valid,
        "reason": reason,
        "raw_occurrence_bars": raw,
        "predecessor_occurrence_bar": 5 if valid else None,
        "predecessor_confirmation_bar": 6 if valid else None,
    }


def run(rows):
    return publish_first_valid_candidate("low", [10, 20, 30, 40, 50], rows)


def test_first_valid_member_publishes_immediately():
    out = run([member("a", 60, 2, True, [11, 21, 31, 41, 51])])
    assert out["status"] == "published_single_identity"
    assert out["publication_event"]["publishing_member_event_id"] == "a"


def test_invalid_first_then_second_valid_publishes():
    out = run([
        member("a", 55, 1, False, None, "x"),
        member("b", 60, 2, True, [11, 21, 31, 41, 51]),
    ])
    assert out["publication_event"]["publishing_member_event_id"] == "b"
    assert out["publication_event"]["prior_invalid_evidence_count"] == 1
    assert out["evidence_events"][0]["disposition"] == "invalid_before_publication"


def test_all_invalid_means_no_publication():
    out = run([
        member("a", 55, 1, False, None, "x"),
        member("b", 60, 2, False, None, "y"),
    ])
    assert out["status"] == "no_valid_published_projection"
    assert out["publication_event"] is None


def test_later_same_identity_is_append_only():
    raw = [11, 21, 31, 41, 51]
    out = run([member("a", 60, 2, True, raw), member("b", 70, 3, True, raw)])
    assert out["publication_event"]["published_raw_occurrence_bars"] == raw
    assert out["evidence_events"][1]["disposition"] == "later_valid_same_identity"
    assert out["suppressed_would_be_rewrite_count"] == 0


def test_later_different_identity_is_suppressed_not_rewritten():
    first = [11, 21, 31, 41, 51]
    later = [12, 21, 31, 41, 51]
    out = run([member("a", 60, 2, True, first), member("b", 70, 3, True, later)])
    assert out["publication_event"]["published_raw_occurrence_bars"] == first
    assert out["evidence_events"][1]["disposition"] == "later_valid_would_rewrite_suppressed"
    assert out["suppressed_would_be_rewrite_count"] == 1


def test_equal_confirmation_orders_by_level_then_event_id():
    rows = [
        member("z", 60, 3, True, [13, 21, 31, 41, 51]),
        member("b", 60, 2, True, [12, 21, 31, 41, 51]),
        member("a", 60, 2, True, [11, 21, 31, 41, 51]),
    ]
    assert [r["event_id"] for r in sorted(rows, key=evidence_order_key)] == ["a", "b", "z"]
    out = run(rows)
    assert out["publication_event"]["publishing_member_event_id"] == "a"


def test_prefix_through_publisher_equals_full_publication_event():
    rows = [
        member("a", 55, 1, False, None, "x"),
        member("b", 60, 2, True, [11, 21, 31, 41, 51]),
        member("c", 70, 3, True, [12, 21, 31, 41, 51]),
    ]
    prefix = run(rows[:2])
    full = run(rows)
    assert prefix["publication_event"] == full["publication_event"]


def test_future_evidence_append_cannot_change_publication_identity():
    base = run([member("a", 60, 2, True, [11, 21, 31, 41, 51])])
    full = run([
        member("a", 60, 2, True, [11, 21, 31, 41, 51]),
        member("future", 1000, 9, True, [19, 29, 39, 49, 59]),
    ])
    assert base["publication_event"] == full["publication_event"]


def test_api_has_no_cross_view_similarity_input():
    out = publish_first_valid_candidate(
        "low",
        [10, 20, 30, 40, 50],
        [member("a", 60, 2, True, [11, 21, 31, 41, 51])],
    )
    assert out["publication_event"]["publishing_member_event_id"] == "a"
