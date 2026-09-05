#!/usr/bin/env python3
"""v0.4.4 hierarchical candidate-construction ablation; no outcomes or trading."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.frequency_v03 import path_metrics
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig, TemporalMaturityEngine
from factor_lab.visual_structure.two_wave.same_scale_v044 import (
    H16_ROLE,
    HIERARCHY_MODE,
    HierarchicalCycleEngine,
    hierarchy_reason_counts,
)

VIEWS = [f"5m_offset_{i}" for i in range(5)] + ["1m_official"]
FIXED_DAYS = ["2018-06-20", "2019-04-15", "2020-07-15"]
FOCUS_CASES = {
    "case_00_A_clear_C_uncertain",
    "case_02_C_new_downtrend",
    "case_10_stable_range",
    "case_11_stable_range",
    "case_14_stable_uptrend",
}


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def lines(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as file:
        with gzip.GzipFile(fileobj=file, mode="wb", mtime=0, filename="") as out:
            for record in records:
                out.write(
                    (json.dumps(record, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()
                )


def quantile(values):
    return {str(q): float(np.quantile(values, q)) for q in (0, .5, .9, 1)} if len(values) else None


def run(engine_cls, bars, cfg):
    engine = engine_cls(cfg)
    for bar in bars:
        engine.update(bar)
    return engine


def summary_v043(engine, n):
    records, selected = engine.ledger.records, engine.ledger.selected
    partition = engine.ledger.partition(n)
    owned = sum(r["pair_duration"] for r in selected)
    return {
        "candidates": len(records),
        "scale_qualified": sum(r["scale_qualified"] for r in records),
        "selected_disjoint": len(selected),
        "selected_labels": dict(Counter(r["classification"] for r in selected)),
        "owned_bars": owned,
        "bars": n,
        "owned_fraction_not_accuracy": owned / n,
        "local_pivots": len(engine.pivots),
        "duration_resets": len(engine.resets),
        "partition_full": (
            partition[0]["first_bar"] == 0
            and partition[-1]["last_bar"] == n - 1
            and all(a["last_bar"] + 1 == b["first_bar"] for a, b in zip(partition, partition[1:]))
        ),
        "status": "morphology_replication_not_yet_accepted",
    }


def summary_v044(engine, n):
    records, selected = engine.ledger.records, engine.ledger.selected
    partition = engine.ledger.partition(n)
    owned = sum(r["pair_duration"] for r in selected)
    return {
        "candidates": len(records),
        "scale_qualified": sum(r["scale_qualified"] for r in records),
        "selected_disjoint": len(selected),
        "selected_labels": dict(Counter(r["classification"] for r in selected)),
        "owned_bars": owned,
        "bars": n,
        "owned_fraction_not_accuracy": owned / n,
        "local_pivots_frozen_v043": len(engine.local_pivots),
        "parent_pivots": len(engine.parent_pivots),
        "parent_cycles": len(engine.parent_cycles),
        "skipped_local_pivots_decided": len(engine.skipped_local_pivots),
        "pending_local_pivots_provisional": len(engine.pending_local_pivots),
        "skip_reason_counts": hierarchy_reason_counts(engine),
        "parent_cycle_duration_quantiles": quantile([c["duration_bars"] for c in engine.parent_cycles]),
        "collapsed_local_pivots_per_cycle_quantiles": quantile(
            [c["collapsed_local_pivot_count"] for c in engine.parent_cycles]
        ),
        "collapsed_local_pivots_per_candidate_quantiles": quantile(
            [r["collapsed_local_pivots_in_two_cycles"] for r in records]
        ),
        "candidate_span_quantiles": quantile([r["pair_duration"] for r in records]),
        "selected_span_quantiles": quantile([r["pair_duration"] for r in selected]),
        "selected_confirmation_delay_quantiles": quantile(
            [r["confirmation_delay_bars"] for r in selected]
        ),
        "rejection_counts_multilabel": dict(
            Counter(k for r in records for k in r["scale_rejection_reasons"])
        ),
        "partition_full": (
            partition[0]["first_bar"] == 0
            and partition[-1]["last_bar"] == n - 1
            and all(a["last_bar"] + 1 == b["first_bar"] for a, b in zip(partition, partition[1:]))
        ),
        "hierarchy_mode": HIERARCHY_MODE,
        "h16_role": H16_ROLE,
        "status": "morphology_replication_not_yet_accepted",
    }


def export_engine(folder, engine, bars):
    lines(folder / "candidates.jsonl.gz", engine.ledger.records)
    lines(folder / "selected.jsonl.gz", engine.ledger.selected)
    lines(folder / "partition.jsonl.gz", engine.ledger.partition(len(bars)))
    lines(folder / "confirmation_events.jsonl.gz", engine.ledger.events)
    lines(folder / "local_pivots_v043.jsonl.gz", engine.local_pivots)
    lines(folder / "parent_pivots_v044.jsonl.gz", engine.parent_pivots)
    lines(folder / "parent_cycles_v044.jsonl.gz", engine.parent_cycles)
    lines(folder / "skipped_local_pivots_v044.jsonl.gz", engine.skipped_local_pivots)
    lines(folder / "pending_local_pivots_v044.jsonl.gz", engine.pending_local_pivots)
    lines(folder / "local_resets_v043.jsonl.gz", engine.resets)
    lines(folder / "hierarchy_resets_v044.jsonl.gz", engine.hierarchy_resets)


def coverage_and_labels(selected, timestamps):
    mask = np.zeros(len(timestamps), dtype=bool)
    labels = np.full(len(timestamps), "", dtype=object)
    for record in selected:
        start = pd.Timestamp(record["start_time"]).value
        end = pd.Timestamp(record["end_time"]).value
        left = np.searchsorted(timestamps, start, side="right")
        right = np.searchsorted(timestamps, end, side="right")
        mask[left:right] = True
        labels[left:right] = record["classification"]
    return mask, labels


def cross_offset_metrics(series):
    main_mask, main_labels = series["5m_offset_0"]
    out = {}
    for view in [f"5m_offset_{i}" for i in range(1, 5)]:
        mask, labels = series[view]
        inter_mask = main_mask & mask
        union = int(np.sum(main_mask | mask))
        same_label = int(np.sum((main_labels == labels) & inter_mask))
        inter = int(np.sum(inter_mask))
        out[view] = {
            "intersection_1m_bars": inter,
            "union_1m_bars": union,
            "iou": inter / union if union else None,
            "main_owned_fraction": float(np.mean(main_mask)),
            "other_owned_fraction": float(np.mean(mask)),
            "main_only_fraction": float(np.mean(main_mask & ~mask)),
            "other_only_fraction": float(np.mean(mask & ~main_mask)),
            "both_uncovered_fraction": float(np.mean(~main_mask & ~mask)),
            "same_direction_or_uncertain_fraction_on_common_owned": same_label / inter if inter else None,
        }
    return out


def day_of(bar):
    if bar.get("trading_day") is not None:
        return str(bar["trading_day"])
    stamp = pd.Timestamp(bar["timestamp"])
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("Asia/Shanghai")
    else:
        stamp = stamp.tz_convert("Asia/Shanghai")
    return stamp.date().isoformat()


def compact_record(record):
    return {
        k: record[k]
        for k in (
            "record_id", "classification", "five_occurrence_bars", "leg_durations",
            "cycle_durations", "confirmation_bar", "scale_qualified",
            "scale_rejection_reasons", "collapsed_local_pivots_in_two_cycles",
        )
    }


def fixed_window_audit(bars, v043, v044):
    out = {}
    for day in FIXED_DAYS:
        ids = [i for i, bar in enumerate(bars) if day_of(bar) == day]
        if not ids:
            out[day] = {"present": False}
            continue
        lo, hi = min(ids), max(ids)

        def overlap(engine):
            records = [
                r for r in engine.ledger.records
                if r["end_bar"] >= lo and r["start_bar"] <= hi
            ]
            selected = [
                r for r in engine.ledger.selected
                if r["end_bar"] >= lo and r["start_bar"] <= hi
            ]
            return {
                "candidate_count": len(records),
                "qualified_count": sum(r["scale_qualified"] for r in records),
                "selected_count": len(selected),
                "candidates": [compact_record(r) for r in records],
                "selected": [compact_record(r) for r in selected],
            }

        parent_cycles = [
            c for c in v044.parent_cycles
            if c["occurrence_bars"][-1] >= lo and c["occurrence_bars"][0] <= hi
        ]
        out[day] = {
            "present": True,
            "bar_range": [lo, hi],
            "v043": overlap(v043),
            "v044": overlap(v044),
            "v044_parent_cycles": parent_cycles,
        }
    return out


def interval_iou_pair(a0, a1, b0, b1):
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = (a1 - a0) + (b1 - b0) - inter
    return inter / union if union else 1.0


def legacy_audit(path, v043, v044):
    if not path.exists():
        return {"present": False}
    cases = json.loads(path.read_text())
    exact43 = {tuple(r["five_occurrence_bars"]): r for r in v043.ledger.records}
    exact44 = {tuple(r["five_occurrence_bars"]): r for r in v044.ledger.records}
    rows = []
    for case in cases:
        piv = tuple(case["five_occurrence_bars"])
        lo, hi = piv[0], piv[-1]
        overlaps = [
            r for r in v044.ledger.records
            if r["end_bar"] >= lo and r["start_bar"] <= hi
        ]
        ranked = sorted(
            overlaps,
            key=lambda r: interval_iou_pair(lo, hi, r["start_bar"], r["end_bar"]),
            reverse=True,
        )
        selected = [
            r for r in v044.ledger.selected
            if r["end_bar"] >= lo and r["start_bar"] <= hi
        ]
        rows.append({
            "case": case["case"],
            "legacy_five_occurrence_bars": list(piv),
            "legacy_cycle_bars": case.get("cycle_bars"),
            "legacy_leg_bars": case.get("leg_bars"),
            "exact_v043_candidate": piv in exact43,
            "exact_v044_candidate": piv in exact44,
            "v044_candidate_overlap_count": len(overlaps),
            "v044_selected_overlap_count": len(selected),
            "v044_top_interval_overlap_candidates_not_model_selection": [
                {
                    **compact_record(r),
                    "legacy_interval_iou": interval_iou_pair(lo, hi, r["start_bar"], r["end_bar"]),
                }
                for r in ranked[:5]
            ],
            "v044_selected_overlaps": [compact_record(r) for r in selected],
        })
    return {"present": True, "cases": rows}


def render_windows(folder, bars, v044, legacy_rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    folder.mkdir(parents=True, exist_ok=True)
    close = np.asarray([b["close"] for b in bars], float)
    er = path_metrics(np.log(close), 16)["er"]
    er_std = pd.Series(er).rolling(128, min_periods=128).std(ddof=0).to_numpy()

    windows = []
    for day in FIXED_DAYS:
        ids = [i for i, bar in enumerate(bars) if day_of(bar) == day]
        if ids:
            windows.append((f"fixed_{day}", max(0, min(ids) - 48), min(len(bars) - 1, max(ids) + 48)))
    by_case = {row["case"]: row for row in legacy_rows}
    for case in sorted(FOCUS_CASES):
        row = by_case.get(case)
        if row:
            p = row["legacy_five_occurrence_bars"]
            windows.append((case, max(0, p[0] - 36), min(len(bars) - 1, p[-1] + 36)))

    manifest = []
    for tag, lo, hi in windows:
        x = np.arange(lo, hi + 1)
        fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
        axes[0].plot(x, close[lo:hi + 1], linewidth=1)
        for p in v044.local_pivots:
            if lo <= p["occurrence_bar"] <= hi and not p["left_censored"]:
                axes[0].scatter(p["occurrence_bar"], p["price"], marker="x", s=25)
        for p in v044.parent_pivots:
            if lo <= p["occurrence_bar"] <= hi:
                axes[0].scatter(p["occurrence_bar"], p["price"], marker="o", facecolors="none", s=55)
        for r in v044.ledger.selected:
            if r["end_bar"] >= lo and r["start_bar"] <= hi:
                axes[0].axvspan(max(lo, r["start_bar"]), min(hi, r["end_bar"]), alpha=.10)
                axes[0].annotate(r["classification"], (r["end_bar"], close[r["end_bar"]]), fontsize=7)
        axes[0].set_title(f"{tag} | x=v0.4.3 local pivot; circle=v0.4.4 parent pivot")
        axes[0].set_ylabel("close")
        axes[1].plot(x, er[lo:hi + 1], label="ER H16 diagnostic")
        axes[1].plot(x, er_std[lo:hi + 1], label="ER std W128 diagnostic")
        axes[1].set_ylim(0, 1)
        axes[1].set_xlabel("original bar ordinal")
        axes[1].legend(fontsize=8)
        fig.tight_layout()
        path = folder / f"{tag}.png"
        fig.savefig(path, dpi=130)
        plt.close(fig)
        manifest.append({"tag": tag, "lo": lo, "hi": hi, "image": path.name})
    save(folder / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--views", nargs="+", default=VIEWS)
    parser.add_argument("--skip-prefix", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if not set(args.views) <= set(VIEWS):
        raise ValueError("only original six development views allowed")

    sources = [
        Path(__file__),
        ROOT / "src/factor_lab/visual_structure/two_wave/same_scale_v044.py",
        ROOT / "tests/unit/test_two_wave_hierarchy_v044.py",
        ROOT / "docs/research/two_wave_hierarchy_protocol_v044.md",
    ]
    summary = {
        "schema": "two_wave_hierarchy_ablation@0.4.4",
        "data_role": "development_material",
        "fresh_oos": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "status": "morphology_replication_not_yet_accepted",
        "changed_component_only": "hierarchical_candidate_construction_over_frozen_v043_local_pivots",
        "unchanged_components": [
            "v0.4.3 local pivot detector",
            "v0.4.2/v0.4.3 pair qualification",
            "D1 direction",
            "effective information clock",
            "exclusive (start,end] publishing",
        ],
        "hierarchy_mode": HIERARCHY_MODE,
        "h16_role": H16_ROLE,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "source_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sources
        },
        "views": {},
        "prefix_checks": [],
    }

    engines = {}
    bars_by_view = {}
    for view in args.views:
        bars, audit = load_development_bars(
            ROOT / f"data/development/{view}.parquet",
            ROOT / "data/manifest.json",
        )
        cfg = MaturityConfig(timeframe=view)
        baseline = run(TemporalMaturityEngine, bars, cfg)
        hierarchy = run(HierarchicalCycleEngine, bars, cfg)

        assert hierarchy.local_pivots == baseline.pivots
        assert hierarchy.resets == baseline.resets
        assert hierarchy.local.ledger.records == baseline.ledger.records
        assert all(
            cfg.min_cycle <= c["duration_bars"] <= cfg.max_cycle
            for c in hierarchy.parent_cycles
        )
        local_ids = {p["pivot_id"] for p in hierarchy.local_pivots}
        assert all(
            p["source_local_pivot_id"] in local_ids
            for p in hierarchy.parent_pivots
        )
        assert all(
            all(pid in local_ids for pid in r["source_local_pivot_ids"])
            for r in hierarchy.ledger.records
        )
        assert all(
            len({p["epoch"] for p in r["points"]}) == 1
            for r in hierarchy.ledger.records
        )
        if view == "5m_offset_0":
            base_tuple = (
                len(baseline.ledger.records),
                sum(r["scale_qualified"] for r in baseline.ledger.records),
                len(baseline.ledger.selected),
            )
            assert base_tuple == (4706, 341, 212), base_tuple

        base_summary = summary_v043(baseline, len(bars))
        hierarchy_summary = summary_v044(hierarchy, len(bars))
        export_engine(args.output / view, hierarchy, bars)
        summary["views"][view] = {
            "data_audit": audit,
            "v043": base_summary,
            "v044": hierarchy_summary,
            "v044_config_reused_v043": asdict(cfg),
            "local_stream_exactly_frozen": True,
        }

        if not args.skip_prefix:
            for fraction in (.25, .5, .75):
                n = int(len(bars) * fraction)
                prefix = run(HierarchicalCycleEngine, bars[:n], MaturityConfig(timeframe=view))
                assert prefix.local_pivots == [
                    p for p in hierarchy.local_pivots if p["confirmation_bar"] < n
                ]
                assert prefix.resets == [r for r in hierarchy.resets if r["bar"] < n]
                assert prefix.parent_pivots == [
                    p for p in hierarchy.parent_pivots if p["confirmation_bar"] < n
                ]
                assert prefix.parent_cycles == [
                    c for c in hierarchy.parent_cycles if c["confirmation_bar"] < n
                ]
                assert prefix.skipped_local_pivots == [
                    r for r in hierarchy.skipped_local_pivots
                    if r["decision_confirmation_bar"] < n
                ]
                assert prefix.hierarchy_resets == [
                    r for r in hierarchy.hierarchy_resets if r["bar"] < n
                ]
                assert prefix.ledger.records == [
                    r for r in hierarchy.ledger.records if r["confirmation_bar"] < n
                ]
                summary["prefix_checks"].append({
                    "view": view,
                    "fraction": fraction,
                    "bars": n,
                    "parent_cycles": len(prefix.parent_cycles),
                    "records": len(prefix.ledger.records),
                    "passed": True,
                })

        engines[view] = (baseline, hierarchy)
        bars_by_view[view] = bars
        save(args.output / "summary.json", summary)
        print(
            "VIEW_DONE", view,
            "v043", base_summary["candidates"], base_summary["selected_disjoint"],
            "v044", hierarchy_summary["candidates"], hierarchy_summary["selected_disjoint"],
            "parent_cycles", hierarchy_summary["parent_cycles"],
            flush=True,
        )

    five_views = [f"5m_offset_{i}" for i in range(5)]
    if all(v in engines for v in five_views) and "1m_official" in bars_by_view:
        one_minute_ns = np.asarray(
            [pd.Timestamp(b["timestamp"]).value for b in bars_by_view["1m_official"]],
            dtype=np.int64,
        )
        v043_series = {
            v: coverage_and_labels(engines[v][0].ledger.selected, one_minute_ns)
            for v in five_views
        }
        v044_series = {
            v: coverage_and_labels(engines[v][1].ledger.selected, one_minute_ns)
            for v in five_views
        }
        summary["native_5m_offset_stability"] = {
            "v043": cross_offset_metrics(v043_series),
            "v044": cross_offset_metrics(v044_series),
            "mapping_basis": "existing 1m timestamps only; no price resampling",
        }

    if "5m_offset_0" in engines:
        baseline, hierarchy = engines["5m_offset_0"]
        bars = bars_by_view["5m_offset_0"]
        summary["fixed_window_audit"] = fixed_window_audit(bars, baseline, hierarchy)
        legacy_path = ROOT / "cloud_results/two_wave_same_scale_delivery/v04/legacy_case_reaudit.json"
        summary["legacy_C1_case_audit"] = legacy_audit(legacy_path, baseline, hierarchy)
        legacy_rows = summary["legacy_C1_case_audit"].get("cases", [])
        summary["rendered_windows"] = render_windows(
            args.output / "gallery",
            bars,
            hierarchy,
            legacy_rows,
        )

        case02 = next(
            (row for row in legacy_rows if row["case"].startswith("case_02")),
            None,
        )
        if case02 is not None:
            assert case02["exact_v044_candidate"] is False
        assert all(r["pair_duration"] <= hierarchy.shape_config.max_pair for r in hierarchy.ledger.records)

    save(args.output / "summary.json", summary)

    if "5m_offset_0" in summary["views"]:
        print("V044_MAIN", json.dumps(summary["views"]["5m_offset_0"], ensure_ascii=False), flush=True)
    if "native_5m_offset_stability" in summary:
        print("V044_OFFSET_STABILITY", json.dumps(summary["native_5m_offset_stability"], ensure_ascii=False), flush=True)
    if "fixed_window_audit" in summary:
        print("V044_FIXED_WINDOWS", json.dumps(summary["fixed_window_audit"], ensure_ascii=False), flush=True)
    if "legacy_C1_case_audit" in summary:
        focus = [
            row for row in summary["legacy_C1_case_audit"].get("cases", [])
            if row["case"] in FOCUS_CASES
        ]
        print("V044_FOCUS_CASES", json.dumps(focus, ensure_ascii=False), flush=True)
    print("STUDY_COMPLETE", args.output, flush=True)


if __name__ == "__main__":
    main()
