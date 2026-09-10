#!/usr/bin/env python3
"""Formal read-only v0.6.28 attribution of v0.6.27 Range rescues."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.d1_huber_margin_rescue_v0625 import d1_primary_margin_rescue
from factor_lab.visual_structure.two_wave.d1_huber_state_relative_margin_v0627 import d1_primary_state_relative_margin_rescue
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import build_edge_graph
from factor_lab.visual_structure.two_wave.v0627_range_rescue_attribution_v0628 import (
    exactness_transition,
    normalized_range_support_dispersion,
    pair_range_topology,
    summarize,
)
from scripts.run_two_wave_d1_huber_erosion_consensus_v0623 import (
    EXPECTED_BOTHQ, EXPECTED_FILTERED, EXPECTED_RAW, EXPECTED_V0618, VIEWS,
    fkey, find_one, load_gz, metrics, qmatrix, reconstruct_pair,
)

EXPECTED_D1_EXACT = 1400
EXPECTED_V0625_EXACT = 1402
EXPECTED_V0627_EXACT = 1388


def state_details(row, bars, closes, view):
    pair = reconstruct_pair(row, bars, view)
    d1 = str(pair["direction_versions"]["D1"])
    raw = row["published_raw_occurrence_bars"]
    amp = float(pair["amplitude_unit_price"])
    v25 = d1_primary_margin_rescue(d1, closes, raw, amp)
    v27 = d1_primary_state_relative_margin_rescue(d1, closes, raw, amp)
    before = str(v25["classification"]); after = str(v27["classification"])
    changed = before != after
    if changed and not (before == "uncertain" and after == "range"):
        raise AssertionError(f"unexpected v0625->v0627 label change: {before}->{after}")
    detail = {"D1": d1, "v0625": before, "v0627": after, "changed_to_range": changed}
    if changed:
        span = float(v27["support_score_span"])
        margin = float(v27["consensus_margin_to_frozen_boundary"])
        score_map = v27["support_scores"]
        if not isinstance(score_map, dict):
            raise AssertionError("v0623 support_scores must remain a mapping")
        scores = [float(x) for x in score_map.values()]
        detail.update({
            "range_margin": margin,
            "range_support_span": span,
            "range_support_dispersion": normalized_range_support_dispersion(span),
            "support_score_min": min(scores),
            "support_score_max": max(scores),
            "support_scores": {str(k): float(v) for k, v in score_map.items()},
        })
    return detail


def write_jsonl_gz(path: Path, rows):
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_card(path: Path, result: dict):
    t=result["pair_transitions"]; g=result["groups"]
    lines=[
        "# Two-Wave v0.6.28 v0.6.27 Range-rescue attribution result","",
        f"Formal attribution: **`{result['formal_attribution']}`**","",
        "This diagnostic changed no recognizer rule.","",
        "Frozen exact-count controls:",
        f"- D1: **{result['controls']['D1_exact_count']} / 1462**",
        f"- v0.6.25: **{result['controls']['v0625_exact_count']} / 1462**",
        f"- v0.6.27: **{result['controls']['v0627_exact_count']} / 1462**","",
        "Pair transitions v0.6.25 -> v0.6.27:",
        f"- retained exact: **{t['retained_exact']}**",
        f"- introduced harm: **{t['introduced_harm']}**",
        f"- repaired v0.6.25 nonexact: **{t['repaired_v0625_nonexact']}**",
        f"- persistent nonexact: **{t['persistent_nonexact']}**","",
        "New-Range topology:",
    ]
    for k,v in result["range_topology_counts"].items(): lines.append(f"- {k}: **{v}**")
    lines += ["","Range support-dispersion groups:","","| group | n sides | median | p25 | p90 |","|---|---:|---:|---:|---:|"]
    for key in ("introduced_harm","successful_exact_or_repaired"):
        d=g[key]["dispersion"]
        def f(x): return "n/a" if x is None else f"{x:.4f}"
        lines.append(f"| {key} | {d['n']} | {f(d['median'])} | {f(d['p25'])} | {f(d['p90'])} |")
    lines += ["","Frozen attribution gates:"] + [f"- {k}: **{v}**" for k,v in result["gates"].items()]
    lines += ["",f"Next-step authorization: **{result['next_step_authorized']}**","","Qualification remains v0.6.18; direction winner remains unset; morphology acceptance remains false."]
    path.write_text("\n".join(lines)+"\n")


def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",type=Path,required=True); p.add_argument("--output",type=Path,required=True)
    args=p.parse_args(); args.output.mkdir(parents=True,exist_ok=True)

    filtered={}; records={}; maps={}; bars={}; closes={}; states={}
    for view in VIEWS:
        filtered[view]=load_gz(find_one(args.input,f"filtered-{view}.json.gz"))
        records[view]=load_gz(find_one(args.input,f"records-{view}.json.gz"))
        maps[view]={fkey(r):r for r in records[view]}
        bars[view],_=load_development_bars(ROOT/f"data/development/{view}.parquet",ROOT/"data/manifest.json")
        closes[view]=[float(b["close"]) for b in bars[view]]
        states[view]={}
        for row in records[view]:
            if bool(row["candidate_qualified"]):
                states[view][fkey(row)] = state_details(row,bars[view],closes[view],view)

    main_view="5m_offset_0"; total=0; pd1=[]; p25=[]; p27=[]; audit=[]
    transitions=Counter(); topology=Counter(); harmful=[]; successful=[]
    for view in VIEWS[1:]:
        graph=build_edge_graph(filtered[main_view],filtered[view],time_field="five_filtered_occurrence_times",nominal_bar_minutes=5.0,require_phase=True)
        fp=list(graph.mutual_unique_matches); assert len(fp)==EXPECTED_FILTERED[view]
        strict=[]
        for i,j in fp:
            a=maps[main_view].get(fkey(filtered[main_view][i])); b=maps[view].get(fkey(filtered[view][j]))
            if a is not None and b is not None and strict_anchor_edge(a,b,5.0) is not None: strict.append((a,b))
        assert len(strict)==EXPECTED_RAW[view]; assert qmatrix(strict)==EXPECTED_V0618[view]
        both=[(a,b) for a,b in strict if a["candidate_qualified"] and b["candidate_qualified"]]; total += len(both)
        for a,b in both:
            sa=states[main_view][fkey(a)]; sb=states[view][fkey(b)]
            pd1.append((sa["D1"],sb["D1"])); p25.append((sa["v0625"],sb["v0625"])); p27.append((sa["v0627"],sb["v0627"]))
            tr=exactness_transition(sa["v0625"],sb["v0625"],sa["v0627"],sb["v0627"]); transitions[tr]+=1
            top=pair_range_topology(sa["v0625"],sb["v0625"],sa["v0627"],sb["v0627"]); topology[top]+=1
            changed_sides=[]
            for side,label,s in (("main",main_view,sa),("other",view,sb)):
                if s["changed_to_range"]:
                    row={"side":side,"view":label,"margin":s["range_margin"],"span":s["range_support_span"],"dispersion":s["range_support_dispersion"],"support_scores":s["support_scores"]}
                    changed_sides.append(row)
                    if tr=="introduced_harm": harmful.append(row["dispersion"])
                    if tr in {"retained_exact","repaired_v0625_nonexact"} and sa["v0627"]==sb["v0627"]: successful.append(row["dispersion"])
            if changed_sides:
                audit.append({"offset":view,"transition":tr,"topology":top,"v0625":[sa["v0625"],sb["v0625"]],"v0627":[sa["v0627"],sb["v0627"]],"changed_sides":changed_sides})
    assert total==EXPECTED_BOTHQ
    md1=metrics(pd1); m25=metrics(p25); m27=metrics(p27)
    assert md1["exact_agreement_count"]==EXPECTED_D1_EXACT
    assert m25["exact_agreement_count"]==EXPECTED_V0625_EXACT
    assert m27["exact_agreement_count"]==EXPECTED_V0627_EXACT
    assert sum(transitions.values())==EXPECTED_BOTHQ

    introduced=transitions["introduced_harm"]
    one_sided_harm=sum(1 for r in audit if r["transition"]=="introduced_harm" and len(r["changed_sides"])==1)
    h=summarize(harmful); s=summarize(successful)
    separation=False
    if h["n"] and s["n"]:
        separation=(h["median"] >= 1.5*s["median"]) or (h["p25"] > s["median"])
    gates={
        "upstream_controls":True,
        "all_label_changes_uncertain_to_range":True,
        "introduced_harm_one_sided_fraction_at_least_80pct":introduced>0 and one_sided_harm/introduced>=0.80,
        "support_dispersion_separation":separation,
        "minimum_group_sizes":h["n"]>=20 and s["n"]>=20,
    }
    authorized=all(gates.values())
    formal="v0628_range_rescue_harm_is_one_sided_and_support_dispersion_separates" if authorized else "v0628_range_rescue_topology_does_not_authorize_support_dispersion_gate"
    result={
        "schema":"two_wave_v0627_range_rescue_attribution_result@0.6.28",
        "formal_attribution":formal,
        "controls":{"filtered_pairs":57029,"raw_strict_pairs":29453,"both_v0618_qualified_pairs":total,"D1_exact_count":md1["exact_agreement_count"],"v0625_exact_count":m25["exact_agreement_count"],"v0627_exact_count":m27["exact_agreement_count"],"reproduced":True},
        "pair_transitions":dict(transitions),"range_topology_counts":dict(topology),
        "introduced_harm_one_sided_count":one_sided_harm,"introduced_harm_one_sided_fraction":one_sided_harm/introduced if introduced else None,
        "groups":{"introduced_harm":{"dispersion":h},"successful_exact_or_repaired":{"dispersion":s}},
        "gates":gates,"next_step_authorized":"single_view_range_support_dispersion_gate_challenger" if authorized else "no_support_dispersion_gate_from_v0628",
        "qualification_policy":"v0.6.18","recognizer_changed":False,"morphology_acceptance":False,"future_outcome_used":False,"trade_authority":False,"production_authority":False,
    }
    (args.output/"summary.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    write_jsonl_gz(args.output/"range_rescue_audit.jsonl.gz",audit)
    write_card(args.output/"RESULT_CARD.md",result)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))

if __name__=="__main__": main()
