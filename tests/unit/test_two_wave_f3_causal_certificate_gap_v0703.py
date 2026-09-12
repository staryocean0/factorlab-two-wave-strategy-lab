from types import SimpleNamespace

from factor_lab.visual_structure.two_wave.f3_causal_certificate_gap_v0703 import (
    analyze_realization_certificate,
    frozen_decision,
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
    # At death coarse level 1, b is intentionally absent from stored representation;
    # both a and b are nevertheless confirmed at level 2, which is sufficient for C1.
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
