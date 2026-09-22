from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts"))
import r7_cost_tempo_core as c
import run_R7_native_1m_rejected_excursion as parent
import run_R7_cost_tempo_reversal as runner


def test_parent_h5_numeric_parity_and_h15_monotone():
    p=np.array([0., .1, .4, .2, .3, .1])
    np.testing.assert_allclose(c.path_coordinates(p,.1),parent.path_features(p,.1)[:2],atol=1e-14)
    assert c.path_coordinates(np.arange(16)*.001,.001)[1]==0.


def test_feature_sign_symmetry():
    p=np.array([0., .1, .4, .2, .3, -.1])
    np.testing.assert_allclose(c.path_coordinates(-p,.1),-np.array(c.path_coordinates(p,.1)))


def test_path_and_state_fail_closed():
    with pytest.raises(ValueError): c.path_coordinates(np.zeros(8),.1)
    with pytest.raises(ValueError): c.path_coordinates(np.zeros(6),0.)
    with pytest.raises(ValueError): c.select_horizon(float("nan"),.1)
    with pytest.raises(ValueError): c.point_move_bp(.1,-.01,5)


def test_tempo_is_absolute_vol_not_risk_state():
    assert c.select_horizon(.001,.001)==15
    assert c.select_horizon(.00101,.001)==5


def test_scheduled_session_room():
    t=lambda s: pd.Timestamp("2019-01-02 "+s,tz="Asia/Shanghai")
    assert c.scheduled_room(t("11:15"),15)
    assert not c.scheduled_room(t("11:20"),15)
    assert c.scheduled_room(t("14:55"),5)
    assert not c.scheduled_room(t("14:55"),15)
    assert not c.scheduled_room(t("12:00"),5)


def market():
    segments=[]
    for day in ("2018-12-27","2018-12-28","2019-01-02"):
        for start in ("09:31","13:01"):
            segments.extend(pd.date_range(day+" "+start,periods=120,freq="1min",tz="Asia/Shanghai"))
    ts=pd.DatetimeIndex(segments).tz_convert("UTC")
    lp=np.cumsum(np.sin(np.arange(len(ts))*.71)*.0005)+np.log(5000.)
    z=pd.DataFrame({"bar_end_shanghai":ts,"trading_day":ts.tz_convert("Asia/Shanghai").strftime("%Y-%m-%d"),
                    "close":np.exp(lp),"open":np.exp(lp),"causal_flat_fill":False})
    f=z.loc[z.bar_end_shanghai.dt.minute%5==0,["bar_end_shanghai","close"]]
    return z,f


def test_native_features_prefix_invariant_even_when_labels_unavailable():
    one,five=market()
    stop=650
    full=c.native_scale_frame(one,five,15)
    prefix=c.native_scale_frame(one.iloc[:stop],five.loc[five.bar_end_shanghai<=one.iloc[stop-1].bar_end_shanghai],15)
    earlier=full.loc[full.ts<=one.iloc[stop-1].bar_end_shanghai]
    cols=["ts","sigma","endpoint_z","rejection_signed_z","native_i"]
    pd.testing.assert_frame_equal(prefix[cols].reset_index(drop=True),earlier[cols].reset_index(drop=True))
    assert prefix.target_z.isna().any()


def test_current_day_target_cannot_change_its_forecast():
    rng=np.random.default_rng(42)
    x=pd.DataFrame({"trading_day":["2018-12-28"]*25+["2019-01-02"]*4+["2019-01-03"]*4,
                    "endpoint_z":rng.normal(size=33),"rejection_signed_z":rng.normal(size=33),
                    "target_z":rng.normal(size=33)})
    a,audit=c.daily_forecasts(x,minimum_history=10)
    y=x.copy(); y.loc[y.trading_day=="2019-01-02","target_z"]+=100.
    b,_=c.daily_forecasts(y,minimum_history=10)
    np.testing.assert_allclose(a.loc[a.trading_day=="2019-01-02","forecast_z"],b.loc[b.trading_day=="2019-01-02","forecast_z"])
    assert all(row["history_max_day"]<row["day"] for row in audit)


def test_economic_screen_uses_return_units_not_forecast_z():
    assert c.point_move_bp(.2,.0001,5)<4.
    assert c.point_move_bp(.2,.002,5)>4.
    assert c.point_move_bp(-.2,.002,5)>4.


def trading_fixture():
    ts=pd.date_range("2019-01-02 10:00",periods=31,freq="1min",tz="Asia/Shanghai")
    one=pd.DataFrame({"bar_end_shanghai":ts,"trading_day":"2019-01-02","open":100.,"close":100.1,"causal_flat_fill":False})
    frame=pd.DataFrame({"ts":ts[::5][:-1],"trading_day":"2019-01-02","native_i":np.arange(0,30,5),
                        "sigma":.002,"forecast_z":[.3,-.9,.8,.3,-.8,.6]})
    slow=frame.iloc[:4].copy()
    return {5:frame,15:slow},one


def test_episode_ignores_intermediate_resizing():
    frames,one=trading_fixture()
    ledger=c.episode_ledger(frames,one,"ADAPTIVE_COST",.003)
    assert ledger.horizon.tolist()==[15,15]
    assert ledger.position.tolist()==[.3,.3]
    assert ledger.turnover.tolist()==[.6,.6]
    np.testing.assert_allclose(ledger.gross_return, .3*(100.1/100.-1))


def test_missing_future_execution_is_failure_not_hindsight_trade_deletion():
    frames,one=trading_fixture()
    with pytest.raises(ValueError,match="missing actual execution"):
        c.episode_ledger(frames,one.drop(index=3),"ADAPTIVE_COST",.003)


def test_idle_days_retained_and_round_trip_cost_exact():
    frames,one=trading_fixture()
    ledger=c.episode_ledger(frames,one,"ADAPTIVE_COST",.003)
    m,ds,ms=runner.metrics(ledger,["2019-01-02","2019-01-03","2020-01-02"],2.)
    assert len(ds)==3 and ds.loc["2020-01-02"]==0
    assert m["explicit_cost_sum_return_units"]==pytest.approx(1.2*2/10000.)
    assert m["average_daily_turnover"]==pytest.approx(.4)


def test_option_cost_card_is_measurement_only_and_no_cross_underlying():
    now=pd.Timestamp("2023-06-01 10:00",tz="Asia/Shanghai")
    common={"underlying":"000852.SH","delta_forward":.5,"exposure_side":"buyer","structure":"long_single",
            "available_at":str(now-pd.Timedelta(seconds=10)),"expires_at":str(now+pd.Timedelta(days=10)),
            "source_semantics":"point_in_time_quote_measurement","cost_status":"ok_identified_only",
            "risk_mandate_id":"synthetic-mandate","eligible_under_mandate":True,
            "bid":100.,"ask":101.,"forward":5000.,"contract_multiplier":100.,
            "fee_open":14.,"fee_close":14.,"gamma":.001,"vega":20.,"theta":-.1}
    rows=[{**common,"contract_id":"A","identified_round_trip_hurdle_bp":5.12},
          {**common,"contract_id":"B","ask":102.,"identified_round_trip_hurdle_bp":9.12},
          {**common,"contract_id":"foreign","underlying":"000300.SH","identified_round_trip_hurdle_bp":.01},
          {**common,"contract_id":"stale","available_at":str(now-pd.Timedelta(seconds=121)),"identified_round_trip_hurdle_bp":5.12},
          {**common,"contract_id":"unknown_delta","delta_forward":.001,"identified_round_trip_hurdle_bp":.01}]
    ranked=c.rank_identified_option_cards(rows,underlying="000852.SH",direction=1,now=now,risk_mandate_id="synthetic-mandate")
    assert [r["contract_id"] for r in ranked]==["A","B"]
    assert ranked[0]["complete_all_in_cost_ready"] is False
    assert ranked[0]["routing_authority"] is False


def test_no_average_hurdle_or_fake_low_cost_card():
    now=pd.Timestamp("2023-06-01 10:00",tz="Asia/Shanghai")
    bad={"source_semantics":"sample_average_cost", "identified_round_trip_hurdle_bp":0.}
    assert c.rank_identified_option_cards([bad],underlying="000852.SH",direction=1,now=now,risk_mandate_id="test")==[]


def test_option_card_rejects_forged_cost_and_missing_greeks():
    now=pd.Timestamp("2023-06-01 10:00",tz="Asia/Shanghai")
    base={"contract_id":"fake", "underlying":"000852.SH", "delta_forward":.5,"exposure_side":"buyer","structure":"long_single", "available_at":str(now),"expires_at":str(now+pd.Timedelta(days=10)),"source_semantics":"point_in_time_quote_measurement","cost_status":"ok_identified_only","risk_mandate_id":"test","eligible_under_mandate":True,"bid":100.,"ask":101.,"forward":5000.,"contract_multiplier":100.,"fee_open":14.,"fee_close":14.,"gamma":.001,"vega":20.,"theta":-.1,"identified_round_trip_hurdle_bp":.01}
    assert c.rank_identified_option_cards([base],underlying="000852.SH",direction=1,now=now,risk_mandate_id="test")==[]
    base["identified_round_trip_hurdle_bp"]=5.12; base["gamma"]=float("nan")
    assert c.rank_identified_option_cards([base],underlying="000852.SH",direction=1,now=now,risk_mandate_id="test")==[]
