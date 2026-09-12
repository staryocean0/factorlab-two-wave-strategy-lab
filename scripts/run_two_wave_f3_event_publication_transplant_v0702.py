#!/usr/bin/env python3
"""Formal v0.7.2 F3 causal event/publication and downstream transplant precheck."""
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

from factor_lab.visual_structure.two_wave.d1_huber_margin_rescue_v0625 import d1_primary_margin_rescue
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import build_ridge_run
from factor_lab.visual_structure.two_wave.f3_event_publication_transplant_v0702 import (
    frozen_decision,
    summarize_case,
    summarize_cases,
)
from factor_lab.visual_structure.two_wave.path_gate_demotion_v0618 import requalify_v066_control
from factor_lab.visual_structure.two_wave.published_identity_qualification_v066 import qualify_published_raw_identity
from factor_lab.visual_structure.two_wave.reference_label_freeze_v0648 import validate_final_reference_frame
from factor_lab.visual_structure.two_wave.reference_label_packet_v0648 import sampling_commitment, select_blinded_cases
from factor_lab.visual_structure.two_wave.same_scale_v04 import evaluate_pair
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

PROTOCOL = "docs/research/TWO_WAVE_F3_CAUSAL_EVENT_PUBLICATION_TRANSPLANT_V0702_PROTOCOL.md"
PROTOCOL_FREEZE_COMMIT = "3e4e12d27dc28f93aa3079d8ea0899601931ec60"
REFERENCE_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/FINAL_REFERENCE_LABELS.csv"
COMMITMENT_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/SAMPLING_COMMITMENT.json"
OUTPUT_DIR = ROOT / "experiments/two_wave_f3_event_publication_transplant_v0702"
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
        raise RuntimeError("frozen sampling commitment record mismatch")

    bars, source_audit = load_development_bars(DATA_PATH, MANIFEST_PATH)
    frame = pd.read_parquet(DATA_PATH).copy()
    closes = [float(x["close"]) for x in bars]
    cfg = MaturityConfig(timeframe=VIEW)

    ridge = build_ridge_run(bars, cfg=cfg)
    if ridge.lineage_anomalies:
        raise AssertionError(f"v0.5.2 ridge lineage anomalies: {len(ridge.lineage_anomalies)}")

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

    case_records = []
    positive_candidate_count = 0
    anchored_count = 0
    interface_publications = {}

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
        row = summarize_case(ridge, chart_start, cutoff, cells, kinds, human_bars, bars)
        case_records.append(row)

        for publication_row in row["valid_publications"]:
            pub = publication_row["publication"]
            key = (
                tuple(pub["object_key"]),
                int(pub["publishing_confirmation_bar"]),
                tuple(int(x) for x in pub["raw_occurrence_bars"]),
            )
            interface_publications.setdefault(key, pub)

    if positive_candidate_count != 16:
        raise RuntimeError(f"reference-positive candidate count drift: {positive_candidate_count} != 16")
    if anchored_count != 11:
        raise RuntimeError(f"anchored reference-positive count drift: {anchored_count} != 11")

    summary = summarize_cases(case_records)

    interface_exception_count = 0
    interface_exception_types: Counter[str] = Counter()
    qualified_count = 0
    d1_counts: Counter[str] = Counter()
    v0625_counts: Counter[str] = Counter()
    d1_decisive_override_count = 0

    for pub in interface_publications.values():
        try:
            record = evaluate_pair(pub["points"], list(bars), cfg, source="F3_v0702_transplant_precheck")
            control = qualify_published_raw_identity(
                str(pub["phase"]),
                pub["raw_occurrence_bars"],
                int(pub["publishing_confirmation_bar"]),
                bars,
                cfg=cfg,
            )
            candidate = requalify_v066_control(control)
            qualified_count += int(bool(candidate["scale_qualified"]))
            d1 = str(record["direction_versions"]["D1"])
            d1_counts[d1] += 1
            rescued = d1_primary_margin_rescue(
                d1,
                closes,
                pub["raw_occurrence_bars"],
                float(record["amplitude_unit_price"]),
            )
            v0625_counts[str(rescued["classification"])] += 1
            d1_decisive_override_count += int(bool(rescued["D1_decisive_overridden"]))
            if d1 in {"range", "uptrend", "downtrend"} and str(rescued["classification"]) != d1:
                raise AssertionError("v0.6.25 changed a D1-decisive state")
        except Exception as exc:  # formal aggregate interface audit; no case identifiers emitted
            interface_exception_count += 1
            interface_exception_types[type(exc).__name__] += 1

    decision = frozen_decision(summary, interface_exception_count, d1_decisive_override_count)

    n_interface = len(interface_publications)
    result = {
        "schema": "two_wave_f3_event_publication_transplant_precheck@0.7.2",
        "protocol": PROTOCOL,
        "protocol_freeze_commit": PROTOCOL_FREEZE_COMMIT,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_manifest_verified": bool(source_audit["manifest_verified"]),
        "final_reference_sha256": EXPECTED_REFERENCE_SHA256,
        "sampling_commitment_sha256": commitment,
        "construction": construction,
        "reference_positive_candidate_cases": positive_candidate_count,
        "anchored_reference_positive_cases": anchored_count,
        "f3_event_publication_summary": summary,
        "downstream_transplant_interface_precheck": {
            "unique_published_f3_raw_records": n_interface,
            "interface_exception_count": interface_exception_count,
            "interface_exception_type_counts": dict(sorted(interface_exception_types.items())),
            "v0618_qualified_count": qualified_count,
            "v0618_qualified_fraction": qualified_count / n_interface if n_interface else None,
            "D1_state_counts": dict(sorted(d1_counts.items())),
            "v0625_state_counts": dict(sorted(v0625_counts.items())),
            "D1_decisive_override_count": d1_decisive_override_count,
            "reference_scoring_performed": False,
        },
        "frozen_decision": decision,
        "primary_category": decision["primary_category"],
        "development_discovery_only": True,
        "human_reference_labels_used_for_semantic_preservation_only": True,
        "annotator_notes_used": False,
        "annotator_confidence_used": False,
        "future_outcome_used": False,
        "threshold_fitting_performed": False,
        "bar_distance_tolerance_fitted": False,
        "persistence_threshold_fitted": False,
        "qualification_threshold_retuned": False,
        "direction_threshold_retuned": False,
        "projection_geometry_changed_from_frozen_v0702_adapter": False,
        "active_parent_authority_granted": False,
        "qualification_authority_restored": False,
        "direction_winner_changed": False,
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
