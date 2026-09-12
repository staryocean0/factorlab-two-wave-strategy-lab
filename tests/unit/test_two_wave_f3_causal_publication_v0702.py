from types import SimpleNamespace

from factor_lab.visual_structure.two_wave.f3_causal_publication_v0702 import (
    certificate_object,
    certificate_realization,
    distribution,
    frozen_decision,
)


def _row(rid, kind, occurrence, confirmation):
    return SimpleNamespace(
        ridge_id=rid,
        node=SimpleNamespace(
            kind=kind,
            occurrence_index=occurrence,
            confirmation_index=confirmation,
            node_id=f"{rid}-{occurrence}-{confirmation}",
        ),
    )


def test_distribution_has_linear_quartiles():
    out = distribution([0, 1, 2, 3, 4])
    assert out["median"] == 2
    assert out["q1"] == 1
    assert out["q3"] == 3


def test_death_certificate_uses_confirmed_boundary_survival_and_explicit_skipped_death():
    r0_0 = _row("r0", "low", 0, 1)
    x_0 = _row("x", "high", 1, 1)
    r1_0 = _row("r1", "high", 2, 2)
    r2_0 = _row("r2", "low", 3, 3)
    r3_0 = _row("r3", "high", 4, 4)
    r4_0 = _row("r4", "low", 5, 5)
    level0 = [r0_0, x_0, r1_0, r2_0, r3_0, r4_0]

    level1 = [
        _row("r0", "low", 0, 8),
        _row("r1", "high", 2, 8),
        _row("r2", "low", 3, 8),
        _row("r3", "high", 4, 8),
        _row("r4", "low", 5, 8),
    ]
    death = SimpleNamespace(
        ridge_id="x",
        fine_level=0,
        coarse_level=1,
        confirmation_index=7,
    )
    ridge = SimpleNamespace(
        deaths=[death],
        ridge_nodes_by_level=(tuple(level0), tuple(level1)),
    )
    levels = [level0, level1]
    key = ("r0", "r1", "r2", "r3", "r4")

    cert = certificate_realization(ridge, levels, key, 0, 8)
    assert cert is not None
    assert cert["certificate_time"] == 8
    assert cert["base_realization_confirmation"] == 5
    assert cert["certificate_delay_bars"] == 3
    assert cert["used_death_witness"] is True

    obj = certificate_object(ridge, 0, 8, key, 1 << 0, levels)
    assert obj is not None
    assert obj["certificate_time"] == 8


def test_missing_explicit_death_blocks_nonconsecutive_certificate():
    level0 = [
        _row("r0", "low", 0, 1),
        _row("x", "high", 1, 1),
        _row("r1", "high", 2, 2),
        _row("r2", "low", 3, 3),
        _row("r3", "high", 4, 4),
        _row("r4", "low", 5, 5),
    ]
    level1 = [
        _row("r0", "low", 0, 8),
        _row("r1", "high", 2, 8),
        _row("r2", "low", 3, 8),
        _row("r3", "high", 4, 8),
        _row("r4", "low", 5, 8),
    ]
    ridge = SimpleNamespace(deaths=[], ridge_nodes_by_level=(tuple(level0), tuple(level1)))
    key = ("r0", "r1", "r2", "r3", "r4")
    assert certificate_realization(ridge, [level0, level1], key, 0, 8) is None


def test_consecutive_f3_realization_certifies_without_death_witness():
    level0 = [
        _row("r0", "low", 0, 1),
        _row("r1", "high", 1, 2),
        _row("r2", "low", 2, 3),
        _row("r3", "high", 3, 4),
        _row("r4", "low", 4, 5),
    ]
    ridge = SimpleNamespace(deaths=[], ridge_nodes_by_level=(tuple(level0),))
    key = ("r0", "r1", "r2", "r3", "r4")
    cert = certificate_realization(ridge, [level0], key, 0, 5)
    assert cert is not None
    assert cert["certificate_time"] == 5
    assert cert["certificate_delay_bars"] == 0
    assert cert["used_death_witness"] is False


def test_frozen_decision_distinguishes_coverage_and_uniqueness():
    base = {
        "certified_object_fraction": 0.9,
        "certified_presence_fraction_given_f3_positive_cutoff": 0.9,
        "certificate_replay_failure_count": 0,
        "certified_object_count_per_f3_positive_cutoff": {"median": 3.0, "q3": 5.0},
    }
    out = frozen_decision(base)
    assert out["gate_A_causal_certificate_coverage"] is True
    assert out["gate_B_direct_single_parent_publication_identifiability"] is False
    assert out["primary_category"] == "v0702_f3_immutable_event_certificate_supported_append_only_concept_salvaged_object_selection_unresolved"

    base["certified_object_count_per_f3_positive_cutoff"] = {"median": 1.0, "q3": 2.0}
    out = frozen_decision(base)
    assert out["primary_category"] == "v0702_f3_immutable_event_and_single_parent_publication_precheck_supported"

    base["certified_object_fraction"] = 0.5
    out = frozen_decision(base)
    assert out["primary_category"] == "v0702_f3_death_certificate_coverage_insufficient_event_semantics_not_frozen"
