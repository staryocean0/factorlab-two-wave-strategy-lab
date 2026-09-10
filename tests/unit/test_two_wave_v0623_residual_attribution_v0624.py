import pytest

from factor_lab.visual_structure.two_wave.v0623_residual_attribution_v0624 import (
    consensus_margin_and_span,
    d1_pair_topology,
    pair_transition_category,
    rescue_topology,
)


def test_pair_transition_categories_are_exhaustive_examples():
    assert pair_transition_category("uncertain", "uncertain", "uptrend", "uptrend") == "retained_exact"
    assert pair_transition_category("uncertain", "uncertain", "uptrend", "uncertain") == "introduced_harm"
    assert pair_transition_category("uncertain", "uptrend", "uptrend", "uptrend") == "repaired_old_nonexact"
    assert pair_transition_category("uncertain", "uptrend", "downtrend", "uptrend") == "persistent_nonexact"


def test_rescue_topology_is_frozen():
    assert rescue_topology(False, False) == "neither_rescued"
    assert rescue_topology(True, False) == "main_only_rescued"
    assert rescue_topology(False, True) == "other_only_rescued"
    assert rescue_topology(True, True) == "both_rescued"


def test_d1_pair_topology_is_frozen():
    assert d1_pair_topology("uncertain", "uncertain") == "both_uncertain"
    assert d1_pair_topology("uncertain", "range") == "main_uncertain_other_decisive"
    assert d1_pair_topology("downtrend", "uncertain") == "main_decisive_other_uncertain"
    assert d1_pair_topology("uptrend", "uptrend") == "both_decisive"


def test_consensus_margin_uptrend_and_span():
    states = {"full":"uptrend","left":"uptrend","right":"uptrend","both":"uptrend"}
    scores = {"full":0.8,"left":0.7,"right":0.65,"both":0.6}
    out = consensus_margin_and_span(states, scores, "uptrend")
    assert out["consensus_margin_to_frozen_boundary"] == pytest.approx(0.1)
    assert out["support_score_span"] == pytest.approx(0.2)


def test_consensus_margin_range():
    states = {"full":"range","left":"range","right":"range","both":"range"}
    scores = {"full":0.10,"left":0.05,"right":-0.08,"both":0.02}
    out = consensus_margin_and_span(states, scores, "range")
    assert out["consensus_margin_to_frozen_boundary"] == pytest.approx(0.05)
    assert out["support_score_span"] == pytest.approx(0.18)


def test_consensus_margin_fails_closed_on_mixed_states():
    with pytest.raises(ValueError):
        consensus_margin_and_span(
            {"full":"uptrend","left":"uptrend","right":"uncertain","both":"uptrend"},
            {"full":0.8,"left":0.7,"right":0.49,"both":0.6},
            "uptrend",
        )
