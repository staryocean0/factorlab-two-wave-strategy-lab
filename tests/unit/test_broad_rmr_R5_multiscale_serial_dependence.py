from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "run_broad_rmr_R5_multiscale_serial_dependence.py"
SPEC = importlib.util.spec_from_file_location("r5_serial", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
r5 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = r5
SPEC.loader.exec_module(r5)


def _native(times: list[str], days: list[str] | None = None) -> pd.DataFrame:
    if days is None:
        days = ["2019-01-02"] * len(times)
    return pd.DataFrame(
        {
            "symbol": [r5.SYMBOL] * len(times),
            "trading_day": days,
            "close": 100.0 * np.exp(np.arange(len(times), dtype=float) * 0.001),
            "bar_end_shanghai": pd.to_datetime(times),
        }
    )


def test_exact_5m_returns_do_not_bridge_lunch_or_day() -> None:
    frame = _native(
        [
            "2019-01-02 09:35:00",
            "2019-01-02 09:40:00",
            "2019-01-02 09:45:00",
            "2019-01-02 13:05:00",
            "2019-01-02 13:10:00",
            "2019-01-03 09:35:00",
            "2019-01-03 09:40:00",
        ],
        ["2019-01-02"] * 5 + ["2019-01-03"] * 2,
    )
    ret = r5.build_continuous_returns(frame)
    assert len(ret) == 4
    assert ret["bar_end_shanghai"].dt.strftime("%H:%M").tolist() == ["09:40", "09:45", "13:10", "09:40"]
    # Morning, afternoon and next day are distinct exact-support segments.
    assert ret["segment_id"].nunique() == 3


def test_causal_volatility_excludes_current_return(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(r5, "VOL_WINDOW", 3)
    frame = pd.DataFrame(
        {
            "r": [1.0, 2.0, 3.0, 100.0],
            "segment_id": [1, 1, 1, 1],
            "trading_day": ["2019-01-02"] * 4,
            "bar_end_shanghai": pd.date_range("2019-01-02 09:40", periods=4, freq="5min"),
            "segment_pos": range(4),
            "year": [2019] * 4,
            "role": ["VALIDATION"] * 4,
        }
    )
    out = r5.add_causal_normalization(frame)
    expected = np.sqrt((1.0 + 4.0 + 9.0) / 3.0)
    assert out.loc[3, "sigma_past"] == pytest.approx(expected)
    assert out.loc[3, "z"] == pytest.approx(100.0 / expected)


def test_lag_pair_never_crosses_segment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(r5, "STATE_WINDOW", 5)
    monkeypatch.setattr(r5, "MIN_PAIRS_PER_LAG", 1)
    z = pd.Series([1.0, 1.0, 1.0, -1.0, -1.0])
    segment = pd.Series([1, 1, 1, 2, 2])
    denominator = pd.Series([1.0] * 5)
    _, count = r5._lag_rho_from_past(z, segment, 1, denominator)
    # At index 4, the past includes valid pairs ending at indices 1 and 2.
    # The index-3 pair would cross segment 1 -> 2 and must not be counted.
    assert count.iloc[4] == 2


def test_memory_state_can_represent_short_reversion_longer_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(r5, "STATE_WINDOW", 40)
    monkeypatch.setattr(r5, "SHORT_LAGS", (1,))
    monkeypatch.setattr(r5, "LONG_LAGS", (2,))
    monkeypatch.setattr(r5, "MIN_PAIRS_PER_LAG", 5)
    # Alternating signs have negative lag-1 and positive lag-2 dependence.
    z = np.tile([1.0, -1.0], 60)
    frame = pd.DataFrame(
        {
            "z": z,
            "segment_id": [1] * len(z),
            "r": z,
            "trading_day": ["2019-01-02"] * len(z),
            "bar_end_shanghai": pd.date_range("2019-01-02 09:40", periods=len(z), freq="5min"),
            "segment_pos": range(len(z)),
            "year": [2019] * len(z),
            "role": ["VALIDATION"] * len(z),
        }
    )
    out = r5.add_memory_state(frame)
    available = out.loc[out["state_available"]]
    assert len(available) > 0
    assert (available["short_memory"] < 0.0).all()
    assert (available["long_memory"] > 0.0).all()
    assert available["mixed_state"].all()


def test_parent_and_future_recovery_are_segment_local() -> None:
    n1, n2 = 20, 20
    frame = pd.DataFrame(
        {
            "z": np.arange(n1 + n2, dtype=float) + 1.0,
            "segment_id": [1] * n1 + [2] * n2,
            "role": ["TRAIN"] * (n1 + n2),
            "year": [2018] * (n1 + n2),
        }
    )
    out = r5.add_parent_and_recovery(frame)
    assert np.isnan(out.loc[n1, "parent_drift_12"])
    assert np.isnan(out.loc[n1 - 2, "future_3_z_sum"])
    # Once 12 prior values exist inside segment 2, parent drift becomes available.
    assert np.isfinite(out.loc[n1 + 12, "parent_drift_12"])


def test_R5_B_detects_stronger_reversion_when_anti_persistence_is_high() -> None:
    rng = np.random.default_rng(7)
    n = 1200
    anti = 0.1 + 0.9 * rng.random(n)
    long = 0.05 + 0.1 * rng.random(n)
    z = np.empty(n, dtype=float)
    z[0] = 1.0
    for i in range(n - 1):
        coefficient = 0.10 - 0.55 * anti[i]
        z[i + 1] = coefficient * z[i] + rng.normal(scale=0.35)
    state = pd.DataFrame(
        {
            "z": z,
            "anti_persistence": anti,
            "long_memory": long,
            "short_memory": -anti,
            "state_available": [True] * n,
            "mixed_state": [True] * n,
            "segment_id": [1] * n,
            "year": [2018] * 800 + [2019] * 200 + [2020] * 200,
            "role": ["TRAIN"] * 800 + ["VALIDATION"] * 400,
        }
    )
    result = r5.evaluate_R5_B(state)
    assert result["B1_supported"] is True
    assert result["B1"]["TRAIN_coefficients"][2] < 0.0
    assert result["B1"]["VALIDATION_metrics"]["MSE"] < result["B0"]["VALIDATION_metrics"]["MSE"]
    assert result["B2"]["status"] == "computed_only_because_B1_supported"


def test_load_native_fails_closed_on_post_2020(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    frame = pd.DataFrame(
        {
            "symbol": [r5.SYMBOL, r5.SYMBOL],
            "trading_day": ["2020-12-31", "2021-01-04"],
            "close": [100.0, 101.0],
            "bar_end_shanghai": pd.to_datetime(["2020-12-31 15:00", "2021-01-04 09:35"]),
        }
    )
    path = tmp_path / "x.parquet"
    frame.to_parquet(path, index=False)
    monkeypatch.setattr(r5, "DATA_SHA256", r5.sha256_file(path))
    monkeypatch.setattr(r5, "EXPECTED_ROWS", 2)
    with pytest.raises(RuntimeError, match="escaped"):
        r5.load_native(path)
