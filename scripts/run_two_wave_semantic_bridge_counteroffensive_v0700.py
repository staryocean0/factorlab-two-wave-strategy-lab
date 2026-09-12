#!/usr/bin/env python3
"""Formal v0.7.0 semantic-bridge counteroffensive / salvage staircase."""
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
from factor_lab.visual_structure.two_wave.ordinal0_predecessor_support_v064 import project_birth_with_predecessor
from factor_lab.visual_structure.two_wave.path_gate_demotion_v0618 import requalify_v066_control
from factor_lab.visual_structure.two_wave.published_identity_qualification_v066 import qualify_published_raw_identity
from factor_lab.visual_structure.two_wave.reference_label_freeze_v0648 import validate_final_reference_frame
from factor_lab.visual_structure.two_wave.reference_label_packet_v0648 import sampling_commitment, select_blinded_cases
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from factor_lab.visual_structure.two_wave.scale_invariant_predecessor_publication_v065 import publish_first_valid_candidate
from factor_lab.visual_structure.two_wave.semantic_bridge_counteroffensive_v0700 import (
    common_scale_support,
    count_exact_tuple_support,
    count_tuple_birth_support,
    five_bars_hit_cells,
    frozen_decision,
    human_support_cells,
    infer_human_kinds,
    raw_cell_extreme,
    summarize_cases,
)
from factor_lab.visual_structure.two_wave.semantic_object_parent_representation_v0650 import (
    canonical_identity,
    parse_human_anchors,
)
from scripts.build_two_wave_independent_reference_packet_v0648 import (
    DATA_PATH,
    EXPECTED_SOURCE_SHA256,
    MANIFEST_PATH,
    VIEW,
)

PROTOCOL = "docs/research/TWO_WAVE_SEMANTIC_BRIDGE_COUNTEROFFENSIVE_V0700_PROTOCOL.md"
PROTOCOL_FREEZE_COMMIT = "525948dc7f22a01fdfd6df453a935181df41e0f6"
REFERENCE_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/FINAL_REFERENCE_LABELS.csv"
COMMITMENT_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/SAMPLING_COMMITMENT.json"
OUTPUT_DIR = ROOT / "experiments/two_wave_semantic_bridge_counteroffensive_v0700"
EXPECTED_REFERENCE_SHA256 = "321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d"
EXPECTED_COMMITMENT = "f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8"
EXPECTED_QUALIFIED_PUBLICATIONS = 2115
LOOKBACK_BARS = 96


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_qualified_publications(ridge, bars: list[dict]) -> tuple[list[dict], dict]:
    cfg = MaturityConfig(timeframe=VIEW)
    groups: dict[tuple[str, tuple[int, ...]], list[dict]] = defaultdict(list)
    for birth in ridge.tuple_births:
        phase = str(birth.nodes[0].node.kind)
        filtered = tuple(int(x) for x in birth.occurrence_indices)
        candidate = dict(
            project_birth_with_predecessor(
                birth,
                ridge.ridge_nodes_by_level[int(birth.level)],
                bars,
            )
        )
        candidate.update(
            {
                "event_id": str(birth.event_id),
                "birth_level": int(birth.level),
                "birth_confirmation_bar": int(birth.confirmation_index),
            }
        )
        groups[(phase, filtered)].append(candidate)

    rows: list[dict] = []
    published = 0
    for (phase, filtered), members in sorted(groups.items(), key=lambda x: (x[0][1], x[0][0])):
        publication = publish_first_valid_candidate(phase, filtered, members)
        event = publication["publication_event"]
        if event is None:
            continue
        published += 1
        raw = tuple(int(x) for x in event["published_raw_occurrence_bars"])
        confirmation = int(event["publishing_birth_confirmation_bar"])
        control = qualify_published_raw_identity(phase, raw, confirmation, bars, cfg=cfg)
        candidate = requalify_v066_control(control)
        if not bool(candidate["scale_qualified"]):
            continue
        rows.append(
            {
                "phase": phase,
                "five_filtered_occurrence_bars": list(filtered),
                "published_raw_occurrence_bars": list(raw),
                "publishing_confirmation_bar": confirmation,
                "candidate_qualified": True,
            }
        )

    if len(rows) != EXPECTED_QUALIFIED_PUBLICATIONS:
        raise RuntimeError(
            f"v0.6.18 qualified publication count drift: {len(rows)} != {EXPECTED_QUALIFIED_PUBLICATIONS}"
        )
    return rows, {"canonical_groups": len(groups), "published_groups": published, "qualified_publications": len(rows)}


def strict_raw_turns(bars: list[int], kinds: list[str], closes: list[float]) -> bool:
    x = [float(closes[i]) for i in bars]
    for i in range(4):
        if kinds[i] == "low" and not x[i + 1] > x[i]:
            return False
        if kinds[i] == "high" and not x[i + 1] < x[i]:
            return False
    return True


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

    records: list[dict] = []
    candidate_positive_count = 0
    anchored_positive_count = 0
    for case in cases:
        if case.stratum != "candidate":
            continue
        ref = reference.loc[case.case_id].to_dict()
        if str(ref["two_complete_same_scale_waves"]) != "yes":
            continue
        candidate_positive_count += 1
        human = parse_human_anchors(ref)
        if human is None:
            continue
        anchored_positive_count += 1

        cutoff = int(case.cutoff_bar)
        chart_start = cutoff - (LOOKBACK_BARS - 1)
        human_bars = [chart_start + int(x) for x in human]
        kinds = infer_human_kinds(human_bars, closes)
        cells = human_support_cells(human_bars, chart_start, cutoff)

        raw_extremes = [raw_cell_extreme(cell, kind, closes) for cell, kind in zip(cells, kinds)]
        raw_anchor_exact = [raw_extremes[i] == human_bars[i] for i in range(5)]
        L0 = strict_raw_turns(raw_extremes, kinds, closes)

        common = common_scale_support(ridge, cells, kinds, cutoff)
        common_levels = list(common["common_levels"])
        L1 = bool(common_levels)
        nearest = []
        for i, occurrences in enumerate(common["occurrences_by_ordinal"]):
            if not occurrences:
                nearest.append(None)
            else:
                nearest.append(min(abs(int(x) - human_bars[i]) for x in occurrences))

        exact_tuple_count = count_exact_tuple_support(ridge, cells, kinds, cutoff)
        birth_count = count_tuple_birth_support(ridge, cells, kinds, cutoff)
        L2 = exact_tuple_count > 0
        L3 = birth_count > 0

        matches = by_cutoff.get(cutoff, [])
        if not matches:
            raise AssertionError("candidate reference-positive cutoff lacks qualified identity")
        canonical = canonical_identity(matches)
        L4, L4_hits = five_bars_hit_cells(
            canonical["five_filtered_occurrence_bars"],
            str(canonical["phase"]),
            cells,
            kinds,
        )
        L5, L5_hits = five_bars_hit_cells(
            canonical["published_raw_occurrence_bars"],
            str(canonical["phase"]),
            cells,
            kinds,
        )

        records.append(
            {
                "L0": L0,
                "L1": L1,
                "L2": L2,
                "L3": L3,
                "L4": L4,
                "L5": L5,
                "raw_anchor_exact": raw_anchor_exact,
                "nearest_common_scale_ridge_distance": nearest,
                "common_scale_level_count": len(common_levels),
                "exact_tuple_match_count": exact_tuple_count,
                "tuple_birth_match_count": birth_count,
                "L4_hits": L4_hits,
                "L5_hits": L5_hits,
            }
        )

    if candidate_positive_count != 16:
        raise RuntimeError(f"reference-positive candidate count drift: {candidate_positive_count} != 16")
    if anchored_positive_count != 11 or len(records) != 11:
        raise RuntimeError(f"anchored reference-positive count drift: {anchored_positive_count} != 11")

    summary = summarize_cases(records)
    decision = frozen_decision(summary)
    result = {
        "schema": "two_wave_semantic_bridge_counteroffensive@0.7.0",
        "protocol": PROTOCOL,
        "protocol_freeze_commit": PROTOCOL_FREEZE_COMMIT,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_manifest_verified": bool(source_audit["manifest_verified"]),
        "final_reference_sha256": EXPECTED_REFERENCE_SHA256,
        "sampling_commitment_sha256": commitment,
        "construction": construction,
        "reference_positive_candidate_cases": candidate_positive_count,
        "anchored_reference_positive_cases": anchored_positive_count,
        "salvage_staircase": summary,
        "frozen_decision": decision,
        "primary_category": decision["primary_category"],
        "component_retention_map": decision["component_retention_map"],
        "development_discovery_only": True,
        "human_reference_labels_used": True,
        "annotator_notes_used": False,
        "annotator_confidence_used": False,
        "direction_prediction_used": False,
        "future_outcome_used": False,
        "threshold_fitting_performed": False,
        "new_object_constructor_fitted": False,
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
