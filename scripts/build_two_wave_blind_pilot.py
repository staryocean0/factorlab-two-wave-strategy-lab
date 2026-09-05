#!/usr/bin/env python3
"""Package the first preselected baseline window, with no algorithm labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars  # noqa: E402
from factor_lab.visual_structure.two_wave.replay import write_replay_bundle  # noqa: E402


def build_pilot(run_dir: Path, output: Path) -> dict:
    """Use the first saved window by time; never inspect model outcomes."""
    config = json.loads((run_dir / "config.json").read_text())
    windows_path = run_dir / "preselected_review_windows.json"
    windows = json.loads(windows_path.read_text())
    if config["config"]["reversal_log"] != 0.01:
        raise ValueError("The pilot uses the frozen .01 baseline")
    window = min(windows, key=lambda w: (w["start_index"], w["window_id"]))
    view = config["config"]["timeframe"]
    if view != "30m_offset_15":
        raise ValueError("This predeclared pilot uses 30m_offset_15")
    bars, audit = load_development_bars(ROOT / "data/development" / f"{view}.parquet", ROOT / "data/manifest.json")
    end = window["end_index"]
    if not 0 <= window["start_index"] <= end < len(bars):
        raise ValueError("Preselected window outside supplied input")
    # Only the original OHLC/clock rows, config identity, and empty arrays enter
    # a blind document. Neither candidates nor algorithm decisions are embedded.
    empty_export = {**config, "pivots": [], "cycles": [], "structures": [], "events": []}
    output.mkdir(parents=True, exist_ok=True)
    after = 128
    offline_cutoff = min(len(bars) - 1, end + after)
    for name, cutoff in (("pilot_online_blind", end), ("pilot_offline_blind", offline_cutoff)):
        write_replay_bundle(
            output / f"{name}.html",
            [{"name": f"{view} / reversal_log=.01 / {name}", "bars": bars[: cutoff + 1], "export": empty_export}],
        )
    task = {
        "status": "unlabelled_pilot_not_acceptance_sample",
        "selection": "first chronological saved window of 30m_offset_15, baseline .01; no outcomes used",
        "window": window,
        "core_start_utc": bars[window["start_index"]]["timestamp"],
        "core_end_utc": bars[end]["timestamp"],
        "online_max_bar": end,
        "offline_max_bar": offline_cutoff,
        "offline_context_after_bars": offline_cutoff - end,
        "online_future_rows_embedded": 0,
        "algorithm_records_embedded": 0,
        "reference_annotations": [],
        "independent_label_count": 0,
        "preselected_windows_sha256": hashlib.sha256(windows_path.read_bytes()).hexdigest(),
        "source_audit": audit,
        "online_clock": "bar_prefix_ideal_synchronous_not_historical_PIT",
        "completion": "Two independent reviewers per mode; online reviewers must not have seen this interval's future.",
        "scoring_core": "Assign an object by its fifth extremum; earlier four extrema may be in context.",
        "limitation": "One window is a workflow and definition pilot; it cannot satisfy 200-object morphology acceptance.",
    }
    (output / "pilot_task.json").write_text(json.dumps(task, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return task


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "cloud_results/two_wave_continuation/blind_pilot")
    args = parser.parse_args()
    if args.output.resolve() == ROOT or ROOT / "cloud_results" not in args.output.resolve().parents:
        parser.error("--output must be inside this repository's cloud_results/")
    task = build_pilot(args.run_dir, args.output)
    print(json.dumps({k: task[k] for k in ("status", "core_start_utc", "core_end_utc", "online_max_bar", "offline_max_bar")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
