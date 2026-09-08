#!/usr/bin/env python3
"""Execute the frozen R5 multiscale serial-dependence shallow screen.

TRAIN and VALIDATION are reusable research data. This runner never reads a
BLACKBOX partition, post-2020 data, trading PnL, or any two-wave outcome.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/development/5m_offset_0.parquet"
DATA_SHA256 = "bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48"
EXPECTED_ROWS = 70114
SYMBOL = "000852.SH"
MIN_DAY = "2015-01-05"
MAX_DAY = "2020-12-31"

VOL_WINDOW = 240
STATE_WINDOW = 960
SHORT_LAGS = (1, 2, 3)
LONG_LAGS = (12, 13, 14, 15, 16, 17, 18)
MIN_PAIRS_PER_LAG = 100
MIXED_MIN_TRAIN = 500
MIXED_MIN_VALIDATION = 200
SHOCK_QUANTILE = 0.80
C_MIN_TRAIN = 150
C_MIN_VALIDATION = 100


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def evidence_role(day: str) -> str | None:
    if "2015-01-05" <= day <= "2018-12-31":
        return "TRAIN"
    if "2019-01-01" <= day <= "2020-12-31":
        return "VALIDATION"
    return None


def load_native(path: Path = DATA_PATH) -> pd.DataFrame:
    actual_sha = sha256_file(path)
    if actual_sha != DATA_SHA256:
        raise RuntimeError(f"source SHA256 mismatch: {actual_sha}")
    frame = pd.read_parquet(
        path,
        columns=["symbol", "trading_day", "close", "bar_end_shanghai"],
    )
    if len(frame) != EXPECTED_ROWS:
        raise RuntimeError(f"source row mismatch: {len(frame)} != {EXPECTED_ROWS}")
    if set(frame["symbol"].astype(str)) != {SYMBOL}:
        raise RuntimeError("symbol identity mismatch")
    out = frame.copy()
    out["trading_day"] = out["trading_day"].astype(str)
    if out["trading_day"].min() < MIN_DAY or out["trading_day"].max() > MAX_DAY:
        raise RuntimeError("source escaped admitted TRAIN/VALIDATION interval")
    out["bar_end_shanghai"] = pd.to_datetime(out["bar_end_shanghai"], errors="raise")
    out["close"] = pd.to_numeric(out["close"], errors="raise").astype(float)
    if not np.isfinite(out["close"].to_numpy()).all() or bool((out["close"] <= 0.0).any()):
        raise RuntimeError("invalid close")
    out = out.sort_values("bar_end_shanghai", kind="stable").reset_index(drop=True)
    if out["bar_end_shanghai"].duplicated().any():
        raise RuntimeError("duplicate native timestamp")
    return out


def build_continuous_returns(native: pd.DataFrame) -> pd.DataFrame:
    """Create only exact same-day 5-minute close-to-close transitions."""
    time = native["bar_end_shanghai"]
    day = native["trading_day"].astype(str)
    exact = (day == day.shift(1)) & ((time - time.shift(1)) == pd.Timedelta(minutes=5))
    # A gap/session boundary starts a new segment. The boundary row itself has no return.
    segment_id = (~exact).cumsum().astype(int)
    log_close = np.log(native["close"].to_numpy(dtype=float))
    r = np.full(len(native), np.nan, dtype=float)
    idx = np.flatnonzero(exact.to_numpy())
    r[idx] = log_close[idx] - log_close[idx - 1]

    cols = native.loc[exact, ["trading_day", "bar_end_shanghai"]].copy()
    cols["r"] = r[exact.to_numpy()]
    cols["segment_id"] = segment_id.loc[exact].to_numpy(dtype=int)
    cols["segment_pos"] = cols.groupby("segment_id", sort=False).cumcount().astype(int)
    cols["year"] = cols["trading_day"].str.slice(0, 4).astype(int)
    cols["role"] = cols["trading_day"].map(evidence_role)
    if cols["role"].isna().any():
        raise RuntimeError("return row outside TRAIN/VALIDATION role")
    return cols.reset_index(drop=True)


def add_causal_normalization(returns: pd.DataFrame) -> pd.DataFrame:
    out = returns.copy()
    r = out["r"].astype(float)
    sigma = np.sqrt(r.pow(2).rolling(VOL_WINDOW, min_periods=VOL_WINDOW).mean().shift(1))
    sigma = sigma.where(np.isfinite(sigma) & (sigma > 0.0))
    out["sigma_past"] = sigma
    out["z"] = r / sigma
    return out


def _lag_rho_from_past(
    z: pd.Series,
    segment: pd.Series,
    lag: int,
    denominator: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    lag_z = z.shift(lag)
    same_segment = segment.eq(segment.shift(lag))
    pair = (z * lag_z).where(same_segment & z.notna() & lag_z.notna())
    past_pair = pair.shift(1)
    rolling = past_pair.rolling(STATE_WINDOW, min_periods=1)
    count = rolling.count()
    mean = rolling.mean()
    rho = (mean / denominator).where((count >= MIN_PAIRS_PER_LAG) & denominator.notna() & (denominator > 0.0))
    return rho, count


def add_memory_state(normalized: pd.DataFrame) -> pd.DataFrame:
    out = normalized.copy()
    z = out["z"].astype(float)
    segment = out["segment_id"]
    denominator = z.pow(2).shift(1).rolling(STATE_WINDOW, min_periods=STATE_WINDOW).mean()
    rho_columns: dict[int, pd.Series] = {}
    count_columns: dict[int, pd.Series] = {}
    for lag in SHORT_LAGS + LONG_LAGS:
        rho, count = _lag_rho_from_past(z, segment, lag, denominator)
        rho_columns[lag] = rho
        count_columns[lag] = count
        out[f"rho_{lag}"] = rho
        out[f"rho_{lag}_pair_count"] = count

    short_frame = pd.concat([rho_columns[k] for k in SHORT_LAGS], axis=1)
    long_frame = pd.concat([rho_columns[k] for k in LONG_LAGS], axis=1)
    short_available = short_frame.notna().all(axis=1)
    long_available = long_frame.notna().all(axis=1)
    out["short_memory"] = short_frame.mean(axis=1).where(short_available)
    out["long_memory"] = long_frame.mean(axis=1).where(long_available)
    out["anti_persistence"] = -out["short_memory"]
    out["state_available"] = out["short_memory"].notna() & out["long_memory"].notna()
    out["mixed_state"] = out["state_available"] & (out["short_memory"] < 0.0) & (out["long_memory"] > 0.0)
    return out


def _summary(values: Iterable[float]) -> dict[str, Any]:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return {"n": 0, "mean": None, "median": None, "p10": None, "p90": None}
    return {
        "n": int(len(arr)),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p10": float(np.quantile(arr, 0.10)),
        "p90": float(np.quantile(arr, 0.90)),
    }


def _run_lengths(mask: np.ndarray, segment: np.ndarray) -> list[int]:
    runs: list[int] = []
    current = 0
    previous_segment: int | None = None
    for flag, seg in zip(mask.astype(bool), segment.astype(int), strict=True):
        if flag and current > 0 and previous_segment == int(seg):
            current += 1
        elif flag:
            if current > 0:
                runs.append(current)
            current = 1
        else:
            if current > 0:
                runs.append(current)
            current = 0
        previous_segment = int(seg)
    if current > 0:
        runs.append(current)
    return runs


def evaluate_R5_A(state: pd.DataFrame) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for role in ("TRAIN", "VALIDATION"):
        sub = state.loc[state["role"] == role].copy()
        available = sub.loc[sub["state_available"]]
        mixed = available["mixed_state"].to_numpy(dtype=bool)
        runs = _run_lengths(mixed, available["segment_id"].to_numpy(dtype=int)) if len(available) else []
        payload[role] = {
            "state_available": int(len(available)),
            "mixed_state": int(np.sum(mixed)),
            "mixed_fraction": float(np.mean(mixed)) if len(mixed) else None,
            "short_memory": _summary(available["short_memory"]),
            "long_memory": _summary(available["long_memory"]),
            "short_negative_fraction": float(np.mean(available["short_memory"].to_numpy() < 0.0)) if len(available) else None,
            "long_positive_fraction": float(np.mean(available["long_memory"].to_numpy() > 0.0)) if len(available) else None,
            "mixed_run_lengths": _summary(runs),
        }
    supply_pass = (
        payload["TRAIN"]["mixed_state"] >= MIXED_MIN_TRAIN
        and payload["VALIDATION"]["mixed_state"] >= MIXED_MIN_VALIDATION
    )
    payload["supply_pass"] = bool(supply_pass)
    payload["minimums"] = {"TRAIN": MIXED_MIN_TRAIN, "VALIDATION": MIXED_MIN_VALIDATION}
    return payload


def _fit_ols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    if X.ndim != 2 or y.ndim != 1 or len(X) != len(y) or len(y) <= X.shape[1]:
        raise RuntimeError("insufficient or invalid OLS design")
    if not np.isfinite(X).all() or not np.isfinite(y).all():
        raise RuntimeError("non-finite OLS input")
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta.astype(float)


def _predict(X: np.ndarray, beta: np.ndarray) -> np.ndarray:
    return np.asarray(X, dtype=float) @ np.asarray(beta, dtype=float)


def _metrics(y: np.ndarray, pred: np.ndarray) -> dict[str, Any]:
    y = np.asarray(y, dtype=float)
    pred = np.asarray(pred, dtype=float)
    mse = float(np.mean((y - pred) ** 2))
    if len(y) >= 2 and np.std(y) > 0.0 and np.std(pred) > 0.0:
        corr = float(np.corrcoef(y, pred)[0, 1])
    else:
        corr = None
    return {"n": int(len(y)), "MSE": mse, "prediction_correlation": corr}


def _design_B(frame: pd.DataFrame, candidate: str) -> tuple[np.ndarray, np.ndarray]:
    z = frame["z"].to_numpy(dtype=float)
    anti = frame["anti_persistence"].to_numpy(dtype=float)
    long = frame["long_memory"].to_numpy(dtype=float)
    if candidate == "B0":
        X = np.column_stack([np.ones(len(frame)), z])
    elif candidate == "B1":
        X = np.column_stack([np.ones(len(frame)), z, z * anti])
    elif candidate == "B2":
        X = np.column_stack([np.ones(len(frame)), z, z * anti, z * long, z * anti * long])
    else:
        raise ValueError(candidate)
    return X, frame["next_z"].to_numpy(dtype=float)


def _year_metrics(frame: pd.DataFrame, pred: np.ndarray) -> dict[str, Any]:
    out: dict[str, Any] = {}
    y = frame["next_z"].to_numpy(dtype=float)
    years = frame["year"].to_numpy(dtype=int)
    for year in (2019, 2020):
        mask = years == year
        if np.any(mask):
            out[str(year)] = _metrics(y[mask], pred[mask])
    return out


def evaluate_R5_B(state: pd.DataFrame) -> dict[str, Any]:
    frame = state.copy()
    frame["next_z"] = frame["z"].shift(-1)
    same_next_segment = frame["segment_id"].eq(frame["segment_id"].shift(-1))
    valid = frame["state_available"] & frame["z"].notna() & frame["next_z"].notna() & same_next_segment
    frame = frame.loc[valid].copy()
    train = frame.loc[frame["role"] == "TRAIN"].copy()
    val = frame.loc[frame["role"] == "VALIDATION"].copy()
    if len(train) < 20 or len(val) < 20:
        return {"status": "insufficient_prediction_rows", "TRAIN": int(len(train)), "VALIDATION": int(len(val)), "B1_supported": false}

    result: dict[str, Any] = {"TRAIN_rows": int(len(train)), "VALIDATION_rows": int(len(val))}
    fitted: dict[str, np.ndarray] = {}
    for candidate in ("B0", "B1"):
        X_train, y_train = _design_B(train, candidate)
        X_val, y_val = _design_B(val, candidate)
        beta = _fit_ols(X_train, y_train)
        fitted[candidate] = beta
        train_pred = _predict(X_train, beta)
        val_pred = _predict(X_val, beta)
        result[candidate] = {
            "TRAIN_coefficients": [float(x) for x in beta],
            "TRAIN_metrics": _metrics(y_train, train_pred),
            "VALIDATION_metrics": _metrics(y_val, val_pred),
            "VALIDATION_by_year": _year_metrics(val, val_pred),
        }

    b1_supported = (
        result["B1"]["VALIDATION_metrics"]["MSE"] < result["B0"]["VALIDATION_metrics"]["MSE"]
        and float(fitted["B1"][2]) < 0.0
    )
    result["B1_supported"] = bool(b1_supported)

    if b1_supported:
        X_train, y_train = _design_B(train, "B2")
        X_val, y_val = _design_B(val, "B2")
        beta = _fit_ols(X_train, y_train)
        train_pred = _predict(X_train, beta)
        val_pred = _predict(X_val, beta)
        result["B2"] = {
            "status": "computed_only_because_B1_supported",
            "TRAIN_coefficients": [float(x) for x in beta],
            "TRAIN_metrics": _metrics(y_train, train_pred),
            "VALIDATION_metrics": _metrics(y_val, val_pred),
            "VALIDATION_by_year": _year_metrics(val, val_pred),
        }
    else:
        result["B2"] = {"status": "not_computed_B1_failed_core_gate"}
    return result


def add_parent_and_recovery(state: pd.DataFrame) -> pd.DataFrame:
    out = state.copy()
    parent = out.groupby("segment_id", sort=False)["z"].transform(
        lambda s: s.rolling(12, min_periods=12).sum().shift(1)
    )
    future = out.groupby("segment_id", sort=False)["z"].transform(
        lambda s: s.shift(-1) + s.shift(-2) + s.shift(-3)
    )
    out["parent_drift_12"] = parent
    out["future_3_z_sum"] = future
    parent_sign = np.sign(parent.to_numpy(dtype=float))
    out["recovery_15m"] = parent_sign * future.to_numpy(dtype=float)
    return out


def _design_C(frame: pd.DataFrame, candidate: str) -> tuple[np.ndarray, np.ndarray]:
    severity = np.abs(frame["z"].to_numpy(dtype=float))
    if candidate == "C0":
        X = np.column_stack([np.ones(len(frame)), severity])
    elif candidate == "C1":
        X = np.column_stack(
            [
                np.ones(len(frame)),
                severity,
                frame["long_memory"].to_numpy(dtype=float),
                frame["anti_persistence"].to_numpy(dtype=float),
            ]
        )
    else:
        raise ValueError(candidate)
    return X, frame["recovery_15m"].to_numpy(dtype=float)


def _year_metrics_C(frame: pd.DataFrame, pred: np.ndarray) -> dict[str, Any]:
    out: dict[str, Any] = {}
    y = frame["recovery_15m"].to_numpy(dtype=float)
    years = frame["year"].to_numpy(dtype=int)
    for year in (2019, 2020):
        mask = years == year
        if np.any(mask):
            out[str(year)] = _metrics(y[mask], pred[mask])
    return out


def _event_descriptive(frame: pd.DataFrame) -> dict[str, Any]:
    if len(frame) == 0:
        return {"n": 0, "mean_recovery": None, "positive_recovery_fraction": None}
    y = frame["recovery_15m"].to_numpy(dtype=float)
    return {
        "n": int(len(frame)),
        "mean_recovery": float(np.mean(y)),
        "positive_recovery_fraction": float(np.mean(y > 0.0)),
    }


def evaluate_R5_C(state: pd.DataFrame) -> dict[str, Any]:
    frame = add_parent_and_recovery(state)
    train_z = np.abs(frame.loc[(frame["role"] == "TRAIN") & frame["z"].notna(), "z"].to_numpy(dtype=float))
    if len(train_z) == 0:
        return {"status": "no_TRAIN_z", "C1_supported": false}
    q80 = float(np.quantile(train_z, SHOCK_QUANTILE))
    parent = frame["parent_drift_12"].to_numpy(dtype=float)
    z = frame["z"].to_numpy(dtype=float)
    event = (
        frame["state_available"].to_numpy(dtype=bool)
        & np.isfinite(parent)
        & (parent != 0.0)
        & np.isfinite(z)
        & (np.abs(z) >= q80)
        & (np.sign(z) == -np.sign(parent))
    )
    triggers = frame.loc[event].copy()
    resolved = triggers.loc[np.isfinite(triggers["recovery_15m"].to_numpy(dtype=float))].copy()
    train = resolved.loc[resolved["role"] == "TRAIN"].copy()
    val = resolved.loc[resolved["role"] == "VALIDATION"].copy()

    supply_pass = len(train) >= C_MIN_TRAIN and len(val) >= C_MIN_VALIDATION
    result: dict[str, Any] = {
        "TRAIN_q80_abs_z": q80,
        "trigger_counts": {
            "TRAIN": int(np.sum(triggers["role"] == "TRAIN")),
            "VALIDATION": int(np.sum(triggers["role"] == "VALIDATION")),
            "2019": int(np.sum(triggers["year"] == 2019)),
            "2020": int(np.sum(triggers["year"] == 2020)),
        },
        "resolved_counts": {
            "TRAIN": int(len(train)),
            "VALIDATION": int(len(val)),
            "2019": int(np.sum(val["year"] == 2019)),
            "2020": int(np.sum(val["year"] == 2020)),
        },
        "minimums": {"TRAIN": C_MIN_TRAIN, "VALIDATION": C_MIN_VALIDATION},
        "supply_pass": bool(supply_pass),
        "descriptive": {
            "TRAIN": _event_descriptive(train),
            "VALIDATION": _event_descriptive(val),
            "2019": _event_descriptive(val.loc[val["year"] == 2019]),
            "2020": _event_descriptive(val.loc[val["year"] == 2020]),
        },
    }
    if not supply_pass:
        result["status"] = "resolved_event_supply_insufficient"
        result["C1_supported"] = False
        return result

    fitted: dict[str, np.ndarray] = {}
    for candidate in ("C0", "C1"):
        X_train, y_train = _design_C(train, candidate)
        X_val, y_val = _design_C(val, candidate)
        beta = _fit_ols(X_train, y_train)
        fitted[candidate] = beta
        train_pred = _predict(X_train, beta)
        val_pred = _predict(X_val, beta)
        result[candidate] = {
            "TRAIN_coefficients": [float(x) for x in beta],
            "TRAIN_metrics": _metrics(y_train, train_pred),
            "VALIDATION_metrics": _metrics(y_val, val_pred),
            "VALIDATION_by_year": _year_metrics_C(val, val_pred),
        }

    c1_supported = (
        result["C1"]["VALIDATION_metrics"]["MSE"] < result["C0"]["VALIDATION_metrics"]["MSE"]
        and float(fitted["C1"][2]) > 0.0
        and float(fitted["C1"][3]) > 0.0
    )
    result["C1_supported"] = bool(c1_supported)
    result["status"] = "evaluated"
    return result


def run(path: Path = DATA_PATH) -> dict[str, Any]:
    native = load_native(path)
    returns = build_continuous_returns(native)
    normalized = add_causal_normalization(returns)
    state = add_memory_state(normalized)
    A = evaluate_R5_A(state)

    result: dict[str, Any] = {
        "schema_id": "factorlab_broad_rmr_R5_multiscale_serial_dependence_receipt@1.0",
        "research_identity": "R5_multiscale_serial_dependence_state_v1",
        "execution_scope": "reusable_TRAIN_VALIDATION_only_no_BLACKBOX_no_PnL",
        "source_identity": {
            "path": str(path),
            "sha256": sha256_file(path),
            "rows": int(len(native)),
            "symbol": SYMBOL,
            "minimum_day": str(native["trading_day"].min()),
            "maximum_day": str(native["trading_day"].max()),
        },
        "construction": {
            "continuous_return_rows": int(len(returns)),
            "volatility_window": VOL_WINDOW,
            "state_window": STATE_WINDOW,
            "short_lags": list(SHORT_LAGS),
            "long_lags": list(LONG_LAGS),
            "minimum_pairs_each_lag": MIN_PAIRS_PER_LAG,
            "cross_session_or_gap_return_fill": False,
        },
        "R5_A": A,
        "BLACKBOX_read": False,
        "post_2020_rows_read": False,
        "PnL_read": False,
        "fresh_OOS_claim": False,
        "production_authority": False,
    }

    if not A["supply_pass"]:
        result["R5_B"] = {"status": "not_executed_R5_A_supply_failed"}
        result["R5_C"] = {"status": "not_executed_R5_A_supply_failed"}
        result["adjudication"] = "R5_state_supply_insufficient"
        return result

    B = evaluate_R5_B(state)
    C = evaluate_R5_C(state)
    result["R5_B"] = B
    result["R5_C"] = C
    b = bool(B.get("B1_supported", False))
    c = bool(C.get("C1_supported", False))
    if b and c:
        adjudication = "R5_multiscale_serial_dependence_supported_for_deeper_validation"
    elif b or c:
        adjudication = "R5_partial_support_keep_researching_on_TRAIN_VALIDATION"
    else:
        adjudication = "R5_low_capacity_mechanisms_not_supported"
    result["adjudication"] = adjudication
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DATA_PATH)
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
