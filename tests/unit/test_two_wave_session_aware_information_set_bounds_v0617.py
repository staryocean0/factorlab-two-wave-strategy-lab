from __future__ import annotations

import inspect
import itertools

import numpy as np
import pytest

from factor_lab.visual_structure.two_wave.session_aware_information_set_bounds_v0617 import (
    EXPECTED_DATASET_VERSION,
    bar_tv_upper_variable,
    session_aware_concentration_bounds,
    validate_source_identity,
    validate_transition_topology,
)
from factor_lab.visual_structure.two_wave.step_count_normalized_concentration_v0613 import (
    concentration_profile,
)


def fine_metrics(path):
    x = np.abs(np.diff(np.asarray(path, dtype=float)))
    s = float(x.sum())
    j = float(x.max() / s)
    return j, concentration_profile(x)


def test_variable_bar_tv_upper_matches_explicit_vertices_m1_to_m6():
    c0, low, high, close = 10.0, 8.0, 13.0, 11.0
    for m in range(1, 7):
        got = bar_tv_upper_variable(c0, low, high, close, m)
        if m == 1:
            assert got == abs(close - c0)
            continue
        vals = []
        for hidden in itertools.product((low, high), repeat=m - 1):
            path = (c0,) + hidden + (close,)
            vals.append(sum(abs(b - a) for a, b in zip(path, path[1:])))
        assert got == max(vals)


def test_random_variable_step_fully_enveloped_paths_are_covered():
    rng = np.random.default_rng(17)
    highs = np.asarray([10.0, 13.0, 15.0])
    lows = np.asarray([9.0, 8.0, 10.0])
    closes = np.asarray([10.0, 11.0, 14.0])
    support = [6, 5]
    bounds = session_aware_concentration_bounds(highs, lows, closes, support, [0, 0])
    assert bounds["bound_class"] == "fully_enveloped_bound"
    assert bounds["fine_step_count"] == 11

    for _ in range(100):
        path = [closes[0]]
        for j, m in zip((1, 2), support):
            path.extend(rng.uniform(lows[j], highs[j], m - 1).tolist())
            path.append(closes[j])
        j_value, profile = fine_metrics(path)
        assert bounds["j_low"] - 1e-12 <= j_value <= bounds["j_high"] + 1e-12
        for key, lo, hi in (
            ("c_inf", "c_inf_low", "c_inf_high"),
            ("c_1", "c_1_low", "c_1_high"),
            ("c_2", "c_2_low", "c_2_high"),
        ):
            assert bounds[lo] - 1e-12 <= profile[key] <= bounds[hi] + 1e-12


def test_unenveloped_source_gap_forces_universal_bound_without_deleting_leg():
    bounds = session_aware_concentration_bounds(
        [10.0, 13.0, 15.0],
        [9.0, 8.0, 10.0],
        [10.0, 11.0, 14.0],
        [6, 5],
        [4, 0],
    )
    assert bounds["defined"] is True
    assert bounds["bound_class"] == "structural_gap_universal_bound"
    assert bounds["gap_source_count_total"] == 4
    assert bounds["fine_step_count"] == 15
    assert bounds["j_low"] == pytest.approx(1.0 / 15.0)
    assert bounds["j_high"] == 1.0
    cap = np.log(15.0)
    assert bounds["c_inf_low"] == 0.0 and bounds["c_inf_high"] == pytest.approx(cap)
    assert bounds["c_1_low"] == 0.0 and bounds["c_1_high"] == pytest.approx(cap)
    assert bounds["c_2_low"] == 0.0 and bounds["c_2_high"] == pytest.approx(cap)


def test_arbitrary_positive_path_is_covered_by_structural_gap_universal_bound():
    bounds = session_aware_concentration_bounds(
        [10.0, 13.0], [9.0, 8.0], [10.0, 11.0], [6], [3]
    )
    path = [10.0, 100.0, 3.0, 50.0, 9.0, 10.0, 8.5, 12.0, 9.5, 11.0]
    assert len(path) - 1 == bounds["fine_step_count"]
    j_value, profile = fine_metrics(path)
    assert bounds["j_low"] - 1e-12 <= j_value <= bounds["j_high"] + 1e-12
    assert bounds["c_inf_low"] - 1e-12 <= profile["c_inf"] <= bounds["c_inf_high"] + 1e-12
    assert bounds["c_1_low"] - 1e-12 <= profile["c_1"] <= bounds["c_1_high"] + 1e-12
    assert bounds["c_2_low"] - 1e-12 <= profile["c_2"] <= bounds["c_2_high"] + 1e-12


def test_zero_source_row_session_elapsed_time_does_not_create_fake_gap():
    a = session_aware_concentration_bounds(
        [10.0, 13.0], [9.0, 8.0], [10.0, 11.0], [5], [0]
    )
    assert a["bound_class"] == "fully_enveloped_bound"
    assert a["gap_transition_count"] == 0


def test_actual_discarded_source_row_creates_gap_class():
    topo = validate_transition_topology(
        ["2020-01-02T13:01:00Z", "2020-01-02T13:02:00Z"],
        ["2020-01-02T11:27:00Z"],
    )
    assert topo["transition_class"] == "contains_unenveloped_source_gap"
    assert topo["support_source_count"] == 2
    assert topo["gap_source_count"] == 1


def test_transition_topology_rejects_overlap_and_duplicates():
    with pytest.raises(ValueError):
        validate_transition_topology(["a", "b"], ["b"])
    with pytest.raises(ValueError):
        validate_transition_topology(["a", "a"], [])


def test_transition_topology_exact_partition_rejects_missing_or_unexpected_rows():
    expected = ["2020-01-02T09:31:00Z", "2020-01-02T09:32:00Z", "2020-01-02T09:33:00Z"]
    topo = validate_transition_topology(
        ["2020-01-02T09:32:00Z", "2020-01-02T09:33:00Z"],
        ["2020-01-02T09:31:00Z"],
        expected,
    )
    assert topo["support_source_count"] == 2
    assert topo["gap_source_count"] == 1

    with pytest.raises(ValueError, match="not an exact source-row partition"):
        validate_transition_topology(
            ["2020-01-02T09:32:00Z", "2020-01-02T09:33:00Z"],
            [],
            expected,
        )

    with pytest.raises(ValueError, match="not an exact source-row partition"):
        validate_transition_topology(
            ["2020-01-02T09:32:00Z", "2020-01-02T09:33:00Z", "2020-01-02T09:34:00Z"],
            ["2020-01-02T09:31:00Z"],
            expected,
        )


def test_positive_price_scaling_preserves_dimensionless_bounds():
    args = ([10.0, 13.0, 15.0], [9.0, 8.0, 10.0], [10.0, 11.0, 14.0], [6, 5], [0, 0])
    a = session_aware_concentration_bounds(*args)
    b = session_aware_concentration_bounds(
        np.asarray(args[0]) * 10,
        np.asarray(args[1]) * 10,
        np.asarray(args[2]) * 10,
        args[3],
        args[4],
    )
    for key in (
        "j_low", "j_high", "c_inf_low", "c_inf_high",
        "c_1_low", "c_1_high", "c_2_low", "c_2_high",
    ):
        assert abs(a[key] - b[key]) < 1e-12


def test_m1_transition_is_exact_and_supported():
    b = session_aware_concentration_bounds(
        [10.0, 11.0], [9.0, 10.0], [10.0, 11.0], [1], [0]
    )
    assert b["fine_step_count"] == 1
    assert b["j_low"] == b["j_high"] == 1.0
    assert b["c_inf_low"] == b["c_inf_high"] == 0.0
    assert b["c_1_low"] == b["c_1_high"] == 0.0
    assert b["c_2_low"] == b["c_2_high"] == 0.0


def test_source_identity_gate_accepts_only_frozen_datahub_surface():
    good = {
        "symbol": "000852.SH",
        "source_kind": "market_index_transaction_derived_1m",
        "dataset_version": EXPECTED_DATASET_VERSION,
        "source_rows": 349923,
        "date_range": ["2015-01-05", "2020-12-31"],
        "future_2021_plus_rows_loaded": 0,
    }
    validate_source_identity(good)
    bad = dict(good)
    bad["source_rows"] = 350561
    with pytest.raises(ValueError):
        validate_source_identity(bad)


def test_zero_possible_movement_is_explicit_undefined_for_fully_enveloped_leg():
    b = session_aware_concentration_bounds([1.0, 1.0], [1.0, 1.0], [1.0, 1.0], [5], [0])
    assert b["defined"] is False
    assert b["reason"] == "no_positive_hidden_movement_possible"


def test_closed_leg_prefix_locality_and_no_outcome_authority():
    a = session_aware_concentration_bounds(
        [10.0, 13.0, 15.0], [9.0, 8.0, 10.0], [10.0, 11.0, 14.0], [6, 5], [0, 0]
    )
    b = session_aware_concentration_bounds(
        [10.0, 13.0, 15.0], [9.0, 8.0, 10.0], [10.0, 11.0, 14.0], [6, 5], [0, 0]
    )
    assert a == b
    text = repr(a)
    assert "oracle" not in text
    assert "counterpart" not in text
    assert "direction" not in text
    assert a["future_outcome_used"] is False
    assert a["trade_authority"] is False


def test_bound_api_signature_excludes_forbidden_fine_or_outcome_inputs():
    params = set(inspect.signature(session_aware_concentration_bounds).parameters)
    assert params == {
        "highs",
        "lows",
        "closes",
        "support_source_counts",
        "gap_source_counts",
    }
    forbidden = {"source_prices", "fine_prices", "oracle", "counterpart", "direction", "outcome", "pnl"}
    assert params.isdisjoint(forbidden)
