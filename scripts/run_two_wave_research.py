#!/usr/bin/env python3
"""Reproduce bounded H0 morphology research; no H1 inference or trading output."""

from __future__ import annotations

import argparse
import copy
import glob
import hashlib
import importlib.metadata
import json
import platform
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave import Config, Engine, run_bars  # noqa: E402
from factor_lab.visual_structure.two_wave.annotations import annotation_template, evaluate_annotations  # noqa: E402
from factor_lab.visual_structure.two_wave.data import load_development_bars  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def write_jsonl(path: Path, values) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")


def quantiles(values: list[int | float]) -> dict | None:
    if not values:
        return None
    import numpy as np

    return {str(q): float(np.quantile(values, q)) for q in (0, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1)}


def selected_windows(bars: list[dict], config: Config) -> list[dict]:
    """Two random non-overlapping 256-bar cores per view/year, before predictions."""
    import numpy as np

    years: dict[str, list[int]] = defaultdict(list)
    for index, bar in enumerate(bars):
        years[bar["trading_day"][:4]].append(index)
    result = []
    for year, indices in sorted(years.items()):
        # Same windows across scales. The seed is fixed; the view/year hash just
        # makes the draw independent of invocation order and selected products.
        seed_material = f"20260905/{config.timeframe}/{year}".encode()
        seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "big")
        rng = np.random.default_rng(seed)
        if len(indices) < 512:
            cores = [(indices[0], indices[-1])]
            exception = "fewer_than_512_rows_use_full_year_available_interval"
        else:
            starts = np.arange(len(indices) - 255)
            eligible = starts[(starts >= 256) | (starts + 512 <= len(indices))]
            first = int(rng.choice(eligible))
            remaining = starts[(starts + 256 <= first) | (starts >= first + 256)]
            second = int(rng.choice(remaining))
            cores = [(indices[0] + start, indices[0] + start + 255) for start in sorted((first, second))]
            exception = None
        for start, end in cores:
            result.append(
                {
                    "window_id": f"{config.config_hash}_{year}_{start}",
                    "config_id": config.config_hash,
                    "timeframe": config.timeframe,
                    "scale_id": config.scale_id,
                    "start_index": start,
                    "end_index": end,
                    "visible_cutoff": end,
                    "selection_rule": "two_nonoverlapping_256_bar_cores_per_product_year",
                    "seed": 20260905,
                    "seed_derivation": "sha256(seed/view/year) first 8 bytes big-endian",
                    "sampling_exception": exception,
                    "score_core_start_index": start,
                    "score_core_end_index": end,
                    "context_before_bars": 0,
                    "context_after_bars": 0,
                    "fully_reviewed": False,
                    "notice": "Year is a descriptive sampling stratum, never a runtime state. Labels remain empty.",
                }
            )
    return result


def verify_prefixes(bars: list[dict], config: Config, stream_export: dict, emitted: list[dict]) -> dict:
    """Check all emitted event prefixes and independently replay fixed checkpoints."""
    batch = run_bars(bars, config).export()
    checks = sorted({min(len(bars), k) for k in (1, 2, 5, 10, 25, 50, 100, 200, 400, 800, 1600, len(bars) // 2, len(bars)) if k > 0})
    errors = []
    if stream_export != batch:
        errors.append("stream_export_differs_from_batch_export")
    if emitted != batch["events"]:
        errors.append("new_events_emitted_at_prefixes_differ_from_final_confirmed_event_history")
    if any(second["confirmation_bar"] < first["confirmation_bar"] for first, second in zip(emitted, emitted[1:], strict=False)):
        errors.append("event_confirmation_order_invalid")
    for size in checks:
        prefix = batch if size == len(bars) else run_bars(bars[:size], config).export()
        for key in ("pivots", "cycles", "structures", "events"):
            expected = [item for item in batch[key] if item["confirmation_bar"] < size]
            if prefix[key] != expected:
                errors.append(f"{key}_rewritten_at_prefix_{size}")
    return {
        "passed": not errors,
        "stream_batch_export_equal": stream_export == batch,
        "all_emitted_event_prefixes_match_final_history": emitted == batch["events"],
        "event_prefixes_observed": len(bars),
        "confirmed_events_compared": len(emitted),
        "independently_reexecuted_prefix_lengths": checks,
        "exhaustive_independent_reexecution_of_every_prefix": False,
        "failures": errors,
    }


def describe(export: dict, prefix: dict, bars: list[dict]) -> dict:
    structures, pivots = export["structures"], export["pivots"]
    counts = Counter(item["classification"] for item in structures)
    total = len(structures)
    years = {}
    for year in sorted({bar["trading_day"][:4] for bar in bars}):
        group = [s for s in structures if s["confirmation_time"][:4] == year]
        classified = sum(s["classification"] != "uncertain" for s in group)
        years[year] = {
            "bar_count": sum(bar["trading_day"].startswith(year) for bar in bars),
            "structure_count": len(group),
            "classification_counts": dict(Counter(s["classification"] for s in group)),
            "classification_coverage_among_structures": classified / len(group) if group else None,
        }

    def seconds_between(items, later, earlier):
        return quantiles([(datetime.fromisoformat(item[later]) - datetime.fromisoformat(item[earlier])).total_seconds() for item in items])

    confirmed_pivots = [pivot for pivot in pivots if not pivot["left_censored"]]
    confirmation_breakouts = [
        event for event in export["events"] if event["type"] == "structure_breakout" and event["confirmation_already_outside"]
    ]
    return {
        "config": export["config"],
        "config_hash": export["config_hash"],
        "scale_id": export["scale_id"],
        "bars": len(bars),
        "pivots": len(pivots),
        "left_censored_pivots": sum(p["left_censored"] for p in pivots),
        "cycles": len(export["cycles"]),
        "structures": total,
        "events": len(export["events"]),
        "classification_counts": {label: counts[label] for label in ("range", "uptrend", "downtrend", "uncertain")},
        "rejection_attribute_counts_nonexclusive": dict(
            Counter(
                attribute for structure in structures if structure["classification"] == "uncertain" for attribute in structure["attributes"]
            )
        ),
        "classification_coverage_among_structures": (total - counts["uncertain"]) / total if total else None,
        "rejection_fraction_among_structures": counts["uncertain"] / total if total else None,
        "no_complete_two_wave_structure": total == 0,
        "invalid_geometry_structures": sum(not s["geometry"]["valid"] for s in structures),
        "pivot_confirmation_delay_bars_quantiles": quantiles([p["confirmation_delay_bars"] for p in pivots if not p["left_censored"]]),
        "structure_confirmation_delay_bars_quantiles": quantiles([s["confirmation_delay_bars"] for s in structures]),
        "pivot_confirmation_delay_seconds_quantiles": seconds_between(confirmed_pivots, "confirmation_time", "occurrence_time"),
        "structure_confirmation_delay_seconds_quantiles": seconds_between(structures, "confirmation_time", "end_time"),
        "pivot_additional_information_wait_seconds_quantiles": seconds_between(
            confirmed_pivots, "information_available_time", "confirmation_time"
        ),
        "structure_additional_information_wait_seconds_quantiles": seconds_between(
            structures, "information_available_time", "confirmation_time"
        ),
        "nominal_channel_close_coverage_quantiles": quantiles(
            [s["geometry"]["nominal_coverage"] for s in structures if s["geometry"].get("nominal_coverage") is not None]
        ),
        "frozen_envelope_close_coverage_quantiles": quantiles(
            [s["geometry"]["envelope_coverage"] for s in structures if s["geometry"].get("envelope_coverage") is not None]
        ),
        "already_outside_at_confirmation_count": len(confirmation_breakouts),
        "already_outside_at_confirmation_fraction": len(confirmation_breakouts) / total if total else None,
        "year_descriptions_not_runtime_rules": years,
        "prefix_invariance": prefix,
        "morphology_evaluation": evaluate_annotations(export, None),
        "accuracy": None,
        "independent_label_count": 0,
        "status": "morphology_replication_not_yet_accepted",
        "h1_opened": False,
        "pnl_computed": False,
        "selection_authority": False,
        "production_authority": False,
        "interpretation": "Overlapping structures and phases are descriptive, correlated candidates, not independent trials.",
        "unexecuted_protocol_components": [
            "independent_offline_and_online_human_reference_evaluation",
            "human_adjudication_and_complete_reviewed_windows",
            "label_based_accuracy_confusion_matrix_recall_precision_f1",
            "block_bootstrap_confidence_intervals_without_independent_labels",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", nargs="+", default=["data/development/*.parquet"])
    parser.add_argument("--output", default="cloud_results/two_wave_h0")
    parser.add_argument("--reversal-logs", default=".008,.01,.012")
    parser.add_argument("--max-bars", type=int)
    parser.add_argument("--replay-bars", type=int, default=1200)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if not output.is_relative_to(ROOT / "cloud_results"):
        parser.error("--output must be inside this repository's cloud_results/")
    if args.replay_bars <= 0 or (args.max_bars is not None and args.max_bars <= 0):
        parser.error("--replay-bars and --max-bars must be positive")
    try:
        scales = [float(item) for item in args.reversal_logs.split(",")]
        for threshold in scales:
            Config(reversal_log=threshold)
        if len(set(scales)) != len(scales):
            raise ValueError("duplicate scales")
    except ValueError as exc:
        parser.error(str(exc))
    paths = sorted({Path(path).resolve() for expression in args.data for path in glob.glob(expression)})
    if not paths:
        parser.error("--data matched no local manifest-backed files")
    # Freeze the human-readable definitions and run parameters before recognition.
    documents = [ROOT / "docs/research/two_wave_recognition_spec_v0_1.md", ROOT / "docs/research/two_wave_evaluation_protocol_v0_1.md"]
    document_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in documents}
    manifest_path = ROOT / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    run_manifest = {
        "schema_version": "two_wave_h0_run@0.1",
        "started_at": datetime.now(UTC).isoformat(),
        "source_snapshot_commit": "9c1f588a51c1db10a687f2df52719b5ecbed4d03",
        "preregistration_commit": "faeb8c44cc1cc1c8a3a2abed3eee1174f168335e",
        "definition_sha256": document_hashes,
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [Path(__file__), *sorted((ROOT / "src/factor_lab/visual_structure/two_wave").glob("*.py"))]
        },
        "data_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "reversal_logs": scales,
        "max_bars": args.max_bars,
        "replay_bars": args.replay_bars,
        "input_products": [path.name for path in paths],
        "manifest_products_not_selected": [
            p["path"] for p in manifest["products"] if Path(p["path"]).name not in {path.name for path in paths}
        ],
        "manifest_products_missing_locally": [p["path"] for p in manifest["products"] if not (ROOT / p["path"]).is_file()],
        "python": platform.python_version(),
        "python_supported": sys.version_info[:2] == (3, 11),
        "dependencies": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "pyarrow", "pytest")},
        "independent_labels": None,
        "h1_opened": False,
        "pnl_computed": False,
        "fresh_oos": False,
        "production_authority": False,
    }
    write_json(output / "run_manifest.json", run_manifest)
    summaries, audits, replay_runs, failures = [], [], [], []
    for path in paths:
        try:
            bars, audit = load_development_bars(path, manifest_path, max_bars=args.max_bars)
            audits.append(audit)
            view_dir = output / audit["view_id"]
            write_json(view_dir / "data_audit.json", audit)
            for threshold in scales:
                config = Config(timeframe=audit["view_id"], reversal_log=threshold)
                destination = view_dir / f"reversal_{threshold:g}"
                windows = selected_windows(bars, config)
                write_json(destination / "preselected_review_windows.json", windows)
                engine, emitted, snapshots = Engine(config), [], []
                replay_export = None
                replay_size = min(len(bars), args.replay_bars)
                first_structure_confirmation = None
                bars_without_confirmed_two_wave_structure = 0
                for index, bar in enumerate(bars):
                    new_events = engine.update(bar)
                    if any(event["confirmation_bar"] != index for event in new_events):
                        raise AssertionError("new event carries a backdated confirmation index")
                    emitted.extend(copy.deepcopy(new_events))
                    if first_structure_confirmation is None:
                        if any(event["type"] == "structure_confirmed" for event in new_events):
                            first_structure_confirmation = index
                        else:
                            bars_without_confirmed_two_wave_structure += 1
                    if index < replay_size:
                        snapshot = engine.snapshot()
                        # The replay derives historical structure states from versioned events.
                        snapshots.append({key: value for key, value in snapshot.items() if key != "structure_states"})
                    if index + 1 == replay_size:
                        replay_export = engine.export()
                export = engine.export()
                prefix = verify_prefixes(bars, config, export, emitted)
                summary = describe(export, prefix, bars)
                summary["initial_bars_without_confirmed_two_wave_structure"] = bars_without_confirmed_two_wave_structure
                summary["first_structure_confirmation_bar"] = first_structure_confirmation
                summaries.append(summary)
                write_json(destination / "summary.json", summary)
                write_json(
                    destination / "config.json",
                    {
                        "config": export["config"],
                        "config_hash": export["config_hash"],
                        "scale_id": export["scale_id"],
                    },
                )
                write_json(destination / "final_state.json", export["state"])
                for key in ("pivots", "cycles", "structures", "events"):
                    write_jsonl(destination / f"{key}.jsonl", export[key])
                write_json(destination / "annotations_empty.json", annotation_template(export))
                replay_runs.append(
                    {
                        "name": f"{audit['view_id']} / reversal_log={threshold:g}",
                        "bars": bars[:replay_size],
                        "export": replay_export,
                        "snapshots": snapshots,
                    }
                )
                print(
                    json.dumps(
                        {
                            "view": audit["view_id"],
                            "reversal_log": threshold,
                            "bars": len(bars),
                            "structures": summary["structures"],
                            "prefix_passed": prefix["passed"],
                        }
                    ),
                    flush=True,
                )
                if not prefix["passed"]:
                    failures.append({"view": audit["view_id"], "reversal_log": threshold, "errors": prefix["failures"]})
        except Exception as exc:
            failures.append({"path": str(path), "error_type": type(exc).__name__, "error": str(exc)})
            print(json.dumps(failures[-1]), file=sys.stderr, flush=True)
    if replay_runs:
        from factor_lab.visual_structure.two_wave.replay import write_replay_bundle

        write_replay_bundle(output / "replay.html", replay_runs)
    changed_files = [
        name
        for name, expected in {**run_manifest["source_sha256"], **document_hashes}.items()
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected
    ]
    if changed_files:
        failures.append({"error": "source_or_frozen_definition_changed_during_run", "paths": changed_files})
    run_manifest["source_and_definition_unchanged_during_run"] = not changed_files
    run_manifest["finished_at"] = datetime.now(UTC).isoformat()
    write_json(output / "run_manifest.json", run_manifest)
    write_json(output / "data_audit.json", audits)
    write_json(
        output / "summary.json",
        {
            "status": "morphology_replication_not_yet_accepted",
            "view_count": len(audits),
            "run_count": len(summaries),
            "processed_source_rows": sum(audit["processed_rows"] for audit in audits),
            "independent_label_count": 0,
            "accuracy": None,
            "runs": summaries,
            "failures": failures,
            "h1_opened": False,
            "pnl_computed": False,
            "production_authority": False,
            "coverage_warning": "Selected views and scales overlap; neither their rows nor structures are independent observations.",
        },
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
