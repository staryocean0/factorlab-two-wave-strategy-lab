"""No economic outcomes: grammar, clocks, immutable prefix and known failures."""
import copy
import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from factor_lab.visual_structure.two_wave.same_scale_v04 import (
    ExclusiveLedger, ScaleConfig, TimeEngine, direction_versions, evaluate_pair,
)


def bars_for(values, *, days_gap=0):
    start = datetime(2019, 1, 1, 1, 30, tzinfo=UTC)
    out = []
    for i, price in enumerate(values):
        t = start + timedelta(minutes=5*i, days=days_gap if i >= len(values)//2 else 0)
        out.append({'timestamp': t.isoformat(), 'available_at': (t+timedelta(hours=6)).isoformat(),
                    'open': float(price), 'high': float(price), 'low': float(price), 'close': float(price),
                    'log_close': math.log(float(price))})
    return out


def manual_pair(values=(100, 110, 101, 111, 102), indices=(0, 8, 16, 24, 32), days_gap=0):
    y = np.interp(np.arange(indices[-1]+4), indices, values)
    bars = bars_for(y, days_gap=days_gap)
    points = [{'pivot_id': f'p{i}', 'kind': 'low' if i % 2 == 0 else 'high', 'price': values[i],
               'log_price': math.log(values[i]), 'occurrence_bar': j,
               'occurrence_time': bars[j]['timestamp'], 'confirmation_bar': j+3,
               'confirmation_time': bars[j+3]['timestamp'], 'left_censored': False}
              for i, j in enumerate(indices)]
    return points, bars


def replay(bars, cfg=None):
    e = TimeEngine(cfg)
    for bar in bars:
        e.update(bar)
    return e


@pytest.mark.parametrize('field,value', [('reversal_bars', True), ('min_leg', 2.5), ('amplitude_ratio', .5),
                                        ('duration_ratio', float('nan')), ('max_jump_share', 1.1),
                                        ('min_cycle', 4), ('timeframe', ''), ('max_pair', 1)])
def test_invalid_configuration(field, value):
    with pytest.raises(ValueError):
        ScaleConfig(**{field: value})


@pytest.mark.parametrize('slope', [0, .03, -.03])
def test_complete_periods_and_partition(slope):
    bars = bars_for(100 + 2*np.sin(np.arange(180)*2*np.pi/24) + slope*np.arange(180))
    e = replay(bars)
    assert e.ledger.selected
    for r in e.ledger.selected:
        assert r['scale_qualified'] and len(r['pivot_ids']) == 5 and len(r['cycle_ids']) == 2
        assert min(r['leg_durations']) >= 4
        assert r['confirmation_bar'] >= r['end_bar']+3
        assert r['known_at'] >= r['confirmation_time']
        assert len({p['epoch'] for p in r['points']}) == 1
    owner = np.zeros(len(bars), int)
    for part in e.ledger.partition(len(bars)):
        owner[part['first_bar']:part['last_bar']+1] += 1
    assert np.all(owner == 1)
    for a, b in zip(e.ledger.selected, e.ledger.selected[1:]):
        assert b['start_bar'] >= a['end_bar']


@pytest.mark.parametrize('values', [np.ones(200)*100, np.arange(200)+100,
                                    100+np.arange(200)+.1*np.sin(np.arange(200))])
def test_no_fabricated_cycles_in_constant_or_strong_monotonic_path(values):
    assert replay(bars_for(values)).ledger.records == []


def test_every_prefix_append_invariance_and_copied_outputs():
    bars = bars_for(100+2*np.sin(np.arange(95)*2*np.pi/24))
    e = TimeEngine(); full = replay(bars)
    for i, b in enumerate(bars):
        before = copy.deepcopy(e.ledger.closed_partition)
        returned = e.update(b)
        if returned:
            returned[0]['classification'] = 'tampered'
        oracle = replay(bars[:i+1])
        assert e.ledger.records == oracle.ledger.records
        assert e.pivots == oracle.pivots
        assert e.resets == oracle.resets
        assert e.ledger.events == [v for v in full.ledger.events if v['confirmation_bar'] <= i]
        assert e.ledger.closed_partition[:len(before)] == before
        assert e.ledger.partition(i+1) == oracle.ledger.partition(i+1)


def test_duration_reset_does_not_bridge_chains():
    values = np.r_[100+np.sin(np.arange(80)*2*np.pi/24), np.arange(80)+102,
                   180+np.sin(np.arange(150)*2*np.pi/24)]
    e = replay(bars_for(values)); assert e.resets
    for r in e.ledger.records:
        assert len({p['epoch'] for p in r['points']}) == 1
    for reset in e.resets:
        assert not any(r['start_bar'] < reset['bar'] < r['end_bar'] for r in e.ledger.records)


@pytest.mark.parametrize('steps,spans,wanted', [
    ([-.2335380601, -.2638717691, -.3512174141], [.4974098292, .3512174141], 'downtrend'),
    ([.3, .3, .02], [.6, .02], 'uptrend'),
    ([-.3, -.3, -.02], [.6, .02], 'downtrend'),
    ([.3, -.3, .2], [.3, .2], 'uncertain'),
    ([.01, -.02, .03], [.02, .03], 'range'),
    ([.3, .3, -.2], [.6, .2], 'uncertain'),
])
def test_direction_counterexamples(steps, spans, wanted):
    d = direction_versions(steps, spans, ScaleConfig())
    assert d['D1'] == wanted
    reflected = direction_versions([-x for x in steps], spans, ScaleConfig())
    assert reflected['D1'] == {'uptrend': 'downtrend', 'downtrend': 'uptrend'}.get(wanted, wanted)


def test_historical_d0_false_range_is_preserved_but_d1_fixes_it():
    d = direction_versions([-.2335380601, -.2638717691, -.3512174141], [.4974098292, .3512174141], ScaleConfig())
    assert d['D0'] == 'range' and d['D1'] == 'downtrend' and d['changed_from_D0']


@pytest.mark.parametrize('indices,reason', [((0, 45, 90, 91, 93), 'short_leg'),
                                           ((0, 4, 8, 12, 16), 'short_cycle'),
                                           ((0, 40, 80, 120, 160), 'long_pair'),
                                           ((0, 4, 12, 36, 48), 'cycle_duration_mismatch')])
def test_duration_failures(indices, reason):
    p, b = manual_pair(indices=indices)
    r = evaluate_pair(p, b, ScaleConfig())
    assert reason in r['scale_rejection_reasons'] and r['classification'] == 'not_same_scale'


def test_amplitude_is_chord_residual_not_drift_range():
    p, b = manual_pair(values=(100, 111, 102, 113, 104))
    r = evaluate_pair(p, b, ScaleConfig())
    assert r['detrended_amplitudes_price'] == [10, 10] and r['amplitude_ratio'] == 1
    assert r['scale_qualified']
    p, b = manual_pair(values=(100, 120, 100, 103, 100))
    assert 'amplitude_mismatch' in evaluate_pair(p, b, ScaleConfig())['scale_rejection_reasons']


def test_jump_platform_and_calendar_are_not_cleaned_away():
    p, b = manual_pair(days_gap=15)
    for i in range(1, 8):
        b[i].update(close=100., log_close=math.log(100.))
    r = evaluate_pair(p, b, ScaleConfig())
    assert {'jump_dominated_leg', 'flat_dominated_leg', 'wall_span_too_long'} <= set(r['scale_rejection_reasons'])


def test_all_rejections_not_first_reason_and_unconfirmed_pivot_rejected():
    p, b = manual_pair(indices=(0, 45, 90, 91, 93), days_gap=20)
    r = evaluate_pair(p, b, ScaleConfig())
    assert len(r['scale_rejection_reasons']) >= 4
    p[1]['confirmation_bar'] = len(b)+10
    with pytest.raises(ValueError):
        evaluate_pair(p, b, ScaleConfig())


def test_uncertain_qualified_pair_owns_interval_no_direction_selection():
    p, b = manual_pair(); r = evaluate_pair(p, b, ScaleConfig())
    r['classification'] = 'uncertain'; ledger = ExclusiveLedger(); ledger.add(r)
    second = copy.deepcopy(r); second.update(record_id='later', confirmation_bar=r['confirmation_bar']+1)
    ledger.add(second)
    assert ledger.selected[0]['classification'] == 'uncertain' and len(ledger.selected) == 1
    assert ledger.records[-1]['overlap_suppressed_by'] == r['record_id']
    assert ledger.events[0]['confirmation_bar'] == r['confirmation_bar']
    assert ledger.partition(len(b))[-1]['provisional']


def test_information_clock_uses_prefix_maximum_not_current_bar():
    bars = bars_for(100+2*np.sin(np.arange(100)*2*np.pi/24))
    future = '2030-01-01T00:00:00+00:00'; bars[0]['available_at'] = future
    e = replay(bars)
    assert e.ledger.selected and all(r['known_at'] == future for r in e.ledger.records)


def test_input_validation_does_not_mutate_before_error():
    e = TimeEngine(); b = bars_for([100, 101]); e.update(b[0]); before = copy.deepcopy(e.bars)
    bad = dict(b[1], high=1)
    with pytest.raises(ValueError):
        e.update(bad)
    assert e.bars == before
    with pytest.raises(ValueError):
        e.update(b[0])


def test_qualification_price_rescale_invariance():
    p, b = manual_pair(); a = evaluate_pair(p, b, ScaleConfig())
    for point in p:
        point['price'] *= 10; point['log_price'] = math.log(point['price'])
    for bar in b:
        for key in ('open', 'high', 'low', 'close'):
            bar[key] *= 10
        bar['log_close'] = math.log(bar['close'])
    z = evaluate_pair(p, b, ScaleConfig())
    assert a['classification'] == z['classification']
    assert a['scale_rejection_reasons'] == z['scale_rejection_reasons']
    np.testing.assert_allclose(a['phase_steps_in_amplitude_units'], z['phase_steps_in_amplitude_units'])


def test_post_extremum_backtracking_extreme_is_not_discarded():
    # First establish an up leg; an earlier 100 low precedes the 106 confirmation.
    values = [100, 102, 104, 106, 110, 105, 100, 109, 108, 107, 106, 107, 108, 109]
    e = replay(bars_for(values))
    turns = [(p['kind'], p['occurrence_bar'], p['price']) for p in e.pivots if not p['left_censored']]
    assert turns[:2] == [('high', 4, 110.0), ('low', 6, 100.0)]
    assert e.pivots[-1]['confirmation_bar'] == 13


@pytest.mark.parametrize('change', ['negative_index', 'fake_price', 'invalid_kind', 'backward_clock'])
def test_pair_rejects_fabricated_pivot_inputs(change):
    p, b = manual_pair()
    if change == 'negative_index': p[0]['occurrence_bar'] = -1
    if change == 'fake_price': p[1]['price'] += 1
    if change == 'invalid_kind': p[1]['kind'] = 'other'
    if change == 'backward_clock': p[1]['confirmation_bar'] = 0
    with pytest.raises(ValueError):
        evaluate_pair(p, b, ScaleConfig())
