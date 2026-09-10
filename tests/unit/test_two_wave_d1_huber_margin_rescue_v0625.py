import pytest

import factor_lab.visual_structure.two_wave.d1_huber_margin_rescue_v0625 as v0625


def test_margin_threshold_is_exactly_frozen():
    assert v0625.MIN_CONSENSUS_MARGIN == 0.10


def test_decisive_D1_is_never_overridden():
    out = v0625.d1_primary_margin_rescue("range", [], [10, 14, 22, 28, 35], 1.0)
    assert out["classification"] == "range"
    assert out["decision_source"] == "D1"
    assert out["D1_decisive_overridden"] is False
    assert out["rescue_applied"] is False


def test_uncertain_without_v0623_consensus_remains_uncertain(monkeypatch):
    monkeypatch.setattr(
        v0625,
        "erosion_consensus_huber_state",
        lambda *args, **kwargs: {
            "erosion_consensus_state": "uncertain",
            "support_states": {"full":"uptrend","left_eroded_1":"uptrend","right_eroded_1":"uncertain","both_eroded_1":"uptrend"},
            "support_scores": {"full":0.8,"left_eroded_1":0.7,"right_eroded_1":0.49,"both_eroded_1":0.6},
            "future_outcome_used": False,
            "trade_authority": False,
        },
    )
    out = v0625.d1_primary_margin_rescue("uncertain", [100.0]*40, [5,10,15,20,30], 5.0)
    assert out["classification"] == "uncertain"
    assert out["margin_gate_pass"] is False


def test_exact_margin_point_one_passes(monkeypatch):
    monkeypatch.setattr(
        v0625,
        "erosion_consensus_huber_state",
        lambda *args, **kwargs: {
            "erosion_consensus_state": "uptrend",
            "support_states": {k:"uptrend" for k in ("full","left_eroded_1","right_eroded_1","both_eroded_1")},
            "support_scores": {"full":0.8,"left_eroded_1":0.7,"right_eroded_1":0.65,"both_eroded_1":0.6},
            "future_outcome_used": False,
            "trade_authority": False,
        },
    )
    out = v0625.d1_primary_margin_rescue("uncertain", [100.0]*40, [5,10,15,20,30], 5.0)
    assert out["consensus_margin_to_frozen_boundary"] == pytest.approx(0.10)
    assert out["margin_gate_pass"] is True
    assert out["classification"] == "uptrend"


def test_margin_below_point_one_is_withheld(monkeypatch):
    monkeypatch.setattr(
        v0625,
        "erosion_consensus_huber_state",
        lambda *args, **kwargs: {
            "erosion_consensus_state": "uptrend",
            "support_states": {k:"uptrend" for k in ("full","left_eroded_1","right_eroded_1","both_eroded_1")},
            "support_scores": {"full":0.8,"left_eroded_1":0.7,"right_eroded_1":0.65,"both_eroded_1":0.599},
            "future_outcome_used": False,
            "trade_authority": False,
        },
    )
    out = v0625.d1_primary_margin_rescue("uncertain", [100.0]*40, [5,10,15,20,30], 5.0)
    assert out["consensus_margin_to_frozen_boundary"] == pytest.approx(0.099)
    assert out["margin_gate_pass"] is False
    assert out["classification"] == "uncertain"


def test_invalid_D1_fails_closed():
    with pytest.raises(ValueError):
        v0625.d1_primary_margin_rescue("sideways", [100.0]*40, [5,10,15,20,30], 5.0)
