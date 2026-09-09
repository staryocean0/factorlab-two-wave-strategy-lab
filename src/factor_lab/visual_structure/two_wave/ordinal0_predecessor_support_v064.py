"""v0.6.4 repair-POC helpers: replace only ordinal0 mirror support with a real birth-level predecessor."""
from __future__ import annotations
from collections import Counter
from typing import Sequence
import numpy as np

SCHEMA = "two_wave_ordinal0_predecessor_support@0.6.4"
CANDIDATE = "birth_scale_predecessor_filtered_phase_start"


def _last_argextreme(values: np.ndarray, kind: str) -> tuple[int, float, int]:
    if values.ndim != 1 or not len(values):
        raise ValueError("nonempty one-dimensional values required")
    if kind == "high": target=float(np.max(values))
    elif kind == "low": target=float(np.min(values))
    else: raise ValueError("kind must be high or low")
    pos=np.flatnonzero(values==target)
    return int(pos[-1]), target, int(len(pos))


def locate_birth_predecessor(birth, ridge_nodes_level: Sequence[object]) -> dict:
    ordered=sorted(ridge_nodes_level,key=lambda r:(int(r.node.occurrence_index),int(r.node.confirmation_index),str(r.node.node_id)))
    birth_ids=[str(r.node.node_id) for r in birth.nodes]
    ids=[str(r.node.node_id) for r in ordered]
    try: start=ids.index(birth_ids[0])
    except ValueError: return {"valid":False,"reason":"birth_first_node_missing_from_level","predecessor":None}
    if ids[start:start+5] != birth_ids:
        return {"valid":False,"reason":"birth_nodes_not_consecutive_at_level","predecessor":None}
    if start==0:
        return {"valid":False,"reason":"ordinal0_left_censored_no_predecessor","predecessor":None}
    pred=ordered[start-1]
    if str(pred.node.kind)==str(birth.nodes[0].node.kind):
        return {"valid":False,"reason":"predecessor_kind_not_opposite","predecessor":pred}
    if int(pred.node.confirmation_index)>int(birth.confirmation_index):
        return {"valid":False,"reason":"predecessor_confirmed_after_tuple_birth","predecessor":pred}
    return {"valid":True,"reason":None,"predecessor":pred}


def project_birth_with_predecessor(birth, ridge_nodes_level: Sequence[object], bars: Sequence[dict], closes: np.ndarray|None=None) -> dict:
    pred_info=locate_birth_predecessor(birth,ridge_nodes_level)
    if not pred_info["valid"]:
        return {"schema":SCHEMA,"candidate":CANDIDATE,"event_id":str(birth.event_id),"valid":False,"reason":pred_info["reason"],"raw_occurrence_bars":None,"windows":[]}
    if closes is None: closes=np.asarray([float(x["close"]) for x in bars],dtype=float)
    if closes.ndim!=1 or len(closes)!=len(bars): raise ValueError("closes must align with bars")
    filtered=[int(x) for x in birth.occurrence_indices]
    kinds=[str(x.node.kind) for x in birth.nodes]
    member_confirmation=int(birth.nodes[-1].node.confirmation_index)
    selection_confirmation=int(birth.confirmation_index)
    if member_confirmation>=len(bars) or selection_confirmation>=len(bars):
        return {"schema":SCHEMA,"candidate":CANDIDATE,"event_id":str(birth.event_id),"valid":False,"reason":"confirmation_outside_bars","raw_occurrence_bars":None,"windows":[]}
    pred=pred_info["predecessor"]
    lo=int(pred.node.occurrence_index)+1
    uppers=[filtered[1]-1,filtered[2]-1,filtered[3]-1,filtered[4]-1,member_confirmation]
    occ=[];prices=[];windows=[]
    for ordinal,(kind,hi0) in enumerate(zip(kinds,uppers)):
        hi=min(int(hi0),member_confirmation)
        if lo>hi:
            return {"schema":SCHEMA,"candidate":CANDIDATE,"event_id":str(birth.event_id),"valid":False,"reason":"raw_projection_empty_phase_window","phase_ordinal":ordinal,"raw_occurrence_bars":None,"windows":windows}
        rel,price,ties=_last_argextreme(closes[lo:hi+1],kind);idx=lo+rel
        occ.append(idx);prices.append(price)
        windows.append({"ordinal":ordinal,"kind":kind,"lower_bar":lo,"lower_time":str(bars[lo]["timestamp"]),"upper_bar":hi,"upper_time":str(bars[hi]["timestamp"]),"selected_raw_bar":idx,"selected_raw_time":str(bars[idx]["timestamp"]),"selected_raw_close":price,"exact_extreme_tie_count":ties,"source_predecessor_bar":int(pred.node.occurrence_index) if ordinal==0 else None})
        lo=idx+1
    if any(a>=b for a,b in zip(occ,occ[1:])):
        return {"schema":SCHEMA,"candidate":CANDIDATE,"event_id":str(birth.event_id),"valid":False,"reason":"raw_projection_order_conflict","raw_occurrence_bars":None,"windows":windows}
    for kind,a,b in zip(kinds,prices,prices[1:]):
        if kind=="low" and not b>a:
            return {"schema":SCHEMA,"candidate":CANDIDATE,"event_id":str(birth.event_id),"valid":False,"reason":"raw_projection_not_actual_turn","raw_occurrence_bars":None,"windows":windows}
        if kind=="high" and not b<a:
            return {"schema":SCHEMA,"candidate":CANDIDATE,"event_id":str(birth.event_id),"valid":False,"reason":"raw_projection_not_actual_turn","raw_occurrence_bars":None,"windows":windows}
    return {"schema":SCHEMA,"candidate":CANDIDATE,"event_id":str(birth.event_id),"valid":True,"reason":None,"raw_occurrence_bars":occ,"raw_occurrence_times":[str(bars[i]["timestamp"]) for i in occ],"windows":windows,"predecessor_occurrence_bar":int(pred.node.occurrence_index),"predecessor_confirmation_bar":int(pred.node.confirmation_index),"member_confirmation_bar":member_confirmation,"selection_confirmation_bar":selection_confirmation}


def summarize_candidate_group(rows: Sequence[dict]) -> dict:
    if not rows: raise ValueError("candidate member rows required")
    valid=[r for r in rows if r.get("valid")]; invalid=[r for r in rows if not r.get("valid")]
    ids={tuple(int(x) for x in r["raw_occurrence_bars"]) for r in valid}
    if not valid: status="no_valid_candidate_projection"
    elif len(ids)==1: status="single_valued_candidate_projection"
    else: status="multi_valued_candidate_projection"
    return {"status":status,"member_count":len(rows),"valid_count":len(valid),"invalid_count":len(invalid),"invalid_reasons":dict(sorted(Counter(str(r.get('reason')) for r in invalid).items())),"distinct_valid_raw_identity_count":len(ids),"valid_raw_identities":[list(x) for x in sorted(ids)]}
