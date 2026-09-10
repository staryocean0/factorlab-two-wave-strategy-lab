import pytest

from factor_lab.visual_structure.two_wave.v0625_residual_attribution_v0626 import (
    attribution_verdict,
    d1_topology,
    range_relative_margin,
    rescue_topology,
    transition_category,
)


def test_transition_categories_are_exhaustive():
    assert transition_category("uncertain", "uncertain", "uptrend", "uptrend") == "retained_exact"
    assert transition_category("uncertain", "uncertain", "uptrend", "uncertain") == "introduced_harm"
    assert transition_category("uncertain", "uptrend", "uptrend", "uptrend") == "repaired_old_nonexact"
    assert transition_category("uncertain", "uptrend", "uncertain", "uptrend") == "persistent_nonexact"


def test_rescue_and_d1_topologies():
    assert rescue_topology(True, False) == "main_only_rescued"
    assert rescue_topology(False, True) == "other_only_rescued"
    assert rescue_topology(True, True) == "both_rescued"
    assert rescue_topology(False, False) == "neither_rescued"
    assert d1_topology("uncertain", "uncertain") == "both_uncertain"


def test_range_relative_margin_uses_frozen_range_width():
    assert range_relative_margin(0.15) == pytest.approx(1.0)
    assert range_relative_margin(0.10) == pytest.approx(2 / 3)
    with pytest.raises(ValueError):
        range_relative_margin(-0.01)


def test_asymmetry_verdict_requires_both_frozen_gates():
    out = attribution_verdict(0.30, 0.80, ["main_only_rescued"] * 8 + ["both_rescued"] * 2)
    assert out["verdict"] == "v0626_absolute_margin_geometry_is_state_asymmetric"
    assert out["introduced_harm_one_sided_fraction"] == pytest.approx(0.8)

    out = attribution_verdict(0.50, 0.80, ["main_only_rescued"] * 10)
    assert out["verdict"] == "v0626_residual_harm_not_explained_by_margin_geometry"

    out = attribution_verdict(0.30, 0.80, ["main_only_rescued"] * 7 + ["both_rescued"] * 3)
    assert out["verdict"] == "v0626_residual_harm_not_explained_by_margin_geometry"
