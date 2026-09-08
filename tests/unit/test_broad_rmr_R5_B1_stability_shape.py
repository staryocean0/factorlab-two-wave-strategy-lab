from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "diagnose_broad_rmr_R5_B1_stability_shape.py"
SPEC = importlib.util.spec_from_file_location("r5_b1_diag", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
diag = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = diag
SPEC.loader.exec_module(diag)


def test_adjudication_table_is_exact() -> None:
    assert diag.adjudicate(True, True) == "R5_B1_diagnostic_supported_for_specialist_research"
    assert diag.adjudicate(False, True) == "R5_B1_mechanism_shape_supported_but_day_breadth_weak"
    assert diag.adjudicate(True, False) == "R5_B1_day_breadth_supported_but_shape_weak"
    assert diag.adjudicate(False, False) == "R5_B1_small_gain_not_robust_enough_to_specialize"


def test_train_quintile_edges_are_feature_only_and_strict() -> None:
    frame = pd.DataFrame({"anti_persistence": np.linspace(-1.0, 1.0, 1000)})
    edges = diag.train_quintile_edges(frame)
    assert len(edges) == 4
    assert np.all(np.diff(edges) > 0.0)
    q = diag.assign_quintiles(np.array([-2.0, edges[0] - 1e-6, edges[0] + 1e-6, 2.0]), edges)
    assert q.tolist()[0] == 0
    assert q.tolist()[-1] == 4


def test_D1_marks_broad_daily_improvement_when_B1_is_uniformly_better() -> None:
    rows = []
    for year in (2019, 2020):
        for day_i in range(20):
            day = f"{year}-01-{day_i + 1:02d}"
            for j in range(10):
                z = -1.0 + 2.0 * j / 9.0
                anti = 0.5
                next_z = -0.5 * z
                rows.append((day, year, z, anti, 0.1, next_z))
    validation = pd.DataFrame(rows, columns=["trading_day", "year", "z", "anti_persistence", "long_memory", "next_z"])
    beta0 = np.array([0.0, 0.0])
    beta1 = np.array([0.0, 0.0, -1.0])
    result = diag.evaluate_D1(validation, beta0, beta1)
    assert result["D1_day_breadth_supported"] is True
    assert result["by_year"]["2019"]["fraction_B1_better"] == 1.0
    assert result["by_year"]["2020"]["median"] > 0.0


def _shape_frame(years: np.ndarray, anti: np.ndarray) -> pd.DataFrame:
    z = np.tile(np.array([-1.5, -0.5, 0.5, 1.5]), len(anti) // 4 + 1)[: len(anti)]
    slope = 0.4 - 1.2 * anti
    next_z = slope * z
    return pd.DataFrame(
        {
            "year": years,
            "anti_persistence": anti,
            "z": z,
            "next_z": next_z,
        }
    )


def test_D2_detects_decreasing_empirical_slope_shape() -> None:
    anti_train = np.linspace(-0.5, 1.0, 2000)
    train = _shape_frame(np.full(2000, 2018), anti_train)
    anti_val = np.linspace(-0.5, 1.0, 2000)
    years = np.array([2019] * 1000 + [2020] * 1000)
    validation = _shape_frame(years, anti_val)
    result = diag.evaluate_D2(train, validation)
    assert result["D2_shape_supported"] is True
    assert result["VALIDATION"]["shape_trend"] < 0.0
    assert result["2019"]["top_lt_bottom"] is True
    assert result["2020"]["top_lt_bottom"] is True
