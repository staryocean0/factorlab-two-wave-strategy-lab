#!/usr/bin/env python3
"""Formal v0.6.49 reference-conditioned qualification failure attribution."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.cycle_scale_qualification_v054 import (
    corresponding_leg_duration_ratios,
)
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.path_gate_demotion_v0618 import requalify_v066_control
from factor_lab.visual_structure.two_wave.published_identity_qualification_v066 import (
    qualify_published_raw_identity,
)
from factor_lab.visual_structure.two_wave.reference_conditioned_qualification_attribution_v0649 import (
    BINARY_SPECS,
    CONTINUOUS_SPECS,
    SCHEMA,
    binary_result,
    continuous_result,
    family_decision,
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
from scripts.run_two_wave_d1_huber_erosion_consensus_v0623 import reconstruct_pair
from scripts.run_two_wave_independent_temporal_replication_v0647 import build_publications

FINAL_REFERENCE = ROOT / "experiments/two_wave_independent_reference_label_v0648/FINAL_REFERENCE_LABELS.csv"
FINAL_FREEZE = ROOT / "experiments/two_wave_independent_reference_label_v0648/FINAL_REFERENCE_FREEZE.json"
SAMPLING = ROOT / "experiments/two_wave_independent_reference_label_v0648/SAMPLING_COMMITMENT.json"
EXPECTED_FINAL_REFERENCE_SHA256 = "321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d"
EXPECTED_SAMPLING_COMMITMENT = "f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8"
PROTOCOL = "docs/research/TWO_WAVE_REFERENCE_CONDITIONED_QUALIFICATION_FAILURE_ATTRIBUTION_V0649_PROTOCOL.md"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _median(values):
    arr = np.asarray(values, dtype=float)
    if arr.size == 0 or not np.isfinite(arr).all():
        raise ValueError("finite identity values required")
    return float(np.median(arr))


def identity_metrics(row: dict, bars: list[dict], frame: pd.DataFrame, cutoff: int) -> tuple[dict, dict]:
    raw = [int(x) for x in row["published_raw_occurrence_bars"]]
    cfg = MaturityConfig(timeframe=VIEW)
    control = qualify_published_raw_identity(
        str(row["phase"]), raw, int(row["publishing_confirmation_bar"]), bars, cfg=cfg
    )
    candidate = requalify_v066_control(control)
    if not bool(candidate["scale_qualified"]):
        raise AssertionError("mapped candidate identity is not v0.6.18 qualified")
    pair = reconstruct_pair(row, bars, VIEW)

    start = int(cutoff) - LOOKBACK_BARS + 1
    if start < 0:
        raise AssertionError("candidate case lacks frozen 96-bar window")
    visible = frame.iloc[start : int(cutoff) + 1]["close"].astype(float).to_numpy()
    if len(visible) != LOOKBACK_BARS:
        raise AssertionError("visible case window length drift")
    visible_range = float(np.max(visible) - np.min(visible))
    if not math.isfinite(visible_range) or visible_range <= 0:
        raise AssertionError("non-positive visible close range")
    anchor_closes = [float(bars[i]["close"]) for i in raw]
    leg_ratios = corresponding_leg_duration_ratios(control)
    cycles = [float(x) for x in control["cycle_durations"]]
    if min(cycles) <= 0:
        raise AssertionError("non-positive cycle duration")

    continuous = {
        "confirmation_delay_bars": float(control["confirmation_delay_bars"]),
        "completion_buffer_fraction": float(control["confirmation_delay_bars"]) / 95.0,
        "parent_span_bars": float(raw[-1] - raw[0]),
        "parent_span_fraction": float(raw[-1] - raw[0]) / 95.0,
        "parent_anchor_excursion_fraction": (max(anchor_closes) - min(anchor_closes)) / visible_range,
        "amplitude_unit_fraction": float(pair["amplitude_unit_price"]) / visible_range,
        "cycle_duration_ratio": max(cycles) / min(cycles),
        "corresponding_leg_duration_max_ratio": max(float(x) for x in leg_ratios),
        "amplitude_ratio": float(control["amplitude_ratio"]),
        "min_leg_efficiency": min(float(x) for x in control["leg_efficiencies"]),
        "max_leg_jump_share": max(float(x) for x in control["leg_jump_shares"]),
        "max_leg_flat_share": max(float(x) for x in control["leg_flat_shares"]),
    }
    v043 = set(str(x) for x in control["v043_scale_rejection_reasons"])
    binary = {
        "inefficient_leg_triggered": "inefficient_leg" in v043,
        "jump_dominated_leg_triggered": "jump_dominated_leg" in v043,
        "corresponding_leg_duration_mismatch_triggered": "corresponding_leg_duration_mismatch" in v043,
    }
    return continuous, binary


def aggregate_case(rows: list[dict], bars: list[dict], frame: pd.DataFrame, cutoff: int) -> dict:
    continuous_by_name: dict[str, list[float]] = defaultdict(list)
    binary_by_name: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        c, b = identity_metrics(row, bars, frame, cutoff)
        for key, value in c.items():
            continuous_by_name[key].append(float(value))
        for key, value in b.items():
            binary_by_name[key].append(bool(value))
    n = len(rows)
    if n < 1:
        raise AssertionError("candidate cutoff has no qualified identity")
    out = {key: _median(values) for key, values in continuous_by_name.items()}
    out["qualified_identity_count_at_cutoff"] = float(n)
    out.update({key: any(values) for key, values in binary_by_name.items()})
    out["multi_identity_at_cutoff"] = n > 1
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="experiments/two_wave_reference_conditioned_qualification_attribution_v0649",
    )
    args = parser.parse_args()
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.mkdir(parents=True, exist_ok=True)

    if sha256_file(DATA_PATH) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("frozen Development source SHA256 mismatch")
    if sha256_file(FINAL_REFERENCE) != EXPECTED_FINAL_REFERENCE_SHA256:
        raise RuntimeError("final reference SHA256 mismatch")
    freeze = json.loads(FINAL_FREEZE.read_text())
    if freeze.get("final_reference_sha256") != EXPECTED_FINAL_REFERENCE_SHA256:
        raise RuntimeError("final reference freeze belongs to different bytes")
    if freeze.get("unresolved_disagreements") != 0:
        raise RuntimeError("final reference still has unresolved disagreements")
    sampling_record = json.loads(SAMPLING.read_text())
    if sampling_record.get("sha256") != EXPECTED_SAMPLING_COMMITMENT:
        raise RuntimeError("sampling commitment record drift")

    bars, source_audit = load_development_bars(DATA_PATH, MANIFEST_PATH)
    frame = pd.read_parquet(DATA_PATH).copy()
    publication_rows, _, generation_summary = build_publications(VIEW, bars)
    qualified_rows = [r for r in publication_rows if bool(r["candidate_qualified"])]
    by_cutoff: dict[int, list[dict]] = defaultdict(list)
    for row in qualified_rows:
        by_cutoff[int(row["publishing_confirmation_bar"])].append(row)

    cases = select_blinded_cases(frame, by_cutoff.keys())
    commitment = sampling_commitment(cases)
    if commitment != EXPECTED_SAMPLING_COMMITMENT:
        raise RuntimeError("hidden deterministic case mapping no longer matches frozen commitment")

    reference = pd.read_csv(FINAL_REFERENCE, dtype=str, keep_default_na=False).set_index("case_id")
    if sorted(reference.index.tolist()) != sorted(c.case_id for c in cases):
        raise RuntimeError("final reference membership differs from frozen packet")

    candidate_cases = [c for c in cases if c.stratum == "candidate"]
    control_cases = [c for c in cases if c.stratum == "control"]
    if len(candidate_cases) != 120 or len(control_cases) != 120:
        raise AssertionError("frozen candidate/control count drift")

    records = []
    for case in candidate_cases:
        presence = str(reference.loc[case.case_id, "two_complete_same_scale_waves"])
        if presence not in {"yes", "no"}:
            raise AssertionError("candidate reference partition is not exactly yes/no")
        rows = by_cutoff.get(int(case.cutoff_bar), [])
        if not rows:
            raise AssertionError("candidate cutoff lacks v0.6.18-qualified identity")
        metrics = aggregate_case(rows, bars, frame, int(case.cutoff_bar))
        records.append({"reference_presence": presence, **metrics})

    yes = [r for r in records if r["reference_presence"] == "yes"]
    no = [r for r in records if r["reference_presence"] == "no"]
    if len(yes) != 16 or len(no) != 104:
        raise AssertionError(f"frozen v0.6.48 partition drifted: yes={len(yes)} no={len(no)}")

    continuous = {}
    for spec in CONTINUOUS_SPECS:
        continuous[spec.name] = continuous_result(
            spec,
            [r[spec.name] for r in no],
            [r[spec.name] for r in yes],
        )
    binary = {}
    for name, family in BINARY_SPECS:
        binary[name] = binary_result(
            [r[name] for r in no],
            [r[name] for r in yes],
            family,
        )
    decision = family_decision(continuous, binary)

    control_presence = [str(reference.loc[c.case_id, "two_complete_same_scale_waves"]) for c in control_cases]
    result = {
        "schema": SCHEMA,
        "protocol": PROTOCOL,
        "source_manifest_verified": bool(source_audit["manifest_verified"]),
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "sampling_commitment_sha256": commitment,
        "final_reference_sha256": EXPECTED_FINAL_REFERENCE_SHA256,
        "candidate_qualified_publications_available": int(generation_summary["candidate_qualified"]),
        "candidate_cases": 120,
        "reference_yes_candidates": 16,
        "reference_no_candidates": 104,
        "control_cases": 120,
        "control_reference_yes": int(sum(x == "yes" for x in control_presence)),
        "continuous_diagnostics": continuous,
        "binary_diagnostics": binary,
        "family_decision": decision,
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
    (output / "RESULT.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
