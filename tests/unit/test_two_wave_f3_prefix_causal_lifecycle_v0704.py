from itertools import combinations
from types import SimpleNamespace

from factor_lab.visual_structure.two_wave.f3_prefix_causal_lifecycle_v0704 import (
    build_lifecycle_for_case,
    dominant_quintet_indices,
)
from factor_lab.visual_structure.two_wave.ridge_semantic_objectization_stream_v0701 import (
    _dominant_incremental,
)


def rr(rid, kind, occ, conf):
    return SimpleNamespace(
        ridge_id=rid,
        node=SimpleNamespace(
            node_id=f"n-{rid}-{occ}-{conf}",
            kind=kind,
            occurrence_index=occ,
            confirmation_index=conf,
        ),
    )


def death(rid, fine, coarse, conf):
    return SimpleNamespace(
        ridge_id=rid,
        fine_level=fine,
        coarse_level=coarse,
        confirmation_index=conf,
    )


def test_visibility_path_enumerator_matches_bruteforce_f3_definition():
    rows = [
        rr("a", "low", 1, 1),
        rr("x", "high", 2, 2),
        rr("b", "high", 3, 3),
        rr("c", "low", 4, 4),
        rr("y", "high", 5, 5),
        rr("d", "high", 6, 6),
        rr("e", "low", 7, 7),
        rr("f", "high", 8, 8),
    ]
    survival = {
        "a": 3,
        "x": 0,
        "b": 2,
        "c": 2,
        "y": 0,
        "d": 2,
        "e": 2,
        "f": 1,
    }
    brute = set()
    for idxs in combinations(range(len(rows)), 5):
        nodes = tuple(rows[i] for i in idxs)
        if any(str(a.node.kind) == str(b.node.kind) for a, b in zip(nodes, nodes[1:])):
            continue
        if _dominant_incremental(rows, idxs, survival):
            brute.add(tuple(idxs))
    fast = set(dominant_quintet_indices(rows, survival))
    assert fast == brute


def test_prefix_extension_keeps_first_observation_immutable_until_later_c1_certification():
    # All level-0 turns are known by bar 6. Boundary a/b survive to level 1
    # at bar 7, making the nonconsecutive F3 object observable. The skipped
    # ridge x receives an explicit 0->1 death only at bar 9, so cutoff=8 must
    # leave the object unresolved while cutoff=9 may append certification.
    level0 = [
        rr("a", "low", 1, 1),
        rr("x", "high", 2, 2),
        rr("b", "high", 3, 3),
        rr("c", "low", 4, 4),
        rr("d", "high", 5, 5),
        rr("e", "low", 6, 6),
    ]
    level1 = [
        rr("a", "low", 1, 7),
        rr("b", "high", 3, 7),
    ]
    run = SimpleNamespace(
        ridge_nodes_by_level=(tuple(level0), tuple(level1)),
        deaths=[death("x", 0, 1, 9)],
    )

    short = build_lifecycle_for_case(run, 0, 8)
    long = build_lifecycle_for_case(run, 0, 9)
    key = ("a", "b", "c", "d", "e")

    assert key in short["objects"]
    assert key in long["objects"]
    s = short["objects"][key]
    l = long["objects"][key]
    assert s["first_observation_bar"] == 7
    assert l["first_observation_bar"] == 7
    assert s["object_id"] == l["object_id"]
    assert s["first_witness_order"] == l["first_witness_order"]
    assert s["certified"] is False
    assert l["certified"] is True
    assert l["certification_bar"] == 9
    assert short["violations"] == {}
    assert long["violations"] == {}


def test_final_live_keys_equal_static_keys_for_simple_certified_object():
    level0 = [
        rr("a", "low", 1, 1),
        rr("b", "high", 2, 2),
        rr("c", "low", 3, 3),
        rr("d", "high", 4, 4),
        rr("e", "low", 5, 5),
    ]
    run = SimpleNamespace(ridge_nodes_by_level=(tuple(level0),), deaths=[])
    life = build_lifecycle_for_case(run, 0, 6)
    key = ("a", "b", "c", "d", "e")
    assert set(life["final_static_store"]) == {key}
    assert life["final_live_keys"] == {key}
    assert life["objects"][key]["first_observation_bar"] == 5
    assert life["objects"][key]["certified"] is True
    assert [x["kind"] for x in life["objects"][key]["events"]] == ["observed", "certified"]
    assert life["violations"] == {}
