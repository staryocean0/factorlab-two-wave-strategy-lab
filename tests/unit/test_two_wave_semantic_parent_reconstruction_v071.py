from types import SimpleNamespace

from factor_lab.visual_structure.two_wave.semantic_parent_reconstruction_v071 import (
    F0_EXACT,
    F1_FULL,
    F2_CORE,
    F3_SUBSEQUENCE,
    base_five_turn_object,
    family_member,
    frozen_adjudication,
    skipped_snapshot_ridges,
    summarize_family_records,
)


def _ridge(idx, kind, value, ridge_id=None):
    node = SimpleNamespace(
        node_id=f"n{idx}_{kind}_{value}",
        occurrence_index=idx,
        confirmation_index=idx,
        kind=kind,
        value=float(value),
    )
    return SimpleNamespace(node=node, ridge_id=ridge_id or f"r{idx}")


def _selected_and_snapshot(endpoint_break=False, core_break=False):
    selected = (
        _ridge(0, "low", 1.0, "a"),
        _ridge(4, "high", 5.0, "b"),
        _ridge(8, "low", 2.0, "c"),
        _ridge(12, "high", 6.0, "d"),
        _ridge(16, "low", 1.5, "e"),
    )
    extras = [
        _ridge(2, "low", 0.5 if endpoint_break else 2.5, "x0"),
        _ridge(6, "high", 7.0 if core_break else 4.0, "x1"),
        _ridge(10, "low", 3.0, "x2"),
        _ridge(14, "high", 5.0, "x3"),
    ]
    snapshot = tuple(sorted(selected + tuple(extras), key=lambda x: x.node.occurrence_index))
    return selected, snapshot


def test_base_object_and_ordered_subsequence_allow_intervening_ridges():
    obj, snapshot = _selected_and_snapshot()
    assert base_five_turn_object(obj)
    assert family_member(F3_SUBSEQUENCE, obj, snapshot)
    assert skipped_snapshot_ridges(obj, snapshot) == 4


def test_full_envelope_accepts_dominant_selected_turns():
    obj, snapshot = _selected_and_snapshot()
    assert family_member(F1_FULL, obj, snapshot)
    assert family_member(F2_CORE, obj, snapshot)


def test_core_envelope_can_survive_endpoint_envelope_failure():
    obj, snapshot = _selected_and_snapshot(endpoint_break=True)
    assert not family_member(F1_FULL, obj, snapshot)
    assert family_member(F2_CORE, obj, snapshot)
    assert family_member(F3_SUBSEQUENCE, obj, snapshot)


def test_core_envelope_rejects_more_extreme_internal_turn():
    obj, snapshot = _selected_and_snapshot(core_break=True)
    assert not family_member(F1_FULL, obj, snapshot)
    assert not family_member(F2_CORE, obj, snapshot)
    assert family_member(F3_SUBSEQUENCE, obj, snapshot)


def _case(exact=False, full=False, core=False, subsequence=False):
    flags = {
        F0_EXACT: exact,
        F1_FULL: full,
        F2_CORE: core,
        F3_SUBSEQUENCE: subsequence,
    }
    return {
        family: {
            "supported": flag,
            "compatible_object_count": 1 if flag else 0,
            "supported_level_count": 1 if flag else 0,
            "minimum_skipped_snapshot_ridges": 0 if family == F0_EXACT and flag else (2 if flag else None),
        }
        for family, flag in flags.items()
    }


def test_adjudication_prefers_full_envelope_over_looser_families():
    rows = [_case(full=True, core=True, subsequence=True) for _ in range(8)] + [_case() for _ in range(3)]
    decision = frozen_adjudication(summarize_family_records(rows))
    assert decision["primary_category"] == "v071_full_envelope_parent_objectization_development_rescue_supported"
    assert decision["selected_development_challenger_family"] == F1_FULL


def test_adjudication_can_fall_through_to_ordered_subsequence():
    rows = [_case(subsequence=True) for _ in range(8)] + [_case() for _ in range(3)]
    decision = frozen_adjudication(summarize_family_records(rows))
    assert decision["primary_category"] == "v071_ordered_subsequence_parent_objectization_development_rescue_supported"
    assert decision["selected_development_challenger_family"] == F3_SUBSEQUENCE


def test_legacy_exact_threshold_is_fail_closed_control_drift():
    rows = [_case(exact=True) for _ in range(8)] + [_case() for _ in range(3)]
    decision = frozen_adjudication(summarize_family_records(rows))
    assert decision["primary_category"] == "v071_legacy_exact_tuple_control_drift_or_contradiction"
    assert decision["development_challenger_selected"] is False
