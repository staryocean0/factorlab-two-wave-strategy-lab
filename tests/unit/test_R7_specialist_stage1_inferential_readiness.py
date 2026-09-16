from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "run_R7_specialist_stage1_inferential_readiness.py"
SPEC = importlib.util.spec_from_file_location("r7_specialist_stage1", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
s1 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = s1
SPEC.loader.exec_module(s1)


def _synthetic() -> pd.DataFrame:
    rows = []
    for year in range(2015, 2021):
        role = "TRAIN" if year <= 2018 else "VALIDATION"
        for day in range(1, 21):
            date = f"{year}-03-{day:02d}"
            for i in range(20):
                endpoint = [-1.0, -0.3, 0.4, 0.9][i % 4]
                rejection = [0.25, -0.35, 0.65, -0.75][i % 4]
                noise = ((day % 5) - 2) * 0.002
                y = 0.02 + 0.08 * endpoint - 0.55 * rejection + noise
                rows.append((date, year, role, endpoint, rejection, y))
    return pd.DataFrame(
        rows,
        columns=["trading_day", "year", "role", "endpoint_z", "rejection_signed_z", "next5_z"],
    )


def test_cluster_robust_ols_recovers_negative_rejection_and_ci() -> None:
    x = _synthetic()
    X, y = s1._b1_matrix(x)
    fit = s1.cluster_robust_ols(X, y, x["trading_day"].to_numpy())
    assert fit["beta"][2] < 0.0
    assert fit["ci_upper"][2] < 0.0
    assert fit["clusters"] == x["trading_day"].nunique()


def test_bootstrap_mean_ci_is_deterministic() -> None:
    values = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
    a = s1.bootstrap_mean_ci(values, seed=123, reps=500)
    b = s1.bootstrap_mean_ci(values, seed=123, reps=500)
    assert a == b
    assert a[0] > 0.0


def test_C1_supports_consistent_negative_clustered_effect() -> None:
    result = s1.evaluate_C1(_synthetic())
    assert result["C1_clustered_coefficient_supported"] is True
    for group in ("TRAIN", "VALIDATION", "2019", "2020"):
        assert result[group]["rejection_CI95_upper"] < 0.0


def test_C3_clean_for_exact_fixed_model() -> None:
    x = _synthetic()
    beta1 = np.array([0.02, 0.08, -0.55])
    result = s1.evaluate_C3(x, beta1)
    assert result["C3_calibration_clean"] is True
    for group in ("VALIDATION", "2019", "2020"):
        assert result[group]["clean"] is True


def test_adjudication_separates_calibration_drift_from_mechanism_failure() -> None:
    assert s1.adjudicate(True, True, True) == "R7_specialist_stage1_inferentially_supported_calibration_clean"
    assert s1.adjudicate(True, True, False) == "R7_specialist_stage1_inferentially_supported_calibration_drift"
    assert s1.adjudicate(False, True, True) == "R7_specialist_stage1_inferential_support_insufficient"
    assert s1.adjudicate(True, False, True) == "R7_specialist_stage1_inferential_support_insufficient"
