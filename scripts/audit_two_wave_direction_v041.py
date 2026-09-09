#!/usr/bin/env python3
"""D1 audit on frozen D0 candidates, plus independent streaming prefix replay."""
from __future__ import annotations
import argparse
import gc
import gzip
import hashlib
import html
import json
import math
import platform
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from run_two_wave_structure_v04 import ROOT,VIEWS,save,export_group
from factor_lab.visual_structure.two_wave.direction_v041 import SCHEMA,audit_d0_direction,TimeDirectionEngine
from factor_lab.visual_structure.two_wave.structure_v04 import ExclusiveLedger
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.frequency_v03 import path_metrics


def replay(raw,view):
    e=TimeDirectionEngine(view)
    for b in raw:e.update(b)
    return e


def prefix_checks(raw,view,ledger):
    result=[]
    for n in sorted({128,1000,len(raw)//2,len(raw)-1}):
        if n>len(raw):continue
        e=replay(raw[:n],view)
        assert e.records==[r for r in ledger.candidates if r['confirmation_bar']<n]
        assert e.ledger.segments==[s for s in ledger.segments if s['known_at_bar']<n]
        assert [s for s in e.ledger.partition(n) if not s['provisional']]==[
            s for s in ledger.partition(len(raw)) if not s['provisional'] and s['known_at_bar']<n]
        result.append({'bars':n,'independent_stream_equal':True,'closed_partition_equal':True})
        del e;gc.collect()
    return result


def perturbation(raw,ledger):
    # Fixed tiny measurement-noise diagnostic, not a search or a new market product.
    rng=np.random.default_rng(20260905);noise=rng.uniform(-1e-6,1e-6,len(raw));modified=[]
    for b,eps in zip(raw,noise):
        modified.append({**b,**{k:b[k]*math.exp(float(eps)) for k in ('open','high','low','close')}})
    e=replay(modified,'5m_offset_0')
    original={tuple(r['five_occurrence_bars']):r for r in ledger.candidates}
    perturbed={tuple(r['five_occurrence_bars']):r for r in e.records}
    common=original.keys()&perturbed.keys()
    selected0={k for k,v in original.items() if v['selected']};selected1={k for k,v in perturbed.items() if v['selected']}
    ans={'log_noise_bound':1e-6,'seed':20260905,'distribution':'uniform, applied to all OHLC of each copied bar',
         'source_data_mutated':False,'used_to_select_parameters':False,'original_candidates':len(original),
         'perturbed_candidates':len(perturbed),'matched_five_pivot_positions':len(common),
         'matched_direction_changes':sum(original[k]['direction']!=perturbed[k]['direction'] for k in common),
         'matched_confirmation_changes':sum(original[k]['confirmation_bar']!=perturbed[k]['confirmation_bar'] for k in common),
         'matched_eligibility_changes':sum(original[k]['scale_eligible']!=perturbed[k]['scale_eligible'] for k in common),
         'original_selected':len(selected0),'perturbed_selected':len(selected1),
         'selected_exact_position_intersection':len(selected0&selected1),
         'selected_exact_position_union':len(selected0|selected1)}
    return ans


def gallery(out,raw,ledger):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder=out/'gallery';folder.mkdir(parents=True,exist_ok=True)
    rows=[r for r in ledger.candidates if r['selected']]
    index=[];body=['<!doctype html><meta charset="utf-8"><title>D1 full published gallery</title>',
         '<h1>D1: every published primary-view pair, in time order</h1>',
         '<p>No success sampling. Grey/blank context is not automatically a range. Shading is retrospective ownership, '
         'not an online regime. Respect effective information time, which is after bar-end in this dataset. '
         'D0 labels are retained. D0 failure/legacy/fixed-date panels remain in the companion v0.4 gallery.</p>']
    x=np.log([b['close'] for b in raw]);er=path_metrics(x,16)['er'];std=pd.Series(er).rolling(128).std(ddof=0).to_numpy()
    for j,r in enumerate(rows):
        name=f'pair_{j:03d}';a=max(0,r['start_bar']-16);b=min(len(raw),r['confirmation_bar']+17)
        pos=np.arange(a,b);idx=r['five_occurrence_bars']
        fig=plt.figure(figsize=(12,4.5));ax=fig.add_subplot(111)
        ax.vlines(pos,[q['low'] for q in raw[a:b]],[q['high'] for q in raw[a:b]],linewidth=.7)
        ax.vlines(pos,[q['open'] for q in raw[a:b]],[q['close'] for q in raw[a:b]],linewidth=2)
        ax.plot(pos,[q['close'] for q in raw[a:b]],linewidth=.6,label='native OHLC / close')
        ax.plot(idx,[raw[i]['close'] for i in idx],'o--',label='five confirmed raw extrema')
        ax.axvspan(r['start_bar']+.5,r['end_bar']+.5,alpha=.15)
        ax.axvline(r['confirmation_bar'],linestyle=':',label='bar-prefix confirmation (not data availability)')
        tick=np.linspace(a,b-1,5,dtype=int);ax.set_xticks(tick)
        ax.set_xticklabels([raw[i]['timestamp'][:16] for i in tick],fontsize=8)
        ax.set_title(f"{name}: D0 {r['source_D0_direction']} -> D1 {r['direction']} | cycles {r['cycle_bars']}\n"
                     f"phase steps {[round(v,3) for v in r['phase_steps']]} | available {r['effective_information_time']}",fontsize=10)
        ax.set_ylabel('CSI1000 index level');ax.set_xlabel('UTC bar end; native-bar spacing')
        ax.legend(fontsize=7);fig.tight_layout();fig.savefig(folder/f'{name}.png',dpi=125);plt.close(fig)
        fig=plt.figure(figsize=(12,2.7));ax=fig.add_subplot(111)
        ax.plot(pos,er[a:b],label='ER16');ax.plot(pos,std[a:b],label='std128(ER16) diagnostic')
        ax.axvline(r['confirmation_bar'],linestyle=':');ax.legend(fontsize=8)
        ax.set_title(name+' | diagnostics only');fig.tight_layout();fig.savefig(folder/f'{name}_ER.png',dpi=125);plt.close(fig)
        index.append({'case':name,'record_id':r['record_id'],'source_D0_record_id':r['source_D0_record_id'],
             'D0':r['source_D0_direction'],'D1':r['direction'],'selection':'all published pairs, chronological',
             'bars_start':a,'bars_stop':b,'effective_information_time':r['effective_information_time']})
        save(folder/f'{name}.json',r)
        body.append(f'<h2>{name}: {html.escape(r["source_D0_direction"])} → {html.escape(r["direction"])}</h2>'
             f'<p>{html.escape(r["record_id"])}</p><img width="1100" src="{name}.png"><img width="1100" src="{name}_ER.png">')
    save(folder/'index.json',index);(folder/'index.html').write_text('\n'.join(body),encoding='utf-8')
    return {'all_selected_pairs_shown':len(index),'independent_human_labels':0}


def phase_overlap(intervals,fine_raw):
    # Mapping labels to EXISTING 1m timestamps is not OHLC resampling.
    clock=pd.DatetimeIndex([b['timestamp'] for b in fine_raw]).asi8
    codes={'range':1,'uptrend':2,'downtrend':3,'uncertain':4};arrays={}
    for view,segs in intervals.items():
        labels=np.zeros(len(clock),dtype=np.int8)
        for s in segs:
            a=np.searchsorted(clock,pd.Timestamp(s['anchor']).value,side='right')
            b=np.searchsorted(clock,pd.Timestamp(s['end']).value,side='right')
            assert not labels[a:b].any()
            labels[a:b]=codes[s['direction']]
        arrays[view]=labels
    base=arrays['5m_offset_0'];out=[]
    for view,other in arrays.items():
        common=(base>0)&(other>0);union=(base>0)|(other>0)
        out.append({'view':view,'comparison_grid':'existing native 1m bar-end timestamps, no price resampling',
            'owned_intersection':int(common.sum()),'owned_union':int(union.sum()),
            'ownership_iou':float(common.sum()/union.sum()) if union.any() else None,
            'direction_agreement_on_owned_intersection':float((base[common]==other[common]).mean()) if common.any() else None,
            'not_accuracy':True})
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();source=Path(args.input);out=Path(args.output)
    if out.exists() and any(out.iterdir()):raise SystemExit('output must be empty')
    out.mkdir(parents=True,exist_ok=True)
    base_manifest=json.loads((source/'run_manifest.json').read_text())
    for path,digest in base_manifest['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    paths=[Path(__file__),ROOT/'src/factor_lab/visual_structure/two_wave/direction_v041.py']
    manifest={'schema':SCHEMA,'python':platform.python_version(),'actual_git_commit':base_manifest['actual_git_commit'],
        'source_sha256':{str(q.relative_to(ROOT)):hashlib.sha256(q.read_bytes()).hexdigest() for q in paths},
        'source_D0_manifest_sha256':hashlib.sha256((source/'run_manifest.json').read_bytes()).hexdigest(),
        'protocol_freeze_commit':'67acf42aea08781ecf7f2aca2e9c126421287760',
        'started_at_utc':datetime.now(timezone.utc).isoformat(),'pnl_computed':False,'fresh_oos':False}
    save(out/'run_manifest.json',manifest);groups=[];intervals={};g=None;pert=None;phases=None
    for view in VIEWS:
        with gzip.open(source/view/'D0/candidates.jsonl.gz','rt',encoding='utf-8') as f:original=[json.loads(line) for line in f]
        ledger=ExclusiveLedger()
        for r in original:
            q=ledger.offer(audit_d0_direction(r))
            assert (q['selected'],q['start_bar'],q['end_bar'],q['confirmation_bar'])==(r['selected'],r['start_bar'],r['end_bar'],r['confirmation_bar'])
        migration=dict(Counter(r['source_D0_direction']+'->'+r['direction'] for r in ledger.candidates if r['selected']))
        del original;gc.collect()
        raw,audit=load_development_bars(ROOT/f'data/development/{view}.parquet',ROOT/'data/manifest.json')
        dest=out/view/'D1';s=export_group(dest,raw,None,ledger,view,'D1',None,False)
        s.update(D0_to_D1_selected=migration,independent_D1_prefix_checks=prefix_checks(raw,view,ledger),
                 D0_ownership_unchanged=True,data_audit=audit)
        save(dest/'summary.json',s);groups.append(s)
        if view.startswith('5m'):
            intervals[view]=[{'anchor':raw[r['start_bar']]['timestamp'],'end':raw[r['end_bar']]['timestamp'],'direction':r['direction']}
                             for r in ledger.candidates if r['selected']]
        if view=='5m_offset_0':g=gallery(out,raw,ledger);pert=perturbation(raw,ledger)
        if view=='1m_official':phases=phase_overlap(intervals,raw)
        del raw,ledger;gc.collect()
    result={'schema':SCHEMA,'status':'morphology_replication_not_yet_accepted','groups':groups,'gallery':g,
        'fixed_primary_perturbation':pert,'phase_ownership_diagnostics':phases,
        'independent_D1_prefix_checks_passed':sum(len(s['independent_D1_prefix_checks']) for s in groups),
        'D0_ownership_changed':False,'pnl_computed':False,'fresh_oos':False,'trade_authority':False,
        'independent_human_reference_count':0,'not_accuracy':True}
    save(out/'summary.json',result)
    assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in manifest['source_sha256'].items())
    manifest.update(finished_at_utc=datetime.now(timezone.utc).isoformat(),source_hashes_unchanged=True)
    save(out/'run_manifest.json',manifest)
    save(out/'output_sha256.json',{str(q.relative_to(out)):hashlib.sha256(q.read_bytes()).hexdigest()
        for q in sorted(out.rglob('*')) if q.is_file() and q.name!='output_sha256.json'})
    print('D1_COMPLETE',result['independent_D1_prefix_checks_passed'],flush=True)


if __name__=='__main__':main()
