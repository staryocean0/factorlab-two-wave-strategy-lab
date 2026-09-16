#!/usr/bin/env python3
"""Frozen broad shallow R6 close-boundary rejection screen."""

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
PARENT = ROOT / "scripts" / "run_broad_rmr_R5_multiscale_serial_dependence.py"
SPEC = importlib.util.spec_from_file_location("r5_parent_for_r6", PARENT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load R5 parent utilities")
r5 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = r5
SPEC.loader.exec_module(r5)

LOOKBACK = 12
HORIZON = 3
SQRT_H = math.sqrt(HORIZON)


def classify_breakout_failure(prior: np.ndarray, close_t0: float, close_t1: float) -> tuple[int, bool] | None:
    prior = np.asarray(prior, dtype=float)
    if len(prior) != LOOKBACK:
        raise ValueError("prior must have exactly 12 closes")
    upper = float(np.max(prior))
    lower = float(np.min(prior))
    if close_t0 > upper:
        return 1, bool(close_t1 <= upper)
    if close_t0 < lower:
        return -1, bool(close_t1 >= lower)
    return None


def build_events(data_path: Path = r5.DATA_PATH) -> pd.DataFrame:
    native = r5.load_native(data_path)
    returns = r5.build_continuous_returns(native)
    normalized = r5.add_causal_normalization(returns)
    sigma_map = normalized.set_index("bar_end_shanghai")["sigma_past"]

    out = native.copy()
    same_prev = (
        out["trading_day"].eq(out["trading_day"].shift(1))
        & ((out["bar_end_shanghai"] - out["bar_end_shanghai"].shift(1)) == pd.Timedelta(minutes=5))
    )
    out["segment_id"] = (~same_prev).cumsum().astype(int)
    close = out["close"].to_numpy(dtype=float)
    log_close = np.log(close)
    seg = out["segment_id"].to_numpy(dtype=int)
    rows: list[dict[str, Any]] = []

    for i in range(LOOKBACK + 1, len(out) - HORIZON):
        # i=t1, i-1=t0, prior closes are i-13..i-2 inclusive (12 bars).
        if seg[i - (LOOKBACK + 1)] != seg[i + HORIZON]:
            continue
        prior = close[i - (LOOKBACK + 1) : i - 1]
        cls = classify_breakout_failure(prior, close[i - 1], close[i])
        if cls is None:
            continue
        sigma = float(sigma_map.get(out.iloc[i]["bar_end_shanghai"], np.nan))
        if not np.isfinite(sigma) or sigma <= 0.0:
            continue
        direction, failed = cls
        forward = direction * (log_close[i + HORIZON] - log_close[i]) / (sigma * SQRT_H)
        day = str(out.iloc[i]["trading_day"])
        role = r5.evidence_role(day)
        if role is None:
            raise RuntimeError("event escaped TRAIN/VALIDATION")
        rows.append(
            {
                "trading_day": day,
                "year": int(day[:4]),
                "bar_end_shanghai": str(out.iloc[i]["bar_end_shanghai"]),
                "role": role,
                "direction": int(direction),
                "failed": bool(failed),
                "signed_forward_z3": float(forward),
            }
        )
    return pd.DataFrame(rows)


def summarize(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"failed_n": 0, "control_n": 0, "usable": False}
    f = frame.loc[frame["failed"]]
    c = frame.loc[~frame["failed"]]
    result: dict[str, Any] = {"failed_n": int(len(f)), "control_n": int(len(c))}
    if len(f) == 0 or len(c) == 0:
        result["usable"] = False
        return result
    fm = float(f["signed_forward_z3"].mean())
    cm = float(c["signed_forward_z3"].mean())
    fr = float((f["signed_forward_z3"] < 0.0).mean())
    cr = float((c["signed_forward_z3"] < 0.0).mean())
    result.update(
        {
            "usable": True,
            "failed_mean": fm,
            "control_mean": cm,
            "mean_effect": fm - cm,
            "failed_median": float(f["signed_forward_z3"].median()),
            "control_median": float(c["signed_forward_z3"].median()),
            "failed_reversal_fraction": fr,
            "control_reversal_fraction": cr,
            "reversal_fraction_delta": fr - cr,
        }
    )
    return result


def evaluate(events: pd.DataFrame) -> dict[str, Any]:
    train = events.loc[events["role"] == "TRAIN"].copy()
    val = events.loc[events["role"] == "VALIDATION"].copy()
    groups = {
        "TRAIN": summarize(train),
        "VALIDATION": summarize(val),
        "2019": summarize(val.loc[val["year"] == 2019]),
        "2020": summarize(val.loc[val["year"] == 2020]),
        "VALIDATION_upper": summarize(val.loc[val["direction"] == 1]),
        "VALIDATION_lower": summarize(val.loc[val["direction"] == -1]),
    }

    supply = (
        groups["TRAIN"]["failed_n"] >= 100
        and groups["TRAIN"]["control_n"] >= 200
        and groups["VALIDATION"]["failed_n"] >= 50
        and groups["VALIDATION"]["control_n"] >= 100
        and groups["2019"]["failed_n"] >= 20
        and groups["2019"]["control_n"] >= 40
        and groups["2020"]["failed_n"] >= 20
        and groups["2020"]["control_n"] >= 40
        and groups["VALIDATION_upper"]["failed_n"] >= 20
        and groups["VALIDATION_upper"]["control_n"] >= 40
        and groups["VALIDATION_lower"]["failed_n"] >= 20
        and groups["VALIDATION_lower"]["control_n"] >= 40
    )
    if not all(g.get("usable", False) for g in groups.values()):
        direction = False
    else:
        direction = (
            groups["TRAIN"]["mean_effect"] < 0.0
            and groups["TRAIN"]["reversal_fraction_delta"] > 0.0
            and groups["VALIDATION"]["mean_effect"] < 0.0
            and groups["VALIDATION"]["reversal_fraction_delta"] > 0.0
            and groups["2019"]["mean_effect"] < 0.0
            and groups["2020"]["mean_effect"] < 0.0
            and groups["VALIDATION_upper"]["mean_effect"] < 0.0
            and groups["VALIDATION_lower"]["mean_effect"] < 0.0
        )
    if not supply:
        adjudication = "R6_supply_insufficient"
    elif not direction:
        adjudication = "R6_direction_not_supported"
    else:
        adjudication = "R6_supported_for_one_bounded_diagnostic"
    return {
        "groups": groups,
        "supply_supported": bool(supply),
        "direction_supported": bool(direction),
        "adjudication": adjudication,
    }


def run(data_path: Path = r5.DATA_PATH) -> dict[str, Any]:
    events = build_events(data_path)
    ev = evaluate(events)
    return {
        "schema_id": "factorlab_R6_close_boundary_rejection_receipt@1.0",
        "identity": "R6_close_boundary_rejection_v1",
        "source": {
            "path": "data/development/5m_offset_0.parquet",
            "sha256": r5.DATA_SHA256,
            "rows": r5.EXPECTED_ROWS,
            "symbol": r5.SYMBOL,
            "max_day": r5.MAX_DAY,
            "post_2020_rows_read": False,
        },
        "construction": {
            "boundary_lookback_bars": LOOKBACK,
            "rejection_delay_bars": 1,
            "forward_horizon_bars": HORIZON,
            "sigma_window_returns": r5.VOL_WINDOW,
            "structure_cache_read": False,
            "B1_feature_read": False,
        },
        "event_count": int(len(events)),
        **ev,
        "BLACKBOX_read": False,
        "PnL_read": False,
        "fresh_OOS_claim": False,
        "production_authority": False,
    }


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
