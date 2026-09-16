#!/usr/bin/env python3
"""Frozen bounded diagnostic for R7 native 1m rejected-excursion identity."""

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
SPEC = importlib.util.spec_from_file_location("r7_parent", PARENT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load frozen R7 parent")
r7 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = r7
SPEC.loader.exec_module(r7)

ATOL = 1e-12
MIN_BLOCK = 4000
MIN_BIN = 300
MIN_SIGN_BIN = 100
EXPECTED_TRAIN_BLOCKS = [f"{y}H{h}" for y in range(2015, 2019) for h in (1, 2)]
EXPECTED_VALID_BLOCKS = [f"{y}H{h}" for y in range(2019, 2021) for h in (1, 2)]
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
    actual: dict[str, Any] = {
        "candidate_rows": int(len(candidates)),
        "B0": [float(x) for x in beta0],
        "B1": [float(x) for x in beta1],
    }
    checks: dict[str, bool] = {
        "candidate_rows": len(candidates) == EXPECTED["candidate_rows"],
        "B0": bool(np.allclose(beta0, EXPECTED["B0"], rtol=0.0, atol=ATOL)),
        "B1": bool(np.allclose(beta1, EXPECTED["B1"], rtol=0.0, atol=ATOL)),
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
    return {"pass": bool(all(checks.values())), "checks": checks, "actual": actual, "beta0": beta0, "beta1": beta1}


def add_halfyear(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    dt = pd.to_datetime(out["trading_day"], errors="raise")
    half = np.where(dt.dt.month.to_numpy() <= 6, 1, 2)
    out["halfyear"] = dt.dt.year.astype(str) + "H" + pd.Series(half, index=out.index).astype(str)
    return out


def evaluate_D1(candidates: pd.DataFrame, beta0: np.ndarray, beta1: np.ndarray, min_block: int = MIN_BLOCK) -> dict[str, Any]:
    train = add_halfyear(candidates.loc[candidates["role"] == "TRAIN"].copy())
    val = add_halfyear(candidates.loc[candidates["role"] == "VALIDATION"].copy())
    roles: dict[str, Any] = {}
    usable = True
    for role, frame, labels in (("TRAIN", train, EXPECTED_TRAIN_BLOCKS), ("VALIDATION", val, EXPECTED_VALID_BLOCKS)):
        blocks = []
        for label in labels:
            sub = frame.loc[frame["halfyear"] == label].copy()
            item: dict[str, Any] = {"block": label, "n": int(len(sub))}
            if len(sub) < min_block:
                item["usable"] = False
                usable = False
            else:
                local = r7._fit(sub, "B1")
                mse0 = r7._mse(sub, "B0", beta0)
                mse1 = r7._mse(sub, "B1", beta1)
                item.update({
                    "usable": True,
                    "local_rejection_coefficient": float(local[2]),
                    "fixed_B0_MSE": mse0,
                    "fixed_B1_MSE": mse1,
                    "fixed_B1_improvement": float(mse0 - mse1),
                })
            blocks.append(item)
        roles[role] = {"blocks": blocks}
    if not usable:
        return {"usable": False, "minimum_candidates_per_block": int(min_block), "roles": roles, "D1_time_stability_supported": False}

    tc = np.array([x["local_rejection_coefficient"] for x in roles["TRAIN"]["blocks"]], dtype=float)
    vc = np.array([x["local_rejection_coefficient"] for x in roles["VALIDATION"]["blocks"]], dtype=float)
    vi = np.array([x["fixed_B1_improvement"] for x in roles["VALIDATION"]["blocks"]], dtype=float)
    summary = {
        "TRAIN_negative_coefficient_blocks": int(np.sum(tc < 0.0)),
        "TRAIN_median_coefficient": float(np.median(tc)),
        "VALIDATION_negative_coefficient_blocks": int(np.sum(vc < 0.0)),
        "VALIDATION_median_coefficient": float(np.median(vc)),
        "VALIDATION_positive_fixed_improvement_blocks": int(np.sum(vi > 0.0)),
        "VALIDATION_median_fixed_improvement": float(np.median(vi)),
    }
    supported = (
        summary["TRAIN_negative_coefficient_blocks"] >= 6
        and summary["TRAIN_median_coefficient"] < 0.0
        and summary["VALIDATION_negative_coefficient_blocks"] >= 3
        and summary["VALIDATION_median_coefficient"] < 0.0
        and summary["VALIDATION_positive_fixed_improvement_blocks"] >= 3
    )
    return {"usable": True, "minimum_candidates_per_block": int(min_block), "roles": roles, "summary": summary, "D1_time_stability_supported": bool(supported)}


def train_magnitude_edges(train: pd.DataFrame) -> np.ndarray:
    nz = np.abs(train.loc[train["rejection_signed_z"] != 0.0, "rejection_signed_z"].to_numpy(dtype=float))
    edges = np.quantile(nz, [0.2, 0.4, 0.6, 0.8])
    if len(edges) != 4 or not np.all(np.diff(edges) > 0.0):
        raise RuntimeError("non-strict TRAIN magnitude quintile edges")
    return edges.astype(float)


def _shape_group(frame: pd.DataFrame, beta0: np.ndarray, edges: np.ndarray, min_bin: int, min_sign: int) -> dict[str, Any]:
    work = frame.loc[frame["rejection_signed_z"] != 0.0].copy()
    rz = work["rejection_signed_z"].to_numpy(dtype=float)
    _, y = r7._design(work, "B0")
    residual = y - r7._predict(work, "B0", beta0)
    work["abs_rejection"] = np.abs(rz)
    work["residual"] = residual
    work["aligned_score"] = -np.sign(rz) * residual
    work["bin"] = np.searchsorted(edges, work["abs_rejection"].to_numpy(dtype=float), side="right")
    bins: list[dict[str, Any]] = []
    usable = True
    for q in range(5):
        sub = work.loc[work["bin"] == q].copy()
        pos = sub.loc[sub["rejection_signed_z"] > 0.0]
        neg = sub.loc[sub["rejection_signed_z"] < 0.0]
        item: dict[str, Any] = {"bin": q + 1, "n": int(len(sub)), "positive_n": int(len(pos)), "negative_n": int(len(neg))}
        if len(sub) < min_bin or len(pos) < min_sign or len(neg) < min_sign:
            item["usable"] = False
            usable = False
        else:
            item.update({
                "usable": True,
                "mean_abs_rejection": float(sub["abs_rejection"].mean()),
                "mean_aligned_score": float(sub["aligned_score"].mean()),
                "positive_mean_residual": float(pos["residual"].mean()),
                "negative_mean_residual": float(neg["residual"].mean()),
            })
        bins.append(item)
    if not usable:
        return {"usable": False, "bins": bins, "shape_supported": False}
    x = np.array([b["mean_abs_rejection"] for b in bins], dtype=float)
    s = np.array([b["mean_aligned_score"] for b in bins], dtype=float)
    trend = float(np.polyfit(x, s, 1)[0])
    top = bins[-1]
    bottom = bins[0]
    supported = (
        trend > 0.0
        and top["mean_aligned_score"] > bottom["mean_aligned_score"]
        and top["mean_aligned_score"] > 0.0
        and top["positive_mean_residual"] < 0.0
        and top["negative_mean_residual"] > 0.0
    )
    return {
        "usable": True,
        "bins": bins,
        "linear_trend_score_vs_abs_rejection": trend,
        "top_gt_bottom": bool(top["mean_aligned_score"] > bottom["mean_aligned_score"]),
        "top_score_positive": bool(top["mean_aligned_score"] > 0.0),
        "top_sign_symmetry": bool(top["positive_mean_residual"] < 0.0 and top["negative_mean_residual"] > 0.0),
        "shape_supported": bool(supported),
    }


def evaluate_D2(candidates: pd.DataFrame, beta0: np.ndarray, min_bin: int = MIN_BIN, min_sign: int = MIN_SIGN_BIN) -> dict[str, Any]:
    train = candidates.loc[candidates["role"] == "TRAIN"].copy()
    val = candidates.loc[candidates["role"] == "VALIDATION"].copy()
    edges = train_magnitude_edges(train)
    groups = {"TRAIN": train, "VALIDATION": val, "2019": val.loc[val["year"] == 2019].copy(), "2020": val.loc[val["year"] == 2020].copy()}
    out: dict[str, Any] = {"TRAIN_fixed_abs_rejection_edges": [float(x) for x in edges], "minimum_total_rows_per_bin": int(min_bin), "minimum_each_sign_rows_per_bin": int(min_sign)}
    usable = True
    for name, frame in groups.items():
        out[name] = _shape_group(frame, beta0, edges, min_bin, min_sign)
        usable = usable and bool(out[name]["usable"])
    out["usable"] = bool(usable)
    out["D2_magnitude_shape_supported"] = bool(usable and all(out[g]["shape_supported"] for g in groups))
    return out


def adjudicate(d1: bool, d2: bool) -> str:
    if d1 and d2:
        return "R7_diagnostic_supported_for_specialist_research"
    if d1 and not d2:
        return "R7_diagnostic_time_stable_but_magnitude_shape_weak"
    if not d1 and d2:
        return "R7_diagnostic_shape_supported_but_time_stability_weak"
    return "R7_diagnostic_not_robust_enough_for_specialist"


def run() -> dict[str, Any]:
    candidates = r7.build_candidates()
    entry = reproduce_entry(candidates)
    base: dict[str, Any] = {
        "schema_id": "factorlab_R7_rejected_excursion_stability_shape_diagnostic@1.0",
        "parent_identity": "R7_native_1m_rejected_excursion_v1",
        "diagnostic_identity": "R7_rejected_excursion_stability_shape_diagnostic_v1",
        "entry_reproduction": {k: v for k, v in entry.items() if k not in ("beta0", "beta1")},
        "BLACKBOX_read": False,
        "post_2020_rows_read": False,
        "PnL_read": False,
        "fresh_OOS_claim": False,
        "production_authority": False,
    }
    if not entry["pass"]:
        base["adjudication"] = "R7_diagnostic_execution_drift_or_insufficient"
        return base
    d1 = evaluate_D1(candidates, entry["beta0"], entry["beta1"])
    d2 = evaluate_D2(candidates, entry["beta0"])
    base["D1"] = d1
    base["D2"] = d2
    if not d1["usable"] or not d2["usable"]:
        base["adjudication"] = "R7_diagnostic_execution_drift_or_insufficient"
        return base
    base["adjudication"] = adjudicate(bool(d1["D1_time_stability_supported"]), bool(d2["D2_magnitude_shape_supported"]))
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
