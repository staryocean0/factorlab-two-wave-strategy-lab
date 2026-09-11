#!/usr/bin/env python3
"""Formal read-only v0.6.38 attribution of phase-balanced W1 residuals."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.phase_balance_residual_attribution_v0638 import (
    phase_balance_transition,
    rescue_origin,
    semantic_class,
)
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import build_edge_graph
from scripts.run_two_wave_d1_huber_erosion_consensus_v0623 import (
    EXPECTED_BOTHQ,
    EXPECTED_FILTERED,
    EXPECTED_RAW,
    EXPECTED_V0618,
    VIEWS,
    fkey,
    find_one,
    load_gz,
    qmatrix,
)
from scripts.run_two_wave_phase_balanced_wasserstein_range_v0637 import state as state_v0637
from scripts.run_two_wave_two_cycle_wasserstein_range_v0635 import state as state_v0635

EXPECTED_V0635_TOPOLOGY = {"both": 93, "main_only": 26, "other_only": 24, "none": 1319}
EXPECTED_V0637_TOPOLOGY = {"both": 61, "main_only": 23, "other_only": 21, "none": 1357}


def write_card(path: Path, result: dict) -> None:
    lines = [
        "# Two-Wave v0.6.38 phase-balance residual attribution",
        "",
        f"Formal attribution: **`{result['formal_attribution']}`**",
        "",
        "v0.6.35 -> v0.6.37 exact-status transitions:",
        "",
        "| class | count |",
        "|---|---:|",
    ]
    for k, v in result["phase_balance_transition_counts"].items():
        lines.append(f"| {k} | {v} |")
    lines += [
        "",
        f"Remaining v0.6.37 one-sided changes vs v0.6.25: **{result['v0637_one_sided_changes']}**.",
        f"Semantic classes: `{result['v0637_one_sided_semantic_counts']}`.",
        "",
        "Semantic class by rescue origin:",
        "",
        "| semantic class | shared v0635+v0637 | phase-balanced only |",
        "|---|---:|---:|",
    ]
    origins = result["semantic_by_rescue_origin"]
    for semantic in ("introduced_harm", "repaired_old_nonexact", "persistent_nonexact"):
        row = origins.get(semantic, {})
        lines.append(
            f"| {semantic} | {row.get('shared_bar_equal_and_phase_balanced_rescue', 0)} | {row.get('phase_balanced_only_rescue', 0)} |"
        )
    lines += [
        "",
        "This diagnostic changes no recognizer and does not authorize threshold tuning or automatic weighting-consensus promotion.",
        "v0.6.25 remains the strongest pooled-exact direction contribution; v0.6.18 remains the qualification champion; morphology acceptance, trading and production remain closed.",
    ]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    filtered = {}
    records = {}
    maps = {}
    bars = {}
    closes = {}
    states35 = {}
    states37 = {}

    for view in VIEWS:
        filtered[view] = load_gz(find_one(args.input, f"filtered-{view}.json.gz"))
        records[view] = load_gz(find_one(args.input, f"records-{view}.json.gz"))
        maps[view] = {fkey(r): r for r in records[view]}
        bars[view], _ = load_development_bars(
            ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json"
        )
        closes[view] = [float(x["close"]) for x in bars[view]]
        states35[view] = {}
        states37[view] = {}
        for row in records[view]:
            if not bool(row["candidate_qualified"]):
                continue
            key = fkey(row)
            states35[view][key] = state_v0635(row, bars[view], closes[view], view)
            states37[view][key] = state_v0637(row, bars[view], closes[view], view)
            assert states35[view][key]["v0625"] == states37[view][key]["v0625"]

    total = 0
    topology35 = Counter()
    topology37 = Counter()
    transitions = Counter()
    transitions_by_offset = defaultdict(Counter)
    semantic = Counter()
    by_origin = defaultdict(Counter)
    audit = []
    main_view = "5m_offset_0"

    for view in VIEWS[1:]:
        graph = build_edge_graph(
            filtered[main_view],
            filtered[view],
            time_field="five_filtered_occurrence_times",
            nominal_bar_minutes=5.0,
            require_phase=True,
        )
        fp = list(graph.mutual_unique_matches)
        assert len(fp) == EXPECTED_FILTERED[view]
        strict = []
        for i, j in fp:
            a = maps[main_view].get(fkey(filtered[main_view][i]))
            b = maps[view].get(fkey(filtered[view][j]))
            if a is not None and b is not None and strict_anchor_edge(a, b, 5.0) is not None:
                strict.append((a, b))
        assert len(strict) == EXPECTED_RAW[view]
        assert qmatrix(strict) == EXPECTED_V0618[view]
        both = [
            (a, b)
            for a, b in strict
            if a["candidate_qualified"] and b["candidate_qualified"]
        ]
        total += len(both)

        for a, b in both:
            ka, kb = fkey(a), fkey(b)
            a35, b35 = states35[main_view][ka], states35[view][kb]
            a37, b37 = states37[main_view][ka], states37[view][kb]
            p25 = (a35["v0625"], b35["v0625"])
            p35 = (a35["v0635"], b35["v0635"])
            p37 = (a37["v0637"], b37["v0637"])

            lc35, rc35 = p25[0] != p35[0], p25[1] != p35[1]
            topo35 = "both" if lc35 and rc35 else "main_only" if lc35 else "other_only" if rc35 else "none"
            topology35[topo35] += 1

            lc37, rc37 = p25[0] != p37[0], p25[1] != p37[1]
            topo37 = "both" if lc37 and rc37 else "main_only" if lc37 else "other_only" if rc37 else "none"
            topology37[topo37] += 1

            trans = phase_balance_transition(p35, p37)
            transitions[trans] += 1
            transitions_by_offset[view][trans] += 1

            if topo37 not in {"main_only", "other_only"}:
                continue

            sem = semantic_class(p25, p37)
            semantic[sem] += 1
            if lc37:
                old_label, plain_label, balanced_label = a35["v0625"], a35["v0635"], a37["v0637"]
                changed_side = "main"
            else:
                old_label, plain_label, balanced_label = b35["v0625"], b35["v0635"], b37["v0637"]
                changed_side = "other"
            origin = rescue_origin(old_label, plain_label, balanced_label)
            by_origin[sem][origin] += 1
            audit.append(
                {
                    "offset": view,
                    "v0637_topology": topo37,
                    "semantic_class": sem,
                    "rescue_origin": origin,
                    "changed_side": changed_side,
                    "v0625_pair": list(p25),
                    "v0635_pair": list(p35),
                    "v0637_pair": list(p37),
                }
            )

    assert total == EXPECTED_BOTHQ
    assert dict(topology35) == EXPECTED_V0635_TOPOLOGY
    assert dict(topology37) == EXPECTED_V0637_TOPOLOGY
    assert len(audit) == EXPECTED_V0637_TOPOLOGY["main_only"] + EXPECTED_V0637_TOPOLOGY["other_only"]

    result = {
        "schema": "two_wave_phase_balance_residual_attribution_result@0.6.38",
        "formal_attribution": "v0638_phase_balance_residual_attribution_complete",
        "controls": {
            "filtered_pairs": 57029,
            "raw_strict_pairs": 29453,
            "both_v0618_qualified_pairs": total,
            "v0635_pair_change_topology": dict(topology35),
            "v0637_pair_change_topology": dict(topology37),
            "reproduced": True,
        },
        "phase_balance_transition_counts": dict(transitions),
        "phase_balance_transition_counts_by_offset": {
            k: dict(v) for k, v in transitions_by_offset.items()
        },
        "v0637_one_sided_changes": len(audit),
        "v0637_one_sided_semantic_counts": dict(semantic),
        "semantic_by_rescue_origin": {k: dict(v) for k, v in by_origin.items()},
        "recognizer_changed": False,
        "threshold_changed": False,
        "qualification_changed": False,
        "morphology_acceptance": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "production_authority": False,
    }
    (args.output / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    write_card(args.output / "RESULT_CARD.md", result)
    with gzip.open(args.output / "v0637_one_sided_audit.jsonl.gz", "wt", encoding="utf-8") as fh:
        for row in audit:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
