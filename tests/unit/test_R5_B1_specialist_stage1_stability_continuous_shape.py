from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "diagnose_R5_B1_specialist_stage1_stability_continuous_shape.py"
SPEC = importlib.util.spec_from_file_location("r5_b1_stage1", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
stage1 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = stage1
SPEC.loader.exec_module(stage1)


def test_adjudication_table_is_exact() -> None:
    assert stage1.adjudicate(True, True) == "R5_B1_specialist_stage1_stability_and_continuous_shape_supported"
    assert stage1.adjudicate(True, False) == "R5_B1_specialist_stage1_time_stable_but_shape_weak"
    assert stage1.adjudicate(False, True) == "R5_B1_specialist_stage1_shape_supported_but_time_stability_weak"
    assert stage1.adjudicate(False, False) == "R5_B1_specialist_stage1_not_robust_enough_for_transport"


def test_halfyear_labels_are_calendar_fixed() -> None:
    frame = pd.DataFrame(
        {
            "bar_end_shanghai": pd.to_datetime(["2019-01-02 09:35", "2019-06-28 14:55", "2019-07-01 09:35", "2020-12-31 14:55"]),
            "year": [2019, 2019, 2019, 2020],
        }
    )
    out = stage1.add_halfyear(frame)
    assert out["halfyear"].tolist() == ["2019H1", "2019H1", "2019H2", "2020H2"]


def _stable_frame(years: list[int], rows_per_half: int = 60) -> pd.DataFrame:
    rows = []
    for year in years:
        for half in (1, 2):
            month = 3 if half == 1 else 9
            anti = np.linspace(-0.25, 0.25, rows_per_half)
            z = np.tile(np.array([-1.5, -0.5, 0.5, 1.5]), rows_per_half // 4 + 1)[:rows_per_half]
            next_z = 0.10 * z - 0.80 * z * anti
            for i in range(rows_per_half):
                rows.append(
                    {
                        "bar_end_shanghai": pd.Timestamp(year=year, month=month, day=1) + pd.Timedelta(minutes=5 * i),
                        "year": year,
                        "z": float(z[i]),
                        "anti_persistence": float(anti[i]),
                        "long_memory": 0.0,
                        "next_z": float(next_z[i]),
                    }
                )
    return pd.DataFrame(rows)


def test_S1_supports_persistent_negative_interaction_and_fixed_gain() -> None:
    train = _stable_frame([2015, 2016, 2017, 2018])
    validation = _stable_frame([2019, 2020])
    beta0 = np.array([0.0, 0.10])
    beta1 = np.array([0.0, 0.10, -0.80])
    result = stage1.evaluate_S1(train, validation, beta0, beta1, min_block_rows=40)
    assert result["usable"] is True
    assert result["S1_time_stability_supported"] is True
    assert result["summary"]["TRAIN_negative_local_interaction_blocks"] == 8
    assert result["summary"]["VALIDATION_negative_local_interaction_blocks"] == 4
    assert result["summary"]["VALIDATION_positive_fixed_B1_improvement_blocks"] == 4


def _shape_frame(years: np.ndarray, anti: np.ndarray) -> pd.DataFrame:
    z = np.tile(np.array([-1.5, -0.5, 0.5, 1.5]), len(anti) // 4 + 1)[: len(anti)]
    next_z = (0.20 - 0.70 * anti) * z
    return pd.DataFrame({"year": years, "anti_persistence": anti, "z": z, "next_z": next_z})


def test_S2_supports_continuous_decreasing_shape() -> None:
    anti_train = np.linspace(-0.5, 0.5, 4000)
    train = _shape_frame(np.full(4000, 2018), anti_train)
    one_year = np.linspace(-0.5, 0.5, 2000)
    validation = _shape_frame(np.array([2019] * 2000 + [2020] * 2000), np.concatenate([one_year, one_year]))
    result = stage1.evaluate_S2(train, validation, min_bin_rows=100)
    assert result["usable"] is True
    assert result["S2_continuous_shape_supported"] is True
    assert result["VALIDATION"]["linear_trend"] < 0.0
    assert result["VALIDATION"]["spearman"] <= -0.50
    assert result["VALIDATION"]["top20_slope"] < result["VALIDATION"]["bottom20_slope"]


def test_S2_rejects_increasing_shape() -> None:
    anti_train = np.linspace(-0.5, 0.5, 4000)
    z_train = np.tile(np.array([-1.5, -0.5, 0.5, 1.5]), 1000)
    train = pd.DataFrame({"year": 2018, "anti_persistence": anti_train, "z": z_train})
    train["next_z"] = (0.20 + 0.70 * train["anti_persistence"]) * train["z"]
    one_year = np.linspace(-0.5, 0.5, 2000)
    anti_val = np.concatenate([one_year, one_year])
    z_val = np.tile(np.array([-1.5, -0.5, 0.5, 1.5]), 1000)
    validation = pd.DataFrame({"year": [2019] * 2000 + [2020] * 2000, "anti_persistence": anti_val, "z": z_val})
    validation["next_z"] = (0.20 + 0.70 * validation["anti_persistence"]) * validation["z"]
    result = stage1.evaluate_S2(train, validation, min_bin_rows=100)
    assert result["usable"] is True
    assert result["S2_continuous_shape_supported"] is False
    assert result["VALIDATION"]["linear_trend"] > 0.0
