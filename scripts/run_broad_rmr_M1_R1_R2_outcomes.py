#!/usr/bin/env python3
"""Frozen M1 R1/R2 outcome screen.

This runner is authorized only because M1-S0 supply gates passed without reading
post-trigger outcomes. It reuses the exact frozen M1 triggers and parent geometry,
then constructs only the preregistered first-passage outcomes through 2020.
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
import inventory_broad_rmr_M1_event_supply as m1

PROTOCOL = ROOT / "docs/governance/reversal_mean_reversion_M1_R1_R2_outcome_protocol_v1.json"
SUPPLY_RECEIPT = ROOT / "docs/research/cloud_session_20260908_broad_rmr_M1_S0_event_supply_receipt_v1.json"
MAX_POST = 96


def validate_contracts() -> tuple[dict, dict]:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    supply = json.loads(SUPPLY_RECEIPT.read_text(encoding="utf-8"))
    if protocol["stage"] != "outcome_protocol_frozen_after_supply_pass_before_post_trigger_first_passage_read":
        raise RuntimeError("M1 outcome protocol stage drifted")
    if not protocol["supply_gate"]["R1_passed"] or not protocol["supply_gate"]["R2_passed"]:
        raise RuntimeError("M1 outcome run lacks supply authorization")
    if not supply["outcome_screen_authorized_by_supply"]["R1"] or not supply["outcome_screen_authorized_by_supply"]["R2"]:
        raise RuntimeError("persisted M1 supply receipt does not authorize both lanes")
    if protocol["R1"]["shock_fraction"] != m1.SHOCK_FRACTION:
        raise RuntimeError("M1 R1 shock fraction drifted")
    if protocol["R2"]["additional_excursion_threshold"] is not None:
        raise RuntimeError("M1 R2 excursion threshold drifted")
    if protocol["source"]["post_2020_open"] is not False:
        raise RuntimeError("post-2020 unexpectedly authorized")
    return protocol, supply


def r1_outcomes(parents, logp: np.ndarray, days: np.ndarray, year_end: dict[int, int]):
    expiries = base.parent_expiries(parents)
    rows = []
    trigger_reasons = {"triggered": 0, "parent_failure_before_trigger": 0, "no_trigger_before_expiry": 0}
    for parent in parents:
        state_end = min(expiries[parent.ident], year_end[int(parent.day[:4])])
        trigger, reason = m1.find_r1_trigger(logp, parent, state_end)
        trigger_reasons[reason] += 1
        if trigger is None:
            continue
        j = int(trigger["event_idx"])
        event = float(logp[j])
        recovery = float(trigger["recovery_boundary"])
        failure = float(parent.failure)
        if parent.direction > 0:
            if not (failure < event < recovery):
                continue
            upper, lower = recovery, failure
            upper_label, lower_label = "recovery", "failure"
        else:
            if not (recovery < event < failure):
                continue
            upper, lower = failure, recovery
            upper_label, lower_label = "failure", "recovery"
        outcome_end = min(state_end, j + MAX_POST)
        outcome, resolved = base.first_passage(
            logp, j, outcome_end, upper, lower, upper_label, lower_label
        )
        rows.append(
            {
                "day": str(days[j]),
                "severity": float(trigger["severity"]),
                "abs_drift": parent.abs_drift,
                "overlap": parent.overlap,
                "parent_eff": parent.eff,
                "outcome": outcome,
                "resolve_idx": int(resolved),
            }
        )
    return base.pd.DataFrame(rows), trigger_reasons


def r2_outcomes(parents, logp: np.ndarray, days: np.ndarray, year_end: dict[int, int]):
    expiries = base.parent_expiries(parents)
    rows = []
    for parent in parents:
        state_end = min(expiries[parent.ident], year_end[int(parent.day[:4])])
        trigger = m1.find_r2_trigger(logp, parent, state_end)
        if trigger is None:
            continue
        j = int(trigger["event_idx"])
        event = float(logp[j])
        side = int(trigger["side"])
        edge = float(trigger["edge"])
        dist = float(trigger["outside_distance"])
        continuation = event + side * dist
        if side > 0:
            upper, lower = continuation, edge
            upper_label, lower_label = "continuation", "reentry"
        else:
            upper, lower = edge, continuation
            upper_label, lower_label = "reentry", "continuation"
        outcome_end = min(state_end, j + MAX_POST)
        outcome, resolved = base.first_passage(
            logp, j, outcome_end, upper, lower, upper_label, lower_label
        )
        rows.append(
            {
                "day": str(days[j]),
                "severity": float(trigger["severity"]),
                "abs_drift": parent.abs_drift,
                "overlap": parent.overlap,
                "parent_eff": parent.eff,
                "outcome": outcome,
                "resolve_idx": int(resolved),
            }
        )
    return base.pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    validate_contracts()
    identities, bars, _, _ = base.load_inputs()
    geos, logp, days = base.build_geos(identities, bars)
    parents = geos[base.PARENT_LEVEL]
    year_end = base.year_end_indices(days)

    r1_events, trigger_reasons = r1_outcomes(parents, logp, days, year_end)
    r2_events = r2_outcomes(parents, logp, days, year_end)

    r1_models = {
        "severity_only": ["severity"],
        "parent_integrity_only": ["abs_drift", "overlap", "parent_eff"],
        "parent_plus_severity": ["severity", "abs_drift", "overlap", "parent_eff"],
    }
    r2_models = {
        "excursion_severity_only": ["severity"],
        "parent_range_state_only": ["abs_drift", "overlap", "parent_eff"],
        "parent_plus_excursion_state": ["severity", "abs_drift", "overlap", "parent_eff"],
    }

    r1_result, r1_fit = base.evaluate_lane(r1_events, r1_models, "recovery", "failure")
    r1_gates, r1_projection = base.gate_r1(r1_result, r1_fit["parent_plus_severity"])
    r2_result, r2_fit = base.evaluate_lane(r2_events, r2_models, "reentry", "continuation")
    r2_gates, r2_projection = base.gate_r2(r2_result, r2_fit["parent_plus_excursion_state"])

    payload = {
        "schema_id": "factorlab_broad_rmr_M1_R1_R2_outcome_receipt@1.0",
        "session_date": "2026-09-08",
        "program_identity": "broad_reversal_mean_reversion_discovery_program_v1",
        "measurement_identity": "M1_parent_structure_plus_single_shock_event_adapter_v1",
        "code_commit": base.git_head(),
        "source": {
            "structure_cache_sha256": base.CACHE_SHA,
            "price_view_sha256": base.BARS_SHA,
            "max_day": str(bars.trading_day.max()),
            "post_2020_rows_read": False,
        },
        "parent": {"view": "5m_offset_0", "birth_level": 5},
        "R1": {
            "trigger_scan_reasons": trigger_reasons,
            "result": r1_result,
            "integrity_projection": r1_projection,
            "gates": r1_gates,
            "progression_worthy": bool(all(r1_gates.values())),
        },
        "R2": {
            "result": r2_result,
            "range_projection": r2_projection,
            "gates": r2_gates,
            "progression_worthy": bool(all(r2_gates.values())),
        },
        "R3_reopened": False,
        "shock_fraction_search_performed": False,
        "excursion_threshold_search_performed": False,
        "parent_scale_or_offset_search_performed": False,
        "scientifically_fresh": False,
        "morphology_replication_accepted": False,
        "trading_PnL_used": False,
        "production_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "R1_progression": payload["R1"]["progression_worthy"],
                "R2_progression": payload["R2"]["progression_worthy"],
                "R3_reopened": False,
                "post_2020_rows_read": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
