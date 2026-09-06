from __future__ import annotations
import numpy as np
import pytest
from factor_lab.visual_structure.two_wave.qualification_disagreement_v067 import (
    classify_primary_family, reason_metric_and_margin, path_metrics_from_times,
    one_minute_path_profile, one_minute_path_reason_flag, diagnostic_relation,
    anchor_displacement, session_calendar_overlay,
)
from factor_lab.visual_structure.two_wave.raw_projection_identity_v062 import CanonicalPathIndex


def q(**kw):
    base={
        'leg_durations':[4,5,6,7], 'cycle_durations':[9,13], 'leg_efficiencies':[.7,.6,.4,.8],
        'leg_jump_shares':[.2,.6,.3,.1], 'leg_flat_shares':[0,.1,.2,.3], 'amplitude_ratio':2.2,
        'confirmation_delay_bars':9, 'observed_trading_days':4, 'wall_days':8.0,
    }; base.update(kw); return base

def idx():
    return CanonicalPathIndex(
        timestamps=tuple(f'1970-01-01T00:{i:02d}:00+00:00' for i in range(11)),
        minutes=np.arange(11,dtype=float), closes=np.array([1,2,3,2,1,2,3,4,3,2,1],dtype=float)
    )

def test_reason_family_single_and_mixed():
    assert classify_primary_family(['jump_dominated_leg'])=='path_metric_only'
    assert classify_primary_family(['short_leg','short_cycle'])=='duration_geometry_only'
    assert classify_primary_family(['jump_dominated_leg','short_leg'])=='mixed_multi_family'

def test_exact_signed_margin_formulas():
    x=q()
    assert reason_metric_and_margin('jump_dominated_leg',x)['signed_violation_margin']==pytest.approx(.1)
    assert reason_metric_and_margin('inefficient_leg',x)['signed_violation_margin']==pytest.approx(.1)
    assert reason_metric_and_margin('short_leg',x)['signed_violation_margin']==0.0
    assert reason_metric_and_margin('amplitude_mismatch',x)['signed_violation_margin']==pytest.approx(.2)
    assert reason_metric_and_margin('confirmation_too_late',x)['signed_violation_margin']==1.0

def test_one_minute_path_metrics():
    out=path_metrics_from_times('1970-01-01T00:00:00+00:00','1970-01-01T00:05:00+00:00',idx())
    assert out is not None and out['rows']==6
    assert 0 <= out['efficiency'] <= 1
    assert 0 <= out['jump_share'] <= 1

def test_path_profile_and_flags():
    p=one_minute_path_profile([0,2,4,6,8],idx())
    assert p['available']
    assert isinstance(one_minute_path_reason_flag('jump_dominated_leg',p),bool)
    assert isinstance(one_minute_path_reason_flag('inefficient_leg',p),bool)

def test_diagnostic_relations():
    assert diagnostic_relation(False,False)=='both_pass'
    assert diagnostic_relation(True,True)=='both_fail'
    assert diagnostic_relation(True,False)=='rejected_side_only'
    assert diagnostic_relation(False,True)=='qualified_side_only'
    assert diagnostic_relation(None,False)=='unavailable'

def test_anchor_displacement():
    out=anchor_displacement([0,5,10,15,20],[1,5,12,15,24])
    assert out['deltas_minutes']==[1,0,2,0,4]
    assert out['max_delta_minutes']==4
    assert out['nonzero_anchor_count']==3

def test_session_overlay():
    out=session_calendar_overlay([
        '2020-01-02T03:25:00+00:00','2020-01-02T03:30:00+00:00','2020-01-02T05:00:00+00:00',
        '2020-01-02T05:05:00+00:00','2020-01-02T05:10:00+00:00'], '2020-01-02T05:15:00+00:00')
    assert out['session_boundary_nearby'] is True
    assert out['lunch_gap_crossed'] is True


def test_constant_one_minute_path_uses_frozen_zero_length_convention():
    z=CanonicalPathIndex(
        timestamps=tuple(f'1970-01-01T00:{i:02d}:00+00:00' for i in range(4)),
        minutes=np.arange(4,dtype=float), closes=np.ones(4,dtype=float))
    out=path_metrics_from_times(0,3,z)
    assert out['efficiency']==0.0
    assert out['jump_share']==1.0
    assert out['flat_share']==1.0

def test_unknown_reason_fails_closed():
    with pytest.raises(ValueError):
        classify_primary_family(['not_a_frozen_reason'])
