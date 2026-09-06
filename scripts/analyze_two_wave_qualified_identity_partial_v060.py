#!/usr/bin/env python3
"""Partial v0.6.0 audit from already-completed frozen artifacts.

This script intentionally does not adjudicate Route Q/U/M because the formal
v0.5.4 per-view artifacts serialized full qualified record bodies only for the
main-view diagnostic line, while native offset artifacts retained counts and
legacy-selected coverage. It extracts every claim that is valid without
re-running the recognizer or inventing missing qualified records.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.morphology_identity_v060 import (
    canonicalize_qualified_records,
)


def load(path: Path):
    return json.loads(path.read_text())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v054-final", type=Path, required=True)
    ap.add_argument("--v055-main-qualified", type=Path, required=True)
    ap.add_argument("--v057b-pairs", type=Path, required=True)
    ap.add_argument("--v058-pairs", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    v054 = load(args.v054_final)
    qmain = load(args.v055_main_qualified)
    geom = load(args.v057b_pairs)["rows"]
    paw = load(args.v058_pairs)["rows"]
    paw_by_key = {
        (r["view"], r["main_record_id"], r["other_record_id"]): r for r in paw
    }
    if len(paw_by_key) != len(paw):
        raise AssertionError("v0.5.8 pair key collision")

    per_view = {}
    suppression = []
    for view in sorted(v054["views"]):
        row = v054["views"][view]
        qualified = int(row["v054"]["qualified"])
        selected = int(row["v054"]["selected_disjoint"])
        frac = (qualified - selected) / qualified
        suppression.append(frac)
        per_view[view] = {
            "qualified_records": qualified,
            "legacy_selected_records": selected,
            "packing_suppressed_records": qualified - selected,
            "packing_suppressed_fraction": frac,
            "upstream_prefix_checks": len(row["prefix_checks"]),
            "upstream_prefix_checks_all_passed": all(
                x["passed"] and x["confirmed_rewrite_count"] == 0
                for x in row["prefix_checks"]
            ),
        }

    canonical = canonicalize_qualified_records(qmain)
    main_identity = {
        "qualified_records": len(qmain),
        "canonical_financial_identities": len(canonical),
        "duplicate_scale_evidence_groups": sum(x["member_count"] > 1 for x in canonical),
        "records_in_duplicate_scale_groups": sum(
            x["member_count"] for x in canonical if x["member_count"] > 1
        ),
        "max_scale_evidence_members": max(x["member_count"] for x in canonical),
        "canonical_with_any_legacy_selected_member": sum(x["selected_any"] for x in canonical),
        "canonical_hidden_by_legacy_packing": sum(not x["selected_any"] for x in canonical),
        "canonical_hidden_fraction": sum(not x["selected_any"] for x in canonical) / len(canonical),
    }

    selected_strict = {}
    for view in sorted({r["view"] for r in geom}):
        all_rows = [r for r in geom if r["view"] == view]
        strict = [
            r
            for r in all_rows
            if bool(r["phase_match"])
            and max(float(x) for x in r["occurrence_timestamp_abs_delta_minutes"]) <= 5.0
        ]
        bars = sum(int(r["bars"]) for r in all_rows)
        sbars = sum(int(r["bars"]) for r in strict)
        d1_same = sum(int(r["bars"]) for r in strict if r["main_D1"] == r["other_D1"])
        d2_same = sum(int(r["bars"]) for r in strict if r["main_D2"] == r["other_D2"])
        direct_d1 = sum(
            int(r["bars"])
            for r in strict
            if {r["main_D1"], r["other_D1"]} == {"uptrend", "downtrend"}
        )
        direct_d2 = sum(
            int(r["bars"])
            for r in strict
            if {r["main_D2"], r["other_D2"]} == {"uptrend", "downtrend"}
        )
        lm = 0
        for r in strict:
            p = paw_by_key[(r["view"], r["main_record_id"], r["other_record_id"])]
            if bool(p["large_margin_scalar_sign_flip"]):
                lm += int(r["bars"])
        selected_strict[view] = {
            "all_selected_ownership_pairs": len(all_rows),
            "all_selected_ownership_bars": bars,
            "strict_same_event_pairs": len(strict),
            "strict_same_event_bars": sbars,
            "strict_same_event_bar_fraction_of_ownership_pairs": sbars / bars,
            "D1_same_label_fraction": d1_same / sbars,
            "D2_same_label_fraction": d2_same / sbars,
            "D1_direct_up_down_reversal_fraction": direct_d1 / sbars,
            "D2_direct_up_down_reversal_fraction": direct_d2 / sbars,
            "PAWCT_large_margin_flip_bars": lm,
            "PAWCT_large_margin_flip_fraction": lm / sbars,
        }

    result = {
        "schema": "two_wave_qualified_identity_partial_audit@0.6.0",
        "status": "partial_evidence_generated_route_Q_U_M_not_adjudicated",
        "sources": {
            "v054_formal_five_view_run": 33998425000,
            "v054_formal_final_artifact": 9978815239,
            "v057b_formal_run": 34010814782,
            "v058_formal_run": 34011528190,
        },
        "upstream_native5m_prefix_zero_rewrite": int(v054["prefix_zero_rewrite_count"]),
        "per_view_packing": per_view,
        "packing_suppression_fraction_mean": statistics.mean(suppression),
        "packing_suppression_fraction_min": min(suppression),
        "packing_suppression_fraction_max": max(suppression),
        "main_view_canonicalization_with_v060_helper": main_identity,
        "legacy_selected_strict_same_event_diagnostic": selected_strict,
        "missing_for_formal_v060_route_adjudication": [
            "full v0.5.4 qualified record bodies for 5m_offset_1..4",
            "cross-view mutual-unique matching over all canonical qualified identities",
            "derived v0.6.0 identity-event replay on those four full qualified streams",
        ],
        "research_conclusion": (
            "exclusive packing is a material five-view morphology-layer contaminant, "
            "but Route Q/U/M remains intentionally unadjudicated until full qualified "
            "cross-view identity bodies are available"
        ),
        "future_outcome_used": False,
        "trade_authority": False,
        "operational_baseline": "v0.4.3",
        "morphology_status": "morphology_replication_not_yet_accepted",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
