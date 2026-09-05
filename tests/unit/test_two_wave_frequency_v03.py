"""Property tests are not real-market human reference labels."""
import copy
from datetime import UTC, datetime, timedelta
import numpy as np
import pytest
from factor_lab.visual_structure.two_wave.frequency_v03 import (
    DirectionConfig, DirectionEngine, coarse_fine_path, direction_record, path_metrics,
)
from factor_lab.visual_structure.two_wave.candidate_v02 import CandidateConfig, fit_geometry_v02


def fixture(values, times=(0,10,20,30,40)):
    x=np.asarray(values)+4.
    points=[{'pivot_id':f'p{i}','occurrence_bar':t,'confirmation_bar':t+1,'log_price':float(v),'kind':'low' if i%2==0 else 'high'} for i,(t,v) in enumerate(zip(times,x))]
    bars=[{'log_close':float(z)} for z in np.interp(np.arange(times[-1]+1),times,x)]
    g=fit_geometry_v02(points,bars,CandidateConfig())
    s={'pivot_ids':[p['pivot_id'] for p in points], 'cycle_ids':['c1','c2'],
       'structure_id':'test','phase':'low','geometry':g,'classification':g['classification'],
       'attributes':g['attributes'],'timeframe':'5m_offset_0','scale_id':'test_scale',
       'start_bar':0,'end_bar':times[-1],'confirmation_bar':times[-1]+1,
       'confirmation_time':'2015-01-05T02:30:00+00:00','effective_information_time':'2015-01-05T02:30:00+00:00'}
    return s,points,bars


@pytest.mark.parametrize('n',[1,2,12,24])
def test_monotone_efficiency(n):
    x=np.arange(100,dtype=float)
    m=path_metrics(x,n)
    assert np.all(m['er'][n:]==1)
    assert np.isnan(m['er'][:n]).all()
    assert np.allclose(m['signed_rms_slope'][n:],1)
    assert np.all(path_metrics(-x,n)['signed_er'][n:]==-1)


def test_range_constant_and_prefix():
    assert path_metrics(np.array([0.,1.,0.,1.,0.]),4)['er'][-1]==0
    assert np.all(path_metrics(np.ones(40),12)['er'][12:]==0)
    x=np.random.default_rng(20260905).normal(size=200).cumsum()
    for n in (12,24,48):
        all_=path_metrics(x,n)
        for k in (20,75,100):
            part=path_metrics(x[:k],n)
            for key in part:assert np.allclose(part[key],all_[key][:k],equal_nan=True)


@pytest.mark.parametrize('n',[0,-1,True,2.5])
def test_invalid_horizon(n):
    with pytest.raises(ValueError):path_metrics(np.arange(20),n)


def test_nonfinite_rejected():
    with pytest.raises(ValueError):path_metrics(np.array([0.,np.nan]),1)


def test_triangle_and_unmatched_windows():
    f=np.random.default_rng(3).normal(size=1001).cumsum()
    indices=np.arange(0,1001,5);c=f[indices]
    p=coarse_fine_path(f,c,indices,24)
    assert p['valid'].all() and p['all_prices_match'].all()
    assert np.all(p['coarse_er']+1e-10>=p['fine_er'])
    indices[50]=-1
    p=coarse_fine_path(f,c,indices,24)
    assert (~p['valid']).sum()==25


@pytest.mark.parametrize('drift,label',[(0,'range'),(.001,'uptrend'),(-.001,'downtrend')])
def test_clean_directions(drift,label):
    t=np.array([0,10,20,30,40]);s,p,b=fixture(drift*t+np.array([0,.04,0,.04,0]))
    r=direction_record(s,p,b)
    assert r['direction_classification']==label
    assert r['trade_authority'] is False


def test_convergence_does_not_erase_direction():
    s,p,b=fixture([0,.045,.02,.055,.04])
    r=direction_record(s,p,b)
    assert 'converging' in s['attributes']
    assert r['direction_classification']=='uptrend'
    assert r['channel_accepted_by_A'] is False


def test_internal_reversal_not_called_range_or_trend():
    s,p,b=fixture([0,.05,-.015,.052,.012])
    assert direction_record(s,p,b)['direction_classification']=='uncertain'


def test_expanding_flat_center_is_not_forced_direction():
    s,p,b=fixture([0,.03,-.025,.055,-.05])
    r=direction_record(s,p,b)
    assert r['direction_classification']=='uncertain'


def test_unconfirmed_pivots_rejected():
    s,p,b=fixture([0,.04,0,.04,0]);p[-1]['confirmation_bar']=s['confirmation_bar']+1
    with pytest.raises(ValueError):direction_record(s,p,b)


def test_no_future_no_mutation():
    s,p,b=fixture([0,.045,.02,.055,.04]);saved=copy.deepcopy((s,p,b))
    r=direction_record(s,p,b)
    assert r==direction_record(s,p,b+[{'log_close':99}])
    assert (s,p,b)==saved


def stream():
    times=[0,2,3,4,23,24,26,40,55,70,90]
    logs=np.interp(np.arange(91),times,[4.05,4,4.021,4.002,4.041,4.022,4.05,4,4.04,4.01,4.06])
    rows=[]
    for i,x in enumerate(logs):
        t=datetime(2015,1,5,tzinfo=UTC)+timedelta(minutes=5*i);price=float(np.exp(x))
        rows.append({'timestamp':t.isoformat(),'open':price,'high':price,'low':price,'close':price,'available_at':t.isoformat()})
    return rows


def test_every_synthetic_prefix_and_return_copy():
    bars=stream();engine=DirectionEngine();emitted=[]
    for b in bars:emitted.extend(engine.update(b))
    assert emitted==engine.records and len(emitted)>0
    emitted[0]['D']=123
    assert engine.records[0]['D']!=123
    for n in range(1,len(bars)+1):
        e=DirectionEngine()
        for b in bars[:n]:e.update(b)
        assert e.records==[r for r in engine.records if r['confirmation_bar']<n]


def test_source_A_only_and_no_threshold_monotone_waves():
    with pytest.raises(ValueError):DirectionEngine(CandidateConfig(geometry_variant='drift_tolerant'))
    e=DirectionEngine()
    for i,b in enumerate(stream()):
        p=float(np.exp(4+i*.01)); e.update({**b,'open':p,'high':p,'low':p,'close':p})
    assert e.records==[]


@pytest.mark.parametrize('bad',[float('nan'),-1,0,True])
def test_invalid_config(bad):
    with pytest.raises(ValueError):DirectionConfig(phase_step_tolerance=bad)
