#!/usr/bin/env python3
"""Formal v0.7.3 F3 causal-certificate gap attribution."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import build_ridge_run
from factor_lab.visual_structure.two_wave.f3_causal_certificate_gap_v0703 import (
    analyze_realization_certificate,
    distribution,
    frozen_decision,
)
from factor_lab.visual_structure.two_wave.reference_label_freeze_v0648 import validate_final_reference_frame
from factor_lab.visual_structure.two_wave.reference_label_packet_v0648 import sampling_commitment, select_blinded_cases
from factor_lab.visual_structure.two_wave.ridge_semantic_objectization_v0701 import (
    causal_survival_levels,
    eligible_nodes_by_level,
    realization_matches_human,
)
from factor_lab.visual_structure.two_wave.ridge_semantic_objectization_stream_v0701 import (
    _dominant_incremental,
    alternating_quintet_indices,
)
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

PROTOCOL = "docs/research/TWO_WAVE_F3_CAUSAL_CERTIFICATE_GAP_ATTRIBUTION_V0703_PROTOCOL.md"
PROTOCOL_FREEZE_COMMIT = "de795faf95a8a47c4835ccae76f37c6d1c196821"
REFERENCE_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/FINAL_REFERENCE_LABELS.csv"
COMMITMENT_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/SAMPLING_COMMITMENT.json"
OUTPUT_DIR = ROOT / "experiments/two_wave_f3_causal_certificate_gap_v0703"
EXPECTED_REFERENCE_SHA256 = "321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d"
EXPECTED_COMMITMENT = "f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8"
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
        raise RuntimeError("frozen sampling commitment mismatch")

    bars, source_audit = load_development_bars(DATA_PATH, MANIFEST_PATH)
    frame = pd.read_parquet(DATA_PATH).copy()
    closes = frame["close"].astype(float).tolist()
    ridge = build_ridge_run(bars, cfg=MaturityConfig(timeframe=VIEW))
    if ridge.lineage_anomalies:
        raise AssertionError(f"v0.5.2 ridge lineage anomalies: {len(ridge.lineage_anomalies)}")

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

    positive_candidate_count = 0
    anchored_count = 0
    static_support_cases = 0
    c0_support_cases = 0
    c1_support_cases = 0
    gap_case_count = 0

    aggregate_blockers: Counter[str] = Counter()
    gap_blockers: Counter[str] = Counter()
    aggregate_compatible_realizations = 0
    gap_compatible_realizations = 0
    c1_delays = []
    gap_realization_blocker_sets: list[list[str]] = []
    per_case_compatible_counts = []
    per_case_c0_counts = []
    per_case_c1_counts = []

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

        levels = eligible_nodes_by_level(ridge, chart_start, cutoff)
        survival = causal_survival_levels(levels)
        compatible = []
        for level, rows in enumerate(levels):
            for idxs in alternating_quintet_indices(rows):
                if not _dominant_incremental(rows, idxs, survival):
                    continue
                nodes = tuple(rows[i] for i in idxs)
                realization = {"level": int(level), "nodes": nodes}
                hit, _ = realization_matches_human(realization, cells, kinds, human_bars)
                if not hit:
                    continue
                audit = analyze_realization_certificate(ridge, rows, idxs, level, cutoff)
                compatible.append(audit)
                aggregate_compatible_realizations += 1
                aggregate_blockers.update(str(x) for x in audit["blockers"])
                if bool(audit["c1_ok"]):
                    c1_delays.append(int(audit["c1_confirmation_delay_from_selected_nodes"]))

        static_case = bool(compatible)
        c0_case = any(bool(x["c0_ok"]) for x in compatible)
        c1_case = any(bool(x["c1_ok"]) for x in compatible)
        static_support_cases += int(static_case)
        c0_support_cases += int(c0_case)
        c1_support_cases += int(c1_case)
        per_case_compatible_counts.append(len(compatible))
        per_case_c0_counts.append(sum(bool(x["c0_ok"]) for x in compatible))
        per_case_c1_counts.append(sum(bool(x["c1_ok"]) for x in compatible))

        if static_case and not c0_case:
            gap_case_count += 1
            gap_compatible_realizations += len(compatible)
            for audit in compatible:
                blockers = [str(x) for x in audit["blockers"]]
                gap_realization_blocker_sets.append(blockers)
                gap_blockers.update(blockers)

    if positive_candidate_count != 16:
        raise RuntimeError(f"reference-positive candidate count drift: {positive_candidate_count} != 16")
    if anchored_count != 11:
        raise RuntimeError(f"anchored reference-positive count drift: {anchored_count} != 11")

    decision = frozen_decision(
        static_support_cases=static_support_cases,
        c0_support_cases=c0_support_cases,
        gap_case_count=gap_case_count,
        c1_support_cases=c1_support_cases,
        gap_realization_blocker_sets=gap_realization_blocker_sets,
    )

    result = {
        "schema": "two_wave_f3_causal_certificate_gap_attribution@0.7.3",
        "protocol": PROTOCOL,
        "protocol_freeze_commit": PROTOCOL_FREEZE_COMMIT,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_manifest_verified": bool(source_audit["manifest_verified"]),
        "final_reference_sha256": EXPECTED_REFERENCE_SHA256,
        "sampling_commitment_sha256": commitment,
        "construction": construction,
        "reference_positive_candidate_cases": positive_candidate_count,
        "anchored_reference_positive_cases": anchored_count,
        "required_replication": {
            "static_f3_support_cases": static_support_cases,
            "c0_causal_support_cases": c0_support_cases,
            "static_supported_c0_unsupported_gap_cases": gap_case_count,
        },
        "c1_minimal_explicit_death_certificate": {
            "causal_support_cases": c1_support_cases,
            "recovered_cases_vs_c0": c1_support_cases - c0_support_cases,
            "proof_delay_bars_from_selected_nodes": distribution(c1_delays),
        },
        "blocker_attribution": {
            "aggregate_human_compatible_static_realizations": aggregate_compatible_realizations,
            "aggregate_blocker_counts": dict(sorted(aggregate_blockers.items())),
            "gap_case_count": gap_case_count,
            "gap_human_compatible_static_realizations": gap_compatible_realizations,
            "gap_blocker_counts": dict(sorted(gap_blockers.items())),
            "per_case_compatible_realization_count": distribution(per_case_compatible_counts),
            "per_case_c0_certified_realization_count": distribution(per_case_c0_counts),
            "per_case_c1_certified_realization_count": distribution(per_case_c1_counts),
            "case_identity_or_time_emitted": False,
        },
        "frozen_decision": decision,
        "primary_category": decision["primary_category"],
        "development_discovery_only": True,
        "human_reference_labels_used_for_same_frozen_semantic_support_only": True,
        "annotator_notes_used": False,
        "annotator_confidence_used": False,
        "future_outcome_used": False,
        "future_ridge_survival_used": False,
        "threshold_fitting_performed": False,
        "event_delay_tolerance_fitted": False,
        "f3_objectization_changed": False,
        "salvage_gate_changed": False,
        "qualification_or_direction_evaluated": False,
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
