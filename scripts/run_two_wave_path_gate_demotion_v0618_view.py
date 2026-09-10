#!/usr/bin/env python3
"""Build one native-5m v0.6.18 qualification shard from frozen upstream."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import build_ridge_run
from factor_lab.visual_structure.two_wave.ordinal0_predecessor_support_v064 import (
    project_birth_with_predecessor,
)
from factor_lab.visual_structure.two_wave.path_gate_demotion_v0618 import (
    requalify_v066_control,
)
from factor_lab.visual_structure.two_wave.published_identity_qualification_v066 import (
    qualify_published_raw_identity,
)
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from factor_lab.visual_structure.two_wave.scale_invariant_predecessor_publication_v065 import (
    publish_first_valid_candidate,
)

VIEWS = tuple(f"5m_offset_{i}" for i in range(5))
EXPECTED_PUBLICATIONS = {
    "5m_offset_0": 38176,
    "5m_offset_1": 36737,
    "5m_offset_2": 36619,
    "5m_offset_3": 36480,
    "5m_offset_4": 36264,
}
SAFETY_REASONS = {
    "long_cycle",
    "long_pair",
    "too_many_observed_days",
    "wall_span_too_long",
}
CASE02_RAW = (4565, 4617, 4655, 4656, 4658)


def dump_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def dump_jsonl_gz(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def build_publications(view: str, bars: list[dict]) -> tuple[list[dict], dict]:
    cfg = MaturityConfig(timeframe=view)
    ridge = build_ridge_run(bars, cfg=cfg)
    if ridge.lineage_anomalies:
        raise AssertionError(f"v0.5.2 lineage anomalies on {view}: {len(ridge.lineage_anomalies)}")

    groups: dict[tuple[str, tuple[int, ...]], list[dict]] = defaultdict(list)
    for birth in ridge.tuple_births:
        phase = str(birth.nodes[0].node.kind)
        filtered = tuple(int(x) for x in birth.occurrence_indices)
        candidate = project_birth_with_predecessor(
            birth,
            ridge.ridge_nodes_by_level[int(birth.level)],
            bars,
        )
        candidate = dict(candidate)
        candidate.update(
            {
                "event_id": str(birth.event_id),
                "birth_level": int(birth.level),
                "birth_confirmation_bar": int(birth.confirmation_index),
            }
        )
        groups[(phase, filtered)].append(candidate)

    rows = []
    no_valid = 0
    suppressed_rewrites = 0
    safety_candidates = 0
    case02_seen = 0
    for (phase, filtered), members in sorted(groups.items(), key=lambda x: (x[0][1], x[0][0])):
        publication = publish_first_valid_candidate(phase, filtered, members)
        suppressed_rewrites += int(publication["suppressed_would_be_rewrite_count"])
        event = publication["publication_event"]
        if event is None:
            no_valid += 1
            continue
        raw = tuple(int(x) for x in event["published_raw_occurrence_bars"])
        confirmation = int(event["publishing_birth_confirmation_bar"])
        control = qualify_published_raw_identity(phase, raw, confirmation, bars, cfg=cfg)
        candidate = requalify_v066_control(control)

        old_hard = [str(x) for x in control["v054_hard_rejection_reasons"]]
        new_hard = [str(x) for x in candidate["v0618_hard_rejection_reasons"]]
        expected_new = [x for x in old_hard if x not in {"inefficient_leg", "jump_dominated_leg"}]
        if new_hard != expected_new:
            raise AssertionError("v0.6.18 changed a non-registered hard reason")
        if bool(control["scale_qualified"]) and not bool(candidate["scale_qualified"]):
            raise AssertionError("demotion candidate cannot reject a control-qualified identity")
        if any(x in SAFETY_REASONS for x in old_hard):
            safety_candidates += 1
            if bool(candidate["scale_qualified"]):
                raise AssertionError("v0.6.18 bypassed an unchanged long-span safety gate")
        if raw == CASE02_RAW:
            case02_seen += 1
            if bool(candidate["scale_qualified"]):
                raise AssertionError("legacy case_02 90/3 pathology became qualified")

        times = [str(bars[i]["timestamp"]) for i in raw]
        rows.append(
            {
                "phase": phase,
                "five_filtered_occurrence_bars": list(filtered),
                "published_raw_occurrence_bars": list(raw),
                "five_occurrence_times": times,
                "publishing_confirmation_bar": confirmation,
                "control_qualified": bool(control["scale_qualified"]),
                "candidate_qualified": bool(candidate["scale_qualified"]),
                "control_hard_reasons": old_hard,
                "candidate_hard_reasons": new_hard,
                "demoted_path_diagnostics": candidate["demoted_path_diagnostics"],
                "future_outcome_used": False,
                "trade_authority": False,
            }
        )

    if len(rows) != EXPECTED_PUBLICATIONS[view]:
        raise AssertionError(
            f"v0.6.5 publication count drift for {view}: {len(rows)} != {EXPECTED_PUBLICATIONS[view]}"
        )
    summary = {
        "view": view,
        "bars": len(bars),
        "tuple_births": len(ridge.tuple_births),
        "canonical_filtered_groups": len(groups),
        "published_identities": len(rows),
        "no_valid_publication": no_valid,
        "suppressed_would_be_rewrites": suppressed_rewrites,
        "control_qualified": sum(r["control_qualified"] for r in rows),
        "candidate_qualified": sum(r["candidate_qualified"] for r in rows),
        "newly_qualified": sum(r["candidate_qualified"] and not r["control_qualified"] for r in rows),
        "control_hard_reason_counts": dict(Counter(x for r in rows for x in r["control_hard_reasons"])),
        "candidate_hard_reason_counts": dict(Counter(x for r in rows for x in r["candidate_hard_reasons"])),
        "long_span_safety_candidates_checked": safety_candidates,
        "legacy_case02_exact_identity_seen": case02_seen,
        "future_outcome_used": False,
        "trade_authority": False,
    }
    return rows, summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--view", required=True, choices=VIEWS)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    bars, audit = load_development_bars(
        ROOT / f"data/development/{args.view}.parquet",
        ROOT / "data/manifest.json",
    )
    rows, summary = build_publications(args.view, bars)
    summary["data_audit"] = audit
    dump_jsonl_gz(args.output / f"records-{args.view}.json.gz", rows)
    dump_json(args.output / f"summary-{args.view}.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
