import numpy as np
import pytest

from factor_lab.visual_structure.two_wave.whole_window_huber_direction_v0621 import (
    HUBER_C,
    IRLS_ITERATIONS,
    classify_normalized_parent_drift,
    classify_parent_window,
    huber_centerline_score,
)


def test_frozen_threshold_mapping():
    assert classify_normalized_parent_drift(0.50) == "uptrend"
    assert classify_normalized_parent_drift(-0.50) == "downtrend"
    assert classify_normalized_parent_drift(0.15) == "range"
    assert classify_normalized_parent_drift(-0.15) == "range"
    assert classify_normalized_parent_drift(0.30) == "uncertain"


def test_whole_window_huber_detects_clean_drift():
    closes = np.linspace(100.0, 110.0, 21)
    out = classify_parent_window(closes, [0, 5, 10, 15, 20], amplitude_unit_price=2.0)
    assert out["classification"] == "uptrend"
    assert out["normalized_parent_drift"] > 4.9
    assert out["huber_c"] == HUBER_C
    assert out["irls_iterations"] == IRLS_ITERATIONS
    assert out["future_outcome_used"] is False


def test_huber_centerline_is_robust_to_single_interior_spike():
    base = np.linspace(100.0, 106.0, 25)
    spiked = base.copy()
    spiked[12] += 40.0
    clean = huber_centerline_score(base, [0, 6, 12, 18, 24], 3.0)["normalized_parent_drift"]
    dirty = huber_centerline_score(spiked, [0, 6, 12, 18, 24], 3.0)["normalized_parent_drift"]
    assert clean > 1.9
    assert dirty > 1.5
    assert abs(dirty - clean) < 0.5


def test_uses_complete_parent_window_not_only_five_endpoint_prices():
    # Same five anchor closes, different interior centerline shape.
    anchors = [0, 5, 10, 15, 20]
    a = np.full(21, 100.0)
    b = np.full(21, 100.0)
    for idx in anchors:
        a[idx] = b[idx] = 100.0
    b[1:5] = 99.0
    b[6:10] = 100.0
    b[11:15] = 101.0
    b[16:20] = 102.0
    sa = huber_centerline_score(a, anchors, 1.0)["normalized_parent_drift"]
    sb = huber_centerline_score(b, anchors, 1.0)["normalized_parent_drift"]
    assert abs(sa) < 1e-9
    assert sb > 1.0


def test_invalid_anchor_or_amplitude_fails_closed():
    closes = np.arange(20.0) + 100.0
    with pytest.raises(ValueError):
        huber_centerline_score(closes, [0, 4, 4, 12, 16], 1.0)
    with pytest.raises(ValueError):
        huber_centerline_score(closes, [0, 4, 8, 12, 16], 0.0)
