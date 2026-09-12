#!/usr/bin/env python3
"""Formal v0.7.5 F3 provisional lifecycle raw-publication transplant."""
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
from factor_lab.visual_structure.two_wave.f3_prefix_causal_lifecycle_v0704 import (
    build_lifecycle_for_case,
    summarize_case_semantics as summarize_lifecycle_case_semantics,
)
from factor_lab.visual_structure.two_wave.f3_provisional_lifecycle_publication_v0705 import (
    cache_prefix_static_stores,
    frozen_decision,
    replay_publications_from_cache,
    summarize_case_semantics as summarize_publication_case_semantics,
    summarize_cases,
)
from factor_lab.visual_structure.two_wave.reference_label_freeze_v0648 import validate_final_reference_frame
from factor_lab.visual_structure.two_wave.reference_label_packet_v0648 import sampling_commitment, select_blinded_cases
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from factor_lab.visual_structure.two_wave.semantic_bridge_counteroffensive_v0700 import (
    human_support_cells,
    infer_human_kinds,
)
from factor_lab.visual_structure.two_wave.semantic_object_parent_representation_v0650 import parse_human_anchors
from scripts.build_two_wave_independent_reference_packet_v0648 import (
    DATA_PATH,
    EXPECTED_SOURCE_SHA256,
    MANIFEST_PATH,
    VIEW,
)
from scripts.run_two_wave_semantic_bridge_counteroffensive_v0700 import build_qualified_publications

PROTOCOL = "docs/research/TWO_WAVE_F3_PROVISIONAL_LIFECYCLE_PUBLICATION_V0705_PROTOCOL.md"
PROTOCOL_FREEZE_COMMIT = "9652c7c2b0ba3761f1f326fd69d2d79039bd397d"
REFERENCE_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/FINAL_REFERENCE_LABELS.csv"
COMMITMENT_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/SAMPLING_COMMITMENT.json"
OUTPUT_DIR = ROOT / "experiments/two_wave_f3_provisional_lifecycle_publication_v0705"
EXPECTED_REFERENCE_SHA256 = "321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d"
EXPECTED_COMMITMENT = "f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8"
LOOKBACK_BARS = 96


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay_digest(row: dict) -> dict:
    """Fields that must match under a second deterministic publication replay."""
    return {
        "publication_count": int(row["publication_count"]),
        "certified_published_count": int(row["certified_published_count"]),
        "final_unresolved_published_count": int(row["final_unresolved_published_count"]),
        "prior_invalid_projection_count": int(row["prior_invalid_projection_count"]),
        "prior_invalid_projection_reason_counts": dict(row["prior_invalid_projection_reason_counts"]),
        "invalid_after_publication_count": int(row["invalid_after_publication_count"]),
        "later_valid_same_identity_count": int(row["later_valid_same_identity_count"]),
        "later_valid_would_rewrite_suppressed_count": int(row["later_valid_would_rewrite_suppressed_count"]),
        "prefix_predecessor_change_evidence_count": int(row["prefix_predecessor_change_evidence_count"]),
        "unresolved_then_certified_publication_count": int(row["unresolved_then_certified_publication_count"]),
        "published_still_unresolved_count": int(row["published_still_unresolved_count"]),
        "already_certified_publication_count": int(row["already_certified_publication_count"]),
        "aggregate_publication_identity_sha256": str(row["aggregate_publication_identity_sha256"]),
        "hard_invariant_violation_counts": dict(row["hard_invariant_violation_counts"]),
    }


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

    # Reconstruct the hidden deterministic v0.6.48 packet membership exactly.
    qualified_rows, construction = build_qualified_publications(ridge, bars)
    by_cutoff: dict[int, list[dict]] = defaultdict(list)
    for row in qualified_rows:
        by_cutoff[int(row["publishing_confirmation_bar"])].append(row)
    cases = select_blinded_cases(frame, by_cutoff.keys())
    commitment = sampling_commitment(cases)
    if commitment != EXPECTED_COMMITMENT:
        raise RuntimeError("reconstructed v0.6.48 sampling commitment drift")

    final = validate_final_reference_frame(pd.read_csv(REFERENCE_PATH, dtype=str, keep_default_na=False))
    reference = final.set_index("case_id")
    if sorted(c.case_id for c in cases) != sorted(reference.index.tolist()):
        raise RuntimeError("frozen final-reference membership drift")

    records = []
    positive_candidate_count = 0
    anchored_count = 0
    deterministic_case_replays = []
    lifecycle_live_support_cases = 0

    for case in cases:
        if case.stratum != "candidate":
            continue
        ref = reference.loc[case.case_id].to_dict()
        if str(ref["two_complete_same_scale_waves"]) != "yes":
            continue
        positive_candidate_count += 1
        human = parse_human_anchors(ref)
        if human is None:
            continue
        anchored_count += 1

        cutoff = int(case.cutoff_bar)
        chart_start = cutoff - (LOOKBACK_BARS - 1)
        human_bars = [chart_start + int(x) for x in human]
        kinds = infer_human_kinds(human_bars, closes)
        cells = human_support_cells(human_bars, chart_start, cutoff)

        lifecycle = build_lifecycle_for_case(ridge, chart_start, cutoff)
        lifecycle_semantics = summarize_lifecycle_case_semantics(
            lifecycle,
            ridge,
            cutoff,
            cells,
            kinds,
            human_bars,
        )
        lifecycle_live_support_cases += int(bool(lifecycle_semantics["lifecycle_live_support"]))

        prefix_frames = cache_prefix_static_stores(ridge, chart_start, cutoff)
        publication = replay_publications_from_cache(ridge, lifecycle, prefix_frames, bars)
        publication_repeat = replay_publications_from_cache(ridge, lifecycle, prefix_frames, bars)
        replay_ok = replay_digest(publication) == replay_digest(publication_repeat)
        deterministic_case_replays.append(bool(replay_ok))

        semantics = summarize_publication_case_semantics(publication, lifecycle, cells, kinds, human_bars)
        # Upstream semantic lineage must use the frozen v0.7.4 realization-level scorer,
        # not an object-level proxy introduced by the publication layer.
        semantics["static_support"] = bool(lifecycle_semantics["static_support"])
        semantics["certified_semantic_support"] = bool(lifecycle_semantics["certified_support"])
        semantics["permanent_certificate_gap_case"] = bool(
            lifecycle_semantics["static_support"] and not lifecycle_semantics["certified_support"]
        )
        records.append(
            {
                "lifecycle": lifecycle,
                "publication": publication,
                "semantics": semantics,
            }
        )

    if positive_candidate_count != 16:
        raise RuntimeError(f"reference-positive candidate count drift: {positive_candidate_count} != 16")
    if anchored_count != 11:
        raise RuntimeError(f"anchored reference-positive count drift: {anchored_count} != 11")
    if lifecycle_live_support_cases != 8:
        raise AssertionError(f"v0704 lifecycle-live support drift: {lifecycle_live_support_cases} != 8")

    summary = summarize_cases(records)
    deterministic_replay_ok = all(deterministic_case_replays) and len(deterministic_case_replays) == 11
    decision = frozen_decision(summary, deterministic_replay_ok)

    result = {
        "schema": "two_wave_f3_provisional_lifecycle_publication@0.7.5",
        "protocol": PROTOCOL,
        "protocol_freeze_commit": PROTOCOL_FREEZE_COMMIT,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_manifest_verified": bool(source_audit["manifest_verified"]),
        "final_reference_sha256": EXPECTED_REFERENCE_SHA256,
        "sampling_commitment_sha256": commitment,
        "construction": construction,
        "reference_positive_candidate_cases": positive_candidate_count,
        "anchored_reference_positive_cases": anchored_count,
        "required_upstream_replication": {
            **summary["upstream_replication"],
            "lifecycle_live_support_cases": int(lifecycle_live_support_cases),
        },
        "publication_summary": summary["publication"],
        "semantic_continuity": summary["semantic_continuity"],
        "frozen_decision": decision,
        "primary_category": decision["primary_category"],
        "deterministic_case_replay_count": sum(bool(x) for x in deterministic_case_replays),
        "development_discovery_only": True,
        "human_reference_labels_used_for_final_semantic_continuity_only": True,
        "annotator_notes_used": False,
        "annotator_confidence_used": False,
        "future_outcome_used": False,
        "future_certification_used_to_backdate_publication": False,
        "future_unconfirmed_ridge_used_for_predecessor_selection": False,
        "threshold_fitting_performed": False,
        "publication_waiting_period_fitted": False,
        "raw_window_geometry_retuned": False,
        "predecessor_rule_fitted": False,
        "lifecycle_semantics_changed": False,
        "qualification_or_direction_evaluated": False,
        "active_parent_authority_granted": False,
        "morphology_acceptance": False,
        "trade_authority": False,
        "production_authority": False,
        "case_level_table_written": False,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "RESULT.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
