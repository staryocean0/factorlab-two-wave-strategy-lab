import pytest

from factor_lab.visual_structure.two_wave.d1_huber_rescue_direction_v0622 import rescue_direction


def test_never_overrides_decisive_D1():
    for d1 in ("range", "uptrend", "downtrend"):
        for huber in ("range", "uptrend", "downtrend", "uncertain"):
            out = rescue_direction(d1, huber)
            assert out["classification"] == d1
            assert out["source"] == "D1_primary"
            assert out["D1_decisive_overridden"] is False


def test_huber_rescues_only_D1_uncertain():
    for huber in ("range", "uptrend", "downtrend"):
        out = rescue_direction("uncertain", huber)
        assert out["classification"] == huber
        assert out["source"] == "Huber_rescue"
        assert out["D1_decisive_overridden"] is False


def test_both_uncertain_remains_uncertain():
    out = rescue_direction("uncertain", "uncertain")
    assert out["classification"] == "uncertain"
    assert out["source"] == "abstain"


def test_unknown_label_fails_closed():
    with pytest.raises(ValueError):
        rescue_direction("up", "uptrend")
    with pytest.raises(ValueError):
        rescue_direction("uncertain", "flat")
