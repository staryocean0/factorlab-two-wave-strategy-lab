#!/usr/bin/env python3
"""Formal read-only v0.6.41 cycle-drift sign-topology attribution."""
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

from factor_lab.visual_structure.two_wave.cycle_drift_sign_topology_v0641 import (
    categorical_summary,
    cycle_drift_topology,
    true_rate,
)
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.phase_balance_residual_attribution_v0638 import (
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

EXPECTED_TOPOLOGY = {"both": 61, "main_only": 23, "other_only": 21, "none": 1357}
EXPECTED_SEMANTIC = {"introduced_harm": 38, "repaired_old_nonexact": 6}
EXPECTED_ORIGIN = {
    "shared_bar_equal_and_phase_balanced_rescue": 32,
    "phase_balanced_only_rescue": 12,
}


def side_topology(record: dict) -> dict:
    return cycle_drift_topology(record["phase_steps_in_amplitude_units"])


def bool_fraction(rows: list[dict], field: str) -> float:
    return true_rate([bool(r[field]) for r in rows])


def side_summary(rows: list[dict], prefix: str) -> dict:
    relation = [r[f"{prefix}_cycle_drift_relation"] for r in rows]
    all_three = [r[f"{prefix}_all_three_same_direction"] for r in rows]
    return {
        "cycle_drift_relation": categorical_summary(relation),
        "all_three_same_direction_rate": true_rate(all_three),
    }


def one_group_summary(rows: list[dict]) -> dict:
    return {
        "count": len(rows),
        "rescue_side": side_summary(rows, "rescue"),
        "nonrescue_side": side_summary(rows, "nonrescue"),
        "cycle_relation_flip_rate": bool_fraction(rows, "cycle_relation_flipped"),
        "all_three_flip_rate": bool_fraction(rows, "all_three_flipped"),
        "rescue_same_nonrescue_not_rate": bool_fraction(rows, "rescue_same_nonrescue_not"),
        "rescue_all_three_nonrescue_not_rate": bool_fraction(rows, "rescue_all_three_nonrescue_not"),
    }


def write_card(path: Path, result: dict) -> None:
    p = result["primary_comparisons"]
    stable = result["stable_both_summary"]
    harm = result["one_sided_summary_by_semantic"]["introduced_harm"]
    repair = result["one_sided_summary_by_semantic"]["repaired_old_nonexact"]
    lines = [
        "# Two-Wave v0.6.41 cycle-drift sign-topology attribution",
        "",
        f"Formal attribution: **`{result['formal_attribution']}`**",
        "",
        "No classifier or magnitude threshold was changed. All quantities use only strict sign topology around structural zero.",
        "",
        "| quantity | stable both-rescue | harm one-sided | repair one-sided |",
        "|---|---:|---:|---:|",
        f"| same-direction cycle drift | {stable['side_same_direction_rate']:.4f} | {harm['rescue_side']['cycle_drift_relation']['rates'].get('same_direction', 0.0):.4f} | {repair['rescue_side']['cycle_drift_relation']['rates'].get('same_direction', 0.0):.4f} |",
        f"| all three migrations same direction | {stable['side_all_three_same_direction_rate']:.4f} | {harm['rescue_side']['all_three_same_direction_rate']:.4f} | {repair['rescue_side']['all_three_same_direction_rate']:.4f} |",
        f"| harmless-view cycle-relation flip | {stable['cycle_relation_flip_rate']:.4f} | {harm['cycle_relation_flip_rate']:.4f} | {repair['cycle_relation_flip_rate']:.4f} |",
        f"| harmless-view all-three flip | {stable['all_three_flip_rate']:.4f} | {harm['all_three_flip_rate']:.4f} | {repair['all_three_flip_rate']:.4f} |",
        "",
        f"Primary same-direction rate delta (harm - stable): **{p['harm_rescue_same_direction_minus_stable']:+.6f}**",
        f"Primary all-three rate delta (harm - stable): **{p['harm_rescue_all_three_minus_stable']:+.6f}**",
        f"Primary cycle-relation flip delta (harm - stable): **{p['harm_cycle_relation_flip_minus_stable']:+.6f}**",
        f"Primary all-three flip delta (harm - stable): **{p['harm_all_three_flip_minus_stable']:+.6f}**",
        "",
        "v0.6.41 is diagnostic only; `gate_authorized=false` by protocol.",
    ]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    filtered, records, maps, bars, closes, states35, states37 = {}, {}, {}, {}, {}, {}, {}
    for view in VIEWS:
        filtered[view] = load_gz(find_one(args.input, f"filtered-{view}.json.gz"))
        records[view] = load_gz(find_one(args.input, f"records-{view}.json.gz"))
        maps[view] = {fkey(r): r for r in records[view]}
        bars[view], _ = load_development_bars(ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json")
        closes[view] = [float(x["close"]) for x in bars[view]]
        states35[view], states37[view] = {}, {}
        for row in records[view]:
            if not bool(row["candidate_qualified"]):
                continue
            key = fkey(row)
            states35[view][key] = state_v0635(row, bars[view], closes[view], view)
            states37[view][key] = state_v0637(row, bars[view], closes[view], view)
            assert states35[view][key]["v0625"] == states37[view][key]["v0625"]

    main_view = "5m_offset_0"
    total = 0
    topology_counts = Counter()
    semantic_counts = Counter()
    origin_counts = Counter()
    stable_rows: list[dict] = []
    one_rows: list[dict] = []

    for view in VIEWS[1:]:
        graph = build_edge_graph(
            filtered[main_view], filtered[view], time_field="five_filtered_occurrence_times",
            nominal_bar_minutes=5.0, require_phase=True,
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
        bothq = [(a, b) for a, b in strict if a["candidate_qualified"] and b["candidate_qualified"]]
        total += len(bothq)

        for a, b in bothq:
            ka, kb = fkey(a), fkey(b)
            a35, b35 = states35[main_view][ka], states35[view][kb]
            a37, b37 = states37[main_view][ka], states37[view][kb]
            p25 = (a37["v0625"], b37["v0625"])
            p37 = (a37["v0637"], b37["v0637"])
            lc, rc = p25[0] != p37[0], p25[1] != p37[1]
            topo = "both" if lc and rc else "main_only" if lc else "other_only" if rc else "none"
            topology_counts[topo] += 1

            if topo == "both":
                mt, ot = side_topology(a), side_topology(b)
                stable_rows.append({
                    "offset_pair": view,
                    "main_cycle_drift_relation": mt["cycle_drift_relation"],
                    "other_cycle_drift_relation": ot["cycle_drift_relation"],
                    "main_all_three_same_direction": mt["all_three_same_direction"],
                    "other_all_three_same_direction": ot["all_three_same_direction"],
                    "cycle_relation_flipped": mt["cycle_drift_relation"] != ot["cycle_drift_relation"],
                    "all_three_flipped": mt["all_three_same_direction"] != ot["all_three_same_direction"],
                })
                continue
            if topo not in {"main_only", "other_only"}:
                continue

            sem = semantic_class(p25, p37)
            semantic_counts[sem] += 1
            if lc:
                rescue_record, nonrescue_record = a, b
                old_label, plain_label, balanced_label = a37["v0625"], a35["v0635"], a37["v0637"]
                rescue_side = "main"
            else:
                rescue_record, nonrescue_record = b, a
                old_label, plain_label, balanced_label = b37["v0625"], b35["v0635"], b37["v0637"]
                rescue_side = "other"
            origin = rescue_origin(old_label, plain_label, balanced_label)
            origin_counts[origin] += 1
            rt, nt = side_topology(rescue_record), side_topology(nonrescue_record)
            one_rows.append({
                "offset_pair": view,
                "topology": topo,
                "semantic_class": sem,
                "rescue_origin": origin,
                "rescue_side": rescue_side,
                "rescue_cycle_drift_relation": rt["cycle_drift_relation"],
                "nonrescue_cycle_drift_relation": nt["cycle_drift_relation"],
                "rescue_all_three_same_direction": rt["all_three_same_direction"],
                "nonrescue_all_three_same_direction": nt["all_three_same_direction"],
                "cycle_relation_flipped": rt["cycle_drift_relation"] != nt["cycle_drift_relation"],
                "all_three_flipped": rt["all_three_same_direction"] != nt["all_three_same_direction"],
                "rescue_same_nonrescue_not": rt["cycle_drift_relation"] == "same_direction" and nt["cycle_drift_relation"] != "same_direction",
                "rescue_all_three_nonrescue_not": bool(rt["all_three_same_direction"] and not nt["all_three_same_direction"]),
            })

    assert total == EXPECTED_BOTHQ
    assert dict(topology_counts) == EXPECTED_TOPOLOGY
    assert len(stable_rows) == 61 and len(one_rows) == 44
    assert dict(semantic_counts) == EXPECTED_SEMANTIC
    assert dict(origin_counts) == EXPECTED_ORIGIN

    stable_sides = []
    for r in stable_rows:
        stable_sides.extend([
            {"cycle_drift_relation": r["main_cycle_drift_relation"], "all_three_same_direction": r["main_all_three_same_direction"]},
            {"cycle_drift_relation": r["other_cycle_drift_relation"], "all_three_same_direction": r["other_all_three_same_direction"]},
        ])
    stable_same = true_rate([r["cycle_drift_relation"] == "same_direction" for r in stable_sides])
    stable_all3 = true_rate([r["all_three_same_direction"] for r in stable_sides])
    stable_relation_flip = bool_fraction(stable_rows, "cycle_relation_flipped")
    stable_all3_flip = bool_fraction(stable_rows, "all_three_flipped")
    stable_summary = {
        "side_count": len(stable_sides),
        "side_cycle_drift_relation": categorical_summary([r["cycle_drift_relation"] for r in stable_sides]),
        "side_same_direction_rate": stable_same,
        "side_all_three_same_direction_rate": stable_all3,
        "cycle_relation_flip_rate": stable_relation_flip,
        "all_three_flip_rate": stable_all3_flip,
    }

    by_sem, by_origin = defaultdict(list), defaultdict(list)
    for r in one_rows:
        by_sem[r["semantic_class"]].append(r)
        by_origin[r["rescue_origin"]].append(r)
    sem_summary = {k: one_group_summary(v) for k, v in by_sem.items()}
    origin_summary = {k: one_group_summary(v) for k, v in by_origin.items()}
    harm = sem_summary["introduced_harm"]
    harm_same = harm["rescue_side"]["cycle_drift_relation"]["rates"].get("same_direction", 0.0)
    harm_all3 = harm["rescue_side"]["all_three_same_direction_rate"]
    primary = {
        "harm_rescue_same_direction_minus_stable": float(harm_same - stable_same),
        "harm_rescue_all_three_minus_stable": float(harm_all3 - stable_all3),
        "harm_cycle_relation_flip_minus_stable": float(harm["cycle_relation_flip_rate"] - stable_relation_flip),
        "harm_all_three_flip_minus_stable": float(harm["all_three_flip_rate"] - stable_all3_flip),
    }

    result = {
        "schema": "two_wave_cycle_drift_sign_topology_result@0.6.41",
        "formal_attribution": "v0641_cycle_drift_sign_topology_attribution_complete_no_gate_authorized",
        "controls": {
            "filtered_pairs": 57029,
            "raw_strict_pairs": 29453,
            "both_v0618_qualified_pairs": total,
            "v0637_pair_change_topology": dict(topology_counts),
            "reproduced": True,
        },
        "diagnostic_pairs": 105,
        "stable_both_rows": len(stable_rows),
        "one_sided_rows": len(one_rows),
        "semantic_counts": dict(semantic_counts),
        "rescue_origin_counts": dict(origin_counts),
        "stable_both_summary": stable_summary,
        "one_sided_summary_by_semantic": sem_summary,
        "one_sided_summary_by_rescue_origin": origin_summary,
        "primary_comparisons": primary,
        "gate_authorized": False,
        "reason_gate_not_authorized": "read_only_sign_topology_attribution; any structural veto requires a separate preregistered challenger",
        "recognizer_changed": False,
        "qualification_changed": False,
        "morphology_acceptance": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "production_authority": False,
    }
    (args.output / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_card(args.output / "RESULT_CARD.md", result)
    with gzip.open(args.output / "stable_both_rows.jsonl.gz", "wt", encoding="utf-8") as fh:
        for row in stable_rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    with gzip.open(args.output / "one_sided_rows.jsonl.gz", "wt", encoding="utf-8") as fh:
        for row in one_rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
