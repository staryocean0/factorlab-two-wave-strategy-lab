#!/usr/bin/env python3
"""Expose bounded morphology aggregates in native CI logs, without raw rows."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("cloud_results/two_wave_h0"))
    args = parser.parse_args()
    summary = json.loads((args.input / "summary.json").read_text())
    manifest = json.loads((args.input / "run_manifest.json").read_text())
    if summary["failures"] or not manifest["source_and_definition_unchanged_during_run"]:
        raise ValueError("Cannot publish a successful audit for a failed or changing run")
    runs = summary["runs"]
    totals = Counter()
    baseline = Counter()
    for run in runs:
        counts = run["classification_counts"]
        if sum(counts.values()) != run["structures"] or not run["prefix_invariance"]["passed"]:
            raise ValueError("Classification counts or prefix checks do not reconcile")
        totals.update(counts)
        if run["config"]["reversal_log"] == 0.01:
            baseline.update(counts)
        record = {
            "view": run["config"]["timeframe"],
            "reversal_log": run["config"]["reversal_log"],
            "config_hash": run["config_hash"],
            "bars": run["bars"],
            "structures": run["structures"],
            "classification_counts": counts,
            "rejection_attribute_counts_nonexclusive": run["rejection_attribute_counts_nonexclusive"],
            "invalid_geometry_structures": run["invalid_geometry_structures"],
            "classification_coverage_among_structures": run["classification_coverage_among_structures"],
            "already_outside_at_confirmation_count": run["already_outside_at_confirmation_count"],
            "structure_confirmation_delay_bars_quantiles": run["structure_confirmation_delay_bars_quantiles"],
            "prefix_passed": True,
        }
        print("TWO_WAVE_RUN_JSON=" + json.dumps(record, sort_keys=True, allow_nan=False), flush=True)
    audit = {
        "status": summary["status"],
        "view_count": summary["view_count"],
        "run_count": summary["run_count"],
        "processed_source_rows": summary["processed_source_rows"],
        "classification_counts_all_scales": dict(totals),
        "classification_counts_baseline_0_01": dict(baseline),
        "independent_label_count": summary["independent_label_count"],
        "accuracy": summary["accuracy"],
        "definition_sha256": manifest["definition_sha256"],
        "source_sha256": manifest["source_sha256"],
        "data_manifest_sha256": manifest["data_manifest_sha256"],
        "source_and_definition_unchanged_during_run": True,
        "input_products": manifest["input_products"],
        "manifest_products_missing_locally": manifest["manifest_products_missing_locally"],
        "started_at": manifest["started_at"],
        "finished_at": manifest["finished_at"],
        "h1_opened": False,
        "pnl_computed": False,
        "interpretation": "Correlated descriptive counts, never independent labels or accuracy.",
    }
    print("TWO_WAVE_AUDIT_JSON=" + json.dumps(audit, sort_keys=True, allow_nan=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
