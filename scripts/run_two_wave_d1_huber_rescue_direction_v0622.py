#!/usr/bin/env python3
"""Formal v0.6.22 D1-primary Huber-rescue direction replay."""
from __future__ import annotations

import argparse, gzip, json, math, sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.d1_huber_rescue_direction_v0622 import rescue_direction
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.models import stable_id
from factor_lab.visual_structure.two_wave.same_scale_v04 import evaluate_pair
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import build_edge_graph
from factor_lab.visual_structure.two_wave.whole_window_huber_direction_v0621 import classify_parent_window

VIEWS=tuple(f"5m_offset_{i}" for i in range(5))
EXPECTED_FILTERED={"5m_offset_1":14784,"5m_offset_2":12725,"5m_offset_3":13412,"5m_offset_4":16108}
EXPECTED_RAW={"5m_offset_1":8381,"5m_offset_2":5770,"5m_offset_3":6204,"5m_offset_4":9098}
EXPECTED_V0618={
"5m_offset_1":{"both_qualified":400,"both_rejected":7809,"main_only_qualified":101,"other_only_qualified":71},
"5m_offset_2":{"both_qualified":287,"both_rejected":5323,"main_only_qualified":93,"other_only_qualified":67},
"5m_offset_3":{"both_qualified":302,"both_rejected":5736,"main_only_qualified":90,"other_only_qualified":76},
"5m_offset_4":{"both_qualified":473,"both_rejected":8447,"main_only_qualified":102,"other_only_qualified":76}}
EXPECTED_BOTHQ=1462
LABELS=("range","uptrend","downtrend","uncertain")


def load_gz(path):
    with gzip.open(path,"rt",encoding="utf-8") as fh:return [json.loads(x) for x in fh if x.strip()]

def find_one(root,name):
    hits=list(root.rglob(name));
    if len(hits)!=1: raise RuntimeError(f"expected one {name}, got {len(hits)}")
    return hits[0]

def fkey(r): return str(r["phase"]),tuple(int(x) for x in r["five_filtered_occurrence_bars"])

def qmatrix(pairs):
    o={"both_qualified":0,"both_rejected":0,"main_only_qualified":0,"other_only_qualified":0}
    for a,b in pairs:
        qa,qb=bool(a["candidate_qualified"]),bool(b["candidate_qualified"])
        if qa and qb:o["both_qualified"]+=1
        elif not qa and not qb:o["both_rejected"]+=1
        elif qa:o["main_only_qualified"]+=1
        else:o["other_only_qualified"]+=1
    return o

def reconstruct_pair(row,bars,view):
    cfg=MaturityConfig(timeframe=view); raw=[int(x) for x in row["published_raw_occurrence_bars"]]
    confirmation=int(row["publishing_confirmation_bar"]); phase=str(row["phase"]); other="high" if phase=="low" else "low"
    kinds=[phase,other,phase,other,phase]; ct=str(bars[confirmation]["timestamp"]); points=[]
    for n,(kind,occ) in enumerate(zip(kinds,raw)):
        p=float(bars[occ]["close"])
        points.append({"kind":kind,"occurrence_bar":occ,"occurrence_time":str(bars[occ]["timestamp"]),"price":p,"log_price":math.log(p),"left_censored":False,"confirmation_bar":confirmation,"confirmation_time":ct,"bar_end_assumed":False,"pivot_id":stable_id("v0622_audit_pivot",[view,phase,raw,confirmation,n,occ,p])})
    return evaluate_pair(points,bars,cfg,source="v0622_direction_audit")

def state(row,bars,closes,view):
    pair=reconstruct_pair(row,bars,view); d1=str(pair["direction_versions"]["D1"])
    huber=classify_parent_window(closes,row["published_raw_occurrence_bars"],float(pair["amplitude_unit_price"]))["classification"]
    rescue=rescue_direction(d1,huber)
    return {"D1":d1,"Huber":huber,"v0622":rescue["classification"],"source":rescue["source"],"overridden":rescue["D1_decisive_overridden"]}

def metrics(pairs):
    n=len(pairs); exact=sum(a==b for a,b in pairs); dec=[(a,b) for a,b in pairs if a!="uncertain" and b!="uncertain"]
    labels=[x for p in pairs for x in p]; counts=Counter(labels); dcounts=Counter(x for x in labels if x!="uncertain"); dt=sum(dcounts.values())
    return {"pairs":n,"exact_agreement":exact/n if n else 0.0,"exact_agreement_count":exact,"decisive_agreement":sum(a==b for a,b in dec)/len(dec) if dec else 0.0,"decisive_pair_count":len(dec),"opposite_trend_conflict_count":sum({a,b}=={"uptrend","downtrend"} for a,b in pairs),"main_decisive_coverage":sum(a!="uncertain" for a,_ in pairs)/n if n else 0.0,"other_decisive_coverage":sum(b!="uncertain" for _,b in pairs)/n if n else 0.0,"pooled_decisive_coverage":dt/(2*n) if n else 0.0,"pooled_label_counts":{k:counts.get(k,0) for k in LABELS},"pooled_decisive_label_shares":{k:(dcounts.get(k,0)/dt if dt else 0.0) for k in LABELS if k!="uncertain"}}

def write_card(path,r):
    b=r["pooled"]["D1"]; c=r["pooled"]["v0622"]
    lines=["# Two-Wave v0.6.22 D1-primary Huber-rescue result","",f"Formal verdict: **`{r['verdict']}`**","",f"D1 decisive overrides: **{r['rescue_audit']['D1_decisive_override_count']}**.",f"D1-Uncertain records rescued: **{r['rescue_audit']['rescued_record_count']}**.","","| metric | D1 | v0.6.22 |","|---|---:|---:|",f"| pooled exact agreement | {b['exact_agreement']:.2%} | {c['exact_agreement']:.2%} |",f"| pooled decisive coverage | {b['pooled_decisive_coverage']:.2%} | {c['pooled_decisive_coverage']:.2%} |",f"| decisive agreement | {b['decisive_agreement']:.2%} | {c['decisive_agreement']:.2%} |",f"| opposite trend conflicts | {b['opposite_trend_conflict_count']} | {c['opposite_trend_conflict_count']} |","","Per-offset exact agreement:","","| offset | D1 | v0.6.22 | delta pp |","|---|---:|---:|---:|"]
    for v,row in r["per_offset"].items():
        d=row["D1"]["exact_agreement"]; x=row["v0622"]["exact_agreement"]; lines.append(f"| {v} | {d:.2%} | {x:.2%} | {(x-d)*100:.2f} |")
    lines += ["","Promotion gates:"]+[f"- {k}: **{v}**" for k,v in r["gates"].items()]+["","Independent morphology acceptance remains false; qualification champion remains v0.6.18."]
    path.write_text("\n".join(lines)+"\n")

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    filtered={};records={};maps={};bars={};closes={};states={}
    override=0; rescued=Counter()
    for v in VIEWS:
        filtered[v]=load_gz(find_one(a.input,f"filtered-{v}.json.gz"));records[v]=load_gz(find_one(a.input,f"records-{v}.json.gz"));maps[v]={fkey(r):r for r in records[v]}
        bars[v],_=load_development_bars(ROOT/f"data/development/{v}.parquet",ROOT/"data/manifest.json");closes[v]=[float(x["close"]) for x in bars[v]];states[v]={}
        for r in records[v]:
            if r["candidate_qualified"]:
                s=state(r,bars[v],closes[v],v);states[v][fkey(r)]=s;override+=int(s["overridden"])
                if s["source"]=="Huber_rescue":rescued[s["v0622"]]+=1
    assert override==0
    pooled_d=[];pooled_c=[];per={};total=0;main="5m_offset_0"
    for v in VIEWS[1:]:
        g=build_edge_graph(filtered[main],filtered[v],time_field="five_filtered_occurrence_times",nominal_bar_minutes=5.0,require_phase=True);fp=list(g.mutual_unique_matches);assert len(fp)==EXPECTED_FILTERED[v]
        strict=[]
        for i,j in fp:
            ra=maps[main].get(fkey(filtered[main][i]));rb=maps[v].get(fkey(filtered[v][j]))
            if ra is not None and rb is not None and strict_anchor_edge(ra,rb,5.0) is not None:strict.append((ra,rb))
        assert len(strict)==EXPECTED_RAW[v];assert qmatrix(strict)==EXPECTED_V0618[v]
        both=[(x,y) for x,y in strict if x["candidate_qualified"] and y["candidate_qualified"]];total+=len(both)
        dp=[];cp=[]
        for x,y in both:
            sx=states[main][fkey(x)];sy=states[v][fkey(y)];dp.append((sx["D1"],sy["D1"]));cp.append((sx["v0622"],sy["v0622"]))
        pooled_d+=dp;pooled_c+=cp;per[v]={"D1":metrics(dp),"v0622":metrics(cp)}
    assert total==EXPECTED_BOTHQ
    d=metrics(pooled_d);c=metrics(pooled_c);shares=c["pooled_decisive_label_shares"]
    gates={"upstream_controls":True,"D1_decisive_override_zero":override==0,"all_offsets_exact_agreement_nonworse":all(row["v0622"]["exact_agreement"]>=row["D1"]["exact_agreement"] for row in per.values()),"pooled_exact_agreement_plus_1pp":c["exact_agreement"]>=d["exact_agreement"]+0.01,"opposite_trend_conflict_zero":c["opposite_trend_conflict_count"]==0,"pooled_decisive_agreement_at_least_99pct":c["decisive_agreement"]>=0.99,"pooled_decisive_coverage_material":c["pooled_decisive_coverage"]>=0.65 and c["pooled_decisive_coverage"]>=d["pooled_decisive_coverage"]+0.15,"each_offset_side_decisive_coverage_at_least_55pct":all(min(row["v0622"]["main_decisive_coverage"],row["v0622"]["other_decisive_coverage"])>=0.55 for row in per.values()),"decisive_class_diversity":shares.get("uptrend",0)>=0.15 and shares.get("downtrend",0)>=0.15 and shares.get("range",0)>=0.02}
    passed=all(gates.values());result={"schema":"two_wave_d1_huber_rescue_direction_result@0.6.22","verdict":"v0622_D1_primary_Huber_rescue_direction_research_component_pass" if passed else "v0622_D1_primary_Huber_rescue_direction_rejected","controls":{"filtered_pairs":57029,"raw_strict_pairs":29453,"both_v0618_qualified_pairs":total,"reproduced":True},"rescue_audit":{"D1_decisive_override_count":override,"rescued_record_count":sum(rescued.values()),"rescued_label_counts":dict(rescued)},"pooled":{"D1":d,"v0622":c},"per_offset":per,"gates":gates,"qualification_policy":"v0.6.18","qualification_changed":False,"morphology_acceptance":False,"future_outcome_used":False,"trade_authority":False,"production_authority":False}
    (a.output/"summary.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n");write_card(a.output/"RESULT_CARD.md",result);print(json.dumps(result,ensure_ascii=False,sort_keys=True))
if __name__=="__main__":main()
