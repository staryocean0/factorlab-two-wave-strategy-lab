from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "diagnose_R7_rejected_excursion_stability_shape.py"
SPEC = importlib.util.spec_from_file_location("r7_diag", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
diag = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = diag
SPEC.loader.exec_module(diag)


def test_adjudication_table_is_exact() -> None:
    assert diag.adjudicate(True, True) == "R7_diagnostic_supported_for_specialist_research"
    assert diag.adjudicate(True, False) == "R7_diagnostic_time_stable_but_magnitude_shape_weak"
    assert diag.adjudicate(False, True) == "R7_diagnostic_shape_supported_but_time_stability_weak"
    assert diag.adjudicate(False, False) == "R7_diagnostic_not_robust_enough_for_specialist"


def _stable_blocks() -> pd.DataFrame:
    rows = []
    for year in range(2015, 2021):
        role = "TRAIN" if year <= 2018 else "VALIDATION"
        for half, month in ((1, 3), (2, 9)):
            for i in range(80):
                endpoint = [-1.0, -0.3, 0.4, 0.9][i % 4]
                rejection = [0.25, -0.35, 0.65, -0.75][i % 4]
                y = 0.1 * endpoint - 0.5 * rejection
                rows.append((f"{year}-{month:02d}-01", year, role, endpoint, rejection, y))
    return pd.DataFrame(rows, columns=["trading_day", "year", "role", "endpoint_z", "rejection_signed_z", "next5_z"])


def test_D1_supports_stable_halfyear_effect() -> None:
    x = _stable_blocks()
    result = diag.evaluate_D1(x, np.array([0.0, 0.1]), np.array([0.0, 0.1, -0.5]), min_block=40)
    assert result["usable"] is True
    assert result["D1_time_stability_supported"] is True
    assert result["summary"]["TRAIN_negative_coefficient_blocks"] == 8
    assert result["summary"]["VALIDATION_negative_coefficient_blocks"] == 4
    assert result["summary"]["VALIDATION_positive_fixed_improvement_blocks"] == 4


def _shape_candidates() -> pd.DataFrame:
    rows = []
    specs = [("TRAIN", 2018, 2000), ("VALIDATION", 2019, 1000), ("VALIDATION", 2020, 1000)]
    for role, year, n in specs:
        for i in range(n):
            mag = 0.05 + 0.95 * (i + 1) / n
            rejection = mag if i % 2 == 0 else -mag
            endpoint = [-0.5, 0.5][i % 2]
            y = -0.8 * rejection
            rows.append((str(year) + "-06-01", year, role, endpoint, rejection, y))
    return pd.DataFrame(rows, columns=["trading_day", "year", "role", "endpoint_z", "rejection_signed_z", "next5_z"])


def test_D2_detects_increasing_reversal_score_with_magnitude() -> None:
    result = diag.evaluate_D2(_shape_candidates(), np.array([0.0, 0.0]), min_bin=40, min_sign=15)
    assert result["usable"] is True
    assert result["D2_magnitude_shape_supported"] is True
    for group in ("TRAIN", "VALIDATION", "2019", "2020"):
        assert result[group]["linear_trend_score_vs_abs_rejection"] > 0.0
        assert result[group]["top_sign_symmetry"] is True


def test_D2_rejects_wrong_magnitude_direction() -> None:
    x = _shape_candidates()
    x["next5_z"] = 0.8 * x["rejection_signed_z"]
    result = diag.evaluate_D2(x, np.array([0.0, 0.0]), min_bin=40, min_sign=15)
    assert result["usable"] is True
    assert result["D2_magnitude_shape_supported"] is False
