#!/usr/bin/env python3
"""Frozen broad reversal Stage-1 screen for R1/R2/R3.

Uses only the preselected 5m_offset_0 M0 publication surface, parent birth level 5,
finer level 3, BUILD 2015-2018 and chronological check 2019-2020. No post-2020
rows, PnL, scale search, threshold search or morphology-acceptance claim.
"""
from __future__ import annotations

import argparse, hashlib, json, math, subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'cloud_inputs/frozen_research_cache_v065_v0613/published_identities_v065.parquet'
BARS=ROOT/'data/development/5m_offset_0.parquet'
ADAPTER=ROOT/'docs/governance/reversal_mean_reversion_stage1_event_adapter_v1.json'
CENSOR=ROOT/'docs/governance/reversal_mean_reversion_stage1_partition_censor_v1.json'
CACHE_SHA='8596622924e92182756162b7bdf0959f6d8ddc2222d6dbc9b4e4379cada9974c'
BARS_SHA='bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48'
VIEW='5m_offset_0'; PARENT_LEVEL=5; FINER_LEVEL=3
BUILD_END='2018-12-31'; CHECK_START='2019-01-01'; CHECK_END='2020-12-31'
MIN_CYCLE=12; MAX_CYCLE=48; MAX_PAIR=96; R3_WAIT=192

@dataclass(frozen=True)
class Geo:
    ident:str; phase:str; level:int; conf:int; occ:tuple[int,int,int,int,int]
    day:str; direction:int; amp:float; abs_drift:float; overlap:float; eff:float
    low:float; high:float; failure:float; span:int


def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def git_head():
    try:return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
    except Exception:return None

def mature(occ)->bool:
    if occ is None or len(occ)!=5:return False
    p=[int(x) for x in occ]; d1=p[2]-p[0]; d2=p[4]-p[2]; span=p[4]-p[0]
    return MIN_CYCLE<=d1<=MAX_CYCLE and MIN_CYCLE<=d2<=MAX_CYCLE and span<=MAX_PAIR

def load_inputs():
    if sha256(CACHE)!=CACHE_SHA: raise RuntimeError('cache SHA drift')
    if sha256(BARS)!=BARS_SHA: raise RuntimeError('bar SHA drift')
    adapter=json.loads(ADAPTER.read_text()); censor=json.loads(CENSOR.read_text())
    if adapter['price_outcomes_opened_for_adapter_design'] is not False: raise RuntimeError('adapter not results blind')
    if adapter['scale_binding']['parent_birth_level']!=PARENT_LEVEL or adapter['scale_binding']['finer_birth_level']!=FINER_LEVEL: raise RuntimeError('scale binding drift')
    x=pd.read_parquet(CACHE,columns=['view','canonical_filtered_identity_id','phase','published_raw_occurrence_bars','publishing_birth_level','publishing_birth_confirmation_bar'],filters=[('view','==',VIEW)])
    b=pd.read_parquet(BARS,columns=['trading_day','close'])
    b['trading_day']=b.trading_day.astype(str); b['close']=pd.to_numeric(b.close,errors='coerce')
    if b.empty or b.trading_day.max()>CHECK_END: raise RuntimeError('post-2020 rows present in Stage1 price view')
    if not np.isfinite(b.close.to_numpy(float)).all() or (b.close.to_numpy(float)<=0).any(): raise RuntimeError('invalid close')
    return x,b,adapter,censor

def dedup_level(x,level):
    p=x[(x.publishing_birth_level.astype(int)==level)&x.published_raw_occurrence_bars.map(mature)].copy()
    p['conf']=p.publishing_birth_confirmation_bar.astype(int)
    p=p.sort_values(['conf','canonical_filtered_identity_id'],kind='mergesort').drop_duplicates(['conf'],keep='first').reset_index(drop=True)
    return p

def geometry(row,logp,days)->Geo|None:
    occ=tuple(int(v) for v in row.published_raw_occurrence_bars); conf=int(row.conf)
    if min(occ)<0 or max(occ)>=len(logp) or conf<0 or conf>=len(logp): return None
    z=np.asarray([logp[i] for i in occ],dtype=float)
    r1=float(np.max(z[:3])-np.min(z[:3])); r2=float(np.max(z[2:])-np.min(z[2:])); amp=0.5*(r1+r2)
    if not np.isfinite(amp) or amp<=0 or min(r1,r2)<=0:return None
    drift=float(z[4]-z[0]); direction=1 if drift>0 else -1 if drift<0 else 0
    if direction==0:return None
    lo1,hi1=float(np.min(z[:3])),float(np.max(z[:3])); lo2,hi2=float(np.min(z[2:])),float(np.max(z[2:]))
    inter=max(0.0,min(hi1,hi2)-max(lo1,lo2)); overlap=float(inter/min(r1,r2))
    path=float(np.sum(np.abs(np.diff(z)))); eff=float(abs(drift)/path) if path>0 else np.nan
    phase=str(row.phase)
    if phase not in {'low','high'} or not np.isfinite(eff): return None
    kinds=['low','high','low','high','low'] if phase=='low' else ['high','low','high','low','high']
    target='low' if direction>0 else 'high'; boundary_idx=max(i for i,k in enumerate(kinds) if k==target)
    return Geo(str(row.canonical_filtered_identity_id),phase,int(row.publishing_birth_level),conf,occ,str(days[conf]),direction,amp,float(abs(drift)/amp),overlap,eff,float(np.min(z)),float(np.max(z)),float(z[boundary_idx]),int(occ[4]-occ[0]))

def build_geos(x,b):
    logp=np.log(b.close.to_numpy(float)); days=b.trading_day.to_numpy(str)
    out={}
    for level in (PARENT_LEVEL,FINER_LEVEL):
        rows=dedup_level(x,level); geos=[]
        for _,r in rows.iterrows():
            g=geometry(r,logp,days)
            if g is not None: geos.append(g)
        out[level]=sorted(geos,key=lambda g:(g.conf,g.ident))
    return out,logp,days

def year_end_indices(days):
    out={}
    for i,d in enumerate(days): out[int(str(d)[:4])]=i
    return out

def parent_expiries(parents):
    distinct=sorted(set(g.conf for g in parents)); next_map={}
    for i,c in enumerate(distinct): next_map[c]=distinct[i+1] if i+1<len(distinct) else 10**18
    return {g.ident:min(g.conf+MAX_PAIR,next_map[g.conf]-1) for g in parents}

def first_passage(logp,start,end,positive_boundary,negative_boundary,positive_label,negative_label):
    for j in range(start+1,min(end,len(logp)-1)+1):
        x=float(logp[j])
        if x>=positive_boundary:return positive_label,j
        if x<=negative_boundary:return negative_label,j
    return 'censored',min(end,len(logp)-1)

def eligible_finers(finers,parent,expiry):
    return [f for f in finers if f.conf>parent.conf and f.conf<=expiry and f.occ[0]>parent.conf]

def r1_events(parents,finers,logp,days,year_end):
    exp=parent_expiries(parents); rows=[]
    for p in parents:
        fs=eligible_finers(finers,p,exp[p.ident]); fs=[f for f in fs if f.direction==-p.direction]
        if not fs:continue
        f=min(fs,key=lambda z:(z.conf,z.ident)); event=float(logp[f.conf]); recovery=float(logp[f.occ[0]]); failure=p.failure
        if p.direction>0:
            if not (failure<event<recovery):continue
            pos,neg=recovery,failure; pl,nl='recovery','failure'
        else:
            if not (recovery<event<failure):continue
            pos,neg=failure,recovery; pl,nl='failure','recovery'
        end=min(f.conf+MAX_PAIR,exp[p.ident],year_end[int(f.day[:4])])
        outcome,res=first_passage(logp,f.conf,end,pos,neg,pl,nl)
        sev=float(abs(logp[f.occ[4]]-logp[f.occ[0]])/p.amp)
        rows.append({'day':f.day,'severity':sev,'abs_drift':p.abs_drift,'overlap':p.overlap,'parent_eff':p.eff,'outcome':outcome,'resolve_idx':res})
    return pd.DataFrame(rows)

def r2_events(parents,finers,logp,days,year_end):
    exp=parent_expiries(parents); rows=[]
    for p in parents:
        chosen=None; side=0; dist=0.0; edge=0.0
        for f in eligible_finers(finers,p,exp[p.ident]):
            event=float(logp[f.conf])
            if event>p.high and f.direction>0: chosen=f;side=1;dist=event-p.high;edge=p.high;break
            if event<p.low and f.direction<0: chosen=f;side=-1;dist=p.low-event;edge=p.low;break
        if chosen is None or dist<=0:continue
        event=float(logp[chosen.conf]); ext=event+side*dist
        if side>0: pos,neg=ext,edge; pl,nl='continuation','reentry'
        else: pos,neg=edge,ext; pl,nl='reentry','continuation'
        end=min(chosen.conf+MAX_PAIR,exp[p.ident],year_end[int(chosen.day[:4])])
        outcome,res=first_passage(logp,chosen.conf,end,pos,neg,pl,nl)
        width=p.high-p.low
        if width<=0:continue
        rows.append({'day':chosen.day,'severity':float(dist/width),'abs_drift':p.abs_drift,'overlap':p.overlap,'parent_eff':p.eff,'outcome':outcome,'resolve_idx':res})
    return pd.DataFrame(rows)

def r3_events(parents,logp,days,year_end):
    rows=[]
    ps=parents
    for i,p0 in enumerate(ps[:-1]):
        cur=None
        for p1 in ps[i+1:]:
            if p1.conf<=p0.conf:continue
            if p1.conf-p0.conf>R3_WAIT:break
            if p1.occ[0]>p0.conf and p1.direction==p0.direction: cur=p1;break
        if cur is None:continue
        event=float(logp[cur.conf]); failure=cur.failure; d=abs(event-failure)
        if d<=0:continue
        if cur.direction>0:
            if not failure<event:continue
            pos,neg=event+d,failure;pl,nl='extension','failure'
        else:
            if not event<failure:continue
            pos,neg=failure,event-d;pl,nl='failure','extension'
        end=min(cur.conf+MAX_PAIR,year_end[int(cur.day[:4])])
        outcome,res=first_passage(logp,cur.conf,end,pos,neg,pl,nl)
        rows.append({'day':cur.day,'current_abs_drift':cur.abs_drift,'translation_decay':p0.abs_drift-cur.abs_drift,'quality_decay':0.5*((cur.overlap-p0.overlap)+(p0.eff-cur.eff)),'outcome':outcome,'resolve_idx':res})
    return pd.DataFrame(rows)

def fit_model(train,features,positive):
    d=train[train.outcome.isin([positive, 'failure' if positive in {'recovery','reentry'} else 'extension'])].copy()
    negative='failure' if positive in {'recovery','reentry'} else 'extension'
    d=d[d.outcome.isin([positive,negative])].copy(); d['y']=(d.outcome==positive).astype(int); d=d.replace([np.inf,-np.inf],np.nan).dropna(subset=features+['y'])
    if len(d)<30 or d.y.nunique()<2:return None
    m=Pipeline([('sc',StandardScaler()),('lr',LogisticRegression(C=1.0,penalty='l2',solver='lbfgs',max_iter=1000))]);m.fit(d[features].to_numpy(float),d.y.to_numpy(int));return m

def score(model,data,features,positive,negative):
    d=data[data.outcome.isin([positive,negative])].copy();d['y']=(d.outcome==positive).astype(int);d=d.replace([np.inf,-np.inf],np.nan).dropna(subset=features+['y'])
    if model is None or d.empty:return {'status':'insufficient','n':int(len(d))}
    y=d.y.to_numpy(int);p=model.predict_proba(d[features].to_numpy(float))[:,1]
    return {'status':'scored','n':int(len(d)),'event_rate':float(y.mean()),'brier':float(brier_score_loss(y,p)),'log_loss':float(log_loss(y,p,labels=[0,1]))}

def standardized_coef(model,feature):
    names=list(model.feature_names_in_) if hasattr(model,'feature_names_in_') else None
    return None

def evaluate_lane(df,models,positive,negative,projection=None,gate_counts=(150,50)):
    df=df.copy(); build=df[df.day<=BUILD_END]; check=df[(df.day>=CHECK_START)&(df.day<=CHECK_END)]
    fitted={}; result={'inventory':{},'models':{},'annual':{}}
    resolved=lambda x:x[x.outcome.isin([positive,negative])]
    result['inventory']={'BUILD_resolved':int(len(resolved(build))),'CHECK_2019_resolved':int(len(resolved(check[check.day.str.startswith('2019')]))),'CHECK_2020_resolved':int(len(resolved(check[check.day.str.startswith('2020')])))}
    for name,features in models.items():
        m=fit_model(build,features,positive); fitted[name]=m; result['models'][name]=score(m,check,features,positive,negative)
    for year in ('2019','2020'):
        y=check[check.day.str.startswith(year)];result['annual'][year]={name:score(fitted[name],y,features,positive,negative) for name,features in models.items()}
    return result,fitted

def projection_value(model,features,weights):
    if model is None:return None
    coef=model.named_steps['lr'].coef_[0]; idx={f:i for i,f in enumerate(features)}
    return float(sum(weights[f]*coef[idx[f]] for f in weights))

def gate_r1(res,model):
    inv=res['inventory'];b=res['models']['severity_only'];c=res['models']['parent_plus_severity'];fs=['severity','abs_drift','overlap','parent_eff']
    proj=projection_value(model,fs,{'abs_drift':1,'overlap':-1,'parent_eff':1})
    g={'supply':inv['BUILD_resolved']>=150 and inv['CHECK_2019_resolved']>=50 and inv['CHECK_2020_resolved']>=50,'pooled_brier':c.get('brier',9)<b.get('brier',-9),'pooled_logloss':c.get('log_loss',9)<b.get('log_loss',-9),'both_years_brier':all(res['annual'][y]['parent_plus_severity'].get('brier',9)<res['annual'][y]['severity_only'].get('brier',-9) for y in ('2019','2020')),'integrity_direction':proj is not None and proj>0};return g,proj

def gate_r2(res,model):
    inv=res['inventory'];b=res['models']['excursion_severity_only'];c=res['models']['parent_plus_excursion_state'];fs=['severity','abs_drift','overlap','parent_eff']
    proj=projection_value(model,fs,{'abs_drift':-1,'overlap':1,'parent_eff':-1})
    g={'supply':inv['BUILD_resolved']>=150 and inv['CHECK_2019_resolved']>=50 and inv['CHECK_2020_resolved']>=50,'pooled_brier':c.get('brier',9)<b.get('brier',-9),'pooled_logloss':c.get('log_loss',9)<b.get('log_loss',-9),'both_years_brier':all(res['annual'][y]['parent_plus_excursion_state'].get('brier',9)<res['annual'][y]['excursion_severity_only'].get('brier',-9) for y in ('2019','2020')),'range_direction':proj is not None and proj>0};return g,proj

def gate_r3(res,fitted):
    inv=res['inventory'];out={}
    for cand,feat in [('translation_decay','translation_decay'),('quality_decay','quality_decay')]:
        b=res['models']['baseline'];c=res['models'][cand];m=fitted[cand];features=['current_abs_drift',feat];coef=projection_value(m,features,{feat:1})
        g={'supply':inv['BUILD_resolved']>=100 and inv['CHECK_2019_resolved']>=40 and inv['CHECK_2020_resolved']>=40,'pooled_brier':c.get('brier',9)<b.get('brier',-9),'pooled_logloss':c.get('log_loss',9)<b.get('log_loss',-9),'both_years_brier':all(res['annual'][y][cand].get('brier',9)<res['annual'][y]['baseline'].get('brier',-9) for y in ('2019','2020')),'positive_deterioration':coef is not None and coef>0};out[cand]={'gates':g,'coefficient':coef,'passed':all(g.values())}
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    x,b,adapter,censor=load_inputs(); geos,logp,days=build_geos(x,b); yend=year_end_indices(days)
    parents=geos[PARENT_LEVEL];finers=geos[FINER_LEVEL]
    R1=r1_events(parents,finers,logp,days,yend);R2=r2_events(parents,finers,logp,days,yend);R3=r3_events(parents,logp,days,yend)
    r1_models={'severity_only':['severity'],'parent_integrity_only':['abs_drift','overlap','parent_eff'],'parent_plus_severity':['severity','abs_drift','overlap','parent_eff']}
    r2_models={'excursion_severity_only':['severity'],'parent_range_state_only':['abs_drift','overlap','parent_eff'],'parent_plus_excursion_state':['severity','abs_drift','overlap','parent_eff']}
    r3_models={'baseline':['current_abs_drift'],'translation_decay':['current_abs_drift','translation_decay'],'quality_decay':['current_abs_drift','quality_decay']}
    r1res,r1fit=evaluate_lane(R1,r1_models,'recovery','failure');g1,p1=gate_r1(r1res,r1fit['parent_plus_severity'])
    r2res,r2fit=evaluate_lane(R2,r2_models,'reentry','continuation');g2,p2=gate_r2(r2res,r2fit['parent_plus_excursion_state'])
    r3res,r3fit=evaluate_lane(R3,r3_models,'failure','extension');g3=gate_r3(r3res,r3fit)
    out={'schema_id':'factorlab_broad_rmr_stage1_R1_R2_R3_receipt@1.0','session_date':'2026-09-08','program_identity':'broad_reversal_mean_reversion_discovery_program_v1','code_commit':git_head(),'source':{'structure_cache_sha256':CACHE_SHA,'price_view_sha256':BARS_SHA,'max_day':str(b.trading_day.max()),'post_2020_rows_read':False},'scale':{'parent_level':5,'finer_level':3},'event_inventory':{'parent_mature_dedup':len(parents),'finer_mature_dedup':len(finers)},'R1':{'result':r1res,'projection':p1,'gates':g1,'progression_worthy':all(g1.values())},'R2':{'result':r2res,'projection':p2,'gates':g2,'progression_worthy':all(g2.values())},'R3':{'result':r3res,'candidate_gates':g3,'progression_worthy':any(v['passed'] for v in g3.values())},'scientifically_fresh':False,'morphology_replication_accepted':False,'trading_PnL_used':False,'production_authority':False}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps({'R1':out['R1']['progression_worthy'],'R2':out['R2']['progression_worthy'],'R3':out['R3']['progression_worthy'],'post_2020_rows_read':False},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
