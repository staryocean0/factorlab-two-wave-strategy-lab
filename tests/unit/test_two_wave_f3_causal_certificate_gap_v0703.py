from types import SimpleNamespace

from factor_lab.visual_structure.two_wave.f3_causal_certificate_gap_v0703 import (
    analyze_realization_certificate,
    audit_human_compatible_static_f3,
    frozen_decision,
)
from factor_lab.visual_structure.two_wave.ridge_semantic_objectization_v0701 import (
    causal_survival_levels,
    eligible_nodes_by_level,
    realization_matches_human,
)
from factor_lab.visual_structure.two_wave.ridge_semantic_objectization_stream_v0701 import (
    _dominant_incremental,
    alternating_quintet_indices,
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
    return SimpleNamespace(ridge_id=rid, fine_level=fine, coarse_level=coarse, confirmation_index=conf)


def test_c1_accepts_coarser_confirmed_boundary_survival_when_exact_level_missing():
    level0 = [
        rr("a", "low", 10, 11), rr("x", "high", 15, 16), rr("b", "high", 20, 21),
        rr("c", "low", 30, 31), rr("d", "high", 40, 41), rr("e", "low", 50, 51),
    ]
    level1 = [rr("a", "low", 10, 18), rr("c", "low", 30, 33), rr("d", "high", 40, 43), rr("e", "low", 50, 53)]
    level2 = [rr("a", "low", 10, 20), rr("b", "high", 20, 24), rr("c", "low", 30, 35), rr("d", "high", 40, 45), rr("e", "low", 50, 55)]
    run = SimpleNamespace(
        deaths=[death("x", 0, 1, 22)],
        ridge_nodes_by_level=[tuple(level0), tuple(level1), tuple(level2)],
    )
    out = analyze_realization_certificate(run, level0, (0, 2, 3, 4, 5), 0, 60)
    assert out["c0_ok"] is False
    assert out["c1_ok"] is True
    assert "exact_coarse_boundary_representation_missing_but_coarser_confirmed_survival_exists" in out["blockers"]


def test_c1_never_waives_missing_explicit_death():
    level0 = [
        rr("a", "low", 10, 11), rr("x", "high", 15, 16), rr("b", "high", 20, 21),
        rr("c", "low", 30, 31), rr("d", "high", 40, 41), rr("e", "low", 50, 51),
    ]
    run = SimpleNamespace(deaths=[], ridge_nodes_by_level=[tuple(level0)])
    out = analyze_realization_certificate(run, level0, (0, 2, 3, 4, 5), 0, 60)
    assert out["c0_ok"] is False
    assert out["c1_ok"] is False
    assert out["blockers"] == ["missing_explicit_death_by_cutoff"]


def test_human_compatible_pruning_matches_bruteforce_f3_realizations():
    level0 = [
        rr("a", "low", 10, 11),
        rr("x", "high", 15, 16),
        rr("b", "high", 20, 21),
        rr("c", "low", 30, 31),
        rr("d", "high", 40, 41),
        rr("e", "low", 50, 51),
    ]
    level1 = [
        rr("a", "low", 10, 18),
        rr("b", "high", 20, 24),
        rr("c", "low", 30, 35),
        rr("d", "high", 40, 45),
        rr("e", "low", 50, 55),
    ]
    run = SimpleNamespace(deaths=[], ridge_nodes_by_level=[tuple(level0), tuple(level1)])
    levels = eligible_nodes_by_level(run, chart_start=0, cutoff=60)
    survival = causal_survival_levels(levels)
    cells = ((8, 12), (18, 22), (28, 32), (38, 42), (48, 52))
    kinds = ("low", "high", "low", "high", "low")
    human_bars = (10, 20, 30, 40, 50)

    brute = set()
    for level, rows in enumerate(levels):
        for idxs in alternating_quintet_indices(rows):
            if not _dominant_incremental(rows, idxs, survival):
                continue
            nodes = tuple(rows[i] for i in idxs)
            hit, _ = realization_matches_human(
                {"level": level, "nodes": nodes}, cells, kinds, human_bars
            )
            if hit:
                brute.add((level, tuple(str(x.ridge_id) for x in nodes)))

    pruned = audit_human_compatible_static_f3(
        run,
        levels,
        survival,
        cells,
        kinds,
        cutoff=60,
    )
    pruned_keys = {
        (int(row["level"]), tuple(str(x.ridge_id) for x in row["nodes"]))
        for row in pruned
    }
    assert pruned_keys == brute
    assert pruned_keys == {
        (0, ("a", "b", "c", "d", "e")),
        (1, ("a", "b", "c", "d", "e")),
    }


def test_frozen_decision_prefers_c1_restoration_then_missing_death():
    restored = frozen_decision(
        static_support_cases=8,
        c0_support_cases=7,
        gap_case_count=1,
        c1_support_cases=8,
        gap_realization_blocker_sets=[["exact_coarse_boundary_representation_missing_but_coarser_confirmed_survival_exists"]],
    )
    assert restored["primary_category"] == "v0703_minimal_explicit_death_certificate_restores_f3_causal_support"

    missing = frozen_decision(
        static_support_cases=8,
        c0_support_cases=7,
        gap_case_count=1,
        c1_support_cases=7,
        gap_realization_blocker_sets=[["missing_explicit_death_by_cutoff"], ["missing_explicit_death_by_cutoff"]],
    )
    assert missing["primary_category"] == "v0703_gap_requires_explicit_death_evidence_unavailable_at_cutoff"
