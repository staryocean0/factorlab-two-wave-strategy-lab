#!/usr/bin/env python3
"""Run the pre-frozen v0.6.48 aggregate scoring only after final reference freeze."""
from __future__ import annotations

import argparse
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
from factor_lab.visual_structure.two_wave.reference_label_packet_v0648 import sampling_commitment, select_blinded_cases
from factor_lab.visual_structure.two_wave.reference_label_scoring_v0648 import score_by_year, score_reference_cases
from scripts.build_two_wave_independent_reference_packet_v0648 import (
    DATA_PATH,
    EXPECTED_SOURCE_SHA256,
    MANIFEST_PATH,
    VIEW,
)
from scripts.run_two_wave_independent_temporal_replication_v0647 import build_publications, record_state

COMMITMENT_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/SAMPLING_COMMITMENT.json"
DETERMINACY_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/SCORING_DETERMINACY_AUDIT.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-reference", type=Path, required=True)
    parser.add_argument("--freeze-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    freeze = json.loads(args.freeze_audit.read_text())
    final_bytes = args.final_reference.read_bytes()
    if freeze.get("final_reference_sha256") != sha256_bytes(final_bytes):
        raise RuntimeError("final reference bytes do not match frozen SHA256")
    if freeze.get("model_scoring_allowed") is not True:
        raise RuntimeError("v0.6.48 first-pass label-quality gates do not authorize model/reference scoring")
    final = validate_final_reference_frame(pd.read_csv(args.final_reference, dtype=str, keep_default_na=False))
    reference = final.set_index("case_id")

    if sha256_file(DATA_PATH) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("frozen main-view source SHA256 mismatch")
    bars, source_audit = load_development_bars(DATA_PATH, MANIFEST_PATH)
    frame = pd.read_parquet(DATA_PATH).copy()
    publication_rows, _, generation_summary = build_publications(VIEW, bars)
    qualified_rows = [r for r in publication_rows if bool(r["candidate_qualified"])]
    by_cutoff: dict[int, list[dict]] = defaultdict(list)
    for row in qualified_rows:
        by_cutoff[int(row["publishing_confirmation_bar"])].append(row)

    cases = select_blinded_cases(frame, by_cutoff.keys())
    commitment = sampling_commitment(cases)
    expected_commitment = json.loads(COMMITMENT_PATH.read_text())["sha256"]
    if commitment != expected_commitment:
        raise RuntimeError("hidden case mapping no longer matches frozen sampling commitment")
    if sorted(c.case_id for c in cases) != sorted(reference.index.tolist()):
        raise RuntimeError("final reference case IDs do not match frozen packet membership")

    determinacy = json.loads(DETERMINACY_PATH.read_text())
    if determinacy.get("sampling_commitment_sha256") != commitment:
        raise RuntimeError("scoring determinacy audit belongs to a different packet")
    if determinacy.get("multi_identity_v0625_state_disagreement_cases") != 0:
        raise RuntimeError("pre-label audit did not establish case-level v0.6.25 determinacy")
    if determinacy.get("multi_identity_d1_state_disagreement_cases") != 0:
        raise RuntimeError("pre-label audit did not establish case-level D1 determinacy")

    closes = frame["close"].astype(float).tolist()
    records = []
    for case in cases:
        ref = reference.loc[case.case_id]
        record = {
            "case_id": case.case_id,
            "year": int(case.year),
            "stratum": case.stratum,
            "reference_presence": str(ref["two_complete_same_scale_waves"]),
            "reference_state": str(ref["parent_state"]),
        }
        if case.stratum == "candidate":
            rows = by_cutoff.get(case.cutoff_bar, [])
            if not rows:
                raise AssertionError("candidate case lacks frozen qualified identity")
            states = [record_state(row, bars, closes, VIEW) for row in rows]
            d1 = sorted(set(str(x["D1"]) for x in states))
            v0625 = sorted(set(str(x["v0625"]) for x in states))
            if len(d1) != 1 or len(v0625) != 1:
                raise RuntimeError("case-level state unanimity assertion drifted after pre-label audit")
            record["D1"] = d1[0]
            record["v0625"] = v0625[0]
        else:
            if by_cutoff.get(case.cutoff_bar):
                raise AssertionError("control case unexpectedly maps to a qualified publication")
            record["D1"] = None
            record["v0625"] = None
        records.append(record)

    aggregate = score_reference_cases(records)
    result = {
        "schema": "two_wave_independent_reference_scoring_v0648@1.0",
        "primary_gated_model": "v0.6.25_absolute_margin_erosion_consensus_rescue",
        "qualification_policy": "v0.6.18_path_gate_demotion",
        "descriptive_comparator": "D1",
        "source_manifest_verified": bool(source_audit["manifest_verified"]),
        "candidate_qualified_publications": int(generation_summary["candidate_qualified"]),
        "sampling_commitment_sha256": commitment,
        "final_reference_sha256": freeze["final_reference_sha256"],
        "aggregate": aggregate,
        "by_year_descriptive": score_by_year(records),
        "verdict": (
            "independent_reference_label_calibration_supported_on_frozen_2015_2020_blinded_sample"
            if aggregate["all_calibration_support_gates_pass"]
            else "v0648_independent_reference_calibration_gates_not_all_pass"
        ),
        "morphology_acceptance": False,
        "direction_winner_changed": False,
        "trade_authority": False,
        "production_authority": False,
        "future_outcome_used": False,
        "threshold_retuning_performed": False,
    }

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "REFERENCE_SCORING_RESULT.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
