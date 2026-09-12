#!/usr/bin/env python3
"""Formal v0.7.2 F3 causal event/publication + downstream transplant precheck.

Primary metrics are label-blind. The frozen v0.6.48 packet is used only as a
committed set of 240 historical 96-bar cutoffs.
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
from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import build_ridge_run
from factor_lab.visual_structure.two_wave.f3_causal_publication_v0702 import (
    build_cutoff_context,
    build_death_map,
    certificate_object,
    distribution,
    enumerate_f3_object_masks,
    frozen_decision,
)
from factor_lab.visual_structure.two_wave.reference_label_packet_v0648 import (
    sampling_commitment,
    select_blinded_cases,
)
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from scripts.build_two_wave_independent_reference_packet_v0648 import (
    DATA_PATH,
    EXPECTED_SOURCE_SHA256,
    MANIFEST_PATH,
    VIEW,
)
from scripts.run_two_wave_semantic_bridge_counteroffensive_v0700 import (
    build_qualified_publications,
)

PROTOCOL = "docs/research/TWO_WAVE_F3_CAUSAL_PUBLICATION_TRANSPLANT_V0702_PROTOCOL.md"
PROTOCOL_FREEZE_COMMIT = "9b062153bd28b9591b66eb26fcebf8f1d431a24f"
COMMITMENT_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/SAMPLING_COMMITMENT.json"
OUTPUT_DIR = ROOT / "experiments/two_wave_f3_causal_publication_transplant_v0702"
EXPECTED_COMMITMENT = "f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8"
LOOKBACK_BARS = 96
EXPECTED_PACKET_CASES = 240


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if sha256(DATA_PATH) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("frozen source SHA256 mismatch")
    commitment_record = json.loads(COMMITMENT_PATH.read_text())
    if commitment_record.get("sha256") != EXPECTED_COMMITMENT:
        raise RuntimeError("frozen sampling commitment record mismatch")

    bars, source_audit = load_development_bars(DATA_PATH, MANIFEST_PATH)
    frame = pd.read_parquet(DATA_PATH).copy()
    ridge = build_ridge_run(bars, cfg=MaturityConfig(timeframe=VIEW))
    if ridge.lineage_anomalies:
        raise AssertionError(f"v0.5.2 ridge lineage anomalies: {len(ridge.lineage_anomalies)}")

    # Legacy qualification is used only to reconstruct the already committed
    # packet cutoff universe. Its labels do not enter any F3 metric.
    qualified_rows, construction = build_qualified_publications(ridge, bars)
    by_cutoff: dict[int, list[dict]] = defaultdict(list)
    for row in qualified_rows:
        by_cutoff[int(row["publishing_confirmation_bar"])].append(row)
    cases = select_blinded_cases(frame, by_cutoff.keys())
    commitment = sampling_commitment(cases)
    if commitment != EXPECTED_COMMITMENT:
        raise RuntimeError("reconstructed v0.6.48 packet commitment drift")
    if len(cases) != EXPECTED_PACKET_CASES:
        raise RuntimeError(f"packet case count drift: {len(cases)} != {EXPECTED_PACKET_CASES}")

    # No reference CSV is opened in this runner. Do not branch on case.stratum.
    cutoffs = [int(case.cutoff_bar) for case in cases]
    if len(set(cutoffs)) != EXPECTED_PACKET_CASES:
        raise RuntimeError("packet cutoff bars are not unique")

    global_death_map = build_death_map(ridge)

    ordinary_counts: list[int] = []
    certified_counts_positive: list[int] = []
    certificate_delays: list[int] = []
    total_ordinary_objects = 0
    total_certified_objects = 0
    f3_positive_cutoffs = 0
    certified_presence_cutoffs = 0
    certified_with_death_witness = 0
    certified_immediate_no_skip = 0
    certificate_replay_failures = 0

    for cutoff in cutoffs:
        chart_start = int(cutoff) - (LOOKBACK_BARS - 1)
        objects, levels = enumerate_f3_object_masks(ridge, chart_start, cutoff)
        ordinary_count = len(objects)
        ordinary_counts.append(ordinary_count)
        total_ordinary_objects += ordinary_count
        if ordinary_count == 0:
            continue

        f3_positive_cutoffs += 1
        cutoff_context = build_cutoff_context(levels)
        replay_context_cache: dict[int, dict] = {}
        certified_here = 0

        for object_key, level_mask in objects.items():
            try:
                cert = certificate_object(
                    ridge,
                    chart_start,
                    cutoff,
                    object_key,
                    level_mask,
                    levels,
                    death_map=global_death_map,
                    cutoff_context=cutoff_context,
                    replay_context_cache=replay_context_cache,
                )
            except AssertionError:
                certificate_replay_failures += 1
                continue
            if cert is None:
                continue
            certified_here += 1
            total_certified_objects += 1
            certificate_delays.append(int(cert["certificate_delay_bars"]))
            if bool(cert["used_death_witness"]):
                certified_with_death_witness += 1
            else:
                certified_immediate_no_skip += 1

        certified_counts_positive.append(certified_here)
        if certified_here > 0:
            certified_presence_cutoffs += 1

    if f3_positive_cutoffs == 0 or total_ordinary_objects == 0:
        raise RuntimeError("frozen packet unexpectedly contains no ordinary F3 objects")

    summary = {
        "packet_cutoffs": EXPECTED_PACKET_CASES,
        "f3_positive_cutoffs": f3_positive_cutoffs,
        "ordinary_f3_object_count_per_cutoff": distribution(ordinary_counts),
        "total_ordinary_final_cutoff_f3_objects": total_ordinary_objects,
        "total_death_certified_f3_objects": total_certified_objects,
        "certified_object_fraction": total_certified_objects / total_ordinary_objects,
        "cutoffs_with_at_least_one_certified_object": certified_presence_cutoffs,
        "certified_presence_fraction_given_f3_positive_cutoff": certified_presence_cutoffs / f3_positive_cutoffs,
        "certified_object_count_per_f3_positive_cutoff": distribution(certified_counts_positive),
        "certificate_delay_bars": distribution(certificate_delays),
        "certified_objects_requiring_death_witness": certified_with_death_witness,
        "certified_objects_immediate_no_skipped_ridge": certified_immediate_no_skip,
        "death_witness_fraction_among_certified": (
            certified_with_death_witness / total_certified_objects
            if total_certified_objects else 0.0
        ),
        "immediate_no_skip_fraction_among_certified": (
            certified_immediate_no_skip / total_certified_objects
            if total_certified_objects else 0.0
        ),
        "certificate_replay_failure_count": certificate_replay_failures,
    }
    decision = frozen_decision(summary)

    gate_a = bool(decision["gate_A_causal_certificate_coverage"])
    result = {
        "schema": "two_wave_f3_causal_publication_transplant_precheck@0.7.2",
        "protocol": PROTOCOL,
        "protocol_freeze_commit": PROTOCOL_FREEZE_COMMIT,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_manifest_verified": bool(source_audit["manifest_verified"]),
        "sampling_commitment_sha256": commitment,
        "packet_cutoff_reconstruction": construction,
        "f3_family": "F3_persistence_dominant_nonconsecutive_quintet",
        "f3_definition_changed": False,
        "primary_label_blind_event_audit": summary,
        "frozen_decision": decision,
        "primary_category": decision["primary_category"],
        "downstream_transplant_precheck": {
            "v065_append_only_publication_concept_salvage_eligible": gate_a,
            "v065_exact_grouping_or_function_transplantable_unchanged": False,
            "v064_predecessor_raw_projection_transplantable_unchanged": False,
            "v064_direct_projection_block_reason": "requires_consecutive_birth_nodes_but_F3_is_nonconsecutive",
            "v064_sequential_raw_projection_idea_declared_false": False,
            "v066_v0618_interface_structurally_eligible_after_generalized_F3_projection_freeze": True,
            "v054_v0618_thresholds_revalidated": False,
            "D1_v0625_direction_transplant_test_started": False,
        },
        "human_reference_labels_used": False,
        "packet_stratum_used": False,
        "annotator_notes_used": False,
        "annotator_confidence_used": False,
        "direction_prediction_used": False,
        "future_outcome_used": False,
        "threshold_fitting_performed": False,
        "multiplicity_threshold_fitted": False,
        "delay_threshold_fitted": False,
        "case_level_table_written": False,
        "projection_geometry_changed": False,
        "publication_policy_changed": False,
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
