#!/usr/bin/env python3
"""Audit frozen review-window dependence without inventing reference labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars  # noqa: E402
from factor_lab.visual_structure.two_wave.uncertainty import (  # noqa: E402
    MIN_BLOCKS,
    build_calendar_blocks,
    shared_block_weights,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True, help="Existing run directory containing per-view/reversal_0.01 windows")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data/development")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifest.json")
    args = parser.parse_args()
    files = sorted(args.results.glob("*/reversal_0.01/preselected_review_windows.json"))
    if not files:
        raise ValueError("No frozen baseline reversal_0.01 window lists found")
    windows, inputs, input_rows = [], [], 0
    for path in files:
        view = path.parent.parent.name
        bars, audit = load_development_bars(args.data_root / f"{view}.parquet", args.manifest)
        declared = json.loads(path.read_text())
        input_rows += len(bars)
        product = f"{audit['view_id']}|actual_export_frequency={audit['export_frequency']}"
        for window in declared:
            if window.get("fully_reviewed", False) or window.get("complete_reviewed", False):
                raise ValueError("Design audit requires unreviewed preselected windows; use evaluation for completed reviews")
            windows.append({
                **window,
                "product_id": product,
                "start_time": bars[window["start_index"]]["timestamp"],
                "end_time": bars[window["end_index"]]["timestamp"],
            })
        inputs.append({
            "view_id": view,
            "actual_export_frequency": audit["export_frequency"],
            "bar_rows": len(bars),
            "window_count": len(declared),
            "source_window_path": str(path.resolve()),
            "source_window_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "source_parquet_sha256": hashlib.sha256((args.data_root / f"{view}.parquet").read_bytes()).hexdigest(),
        })
    plan = build_calendar_blocks(windows)
    weights, strata = shared_block_weights(plan["blocks"])
    by_product_year: dict[tuple[str, int], set[str]] = defaultdict(set)
    for block in plan["blocks"]:
        for product, _, _, year in block["participation"]:
            by_product_year[product, year].add(block["block_id"])
    own_product_plans = {}
    for product in sorted({w["product_id"] for w in windows}):
        own = build_calendar_blocks([w for w in windows if w["product_id"] == product])
        own_product_plans[product] = {"window_count": own["input_window_count"], "within_product_block_count": own["block_count"]}
    protocol = ROOT / "docs/research/two_wave_evaluation_protocol_v0_1.md"
    source_files = [
        Path(__file__), ROOT / "src/factor_lab/visual_structure/two_wave/uncertainty.py",
        ROOT / "docs/research/two_wave_recognition_spec_v0_1.md", protocol, args.manifest,
    ]
    result = {
        "schema_version": "two_wave_window_block_design_audit@1.0",
        "status": "morphology_replication_not_yet_accepted",
        "authority": "research_only_no_hypothesis_or_trading_promotion",
        "run_scope": "Existing preselected baseline windows; calendar design only; no recognizer rerun or reference evaluation",
        "actual_input_view_count": len(files),
        "actual_input_bar_rows": input_rows,
        "overlapping_product_rows_are_not_independent_observations": True,
        "inputs": inputs,
        "frozen_protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
        "source_files_sha256": {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files},
        "calendar_plan": plan,
        "joint_product_scale_year_sampling_strata": strata,
        "minimum_blocks_per_joint_stratum": MIN_BLOCKS,
        "minimum_blocks_policy": "Supplementary conservative implementation assumption; not predeclared numeric protocol v0.1 threshold",
        "sparse_joint_strata_count": sum(s["block_count"] < MIN_BLOCKS for s in strata),
        "resampling_design_draws": len(weights),
        "resampling_design_seed": 20260905,
        "resampling_weights_sha256": hashlib.sha256(weights.astype("<i8").tobytes()).hexdigest(),
        "by_product_year": [
            {"product_id": product, "year": year, "joint_calendar_block_count": len(ids), "block_ids": sorted(ids)}
            for (product, year), ids in sorted(by_product_year.items())
        ],
        "product_only_plans_descriptive": own_product_plans,
        "complete_reviewed_windows": 0,
        "independent_reference_count": 0,
        "bootstrap_metric_evaluation_run": False,
        "confidence_intervals_95": None,
        "ci_withheld_reasons": ["no_independent_reference_labels", "no_complete_reviewed_windows"]
        + (["sparse_joint_calendar_blocks"] if any(s["block_count"] < MIN_BLOCKS for s in strata) else []),
        "interpretation": (
            "When present, full-year daily cores connect all overlapping intraday cores of that year. "
            "Repeated products/frequencies do not create independent blocks. "
            "Removing daily products or shortening frozen cores solely to obtain intervals would change the evaluation design."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "views": len(files), "windows": len(windows), "calendar_blocks": plan["block_count"],
        "sparse_joint_strata": result["sparse_joint_strata_count"], "confidence_intervals_95": None,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
