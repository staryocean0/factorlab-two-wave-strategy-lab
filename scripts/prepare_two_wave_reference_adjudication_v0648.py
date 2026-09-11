#!/usr/bin/env python3
"""Freeze two first-pass sheets and prepare the model-blind v0.6.48 disagreement packet."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.reference_label_freeze_v0648 import adjudication_tables

EXPECTED_PACKET_SHA256 = "4c08c8d3f32c6e222acb3c4236fa8f39428ff25349deae16d6f49dca2901566e"
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def add_bytes(zf: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    zf.writestr(info, data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotator-a", type=Path, required=True)
    parser.add_argument("--annotator-b", type=Path, required=True)
    parser.add_argument("--packet-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    a_bytes = args.annotator_a.read_bytes()
    b_bytes = args.annotator_b.read_bytes()
    packet_bytes = args.packet_zip.read_bytes()
    if sha256_bytes(packet_bytes) != EXPECTED_PACKET_SHA256:
        raise RuntimeError("blinded packet SHA256 does not match frozen v0.6.48 packet")

    a = pd.read_csv(io.BytesIO(a_bytes), dtype=str, keep_default_na=False)
    b = pd.read_csv(io.BytesIO(b_bytes), dtype=str, keep_default_na=False)
    quality, first_pass, blank = adjudication_tables(a, b)
    disagreement_ids = quality["disagreement_case_ids"]

    args.output.mkdir(parents=True, exist_ok=True)
    quality_path = args.output / "FIRST_PASS_QUALITY.json"
    freeze = {
        "schema": "two_wave_v0648_first_pass_freeze@1.0",
        "annotator_a_sha256": sha256_bytes(a_bytes),
        "annotator_b_sha256": sha256_bytes(b_bytes),
        "blinded_packet_sha256": EXPECTED_PACKET_SHA256,
        "annotator_a_id": quality["annotator_a"],
        "annotator_b_id": quality["annotator_b"],
        "disagreement_count": quality["disagreement_count"],
        "first_pass_label_quality_pass": bool(quality["all_label_quality_gates_pass"]),
        "hidden_strata_unblinded": False,
        "model_predictions_unblinded": False,
        "model_scoring_allowed": False,
    }
    quality_path.write_text(json.dumps(quality, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    (args.output / "FIRST_PASS_FREEZE.json").write_text(
        json.dumps(freeze, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )

    zip_path = args.output / "two_wave_v0648_disagreement_adjudication_packet.zip"
    readme = f"""# Two-Wave v0.6.48 independent third adjudication\n\nThis packet contains only the {len(disagreement_ids)} cases where the two already-frozen first-pass annotators disagree under the v0.6.48 protocol.\n\nThe third adjudicator must remain blind to model predictions, hidden candidate/control stratum, absolute date/year, future bars, returns and P&L. The first-pass labels shown here are frozen and may not be edited. Complete only `ADJUDICATION_LABEL_SHEET.csv`.\n\n`annotator_id` must identify one adjudicator distinct from both first-pass annotators. Set `independent_of_first_pass_annotators=true` and `blinded_to_model=true` only if true. `completed_at` must be timezone-aware ISO-8601.\n\nThe semantic labels and optional anchors use the same definitions as the original packet. No unresolved disagreement may remain in the finalized reference set.\n"""

    with zipfile.ZipFile(io.BytesIO(packet_bytes), "r") as source, zipfile.ZipFile(
        zip_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as out:
        add_bytes(out, "ADJUDICATOR_README.md", readme.encode("utf-8"))
        add_bytes(out, "FIRST_PASS_LABELS.csv", csv_bytes(first_pass))
        add_bytes(out, "ADJUDICATION_LABEL_SHEET.csv", csv_bytes(blank))
        for case_id in disagreement_ids:
            chart = f"cases/{case_id}.png"
            try:
                data = source.read(chart)
            except KeyError as exc:
                raise RuntimeError(f"missing frozen blinded chart {chart}") from exc
            add_bytes(out, chart, data)

    manifest = {
        **freeze,
        "adjudication_packet_sha256": sha256_bytes(zip_path.read_bytes()),
        "adjudication_packet_case_count": len(disagreement_ids),
        "adjudication_packet_contains_hidden_mapping": False,
    }
    (args.output / "ADJUDICATION_PACKET_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
