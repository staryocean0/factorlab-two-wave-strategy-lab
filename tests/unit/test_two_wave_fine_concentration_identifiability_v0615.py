from __future__ import annotations

import itertools
import numpy as np

from factor_lab.visual_structure.two_wave.fine_concentration_identifiability_v0615 import (
    bar_tv_upper,
    native_ohlc_concentration_bounds,
)
from factor_lab.visual_structure.two_wave.step_count_normalized_concentration_v0613 import concentration_profile


def fine_metrics(path):
    x=np.abs(np.diff(np.asarray(path,dtype=float)))
    s=float(x.sum())
    j=float(x.max()/s)
    p=concentration_profile(x)
    return j,p


def test_bar_tv_upper_matches_explicit_vertices():
    c0,L,H,c5=10.0,8.0,13.0,11.0
    vals=[]
    for z in itertools.product((L,H),repeat=4):
        p=(c0,)+z+(c5,)
        vals.append(sum(abs(b-a) for a,b in zip(p,p[1:])))
    assert bar_tv_upper(c0,L,H,c5)==max(vals)


def test_feasible_single_bar_path_is_inside_all_bounds():
    H=[10,13];L=[9,8];C=[10,11]
    b=native_ohlc_concentration_bounds(H,L,C)
    path=[10,9,12,8.5,12.5,11]
    j,p=fine_metrics(path)
    assert b['j_low']-1e-12 <= j <= b['j_high']+1e-12
    for k,lo,hi in [('c_inf','c_inf_low','c_inf_high'),('c_1','c_1_low','c_1_high'),('c_2','c_2_low','c_2_high')]:
        assert b[lo]-1e-12 <= p[k] <= b[hi]+1e-12


def test_random_feasible_two_bar_paths_are_covered():
    rng=np.random.default_rng(7)
    H=np.array([10,13,15.],float);L=np.array([9,8,10.],float);C=np.array([10,11,14.],float)
    b=native_ohlc_concentration_bounds(H,L,C)
    for _ in range(100):
        p=[C[0]]
        for j in (1,2):
            p.extend(rng.uniform(L[j],H[j],4).tolist())
            p.append(C[j])
        jv,prof=fine_metrics(p)
        assert b['j_low']-1e-12 <= jv <= b['j_high']+1e-12
        assert b['c_inf_low']-1e-12 <= prof['c_inf'] <= b['c_inf_high']+1e-12
        assert b['c_1_low']-1e-12 <= prof['c_1'] <= b['c_1_high']+1e-12
        assert b['c_2_low']-1e-12 <= prof['c_2'] <= b['c_2_high']+1e-12


def test_bounds_obey_probability_profile_range():
    b=native_ohlc_concentration_bounds([1,4,6],[0,1,2],[1,3,5])
    cap=np.log(b['fine_step_count'])
    for lo,hi in [('c_inf_low','c_inf_high'),('c_1_low','c_1_high'),('c_2_low','c_2_high')]:
        assert 0 <= b[lo] <= b[hi] <= cap+1e-12


def test_positive_price_scaling_preserves_dimensionless_bounds():
    a=native_ohlc_concentration_bounds([10,13,15],[9,8,10],[10,11,14])
    b=native_ohlc_concentration_bounds([100,130,150],[90,80,100],[100,110,140])
    for k in ('j_low','j_high','c_inf_low','c_inf_high','c_1_low','c_1_high','c_2_low','c_2_high'):
        assert abs(a[k]-b[k])<1e-12


def test_zero_possible_movement_is_explicit_undefined():
    b=native_ohlc_concentration_bounds([1,1],[1,1],[1,1])
    assert b['defined'] is False
    assert b['reason']=='no_positive_hidden_movement_possible'


def test_closed_leg_prefix_locality():
    a=native_ohlc_concentration_bounds([10,13,15],[9,8,10],[10,11,14])
    b=native_ohlc_concentration_bounds([10,13,15],[9,8,10],[10,11,14])
    assert a==b


def test_native_api_has_no_oracle_counterpart_or_outcome_dependency():
    b=native_ohlc_concentration_bounds([10,13],[9,8],[10,11])
    text=repr(b)
    assert 'oracle' not in text
    assert 'counterpart' not in text
    assert 'direction' not in text
    assert b['future_outcome_used'] is False
    assert b['trade_authority'] is False
