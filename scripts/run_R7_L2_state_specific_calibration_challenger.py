#!/usr/bin/env python3
"""Frozen R7 x Layer2 state-specific expanding-calibration trading challenger."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import run_R7_trading_strategy_baseline as base
import diagnose_R7_L2_5m_risk_bucket_calibration as l2

COSTS = (0.0, 1.0, 2.0, 5.0)
PRIMARY = 2.0
ATOL = 1e-12
EXPECTED_OLD = {
    "total_return": -0.026713436670182222,
    "sharpe": -0.2670672170031825,
    "2019": -0.03560696616960668,
    "2020": 0.00922189313634858,
    "average_daily_turnover": 9.691847216614384,
    "max_drawdown": -0.13270195650953243,
}
BUCKETS = ("LOW_RISK", "RISK_ACTIVE")


def _design_rank(frame: pd.DataFrame) -> int:
    X = np.column_stack([
        np.ones(len(frame), dtype=float),
        frame["endpoint_z"].to_numpy(dtype=float),
        frame["rejection_signed_z"].to_numpy(dtype=float),
    ])
    return int(np.linalg.matrix_rank(X))


def causal_state_specific_forecasts(attached: pd.DataFrame) -> tuple[pd.Series, dict[str, Any]]:
    """Fit each frozen risk bucket once per evaluation day on strictly prior rows only."""
    x = attached.copy()
    x["trading_day"] = x["trading_day"].astype(str)
    if "candidate_id" not in x.columns:
        raise RuntimeError("candidate_id missing")
    eval_frame = x.loc[(x["trading_day"] >= base.EVAL_START) & (x["trading_day"] <= base.EVAL_END)].copy()
    if eval_frame["risk_bucket"].isna().any():
        raise RuntimeError("Layer2 state missing on evaluation row")
    output = pd.Series(index=eval_frame["candidate_id"].astype(int).to_numpy(), dtype=float)
    records: list[dict[str, Any]] = []

    for day, day_frame in eval_frame.groupby("trading_day", sort=True):
        for bucket in BUCKETS:
            current = day_frame.loc[day_frame["risk_bucket"].eq(bucket)]
            if current.empty:
                continue
            hist = x.loc[(x["trading_day"] < str(day)) & x["risk_bucket"].eq(bucket)].copy()
            if len(hist) < 3 or _design_rank(hist) != 3:
                raise RuntimeError(f"insufficient/full-rank history for {day} {bucket}")
            history_max_day = str(hist["trading_day"].max())
            if not history_max_day < str(day):
                raise RuntimeError("causality violation")
            beta = base._fit_b1(hist)
            pred = base.forecast_b1(current, beta)
            output.loc[current["candidate_id"].astype(int).to_numpy()] = pred
            records.append({
                "trading_day": str(day),
                "bucket": bucket,
                "history_n": int(len(hist)),
                "history_max_day": history_max_day,
                "history_rank": 3,
                "beta": [float(v) for v in beta],
                "current_n": int(len(current)),
            })

    if output.isna().any():
        raise RuntimeError("missing state-specific expanding forecast")
    by_bucket: dict[str, Any] = {}
    for bucket in BUCKETS:
        z = [r for r in records if r["bucket"] == bucket]
        by_bucket[bucket] = {
            "updates": int(len(z)),
            "first": z[0] if z else None,
            "last": z[-1] if z else None,
        }
    audit = {
        "evaluation_rows": int(len(eval_frame)),
        "evaluation_days": int(eval_frame["trading_day"].nunique()),
        "all_history_strictly_prior": bool(all(r["history_max_day"] < r["trading_day"] for r in records)),
        "all_history_full_rank": bool(all(r["history_rank"] == 3 for r in records)),
        "bucket_updates": by_bucket,
    }
    return output.sort_index(), audit


def _evaluate(exec_eval: pd.DataFrame, position: np.ndarray) -> dict[str, Any]:
    x = exec_eval.copy()
    x["_position_input"] = np.asarray(position, dtype=float)
    legs = base.build_strategy_legs(x, np.asarray(position, dtype=float))
    return {
        "cost_panel": {f"{int(c)}bps": base.performance_metrics(legs, c) for c in COSTS},
        "trade_intervals": int(len(legs)),
    }


def _mse(y: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean((np.asarray(y, dtype=float) - np.asarray(pred, dtype=float)) ** 2))


def _reproduce_old(m: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "total_return": math.isclose(m["total_return"], EXPECTED_OLD["total_return"], rel_tol=0.0, abs_tol=ATOL),
        "sharpe": math.isclose(m["sharpe"], EXPECTED_OLD["sharpe"], rel_tol=0.0, abs_tol=ATOL),
        "2019": math.isclose(m["year_total_return"]["2019"], EXPECTED_OLD["2019"], rel_tol=0.0, abs_tol=ATOL),
        "2020": math.isclose(m["year_total_return"]["2020"], EXPECTED_OLD["2020"], rel_tol=0.0, abs_tol=ATOL),
        "average_daily_turnover": math.isclose(m["average_daily_turnover"], EXPECTED_OLD["average_daily_turnover"], rel_tol=0.0, abs_tol=ATOL),
        "max_drawdown": math.isclose(m["max_drawdown"], EXPECTED_OLD["max_drawdown"], rel_tol=0.0, abs_tol=ATOL),
    }
    return {"pass": bool(all(checks.values())), "checks": checks, "actual": {
        "total_return": m["total_return"], "sharpe": m["sharpe"],
        "2019": m["year_total_return"]["2019"], "2020": m["year_total_return"]["2020"],
        "average_daily_turnover": m["average_daily_turnover"], "max_drawdown": m["max_drawdown"],
    }}


def run() -> dict[str, Any]:
    candidates = base.build_candidates().copy()
    candidates["candidate_id"] = np.arange(len(candidates), dtype=int)
    candidates["trading_day"] = candidates["trading_day"].astype(str)

    attached, replay_meta = l2.attach_frozen_states(candidates)
    attached["trading_day"] = attached["trading_day"].astype(str)
    eval_state = attached.loc[(attached["trading_day"] >= base.EVAL_START) & (attached["trading_day"] <= base.EVAL_END)].copy()
    if len(eval_state) != 21428:
        raise RuntimeError(f"unexpected evaluation rows {len(eval_state)}")
    if eval_state["risk_bucket"].isna().any():
        raise RuntimeError("state mapping incomplete on evaluation")
    counts = eval_state["risk_bucket"].value_counts().to_dict()

    global_forecast, global_audit = base.causal_expanding_forecasts(candidates)
    state_forecast, state_audit = causal_state_specific_forecasts(attached)
    ids = eval_state["candidate_id"].astype(int).to_numpy()
    old_pred = global_forecast.reindex(ids).to_numpy(dtype=float)
    new_pred = state_forecast.reindex(ids).to_numpy(dtype=float)
    if not np.isfinite(old_pred).all() or not np.isfinite(new_pred).all():
        raise RuntimeError("non-finite forecast")

    old_pos = base.position_from_forecast(old_pred)
    new_pos = base.position_from_forecast(new_pred)

    one = base._load_execution_source()
    exec_eval = base.attach_execution_prices(eval_state, one)
    old_result = _evaluate(exec_eval, old_pos)
    challenger_result = _evaluate(exec_eval, new_pos)
    old2 = old_result["cost_panel"]["2bps"]
    new2 = challenger_result["cost_panel"]["2bps"]
    reproduction = _reproduce_old(old2)

    y = eval_state["next5_z"].to_numpy(dtype=float)
    years = eval_state["trading_day"].str[:4]
    predictive = {
        "VALIDATION": {"OLD_BASELINE_MSE": _mse(y, old_pred), "CHALLENGER_MSE": _mse(y, new_pred)},
    }
    for year in ("2019", "2020"):
        mask = years.eq(year).to_numpy()
        predictive[year] = {"OLD_BASELINE_MSE": _mse(y[mask], old_pred[mask]), "CHALLENGER_MSE": _mse(y[mask], new_pred[mask])}

    structural_ok = bool(
        global_audit["all_history_max_day_strictly_before_eval_day"]
        and state_audit["all_history_strictly_prior"]
        and state_audit["all_history_full_rank"]
        and not eval_state["risk_bucket"].isna().any()
    )
    gates = {
        "old_baseline_reproduction": bool(reproduction["pass"]),
        "state_complete_and_causal_full_rank": structural_ok,
        "challenger_total_return_gt_0": bool(new2["total_return"] > 0.0),
        "challenger_sharpe_gt_0": bool(new2["sharpe"] is not None and new2["sharpe"] > 0.0),
        "challenger_2019_return_gt_0": bool(new2["year_total_return"]["2019"] > 0.0),
        "challenger_2020_return_gt_0": bool(new2["year_total_return"]["2020"] > 0.0),
        "challenger_total_return_gt_old_baseline": bool(new2["total_return"] > old2["total_return"]),
        "challenger_sharpe_gt_old_baseline": bool(new2["sharpe"] is not None and old2["sharpe"] is not None and new2["sharpe"] > old2["sharpe"]),
        "challenger_average_daily_turnover_lt_old_baseline": bool(new2["average_daily_turnover"] < old2["average_daily_turnover"]),
        "challenger_max_drawdown_ge_old_baseline": bool(new2["max_drawdown"] >= old2["max_drawdown"]),
    }
    if not reproduction["pass"] or not structural_ok:
        adjudication = "R7_L2_CHALLENGER_EXECUTION_DRIFT_OR_INSUFFICIENT"
    elif all(gates.values()):
        adjudication = "R7_L2_CHALLENGER_PROMOTED_NEW_RESEARCH_BASELINE"
    else:
        adjudication = "R7_L2_CHALLENGER_EVALUATED_NOT_PROMOTED_NO_RESCUE"

    return {
        "schema_id": "factorlab_R7_L2_state_specific_calibration_challenger_receipt@1.0",
        "identity": "R7_L2_state_specific_calibration_challenger_v1",
        "parent_strategy": "R7_trading_strategy_baseline_v1",
        "candidate_rows": int(len(candidates)),
        "evaluation_rows": int(len(eval_state)),
        "state_supply_evaluation": {k: int(v) for k, v in counts.items()},
        "state_replay_meta": replay_meta,
        "global_expanding_audit": global_audit,
        "state_specific_expanding_audit": state_audit,
        "predictive_diagnostic": predictive,
        "OLD_BASELINE_reproduction": reproduction,
        "OLD_BASELINE": old_result,
        "L2_CHALLENGER": challenger_result,
        "primary_2bps_gates": gates,
        "adjudication": adjudication,
        "BLACKBOX_read": False,
        "post_2020_rows_read": False,
        "fresh_OOS_claim": False,
        "actual_IM_execution_cost_claim": False,
        "paper_trading_authority": False,
        "production_authority": False,
        "registry_mutation": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(receipt["adjudication"])
    print(json.dumps(receipt["L2_CHALLENGER"]["cost_panel"]["2bps"], indent=2))


if __name__ == "__main__":
    main()
