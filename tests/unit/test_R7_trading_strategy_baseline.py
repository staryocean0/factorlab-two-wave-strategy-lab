from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
SCRIPT = SCRIPTS / "run_R7_trading_strategy_baseline.py"
SPEC = importlib.util.spec_from_file_location("r7_strategy", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def test_position_rule_is_fixed_continuous_clip() -> None:
    x = np.array([-2.0, -1.0, -0.2, 0.0, 0.4, 1.0, 3.0])
    got = mod.position_from_forecast(x)
    np.testing.assert_allclose(got, [-1.0, -1.0, -0.2, 0.0, 0.4, 1.0, 1.0])


def _synthetic_candidates() -> pd.DataFrame:
    rows = []
    # Enough pre-2019 history for a full-rank B1 design.
    for i, day in enumerate(["2018-12-26", "2018-12-27", "2018-12-28", "2018-12-31"]):
        endpoint = [-1.0, -0.2, 0.4, 1.1][i]
        rejection = [0.5, -0.7, 0.9, -0.4][i]
        y = 0.02 + 0.1 * endpoint - 0.5 * rejection
        rows.append((day, "TRAIN", endpoint, rejection, y))
    # Day one is deliberately different so day two's expanding fit may use it,
    # while day one's forecast may not use its own outcomes.
    for day, endpoint, rejection, y in [
        ("2019-01-02", 0.3, 0.8, -0.30),
        ("2019-01-02", -0.4, -0.6, 0.35),
        ("2019-01-03", 0.2, 0.5, -0.10),
    ]:
        rows.append((day, "VALIDATION", endpoint, rejection, y))
    x = pd.DataFrame(rows, columns=["trading_day", "role", "endpoint_z", "rejection_signed_z", "next5_z"])
    x.index = np.arange(100, 100 + len(x))
    return x


def test_daily_expanding_fit_is_strictly_prior_day() -> None:
    x = _synthetic_candidates()
    pred, audit = mod.causal_expanding_forecasts(x)
    first = x.loc[x["trading_day"] == "2019-01-02"]
    beta_pre = mod._fit_b1(x.loc[x["trading_day"] < "2019-01-02"])
    expected = mod.forecast_b1(first, beta_pre)
    np.testing.assert_allclose(pred.loc[first.index].to_numpy(), expected, atol=1e-12)
    assert audit["all_history_max_day_strictly_before_eval_day"] is True
    assert audit["first_day"]["history_max_day"] == "2018-12-31"
    assert audit["last_day"]["history_max_day"] == "2019-01-02"


def test_execution_attachment_uses_next_open_and_t_plus_5_close() -> None:
    tz = "Asia/Shanghai"
    ts = pd.date_range("2019-01-02 10:00", periods=7, freq="1min", tz=tz)
    one = pd.DataFrame({
        "trading_day": ["2019-01-02"] * 7,
        "ts_utc": ts.tz_convert("UTC"),
        "open": [100, 101, 102, 103, 104, 105, 106],
        "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5],
        "causal_flat_fill": [False] * 7,
    })
    candidate = pd.DataFrame({
        "trading_day": ["2019-01-02"],
        "bar_end_shanghai": [str(ts[0])],
        "endpoint_z": [0.0],
        "rejection_signed_z": [0.2],
        "next5_z": [-0.1],
    }, index=[7])
    out = mod.attach_execution_prices(candidate, one)
    assert out.loc[7, "entry_open"] == 101.0
    assert out.loc[7, "window_exit_close"] == 105.5
    assert out.loc[7, "entry_ts_utc"] > out.loc[7, "signal_ts_utc"]
    assert out.loc[7, "execution_flat_fill_touch"] is False or bool(out.loc[7, "execution_flat_fill_touch"]) is False


def test_turnover_contiguous_rebalance_and_gap_flatten_are_exact() -> None:
    tz = "UTC"
    signals = pd.to_datetime([
        "2019-01-02 02:00:00+00:00",
        "2019-01-02 02:05:00+00:00",
        "2019-01-02 05:05:00+00:00",
    ])
    x = pd.DataFrame({
        "trading_day": ["2019-01-02"] * 3,
        "signal_ts_utc": signals,
        "entry_open": [100.0, 101.0, 100.0],
        "window_exit_close": [100.0, 100.0, 100.0],
        "window_underlying_return": [0.0, 0.0, 0.0],
        "_position_input": [0.2, -0.1, 0.3],
    })
    legs = mod.build_strategy_legs(x, x["_position_input"].to_numpy())
    # open .2; contiguous rebalance .3; then close .1 at the gap;
    # new block opens .3 and final close .3.
    np.testing.assert_allclose(legs["turnover"].to_numpy(), [0.2, 0.4, 0.6], atol=1e-12)
    assert legs.loc[1, "contiguous_from_prev"]
    assert not legs.loc[2, "contiguous_from_prev"]
    # During the contiguous close-to-next-open gap, the old +0.2 position is carried.
    np.testing.assert_allclose(legs.loc[1, "gap_carry_return"], 0.2 * (101.0 / 100.0 - 1.0), atol=1e-12)
    assert legs.loc[2, "gap_carry_return"] == 0.0


def test_cost_is_one_way_bps_times_absolute_turnover() -> None:
    x = pd.DataFrame({
        "trading_day": ["2019-01-02", "2019-01-03"],
        "gross_return": [0.01, -0.005],
        "turnover": [0.5, 1.5],
        "position": [0.2, -0.3],
    })
    m0 = mod.performance_metrics(x, 0.0)
    m2 = mod.performance_metrics(x, 2.0)
    assert m0["cumulative_explicit_cost"] == 0.0
    np.testing.assert_allclose(m2["cumulative_explicit_cost"], (0.5 + 1.5) * 2.0 / 10000.0, atol=1e-15)
    assert m2["total_return"] < m0["total_return"]
