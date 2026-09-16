#!/usr/bin/env python3
"""Frozen R7 native-1m rejected-excursion broad shallow screen.

Uses official 1m paths anchored on official 5m endpoints. No resampling,
BLACKBOX, post-2020, PnL, M0 structure cache, or R5-B1 features.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ONE_MIN_PATH = ROOT / "data" / "development" / "1m_official.parquet"
FIVE_MIN_PATH = ROOT / "data" / "development" / "5m_offset_0.parquet"
ONE_MIN_SHA = "755217afce9dec383e48cd46d591402fa90dc50897abeb3dc7097c9a18a109d4"
FIVE_MIN_SHA = "bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48"
ONE_MIN_ROWS = 350561
FIVE_MIN_ROWS = 70114
SYMBOL = "000852.SH"
MIN_DAY = "2015-01-05"
MAX_DAY = "2020-12-31"
VOL_WINDOW = 240
PATH_RETURNS = 5
FORWARD_RETURNS = 5
SQRT5 = math.sqrt(5.0)

SUPPLY_DEFAULTS = {
    "train_candidates": 30000,
    "validation_candidates": 15000,
    "year_candidates": 7000,
    "train_positive": 2000,
    "train_negative": 2000,
    "validation_positive": 1000,
    "validation_negative": 1000,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def evidence_role(day: str) -> str | None:
    if "2015-01-05" <= day <= "2018-12-31":
        return "TRAIN"
    if "2019-01-01" <= day <= "2020-12-31":
        return "VALIDATION"
    return None


def _load(path: Path, expected_sha: str, expected_rows: int) -> pd.DataFrame:
    actual_sha = sha256_file(path)
    if actual_sha != expected_sha:
        raise RuntimeError(f"source SHA mismatch for {path}: {actual_sha}")
    x = pd.read_parquet(path, columns=["symbol", "trading_day", "bar_end_shanghai", "close"])
    if len(x) != expected_rows:
        raise RuntimeError(f"source row mismatch for {path}: {len(x)}")
    if set(x["symbol"].astype(str)) != {SYMBOL}:
        raise RuntimeError(f"symbol mismatch for {path}")
    x = x.copy()
    x["trading_day"] = x["trading_day"].astype(str)
    if x["trading_day"].min() < MIN_DAY or x["trading_day"].max() > MAX_DAY:
        raise RuntimeError("source escaped admitted TRAIN/VALIDATION date range")
    x["bar_end_shanghai"] = pd.to_datetime(x["bar_end_shanghai"], errors="raise")
    x["close"] = pd.to_numeric(x["close"], errors="raise").astype(float)
    if not np.isfinite(x["close"].to_numpy()).all() or bool((x["close"] <= 0.0).any()):
        raise RuntimeError("invalid close")
    x = x.sort_values("bar_end_shanghai", kind="stable").reset_index(drop=True)
    if x["bar_end_shanghai"].duplicated().any():
        raise RuntimeError("duplicate timestamp")
    return x


def path_features(log_prices_6: np.ndarray, sigma_past: float) -> tuple[float, float, float, int]:
    """Return endpoint_z, rejection_signed_z, extreme displacement, extreme k (1..5)."""
    p = np.asarray(log_prices_6, dtype=float)
    if p.shape != (6,):
        raise ValueError("path must contain exactly 6 log closes / 5 returns")
    if not np.isfinite(sigma_past) or sigma_past <= 0.0:
        raise ValueError("sigma_past must be finite and positive")
    d = p[1:] - p[0]
    j = int(np.argmax(np.abs(d)))  # earliest tie by numpy definition
    e = float(d[j])
    endpoint = float(d[-1])
    denom = float(sigma_past * SQRT5)
    endpoint_z = endpoint / denom
    if e == 0.0:
        rejection = 0.0
    else:
        s = 1.0 if e > 0.0 else -1.0
        rejection = s * (abs(e) - s * endpoint) / denom
    return float(endpoint_z), float(rejection), e, j + 1


def build_candidates(one_min_path: Path = ONE_MIN_PATH, five_min_path: Path = FIVE_MIN_PATH) -> pd.DataFrame:
    one = _load(one_min_path, ONE_MIN_SHA, ONE_MIN_ROWS)
    five = _load(five_min_path, FIVE_MIN_SHA, FIVE_MIN_ROWS)

    ts = one["bar_end_shanghai"]
    day = one["trading_day"]
    exact = day.eq(day.shift(1)) & ((ts - ts.shift(1)) == pd.Timedelta(minutes=1))
    segment_id = (~exact).cumsum().to_numpy(dtype=int)
    log_close = np.log(one["close"].to_numpy(dtype=float))

    exact_idx = np.flatnonzero(exact.to_numpy())
    exact_r = log_close[exact_idx] - log_close[exact_idx - 1]
    sigma_exact = np.sqrt(pd.Series(exact_r).pow(2).rolling(VOL_WINDOW, min_periods=VOL_WINDOW).mean().shift(1)).to_numpy(dtype=float)
    sigma_by_row = np.full(len(one), np.nan, dtype=float)
    sigma_by_row[exact_idx] = sigma_exact

    official = set(pd.to_datetime(five["bar_end_shanghai"], errors="raise").tolist())
    one_times = one["bar_end_shanghai"].tolist()
    one_days = one["trading_day"].tolist()
    rows: list[dict[str, Any]] = []

    for i in range(PATH_RETURNS, len(one) - FORWARD_RETURNS):
        t = one_times[i]
        if t not in official:
            continue
        if (t - pd.Timedelta(minutes=5)) not in official or (t + pd.Timedelta(minutes=5)) not in official:
            continue
        if segment_id[i - PATH_RETURNS] != segment_id[i + FORWARD_RETURNS]:
            continue
        sigma = float(sigma_by_row[i])
        if not np.isfinite(sigma) or sigma <= 0.0:
            continue
        day_i = str(one_days[i])
        role = evidence_role(day_i)
        if role is None:
            raise RuntimeError("candidate escaped admitted TRAIN/VALIDATION date range")

        endpoint_z, rejection_z, extreme_disp, extreme_k = path_features(log_close[i - PATH_RETURNS : i + 1], sigma)
        next5_z = float((log_close[i + FORWARD_RETURNS] - log_close[i]) / (sigma * SQRT5))
        rows.append(
            {
                "trading_day": day_i,
                "year": int(day_i[:4]),
                "bar_end_shanghai": str(t),
                "role": role,
                "endpoint_z": endpoint_z,
                "rejection_signed_z": rejection_z,
                "next5_z": next5_z,
                "extreme_signed_log_displacement": extreme_disp,
                "extreme_k": int(extreme_k),
            }
        )
    return pd.DataFrame(rows)


def _design(frame: pd.DataFrame, model: str) -> tuple[np.ndarray, np.ndarray]:
    y = frame["next5_z"].to_numpy(dtype=float)
    endpoint = frame["endpoint_z"].to_numpy(dtype=float)
    if model == "B0":
        X = np.column_stack([np.ones(len(frame)), endpoint])
    elif model == "B1":
        rejection = frame["rejection_signed_z"].to_numpy(dtype=float)
        X = np.column_stack([np.ones(len(frame)), endpoint, rejection])
    else:
        raise ValueError(model)
    return X, y


def _fit(frame: pd.DataFrame, model: str) -> np.ndarray:
    X, y = _design(frame, model)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta.astype(float)


def _predict(frame: pd.DataFrame, model: str, beta: np.ndarray) -> np.ndarray:
    X, _ = _design(frame, model)
    return X @ np.asarray(beta, dtype=float)


def _mse(frame: pd.DataFrame, model: str, beta: np.ndarray) -> float:
    _, y = _design(frame, model)
    pred = _predict(frame, model, beta)
    return float(np.mean((y - pred) ** 2))


def _local_summary(frame: pd.DataFrame) -> dict[str, Any]:
    beta = _fit(frame, "B1")
    return {
        "n": int(len(frame)),
        "B1_beta": [float(x) for x in beta],
        "rejection_coefficient": float(beta[2]),
        "positive_rejection_n": int((frame["rejection_signed_z"] > 0.0).sum()),
        "negative_rejection_n": int((frame["rejection_signed_z"] < 0.0).sum()),
        "zero_rejection_n": int((frame["rejection_signed_z"] == 0.0).sum()),
    }


def evaluate(candidates: pd.DataFrame, supply_thresholds: dict[str, int] | None = None) -> dict[str, Any]:
    req = dict(SUPPLY_DEFAULTS if supply_thresholds is None else supply_thresholds)
    train = candidates.loc[candidates["role"] == "TRAIN"].copy()
    val = candidates.loc[candidates["role"] == "VALIDATION"].copy()
    y2019 = val.loc[val["year"] == 2019].copy()
    y2020 = val.loc[val["year"] == 2020].copy()
    if min(len(train), len(val), len(y2019), len(y2020)) == 0:
        return {"adjudication": "R7_execution_drift_or_insufficient", "reason": "empty required role/year"}

    local = {
        "TRAIN": _local_summary(train),
        "VALIDATION": _local_summary(val),
        "2019": _local_summary(y2019),
        "2020": _local_summary(y2020),
    }
    supply = (
        len(train) >= req["train_candidates"]
        and len(val) >= req["validation_candidates"]
        and len(y2019) >= req["year_candidates"]
        and len(y2020) >= req["year_candidates"]
        and local["TRAIN"]["positive_rejection_n"] >= req["train_positive"]
        and local["TRAIN"]["negative_rejection_n"] >= req["train_negative"]
        and local["VALIDATION"]["positive_rejection_n"] >= req["validation_positive"]
        and local["VALIDATION"]["negative_rejection_n"] >= req["validation_negative"]
    )

    beta0 = _fit(train, "B0")
    beta1 = _fit(train, "B1")
    fixed: dict[str, Any] = {}
    for name, frame in (("VALIDATION", val), ("2019", y2019), ("2020", y2020)):
        mse0 = _mse(frame, "B0", beta0)
        mse1 = _mse(frame, "B1", beta1)
        fixed[name] = {
            "MSE_B0": mse0,
            "MSE_B1": mse1,
            "improvement": float(mse0 - mse1),
            "relative_improvement": float((mse0 - mse1) / mse0) if mse0 > 0.0 else None,
        }

    _, y_val = _design(val, "B0")
    residual = y_val - _predict(val, "B0", beta0)
    rz = val["rejection_signed_z"].to_numpy(dtype=float)
    pos = rz > 0.0
    neg = rz < 0.0
    symmetry = {
        "positive_rejection_n": int(pos.sum()),
        "positive_rejection_mean_B0_residual": float(np.mean(residual[pos])) if pos.any() else None,
        "negative_rejection_n": int(neg.sum()),
        "negative_rejection_mean_B0_residual": float(np.mean(residual[neg])) if neg.any() else None,
    }

    coefficient_direction = all(local[g]["rejection_coefficient"] < 0.0 for g in ("TRAIN", "VALIDATION", "2019", "2020"))
    fixed_prediction = all(fixed[g]["improvement"] > 0.0 for g in ("VALIDATION", "2019", "2020"))
    directional_symmetry = (
        symmetry["positive_rejection_mean_B0_residual"] is not None
        and symmetry["negative_rejection_mean_B0_residual"] is not None
        and symmetry["positive_rejection_mean_B0_residual"] < 0.0
        and symmetry["negative_rejection_mean_B0_residual"] > 0.0
    )

    if not supply:
        adjudication = "R7_supply_insufficient"
    elif not coefficient_direction:
        adjudication = "R7_coefficient_direction_not_supported"
    elif not fixed_prediction:
        adjudication = "R7_fixed_prediction_not_supported"
    elif not directional_symmetry:
        adjudication = "R7_directional_symmetry_not_supported"
    else:
        adjudication = "R7_supported_for_one_bounded_diagnostic"

    return {
        "supply_thresholds": req,
        "supply_supported": bool(supply),
        "local_coefficients": local,
        "TRAIN_fixed_beta": {
            "B0": [float(x) for x in beta0],
            "B1": [float(x) for x in beta1],
        },
        "coefficient_direction_supported": bool(coefficient_direction),
        "fixed_prediction": fixed,
        "fixed_prediction_supported": bool(fixed_prediction),
        "directional_symmetry": symmetry,
        "directional_symmetry_supported": bool(directional_symmetry),
        "adjudication": adjudication,
    }


def run(one_min_path: Path = ONE_MIN_PATH, five_min_path: Path = FIVE_MIN_PATH) -> dict[str, Any]:
    candidates = build_candidates(one_min_path, five_min_path)
    result = evaluate(candidates)
    return {
        "schema_id": "factorlab_R7_native_1m_rejected_excursion_receipt@1.0",
        "identity": "R7_native_1m_rejected_excursion_v1",
        "sources": {
            "one_min": {"path":"data/development/1m_official.parquet","sha256":ONE_MIN_SHA,"rows":ONE_MIN_ROWS,"symbol":SYMBOL,"max_day":MAX_DAY},
            "five_min_reference": {"path":"data/development/5m_offset_0.parquet","sha256":FIVE_MIN_SHA,"rows":FIVE_MIN_ROWS,"symbol":SYMBOL,"max_day":MAX_DAY},
        },
        "construction": {
            "official_5m_endpoint_anchor": True,
            "native_path_returns": PATH_RETURNS,
            "native_forward_returns": FORWARD_RETURNS,
            "sigma_window_exact_1m_returns": VOL_WINDOW,
            "local_resampling_performed": False,
            "M0_structure_cache_read": False,
            "B1_feature_read": False,
        },
        "candidate_rows": int(len(candidates)),
        **result,
        "BLACKBOX_read": False,
        "post_2020_rows_read": False,
        "PnL_read": False,
        "fresh_OOS_claim": False,
        "production_authority": False,
    }


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
