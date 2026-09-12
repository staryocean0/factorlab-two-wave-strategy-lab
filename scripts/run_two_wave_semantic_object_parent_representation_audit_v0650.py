#!/usr/bin/env python3
"""Formal v0.6.50 semantic-object / parent-representation audit.

Read-only: no threshold fitting, qualification change, direction scoring, future
outcome, PnL, annotator notes/confidence, or case-level residual output.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.reference_label_freeze_v0648 import validate_final_reference_frame
from factor_lab.visual_structure.two_wave.reference_label_packet_v0648 import (
    LOOKBACK_BARS,
    sampling_commitment,
    select_blinded_cases,
)
from factor_lab.visual_structure.two_wave.semantic_object_parent_representation_v0650 import (
    anchor_alignment,
    canonical_identity,
    frozen_decision,
    full_visibility,
    parse_human_anchors,
    rank_probability,
    summarize_alignment,
    visible_anchor_positions,
)
from scripts.build_two_wave_independent_reference_packet_v0648 import (
    DATA_PATH,
    EXPECTED_SOURCE_SHA256,
    MANIFEST_PATH,
    VIEW,
)
from scripts.run_two_wave_independent_temporal_replication_v0647 import build_publications

REFERENCE_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/FINAL_REFERENCE_LABELS.csv"
COMMITMENT_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/SAMPLING_COMMITMENT.json"
OUTPUT_DIR = ROOT / "experiments/two_wave_semantic_object_parent_representation_v0650"
PROTOCOL = "docs/research/TWO_WAVE_SEMANTIC_OBJECT_PARENT_REPRESENTATION_AUDIT_V0650_PROTOCOL.md"
EXPECTED_REFERENCE_SHA256 = "321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d"
EXPECTED_COMMITMENT = "f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dist(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "median": None, "q1": None, "q3": None}
    s = pd.Series(values, dtype=float)
    return {
        "count": int(len(values)),
        "median": float(s.median()),
        "q1": float(s.quantile(0.25)),
        "q3": float(s.quantile(0.75)),
    }


def main() -> int:
    if sha256(DATA_PATH) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("frozen source SHA256 mismatch")
    if sha256(REFERENCE_PATH) != EXPECTED_REFERENCE_SHA256:
        raise RuntimeError("frozen final reference SHA256 mismatch")
    commitment_record = json.loads(COMMITMENT_PATH.read_text())
    if commitment_record.get("sha256") != EXPECTED_COMMITMENT:
        raise RuntimeError("frozen sampling commitment record mismatch")

    final = validate_final_reference_frame(
        pd.read_csv(REFERENCE_PATH, dtype=str, keep_default_na=False)
    )
    reference = final.set_index("case_id")

    bars, source_audit = load_development_bars(DATA_PATH, MANIFEST_PATH)
    frame = pd.read_parquet(DATA_PATH).copy()
    publication_rows, _, generation_summary = build_publications(VIEW, bars)
    qualified = [r for r in publication_rows if bool(r["candidate_qualified"])]
    by_cutoff: dict[int, list[dict]] = defaultdict(list)
    for row in qualified:
        by_cutoff[int(row["publishing_confirmation_bar"])].append(row)

    cases = select_blinded_cases(frame, by_cutoff.keys())
    commitment = sampling_commitment(cases)
    if commitment != EXPECTED_COMMITMENT:
        raise RuntimeError("reconstructed hidden mapping mismatches frozen commitment")
    if sorted(c.case_id for c in cases) != sorted(reference.index.tolist()):
        raise RuntimeError("reference membership differs from frozen packet")

    candidate_cases = [c for c in cases if c.stratum == "candidate"]
    if len(candidate_cases) != 120:
        raise AssertionError("candidate case count drift")

    grouped = {"no": [], "yes": []}
    alignment_rows = []
    multi_identity_count = 0

    for case in candidate_cases:
        ref = reference.loc[case.case_id].to_dict()
        presence = str(ref["two_complete_same_scale_waves"])
        if presence not in {"no", "yes"}:
            raise RuntimeError("v0.6.50 expects frozen candidate reference labels to be yes/no")
        rows = by_cutoff.get(int(case.cutoff_bar), [])
        if not rows:
            raise AssertionError("candidate cutoff lacks v0.6.18-qualified published identity")
        if len(rows) > 1:
            multi_identity_count += 1
        model = canonical_identity(rows)
        visible = visible_anchor_positions(model["published_raw_occurrence_bars"], int(case.cutoff_bar))
        fully_visible = full_visibility(visible)
        right_gap = int(case.cutoff_bar) - int(model["published_raw_occurrence_bars"][-1])
        span = int(model["published_raw_occurrence_bars"][-1]) - int(model["published_raw_occurrence_bars"][0])
        if span <= 0:
            raise AssertionError("non-positive model parent span")
        record = {
            "fully_visible": fully_visible,
            "right_edge_gap_bars": float(right_gap),
            "parent_span_fraction": float(span / (LOOKBACK_BARS - 1)),
        }
        grouped[presence].append(record)

        human = parse_human_anchors(ref)
        if human is not None:
            alignment_rows.append(anchor_alignment(visible, human))

    if len(grouped["no"]) != 104 or len(grouped["yes"]) != 16:
        raise RuntimeError("frozen v0.6.48 candidate reference counts drifted")

    no_full = sum(bool(x["fully_visible"]) for x in grouped["no"]) / len(grouped["no"])
    yes_full = sum(bool(x["fully_visible"]) for x in grouped["yes"]) / len(grouped["yes"])
    no_gaps = [float(x["right_edge_gap_bars"]) for x in grouped["no"]]
    yes_gaps = [float(x["right_edge_gap_bars"]) for x in grouped["yes"]]
    no_spans = [float(x["parent_span_fraction"]) for x in grouped["no"]]
    yes_spans = [float(x["parent_span_fraction"]) for x in grouped["yes"]]

    gap_rank = rank_probability(no_gaps, yes_gaps)
    # P(no < yes)+0.5*tie = P(yes > no)+0.5*tie.
    smaller_span_rank = rank_probability(yes_spans, no_spans)
    alignment = summarize_alignment(alignment_rows)
    decision = frozen_decision(
        no_not_visible_incidence=1.0 - no_full,
        yes_not_visible_incidence=1.0 - yes_full,
        right_edge_gap_rank_no_gt_yes=gap_rank,
        span_fraction_rank_no_lt_yes=smaller_span_rank,
        alignment=alignment,
    )

    result = {
        "schema": "two_wave_semantic_object_parent_representation_audit@0.6.50",
        "protocol": PROTOCOL,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_manifest_verified": bool(source_audit["manifest_verified"]),
        "final_reference_sha256": EXPECTED_REFERENCE_SHA256,
        "sampling_commitment_sha256": commitment,
        "candidate_qualified_publications_available": int(generation_summary["candidate_qualified"]),
        "candidate_cases": 120,
        "reference_no_candidates": 104,
        "reference_yes_candidates": 16,
        "multi_identity_candidate_cutoffs": multi_identity_count,
        "canonical_identity_selection": "lexicographic_published_raw_occurrence_bars_then_phase",
        "visibility": {
            "reference_no_full_visibility_incidence": no_full,
            "reference_yes_full_visibility_incidence": yes_full,
            "reference_no_not_fully_visible_incidence": 1.0 - no_full,
            "reference_yes_not_fully_visible_incidence": 1.0 - yes_full,
        },
        "right_edge_gap_bars": {
            "reference_no": dist(no_gaps),
            "reference_yes": dist(yes_gaps),
            "rank_probability_no_gt_yes_plus_half_tie": gap_rank,
        },
        "algorithmic_parent_span_fraction": {
            "reference_no": dist(no_spans),
            "reference_yes": dist(yes_spans),
            "rank_probability_no_lt_yes_plus_half_tie": smaller_span_rank,
        },
        "human_anchor_correspondence": alignment,
        "frozen_decision": decision,
        "primary_category": decision["primary_category"],
        "case_level_table_written": False,
        "annotator_notes_used": False,
        "annotator_confidence_used": False,
        "direction_prediction_used": False,
        "future_outcome_used": False,
        "threshold_fitting_performed": False,
        "qualification_changed": False,
        "direction_winner_changed": False,
        "morphology_acceptance": False,
        "trade_authority": False,
        "production_authority": False,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "RESULT.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
