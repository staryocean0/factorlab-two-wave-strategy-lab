#!/usr/bin/env python3
"""Formal read-only v0.6.36 attribution of v0.6.35 one-sided W1 rescues."""
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
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import build_edge_graph
from factor_lab.visual_structure.two_wave.w1_residual_attribution_v0636 import (
    margin_authorized,
    semantic_class,
    summarize_slacks,
)
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
from scripts.run_two_wave_two_cycle_wasserstein_range_v0635 import state

EXPECTED_V0635_TOPOLOGY = {"both": 93, "main_only": 26, "other_only": 24, "none": 1319}


def write_card(path: Path, result: dict) -> None:
    lines = [
        "# Two-Wave v0.6.36 W1 residual attribution",
        "",
        f"Formal attribution: **`{result['formal_attribution']}`**",
        "",
        f"One-sided changes: **{result['one_sided_changes']}**.",
        f"Semantic classes: `{result['semantic_counts']}`.",
        "",
        "Changed-side W1 slack (`0.15 - max_support_W1`):",
        "",
        "| group | n | median | q25 | q75 | fraction <=0.03 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in ("introduced_harm", "repaired_old_nonexact", "persistent_nonexact"):
        s = result["slack_stats"].get(name, {})
        def fmt(v):
            return "NA" if v is None else f"{float(v):.6f}"
        lines.append(
            f"| {name} | {s.get('count',0)} | {fmt(s.get('median'))} | {fmt(s.get('q25'))} | {fmt(s.get('q75'))} | {fmt(s.get('fraction_le_0_03'))} |"
        )
    lines += ["", f"W1-margin challenger authorized: **{result['w1_margin_authorized']}**", "", "Authorization gates:"]
    lines += [f"- {k}: **{v}**" for k, v in result["authorization_gates"].items()]
    lines += [
        "",
        "This diagnostic changes no recognizer. v0.6.25 remains the strongest pooled-exact direction contribution and v0.6.18 remains the qualification champion unless a later preregistered challenger passes all gates.",
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
    states = {}
    for view in VIEWS:
        filtered[view] = load_gz(find_one(args.input, f"filtered-{view}.json.gz"))
        records[view] = load_gz(find_one(args.input, f"records-{view}.json.gz"))
        maps[view] = {fkey(r): r for r in records[view]}
        bars[view], _ = load_development_bars(
            ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json"
        )
        closes[view] = [float(x["close"]) for x in bars[view]]
        states[view] = {}
        for row in records[view]:
            if bool(row["candidate_qualified"]):
                states[view][fkey(row)] = state(row, bars[view], closes[view], view)

    topology = Counter()
    semantic = Counter()
    slacks = defaultdict(list)
    audit = []
    total = 0
    main_view = "5m_offset_0"

    for view in VIEWS[1:]:
        graph = build_edge_graph(
            filtered[main_view], filtered[view],
            time_field="five_filtered_occurrence_times", nominal_bar_minutes=5.0, require_phase=True,
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
        both = [(a, b) for a, b in strict if a["candidate_qualified"] and b["candidate_qualified"]]
        total += len(both)

        for a, b in both:
            sa = states[main_view][fkey(a)]
            sb = states[view][fkey(b)]
            old_pair = (sa["v0625"], sb["v0625"])
            new_pair = (sa["v0635"], sb["v0635"])
            lc = old_pair[0] != new_pair[0]
            rc = old_pair[1] != new_pair[1]
            topo = "both" if lc and rc else "main_only" if lc else "other_only" if rc else "none"
            topology[topo] += 1
            if topo not in {"main_only", "other_only"}:
                continue
            cls = semantic_class(old_pair, new_pair)
            semantic[cls] += 1
            changed_state = sa if lc else sb
            slack = 0.15 - float(changed_state["max_w1"])
            assert slack >= -1e-12
            slacks[cls].append(slack)
            audit.append({
                "offset": view,
                "topology": topo,
                "semantic_class": cls,
                "old_pair": list(old_pair),
                "new_pair": list(new_pair),
                "changed_side": "main" if lc else "other",
                "changed_side_max_normalized_w1": float(changed_state["max_w1"]),
                "changed_side_w1_slack": slack,
            })

    assert total == EXPECTED_BOTHQ
    assert dict(topology) == EXPECTED_V0635_TOPOLOGY
    assert len(audit) == 50

    stats = {
        name: summarize_slacks(slacks.get(name, []))
        for name in ("introduced_harm", "repaired_old_nonexact", "persistent_nonexact")
    }
    authorized, gates = margin_authorized(stats)
    result = {
        "schema": "two_wave_w1_residual_attribution_result@0.6.36",
        "formal_attribution": "v0636_w1_margin_route_authorized" if authorized else "v0636_w1_margin_route_not_authorized",
        "controls": {
            "filtered_pairs": 57029,
            "raw_strict_pairs": 29453,
            "both_v0618_qualified_pairs": total,
            "v0635_pair_change_topology": dict(topology),
            "reproduced": True,
        },
        "one_sided_changes": len(audit),
        "semantic_counts": dict(semantic),
        "slack_stats": stats,
        "w1_margin_authorized": authorized,
        "authorization_gates": gates,
        "recognizer_changed": False,
        "qualification_changed": False,
        "morphology_acceptance": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "production_authority": False,
    }
    (args.output / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_card(args.output / "RESULT_CARD.md", result)
    with gzip.open(args.output / "one_sided_audit.jsonl.gz", "wt", encoding="utf-8") as fh:
        for row in audit:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
