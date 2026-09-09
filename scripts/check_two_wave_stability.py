#!/usr/bin/env python3
"""Fixed H0 sensitivity checks on manifest-backed bars; never parameter selection."""

from __future__ import annotations

import argparse
import bisect
import glob
import hashlib
import importlib.metadata
import json
import platform
import sys
from collections import Counter, defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave import Config, run_bars  # noqa: E402
from factor_lab.visual_structure.two_wave.data import load_development_bars  # noqa: E402

SEED = 20260905
LOG_PERTURBATION_AMPLITUDE = 1e-5
TOLERANCE_BARS = 2
CLASSES = ("range", "uptrend", "downtrend", "uncertain")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distribution(values) -> dict:
    values = [float(value) for value in values if value is not None]
    return {
        "n": len(values),
        "quantiles": {str(q): float(np.quantile(values, q)) for q in (0, 0.5, 0.9, 0.95, 1)} if values else None,
        "mean": float(np.mean(values)) if values else None,
    }


def elapsed_seconds(later: str, earlier: str) -> float:
    return (datetime.fromisoformat(later) - datetime.fromisoformat(earlier)).total_seconds()


def objects(engine, level: str) -> list[dict]:
    pivots = {pivot["pivot_id"]: pivot for pivot in engine.pivots}
    source = {"pivot": engine.pivots, "cycle": engine.cycles, "structure": engine.structures}[level]
    result = []
    for item in source:
        if level == "pivot" and item["left_censored"]:
            continue
        result.append(
            {
                "identity": item[f"{level}_id"],
                "phase": item["kind"] if level == "pivot" else item["phase"],
                "indices": [item["occurrence_bar"]]
                if level == "pivot"
                else [pivots[pivot_id]["occurrence_bar"] for pivot_id in item["pivot_ids"]],
                "record": item,
            }
        )
    return result


def match_objects(base: list[dict], comparison: list[dict]) -> list[tuple[int, int, int]]:
    """Max cardinality, then minimum total extrema distance, independent of class.

    First-extremum buckets avoid a dense all-history matrix. Each connected
    component gets an exact rectangular assignment with explicit unmatched
    columns. Identity sorting gives deterministic solver input and tie behavior;
    identity equality is never required, including in the same-config perturbation.
    """
    ordered = defaultdict(list)
    for j, item in enumerate(comparison):
        ordered[item["phase"]].append((item["indices"][0], j))
    for entries in ordered.values():
        entries.sort()
    starts = {phase: [entry[0] for entry in entries] for phase, entries in ordered.items()}
    edges, reverse = defaultdict(dict), defaultdict(set)
    for i, item in enumerate(base):
        entries = ordered[item["phase"]]
        start_values = starts.get(item["phase"], [])
        left = bisect.bisect_left(start_values, item["indices"][0] - TOLERANCE_BARS)
        right = bisect.bisect_right(start_values, item["indices"][0] + TOLERANCE_BARS)
        for _, j in entries[left:right]:
            other = comparison[j]
            if len(item["indices"]) != len(other["indices"]):
                continue
            distances = [abs(a - b) for a, b in zip(item["indices"], other["indices"], strict=True)]
            if max(distances) <= TOLERANCE_BARS:
                edges[i][j] = sum(distances)
                reverse[j].add(i)
    seen, result = set(), []
    for root in sorted(edges, key=lambda index: base[index]["identity"]):
        if root in seen:
            continue
        left_nodes, right_nodes, queue = set(), set(), deque([root])
        while queue:
            i = queue.popleft()
            if i in left_nodes:
                continue
            left_nodes.add(i)
            seen.add(i)
            for j in edges[i]:
                right_nodes.add(j)
                queue.extend(reverse[j] - left_nodes)
        left_nodes = sorted(left_nodes, key=lambda index: base[index]["identity"])
        right_nodes = sorted(right_nodes, key=lambda index: comparison[index]["identity"])
        column_of = {index: column for column, index in enumerate(right_nodes)}
        # One additional match outweighs the total possible extrema distance.
        penalty = (len(left_nodes) + 1) * (max(len(base[i]["indices"]) for i in left_nodes) * TOLERANCE_BARS + 1)
        cost = np.full((len(left_nodes), len(right_nodes) + len(left_nodes)), penalty, dtype=np.int64)
        cost[:, : len(right_nodes)] = penalty * 2
        for row, i in enumerate(left_nodes):
            for j, distance in edges[i].items():
                cost[row, column_of[j]] = distance
        rows, cols = linear_sum_assignment(cost)
        for row, col in zip(rows, cols, strict=True):
            if col < len(right_nodes) and cost[row, col] < penalty:
                result.append((left_nodes[row], right_nodes[col], int(cost[row, col])))
    return sorted(result)


def profile(engine) -> dict:
    structures = engine.structures
    counts = Counter(item["classification"] for item in structures)
    return {
        "config": engine.config.to_dict(),
        "config_hash": engine.config.config_hash,
        "scale_id": engine.config.scale_id,
        "bars": len(engine.bars),
        "pivots": len(engine.pivots),
        "left_censored_pivots": sum(p["left_censored"] for p in engine.pivots),
        "cycles": len(engine.cycles),
        "structures": len(structures),
        "events": len(engine.events),
        "classification_counts": {name: counts[name] for name in CLASSES},
        "classification_coverage": (len(structures) - counts["uncertain"]) / len(structures) if structures else None,
        "uncertain_fraction": counts["uncertain"] / len(structures) if structures else None,
        "drift_D": distribution(s["geometry"]["D"] for s in structures),
        "pivot_confirmation_delay_bars": distribution(p["confirmation_delay_bars"] for p in engine.pivots if not p["left_censored"]),
        "structure_confirmation_delay_bars": distribution(s["confirmation_delay_bars"] for s in structures),
        "structure_confirmation_delay_elapsed_seconds": distribution(
            elapsed_seconds(s["confirmation_time"], s["end_time"]) for s in structures
        ),
        "structure_extra_availability_wait_seconds": distribution(
            elapsed_seconds(s["information_available_time"], s["confirmation_time"]) for s in structures
        ),
    }


def compare(base_engine, comparison_engine, *, kind: str) -> dict:
    result = {
        "kind": kind,
        "base_reversal_log": base_engine.config.reversal_log,
        "comparison_reversal_log": comparison_engine.config.reversal_log,
        "base_scale_id": base_engine.config.scale_id,
        "comparison_scale_id": comparison_engine.config.scale_id,
        "scale_changed": base_engine.config.scale_id != comparison_engine.config.scale_id,
        "not_independent_ground_truth": True,
        "matching_role": "descriptive_cross_scale_sensitivity"
        if kind == "threshold_sensitivity"
        else "same_scale_development_perturbation",
    }
    for level in ("pivot", "cycle", "structure"):
        base, other = objects(base_engine, level), objects(comparison_engine, level)
        matches = match_objects(base, other)
        pairs = [(base[i], other[j]) for i, j, _ in matches]
        result[level] = {
            "base_count": len(base),
            "comparison_count": len(other),
            "matched_count": len(matches),
            "unmatched_base_count": len(base) - len(matches),
            "unmatched_comparison_count": len(other) - len(matches),
            "base_match_coverage": len(matches) / len(base) if base else None,
            "comparison_match_coverage": len(matches) / len(other) if other else None,
            "matched_total_extrema_bar_distance": sum(distance for _, _, distance in matches),
            "confirmation_shift_bars": distribution(b["record"]["confirmation_bar"] - a["record"]["confirmation_bar"] for a, b in pairs),
            "confirmation_shift_elapsed_seconds": distribution(
                elapsed_seconds(b["record"]["confirmation_time"], a["record"]["confirmation_time"]) for a, b in pairs
            ),
            "confirmation_changed_count": sum(a["record"]["confirmation_bar"] != b["record"]["confirmation_bar"] for a, b in pairs),
            "confirmation_delay_change_bars": distribution(
                b["record"]["confirmation_delay_bars"] - a["record"]["confirmation_delay_bars"] for a, b in pairs
            ),
        }
        if level != "structure":
            continue
        transition = {name: {other_name: 0 for other_name in CLASSES} for name in CLASSES}
        drift_changes, agreement, clear_pairs, clear_agreement = [], 0, 0, 0
        for a, b in pairs:
            first, second = a["record"], b["record"]
            transition[first["classification"]][second["classification"]] += 1
            same = first["classification"] == second["classification"]
            agreement += same
            if first["classification"] != "uncertain" and second["classification"] != "uncertain":
                clear_pairs += 1
                clear_agreement += same
            if first["geometry"]["D"] is not None and second["geometry"]["D"] is not None:
                drift_changes.append(second["geometry"]["D"] - first["geometry"]["D"])
        result[level].update(
            {
                "classification_transition_base_rows_comparison_columns": transition,
                "classification_agreement_count": agreement,
                "classification_change_count": len(pairs) - agreement,
                "classification_agreement_fraction_among_matched": agreement / len(pairs) if pairs else None,
                "both_clearly_classified_count": clear_pairs,
                "classification_agreement_fraction_among_both_clear": clear_agreement / clear_pairs if clear_pairs else None,
                "matched_and_clearly_classified_comparison_fraction_of_all_base": sum(
                    b["record"]["classification"] != "uncertain" for _, b in pairs
                )
                / len(base)
                if base
                else None,
                "drift_D_change": distribution(drift_changes),
                "absolute_drift_D_change": distribution(abs(value) for value in drift_changes),
            }
        )
        base_breakouts = {e["structure_id"]: e for e in base_engine.events if e["type"] == "structure_breakout"}
        other_breakouts = {e["structure_id"]: e for e in comparison_engine.events if e["type"] == "structure_breakout"}
        availability_patterns, direction_changes, confirmation_changes, event_shifts = Counter(), 0, 0, []
        for a, b in pairs:
            first, second = base_breakouts.get(a["identity"]), other_breakouts.get(b["identity"])
            availability_patterns[f"base_{'observed' if first else 'unobserved'}_comparison_{'observed' if second else 'unobserved'}"] += 1
            if first and second:
                direction_changes += first["direction"] != second["direction"]
                confirmation_changes += first["confirmation_bar"] != second["confirmation_bar"]
                event_shifts.append(second["confirmation_bar"] - first["confirmation_bar"])
        result["matched_structure_first_geometry_breakout_events"] = {
            "availability_patterns": dict(availability_patterns),
            "direction_change_count": direction_changes,
            "confirmation_changed_count_when_both_observed": confirmation_changes,
            "confirmation_shift_bars_when_both_observed": distribution(event_shifts),
            "unobserved_note": "No first breakout in the observed prefix or invalid geometry; no future outcome imputed.",
            "no_hazard_or_third_wave_analysis": True,
        }
    return result


def self_checks() -> dict:
    def item(identity, index):
        return {"identity": identity, "phase": "low", "indices": [index]}

    base = [item("base0", 0), item("base1", 2)]
    other = [item("other0", 2), item("other1", 4)]
    assert match_objects(base, other) == [(0, 0, 2), (1, 1, 2)]
    assert match_objects(base, base) == [(0, 0, 0), (1, 1, 0)]
    incompatible = [{"identity": "high0", "phase": "high", "indices": [0]}]
    assert match_objects(base, incompatible) == []
    return {"maximum_cardinality_adversarial_case": True, "minimum_distance_identity_case": True, "phase_separation": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", nargs="+", default=["data/development/*.parquet"])
    parser.add_argument("--output", default="cloud_results/two_wave_stability")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if not output.is_relative_to(ROOT / "cloud_results"):
        parser.error("--output must be inside this repository's cloud_results/")
    paths = sorted({Path(path).resolve() for expression in args.data for path in glob.glob(expression)})
    if not paths:
        parser.error("--data matched no local manifest-backed files")
    protocol = ROOT / "docs/research/two_wave_evaluation_protocol_v0_1.md"
    spec = ROOT / "docs/research/two_wave_recognition_spec_v0_1.md"
    manifest_path = ROOT / "data/manifest.json"
    sources = [Path(__file__).resolve()] + sorted((ROOT / "src/factor_lab/visual_structure/two_wave").glob("*.py"))
    frozen_hashes = {str(path.relative_to(ROOT)): digest(path) for path in [protocol, spec, manifest_path, *sources]}
    report = {
        "schema_version": "two_wave_stability@0.1",
        "started_at": datetime.now(UTC).isoformat(),
        "protocol_sha256": digest(protocol),
        "source_and_definition_sha256": frozen_hashes,
        "python": platform.python_version(),
        "dependencies": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "pandas", "pyarrow")},
        "seed": SEED,
        "perturbation_amplitude_log": LOG_PERTURBATION_AMPLITUDE,
        "perturbation_method": (
            "Per product reset numpy.default_rng(20260905); draw epsilon_t iid Uniform[-1e-5,1e-5]; "
            "multiply all OHLC of bar t by exp(epsilon_t)."
        ),
        "perturbation_baseline_reversal_log": 0.01,
        "threshold_comparisons": [0.008, 0.012],
        "structure_matching": (
            "same phase, five ordered extrema each within +/-2 bars; maximum cardinality then minimum "
            "sum of absolute bar distances; deterministic ID-sorted assignment input"
        ),
        "cross_threshold_matching_exception": (
            "Scales intentionally differ; this descriptive sensitivity comparison is not protocol "
            "ground-truth matching and is not accuracy."
        ),
        "clock_notice": "Bar-order replay preserves source available_at; historical intraday PIT and execution remain unproven.",
        "status": "morphology_replication_not_yet_accepted",
        "independent_label_count": 0,
        "accuracy": None,
        "parameter_selection_authority": False,
        "h1_opened": False,
        "pnl_computed": False,
        "fresh_oos": False,
        "production_authority": False,
        "statistical_uncertainty": (
            "Descriptive finite-input changes only; no confidence intervals computed; overlapping "
            "structures and views are not independent trials."
        ),
        "synthetic_market_assets_written": False,
        "self_checks": self_checks(),
        "views": [],
        "failures": [],
    }
    output.mkdir(parents=True, exist_ok=True)
    for path in paths:
        try:
            bars, audit = load_development_bars(path, manifest_path)
            base_config = Config(timeframe=path.stem, reversal_log=0.01)
            baseline = run_bars(bars, base_config)
            view = {"source_audit": audit, "profiles": {"baseline": profile(baseline)}, "comparisons": []}
            for threshold in (0.008, 0.012):
                other = run_bars(bars, Config(timeframe=path.stem, reversal_log=threshold))
                view["profiles"][f"threshold_{threshold:g}"] = profile(other)
                view["comparisons"].append(compare(baseline, other, kind="threshold_sensitivity"))
                del other
            epsilon = np.random.default_rng(SEED).uniform(-LOG_PERTURBATION_AMPLITUDE, LOG_PERTURBATION_AMPLITUDE, len(bars))
            perturbed = [
                {**bar, **{field: bar[field] * float(np.exp(shift)) for field in ("open", "high", "low", "close")}}
                for bar, shift in zip(bars, epsilon, strict=True)
            ]
            other = run_bars(perturbed, base_config)
            view["profiles"]["synthetic_log_price_perturbation"] = profile(other)
            view["perturbation_draws"] = {
                "n": len(epsilon),
                "minimum": float(epsilon.min()),
                "maximum": float(epsilon.max()),
                "float64_little_endian_sha256": hashlib.sha256(epsilon.astype("<f8").tobytes()).hexdigest(),
            }
            view["comparisons"].append(compare(baseline, other, kind="synthetic_log_price_perturbation"))
            report["views"].append(view)
            print(
                json.dumps(
                    {
                        "view": path.stem,
                        "bars": len(bars),
                        "baseline_structures": len(baseline.structures),
                        "perturbed_matched_structures": view["comparisons"][-1]["structure"]["matched_count"],
                    }
                ),
                flush=True,
            )
            del other, baseline, bars, perturbed
        except Exception as exc:
            failure = {"path": str(path), "error_type": type(exc).__name__, "error": str(exc)}
            report["failures"].append(failure)
            print(json.dumps(failure), file=sys.stderr, flush=True)
    changed = [relative for relative, value in frozen_hashes.items() if digest(ROOT / relative) != value]
    if changed:
        report["failures"].append({"error": "source_or_definition_changed_during_run", "paths": changed})
    report.update(
        {
            "view_count": len(report["views"]),
            "configuration_runs": len(report["views"]) * 4,
            "processed_source_rows": sum(v["source_audit"]["rows"] for v in report["views"]),
            "completed_at": datetime.now(UTC).isoformat(),
        }
    )
    (output / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
