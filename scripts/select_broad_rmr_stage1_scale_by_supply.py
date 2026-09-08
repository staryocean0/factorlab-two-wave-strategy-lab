#!/usr/bin/env python3
"""Outcome-blind M0 representation-scale supply inventory/selector.

Reads only structural publication identity fields and trading-day labels from the
preexisting 5m view. No OHLC/price/path outcome values are loaded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cloud_inputs/frozen_research_cache_v065_v0613/published_identities_v065.parquet"
BARS = ROOT / "data/development/5m_offset_0.parquet"
EXPECTED_CACHE_SHA = "8596622924e92182756162b7bdf0959f6d8ddc2222d6dbc9b4e4379cada9974c"
EXPECTED_BARS_SHA = "bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48"
VIEW = "5m_offset_0"
BUILD_END = "2018-12-31"
CHECK_2019_END = "2019-12-31"
CHECK_2020_END = "2020-12-31"
MIN_BUILD = 300
MIN_YEAR = 75


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sigma(level: int) -> float:
    return 0.5 * math.sqrt(2.0) ** int(level)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    if sha256(CACHE) != EXPECTED_CACHE_SHA:
        raise RuntimeError("published identity cache SHA drift")
    if sha256(BARS) != EXPECTED_BARS_SHA:
        raise RuntimeError("5m_offset_0 SHA drift")

    identities = pd.read_parquet(
        CACHE,
        columns=["view", "publishing_birth_level", "publishing_birth_confirmation_bar"],
        filters=[("view", "==", VIEW)],
    )
    bars = pd.read_parquet(BARS, columns=["trading_day"])
    bars["trading_day"] = bars["trading_day"].astype(str)
    if identities.empty:
        raise RuntimeError("no primary-view published identities")

    idx = identities["publishing_birth_confirmation_bar"].astype(int)
    if idx.min() < 0 or idx.max() >= len(bars):
        raise RuntimeError("publication confirmation index outside primary view")
    identities = identities.copy()
    identities["day"] = bars.iloc[idx.to_numpy()]["trading_day"].to_numpy()
    identities["level"] = identities["publishing_birth_level"].astype(int)

    rows = []
    levels = sorted(int(x) for x in identities["level"].unique())
    level_set = set(levels)
    for level in levels:
        p = identities.loc[identities["level"].eq(level)]
        counts = {
            "BUILD_2015_2018": int((p["day"] <= BUILD_END).sum()),
            "CHECK_2019": int(((p["day"] > BUILD_END) & (p["day"] <= CHECK_2019_END)).sum()),
            "CHECK_2020": int(((p["day"] > CHECK_2019_END) & (p["day"] <= CHECK_2020_END)).sum()),
        }
        finer = level - 1
        f = identities.loc[identities["level"].eq(finer)] if finer in level_set else identities.iloc[0:0]
        finer_counts = {
            "BUILD_2015_2018": int((f["day"] <= BUILD_END).sum()),
            "CHECK_2019": int(((f["day"] > BUILD_END) & (f["day"] <= CHECK_2019_END)).sum()),
            "CHECK_2020": int(((f["day"] > CHECK_2019_END) & (f["day"] <= CHECK_2020_END)).sum()),
        }
        parent_ok = counts["BUILD_2015_2018"] >= MIN_BUILD and counts["CHECK_2019"] >= MIN_YEAR and counts["CHECK_2020"] >= MIN_YEAR
        finer_ok = finer in level_set and finer_counts["BUILD_2015_2018"] >= MIN_BUILD and finer_counts["CHECK_2019"] >= MIN_YEAR and finer_counts["CHECK_2020"] >= MIN_YEAR
        rows.append({
            "parent_level": level,
            "parent_sigma_bars": sigma(level),
            "finer_level": finer,
            "finer_sigma_bars": sigma(finer) if finer >= 0 else None,
            "parent_counts": counts,
            "finer_counts": finer_counts,
            "parent_supply_gate": bool(parent_ok),
            "finer_supply_gate": bool(finer_ok),
            "eligible": bool(parent_ok and finer_ok),
        })

    eligible = [r for r in rows if r["eligible"]]
    selected = min((r["parent_level"] for r in eligible), default=None)
    payload = {
        "schema_id": "factorlab_broad_rmr_stage1_scale_supply_selection@1.0",
        "research_role": "outcome_blind_structural_supply_only",
        "primary_view": VIEW,
        "price_columns_read": False,
        "future_price_outcomes_read": False,
        "build": "2015-01-05_to_2018-12-31_consumed_development",
        "check": "2019_and_2020_not_fresh",
        "minimum_build_publications_each_level": MIN_BUILD,
        "minimum_publications_each_check_year_each_level": MIN_YEAR,
        "selection_rule": "smallest_parent_level_with_supply_gate_for_parent_and_adjacent_finer_level",
        "inventory": rows,
        "selected_parent_level": selected,
        "selected_parent_sigma_bars": None if selected is None else sigma(selected),
        "selected_finer_level": None if selected is None else selected - 1,
        "selected_finer_sigma_bars": None if selected is None else sigma(selected - 1),
        "selection_status": "selected" if selected is not None else "evidence_supply_insufficient_fail_closed",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ["selection_status", "selected_parent_level", "selected_parent_sigma_bars", "selected_finer_level", "selected_finer_sigma_bars"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
