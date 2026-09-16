#!/usr/bin/env python3
"""Frozen R7 complete index-proxy trading-strategy baseline.

This runner is intentionally narrow. It preserves the parent R7 feature identity,
compares the historical fixed-TRAIN coefficients with a daily causal expanding-OLS
OLD_BASELINE, and evaluates 2019-2020 under a predeclared execution/cost contract.
It does not read BLACKBOX/post-2020 data and does not authorize production use.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from run_R7_native_1m_rejected_excursion import (
    FIVE_MIN_PATH,
    FIVE_MIN_ROWS,
    FIVE_MIN_SHA,
    MAX_DAY,
    ONE_MIN_PATH,
    ONE_MIN_ROWS,
    ONE_MIN_SHA,
    SYMBOL,
    build_candidates,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[1]
COST_SCENARIOS_BPS = (0.0, 1.0, 2.0, 5.0)
PRIMARY_COST_BPS = 2.0
EVAL_START = "2019-01-01"
EVAL_END = "2020-12-31"
SQRT252 = math.sqrt(252.0)


def _fit_b1(frame: pd.DataFrame) -> np.ndarray:
    X = np.column_stack(
        [
            np.ones(len(frame), dtype=float),
            frame["endpoint_z"].to_numpy(dtype=float),
            frame["rejection_signed_z"].to_numpy(dtype=float),
        ]
    )
    y = frame["next5_z"].to_numpy(dtype=float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta.astype(float)


def forecast_b1(frame: pd.DataFrame, beta: np.ndarray) -> np.ndarray:
    X = np.column_stack(
        [
            np.ones(len(frame), dtype=float),
            frame["endpoint_z"].to_numpy(dtype=float),
            frame["rejection_signed_z"].to_numpy(dtype=float),
        ]
    )
    return X @ np.asarray(beta, dtype=float)


def position_from_forecast(forecast_z: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(forecast_z, dtype=float), -1.0, 1.0)


def causal_expanding_forecasts(candidates: pd.DataFrame) -> tuple[pd.Series, dict[str, Any]]:
    """Fit once per evaluation day using only rows from strictly earlier days."""
    x = candidates.copy()
    x["trading_day"] = x["trading_day"].astype(str)
    eval_frame = x.loc[(x["trading_day"] >= EVAL_START) & (x["trading_day"] <= EVAL_END)].copy()
    output = pd.Series(index=eval_frame.index, dtype=float)
    beta_rows: list[dict[str, Any]] = []
    causality_ok = True

    for day, day_frame in eval_frame.groupby("trading_day", sort=True):
        history = x.loc[x["trading_day"] < str(day)]
        if history.empty:
            raise RuntimeError(f"no prior history for evaluation day {day}")
        max_history_day = str(history["trading_day"].max())
        if not max_history_day < str(day):
            causality_ok = False
        beta = _fit_b1(history)
        output.loc[day_frame.index] = forecast_b1(day_frame, beta)
        beta_rows.append(
            {
                "trading_day": str(day),
                "history_n": int(len(history)),
                "history_max_day": max_history_day,
                "beta": [float(v) for v in beta],
            }
        )

    if output.isna().any():
        raise RuntimeError("missing expanding forecast")
    audit = {
        "causality_ok": bool(causality_ok),
        "evaluation_days": int(len(beta_rows)),
        "first_day": beta_rows[0] if beta_rows else None,
        "last_day": beta_rows[-1] if beta_rows else None,
        "all_history_max_day_strictly_before_eval_day": bool(
            all(r["history_max_day"] < r["trading_day"] for r in beta_rows)
        ),
    }
    return output, audit


def _load_execution_source(path: Path = ONE_MIN_PATH) -> pd.DataFrame:
    if sha256_file(path) != ONE_MIN_SHA:
        raise RuntimeError("1m source SHA mismatch")
    one = pd.read_parquet(
        path,
        columns=[
            "symbol",
            "trading_day",
            "bar_end_shanghai",
            "open",
            "close",
            "causal_flat_fill",
            "instrument_type",
            "signal_price_view",
            "fill_price_view",
            "data_contract",
            "package_data_role",
        ],
    )
    if len(one) != ONE_MIN_ROWS:
        raise RuntimeError("1m source row mismatch")
    if set(one["symbol"].astype(str)) != {SYMBOL}:
        raise RuntimeError("1m source symbol mismatch")
    one = one.copy()
    one["trading_day"] = one["trading_day"].astype(str)
    if one["trading_day"].max() > MAX_DAY:
        raise RuntimeError("post-2020 data present")
    expected_meta = {
        "instrument_type": "market_index",
        "signal_price_view": "identity_index_point",
        "fill_price_view": "raw_pit",
        "data_contract": "cn_a_session_wall_clock_offset_v1",
        "package_data_role": "development_material",
    }
    for col, expected in expected_meta.items():
        vals = set(one[col].dropna().astype(str))
        if vals != {expected}:
            raise RuntimeError(f"unexpected {col}: {vals}")
    one["ts_utc"] = pd.to_datetime(one["bar_end_shanghai"], utc=True, errors="raise")
    one["open"] = pd.to_numeric(one["open"], errors="raise").astype(float)
    one["close"] = pd.to_numeric(one["close"], errors="raise").astype(float)
    if not np.isfinite(one[["open", "close"]].to_numpy(dtype=float)).all():
        raise RuntimeError("non-finite execution price")
    if bool((one[["open", "close"]] <= 0.0).any().any()):
        raise RuntimeError("non-positive execution price")
    one["causal_flat_fill"] = one["causal_flat_fill"].fillna(False).astype(bool)
    one = one.sort_values("ts_utc", kind="stable").reset_index(drop=True)
    if one["ts_utc"].duplicated().any():
        raise RuntimeError("duplicate native timestamp")
    return one


def attach_execution_prices(candidates: pd.DataFrame, one: pd.DataFrame) -> pd.DataFrame:
    """Attach delayed t+1 open and t+5 close to frozen R7 candidates."""
    x = candidates.copy()
    x["signal_ts_utc"] = pd.to_datetime(x["bar_end_shanghai"], utc=True, errors="raise")
    index_by_ns = {int(ts.value): i for i, ts in enumerate(one["ts_utc"].tolist())}
    rows: list[dict[str, Any]] = []

    for idx, row in x.iterrows():
        key = int(row["signal_ts_utc"].value)
        if key not in index_by_ns:
            raise RuntimeError("candidate endpoint absent from native source")
        i = index_by_ns[key]
        if i + 5 >= len(one):
            raise RuntimeError("candidate has no t+5 execution endpoint")
        future = one.iloc[i + 1 : i + 6]
        day = str(row["trading_day"])
        if len(future) != 5 or set(future["trading_day"].astype(str)) != {day}:
            raise RuntimeError("execution escaped same trading day")
        expected_ts = [one.loc[i, "ts_utc"] + pd.Timedelta(minutes=k) for k in range(1, 6)]
        if list(future["ts_utc"]) != expected_ts:
            raise RuntimeError("execution future bars are not exact native minutes")
        entry_open = float(future.iloc[0]["open"])
        exit_close = float(future.iloc[-1]["close"])
        rows.append(
            {
                "candidate_index": int(idx),
                "entry_ts_utc": future.iloc[0]["ts_utc"],
                "entry_open": entry_open,
                "window_exit_ts_utc": future.iloc[-1]["ts_utc"],
                "window_exit_close": exit_close,
                "window_underlying_return": float(exit_close / entry_open - 1.0),
                "execution_flat_fill_touch": bool(future["causal_flat_fill"].any()),
            }
        )

    z = pd.DataFrame(rows).set_index("candidate_index")
    out = x.join(z, how="left")
    if out[["entry_open", "window_exit_close", "window_underlying_return"]].isna().any().any():
        raise RuntimeError("execution join missing values")
    if not bool((out["entry_ts_utc"] > out["signal_ts_utc"]).all()):
        raise RuntimeError("execution is not delayed beyond signal")
    return out


def build_strategy_legs(frame: pd.DataFrame, position: np.ndarray) -> pd.DataFrame:
    """Create continuous-block carry, turnover, and gross returns."""
    x = frame.copy().sort_values("signal_ts_utc", kind="stable").reset_index(drop=True)
    p = np.asarray(position, dtype=float)
    if len(p) != len(frame):
        raise ValueError("position length mismatch")
    # frame sorting can change order, so caller must provide position as a column when needed.
    if "_position_input" in x.columns:
        p = x["_position_input"].to_numpy(dtype=float)
    if np.any(np.abs(p) > 1.0 + 1e-12):
        raise RuntimeError("position cap breached")

    n = len(x)
    gap_carry = np.zeros(n, dtype=float)
    turnover = np.zeros(n, dtype=float)
    contiguous_from_prev = np.zeros(n, dtype=bool)

    for i in range(n):
        if i == 0:
            turnover[i] += abs(p[i])
            continue
        same_day = str(x.loc[i, "trading_day"]) == str(x.loc[i - 1, "trading_day"])
        dt = x.loc[i, "signal_ts_utc"] - x.loc[i - 1, "signal_ts_utc"]
        contiguous = bool(same_day and dt == pd.Timedelta(minutes=5))
        contiguous_from_prev[i] = contiguous
        if contiguous:
            gap_carry[i] = float(
                p[i - 1] * (float(x.loc[i, "entry_open"]) / float(x.loc[i - 1, "window_exit_close"]) - 1.0)
            )
            turnover[i] += abs(p[i] - p[i - 1])
        else:
            turnover[i - 1] += abs(p[i - 1])
            turnover[i] += abs(p[i])

    if n:
        turnover[-1] += abs(p[-1])

    window_return = p * x["window_underlying_return"].to_numpy(dtype=float)
    gross_return = (1.0 + gap_carry) * (1.0 + window_return) - 1.0
    x["position"] = p
    x["contiguous_from_prev"] = contiguous_from_prev
    x["gap_carry_return"] = gap_carry
    x["window_position_return"] = window_return
    x["gross_return"] = gross_return
    x["turnover"] = turnover
    return x


def _compound(values: np.ndarray | pd.Series) -> float:
    a = np.asarray(values, dtype=float)
    if len(a) == 0:
        return float("nan")
    return float(np.prod(1.0 + a) - 1.0)


def _max_drawdown(returns: np.ndarray) -> float:
    if len(returns) == 0:
        return float("nan")
    equity = np.cumprod(1.0 + np.asarray(returns, dtype=float))
    peak = np.maximum.accumulate(np.r_[1.0, equity])[:-1]
    dd = equity / peak - 1.0
    return float(np.min(dd))


def performance_metrics(legs: pd.DataFrame, cost_bps: float) -> dict[str, Any]:
    x = legs.copy()
    cost_rate = float(cost_bps) / 10000.0
    x["explicit_cost"] = x["turnover"] * cost_rate
    x["net_return"] = x["gross_return"] - x["explicit_cost"]
    if bool((x["net_return"] <= -1.0).any()):
        raise RuntimeError("portfolio return below -100%")

    daily = x.groupby("trading_day", sort=True)["net_return"].apply(lambda s: _compound(s.to_numpy()))
    day_index = pd.to_datetime(daily.index)
    monthly = daily.groupby(day_index.to_period("M")).apply(lambda s: _compound(s.to_numpy()))
    total = _compound(x["net_return"].to_numpy())
    gross_total = _compound(x["gross_return"].to_numpy())
    n_days = int(len(daily))
    ann_return = float((1.0 + total) ** (252.0 / n_days) - 1.0) if n_days and total > -1.0 else float("nan")
    daily_arr = daily.to_numpy(dtype=float)
    vol_daily = float(np.std(daily_arr, ddof=1)) if len(daily_arr) > 1 else float("nan")
    ann_vol = float(vol_daily * SQRT252) if np.isfinite(vol_daily) else float("nan")
    mean_daily = float(np.mean(daily_arr)) if len(daily_arr) else float("nan")
    sharpe = float(mean_daily / vol_daily * SQRT252) if np.isfinite(vol_daily) and vol_daily > 0.0 else None
    downside = np.minimum(daily_arr, 0.0)
    downside_dev = float(np.sqrt(np.mean(downside**2))) if len(downside) else float("nan")
    sortino = float(mean_daily / downside_dev * SQRT252) if np.isfinite(downside_dev) and downside_dev > 0.0 else None
    mdd = _max_drawdown(x["net_return"].to_numpy(dtype=float))
    calmar = float(ann_return / abs(mdd)) if np.isfinite(mdd) and mdd < 0.0 else None

    by_year = {}
    for year in (2019, 2020):
        mask = x["trading_day"].astype(str).str.startswith(str(year))
        by_year[str(year)] = _compound(x.loc[mask, "net_return"].to_numpy(dtype=float))

    p = x["position"].to_numpy(dtype=float)
    daily_turnover = x.groupby("trading_day", sort=True)["turnover"].sum().to_numpy(dtype=float)
    return {
        "cost_bps": float(cost_bps),
        "trade_intervals": int(len(x)),
        "trading_days": n_days,
        "gross_total_return": gross_total,
        "total_return": total,
        "annualized_return": ann_return,
        "annualized_volatility": ann_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": mdd,
        "calmar": calmar,
        "positive_day_fraction": float(np.mean(daily_arr > 0.0)),
        "positive_month_fraction": float(np.mean(monthly.to_numpy(dtype=float) > 0.0)),
        "average_daily_turnover": float(np.mean(daily_turnover)),
        "annualized_turnover": float(np.mean(daily_turnover) * 252.0),
        "cumulative_explicit_cost": float(x["explicit_cost"].sum()),
        "gross_minus_net_total_return": float(gross_total - total),
        "average_abs_exposure": float(np.mean(np.abs(p))),
        "long_fraction": float(np.mean(p > 0.0)),
        "short_fraction": float(np.mean(p < 0.0)),
        "flat_fraction": float(np.mean(p == 0.0)),
        "year_total_return": by_year,
    }


def evaluate_policy(exec_eval: pd.DataFrame, forecast: np.ndarray, policy_name: str) -> dict[str, Any]:
    x = exec_eval.copy()
    x["forecast_z"] = np.asarray(forecast, dtype=float)
    x["_position_input"] = position_from_forecast(x["forecast_z"].to_numpy(dtype=float))
    legs = build_strategy_legs(x, x["_position_input"].to_numpy(dtype=float))
    panels = {f"{c:g}bps": performance_metrics(legs, c) for c in COST_SCENARIOS_BPS}
    return {
        "policy": policy_name,
        "forecast_summary": {
            "mean": float(x["forecast_z"].mean()),
            "std": float(x["forecast_z"].std(ddof=1)),
            "min": float(x["forecast_z"].min()),
            "max": float(x["forecast_z"].max()),
        },
        "cost_panel": panels,
    }


def run() -> dict[str, Any]:
    if sha256_file(FIVE_MIN_PATH) != FIVE_MIN_SHA:
        raise RuntimeError("5m source SHA mismatch")
    five_meta = pd.read_parquet(FIVE_MIN_PATH, columns=["symbol", "trading_day"])
    if len(five_meta) != FIVE_MIN_ROWS or set(five_meta["symbol"].astype(str)) != {SYMBOL}:
        raise RuntimeError("5m source identity mismatch")
    if str(five_meta["trading_day"].astype(str).max()) > MAX_DAY:
        raise RuntimeError("5m source escaped admitted range")

    candidates = build_candidates()
    candidates = candidates.copy()
    candidates["trading_day"] = candidates["trading_day"].astype(str)
    train = candidates.loc[candidates["role"] == "TRAIN"].copy()
    eval_candidates = candidates.loc[
        (candidates["trading_day"] >= EVAL_START) & (candidates["trading_day"] <= EVAL_END)
    ].copy()
    if len(train) != 42787 or len(eval_candidates) != 21428:
        raise RuntimeError(f"parent candidate reproduction drift: {len(train)}, {len(eval_candidates)}")

    legacy_beta = _fit_b1(train)
    legacy_forecast = forecast_b1(eval_candidates, legacy_beta)
    expanding_forecast_series, expanding_audit = causal_expanding_forecasts(candidates)
    expanding_forecast = expanding_forecast_series.loc[eval_candidates.index].to_numpy(dtype=float)

    one = _load_execution_source()
    exec_eval = attach_execution_prices(eval_candidates, one)
    exec_eval = exec_eval.sort_values("signal_ts_utc", kind="stable")

    # Align forecasts after timestamp sort using original candidate index.
    legacy_s = pd.Series(legacy_forecast, index=eval_candidates.index)
    expanding_s = pd.Series(expanding_forecast, index=eval_candidates.index)
    legacy_sorted = legacy_s.loc[exec_eval.index].to_numpy(dtype=float)
    expanding_sorted = expanding_s.loc[exec_eval.index].to_numpy(dtype=float)

    legacy = evaluate_policy(exec_eval, legacy_sorted, "legacy_static_2015_2018_B1")
    baseline = evaluate_policy(exec_eval, expanding_sorted, "OLD_BASELINE_daily_causal_expanding_B1")
    primary = baseline["cost_panel"]["2bps"]
    gates = {
        "net_total_return_gt_0": bool(primary["total_return"] > 0.0),
        "net_sharpe_gt_0": bool(primary["sharpe"] is not None and primary["sharpe"] > 0.0),
        "2019_net_total_return_gt_0": bool(primary["year_total_return"]["2019"] > 0.0),
        "2020_net_total_return_gt_0": bool(primary["year_total_return"]["2020"] > 0.0),
        "causal_expanding_fit": bool(expanding_audit["all_history_max_day_strictly_before_eval_day"]),
        "delayed_execution": bool((exec_eval["entry_ts_utc"] > exec_eval["signal_ts_utc"]).all()),
        "no_execution_day_escape": bool(
            (exec_eval["trading_day"].astype(str) == exec_eval["entry_ts_utc"].dt.tz_convert("Asia/Shanghai").dt.strftime("%Y-%m-%d")).all()
            and (exec_eval["trading_day"].astype(str) == exec_eval["window_exit_ts_utc"].dt.tz_convert("Asia/Shanghai").dt.strftime("%Y-%m-%d")).all()
        ),
    }
    supported = bool(all(gates.values()))
    adjudication = (
        "R7_OLD_BASELINE_ECONOMICALLY_SUPPORTED_AT_2BPS_RESEARCH_STRESS"
        if supported
        else "R7_OLD_BASELINE_EVALUATED_NOT_SUPPORTED_AT_2BPS_NO_RESCUE"
    )

    return {
        "schema_id": "factorlab_R7_trading_strategy_baseline_receipt@1.0",
        "identity": "R7_trading_strategy_baseline_v1",
        "parent_identity": "R7_native_1m_rejected_excursion_v1",
        "strategy_role": "index_proxy_research_backtest",
        "sources": {
            "one_min": {"path": str(ONE_MIN_PATH.relative_to(ROOT)), "sha256": ONE_MIN_SHA, "rows": ONE_MIN_ROWS},
            "five_min": {"path": str(FIVE_MIN_PATH.relative_to(ROOT)), "sha256": FIVE_MIN_SHA, "rows": FIVE_MIN_ROWS},
            "symbol": SYMBOL,
            "max_day": MAX_DAY,
            "instrument_type": "market_index",
            "signal_price_view": "identity_index_point",
            "fill_price_view": "raw_pit",
            "data_contract": "cn_a_session_wall_clock_offset_v1",
            "package_data_role": "development_material",
        },
        "parent_reproduction": {
            "candidate_rows": int(len(candidates)),
            "TRAIN_rows": int(len(train)),
            "VALIDATION_rows": int(len(eval_candidates)),
            "legacy_TRAIN_B1_beta": [float(v) for v in legacy_beta],
        },
        "execution": {
            "signal_to_entry": "next_native_1m_open",
            "window_exit": "t_plus_5_native_1m_close",
            "contiguous_gap_carry": True,
            "noncontiguous_flatten": True,
            "overnight_exposure": False,
            "trade_intervals": int(len(exec_eval)),
            "flat_fill_touch_intervals": int(exec_eval["execution_flat_fill_touch"].sum()),
            "flat_fill_touch_fraction": float(exec_eval["execution_flat_fill_touch"].mean()),
        },
        "coefficient_policies": {
            "legacy": "fixed_2015_2018_B1",
            "OLD_BASELINE": "daily_expanding_B1_using_strictly_prior_trading_days",
            "expanding_audit": expanding_audit,
        },
        "position_rule": "clip(forecast_z,-1,+1)",
        "cost_scenarios_bps": [float(v) for v in COST_SCENARIOS_BPS],
        "primary_cost_bps": PRIMARY_COST_BPS,
        "legacy_comparator": legacy,
        "OLD_BASELINE": baseline,
        "primary_acceptance_gates": gates,
        "adjudication": adjudication,
        "BLACKBOX_read": False,
        "post_2020_rows_read": False,
        "fresh_OOS_claim": False,
        "actual_IM_execution_cost_claim": False,
        "paper_trading_authority": False,
        "production_authority": False,
        "registry_mutation": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "identity": result["identity"],
        "adjudication": result["adjudication"],
        "primary_2bps": result["OLD_BASELINE"]["cost_panel"]["2bps"],
        "gates": result["primary_acceptance_gates"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
