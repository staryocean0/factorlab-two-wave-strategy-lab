#!/usr/bin/env python3
"""Formal v0.6.51 left-boundary / internal-pivot correspondence decomposition."""
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
from factor_lab.visual_structure.two_wave.left_boundary_internal_pivot_decomposition_v0651 import (
    decompose_case,
    summarize_decomposition,
)
from factor_lab.visual_structure.two_wave.reference_label_freeze_v0648 import validate_final_reference_frame
from factor_lab.visual_structure.two_wave.reference_label_packet_v0648 import sampling_commitment, select_blinded_cases
from factor_lab.visual_structure.two_wave.semantic_object_parent_representation_v0650 import (
    canonical_identity,
    parse_human_anchors,
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
OUTPUT_DIR = ROOT / "experiments/two_wave_left_boundary_internal_pivot_decomposition_v0651"
PROTOCOL = "docs/research/TWO_WAVE_LEFT_BOUNDARY_INTERNAL_PIVOT_DECOMPOSITION_V0651_PROTOCOL.md"
EXPECTED_REFERENCE_SHA256 = "321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d"
EXPECTED_COMMITMENT = "f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8"
EXPECTED_ANCHORED_CASES = 11


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if sha256(DATA_PATH) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("frozen source SHA256 mismatch")
    if sha256(REFERENCE_PATH) != EXPECTED_REFERENCE_SHA256:
        raise RuntimeError("frozen final reference SHA256 mismatch")
    if json.loads(COMMITMENT_PATH.read_text()).get("sha256") != EXPECTED_COMMITMENT:
        raise RuntimeError("sampling commitment record mismatch")

    final = validate_final_reference_frame(pd.read_csv(REFERENCE_PATH, dtype=str, keep_default_na=False))
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
        raise RuntimeError("hidden mapping differs from frozen commitment")
    if sorted(c.case_id for c in cases) != sorted(reference.index.tolist()):
        raise RuntimeError("reference membership differs from packet")

    rows = []
    candidate_count = 0
    human_positive_candidate_count = 0
    multi_identity_anchored_cases = 0
    for case in cases:
        if case.stratum != "candidate":
            continue
        candidate_count += 1
        ref = reference.loc[case.case_id].to_dict()
        if str(ref["two_complete_same_scale_waves"]) != "yes":
            continue
        human_positive_candidate_count += 1
        human = parse_human_anchors(ref)
        if human is None:
            continue
        identities = by_cutoff.get(int(case.cutoff_bar), [])
        if not identities:
            raise AssertionError("anchored candidate lacks qualified identity")
        if len(identities) > 1:
            multi_identity_anchored_cases += 1
        model_identity = canonical_identity(identities)
        model_visible = visible_anchor_positions(
            model_identity["published_raw_occurrence_bars"], int(case.cutoff_bar)
        )
        rows.append(decompose_case(model_visible, human))

    if candidate_count != 120:
        raise RuntimeError("candidate count drift")
    if human_positive_candidate_count != 16:
        raise RuntimeError("reference-positive candidate count drift")
    if len(rows) != EXPECTED_ANCHORED_CASES:
        raise RuntimeError(f"anchored case count drift: {len(rows)} != {EXPECTED_ANCHORED_CASES}")

    aggregate = summarize_decomposition(rows)
    result = {
        "schema": "two_wave_left_boundary_internal_pivot_decomposition_audit@0.6.51",
        "protocol": PROTOCOL,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_manifest_verified": bool(source_audit["manifest_verified"]),
        "final_reference_sha256": EXPECTED_REFERENCE_SHA256,
        "sampling_commitment_sha256": commitment,
        "candidate_qualified_publications_available": int(generation_summary["candidate_qualified"]),
        "candidate_cases": candidate_count,
        "reference_positive_candidate_cases": human_positive_candidate_count,
        "anchored_reference_positive_cases": len(rows),
        "multi_identity_anchored_cases": multi_identity_anchored_cases,
        "canonical_identity_selection": "lexicographic_published_raw_occurrence_bars_then_phase",
        "aggregate_decomposition": aggregate,
        "primary_category": aggregate["primary_category"],
        "case_level_table_written": False,
        "annotator_notes_used": False,
        "annotator_confidence_used": False,
        "direction_prediction_used": False,
        "future_outcome_used": False,
        "threshold_fitting_performed": False,
        "pivot_remapping_performed": False,
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
