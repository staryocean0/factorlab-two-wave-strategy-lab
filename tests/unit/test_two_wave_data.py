"""Input contract tests prevent false causal or out-of-scope data evidence."""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from factor_lab.visual_structure.two_wave.data import audit_frame


def frame():
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2015-01-05T02:00Z", "2015-01-05T02:30Z"], utc=True),
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
            "symbol": ["000852.SH"] * 2,
            "trading_day": ["2015-01-05"] * 2,
            "export_view_id": ["30m_offset_15"] * 2,
            "export_frequency": ["30m"] * 2,
            "package_data_role": ["development_material"] * 2,
            "available_at": ["2015-01-05T15:30:00+08:00"] * 2,
            "volume": [None, None],
        }
    )


def test_reports_availability_delay_without_filling_volume():
    original = frame()
    report = audit_frame(original)
    assert report["available_at_after_bar_end_rows"] == 2
    assert report["availability_delay_minutes_quantiles"]["1"] == 330
    assert report["volume_missing_rows"] == 2
    assert report["historical_bar_end_realtime_availability_proven"] is False
    assert original["volume"].isna().all()


@pytest.mark.parametrize("defect", ["duplicate", "out_of_order", "naive", "after_2020", "bad_ohlc", "missing_close", "wrong_role"])
def test_rejects_contract_defects(defect):
    data = frame()
    if defect == "duplicate":
        data.loc[1, "timestamp"] = data.loc[0, "timestamp"]
    elif defect == "out_of_order":
        data = data.iloc[::-1]
    elif defect == "naive":
        data["timestamp"] = data["timestamp"].dt.tz_localize(None)
    elif defect == "after_2020":
        data.loc[1, "trading_day"] = "2021-01-01"
    elif defect == "bad_ohlc":
        data.loc[0, "high"] = 98
    elif defect == "missing_close":
        data.loc[0, "close"] = float("nan")
    else:
        data.loc[0, "package_data_role"] = "fresh_oos"
    with pytest.raises(ValueError):
        audit_frame(data)


def test_preregistered_windows_are_nonoverlapping_and_same_across_scales():
    from factor_lab.visual_structure.two_wave import Config

    workflow_path = Path(__file__).resolve().parents[2] / "scripts/run_two_wave_research.py"
    spec = importlib.util.spec_from_file_location("two_wave_workflow", workflow_path)
    workflow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(workflow)
    bars = [{"trading_day": "2015-01-05"}] * 1000 + [{"trading_day": "2016-01-05"}] * 240
    first = workflow.selected_windows(bars, Config(reversal_log=0.008))
    second = workflow.selected_windows(bars, Config(reversal_log=0.012))

    def bounds(windows):
        return [(w["start_index"], w["end_index"]) for w in windows]

    assert bounds(first) == bounds(second)
    assert len(first) == 3
    assert first[0]["end_index"] - first[0]["start_index"] == 255
    assert first[1]["end_index"] - first[1]["start_index"] == 255
    assert first[0]["end_index"] < first[1]["start_index"]
    assert bounds(first)[2] == (1000, 1239)
    assert all(w["fully_reviewed"] is False for w in first)
