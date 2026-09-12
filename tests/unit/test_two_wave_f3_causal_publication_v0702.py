from types import SimpleNamespace

from factor_lab.visual_structure.two_wave.f3_causal_publication_v0702 import (
    build_lineage_index,
    enumerate_checkpoint_f3_objects,
    f3_publication_id,
    summarize_publication_precheck,
    trace_f3_identity,
    valid_realizations_at,
)


def _row(rid, level, occ, conf, kind):
    return SimpleNamespace(
        ridge_id=rid,
        node=SimpleNamespace(
            node_id=f"{rid}_L{level}",
            occurrence_index=occ,
            confirmation_index=conf,
            kind=kind,
            value=float(occ),
        ),
    )


def _synthetic_run():
    # F3 identity A-B-C-D-E is valid at t=20 because all five selected
    # ridges have survived to level 1 while skipped X/Y remain level-0 only.
    # X survives to level 1 at t=30 and temporarily blocks A-B. At t=40 the
    # selected ridges survive to level 2 and F3 becomes valid again.
    # Every confirmation is at or after its occurrence, so the fixture itself
    # respects the causal visibility rule exercised by checkpoint enumeration.
    level0 = [
        _row("A", 0, 0, 1, "low"),
        _row("X", 0, 1, 2, "high"),
        _row("Y", 0, 2, 3, "low"),
        _row("B", 0, 4, 6, "high"),
        _row("C", 0, 8, 10, "low"),
        _row("D", 0, 12, 14, "high"),
        _row("E", 0, 16, 18, "low"),
    ]
    level1 = [
        _row("A", 1, 0, 20, "low"),
        _row("X", 1, 1, 30, "high"),
        _row("B", 1, 5, 20, "high"),
        _row("C", 1, 8, 20, "low"),
        _row("D", 1, 12, 20, "high"),
        _row("E", 1, 16, 20, "low"),
    ]
    level2 = [
        _row("A", 2, 0, 40, "low"),
        _row("B", 2, 5, 40, "high"),
        _row("C", 2, 8, 40, "low"),
        _row("D", 2, 12, 40, "high"),
        _row("E", 2, 16, 40, "low"),
    ]
    return SimpleNamespace(ridge_nodes_by_level=(level0, level1, level2))


def test_publication_id_is_identity_only_and_stable():
    identity = ("A", "B", "C", "D", "E")
    assert f3_publication_id(identity) == f3_publication_id(list(identity))
    assert f3_publication_id(identity) != f3_publication_id(("A", "B", "C", "D", "F"))


def test_prefix_f3_can_invalidate_and_revalidate_without_rewriting_event():
    run = _synthetic_run()
    index = build_lineage_index(run)
    identity = ("A", "B", "C", "D", "E")

    assert valid_realizations_at(index, identity, 20)
    assert not valid_realizations_at(index, identity, 30)
    assert valid_realizations_at(index, identity, 40)

    trace = trace_f3_identity(index, identity, observed_checkpoints=(20, 40))
    assert trace["first_event"]["first_known_confirmation_bar"] == 20
    assert trace["first_event"]["publishing_level"] == 0
    assert trace["validity_gap_after_publication"] is True
    assert trace["would_rewrite_filtered_coordinates"] is True
    assert all(trace["gates"].values())


def test_checkpoint_continuity_gate_fails_if_identity_is_observed_when_prefix_f3_is_false():
    run = _synthetic_run()
    trace = trace_f3_identity(
        build_lineage_index(run),
        ("A", "B", "C", "D", "E"),
        observed_checkpoints=(20, 30),
    )
    assert trace["gates"]["A_causal_reconstruction"] is True
    assert trace["gates"]["B_checkpoint_continuity"] is False


def test_checkpoint_enumerator_contains_expected_f3_identity():
    run = _synthetic_run()
    objects = enumerate_checkpoint_f3_objects(run, chart_start=0, cutoff=20)
    assert ("A", "B", "C", "D", "E") in objects


def test_summary_uses_hard_gate_failures_not_rewrite_thresholds():
    run = _synthetic_run()
    index = build_lineage_index(run)
    good = trace_f3_identity(index, ("A", "B", "C", "D", "E"), observed_checkpoints=(20, 40))
    summary = summarize_publication_precheck([1, 1], [good])
    assert summary["all_hard_gates_pass"] is True
    assert summary["identities_with_later_filtered_coordinate_rewrite_pressure"] == 1
    assert summary["identities_with_validity_gap_after_publication"] == 1
    assert summary["primary_category"] == "v0702_f3_append_only_event_publication_structurally_transplantable"

    bad = dict(good)
    bad["ridge_ids"] = ["A", "B", "C", "D", "F"]
    bad["publication_event_id"] = good["publication_event_id"]
    failed = summarize_publication_precheck([1], [good, bad])
    assert failed["all_hard_gates_pass"] is False
    assert failed["identity_or_publication_id_collision"] is True
    assert failed["primary_category"] == "v0702_f3_causal_event_publication_precheck_failed"
