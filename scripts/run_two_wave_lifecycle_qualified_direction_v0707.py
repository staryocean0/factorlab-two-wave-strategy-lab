#!/usr/bin/env python3
"""Formal v0.7.7 lifecycle-qualified D1/v0.6.25 direction transplant."""
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

from factor_lab.visual_structure.two_wave.d1_huber_erosion_consensus_v0623 import DECISIVE
from factor_lab.visual_structure.two_wave.d1_huber_margin_rescue_v0625 import (
    BOUNDARY_EPS,
    MIN_CONSENSUS_MARGIN,
    d1_primary_margin_rescue,
)
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import build_ridge_run
from factor_lab.visual_structure.two_wave.f3_lifecycle_qualification_transplant_v0706 import (
    publication_identity_hash,
    qualification_args,
    qualification_contract_violations,
    summarize_case_semantics as summarize_qualification_case_semantics,
    summarize_qualification_records,
    summarize_semantic_cases,
)
from factor_lab.visual_structure.two_wave.f3_prefix_causal_lifecycle_v0704 import build_lifecycle_for_case
from factor_lab.visual_structure.two_wave.f3_provisional_lifecycle_publication_v0705 import (
    cache_prefix_static_stores,
    replay_publications_from_cache,
)
from factor_lab.visual_structure.two_wave.lifecycle_qualified_direction_v0707 import (
    LABELS,
    frozen_decision,
    stage_a_gates,
    summarize_semantic_direction_cases,
    unanimous_case_label,
)
from factor_lab.visual_structure.two_wave.path_gate_demotion_v0618 import qualify_published_raw_identity_v0618
from factor_lab.visual_structure.two_wave.published_identity_qualification_v066 import qualify_published_raw_identity
from factor_lab.visual_structure.two_wave.reference_label_freeze_v0648 import validate_final_reference_frame
from factor_lab.visual_structure.two_wave.reference_label_packet_v0648 import sampling_commitment, select_blinded_cases
from factor_lab.visual_structure.two_wave.same_scale_v04 import evaluate_pair
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from factor_lab.visual_structure.two_wave.semantic_bridge_counteroffensive_v0700 import (
    five_bars_hit_cells,
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

PROTOCOL = "docs/research/TWO_WAVE_LIFECYCLE_QUALIFIED_DIRECTION_TRANSPLANT_V0707_PROTOCOL.md"
PROTOCOL_FREEZE_COMMIT = "c2fe567fec232e7bbd93614917d85f85b984dfbb"
REFERENCE_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/FINAL_REFERENCE_LABELS.csv"
COMMITMENT_PATH = ROOT / "experiments/two_wave_independent_reference_label_v0648/SAMPLING_COMMITMENT.json"
V0705_RESULT_PATH = ROOT / "experiments/two_wave_f3_provisional_lifecycle_publication_v0705/RESULT.json"
V0706_RESULT_PATH = ROOT / "experiments/two_wave_f3_lifecycle_qualification_transplant_v0706/RESULT.json"
OUTPUT_DIR = ROOT / "experiments/two_wave_lifecycle_qualified_direction_v0707"
EXPECTED_REFERENCE_SHA256 = "321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d"
EXPECTED_COMMITMENT = "f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8"
V0706_AUTHORITY_RUN = 34687608997
V0706_AUTHORITY_RESULT_COMMIT = "cc5942b074fd42ffdc10f78508688e21a451bc06"
LOOKBACK_BARS = 96


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_hash(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def normalized_label(value: str) -> str:
    out = str(value).strip().lower()
    if out not in LABELS:
        raise ValueError(f"direction label outside frozen vocabulary: {value!r}")
    return out


def formal_v0706_authority_ok(result: dict) -> bool:
    try:
        return (
            result["primary_category"] == "v0706_v0618_lifecycle_qualification_transplant_supported"
            and int(result["required_upstream_replication"]["published_lifecycle_object_count"]) == 1543
            and int(result["interface_audit"]["v054_exception_count"]) == 0
            and int(result["interface_audit"]["v0618_exception_count"]) == 0
            and int(result["qualification_summary"]["contract_violation_count"]) == 0
            and int(result["qualification_summary"]["v0618"]["qualified_count"]) == 115
            and int(result["semantic_transplant"]["v0618_qualified_semantic_support_cases"]) == 9
            and bool(result["frozen_decision"]["qualification_transplant_supported"])
        )
    except (KeyError, TypeError, ValueError):
        return False


def publication_semantic_metrics(rows: list[dict]) -> dict:
    out = {}
    for key in ("D1", "v0625"):
        exact = sum(row[key] == row["reference_state"] for row in rows)
        uncertain = sum(row[key] == "uncertain" for row in rows)
        opposite = sum({row[key], row["reference_state"]} == {"uptrend", "downtrend"} for row in rows)
        out[key] = {
            "publication_count": len(rows),
            "exact_count": exact,
            "exact_fraction": exact / len(rows) if rows else None,
            "uncertain_count": uncertain,
            "uncertain_fraction": uncertain / len(rows) if rows else None,
            "opposite_human_trend_conflict_count": opposite,
            "label_counts": dict(sorted(Counter(row[key] for row in rows).items())),
        }
    transitions = Counter(f"{row['D1']}->{row['v0625']}" for row in rows)
    out["D1_to_v0625_transition_counts"] = dict(sorted(transitions.items()))
    return out


def main() -> int:
    if sha256(DATA_PATH) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("frozen source SHA256 mismatch")
    if sha256(REFERENCE_PATH) != EXPECTED_REFERENCE_SHA256:
        raise RuntimeError("frozen final-reference SHA256 mismatch")
    commitment_record = json.loads(COMMITMENT_PATH.read_text())
    if commitment_record.get("sha256") != EXPECTED_COMMITMENT:
        raise RuntimeError("frozen sampling commitment record mismatch")

    formal_v0705 = json.loads(V0705_RESULT_PATH.read_text())
    formal_v0706 = json.loads(V0706_RESULT_PATH.read_text())
    if formal_v0705.get("primary_category") != "v0705_f3_provisional_lifecycle_publication_transplant_supported":
        raise RuntimeError("formal v0705 authority mismatch")
    formal_v0706_ok = formal_v0706_authority_ok(formal_v0706)
    if not formal_v0706_ok:
        raise RuntimeError("authoritative v0706 result mismatch")

    bars, source_audit = load_development_bars(DATA_PATH, MANIFEST_PATH)
    frame = pd.read_parquet(DATA_PATH).copy()
    full_closes = frame["close"].astype(float).tolist()
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

    # Reconstruct the inherited 11-case lifecycle/publication audit universe.
    # Human support cells and parent_state are deliberately not computed here;
    # Stage A direction construction sees only publication-prefix market data.
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
        lifecycle = build_lifecycle_for_case(ridge, chart_start, cutoff)
        prefix_frames = cache_prefix_static_stores(ridge, chart_start, cutoff)
        publication = replay_publications_from_cache(ridge, lifecycle, prefix_frames, bars)
        case_rows.append(
            {
                "case_id": case.case_id,
                "cutoff": cutoff,
                "chart_start": chart_start,
                "human_anchor_offsets": tuple(int(x) for x in human),
                "lifecycle": lifecycle,
                "publication": publication,
            }
        )

    if positive_candidate_count != 16:
        raise RuntimeError(f"reference-positive candidate count drift: {positive_candidate_count} != 16")
    if anchored_count != 11 or len(case_rows) != 11:
        raise RuntimeError(f"anchored reference-positive count drift: {anchored_count} != 11")

    # Fresh label-free replay of the complete v0706 qualification contract.
    v054_exceptions: Counter[str] = Counter()
    v0618_exceptions: Counter[str] = Counter()
    v054_evaluated = 0
    v0618_evaluated = 0
    qualification_identity_mutation_count = 0
    qualification_future_dependency_violations = 0
    qualification_leaks = 0
    qualification_rows = []
    by_case_qualification: list[dict[tuple[str, ...], dict]] = []
    by_case_direction: list[dict[tuple[str, ...], dict]] = []

    # Stage-A direction audit counters over exactly the v0618-qualified subset.
    d1_exceptions: Counter[str] = Counter()
    v0625_exceptions: Counter[str] = Counter()
    d1_evaluated = 0
    v0625_evaluated = 0
    direction_identity_mutation_count = 0
    qualification_result_mutation_count = 0
    future_bar_dependency_violation_count = 0
    future_outcome_or_trade_authority_leak_count = 0
    d1_labels: Counter[str] = Counter()
    v0625_labels: Counter[str] = Counter()
    rescue_labels: Counter[str] = Counter()
    d1_uncertain_count = 0
    rescue_count = 0
    d1_decisive_override_count = 0
    rescue_nonunanimous_consensus_count = 0
    rescue_below_frozen_margin_count = 0
    invalid_classification_change_count = 0

    for case_row in case_rows:
        lifecycle = case_row["lifecycle"]
        publication = case_row["publication"]
        case_q: dict[tuple[str, ...], dict] = {}
        case_direction: dict[tuple[str, ...], dict] = {}
        for key, state in publication["states"].items():
            pub = state["publication"]
            if pub is None:
                continue
            before_identity = publication_identity_hash(pub)
            try:
                phase, raw, confirmation, prefix = qualification_args(pub, bars)
            except Exception as exc:
                name = f"input_{type(exc).__name__}"
                v054_exceptions[name] += 1
                v0618_exceptions[name] += 1
                qualification_identity_mutation_count += int(
                    before_identity != publication_identity_hash(pub)
                )
                continue

            if len(prefix) != confirmation + 1 or max(raw) > confirmation:
                qualification_future_dependency_violations += 1

            v054 = None
            v0618 = None
            try:
                v054 = qualify_published_raw_identity(phase, raw, confirmation, prefix, cfg=cfg)
                v054_evaluated += 1
            except Exception as exc:
                v054_exceptions[type(exc).__name__] += 1
            try:
                v0618 = qualify_published_raw_identity_v0618(phase, raw, confirmation, prefix, cfg=cfg)
                v0618_evaluated += 1
            except Exception as exc:
                v0618_exceptions[type(exc).__name__] += 1

            after_qualification_identity = publication_identity_hash(pub)
            qualification_identity_mutation_count += int(before_identity != after_qualification_identity)
            if v054 is None or v0618 is None:
                continue

            qualification_leaks += int(
                bool(v054.get("future_outcome_used"))
                or bool(v054.get("trade_authority"))
                or bool(v0618.get("future_outcome_used"))
                or bool(v0618.get("trade_authority"))
            )
            contract = qualification_contract_violations(v054, v0618)
            final_certified = bool(lifecycle["objects"][key]["certified"])
            status_at_pub = str(pub["status_at_publication"])
            cert_bar = lifecycle["objects"][key].get("certification_bar")
            qrow = {
                "v054": v054,
                "v0618": v0618,
                "identity_mutated": before_identity != after_qualification_identity,
                "contract_violations": contract,
                "strata": {
                    "already_certified_at_publication": status_at_pub == "certified",
                    "unresolved_at_publication_later_certified": (
                        status_at_pub == "observed_live_unresolved"
                        and final_certified
                        and cert_bar is not None
                        and int(cert_bar) > confirmation
                    ),
                    "unresolved_at_publication_still_unresolved": (
                        status_at_pub == "observed_live_unresolved" and not final_certified
                    ),
                    "final_certified": final_certified,
                    "final_unresolved": not final_certified,
                },
            }
            qualification_rows.append(qrow)
            case_q[key] = qrow

            if not bool(v0618["scale_qualified"]):
                continue

            # Direction runtime is restricted to a materialized copy of the
            # exact causal prefix. No post-publication bar can be addressed.
            prefix_bars = [prefix[i] for i in range(len(prefix))]
            prefix_closes = [float(row["close"]) for row in prefix_bars]
            if (
                len(prefix_bars) != confirmation + 1
                or max(raw) > confirmation
                or any(int(point["occurrence_bar"]) > confirmation for point in pub["points"])
            ):
                future_bar_dependency_violation_count += 1

            q_before = stable_hash({"v054": v054, "v0618": v0618, "contract": contract})
            direction_identity_before = publication_identity_hash(pub)
            try:
                record = evaluate_pair(
                    pub["points"],
                    prefix_bars,
                    cfg,
                    source="F3_v0707_lifecycle_qualified_direction",
                )
                d1 = normalized_label(record["direction_versions"]["D1"])
                amplitude_unit = float(record["amplitude_unit_price"])
                d1_evaluated += 1
                d1_labels[d1] += 1
                d1_uncertain_count += int(d1 == "uncertain")
            except Exception as exc:
                d1_exceptions[type(exc).__name__] += 1
                direction_identity_mutation_count += int(
                    direction_identity_before != publication_identity_hash(pub)
                )
                qualification_result_mutation_count += int(
                    q_before != stable_hash({"v054": v054, "v0618": v0618, "contract": contract})
                )
                continue

            try:
                rescued = d1_primary_margin_rescue(d1, prefix_closes, raw, amplitude_unit)
                v_label = normalized_label(rescued["classification"])
                v0625_evaluated += 1
                v0625_labels[v_label] += 1
            except Exception as exc:
                v0625_exceptions[type(exc).__name__] += 1
                direction_identity_mutation_count += int(
                    direction_identity_before != publication_identity_hash(pub)
                )
                qualification_result_mutation_count += int(
                    q_before != stable_hash({"v054": v054, "v0618": v0618, "contract": contract})
                )
                continue

            leak = (
                bool(v054.get("future_outcome_used"))
                or bool(v054.get("trade_authority"))
                or bool(v0618.get("future_outcome_used"))
                or bool(v0618.get("trade_authority"))
                or bool(record.get("future_outcome_used", False))
                or bool(record.get("trade_authority", False))
                or bool(rescued.get("future_outcome_used", False))
                or bool(rescued.get("trade_authority", False))
            )
            future_outcome_or_trade_authority_leak_count += int(leak)

            direct_override = d1 in DECISIVE and v_label != d1
            d1_decisive_override_count += int(
                bool(rescued.get("D1_decisive_overridden", False)) or direct_override
            )
            if v_label != d1 and not (d1 == "uncertain" and v_label in DECISIVE):
                invalid_classification_change_count += 1

            applied = bool(rescued.get("rescue_applied", False))
            if applied:
                rescue_count += 1
                rescue_labels[v_label] += 1
                support_states = rescued.get("support_states", {})
                unanimous = (
                    bool(rescued.get("v0623_consensus_decisive", False))
                    and str(rescued.get("erosion_consensus_state")) == v_label
                    and bool(support_states)
                    and {str(x) for x in support_states.values()} == {v_label}
                )
                rescue_nonunanimous_consensus_count += int(not unanimous)
                margin = rescued.get("consensus_margin_to_frozen_boundary")
                margin_ok = (
                    margin is not None
                    and float(margin) + BOUNDARY_EPS >= MIN_CONSENSUS_MARGIN
                )
                rescue_below_frozen_margin_count += int(not margin_ok)

            direction_identity_mutation_count += int(
                direction_identity_before != publication_identity_hash(pub)
            )
            q_after = stable_hash({"v054": v054, "v0618": v0618, "contract": contract})
            qualification_result_mutation_count += int(q_before != q_after)
            case_direction[key] = {
                "D1": d1,
                "v0625": v_label,
                "rescue_applied": applied,
            }

        by_case_qualification.append(case_q)
        by_case_direction.append(case_direction)

    qualification = summarize_qualification_records(qualification_rows)
    qualification_interface = {
        "publication_count": len(qualification_rows),
        "v054_evaluated_count": v054_evaluated,
        "v0618_evaluated_count": v0618_evaluated,
        "v054_exception_count": int(sum(v054_exceptions.values())),
        "v054_exception_type_counts": dict(sorted(v054_exceptions.items())),
        "v0618_exception_count": int(sum(v0618_exceptions.values())),
        "v0618_exception_type_counts": dict(sorted(v0618_exceptions.items())),
        "identity_mutation_count": qualification_identity_mutation_count,
        "future_bar_dependency_violation_count": qualification_future_dependency_violations,
        "future_outcome_or_trade_authority_violation_count": qualification_leaks,
    }

    fresh_v0706_label_free_reproduction = (
        len(qualification_rows) == 1543
        and v054_evaluated == 1543
        and v0618_evaluated == 1543
        and not v054_exceptions
        and not v0618_exceptions
        and qualification_identity_mutation_count == 0
        and qualification_future_dependency_violations == 0
        and qualification_leaks == 0
        and int(qualification["contract_violation_count"]) == 0
        and int(qualification["v0618"]["qualified_count"]) == 115
    )
    upstream_v0706_exact_reproduction = bool(formal_v0706_ok and fresh_v0706_label_free_reproduction)

    stage_a = {
        "upstream_v0706_exact_reproduction": upstream_v0706_exact_reproduction,
        "qualified_publication_universe_count": int(qualification["v0618"]["qualified_count"]),
        "D1_evaluated_count": d1_evaluated,
        "D1_exception_count": int(sum(d1_exceptions.values())),
        "D1_exception_type_counts": dict(sorted(d1_exceptions.items())),
        "v0625_evaluated_count": v0625_evaluated,
        "v0625_exception_count": int(sum(v0625_exceptions.values())),
        "v0625_exception_type_counts": dict(sorted(v0625_exceptions.items())),
        "publication_or_lifecycle_identity_mutation_count": (
            qualification_identity_mutation_count + direction_identity_mutation_count
        ),
        "qualification_result_mutation_count": qualification_result_mutation_count,
        "future_bar_dependency_violation_count": (
            qualification_future_dependency_violations + future_bar_dependency_violation_count
        ),
        "future_outcome_or_trade_authority_leak_count": (
            qualification_leaks + future_outcome_or_trade_authority_leak_count
        ),
        "D1_label_counts": dict(sorted(d1_labels.items())),
        "v0625_label_counts": dict(sorted(v0625_labels.items())),
        "D1_uncertain_count": d1_uncertain_count,
        "v0625_rescue_count": rescue_count,
        "rescue_label_counts": dict(sorted(rescue_labels.items())),
        "D1_decisive_override_count": d1_decisive_override_count,
        "rescue_nonunanimous_consensus_count": rescue_nonunanimous_consensus_count,
        "rescue_below_frozen_margin_count": rescue_below_frozen_margin_count,
        "invalid_classification_change_count": invalid_classification_change_count,
        "human_labels_or_support_cells_used_for_direction_runtime": False,
        "future_lifecycle_state_used_for_direction_runtime": False,
    }
    a_gates = stage_a_gates(stage_a)
    hard_stage_a_pass = all(list(a_gates.values())[:10])

    # Stage B is opened only after Stage-A gates 1-10 are clean. Human support
    # cells and parent_state enter only here, after all direction outputs exist.
    stage_b = None
    human_direction_scoring_performed = False
    if hard_stage_a_pass:
        human_direction_scoring_performed = True
        semantic_rows = []
        supported_case_rows = []
        publication_semantic_rows = []
        supported_publication_count = 0
        for case_row, case_q, case_direction in zip(
            case_rows, by_case_qualification, by_case_direction
        ):
            ref = reference.loc[case_row["case_id"]].to_dict()
            human_bars = [
                int(case_row["chart_start"]) + int(x)
                for x in case_row["human_anchor_offsets"]
            ]
            kinds = infer_human_kinds(human_bars, full_closes)
            cells = human_support_cells(
                human_bars,
                int(case_row["chart_start"]),
                int(case_row["cutoff"]),
            )
            lifecycle = case_row["lifecycle"]
            publication = case_row["publication"]
            qsem = summarize_qualification_case_semantics(
                publication, lifecycle, case_q, cells, kinds
            )
            semantic_rows.append(qsem)

            supported = []
            final_live_keys = set(lifecycle["final_live_keys"])
            for key, state in publication["states"].items():
                pub = state["publication"]
                q = case_q.get(key)
                direction = case_direction.get(key)
                if (
                    pub is None
                    or q is None
                    or direction is None
                    or key not in final_live_keys
                    or not bool(q["v0618"]["scale_qualified"])
                ):
                    continue
                hit, _ = five_bars_hit_cells(
                    pub["raw_occurrence_bars"], pub["phase"], cells, kinds
                )
                if not hit:
                    continue
                supported.append(direction)

            if not supported:
                continue
            supported_publication_count += len(supported)
            reference_state = normalized_label(ref["parent_state"])
            d1_publication_labels = [row["D1"] for row in supported]
            v0625_publication_labels = [row["v0625"] for row in supported]
            supported_case_rows.append(
                {
                    "reference_state": reference_state,
                    "D1": unanimous_case_label(d1_publication_labels),
                    "v0625": unanimous_case_label(v0625_publication_labels),
                    "D1_publication_labels": d1_publication_labels,
                    "v0625_publication_labels": v0625_publication_labels,
                }
            )
            for row in supported:
                publication_semantic_rows.append(
                    {
                        "reference_state": reference_state,
                        "D1": row["D1"],
                        "v0625": row["v0625"],
                    }
                )

        fresh_semantic = summarize_semantic_cases(semantic_rows)
        semantic_support_count = int(fresh_semantic["v0618_qualified_semantic_support_cases"])
        case_summary = summarize_semantic_direction_cases(supported_case_rows)
        stage_b = {
            **case_summary,
            "anchored_case_count": 11,
            "v0618_qualified_semantic_support_cases": semantic_support_count,
            "unsupported_case_count": 11 - semantic_support_count,
            "qualified_semantic_support_reproduced": (
                semantic_support_count == 9 and len(supported_case_rows) == 9
            ),
            "semantically_supported_publication_count": supported_publication_count,
            "publication_level_diagnostics": publication_semantic_metrics(
                publication_semantic_rows
            ),
            "human_support_cells_used_only_after_stage_a_gates_1_to_10": True,
            "case_level_rows_written": False,
        }

    decision = frozen_decision(stage_a=stage_a, stage_b=stage_b)

    negative_constraints = {
        "v0647_temporal_replication": {
            "universe": "2024_2025_temporal_replication",
            "D1_pooled_exact_count": 242,
            "pair_count": 253,
            "D1_pooled_exact_agreement": 0.9565217391304348,
            "v0625_pooled_exact_count": 238,
            "v0625_pooled_exact_agreement": 0.9407114624505929,
            "v0625_pooled_decisive_coverage": 0.6857707509881423,
            "v0625_decisive_agreement": 1.0,
            "v0625_opposite_trend_conflicts": 0,
            "original_v0625_all_gates_pass": False,
            "binding_external_validation_weakness": True,
        },
        "v0648_independent_reference_calibration": {
            "candidate_reference_confirmed_presence_count": 16,
            "candidate_case_count": 120,
            "candidate_reference_confirmed_presence_fraction": 0.13333333333333333,
            "v0625_parent_state_exact_count": 5,
            "reference_confirmed_candidate_count": 16,
            "v0625_parent_state_exact_agreement": 0.3125,
            "D1_parent_state_exact_count": 5,
            "D1_parent_state_exact_agreement": 0.3125,
            "v0625_opposite_trend_conflict_rate": 0.0,
            "D1_uncertain_rate": 0.5625,
            "v0625_uncertain_rate": 0.4375,
            "all_calibration_support_gates_pass": False,
            "binding_external_validation_weakness": True,
        },
    }

    result = {
        "schema": "two_wave_lifecycle_qualified_direction_transplant@0.7.7",
        "protocol": PROTOCOL,
        "protocol_freeze_commit": PROTOCOL_FREEZE_COMMIT,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_manifest_verified": bool(source_audit["manifest_verified"]),
        "final_reference_sha256": EXPECTED_REFERENCE_SHA256,
        "sampling_commitment_sha256": commitment,
        "v0705_result_sha256": sha256(V0705_RESULT_PATH),
        "v0706_result_sha256": sha256(V0706_RESULT_PATH),
        "v0706_authority_run": V0706_AUTHORITY_RUN,
        "v0706_authority_result_commit": V0706_AUTHORITY_RESULT_COMMIT,
        "construction": construction,
        "reference_positive_candidate_cases": positive_candidate_count,
        "anchored_reference_positive_cases": anchored_count,
        "v0706_upstream_replication": {
            "formal_authority_verified": formal_v0706_ok,
            "fresh_label_free_reproduction_pass": fresh_v0706_label_free_reproduction,
            "formal_publication_count": int(
                formal_v0706["required_upstream_replication"]["published_lifecycle_object_count"]
            ),
            "fresh_publication_count": len(qualification_rows),
            "formal_v0618_qualified_count": int(
                formal_v0706["qualification_summary"]["v0618"]["qualified_count"]
            ),
            "fresh_v0618_qualified_count": int(qualification["v0618"]["qualified_count"]),
            "formal_qualification_interface_exception_count": int(
                formal_v0706["interface_audit"]["v0618_exception_count"]
            ),
            "fresh_qualification_interface_exception_count": int(sum(v0618_exceptions.values())),
            "formal_contract_violation_count": int(
                formal_v0706["qualification_summary"]["contract_violation_count"]
            ),
            "fresh_contract_violation_count": int(qualification["contract_violation_count"]),
            "formal_v0618_qualified_semantic_support_cases": int(
                formal_v0706["semantic_transplant"]["v0618_qualified_semantic_support_cases"]
            ),
            "stage_b_fresh_v0618_qualified_semantic_support_cases": (
                None if stage_b is None else int(stage_b["v0618_qualified_semantic_support_cases"])
            ),
        },
        "qualification_interface_audit": qualification_interface,
        "qualification_summary": qualification,
        "stage_a_direction_interface_and_contract_audit": stage_a,
        "stage_b_semantic_direction_comparison": stage_b,
        "human_direction_scoring_performed": human_direction_scoring_performed,
        "negative_constraint_snapshot": negative_constraints,
        "frozen_decision": decision,
        "primary_category": decision["primary_category"],
        "development_direction_contribution_only": True,
        "threshold_fitting_performed": False,
        "qualification_changed": False,
        "publication_or_lifecycle_identity_changed": False,
        "future_lifecycle_state_used_for_direction": False,
        "future_bar_used_for_direction": False,
        "future_outcome_used": False,
        "cross_offset_runtime_input_used": False,
        "active_semantic_parent_authority": None,
        "morphology_acceptance": False,
        "trade_authority": False,
        "production_authority": False,
        "direction_winner": None,
        "case_level_table_written": False,
        "hidden_annotation_notes_written": False,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "RESULT.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
