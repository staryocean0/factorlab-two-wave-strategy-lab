#!/usr/bin/env python3
"""Formal v0.6.21 whole-window Huber direction replay."""
from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.same_scale_v04 import evaluate_pair
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import build_edge_graph
from factor_lab.visual_structure.two_wave.whole_window_huber_direction_v0621 import classify_parent_window
from factor_lab.visual_structure.two_wave.models import stable_id

VIEWS = tuple(f"5m_offset_{i}" for i in range(5))
EXPECTED_FILTERED = {"5m_offset_1":14784,"5m_offset_2":12725,"5m_offset_3":13412,"5m_offset_4":16108}
EXPECTED_RAW = {"5m_offset_1":8381,"5m_offset_2":5770,"5m_offset_3":6204,"5m_offset_4":9098}
EXPECTED_V0618 = {
    "5m_offset_1":{"both_qualified":400,"both_rejected":7809,"main_only_qualified":101,"other_only_qualified":71},
    "5m_offset_2":{"both_qualified":287,"both_rejected":5323,"main_only_qualified":93,"other_only_qualified":67},
    "5m_offset_3":{"both_qualified":302,"both_rejected":5736,"main_only_qualified":90,"other_only_qualified":76},
    "5m_offset_4":{"both_qualified":473,"both_rejected":8447,"main_only_qualified":102,"other_only_qualified":76},
}
EXPECTED_BOTHQ = 1462
LABELS = ("range","uptrend","downtrend","uncertain")


def load_gz(path: Path):
    with gzip.open(path,"rt",encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def find_one(root: Path, name: str) -> Path:
    hits=list(root.rglob(name))
    if len(hits)!=1:
        raise RuntimeError(f"expected one {name}, got {len(hits)}")
    return hits[0]


def fkey(row):
    return str(row["phase"]), tuple(int(x) for x in row["five_filtered_occurrence_bars"])


def qualification_matrix(pairs):
    out={"both_qualified":0,"both_rejected":0,"main_only_qualified":0,"other_only_qualified":0}
    for a,b in pairs:
        qa=bool(a["candidate_qualified"]); qb=bool(b["candidate_qualified"])
        if qa and qb: out["both_qualified"]+=1
        elif not qa and not qb: out["both_rejected"]+=1
        elif qa: out["main_only_qualified"]+=1
        else: out["other_only_qualified"]+=1
    return out


def reconstruct_pair(row, bars, view):
    cfg=MaturityConfig(timeframe=view)
    raw=[int(x) for x in row["published_raw_occurrence_bars"]]
    confirmation=int(row["publishing_confirmation_bar"])
    phase=str(row["phase"])
    kinds=[phase,"high" if phase=="low" else "low",phase,"high" if phase=="low" else "low",phase]
    points=[]
    confirmation_time=str(bars[confirmation]["timestamp"])
    for ordinal,(kind,occ) in enumerate(zip(kinds,raw)):
        price=float(bars[occ]["close"])
        points.append({
            "kind":kind,"occurrence_bar":occ,"occurrence_time":str(bars[occ]["timestamp"]),
            "price":price,"log_price":math.log(price),"left_censored":False,
            "confirmation_bar":confirmation,"confirmation_time":confirmation_time,"bar_end_assumed":False,
            "pivot_id":stable_id("v0621_audit_pivot",[view,phase,raw,confirmation,ordinal,occ,price]),
        })
    return evaluate_pair(points,bars,cfg,source="v0621_direction_audit")


def per_row_direction(row,bars,view):
    pair=reconstruct_pair(row,bars,view)
    d1=str(pair["direction_versions"]["D1"])
    challenger=classify_parent_window(
        [float(bar["close"]) for bar in bars],
        row["published_raw_occurrence_bars"],
        float(pair["amplitude_unit_price"]),
    )
    return {"D1":d1,"v0621":challenger["classification"],"score":challenger["normalized_parent_drift"]}


def label_metrics(label_pairs):
    n=len(label_pairs)
    exact=sum(a==b for a,b in label_pairs)
    decisive=[(a,b) for a,b in label_pairs if a!="uncertain" and b!="uncertain"]
    opposite=sum({a,b}=={"uptrend","downtrend"} for a,b in label_pairs)
    main_labels=[a for a,_ in label_pairs]; other_labels=[b for _,b in label_pairs]
    all_labels=main_labels+other_labels
    counts=Counter(all_labels)
    decisive_counts=Counter(x for x in all_labels if x!="uncertain")
    decisive_total=sum(decisive_counts.values())
    return {
        "pairs":n,
        "exact_agreement_count":exact,
        "exact_agreement":exact/n if n else 0.0,
        "decisive_pair_count":len(decisive),
        "decisive_agreement_count":sum(a==b for a,b in decisive),
        "decisive_agreement":sum(a==b for a,b in decisive)/len(decisive) if decisive else 0.0,
        "opposite_trend_conflict_count":opposite,
        "opposite_trend_conflict_rate":opposite/n if n else 0.0,
        "main_decisive_coverage":sum(x!="uncertain" for x in main_labels)/n if n else 0.0,
        "other_decisive_coverage":sum(x!="uncertain" for x in other_labels)/n if n else 0.0,
        "pooled_decisive_coverage":decisive_total/(2*n) if n else 0.0,
        "pooled_label_counts":{k:counts.get(k,0) for k in LABELS},
        "pooled_decisive_label_shares":{k:(decisive_counts.get(k,0)/decisive_total if decisive_total else 0.0) for k in LABELS if k!="uncertain"},
    }


def write_card(path,result):
    b=result["pooled"]["D1"]; c=result["pooled"]["v0621"]
    lines=[
        "# Two-Wave v0.6.21 whole-window Huber direction result","",
        f"Formal verdict: **`{result['verdict']}`**","",
        "Qualification remained frozen at v0.6.18. Direction evaluation used only 1,462 strict same-financial-identity pairs where both views were v0.6.18-qualified.","",
        "| metric | D1 | v0.6.21 |","|---|---:|---:|",
        f"| pooled exact four-state agreement | {b['exact_agreement']:.2%} | {c['exact_agreement']:.2%} |",
        f"| pooled decisive coverage | {b['pooled_decisive_coverage']:.2%} | {c['pooled_decisive_coverage']:.2%} |",
        f"| opposite-trend conflict | {b['opposite_trend_conflict_rate']:.2%} | {c['opposite_trend_conflict_rate']:.2%} |","",
        "Per-offset exact agreement:","","| offset | D1 | v0.6.21 | delta pp |","|---|---:|---:|---:|",
    ]
    for view,row in result["per_offset"].items():
        d=row["D1"]["exact_agreement"]; h=row["v0621"]["exact_agreement"]
        lines.append(f"| {view} | {d:.2%} | {h:.2%} | {(h-d)*100:.2f} |")
    lines += ["","Promotion gates:"]
    for key,value in result["gates"].items(): lines.append(f"- {key}: **{value}**")
    lines += ["","This is direction research only. Independent morphology acceptance remains false; no trading or production authority follows."]
    path.write_text("\n".join(lines)+"\n")


def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",type=Path,required=True); p.add_argument("--output",type=Path,required=True)
    args=p.parse_args(); args.output.mkdir(parents=True,exist_ok=True)

    filtered={}; records={}; recmap={}; bars={}; directions={}
    for view in VIEWS:
        filtered[view]=load_gz(find_one(args.input,f"filtered-{view}.json.gz"))
        records[view]=load_gz(find_one(args.input,f"records-{view}.json.gz"))
        recmap[view]={fkey(r):r for r in records[view]}
        bars[view],_=load_development_bars(ROOT/f"data/development/{view}.parquet",ROOT/"data/manifest.json")
        directions[view]={}
        for r in records[view]:
            if bool(r["candidate_qualified"]):
                directions[view][fkey(r)]=per_row_direction(r,bars[view],view)

    total_bothq=0; per_offset={}; pooled_d1=[]; pooled_h=[]
    main="5m_offset_0"
    for view in VIEWS[1:]:
        graph=build_edge_graph(filtered[main],filtered[view],time_field="five_filtered_occurrence_times",nominal_bar_minutes=5.0,require_phase=True)
        fp=list(graph.mutual_unique_matches)
        assert len(fp)==EXPECTED_FILTERED[view]
        strict=[]
        for i,j in fp:
            ra=recmap[main].get(fkey(filtered[main][i])); rb=recmap[view].get(fkey(filtered[view][j]))
            if ra is not None and rb is not None and strict_anchor_edge(ra,rb,5.0) is not None:
                strict.append((ra,rb))
        assert len(strict)==EXPECTED_RAW[view]
        qm=qualification_matrix(strict); assert qm==EXPECTED_V0618[view]
        both=[(a,b) for a,b in strict if a["candidate_qualified"] and b["candidate_qualified"]]
        total_bothq += len(both)
        d1pairs=[]; hpairs=[]
        for a,b in both:
            da=directions[main][fkey(a)]; db=directions[view][fkey(b)]
            d1pairs.append((da["D1"],db["D1"])); hpairs.append((da["v0621"],db["v0621"]))
        pooled_d1.extend(d1pairs); pooled_h.extend(hpairs)
        per_offset[view]={"D1":label_metrics(d1pairs),"v0621":label_metrics(hpairs)}
    assert total_bothq==EXPECTED_BOTHQ

    d1=label_metrics(pooled_d1); h=label_metrics(pooled_h)
    per_nonworse=all(row["v0621"]["exact_agreement"]>=row["D1"]["exact_agreement"] for row in per_offset.values())
    coverage_floor=all(min(row["v0621"]["main_decisive_coverage"],row["v0621"]["other_decisive_coverage"])>=0.40 for row in per_offset.values())
    shares=h["pooled_decisive_label_shares"]
    gates={
        "upstream_controls":True,
        "all_offsets_exact_agreement_nonworse":per_nonworse,
        "pooled_exact_agreement_plus_3pp":h["exact_agreement"]>=d1["exact_agreement"]+0.03,
        "opposite_trend_conflict_nonworse":h["opposite_trend_conflict_rate"]<=d1["opposite_trend_conflict_rate"],
        "pooled_decisive_coverage_floor_and_nonregression":h["pooled_decisive_coverage"]>=0.50 and h["pooled_decisive_coverage"]>=d1["pooled_decisive_coverage"]-0.02,
        "each_offset_side_decisive_coverage_at_least_40pct":coverage_floor,
        "decisive_class_diversity":shares.get("uptrend",0)>=0.15 and shares.get("downtrend",0)>=0.15 and shares.get("range",0)>=0.02,
    }
    passed=all(gates.values())
    result={
        "schema":"two_wave_whole_window_huber_direction_result@0.6.21",
        "verdict":"v0621_whole_window_huber_direction_research_component_pass" if passed else "v0621_whole_window_huber_direction_rejected",
        "controls":{"filtered_pairs":57029,"raw_strict_pairs":29453,"both_v0618_qualified_pairs":total_bothq,"reproduced":True},
        "pooled":{"D1":d1,"v0621":h},"per_offset":per_offset,"gates":gates,
        "qualification_policy":"v0.6.18","qualification_changed":False,"morphology_acceptance":False,
        "future_outcome_used":False,"trade_authority":False,"production_authority":False,
    }
    (args.output/"summary.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    write_card(args.output/"RESULT_CARD.md",result)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))

if __name__=="__main__": main()
