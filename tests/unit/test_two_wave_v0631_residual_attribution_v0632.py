import math

from factor_lab.visual_structure.two_wave.v0631_residual_attribution_v0632 import (
    classify_one_sided_change,
    support_containment_slacks,
    summarize_support_slacks,
)


def test_one_sided_semantic_classes():
    assert classify_one_sided_change(("uncertain", "uncertain"), ("range", "uncertain")) == "introduced_harm"
    assert classify_one_sided_change(("uncertain", "range"), ("range", "range")) == "repaired_old_nonexact"
    assert classify_one_sided_change(("uncertain", "uptrend"), ("range", "uptrend")) == "neutral_nonexact"


def test_support_slack_positive_inside_and_negative_outside():
    inside = support_containment_slacks({
        "cycle1_q25": 0.0, "cycle1_median": 1.0, "cycle1_q75": 2.0,
        "cycle2_q25": 0.5, "cycle2_median": 1.2, "cycle2_q75": 2.5,
    })
    assert inside["support_min_slack"] > 0
    outside = support_containment_slacks({
        "cycle1_q25": 0.0, "cycle1_median": 1.0, "cycle1_q75": 2.0,
        "cycle2_q25": 1.5, "cycle2_median": 1.8, "cycle2_q75": 2.5,
    })
    assert outside["support_min_slack"] < 0


def test_summary_uses_all_four_frozen_supports():
    base = {
        "cycle1_q25": 0.0, "cycle1_median": 1.0, "cycle1_q75": 2.0,
        "cycle2_q25": 0.5, "cycle2_median": 1.2, "cycle2_q75": 2.5,
    }
    details = {name: dict(base) for name in ("full", "left_eroded_1", "right_eroded_1", "both_eroded_1")}
    details["right_eroded_1"]["cycle2_q25"] = 0.95
    out = summarize_support_slacks(details)
    assert out["min_slack_support"] == "right_eroded_1"
    assert math.isfinite(out["min_containment_slack_iqr"])
    assert math.isfinite(out["median_containment_slack_iqr"])
