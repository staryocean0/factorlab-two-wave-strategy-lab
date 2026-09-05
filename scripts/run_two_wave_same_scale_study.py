#!/usr/bin/env python3
"""Reproduce v0.4.2 development-only grammar, packing and failure audit.

This is not an acceptance/accuracy study and never computes future returns.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import platform
import sys
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from factor_lab.visual_structure.two_wave.candidate_v02 import CandidateConfig
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.frequency_v03 import path_metrics
from factor_lab.visual_structure.two_wave.frequency_v031 import DirectionEngine
from factor_lab.visual_structure.two_wave.same_scale_v04 import ScaleConfig, TimeEngine, audit_c1_records

VIEWS = [f'5m_offset_{i}' for i in range(5)] + ['1m_official']


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def lines(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as file:
        with gzip.GzipFile(fileobj=file, mode='wb', mtime=0, filename='') as out:
            for r in records:
                out.write((json.dumps(r, ensure_ascii=False, allow_nan=False, separators=(',', ':'))+'\n').encode())


def quantile(values):
    return {str(q): float(np.quantile(values, q)) for q in (0, .5, .9, 1)} if len(values) else None


def run(bars, cfg):
    e = TimeEngine(cfg)
    for b in bars:
        e.update(b)
    return e


def ledger_summary(ledger, n):
    records, selected = ledger.records, ledger.selected
    partition = ledger.partition(n)
    assert all(a['last_bar']+1 == b['first_bar'] for a, b in zip(partition, partition[1:]))
    assert partition[0]['first_bar'] == 0 and partition[-1]['last_bar'] == n-1
    assert all(r['first_bar'] <= r['last_bar'] for r in partition)
    owned = sum(r['pair_duration'] for r in selected)
    return {'candidates': len(records), 'scale_qualified': sum(r['scale_qualified'] for r in records),
            'selected_disjoint': len(selected), 'overlap_suppressed': sum(bool(r['overlap_suppressed_by']) for r in records),
            'qualified_labels': dict(Counter(r['classification'] for r in records if r['scale_qualified'])),
            'selected_labels': dict(Counter(r['classification'] for r in selected)),
            'owned_bars': owned, 'bars': n, 'owned_fraction_not_accuracy': owned/n,
            'rejection_counts_multilabel': dict(Counter(k for r in records for k in r['scale_rejection_reasons'])),
            'selected_span_quantiles': quantile([r['pair_duration'] for r in selected]),
            'selected_confirmation_delay_quantiles': quantile([r['confirmation_delay_bars'] for r in selected]),
            'selected_effective_delay_minutes': quantile([(pd.Timestamp(r['known_at'])-pd.Timestamp(r['confirmation_time'])).total_seconds()/60 for r in selected]),
            'all_candidate_leg_duration_quantiles': quantile([d for r in records for d in r['leg_durations']]),
            'D0_D1_all_candidate_migration': dict(Counter(r['direction_versions']['D0']+'->'+r['direction_versions']['D1'] for r in records)),
            'D0_D1_selected_migration': dict(Counter(r['direction_versions']['D0']+'->'+r['direction_versions']['D1'] for r in selected)),
            'partition_coverage_all_bars': True, 'partition_max_ownership': 1,
            'selected_by_year': dict(Counter(r['end_time'][:4] for r in selected)),
            'selected_by_phase': dict(Counter(r['phase'] for r in selected)),
            'selected_channel_diagnostic_labels': dict(Counter(r['geometry_log_diagnostic']['classification'] for r in selected)),
            'status': 'morphology_replication_not_yet_accepted'}


def export_ledger(output, ledger, bars):
    lines(output/'candidates.jsonl.gz', ledger.records)
    lines(output/'selected.jsonl.gz', ledger.selected)
    lines(output/'partition.jsonl.gz', ledger.partition(len(bars)))
    lines(output/'confirmation_events.jsonl.gz', ledger.events)
    events = {e['confirmation_bar']: e for e in ledger.events}
    # One explicit row per bar; absent events are not forward-filled as a state.
    lines(output/'online_tape.jsonl.gz', ({'bar_index': i, 'timestamp': b['timestamp'],
                                         'source_available_at': b['available_at'],
                                         'confirmed_event': events.get(i)} for i, b in enumerate(bars)))
    summary = ledger_summary(ledger, len(bars)); save(output/'summary.json', summary)
    return summary


def matched(main, other):
    def keyed(e):
        return {tuple(r['five_occurrence_bars']): r for r in e.ledger.records}
    a, b = keyed(main), keyed(other); common = a.keys() & b.keys()
    return {'exact_five_point_matches': len(common), 'main_unmatched': len(a.keys()-b.keys()),
            'other_unmatched': len(b.keys()-a.keys()),
            'classification_changes_matched': sum(a[k]['classification'] != b[k]['classification'] for k in common),
            'qualification_changes_matched': sum(a[k]['scale_qualified'] != b[k]['scale_qualified'] for k in common),
            'confirmation_changes_matched': sum(a[k]['confirmation_bar'] != b[k]['confirmation_bar'] for k in common),
            'selection_changes_matched': sum(a[k]['selected'] != b[k]['selected'] for k in common)}


def c1_audit(bars, records):
    n = len(bars); difference = np.zeros(n+1, int); kinds = {k: np.zeros(n+1, int) for k in ('uptrend','downtrend','range','uncertain')}
    for r in records:
        a, b = r['start_bar']+1, r['end_bar']+1
        difference[a] += 1; difference[b] -= 1
        kinds[r['direction_classification']][a] += 1; kinds[r['direction_classification']][b] -= 1
    overlap = np.cumsum(difference)[:-1]
    distinct = sum(np.cumsum(v)[:-1] > 0 for v in kinds.values())
    return {'candidates': len(records), 'classification_counts': dict(Counter(r['direction_classification'] for r in records)),
            'candidate_membership_mean_all_bars': float(overlap.mean()), 'candidate_membership_max': int(overlap.max()),
            'fraction_bars_in_multiple_candidates': float(np.mean(overlap > 1)),
            'fraction_bars_in_conflicting_candidate_labels': float(np.mean(distinct > 1)),
            'span_by_class': {k: quantile([r['end_bar']-r['start_bar'] for r in records if r['direction_classification'] == k]) for k in kinds},
            'semantics': 'retrospective_occurrence_intervals_not_online_current_state'}


def compare_parallel_implementation(output, bars, independent):
    """Preserve concurrent ba871b7 D0/D1; compare rather than overwrite it."""
    try:
        from factor_lab.visual_structure.two_wave.direction_v041 import TimeDirectionEngine
        from factor_lab.visual_structure.two_wave.structure_v04 import summarize_ledger
    except ModuleNotFoundError:
        return {'executed': False, 'reason': 'parallel implementation absent in archived local base'}
    legacy = TimeDirectionEngine()
    for bar in bars:
        legacy.update(bar)
    lines(output/'parallel_D1_candidates.jsonl.gz', legacy.records)
    a = {tuple(r['five_occurrence_bars']): r for r in legacy.records}
    b = {tuple(r['five_occurrence_bars']): r for r in independent.ledger.records}
    common = a.keys() & b.keys()
    differences = [{'five_occurrence_bars': list(k), 'parallel_selected': a[k]['selected'],
                    'independent_selected': b[k]['selected'],
                    'parallel_qualified': a[k]['scale_eligible'], 'independent_qualified': b[k]['scale_qualified'],
                    'parallel_label': a[k]['direction'], 'independent_label': b[k]['direction_versions']['D1'],
                    'parallel_confirmation': a[k]['confirmation_bar'], 'independent_confirmation': b[k]['confirmation_bar']}
                   for k in sorted(common) if a[k]['selected'] != b[k]['selected'] or a[k]['scale_eligible'] != b[k]['scale_qualified']
                   or a[k]['direction'] != b[k]['direction_versions']['D1'] or a[k]['confirmation_bar'] != b[k]['confirmation_bar']]
    save(output/'parallel_implementation_differences.json', differences)
    return {'executed': True, 'parallel_baseline_commit': 'ba871b71edc3994c9e611f2451d414bb4f33cfcb',
            'parallel_summary': summarize_ledger(legacy.ledger, len(bars)),
            'exact_five_point_matches': len(common), 'parallel_unmatched': len(a.keys()-b.keys()),
            'independent_unmatched': len(b.keys()-a.keys()), 'matched_difference_count': len(differences),
            'qualification_changes_matched': sum(a[k]['scale_eligible'] != b[k]['scale_qualified'] for k in common),
            'direction_changes_matched': sum(a[k]['direction'] != b[k]['direction_versions']['D1'] for k in common),
            'confirmation_changes_matched': sum(a[k]['confirmation_bar'] != b[k]['confirmation_bar'] for k in common),
            'selection_changes_matched': sum(a[k]['selected'] != b[k]['selected'] for k in common),
            'not_identical_algorithms': ['bootstrap differs: first nonzero move versus three strict moves',
                'pair amplitude/path/direction uses log price in parallel baseline and raw price in independent implementation'],
            'not_accuracy_or_winner_selection': True}


def build_gallery(output, bars, engine, c2ledger, original_cases=None):
    """Failure-stratified examples plus unselected continuous context, not accuracy."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    folder = output/'gallery'; folder.mkdir(parents=True, exist_ok=True)
    cases = []; records = engine.ledger.records
    def pick(tag, pool, count=1):
        for r in pool[:count]:
            cases.append({'tag': tag, 'record': r})
    for label in ('uptrend','downtrend','range','uncertain'):
        pick('D1_selected_'+label, [r for r in records if r['selected'] and r['classification'] == label], 2)
    for reason in ('short_leg','jump_dominated_leg','amplitude_mismatch','corresponding_leg_duration_mismatch','long_pair','wall_span_too_long','inefficient_leg'):
        pool = [r for r in records if reason in r['scale_rejection_reasons']]
        if not pool:
            pool = [r for r in c2ledger.records if reason in r['scale_rejection_reasons']]
        pick('failure_'+reason, pool)
    pick('overlap_suppressed', [r for r in records if r['overlap_suppressed_by']])
    pick('D0_false_range', [r for r in records if r['selected'] and r['direction_versions']['D0'] == 'range' and r['direction_versions']['D1'] != 'range'])
    pick('weak_third_phase', [r for r in records if r['selected'] and r['direction_versions']['D1_reason'] == 'strong_drift_two_phases_no_opposition'])
    mapping = []
    if original_cases:
        lookup = {r['source_C1_record_id']: r for r in c2ledger.records}
        for path in sorted(Path(original_cases).glob('case_*.json')):
            obj = json.loads(path.read_text())
            # Original exports use different nesting across versions; search IDs only.
            text = json.dumps(obj)
            match = next((r for key, r in lookup.items() if key in text), None)
            if match:
                mapping.append({'case': path.name, 'source_C1_record_id': match['source_C1_record_id'],
                                'scale_qualified': match['scale_qualified'], 'rejections': match['scale_rejection_reasons'],
                                'cycle_durations': match['cycle_durations'], 'D1_direction_diagnostic_only': match['direction_versions']['D1'],
                                'C1_direction': match['source_C1_classification']})
                if path.name.startswith(('case_00','case_02','case_06','case_08','case_11','case_14')):
                    cases.append({'tag': 'original_'+path.stem, 'record': match})
    save(output/'original_C1_case_mapping.json', mapping)
    timestamps = pd.to_datetime([b['timestamp'] for b in bars], utc=True)
    for day in ('2018-06-20', '2019-04-15', '2020-07-15'):
        ix = np.where(timestamps.tz_convert('Asia/Shanghai').strftime('%Y-%m-%d') == day)[0]
        if len(ix):
            cases.append({'tag': 'fixed_window_'+day, 'record': None, 'start': max(0, int(ix[0])-48), 'end': min(len(bars)-1, int(ix[-1])+48)})
    x = np.log([b['close'] for b in bars]); er = path_metrics(x,16)['er']
    std = pd.Series(er).rolling(128, min_periods=128).std(ddof=0).to_numpy()
    payload = []; manifest = []
    for number, case in enumerate(cases):
        r = case['record']; tag = f'{number:02d}_'+case['tag']
        a = max(0, r['start_bar']-24) if r else case['start']
        z = min(len(bars)-1, r['confirmation_bar']+24) if r else case['end']
        fig, ax = plt.subplots(figsize=(13,5))
        for j in range(a,z+1):
            b=bars[j]; ax.vlines(j,b['low'],b['high'],linewidth=.6)
            ax.add_patch(Rectangle((j-.3,min(b['open'],b['close'])),.6,max(abs(b['close']-b['open']),.01),fill=b['close']<b['open'],linewidth=.6))
        ax.plot(np.arange(a,z+1), [b['close'] for b in bars[a:z+1]], linewidth=.5, label='close')
        if r:
            ax.plot(r['five_occurrence_bars'], [p['price'] for p in r['points']], 'o-', label='five occurrence extrema (retrospective)')
            ax.axvline(r['confirmation_bar'], linestyle='--', label='calculation confirmation')
            title = f'{tag} | {r["classification"]} | cycles={r["cycle_durations"]} | delay={r["confirmation_delay_bars"]}'
        else:
            title = tag+' | continuous context; no forced wave annotation'
            for s in engine.ledger.selected:
                if s['start_bar'] >= a and s['end_bar'] <= z:
                    ax.axvspan(s['start_bar']+.5,s['end_bar']+.5,alpha=.15)
                    ax.annotate(s['classification'], (s['end_bar'], bars[s['end_bar']]['close']),fontsize=7)
        ax.set_title(title,fontsize=10); ax.set_xlabel(f'Original bar ordinal | {bars[a]["timestamp"]} to {bars[z]["timestamp"]}'); ax.legend(fontsize=7)
        fig.tight_layout(); fig.savefig(folder/f'{tag}.png',dpi=130); plt.close(fig)
        # A separate diagnostic figure uses the same bar coordinates; no scale substitution.
        fig, ax = plt.subplots(figsize=(13,2.6)); ax.plot(np.arange(a,z+1),er[a:z+1],label='ER H16'); ax.plot(np.arange(a,z+1),std[a:z+1],label='ER std W128 ddof0')
        ax.set_ylim(0,1); ax.set_xlabel('Same original bar ordinal'); ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(folder/f'{tag}_ER.png',dpi=110); plt.close(fig)
        local_pivots = [p for p in engine.pivots if a <= p['occurrence_bar'] <= z] if not r or r['source']=='D1' else r['points']
        payload.append({'tag':tag, 'a':a, 'z':z, 'record':r, 'pivots':local_pivots,
                        'bars':[{'i':j, **{k:bars[j][k] for k in ('timestamp','open','high','low','close','available_at')},
                                 'er':float(er[j]) if np.isfinite(er[j]) else None, 'std':float(std[j]) if np.isfinite(std[j]) else None} for j in range(a,z+1)]})
        manifest.append({'tag':tag, 'start_bar':a, 'end_bar':z, 'record_id':r['record_id'] if r else None,
                         'selection':'first chronological within prespecified failure stratum or fixed calendar context; not random independent labels'})
        if r: save(folder/f'{tag}.json',r)
    save(output/'gallery_manifest.json',manifest)
    script = r'''
const cases=PAYLOAD, sel=document.getElementById('case'), cut=document.getElementById('cut');
cases.forEach((x,i)=>sel.add(new Option(x.tag,i)));
function choose(){let c=cases[sel.value];cut.min=c.a;cut.max=c.z;cut.value=c.z;draw()}
function chart(id,bs,indicator){let cv=document.getElementById(id),g=cv.getContext('2d'),w=cv.width,h=cv.height;g.clearRect(0,0,w,h);if(!bs.length)return;
let lo=indicator?0:Math.min(...bs.map(b=>b.low)),hi=indicator?1:Math.max(...bs.map(b=>b.high));let X=i=>45+(i-bs[0].i)/(Math.max(1,bs.at(-1).i-bs[0].i))*(w-65),Y=v=>h-25-(v-lo)/Math.max(.001,hi-lo)*(h-50);
g.strokeRect(45,15,w-65,h-40);g.fillText(hi.toFixed(2),2,20);g.fillText(lo.toFixed(2),2,h-20);
if(indicator){['er','std'].forEach((key,k)=>{g.setLineDash(k?[5,3]:[]);g.beginPath();let started=false;bs.forEach(b=>{if(b[key]!==null){started?g.lineTo(X(b.i),Y(b[key])):g.moveTo(X(b.i),Y(b[key]));started=true}});g.stroke()});g.setLineDash([]);return}
bs.forEach(b=>{g.beginPath();g.moveTo(X(b.i),Y(b.low));g.lineTo(X(b.i),Y(b.high));g.stroke();g.strokeRect(X(b.i)-2,Y(Math.max(b.open,b.close)),4,Math.max(1,Math.abs(Y(b.open)-Y(b.close))))});
let c=cases[sel.value],ps=c.pivots.filter(p=>p.confirmation_bar<=+cut.value&&p.occurrence_bar>=bs[0].i);g.setLineDash([4,3]);g.beginPath();ps.forEach((p,i)=>{i?g.lineTo(X(p.occurrence_bar),Y(p.price)):g.moveTo(X(p.occurrence_bar),Y(p.price))});g.stroke();g.setLineDash([]);ps.forEach(p=>{g.beginPath();g.arc(X(p.occurrence_bar),Y(p.price),4,0,7);g.stroke()});
}
function draw(){let c=cases[sel.value],bs=c.bars.filter(b=>b.i<=+cut.value),r=c.record;chart('price',bs,false);chart('er',bs,true);document.getElementById('clock').textContent='计算截断bar '+cut.value+' / '+bs.at(-1).timestamp+' | 原始available_at '+bs.at(-1).available_at;
document.getElementById('details').textContent=r&&r.confirmation_bar<=+cut.value?JSON.stringify({classification:r.classification,cycles:r.cycle_durations,rejections:r.scale_rejection_reasons,computed_at:r.confirmation_time,effective_information_time:r.known_at,selected:r.selected,source:r.source},null,2):'此截断点尚无该两浪对象的计算确认；不能使用事后类别。';}
sel.onchange=choose;cut.oninput=draw;document.getElementById('prev').onclick=()=>{cut.value=Math.max(+cut.min,+cut.value-1);draw()};document.getElementById('next').onclick=()=>{cut.value=Math.min(+cut.max,+cut.value+1);draw()};choose();
'''
    html = '<!doctype html><meta charset="utf-8"><title>Two-wave v0.4.2 audit replay</title><style>body{font:16px sans-serif;max-width:1250px;margin:24px auto}canvas{width:100%}pre{white-space:pre-wrap}select{max-width:100%}input{width:70%}</style><h1>两浪尺度与分段审查</h1><p>仅2015–2020开发数据。按bar顺序回放，不等于盘中实际可用；供应商available_at原样保留。候选、事后段、确认事件不等于当前状态或交易信号。案例选择使用完整历史，仅供失败诊断，非盲标。</p><select id="case"></select><p><button id="prev">前一根</button> <input id="cut" type="range"> <button id="next">后一根</button></p><p id="clock"></p><canvas id="price" width="1200" height="440"></canvas><p>实线ER H16；虚线ER标准差W128；均非识别器输入。</p><canvas id="er" width="1200" height="180"></canvas><pre id="details"></pre><script>'+script.replace('PAYLOAD',json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('</','<\\/'))+'</script>'
    (output/'replay.html').write_text(html)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--views',nargs='+',default=VIEWS)
    p.add_argument('--c1-root',type=Path);p.add_argument('--skip-sensitivity',action='store_true');p.add_argument('--skip-prefix',action='store_true')
    args=p.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    if not set(args.views) <= set(VIEWS):raise ValueError('only original six views allowed')
    summary={'schema':'two_wave_same_scale_study@0.4.2','data_role':'development_material','fresh_oos':False,
             'status':'morphology_replication_not_yet_accepted','trade_authority':False,'environment':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__},
             'views':{},'prefix_checks':[],'sensitivity':{},'source_sha256':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in [Path(__file__),ROOT/'src/factor_lab/visual_structure/two_wave/same_scale_v04.py',ROOT/'tests/unit/test_two_wave_same_scale_v04.py']}}
    main_bars=main_e=None
    for view in args.views:
        bars,audit=load_development_bars(ROOT/f'data/development/{view}.parquet',ROOT/'data/manifest.json')
        cfg=ScaleConfig(timeframe=view);e=run(bars,cfg);folder=out/view
        result=export_ledger(folder,e.ledger,bars);result.update({'pivots':len(e.pivots),'duration_resets':len(e.resets),'data_audit':audit,'config':asdict(cfg)})
        lines(folder/'pivots.jsonl.gz',e.pivots);lines(folder/'resets.jsonl.gz',e.resets)
        if not args.skip_prefix:
            for fraction in (.25,.5,.75):
                n=int(len(bars)*fraction);prefix=run(bars[:n],cfg)
                expected=[r for r in e.ledger.records if r['confirmation_bar']<n]
                assert prefix.ledger.records==expected
                assert prefix.pivots==[r for r in e.pivots if r['confirmation_bar']<n]
                assert prefix.resets==[r for r in e.resets if r['bar']<n]
                assert prefix.ledger.closed_partition==[r for r in e.ledger.closed_partition if r['confirmation_bar']<n]
                assert prefix.ledger.events==[r for r in e.ledger.events if r['confirmation_bar']<n]
                ledger_summary(prefix.ledger,n)
                summary['prefix_checks'].append({'view':view,'bars':n,'records':len(expected),'passed':True})
        summary['views'][view]=result;save(out/'summary.json',summary)
        print('VIEW_DONE',view,result['candidates'],result['scale_qualified'],result['selected_disjoint'],result['selected_labels'],flush=True)
        if view=='5m_offset_0':main_bars,main_e=bars,e
    if main_e is not None:
        summary['parallel_implementation_comparison'] = compare_parallel_implementation(out, main_bars, main_e)
        summary['C1']={};summary['C2G']={};main_c2=None
        for threshold in (.008,.01,.012):
            source_path=args.c1_root/f'5m_offset_0/reversal_{threshold}/direction_records.jsonl.gz' if args.c1_root else None
            if source_path and source_path.exists():
                with gzip.open(source_path,'rt') as f:records=[json.loads(line) for line in f]
                provenance={'kind':'original_GitHub_C1_artifact_33955675562','source_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest()}
            else:
                source=DirectionEngine(CandidateConfig(timeframe='5m_offset_0',reversal_log=threshold,geometry_variant='detrended_width'))
                for b in main_bars:source.update(b)
                records=source.records;provenance={'kind':'recomputed_unchanged_C1_engine'}
            c2=audit_c1_records(records,main_bars,ScaleConfig());summary['C1'][str(threshold)]={**c1_audit(main_bars,records),'provenance':provenance}
            summary['C2G'][str(threshold)]=export_ledger(out/f'C2G_{threshold}',c2,main_bars)
            lines(out/f'C2G_{threshold}'/'source_C1.jsonl.gz',records)
            if threshold==.01:main_c2=c2
            print('C2G_DONE',threshold,len(c2.selected),flush=True)
        if not args.skip_sensitivity:
            cfg=ScaleConfig();variants={'reversal_2':replace(cfg,reversal_bars=2),'reversal_4':replace(cfg,reversal_bars=4),
                'time_075':replace(cfg,min_leg=3,min_cycle=9,max_cycle=36,max_pair=72,max_unfinished_leg=36,max_confirmation_delay=6),
                'time_125':replace(cfg,min_leg=5,min_cycle=15,max_cycle=60,max_pair=120,max_unfinished_leg=60,max_confirmation_delay=10),
                'amplitude_1.8':replace(cfg,amplitude_ratio=1.8),'amplitude_2.2':replace(cfg,amplitude_ratio=2.2)}
            for name,vcfg in variants.items():
                other=run(main_bars,vcfg);summary['sensitivity'][name]={'config':asdict(vcfg),'summary':ledger_summary(other.ledger,len(main_bars)),'matching':matched(main_e,other)}
                print('SENSITIVITY_DONE',name,flush=True)
            perturbed=[]
            for i,b in enumerate(main_bars):
                factor=1+1e-8*math.sin(i*.731)
                perturbed.append({**b,**{k:b[k]*factor for k in ('open','high','low','close')}})
            pe=run(perturbed,cfg);summary['price_perturbation']={'relative_size':1e-8,'not_written_to_source':True,'matching':matched(main_e,pe),'summary':ledger_summary(pe.ledger,len(perturbed))}
        build_gallery(out,main_bars,main_e,main_c2,args.c1_root/'gallery' if args.c1_root else None)
    save(out/'summary.json',summary)
    print('STUDY_COMPLETE',out,flush=True)


if __name__=='__main__':main()
