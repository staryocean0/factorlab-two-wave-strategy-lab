#!/usr/bin/env python3
"""Bounded post-R5 diagnostic for the small B1 anti-persistence increment.

This is reusable TRAIN/VALIDATION diagnosis, not fresh OOS and not BLACKBOX.
It must reproduce the frozen CL-007 B0/B1 result before producing diagnostics.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PARENT_SCRIPT = ROOT / "scripts" / "run_broad_rmr_R5_multiscale_serial_dependence.py"
SPEC = importlib.util.spec_from_file_location("r5_parent", PARENT_SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load R5 parent runner")
r5 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = r5
SPEC.loader.exec_module(r5)

EXPECTED = {
    "B0_beta": np.array([0.005567078395256155, 0.03487451881755519], dtype=float),
    "B1_beta": np.array([0.004947147092300985, 0.01303609638446463, -1.069228621037033], dtype=float),
    "B0_validation_mse": 1.011653266505294,
    "B1_validation_mse": 1.0101116108135515,
    "train_rows": 41685,
    "validation_rows": 21428,
}
REPRO_ATOL = 1e-12


def build_B_frames(data_path: Path = r5.DATA_PATH) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    native = r5.load_native(data_path)
    returns = r5.build_continuous_returns(native)
    normalized = r5.add_causal_normalization(returns)
    state = r5.add_memory_state(normalized)
    frame = state.copy()
    frame["next_z"] = frame["z"].shift(-1)
    same_next_segment = frame["segment_id"].eq(frame["segment_id"].shift(-1))
    valid = frame["state_available"] & frame["z"].notna() & frame["next_z"].notna() & same_next_segment
    frame = frame.loc[valid].copy()
    train = frame.loc[frame["role"] == "TRAIN"].copy()
    validation = frame.loc[frame["role"] == "VALIDATION"].copy()

    X0_train, y_train = r5._design_B(train, "B0")
    X1_train, _ = r5._design_B(train, "B1")
    beta0 = r5._fit_ols(X0_train, y_train)
    beta1 = r5._fit_ols(X1_train, y_train)
    return train, validation, beta0, beta1


def reproduce_entry_gate(train: pd.DataFrame, validation: pd.DataFrame, beta0: np.ndarray, beta1: np.ndarray) -> dict[str, Any]:
    X0_val, y_val = r5._design_B(validation, "B0")
    X1_val, _ = r5._design_B(validation, "B1")
    pred0 = r5._predict(X0_val, beta0)
    pred1 = r5._predict(X1_val, beta1)
    mse0 = float(np.mean((y_val - pred0) ** 2))
    mse1 = float(np.mean((y_val - pred1) ** 2))

    checks = {
        "TRAIN_rows": len(train) == EXPECTED["train_rows"],
        "VALIDATION_rows": len(validation) == EXPECTED["validation_rows"],
        "B0_beta": bool(np.allclose(beta0, EXPECTED["B0_beta"], rtol=0.0, atol=REPRO_ATOL)),
        "B1_beta": bool(np.allclose(beta1, EXPECTED["B1_beta"], rtol=0.0, atol=REPRO_ATOL)),
        "B0_validation_mse": math.isclose(mse0, EXPECTED["B0_validation_mse"], rel_tol=0.0, abs_tol=REPRO_ATOL),
        "B1_validation_mse": math.isclose(mse1, EXPECTED["B1_validation_mse"], rel_tol=0.0, abs_tol=REPRO_ATOL),
    }
    return {
        "checks": checks,
        "pass": bool(all(checks.values())),
        "actual": {
            "TRAIN_rows": int(len(train)),
            "VALIDATION_rows": int(len(validation)),
            "B0_beta": [float(x) for x in beta0],
            "B1_beta": [float(x) for x in beta1],
            "B0_validation_mse": mse0,
            "B1_validation_mse": mse1,
        },
    }


def _day_table(validation: pd.DataFrame, beta0: np.ndarray, beta1: np.ndarray) -> pd.DataFrame:
    X0, y = r5._design_B(validation, "B0")
    X1, _ = r5._design_B(validation, "B1")
    pred0 = r5._predict(X0, beta0)
    pred1 = r5._predict(X1, beta1)
    work = validation[["trading_day", "year"]].copy()
    work["err0"] = (y - pred0) ** 2
    work["err1"] = (y - pred1) ** 2
    day = (
        work.groupby(["trading_day", "year"], sort=True)
        .agg(n=("err0", "size"), mse0=("err0", "mean"), mse1=("err1", "mean"))
        .reset_index()
    )
    day["improvement"] = day["mse0"] - day["mse1"]
    return day


def _summarize_day_improvement(day: pd.DataFrame) -> dict[str, Any]:
    arr = day["improvement"].to_numpy(dtype=float)
    if len(arr) == 0:
        return {"days": 0, "mean": None, "median": None, "p10": None, "p90": None, "fraction_B1_better": None}
    return {
        "days": int(len(day)),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p10": float(np.quantile(arr, 0.10)),
        "p90": float(np.quantile(arr, 0.90)),
        "fraction_B1_better": float(np.mean(arr > 0.0)),
        "weighted_MSE_B0": float(np.average(day["mse0"].to_numpy(dtype=float), weights=day["n"].to_numpy(dtype=float))),
        "weighted_MSE_B1": float(np.average(day["mse1"].to_numpy(dtype=float), weights=day["n"].to_numpy(dtype=float))),
    }


def evaluate_D1(validation: pd.DataFrame, beta0: np.ndarray, beta1: np.ndarray) -> dict[str, Any]:
    day = _day_table(validation, beta0, beta1)
    pooled = _summarize_day_improvement(day)
    by_year = {str(year): _summarize_day_improvement(day.loc[day["year"] == year]) for year in (2019, 2020)}
    support = all(
        by_year[str(year)]["fraction_B1_better"] is not None
        and by_year[str(year)]["fraction_B1_better"] > 0.50
        and by_year[str(year)]["median"] is not None
        and by_year[str(year)]["median"] > 0.0
        for year in (2019, 2020)
    )
    return {"pooled": pooled, "by_year": by_year, "D1_day_breadth_supported": bool(support)}


def train_quintile_edges(train: pd.DataFrame) -> np.ndarray:
    values = train["anti_persistence"].to_numpy(dtype=float)
    if not np.isfinite(values).all() or len(values) < 100:
        raise RuntimeError("invalid TRAIN anti_persistence distribution")
    edges = np.quantile(values, [0.2, 0.4, 0.6, 0.8]).astype(float)
    if not np.all(np.diff(edges) > 0.0):
        raise RuntimeError("TRAIN anti_persistence quintile edges are not strictly increasing")
    return edges


def assign_quintiles(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    return np.searchsorted(np.asarray(edges, dtype=float), np.asarray(values, dtype=float), side="right").astype(int)


def _fit_bin(frame: pd.DataFrame) -> dict[str, Any]:
    if len(frame) < 20:
        return {"n": int(len(frame)), "mean_anti_persistence": None, "slope": None, "MSE": None}
    z = frame["z"].to_numpy(dtype=float)
    y = frame["next_z"].to_numpy(dtype=float)
    X = np.column_stack([np.ones(len(frame)), z])
    beta = r5._fit_ols(X, y)
    pred = X @ beta
    return {
        "n": int(len(frame)),
        "mean_anti_persistence": float(np.mean(frame["anti_persistence"].to_numpy(dtype=float))),
        "slope": float(beta[1]),
        "MSE": float(np.mean((y - pred) ** 2)),
    }


def _bin_shape(frame: pd.DataFrame, edges: np.ndarray) -> dict[str, Any]:
    work = frame.copy()
    work["anti_quintile"] = assign_quintiles(work["anti_persistence"].to_numpy(dtype=float), edges)
    bins = [_fit_bin(work.loc[work["anti_quintile"] == q]) for q in range(5)]
    usable = all(item["slope"] is not None and item["mean_anti_persistence"] is not None for item in bins)
    if not usable:
        return {"bins": bins, "usable": False, "top_lt_bottom": False, "shape_trend": None, "shape_supported": False}
    mean_anti = np.array([item["mean_anti_persistence"] for item in bins], dtype=float)
    slopes = np.array([item["slope"] for item in bins], dtype=float)
    trend_X = np.column_stack([np.ones(5), mean_anti])
    trend_beta = r5._fit_ols(trend_X, slopes)
    top_lt_bottom = bool(slopes[-1] < slopes[0])
    shape_trend = float(trend_beta[1])
    return {
        "bins": bins,
        "usable": True,
        "top_lt_bottom": top_lt_bottom,
        "shape_trend": shape_trend,
        "shape_supported": bool(top_lt_bottom and shape_trend < 0.0),
    }


def evaluate_D2(train: pd.DataFrame, validation: pd.DataFrame) -> dict[str, Any]:
    edges = train_quintile_edges(train)
    train_shape = _bin_shape(train, edges)
    validation_shape = _bin_shape(validation, edges)
    y2019 = _bin_shape(validation.loc[validation["year"] == 2019], edges)
    y2020 = _bin_shape(validation.loc[validation["year"] == 2020], edges)
    support = bool(validation_shape["shape_supported"] and y2019["shape_supported"] and y2020["shape_supported"])
    return {
        "TRAIN_fixed_edges": [float(x) for x in edges],
        "TRAIN": train_shape,
        "VALIDATION": validation_shape,
        "2019": y2019,
        "2020": y2020,
        "D2_shape_supported": support,
    }


def adjudicate(d1: bool, d2: bool) -> str:
    if d1 and d2:
        return "R5_B1_diagnostic_supported_for_specialist_research"
    if (not d1) and d2:
        return "R5_B1_mechanism_shape_supported_but_day_breadth_weak"
    if d1 and (not d2):
        return "R5_B1_day_breadth_supported_but_shape_weak"
    return "R5_B1_small_gain_not_robust_enough_to_specialize"


def run(data_path: Path = r5.DATA_PATH) -> dict[str, Any]:
    train, validation, beta0, beta1 = build_B_frames(data_path)
    entry = reproduce_entry_gate(train, validation, beta0, beta1)
    result: dict[str, Any] = {
        "schema_id": "factorlab_broad_rmr_R5_B1_stability_shape_diagnostic@1.0",
        "diagnostic_identity": "R5_B1_stability_shape_diagnostic_v1",
        "parent_identity": "R5_multiscale_serial_dependence_state_v1",
        "execution_scope": "post_R5_reusable_TRAIN_VALIDATION_diagnostic_no_BLACKBOX_no_PnL",
        "entry_reproduction": entry,
        "source_identity": {
            "path": str(data_path),
            "sha256": r5.sha256_file(data_path),
            "rows_expected": r5.EXPECTED_ROWS,
            "symbol": r5.SYMBOL,
            "maximum_day": r5.MAX_DAY,
        },
        "BLACKBOX_read": False,
        "post_2020_rows_read": False,
        "PnL_read": False,
        "fresh_OOS_claim": False,
        "production_authority": False,
    }
    if not entry["pass"]:
        result["D1"] = {"status": "not_executed_entry_reproduction_failed"}
        result["D2"] = {"status": "not_executed_entry_reproduction_failed"}
        result["adjudication"] = "R5_B1_diagnostic_execution_drift_or_insufficient"
        return result

    d1 = evaluate_D1(validation, beta0, beta1)
    d2 = evaluate_D2(train, validation)
    result["D1"] = d1
    result["D2"] = d2
    result["adjudication"] = adjudicate(d1["D1_day_breadth_supported"], d2["D2_shape_supported"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=r5.DATA_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.data)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(text)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
