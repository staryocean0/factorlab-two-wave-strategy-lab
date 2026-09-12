from types import SimpleNamespace

from factor_lab.visual_structure.two_wave.f3_event_publication_transplant_v0702 import (
    certify_f3_realization,
    frozen_decision,
    project_f3_realization_with_predecessor,
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


def test_certification_requires_explicit_skipped_ridge_death_and_boundary_survival():
    level0 = [
        rr("a", "low", 10, 11),
        rr("x", "high", 15, 16),
        rr("b", "high", 20, 21),
        rr("c", "low", 30, 31),
        rr("d", "high", 40, 41),
        rr("e", "low", 50, 51),
    ]
    # a/b survive beyond x's death; remaining selected ridges are present too.
    level1 = [
        rr("a", "low", 10, 12),
        rr("b", "high", 20, 22),
        rr("c", "low", 30, 32),
        rr("d", "high", 40, 42),
        rr("e", "low", 50, 52),
    ]
    ridge_run = SimpleNamespace(deaths=[death("x", 0, 1, 22)])
    out = certify_f3_realization(
        ridge_run,
        [level0, level1],
        0,
        level0,
        (0, 2, 3, 4, 5),
        60,
    )
    assert out["certified"] is True
    # Only the selected level-0 nodes plus the a/b survival proof for skipped x
    # enter this certificate. Unrelated level-1 confirmations (e.g. e at 52)
    # must not delay the event.
    assert out["event_confirmation_bar"] == 51
    assert out["certificate_count"] == 1

    no_death = SimpleNamespace(deaths=[])
    fail = certify_f3_realization(
        no_death,
        [level0, level1],
        0,
        level0,
        (0, 2, 3, 4, 5),
        60,
    )
    assert fail["certified"] is False
    assert fail["reason"] == "skipped_ridge_has_no_explicit_death"


def test_nonconsecutive_predecessor_projection_preserves_v064_sequential_principle():
    pred = rr("p", "high", 5, 6)
    # selected low/high/low/high/low; x is a skipped lower-persistence ridge.
    a = rr("a", "low", 10, 11)
    x = rr("x", "high", 15, 16)
    b = rr("b", "high", 20, 21)
    c = rr("c", "low", 30, 31)
    d = rr("d", "high", 40, 41)
    e = rr("e", "low", 50, 55)
    ridge_run = SimpleNamespace(ridge_nodes_by_level=[(pred, a, x, b, c, d, e)])
    closes = [10.0] * 60
    closes[10] = 5.0
    closes[20] = 15.0
    closes[30] = 6.0
    closes[40] = 14.0
    closes[50] = 7.0
    bars = [
        {"timestamp": f"2026-01-01T00:{i:02d}:00+00:00", "close": value, "available_at": f"2026-01-01T00:{i:02d}:00+00:00"}
        for i, value in enumerate(closes)
    ]
    realization = {
        "level": 0,
        "nodes": (a, b, c, d, e),
        "event_confirmation_bar": 55,
    }
    out = project_f3_realization_with_predecessor(ridge_run, realization, bars)
    assert out["valid"] is True
    assert out["raw_occurrence_bars"] == [10, 20, 30, 40, 50]
    assert out["predecessor_occurrence_bar"] == 5
    assert [w["lower_bar"] for w in out["windows"]] == [6, 11, 21, 31, 41]


def test_frozen_decision_precedence():
    summary = {
        "static_f3_support_cases": 8,
        "causally_certified_f3_support_cases": 7,
        "published_raw_semantic_support_cases": 8,
    }
    out = frozen_decision(summary, 0, 0)
    assert out["primary_category"] == "v0702_f3_static_objectization_not_causally_publishable"

    summary["causally_certified_f3_support_cases"] = 8
    summary["published_raw_semantic_support_cases"] = 7
    out = frozen_decision(summary, 0, 0)
    assert out["primary_category"] == "v0702_f3_event_salvaged_raw_projection_requires_reconstruction"

    summary["published_raw_semantic_support_cases"] = 8
    out = frozen_decision(summary, 1, 0)
    assert out["primary_category"] == "v0702_f3_event_projection_salvaged_downstream_interface_incompatible"

    out = frozen_decision(summary, 0, 0)
    assert out["primary_category"] == "v0702_f3_event_projection_publication_transplant_supported_downstream_semantic_retest_next"
