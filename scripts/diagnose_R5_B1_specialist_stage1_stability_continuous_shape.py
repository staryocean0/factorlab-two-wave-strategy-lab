#!/usr/bin/env python3
"""Frozen Stage-1 specialist diagnostic for the R5-B1 anti-persistence interaction.

Reusable TRAIN/VALIDATION research only. No BLACKBOX, post-2020, PnL, or production authority.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PARENT_DIAG = ROOT / "scripts" / "diagnose_broad_rmr_R5_B1_stability_shape.py"
SPEC = importlib.util.spec_from_file_location("r5_b1_cl008", PARENT_DIAG)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load CL-008 diagnostic runner")
cl008 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cl008
SPEC.loader.exec_module(cl008)
r5 = cl008.r5

MIN_BLOCK_ROWS = 1000
MIN_BIN_ROWS = 100
EXPECTED_TRAIN_BLOCKS = [f"{year}H{half}" for year in range(2015, 2019) for half in (1, 2)]
EXPECTED_VALIDATION_BLOCKS = [f"{year}H{half}" for year in range(2019, 2021) for half in (1, 2)]


def add_halfyear(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    ts = pd.to_datetime(out["bar_end_shanghai"], errors="raise")
    half = np.where(ts.dt.month.to_numpy() <= 6, 1, 2)
    out["halfyear"] = out["year"].astype(int).astype(str) + "H" + pd.Series(half, index=out.index).astype(str)
    return out


def _mse(y: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean((np.asarray(y, dtype=float) - np.asarray(pred, dtype=float)) ** 2))


def _local_b1_interaction(block: pd.DataFrame) -> float:
    X, y = r5._design_B(block, "B1")
    beta = r5._fit_ols(X, y)
    return float(beta[2])


def _fixed_improvement(block: pd.DataFrame, beta0: np.ndarray, beta1: np.ndarray) -> tuple[float, float, float]:
    X0, y = r5._design_B(block, "B0")
    X1, _ = r5._design_B(block, "B1")
    mse0 = _mse(y, r5._predict(X0, beta0))
    mse1 = _mse(y, r5._predict(X1, beta1))
    return mse0, mse1, float(mse0 - mse1)


def evaluate_S1(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    beta0: np.ndarray,
    beta1: np.ndarray,
    min_block_rows: int = MIN_BLOCK_ROWS,
) -> dict[str, Any]:
    train_h = add_halfyear(train)
    val_h = add_halfyear(validation)
    rows: dict[str, dict[str, Any]] = {}
    usable = True
    for role, frame, labels in (
        ("TRAIN", train_h, EXPECTED_TRAIN_BLOCKS),
        ("VALIDATION", val_h, EXPECTED_VALIDATION_BLOCKS),
    ):
        role_rows: list[dict[str, Any]] = []
        for label in labels:
            block = frame.loc[frame["halfyear"] == label].copy()
            item: dict[str, Any] = {"block": label, "n": int(len(block))}
            if len(block) < min_block_rows:
                item["usable"] = False
                usable = False
            else:
                interaction = _local_b1_interaction(block)
                mse0, mse1, improvement = _fixed_improvement(block, beta0, beta1)
                item.update(
                    {
                        "usable": True,
                        "local_B1_interaction": interaction,
                        "fixed_B0_MSE": mse0,
                        "fixed_B1_MSE": mse1,
                        "fixed_B1_improvement": improvement,
                    }
                )
            role_rows.append(item)
        rows[role] = {"blocks": role_rows}

    if not usable:
        return {"usable": False, "minimum_rows_per_block": int(min_block_rows), "roles": rows, "S1_time_stability_supported": False}

    train_coef = np.array([x["local_B1_interaction"] for x in rows["TRAIN"]["blocks"]], dtype=float)
    val_coef = np.array([x["local_B1_interaction"] for x in rows["VALIDATION"]["blocks"]], dtype=float)
    val_imp = np.array([x["fixed_B1_improvement"] for x in rows["VALIDATION"]["blocks"]], dtype=float)
    summary = {
        "TRAIN_negative_local_interaction_blocks": int(np.sum(train_coef < 0.0)),
        "TRAIN_median_local_interaction": float(np.median(train_coef)),
        "VALIDATION_negative_local_interaction_blocks": int(np.sum(val_coef < 0.0)),
        "VALIDATION_median_local_interaction": float(np.median(val_coef)),
        "VALIDATION_positive_fixed_B1_improvement_blocks": int(np.sum(val_imp > 0.0)),
        "VALIDATION_median_fixed_B1_improvement": float(np.median(val_imp)),
    }
    supported = (
        summary["TRAIN_negative_local_interaction_blocks"] >= 6
        and summary["TRAIN_median_local_interaction"] < 0.0
        and summary["VALIDATION_negative_local_interaction_blocks"] >= 3
        and summary["VALIDATION_median_local_interaction"] < 0.0
        and summary["VALIDATION_positive_fixed_B1_improvement_blocks"] >= 3
    )
    return {
        "usable": True,
        "minimum_rows_per_block": int(min_block_rows),
        "roles": rows,
        "summary": summary,
        "S1_time_stability_supported": bool(supported),
    }


def train_decile_edges(train: pd.DataFrame) -> np.ndarray:
    anti = train["anti_persistence"].to_numpy(dtype=float)
    edges = np.quantile(anti, np.arange(0.1, 1.0, 0.1))
    if len(edges) != 9 or not np.all(np.diff(edges) > 0.0):
        raise RuntimeError("non-strict TRAIN decile edges")
    return edges.astype(float)


def assign_deciles(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    return np.searchsorted(np.asarray(edges, dtype=float), np.asarray(values, dtype=float), side="right").astype(int)


def _slope_fit(frame: pd.DataFrame) -> tuple[float, float]:
    z = frame["z"].to_numpy(dtype=float)
    y = frame["next_z"].to_numpy(dtype=float)
    X = np.column_stack([np.ones(len(frame)), z])
    beta = r5._fit_ols(X, y)
    pred = r5._predict(X, beta)
    return float(beta[1]), _mse(y, pred)


def _shape_group(frame: pd.DataFrame, edges: np.ndarray, min_bin_rows: int) -> dict[str, Any]:
    work = frame.copy()
    work["decile"] = assign_deciles(work["anti_persistence"].to_numpy(dtype=float), edges)
    bins: list[dict[str, Any]] = []
    usable = True
    for q in range(10):
        sub = work.loc[work["decile"] == q].copy()
        item: dict[str, Any] = {"decile": q + 1, "n": int(len(sub))}
        if len(sub) < min_bin_rows:
            item["usable"] = False
            usable = False
        else:
            slope, mse = _slope_fit(sub)
            item.update(
                {
                    "usable": True,
                    "mean_anti_persistence": float(sub["anti_persistence"].mean()),
                    "slope": slope,
                    "MSE": mse,
                }
            )
        bins.append(item)
    if not usable:
        return {"usable": False, "bins": bins, "shape_supported": False}

    means = np.array([x["mean_anti_persistence"] for x in bins], dtype=float)
    slopes = np.array([x["slope"] for x in bins], dtype=float)
    trend = float(np.polyfit(means, slopes, 1)[0])
    slope_ranks = pd.Series(slopes).rank(method="average").to_numpy(dtype=float)
    mean_ranks = pd.Series(means).rank(method="average").to_numpy(dtype=float)
    spearman = float(np.corrcoef(mean_ranks, slope_ranks)[0, 1])
    bottom20 = work.loc[work["decile"] <= 1]
    top20 = work.loc[work["decile"] >= 8]
    bottom20_slope, _ = _slope_fit(bottom20)
    top20_slope, _ = _slope_fit(top20)
    return {
        "usable": True,
        "bins": bins,
        "linear_trend": trend,
        "spearman": spearman,
        "bottom20_slope": bottom20_slope,
        "top20_slope": top20_slope,
    }


def evaluate_S2(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    min_bin_rows: int = MIN_BIN_ROWS,
) -> dict[str, Any]:
    edges = train_decile_edges(train)
    groups = {
        "TRAIN": train,
        "VALIDATION": validation,
        "2019": validation.loc[validation["year"] == 2019].copy(),
        "2020": validation.loc[validation["year"] == 2020].copy(),
    }
    out: dict[str, Any] = {
        "TRAIN_fixed_decile_edges": [float(x) for x in edges],
        "minimum_rows_per_group_bin": int(min_bin_rows),
    }
    usable = True
    for name, frame in groups.items():
        out[name] = _shape_group(frame, edges, min_bin_rows)
        usable = usable and bool(out[name]["usable"])
    if not usable:
        out["usable"] = False
        out["S2_continuous_shape_supported"] = False
        return out

    train_ok = out["TRAIN"]["linear_trend"] < 0.0 and out["TRAIN"]["top20_slope"] < out["TRAIN"]["bottom20_slope"]
    val_ok = (
        out["VALIDATION"]["linear_trend"] < 0.0
        and out["VALIDATION"]["spearman"] <= -0.50
        and out["VALIDATION"]["top20_slope"] < out["VALIDATION"]["bottom20_slope"]
    )
    y2019_ok = out["2019"]["linear_trend"] < 0.0 and out["2019"]["top20_slope"] < out["2019"]["bottom20_slope"]
    y2020_ok = out["2020"]["linear_trend"] < 0.0 and out["2020"]["top20_slope"] < out["2020"]["bottom20_slope"]
    out["group_support"] = {"TRAIN": bool(train_ok), "VALIDATION": bool(val_ok), "2019": bool(y2019_ok), "2020": bool(y2020_ok)}
    out["usable"] = True
    out["S2_continuous_shape_supported"] = bool(train_ok and val_ok and y2019_ok and y2020_ok)
    return out


def adjudicate(s1: bool, s2: bool) -> str:
    if s1 and s2:
        return "R5_B1_specialist_stage1_stability_and_continuous_shape_supported"
    if s1 and not s2:
        return "R5_B1_specialist_stage1_time_stable_but_shape_weak"
    if not s1 and s2:
        return "R5_B1_specialist_stage1_shape_supported_but_time_stability_weak"
    return "R5_B1_specialist_stage1_not_robust_enough_for_transport"


def run(data_path: Path = r5.DATA_PATH) -> dict[str, Any]:
    train, validation, beta0, beta1 = cl008.build_B_frames(data_path)
    entry = cl008.reproduce_entry_gate(train, validation, beta0, beta1)
    base: dict[str, Any] = {
        "schema_id": "factorlab_R5_B1_specialist_stage1_stability_continuous_shape@1.0",
        "specialist_identity": "R5_B1_anti_persistence_interaction_specialist_v1",
        "stage_identity": "R5_B1_specialist_stage1_stability_continuous_shape_v1",
        "execution_scope": "reusable_TRAIN_VALIDATION_no_BLACKBOX_no_post2020_no_PnL",
        "source_identity": {
            "path": "data/development/5m_offset_0.parquet",
            "sha256": r5.DATA_SHA256,
            "rows_expected": r5.EXPECTED_ROWS,
            "symbol": r5.SYMBOL,
            "maximum_day": r5.MAX_DAY,
        },
        "entry_reproduction": entry,
        "BLACKBOX_read": False,
        "post_2020_rows_read": False,
        "PnL_read": False,
        "fresh_OOS_claim": False,
        "production_authority": False,
    }
    if not entry["pass"]:
        base["adjudication"] = "R5_B1_specialist_stage1_execution_drift_or_insufficient"
        return base

    s1 = evaluate_S1(train, validation, beta0, beta1)
    s2 = evaluate_S2(train, validation)
    base["S1"] = s1
    base["S2"] = s2
    if not s1["usable"] or not s2["usable"]:
        base["adjudication"] = "R5_B1_specialist_stage1_execution_drift_or_insufficient"
        return base
    base["adjudication"] = adjudicate(bool(s1["S1_time_stability_supported"]), bool(s2["S2_continuous_shape_supported"]))
    return base


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=r5.DATA_PATH)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
