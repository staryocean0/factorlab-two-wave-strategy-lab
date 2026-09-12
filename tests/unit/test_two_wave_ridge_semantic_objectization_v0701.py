from types import SimpleNamespace

from factor_lab.visual_structure.two_wave.ridge_semantic_objectization_f3dp_v0701 import (
    evaluate_f3_case_dp,
)
from factor_lab.visual_structure.two_wave.ridge_semantic_objectization_v0701 import (
    causal_survival_levels,
    family_f1_ordered_common_scale,
    family_f2_one_step_survivor,
    family_f3_persistence_dominant,
    frozen_decision,
    summarize_family_records,
    summarize_family_case,
)
from factor_lab.visual_structure.two_wave.ridge_semantic_objectization_stream_v0701 import (
    evaluate_f1_case,
)


def node(rid, kind, occ, conf=0):
    return SimpleNamespace(
        ridge_id=rid,
        node=SimpleNamespace(
            kind=kind,
            occurrence_index=occ,
            confirmation_index=conf,
            node_id=f"n-{rid}-{occ}",
        ),
    )


def run(levels, tuples_by_level=None):
    return SimpleNamespace(
        ridge_nodes_by_level=tuple(tuple(x) for x in levels),
        tuples_by_level=tuple(tuple(x) for x in (tuples_by_level or [[] for _ in levels])),
    )


def test_causal_survival_level_uses_only_eligible_levels_passed_in():
    a0 = node("A", "low", 1)
    a1 = node("A", "low", 2)
    b0 = node("B", "high", 3)
    assert causal_survival_levels([[a0, b0], [a1]]) == {"A": 1, "B": 0}


def test_f1_dynamic_count_matches_bruteforce_unique_ridge_objects():
    l0 = [
        node("A", "low", 10), node("B", "high", 20), node("C", "low", 30),
        node("D", "high", 40), node("E", "low", 50), node("F", "high", 60),
    ]
    l1 = [
        node("A", "low", 10), node("B", "high", 20), node("C", "low", 30),
        node("D", "high", 40), node("E", "low", 50),
    ]
    r = run([l0, l1])
    brute = family_f1_ordered_common_scale(r, 0, 70)
    cells = [(8, 12), (18, 22), (28, 32), (38, 42), (48, 52)]
    kinds = ["low", "high", "low", "high", "low"]
    out = evaluate_f1_case(r, 0, 70, cells, kinds, [10, 20, 30, 40, 50])
    assert out["candidate_object_count"] == len(brute)
    assert out["compatible_object_count"] == 1
    assert out["support"] is True
    assert out["ordinal_exact_anchor"] == [True] * 5


def test_f2_removes_one_level_only_interstitial_ridge():
    # At level 0 the desired five survivor ridges are interrupted by X/Y.
    l0 = [
        node("A", "low", 10),
        node("X", "high", 12),
        node("B", "high", 20),
        node("C", "low", 30),
        node("Y", "high", 32),
        node("D", "high", 40),
        node("E", "low", 50),
    ]
    l1 = [
        node("A", "low", 10),
        node("B", "high", 20),
        node("C", "low", 30),
        node("D", "high", 40),
        node("E", "low", 50),
    ]
    objects = family_f2_one_step_survivor(run([l0, l1]), 0, 60)
    assert ("A", "B", "C", "D", "E") in objects


def test_f3_allows_only_lower_persistence_skipped_ridges():
    l0 = [
        node("A", "low", 10),
        node("X", "high", 12),
        node("B", "high", 20),
        node("C", "low", 30),
        node("D", "high", 40),
        node("E", "low", 50),
    ]
    l1 = [
        node("A", "low", 10),
        node("B", "high", 20),
        node("C", "low", 30),
        node("D", "high", 40),
        node("E", "low", 50),
    ]
    r = run([l0, l1])
    objects = family_f3_persistence_dominant(r, 0, 60)
    assert ("A", "B", "C", "D", "E") in objects

    cells = [(8, 11), (18, 22), (28, 32), (38, 42), (48, 52)]
    kinds = ["low", "high", "low", "high", "low"]
    brute_summary = summarize_family_case(objects, cells, kinds, [10, 20, 30, 40, 50])
    dp_summary = evaluate_f3_case_dp(r, 0, 60, cells, kinds, [10, 20, 30, 40, 50])
    assert dp_summary == brute_summary

    # If X survives just as high as the selected boundaries, it may not be skipped.
    l1_with_x = [
        node("A", "low", 10), node("X", "high", 12), node("B", "high", 20),
        node("C", "low", 30), node("D", "high", 40), node("E", "low", 50),
    ]
    objects2 = family_f3_persistence_dominant(run([l0, l1_with_x]), 0, 60)
    assert ("A", "B", "C", "D", "E") not in objects2


def test_summary_and_frozen_precedence():
    def records(n):
        return [
            {
                "support": i < n,
                "candidate_object_count": 2,
                "compatible_object_count": 1 if i < n else 0,
                "ordinal_exact_anchor": [False] * 5,
            }
            for i in range(11)
        ]

    families = {
        "F0": summarize_family_records(records(3)),
        "F1": summarize_family_records(records(10)),
        "F2": summarize_family_records(records(8)),
        "F3": summarize_family_records(records(10)),
    }
    out = frozen_decision(families)
    assert out["selected_reconstruction_family"] == "F2_one_step_survivor_skeleton"
    assert out["primary_category"] == "v0701_one_step_survivor_objectization_candidate_supported"
