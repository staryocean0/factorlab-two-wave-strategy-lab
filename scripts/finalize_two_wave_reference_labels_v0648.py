#!/usr/bin/env python3
"""Freeze final v0.6.48 reference labels after model-blind adjudication."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.reference_label_freeze_v0648 import freeze_final_reference


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotator-a", type=Path, required=True)
    parser.add_argument("--annotator-b", type=Path, required=True)
    parser.add_argument("--adjudicator", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    a_bytes = args.annotator_a.read_bytes()
    b_bytes = args.annotator_b.read_bytes()
    third_bytes = args.adjudicator.read_bytes() if args.adjudicator else None
    a = pd.read_csv(io.BytesIO(a_bytes), dtype=str, keep_default_na=False)
    b = pd.read_csv(io.BytesIO(b_bytes), dtype=str, keep_default_na=False)
    third = (
        pd.read_csv(io.BytesIO(third_bytes), dtype=str, keep_default_na=False)
        if third_bytes is not None
        else None
    )

    final, audit = freeze_final_reference(a, b, third)
    args.output.mkdir(parents=True, exist_ok=True)
    final_bytes = final.to_csv(index=False, lineterminator="\n").encode("utf-8")
    final_path = args.output / "FINAL_REFERENCE_LABELS.csv"
    final_path.write_bytes(final_bytes)
    audit = {
        **audit,
        "annotator_a_sha256": sha256_bytes(a_bytes),
        "annotator_b_sha256": sha256_bytes(b_bytes),
        "adjudicator_sha256": sha256_bytes(third_bytes) if third_bytes is not None else None,
        "final_reference_sha256": sha256_bytes(final_bytes),
        "final_reference_file": final_path.name,
        "morphology_acceptance": False,
        "trade_authority": False,
        "production_authority": False,
    }
    audit["status"] = (
        "final_reference_frozen_model_scoring_authorized"
        if audit["model_scoring_allowed"]
        else "final_reference_frozen_model_scoring_blocked_by_first_pass_quality"
    )
    (args.output / "FINAL_REFERENCE_FREEZE.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(audit, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
