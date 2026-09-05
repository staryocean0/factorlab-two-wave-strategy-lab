#!/usr/bin/env python3
"""Reproduce the H16/W128 supplementary diagnostic inside the repository.

This is descriptive development analysis. It does not recalibrate C1, optimize
P&L, open H1/H2, register a strategy, or create trading authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.candidate_v02 import CandidateConfig  # noqa: E402
from factor_lab.visual_structure.two_wave.data import audit_frame, load_development_bars  # noqa: E402
from factor_lab.visual_structure.two_wave.frequency_v031 import DirectionEngine  # noqa: E402

VIEWS = ["1m_official", *[f"5m_offset_{i}" for i in range(5)]]
HORIZONS = (8, 16, 32, 64)
W = 128
LOW, HIGH = 0.2, 0.6


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def er_series(values: np.ndarray, h: int) -> pd.Series:
    x = pd.Series(np.asarray(values, dtype=float))
    path = x.diff().abs().rolling(h, min_periods=h).sum()
    er = (x - x.shift(h)).abs().div(path)
    er.loc[path.eq(0)] = 0.0
    return er.clip(0, 1)


def dynamics(er: pd.Series) -> pd.DataFrame:
    state = pd.Series(np.where(er <= LOW, 0, np.where(er >= HIGH, 2, 1)), index=er.index, dtype=float)
    state.loc[er.isna()] = np.nan
    pair = state.notna() & state.shift().notna()
    switch = state.ne(state.shift()).astype(float).where(pair)
    direct = (state.sub(state.shift()).abs() == 2).astype(float).where(pair)
    return pd.DataFrame({
        "er": er,
        "local_std128": er.rolling(W, min_periods=W).std(ddof=0),
        "mean_abs_change127": er.diff().abs().rolling(W - 1, min_periods=W - 1).mean(),
        "state_switch127": switch.rolling(W - 1, min_periods=W - 1).mean(),
        "direct_extreme_switch127": direct.rolling(W - 1, min_periods=W - 1).mean(),
        "low_occupancy128": er.le(LOW).astype(float).where(er.notna()).rolling(W, min_periods=W).mean(),
        "high_occupancy128": er.ge(HIGH).astype(float).where(er.notna()).rolling(W, min_periods=W).mean(),
    })


def summarize(frame: pd.DataFrame) -> dict:
    frame = frame.dropna()
    return {"n": len(frame), **{key: {
        "mean": float(frame[key].mean()),
        "median": float(frame[key].median()),
        "p10": float(frame[key].quantile(0.1)),
        "p90": float(frame[key].quantile(0.9)),
    } for key in frame.columns}}


def self_test() -> None:
    rng = np.random.default_rng(123)
    x = np.cumsum(rng.normal(size=1000))
    e = er_series(x, 16)
    for t in (16, 150, 300, 999):
        expected = abs(x[t] - x[t - 16]) / abs(np.diff(x[t - 16:t + 1])).sum()
        assert abs(expected - e.iloc[t]) < 1e-12
    full = dynamics(e)
    for t in (143, 300, 999):
        seq = e.iloc[t - 127:t + 1].to_numpy()
        assert abs(full.local_std128.iloc[t] - np.std(seq, ddof=0)) < 1e-12
        assert abs(full.mean_abs_change127.iloc[t] - np.mean(np.abs(np.diff(seq)))) < 1e-12
    for t in (150, 300, 999):
        pd.testing.assert_frame_equal(dynamics(er_series(x[:t + 1], 16)), full.iloc[:t + 1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="cloud_results/two_wave_H16_W128")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise SystemExit("output directory must be empty")
    output.mkdir(parents=True, exist_ok=True)

    self_test()
    manifest_path = ROOT / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    entries = {Path(item["path"]).name: item for item in manifest["products"]}
    frequency_results, cross = [], []
    source_hashes = {}

    for view in VIEWS:
        path = ROOT / f"data/development/{view}.parquet"
        item = entries[path.name]
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == item["sha256"] and len(raw) == item["file_bytes"]
        source_hashes[path.name] = digest
        frame = pd.read_parquet(path)
        audit_frame(frame)
        days = pd.to_datetime(frame.trading_day.astype(str)).dt.strftime("%Y-%m-%d")
        years = days.str[:4]

        for basis in ("close", "log_close"):
            prices = frame.close.to_numpy(float)
            if basis == "log_close":
                prices = np.log(prices)
            for h in HORIZONS:
                dyn = dynamics(er_series(prices, h))
                frequency_results.append({
                    "view": view,
                    "basis": basis,
                    "H": h,
                    "W": W,
                    "whole_period": summarize(dyn),
                    "annual": {year: summarize(dyn.loc[years == year]) for year in sorted(years.unique())},
                })
                if h == 16 and basis == "close":
                    dyn.assign(day=days).groupby("day").mean().reset_index().to_csv(
                        output / f"{view}_H16_W128_daily.csv", index=False
                    )

        bars, _audit = load_development_bars(path, manifest_path)
        engine = DirectionEngine(CandidateConfig(timeframe=view, reversal_log=0.01, geometry_variant="detrended_width"))
        for bar in bars:
            engine.update(bar)
        dyn16 = dynamics(er_series(frame.close.to_numpy(float), 16))
        joined = []
        for record in engine.records:
            t, a, b = record["confirmation_bar"], record["start_bar"], record["end_bar"]
            joined.append({
                "direction": record["direction_classification"],
                "confirmed_bar": t,
                "completed_two_cycle_return_count": b - a,
                "confirmation_delay_bars": t - b,
                "channel_accepted_by_A": record["channel_accepted_by_A"],
                "ER_whole_two_cycles_log": record["path_er"],
                **dyn16.iloc[t].to_dict(),
            })
        joined_frame = pd.DataFrame(joined)
        joined_frame.to_csv(output / f"{view}_C1_at_confirmation_H16W128.csv", index=False)
        classes = {}
        for label, group in joined_frame.groupby("direction"):
            classes[label] = {
                "n": len(group),
                "channel_A_accepted": int(group.channel_accepted_by_A.sum()),
                "median_completed_two_cycle_return_count": float(group.completed_two_cycle_return_count.median()),
                "p10_completed_two_cycle_return_count": float(group.completed_two_cycle_return_count.quantile(0.1)),
                "p90_completed_two_cycle_return_count": float(group.completed_two_cycle_return_count.quantile(0.9)),
                "median_confirmation_delay_bars": float(group.confirmation_delay_bars.median()),
                "median_ER16_at_confirmation": float(group.er.median()),
                "median_ER_two_cycles_log": float(group.ER_whole_two_cycles_log.median()),
                "mean_std128_at_confirmation": float(group.local_std128.mean()),
            }
        cross.append({"view": view, "scale": 0.01, "C1_class_vs_H16_diagnostic_only": classes})
        print(json.dumps({"view": view, "C1_counts": dict(Counter(r["direction_classification"] for r in engine.records))}), flush=True)

    result = {
        "status": "supplementary_H16_W128_diagnostic_not_recognizer_recalibration",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_range": "2015-01-05 to 2020-12-31, previously used development data",
        "source_data_sha256": source_hashes,
        "external_AI_method_confirmed_by_user": {
            "same_bar_count_across_frequencies": True,
            "primary_H": 16,
            "dynamic_window_ER_observations": 128,
            "sensitivity_H": [8, 16, 32, 64],
        },
        "still_not_identified_from_external_study": [
            "exact historical-versus-recent split dates",
            "high/mid/low ER thresholds",
            "whether high-low switching permits traversal through the middle state",
            "raw-close versus log-close basis",
            "population versus sample standard-deviation convention",
        ],
        "H_interpretation": "H price changes, H+1 closes; H16 plus W128 spans 143 return intervals / 144 closes",
        "definitions": {
            "std": "population standard deviation of last 128 ER observations, ddof=0",
            "mean_abs_change": "127 adjacent absolute ER differences within last 128 observations",
            "state_switch_rate": "adjacent changes among low <= .2, mid (.2,.6), high >= .6 divided by 127",
            "direct_extreme_switch_rate": "adjacent low/high swaps only, no skipping intermediate observations, divided by 127",
            "basis": "raw close primary, log close sensitivity",
            "clock": "continuous supplied bar sequence; gaps are not filled",
        },
        "self_tests": "direct ER oracle, std128, mean-delta127, and prefix identity passed",
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
        "frequency_results": frequency_results,
        "recognizer_cross_diagnostics": cross,
        "recognizer_modified": False,
        "fresh_oos": False,
        "pnl_computed": False,
        "h1_opened": False,
        "production_authority": False,
    }
    write_json(output / "H16_W128_diagnostic.json", result)
    core = {
        **{key: result[key] for key in (
            "status", "generated_at_utc", "source_range", "source_data_sha256",
            "external_AI_method_confirmed_by_user", "still_not_identified_from_external_study",
            "H_interpretation", "definitions", "self_tests", "environment",
            "recognizer_modified", "fresh_oos", "pnl_computed", "h1_opened", "production_authority"
        )},
        "whole_period_close_core_metrics": [{
            "view": row["view"], "H": row["H"], "W": row["W"],
            **{f"{key}_mean": row["whole_period"][key]["mean"] for key in (
                "er", "local_std128", "mean_abs_change127", "state_switch127",
                "direct_extreme_switch127", "low_occupancy128", "high_occupancy128"
            )}
        } for row in frequency_results if row["basis"] == "close"],
        "recognizer_cross_diagnostics": cross,
    }
    write_json(output / "H16_W128_core_summary.json", core)


if __name__ == "__main__":
    main()
