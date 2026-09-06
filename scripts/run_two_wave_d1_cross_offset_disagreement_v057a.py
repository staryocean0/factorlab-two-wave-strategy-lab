#!/usr/bin/env python3
"""Read-only v0.5.7a attribution of v0.5.6 D2 cross-offset label instability.

No recognizer is executed here. Inputs are the already-successful formal v0.5.6
native-view artifacts plus the persisted v0.5.6 failure diagnostic.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from aggregate_two_wave_envelope_direction_v056_five_view import load_payloads
from factor_lab.visual_structure.two_wave.data import load_development_bars
from run_two_wave_extremum_ridge_v052 import save

VIEWS = [f"5m_offset_{i}" for i in range(5)]
CATEGORIES = ("both_agree", "D2_harm", "D2_help", "both_disagree")
LABELS = ("range", "uncertain", "uptrend", "downtrend")


def load_failure_summary(root: Path) -> dict:
    matches = []
    for path in root.rglob("summary.json"):
        payload = json.loads(path.read_text())
        if payload.get("schema") == "two_wave_envelope_direction_v056_failed_aggregate_diagnostic@1.0":
            matches.append((path, payload))
    if len(matches) != 1:
        raise AssertionError(f"expected one frozen failure summary, found {len(matches)}")
    return matches[0][1]


def timeline(rows: list[dict], timestamps: np.ndarray):
    n = len(timestamps)
    mask = np.zeros(n, dtype=bool)
    labels = np.full(n, "", dtype=object)
    record_ids = np.full(n, "", dtype=object)
    for row in rows:
        start = pd.Timestamp(row["start_time"]).value
        end = pd.Timestamp(row["end_time"]).value
        left = int(np.searchsorted(timestamps, start, side="right"))
        right = int(np.searchsorted(timestamps, end, side="right"))
        if right < left:
            raise AssertionError("invalid selected interval mapping")
        if np.any(mask[left:right]):
            raise AssertionError("selected intervals must be disjoint within one view")
        mask[left:right] = True
        labels[left:right] = row["classification"]
        record_ids[left:right] = row["record_id"]
    return mask, labels, record_ids


def q(values):
    arr = np.asarray(list(values), dtype=float)
    if not len(arr):
        return None
    return {str(x): float(np.quantile(arr, x)) for x in (0, 0.5, 0.9, 0.99, 1)}


def category(d1_agree: bool, d2_agree: bool) -> str:
    if d1_agree and d2_agree:
        return "both_agree"
    if d1_agree and not d2_agree:
        return "D2_harm"
    if not d1_agree and d2_agree:
        return "D2_help"
    return "both_disagree"


def summarize_offset(view: str, main_cov: dict, other_cov: dict, timestamps: np.ndarray, frozen: dict) -> dict:
    main_d1 = timeline(main_cov["D1"], timestamps)
    main_d2 = timeline(main_cov["D2"], timestamps)
    other_d1 = timeline(other_cov["D1"], timestamps)
    other_d2 = timeline(other_cov["D2"], timestamps)

    # D1/D2 must differ only in labels, never selected boundaries or record ids.
    assert np.array_equal(main_d1[0], main_d2[0])
    assert np.array_equal(main_d1[2], main_d2[2])
    assert np.array_equal(other_d1[0], other_d2[0])
    assert np.array_equal(other_d1[2], other_d2[2])

    common = main_d1[0] & other_d1[0]
    common_idx = np.flatnonzero(common)
    common_n = int(len(common_idx))
    if not common_n:
        raise AssertionError(f"no common owned bars for {view}")

    m1 = main_d1[1][common]
    o1 = other_d1[1][common]
    m2 = main_d2[1][common]
    o2 = other_d2[1][common]
    mid = main_d1[2][common]
    oid = other_d1[2][common]

    d1_agree = m1 == o1
    d2_agree = m2 == o2
    cats = np.empty(common_n, dtype=object)
    cats[d1_agree & d2_agree] = "both_agree"
    cats[d1_agree & ~d2_agree] = "D2_harm"
    cats[~d1_agree & d2_agree] = "D2_help"
    cats[~d1_agree & ~d2_agree] = "both_disagree"

    counts = Counter(cats.tolist())
    for name in CATEGORIES:
        counts.setdefault(name, 0)
    d1_fraction = float(np.mean(d1_agree))
    d2_fraction = float(np.mean(d2_agree))
    delta = d2_fraction - d1_fraction
    identity_delta = (counts["D2_help"] - counts["D2_harm"]) / common_n
    assert math.isclose(delta, identity_delta, abs_tol=1e-15, rel_tol=0)

    frozen_row = frozen["comparison"][view]
    assert common_n == frozen_row["common_owned_1m_bars"]
    assert math.isclose(d1_fraction, frozen_row["D1_same_label_fraction"], abs_tol=1e-15, rel_tol=0)
    assert math.isclose(d2_fraction, frozen_row["D2_same_label_fraction"], abs_tol=1e-15, rel_tol=0)
    assert math.isclose(delta, frozen_row["D2_minus_D1"], abs_tol=1e-15, rel_tol=0)

    harm_shared_d1 = Counter()
    harm_transitions = Counter()
    help_transitions = Counter()
    harm_range_involved = 0
    help_range_involved = 0

    pair_weights = defaultdict(int)
    pair_meta = {}
    for i in range(common_n):
        cat = str(cats[i])
        if cat == "D2_harm":
            if m1[i] != o1[i]:
                raise AssertionError("D2_harm requires shared D1 label")
            harm_shared_d1[str(m1[i])] += 1
            harm_transitions[(str(m1[i]), str(m2[i]), str(o2[i]))] += 1
            if "range" in (m2[i], o2[i]):
                harm_range_involved += 1
        elif cat == "D2_help":
            if m2[i] != o2[i]:
                raise AssertionError("D2_help requires shared D2 label")
            help_transitions[(str(m1[i]), str(o1[i]), str(m2[i]))] += 1
            if "range" in (m2[i], o2[i]):
                help_range_involved += 1

        key = (str(mid[i]), str(oid[i]))
        pair_weights[key] += 1
        meta = (cat, str(m1[i]), str(o1[i]), str(m2[i]), str(o2[i]))
        if key in pair_meta and pair_meta[key] != meta:
            raise AssertionError("labels/category must be constant within one selected record pair overlap")
        pair_meta[key] = meta

    pair_category_counts = Counter(meta[0] for meta in pair_meta.values())
    pair_weight_by_category = defaultdict(list)
    for key, weight in pair_weights.items():
        pair_weight_by_category[pair_meta[key][0]].append(weight)

    harm_n = counts["D2_harm"]
    harm_uncertain = harm_shared_d1.get("uncertain", 0)
    harm_uncertain_fraction = harm_uncertain / harm_n if harm_n else None

    def counter_rows(counter: Counter, names: tuple[str, ...]):
        rows = []
        for key, count in counter.most_common():
            if not isinstance(key, tuple):
                key = (key,)
            rows.append({**{name: value for name, value in zip(names, key)}, "bars": int(count), "fraction_of_common": count / common_n})
        return rows

    return {
        "view": view,
        "common_owned_1m_bars": common_n,
        "D1_same_label_fraction": d1_fraction,
        "D2_same_label_fraction": d2_fraction,
        "D2_minus_D1": delta,
        "four_way_bar_counts": {name: int(counts[name]) for name in CATEGORIES},
        "four_way_bar_fractions": {name: counts[name] / common_n for name in CATEGORIES},
        "agreement_delta_identity_verified": True,
        "D2_harm_shared_D1_labels": {label: int(harm_shared_d1.get(label, 0)) for label in LABELS},
        "D2_harm_shared_D1_uncertain_fraction": harm_uncertain_fraction,
        "D2_harm_transitions": counter_rows(harm_transitions, ("shared_D1", "main_D2", "other_D2")),
        "D2_help_transitions": counter_rows(help_transitions, ("main_D1", "other_D1", "shared_D2")),
        "D2_harm_range_involved_bars": int(harm_range_involved),
        "D2_help_range_involved_bars": int(help_range_involved),
        "record_pairs": {
            "total": len(pair_meta),
            "category_counts": {name: int(pair_category_counts.get(name, 0)) for name in CATEGORIES},
            "weight_1m_bars_quantiles_by_category": {
                name: q(pair_weight_by_category.get(name, [])) for name in CATEGORIES
            },
            "D2_harm_weighted_pairs": [
                {
                    "main_record_id": key[0],
                    "other_record_id": key[1],
                    "bars": int(pair_weights[key]),
                    "shared_D1": pair_meta[key][1],
                    "main_D2": pair_meta[key][3],
                    "other_D2": pair_meta[key][4],
                }
                for key in sorted(pair_weights, key=lambda k: pair_weights[k], reverse=True)
                if pair_meta[key][0] == "D2_harm"
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--views-root", type=Path, required=True)
    parser.add_argument("--failure-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "cloud_results/two_wave_d1_cross_offset_disagreement_v057a/summary.json",
    )
    args = parser.parse_args()

    summaries, coverages = load_payloads(args.views_root)
    frozen = load_failure_summary(args.failure_root)
    assert frozen["source_formal_run"] == 34009427027
    assert frozen["all_four_worse"] is True and frozen["worse_count"] == 4

    prefix_checks = [row for view in VIEWS for row in summaries[view]["prefix_checks"]]
    assert len(prefix_checks) == 15
    assert all(row["passed"] and row["confirmed_rewrite_count"] == 0 for row in prefix_checks)

    bars, data_audit = load_development_bars(
        ROOT / "data/development/1m_official.parquet", ROOT / "data/manifest.json"
    )
    timestamps = np.asarray([pd.Timestamp(bar["timestamp"]).value for bar in bars], dtype=np.int64)

    results = {}
    pooled = Counter()
    pooled_harm_labels = Counter()
    pooled_harm = 0
    pooled_help = 0
    for view in VIEWS[1:]:
        row = summarize_offset(view, coverages["5m_offset_0"], coverages[view], timestamps, frozen)
        results[view] = row
        pooled.update(row["four_way_bar_counts"])
        pooled_harm += row["four_way_bar_counts"]["D2_harm"]
        pooled_help += row["four_way_bar_counts"]["D2_help"]
        pooled_harm_labels.update(row["D2_harm_shared_D1_labels"])

    pooled_uncertain = pooled_harm_labels.get("uncertain", 0)
    pooled_uncertain_fraction = pooled_uncertain / pooled_harm if pooled_harm else None
    next_branch = (
        "stageB_uncertain_resolution_instability"
        if pooled_uncertain_fraction is not None and pooled_uncertain_fraction > 0.5
        else "stageB_stable_label_damage_or_broad_geometry"
    )

    output = {
        "schema": "two_wave_d1_cross_offset_disagreement_attribution@0.5.7a",
        "status": "read_only_cross_offset_disagreement_attribution_not_classifier_result",
        "protocol": "docs/research/two_wave_d1_cross_offset_disagreement_protocol_v057a.md",
        "source_formal_run": 34009427027,
        "source_formal_execution_commit": "266bac6389098169598084667fcb46897a53ccf2",
        "source_failure_diagnostic_run": 34009928175,
        "source_failure_diagnostic_artifact": 9982147148,
        "recognizer_rerun_performed": False,
        "formula_or_threshold_changed": False,
        "native_5m_prefix_evidence_reused": 15,
        "offsets": results,
        "pooled": {
            "four_way_bar_counts_across_four_offset_comparisons": {name: int(pooled[name]) for name in CATEGORIES},
            "D2_harm_bars": int(pooled_harm),
            "D2_help_bars": int(pooled_help),
            "D2_harm_minus_help_bars": int(pooled_harm - pooled_help),
            "D2_harm_shared_D1_labels": {label: int(pooled_harm_labels.get(label, 0)) for label in LABELS},
            "D2_harm_shared_D1_uncertain_fraction": pooled_uncertain_fraction,
        },
        "next_diagnostic_branch_by_frozen_rule": next_branch,
        "one_minute_data_audit": data_audit,
        "trade_authority": False,
        "future_outcome_used": False,
    }
    save(args.output, output)
    print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
