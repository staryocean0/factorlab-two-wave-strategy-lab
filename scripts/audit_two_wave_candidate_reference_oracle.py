"""Independent arithmetic oracle from saved v0.1 prefixes, not human reference labels.

Reads original replay's raw close prefixes and stored original geometry. Does NOT
import the candidate fitter/engine. This checks implementation equivalence only.
"""
from __future__ import annotations
import argparse, base64, gzip, hashlib, json, math, re
from collections import Counter
from pathlib import Path
from zipfile import ZipFile


def old_prefixes(archive):
    with ZipFile(archive) as bundle:
        text=bundle.read('two_wave_h0/replay.html').decode()
    match=re.search(r'<script id="replayData"[^>]*>(.*?)</script>',text,re.S)
    return json.loads(gzip.decompress(base64.b64decode(match.group(1))))


def derive(runs):
    oracle=[]
    for run in runs:
        old=run['export']; points={p['pivot_id']:p for p in old['pivots']}
        cfg=old['config']; rows=run['bars']
        for s in old['structures']:
            g=s['geometry']; pivot_bars=[points[i]['occurrence_bar'] for i in s['pivot_ids']]
            a=s['attributes'].copy(); widths=None; ratio=None
            if g['valid']:
                widths=[]
                for k in (0,2):
                    z=[math.log(rows[i]['close'])-g['b']*(i-pivot_bars[0]) for i in range(pivot_bars[k],pivot_bars[k+2]+1)]
                    widths.append(max(z)-min(z))
                ratio=max(widths)/min(widths) if min(widths)>cfg['min_width'] else None
                a=[x for x in a if x!='cycle_amplitude_change']
                if ratio is None or ratio>cfg['max_width_ratio']: a.append('detrended_cycle_width_change')
            b=[x for x in a if x!='uneven_phase_drift'] if g['valid'] else a[:]
            def label(blockers):
                return 'uncertain' if blockers or not g['valid'] else ('range' if abs(g['D'])<=cfg['drift_threshold'] else 'uptrend' if g['D']>0 else 'downtrend')
            oracle.append({'view':cfg['timeframe'],'scale':cfg['reversal_log'],'phase':s['phase'],
                           'pivots':pivot_bars,'confirmation_bar':s['confirmation_bar'],
                           'baseline':s['classification'],'A':label(a),'B':label(b),
                           'widths':widths,'ratio':ratio,'A_blockers':a,'B_blockers':b})
    return oracle


def check(oracle,archive):
    mapping={}
    with ZipFile(archive) as z:
        for name in z.namelist():
            if not name.endswith('/structures.jsonl'):continue
            parts=Path(name).parts
            if len(parts)<4:continue
            view,scale_name,method=parts[-4:-1]
            scale=float(scale_name.removeprefix('reversal_'))
            prefix=str(Path(name).parent)
            pivots={p['pivot_id']:p['occurrence_bar'] for p in map(json.loads,z.read(prefix+'/pivots.jsonl').splitlines())}
            for s in map(json.loads,z.read(name).splitlines()):
                if s['confirmation_bar']>=1200:continue
                key=(view,scale,method,s['phase'],* [pivots[i] for i in s['pivot_ids']])
                if key in mapping:raise AssertionError('duplicate identity in archive')
                mapping[key]=s
    checks=0; maxerr=0.; failures=[]
    for r in oracle:
        for method,short in [('v01','baseline'),('detrended_width','A'),('drift_tolerant','B')]:
            key=(r['view'],r['scale'],method,r['phase'],*r['pivots'])
            s=mapping.pop(key,None)
            if s is None:failures.append({'key':key,'error':'missing'});continue
            checks+=1
            if s['classification']!=r[short] or s['confirmation_bar']!=r['confirmation_bar']:
                failures.append({'key':key,'error':'label_or_clock'})
            if method!='v01':
                if s['rejection_reasons']!=r[short+'_blockers']:failures.append({'key':key,'error':'blockers'})
                for key2 in [('cycle_detrended_width_ratio','ratio')]:
                    actual=s['geometry'][key2[0]]; expected=r[key2[1]]
                    if actual is None or expected is None:
                        if actual!=expected:failures.append({'key':key,'error':'undefined_ratio'})
                    else:
                        err=abs(actual-expected);maxerr=max(maxerr,err)
                        if not math.isclose(actual,expected,rel_tol=1e-9,abs_tol=1e-10):failures.append({'key':key,'error':'width_ratio'})
    return {'comparison_records':checks,'extra_records_in_new_prefix':len(mapping),'maximum_ratio_absolute_error':maxerr,
            'failures':failures,'passed':not failures and not mapping,'independent_human_reference':False,
            'scope':'implementation_arithmetic_oracle_on_saved_first_1200_bar_prefixes'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--old',type=Path,required=True);p.add_argument('--new',type=Path)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    rows=derive(old_prefixes(args.old));result={'old_zip_sha256':hashlib.sha256(args.old.read_bytes()).hexdigest(),
        'source':'original v0.1 native replay prefixes; no modified or new market data','objects':len(rows),
        'counts':{m:dict(Counter(r[m] for r in rows)) for m in ['baseline','A','B']},
        'scope':'independent implementation oracle; NOT independent morphology truth'}
    if args.new:result['verification']=check(rows,args.new)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    args.output.with_name('prefix_oracle_objects.json').write_text(json.dumps(rows,separators=(',',':')))
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
