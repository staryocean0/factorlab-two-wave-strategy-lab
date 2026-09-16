from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
SCRIPT = SCRIPTS / "run_R7_L2_state_specific_calibration_challenger.py"
SPEC = importlib.util.spec_from_file_location("r7_l2_challenger", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def _frame() -> pd.DataFrame:
    rows = []
    cid = 0
    # Full-rank prior history in each bucket with deliberately different coefficients.
    for bucket, beta in [
        ("LOW_RISK", np.array([0.01, 0.10, -0.40])),
        ("RISK_ACTIVE", np.array([-0.02, 0.20, -0.70])),
    ]:
        for day, endpoint, rejection in [
            ("2018-12-26", -1.0, 0.5),
            ("2018-12-27", -0.2, -0.7),
            ("2018-12-28", 0.4, 0.9),
            ("2018-12-31", 1.1, -0.4),
        ]:
            y = float(beta @ np.array([1.0, endpoint, rejection]))
            rows.append((cid, day, "TRAIN", endpoint, rejection, y, bucket))
            cid += 1
    # First evaluation day in both buckets.
    rows.extend([
        (cid, "2019-01-02", "VALIDATION", 0.3, 0.8, 9.0, "LOW_RISK"),
        (cid + 1, "2019-01-02", "VALIDATION", -0.4, -0.6, -9.0, "RISK_ACTIVE"),
        (cid + 2, "2019-01-03", "VALIDATION", 0.2, 0.5, 0.0, "LOW_RISK"),
        (cid + 3, "2019-01-03", "VALIDATION", 0.6, -0.1, 0.0, "RISK_ACTIVE"),
    ])
    return pd.DataFrame(rows, columns=[
        "candidate_id", "trading_day", "role", "endpoint_z", "rejection_signed_z", "next5_z", "risk_bucket"
    ])


def test_state_specific_first_day_uses_only_prior_history() -> None:
    x = _frame()
    pred, audit = mod.causal_state_specific_forecasts(x)
    for bucket in mod.BUCKETS:
        hist = x.loc[(x["trading_day"] < "2019-01-02") & x["risk_bucket"].eq(bucket)]
        cur = x.loc[(x["trading_day"] == "2019-01-02") & x["risk_bucket"].eq(bucket)]
        beta = mod.base._fit_b1(hist)
        expected = mod.base.forecast_b1(cur, beta)
        np.testing.assert_allclose(pred.loc[cur["candidate_id"]].to_numpy(), expected, atol=1e-12)
    assert audit["all_history_strictly_prior"] is True
    assert audit["all_history_full_rank"] is True


def test_same_day_outcomes_do_not_enter_same_day_fit() -> None:
    x = _frame()
    p1, _ = mod.causal_state_specific_forecasts(x)
    x2 = x.copy()
    x2.loc[x2["trading_day"].eq("2019-01-02"), "next5_z"] *= 1000.0
    p2, _ = mod.causal_state_specific_forecasts(x2)
    ids = x.loc[x["trading_day"].eq("2019-01-02"), "candidate_id"]
    np.testing.assert_allclose(p1.loc[ids].to_numpy(), p2.loc[ids].to_numpy(), atol=1e-12)


def test_prior_day_outcomes_may_enter_next_day_fit() -> None:
    x = _frame()
    p1, _ = mod.causal_state_specific_forecasts(x)
    x2 = x.copy()
    x2.loc[(x2["trading_day"] == "2019-01-02") & x2["risk_bucket"].eq("LOW_RISK"), "next5_z"] += 100.0
    p2, _ = mod.causal_state_specific_forecasts(x2)
    low_next = x.loc[(x["trading_day"] == "2019-01-03") & x["risk_bucket"].eq("LOW_RISK"), "candidate_id"]
    assert not np.allclose(p1.loc[low_next].to_numpy(), p2.loc[low_next].to_numpy())


def test_bucket_updates_are_independent() -> None:
    x = _frame()
    p1, _ = mod.causal_state_specific_forecasts(x)
    x2 = x.copy()
    x2.loc[x2["risk_bucket"].eq("RISK_ACTIVE"), "next5_z"] += 50.0
    p2, _ = mod.causal_state_specific_forecasts(x2)
    low_ids = x.loc[x["risk_bucket"].eq("LOW_RISK") & (x["trading_day"] >= "2019-01-01"), "candidate_id"]
    np.testing.assert_allclose(p1.loc[low_ids].to_numpy(), p2.loc[low_ids].to_numpy(), atol=1e-12)


def test_position_and_cost_contract_are_reused_from_old_baseline() -> None:
    forecast = np.array([-2.0, -0.25, 0.0, 0.3, 2.0])
    np.testing.assert_allclose(mod.base.position_from_forecast(forecast), [-1.0, -0.25, 0.0, 0.3, 1.0])
    legs = pd.DataFrame({
        "trading_day": ["2019-01-02", "2019-01-03"],
        "gross_return": [0.01, -0.005],
        "turnover": [0.5, 1.5],
        "position": [0.2, -0.3],
    })
    m2 = mod.base.performance_metrics(legs, 2.0)
    np.testing.assert_allclose(m2["cumulative_explicit_cost"], 2.0 * 2.0 / 10000.0, atol=1e-15)
