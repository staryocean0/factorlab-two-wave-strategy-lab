import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit_broad_rmr_T1_transitory_shock_supply.py"
spec = importlib.util.spec_from_file_location("t1_supply", SCRIPT)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_frozen_constants():
    assert mod.REFERENCE_BARS == 960
    assert mod.EXTREME_Z == 5.0
    assert mod.MINIMUMS == {"BUILD": 150, "CHECK_2019": 50, "CHECK_2020": 50}


def test_robust_z_uses_only_past_window():
    base = np.tile(np.array([-2.0, -1.0, 1.0, 2.0]), 240)
    values = np.concatenate([base, np.array([20.0, -20.0])])
    z = mod.robust_z_from_past_window(values, 960)
    assert np.isnan(z[:960]).all()
    assert z[960] > 5.0
    # The first extreme can enter the reference set only for the next observation.
    assert np.isfinite(z[961])


def test_within_bar_retrace_fraction_positive_shock():
    native_open = 100.0
    native_close = 108.0
    closes = np.array([102.0, 105.0, 110.0, 109.0, 108.0])
    value = mod.within_bar_retrace_fraction(native_open, native_close, closes)
    assert 0.0 < value < 1.0


def test_within_bar_retrace_fraction_negative_shock():
    native_open = 100.0
    native_close = 92.0
    closes = np.array([98.0, 95.0, 90.0, 91.0, 92.0])
    value = mod.within_bar_retrace_fraction(native_open, native_close, closes)
    assert 0.0 < value < 1.0


def test_monotone_event_has_zero_retrace():
    native_open = 100.0
    native_close = 110.0
    closes = np.array([102.0, 104.0, 106.0, 108.0, 110.0])
    assert mod.within_bar_retrace_fraction(native_open, native_close, closes) == 0.0


def test_alignment_selects_exact_open_interval_close_endpoint():
    day = "2019-01-02"
    times = pd.to_datetime(
        [
            "2019-01-02 09:31:00+08:00",
            "2019-01-02 09:32:00+08:00",
            "2019-01-02 09:33:00+08:00",
            "2019-01-02 09:34:00+08:00",
            "2019-01-02 09:35:00+08:00",
            "2019-01-02 09:36:00+08:00",
        ]
    ).to_numpy(dtype="datetime64[ns]")
    closes = np.array([1, 2, 3, 4, 5, 6], dtype=float)
    index = {day: (times, closes)}
    selected, reason = mod.aligned_one_minute_closes(
        index,
        day=day,
        native_end=pd.Timestamp("2019-01-02 09:35:00+08:00"),
    )
    assert reason is None
    assert selected is not None
    assert selected.tolist() == [1, 2, 3, 4, 5]


def test_partition_boundaries():
    assert mod.partition_for_day("2015-01-05") == "BUILD"
    assert mod.partition_for_day("2018-12-31") == "BUILD"
    assert mod.partition_for_day("2019-01-01") == "CHECK_2019"
    assert mod.partition_for_day("2020-12-31") == "CHECK_2020"
    assert mod.partition_for_day("2021-01-01") is None


def test_runner_contains_no_post_event_outcome_modeling_surface():
    text = SCRIPT.read_text(encoding="utf-8")
    forbidden_code_fragments = [
        "LogisticRegression",
        "brier_score",
        "log_loss",
        "future_return =",
        "reversal_label =",
        "continuation_label =",
        "shift(-",
    ]
    for fragment in forbidden_code_fragments:
        assert fragment not in text
    assert '"post_event_outcomes_read": False' in text
    assert '"outcome_execution_authorized": False' in text
