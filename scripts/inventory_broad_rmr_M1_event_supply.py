#!/usr/bin/env python3
"""M1 event-supply-only inventory for broad R1/R2.

Reads causal parent structures and contemporaneous 5m closes only to determine
whether/when the preregistered M1 trigger occurs. It never inspects price action
after an event trigger and never constructs recovery/failure/reentry outcomes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_broad_rmr_stage1_R1_R2_R3 as base

ADAPTER = ROOT / "docs/governance/reversal_mean_reversion_M1_single_shock_event_adapter_v1.json"
SHOCK_FRACTION = 0.5


def find_r1_trigger(logp: np.ndarray, parent: base.Geo, end: int):
    extreme = float(logp[parent.conf])
    for j in range(parent.conf + 1, min(end, len(logp) - 1) + 1):
        x = float(logp[j])
        if parent.direction > 0:
            if x <= parent.failure:
                return None, "parent_failure_before_trigger"
            extreme = max(extreme, x)
            move = extreme - x
            if move >= SHOCK_FRACTION * parent.amp:
                return {
                    "event_idx": j,
                    "severity": float(move / parent.amp),
                    "recovery_boundary": extreme,
                    "failure_boundary": parent.failure,
                }, "triggered"
        else:
            if x >= parent.failure:
                return None, "parent_failure_before_trigger"
            extreme = min(extreme, x)
            move = x - extreme
            if move >= SHOCK_FRACTION * parent.amp:
                return {
                    "event_idx": j,
                    "severity": float(move / parent.amp),
                    "recovery_boundary": extreme,
                    "failure_boundary": parent.failure,
                }, "triggered"
    return None, "no_trigger_before_expiry"


def find_r2_trigger(logp: np.ndarray, parent: base.Geo, end: int):
    for j in range(parent.conf + 1, min(end, len(logp) - 1) + 1):
        x = float(logp[j])
        if x > parent.high:
            dist = x - parent.high
            return {
                "event_idx": j,
                "side": 1,
                "severity": float(dist / (parent.high - parent.low)),
                "edge": parent.high,
                "outside_distance": float(dist),
            }
        if x < parent.low:
            dist = parent.low - x
            return {
                "event_idx": j,
                "side": -1,
                "severity": float(dist / (parent.high - parent.low)),
                "edge": parent.low,
                "outside_distance": float(dist),
            }
    return None


def role_counts(events: list[dict]) -> dict:
    out = {"BUILD_2015_2018": 0, "CHECK_2019": 0, "CHECK_2020": 0}
    for e in events:
        day = e["day"]
        if day <= "2018-12-31": out["BUILD_2015_2018"] += 1
        elif day <= "2019-12-31": out["CHECK_2019"] += 1
        elif day <= "2020-12-31": out["CHECK_2020"] += 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    cfg = json.loads(ADAPTER.read_text(encoding="utf-8"))
    if cfg["M1_S0_supply_only"]["post_event_outcomes_read"] is not False:
        raise RuntimeError("M1 S0 outcome boundary drifted")
    if cfg["R1_single_counter_shock"]["shock_threshold"] != "0.5_times_parent_amplitude_scale":
        raise RuntimeError("M1 shock threshold drifted")

    x, bars, _, _ = base.load_inputs()
    geos, logp, days = base.build_geos(x, bars)
    parents = geos[base.PARENT_LEVEL]
    expiries = base.parent_expiries(parents)
    year_end = base.year_end_indices(days)

    r1_events = []
    r1_reasons = {"triggered": 0, "parent_failure_before_trigger": 0, "no_trigger_before_expiry": 0}
    r2_events = []
    for parent in parents:
        year = int(parent.day[:4])
        end = min(expiries[parent.ident], year_end[year])

        r1, reason = find_r1_trigger(logp, parent, end)
        r1_reasons[reason] += 1
        if r1 is not None:
            j = int(r1["event_idx"])
            event = float(logp[j])
            if parent.direction > 0:
                valid = parent.failure < event < r1["recovery_boundary"]
            else:
                valid = r1["recovery_boundary"] < event < parent.failure
            if valid:
                r1_events.append({"day": str(days[j]), "event_idx": j, "severity": r1["severity"]})

        r2 = find_r2_trigger(logp, parent, end)
        if r2 is not None and parent.high > parent.low:
            j = int(r2["event_idx"])
            r2_events.append({"day": str(days[j]), "event_idx": j, "severity": r2["severity"], "side": r2["side"]})

    r1_counts = role_counts(r1_events)
    r2_counts = role_counts(r2_events)
    r1_gate = r1_counts["BUILD_2015_2018"] >= 150 and r1_counts["CHECK_2019"] >= 50 and r1_counts["CHECK_2020"] >= 50
    r2_gate = r2_counts["BUILD_2015_2018"] >= 150 and r2_counts["CHECK_2019"] >= 50 and r2_counts["CHECK_2020"] >= 50

    payload = {
        "schema_id": "factorlab_broad_rmr_M1_event_supply_receipt@1.0",
        "session_date": "2026-09-08",
        "program_identity": "broad_reversal_mean_reversion_discovery_program_v1",
        "measurement_identity": "M1_parent_structure_plus_single_shock_event_adapter_v1",
        "research_role": "event_supply_only_no_post_event_outcome",
        "price_values_read_only_through_event_trigger": True,
        "post_event_outcomes_read": False,
        "post_2020_rows_read": False,
        "parent_level": 5,
        "primary_view": "5m_offset_0",
        "R1": {
            "shock_fraction": SHOCK_FRACTION,
            "counts": r1_counts,
            "supply_gate_passed": bool(r1_gate),
            "trigger_scan_reasons": r1_reasons,
        },
        "R2": {
            "additional_excursion_threshold": None,
            "counts": r2_counts,
            "supply_gate_passed": bool(r2_gate),
        },
        "outcome_screen_authorized_by_supply": {
            "R1": bool(r1_gate),
            "R2": bool(r2_gate),
        },
        "scientifically_fresh": False,
        "trading_PnL_used": False,
        "production_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"R1_counts": r1_counts, "R1_supply": r1_gate, "R2_counts": r2_counts, "R2_supply": r2_gate}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
