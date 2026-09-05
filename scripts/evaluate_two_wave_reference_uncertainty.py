#!/usr/bin/env python3
"""Load existing morphology exports and independently supplied references for CI."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.annotations import validate_annotation_document  # noqa: E402
from factor_lab.visual_structure.two_wave.data import load_development_bars  # noqa: E402
from factor_lab.visual_structure.two_wave.models import Config  # noqa: E402
from factor_lab.visual_structure.two_wave.uncertainty import evaluate_block_bootstrap  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_reference_run(run_dir: Path, annotation_path: Path, data_root: Path, manifest: Path) -> tuple[dict, dict]:
    """Fail on product/config mismatch instead of quietly applying foreign labels."""
    config_path, summary_path = run_dir / "config.json", run_dir / "summary.json"
    export = json.loads(config_path.read_text())
    config = Config(**export["config"])
    if export["config_hash"] != config.config_hash or export["scale_id"] != config.scale_id:
        raise ValueError("Stored config identity does not match its parameters")
    if run_dir.parent.name != config.timeframe:
        raise ValueError("Run directory product identity differs from config timeframe")
    summary = json.loads(summary_path.read_text())
    if (summary.get("config_hash"), summary.get("scale_id")) != (config.config_hash, config.scale_id):
        raise ValueError("Summary and export config identities differ")
    bars, audit = load_development_bars(data_root / f"{config.timeframe}.parquet", manifest, max_bars=summary["bars"])
    if audit["view_id"] != config.timeframe or len(bars) != summary["bars"]:
        raise ValueError("Supplied bar product or prefix length differs from the saved export")
    source_files = [config_path, summary_path, annotation_path]
    for kind in ("pivots", "cycles", "structures", "events"):
        path = run_dir / f"{kind}.jsonl"
        export[kind] = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if len(export[kind]) != summary[kind]:
            raise ValueError(f"Saved {kind} count differs from run summary")
        for record in export[kind]:
            for key, expected in (("config_hash", config.config_hash), ("scale_id", config.scale_id), ("timeframe", config.timeframe)):
                if key in record and record[key] != expected:
                    raise ValueError(f"Foreign {kind} record identity: {key}")
            if not 0 <= record["confirmation_bar"] < len(bars):
                raise ValueError(f"Saved {kind} confirmation falls outside the supplied prefix")
        source_files.append(path)
    document = json.loads(annotation_path.read_text())
    if document.get("schema_version") == "two_wave_annotation_reconciliation@1.0":
        document = document["adjudicated_reference"]
    normalized = validate_annotation_document(document)
    expected = (config.config_hash, config.timeframe, config.scale_id)
    keys = ("config_id", "timeframe", "scale_id")
    root_identity = tuple(normalized.get(key) for key in keys)
    if any(root_identity) and root_identity != expected:
        raise ValueError("Reference document root belongs to a different product/config/scale")
    for record in (*normalized["annotations"], *normalized["review_windows"]):
        if tuple(record[key] for key in keys) != expected:
            raise ValueError("Reference record belongs to a different product/config/scale; use a matching --run-dir pair")
    return {
        "product_id": f"{audit['view_id']}|actual_export_frequency={audit['export_frequency']}",
        "export": export, "bars": bars, "annotations": document,
    }, {
        "run_dir": str(run_dir.resolve()), "view_id": audit["view_id"],
        "actual_export_frequency": audit["export_frequency"], "processed_bar_rows": len(bars),
        "independent_reference_records_supplied": len(normalized["annotations"]),
        "source_files_sha256": {str(path.resolve()): digest(path) for path in source_files},
        "source_parquet_sha256": audit["sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir", type=Path, action="append", required=True,
        help="Existing product/reversal directory; repeat with paired labels",
    )
    parser.add_argument("--annotations", type=Path, action="append", required=True, help="Corresponding reference JSON; one per --run-dir")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data/development")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifest.json")
    args = parser.parse_args()
    if len(args.run_dir) != len(args.annotations):
        parser.error("Provide exactly one --annotations for each --run-dir, in the same order")
    runs, inputs = [], []
    for run_dir, annotation_path in zip(args.run_dir, args.annotations, strict=True):
        run, audit = load_reference_run(run_dir, annotation_path, args.data_root, args.manifest)
        runs.append(run)
        inputs.append(audit)
    result = evaluate_block_bootstrap(runs)
    files = [
        Path(__file__), ROOT / "src/factor_lab/visual_structure/two_wave/uncertainty.py",
        ROOT / "src/factor_lab/visual_structure/two_wave/annotations.py",
        ROOT / "docs/research/two_wave_recognition_spec_v0_1.md",
        ROOT / "docs/research/two_wave_evaluation_protocol_v0_1.md", args.manifest,
    ]
    result["execution"] = {
        "actual_input_view_count": len(runs), "inputs": inputs,
        "source_files_sha256": {str(path.resolve()): digest(path) for path in files},
        "recognizer_rerun": False, "third_wave_or_return_research_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"views": len(runs), "status": result["status"], "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
