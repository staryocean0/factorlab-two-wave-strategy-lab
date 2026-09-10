#!/usr/bin/env python3
"""Formal v0.6.27 state-relative margin direction replay."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.d1_huber_erosion_consensus_v0623 import d1_primary_erosion_consensus_rescue
from factor_lab.visual_structure.two_wave.d1_huber_margin_rescue_v0625 import d1_primary_margin_rescue
from factor_lab.visual_structure.two_wave.d1_huber_state_relative_margin_v0627 import (
    RELATIVE_MARGIN_FRACTION,
    d1_primary_state_relative_margin_rescue,
)
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import build_edge_graph
from scripts.run_two_wave_d1_huber_erosion_consensus_v0623 import (
    EXPECTED_BOTHQ, EXPECTED_D1_COVERAGE, EXPECTED_D1_EXACT, EXPECTED_FILTERED,
    EXPECTED_RAW, EXPECTED_V0618, VIEWS, fkey, find_one, load_gz, metrics, qmatrix,
    reconstruct_pair,
)

EXPECTED_V0623_EXACT_COUNT = 1397
EXPECTED_V0625_EXACT_COUNT = 1402


def state(row, bars, closes, view):
    pair = reconstruct_pair(row, bars, view)
    d1 = str(pair["direction_versions"]["D1"])
    amp = float(pair["amplitude_unit_price"])
    raw = row["published_raw_occurrence_bars"]
    v23 = d1_primary_erosion_consensus_rescue(d1, closes, raw, amp)
    v25 = d1_primary_margin_rescue(d1, closes, raw, amp)
    v27 = d1_primary_state_relative_margin_rescue(d1, closes, raw, amp)
    if d1 != "uncertain":
        assert v23["classification"] == d1
        assert v25["classification"] == d1
        assert v27["classification"] == d1
        assert not v27["D1_decisive_overridden"]
    return {
        "D1": d1,
        "v0623": str(v23["classification"]),
        "v0625": str(v25["classification"]),
        "v0627": str(v27["classification"]),
        "v0623_rescue": bool(v23["rescue_applied"]),
        "v0625_rescue": bool(v25["rescue_applied"]),
        "v0627_rescue": bool(v27["rescue_applied"]),
        "v0627_required_margin": v27.get("required_absolute_margin"),
        "overridden": bool(v27["D1_decisive_overridden"]),
    }


def write_card(path, result):
    d1=result["pooled"]["D1"]; v25=result["pooled"]["v0625"]; v27=result["pooled"]["v0627"]
    lines=[
        "# Two-Wave v0.6.27 state-relative margin rescue result","",
        f"Formal verdict: **`{result['verdict']}`**","",
        f"Frozen relative margin fraction: **{RELATIVE_MARGIN_FRACTION:.0%}**.",
        "Trend absolute margin remains 0.10; Range equivalent state-relative margin is 0.03.",
        f"D1 decisive overrides: **{result['rescue_audit']['D1_decisive_override_count']}**.","",
        "| metric | D1 | v0.6.25 | v0.6.27 |","|---|---:|---:|---:|",
        f"| pooled exact agreement | {d1['exact_agreement']:.2%} | {v25['exact_agreement']:.2%} | {v27['exact_agreement']:.2%} |",
        f"| pooled decisive coverage | {d1['pooled_decisive_coverage']:.2%} | {v25['pooled_decisive_coverage']:.2%} | {v27['pooled_decisive_coverage']:.2%} |",
        f"| decisive agreement | {d1['decisive_agreement']:.2%} | {v25['decisive_agreement']:.2%} | {v27['decisive_agreement']:.2%} |",
        f"| opposite trend conflicts | {d1['opposite_trend_conflict_count']} | {v25['opposite_trend_conflict_count']} | {v27['opposite_trend_conflict_count']} |","",
        "Per-offset exact agreement:","","| offset | D1 | v0.6.25 | v0.6.27 | delta vs D1 pp |","|---|---:|---:|---:|---:|",
    ]
    for view,row in result["per_offset"].items():
        b=row["D1"]["exact_agreement"]; x=row["v0625"]["exact_agreement"]; y=row["v0627"]["exact_agreement"]
        lines.append(f"| {view} | {b:.2%} | {x:.2%} | {y:.2%} | {(y-b)*100:.2f} |")
    lines += ["","Promotion gates:"] + [f"- {k}: **{v}**" for k,v in result["gates"].items()]
    lines += ["","Qualification remains frozen at v0.6.18. Independent morphology acceptance remains false; no trading or production authority follows."]
    path.write_text("\n".join(lines)+"\n")


def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",type=Path,required=True); p.add_argument("--output",type=Path,required=True)
    args=p.parse_args(); args.output.mkdir(parents=True,exist_ok=True)

    filtered={}; records={}; maps={}; bars={}; closes={}; states={}
    overrides=0; rescued23=Counter(); rescued25=Counter(); rescued27=Counter()
    for view in VIEWS:
        filtered[view]=load_gz(find_one(args.input,f"filtered-{view}.json.gz"))
        records[view]=load_gz(find_one(args.input,f"records-{view}.json.gz"))
        maps[view]={fkey(r):r for r in records[view]}
        bars[view],_=load_development_bars(ROOT/f"data/development/{view}.parquet",ROOT/"data/manifest.json")
        closes[view]=[float(x["close"]) for x in bars[view]]
        states[view]={}
        for row in records[view]:
            if not bool(row["candidate_qualified"]): continue
            s=state(row,bars[view],closes[view],view); states[view][fkey(row)]=s
            overrides += int(s["overridden"])
            if s["v0623_rescue"]: rescued23[s["v0623"]]+=1
            if s["v0625_rescue"]: rescued25[s["v0625"]]+=1
            if s["v0627_rescue"]: rescued27[s["v0627"]]+=1
    assert overrides==0

    main_view="5m_offset_0"; total=0; pd1=[]; p25=[]; p27=[]; per={}
    for view in VIEWS[1:]:
        graph=build_edge_graph(filtered[main_view],filtered[view],time_field="five_filtered_occurrence_times",nominal_bar_minutes=5.0,require_phase=True)
        fp=list(graph.mutual_unique_matches); assert len(fp)==EXPECTED_FILTERED[view]
        strict=[]
        for i,j in fp:
            a=maps[main_view].get(fkey(filtered[main_view][i])); b=maps[view].get(fkey(filtered[view][j]))
            if a is not None and b is not None and strict_anchor_edge(a,b,5.0) is not None: strict.append((a,b))
        assert len(strict)==EXPECTED_RAW[view]; assert qmatrix(strict)==EXPECTED_V0618[view]
        both=[(a,b) for a,b in strict if a["candidate_qualified"] and b["candidate_qualified"]]; total += len(both)
        d=[]; x=[]; y=[]
        for a,b in both:
            sa=states[main_view][fkey(a)]; sb=states[view][fkey(b)]
            d.append((sa["D1"],sb["D1"])); x.append((sa["v0625"],sb["v0625"])); y.append((sa["v0627"],sb["v0627"]))
        pd1 += d; p25 += x; p27 += y
        per[view]={"D1":metrics(d),"v0625":metrics(x),"v0627":metrics(y)}
    assert total==EXPECTED_BOTHQ
    d1=metrics(pd1); v25=metrics(p25); v27=metrics(p27)
    assert abs(d1["exact_agreement"]-EXPECTED_D1_EXACT)<=1e-12
    assert abs(d1["pooled_decisive_coverage"]-EXPECTED_D1_COVERAGE)<=1e-12
    assert d1["exact_agreement_count"]==1400 and d1["decisive_agreement"]==1.0 and d1["opposite_trend_conflict_count"]==0
    assert v25["exact_agreement_count"]==EXPECTED_V0625_EXACT_COUNT
    shares=v27["pooled_decisive_label_shares"]
    gates={
        "upstream_controls":True,
        "D1_controls_reproduced":True,
        "v0625_control_reproduced":True,
        "D1_decisive_override_zero":overrides==0,
        "all_offsets_exact_agreement_nonworse":all(r["v0627"]["exact_agreement"]>=r["D1"]["exact_agreement"] for r in per.values()),
        "pooled_exact_agreement_nonworse":v27["exact_agreement"]>=d1["exact_agreement"],
        "pooled_decisive_coverage_material":v27["pooled_decisive_coverage"]>=0.65 and v27["pooled_decisive_coverage"]>=d1["pooled_decisive_coverage"]+0.15,
        "each_offset_side_decisive_coverage_at_least_55pct":all(min(r["v0627"]["main_decisive_coverage"],r["v0627"]["other_decisive_coverage"])>=0.55 for r in per.values()),
        "pooled_decisive_agreement_at_least_99_5pct":v27["decisive_agreement"]>=0.995,
        "opposite_trend_conflict_zero":v27["opposite_trend_conflict_count"]==0,
        "decisive_class_diversity":shares.get("uptrend",0)>=0.15 and shares.get("downtrend",0)>=0.15 and shares.get("range",0)>=0.02,
        "nonzero_rescue":sum(rescued27.values())>0,
    }
    passed=all(gates.values())
    result={
        "schema":"two_wave_d1_huber_state_relative_margin_result@0.6.27",
        "verdict":"v0627_D1_primary_state_relative_margin_rescue_direction_research_component_pass" if passed else "v0627_D1_primary_state_relative_margin_rescue_direction_rejected",
        "controls":{"filtered_pairs":57029,"raw_strict_pairs":29453,"both_v0618_qualified_pairs":total,"D1_exact_count":d1["exact_agreement_count"],"v0625_exact_count":v25["exact_agreement_count"],"reproduced":True},
        "rescue_audit":{"D1_decisive_override_count":overrides,"v0623_rescued_record_count":sum(rescued23.values()),"v0625_rescued_record_count":sum(rescued25.values()),"v0627_rescued_record_count":sum(rescued27.values()),"v0627_rescued_label_counts":dict(rescued27),"relative_margin_fraction":RELATIVE_MARGIN_FRACTION,"trend_required_absolute_margin":0.10,"range_required_absolute_margin":0.03},
        "pooled":{"D1":d1,"v0625":v25,"v0627":v27},"per_offset":per,"gates":gates,
        "qualification_policy":"v0.6.18","qualification_changed":False,"morphology_acceptance":False,"future_outcome_used":False,"trade_authority":False,"production_authority":False,
    }
    (args.output/"summary.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    write_card(args.output/"RESULT_CARD.md",result)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))

if __name__=="__main__": main()
