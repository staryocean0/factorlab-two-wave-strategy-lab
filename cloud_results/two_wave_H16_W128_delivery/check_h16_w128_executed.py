# EXECUTED SCRATCH SNAPSHOT — audit evidence, not a portable CLI.
# It was run against the locally materialized verified inputs and downloaded C1 artifact.
# See README.md and H16_W128_diagnostic.json for hashes and environment.
"""Supplementary diagnostic only; no recognizer changes or external-study replication claim."""
from pathlib import Path
import gzip, hashlib, json, sys, zipfile
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
HORIZONS=(8,16,32,64)
W=128
LOW=.2; HIGH=.6  # Prior repository diagnostic thresholds, NOT supplied external-AI thresholds.

def er_series(values: np.ndarray,h: int) -> pd.Series:
    x=pd.Series(np.asarray(values,float))
    d=x.diff().abs().rolling(h,min_periods=h).sum()
    v=(x-x.shift(h)).abs().div(d)
    v.loc[d.eq(0)]=0.
    return v.clip(0,1)

def dynamics(er: pd.Series) -> pd.DataFrame:
    state=pd.Series(np.where(er<=LOW,0,np.where(er>=HIGH,2,1)),index=er.index,dtype=float)
    state.loc[er.isna()]=np.nan
    pair=state.notna() & state.shift().notna()
    switch=state.ne(state.shift()).astype(float).where(pair)
    direct=(state.sub(state.shift()).abs()==2).astype(float).where(pair)
    f=pd.DataFrame({'er':er,'local_std128':er.rolling(W,min_periods=W).std(ddof=0),
       'mean_abs_change127':er.diff().abs().rolling(W-1,min_periods=W-1).mean(),
       'state_switch127':switch.rolling(W-1,min_periods=W-1).mean(),
       'direct_extreme_switch127':direct.rolling(W-1,min_periods=W-1).mean(),
       'low_occupancy128':er.le(LOW).astype(float).where(er.notna()).rolling(W,min_periods=W).mean(),
       'high_occupancy128':er.ge(HIGH).astype(float).where(er.notna()).rolling(W,min_periods=W).mean()})
    return f

def summarize(f):
    f=f.dropna()
    return {'n':len(f),**{k:{'mean':float(f[k].mean()),'median':float(f[k].median()),'p10':float(f[k].quantile(.1)),
                           'p90':float(f[k].quantile(.9))} for k in f.columns}}

# Direct loop oracle and prefix checks, independent of rolling implementation.
rng=np.random.default_rng(123)
x=np.cumsum(rng.normal(size=1000))
e=er_series(x,16)
for t in (16,150,300,999):
    expected=abs(x[t]-x[t-16])/abs(np.diff(x[t-16:t+1])).sum()
    assert abs(expected-e.iloc[t])<1e-12
f=dynamics(e)
for t in (143,300,999):
    seq=e.iloc[t-127:t+1].to_numpy()
    assert abs(f.local_std128.iloc[t]-np.std(seq,ddof=0))<1e-12
    assert abs(f.mean_abs_change127.iloc[t]-np.mean(np.abs(np.diff(seq))))<1e-12
for t in (150,300,999):
    pd.testing.assert_frame_equal(dynamics(er_series(x[:t+1],16)),f.iloc[:t+1])

c1=zipfile.ZipFile('/mnt/data/two_wave_frequency_v031_current.zip')
rows=[]; crossings=[]
for path in sorted((ROOT/'inputs').glob('*.parquet')):
    view=path.stem; data=pd.read_parquet(path)
    days=pd.to_datetime(data.trading_day.astype(str)).dt.strftime('%Y-%m-%d')
    years=days.str[:4]
    for basis in ('close','log_close'):
        prices=data.close.to_numpy(float)
        if basis=='log_close':prices=np.log(prices)
        for h in HORIZONS:
            f=dynamics(er_series(prices,h))
            row={'view':view,'basis':basis,'H':h,'W':W,'whole_period':summarize(f),
                 'annual':{year:summarize(f.loc[years==year]) for year in sorted(years.unique())}}
            rows.append(row)
            if h==16 and basis=='close':
                daily=f.assign(day=days).groupby('day').mean().reset_index()
                daily.to_csv(ROOT/f'{view}_H16_W128_daily.csv',index=False)
                name=next(n for n in c1.namelist() if f'/{view}/reversal_0.01/direction_records.jsonl.gz' in n)
                records=[json.loads(s) for s in gzip.decompress(c1.read(name)).decode().splitlines()]
                joined=[]
                for r in records:
                    t=r['confirmation_bar']; a=r['start_bar'];b=r['end_bar']
                    hist=f.iloc[t].to_dict()
                    joined.append({'direction':r['direction_classification'],
                        'confirmed_bar':t,'completed_two_cycle_return_count':b-a,
                        'confirmation_delay_bars':t-b,
                        'channel_accepted_by_A':r['channel_accepted_by_A'],
                        'ER_whole_two_cycles_log':r['path_er'],**hist})
                j=pd.DataFrame(joined)
                j.to_csv(ROOT/f'{view}_C1_at_confirmation_H16W128.csv',index=False)
                c={}
                for label,g in j.groupby('direction'):
                    counts={'n':len(g),'channel_A_accepted':int(g.channel_A_accepted.sum()),
                       'median_completed_two_cycle_return_count':float(g.completed_two_cycle_return_count.median()),
                       'p10_completed_two_cycle_return_count':float(g.completed_two_cycle_return_count.quantile(.1)),
                       'p90_completed_two_cycle_return_count':float(g.completed_two_cycle_return_count.quantile(.9)),
                       'median_confirmation_delay_bars':float(g.confirmation_delay_bars.median()),
                       'median_ER16_at_confirmation':float(g.er.median()),
                       'median_ER_two_cycles_log':float(g.ER_whole_two_cycles_log.median()),
                       'mean_std128_at_confirmation':float(g.local_std128.mean())}
                    c[label]=counts
                crossings.append({'view':view,'scale':.01,'C1_class_vs_H16_diagnostic_only':c})
    print('completed',view,flush=True)
meta={'status':'supplementary_H16_W128_diagnostic_not_recognizer_recalibration',
      'source_range':'2015-01-05 to 2020-12-31, previously used development data',
      'source_data_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'inputs').glob('*.parquet')},
      'H_interpretation':'H price changes, H+1 closes; H16 and W128 cover 143 return intervals and 144 closes',
      'definitions':{'std':'population standard deviation of last 128 ER observations, ddof=0',
       'mean_abs_change':'127 adjacent absolute ER differences within last 128 observations',
       'state_switch_rate':'adjacent changes among low <= .2, mid (.2,.6), high >= .6 divided by 127',
       'direct_extreme_switch_rate':'adjacent low/high swaps only, no skipping intermediate observations, divided by 127',
       'basis':'raw close primary, log close sensitivity; external AI price basis not confirmed',
       'clock':'continuous supplied bar sequence, gaps/lunch/overnight not filled; not wall-clock minutes'},
      'not_identified_from_user': ['external historical/recent split','low/high state thresholds','whether high-low transitions skip intermediate observations','raw or log prices','ddof'],
      'tests':'direct ER oracle, std128 and mean-delta127 oracles, three prefix identity tests passed',
      'statistical_claims':'descriptive only; overlapping windows not independent; no accuracy or future advantage claims',
      'recognizer_modified':False,'repository_modified':False,'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'frequency_results':rows,'recognizer_cross_diagnostics':crossings}
(ROOT/'H16_W128_diagnostic.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
for r in rows:
    if r['basis']=='close' and r['H']==16 and r['view'] in ('1m_official','5m_offset_0'):
        print(r['view'],{k:v for k,v in r['whole_period'].items() if k in ('local_std128','mean_abs_change127','state_switch127','direct_extreme_switch127')})
for c in crossings:
    if c['view']=='5m_offset_0':print('main5 C1',json.dumps(c,ensure_ascii=False,indent=2))
