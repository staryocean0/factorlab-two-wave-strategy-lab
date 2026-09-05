"""D0 false-range regression and D1 streaming invariants."""
import copy
import numpy as np
import pytest
from factor_lab.visual_structure.two_wave.direction_v041 import audit_d0_direction,TimeDirectionEngine
from factor_lab.visual_structure.two_wave.structure_v04 import ScaleGrammar
from test_two_wave_structure_v04 import bars,linear,replay


def record(steps,net=None,label='range'):
    return dict(operator='D0',grammar_hash=ScaleGrammar().config_hash,record_id='fixture',
        phase_steps=steps,phase_spans=[abs(sum(steps[:2])),abs(steps[2])],
        net_drift=sum(steps[:2]) if net is None else net,direction=label)


@pytest.mark.parametrize('sign',[-1,1])
def test_three_clear_phase_steps_do_not_require_net_point_five(sign):
    r=record([sign*.2,sign*.2,sign*.2]);original=copy.deepcopy(r)
    result=audit_d0_direction(r)
    assert result['direction']==('uptrend' if sign==1 else 'downtrend')
    assert result['source_D0_direction']=='range' and result['direction_changed']
    assert r==original


def test_exact_visual_failure_is_retained_and_corrected():
    r=record([-.23353806009678074,-.26387176908689924,-.3512174140865163])
    assert abs(r['net_drift'])<.5
    assert audit_d0_direction(r)['direction']=='downtrend'


@pytest.mark.parametrize('steps,expected',[
    ([.1,.1,.1],'range'),([-.1,-.1,-.1],'range'),([0,0,0],'range'),
    ([.2,-.2,0],'uncertain'),([.2,0,.1],'uncertain'),([.4,.4,-.4],'uncertain'),
])
def test_only_small_all_phase_movement_can_be_range(steps,expected):
    assert audit_d0_direction(record(steps))['direction']==expected


def test_strong_drift_neutral_third_phase_is_preserved():
    assert audit_d0_direction(record([.4,.4,0],label='uptrend'))['direction']=='uptrend'


def test_wrong_source_rejected():
    with pytest.raises(ValueError):audit_d0_direction({**record([0,0,0]),'operator':'C1'})


def test_online_prefixes_and_ownership_identical_to_D0():
    raw=bars(linear([0,1,.2,1.2,.4,1.4,.6,1.6,.8],[8]*8))
    e=TimeDirectionEngine()
    for b in raw:e.update(b)
    d0=replay(raw)
    assert [r['selected'] for r in d0.records]==[r['selected'] for r in e.records]
    assert [(s['start'],s['stop'],s['known_at_bar']) for s in d0.ledger.segments]==[(s['start'],s['stop'],s['known_at_bar']) for s in e.ledger.segments]
    for n in range(1,len(raw)+1):
        q=TimeDirectionEngine()
        for b in raw[:n]:q.update(b)
        assert q.records==[r for r in e.records if r['confirmation_bar']<n]


def test_nextafter_boundary_is_explicit_not_retuned():
    r=record([.15,.15,.15])
    assert audit_d0_direction(r)['direction']=='range'
    r=record([float(np.nextafter(.15,1))]*3)
    assert audit_d0_direction(r)['direction']=='uptrend'
