from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from factor_lab.visual_structure.two_wave.characteristic_scale_v051 import (
    CandidateFeature,
    CharacteristicEvent,
    project_event_to_raw,
)
from factor_lab.visual_structure.two_wave.multiscale_v050 import (
    ConfirmedExtremum,
    TwoWaveCandidate,
)
from factor_lab.visual_structure.two_wave.raw_projection_identity_v062 import (
    CanonicalPathIndex,
    audit_projection_event,
    earliest_valid_member,
    one_minute_projection_from_windows,
    paired_window_diagnostics,
    raw_pair_displacement,
    strict_time_tuple_match,
    summarize_projection_group,
)


def bars(n=50, closes=None):
    if closes is None:
        closes = [100.0] * n
    assert len(closes) == n
    return [
        {
            "timestamp": f"2020-01-02T{(90 + 5*i) // 60:02d}:{(90 + 5*i) % 60:02d}:00+00:00",
            "available_at": f"2020-01-02T{(90 + 5*i) // 60:02d}:{(90 + 5*i) % 60:02d}:00+00:00",
            "close": float(closes[i]),
        }
        for i in range(n)
    ]


def make_event(filtered=(5, 10, 15, 20, 25), member_confirmation=30, selection_confirmation=32):
    kinds = ("low", "high", "low", "high", "low")
    extrema = tuple(
        ConfirmedExtremum(
            scale_id="x",
            kind=kind,
            occurrence_index=idx,
            confirmation_index=min(idx + 1, member_confirmation),
            value=1.0,
        )
        for kind, idx in zip(kinds, filtered)
    )
    candidate = TwoWaveCandidate("x", extrema)
    feature = CandidateFeature(
        level=2,
        scale_id="x",
        sigma_bars=2.0,
        phase="low",
        occurrence_indices=tuple(filtered),
        confirmation_index=member_confirmation,
        corrected_center=float(filtered[2]),
        common_response=None,
        candidate=candidate,
        member_id="m",
    )
    return CharacteristicEvent(
        event_id=f"e-{filtered}-{member_confirmation}",
        family_id="f",
        level=2,
        scale_id="x",
        sigma_bars=2.0,
        feature=feature,
        finer_feature=feature,
        coarser_feature=feature,
        confirmation_index=selection_confirmation,
        scale_selection_delay_bars=selection_confirmation - member_confirmation,
    )


def valid_closes(n=50):
    x = [100.0] * n
    x[4] = 90.0
    x[12] = 110.0
    x[17] = 92.0
    x[22] = 115.0
    x[28] = 91.0
    return x


def test_audit_projection_is_output_equivalent_to_frozen_operator():
    bs = bars(closes=valid_closes())
    event = make_event()
    frozen = project_event_to_raw(event, bs)
    audited = audit_projection_event(event, bs)
    assert audited["valid"] is True
    assert audited["raw_occurrence_bars"] == list(frozen["raw_occurrence_indices"])
    assert audited["raw_occurrence_bars"] == [4, 12, 17, 22, 28]
    assert [row["ordinal"] for row in audited["windows"]] == [0, 1, 2, 3, 4]


def test_projection_is_prefix_immutable_after_confirmation_clock():
    x = valid_closes()
    bs = bars(closes=x)
    event = make_event()
    prefix = bs[:33]
    full = bs + [
        {
            "timestamp": "2020-01-03T00:00:00+00:00",
            "available_at": "2020-01-03T00:00:00+00:00",
            "close": 1000000.0,
        }
    ]
    a = project_event_to_raw(event, prefix)
    b = project_event_to_raw(event, full)
    assert a["raw_occurrence_indices"] == b["raw_occurrence_indices"]


def test_one_bar_filtered_bound_change_can_change_raw_identity_without_future_data():
    x = valid_closes()
    x[10] = 80.0
    bs = bars(closes=x)
    a = audit_projection_event(make_event((5, 10, 15, 20, 25)), bs)
    b = audit_projection_event(make_event((5, 11, 15, 20, 25)), bs)
    assert a["valid"] and b["valid"]
    assert a["raw_occurrence_bars"][0] == 4
    assert b["raw_occurrence_bars"][0] == 10
    assert a["raw_occurrence_bars"] != b["raw_occurrence_bars"]


def test_group_single_valuedness_never_selects_best_member():
    rows = [
        {
            "event_id": "a",
            "birth_level": 2,
            "birth_confirmation_bar": 20,
            "projection_valid": True,
            "projection_reason": None,
            "raw_occurrence_bars": [1, 2, 3, 4, 5],
        },
        {
            "event_id": "b",
            "birth_level": 3,
            "birth_confirmation_bar": 25,
            "projection_valid": True,
            "projection_reason": None,
            "raw_occurrence_bars": [1, 2, 3, 4, 6],
        },
    ]
    out = summarize_projection_group(rows)
    assert out["status"] == "multi_valued_projection"
    assert out["distinct_valid_raw_identity_count"] == 2
    assert out["changed_raw_ordinals"] == [4]


def test_earliest_valid_member_is_causal_not_cross_view_selected():
    rows = [
        {"event_id": "z", "birth_level": 1, "birth_confirmation_bar": 5, "projection_valid": False},
        {"event_id": "b", "birth_level": 3, "birth_confirmation_bar": 12, "projection_valid": True},
        {"event_id": "a", "birth_level": 2, "birth_confirmation_bar": 12, "projection_valid": True},
    ]
    assert earliest_valid_member(rows)["event_id"] == "a"


def test_canonical_path_projects_same_frozen_absolute_window_without_resampling():
    one_min = []
    for i in range(20):
        close = 100.0
        if i == 7:
            close = 80.0
        one_min.append(
            {
                "timestamp": f"2020-01-02T01:{30+i:02d}:00+00:00",
                "close": close,
            }
        )
    index = CanonicalPathIndex.from_bars(one_min)
    windows = [
        {"lower_time": "2020-01-02T01:30:00+00:00", "upper_time": "2020-01-02T01:40:00+00:00", "kind": "low"}
    ] * 5
    out = one_minute_projection_from_windows(windows, index)
    assert out["available"] is True
    assert out["times"] == ["2020-01-02T01:37:00+00:00"] * 5


def test_raw_pair_displacement_reports_first_and_suffix():
    a = [0, 5, 10, 15, 20]
    b = [1, 6, 20, 25, 30]
    out = raw_pair_displacement(a, b)
    assert out["first_displaced_ordinal"] == 2
    assert out["displaced_ordinals"] == [2, 3, 4]
    assert out["displaced_is_suffix"] is True


def test_strict_time_tuple_match_keeps_frozen_five_minute_relation():
    assert strict_time_tuple_match("low", [0, 5, 10, 15, 20], "low", [5, 10, 15, 20, 25])
    assert not strict_time_tuple_match("low", [0, 5, 10, 15, 20], "low", [6, 10, 15, 20, 25])
    assert not strict_time_tuple_match("low", [0, 5, 10, 15, 20], "high", [0, 5, 10, 15, 20])


def test_paired_window_diagnostic_flags_cross_window_exclusion_and_ties():
    a = [
        {
            "ordinal": i,
            "lower_time": 0,
            "upper_time": 10,
            "selected_raw_time": 2,
            "exact_extreme_tie_count": 1,
        }
        for i in range(5)
    ]
    b = [
        {
            "ordinal": i,
            "lower_time": 5,
            "upper_time": 15,
            "selected_raw_time": 12,
            "exact_extreme_tie_count": 2 if i == 3 else 1,
        }
        for i in range(5)
    ]
    out = paired_window_diagnostics(a, b)
    assert out["any_exact_tie"] is True
    assert out["rows"][0]["a_selected_inside_b_window"] is False
    assert out["rows"][0]["b_selected_inside_a_window"] is False
