#!/usr/bin/env python3
"""Frozen state-conditioned calibration diagnostic for R7 using read-only Layer2 5m risk states."""
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


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


r7 = _load_module("r7_parent_state_diag", ROOT / "scripts" / "run_R7_native_1m_rejected_excursion.py")
inv = _load_module("r7_l2_inventory_state_diag", ROOT / "scripts" / "inventory_R7_layer2_5m_risk_state_alignment.py")

ATOL = 1e-12
Z95 = 1.959963984540054
CHI2_DF3_95 = 7.814727903251179
EXPECTED = {
    "candidate_rows": 64215,
    "B1": np.array([0.0014301524091757736, 0.06384569479627833, -0.5327696198414718]),
    "VALIDATION_MSE_B1": 1.6349712859035168,
    "2019_MSE_B1": 1.720788967326843,
    "2020_MSE_B1": 1.5488004452973783,
    "state_matched_rows": 64152,
    "state_match_fraction": 0.9990189208128942,
}
SUPPLY_MIN = {
    "TRAIN": {"LOW_RISK": 5000, "RISK_ACTIVE": 500},
    "VALIDATION": {"LOW_RISK": 5000, "RISK_ACTIVE": 500},
    "2019": {"LOW_RISK": 5000, "RISK_ACTIVE": 500},
    "2020": {"LOW_RISK": 5000, "RISK_ACTIVE": 500},
}


def cluster_robust_ols(X: np.ndarray, y: np.ndarray, clusters: np.ndarray) -> dict[str, Any]:
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    clusters = np.asarray(clusters)
    n, k = X.shape
    if X.ndim != 2 or y.ndim != 1 or len(y) != n or len(clusters) != n:
        raise ValueError("shape mismatch")
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
    return {
        "n": int(n),
        "clusters": int(g),
        "beta": beta,
        "cov": cov,
        "se": se,
        "ci_lower": beta - Z95 * se,
        "ci_upper": beta + Z95 * se,
    }


def state_design(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    endpoint = frame["endpoint_z"].to_numpy(dtype=float)
    rejection = frame["rejection_signed_z"].to_numpy(dtype=float)
    risk = frame["risk_bucket"].eq("RISK_ACTIVE").to_numpy(dtype=float)
    X = np.column_stack([
        np.ones(len(frame)), endpoint, rejection, risk, risk * endpoint, risk * rejection
    ])
    y = frame["next5_z"].to_numpy(dtype=float)
    return X, y


def fit_state(frame: pd.DataFrame) -> np.ndarray:
    X, y = state_design(frame)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta.astype(float)


def predict_state(frame: pd.DataFrame, beta: np.ndarray) -> np.ndarray:
    X, _ = state_design(frame)
    return X @ np.asarray(beta, dtype=float)


def mse_state(frame: pd.DataFrame, beta: np.ndarray) -> float:
    _, y = state_design(frame)
    pred = predict_state(frame, beta)
    return float(np.mean((y - pred) ** 2))


def attach_frozen_states(candidates: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    five = r7._load(r7.FIVE_MIN_PATH, r7.FIVE_MIN_SHA, r7.FIVE_MIN_ROWS)
    l3 = inv.normalize_5m(five.rename(columns={"bar_end_shanghai": "timestamp"}), "timestamp")
    states, meta = inv.finalized_state_replay(l3)
    work = candidates.copy()
    work["timestamp"] = pd.to_datetime(work["bar_end_shanghai"], errors="raise").dt.strftime("%Y-%m-%d %H:%M:%S")
    out = work.merge(
        states[["timestamp", "risk_state", "risk_bucket", "vol_ratio", "shock_intensity"]],
        on="timestamp", how="left", validate="one_to_one"
    )
    return out, meta


def reproduce_entry(candidates: pd.DataFrame, attached: pd.DataFrame) -> dict[str, Any]:
    train = candidates.loc[candidates["role"].eq("TRAIN")]
    val = candidates.loc[candidates["role"].eq("VALIDATION")]
    beta1 = r7._fit(train, "B1")
    checks: dict[str, bool] = {
        "candidate_rows": len(candidates) == EXPECTED["candidate_rows"],
        "B1": bool(np.allclose(beta1, EXPECTED["B1"], rtol=0.0, atol=ATOL)),
    }
    actual: dict[str, Any] = {
        "candidate_rows": int(len(candidates)),
        "B1": [float(x) for x in beta1],
    }
    for name, frame, expected in (
        ("VALIDATION", val, EXPECTED["VALIDATION_MSE_B1"]),
        ("2019", val.loc[val["year"].eq(2019)], EXPECTED["2019_MSE_B1"]),
        ("2020", val.loc[val["year"].eq(2020)], EXPECTED["2020_MSE_B1"]),
    ):
        m = r7._mse(frame, "B1", beta1)
        actual[f"{name}_MSE_B1"] = m
        checks[f"{name}_MSE_B1"] = math.isclose(m, expected, rel_tol=0.0, abs_tol=ATOL)
    matched = attached["risk_state"].notna()
    match_fraction = float(matched.mean())
    actual["state_matched_rows"] = int(matched.sum())
    actual["state_match_fraction"] = match_fraction
    checks["state_matched_rows"] = int(matched.sum()) == EXPECTED["state_matched_rows"]
    checks["state_match_fraction"] = math.isclose(match_fraction, EXPECTED["state_match_fraction"], rel_tol=0.0, abs_tol=ATOL)
    return {"pass": bool(all(checks.values())), "checks": checks, "actual": actual, "beta1": beta1}


def supply_check(matched: pd.DataFrame) -> dict[str, Any]:
    val = matched.loc[matched["role"].eq("VALIDATION")]
    groups = {
        "TRAIN": matched.loc[matched["role"].eq("TRAIN")],
        "VALIDATION": val,
        "2019": val.loc[val["year"].eq(2019)],
        "2020": val.loc[val["year"].eq(2020)],
    }
    out: dict[str, Any] = {}
    ok = True
    for name, g in groups.items():
        vc = g["risk_bucket"].value_counts()
        item = {
            "n": int(len(g)),
            "LOW_RISK": int(vc.get("LOW_RISK", 0)),
            "RISK_ACTIVE": int(vc.get("RISK_ACTIVE", 0)),
            "trading_days": int(g["trading_day"].nunique()),
        }
        item["pass"] = bool(
            item["LOW_RISK"] >= SUPPLY_MIN[name]["LOW_RISK"]
            and item["RISK_ACTIVE"] >= SUPPLY_MIN[name]["RISK_ACTIVE"]
        )
        out[name] = item
        ok = ok and item["pass"]
    out["pass"] = bool(ok)
    return out


def evaluate_G1(train: pd.DataFrame) -> dict[str, Any]:
    X, y = state_design(train)
    fit = cluster_robust_ols(X, y, train["trading_day"].to_numpy())
    idx = np.array([3, 4, 5], dtype=int)
    c = fit["beta"][idx]
    cov_c = fit["cov"][np.ix_(idx, idx)]
    wald = float(c.T @ np.linalg.inv(cov_c) @ c)
    return {
        "n": fit["n"],
        "trading_days": fit["clusters"],
        "B2_beta": [float(x) for x in fit["beta"]],
        "B2_CI95": [[float(fit["ci_lower"][i]), float(fit["ci_upper"][i])] for i in range(6)],
        "interaction_beta": [float(x) for x in c],
        "joint_wald_df3": wald,
        "chi_square_95_critical": CHI2_DF3_95,
        "G1_heterogeneity_supported": bool(wald > CHI2_DF3_95),
    }


def bucket_vectors(frame: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for bucket in ("LOW_RISK", "RISK_ACTIVE"):
        g = frame.loc[frame["risk_bucket"].eq(bucket)]
        beta = r7._fit(g, "B1")
        out[bucket] = {
            "n": int(len(g)),
            "trading_days": int(g["trading_day"].nunique()),
            "local_B1_beta": [float(x) for x in beta],
            "local_rejection_coefficient": float(beta[2]),
        }
    return out


def evaluate_G2(matched: pd.DataFrame, beta1: np.ndarray, beta2: np.ndarray) -> dict[str, Any]:
    val = matched.loc[matched["role"].eq("VALIDATION")]
    groups = {
        "VALIDATION": val,
        "2019": val.loc[val["year"].eq(2019)],
        "2020": val.loc[val["year"].eq(2020)],
    }
    out: dict[str, Any] = {}
    supported = True
    for name, g in groups.items():
        mse1 = r7._mse(g, "B1", beta1)
        mse2 = mse_state(g, beta2)
        bucket_mse: dict[str, Any] = {}
        for bucket in ("LOW_RISK", "RISK_ACTIVE"):
            b = g.loc[g["risk_bucket"].eq(bucket)]
            bucket_mse[bucket] = {
                "n": int(len(b)),
                "MSE_B1": r7._mse(b, "B1", beta1),
                "MSE_B2": mse_state(b, beta2),
            }
        item = {
            "n": int(len(g)),
            "MSE_B1": mse1,
            "MSE_B2": mse2,
            "improvement": float(mse1 - mse2),
            "relative_improvement": float((mse1 - mse2) / mse1) if mse1 > 0 else None,
            "B2_better": bool(mse2 < mse1),
            "bucket_MSE_descriptive": bucket_mse,
        }
        out[name] = item
        supported = supported and item["B2_better"]
    out["G2_prediction_supported"] = bool(supported)
    return out


def _contains(ci: list[float], value: float) -> bool:
    return bool(ci[0] - ATOL <= value <= ci[1] + ATOL)


def calibration_group(frame: pd.DataFrame, beta2: np.ndarray) -> dict[str, Any]:
    X2, y = state_design(frame)
    pred = X2 @ beta2
    clusters = frame["trading_day"].to_numpy()
    cal = cluster_robust_ols(np.column_stack([np.ones(len(frame)), pred]), y, clusters)
    resid = y - pred
    resfit = cluster_robust_ols(X2, resid, clusters)
    cal_int_ci = [float(cal["ci_lower"][0]), float(cal["ci_upper"][0])]
    cal_slope_ci = [float(cal["ci_lower"][1]), float(cal["ci_upper"][1])]
    residual_feature_cis = [
        [float(resfit["ci_lower"][i]), float(resfit["ci_upper"][i])] for i in range(1, 6)
    ]
    clean = (
        _contains(cal_int_ci, 0.0)
        and _contains(cal_slope_ci, 1.0)
        and all(_contains(ci, 0.0) for ci in residual_feature_cis)
    )
    return {
        "n": int(len(frame)),
        "trading_days": int(cal["clusters"]),
        "calibration_intercept": float(cal["beta"][0]),
        "calibration_intercept_CI95": cal_int_ci,
        "calibration_slope": float(cal["beta"][1]),
        "calibration_slope_CI95": cal_slope_ci,
        "residual_beta": [float(x) for x in resfit["beta"]],
        "residual_feature_CI95": residual_feature_cis,
        "clean": bool(clean),
    }


def evaluate_G3(matched: pd.DataFrame, beta2: np.ndarray) -> dict[str, Any]:
    val = matched.loc[matched["role"].eq("VALIDATION")]
    out = {
        "VALIDATION": calibration_group(val, beta2),
        "2019": calibration_group(val.loc[val["year"].eq(2019)], beta2),
        "2020": calibration_group(val.loc[val["year"].eq(2020)], beta2),
    }
    out["G3_calibration_clean"] = bool(all(out[g]["clean"] for g in ("VALIDATION", "2019", "2020")))
    return out


def adjudicate(g1: bool, g2: bool, g3: bool) -> str:
    if not g1:
        return "R7_L2_state_conditioning_not_supported"
    if not g2:
        return "R7_L2_state_heterogeneity_supported_but_prediction_not_robust"
    if g3:
        return "R7_L2_state_conditioning_supported_calibration_clean"
    return "R7_L2_state_conditioning_supported_residual_drift"


def run() -> dict[str, Any]:
    candidates = r7.build_candidates()
    attached, replay_meta = attach_frozen_states(candidates)
    entry = reproduce_entry(candidates, attached)
    base: dict[str, Any] = {
        "schema_id": "factorlab_R7_L2_5m_risk_bucket_calibration_diagnostic@1.0",
        "identity": "R7_L2_5m_risk_bucket_calibration_diagnostic_v1",
        "parent_identity": "R7_native_1m_rejected_excursion_v1",
        "entry_reproduction": {k: v for k, v in entry.items() if k != "beta1"},
        "state_replay_meta": replay_meta,
        "BLACKBOX_read": False,
        "post_2020_rows_read": False,
        "PnL_read": False,
        "fresh_OOS_claim": False,
        "production_authority": False,
    }
    if not entry["pass"]:
        base["adjudication"] = "R7_L2_state_diagnostic_execution_drift_or_insufficient"
        return base
    matched = attached.loc[attached["risk_state"].notna()].copy()
    supply = supply_check(matched)
    base["supply"] = supply
    if not supply["pass"]:
        base["adjudication"] = "R7_L2_state_diagnostic_execution_drift_or_insufficient"
        return base

    train = matched.loc[matched["role"].eq("TRAIN")].copy()
    beta2 = fit_state(train)
    g1 = evaluate_G1(train)
    g2 = evaluate_G2(matched, entry["beta1"], beta2)
    g3 = evaluate_G3(matched, beta2)
    val = matched.loc[matched["role"].eq("VALIDATION")]
    base["TRAIN_B2_beta"] = [float(x) for x in beta2]
    base["derived_bucket_parameters"] = {
        "LOW_RISK": [float(beta2[0]), float(beta2[1]), float(beta2[2])],
        "RISK_ACTIVE": [float(beta2[0] + beta2[3]), float(beta2[1] + beta2[4]), float(beta2[2] + beta2[5])],
    }
    base["bucket_local_vectors_descriptive"] = {
        "TRAIN": bucket_vectors(train),
        "VALIDATION": bucket_vectors(val),
        "2019": bucket_vectors(val.loc[val["year"].eq(2019)]),
        "2020": bucket_vectors(val.loc[val["year"].eq(2020)]),
    }
    base["G1"] = g1
    base["G2"] = g2
    base["G3"] = g3
    base["adjudication"] = adjudicate(
        bool(g1["G1_heterogeneity_supported"]),
        bool(g2["G2_prediction_supported"]),
        bool(g3["G3_calibration_clean"]),
    )
    return base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
