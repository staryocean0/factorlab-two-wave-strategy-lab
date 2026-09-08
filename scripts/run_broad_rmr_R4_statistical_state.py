#!/usr/bin/env python3
"""Frozen R4 statistical-state Stage-1 screen.

At each mature published L5 parent, build three past-only statistical-state
variables and test each independently against a common geometry baseline for
failure-first versus same-direction extension-first. Reads no post-2020 rows.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_broad_rmr_stage1_R1_R2_R3 as base

PROTOCOL = ROOT / "docs/governance/reversal_mean_reversion_R4_statistical_state_protocol_v1.json"
REFERENCE = 100
DENSITY_WINDOW = 96
BASELINE = ["abs_drift", "log_amplitude"]
CANDIDATES = {
    "R4_A_inefficiency": BASELINE + ["R4_A_inefficiency"],
    "R4_B_event_density": BASELINE + ["R4_B_event_density"],
    "R4_C_amplitude_extremity": BASELINE + ["R4_C_amplitude_extremity"],
}


def robust_z_past(values: list[float], reference: int = REFERENCE) -> np.ndarray:
    out = np.full(len(values), np.nan, dtype=float)
    arr = np.asarray(values, dtype=float)
    for i in range(reference, len(arr)):
        hist = arr[i-reference:i]
        if not np.isfinite(hist).all() or not np.isfinite(arr[i]):
            continue
        med = float(np.median(hist))
        mad = float(np.median(np.abs(hist - med)))
        scale = 1.4826 * mad
        if not np.isfinite(scale) or scale <= 0:
            continue
        out[i] = float((arr[i] - med) / scale)
    return out


def event_density(parents: list[base.Geo], finers: list[base.Geo]) -> np.ndarray:
    finer_conf = np.asarray([f.conf for f in finers], dtype=int)
    out = np.zeros(len(parents), dtype=float)
    for i, p in enumerate(parents):
        out[i] = float(np.sum((finer_conf > p.conf - DENSITY_WINDOW) & (finer_conf < p.conf)))
    return out


def state_frame(parents: list[base.Geo], finers: list[base.Geo]) -> pd.DataFrame:
    density = event_density(parents, finers)
    eff = np.asarray([p.eff for p in parents], dtype=float)
    log_amp = np.log(np.asarray([p.amp for p in parents], dtype=float))
    z_eff = robust_z_past(eff)
    z_density = robust_z_past(density)
    z_amp = robust_z_past(log_amp)
    return pd.DataFrame({
        "ident": [p.ident for p in parents],
        "day": [p.day for p in parents],
        "conf": [p.conf for p in parents],
        "abs_drift": [p.abs_drift for p in parents],
        "log_amplitude": log_amp,
        "raw_parent_eff": eff,
        "raw_event_density": density,
        "R4_A_inefficiency": -z_eff,
        "R4_B_event_density": z_density,
        "R4_C_amplitude_extremity": np.abs(z_amp),
    })


def add_outcomes(states: pd.DataFrame, parents: list[base.Geo], logp: np.ndarray, days: np.ndarray) -> pd.DataFrame:
    by_id = {p.ident: p for p in parents}
    expiries = base.parent_expiries(parents)
    year_end = base.year_end_indices(days)
    rows = []
    for _, row in states.iterrows():
        p = by_id[str(row.ident)]
        event = float(logp[p.conf])
        failure = float(p.failure)
        dist = abs(event - failure)
        if not np.isfinite(dist) or dist <= 0:
            outcome, resolved = "censored", p.conf
        elif p.direction > 0:
            if not failure < event:
                outcome, resolved = "censored", p.conf
            else:
                extension = event + dist
                end = min(expiries[p.ident], p.conf + base.MAX_PAIR, year_end[int(p.day[:4])])
                outcome, resolved = base.first_passage(logp, p.conf, end, extension, failure, "extension", "failure")
        else:
            if not event < failure:
                outcome, resolved = "censored", p.conf
            else:
                extension = event - dist
                end = min(expiries[p.ident], p.conf + base.MAX_PAIR, year_end[int(p.day[:4])])
                outcome, resolved = base.first_passage(logp, p.conf, end, failure, extension, "failure", "extension")
        rec = dict(row)
        rec["outcome"] = outcome
        rec["resolve_idx"] = int(resolved)
        rows.append(rec)
    return pd.DataFrame(rows)


def fit_model(data: pd.DataFrame, features: list[str]) -> Pipeline | None:
    clean = data.dropna(subset=features + ["y"]).copy()
    if len(clean) < 30 or clean["y"].nunique() < 2:
        return None
    model = Pipeline([
        ("sc", StandardScaler()),
        ("lr", LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=1000, class_weight=None)),
    ])
    model.fit(clean[features].to_numpy(float), clean["y"].to_numpy(int))
    return model


def score(model: Pipeline | None, data: pd.DataFrame, features: list[str]) -> dict:
    clean = data.dropna(subset=features + ["y"]).copy()
    if model is None or clean.empty:
        return {"status": "insufficient", "n": int(len(clean))}
    y = clean["y"].to_numpy(int)
    p = model.predict_proba(clean[features].to_numpy(float))[:, 1]
    return {
        "status": "scored",
        "n": int(len(clean)),
        "event_rate": float(np.mean(y)),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
    }


def property_reversion(data: pd.DataFrame, state_col: str) -> dict:
    d = data.loc[(data["day"] >= base.CHECK_START) & (data["day"] <= base.CHECK_END), ["conf", state_col]].dropna().sort_values("conf")
    if len(d) < 3:
        return {"n_pairs": max(0, len(d)-1), "current_next_state_correlation": None, "absolute_state_contraction_share": None}
    x = d[state_col].to_numpy(float)
    cur, nxt = x[:-1], x[1:]
    corr = float(np.corrcoef(cur, nxt)[0, 1]) if np.std(cur) > 0 and np.std(nxt) > 0 else None
    contraction = float(np.mean(np.abs(nxt) < np.abs(cur)))
    return {"n_pairs": int(len(cur)), "current_next_state_correlation": corr, "absolute_state_contraction_share": contraction}


def candidate_summary(events: pd.DataFrame, candidate: str) -> dict:
    state_col = candidate
    # Exact same rows for baseline and candidate.
    d = events.loc[events["outcome"].isin(["failure", "extension"])].copy()
    d = d.dropna(subset=BASELINE + [state_col])
    d["y"] = d["outcome"].eq("failure").astype(int)
    build = d.loc[d["day"] <= base.BUILD_END].copy()
    check = d.loc[(d["day"] >= base.CHECK_START) & (d["day"] <= base.CHECK_END)].copy()
    baseline = fit_model(build, BASELINE)
    cand_features = CANDIDATES[candidate]
    cand = fit_model(build, cand_features)
    pooled_b = score(baseline, check, BASELINE)
    pooled_c = score(cand, check, cand_features)
    annual = {}
    for year in (2019, 2020):
        yp = check.loc[check["day"].str.startswith(str(year))]
        annual[str(year)] = {"baseline": score(baseline, yp, BASELINE), "candidate": score(cand, yp, cand_features)}
    coefficient = None if cand is None else float(cand.named_steps["lr"].coef_[0][-1])
    counts = {
        "BUILD_resolved": int(len(build)),
        "CHECK_2019_resolved": int(len(check.loc[check["day"].str.startswith("2019")])),
        "CHECK_2020_resolved": int(len(check.loc[check["day"].str.startswith("2020")])),
    }
    gates = {
        "supply": counts["BUILD_resolved"] >= 150 and counts["CHECK_2019_resolved"] >= 50 and counts["CHECK_2020_resolved"] >= 50,
        "pooled_brier": pooled_c.get("brier", 9.0) < pooled_b.get("brier", -9.0),
        "pooled_logloss": pooled_c.get("log_loss", 9.0) < pooled_b.get("log_loss", -9.0),
        "both_years_brier": all(annual[y]["candidate"].get("brier", 9.0) < annual[y]["baseline"].get("brier", -9.0) for y in ("2019", "2020")),
        "positive_state_coefficient": coefficient is not None and coefficient > 0.0,
    }
    return {
        "inventory": counts,
        "pooled": {"baseline": pooled_b, "candidate": pooled_c},
        "annual": annual,
        "state_coefficient": coefficient,
        "descriptive_property_reversion": property_reversion(events, state_col),
        "gates": gates,
        "qualifies_for_specialist_review": bool(all(gates.values())),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol["stage"] != "results_blind_R4_protocol_freeze_before_price_outcome_execution":
        raise RuntimeError("R4 protocol stage drifted")
    if protocol["candidate_budget"]["combined_state_model"] is not False:
        raise RuntimeError("R4 combined model unexpectedly authorized")
    if protocol["source"]["post_2020_open"] is not False:
        raise RuntimeError("R4 post-2020 unexpectedly authorized")

    identities, bars, _, _ = base.load_inputs()
    geos, logp, days = base.build_geos(identities, bars)
    parents = geos[base.PARENT_LEVEL]
    finers = geos[base.FINER_LEVEL]
    states = state_frame(parents, finers)
    events = add_outcomes(states, parents, logp, days)
    results = {candidate: candidate_summary(events, candidate) for candidate in CANDIDATES}
    qualified = [c for c in CANDIDATES if results[c]["qualifies_for_specialist_review"]]

    payload = {
        "schema_id": "factorlab_broad_rmr_R4_statistical_state_receipt@1.0",
        "session_date": "2026-09-08",
        "program_identity": "broad_reversal_mean_reversion_discovery_program_v1",
        "research_identity": "R4_statistical_state_extremes_stage1_v1",
        "code_commit": base.git_head(),
        "source": {
            "structure_cache_sha256": base.CACHE_SHA,
            "price_view_sha256": base.BARS_SHA,
            "max_day": str(bars.trading_day.max()),
            "post_2020_rows_read": False,
        },
        "parent": {"view": "5m_offset_0", "birth_level": 5, "mature_dedup_count": int(len(parents))},
        "finer_activity": {"birth_level": 3, "mature_dedup_count": int(len(finers)), "density_window_bars": DENSITY_WINDOW},
        "normalization_reference_parent_count": REFERENCE,
        "geometry_baseline": list(BASELINE),
        "candidate_ids": list(CANDIDATES),
        "combined_state_model_used": False,
        "results": results,
        "qualified_candidate_ids": qualified,
        "property_self_reversion_used_for_progression": False,
        "normalization_window_search_performed": False,
        "density_window_search_performed": False,
        "state_threshold_search_performed": False,
        "post_2020_rows_read": False,
        "scientifically_fresh": False,
        "morphology_replication_accepted": False,
        "trading_PnL_used": False,
        "production_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"qualified_candidate_ids": qualified, "post_2020_rows_read": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
