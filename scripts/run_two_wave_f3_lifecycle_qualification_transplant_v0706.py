#!/usr/bin/env python3
"""Formal v0.7.6 F3 lifecycle-publication qualification transplant precheck."""
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
from factor_lab.visual_structure.two_wave.f3_lifecycle_qualification_transplant_v0706 import (
    frozen_decision,
    publication_identity_hash,
    qualification_args,
    qualification_contract_violations,
    summarize_case_semantics as summarize_qualification_case_semantics,
    summarize_qualification_records,
    summarize_semantic_cases,
)
from factor_lab.visual_structure.two_wave.f3_prefix_causal_lifecycle_v0704 import (
    build_lifecycle_for_case,
    summarize_case_semantics as summarize_lifecycle_case_semantics,
)
from factor_lab.visual_structure.two_wave.f3_provisional_lifecycle_publication_v0705 import (
    cache_prefix_static_stores,
    replay_publications_from_cache,
    summarize_case_semantics as summarize_publication_case_semantics,
    summarize_cases as summarize_publication_cases,
)
from factor_lab.visual_structure.two_wave.path_gate_demotion_v0618 import (
    qualify_published_raw_identity_v0618,
)
from factor_lab.visual_structure.two_wave.published_identity_qualification_v066 import (
    qualify_published_raw_identity,
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

PROTOCOL = "docs/research/TWO_WAVE_F3_LIFECYCLE_QUALIFICATION_TRANSPLANT_V0706_PROTOCOL.md"
PROTOCOL_FREEZE_COMMIT = "174188e55f573f43c7dac0e2d5d87f9a223bebaf"
REFERENCE_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/FINAL_REFERENCE_LABELS.csv"
COMMITMENT_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/SAMPLING_COMMITMENT.json"
V0705_RESULT_PATH = ROOT / "experiments/two_wave_f3_provisional_lifecycle_publication_v0705/RESULT.json"
OUTPUT_DIR = ROOT / "experiments/two_wave_f3_lifecycle_qualification_transplant_v0706"
EXPECTED_REFERENCE_SHA256 = "321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d"
EXPECTED_COMMITMENT = "f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8"
LOOKBACK_BARS = 96


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mechanical_upstream(case_rows: list[dict], formal_v0705: dict) -> dict:
    observed = sum(len(row["lifecycle"]["objects"]) for row in case_rows)
    published = sum(int(row["publication"]["publication_count"]) for row in case_rows)
    certified = sum(int(row["publication"]["certified_object_count"]) for row in case_rows)
    certified_published = sum(int(row["publication"]["certified_published_count"]) for row in case_rows)
    unresolved = sum(int(row["publication"]["final_unresolved_object_count"]) for row in case_rows)
    unresolved_published = sum(int(row["publication"]["final_unresolved_published_count"]) for row in case_rows)
    hard = sum(int(row["publication"]["hard_invariant_violation_count"]) for row in case_rows)
    delays = [row["publication"]["publication_delay_bars_from_observation"] for row in case_rows]
    delay_mins = [float(x["min"]) for x in delays if x["min"] is not None]
    delay_medians = [float(x["median"]) for x in delays if x["median"] is not None]
    delay_maxes = [float(x["max"]) for x in delays if x["max"] is not None]
    formal_sem = formal_v0705["semantic_continuity"]
    return {
        "observed_lifecycle_object_count": int(observed),
        "published_lifecycle_object_count": int(published),
        "certified_lifecycle_object_count": int(certified),
        "certified_object_publication_count": int(certified_published),
        "final_unresolved_object_count": int(unresolved),
        "final_unresolved_published_count": int(unresolved_published),
        "publication_delay_min_bars": min(delay_mins) if delay_mins else None,
        "publication_delay_median_bars": 0.0 if delay_medians and all(x == 0.0 for x in delay_medians) else None,
        "publication_delay_max_bars": max(delay_maxes) if delay_maxes else None,
        "publication_hard_invariant_violation_count": int(hard),
        # These two semantic values are overwritten by fresh scoring after the
        # label-free interface/contract gates pass. Until then the formal v0705
        # authority keeps upstream precedence deterministic without unblinding
        # qualification construction to human support cells.
        "published_raw_semantic_support_cases": int(formal_sem["published_raw_semantic_support_cases"]),
        "published_raw_ordinal_hit_cases": [int(x) for x in formal_sem["per_ordinal_published_raw_cell_hit_cases"]],
        "permanent_certificate_gap_case_count": int(formal_sem["permanent_certificate_gap_case_count"]),
        "gap_same_object_provisional_raw_support_cases": int(
            formal_sem["gap_same_object_provisional_raw_support_cases"]
        ),
    }


def main() -> int:
    if sha256(DATA_PATH) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("frozen source SHA256 mismatch")
    if sha256(REFERENCE_PATH) != EXPECTED_REFERENCE_SHA256:
        raise RuntimeError("frozen final-reference SHA256 mismatch")
    commitment_record = json.loads(COMMITMENT_PATH.read_text())
    if commitment_record.get("sha256") != EXPECTED_COMMITMENT:
        raise RuntimeError("frozen sampling commitment record mismatch")
    formal_v0705 = json.loads(V0705_RESULT_PATH.read_text())
    if formal_v0705.get("primary_category") != "v0705_f3_provisional_lifecycle_publication_transplant_supported":
        raise RuntimeError("formal v0705 authority mismatch")

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
        raise RuntimeError("reconstructed v0.6.48 sampling commitment drift")

    final = validate_final_reference_frame(pd.read_csv(REFERENCE_PATH, dtype=str, keep_default_na=False))
    reference = final.set_index("case_id")
    if sorted(c.case_id for c in cases) != sorted(reference.index.tolist()):
        raise RuntimeError("frozen final-reference membership drift")

    # Stage A: reconstruct the frozen anchored universe and v0705 publications,
    # but do not score human support cells through qualification yet.
    case_rows = []
    positive_candidate_count = 0
    anchored_count = 0
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
        prefix_frames = cache_prefix_static_stores(ridge, chart_start, cutoff)
        publication = replay_publications_from_cache(ridge, lifecycle, prefix_frames, bars)
        case_rows.append(
            {
                "lifecycle": lifecycle,
                "publication": publication,
                "cells": cells,
                "kinds": kinds,
                "human_bars": human_bars,
            }
        )

    if positive_candidate_count != 16:
        raise RuntimeError(f"reference-positive candidate count drift: {positive_candidate_count} != 16")
    if anchored_count != 11 or len(case_rows) != 11:
        raise RuntimeError(f"anchored reference-positive count drift: {anchored_count} != 11")

    upstream = _mechanical_upstream(case_rows, formal_v0705)

    # Stage B: label-free qualification interface + contract audit over all
    # immutable v0705 publications in the frozen 11-case universe.
    v054_exceptions: Counter[str] = Counter()
    v0618_exceptions: Counter[str] = Counter()
    v054_evaluated = 0
    v0618_evaluated = 0
    identity_mutation_count = 0
    future_bar_dependency_violation_count = 0
    future_or_trade_violation_count = 0
    qualification_rows = []
    by_case_qualification: list[dict[tuple[str, ...], dict]] = []

    for case_row in case_rows:
        lifecycle = case_row["lifecycle"]
        publication = case_row["publication"]
        case_q: dict[tuple[str, ...], dict] = {}
        for key, state in publication["states"].items():
            pub = state["publication"]
            if pub is None:
                continue
            before = publication_identity_hash(pub)
            try:
                phase, raw, confirmation, prefix = qualification_args(pub, bars)
            except Exception as exc:
                name = f"input_{type(exc).__name__}"
                v054_exceptions[name] += 1
                v0618_exceptions[name] += 1
                if before != publication_identity_hash(pub):
                    identity_mutation_count += 1
                continue

            if len(prefix) != confirmation + 1:
                future_bar_dependency_violation_count += 1

            v054 = None
            v0618 = None
            try:
                v054 = qualify_published_raw_identity(phase, raw, confirmation, prefix, cfg=MaturityConfig(timeframe=VIEW))
                v054_evaluated += 1
            except Exception as exc:
                v054_exceptions[type(exc).__name__] += 1
            try:
                v0618 = qualify_published_raw_identity_v0618(
                    phase,
                    raw,
                    confirmation,
                    prefix,
                    cfg=MaturityConfig(timeframe=VIEW),
                )
                v0618_evaluated += 1
            except Exception as exc:
                v0618_exceptions[type(exc).__name__] += 1

            after = publication_identity_hash(pub)
            mutated = before != after
            identity_mutation_count += int(mutated)

            for q in (v054, v0618):
                if q is not None and (bool(q.get("future_outcome_used")) or bool(q.get("trade_authority"))):
                    future_or_trade_violation_count += 1

            if v054 is None or v0618 is None:
                continue
            contract = qualification_contract_violations(v054, v0618)
            final_certified = bool(lifecycle["objects"][key]["certified"])
            status_at_pub = str(pub["status_at_publication"])
            cert_bar = lifecycle["objects"][key].get("certification_bar")
            strata = {
                "already_certified_at_publication": status_at_pub == "certified",
                "unresolved_at_publication_later_certified": (
                    status_at_pub == "observed_live_unresolved" and final_certified
                    and cert_bar is not None and int(cert_bar) > int(pub["publishing_evidence_bar"])
                ),
                "unresolved_at_publication_still_unresolved": (
                    status_at_pub == "observed_live_unresolved" and not final_certified
                ),
                "final_certified": final_certified,
                "final_unresolved": not final_certified,
            }
            qrow = {
                "v054": v054,
                "v0618": v0618,
                "identity_mutated": bool(mutated),
                "contract_violations": contract,
                "strata": strata,
            }
            qualification_rows.append(qrow)
            case_q[key] = qrow
        by_case_qualification.append(case_q)

    qualification = summarize_qualification_records(qualification_rows)
    interface = {
        "publication_count": int(upstream["published_lifecycle_object_count"]),
        "v054_evaluated_count": int(v054_evaluated),
        "v0618_evaluated_count": int(v0618_evaluated),
        "v054_exception_count": int(sum(v054_exceptions.values())),
        "v054_exception_type_counts": dict(sorted(v054_exceptions.items())),
        "v0618_exception_count": int(sum(v0618_exceptions.values())),
        "v0618_exception_type_counts": dict(sorted(v0618_exceptions.items())),
        "identity_mutation_count": int(identity_mutation_count),
        "future_bar_dependency_violation_count": int(future_bar_dependency_violation_count),
        "future_outcome_or_trade_authority_violation_count": int(future_or_trade_violation_count),
    }

    clean_interface = (
        interface["v054_evaluated_count"] == 1543
        and interface["v0618_evaluated_count"] == 1543
        and interface["v054_exception_count"] == 0
        and interface["v0618_exception_count"] == 0
        and interface["identity_mutation_count"] == 0
        and interface["future_bar_dependency_violation_count"] == 0
        and interface["future_outcome_or_trade_authority_violation_count"] == 0
    )
    clean_contract = qualification["contract_violation_count"] == 0

    # Stage C: only after the label-free interface and policy contract are clean,
    # apply the frozen human support cells for semantic correspondence.
    semantic_rows = []
    publication_records = []
    semantic_scoring_blocked = not (clean_interface and clean_contract)
    if not semantic_scoring_blocked:
        for case_row, case_q in zip(case_rows, by_case_qualification):
            lifecycle = case_row["lifecycle"]
            publication = case_row["publication"]
            cells = case_row["cells"]
            kinds = case_row["kinds"]
            human_bars = case_row["human_bars"]

            lifecycle_sem = summarize_lifecycle_case_semantics(
                lifecycle,
                ridge,
                int(max(human_bars[-1], lifecycle.get("cutoff", human_bars[-1]))),
                cells,
                kinds,
                human_bars,
            )
            # build_lifecycle_for_case does not expose cutoff as a public key in
            # every historical implementation; the semantic scorer only needs
            # the frozen case cutoff, which is the upper edge of cells[-1].
            cutoff = int(cells[-1][1])
            lifecycle_sem = summarize_lifecycle_case_semantics(
                lifecycle,
                ridge,
                cutoff,
                cells,
                kinds,
                human_bars,
            )
            pub_sem = summarize_publication_case_semantics(publication, lifecycle, cells, kinds, human_bars)
            pub_sem["static_support"] = bool(lifecycle_sem["static_support"])
            pub_sem["certified_semantic_support"] = bool(lifecycle_sem["certified_support"])
            pub_sem["permanent_certificate_gap_case"] = bool(
                lifecycle_sem["static_support"] and not lifecycle_sem["certified_support"]
            )
            publication_records.append({"lifecycle": lifecycle, "publication": publication, "semantics": pub_sem})

            qsem = summarize_qualification_case_semantics(publication, lifecycle, case_q, cells, kinds)
            qsem["permanent_certificate_gap_case"] = bool(pub_sem["permanent_certificate_gap_case"])
            qsem["gap_v0618_qualified_same_object_raw_support"] = bool(
                pub_sem["permanent_certificate_gap_case"]
                and qsem["final_unresolved_v0618_qualified_raw_support"]
            )
            semantic_rows.append(qsem)

        publication_summary = summarize_publication_cases(publication_records)
        semantic = summarize_semantic_cases(semantic_rows)
        semantic["permanent_certificate_gap_case_count"] = sum(
            bool(x["permanent_certificate_gap_case"]) for x in semantic_rows
        )
        semantic["gap_v0618_qualified_same_object_raw_support_cases"] = sum(
            bool(x["gap_v0618_qualified_same_object_raw_support"]) for x in semantic_rows
        )
        # Freshly reproduce the semantic pieces of v0705 before adjudication.
        upstream["published_raw_semantic_support_cases"] = int(
            publication_summary["semantic_continuity"]["published_raw_semantic_support_cases"]
        )
        upstream["published_raw_ordinal_hit_cases"] = [
            int(x) for x in publication_summary["semantic_continuity"]["per_ordinal_published_raw_cell_hit_cases"]
        ]
        upstream["permanent_certificate_gap_case_count"] = int(
            publication_summary["semantic_continuity"]["permanent_certificate_gap_case_count"]
        )
        upstream["gap_same_object_provisional_raw_support_cases"] = int(
            publication_summary["semantic_continuity"]["gap_same_object_provisional_raw_support_cases"]
        )
    else:
        semantic = {
            "scoring_blocked": True,
            "case_count": 11,
            "published_raw_support_cases": None,
            "v054_qualified_semantic_support_cases": 0,
            "v0618_qualified_semantic_support_cases": 0,
            "published_raw_ordinal_hit_cases": None,
            "v054_qualified_ordinal_hit_cases": None,
            "v0618_qualified_ordinal_hit_cases": None,
            "final_unresolved_v0618_qualified_raw_support_cases": None,
            "permanent_certificate_gap_case_count": None,
            "gap_v0618_qualified_same_object_raw_support_cases": None,
        }

    decision = frozen_decision(
        upstream=upstream,
        interface=interface,
        qualification=qualification,
        semantic=semantic,
    )

    result = {
        "schema": "two_wave_f3_lifecycle_qualification_transplant@0.7.6",
        "protocol": PROTOCOL,
        "protocol_freeze_commit": PROTOCOL_FREEZE_COMMIT,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_manifest_verified": bool(source_audit["manifest_verified"]),
        "final_reference_sha256": EXPECTED_REFERENCE_SHA256,
        "sampling_commitment_sha256": commitment,
        "construction": construction,
        "reference_positive_candidate_cases": positive_candidate_count,
        "anchored_reference_positive_cases": anchored_count,
        "required_upstream_replication": upstream,
        "interface_audit": interface,
        "qualification_summary": qualification,
        "semantic_transplant": semantic,
        "semantic_scoring_blocked": bool(semantic_scoring_blocked),
        "frozen_decision": decision,
        "primary_category": decision["primary_category"],
        "development_discovery_only": True,
        "qualification_thresholds_changed": False,
        "additional_hard_reason_demoted": False,
        "future_lifecycle_state_used_for_qualification": False,
        "future_bar_used_for_qualification": False,
        "publication_identity_changed": False,
        "direction_component_scored": False,
        "future_outcome_used": False,
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
