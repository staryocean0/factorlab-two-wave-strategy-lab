from types import SimpleNamespace as NS
import numpy as np
from factor_lab.visual_structure.two_wave.ordinal0_predecessor_support_v064 import locate_birth_predecessor,project_birth_with_predecessor,summarize_candidate_group

def node(i,kind,confirm=None,nid=None):
 return NS(node=NS(occurrence_index=i,confirmation_index=i+1 if confirm is None else confirm,kind=kind,node_id=nid or f'n{i}'))
def birth(nodes,confirm=40):
 return NS(nodes=tuple(nodes),occurrence_indices=tuple(x.node.occurrence_index for x in nodes),confirmation_index=confirm,event_id='b')
def bars(n=60,closes=None):
 closes=closes or [100.0]*n
 return [{'timestamp':f'2020-01-02T00:{i:02d}:00+00:00','close':float(closes[i])} for i in range(n)]
def fixture():
 pred=node(5,'high'); ns=[node(10,'low'),node(20,'high'),node(30,'low'),node(40,'high'),node(50,'low',confirm=52)]; return pred,ns,birth(ns,55)
def good_closes():
 x=[100.0]*60;x[8]=90;x[15]=110;x[25]=92;x[35]=115;x[51]=91;return x

def test_valid_predecessor():
 p,ns,b=fixture();o=locate_birth_predecessor(b,[p,*ns]);assert o['valid'] and o['predecessor'].node.node_id==p.node.node_id
def test_no_predecessor_is_left_censor():
 _,ns,b=fixture();o=project_birth_with_predecessor(b,ns,bars(closes=good_closes()));assert not o['valid'] and o['reason']=='ordinal0_left_censored_no_predecessor'
def test_predecessor_kind_mismatch_invalid():
 p,ns,b=fixture();p.node.kind='low';o=project_birth_with_predecessor(b,[p,*ns],bars(closes=good_closes()));assert o['reason']=='predecessor_kind_not_opposite'
def test_predecessor_confirmation_after_birth_invalid():
 p,ns,b=fixture();p.node.confirmation_index=56;o=project_birth_with_predecessor(b,[p,*ns],bars(closes=good_closes()));assert o['reason']=='predecessor_confirmed_after_tuple_birth'
def test_exact_tie_keeps_last_occurrence():
 p,ns,b=fixture();x=good_closes();x[8]=x[9]=90;o=project_birth_with_predecessor(b,[p,*ns],bars(closes=x));assert o['valid'] and o['raw_occurrence_bars'][0]==9 and o['windows'][0]['exact_extreme_tie_count']==2
def test_future_append_after_confirmation_no_rewrite():
 p,ns,b=fixture();bs=bars(closes=good_closes());a=project_birth_with_predecessor(b,[p,*ns],bs);bs2=bs+[{'timestamp':'2020-01-03T00:00:00+00:00','close':1e9}];c=project_birth_with_predecessor(b,[p,*ns],bs2);assert a['raw_occurrence_bars']==c['raw_occurrence_bars']
def test_later_ordinals_follow_same_sequential_rule_once_ordinal0_fixed():
 p,ns,b=fixture();o=project_birth_with_predecessor(b,[p,*ns],bars(closes=good_closes()));assert o['valid'];assert [w['lower_bar'] for w in o['windows'][1:]]==[x+1 for x in o['raw_occurrence_bars'][:-1]]
def test_group_single_valuedness():
 rows=[{'valid':True,'raw_occurrence_bars':[1,2,3,4,5]},{'valid':True,'raw_occurrence_bars':[1,2,3,4,5]}];assert summarize_candidate_group(rows)['status']=='single_valued_candidate_projection'
def test_predecessor_support_can_include_extremum_excluded_by_mirror():
 # f0=10,f1=20 => mirror lower=0; construct a harmless-offset analogue where index mirror starts at 2,
 # while the real predecessor at absolute phase boundary still starts before a shared first extremum.
 p,ns,b=fixture();x=good_closes();x[6]=89;o=project_birth_with_predecessor(b,[p,*ns],bars(closes=x));assert o['valid'];assert o['windows'][0]['lower_bar']==6 and o['raw_occurrence_bars'][0]==6
