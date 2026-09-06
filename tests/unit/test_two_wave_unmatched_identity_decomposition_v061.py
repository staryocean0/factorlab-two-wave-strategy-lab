from types import SimpleNamespace

from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import (
    anchor_edge,
    any_level_anchor_survival,
    build_edge_graph,
    canonicalize_evaluated_records,
    canonicalize_tuple_births,
    level_anchor_survival,
    local_envelope_overlap_diagnostic,
    session_boundary_overlay,
)


def bars(minutes):
    return [
        {"timestamp": f"2020-01-02T{m // 60:02d}:{m % 60:02d}:00+00:00"}
        for m in minutes
    ]


def test_evaluated_raw_identity_groups_scale_evidence_and_rejections():
    bs = bars([90, 95, 100, 105, 110, 115])
    base = {
        "phase": "low",
        "five_occurrence_bars": [0, 1, 2, 3, 4],
        "scale_rejection_reasons": ["x"],
        "scale_qualified": False,
    }
    records = [
        {**base, "record_id": "a", "birth_scale_level": 2},
        {
            **base,
            "record_id": "b",
            "birth_scale_level": 3,
            "scale_rejection_reasons": [],
            "scale_qualified": True,
        },
    ]
    out = canonicalize_evaluated_records(records, bs)
    assert len(out) == 1
    assert out[0]["member_count"] == 2
    assert out[0]["qualified_any"] is True
    assert out[0]["rejection_reasons_union"] == ["x"]
    assert out[0]["birth_scale_levels"] == [2, 3]


def birth(event_id, level, phase="low", occ=(0, 1, 2, 3, 4)):
    other = "high" if phase == "low" else "low"
    kinds = [phase, other, phase, other, phase]
    nodes = tuple(SimpleNamespace(node=SimpleNamespace(kind=k)) for k in kinds)
    return SimpleNamespace(event_id=event_id, level=level, nodes=nodes, occurrence_indices=occ)


def test_tuple_births_group_exact_filtered_identity_across_levels():
    bs = bars([90, 95, 100, 105, 110])
    out = canonicalize_tuple_births([birth("a", 2), birth("b", 3)], bs)
    assert len(out) == 1
    assert out[0]["member_event_ids"] == ["a", "b"]
    assert out[0]["birth_scale_levels"] == [2, 3]


def event(phase, times):
    return {"phase": phase, "five_occurrence_times": times}


def test_phase_ignored_edge_diagnoses_phase_only_mismatch():
    a = event("low", [90, 95, 100, 105, 110])
    b = event("high", [91, 96, 101, 106, 111])
    assert anchor_edge(a, b, time_field="five_occurrence_times", require_phase=True) is None
    assert anchor_edge(a, b, time_field="five_occurrence_times", require_phase=False) is not None


def test_edge_graph_preserves_nonmutual_degree_without_tie_break():
    a = [
        event("low", [90, 95, 100, 105, 110]),
        event("low", [90, 95, 100, 105, 110]),
    ]
    b = [event("low", [90, 95, 100, 105, 110])]
    graph = build_edge_graph(a, b, time_field="five_occurrence_times")
    assert graph.a_edges == ((0,), (0,))
    assert graph.b_edges == ((0, 1),)
    assert graph.mutual_unique_matches == ()


def extrema_nodes(kinds_and_indices):
    return [SimpleNamespace(kind=k, occurrence_index=i) for k, i in kinds_and_indices]


def test_same_level_anchor_survival_requires_exactly_one_same_kind_node_per_anchor():
    bs = bars([90, 95, 100, 105, 110, 111])
    main = [90, 95, 100, 105, 110]
    nodes = extrema_nodes(
        [("low", 0), ("high", 1), ("low", 2), ("high", 3), ("low", 4)]
    )
    out = level_anchor_survival(main, "low", nodes, bs)
    assert out["all_unique"] is True
    nodes.append(SimpleNamespace(kind="low", occurrence_index=5))
    out2 = level_anchor_survival(main, "low", nodes, bs)
    assert out2["all_unique"] is False
    assert out2["ambiguous_anchor_count"] >= 1


def test_any_level_survival_reports_all_qualifying_levels_without_choosing():
    bs = bars([90, 95, 100, 105, 110])
    nodes = extrema_nodes(
        [("low", 0), ("high", 1), ("low", 2), ("high", 3), ("low", 4)]
    )
    out = any_level_anchor_survival([90, 95, 100, 105, 110], "low", [nodes, nodes], bs)
    assert out["all_unique_levels"] == [0, 1]


def test_session_boundary_is_overlay_with_one_nominal_bar_window():
    out = session_boundary_overlay(
        ["2020-01-02T01:35:00+00:00"] * 5,
        ["2020-01-02T06:00:00+00:00"] * 5,
    )
    assert out["boundary_tagged"] is True
    far = session_boundary_overlay(
        ["2020-01-02T02:00:00+00:00"] * 5,
        ["2020-01-02T06:00:00+00:00"] * 5,
    )
    assert far["boundary_tagged"] is False


def test_local_envelope_diagnostic_reports_minimum_and_tie_not_winner():
    main = event("low", [90, 100, 110, 120, 130])
    others = [
        event("low", [91, 101, 111, 121, 131]),
        event("low", [89, 99, 109, 119, 129]),
        event("high", [90, 100, 110, 120, 130]),
    ]
    out = local_envelope_overlap_diagnostic(main, others)
    assert out["candidate_count"] == 2
    assert out["minimum_max_delta_minutes"] == 1
    assert out["minimum_tie_count"] == 2
