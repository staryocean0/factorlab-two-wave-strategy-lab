#!/usr/bin/env python3
"""Formal read-only v0.6.42 amplitude-normalization stability attribution."""
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

from factor_lab.visual_structure.two_wave.amplitude_normalization_stability_v0642 import (
    amplitude_metrics,
    counterfactual_crossing_attribution,
    signed_symmetric_relative_difference,
    symmetric_relative_difference,
)
from factor_lab.visual_structure.two_wave.d1_huber_erosion_consensus_v0623 import (
    SUPPORT_NAMES,
    endpoint_erosion_anchor_views,
)
from factor_lab.visual_structure.two_wave.d1_phase_balanced_wasserstein_range_v0637 import (
    RANGE_W1_MAX,
    phase_balanced_cycle_wasserstein_distance,
)
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.leg_asymmetry_stability_v0640 import (
    greater_probability,
    sign_fractions,
)
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.order_sensitive_residual_shape_v0639 import numeric_summary
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
    reconstruct_pair,
)
from scripts.run_two_wave_phase_balanced_wasserstein_range_v0637 import state as state_v0637
from scripts.run_two_wave_two_cycle_wasserstein_range_v0635 import state as state_v0635

EXPECTED_TOPOLOGY = {"both": 61, "main_only": 23, "other_only": 21, "none": 1357}
EXPECTED_SEMANTIC = {"introduced_harm": 38, "repaired_old_nonexact": 6}
EXPECTED_ORIGIN = {
    "shared_bar_equal_and_phase_balanced_rescue": 32,
    "phase_balanced_only_rescue": 12,
}
EXPECTED_DIAGNOSTIC_PAIRS = 105

STABLE_FIELDS = (
    "pair_mean_amplitude_unit_price",
    "amplitude_unit_SRD",
    "max_raw_w1_SRD",
    "max_normalized_w1_SRD",
    "pair_mean_cycle_amplitude_imbalance",
    "cycle_amplitude_imbalance_SRD",
)
ONE_FIELDS = (
    "rescue_amplitude_unit_price",
    "nonrescue_amplitude_unit_price",
    "amplitude_unit_signed_SRD",
    "amplitude_unit_SRD",
    "rescue_max_raw_w1_price",
    "nonrescue_max_raw_w1_price",
    "max_raw_w1_signed_SRD",
    "max_raw_w1_SRD",
    "rescue_max_normalized_w1",
    "nonrescue_max_normalized_w1",
    "max_normalized_w1_signed_SRD",
    "max_normalized_w1_SRD",
    "rescue_cycle_amplitude_imbalance",
    "nonrescue_cycle_amplitude_imbalance",
    "cycle_amplitude_imbalance_signed_SRD",
    "cycle_amplitude_imbalance_SRD",
)


def side_metrics(record: dict, bars: list[dict], closes: list[float], view: str) -> dict:
    pair = reconstruct_pair(record, bars, view)
    amp = amplitude_metrics(
        pair["detrended_amplitudes_price"], float(pair["amplitude_unit_price"])
    )
    anchors = record["published_raw_occurrence_bars"]
    support_views = endpoint_erosion_anchor_views(anchors)
    supports = {}
    raws = []
    norms = []
    for name in SUPPORT_NAMES:
        detail = phase_balanced_cycle_wasserstein_distance(
            closes,
            support_views[name],
            amp["amplitude_unit_price"],
        )
        raw = float(detail["phase_balanced_cycle_wasserstein_price"])
        norm = float(detail["normalized_phase_balanced_cycle_wasserstein"])
        supports[name] = {"raw_w1_price": raw, "normalized_w1": norm}
        raws.append(raw)
        norms.append(norm)
    max_raw = max(raws)
    max_norm = max(norms)
    if abs(max_norm - max_raw / amp["amplitude_unit_price"]) > 1e-12:
        raise AssertionError("max normalized W1 must equal max raw W1 / frozen amplitude unit")
    return {
        **amp,
        "max_raw_w1_price": float(max_raw),
        "mean_raw_w1_price": float(sum(raws) / len(raws)),
        "max_normalized_w1": float(max_norm),
        "mean_normalized_w1": float(sum(norms) / len(norms)),
        "w1_ceiling_price": float(RANGE_W1_MAX * amp["amplitude_unit_price"]),
        "price_headroom": float(RANGE_W1_MAX * amp["amplitude_unit_price"] - max_raw),
        "normalized_headroom": float(RANGE_W1_MAX - max_norm),
        "all_supports_w1_pass": bool(all(v <= RANGE_W1_MAX + 1e-12 for v in norms)),
        "supports": supports,
    }


def summarize(rows: list[dict], fields: tuple[str, ...]) -> dict:
    return {field: numeric_summary([float(row[field]) for row in rows]) for field in fields}


def category_summary(values: list[str]) -> dict:
    if not values:
        raise ValueError("non-empty category values required")
    counts = Counter(values)
    n = len(values)
    return {
        "count": n,
        "counts": dict(sorted(counts.items())),
        "rates": {k: float(v / n) for k, v in sorted(counts.items())},
    }


def write_card(path: Path, result: dict) -> None:
    rank = result["threshold_free_rank_comparisons"]
    cats = result["harm_counterfactual_attribution"]
    harm = result["one_sided_summary_by_semantic"]["introduced_harm"]
    stable = result["stable_both_rescue_summary"]
    lines = [
        "# Two-Wave v0.6.42 amplitude-normalization stability attribution",
        "",
        f"Formal attribution: **`{result['formal_attribution']}`**",
        "",
        f"Diagnostic universe: **{result['diagnostic_pairs']}** = {result['topology_counts']['both']} stable both-rescue + {result['one_sided_rows']} one-sided; harm counterfactual rows = {cats['count']}.",
        "",
        "| quantity | stable median | harm median | rank P(harm > stable) |",
        "|---|---:|---:|---:|",
        f"| amplitude-unit SRD | {stable['amplitude_unit_SRD']['median']:.6f} | {harm['amplitude_unit_SRD']['median']:.6f} | {rank['harm_amplitude_unit_SRD_gt_stable']:.6f} |",
        f"| max raw-W1 SRD | {stable['max_raw_w1_SRD']['median']:.6f} | {harm['max_raw_w1_SRD']['median']:.6f} | {rank['harm_max_raw_w1_SRD_gt_stable']:.6f} |",
        f"| max normalized-W1 SRD | {stable['max_normalized_w1_SRD']['median']:.6f} | {harm['max_normalized_w1_SRD']['median']:.6f} | {rank['harm_max_normalized_w1_SRD_gt_stable']:.6f} |",
        f"| cycle-amplitude-imbalance SRD | {stable['cycle_amplitude_imbalance_SRD']['median']:.6f} | {harm['cycle_amplitude_imbalance_SRD']['median']:.6f} | {rank['harm_cycle_amplitude_imbalance_SRD_gt_stable']:.6f} |",
        "",
        f"Harm counterfactual attribution counts: `{cats['counts']}`.",
        f"Harm signed amplitude-unit change fractions: `{result['harm_signed_change_fractions']['amplitude_unit']}`.",
        f"Harm signed raw-W1 change fractions: `{result['harm_signed_change_fractions']['max_raw_w1']}`.",
        f"Harm signed normalized-W1 change fractions: `{result['harm_signed_change_fractions']['max_normalized_w1']}`.",
        "",
        "v0.6.42 is diagnostic only. It does not change the recognizer, tune the inherited 0.15 ceiling, or authorize a gate.",
    ]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    filtered: dict[str, list[dict]] = {}
    records: dict[str, list[dict]] = {}
    maps: dict[str, dict] = {}
    bars: dict[str, list[dict]] = {}
    closes: dict[str, list[float]] = {}
    states35: dict[str, dict] = {}
    states37: dict[str, dict] = {}
    side_cache: dict[str, dict] = {}

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
        side_cache[view] = {}
        for row in records[view]:
            if not bool(row["candidate_qualified"]):
                continue
            key = fkey(row)
            states35[view][key] = state_v0635(row, bars[view], closes[view], view)
            states37[view][key] = state_v0637(row, bars[view], closes[view], view)
            assert states35[view][key]["v0625"] == states37[view][key]["v0625"]

    def get_side(view: str, record: dict) -> dict:
        key = fkey(record)
        if key not in side_cache[view]:
            side_cache[view][key] = side_metrics(record, bars[view], closes[view], view)
        return side_cache[view][key]

    main_view = "5m_offset_0"
    total = 0
    topology = Counter()
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
            topology[topo] += 1

            if topo == "both":
                ma = get_side(main_view, a)
                ob = get_side(view, b)
                assert ma["all_supports_w1_pass"] and ob["all_supports_w1_pass"]
                stable_rows.append(
                    {
                        "offset_pair": view,
                        "topology": "both",
                        "main_amplitude_unit_price": ma["amplitude_unit_price"],
                        "other_amplitude_unit_price": ob["amplitude_unit_price"],
                        "pair_mean_amplitude_unit_price": float((ma["amplitude_unit_price"] + ob["amplitude_unit_price"]) / 2.0),
                        "amplitude_unit_SRD": symmetric_relative_difference(ma["amplitude_unit_price"], ob["amplitude_unit_price"]),
                        "main_max_raw_w1_price": ma["max_raw_w1_price"],
                        "other_max_raw_w1_price": ob["max_raw_w1_price"],
                        "max_raw_w1_SRD": symmetric_relative_difference(ma["max_raw_w1_price"], ob["max_raw_w1_price"]),
                        "main_max_normalized_w1": ma["max_normalized_w1"],
                        "other_max_normalized_w1": ob["max_normalized_w1"],
                        "max_normalized_w1_SRD": symmetric_relative_difference(ma["max_normalized_w1"], ob["max_normalized_w1"]),
                        "main_cycle_amplitude_imbalance": ma["cycle_amplitude_imbalance"],
                        "other_cycle_amplitude_imbalance": ob["cycle_amplitude_imbalance"],
                        "pair_mean_cycle_amplitude_imbalance": float((ma["cycle_amplitude_imbalance"] + ob["cycle_amplitude_imbalance"]) / 2.0),
                        "cycle_amplitude_imbalance_SRD": symmetric_relative_difference(ma["cycle_amplitude_imbalance"], ob["cycle_amplitude_imbalance"]),
                    }
                )
                continue

            if topo not in {"main_only", "other_only"}:
                continue

            sem = semantic_class(p25, p37)
            semantic_counts[sem] += 1
            if lc:
                rescue_view, rescue_record = main_view, a
                nonrescue_view, nonrescue_record = view, b
                old_label, plain_label, balanced_label = a37["v0625"], a35["v0635"], a37["v0637"]
                rescue_side = "main"
            else:
                rescue_view, rescue_record = view, b
                nonrescue_view, nonrescue_record = main_view, a
                old_label, plain_label, balanced_label = b37["v0625"], b35["v0635"], b37["v0637"]
                rescue_side = "other"
            origin = rescue_origin(old_label, plain_label, balanced_label)
            origin_counts[origin] += 1
            rs = get_side(rescue_view, rescue_record)
            ns = get_side(nonrescue_view, nonrescue_record)
            assert rs["all_supports_w1_pass"]
            if sem == "introduced_harm":
                assert not ns["all_supports_w1_pass"]
                counterfactual = counterfactual_crossing_attribution(
                    rescue_max_raw_w1=rs["max_raw_w1_price"],
                    rescue_amplitude_unit=rs["amplitude_unit_price"],
                    nonrescue_max_raw_w1=ns["max_raw_w1_price"],
                    nonrescue_amplitude_unit=ns["amplitude_unit_price"],
                    inherited_w1_ceiling=RANGE_W1_MAX,
                )
                category = counterfactual["attribution_category"]
            else:
                counterfactual = None
                category = None

            one_rows.append(
                {
                    "offset_pair": view,
                    "topology": topo,
                    "rescue_side": rescue_side,
                    "rescue_view": rescue_view,
                    "nonrescue_view": nonrescue_view,
                    "semantic_class": sem,
                    "rescue_origin": origin,
                    "rescue_amplitude_unit_price": rs["amplitude_unit_price"],
                    "nonrescue_amplitude_unit_price": ns["amplitude_unit_price"],
                    "amplitude_unit_signed_SRD": signed_symmetric_relative_difference(rs["amplitude_unit_price"], ns["amplitude_unit_price"]),
                    "amplitude_unit_SRD": symmetric_relative_difference(rs["amplitude_unit_price"], ns["amplitude_unit_price"]),
                    "rescue_max_raw_w1_price": rs["max_raw_w1_price"],
                    "nonrescue_max_raw_w1_price": ns["max_raw_w1_price"],
                    "max_raw_w1_signed_SRD": signed_symmetric_relative_difference(rs["max_raw_w1_price"], ns["max_raw_w1_price"]),
                    "max_raw_w1_SRD": symmetric_relative_difference(rs["max_raw_w1_price"], ns["max_raw_w1_price"]),
                    "rescue_max_normalized_w1": rs["max_normalized_w1"],
                    "nonrescue_max_normalized_w1": ns["max_normalized_w1"],
                    "max_normalized_w1_signed_SRD": signed_symmetric_relative_difference(rs["max_normalized_w1"], ns["max_normalized_w1"]),
                    "max_normalized_w1_SRD": symmetric_relative_difference(rs["max_normalized_w1"], ns["max_normalized_w1"]),
                    "rescue_cycle_amplitude_imbalance": rs["cycle_amplitude_imbalance"],
                    "nonrescue_cycle_amplitude_imbalance": ns["cycle_amplitude_imbalance"],
                    "cycle_amplitude_imbalance_signed_SRD": signed_symmetric_relative_difference(rs["cycle_amplitude_imbalance"], ns["cycle_amplitude_imbalance"]),
                    "cycle_amplitude_imbalance_SRD": symmetric_relative_difference(rs["cycle_amplitude_imbalance"], ns["cycle_amplitude_imbalance"]),
                    "rescue_price_headroom": rs["price_headroom"],
                    "nonrescue_price_headroom": ns["price_headroom"],
                    "counterfactual_attribution": category,
                    "counterfactual_detail": counterfactual,
                }
            )

    assert total == EXPECTED_BOTHQ
    assert dict(topology) == EXPECTED_TOPOLOGY
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

    stable_summary = summarize(stable_rows, STABLE_FIELDS)
    one_summary = summarize(one_rows, ONE_FIELDS)
    semantic_summary = {key: summarize(group, ONE_FIELDS) for key, group in by_semantic.items()}
    origin_summary = {key: summarize(group, ONE_FIELDS) for key, group in by_origin.items()}

    harm = by_semantic["introduced_harm"]
    rank = {
        "harm_amplitude_unit_SRD_gt_stable": greater_probability(
            [r["amplitude_unit_SRD"] for r in harm],
            [r["amplitude_unit_SRD"] for r in stable_rows],
        ),
        "harm_max_raw_w1_SRD_gt_stable": greater_probability(
            [r["max_raw_w1_SRD"] for r in harm],
            [r["max_raw_w1_SRD"] for r in stable_rows],
        ),
        "harm_max_normalized_w1_SRD_gt_stable": greater_probability(
            [r["max_normalized_w1_SRD"] for r in harm],
            [r["max_normalized_w1_SRD"] for r in stable_rows],
        ),
        "harm_cycle_amplitude_imbalance_SRD_gt_stable": greater_probability(
            [r["cycle_amplitude_imbalance_SRD"] for r in harm],
            [r["cycle_amplitude_imbalance_SRD"] for r in stable_rows],
        ),
    }

    harm_categories = [str(r["counterfactual_attribution"]) for r in harm]
    if any(v == "None" for v in harm_categories):
        raise AssertionError("every harm row must have a counterfactual attribution")
    harm_counterfactual = category_summary(harm_categories)
    harm_signs = {
        "amplitude_unit": sign_fractions([r["amplitude_unit_signed_SRD"] for r in harm]),
        "max_raw_w1": sign_fractions([r["max_raw_w1_signed_SRD"] for r in harm]),
        "max_normalized_w1": sign_fractions([r["max_normalized_w1_signed_SRD"] for r in harm]),
    }

    result = {
        "schema": "two_wave_amplitude_normalization_stability_result@0.6.42",
        "formal_attribution": "v0642_amplitude_normalization_stability_attribution_complete_no_gate_authorized",
        "controls": {
            "filtered_pairs": 57029,
            "raw_strict_pairs": 29453,
            "both_v0618_qualified_pairs": total,
            "v0637_pair_change_topology": dict(topology),
            "inherited_w1_ceiling": RANGE_W1_MAX,
            "phase_balanced_leg_mass": 0.5,
            "reproduced": True,
        },
        "diagnostic_pairs": EXPECTED_DIAGNOSTIC_PAIRS,
        "stable_both_rows": len(stable_rows),
        "one_sided_rows": len(one_rows),
        "semantic_counts": dict(semantic_counts),
        "rescue_origin_counts": dict(origin_counts),
        "stable_both_rescue_summary": stable_summary,
        "one_sided_summary": one_summary,
        "one_sided_summary_by_semantic": semantic_summary,
        "one_sided_summary_by_rescue_origin": origin_summary,
        "threshold_free_rank_comparisons": rank,
        "harm_counterfactual_attribution": harm_counterfactual,
        "harm_signed_change_fractions": harm_signs,
        "repair_counterfactual_categories_assigned": False,
        "gate_authorized": False,
        "reason_gate_not_authorized": "read_only_numerator_denominator_attribution_only; any alternative normalization requires a separately frozen challenger",
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
