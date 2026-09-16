from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "inventory_R7_layer2_5m_risk_state_alignment.py"
SPEC = importlib.util.spec_from_file_location("r7_l2_inventory", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
inv = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = inv
SPEC.loader.exec_module(inv)


def test_transition_preserves_frozen_v9_semantics() -> None:
    assert inv.transition("NORMAL", 2.0, False) == "NORMAL"
    assert inv.transition("NORMAL", 0.8, True) == "UNSAFE"
    assert inv.transition("UNSAFE", 1.5, False) == "UNSAFE"
    assert inv.transition("UNSAFE", 1.2, False) == "RECOVERING"
    assert inv.transition("UNSAFE", 1.1, False) == "NORMAL"
    assert inv.transition("RECOVERING", 1.6, False) == "UNSAFE"
    assert inv.transition("RECOVERING", 1.2, False) == "RECOVERING"
    assert inv.transition("RECOVERING", 1.0, False) == "NORMAL"


def test_transition_missing_ratio_holds_existing_risk_state() -> None:
    assert inv.transition("UNSAFE", np.nan, False) == "UNSAFE"
    assert inv.transition("RECOVERING", np.nan, False) == "RECOVERING"
    assert inv.transition("NORMAL", np.nan, False) == "NORMAL"


def _days(n_days: int = 3) -> pd.DataFrame:
    rows = []
    price = 100.0
    for d in range(n_days):
        day = f"2020-01-{d + 2:02d}"
        for k in range(48):
            price *= np.exp(0.0002 * np.sin(k / 3.0))
            rows.append(("000852.SH", day, f"{day} {9 + (k * 5 + 30) // 60:02d}:{(k * 5 + 30) % 60:02d}:00", price))
    return pd.DataFrame(rows, columns=["symbol", "trading_day", "timestamp", "close"])


def test_finalized_replay_has_fixed_bucket_mapping() -> None:
    x = _days(4)
    out, meta = inv.finalized_state_replay(x)
    assert meta["complete_48bar_days"] == 4
    assert set(out["risk_state"]).issubset({"NORMAL", "UNSAFE", "RECOVERING"})
    assert set(out.loc[out["risk_state"].eq("NORMAL"), "risk_bucket"]) <= {"LOW_RISK"}
    assert set(out.loc[out["risk_state"].isin({"UNSAFE", "RECOVERING"}), "risk_bucket"]) <= {"RISK_ACTIVE"}


def test_incomplete_day_is_excluded_not_filled() -> None:
    x = _days(3)
    partial_day = x["trading_day"].unique()[1]
    x = x.loc[~((x["trading_day"] == partial_day) & x["timestamp"].str.contains("10:00:00"))].copy()
    out, meta = inv.finalized_state_replay(x)
    assert meta["excluded_incomplete_days"] == 1
    assert partial_day in meta["excluded_day_labels"]
    assert partial_day not in set(out["trading_day"])
