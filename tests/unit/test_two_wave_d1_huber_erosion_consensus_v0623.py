import pytest

import factor_lab.visual_structure.two_wave.d1_huber_erosion_consensus_v0623 as v0623


def test_endpoint_erosion_views_are_exactly_frozen_one_bar_supports():
    views = v0623.endpoint_erosion_anchor_views([10, 14, 22, 28, 35])
    assert views == {
        "full": (10, 14, 22, 28, 35),
        "left_eroded_1": (11, 14, 22, 28, 35),
        "right_eroded_1": (10, 14, 22, 28, 34),
        "both_eroded_1": (11, 14, 22, 28, 34),
    }


def test_erosion_cannot_cross_adjacent_parent_extremum():
    with pytest.raises(ValueError):
        v0623.endpoint_erosion_anchor_views([0, 1, 2, 3, 4])


def test_decisive_D1_is_returned_without_huber_access():
    out = v0623.d1_primary_erosion_consensus_rescue(
        "uptrend", [], [10, 14, 22, 28, 35], 1.0
    )
    assert out["classification"] == "uptrend"
    assert out["decision_source"] == "D1"
    assert out["D1_decisive_overridden"] is False
    assert out["rescue_applied"] is False


def test_uncertain_is_rescued_when_all_four_supports_are_decisive_and_equal():
    closes = [100.0 + i for i in range(40)]
    out = v0623.d1_primary_erosion_consensus_rescue(
        "uncertain", closes, [5, 10, 15, 20, 30], 5.0
    )
    assert out["classification"] == "uptrend"
    assert out["erosion_consensus_state"] == "uptrend"
    assert out["rescue_applied"] is True
    assert set(out["support_states"].values()) == {"uptrend"}


def test_uncertain_remains_uncertain_without_unanimous_support(monkeypatch):
    states = iter(["uptrend", "uptrend", "uncertain", "uptrend"])

    def fake_classifier(*args, **kwargs):
        return {"classification": next(states), "normalized_parent_drift": 0.8}

    monkeypatch.setattr(v0623, "classify_parent_window", fake_classifier)
    out = v0623.d1_primary_erosion_consensus_rescue(
        "uncertain", [100.0] * 40, [5, 10, 15, 20, 30], 5.0
    )
    assert out["classification"] == "uncertain"
    assert out["erosion_consensus_state"] == "uncertain"
    assert out["rescue_applied"] is False


def test_range_consensus_is_a_valid_rescue():
    closes = [100.0] * 40
    out = v0623.d1_primary_erosion_consensus_rescue(
        "uncertain", closes, [5, 10, 15, 20, 30], 5.0
    )
    assert out["classification"] == "range"
    assert out["rescue_applied"] is True


def test_invalid_D1_fails_closed():
    with pytest.raises(ValueError):
        v0623.d1_primary_erosion_consensus_rescue(
            "sideways", [100.0] * 40, [5, 10, 15, 20, 30], 5.0
        )
