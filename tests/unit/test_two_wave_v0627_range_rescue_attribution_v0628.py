from factor_lab.visual_structure.two_wave.v0627_range_rescue_attribution_v0628 import (
    exactness_transition,
    normalized_range_support_dispersion,
    pair_range_topology,
)


def test_exactness_transition_categories_are_frozen():
    assert exactness_transition("range", "range", "range", "range") == "retained_exact"
    assert exactness_transition("uncertain", "uncertain", "range", "uncertain") == "introduced_harm"
    assert exactness_transition("uncertain", "range", "range", "range") == "repaired_v0625_nonexact"
    assert exactness_transition("uncertain", "range", "range", "uptrend") == "persistent_nonexact"


def test_range_topology_distinguishes_both_and_one_sided_rescue():
    assert pair_range_topology("uncertain", "uncertain", "range", "range") == "both_sides_new_range"
    assert pair_range_topology("uncertain", "uncertain", "range", "uncertain") == "main_only_new_range"
    assert pair_range_topology("uncertain", "uncertain", "uncertain", "range") == "other_only_new_range"
    assert pair_range_topology("uncertain", "uptrend", "range", "uptrend") == "one_side_new_range_other_already_decisive"
    assert pair_range_topology("range", "range", "range", "range") == "no_new_range"


def test_range_support_dispersion_uses_frozen_range_scale():
    assert abs(normalized_range_support_dispersion(0.03) - 0.20) < 1e-12
    assert abs(normalized_range_support_dispersion(0.15) - 1.0) < 1e-12
