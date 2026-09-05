#!/usr/bin/env python3
"""Render the exact parallel-channel counterexample and descriptive flag audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.diagnostics.read_text())["overall"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={"width_ratios": [1.25, 1]})
    t = np.array([0, 1, 2, 18, 19])
    y = .001 * t + .02 * (np.arange(5) % 2)
    axis = axes[0]
    axis.plot(t, y, color="#2563eb", lw=2.3, marker="o", zorder=3)
    axis.plot([0, 19], [0, .019], "--", color="#8b8b8b", lw=1.4)
    axis.plot([0, 19], [.02, .039], "--", color="#8b8b8b", lw=1.4)
    for i, (x, value) in enumerate(zip(t, y, strict=True)):
        axis.annotate(f"P{i}", (x, value), xytext=(0, 8 if i % 2 else -15), textcoords="offset points", ha="center")
    axis.text(9, .005, "Same slope: 0.001 / bar\nConstant width: 0.020\nE = 0, D = 0.95", fontsize=10,
              bbox={"facecolor": "white", "edgecolor": "#dddddd", "pad": 7})
    axis.set(title="Exact synthetic parallel channel", xlabel="Bar index", ylabel="Log price minus 8")
    axis.set_xlim(-1, 20)
    axis.set_ylim(-.005, .046)
    axis.text(.01, -.26, "Raw cycle ranges: 0.021 and 0.036\nRatio = 12/7 > 1.6: frozen rule rejects this channel.",
              transform=axis.transAxes, fontsize=10)
    removal = data["single_rule_removals"]
    values = [data["clear_fraction"], removal["cycle_amplitude_change"]["clear_fraction_if_flags_removed"],
              removal["uneven_phase_drift"]["clear_fraction_if_flags_removed"],
              data["group_removals"]["local_drift_and_cycle_amplitude"]["clear_fraction_if_flags_removed"]]
    names = ["Frozen v0.1", "Ignore raw amplitude flag", "Ignore uneven drift flag", "Ignore both flags"]
    axis = axes[1]
    axis.barh(names, np.array(values) * 100, color=["#1e3a5f", "#94a3b8", "#94a3b8", "#94a3b8"], height=.52)
    for i, value in enumerate(values):
        axis.text(value * 100 + .25, i, f"{value:.2%}", va="center", fontsize=10)
    axis.invert_yaxis()
    axis.set_xlim(0, max(values) * 100 + 3)
    axis.set(title=f"{data['structures']:,} correlated candidates, 6 views", xlabel="Clear classifications (%)")
    axis.text(0, -.26, "Boolean flag accounting only. No model was changed.\nThese percentages are not accuracy or validation.",
              transform=axis.transAxes, fontsize=10)
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="x", alpha=.13)
        axis.set_axisbelow(True)
    fig.subplots_adjust(left=.075, right=.965, top=.90, bottom=.25, wspace=.68)
    args.output.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output / "two_wave_diagnostic.png", dpi=180)
    fig.savefig(args.output / "two_wave_diagnostic.svg")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
