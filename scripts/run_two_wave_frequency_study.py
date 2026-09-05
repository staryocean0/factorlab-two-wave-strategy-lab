#!/usr/bin/env python3
"""Five-minute primary research; one-minute diagnostics, never P&L optimization."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import platform
import sys
import subprocess
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from factor_lab.visual_structure.two_wave.frequency_v03 import (DirectionEngine, coarse_fine_path, describe_er, path_metrics)
from factor_lab.visual_structure.two_wave.candidate_v02 import CandidateConfig
from factor_lab.visual_structure.two_wave.data import audit_frame, load_development_bars

VIEWS = ['1m_official'] + [f'5m_offset_{i}' for i in range(5)]


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def scope_masks(frame, n, minutes):
    days = frame.trading_day.astype(str).to_numpy()
    stamp = frame.timestamp.astype('int64').to_numpy()
    idx = np.arange(len(frame)); starts = np.maximum(0, idx-n)
    breaks = np.r_[0, np.cumsum(np.diff(stamp) > minutes*60*1e9*1.01)]
    warm = idx >= n
    return {'continuous': warm, 'within_day': warm & (days == days[starts]),
            'within_session': warm & (breaks == breaks[starts])}


def persistence(frame, er, signed, n):
    """Nonoverlapping n-return intervals; no cross-day transition pairs."""
    counts = Counter(); marg1 = Counter(); marg2 = Counter(); transitions = Counter()
    days = frame.trading_day.astype(str).to_numpy()
    first = np.r_[0, np.where(days[1:] != days[:-1])[0]+1]
    last = np.r_[first[1:], len(days)]
    for a, b in zip(first, last):
        ends = np.arange(a+n, b, n)
        labels = []
        for i in ends:
            e, d = er[i], signed[i]
            if not np.isfinite(e): continue
            label = 'range' if e <= .2 else ('up' if d > 0 else 'down') if e >= .6 else 'mixed'
            labels.append(label); counts[label] += 1
        for prev, nex in zip(labels, labels[1:]):
            marg1[prev] += 1; marg2[nex] += 1; transitions[prev+'->'+nex] += 1
    total = sum(transitions.values())
    stay = sum(transitions[k+'->'+k] for k in ('range','mixed','up','down'))
    reference = sum(marg1[k]*marg2[k] for k in marg1)/total**2 if total else None
    return {'disjoint_windows': sum(counts.values()), 'adjacent_pairs':total, 'counts':dict(counts),
            'transitions':dict(transitions), 'stay_rate':stay/total if total else None,
            'stay_excess_over_independent_marginals':stay/total-reference if total else None}


def circular_block_ci(values, block, reps=600):
    x = np.asarray(values, float); n = len(x)
    if n < block*3: return None
    rng = np.random.default_rng(20260905+block)
    samples=[]
    for _ in range(reps):
        starts=rng.integers(0,n,size=(n+block-1)//block)
        ind=((starts[:,None]+np.arange(block))%n).ravel()[:n]
        samples.append(float(x[ind].mean()))
    return {'block_trading_days':block,'repetitions':reps,'mean':float(x.mean()),
            'interval_95': [float(v) for v in np.quantile(samples,[.025,.975])],
            'estimand':'mean_paired_daily_ER_standard_deviation_difference_not_accuracy'}


def frequency_study(output):
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    frames={}; audits=[]; native=[]; paired=[]; annual=[]; alignments=[]; persist=[]
    features={}
    for view in VIEWS:
        path=ROOT/f'data/development/{view}.parquet'; e=next(p for p in manifest['products'] if Path(p['path']).name==path.name)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==e['sha256']
        f=pd.read_parquet(path); a=audit_frame(f); a['sha256']=e['sha256']; audits.append(a);frames[view]=f
        x=np.log(f.close.to_numpy()); mins=1 if view.startswith('1m') else 5
        for n in ([12,24,48,60,120,240] if mins==1 else [12,24,48]):
            v=path_metrics(x,n); features[(view,n)]=v
            for scope,mask in scope_masks(f,n,mins).items():
                native.append({'view':view,'n_returns':n,'nominal_minutes':n*mins,'scope':scope, **describe_er(v['er'][mask])})
            persist.append({'view':view,'n_returns':n,**persistence(f,v['er'],v['signed_er'],n)})
        print('NATIVE_DONE',view,flush=True)
    fine=frames['1m_official']; fx=np.log(fine.close.to_numpy())
    fine_idx=pd.Index(fine.timestamp)
    for view in VIEWS[1:]:
        f=frames[view]; cx=np.log(f.close.to_numpy()); lookup=fine_idx.get_indexer(f.timestamp)
        ok=lookup>=0
        alignments.append({'view':view,'coarse_rows':len(f),'matched_timestamps':int(ok.sum()),
             'max_common_close_absolute_difference':float(np.max(np.abs(f.close.to_numpy()[ok]-fine.close.to_numpy()[lookup[ok]]))),
             'matching_price_rows':int(np.isclose(cx[ok],fx[lookup[ok]],rtol=0,atol=1e-10).sum())})
        for n in (12,24,48):
            p=coarse_fine_path(fx,cx,lookup,n);end=p['end'];start=p['start']; days=f.trading_day.astype(str).to_numpy()
            v=features[('1m_official',n)]['er']
            table=pd.DataFrame({'coarse_end':end,'timestamp':f.timestamp.iloc[end].to_numpy(),
                'day':days[end],'year':[s[:4] for s in days[end]], 'er_5m':p['coarse_er'],
                'er_1m_same_endpoints':p['fine_er'], 'er_1m_same_bars':v[np.maximum(lookup[end],0)],
                'fine_return_count':p['fine_return_count'],
                'valid':p['valid'],'all_prices_match':p['all_prices_match'],
                'within_day':days[start]==days[end]})
            table=table.loc[table.valid].copy()
            name=f'{view}_n{n}'
            table.to_csv(output/f'{name}_pairs.csv.gz',index=False,compression={'method':'gzip','compresslevel':1})
            for scope in ('continuous','within_day'):
                selected=table if scope=='continuous' else table.loc[table.within_day]
                vals={c:describe_er(selected[c].to_numpy()) for c in ['er_5m','er_1m_same_endpoints','er_1m_same_bars']}
                p_row={'view':view,'n_5m_returns':n,'scope':scope,'n_pairs':len(selected),'statistics':vals,
                       'all_prices_match_windows':int(selected.all_prices_match.sum()),
                       'fine_return_count_min':int(selected.fine_return_count.min()) if len(selected) else None,
                       'fine_return_count_max':int(selected.fine_return_count.max()) if len(selected) else None,
                       'triangle_inequality_failures':int(((selected.er_5m+1e-8 < selected.er_1m_same_endpoints)&selected.all_prices_match).sum())}
                paired.append(p_row)
                for year,g in selected.groupby('year'):
                    annual.append({'view':view,'n_5m_returns':n,'scope':scope,'year':year,
                           **{c:describe_er(g[c].to_numpy()) for c in vals}})
                if view=='5m_offset_0' and n in (12,24) and scope=='within_day':
                    stds=selected.groupby('day')[list(vals)].std(ddof=0).dropna()
                    stds.to_csv(output/f'{name}_daily_std.csv')
                    for comparator in ['er_1m_same_endpoints','er_1m_same_bars']:
                        differences=(stds.er_5m-stds[comparator]).to_numpy()
                        p_row['daily_std_difference_'+comparator]={
                            'days':len(differences),'fraction_positive':float(np.mean(differences>0)),
                            'block_ci':[circular_block_ci(differences,b) for b in (20,60)]}
        print('PAIRED_DONE',view,flush=True)
    # Sequence-destruction control. Returns crossing a session boundary stay fixed.
    null=[]
    for view in ('1m_official','5m_offset_0'):
        f=frames[view]; x=np.log(f.close.to_numpy()); minutes=1 if view.startswith('1m') else 5
        stamp=f.timestamp.astype('int64').to_numpy();breaks=np.r_[0,np.where(np.diff(stamp)>minutes*60*1e9*1.01)[0]+1,len(x)]
        mask=scope_masks(f,24,minutes)['within_day']; rng=np.random.default_rng(20260905)
        control=[]; r=np.diff(x)
        for _ in range(16):
            sr=r.copy()
            for a,b in zip(breaks,breaks[1:]):
                if b-a>1:sr[a:b-1]=rng.permutation(sr[a:b-1])
            y=np.r_[x[0], x[0]+np.cumsum(sr)]
            control.append(describe_er(path_metrics(y,24)['er'][mask]))
        null.append({'view':view,'control':'shuffle_in_session_returns_keep_boundary_jumps_fixed',
                 'n_returns':24,'observed':describe_er(features[(view,24)]['er'][mask]),'replicates':control})
    result={'status':'descriptive_frequency_comparison_not_external_AI_replication','primary_view':'5m_offset_0',
            'data_audits':audits,'alignments':alignments,'native':native,'paired':paired,'annual':annual,
            'nonoverlap_persistence':persist,'sequence_destruction_control':null,
            'fresh_oos':False,'pnl_computed':False,'external_AI_formula_available':False}
    save(output/'frequency_summary.json',result)
    print('FREQUENCY_DONE',json.dumps({'views':len(frames),'paired_groups':len(paired)}),flush=True)
    return result


def replay_study(output, engine_type=DirectionEngine):
    summaries=[]; selected=[]
    for view in VIEWS:
        bars,audit=load_development_bars(ROOT/f'data/development/{view}.parquet',ROOT/'data/manifest.json')
        for scale in (.008,.01,.012):
            config=CandidateConfig(timeframe=view,reversal_log=scale,geometry_variant='detrended_width')
            engine=engine_type(config); emitted=[]
            for bar in bars: emitted.extend(engine.update(bar))
            assert emitted==engine.records
            records=engine.records; counts=Counter(r['direction_classification'] for r in records)
            source=engine.source; base_counts=Counter(s['classification'] for s in source.structures)
            transitions=Counter(r['channel_classification_A']+'->'+r['direction_classification'] for r in records)
            checkpoints=sorted({i for i in (200,800,1600,len(bars)//2) if 0<i<len(bars)})
            for stop in checkpoints:
                prefix=engine_type(config)
                for bar in bars[:stop]:prefix.update(bar)
                assert prefix.records==[r for r in records if r['confirmation_bar']<stop]
            dest=output/view/f'reversal_{scale:g}';dest.mkdir(parents=True,exist_ok=True)
            with gzip.open(dest/'direction_records.jsonl.gz','wt') as h:
                for r in records:h.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
            perturb=None
            if scale==.01:
                altered=engine_type(config)
                for i,bar in enumerate(bars):
                    mult=math_exp_perturb(i)
                    altered.update({**bar,**{k:bar[k]*mult for k in ('open','high','low','close')}})
                key=lambda r:(r['phase'],*r['five_occurrence_bars'])
                lookup={key(r):r for r in altered.records};matched=[(r,lookup[key(r)]) for r in records if key(r) in lookup]
                perturb={'original':len(records),'perturbed':len(altered.records),'strict_matches':len(matched),
                    'original_unmatched':len(records)-len(matched),'perturbed_unmatched':len(altered.records)-len(matched),
                    'classification_changes':sum(a['direction_classification']!=b['direction_classification'] for a,b in matched),
                    'confirmation_bar_changes':sum(a['confirmation_bar']!=b['confirmation_bar'] for a,b in matched)}
            row={'view':view,'scale':scale,'bars':len(bars),'structures':len(records),
                'A_counts':dict(base_counts),'C_direction_counts':dict(counts),'transitions_A_to_C':dict(transitions),
                'C_clear_A_channel_rejected':sum(r['direction_classification']!='uncertain' and not r['channel_accepted_by_A'] for r in records),
                'independent_prefix_checks':len(checkpoints),'prefix_passed':True,'perturbation':perturb,
                'C_er_by_direction':{label:describe_er(np.array([r['path_er'] for r in records if r['direction_classification']==label and r['path_er'] is not None])) for label in counts}}
            summaries.append(row);save(dest/'summary.json',row)
            if view=='5m_offset_0' and scale==.01:
                groups={}
                for i,r in enumerate(records):
                    label=r['direction_classification'];a=r['channel_classification_A']
                    bucket=('A_clear_C_uncertain' if a!='uncertain' and label=='uncertain' else
                            'C_new_'+label if a=='uncertain' and label!='uncertain' else 'stable_'+label)
                    groups.setdefault(bucket,[]).append((hashlib.sha256(r['direction_record_id'].encode()).hexdigest(),i))
                pmap={p['pivot_id']:p for p in source.pivots}
                for bucket,items in sorted(groups.items()):
                    for _,i in sorted(items)[:2]:
                        s=source.structures[i];r=records[i];a=max(0,r['start_bar']-12);b=r['confirmation_bar']
                        case={'bucket':bucket,'direction':r,'source_structure':s,
                              'pivots':[pmap[k] for k in s['pivot_ids']],
                              'bars_start_index':a,'bars':source.bars[a:b+1],
                              'selection':'two_smallest_sha256_direction_record_ids_per_bucket_5m_offset_0_scale_001',
                              'not_human_reference':True}
                        name=f'case_{len(selected):02d}_{bucket}'
                        selected.append({'name':name,'bucket':bucket,'record_id':r['direction_record_id']})
                        save(output/'gallery'/f'{name}.json',case)
            print('DIRECTION_GROUP',json.dumps(row,ensure_ascii=False),flush=True)
    result={'status':'C_direction_channel_decoupling_replayed_not_user_accepted','groups':summaries,
            'gallery':selected,'primary_view':'5m_offset_0','one_minute_is_diagnostic_not_acceptance_gate':True,
            'fresh_oos':False,'pnl_computed':False,'h1_opened':False,'ready_for_user_acceptance':False}
    save(output/'direction_summary.json',result)
    return result


def math_exp_perturb(i):
    return float(np.exp(1e-5*np.sin(i*np.sqrt(2))))


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--stage',choices=['frequency','direction','all'],default='all')
    args=p.parse_args();out=Path(args.output)
    if out.exists() and any(out.iterdir()):raise SystemExit('output must be empty to preserve prior runs')
    out.mkdir(parents=True,exist_ok=True)
    source_paths=[Path(__file__), *sorted((ROOT/'src/factor_lab/visual_structure/two_wave').glob('*.py')), ROOT/'data/manifest.json',ROOT/'docs/research/two_wave_5m_separation_protocol_v03.md']
    hashes={str(q.relative_to(ROOT)):hashlib.sha256(q.read_bytes()).hexdigest() for q in source_paths}
    try:
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,stderr=subprocess.DEVNULL,text=True).strip()
    except (subprocess.CalledProcessError,FileNotFoundError):
        git_commit=None
    save(out/'run_manifest.json',{'started_at_utc':datetime.now(timezone.utc).isoformat(),'actual_git_commit':git_commit,'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,
        'source_sha256':hashes,'workspace_commit':(ROOT/'WORKSPACE_COMMIT.txt').read_text().strip() if (ROOT/'WORKSPACE_COMMIT.txt').exists() else None,
        'stage':args.stage,'all_data_development':True,'resampling_performed':False})
    if args.stage in ('frequency','all'):frequency_study(out)
    if args.stage in ('direction','all'):replay_study(out)
    assert all(hashlib.sha256((ROOT/q).read_bytes()).hexdigest()==h for q,h in hashes.items())
    m=json.loads((out/'run_manifest.json').read_text());m.update({'finished_at_utc':datetime.now(timezone.utc).isoformat(),'all_source_hashes_unchanged':True});save(out/'run_manifest.json',m)

if __name__=='__main__':main()
