#!/usr/bin/env python3
"""Reproducible implementation examples; never evidence of a market advantage."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from factor_lab.visual_structure.two_wave import Config, run_bars


def scenarios() -> dict[str, np.ndarray]:
    t = np.arange(361, dtype=float)
    phase = 2 * np.pi * t / 60
    rng = np.random.default_rng(20260905)
    platform = 0.025 * np.sin(phase)
    platform[120:160] = platform[120]
    return {
        "horizontal": 0.025 * np.sin(phase),
        "upward_drift": 0.00045 * t + 0.025 * np.sin(phase),
        "downward_drift": -0.00045 * t + 0.025 * np.sin(phase),
        "strong_drift_no_reversals": 0.003 * t + 0.025 * np.sin(phase),
        "amplitude_step": np.where(t < 180, 0.025, 0.06) * np.sin(phase),
        "frequency_change": 0.025 * np.sin(np.where(t < 180, phase, 6 * np.pi + (t - 180) * 2 * np.pi / 30)),
        "converging": (0.05 - 0.00012 * t) * np.sin(phase),
        "expanding": (0.009 + 0.00012 * t) * np.sin(phase),
        "single_jump": 0.025 * np.sin(phase) + np.where(t < 170, 0, 0.07),
        "long_platform": platform,
        "constant": t * 0,
        "mixed_scale_noise": 0.025 * np.sin(phase) + 0.002 * np.sin(2 * np.pi * t / 7) + rng.normal(0, 0.00015, len(t)),
    }


def build(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(4, 3, figsize=(16, 13), constrained_layout=True)
    reports = []
    base = datetime(2018, 1, 2, tzinfo=UTC)
    for (name, x), ax in zip(scenarios().items(), axes.flat, strict=True):
        bars = []
        for i, value in enumerate(x):
            close = float(100 * np.exp(value))
            bars.append(
                {"timestamp": (base + timedelta(minutes=i)).isoformat(), "open": close, "high": close, "low": close, "close": close}
            )
        cfg = Config(instrument="SYNTHETIC", timeframe="synthetic_1bar", reversal_log=0.01)
        result = run_bars(bars, cfg).export()
        counts = Counter(s["classification"] for s in result["structures"])
        reports.append(
            {
                "scenario": name,
                "bars": len(bars),
                "confirmed_pivots": len(result["pivots"]),
                "cycles": len(result["cycles"]),
                "structures": len(result["structures"]),
                "classifications": dict(counts),
                "attributes": dict(Counter(a for s in result["structures"] for a in s["attributes"])),
                "expected_no_structure": name in ("constant", "strong_drift_no_reversals"),
                "source": "deterministic_synthetic_implementation_check_not_market_evidence",
            }
        )
        (output / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")))
        ax.plot(x, color="#29456a", linewidth=1)
        for kind, marker, color in [("high", "^", "#db704b"), ("low", "v", "#377f74")]:
            pivots = [p for p in result["pivots"] if p["kind"] == kind and not p["left_censored"]]
            ax.scatter(
                [p["occurrence_bar"] for p in pivots], [x[p["occurrence_bar"]] for p in pivots], marker=marker, color=color, s=17, zorder=4
            )
        for pivot in result["pivots"]:
            if not pivot["left_censored"]:
                ax.plot(
                    [pivot["occurrence_bar"], pivot["confirmation_bar"]],
                    [x[pivot["occurrence_bar"]]] * 2,
                    color="#888888",
                    alpha=0.45,
                    linewidth=0.6,
                )
        ax.set_title(name + "\n" + str(dict(counts)), fontsize=9, loc="left")
        ax.set_xlabel("bar ordinal", fontsize=8)
        ax.set_ylabel("log price / initial price", fontsize=8)
        ax.grid(alpha=0.16)
        ax.tick_params(labelsize=7)
    fig.suptitle(
        "Two-wave recognizer: synthetic implementation gallery\n"
        "Extrema markers are retrospective; horizontal whiskers end at confirmation. No market-law evidence.",
        fontsize=13,
    )
    fig.savefig(output / "synthetic_gallery.svg")
    fig.savefig(output / "synthetic_gallery.png", dpi=120)
    plt.close(fig)
    report = {
        "schema_version": "two_wave_synthetic_gallery@1.0",
        "scenario_count": len(reports),
        "morphology_status": "morphology_replication_not_yet_accepted",
        "scenarios": reports,
    }
    (output / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("cloud_results/two_wave_synthetic"))
    print(json.dumps(build(parser.parse_args().output), ensure_ascii=False, indent=2))
