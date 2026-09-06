from __future__ import annotations

import numpy as np
import pytest

from factor_lab.visual_structure.two_wave.parent_translation_v058 import (
    GRID_POINTS_PER_LEG,
    TOTAL_PHASE_POINTS,
    phase_aligned_translation_from_closes,
)


def _path(points, leg_bars):
    if len(points) != 5 or len(leg_bars) != 4:
        raise ValueError
    out = list(np.linspace(points[0], points[1], leg_bars[0] + 1))
    anchors = [0, leg_bars[0]]
    cursor = leg_bars[0]
    for a, b, n in zip(points[1:], points[2:], leg_bars[1:]):
        seg = np.linspace(a, b, n + 1)
        out.extend(seg[1:])
        cursor += n
        anchors.append(cursor)
    return np.asarray(out, dtype=float), anchors


def test_grid_is_frozen_129_points():
    assert GRID_POINTS_PER_LEG == 65
    assert TOTAL_PHASE_POINTS == 129


def test_pure_translation_is_recovered():
    closes, anchors = _path([100.0, 110.0, 102.0, 112.0, 104.0], [8, 8, 8, 8])
    result = phase_aligned_translation_from_closes(closes, anchors, 10.0)
    assert result["translation_raw_price"] == pytest.approx(2.0)
    assert result["translation_in_amplitude_units"] == pytest.approx(0.2)
    assert result["translation_mad_in_amplitude_units"] == pytest.approx(0.0)


def test_phase_allocation_change_without_translation_stays_zero():
    closes, anchors = _path([100.0, 110.0, 100.0, 110.0, 100.0], [4, 13, 15, 6])
    result = phase_aligned_translation_from_closes(closes, anchors, 10.0)
    assert result["translation_raw_price"] == pytest.approx(0.0, abs=1e-12)
    assert result["translation_in_amplitude_units"] == pytest.approx(0.0, abs=1e-12)


def test_translation_survives_phase_allocation_change():
    closes, anchors = _path([100.0, 110.0, 102.0, 112.0, 104.0], [6, 5, 12, 8])
    result = phase_aligned_translation_from_closes(closes, anchors, 10.0)
    assert result["translation_raw_price"] == pytest.approx(2.0)
    assert result["translation_in_amplitude_units"] == pytest.approx(0.2)


def test_single_endpoint_contamination_does_not_control_median_translation():
    closes, anchors = _path([100.0, 110.0, 102.0, 112.0, 104.0], [6, 5, 12, 8])
    closes[anchors[-1]] = 150.0
    result = phase_aligned_translation_from_closes(closes, anchors, 10.0)
    assert result["translation_raw_price"] == pytest.approx(2.0)
    assert abs(result["translation_raw_price"] - 2.0) < abs(150.0 - 104.0) * 0.05


def test_high_start_symmetry_recovers_negative_translation():
    closes, anchors = _path([110.0, 100.0, 108.0, 98.0, 106.0], [7, 4, 11, 9])
    result = phase_aligned_translation_from_closes(closes, anchors, 10.0)
    assert result["translation_raw_price"] == pytest.approx(-2.0)
    assert result["translation_in_amplitude_units"] == pytest.approx(-0.2)


def test_nonfinite_or_invalid_record_is_rejected_not_published():
    closes, anchors = _path([100.0, 110.0, 102.0, 112.0, 104.0], [6, 5, 12, 8])
    bad = closes.copy()
    bad[10] = np.nan
    with pytest.raises(ValueError):
        phase_aligned_translation_from_closes(bad, anchors, 10.0)
    with pytest.raises(ValueError):
        phase_aligned_translation_from_closes(closes, [0, 1, 1, 3, 4], 10.0)
    with pytest.raises(ValueError):
        phase_aligned_translation_from_closes(closes, anchors, 0.0)
