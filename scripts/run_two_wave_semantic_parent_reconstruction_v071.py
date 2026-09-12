#!/usr/bin/env python3
"""Formal v0.7.1 ridge-supported semantic-parent reconstruction audit."""
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
from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import build_ridge_run
from factor_lab.visual_structure.two_wave.reference_label_freeze_v0648 import validate_final_reference_frame
from factor_lab.visual_structure.two_wave.reference_label_packet_v0648 import sampling_commitment, select_blinded_cases
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from factor_lab.visual_structure.two_wave.semantic_bridge_counteroffensive_v0700 import (
    human_support_cells,
    infer_human_kinds,
)
from factor_lab.visual_structure.two_wave.semantic_object_parent_representation_v0650 import parse_human_anchors
from factor_lab.visual_structure.two_wave.semantic_parent_reconstruction_v071 import (
    F0_EXACT,
    audit_case_families,
    frozen_adjudication,
    summarize_family_records,
)
from scripts.build_two_wave_independent_reference_packet_v0648 import (
    DATA_PATH,
    EXPECTED_SOURCE_SHA256,
    MANIFEST_PATH,
    VIEW,
)
from scripts.run_two_wave_semantic_bridge_counteroffensive_v0700 import build_qualified_publications

PROTOCOL = "docs/research/TWO_WAVE_RIDGE_SUPPORTED_SEMANTIC_PARENT_RECONSTRUCTION_V071_PROTOCOL.md"
PROTOCOL_FREEZE_COMMIT = "d39d3b555b486642c27e0ebb724f164af98ad3f4"
REFERENCE_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/FINAL_REFERENCE_LABELS.csv"
COMMITMENT_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/SAMPLING_COMMITMENT.json"
OUTPUT_DIR = ROOT / "experiments/two_wave_ridge_supported_semantic_parent_reconstruction_v071"
EXPECTED_REFERENCE_SHA256 = "321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d"
EXPECTED_COMMITMENT = "f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8"
EXPECTED_REFERENCE_POSITIVE_CANDIDATES = 16
EXPECTED_ANCHORED_POSITIVES = 11
EXPECTED_V0700_EXACT_SUPPORT = 3
LOOKBACK_BARS = 96


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if sha256(DATA_PATH) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("frozen source SHA256 mismatch")
    if sha256(REFERENCE_PATH) != EXPECTED_REFERENCE_SHA256:
        raise RuntimeError("frozen final-reference SHA256 mismatch")
    commitment_record = json.loads(COMMITMENT_PATH.read_text())
    if commitment_record.get("sha256") != EXPECTED_COMMITMENT:
        raise RuntimeError("frozen sampling commitment record mismatch")

    bars, source_audit = load_development_bars(DATA_PATH, MANIFEST_PATH)
    frame = pd.read_parquet(DATA_PATH).copy()
    closes = frame["close"].astype(float).tolist()

    ridge = build_ridge_run(bars, cfg=MaturityConfig(timeframe=VIEW))
    if ridge.lineage_anomalies:
        raise AssertionError(f"v0.5.2 ridge lineage anomalies: {len(ridge.lineage_anomalies)}")

    # Reconstruct the frozen v0.6.48 packet membership using the identical
    # legacy candidate chain.  These rows are used only to recover the already
    # committed case universe; v0.7.1 family membership never reads their
    # qualification or raw-projection outcomes.
    qualified_rows, construction = build_qualified_publications(ridge, bars)
    by_cutoff: dict[int, list[dict]] = defaultdict(list)
    for row in qualified_rows:
        by_cutoff[int(row["publishing_confirmation_bar"])].append(row)

    cases = select_blinded_cases(frame, by_cutoff.keys())
    commitment = sampling_commitment(cases)
    if commitment != EXPECTED_COMMITMENT:
        raise RuntimeError("reconstructed v0.6.48 packet commitment drift")

    final = validate_final_reference_frame(pd.read_csv(REFERENCE_PATH, dtype=str, keep_default_na=False))
    reference = final.set_index("case_id")
    if sorted(c.case_id for c in cases) != sorted(reference.index.tolist()):
        raise RuntimeError("final-reference membership differs from frozen packet")

    family_records: list[dict[str, dict]] = []
    reference_positive_count = 0
    anchored_positive_count = 0

    for case in cases:
        if case.stratum != "candidate":
            continue
        ref = reference.loc[case.case_id].to_dict()
        if str(ref["two_complete_same_scale_waves"]) != "yes":
            continue
        reference_positive_count += 1

        human = parse_human_anchors(ref)
        if human is None:
            continue
        anchored_positive_count += 1

        cutoff = int(case.cutoff_bar)
        chart_start = cutoff - (LOOKBACK_BARS - 1)
        human_bars = [chart_start + int(x) for x in human]
        kinds = infer_human_kinds(human_bars, closes)
        cells = human_support_cells(human_bars, chart_start, cutoff)

        family_records.append(
            audit_case_families(
                ridge,
                cells=cells,
                kinds=kinds,
                chart_start=chart_start,
                cutoff=cutoff,
            )
        )

    if reference_positive_count != EXPECTED_REFERENCE_POSITIVE_CANDIDATES:
        raise RuntimeError(
            f"reference-positive candidate count drift: {reference_positive_count} != {EXPECTED_REFERENCE_POSITIVE_CANDIDATES}"
        )
    if anchored_positive_count != EXPECTED_ANCHORED_POSITIVES or len(family_records) != EXPECTED_ANCHORED_POSITIVES:
        raise RuntimeError(
            f"anchored reference-positive count drift: {anchored_positive_count} != {EXPECTED_ANCHORED_POSITIVES}"
        )

    summary = summarize_family_records(family_records)

    # Hard bridge back to the formal v0.7.0 result.  The legacy exact control
    # must remain exactly 3/11; otherwise v0.7.1 fails rather than changing the
    # historical denominator or compatibility semantics.
    exact_support = int(summary[F0_EXACT]["support_count"])
    if exact_support != EXPECTED_V0700_EXACT_SUPPORT:
        raise RuntimeError(
            f"v0.7.0 exact-tuple control drift: {exact_support} != {EXPECTED_V0700_EXACT_SUPPORT}"
        )

    decision = frozen_adjudication(summary)
    result = {
        "schema": "two_wave_ridge_supported_semantic_parent_reconstruction@0.7.1",
        "protocol": PROTOCOL,
        "protocol_freeze_commit": PROTOCOL_FREEZE_COMMIT,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_manifest_verified": bool(source_audit["manifest_verified"]),
        "final_reference_sha256": EXPECTED_REFERENCE_SHA256,
        "sampling_commitment_sha256": commitment,
        "construction_replay": construction,
        "reference_positive_candidate_cases": reference_positive_count,
        "anchored_reference_positive_cases": anchored_positive_count,
        "legacy_exact_control_expected_support": EXPECTED_V0700_EXACT_SUPPORT,
        "family_support": summary,
        "frozen_decision": decision,
        "primary_category": decision["primary_category"],
        "selected_development_challenger_family": decision["selected_development_challenger_family"],
        "development_challenger_selected": bool(decision["development_challenger_selected"]),
        "development_discovery_only": True,
        "human_reference_labels_used_for_postconstruction_compatibility_only": True,
        "annotator_notes_used": False,
        "annotator_confidence_used": False,
        "future_outcome_used": False,
        "direction_prediction_used": False,
        "qualification_outcome_used_for_family_membership": False,
        "raw_projection_outcome_used_for_family_membership": False,
        "threshold_fitting_performed": False,
        "human_anchor_distance_tolerance_fitted": False,
        "case_level_table_written": False,
        "qualification_changed": False,
        "direction_winner_changed": False,
        "morphology_acceptance": False,
        "trade_authority": False,
        "production_authority": False,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "RESULT.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
