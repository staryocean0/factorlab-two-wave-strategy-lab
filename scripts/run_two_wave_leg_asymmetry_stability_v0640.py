#!/usr/bin/env python3
"""Formal read-only v0.6.40 leg-asymmetry and harmless-slicing attribution."""
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
from factor_lab.visual_structure.two_wave.leg_asymmetry_stability_v0640 import (
    greater_probability,
    leg_asymmetry,
    sign_bucket,
    sign_fractions,
)
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.order_sensitive_residual_shape_v0639 import (
    GRID_POINTS_PER_LEG,
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
EXPECTED_DIAGNOSTIC_PAIRS = 105

BOTH_FIELDS = (
    "pair_mean_A_L1",
    "pair_abs_delta_A_L1",
    "pair_mean_A_Linf",
    "pair_abs_delta_A_Linf",
)
ONE_FIELDS = (
    "rescue_A_L1",
    "nonrescue_A_L1",
    "rescue_minus_nonrescue_A_L1",
    "pair_abs_delta_A_L1",
    "rescue_A_Linf",
    "nonrescue_A_Linf",
    "rescue_minus_nonrescue_A_Linf",
    "pair_abs_delta_A_Linf",
)


def shape_asymmetry(closes: list[float], record: dict) -> dict:
    desc = progress_shape_descriptors(closes, record["published_raw_occurrence_bars"])
    asym = leg_asymmetry(desc)
    return {
        "first_leg_progress_l1": float(desc["first_leg_progress_l1"]),
        "second_leg_progress_l1": float(desc["second_leg_progress_l1"]),
        "first_leg_progress_linf": float(desc["first_leg_progress_linf"]),
        "second_leg_progress_linf": float(desc["second_leg_progress_linf"]),
        "A_L1": float(asym["A_L1"]),
        "A_Linf": float(asym["A_Linf"]),
    }


def summarize(rows: list[dict], fields: tuple[str, ...]) -> dict:
    return {field: numeric_summary([float(row[field]) for row in rows]) for field in fields}


def paired_sign_counts(rows: list[dict], field: str) -> dict:
    vals = [float(row[field]) for row in rows]
    return sign_fractions(vals)


def write_card(path: Path, result: dict) -> None:
    stable = result["stable_both_rescue_summary"]
    sem = result["one_sided_summary_by_semantic"]
    harm = sem["introduced_harm"]
    repair = sem["repaired_old_nonexact"]
    rank = result["threshold_free_rank_comparisons"]
    lines = [
        "# Two-Wave v0.6.40 leg-asymmetry and harmless-slicing stability attribution",
        "",
        f"Formal attribution: **`{result['formal_attribution']}`**",
        "",
        f"Diagnostic universe: **{result['diagnostic_pairs']}** rescue-involved pairs = {result['topology_counts']['both']} stable both-rescue + {result['one_sided_rows']} one-sided.",
        "",
        "Primary quantity: `A_L1 = first_leg_progress_l1 - second_leg_progress_l1`. Zero is the structural equality point, not a fitted cutoff.",
        "",
        "| quantity | stable both-rescue median | harm one-sided median | repair one-sided median |",
        "|---|---:|---:|---:|",
        f"| pair/rescue A_L1 | {stable['pair_mean_A_L1']['median']:.6f} | {harm['rescue_A_L1']['median']:.6f} | {repair['rescue_A_L1']['median']:.6f} |",
        f"| harmless-slicing abs delta A_L1 | {stable['pair_abs_delta_A_L1']['median']:.6f} | {harm['pair_abs_delta_A_L1']['median']:.6f} | {repair['pair_abs_delta_A_L1']['median']:.6f} |",
        f"| pair/rescue A_Linf | {stable['pair_mean_A_Linf']['median']:.6f} | {harm['rescue_A_Linf']['median']:.6f} | {repair['rescue_A_Linf']['median']:.6f} |",
        f"| harmless-slicing abs delta A_Linf | {stable['pair_abs_delta_A_Linf']['median']:.6f} | {harm['pair_abs_delta_A_Linf']['median']:.6f} | {repair['pair_abs_delta_A_Linf']['median']:.6f} |",
        "",
        f"P(harm rescue A_L1 > stable pair-mean A_L1): **{rank['harm_rescue_A_L1_gt_stable_pair_mean_A_L1']:.6f}**",
        f"P(harm |delta A_L1| > stable |delta A_L1|): **{rank['harm_abs_delta_A_L1_gt_stable_abs_delta_A_L1']:.6f}**",
        f"P(harm rescue A_Linf > stable pair-mean A_Linf): **{rank['harm_rescue_A_Linf_gt_stable_pair_mean_A_Linf']:.6f}**",
        f"P(harm |delta A_Linf| > stable |delta A_Linf|): **{rank['harm_abs_delta_A_Linf_gt_stable_abs_delta_A_Linf']:.6f}**",
        "",
        f"One-sided rescue-minus-nonrescue A_L1 sign fractions: `{result['paired_difference_sign_fractions']['A_L1']}`.",
        "",
        "This remains diagnostic only. No fitted threshold, recognizer change, trade authority or production authority is authorized by v0.6.40 itself.",
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
    stable_rows: list[dict] = []
    one_rows: list[dict] = []

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
            topology37[topo] += 1

            if topo == "both":
                main_shape = shape_asymmetry(closes[main_view], a)
                other_shape = shape_asymmetry(closes[view], b)
                row = {
                    "offset_pair": view,
                    "topology": "both",
                    "v0625_pair": list(p25),
                    "v0637_pair": list(p37),
                    "main_A_L1": main_shape["A_L1"],
                    "other_A_L1": other_shape["A_L1"],
                    "pair_mean_A_L1": float((main_shape["A_L1"] + other_shape["A_L1"]) / 2.0),
                    "pair_abs_delta_A_L1": float(abs(main_shape["A_L1"] - other_shape["A_L1"])),
                    "main_A_Linf": main_shape["A_Linf"],
                    "other_A_Linf": other_shape["A_Linf"],
                    "pair_mean_A_Linf": float((main_shape["A_Linf"] + other_shape["A_Linf"]) / 2.0),
                    "pair_abs_delta_A_Linf": float(abs(main_shape["A_Linf"] - other_shape["A_Linf"])),
                    "main_A_L1_sign": sign_bucket(main_shape["A_L1"]),
                    "other_A_L1_sign": sign_bucket(other_shape["A_L1"]),
                    "main_A_Linf_sign": sign_bucket(main_shape["A_Linf"]),
                    "other_A_Linf_sign": sign_bucket(other_shape["A_Linf"]),
                }
                stable_rows.append(row)
                continue

            if topo not in {"main_only", "other_only"}:
                continue

            sem = semantic_class(p25, p37)
            semantic_counts[sem] += 1
            if lc:
                rescue_view, rescue_record = main_view, a
                nonrescue_view, nonrescue_record = view, b
                old_label, plain_label, balanced_label = a37["v0625"], a35["v0635"], a37["v0637"]
                side = "main"
            else:
                rescue_view, rescue_record = view, b
                nonrescue_view, nonrescue_record = main_view, a
                old_label, plain_label, balanced_label = b37["v0625"], b35["v0635"], b37["v0637"]
                side = "other"
            origin = rescue_origin(old_label, plain_label, balanced_label)
            origin_counts[origin] += 1
            rescue_shape = shape_asymmetry(closes[rescue_view], rescue_record)
            nonrescue_shape = shape_asymmetry(closes[nonrescue_view], nonrescue_record)
            d_l1 = float(rescue_shape["A_L1"] - nonrescue_shape["A_L1"])
            d_linf = float(rescue_shape["A_Linf"] - nonrescue_shape["A_Linf"])
            one_rows.append(
                {
                    "offset_pair": view,
                    "topology": topo,
                    "rescue_side": side,
                    "rescue_view": rescue_view,
                    "nonrescue_view": nonrescue_view,
                    "semantic_class": sem,
                    "rescue_origin": origin,
                    "v0625_pair": list(p25),
                    "v0637_pair": list(p37),
                    "rescue_A_L1": rescue_shape["A_L1"],
                    "nonrescue_A_L1": nonrescue_shape["A_L1"],
                    "rescue_minus_nonrescue_A_L1": d_l1,
                    "pair_abs_delta_A_L1": float(abs(d_l1)),
                    "rescue_A_Linf": rescue_shape["A_Linf"],
                    "nonrescue_A_Linf": nonrescue_shape["A_Linf"],
                    "rescue_minus_nonrescue_A_Linf": d_linf,
                    "pair_abs_delta_A_Linf": float(abs(d_linf)),
                }
            )

    assert total == EXPECTED_BOTHQ
    assert dict(topology37) == EXPECTED_V0637_TOPOLOGY
    assert len(stable_rows) == 61
    assert len(one_rows) == 44
    assert len(stable_rows) + len(one_rows) == EXPECTED_DIAGNOSTIC_PAIRS
    assert dict(semantic_counts) == EXPECTED_SEMANTIC
    assert dict(origin_counts) == EXPECTED_ORIGIN

    by_semantic = defaultdict(list)
    by_origin = defaultdict(list)
    for row in one_rows:
        by_semantic[row["semantic_class"]].append(row)
        by_origin[row["rescue_origin"]].append(row)

    stable_summary = summarize(stable_rows, BOTH_FIELDS)
    one_summary = summarize(one_rows, ONE_FIELDS)
    semantic_summary = {key: summarize(group, ONE_FIELDS) for key, group in by_semantic.items()}
    origin_summary = {key: summarize(group, ONE_FIELDS) for key, group in by_origin.items()}

    harm = by_semantic["introduced_harm"]
    rank = {
        "harm_rescue_A_L1_gt_stable_pair_mean_A_L1": greater_probability(
            [r["rescue_A_L1"] for r in harm], [r["pair_mean_A_L1"] for r in stable_rows]
        ),
        "harm_abs_delta_A_L1_gt_stable_abs_delta_A_L1": greater_probability(
            [r["pair_abs_delta_A_L1"] for r in harm], [r["pair_abs_delta_A_L1"] for r in stable_rows]
        ),
        "harm_rescue_A_Linf_gt_stable_pair_mean_A_Linf": greater_probability(
            [r["rescue_A_Linf"] for r in harm], [r["pair_mean_A_Linf"] for r in stable_rows]
        ),
        "harm_abs_delta_A_Linf_gt_stable_abs_delta_A_Linf": greater_probability(
            [r["pair_abs_delta_A_Linf"] for r in harm], [r["pair_abs_delta_A_Linf"] for r in stable_rows]
        ),
    }

    sign_by_semantic = {
        "A_L1": {
            key: paired_sign_counts(group, "rescue_minus_nonrescue_A_L1")
            for key, group in by_semantic.items()
        },
        "A_Linf": {
            key: paired_sign_counts(group, "rescue_minus_nonrescue_A_Linf")
            for key, group in by_semantic.items()
        },
    }
    stable_sign_agreement = {
        "A_L1": {
            "count": len(stable_rows),
            "same_sign_fraction": float(
                sum(r["main_A_L1_sign"] == r["other_A_L1_sign"] for r in stable_rows) / len(stable_rows)
            ),
        },
        "A_Linf": {
            "count": len(stable_rows),
            "same_sign_fraction": float(
                sum(r["main_A_Linf_sign"] == r["other_A_Linf_sign"] for r in stable_rows) / len(stable_rows)
            ),
        },
    }

    result = {
        "schema": "two_wave_leg_asymmetry_stability_result@0.6.40",
        "formal_attribution": "v0640_leg_asymmetry_and_harmless_slicing_stability_attribution_complete_no_gate_authorized",
        "controls": {
            "filtered_pairs": 57029,
            "raw_strict_pairs": 29453,
            "both_v0618_qualified_pairs": total,
            "grid_points_per_leg": GRID_POINTS_PER_LEG,
            "v0637_pair_change_topology": dict(topology37),
            "reproduced": True,
        },
        "diagnostic_pairs": len(stable_rows) + len(one_rows),
        "topology_counts": dict(topology37),
        "stable_both_rescue_rows": len(stable_rows),
        "one_sided_rows": len(one_rows),
        "semantic_counts": dict(semantic_counts),
        "rescue_origin_counts": dict(origin_counts),
        "stable_both_rescue_summary": stable_summary,
        "one_sided_summary_all": one_summary,
        "one_sided_summary_by_semantic": semantic_summary,
        "one_sided_summary_by_rescue_origin": origin_summary,
        "threshold_free_rank_comparisons": rank,
        "paired_difference_sign_fractions": sign_by_semantic,
        "stable_both_sign_agreement": stable_sign_agreement,
        "gate_authorized": False,
        "reason_gate_not_authorized": "read_only_attribution; no fitted threshold allowed; any equality-boundary challenger requires separate v0641 freeze",
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
    with gzip.open(args.output / "stable_both_rows.jsonl.gz", "wt", encoding="utf-8") as fh:
        for row in stable_rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    with gzip.open(args.output / "one_sided_rows.jsonl.gz", "wt", encoding="utf-8") as fh:
        for row in one_rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
