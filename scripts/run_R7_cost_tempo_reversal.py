#!/usr/bin/env python3
"""Execute only the preregistered Stage-A INDEX proxy; never real option PnL."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
import run_R7_trading_strategy_baseline as old
import r7_cost_tempo_core as core

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("FAST_EPISODE", "FAST_COST", "SLOW_COST", "ADAPTIVE_COST")


def compound(a) -> float:
    return float(np.prod(1. + np.asarray(a, float))-1.)


def metrics(legs: pd.DataFrame, days: list[str], cost: float) -> tuple[dict, pd.Series, pd.Series]:
    net = legs.gross_return.to_numpy(float)-legs.turnover.to_numpy(float)*cost/10000.
    if not np.isfinite(net).all() or (net <= -1).any():
        raise ValueError("invalid portfolio returns")
    x = legs.assign(net_return=net)
    daily = x.groupby("trading_day").net_return.apply(compound).reindex(days, fill_value=0.).astype(float)
    monthly = daily.groupby(pd.to_datetime(daily.index).to_period("M")).apply(compound)
    n = len(days)
    total = compound(net)
    ann = (1.+total)**(252./n)-1.
    vol = float(daily.std(ddof=1)*math.sqrt(252))
    mu = float(daily.mean()*252)
    downside = float(np.sqrt(np.mean(np.minimum(daily.to_numpy(),0)**2))*math.sqrt(252))
    eq = np.r_[1., np.cumprod(1.+net)]
    dd = float(np.min(eq/np.maximum.accumulate(eq)-1.))
    turn = float(legs.turnover.sum())
    time_exposure = float((legs.position.abs()*legs.horizon).sum()/(n*240.))
    m = {"cost_bps": cost, "total_return": total, "annualized_return": ann,
         "annualized_volatility": vol, "sharpe": mu/vol if vol>0 else None,
         "sortino": mu/downside if downside>0 else None,
         "max_drawdown_episode_marks": dd, "calmar": ann/abs(dd) if dd<0 else None,
         "positive_day_fraction": float((daily>0).mean()), "positive_month_fraction": float((monthly>0).mean()),
         "trading_calendar_days": n, "active_days": int(legs.trading_day.nunique()),
         "trade_episodes": len(legs), "average_daily_turnover": turn/n,
         "annualized_turnover": turn/n*252., "time_weighted_abs_exposure": time_exposure,
         "signal_average_abs_exposure": float(legs.position.abs().mean()) if len(legs) else 0.,
         "long_episode_fraction": float((legs.position>0).mean()) if len(legs) else 0.,
         "short_episode_fraction": float((legs.position<0).mean()) if len(legs) else 0.,
         "mean_holding_minutes": float(legs.horizon.mean()) if len(legs) else 0.,
         "gross_bp_per_unit_turnover": float(legs.gross_return.sum()/turn*10000.) if turn else None,
         "net_bp_per_unit_turnover": float(np.sum(net)/turn*10000.) if turn else None,
         "explicit_cost_sum_return_units": turn*cost/10000.,
         "flat_fill_touch_episodes": int(legs.flat_fill_touch.sum()),
         "year_total_return": {y: compound(daily.loc[daily.index.str.startswith(y)]) for y in ("2019","2020")}}
    return m, daily, monthly


def break_even(legs: pd.DataFrame) -> float | None:
    if legs.empty:
        return None
    gross = legs.gross_return.to_numpy(float)
    turn = legs.turnover.to_numpy(float)
    def terminal(c):
        return compound(gross-turn*c/10000.)
    if terminal(0.) <= 0:
        return 0.
    if terminal(100.) >= 0:
        return None
    lo, hi = 0., 100.
    for _ in range(64):
        mid = (lo+hi)/2.
        if terminal(mid)>0: lo=mid
        else: hi=mid
    return (lo+hi)/2.


def run(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=False)
    one = old._load_execution_source()
    five = pd.read_parquet(old.FIVE_MIN_PATH, columns=["bar_end_shanghai","close"])
    if old.sha256_file(old.FIVE_MIN_PATH) != old.FIVE_MIN_SHA or len(five) != old.FIVE_MIN_ROWS:
        raise ValueError("5m identity mismatch")
    days = sorted(one.loc[one.trading_day.between("2019-01-01","2020-12-31"),"trading_day"].unique().tolist())
    candidates = old.build_candidates()
    if len(candidates) != 64215:
        raise ValueError("parent candidate drift")
    pred, old_audit = old.causal_expanding_forecasts(candidates)
    old_eval = candidates.loc[pred.index].copy()
    execution = old.attach_execution_prices(old_eval, one)
    execution["_position_input"] = old.position_from_forecast(pred.loc[execution.index].to_numpy())
    old_legs = old.build_strategy_legs(execution, execution._position_input.to_numpy())
    baseline = {f"{c:g}bps": old.performance_metrics(old_legs,c) for c in core.COSTS}
    ref = baseline["2bps"]
    expected = {"total_return": -.026713436670182222, "sharpe": -.2670672170031825,
                "max_drawdown": -.13270195650953243, "average_daily_turnover": 9.691847216614384}
    reproduction = {k: math.isclose(ref[k],v,abs_tol=1e-9,rel_tol=0.) for k,v in expected.items()}
    if not all(reproduction.values()):
        raise ValueError(f"OLD_BASELINE drift: {reproduction}")
    frames = {h: core.native_scale_frame(one,five,h) for h in core.HORIZONS}
    train = frames[5].loc[frames[5].trading_day <= "2018-12-31"]
    cutoff = float(train.sigma.median())
    forecasts, audits = {}, {}
    for h,f in frames.items():
        forecasts[h], audit = core.daily_forecasts(f)
        audits[str(h)] = {"feature_rows": len(f), "missing_labels": int(f.target_z.isna().sum()),
                          "all_history_prior": all(a["history_max_day"]<a["day"] for a in audit),
                          "first": audit[0], "last": audit[-1], "fit_days":len(audit)}
        pd.DataFrame(audit).to_json(output_dir/f"coefficients_H{h}.json",orient="records",indent=2)
    results = {}
    all_daily, all_monthly = [], []
    for c in core.COSTS:
        v = old_legs.gross_return-old_legs.turnover*c/10000.
        ds = v.groupby(old_legs.trading_day).apply(compound).reindex(days,fill_value=0.)
        all_daily.append(pd.DataFrame({"day":ds.index,"arm":"OLD_BASELINE","cost_bps":c,"return":ds.values}))
    for arm in ARMS:
        ledger = core.episode_ledger(forecasts,one,arm,cutoff)
        ledger.to_csv(output_dir/f"{arm}_trades.csv",index=False)
        panel = {}
        for c in core.COSTS:
            m,ds,ms = metrics(ledger,days,c)
            panel[f"{c:g}bps"] = m
            all_daily.append(pd.DataFrame({"day":ds.index,"arm":arm,"cost_bps":c,"return":ds.values}))
            all_monthly.append(pd.DataFrame({"month":ms.index.astype(str),"arm":arm,"cost_bps":c,"return":ms.values}))
        results[arm] = {"cost_panel":panel,"break_even_one_way_bps":break_even(ledger),
                        "horizon_counts":{str(k):int(v) for k,v in ledger.horizon.value_counts().items()},
                        "tempo_state_counts":ledger.tempo_state.value_counts().to_dict()}
    pd.concat(all_daily,ignore_index=True).to_csv(output_dir/"daily_returns.csv",index=False)
    pd.concat(all_monthly,ignore_index=True).to_csv(output_dir/"monthly_returns.csv",index=False)
    a = results["ADAPTIVE_COST"]["cost_panel"]["2bps"]
    positive = lambda x: x is not None and x>0
    gates = {"old_baseline_reproduced":all(reproduction.values()),
             "strict_prior_history":all(v["all_history_prior"] for v in audits.values()),
             "total_positive":a["total_return"]>0, "sharpe_positive":positive(a["sharpe"]),
             "2019_positive":a["year_total_return"]["2019"]>0,
             "2020_positive":a["year_total_return"]["2020"]>0,
             "total_above_old":a["total_return"]>ref["total_return"],
             "sharpe_above_old":a["sharpe"] is not None and a["sharpe"]>ref["sharpe"],
             "drawdown_no_worse_than_old":a["max_drawdown_episode_marks"]>=ref["max_drawdown"],
             "turnover_below_old":a["average_daily_turnover"]<ref["average_daily_turnover"]}
    tempo_gate = all(a["total_return"]>results[arm]["cost_panel"]["2bps"]["total_return"] for arm in ("FAST_COST","SLOW_COST"))
    result = {"identity":core.IDENTITY, "date":"2026-09-22", "execution_surface":"authorized_local_debian_isolated_worktree",
              "execution_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
              "stage":"A_index_proxy_engineering_diagnostic", "source_sha256":{"1m":old.ONE_MIN_SHA,"5m":old.FIVE_MIN_SHA},
              "data_max_day":"2020-12-31", "evaluation_days":len(days), "sigma_train_only_median":cutoff,
              "train_sigma_rows":len(train), "OLD_BASELINE_reproduction":reproduction,
              "OLD_BASELINE":baseline, "coefficient_audits":audits, "new_arms":results,
              "primary_2bps_gates":gates, "incremental_tempo_above_both_fixed_arms":tempo_gate,
              "adjudication":"STAGE_A_ENGINEERING_SUPPORTED" if all(gates.values()) else "STAGE_A_ENGINEERING_NOT_SUPPORTED",
              "causal_execution_qualification":False, "qualification_limit":"next_bar_open_is_boundary_price_proxy_not_positive_latency_execution_proof; drawdown_is_episode_marked_not_minute_marked",
              "stage_B_real_option_replay_executed":False,"real_option_selection_executed":False,
              "post_2020_outcomes_read":False,"BLACKBOX_read":False,"fresh_OOS":False,"production_authority":False}
    result["files"] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output_dir.iterdir()) if p.is_file()}
    (output_dir/"receipt.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"adjudication":result["adjudication"],"gates":gates,"tempo_gate":tempo_gate,
                      "primary":{arm:results[arm]["cost_panel"]["2bps"] for arm in ARMS}},ensure_ascii=False,indent=2))
    return result

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    run(args.output_dir)
