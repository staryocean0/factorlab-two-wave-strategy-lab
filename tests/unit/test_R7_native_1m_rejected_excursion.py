from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "run_R7_native_1m_rejected_excursion.py"
SPEC = importlib.util.spec_from_file_location("r7_native_path", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
r7 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = r7
SPEC.loader.exec_module(r7)

SMALL_SUPPLY = {
    "train_candidates": 40,
    "validation_candidates": 40,
    "year_candidates": 15,
    "train_positive": 15,
    "train_negative": 15,
    "validation_positive": 15,
    "validation_negative": 15,
}


def test_path_feature_sign_is_symmetric_for_rejected_excursions() -> None:
    sigma = 0.01
    up = np.array([0.0, 0.01, 0.03, 0.025, 0.015, 0.01])
    endpoint_u, reject_u, extreme_u, k_u = r7.path_features(up, sigma)
    assert extreme_u > 0.0
    assert reject_u > 0.0
    assert k_u == 2
    assert endpoint_u > 0.0

    down = -up
    endpoint_d, reject_d, extreme_d, k_d = r7.path_features(down, sigma)
    assert extreme_d < 0.0
    assert reject_d < 0.0
    assert k_d == 2
    assert endpoint_d < 0.0
    assert np.isclose(reject_d, -reject_u)


def _synthetic_candidates(rejection_beta: float = -0.8) -> pd.DataFrame:
    rows = []
    specs = [("TRAIN", 2018, 120), ("VALIDATION", 2019, 60), ("VALIDATION", 2020, 60)]
    for role, year, n in specs:
        for i in range(n):
            endpoint = [-1.0, -0.4, 0.2, 0.8][i % 4]
            magnitude = [0.25, 0.55, 0.85][i % 3]
            rejection = magnitude if i % 2 == 0 else -magnitude
            next5 = 0.15 * endpoint + rejection_beta * rejection
            rows.append((role, year, endpoint, rejection, next5))
    return pd.DataFrame(rows, columns=["role", "year", "endpoint_z", "rejection_signed_z", "next5_z"])


def test_supported_synthetic_path_information_passes_all_gates() -> None:
    result = r7.evaluate(_synthetic_candidates(-0.8), SMALL_SUPPLY)
    assert result["supply_supported"] is True
    assert result["coefficient_direction_supported"] is True
    assert result["fixed_prediction_supported"] is True
    assert result["directional_symmetry_supported"] is True
    assert result["adjudication"] == "R7_supported_for_one_bounded_diagnostic"
    assert result["local_coefficients"]["2019"]["rejection_coefficient"] < 0.0
    assert result["local_coefficients"]["2020"]["rejection_coefficient"] < 0.0


def test_wrong_coefficient_direction_is_rejected() -> None:
    result = r7.evaluate(_synthetic_candidates(+0.8), SMALL_SUPPLY)
    assert result["supply_supported"] is True
    assert result["coefficient_direction_supported"] is False
    assert result["adjudication"] == "R7_coefficient_direction_not_supported"


def test_supply_failure_is_rejected_before_progression() -> None:
    tiny = _synthetic_candidates(-0.8).iloc[:20].copy()
    result = r7.evaluate(tiny, SMALL_SUPPLY)
    assert result["adjudication"] in {"R7_execution_drift_or_insufficient", "R7_supply_insufficient"}
