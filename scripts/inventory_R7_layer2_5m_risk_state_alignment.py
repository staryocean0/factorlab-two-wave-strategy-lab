#!/usr/bin/env python3
"""Outcome-blind alignment inventory for R7 and frozen Layer2 5m risk states."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "scripts" / "run_R7_native_1m_rejected_excursion.py"
SPEC = importlib.util.spec_from_file_location("r7_parent_inventory", PARENT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load frozen R7 parent")
r7 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = r7
SPEC.loader.exec_module(r7)

RV_WINDOW = 12
BG_WINDOW = 48
HIGHVOL_RATIO = 1.5
RECOVERY_NORMAL_RATIO = 1.1
SHOCK_SIGMA = 3.0
RISK_STATES = {"UNSAFE", "RECOVERING"}
EXPECTED_LAYER3_FIVE_SHA = "bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def transition(prev_state: str, ratio: float, is_shock: bool) -> str:
    if is_shock:
        return "UNSAFE"
    if prev_state == "UNSAFE":
        if pd.isna(ratio) or ratio >= HIGHVOL_RATIO:
            return "UNSAFE"
        if ratio > RECOVERY_NORMAL_RATIO:
            return "RECOVERING"
        return "NORMAL"
    if prev_state == "RECOVERING":
        if pd.isna(ratio):
            return "RECOVERING"
        if ratio >= HIGHVOL_RATIO:
            return "UNSAFE"
        if ratio > RECOVERY_NORMAL_RATIO:
            return "RECOVERING"
        return "NORMAL"
    return "NORMAL"


def _ts_key(s: pd.Series) -> pd.Series:
    x = pd.to_datetime(s, errors="raise")
    return x.dt.strftime("%Y-%m-%d %H:%M:%S")


def normalize_5m(frame: pd.DataFrame, timestamp_col: str) -> pd.DataFrame:
    out = pd.DataFrame({
        "symbol": frame["symbol"].astype(str),
        "trading_day": pd.to_datetime(frame["trading_day"], errors="raise").dt.strftime("%Y-%m-%d"),
        "timestamp": _ts_key(frame[timestamp_col]),
        "close": pd.to_numeric(frame["close"], errors="raise").astype(float),
    })
    out = out.sort_values(["trading_day", "timestamp"], kind="stable").reset_index(drop=True)
    if out["timestamp"].duplicated().any():
        raise RuntimeError("duplicate 5m timestamp")
    return out


def finalized_state_replay(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    counts = frame.groupby("trading_day", sort=False).size()
    complete_days = set(counts.index[counts.eq(48)])
    work = frame.loc[frame["trading_day"].isin(complete_days)].copy().reset_index(drop=True)
    excluded = sorted(set(frame["trading_day"]) - complete_days)

    work["ret_5m"] = work.groupby("trading_day", sort=False)["close"].transform(lambda s: np.log(s).diff())
    valid = work["ret_5m"].dropna()
    work["rv12"] = valid.rolling(RV_WINDOW, min_periods=RV_WINDOW).std(ddof=0).reindex(work.index)
    work["bg_vol48"] = valid.shift(1).rolling(BG_WINDOW, min_periods=BG_WINDOW).std(ddof=0).reindex(work.index)
    work.loc[work["bg_vol48"] <= 0.0, "bg_vol48"] = np.nan
    work["vol_ratio"] = work["rv12"] / work["bg_vol48"]
    work["shock_intensity"] = work["ret_5m"].abs() / work["bg_vol48"]
    work["shock"] = work["shock_intensity"] >= SHOCK_SIGMA

    states = pd.Series("NORMAL", index=work.index, dtype="object")
    for _, idx in work.groupby("trading_day", sort=False).groups.items():
        mode = "NORMAL"
        for i in idx:
            shock = bool(work.at[i, "shock"]) if pd.notna(work.at[i, "shock"]) else False
            mode = transition(mode, float(work.at[i, "vol_ratio"]) if pd.notna(work.at[i, "vol_ratio"]) else np.nan, shock)
            states.at[i] = mode
    work["risk_state"] = states
    work["risk_bucket"] = np.where(work["risk_state"].isin(RISK_STATES), "RISK_ACTIVE", "LOW_RISK")
    meta = {
        "input_rows": int(len(frame)),
        "input_days": int(frame["trading_day"].nunique()),
        "complete_48bar_days": int(len(complete_days)),
        "excluded_incomplete_days": int(len(excluded)),
        "excluded_day_labels": excluded,
        "replayed_rows": int(len(work)),
    }
    return work, meta


def outcome_blind_r7_endpoint_eligibility(one_min_path: Path, five_min_path: Path) -> pd.DataFrame:
    one = r7._load(one_min_path, r7.ONE_MIN_SHA, r7.ONE_MIN_ROWS)
    five = r7._load(five_min_path, r7.FIVE_MIN_SHA, r7.FIVE_MIN_ROWS)

    ts = one["bar_end_shanghai"]
    day = one["trading_day"]
    exact = day.eq(day.shift(1)) & ((ts - ts.shift(1)) == pd.Timedelta(minutes=1))
    segment_id = (~exact).cumsum().to_numpy(dtype=int)
    log_close = np.log(one["close"].to_numpy(dtype=float))
    exact_idx = np.flatnonzero(exact.to_numpy())
    exact_r = log_close[exact_idx] - log_close[exact_idx - 1]
    sigma_exact = np.sqrt(pd.Series(exact_r).pow(2).rolling(r7.VOL_WINDOW, min_periods=r7.VOL_WINDOW).mean().shift(1)).to_numpy(dtype=float)
    sigma_by_row = np.full(len(one), np.nan, dtype=float)
    sigma_by_row[exact_idx] = sigma_exact

    official = set(pd.to_datetime(five["bar_end_shanghai"], errors="raise").tolist())
    one_times = one["bar_end_shanghai"].tolist()
    one_days = one["trading_day"].tolist()
    rows = []
    for i in range(r7.PATH_RETURNS, len(one) - r7.FORWARD_RETURNS):
        t = one_times[i]
        if t not in official:
            continue
        if (t - pd.Timedelta(minutes=5)) not in official or (t + pd.Timedelta(minutes=5)) not in official:
            continue
        if segment_id[i - r7.PATH_RETURNS] != segment_id[i + r7.FORWARD_RETURNS]:
            continue
        sigma = float(sigma_by_row[i])
        if not np.isfinite(sigma) or sigma <= 0.0:
            continue
        d = str(one_days[i])
        role = r7.evidence_role(d)
        if role is None:
            raise RuntimeError("eligible endpoint escaped admitted period")
        rows.append({
            "trading_day": d,
            "year": int(d[:4]),
            "role": role,
            "timestamp": pd.Timestamp(t).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return pd.DataFrame(rows)


def summarize_supply(joined: pd.DataFrame) -> dict[str, Any]:
    groups = {
        "TRAIN": joined.loc[joined["role"].eq("TRAIN")],
        "VALIDATION": joined.loc[joined["role"].eq("VALIDATION")],
        "2019": joined.loc[joined["year"].eq(2019)],
        "2020": joined.loc[joined["year"].eq(2020)],
    }
    out: dict[str, Any] = {}
    for name, g in groups.items():
        vc = g["risk_bucket"].value_counts(dropna=False)
        sv = g["risk_state"].value_counts(dropna=False)
        out[name] = {
            "eligible_candidates": int(len(g)),
            "LOW_RISK": int(vc.get("LOW_RISK", 0)),
            "RISK_ACTIVE": int(vc.get("RISK_ACTIVE", 0)),
            "NORMAL": int(sv.get("NORMAL", 0)),
            "UNSAFE": int(sv.get("UNSAFE", 0)),
            "RECOVERING": int(sv.get("RECOVERING", 0)),
            "matched_days": int(g.loc[g["risk_state"].notna(), "trading_day"].nunique()),
        }
    return out


def run(layer2_2020: Path) -> dict[str, Any]:
    if sha256_file(r7.FIVE_MIN_PATH) != EXPECTED_LAYER3_FIVE_SHA:
        raise RuntimeError("Layer3 5m SHA drift")
    five = r7._load(r7.FIVE_MIN_PATH, r7.FIVE_MIN_SHA, r7.FIVE_MIN_ROWS)
    l3 = normalize_5m(five.rename(columns={"bar_end_shanghai": "timestamp"}), "timestamp")

    # Full-history replay is the consumer state series used for 2015-2020 R7 bucketing.
    l3_states, l3_meta = finalized_state_replay(l3)

    ext_raw = pd.read_parquet(layer2_2020)
    required = {"symbol", "trading_day", "timestamp", "close"}
    if not required.issubset(ext_raw.columns):
        raise RuntimeError(f"Layer2 overlap missing columns: {required - set(ext_raw.columns)}")
    ext = normalize_5m(ext_raw, "timestamp")
    if set(ext["symbol"]) != {"000852.SH"}:
        raise RuntimeError("Layer2 overlap symbol mismatch")
    ext_states, ext_meta = finalized_state_replay(ext)

    # Cross-repository equivalence must use the same physical 2020 boundary as the
    # frozen Layer2 V9 loader. Do not carry 2019 rolling history into this comparator.
    l3_2020_raw = l3.loc[l3["trading_day"].str.startswith("2020-")].copy()
    l3_overlap_states, l3_overlap_meta = finalized_state_replay(l3_2020_raw)
    overlap = l3_overlap_states.merge(ext_states, on="timestamp", suffixes=("_l3", "_l2"), how="inner")
    close_diff = np.abs(overlap["close_l3"].to_numpy(float) - overlap["close_l2"].to_numpy(float)) if len(overlap) else np.array([])
    state_agreement = float(overlap["risk_state_l3"].eq(overlap["risk_state_l2"]).mean()) if len(overlap) else 0.0

    eligible = outcome_blind_r7_endpoint_eligibility(r7.ONE_MIN_PATH, r7.FIVE_MIN_PATH)
    joined = eligible.merge(
        l3_states[["timestamp", "risk_state", "risk_bucket", "vol_ratio", "shock_intensity"]],
        on="timestamp", how="left", validate="one_to_one"
    )
    match_fraction = float(joined["risk_state"].notna().mean()) if len(joined) else 0.0
    supply = summarize_supply(joined)
    supply_ok = all(
        supply[g]["RISK_ACTIVE"] >= 500 and supply[g]["LOW_RISK"] >= 5000
        for g in ("TRAIN", "VALIDATION", "2019", "2020")
    )
    gates = {
        "layer3_sha_pass": True,
        "layer3_symbol_pass": set(l3["symbol"]) == {"000852.SH"},
        "layer3_max_day_pass": l3["trading_day"].max() <= "2020-12-31",
        "overlap_nonempty": bool(len(overlap) > 0),
        "overlap_close_max_abs_diff_le_1e12": bool(len(overlap) > 0 and float(close_diff.max()) <= 1e-12),
        "overlap_state_agreement_exact": bool(len(overlap) > 0 and state_agreement == 1.0),
        "candidate_state_match_ge_099": bool(match_fraction >= 0.99),
        "bucket_supply_pass": bool(supply_ok),
    }
    return {
        "schema_id": "factorlab_R7_L2_5m_risk_state_alignment_inventory@1.0",
        "identity": "R7_L2_5m_risk_state_alignment_inventory_v1",
        "layer2_reference": {
            "state_runner_blob": "ae2a7e095df58692ef9df0dfee5856cac727ca44",
            "canonical_market_repo": "staryocean0/factorlab-trend-reversion-regime-lab",
            "canonical_market_commit": "1d760ea9525eb3688b70a4aa0f2b5b207af16a17",
            "external_2020_sha256": sha256_file(layer2_2020),
        },
        "layer3_replay": l3_meta,
        "layer3_overlap_replay_2020_physical_boundary": l3_overlap_meta,
        "layer2_overlap_replay": ext_meta,
        "overlap_2020": {
            "common_rows": int(len(overlap)),
            "close_max_abs_diff": float(close_diff.max()) if len(overlap) else None,
            "risk_state_agreement": state_agreement,
        },
        "r7_endpoint_eligibility": {
            "candidate_rows_without_outcome": int(len(eligible)),
            "state_matched_rows": int(joined["risk_state"].notna().sum()),
            "state_match_fraction": match_fraction,
        },
        "supply": supply,
        "gates": gates,
        "alignment_supported": bool(all(gates.values())),
        "outcome_columns_read": False,
        "R7_model_fit_performed": False,
        "BLACKBOX_read": False,
        "post_2020_rows_read_in_layer3": False,
        "PnL_read": False,
        "fresh_OOS_claim": False,
        "production_authority": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer2-2020", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = run(args.layer2_2020)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
