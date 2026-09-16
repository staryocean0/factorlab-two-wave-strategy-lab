#!/usr/bin/env python3
"""Frozen R7 specialist Stage 1 inferential-readiness diagnostic."""

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
PARENT = ROOT / "scripts" / "run_R7_native_1m_rejected_excursion.py"
SPEC = importlib.util.spec_from_file_location("r7_parent_stage1", PARENT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load frozen R7 parent")
r7 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = r7
SPEC.loader.exec_module(r7)

ATOL = 1e-12
Z95 = 1.959963984540054
BOOTSTRAP_SEED = 20260916
BOOTSTRAP_REPS = 10000
EXPECTED = {
    "candidate_rows": 64215,
    "B0": np.array([0.0137526453386167, 0.04853230586734814]),
    "B1": np.array([0.0014301524091757736, 0.06384569479627833, -0.5327696198414718]),
    "VALIDATION": (1.6598472863016687, 1.6349712859035168),
    "2019": (1.7444187739434946, 1.720788967326843),
    "2020": (1.5749277678465021, 1.5488004452973783),
}


def reproduce_entry(candidates: pd.DataFrame) -> dict[str, Any]:
    train = candidates.loc[candidates["role"] == "TRAIN"].copy()
    val = candidates.loc[candidates["role"] == "VALIDATION"].copy()
    beta0 = r7._fit(train, "B0")
    beta1 = r7._fit(train, "B1")
    checks: dict[str, bool] = {
        "candidate_rows": len(candidates) == EXPECTED["candidate_rows"],
        "B0": bool(np.allclose(beta0, EXPECTED["B0"], rtol=0.0, atol=ATOL)),
        "B1": bool(np.allclose(beta1, EXPECTED["B1"], rtol=0.0, atol=ATOL)),
    }
    actual: dict[str, Any] = {
        "candidate_rows": int(len(candidates)),
        "B0": [float(x) for x in beta0],
        "B1": [float(x) for x in beta1],
    }
    for name, frame in (
        ("VALIDATION", val),
        ("2019", val.loc[val["year"] == 2019]),
        ("2020", val.loc[val["year"] == 2020]),
    ):
        mse0 = r7._mse(frame, "B0", beta0)
        mse1 = r7._mse(frame, "B1", beta1)
        actual[f"{name}_MSE_B0"] = mse0
        actual[f"{name}_MSE_B1"] = mse1
        checks[f"{name}_MSE_B0"] = math.isclose(mse0, EXPECTED[name][0], rel_tol=0.0, abs_tol=ATOL)
        checks[f"{name}_MSE_B1"] = math.isclose(mse1, EXPECTED[name][1], rel_tol=0.0, abs_tol=ATOL)
    return {
        "pass": bool(all(checks.values())),
        "checks": checks,
        "actual": actual,
        "beta0": beta0,
        "beta1": beta1,
    }


def cluster_robust_ols(X: np.ndarray, y: np.ndarray, clusters: np.ndarray) -> dict[str, Any]:
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    clusters = np.asarray(clusters)
    if X.ndim != 2 or y.ndim != 1 or len(X) != len(y) or len(y) != len(clusters):
        raise ValueError("shape mismatch")
    n, k = X.shape
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    xtx_inv = np.linalg.inv(X.T @ X)
    unique = pd.unique(clusters)
    g = len(unique)
    if g <= 1 or n <= k:
        raise ValueError("insufficient clusters")
    meat = np.zeros((k, k), dtype=float)
    for label in unique:
        idx = clusters == label
        score = X[idx].T @ resid[idx]
        meat += np.outer(score, score)
    correction = (g / (g - 1.0)) * ((n - 1.0) / (n - k))
    cov = correction * (xtx_inv @ meat @ xtx_inv)
    se = np.sqrt(np.clip(np.diag(cov), 0.0, np.inf))
    lower = beta - Z95 * se
    upper = beta + Z95 * se
    return {
        "n": int(n),
        "clusters": int(g),
        "beta": beta,
        "se": se,
        "ci_lower": lower,
        "ci_upper": upper,
    }


def _b1_matrix(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    X = np.column_stack([
        np.ones(len(frame)),
        frame["endpoint_z"].to_numpy(dtype=float),
        frame["rejection_signed_z"].to_numpy(dtype=float),
    ])
    y = frame["next5_z"].to_numpy(dtype=float)
    return X, y


def evaluate_C1(candidates: pd.DataFrame) -> dict[str, Any]:
    train = candidates.loc[candidates["role"] == "TRAIN"].copy()
    val = candidates.loc[candidates["role"] == "VALIDATION"].copy()
    groups = {
        "TRAIN": train,
        "VALIDATION": val,
        "2019": val.loc[val["year"] == 2019].copy(),
        "2020": val.loc[val["year"] == 2020].copy(),
    }
    out: dict[str, Any] = {}
    supported = True
    for name, frame in groups.items():
        X, y = _b1_matrix(frame)
        fit = cluster_robust_ols(X, y, frame["trading_day"].to_numpy())
        item = {
            "n": fit["n"],
            "trading_days": fit["clusters"],
            "beta": [float(x) for x in fit["beta"]],
            "rejection_coefficient": float(fit["beta"][2]),
            "rejection_se_CR1": float(fit["se"][2]),
            "rejection_CI95_lower": float(fit["ci_lower"][2]),
            "rejection_CI95_upper": float(fit["ci_upper"][2]),
        }
        item["supported"] = bool(item["rejection_CI95_upper"] < 0.0)
        out[name] = item
        supported = supported and item["supported"]
    out["C1_clustered_coefficient_supported"] = bool(supported)
    return out


def _day_improvements(frame: pd.DataFrame, beta0: np.ndarray, beta1: np.ndarray) -> pd.Series:
    work = frame[["trading_day"]].copy()
    _, y0 = r7._design(frame, "B0")
    pred0 = r7._predict(frame, "B0", beta0)
    pred1 = r7._predict(frame, "B1", beta1)
    work["sq0"] = (y0 - pred0) ** 2
    work["sq1"] = (y0 - pred1) ** 2
    daily = work.groupby("trading_day", sort=True)[["sq0", "sq1"]].mean()
    return (daily["sq0"] - daily["sq1"]).astype(float)


def bootstrap_mean_ci(values: np.ndarray, seed: int = BOOTSTRAP_SEED, reps: int = BOOTSTRAP_REPS) -> tuple[float, float]:
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        raise ValueError("empty bootstrap input")
    rng = np.random.default_rng(seed)
    means = np.empty(reps, dtype=float)
    for i in range(reps):
        sample = rng.choice(arr, size=len(arr), replace=True)
        means[i] = float(np.mean(sample))
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def _day_summary(frame: pd.DataFrame, beta0: np.ndarray, beta1: np.ndarray, seed_offset: int) -> dict[str, Any]:
    d = _day_improvements(frame, beta0, beta1)
    ci = bootstrap_mean_ci(d.to_numpy(dtype=float), BOOTSTRAP_SEED + seed_offset, BOOTSTRAP_REPS)
    arr = d.to_numpy(dtype=float)
    return {
        "days": int(len(arr)),
        "mean_day_improvement": float(np.mean(arr)),
        "median_day_improvement": float(np.median(arr)),
        "fraction_positive_days": float(np.mean(arr > 0.0)),
        "p10_day_improvement": float(np.quantile(arr, 0.10)),
        "p90_day_improvement": float(np.quantile(arr, 0.90)),
        "bootstrap_mean_CI95_lower": ci[0],
        "bootstrap_mean_CI95_upper": ci[1],
    }


def evaluate_C2(candidates: pd.DataFrame, beta0: np.ndarray, beta1: np.ndarray) -> dict[str, Any]:
    val = candidates.loc[candidates["role"] == "VALIDATION"].copy()
    out = {
        "bootstrap_seed_base": BOOTSTRAP_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPS,
        "VALIDATION": _day_summary(val, beta0, beta1, 0),
        "2019": _day_summary(val.loc[val["year"] == 2019].copy(), beta0, beta1, 1),
        "2020": _day_summary(val.loc[val["year"] == 2020].copy(), beta0, beta1, 2),
    }
    supported = True
    for name in ("2019", "2020"):
        x = out[name]
        x["supported"] = bool(
            x["bootstrap_mean_CI95_lower"] > 0.0
            and x["median_day_improvement"] > 0.0
            and x["fraction_positive_days"] > 0.50
        )
        supported = supported and x["supported"]
    out["C2_day_prediction_robustness_supported"] = bool(supported)
    return out


def _ci_contains(lower: float, upper: float, value: float) -> bool:
    return bool(lower <= value <= upper)


def _calibration_group(frame: pd.DataFrame, beta1: np.ndarray) -> dict[str, Any]:
    _, y = r7._design(frame, "B1")
    pred = r7._predict(frame, "B1", beta1)
    clusters = frame["trading_day"].to_numpy()

    Xcal = np.column_stack([np.ones(len(frame)), pred])
    cal = cluster_robust_ols(Xcal, y, clusters)

    residual = y - pred
    Xres = np.column_stack([
        np.ones(len(frame)),
        frame["endpoint_z"].to_numpy(dtype=float),
        frame["rejection_signed_z"].to_numpy(dtype=float),
    ])
    res = cluster_robust_ols(Xres, residual, clusters)

    item = {
        "n": int(len(frame)),
        "trading_days": int(cal["clusters"]),
        "calibration_intercept": float(cal["beta"][0]),
        "calibration_intercept_CI95": [float(cal["ci_lower"][0]), float(cal["ci_upper"][0])],
        "calibration_slope": float(cal["beta"][1]),
        "calibration_slope_CI95": [float(cal["ci_lower"][1]), float(cal["ci_upper"][1])],
        "residual_endpoint_slope": float(res["beta"][1]),
        "residual_endpoint_CI95": [float(res["ci_lower"][1]), float(res["ci_upper"][1])],
        "residual_rejection_slope": float(res["beta"][2]),
        "residual_rejection_CI95": [float(res["ci_lower"][2]), float(res["ci_upper"][2])],
    }
    item["calibration_intercept_contains_0"] = _ci_contains(*item["calibration_intercept_CI95"], 0.0)
    item["calibration_slope_contains_1"] = _ci_contains(*item["calibration_slope_CI95"], 1.0)
    item["residual_endpoint_contains_0"] = _ci_contains(*item["residual_endpoint_CI95"], 0.0)
    item["residual_rejection_contains_0"] = _ci_contains(*item["residual_rejection_CI95"], 0.0)
    item["clean"] = bool(
        item["calibration_intercept_contains_0"]
        and item["calibration_slope_contains_1"]
        and item["residual_endpoint_contains_0"]
        and item["residual_rejection_contains_0"]
    )
    return item


def evaluate_C3(candidates: pd.DataFrame, beta1: np.ndarray) -> dict[str, Any]:
    val = candidates.loc[candidates["role"] == "VALIDATION"].copy()
    out = {
        "VALIDATION": _calibration_group(val, beta1),
        "2019": _calibration_group(val.loc[val["year"] == 2019].copy(), beta1),
        "2020": _calibration_group(val.loc[val["year"] == 2020].copy(), beta1),
    }
    out["C3_calibration_clean"] = bool(all(out[g]["clean"] for g in ("VALIDATION", "2019", "2020")))
    return out


def adjudicate(c1: bool, c2: bool, c3: bool) -> str:
    if not c1 or not c2:
        return "R7_specialist_stage1_inferential_support_insufficient"
    if c3:
        return "R7_specialist_stage1_inferentially_supported_calibration_clean"
    return "R7_specialist_stage1_inferentially_supported_calibration_drift"


def run() -> dict[str, Any]:
    candidates = r7.build_candidates()
    entry = reproduce_entry(candidates)
    base: dict[str, Any] = {
        "schema_id": "factorlab_R7_specialist_stage1_inferential_readiness@1.0",
        "identity": "R7_specialist_stage1_inferential_readiness_v1",
        "parent_identity": "R7_native_1m_rejected_excursion_v1",
        "entry_reproduction": {k: v for k, v in entry.items() if k not in ("beta0", "beta1")},
        "BLACKBOX_read": False,
        "post_2020_rows_read": False,
        "PnL_read": False,
        "fresh_OOS_claim": False,
        "production_authority": False,
    }
    if not entry["pass"]:
        base["adjudication"] = "R7_specialist_stage1_execution_drift_or_insufficient"
        return base
    c1 = evaluate_C1(candidates)
    c2 = evaluate_C2(candidates, entry["beta0"], entry["beta1"])
    c3 = evaluate_C3(candidates, entry["beta1"])
    base["C1"] = c1
    base["C2"] = c2
    base["C3"] = c3
    base["adjudication"] = adjudicate(
        bool(c1["C1_clustered_coefficient_supported"]),
        bool(c2["C2_day_prediction_robustness_supported"]),
        bool(c3["C3_calibration_clean"]),
    )
    return base


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
