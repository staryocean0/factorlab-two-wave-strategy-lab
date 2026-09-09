#!/usr/bin/env python3
"""Autonomous H0 candidate comparison. No P&L or independent-label claim."""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import math
import os
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from factor_lab.visual_structure.two_wave.candidate_v02 import CandidateConfig, CandidateEngine, VARIANTS
from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.engine import Engine
from factor_lab.visual_structure.two_wave.models import Config

METHODS = ("v01", *VARIANTS)
SCALES = (.008, .01, .012)
BUCKETS = ("stable_range", "stable_uptrend", "stable_downtrend", "stable_uncertain",
           "A_recovered", "A_regressed", "B_only_recovered", "B_regressed")
FIELDS = ("pivots", "cycles", "structures", "events")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def rows_file(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(encoded(row) + "\n")


def quantiles(values):
    if not values:
        return None
    import numpy as np
    return {str(q): float(np.quantile(values, q)) for q in (0, .5, .9, .99, 1)}


def new_engine(method, view, scale):
    if method not in METHODS:
        raise ValueError("unknown method")
    return Engine(Config(timeframe=view, reversal_log=scale)) if method == "v01" else CandidateEngine(
        CandidateConfig(timeframe=view, reversal_log=scale, geometry_variant=method))


def replay(bars, method, view, scale, check_prefix=True):
    engine = new_engine(method, view, scale)
    emitted = hashlib.sha256()
    emitted_count = 0
    for index, bar in enumerate(bars):
        events = engine.update(bar)
        if any(e["confirmation_bar"] != index for e in events):
            raise AssertionError("backdated emitted event")
        for event in events:
            emitted.update((encoded(event) + "\n").encode())
            emitted_count += 1
    final = hashlib.sha256()
    for event in engine.events:
        final.update((encoded(event) + "\n").encode())
    if emitted.digest() != final.digest() or emitted_count != len(engine.events):
        raise AssertionError("emitted event history was rewritten")
    lengths = sorted({min(1600, len(bars)), len(bars) // 2} - {0, len(bars)}) if check_prefix else []
    for length in lengths:
        prefix = new_engine(method, view, scale)
        for row in bars[:length]:
            prefix.update(row)
        for name in FIELDS:
            expected = [r for r in getattr(engine, name) if r["confirmation_bar"] < length]
            if getattr(prefix, name) != expected:
                raise AssertionError(f"{method}: {name} changed at prefix {length}")
    return engine, {"passed": True, "independent_prefix_lengths": lengths,
                    "all_emitted_events_checked": emitted_count,
                    "all_emitted_events_sha256": final.hexdigest(),
                    "exhaustive_independent_prefix_replay": False}


def keyed(engine):
    lookup = {p["pivot_id"]: p["occurrence_bar"] for p in engine.pivots}
    pairs = [((s["phase"], *(lookup[p] for p in s["pivot_ids"])), s) for s in engine.structures]
    result = dict(pairs)
    if len(result) != len(pairs):
        raise AssertionError("duplicate five-pivot structure identity")
    return result


def breakouts(engine):
    keys = {s["structure_id"]: key for key, s in keyed(engine).items()}
    pairs = [(keys[e["structure_id"]], {f: e[f] for f in (
        "confirmation_bar", "direction", "directional_relation", "confirmation_already_outside",
        "lower_log", "upper_log", "close_log", "boundary_overtook_price")})
        for e in engine.events if e["type"] == "structure_breakout"]
    result = dict(pairs)
    if len(result) != len(pairs):
        raise AssertionError("more than one first breakout for a structure")
    return result


def compare_same_input(reference, candidate):
    rk, ck = keyed(reference), keyed(candidate)
    if rk.keys() != ck.keys():
        raise AssertionError("candidate changed raw two-wave membership")
    transitions = Counter()
    for key in rk:
        r, c = rk[key], ck[key]
        transitions[f"{r['classification']}->{c['classification']}"] += 1
        for name in ("confirmation_bar", "confirmation_time", "classification_available_time", "effective_information_time"):
            if r[name] != c[name]:
                raise AssertionError(f"candidate changed {name}")
        for name in ("b", "width", "D", "E", "lower_offset", "upper_offset", "valid"):
            if r["geometry"][name] != c["geometry"][name]:
                raise AssertionError(f"candidate changed frozen geometry {name}")
    rb, cb = breakouts(reference), breakouts(candidate)
    if rb.keys() != cb.keys():
        raise AssertionError("candidate changed breakout membership")
    relations = 0
    for key in rb:
        for name in rb[key]:
            if name == "directional_relation":
                relations += rb[key][name] != cb[key][name]
            elif rb[key][name] != cb[key][name]:
                raise AssertionError(f"candidate changed geometric breakout {name}")
    return {"structure_members_and_clocks_identical": True, "geometric_breakouts_identical": True,
            "classification_transitions": dict(transitions), "directional_relation_changes": relations,
            "not_h1_or_trading_evaluation": True}


def describe(engine, prefix):
    structures = engine.structures
    return {"candidate_count": len(structures),
            "classification_counts": dict(Counter(s["classification"] for s in structures)),
            "clear_count": sum(s["classification"] != "uncertain" for s in structures),
            "invalid_count": sum(not s["geometry"]["valid"] for s in structures),
            "blocker_counts": dict(Counter(a for s in structures for a in s.get("rejection_reasons", s["attributes"]))),
            "joint_blockers": dict(Counter("|".join(sorted(s.get("rejection_reasons", s["attributes"]))) or "none"
                                          for s in structures)),
            "confirmation_delay_bars": quantiles([s["confirmation_delay_bars"] for s in structures]),
            "fit_error_of_clear": quantiles([s["geometry"]["E"] for s in structures if s["classification"] != "uncertain"]),
            "clear_counts_by_year": dict(Counter(s["confirmation_time"][:4] for s in structures if s["classification"] != "uncertain")),
            "prefix": prefix}


def perturb(bars):
    result = []
    for i, source in enumerate(bars):
        row = dict(source)
        factor = math.exp(1e-5 * math.sin(i * math.sqrt(2)))
        for field in ("open", "high", "low", "close"):
            row[field] = source[field] * factor
        result.append(row)
    return result


def perturb_compare(base, changed):
    bk, ck = keyed(base), keyed(changed)
    matched = bk.keys() & ck.keys()
    transitions = Counter(f"{bk[k]['classification']}->{ck[k]['classification']}" for k in matched)
    bb, cb = breakouts(base), breakouts(changed)
    timing = Counter()
    for key in matched:
        x, y = bb.get(key), cb.get(key)
        if x is None or y is None:
            timing["both_no_observed_breakout" if x is y else "observed_breakout_presence_changed"] += 1
        else:
            timing["same_time_and_direction" if (x["confirmation_bar"], x["direction"]) ==
                   (y["confirmation_bar"], y["direction"]) else "time_or_direction_changed"] += 1
    return {"baseline_count": len(bk), "perturbed_count": len(ck), "exact_five_pivot_matches": len(matched),
            "baseline_unmatched": len(bk) - len(matched), "perturbed_unmatched": len(ck) - len(matched),
            "classification_transitions": dict(transitions),
            "matched_classification_changes": sum(bk[k]["classification"] != ck[k]["classification"] for k in matched),
            "matched_clear_label_changes": sum(bk[k]["classification"] != ck[k]["classification"] and
                                                "uncertain" not in (bk[k]["classification"], ck[k]["classification"]) for k in matched),
            "matched_confirmation_bar_changes": sum(bk[k]["confirmation_bar"] != ck[k]["confirmation_bar"] for k in matched),
            "matched_breakout_changes": dict(timing), "matching": "strict_phase_and_five_occurrence_indices",
            "not_reference_accuracy": True}


def collect_cases(pool, engines, view, scale):
    maps = {method: keyed(engine) for method, engine in engines.items()}
    pivot_lookup = {p["pivot_id"]: p for p in engines["v01"].pivots}
    for key, s in maps["v01"].items():
        paired = {m: mapping[key] for m, mapping in maps.items()}
        v, a, b = [paired[m]["classification"] for m in METHODS]
        groups = []
        if v == a == b:
            groups.append("stable_" + v)
        if v == "uncertain" and a != "uncertain":
            groups.append("A_recovered")
        if v != "uncertain" and a == "uncertain":
            groups.append("A_regressed")
        if a == "uncertain" and b != "uncertain":
            groups.append("B_only_recovered")
        if a != "uncertain" and b == "uncertain":
            groups.append("B_regressed")
        rank = digest([20260905, view, scale, key])
        for group in groups:
            if len(pool[group]) >= 2 and rank >= pool[group][-1]["rank"]:
                continue
            start, stop = max(0, s["start_bar"] - 16), s["confirmation_bar"]
            item = {"rank": rank, "bucket": group, "view": view, "scale": scale, "key": key,
                    "structures": paired, "pivots": [pivot_lookup[x] for x in s["pivot_ids"]],
                    "bars": copy.deepcopy(engines["v01"].bars[start:stop + 1]),
                    "cutoff_bar": stop, "future_after_confirmation_included": False}
            pool[group] = sorted([*pool[group], item], key=lambda x: x["rank"])[:2]


def make_gallery(destination, pool):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    destination.mkdir(parents=True, exist_ok=True)
    cases = [case for group in BUCKETS for case in pool[group]]
    cards = []
    for i, case in enumerate(cases):
        name = f"case_{i:02d}_{case['bucket']}"
        save(destination / f"{name}.json", case)
        rows = case["bars"]
        indices = [r["bar_index"] for r in rows]
        g = case["structures"]["v01"]["geometry"]
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(indices, [r["log_close"] for r in rows], label="log(close)", linewidth=1)
        if len(rows) <= 320:
            ax.vlines(indices, [math.log(r["low"]) for r in rows], [math.log(r["high"]) for r in rows], alpha=.25,
                      label="raw high-low")
        if g["valid"]:
            ts = [x for x in indices if x >= g["origin_bar"]]
            ax.plot(ts, [g["lower_offset"] + g["b"] * (t - g["origin_bar"]) for t in ts], "--", label="frozen lower")
            ax.plot(ts, [g["upper_offset"] + g["b"] * (t - g["origin_bar"]) for t in ts], "--", label="frozen upper")
        for j, p in enumerate(case["pivots"]):
            ax.scatter([p["occurrence_bar"]], [p["log_price"]], marker="o")
            ax.annotate(str(j), (p["occurrence_bar"], p["log_price"]), xytext=(0, 8), textcoords="offset points")
        ax.axvline(case["cutoff_bar"], linestyle=":", label="classification confirmation")
        labels = " / ".join(case["structures"][m]["classification"] for m in METHODS)
        ax.set_title(f"{case['bucket']} | {case['view']} | {case['scale']}\nv01 / A / B: {labels}")
        ax.set_xlabel("Original bar ordinal; no data after confirmation")
        ax.set_ylabel("Log price")
        ax.legend(loc="best", fontsize=8)
        fig.tight_layout()
        fig.savefig(destination / f"{name}.svg")
        plt.close(fig)
        cards.append(f'<h2>{html.escape(name)}</h2><img width="100%" src="{name}.svg"><p><a href="{name}.json">Complete case JSON</a></p>')
        if i % 2 == 0:
            stride = max(1, math.ceil(len(rows) / 160))
            sampled = rows[::stride]
            if sampled[-1] != rows[-1]:
                sampled.append(rows[-1])
            compact = {"case_name": name, "view": case["view"], "scale": case["scale"], "key": case["key"],
                       "cutoff": case["cutoff_bar"], "plot_stride": stride, "raw_case_rows": len(rows),
                       "line": [[r["bar_index"], round(r["log_close"], 8)] for r in sampled],
                       "points": [[p["occurrence_bar"], p["log_price"]] for p in case["pivots"]],
                       "geometry": {k: g.get(k) for k in ("origin_bar", "b", "lower_offset", "upper_offset", "D", "E")},
                       "methods": {m: {"label": s["classification"], "blockers": s.get("rejection_reasons", s["attributes"]),
                                       "raw_ratio": s["geometry"].get("cycle_amplitude_ratio"),
                                       "detrended_ratio": s["geometry"].get("cycle_detrended_width_ratio")}
                                   for m, s in case["structures"].items()}}
            print("V02_CASE " + encoded(compact), flush=True)
    (destination / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>v0.2 audit</title>'
        '<h1>Deterministically selected H0 development cases</h1><p>Not independent accuracy labels. '
        'Plots stop at confirmation. Full case JSON is retained. Shared bounds are identical across methods.</p>' + "\n".join(cards))
    return {"case_count": len(cases), "bucket_counts": {g: len(pool[g]) for g in BUCKETS},
            "selection": "two_minimum_sha256_keys_per_bucket_over_all_views_and_scales"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "cloud_results/two_wave_candidate_v02")
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit("output must be new or empty; preserve previous runs")
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    source_paths = [Path(__file__), ROOT / "docs/research/two_wave_autonomous_iteration_v02.md",
                    ROOT / "docs/research/two_wave_recognition_spec_v0_1.md",
                    ROOT / "docs/research/two_wave_evaluation_protocol_v0_1.md",
                    *sorted((ROOT / "src/factor_lab/visual_structure/two_wave").glob("*.py"))]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    receipt = {"checkout_commit": commit, "github_sha": os.environ.get("GITHUB_SHA"),
               "github_run_id": os.environ.get("GITHUB_RUN_ID"), "python": platform.python_version(),
               "source_sha256": hashes, "data_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
               "methods": METHODS, "scales": SCALES, "data_role": "development_material",
               "independent_reference_count": 0, "h1_opened": False, "pnl_computed": False,
               "production_authority": False, "ready_for_user_review": False}
    save(out / "run_manifest.json", receipt)
    all_runs, sensitivity, data_audits = [], [], []
    pool = defaultdict(list)
    for product in sorted(manifest["products"], key=lambda p: p["path"]):
        path = ROOT / product["path"]
        bars, audit = load_development_bars(path, manifest_path)
        data_audits.append(audit)
        view = audit["view_id"]
        for scale in SCALES:
            engines, summaries = {}, {}
            folder = out / view / f"reversal_{scale:g}"
            for method in METHODS:
                engine, prefix = replay(bars, method, view, scale)
                engines[method] = engine
                summaries[method] = describe(engine, prefix)
                for field in FIELDS:
                    rows_file(folder / method / f"{field}.jsonl", getattr(engine, field))
                save(folder / method / "config.json", engine.config.to_dict())
            comparisons = {method: compare_same_input(engines["v01"], engines[method]) for method in VARIANTS}
            group = {"view": view, "scale": scale, "source_rows": len(bars), "methods": summaries, "comparisons": comparisons}
            all_runs.append(group)
            save(folder / "summary.json", group)
            collect_cases(pool, engines, view, scale)
            print("V02_GROUP " + encoded({"view": view, "scale": scale, "counts": {
                m: {"n": s["candidate_count"], "clear": s["clear_count"], "classes": s["classification_counts"]}
                for m, s in summaries.items()}, "prefix_passed": True, "alignment_passed": True}), flush=True)
            if scale == .01:
                altered = perturb(bars)
                result = {"view": view, "scale": scale, "methods": {}}
                for method in METHODS:
                    modified, check = replay(altered, method, view, scale, check_prefix=False)
                    result["methods"][method] = perturb_compare(engines[method], modified)
                    save(folder / method / "perturbation.json", result["methods"][method])
                    del modified
                sensitivity.append(result)
                print("V02_PERTURB " + encoded(result), flush=True)
    totals = {}
    for method in METHODS:
        counts, blockers, transitions = Counter(), Counter(), Counter()
        for group in all_runs:
            counts.update(group["methods"][method]["classification_counts"])
            blockers.update(group["methods"][method]["blocker_counts"])
            if method != "v01":
                transitions.update(group["comparisons"][method]["classification_transitions"])
        n = sum(counts.values())
        totals[method] = {"candidate_count": n, "clear_count": n - counts["uncertain"],
                          "clear_fraction": (n - counts["uncertain"]) / n if n else None,
                          "classification_counts": dict(counts), "blocker_counts": dict(blockers),
                          "transitions_from_v01": dict(transitions)}
    save(out / "precheck_totals.json", totals)
    expected = {"range": 816, "uptrend": 620, "downtrend": 751, "uncertain": 41687}
    if totals["v01"]["classification_counts"] != expected:
        raise AssertionError("v0.1 all-product baseline differs from the previous verified run")
    gallery = make_gallery(out / "gallery", pool)
    changed_sources = [name for name, expected_hash in hashes.items()
                       if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected_hash]
    changed_data = [p["path"] for p in manifest["products"] if hashlib.sha256((ROOT / p["path"]).read_bytes()).hexdigest() != p["sha256"]]
    if changed_sources or changed_data:
        raise AssertionError(f"source/data changed: {changed_sources}, {changed_data}")
    compact = {"status": "autonomous_candidate_audit_completed_not_user_accepted",
               "checkout_commit": commit, "views": len(data_audits), "source_rows": sum(a["rows"] for a in data_audits),
               "view_scale_groups": len(all_runs), "method_replays": len(all_runs) * len(METHODS),
               "prefix_and_alignment_groups_passed": len(all_runs), "all_source_and_data_hashes_unchanged": True,
               "baseline_reproduced": True, "totals": totals, "gallery": gallery,
               "independent_reference_count": 0, "ready_for_user_review": False,
               "h1_opened": False, "pnl_computed": False, "fresh_oos": False}
    save(out / "summary.json", compact)
    save(out / "per_view_scale.json", all_runs)
    save(out / "perturbation_summary.json", sensitivity)
    save(out / "data_audits.json", data_audits)
    save(out / "run_manifest.json", {**receipt, "completed": True, "source_and_data_unchanged": True})
    print("V02_SUMMARY " + encoded(compact), flush=True)


if __name__ == "__main__":
    main()
