#!/usr/bin/env python3
"""Formal read-only v0.6.39 order-sensitive residual-shape attribution."""
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
from factor_lab.visual_structure.two_wave.order_sensitive_residual_shape_v0639 import (
    GRID_POINTS_PER_LEG,
    harm_greater_probability,
    numeric_summary,
    progress_shape_descriptors,
)
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

EXPECTED_V0637_TOPOLOGY = {"both": 61, "main_only": 23, "other_only": 21, "none": 1357}
EXPECTED_SEMANTIC = {"introduced_harm": 38, "repaired_old_nonexact": 6}
EXPECTED_ORIGIN = {
    "shared_bar_equal_and_phase_balanced_rescue": 32,
    "phase_balanced_only_rescue": 12,
}
DESCRIPTORS = (
    "first_leg_progress_l1",
    "second_leg_progress_l1",
    "first_leg_progress_linf",
    "second_leg_progress_linf",
    "mean_leg_progress_l1",
    "max_leg_progress_l1",
    "mean_leg_progress_linf",
    "max_leg_progress_linf",
)


def summarize_group(rows: list[dict]) -> dict:
    return {key: numeric_summary([float(row[key]) for row in rows]) for key in DESCRIPTORS}


def write_card(path: Path, result: dict) -> None:
    lines = [
        "# Two-Wave v0.6.39 order-sensitive residual-shape attribution",
        "",
        f"Formal attribution: **`{result['formal_attribution']}`**",
        "",
        f"Residual universe: **{result['residual_rows']}** one-sided v0.6.37 changes; semantics `{result['semantic_counts']}`.",
        "",
        "The representation removes each leg's absolute level and endpoint displacement, then compares corresponding 65-point within-leg progress curves.",
        "",
        "| descriptor | harm median | repair median | P(harm > repair) |",
        "|---|---:|---:|---:|",
    ]
    harm_stats = result["descriptor_stats_by_semantic"]["introduced_harm"]
    repair_stats = result["descriptor_stats_by_semantic"]["repaired_old_nonexact"]
    for key in DESCRIPTORS:
        lines.append(
            f"| {key} | {harm_stats[key]['median']:.6f} | {repair_stats[key]['median']:.6f} | {result['harm_greater_probability'][key]:.6f} |"
        )
    lines += [
        "",
        f"Rescue-origin counts: `{result['rescue_origin_counts']}`.",
        "",
        "No threshold or gate is authorized from this diagnostic. The repaired group has only six observations by frozen design.",
        "v0.6.25 remains the strongest pooled-exact direction contribution; v0.6.18 remains qualification champion; morphology acceptance, trading and production remain closed.",
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

    main_view = "5m_offset_0"
    total = 0
    topology37 = Counter()
    semantic_counts = Counter()
    origin_counts = Counter()
    rows = []

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
        both = [(a, b) for a, b in strict if a["candidate_qualified"] and b["candidate_qualified"]]
        total += len(both)

        for a, b in both:
            ka, kb = fkey(a), fkey(b)
            a35, b35 = states35[main_view][ka], states35[view][kb]
            a37, b37 = states37[main_view][ka], states37[view][kb]
            p25 = (a37["v0625"], b37["v0625"])
            p37 = (a37["v0637"], b37["v0637"])
            lc, rc = p25[0] != p37[0], p25[1] != p37[1]
            topo = "both" if lc and rc else "main_only" if lc else "other_only" if rc else "none"
            topology37[topo] += 1
            if topo not in {"main_only", "other_only"}:
                continue

            sem = semantic_class(p25, p37)
            semantic_counts[sem] += 1
            if lc:
                changed_view = main_view
                changed_record = a
                old_label = a37["v0625"]
                plain_label = a35["v0635"]
                balanced_label = a37["v0637"]
                side = "main"
            else:
                changed_view = view
                changed_record = b
                old_label = b37["v0625"]
                plain_label = b35["v0635"]
                balanced_label = b37["v0637"]
                side = "other"
            origin = rescue_origin(old_label, plain_label, balanced_label)
            origin_counts[origin] += 1
            desc = progress_shape_descriptors(
                closes[changed_view], changed_record["published_raw_occurrence_bars"]
            )
            rows.append(
                {
                    "offset_pair": view,
                    "changed_view": changed_view,
                    "changed_side": side,
                    "semantic_class": sem,
                    "rescue_origin": origin,
                    "v0625_pair": list(p25),
                    "v0637_pair": list(p37),
                    **{key: float(desc[key]) for key in DESCRIPTORS},
                }
            )

    assert total == EXPECTED_BOTHQ
    assert dict(topology37) == EXPECTED_V0637_TOPOLOGY
    assert dict(semantic_counts) == EXPECTED_SEMANTIC
    assert dict(origin_counts) == EXPECTED_ORIGIN
    assert len(rows) == 44

    by_semantic = defaultdict(list)
    by_origin = defaultdict(list)
    for row in rows:
        by_semantic[row["semantic_class"]].append(row)
        by_origin[row["rescue_origin"]].append(row)

    descriptor_stats_by_semantic = {
        key: summarize_group(group) for key, group in by_semantic.items()
    }
    descriptor_stats_by_origin = {
        key: summarize_group(group) for key, group in by_origin.items()
    }
    rank = {
        key: harm_greater_probability(
            [row[key] for row in by_semantic["introduced_harm"]],
            [row[key] for row in by_semantic["repaired_old_nonexact"]],
        )
        for key in DESCRIPTORS
    }

    result = {
        "schema": "two_wave_order_sensitive_residual_shape_result@0.6.39",
        "formal_attribution": "v0639_order_sensitive_residual_shape_attribution_complete_no_gate_authorized",
        "controls": {
            "filtered_pairs": 57029,
            "raw_strict_pairs": 29453,
            "both_v0618_qualified_pairs": total,
            "v0637_pair_change_topology": dict(topology37),
            "grid_points_per_leg": GRID_POINTS_PER_LEG,
            "reproduced": True,
        },
        "residual_rows": len(rows),
        "semantic_counts": dict(semantic_counts),
        "rescue_origin_counts": dict(origin_counts),
        "descriptor_stats_by_semantic": descriptor_stats_by_semantic,
        "descriptor_stats_by_rescue_origin": descriptor_stats_by_origin,
        "harm_greater_probability": rank,
        "gate_authorized": False,
        "reason_gate_not_authorized": "read_only_threshold_free_diagnostic_and_only_6_repaired_rows",
        "recognizer_changed": False,
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
    with gzip.open(args.output / "residual_shape_rows.jsonl.gz", "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
