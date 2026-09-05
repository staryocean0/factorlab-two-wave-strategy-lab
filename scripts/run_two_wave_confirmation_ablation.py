#!/usr/bin/env python3
"""v0.4.3: isolate the pivot-confirmation kernel; no outcome or trading study.

The frozen v0.4.2 strict-three-close detector is the baseline. The only
structural change is confirmation: the opposite running extremum must mature by
the already-frozen ``min_leg`` duration. Qualification, D1 direction logic and
exclusive publishing are imported unchanged from v0.4.2.
"""
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
from factor_lab.visual_structure.two_wave.same_scale_v04 import ScaleConfig, TimeEngine
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig, TemporalMaturityEngine

VIEWS = [f"5m_offset_{i}" for i in range(5)] + ["1m_official"]
FIXED_DAYS = ["2018-06-20", "2019-04-15", "2020-07-15"]


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def lines(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as file:
        with gzip.GzipFile(fileobj=file, mode="wb", mtime=0, filename="") as out:
            for record in records:
                out.write((json.dumps(record, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode())


def quantile(values):
    return {str(q): float(np.quantile(values, q)) for q in (0, .5, .9, 1)} if len(values) else None


def run(engine_cls, bars, cfg):
    engine = engine_cls(cfg)
    for bar in bars:
        engine.update(bar)
    return engine


def ledger_summary(engine, n):
    records, selected = engine.ledger.records, engine.ledger.selected
    partition = engine.ledger.partition(n)
    assert partition[0]["first_bar"] == 0 and partition[-1]["last_bar"] == n - 1
    assert all(a["last_bar"] + 1 == b["first_bar"] for a, b in zip(partition, partition[1:]))
    owned = sum(r["pair_duration"] for r in selected)
    pivots = [p for p in engine.pivots if not p["left_censored"]]
    pivot_spans = [b["occurrence_bar"] - a["occurrence_bar"] for a, b in zip(pivots, pivots[1:]) if a["epoch"] == b["epoch"]]
    return {
        "candidates": len(records), "scale_qualified": sum(r["scale_qualified"] for r in records),
        "selected_disjoint": len(selected), "selected_labels": dict(Counter(r["classification"] for r in selected)),
        "overlap_suppressed": sum(bool(r["overlap_suppressed_by"]) for r in records),
        "owned_bars": owned, "bars": n, "owned_fraction_not_accuracy": owned / n,
        "pivots": len(engine.pivots), "duration_resets": len(engine.resets),
        "pivot_spacing_quantiles": quantile(pivot_spans),
        "candidate_leg_duration_quantiles": quantile([d for r in records for d in r["leg_durations"]]),
        "selected_span_quantiles": quantile([r["pair_duration"] for r in selected]),
        "selected_confirmation_delay_quantiles": quantile([r["confirmation_delay_bars"] for r in selected]),
        "rejection_counts_multilabel": dict(Counter(k for r in records for k in r["scale_rejection_reasons"])),
        "short_leg_rejections": sum("short_leg" in r["scale_rejection_reasons"] for r in records),
        "status": "morphology_replication_not_yet_accepted",
    }


def match_records(a, b):
    aa = {tuple(r["five_occurrence_bars"]): r for r in a.ledger.records}
    bb = {tuple(r["five_occurrence_bars"]): r for r in b.ledger.records}
    common = aa.keys() & bb.keys()
    return {
        "exact_five_point_matches": len(common), "strict3_unmatched": len(aa.keys() - bb.keys()),
        "maturity_unmatched": len(bb.keys() - aa.keys()),
        "classification_changes_matched": sum(aa[k]["classification"] != bb[k]["classification"] for k in common),
        "qualification_changes_matched": sum(aa[k]["scale_qualified"] != bb[k]["scale_qualified"] for k in common),
        "confirmation_changes_matched": sum(aa[k]["confirmation_bar"] != bb[k]["confirmation_bar"] for k in common),
        "selection_changes_matched": sum(aa[k]["selected"] != bb[k]["selected"] for k in common),
    }


def export_engine(folder, engine, bars):
    lines(folder / "candidates.jsonl.gz", engine.ledger.records)
    lines(folder / "selected.jsonl.gz", engine.ledger.selected)
    lines(folder / "partition.jsonl.gz", engine.ledger.partition(len(bars)))
    lines(folder / "confirmation_events.jsonl.gz", engine.ledger.events)
    lines(folder / "pivots.jsonl.gz", engine.pivots)
    lines(folder / "resets.jsonl.gz", engine.resets)


def coverage_mask(selected, timestamps):
    mask = np.zeros(len(timestamps), dtype=bool)
    for record in selected:
        start = pd.Timestamp(record["start_time"]).value
        end = pd.Timestamp(record["end_time"]).value
        left = np.searchsorted(timestamps, start, side="right")
        right = np.searchsorted(timestamps, end, side="right")
        mask[left:right] = True
    return mask


def interval_iou(masks):
    main = masks["5m_offset_0"]
    out = {}
    for view in [f"5m_offset_{i}" for i in range(1, 5)]:
        other = masks[view]
        inter = int(np.sum(main & other)); union = int(np.sum(main | other))
        out[view] = {"intersection_1m_bars": inter, "union_1m_bars": union,
                     "iou": inter / union if union else None}
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


def fixed_window_audit(bars, strict3, maturity):
    out = {}
    for day in FIXED_DAYS:
        ids = [i for i, bar in enumerate(bars) if day_of(bar) == day]
        if not ids:
            out[day] = {"present": False}; continue
        lo, hi = min(ids), max(ids)
        def overlap(engine):
            records = [r for r in engine.ledger.records if r["end_bar"] >= lo and r["start_bar"] <= hi]
            selected = [r for r in engine.ledger.selected if r["end_bar"] >= lo and r["start_bar"] <= hi]
            return {
                "candidate_count": len(records), "qualified_count": sum(r["scale_qualified"] for r in records),
                "selected_count": len(selected),
                "selected": [{k: r[k] for k in ("record_id", "classification", "five_occurrence_bars", "confirmation_bar")} for r in selected],
            }
        out[day] = {"present": True, "bar_range": [lo, hi], "strict3": overlap(strict3), "maturity": overlap(maturity)}
    return out


def legacy_audit(path, maturity):
    if not path.exists():
        return {"present": False}
    cases = json.loads(path.read_text())
    exact = {tuple(r["five_occurrence_bars"]): r for r in maturity.ledger.records}
    selected = maturity.ledger.selected
    rows = []
    for case in cases:
        piv = tuple(case["five_occurrence_bars"]); lo, hi = piv[0], piv[-1]
        overlaps = [r for r in selected if r["end_bar"] >= lo and r["start_bar"] <= hi]
        rows.append({
            "case": case["case"], "legacy_five_occurrence_bars": list(piv),
            "legacy_cycle_bars": case.get("cycle_bars"), "legacy_leg_bars": case.get("leg_bars"),
            "exact_v043_candidate": piv in exact,
            "v043_selected_overlap_count": len(overlaps),
            "v043_selected_overlaps": [{k: r[k] for k in ("record_id", "classification", "five_occurrence_bars")} for r in overlaps],
        })
    return {"present": True, "cases": rows}


def render_examples(folder, bars, strict3, maturity):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    folder.mkdir(parents=True, exist_ok=True)
    pools = []
    for label in ("uptrend", "downtrend", "range", "uncertain"):
        rec = next((r for r in maturity.ledger.selected if r["classification"] == label), None)
        if rec: pools.append((f"selected_{label}", rec))
    if maturity.ledger.selected:
        pools.append(("selected_max_confirmation_delay", max(maturity.ledger.selected, key=lambda r: r["confirmation_delay_bars"])))
    rejected = next((r for r in maturity.ledger.records if "jump_dominated_leg" in r["scale_rejection_reasons"]), None)
    if rejected: pools.append(("rejected_jump_dominated", rejected))
    manifest = []
    for tag, record in pools:
        lo = max(0, record["start_bar"] - 20); hi = min(len(bars) - 1, record["end_bar"] + 20)
        x = np.arange(lo, hi + 1); y = [bars[i]["close"] for i in x]
        fig, ax = plt.subplots(figsize=(12, 5)); ax.plot(x, y, linewidth=1)
        for p in strict3.pivots:
            if lo <= p["occurrence_bar"] <= hi and not p["left_censored"]:
                ax.scatter(p["occurrence_bar"], p["price"], marker="x", s=30)
        for p in maturity.pivots:
            if lo <= p["occurrence_bar"] <= hi and not p["left_censored"]:
                ax.scatter(p["occurrence_bar"], p["price"], marker="o", facecolors="none", s=45)
        ax.set_title(f"{tag}: x=strict3 pivot, circle=v0.4.3 maturity pivot; {record['classification']}")
        ax.set_xlabel("bar index"); ax.set_ylabel("close")
        fig.tight_layout(); path = folder / f"{tag}.png"; fig.savefig(path, dpi=130); plt.close(fig)
        manifest.append({"tag": tag, "record_id": record["record_id"], "image": path.name,
                         "five_occurrence_bars": record["five_occurrence_bars"],
                         "rejections": record["scale_rejection_reasons"]})
    save(folder / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--views", nargs="+", default=VIEWS)
    parser.add_argument("--skip-prefix", action="store_true")
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    if not set(args.views) <= set(VIEWS):
        raise ValueError("only original six development views allowed")

    sources = [Path(__file__), ROOT / "src/factor_lab/visual_structure/two_wave/same_scale_v043.py",
               ROOT / "tests/unit/test_two_wave_confirmation_v043.py"]
    summary = {
        "schema": "two_wave_confirmation_ablation@0.4.3", "data_role": "development_material",
        "fresh_oos": False, "future_outcome_used": False, "trade_authority": False,
        "status": "morphology_replication_not_yet_accepted",
        "changed_component_only": "pivot_confirmation_kernel",
        "unchanged_components": ["v0.4.2 pair qualification", "D1 direction", "exclusive (start,end] publishing"],
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        "views": {}, "prefix_checks": [],
    }
    engines = {}; bars_by_view = {}
    for view in args.views:
        bars, audit = load_development_bars(ROOT / f"data/development/{view}.parquet", ROOT / "data/manifest.json")
        strict3 = run(TimeEngine, bars, ScaleConfig(timeframe=view))
        maturity = run(TemporalMaturityEngine, bars, MaturityConfig(timeframe=view))
        if view == "5m_offset_0":
            assert (len(strict3.ledger.records), sum(r["scale_qualified"] for r in strict3.ledger.records), len(strict3.ledger.selected)) == (4184, 151, 100)
        usable = [p for p in maturity.pivots if not p["left_censored"]]
        assert all(b["occurrence_bar"] - a["occurrence_bar"] >= maturity.shape_config.min_leg
                   for a, b in zip(usable, usable[1:]) if a["epoch"] == b["epoch"])
        assert all("short_leg" not in r["scale_rejection_reasons"] for r in maturity.ledger.records)
        strict_summary = ledger_summary(strict3, len(bars)); mature_summary = ledger_summary(maturity, len(bars))
        export_engine(args.output / view, maturity, bars)
        summary["views"][view] = {"data_audit": audit, "strict3_v042": strict_summary,
                                  "maturity_v043": mature_summary, "matching": match_records(strict3, maturity),
                                  "v043_config": asdict(maturity.shape_config)}
        if not args.skip_prefix:
            for fraction in (.25, .5, .75):
                n = int(len(bars) * fraction); prefix = run(TemporalMaturityEngine, bars[:n], MaturityConfig(timeframe=view))
                expected_records = [r for r in maturity.ledger.records if r["confirmation_bar"] < n]
                assert prefix.ledger.records == expected_records
                assert prefix.pivots == [p for p in maturity.pivots if p["confirmation_bar"] < n]
                assert prefix.resets == [r for r in maturity.resets if r["bar"] < n]
                summary["prefix_checks"].append({"view": view, "bars": n, "records": len(expected_records), "passed": True})
        engines[view] = (strict3, maturity); bars_by_view[view] = bars
        save(args.output / "summary.json", summary)
        print("VIEW_DONE", view, strict_summary["candidates"], "->", mature_summary["candidates"],
              strict_summary["selected_disjoint"], "->", mature_summary["selected_disjoint"], flush=True)

    if all(v in engines for v in [f"5m_offset_{i}" for i in range(5)]) and "1m_official" in bars_by_view:
        one_minute_ns = np.asarray([pd.Timestamp(b["timestamp"]).value for b in bars_by_view["1m_official"]], dtype=np.int64)
        strict_masks = {v: coverage_mask(engines[v][0].ledger.selected, one_minute_ns) for v in [f"5m_offset_{i}" for i in range(5)]}
        mature_masks = {v: coverage_mask(engines[v][1].ledger.selected, one_minute_ns) for v in [f"5m_offset_{i}" for i in range(5)]}
        summary["native_5m_offset_interval_iou"] = {"strict3_v042": interval_iou(strict_masks), "maturity_v043": interval_iou(mature_masks),
                                                      "mapping_basis": "existing 1m timestamps only; no price resampling"}

    if "5m_offset_0" in engines:
        strict3, maturity = engines["5m_offset_0"]; bars = bars_by_view["5m_offset_0"]
        summary["fixed_window_audit"] = fixed_window_audit(bars, strict3, maturity)
        legacy_path = ROOT / "cloud_results/two_wave_same_scale_delivery/v04/legacy_case_reaudit.json"
        summary["legacy_C1_case_audit"] = legacy_audit(legacy_path, maturity)
        summary["rendered_examples"] = render_examples(args.output / "gallery", bars, strict3, maturity)
        case02 = next((x for x in summary["legacy_C1_case_audit"].get("cases", []) if x["case"].startswith("case_02")), None)
        if case02 is not None:
            assert case02["exact_v043_candidate"] is False

    save(args.output / "summary.json", summary)
    print("STUDY_COMPLETE", args.output, flush=True)


if __name__ == "__main__":
    main()
