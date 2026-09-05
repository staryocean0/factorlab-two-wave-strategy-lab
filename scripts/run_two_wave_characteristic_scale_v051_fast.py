#!/usr/bin/env python3
"""Run the frozen v0.5.1 formal experiment with an output-equivalent clock optimization."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_two_wave_characteristic_scale_v051 as frozen_runner
from factor_lab.visual_structure.two_wave.characteristic_scale_v051_fast import build_characteristic_run_fast

# The frozen runner owns all metrics, fixed cases, prefix checks, qualification,
# D1 and output schemas.  Only its build function is replaced by a tested
# output-equivalent implementation that precomputes the information clock.
frozen_runner.build_characteristic_run = build_characteristic_run_fast

if __name__ == "__main__":
    frozen_runner.main()
