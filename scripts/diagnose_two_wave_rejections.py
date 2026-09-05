#!/usr/bin/env python3
"""Audit saved H0 rejection combinations; preserve all frozen recognizer outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.diagnostics import (  # noqa: E402
    diagnostic_features,
    mechanism_summary,
    rejection_summary,
)
from factor_lab.visual_structure.two_wave.models import Config  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def compact_summary(summary: dict) -> dict:
    return {
        "n": summary["structures"],
        "clear": summary["clear_count"],
        "uncertain": summary["uncertain_count"],
        "invalid": summary["invalid_geometry_count"],
        "classes": summary["classification_counts"],
        "clear_fraction": summary["clear_fraction"],
        "rule_counts_triggered_sole": {k: [v["triggered"], v["sole_blocker"]] for k, v in summary["rules"].items()},
        "joint_patterns_count_rules": [[row["count"], row["rules"]] for row in summary["joint_patterns"]],
        "single_rule_removed_recovered_clear": {
            k: [v["recovered_count"], v["clear_count_if_flags_removed"]] for k, v in summary["single_rule_removals"].items()
        },
        "group_removed_recovered_clear": {
            k: [v["recovered_count"], v["clear_count_if_flags_removed"]] for k, v in summary["group_removals"].items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True, help="Saved run root containing view/reversal_*/structures.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "cloud_results/two_wave_continuation/rejection_diagnostics")
    args = parser.parse_args()
    source = args.input_root.resolve()
    output = args.output.resolve()
    if output == source or source in output.parents:
        parser.error("diagnostic output must be outside the frozen input run")
    paths = sorted(source.glob("*/reversal_*/structures.jsonl"))
    if not paths:
        parser.error("no saved structure runs found")
    manifest_path = source / "run_manifest.json"
    original_manifest = json.loads(manifest_path.read_text())
    frozen_names = [
        "docs/research/two_wave_recognition_spec_v0_1.md",
        "docs/research/two_wave_evaluation_protocol_v0_1.md",
        "src/factor_lab/visual_structure/two_wave/geometry.py",
        "src/factor_lab/visual_structure/two_wave/models.py",
    ]
    old_hashes = original_manifest["definition_sha256"] | original_manifest["source_sha256"]
    for name in frozen_names:
        if old_hashes.get(name) != digest(ROOT / name):
            raise ValueError(f"frozen definition/model mismatch: {name}")
    input_hashes = {"run_manifest.json": digest(manifest_path)}
    all_rows, per_run, cases = [], {}, []
    for path in paths:
        directory = path.parent
        run_id = directory.relative_to(source).as_posix()
        config_record = json.loads((directory / "config.json").read_text())
        config = Config(**config_record["config"])
        if config.config_hash != config_record["config_hash"] or config.scale_id != config_record["scale_id"]:
            raise ValueError(f"config identity mismatch: {run_id}")
        pivot_rows = read_jsonl(directory / "pivots.jsonl")
        pivots = {p["pivot_id"]: p for p in pivot_rows}
        if len(pivots) != len(pivot_rows):
            raise ValueError(f"duplicate pivot identities: {run_id}")
        rows = read_jsonl(path)
        for row in rows:
            if row["config_hash"] != config.config_hash or row["scale_id"] != config.scale_id or row["timeframe"] != config.timeframe:
                raise ValueError(f"mixed structure identity: {run_id}")
            if not all(
                2015 <= datetime.fromisoformat(row[field]).year <= 2020 for field in ("start_time", "end_time", "confirmation_time")
            ):
                raise ValueError("source contains records outside the declared development interval")
            members = [pivots[pivot_id] for pivot_id in row["pivot_ids"]]
            row.update(
                {
                    "run_id": run_id,
                    "drift_threshold": config.drift_threshold,
                    "max_slope_disagreement": config.max_slope_disagreement,
                    "max_width_ratio": config.max_width_ratio,
                }
            )
            row["diagnostics"] = diagnostic_features(row, members)
        summary = rejection_summary(rows)
        per_run[run_id] = {"config": config.to_dict(), "summary": summary, "mechanisms": mechanism_summary(rows)}
        for name in ("structures.jsonl", "pivots.jsonl", "config.json"):
            input_hashes[(directory / name).relative_to(source).as_posix()] = digest(directory / name)
        all_rows.extend(rows)
        # Explain isolated blockers, not a success gallery. Sample order is fully
        # deterministic and every eligible count remains available in summaries.
        for rule in ("cycle_amplitude_change", "uneven_phase_drift"):
            if any(case["selection_rule"] == rule for case in cases):
                continue
            eligible = sorted((row for row in rows if row["attributes"] == [rule]), key=lambda row: (row["start_bar"], row["structure_id"]))
            if eligible:
                row = eligible[0]
                cases.append(
                    {
                        "selection_rule": rule,
                        "selection": "first run lexicographically, then earliest sole-blocker structure",
                        "not_independent_reference": True,
                        "record": row,
                        "member_pivots": [pivots[pivot_id] for pivot_id in row["pivot_ids"]],
                    }
                )
    overall = rejection_summary(all_rows)
    pooled_views = defaultdict(list)
    for row in all_rows:
        pooled_views[row["timeframe"]].append(row)
    report = {
        "schema_version": "two_wave_rejection_diagnostics@1.0",
        "status": "descriptive_rejection_diagnostics_only_morphology_replication_not_yet_accepted",
        "data_role": "2015_2020_development_material",
        "independent_labels": 0,
        "parameter_selection_authority": False,
        "production_authority": False,
        "h1_opened": False,
        "pnl_computed": False,
        "recognizer_or_thresholds_modified": False,
        "counterfactual_scope": (
            "Remove stored Boolean blockers only; preserve five pivots, fit, D, thresholds and causal history. No rerun."
        ),
        "sample_unit": "Correlated overlapping candidates; cross-view and cross-threshold counts are not independent samples.",
        "per_run": per_run,
        "per_view_pooled_across_correlated_scales": {name: rejection_summary(rows) for name, rows in sorted(pooled_views.items())},
        "overall": overall,
        "mechanisms": mechanism_summary(all_rows),
        "source_snapshot_commit_from_original_manifest": original_manifest.get("source_snapshot_commit"),
        "original_manifest_recognizer_code_commit": None,
        "code_attribution_note": (
            "The original manifest source_snapshot_commit names the asset handoff, not the running recognizer code. "
            "Attribute implementation through the frozen geometry/models source hashes and the original delivery record."
        ),
        "provenance": {
            "input_sha256": input_hashes,
            "frozen_source_and_definition_sha256": {name: digest(ROOT / name) for name in frozen_names},
            "diagnostic_source_sha256": {
                name: digest(ROOT / name)
                for name in ("src/factor_lab/visual_structure/two_wave/diagnostics.py", "scripts/diagnose_two_wave_rejections.py")
            },
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "report.json", report)
    write_json(output / "case_studies.json", {"cases": cases, "morphology_correctness_claimed": False})
    with (output / "structure_diagnostics.jsonl").open("w") as handle:
        for row in all_rows:
            payload = {
                key: row[key]
                for key in (
                    "run_id",
                    "structure_id",
                    "phase",
                    "start_time",
                    "end_time",
                    "confirmation_time",
                    "attributes",
                    "classification",
                    "diagnostics",
                )
            }
            handle.write(json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n")
    # Single complete JSON record is convenient in native CI logs when remote
    # artifact download is unavailable. Pairwise details stay in report.json.
    print(
        json.dumps(
            {
                "status": report["status"],
                "run_count": len(per_run),
                "view_count": len(pooled_views),
                "overall": compact_summary(overall),
                "per_run": {name: compact_summary(value["summary"]) for name, value in per_run.items()},
                "mechanisms": report["mechanisms"],
                "output": str(output),
            },
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
