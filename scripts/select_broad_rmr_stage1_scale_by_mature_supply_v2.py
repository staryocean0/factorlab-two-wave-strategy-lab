#!/usr/bin/env python3
"""Outcome-blind one-octave M0 scale selector with temporal maturity gates.

Reads structural occurrence indices and publication confirmation indices only;
no OHLC/price values or future price outcomes are read.
"""
from __future__ import annotations

import argparse, hashlib, json, math
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'cloud_inputs/frozen_research_cache_v065_v0613/published_identities_v065.parquet'
BARS=ROOT/'data/development/5m_offset_0.parquet'
CACHE_SHA='8596622924e92182756162b7bdf0959f6d8ddc2222d6dbc9b4e4379cada9974c'
BARS_SHA='bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48'
VIEW='5m_offset_0'; BUILD_END='2018-12-31'; Y2019='2019-12-31'; Y2020='2020-12-31'
MIN_BUILD=300; MIN_YEAR=75; MIN_CYCLE=12; MAX_CYCLE=48; MAX_PAIR=96

def sha256(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def sigma(level): return 0.5*math.sqrt(2.0)**int(level)

def mature(v):
    if v is None or len(v)!=5: return False
    p=[int(x) for x in v]
    d1=p[2]-p[0]; d2=p[4]-p[2]; span=p[4]-p[0]
    return MIN_CYCLE<=d1<=MAX_CYCLE and MIN_CYCLE<=d2<=MAX_CYCLE and span<=MAX_PAIR

def counts(df, level):
    p=df[(df.level==level)&(df.mature)]
    return {
      'BUILD_2015_2018':int((p.day<=BUILD_END).sum()),
      'CHECK_2019':int(((p.day>BUILD_END)&(p.day<=Y2019)).sum()),
      'CHECK_2020':int(((p.day>Y2019)&(p.day<=Y2020)).sum()),
    }

def gate(c): return c['BUILD_2015_2018']>=MIN_BUILD and c['CHECK_2019']>=MIN_YEAR and c['CHECK_2020']>=MIN_YEAR

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    if sha256(CACHE)!=CACHE_SHA: raise RuntimeError('cache SHA drift')
    if sha256(BARS)!=BARS_SHA: raise RuntimeError('bar SHA drift')
    x=pd.read_parquet(CACHE,columns=['view','publishing_birth_level','publishing_birth_confirmation_bar','published_raw_occurrence_bars'],filters=[('view','==',VIEW)])
    b=pd.read_parquet(BARS,columns=['trading_day']); b['trading_day']=b.trading_day.astype(str)
    idx=x.publishing_birth_confirmation_bar.astype(int)
    if idx.min()<0 or idx.max()>=len(b): raise RuntimeError('confirmation index outside view')
    x=x.copy(); x['day']=b.iloc[idx.to_numpy()].trading_day.to_numpy(); x['level']=x.publishing_birth_level.astype(int); x['mature']=x.published_raw_occurrence_bars.map(mature)
    levels=sorted(int(v) for v in x.level.unique()); inv=[]
    for L in levels:
        F=L-2
        pc=counts(x,L); fc=counts(x,F) if F in levels else {'BUILD_2015_2018':0,'CHECK_2019':0,'CHECK_2020':0}
        inv.append({'parent_level':L,'parent_sigma_bars':sigma(L),'finer_level':F,'finer_sigma_bars':sigma(F) if F>=0 else None,'parent_mature_counts':pc,'finer_mature_counts':fc,'eligible':bool(F in levels and gate(pc) and gate(fc))})
    elig=[r for r in inv if r['eligible']]; sel=min((r['parent_level'] for r in elig),default=None)
    out={'schema_id':'factorlab_broad_rmr_stage1_mature_scale_supply@2.0','research_role':'structural_only_no_price_outcome','primary_view':VIEW,'OHLC_or_price_values_read':False,'future_price_outcomes_read':False,'temporal_maturity':{'min_cycle':MIN_CYCLE,'max_cycle':MAX_CYCLE,'max_pair':MAX_PAIR},'scale_relation':'parent_L_finer_L_minus_2_one_octave','inventory':inv,'selected_parent_level':sel,'selected_parent_sigma_bars':None if sel is None else sigma(sel),'selected_finer_level':None if sel is None else sel-2,'selected_finer_sigma_bars':None if sel is None else sigma(sel-2),'selection_status':'selected' if sel is not None else 'fail_closed_insufficient_mature_supply'}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps({k:out[k] for k in ['selection_status','selected_parent_level','selected_parent_sigma_bars','selected_finer_level','selected_finer_sigma_bars']},sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
