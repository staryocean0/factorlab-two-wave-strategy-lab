#!/usr/bin/env python3
"""Pre-label v0.6.48 case-level scoring determinacy audit.

This audit is intentionally run before any independent annotations exist. It
reconstructs the frozen 240-case sample and asks whether a selected candidate
cutoff maps to exactly one v0.6.18-qualified parent identity, or at least to a
single unanimous D1/v0.6.25 state. It never reads human labels, future returns,
PnL, harmless comparison offsets, or post-cutoff bars.
"""
from __future__ import annotations

import argparse
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
from factor_lab.visual_structure.two_wave.reference_label_packet_v0648 import (
    sampling_commitment,
    select_blinded_cases,
)
from scripts.build_two_wave_independent_reference_packet_v0648 import (
    DATA_PATH,
    EXPECTED_SOURCE_SHA256,
    MANIFEST_PATH,
    VIEW,
)
from scripts.run_two_wave_independent_temporal_replication_v0647 import (
    build_publications,
    record_state,
)

COMMITMENT_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/SAMPLING_COMMITMENT.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="experiments/two_wave_independent_reference_label_v0648/SCORING_DETERMINACY_AUDIT.json",
    )
    args = parser.parse_args()

    if sha256_file(DATA_PATH) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("frozen main-view source SHA256 mismatch")

    bars, source_audit = load_development_bars(DATA_PATH, MANIFEST_PATH)
    frame = pd.read_parquet(DATA_PATH).copy()
    publication_rows, _, generation_summary = build_publications(VIEW, bars)
    qualified_rows = [r for r in publication_rows if bool(r["candidate_qualified"])]
    qualified_by_cutoff: dict[int, list[dict]] = defaultdict(list)
    for row in qualified_rows:
        qualified_by_cutoff[int(row["publishing_confirmation_bar"])].append(row)

    cases = select_blinded_cases(frame, qualified_by_cutoff.keys())
    expected_commitment = json.loads(COMMITMENT_PATH.read_text())["sha256"]
    actual_commitment = sampling_commitment(cases)
    if actual_commitment != expected_commitment:
        raise RuntimeError("reconstructed case mapping does not match frozen sampling commitment")

    closes = frame["close"].astype(float).tolist()
    multiplicity = Counter()
    d1_case_states = Counter()
    v0625_case_states = Counter()
    multi_identity_cases = 0
    multi_identity_d1_disagreement = 0
    multi_identity_v0625_disagreement = 0
    candidate_cases = 0
    control_cases = 0

    for case in cases:
        if case.stratum == "control":
            control_cases += 1
            if qualified_by_cutoff.get(case.cutoff_bar):
                raise AssertionError("control case unexpectedly maps to a qualified publication")
            continue

        candidate_cases += 1
        rows = qualified_by_cutoff.get(case.cutoff_bar, [])
        if not rows:
            raise AssertionError("candidate case lacks a qualified publication")
        multiplicity[len(rows)] += 1
        if len(rows) > 1:
            multi_identity_cases += 1

        d1_states = []
        v0625_states = []
        for row in rows:
            state = record_state(row, bars, closes, VIEW)
            d1_states.append(str(state["D1"]))
            v0625_states.append(str(state["v0625"]))

        unique_d1 = sorted(set(d1_states))
        unique_v0625 = sorted(set(v0625_states))
        if len(unique_d1) == 1:
            d1_case_states[unique_d1[0]] += 1
        elif len(rows) > 1:
            multi_identity_d1_disagreement += 1
        if len(unique_v0625) == 1:
            v0625_case_states[unique_v0625[0]] += 1
        elif len(rows) > 1:
            multi_identity_v0625_disagreement += 1

    if candidate_cases != 120 or control_cases != 120:
        raise AssertionError("frozen v0.6.48 stratum counts drifted")

    if multi_identity_cases == 0:
        conclusion = "case_level_scoring_determinate_unique_qualified_identity_at_every_candidate_cutoff"
    elif multi_identity_v0625_disagreement == 0:
        conclusion = "v0625_case_state_determinate_despite_multiple_qualified_identities"
    else:
        conclusion = "additional_prelabel_case_identity_selection_rule_required_before_reference_scoring"

    result = {
        "schema": "two_wave_v0648_scoring_determinacy_audit@1.0",
        "performed_before_independent_labels": True,
        "independent_labels_read": False,
        "model_reference_scoring_started": False,
        "hidden_mapping_commitment_verified": True,
        "sampling_commitment_sha256": actual_commitment,
        "source_manifest_verified": bool(source_audit["manifest_verified"]),
        "candidate_qualified_publications": int(generation_summary["candidate_qualified"]),
        "selected_candidate_cases": candidate_cases,
        "selected_control_cases": control_cases,
        "qualified_identity_multiplicity_counts": {str(k): int(v) for k, v in sorted(multiplicity.items())},
        "multi_identity_candidate_cases": multi_identity_cases,
        "multi_identity_d1_state_disagreement_cases": multi_identity_d1_disagreement,
        "multi_identity_v0625_state_disagreement_cases": multi_identity_v0625_disagreement,
        "candidate_case_D1_state_counts_when_unanimous": dict(sorted(d1_case_states.items())),
        "candidate_case_v0625_state_counts_when_unanimous": dict(sorted(v0625_case_states.items())),
        "conclusion": conclusion,
        "morphology_acceptance": False,
        "trade_authority": False,
        "production_authority": False,
    }

    out = Path(args.output)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
