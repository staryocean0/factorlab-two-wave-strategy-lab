#!/usr/bin/env python3
"""Validate two frozen first-pass v0.6.48 annotation sheets while still model-blind."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.reference_label_quality_v0648 import (
    compare_first_pass_labels,
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotator-a", required=True)
    parser.add_argument("--annotator-b", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    a_path = Path(args.annotator_a)
    b_path = Path(args.annotator_b)
    result = compare_first_pass_labels(pd.read_csv(a_path, dtype=str), pd.read_csv(b_path, dtype=str))
    result["first_pass_sheet_sha256"] = {
        "annotator_a": sha256(a_path),
        "annotator_b": sha256(b_path),
    }
    result["model_scoring_allowed"] = False
    result["reason_model_scoring_blocked"] = (
        "first-pass label quality precedes third-party disagreement adjudication and final reference freeze"
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "all_label_quality_gates_pass": result["all_label_quality_gates_pass"],
        "disagreement_count": result["disagreement_count"],
        "model_scoring_allowed": False,
        "output": str(out),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
