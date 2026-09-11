import pytest

from factor_lab.visual_structure.two_wave.phase_balance_residual_attribution_v0638 import (
    phase_balance_transition,
    rescue_origin,
    semantic_class,
)


def test_phase_balance_transition_classes_exact_status_only():
    assert phase_balance_transition(("range", "uncertain"), ("range", "range")) == "phase_balance_repaired_v0635_nonexact"
    assert phase_balance_transition(("range", "range"), ("range", "uncertain")) == "phase_balance_harmed_v0635_exact"
    assert phase_balance_transition(("uptrend", "uptrend"), ("uptrend", "uptrend")) == "both_exact"
    assert phase_balance_transition(("range", "uncertain"), ("uncertain", "range")) == "both_nonexact"


def test_v0637_one_sided_semantic_class_matches_v0636_definition():
    assert semantic_class(("uncertain", "uncertain"), ("range", "uncertain")) == "introduced_harm"
    assert semantic_class(("uncertain", "range"), ("range", "range")) == "repaired_old_nonexact"
    assert semantic_class(("uncertain", "uptrend"), ("range", "uptrend")) == "persistent_nonexact"
    with pytest.raises(ValueError):
        semantic_class(("range", "range"), ("range", "range"))


def test_rescue_origin_distinguishes_shared_from_phase_balance_only():
    assert rescue_origin("uncertain", "range", "range") == "shared_bar_equal_and_phase_balanced_rescue"
    assert rescue_origin("uncertain", "uncertain", "range") == "phase_balanced_only_rescue"
    with pytest.raises(ValueError):
        rescue_origin("uptrend", "uptrend", "uptrend")
