#!/usr/bin/env python3
"""Formal v0.7.2 F3 causal event/publication + transplant precheck."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import build_ridge_run
from factor_lab.visual_structure.two_wave.f3_causal_publication_v0702 import (
    build_lineage_index,
    enumerate_checkpoint_f3_objects,
    summarize_publication_precheck,
    trace_f3_identity,
)
from factor_lab.visual_structure.two_wave.reference_label_packet_v0648 import (
    LOOKBACK_BARS,
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
from scripts.run_two_wave_semantic_bridge_counteroffensive_v0700 import build_qualified_publications

PROTOCOL = "docs/research/TWO_WAVE_F3_CAUSAL_PUBLICATION_TRANSPLANT_PRECHECK_V0702_PROTOCOL.md"
PROTOCOL_FREEZE_COMMIT = "c6df4a443ff85f700f898ee6de4dce44fdaf4548"
COMMITMENT_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/SAMPLING_COMMITMENT.json"
OUTPUT_DIR = ROOT / "experiments/two_wave_f3_causal_publication_v0702"
EXPECTED_COMMITMENT = "f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8"
EXPECTED_CHECKPOINT_COUNT = 240


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dist(values) -> dict:
    vals = sorted(int(x) for x in values)
    if not vals:
        return {"count": 0, "median": None, "min": None, "max": None}
    return {
        "count": len(vals),
        "median": float(median(vals)),
        "min": int(vals[0]),
        "max": int(vals[-1]),
    }


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

    # Rebuild the hidden v0.6.48 checkpoint mapping from the frozen legacy
    # candidate chain. The resulting 240 timestamps are only a deterministic,
    # label-free checkpoint sampler for v0.7.2. No reference-label file is read.
    qualified_rows, legacy_sampling_construction = build_qualified_publications(ridge, bars)
    candidate_cutoffs = {int(row["publishing_confirmation_bar"]) for row in qualified_rows}
    cases = select_blinded_cases(frame, candidate_cutoffs)
    if len(cases) != EXPECTED_CHECKPOINT_COUNT:
        raise RuntimeError(f"frozen checkpoint count drift: {len(cases)} != {EXPECTED_CHECKPOINT_COUNT}")
    commitment = sampling_commitment(cases)
    if commitment != EXPECTED_COMMITMENT:
        raise RuntimeError("reconstructed v0.6.48 packet commitment drift")

    observed: dict[tuple[str, ...], set[int]] = defaultdict(set)
    checkpoint_counts: list[int] = []
    checkpoint_counts_by_stratum: dict[str, list[int]] = defaultdict(list)
    checkpoint_counts_by_year: dict[int, list[int]] = defaultdict(list)

    for case in cases:
        cutoff = int(case.cutoff_bar)
        chart_start = cutoff - (LOOKBACK_BARS - 1)
        objects = enumerate_checkpoint_f3_objects(ridge, chart_start, cutoff)
        count = len(objects)
        checkpoint_counts.append(count)
        checkpoint_counts_by_stratum[str(case.stratum)].append(count)
        checkpoint_counts_by_year[int(case.year)].append(count)
        for identity in objects:
            observed[tuple(identity)].add(cutoff)

    if not observed:
        raise RuntimeError("frozen checkpoint census produced no F3 identities")

    lineage_index = build_lineage_index(ridge)
    traces = []
    for identity in sorted(observed):
        traces.append(
            trace_f3_identity(
                lineage_index,
                identity,
                observed_checkpoints=sorted(observed[identity]),
            )
        )

    summary = summarize_publication_precheck(checkpoint_counts, traces)
    first_known_lags = []
    observed_checkpoint_multiplicity = []
    for row in traces:
        event = row.get("first_event")
        if event is not None:
            first_known_lags.append(
                int(row["first_observed_checkpoint"]) - int(event["first_known_confirmation_bar"])
            )
        observed_checkpoint_multiplicity.append(int(row["observed_checkpoint_count"]))

    hard_pass = bool(summary["all_hard_gates_pass"])
    contract_precheck = {
        "v065_append_only_publication_concept_transplantable": hard_pass,
        "v065_direct_function_reuse_authorized": False,
        "v065_direct_function_reuse_block_reason": (
            "legacy canonical identity is phase + five filtered bars; F3 canonical identity is ordered five ridge IDs"
        ),
        "v064_raw_projection_direct_adapter_compatible": False,
        "v064_raw_projection_direct_adapter_block_reason": (
            "legacy locate_birth_predecessor requires five birth nodes consecutive at the birth level; F3 is nonconsecutive"
        ),
        "raw_projection_executed": False,
        "raw_projection_changed": False,
        "predecessor_semantics_changed": False,
    }

    next_step = (
        "freeze and test v0.7.3 F3-specific predecessor/raw-projection adapter; do not reopen F3 object selection and do not retest qualification or direction yet"
        if hard_pass
        else
        "repair causal F3 event/publication semantics under a separately frozen protocol without changing the v0.7.1 F3 object definition"
    )

    result = {
        "schema": "two_wave_f3_causal_publication_transplant_precheck@0.7.2",
        "protocol": PROTOCOL,
        "protocol_freeze_commit": PROTOCOL_FREEZE_COMMIT,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_manifest_verified": bool(source_audit["manifest_verified"]),
        "sampling_commitment_sha256": commitment,
        "checkpoint_count": len(cases),
        "checkpoint_stratum_counts": {
            key: sum(1 for case in cases if case.stratum == key)
            for key in ("candidate", "control")
        },
        "checkpoint_year_counts": {
            str(year): sum(1 for case in cases if int(case.year) == year)
            for year in range(2015, 2021)
        },
        "legacy_chain_replayed_for_checkpoint_sampling_only": legacy_sampling_construction,
        "checkpoint_f3_object_count_by_stratum": {
            key: _dist(values) for key, values in sorted(checkpoint_counts_by_stratum.items())
        },
        "checkpoint_f3_object_count_by_year": {
            str(year): _dist(values) for year, values in sorted(checkpoint_counts_by_year.items())
        },
        "publication_precheck": summary,
        "first_observed_checkpoint_minus_first_known_event_bars": _dist(first_known_lags),
        "checkpoint_observation_count_per_unique_f3_identity": _dist(observed_checkpoint_multiplicity),
        "historical_downstream_contract_precheck": contract_precheck,
        "primary_category": summary["primary_category"],
        "next_authorized_step": next_step,
        "development_discovery_only": True,
        "human_reference_labels_used": False,
        "final_reference_file_read": False,
        "annotator_notes_used": False,
        "annotator_confidence_used": False,
        "future_outcome_used": False,
        "direction_prediction_used": False,
        "F3_definition_changed": False,
        "threshold_fitting_performed": False,
        "bar_distance_tolerance_fitted": False,
        "skip_count_threshold_fitted": False,
        "persistence_threshold_fitted": False,
        "raw_projection_changed": False,
        "qualification_changed": False,
        "direction_winner_changed": False,
        "morphology_acceptance": False,
        "trade_authority": False,
        "production_authority": False,
        "case_level_table_written": False,
        "object_level_table_written": False,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "RESULT.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
