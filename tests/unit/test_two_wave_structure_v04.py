"""Synthetic structure/clock tests; fixtures are not market ground truth."""
from __future__ import annotations
import copy
import itertools
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from factor_lab.visual_structure.two_wave.structure_v04 import (
    ExclusiveLedger, ScaleGrammar, TimeStructureEngine, phase_direction,
    scale_audit, summarize_ledger,
)


def bars(values):
    start = datetime(2019, 1, 2, 1, 35, tzinfo=timezone.utc)
    result = []
    for i, x in enumerate(values):
        t = (start+timedelta(minutes=5*i)).isoformat()
        p = float(np.exp(8+float(x)*.01))
        result.append(dict(timestamp=t, available_at=t, open=p, high=p, low=p, close=p))
    return result


def linear(vertices, lengths):
    return np.concatenate([np.linspace(a, b, n, endpoint=False)
        for a, b, n in zip(vertices, vertices[1:], lengths)] + [[vertices[-1]]])


def audited(vertices=(0, 1, 0, 1, 0), lengths=(8, 8, 8, 8), raw_values=None):
    idx = np.r_[0, np.cumsum(lengths)].tolist()
    values = linear(vertices, lengths) if raw_values is None else raw_values
    raw = bars(list(values)+[values[-1]]*3)
    norm = [{**b, 'log_close':float(np.log(b['close']))} for b in raw]
    points = [dict(occurrence_bar=i, confirmation_bar=i, log_price=norm[i]['log_close'],
                   kind=('low' if j%2 == 0 else 'high')) for j, i in enumerate(idx)]
    return points, norm, idx[-1]+3


def replay(raw, config=None):
    e=TimeStructureEngine(config=config)
    for b in raw: e.update(b)
    return e


@pytest.mark.parametrize('direction,vertices', [
    ('range', [0,1,0,1,0]), ('uptrend',[0,1,.4,1.4,.8]),
    ('downtrend',[0,1,-.4,.6,-.8]),
])
def test_clean_complete_cycles_and_phase_direction(direction, vertices):
    p,b,t=audited(vertices)
    a=scale_audit(p,b,t)
    assert a['scale_eligible']
    assert a['cycle_bars']==[16,16]
    assert phase_direction(p,a)['direction']==direction


@pytest.mark.parametrize('lengths,flag', [
    ((8,8,1,2),'short_leg'), ((8,8,2,3),'cycle_duration'),
    ((10,10,30,30),'period_asymmetry'), ((4,20,20,4),'leg_time_asymmetry'),
    ((60,60,60,60),'pair_duration'),
])
def test_time_failures_are_explicit(lengths,flag):
    p,b,t=audited(lengths=lengths)
    assert flag in scale_audit(p,b,t)['scale_rejection_reasons']


def test_amplitudes_remove_cycle_drift_and_reject_asymmetry():
    p,b,t=audited([0,1,.2,4,.4]); a=scale_audit(p,b,t)
    assert a['amplitude_ratio']>2
    assert 'amplitude_asymmetry' in a['scale_rejection_reasons']
    p,b,t=audited([0,1,.4,1.4,.8]); a=scale_audit(p,b,t)
    assert a['cycle_chord_amplitudes']==pytest.approx([.008,.008])


def test_jump_and_platform_are_not_complete_smooth_legs():
    values=linear([0,1,0,1,0],[8]*4)
    values[:9]=[0,0,0,0,0,0,0,.01,1]
    p,b,t=audited(raw_values=values); a=scale_audit(p,b,t)
    assert 'single_bar_dominance' in a['scale_rejection_reasons']
    assert 'long_exact_plateau' in a['scale_rejection_reasons']


def test_internal_nested_backtracking_is_not_pure_leg():
    values=linear([0,1,0,1,0],[8]*4)
    values[:9]=[0,.9,.1,.9,.1,.9,.1,.9,1]
    p,b,t=audited(raw_values=values)
    assert 'internal_backtracking' in scale_audit(p,b,t)['scale_rejection_reasons']


def test_observed_days_and_week_spans_are_audited():
    p,b,t=audited()
    for i,v in enumerate(b):
        v['timestamp']=(datetime(2019,1,2,tzinfo=timezone.utc)+timedelta(days=i)).isoformat()
    a=scale_audit(p,b,t)
    assert {'calendar_span','too_many_sessions'} <= set(a['scale_rejection_reasons'])


def test_ordinary_weekend_is_not_forbidden_by_week_number():
    p,b,t=audited()
    for i,v in enumerate(b):
        day=4 if i<16 else 7
        v['timestamp']=datetime(2019,1,day,1,35,tzinfo=timezone.utc).isoformat()
    a=scale_audit(p,b,t)
    assert a['observed_sessions']==2 and a['scale_eligible']


def test_weak_neutral_third_step_does_not_veto_clear_downtrend():
    p,b,t=audited([0,1,-.5,.99,-1.]); a=scale_audit(p,b,t)
    assert phase_direction(p,a)['direction']=='downtrend'
    p,b,t=audited([0,1,-.5,1.5,-1.]); a=scale_audit(p,b,t)
    assert phase_direction(p,a)['direction']=='uncertain'


def test_cancelling_phase_migrations_cannot_be_range():
    p,b,t=audited([0,1,.3,1,0])
    assert phase_direction(p,scale_audit(p,b,t))['direction']=='uncertain'


def test_confirmation_delay_not_backdated():
    raw=bars(linear([0,1,0,1,0,1,0,1],[8]*7))
    e=replay(raw)
    assert e.records and any(r['selected'] for r in e.records)
    assert {p['confirmation_bar']-p['occurrence_bar'] for p in e.pivots if not p['left_censored']}=={3}
    assert all(not p['left_censored'] for p in e.pivots if p['pivot_id'] in e.records[0]['pivot_ids'])
    assert {r['phase'] for r in e.records}=={'high','low'}
    assert all(r['confirmation_bar']>r['end_bar'] for r in e.records)


def test_flat_and_monotonic_paths_do_not_force_pivots():
    for values in (np.zeros(180),np.arange(180)*.01):
        e=replay(bars(values))
        assert not e.records
        assert not [p for p in e.pivots if not p['left_censored']]
        assert len(e.resets)>=3


def test_one_complete_cycle_not_two():
    e=replay(bars(linear([0,1,0,1],[8]*3)))
    assert not e.records


def test_every_prefix_on_complete_waves_and_returned_copy_isolation():
    raw=bars(linear([0,1,.2,1.2,.4,1.4,.6,1.6,.8],[8]*8))
    full=replay(raw)
    for n in range(1,len(raw)+1):
        e=replay(raw[:n])
        assert e.records==[r for r in full.records if r['confirmation_bar']<n]
        assert e.pivots==[p for p in full.pivots if p['confirmation_bar']<n]
        assert e.ledger.segments==[s for s in full.ledger.segments if s['known_at_bar']<n]
        p=e.ledger.partition(n)
        assert sum(s['stop']-s['start'] for s in p)==n
    e=TimeStructureEngine()
    for b in raw:
        result=e.update(b)
        if result: result[0]['direction']='tampered'
    assert e.records==full.records


def test_exhaustive_short_sign_prefixes():
    cfg=ScaleGrammar(reversal_run=1,min_leg=1,min_cycle=2)
    for signs in itertools.product((-1,1),repeat=9):
        raw=bars(np.r_[0,np.cumsum(signs)]); full=replay(raw,cfg)
        for n in (4,7,9):
            e=replay(raw[:n],cfg)
            assert e.records==[r for r in full.records if r['confirmation_bar']<n]
            assert e.pivots==[r for r in full.pivots if r['confirmation_bar']<n]


def offer(ledger, a,b,t,label='range',eligible=True):
    return ledger.offer(dict(start_bar=a,end_bar=b,confirmation_bar=t,direction=label,
        scale_eligible=eligible,record_id=str((a,b,t)),scale_rejection_reasons=[],
        pair_bars=b-a,confirmation_delay_bars=t-b))


def test_exclusive_ownership_uses_full_pair_not_later_prettier_label():
    e=ExclusiveLedger()
    assert offer(e,0,32,35,'uncertain')['selected']
    assert not offer(e,8,40,43,'uptrend')['selected']
    assert offer(e,32,64,67,'downtrend')['selected']
    assert [(r['start'],r['stop']) for r in e.segments]==[(1,33),(33,65)]
    s=summarize_ledger(e,70)
    assert s['max_published_ownership_multiplicity']==1 and s['owned_bars']==64
    assert s['direction_counts']=={'uncertain':1,'downtrend':1}
    assert e.partition(70)[-1]['provisional']
    assert e.partition(70)[0]['label']=='uncovered'
    saved=copy.deepcopy(e.segments)
    offer(e,70,102,105)
    assert e.segments[:2]==saved


def test_rejections_do_not_own_occurrence_bars():
    e=ExclusiveLedger(); assert not offer(e,0,32,35,eligible=False)['selected']
    assert offer(e,0,32,36)['selected']
    with pytest.raises(ValueError): offer(e,40,72,30)
    with pytest.raises(ValueError): e.partition(20)


@pytest.mark.parametrize('field,value', [('min_leg',0),('max_pair',-1),('min_leg',1.5),
    ('min_leg',True),('max_period_ratio',.5),('max_step_share',1.1),('drift',float('nan')),
    ('opposite_step',.2),('max_cycle',3)])
def test_bad_config(field,value):
    with pytest.raises(ValueError): ScaleGrammar(**{field:value})


def test_bad_prices_timestamps_and_available_at():
    raw=bars([0,1,0]);e=TimeStructureEngine();e.update(raw[0])
    with pytest.raises(ValueError):e.update(raw[0])
    with pytest.raises(ValueError):e.update({**raw[1],'close':float('nan')})
    with pytest.raises(ValueError):e.update({**raw[1],'available_at':raw[0]['timestamp']})
    assert len(e.bars)==1


def test_late_data_clock_is_preserved():
    raw=bars(linear([0,1,0,1,0,1,0],[8]*6))
    raw[0]['available_at']='2019-01-10T01:35:00+00:00'
    e=replay(raw)
    assert e.records
    assert all(r['effective_information_time']==raw[0]['available_at'] for r in e.records)
