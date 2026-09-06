from __future__ import annotations

import pytest

from factor_lab.visual_structure.two_wave.morphology_identity_v060 import (
    canonicalize_qualified_records,
    causal_publish_qualified_identities,
    mutual_unique_strict_matches,
    strict_anchor_edge,
)


def _record(rid, bars, level=2, selected=False, d1="uptrend", phase="low"):
    return {
        "record_id": rid,
        "scale_qualified": True,
        "phase": phase,
        "five_occurrence_bars": bars,
        "birth_scale_level": level,
        "selected": selected,
        "D1": d1,
        "s0_same_phase_first": 1.0,
        "s1_same_phase_second": 1.2,
        "s2_opposite_envelope": 1.1,
    }


def _event(phase, times):
    return {"phase": phase, "five_occurrence_times": times}


def test_exact_same_anchor_scale_duplicates_collapse_without_losing_scale_evidence():
    out = canonicalize_qualified_records(
        [
            _record("a", [0, 5, 10, 15, 20], 2, True),
            _record("b", [0, 5, 10, 15, 20], 4, False),
        ]
    )
    assert len(out) == 1
    assert out[0]["member_count"] == 2
    assert out[0]["birth_scale_levels"] == [2, 4]
    assert out[0]["selected_member_ids"] == ["a"]


def test_rolling_two_wave_windows_remain_two_financial_events_despite_overlap():
    out = canonicalize_qualified_records(
        [
            _record("w12", [0, 5, 10, 15, 20]),
            _record("w23", [10, 15, 20, 25, 30]),
        ]
    )
    assert len(out) == 2
    assert [x["five_occurrence_bars"] for x in out] == [
        [0, 5, 10, 15, 20],
        [10, 15, 20, 25, 30],
    ]


def test_conflicting_direction_on_identical_financial_identity_is_an_error():
    with pytest.raises(ValueError):
        canonicalize_qualified_records(
            [
                _record("a", [0, 5, 10, 15, 20], d1="uptrend"),
                _record("b", [0, 5, 10, 15, 20], d1="downtrend"),
            ]
        )


def test_strict_anchor_match_is_one_nominal_bar_and_phase_sensitive():
    a = _event("low", [0, 5, 10, 15, 20])
    assert strict_anchor_edge(a, _event("low", [1, 6, 11, 16, 25]), 5) is not None
    assert strict_anchor_edge(a, _event("low", [1, 6, 11, 16, 26]), 5) is None
    assert strict_anchor_edge(a, _event("high", [0, 5, 10, 15, 20]), 5) is None


def test_mutual_unique_match_refuses_ambiguity_instead_of_tie_breaking():
    a = [_event("low", [0, 5, 10, 15, 20])]
    b = [
        _event("low", [1, 6, 11, 16, 21]),
        _event("low", [2, 7, 12, 17, 22]),
    ]
    audit = mutual_unique_strict_matches(a, b, 5)
    assert audit.matches == ()
    assert audit.ambiguous_a == (0,)


def test_mutual_unique_match_returns_only_same_identity():
    a = [
        _event("low", [0, 5, 10, 15, 20]),
        _event("low", [100, 105, 110, 115, 120]),
    ]
    b = [
        _event("low", [1, 6, 11, 16, 21]),
        _event("low", [101, 106, 111, 116, 121]),
    ]
    audit = mutual_unique_strict_matches(a, b, 5)
    assert audit.matches == ((0, 0), (1, 1))
    assert not audit.ambiguous_a and not audit.ambiguous_b


def test_causal_identity_publication_is_append_only_when_later_scale_evidence_arrives():
    first = _record("fine", [0, 5, 10, 15, 20], level=2)
    first["confirmation_bar"] = 24
    later = _record("coarse", [0, 5, 10, 15, 20], level=4)
    later["confirmation_bar"] = 31
    prefix = causal_publish_qualified_identities([first])
    full = causal_publish_qualified_identities([first, later])
    assert prefix["identity_events"] == full["identity_events"]
    assert len(prefix["evidence_events"]) == 1
    assert len(full["evidence_events"]) == 2
    assert (
        full["evidence_events"][1]["canonical_identity_id"]
        == full["identity_events"][0]["canonical_identity_id"]
    )


def test_causal_publication_keeps_overlapping_rolling_windows():
    w12 = _record("w12", [0, 5, 10, 15, 20])
    w12["confirmation_bar"] = 24
    w23 = _record("w23", [10, 15, 20, 25, 30])
    w23["confirmation_bar"] = 34
    out = causal_publish_qualified_identities([w12, w23])
    assert len(out["identity_events"]) == 2
