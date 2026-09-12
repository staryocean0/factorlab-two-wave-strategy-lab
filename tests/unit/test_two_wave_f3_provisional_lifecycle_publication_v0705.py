from types import SimpleNamespace

import numpy as np

from factor_lab.visual_structure.two_wave.f3_provisional_lifecycle_publication_v0705 import (
    prefix_predecessor,
    project_prefix_realization,
    replay_publications_from_cache,
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


def bars_with_closes(closes):
    return [
        {
            "timestamp": f"2020-01-01T00:{i:02d}:00Z",
            "available_at": f"2020-01-01T00:{i:02d}:00Z",
            "close": float(value),
        }
        for i, value in enumerate(closes)
    ]


def base_rows(future_pred_conf=20):
    old_pred = rr("p0", "high", 0, 1)
    future_pred = rr("p1", "high", 2, future_pred_conf)
    selected = [
        rr("a", "low", 3, 4),
        rr("b", "high", 6, 7),
        rr("c", "low", 9, 10),
        rr("d", "high", 12, 13),
        rr("e", "low", 15, 16),
    ]
    rows = [old_pred, future_pred, *selected]
    rows.sort(key=lambda x: (x.node.occurrence_index, x.node.confirmation_index, x.node.node_id))
    realization = {"level": 0, "nodes": tuple(selected)}
    return rows, realization


def test_prefix_predecessor_bypasses_future_unconfirmed_blocker():
    rows, realization = base_rows(future_pred_conf=20)
    run = SimpleNamespace(ridge_nodes_by_level=(tuple(rows),))

    early = prefix_predecessor(run, realization, 16)
    late = prefix_predecessor(run, realization, 20)

    assert early["valid"] is True
    assert early["predecessor_ridge_id"] == "p0"
    assert late["valid"] is True
    assert late["predecessor_ridge_id"] == "p1"


def test_first_invalid_projection_can_publish_when_causal_predecessor_arrives():
    rows, realization = base_rows(future_pred_conf=18)
    # Remove p0 so the first observation is left-censored until p1 confirms.
    rows = [x for x in rows if x.ridge_id != "p0"]
    run = SimpleNamespace(ridge_nodes_by_level=(tuple(rows),))
    key = tuple(str(x.ridge_id) for x in realization["nodes"])
    lifecycle = {
        "objects": {
            key: {
                "object_id": "obj-delay",
                "first_observation_bar": 16,
                "certified": False,
                "certification_bar": None,
                "events": [{"kind": "observed", "event_bar": 16}],
            }
        },
        "final_live_keys": {key},
        "final_static_store": {key: [realization]},
        "violations": {},
    }
    closes = [5, 1, 6, 2, 4, 5, 10, 8, 7, 3, 5, 6, 9, 7, 6, 4, 5, 5, 5]
    bars = bars_with_closes(closes)
    prefix_frames = [(16, {key: [realization]}), (18, {key: [realization]})]

    out = replay_publications_from_cache(run, lifecycle, prefix_frames, bars)
    state = out["states"][key]

    assert state["prior_invalid_projection_count"] == 1
    assert state["publication"] is not None
    assert state["publication"]["publishing_evidence_bar"] == 18
    assert state["publication"]["predecessor_ridge_id"] == "p1"
    assert out["hard_invariant_violation_count"] == 0


def test_later_predecessor_change_cannot_rewrite_first_publication_and_status_append_is_stable():
    rows, realization = base_rows(future_pred_conf=20)
    run = SimpleNamespace(ridge_nodes_by_level=(tuple(rows),))
    key = tuple(str(x.ridge_id) for x in realization["nodes"])
    lifecycle = {
        "objects": {
            key: {
                "object_id": "obj-stable",
                "first_observation_bar": 16,
                "certified": True,
                "certification_bar": 20,
                "events": [
                    {"kind": "observed", "event_bar": 16},
                    {"kind": "certified", "event_bar": 20},
                ],
            }
        },
        "final_live_keys": {key},
        "final_static_store": {key: [realization]},
        "violations": {},
    }
    # p0 permits raw ordinal-0 to select bar 1 at price 1; after p1 confirms,
    # the closer predecessor moves the lower bound to bar 3 and would select
    # a different valid raw identity. The first publication must remain frozen.
    closes = [5, 1, 6, 2, 4, 5, 10, 8, 7, 3, 5, 6, 9, 7, 6, 4, 5, 5, 5, 5, 5]
    bars = bars_with_closes(closes)
    prefix_frames = [(16, {key: [realization]}), (20, {key: [realization]})]

    out1 = replay_publications_from_cache(run, lifecycle, prefix_frames, bars)
    out2 = replay_publications_from_cache(run, lifecycle, prefix_frames, bars)
    state = out1["states"][key]
    pub = state["publication"]

    assert pub is not None
    assert pub["publishing_evidence_bar"] == 16
    assert pub["status_at_publication"] == "observed_live_unresolved"
    assert pub["raw_occurrence_bars"][0] == 1
    assert state["later_valid_would_rewrite_suppressed_count"] == 1
    assert out1["unresolved_then_certified_publication_count"] == 1
    assert out1["hard_invariant_violation_count"] == 0
    assert out1["aggregate_publication_identity_sha256"] == out2["aggregate_publication_identity_sha256"]
    assert out1["publication_count"] == out2["publication_count"] == 1


def test_prefix_projection_uses_no_bar_after_evidence_time():
    rows, realization = base_rows(future_pred_conf=20)
    run = SimpleNamespace(ridge_nodes_by_level=(tuple(rows),))
    closes = np.asarray([5, 1, 6, 2, 4, 5, 10, 8, 7, 3, 5, 6, 9, 7, 6, 4, 5, 100, 100, 100, 100], dtype=float)
    bars = bars_with_closes(closes)
    pred = prefix_predecessor(run, realization, 16)
    out = project_prefix_realization(run, realization, 16, bars, closes, predecessor=pred, object_id="obj")
    assert out["valid"] is True
    assert max(out["raw_occurrence_bars"]) <= 16
    assert all(window["upper_bar"] <= 16 for window in out["windows"])
