from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "run_R6_close_boundary_rejection.py"
SPEC = importlib.util.spec_from_file_location("r6_boundary", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
r6 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = r6
SPEC.loader.exec_module(r6)


def test_breakout_failure_classification_is_symmetric() -> None:
    prior = np.arange(100.0, 112.0)
    assert r6.classify_breakout_failure(prior, 113.0, 111.0) == (1, True)
    assert r6.classify_breakout_failure(prior, 113.0, 112.5) == (1, False)
    assert r6.classify_breakout_failure(prior, 99.0, 100.0) == (-1, True)
    assert r6.classify_breakout_failure(prior, 99.0, 99.5) == (-1, False)
    assert r6.classify_breakout_failure(prior, 105.0, 104.0) is None


def _supported_events() -> pd.DataFrame:
    rows = []
    # TRAIN supply.
    for i in range(120):
        rows.append(("TRAIN", 2018, 1 if i % 2 == 0 else -1, True, -0.30))
    for i in range(220):
        rows.append(("TRAIN", 2018, 1 if i % 2 == 0 else -1, False, 0.10))
    # VALIDATION: each year and each direction independently has enough supply.
    for year in (2019, 2020):
        for direction in (1, -1):
            for _ in range(25):
                rows.append(("VALIDATION", year, direction, True, -0.25))
            for _ in range(50):
                rows.append(("VALIDATION", year, direction, False, 0.05))
    return pd.DataFrame(rows, columns=["role", "year", "direction", "failed", "signed_forward_z3"])


def test_supported_synthetic_effect_passes_all_frozen_gates() -> None:
    result = r6.evaluate(_supported_events())
    assert result["supply_supported"] is True
    assert result["direction_supported"] is True
    assert result["adjudication"] == "R6_supported_for_one_bounded_diagnostic"


def test_direction_failure_does_not_progress() -> None:
    frame = _supported_events()
    frame.loc[frame["failed"], "signed_forward_z3"] = 0.20
    frame.loc[~frame["failed"], "signed_forward_z3"] = -0.10
    result = r6.evaluate(frame)
    assert result["supply_supported"] is True
    assert result["direction_supported"] is False
    assert result["adjudication"] == "R6_direction_not_supported"


def test_supply_failure_does_not_progress() -> None:
    frame = _supported_events().iloc[:80].copy()
    result = r6.evaluate(frame)
    assert result["supply_supported"] is False
    assert result["adjudication"] == "R6_supply_insufficient"
