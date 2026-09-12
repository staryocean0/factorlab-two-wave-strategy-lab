#!/usr/bin/env python3
"""Formal v0.6.52 ordinal-0 predecessor / first-valid publication lineage audit."""
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
from factor_lab.visual_structure.two_wave.ordinal0_predecessor_support_v064 import (
    project_birth_with_predecessor,
)
from factor_lab.visual_structure.two_wave.ordinal0_publication_lineage_v0652 import (
    frozen_decision,
    summarize_groups,
    validate_projection_contract,
)
from factor_lab.visual_structure.two_wave.path_gate_demotion_v0618 import (
    requalify_v066_control,
)
from factor_lab.visual_structure.two_wave.published_identity_qualification_v066 import (
    qualify_published_raw_identity,
)
from factor_lab.visual_structure.two_wave.reference_label_packet_v0648 import (
    sampling_commitment,
    select_blinded_cases,
)
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from factor_lab.visual_structure.two_wave.scale_invariant_predecessor_publication_v065 import (
    evidence_order_key,
    publish_first_valid_candidate,
)
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import (
    canonicalize_tuple_births,
)
from scripts.build_two_wave_independent_reference_packet_v0648 import (
    DATA_PATH,
    EXPECTED_SOURCE_SHA256,
    MANIFEST_PATH,
    VIEW,
)

PROTOCOL = "docs/research/TWO_WAVE_ORDINAL0_FIRST_VALID_PUBLICATION_LINEAGE_AUDIT_V0652_PROTOCOL.md"
OUTPUT_DIR = ROOT / "experiments/two_wave_ordinal0_publication_lineage_audit_v0652"
COMMITMENT_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/SAMPLING_COMMITMENT.json"
EXPECTED_COMMITMENT = "f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8"
EXPECTED_V0618_QUALIFIED_PUBLICATIONS = 2115


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_group_records(bars: list[dict]) -> tuple[list[dict], dict]:
    cfg = MaturityConfig(timeframe=VIEW)
    ridge = build_ridge_run(bars, cfg=cfg)
    if ridge.lineage_anomalies:
        raise AssertionError(f"v0.5.2 lineage anomalies: {len(ridge.lineage_anomalies)}")

    canonical_rows = canonicalize_tuple_births(ridge.tuple_births, bars)
    groups: dict[tuple[str, tuple[int, ...]], list[dict]] = defaultdict(list)
    valid_evidence_members = 0
    projection_contract_verified = 0

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
        if bool(candidate.get("valid")):
            validate_projection_contract(candidate, filtered)
            valid_evidence_members += 1
            projection_contract_verified += 1
        groups[(phase, filtered)].append(candidate)

    if len(groups) != len(canonical_rows):
        raise AssertionError("grouping drifted from canonical filtered identity universe")

    out = []
    no_valid = 0
    total_suppressed = 0
    qualification_count = 0
    all_prepublication_reason_counts: Counter[str] = Counter()

    for (phase, filtered), members in sorted(groups.items(), key=lambda x: (x[0][1], x[0][0])):
        ordered = sorted((dict(x) for x in members), key=evidence_order_key)
        publication = publish_first_valid_candidate(phase, filtered, ordered)
        event = publication["publication_event"]
        if event is None:
            if any(bool(x.get("valid")) for x in ordered):
                raise AssertionError("valid evidence exists but publication is absent")
            no_valid += 1
            continue

        first_valid_index = next((i for i, row in enumerate(ordered) if bool(row.get("valid"))), None)
        if first_valid_index is None:
            raise AssertionError("published identity has no valid evidence")
        publishing_member = ordered[first_valid_index]
        if str(publishing_member["event_id"]) != str(event["publishing_member_event_id"]):
            raise AssertionError("v0.6.5 publication is not the first valid ordered member")
        if int(event["prior_invalid_evidence_count"]) != first_valid_index:
            raise AssertionError("published prior-invalid count drift")
        if int(event["publishing_birth_level"]) != int(publishing_member["birth_level"]):
            raise AssertionError("publishing birth level drift")
        if int(event["publishing_birth_confirmation_bar"]) != int(publishing_member["birth_confirmation_bar"]):
            raise AssertionError("publishing confirmation drift")
        if [int(x) for x in event["published_raw_occurrence_bars"]] != [
            int(x) for x in publishing_member["raw_occurrence_bars"]
        ]:
            raise AssertionError("published raw tuple differs from first valid member")

        computed_suppressed = 0
        published_raw = tuple(int(x) for x in publishing_member["raw_occurrence_bars"])
        for later in ordered[first_valid_index + 1 :]:
            if bool(later.get("valid")) and tuple(int(x) for x in later["raw_occurrence_bars"]) != published_raw:
                computed_suppressed += 1
        if computed_suppressed != int(publication["suppressed_would_be_rewrite_count"]):
            raise AssertionError("suppressed rewrite count drift")
        total_suppressed += computed_suppressed

        for row in ordered[:first_valid_index]:
            all_prepublication_reason_counts[str(row.get("reason"))] += 1

        raw = tuple(int(x) for x in event["published_raw_occurrence_bars"])
        confirmation = int(event["publishing_birth_confirmation_bar"])
        control = qualify_published_raw_identity(phase, raw, confirmation, bars, cfg=cfg)
        candidate = requalify_v066_control(control)
        qualified = bool(candidate["scale_qualified"])
        qualification_count += int(qualified)

        out.append(
            {
                "phase": phase,
                "filtered": list(filtered),
                "ordered_members": ordered,
                "publishing_member": publishing_member,
                "publishing_index": first_valid_index,
                "prior_invalid_count": first_valid_index,
                "publishing_confirmation_bar": confirmation,
                "candidate_qualified": qualified,
            }
        )

    if qualification_count != EXPECTED_V0618_QUALIFIED_PUBLICATIONS:
        raise RuntimeError(
            f"v0.6.18 qualified publication count drift: {qualification_count} != {EXPECTED_V0618_QUALIFIED_PUBLICATIONS}"
        )

    construction = {
        "canonical_filtered_groups": len(canonical_rows),
        "published_groups": len(out),
        "no_valid_publication_groups": no_valid,
        "valid_evidence_members": valid_evidence_members,
        "projection_contract_verified_valid_members": projection_contract_verified,
        "v0618_qualified_publications": qualification_count,
        "suppressed_would_be_rewrite_comparisons_all_published": total_suppressed,
        "all_prepublication_invalid_reason_counts": dict(sorted(all_prepublication_reason_counts.items())),
        "ridge_tuple_births": len(ridge.tuple_births),
    }
    return out, construction


def main() -> int:
    if sha256(DATA_PATH) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("frozen source SHA256 mismatch")
    commitment_record = json.loads(COMMITMENT_PATH.read_text())
    if commitment_record.get("sha256") != EXPECTED_COMMITMENT:
        raise RuntimeError("frozen sampling commitment record mismatch")

    bars, source_audit = load_development_bars(DATA_PATH, MANIFEST_PATH)
    frame = pd.read_parquet(DATA_PATH).copy()
    groups, construction = build_group_records(bars)

    background = summarize_groups(groups)
    primary_groups = [g for g in groups if bool(g["candidate_qualified"])]
    if len(primary_groups) != EXPECTED_V0618_QUALIFIED_PUBLICATIONS:
        raise AssertionError("primary qualified lineage universe drift")
    primary = summarize_groups(primary_groups)
    decision = frozen_decision(primary)

    by_cutoff: dict[int, list[dict]] = defaultdict(list)
    for group in primary_groups:
        by_cutoff[int(group["publishing_confirmation_bar"])].append(group)
    cases = select_blinded_cases(frame, by_cutoff.keys())
    commitment = sampling_commitment(cases)
    if commitment != EXPECTED_COMMITMENT:
        raise RuntimeError("v0.6.48 packet reconstruction commitment drift")
    candidate_cases = [c for c in cases if c.stratum == "candidate"]
    if len(candidate_cases) != 120:
        raise AssertionError("frozen candidate cutoff count drift")
    sample_groups = []
    multi_identity_cutoffs = 0
    for case in candidate_cases:
        matches = by_cutoff.get(int(case.cutoff_bar), [])
        if not matches:
            raise AssertionError("frozen candidate cutoff lacks qualified identity")
        multi_identity_cutoffs += int(len(matches) > 1)
        sample_groups.extend(matches)
    sample_summary = summarize_groups(sample_groups)

    result = {
        "schema": "two_wave_ordinal0_publication_lineage_audit@0.6.52",
        "protocol": PROTOCOL,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_manifest_verified": bool(source_audit["manifest_verified"]),
        "sampling_commitment_sha256": commitment,
        "runtime_lineage_contract": {
            "ordinal0_lower_source": "birth_level_predecessor_occurrence_plus_one",
            "ordinal1_4_lower_source": "previous_selected_raw_anchor_plus_one",
            "source_predecessor_marker_only_on_ordinal0": True,
            "publication_evidence_order": "birth_confirmation_bar_then_birth_level_then_event_id",
            "publication_policy": "first_valid_immutable_later_rewrites_suppressed",
            "projection_contract_verified_valid_members": construction["projection_contract_verified_valid_members"],
            "first_valid_publication_contract_verified_published_groups": construction["published_groups"],
            "contract_verified": True,
        },
        "background_construction": construction,
        "background_publication_universe": background,
        "primary_v0618_qualified_universe": primary,
        "unlabeled_v0648_candidate_cutoff_replication": {
            "candidate_cutoffs": len(candidate_cases),
            "qualified_identity_records_at_candidate_cutoffs": len(sample_groups),
            "multi_identity_cutoffs": multi_identity_cutoffs,
            "lineage_summary": sample_summary,
            "human_reference_labels_used": False,
            "decision_weight": "descriptive_only",
        },
        "frozen_decision": decision,
        "primary_category": decision["primary_category"],
        "human_reference_labels_used": False,
        "annotator_notes_used": False,
        "annotator_confidence_used": False,
        "direction_prediction_used": False,
        "future_outcome_used": False,
        "threshold_fitting_performed": False,
        "projection_geometry_changed": False,
        "publication_policy_changed": False,
        "qualification_changed": False,
        "direction_winner_changed": False,
        "morphology_acceptance": False,
        "trade_authority": False,
        "production_authority": False,
        "case_level_table_written": False,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "RESULT.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
