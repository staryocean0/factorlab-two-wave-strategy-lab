"""Synthetic hard gates for the frozen v0.5 causal multiscale pre-study."""
from __future__ import annotations

import math

import numpy as np

from factor_lab.visual_structure.two_wave.multiscale_v050 import (
    _pole_for_discrete_geometric_variance,
    build_scale_levels,
    confirmed_extrema,
    default_scale_sigmas,
    scale_space_two_wave_candidates,
    time_causal_scale_space,
    two_wave_candidates,
)


def test_scale_lattice_is_geometric_and_not_the_old_cycle_closure_band():
    sigmas = default_scale_sigmas()
    assert len(sigmas) == 14
    assert math.isclose(sigmas[0], 0.5)
    assert math.isclose(sigmas[-1], 0.5 * math.sqrt(2.0) ** 13)
    assert all(math.isclose(b / a, math.sqrt(2.0)) for a, b in zip(sigmas, sigmas[1:]))
    # 12--48 remains a later qualification/diagnostic grammar.  It is not the
    # scale-space closure rule and was not reused as this scale lattice.
    assert 12.0 not in sigmas
    assert 48.0 not in sigmas


def test_recursive_pole_matches_requested_discrete_kernel_variance():
    for variance in (0.01, 0.25, 1.0, 4.0, 25.0, 400.0):
        pole = _pole_for_discrete_geometric_variance(variance)
        assert 0.0 <= pole < 1.0
        recovered = pole / (1.0 - pole) ** 2
        assert math.isclose(recovered, variance, rel_tol=1e-11, abs_tol=1e-11)
    levels = build_scale_levels((0.5, 1.0, 2.0, 4.0))
    cumulative = 0.0
    for level in levels:
        cumulative += level.added_variance
        assert math.isclose(cumulative, level.sigma_bars**2)


def test_strictly_monotonic_raw_price_cannot_fabricate_two_waves():
    t = np.arange(600, dtype=float)
    paths = [
        100.0 + t,
        500.0 - t,
        # b > A*omega: the sampled raw path is strictly increasing even though
        # a detrended sinusoid exists.  The raw-reversal contract requires zero.
        100.0 + 0.5 * t + np.sin(2.0 * np.pi * t / 32.0),
    ]
    assert np.all(np.diff(paths[-1]) > 0)
    for raw in paths:
        for scale_id, filtered in time_causal_scale_space(raw).items():
            assert confirmed_extrema(filtered, scale_id) == []
        assert all(not records for records in scale_space_two_wave_candidates(raw).values())


def test_nested_parent_child_signal_is_actually_coarsened_across_scales():
    t = np.arange(600, dtype=float)
    raw = 2.0 * np.sin(2.0 * np.pi * t / 48.0) + 0.35 * np.sin(2.0 * np.pi * t / 6.0)
    space = time_causal_scale_space(raw)
    counts = [len(confirmed_extrema(series, scale_id)) for scale_id, series in space.items()]

    # The defining v0.4.4 failure was a nominal parent layer whose median
    # collapsed count was zero.  Here increasing causal scale must really remove
    # fine extrema, not merely delete whole candidate records.
    assert all(a >= b for a, b in zip(counts, counts[1:]))
    assert counts[-1] < counts[0] / 4
    assert counts[-1] >= 5  # the broad parent oscillation was not deleted away

    candidates = scale_space_two_wave_candidates(raw)
    assert candidates[next(reversed(candidates))]


def test_every_candidate_is_two_complete_cycles_at_one_scale():
    t = np.arange(300, dtype=float)
    raw = np.sin(2.0 * np.pi * t / 32.0)
    scale_id, series = next(iter(time_causal_scale_space(raw, (2.0,)).items()))
    extrema = confirmed_extrema(series, scale_id)
    records = two_wave_candidates(extrema)
    assert records
    for record in records:
        assert len(record.extrema) == 5
        assert len({p.scale_id for p in record.extrema}) == 1
        assert [p.kind for p in record.extrema] in (
            ["high", "low", "high", "low", "high"],
            ["low", "high", "low", "high", "low"],
        )
        assert all(duration > 0 for duration in record.cycle_durations)
        assert record.confirmation_index > record.occurrence_indices[-1]


def test_batch_extension_cannot_rewrite_causal_scale_space_or_confirmed_events():
    t = np.arange(500, dtype=float)
    raw = 0.04 * t + 2.0 * np.sin(2.0 * np.pi * t / 40.0) + 0.2 * np.sin(2.0 * np.pi * t / 7.0)
    sigmas = (0.5, 1.0, 2.0, 4.0, 8.0)
    full_space = time_causal_scale_space(raw, sigmas)

    for cut in (125, 250, 375):
        prefix_space = time_causal_scale_space(raw[:cut], sigmas)
        for scale_id, prefix_series in prefix_space.items():
            np.testing.assert_array_equal(prefix_series, full_space[scale_id][:cut])

            prefix_events = confirmed_extrema(prefix_series, scale_id)
            full_confirmed_before_cut = [
                event for event in confirmed_extrema(full_space[scale_id], scale_id)
                if event.confirmation_index < cut
            ]
            assert prefix_events == full_confirmed_before_cut

            prefix_pairs = two_wave_candidates(prefix_events)
            full_pairs_before_cut = [
                pair for pair in two_wave_candidates(full_confirmed_before_cut)
                if pair.confirmation_index < cut
            ]
            assert prefix_pairs == full_pairs_before_cut
