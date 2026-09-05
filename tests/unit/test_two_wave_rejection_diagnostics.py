"""Tests of rejection arithmetic and concrete non-equivalence counterexamples."""

from __future__ import annotations

import copy
import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from factor_lab.visual_structure.two_wave import Engine, run_bars
from factor_lab.visual_structure.two_wave.diagnostics import (
    REJECTION_RULES,
    counterfactual_removal,
    diagnostic_features,
    rejection_summary,
)
from factor_lab.visual_structure.two_wave.geometry import fit_geometry
from factor_lab.visual_structure.two_wave.models import Config


def make_geometry(times, prices):
    pivots = [
        {"pivot_id": str(i), "occurrence_bar": t, "log_price": x, "kind": "low" if i % 2 == 0 else "high"}
        for i, (t, x) in enumerate(zip(times, prices, strict=True))
    ]
    closes = np.interp(np.arange(times[-1] + 1), times, prices)
    g = fit_geometry(pivots, [{"log_close": float(x)} for x in closes], Config())
    structure = {"pivot_ids": [p["pivot_id"] for p in pivots], "geometry": g}
    return g, diagnostic_features(structure, pivots)


def row(identity, attributes, *, valid=True, d=0.1):
    classification = "uncertain" if attributes or not valid else "range" if abs(d) <= 0.5 else "uptrend" if d > 0 else "downtrend"
    return {
        "run_id": "run",
        "structure_id": identity,
        "attributes": attributes,
        "classification": classification,
        "drift_threshold": 0.5,
        "geometry": {"valid": valid, "D": d, "E": 0.1, "width": 1, "attributes": attributes, "classification": classification},
    }


def test_joint_blockers_require_all_flags_removed_and_preserve_invalid_geometry():
    rows = [
        row("clear", []),
        row("one", ["uneven_phase_drift"], d=0.7),
        row("two", ["uneven_phase_drift", "cycle_amplitude_change"], d=-0.7),
        row("invalid", ["nonpositive_or_tiny_width"], valid=False),
    ]
    before = copy.deepcopy(rows)
    summary = rejection_summary(rows)
    assert summary["structures"] == 4
    assert summary["rules"]["uneven_phase_drift"] == {"triggered": 2, "sole_blocker": 1, "trigger_fraction": 0.5}
    single = summary["single_rule_removals"]["uneven_phase_drift"]
    assert single["recovered_count"] == 1 and single["clear_count_if_flags_removed"] == 2
    both = summary["group_removals"]["local_drift_and_cycle_amplitude"]
    assert both["recovered_count"] == 2
    assert both["recovered_frozen_D_classes_not_truth"] == {"downtrend": 1, "uptrend": 1}
    assert counterfactual_removal(rows, REJECTION_RULES + ("nonpositive_or_tiny_width",))["recovered_count"] == 2
    assert rows == before


def test_no_denominator_is_not_perfect_coverage_and_unknown_flags_fail():
    assert rejection_summary([])["clear_fraction"] is None
    with pytest.raises(ValueError, match="unknown"):
        rejection_summary([row("bad", ["new_unfrozen_rule"])])
    with pytest.raises(ValueError, match="duplicate structure"):
        rejection_summary([row("same", []), row("same", [])])


def test_exact_parallel_constant_width_model_can_trigger_raw_cycle_amplitude_change():
    # Both low-point cycles have the identical slope and channel width, but the
    # second spends 16 bars on its upward leg versus one bar for the first.
    times = [0, 1, 2, 18, 19]
    prices = [8 + 0.001 * t + 0.02 * (i % 2) for i, t in enumerate(times)]
    g, f = make_geometry(times, prices)
    assert g["E"] < 1e-10
    assert g["attributes"] == ["cycle_amplitude_change"]
    assert g["cycle_amplitude_ratio"] == pytest.approx(12 / 7)
    assert f["frozen_drift_removed_amplitude_ratio_diagnostic_only"] == pytest.approx(1)
    assert f["uneven_phase_drift_value"] < 1e-9
    assert g["phase_width_ratio"] == pytest.approx(1)


def test_parallel_channel_amplitude_counterexample_survives_causal_pivot_confirmation():
    times = [0, 1, 2, 18, 19]
    values = [8 + 0.001 * t + 0.02 * (i % 2) for i, t in enumerate(times)]
    # An earlier high establishes a censored initial pivot. The five fixture
    # points are then all usable, and the final rebound confirms the fifth.
    logs = [8.04, *np.interp(np.arange(20), times, values), 8.030]
    start = datetime(2016, 1, 4, 1, 35, tzinfo=UTC)
    bars = []
    for i, x in enumerate(logs):
        price = math.exp(x)
        bars.append({"timestamp": (start + timedelta(minutes=5 * i)).isoformat(),
                     "open": price, "high": price, "low": price, "close": price})
    engine = Engine(Config())
    for bar in bars[:-1]:
        engine.update(bar)
    assert engine.structures == []
    engine.update(bars[-1])
    assert engine.export() == run_bars(bars, Config()).export()
    assert len(engine.structures) == 1
    structure = engine.structures[0]
    assert engine.pivots[0]["left_censored"] is True
    assert [p["occurrence_bar"] for p in engine.pivots[1:]] == [t + 1 for t in times]
    assert structure["end_bar"] == 20 and structure["confirmation_bar"] == 21
    assert structure["attributes"] == ["cycle_amplitude_change"]
    assert structure["geometry"]["D"] == pytest.approx(0.95)
    assert structure["geometry"]["E"] < 1e-10
    assert structure["geometry"]["envelope_coverage"] == 1
    assert structure["geometry"]["cycle_amplitude_ratio"] == pytest.approx(12 / 7)


def test_duration_normalization_changes_with_time_allocation_but_not_time_units():
    prices = [8, 8.04, 8.006, 8.046, 8.012]
    _, equal = make_geometry([0, 2, 4, 6, 8], prices)
    g, unequal = make_geometry([0, 1, 2, 5, 8], prices)
    scaled_g, scaled = make_geometry([0, 3, 6, 15, 24], prices)
    assert equal["uneven_phase_drift_value"] == pytest.approx(0, abs=1e-10)
    assert unequal["uneven_phase_drift_value"] > 0
    assert scaled["uneven_phase_drift_value"] == pytest.approx(unequal["uneven_phase_drift_value"])
    assert scaled_g["D"] == pytest.approx(g["D"])
    assert scaled_g["E"] == pytest.approx(g["E"])


def test_five_point_error_decomposition_for_irregular_times_and_curved_phases():
    g, features = make_geometry([0, 3, 4, 10, 17], [8, 8.04, 8.01, 8.06, 8.025])
    assert math.isclose(features["E_reconstructed"], g["E"], abs_tol=1e-12)
    assert 0 < features["curvature_share_of_pivot_SSE"] < 1
