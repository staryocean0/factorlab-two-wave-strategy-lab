from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "diagnose_R7_L2_5m_risk_bucket_calibration.py"
SPEC = importlib.util.spec_from_file_location("r7_l2_state_diag", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
diag = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = diag
SPEC.loader.exec_module(diag)


def _synthetic() -> pd.DataFrame:
    rows = []
    for year in (2018, 2019, 2020):
        role = "TRAIN" if year == 2018 else "VALIDATION"
        for day in range(1, 31):
            d = f"{year}-03-{day:02d}"
            for i in range(40):
                endpoint = [-1.2, -0.4, 0.3, 1.0][i % 4] + 0.01 * (day % 3)
                rejection = [-0.8, -0.2, 0.35, 0.9][(i // 2) % 4] + 0.005 * (day % 5)
                risk = 1.0 if (i % 5 in (0, 1)) else 0.0
                # LOW_RISK: [0.02, 0.08, -0.45]
                # RISK_ACTIVE: [0.08, -0.02, -0.80]
                y = 0.02 + 0.08 * endpoint - 0.45 * rejection
                if risk:
                    y += 0.06 - 0.10 * endpoint - 0.35 * rejection
                y += ((day % 7) - 3) * 0.001
                rows.append((d, year, role, endpoint, rejection, y, "RISK_ACTIVE" if risk else "LOW_RISK"))
    return pd.DataFrame(rows, columns=[
        "trading_day", "year", "role", "endpoint_z", "rejection_signed_z", "next5_z", "risk_bucket"
    ])


def test_state_design_recovers_two_parameter_vectors() -> None:
    x = _synthetic()
    train = x.loc[x["role"].eq("TRAIN")]
    beta = diag.fit_state(train)
    low = np.array([beta[0], beta[1], beta[2]])
    high = np.array([beta[0] + beta[3], beta[1] + beta[4], beta[2] + beta[5]])
    assert np.allclose(low, [0.02, 0.08, -0.45], atol=0.01)
    assert np.allclose(high, [0.08, -0.02, -0.80], atol=0.01)


def test_G1_detects_joint_state_heterogeneity() -> None:
    x = _synthetic()
    train = x.loc[x["role"].eq("TRAIN")]
    result = diag.evaluate_G1(train)
    assert result["joint_wald_df3"] > diag.CHI2_DF3_95
    assert result["G1_heterogeneity_supported"] is True


def test_G2_requires_prediction_gain_in_both_validation_years() -> None:
    x = _synthetic()
    train = x.loc[x["role"].eq("TRAIN")]
    beta2 = diag.fit_state(train)
    beta1 = np.array([0.02, 0.08, -0.45])
    result = diag.evaluate_G2(x, beta1, beta2)
    assert result["G2_prediction_supported"] is True
    for group in ("VALIDATION", "2019", "2020"):
        assert result[group]["MSE_B2"] < result[group]["MSE_B1"]


def test_G3_clean_for_exact_state_model() -> None:
    x = _synthetic()
    train = x.loc[x["role"].eq("TRAIN")]
    beta2 = diag.fit_state(train)
    result = diag.evaluate_G3(x, beta2)
    assert result["G3_calibration_clean"] is True
    assert result["VALIDATION"]["clean"] is True
    assert result["2019"]["clean"] is True
    assert result["2020"]["clean"] is True


def test_adjudication_table_is_exact() -> None:
    assert diag.adjudicate(True, True, True) == "R7_L2_state_conditioning_supported_calibration_clean"
    assert diag.adjudicate(True, True, False) == "R7_L2_state_conditioning_supported_residual_drift"
    assert diag.adjudicate(True, False, True) == "R7_L2_state_heterogeneity_supported_but_prediction_not_robust"
    assert diag.adjudicate(False, True, True) == "R7_L2_state_conditioning_not_supported"
    assert diag.adjudicate(False, False, False) == "R7_L2_state_conditioning_not_supported"
