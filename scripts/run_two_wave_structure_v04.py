#!/usr/bin/env python3
"""Frozen same-scale grammar, full native development replay, no returns/P&L."""
from __future__ import annotations
import argparse
import csv
import gc
import gzip
import hashlib
import html
import json
import platform
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.candidate_v02 import CandidateConfig
from factor_lab.visual_structure.two_wave.frequency_v031 import DirectionEngine
from factor_lab.visual_structure.two_wave.frequency_v03 import path_metrics
from factor_lab.visual_structure.two_wave.structure_v04 import (
    SCHEMA,ScaleGrammar,ExclusiveLedger,TimeStructureEngine,gate_c1,summarize_ledger)
VIEWS=[f'5m_offset_{i}' for i in range(5)]+['1m_official']


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def jsonlines(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(path,'wt',encoding='utf-8') as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')


def quantile(values):
    if not len(values):return None
    return dict(zip(['min','p50','p90','max'],map(float,np.quantile(values,[0,.5,.9,1]))))


def replay(raw,view,operator,scale=.01):
    if operator=='D0':
        engine=TimeStructureEngine(view)
        for b in raw:engine.update(b)
        return engine,engine.ledger
    engine=DirectionEngine(CandidateConfig(timeframe=view,reversal_log=scale))
    ledger=ExclusiveLedger()
    for b in raw:
        for r in engine.update(b):
            points=engine.source.pivots[-5:]
            assert [p['pivot_id'] for p in points]==r['pivot_ids']
            ledger.offer(gate_c1(r,points,engine.source.bars))
    return engine,ledger


def prefix_oracle(raw,view,operator,scale,full):
    checks=[]
    for n in sorted({min(len(raw),128),min(len(raw),1000),len(raw)//2,len(raw)-1}):
        if n<1:continue
        e,p=replay(raw[:n],view,operator,scale)
        assert p.candidates==[r for r in full.candidates if r['confirmation_bar']<n]
        assert p.segments==[r for r in full.segments if r['known_at_bar']<n]
        sealed=[s for s in p.partition(n) if not s['provisional']]
        final=[s for s in full.partition(len(raw)) if not s['provisional'] and s['known_at_bar']<n]
        assert sealed==final
        checks.append({'bars':n,'candidate_records':len(p.candidates),'selected':len(p.segments),
                       'independent_replay_equal':True,'closed_partition_equal':True})
        del e,p
    return checks


def overlaps(rows,n):
    delta=np.zeros(n+1,dtype=np.int32)
    for r in rows:delta[r['start_bar']]+=1;delta[r['end_bar']+1]-=1
    mult=np.cumsum(delta[:-1]);covered=mult>0
    return {'interval_convention':'inclusive C1 occurrence windows, audit only',
        'histogram':{str(k):int(v) for k,v in Counter(mult.tolist()).items()},
        'mean_multiplicity_all_bars':float(mult.mean()),
        'mean_multiplicity_covered_bars':float(mult[covered].mean()) if covered.any() else None,
        'fraction_bars_multiple_candidates':float((mult>1).mean()),'max':int(mult.max())}


def export_group(out,raw,engine,ledger,view,operator,scale,do_prefix):
    out.mkdir(parents=True,exist_ok=True)
    summary=summarize_ledger(ledger,len(raw))
    summary.update(view=view,operator=operator,reversal_log=scale if operator=='C2G' else None)
    jsonlines(out/'candidates.jsonl.gz',ledger.candidates)
    save(out/'segments.json',ledger.segments);save(out/'partition.json',ledger.partition(len(raw)))
    if operator=='D0':
        jsonlines(out/'pivots.jsonl.gz',engine.pivots);save(out/'resets.json',engine.resets)
        summary['stale_leg_resets']=len(engine.resets)
        summary['raw_confirmed_pivots']=sum(not p['left_censored'] for p in engine.pivots)
    if operator=='C2G':
        summary['C1_all_overlap']=overlaps(ledger.candidates,len(raw))
        summary['C1_definite_overlap']=overlaps([r for r in ledger.candidates if r['direction']!='uncertain'],len(raw))
        summary['C1_counts']=dict(Counter(r['direction'] for r in ledger.candidates))
        summary['C1_span_by_direction']={k:quantile([r['pair_bars'] for r in ledger.candidates if r['direction']==k])
                                       for k in ('range','uptrend','downtrend','uncertain')}
    # Computational bar-prefix confirmation is NOT an as-delivered live signal.
    chosen={r['confirmation_bar']:r for r in ledger.candidates if r['selected']}
    assert len(chosen)==len(ledger.segments)
    availability_delays=[]
    with gzip.open(out/'confirmation_tape.csv.gz','wt',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['bar_index','bar_end','source_available_at',
            'confirmation_record_id','confirmed_pair_direction','effective_information_time',
            'availability_lag_seconds','trade_authority'])
        for i,b in enumerate(raw):
            r=chosen.get(i);info=r['effective_information_time'] if r else None
            delay=(datetime.fromisoformat(info)-datetime.fromisoformat(b['timestamp'])).total_seconds() if r else None
            if r:availability_delays.append(delay)
            w.writerow([i,b['timestamp'],b['available_at'],r['record_id'] if r else '',
                        r['direction'] if r else '',info or '',delay if r else '',False])
    summary['selected_information_lag_seconds']=quantile(availability_delays)
    summary['all_confirmations_available_at_bar_end']=all(d==0 for d in availability_delays) if availability_delays else None
    summary['confirmation_tape_semantics']='bar-prefix event only; respect effective_information_time; no forward filling'
    annual=[]
    for year in sorted({b['trading_day'][:4] for b in raw}):
        rs=[r for r in ledger.candidates if r['selected'] and raw[r['confirmation_bar']]['trading_day'].startswith(year)]
        annual.append({'year':year,'selected':len(rs),'directions':dict(Counter(r['direction'] for r in rs))})
    summary['annual']=annual
    summary['prefix_checks']=prefix_oracle(raw,view,operator,scale,ledger) if do_prefix else []
    save(out/'summary.json',summary)
    print('GROUP_DONE',view,operator,scale,summary['candidates'],summary['selected_pairs'],flush=True)
    return summary


def make_gallery(output,raw,d0,c2g):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder=output/'gallery';folder.mkdir(parents=True,exist_ok=True)
    x=np.log([b['close'] for b in raw]);er=path_metrics(x,16)['er']
    std=pd.Series(er).rolling(128,min_periods=128).std(ddof=0).to_numpy()
    change=pd.Series(er).diff().abs().rolling(128,min_periods=128).mean().to_numpy()
    case_rows=[];specs=[]
    legacy=json.loads((ROOT/'docs/research/two_wave_v04_legacy_cases.json').read_text())
    source={r['source_C1_id']:r for r in c2g.candidates}
    for case in legacy['cases']:
        r=source[case['source_C1_id']]
        assert r['five_occurrence_bars']==case['five_occurrence_bars']
        specs.append(('legacy_'+case['case'],r,'retained legacy sample; no new case selection',None))
        case_rows.append({**case,**{k:r[k] for k in ('cycle_bars','leg_bars','scale_eligible',
            'scale_rejection_reasons','selected','pair_bars','amplitude_ratio','direction')}})
    save(output/'legacy_case_reaudit.json',case_rows)
    for label in ('range','uptrend','downtrend','uncertain'):
        rs=[r for r in d0.candidates if r['selected'] and r['direction']==label]
        for j,r in enumerate(rs[:2]):specs.append((f'D0_selected_{label}_{j}',r,'first two chronological in direction; diagnostic not truth',None))
    for flag in ('short_leg','cycle_duration','leg_time_asymmetry','amplitude_asymmetry',
                 'single_bar_dominance','internal_backtracking','late_confirmation','calendar_span'):
        rs=[r for r in d0.candidates if flag in r['scale_rejection_reasons']]
        if rs:specs.append((f'D0_rejected_{flag}',rs[0],f'earliest candidate with {flag}; diagnostic',None))
    suppressed=[r for r in d0.candidates if r['ownership_rejection']]
    if suppressed:specs.append(('D0_eligible_overlap_suppressed',suppressed[0],'earliest eligible full pair suppressed by ownership',None))
    weak=[r for r in d0.candidates if r['selected'] and r['direction'] in ('uptrend','downtrend') and
          min(abs(v) for v in r['phase_steps'])<=ScaleGrammar().phase_step]
    if weak:specs.append(('D0_weak_third_phase',weak[0],'earliest selected trend with one weak phase; diagnostic',None))
    days=np.array([b['trading_day'][:10] for b in raw])
    # Calendar rules below select review panels ONLY; not runtime states.
    for year in range(2015,2021):
        ids=np.flatnonzero(np.char.startswith(days,str(year)))
        if len(ids):specs.append((f'fixed_{year}_start',None,'first 144 native bars of each development year',(int(ids[0]),min(len(raw),int(ids[0])+144))))
    ids=np.flatnonzero(days=='2018-06-20')
    if len(ids):specs.append(('review_2018_06_20',None,'user-specified conflicting-overlay review date',(max(0,int(ids[0])-48),min(len(raw),int(ids[-1])+49))))
    index=[];body=['<!doctype html><meta charset="utf-8"><title>Two-wave v0.4 audit</title>',
        '<h1>Two-wave same-scale audit: D0 and C2G</h1>',
        '<p>Development data only; neither independent human truth nor trading signals. '
        'Shading shows retrospective (start,end] ownership. Confirmations are not available before recorded information time. '
        'Blank regions are uncovered/pending, not automatically range. ER16 and rolling128 are diagnostics only.</p>']
    for name,r,selection,interval in specs:
        a,b=interval if interval else (max(0,r['start_bar']-16),min(len(raw),r['confirmation_bar']+17))
        fig=plt.figure(figsize=(12,4.5));ax=fig.add_subplot(111)
        positions=np.arange(a,b);close=np.array([v['close'] for v in raw[a:b]])
        ax.vlines(positions,[v['low'] for v in raw[a:b]],[v['high'] for v in raw[a:b]],linewidth=.7)
        ax.vlines(positions,[v['open'] for v in raw[a:b]],close,linewidth=2)
        ax.plot(positions,close,linewidth=.6,label='raw close / OHLC')
        for seg in d0.segments:
            if seg['start']<b and seg['stop']>a:
                lo=max(a,seg['start']);hi=min(b,seg['stop'])
                ax.axvspan(lo-.5,hi-.5,alpha=.15)
                ax.text((lo+hi)/2,.03,'D0 '+seg['label'],transform=ax.get_xaxis_transform(),
                        ha='center',va='bottom',fontsize=7,rotation=30)
        if r:
            idx=r['five_occurrence_bars'];ax.plot(idx,[raw[i]['close'] for i in idx],'o--',label=f"{r['operator']} five real pivots")
            ax.axvline(r['confirmation_bar'],linestyle=':',label='bar-prefix confirmation')
            ax.set_title(f"{name} | {r['direction']} | eligible={r['scale_eligible']} selected={r['selected']}\ncycles={r['cycle_bars']} legs={r['leg_bars']}",fontsize=10)
        else:ax.set_title(f'{name} | native-bar window; only published D0 ownership shaded')
        tick=np.linspace(a,b-1,5,dtype=int);ax.set_xticks(tick)
        ax.set_xticklabels([raw[i]['timestamp'][:16].replace('T',' ') for i in tick],fontsize=8)
        ax.set_ylabel('CSI1000 index level');ax.set_xlabel('UTC bar-end time; native bar spacing')
        ax.legend(loc='best',fontsize=8);fig.tight_layout();fig.savefig(folder/f'{name}.png',dpi=125);plt.close(fig)
        fig=plt.figure(figsize=(12,2.8));ax=fig.add_subplot(111)
        ax.plot(positions,er[a:b],label='ER16');ax.plot(positions,std[a:b],label='std128(ER16), ddof=0')
        ax.plot(positions,change[a:b],label='mean128(abs(delta ER16))')
        if r:ax.axvline(r['confirmation_bar'],linestyle=':')
        ax.set_xticks(tick);ax.set_xticklabels([raw[i]['timestamp'][:16] for i in tick],fontsize=8)
        ax.set_title(name+' | diagnostics only',fontsize=10);ax.legend(fontsize=8);fig.tight_layout()
        fig.savefig(folder/f'{name}_ER.png',dpi=125);plt.close(fig)
        item={'case':name,'selection':selection,'bars_start':a,'bars_stop':b,'record':r,
              'human_reference':False,'future_prices_shown_only_as_review_context':True}
        save(folder/f'{name}.json',item);index.append({k:v for k,v in item.items() if k!='record'})
        body.extend([f'<h2>{html.escape(name)}</h2><p>{html.escape(selection)}</p>',
            f'<p>{html.escape(str(r["scale_rejection_reasons"])) if r else "Fixed window; inspect omissions as well as detections."}</p>',
            f'<img width="1100" src="{name}.png"><img width="1100" src="{name}_ER.png">'])
    save(folder/'index.json',index);(folder/'index.html').write_text('\n'.join(body),encoding='utf-8')
    return {'panels':len(specs),'legacy_cases':len(case_rows),'independent_human_labels':0}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True)
    p.add_argument('--views',nargs='+',default=VIEWS,choices=VIEWS)
    p.add_argument('--skip-prefix',action='store_true');p.add_argument('--skip-gallery',action='store_true')
    args=p.parse_args();out=Path(args.output)
    if out.exists() and any(out.iterdir()):raise SystemExit('output must be empty')
    out.mkdir(parents=True,exist_ok=True)
    paths=[Path(__file__),ROOT/'data/manifest.json',ROOT/'docs/research/two_wave_same_scale_protocol_v04.md',
           ROOT/'docs/research/two_wave_v04_legacy_cases.json',*sorted((ROOT/'src/factor_lab/visual_structure/two_wave').glob('*.py'))]
    hashes={str(q.relative_to(ROOT)):hashlib.sha256(q.read_bytes()).hexdigest() for q in paths}
    try:commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,stderr=subprocess.DEVNULL,text=True).strip()
    except (subprocess.CalledProcessError,FileNotFoundError):commit=None
    manifest={'schema':SCHEMA,'actual_git_commit':commit,'source_sha256':hashes,'python':platform.python_version(),
        'numpy':np.__version__,'pandas':pd.__version__,'protocol_freeze_commit':'6684e599fce98fe638990d01d4aef3ddd56e6abf',
        'started_at_utc':datetime.now(timezone.utc).isoformat(),'grammar':asdict(ScaleGrammar()),
        'views_requested':args.views,'data_role':'development_material','fresh_oos':False,'new_market_data':False,
        'local_resampling':False,'pnl_computed':False,'H1_H2_opened':False,'production_authority':False}
    save(out/'run_manifest.json',manifest);groups=[];audits=[];gallery=None
    for view in args.views:
        raw,audit=load_development_bars(ROOT/f'data/development/{view}.parquet',ROOT/'data/manifest.json');audits.append(audit)
        d0,d0ledger=replay(raw,view,'D0')
        groups.append(export_group(out/view/'D0',raw,d0,d0ledger,view,'D0',None,not args.skip_prefix))
        for scale in (.008,.01,.012):
            eng,ledger=replay(raw,view,'C2G',scale)
            groups.append(export_group(out/view/f'C2G_{scale:g}',raw,eng,ledger,view,'C2G',scale,not args.skip_prefix))
            if view=='5m_offset_0' and scale==.01 and not args.skip_gallery:gallery=make_gallery(out,raw,d0ledger,ledger)
            del eng,ledger;gc.collect()
        del raw,d0,d0ledger;gc.collect()
    result={'schema':SCHEMA,'status':'morphology_replication_not_yet_accepted','primary_view':'5m_offset_0',
        'data_audits':audits,'groups':groups,'gallery':gallery,'independent_human_reference_count':0,
        'prefix_checks_passed':sum(len(g['prefix_checks']) for g in groups),'not_accuracy':True,
        'complete_bar_partition_includes_unknown':True,'online_structure_lifetime_not_implemented':True,
        'H16_W128_is_diagnostic_only':True,'fresh_oos':False,'pnl_computed':False,'trade_authority':False}
    save(out/'summary.json',result)
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items())
    manifest.update(finished_at_utc=datetime.now(timezone.utc).isoformat(),all_input_source_hashes_unchanged=True)
    save(out/'run_manifest.json',manifest)
    save(out/'output_sha256.json',{str(q.relative_to(out)):hashlib.sha256(q.read_bytes()).hexdigest()
        for q in sorted(out.rglob('*')) if q.is_file() and q.name!='output_sha256.json'})
    print('COMPLETE',json.dumps({'groups':len(groups),'prefix_checks':result['prefix_checks_passed'],'status':result['status']}),flush=True)


if __name__=='__main__':main()
