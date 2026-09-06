#!/usr/bin/env python3
"""Local-only v0.6.0 audit: qualified financial identity vs legacy packing.

No GitHub Actions are required. This script replays only the supplied frozen
5m development views and never uses outcomes or cross-view information inside
the single-view recognizer.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.cycle_scale_qualification_v054 import (
    build_cycle_scale_qualification_run,
)
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import (
    canonicalize_qualified_records,
    causal_publish_qualified_identities,
    mutual_unique_strict_matches,
)
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig

VIEWS = [f"5m_offset_{i}" for i in range(5)]
PREFIX_FRACTIONS = (0.25, 0.50, 0.75)
NOMINAL_BAR_MINUTES = 5.0


def save(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def attach_times(event: dict, bars: list[dict]) -> dict:
    out = dict(event)
    out["five_occurrence_times"] = [
        str(bars[int(i)]["timestamp"]) for i in out["five_occurrence_bars"]
    ]
    return out


def overlap_component_stats(events: list[dict]) -> dict:
    rows = sorted(events, key=lambda r: (int(r["start_bar"]), int(r["end_bar"])))
    components = []
    cur = []
    max_end = None
    for row in rows:
        start, end = int(row["start_bar"]), int(row["end_bar"])
        if not cur or start < max_end:
            cur.append(row)
            max_end = max(end, max_end if max_end is not None else end)
        else:
            components.append(cur)
            cur = [row]
            max_end = end
    if cur:
        components.append(cur)
    sizes = sorted(len(c) for c in components)
    spans = sorted(
        max(int(r["end_bar"]) for r in c) - min(int(r["start_bar"]) for r in c)
        for c in components
    )

    def q(values, frac):
        if not values:
            return None
        return values[int(round((len(values) - 1) * frac))]

    return {
        "components": len(components),
        "nontrivial_components": sum(x > 1 for x in sizes),
        "component_size_median": q(sizes, 0.5),
        "component_size_p90": q(sizes, 0.9),
        "component_size_p95": q(sizes, 0.95),
        "component_size_p99": q(sizes, 0.99),
        "component_size_max": max(sizes) if sizes else None,
        "component_span_median_bars": q(spans, 0.5),
        "component_span_p90_bars": q(spans, 0.9),
        "component_span_max_bars": max(spans) if spans else None,
    }


def build_view(view: str, bars: list[dict]) -> dict:
    run = build_cycle_scale_qualification_run(bars, cfg=MaturityConfig(timeframe=view))
    qualified = [r for r in run.ledger.records if bool(r.get("scale_qualified"))]
    static_events = [
        attach_times(e, bars) for e in canonicalize_qualified_records(qualified)
    ]
    causal = causal_publish_qualified_identities(qualified)
    causal_events = list(causal["identity_events"])
    evidence_events = list(causal["evidence_events"])
    if {e["canonical_identity_id"] for e in static_events} != {
        e["canonical_identity_id"] for e in causal_events
    }:
        raise AssertionError("static and causal identity sets differ")
    return {
        "view": view,
        "bars": len(bars),
        "qualified_records": len(qualified),
        "canonical_events": static_events,
        "causal_identity_events": causal_events,
        "evidence_events": evidence_events,
        "selected_events": [e for e in static_events if bool(e["selected_any"])],
        "duplicate_scale_groups": sum(int(e["member_count"]) > 1 for e in static_events),
        "overlap_components": overlap_component_stats(static_events),
    }


def identity_event_prefix(events: list[dict], cutoff: int) -> list[dict]:
    return [e for e in events if int(e["confirmation_bar"]) < cutoff]


def evidence_prefix(events: list[dict], cutoff: int) -> list[dict]:
    return [e for e in events if int(e["confirmation_bar"]) < cutoff]


def prefix_check(full: dict, prefix: dict, cutoff: int) -> dict:
    a = identity_event_prefix(full["causal_identity_events"], cutoff)
    b = prefix["causal_identity_events"]
    ea = evidence_prefix(full["evidence_events"], cutoff)
    eb = prefix["evidence_events"]
    if a != b:
        raise AssertionError("canonical identity prefix rewrite")
    if ea != eb:
        raise AssertionError("identity evidence prefix rewrite")
    return {
        "cutoff_bars": cutoff,
        "identity_events_compared": len(a),
        "evidence_events_compared": len(ea),
        "passed": True,
        "confirmed_rewrite_count": 0,
    }


def audit_pair(main: dict, other: dict) -> dict:
    q = mutual_unique_strict_matches(
        main["canonical_events"], other["canonical_events"], NOMINAL_BAR_MINUTES
    )
    s = mutual_unique_strict_matches(
        main["selected_events"], other["selected_events"], NOMINAL_BAR_MINUTES
    )
    hidden = 0
    d1_same = 0
    d1_total = 0
    for i, j in q.matches:
        a, b = main["canonical_events"][i], other["canonical_events"][j]
        if not (a["selected_any"] and b["selected_any"]):
            hidden += 1
        if a.get("D1") is not None and b.get("D1") is not None:
            d1_total += 1
            d1_same += int(a["D1"] == b["D1"])
    return {
        "main_view": main["view"],
        "other_view": other["view"],
        "nominal_bar_minutes": NOMINAL_BAR_MINUTES,
        "qualified": {
            "main_events": len(main["canonical_events"]),
            "other_events": len(other["canonical_events"]),
            "mutual_unique_matches": len(q.matches),
            "main_match_fraction": (
                len(q.matches) / len(main["canonical_events"])
                if main["canonical_events"]
                else None
            ),
            "other_match_fraction": (
                len(q.matches) / len(other["canonical_events"])
                if other["canonical_events"]
                else None
            ),
            "ambiguous_main": len(q.ambiguous_a),
            "ambiguous_other": len(q.ambiguous_b),
            "unmatched_main": len(q.unmatched_a),
            "unmatched_other": len(q.unmatched_b),
            "matches_hidden_by_legacy_packing": hidden,
            "hidden_match_fraction": hidden / len(q.matches) if q.matches else None,
            "D1_same_label_fraction_on_strict_identity_matches": (
                d1_same / d1_total if d1_total else None
            ),
        },
        "legacy_selected": {
            "main_events": len(main["selected_events"]),
            "other_events": len(other["selected_events"]),
            "mutual_unique_matches": len(s.matches),
            "main_match_fraction": (
                len(s.matches) / len(main["selected_events"])
                if main["selected_events"]
                else None
            ),
            "other_match_fraction": (
                len(s.matches) / len(other["selected_events"])
                if other["selected_events"]
                else None
            ),
            "ambiguous_main": len(s.ambiguous_a),
            "ambiguous_other": len(s.ambiguous_b),
            "unmatched_main": len(s.unmatched_a),
            "unmatched_other": len(s.unmatched_b),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--output",
        type=Path,
        default=ROOT / "cloud_results/two_wave_qualified_identity_audit_v060",
    )
    args = ap.parse_args()

    bars_by_view = {}
    audits = {}
    for view in VIEWS:
        bars, data_audit = load_development_bars(
            ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json"
        )
        bars_by_view[view] = bars
        audits[view] = data_audit

    full = {view: build_view(view, bars_by_view[view]) for view in VIEWS}
    prefix_checks = []
    for view in VIEWS:
        for frac in PREFIX_FRACTIONS:
            cutoff = int(len(bars_by_view[view]) * frac)
            prefix = build_view(view, bars_by_view[view][:cutoff])
            prefix_checks.append(
                {
                    "view": view,
                    "fraction": frac,
                    **prefix_check(full[view], prefix, cutoff),
                }
            )

    pair_audits = {
        view: audit_pair(full["5m_offset_0"], full[view]) for view in VIEWS[1:]
    }
    result = {
        "schema": "two_wave_qualified_identity_audit@0.6.0",
        "status": "identity_audit_generated_not_morphology_acceptance",
        "upstream": "v0.5.2_exact_ridge_plus_v0.5.4_full_cycle_qualification",
        "changed_component_only": "financial_identity_decoupled_from_exclusive_packing",
        "cross_view_relation": (
            "same_phase_and_all_five_occurrence_timestamp_deltas_lte_one_5m_bar; "
            "mutual_unique_only"
        ),
        "views": {
            view: {
                "data_audit": audits[view],
                "qualified_records": full[view]["qualified_records"],
                "canonical_qualified_identities": len(full[view]["canonical_events"]),
                "legacy_selected_identities": len(full[view]["selected_events"]),
                "duplicate_scale_groups": full[view]["duplicate_scale_groups"],
                "overlap_components": full[view]["overlap_components"],
            }
            for view in VIEWS
        },
        "pair_audits": pair_audits,
        "prefix_checks": prefix_checks,
        "prefix_zero_rewrite_count": len(prefix_checks),
        "future_outcome_used": False,
        "trade_authority": False,
        "operational_baseline": "v0.4.3",
        "morphology_status": "morphology_replication_not_yet_accepted",
    }
    save(args.output / "summary.json", result)
    for view in VIEWS:
        save(
            args.output / view / "canonical_qualified_identities.json",
            full[view]["canonical_events"],
        )
        save(
            args.output / view / "causal_identity_events.json",
            full[view]["causal_identity_events"],
        )
        save(
            args.output / view / "identity_evidence_events.json",
            full[view]["evidence_events"],
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
