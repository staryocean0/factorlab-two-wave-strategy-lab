#!/usr/bin/env python3
"""Formal read-only v0.6.32 attribution of v0.6.31 one-sided Range rescues."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.d1_mutual_median_range_rescue_v0631 import d1_primary_mutual_median_range_rescue
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import build_edge_graph
from factor_lab.visual_structure.two_wave.v0631_residual_attribution_v0632 import (
    classify_one_sided_change,
    summarize_support_slacks,
)
from scripts.run_two_wave_d1_huber_erosion_consensus_v0623 import (
    EXPECTED_BOTHQ, EXPECTED_FILTERED, EXPECTED_RAW, EXPECTED_V0618, VIEWS,
    fkey, find_one, load_gz, metrics, qmatrix, reconstruct_pair,
)

EXPECTED_OLD_EXACT = 1402
EXPECTED_NEW_EXACT = 1384
EXPECTED_TOPOLOGY = {"both":17,"main_only":14,"other_only":12,"none":1419}
EXPECTED_NEW_RANGE = 154


def state(row, bars, closes, view):
    pair = reconstruct_pair(row, bars, view)
    d1 = str(pair["direction_versions"]["D1"])
    out = d1_primary_mutual_median_range_rescue(
        d1, closes, row["published_raw_occurrence_bars"], float(pair["amplitude_unit_price"])
    )
    old = str(out["v0625_classification"])
    new = str(out["classification"])
    if old != new:
        assert old == "uncertain" and new == "range"
    return {"D1":d1,"v0625":old,"v0631":new,"out":out}


def dist(values):
    if not values:
        return {"count":0}
    a=np.asarray(values,dtype=float)
    return {
        "count":int(len(a)),"min":float(np.min(a)),"q25":float(np.quantile(a,.25)),
        "median":float(np.median(a)),"q75":float(np.quantile(a,.75)),"max":float(np.max(a)),
    }


def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",type=Path,required=True); p.add_argument("--output",type=Path,required=True)
    args=p.parse_args(); args.output.mkdir(parents=True,exist_ok=True)

    filtered={}; records={}; maps={}; bars={}; closes={}; states={}
    override_count=0; new_range_count=0
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
            override_count += int(bool(s["out"]["D1_decisive_overridden"]))
            new_range_count += int(bool(s["out"]["new_range_rescue_applied"]))
    assert override_count==0
    assert new_range_count==EXPECTED_NEW_RANGE

    topology=Counter(); pooled_old=[]; pooled_new=[]; audit_rows=[]
    class_counts=Counter(); changed_slacks=defaultdict(list); changed_owner=defaultdict(Counter)
    unchanged_reason=defaultdict(Counter); unchanged_min_slacks=defaultdict(list)
    main_view="5m_offset_0"; total=0

    for view in VIEWS[1:]:
        graph=build_edge_graph(filtered[main_view],filtered[view],time_field="five_filtered_occurrence_times",nominal_bar_minutes=5.0,require_phase=True)
        fp=list(graph.mutual_unique_matches); assert len(fp)==EXPECTED_FILTERED[view]
        strict=[]
        for i,j in fp:
            a=maps[main_view].get(fkey(filtered[main_view][i])); b=maps[view].get(fkey(filtered[view][j]))
            if a is not None and b is not None and strict_anchor_edge(a,b,5.0) is not None: strict.append((a,b))
        assert len(strict)==EXPECTED_RAW[view]; assert qmatrix(strict)==EXPECTED_V0618[view]
        both=[(a,b) for a,b in strict if a["candidate_qualified"] and b["candidate_qualified"]]
        total += len(both)
        for a,b in both:
            sa=states[main_view][fkey(a)]; sb=states[view][fkey(b)]
            old=(sa["v0625"],sb["v0625"]); new=(sa["v0631"],sb["v0631"])
            pooled_old.append(old); pooled_new.append(new)
            lc=old[0]!=new[0]; rc=old[1]!=new[1]
            topo="both" if lc and rc else "main_only" if lc else "other_only" if rc else "none"
            topology[topo]+=1
            if not (lc ^ rc): continue
            semantic=classify_one_sided_change(old,new); class_counts[semantic]+=1
            changed_state=sa if lc else sb; unchanged_state=sb if lc else sa
            changed_view=main_view if lc else view; unchanged_view=view if lc else main_view
            cout=changed_state["out"]; uout=unchanged_state["out"]
            cs=summarize_support_slacks(cout["support_containment_details"])
            changed_slacks[semantic].append(cs["min_containment_slack_iqr"])
            changed_owner[semantic][cs["min_slack_support"]]+=1
            ureason="containment_unavailable"
            us=None
            if uout.get("range_consensus") is False:
                ureason="not_range_consensus"
            elif uout.get("range_margin_gate_pass") is False:
                ureason="range_margin_fail"
            elif uout.get("support_containment_details"):
                us=summarize_support_slacks(uout["support_containment_details"])
                if uout.get("all_supports_mutual_median_containment") is False:
                    ureason="mutual_containment_fail"
                    unchanged_min_slacks[semantic].append(us["min_containment_slack_iqr"])
                else:
                    ureason="containment_pass_but_not_rescued"
            unchanged_reason[semantic][ureason]+=1
            audit_rows.append({
                "offset":view,"topology":topo,"semantic_class":semantic,
                "old_pair":old,"new_pair":new,
                "changed_view":changed_view,"unchanged_view":unchanged_view,
                "changed_min_containment_slack_iqr":cs["min_containment_slack_iqr"],
                "changed_median_containment_slack_iqr":cs["median_containment_slack_iqr"],
                "changed_min_slack_support":cs["min_slack_support"],
                "changed_support_slacks":cs["support_slacks"],
                "changed_range_margin":cout.get("range_margin"),
                "unchanged_reason":ureason,
                "unchanged_min_containment_slack_iqr":None if us is None else us["min_containment_slack_iqr"],
                "unchanged_min_slack_support":None if us is None else us["min_slack_support"],
            })

    assert total==EXPECTED_BOTHQ
    oldm=metrics(pooled_old); newm=metrics(pooled_new)
    assert oldm["exact_agreement_count"]==EXPECTED_OLD_EXACT
    assert newm["exact_agreement_count"]==EXPECTED_NEW_EXACT
    assert dict(topology)==EXPECTED_TOPOLOGY
    assert sum(class_counts.values())==26

    result={
        "schema":"two_wave_v0631_residual_attribution_result@0.6.32",
        "formal_attribution":"v0632_v0631_one_sided_range_rescue_slack_decomposition",
        "controls":{"both_v0618_qualified_pairs":total,"v0625_exact_count":oldm["exact_agreement_count"],"v0631_exact_count":newm["exact_agreement_count"],"v0631_topology":dict(topology),"v0631_new_range_rescues":new_range_count,"reproduced":True},
        "one_sided_semantic_counts":dict(class_counts),
        "changed_side_min_slack_by_class":{k:dist(v) for k,v in changed_slacks.items()},
        "changed_side_min_slack_support_by_class":{k:dict(v) for k,v in changed_owner.items()},
        "unchanged_side_reason_by_class":{k:dict(v) for k,v in unchanged_reason.items()},
        "unchanged_side_min_slack_when_available_by_class":{k:dist(v) for k,v in unchanged_min_slacks.items()},
        "recognizer_changed":False,"qualification_changed":False,"morphology_acceptance":False,
        "future_outcome_used":False,"trade_authority":False,"production_authority":False,
    }
    (args.output/"summary.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    with gzip.open(args.output/"one_sided_audit.jsonl.gz","wt",encoding="utf-8") as fh:
        for row in audit_rows: fh.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")
    card=["# Two-Wave v0.6.32 v0.6.31 residual attribution","",f"Formal attribution: **`{result['formal_attribution']}`**","",
          f"One-sided changes: **{sum(class_counts.values())}**; classes: `{dict(class_counts)}`.","",
          "This diagnostic changes no recognizer. See summary.json and one_sided_audit.jsonl.gz for frozen slack decomposition.",
          "","Independent morphology acceptance remains false; trading and production authority remain false."]
    (args.output/"RESULT_CARD.md").write_text("\n".join(card)+"\n")
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))

if __name__=="__main__": main()
